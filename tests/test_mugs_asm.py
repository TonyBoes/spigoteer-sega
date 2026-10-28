# Equivalence of the asm mug code (src/mugs.c: ASM_DRAW_HELD folds draw_held into draw_mugs_loop, ASM_UPDATE_MUGS is the update_mugs
# loop) with its C versions (build/game-c.gb, `make cfall`): update_mugs and draw_mugs are called on the SAME memory image on
# both builds (tests/asm_rig.py) and must leave exactly the same WRAM / HRAM (so the same mug_state / mug_x / mug_timer, the same
# shadow OAM, the same score / lives / sfx) and return the same. Two sources of images:
#   - real calls captured from the busy scenes (the arcade realistic peak, CLASSIC's level 25, both models), a few hundred each;
#   - random images of the pool (every state, x, timer, bar, holder) with random patron arrays, lift counts and bartender spots.
# make test runs a subset, RUN_SLOW=1 the full set. (The video-frame-by-video-frame comparison of two whole runs cannot be done:
# the builds differ in speed, so the scene's frames fall in different places and the scenes drift apart.)
import os
import random

import pytest
from asm_rig import Call, Rig, cycles_summary, WRAM, HRAM
from conftest import ROOT
import perf_helpers as ph
from gbtools import Rom

SLOW = bool(os.environ.get("RUN_SLOW"))
ASM_ROM, C_ROM = ROOT / "build" / "game.gb", ROOT / "build" / "game-c.gb"
pytestmark = [pytest.mark.timeout(1200), pytest.mark.usefixtures("c_rom_fresh"),
              pytest.mark.skipif(not C_ROM.exists(), reason="needs build/game-c.gb (make cfall)")]
N_REAL, N_RANDOM = (400, 6000) if SLOW else (150, 1500)


@pytest.fixture(params=["dmg", "cgb"])
def model(request):
    return request.param


def capture(model, fns, frames, **kw):
    """Real calls of each function in `fns` over `frames` frames of the realistic-peak scenario on the asm ROM."""
    gb = Rom(ASM_ROM, model)
    gb.run(120)
    gb.model_name = model
    rig = Rig(ASM_ROM, model, gb=gb)
    m, rf = gb.pb.memory, gb.pb.register_file
    caps = {f: [] for f in fns}
    for f in fns:
        bank, fa = rig.fn(f)

        def entry(_, f=f):
            caps[f].append(Call(f, wram=bytes(m[WRAM[0]:WRAM[1]]), hram=bytes(m[HRAM[0]:HRAM[1]])))
        gb.pb.hook_register(0, fa, entry, None)
    ph.realistic_run(gb, frames, None, **kw)
    gb.stop()
    return caps


def compare_ignoring_scratch(ra, rc, calls):
    """asm_rig.compare, except for mugs.c's static oam_next (2 bytes; and patrons.c's fc_best / fc_x, the asm catch scans' dead scratch): the C draw_held keeps it in step, the asm loop keeps the entry
    pointer in DE and does not write it back; draw_mugs sets it before any use, so after the call it is dead."""
    ign = {ra.addr("mugs:_oam_next"), ra.addr("mugs:_oam_next") + 1, ra.addr("patrons:_fc_best"), ra.addr("patrons:_fc_x")}   # (and the catch scans' scratch, patrons.c)
    xa, xc = ra.run(calls), rc.run(calls)
    bad = []
    for i, (x, y) in enumerate(zip(xa, xc)):
        dx = {k: v for k, v in x.diff.items() if k not in ign}
        dy = {k: v for k, v in y.diff.items() if k not in ign}
        if dx != dy:
            keys = sorted(set(dx) | set(dy))
            bad.append((i, [(hex(k), dx.get(k), dy.get(k)) for k in keys if dx.get(k) != dy.get(k)][:8]))
    return bad, xa, xc


def pick(calls, n):
    step = max(1, len(calls) // n)
    return calls[::step][:n]


SCENES = [dict(), dict(target=16, cls=ph.ClassicPeak, classic=25)]


@pytest.mark.parametrize("scene", range(len(SCENES)))
@pytest.mark.parametrize("fn,ret", [("update_mugs", "none"), ("draw_mugs", "none")])
def test_real_calls(model, scene, fn, ret):
    caps = capture(model, ["update_mugs", "draw_mugs"], 700 if SLOW else 400, **SCENES[scene])
    calls = pick(caps[fn], N_REAL)
    assert len(calls) >= 60, len(calls)
    ra, rc = Rig(ASM_ROM, model), Rig(C_ROM, model)
    bad, xa, xc = compare_ignoring_scratch(ra, rc, calls)
    print(fn, model, "scene", scene, len(calls), "calls, T asm / c (min, median, max)", cycles_summary(xa), cycles_summary(xc))
    assert not bad, bad[:5]
    assert any(r.diff for r in xa)


def rnd_image(rnd, fn):
    """Pokes for one random case. The pool: a few free, many live slots; patrons of every state; the arrays stay in their domains."""
    p = {}
    n = 20
    state = [rnd.choice([0, 0, 1, 1, 2, 2, 3, 4, 4, 4, 5]) for _ in range(n)]
    bar = [rnd.randrange(4) for _ in range(n)]
    p["mug_state"] = bytes(state)
    p["mug_bar"] = bytes(bar)
    p["mug_x"] = bytes(rnd.choice([rnd.randrange(256), rnd.randrange(14, 40), rnd.randrange(100, 150), rnd.randrange(120, 135)]) for _ in range(n))
    p["mug_timer"] = bytes(rnd.choice([rnd.randrange(256), rnd.randrange(40), 30, 31]) for _ in range(n))
    p["mug_timer"] = bytes(t % 32 if st == 3 else t for t, st in zip(p["mug_timer"], state))   # a breaking glass: 0..31 (draw_glass tables)
    p["mug_patron"] = bytes(rnd.randrange(16) for _ in range(n))
    p["mugs_live"] = sum(1 for s in state if s) or 1
    m = 16
    p["patron_state"] = bytes(rnd.choice([0, 1, 2, 3, 3, 3, 4]) for _ in range(m))
    p["patron_bar"] = bytes(rnd.randrange(4) for _ in range(m))
    p["patron_x"] = bytes(rnd.randrange(256) for _ in range(m))
    p["patron_draw"] = bytes(rnd.randrange(256) for _ in range(m))
    p["patron_timer"] = bytes(rnd.choice([rnd.randrange(256), rnd.randrange(140), 96 + rnd.randrange(32)]) for _ in range(m))
    p["patron_aux"] = bytes(rnd.randrange(256) for _ in range(m))
    p["patron_lift"] = bytes(rnd.choice([0, 0, 1, 2, 3, 4]) for _ in range(m))
    p["patron_mug"] = bytes(rnd.choice([255, rnd.randrange(n), rnd.randrange(n)]) for _ in range(m))
    for i in range(n):                                  # most holders really hold their mug
        if state[i] == 4 and rnd.random() < 0.8:
            q = rnd.randrange(m)
            pm = bytearray(p["patron_mug"]); pm[q] = i; p["patron_mug"] = bytes(pm)
            mp = bytearray(p["mug_patron"]); mp[i] = q; p["mug_patron"] = bytes(mp)
    p["bar"] = rnd.randrange(4)
    p["bartender_x"] = rnd.choice([rnd.randrange(256), rnd.randrange(100, 140)])
    p["tap_now"] = rnd.choice([120, p["bartender_x"], rnd.randrange(100, 140)])
    p["lift_total"] = rnd.randrange(0, 9)
    p["oam_used"] = rnd.randrange(0, 27)
    p["catch_pose"] = rnd.randrange(8)
    return p


@pytest.mark.parametrize("fn", ["update_mugs", "draw_mugs"])
def test_random_images(model, fn):
    rnd = random.Random(7)
    calls = [Call(fn, poke=rnd_image(rnd, fn)) for _ in range(N_RANDOM)]
    ra, rc = Rig(ASM_ROM, model), Rig(C_ROM, model)
    bad, xa, xc = compare_ignoring_scratch(ra, rc, calls)
    print(fn, model, "random", len(calls), "T asm / c (min, median, max)", cycles_summary(xa), cycles_summary(xc))
    assert not bad, bad[:5]
    assert sum(1 for r in xa if r.diff) > len(calls) // 2
