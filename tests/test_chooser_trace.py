# The crowd chooser makes the decisions it made before it was made cheaper (src/lift.c choose_bar; asm_cfg.h ASM_CHOOSER).
#
# tests/data/chooser_trace.json.gz holds states the chooser was called in (captured from the ARCADE peaks of 10 and 12 patrons, with their
# shows and tips, and from CLASSIC's 16-patron level, DMG and CGB; plus random crowded bars: every state, column, lift, flag and budget) and
# what the call did to WRAM, as the build BEFORE the speed-up made it (tools/gen_chooser_trace.py). Every case is run on the ROM under test
# (build/game.gb, or GB_ROM=build/game-c.gb for the C version) with the function-level rig (tests/asm_rig.py) and must change exactly the
# same bytes to the same values: the patron flags, who is lifted, the busy and clear counters, the lift counts, the retry state, the spans
# marked dirty and the urgent copies asked for. See tests/chooser_trace_lib.py for why the cases are calls and not a recording of whole runs.
#
# Regenerating the data is a decision to change the chooser's behaviour: say so in the commit message.
import collections

import pytest
from conftest import ROM, ROOT

import chooser_trace_lib as L

pytestmark = [pytest.mark.timeout(900), pytest.mark.usefixtures("c_rom_fresh")]


@pytest.fixture(scope="module")
def cases():
    return L.load()


C_ROM = ROOT / "build" / "game-c.gb"
ROMS = [ROM] + ([C_ROM] if C_ROM.exists() and C_ROM.resolve() != ROM.resolve() else [])   # (the all-C build too: `make cfall`)


@pytest.fixture(params=["dmg", "cgb"])
def model(request):
    return request.param


@pytest.fixture(params=ROMS, ids=lambda p: p.stem)
def rom(request):
    return request.param


def mine(cases, model):
    return [c for c in cases if model in c["out"]]


def test_the_data_is_a_crowd(cases):
    """The cases are what they say: all the scenes, both models, lifts, flags, budgets refusing and a lift going through."""
    scenes = collections.Counter(c["s"].split("-")[0] for c in cases)
    assert set(scenes) == {"peak10", "peak12", "classic16", "random"}, scenes
    changes = [m for c in cases for m in c["out"].values()]
    assert len(changes) > 1000
    assert sum(1 for m in changes if any(k.startswith("lift_lifts") for k in m)) > 30            # someone lifted
    assert sum(1 for m in changes if any(k.startswith("patron_ovl") for k in m)) > 200           # flags set / cleared
    assert sum(1 for m in changes if any(k.startswith("lift_bp") for k in m)) > 100              # busy flags
    assert {m.get("lift:_ch_retry+0") for m in changes} >= {0, 1, 2}                             # a lift waits (budgets / copy list)
    assert sum(1 for m in changes if any(k.startswith("render:_dirty") for k in m)) > 100        # spans composed again


def test_decisions_unchanged(cases, model, rom):
    cs = mine(cases, model)
    got, res = L.run_cases(rom, model, cs)
    bad = []
    for i, (c, g) in enumerate(zip(cs, got)):
        want = c["out"][model]
        if g != want:
            keys = sorted(set(g) | set(want))
            bad.append((i, c["s"], c["b"], [(k, want.get(k), g.get(k)) for k in keys if want.get(k) != g.get(k)][:6]))
    cyc = sorted(r.cycles for r, c in zip(res, cs) if c["s"] != "random")
    print(rom.stem, model, len(cs), "cases;", "real calls T-cycles min / median / max", cyc[0], cyc[len(cyc) // 2], cyc[-1])
    assert not bad, f"{len(bad)} of {len(cs)} cases differ, first: {bad[:3]}"
