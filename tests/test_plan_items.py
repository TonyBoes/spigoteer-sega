# Four items the Graphics Atlas page check found (QUEUE 11-11), brought in line with the plan ("the plan is the spec"). Color only; every DMG golden stays.
#   1  Saloon full mug: OBJ 1 colour 1 is the tan #FFE6CD (5-bit 31, 28, 25), no longer the cream #FFF6D5.
#   2  Saloon boss body: BG 7 (not BG 4), and no patron walks on BG 7 during the fight (the Saloon's instance 3 sits out).
#   3  Robot Factory boss body: BG 7 (not BG 4, BLIP and NEKA's).
#   4  Teahouse RONIN: SAKURA's OBJ 6 / BG 6 (not his own OBJ 7 / BG 7, which is POET's).
# Each reads the palette RAM (and the instance tables the engine looks them up in) in the real Color scene.
import pytest
from boss_common import fight, frames
from conftest import ROOT
from test_patron_imports import bg_slot_colours, settle
from test_venues import cgb_palette

import json

ATLAS = json.loads((ROOT / "tools" / "artifacts" / "palette_plan" / "plan_slots.json").read_text())["venues"]
SALOON, FACTORY, TEAHOUSE = 0, 5, 7
pytestmark = [pytest.mark.only_model("cgb"), pytest.mark.timeout(240)]


def c5(hexs):
    return [(int(h[1:3], 16) >> 3) | (int(h[3:5], 16) >> 3) << 5 | (int(h[5:7], 16) >> 3) << 10 for h in hexs]


def inst(gb):
    sc = gb.addr("story_scratch")
    return list(gb.read(sc + 254, 8)), list(gb.read(sc + 262, 8))       # INST_OBJ, INST_BG


def test_the_saloon_full_mug_is_the_plans_tan(gb):
    settle(gb, "cowboys")
    assert cgb_palette(gb, 1, obj=True)[1] == c5(["#FFE6CD"])[0] == 31 | 28 << 5 | 25 << 10
    assert cgb_palette(gb, 1, obj=True)[1:] == c5(ATLAS["cowboys"]["obj"]["1"]["cols"][1:]), "OBJ 1 is the Atlas's"
