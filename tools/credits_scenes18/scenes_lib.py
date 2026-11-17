"""Credits scene pages (owner 2026-11-13): the tools that CONVERT, COUNT and PREVIEW. They place no art pixel of their own.

Every art pixel comes from one of three hand-made sources:
  * the owner's portrait (assets/story/portraits/<name>.txt, copied as it is, one 56x56 box of 7x7 tiles);
  * the venue's approved in-game tiles (assets/approved/venues/<venue>_stage / _bar / _floor .txt, copied tile for tile);
  * tile kits drawn by hand in scenes_a.py / scenes_b.py (8 text rows of 8 characters a tile, one letter a colour).
The page is a map of 20 x 13 cells (160 x 104, the size of the story's pictures) of those tiles; the portrait is blitted into its 7x7 box.
The library writes the page as a portrait-v2 picture (the story's own picture source format: one hex a DMG shade a tile, tools/gen_story.py read_pic
checks it exactly and packs the Color palettes), counts its unique tiles and palettes, and renders the DMG and Color previews.
"""
import json
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "tools"))

PW, PH = 160, 104
VEN = ROOT / "assets/approved/venues"
PORT = ROOT / "assets/story/portraits"

DMG_GRAY = {0: (255, 255, 255), 1: (153, 153, 153), 2: (85, 85, 85), 3: (0, 0, 0)}   # the shades PyBoy / the game's screenshots show
PAGE_BG = "#181040"      # the credits page behind the picture (COL_BAND: RGB15(3, 2, 8))
CREAM = "#f8e8b0"        # the HUD text colour on the cards
VNAMES = {}
VENUE_BAND = {"saloon": "#702840", "igloo": "#285090", "space": "#181868"}   # the stripe's colour: the venue's stage palette colour 2 (sampled from the real cards)


def q5(h):
    return "#%02x%02x%02x" % tuple((int(h[i:i + 2], 16) >> 3) << 3 for i in (1, 3, 5))


def hexrgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def cc(rgb):
    """the colour-corrected CGB screen (the usual gbdev matrix); the preview of what the real screen shows"""
    r, g, b = rgb
    return (r, g, b)


# ---- sources -----------------------------------------------------------------------------------------------------------
def read_portrait(name):
    """-> pix[56][56] of (shade, hex) as the portrait's own key gives them, and the backdrop pixel"""
    key, rows, mode, acc = {}, [], None, {}
    for ln in (PORT / f"{name}.txt").read_text().splitlines():
        if ln.startswith("@key"):
            mode = "k"
        elif ln.startswith("@pixels"):
            mode = "p"
        elif ln.startswith(";") or ln.startswith("@") or not ln.strip():
            continue
        elif mode == "k":
            p = ln.split()
            key[p[0]] = (int(p[1]), p[2])
            if len(p) > 4 and p[4].startswith("obj="):
                acc[p[0]] = p[4][4:]            # a Color-only OBJ accent: the BG art shows the key it names under it
        elif mode == "p":
            rows.append(ln)
    assert len(rows) == 56 and all(len(r) == 56 for r in rows), name
    return [[key[acc.get(c, c)] for c in r] for r in rows], key["."]


def venue_tiles(venue, part, pal, w=20):
    """an approved in-game strip (stage 160x32, bar 160x24, floor 8x8) as a dict (col, row) -> 8x8 of (shade, hex); colours from <venue>_pal.json[pal]"""
    cols = json.load(open(VEN / f"{venue}_pal.json"))[pal]["hex"]
    rows = [l for l in (VEN / f"{venue}_{part}.txt").read_text().splitlines() if l and not l.startswith(";")]
    out = {}
    for ty in range(len(rows) // 8):
        for tx in range(len(rows[0]) // 8):
            out[(tx, ty)] = [[(".-+#".index(rows[ty * 8 + y][tx * 8 + x]), cols[".-+#".index(rows[ty * 8 + y][tx * 8 + x])]) for x in range(8)] for y in range(8)]
    return out


def kit(key, tiles):
    """a hand-drawn kit: key = {char: (shade, hex)}, tiles = {name: 8 strings of 8 characters} -> {name: 8x8 of (shade, hex)}"""
    out = {}
    for n, rows in tiles.items():
        assert len(rows) == 8 and all(len(r) == 8 for r in rows), (n, [len(r) for r in rows])
        out[n] = [[key[c] for c in r] for r in rows]
    return out


def split16(name, rows):
    """a hand-drawn 16 x 16 piece (16 rows of 16 characters) cut into its four 8 x 8 tiles: <name>00 <name>10 (top: left, right) <name>01 <name>11"""
    assert len(rows) == 16 and all(len(r) == 16 for r in rows), (name, [len(r) for r in rows])
    return {f"{name}{i}{j}": [r[i * 8:i * 8 + 8] for r in rows[j * 8:j * 8 + 8]] for j in (0, 1) for i in (0, 1)}


# ---- the page ----------------------------------------------------------------------------------------------------------
class Page:
    def __init__(self, name, fill):
        self.name = name
        self.px = [[fill] * PW for _ in range(PH)]
        self.cells = {}        # (cx, cy) -> a label of where the tile came from (for the notes)

    def tile(self, cx, cy, t, label=""):
        for y in range(8):
            for x in range(8):
                self.px[cy * 8 + y][cx * 8 + x] = t[y][x]
        self.cells[(cx, cy)] = label

    def mapped(self, rows, lib):
        """rows: 13 lists of 20 tile names (or None to leave the cell); lib: name -> tile"""
        assert len(rows) == 13
        for cy, r in enumerate(rows):
            assert len(r) == 20, (cy, len(r))
            for cx, n in enumerate(r):
                if n is not None:
                    self.tile(cx, cy, lib[n], n)

    def portrait(self, pix, cx, cy, over=None):
        """the owner's 56x56 as it is at cell (cx, cy); over = {(i, j): tile}: box cells that are pure backdrop in the portrait and are decorated by the scene instead"""
        for y in range(56):
            for x in range(56):
                self.px[cy * 8 + y][cx * 8 + x] = pix[y][x]
        for (i, j), t in (over or {}).items():
            # the portrait's cell must be all backdrop: the scene may decorate empty tiles only
            bg = pix[0][0]
            assert all(pix[j * 8 + y][i * 8 + x] == bg for y in range(8) for x in range(8)), f"{self.name}: portrait cell {(i, j)} is not empty"
            self.tile(cx + i, cy + j, t, f"over{(i, j)}")

    # ---- the checks (the story picture's: one colour a DMG shade in a tile, the palettes packed) ----
    def unique_tiles(self):
        seen = {}
        for ty in range(13):
            for tx in range(20):
                t = tuple(self.px[ty * 8 + y][tx * 8 + x][0] for y in range(8) for x in range(8))
                seen.setdefault(t, 0)
                seen[t] += 1
        return len(seen)

    def unique_tiles_flip(self):
        seen = set()
        for ty in range(13):
            for tx in range(20):
                t = [[self.px[ty * 8 + y][tx * 8 + x][0] for x in range(8)] for y in range(8)]
                cands = []
                for fx in (0, 1):
                    for fy in (0, 1):
                        u = [r[::-1] if fx else r for r in (t[::-1] if fy else t)]
                        cands.append(tuple(v for r in u for v in r))
                seen.add(min(cands))
        return len(seen)

    def tile_maps(self):
        out = []
        for ty in range(13):
            for tx in range(20):
                m = {}
                for y in range(8):
                    for x in range(8):
                        s, h = self.px[ty * 8 + y][tx * 8 + x]
                        h = q5(h)
                        if m.setdefault(s, h) != h:
                            raise SystemExit(f"{self.name}: tile ({tx},{ty}): two colours on DMG shade {s}: {m[s]} and {h}")
                out.append(m)
        return out

    def palettes(self):
        """the Color BG palettes the page needs, as gen_story packs them (the HUD palette not counted): list of 4 hex, and the cells' palette index"""
        import gen_story as g
        maps = self.tile_maps()
        umaps = []
        for m in maps:
            if tuple(sorted(m.items())) not in umaps:
                umaps.append(tuple(sorted(m.items())))
        big = list(dict.fromkeys(m for m in umaps if not any(set(m) < set(o) for o in umaps)))
        pals = g.pack_palettes([dict(m) for m in big])[0]
        attr = []
        for m in maps:
            attr.append(next(i for i, p in enumerate(pals) if all(p.get(s, c) == c for s, c in m.items())))
        return [[p.get(s, "-") for s in range(4)] for p in pals], attr, len(big)

    # ---- the preview ----
    def render(self, cgb):
        im = Image.new("RGB", (PW, PH))
        for y in range(PH):
            for x in range(PW):
                s, h = self.px[y][x]
                im.putpixel((x, y), cc(hexrgb(q5(h))) if cgb else DMG_GRAY[s])
        return im

    def write_v2(self, path):
        """the page as a portrait-v2 picture source (the story's picture format): one character a (shade, hex)"""
        chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@%&*=~^"
        key = {}
        for row in self.px:
            for p in row:
                if p not in key:
                    key[p] = chars[len(key)]
        lines = [f"; {self.name}: a credits scene page proposal (owner 2026-11-13), hand-made tiles plus the owner's portrait, written by scenes_lib.py (a transcription).",
                 "@size 160 104", "@maxpal 5", "@key"]
        for (s, h), c in key.items():
            lines.append(f"{c} {s} {h} c{c}")
        lines.append("@pixels")
        for row in self.px:
            lines.append("".join(key[p] for p in row))
        Path(path).write_text("\n".join(lines) + "\n")


def page_card(pic, venue, owner_name, cgb):
    """the whole 160x144 card as the roll would show it: the venue's band (name in 16 px tall letters on the stripe), the picture, the owner's name"""
    import gen_credits as gc
    im = Image.new("RGB", (160, 144), cc(hexrgb(q5(PAGE_BG))) if cgb else DMG_GRAY[3])
    band = cc(hexrgb(q5(VENUE_BAND[venue]))) if cgb else DMG_GRAY[2]
    ink = cc(hexrgb(q5(CREAM))) if cgb else DMG_GRAY[0]
    vname = VNAMES.get(venue) or {"saloon": "THE SALOON", "igloo": "THE IGLOO", "space": "THE SPACE LOUNGE"}[venue]
    for y in range(8, 32):
        for x in range(160):
            im.putpixel((x, y), band)
    px, x0, x1 = gc.strip(vname)
    dx = 80 - (x0 + x1 + 1) // 2
    for y in range(16):
        for x in range(len(px[0])):
            if px[y // 2][x] != gc.BAND:
                im.putpixel((x + dx, 8 + 4 + y), ink)
    im.paste(pic.render(cgb), (0, 32))
    px, x0, x1 = gc.strip(owner_name)
    dx = 80 - (x0 + x1 + 1) // 2
    for y in range(8):
        for x in range(len(px[0])):
            if px[y][x] != gc.BAND:
                im.putpixel((x + dx, 136 + y), ink)
    return im
