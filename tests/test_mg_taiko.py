# docs/minigames_bosses.md 4.7: TAIKO POUR (src/tk.c), the teahouse's mini-game, on the framework (src/mg.c): the screen (the
# approved look B art, its palettes, the DMG registers), the chart and the clock (the tune's music_frames; the game's own count
# with MUSIC OFF, which most tests use for exact frames), the windows (PERFECT 3, GOOD 6, MISS to 10, a SPILL else), scoring,
# the bowl, the count-in, the beat flash, medals, the sprites per line over whole games, STORY / ARCADE reaching it in
# chapter 8, BONUS > MINI GAMES, what is put back when it is left.
#
# Harness notes: PyBoy's frame ends a few lines after the game's logic has begun, so a read at a frame's end may or may not
# have that frame's update in it and a held key is read by the update after the one in progress. Exact tests therefore read
# in a paused frame (`snap`) and set the game's own clock before the update that is to see a key (`press_at`); the bots, which
# play whole games, are at most a frame early (PERFECT is +-3).
import pytest
from conftest import ROOT, check_golden, hold_stage_anim, logic_paused
from test_flow import GS_GOAL, LEVEL_CLEAR, TITLE, run_until, state, tilemap_row
from test_mg import (GS_MGLIST, GS_MINI, MG_COUNT, MG_END, MG_PRACTICE, MG_RESULT, MG_STORY, RESULT_MIN, frames, mg_enter,
                     score, text, to_play, to_result, until)
from test_mg_list import release_built  # noqa: F401  (the fixture: `make release`)
from tk_helpers import (ART, CHART, LAYOUT, MG_TAIKO, STATE_SIZE, TEAHOUSE, TK_BG, TK_OBJ, glyph, perfect_score, plan_for,
                        poke, run_bot, tk, tk_define)

pytestmark = pytest.mark.timeout(300)

MEDAL_NONE, MEDAL_BRONZE, MEDAL_SILVER, MEDAL_GOLD = range(4)
SEED = 0x5A17
OUT = ROOT / "out" / "tk"
NOTES = len(CHART)
SPAWN, PERFECT, GOOD, REACH, DROP, BEAT, FLASH_LEN, FIRST = (tk_define(n) for n in (
    "TK_SPAWN", "TK_PERFECT", "TK_GOOD", "TK_REACH", "TK_DROP", "TK_BEAT", "TK_FLASH_LEN", "TK_FIRST"))
COUNT_AT, END_WAIT, POUR_LEN, SPILL_LEN, SERVE_LEN, OWN_START = (tk_define(n) for n in (
    "TK_COUNT_AT", "TK_END_WAIT", "TK_POUR_LEN", "TK_SPILL_LEN", "TK_SERVE_LEN", "TK_OWN_START"))
OAM_SPIG, OAM_POT, OAM_STREAM, OAM_STEAM, OAM_FLASH, OAM_DRUM, OAM_NOTES = (tk_define(n) for n in (
    "OAM_SPIG", "OAM_POT", "OAM_STREAM", "OAM_STEAM", "OAM_FLASH", "OAM_DRUM", "OAM_NOTES"))
TK_GOLD_PCT, TK_SILVER_PCT, TK_BRONZE_PCT = (tk_define(n) for n in ("TK_GOLD_PCT", "TK_SILVER_PCT", "TK_BRONZE_PCT"))
SFX_CATCH, SFX_BREAK, SFX_SERVE, SFX_COIN = 3, 4, 5, 6
SFX_DON, SFX_KA = 10, 11
BACKING = 0x70      # music.h TK_NOGROOVE | TK_NOHARM | TK_NOMELODY: the default sound balance (D3: the melody's own mute bit toggles with the half bars)
OFF = ART["off"]
OBJ = ART["obj_at"]
S_PALETTE = 0x10
LANE_Y = (48, 72)
BT_FILL, BT_FAIL, BT_TILES = 3, 4, 8            # Sal's PICTURES (bartender.txt: idle, walk1, walk2, fill, fail) and their OBJ tiles a frame


def taiko(model, mode=MG_PRACTICE, seed=SEED, music=False):
    """A booted rom on the title, then Taiko Pour in practice (or `mode`); MUSIC OFF (the game counts its own frames: exact)
    unless `music`."""
    from test_scores import booted
    rom = booted(model)
    hold_stage_anim(rom)
    if not music:
        rom.write("sound_on", 0)
    mg_enter(rom, MG_TAIKO, mode, seed)
    return rom


def shot(gb, name):
    OUT.mkdir(parents=True, exist_ok=True)
    gb.screenshot(OUT / f"{name}.{gb.model_name}.png", 4)


def oam(gb, i):
    a = 0xFE00 + 4 * i
    return dict(y=gb.mem(a), x=gb.mem(a + 1), tile=gb.mem(a + 2), prop=gb.mem(a + 3))


def tap(gb, key, n=2):
    gb.hold(key)
    frames(gb, n)
    gb.release(key)
    frames(gb, 1)


def snap(gb):
    """The state as of a whole update, read in a paused frame (the VBlank copy and the OAM DMA have caught up there too, so VRAM
    and OAM read right after are the state's)."""
    with logic_paused(gb):
        return tk(gb)


def at_clock(gb, c):
    """Between two updates with the game's own clock (MUSIC OFF) at c - 1, so that the next update has clock c: frames until
    the clock is within 4, then a poke of the last few (notes passed meanwhile are misses at that update, as they would be)."""
    for _ in range(4000):
        s = snap(gb)
        if s["own"] >= c - 4:
            break
        frames(gb, max(1, (c - 4 - s["own"]) // 2))
    assert s["own"] <= c - 1, (s["own"], c)
    with logic_paused(gb):
        a = gb.addr("story_scratch") + LAYOUT["own"][0]
        gb.write(a, (c - 1) & 0xFF)
        gb.write(a + 1, (c - 1) >> 8)


def press_at(gb, key, c):
    """`key` pressed so that the update with clock c reads it (MUSIC OFF): the clock is set, the key held for 2 frames (the one
    edge, however the frames cut the updates); returns the state after (its clk is c, c + 1 or c + 2)."""
    at_clock(gb, c)
    gb.hold(key)
    frames(gb, 2)
    gb.release(key)
    s = snap(gb)
    assert c <= s["clk"] <= c + 2, (s["clk"], c)
    return s


def to_clock(gb, c):
    """Frames until the state's clock reaches c (no keys; a frame or so of slack)."""
    for _ in range(4000):
        if tk(gb)["clk"] >= c:
            return
        frames(gb, 1)
    raise AssertionError("clock not reached")


def play_to(gb, c, plan=None, worst=None):
    """The bot plays until the clock reaches c."""
    step = (lambda g, n: frames(g, n, worst)) if worst is not None else frames
    return run_bot(gb, step, plan if plan is not None else plan_for(), lambda s: s["clk"] >= c)


def tile_bytes(gb, t):
    a = 0x9000 + t * 16 if t < 128 else 0x8000 + t * 16
    return list(gb.read(a, 16))


def bank1(gb, col, row):
    gb.pb.memory[0xFF4F] = 1
    try:
        return gb.pb.memory[0x9800 + row * 32 + col]
    finally:
        gb.pb.memory[0xFF4F] = 0


def map_row(gb, row):
    return tilemap_row(gb, row, 0, 20)


def note_x(t, c):
    d = t - c
    return 24 + d + (d >> 1)


def pot_tile(pour_t):
    """The pot's left entry for a `pour_t` (tilts at the ends of the pour, pours in the middle)."""
    if not pour_t:
        return TK_OBJ + OBJ["pot"][0]
    return TK_OBJ + OBJ["pot"][1 if pour_t > 13 or pour_t < 4 else 2]


# ---- the screen ------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_screen_and_its_art(model):
    """The intro: the banner, the HUD (the combo and cups icons), every row of the approved art as the generator laid it out, the
    tiles and palettes, the sprites (the Spigoteer, the pot, the drummer), the DMG registers."""
    with taiko(model) as gb:
        assert gb.mem("mg_id") == MG_TAIKO and gb.mem("mg_mode") == MG_PRACTICE and gb.mem("mg_phase") == 0
        frames(gb, 30)
        assert text(gb, 2) == "TAIKO POUR" and text(gb, 3) == "A TOP LANE B BOTTOM"
        assert tilemap_row(gb, 0, 10, 4) == [TK_BG + OFF["hud"], glyph("X"), glyph("0"), glyph("0")]
        assert tilemap_row(gb, 0, 16, 4) == [TK_BG + OFF["hud"] + 1, glyph("X"), glyph("0"), glyph("0")]
        s = tk(gb)
        assert (s["next"], s["judged"], s["combo"], s["cups"], s["cup_shown"]) == (0, 0, 0, 0, 0)
        # the art's tiles
        got = [b for t in range(TK_BG, TK_BG + ART["n_bg"]) for b in tile_bytes(gb, t)]
        assert got == ART["bg"], "BG tiles"
        got = [b for t in range(TK_OBJ, TK_OBJ + ART["n_obj"]) for b in gb.read(0x8000 + t * 16, 16)]
        assert got == ART["obj"], "OBJ tiles"
        # the window's rows 1 and 4 (the banner covers 2-3 until the first note nears), banks, lanes, marks, blind, bowl
        band = [TK_BG + OFF["band"] + i for i in ART["band_map"]]
        assert map_row(gb, 1) == band[0:20] and map_row(gb, 4) == band[60:80]
        rail, lane = TK_BG + OFF["rail"], TK_BG + OFF["lane"]
        for r in (5, 8, 11):
            assert map_row(gb, r) == [rail] * 20
        for r in (6, 9):
            assert map_row(gb, r)[4:] == [lane] * 16 and map_row(gb, r)[:2] == [lane] * 2
        for r in (7, 10):
            assert map_row(gb, r)[4:] == [lane + 1] * 16 and map_row(gb, r)[:2] == [lane + 1] * 2
        mark = TK_BG + OFF["mark"]
        assert tilemap_row(gb, 6, 2, 2) == [mark, mark + 1] and tilemap_row(gb, 7, 2, 2) == [mark + 2, mark + 3]
        assert tilemap_row(gb, 9, 2, 2) == [mark + 4, mark + 5] and tilemap_row(gb, 10, 2, 2) == [mark + 6, mark + 7]
        blind = TK_BG + OFF["blind"]
        assert map_row(gb, 12) == [blind] * 20 and map_row(gb, 13) == [blind + 1] * 20
        cup, cm = TK_BG + OFF["cup"], ART["cup_map"]
        assert tilemap_row(gb, 15, 13, 2) == [cup + cm[0], cup + cm[1]]
        assert tilemap_row(gb, 16, 13, 2) == [cup + cm[2], cup + cm[3]]
        # the sprites: no note yet; the pot, the drummer, the Spigoteer in the fill pose mirrored
        assert oam(gb, OAM_NOTES)["y"] == 0
        pot, drum, spig = oam(gb, OAM_POT), oam(gb, OAM_DRUM), oam(gb, OAM_SPIG)
        assert (pot["x"], pot["y"], pot["tile"]) == (94 + 8, 118 + 16, TK_OBJ + OBJ["pot"][0])
        assert oam(gb, OAM_POT + 1)["tile"] == TK_OBJ + OBJ["pot"][0] + 2
        assert (drum["x"], drum["y"]) == (16 + 8, 112 + 16)
        assert spig["prop"] & 0x20 and spig["tile"] == BT_FILL * BT_TILES
        if model == "cgb":
            assert pot["prop"] & 7 == 7 and drum["prop"] & 7 == 5 and spig["prop"] & 7 == 0
            assert bank1(gb, 3, 1) == 3 and bank1(gb, 3, 6) == 2 and bank1(gb, 3, 12) == 5 and bank1(gb, 13, 15) == 6
            assert bank1(gb, 10, 0) == 1, "the HUD's palette"
        else:
            assert pot["prop"] & S_PALETTE and drum["prop"] & S_PALETTE and not spig["prop"] & S_PALETTE
            assert gb.mem(0xFF49) == 0xE4 and gb.mem(0xFF48) == 0xD0


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_colours_are_the_approved_ones(model):
    """CGB: the lane, shoji and blind colours on the screen are the mock-up's (sampled from the proposal's CGB screen); DMG: the
    four greys only."""
    from PIL import Image
    with taiko(model) as gb:
        frames(gb, 30)
        OUT.mkdir(parents=True, exist_ok=True)
        gb.screenshot(OUT / f"colours.{model}.png", 1)
    px = Image.open(OUT / f"colours.{model}.png").convert("RGB")
    if model == "dmg":
        assert len({px.getpixel((x, y)) for x in range(160) for y in range(144)}) <= 4
        return
    near = lambda a, b: all(abs(x - y) <= 8 for x, y in zip(a, b))
    assert near(px.getpixel((100, 50)), (0xE0, 0xF0, 0xE8)), "the lane"
    assert near(px.getpixel((110, 33)), (0xF8, 0xF0, 0xE0)), "the shoji paper"
    assert near(px.getpixel((100, 100)), (0xE8, 0xF0, 0xB8)), "the blind"


# ---- the chart and the clock -----------------------------------------------------------------------------------------------
def test_the_chart_keeps_its_rules():
    """NORMAL (D6a): hit times on the tune's rows (12 frames) from bar 4 (FIRST 288); every note on a quarter-note row, no two
    notes (either lane) closer than 24 frames, no eighth pairs (so none of HARD's fast runs); at most 5 notes a lane in the 105
    frames a note lives on screen; the rounds: bars 1-8 the don only, both lanes from bar 9; clearly fewer notes than HARD's 112."""
    assert CHART[0][0] == FIRST == 288 and all((t - FIRST) % 24 == 0 for t, _ in CHART)
    assert [t for t, _ in CHART] == sorted(t for t, _ in CHART) and len({t for t, _ in CHART}) == NOTES
    assert min(b - a for (a, _), (b, _) in zip(CHART, CHART[1:])) >= 24
    for lane in (0, 1):
        ts = [t for t, ln in CHART if ln == lane]
        assert max(sum(1 for u in ts if t <= u < t + 105) for t in ts) <= 5
    assert all(ln == 0 for t, ln in CHART if t < FIRST + 8 * 96)
    assert any(ln == 1 for t, ln in CHART if FIRST + 8 * 96 <= t < FIRST + 16 * 96)
    assert 60 <= NOTES <= 80 and CHART[-1][0] - FIRST < 45 * 60


def test_the_hard_chart_is_kept_for_the_difficulty_table():
    """The first chart (112 notes, eighth pairs 12 frames apart) stays buildable: tools/taiko_chart.py GRIDS["hard"]."""
    import sys
    sys.path.insert(0, str(ROOT / "tools"))
    import taiko_chart
    hard = taiko_chart.build("hard")
    assert len(hard) == 112 and len(hard) > NOTES * 1.4 and taiko_chart.stats(hard)["gap0"] == 12


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_note_slides_1_5_px_a_frame_to_the_mark_and_is_dropped_at_x_under_6(model):
    """MUSIC OFF clock: a note appears at x 163 (93 frames ahead), moves 3 px every 2 frames, is at the mark's x 24 at its hit
    time; a note not pressed is a MISS at T + 11 and keeps sliding; at T + 12 it is at x 6 (shown), at T + 13 it is gone."""
    with taiko(model) as gb:
        to_play(gb)
        t0 = CHART[0][0]
        seen = {}
        for _ in range(240):
            frames(gb, 1)
            s = snap(gb)
            o = oam(gb, OAM_NOTES)
            if o["y"]:
                seen[s["clk"]] = (o["x"] - 8 + 4, o["y"] - 16, o["tile"], o["prop"])      # the note's centre x
        assert min(seen) == t0 - SPAWN, "spawned 93 frames ahead"
        for c, (cx, y, tile, prop) in seen.items():
            if c <= t0 + DROP:
                assert cx == note_x(t0, c) and y == LANE_Y[0] and tile == TK_OBJ + OBJ["don"], (c, cx)
                assert (prop & 7 == 1) if model == "cgb" else bool(prop & S_PALETTE)
        assert seen[t0 - SPAWN][0] == 163 and seen[t0][0] == 24 and seen[t0 + DROP][0] == 6, "the last frame shown: x 6"
        assert seen[t0 + DROP + 1][0] == note_x(CHART[1][0], t0 + DROP + 1), "gone at T + 13: the slot holds the next note"
        assert snap(gb)["miss"] >= 1


def test_a_lane_never_holds_more_than_5_notes_and_one_sliding_off():
    """The engine rule at work: with nothing pressed the live list never has more than 6 entries (5 and one dropped late)."""
    with taiko("cgb") as gb:
        to_play(gb)
        top = 0
        for _ in range(900):
            frames(gb, 1)
            top = max(top, sum(1 for i in tk(gb)["live"] if i != 255))
        assert 2 <= top <= 6, top


# ---- the windows -----------------------------------------------------------------------------------------------------------
WINDOWS = [0, 4, -4, 5, -5, 8, -8, 9, -9, 12, -9, 9, -12]     # (each press 3 or more frames after the last: a key needs a frame up)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_windows_perfect_4_good_8_miss_11_spill_beyond(model):
    """A press at the note's frame +-4 is PERFECT, +-5..8 GOOD, +-9..11 a MISS (the note spent, no -50), +12 is after the note
    (a miss by itself) and -12 before it: both a SPILL (-50). The score follows: 300 / 100 + 10 a note of the combo; a miss
    resets the combo."""
    with taiko(model) as gb:
        to_play(gb)
        for i, d in enumerate(WINDOWS):
            press_at(gb, "a", CHART[i][0] + d)
        s = press_at(gb, "a", CHART[len(WINDOWS) - 1][0] + 12)         # (a last press with no note within 11: a spill)
        assert (s["perfect"], s["good"], s["miss"], s["spills"]) == (3, 4, 4 + 2, 3)
        assert gb.mem16("mg_score") == 310 + 320 + 330 + 140 + 150 + 160 + 170 - 50 - 50 - 50
        assert s["combo"] == 0 and s["best"] == 7 and s["hits"] == 7 and s["cups"] == 0
        assert s["judged"] == len(WINDOWS)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_each_window_edge_in_isolation(model):
    """The edges one note at a time: the last frame of PERFECT / GOOD, the first of the next window, as the state's `last`
    (1 PERFECT, 2 GOOD, 3 MISS, 4 SPILL) says right after the press."""
    cases = [(4, 1), (5, 2), (8, 2), (9, 3), (11, 3), (-4, 1), (-5, 2), (-8, 2), (-9, 3), (-11, 3), (-12, 4)]
    with taiko(model) as gb:
        to_play(gb)
        for i, (d, want) in enumerate(cases):
            s = press_at(gb, "a", CHART[i][0] + d)
            assert s["last"] == want, (d, s["last"], want)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_press_judges_the_earliest_note_of_its_lane_and_the_other_lane_is_left(model):
    """A lane's presses count only its own notes: B at an A note's frame is a SPILL, the A note is then a MISS (not pressed by
    T + 10) and the next is pressed PERFECT; A at the first B note is a spill, the B note is still there for B."""
    with taiko(model) as gb:
        to_play(gb)
        t = CHART[0][0]
        s = press_at(gb, "b", t)
        assert s["spills"] == 1 and s["last"] == 4 and s["judged"] == 0
        to_clock(gb, t + 14)
        assert snap(gb)["miss"] == 1, "not pressed by t + 10: a MISS"
        assert press_at(gb, "a", CHART[1][0])["perfect"] == 1
        tb = next(t for t, ln in CHART if ln == 1)
        assert press_at(gb, "a", tb)["spills"] == 2
        s = press_at(gb, "b", tb + 5)
        assert s["good"] == 1 and s["last"] == 2


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_spills_cost_50_never_below_zero_and_reset_the_combo(model):
    """Mashing scores nothing: a spill at 0 points stays 0 (no wrap), after points it takes 50 off (the HUD's score too), the
    combo resets, the Spigoteer's fail pose and the puddle show, SFX_BREAK sounds."""
    with taiko(model) as gb:
        to_play(gb)
        s = press_at(gb, "b", 170)
        assert s["spills"] == 1 and gb.mem16("mg_score") == 0 and score(gb) == 0
        t = CHART[0][0]
        s = press_at(gb, "a", t)                    # the first note PERFECT: 310
        assert gb.mem16("mg_score") == 310 and score(gb) == 310 and s["combo"] == 1
        s = press_at(gb, "b", t + 30)               # a spill: 260, combo 0
        assert (s["spills"], s["combo"]) == (2, 0) and SPILL_LEN - 3 <= s["spill_t"] <= SPILL_LEN
        assert gb.mem16("mg_score") == 260 and score(gb) == 260
        assert tilemap_row(gb, 0, 0, 6) == [glyph(c) for c in "000260"]
        puddle = oam(gb, OAM_STEAM)
        assert puddle["y"] and puddle["x"] == 124 + 8 and puddle["tile"] in (TK_OBJ + OBJ["spill"][0], TK_OBJ + OBJ["spill"][1])
        assert oam(gb, OAM_SPIG)["tile"] == BT_FAIL * BT_TILES, "the fail pose"
        assert gb.mem("last_sfx") == SFX_BREAK
        frames(gb, SPILL_LEN)
        s = snap(gb)
        assert s["spill_t"] == 0 and oam(gb, OAM_STEAM)["y"] == 0 and oam(gb, OAM_SPIG)["tile"] == BT_FILL * BT_TILES


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_perfect_run_scores_the_spec_and_wins_gold(model):
    """Every note on its frame: the points of the rules (300 + 10 a combo note up to 100, 500 a bowl of 8), 14 bowls, GOLD, the
    result window; the sprites per line <= 10 on every frame, the worst line measured."""
    worst = [0]
    with taiko(model) as gb:
        to_play(gb)
        s = play_to(gb, CHART[-1][0] + 20, worst=worst)
        assert (s["perfect"], s["good"], s["miss"], s["spills"]) == (NOTES, 0, 0, 0)
        assert s["cups"] == NOTES // 8 and s["combo"] == NOTES and s["best"] == NOTES
        assert gb.mem16("mg_score") == perfect_score() == score(gb)
        assert tilemap_row(gb, 0, 18, 2) == [glyph(c) for c in f"{NOTES // 8:02d}"]
        assert tilemap_row(gb, 0, 12, 2) == [glyph(c) for c in f"{min(NOTES, 99):02d}"]
        until(gb, lambda: gb.mem("mg_phase") == MG_END, END_WAIT + 10)
        until(gb, lambda: gb.mem("overlay_on") == 1, 100)
        frames(gb, 3)
        assert gb.mem("mg_medal") == MEDAL_GOLD
        assert text(gb, 2, True, x0=4) == "SCORE " + str(perfect_score()) and text(gb, 3, True, x0=4) == "GOLD 3000"
        assert score(gb) == perfect_score() + 3000
        shot(gb, "result")
        check_golden(gb, "tk_result")
    assert 5 <= worst[0] <= 9, worst


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_game_with_nothing_pressed_misses_everything_and_ends(model):
    """No keys: every note a MISS, no spill, no points, NO MEDAL; the game ends END_WAIT frames after the last one resolves;
    the sprites per line stay small (the notes slide off and are dropped)."""
    worst = [0]
    with taiko(model) as gb:
        to_play(gb)
        for _ in range(CHART[-1][0] + 60):
            frames(gb, 1, worst)
            if gb.mem("mg_phase") >= MG_END:
                break
        s = snap(gb)
        assert (s["perfect"], s["good"], s["miss"], s["spills"], s["judged"]) == (0, 0, NOTES, 0, NOTES)
        assert gb.mem16("mg_score") == 0 and s["clk"] >= CHART[-1][0] + 11 + END_WAIT - 3
        until(gb, lambda: gb.mem("overlay_on") == 1, 100)
        frames(gb, 3)
        assert gb.mem("mg_medal") == MEDAL_NONE and text(gb, 3, True, x0=4) == "NO MEDAL"
    assert worst[0] <= 8, worst


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_mashing_both_keys_keeps_to_10_sprites_a_line(model):
    """The worst scene we can force: A and B pressed every 3 frames through the densest bars (flashes in both lanes, the pot
    pouring, the spill and the Spigoteer's pose, the notes of both lanes): <= 10 a line on every frame."""
    worst = [0]
    with taiko(model) as gb:
        to_play(gb)
        to_clock(gb, CHART[0][0] + 16 * 96)
        for i in range(0, 700, 3):
            gb.hold("a" if i % 6 == 0 else "b")
            frames(gb, 1, worst)
            gb.release("a")
            gb.release("b")
            frames(gb, 2, worst)
    assert 6 <= worst[0] <= 10, worst


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_medal_edges_accuracy_90_70_50(model):
    """Accuracy = (PERFECT + GOOD / 2) / notes: in half notes a2 of 2 x NOTES: GOLD from 90%, SILVER from 70%, BRONZE from 50%
    (NORMAL, TK_*_PCT; derived from scripted bots, DESIGN.md); the result window names it and adds its points to the score."""
    need = [-(-2 * p * NOTES // 100) for p in (TK_GOLD_PCT, TK_SILVER_PCT, TK_BRONZE_PCT)]    # ceil
    g, sv, br = need
    with taiko(model) as gb:
        to_play(gb)
        for a2, medal in ((g - 1, MEDAL_SILVER), (g, MEDAL_GOLD), (sv, MEDAL_SILVER), (sv - 1, MEDAL_BRONZE),
                          (br, MEDAL_BRONZE), (br - 1, MEDAL_NONE)):
            poke(gb, perfect=a2 // 2, good=a2 % 2)
            gb.write("mg_phase", MG_RESULT)
            until(gb, lambda: gb.mem("overlay_on") == 1, 10)
            frames(gb, 2)
            assert gb.mem("mg_medal") == medal, (a2, gb.mem("mg_medal"))
            gb.press("a", 2)
            run_until(gb, lambda: gb.mem("mg_phase") == 0 and gb.pb.memory[0xFF40] & 0x80, 30)
            to_play(gb)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("name, offset, skip_mod, medal", [
    ("every note PERFECT: 100%", 0, 0, MEDAL_GOLD),
    ("every 4th note left, the rest PERFECT: 75%", 0, 4, MEDAL_SILVER),
    ("every 3rd note left, the rest PERFECT: 66%", 0, 3, MEDAL_BRONZE),
    ("every note GOOD (5-6 late): 50%", 6, 0, MEDAL_BRONZE),
    ("every 4th left, the rest GOOD: 37%", 6, 4, MEDAL_NONE)])
def test_scripted_players_earn_the_medals_of_the_design(model, name, offset, skip_mod, medal):
    """D6a: the thresholds (90 / 70 / 50 %) were derived from jittery bots (DESIGN.md); these deterministic ones pin the edges
    in the real game: all-GOOD is exactly 50% (BRONZE), a PERFECT player who leaves a quarter is 75% (SILVER)."""
    skip = {i for i in range(NOTES) if skip_mod and i % skip_mod == skip_mod - 1}
    with taiko(model) as gb:
        to_play(gb)
        s = play_to(gb, CHART[-1][0] + 20, plan_for(offset=offset, skip=skip))
        acc = (2 * s["perfect"] + s["good"]) / (2 * NOTES)
        until(gb, lambda: gb.mem("mg_phase") == MG_END, END_WAIT + 10)
        until(gb, lambda: gb.mem("overlay_on") == 1, 100)
        frames(gb, 3)
        assert gb.mem("mg_medal") == medal, (name, acc)


# ---- the bowl, the pour, the count-in, the beat ------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_eight_good_hits_serve_a_bowl_for_500(model):
    """The bowl fills a step every 2 hits (0, 1, 2, 3 of 4), the 8th note served: +500, the cups digit, the bowl full and
    steaming for SERVE_LEN frames, SFX_SERVE; GOOD counts as much as PERFECT."""
    with taiko(model) as gb:
        to_play(gb)
        cm, cup = ART["cup_map"], TK_BG + OFF["cup"]

        def bowl():
            return [tilemap_row(gb, 15, 13, 2), tilemap_row(gb, 16, 13, 2)]

        def want(st):
            return [[cup + cm[4 * st], cup + cm[4 * st + 1]], [cup + cm[4 * st + 2], cup + cm[4 * st + 3]]]

        plan = plan_for(offset=6)                  # every note GOOD (judged 5 or 6 frames late)
        assert bowl() == want(0)
        for k in range(1, 9):
            play_to(gb, CHART[k - 1][0] + 6 + 2, plan)
            s = snap(gb)
            if k < 8:
                assert (s["good"], s["hits"], s["cups"]) == (k, k, 0) and bowl() == want(k // 2), (k, s)
        assert (s["good"], s["hits"], s["cups"], s["serve_t"] > SERVE_LEN - 8) == (8, 0, 1, True)
        pts = sum(100 + 10 * min(c, 10) for c in range(1, 9)) + 500
        assert gb.mem16("mg_score") == pts and bowl() == want(4)
        assert tilemap_row(gb, 0, 18, 2) == [glyph("0"), glyph("1")] and gb.mem("last_sfx") == SFX_SERVE
        steam = oam(gb, OAM_STEAM)
        assert steam["y"] and steam["x"] == 108 + 8
        frames(gb, SERVE_LEN + 2)
        snap(gb)
        assert bowl() == want(0) and oam(gb, OAM_STEAM)["y"] == 0


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_hit_pours_flashes_and_sounds(model):
    """A PERFECT: the blossom at the mark of its lane, the pot tilts, pours (the stream), tilts back, SFX_DON (lane A); a GOOD on
    lane B: the ring, SFX_KA; the B lane's flash is at the lower mark."""
    with taiko(model) as gb:
        to_play(gb)
        t = CHART[0][0]
        s = press_at(gb, "a", t)
        k = s["clk"] - t
        assert s["last"] == 1 and s["flash_k"][0] == 0 and s["pour_t"] == POUR_LEN - 1 - k and s["flash_t"][0] == FLASH_LEN - 1 - k
        f = oam(gb, OAM_FLASH)
        assert (f["x"], f["y"], f["tile"]) == (16 + 8, 48 + 16, TK_OBJ + OBJ["flash_p"])
        assert oam(gb, OAM_FLASH + 1)["tile"] == TK_OBJ + OBJ["flash_p"] + 2 and oam(gb, OAM_FLASH + 2)["y"] == 0
        assert gb.mem("last_sfx") == SFX_DON
        pots, streams = [], []
        for _ in range(POUR_LEN + 2):                 # the pot: tilts, pours (the stream), tilts back, level again
            s = snap(gb)
            assert oam(gb, OAM_POT)["tile"] == pot_tile(s["pour_t"]), s["pour_t"]
            assert (oam(gb, OAM_FLASH)["y"] != 0) == (s["flash_t"][0] > 0)
            pots.append(oam(gb, OAM_POT)["tile"])
            st = oam(gb, OAM_STREAM)
            streams.append(bool(st["y"]))
            if st["y"]:
                assert st["x"] == 108 + 8 and st["tile"] in (TK_OBJ + OBJ["stream"][0], TK_OBJ + OBJ["stream"][1])
            frames(gb, 1)
        tilt, pour, level = (TK_OBJ + OBJ["pot"][i] for i in (1, 2, 0))
        assert pots[0] == tilt and pour in pots and pots[-1] == level and tilt in pots[pots.index(pour):]
        assert any(streams) and (pots.index(pour) == streams.index(True)) and not streams[-1] and not streams[0]
        tb = next(t for t, ln in CHART if ln == 1)
        s = press_at(gb, "b", tb + 5)
        assert s["last"] == 2 and s["flash_k"][1] == 1 and gb.mem("last_sfx") == SFX_KA
        f = oam(gb, OAM_FLASH + 2)
        assert (f["x"], f["y"], f["tile"]) == (16 + 8, 72 + 16, TK_OBJ + OBJ["flash_g"])


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_count_in_and_the_window_returning_to_the_banner_rows(model):
    """The banner rows show 1 2 3 4 on the beats at 192, 216, 240, 264; at 276 the shoji window's rows 2-3 (and on CGB their
    palette) are back, and the lantern then flickers (its 2x2 tiles swap)."""
    with taiko(model) as gb:
        to_play(gb)
        band = [TK_BG + OFF["band"] + i for i in ART["band_map"]]
        for k, c in enumerate((192, 216, 240, 264)):
            to_clock(gb, c + 3)
            assert text(gb, 2) == str(k + 1), (c, text(gb, 2))
        assert tk(gb)["band_on"] == 0
        to_clock(gb, 276 + 3)
        snap(gb)
        assert tk(gb)["band_on"] == 1 and map_row(gb, 2) == band[20:40]
        if model == "cgb":
            assert all(bank1(gb, c, 2) == 3 and bank1(gb, c, 3) == 3 for c in range(20))
        lant, lx = {}, ART["lantern"]["x"]
        for _ in range(100):
            frames(gb, 1)
            s = snap(gb)
            lant[s["lant_on"]] = lant.get(s["lant_on"], 0) + 1
            alt = ART["band_alt"][:2] if s["lant_on"] else [ART["band_map"][2 * 20 + lx + k] for k in range(2)]
            assert tilemap_row(gb, 3, lx, 2) == [TK_BG + OFF["band"] + a for a in alt]
        assert set(lant) == {0, 1}


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_banks_flash_on_each_beat(model):
    """The beat's flash: the banks' tile data is the lit tile for the first 8 frames of each 24, the dim one else (from the
    clock 0, so with the tune the flash is on its quarter notes)."""
    with taiko(model) as gb:
        to_play(gb)
        dim = ART["bg"][OFF["rail"] * 16:(OFF["rail"] + 1) * 16]
        lit = ART["bg"][(OFF["rail"] + 1) * 16:(OFF["rail"] + 2) * 16]
        assert dim != lit
        for _ in range(100):
            frames(gb, 1)
            c = snap(gb)["clk"]
            assert tile_bytes(gb, TK_BG + OFF["rail"]) == (lit if c % BEAT < FLASH_LEN else dim), (c, c % BEAT)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_drummer_dances_on_the_beat(model):
    """The drummer shows the show's dance steps on the first half of each beat, his rest pose between."""
    with taiko(model) as gb:
        to_play(gb)
        seen = {}
        for _ in range(80):
            frames(gb, 1)
            c = snap(gb)["clk"]
            seen.setdefault(c % BEAT < 12, set()).add(oam(gb, OAM_DRUM)["tile"])
        assert len(seen[False]) == 1 and len(seen[True]) >= 1 and seen[False].isdisjoint(seen[True])


# ---- sync with the tune ----------------------------------------------------------------------------------------------------
def test_with_music_the_clock_is_the_tunes_and_the_chart_loops_with_it():
    """The clock is music_frames: the tune restarted at entry (the same tune already playing is stopped first); the driver
    changes row on the tick that makes music_frames a multiple of 12 (so the update with clock 12 r is the first frame of row
    r's sound, and a note's hit time, a multiple of 12, is a row's first frame); 1344 frames later (the tune's loop, 14 bars)
    the driver is on the same row: the chart's bars 1-14 and 15-24 play over the tune's bars again. (A read at a frame's end
    can fall inside the music tick, between the driver and the counter: one frame of slack on both.)"""
    with taiko("cgb", music=True) as gb:
        assert gb.mem("sound_on") == 1
        to_play(gb)
        seen = {}
        for _ in range(760):                         # (a frame and a paused frame each: the music runs through both)
            frames(gb, 1)
            with logic_paused(gb):
                s = tk(gb)
                mf, row, tick = gb.mem16("music_frames"), gb.mem("hUGE_row"), gb.mem("hUGE_tick")
            assert (tick - mf) % 12 in (0, 1), (mf, tick)
            assert abs(s["clk"] - mf) <= 3, (s["clk"], mf)
            seen[mf] = row
        rows = {}                                    # the row of each 12-frame group, from the frames well inside it
        for mf, row in seen.items():
            if 2 <= mf % 12 <= 10:
                assert rows.setdefault(mf // 12, row) == row, (mf, row)
        groups = sorted(rows)
        assert len(groups) > 100 and all(b == a + 1 and (rows[b] == rows[a] + 1 or rows[b] == 0)    # (+1, or the order's end)
                                         for a, b in zip(groups, groups[1:]))
        both = [m for m in seen if m + 1344 in seen]
        assert len(both) > 50 and all(seen[m] == seen[m + 1344] for m in both)
        assert 1344 % 96 == 0 and FIRST % 12 == 0


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_lagging_frame_does_not_move_the_chart(model):
    """3 frames in which the game logic does not run while the music does (a forced lag): afterwards the clock is the
    music's again and the note is where the clock puts it (its position is computed from the clock, not stepped)."""
    with taiko(model, music=True) as gb:
        to_play(gb)
        to_clock(gb, 230)
        with logic_paused(gb):
            frames(gb, 3)
        frames(gb, 2)
        with logic_paused(gb):
            s = tk(gb)
            assert abs(s["clk"] - gb.mem16("music_frames")) <= 3
            o = oam(gb, OAM_NOTES)
            assert o["y"] and o["x"] - 8 + 4 == note_x(CHART[0][0], s["clk"])


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_with_music_a_bot_on_the_clock_hits_every_note(model):
    """The first 12 notes pressed on the music's clock: all PERFECT or GOOD (the bot is at most a frame early)."""
    with taiko(model, music=True) as gb:
        to_play(gb)
        play_to(gb, CHART[11][0] + 14)
        s = snap(gb)
        assert s["perfect"] + s["good"] == 12 and s["miss"] == 0 and s["spills"] == 0


# ---- flow: practice, story, arcade, the list, what is put back ---------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_practice_retry_and_menu(model):
    """Practice: A on the result retries (the score from 0, the counters zero), B comes back to the list."""
    with taiko(model) as gb:
        to_play(gb)
        play_to(gb, CHART[2][0] + 5)
        assert snap(gb)["perfect"] == 3
        to_result(gb)
        assert text(gb, 4, True, x0=4) == "A RETRY B MENU"
        gb.press("a", 2)
        run_until(gb, lambda: gb.mem("mg_phase") == 0 and gb.pb.memory[0xFF40] & 0x80, 30)
        s = tk(gb)
        assert state(gb) == GS_MINI and score(gb) == 0 and (s["perfect"], s["judged"], s["next"], s["combo"]) == (0, 0, 0, 0)
        assert text(gb, 2) == "TAIKO POUR"
        to_play(gb)
        to_result(gb)
        gb.press("b", 2)
        run_until(gb, lambda: state(gb) == GS_MGLIST and gb.pb.memory[0xFF40] & 0x80, 30)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_story_plays_it_in_chapter_8_and_the_last_call_has_everything_back(model):
    """Chapter 8 (the teahouse): after the Happy hour, Taiko Pour in MG_STORY (the score carried, the count not skippable,
    unlocked for Practice at once); the result's A CONTINUE leads to the Last call, whose VRAM and palettes are those of the
    Last call reached without it."""
    from test_bs import level_vram, palettes
    from test_story import to_goal, to_shift, win
    with to_shift(model, TEAHOUSE, 2) as gb:
        gb.run(2)
        fresh, pals = level_vram(gb), palettes(gb)
    with to_shift(model, TEAHOUSE, 1) as gb:
        assert gb.mem16("mg_unlocked") == 0
        win(gb, TEAHOUSE, 1)
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 20)
        run_until(gb, lambda: state(gb) == GS_MINI, 800)
        run_until(gb, lambda: gb.pb.memory[0xFF40] & 0x80, 10)
        assert gb.mem("mg_id") == MG_TAIKO and gb.mem("mg_mode") == MG_STORY and gb.mem("venue_id") == TEAHOUSE
        assert text(gb, 2) == "TAIKO POUR" and score(gb) > 0
        assert gb.mem16("mg_unlocked") == 1 << MG_TAIKO
        until(gb, lambda: gb.mem("mg_phase") == MG_COUNT, 100)
        frames(gb, 3)
        gb.press("a", 1)
        assert gb.mem("mg_phase") == MG_COUNT, "no skipping in the story"
        to_play(gb)
        frames(gb, 30)
        to_result(gb)
        assert text(gb, 4, True, x0=4) == "A CONTINUE"
        until(gb, lambda: gb.mem("mg_t") >= RESULT_MIN, RESULT_MIN)
        assert gb.mem("hUGE_mute_mask") & BACKING == BACKING, "the groove and harmony are out, the melody thinned, behind the drums"
        gb.press("a", 2)
        run_until(gb, lambda: state(gb) == GS_GOAL, 60)
        gb.run(3)
        assert gb.mem("hUGE_mute_mask") & 0x72 == 0, "the Last call's tune has its melody, harmony and groove back (src/tk.c tk_leave)"
        assert gb.mem("story_chapter") == TEAHOUSE and gb.mem("story_shift") == 2 and gb.mem("story_step") == 3
        to_goal(gb)
        gb.run(2)
        assert level_vram(gb) == fresh
        assert palettes(gb) == pals


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_level_after_taiko_pour_has_everything_back(model):
    """Taiko Pour (hits, a spill) -> B to the list -> the title -> a level: the level's OBJ tiles, BG 77-255, OBP0 / OBP1 and every
    palette are byte for byte those of a level started from a fresh boot."""
    from conftest import title_level
    from test_bs import level_vram, palettes
    from test_flow import PLAYING
    from test_scores import booted
    with booted(model) as gb:
        hold_stage_anim(gb)
        title_level(gb)
        run_until(gb, lambda: state(gb) == PLAYING, 60)
        gb.run(2)
        fresh, pals = level_vram(gb), palettes(gb)
    with taiko(model) as gb:
        to_play(gb)
        play_to(gb, CHART[4][0] + 5)
        press_at(gb, "b", CHART[4][0] + 30)
        to_result(gb)
        gb.press("b", 2)
        run_until(gb, lambda: state(gb) == GS_MGLIST and gb.pb.memory[0xFF40] & 0x80, 30)
        gb.run(3)
        gb.press("b", 2)
        run_until(gb, lambda: state(gb) == TITLE and gb.pb.memory[0xFF40] & 0x80, 30)
        gb.run(10)
        gb.press("b", 2)
        gb.run(10)
        title_level(gb)
        run_until(gb, lambda: state(gb) == PLAYING, 60)
        gb.run(62)
        assert level_vram(gb) == fresh
        assert palettes(gb) == pals


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_arcade_plays_it_in_chapter_8(model):
    """ARCADE plays the story's steps: the teahouse's mini slot is Taiko Pour, in MG_STORY; reaching it unlocks it."""
    from test_arcade import start_arcade
    from test_story import to_goal, win
    with start_arcade(model) as gb:
        to_goal(gb)
        gb.write("story_chapter", TEAHOUSE)
        gb.write("story_step", 1)
        win(gb, 0, 0)
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 20)
        run_until(gb, lambda: state(gb) == GS_MINI, 800)
        run_until(gb, lambda: gb.pb.memory[0xFF40] & 0x80, 10)
        assert gb.mem("mg_id") == MG_TAIKO and gb.mem("mg_mode") == MG_STORY and gb.mem("venue_id") == TEAHOUSE
        assert gb.mem("save_lock") == 1 and gb.mem16("mg_unlocked") == 1 << MG_TAIKO
        assert text(gb, 2) == "TAIKO POUR"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_bonus_mini_games_lists_and_plays_it(model):
    """BONUS > MINI GAMES (the debug build: all unlocked): TAIKO POUR on the eighth line (chapter order), its details THE TEAHOUSE; A plays it in
    practice (score from 0); its result's B comes back to the list on it."""
    from test_mg_list import line, tap as list_tap, to_list
    from test_scores import booted
    with to_list(booted(model)) as gb:
        for _ in range(7):
            list_tap(gb, "down")
        assert gb.mem("ml_sel") == 7
        assert line(gb, 15).strip() == "NORMAL NO MEDAL YET"
        list_tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_MINI and gb.pb.memory[0xFF40] & 0x80, 30)
        assert gb.mem("mg_id") == MG_TAIKO and gb.mem("mg_mode") == MG_PRACTICE and score(gb) == 0
        assert text(gb, 2) == "TAIKO POUR"
        gb.write("mg_phase", MG_RESULT)
        run_until(gb, lambda: gb.mem("overlay_on") == 1, 10)
        frames(gb, 3)
        gb.press("b", 2)
        run_until(gb, lambda: state(gb) == GS_MGLIST and gb.pb.memory[0xFF40] & 0x80, 30)
        gb.run(3)
        assert gb.mem("ml_sel") == 7 and line(gb, 12).strip() == "TAIKO POUR"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_release_list_unlocks_it_when_reached(model, release_built):
    from test_mg_list import MG_PLANNED, line, pr_block, release_rom, tap as list_tap, to_list, with_block
    from test_scores import v7_image
    best = [0] * MG_PLANNED
    best[MG_TAIKO] = MEDAL_SILVER
    ram = with_block(v7_image(), pr_block(1 << MG_TAIKO, best))
    with release_rom(model, ram) as gb:
        to_list(gb)
        assert [line(gb, r).strip() for r in range(2, 13, 2)] == ["? ? ?"] * 6
        for _ in range(7):
            list_tap(gb, "down")
        assert line(gb, 12) == " TAIKO POUR   SILVER"
        assert line(gb, 15).strip() == "NORMAL BEST SILVER"
        list_tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_MINI, 30)
        assert gb.mem("mg_id") == MG_TAIKO and gb.mem("mg_mode") == MG_PRACTICE


def test_the_state_fits_the_union():
    from tk_helpers import mg_define
    assert STATE_SIZE <= 520 and LAYOUT["live"][1] == mg_define("TK_LIVE")


# ---- goldens ---------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_goldens(model):
    """The intro banner, a lane-B hit amid notes of both lanes, a served bowl, a spill, from a seeded game (MUSIC OFF: the
    frames are exact: each shot is taken a fixed number of frames after a press set at its clock)."""
    with taiko(model) as gb:
        frames(gb, 40)
        shot(gb, "intro")
        check_golden(gb, "tk_intro")
        to_play(gb)
        # a served bowl, steaming: the 8th note of round 1 (the bot plays)
        play_to(gb, CHART[7][0] + 6)
        s = snap(gb)
        assert s["cups"] == 1 and s["serve_t"] > SERVE_LEN - 12
        shot(gb, "cup")
        check_golden(gb, "tk_cup")
        # round 2's first B note, PERFECT: its blossom at the lower mark, the pot tilting, notes in both lanes
        tb = next(t for t, ln in CHART if ln == 1)
        play_to(gb, tb - 4)
        press_at(gb, "b", tb)
        s = snap(gb)
        assert s["last"] == 1 and s["flash_t"][1] > 0
        shot(gb, "play")
        check_golden(gb, "tk_play")
        # a spill: the Spigoteer's fail pose and the puddle, a few frames after
        c = snap(gb)["clk"] + 20
        press_at(gb, "b", c)
        frames(gb, 4)
        assert snap(gb)["spill_t"] > 0
        shot(gb, "spill")
        check_golden(gb, "tk_spill")
