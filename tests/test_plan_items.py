# Four items the Graphics Atlas page check found (QUEUE 11-11), brought in line with the plan ("the plan is the spec"). Color only; every DMG golden stays.
#   1  Saloon full mug: OBJ 1 colour 1 is the tan #FFE6CD (5-bit 31, 28, 25), no longer the cream #FFF6D5.
#   2  Saloon boss body: BG 7 (not BG 4), and no patron walks on BG 7 during the fight: the Saloon's instance 3 (OBJ 4, ROSIE and REDD's palette-4 look) moves to the free BG 4
#      for the fight, same colours (owner 2026-11-12: "You have free bg palettes"); all 21 combos stay in the fight.
#   3  Robot Factory boss body: BG 7 (not BG 4, BLIP and NEKA's).
#   4  Teahouse RONIN: SAKURA's OBJ 6 / BG 6 (not his own OBJ 7 / BG 7, which is POET's).
# Each reads the palette RAM (and the instance tables the engine looks them up in) in the real Color scene.
import pytest
from boss_common import fight, frames
from conftest import ROOT, ROM
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
        if c == FACTORY:
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


def saloon_fight_pal_dump(gb):
    return [cgb_palette(gb, i) for i in range(8)], [cgb_palette(gb, i, obj=True) for i in range(8)]


def test_the_saloons_instance_3_walks_on_bg_4_in_the_fight_in_its_own_colours(gb):
    """OBJ 4 / BG 7 in the levels, OBJ 4 / BG 4 in the fight (BG 4 is instance 2's, OBJ 7's pair: the topper's, so it sits out): a slot move, the colours are the Atlas's OBJ 4."""
    want = c5(ATLAS["cowboys"]["obj"]["4"]["cols"][1:])
    settle(gb, "cowboys")
    obj, bg = inst(gb)
    assert (obj[3], bg[3]) == (4, 7)
    assert bg_slot_colours(gb, 7) == want
    lvl_bg, lvl_obj = saloon_fight_pal_dump(gb)
    with fight("cgb", SALOON) as fg:
        frames(fg, 30)
        obj, bg = inst(fg)
        assert (obj[3], bg[3]) == (4, 4), "instance 3: OBJ 4, BG 4 (BG 7 is the body's)"
        assert cgb_palette(fg, 4)[1:] == want, "BG 4 = the same colours as OBJ 4"
        assert cgb_palette(fg, 4)[0] == cgb_palette(fg, 2)[0], "over the wall"
        assert bg.count(7) == 0
        pis = set()                                  # an instance-3 regular (ROSIE, REDD ...) does come in the fight
        for _ in range(300):
            frames(fg, 10)
            pis |= {(v ^ v >> 3) & 7 for v, st in zip(fg.read("patron_variant", 16), fg.read("patron_state", 16)) if st}
            if 3 in pis:
                break
        assert 3 in pis and not pis & {2, 4}, pis
        f_bg, f_obj = saloon_fight_pal_dump(fg)
    # nothing else changed colour: the instances' BG 2, 3, the bar, the HUD slots, and the OBJ palettes the fight does not own (OBJ 5 and 7: the body / topper's)
    for i in (0, 1, 2, 3):
        assert f_bg[i] == lvl_bg[i], f"BG {i}"
    for i in (0, 1, 2, 3, 4, 6):
        assert f_obj[i] == lvl_obj[i], f"OBJ {i}"


def test_every_saloon_fight_combo_is_in_the_table():
    """All 21 (look, palette) combinations of the fight: every sal_combo entry but GUS (look 2) and the instances on OBJ 7 and 5 (pi 2, 4). The table is in the ROM as its bytes."""
    import re
    m = (ROOT / "src" / "mirror.c").read_text()
    blk = re.search(r"sal_combo\[\d+\] = \{(.*?)\};", m, re.S).group(1)
    combos = [(int(l), int(p)) for l, p in re.findall(r"V\((\d), (\d)\)", blk)]
    assert len(combos) == 36

    def v(l, p):
        return l | (p ^ l) << 3 | (0x40 if l > 2 else 0)
    want = [v(l, p) for l, p in combos if l != 2 and p in (0, 1, 3)]
    assert len(want) == 21
    rom = ROM.read_bytes()
    assert any(sorted(rom[i:i + 21]) == sorted(want) for i in range(len(rom) - 21) if rom[i] in want), "the 21 combos are a table in the ROM"
    body = re.search(r"sal_boss\[(\d+)\] = \{(.*?)\};", m, re.S)
    assert body.group(1) == "21"
    assert sorted((int(l), int(p)) for l, p in re.findall(r"V\((\d), (\d)\)", body.group(2))) == sorted((l, p) for l, p in combos if l != 2 and p in (0, 1, 3))


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
