# Owner 2026-10-30: ASH (the Lodge's look C) has his skin in palette colour 1 like every other look, so his palette can be shared. On Color
# the level load plane-swaps his tiles (level.c swap_gus, as GUS's) and assets/palettes.json "lumberjacks_c" has colours 1 and 2 exchanged:
# what the screen shows must be exactly what the original art drew with the original palette (#389040 hat and clothes, #906800 skin, #102810).
import re

import pytest
from conftest import ROOT
from test_art import goto_group
from test_patrons import BASE, SHIFT0_OFS, SHIFTED
from test_venues import cgb_palette

pytestmark = pytest.mark.timeout(60)

OLD = {1: 0x389040, 2: 0xC08858, 3: 0x102810}      # lumberjacks_c: index 1 (art '-') hat and clothes, 2 ('+') skin (#906800 until the owner's 2026-10-31 "Ash to medium", Q86), 3 ('#') dark


def rgb15(c):
    return (c >> 19 & 31) | (c >> 11 & 31) << 5 | (c >> 3 & 31) << 10


def rom_tiles():
    src = (ROOT / "build" / "patrons_lumberjacks.c").read_text()
    return bytes(int(h, 16) for h in re.findall(r"0x([0-9A-F]{2})", src))


def pixels(t):
    return [(t[2 * r] >> (7 - x) & 1) | (t[2 * r + 1] >> (7 - x) & 1) << 1 for r in range(8) for x in range(8)]


def ash_ids():
    return list(range(84, 126)) + list(range(SHIFT0_OFS + 8, SHIFT0_OFS + 12)) + list(range(SHIFTED + 8, SHIFTED + 12))


@pytest.mark.only_model("cgb")
def test_ash_looks_the_same_on_color(gb):
    goto_group(gb, 2)
    gb.run(30)
    assert gb.mem("cur_group") == 2
    rom = rom_tiles()
    vram = gb.pb.memory
    bg = cgb_palette(gb, 2 + 2)                     # BGPAL_PATRON + 2: variant C
    assert bg[1] == rgb15(0xC08858) and bg[2] == rgb15(0x389040) and bg[3] == rgb15(0x102810), "skin in colour 1, green in 2"
    swapped = 0
    for o in ash_ids():
        t = BASE + o
        a = 0x9000 + 16 * t if t < 128 else 0x8800 + 16 * (t - 128)
        want = [0 if i == 0 else rgb15(OLD[i]) for i in pixels(rom[16 * o:16 * o + 16])]
        got = [bg[i] if i else 0 for i in pixels(bytes(vram[0, a:a + 16]))]
        assert got == want, f"tile {o}: the screen's colours changed"
        swapped += pixels(bytes(vram[0, a:a + 16])) != pixels(rom[16 * o:16 * o + 16])
    assert swapped, "his tiles are plane-swapped in VRAM"


@pytest.mark.only_model("cgb")
def test_the_other_lodge_looks_are_not_swapped(gb):
    goto_group(gb, 2)
    gb.run(30)
    rom = rom_tiles()
    vram = gb.pb.memory
    for o in list(range(0, 84)) + list(range(126, 136)):
        t = BASE + o
        a = 0x9000 + 16 * t if t < 128 else 0x8800 + 16 * (t - 128)
        assert bytes(vram[0, a:a + 16]) == rom[16 * o:16 * o + 16]


@pytest.mark.only_model("dmg")
def test_ash_is_the_original_art_on_the_dmg(gb):
    goto_group(gb, 2)
    gb.run(30)
    rom = rom_tiles()
    vram = gb.pb.memory
    for o in ash_ids():
        t = BASE + o
        a = 0x9000 + 16 * t if t < 128 else 0x8800 + 16 * (t - 128)
        assert bytes(vram[a:a + 16]) == rom[16 * o:16 * o + 16]
