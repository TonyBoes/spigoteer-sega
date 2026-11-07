"""python3 sheet.py: renders round 3 | upright | slant in the real map's own tile/palette code (tools/smap_world), DMG row and Color row, with a close-up of the lot,
checks that the building did not change, counts unique DMG tiles, writes ../milkbar_sheet.png (scratch in out/mb/)."""
import os
import subprocess
import sys

import common as C
import cow_lot as L
from PIL import Image

OUT = C.ROOT + '/docs/dev/proposals/smap_milkbar'
TMP = C.ROOT + '/out/mb'
os.makedirs(TMP, exist_ok=True)

GRAIN, LINE = False, '1'
R3 = L.round3()
VARIANTS = [('ROUND 3', R3),
            ('UPRIGHT', L.upright({1: L.UP_A, 3: L.UP_B, 4: L.UP_A}, GRAIN, LINE)),
            ('SLANT', L.slant({1: L.SL_A, 3: L.SL_B, 5: L.SL_A}, GRAIN, LINE))]


def check_unchanged(c):
    """every pixel outside the lot (x 32..95, y 56..71) equals round 3"""
    bad = [(x, y) for y in range(L.H) for x in range(L.W)
           if not (L.X0 <= x < L.X1 and L.Y0 <= y < L.Y1) and c.px[y][x] != R3.px[y][x]]
    return bad


def main():
    items, close = [], []
    for cgb in (False, True):
        tag = 'Color' if cgb else 'DMG'
        for name, c in VARIANTS:
            im = C.render(c, L.BIOME, L.AT, cgb)
            f = f'{TMP}/{name}_{tag}.png'
            im.save(f)
            big = im.resize((im.width * 3, im.height * 3), 0)
            fb = f'{TMP}/{name}_{tag}_x3.png'
            big.save(fb)
            items.append((f'{name} {tag} x3', fb))
            # close-up of the lot and the diner's foot: piece x 16..104, y 46..78 (+8 margin)
            cr = im.crop((16 + 8, 46 + 8, 104 + 8, 72 + 8 + 4))
            cr = cr.resize((cr.width * 6, cr.height * 6), 0)
            fc = f'{TMP}/{name}_{tag}_close.png'
            cr.save(fc)
            close.append((f'{name} {tag} lot x6', fc))
    for name, c in VARIANTS:
        print(name, 'DMG unique tiles', C.tile_count(c), 'building changed pixels:', len(check_unchanged(c)))
    args = [sys.executable, C.ROOT + '/tools/dev/contact_sheet.py', OUT + '/milkbar_sheet.png', '--scale', '1', '--cols', '3',
            '--title', 'milk bar lot + bikes: round 3 | upright bays | slanted bays (DMG row, Color row, then lot close-ups x6)']
    subprocess.run(args + [f'{l}={p}' for l, p in items + close], check=True)
    for name, c in VARIANTS[1:]:
        C.tilemap(c)


if __name__ == '__main__':
    main()
