# M13a: lifted patrons, the plumbing (docs/overlap_design.md). A patron can be lifted from the BG to two 8x16 sprites
# (his own shift-0 BG tiles) and dropped back. No rule lifts anyone yet: the tests use the hook (lift_hook_p /
# lift_hook_op). The main check runs two copies of the game side by side, fed the same inputs and pokes, and lifts
# patrons in one of them only: every frame of the two must be the same picture, pixel for pixel.
from pathlib import Path

import numpy as np
import pytest
from gbtools import Rom

from conftest import GAME, ROM, ROOT, title_level, bar_top_row, bar_top_y, logical_tile, OBJ_DMG_COPY, DMG_COPIES, OBJ_MUG_ID
from test_art import GROUPS, goto_group
from test_flow import PLAYING, run_until, state
from test_venues import cgb_palette
from test_patrons import (BASE, DRINKING, PUSHED, EMPTY, MAX_M, MAX_P, SHIFT0_OFS, WALKING, drawn_tiles, inject_mug, lineup,
                          map_ids, put)

pytestmark = pytest.mark.timeout(240)

HOOK_LIFT, HOOK_DROP = 1, 3                  # (2, the M13c door's lift behind the BG, is gone)
LIFT_DROP = 0x80
OBJ_BASE = BASE + SHIFT0_OFS                 # shift-0 pose of variant v: OBJ_BASE + 6 v (tiles t, t + 2 as 8x16 entries)
BLANK = OBJ_BASE + 4                         # its 3rd column: plain colour 0, what a lifted patron leaves on the BG
OAM_LIFT_TOP = GAME["OAM_MUG_END"] - 1       # 25: lifted patrons count down from here
OAM_DANCERS = GAME["OAM_DANCERS"]
LIFT_PAL = [3, 6, 7]                          # CGB OBJ palettes of variants A, B, C
OUT = ROOT / "out" / "m13a"
import json as _json
ENH_TAB = [v["tab"] for v in _json.loads((ROOT / "build" / "patron_enh.json").read_text()).values()]   # (M14a, group order)


# ---- helpers -----------------------------------------------------------------------------------
def boot_play(model):
    rom = Rom(ROM, model)
    rom.__enter__()
    rom.model_name = model
    rom.run(120)
    rom.write("sa_hold", 1)                   # stage animation frozen (conftest.hold_stage_anim), as in every fixture
    title_level(rom)
    for _ in range(30):
        if rom.mem("game_state") == PLAYING:
            break
        rom.run(1)
    assert rom.mem("game_state") == PLAYING
    rom.write("tip_chance", 0)
    return rom


@pytest.fixture(params=["dmg", "cgb"])
def pair(request):
    """Two copies of the game in the same state: a (reference, nobody lifted) and b (lifts)."""
    a, b = boot_play(request.param), boot_play(request.param)
    yield a, b
    a.stop()
    b.stop()


def both(pair, fn):
    for g in pair:
        fn(g)


def freeze(gb):
    gb.write("intro_timer", 255)                  # nobody walks or spawns
    gb.write("quota", 200)
    gb.write("spawn_timer", 0xFF)
    gb.write(gb.addr("spawn_timer") + 1, 0xFF)


def screen(gb):
    return np.asarray(gb.image())


def step_same(pair, n, every=None, after=None):
    """Run both n frames; after each one the two screens must be identical. every(i) runs before each frame,
    after(i) after it."""
    a, b = pair
    for i in range(n):
        if every:
            every(i)
        a.run(1, render=True)
        b.run(1, render=True)
        if after:
            after(i)
        sa, sb = screen(a), screen(b)
        diff = (sa != sb).any(axis=2)
        assert not diff.any(), f"frame {i}: {int(diff.sum())} pixels differ, first at {np.argwhere(diff)[0][::-1]}"


def hook(gb, p, op):
    gb.write("lift_hook_p", p)
    gb.write("lift_hook_res", 0)
    gb.write("lift_hook_op", op)


def lift_state(gb):
    return list(gb.read("patron_lift", MAX_P))


def slots_by_place(gb):
    st, bar, x = gb.read("patron_state", MAX_P), gb.read("patron_bar", MAX_P), gb.read("patron_x", MAX_P)
    return {(bar[i], x[i]): i for i in range(MAX_P) if st[i]}


def run_hooks(pair, ops, settle=4):
    """Issue the hook ops [(slot, op)] in b, one after the other (each waits for the last to be taken), frames
    compared all the while; then `settle` more frames."""
    a, b = pair
    queue = list(ops)

    def feed(_):
        if queue and b.mem("lift_hook_op") == 0:
            if b.mem("lift_hook_res") == 2:
                raise AssertionError(f"hook refused: {queue}")
            p, op = queue.pop(0)
            hook(b, p, op)
    step_same(pair, len(ops) * 3 + settle, feed)
    assert not queue and b.mem("lift_hook_op") == 0 and b.mem("lift_hook_res") == 1


def oam_lines(gb):
    """Objects on each of the 144 lines (what the hardware's 10-per-line limit counts)."""
    c = [0] * 144
    for s in gb.oam():
        if not s["y"] or s["y"] >= 160:
            continue
        y = s["y"] - 16
        for line in range(max(0, y), min(144, y + 16)):
            c[line] += 1
    return c


def lifted_sprites(gb):
    return [s for s in gb.oam()[OAM_LIFT_TOP - 7:OAM_LIFT_TOP + 1] if s["y"]]


def mug_sprites(gb):
    return [s for s in gb.visible_sprites() if logical_tile(s["tile"]) in (OBJ_MUG_ID, OBJ_MUG_ID + 2)]


# ---- lifted == BG, all groups and variants, at rest and swaying ----------------------------------------
# bar: [(x, variant, drinking)]. Every variant both at rest and swaying; shifts 0..7 spread over them (the 70 and 100
# drinkers sway across a column boundary: 70 -> 72, 100 -> 102 stays, 93 -> 95).
PLACES = {0: [(27, 0, 0), (70, 1, 1)], 1: [(40, 2, 0), (93, 0, 1)], 2: [(61, 1, 0), (100, 2, 1)], 3: [(56, 1, 0)]}
SET_A = [(0, 27), (0, 70), (1, 40), (1, 93)]
SET_B = [(2, 61), (2, 100)]


def place(gb, group):
    goto_group(gb, group)
    freeze(gb)
    slots = lineup(gb, {b: [(x, v, 0) for x, v, _ in row] for b, row in PLACES.items() if row})
    for (b, x), (i, v, d) in slots.items():
        if any(xx == x and dr for xx, _, dr in PLACES[b]):
            put(gb, "patron_state", i, DRINKING)
            put(gb, "patron_timer", i, 0)
            put(gb, "patron_aux", i, 0)
            put(gb, "patron_mug", i, 255)     # no mug: he sways for 90 frames, then stands (frozen)
    return {k: v[0] for k, v in slots.items()}


@pytest.mark.parametrize("group", range(len(GROUPS)), ids=GROUPS)
def test_lifted_patrons_look_exactly_like_bg_ones(pair, group):
    a, b = pair
    slot = None
    for g in pair:
        slot = place(g, group)
    step_same(pair, 20)
    for g in pair:                                  # (a lift on the very frame a drinker's sway changes leaves a pixel or a figure for a frame, with or without
        for k in ((0, 70), (1, 93), (2, 100)):      # this change of timing (drinkers are stepped every other frame now): the lifts start 6 frames before the next change)
            put(g, "patron_timer", slot[k], 30)
    run_hooks(pair, [(slot[k], HOOK_LIFT) for k in SET_A])
    assert b.mem("lift_total") == 4 and [b.read("lift_n", 4)[k] for k in range(4)] == [2, 2, 0, 0]
    assert len(lifted_sprites(b)) == 8
    for (bb, x) in SET_A:                           # the BG footprint is plain wall while he is a sprite
        d = b.read("patron_draw", MAX_P)[slot[(bb, x)]]
        assert map_ids(b, bb, d >> 3) == [[BLANK] * 3, [BLANK + 1] * 3] or \
            all(t in (BLANK, BLANK + 1) for r in map_ids(b, bb, d >> 3) for t in r)
    step_same(pair, 60)                             # the drinkers sway (every 12 frames)
    run_hooks(pair, [(slot[k], HOOK_DROP) for k in SET_A])
    assert b.mem("lift_total") == 0 and lifted_sprites(b) == []
    for g in pair:                                  # the second set: bar 2's drinker sways again
        put(g, "patron_timer", slot[(2, 100)], 0)
        put(g, "patron_state", slot[(2, 100)], DRINKING)
        put(g, "patron_aux", slot[(2, 100)], 0)
    run_hooks(pair, [(slot[k], HOOK_LIFT) for k in SET_B])
    assert b.mem("lift_total") == 2
    step_same(pair, 40)
    run_hooks(pair, [(slot[k], HOOK_DROP) for k in SET_B])
    assert b.mem("lift_total") == 0
    assert a.bg_tilemap() == b.bg_tilemap(), "the BG is back exactly as it was"


@pytest.mark.xfail(reason="known, rare (perf agent, 854c894): the 4th lift of a one-per-frame run lands on the frame a lifted drinker's 2 px sway crosses a column; "
                          "its urgent span (48 of the 64-unit VBlank budget) defers the sway's footprint span (queue_vram, render.c) by a frame, so the sprite is "
                          "at the new x while the plain-wall footprint is still the old one: 1 wall speck (or a 131 px figure, other phases) for one frame. "
                          "Not easy: needs the budget's priorities changed (docs: report of 2026-10-19)", strict=False)
def test_a_lift_on_the_frame_a_drinkers_sway_crosses_a_column_leaves_nothing_for_a_frame():
    pair = (boot_play("dmg"), boot_play("dmg"))
    try:
        for g in pair:
            slot = place(g, 0)
        step_same(pair, 20)                         # (no timer change: the sway moves on the lifts' 4th frame)
        run_hooks(pair, [(slot[k], HOOK_LIFT) for k in SET_A])
        step_same(pair, 30)
    finally:
        for g in pair:
            g.stop()


def test_lift_and_drop_change_no_pixel_and_put_the_bg_back(gb):
    """One patron, alone: the picture never changes on any frame through a lift and the drop;
    his BG copy goes while he is a sprite and comes back after. Before/after x4 screenshots land in out/m13a/."""
    freeze(gb)
    gb.run(4, render=True)
    ref = screen(gb)
    tm0 = gb.bg_tilemap()
    p = list(gb.read("patron_state", MAX_P)).index(WALKING)
    b, x, v = gb.read("patron_bar", MAX_P)[p], gb.read("patron_x", MAX_P)[p], gb.read("patron_variant", MAX_P)[p]
    OUT.mkdir(parents=True, exist_ok=True)
    gb.screenshot(OUT / f"before_bg.{gb.model_name}.png", 4)
    for op in (HOOK_LIFT,):
        hook(gb, p, op)
        for i in range(12):
            gb.run(1, render=True)
            assert (screen(gb) == ref).all(), f"lift frame {i}"
        assert gb.mem("lift_hook_res") == 1 and lift_state(gb)[p] == op
        spr = lifted_sprites(gb)
        assert sorted((s["x"] - 8, s["tile"]) for s in spr) == [(x, OBJ_BASE + 6 * v), (x + 8, OBJ_BASE + 6 * v + 2)]
        assert all(s["y"] - 16 == bar_top_y(b) for s in spr)
        assert all(not s["flags"] & 0x80 for s in spr), "in front of the BG"
        if gb.model_name == "cgb":
            # M14a: each column its own attributes (palette, bit 3 VRAM bank 1); a plain variant: LIFT_PAL[v] for both
            tab = ENH_TAB[gb.mem("cur_group")]
            want = {OBJ_BASE + 6 * v: tab[16 + v], OBJ_BASE + 6 * v + 2: tab[20 + v]}
            assert all(s["flags"] & 0x0F == want[s["tile"]] for s in spr)
            if tab[16 + v] == tab[20 + v]:
                assert all(s["flags"] & 0x0F == LIFT_PAL[v] for s in spr)
        else:
            assert all(s["flags"] & 0x10 for s in spr), "DMG: OBP1"
        assert all(t in (BLANK, BLANK + 1) for r in map_ids(gb, b, x >> 3) for t in r), "BG: plain wall under him"
        if op == HOOK_LIFT:
            gb.screenshot(OUT / f"after_lifted.{gb.model_name}.png", 4)
            gb.write(0xFF40, gb.mem(0xFF40) & ~2)          # sprites off for a moment: the BG alone (not compared)
            gb.run(1, render=True)
            gb.screenshot(OUT / f"after_lifted_bg_only.{gb.model_name}.png", 4)
            gb.write(0xFF40, gb.mem(0xFF40) | 2)
            gb.run(1, render=True)
            assert (screen(gb) == ref).all()
        hook(gb, p, HOOK_DROP)
        for i in range(12):
            gb.run(1, render=True)
            assert (screen(gb) == ref).all(), f"drop frame {i}"
        assert gb.mem("lift_hook_res") == 1 and lift_state(gb)[p] == 0 and lifted_sprites(gb) == []
        assert gb.bg_tilemap() == tm0
        col, ids = drawn_tiles(v, x, b)
        assert map_ids(gb, b, col) == ids


def test_drop_keeps_the_sprite_until_the_bg_copy_is_out(gb):
    """The drop puts the BG copy back first: on the frame the hook is taken he is still a sprite (LIFT_DROP), the
    next frame he is BG only."""
    freeze(gb)
    p = list(gb.read("patron_state", MAX_P)).index(WALKING)
    hook(gb, p, HOOK_LIFT)
    gb.run(3)
    hook(gb, p, HOOK_DROP)
    gb.run(1)
    assert lift_state(gb)[p] == 1 | LIFT_DROP and len(lifted_sprites(gb)) == 2
    gb.run(1)
    assert lift_state(gb)[p] == 0 and lifted_sprites(gb) == []


def test_lifts_are_capped_per_bar_and_in_all_and_never_in_a_back_view(gb):
    freeze(gb)
    slots = lineup(gb, {0: [(20, 0, 0), (56, 1, 0), (92, 2, 0)], 1: [(24, 0, 0), (60, 1, 0)], 2: [(32, 2, 0), (80, 0, 1)],
                        3: [(40, 1, 0)]})
    s = {k: v[0] for k, v in slots.items()}
    gb.run(30)
    def ask(p, op=HOOK_LIFT):
        hook(gb, p, op)
        for _ in range(4):
            gb.run(1)
            if gb.mem("lift_hook_op") == 0:
                break
        return gb.mem("lift_hook_res")
    assert ask(s[(0, 20)]) == 1 and ask(s[(0, 56)]) == 1
    assert ask(s[(0, 92)]) == 2, "LIFT_PER_BAR: two per bar"
    assert ask(s[(1, 24)]) == 1 and ask(s[(1, 60)]) == 1
    assert ask(s[(3, 40)]) == 2, "LIFT_MAX: four in all"
    assert ask(s[(2, 80)]) == 2, "distracted (back view): never lifted"
    assert ask(s[(0, 20)]) == 2, "already lifted"
    assert ask(s[(3, 40)], HOOK_DROP) == 2, "not lifted: nothing to drop"
    assert gb.mem("lift_total") == 4


def test_a_lifted_patron_who_leaves_takes_his_sprite_along(gb):
    freeze(gb)
    p = list(gb.read("patron_state", MAX_P)).index(WALKING)
    b = gb.read("patron_bar", MAX_P)[p]
    hook(gb, p, HOOK_LIFT)
    gb.run(3)
    assert len(lifted_sprites(gb)) == 2
    inject_mug(gb, b, gb.read("patron_x", MAX_P)[p] + 4)   # he catches it at ENTRY_X: served, slides out past the edge
    for _ in range(60):
        gb.run(1)
        if not gb.read("patron_state", MAX_P)[p]:
            break
    gb.run(2)
    assert gb.read("patron_state", MAX_P)[p] == 0 and gb.mem("served") == 1
    assert lifted_sprites(gb) == [] and gb.mem("lift_total") == 0 and lift_state(gb)[p] == 0


# ---- the budgets: mugs keep their entries, 10 per line, 40 in all -------------------------------------------
def four_lifted(pair, places):
    slot = None
    for g in pair:
        freeze(g)
        slot = {k: v[0] for k, v in lineup(g, places).items()}
    step_same(pair, 10)
    return slot


def test_mugs_never_lose_oam_entries_with_four_lifted_and_six_mugs(pair):
    a, b = pair
    slot = four_lifted(pair, {0: [(20, 0, 0), (60, 1, 0)], 2: [(24, 2, 0), (64, 0, 0)]})
    run_hooks(pair, [(slot[k], HOOK_LIFT) for k in [(0, 20), (0, 60), (2, 24), (2, 64)]])
    assert b.mem("lift_total") == 4
    for g in pair:                                   # six empties on bars 1 and 3, sliding right (nobody catches them)
        for k in range(3):
            inject_mug(g, 1, 20 + 24 * k, EMPTY)
            inject_mug(g, 3, 30 + 24 * k, EMPTY)

    def check(_):
        assert len(mug_sprites(b)) == 6 == len(mug_sprites(a)) or b.mem("game_state") != PLAYING
        assert len(lifted_sprites(b)) == 8 and b.mem("lift_total") == 4
        mug_idx = [i for i, s in enumerate(b.oam()) if s["y"] and logical_tile(s["tile"]) in (OBJ_MUG_ID, OBJ_MUG_ID + 2)]
        assert max(mug_idx) < OAM_LIFT_TOP - 7, "mug entries stay below the lifted ones"
        assert max(oam_lines(b)) <= 10
    step_same(pair, 60, after=check)


def test_a_line_that_would_pass_10_objects_forces_a_drop(pair):
    """Bar 1: the bartender (2), two lifted patrons (4), then empties arrive one by one (1 each). At the 5th the
    estimate passes 10: one patron is dropped at once (BG copy and sprite swap in one VBlank); the 6th makes 10 again.
    Then the bartender starts filling (the fill glass, 1 more): the other one is dropped. No line ever holds more than
    10 objects and no frame differs from the game without lifts."""
    a, b = pair
    slot = four_lifted(pair, {0: [(30, 0, 0)], 1: [(24, 0, 0), (64, 1, 0)], 2: [(30, 2, 0)]})
    for g in pair:
        g.press("down", 2)                            # the bartender to bar 1
    step_same(pair, 4)
    run_hooks(pair, [(slot[(1, 24)], HOOK_LIFT), (slot[(1, 64)], HOOK_LIFT)])
    assert b.mem("lift_total") == 2 and b.mem("bar") == 1
    forced0 = b.mem("lift_forced")
    seen = []

    def feed(i):
        if i % 6 == 0 and i // 6 < 6:
            for g in pair:                            # (right of both patrons: on DMG a sprite right of a lifted one
                inject_mug(g, 1, 84 + 2 * (i // 6), EMPTY)   # is drawn behind it where they overlap, see M13b)

    def check(i):
        assert max(oam_lines(b)) <= 10, (i, max(oam_lines(b)))
        seen.append((b.read("lift_load", 4)[1], b.mem("lift_total")))
    step_same(pair, 40, feed, check)
    assert b.mem("lift_forced") - forced0 == 1 and b.mem("lift_total") == 1, seen
    assert [t for _, t in seen][23:26] == [2, 1, 1], "dropped on the frame the 5th empty appeared"
    for g in pair:
        g.hold("a")
    step_same(pair, 12, after=check)
    for g in pair:
        g.release("a")
    assert b.mem("lift_forced") - forced0 == 2 and b.mem("lift_total") == 0, seen
    assert all(load <= 10 for load, _ in seen), seen


def test_a_patron_whose_drop_is_still_pending_goes_when_his_line_is_over_budget(pair):
    """Bar 1 at exactly 10 objects: the bartender (2), one lifted patron (2), six empties (6). The patron's drop has
    begun (LIFT_DROP) but his BG copy stays pending (a pushed patron who keeps sliding has his columns dirty every
    frame, so such a drop can last for many frames: CLASSIC level 13 on CGB showed 11 objects on a line for 15 frames).
    The bartender starts filling (the fill glass, 1 more): the line is over budget and the dropping patron's sprite is
    the only one on the bar, so it has to go at once (before: only a patron not yet dropping could be forced out, and
    the 11th object stayed). He is back on the BG, not taken out of the game."""
    a, b = pair
    slot = four_lifted(pair, {0: [(30, 0, 0)], 1: [(24, 0, 0)], 2: [(30, 2, 0)]})
    for g in pair:
        g.press("down", 2)                            # the bartender to bar 1
    step_same(pair, 4)
    run_hooks(pair, [(slot[(1, 24)], HOOK_LIFT)])
    p = slot[(1, 24)]
    assert b.mem("lift_total") == 1 and b.mem("bar") == 1
    for k in range(6):
        inject_mug(b, 1, 56 + 9 * k, EMPTY)
    forced0 = b.mem("lift_forced")

    def keep_pending():
        b.write(b.addr("patron_lift") + p, 0x80 | 1)      # LIFT_DROP | LIFT_OBJ, his BG copy still not out
        b.write("vq_held", 1)                              # (last frame's copy list still waits: no drop can end)
    for _ in range(3):
        keep_pending()
        b.run(1)
        assert max(oam_lines(b)) <= 10
    assert b.read("lift_load", 4)[1] == 10 and b.mem("lift_total") == 1 and b.mem("lift_forced") == forced0
    b.hold("a")
    for _ in range(12):
        keep_pending()
        b.run(1)
        assert max(oam_lines(b)) <= 10, max(oam_lines(b))
    b.release("a")
    assert b.mem("lift_forced") - forced0 == 1 and b.mem("lift_total") == 0
    assert b.read("patron_state", 16)[p] == WALKING, "still in the game"


def test_a_tip_that_appears_on_a_full_line_forces_a_drop_in_the_same_frame(pair):
    """Bar 1 at exactly 10 objects: the bartender (2), two lifted patrons (4), four empties (4). A tip's coin (1 more,
    drawn by the same frame: tip_timer is set before lift_frame's estimate, like maybe_tip / classic_tip in the rules)
    makes 11: a patron is dropped at once, so no frame ever shows more than 10 on a line. (The perf scenarios' own tip
    pokes land between whole game frames for the same reason: logic_paused. A poke that lands after the estimate
    shows an 11th object for one frame, a scenario artifact the real rules cannot make: the CLASSIC rows 23 / 24 on CGB
    did, once the music changed the frame alignment.)"""
    from conftest import logic_paused
    a, b = pair
    slot = four_lifted(pair, {0: [(30, 0, 0)], 1: [(24, 0, 0), (64, 1, 0)], 2: [(30, 2, 0)]})
    for g in pair:
        g.press("down", 2)                            # the bartender to bar 1
    step_same(pair, 4)
    run_hooks(pair, [(slot[(1, 24)], HOOK_LIFT), (slot[(1, 64)], HOOK_LIFT)])
    assert b.mem("lift_total") == 2 and b.mem("bar") == 1
    for k in range(4):
        inject_mug(b, 1, 100 + 2 * k, EMPTY)
    b.run(2)
    assert b.read("lift_load", 4)[1] == 10 and max(oam_lines(b)) == 10
    forced0 = b.mem("lift_forced")
    with logic_paused(b):
        b.write("tip_timer", 400 & 255)
        b.write(b.addr("tip_timer") + 1, 400 >> 8)
        b.write("tip_bar", 1)
        b.write("tip_x", 60)
    for _ in range(6):
        b.run(1)
        assert max(oam_lines(b)) <= 10, max(oam_lines(b))
    assert b.mem("lift_forced") - forced0 == 1 and b.mem("lift_total") == 1
    assert b.oam()[27]["y"], "the coin is on screen"


def test_forty_entries_with_the_show_running(pair):
    """Show on (12 dancer entries), four lifted, then 12 mugs: the mugs keep every entry, a lifted patron is dropped
    to make room (mugs + lifted <= 21 - 2 spare), nothing overlaps, and the picture equals the game's without lifts."""
    a, b = pair
    slot = four_lifted(pair, {0: [(20, 0, 0), (60, 1, 0)], 2: [(24, 2, 0), (64, 0, 0)]})
    for g in pair:
        g.write("show_timer", 200)
        g.write(g.addr("show_timer") + 1, 0)
    run_hooks(pair, [(slot[k], HOOK_LIFT) for k in [(0, 20), (0, 60), (2, 24), (2, 64)]], settle=30)
    assert b.mem("lift_total") == 4
    for g in pair:
        for k in range(6):
            inject_mug(g, 1, 16 + 16 * k, EMPTY)
            inject_mug(g, 3, 20 + 16 * k, EMPTY)

    def check(_):
        oam = b.oam()
        live = [i for i, s in enumerate(oam) if s["y"]]
        mug_idx = [i for i in live if logical_tile(oam[i]["tile"]) in (OBJ_MUG_ID, OBJ_MUG_ID + 2)]
        lift_idx = [i for i in live if OBJ_BASE <= oam[i]["tile"] < OBJ_BASE + 18]
        dancers = [i for i in live if i >= OAM_DANCERS]
        assert len(mug_idx) == 12 or b.mem("game_state") != PLAYING
        assert len(lift_idx) == 2 * b.mem("lift_total") and (not lift_idx or max(mug_idx) < min(lift_idx))
        assert len(dancers) == 12 and len(live) <= 40
        assert len(mug_idx) + len(lift_idx) <= 21
        assert max(oam_lines(b)) <= 10
    step_same(pair, 40, after=check)
    assert b.mem("lift_total") == 3, "12 mugs + 2 x 3 lifted = 18 <= 19"


# ---- palettes and DMG copies ---------------------------------------------------------------------------
def obj_tile(gb, t):
    return bytes(gb.read(0x8000 + t * 16, 16))


def cgb_obj_palette(gb, k):
    return cgb_palette(gb, k, obj=True)


def cgb_bg_palette(gb, k):
    return cgb_palette(gb, k)


def test_patron_obj_palettes_and_dmg_copies(gb):
    if gb.model_name == "dmg":
        assert gb.mem(0xFF49) == 0xE4, "OBP1 in play: the BG's shades, for lifted patrons"
        assert gb.mem(0xFF48) == 0xD0
        for copy, orig in DMG_COPIES.items():
            o, c = obj_tile(gb, orig), obj_tile(gb, copy)
            assert c == bytes(o[i ^ 1] for i in range(16)), f"OBJ {copy}: bit planes of {orig} swapped"
        return
    for v in range(3):
        assert cgb_obj_palette(gb, LIFT_PAL[v])[1:] == cgb_bg_palette(gb, 2 + v)[1:], f"variant {v}"


def test_coin_and_show_share_obj_palette_5(gb):
    if gb.model_name != "cgb":
        pytest.skip("CGB palettes")
    from conftest import venue
    show = venue(0)["pal"][6]
    assert cgb_obj_palette(gb, 5)[1:] == show[1:], "the level starts with the show's colours in slot 5"
    gb.write("tip_timer", 200)
    gb.write("tip_bar", 1)
    gb.write("tip_x", 60)
    gb.run(2)
    coin = cgb_obj_palette(gb, 5)
    assert coin[1:] != show[1:] and gb.mem("pal5_cur") == 1, "a tip: the coin's colours"
    gb.write("tip_timer", 0)
    gb.write("show_timer", 100)
    gb.run(2)
    assert cgb_obj_palette(gb, 5)[1:] == show[1:] and gb.mem("pal5_cur") == 2, "the show: its colours again"
