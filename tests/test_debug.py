# Debug level select: hold START + SELECT ~30 frames (title or play) -> a banner "LEVEL nn"; Left/Right change it,
# A starts that level from scratch, B closes. Only in DEBUG_MENU builds (the normal build); `make release` has none.
import subprocess

import pytest
from conftest import (clear_regulars, K_ARCADE, K_BONUS, K_CLASSIC, K_CONTINUE, K_MUSIC, K_PLAY, K_SETTINGS, K_SOUNDTRACK, K_STORY, MENU_SETTLE,
                      ROOT, TM_PLAY, TM_SETTINGS, TM_TOP, menu_items, menu_tap, menu_to, title_arcade, title_level, title_pick)

pytestmark = pytest.mark.timeout(120)

TITLE, PLAYING, PAUSED = 0, 1, 5
MODE_ARCADE, MODE_STORY, MODE_CLASSIC, MODE_LEVEL = range(4)   # src/game.h play_mode
COMBO = 30
SAVE_LOCK_DEBUG = 2     # save.c save_lock: a debug-select run (ARCADE alone is 1: it still records the mini-games reached)


def combo(gb, frames=COMBO + 5):      # (the pause menu opens in the first frames and its music tick makes a frame or two take two: the combo counts game frames)
    gb.hold("start")
    gb.hold("select")
    gb.run(frames)


def release_combo(gb):
    gb.release("start")
    gb.release("select")
    gb.run(2)


def banner_text(gb):
    return [t & 0xFF for t in gb.bg_tilemap(True)[1][:20]]


def test_the_combo_opens_the_menu_on_the_title(boot):
    combo(boot)
    assert boot.mem("debug_menu_open") == 1 and boot.mem("debug_level") == 1
    assert boot.mem("game_state") not in (TITLE, PLAYING), "paused: its own state"
    assert boot.mem("overlay_on") == 1
    release_combo(boot)
    assert boot.mem("debug_menu_open") == 1


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


def test_holding_the_combo_a_little_is_not_enough(boot):
    combo(boot, COMBO - 5)
    assert boot.mem("debug_menu_open") == 0
    release_combo(boot)
    boot.run(10)
    assert boot.mem("debug_menu_open") == 0 and boot.mem("game_state") == TITLE


def test_the_combo_on_the_title_does_not_leave_the_music_toggled(boot):
    s0 = boot.mem("sound_on")
    boot.hold("select")
    boot.run(2)
    boot.hold("start")
    boot.run(COMBO + 2)
    assert boot.mem("debug_menu_open") == 1
    assert boot.mem("sound_on") == s0
    release_combo(boot)


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
    boot.press("up", 2)
    boot.press("down", 2)
    assert boot.mem("debug_level") == 1


def test_the_box_shows_the_level(boot):
    combo(boot)
    release_combo(boot)
    boot.press("right", 2)
    boot.press("right", 2)
    boot.run(3)
    from test_flow import tile_id
    txt = banner_text(boot)
    want = [tile_id("GLYPH_" + c) for c in "L" "E" "V" "E" "L"] + [tile_id("HUD_BLANK"), tile_id("GLYPH_0"), tile_id("GLYPH_3")]
    start = (20 - 13) // 2                           # (then " SNAP": the bar-change mode)
    assert txt[start:start + 8] == want, txt


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


def test_the_combo_in_play_pauses_then_a_starts_a_level_fresh(gb):
    gb.write("lives", 1)
    gb.write("score", 77)
    combo(gb)
    assert gb.mem("debug_menu_open") == 1
    x = gb.mem("bartender_x")
    gb.run(20)
    assert gb.mem("bartender_x") == x, "paused while open"
    release_combo(gb)
    gb.press("right", 2)
    assert gb.mem("debug_level") == 2
    gb.press("a", 2)
    gb.run(15)
    assert gb.mem("game_state") == PLAYING and gb.mem("level") == 2 and gb.mem("cur_group") == 1
    assert gb.mem("lives") == 3 and gb.mem("score") == 0 and gb.mem("debug_menu_open") == 0


def test_b_closes_and_play_resumes(gb):
    fc = gb.mem("intro_timer")
    combo(gb)
    release_combo(gb)
    gb.press("b", 2)
    assert gb.mem("debug_menu_open") == 0 and gb.mem("game_state") == PLAYING and gb.mem("overlay_on") == 0
    gb.run(10)
    assert gb.mem("game_state") == PLAYING and gb.mem("level") == 1
    assert gb.mem("intro_timer") != fc or gb.mem("intro_timer") == 0, "the game runs again"


def test_b_returns_to_the_title(boot):
    combo(boot)
    release_combo(boot)
    boot.press("b", 2)
    boot.run(5)
    assert boot.mem("debug_menu_open") == 0 and boot.mem("game_state") == TITLE and boot.mem("overlay_on") == 0
    title_level(boot)
    boot.run(20)
    assert boot.mem("game_state") == PLAYING, "the title still works"


def test_b_with_the_combo_still_held_does_not_reopen(gb):
    combo(gb)
    gb.press("b", 2)
    gb.run(COMBO + 10)
    assert gb.mem("debug_menu_open") == 0 and gb.mem("game_state") == PLAYING
    release_combo(gb)


def test_short_start_pauses_normally(gb):
    gb.press("start", 3)
    gb.run(3)
    assert gb.mem("game_state") == PAUSED and gb.mem("debug_menu_open") == 0
    gb.press("start", 3)
    gb.run(3)
    assert gb.mem("game_state") == PLAYING


def test_the_release_build_has_no_debug_menu():
    subprocess.run(["make", "release"], cwd=ROOT, check=True, capture_output=True)
    noi = (ROOT / "build" / "release.noi").read_text()
    assert "debug_menu_open" not in noi and "debug_level" not in noi
    assert "debug_menu_open" in (ROOT / "build" / "game.noi").read_text()


def test_the_combo_works_from_any_menu_item_and_the_menu_survives(boot):
    from test_flow import music_line, title_text_row
    title_pick(boot, K_SETTINGS)                          # the cursor on MUSIC
    assert menu_items(boot) == [K_MUSIC] and boot.mem("title_sel") == 0
    s0 = boot.mem("sound_on")
    boot.hold("select")
    boot.run(2)
    boot.hold("start")
    boot.run(COMBO + 2)
    assert boot.mem("debug_menu_open") == 1 and boot.mem("sound_on") == s0, "neither START nor SELECT toggled it"
    release_combo(boot)
    boot.press("b", 2)
    boot.run(3)
    boot.run(MENU_SETTLE)
    assert boot.mem("game_state") == TITLE and boot.mem("title_menu") == TM_SETTINGS and boot.mem("title_sel") == 0
    assert music_line(boot) == title_text_row("music_on" if s0 else "music_off")
    menu_tap(boot, "b")                                   # the top level
    title_level(boot)
    boot.run(20)
    assert boot.mem("game_state") == PLAYING and boot.mem("level") == 1


# ---- mode-aware (owner 2026-10-10): story positions when opened in story play or on PLAY's STORY / CONTINUE -----------
# Positions of a chapter: 0 its PRE scene, 1..STORY_STEPS its steps (only those the engine plays: STEP_SKIP ones only
# with story_unskip), STORY_STEPS + 1 its POST scene. Left/Right the chapter, Up/Down the position. A story run started
# here writes nothing to SRAM (save.c save_lock).
GS_STORY, GS_GOAL = 11, 12


def banner_is(gb, s):
    """The box's text s, then the bar-change mode (src/debug.c show_mode): SNAP by default."""
    from test_flow import tile_id
    s += " SNAP"
    want = [tile_id("HUD_BLANK")] * 20
    x = (20 - len(s)) // 2
    for i, ch in enumerate(s):
        want[x + i] = tile_id("HUD_BLANK") if ch == " " else tile_id("GLYPH_" + ch)
    return banner_text(gb) == want


def tap(gb, b):
    gb.press(b, 2)
    gb.run(1)


# where each title item is: the top level's own, or the submenu of a top item
WHERE = {K_STORY: K_PLAY, K_CONTINUE: K_PLAY, K_ARCADE: K_PLAY, K_CLASSIC: K_PLAY, K_SOUNDTRACK: K_BONUS, K_MUSIC: K_SETTINGS}


def open_on(boot, k):
    """The title's cursor on item k (K_*: opening its submenu first), then the combo."""
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
        tap(boot, "down")
        seen.append(boot.mem("debug_pos"))
    assert seen == seq[1:] + [0], "Down: the chapter's playable positions (unbuilt slots passed over), wrapping"
    tap(boot, "up")
    assert boot.mem("debug_pos") == seq[-1]
    boot.run(3)
    assert banner_is(boot, "STORY 1 POST")
    tap(boot, "left")
    assert boot.mem("debug_chapter") == 9 and boot.mem("debug_pos") == seq[-1], "chapters wrap, the position kept"
    assert banner_is(boot, "STORY 10 POST"), "chapter 10: two digits"
    tap(boot, "right")
    tap(boot, "right")
    tap(boot, "down")
    tap(boot, "down")
    tap(boot, "down")
    boot.run(3)
    assert (boot.mem("debug_chapter"), boot.mem("debug_pos")) == (1, playable(1)[2])
    assert banner_is(boot, "STORY 2 HAPPY")


def test_an_unskipped_step_is_offered(boot):
    from test_story import SEQ
    mini = next(i for i, s in enumerate(SEQ) if s["kind"] == "MINI")
    boot.write("story_unskip", 1 << mini)
    open_on(boot, K_STORY)
    while boot.mem("debug_pos") != mini + 1:
        tap(boot, "down")
    boot.run(3)
    assert banner_is(boot, "STORY 1 MINI")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("c,k", [(2, 0), (6, 2), (0, 0)])   # (a Happy hour of a chapter with a built mini-game goes on to it)
def test_a_starts_the_chapter_s_shift_with_the_story_rules_and_saves_nothing(model, c, k):
    from test_flow import run_until
    from test_scores import booted, v7_image
    from test_sound import save_ram
    from test_story import SHIFT_STEP, SHIFTS, banner_text as goal_text, centred, shift_title, win
    ram = v7_image([("ABC", 500)], story=1, step=1, tunes=0x21)
    with booted(model, ram) as rom:
        open_on(rom, K_STORY)
        for _ in range(c):
            tap(rom, "right")
        while rom.mem("debug_pos") != SHIFT_STEP[k] + 1:
            tap(rom, "down")
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
        run_until(rom, lambda: rom.mem("game_state") in (GS_GOAL, GS_STORY), 400)
        assert (rom.mem("story_progress"), rom.mem("story_reached")) == (1, 1), "the real progress untouched"
        assert rom.mem16("tune_unlocked") == 0x21, "no unlocks from a debug run"
        after = save_ram(rom)
    assert after[:40] == ram[:40], "SRAM not written"


@pytest.mark.parametrize("pos,scene", [("pre", "PRE_BISTRO"), ("post", "POST_BISTRO")])
def test_a_on_a_scene_plays_it(boot, pos, scene):
    from test_flow import run_until
    from test_story import SC
    open_on(boot, K_STORY)
    for _ in range(3):
        tap(boot, "right")
    if pos == "post":
        tap(boot, "up")
    tap(boot, "a")
    run_until(boot, lambda: boot.mem("game_state") == GS_STORY and boot.mem("story_scene") == SC[scene], 60)
    assert boot.mem("story_on") == 1 and boot.mem("story_chapter") == 3


def test_on_continue_the_box_starts_at_the_saved_chapter():
    from test_flow import run_until
    from test_scores import booted, v7_image
    for story, step, pos in ((4, 0, 0), (4, 3, 1)):
        with booted("cgb", v7_image([], story=story, step=step)) as rom:
            open_on(rom, K_CONTINUE)
            assert rom.mem("debug_story") == 1 and (rom.mem("debug_chapter"), rom.mem("debug_pos")) == (story, pos)


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
    from conftest import ROM, check_golden
    from gbtools import Rom
    from test_flow import settle_title
    with Rom(ROM, model) as rom:
        rom.model_name = model
        rom.run(120)
        settle_title(rom)
        open_on(rom, K_STORY)
        tap(rom, "right")
        tap(rom, "right")
        tap(rom, "down")
        tap(rom, "down")
        rom.run(3)
        assert banner_is(rom, "STORY 3 HAPPY")
        check_golden(rom, "debug_story")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_starts_a_built_boss_fight_and_saves_nothing(model):
    """A chapter whose boss slot is built offers it ("BOSS"); A starts the fight through step_start (boss_set): its
    banner, the fight; satisfied, CHAPTER CLEAR and the POST scene follow, and SRAM stays as it was."""
    from test_flow import LEVEL_CLEAR, run_until
    from test_scores import booted, v7_image
    from test_sound import save_ram
    from test_story import BOSS_BUILT, BOSS_STEP, SC, banner_text as goal_text, centred
    assert BOSS_BUILT, "no boss is built yet"
    c = min(BOSS_BUILT)
    ram = v7_image([("ABC", 500)], tunes=1)
    with booted(model, ram) as rom:
        open_on(rom, K_STORY)
        for _ in range(c):
            tap(rom, "right")
        assert BOSS_STEP + 1 in playable(c)
        while rom.mem("debug_pos") != BOSS_STEP + 1:
            tap(rom, "down")
        rom.run(3)
        assert banner_is(rom, f"STORY {c + 1} BOSS")
        tap(rom, "a")
        run_until(rom, lambda: rom.mem("game_state") == GS_GOAL, 60)
        rom.run(3)
        assert rom.mem("story_on") == 1 and rom.mem("boss_on") == 1 and rom.mem("boss_id") == c
        assert (rom.mem("story_chapter"), rom.mem("story_step")) == (c, BOSS_STEP)
        assert rom.mem("lives") == 3 and rom.mem("save_lock") == SAVE_LOCK_DEBUG
        assert goal_text(rom, 1) == centred("BOSS")
        rom.write("tip_chance", 0)
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
    assert after[:40] == ram[:40], "SRAM not written"


# ---- the ARCADE box (the three modes): PLAY's ARCADE or ARCADE play; its steps only (no scenes) ----------------------
def test_the_arcade_box_offers_the_steps_only_and_a_starts_an_arcade_run(boot):
    from test_flow import GS_GOAL, run_until
    from test_story import STORY_STEPS, BOSS_BUILT, BOSS_STEP
    open_on(boot, K_ARCADE)
    release_combo(boot)
    assert boot.mem("debug_story") == 2 and boot.mem("debug_chapter") == 0 and boot.mem("debug_pos") == 1
    assert banner_is(boot, "ARCADE 1 OPEN")
    seen = []
    for _ in range(STORY_STEPS + 1):
        seen.append(boot.mem("debug_pos"))
        tap(boot, "down")
    assert 0 not in seen and STORY_STEPS + 1 not in seen, "no PRE / POST scene in ARCADE"
    assert (BOSS_STEP + 1 in seen) == (0 in BOSS_BUILT)
    while boot.mem("debug_pos") != 2:
        tap(boot, "down")                                  # the Happy hour
    tap(boot, "right")                                     # chapter 2
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
