# patron-rev-2: the Color-only mid-frame palette split (game.h SPLIT_*). BG palette 5 is the stage's; at the first line of the playfield
# (row 5, y 40) lcd_isr rewrites it with the patron palette in HRAM SPLIT_PAL, and the VBlank puts the stage's back.
import pytest

from test_lift import boot_play
from test_venues import cgb_palette

SPLIT_ON, SPLIT_WANT, SPLIT_PAL, SPLIT_STG = 0xFFD4, 0xFFD5, 0xFFD6, 0xFFDE
SPLIT_LY = 39
TILE = 255                                     # a solid colour-3 tile, put in BG tile 255 for the test
COL = 9


def put_tile(gb, row, pal):
    gb.write(0xFF4F, 0)
    for k in range(16):
        gb.write(0x8000 + TILE * 16 + k, 0xFF)  # colour 3 everywhere (the shared block: not a stage tile in use)
    gb.write(0x9800 + row * 32 + COL, TILE)
    gb.write(0xFF4F, 1)
    gb.write(0x9800 + row * 32 + COL, pal)
    gb.write(0xFF4F, 0)


def test_dmg_never_splits():
    gb = boot_play("dmg")
    try:
        gb.run(5)
        assert gb.read(SPLIT_ON, 1)[0] == 0
    finally:
        gb.stop()


def test_the_split_paints_the_playfield_with_the_patron_palette_and_the_stage_with_its_own():
    gb = boot_play("cgb")
    try:
        gb.run(3)
        assert gb.read(SPLIT_ON, 1)[0] == 1
        stg = list(gb.read(SPLIT_STG, 8))
        pal5 = cgb_palette(gb, 5)
        assert [(pal5[i // 2] >> (8 * (i & 1))) & 0xFF for i in range(8)] == stg, "the VBlank restored the stage's palette"
        for k, b in enumerate([0, 0, 0x1F, 0, 0xE0, 0x03, 0, 0x7C]):    # black, red, green, blue
            gb.write(SPLIT_PAL + k, b)
        put_tile(gb, 4, 5)                      # the stage's last row (y 32..39)
        put_tile(gb, 5, 5)                      # the playfield's first row (y 40..47)
        gb.run(3)
        img = gb.image()
        x = COL * 8 + 3
        for y in range(32, 40):
            r, g, b = img.getpixel((x, y))[:3]
            assert not (r > 200 and g < 60 and b < 60 or b > 200 and r < 60 and g < 60), f"stage line {y} is not the patron's: {(r, g, b)}"
        for y in range(40, 48):
            r, g, b = img.getpixel((x, y))[:3]
            assert b > 200 and r < 60 and g < 60, f"playfield line {y} wears the patron palette (blue, colour 3): {(r, g, b)}"
        # (PyBoy is not cycle-accurate: that the write ends before line 40's pixels was checked in SameBoy, see the commit)
        # the stage palette is back after the VBlank, the window's LYC is kept
        assert cgb_palette(gb, 5) == pal5
        assert gb.read(SPLIT_WANT, 1)[0] == 86
    finally:
        gb.stop()
