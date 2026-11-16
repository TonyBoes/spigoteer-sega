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
sys.path.insert(0, str(HERE / "credits_scenes"))
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


OBJ_PERFORMERS = {"bistro": [1]}       # performers drawn as OBJ sprites, not BG art: Bistro's would need 9 BG palettes, the hardware has 8


def scene(v, cgb):
    import copy
    from scenes_e import perf_sprite
    spr = OBJ_PERFORMERS.get(v.key, [])
    r = F.build(v)
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
                    grid[y][x] = s
                    if m.setdefault(s, q5(h)) != q5(h):
                        raise SystemExit(f"{v.key}: cell ({cx},{cy}): two colours on shade {s}")
            if set(m.items()) == {(3, q5(PAGE_BG))} and not (BX <= cx < BX + BW and BY <= cy < BY + BH):
                row.append(None)
            else:
                row.append([m, grid])
                maps[(cx, cy)] = m
        cells.append(row)
    pals = _pack(list(maps.values()))
    # slot 0: the stage palette (the page, the band, the name): the palette that holds it, else a new one
    k0 = next((i for i, p in enumerate(pals) if all(p.get(s) in (None, stage[s]) for s in range(4)) and sum(1 for s in range(4) if p.get(s) == stage[s]) >= 3), None)
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
