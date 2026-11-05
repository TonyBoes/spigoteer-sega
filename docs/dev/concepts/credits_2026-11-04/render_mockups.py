#!/usr/bin/env python3
"""Credits remake mockups (concept only, nothing imported). Read-only on the repo; writes PNGs under the output directory.

    python3 render_mockups.py OUTDIR

Every patron pixel is copied from assets/art/patrons/<group>.txt / <group>_x.txt (the shift-0 front pose, as src/credits.c draws it); colours are the
Palette Plan's (tools/artifacts/palette_plan/plan_slots.json, the Atlas export), 5 bits a channel as the hardware holds them; the lettering is the
game's own (tools/gen_credits.py: the glyphs of assets/tiles/bar.txt, one 8 px cell a character, the ink centred to the pixel). Nothing is drawn
by this script: it places the art, the palettes and the text, and measures (tiles, sprites per line, OBJ palettes).
"""
import ast
import json
import re
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import gen_credits as gc  # noqa: E402  (glyphs, strip, VENUES, PATRONS)

SLOTS = json.load(open(ROOT / "tools/artifacts/palette_plan/plan_slots.json"))["venues"]
GROUPS = ["cowboys", "sports", "lumberjacks", "chefs", "divers", "robots", "punks", "ninjas", "zoo", "aliens"]


def plan_names():
    """plan_data.NAMES, read without importing plan_data (which needs a built ROM's palettes.c)"""
    tree = ast.parse((ROOT / "tools/artifacts/palette_plan/plan_data.py").read_text())
    for n in tree.body:
        if isinstance(n, ast.Assign) and n.targets[0].id == "NAMES":
            return ast.literal_eval(n.value)


NAMES = plan_names()
BAND = (24, 16, 64)          # the CGB card's navy (the HUD palette's colour 3: golden credits_cast_patrons_*.cgb.png)
CREAM = (248, 232, 176)      # the lettering
DMG_BAND, DMG_INK = (0, 0, 0), (255, 255, 255)
DMG_SHADE = {1: (255, 255, 255), 2: (153, 153, 153), 3: (0, 0, 0)}   # the DMG card's patron shades (golden: idx 1 white, 2 light, 3 dark)

# Saloon: each look's own (primary) palette instance, plan_data.SALOON_PRIMARY; instance -> OBJ slot (INST_OBJ)
SAL_PRIMARY = {"DUSTY": 1, "EMMA": 1, "GUS": 0, "HANK": 0, "ROSIE": 3, "REDD": 3, "MABEL": 4, "ARTIE": 4}
SAL_OBJ = [3, 6, 7, 4, 5]
# the game swaps planes 1/2 of the C variant of the Saloon (GUS) and the Lodge (ASH) at level load (level.c swap_gus), and the plan's colours are for the
# swapped tiles: the mockup swaps the art's indices the same way before it applies the plan's palette (a Color build writes the palette swapped instead)
SWAPPED = {("cowboys", "GUS"), ("lumberjacks", "ASH")}


def blocks(path):
    out, cur, lab = [], [], ""
    for l in Path(path).read_text().splitlines():
        if re.fullmatch(r"[.\-+#]{16}", l):
            cur.append(l)
        else:
            if cur:
                out.append((lab, cur))
                cur = []
            if l.startswith(";"):
                lab = l[1:].strip()
    if cur:
        out.append((lab, cur))
    return out


def c5(h):
    """plan hex (a 5-bit channel lifted to 8) -> the 8 bit the emulator shows (5 bits << 3)"""
    return tuple(((int(h[i:i + 2], 16) >> 3) << 3) for i in (1, 3, 5))


def looks(g):
    """the venue's 8 looks, in order (3 base looks, then the Color-only ones): dict name, art, cols (3 colours: indices 1-3), obj slot"""
    d = ROOT / "assets/art/patrons"
    base = blocks(d / ("cowboys.txt" if g == "cowboys" else g + ".txt"))
    xs = blocks(d / ("saloon_x.txt" if g == "cowboys" else g + "_x.txt"))
    names = [n.split(",")[0].strip() for n in NAMES[g]]
    items = [(names[i], base[i][1], True) for i in range(3)] + [(lab.split()[0], rows, False) for lab, rows in xs]
    if g == "cowboys":
        assert [n for n, _, _ in items] == ["DUSTY", "EMMA", "GUS", "HANK", "ROSIE", "REDD", "MABEL", "ARTIE"], items
    out = []
    for name, rows, is_base in items:
        if g == "cowboys":
            slot = SAL_OBJ[SAL_PRIMARY[name]]
        else:
            hit = [int(k) for k, e in SLOTS[g]["obj"].items() if any(p.split(",")[0].strip() == name for p in e["patrons"])]
            assert len(hit) == 1, (g, name, hit)
            slot = hit[0]
        cols = [c5(h) for h in SLOTS[g]["obj"][str(slot)]["cols"][1:]]
        if (g, name) in SWAPPED:
            rows = [r.translate(str.maketrans("-+", "+-")) for r in rows]
        out.append(dict(name=name, art=rows, cols=cols, obj=slot, base=is_base))
    assert len(out) == 8, (g, len(out))
    if g == "lumberjacks":          # the owner's order (2026-10-17): ASH in the middle, so the three labels fit one row (gen_credits.py SLOT)
        out[1], out[2] = out[2], out[1]
    return out


IDX = {".": 0, "-": 1, "+": 2, "#": 3}


class Card:
    def __init__(self, cgb):
        self.cgb = cgb
        self.im = Image.new("RGB", (160, 144), BAND if cgb else DMG_BAND)
        self.ink = CREAM if cgb else DMG_INK
        self.sprites = []          # (x, y) of each 8x16 object's top left
        self.text_rows = {}        # tile row -> list of the 8x8 tile contents (non-blank), for the tile count

    def text(self, s, cx=None, x0=None, y=0, edge=8):
        """lettering at tile row y/8: ink centred on cx (as gen_credits row()), or its ink starting at x0"""
        px, a, b = gc.strip(s)
        dx = (cx - (a + b + 1) // 2) if cx is not None else x0 - a
        assert a + dx >= edge and b + dx < 160 - edge, (s, a + dx, b + dx)
        for yy in range(8):
            for xx in range(len(px[0])):
                if px[yy][xx] != gc.BAND:
                    self.im.putpixel((xx + dx, y + yy), self.ink)
        return a + dx, b + dx

    def patron(self, L, x, y):
        """the 16x16 front pose at (x, y): index 0 is transparent; two 8x16 objects"""
        for yy, row in enumerate(L["art"]):
            for xx, ch in enumerate(row):
                i = IDX[ch]
                if i:
                    self.im.putpixel((x + xx, y + yy), L["cols"][i - 1] if self.cgb else DMG_SHADE[i])
        self.sprites += [(x, y), (x + 8, y)]

    def tiles(self):
        """tile rows of the lettering (BG tiles): the non-blank 8x8 cells, unique by content, among the card's rows 2-17 (the header is the venue's, kept)"""
        seen = set()
        n = 0
        for ty in range(2, 18):
            for tx in range(20):
                t = tuple(self.im.getpixel((tx * 8 + x, ty * 8 + y)) == self.ink for y in range(8) for x in range(8))
                # only cells that hold lettering: the sprites are objects, not tiles; so count a cell as text when it is on a name row (set by the caller)
                if ty in self.text_rows and any(t):
                    n += 1
                    seen.add(t)
        return n, len(seen)

    def per_line(self, bob=2):
        worst = 0
        for ly in range(-4, 150):
            n = sum(1 for (_, y) in self.sprites if y - bob <= ly < y + 16)
            worst = max(worst, n)
        return worst


def header(c, g):
    c.text(gc.VENUES[GROUPS.index(g)], cx=80, y=8)


def row_layout(widths, gap_max=24, edge=8):
    """x of each ink start in one row of labels: equal gaps (at most gap_max), the row centred (as gen_credits does for the three labels)"""
    gap = min(gap_max, (160 - 2 * edge - sum(widths)) // (len(widths) - 1)) if len(widths) > 1 else 0
    total = sum(widths) + gap * (len(widths) - 1)
    x = (160 - total) // 2
    xs = []
    for w in widths:
        xs.append(x)
        x += w + gap
    return xs, gap


def put_label_sprite(c, L, x0, w, name_y, air=4):
    cx = x0 + w // 2
    c.text(L["name"], x0=x0, y=name_y)
    c.text_rows[name_y // 8] = 1
    c.patron(L, cx - 8, name_y - 16 - air)


def layout_dmg(g):
    """the DMG card as it is now: header, the three base patrons in a row, labels under (credits.c: label row 11, sprites 24 px above)"""
    c = Card(False)
    header(c, g)
    ls = looks(g)[:3]
    ws = [gc.ink_width(L["name"]) for L in ls]
    xs, _ = row_layout(ws)
    for L, x0, w in zip(ls, xs, ws):
        put_label_sprite(c, L, x0, w, 88, air=8)
    return c


def layout_A(g, k=0):
    """one card, a 3 / 3 / 2 grid: sprite over its name, each row centred (a row's labels laid out from their ink widths, like today's one row)"""
    c = Card(True)
    header(c, g)
    ls = looks(g)
    rows = [ls[0:3], ls[3:6], ls[6:8]]
    for r, grp in enumerate(rows):
        ws = [gc.ink_width(L["name"]) for L in grp]
        xs, gap = row_layout(ws, gap_max=24 if r < 2 else 40)
        assert gap >= 6, (g, [L["name"] for L in grp], gap)
        for L, x0, w in zip(grp, xs, ws):
            put_label_sprite(c, L, x0, w, 48 + 40 * r)
    return c


def layout_B(g, k=0):
    """one card, a roster: two columns of four, the sprite at the left, its name to the right, rows 24 px apart"""
    c = Card(True)
    header(c, g)
    ls = looks(g)
    for i, L in enumerate(ls):
        col, r = divmod(i, 4)
        x = 8 if col == 0 else 84
        ny = 40 + 24 * r
        c.patron(L, x, ny - 4)
        c.text(L["name"], x0=x + 16 + 6, y=ny, edge=0)
        c.text_rows[ny // 8] = 1
    return c


def layout_C(g, k):
    """two cards of four (k = 0, 1): a 2 x 2 grid, sprite over its name, columns 64 px apart"""
    c = Card(True)
    header(c, g)
    ls = looks(g)[4 * k:4 * k + 4]
    for i, L in enumerate(ls):
        r, col = divmod(i, 2)
        cx = 48 + 64 * col
        w = gc.ink_width(L["name"])
        put_label_sprite(c, L, cx - w // 2, w, 56 + 48 * r)
    return c


LAYOUTS = {"A": layout_A, "B": layout_B, "C": layout_C}


def four_across():
    """why 2 rows of 4 with the name under each does not fit: the gap left between neighbouring names in the worse row of four (8 px needed, as gen_credits asserts)"""
    res = {}
    for g in GROUPS:
        ls = looks(g)
        gaps = []
        for grp in (ls[:4], ls[4:]):
            ws = [gc.ink_width(L["name"]) for L in grp]
            gaps.append((160 - 16 - sum(ws)) // 3)
        res[g] = min(gaps)
    return res


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    stats = {}
    for g in GROUPS:
        for lay, fn in LAYOUTS.items():
            for k in ((0, 1) if lay == "C" else (0,)):
                c = fn(g, k)
                c.im.save(out / f"{lay}_{g}_{k}.png")
                n, u = c.tiles()
                stats[(lay, g, k)] = dict(lines=c.per_line(), text_tiles=n, text_unique=u, spr=len(c.sprites))
        layout_dmg(g).im.save(out / f"dmg_{g}.png")
        L = looks(g)
        stats[("pal", g, 0)] = dict(palettes=len({tuple(x["cols"]) for x in L}), obj=sorted({x["obj"] for x in L}))
    print("four across, the gap left between names (px, 8 needed):", four_across())
    json.dump({"|".join(map(str, k)): v for k, v in stats.items()}, open(out / "stats.json", "w"), indent=1)
    for k, v in stats.items():
        print(k, v)


if __name__ == "__main__":
    main()
