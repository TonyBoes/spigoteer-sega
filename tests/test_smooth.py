# M4.7: smooth patrons (pixel positions, pre-shifted BG tiles) and the drinking animation.
# M8b: 8 shifts, so a patron is drawn at every pixel (was 2 px steps); the BG tile budget.
import re

import pytest
from conftest import GAME, ROOT, bar_top_row, bar_top_y, check_golden, logical_tile

import test_patrons as tp
from test_patrons import (BACK_BASE, BASE, BG_TILES_TOTAL, DRINKING, EMPTY, FREE, FULL, HELD, MAX_M, MAX_P, PUSHED,
                          PX, WALKING, clear_patrons, drawn_tiles, freeze, go, hold_mug, inject_mug, map_ids, mugs, patrons, put, set_patron)

pytestmark = pytest.mark.timeout(90)

ENTRY_X = GAME["ENTRY_X"]
ART_H = (ROOT / "build" / "art.h").read_text()


def define(name):
    return int(re.search(rf"#define {name} (\d+)", ART_H).group(1))


OBJ_DRINK = (GAME["OBJ_BT_END"] + define("MUG_TILE_COUNT") + define("GLASS_TILE_COUNT")
             + define("MUG_FILL_TILE_COUNT"))
DRINK_TILES = range(OBJ_DRINK, OBJ_DRINK + define("MUG_DRINK_TILE_COUNT"))


def drawn(gb, i):
    return gb.read("patron_draw", MAX_P)[i]


def drink_sprites(gb):
    """The held-drink sprites (M13a: a DMG copy is reported as the tile it was made from)."""
    return [dict(s, tile=logical_tile(s["tile"])) for s in gb.visible_sprites() if logical_tile(s["tile"]) in DRINK_TILES]


def test_walking_drawn_x_advances_in_1_px_steps(gb):
    go(gb)
    ps = patrons(gb)
    last = {p["i"]: drawn(gb, p["i"]) for p in ps}
    changes = 0
    for _ in range(200):
        gb.run(1)
        for p in ps:
            d = drawn(gb, p["i"])
            assert 0 <= d - last[p["i"]] <= 1, f"drawn x jumped {last[p['i']]} -> {d}"
            changes += d != last[p["i"]]
            last[p["i"]] = d
    assert changes >= 2 * 20, "about 25 px in 200 frames = 25 steps each"
    # the screen follows the drawn position without lagging more than a few frames
    for p in patrons(gb):
        col, ids = drawn_tiles(p["variant"], drawn(gb, p["i"]), p["bar"])
        assert map_ids(gb, p["bar"], col) == ids


def test_level_1_crossing_time_still_about_16_seconds(gb):
    """M8a: 120 px (to the spout) in 960 frames (16 s). Door fix: the walk starts at ENTRY_X (104 px) at 28/256 px per
    frame: 951 frames, within 2% of the old 960 (and above the 15 s guarantee)."""
    assert gb.mem("patron_speed") == 28 and gb.mem("step_frames") == 64
    clear_patrons(gb)
    go(gb)
    set_patron(gb, 0, ENTRY_X)
    n = 0
    while gb.mem("lives") == 3 and n < 1200:
        gb.run(1)
        n += 1
    assert abs(n - 960) <= 0.02 * 960 and n >= 15 * 60, n


def test_pushed_patron_slides_one_px_per_frame(gb):
    clear_patrons(gb)
    freeze(gb)
    p = set_patron(gb, 1, 96)
    inject_mug(gb, 1, 110)
    for _ in range(10):
        gb.run(1)
        if gb.read("patron_state", MAX_P)[p] == PUSHED:
            break
    assert gb.read("patron_state", MAX_P)[p] == PUSHED
    xs = [gb.read("patron_x", MAX_P)[p]]
    for _ in range(PX - 1):
        gb.run(1)
        xs.append(gb.read("patron_x", MAX_P)[p])
    assert all(a - b == 1 for a, b in zip(xs, xs[1:])), xs
    assert xs[-1] == 96 - PX
    gb.run(1)
    assert gb.read("patron_state", MAX_P)[p] == DRINKING and gb.read("patron_x", MAX_P)[p] == xs[-1]


def test_a_push_off_the_screen_serves_him_and_slides_out(gb):
    """A patron at ENTRY_X (x + 16 = the push): caught, he slides out past the left edge (LEAVING) and is served, scored
    and removed only when all of him is off the screen."""
    clear_patrons(gb)
    freeze(gb)
    p = set_patron(gb, 1, ENTRY_X)
    gb.run(3)
    inject_mug(gb, 1, ENTRY_X + 10)
    for _ in range(8):
        gb.run(1)
        if gb.read("patron_state", MAX_P)[p] == 4:           # LEAVING
            break
    assert gb.read("patron_state", MAX_P)[p] == 4 and gb.mem("served") == 0 and tp.score(gb) == 0
    gb.run(ENTRY_X + 4)
    assert gb.read("patron_state", MAX_P)[p] == 4 and gb.mem("served") == 0, "still on the screen"
    gb.run(ENTRY_X)
    assert gb.read("patron_state", MAX_P)[p] == 0 and mugs(gb) == []
    assert gb.mem("served") == 1 and tp.score(gb) == 50


def catch_one(gb, bar=1, x=96):
    clear_patrons(gb)
    freeze(gb)
    p = set_patron(gb, bar, x, variant=1)
    inject_mug(gb, bar, x + 14)
    gb.run(2)
    assert gb.read("patron_state", MAX_P)[p] == PUSHED
    return p


def test_caught_mug_is_held_and_drawn_at_the_patron(gb):
    p = catch_one(gb)
    ms = mugs(gb)
    assert [m["state"] for m in ms] == [HELD] and gb.read("patron_mug", MAX_P)[p] == ms[0]["i"]
    assert gb.read("mug_patron", MAX_M)[ms[0]["i"]] == p
    for _ in range(60):                           # while pushed back and then drinking
        gb.run(1)
        px = gb.read("patron_draw", MAX_P)[p]
        ss = drink_sprites(gb)
        assert len(ss) == 1, "the held mug is a sprite"
        s = ss[0]
        assert px <= s["x"] - 8 <= px + 16, (px, s)
        assert bar_top_y(1) <= s["y"] - 16 <= bar_top_y(1) + 8, "inside the bar's own 24 scanlines"
    assert gb.read("patron_state", MAX_P)[p] == DRINKING
    assert [m["state"] for m in mugs(gb)] == [HELD]


def test_drinking_mug_tilts_then_the_empty_slides_right(gb):
    p = catch_one(gb)
    tiles = []
    ys = []
    while gb.read("patron_state", MAX_P)[p] != DRINKING:
        gb.run(1)
    for t in range(95 + GAME["WINDUP_FRAMES"]):  # M8d: the empty is lowered in the wind-up, after the drink
        ss = drink_sprites(gb)
        if gb.read("patron_state", MAX_P)[p] == DRINKING:
            assert len(ss) == 1
            tiles.append(ss[0]["tile"] - OBJ_DRINK)
            ys.append(ss[0]["y"])
        gb.run(1)
    assert tiles[0] == 0 and 2 in tiles and 4 in tiles and tiles[-1] == 6, "upright, tilted, tipped, empty"
    assert tiles == sorted(tiles), "frames only advance"
    assert min(ys) < ys[0] and ys[-1] > min(ys), "rises to the mouth, then is lowered"
    ms = mugs(gb)
    assert len(ms) == 1 and ms[0]["state"] == EMPTY
    assert ms[0]["x"] >= gb.read("patron_x", MAX_P)[p] + 16
    x = ms[0]["x"]
    gb.run(6)
    assert mugs(gb)[0]["x"] == x + 3, "M8a: 0.5 px per frame"
    assert gb.read("patron_state", MAX_P)[p] == WALKING


def test_drinking_patron_sways_by_2_px(gb):
    p = catch_one(gb)
    while gb.read("patron_state", MAX_P)[p] != DRINKING:
        gb.run(1)
    seq = []
    for _ in range(80):
        d = drawn(gb, p)
        if not seq or seq[-1][0] != d:
            seq.append((d, 0))
        seq[-1] = (d, seq[-1][1] + 1)
        gb.run(1)
    xs = [d for d, _ in seq]
    base = gb.read("patron_x", MAX_P)[p]
    assert set(xs) == {base, base + 2}, xs
    assert len(xs) >= 6 and all(a != b for a, b in zip(xs, xs[1:]))
    assert all(n in (11, 12, 13) for _, n in seq[1:-1]), seq
    col, ids = drawn_tiles(1, drawn(gb, p), 1)
    assert map_ids(gb, 1, col) == ids


def test_held_mugs_count_against_the_per_bar_cap_and_the_scanline_limit(gb):
    """Worst case on one bar: 6 mugs (4 held at different poses + 2 sliding) + bartender (2 per line) + fill glass."""
    clear_patrons(gb)
    freeze(gb)
    for k, t in enumerate((0, 20, 40, 70)):
        i = set_patron(gb, 0, ENTRY_X + 32 * k, state=DRINKING, timer=t)
        hold_mug(gb, i, 0)
    inject_mug(gb, 0, 130)
    inject_mug(gb, 0, 120)
    gb.hold("a")
    gb.run(10)
    assert tp.mugs(gb) and len(tp.mugs(gb)) == 6
    spr = gb.visible_sprites()
    counts = [0] * 144
    for s in spr:
        top = s["y"] - 16
        for line in range(max(top, 0), min(top + 16, 144)):
            counts[line] += 1
    assert max(counts) <= 10, max(counts)
    for s in drink_sprites(gb):                   # no held mug leaves its own bar's 24 scanlines
        assert bar_top_y(0) <= s["y"] - 16 <= bar_top_y(0) + 8
    gb.release("a")


def test_spawn_mug_refuses_a_seventh_mug_when_held_ones_fill_the_bar(gb):
    clear_patrons(gb)
    freeze(gb)
    for k in range(5):
        i = set_patron(gb, 0, ENTRY_X + 32 * k, state=DRINKING, timer=10)
        hold_mug(gb, i, 0)
    gb.hold("a")
    gb.run(30)
    gb.release("a")
    gb.run(3)
    assert len(mugs(gb)) == 6 and gb.mem("mugs_live") == 6      # 5 held + the launched one
    gb.hold("a")
    gb.run(30)
    gb.release("a")
    gb.run(3)
    assert len([m for m in mugs(gb) if m["bar"] == 0]) <= 6


def test_drinking_golden(gb):
    p = catch_one(gb)
    while not (gb.read("patron_state", MAX_P)[p] == DRINKING and gb.read("patron_timer", MAX_P)[p] == 24):
        gb.run(1)
    assert [s["tile"] - OBJ_DRINK for s in drink_sprites(gb)] == [2]
    check_golden(gb, "drinking")


# ---- M8b: every pixel ------------------------------------------------------------------------
def test_drawn_x_follows_patron_x_every_pixel(gb):
    """A lone walker at 1 px per frame: drawn at exactly patron_x on every frame, every x in turn, and the tilemap
    shows the matching pre-shifted tiles (a frame behind at most: the copy goes out in the next VBlank)."""
    clear_patrons(gb)
    go(gb)
    p = set_patron(gb, 2, ENTRY_X + 3, variant=1)
    gb.run(2)
    xs, exact = [], 0
    # (patron_x and patron_draw are compared where the game's frame ends, vq_frame_end: the emulator's frame boundary
    # can fall in the middle of the game's update, between the two writes)
    snap = []
    a = gb.addr("vq_frame_end")
    gb.pb.hook_register(a >> 16, a & 0xFFFF, lambda _: snap.append((gb.read("patron_x", MAX_P)[p], drawn(gb, p))), None)
    for _ in range(40):
        gb.write("patron_speed", 255)              # ~1 px per frame
        gb.run(1)
        x = gb.read("patron_x", MAX_P)[p]
        assert snap and snap[-1][0] == snap[-1][1], snap[-3:]
        xs.append(x)
        now = drawn_tiles(1, x, 2)
        before = drawn_tiles(1, x - 1, 2)
        if map_ids(gb, 2, now[0]) == now[1]:
            exact += 1
        else:                                      # one frame behind at most
            assert map_ids(gb, 2, before[0]) == before[1], (x, map_ids(gb, 2, now[0]))
    assert len(set(xs)) >= 35 and all(0 <= b - a <= 1 for a, b in zip(xs, xs[1:])), xs
    assert {x & 7 for x in xs} == set(range(8)), "every shift is used"
    assert exact >= 1


def test_tile_ids_for_an_odd_x(gb):
    clear_patrons(gb)
    freeze(gb)
    p = set_patron(gb, 1, 37, variant=2)
    gb.run(4)
    assert drawn(gb, p) == 37
    col, ids = drawn_tiles(2, 37, 1)
    assert col == 4 and ids[0][0] == BASE + 2 * 42 + 4 * 6, "variant C, shift 5 (M13a layout)"
    assert map_ids(gb, 1, col) == ids
    tm = gb.bg_tilemap()
    assert (tm[bar_top_row(1)][3] & 0xFF) < BASE and (tm[bar_top_row(1)][7] & 0xFF) < BASE, "wall either side"


def test_bg_tile_budget(gb):
    """Scene tiles + 140 shifted + 12 back-view patron tiles fit the 256 BG ids; the BG uses the signed 0x8800
    mode, so BG ids 128+ share VRAM with OBJ ids 128+, which no sprite uses (OBJ ids stay below 128)."""
    assert BG_TILES_TOTAL == BASE + 140 + 12 and BG_TILES_TOTAL <= 256, BG_TILES_TOTAL
    assert BACK_BASE == BASE + 140
    assert gb.regs()["LCDC"] & 0x10 == 0, "BG/window tile data at 0x8800 (signed ids)"
    clear_patrons(gb)
    freeze(gb)
    for b in range(4):                            # all three variants, odd and even shifts, everywhere
        set_patron(gb, b, ENTRY_X + 5 + 9 * b, variant=b % 3)
        set_patron(gb, b, 50 + 11 * b, variant=(b + 1) % 3)
        set_patron(gb, b, 95 + 3 * b, variant=(b + 2) % 3)
    gb.run(10)
    used = {t & 0xFF for row in gb.bg_tilemap()[:18] for t in row[:20]}
    assert max(used) < BG_TILES_TOTAL, max(used)
    assert all(s["tile"] < 128 or s["tile"] >= BG_TILES_TOTAL for s in gb.visible_sprites()), "no OBJ tile in the shared 0x8800 block"
    assert max(used) >= 128, "the patrons do reach into the shared block (so the OBJ rule matters)"
