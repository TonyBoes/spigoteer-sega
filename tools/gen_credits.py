#!/usr/bin/env python3
"""The credits' pre-rendered text (src/credits.c; owner 2026-10-17: "title-style centring").

Every line of the cast cards and of the roll is drawn here, at build time, into its own 8x8 tiles, as the title menu's text is (tools/gen_art.py
title_art): the HUD glyphs of assets/tiles/bar.txt and the story punctuation of assets/tiles/story.txt (one 8 px cell a character, the letter in
columns 1-5), blitted onto a 160 px row at a pixel x that centres the line's INK exactly (an odd-length line sits 4 px right of the tile grid,
inside one more tile), and cut into tiles. Identical tiles are stored once. The game streams a row's tiles into VRAM as it needs the row.

Writes (build/):
  credits_text.c  the pool, the rows' cell lists, two banked accessors (credits_tile_put, credits_row_get)   (#pragma bank 255, its own file)
  credits_text.h  row ids, the Spigoteer's / Dregs's sprite x, the venues whose middle label drops a row, the roll's row table
  credits_text.json  every row's text and ink box (tests)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_art import blocks, IDX  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BAND = 3                                     # the HUD palette's colour 3: the band (a glyph tile is '#' where it is empty)

TITLE = ["CAST OF", "CHARACTERS"]
SAL = ["SAL TAPLEY", "THE SPIGOTEER"]
DREGS = ["DREGS", "RIVAL"]
VENUES = ["THE SALOON", "THE STADIUM", "THE LUMBER LODGE", "THE BISTRO", "THE IGLOO", "THE ROBOT FACTORY", "THE CHROME COW", "THE TEAHOUSE",
          "THE JUNGLE ZOO", "THE SPACE LOUNGE"]
OWNERS = ["SADIE", "COACH", "JUNE", "COLBY", "AURORA", "MANAGER-BOT", "GRANNY", "HANA", "KIKI", "ZIZZ"]      # the story's own names, in venue order
BOSSES = ["BIG TEX", "THE MASCOT", "SASQUATCH", "THE CRITIC", "THE YETI", "PROTOTYPE", "DUKE", "SUMO CHAMP", "LEO THE LION", "MOTHERSHIP"]
# The patrons' names are the Graphics Atlas plan's (tools/artifacts/palette_plan/plan_data.py NAMES: the three base looks, art variants A, B, C; the Color-only
# looks are the labels of assets/art/patrons/<group>_x.txt, the plan's EXTRA_LOOKS order). Owner Q80 (2026-11-04, layout A): one card a venue with all 8
# looks on Color, in rows of 3, 3 and 2, the name under each; the DMG card keeps the three base looks, one row (the first row of the Color card).
# SLOT is the base art variant standing in each of the first three places: only the lumber lodge is reordered (owner 2026-10-17: ASH in the middle, so
# the three labels fit one row): CEDAR (variant A, the cap), ASH (C, the green hat), WILLOW (B, the red-haired one).
GROUPS = ["cowboys", "sports", "lumberjacks", "chefs", "divers", "robots", "punks", "ninjas", "zoo", "aliens"]   # = gen_art.PATRON_GROUPS
SLOT = [[0, 1, 2]] * 10
SLOT[2] = [0, 2, 1]
# the Saloon's palette instance of each look (plan_data SALOON_PRIMARY: each look's own); instance -> the plan's OBJ slot (plan_data INST_OBJ)
SAL_PRIMARY = {"DUSTY": 1, "EMMA": 1, "GUS": 0, "HANK": 0, "ROSIE": 3, "REDD": 3, "MABEL": 4, "ARTIE": 4}
SAL_OBJ = [3, 6, 7, 4, 5]
# the game swaps planes 1 and 2 of GUS's and ASH's tiles at level load (level.c swap_gus) and the plan's colours are for the swapped tiles; the card loads
# the art as it is, so it writes their palettes with colours 1 and 2 swapped
SWAPPED = {("cowboys", "GUS"), ("lumberjacks", "ASH")}
PAT_ROWS = [(0, 3), (3, 6), (6, 8)]        # the looks of each card row (Color)
PAT_GAP = [24, 24, 40]                     # the widest gap of each row
PAT_MIN_GAP = 6                            # the narrowest gap any row may have (px)


def plan_names():
    """plan_data.NAMES, read without importing plan_data (which needs a built ROM's palettes.c)"""
    import ast
    tree = ast.parse((ROOT / "tools/artifacts/palette_plan/plan_data.py").read_text())
    for n in tree.body:
        if isinstance(n, ast.Assign) and n.targets[0].id == "NAMES":
            return ast.literal_eval(n.value)


def x_labels(g):
    """the first word of each label of assets/art/patrons/<x>.txt, in art order (the venue's Color-only looks)"""
    import re
    tag = "saloon_x" if g == "cowboys" else g + "_x"
    out, lab, cur = [], "", []
    for l in (ROOT / f"assets/art/patrons/{tag}.txt").read_text().splitlines():
        if re.fullmatch(r"[.\-+#]{16}", l):
            cur.append(l)
        else:
            if cur:
                out.append(lab.split()[0])
                cur = []
            if l.startswith(";"):
                lab = l[1:].strip()
    if cur:
        out.append(lab.split()[0])
    return out


def rgb555(h):
    return (int(h[1:3], 16) >> 3) | (int(h[3:5], 16) >> 3) << 5 | (int(h[5:7], 16) >> 3) << 10


def venue_looks():
    """per venue the 8 looks in card order: name, the plan's three colours (RGB555, colours 1-3, as the tiles are loaded), and the base art variant (3 looks) or None"""
    names, slots = plan_names(), json.load(open(ROOT / "tools/artifacts/palette_plan/plan_slots.json"))["venues"]
    out = []
    for gi, g in enumerate(GROUPS):
        base = [n.split(",")[0].strip() for n in names[g]][:3]
        xs = x_labels(g)
        assert len(xs) == 5, (g, xs)
        order = [(base[SLOT[gi][k]], SLOT[gi][k]) for k in range(3)] + [(n, None) for n in xs]
        lk = []
        for name, var in order:
            if g == "cowboys":
                slot = SAL_OBJ[SAL_PRIMARY[name]]
            else:
                hit = [int(k) for k, e in slots[g]["obj"].items() if any(p.split(",")[0].strip() == name for p in e["patrons"])]
                assert len(hit) == 1, (g, name, hit)
                slot = hit[0]
            cols = [rgb555(h) for h in slots[g]["obj"][str(slot)]["cols"][1:]]
            if (g, name) in SWAPPED:
                cols[0], cols[1] = cols[1], cols[0]
            lk.append(dict(name=name, cols=cols, var=var))
        assert len(lk) == 8 and all(len(l["name"]) <= 6 for l in lk), (g, [l["name"] for l in lk])
        out.append(lk)
    return out


LOOKS = venue_looks()
PATRONS = [[l["name"] for l in lk] for lk in LOOKS]      # the 8 names of each venue, in card order (the DMG card shows the first three)

# the roll: one string a tilemap ROW, centred; "" is a blank row. A sentence's lines are on consecutive rows, a list's items have two blank rows
# between them, a section gap is four or five. (Owner's lines 2026-10-17: "Game Design, Media, and Story by Tony and his tireless team of robot
# friends"; "no credits for public domain tunes. Public Domain."; "Special thanks to:" the platforms, frameworks and projects used.)
ROLL = [
    "SPIGOTEER",
    "", "", "",
    "GAME DESIGN,", "MEDIA, AND", "STORY BY", "TONY", "AND HIS TIRELESS", "TEAM OF", "ROBOT FRIENDS",   # one sentence
    "", "", "",
    "", "", "", "",                                 # the sprites' band (CR_BAND: 4 rows)
    "", "", "", "",
    "MUSIC",
    "", "", "",
    "PUBLIC DOMAIN", "MELODIES,", "ARRANGED", "FOR THIS GAME",                           # one sentence
    "", "", "", "", "",
    "SPECIAL", "THANKS TO:",
    "", "", "",
    "GBDK-2020", "", "",                            # the list: an item, two blank rows
    "SDCC", "", "",
    "HUGEDRIVER", "", "",
    "RGBDS", "", "",
    "SAMEBOY", "", "",
    "PYBOY", "", "",
    "PAN DOCS", "", "",
    "THE GBDEV", "COMMUNITY",                       # (one item, two lines)
    "", "", "", "", "", "", "", "", "", "", "", "",   # the screen empties before the last words
    "THANKS FOR", "PLAYING!",
]
ROLL_POOL = 160                                      # the roll's BG ids (credits.c CR_RING): the most tiles of 21 consecutive rows it may need
PUNCT = {".": "period", ",": "comma", "!": "excl", "?": "quest", "'": "apos", "-": "hyphen", ":": "colon"}

bar = dict(blocks(ROOT / "assets/tiles/bar.txt", named=True))
story = dict(blocks(ROOT / "assets/tiles/story.txt", named=True))


def glyph(ch):
    if ch == " ":
        return [[BAND] * 8 for _ in range(8)]
    rows = story["glyph_" + PUNCT[ch]] if ch in PUNCT else bar["glyph_" + ch]
    return [[IDX[c] for c in r] for r in rows]


def strip(text):
    """The line as a pixel strip (8 rows of 8 per character) and its ink box (x0, x1 inclusive) in it."""
    px = [[] for _ in range(8)]
    for ch in text:
        g = glyph(ch)
        for y in range(8):
            px[y] += g[y]
    xs = [x for x in range(len(px[0])) if any(px[y][x] != BAND for y in range(8))]
    return px, min(xs), max(xs)


POOL, POOL_IDX, ROWS, INFO = [], {}, [], {}


def tile_of(px, tx):
    t = tuple(tuple(px[y][tx * 8:tx * 8 + 8]) for y in range(8))
    if t not in POOL_IDX:
        POOL_IDX[t] = len(POOL)
        POOL.append(t)
    return POOL_IDX[t]


def row(name, items, edge=8):
    """A row of the screen: items = [(text, centre x)]. The ink of each is centred on its x (to the pixel: the half pixel goes left); the tiles cut,
    the empty ones at the ends dropped. Returns the ink boxes."""
    full = [[BAND] * 160 for _ in range(8)]
    boxes = []
    for text, cx in items:
        px, x0, x1 = strip(text)
        dx = cx - (x0 + x1 + 1) // 2
        assert x0 + dx >= edge and x1 + dx < 160 - edge, f"{name}: {text!r} reaches the screen's edge ({x0 + dx}..{x1 + dx})"
        for y in range(8):
            for x in range(len(px[0])):
                if px[y][x] != BAND:
                    full[y][x + dx] = px[y][x]
        boxes.append((text, x0 + dx, x1 + dx))
    tiles = []
    for tx in range(20):
        blank = all(full[y][tx * 8 + x] == BAND for y in range(8) for x in range(8))
        tiles.append(None if blank else tile_of(full, tx))
    live = [i for i, t in enumerate(tiles) if t is not None]
    c0, c1 = (live[0], live[-1]) if live else (0, -1)
    cells = [0xFFFF if t is None else t for t in tiles[c0:c1 + 1]]
    ROWS.append((name, c0, cells))
    INFO[name] = {"col": c0, "n": len(cells), "cells": cells, "ink": [{"text": t, "x0": a, "x1": b} for t, a, b in boxes]}
    return boxes


def centred(text, cx=80):
    return [(text, cx)]


def ink_width(text):
    _, a, b = strip(text)
    return b - a + 1


def main():
    out = Path(sys.argv[1])
    ids = {}

    def add(name, items):
        ids[name] = len(ROWS)
        return row(name, items)

    for i, t in enumerate(TITLE):
        add(f"TITLE{i}", centred(t))
    # the Spigoteer and Dregs: the 16 px sprite, a tile of air, then the two lines centred in a block of the wider one's width; the group centred
    pair_x = {}
    for key, lines in (("SAL", SAL), ("DREGS", DREGS)):
        w = max(ink_width(t) for t in lines)
        g = 16 + 8 + w
        left = (160 - g) // 2
        pair_x[key] = left
        for i, t in enumerate(lines):
            add(f"{key}{i}", centred(t, left + 24 + w // 2))
    for v in range(10):
        add(f"HDR{v}", centred(VENUES[v]))
    for v in range(10):
        add(f"OWNER{v}", centred(OWNERS[v]))
    # the labels of each card row are laid out from their ACTUAL ink widths: the widest gap (at most PAT_GAP, at least PAT_MIN_GAP) that keeps the whole
    # row inside the screen's edge margins, the row centred; each patron sprite then stands centred over its own label. Row 0 is the DMG card's (its three
    # looks), rows 1 and 2 are Color's.
    pat_cx = [[] for _ in range(10)]
    for r, (a, b) in enumerate(PAT_ROWS):
        for v in range(10):
            labels = PATRONS[v][a:b]
            w = [ink_width(t) for t in labels]
            gap = min(PAT_GAP[r], (160 - 2 * 8 - sum(w)) // (len(labels) - 1))
            assert gap >= PAT_MIN_GAP, f"{labels}: the labels leave a gap of {gap} px"
            total = sum(w) + (len(labels) - 1) * gap
            x = (160 - total) // 2
            items, cxs = [], []
            for t, wi in zip(labels, w):
                cx = x + wi // 2                    # (the ink's centre; the sprite's 16 px are centred on it)
                items.append((t, cx))
                cxs.append(cx)
                x += wi + gap
            pat_cx[v] += cxs
            add(f"PAT{'ABC'[r]}{v}", items)
    # the cards' OBJ palettes (Color): each venue's distinct colour triples, at most 7 (OBJ 1-7: OBJ 0 is the Spigoteer's, which the roll still needs)
    for v in range(10):      # credits.c writes a card's text cells to BG ids 178-255 (78), one a cell
        n = sum(1 for r in "ABC" for c in INFO[f"PAT{r}{v}"]["cells"] if c != 0xFFFF)
        assert n <= 78, (v, n, "the patron card's text outgrows BG ids 178-255")
    PAL_COLS, LOOK_PAL = [], []
    for lk in LOOKS:
        pcs = []
        for l in lk:
            if l["cols"] not in pcs:
                pcs.append(l["cols"])
        assert len(pcs) <= 7, ([l["name"] for l in lk], len(pcs))
        PAL_COLS.append(pcs)
        LOOK_PAL.append([pcs.index(l["cols"]) for l in lk])
    for v in range(10):
        add(f"BOSS{v}", centred(BOSSES[v]))
    roll_ids = []
    for j, text in enumerate(ROLL):
        if text:
            roll_ids.append(len(ROWS))
            add(f"ROLL{j}", centred(text))
        else:
            roll_ids.append(255)
    # the roll's ring: the most tiles 21 consecutive rows need (credits.c CR_AHEAD + 1)
    cnt = [0 if r == 255 else sum(1 for c in ROWS[r][2] if c != 0xFFFF) for r in roll_ids]
    peak = max(sum(cnt[i:i + 21]) for i in range(len(cnt)))
    assert peak <= ROLL_POOL, f"the roll needs {peak} tiles at once, the ring has {ROLL_POOL}"
    # a row with nothing in it (PATB of a venue that does not drop a row) stays out of the tables' way: one blank cell
    n_rows = len(ROWS)
    flat, offs = [], []
    for name, c0, cells in ROWS:
        offs.append(len(flat))
        flat += cells
    pool_b = []
    for t in POOL:
        for y in range(8):
            lo = hi = 0
            for x in range(8):
                lo |= (t[y][x] & 1) << (7 - x)
                hi |= (t[y][x] >> 1) << (7 - x)
            pool_b += [lo, hi]

    def arr(name, vals, ty="uint8_t"):
        return f"static const {ty} {name}[{len(vals)}] = {{ " + ", ".join(str(v) for v in vals) + " };"
    c = ["// generated by tools/gen_credits.py -- do not edit", "#pragma bank 255", "#include <gb/gb.h>", "#include <stdint.h>", '#include "credits_text.h"', "",
         arr("ct_pool", pool_b), arr("ct_off", offs, "uint16_t"), arr("ct_cell", flat, "uint16_t"),
         arr("ct_col", [r[1] for r in ROWS]), arr("ct_len", [len(r[2]) if any(x != 0xFFFF for x in r[2]) else 0 for r in ROWS]), "",
         "// pool tile idx to BG tile `to` (one tile: a library write with the LCD on takes a twentieth of a frame)",
         "void credits_tile_put(uint16_t idx, uint8_t to) BANKED {",
         "    set_bkg_data(to, 1, ct_pool + (idx << 4));", "}", "",
         "// row r's cells: dst[0] the first column, dst[1] the count (0: nothing on the row), then the pool index of each (16 bits, 0xFFFF: empty)",
         "uint8_t credits_row_get(uint8_t r, uint8_t *dst) BANKED {",
         "    uint8_t i, n = ct_len[r];",
         "    uint16_t *d = (uint16_t *)(dst + 2);",
         "    const uint16_t *s = ct_cell + ct_off[r];",
         "    dst[0] = ct_col[r]; dst[1] = n;",
         "    for (i = 0; i != n; i++) d[i] = s[i];",
         "    return n;", "}", ""]
    (out / "credits_text.c").write_text("\n".join(c))
    h = ["// generated by tools/gen_credits.py -- do not edit", "#ifndef CREDITS_TEXT_H", "#define CREDITS_TEXT_H", "#include <stdint.h>", "",
         f"#define CT_POOL_TILES {len(POOL)}   // unique tiles ({len(POOL) * 16} bytes), {n_rows} rows, {len(flat)} cells", f"#define CT_ROWS {n_rows}"]
    for key in ("TITLE", "SAL", "DREGS"):
        h.append(f"#define CT_{key} {ids[key + '0']}   // two rows")
    for key in ("HDR", "OWNER", "PATA", "PATB", "PATC", "BOSS"):
        h.append(f"#define CT_{key} {ids[key + '0']}   // ten rows (a venue each)")
    h += [f"#define CT_SAL_X {pair_x['SAL']}      // the Spigoteer's sprite's left edge (px): sprite, a tile of air and his two lines, centred as a group",
          f"#define CT_DREGS_X {pair_x['DREGS']}",
          "static const uint8_t ct_cx[10][8] = { " + ", ".join("{ " + ", ".join(str(x) for x in c) + " }" for c in pat_cx) + " };   // each patron's centre x (px): over his label",
          f"#define CT_ROLL_N {len(ROLL)}   // the roll's rows", f"#define CT_RING {ROLL_POOL}   // BG tiles for the roll's text at once (peak {peak})", "",
          "static const uint8_t ct_roll[CT_ROLL_N] = { " + ", ".join(str(r) for r in roll_ids) + " };   // each roll row's text row, 255: blank",
          "static const uint8_t ct_slot[10][3] = { " + ", ".join("{ " + ", ".join(str(x) for x in s) + " }" for s in SLOT) + " };   // the patron art variant in each slot",
          "static const uint8_t ct_lp[10][8] = { " + ", ".join("{ " + ", ".join(str(x) for x in lp) + " }" for lp in LOOK_PAL) + " };   // each look's OBJ palette (Color): 1 + the index here (OBJ 0 is the Spigoteer's, kept for the roll)",
          "static const uint16_t ct_pcol[10][7][3] = { " + ", ".join("{ " + ", ".join("{ " + ", ".join(str(c) for c in (pc + [0, 0, 0])[:3]) + " }" for pc in pcs + [[]] * (7 - len(pcs))) + " }" for pcs in PAL_COLS) + " };   // the palettes' colours 1-3 (RGB555, before BRIGHTEN)",
          "void credits_tile_put(uint16_t idx, uint8_t to) BANKED;", "uint8_t credits_row_get(uint8_t r, uint8_t *dst) BANKED;", "#endif", ""]
    (out / "credits_text.h").write_text("\n".join(h))
    js = {"rows": INFO, "ids": ids, "roll": ROLL, "roll_ids": roll_ids, "venues": VENUES, "owners": OWNERS, "bosses": BOSSES, "patrons": PATRONS,
          "slot": SLOT, "pair_x": pair_x, "pat_cx": pat_cx, "look_pal": LOOK_PAL, "pal_cols": PAL_COLS, "pool": len(POOL), "ring_peak": peak, "title": TITLE}
    (out / "credits_text.json").write_text(json.dumps(js, indent=1))
    print(f"credits text: {n_rows} rows, {len(POOL)} tiles ({len(POOL) * 16} bytes) + {len(flat) * 2} bytes of cells, roll peak {peak}/{ROLL_POOL}, one row each")


if __name__ == "__main__":
    main()
