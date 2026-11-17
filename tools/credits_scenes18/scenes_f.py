"""Round 5 (owner, on round 4: "move the characters to the left... use sprites for the edges, so it can overlap background tiles without colour artifacting"):
all 10 venues, every owner on the LEFT of the 14 x 9 box (the portrait as drawn on the bottom edge), the room and the performers to the right.

Hardware model (what is mocked):
  * BG: room cells in the venue's own palettes (the game's attr files); a cell that holds ONLY owner pixels is a BG cell in the owner's palette; a cell that holds owner
    AND room pixels (an edge cell) is the ROOM's BG tile, and the owner's pixels in it are an OBJ sprite on top (colour 0 transparent, drawn above all BG).
  * OBJ, 8 x 16 mode (the credits' mode). A sprite's pixels are indices 1-3. DMG: idx -> shade through OBP0 (idx 1, 2, 3 = shades 0, 1, 2) or OBP1 (idx 1, 2, 3 =
    shades 1, 2, 3; the performers' mapping). An edge cell with shades inside {1,2,3} is one OBP1 sprite, inside {0,1,2} one OBP0 sprite, one that holds shade 0 AND shade 3
    is two sprites on the same spot (OBP0: shades 0-2, OBP1: shade 3). Colour 0 is never needed: shade 0 is an index 1 under OBP0. Color: each sprite's three colours are the
    owner's colours of those shades in that cell; sprites whose colours agree share an OBJ palette (greedy merge). The same tile data serves both machines.
  * Vertically adjacent sprites with the same OBP and palette are one 8 x 16 object; a lone cell is an object with a blank half.
  * The mock composites BG then OBJ and CHECKS that every owner pixel comes out with its own colour (Color) and shade (DMG).
"""
from scenes_lib import *
from scenes_e import (Venue, lines, owner_palettes, nearest, show_frames, perf_sprite, BX, BY, BW, BH)
from scenes_c import read_raw, backdrop_mask

UNDER = True
# Round 20 (Granny's heart tattoo): sprite pixels drawn over the BG, {venue: [(portrait x, y, hex)]}: OBP1 index 3 (DMG: shade 3, black; Color: the hex, her bandana red) in a sprite of its own
OVERLAYS = {}
OVERLAY_SHADE = {}
OVERLAY_COLOR_ONLY = set()      # venues whose overlays are Color-only sprites (the story's OBJ accents): not drawn on DMG
PAINT_ON = False         # round 10 (the owner's painting): frozen off, not part of the final set
# Round 13 (Kiki): the Zoo's lane cells that carry her outline / filled hair pockets use the zoo's own bar_b palette (BG slot of bar_b: colours #234e5c, #e8c880, #a05828 and the
# near-black #2c1808) instead of bar (whose darkest is the olive #384018): same tiles, same indices.
RING_PAL = {}
# Round 11 (Coach, the small gap under the brim tip, portrait pixels): the leftover wall pixels between the brim's dark line (rows 12-14) and the rail (row 16, which starts at x 38)
GAP = [(38, 14), (39, 14)] + [(x, 15) for x in range(38, 47)]
JUNEFILL = None           # round 11, June: None (round 9), "line" (the 3 wall pixels at x 16, rows 32-34 go dark) or "finger" (and the row 33 finger x 10-15)
GAPFILL = None            # None (round 9), "light" (the rail's light colour, palette colour 0) or "dark" (the brim's dark colour, palette colour 3)
# Round 10: the owner's own painting on Coach's round 9 crop (crop at 15,7 -> portrait pixels): the space under the brim tip is clean and light. (x, y, DMG shade); BG pixels
# only: shade 0 is colour 0 of the room cell's palette, shade 1 its colour 1.
PAINT = {"sports": [(32, 12, 0)] + [(x, 13, 0) for x in range(32, 41)] + [(41, 13, 1)] + [(x, 14, 0) for x in range(33, 42)] + [(x, 15, 0) for x in range(35, 38)] + [(38, 15, 1)]}
OBP_SHADE = {0: {1: 0, 2: 1, 3: 2}, 1: {1: 1, 2: 2, 3: 3}}      # idx -> DMG shade


def plan_cell(fcell, m):
    """the sprite layers of one edge cell: [(obp, idx grid, colour triple with None where unused)]"""
    S = set(m)
    if 0 in S and 3 in S:
        layers = [(0, lambda s: s <= 2), (1, lambda s: s == 3)]
    elif 0 in S:
        layers = [(0, lambda s: True)]
    else:
        layers = [(1, lambda s: True)]
    out = []
    for obp, sel in layers:
        inv = {sh: i for i, sh in OBP_SHADE[obp].items()}
        grid = [[0] * 8 for _ in range(8)]
        for (x, y), (s, h) in fcell.items():
            if sel(s):
                grid[y][x] = inv[s]
        used = {sh for (x, y), (sh, h) in fcell.items() if sel(sh)}
        tri = [m.get(OBP_SHADE[obp][i]) if OBP_SHADE[obp][i] in used else None for i in (1, 2, 3)]
        out.append((obp, grid, tri))
    return out


def finalize(sprites):
    """Color OBJ palettes (compatible triples merged) and the 8 x 16 objects (vertically adjacent sprites of one OBP and palette stacked)"""
    opals = []
    for sp in sprites:
        for i, pl in enumerate(opals):
            if all(a is None or b is None or a == b for a, b in zip(sp["tri"], pl)):
                opals[i] = [b if b is not None else a for a, b in zip(sp["tri"], pl)]
                sp["pal"] = i
                break
        else:
            opals.append(list(sp["tri"]))
            sp["pal"] = len(opals) - 1
    objs, taken = [], set()
    srt = sorted(range(len(sprites)), key=lambda i: (sprites[i]["cx"], sprites[i]["cy"]))
    for i in srt:
        if i in taken:
            continue
        a = sprites[i]
        taken.add(i)
        j = next((k for k in srt if k not in taken and sprites[k]["cx"] == a["cx"] and sprites[k]["cy"] == a["cy"] + 1 and sprites[k]["obp"] == a["obp"] and sprites[k]["pal"] == a["pal"]), None)
        if j is not None:
            taken.add(j)
        objs.append(dict(cx=a["cx"], cy=a["cy"], top=a, bot=sprites[j] if j is not None else None, obp=a["obp"], pal=a["pal"]))
    return objs, opals


def budget_ok(v, sprites, limits):
    objs, opals = finalize(sprites)
    # performers: the Color art is the wider (24 px: 3 columns), so plan with it
    lines = [0] * 72
    for o in objs:
        for y in range(o["cy"] * 8, min(72, o["cy"] * 8 + 16)):
            lines[y] += 1
    return (max(lines) <= limits["line"] and len(objs) <= limits["objs"] and len(opals) <= limits["pals"])


def build(v, limits=None):
    """Round 8: in an edge cell (owner + room pixels) the owner's OUTLINE pixels (the portrait's backdrop-coloured pixels that the mask keeps) go into the room's BG tile,
    in the room palette's colour nearest to the portrait's outline colour; the owner's other pixels are the sprite on top (so a sprite never carries the darkest shade
    unless the portrait has a second dark colour, and no cell needs two stacked sprites for that). limits None: every edge cell with sprite pixels is a sprite."""
    pals = owner_palettes(v.owner)
    key, rows = read_raw(v.owner)
    mask = backdrop_mask(rows)
    bgk = key[rows[0][0]]                                    # the outline / backdrop colour (shade, hex)
    fig = {(x, 16 + y): key[rows[y][x]] for y in range(56) for x in range(56) if not mask[y][x]}
    room = v.room_cells()
    cells = []
    for cy in range(BH):
        for cx in range(BW):
            fcell = {(x, y): fig[(cx * 8 + x, cy * 8 + y)] for y in range(8) for x in range(8) if (cx * 8 + x, cy * 8 + y) in fig}
            cells.append((cx, cy, fcell))
    edge = [(cx, cy, f) for cx, cy, f in cells if 0 < len(f) < 64]
    layers, outline, sprite_cells = {}, {}, []
    for cx, cy, f in edge:
        outline[(cx, cy)] = {pos for pos, f_ in f.items() if f_ == bgk}
        rest = {pos: f_ for pos, f_ in f.items() if f_ != bgk}
        if rest:
            m = {}
            for (s, h) in rest.values():
                if m.setdefault(s, h) != h:
                    raise SystemExit(f"{v.key}: edge cell ({cx},{cy}) two colours of shade {s}")
            layers[(cx, cy)] = (m, plan_cell(rest, m))
            sprite_cells.append((cx, cy, rest))
    ov_sprites = []
    overlay_px = set()
    ovl = [(ox, oy, ohex) for (ox, oy, ohex) in OVERLAYS.get(v.key, ()) if (ox, 16 + oy) in fig]       # (an overlay pixel outside the silhouette is dropped)
    for (ox, oy, ohex) in ovl:
        overlay_px.add((ox, 16 + oy))
    if v.key in OVERLAY_COLOR_ONLY:
        # Color-only accent sprites (the story's OBJ accents, e.g. Granny's red lips): per cell up to three colours, index by colour, not drawn on DMG
        cellpts = {}
        for (ox, oy, ohex) in ovl:
            cellpts.setdefault((ox // 8, (16 + oy) // 8), []).append((ox % 8, (16 + oy) % 8, ohex))
        for (ocx, ocy), pts in cellpts.items():
            hexes = list(dict.fromkeys(h for _, _, h in pts))
            assert len(hexes) <= 3, (v.key, ocx, ocy, hexes)
            g8 = [[0] * 8 for _ in range(8)]
            for (px_, py_, h) in pts:
                g8[py_][px_] = 1 + hexes.index(h)
            ov_sprites.append(dict(cx=ocx, cy=ocy, obp=0, grid=g8, tri=hexes + [None] * (3 - len(hexes)), color_only=True))
    else:
        byc = {}
        for (ox, oy, ohex) in ovl:
            byc.setdefault((ox // 8, (16 + oy) // 8, ohex), []).append((ox % 8, (16 + oy) % 8))
        osh = OVERLAY_SHADE.get(v.key, 3)                       # the DMG shade of the overlay: 0 = OBP0 idx 1; 1-3 = OBP1 idx 1-3
        oobp, oidx = (0, 1) if osh == 0 else (1, osh)
        for (ocx, ocy, ohex), pts in byc.items():
            g8 = [[0] * 8 for _ in range(8)]
            for (px_, py_) in pts:
                g8[py_][px_] = oidx
            tri = [None, None, None]
            tri[oidx - 1] = ohex
            ov_sprites.append(dict(cx=ocx, cy=ocy, obp=oobp, grid=g8, tri=tri))
    chosen, sprites = [], list(ov_sprites)       # (the overlay sprites count against the per-line / object / palette limits from the start)
    for cx, cy, f in sorted(sprite_cells, key=lambda e: len(e[2])):
        trial = sprites + [dict(cx=cx, cy=cy, obp=o, grid=g_, tri=list(t)) for o, g_, t in layers[(cx, cy)][1]]
        if limits is None or budget_ok(v, [dict(s) for s in trial], limits):
            sprites = trial
            chosen.append((cx, cy))
    page = Page(v.key, (3, PAGE_BG))
    bg_owner, fallback, diffs = [], [], []
    for cx, cy, fcell in cells:
        g, pn = room[(cx, cy)]
        full = len(fcell) == 64
        if full:                                             # entirely owner: a BG cell in the owner's palette
            bg_owner.append((cx, cy))
            for (x, y), f in fcell.items():
                page.px[(BY + cy) * 8 + y][(BX + cx) * 8 + x] = f
            continue
        if fcell and (cx, cy) not in chosen and (cx, cy) in layers:
            fallback.append((cx, cy))                        # (limits only: an edge cell left without its sprite)
            # that cell is a BG cell in the owner's palette (it keeps the owner's near-black): the room's few pixels in it take the nearest owner colour
            m = {}
            for (s_, h_) in fcell.values():
                m.setdefault(s_, h_)
            cands = [pp for pp in pals if all(pp.get(s_) == h_ for s_, h_ in m.items())]
            rc = {v.pal[pn][g[y][x]] for y in range(8) for x in range(8) if (x, y) not in fcell}
            pp = min(cands, key=lambda q: sum(sum((a - b) ** 2 for a, b in zip(hexrgb(nearest(h, q)[1]), hexrgb(h))) for h in rc)) if rc else cands[0]
            for y in range(8):
                for x in range(8):
                    page.px[(BY + cy) * 8 + y][(BX + cx) * 8 + x] = fcell[(x, y)] if (x, y) in fcell else nearest(v.pal[pn][g[y][x]], pp)
            continue
        if outline.get((cx, cy)):
            pn = RING_PAL.get(v.key, {}).get(pn, pn)           # round 13: a room cell that carries the owner's outline may use the venue's other palette with the near-black
        for y in range(8):
            for x in range(8):
                s = g[y][x]
                if v.dim and pn.startswith("stage"):
                    s = {0: 1, 1: 2, 2: 3, 3: 3}[s]
                px = (s, v.pal[pn][s])
                if (x, y) in outline.get((cx, cy), ()):      # the owner's outline pixel, in the room palette's nearest colour
                    near = min(range(4), key=lambda i: sum((a - b) ** 2 for a, b in zip(hexrgb(v.pal[pn][i]), hexrgb(bgk[1]))))
                    px = (near, v.pal[pn][near])
                    diffs.append(max(abs((a >> 3) - (b >> 3)) for a, b in zip(hexrgb(v.pal[pn][near]), hexrgb(bgk[1]))))
                page.px[(BY + cy) * 8 + y][(BX + cx) * 8 + x] = px
    # round 9 (rule: every south-facing ring pixel, i.e. its south neighbour is room): under every overhang the story portrait shows dark backdrop (brims, hat edges, hair, chins, shoulders): where the one pixel ring sits directly under the
    # figure (its north neighbour is a figure pixel) and the room starts below it, the next pixel down is the ring's colour too: a two pixel dark underside, in the
    # darkest colour of the room cell's palette (BG pixels, no sprite). Other edges keep the one pixel ring.
    under = set()
    if UNDER:
        for (x, y), f in fig.items():
            if f == bgk and (x, y + 1) not in fig and y + 1 < 72:
                under.add((x, y + 1))
        for (x, y) in under:
            cx, cy = x // 8, y // 8
            g, pn = room[(cx, cy)]
            if outline.get((cx, cy)):
                pn = RING_PAL.get(v.key, {}).get(pn, pn)
            near = min(range(4), key=lambda i: sum((a - b) ** 2 for a, b in zip(hexrgb(v.pal[pn][i]), hexrgb(bgk[1]))))
            page.px[(BY + cy) * 8 + y % 8][(BX + cx) * 8 + x % 8] = (near, v.pal[pn][near])
    gapchanged = []
    if GAPFILL and v.key == "sports":
        want = 0 if GAPFILL == "light" else 3
        targets = list(GAP)
        if GAPFILL == "dark15":
            # round 15: after the dark fill, every wall-blue pixel left under the brim (between the brim's dark line and the face or rail, forehead to tip: x 24-46, rows 11-15,
            # room pixels only) is the same dark
            for yy in range(11, 16):
                for xx in range(24, 47):
                    if (xx, 16 + yy) in fig and fig[(xx, 16 + yy)] != bgk:
                        continue
                    cx_, cy_ = xx // 8, (16 + yy) // 8
                    cur_ = page.px[(BY + cy_) * 8 + (16 + yy) % 8][(BX + cx_) * 8 + xx % 8]
                    if cur_[1] in ("#6080c0", "#283c78") and (xx, yy) not in targets:
                        targets.append((xx, yy))
        for (x, y) in targets:
            cx, cy = x // 8, (16 + y) // 8
            g, pn = room[(cx, cy)]
            cur = page.px[(BY + cy) * 8 + (16 + y) % 8][(BX + cx) * 8 + x % 8]
            new_px = (want, v.pal[pn][want])
            if cur != new_px:
                gapchanged.append((x, y, cur[1], new_px[1]))
                page.px[(BY + cy) * 8 + (16 + y) % 8][(BX + cx) * 8 + x % 8] = new_px
    junechanged = []
    if JUNEFILL and v.key == "lodge":
        targets = [(16, 32), (16, 33), (16, 34)] + ([(x, 33) for x in range(10, 16)] if JUNEFILL == "finger" else [])
        ref = page.px[(BY + (16 + 33) // 8) * 8 + (16 + 33) % 8][(BX + 17 // 8) * 8 + 17 % 8]        # the dark next to them (x 17, row 33)
        for (x, y) in targets:
            cx, cy = x // 8, (16 + y) // 8
            cur = page.px[(BY + cy) * 8 + (16 + y) % 8][(BX + cx) * 8 + x % 8]
            if cur != ref:
                junechanged.append((x, y, cur[1], ref[1]))
                page.px[(BY + cy) * 8 + (16 + y) % 8][(BX + cx) * 8 + x % 8] = ref
    painted, unpainted = [], []
    for (x, y, sh) in PAINT.get(v.key, ()) if PAINT_ON else ():
        cx, cy = x // 8, (16 + y) // 8
        g, pn = room[(cx, cy)]
        if (cx, cy) in bg_owner or ((x, 16 + y) in fig and fig[(x, 16 + y)] != bgk):
            unpainted.append((x, y))                        # an owner pixel (sprite) or an owner BG cell: not the room's to paint
            continue
        page.px[(BY + cy) * 8 + (16 + y) % 8][(BX + cx) * 8 + x % 8] = (sh, v.pal[pn][sh])
        painted.append((x, y, sh, pn))
    page.box = (BX, BY, BW, BH)
    objs, opals = finalize(sprites)
    return dict(page=page, fig=fig, overlay_px=overlay_px, under=under, gapchanged=gapchanged, junechanged=junechanged, painted=painted, unpainted=unpainted, sprites=sprites, objs=objs, opals=opals, edge=chosen, bg_owner=bg_owner, fallback=fallback, edge_total=len(edge), bgk=bgk,
                outline_cells=len(outline), outline_pixels=sum(len(x) for x in outline.values()), outline_diff_max=max(diffs) if diffs else 0,
                outline_diff_mean=(sum(diffs) / len(diffs)) if diffs else 0)


def perf_objs(v, cgb):
    """the performers as 8 x 16 objects: a column of 8 wide is 2 objects (24 rows -> 32 covered)"""
    out = []
    for spec in v.perf:
        fr, cols = perf_sprite(v, spec, cgb)
        for c in range(len(fr[0]) // 8):
            for r in (0, 16):
                out.append(dict(x=spec[0] + c * 8, y=16 + r, tri=cols))
    return out


def bg_with_perf(r, v, cgb):
    """the BG as the hardware holds it, the performers drawn into it as BG art (their own pixels and colours). A cell they touch gets one palette: the room's
    commonest colour there on the shade it has in the room, the performer's three colours on the other three shades (in order, light to dark); the cell's other room
    pixels take the nearest of those four colours. The DMG shades of the performer in that cell are those three shades (so they follow the room behind them)."""
    page = r["page"]
    px = [list(row) for row in page.px]
    figset = {(BX * 8 + a, BY * 8 + b) for a, b in r["fig"]}
    cellspec = {}
    for si, spec in enumerate(v.perf):
        fr, cols = perf_sprite(v, spec, cgb)
        for y in range(24):
            for x in range(len(fr[0])):
                ch = fr[y][x]
                if ch == ".":
                    continue
                gx, gy = BX * 8 + spec[0] + x, BY * 8 + 16 + y
                assert (gx, gy) not in figset, "performer overlaps the owner"
                key = (gx // 8, gy // 8)
                assert cellspec.setdefault(key, (si, cols))[0] == si, ("two performers share a cell", key)
                cellspec[key] = (si, cols)
    rec = {}
    from collections import Counter
    perf_pix = {}                      # per performer: {(gx, gy): idx}
    for si, spec in enumerate(v.perf):
        fr, cols = perf_sprite(v, spec, cgb)
        d_ = {}
        for y in range(24):
            for x in range(len(fr[0])):
                ch = fr[y][x]
                if ch != ".":
                    d_[(BX * 8 + spec[0] + x, BY * 8 + 16 + y)] = "-+#".index(ch)
        perf_pix[si] = (d_, cols)
    for si, (d_, cols) in perf_pix.items():
        cells = {(g[0] // 8, g[1] // 8) for g in d_}
        room = [(px[cy * 8 + y][cx * 8 + x]) for (cx, cy) in cells for y in range(8) for x in range(8) if (cx * 8 + x, cy * 8 + y) not in d_]
        dom = Counter(h for s_, h in room).most_common(1)[0][0]
        sr = next(s_ for s_, h in room if h == dom)
        free = [s_ for s_ in range(4) if s_ != sr]
        P = {sr: dom, free[0]: cols[0], free[1]: cols[1], free[2]: cols[2]}      # ONE palette for the whole performer
        for (cx, cy) in cells:
            for y in range(8):
                for x in range(8):
                    g = (cx * 8 + x, cy * 8 + y)
                    if g in d_:
                        px[g[1]][g[0]] = (free[d_[g]], cols[d_[g]])
                    else:
                        h = px[g[1]][g[0]][1]
                        px[g[1]][g[0]] = (sr, dom) if h == dom else min(P.items(), key=lambda kv: sum((a - b) ** 2 for a, b in zip(hexrgb(kv[1]), hexrgb(h))))
            rec[(cx, cy)] = P
    p2 = Page(page.name, (3, PAGE_BG))
    p2.px = px
    p2.box = page.box
    p2.perf_cells = rec
    return p2


def composite(r, v, cgb):
    """BG (with the performers), then OBJ (the owner's edge sprites, colour 0 transparent), the way the hardware does; asserts the owner comes out as drawn"""
    p2 = bg_with_perf(r, v, cgb)
    px = p2.px
    for sp in r["sprites"]:
        if sp.get("color_only") and not cgb:
            continue
        tri = r["opals"][sp["pal"]]
        for y in range(8):
            for x in range(8):
                i = sp["grid"][y][x]
                if i:
                    s = OBP_SHADE[sp["obp"]][i]
                    px[(BY + sp["cy"]) * 8 + y][(BX + sp["cx"]) * 8 + x] = (s, tri[i - 1])
    for (x, y), f in r["fig"].items():
        got = px[BY * 8 + y][BX * 8 + x]
        if (x, y) in r.get("overlay_px", ()):
            continue                                   # a tattoo pixel: the sprite draws it red (Color) / black (DMG)
        if f == r["bgk"] and (x // 8, y // 8) not in r["bg_owner"]:
            continue                                   # an outline pixel in an edge cell: the room palette's nearest colour (round 8)
        assert got == f, (v.key, x, y, got, f)        # shade (DMG) and colour (Color) of every other owner pixel
    return p2


def obj_stats(r, v, cgb):
    lines_cnt = [0] * 72
    n = 0
    for o in r["objs"]:
        n += 1
        for y in range(o["cy"] * 8, min(72, o["cy"] * 8 + 16)):
            lines_cnt[y] += 1
    own_max = max(lines_cnt)
    tiles, flips = set(), set()

    def add(g):
        t = tuple(tuple(r_) for r_ in g)
        if any(any(r_) for r_ in t):
            tiles.add(t)
            c = []
            for fx in (0, 1):
                for fy in (0, 1):
                    u = [rr[::-1] if fx else rr for rr in (t[::-1] if fy else t)]
                    c.append(tuple(tuple(rr) for rr in u))
            flips.add(min(c))
    for o in r["objs"]:
        add(o["top"]["grid"])
        if o["bot"]:
            add(o["bot"]["grid"])
    owner_tiles = (len(tiles), len(flips))
    pal = [list(p) for p in r["opals"]]
    return dict(objects=n, owner_objects=len(r["objs"]), sprites=len(r["sprites"]), per_line_max=max(lines_cnt), owner_per_line_max=own_max,
                obj_tiles=len(tiles), obj_tiles_flip_merged=len(flips), owner_obj_tiles=owner_tiles[0], obj_palettes_color=len(pal), owner_obj_palettes=len(r["opals"]),
                cells_two_sprites=sum(1 for c in r["edge"] if sum(1 for s in r["sprites"] if (s["cx"], s["cy"]) == c) == 2),
                per_line=lines_cnt)


# rooms: owner always on the left (box cols 0-6); sc = 14 stage columns, hand-picked; bar group (keg etc) at box cols 11-13; performers at x 60 / 84 (clear of the owner)
BARR = {11: 17, 12: 18, 13: 19}
P2 = lambda a, b, c, d, e, f: [(60, a, b, c), (88, d, e, f)]
VENUES = [
    Venue("saloon", "THE SALOON", "sadie", "SADIE", "L", [0, 2, 3, 4, 5, 6, 17, 7, 8, 9, 10, 11, 12, 18], BARR, P2(0, 0, 0, 0, 0, 1)),
    Venue("sports", "THE STADIUM", "coach", "COACH", "L", [0, 1, 2, 3, 4, 10, 15, 5, 6, 7, 8, 9, 11, 12], BARR, P2(0, 0, 0, 0, 0, 0)),
    Venue("lodge", "THE LUMBER LODGE", "june", "JUNE", "L", [0, 1, 2, 3, 4, 9, 10, 5, 6, 7, 8, 12, 13, 17], BARR, P2(0, 0, 0, 0, 11, 0)),
    Venue("bistro", "THE BISTRO", "colby", "COLBY", "L", [0, 1, 2, 3, 4, 5, 6, 11, 12, 13, 14, 15, 16, 17], BARR, P2(0, 0, 0, 4, 4, 1)),
    Venue("igloo", "THE IGLOO", "aurora", "AURORA", "L", [0, 1, 2, 3, 4, 9, 10, 5, 6, 7, 8, 12, 13, 14], BARR, P2(0, 0, 0, 0, 3, 0), dim=True),
    Venue("factory", "THE ROBOT FACTORY", "managerbot", "MANAGER-BOT", "L", [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 15], BARR, P2(0, 0, 0, 4, 8, 0)),
    Venue("biker", "THE CHROME COW", "granny", "GRANNY", "L", [0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14], BARR, P2(0, 0, 0, 2, 2, 0), band_from_bar=True),
    Venue("teahouse", "THE TEAHOUSE", "hana", "HANA", "L", [0, 1, 2, 3, 4, 5, 6, 11, 12, 13, 14, 15, 16, 17], BARR, [(76, 0, 0, 0)]),
    Venue("zoo", "THE JUNGLE ZOO", "kiki", "KIKI", "L", [0, 1, 2, 3, 4, 5, 6, 12, 13, 14, 15, 16, 17, 18], BARR, P2(0, 0, 0, 3, 5, 0)),
    Venue("space", "THE SPACE LOUNGE", "zizz", "ZIZZ", "L", [0, 1, 2, 3, 4, 10, 11, 5, 6, 12, 13, 7, 8, 9], BARR, P2(0, 0, 0, 1, 4, 0)),
]


def bg_stats(page):
    import gen_story as g
    tiles, flips, maps = set(), set(), []
    for cy in range(BY, BY + BH):
        for cx in range(BX, BX + BW):
            t = [[page.px[cy * 8 + y][cx * 8 + x][0] for x in range(8)] for y in range(8)]
            tiles.add(tuple(a for r_ in t for a in r_))
            c = []
            for fx in (0, 1):
                for fy in (0, 1):
                    u = [r_[::-1] if fx else r_ for r_ in (t[::-1] if fy else t)]
                    c.append(tuple(a for r_ in u for a in r_))
            flips.add(min(c))
            m = {}
            for y in range(8):
                for x in range(8):
                    s, h = page.px[cy * 8 + y][cx * 8 + x]
                    m[s] = q5(h)
            maps.append(tuple(sorted(m.items())))
    um = list(dict.fromkeys(maps))
    big = list(dict.fromkeys(m for m in um if not any(set(m) < set(o) for o in um)))
    try:
        pals = g.pack_palettes([dict(m) for m in big])[0]
    except TypeError:                       # more than 8 palettes needed: a greedy merge gives the count (an upper bound)
        pals = []
        for m in sorted(big, key=len, reverse=True):
            for p in pals:
                if all(p.get(s, h) == h for s, h in m):
                    p.update(dict(m))
                    break
            else:
                pals.append(dict(m))
    return len(tiles), len(flips), [[p.get(s, "-") for s in range(4)] for p in pals]
