#!/usr/bin/env python3
"""Before | after pictures of the four reuse options the owner asked to see (11-08), built from edited copies of the finished map (nothing in src/, assets/ or tests/ changes):

    A  cactus palette onto grass (Color)
    B  small town palettes merged: town4, town5, town1@z, town1@n into town1; bistro@g into bistro (Color)
    C  tree phase snap: pines, round trees, bushes at one pixel offset (DMG + Color; trees move up to 4 px)
    D  near twins up to 2 px merged (DMG + Color)

    python3 tools/artifacts/map_atlas/reuse_views.py        # writes out/sheet_A_B.png, sheet_C.png, sheet_D.png, sheet_all.png and prints the table (about 3 minutes)
"""
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reuse as R  # noqa: E402
import reuse_sheet as S  # noqa: E402

NAMES, W, OUT = R.NAMES, R.W, R.OUT
VIEWS = OUT / "reuse_views"
RED = (255, 40, 40)


def A(e):
    a, b = NAMES.index("cactus"), NAMES.index("grass")
    return R.merge_edit(e, a, b, R.palette_distance(a, b)[1])


B_MERGES = [("town4", "town1"), ("town5", "town1"), ("town1@z", "town1"), ("town1@n", "town1"), ("bistro@g", "bistro")]


def B(e):
    for x, y in B_MERGES:
        a, b = NAMES.index(x), NAMES.index(y)
        e = R.merge_edit(e, a, b, R.palette_distance(a, b)[1])
    return e


def C(e, base):
    fam = R.templates(e)
    names = ["PINE", "ROUND", "BUSH"]
    out, _ = R.best_snaps(e, base, fam, R.instances(e, fam, "C"), R.instances(e, fam, "D"), names)
    return out


def D(e):
    ec = R.near_simulate(e, "C", 2, True)[0]
    return R.near_simulate(ec, "D", 2, False)[0]


def changed_cells(e0, e1, which):
    """boolean (CH, CW): cells whose pixels (or, for Color, palette) differ"""
    a, b = (e0.C, e1.C) if which == "C" else (e0.D, e1.D)
    d = (a != b).reshape(R.CH, 8, R.CW, 8).any(axis=(1, 3))
    if which == "C":
        d |= e0.P != e1.P
    return d


def px_changed(e0, e1, which):
    a, b = (e0.C, e1.C) if which == "C" else (e0.D, e1.D)
    return (a != b).reshape(R.CH, 8, R.CW, 8).sum(axis=(1, 3))


def crop(e, which, box, scale=1, mark=None, ref=None):
    """box = (cx0, cy0, cx1, cy1) in cells; mark: highlight pixels that differ from ref (an Edit)"""
    cx0, cy0, cx1, cy1 = box
    im = S.render(e, which, (cx0 * 8, cy0 * 8, (cx1 - cx0 + 1) * 8, (cy1 - cy0 + 1) * 8))
    if mark:
        a = (e.C if which == "C" else e.D)[cy0 * 8:(cy1 + 1) * 8, cx0 * 8:(cx1 + 1) * 8]
        b = (ref.C if which == "C" else ref.D)[cy0 * 8:(cy1 + 1) * 8, cx0 * 8:(cx1 + 1) * 8]
        px = im.load()
        grey = Image.eval(im, lambda v: v // 3 + 60)
        im = grey
        px = im.load()
        ys, xs = np.nonzero(a != b)
        for y, x in zip(ys, xs):                                       # a yellow ring round each changed pixel, so a single dot can be found
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if 0 <= x + dx < im.width and 0 <= y + dy < im.height:
                        px[int(x + dx), int(y + dy)] = (255, 220, 40)
        for y, x in zip(ys, xs):
            px[int(x), int(y)] = RED
    return im.resize((im.width * scale, im.height * scale), Image.NEAREST) if scale > 1 else im


def box_around(cells, margin=1, maxw=18, maxh=11):
    """a (cx0, cy0, cx1, cy1) box around a set of (x, y) cells, at most maxw x maxh, clipped to the map"""
    xs, ys = [c[0] for c in cells], [c[1] for c in cells]
    x0, x1, y0, y1 = min(xs) - margin, max(xs) + margin, min(ys) - margin, max(ys) + margin
    if x1 - x0 + 1 > maxw:
        m = (x0 + x1) // 2
        x0, x1 = m - maxw // 2, m + maxw // 2 - 1
    if y1 - y0 + 1 > maxh:
        m = (y0 + y1) // 2
        y0, y1 = m - maxh // 2, m + maxh // 2 - 1
    x0, y0 = max(x0, 0), max(y0, 0)
    return x0, y0, min(x1, R.CW - 1), min(y1, R.CH - 1)


def components(mask, gap=2):
    """connected groups of True cells, neighbours within `gap` cells"""
    seen, out = set(), []
    pts = list(zip(*np.nonzero(mask)[::-1]))
    todo = set(pts)
    for p in pts:
        if p in seen:
            continue
        grp, st = [], [p]
        seen.add(p)
        while st:
            q = st.pop()
            grp.append(q)
            for dx in range(-gap, gap + 1):
                for dy in range(-gap, gap + 1):
                    n = (q[0] + dx, q[1] + dy)
                    if n in todo and n not in seen:
                        seen.add(n)
                        st.append(n)
        out.append(grp)
    return out


def sheet(name, panels, title):
    VIEWS.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(R.ROOT / "tools" / "dev" / "contact_sheet.py"), str(OUT / name), "--scale", "3", "--cols", "1", "--title", title] + [" =%s" % p for p in panels]
    subprocess.run(cmd, check=True)


def main():
    OUT.mkdir(exist_ok=True)
    e0 = R.Edit()
    base = R.Metrics(e0)
    eA, eB, eC, eD = A(e0), B(e0), C(e0, base), D(e0)
    eAll = A(B(D(eC)))
    scen = {"base": e0, "A cactus": eA, "B small town": eB, "C trees": eC, "D twins <=2px": eD, "A+B+C+D": eAll}
    table = []
    for k, e in scen.items():
        m = R.Metrics(e)
        table.append((k, m.tiles, m.ids, m.pad_max, m.w21_max, m.pal_at8))
        print("TABLE %-14s DMG %d  Color %d  padded %d  21x19 %d  8/8 windows %d" % table[-1])
    # ---- sheet A+B: every changed palette area, Color only
    eAB = A(B(e0))
    ch = changed_cells(e0, eAB, "C")
    panels = []
    for i, grp in enumerate(sorted(components(ch, 3), key=lambda g: -len(g))):
        bx = box_around(grp, 1, 18, 11)
        names = sorted({NAMES[e0.P[y, x]] for x, y in grp})
        tgt = {"cactus": "grass", "bistro@g": "bistro"}
        lab = "%d  %s" % (i + 1, ", ".join("%s to %s" % (n, tgt.get(n, "town1")) for n in names))
        z = max(1, min(4, 120 // ((bx[2] - bx[0] + 1) * 8)))
        panels.append(S.panel(lab, ["cells %d,%d to %d,%d: %d cells change palette" % (bx[0], bx[1], bx[2], bx[3], len(grp))],
                              [(S.row([crop(e0, "C", bx, z), crop(eAB, "C", bx, z)]), "COLOR  before | after")], "AB_%02d" % i))
    sheet("sheet_A_B.png", panels, "A + B: palette merges (%d spots)" % len(panels))
    # ---- sheet C: tree areas
    chc = changed_cells(e0, eC, "C") | changed_cells(e0, eC, "D")
    comps = sorted(components(chc, 3), key=lambda g: -len(g))
    panels = []
    for i, grp in enumerate(comps[:6]):
        bx = box_around(grp, 1, 16, 10)
        panels.append(S.panel("%d  trees moved" % (i + 1), ["cells %d,%d to %d,%d" % (bx[0], bx[1], bx[2], bx[3])],
                              [(S.row([crop(e0, "C", bx), crop(eC, "C", bx)]), "COLOR  before | after"), (S.row([crop(e0, "D", bx), crop(eC, "D", bx)]), "DMG  before | after")], "C_%02d" % i))
    sheet("sheet_C.png", panels, "C: tree offsets (%d areas moved, 6 shown)" % len(comps))
    # ---- sheet D: the most visible spots
    cat = R.categories(e0, R.instances(e0, R.templates(e0), "D"), base.dm)
    pc, pd_ = px_changed(e0, eD, "C"), px_changed(e0, eD, "D")
    wx, wy = 14, 10
    cand = []
    for y0 in range(0, R.CH - wy + 1, 3):
        for x0 in range(0, R.CW - wx + 1, 4):
            sc = int(pd_[y0:y0 + wy, x0:x0 + wx].sum()) * 3 + int(pc[y0:y0 + wy, x0:x0 + wx].sum() > 0) * int((pc[y0:y0 + wy, x0:x0 + wx] > 0).sum())
            sub = cat[y0:y0 + wy, x0:x0 + wx][(pd_[y0:y0 + wy, x0:x0 + wx] > 0) | (pc[y0:y0 + wy, x0:x0 + wx] > 0)]
            dom = max(set(sub.ravel()), key=list(sub.ravel()).count) if sub.size else ""
            cand.append((sc, x0, y0, str(dom).split(" ")[0]))
    cand.sort(reverse=True)
    picked, per = [], {}
    for sc, x0, y0, dom in cand:
        if len(picked) >= 8 or sc == 0:
            break
        if per.get(dom, 0) >= 2 or any(abs(x0 - p[1]) < wx and abs(y0 - p[2]) < wy for p in picked):
            continue
        per[dom] = per.get(dom, 0) + 1
        picked.append((sc, x0, y0, dom))
    panels = []
    for i, (sc, x0, y0, dom) in enumerate(picked):
        bx = (x0, y0, x0 + wx - 1, y0 + wy - 1)
        n_c, n_d = int(pc[y0:y0 + wy, x0:x0 + wx].sum()), int(pd_[y0:y0 + wy, x0:x0 + wx].sum())
        panels.append(S.panel("%d  %s" % (i + 1, dom), ["cells %d,%d to %d,%d: %d Color px, %d DMG px change" % (bx[0], bx[1], bx[2], bx[3], n_c, n_d)],
                              [(S.row([crop(e0, "C", bx), crop(eD, "C", bx), crop(eD, "C", bx, mark=True, ref=e0)]), "COLOR  before | after | changed"),
                               (S.row([crop(e0, "D", bx), crop(eD, "D", bx), crop(eD, "D", bx, mark=True, ref=e0)]), "DMG  before | after | changed")], "D_%02d" % i))
    sheet("sheet_D.png", panels, "D: near twins up to 2 px (8 spots)")
    # ---- sheet all: whole map, x2
    full = (0, 0, R.CW - 1, R.CH - 1)
    pan = []
    for which, lab in (("C", "COLOR"), ("D", "DMG")):
        for e, t in ((e0, "BEFORE"), (eAll, "AFTER  A+B+C+D")):
            im = crop(e, which, full, 2)
            pan.append(S.panel("%s  %s" % (lab, t), [], [(S.row([im]), "")], "ALL_%s_%s" % (which, t[:3])))
    VIEWS.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, str(R.ROOT / "tools" / "dev" / "contact_sheet.py"), str(OUT / "sheet_all.png"), "--scale", "1", "--cols", "1", "--title", "Whole map, before and after A+B+C+D"] + [" =%s" % p for p in pan], check=True)
    print("table rows", len(table))


if __name__ == "__main__":
    main()
