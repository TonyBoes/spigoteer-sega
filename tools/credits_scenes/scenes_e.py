"""Round 4 (owner, on round 3: "use enough color palettes to color the kegs and what not correctly. Maybe add some of the entertainers in the background"):
all 10 venues, the round-3 layout (box 14 x 9 cells, 112 x 72 px, centred on the page; the owner's portrait exactly as drawn on its bottom edge, cut out of its
backdrop by scenes_c.backdrop_mask), with

  * the ROOM in the venue's OWN in-game colours: every stage / bar / floor tile is the game's approved tile with the game's own palette (stage_a / stage_b per
    <venue>_attr.txt, bar / bar_b per <venue>_bar_attr.txt, the floor tile in the bar palette);
  * the OWNER in the owner's own palettes (as the story packs them);
  * a cell that holds owner and room pixels has ONE palette, the owner's: its room pixels take the nearest of the owner palette's colours (a recolour of the room's
    pixels in that cell, never of the owner's); the report lists those cells;
  * the venue's show performers (assets/approved/venues/<venue>_show*.txt, first frame of a performer, the game's OBJ colours) standing on the stage ledge: they are
    OBJ sprites in the game (the Color art where the Color show has its own), so they are drawn over the room in the preview and costed as OBJ tiles / palettes;
  * the room one step back in value only where its true colours are brighter than the owner (DIM_STAGE: stage palette shades 0->1, 1->2, 2->3 within the stage's
    own palette, props untouched).
The room's arrangement is the game's own tiles in the order the game lays them out, columns picked by hand (sc / BAR below); the row above the ledge is the wall's
most common tile; the front row is the venue's floor tile.
"""
import json
import sys
from collections import Counter

from scenes_lib import *
from scenes_c import read_raw, backdrop_mask

BX, BY, BW, BH = 3, 2, 14, 9


def lines(path):
    return [l for l in path.read_text().splitlines() if l and not l.startswith(";")]


class Venue:
    def __init__(self, key, vname, owner, oname, side, sc, bar, perf, dim=False, band_from_bar=False):
        self.key, self.vname, self.owner, self.oname, self.side = key, vname, owner, oname, side
        self.sc, self.bar, self.perf, self.dim = sc, bar, perf, dim
        pal = json.load(open(VEN / f"{key}_pal.json"))
        self.pal = {k: v["hex"] for k, v in pal.items() if isinstance(v, dict) and "hex" in v}
        self.stage = lines(VEN / f"{key}_stage.txt")
        self.sattr = lines(VEN / f"{key}_attr.txt")
        self.barg = lines(VEN / f"{key}_bar.txt")
        self.battr = lines(VEN / f"{key}_bar_attr.txt")
        self.floor = lines(VEN / f"{key}_floor.txt")
        VNAMES[key] = vname
        VENUE_BAND[key] = self.pal["bar"][2] if band_from_bar else self.pal["stage_a"][2]

    def stage_tile(self, c, r):
        a = int(self.sattr[r][c])
        pn = ["stage_a", "stage_b"][a]
        g = [[".-+#".index(self.stage[r * 8 + y][c * 8 + x]) for x in range(8)] for y in range(8)]
        return g, pn

    def bar_tile(self, c, r):
        a = int(self.battr[r][c]) if r < len(self.battr) and c < len(self.battr[r]) else 0
        pn = ["bar", "bar_b"][a]
        g = [[".-+#".index(self.barg[r * 8 + y][c * 8 + x]) for x in range(8)] for y in range(8)]
        return g, pn

    def floor_tile(self):
        return [[".-+#".index(self.floor[y][x]) for x in range(8)] for y in range(8)], "bar"

    def plain_wall(self):
        cnt = Counter()
        for c in range(20):
            g, pn = self.stage_tile(c, 1)
            cnt[(tuple(map(tuple, g)), pn)] += 1
        (g, pn), _ = cnt.most_common(1)[0]
        return [list(r) for r in g], pn

    def plain_bar(self, r, c):
        if r == 2:
            return self.bar_tile(c % 2, 2)
        cnt = Counter()
        for cc_ in range(17):
            g, pn = self.bar_tile(cc_, r)
            cnt[(tuple(map(tuple, g)), pn)] += 1
        (g, pn), _ = cnt.most_common(1)[0]
        return [list(x) for x in g], pn

    def room_cells(self):
        """13 x 9 -> {(cx, cy): (shades 8 x 8, palette name)}"""
        out = {}
        pw = self.plain_wall()
        for cx in range(BW):
            c = self.sc[cx]
            for cy, r in ((0, 0), (1, 1), (2, 2), (4, 3)):
                out[(cx, cy)] = self.stage_tile(c, r)
            out[(cx, 3)] = pw
            for cy, r in ((5, 0), (6, 1), (7, 2)):
                if cx in self.bar:
                    out[(cx, cy)] = self.bar_tile(self.bar[cx], r)
                else:
                    out[(cx, cy)] = self.plain_bar(r, cx)
            out[(cx, 8)] = self.floor_tile()
        return out


def owner_palettes(owner):
    import gen_story as g
    key, rows = read_raw(owner)
    maps = []
    for ty in range(7):
        for tx in range(7):
            m = {}
            for y in range(8):
                for x in range(8):
                    s, h = key[rows[ty * 8 + y][tx * 8 + x]]
                    m[s] = q5(h)
            maps.append(tuple(sorted(m.items())))
    um = list(dict.fromkeys(maps))
    big = list(dict.fromkeys(m for m in um if not any(set(m) < set(o) for o in um)))
    return g.pack_palettes([dict(m) for m in big])[0]


def nearest(h, pal):
    r, g, b = hexrgb(h)
    return min(pal.items(), key=lambda kv: sum((a - c) ** 2 for a, c in zip(hexrgb(kv[1]), (r, g, b))))


def build(v):
    """-> page (the box on the 20 x 13 picture, no performers), the list of mixed cells, per-cell palette names"""
    pals = owner_palettes(v.owner)
    key, rows = read_raw(v.owner)
    mask = backdrop_mask(rows)
    x0 = 56 if v.side == "R" else 0
    fig = {}
    for y in range(56):
        for x in range(56):
            if not mask[y][x]:
                fig[(x0 + x, 16 + y)] = key[rows[y][x]]
    room = v.room_cells()
    page = Page(v.key, (3, PAGE_BG))
    mixed, used = [], {}
    for cy in range(BH):
        for cx in range(BW):
            g, pn = room[(cx, cy)]
            fcell = {(x, y): fig[(cx * 8 + x, cy * 8 + y)] for y in range(8) for x in range(8) if (cx * 8 + x, cy * 8 + y) in fig}
            if fcell:
                m = {}
                for f in fcell.values():
                    if m.setdefault(f[0], f[1]) != f[1]:
                        raise SystemExit(f"{v.key}: owner cell ({cx},{cy}) holds two colours of shade {f[0]}")
                cands = [p for p in pals if all(p.get(s) == h for s, h in m.items())]
                assert cands, (v.key, cx, cy, m)
                # of the owner palettes that hold this cell's owner colours, the one nearest to the room's colours in the cell
                rc = {v.pal[pn][g[y][x]] for y in range(8) for x in range(8) if (x, y) not in fcell}
                p = min(cands, key=lambda q: sum(sum((a - b) ** 2 for a, b in zip(hexrgb(nearest(h, q)[1]), hexrgb(h))) for h in rc))
                if len(fcell) < 64:
                    mixed.append((cx, cy))
                used[(cx, cy)] = "owner"
            for y in range(8):
                for x in range(8):
                    px, py = (BX + cx) * 8 + x, (BY + cy) * 8 + y
                    if (x, y) in fcell:
                        page.px[py][px] = fcell[(x, y)]
                    elif fcell:
                        s, h = nearest(v.pal[pn][g[y][x]], p)      # a room pixel in an owner cell: the nearest of the owner palette's colours
                        page.px[py][px] = (s, h)
                    else:
                        s = g[y][x]
                        if v.dim and pn.startswith("stage"):
                            s = {0: 1, 1: 2, 2: 3, 3: 3}[s]
                        page.px[py][px] = (s, v.pal[pn][s])
                        used[(cx, cy)] = pn
    page.box = (BX, BY, BW, BH)
    page.fig = {(BX * 8 + x, BY * 8 + y) for (x, y) in fig}
    return page, mixed, used


def show_frames(path):
    rows = lines(path)
    n = len(rows) // 24
    return [rows[24 * k:24 * k + 24] for k in range(n)]


def perf_sprite(v, spec, cgb):
    """-> (frame rows, the three OBJ colours): the Color art where the venue has its own"""
    x, fd, fc, oi = spec
    f_cgb = VEN / f"{v.key}_show_cgb.txt"
    fr = show_frames(f_cgb if (cgb and f_cgb.exists()) else VEN / f"{v.key}_show.txt")[fc if (cgb and f_cgb.exists()) else fd]
    pj = json.load(open(VEN / f"{v.key}_show_pal.json"))["obj"]
    cols = pj[oi]["hex"] if isinstance(pj, list) else pj["hex"]
    return fr, cols


def with_performers(page, v, cgb):
    """a copy of the page with the performers drawn in (preview only; in the game they are OBJ)"""
    p2 = Page(page.name, (3, PAGE_BG))
    p2.px = [list(r) for r in page.px]
    for spec in v.perf:
        fr, cols = perf_sprite(v, spec, cgb)
        w = len(fr[0])
        for y in range(24):
            for x in range(w):
                c = fr[y][x]
                if c != ".":
                    i = "-+#".index(c)
                    py, px = (BY * 8 + 40 - 24) + y, BX * 8 + spec[0] + x
                    if (px, py) not in page.fig:      # behind the owner
                        p2.px[py][px] = (i + 1, cols[i])
    return p2


def obj_cost(v, cgb):
    tiles, cols = set(), set()
    for spec in v.perf:
        fr, c = perf_sprite(v, spec, cgb)
        w = len(fr[0])
        for ty in range(3):
            for tx in range(w // 8):
                t = tuple(fr[ty * 8 + y][tx * 8 + x] for y in range(8) for x in range(8))
                if any(ch != "." for ch in t):
                    tiles.add(t)
        cols.add(tuple(c))
    return len(tiles), len(cols)


def stats(page):
    import gen_story as g
    bx, by, bw, bh = page.box
    tiles, flips, maps = set(), set(), []
    for cy in range(by, by + bh):
        for cx in range(bx, bx + bw):
            t = [[page.px[cy * 8 + y][cx * 8 + x][0] for x in range(8)] for y in range(8)]
            tiles.add(tuple(a for r in t for a in r))
            c = []
            for fx in (0, 1):
                for fy in (0, 1):
                    u = [r[::-1] if fx else r for r in (t[::-1] if fy else t)]
                    c.append(tuple(a for r in u for a in r))
            flips.add(min(c))
            m = {}
            for y in range(8):
                for x in range(8):
                    s, h = page.px[cy * 8 + y][cx * 8 + x]
                    m[s] = q5(h)
            maps.append(tuple(sorted(m.items())))
    um = list(dict.fromkeys(maps))
    big = list(dict.fromkeys(m for m in um if not any(set(m) < set(o) for o in um)))
    pals = g.pack_palettes([dict(m) for m in big])[0]
    return len(tiles), len(flips), [[p.get(s, "-") for s in range(4)] for p in pals]


# sc: the 14 stage columns (box cols 0..13) in the game's order, hand-picked so the room's features show beside the owner; BAR: box col -> bar col (the keg / kettle group)
# perf: (x in the box, DMG frame, Color frame, OBJ palette index)   side: where the owner stands (R: box cols 7-13, L: 0-6)
VENUES = [
    Venue("saloon", "THE SALOON", "sadie", "SADIE", "R", [0, 2, 7, 8, 9, 10, 11, 12, 3, 4, 5, 6, 17, 18], {1: 17, 2: 18, 3: 19}, [(6, 0, 0, 0), (30, 0, 0, 1)]),
    Venue("sports", "THE STADIUM", "coach", "COACH", "L", [0, 1, 2, 3, 4, 10, 15, 5, 6, 7, 8, 9, 11, 12], {11: 17, 12: 18, 13: 19}, [(60, 0, 0, 0), (84, 0, 0, 0)]),
    Venue("lodge", "THE LUMBER LODGE", "june", "JUNE", "R", [0, 1, 2, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 17], {1: 17, 2: 18, 3: 19}, [(6, 0, 0, 0), (30, 0, 11, 0)]),
    Venue("bistro", "THE BISTRO", "colby", "COLBY", "L", [0, 1, 2, 3, 4, 5, 6, 11, 12, 13, 14, 15, 16, 17], {11: 17, 12: 18, 13: 19}, [(60, 0, 0, 0), (84, 4, 4, 1)]),
    Venue("igloo", "THE IGLOO", "aurora", "AURORA", "L", [0, 1, 2, 3, 4, 9, 10, 5, 6, 7, 8, 12, 13, 14], {11: 17, 12: 18, 13: 19}, [(60, 0, 0, 0), (84, 0, 3, 0)], dim=True),
    Venue("factory", "THE ROBOT FACTORY", "managerbot", "MANAGER-BOT", "L", [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 15], {11: 17, 12: 18, 13: 19}, [(60, 0, 0, 0), (84, 4, 8, 0)]),
    Venue("biker", "THE CHROME COW", "granny", "GRANNY", "R", [0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14], {1: 17, 2: 18, 3: 19}, [(6, 0, 0, 0), (30, 2, 2, 0)], band_from_bar=True),
    Venue("teahouse", "THE TEAHOUSE", "hana", "HANA", "R", [0, 1, 2, 3, 4, 5, 6, 11, 12, 13, 14, 15, 16, 17], {1: 17, 2: 18, 3: 19}, [(30, 0, 0, 0)]),
    Venue("zoo", "THE JUNGLE ZOO", "kiki", "KIKI", "L", [0, 1, 2, 3, 4, 5, 6, 12, 13, 14, 15, 16, 17, 18], {11: 17, 12: 18, 13: 19}, [(60, 0, 0, 0), (84, 3, 5, 0)]),
    Venue("space", "THE SPACE LOUNGE", "zizz", "ZIZZ", "R", [0, 5, 6, 12, 13, 1, 2, 3, 4, 7, 8, 9, 10, 11], {1: 17, 2: 18, 3: 19}, [(6, 0, 0, 0), (30, 1, 4, 0)]),
]
