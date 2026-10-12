# The title's BONUS > SOUNDTRACK: the soundtrack player (src/jukebox.c) and its unlocks (src/save.c, SRAM version 5).
# BONUS is always on the top level; its submenu's SOUNDTRACK opens the soundtrack list, B there comes back to it. Every tune of music.h in order, by its real
# name (tools/songs.py SOUNDTRACK -> build/jukebox_names.h); a locked tune shows "? ? ?" and does not play. Unlocks:
# the title tune always, any tune once it plays in story mode, the jingles also with chapter 1 cleared; they are saved
# at once and a new story never clears them. A debug-select story run saves nothing (test_debug.py).
import json
import re

import pytest
from conftest import (K_BONUS, K_MINIGAMES, K_PLAY, K_SETTINGS, K_SOUNDTRACK, MENU_SETTLE, ROOT, TM_BONUS, TM_TOP, check_golden,
                      hold_stage_anim, menu_items, title_pick)
from test_flow import (GS_GOAL, GS_STORY, TITLE, most_per_scanline, run_until, settle_title, state, tilemap_row,
                       title_text_row)
from test_scores import (JINGLES, TUNE_COUNT, TUNE_VENUE0, V4_SUM, V6_SUM, booted, old_progress, old_tunes, parse_save,
                         progress_unlocks, saved_tunes, table, v4_image, v5_image, v7_image, EMPTY, V7_SUM,
                         main_block, saved_story)
from test_sound import save_ram

pytestmark = pytest.mark.timeout(240)

GS_JUKEBOX = 14
TUNE_NONE = 255
ALL = (1 << TUNE_COUNT) - 1
STORY = json.loads((ROOT / "build" / "story.json").read_text())
GLYPH = STORY["glyphs"]                       # character -> BG tile (HUD glyphs + the story font)
ART = {m[0]: int(m[1]) for m in re.findall(r"#define (TILE_\w+) (\d+)", (ROOT / "build" / "art.h").read_text())}
_H = (ROOT / "build" / "jukebox_names.h").read_text()
NAMES = re.findall(r'^    "([^"]*)",   //', _H, re.M)
INFO = [re.findall(r'"([^"]*)"', l) for l in re.findall(r"^    \{ (.*) \},$", _H, re.M)]
ROW_LIST, VISIBLE, ROW_INFO, COL_PLAY = 2, 10, 13, 19


def row_text(s, x=1):
    r = [ART["TILE_HUD_BLANK"]] * 20
    if x == 255:
        x = (20 - len(s)) // 2
    for i, c in enumerate(s):
        r[x + i] = GLYPH[c]
    return r


def list_row(gb, k):
    """List line k without the playing icon's column."""
    return tilemap_row(gb, ROW_LIST + k, 0, 19)


def tap(rom, b):
    rom.press(b, 2)
    rom.run(1)                                # (the release must be seen before the next press)


def to_jukebox(rom):
    title_pick(rom, K_BONUS, K_SOUNDTRACK)
    run_until(rom, lambda: state(rom) == GS_JUKEBOX, 30)
    rom.run(2)
    return rom


def settle_rows(gb):
    gb.run(6)                                 # 4 rows a frame through the VBlank queue


# ---- the data ------------------------------------------------------------------------------------------------
def test_the_names_follow_music_h_and_songs_py():
    import importlib.util
    import sys
    sys.path.insert(0, str(ROOT / "tools"))
    spec = importlib.util.spec_from_file_location("gen_music", ROOT / "tools" / "gen_music.py")
    gm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gm)
    assert len(NAMES) == len(INFO) == TUNE_COUNT == len(gm.ORDER), "one name per tune, sized by TUNE_COUNT"
    src = [gm.SOURCE.get(n, n) for n in gm.ORDER]
    assert src[:5] == ["entertainer", "clear", "over", "bonus", "galop"] and src[5:] == gm.songs.VENUES
    for k, name, info in zip(src, NAMES, INFO):
        short, full, credit, where = gm.songs.SOUNDTRACK[k]
        assert name == short and " ".join(i for i in info[:2] if i) == full and info[2:] == [credit, where]
        assert all(len(s) <= 18 and set(s) <= set(GLYPH) for s in [name] + info)
    assert NAMES[0] == "THE ENTERTAINER" and NAMES[TUNE_VENUE0] == "OH! SUSANNA"


# ---- the menu --------------------------------------------------------------------------------------------------
def test_bonus_is_always_on_the_menu(boot):
    assert menu_items(boot) == [K_PLAY, K_BONUS, K_SETTINGS], "PLAY, BONUS, SETTINGS"
    assert tilemap_row(boot, 9, 0, 20) == title_text_row("bonus")
    with booted(boot.model_name, v7_image([], story=3, step=1, tunes=ALL)) as rom:
        assert menu_items(rom) == [K_PLAY, K_BONUS, K_SETTINGS], "the same with a story save"
        title_pick(rom, K_BONUS)
        rom.run(MENU_SETTLE)
        assert menu_items(rom) == [K_SOUNDTRACK, K_MINIGAMES] and tilemap_row(rom, 8, 0, 20) == title_text_row("soundtrack")
        assert tilemap_row(rom, 10, 0, 20) == title_text_row("minigames"), "MINI GAMES second (tests/test_mg_list.py)"


def test_soundtrack_opens_the_player_and_b_comes_back_to_bonus(boot):
    to_jukebox(boot)
    assert state(boot) == GS_JUKEBOX
    tap(boot, "b")                                            # (nothing playing: back to the title)
    run_until(boot, lambda: state(boot) == TITLE, 30)
    boot.run(MENU_SETTLE)
    assert boot.mem("title_menu") == TM_BONUS and menu_items(boot) == [K_SOUNDTRACK, K_MINIGAMES]
    assert boot.mem("title_sel") == 0
    assert tilemap_row(boot, 8, 0, 20) == title_text_row("soundtrack"), "the BONUS submenu, where it was opened"
    tap(boot, "b")
    boot.run(MENU_SETTLE)
    assert boot.mem("title_menu") == TM_TOP and boot.mem("title_sel") == 1, "then the top level, on BONUS"
    assert boot.mem("title_back") == TM_TOP, "used once: the next title (a game over, the table) is the top level"


def test_up_down_select_and_wrap(boot):
    to_jukebox(boot)
    assert boot.mem("jb_sel") == 0 and boot.mem("jb_top") == 0 and boot.mem("cur_tune") == TUNE_NONE, "silence"
    tap(boot, "up")
    assert boot.mem("jb_sel") == TUNE_COUNT - 1 and boot.mem("jb_top") == TUNE_COUNT - VISIBLE, "wraps, scrolls"
    tap(boot, "down")
    assert boot.mem("jb_sel") == 0 and boot.mem("jb_top") == 0
    for i in range(1, TUNE_COUNT):
        tap(boot, "down")
        assert boot.mem("jb_sel") == i and boot.mem("jb_top") == max(0, i - VISIBLE + 1)
        c = boot.oam()[0]
        assert c["y"] - 16 + 7 == (ROW_LIST + i - boot.mem("jb_top")) * 8 and c["x"] == 8, "the mug on the line"
    assert state(boot) == GS_JUKEBOX


def test_a_fresh_cartridge_has_only_the_title_tune(boot):
    to_jukebox(boot)
    settle_rows(boot)
    assert boot.mem16("tune_unlocked") == 1
    assert tilemap_row(boot, 0, 0, 20) == row_text("SOUNDTRACK", 255)
    assert list_row(boot, 0) == row_text(NAMES[0])[:19]
    for k in range(1, VISIBLE):
        assert list_row(boot, k) == row_text("? ? ?")[:19], k
    assert tilemap_row(boot, ROW_INFO, 0, 20) == row_text("THE ENTERTAINER", 255)
    assert tilemap_row(boot, ROW_INFO + 2, 0, 20) == row_text("SCOTT JOPLIN, 1902", 255)
    tap(boot, "down")
    settle_rows(boot)
    assert tilemap_row(boot, ROW_INFO, 0, 20) == row_text("? ? ?", 255)
    assert tilemap_row(boot, ROW_INFO + 2, 0, 20) == row_text("LOCKED", 255)
    tap(boot, "a")
    boot.run(3)
    assert boot.mem("cur_tune") == TUNE_NONE, "a locked tune does not play"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_every_name_shows_once_unlocked_and_the_list_scrolls(model):
    with booted(model, v7_image([], tunes=ALL)) as rom:
        to_jukebox(rom)
        settle_rows(rom)
        for k in range(VISIBLE):
            assert list_row(rom, k) == row_text(NAMES[k])[:19], k
        for _ in range(TUNE_COUNT - 1):
            tap(rom, "down")
        settle_rows(rom)
        top = TUNE_COUNT - VISIBLE
        assert rom.mem("jb_top") == top
        for k in range(VISIBLE):
            assert list_row(rom, k) == row_text(NAMES[top + k])[:19], k
        assert [tilemap_row(rom, ROW_INFO + i, 0, 20) for i in range(4)] == [row_text(s, 255) for s in INFO[-1]]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_plays_b_stops_then_b_goes_back(model):
    with booted(model, v7_image([], tunes=ALL)) as rom:
        to_jukebox(rom)
        for t in (0, TUNE_VENUE0 + 3, 2):
            while rom.mem("jb_sel") != t:
                tap(rom, "down")
            tap(rom, "a")
            assert rom.mem("cur_tune") == t, t
            seen = set()
            for _ in range(40):
                rom.run(1)
                seen.add(tilemap_row(rom, ROW_LIST + t - rom.mem("jb_top"), COL_PLAY, 1)[0])
            if t != 2:                                          # (the GAME OVER jingle may end within the 40 frames)
                assert seen == {ART["TILE_HUD_MUG"], ART["TILE_HUD_BLANK"]}, "the playing icon blinks"
        tap(rom, "b")
        assert rom.mem("cur_tune") == TUNE_NONE and state(rom) == GS_JUKEBOX, "B stops the tune"
        rom.run(3)
        assert tilemap_row(rom, ROW_LIST + 2 - rom.mem("jb_top"), COL_PLAY, 1)[0] == ART["TILE_HUD_BLANK"]
        tap(rom, "b")
        run_until(rom, lambda: state(rom) == TITLE, 30)
        assert rom.mem("cur_tune") == 0 and rom.mem("sound_on") == 1, "the title and its tune"


def test_a_jingle_stops_by_itself_and_its_icon_goes(boot):
    to_jukebox(boot)
    boot.write("tune_unlocked", 0xFF)
    tap(boot, "down")
    tap(boot, "a")
    assert boot.mem("cur_tune") == 1
    run_until(boot, lambda: boot.mem("cur_tune") == TUNE_NONE, 200)
    boot.run(3)
    assert boot.mem("jb_shown") == TUNE_NONE
    assert tilemap_row(boot, ROW_LIST + 1, COL_PLAY, 1)[0] == ART["TILE_HUD_BLANK"]


def test_music_off_still_plays_here_and_stays_off_after(boot):
    tap(boot, "select")
    boot.run(2)
    assert boot.mem("sound_on") == 0
    to_jukebox(boot)
    tap(boot, "a")
    assert boot.mem("cur_tune") == 0 and boot.mem("sound_on") == 1 and boot.mem("jb_forced") == 1
    boot.run(20)
    assert boot.mem16("music_frames") > 0, "the driver ticks: the tune really plays"
    tap(boot, "b")
    tap(boot, "b")
    run_until(boot, lambda: state(boot) == TITLE, 30)
    boot.run(3)
    assert boot.mem("sound_on") == 0
    tap(boot, "b")                                            # BONUS -> the top level
    title_pick(boot, K_SETTINGS)
    boot.run(MENU_SETTLE)
    assert tilemap_row(boot, 9, 0, 20) == title_text_row("music_off")


def test_no_more_than_ten_sprites_a_line(boot):
    to_jukebox(boot)
    boot.write("tune_unlocked", 0xFF)
    tap(boot, "a")
    for b in ["down"] * 15 + ["up"] * 3:
        boot.press(b, 2)
        assert most_per_scanline(boot) <= 10
    assert len(boot.visible_sprites()) == 1, "the cursor only"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_soundtrack_screen_golden(model):
    tunes = 1 | (1 << 1) | (1 << 2) | (1 << TUNE_VENUE0) | (1 << (TUNE_VENUE0 + 1))
    with booted(model, v7_image([], story=1, step=1, tunes=tunes)) as rom:
        to_jukebox(rom)
        for _ in range(TUNE_VENUE0):
            tap(rom, "down")
        tap(rom, "a")
        run_until(rom, lambda: rom.mem("jb_t") & 31 == 4, 40)     # the icon's "on" half
        settle_rows(rom)
        assert rom.mem("cur_tune") == TUNE_VENUE0
        check_golden(rom, "jukebox")


# ---- the unlocks -------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_venue_unlocks_when_its_pre_scene_starts_and_it_is_saved(model):
    from test_story import skip_scene, start_story
    with start_story(model) as rom:
        assert rom.mem16("tune_unlocked") == 1, "the INTRO plays the title tune"
        skip_scene(rom)                                       # INTRO -> the saloon's PRE scene
        run_until(rom, lambda: state(rom) == GS_STORY and rom.mem("cur_tune") == TUNE_VENUE0, 30)
        assert rom.mem("story_scene") == 1
        assert rom.mem16("tune_unlocked") == 1 | 1 << TUNE_VENUE0
        ram = save_ram(rom)
    assert parse_save(ram) == [("   ", 0)] * 5 and saved_tunes(ram) == 1 | 1 << TUNE_VENUE0, "saved at once"
    assert saved_story(ram) == (0, 0), "no story progress yet"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_jingle_unlocks_when_first_heard_in_story(model):
    from test_story import to_chapter, win
    with to_chapter(model, 0) as gb:
        assert not gb.mem16("tune_unlocked") & 1 << 1
        win(gb, 0, 0)
        run_until(gb, lambda: gb.mem("cur_tune") == 1, 30)          # SHIFT CLEAR's jingle
        assert gb.mem16("tune_unlocked") & 1 << 1 and not gb.mem16("tune_unlocked") & 1 << 3


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_clearing_chapter_1_unlocks_every_jingle(model):
    from test_story import beat_the_boss, to_shift, win
    with to_shift(model, 0, 2) as gb:
        win(gb, 0, 2)
        beat_the_boss(gb, 0)                                         # (chapter 1 ends with Big Tex once he is built)
        run_until(gb, lambda: state(gb) == GS_STORY, 300)
        assert gb.mem("story_progress") == 1
        assert gb.mem16("tune_unlocked") & JINGLES == JINGLES, "BONUS and SHOW too, never heard in the story"
        ram = save_ram(gb)
    assert saved_tunes(ram) & JINGLES == JINGLES


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_unlocks_survive_a_new_story(model):
    """The unlocks are never re-locked: a new story's first save resets the progress, not the soundtrack."""
    from test_story import skip_scene, start_story, to_goal, win
    tunes = progress_unlocks(5, 2)
    with start_story(model, v7_image([("ABC", 500)], story=5, step=2, tunes=tunes)) as rom:
        assert rom.mem("story_scene") == 0, "STORY: a new story from the INTRO"
        skip_scene(rom)
        skip_scene(rom)
        to_goal(rom)
        win(rom, 0, 0)
        run_until(rom, lambda: state(rom) == GS_GOAL, 400)          # the happy hour's banner: saved (0, 1)
        assert (rom.mem("story_progress"), rom.mem("story_reached")) == (0, 1)
        assert rom.mem16("tune_unlocked") == tunes, "nothing re-locked"
        ram = save_ram(rom)
    assert saved_story(ram) == (0, 1) and saved_tunes(ram) == tunes and parse_save(ram)[0] == ("ABC", 500)
    with booted(model, ram) as again:
        assert again.mem16("tune_unlocked") == tunes
        to_jukebox(again)
        for _ in range(TUNE_VENUE0 + 6):
            tap(again, "down")
        settle_rows(again)
        top = again.mem("jb_top")
        assert top == TUNE_VENUE0 + 6 - (VISIBLE - 1)
        assert list_row(again, TUNE_VENUE0 + 5 - top) == row_text(NAMES[TUNE_VENUE0 + 5])[:19], "chapter 6: reached"
        assert list_row(again, TUNE_VENUE0 + 6 - top) == row_text("? ? ?")[:19]


# ---- SRAM version 7 (the three modes) and the migrations from versions 4 and 5 -----------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("story,step", [(0, 0), (0, 2), (3, 0), (3, 1), (6, 2), (9, 0)])
def test_a_version_4_save_migrates_to_version_7(model, story, step):
    entries = [("ABC", 500), ("DEF", 400)]
    with booted(model, v4_image(entries, story=story, step=step)) as rom:
        assert rom.mem("save_migrated") == 4 and table(rom) == EMPTY, "the old table is dropped (owner Q4)"
        p, r = old_progress(story, step)
        assert (rom.mem("story_progress"), rom.mem("story_reached")) == (p, r)
        want = progress_unlocks(p, r)
        assert rom.mem16("tune_unlocked") == want
        ram = save_ram(rom)
    assert main_block(ram) == (p, r, want) and all(parse_save(ram, t) == EMPTY for t in range(3)), "written back"
    with booted(model, ram) as again:
        assert again.mem("save_migrated") == 0 and again.mem16("tune_unlocked") == want


V0 = TUNE_VENUE0


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("old, new", [
    (1, 1),                                                    # the title only
    (1 | 1 << V0 | 1 << (V0 + 5), 1 | 1 << V0 | 1 << (V0 + 5)),  # venues 0-5 keep their bits
    (1 | 1 << (V0 + 6), 1 | 1 << (V0 + 7)),                    # the teahouse's Sakura Sakura: old venue 6 -> 7
    (1 | 1 << (V0 + 7), 1 | 1 << (V0 + 9)),                    # the space lounge's Blue Danube: 7 -> 9
    (1 | 1 << (V0 + 8), 1 | 1 << (V0 + 8)),                    # the zoo's Pop Goes the Weasel stays 8
    (0x7FFF, 0x7FFF & ~(1 << (V0 + 6))),                       # everything the old game had; Drunken Sailor never heard
    (0xFFFF, 0x7FFF & ~(1 << (V0 + 6))),                       # (old bits 14-15 meant nothing: dropped)
])
def test_a_version_5_save_s_unlocks_follow_the_new_tune_order(model, old, new):
    assert old_tunes(old) == new
    with booted(model, v5_image([("ABC", 500)], tunes=old)) as rom:
        assert rom.mem("save_migrated") == 5 and rom.mem16("tune_unlocked") == new
        ram = save_ram(rom)
    assert saved_tunes(ram) == new and ram[:4] == b"TPR7"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_version_5_save_keeps_its_unlocks_and_gains_its_progress_s(model):
    """A v5 save at the old chapter 8 (the space lounge) having heard its tunes: progress 6, step 0; the tunes heard
    stay unlocked in their new places (the old space tune is venue 9's now), with the unlocks of progress 6 added."""
    heard = progress_unlocks(7, 1)                              # old order: venues 0-7 (7 = the space lounge)
    with booted(model, v5_image([], story=7, step=1, tunes=heard)) as rom:
        assert (rom.mem("story_progress"), rom.mem("story_reached")) == (6, 0)
        want = old_tunes(heard) | progress_unlocks(6, 0)
        assert rom.mem16("tune_unlocked") == want
        assert want & 1 << (V0 + 9) and want & 1 << (V0 + 7) and not want & 1 << (V0 + 6) and not want & 1 << (V0 + 8)


def test_progress_unlocks_rule():
    assert progress_unlocks(0, 0) == 1, "nothing played: the title tune"
    assert progress_unlocks(0, 1) == 1 | 1 << TUNE_VENUE0, "a step of chapter 1 reached: the saloon"
    assert progress_unlocks(1, 0) == 1 | 1 << TUNE_VENUE0 | JINGLES
    assert progress_unlocks(10, 0) == ALL, "the story complete: everything"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_version_7_loads_its_unlocks_and_rejects_a_bad_one(model):
    with booted(model, v7_image([("ABC", 500)], story=2, step=1, tunes=0x1234 | 1)) as rom:
        assert rom.mem("save_migrated") == 0 and rom.mem16("tune_unlocked") == 0x1235, "kept as saved"
        assert (rom.mem("story_progress"), rom.mem("story_reached")) == (2, 1)
    with booted(model, v7_image([("ABC", 500)], tunes=0x0100)) as rom:
        assert rom.mem16("tune_unlocked") == 0x0101, "the title tune is always unlocked"
    good = bytearray(v7_image([("ABC", 500)], tunes=0x00F1))
    for name, edit in (("bad checksum", lambda r: r.__setitem__(V7_SUM, r[V7_SUM] ^ 1)),
                       ("unlocks outside the checksum", lambda r: r.__setitem__(6, r[6] ^ 2)),
                       ("bad progress", lambda r: r.__setitem__(4, 11))):
        r = bytearray(good)
        edit(r)
        with booted(model, bytes(r)) as rom:      # (a bad main block: no story, no unlocks; the tables are kept)
            assert table(rom)[0] == ("ABC", 500) and rom.mem16("tune_unlocked") == 1, name
            assert rom.mem("story_progress") == 0, name
