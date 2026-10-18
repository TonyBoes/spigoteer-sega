# The asm pass's equivalence tests (asm_plan PLAN.md section 6.1) and the tests of the rig itself (tests/asm_rig.py).
#
#  - test_rig_*: the rig on functions that exist as C today, against a Python model and against real captured calls
#    (batch 0: nothing is asm yet; these prove the rig before a batch relies on it).
#  - test_c_vs_asm: every candidate registered with @candidate below, run on build/game.gb (asm) and build/game-c.gb
#    (`make cfall`): the same random cases and the replayed real calls, with exactly equal WRAM / HRAM diffs and return values.
#    A batch adds its generator here. A fast subset (FAST cases) runs in `make test`; RUN_SLOW=1 runs the full set (FULL).
#  - test_data_layout: tools/data_layout_check.py on the two builds.
import os
import random
import subprocess
import sys

import pytest
from asm_rig import Call, Rig, compare, cycles_summary
from conftest import ROM, ROOT
import perf_helpers as ph
from gbtools import Rom

SLOW = bool(os.environ.get("RUN_SLOW"))
FAST, FULL = 2000, 20000
ASM_ROM, C_ROM = ROOT / "build" / "game.gb", ROOT / "build" / "game-c.gb"
MODELS = ["dmg", "cgb"]
pytestmark = pytest.mark.timeout(1200)


@pytest.fixture(params=MODELS)
def model(request):
    return request.param


# ---------------------------------------------------------------------------------------------------------------------------
# candidates: name -> (generator(rnd, rig) -> Call, return register to compare)
CANDIDATES = {}


def candidate(name, ret="none"):
    """Register a batch's function: `gen(rnd, rig)` returns one random Call over the function's legal input domain (see PLAN.md
    section 6.1 for each batch's domains). `ret` is the return register: a, bc, de, hl or none."""
    def deco(gen):
        CANDIDATES[name] = (gen, ret)
        return gen
    return deco


# batch 1 (ASM_F): main.c perf_ly(t0 in A, t in E, ly on the stack) -> BC, and perf_snap (writes snap_t / snap_ly).
@candidate("perf_ly", ret="bc")
def _gen_perf_ly(rnd, rig):
    t0, t, ly = perf_ly_cases(rnd, 15)[-1]
    return Call("main:_perf_ly", a=t0, e=t, stack=bytes([ly]))


@candidate("perf_snap")
def _gen_perf_snap(rnd, rig):
    return Call("main:_perf_snap", poke={"main:_snap_t": rnd.randrange(256), "main:_snap_ly": rnd.randrange(256)})


# batch 2 .. 11 add their @candidate generators here.


@pytest.mark.skipif(not C_ROM.exists() or not CANDIDATES, reason="needs build/game-c.gb (make cfall) and a registered candidate")
@pytest.mark.parametrize("name", sorted(CANDIDATES) or ["none"])
def test_c_vs_asm(name, model):
    gen, ret = CANDIDATES[name]
    rnd = random.Random(1)
    ra, rc = Rig(ASM_ROM, model), Rig(C_ROM, model)
    calls = [gen(rnd, ra) for _ in range(FULL if SLOW else FAST)]
    bad, xa, xc = compare(ra, rc, calls, ret)
    print(name, model, "T per call asm / c (min, median, max)", cycles_summary(xa), cycles_summary(xc))
    assert not bad, bad[:5]


def test_data_layout():
    if not C_ROM.exists():
        pytest.skip("build/game-c.gb is not built (make cfall)")
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "data_layout_check.py"), str(ASM_ROM), str(C_ROM)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


# ---------------------------------------------------------------------------------------------------------------------------
# the rig on a C function against a Python model: main.c perf_ly(t0, t, ly) (uint8_t, uint8_t, uint8_t) -> uint16_t, the batch 1
# target; the third argument is on the stack.
def perf_ly_model(t0, t, ly):
    dt = (t - t0) & 255
    if dt == 0:
        return 0 if ly >= 144 else ly
    return (144 + (dt - 1) * 154 + (ly - 144 if ly >= 144 else ly + 10)) & 0xFFFF


def perf_ly_cases(rnd, n):
    cases = [(0, 0, 0), (0, 0, 143), (0, 0, 144), (0, 0, 255), (0, 1, 0), (0, 1, 143), (0, 1, 144), (0, 1, 153), (0, 2, 0),
             (255, 0, 10), (255, 1, 10), (0, 255, 255), (1, 0, 144), (200, 100, 7)]
    while len(cases) < n:
        t0 = rnd.randrange(256)
        dt = rnd.choice([0, 1, 1, 2, 2, 3, rnd.randrange(256)])
        cases.append((t0, (t0 + dt) & 255, rnd.choice([rnd.randrange(256), rnd.randrange(154), 143, 144, 153])))
    return cases


def test_rig_perf_ly_matches_its_python_model(model):
    rig = Rig(ROM, model)
    cases = perf_ly_cases(random.Random(7), FULL if SLOW else FAST)
    res = rig.run([Call("main:_perf_ly", a=t0, e=t, stack=bytes([ly])) for t0, t, ly in cases])
    assert len(res) == len(cases)
    for (t0, t, ly), r in zip(cases, res):
        assert r.bc == perf_ly_model(t0, t, ly), (t0, t, ly, r.de, r.bc)         # a 16-bit return is in BC here (measured)
        assert r.diff == {}, (t0, t, ly, r.diff)                                 # a pure function writes nothing outside the stack
    lo, med, hi = cycles_summary(res)
    print(model, "perf_ly T per call (C)", lo, med, hi)
    assert 60 <= lo and hi <= 7000                                               # C: 332 (dt 0) .. ~1,036; asm: 120 (dt 0) .. ~190 (dt 1-2), 6,272 at dt 255 (an add loop; dt is that large only after a long transition)


@pytest.mark.skipif(not SLOW, reason="the exhaustive perf_ly sweep: RUN_SLOW=1")
def test_perf_ly_exhaustive(model):
    """Every dt (0..255) x every ly (0..255) against the Python model; t0 is poked through the register so only dt matters."""
    rig = Rig(ROM, model)
    cases = [(5, (5 + dt) & 255, ly) for dt in range(256) for ly in range(256)]
    res = rig.run([Call("main:_perf_ly", a=t0, e=t, stack=bytes([ly])) for t0, t, ly in cases])
    for (t0, t, ly), r in zip(cases, res):
        assert r.bc == perf_ly_model(t0, t, ly), (t0, t, ly, r.bc)
        assert r.diff == {}


def test_rig_leaves_the_game_running(model):
    """Calls between frames put every register, WRAM / HRAM byte, LCDC and IE back: the game plays on as if they never ran."""
    rig = Rig(ROM, model)
    gb = rig.gb
    st = gb.mem("game_state")
    f0 = gb.mem("frame_counter")
    rig.run([Call("main:_perf_ly", a=1, e=3, stack=bytes([150]))] * 50)
    assert gb.mem("game_state") == st
    gb.run(10)
    assert gb.mem("game_state") == st and (gb.mem("frame_counter") - f0) & 255 >= 8


# ---------------------------------------------------------------------------------------------------------------------------
# the rig on real calls: draw_held (mugs.c, static, a `uint8_t i` in A) captured from the realistic-peak scenario and replayed.
# Structure of its effect (src/mugs.c): it writes mug_x[i] and ONE OAM entry (4 bytes) at oam_next, then oam_next += 4.
def test_rig_replays_real_draw_held_calls(model):
    gb = Rom(ROM, model)
    gb.run(120)
    gb.model_name = model
    rig = Rig(ROM, model, gb=gb)
    caps = []

    def check(g, i):
        pass
    # the capture hook is registered before the scenario starts and records every real call of the realistic peak
    bank, fa = rig.fn("mugs:_draw_held")
    from asm_rig import WRAM, HRAM
    m, rf = gb.pb.memory, gb.pb.register_file

    def entry(_):
        if len(caps) < 400:
            caps.append(Call("mugs:_draw_held", a=rf.A, wram=bytes(m[WRAM[0]:WRAM[1]]), hram=bytes(m[HRAM[0]:HRAM[1]])))
    gb.pb.hook_register(0, fa, entry, None)
    ph.realistic_run(gb, 600, check)
    assert len(caps) >= 100, len(caps)
    one = rig.run(caps)
    two = rig.run(caps)
    assert [(r.cycles, r.diff, r.a) for r in one] == [(r.cycles, r.diff, r.a) for r in two], "replay is not deterministic"
    on = rig.addr("mugs:_oam_next")
    mx, mxn = rig.addr("mug_x"), 20
    for c, r in zip(caps, one):
        before = c.wram
        old = before[on - 0xC000] | (before[on + 1 - 0xC000] << 8)
        assert 0xC000 <= old < 0xC0A0 and (old & 3) == 0, hex(old)               # shadow_OAM
        new = r.diff.get(on, before[on - 0xC000]) | (r.diff.get(on + 1, before[on + 1 - 0xC000]) << 8)
        assert new == old + 4, (hex(old), hex(new))
        for a in r.diff:
            assert old <= a < old + 4 or on <= a <= on + 1 or mx <= a < mx + mxn, hex(a)
    lo, med, hi = cycles_summary(one)
    print(model, "real draw_held calls:", len(caps), "T per call (C)", lo, med, hi)
    assert 900 <= lo and hi <= 1600                                              # the profiler: 1,107 + oam_put's 196


def test_compare_reports_a_difference(model):
    """compare() must see a changed byte: perf_snap writes snap_t (sys_time), so two rigs that have run different numbers of frames
    differ, and two identically booted rigs do not. (A run leaves the game a frame or so further on, so a second run on the
    same rig sees a later sys_time: compare fresh rigs, and poke or restore every input a function reads.)"""
    a, b = Rig(ROM, model), Rig(ROM, model)
    b.gb.run(3)
    calls = [Call("main:_perf_snap")]
    bad, ra, _ = compare(a, b, calls)
    assert ra[0].diff, "perf_snap changed nothing"
    assert bad and bad[0][1] == "diff", bad
    c, d = Rig(ROM, model), Rig(ROM, model)                  # two rigs booted the same way see the same state: no mismatch
    assert compare(c, d, calls)[0] == []
