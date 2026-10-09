# M5: tips and the stage show. Situations are set up by poking globals, as in test_patrons.
import re

import pytest
from conftest import GAME, LAYOUT, ROOT, bar_top_y, check_golden
from test_flow import LEVEL_CLEAR, LIFE_LOST, PAUSED, PLAYING, clear_level, lose_a_life, run_until, state
from test_patrons import (BACK_BASE, BASE, DRINKING, FULL, HELD, MAX_M, MAX_P, PUSHED, WALKING, clear_patrons,
                          drawn_tiles, go, inject_mug, lineup, map_ids, mugs, patrons, put, score, set_patron)

pytestmark = pytest.mark.timeout(60)

_ART_H = (ROOT / "build" / "art.h").read_text()
_MAIN = (ROOT / "src" / "main.c").read_text()


def art(name):
    return int(re.search(rf"#define {name} (\d+)", _ART_H).group(1))


OBJ_COIN = art("BARTENDER_FRAMES") * art("BARTENDER_TILES_PER_FRAME") + art("MUG_TILE_COUNT") + art("GLASS_TILE_COUNT") \
    + art("MUG_FILL_TILE_COUNT") + art("MUG_DRINK_TILE_COUNT")
OBJ_DANCER = OBJ_COIN + art("COIN_TILE_COUNT")
DANCER_TILES = art("DANCER_FRAMES") * art("DANCER_TILES_PER_FRAME")
TIP_FRAMES, SHOW_FRAMES, TIP_SCORE = 480, 704, 1500
MUG_DY = LAYOUT["MUG_DY"]
STAGE_Y0, STAGE_Y1 = LAYOUT["STAGE_FIRST_ROW"] * 8, (LAYOUT["STAGE_LAST_ROW"] + 1) * 8   # screen y 8..39


def w16(gb, name, v):
    gb.write(name, v & 255)
    gb.write(gb.addr(name) + 1, v >> 8)


def quiet(gb):
    """No patrons, nothing spawns, nothing blocks: a clean bar for a tip test."""
    clear_patrons(gb)
    gb.write("intro_timer", 0)
    w16(gb, "spawn_timer", 0xFFFF)
    gb.write("quota", 200)
    gb.write("tip_chance", 255)


def coin_sprites(gb):
    return [s for s in gb.visible_sprites() if OBJ_COIN <= s["tile"] < OBJ_DANCER]


def dancer_sprites(gb):
    return [s for s in gb.visible_sprites() if OBJ_DANCER <= s["tile"] < OBJ_DANCER + DANCER_TILES]


def started(gb):
    """Run until a show has begun. The emulated frame can end in the middle of the game's update, so
    the show_timer may be seen set before start_show() has finished picking the audience: settle a frame."""
    run_until(gb, lambda: gb.mem16("show_timer") > 0, 10)
    gb.run(2)


def serve(gb, bar, catch_x, x=2):
    """A pushed-back patron one step from the door: it is served in a few frames."""
    i = set_patron(gb, bar, x, state=PUSHED, aux=40)
    put(gb, "patron_catchx", i, catch_x)
    s0 = gb.mem("served")
    gb.run(8)
    assert gb.mem("served") == s0 + 1
    return i


def dist(gb):
    return list(gb.read("patron_dist", MAX_P))


# ---- tips -------------------------------------------------------------------------------
def test_served_patron_leaves_a_tip_where_it_caught_its_last_mug(gb):
    quiet(gb)
    serve(gb, 2, 90)
    assert 470 < gb.mem16("tip_timer") <= TIP_FRAMES
    assert gb.mem("tip_bar") == 2 and gb.mem("tip_x") == 90
    cs = coin_sprites(gb)
    assert len(cs) == 1
    assert cs[0]["x"] - 8 == 90 and cs[0]["y"] - 16 == bar_top_y(2) + MUG_DY
    if gb.model_name == "cgb":
        assert cs[0]["flags"] & 7 == 5, "coin OBJ palette (M13a: slot 5, shared with the show)"


def test_a_catch_remembers_where_the_mug_was_caught(gb):
    quiet(gb)
    i = set_patron(gb, 1, 20)
    gb.write("tip_chance", 255)
    inject_mug(gb, 1, 20 + 14)
    gb.run(2)
    assert gb.read("patron_state", MAX_P)[i] == PUSHED
    x = gb.read("patron_catchx", MAX_P)[i]
    assert 20 <= x < 36
    gb.run(60)                                    # pushed out through the door: served
    assert gb.mem("tip_x") == x and gb.mem("tip_bar") == 1


def test_no_tip_when_the_chance_is_never(gb):
    quiet(gb)
    gb.write("tip_chance", 0)
    serve(gb, 2, 90)
    assert gb.mem16("tip_timer") == 0 and coin_sprites(gb) == []


def test_tip_chance_is_a_probability_out_of_256(gb):
    quiet(gb)
    gb.write("tip_chance", 64)
    got = 0
    for n in range(40):
        gb.write("tip_chance", 64)
        w16(gb, "tip_timer", 0)
        serve(gb, n % 4, 50)
        got += gb.mem16("tip_timer") > 0
    assert 3 <= got <= 20, got                    # about 1 in 4


def test_only_one_tip_at_a_time(gb):
    quiet(gb)
    serve(gb, 2, 90)
    serve(gb, 3, 40)
    assert gb.mem("tip_bar") == 2 and gb.mem("tip_x") == 90 and len(coin_sprites(gb)) == 1


def test_tip_vanishes_after_480_frames(gb):
    quiet(gb)
    serve(gb, 2, 90)
    left = gb.mem16("tip_timer")
    gb.run(left - 2)
    assert gb.mem16("tip_timer") == 2
    gb.run(3)
    assert gb.mem16("tip_timer") == 0 and coin_sprites(gb) == [] and gb.mem("show_timer") == 0 \
        and gb.mem16("show_timer") == 0


def test_the_coin_glints(gb):
    quiet(gb)
    serve(gb, 2, 90)
    tiles = set()
    for _ in range(80):
        gb.run(1)
        tiles |= {s["tile"] for s in coin_sprites(gb)}
    assert tiles == {OBJ_COIN, OBJ_COIN + 2}


# ---- picking it up --------------------------------------------------------------------
def walk_onto_coin(gb, bar, coin_x):
    gb.press("down" if bar > gb.mem("bar") else "up", 1)
    gb.run(2)
    gb.hold("left")
    run_until(gb, lambda: gb.mem16("show_timer") > 0, 60)
    gb.release("left")


def test_walking_over_the_coin_scores_1500_and_starts_the_show(gb):
    quiet(gb)
    serve(gb, 1, 100)
    s0 = score(gb)
    walk_onto_coin(gb, 1, 100)
    assert gb.mem("bar") == 1 and 85 <= gb.mem("bartender_x") <= 107, "the 16 px span overlaps the 8 px coin"
    assert score(gb) == s0 + TIP_SCORE
    assert gb.mem16("tip_timer") == 0 and coin_sprites(gb) == []
    assert 0 < gb.mem16("show_timer") <= SHOW_FRAMES
    gb.run(40)
    ds = dancer_sprites(gb)
    assert len(ds) == 12, "three dancers x 4 entries"
    for s in ds:                                   # only on the stage rows
        assert STAGE_Y0 <= s["y"] - 16 and s["y"] - 16 + 16 <= STAGE_Y1, s
    assert max(s["tile"] for s in ds) < 128, "OBJ ids >= 128 would overlap the patron BG tiles"
    xs = sorted({s["x"] - 8 for s in ds})
    assert xs == [24, 32, 72, 80, 120, 128] and xs[2] - xs[0] == 48
    if gb.model_name == "cgb":
        assert {s["flags"] & 7 for s in ds} == {5}


def test_the_coin_on_another_bar_is_not_picked_up(gb):
    quiet(gb)
    serve(gb, 1, 140)                              # bar 1, x 140: the bartender at the tap on bar 0 is not there
    gb.hold("left")
    gb.run(80)
    gb.release("left")
    assert gb.mem("bar") == 0 and gb.mem16("show_timer") == 0 and gb.mem16("tip_timer") > 0


def test_standing_at_the_tap_picks_up_a_coin_that_lies_there(gb):
    quiet(gb)
    w16(gb, "tip_timer", 300)
    gb.write("tip_bar", gb.mem("bar"))
    gb.write("tip_x", GAME["TAP_X"] + 8)   # M8a: under the bartender at the fill position
    s0 = score(gb)
    started(gb)
    assert score(gb) == s0 + TIP_SCORE and gb.mem16("show_timer") > 0


def test_dancers_kick(gb):
    quiet(gb)
    w16(gb, "show_timer", SHOW_FRAMES)
    seen = set()
    for _ in range(120):
        gb.run(1)
        ds = dancer_sprites(gb)
        if len(ds) == 12:
            seen.add(tuple(sorted(s["tile"] for s in ds)))
    assert len(seen) >= 4, "stand, left kick, arms up, right kick"


def test_dancers_pop_in_and_out_one_after_the_other(gb):
    quiet(gb)
    w16(gb, "show_timer", SHOW_FRAMES)
    counts = []
    for _ in range(SHOW_FRAMES + 2):
        gb.run(1)
        counts.append(len(dancer_sprites(gb)) // 4)
    assert counts[0] == 0 and max(counts) == 3 and counts[-1] == 0
    first = [counts.index(n) for n in (1, 2, 3)]
    assert first == sorted(first) and len(set(first)) == 3


# ---- distraction ------------------------------------------------------------------------
def crowd(gb):
    """Two walking patrons on each bar, 64 px apart."""
    clear_patrons(gb)
    ps = [set_patron(gb, b, x) for b in range(4) for x in (10, 74)]
    gb.write("intro_timer", 0)
    w16(gb, "spawn_timer", 0xFFFF)
    gb.write("quota", 200)
    return ps


def test_the_show_distracts_some_walking_patrons(gb):
    ps = crowd(gb)
    w16(gb, "tip_timer", 300)
    gb.write("tip_bar", gb.mem("bar"))
    gb.write("tip_x", GAME["TAP_X"] + 8)   # M8a: under the bartender at the fill position
    started(gb)
    gb.run(4)                                      # M8b: the distracted ones shuffle (<= 4 px) onto a multiple of 8 first
    assert gb.mem16("show_timer") > 0
    d = dist(gb)
    n = sum(d[i] for i in ps)
    assert 1 <= n < len(ps), "some but not all"
    assert all(d[i] == 0 for i in range(MAX_P) if i not in ps)
    x0 = list(gb.read("patron_x", MAX_P))
    gb.run(80)                                     # 8 px per 64 frames
    x1 = list(gb.read("patron_x", MAX_P))
    for i in ps:
        if d[i]:
            assert x1[i] == x0[i], "distracted patrons stand still"
        else:
            assert x1[i] > x0[i], "the others walk on"
    assert dist(gb) == d


def test_at_least_one_is_distracted_if_any_walk(gb):
    for n in range(12):                            # different random draws
        clear_patrons(gb)
        i = set_patron(gb, n % 4, 20)
        gb.write("intro_timer", 255)
        w16(gb, "tip_timer", 300)
        gb.write("tip_bar", gb.mem("bar"))
        gb.write("tip_x", GAME["TAP_X"] + 8)   # M8a: under the bartender at the fill position
        gb.write("bartender_x", GAME["TAP_X"])
        started(gb)
        assert dist(gb)[i] == 1, n
        w16(gb, "show_timer", 0)
        put(gb, "patron_dist", i, 0)


def test_a_show_with_nobody_walking_distracts_nobody(gb):
    clear_patrons(gb)
    gb.write("intro_timer", 255)
    i = set_patron(gb, 0, 50, state=DRINKING, timer=10)
    w16(gb, "tip_timer", 300)
    gb.write("tip_bar", 0)
    gb.write("tip_x", GAME["TAP_X"] + 8)   # M8a: under the bartender at the fill position
    started(gb)
    assert gb.mem16("show_timer") > 0 and sum(dist(gb)) == 0


# ---- M8b: distracted patrons turn round to watch the stage ------------------------------------------
DRAW_BACK = 0x80


def facing(gb, i):
    return gb.read("patron_facing", MAX_P)[i]


def back_ids(variant, x):
    """(column, [row0, row1]) of a back view at x (a multiple of 8): 2 columns of 2x2 tiles."""
    t = BACK_BASE + variant * 4
    return x >> 3, [[t, t + 1], [t + 2, t + 3]]


def watcher(gb, bar, x, variant=0, others=()):
    """One distracted walker at x (and plain walkers at `others`) with a show running."""
    clear_patrons(gb)
    gb.write("intro_timer", 0)
    w16(gb, "spawn_timer", 0xFFFF)
    gb.write("quota", 200)
    i = set_patron(gb, bar, x, variant=variant)
    for ox in others:
        set_patron(gb, bar, ox)
    w16(gb, "show_timer", 300)
    put(gb, "patron_dist", i, 1)
    return i


@pytest.mark.parametrize("x0,x1", [(45, 48), (42, 40), (44, 40), (47, 48), (41, 40), (48, 48)])
def test_a_distracted_patron_snaps_to_a_multiple_of_8_and_shows_its_back(gb, x0, x1):
    i = watcher(gb, 2, x0, variant=1)
    xs, turned = [], None
    for f in range(6):
        gb.run(1)
        xs.append(gb.read("patron_x", MAX_P)[i])
        if turned is None and facing(gb, i):
            turned = f
            assert xs[-1] == x1 and gb.read("patron_draw", MAX_P)[i] == x1 | DRAW_BACK, "turns on arrival"
    moves = sum(a != b for a, b in zip([x0] + xs, xs))
    assert xs[-1] == x1 and all(abs(b - a) <= 1 for a, b in zip([x0] + xs, xs)), xs
    assert moves == abs(x1 - x0) <= 4, "1 px a frame, 4 frames at most"
    assert turned is not None and turned <= moves + 1, (turned, xs)
    assert facing(gb, i) == 1 and gb.read("patron_draw", MAX_P)[i] == x1 | DRAW_BACK
    gb.run(2)                                      # the copy goes out in the next VBlank
    col, ids = back_ids(1, x1)
    assert [r[:2] for r in map_ids(gb, 2, col)] == ids, "back-view tile ids"
    assert all(t < BASE for t in (r[2] for r in map_ids(gb, 2, col))), "the 3rd column of the footprint is wall"
    for _ in range(60):                            # stays put, still turned round, no bob
        gb.run(1)
        assert gb.read("patron_x", MAX_P)[i] == x1 and facing(gb, i) == 1
        assert gb.read("patron_draw", MAX_P)[i] == x1 | DRAW_BACK


def other_watcher_first(gb, x, ox):
    """A watcher at ox, turned round already, then one at x who starts his shuffle (bar 1, nobody walks)."""
    i = watcher(gb, 1, x, others=(ox,))
    put(gb, "patron_dist", i, 0)
    put(gb, "patron_dist", i + 1, 1)
    gb.write("intro_timer", 255)
    gb.run(2)
    assert facing(gb, i + 1) == 1 and gb.read("patron_x", MAX_P)[i] == x
    put(gb, "patron_dist", i, 1)
    return i


def test_the_shuffle_passes_a_walker_but_never_lands_on_another_watcher(gb):
    """M13b (was: the shuffle kept PATRON_SPACING from the patron behind). x 43 wants 40 (columns 5-6). A plain walker
    behind him in those columns does not stop him (walkers can be lifted). Another watcher standing in his back view at
    32 (columns 4-5) does: neither can be lifted, so they would cover each other; he keeps facing the bar at 43."""
    i = watcher(gb, 1, 43, others=(30,))
    gb.write("intro_timer", 255)                   # the walker behind stays where he is
    gb.run(10)
    assert gb.read("patron_x", MAX_P)[i] == 40 and facing(gb, i) == 1, "a walker does not block the shuffle"
    i = other_watcher_first(gb, 43, 32)
    gb.run(10)
    assert facing(gb, i + 1) == 1 and gb.read("patron_x", MAX_P)[i + 1] == 32
    x = gb.read("patron_x", MAX_P)[i]
    assert x == 43 and facing(gb, i) == 0 and gb.read("patron_draw", MAX_P)[i] == 43, "waits facing the bar"


def test_four_px_off_with_a_watcher_on_the_left_place_goes_the_other_way(gb):
    """M13b (was: a walker 33 px behind). x 44, another watcher in his back view at 32: the place at 40 shares his
    column 5, so he goes right to 48 (columns 6-7) and turns round."""
    i = other_watcher_first(gb, 44, 32)
    gb.run(6)
    assert gb.read("patron_x", MAX_P)[i] == 48 and facing(gb, i) == 1
    assert gb.read("patron_x", MAX_P)[i + 1] == 32 and facing(gb, i + 1) == 1


def test_the_shuffle_never_reaches_the_tap(gb):
    """x 117 would round to 120, which is the tap end (PATRON_FAR_X): he stays and costs no life."""
    lives = gb.mem("lives")
    i = watcher(gb, 0, 117)
    gb.run(30)
    assert gb.read("patron_x", MAX_P)[i] == 117 and facing(gb, i) == 0 and gb.mem("lives") == lives
    assert gb.read("patron_state", MAX_P)[i] == WALKING


def test_after_the_show_it_turns_back_and_walks_on(gb):
    i = watcher(gb, 3, 61, variant=2)
    gb.run(5)
    assert gb.read("patron_x", MAX_P)[i] == 64 and facing(gb, i) == 1
    w16(gb, "show_timer", 2)
    gb.run(3)
    assert gb.mem16("show_timer") == 0 and dist(gb)[i] == 0
    assert facing(gb, i) == 0 and gb.read("patron_draw", MAX_P)[i] == gb.read("patron_x", MAX_P)[i]
    gb.run(2)
    x = gb.read("patron_x", MAX_P)[i]
    col, ids = drawn_tiles(2, x, 3)
    assert map_ids(gb, 3, col) == ids, "front view again"
    gb.run(80)
    assert gb.read("patron_x", MAX_P)[i] > 64, "walking again"


def test_a_watcher_ignores_mugs(gb):
    i = watcher(gb, 1, 40)
    gb.run(5)
    inject_mug(gb, 1, 50)
    gb.run(3)
    assert gb.read("patron_state", MAX_P)[i] == WALKING and facing(gb, i) == 1


def test_show_backs_golden(gb):
    """Mid-show: three watchers in their back views (A, B, C) on bars 0, 1 and 3, a front-facing walker on bar 2."""
    gb.write("intro_timer", 255)
    gb.write("quota", 200)
    lineup(gb, {0: [(30, 0, 1)], 1: [(75, 1, 1)], 2: [(45, 1, 0)], 3: [(52, 2, 1)]})   # (the start patrons are moved)
    w16(gb, "show_timer", 200)
    gb.write("dancer_frame", 0)
    gb.write("dance_tick", 0)
    gb.run(15)
    assert sorted(gb.read("patron_facing", MAX_P)[:4]) == [0, 1, 1, 1]
    check_golden(gb, "show_backs")


def show_with(gb, bar, specs):
    """Patrons (x, distracted) on one bar, show running. Returns the patron slots."""
    clear_patrons(gb)
    gb.write("intro_timer", 0)
    w16(gb, "spawn_timer", 0xFFFF)
    gb.write("quota", 200)
    ids = []
    for x, d in specs:
        i = set_patron(gb, bar, x)
        put(gb, "patron_dist", i, d)
        ids.append(i)
    w16(gb, "show_timer", 300)
    return ids


def test_a_full_mug_slides_past_a_distracted_patron_to_the_next_one(gb):
    a, b = show_with(gb, 1, [(40, 0), (90, 1)])    # b is the distracted one, further right
    inject_mug(gb, 1, 136)
    run_until(gb, lambda: gb.read("patron_state", MAX_P)[a] == PUSHED, 120)
    assert gb.read("patron_state", MAX_P)[b] == WALKING and gb.read("patron_x", MAX_P)[b] == 88   # M8b: shuffled to 88
    assert [m["state"] for m in mugs(gb)] == [HELD]
    assert gb.read("patron_mug", MAX_P)[a] != 255 and gb.read("patron_mug", MAX_P)[b] == 255


def test_a_full_mug_is_caught_by_the_same_patron_once_he_pays_attention(gb):
    a, b = show_with(gb, 1, [(40, 0), (90, 0)])
    inject_mug(gb, 1, 136)
    run_until(gb, lambda: gb.read("patron_state", MAX_P)[b] == PUSHED, 120)
    assert gb.read("patron_state", MAX_P)[a] == WALKING


def test_a_mug_that_passes_everyone_falls_off_the_end(gb):
    (a,) = show_with(gb, 1, [(40, 1)])
    lives = gb.mem("lives")
    inject_mug(gb, 1, 136)
    run_until(gb, lambda: state(gb) == LIFE_LOST, 120)
    assert gb.mem("lives") == lives - 1 and gb.read("patron_state", MAX_P)[a] == WALKING


def test_new_patrons_during_the_show_are_not_distracted(gb):
    clear_patrons(gb)
    gb.write("intro_timer", 0)
    gb.write("quota", 200)
    w16(gb, "show_timer", 300)
    w16(gb, "spawn_timer", 0)
    gb.run(3)
    ps = patrons(gb)
    assert len(ps) == 1 and dist(gb)[ps[0]["i"]] == 0


def test_when_the_show_ends_patrons_resume_and_spawning_speeds_up_once(gb):
    a, b = show_with(gb, 1, [(40, 1), (100, 1)])
    w16(gb, "show_timer", 3)
    w16(gb, "spawn_timer", 0xFFFF)
    gb.run(5)
    assert gb.mem16("show_timer") == 0 and dist(gb) == [0] * MAX_P
    assert gb.mem16("spawn_timer") < gb.mem16("spawn_interval") // 2, "new patrons come sooner"
    assert dancer_sprites(gb) == []
    x0 = gb.read("patron_x", MAX_P)[a]
    gb.run(70)
    assert gb.read("patron_x", MAX_P)[a] > x0, "walking again"
    assert gb.mem16("spawn_timer") < 0xFFFF and gb.mem16("spawn_timer") <= gb.mem16("spawn_interval"), \
        "boosted once: it is not reset again"


# ---- sprite budget ----------------------------------------------------------------------
def test_oam_and_scanline_budget_during_a_busy_show(gb):
    clear_patrons(gb)
    gb.write("intro_timer", 255)
    gb.write("quota", 200)
    for i in range(4):
        set_patron(gb, i, 20 + 32 * i)
    for b in range(4):                             # 20 mugs: the whole pool, 6 on bar 0
        for k in range(6 if b == 0 else 5):
            if len(mugs(gb)) < 20:
                inject_mug(gb, b, 40 + 12 * k, state=FULL if k % 2 else 2)
    w16(gb, "show_timer", 200)
    w16(gb, "tip_timer", 300)
    gb.write("tip_bar", 0)
    gb.write("tip_x", 100)
    gb.write("bartender_x", GAME["TAP_X"])
    gb.write("bar", 0)
    gb.hold("a")
    for _ in range(30):
        gb.run(1)
        spr = gb.visible_sprites()
        assert len(spr) <= 40
        counts = [0] * 144
        for s in spr:
            top = s["y"] - 16
            for line in range(max(top, 0), min(top + 16, 144)):
                counts[line] += 1
        assert max(counts) <= 10, (max(counts), counts.index(max(counts)))
        if state(gb) != PLAYING:
            break
    gb.release("a")
    assert len(mugs(gb)) <= 20
    assert len(dancer_sprites(gb)) == 12 and len(coin_sprites(gb)) == 1


def test_obj_tiles_stay_below_the_shared_block(gb):
    assert OBJ_DANCER + DANCER_TILES <= 128, (OBJ_DANCER, DANCER_TILES)
    assert OBJ_COIN + art("COIN_TILE_COUNT") == OBJ_DANCER


# ---- game flow ---------------------------------------------------------------------------
def test_pause_freezes_the_show_and_the_tip(gb):
    quiet(gb)
    w16(gb, "show_timer", 200)
    w16(gb, "tip_timer", 300)
    gb.run(10)
    s, t = gb.mem16("show_timer"), gb.mem16("tip_timer")
    gb.press("start", 2)
    gb.run(2)
    assert state(gb) == PAUSED
    s, t = gb.mem16("show_timer"), gb.mem16("tip_timer")
    gb.run(60)
    assert (gb.mem16("show_timer"), gb.mem16("tip_timer")) == (s, t)
    gb.press("start", 2)
    gb.run(10)
    assert state(gb) == PLAYING and gb.mem16("show_timer") < s and gb.mem16("tip_timer") < t


def test_losing_a_life_clears_the_show_and_the_tip(gb):
    quiet(gb)
    w16(gb, "show_timer", 300)
    w16(gb, "tip_timer", 300)
    gb.run(5)
    lose_a_life(gb)
    gb.run(130)
    assert state(gb) == PLAYING
    assert gb.mem16("show_timer") == 0 and gb.mem16("tip_timer") == 0
    assert dancer_sprites(gb) == [] and coin_sprites(gb) == [] and sum(dist(gb)) == 0


def test_level_clear_ignores_the_tip_and_forgets_it(gb):
    w16(gb, "tip_timer", 300)
    gb.write("tip_bar", 3)
    gb.write("tip_x", 100)
    clear_level(gb)
    assert state(gb) == LEVEL_CLEAR
    assert gb.mem16("tip_timer") == 0 and coin_sprites(gb) == []
    gb.run(200)
    assert state(gb) == PLAYING and gb.mem16("tip_timer") == 0


# ---- golden ---------------------------------------------------------------------------
def test_show_golden(gb):
    """Dancers mid-kick, a coin on bar 1, one patron watching the show (the two start patrons are moved, not
    replaced, so the tilemap holds no stale figures)."""
    gb.write("intro_timer", 255)
    gb.write("quota", 200)
    a, b = [p["i"] for p in patrons(gb)]
    put(gb, "patron_x", a, 56)
    put(gb, "patron_x", b, 40)
    c = set_patron(gb, 3, 88)
    put(gb, "patron_dist", b, 1)
    w16(gb, "show_timer", 200)
    w16(gb, "tip_timer", 300)
    gb.write("tip_bar", 1)
    gb.write("tip_x", 100)
    gb.write("dancer_frame", 0)
    gb.write("dance_tick", 0)
    gb.run(15)                                     # the first step (12 frames) is over: left kick
    assert gb.mem("dancer_frame") == 1 and len(dancer_sprites(gb)) == 12
    check_golden(gb, "show")
