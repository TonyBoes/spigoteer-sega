# The DMG's route plan (tools/smap_world/route.py, src/smap_eng.c; owner 11-11, Q17): the tile slots are planned at build time, along the roads.
#   - the generator's proof is re-run here from the built data (build/smap_world.json) and fails on a damaged plan;
#   - the plan is what the engine follows: on every frame of every leg, both ways, every cell of the region has its planned tile in its planned slot (the slot table in
#     story_scratch against the plan), and the region is inside the windows the plan was proved for;
#   - the pictures on the way are the world's (tests/test_story_map_world.py walks every leg frame by frame against the world's render, on both models).
import sys

import numpy as np
import pytest
import test_story_map as sm
from conftest import ROOT
from test_story_map_world import DIRS, LEG_WALKS, SV, WORLD, var

pytestmark = pytest.mark.timeout(600)
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "smap_world"))
import gen_smap_world as g  # noqa: E402
import route as R  # noqa: E402

V_C0, V_C1, V_R0, V_R1 = 26, 27, 28, 29
CW, CH, POOL = WORLD["cw"], WORLD["ch"], 176


def plan():
    stops, legs, _, _ = g.geometry()
    leads = {(li, rev, j): n for li, rev, j, n in WORLD["leads_d"]}
    seqs = R.walk_sequences(stops, legs, g.STOP_ORDER, g.STOP_VIEW, g.CW, g.CH, g.SAL_Y, leads=leads)
    tiles = {s: np.array(WORLD["disp_d"][s - 1], dtype=np.int64).reshape(CH, CW) & 0x3FF for s in (1, 11)}
    return tiles, [int(v) for v in WORLD["slot_d"]], {int(k): v for k, v in WORLD["dslot_d"].items()}, seqs


def test_the_generators_proof_holds_for_the_built_plan():
    tiles, slot, dslot, seqs = plan()
    steps = R.check_plan(tiles, slot, dslot, seqs, CW, CH, POOL)
    assert steps > 4000 and len(seqs) > 30


def test_the_proof_fails_when_two_tiles_share_a_slot_in_a_window():
    tiles, slot, dslot, seqs = plan()
    c0, c1, r0, r1 = seqs[0][0]                       # a window the plan covers: make one of its cells take another tile's slot
    cells = [y * CW + x for y in range(r0, r1 + 1) for x in range(c0, c1 + 1)]
    a = cells[0]
    b = next(c for c in cells if tiles[11].reshape(-1)[c] != tiles[11].reshape(-1)[a])
    slot[b] = slot[a]
    with pytest.raises(AssertionError):
        R.check_plan(tiles, slot, dslot, seqs, CW, CH, POOL)


def test_the_proof_fails_when_a_line_that_enters_clobbers_a_slot_that_stays():
    """two cells in different windows of a walk share a slot, and the tile that enters is not the one that stays"""
    tiles, slot, dslot, seqs = plan()
    t = tiles[11].reshape(-1)
    for sq in seqs:
        for w0, w1 in zip(sq, sq[1:]):
            if w0 == w1:
                continue
            old = {y * CW + x for y in range(w0[2], w0[3] + 1) for x in range(w0[0], w0[1] + 1)}
            new = {y * CW + x for y in range(w1[2], w1[3] + 1) for x in range(w1[0], w1[1] + 1)}
            enter, stay = sorted(new - old), sorted(new & old)
            if enter and stay:
                e = enter[0]
                s = next((c for c in stay if t[c] != t[e]), None)
                if s is None:
                    continue
                slot[e] = slot[s]
                with pytest.raises(AssertionError):
                    R.check_plan(tiles, slot, dslot, seqs, CW, CH, POOL)
                return
    raise AssertionError("no walk step with a line entering")


def test_the_engine_follows_the_plan_on_every_frame_of_every_leg_both_ways():
    tiles, slot, dslot, seqs = plan()
    t = tiles[11].reshape(-1)
    windows = {w for sq in seqs for w in sq}
    cells = checked = 0
    for s, d in LEG_WALKS:
        gb = sm.to_map("dmg", 10, stop=s)
        gb.press(DIRS[d], 4)
        started = False
        for f in range(1500):
            gb.run(1, True)
            sc = gb.read("story_scratch", 520)
            walking = bool(sc[SV + 20])
            started = started or walking
            if not started:
                continue
            c0, c1, r0, r1 = (sc[SV + v] for v in (V_C0, V_C1, V_R0, V_R1))
            assert (c0, c1, r0, r1) == (c0, c1, r0, r1) and c0 <= c1 + 1 and r0 <= r1
            tbl = [sc[2 * i] | sc[2 * i + 1] << 8 for i in range(POOL)]
            for y in range(r0, r1 + 1):
                for x in range(c0, c1 + 1):
                    c = y * CW + x
                    assert tbl[slot[c]] == t[c], (s, d, f, "cell", (x, y), "slot", slot[c], "holds", tbl[slot[c]], "wants", t[c])
                    cells += 1
            # the region lies inside a window the plan covers (the view and a line either side)
            assert any(w[0] <= c0 and c1 <= w[1] and w[2] <= r0 and r1 <= w[3] for w in windows), (s, d, f, (c0, c1, r0, r1))
            checked += 1
            if f > 4 and not walking:
                break
    assert checked > 3000 and cells > 1000000
