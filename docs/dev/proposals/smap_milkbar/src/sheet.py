"""python3 sheet.py: round 3 | A rear view | B side view row | C props, DMG row and Color row at x3, then lot close-ups x6, in the map's own tile/palette code;
checks the building is unchanged; counts unique DMG tiles; writes ../milkbar_sheet3.png (scratch in out/mb/)."""
import os
import subprocess
import sys

import common as C
import cow_lot as L

OUT = C.ROOT + '/docs/dev/proposals/smap_milkbar'
TMP = C.ROOT + '/out/mb'
os.makedirs(TMP, exist_ok=True)

R3 = L.round3()
VARIANTS = [('ROUND 3', R3), ('A rear view bays', L.build_a()), ('B side view row', L.build_b()), ('C props, no lot', L.build_c())]


def check_unchanged(c):
    """every pixel outside the lot rectangle (x 32..95, y 56..71) equals round 3"""
    return [(x, y) for y in range(L.Y1) for x in range(L.W)
            if not (L.X0 <= x < L.X1 and y >= L.Y0) and c.px[y][x] != R3.px[y][x]]


def main():
    items, close = [], []
    for cgb in (False, True):
        tag = 'Color' if cgb else 'DMG'
        for name, c in VARIANTS:
            im = C.render(c, L.BIOME, L.AT, cgb)
            fb = f'{TMP}/{name[:3].strip()}_{tag}_x3.png'
            im.resize((im.width * 3, im.height * 3), 0).save(fb)
            items.append((f'{name} {tag} x3', fb))
            cr = im.crop((16 + 8, 46 + 8, 104 + 8, 76 + 8))
            fc = f'{TMP}/{name[:3].strip()}_{tag}_close.png'
            cr.resize((cr.width * 4, cr.height * 4), 0).save(fc)
            close.append((f'{name} {tag} lot x4', fc))
    for name, c in VARIANTS:
        print(name, 'DMG unique tiles', C.tile_count(c), 'building changed pixels:', len(check_unchanged(c)))
    args = [sys.executable, C.ROOT + '/tools/dev/contact_sheet.py', OUT + '/milkbar_sheet3.png', '--scale', '1', '--cols', '4',
            '--title', 'milk bar round 4c, all front-on: round 3 | A rear view | B side view row | C props (DMG row, Color row, then lot close-ups x4)']
    subprocess.run(args + [f'{l}={p}' for l, p in items + close], check=True)


if __name__ == '__main__':
    main()
