# Door fix: patrons are served out when pushed back past DOOR_X (the 16 px door's right edge), never draw over columns
# 0-1 of the wall rows, walk the shorter way in the same time, and a dust puff marks the door swinging when one leaves.
# M13c: a new patron steps out from behind the door: he spawns at SPAWN_X lifted behind the BG (the door's colours 1-3
# hide him; no venue's door has colour 0), emerges at EMERGE_SPEED / 256 px a frame to DOOR_X, then walks at the level's
# speed; the door's tiles never change; no puff on entry. The M13c tests are at the end of the file.
import re

import numpy as np
import pytest
from conftest import GAME, ROOT, THEMES, bar_top_row, logical_tile, venue
from test_art import goto_group
from test_bonus import pick
from test_flow import PLAYING, BONUS, TABLE, run_until, state
from test_patrons import (DRINKING, MAX_P, PUSHED, WALKING, FAR_X, clear_patrons, drawn_tiles, freeze, go, hold_mug, inject_mug,
                          map_ids, mugs, patrons, put, score, set_patron, spawn_now)

pytestmark = pytest.mark.timeout(120)

DOOR_X = GAME["DOOR_X"]
PUFF_TOTAL, PUFF_X, OAM_PUFF = GAME["PUFF_TOTAL"], GAME["PUFF_X"], GAME["OAM_PUFF"]
_ART_H = (ROOT / "build" / "art.h").read_text()
_BG_TOTAL = int(re.search(r"#define BAR_TILE_COUNT (\d+)", _ART_H).group(1)) + int(re.search(r"#define PATRON_GROUP_TILES (\d+)", _ART_H).group(1))
OBJ_PUFF = (_BG_TOTAL + 1) & ~1
PUFF_TILES = {OBJ_PUFF, OBJ_PUFF + 2, OBJ_PUFF + 4}
SPAWN_X, EMERGE_SPEED, DOOR_COLS = GAME["SPAWN_X"], GAME["EMERGE_SPEED"], GAME["DOOR_COLS"]
LIFT_BG, LIFT_OBJ, LIFT_BEHIND = GAME["LIFT_BG"], GAME["LIFT_OBJ"], GAME["LIFT_BEHIND"]
OAM_LIFT_TOP = GAME["OAM_MUG_END"] - 1


def door_tiles(gb, b):
    tm = gb.bg_tilemap()
    return [[t & 0xFF for t in tm[bar_top_row(b) + r][:2]] for r in range(2)]


def venue_door(group, b=0):
    m = venue(group)["bar_map"]
    return [m[r * 20:r * 20 + 2] for r in range(2)]


def puffs(gb):
    """The puff sprites (M13a: on DMG they show copies at OBJ 246-251, reported as the tile they were made from)."""
    return [dict(s, tile=logical_tile(s["tile"])) for s in gb.visible_sprites() if logical_tile(s["tile"]) in PUFF_TILES]


def emerging_sprites(gb, p):
    """The OAM entries showing lifted patron p (his shift-0 tiles at his drawn x + 8 and + 16, OAM 25 down)."""
    d = gb.read("patron_draw", MAX_P)[p]
    return [s for s in gb.oam()[OAM_LIFT_TOP - 7:OAM_LIFT_TOP + 1] if s["y"] and s["x"] in (d + 8, d + 16)]


def test_door_x_is_the_door_width():
    assert DOOR_X == 16 and GAME["LEFT_LIMIT"] == 16


def test_a_spawned_patron_stands_behind_the_door_lifted_behind_the_bg(gb):
    """M13c: a new patron appears at SPAWN_X (OAM X 8: no left-edge clipping) as two 8x16 sprites with the OAM
    priority bit (behind BG colours 1-3), and the door's tiles stay as they are."""
    clear_patrons(gb)
    gb.write("quota", 5)
    gb.write("intro_timer", 0)
    spawn_now(gb)
    gb.run(2)
    ps = patrons(gb)
    assert len(ps) == 1 and ps[0]["x"] == SPAWN_X and ps[0]["state"] == WALKING
    p, b = ps[0]["i"], ps[0]["bar"]
    assert gb.read("patron_lift", MAX_P)[p] == LIFT_BEHIND
    spr = emerging_sprites(gb, p)
    assert sorted(s["x"] for s in spr) == [8 + SPAWN_X, 16 + SPAWN_X] and all(s["flags"] & 0x80 for s in spr)
    assert door_tiles(gb, b) == venue_door(0)


def test_spawn_waits_while_the_door_end_is_crowded(gb):
    """The spacing rule at the door (M13c): nobody spawns while a patron stands within PATRON_SPACING px of SPAWN_X."""
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


@pytest.mark.parametrize("group", [0, 3, 8])
def test_door_tiles_stay_intact_with_patrons_coming_and_going(gb, group):
    if group:
        goto_group(gb, group)
    gb.write("tip_chance", 0)
    clear_patrons(gb)
    gb.write("quota", 16)
    gb.write("intro_timer", 0)
    want = venue_door(group)
    seen_bars, behind = set(), 0
    for n in range(260):
        if n % 20 == 0:
            spawn_now(gb)
        gb.run(1)
        for p in patrons(gb):
            seen_bars.add(p["bar"])
        behind += list(gb.read("patron_lift", MAX_P)).count(LIFT_BEHIND)
        for b in range(4):                          # (M13c: patrons step out from behind the door: every frame)
            assert door_tiles(gb, b) == want, (group, b, n)
    assert len(seen_bars) >= 3, "patrons entered on most bars"
    assert behind > 0, "they came in from behind the door"
    # serve one out through the door on every bar: the door stays whole while it is pushed out and after
    freeze(gb)
    for b in range(4):
        i = set_patron(gb, b, DOOR_X + 4)
        inject_mug(gb, b, DOOR_X + 12)
        put(gb, "patron_draw", i, 255)
    served0 = gb.mem("served")
    for n in range(60):
        gb.run(1)
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
def test_no_puff_when_a_patron_enters(gb):
    """M13c: the emergence from behind the door replaces the entry puff."""
    clear_patrons(gb)
    gb.write("quota", 5)
    gb.write("intro_timer", 0)
    assert puffs(gb) == []
    spawn_now(gb)
    for _ in range(PUFF_TOTAL + 6):
        gb.run(1)
        assert puffs(gb) == [] and gb.mem("puff_timer") == 0
    assert len(patrons(gb)) == 1


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


# ---- M13c: the door entrance ---------------------------------------------------------------------------------------
OUT = ROOT / "out" / "m13c"
VENUE_DIR = ROOT / "assets" / "approved" / "venues"
EMPTY, BREAKING = 2, 3


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
        ps = [q for q in patrons(gb) if q["x"] <= 1 and lift_of(gb, q["i"]) == LIFT_BEHIND]
        if ps:
            gb.write("spawn_timer", 0xFF)
            gb.write(gb.addr("spawn_timer") + 1, 0xFF)
            return ps[0]["i"], ps[0]["bar"]
    raise AssertionError("no spawn")


def px(gb, p):
    return gb.read("patron_x", MAX_P)[p]


def lift_of(gb, p):
    return gb.read("patron_lift", MAX_P)[p]


def lifted_any(gb):
    return [s for s in gb.oam()[OAM_LIFT_TOP - 7:OAM_LIFT_TOP + 1] if s["y"]]


def line_counts(gb):
    c = [0] * 144
    for s in gb.oam():
        if not s["y"] or s["y"] >= 160:
            continue
        for line in range(max(0, s["y"] - 16), min(144, s["y"])):
            c[line] += 1
    return c


def door_attrs(gb, b):
    return [[gb.pb.memory[1, 0x9800 + (bar_top_row(b) + r) * 32 + c] for c in range(DOOR_COLS)] for r in range(2)]


def test_every_venue_door_is_solid():
    """M13c: the door hides a patron stepping out from behind it (his sprite is behind BG colours 1-3 and shows over
    colour 0), so no venue's 16x16 door may have a colour-0 pixel (owner: the igloo's door was redrawn for this). Its
    generated CGB attributes leave bit 7 (BG over every sprite) clear."""
    for t in THEMES:
        rows = [r for r in (VENUE_DIR / f"{t}_bar.txt").read_text().splitlines() if r and not r.startswith(";")]
        door = [r[:16] for r in rows[:16]]
        assert sum(r.count(".") for r in door) == 0, (t, door)
        attrs = venue(t)["bar_attr"]
        assert all(attrs[r * 20 + c] & 0x80 == 0 for r in range(2) for c in range(DOOR_COLS)), t


def test_bg_priority_is_on_in_play(gb):
    """LCDC bit 0 (CGB: BG and window may cover sprites; DMG: BG on) and, on CGB, the door's attributes in VRAM have
    bit 7 clear: the door covers a LIFT_BEHIND sprite only where its own colours 1-3 are."""
    assert gb.mem(0xFF40) & 1
    if gb.model_name == "cgb":
        for b in range(4):
            assert all(a & 0x80 == 0 for r in door_attrs(gb, b) for a in r)


@pytest.mark.parametrize("group", [0, 4], ids=["saloon", "igloo"])
def test_the_door_hides_him_and_more_of_him_shows_as_he_steps_out(gb, group):
    """From behind the door: the door's pixels and tile ids never change; at x 0 nothing of him shows; the part of him
    right of the door grows with x (and nothing shows beyond his right edge); x4 screenshots mid-emergence in out/m13c/."""
    if group:
        goto_group(gb, group)
    gb.write("tip_chance", 0)
    want = venue_door(group)
    p, b = spawn_one(gb, keep=True)
    top = bar_top_row(b) * 8
    gb.run(1, render=True)
    im = np.asarray(gb.image())
    door_ref = im[top:top + 16, 0:16].copy()
    assert px(gb, p) == SPAWN_X
    wall = tuple(im[top, 20])                                   # (his BG footprint: plain wall, colour 0)
    vis, shot = {}, False
    OUT.mkdir(parents=True, exist_ok=True)
    for i in range(80):
        gb.run(1, render=True)
        x = px(gb, p)
        if x >= DOOR_X:
            break
        assert lift_of(gb, p) == LIFT_BEHIND
        im = np.asarray(gb.image())
        assert (im[top:top + 16, 0:16] == door_ref).all(), (x, "door pixels changed")
        assert door_tiles(gb, b) == want, x
        if x <= 8:
            region = (im[top:top + 16, 16:24] != wall).any(axis=2)
            vis[x] = int(region.sum())
            assert not region[:, x:].any(), (x, "nothing beyond his right edge")
        if x == 10 and not shot:
            gb.screenshot(OUT / f"emerge_{THEMES[group]}.{gb.model_name}.png", 4)
            shot = True
    assert vis[0] == 0, vis
    xs = sorted(vis)
    assert xs == list(range(9)) and all(vis[a] <= vis[a + 1] for a in xs[:-1]), vis
    assert vis[8] > vis[4] > 0, vis
    assert shot and i < 70, i                                   # 16 px at EMERGE_SPEED / 256 px a frame: 64 frames


def test_he_drops_to_the_bg_at_door_x_when_clear(gb):
    p, b = spawn_one(gb)
    v = gb.read("patron_variant", MAX_P)[p]
    while px(gb, p) < DOOR_X:
        gb.run(1)
    gb.run(2)
    x = px(gb, p)
    assert DOOR_X <= x <= DOOR_X + 1 and lift_of(gb, p) == LIFT_BG and gb.mem("lift_total") == 0
    assert lifted_any(gb) == []
    gb.write("intro_timer", 255)                                # stand still: his BG copy is on screen
    gb.run(3)
    col, ids = drawn_tiles(v, px(gb, p), b)
    assert map_ids(gb, b, col) == ids


def test_one_who_meets_someone_at_door_x_stays_lifted_in_front(gb):
    """Not clear at DOOR_X (a drinker stands at x 20): he stays a sprite, now in front (LIFT_OBJ); when the drinker has
    gone he drops after LIFT_CLEAR_FRAMES by the M13b rules; the door never changes."""
    p, b = spawn_one(gb)
    d = set_patron(gb, b, 20, state=DRINKING, variant=1)
    while px(gb, p) < DOOR_X:
        gb.run(1)
        assert door_tiles(gb, b) == venue_door(0)
    gb.run(1)
    assert lift_of(gb, p) == LIFT_OBJ, "in front of the BG once out of the door"
    assert all(not (s["flags"] & 0x80) for s in emerging_sprites(gb, p))
    gb.run(20)
    assert lift_of(gb, p) == LIFT_OBJ, "still over the drinker"
    put(gb, "patron_state", d, 0)                               # the drinker leaves (a poke: the chooser looks again
    gb.write("patrons_live", 1)                                 # when he next changes columns)
    for i in range(150):
        gb.run(1)
        if lift_of(gb, p) == LIFT_BG:
            break
    assert lift_of(gb, p) == LIFT_BG and i >= GAME["LIFT_CLEAR_FRAMES"], i


@pytest.mark.parametrize("level", [1, 9])
def test_door_to_tap_time_from_door_x_is_unchanged(gb, level):
    """He takes 64 frames to step out (16 px at EMERGE_SPEED), and from x = DOOR_X to the tap the level's time as before
    (the old 120 px at 8 px per step_frames, within 2 %); level 1 stays at 15 s or more."""
    if level > 1:
        goto_level(gb, level)
    gb.write("tip_chance", 0)
    p, b = spawn_one(gb)
    put(gb, "patron_hurry", p, 0)
    n, t16 = 0, None
    while gb.mem("lives") == 3 and n < 2000:
        gb.run(1)
        n += 1
        if t16 is None and px(gb, p) >= DOOR_X:
            t16 = n
    step = TABLE[level - 1][5]
    old = 120 * 256 / (2048 // step)
    assert abs(t16 - DOOR_X * 256 / EMERGE_SPEED) <= 3, t16
    cross = n - t16
    assert abs(cross - old) <= 0.02 * old + 1, (level, cross, old)
    if level == 1:
        assert cross >= 15 * 60


def test_he_catches_a_mug_while_stepping_out_and_is_served_through_the_door(gb):
    """A full mug reaching him in the doorway is caught (he is a walker like any other); the push takes him out through
    the door at once: served, his sprite gone on the frame the puff starts, the door untouched, no mug left."""
    p, b = spawn_one(gb)
    while px(gb, p) < 6:
        gb.run(1)
    served0, score0 = gb.mem("served"), score(gb)
    inject_mug(gb, b, DOOR_X + 4)
    seen_puff = False
    for i in range(16):
        gb.run(1)
        spr, pf = lifted_any(gb), puffs(gb)
        assert not (spr and pf), (i, "his sprite and the puff together")
        seen_puff |= bool(pf)
        assert door_tiles(gb, b) == venue_door(0)
    assert gb.mem("served") == served0 + 1 and score(gb) == score0 + 50 and gb.read("patron_state", MAX_P)[p] == 0
    assert seen_puff and mugs(gb) == [] and gb.mem("lives") == 3


def test_a_lifted_patron_served_out_is_gone_before_the_puff_shows(gb):
    clear_patrons(gb)
    freeze(gb)
    p = set_patron(gb, 1, DOOR_X + 4)
    gb.run(3)
    gb.write("lift_hook_p", p)
    gb.write("lift_hook_res", 0)
    gb.write("lift_hook_op", 1)                                 # HOOK_LIFT (test_lift.py)
    gb.run(3)
    assert lift_of(gb, p) == LIFT_OBJ and lifted_any(gb)
    inject_mug(gb, 1, DOOR_X + 12)
    seen_puff = False
    for i in range(24):
        gb.run(1)
        spr, pf = lifted_any(gb), puffs(gb)
        assert not (spr and pf), i
        seen_puff |= bool(pf)
    assert seen_puff and gb.mem("served") == 1


def test_ten_objects_per_line_at_the_door_with_a_breaking_glass_and_a_puff(gb):
    """The emerging patron's bar at its busiest: the bartender filling on it, four empties, a glass breaking at the door
    end (and one on the bar above, which falls into this bar's lines), a patron served out (the puff): no line ever holds
    more than 10 objects (the emerging patron is dropped to the BG, clipped at the door, when the estimate passes 10),
    and the door's tiles never change."""
    p, b = spawn_one(gb)
    gb.write("bar", b)
    gb.hold("a")
    for k in range(4):
        inject_mug(gb, b, 40 + 14 * k, EMPTY)
    gb.run(2)
    for bb in {b, max(0, b - 1)}:
        inject_mug(gb, bb, GAME["GLASS_X"], BREAKING)
    gb.write("mug_events", gb.mem("mug_events") + 1)
    set_patron(gb, b, DOOR_X + 1, state=PUSHED, aux=4)
    worst = 0
    for i in range(30):
        gb.run(1)
        c = line_counts(gb)
        worst = max(worst, max(c))
        assert max(c) <= 10, (i, c[bar_top_row(b) * 8:bar_top_row(b) * 8 + 24])
        assert door_tiles(gb, b) == venue_door(0)
    gb.release("a")
    assert gb.mem("served") >= 1 and worst >= 9, worst


def test_a_spawn_waits_while_there_is_no_sprite_room(gb):
    """18 empties in flight leave no OAM entries for the emerging patron's two sprites: no spawn (retried every
    SPAWN_RETRY frames), never a BG patron over the door; when room comes back he steps out behind the door."""
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
            assert door_tiles(gb, b) == venue_door(0)
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
    assert len(ps) == 1 and gb.mem("spawned") == spawned0 + 1 and ps[0]["x"] <= 1
    assert lift_of(gb, ps[0]["i"]) == LIFT_BEHIND
