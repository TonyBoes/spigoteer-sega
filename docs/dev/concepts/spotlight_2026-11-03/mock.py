"""Spotlight mockups. Every colour a look paints is quantised to RGB15 (5 bits a channel); a tile cell's colours are checked
against the 4-colour limit of one BG palette entry; pools snap to the 8 px tile grid."""
import sys
import numpy as np
from PIL import Image

OUT = "out/spotlight"
BEAT = 12
STAGE_Y0, STAGE_Y1 = 8, 40            # text rows 1..4 (layout.h STAGE_FIRST_ROW..STAGE_LAST_ROW)

# dark = the stage's colours (as they sit in palette RAM, BRIGHT lift included) times a per-channel factor, then to 5 bits
DIM = np.array([0.40, 0.45, 0.62])


def q5(a):
    return (np.clip(np.rint(a / 8.0), 0, 31) * 8).astype(np.uint8)       # (screen RGB of a 5-bit value is ~ v*8.2; /8 keeps it close enough for a mock)


def to15(rgb):
    return np.rint(rgb / 255.0 * 31).astype(np.int32)


def from15(c):
    return np.rint(np.clip(c, 0, 31) / 31.0 * 255).astype(np.uint8)


def dim15(c, k=DIM):
    return np.floor(np.asarray(c, dtype=np.float64) * k).astype(np.int32)


def dim_img(img, k=DIM):
    return from15(dim15(to15(img), k))


def lift_img(img, f=1.18, add=1):
    c = to15(img)
    return from15(np.minimum(31, np.floor(c * f) + add))


def performers(frames, plate):
    """Tile column ranges of the three performers, from the pixels that differ from the show-less plate."""
    m = np.zeros((32, 160), bool)
    for f in frames:
        m |= (f[STAGE_Y0:STAGE_Y1] != plate[STAGE_Y0:STAGE_Y1]).any(-1)
    cols = np.where(m[:24].any(0))[0]
    groups = []
    for c in cols:
        if groups and c - groups[-1][1] <= 6:
            groups[-1][1] = c
        else:
            groups.append([c, c])
    return [(g[0] // 8, g[1] // 8) for g in groups]            # inclusive tile columns


def cell_ok(img, cx, cy):
    cell = img[cy * 8:cy * 8 + 8, cx * 8:cx * 8 + 8].reshape(-1, 3)
    return len({tuple(p) for p in cell}) <= 4


def compose(frame, plate, tile_lit, k=DIM, lift_dancers=False, tint=None):
    """tile_lit(cx, cy) -> bool (the tile keeps its lit palette). The stage's BG pixels (those equal to the plate) are dimmed or kept;
    the dancers' pixels (differ from the plate) stay, or are lifted."""
    res = frame.copy()
    bgmask = (frame == plate).all(-1)
    dim = dim_img(plate, k) if tint is None else tint
    for cy in range(1, 5):
        for cx in range(20):
            ys, xs = slice(cy * 8, cy * 8 + 8), slice(cx * 8, cx * 8 + 8)
            if not tile_lit(cx, cy):
                m = bgmask[ys, xs]
                res[ys, xs][m] = dim[ys, xs][m]
    if lift_dancers:
        dm = ~bgmask
        dm[:STAGE_Y0] = False
        dm[STAGE_Y1:] = False
        res[dm] = lift_img(frame)[dm]
    return res


# ---- the looks -------------------------------------------------------------------------------------------------------------------------
def look_dim(f, plate, step, perf):
    return compose(f, plate, lambda cx, cy: False)


def pool_cells(perf, widths, extra=None, shift=None):
    """Oval pool per performer: row cy (1..4) is widths[cy-1] tiles wide, centred on the performer's tile columns."""
    lit = set()
    for i, (a, b) in enumerate(perf):
        c2 = (a + b + 1) / 2.0                     # centre in tile units (edge between tiles a..b)
        for cy in range(1, 5):
            w = widths[cy - 1] + (extra[i] if extra else 0) * (2 if cy in (2, 3) else 0)
            x0 = int(round(c2 - w / 2.0)) + (shift[i] if shift else 0)
            for cx in range(x0, x0 + w):
                lit.add((cx, cy))
    return lit


def look_pools(f, plate, step, perf):
    lit = pool_cells(perf, [2, 4, 4, 6])
    return compose(f, plate, lambda cx, cy: (cx, cy) in lit, lift_dancers=False)


def look_pools_lift(f, plate, step, perf):
    lit = pool_cells(perf, [2, 4, 4, 6])
    return compose(f, plate, lambda cx, cy: (cx, cy) in lit, lift_dancers=True)


def look_sweep(f, plate, step, perf):
    """Pools on the beat: the beat's soloist has the wide pool, the others the tight one; the pools sway a tile left and right."""
    beat = step
    act = beat % 3
    extra = [1 if i == act else 0 for i in range(3)]
    sh = [(1 if (beat // 3) % 2 else 0) if i == act else 0 for i in range(3)]
    lit = pool_cells(perf, [2, 4, 4, 6], extra, sh)
    return compose(f, plate, lambda cx, cy: (cx, cy) in lit)


def look_cones(f, plate, step, perf):
    """A cone from the lamp (top of row 1) down to each performer: 4 px a side per text row; the cone's edge tiles are new flat
    tiles (lit wall / dark wall / rim, 3 colours: a third borrowed BG palette), the tiles inside it keep their lit palette."""
    res = compose(f, plate, lambda cx, cy: False)
    bgmask = (f == plate).all(-1)
    dimp = dim_img(plate)
    n_edge = 0
    for (a, b) in perf:
        cxm = (a + b + 1) * 4.0                          # centre x in pixels
        for y in range(STAGE_Y0, STAGE_Y1):
            half = 5 + (y - STAGE_Y0) * 0.36            # half width in px at this line (a 12 px lamp: 38 px at the floor)
            x0, x1 = int(round(cxm - half)), int(round(cxm + half))
            for x in range(max(x0, 0), min(x1, 160)):
                if bgmask[y, x]:
                    # interior tiles keep lit; the 1-tile band on each side (the edge tiles) is a flat 3-colour tile
                    res[y, x] = plate[y, x]
    # edge tiles: every 8x8 cell that the cone's side lines cross is flattened to {lit wall, dark wall, rim}
    lit_wall = {}
    cols, cnt = np.unique(plate[STAGE_Y0:STAGE_Y1].reshape(-1, 3), axis=0, return_counts=True)
    wall = cols[cnt.argmax()]                                     # the venue's wall colour: the flat tiles' lit colour
    for cy in range(1, 5):
        for cx in range(20):
            lit_wall[(cx, cy)] = wall
    for (a, b) in perf:
        cxm = (a + b + 1) * 4.0
        for cy in range(1, 5):
            for side in (-1, 1):
                for cx in set(int((cxm + side * (5 + (y - STAGE_Y0) * 0.36)) // 8) for y in range(cy * 8, cy * 8 + 8)):
                    if not (0 <= cx < 20):
                        continue
                    ys, xs = slice(cy * 8, cy * 8 + 8), slice(cx * 8, cx * 8 + 8)
                    bgm = bgmask[ys, xs]
                    lw = lit_wall[(cx, cy)]
                    dw = dim_img(lw[None, None, :])[0, 0]
                    rim = lift_img(lw[None, None, :], 1.0, 4)[0, 0]
                    cell = res[ys, xs]
                    for yy in range(8):
                        y = cy * 8 + yy
                        half = 5 + (y - STAGE_Y0) * 0.36
                        for xx in range(8):
                            x = cx * 8 + xx
                            d = abs(x + 0.5 - cxm)
                            if not bgm[yy, xx]:
                                continue
                            cell[yy, xx] = rim if abs(d - half) < 1.0 else (lw if d < half else dw)
                    n_edge += 1
    return res


def look_wash(f, plate, step, perf):
    """Dim and colour wash: the stage palettes written per beat (one tint of three), 2 palettes x 4 colours in the VBlank."""
    tints = [np.array([0.62, 0.30, 0.55]), np.array([0.30, 0.45, 0.70]), np.array([0.65, 0.48, 0.25])]
    k = tints[(step // 2) % 3]
    return compose(f, plate, lambda cx, cy: False, k=k)


LOOKS = [("today", lambda f, p, s, perf: f), ("dim", look_dim), ("pools", look_pools), ("pools_lift", look_pools_lift),
         ("cones", look_cones), ("sweep", look_sweep), ("wash", look_wash)]


def main():
    from tools_sheet import sheet
    pass


if __name__ == "__main__":
    pass
