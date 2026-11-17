"""The credits' owner scene pages as data for the engine (CRSCENE=1, tools/gen_credits.py): the art, the palettes and the sprites are the artist's round 6
(tools/credits_scenes/, from docs/dev/concepts/credits_scenes_2026-11-13 on branch worktree-agent-aa21f868f71a0344f); this module only CONVERTS them.

scene(v, cgb) -> dict:
  cells[13][20]   the picture's cells (160 x 104): None (the page, blank) | ('t', 8x8 shade grid, palette) | ('f', shade, palette)
  pals            the BG palettes (<= 8 wanted; slot 0 is the venue's stage palette: the page, the band and the name use it): lists of 4 hex (None: unused)
  objs            the owner's edge sprites as 8 x 16 objects: dict(x, y, top, bot, obp, pal) (x, y in the picture's px; top / bot: 8x8 idx grids, bot None)
  opals           the OBJ palettes: lists of 3 hex (idx 1-3)
  stage           the stage palette's hex list (the band: colour 2; the ink: colour `ink`)
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
import os
ART = os.environ.get("CRART", "18")
sys.path.insert(0, str(HERE / {"7": "credits_scenes", "8": "credits_scenes8"}.get(ART, "credits_scenes18")))      # (the owner-approved round 18 is the default; CRART=8 builds round 8, CRART=7 round 7, kept)
sys.path.insert(0, str(HERE))
from scenes_lib import q5, hexrgb, PAGE_BG   # noqa: E402
import scenes_f as F                         # noqa: E402

KEYS = [v.key for v in F.VENUES]
BX, BY, BW, BH = F.BX, F.BY, F.BW, F.BH


def _pack(maps):
    pals = []
    for m in sorted(set(tuple(sorted(m.items())) for m in maps), key=lambda t: (-len(t), t)):
        m = dict(m)
        for p in pals:
            if all(p.get(s, h) == h for s, h in m.items()):
                p.update(m)
                break
        else:
            pals.append(dict(m))
    return pals


def _ne(g):
    return g is not None and any(any(r) for r in g)


def _spread(objs):
    """The hardware shows 10 sprites a line and an 8 x 16 object covers 16 lines: an object with one half empty can sit that half up or down
    (its pixels do not move). Choose the placements with the fewest lines over 10 (then the lowest peak); no pixel is touched."""
    import random
    opts = []
    for o in objs:
        t, b = _ne(o["top"]), _ne(o["bot"])
        if t and not b:
            opts.append([(o["y"], 0), (o["y"] - 8, 1)])
        elif b and not t:
            opts.append([(o["y"], 0), (o["y"] + 8, 2)])
        else:
            opts.append([(o["y"], 0)])

    def cost(ch):
        n = [0] * 260
        for op, c in zip(opts, ch):
            for y in range(op[c][0], op[c][0] + 16):
                n[y] += 1
        return (sum(max(0, c - 10) for c in n), max(n))
    ch = [0] * len(opts)
    best = cost(ch)
    rng = random.Random(7)
    for _ in range(4000):
        i = rng.randrange(len(opts))
        if len(opts[i]) < 2:
            continue
        c2 = ch[:]
        c2[i] ^= 1
        c = cost(c2)
        if c <= best:
            ch, best = c2, c
    blank = [[0] * 8 for _ in range(8)]
    out = []
    for o, op, c in zip(objs, opts, ch):
        o = dict(o)
        y, kind = op[c]
        if kind == 1:                                   # the top half's pixels in the object's lower half
            o["top"], o["bot"] = blank, o["top"]
        elif kind == 2:                                 # the lower half's pixels in the upper half
            o["top"], o["bot"] = o["bot"], None
        o["y"] = y
        out.append(o)
    return out


def _repack(cells, maps, stage):
    """More than 8 BG palettes by the greedy shade-for-shade packing: pack the cells again by their colours (exact search), the stage palette first with its colours where they are; a cell's shades
    and pixels are renumbered to its palette's indexes (the same colours). -> the palettes as {index: colour}; cells / maps are updated in place"""
    import sys as _s
    _s.setrecursionlimit(10000)
    def lum(h):
        r_, g_, b_ = (int(h[k:k + 2], 16) for k in (1, 3, 5))
        return 3 * r_ + 6 * g_ + b_
    ink = 0 if lum(stage[0]) >= lum(stage[1]) else 1
    base = {frozenset(m.values()) for m in maps.values()}
    bins = []
    calls = [0]

    def dfs(sets, k):
        calls[0] += 1
        if calls[0] > 60000000:
            return False
        if k == len(sets):
            return True
        f = sets[k]
        for bn in bins:
            add = [x for x in f if x not in bn]
            if len(bn) + len(add) <= 4:
                bn.extend(add)
                if dfs(sets, k + 1):
                    return True
                del bn[len(bn) - len(add):]
        if len(bins) < nbmax[0]:
            bins.append(list(f))
            if dfs(sets, k + 1):
                return True
            bins.pop()
        return False
    nbmax = [8]
    banded = True
    for extra in ({frozenset([stage[2]])}, set()):         # (the band colour in a palette of the page; if the art alone fills the eight, the band takes the nearest colour a palette has)
        allsets = base | extra
        sets = [f for f in allsets if not any(f < g_ for g_ in allsets)]
        sets.sort(key=lambda f: (-len(f), sorted(f)))
        found = False
        for nbmax[0] in range(4, 9):             # (iterative deepening: the fewest palettes first prunes the search)
            del bins[:]
            calls[0] = 0
            if dfs(sets, 0):
                found = True
                break
        if found:
            break
        banded = False
    else:
        raise SystemExit(f"the page cells do not pack into 8 BG palettes: {len(sets)} colour sets, {len({c for f in sets for c in f})} colours, stage {stage}")
    if banded:
        i0 = next(i for i, b_ in enumerate(bins) if stage[2] in b_)
    else:
        def dist(c):
            return sum((x - y) ** 2 for x, y in zip(hexrgb(c), hexrgb(stage[2])))
        i0 = min(range(len(bins)), key=lambda i: min(dist(c) for c in bins[i]))
        near = min(bins[i0], key=dist)
        print("CRSCENE: the band colour", stage[2], "has no palette entry (the art fills the eight palettes): the band takes", near)
        bins[i0] = [near if c == near else c for c in bins[i0]]
        stage = list(stage)
        stage[2] = near
        if stage[ink] == near:
            stage[ink] = None
    bins.insert(0, bins.pop(i0))                  # (palette 0: the band colour at 2, the ink at its index, the rest the art's)
    arr = [None] * 4
    arr[2] = stage[2]
    if stage[ink] is not None and stage[ink] in bins[0] and stage[ink] != stage[2]:
        arr[ink] = stage[ink]
    for col in bins[0]:
        if col not in arr:
            arr[arr.index(None)] = col
    bins[0] = arr
    for (cx, cy), m in list(maps.items()):
        f = set(m.values())
        bn = next(b for b in bins if f <= set(b))
        mp = {sh: bn.index(col) for sh, col in m.items()}
        mm, grid = cells[cy][cx]
        grid[:] = [[mp[x] for x in r_] for r_ in grid]
        newm = {mp[sh]: col for sh, col in m.items()}
        mm.clear()
        mm.update(newm)
        maps[(cx, cy)] = mm
    return [{i: c for i, c in enumerate(b) if c is not None} for b in bins]


OBJ_PERFORMERS = {"bistro": [1]}       # performers drawn as OBJ sprites, not BG art: Bistro's would need 9 BG palettes, the hardware has 8


def scene(v, cgb):
    if ART == "18":                                    # (round 18: its toggles and the Teahouse / Zoo palette slot changes hold while the page is built)
        import scenes_final
        with scenes_final.configured(v.key) as cfg:
            return _scene(v, cgb, cfg.get("limits"))
    return _scene(v, cgb, None)


def _scene(v, cgb, limits):
    import copy
    from scenes_e import perf_sprite
    spr = OBJ_PERFORMERS.get(v.key, [])
    r = F.build(v, limits)
    vb = copy.copy(v)
    vb.perf = [p for i, p in enumerate(v.perf) if i not in spr]
    page = F.bg_with_perf(r, vb, cgb)
    stage = [q5(h) for h in v.pal["stage_a"]]
    cells, maps = [], {}
    for cy in range(13):
        row = []
        for cx in range(20):
            m, grid = {}, [[0] * 8 for _ in range(8)]
            for y in range(8):
                for x in range(8):
                    s, h = page.px[cy * 8 + y][cx * 8 + x]
                    h = q5(h)
                    if cgb and m.get(s, h) != h:          # (a cell with two colours on one shade, round 18 Zoo's kept owner cell: the second colour takes a shade the cell does not use, its pixels follow)
                        s2 = next((k for k, c in m.items() if c == h), None)
                        if s2 is None:
                            free = [k for k in range(4) if k not in m]
                            if not free:
                                raise SystemExit(f"{v.key}: cell ({cx},{cy}): more than four colours")
                            s2 = free[0]
                        s = s2
                    m.setdefault(s, h)
                    grid[y][x] = s
            if set(m.items()) == {(3, q5(PAGE_BG))} and not (BX <= cx < BX + BW and BY <= cy < BY + BH):
                row.append(None)
            else:
                row.append([m, grid])
                maps[(cx, cy)] = m
        cells.append(row)
    repacked = False
    pals = _pack(list(maps.values()))
    if cgb and len(pals) > 8 - (0 if any(all(p.get(s_) in (None, stage[s_]) for s_ in range(4)) and sum(1 for s_ in range(4) if p.get(s_) == stage[s_]) >= 3 for p in pals) else 1):
        pals = _repack(cells, maps, stage)
        repacked = True
    # slot 0: the stage palette (the page, the band, the name): the palette that holds it, else a new one
    k0 = 0 if repacked else next((i for i, p in enumerate(pals) if all(p.get(s) in (None, stage[s]) for s in range(4)) and sum(1 for s in range(4) if p.get(s) == stage[s]) >= 3), None)
    if k0 is None:
        pals.append({s: stage[s] for s in range(4)})
        k0 = len(pals) - 1
    for s in range(4):
        pals[k0].setdefault(s, stage[s])
    pals.insert(0, pals.pop(k0))
    out = []
    for cy in range(13):
        row = []
        for cx in range(20):
            c = cells[cy][cx]
            if c is None:
                row.append(None)
                continue
            m, grid = c
            pi = next(i for i, p in enumerate(pals) if all(p.get(s, h) == h for s, h in m.items()))
            flat = {s for rr in grid for s in rr}
            row.append(("f", flat.pop(), pi) if len(flat) == 1 else ("t", grid, pi))
        out.append(row)
    objs = [dict(x=(BX + o["cx"]) * 8, y=(BY + o["cy"]) * 8, top=o["top"]["grid"], bot=o["bot"]["grid"] if o["bot"] else None, obp=o["obp"], pal=o["pal"]) for o in r["objs"]]
    opals = [[(h if h else None) for h in p] for p in r["opals"]]
    for i in spr:                                       # a performer as OBJ: columns of 8 x 16 objects, its three colours one OBJ palette, OBP1 on the DMG (idx 1-3 = shades 1-3)
        fr, cols = perf_sprite(v, v.perf[i], cgb)
        opals.append([q5(c) for c in cols])
        for c in range(len(fr[0]) // 8):
            for r0 in (0, 16):
                grid = [[("-+#".index(fr[r0 + y][c * 8 + x]) + 1) if (r0 + y < 24 and fr[r0 + y][c * 8 + x] != ".") else 0 for x in range(8)] for y in range(16)]
                top, bot = grid[:8], grid[8:]
                if any(any(rw) for rw in top + bot):
                    objs.append(dict(x=(BX * 8) + v.perf[i][0] + c * 8, y=BY * 8 + 16 + r0, top=top, bot=bot if any(any(rw) for rw in bot) else None, obp=1, pal=len(opals) - 1))
    objs = _spread(objs)
    objs.sort(key=lambda o: (o["y"], o["x"]))                    # the objects in the order they enter the screen (the engine's OAM slots follow from the number: credits.c cr_pslot)
    return dict(cells=out, pals=[[p.get(s) for s in range(4)] for p in pals], objs=objs, opals=opals, stage=stage, r=r, page=page)


if __name__ == "__main__":
    for v in F.VENUES:
        for cgb in (False, True):
            d = scene(v, cgb)
            nt = sum(1 for row in d["cells"] for c in row if c and c[0] == "t")
            nf = sum(1 for row in d["cells"] for c in row if c and c[0] == "f")
            lines = [0] * 144
            for o in d["objs"]:
                for y in range(o["y"], o["y"] + 16):
                    lines[y] += 1
            print(v.key, "cgb" if cgb else "dmg", "tiles", nt, "flat", nf, "pals", len(d["pals"]), "objs", len(d["objs"]), "line max", max(lines), "opals", len(d["opals"]))
