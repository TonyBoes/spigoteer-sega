# Door fix: patrons come in at DOOR_X (just right of the 16 px door), are served out when pushed back past it, never
# draw over columns 0-1 of the wall rows, walk the shorter way in the same time, and a dust puff marks the door
# swinging when one enters or leaves.
import re

import pytest
from conftest import GAME, ROOT, bar_top_row, venue
from test_art import goto_group
from test_bonus import pick
from test_flow import PLAYING, BONUS, TABLE, run_until, state
from test_patrons import (DRINKING, MAX_P, PUSHED, WALKING, FAR_X, clear_patrons, freeze, go, hold_mug, inject_mug, mugs, patrons, put,
                          score, set_patron, spawn_now)

pytestmark = pytest.mark.timeout(120)

DOOR_X = GAME["DOOR_X"]
PUFF_TOTAL, PUFF_X, OAM_PUFF = GAME["PUFF_TOTAL"], GAME["PUFF_X"], GAME["OAM_PUFF"]
_ART_H = (ROOT / "build" / "art.h").read_text()
_BG_TOTAL = int(re.search(r"#define BAR_TILE_COUNT (\d+)", _ART_H).group(1)) + int(re.search(r"#define PATRON_GROUP_TILES (\d+)", _ART_H).group(1))
OBJ_PUFF = (_BG_TOTAL + 1) & ~1
PUFF_TILES = {OBJ_PUFF, OBJ_PUFF + 2, OBJ_PUFF + 4}


def door_tiles(gb, b):
    tm = gb.bg_tilemap()
    return [[t & 0xFF for t in tm[bar_top_row(b) + r][:2]] for r in range(2)]


def venue_door(group, b=0):
    m = venue(group)["bar_map"]
    return [m[r * 20:r * 20 + 2] for r in range(2)]


def puffs(gb):
    return [s for s in gb.visible_sprites() if s["tile"] in PUFF_TILES]


def drawn_xs(gb):
    d = gb.read("patron_draw", MAX_P)
    st = gb.read("patron_state", MAX_P)
    return [d[i] & 0x7F for i in range(MAX_P) if st[i] and d[i] != 255]


def test_door_x_is_the_door_width():
    assert DOOR_X == 16 and GAME["LEFT_LIMIT"] == 16


def test_a_spawned_patron_stands_at_door_x(gb):
    clear_patrons(gb)
    gb.write("quota", 5)
    gb.write("intro_timer", 0)
    spawn_now(gb)
    gb.run(2)
    ps = patrons(gb)
    assert len(ps) == 1 and ps[0]["x"] == DOOR_X and ps[0]["state"] == WALKING
    assert min(drawn_xs(gb)) >= DOOR_X


def test_spawn_waits_while_the_door_end_is_crowded(gb):
    """The spacing rule at the door: nobody spawns while a patron stands within PATRON_SPACING px of DOOR_X."""
    clear_patrons(gb)
    for b in range(4):
        set_patron(gb, b, DOOR_X + 31, state=DRINKING)     # 31 < 32 px from a patron at DOOR_X
    gb.write("quota", 9)
    gb.write("spawned", 4)
    gb.write("intro_timer", 0)
    spawn_now(gb)
    gb.run(40)
    assert gb.mem("spawned") == 4
    for b in range(4):
        put(gb, "patron_x", [p["i"] for p in patrons(gb) if p["bar"] == b][0], DOOR_X + 32)
    spawn_now(gb)
    gb.run(40)
    assert gb.mem("spawned") == 5


@pytest.mark.parametrize("group", [0, 3, 8])
def test_door_tiles_stay_intact_with_patrons_coming_and_going(gb, group):
    if group:
        goto_group(gb, group)
    gb.write("tip_chance", 0)
    clear_patrons(gb)
    gb.write("quota", 16)
    gb.write("intro_timer", 0)
    want = venue_door(group)
    seen_bars = set()
    for n in range(260):
        if n % 20 == 0:
            spawn_now(gb)
        gb.run(1)
        for p in patrons(gb):
            seen_bars.add(p["bar"])
        assert min(drawn_xs(gb) or [DOOR_X]) >= DOOR_X
        if n % 5 == 0:
            for b in range(4):
                assert door_tiles(gb, b) == want, (group, b, n)
    assert len(seen_bars) >= 3, "patrons entered on most bars"
    # serve one out through the door on every bar: the door stays whole while it is pushed out and after
    freeze(gb)
    for b in range(4):
        i = set_patron(gb, b, DOOR_X + 4)
        inject_mug(gb, b, DOOR_X + 12)
        put(gb, "patron_draw", i, 255)
    served0 = gb.mem("served")
    for n in range(60):
        gb.run(1)
        assert min(drawn_xs(gb) or [DOOR_X]) >= DOOR_X
        for b in range(4):
            assert door_tiles(gb, b) == want, (group, b, "serving", n)
    assert gb.mem("served") >= served0 + 4


def test_pushed_past_door_x_is_served_and_removed(gb):
    clear_patrons(gb)
    freeze(gb)
    p = set_patron(gb, 1, DOOR_X + 1, state=PUSHED, aux=10)
    hold_mug(gb, p, 1)
    gb.run(2)
    assert gb.read("patron_x", MAX_P)[p] == DOOR_X and gb.mem("served") == 0
    gb.run(3)
    assert gb.read("patron_state", MAX_P)[p] == 0 and gb.mem("served") == 1 and score(gb) == 50
    assert mugs(gb) == []


def test_a_patron_pushed_back_from_further_in_never_goes_left_of_door_x(gb):
    clear_patrons(gb)
    freeze(gb)
    p = set_patron(gb, 2, DOOR_X + 6, state=PUSHED, aux=60)
    low = 255
    for _ in range(12):
        gb.run(1)
        if gb.read("patron_state", MAX_P)[p]:
            low = min(low, gb.read("patron_x", MAX_P)[p])
    assert low == DOOR_X and gb.read("patron_state", MAX_P)[p] == 0 and gb.mem("served") == 1


def test_a_watcher_never_shuffles_over_the_door(gb):
    clear_patrons(gb)
    go(gb)
    i = set_patron(gb, 0, DOOR_X + 3)
    put(gb, "patron_dist", i, 1)
    lo = 255
    for _ in range(30):
        gb.run(1)
        lo = min(lo, gb.read("patron_x", MAX_P)[i])
    assert lo >= DOOR_X and gb.read("patron_x", MAX_P)[i] == DOOR_X, "snaps to the multiple of 8 at the door's edge"


def goto_level(gb, level):
    """Level `level` (1..9: its own speed row), through the bonus round that follows an even level."""
    gb.write("level", level - 1)
    gb.write("game_state", 3)                      # GS_LEVEL_CLEAR
    gb.write("state_timer", 149)
    gb.run(1)
    run_until(gb, lambda: state(gb) in (PLAYING, BONUS), 40)
    if state(gb) == BONUS:
        pick(gb, 1)
        run_until(gb, lambda: state(gb) == PLAYING, 400)
    assert gb.mem("level") == level


def crossing_frames(gb):
    clear_patrons(gb)
    go(gb)
    set_patron(gb, 0, DOOR_X)
    n = 0
    while gb.mem("lives") == 3 and n < 1500:
        gb.run(1)
        n += 1
    return n


@pytest.mark.parametrize("level", range(1, 10))
def test_crossing_time_is_unchanged_per_level(gb, level):
    """Door to tap takes what it did when the walk started at x = 0 (120 px at 8 px per step_frames, floor(2048 / step) / 256
    px per frame), within 2%; level 1 stays at 15 s or more."""
    if level > 1:
        goto_level(gb, level)
    gb.write("tip_chance", 0)
    step = TABLE[level - 1][5]
    assert gb.mem("step_frames") == step
    old = 120 * 256 / (2048 // step)
    n = crossing_frames(gb)
    assert abs(n - old) <= 0.02 * old + 1, (level, n, old)
    if level == 1:
        assert n >= 15 * 60


# ---- the door puff ------------------------------------------------------------------------------
def test_puff_when_a_patron_enters(gb):
    clear_patrons(gb)
    gb.write("quota", 5)
    gb.write("intro_timer", 0)
    assert puffs(gb) == []
    spawn_now(gb)
    seen = []
    for _ in range(PUFF_TOTAL + 6):
        gb.run(1)
        seen.append(puffs(gb))
    shown = [s for s in seen if s]
    assert PUFF_TOTAL - 2 <= len(shown) <= PUFF_TOTAL + 1, len(shown)
    b = patrons(gb)[0]["bar"]
    assert all(len(s) == 1 and s[0]["x"] == PUFF_X + 8 and s[0]["y"] == 16 + bar_top_row(b) * 8 for s in shown)
    assert {s[0]["tile"] for s in shown} == PUFF_TILES, "all three frames show"
    assert seen[-1] == [] and puffs(gb) == [], "gone again"
    assert [i for i, s in enumerate(gb.oam()) if s["tile"] in PUFF_TILES and s["y"]] == [] 


def test_puff_when_a_patron_leaves(gb):
    clear_patrons(gb)
    freeze(gb)
    p = set_patron(gb, 3, DOOR_X, state=PUSHED, aux=5)
    gb.run(1)
    assert puffs(gb) == []
    gb.run(2)
    assert gb.mem("served") == 1
    got = []
    for _ in range(PUFF_TOTAL + 4):
        got.append(puffs(gb))
        gb.run(1)
    assert any(got) and sum(1 for s in got if s) >= PUFF_TOTAL - 2
    s = next(s for s in got if s)[0]
    assert s["y"] == 16 + bar_top_row(3) * 8 and s["x"] == PUFF_X + 8
    assert puffs(gb) == []


def test_puff_stays_within_the_scanline_limit(gb):
    """A puff on a bar whose lines already carry the bartender, the fill glass and six mugs: still <= 10 per line."""
    clear_patrons(gb)
    freeze(gb)
    for x in (130, 120, 110, 100, 90, 80):
        inject_mug(gb, 0, x)
    gb.hold("a")
    gb.run(6)
    p = set_patron(gb, 0, DOOR_X, state=PUSHED, aux=3)
    worst = 0
    for _ in range(PUFF_TOTAL + 6):
        gb.run(1)
        counts = [0] * 144
        for s in gb.visible_sprites():
            top = s["y"] - 16
            for line in range(max(top, 0), min(top + 16, 144)):
                counts[line] += 1
        worst = max(worst, max(counts))
        if puffs(gb):
            assert max(counts[bar_top_row(0) * 8:bar_top_row(0) * 8 + 16]) <= 10
    gb.release("a")
    assert worst <= 10 and gb.mem("served") == 1
