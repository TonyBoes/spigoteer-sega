# The bars' left end (owner 2026-10-09: no doors). The wall and the counter run to the screen's left edge. A new patron
# slides in from beyond x 0 as a sprite (LIFT_EDGE: drawn patron_aux px left of patron_x, clipped by the screen edge,
# no BG footprint), 24 px at EMERGE_SPEED / 256 px a frame to WALK_X (48 frames; owner 2026-10-13: he slows to the
# level's walking pace at the old door, x 0-16, not at ENTRY_X), walks at the level's speed and drops to the BG at ENTRY_X
# by the M13b rules. A patron whose push carries all of him off the screen is served: he slides out past the edge as a
# sprite with his mug (PATRON_LEAVING) and the serve (score, count, tip) counts when he is gone. Columns 0-1 of the wall
# rows keep the venue's tiles throughout.
import re

import numpy as np
import pytest
from conftest import GAME, ROOT, THEMES, bar_top_row, venue
from test_art import goto_group
from test_bonus import pick
from test_flow import PLAYING, BONUS, TABLE, run_until, state
from test_patrons import (DRINKING, MAX_P, PUSHED, WALKING, clear_patrons, drawn_tiles, freeze, go, hold_mug, inject_mug,
                          map_ids, mugs, patrons, put, score, set_patron, spawn_now)

pytestmark = pytest.mark.timeout(120)

ENTRY_X, SPAWN_X, EMERGE_SPEED, WALK_X = GAME["ENTRY_X"], GAME["SPAWN_X"], GAME["EMERGE_SPEED"], GAME["WALK_X"]
LIFT_BG, LIFT_OBJ, LIFT_EDGE = GAME["LIFT_BG"], GAME["LIFT_OBJ"], GAME["LIFT_EDGE"]
LEAVING = 4                                     # PATRON_LEAVING
W = GAME["PATRON_W"]
OAM_LIFT_TOP = GAME["OAM_MUG_END"] - 1
OUT = ROOT / "out" / "doors"
EMPTY, BREAKING, HELD = 2, 3, 4
_ART_H = (ROOT / "build" / "art.h").read_text()
BASE = int(re.search(r"#define PATRON_FIRST_TILE (\d+)", _ART_H).group(1))


def left_tiles(gb, b, cols=2):
    tm = gb.bg_tilemap()
    return [[t & 0xFF for t in tm[bar_top_row(b) + r][:cols]] for r in range(2)]


def venue_left(group, cols=2):
    m = venue(group)["bar_map"]
    return [m[r * 20:r * 20 + cols] for r in range(2)]


def px(gb, p):
    return gb.read("patron_x", MAX_P)[p]


def aux(gb, p):
    return gb.read("patron_aux", MAX_P)[p]


def lift_of(gb, p):
    return gb.read("patron_lift", MAX_P)[p]


def lifted_any(gb):
    return [s for s in gb.oam()[OAM_LIFT_TOP - 7:OAM_LIFT_TOP + 1] if s["y"]]


def edge_sprites(gb, p):
    """The two OAM entries showing patron p at the left end: OAM X = his screen x + 8 and + 16 (mod 256)."""
    sx = (px(gb, p) - aux(gb, p)) & 255
    return [s for s in gb.oam()[OAM_LIFT_TOP - 7:OAM_LIFT_TOP + 1] if s["y"] and s["x"] in ((sx + 8) & 255, (sx + 16) & 255)]


def line_counts(gb):
    c = [0] * 144
    for s in gb.oam():
        if not s["y"] or s["y"] >= 160:
            continue
        for line in range(max(0, s["y"] - 16), min(144, s["y"])):
            c[line] += 1
    return c


def spawn_one(gb, keep=False):
    """A new patron now (nobody else spawns afterwards): (slot, bar). Alone on the bars, or (keep) with the level's
    patrons moved on to x 56 first (properly redrawn: for screenshots)."""
    if keep:
        st = gb.read("patron_state", MAX_P)
        for i in range(MAX_P):
            if st[i]:
                put(gb, "patron_x", i, 56)
        gb.write("intro_timer", 255)
        gb.run(12)
    else:
        clear_patrons(gb)
    gb.write("quota", 50)
    gb.write("intro_timer", 0)
    spawn_now(gb)
    for _ in range(4):
        gb.run(1)
        ps = [q for q in patrons(gb) if q["x"] == SPAWN_X and lift_of(gb, q["i"]) == LIFT_EDGE]
        if ps:
            gb.write("spawn_timer", 0xFF)
            gb.write(gb.addr("spawn_timer") + 1, 0xFF)
            return ps[0]["i"], ps[0]["bar"]
    raise AssertionError("no spawn")


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


# ---- the geometry ------------------------------------------------------------------------------------------------------
def test_entry_geometry():
    """ENTRY_X is the old door's right edge (the counter's walk limit too, where a patron is a BG figure from); an
    entering patron covers the 24 px from fully off the screen to WALK_X (the old door, x 0-16) in 48 frames, where he
    slows to the level's walking pace."""
    assert ENTRY_X == 16 == GAME["LEFT_LIMIT"] and SPAWN_X == 0 and W == 16
    assert 0 < WALK_X < ENTRY_X
    assert (WALK_X - SPAWN_X + W) * 256 // EMERGE_SPEED == 48


def test_no_venue_has_a_door():
    """Every venue's wall rows run to the left edge: columns 0-1 are wall tiles of the venue (colour 0 and its specks,
    the same tiles as the rest of the wall) on the bar palette."""
    vd = ROOT / "assets" / "approved" / "venues"
    for t in THEMES:
        rows = [r for r in (vd / f"{t}_bar.txt").read_text().splitlines() if r and not r.startswith(";")]
        assert all(set(r[:16]) <= {".", "-"} for r in rows[:16]), t
        v = venue(t)
        walls = set(v["bar_map"][2:17] + v["bar_map"][22:37])
        assert set(v["bar_map"][0:2] + v["bar_map"][20:22]) <= walls, t
        assert v["bar_attr"][0:2] == [0, 0] and v["bar_attr"][20:22] == [0, 0], t


# ---- entering ----------------------------------------------------------------------------------------------------------
def test_a_spawned_patron_is_a_sprite_wholly_beyond_the_left_edge(gb):
    """A new patron appears at SPAWN_X with all 16 px of him off the screen (patron_aux 16): two 8x16 entries at OAM X
    248 and 0 (nothing shows), in front of the BG (no priority bit); columns 0-1 keep the venue's tiles."""
    clear_patrons(gb)
    gb.write("quota", 5)
    gb.write("intro_timer", 0)
    spawn_now(gb)
    for _ in range(4):
        gb.run(1)
        if patrons(gb):
            break
    ps = patrons(gb)
    assert len(ps) == 1 and ps[0]["x"] == SPAWN_X and ps[0]["state"] == WALKING
    p, b = ps[0]["i"], ps[0]["bar"]
    assert lift_of(gb, p) == LIFT_EDGE and aux(gb, p) == W
    spr = edge_sprites(gb, p)
    assert sorted(s["x"] for s in spr) == [0, 248] and not any(s["flags"] & 0x80 for s in spr)
    assert left_tiles(gb, b) == venue_left(0)


def test_spawn_waits_while_the_left_end_is_crowded(gb):
    """The spacing rule at the left end: nobody spawns while a patron stands within PATRON_SPACING px of SPAWN_X."""
    clear_patrons(gb)
    for b in range(4):
        set_patron(gb, b, SPAWN_X + 31, state=DRINKING)    # 31 < 32 px from a patron at SPAWN_X
    gb.write("quota", 9)
    gb.write("spawned", 4)
    gb.write("intro_timer", 0)
    spawn_now(gb)
    gb.run(40)
    assert gb.mem("spawned") == 4
    for b in range(4):
        put(gb, "patron_x", [p["i"] for p in patrons(gb) if p["bar"] == b][0], SPAWN_X + 32)
    spawn_now(gb)
    gb.run(40)
    assert gb.mem("spawned") == 5


@pytest.mark.parametrize("group", [0, 4], ids=["saloon", "igloo"])
def test_he_slides_in_from_the_left_edge(gb, group):
    """Frame by frame while he enters: the part of him on the screen grows from the edge (none at patron_aux 16, and
    never a pixel right of his right edge, 16 - patron_aux), columns 0-2 of his wall rows keep the venue's tiles (no
    garbage tile, no BG copy of him) until ENTRY_X, and columns 0-1 never change. He enters fast until WALK_X. x4 screenshots in out/doors/."""
    if group:
        goto_group(gb, group)
    gb.write("tip_chance", 0)
    p, b = spawn_one(gb, keep=True)
    top = bar_top_row(b) * 8
    want2, want3 = venue_left(group), venue_left(group, 3)
    gb.run(1, render=True)
    OUT.mkdir(parents=True, exist_ok=True)
    other = bar_top_row((b + 1) & 3) * 8                   # (the same wall, nobody at its left end: the reference)
    ref = np.asarray(gb.image())[other:other + 16, 0:24].copy()
    vis, shot = {}, False
    for i in range(90):
        a, x = aux(gb, p), px(gb, p)
        im = np.asarray(gb.image())
        if x >= WALK_X:
            break
        assert lift_of(gb, p) == LIFT_EDGE
        assert left_tiles(gb, b) == want2, (i, x, a)
        assert left_tiles(gb, b, 3) == want3, (i, x, a, "columns 0-2: the venue's wall, no BG copy of him")
        diff = (im[top:top + 16, 0:24] != ref).any(axis=2)
        right = x - a + W                                  # screen x just right of him
        assert not diff[:, max(right, 0):].any(), (i, x, a, "nothing beyond his right edge")
        if x == 0:
            vis[W - a] = int(diff.sum())
        if a == 6 and not shot:
            gb.screenshot(OUT / f"enter_{THEMES[group]}.{gb.model_name}.png", 4)
            shot = True
        gb.run(1, render=True)
    ks = sorted(vis)
    assert ks[-1] == W and all(vis[k1] <= vis[k2] for k1, k2 in zip(ks, ks[1:])), vis
    assert vis[W] > vis[W // 2] > 0, vis
    assert shot and 44 <= i <= 52, i                       # 24 px at EMERGE_SPEED / 256 px a frame: 48 frames


def test_he_drops_to_the_bg_at_entry_x_when_clear(gb):
    p, b = spawn_one(gb)
    v = gb.read("patron_variant", MAX_P)[p]
    while px(gb, p) < ENTRY_X:
        gb.run(1)
    assert lift_of(gb, p) == LIFT_OBJ, "on the screen: an ordinary lifted patron"
    gb.run(GAME["LIFT_CLEAR_FRAMES"] + 3)
    x = px(gb, p)
    assert ENTRY_X <= x <= ENTRY_X + 1 and lift_of(gb, p) == LIFT_BG and gb.mem("lift_total") == 0
    assert lifted_any(gb) == []
    gb.write("intro_timer", 255)                                # stand still: his BG copy is on screen
    gb.run(3)
    col, ids = drawn_tiles(v, px(gb, p), b)
    assert map_ids(gb, b, col) == ids
    assert left_tiles(gb, b) == venue_left(0)


def test_one_who_meets_someone_at_entry_x_stays_lifted(gb):
    """Not clear at ENTRY_X (a drinker stands at x 20): he stays a sprite (LIFT_OBJ); when the drinker has gone he
    drops after LIFT_CLEAR_FRAMES by the M13b rules; columns 0-1 never change."""
    p, b = spawn_one(gb)
    d = set_patron(gb, b, 20, state=DRINKING, variant=1)
    while px(gb, p) < ENTRY_X:
        gb.run(1)
        assert left_tiles(gb, b) == venue_left(0)
    gb.run(1)
    assert lift_of(gb, p) == LIFT_OBJ
    gb.run(20)
    assert lift_of(gb, p) == LIFT_OBJ, "still over the drinker"
    put(gb, "patron_state", d, 0)                               # the drinker leaves (a poke: the chooser looks again
    gb.write("patrons_live", 1)                                 # when he next changes columns)
    for i in range(150):
        gb.run(1)
        if lift_of(gb, p) == LIFT_BG:
            break
    assert lift_of(gb, p) == LIFT_BG and i >= GAME["LIFT_CLEAR_FRAMES"], i
    assert left_tiles(gb, b) == venue_left(0)


@pytest.mark.parametrize("level", [1, 10])
def test_patrons_slow_to_walking_pace_at_the_old_door_position(gb, level):
    """He takes 48 frames from the spawn to WALK_X (fast: EMERGE_SPEED), where he slows to the level's walking pace (the
    speed is unchanged), so the walk on to the tap takes the level's time for (FAR_X - WALK_X) px: the old walk from
    ENTRY_X (within 2 %) plus the extra WALK_X..ENTRY_X px. Level 1 stays at 15 s or more."""
    if level > 1:
        goto_level(gb, level)
    gb.write("tip_chance", 0)
    p, b = spawn_one(gb)
    put(gb, "patron_hurry", p, 0)
    n, t8, xs = 1, None, []
    while gb.mem("lives") == 3 and n < 2200:
        gb.run(1)
        n += 1
        xs.append(px(gb, p) - aux(gb, p))
        if t8 is None and px(gb, p) >= WALK_X:
            t8 = n
    step = TABLE[level - 1][5]
    old = 120 * 256 / (2048 // step)
    assert abs(t8 - (WALK_X - SPAWN_X + W) * 256 / EMERGE_SPEED) <= 3, t8
    # fast before WALK_X: 0.5 px a frame; slow after it (level 1: about 0.11 px a frame)
    fast = xs[t8 - 2] - xs[t8 - 18]
    assert fast >= 7, fast
    assert xs[t8 + 30] - xs[t8 + 14] <= 4, "slow after WALK_X"
    expect = old * (GAME["PATRON_FAR_X"] - WALK_X) / (GAME["PATRON_FAR_X"] - ENTRY_X)
    cross = n - t8
    assert abs(cross - expect) <= 0.02 * expect + 1, (level, cross, expect)
    if level == 1:
        assert cross >= 15 * 60


@pytest.mark.parametrize("level", range(1, 11))
def test_crossing_time_is_unchanged_per_level(gb, level):
    """ENTRY_X to the tap takes what it did when the walk started at x = 0 (120 px at 8 px per step_frames,
    floor(2048 / step) / 256 px per frame), within 2%; level 1 stays at 15 s or more."""
    if level > 1:
        goto_level(gb, level)
    gb.write("tip_chance", 0)
    step = TABLE[level - 1][5]
    assert gb.mem("step_frames") == step
    old = 120 * 256 / (2048 // step)
    clear_patrons(gb)
    go(gb)
    set_patron(gb, 0, ENTRY_X)
    n = 0
    while gb.mem("lives") == 3 and n < 1500:
        gb.run(1)
        n += 1
    assert abs(n - old) <= 0.02 * old + 1, (level, n, old)
    if level == 1:
        assert n >= 15 * 60


def test_no_catch_while_part_of_him_is_off_the_screen(gb):
    """A full mug reaching the left end while a patron is still sliding in (patron_aux > 0) is not his: it breaks."""
    p, b = spawn_one(gb)
    gb.run(4)
    assert aux(gb, p) > 4
    m = inject_mug(gb, b, ENTRY_X + 2)
    gb.run(4)
    assert gb.read("mug_state", 20)[m] == BREAKING and gb.mem("served") == 0


def test_he_catches_a_mug_while_entering_and_slides_back_out(gb):
    """On the screen but left of ENTRY_X he is a walker like any other: a full mug reaching him is caught, and the push
    carries him all the way off (x + 16 <= the push): served, he slides back out past the edge with the mug in his hand
    and the serve counts when he is gone; columns 0-1 never change; no mug is left."""
    p, b = spawn_one(gb)
    while px(gb, p) < 6:
        gb.run(1)
    served0, score0 = gb.mem("served"), score(gb)
    inject_mug(gb, b, ENTRY_X + 4)
    gb.run(3)
    assert gb.read("patron_state", MAX_P)[p] == LEAVING and lift_of(gb, p) == LIFT_EDGE
    assert gb.mem("served") == served0 and score(gb) == score0, "not counted until he is off the screen"
    held_seen = 0
    for i in range(40):
        gb.run(1)
        assert left_tiles(gb, b) == venue_left(0)
        if gb.read("patron_state", MAX_P)[p] == 0:
            break
        held_seen += any(m["state"] == HELD for m in mugs(gb))
    assert gb.read("patron_state", MAX_P)[p] == 0 and i <= 6 + W + 2, i
    assert held_seen > 0 and mugs(gb) == [] and gb.mem("lives") == 3 and lifted_any(gb) == []
    assert gb.mem("served") == served0 + 1 and score(gb) == score0 + 50


# ---- leaving -----------------------------------------------------------------------------------------------------------
def test_a_push_that_carries_him_off_serves_him_when_he_is_gone_and_he_slides_out_past_the_edge(gb):
    """A push of PUSH px takes a patron at ENTRY_X (x + 16 = PUSH) wholly off the screen: he is a sprite from ENTRY_X on
    (LIFT_EDGE) at 1 px a frame to x 0 and on past the edge (patron_aux grows), his mug drawn in his hand; the serve
    (score, count) counts only when all of him is gone, then he is removed with the mug."""
    clear_patrons(gb)
    freeze(gb)
    p = set_patron(gb, 1, ENTRY_X)
    gb.run(3)                                                   # (drawn first: a never-drawn one has nothing to lift)
    inject_mug(gb, 1, ENTRY_X + 8)
    gb.run(3)
    m = [q["i"] for q in mugs(gb) if q["state"] == HELD][0]
    pos, left = [], False
    for _ in range(80):
        st = gb.read("patron_state", MAX_P)[p]
        if not st:
            break
        if st == LEAVING:
            sx = px(gb, p) - aux(gb, p)
            pos.append(sx)
            assert lift_of(gb, p) == LIFT_EDGE and len(edge_sprites(gb, p)) == 2
            assert gb.mem("served") == 0 and score(gb) == 0, "still on the screen: not served yet"
            mug = gb.read("mug_x", 20)[m]
            assert gb.read("mug_state", 20)[m] == HELD and ((mug - sx) & 255) < 24, "the mug goes with him"
            assert left_tiles(gb, 1) == venue_left(0)
        gb.run(1)
    assert pos == sorted(pos, reverse=True) and pos[-1] <= -W + 1 and pos[0] >= ENTRY_X - 2, pos
    assert all(a - b_ == 1 for a, b_ in zip(pos, pos[1:])), pos
    assert gb.read("patron_state", MAX_P)[p] == 0 and mugs(gb) == [] and lifted_any(gb) == []
    assert gb.mem("served") == 1 and score(gb) == 50


def test_a_push_that_falls_short_stops_him_on_the_screen(gb):
    """Option C: one pixel too far in (x = ENTRY_X + 33: the 32 px push stops 1 px short of the left-edge stop): he is
    pushed the full 32 px, stops at ENTRY_X + 1, a BG figure, and drinks; nothing is served. (One at ENTRY_X + 32 is
    served: test_patrons.py.)"""
    clear_patrons(gb)
    freeze(gb)
    x = ENTRY_X + 33
    p = set_patron(gb, 2, x)
    inject_mug(gb, 2, x + 8)
    gb.run(3 + 36)
    assert gb.read("patron_state", MAX_P)[p] == DRINKING and px(gb, p) == ENTRY_X + 1
    gb.run(40)
    assert gb.mem("served") == 0 and score(gb) == 0 and gb.read("patron_state", MAX_P)[p] == DRINKING


def test_a_lifted_patron_served_out_slides_out_as_he_is(gb):
    """A patron already lifted (LIFT_OBJ) when served becomes LIFT_EDGE in place: his sprite never leaves the screen
    before he does, and columns 0-1 never change."""
    clear_patrons(gb)
    freeze(gb)
    p = set_patron(gb, 1, ENTRY_X)
    gb.run(3)
    gb.write("lift_hook_p", p)
    gb.write("lift_hook_res", 0)
    gb.write("lift_hook_op", 1)                                 # HOOK_LIFT (test_lift.py)
    gb.run(3)
    assert lift_of(gb, p) == LIFT_OBJ and lifted_any(gb)
    inject_mug(gb, 1, ENTRY_X + 8)
    gone = None
    for i in range(50):
        gb.run(1)
        assert left_tiles(gb, 1) == venue_left(0)
        if gb.read("patron_state", MAX_P)[p] == 0:
            gone = i
            break
        if gb.read("patron_state", MAX_P)[p] == LEAVING:
            assert lift_of(gb, p) == LIFT_EDGE and len(edge_sprites(gb, p)) == 2, i
    assert gone is not None and gb.mem("served") == 1 and lifted_any(gb) == []


@pytest.mark.parametrize("group", [0, 3, 8])
def test_columns_0_1_keep_the_venue_tiles_with_patrons_coming_and_going(gb, group):
    if group:
        goto_group(gb, group)
    gb.write("tip_chance", 0)
    clear_patrons(gb)
    gb.write("quota", 16)
    gb.write("intro_timer", 0)
    want = venue_left(group)
    seen_bars, edge = set(), 0
    for n in range(260):
        if n % 20 == 0:
            spawn_now(gb)
        gb.run(1)
        for p in patrons(gb):
            seen_bars.add(p["bar"])
        edge += list(gb.read("patron_lift", MAX_P)).count(LIFT_EDGE)
        for b in range(4):
            assert left_tiles(gb, b) == want, (group, b, n)
    assert len(seen_bars) >= 3 and edge > 0, "patrons came in on most bars"
    # serve one out on every bar: columns 0-1 stay as they are while they slide out
    freeze(gb)
    clear_patrons(gb)
    gb.write("quota", 250)                               # (no level clear while they leave: it would reset `served`)
    gb.write("pushback_px", 32)                          # (the zoo's push is 24: one mug would not carry a patron from ENTRY_X off)
    sx = ENTRY_X
    for b in range(4):
        set_patron(gb, b, sx)
    gb.run(3)
    for b in range(4):
        inject_mug(gb, b, sx + 8)
    served0 = gb.mem("served")
    for n in range(70):
        gb.run(1)
        for b in range(4):
            assert left_tiles(gb, b) == want, (group, b, "serving", n)
    assert gb.mem("served") >= served0 + 4


def test_a_watcher_never_shuffles_left_of_entry_x(gb):
    clear_patrons(gb)
    go(gb)
    i = set_patron(gb, 0, ENTRY_X + 3)
    put(gb, "patron_dist", i, 1)
    lo = 255
    for _ in range(30):
        gb.run(1)
        lo = min(lo, px(gb, i))
    assert lo >= ENTRY_X and px(gb, i) == ENTRY_X, "snaps to the multiple of 8 at ENTRY_X"


# ---- budgets -----------------------------------------------------------------------------------------------------------
def test_ten_objects_per_line_with_patrons_entering_and_leaving(gb):
    """The entering patron's bar at its busiest: the bartender filling on it, four empties, a glass breaking at the left
    end (and one on the bar above, which falls into this bar's lines), a patron served and sliding out: no line ever
    holds more than 10 objects (the sprite at OAM X 248 or 0 counts too), columns 0-1 never change."""
    p, b = spawn_one(gb)
    gb.write("bar", b)
    gb.hold("a")
    for k in range(4):
        inject_mug(gb, b, 40 + 14 * k, EMPTY)
    gb.run(2)
    for bb in {b, max(0, b - 1)}:
        inject_mug(gb, bb, GAME["GLASS_X"], BREAKING)
    gb.write("mug_events", gb.mem("mug_events") + 1)
    set_patron(gb, b, ENTRY_X + 1, state=PUSHED, aux=4)
    worst = 0
    for i in range(40):
        gb.run(1)
        c = line_counts(gb)
        worst = max(worst, max(c))
        assert max(c) <= 10, (i, c[bar_top_row(b) * 8:bar_top_row(b) * 8 + 24])
        assert left_tiles(gb, b) == venue_left(0)
    gb.release("a")
    assert gb.mem("served") >= 1 and worst >= 9, worst


def test_an_entering_patron_partly_off_screen_is_taken_back_when_the_line_is_full(gb):
    """The line budget goes over while a patron is still partly beyond the edge (he cannot drop to the BG there): he is
    taken back (spawned again later), never 11 objects on a line, columns 0-1 unchanged."""
    p, b = spawn_one(gb)
    gb.run(2)
    assert aux(gb, p) > 8
    spawned = gb.mem("spawned")
    gb.write("bar", b)
    gb.hold("a")                                      # the bartender fills on his bar: 3 objects
    for k in range(6):                                # and 6 empties: 9 + his 2 = 11
        inject_mug(gb, b, 30 + 14 * k, EMPTY)
    gb.write("mug_events", gb.mem("mug_events") + 1)
    for i in range(6):
        gb.run(1)
        assert max(line_counts(gb)) <= 10, i
        assert left_tiles(gb, b) == venue_left(0)
    gb.release("a")
    assert gb.read("patron_state", MAX_P)[p] == 0 and gb.mem("spawned") == spawned - 1
    assert gb.mem("lift_forced") > 0


def test_a_spawn_waits_while_there_is_no_sprite_room(gb):
    """18 empties in flight leave no OAM entries for the entering patron's two sprites: no spawn (retried every
    SPAWN_RETRY frames), never a BG patron at the left end; when room comes back he slides in from the edge."""
    clear_patrons(gb)
    gb.write("quota", 50)
    gb.write("intro_timer", 0)
    for b in (1, 2, 3):
        for k in range(6):
            inject_mug(gb, b, 24 + 12 * k, EMPTY)
    spawned0 = gb.mem("spawned")
    spawn_now(gb)

    def keep_away():
        for m in range(20):
            if gb.read("mug_state", 20)[m] == EMPTY and gb.read("mug_x", 20)[m] > 100:
                put(gb, "mug_x", m, 24)
    for i in range(70):
        gb.run(1)
        keep_away()
        assert gb.mem("spawned") == spawned0 and patrons(gb) == [], i
        for b in range(4):
            assert left_tiles(gb, b) == venue_left(0)
    for m in range(20):                                     # empties gone: room for one lifted patron
        if gb.read("mug_state", 20)[m] == EMPTY and gb.read("mug_bar", 20)[m] == 3:
            put(gb, "mug_state", m, 0)
            if sum(1 for s in gb.read("mug_state", 20) if s) <= 15:
                break
    gb.write("mugs_live", sum(1 for s in gb.read("mug_state", 20) if s))
    for i in range(GAME["SPAWN_RETRY"] + 4):
        gb.run(1)
        keep_away()
        if patrons(gb):
            break
    ps = patrons(gb)
    assert len(ps) == 1 and gb.mem("spawned") == spawned0 + 1 and ps[0]["x"] == SPAWN_X
    assert lift_of(gb, ps[0]["i"]) == LIFT_EDGE and aux(gb, ps[0]["i"]) >= W - 4
