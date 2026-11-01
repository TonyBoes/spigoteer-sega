# The patron art imports of Stadium (sports), Lodge (lumberjacks) and Factory (robots; v2: BOXY, VOLTA and the third look): their
# palettes (assets/palettes.json), their tiles in VRAM and the drawn gaps. Until now only a golden per group (test_art.py) covered them,
# which sees a wrong colour but not which look or which palette slot it is.
#   palettes  assets/palettes.json holds three colours per look (light, mid, dark) whose RGB15 are the hex values converted; the Color
#             game puts them in BG palette 2 + v (and the OBJ palette of the lifted one, test_lift.py); Factory's BOXY (robots_a) is
#             yellow #f8d848, grey-blue #7888a0, dark #101828.
#   tiles     a group's tile block is PATRON_GROUP_TILES (152) long: per look 7 shifted poses of 6 tiles, the shared blank pair, the
#             shift-0 poses (4 tiles each), then 3 back views of 4 tiles; every look's block has pixels, no two looks are the same figure.
#   gaps      tools/gen_art.py DRAWN_GAPS: the only enclosed index-0 pixels (see through when lifted, wall colour on the BG) are VOLTA's
#             crest (8, 1) and (9, 1); no other look of the three groups has any, read back from the figures' own VRAM tiles.
import json
import re
import sys

import pytest
from conftest import ROOT
from test_art import GROUPS, goto_group
from test_lift import LIFT_PAL, OBJ_BASE
from test_patrons import BASE, BLANK, BACK_BASE, SHIFTED
from test_venues import cgb_palette

sys.path.insert(0, str(ROOT / "tools"))
import gen_art    # noqa: E402

PALS = json.loads((ROOT / "assets" / "palettes.json").read_text())
IMPORTS = ["sports", "lumberjacks", "robots"]                        # Stadium, Lodge, Factory
ART_H = (ROOT / "build" / "art.h").read_text()
pytestmark = pytest.mark.timeout(120)


def rgb15(hexs):
    r, g, b = (int(hexs[i:i + 2], 16) for i in (1, 3, 5))
    return (r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10)


def settle(gb, g):
    goto_group(gb, GROUPS.index(g))
    gb.write("intro_timer", 255)
    gb.run(40)


def tile(gb, t):
    return bytes(gb.read(0x8000 + t * 16 if t >= 128 else 0x9000 + t * 16, 16))


def figure(gb, look):
    """The look's shift-0 pose as the 16x16 art gen_art checks ('.' = index 0): columns are tiles t / t + 1 and t + 2 / t + 3."""
    t = OBJ_BASE + 4 * look
    art = [[None] * 16 for _ in range(16)]
    for x in range(16):
        for y in range(16):
            d = tile(gb, t + 2 * (x // 8) + y // 8)
            row, bit = y % 8, 7 - x % 8
            v = (d[2 * row] >> bit & 1) | ((d[2 * row + 1] >> bit & 1) << 1)
            art[y][x] = "." if v == 0 else str(v)
    return art


@pytest.mark.parametrize("g", IMPORTS)
def test_the_palettes_json_entries_are_three_consistent_colours(g):
    for v in "abc":
        e = PALS[f"{g}_{v}"]
        assert len(e["hex"]) == 3 and [rgb15(h) for h in e["hex"]] == e["rgb15"], (g, v, e)
        assert len(set(e["hex"])) == 3, "light, mid and dark are three different colours"


def test_factorys_boxy_is_yellow_grey_blue_and_dark():
    assert PALS["robots_a"]["hex"] == ["#f8d848", "#7888a0", "#101828"]
    assert PALS["robots_a"]["rgb15"] == [rgb15("#f8d848"), rgb15("#7888a0"), rgb15("#101828")]


def bg_slot_colours(gb, slot):
    """Colours 1-3 of BG palette `slot` as the playfield shows it: the palette RAM, except the chain's slots (BG 5 early, BG 6 late: the mid-frame reloads put them
    in the playfield and the VBlank puts the stage's back), whose playfield colours are the buffers the ISR writes from (game.h SPLIT_E_PAL, SPLIT_PAL)."""
    early = 6 if (int(re.search(r"LOOKS_EARLY6 0x([0-9A-F]+)u", (ROOT / "build" / "looks.h").read_text()).group(1), 16) >> gb.mem("cur_group")) & 1 else 5   # (looks.h: which stage slot the chain reloads early)
    if slot in (5, 6) and gb.read(0xFFD4, 1)[0] == 3 and slot != early:
        raw = list(gb.read(0xFFD6, 8))
    elif slot in (5, 6) and gb.read(0xFFD4, 1)[0] == 3:
        base = gb.addr("story_scratch") + 238
        raw = [gb.read(base + i, 1)[0] for i in range(8)]
    else:
        return cgb_palette(gb, slot)[1:]
    return [raw[2 * i] | raw[2 * i + 1] << 8 for i in range(1, 4)]


# The slots of the three looks A, B, C (looks 0-2) on the Color level screen, and their palettes. The other venues keep BG 2 + v and the legacy OBJ slots; the
# Factory follows the Graphics Atlas (extra_looks_slots.md): BOXY BG 3 / OBJ 3, VOLTA BG 6 (the chain's late reload) / OBJ 6, and BLIP on NEKA's cyan,
# BG 4 / OBJ 4 (the owner moved BLIP off OBJ 7 to the cyan: plan_data PLANS["robots"] moves).
def looks_slots(g):
    if g == "robots":
        return [(3, 3, "robots_a"), (6, 6, "robots_b"), (4, 4, "robots_neka")]
    return [(2 + v, LIFT_PAL[v], f"{g}_{k}") for v, k in enumerate("abc")]


@pytest.mark.only_model("cgb")
@pytest.mark.parametrize("g", IMPORTS)
def test_the_color_game_loads_each_looks_palette_into_bg_and_obj(gb, g):
    settle(gb, g)
    for v, (bg, obj, key) in enumerate(looks_slots(g)):
        want = PALS[key]["rgb15"]
        assert bg_slot_colours(gb, bg) == want, f"{g} look {v}: BG palette {bg}"
        assert cgb_palette(gb, obj, obj=True)[1:] == want, f"{g} look {v}: lifted OBJ palette {obj}"


def test_the_group_tile_block_is_the_documented_size():
    n = int(re.search(r"#define PATRON_GROUP_TILES (\d+)", ART_H).group(1))
    assert SHIFTED == 3 * 7 * 6 + 2 + 3 * 4 and n == SHIFTED + 12 == 152, (SHIFTED, n)


@pytest.mark.parametrize("g", IMPORTS)
def test_each_look_has_its_own_tiles_blank_pair_and_back_view(gb, g):
    settle(gb, g)
    figs = [figure(gb, v) for v in range(3)]
    for v, f in enumerate(figs):
        assert sum(c != "." for row in f for c in row) > 60, f"{g} look {v}: the figure is drawn"
    assert len({tuple(map(tuple, f)) for f in figs}) == 3, "three different figures"
    assert tile(gb, BLANK) == bytes(16) and tile(gb, BLANK + 1) == bytes(16), "the shared blank pair is plain colour 0"
    for v in range(3):
        back = [tile(gb, BACK_BASE + v * 4 + k) for k in range(4)]
        assert all(any(b) for b in back), f"{g} look {v}: back view"
    shifted = [tile(gb, BASE + v * 42 + k) for v in range(3) for k in range(42)]
    assert len({tuple(shifted[v * 42:(v + 1) * 42]) for v in range(3)}) == 3, "every look's 42 shifted tiles differ"


@pytest.mark.parametrize("g", IMPORTS)
def test_only_the_drawn_gaps_are_see_through_in_the_vram_figures(gb, g):
    settle(gb, g)
    for v in range(3):
        holes = gen_art.index0_holes(figure(gb, v))
        assert holes == gen_art.DRAWN_GAPS.get((g, "front", v), set()), (g, v, sorted(holes))
    if g == "robots":
        assert gen_art.DRAWN_GAPS[("robots", "front", 1)] == {(8, 1), (9, 1)}, "VOLTA's crest"
        assert figure(gb, 1)[1][8] == "." and figure(gb, 1)[1][9] == "."
