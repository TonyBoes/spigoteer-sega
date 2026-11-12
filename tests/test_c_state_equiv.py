# The timing-independent asm/C check: the same scripted run on build/game.gb (asm) and build/game-c.gb (every asm routine as its C twin),
# compared on game STATE at the start of every game step, never on pictures or frame counts (tests/c_state_rig.py explains how it stays
# independent of the C build's slower frames). A difference is a real C-twin bug (or an asm bug): speed cannot cause one here.
#
# On demand: RUN_C_STATE=1 make test F=tests/test_c_state_equiv.py (needs `make cfall`). In the C-build stage (GB_ROM=build/game-c.gb) it runs too.
# Never in the asm build's `make test`: conftest deselects the file (not a skip) unless one of those is set. Not covered: the story map (its walk adapts to the loader rate, see c_state_rig.first_divergence).
import os
import pickle
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from conftest import ROOT, ROM
import c_state_rig as R

ON = True      # (conftest deselects this file unless RUN_C_STATE=1 or the C-build stage: never a skip in the asm run)
pytestmark = [pytest.mark.usefixtures("c_rom_fresh"),
              pytest.mark.timeout(1500)]

WORKER = ROOT / "tests" / "c_state_worker.py"
# (scenario, model, double speed). The Color runs at its shipped double speed and at normal speed; the DMG has only one.
CONFIGS = [("dmg", False), ("cgb", True), ("cgb", False)]
SCENARIOS = ["arcade1", "arcade2", "arcade4", "arcade7", "arcade9", "menus", "boss0", "boss3", "boss6", "pause1", "pause4", "mg0", "mg2", "mg4", "mg6", "mg8", "mg10", "mg12"]


def run_worker(rom, scen, model, ds, out):
    env = dict(os.environ, GB_ROM=str(rom))
    env.pop("GB_DOUBLE_SPEED", None)
    return subprocess.Popen([sys.executable, str(WORKER), scen, model, "1" if ds else "0", str(out)], env=env, cwd=ROOT,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def both(scen, model, ds, rom_a=R.ASM_ROM, rom_c=R.C_ROM):
    with tempfile.TemporaryDirectory() as d:
        pa, pc = Path(d) / "a.pkl", Path(d) / "c.pkl"
        procs = [run_worker(rom_a, scen, model, ds, pa), run_worker(rom_c, scen, model, ds, pc)]
        outs = [p.communicate()[0] for p in procs]
        for p, o in zip(procs, outs):
            assert p.returncode == 0, o[-1500:]
        return pickle.load(open(pa, "rb")), pickle.load(open(pc, "rb"))


# (History: pausing a boss fight on a Color at NORMAL speed livelocked the C ROM until the C split handlers were sped up (src/main.c put8): the pause
# card's fade, src/trans.c vframe, needs the main loop back by line 149 and the C chain resumed it at line 152. Those two runs were strict xfails.)
CASES = [pytest.param(scen, model, ds, id="%s-%s" % (scen, cid))
         for scen in SCENARIOS for (model, ds), cid in zip(CONFIGS, ["dmg", "cgb-double", "cgb-normal"])]


@pytest.mark.parametrize("scen,model,ds", CASES)
def test_the_c_build_keeps_the_same_game_state_as_the_asm_build_at_every_step(scen, model, ds):
    a, c = both(scen, model, ds)
    assert len(a["snaps"]) > 1000 and len(c["snaps"]) > 1000, (len(a["snaps"]), len(c["snaps"]))
    div = R.first_divergence(a, c)
    assert div is None, R.describe(div)


def test_the_comparison_sees_a_difference():
    """A check on the check: the asm build against itself with a different script (seed) must diverge, and with the same script must not."""
    a, _ = both("arcade1", "dmg", False)
    b, _ = both("arcade1_alt", "dmg", False)
    assert R.first_divergence(a, b) is not None, "two different scripts left the same states: the comparison sees nothing"
    a2, c2 = both("arcade1", "dmg", False, R.ASM_ROM, R.ASM_ROM)
    assert R.first_divergence(a2, c2) is None


def test_the_rig_knows_the_game_state_numbers():
    import c_state_scen as S
    from test_flow import PLAYING
    assert S.PLAYING == PLAYING
