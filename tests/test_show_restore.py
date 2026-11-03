# After a show OBJ 5 is the venue's 5th palette instance again (level.c show_pal5; during one the dancers have it above the stage, tests/test_show_obj5.py): the Atlas's OBJ 5 colours, in every generated venue.
import json

import pytest
from conftest import ROOT, logic_paused
from test_patron_imports import settle
from test_plan_slots import atlas5, to5
from test_venues import cgb_palette

ATLAS = json.loads((ROOT / "tools" / "artifacts" / "palette_plan" / "plan_slots.json").read_text())["venues"]


@pytest.mark.only_model("cgb")
@pytest.mark.parametrize("k", ["robots", "sports", "lumberjacks", "chefs"])
def test_obj_5_comes_back_from_the_show(gb, k):
    settle(gb, k)
    want = atlas5(ATLAS[k]["obj"]["5"]["cols"][1:])
    assert [to5(c) for c in cgb_palette(gb, 5, obj=True)[1:]] == want, "before"
    with logic_paused(gb):
        gb.write("show_timer", 200)
    gb.run(20)
    assert [to5(c) for c in cgb_palette(gb, 5, obj=True)[1:]] != want, "the show's colours"
    with logic_paused(gb):
        gb.write("show_timer", 0)
    gb.run(20)
    assert [to5(c) for c in cgb_palette(gb, 5, obj=True)[1:]] == want, "after the show"
