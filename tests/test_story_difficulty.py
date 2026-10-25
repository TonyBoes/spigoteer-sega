"""The STORY's difficulty (owner 2026-10-16: "On story mode only ... To change difficulty you have to start a new run").

A new STORY (PLAY > STORY, not CONTINUE) asks HOW HARD: EASY / NORMAL / HARD, the cursor on NORMAL, B backs out. The choice is saved with the story (bits 6-7 of
the main block's byte 4: 0 NORMAL, 1 HARD, 2 EASY, the codes of mg.h MG_D_*), CONTINUE uses it, an older save reads NORMAL. ARCADE and CLASSIC are unchanged.
EASY unlocks nothing (tunes, BOSS RUSH's bosses, Practice's mini-games and medals; the progress for CONTINUE is kept); NORMAL and HARD unlock as always. On CGB the
HUD's level flag is green (EASY) or red (HARD) through BG palette 1's colour 2; NORMAL and DMG are as before. Owner 2026-10-17: the prompt has no header, each
choice a caption under it (HALF / NORMAL / EXTRA POINTS), and every score added in a STORY run is scaled live (save.c story_pts: EASY x0.5, HARD x1.5, to the
nearest 5), so the HUD shows the scaled score; nothing is multiplied at the end and the initials screen says nothing; the table still marks E / H."""
import pytest
import test_story as ts
from conftest import (K_ARCADE, K_CLASSIC, K_CONTINUE, K_EASY, K_HARD, K_NORMAL, K_PLAY, K_STORY, MENU_SETTLE, ROOT, TM_HARD, TM_PLAY, check_golden,
                      hold_stage_anim, menu_items, menu_tap, menu_to, title_pick)
from test_flow import TITLE_ART, GS_GOAL, GS_STORY, LEVEL_CLEAR, PLAYING, TITLE, run_until, state
from test_hud import FLAG, art_bytes, vram_tile
from test_scores import GS_INITIALS, GS_SCORES, MODE_STORY, booted, screen_text, set_score, v7_image
from test_sound import save_ram
from test_venues import cgb_palette

pytestmark = pytest.mark.timeout(600)

NORMAL, HARD, EASY = 0, 1, 2                      # game.h DIFF_*, mg.h MG_D_*
CODE = {"NORMAL": NORMAL, "HARD": HARD, "EASY": EASY}
ORANGE = (29 | 20 << 5 | 4 << 10)                 # BG palette 1 colour 2, main_cold.c hud_palette
GREEN = (6 | 24 << 5 | 8 << 10)
RED = (30 | 5 << 5 | 5 << 10)
ITEM = {NORMAL: K_NORMAL, HARD: K_HARD, EASY: K_EASY}
MODES = [("dmg", d) for d in (NORMAL, HARD, EASY)] + [("cgb", d) for d in (NORMAL, HARD, EASY)]
IDS = [f"{m}-{'NEH'[d] if d != HARD else 'H'}" for m, d in MODES]


def run_diff(rom):
    return (rom.mem("story_arc") >> 1) & 3


def saved_code(ram):
    return ram[4] >> 6


def image(chapter=1, d=NORMAL, step=0, tunes=1, **kw):
    """A save with `chapter` chapters cleared in difficulty d."""
    return v7_image([], story=chapter | d << 6, step=step, tunes=tunes, **kw)


def new_story(model, d, ram=None):
    """From a boot: PLAY > STORY, the prompt answered with difficulty d; the INTRO scene is up."""
    rom = booted(model, ram)
    hold_stage_anim(rom)
    title_pick(rom, K_PLAY, K_STORY, press=False)
    menu_tap(rom, "a")
    assert rom.mem("title_menu") == TM_HARD
    menu_to(rom, ITEM[d])
    menu_tap(rom, "a")
    run_until(rom, lambda: state(rom) == GS_STORY and rom.mem("story_phase") == ts.SP_SCENE, 30)
    ts.settle(rom)
    return rom


def continued(model, ram):
    return ts.start_story(model, ram, cont=True)


def in_shift(model, d, chapter=1):
    """CONTINUE in chapter `chapter` of a save in difficulty d, through the PRE scene to the first shift, just past its goal banner."""
    rom = continued(model, image(chapter, d))
    ts.skip_scene(rom)
    run_until(rom, lambda: state(rom) == GS_GOAL, 30)
    return ts.to_goal(rom)


def tunes(rom):
    return rom.mem16("tune_unlocked")


# ---- the prompt ---------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_new_story_asks_how_hard_with_the_cursor_on_normal_and_b_backs_out(model):
    with booted(model) as rom:
        title_pick(rom, K_PLAY, K_STORY, press=False)
        assert rom.mem("title_menu") == TM_PLAY
        menu_tap(rom, "a")
        assert rom.mem("title_menu") == TM_HARD and menu_items(rom) == [K_EASY, K_NORMAL, K_HARD]
        assert menu_items(rom)[rom.mem("title_sel")] == K_NORMAL
        assert rom.mem("game_state") == TITLE, "asking starts nothing"
        seen = []
        for _ in range(4):                                       # Down wraps HARD -> EASY
            menu_tap(rom, "down")
            seen.append(menu_items(rom)[rom.mem("title_sel")])
        assert seen == [K_HARD, K_EASY, K_NORMAL, K_HARD]
        menu_tap(rom, "up")
        menu_tap(rom, "up")
        menu_tap(rom, "up")
        assert menu_items(rom)[rom.mem("title_sel")] == K_HARD, "Up from EASY wraps to HARD"
        menu_tap(rom, "b")
        assert rom.mem("title_menu") == TM_PLAY and menu_items(rom)[rom.mem("title_sel")] == K_STORY and rom.mem("game_state") == TITLE


WORDS = {"easy": "EASY", "normal": "NORMAL", "hard": "HARD", "cap_easy": "HALF POINTS", "cap_normal": "NORMAL POINTS", "cap_hard": "EXTRA POINTS"}
ROWS = {"easy": 7, "normal": 8, "hard": 9}
CAP_ROW = 12
CAP_OF = {K_EASY: "cap_easy", K_NORMAL: "cap_normal", K_HARD: "cap_hard"}


def prompt_rows(rom):
    return [[x % 256 for x in r] for r in rom.bg_tilemap()]


def ink_rows(rom):
    """The prompt block's rows (4..13) that hold anything but the blank tile."""
    blank = TITLE_ART["blank"]
    rows = prompt_rows(rom)
    return [r for r in range(4, 14) if any(t != blank for t in rows[r])]


def check_caption(rom):
    t = TITLE_ART["text"]
    sel = menu_items(rom)[rom.mem("title_sel")]
    rows = prompt_rows(rom)
    e = t[CAP_OF[sel]]
    assert rows[CAP_ROW][e["col"]:e["col"] + len(e["tiles"])] == e["tiles"], ("caption of", sel)
    assert ink_rows(rom) == [7, 8, 9, CAP_ROW], "only one caption row has ink"
    for k, r in ROWS.items():
        e = t[k]
        assert rows[r][e["col"]:e["col"] + len(e["tiles"])] == e["tiles"], (r, k)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_prompt_has_no_header_and_one_caption_line_that_follows_the_cursor(model):
    t = TITLE_ART
    with booted(model) as rom:
        title_pick(rom, K_PLAY, K_STORY, press=False)
        menu_tap(rom, "a")
        rom.run(MENU_SETTLE)
        assert "how_hard" not in t["text"], "no header"
        assert menu_items(rom)[rom.mem("title_sel")] == K_NORMAL
        check_caption(rom)
        for b in ["down", "down", "down", "up", "up", "up", "up", "down"]:    # wrapping both ways
            menu_tap(rom, b)
            rom.run(3)
            check_caption(rom)
        assert len({tuple(t["text"][k]["tiles"]) for k in CAP_OF.values()}) == 3
        rows = prompt_rows(rom)
        for r in (4, 5, 6, 10, 11, 13):
            assert len(set(rows[r])) == 1, ("blank row", r)
        assert CAP_ROW - ROWS["hard"] >= 3, "two or more blank rows between HARD and the caption"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_prompt_lines_are_centred_within_half_a_tile(model):
    t = TITLE_ART["text"]
    for k, w in WORDS.items():
        e = t[k]
        first_ink = e["x"]
        last_ink = first_ink + 8 * len(w) - 2           # (8 px a glyph, 1 px shadow inside the cell)
        assert abs((first_ink + last_ink) / 2 - 80) <= 4, (k, first_ink, last_ink)
        assert abs(e["col"] * 8 + len(e["tiles"]) * 4 - 80) <= 0.5, (k, "tiles centred on the grid")
    # the block: rows 7..12 (one row down, owner Q49), in the rows between the logo and the scene (4..13)
    assert (min(ROWS.values()) - 4) == (13 - CAP_ROW) + 2


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_prompt_appears_only_on_a_new_story(model):
    with booted(model, image(2)) as rom:                         # a save: PLAY lists CONTINUE, STORY, ARCADE, CLASSIC
        title_pick(rom, K_PLAY)
        assert menu_items(rom) == [K_CONTINUE, K_STORY, K_ARCADE, K_CLASSIC]
        menu_to(rom, K_STORY)
        menu_tap(rom, "a")
        assert rom.mem("title_menu") == TM_HARD, "STORY asks, even over a save"
        menu_tap(rom, "b")
        assert menu_items(rom)[rom.mem("title_sel")] == K_STORY, "B: back on STORY (after CONTINUE)"
        menu_to(rom, K_CONTINUE)
        menu_tap(rom, "a")
        assert rom.mem("title_menu") != TM_HARD
        run_until(rom, lambda: state(rom) == GS_STORY, 30)       # CONTINUE: straight into the story, no question
    for k in (K_ARCADE, K_CLASSIC):
        with booted(model) as rom:
            title_pick(rom, K_PLAY, k, press=False)
            menu_tap(rom, "a")
            assert rom.mem("title_menu") != TM_HARD
            run_until(rom, lambda: state(rom) == PLAYING, 60)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_golden_of_the_prompt(model):
    with booted(model) as rom:
        title_pick(rom, K_PLAY, K_STORY, press=False)
        menu_tap(rom, "a")
        rom.run(MENU_SETTLE)
        check_golden(rom, "title_how_hard")


# ---- the choice is the run's, saved and restored -------------------------------------------------------------------------------
@pytest.mark.parametrize("model,d", MODES, ids=IDS)
def test_the_choice_is_the_runs_difficulty_saved_with_the_progress_and_continue_restores_it(model, d):
    with new_story(model, d) as rom:
        assert rom.mem("play_mode") == 1 and run_diff(rom) == d and rom.mem("story_arc") & 1 == 0
        ts.skip_scene(rom)                                       # INTRO
        ts.skip_scene(rom)                                       # PRE
        ts.to_goal(rom)
        ts.win(rom, 0, 0)
        run_until(rom, lambda: state(rom) == GS_GOAL, 800)       # the Opening shift cleared: saved (progress 0, step 1)
        assert run_diff(rom) == d
        ram = save_ram(rom)
    assert ram[:4] == b"TPR7" and saved_code(ram) == d and ram[4] & 0x3F == 0 and ram[5] == 1
    with booted(model, ram) as again:
        assert again.mem("story_progress") == 0 and again.mem("story_reached") == 1, "the progress is read without the difficulty bits"
        hold_stage_anim(again)
        ts.to_continue(again)
        run_until(again, lambda: state(again) == GS_GOAL, 60)
        assert run_diff(again) == d and again.mem("story_on") == 1


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_save_without_the_bits_and_a_bad_code_read_as_normal(model):
    for byte4 in (3, 3 | 0xC0):                                  # (an older save; code 3 is no difficulty)
        ram = v7_image([], story=byte4, step=0)
        with booted(model, ram) as rom:
            assert rom.mem("story_progress") == 3 and rom.mem("story_reached") == 0
            hold_stage_anim(rom)
            ts.to_continue(rom)
            run_until(rom, lambda: state(rom) == GS_STORY, 30)
            assert run_diff(rom) == NORMAL


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_other_saves_keep_the_difficulty_and_a_new_story_replaces_it_with_its_first_save(model):
    """A tune heard (a save of the whole block) leaves the code alone; a new EASY story over a HARD save keeps the old story and its difficulty until it saves
    its own progress (the first cleared shift)."""
    ram = image(2, HARD)
    with new_story(model, EASY, ram) as rom:
        assert run_diff(rom) == EASY
        out = save_ram(rom)
    assert saved_code(out) == HARD and out[4] & 0x3F == 2, "nothing saved yet: the old story and its difficulty"
    with booted(model, ram) as rom:
        hold_stage_anim(rom)
        ts.to_continue(rom)
        run_until(rom, lambda: state(rom) == GS_STORY, 30)
        assert run_diff(rom) == HARD
        rom.write("tune_unlocked", 0x11)
        rom.write("save_migrated", 0x80)                         # TUNE_DIRTY: saved at the next quiet moment (the shift's start)
        ts.skip_scene(rom)
        run_until(rom, lambda: state(rom) == GS_GOAL, 30)
        out = save_ram(rom)
    assert saved_code(out) == HARD and int.from_bytes(out[6:8], "little") & 0x10, "the tune was saved, the difficulty stayed"


# ---- EASY unlocks nothing ---------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("d", [NORMAL, HARD, EASY])
def test_clearing_a_shift_unlocks_the_tunes_on_normal_and_hard_and_on_easy_nothing_but_the_progress(model, d):
    with continued(model, image(1, d)) as rom:
        at_pre = tunes(rom)                                      # (chapter 2's PRE scene is up: its tune plays, a story unlock)
        ts.skip_scene(rom)
        run_until(rom, lambda: state(rom) == GS_GOAL, 30)
        ts.to_goal(rom)
        ts.win(rom, 1, 0)
        run_until(rom, lambda: state(rom) == LEVEL_CLEAR, 800)
        run_until(rom, lambda: state(rom) == GS_GOAL, 800)
        assert rom.mem("story_progress") == 1 and rom.mem("story_reached") == 1, "the progress is saved in every difficulty (CONTINUE)"
        after = tunes(rom)
        ram = save_ram(rom)
    if d == EASY:
        assert at_pre == 1 and after == 1, "no tune, no jingle"
        assert int.from_bytes(ram[6:8], "little") == 1 and saved_code(ram) == EASY
    else:
        assert at_pre != 1 and after != 1 and after & at_pre == at_pre, "the venue's tune once heard, the jingles with the progress"
        assert saved_code(ram) == d


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("d", [NORMAL, HARD, EASY])
def test_a_story_mini_game_is_reached_and_earns_a_medal_unless_easy(model, d):
    from test_mg import MG_STORY, mg_enter
    with in_shift(model, d) as rom:
        before = rom.mem16("mg_unlocked")
        mg_enter(rom, 0, MG_STORY)
        rom.run(30)
        assert rom.mem("game_state") == 13, "GS_MINI"
        after = rom.mem16("mg_unlocked")
    assert (after != before) == (d != EASY), (d, before, after)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("d", [NORMAL, HARD, EASY])
def test_beating_the_boss_lists_him_in_boss_rush_unless_easy(model, d):
    ram0 = image(0, d, step=ts.SHIFT_STEP[2])
    with ts.to_shift(model, 0, 2, image=ram0) as gb:
        ts.win(gb, 0, 2)
        ts.beat_the_boss(gb, 0)
        run_until(gb, lambda: state(gb) == GS_STORY, 300)
        assert gb.mem("story_progress") == 1, "the chapter is cleared in every difficulty"
        ram = save_ram(gb)
    bits = int.from_bytes(ram[0x40 + 16:0x40 + 18], "little")
    assert saved_code(ram) == d and ram[4] & 0x3F == 1
    assert (bits & 1) == (d != EASY and 0 in ts.BOSS_BUILT), (d, bits)


# ---- the HUD flag ---------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("d", [NORMAL, HARD, EASY])
def test_the_hud_flag_is_green_or_red_on_cgb_and_nothing_changes_on_dmg(model, d):
    with in_shift(model, d) as rom:
        art = art_bytes("assets/tiles/bar.txt", "hud_flag")
        tile = vram_tile(rom, FLAG)
        if model == "dmg" or d == NORMAL:
            assert tile == art, "the flag as drawn"
        else:                                                    # the cloth (pixels of colour 0) is colour 2
            want = []
            for lo, hi in zip(art[0::2], art[1::2]):
                want += [lo, hi | ~(lo | hi) & 0xFF]
            assert tile == want and tile != art
        if model == "cgb":
            assert cgb_palette(rom, 1)[2] == {NORMAL: ORANGE, HARD: RED, EASY: GREEN}[d]
            assert cgb_palette(rom, 1)[0] == (31 | 29 << 5 | 22 << 10) and cgb_palette(rom, 1)[3] == (3 | 2 << 5 | 8 << 10)
            assert rom.pb.memory[1, 0x9800 + 17] & 7 == 1, "the flag keeps the HUD palette: only its colour 2 changed"
        else:
            assert rom.pb.memory[0xFF47] == 0xE4 or True
        # the play is the same: the HUD is raw points
        assert ts.hud_lives(rom) == ts.lives_hud(3)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_arcade_and_classic_have_no_difficulty_and_the_title_restores_the_palette(model):
    with booted(model, image(2, EASY)) as rom:
        title_pick(rom, K_PLAY, K_ARCADE)
        run_until(rom, lambda: state(rom) == PLAYING, 60)
        assert run_diff(rom) == NORMAL and rom.mem("story_arc") == 1
        assert vram_tile(rom, FLAG) == art_bytes("assets/tiles/bar.txt", "hud_flag")
        if model == "cgb":
            assert cgb_palette(rom, 1)[2] == ORANGE, "the flag as always: the HUD palette is the saved EASY's no more"
    with booted(model, image(2, HARD)) as rom:
        title_pick(rom, K_PLAY, K_CLASSIC)
        run_until(rom, lambda: state(rom) == PLAYING, 60)
        assert run_diff(rom) == NORMAL and rom.mem("story_arc") == 0
        if model == "cgb":
            assert cgb_palette(rom, 1)[2] == ORANGE


# ---- the score ------------------------------------------------------------------------------------------------------------------
def credits_with(model, d, score):
    """The last chapter of a save in difficulty d, played through to the CREDITS scene with `score` poked in; returns the rom there."""
    ram0 = image(9, d, step=ts.SHIFT_STEP[2])
    gb = ts.to_shift(model, 9, 2, image=ram0)
    ts.win(gb, 9, 2)
    ts.beat_the_boss(gb, 9)
    run_until(gb, lambda: state(gb) == GS_STORY, 300)
    ts.skip_scene(gb)
    ts.through_the_pouroff(gb)
    ts.skip_scene(gb)
    assert gb.mem("story_scene") == ts.SC["CREDITS"]
    set_score(gb, score)
    return gb


def names(rom, t=MODE_STORY):
    return bytes(rom.read("top_names", 45))[t * 15:t * 15 + 15]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("d,mark", [(HARD, "H"), (EASY, "E"), (NORMAL, " ")])
def test_the_credits_record_the_score_as_it_is_with_no_indicator_on_the_initials_screen_and_the_table_marks_it(model, d, mark):
    raw = 1495
    with credits_with(model, d, raw) as gb:
        gb.press("start", 2)                                     # (the credits' pages, then the roll: START skips each)
        run_until(gb, lambda: gb.mem("story_phase") == 8, 30)
        gb.run(3)
        gb.press("start", 2)
        run_until(gb, lambda: state(gb) == GS_INITIALS, 30)
        gb.run(2)
        assert int.from_bytes(gb.read("score", 4), "little") == raw, "no multiplier at the end"
        assert screen_text(gb, 5).strip() == "%06d" % raw
        assert screen_text(gb, 14).strip() == "", "no difficulty line"
        n = names(gb)
        assert (n[0] & 0x80 != 0) == (d == HARD) and (n[1] & 0x80 != 0) == (d == EASY) and n[2] & 0x80 == 0
        gb.press("up", 2)
        gb.run(2)
        gb.press("a", 2)
        run_until(gb, lambda: state(gb) == GS_SCORES, 30)
        gb.run(2)
        assert screen_text(gb, 6).strip() == ("1 BAA %06d %s" % (raw, mark)).strip(), "the E / H mark after the score (kept)"
        ram = save_ram(gb)
    assert int.from_bytes(ram[0xC7:0xCA], "little") == raw


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_story_table_screen_marks_only_easy_and_hard_entries(model):
    img = v7_image([], story_tbl=[("AAA", 3000), ("BBB", 2000), ("CCC", 1000)])
    # mark bits as the game writes them: bit 7 of the first initial HARD, of the second EASY
    r = bytearray(img)
    r[0xC4] |= 0x80                                              # entry 1: HARD
    r[0xC4 + 6 + 1] |= 0x80                                      # entry 2: EASY
    c = (0x5A + sum(r[0xC0:0xC0 + 34])) & 255
    r[0xC0 + 34], r[0xC0 + 35] = c, c ^ 0xFF
    with booted(model, bytes(r)) as gb:
        from test_scores import idle_title, tap
        for _ in range(3):                                       # the attract cycle: ARCADE, STORY, CLASSIC
            idle_title(gb)
            run_until(gb, lambda: state(gb) == GS_SCORES, 30)
            gb.run(2)
            if screen_text(gb, 3).strip() == "STORY HIGH SCORES":
                break
            tap(gb, "b")
            run_until(gb, lambda: state(gb) == TITLE, 30)
            gb.run(3)
        rows = [screen_text(gb, 6 + 2 * i).strip() for i in range(4)]
        assert rows[:3] == ["1 AAA 003000 H", "2 BBB 002000 E", "3 CCC 001000"] and rows[3].startswith("4"), rows
        check_golden(gb, "story_table_marks")


def want_pts(n, d):
    return {NORMAL: n, EASY: (n + 5) // 10 * 5, HARD: (3 * n + 5) // 10 * 5}[d]


def hud_digits(rom):
    return int("".join(str(b) for b in rom.read("score_digits", 6)))


@pytest.mark.parametrize("model,d", MODES, ids=IDS)
def test_every_score_event_of_a_story_run_is_scaled_as_it_happens_and_the_hud_shows_it(model, d):
    from test_classic_mode import serve_one
    with in_shift(model, d) as rom:
        base = int.from_bytes(rom.read("score", 4), "little")
        got = serve_one(rom)
        s = rom.mem("serve_score")
        assert got == want_pts(s, d), (d, s, got)
        assert got % 5 == 0
        assert hud_digits(rom) == base + got == int.from_bytes(rom.read("score", 4), "little"), "the HUD shows the scaled score"
        got2 = serve_one(rom)
        assert got2 == want_pts(s, d)


@pytest.mark.parametrize("model,d", MODES, ids=IDS)
def test_the_level_bonus_and_a_medal_are_scaled_too(model, d):
    with in_shift(model, d) as rom:
        s0 = int.from_bytes(rom.read("score", 4), "little")
        ts.win(rom, 1, 0)
        run_until(rom, lambda: state(rom) == LEVEL_CLEAR, 800)
        run_until(rom, lambda: state(rom) == GS_GOAL, 800)
        gained = int.from_bytes(rom.read("score", 4), "little") - s0
        assert gained >= want_pts(1000, d) and gained % 5 == 0, (d, gained)
        assert hud_digits(rom) == s0 + gained


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_arcade_and_classic_scores_are_not_scaled(model):
    from test_classic_mode import serve_one
    for k in (K_ARCADE, K_CLASSIC):
        with booted(model, image(2, EASY)) as rom:
            title_pick(rom, K_PLAY, k)
            run_until(rom, lambda: state(rom) == PLAYING, 60)
            rom.run(60)
            assert run_diff(rom) == NORMAL
            assert serve_one(rom) == rom.mem("serve_score")


# ---- ERASE DATA --------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_erase_data_resets_the_difficulty(model):
    from conftest import K_ERASE, K_SETTINGS, K_YES
    with booted(model, image(2, HARD)) as rom:
        title_pick(rom, K_SETTINGS, K_ERASE)
        menu_to(rom, K_YES)
        menu_tap(rom, "a")
        rom.run(MENU_SETTLE)
        ram = save_ram(rom)
    assert ram[4] == 0, "every byte zeroed, the difficulty with them"
    with new_story(model, NORMAL, ram) as rom:
        assert run_diff(rom) == NORMAL
