# The debug menu (src/debug.c; owner 2026-10-16): a full-screen menu opened by holding SELECT and tapping START three times quickly (title,
# play, a level's pause; not a mini-game's), or SETTINGS > DEBUG MENU. It ships in every build but is LOCKED until its flag is saved (SRAM
# "DU", 0x18): the Konami code on the title unlocks it. Left/Right change the line's value, Up/Down move the cursor, A or START starts, B closes.
import subprocess

import pytest
from conftest import (clear_regulars, debug_unlocked, du_block, gesture, K_ARCADE, K_BARCHANGE, K_BONUS, K_CLASSIC, K_CONTINUE, K_DEBUG, K_ERASE, K_MUSIC, K_PLAY,
                      K_SETTINGS, K_SOUNDTRACK, K_STORY, KONAMI, MENU_SETTLE, ROOT, TM_PLAY, TM_SETTINGS, TM_TOP, konami, menu_items, menu_tap, menu_to,
                      release_gesture, title_arcade, title_level, title_pick, unlock_debug, with_unlock)

pytestmark = pytest.mark.timeout(120)

TITLE, PLAYING, PAUSED, DEBUG = 0, 1, 5, 7
MODE_ARCADE, MODE_STORY, MODE_CLASSIC, MODE_LEVEL = range(4)   # src/game.h play_mode
WINDOW = 72             # src/debug.c DBG_WINDOW: frames from the first START tap to the third
SAVE_LOCK_DEBUG = 2     # save.c save_lock: a debug-select run (ARCADE alone is 1: it still records the mini-games reached)
SFX_EXTRA = 9


def combo(gb):
    """The opening gesture (the menu unlocked first, as a player who has the code would have it)."""
    unlock_debug(gb)
    gesture(gb)


def release_combo(gb):
    release_gesture(gb)


# ---- the screen: the window map's rows (the menu is the window over the whole screen) ----
def win_row(gb, r):
    return [t & 0xFF for t in gb.bg_tilemap(True)[r][:20]]


def row_text(gb, r):
    """Window row r as text: the HUD letters and digits, the keys line's buttons as @ $ >."""
    from test_flow import tile_id
    from test_mg import GLYPH_CH
    blank = tile_id("HUD_BLANK")
    key = {gb_key: c for gb_key, c in zip(KEY_TILES(), "@$>")}
    return "".join(" " if t == blank else key.get(t, GLYPH_CH.get(t, "?")) for t in win_row(gb, r))


def KEY_TILES():
    from test_mg_list import BTN_A, BTN_B, BTN_R
    return [BTN_A, BTN_B, BTN_R]


def line(gb, r):
    """The (label, value) of the menu line on window row r."""
    t = row_text(gb, r)
    return t[1:11].strip(), t[12:].strip()


def banner_text(gb):
    return win_row(gb, 2)


def banner_is(gb, s):
    """The menu shows s: "LEVEL 03", "LEVEL 03 RRLL" (with the bars), "CLASSIC 01", "STORY 3 HAPPY", "ARCADE 1 OPEN" (mode, number or chapter, step)."""
    t = s.split()
    want = {2: ("MODE", t[0])}
    if t[0] in ("STORY", "ARCADE"):
        want[4] = ("CHAPTER", t[1])
        want[6] = ("STEP", t[2] if len(t) > 2 else "")
    else:
        want[4] = ("LEVEL", t[1])
        if len(t) > 2:
            want[6] = ("BARS", t[2])
    got = {r: line(gb, r) for r in want}
    return got == want


def tap(gb, b):
    gb.press(b, 2)
    gb.run(2)


def goto(gb, k):
    """The cursor on line k of the menu."""
    while gb.mem("debug_sel") != k:
        tap(gb, "down")


def chap(gb, d):
    """STORY / ARCADE: the chapter one step on (d > 0) or back."""
    goto(gb, 1)
    tap(gb, "right" if d > 0 else "left")


def pos(gb, d):
    """STORY / ARCADE: the position (PRE, the steps, POST) one step on or back."""
    goto(gb, 2)
    tap(gb, "right" if d > 0 else "left")


# ---- opening ----
def test_the_gesture_opens_the_menu_on_the_title(boot):
    combo(boot)
    assert boot.mem("debug_menu_open") == 1 and boot.mem("debug_level") == 1
    assert boot.mem("game_state") == DEBUG
    assert boot.mem("overlay_on") == 1
    release_combo(boot)
    assert boot.mem("debug_menu_open") == 1


def test_it_is_a_full_screen_menu(boot):
    """The window over the whole screen (WY 0, no LYC end), a header, the panel lines, a cursor sprite and nothing else, the keys line."""
    combo(boot)
    release_combo(boot)
    boot.run(3)
    r = boot.regs()
    assert r["WY"] == 0 and boot.mem(0xFF45) == 255
    assert row_text(boot, 0).strip() == "DEBUG MENU"
    from test_flow import tile_id
    assert win_row(boot, 1) == [0] * 20 and win_row(boot, 14) == [tile_id("PANEL_TOP")] * 20 and win_row(boot, 17) == [tile_id("PANEL_BOT")] * 20
    assert row_text(boot, 16).strip() == "@ GO $ BACK > EDIT"
    assert [line(boot, y) for y in (2, 4, 6, 8)] == [("MODE", "LEVEL"), ("LEVEL", "01"), ("BARS", "LLLL"), ("BAR CHANGE", "SNAP")]
    assert all(row_text(boot, y).strip() == "" for y in (3, 5, 7, 9, 10, 11, 12, 13))   # (the blank rows hold the wall's board seams, tile 0)
    ys = [boot.pb.memory[0xFE00 + 4 * i] for i in range(40)]
    assert sum(1 for y in ys if y) == 1, "the mug cursor only"
    assert boot.pb.memory[0xFE00] == (4 * 8 - 7 + 16) and boot.pb.memory[0xFE01] == 8


def test_a_short_start_still_starts_the_game_and_select_still_toggles_music(boot):
    s0 = boot.mem("sound_on")
    boot.press("select", 3)
    boot.run(5)
    assert boot.mem("sound_on") == 1 - s0 and boot.mem("debug_menu_open") == 0
    boot.press("select", 3)
    boot.run(1)
    title_level(boot)
    boot.run(20)
    assert boot.mem("game_state") == PLAYING and boot.mem("debug_menu_open") == 0


def test_two_taps_are_not_enough(boot):
    unlock_debug(boot)
    gesture(boot, taps=2)
    boot.run(20)
    assert boot.mem("debug_menu_open") == 0 and boot.mem("game_state") == TITLE
    release_combo(boot)


def test_taps_too_slow_do_not_open_and_a_quick_run_after_them_does(boot):
    unlock_debug(boot)
    gesture(boot, taps=3, gap=40)                         # the third tap comes 84 frames after the first: past the window
    boot.run(5)
    assert boot.mem("debug_menu_open") == 0 and boot.mem("game_state") == TITLE
    assert 2 * (2 + 40) > WINDOW
    for _ in range(2):                                    # (that tap started a new count: two quick ones more make three)
        boot.press("start", 2)
        boot.run(3)
    boot.run(4)                                           # (the menu comes up with the LCD off for a few frames)
    assert boot.mem("debug_menu_open") == 1
    release_combo(boot)


def test_three_quick_taps_open_it_at_the_window_s_edge(boot):
    unlock_debug(boot)
    gesture(boot, taps=3, gap=WINDOW // 2 - 6)            # about 60 frames from the first to the third
    assert boot.mem("debug_menu_open") == 1
    release_combo(boot)


def test_a_new_hold_of_select_starts_the_count_again(boot):
    unlock_debug(boot)
    gesture(boot, taps=2)
    release_combo(boot)
    gesture(boot, taps=1)                                 # (one tap in a new hold: the two before do not count)
    boot.run(3)
    assert boot.mem("debug_menu_open") == 0
    release_combo(boot)


def test_locked_the_gesture_does_nothing_and_start_still_works(boot):
    assert not debug_unlocked(boot)
    boot.hold("select")
    boot.run(2)
    for _ in range(3):
        boot.press("start", 2)
        boot.run(3)
    boot.run(10)
    assert boot.mem("debug_menu_open") == 0 and boot.mem("game_state") != DEBUG
    release_combo(boot)


def test_the_gesture_on_the_title_does_not_leave_the_music_toggled(boot):
    s0 = boot.mem("sound_on")
    combo(boot)
    assert boot.mem("debug_menu_open") == 1
    assert boot.mem("sound_on") == s0, "the SELECT that began the gesture toggled it, opening undid that"
    release_combo(boot)


def test_a_gesture_that_does_not_open_leaves_select_s_one_toggle(boot):
    s0 = boot.mem("sound_on")
    unlock_debug(boot)
    gesture(boot, taps=2)
    release_combo(boot)
    assert boot.mem("sound_on") == 1 - s0 and boot.mem("debug_menu_open") == 0
    boot.press("select", 3)
    boot.run(3)
    assert boot.mem("sound_on") == s0


def test_the_practice_list_s_select_is_untouched(boot):
    """SELECT cycles the Practice list's difficulty as before; the gesture lives on the title, in play and in a level's pause only."""
    from conftest import K_MINIGAMES
    from test_mg_list import line as list_line, tap as list_tap, to_list
    unlock_debug(boot)
    to_list(boot)
    assert "NORMAL" in list_line(boot, 0)
    list_tap(boot, "select")
    boot.run(4)
    assert "HARD" in list_line(boot, 0)
    boot.hold("select")
    boot.run(2)
    for _ in range(3):
        boot.press("start", 2)
        boot.run(3)
    boot.release("select")
    boot.run(4)
    assert boot.mem("debug_menu_open") == 0 and boot.mem("game_state") != DEBUG


# ---- using it ----
def test_left_right_change_the_level_and_wrap(boot):
    combo(boot)
    release_combo(boot)
    n = []
    for b in ("right", "right", "left", "left", "left"):
        boot.press(b, 2)
        n.append(boot.mem("debug_level"))
    assert n == [2, 3, 2, 1, 20], "wraps below 1"
    boot.press("right", 2)
    assert boot.mem("debug_level") == 1, "and above 20"
    boot.press("up", 2)                                   # the cursor moves (to MODE and back), the level does not
    boot.press("down", 2)
    assert boot.mem("debug_level") == 1 and boot.mem("debug_sel") == 1


def test_the_box_shows_the_level(boot):
    combo(boot)
    release_combo(boot)
    boot.press("right", 2)
    boot.press("right", 2)
    boot.run(3)
    assert banner_is(boot, "LEVEL 03")


@pytest.mark.parametrize("lvl", [1, 5, 12])
def test_a_starts_that_level_from_scratch(boot, lvl):
    combo(boot)
    release_combo(boot)
    for _ in range(lvl - 1):
        boot.press("right", 2)
    boot.press("a", 2)
    boot.run(15)       # the level load takes a few frames (LCD off)
    assert boot.mem("debug_menu_open") == 0 and boot.mem("game_state") == PLAYING
    assert boot.mem("level") == lvl and boot.mem("cur_group") == (lvl - 1) % 10, "its venue"
    assert boot.mem("lives") == 3 and boot.mem("score") == 0 and boot.mem("overlay_on") == 0
    assert boot.mem("play_mode") == MODE_LEVEL and boot.mem("story_on") == 0, "the LEVEL harness (the old rotation)"
    boot.run(30)
    assert boot.mem("game_state") == PLAYING
    assert boot.regs()["WY"] != 0 and boot.mem(0xFF45) != 255, "the banner window's own LYC and WY are back"


def test_start_starts_too(boot):
    combo(boot)
    release_combo(boot)
    boot.press("right", 2)
    boot.press("start", 2)
    boot.run(15)
    assert boot.mem("game_state") == PLAYING and boot.mem("level") == 2


def test_the_mode_line_switches_between_the_four_runs(boot):
    combo(boot)
    release_combo(boot)
    goto(boot, 0)
    seen = []
    for _ in range(4):
        tap(boot, "right")
        boot.run(6)
        seen.append((line(boot, 2)[1], boot.mem("debug_story"), boot.mem("debug_classic")))
    assert seen == [("STORY", 1, 0), ("ARCADE", 2, 0), ("CLASSIC", 0, 1), ("LEVEL", 0, 0)]
    tap(boot, "left")
    boot.run(6)
    assert line(boot, 2)[1] == "CLASSIC" and [line(boot, y)[0] for y in (2, 4, 6, 8)] == ["MODE", "LEVEL", "", ""]
    tap(boot, "left")
    boot.run(6)                                           # (a mode change rebuilds the screen with the LCD off: a few frames)
    tap(boot, "left")
    boot.run(6)
    assert banner_is(boot, "STORY 1 PRE")
    assert [line(boot, y)[0] for y in (2, 4, 6, 8)] == ["MODE", "CHAPTER", "STEP", "BAR CHANGE"]


def test_the_gesture_in_play_opens_the_menu_then_a_starts_a_level_fresh(gb):
    gb.write("lives", 1)
    gb.write("score", 77)
    combo(gb)
    assert gb.mem("debug_menu_open") == 1 and gb.mem("game_state") == DEBUG
    x = gb.mem("bartender_x")
    gb.run(20)
    assert gb.mem("bartender_x") == x, "stands still while open"
    release_combo(gb)
    gb.press("right", 2)
    assert gb.mem("debug_level") == 2
    gb.press("a", 2)
    gb.run(15)
    assert gb.mem("game_state") == PLAYING and gb.mem("level") == 2 and gb.mem("cur_group") == 1
    assert gb.mem("lives") == 3 and gb.mem("score") == 0 and gb.mem("debug_menu_open") == 0


def test_b_closes_and_play_resumes_as_it_was(gb):
    from test_flow import tile_id
    fc = gb.mem("intro_timer")
    lyc, wy = gb.mem(0xFF45), gb.regs()["WY"]
    combo(gb)
    release_combo(gb)
    gb.press("b", 2); gb.run(1)   # (closing takes a frame more: the LCD goes off while the wall's tiles and palettes go back)
    assert gb.mem("debug_menu_open") == 0 and gb.mem("game_state") == PLAYING and gb.mem("overlay_on") == 0
    assert gb.mem(0xFF45) == lyc and gb.regs()["WY"] == wy, "the banner window's LYC and WY"
    assert win_row(gb, 0) == [tile_id("PANEL_TOP")] * 20 and win_row(gb, 2) == [tile_id("PANEL_BOT")] * 20
    gb.run(10)
    assert gb.mem("game_state") == PLAYING and gb.mem("level") == 1
    assert gb.mem("intro_timer") != fc or gb.mem("intro_timer") == 0, "the game runs again"
    assert any(gb.pb.memory[0xFE00 + 4 * i] for i in range(40)), "its sprites are drawn again"


def test_b_returns_to_the_title(boot):
    combo(boot)
    release_combo(boot)
    boot.press("b", 2); boot.run(1)   # (closing takes a frame more: the LCD goes off while the wall's tiles and palettes go back)
    boot.run(5)
    assert boot.mem("debug_menu_open") == 0 and boot.mem("game_state") == TITLE and boot.mem("overlay_on") == 0
    assert boot.regs()["WY"] == 64 and boot.mem(0xFF45) == 86, "LYC and WY as they were"
    title_level(boot)
    boot.run(20)
    assert boot.mem("game_state") == PLAYING, "the title still works"


def test_b_with_select_still_held_does_not_reopen(gb):
    combo(gb)
    gb.press("b", 2); gb.run(1)   # (closing takes a frame more: the LCD goes off while the wall's tiles and palettes go back)
    gb.run(WINDOW + 10)
    assert gb.mem("debug_menu_open") == 0 and gb.mem("game_state") == PLAYING
    release_combo(gb)


def test_short_start_pauses_normally(gb):
    unlock_debug(gb)
    gb.press("start", 3)
    gb.run(3)
    assert gb.mem("game_state") == PAUSED and gb.mem("debug_menu_open") == 0
    gb.press("start", 3)
    gb.run(3)
    assert gb.mem("game_state") == PLAYING


def test_the_gesture_opens_from_a_level_s_pause(gb):
    unlock_debug(gb)
    gb.press("start", 3)
    gb.run(3)
    assert gb.mem("game_state") == PAUSED
    gesture(gb)
    assert gb.mem("game_state") == DEBUG and gb.mem("debug_menu_open") == 1
    release_combo(gb)
    gb.press("b", 2); gb.run(1)   # (closing takes a frame more: the LCD goes off while the wall's tiles and palettes go back)
    assert gb.mem("game_state") == PLAYING and gb.mem("overlay_on") == 0


# ---- the unlock: the Konami code on the title ----
def test_the_konami_code_unlocks_it(boot):
    assert not debug_unlocked(boot)
    n0 = boot.read("sfx_count", 15)[SFX_EXTRA]
    konami(boot)
    assert debug_unlocked(boot) and boot.read("sfx_count", 15)[SFX_EXTRA] == n0 + 1
    assert boot.mem("game_state") == TITLE and boot.mem("title_menu") == TM_TOP and boot.mem("title_sel") == 0, "the code's A chose nothing"
    boot.run(10)
    gesture(boot)
    assert boot.mem("debug_menu_open") == 1, "and now the gesture opens it"
    release_combo(boot)


@pytest.mark.parametrize("keys", [KONAMI[:-1], KONAMI[:-2] + ["a", "b"], ["up", "up", "down", "down", "left", "right", "left", "right", "a", "b"],
                                  ["up", "up", "up", "down", "down", "left", "right", "left", "right", "b", "a"]], ids=["short", "swapped-end", "ab-swapped", "extra-up"])
def test_a_wrong_code_does_not_unlock(boot, keys):
    konami(boot, keys)
    assert not debug_unlocked(boot)


def test_a_false_start_does_not_spoil_the_code(boot):
    konami(boot, ["left"] + KONAMI)
    assert debug_unlocked(boot)


def test_the_code_works_from_a_submenu_too_and_changes_nothing_there(boot):
    from test_flow import menu_block_rows
    title_pick(boot, K_SETTINGS)
    konami(boot)
    assert debug_unlocked(boot)
    boot.run(MENU_SETTLE)
    assert boot.mem("title_menu") == TM_TOP and boot.mem("game_state") == TITLE, "(its B went back to the top level)"


def test_the_code_is_remembered_after_a_reset(boot):
    from test_sound import save_ram, make_rom
    konami(boot)
    ram = save_ram(boot)
    rom = make_rom(boot.model_name, ram)
    rom.run(120)
    try:
        assert debug_unlocked(rom)
        title_pick(rom, K_SETTINGS)
        assert menu_items(rom) == [K_MUSIC, K_BARCHANGE, K_ERASE, K_DEBUG]
    finally:
        rom.stop()


def test_settings_lists_debug_menu_only_when_unlocked(boot):
    title_pick(boot, K_SETTINGS)
    assert menu_items(boot) == [K_MUSIC, K_BARCHANGE, K_ERASE]
    menu_tap(boot, "b")
    konami(boot)
    title_pick(boot, K_SETTINGS)
    boot.run(MENU_SETTLE)
    assert menu_items(boot) == [K_MUSIC, K_BARCHANGE, K_ERASE, K_DEBUG]
    from test_flow import title_text_row, menu_block_rows
    from test_flow import TITLE_ART
    assert [title_text_row(k) for k in ("music_on", "bar_snap", "erase", "debug")] == [
        menu_block_rows(boot)[r - 4] for r in (6, 8, 10, 12)]


def test_the_settings_line_opens_the_menu_and_b_comes_back_to_it(boot):
    unlock_debug(boot)
    title_pick(boot, K_SETTINGS, K_DEBUG)
    boot.run(7)
    assert boot.mem("debug_menu_open") == 1 and boot.mem("debug_from_title") == 1 and banner_is(boot, "LEVEL 01")
    tap(boot, "b")
    boot.run(MENU_SETTLE)
    assert boot.mem("game_state") == TITLE and boot.mem("title_menu") == TM_SETTINGS
    assert menu_items(boot)[boot.mem("title_sel")] == K_DEBUG, "SETTINGS, the cursor on DEBUG MENU"


def test_the_debug_line_alone_does_not_toggle_the_music(boot):
    unlock_debug(boot)
    s0 = boot.mem("sound_on")
    title_pick(boot, K_SETTINGS, K_DEBUG)
    boot.run(3)
    tap(boot, "b")
    assert boot.mem("sound_on") == s0


def test_the_release_build_ships_the_menu_locked():
    """make release: the menu is in it (locked until the code), not the playtest build's unlock-everything."""
    from gbtools import Rom
    subprocess.run(["make", "release"], cwd=ROOT, check=True, capture_output=True)
    noi = (ROOT / "build" / "release.noi").read_text()
    assert "debug_menu_open" in noi and "debug_unlocked" in noi
    for model in ("dmg", "cgb"):
        with Rom(ROOT / "build" / "release.gb", model) as rom:
            rom.run(120)
            assert not debug_unlocked(rom)
            konami(rom)
            assert debug_unlocked(rom)
            rom.run(10)
            gesture(rom)
            assert rom.mem("debug_menu_open") == 1 and rom.mem("game_state") == DEBUG
            release_gesture(rom)
            rom.press("b", 2); rom.run(1)   # (closing takes a frame more: the LCD goes off while the wall's tiles and palettes go back)
            assert rom.mem("game_state") == TITLE


def test_the_gesture_works_from_any_menu_item_and_the_menu_survives(boot):
    from test_flow import music_line, title_text_row
    title_pick(boot, K_SETTINGS)                          # the cursor on MUSIC
    assert menu_items(boot) == [K_MUSIC, K_BARCHANGE, K_ERASE] and boot.mem("title_sel") == 0
    s0 = boot.mem("sound_on")
    combo(boot)
    assert boot.mem("debug_menu_open") == 1 and boot.mem("sound_on") == s0, "neither START nor SELECT toggled it"
    release_combo(boot)
    boot.press("b", 2); boot.run(1)   # (closing takes a frame more: the LCD goes off while the wall's tiles and palettes go back)
    boot.run(3)
    boot.run(MENU_SETTLE)
    assert boot.mem("game_state") == TITLE and boot.mem("title_menu") == TM_SETTINGS and boot.mem("title_sel") == 0
    assert music_line(boot) == title_text_row("music_on" if s0 else "music_off")
    menu_tap(boot, "b")                                   # the top level
    title_level(boot)
    boot.run(20)
    assert boot.mem("game_state") == PLAYING and boot.mem("level") == 1


# ---- the mini-games: the gesture never opens it from their pause ----
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_gesture_never_opens_from_a_mini_game_s_pause(model):
    from test_mg import GS_MINI, MG_PLAY, MG_PRACTICE, mg_enter, until
    from test_sound import make_rom
    gb = make_rom(model, with_unlock(), sound=False)
    gb.run(120)
    try:
        mg_enter(gb, 1, MG_PRACTICE)
        until(gb, lambda: gb.mem("mg_phase") == MG_PLAY, 400)
        gb.hold("select")
        gb.run(2)
        for _ in range(3):                                # (START pauses it, resumes it, pauses it: the debug menu is not a part of it)
            gb.press("start", 2)
            gb.run(4)
        assert gb.mem("debug_menu_open") == 0 and gb.mem("game_state") in (PAUSED, GS_MINI)
        gb.release("select")
    finally:
        gb.stop()


# ---- mode-aware (owner 2026-10-10): story positions when opened in story play or on PLAY's STORY / CONTINUE -----------
# Positions of a chapter: 0 its PRE scene, 1..STORY_STEPS its steps (only those the engine plays: STEP_SKIP ones only
# with story_unskip), STORY_STEPS + 1 its POST scene. The CHAPTER line's Left/Right the chapter, the STEP line's the position. A story run started
# here writes nothing to SRAM (save.c save_lock).
GS_STORY, GS_GOAL = 11, 12


# where each title item is: the top level's own, or the submenu of a top item
WHERE = {K_STORY: K_PLAY, K_CONTINUE: K_PLAY, K_ARCADE: K_PLAY, K_CLASSIC: K_PLAY, K_SOUNDTRACK: K_BONUS, K_MUSIC: K_SETTINGS}


def open_on(boot, k):
    """The title's cursor on item k (K_*: opening its submenu first), then the gesture (the menu unlocked; SELECT is let go)."""
    if k in WHERE:
        title_pick(boot, WHERE[k], k, press=False)
    else:
        menu_to(boot, k)
    combo(boot)
    release_combo(boot)
    boot.run(3)
    return boot


def playable(c=0, unskip=0):
    """Chapter c's positions the box offers, from the story data (build/story.json "steps": built per chapter)."""
    from test_story import STORY
    steps = STORY["steps"][c]
    n = len(steps)
    return [0] + [p for p in range(1, n + 1) if steps[p - 1]["built"] or (unskip >> (p - 1)) & 1] + [n + 1]


def test_on_story_the_box_selects_story_positions(boot):
    open_on(boot, K_STORY)
    assert boot.mem("debug_menu_open") == 1 and boot.mem("debug_story") == 1
    assert (boot.mem("debug_chapter"), boot.mem("debug_pos")) == (0, 0)
    assert banner_is(boot, "STORY 1 PRE")
    seq = playable()
    seen = []
    for _ in range(len(seq)):
        pos(boot, 1)
        seen.append(boot.mem("debug_pos"))
    assert seen == seq[1:] + [0], "Right on STEP: the chapter's playable positions (unbuilt slots passed over), wrapping"
    pos(boot, -1)
    assert boot.mem("debug_pos") == seq[-1]
    boot.run(3)
    assert banner_is(boot, "STORY 1 POST")
    chap(boot, -1)
    assert boot.mem("debug_chapter") == 9 and boot.mem("debug_pos") == seq[-1], "chapters wrap, the position kept"
    assert banner_is(boot, "STORY 10 POST"), "chapter 10: two digits"
    chap(boot, 1)
    chap(boot, 1)
    pos(boot, 1)
    pos(boot, 1)
    pos(boot, 1)
    boot.run(3)
    assert (boot.mem("debug_chapter"), boot.mem("debug_pos")) == (1, playable(1)[2])
    assert banner_is(boot, "STORY 2 HAPPY")


def test_an_unskipped_step_is_offered(boot):
    from test_story import SEQ
    mini = next(i for i, s in enumerate(SEQ) if s["kind"] == "MINI")
    boot.write("story_unskip", 1 << mini)
    open_on(boot, K_STORY)
    while boot.mem("debug_pos") != mini + 1:
        pos(boot, 1)
    boot.run(3)
    assert banner_is(boot, "STORY 1 MINI")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("c,k", [(2, 0), (6, 2), (0, 0)])   # (a Happy hour of a chapter with a built mini-game goes on to it)
def test_a_starts_the_chapter_s_shift_with_the_story_rules_and_saves_nothing(model, c, k):
    from test_flow import run_until
    from test_scores import booted, v7_image
    from test_sound import save_ram
    from test_story import SHIFT_STEP, SHIFTS, banner_text as goal_text, centred, clear_bars, shift_title, win
    ram = v7_image([("ABC", 500)], story=1, step=1, tunes=0x21)
    with booted(model, ram) as rom:
        open_on(rom, K_STORY)
        for _ in range(c):
            chap(rom, 1)
        while rom.mem("debug_pos") != SHIFT_STEP[k] + 1:
            pos(rom, 1)
        tap(rom, "a")
        run_until(rom, lambda: rom.mem("game_state") == GS_GOAL, 60)
        rom.run(3)
        assert rom.mem("story_on") == 1 and rom.mem("debug_menu_open") == 0 and rom.mem("save_lock") == SAVE_LOCK_DEBUG
        assert (rom.mem("story_chapter"), rom.mem("story_step"), rom.mem("story_shift")) == (c, SHIFT_STEP[k], k)
        assert rom.mem("level") == c + 1 and rom.mem("cur_group") == c, "the chapter's venue"
        assert rom.mem("lives") == 3 and rom.mem("score") == 0, "the venue's lives, a fresh score"
        assert goal_text(rom, 1) == centred(shift_title(c, k)) and goal_text(rom, 2) == centred(SHIFTS[c][k]["line1"])
        assert rom.mem("story_goal") == SHIFTS[c][k]["type"], "the shift's goal"
        rom.press("a", 2)
        run_until(rom, lambda: rom.mem("game_state") == PLAYING, 20)
        win(rom, c, k)
        if k == 2:                                       # (Last call's quota meets the boss: the bars empty, then his banner)
            rom.run(3)
            clear_bars(rom)
        run_until(rom, lambda: rom.mem("game_state") in (GS_GOAL, GS_STORY), 400)
        assert (rom.mem("story_progress"), rom.mem("story_reached")) == (1, 1), "the real progress untouched"
        assert rom.mem16("tune_unlocked") == 0x21, "no unlocks from a debug run"
        after = save_ram(rom)
    assert after[:40] == with_unlock(ram)[:40], "SRAM not written (but for the unlock the test gave itself)"


@pytest.mark.parametrize("pos_name,scene", [("pre", "PRE_BISTRO"), ("post", "POST_BISTRO")])
def test_a_on_a_scene_plays_it(boot, pos_name, scene):
    from test_flow import run_until
    from test_story import SC
    open_on(boot, K_STORY)
    for _ in range(3):
        chap(boot, 1)
    if pos_name == "post":
        pos(boot, -1)
    tap(boot, "a")
    run_until(boot, lambda: boot.mem("game_state") == GS_STORY and boot.mem("story_scene") == SC[scene], 60)
    assert boot.mem("story_on") == 1 and boot.mem("story_chapter") == 3


def test_on_continue_the_box_starts_at_the_saved_chapter():
    from test_scores import booted, v7_image
    for story, step, p in ((4, 0, 0), (4, 3, 1)):
        with booted("cgb", v7_image([], story=story, step=step)) as rom:
            open_on(rom, K_CONTINUE)
            assert rom.mem("debug_story") == 1 and (rom.mem("debug_chapter"), rom.mem("debug_pos")) == (story, p)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_in_story_play_the_box_opens_where_the_story_is(model):
    from test_story import SHIFT_STEP, to_shift
    with to_shift(model, 3, 1) as gb:
        combo(gb)
        release_combo(gb)
        gb.run(3)
        assert gb.mem("debug_story") == 1
        assert (gb.mem("debug_chapter"), gb.mem("debug_pos")) == (3, SHIFT_STEP[1] + 1)
        assert banner_is(gb, "STORY 4 HAPPY")
        tap(gb, "b")
        assert gb.mem("game_state") == PLAYING and gb.mem("story_on") == 1, "B: the shift goes on"


@pytest.mark.parametrize("k", [K_PLAY, K_BONUS, K_SETTINGS, K_SOUNDTRACK, K_MUSIC])
def test_on_other_items_and_in_arcade_play_it_stays_the_level_select(boot, k):
    """The top level (PLAY too: no mode chosen yet) and BONUS / SETTINGS: the LEVEL select (the harness). (P5: PLAY's
    CLASSIC opens the CLASSIC box: tests/test_classic_mode.py.)"""
    open_on(boot, k)
    assert boot.mem("debug_menu_open") == 1
    assert boot.mem("debug_story") == 0 and boot.mem("debug_level") == 1
    assert banner_is(boot, "LEVEL 01")


def test_the_box_follows_play_s_cursor_and_b_leaves_the_submenu_as_it_was(boot):
    open_on(boot, K_STORY)
    assert boot.mem("debug_story") == 1 and banner_is(boot, "STORY 1 PRE")
    tap(boot, "b")
    boot.run(MENU_SETTLE)
    assert boot.mem("game_state") == TITLE and boot.mem("title_menu") == TM_PLAY
    assert menu_items(boot)[boot.mem("title_sel")] == K_STORY, "the PLAY submenu, the cursor on STORY"
    tap(boot, "down")                                      # ARCADE
    combo(boot)
    release_combo(boot)
    boot.run(3)
    assert boot.mem("debug_story") == 2 and banner_is(boot, "ARCADE 1 OPEN")
    tap(boot, "b")
    tap(boot, "down")                                      # CLASSIC (P5: its own box)
    combo(boot)
    release_combo(boot)
    boot.run(3)
    assert boot.mem("debug_story") == 0 and boot.mem("debug_classic") == 1 and banner_is(boot, "CLASSIC 01")
    tap(boot, "b")
    tap(boot, "up")
    tap(boot, "up")                                        # STORY again
    combo(boot)
    release_combo(boot)
    boot.run(3)
    assert boot.mem("debug_story") == 1
    tap(boot, "b")
    tap(boot, "b")                                         # the top level, on PLAY: arcade
    assert boot.mem("title_menu") == TM_TOP and boot.mem("title_sel") == 0
    combo(boot)
    release_combo(boot)
    boot.run(3)
    assert boot.mem("debug_story") == 0 and banner_is(boot, "LEVEL 01")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_story_select_golden(model):
    from conftest import check_golden_game, game_frames
    from test_flow import settle_title
    from test_sound import make_rom
    rom = make_rom(model, with_unlock())
    rom.model_name = model
    try:
        rom.run(120)
        settle_title(rom)
        open_on(rom, K_STORY)
        chap(rom, 1)
        chap(rom, 1)
        pos(rom, 1)
        pos(rom, 1)
        game_frames(rom, 3)
        assert banner_is(rom, "STORY 3 HAPPY")
        check_golden_game(rom, "debug_story")
    finally:
        rom.stop()


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_menu_goldens(model):
    """New goldens: the LEVEL menu opened from SETTINGS' neighbour on the title and the STORY menu (the ERASE prompt's are tests/test_erase.py's)."""
    from conftest import check_golden
    from test_flow import settle_title
    from test_sound import make_rom
    rom = make_rom(model, with_unlock())
    rom.model_name = model
    try:
        rom.run(120)
        settle_title(rom)
        open_on(rom, K_SETTINGS)
        rom.run(3)
        check_golden(rom, "debug_menu_level")
        goto(rom, 0)
        tap(rom, "right")
        rom.run(6)
        assert banner_is(rom, "STORY 1 PRE")
        check_golden(rom, "debug_menu_story")
    finally:
        rom.stop()


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_starts_a_built_boss_fight_and_saves_nothing(model):
    """The boss is no step of its own (owner 2026-10-17): the box offers LAST (Last call); A starts it, meeting its quota turns the level into
    the boss fight (his banner, the fight); satisfied, CHAPTER CLEAR and the POST scene follow, and SRAM stays as it was."""
    from test_flow import LEVEL_CLEAR, run_until
    from test_scores import booted, v7_image
    from test_sound import save_ram
    from test_story import BOSS_BUILT, SC, SHIFT_STEP, banner_text as goal_text, centred, to_boss_banner
    assert BOSS_BUILT, "no boss is built yet"
    c = min(BOSS_BUILT)
    ram = v7_image([("ABC", 500)], tunes=1)
    with booted(model, ram) as rom:
        open_on(rom, K_STORY)
        for _ in range(c):
            chap(rom, 1)
        assert SHIFT_STEP[2] + 1 in playable(c)
        while rom.mem("debug_pos") != SHIFT_STEP[2] + 1:
            pos(rom, 1)
        rom.run(3)
        assert banner_is(rom, f"STORY {c + 1} LAST")
        tap(rom, "a")
        run_until(rom, lambda: rom.mem("game_state") == GS_GOAL, 60)
        rom.run(3)
        assert rom.mem("story_on") == 1 and rom.mem("boss_on") == 0
        assert (rom.mem("story_chapter"), rom.mem("story_step")) == (c, SHIFT_STEP[2])
        assert rom.mem("lives") == 3 and rom.mem("save_lock") == SAVE_LOCK_DEBUG
        rom.write("tip_chance", 0)
        rom.press("a", 2)
        run_until(rom, lambda: rom.mem("game_state") == PLAYING, 20)
        to_boss_banner(rom, c)
        assert rom.mem("boss_on") == 1 and rom.mem("boss_id") == c and goal_text(rom, 1) == centred("BOSS")
        rom.press("a", 2)
        run_until(rom, lambda: rom.mem("game_state") == PLAYING, 20)
        rom.write("boss_hook", 3)                       # satisfied at once (tests/test_boss.py plays the fight)
        clear_regulars(rom)
        run_until(rom, lambda: rom.mem("game_state") == LEVEL_CLEAR, 200)
        run_until(rom, lambda: rom.mem("game_state") == GS_STORY and rom.mem("story_scene") == SC["POST_SALOON"] + 2 * c,
                  400)
        assert rom.mem("boss_on") == 0
        assert (rom.mem("story_progress"), rom.mem("story_reached")) == (0, 0), "nothing saved"
        after = save_ram(rom)
    assert after[:40] == with_unlock(ram)[:40], "SRAM not written (but for the unlock the test gave itself)"


# ---- the ARCADE box (the three modes): PLAY's ARCADE or ARCADE play; its steps only (no scenes) ----------------------
def test_the_arcade_box_offers_the_steps_only_and_a_starts_an_arcade_run(boot):
    from test_flow import GS_GOAL, run_until
    from test_story import STORY_STEPS
    open_on(boot, K_ARCADE)
    release_combo(boot)
    assert boot.mem("debug_story") == 2 and boot.mem("debug_chapter") == 0 and boot.mem("debug_pos") == 1
    assert banner_is(boot, "ARCADE 1 OPEN")
    seen = []
    for _ in range(STORY_STEPS + 1):
        seen.append(boot.mem("debug_pos"))
        pos(boot, 1)
    assert 0 not in seen and STORY_STEPS + 1 not in seen, "no PRE / POST scene in ARCADE"
    while boot.mem("debug_pos") != 2:
        pos(boot, 1)                                       # the Happy hour
    chap(boot, 1)                                          # chapter 2
    assert banner_is(boot, "ARCADE 2 HAPPY")
    tap(boot, "a")
    run_until(boot, lambda: boot.mem("game_state") == GS_GOAL, 60)
    assert boot.mem("story_arc") == 1 and boot.mem("play_mode") == MODE_ARCADE and boot.mem("save_lock") == SAVE_LOCK_DEBUG
    assert boot.mem("story_chapter") == 1 and boot.mem("story_shift") == 1 and boot.mem("lives") == 3
    boot.press("a", 2)
    run_until(boot, lambda: boot.mem("game_state") == PLAYING, 20)
    combo(boot)                                            # in ARCADE play: the ARCADE box where the run is
    release_combo(boot)
    assert boot.mem("debug_story") == 2 and banner_is(boot, "ARCADE 2 HAPPY")


def test_closing_puts_the_wall_s_tiles_back_under_the_game(gb):
    """The menu's wood wall uses the stage ids 0-4 (src/mg_list.c list_skin_load); the game under the window gets its own tiles back on B."""
    vram = lambda: bytes(gb.read(0x9000, 5 * 16))
    before = vram()
    combo(gb)
    release_combo(gb)
    gb.run(3)
    assert vram() != before, "the wall's tiles are in while the menu shows"
    gb.press("b", 2)
    gb.run(3)
    assert gb.mem("debug_menu_open") == 0 and vram() == before
