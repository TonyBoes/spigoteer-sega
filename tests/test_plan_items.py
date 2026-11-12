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


@pytest.mark.parametrize("c", [SALOON, FACTORY])
def test_the_boss_body_is_on_bg_7_and_no_regular_walks_on_it(c):
    with fight("cgb", c) as gb:
        topper = cgb_palette(gb, 7, obj=True)[1:]
        body = cgb_palette(gb, 7)
        skip = 1 if c == FACTORY else -1                  # (the Prototype's lamp: the topper's colour 2 starts green)
        assert [x for k, x in enumerate(body[1:]) if k != skip] == [x for k, x in enumerate(topper) if k != skip], "BG 7 holds his colours (the topper's OBJ 7 pair)"
        assert body[0] == cgb_palette(gb, 2)[0], "over the venue's wall"
        assert cgb_palette(gb, 4)[1:] != topper, "BG 4 is a patron's again"
        seen = set()
        for _ in range(60):
            frames(gb, 10)
            for var, st in zip(gb.read("patron_variant", 16), gb.read("patron_state", 16)):
                if st:
                    seen.add(var)
        assert seen, "regulars came"
        obj, bg = inst(gb)
        for var in seen:
            pi = (var ^ var >> 3) & 7
            assert bg[pi] != 7 and obj[pi] != 7, f"variant {var:#x}: instance {pi} wears his BG 7 / OBJ 7"
            if c == FACTORY:
                assert obj[pi] not in (4, 5), f"variant {var:#x}: the lamp's and the body OBJ slots are his"


def test_ronin_wears_sakuras_palette_in_the_teahouse(gb):
    settle(gb, "ninjas")
    obj, bg = inst(gb)
    assert (obj[1], bg[1]) == (6, 6), "SAKURA"
    assert (obj[2], bg[2]) == (6, 6), "RONIN (look 2, instance 2) shares them"
    want = c5(ATLAS["ninjas"]["obj"]["6"]["cols"][1:])
    assert cgb_palette(gb, 6, obj=True)[1:] == want
    assert bg_slot_colours(gb, 6) == want
    assert {"SAKURA", "RONIN"} <= set(ATLAS["ninjas"]["obj"]["6"]["patrons"]) and ATLAS["ninjas"]["obj"]["7"]["patrons"] == ["POET"]
    assert 7 in obj[:8] and obj.index(7) > 2, "POET keeps OBJ 7 / BG 7 as a later instance"
    assert bg[obj.index(7)] == 7
