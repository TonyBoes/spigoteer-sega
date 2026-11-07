"""python3 sheet5.py (the A5 layout, branch worktree-agent-a9eca06ceee777aa2): round 4c A | round 4d NEW (3/4 bikes, the lot as the road's own widening), DMG and Color at x3, then the wider shot in the real map
(world2.WORLD around the milk bar, the piece placed at its cell (39, 23), the road beside and below it); writes ../milkbar_sheet5.png.  Scratch in out/mb/.
In the wide shot the piece's non-blank cells replace the world's cells; the old 80 x 56 cow venue's cells that the piece leaves blank get the farm ground.
The cow's two cells (x 41 and 42, rows 30 and 31) are shown over the road (its meadow index 0 is left transparent): see NOTES.md."""
import subprocess
import sys

import a5env  # noqa: F401  (first: the A5 scratch world in front of tools/smap_world)
import common as C
import cow_lot as A
import cow_lot4 as N
import world2 as WD
from PIL import Image

P = C.P
OUT = C.ROOT + '/docs/dev/proposals/smap_milkbar'
TMP = C.ROOT + '/out/mb'
w = WD.WORLD
X0, Y0, X1, Y1 = 36, 49, 64, 70                     # the crop, in cells
AT = (50, 55)
COW_CELLS = {(2, 7), (3, 7), (2, 8), (3, 8)}


def tile_rgb(rows, pal, cgb, transparent0=None):
    cols = P.get(pal)
    im = Image.new('RGB', (8, 8))
    for y in range(8):
        for x in range(8):
            v = int(rows[y][x])
            im.putpixel((x, y), tuple(cols[v]) if cgb else (P.DMG_SHADE[v],) * 3)
    return im


def world_shot(c, cgb):
    base = Image.new('RGB', ((X1 - X0) * 8, (Y1 - Y0) * 8))
    for cy in range(Y0, Y1):
        for cx in range(X0, X1):
            base.paste(tile_rgb(w.tile(cx, cy), WD.MERGE.get(w.pal[cy][cx], w.pal[cy][cx]), cgb), ((cx - X0) * 8, (cy - Y0) * 8))
    rx0, ry0, rx1, ry1 = w.venue_rect['cow']
    for (i, j), (t, p) in C.cells(c).items():
        cx, cy = AT[0] + i, AT[1] + j
        inside_old = rx0 <= cx <= rx1 and ry0 <= cy <= ry1
        if t == C.BLANK:
            if inside_old:
                base.paste(tile_rgb(C.ground_cell('farm', cx, cy), 'farm', cgb), ((cx - X0) * 8, (cy - Y0) * 8))
            continue
        if (i, j) in COW_CELLS:                      # the cow over the road: only its non-meadow pixels
            ti = tile_rgb(t, p, cgb)
            for y in range(8):
                for x in range(8):
                    if t[y][x] != '0':
                        base.putpixel(((cx - X0) * 8 + x, (cy - Y0) * 8 + y), ti.getpixel((x, y)))
            continue
        base.paste(tile_rgb(t, p, cgb), ((cx - X0) * 8, (cy - Y0) * 8))
    return base


def main():
    pieces = [('4d 3/4 bikes, road-lot, A5', N.build())]
    items, wide = [], []
    for cgb in (False, True):
        tag = 'Color' if cgb else 'DMG'
        for name, c in pieces:
            im = C.render(c, N.BIOME, N.AT, cgb)
            f = f'{TMP}/s4_{name[:2]}_{tag}.png'
            im.resize((im.width * 3, im.height * 3), 0).save(f)
            items.append((f'{name} {tag} x3', f))
    for cgb in (False, True):
        tag = 'Color' if cgb else 'DMG'
        for name, c in pieces:
            im = world_shot(c, cgb)
            f = f'{TMP}/s4w_{name[:2]}_{tag}.png'
            im.resize((im.width * 3, im.height * 3), 0).save(f)
            wide.append((f'{name} in the map {tag} x3', f))
    for name, c in pieces:
        print(name, 'DMG unique tiles', C.tile_count(c), 'lot cells only', C.tile_count(c, (4, 7, 11, 8)))
    args = [sys.executable, C.ROOT + '/tools/dev/contact_sheet.py', OUT + '/milkbar_sheet5.png', '--scale', '1', '--cols', '2',
            '--title', 'milk bar round 4e in the A5 layout: alone (DMG, Color x3), then in the A5 map around it (DMG, Color x3)']
    subprocess.run(args + [f'{l}={p}' for l, p in items + wide], check=True)


if __name__ == '__main__':
    main()
