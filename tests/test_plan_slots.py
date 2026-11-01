# The drift test: the game matches the Graphics Atlas. plan_slots.json is the Atlas's own export (tools/dev/export_plan_slots.py); this file checks the game
# against it, so a venue import that disagrees with the Atlas (or an Atlas edit the game has not followed) turns red.
#   keg      every venue's keg BG slot (build/art.h VENUE_KEG_BG0) is the Atlas's keg_bg.
#   Factory  the imported venue, checked slot by slot on the Color level screen: BG 0-7 and OBJ 0-7 colours 1-3 equal the Atlas's (5-bit), where the chain's
#            slots (BG 1 keg, BG 5 early, BG 6 late) are read from the buffers the mid-frame writes come from, and the game's instance tables (INST_OBJ,
#            INST_BG) pair each OBJ slot with the BG slot the Atlas lists the same patrons on.
#   others   NOT_IMPORTED lists the venues whose palettes are still the old ones; the test says so rather than passing silently, and the list must shrink,
#            never grow: a venue that already matches is rejected from it.
import json

import pytest
from conftest import ROOT, keg_bg
from test_art import goto_group
from test_patron_imports import bg_slot_colours, settle
from test_venues import cgb_palette

ATLAS = json.loads((ROOT / "tools" / "artifacts" / "palette_plan" / "plan_slots.json").read_text())["venues"]
THEMES = ["cowboys", "sports", "lumberjacks", "chefs", "divers", "robots", "punks", "ninjas", "zoo", "aliens"]      # the game's theme order (saloon .. space)
IMPORTED = ["robots", "sports", "lumberjacks", "chefs"]      # the venues on the Atlas slots (the generated instances: build/looks.c)
NOT_IMPORTED = {"divers", "punks", "ninjas", "zoo", "aliens"}
pytestmark = pytest.mark.timeout(120)


def to5(c):
    return (c & 31, (c >> 5) & 31, (c >> 10) & 31)


def atlas5(hexs):
    return [(int(h[1:3], 16) >> 3, int(h[3:5], 16) >> 3, int(h[5:7], 16) >> 3) for h in hexs]


def keg_colours(gb):
    base = gb.addr("story_scratch") + 270
    raw = [gb.read(base + i, 1)[0] for i in range(8)]
    return [raw[2 * i] | raw[2 * i + 1] << 8 for i in range(1, 4)]


@pytest.mark.parametrize("t", range(10))
def test_the_keg_slot_is_the_atlas_one(t):
    assert keg_bg(t) == ATLAS[THEMES[t]]["keg_bg"], THEMES[t]


def test_the_atlas_export_has_the_documented_shape():
    for k in THEMES:
        v = ATLAS[k]
        assert sorted(v["field"] + v["above"]) == sorted(set(v["field"] + v["above"])), k
        assert set(v["bg"]) == set(v["obj"]) == {str(i) for i in range(8)}, k
        assert all(len(e["cols"]) == 4 for e in list(v["bg"].values()) + list(v["obj"].values())), k
    assert ATLAS["robots"]["field"] == [0, 2, 3, 7] and ATLAS["robots"]["above"] == [1, 5, 6], "the Factory's chain reloads BG 1, 5, 6 where the playfield starts"


@pytest.mark.only_model("cgb")
@pytest.mark.parametrize("k", IMPORTED)
def test_the_imported_venues_slots_are_the_atlas_slots(gb, k):
    settle(gb, k)
    v = ATLAS[k]
    assert gb.read(0xFFD4, 1)[0] == 3, "the mid-frame chain is on"
    for slot in range(8):
        if not v["bg"][str(slot)]["patrons"] and not v["bg"][str(slot)]["other"]:
            continue                                          # (a free slot: the stage's palette above the playfield, nobody's in it)
        want = atlas5(v["bg"][str(slot)]["cols"][1:])
        if slot == 1:
            got = keg_colours(gb)                             # (the chain's HUD slot: the keg's, or the Stadium's PETE and FRANK)
        else:
            got = bg_slot_colours(gb, slot)
        assert [to5(c) for c in got] == want, f"BG {slot}"
    for slot in range(8):
        want = atlas5(v["obj"][str(slot)]["cols"][1:])
        if slot == 0:
            continue                                          # (OBJ 0 is the shared slot of the mug and the HUD: not a patron palette)
        if not v["obj"][str(slot)]["patrons"] and not v["obj"][str(slot)]["other"]:
            continue
        got = [to5(c) for c in cgb_palette(gb, slot, obj=True)[1:]]
        assert got == want, f"OBJ {slot}"
    s = gb.addr("story_scratch")
    obj, bg = list(gb.read(s + 254, 8)), list(gb.read(s + 262, 8))
    for o, b in list(zip(obj, bg))[:6 if k == "robots" else 7]:
        assert set(v["obj"][str(o)]["patrons"]) <= set(v["bg"][str(b)]["patrons"]) and v["obj"][str(o)]["patrons"], (o, b)   # (the Lodge's BG 2 lists the patrons of OBJ 1 and 3 both)


def patron_slots_match(gb, k):
    goto_group(gb, THEMES.index(k))
    gb.write("intro_timer", 255)
    gb.run(40)
    v = ATLAS[k]
    return all([to5(c) for c in cgb_palette(gb, s, obj=o)[1:]] == atlas5(v["obj" if o else "bg"][str(s)]["cols"][1:])
               for o in (False, True) for s in range(8) if v["obj" if o else "bg"][str(s)]["patrons"])


@pytest.mark.only_model("cgb")
def test_the_saloons_patron_slots_are_the_atlas_slots(gb):
    """The Saloon (cowboys) was imported first: every slot that holds patrons has the Atlas's colours (its other slots are the mug, glass and show colours)."""
    assert patron_slots_match(gb, "cowboys")


@pytest.mark.only_model("cgb")
@pytest.mark.parametrize("k", sorted(NOT_IMPORTED))
def test_a_venue_not_yet_imported_still_differs_from_the_atlas(gb, k):
    """The to-do list is honest: if every playfield slot of a venue already equals the Atlas's, it is imported and must leave NOT_IMPORTED."""
    assert not patron_slots_match(gb, k), f"{k} matches the Atlas: remove it from NOT_IMPORTED"
