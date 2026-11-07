"""Typing helpers for the mountain proposals.  What is typed by me, per peak: the skyline (a list of (columns, rise per column) runs, left foot to apex to right
foot), the crease between the lit and the shaded face (a list of (rows, columns moved per row) runs), the snowcap's lower edge (a list of runs), and any gully
(a path of runs).  The helpers only turn those runs into pixels: ink along the skyline, lit face (1) left of the crease, shaded face (2) right of it, dashes every
8 rows on the 8 px grid, a light rim on the lit edge.  Values 0 sand / snow, 1 lit rock, 2 shaded rock, 3 ink (the venue's palette)."""


def runs(x0, y0, segs):
    """x -> y of the skyline: each (n, d) is n columns, each moving y by d (an int, or a list used round and round)"""
    out, x, y = {}, x0, y0
    for n, d in segs:
        for k in range(n):
            y += d[k % len(d)] if isinstance(d, (list, tuple)) else d
            out[x] = y
            x += 1
    return out


def path(x0, y0, segs):
    """a downward path: each (n, d) is n rows, each moving x by d (int or list); returns {y: x} starting at row y0 (x0 on that row)"""
    out, x, y = {}, x0, y0
    out[y] = x
    for n, d in segs:
        for k in range(n):
            y += 1
            x += d[k % len(d)] if isinstance(d, (list, tuple)) else d
            out[y] = x
    return out


def peak(c, yf, left, apex, right, crease, rim_rows=0, cap=None, dash_rows=(), ink_crease_rows=0, shade_dash=False, dashes=(), gullies=(), foot_ink=True, lit=1, shade=2, x_clip=None):
    """left = (x of the left foot, y of its first column, runs), apex = (x, y), right = runs after the apex; the skyline must reach yf at both feet.
    crease = (x at the apex row, runs); cap = (rows below the apex for the snowcap's top, runs of the cap's lower edge as (n, d) from the left) or None."""
    xl, yl, lsegs = left
    top = runs(xl, yl, lsegs)
    xa, ya = apex
    assert xl + len(top) == xa, f"left runs end at x {xl + len(top)}, apex at {xa}"
    top[xa] = ya
    top.update(runs(xa + 1, ya, right))
    cx = path(crease[0], ya, crease[1])
    import sys
    print(f'peak apex {xa},{ya}: left end y {top[xa-1]} (want {ya+1 or ya}), right foot x {max(top)} y {top[max(top)]} (want >= {yf})', file=sys.stderr)
    ink = {}
    xs = sorted(top)
    for x in xs:
        t = top[x]
        nb = [top.get(x - 1, yf), top.get(x + 1, yf)]
        end = max(t, max(nb) - 1)
        for y in range(t, min(end, yf) + 1):
            ink[(x, y)] = True
    capb = {}
    if cap:
        cx0 = cap[0]
        capb = runs(cx0, cap[1], cap[2])
    for x in xs:
        if x_clip and not (x_clip[0] <= x < x_clip[1]):
            continue
        for y in range(top[x], yf + 1):
            if (x, y) in ink:
                v = "3"
            else:
                cxx = cx.get(y, cx[max(cx)])
                if x < cxx:
                    v = str(lit)
                    if y % 8 in dash_rows and x % 8 < 5 and y > top[x] + 2:
                        v = str(shade)
                else:
                    v = str(shade)
                    if shade_dash and y % 8 in dash_rows and x % 8 < 4 and y > top[x] + 2:
                        v = "3"
            c.px[y][x] = v
    # the crease, inked for its first rows
    for y in range(ya + 1, ya + 1 + ink_crease_rows):
        x = cx.get(y)
        if x is not None and (not x_clip or x_clip[0] <= x < x_clip[1]) and c.px[y][x] != "3" and (x, y) not in ink:
            c.px[y][x] = "3"
    if cap:
        for x in sorted(capb):
            if x_clip and not (x_clip[0] <= x < x_clip[1]):
                continue
            for y in range(top.get(x, 99), capb[x]):
                if (x, y) in ink:
                    continue
                cxx = cx.get(y, cx[max(cx)])
                c.px[y][x] = "0" if x < cxx else str(lit)
            if x in top and capb[x] >= top[x] and (x, capb[x]) not in ink:
                c.px[capb[x]][x] = str(shade) if x < cx.get(capb[x], cx[max(cx)]) else "3"
    for x in xs:                                         # the light rim just under the skyline on the lit face, for the first rim_rows rows below the apex
        y = top[x] + 1
        if rim_rows and top[x] < ya + rim_rows and y <= yf and x < cx.get(y, cx[max(cx)]) and c.px[y][x] == str(lit) and (not x_clip or x_clip[0] <= x < x_clip[1]):
            c.px[y][x] = "0"
    for (y, x, n, v) in dashes:                          # hand-placed strata: a row, a first column, a length, a value; only over rock (1 or 2), never over ink
        for xx in range(x, x + n):
            if c.px[y][xx] in "12" and (not x_clip or x_clip[0] <= xx < x_clip[1]):
                c.px[y][xx] = str(v)
    for g in gullies:                                    # (x, y, runs, value, width): a typed path, w columns wide
        for y, x in path(*g[:2], g[2]).items():
            for k in range(g[4] if len(g) > 4 else 1):
                if (not x_clip or x_clip[0] <= x + k < x_clip[1]) and c.px[y][x + k] != "3":
                    c.px[y][x + k] = g[3] if len(g) > 3 else "3"
    if foot_ink:                                         # foot_ink: a typed string of values used round and round along the foot row (e.g. '3333332')
        pat = foot_ink if isinstance(foot_ink, str) else "3"
        for x in xs:
            if x_clip and not (x_clip[0] <= x < x_clip[1]):
                continue
            if top[x] < yf:
                c.px[yf][x] = pat[x % len(pat)]
    return top
