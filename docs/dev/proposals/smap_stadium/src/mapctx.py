"""The A5 map (SMAP_LAYOUT=lay_A5, SMAP_LOG=v1, scratch copy in ../../smap_layout_a5/src: run its mk_src.py and mk_a5.py first) with the APPROVED stadium pasted at its A5 slot,
cell (1, 1), every cell, exactly as the animation import pastes it (docs/dev/proposals/smap_anim/mapctx.py + r4dump.py: stadium park_s2 final 2 with the wavy flag, pasted
at (1, 1), mode 'all', palette names from the piece, the PARK palette taken from the piece's own table because the A5 table has no PARK).
Optional: a module with an `edit(px, pal)` hook (my hand-typed edge, ground and connection edits) is applied after the paste.  Read-only otherwise."""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
os.environ["SMAP_LAYOUT"] = "lay_A5"
os.environ["SMAP_FOG"] = "none"
os.environ["SMAP_LOG"] = "v1"
sys.path.insert(0, str(ROOT / "docs/dev/proposals/smap_layout_a5/src"))
sys.path.append(str(ROOT / "tools/smap_world"))
sys.path.append(str(HERE))
import decor  # noqa: E402,F401
import lay_A5 as lay  # noqa: E402
lay.VENUES = dict(lay.VENUES, stadium=("anim_stub", lay.VENUES["stadium"][1]))      # the 16 x 10 placeholder box becomes a one-cell stand-in, as in the animation import
import pal as PAL  # noqa: E402   (the A5 scratch copies first: common.py would otherwise pull today's tools/smap_world ones)
import world2 as W  # noqa: E402
import common as C  # noqa: E402  (the stadium's own common.py: ROOT, tile helpers)
import park_s2 as PS  # noqa: E402

CW, CH = W.CW, W.CH
AT = (1, 1)


def paste(world, rows_of, pals_of, at=AT):
    for (i, j), (t, p) in rows_of.items():
        cx, cy = at[0] + i, at[1] + j
        for y in range(8):
            for x in range(8):
                world.px[cy * 8 + y][cx * 8 + x] = int(t[y][x])
        world.pal[cy][cx] = p


def stadium_cells(piece=None):
    c = (piece or PS).build()
    return {k: (t, C.W.MERGE.get(p, p)) for k, (t, p) in C.cells(c).items()}


BLANK = tuple(["00000000"] * 8)


def apply(piece=None, edit=None, drop_blank=False):
    """paste the piece at AT; drop_blank=True leaves the map's own ground in every all-index-0 cell of the piece (it is the free ground tile there)"""
    cells = stadium_cells(piece)
    for w in (W.WORLD, W.WORLD_DMG):
        for (i, j), (t, p) in cells.items():
            if drop_blank and tuple(t) == BLANK:
                continue
            cx, cy = AT[0] + i, AT[1] + j
            for y in range(8):
                for x in range(8):
                    w.px[cy * 8 + y][cx * 8 + x] = int(t[y][x])
            w.pal[cy][cx] = p
    if edit:
        edit(W)
    return cells


def render(world, cgb, box=None):
    """PIL image of the world (or the cell box (x0, y0, x1, y1) of it)"""
    from PIL import Image
    x0, y0, x1, y1 = box or (0, 0, CW, CH)
    im = Image.new("RGB", ((x1 - x0) * 8, (y1 - y0) * 8))
    for cy in range(y0, y1):
        for cx in range(x0, x1):
            cols = PAL.get(world.pal[cy][cx]) if cgb else None
            for y in range(8):
                for x in range(8):
                    v = world.px[cy * 8 + y][cx * 8 + x]
                    im.putpixel(((cx - x0) * 8 + x, (cy - y0) * 8 + y), tuple(cols[v]) if cols else (PAL.DMG_SHADE[v],) * 3)
    return im
