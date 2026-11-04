"""Transcribe beam.txt into an indexed PNG (24x48: the 40 rows padded to 3 bands of 8x16 sprites) for the lint, plus x4 previews
(DMG OBP1 0xE4 greys, CGB the UFO palette) of the UFO and the beam together. Usage: python3 beam_png.py OUTDIR"""
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1]
KEY = {'.': 0, '-': 1, '+': 2, '#': 3}
rows = [l for l in open(os.path.join(HERE, 'beam.txt')).read().split('\n') if l and not l.startswith(';')]
im = Image.new('P', (24, 48), 0)
im.putpalette([255, 255, 255, 170, 170, 170, 85, 85, 85, 0, 0, 0])
for y, r in enumerate(rows):
    for x, c in enumerate(r):
        im.putpixel((x, y), KEY[c])
im.save(os.path.join(OUT, 'beam.png'))
ufo = Image.open(os.path.join(HERE, '../../../../assets/story_map/obj_ufo.png'))
for name, bg, pal_u, pal_b in (
        ('dmg', (255, 255, 255), [None, (255, 255, 255), (170, 170, 170), (0, 0, 0)], [None, (170, 170, 170), (85, 85, 85), (0, 0, 0)]),
        ('cgb', (32, 40, 88), [None, (240, 248, 248), (112, 152, 216), (24, 24, 64)], [None, (240, 248, 248), (112, 152, 216), (24, 24, 64)])):
    pv = Image.new('RGB', (32, 60), bg)
    for y in range(11):
        for x in range(24):
            v = ufo.getpixel((x, y))
            if v:
                pv.putpixel((4 + x, 4 + y), pal_u[v])
    for y, r in enumerate(rows):
        for x, c in enumerate(r):
            if KEY[c]:
                pv.putpixel((4 + x, 15 + y), pal_b[KEY[c]])
    pv.resize((128, 240), Image.NEAREST).save(os.path.join(OUT, 'ufo_beam_%s_x4.png' % name))
    pv.save(os.path.join(OUT, 'ufo_beam_%s_x1.png' % name))
