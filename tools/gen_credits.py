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
# The patrons have no names in the game: one short label each (at most 6 letters), three a venue, in the order they STAND (slot A, B, C: left to
# right). SLOT is the patron art variant (art order A, B, C) standing in each slot: only the lumber lodge is reordered (owner 2026-10-17: ASH in the
# middle, so the three labels fit one row): CEDAR (variant A, the cap), ASH (C, the green hat), WILLOW (B, the red-haired one).
PATRONS = [
    ["DUSTY", "ROSIE", "HANK"],              # the saloon: the cowboy, the cowgirl, the ranch hand
    ["PETE", "SERENA", "NORM"],              # the stadium: the cap fan, the band fan, the ref
    ["CEDAR", "ASH", "WILLOW"],              # the lumber lodge
    ["PIERRE", "BRIE", "BASIL"],             # the bistro
    ["IGGY", "POLLY", "MOOSE"],              # the igloo: the parka man, the parka girl, the big parka
    ["BOXY", "VOLTA", "BLIP"],               # the robot factory
    ["SPIKE", "BANDIT", "SLICK"],            # the chrome cow
    ["KAGE", "SAKURA", "RONIN"],             # the teahouse
    ["COCO", "BAMBOO", "MUDDY"],             # the jungle zoo: the monkey, the panda, the hippo
    ["ZORP", "XENO", "GLORP"],               # the space lounge: the green one with eye stalks, the grey one, the squid
]
SLOT = [[0, 1, 2]] * 10
SLOT[2] = [0, 2, 1]
PAL = [list(s) for s in SLOT]             # the palette instance of each slot (Color): the variant's, but the Saloon's C (GUS) wears his own palette,
PAL[0] = [0, 1, 1]                        # EMMA's (owner 2026-10-29); instance 2 is the moss swap he never spawns in

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
    # the three labels of a venue are laid out from their ACTUAL ink widths on one row: the widest gap (at most 24 px, never under a tile) that
    # keeps the whole row inside the screen's edge margins, the row centred; each patron sprite then stands centred over its own label
    pat_cx = []
    for v in range(10):
        labels = PATRONS[v]
        assert all(len(s) <= 6 for s in labels)
        w = [ink_width(t) for t in labels]
        gap = min(24, (160 - 2 * 8 - sum(w)) // 2)
        assert gap >= 8, f"{labels}: the three labels do not fit one row ({sum(w)} px of ink)"
        total = sum(w) + 2 * gap
        x = (160 - total) // 2
        items, cxs = [], []
        for t, wi in zip(labels, w):
            cx = x + wi // 2                    # (the ink's centre; the sprite's 16 px are centred on it)
            items.append((t, cx))
            cxs.append(cx)
            x += wi + gap
        pat_cx.append(cxs)
        add(f"PATA{v}", items)
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
    for key in ("HDR", "OWNER", "PATA", "BOSS"):
        h.append(f"#define CT_{key} {ids[key + '0']}   // ten rows (a venue each)")
    h += [f"#define CT_SAL_X {pair_x['SAL']}      // the Spigoteer's sprite's left edge (px): sprite, a tile of air and his two lines, centred as a group",
          f"#define CT_DREGS_X {pair_x['DREGS']}",
          "static const uint8_t ct_cx[10][3] = { " + ", ".join("{ " + ", ".join(str(x) for x in c) + " }" for c in pat_cx) + " };   // each patron's centre x (px): over his label",
          f"#define CT_ROLL_N {len(ROLL)}   // the roll's rows", f"#define CT_RING {ROLL_POOL}   // BG tiles for the roll's text at once (peak {peak})", "",
          "static const uint8_t ct_roll[CT_ROLL_N] = { " + ", ".join(str(r) for r in roll_ids) + " };   // each roll row's text row, 255: blank",
          "static const uint8_t ct_slot[10][3] = { " + ", ".join("{ " + ", ".join(str(x) for x in s) + " }" for s in SLOT) + " };   // the patron art variant in each slot",
          "static const uint8_t ct_pal[10][3] = { " + ", ".join("{ " + ", ".join(str(x) for x in s) + " }" for s in PAL) + " };   // the palette instance in each slot (Color)",
          "void credits_tile_put(uint16_t idx, uint8_t to) BANKED;", "uint8_t credits_row_get(uint8_t r, uint8_t *dst) BANKED;", "#endif", ""]
    (out / "credits_text.h").write_text("\n".join(h))
    js = {"rows": INFO, "ids": ids, "roll": ROLL, "roll_ids": roll_ids, "venues": VENUES, "owners": OWNERS, "bosses": BOSSES, "patrons": PATRONS,
          "slot": SLOT, "pair_x": pair_x, "pat_cx": pat_cx, "pool": len(POOL), "ring_peak": peak, "title": TITLE}
    (out / "credits_text.json").write_text(json.dumps(js, indent=1))
    print(f"credits text: {n_rows} rows, {len(POOL)} tiles ({len(POOL) * 16} bytes) + {len(flat) * 2} bytes of cells, roll peak {peak}/{ROLL_POOL}, one row each")


if __name__ == "__main__":
    main()
