# M4: game flow. Title, pause, lost life, level clear, game over, level table.
import re

import pytest
from conftest import GAME, LAYOUT, ROOT, bar_top_row, check_golden

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
    (0, 0x5, 1, 8, 300, 64, 4, 50, 120), (1, 0x7, 1, 10, 275, 60, 4, 75, 110), (2, 0xF, 1, 10, 269, 64, 4, 75, 108),
    (3, 0xF, 1, 11, 263, 63, 4, 100, 105), (4, 0xF, 1, 11, 256, 62, 4, 100, 102), (5, 0xF, 1, 12, 250, 61, 4, 125, 100),
    (6, 0xF, 1, 13, 237, 58, 4, 125, 93), (7, 0xF, 1, 15, 223, 56, 3, 150, 87), (8, 0xF, 1, 16, 210, 52, 3, 150, 80),
]
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
# the bonus menu: ARCADE / STORY / BONUS / MUSIC on rows 6-12 (with a story save CONTINUE after STORY: rows 5-13), the HI
# line on row 0 (the in-game HUD's row)
LOGO_ROW, ROW_ARCADE, ROW_STORY, ROW_BONUS, ROW_MUSIC, ROW_HI = 2, 6, 8, 10, 12, 0
MENU_ROWS = (ROW_ARCADE, ROW_STORY, ROW_BONUS, ROW_MUSIC)
MENU_KEYS = ("arcade", "story", "bonus", "music_on")
SEL_ARCADE, SEL_STORY, SEL_BONUS, SEL_MUSIC = range(4)
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


def test_title_menu_is_centred_without_bands(boot):
    blank = TITLE_ART["blank"]
    assert tilemap_row(boot, ROW_ARCADE, 0, 20) == title_text_row("arcade")
    assert tilemap_row(boot, ROW_STORY, 0, 20) == title_text_row("story")
    assert tilemap_row(boot, ROW_BONUS, 0, 20) == title_text_row("bonus")
    assert music_line(boot) == title_text_row("music_on")
    # the HI line on row 0: 8 tiles at columns 6..13 (a small "HI", a space, six digits)
    assert tilemap_row(boot, ROW_HI, 0, 20) == [blank] * 6 + [TITLE_ART["hi"], blank] + hi_tiles("000000") + [blank] * 6
    # every line centred to the pixel: as many px left of the text as right of it. An odd-length line is drawn
    # 4 px right inside one more tile, so its tiles are an even count with as many blank columns either side.
    for key, s in (("arcade", "ARCADE"), ("story", "STORY"), ("music_on", "MUSIC ON"), ("music_off", "MUSIC OFF"),
                   ("continue", "CONTINUE"), ("bonus", "BONUS")):
        t = TITLE_ART["text"][key]
        n = len(t["tiles"])
        assert n % 2 == 0 and t["col"] == (20 - n) // 2, key
        left = t["x"] - 1                       # the first glyph cell's left edge (its text starts 1 px in)
        assert left == 160 - (left + 8 * len(s)), f"{key}: {left} px left, {160 - left - 8 * len(s)} px right"
    # no bands: the menu block (rows 4-13) is the plain wall tile around the text, the old dark HUD band tile is gone
    for y in range(LOGO_ROW + 2, 14):
        row = tilemap_row(boot, y, 0, 20)
        assert row[:4] == [blank] * 4 and row[16:] == [blank] * 4, y
        if y not in MENU_ROWS + (ROW_HI,):
            assert row == [blank] * 20, y
    assert all(tile_id("HUD_BLANK") not in tilemap_row(boot, y, 0, 20) for y in range(18))


def test_up_down_move_the_mug_cursor_and_wrap(boot):
    boot.run(2)
    assert boot.mem("title_sel") == SEL_ARCADE
    seen = []
    for b in ("down", "down", "down", "up", "up"):
        boot.press(b, 2)
        boot.run(1)
        sel = boot.mem("title_sel")
        seen.append(sel)
        c = boot.oam()[OAM_CURSOR]
        key = MENU_KEYS[sel]
        assert c["y"] - 16 + 7 == MENU_ROWS[sel] * 8, "the mug stands on the selected line"
        assert TITLE_ART["text"][key]["x"] - 14 <= c["x"] - 8 <= TITLE_ART["text"][key]["x"] - 12, "just left of it"
    assert seen == [SEL_STORY, SEL_BONUS, SEL_MUSIC, SEL_BONUS, SEL_STORY]
    assert state(boot) == TITLE


def test_start_begins_a_game(boot):
    boot.press("start", 2)
    run_until(boot, lambda: state(boot) == PLAYING, 30)
    assert boot.mem("lives") == 3 and score(boot) == 0 and boot.mem("level") == 1
    assert patrons(boot) == [(0, ENTRY_X), (2, ENTRY_X)]          # level 1 starts on bars 0 and 2
    assert boot.mem("bar") == 0 and boot.mem("bartender_x") == GAME["TAP_X"]
    boot.run(20)
    assert tilemap_row(boot, LAYOUT["HUD_ROW"], 17, 3) == [tile_id("GLYPH_L"), tile_id("GLYPH_0"), tile_id("GLYPH_1")]   # L01


def test_a_on_arcade_starts_level_1(boot):
    settle_title(boot)
    boot.press("down", 2)
    boot.press("up", 2)
    boot.press("a", 2)
    run_until(boot, lambda: state(boot) == PLAYING, 30)
    assert boot.mem("level") == 1 and boot.mem("cur_group") == 0 and boot.mem("lives") == 3
    assert patrons(boot) == [(0, ENTRY_X), (2, ENTRY_X)]
    boot.run(5)
    assert len(boot.visible_sprites()) == 4, "only the bartender: the title's sprites are gone"


def test_story_starts_the_story_mode(boot):
    """M11b (was M10a's COMING SOON): STORY opens the story's first cut-scene (tests/test_story.py has the rest)."""
    boot.press("down", 2)
    boot.press("a", 2)
    run_until(boot, lambda: state(boot) == GS_STORY, 30)
    assert boot.mem("story_on") == 1 and boot.mem("story_scene") == 0, "INTRO"


def test_music_toggles_from_the_menu(boot):
    boot.press("up", 2)                       # wraps to MUSIC
    assert boot.mem("title_sel") == SEL_MUSIC
    boot.press("a", 2)
    boot.run(2)
    assert boot.mem("sound_on") == 0 and music_line(boot) == title_text_row("music_off")
    boot.press("start", 2)
    boot.run(2)
    assert boot.mem("sound_on") == 1 and music_line(boot) == title_text_row("music_on")
    assert state(boot) == TITLE


def test_title_ignores_other_buttons(boot):
    for b in ("b", "left", "right"):
        boot.press(b, 3)
    boot.run(10)
    assert state(boot) == TITLE and boot.mem("title_sel") == SEL_ARCADE


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
    gb.press("start", 2)
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
    row = list(TABLE[(lvl - 1) % 9])
    k = min((lvl - 1) // 9, 3)
    row[4] -= row[4] * (8 * k) // 100                      # spawn interval -8 % per loop, cap -24 %
    row[8] = max(80, row[8] - 5 * k)                       # empty gap -5 frames per loop, never below 80
    return row


def test_level_table_and_wrap(gb):
    for lvl in range(1, 12):
        row = loop_row(lvl)                     # M10b: level 10 is venue 0 again (loop 2), a little harder
        assert gb.mem("level") == lvl
        assert gb.mem("cur_group") == (lvl - 1) % 9
        assert (gb.mem("quota"), gb.mem16("spawn_interval"), gb.mem("step_frames"), gb.mem("pushback_cols"),
                gb.mem("serve_score")) == (row[3], row[4], row[5], row[6], row[7]), lvl
        assert gb.mem("start_mask") == row[1]
        assert gb.mem("empty_gap") == row[8], lvl                # M8a: fair empties, 120 frames at L1 down to 80
        assert len(patrons(gb)) == bin(row[1]).count("1") * row[2], lvl
        assert tilemap_row(gb, LAYOUT["HUD_ROW"], 18, 2) == [tile_id("GLYPH_0") + lvl // 10, tile_id("GLYPH_0") + lvl % 10]
        gb.write("level_clear", 1)
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 5)
        run_until(gb, lambda: state(gb) in (PLAYING, BONUS), 400)     # (the LOOP 2 banner before level 10)
        if state(gb) == BONUS:                  # M6: even levels are followed by the bonus round; jump to its last frame
            gb.write("bonus_phase", 4)
            gb.write("bonus_timer", 129)
            run_until(gb, lambda: state(gb) == PLAYING, 40)
        gb.run(2)
