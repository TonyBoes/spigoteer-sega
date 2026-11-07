#!/usr/bin/env python3
"""Measures one layout and draws it.   python3 -I eval_layout.py NAME [--out DIR]     (NAME = lay_today, lay_A, lay_B, ...)

Prints: map size, scenery that does not fit, unique tiles, the worst 21 x 19 window (all windows and path windows only), new tiles per scroll step
(the counter of the DMG kit proposal, ported), the Color palettes per window, the loop length, how many camera positions on the route show two or
more venues.  Writes DIR/NAME_cgb.png, NAME_dmg.png (the whole map) and NAME_*_route.png (with the route and the stop numbers drawn over it).
Read-only apart from the pictures."""
import json
import os
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
name = sys.argv[1]
out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else ROOT / "out"
os.environ["SMAP_LAYOUT"] = name
sys.path.insert(0, str(HERE / "src"))
sys.path.append(str(ROOT / "tools" / "smap_world"))
import numpy as np  # noqa: E402
import pal as PAL  # noqa: E402
import world2 as W  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

CW, CH = W.CW, W.CH
wd, wc = W.WORLD_DMG, W.WORLD
res = {"layout": name, "cells": CW * CH, "size": [CW, CH], "bad_decor": [list(map(str, b)) for b in wc.bad], "bad_decor_dmg": [list(map(str, b)) for b in wd.bad]}

# ---- tiles (DMG, state 10, no fog) ------------------------------------------------------------------------------------------------------
cells = {(x, y): bytes(wd.px[y * 8 + j][x * 8 + i] for j in range(8) for i in range(8)) for y in range(CH) for x in range(CW)}
ids = {}
g = np.zeros((CH, CW), int)
for y in range(CH):
    for x in range(CW):
        g[y, x] = ids.setdefault(cells[(x, y)], len(ids))
res["unique_tiles"] = len(ids)
res["unique_once"] = sum(1 for v in Counter(cells.values()).values() if v == 1)


def win_max(ww, wh, step=1):
    best, at = 0, None
    for y0 in range(0, CH - wh + 1, step):
        for x0 in range(0, CW - ww + 1, step):
            n = len(np.unique(g[y0:y0 + wh, x0:x0 + ww]))
            if n > best:
                best, at = n, (x0, y0)
    return best, at


res["worst_21x19"], res["worst_21x19_at"] = win_max(21, 19)
res["worst_22x20"], res["worst_22x20_at"] = win_max(22, 20)
best, at = 0, None
for y0 in range(CH - 19):
    for x0 in range(CW - 21):
        c = int(np.bincount(g[y0:y0 + 20, x0:x0 + 22].ravel()).max())
        if c > best:
            best, at = c, (x0, y0)
res["max_uses_22x20"], res["max_uses_at"] = best, at
ww, wh = 22, 20
for label, axis in (("col", "x"), ("row", "y")):
    cnt = []
    if axis == "x":
        for y0 in range(CH - wh + 1):
            for x0 in range(CW - ww):
                win = set(np.unique(g[y0:y0 + wh, x0:x0 + ww]))
                cnt.append(len(set(np.unique(g[y0:y0 + wh, x0 + ww])) - win))
    else:
        for y0 in range(CH - wh):
            for x0 in range(CW - ww + 1):
                win = set(np.unique(g[y0:y0 + wh, x0:x0 + ww]))
                cnt.append(len(set(np.unique(g[y0 + wh, x0:x0 + ww])) - win))
    cnt = np.array(cnt)
    res[f"new_per_{label}_step"] = {"mean": round(float(cnt.mean()), 2), "p95": int(np.percentile(cnt, 95)), "max": int(cnt.max()), "ge5": int((cnt >= 5).sum()), "of": len(cnt)}

# ---- the route: legs, loop length, the windows the camera can show --------------------------------------------------------------------
stops = W.STOPS
legs = W.LEGS


def plen(pts):
    return sum(abs(b[0] - a[0]) + abs(b[1] - a[1]) for a, b in zip(pts, pts[1:]))


order = W.ORDER
nb = {}
for (a, b), pts in legs.items():
    nb.setdefault(a, {})[b] = plen(pts)
    nb.setdefault(b, {})[a] = plen(pts)


def dist(a, b):
    import heapq
    d, h = {a: 0}, [(0, a)]
    while h:
        k, u = heapq.heappop(h)
        if u == b:
            return k
        if k > d[u]:
            continue
        for v, w in nb[u].items():
            if k + w < d.get(v, 1 << 30):
                d[v] = k + w
                heapq.heappush(h, (k + w, v))
    return None


loop = sum(dist(order[i], order[(i + 1) % 10]) for i in range(10))
res["loop_px"] = loop
res["loop_cells"] = round(loop / 8)
res["loop_seconds_at_3px"] = round(loop / 3 / 60, 1)
res["legs"] = {f"{a}-{b}": round(plen(p) / 8) for (a, b), p in legs.items()}
res["total_road_cells"] = len(wc.roads)
# stops on one road with no turning back: count legs where the walk reverses direction on a segment (backtrack along the same road)
back = 0
steps = []
for i in range(10):
    a, b = order[i], order[(i + 1) % 10]
    # shortest path nodes
    import heapq
    prev, d, h = {}, {a: 0}, [(0, a)]
    while h:
        k, u = heapq.heappop(h)
        if u == b:
            break
        if k > d[u]:
            continue
        for v, wgt in nb[u].items():
            if k + wgt < d.get(v, 1 << 30):
                d[v] = k + wgt
                prev[v] = u
                heapq.heappush(h, (k + wgt, v))
    path = [b]
    while path[-1] != a:
        path.append(prev[path[-1]])
    path.reverse()
    steps.append(path)
res["loop_paths"] = [" > ".join(p) for p in steps]
res["loop_stops_passed_through"] = sum(len(p) - 2 for p in steps)           # stops walked through that are not the chapter's own (detours)


def cam(fx, fy):
    return min(max(fx - 80, 0), CW * 8 - 160), min(max(fy - 84, 0), CH * 8 - 144)


def leg_pts(a, b):
    p = W.NEIGH[a][b]
    pts = [p[0]]
    for (x0, y0), (x1, y1) in zip(p, p[1:]):
        n = max(abs(x1 - x0), abs(y1 - y0), 1)
        for k in range(0, n + 1, 3):
            pts.append((x0 + (x1 - x0) * k // n, y0 + (y1 - y0) * k // n))
    return pts


campos = set()
for (a, b) in legs:
    for fx, fy in leg_pts(a, b):
        campos.add(cam(fx, fy))
for s in stops.values():
    campos.add(cam(*s))
vcells = {n: [(x, y) for y in range(r[1], r[3] + 1) for x in range(r[0], r[2] + 1) if wc.kind[y][x] == n] for n, r in wc.venue_rect.items()}
two = 0
three = 0
worstp, atp = 0, None
for (cx, cy) in campos:
    x0, y0 = cx >> 3, cy >> 3
    x1, y1 = min(x0 + 20, CW - 1), min(y0 + 18, CH - 1)
    vis = [n for n, cl in vcells.items() if sum(1 for (x, y) in cl if x0 <= x <= x1 and y0 <= y <= y1) >= 30]
    two += len(vis) >= 2
    three += len(vis) >= 3
    n = len(np.unique(g[y0:y1 + 1, x0:x1 + 1]))
    if n > worstp:
        worstp, atp = n, (x0, y0)
res["route_views"] = len(campos)
res["route_views_two_venues"] = two
res["route_views_three_venues"] = three
res["worst_view_on_route"] = worstp
res["worst_view_on_route_at"] = atp

# ---- junctions and dead ends of the road network (centre lines of the legs) ---------------------------------------------------------------
H, V = [], []
for pts in legs.values():
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if y0 == y1:
            H.append((y0, min(x0, x1), max(x0, x1)))
        else:
            V.append((x0, min(y0, y1), max(y0, y1)))
poi = {(x, y) for (y, a, b) in H for x in (a, b)} | {(x, y0) for (x, a, b) in V for y0 in (a, b)}
poi |= {(x, y) for (y, a, b) in H for (x, c, d) in V if a <= x <= b and c <= y <= d}


def dirs(x, y):
    n = 0
    n += any(yy == y and a <= x < b for (yy, a, b) in H)
    n += any(yy == y and a < x <= b for (yy, a, b) in H)
    n += any(xx == x and a <= y < b for (xx, a, b) in V)
    n += any(xx == x and a < y <= b for (xx, a, b) in V)
    return n


res["junctions"] = sorted((p, dirs(*p)) for p in poi if dirs(*p) >= 3)
res["dead_ends"] = sorted(p for p in poi if dirs(*p) == 1)
res["crossroads"] = [p for p, d in res["junctions"] if d >= 4]
print("junctions", [(tuple(p), d) for p, d in res["junctions"]], "dead ends", res["dead_ends"])
# ---- the stretches: tiles along each leg (a build-time route plan loads ahead along one stretch at a time) -----------------------------------------
stretch = {}
for (a, b) in legs:
    seen, mx = set(), 0
    for fx, fy in leg_pts(a, b):
        cx, cy = cam(fx, fy)
        x0, y0 = max((cx >> 3) - 1, 0), max((cy >> 3) - 1, 0)
        x1, y1 = min(((cx + 159) >> 3) + 1, CW - 1), min(((cy + 143) >> 3) + 1, CH - 1)
        ts = set(np.unique(g[y0:y1 + 1, x0:x1 + 1]).tolist())
        seen |= ts
        mx = max(mx, len(ts))
    stretch[f"{a}-{b}"] = (len(seen), mx, round(plen(legs[(a, b)]) / 8))
res["stretch"] = stretch                                   # leg: (tiles seen along it, busiest view with the line ahead, length in cells)
res["stretch_union_max"] = max(v[0] for v in stretch.values())
res["stretch_view_max"] = max(v[1] for v in stretch.values())
res["stretch_mean_union"] = round(sum(v[0] for v in stretch.values()) / len(stretch), 1)
res["stretch_len_max"] = max(v[2] for v in stretch.values())
res["stretch_len_mean"] = round(sum(v[2] for v in stretch.values()) / len(stretch), 1)
res["stretch_over_pool"] = sum(1 for v in stretch.values() if v[0] > 176)
# ---- the D-pad: the button a stop's exit answers to (the generator: the side the next stop lies on) against the way Sal first walks ----------------------------
mism, tot = 0, 0
for a in W.NEIGH:
    for b in W.NEIGH[a]:
        dx, dy = stops[b][0] - stops[a][0], stops[b][1] - stops[a][1]
        d = ("R" if dx > 0 else "L") if abs(dx) >= abs(dy) else ("D" if dy > 0 else "U")
        tot += 1
        mism += d != W.exit_dir(a, b)
res["dpad_mismatch"], res["dpad_exits"] = mism, tot
res["max_waypoints"] = max(len(p) for p in legs.values())
print("dpad mismatches", mism, "of", tot, "exits; legs", len(legs), "max waypoints", res["max_waypoints"])
# ---- Color palettes per window ----------------------------------------------------------------------------------------------------------
pg = np.zeros((CH, CW), int)
pid = {}
for y in range(CH):
    for x in range(CW):
        pg[y, x] = pid.setdefault(wc.pal[y][x], len(pid))
best = 0
for y0 in range(CH - 18):
    for x0 in range(CW - 20):
        best = max(best, len(np.unique(pg[y0:y0 + 19, x0:x0 + 21])))
res["palettes_21x19_state10"] = best
(Path(out) / f"{name}.json").write_text(json.dumps(res, indent=1, default=str))
if "--full" in sys.argv:
    print(json.dumps({k: v for k, v in res.items() if k not in ("legs", "loop_paths", "bad_decor", "bad_decor_dmg")}, default=str))
r = res
print("SUMMARY %s size %dx%d cells %d | tiles %d | worst21x19 %d (22x20 %d) route-worst %d | col %.2f/%d row %.2f/%d | loop %d cells %.1fs | views2 %d/%d | flat %d@%s | pal %d | bad %d | dropped %d" % (
    name, CW, CH, r["cells"], r["unique_tiles"], r["worst_21x19"], r["worst_22x20"], r["worst_view_on_route"], r["new_per_col_step"]["mean"], r["new_per_col_step"]["p95"],
    r["new_per_row_step"]["mean"], r["new_per_row_step"]["p95"], r["loop_cells"], r["loop_seconds_at_3px"], r["route_views_two_venues"], r["route_views"],
    r["max_uses_22x20"], r["max_uses_at"], r["palettes_21x19_state10"], len(r["bad_decor"]), len(getattr(W.lay, "DROPPED", []))))
print("bad decor", len(res["bad_decor"]), res["bad_decor"][:6])
print("legs", res["legs"])
print("loop", res["loop_paths"])

# ---- pictures ---------------------------------------------------------------------------------------------------------------------------------


def render(w, cgb):
    im = Image.new("RGB", (CW * 8, CH * 8))
    px = im.load()
    for y in range(CH):
        for x in range(CW):
            cols = PAL.get(w.pal[y][x])
            for j in range(8):
                for i in range(8):
                    v = w.px[y * 8 + j][x * 8 + i]
                    px[x * 8 + i, y * 8 + j] = tuple(cols[v]) if cgb else (PAL.DMG_SHADE[v],) * 3
    return im


def route(im, scale):
    from PIL import ImageFont
    font = ImageFont.load_default(size=15)
    big = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
    d = ImageDraw.Draw(big)
    for (a, b), pts in legs.items():
        chord = a == "town" and name not in ("lay_A", "lay_A2", "lay_A3") or b == "town" and name not in ("lay_A", "lay_A2", "lay_A3")
        col = (255, 0, 160) if not chord else (0, 140, 255)
        pp = [(x * scale, (y - 4) * scale) for x, y in pts]
        d.line(pp, fill=(0, 0, 0), width=scale * 3 + 2)
        d.line(pp, fill=col, width=scale * 3)
    # loop direction: a small arrow head on the first straight run of every ring leg, in chapter order (a leg goes from chapter i to i + 1)
    ring = {(order[i], order[(i + 1) % 10]) for i in range(10)}
    def arrow(p, q):
        import math
        (x0, y0), (x1, y1) = p, q
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        ang = math.atan2(y1 - y0, x1 - x0)
        pts3 = [(mx + 11 * math.cos(ang), my + 11 * math.sin(ang)), (mx + 11 * math.cos(ang + 2.5), my + 11 * math.sin(ang + 2.5)),
                (mx + 11 * math.cos(ang - 2.5), my + 11 * math.sin(ang - 2.5))]
        d.polygon(pts3, fill=(255, 255, 255), outline=(0, 0, 0))
    for (a, b), pts in legs.items():
        fw = None
        if (a, b) in ring:
            seq = pts
        elif (b, a) in ring:
            seq = pts[::-1]
        else:
            continue
        # the longest segment of the leg carries the arrow
        segs = list(zip(seq, seq[1:]))
        p, q = max(segs, key=lambda s: abs(s[1][0] - s[0][0]) + abs(s[1][1] - s[0][1]))
        arrow((p[0] * scale, (p[1] - 4) * scale), (q[0] * scale, (q[1] - 4) * scale))
    for n, (x, y) in stops.items():
        lab = "T" if n == "town" else str(order.index(n) + 1)
        cx, cy = x * scale, (y - 4) * scale
        d.ellipse((cx - 12, cy - 12, cx + 12, cy + 12), fill=(255, 255, 255), outline=(0, 0, 0), width=2)
        d.text((cx, cy), lab, fill=(0, 0, 0), font=font, anchor="mm")
    return big


for model, cgb in (("cgb", True), ("dmg", False)):
    im = render(wc if cgb else wd, cgb)
    im.save(Path(out) / f"{name}_{model}.png")
    route(im, 2).save(Path(out) / f"{name}_{model}_route.png")
