"""Round spotlights. Edge tiles are flattened tiles drawn from the venue's wall (or floor) colours: lit / dark (R1, R2), lit / 2 mids / dark (R3).
Counted: unique edge tile images under X and Y flip (attribute bits 5, 6)."""
import numpy as np
from PIL import Image
import mock
from mock import STAGE_Y0, STAGE_Y1, dim_img, to15, from15, performers

CX = None


def centres(perf):
    return [(a + b + 1) * 4.0 for a, b in perf]          # pixel x of the boundary between a performer's two tile columns


def coverage(cx, cy, rx, ry, cell_x, cell_y, aa):
    """coverage 0..1 of the 8x8 cell (cell_x, cell_y in tiles) by the ellipse; 4x4 subsamples if aa else the pixel centre."""
    n = 4 if aa else 1
    c = np.zeros((8, 8))
    for sy in range(n):
        for sx in range(n):
            xs = cell_x * 8 + (np.arange(8) + (sx + 0.5) / n)[None, :]
            ys = cell_y * 8 + (np.arange(8) + (sy + 0.5) / n)[:, None]
            c += (((xs - cx) / rx) ** 2 + ((ys - cy) / ry) ** 2 <= 1.0)
    return c / (n * n)


def levels(cov, aa):
    if not aa:
        return (cov > 0.5).astype(int) * 3                      # 0 dark .. 3 lit
    return np.select([cov < 0.17, cov < 0.5, cov < 0.83], [0, 1, 2], 3)


def canon(lv, cls):
    cands = []
    for f in (lv, lv[:, ::-1], lv[::-1], lv[::-1, ::-1]):
        cands.append(f.tobytes())
    return (min(cands), cls)


def build(perf, rows, cy, rx, ry, aa):
    """-> dict (cx_tile, cy_tile) -> level array for the edge cells, set of lit cells, edge-tile unique set"""
    lit, edge, uniq = set(), {}, set()
    for c in centres(perf):
        for ty in rows:
            for tx in range(int((c - rx) // 8), int((c + rx) // 8) + 1):
                if not (0 <= tx < 20):
                    continue
                cov = coverage(c, cy, rx, ry, tx, ty, aa)
                if cov.min() == 1.0 and (levels(cov, aa) == 3).all():
                    lit.add((tx, ty))
                elif cov.max() > 0:
                    lv = levels(cov, aa)
                    if (lv == 3).all():
                        lit.add((tx, ty))
                    elif (lv == 0).all():
                        pass
                    else:
                        edge[(tx, ty)] = lv
                        uniq.add(canon(lv, "floor" if ty == 4 else "wall"))
    return lit, edge, uniq


def render(f, plate, lit, edge, aa, k=mock.DIM):
    res = mock.compose(f, plate, lambda cx, cy: (cx, cy) in lit, k=k)
    bg = (f == plate).all(-1)
    cols, cnt = np.unique(plate[STAGE_Y0:STAGE_Y1 - 8].reshape(-1, 3), axis=0, return_counts=True)
    wall = cols[cnt.argmax()]
    cols, cnt = np.unique(plate[32:40].reshape(-1, 3), axis=0, return_counts=True)
    floor = cols[cnt.argmax()]
    for (tx, ty), lv in edge.items():
        base = floor if ty == 4 else wall
        d = dim_img(base[None, None, :], k)[0, 0]
        pal = [d] + [from15(np.rint(to15(d[None, None]) + (to15(base[None, None]) - to15(d[None, None])) * k))[0, 0] for k in (1 / 3., 2 / 3.)] + [base]
        ys, xs = slice(ty * 8, ty * 8 + 8), slice(tx * 8, tx * 8 + 8)
        cell = res[ys, xs]
        m = bg[ys, xs]
        for yy in range(8):
            for xx in range(8):
                if m[yy, xx]:
                    cell[yy, xx] = pal[lv[yy, xx]]
    return res


SHAPES = {
    # name: rows, centre y, rx, ry, aa
    "r1": ((1, 2, 3, 4), 24.0, 24.0, 16.0, False),     # full-height oval
    "r2": ((3, 4), 32.0, 24.0, 8.0, False),             # floor pool: rows 3-4, the oval's long axis on the stage edge
    "r3": ((1, 2, 3), 20.0, 20.0, 12.0, True),          # soft oval (4 shades) over rows 1-3 only
}

def main():
    OUT = "out/spotlight"
    for v in ("saloon", "space"):
        d = np.load(f"{OUT}/cap_{v}.npz")
        plate, frames = d["plate"], d["frames"]
        perf = performers(frames[20:], plate)
        for name, (rows, cy, rx, ry, aa) in SHAPES.items():
            lit, edge, uniq = build(perf, rows, cy, rx, ry, aa)
            n_shape = len({u[0] for u in uniq})
            print(v, name, "lit cells", len(lit), "edge cells", len(edge), "unique edge tiles", len(uniq), "(shapes", n_shape, ")")
            imgs = [render(f, plate, lit, edge, aa) for f in frames]
            Image.fromarray(imgs[30]).save(f"{OUT}/round_{v}_{name}.png")
            pil = [Image.fromarray(x).resize((480, 432), Image.NEAREST) for x in imgs[::2]]
            pil[0].save(f"{OUT}/round_{v}_{name}.gif", save_all=True, append_images=pil[1:], duration=33, loop=0)
            # cell colour check (BG pixels only)
            bg = (frames[30] == plate).all(-1)
            r = imgs[30]
            bad = 0
            for ty in range(1, 5):
                for tx in range(20):
                    ys, xs = slice(ty * 8, ty * 8 + 8), slice(tx * 8, tx * 8 + 8)
                    if len({tuple(p) for p in r[ys, xs][bg[ys, xs]]}) > 4:
                        bad += 1
            print("   cells over 4 colours:", bad)


TINTS = [np.array([0.62, 0.30, 0.55]), np.array([0.30, 0.45, 0.70]), np.array([0.65, 0.48, 0.25])]


def sweep_main():
    OUT = "out/spotlight"
    for v in ("saloon", "space"):
        d = np.load(f"{OUT}/cap_{v}.npz")
        plate, frames = d["plate"], d["frames"]
        perf = performers(frames[20:], plate)
        per = {}
        for name in ("r1", "r2"):
            rows, cy, rx, ry, aa = SHAPES[name]
            per[name] = [build([p], rows, cy, rx, ry, aa)[:2] for p in perf]
        looks = {}
        for name in ("r1", "r2"):
            for tint in (False, True):
                key = f"round_{name}_sweep" + ("_wash" if tint else "")
                imgs = []
                for i, f in enumerate(frames):
                    beat = i // mock.BEAT
                    solo = beat % 3
                    on = {solo, (solo - 1) % 3}                     # the soloist and the last one: two ovals lit, one off, rotating
                    lit, edge = set(), {}
                    for j in on:
                        lit |= per[name][j][0]
                        edge.update(per[name][j][1])
                    k = TINTS[(beat // 2) % 3] if tint else mock.DIM
                    imgs.append(render(f, plate, lit, edge, False, k))
                looks[key] = imgs
        # Wash + Sweep on the plain rectangular pools (the owner's two favourites together)
        imgs = []
        for i, f in enumerate(frames):
            beat = i // mock.BEAT
            act = beat % 3
            extra = [1 if j == act else 0 for j in range(3)]
            sh = [(1 if (beat // 3) % 2 else 0) if j == act else 0 for j in range(3)]
            lit = mock.pool_cells(perf, [2, 4, 4, 6], extra, sh)
            imgs.append(mock.compose(f, plate, lambda cx, cy: (cx, cy) in lit, k=TINTS[(beat // 2) % 3]))
        looks["ws_pools"] = imgs
        for key, imgs in looks.items():
            Image.fromarray(imgs[30]).save(f"{OUT}/{key.replace('round_', 'round_' + v + '_') if key.startswith('round_') else 'round_' + v + '_' + key}.png")
            pil = [Image.fromarray(x).resize((480, 432), Image.NEAREST) for x in imgs[::2]]
            nm = key.replace('round_', 'round_' + v + '_') if key.startswith('round_') else 'round_' + v + '_' + key
            pil[0].save(f"{OUT}/{nm}.gif", save_all=True, append_images=pil[1:], duration=33, loop=0)
            print(nm)


if __name__ == "__main__":
    main()
    sweep_main()
