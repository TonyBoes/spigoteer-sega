# M4.7: smooth patrons (pixel positions, pre-shifted BG tiles) and the drinking animation.
import re

import pytest
from conftest import ROOT, bar_top_row, bar_top_y, check_golden

import test_patrons as tp
from test_patrons import (DRINKING, EMPTY, FREE, FULL, HELD, MAX_M, MAX_P, PUSHED, PX, WALKING, clear_patrons,
                          drawn_tiles, freeze, go, hold_mug, inject_mug, map_ids, mugs, patrons, put, set_patron)

pytestmark = pytest.mark.timeout(90)

ART_H = (ROOT / "build" / "art.h").read_text()


def define(name):
    return int(re.search(rf"#define {name} (\d+)", ART_H).group(1))


OBJ_DRINK = (define("BARTENDER_TILE_COUNT") + define("MUG_TILE_COUNT") + define("GLASS_TILE_COUNT")
             + define("MUG_FILL_TILE_COUNT"))
DRINK_TILES = range(OBJ_DRINK, OBJ_DRINK + define("MUG_DRINK_TILE_COUNT"))


def drawn(gb, i):
    return gb.read("patron_draw", MAX_P)[i]


def drink_sprites(gb):
    return [s for s in gb.visible_sprites() if s["tile"] in DRINK_TILES]


def test_walking_drawn_x_advances_in_2_px_steps(gb):
    go(gb)
    ps = patrons(gb)
    last = {p["i"]: drawn(gb, p["i"]) for p in ps}
    changes = 0
    for _ in range(200):
        gb.run(1)
        for p in ps:
            d = drawn(gb, p["i"])
            assert d % 2 == 0
            assert 0 <= d - last[p["i"]] <= 2, f"drawn x jumped {last[p['i']]} -> {d}"
            changes += d != last[p["i"]]
            last[p["i"]] = d
    assert changes >= 2 * 10, "about 25 px in 200 frames = 12 steps each"
    # the screen follows the drawn position without lagging more than a few frames
    for p in patrons(gb):
        col, ids = drawn_tiles(p["variant"], drawn(gb, p["i"]), p["bar"])
        assert map_ids(gb, p["bar"], col) == ids


def test_level_1_crossing_time_still_about_16_seconds(gb):
    """8 px per 64 frames: M8a, 120 px (to the spout) in 960 frames (16 s)."""
    assert gb.mem("patron_speed") == 32 and gb.mem("step_frames") == 64
    clear_patrons(gb)
    go(gb)
    set_patron(gb, 0, 0)
    n = 0
    while gb.mem("lives") == 3 and n < 1200:
        gb.run(1)
        n += 1
    assert 955 <= n <= 965, n


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


def test_pushed_out_through_the_door_is_served(gb):
    clear_patrons(gb)
    freeze(gb)
    p = set_patron(gb, 1, 20)
    inject_mug(gb, 1, 30)
    for _ in range(8):
        gb.run(1)
        if gb.read("patron_state", MAX_P)[p] == PUSHED:
            break
    x0 = gb.read("patron_x", MAX_P)[p]
    gb.run(x0 - 2)
    assert gb.read("patron_state", MAX_P)[p] == PUSHED and gb.mem("served") == 0
    gb.run(6)
    assert gb.read("patron_state", MAX_P)[p] == 0 and gb.mem("served") == 1 and tp.score(gb) == 50
    assert mugs(gb) == []


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
    for t in range(95):
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
    base = gb.read("patron_x", MAX_P)[p] & 0xFE
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
        i = set_patron(gb, 0, 32 * k, state=DRINKING, timer=t)
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
        i = set_patron(gb, 0, 32 * k, state=DRINKING, timer=10)
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
