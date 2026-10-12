# M4: game flow. Title, pause, lost life, level clear, game over, level table.
import re

import pytest
from conftest import (GAME, K_ARCADE, K_BONUS, K_CLASSIC, K_CONTINUE, K_MUSIC, K_PLAY, K_SETTINGS, K_STORY, LAYOUT, MENU_SETTLE,
                      ROOT, TM_BONUS, TM_PLAY, TM_SETTINGS, TM_TOP, bar_top_row, check_golden, menu_items, menu_tap,
                      title_arcade, title_level, title_pick)

pytestmark = pytest.mark.timeout(120)

TITLE, PLAYING, LIFE_LOST, LEVEL_CLEAR, GAME_OVER, PAUSED, BONUS = range(7)
GS_LOOP, GS_INITIALS, GS_SCORES = 8, 9, 10      # M10b
GS_STORY, GS_GOAL = 11, 12                     # M11b
MAX_P, MAX_M = 16, 20
BT_FAIL = 6
ENTRY_X = GAME["ENTRY_X"]

# (group, start bar mask, start per bar, quota, spawn interval, step frames, pushback, serve score, empty gap)
TABLE = [   # playtest 4: L6 = old L3, L9 = old L5, linear in between, plateau after
    # M13b: from L3 about 1 in 4 patrons hurries (1.5x); the step column of L3-L9 is x 12/11 (src/level.c) so the
    # average entry-to-tap time stays where it was (old steps 59 58 57 56 53 51 48)
    # 10th venue (2026-10-11): The Chrome Cow is level 7, a new row midway between levels 6 and 8; levels 8-10 are the
    # old rows 7-9 (the rows stay with the position: teahouse, zoo, then the space lounge, the hardest)
    (0, 0x5, 1, 8, 300, 64, 4, 50, 120), (1, 0x7, 1, 10, 275, 60, 4, 75, 110), (2, 0xF, 1, 10, 269, 64, 4, 75, 108),
    (3, 0xF, 1, 11, 263, 63, 4, 100, 105), (4, 0xF, 1, 11, 256, 62, 4, 100, 102), (5, 0xF, 1, 12, 250, 61, 4, 125, 100),
    (6, 0xF, 1, 12, 244, 60, 4, 125, 97),
    (7, 0xF, 1, 13, 237, 58, 4, 125, 93), (8, 0xF, 1, 15, 223, 56, 3, 150, 87), (9, 0xF, 1, 16, 210, 52, 3, 150, 80),
]
ROWS = len(TABLE)                                   # one arcade loop
ART_H = (ROOT / "build" / "art.h").read_text()
PATRON_TILES = int(re.search(r"#define PATRON_GROUP_TILES (\d+)", ART_H).group(1))   # M8b: 144 shifted + 12 back views
PATRON_GROUP_NAMES = re.search(r"// group order: (.*)", ART_H).group(1).split(", ")


def patron_group_tiles(g):
    """Bytes of patron group g as generated (the ROM keeps them in a switchable bank, so read build/patrons_<g>.c)."""
    src = (ROOT / "build" / f"patrons_{PATRON_GROUP_NAMES[g]}.c").read_text()
    data = bytes(int(h, 16) for h in re.findall(r"0x([0-9A-F]{2})", src))
    assert len(data) == PATRON_TILES * 16
    return data


def tile_id(name):
    return int(re.search(rf"#define TILE_{name} (\d+)", ART_H).group(1))


def patrons(gb):
    st, bar, x = (gb.read(n, MAX_P) for n in ("patron_state", "patron_bar", "patron_x"))
    return sorted((bar[i], x[i]) for i in range(MAX_P) if st[i])


def mugs(gb):
    st = gb.read("mug_state", MAX_M)
    return [(st[i], gb.read("mug_x", MAX_M)[i]) for i in range(MAX_M) if st[i]]


def score(gb):
    return int.from_bytes(gb.read("score", 4), "little")


def hi_score(gb):
    return int.from_bytes(gb.read("hi_score", 4), "little")


def state(gb):
    return gb.mem("game_state")


def run_until(gb, cond, limit=400):
    for _ in range(limit):
        if cond():
            return
        gb.run(1)
    raise AssertionError("condition not reached in %d frames (state %d)" % (limit, state(gb)))


def put(gb, name, i, v):
    gb.write(gb.addr(name) + i, v)


def set_patron(gb, bar, x, pstate=1, frac=0):
    i = list(gb.read("patron_state", MAX_P)).index(0)
    for n, v in (("patron_state", pstate), ("patron_bar", bar), ("patron_x", x), ("patron_variant", 0),
                 ("patron_frac", frac), ("patron_timer", 0), ("patron_aux", 0), ("patron_draw", 255),
                 ("patron_mug", 255), ("patron_hurry", 0)):
        put(gb, n, i, v)
    gb.write("patrons_live", gb.mem("patrons_live") + 1)


def inject_mug(gb, bar, x, st=1):
    i = list(gb.read("mug_state", MAX_M)).index(0)
    for n, v in (("mug_state", st), ("mug_bar", bar), ("mug_x", x), ("mug_timer", 0)):
        put(gb, n, i, v)
    gb.write("mugs_live", gb.mem("mugs_live") + 1)


def lose_a_life(gb):
    """A patron one step from the tap on the top bar."""
    gb.write("intro_timer", 0)
    set_patron(gb, 0, GAME["PATRON_FAR_X"] - 1, frac=255)       # takes its last pixel on the next frame
    run_until(gb, lambda: state(gb) == LIFE_LOST, 20)


def tilemap_row(gb, y, x0, n, window=False):
    return [t & 0xFF for t in gb.bg_tilemap(window)[y][x0:x0 + n]]   # PyBoy numbers the 0x8000 block from 256


# ---- title (M10a) -----------------------------------------------------------------------
import json as _json

TITLE_ART = _json.loads((ROOT / "build" / "title.json").read_text())   # tools/gen_art.py title_art(): tile ids
# the menu (owner 2026-10-11: submenus): the top level PLAY / BONUS / SETTINGS on rows 7, 9, 11; a submenu in the same
# place, its lines centred on row 9 (1 line: row 9; 2: rows 8, 10; 3: rows 7, 9, 11). PLAY: [CONTINUE] / STORY /
# ARCADE, BONUS: SOUNDTRACK, SETTINGS: MUSIC ON-OFF (row 9). The HI line on row 0 (the in-game HUD's row).
LOGO_ROW, ROW_MUSIC, ROW_HI = 2, 9, 0
TOP_ROWS = (7, 9, 11)
TOP_KEYS = ("play", "bonus", "settings")
SEL_PLAY, SEL_BONUS, SEL_SETTINGS = range(3)


def menu_rows(n):
    return tuple(10 - n + 2 * i for i in range(n))
LOGO_STATES = 5
OAM_TMUG, OAM_CURSOR = 4, 5
SCENE_TOP, SCENE_BOTTOM = 14 * 8, 17 * 8          # the bar scene: wall rows 14-15, counter row 16


def title_text_row(key):
    """The 20 tile ids of a menu line as the title draws it: blank, the string centred."""
    t = TITLE_ART["text"][key]
    row = [TITLE_ART["blank"]] * 20
    row[t["col"]:t["col"] + len(t["tiles"])] = t["tiles"]
    return row


def hi_tiles(digits):
    return [TITLE_ART["digits"][int(c)] for c in digits]


def hi_shown(gb):
    return tilemap_row(gb, ROW_HI, 8, 6)


def music_line(gb):
    """The MUSIC line (SETTINGS' only line, row 9)."""
    return tilemap_row(gb, ROW_MUSIC, 0, 20)


def settle_title(gb):
    """Run until the logo has filled and sparkled."""
    run_until(gb, lambda: gb.mem("logo_done") == 1, 300)
    gb.run(2)


def most_per_scanline(gb):
    """Most 8x16 sprites on any one visible scanline."""
    count = [0] * 144
    for s in gb.oam():
        if s["y"] == 0 or s["y"] >= 160 or s["x"] == 0 or s["x"] >= 168:
            continue
        y = s["y"] - 16
        for ly in range(max(0, y), min(144, y + 16)):
            count[ly] += 1
    return max(count)


def test_boots_to_title(boot):
    assert state(boot) == TITLE
    assert not boot.is_blank()
    settle_title(boot)
    # SPIGOTEER: 9 letters of 2x2 tiles at columns 1..18 (E twice), the final art once the logo has filled
    ids = [tile_id("TITLE_" + c) for c in "SPIGOTEER"]
    assert tilemap_row(boot, LOGO_ROW, 1, 18) == [i + k for i in ids for k in (0, 1)]
    assert tilemap_row(boot, LOGO_ROW + 1, 1, 18) == [i + k for i in ids for k in (2, 3)]
    check_golden(boot, "title")


def menu_block_rows(gb):
    return [tilemap_row(gb, y, 0, 20) for y in range(LOGO_ROW + 2, 14)]


def expect_menu(gb, keys):
    """The menu block (rows 4-13) shows exactly these lines, centred on row 9, and the plain wall around them."""
    blank = TITLE_ART["blank"]
    rows = dict(zip(menu_rows(len(keys)), keys))
    want = [title_text_row(rows[y]) if y in rows else [blank] * 20 for y in range(LOGO_ROW + 2, 14)]
    assert menu_block_rows(gb) == want, keys


def cursor_on(gb, key, row):
    c = gb.oam()[OAM_CURSOR]
    assert c["y"] - 16 + 7 == row * 8, "the mug stands on the selected line"
    assert TITLE_ART["text"][key]["x"] - 14 <= c["x"] - 8 <= TITLE_ART["text"][key]["x"] - 12, "just left of it"


def test_title_menu_is_centred_without_bands(boot):
    blank = TITLE_ART["blank"]
    assert boot.mem("title_menu") == TM_TOP and menu_items(boot) == [K_PLAY, K_BONUS, K_SETTINGS]
    expect_menu(boot, TOP_KEYS)
    # the HI line on row 0: 8 tiles at columns 6..13 (a small "HI", a space, six digits)
    assert tilemap_row(boot, ROW_HI, 0, 20) == [blank] * 6 + [TITLE_ART["hi"], blank] + hi_tiles("000000") + [blank] * 6
    # every line centred to the pixel: as many px left of the text as right of it. An odd-length line is drawn
    # 4 px right inside one more tile, so its tiles are an even count with as many blank columns either side.
    for key, s in (("arcade", "ARCADE"), ("story", "STORY"), ("music_on", "MUSIC ON"), ("music_off", "MUSIC OFF"),
                   ("continue", "CONTINUE"), ("bonus", "BONUS"), ("play", "PLAY"), ("settings", "SETTINGS"),
                   ("soundtrack", "SOUNDTRACK")):
        t = TITLE_ART["text"][key]
        n = len(t["tiles"])
        assert n % 2 == 0 and t["col"] == (20 - n) // 2, key
        left = t["x"] - 1                       # the first glyph cell's left edge (its text starts 1 px in)
        assert left == 160 - (left + 8 * len(s)), f"{key}: {left} px left, {160 - left - 8 * len(s)} px right"
    assert all(tile_id("HUD_BLANK") not in tilemap_row(boot, y, 0, 20) for y in range(18)), "no bands"


def test_up_down_move_the_mug_cursor_and_wrap(boot):
    boot.run(2)
    assert boot.mem("title_sel") == SEL_PLAY
    seen = []
    for b in ("down", "down", "down", "up", "up"):
        boot.press(b, 2)
        boot.run(1)
        sel = boot.mem("title_sel")
        seen.append(sel)
        cursor_on(boot, TOP_KEYS[sel], TOP_ROWS[sel])
    assert seen == [SEL_BONUS, SEL_SETTINGS, SEL_PLAY, SEL_SETTINGS, SEL_BONUS]
    assert state(boot) == TITLE and boot.mem("title_menu") == TM_TOP


# (top item, its submenu, the submenu's lines without a story save)
SUBMENUS = [(K_PLAY, TM_PLAY, ("story", "arcade", "classic")), (K_BONUS, TM_BONUS, ("soundtrack",)),
            (K_SETTINGS, TM_SETTINGS, ("music_on",))]


@pytest.mark.parametrize("top,menu,keys", SUBMENUS, ids=["play", "bonus", "settings"])
def test_each_submenu_opens_in_place_and_b_comes_back_to_its_item(boot, top, menu, keys):
    settle_title(boot)
    title_pick(boot, top)
    boot.run(MENU_SETTLE)
    assert state(boot) == TITLE and boot.mem("title_menu") == menu and boot.mem("title_sel") == 0
    expect_menu(boot, keys)
    cursor_on(boot, keys[0], menu_rows(len(keys))[0])
    if len(keys) > 1:                           # Up / Down move and wrap in a submenu too
        menu_tap(boot, "up")
        assert boot.mem("title_sel") == len(keys) - 1
        cursor_on(boot, keys[-1], menu_rows(len(keys))[-1])
    check_golden(boot, "title_" + TOP_KEYS[menu - 1])
    menu_tap(boot, "b")
    boot.run(MENU_SETTLE)
    assert state(boot) == TITLE and boot.mem("title_menu") == TM_TOP
    assert boot.mem("title_sel") == menu - 1, "the cursor back on the item the submenu came from"
    expect_menu(boot, TOP_KEYS)
    cursor_on(boot, TOP_KEYS[menu - 1], TOP_ROWS[menu - 1])
    menu_tap(boot, "b")                         # B on the top level does nothing
    assert boot.mem("title_menu") == TM_TOP and boot.mem("title_sel") == menu - 1


def test_submenu_redraws_stay_within_the_vblank_drain_budget(boot):
    """Switching menus queues its rows a few a frame: the drain stays as short as gameplay's (test_patrons: <= 12
    DIV ticks) and ends before line 0, even with a cursor move during the redraw."""
    from test_scores import booted, v7_image
    with booted(boot.model_name, v7_image([], story=3, step=1)) as rom:
        rom.write("drain_ticks_max", 0)
        for top in (K_PLAY, K_BONUS, K_SETTINGS):
            title_pick(rom, top)
            rom.press("down", 1)                      # straight into the redraw
            rom.run(MENU_SETTLE)
            menu_tap(rom, "b")
            rom.press("up", 1)
            rom.run(MENU_SETTLE)
            menu_tap(rom, "down")
        assert 0 < rom.mem("drain_ticks_max") <= 12, rom.mem("drain_ticks_max")
        assert rom.mem16("vq_late") == 0 and rom.mem("vq_end_ly_max") <= 153


def test_continue_shows_only_with_a_story_save(boot):
    from test_scores import booted, v7_image
    title_pick(boot, K_PLAY)
    boot.run(MENU_SETTLE)
    assert menu_items(boot) == [K_STORY, K_ARCADE, K_CLASSIC]
    expect_menu(boot, ("story", "arcade", "classic"))
    with booted(boot.model_name, v7_image([], story=3, step=1)) as rom:
        rom.model_name = boot.model_name
        settle_title(rom)
        assert menu_items(rom) == [K_PLAY, K_BONUS, K_SETTINGS], "the top level is the same with a save"
        expect_menu(rom, TOP_KEYS)
        title_pick(rom, K_PLAY)
        rom.run(MENU_SETTLE)
        assert menu_items(rom) == [K_CONTINUE, K_STORY, K_ARCADE, K_CLASSIC], "CONTINUE first, then STORY, ARCADE"
        expect_menu(rom, ("continue", "story", "arcade", "classic"))
        cursor_on(rom, "continue", 6)                    # (the golden title_continue: tests/test_story.py)
    with booted(boot.model_name, v7_image([], story=10)) as rom:    # the story finished: nothing to continue
        title_pick(rom, K_PLAY)
        assert menu_items(rom) == [K_STORY, K_ARCADE, K_CLASSIC]


def test_start_works_as_a_too(boot):
    boot.press("start", 2)                    # PLAY
    boot.run(1)
    assert boot.mem("title_menu") == TM_PLAY
    boot.press("down", 2)                     # ARCADE
    boot.run(1)
    boot.press("start", 2)
    run_until(boot, lambda: state(boot) == GS_GOAL, 30)
    assert boot.mem("play_mode") == 0 and boot.mem("story_arc") == 1 and boot.mem("lives") == 3 and score(boot) == 0


def test_play_arcade_starts_the_saloon_s_opening_shift_with_no_scene(boot):
    """The three modes: ARCADE is the story's playable sequence, arcade style (tests/test_arcade.py has the rest)."""
    settle_title(boot)
    title_arcade(boot)
    run_until(boot, lambda: state(boot) == GS_GOAL, 30)
    assert boot.mem("play_mode") == 0 and boot.mem("story_on") == 1 and boot.mem("story_arc") == 1
    assert boot.mem("story_chapter") == 0 and boot.mem("story_shift") == 0 and boot.mem("level") == 1
    assert boot.mem("cur_group") == 0 and boot.mem("lives") == 3
    boot.run(5)
    spr = boot.visible_sprites()                  # (under the goal banner his lower half is hidden)
    assert spr and all(o["tile"] < 56 for o in spr), "only the bartender: the title's sprites are gone"


def test_play_classic_starts_the_old_rotation_as_a_stand_in(boot):
    """Until CLASSIC is built (P5), PLAY > CLASSIC plays the old 10-level rotation, with extra lives and its own top 5."""
    title_pick(boot, K_PLAY, K_CLASSIC)
    run_until(boot, lambda: state(boot) == PLAYING, 30)
    assert boot.mem("play_mode") == 2 and boot.mem("story_on") == 0 and boot.mem("level") == 1
    assert int.from_bytes(boot.read("extra_at", 4), "little") == 20000
    assert patrons(boot) == [(0, ENTRY_X), (2, ENTRY_X)]


@pytest.mark.parametrize("lvl", [1, 7, 23])
def test_the_level_harness_starts_any_level_on_the_same_frame_as_the_menu_did(boot, lvl):
    """tests/conftest.py title_level: the title's test hook title_go starts the old 10-level rotation (MODE_LEVEL) at lvl,
    on the frame A is pressed on PLAY's ARCADE line (the hook is taken before the menu sees the key)."""
    title_level(boot, lvl)
    assert boot.mem("title_go") == 0, "taken"
    run_until(boot, lambda: state(boot) == PLAYING or state(boot) == GS_LOOP, 30)
    assert boot.mem("play_mode") == 3 and boot.mem("story_on") == 0
    assert boot.mem("level") == lvl and boot.mem("cur_group") == (lvl - 1) % ROWS and boot.mem("lives") == 3
    assert boot.mem("arcade_loop") == (lvl - 1) // ROWS + 1


def test_story_starts_the_story_mode(boot):
    """M11b (was M10a's COMING SOON): PLAY > STORY opens the story's first cut-scene (tests/test_story.py has the rest)."""
    title_pick(boot, K_PLAY, K_STORY)
    run_until(boot, lambda: state(boot) == GS_STORY, 30)
    assert boot.mem("story_on") == 1 and boot.mem("story_scene") == 0, "INTRO"


def test_music_toggles_from_the_settings(boot):
    title_pick(boot, K_SETTINGS)
    boot.run(MENU_SETTLE)
    assert menu_items(boot) == [K_MUSIC] and music_line(boot) == title_text_row("music_on")
    menu_tap(boot, "a")
    boot.run(2)
    assert boot.mem("sound_on") == 0 and music_line(boot) == title_text_row("music_off")
    cursor_on(boot, "music_off", ROW_MUSIC)
    boot.press("start", 2)
    boot.run(2)
    assert boot.mem("sound_on") == 1 and music_line(boot) == title_text_row("music_on")
    assert state(boot) == TITLE and boot.mem("title_menu") == TM_SETTINGS


def test_music_off_from_the_settings_holds_into_a_game(boot):
    """The setting behaves as the old MUSIC line did: it holds for the session (not in SRAM, as before)."""
    title_pick(boot, K_SETTINGS, K_MUSIC)
    assert boot.mem("sound_on") == 0
    menu_tap(boot, "b")
    title_arcade(boot)
    run_until(boot, lambda: state(boot) == PLAYING, 30)
    assert boot.mem("sound_on") == 0, "the game starts with the music off"


def test_select_toggles_the_music_on_any_menu_level(boot):
    menu_tap(boot, "select")
    assert boot.mem("sound_on") == 0, "the top level (no MUSIC line shown)"
    title_pick(boot, K_SETTINGS)
    boot.run(MENU_SETTLE)
    assert music_line(boot) == title_text_row("music_off"), "SETTINGS opens on the current setting"
    menu_tap(boot, "select")
    boot.run(2)
    assert boot.mem("sound_on") == 1 and music_line(boot) == title_text_row("music_on")


def test_title_ignores_other_buttons(boot):
    for b in ("b", "left", "right"):
        boot.press(b, 3)
    boot.run(10)
    assert state(boot) == TITLE and boot.mem("title_sel") == SEL_PLAY and boot.mem("title_menu") == TM_TOP


def test_logo_fills_letter_by_letter_then_settles(boot):
    seen = []
    for _ in range(200):
        seen.append(tuple(boot.read("logo_state", 9)))
        if boot.mem("logo_done"):
            break
        boot.run(1)
    assert boot.mem("logo_done") == 1
    assert all(list(s) == sorted(s, reverse=True) for s in seen), "letter by letter, left to right"
    assert all(a <= b for s0, s1 in zip(seen, seen[1:]) for a, b in zip(s0, s1)), "it only ever fills up"
    assert len(set(seen)) >= 10, "in many small steps"
    final = tilemap_row(boot, LOGO_ROW, 1, 18)
    boot.run(120)
    assert tilemap_row(boot, LOGO_ROW, 1, 18) == final, "settled"
    assert tuple(boot.read("logo_state", 9)) == (LOGO_STATES - 1,) * 9


def test_logo_starts_empty_and_fills_mid_animation(boot):
    # a fresh boot, caught as the title appears and 40 frames later (the golden title_anim)
    from gbtools import Rom
    from conftest import ROM
    with Rom(ROM, boot.model_name) as gb:
        gb.model_name = boot.model_name
        run_until(gb, lambda: gb.mem16("title_t") >= 1, 300)
        empty = [TITLE_ART["logo"][c][0] for c in "SPIGOTEER"]
        assert tilemap_row(gb, LOGO_ROW + 1, 1, 18) == [q[k] for q in empty for k in (2, 3)]
        run_until(gb, lambda: gb.mem16("title_t") >= 40, 100)
        gb.run(1)                             # (the frame's tilemap writes land in the next VBlank)
        st = list(gb.read("logo_state", 9))
        assert st[0] == LOGO_STATES - 1 and 0 < max(st[3:6]) < LOGO_STATES - 1 and st[-1] == 0, st
        row = tilemap_row(gb, LOGO_ROW + 1, 1, 18)
        assert row == [TITLE_ART["logo"][c][st[i]][2 + k] for i, c in enumerate("SPIGOTEER") for k in (0, 1)]
        check_golden(gb, "title_anim")


def test_bar_scene_slides_a_mug_and_loops(boot):
    phases, xs, loops0 = [], [], boot.mem("tscene_loops")
    for _ in range(700):
        boot.run(1)
        phases.append(boot.mem("tscene_phase"))
        mug = boot.oam()[OAM_TMUG]
        if 1 <= phases[-1] <= 4 and phases[-3:] == [phases[-1]] * 3:     # (OAM shows the frame before)
            assert mug["y"] != 0, "the mug is on screen while it travels"
            assert SCENE_TOP <= mug["y"] - 16 < SCENE_BOTTOM
        if phases[-1] in (1, 4) and phases[-3:] == [phases[-1]] * 3:
            xs.append((phases[-1], mug["x"] - 8))
    out = [x for p, x in xs if p == 1]
    back = [x for p, x in xs if p == 4]
    assert out[0] > out[-1] and back[-1] > back[0], "slides to the patron, the empty comes back"
    assert boot.mem("tscene_loops") >= loops0 + 2, "and again"
    assert set(phases) == set(range(6))


def test_title_sprites_stay_within_ten_per_line(boot):
    worst = 0
    for _ in range(400):
        boot.run(1)
        worst = max(worst, most_per_scanline(boot))
    assert 3 <= worst <= 10, worst


# ---- pause ---------------------------------------------------------------------------
def test_pause_toggles_and_freezes(gb):
    gb.write("intro_timer", 0)
    gb.write("spawn_timer", 255)
    inject_mug(gb, 2, 120)
    gb.run(45)
    assert state(gb) == PLAYING
    gb.press("start", 2)
    assert state(gb) == PAUSED and gb.mem("overlay_on") == 1
    gb.run(5)
    before = (patrons(gb), mugs(gb), gb.mem("bartender_x"), score(gb), gb.mem("intro_timer"))
    gb.hold("left")
    gb.run(100)
    gb.release("left")
    assert (patrons(gb), mugs(gb), gb.mem("bartender_x"), score(gb), gb.mem("intro_timer")) == before
    assert state(gb) == PAUSED
    check_golden(gb, "pause")
    gb.press("start", 2)
    assert state(gb) == PLAYING and gb.mem("overlay_on") == 0
    gb.run(60)
    assert patrons(gb) != before[0] and mugs(gb) != before[1]


# ---- lost life -----------------------------------------------------------------------
def test_lost_life_freezes_then_restarts_the_bars(gb):
    gb.press("down", 2)
    gb.press("down", 2)
    gb.hold("left"); gb.run(10); gb.release("left")
    inject_mug(gb, 3, 100)
    lose_a_life(gb)
    assert gb.mem("lives") == 2
    gb.run(2)
    assert gb.mem("bartender_frame") == BT_FAIL
    frozen = (patrons(gb), gb.mem("bartender_x"), gb.mem("bar"))
    gb.run(100)
    assert state(gb) == LIFE_LOST and (patrons(gb), gb.mem("bartender_x"), gb.mem("bar")) == frozen
    run_until(gb, lambda: state(gb) == PLAYING, 40)
    assert gb.mem("lives") == 2
    assert mugs(gb) == [] and gb.mem("mugs_live") == 0
    assert patrons(gb) == [(0, ENTRY_X), (2, ENTRY_X)] and gb.mem("spawned") == 2
    assert gb.mem("bar") == 0 and gb.mem("bartender_x") == GAME["TAP_X"] and gb.mem("bartender_frame") == 0
    assert gb.mem("intro_timer") >= 85
    gb.run(30)
    assert patrons(gb) == [(0, ENTRY_X), (2, ENTRY_X)], "intro delay holds"
    assert len([s for s in gb.visible_sprites()]) == 4, "only the bartender is on screen"
    # the tilemap shows exactly the re-placed patrons: no ghost of the one at the tap
    assert tilemap_row(gb, bar_top_row(0), 14, 4)[:3] == tilemap_row(gb, bar_top_row(2), 14, 4)[:3]


def test_lost_life_glass_animation_completes(gb):
    gb.write("intro_timer", 255)
    for i in range(MAX_P):
        put(gb, "patron_state", i, 0)             # nobody to catch it
    inject_mug(gb, 0, 17)
    gb.run(4)
    assert state(gb) == LIFE_LOST and [m for m in gb.read("mug_state", MAX_M) if m == 3]
    gb.run(40)
    assert state(gb) == LIFE_LOST and gb.mem("mugs_live") == 0, "glass finished while frozen"


def test_served_count_persists_across_a_lost_life(gb):
    gb.write("intro_timer", 255)
    inject_mug(gb, 0, ENTRY_X + 8)                        # next to the patron at ENTRY_X: served
    gb.run(6)
    assert gb.mem("served") == 1 and score(gb) == 50
    lose_a_life(gb)
    run_until(gb, lambda: state(gb) == PLAYING, 200)
    assert gb.mem("served") == 1 and gb.mem("lives") == 2
    assert len(patrons(gb)) == 2 and gb.mem("spawned") == 3
    # only quota - served may be placed again
    gb.write("quota", 2)
    lose_a_life(gb)
    run_until(gb, lambda: state(gb) == PLAYING, 200)
    assert len(patrons(gb)) == 1 and gb.mem("spawned") == 2 and gb.mem("served") == 1


# ---- level clear ---------------------------------------------------------------------
def clear_level(gb):
    gb.write("intro_timer", 255)
    gb.write("quota", 2)                        # level 1 starts with two patrons: bars 0 and 2
    for b in (0, 2):
        inject_mug(gb, b, ENTRY_X + 8)
    run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 60)     # (the served patrons slide out past the left edge first)


def test_level_clear_scores_shows_banner_and_loads_level_2(gb):
    gb.press("down", 2)
    clear_level(gb)
    assert score(gb) == 2 * 50 + 1000 and gb.mem("overlay_on") == 1
    gb.run(10)
    msg = tilemap_row(gb, 1, 0, 20, window=True)
    assert msg.count(tile_id("HUD_BLANK")) == 10 and msg[4] == tile_id("GLYPH_L")
    assert tilemap_row(gb, 0, 0, 20, window=True) == [tile_id("PANEL_TOP")] * 20
    run_until(gb, lambda: state(gb) == PLAYING, 200)
    assert gb.mem("level") == 2 and gb.mem("cur_group") == 1 and gb.mem("overlay_on") == 0
    assert gb.mem("lives") == 3 and score(gb) == 1100
    assert (gb.mem("quota"), gb.mem("step_frames"), gb.mem("serve_score")) == (10, 60, 75)
    assert patrons(gb) == [(0, ENTRY_X), (1, ENTRY_X), (2, ENTRY_X)] and gb.mem("bar") == 0 and mugs(gb) == []
    gb.run(15)
    assert tilemap_row(gb, LAYOUT["HUD_ROW"], 17, 3) == [tile_id("GLYPH_L"), tile_id("GLYPH_0"), tile_id("GLYPH_2")]   # L02
    base = int(re.search(r"PATRON_FIRST_TILE (\d+)", ART_H).group(1))
    vram = b"".join(bytes(gb.read((0x9000 + t * 16) if t < 128 else (0x8800 + (t - 128) * 16), 16))   # LCDC bit 4 = 0: ids 0..127 at 0x9000, 128..255 at 0x8800
                    for t in range(base, base + PATRON_TILES))
    assert vram == patron_group_tiles(1), "the sports group is in VRAM"
    check_golden(gb, "level2")


def test_level_clear_banner_is_the_window(gb):
    clear_level(gb)
    gb.run(5)
    r = gb.regs()
    assert r["WY"] == 64 and r["WX"] == 7
    assert gb.mem("overlay_on") == 1


# ---- game over -----------------------------------------------------------------------
def test_three_lost_lives_end_the_game_and_start_goes_on_to_the_title(gb):
    gb.write("intro_timer", 255)
    inject_mug(gb, 0, ENTRY_X + 8)
    gb.run(6)
    assert score(gb) == 50
    for n in range(3):
        lose_a_life(gb)
        assert gb.mem("lives") == 2 - n
        if n < 2:
            run_until(gb, lambda: state(gb) == PLAYING, 200)
    run_until(gb, lambda: state(gb) == GAME_OVER, 200)
    assert gb.mem("game_over") == 1 and hi_score(gb) == 50 and gb.mem("overlay_on") == 1
    gb.run(10)
    check_golden(gb, "gameover")
    x = gb.mem("bartender_x")
    gb.press("left", 5)
    assert state(gb) == GAME_OVER and gb.mem("bartender_x") == x
    gb.press("start", 2)                                # M10b: 50 makes the top 5: initials, A saves, the table
    run_until(gb, lambda: state(gb) == GS_INITIALS, 30)
    gb.press("a", 2)
    run_until(gb, lambda: state(gb) == GS_SCORES, 30)
    gb.press("start", 2)
    run_until(gb, lambda: state(gb) == TITLE, 30)       # the redraw runs with the LCD off and takes a few frames
    gb.run(3)
    assert hi_score(gb) == 50
    assert hi_shown(gb) == hi_tiles("000050"), "title shows the HI score"
    assert gb.mem("title_menu") == TM_TOP, "the top level"
    title_level(gb)
    run_until(gb, lambda: state(gb) == PLAYING, 30)
    assert gb.mem("lives") == 3 and score(gb) == 0 and hi_score(gb) == 50 and gb.mem("game_over") == 0


def test_lower_score_keeps_the_hi_score(gb):
    gb.write("hi_score", 5000 & 0xFF)
    gb.write(gb.addr("hi_score") + 1, 5000 >> 8)
    for n in range(3):
        lose_a_life(gb)
        run_until(gb, lambda: state(gb) in (PLAYING, GAME_OVER) and gb.mem("game_state") != LIFE_LOST, 200)
    assert state(gb) == GAME_OVER and hi_score(gb) == 5000


# ---- level table ---------------------------------------------------------------------
def loop_row(lvl):
    """M10b: the level table row of level lvl with its arcade loop's difficulty (see src/level.c start_level)."""
    row = list(TABLE[(lvl - 1) % ROWS])
    k = min((lvl - 1) // ROWS, 3)
    row[4] -= row[4] * (8 * k) // 100                      # spawn interval -8 % per loop, cap -24 %
    row[8] = max(80, row[8] - 5 * k)                       # empty gap -5 frames per loop, never below 80
    return row


def test_level_table_and_wrap(gb):
    for lvl in range(1, 13):
        row = loop_row(lvl)                     # M10b: level 11 is venue 0 again (loop 2), a little harder
        assert gb.mem("level") == lvl
        assert gb.mem("cur_group") == (lvl - 1) % ROWS
        assert (gb.mem("quota"), gb.mem16("spawn_interval"), gb.mem("step_frames"), gb.mem("pushback_cols"),
                gb.mem("serve_score")) == (row[3], row[4], row[5], row[6], row[7]), lvl
        assert gb.mem("start_mask") == row[1]
        assert gb.mem("empty_gap") == row[8], lvl                # M8a: fair empties, 120 frames at L1 down to 80
        assert len(patrons(gb)) == bin(row[1]).count("1") * row[2], lvl
        assert tilemap_row(gb, LAYOUT["HUD_ROW"], 18, 2) == [tile_id("GLYPH_0") + lvl // 10, tile_id("GLYPH_0") + lvl % 10]
        gb.write("level_clear", 1)
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 5)
        run_until(gb, lambda: state(gb) in (PLAYING, BONUS), 400)     # (the LOOP 2 banner before level 11)
        if state(gb) == BONUS:                  # M6: even levels are followed by the bonus round; jump to its last frame
            gb.write("bonus_phase", 4)
            gb.write("bonus_timer", 129)
            run_until(gb, lambda: state(gb) == PLAYING, 200)          # (after level 10: the LOOP 2 banner)
        gb.run(2)
