# Direct C-versus-asm tests for the asm switches the older twin files (test_asm_equiv, test_mugs_asm, test_catch_asm,
# test_chooser_trace) do not cover, in the same style (tests/asm_rig.py: the same random memory image on build/game.gb and
# build/game-c.gb, the WRAM / HRAM diff and the registers must be equal):
#   ASM_LIFT_DRAW  draw_lifted_asm (the two OAM entries of every lifted patron) and its banked caller draw_lifted
#   ASM_TILE_COPY  load_saloon_x (the Saloon's Color-only tiles into VRAM bank 1, Color only)
# The switches ASM_PATRON_LOOP, ASM_PATRON_STEPS, ASM_BOSS_HATS and ASM_LIFT_FRAME are declared in src/asm_cfg.h but gate no code
# today (no `#if` in src/ uses them: the C is the only version), so there is nothing to compare. The guard test at the bottom
# fails the day one of them gets an `#if`, until it has a twin test listed here. ASM_SPLIT_PAL (split_pal_put) writes palette RAM
# through BCPS/BCPD, which the rig cannot diff; the Color goldens and make check cover it.
import random
import re

import pytest
from asm_rig import Call, Rig, cycles_summary
from conftest import ROOT

ASM_ROM, C_ROM = ROOT / "build" / "game.gb", ROOT / "build" / "game-c.gb"
pytestmark = [pytest.mark.timeout(1200), pytest.mark.usefixtures("c_rom_fresh"),
              pytest.mark.skipif(not C_ROM.exists(), reason="needs build/game-c.gb (make cfall)")]
N_RANDOM = 1500


@pytest.fixture(params=["dmg", "cgb"])
def model(request):
    return request.param


def lift_image(rnd):
    """One random state for draw_lifted: patrons in every lift state, x values (0xFF = not drawn), looks and palette instances in
    their real domain (lift_obj has 5 entries), lift_total 0..8, last frame's entry count and the mugs' OAM use."""
    n = 16
    p = {}
    p["patron_lift"] = bytes(rnd.choice([0, 0, 1, 1, 2, 3, 0x80, 0x81, 0x82]) for _ in range(n))
    p["patron_draw"] = bytes(rnd.choice([0xFF, rnd.randrange(256), rnd.randrange(0x80)]) for _ in range(n))
    p["patron_aux"] = bytes(rnd.randrange(256) for _ in range(n))
    p["patron_bar"] = bytes(rnd.randrange(4) for _ in range(n))

    def variant():
        look, inst = rnd.randrange(8), rnd.randrange(5)
        return look | (((look ^ inst) & 7) << 3) | (rnd.randrange(2) << 6)
    p["patron_variant"] = bytes(variant() for _ in range(n))
    p["lift_total"] = rnd.randrange(0, 9)
    p["lift_oam_n"] = rnd.randrange(0, 5) * 2
    p["lift_prop"] = bytes([rnd.choice([0, 0x10, 0x20])]) + bytes(3)
    p["oam_used"] = rnd.randrange(0, 27)
    p["shadow_OAM"] = bytes(rnd.randrange(256) for _ in range(160))
    return p


@pytest.mark.parametrize("fn", ["draw_lifted_asm", "draw_lifted"])
def test_draw_lifted_random_images(model, fn):
    name = "lift:_draw_lifted_asm" if fn == "draw_lifted_asm" else fn
    rnd = random.Random(11)
    calls = [Call(name, poke=lift_image(rnd)) for _ in range(N_RANDOM)]
    ra, rc = Rig(ASM_ROM, model), Rig(C_ROM, model)
    xa, xc = ra.run(calls), rc.run(calls)
    # the C version also keeps dl_x / dl_y / dl_t / dl_p / dl_o in step; the asm keeps its working values in registers: dead after the call
    ign = {ra.addr(f"lift:_dl_{s}") + k for s in ("v", "x", "y", "t", "p", "o") for k in (0, 1)}
    bad = []
    for i, (x, y) in enumerate(zip(xa, xc)):
        dx = {k: v for k, v in x.diff.items() if k not in ign}
        dy = {k: v for k, v in y.diff.items() if k not in ign}
        if dx != dy:
            bad.append((i, [(hex(k), dx.get(k), dy.get(k)) for k in sorted(set(dx) | set(dy)) if dx.get(k) != dy.get(k)][:8]))
    print(fn, model, N_RANDOM, "calls, T asm / c (min, median, max)", cycles_summary(xa), cycles_summary(xc))
    assert not bad, bad[:5]
    assert sum(1 for r in xa if r.diff) > N_RANDOM // 2, "the images must make the routine write"


@pytest.mark.only_model("cgb")
def test_load_saloon_x_copies_the_same_vram_bank_1(model):
    """ASM_TILE_COPY: the eight parts (LCD off, as the level load runs them) leave VRAM bank 1 0x8000..0x97FF and the WRAM equal."""
    calls = [Call("load_saloon_x", stack=bytes([0, 0, 0, 0, p])) for p in range(8)]   # (a banked function: its argument is on the stack, 6 bytes up)
    ra, rc = Rig(ASM_ROM, model), Rig(C_ROM, model)
    vram = {}
    for tag, r in (("asm", ra), ("c", rc)):
        r.gb.pb.memory[0xFF40] &= 0x7F
        res = r.run(calls)
        vram[tag] = bytes(r.gb.pb.memory[1, 0x8000:0x9800])
        vram[tag + "_diff"] = [x.diff for x in res]
    assert vram["asm_diff"] == vram["c_diff"]
    assert vram["asm"] == vram["c"] and any(vram["asm"]), "tiles were copied"


# ---- the guard: every asm switch that gates code has a twin test --------------------------------------------------------------------
TWIN_TESTED = {                      # switch -> the file with its C-versus-asm test
    "ASM_F": "test_asm_equiv.py", "ASM_DRAW_HELD": "test_mugs_asm.py", "ASM_UPDATE_MUGS": "test_mugs_asm.py",
    "ASM_SCANS": "test_catch_asm.py", "ASM_CHOOSER": "test_chooser_trace.py", "ASM_LIFT_DRAW": "test_asm_twins.py",
    "ASM_TILE_COPY": "test_asm_twins.py", "ASM_SMAP": "test_story_map_world.py", "ASM_CLOUD": "test_smap_clouds_pool.py", "ASM_SPLIT_PAL": "(palette RAM: Color goldens and make check)"}


def test_every_asm_switch_that_gates_code_has_a_twin_test():
    used = set()
    pat = re.compile(r"#\s*(?:if|elif|ifdef)\s*!?\s*\(?\s*(ASM_[A-Z_0-9]+)")
    for f in list((ROOT / "src").rglob("*.c")) + list((ROOT / "src").rglob("*.h")) + [ROOT / "tools" / "gen_art.py"]:
        if f.name == "asm_cfg.h":
            continue
        used |= set(pat.findall(f.read_text()))
        used |= set(re.findall(r'"#if !?(ASM_[A-Z_0-9]+)"', f.read_text())) if f.suffix == ".py" else set()
    used.discard("ASM_PASS")
    missing = sorted(used - set(TWIN_TESTED))
    assert not missing, f"{missing} now gate code in src/: add a C-versus-asm test in tests/test_asm_twins.py and list it in TWIN_TESTED"
    for sw, where in TWIN_TESTED.items():
        if where.endswith(".py"):
            assert (ROOT / "tests" / where).exists(), (sw, where)
