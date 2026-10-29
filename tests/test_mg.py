# docs/minigames_bosses.md step 1: the mini-game framework (src/mg.c) and its stub game GREEN LIGHT (src/mg_stub.c):
# GS_MINI, the phases INTRO -> COUNT -> PLAY -> END -> RESULT, the HUD timer, medals (points, the icon, the story's
# gold-medal life), the story / practice prompts, RETRY / MENU, mg_say (ROM0) and the bonus rounds on it, the story's
# mini slot (story.c step_start, a slot marked built by the story_unskip test hook) and the resources put back after
# a mini-game (the bonus rounds' M12 / M14a checks). Sprites per line <= 10 on every frame of every flow here.
import json
import re

import pytest
from split_helpers import win_lyc
from conftest import ROM, ROOT, check_golden, hold_stage_anim, title_level, venue
from test_bonus import lines
from test_flow import GS_GOAL, LEVEL_CLEAR, PLAYING, TITLE, patron_group_tiles, run_until, state, tilemap_row
from test_story import BANKS, SEQ, hud_lives, lives_hud, to_goal, to_shift, win

pytestmark = pytest.mark.timeout(300)

GS_MINI = 13
GS_MGLIST = 15                                      # BONUS > MINI GAMES (src/mg_list.c): practice's B comes back here
MG_QUICKDRAW, MG_TSHIRT = 0, 1                      # mg.h: game ids (each with its own venue)
MG_INTRO, MG_COUNT, MG_PLAY, MG_END, MG_RESULT = range(5)
MG_STORY, MG_PRACTICE, MG_HARD = 0, 1, 2
MG_STUB = 16                                       # (mg.h: ids are games, not venues; the stub is not saved)
MEDAL_NONE, MEDAL_BRONZE, MEDAL_SILVER, MEDAL_GOLD = range(4)
GL_NEXT, GL_RED, GL_GREEN, GL_SHOW = range(4)
MG_C = (ROOT / "src" / "mg.c").read_text()
STUB_C = (ROOT / "src" / "mg_stub.c").read_text()
MG_H = (ROOT / "src" / "mg.h").read_text()


def define(name, text):
    return int(re.search(rf"#define {name}\s+\(?(\d+)", text).group(1))


INTRO_LEN, COUNT_LEN, GO_AT, END_LEN, RESULT_MIN = (define(n, MG_C) for n in
                                                    ("MG_INTRO_LEN", "MG_COUNT_LEN", "MG_GO_AT", "MG_END_LEN", "MG_RESULT_MIN"))
ROUNDS, RED_MIN, RED_MIN_HARD, GREEN_MAX = (define(n, STUB_C) for n in ("STUB_ROUNDS", "RED_MIN", "RED_MIN_HARD", "GREEN_MAX"))
STEP_PTS, STEP_PTS_HARD, LAMP_COL, LAMP_ROW = (define(n, STUB_C) for n in ("STEP_PTS", "STEP_PTS_HARD", "LAMP_COL", "LAMP_ROW"))
MG_BG, MG_ICON_PAL = define("MG_BG", MG_H), define("MG_ICON_PAL", MG_C)
ICON_N = define("MG_ICON_N", MG_H)                 # the medal icon: ICON_N x ICON_N tiles (32x32) a medal
ICON_TILES = 3 * ICON_N * ICON_N                    # GOLD, SILVER, BRONZE
MG_GAME_BG = MG_BG + ICON_TILES
TEXT_COL = ICON_N                                   # the window's text: centred in columns TEXT_COL..19
MEDAL_AT = [int(v) for v in re.search(r"medal_at\[MG_GAMES\]\[3\] = \{ \{ (\d+), (\d+), (\d+) \}", MG_C).groups()]
MEDAL_PTS = [0, 500, 1500, 3000]
ART = json.loads((ROOT / "build" / "mg.json").read_text())
ART_H = (ROOT / "build" / "art.h").read_text()
GLYPH_CH = {int(m[1]): m[0] for m in re.findall(r"#define TILE_GLYPH_(\w) (\d+)", ART_H)}
BLANK = int(re.search(r"#define TILE_HUD_BLANK (\d+)", ART_H).group(1))
PANEL_TOP = int(re.search(r"#define TILE_PANEL_TOP (\d+)", ART_H).group(1))
PANEL_BOT = int(re.search(r"#define TILE_PANEL_BOT (\d+)", ART_H).group(1))
OUT = ROOT / "out" / "mg"
SEED = 0x5A17


# ---- driving -------------------------------------------------------------------------------------------------------
def mg_enter(gb, gid, mode, seed=SEED):
    """Call the game's BANKED mg_enter(gid, mode) between two frames: a PyBoy hook on vq_frame_end (called right after
    update(), so no frame is half done) diverts the CPU once into a stub below SP (push the registers; the two byte
    arguments on the stack, as SDCC passes them to a banked function; ld e, bank; ld hl, mg_enter; call
    ___sdcc_bcall_ehl; pop) that returns to vq_frame_end."""
    gb.write("mg_seed_force", seed & 0xFF)
    gb.write(gb.addr("mg_seed_force") + 1, seed >> 8)
    f, bank, bc = gb.addr("mg_enter") & 0xFFFF, BANKS["b_mg_enter"], gb.addr("___sdcc_bcall_ehl") & 0xFFFF
    hook = gb.addr("vq_frame_end") & 0xFFFF
    hits = [0]

    def divert(_):
        hits[0] += 1
        if hits[0] != 1:
            return
        rf = gb.pb.register_file
        sp, pc = rf.SP, rf.PC
        stub = sp - 360                       # below anything mg_enter's calls push, and inside the stack's free space (WRAM_HI_0 keeps 446 B between .HEAP and .STACK: sp - 600 was inside the music buffer)
        code = [0xF5, 0xC5, 0xD5, 0xE5, 0x3E, mode, 0xF5, 0x33, 0x3E, gid, 0xF5, 0x33, 0x1E, bank, 0x21, f & 0xFF, f >> 8,
                0xCD, bc & 0xFF, bc >> 8, 0xE1, 0xE1, 0xD1, 0xC1, 0xF1, 0xC9]
        for i, b in enumerate(code):
            gb.pb.memory[stub + i] = b
        gb.pb.memory[sp - 2], gb.pb.memory[sp - 1] = pc & 0xFF, pc >> 8
        rf.SP, rf.PC = sp - 2, stub

    gb.pb.hook_register(0, hook, divert, None)
    try:
        for _ in range(60):
            gb.run(1)
            if hits[0] >= 2:
                break
    finally:
        gb.pb.hook_deregister(0, hook)
    assert hits[0] >= 2 and state(gb) == GS_MINI
    run_until(gb, lambda: gb.pb.memory[0xFF40] & 0x80, 10)


def practice(model, mode=MG_PRACTICE, seed=SEED):
    """A booted rom on the title, then the stub mini-game in practice (or `mode`)."""
    from test_scores import booted
    rom = booted(model)
    hold_stage_anim(rom)
    mg_enter(rom, MG_STUB, mode, seed)
    return rom


def frames(gb, n, worst=None):
    """n frames, one at a time, with the 10-sprites-per-line check on each."""
    for _ in range(n):
        gb.run(1)
        assert max(lines(gb)) <= 10
        if worst is not None:
            worst[0] = max(worst[0], max(lines(gb)))


def until(gb, cond, limit=600):
    for _ in range(limit):
        if cond():
            return
        frames(gb, 1)
    raise AssertionError(f"not reached in {limit} frames (phase {gb.mem('mg_phase')})")


def stub(gb):
    st, rnd, t, wait, react = gb.read("story_scratch", 5)
    return dict(st=st, round=rnd, t=t, wait=wait, react=react)


def text(gb, row, window=False, x0=0):
    return "".join(GLYPH_CH.get(t, " ") if t != BLANK else " " for t in tilemap_row(gb, row, x0, 20 - x0, window)).strip()


HOURGLASS = 220          # MG_HOURGLASS (src/mg.h): the timer's icon tile


def hud_timer(gb):
    """The HUD timer's two digits as text; the layout is column 16 blank, the hourglass at 17, the digits at 18-19
    (owner 2026-10-13: two digits and an hourglass in place of the 'T')."""
    t = tilemap_row(gb, 0, 16, 4)
    assert t[0] == BLANK and t[1] == HOURGLASS, f"HUD timer layout {t}"
    return "".join(GLYPH_CH.get(x, "?") for x in t[2:])


def score(gb):
    return gb.mem16("score") | (gb.mem16(gb.addr("score") + 2) << 16)


def to_play(gb):
    until(gb, lambda: gb.mem("mg_phase") == MG_PLAY, INTRO_LEN + COUNT_LEN + 10)


def press_a(gb):
    gb.hold("a")
    frames(gb, 1)
    gb.release("a")
    frames(gb, 1)


def play_round(gb, after=3):
    """Wait for green, press A `after` frames into it; returns the round's points."""
    until(gb, lambda: stub(gb)["st"] == GL_GREEN, 200)
    while stub(gb)["t"] < after:
        frames(gb, 1)
    before = gb.mem16("mg_score")
    press_a(gb)
    s = stub(gb)
    assert s["st"] == GL_SHOW and s["react"]
    return gb.mem16("mg_score") - before


def shot(gb, name):
    OUT.mkdir(parents=True, exist_ok=True)
    gb.screenshot(OUT / f"{name}.{gb.model_name}.png", 4)


def to_result(gb, mg_score=None):
    if mg_score is not None:
        gb.write("mg_score", mg_score & 0xFF)
        gb.write(gb.addr("mg_score") + 1, mg_score >> 8)
    gb.write("mg_phase", MG_RESULT)
    until(gb, lambda: gb.mem("overlay_on") == 1, 10)
    frames(gb, 2)


def medal_of(points):
    return sum(points >= t for t in MEDAL_AT)


# ---- the flow ----------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_whole_flow_in_practice(model):
    """INTRO banner (name, instruction), READY / GO, five rounds of play with the HUD timer counting, the outro, the
    result window (name, score, medal and its icon, the practice prompt); the medal's points on the score."""
    with practice(model) as gb:
        assert gb.mem("mg_id") == MG_STUB and gb.mem("mg_mode") == MG_PRACTICE and gb.mem("mg_phase") == MG_INTRO
        assert text(gb, 2) == "GREEN LIGHT" and text(gb, 3) == "PRESS A ON GREEN"
        assert hud_timer(gb) == "30" and gb.mem16("mg_timer") == 30 * 60 and score(gb) == 0
        assert gb.mem("overlay_on") == 0
        frames(gb, 30)
        shot(gb, "intro")
        check_golden(gb, "mg_intro")
        until(gb, lambda: gb.mem("mg_phase") == MG_COUNT, INTRO_LEN)
        frames(gb, 2)
        assert text(gb, 2) == "READY" and text(gb, 3) == ""
        shot(gb, "count")
        frames(gb, GO_AT)
        assert gb.mem("mg_phase") == MG_COUNT and text(gb, 2) == "GO"
        to_play(gb)
        frames(gb, 3)
        assert stub(gb)["round"] == 1 and stub(gb)["st"] == GL_RED
        assert text(gb, 2) == "ROUND 1" and text(gb, 3) == "WAIT FOR GREEN"
        total = 0
        for r in range(ROUNDS):
            assert stub(gb)["round"] == r + 1
            if r == 1:
                until(gb, lambda: stub(gb)["st"] == GL_GREEN, 200)
                frames(gb, 2)
                assert tilemap_row(gb, LAMP_ROW, LAMP_COL, 2) == [MG_GAME_BG + 4, MG_GAME_BG + 5], "the green lamp"
                shot(gb, "play")
            pts = play_round(gb, after=3 + r)
            react = stub(gb)["react"]
            assert pts == max(100, 1000 - STEP_PTS * react)
            total += pts
            frames(gb, 2)
            assert text(gb, 3) == f"{pts} POINTS"
            if r < ROUNDS - 1:
                until(gb, lambda: stub(gb)["st"] == GL_RED, 60)
        assert gb.mem16("mg_score") == total and score(gb) == total
        assert int(hud_timer(gb)) < 30, "the timer counts down"
        until(gb, lambda: gb.mem("mg_phase") == MG_END, 60)
        frames(gb, 2)
        assert text(gb, 2) == "WELL DONE"
        until(gb, lambda: gb.mem("mg_phase") == MG_RESULT, END_LEN + 2)
        until(gb, lambda: gb.mem("overlay_on") == 1, 10)
        frames(gb, 2)
        m = medal_of(total)
        assert gb.mem("mg_medal") == m and m == MEDAL_GOLD, "a quick player gets gold"
        assert score(gb) == total + MEDAL_PTS[m]
        assert text(gb, 1, True) == "GREEN LIGHT" and text(gb, 2, True, x0=4) == f"SCORE {total}"
        assert text(gb, 3, True, x0=4) == "GOLD 3000" and text(gb, 4, True, x0=4) == "A RETRY B MENU"
        assert tilemap_row(gb, 0, 0, 20, True) == [PANEL_TOP] * 20 and tilemap_row(gb, 5, 0, 20, True) == [PANEL_BOT] * 20
        assert gb.mem("lives") == 3, "no life in practice"
        shot(gb, "result")
        check_golden(gb, "mg_result")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_retries_and_b_goes_back_to_the_menu(model):
    with practice(model) as gb:
        to_play(gb)
        play_round(gb)
        to_result(gb)
        assert score(gb) > 0
        press_a(gb)
        # (12: the reload's LCD-off frames now let the venue tune tick on, music_pump; CGB took 9 frames, now 10)
        run_until(gb, lambda: gb.pb.memory[0xFF40] & 0x80, 12)
        assert state(gb) == GS_MINI and gb.mem("mg_phase") == MG_INTRO and gb.mem("mg_id") == MG_STUB
        assert score(gb) == 0 and gb.mem16("mg_score") == 0, "practice: a retry starts from 0"
        assert gb.mem("overlay_on") == 0 and text(gb, 2) == "GREEN LIGHT"
        to_result(gb)
        gb.press("b", 2)
        run_until(gb, lambda: state(gb) == GS_MGLIST and gb.pb.memory[0xFF40] & 0x80, 30)
        assert gb.mem("overlay_on") == 0, "B: the practice list (BONUS > MINI GAMES)"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_skips_the_count_in_practice_only(model):
    with practice(model) as gb:
        until(gb, lambda: gb.mem("mg_phase") == MG_COUNT, INTRO_LEN + 2)
        frames(gb, 3)
        gb.press("a", 1)
        assert gb.mem("mg_phase") == MG_PLAY and gb.mem("mg_t") < 3
    with practice(model, MG_STORY) as gb:      # (story mode from the title: only the count is looked at)
        until(gb, lambda: gb.mem("mg_phase") == MG_COUNT, INTRO_LEN + 2)
        frames(gb, 3)
        gb.press("a", 1)
        assert gb.mem("mg_phase") == MG_COUNT
        until(gb, lambda: gb.mem("mg_phase") == MG_PLAY, COUNT_LEN)
        assert gb.mem("mg_t") <= 1


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_too_soon_and_too_slow_score_nothing(model):
    with practice(model) as gb:
        to_play(gb)
        until(gb, lambda: stub(gb)["st"] == GL_RED, 5)
        frames(gb, 5)
        press_a(gb)
        assert stub(gb)["st"] == GL_SHOW and stub(gb)["react"] == 0 and gb.mem16("mg_score") == 0
        frames(gb, 2)
        assert text(gb, 3) == "TOO SOON"
        until(gb, lambda: stub(gb)["st"] == GL_GREEN, 300)
        until(gb, lambda: stub(gb)["st"] == GL_SHOW, GREEN_MAX + 2)
        assert stub(gb)["react"] == 0 and gb.mem16("mg_score") == 0
        frames(gb, 2)
        assert text(gb, 3) == "TOO SLOW"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_hard_and_easy_play_as_normal_for_now(model):
    """Owner 2026-10-15: every difficulty plays the same for now (src/mg_stub.c STUB_IS_HARD 0): the waits and the scoring are NORMAL's."""
    for mode in (MG_PRACTICE | MG_HARD, MG_PRACTICE | 4):
        with practice(model, mode) as gb:
            waits = []
            to_play(gb)
            for r in range(3):
                until(gb, lambda: stub(gb)["st"] == GL_RED and stub(gb)["round"] == r + 1, 200)
                waits.append(stub(gb)["wait"])
                pts = play_round(gb, after=4)
                assert pts == max(100, 1000 - STEP_PTS * stub(gb)["react"])
            assert all(RED_MIN - 1 <= w <= RED_MIN + 63 for w in waits)


def first_wait(model, seed):
    with practice(model, seed=seed) as gb:
        to_play(gb)
        until(gb, lambda: stub(gb)["st"] == GL_RED, 5)
        return [stub(gb)["wait"], gb.mem16("mg_seed")]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_mg_seed_force_makes_a_game_repeat(model):
    a, b, c = first_wait(model, 0x1234), first_wait(model, 0x1234), first_wait(model, 0x4321)
    assert a == b and a != c
    assert RED_MIN - 1 <= a[0] <= RED_MIN + 63


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_timer_ends_the_play(model):
    with practice(model) as gb:
        to_play(gb)
        gb.write("mg_timer", 61)
        gb.write(gb.addr("mg_timer") + 1, 0)
        frames(gb, 2)
        assert hud_timer(gb) == "01"
        until(gb, lambda: gb.mem("mg_phase") == MG_END, 62)
        frames(gb, 2)
        assert gb.mem16("mg_timer") == 0 and hud_timer(gb) == "00" and text(gb, 2) == "TIME UP"
        until(gb, lambda: gb.mem("mg_phase") == MG_RESULT, END_LEN + 2)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("points", [0, 1499, 1500, 2999, 3000, 3999, 4000, 5000])
def test_medals_points_icon_and_palette(model, points):
    with practice(model) as gb:
        to_play(gb)
        before = score(gb)
        to_result(gb, points)
        m = medal_of(points)
        assert gb.mem("mg_medal") == m and score(gb) == before + MEDAL_PTS[m]
        assert text(gb, 2, True, x0=4) == f"SCORE {points}"
        word = ["NO MEDAL", "BRONZE 500", "SILVER 1500", "GOLD 3000"][m]
        assert text(gb, 3, True, x0=4) == word
        icon = [tilemap_row(gb, r, 0, ICON_N, True) for r in range(1, 1 + ICON_N)]
        if m:
            t = MG_BG + (MEDAL_GOLD - m) * ICON_N * ICON_N
            assert icon == [[t + r * ICON_N + c for c in range(ICON_N)] for r in range(ICON_N)], "4x4, row-major"
            vram = b"".join(bytes(gb.read(0x9000 + k * 16, 16)) for k in range(MG_BG, MG_BG + ICON_TILES))
            assert vram == bytes(ART["medal"]), "the icon tiles at MG_BG"
        else:
            assert icon == [[BLANK] * ICON_N] * ICON_N
        if gb.model_name == "cgb":
            from test_lift import cgb_bg_palette
            attrs = [gb.pb.memory[1, 0x9C00 + r * 32 + c] & 7 for r in range(6) for c in range(20)]
            icon_cells = [r * 20 + c for r in range(1, 1 + ICON_N) for c in range(ICON_N)]
            assert [attrs[i] for i in icon_cells] == [MG_ICON_PAL] * len(icon_cells), "the icon's cells: its palette"
            assert all(a == 1 for i, a in enumerate(attrs) if i not in icon_cells), "the rest: the HUD's"
            hud = cgb_bg_palette(gb, 1)
            assert cgb_bg_palette(gb, MG_ICON_PAL)[3] == hud[3], "the icon's band is the HUD's"
            if not m:
                assert cgb_bg_palette(gb, MG_ICON_PAL) == hud, "no medal: the blank cells look like the HUD"
        if m == MEDAL_GOLD:
            shot(gb, "result_gold")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("points", [4000, 2000, 0], ids=["gold", "bronze", "none"])
def test_the_result_window_layout(model, points):
    """The approved 32x32 medal: its 4x4 tiles at columns 0-3 of window rows 1-4 (blank without a medal); every text
    line centred in columns 4-19, none reaching into columns 0-3; the panels full width."""
    with practice(model) as gb:
        to_play(gb)
        to_result(gb, points)
        m = medal_of(points)
        rows = [tilemap_row(gb, r, 0, 20, True) for r in range(6)]
        assert rows[0] == [PANEL_TOP] * 20 and rows[5] == [PANEL_BOT] * 20
        t = MG_BG + (MEDAL_GOLD - m) * ICON_N * ICON_N
        for r in range(1, 5):
            icon = rows[r][:TEXT_COL]
            assert icon == ([t + (r - 1) * ICON_N + c for c in range(ICON_N)] if m else [BLANK] * ICON_N), r
            line = text(gb, r, True, x0=TEXT_COL)
            assert line and len(line) <= 20 - TEXT_COL
            first = next(c for c in range(TEXT_COL, 20) if rows[r][c] != BLANK)
            assert first == TEXT_COL + (20 - TEXT_COL - len(line)) // 2, (r, line, first)
        assert text(gb, 1, True, x0=TEXT_COL) == "GREEN LIGHT" and text(gb, 4, True, x0=TEXT_COL) == "A RETRY B MENU"


# ---- mg_say (ROM0) and the bonus rounds on it: their tests and goldens (test_bonus*.py) are unchanged -----------------
def test_mg_say_is_in_rom0_and_the_bonus_rounds_use_it():
    noi = {p[1]: int(p[2], 16) for p in (l.split() for l in ROM.with_suffix(".noi").read_text().splitlines())
           if len(p) == 3}
    assert noi["_mg_say"] < 0x4000 and noi["_show_overlay"] < 0x4000
    for f in ("bonus.c", "bonus2.c"):
        src = (ROOT / "src" / f).read_text()
        assert "mg_say(" in src and "glyph_for(s[i])" not in src


def test_the_union_fits_story_scratch():
    """The static assert is in src/mg.h; the buffer it overlays is story.c's backdrop (STORY_PIC_ROWS x 20, twice)."""
    assert "mg_ram_fits_in_story_scratch[(sizeof(union mg_ram) <= STORY_SCRATCH)" in MG_H
    assert re.search(r"#define STORY_SCRATCH 520\b", (ROOT / "src" / "game.h").read_text())
    noi = {p[1]: int(p[2], 16) for p in (l.split() for l in ROM.with_suffix(".noi").read_text().splitlines())
           if len(p) == 3}
    assert "_bd_map" not in noi and "_story_scratch" in noi


# ---- back to the bar: everything borrowed is put back by the next level load -----------------------------------------
def restored(gb, theme):
    """The level's screen and VRAM as a level load leaves them (test_bonus2 after a bonus round)."""
    v = venue(theme)
    assert tilemap_row(gb, 7, 0, 20) == v["bar_map"][40:60]
    assert tilemap_row(gb, 17, 0, 20) == [v["floor_tile"]] * 20
    obj = b"".join(bytes(gb.read(0x8000 + t * 16, 16)) for t in range(96, 128))
    assert obj == bytes(v["show"]), "the performer tiles are back"
    g = gb.mem("cur_group")
    n = MG_GAME_BG + max(len(ART["lamp"]), len(ART["qd_bg"])) // 16 - 78   # patron ids 78.. up to the games' own tiles
    # (MG_BG = 77 is no patron's)
    bg = b"".join(bytes(gb.read((0x9000 if t < 128 else 0x8000) + t * 16, 16)) for t in range(78, 78 + n))
    assert bg == patron_group_tiles(g, gb)[:n * 16], "the patron tiles are back over the medal icon and the lamp"
    assert tilemap_row(gb, 0, 0, 20, True) == [PANEL_TOP] * 20, "the window's rows as win_init left them"
    assert tilemap_row(gb, 2, 0, 20, True) == [PANEL_BOT] * 20
    assert win_lyc(gb.mem) == gb.mem(0xFF4A) + 22, "LYC is the banner's (BANNER_LYC) again"
    if gb.model_name == "dmg":
        assert gb.mem(0xFF49) == 0xE4, "OBP1 is the game's (0xE4 in play)"
        return
    assert [gb.pb.memory[1, 0x9C00 + r * 32 + c] & 7 for r in range(6) for c in range(20)] == [1] * 120


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_menu_then_arcade_has_everything_back(model):
    with practice(model) as gb:
        to_play(gb)
        play_round(gb)
        to_result(gb)
        gb.press("b", 2)                                # the practice list
        run_until(gb, lambda: state(gb) == GS_MGLIST and gb.pb.memory[0xFF40] & 0x80, 30)
        gb.run(3)
        gb.press("b", 2)                                # the title's BONUS submenu
        run_until(gb, lambda: state(gb) == TITLE and gb.pb.memory[0xFF40] & 0x80, 30)
        gb.run(10)
        gb.press("b", 2)                                # its top level
        gb.run(10)
        title_level(gb)
        run_until(gb, lambda: state(gb) == PLAYING, 60)
        gb.run(2)
        restored(gb, "saloon")


# ---- the story's mini slot ---------------------------------------------------------------------------------------------
def test_the_mini_slots_stay_not_built():
    assert [s["kind"] for s in SEQ if not s["built"]] == ["MINI"]            # (the boss has no step of his own: he comes in Last call's level)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("points", [4000, 0], ids=["gold", "none"])
def test_a_built_mini_slot_plays_the_mini_game_and_the_story_goes_on(model, points):
    """The saloon's mini slot is built (Quick Draw, tests/test_qd.py): after the Happy hour mg_enter(MG_QUICKDRAW,
    MG_STORY) plays; its result says A CONTINUE, takes A only after 60 frames, gives gold its life; then the Last
    call's banner, the lives carried, the step reached saved; the level load put back everything the mini-game
    borrowed. Any medal (none too) goes on. (The medal is poked through the result: Quick Draw's own rule is
    tests/test_qd.py's; here mg_score stands in and the medal comes from its rounds: none were played.)"""
    with to_shift(model, 0, 1) as gb:
        win(gb, 0, 1)
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 20)
        run_until(gb, lambda: state(gb) == GS_MINI, 800)
        run_until(gb, lambda: gb.pb.memory[0xFF40] & 0x80, 10)
        assert gb.mem("mg_id") == MG_QUICKDRAW and gb.mem("mg_mode") == MG_STORY and gb.mem("story_step") == 2
        assert text(gb, 2) == "QUICK DRAW" and gb.mem("lives") == 3
        before = score(gb)
        assert before > 0, "the story's score carries into the mini-game"
        frames(gb, 30)
        if points:
            shot(gb, "story_intro")
        until(gb, lambda: gb.mem("mg_phase") == MG_COUNT, INTRO_LEN + 2)
        frames(gb, 3)
        gb.press("a", 1)
        assert gb.mem("mg_phase") == MG_COUNT, "the count cannot be skipped in the story"
        to_play(gb)
        if points:                                      # Quick Draw's medal is its rounds: 3-0 is gold
            gb.write(gb.addr("story_scratch") + 2, 3)
        to_result(gb, points)
        m = medal_of(points)
        assert gb.mem("mg_medal") == m and score(gb) == before + MEDAL_PTS[m]
        assert text(gb, 4, True) == "A CONTINUE"
        assert gb.mem("lives") == (4 if m == MEDAL_GOLD else 3)
        frames(gb, 2)
        assert hud_lives(gb) == lives_hud(gb.mem("lives"))
        if points:
            shot(gb, "story_result")
            check_golden(gb, "mg_story_gold")
        press_a(gb)
        assert state(gb) == GS_MINI, "A only after the result has shown 60 frames"
        until(gb, lambda: gb.mem("mg_t") >= RESULT_MIN, RESULT_MIN)
        gb.press("a", 2)
        run_until(gb, lambda: state(gb) == GS_GOAL, 60)
        gb.run(3)
        assert gb.mem("story_shift") == 2 and gb.mem("story_step") == 3 and gb.mem("story_chapter") == 0
        assert gb.mem("lives") == (4 if m == MEDAL_GOLD else 3)
        assert gb.mem("story_reached") == 3, "the step after the mini-game is saved as reached"
        to_goal(gb)
        gb.run(2)
        assert hud_lives(gb) == lives_hud(gb.mem("lives"))
        restored(gb, "saloon")


def unbuilt_game():
    """A planned game (id = its venue) that mg.c has no game for yet, or None: it plays the stub."""
    built = set(re.findall(r"if \(id == (MG_\w+)\) mg_game", MG_C)) | {"MG_QUICKDRAW"}
    for name, gid in re.findall(r"#define (MG_[A-Z]+)\s+(\d+)\s+// the ", MG_H):
        if name not in built and int(gid) < 10:
            return int(gid)
    return None


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_an_unbuilt_venue_s_slot_plays_the_stub_in_its_own_venue(model):
    """The id is the game, not the venue (the old id 9 was both the stub and the space lounge): the slot of a venue whose game is not built,
    marked built by story_unskip, is mg_enter(its id) in that venue (its tune, its backdrop), playing the stub; the stub itself (MG_STUB)
    and the space lounge's id stay apart. With every planned game built (all ten) no venue is left to try, so the first part is skipped and the stub
    mechanism is tested with ids that name no game (10, 15, 20: mg.c's default, G_STUB, in the saloon's venue)."""
    gid0 = unbuilt_game()
    if gid0 is not None:
        with to_shift(model, gid0, 1) as gb:
            gb.write("story_unskip", 1 << 2)
            win(gb, gid0, 1)
            run_until(gb, lambda: state(gb) == GS_MINI, 800)
            run_until(gb, lambda: gb.pb.memory[0xFF40] & 0x80, 10)
            assert gb.mem("mg_id") == gid0 and gb.mem("venue_id") == gid0 and text(gb, 2) == "GREEN LIGHT"
    for gid, venue in ((9, 9), (MG_STUB, 0), (MG_QUICKDRAW, 0), (10, 0), (15, 0), (20, 0)):
        with practice(model) as gb:
            mg_enter(gb, gid, MG_PRACTICE)
            assert gb.mem("mg_id") == gid and gb.mem("venue_id") == venue, (gid, venue)
            if gid in (10, 15, 20):             # no game of that id: the stub plays (mg.c's default)
                run_until(gb, lambda: state(gb) == GS_MINI and gb.pb.memory[0xFF40] & 0x80, 30)
                assert text(gb, 2) == "GREEN LIGHT", gid
