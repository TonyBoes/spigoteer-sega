# Space Lounge on Color (owner Q53, 2026-10-29): the bar palette (BG 0) carries XENO's colours, XENO (aliens variant B) walks in BG 0,
# and BG palette 3 is free (planned for VENUS): no BG cell uses it. DMG is untouched.
import pytest
from conftest import bar_top_row
from test_art import goto_group
from test_patrons import set_patron
from test_venues import BGPAL_BAR, cgb_palette

pytestmark = [pytest.mark.timeout(90), pytest.mark.only_model("cgb")]

SPACE = 9
XENO_B = [30620, 23187, 3138]       # palettes.json aliens_b rgb15 (#E0E0E8 #98A0B0 #101018)


def space_with_aliens(gb):
    goto_group(gb, SPACE)
    gb.write("tip_chance", 0)
    spots = [(0, 24, 1), (1, 56, 0), (2, 88, 1), (3, 40, 2)]
    for bar, x, var in spots:
        set_patron(gb, bar, x, variant=var)
    gb.run(10)                               # (6 frames drew every bar before the venue had the keg split on Color: its ISRs cost the normal-speed frame a vblank)
    return spots


def attr(gb, x, y):
    return gb.pb.memory[1, 0x9800 + y * 32 + x] & 7


def test_the_space_bar_palette_is_xenos_colours(gb):
    space_with_aliens(gb)
    p = cgb_palette(gb, BGPAL_BAR)
    assert p[1:] == XENO_B
    assert p[0] == 11428 or p[0] == cgb_palette(gb, 2)[0], "colour 0 is still the wall"


def test_xeno_walks_in_bg_0_and_nothing_uses_bg_3(gb):
    spots = space_with_aliens(gb)
    for bar, x, var in spots:
        cells = [attr(gb, (x >> 3) + c, bar_top_row(bar) + r) for c in range(2) for r in range(2)]
        want = {0: 2, 1: 0, 2: 4}[var]
        assert set(cells) == {want}, (bar, x, var, cells)
    gb.run(40)
    for y in range(32):
        for x in range(32):
            assert attr(gb, x, y) != 3, (x, y)
