"""Map Atlas: the map pictures and the overlay layers (1024 x 1120, twice the map's pixels so the path lines stay readable on a phone)."""
import colorsys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import static as S

SC = 2
G = S.G
W = S.W

BANDS_TILES = [(130, "#9ecae1", "Up to 130"), (150, "#4292c6", "131 to 150"), (165, "#f0a000", "151 to 165"), (176, "#e02020", "166 to 176"), (999, "#8a00c2", "Over 176, off the paths")]
BANDS_PALS = [(5, "#9ecae1", "5 or fewer"), (6, "#4292c6", "6"), (7, "#f0a000", "7"), (99, "#e02020", "8")]
BANDS_SHARE = [(1, "#d6249f", "1 cell, unique"), (2, "#f0a000", "2 cells"), (8, "#4292c6", "3 to 8 cells"), (9999, None, "9 or more cells")]
TWIN = "#d6249f"
HIT = {3: ("#e02020", "Late frame"), 2: ("#f0a000", "Near the guard"), 1: ("#4292c6", "Camera wait"), 4: ("#8a00c2", "Drain late")}


def rgba(h, a=255):
    return (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16), a)


def band(v, bands):
    for lim, col, _ in bands:
        if v <= lim:
            return col
    return bands[-1][1]


def categorical(n):
    """n well-separated colours (hue steps with alternating lightness)"""
    out = []
    for i in range(n):
        h = (i * 0.381966) % 1.0
        r, g, b = colorsys.hls_to_rgb(h, 0.5 if i % 2 else 0.4, 0.85)
        out.append("#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255)))
    return out


def base_images(st):
    w = G.state_world(W.WORLD, 11)
    wd = G.state_world(W.WORLD_DMG, 11)
    px = np.array(w.px, dtype=np.uint8)
    pxd = np.array(wd.px, dtype=np.uint8)
    pal = np.kron(st.pal, np.ones((8, 8), dtype=np.int32))
    lut = np.array([[tuple(c) for c in cols] for cols in st.rgb], dtype=np.uint8)          # (23, 4, 3)
    color = lut[pal, px]
    dmg = np.array([[W.DMG_SHADE[v]] * 3 for v in range(4)], dtype=np.uint8)[pxd]
    return Image.fromarray(color).resize((S.CW * 8 * SC, S.CH * 8 * SC), Image.NEAREST), Image.fromarray(dmg).resize((S.CW * 8 * SC, S.CH * 8 * SC), Image.NEAREST)


def cell_layer(fn, alpha=150):
    """fn(x, y) -> hex colour or None per cell"""
    a = np.zeros((S.CH, S.CW, 4), dtype=np.uint8)
    for y in range(S.CH):
        for x in range(S.CW):
            c = fn(x, y)
            if c:
                a[y, x] = rgba(c, alpha)
    return Image.fromarray(a).resize((S.CW * 8 * SC, S.CH * 8 * SC), Image.NEAREST)


def path_layer(st, colour_of, base=None, width=3):
    """every leg's pixels as a thick line, coloured per sample, on a white outline"""
    im = base.copy() if base else Image.new("RGBA", (S.CW * 8 * SC, S.CH * 8 * SC), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r = width * SC
    for pas in (0, 1):
        for smp in st.leg_samples:
            for fx, fy, v in smp:
                x, y = fx * SC, fy * SC
                if pas == 0:
                    d.ellipse([x - r - 2, y - r - 2, x + r + 2, y + r + 2], fill=(255, 255, 255, 255))
                else:
                    d.ellipse([x - r, y - r, x + r, y + r], fill=rgba(colour_of(v)))
    return im


def hit_layer(hits):
    im = Image.new("RGBA", (S.CW * 8 * SC, S.CH * 8 * SC), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for kind in (1, 4, 2, 3):                      # the worst on top
        col = rgba(HIT[kind][0])
        for fx, fy, k, *_ in hits:
            if k == kind:
                x, y = fx * SC, fy * SC
                rr = 9 if kind == 3 else 7
                d.ellipse([x - rr - 2, y - rr - 2, x + rr + 2, y + rr + 2], fill=(255, 255, 255, 255))
                d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=col)
    return im


def make_all(st, dyn, out):
    out = Path(out)
    img = out / "img"
    img.mkdir(parents=True, exist_ok=True)
    c, d = base_images(st)
    c.save(img / "map_color.png", optimize=True)
    d.save(img / "map_dmg.png", optimize=True)
    files = {}
    pos = st.pos
    files["dmg_path"] = path_layer(st, lambda v: band(v["tiles_pad"], BANDS_TILES), cell_layer(lambda x, y: None))
    files["dmg_all"] = path_layer(st, lambda v: band(v["tiles_pad"], BANDS_TILES), cell_layer(lambda x, y: band(pos[(x, y)]["tiles_pad"], BANDS_TILES), 130))
    files["pals"] = path_layer(st, lambda v: band(len(v["pals_view"]), BANDS_PALS), cell_layer(lambda x, y: band(len(pos[(x, y)]["pals_view"]), BANDS_PALS), 130))
    cols = categorical(len(st.names))
    files["palcell"] = cell_layer(lambda x, y: cols[int(st.pal[y, x])], 170)
    pcols = categorical(len(st.piece_names))
    files["piece"] = cell_layer(lambda x, y: pcols[int(st.piece[y, x])], 170)
    files["share_dmg"] = cell_layer(lambda x, y: band(int(st.shD[y, x]), BANDS_SHARE), 175)
    files["share_cgb"] = cell_layer(lambda x, y: band(int(st.shC[y, x]), BANDS_SHARE), 175)
    files["twin"] = cell_layer(lambda x, y: TWIN if st.twin_cell[y, x] else None, 175)
    if dyn:
        files["hit_dmg"] = hit_layer(dyn["dmg"]["hits"])
        files["hit_cgb"] = hit_layer(dyn["cgb"]["hits"])
    for k, im in files.items():
        im.save(img / f"ov_{k}.png", optimize=True)
    return dict(pal_cols=cols, piece_cols=pcols, files=sorted(files))
