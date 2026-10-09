# M4: game flow. Title, pause, lost life, level clear, game over, level table.
import re

import pytest
from conftest import GAME, LAYOUT, ROOT, bar_top_row, check_golden

pytestmark = pytest.mark.timeout(120)

TITLE, PLAYING, LIFE_LOST, LEVEL_CLEAR, GAME_OVER, PAUSED, BONUS = range(7)
MAX_P, MAX_M = 16, 20
BT_FAIL = 6

# (group, start bar mask, start per bar, quota, spawn interval, step frames, pushback, serve score, empty gap)
TABLE = [
    (0, 0x5, 1, 8, 300, 64, 4, 50, 120), (1, 0x7, 1, 10, 275, 60, 4, 75, 110), (2, 0xF, 1, 12, 250, 56, 4, 75, 100),
    (3, 0xF, 1, 14, 230, 52, 4, 100, 90), (4, 0xF, 1, 16, 210, 48, 3, 100, 80), (5, 0xF, 2, 18, 190, 44, 3, 125, 70),
    (6, 0xF, 2, 20, 175, 40, 3, 125, 60), (7, 0xF, 2, 21, 160, 37, 3, 150, 52), (8, 0xF, 2, 22, 150, 34, 3, 150, 45),
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
                 ("patron_mug", 255)):
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


# ---- title ---------------------------------------------------------------------------
def test_boots_to_title(boot):
    assert state(boot) == TITLE
    assert not boot.is_blank()
    assert all(s["y"] == 0 or s["y"] >= 160 for s in boot.oam()) or boot.visible_sprites() == []
    # SPIGOTEER: 9 letters of 2x2 tiles at columns 1..18 (E twice)
    ids = [tile_id("TITLE_" + c) for c in "SPIGOTEER"]
    assert tilemap_row(boot, 4, 1, 18) == [i + k for i in ids for k in (0, 1)]
    assert tilemap_row(boot, 5, 1, 18) == [i + k for i in ids for k in (2, 3)]
    check_golden(boot, "title")


def test_start_begins_a_game(boot):
    boot.press("start", 2)
    run_until(boot, lambda: state(boot) == PLAYING, 30)
    assert boot.mem("lives") == 3 and score(boot) == 0 and boot.mem("level") == 1
    assert patrons(boot) == [(0, 0), (2, 0)]          # level 1 starts on bars 0 and 2
    assert boot.mem("bar") == 0 and boot.mem("bartender_x") == GAME["TAP_X"]
    boot.run(20)
    assert tilemap_row(boot, LAYOUT["HUD_ROW"], 17, 3) == [tile_id("GLYPH_L"), tile_id("GLYPH_0"), tile_id("GLYPH_1")]   # L01


def test_title_ignores_other_buttons(boot):
    for b in ("a", "b", "up", "select"):
        boot.press(b, 3)
    boot.run(10)
    assert state(boot) == TITLE


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
    assert patrons(gb) == [(0, 0), (2, 0)] and gb.mem("spawned") == 2
    assert gb.mem("bar") == 0 and gb.mem("bartender_x") == GAME["TAP_X"] and gb.mem("bartender_frame") == 0
    assert gb.mem("intro_timer") >= 85
    gb.run(30)
    assert patrons(gb) == [(0, 0), (2, 0)], "intro delay holds"
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
    inject_mug(gb, 0, 8)                        # next to the patron at the door: served
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
        inject_mug(gb, b, 16)
    run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 30)


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
    assert patrons(gb) == [(0, 0), (1, 0), (2, 0)] and gb.mem("bar") == 0 and mugs(gb) == []
    gb.run(15)
    assert tilemap_row(gb, LAYOUT["HUD_ROW"], 17, 3) == [tile_id("GLYPH_L"), tile_id("GLYPH_0"), tile_id("GLYPH_2")]   # L02
    base = int(re.search(r"BAR_TILE_COUNT (\d+)", ART_H).group(1))
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
def test_three_lost_lives_end_the_game_and_start_returns_to_title(gb):
    gb.write("intro_timer", 255)
    inject_mug(gb, 0, 8)
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
    gb.press("start", 2)
    run_until(gb, lambda: state(gb) == TITLE, 30)       # the redraw runs with the LCD off and takes a few frames
    gb.run(3)
    assert hi_score(gb) == 50
    digits = [tile_id("GLYPH_0")] * 4 + [tile_id("GLYPH_5"), tile_id("GLYPH_0")]
    assert tilemap_row(gb, 12, 8, 6) == digits, "title shows the HI score"
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
def test_level_table_and_wrap(gb):
    for lvl in range(1, 12):
        row = TABLE[min(lvl, 9) - 1]
        assert gb.mem("level") == lvl
        assert gb.mem("cur_group") == (lvl - 1) % 9
        assert (gb.mem("quota"), gb.mem16("spawn_interval"), gb.mem("step_frames"), gb.mem("pushback_cols"),
                gb.mem("serve_score")) == (row[3], row[4], row[5], row[6], row[7]), lvl
        assert gb.mem("start_mask") == row[1]
        assert gb.mem("empty_gap") == row[8], lvl                # M8a: fair empties, 120 frames at L1 down to 45
        assert len(patrons(gb)) == bin(row[1]).count("1") * row[2], lvl
        assert tilemap_row(gb, LAYOUT["HUD_ROW"], 18, 2) == [tile_id("GLYPH_0") + lvl // 10, tile_id("GLYPH_0") + lvl % 10]
        gb.write("level_clear", 1)
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 5)
        run_until(gb, lambda: state(gb) in (PLAYING, BONUS), 200)
        if state(gb) == BONUS:                  # M6: even levels are followed by the bonus round; jump to its last frame
            gb.write("bonus_phase", 4)
            gb.write("bonus_timer", 129)
            run_until(gb, lambda: state(gb) == PLAYING, 40)
        gb.run(2)
