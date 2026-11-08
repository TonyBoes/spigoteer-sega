"""A whole range typed as ONE skyline (runs of columns, see mtn_kit.runs; a run may carry a label, the column where it ends), with a face rule per summit: ink along
the skyline, lit rock (1) left of each summit's crease, shaded rock (2) right of it down to the saddle, the next summit's left slope lit again.  Typed by me: the
skyline, each summit (label, saddle label, crease runs, optional snowcap edge), gullies, the light rim rows.  The helper turns the runs into pixels (ink = the same
skyline rule as mtn_kit.peak)."""
import sys

import mtn_kit as M


def massif(c, yf, x0, y0, segs, summits, foot_ink="33333323", gullies=(), lit=1, shade=2, verbose=True):
    labs, clean, x = {}, [], x0
    for sg in segs:
        x += sg[0]
        clean.append((sg[0], sg[1]))
        if len(sg) > 2:
            labs[sg[2]] = x - 1
    top = M.runs(x0, y0, clean)
    if verbose:
        print({k: (v, top[v]) for k, v in labs.items()}, 'ends at', x - 1, file=sys.stderr)

    def X(v):
        return labs[v] if isinstance(v, str) else v
    xs = sorted(top)
    ink = set()
    for x in xs:
        t = top[x]
        nb = [top.get(x - 1, yf), top.get(x + 1, yf)]
        for y in range(t, min(max(t, max(nb) - 1), yf) + 1):
            ink.add((x, y))
    creases = [(X(s["x"]), X(s.get("saddle", 10 ** 6)), M.path(X(s["x"]), top[X(s["x"])], s.get("crease", [(80, 0)]))) for s in summits]

    def face(x, y):
        for (ax, sad, cx) in creases:
            if ax <= x <= sad:
                return shade if x >= cx.get(y, cx[max(cx)]) else lit
        return lit
    for x in xs:
        for y in range(top[x], yf + 1):
            c.px[y][x] = "3" if (x, y) in ink else str(face(x, y))
    for s, (ax, sad, cx) in zip(summits, creases):
        ya = top[ax]
        for y in range(ya + 1, ya + 1 + s.get("ink_crease_rows", 0)):
            if y in cx and c.px[y][cx[y]] != "3":
                c.px[y][cx[y]] = "3"
        if s.get("cap"):
            lab, dx, cy, csegs = s["cap"]
            capb = M.runs(X(lab) + dx, cy, csegs)
            for x in sorted(capb):
                if x not in top or capb[x] < top[x]:
                    continue
                for y in range(top[x], capb[x]):
                    if (x, y) not in ink:
                        c.px[y][x] = "0" if face(x, y) == lit else str(lit)
                if (x, capb[x]) not in ink and capb[x] <= yf:
                    c.px[capb[x]][x] = str(shade) if face(x, capb[x]) == lit else "3"
        rim = s.get("rim", 0)
        for x in xs:
            y = top[x] + 1
            if rim and ya <= top[x] < ya + rim and abs(x - ax) < 40 and y <= yf and face(x, y) == lit and c.px[y][x] == str(lit):
                c.px[y][x] = "0"
    for g in gullies:                                    # (x, y, runs, value, width): a typed path, w columns wide
        for y, x in M.path(*g[:2], g[2]).items():
            for k in range(g[4] if len(g) > 4 else 1):
                if c.px[y][x + k] not in ("3", "0"):
                    c.px[y][x + k] = g[3]
    if foot_ink:
        for x in xs:
            if top[x] < yf:
                c.px[yf][x] = foot_ink[x % len(foot_ink)]
    return top, labs
