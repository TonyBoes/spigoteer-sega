# Space Lounge on Color (owner Q53, 2026-10-29): the bar palette (BG 0) carries XENO's colours, XENO (aliens variant B) walks in BG 0,
# and BG palette 3 is VENUS's (the Atlas import, Color-only look 7 on OBJ 5 / BG 3): only she uses it. DMG is untouched.
import pytest
from conftest import bar_top_row
from test_art import goto_group
from test_patrons import put, set_patron
from test_venues import BGPAL_BAR, cgb_palette

pytestmark = [pytest.mark.timeout(90), pytest.mark.only_model("cgb")]

SPACE = 9
XENO_B = [30620, 23187, 3138]       # palettes.json aliens_b rgb15 (#E0E0E8 #98A0B0 #101018)


def space_with_aliens(gb):
    goto_group(gb, SPACE)
    gb.write("tip_chance", 0)
    for i in range(16):                                   # (no start patron under the ones placed: their random looks differ with the palette instances)
        put(gb, "patron_state", i, 0)
    gb.write("patrons_live", 0)
    spots = [(0, 24, 1), (1, 56, 0), (2, 88, 1), (3, 40, 2)]
    for bar, x, var in spots:
        set_patron(gb, bar, x, variant=var)
    gb.run(6)
    return spots


def attr(gb, x, y):
    return gb.pb.memory[1, 0x9800 + y * 32 + x] & 7


def test_the_space_bar_palette_is_xenos_colours(gb):
    space_with_aliens(gb)
    p = cgb_palette(gb, BGPAL_BAR)
    assert p[1:] == XENO_B
    assert p[0] == 11428 or p[0] == cgb_palette(gb, 2)[0], "colour 0 is still the wall"


def test_xeno_walks_in_bg_0_and_venus_alone_uses_bg_3(gb):
    spots = space_with_aliens(gb)
    for bar, x, var in spots:
        cells = [attr(gb, (x >> 3) + c, bar_top_row(bar) + r) for c in range(2) for r in range(2)]
        want = {0: 2, 1: 0, 2: 7}[var]      # (GLORP, look 2, has BG 7 in the Atlas layout)
        assert set(cells) == {want}, (bar, x, var, cells)
    venus = 7 | (4 ^ 7) << 3 | 0x40                       # look 7 on palette instance 4 (OBJ 5, BG 3)
    set_patron(gb, 1, 120, variant=venus)
    gb.run(6)
    assert {attr(gb, 15 + c, bar_top_row(1) + r) for c in range(2) for r in range(2)} == {3}
