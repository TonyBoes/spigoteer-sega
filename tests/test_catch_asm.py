# Equivalence of the asm catch scans (src/patrons.c: ASM_SCANS = find_catcher and scan_catcher, behind catch_full) with their C
# versions (build/game-c.gb, `make cfall`): catch_full(i), find_catcher(b) and scan_catcher(b, x) are called on the SAME memory
# image on both builds (tests/asm_rig.py) and must leave exactly the same WRAM / HRAM and return the same. Two image sources, as
# tests/test_mugs_asm.py: real calls captured from the busy scenes (arcade peak, CLASSIC 25; both models), and random images
# (patron states, bars, positions, lift counts, drink / distraction flags, stale catch_* statics).
# The scans' scratch (patrons.c fc_best / fc_x) is dead after the call and is ignored.
import os
import random

import pytest
from asm_rig import Call, Rig, cycles_summary, WRAM, HRAM
from conftest import ROOT
import perf_helpers as ph
from gbtools import Rom
from test_mugs_asm import rnd_image

SLOW = bool(os.environ.get("RUN_SLOW"))
ASM_ROM, C_ROM = ROOT / "build" / "game.gb", ROOT / "build" / "game-c.gb"
pytestmark = [pytest.mark.timeout(1200),
              pytest.mark.skipif(not C_ROM.exists(), reason="needs build/game-c.gb (make cfall)")]
N_REAL, N_RANDOM = (400, 6000) if SLOW else (150, 1500)
SCENES = [dict(), dict(target=16, cls=ph.ClassicPeak, classic=25)]


@pytest.fixture(params=["dmg", "cgb"])
def model(request):
    return request.param


def capture(model, fn, frames, **kw):
    gb = Rom(ASM_ROM, model)
    gb.run(120)
    gb.model_name = model
    rig = Rig(ASM_ROM, model, gb=gb)
    m, rf = gb.pb.memory, gb.pb.register_file
    caps = []
    bank, fa = rig.fn(fn)

    def entry(_):
        caps.append(Call(fn, a=rf.A, e=rf.E, de=(rf.D << 8) | rf.E, wram=bytes(m[WRAM[0]:WRAM[1]]), hram=bytes(m[HRAM[0]:HRAM[1]])))
    gb.pb.hook_register(0, fa, entry, None)
    ph.realistic_run(gb, frames, None, **kw)
    gb.stop()
    return caps


def compare(ra, rc, calls, ret):
    ign = {ra.addr("patrons:_fc_best"), ra.addr("patrons:_fc_x")}
    xa, xc = ra.run(calls), rc.run(calls)
    bad = []
    for i, (x, y) in enumerate(zip(xa, xc)):
        dx = {k: v for k, v in x.diff.items() if k not in ign}
        dy = {k: v for k, v in y.diff.items() if k not in ign}
        if dx != dy or (ret != "none" and x.ret(ret) != y.ret(ret)):
            keys = sorted(set(dx) | set(dy))
            bad.append((i, [(hex(k), dx.get(k), dy.get(k)) for k in keys if dx.get(k) != dy.get(k)][:8], x.ret(ret), y.ret(ret)))
    return bad, xa, xc


@pytest.mark.parametrize("scene", range(len(SCENES)))
def test_real_calls(model, scene):
    calls = capture(model, "catch_full", 700 if SLOW else 450, **SCENES[scene])
    step = max(1, len(calls) // N_REAL)
    calls = calls[::step][:N_REAL]
    assert len(calls) >= 60, len(calls)
    ra, rc = Rig(ASM_ROM, model), Rig(C_ROM, model)
    bad, xa, xc = compare(ra, rc, calls, "a")
    print("catch_full", model, "scene", scene, len(calls), "calls, T asm / c (min, median, max)", cycles_summary(xa), cycles_summary(xc))
    assert not bad, bad[:5]


def rnd_case(rnd):
    p = rnd_image(rnd, "update_mugs")
    p["patrons:_catch_ok"] = 0 if rnd.random() < 0.8 else rnd.randrange(16)
    p["catch_lim"] = bytes(255 if rnd.random() < 0.8 else rnd.choice([0, rnd.randrange(256)]) for _ in range(4))
    if rnd.random() < 0.3:                              # lists_ok 0: build_lists runs first (the asm calls it too)
        p["lists_ok"] = 0
    else:                                               # hand-made lists: random live-looking slots, some stale (state NONE)
        p["lists_ok"] = 1
        ns = [rnd.randrange(0, 9) for _ in range(4)]
        p["bar_n"] = bytes(ns)
        p["bar_list"] = b"".join(bytes(rnd.sample(range(16), 16)) for _ in range(4))
    p["patron_state"] = bytes(rnd.choice([0, 1, 1, 1, 2, 3, 3, 4]) for _ in range(16))
    p["patron_dist"] = bytes(rnd.choice([0, 0, 0, 1]) for _ in range(16))
    p["patron_aux"] = bytes(rnd.choice([0, 0, 1, 2, rnd.randrange(256)]) for _ in range(16))
    p["patron_x"] = bytes(rnd.choice([rnd.randrange(256), rnd.randrange(10, 130), rnd.randrange(60, 130)]) for _ in range(16))
    return p


def rnd_calls(rnd, fn, n):
    out = []
    for _ in range(n):
        p = rnd_case(rnd)
        i = rnd.randrange(20)
        st = bytearray(p["mug_state"]); st[i] = 1; p["mug_state"] = bytes(st)     # a full mug
        mb = bytearray(p["mug_bar"]); mb[i] = rnd.choice([0, 1, 2, 3, 3, 2, 1, 0, 5]); p["mug_bar"] = bytes(mb)
        if fn == "catch_full":
            out.append(Call(fn, a=i, poke=p))
        elif fn == "find_catcher":
            out.append(Call("patrons:_find_catcher", a=rnd.randrange(4), poke=p))
        else:
            out.append(Call("patrons:_scan_catcher", a=rnd.randrange(4), e=rnd.choice([rnd.randrange(256), rnd.randrange(10, 150)]), poke=p))
    return out


@pytest.mark.parametrize("fn", ["catch_full", "find_catcher", "scan_catcher"])
def test_random_images(model, fn):
    rnd = random.Random(11)
    calls = rnd_calls(rnd, fn, N_RANDOM)
    ra, rc = Rig(ASM_ROM, model), Rig(C_ROM, model)
    if fn != "catch_full" and not rc.has_fn("patrons:_" + fn):
        pytest.skip("the C build inlined " + fn)
    bad, xa, xc = compare(ra, rc, calls, "none" if fn == "find_catcher" else "a")
    print(fn, model, "random", len(calls), "T asm / c (min, median, max)", cycles_summary(xa), cycles_summary(xc))
    assert not bad, bad[:5]
    assert sum(1 for r in xa if r.diff) > len(calls) // 4
