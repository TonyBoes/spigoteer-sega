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
import os
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



def resolve_scroll(text):
    """The credits are the scrolling ones only: keep the scrolling side of the generator's #ifdef CREDITS_SCROLL blocks (the card build is gone)."""
    out, state = [], None
    for line in text.split("\n"):
        s = line.strip()
        if s.startswith("#ifdef CREDITS_SCROLL") or s.startswith("#ifndef CREDITS_SCROLL"):
            state = [s.startswith("#ifdef"), False]
            continue
        if state is not None:
            if s.startswith("#else"):
                state[1] = True
                continue
            if s.startswith("#endif"):
                state = None
                continue
            if state[0] != state[1]:
                out.append(line)
            continue
        out.append(line)
    return "\n".join(out)

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
# CREDITS=SCROLL's layout (rows of the world; credits.c uses these through credits_text.h). G: the gap between blocks (a card's top rows and the cards' own blank rows
# included in the heights); LG: the larger gap before a venue's divider (blank rows at the top of its owner card). Stops (the block centred on the screen) are at OFF px from the card's top.
LAY_G, LAY_LG = 2, 12
# Owner 2026-11-13: no spigot icon over a venue's title ("It just reads as garbage scrolling by so fast"), and no REGULARS or BOSS label ("That's implied"): the band
# is where the divider was (the venue's card is 3 rows shorter), the first line of patrons' names is on row R_PA (the label's 2 rows and the blank above it are gone: the card
# is 2 rows shorter), the boss is 3 rows up (H_BOSS 11). R_DIV is the card's row its loads wait for (credits.c cr_lrow), no longer a drawn row.
LAY = dict(G=LAY_G, LG=LAY_LG, MAPFMT=0, FONTFMT=0, H_TITLE=3, GAP_TITLE=8, H_SD=16, R_DIV=LAY_LG, R_BAND=LAY_LG, R_OLBL=LAY_LG + 5, R_PORT=LAY_LG + 7, R_ONAME=LAY_LG + 15,
           H_OWN=LAY_LG + 16, R_PA=3, R_PN=5, H_PAT=14, R_BBODY=3, R_BNAME=7, H_BOSS=11,
           OFF_TITLE=12, OFF_SD=52, OFF_OWN=8 * (LAY_LG + 8), OFF_PAT=56, OFF_BOSS=40)
LABELS = ["OWNER"]
# Proposals, off by default (owner 2026-11-13, nothing goes into the default build until he picks): make BUILD=out/b_crA OUT=out/o_crA CRFONT=A CRMAP=A unlocked
#   CRFONT=A  the venue's name in the HUD font as the story map's panel and the menus set it, 8x8, on the 3-row stripe (middle row)
#   CRFONT=B  the same, on a 1-row stripe (the story map's chapter tag: a ribbon), the stripe's other two rows blank
#   CRMAP=B   a title page of its own for each venue (a card before the owner's): the WHOLE building from the story map on the left, the name beside it (2-3 short lines on a stripe)
CRFONT = os.environ.get("CRFONT", "")
CRMAP = os.environ.get("CRMAP", "")
CRSCENE = os.environ.get("CRSCENE", "")       # 1: the owner scene pages (the artist's round 6, tools/gen_scene_pages.py) replace the OWNER card
assert CRSCENE in ("", "1"), CRSCENE
CRFLOW = os.environ.get("CRFLOW", "")       # SMOOTH: no stops: the whole credits move up at one constant speed, set from the tune's length (owner 2026-11-13: "all one long smooth scroll matched to the song length")
assert CRFLOW in ("", "SMOOTH"), CRFLOW
assert CRFONT in ("", "A", "B") and CRMAP in ("", "B"), (CRFONT, CRMAP)
# The whole buildings of the story map (assets/smap/world_c.png), venue order: (col, row, width, height) in the map's cells, every tile of the building (sign, roof, base, its own ground line;
# the Chrome Cow's milk tank and parked bikes, the factory's roof crates, the space lounge's tower, plane and runway). Neighbouring trees, piles and roads are left out.
SCENE_PALS = 7                                      # the BG palettes a scene may use on Color: slots 2, 3, 4, 6, 7, then 5 and 1 (credits.c cr_scene_slot)
SLOT5_ROW, SLOT1_ROW = 4, 7                         # the first scene row a palette may have cells in, to go in slot 5 / slot 1 (the rows enter after the previous boss's body / name have scrolled off)
VGAP = {0: 20}                                      # the blank rows above a venue's scene (7 after a boss; 20 after Dregs, whose portrait uses BG 5-7)
VGAP_DEF = 7
SCENE_W, SCENE_H = 16, 12                           # every venue's picture: this many cells of the map (the stadium, the largest building, is 12 x 10), the building inside it
SCENE_AT = {9: (3, 36)}                             # (the scene's first cell where it is not centred on the building: the Space Lounge's shows its UFO and the mountain)
BUILD_BOX = {0: (3, 21, 9, 7), 1: (1, 1, 12, 10), 2: (54, 20, 6, 7), 3: (20, 4, 9, 7), 4: (51, 5, 8, 7), 5: (52, 36, 10, 9), 6: (50, 55, 12, 9), 7: (24, 55, 10, 7), 8: (6, 54, 8, 7), 9: (4, 36, 7, 7)}
if CRMAP:                  # the venue's card (CK_VENUE) takes the band; the owner's card starts at OWNER; the venue card's rows are LG blank, the building (BH rows), VPAD blank
    LAY.update(R_OLBL=0, R_PORT=2, R_ONAME=10, H_OWN=11, R_DIV=6, OFF_OWN=8 * 5 + 4, VPAD=16)
LAY["MAPFMT"] = {"": 0, "B": 2}[CRMAP]
LAY["FLOWFMT"] = {"": 0, "SMOOTH": 1}[CRFLOW]
LAY["SCENEFMT"] = 1 if CRSCENE else 0
SGT, SGB = 26, 24                                   # CRSCENE: blank rows above and below a scene page (18 rows: the screen): the cards before and after are off the screen while its palettes are in
if CRSCENE:
    LAY.update(R_OLBL=0, R_PORT=2, R_ONAME=10, H_OWN=SGT + 18 + SGB, R_DIV=6, OFF_OWN=8 * SGT + 72, SGT=SGT, SGB=SGB)
LAY["FONTFMT"] = {"": 0, "A": 1, "B": 2}[CRFONT]
BAND_H = 24                                          # the venue band: 3 rows, the name's 8x16 letters centred in it
SCROLL_RING = 127                                    # the text ring of the cast (credits.c): DMG BG ids 204-255 + 0-75 but 54, Color VRAM bank 1 ids 0-126
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


def cut_row(name, full, bg, store):
    """The 20 cells of a row image (8 pixel rows of 160), the cells that are all `bg` dropped at the ends (and as 0xFFFF inside); one ROWS entry."""
    tiles = []
    for tx in range(20):
        blank = all(full[y][tx * 8 + x] == bg for y in range(8) for x in range(8))
        tiles.append(None if blank else tile_of(full, tx))
    live = [i for i, t in enumerate(tiles) if t is not None]
    c0, c1 = (live[0], live[-1]) if live else (0, -1)
    cells = [0xFFFF if t is None else t for t in tiles[c0:c1 + 1]]
    ROWS.append((name, c0, cells))
    store[name] = {"col": c0, "n": len(cells), "cells": cells}
    return store[name]


def row(name, items, edge=8, inkmap=None, store=None):
    """A row of the screen: items = [(text, centre x)] (text: a string, or (pixel rows, ink x0, x1) of a picture). The ink of each is centred on its x (to the
    pixel: the half pixel goes left); the tiles cut, the empty ones at the ends dropped. inkmap: the ink's colours changed (the labels'). Returns the ink boxes."""
    full = [[BAND] * 160 for _ in range(8)]
    boxes = []
    for text, cx in items:
        px, x0, x1 = strip(text) if isinstance(text, str) else text
        dx = cx - (x0 + x1 + 1) // 2
        assert x0 + dx >= edge and x1 + dx < 160 - edge, f"{name}: {text!r} reaches the screen's edge ({x0 + dx}..{x1 + dx})"
        for y in range(8):
            for x in range(len(px[0])):
                if px[y][x] != BAND:
                    full[y][x + dx] = (inkmap or {}).get(px[y][x], px[y][x])
        boxes.append((text if isinstance(text, str) else name, x0 + dx, x1 + dx))
    e = cut_row(name, full, BAND, INFO if store is None else store)
    e["ink"] = [{"text": t, "x0": a, "x1": b} for t, a, b in boxes]
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
    # the scroll variant's roll (owner 2026-11-05): every line of an entry has its own blank row after it (a 16 px pitch: the 7 px letters nearly touched at 8),
    # the gaps between entries as they are; the same text rows, so no new tiles
    roll2 = []
    for j, r in enumerate(roll_ids):
        roll2.append(r)
        if r != 255 and j + 1 < len(roll_ids) and roll_ids[j + 1] != 255:
            roll2.append(255)
    BAND_ROW = 14                                                  # (credits.c CR_BAND in the default roll: the sprites' band)
    band2 = sum(2 if (roll_ids[k] != 255 and k + 1 < len(roll_ids) and roll_ids[k + 1] != 255) else 1 for k in range(BAND_ROW))
    cnt2 = [0 if r == 255 else sum(1 for c in ROWS[r][2] if c != 0xFFFF) for r in roll2]
    peak2 = max(sum(cnt2[i:i + 21]) for i in range(len(cnt2)))
    assert peak2 <= ROLL_POOL, f"the scroll's roll needs {peak2} tiles at once, the ring has {ROLL_POOL}"
    # ---- CREDITS=SCROLL's own rows (appended after every other row: the default build's tables are the same without them; emitted inside #ifdef CREDITS_SCROLL) ----
    n_base_rows, n_base_pool = len(ROWS), len(POOL)
    EXTRA = {}
    ids["LBL0"] = len(ROWS)
    for t in LABELS:                                  # the labels: the small font, the ink one shade on (DMG light grey, Color the venue palette 0's gold), centred
        row("LBL_" + t, centred(t), inkmap={0: 1}, store=EXTRA)
    ids["BAND0"] = len(ROWS)
    for v in range(10):                               # the venue band: the name's letters 8 px wide, 16 tall, on a stripe (colour 2); three rows of tiles
        px, x0, x1 = strip(VENUES[v])
        dx = 80 - (x0 + x1 + 1) // 2
        assert x0 + dx >= 8 and x1 + dx < 152, (VENUES[v], x0 + dx, x1 + dx)
        img = [[2] * 160 for _ in range(BAND_H)]
        if CRFONT:                                    # the HUD font as it is (8x8, the pixel rows as drawn), on the middle row of the stripe
            for y in range(8):
                for x in range(len(px[0])):
                    if px[y][x] != BAND:
                        img[8 + y][x + dx] = px[y][x]
        else:
            big = [px[y // 2] for y in range(16)]
            ys = [y for y in range(16) if any(c != BAND for c in big[y])]
            top = (BAND_H - (ys[-1] - ys[0] + 1)) // 2 - ys[0]
            for y in range(16):
                for x in range(len(px[0])):
                    if big[y][x] != BAND:
                        img[y + top][x + dx] = big[y][x]
        for j in range(3):
            cut_row(f"BAND{v}_{j}", img[8 * j:8 * j + 8], 2, EXTRA)
    stripe = tile_of([[2] * 160 for _ in range(8)], 0)
    CH = []
    SCN = []                                          # CRSCENE: per (venue, model) the page's data for the engine
    if CRSCENE:
        import gen_scene_pages as GSP
        ids["BLD0"] = len(ROWS)
        POOL_BLD0 = len(POOL)
        solid = [tile_of([[k] * 160 for _ in range(8)], 0) for k in range(4)]     # (the four flat tiles: BG ids 77-80 on both machines, loaded once)
        ids["SOLID"] = solid
        ids["SCN0"] = len(ROWS)

        def lum(h):
            r_, g_, b_ = (int(h[k:k + 2], 16) for k in (1, 3, 5))
            return 3 * r_ + 6 * g_ + b_

        for v in range(10):
            if v in (0, 4, 7):
                CH.append((POOL_BLD0, ids["BLD0"]) if v == 0 else (len(POOL), len(ROWS)))        # (three bank files: a bank holds 16 KB)
            vd = GSP.F.VENUES[v]
            for m in (0, 1):
                sc = GSP.scene(vd, bool(m))
                stage = sc["stage"]
                ink = 0 if lum(stage[0]) >= lum(stage[1]) else 1       # the stage palette's lighter of colours 0 and 1 is the band's and the name's ink on Color (its colour 2 is the band, 3 the page)
                inkv = ink if m else None
                slot_of = {}
                bpl = 7 if (m and vd.key == "biker") else 0       # the band and the name: the stage palette (slot 0); the Chrome Cow's band is its bar's magenta, which BG 7 holds as colour 2 (the artist's VENUE_BAND)
                if bpl:
                    assert sc["pals"][7][2] == "#a03070" and sc["pals"][7][1], sc["pals"][7]
                px_, x0_, x1_ = strip(VENUES[v])
                dxb = 80 - (x0_ + x1_ + 1) // 2
                big = [px_[y // 2] for y in range(16)]
                ys = [y for y in range(16) if any(c != BAND for c in big[y])]
                topb = (BAND_H - (ys[-1] - ys[0] + 1)) // 2 - ys[0]
                band = [[2] * 160 for _ in range(BAND_H)]
                for y in range(16):
                    for x in range(len(px_[0])):
                        if big[y][x] != BAND:
                            band[y + topb][x + dxb] = big[y][x] if inkv is None else inkv
                npx, nx0, nx1 = strip(OWNERS[v])
                dxn = 80 - (nx0 + nx1 + 1) // 2
                for j in range(1, 18):
                    full = [[BAND] * 160 for _ in range(8)]
                    specs = [None] * 20
                    if 1 <= j <= 3:
                        full = [list(rw) for rw in band[8 * (j - 1):8 * j]]
                        auto = True
                    elif j == 17:
                        for y in range(8):
                            for x in range(len(npx[0])):
                                if npx[y][x] != BAND:
                                    full[y][x + dxn] = npx[y][x] if inkv is None else inkv
                        auto = True
                    else:
                        auto = False
                        for tx_, c in enumerate(sc["cells"][j - 4]):
                            if c is None:
                                continue
                            specs[tx_] = c
                            if c[0] == "t":
                                for y in range(8):
                                    for x in range(8):
                                        full[y][8 * tx_ + x] = c[1][y][x]
                            else:
                                for y in range(8):
                                    for x in range(8):
                                        full[y][8 * tx_ + x] = c[1]
                    cells = []
                    for tx_ in range(20):
                        flat = {p for y in range(8) for p in full[y][8 * tx_:8 * tx_ + 8]}
                        if auto:
                            pl = bpl
                            if flat == {3}:
                                cells.append(0xFFFF)
                                continue
                            if flat == {2}:
                                cells.append(0xF000 | bpl << 8 | 2)
                                continue
                        else:
                            if specs[tx_] is None:
                                cells.append(0xFFFF)
                                continue
                            pl = specs[tx_][2]
                            if specs[tx_][0] == "f":
                                cells.append(0xF000 | pl << 8 | specs[tx_][1])
                                continue
                        ti = tile_of(full, tx_)
                        assert ti < 4096
                        if ti in slot_of:
                            cells.append(0xE000 | pl << 8 | slot_of[ti])
                        else:
                            slot_of[ti] = len(slot_of)
                            cells.append(ti | pl << 12)
                    live = [k for k, c in enumerate(cells) if c != 0xFFFF]
                    a0, a1 = (live[0], live[-1]) if live else (0, -1)
                    cl = cells[a0:a1 + 1]
                    ROWS.append((f"SCN{v}_{m}_{j}", a0, cl))
                    EXTRA[f"SCN{v}_{m}_{j}"] = {"col": a0, "n": len(cl), "cells": cl}
                SCN.append(dict(v=v, m=m, sc=sc, ink=ink, su=list(slot_of)))
    BLD_COL, BLD_INFO, SCENE_REPORT, NPALS = [], [], [], []                       # each venue's building palette: the story map's palette of the building's cells (the commonest), colours light to dark
    if CRMAP:
        from PIL import Image
        wj = json.loads((ROOT / "assets/smap/world.json").read_text())
        wim = Image.open(ROOT / "assets/smap/world_c.png")
        ids["BLD0"] = len(ROWS)
        POOL_BLD0 = len(POOL)
        solid = [tile_of([[k] * 160 for _ in range(8)], 0) for k in range(4)]     # (the four flat tiles: BG ids 77-80 on both machines, loaded once)
        ids["SOLID"] = solid
        for v in range(10):
            if v == 5:
                POOL_SPLIT, ROW_SPLIT = len(POOL), len(ROWS)    # (venues 0-4 in credits_text2.c, 5-9 in credits_text3.c: a bank holds 16 KB)
            c0, r0, bwc, bhc = BUILD_BOX[v]
            bx0, by0 = SCENE_AT.get(v, (c0 + bwc // 2 - SCENE_W // 2, r0 + bhc // 2 - SCENE_H // 2))
            bx0 = max(0, min(wj["cw"] - SCENE_W, bx0))
            by0 = max(0, min(wj["ch"] - SCENE_H, by0))
            pals = {}
            for cy in range(SCENE_H):
                for cx in range(SCENE_W):
                    pn = wj["pal_names"][ord(wj["cell_pal"][by0 + cy][bx0 + cx]) - 48]
                    pals[pn] = pals.get(pn, 0) + 1
            order = sorted(pals, key=lambda k: -pals[k])
            minrow = {}
            for cy in range(SCENE_H):
                for cx in range(SCENE_W):
                    nm_ = wj["pal_names"][ord(wj["cell_pal"][by0 + cy][bx0 + cx]) - 48]
                    minrow[nm_] = min(minrow.get(nm_, 99), cy)

            def pcol(nm):
                return wj["pal_rgb"][nm]
            # BG slots of a scene's palettes (credits.c cr_scene_slot): 2, 3, 4, 6, 7 free when the scene is loaded, then 5 (the previous boss's: written when his body rows have scrolled off the
            # top) and 1 (the HUD's: when his name has), so a palette that goes there must have no cell above SLOT5_ROW / SLOT1_ROW (the scene's rows that enter only after that)
            extras = []
            rest = list(order)
            for want in ([] if len(order) <= 5 else [SLOT5_ROW] if len(order) == 6 else [SLOT1_ROW, SLOT5_ROW]):
                cand = [nm for nm in reversed(rest) if minrow[nm] >= want]
                assert cand, (VENUES[v], "no palette fits slot", want, minrow)
                extras.append(cand[0])
                rest.remove(cand[0])
            kept = rest + extras[::-1]                    # indices 0-4 the free slots (the commonest first), then slot 5's palette, then slot 1's
            SCENE_REPORT.append((VENUES[v], len(order), {"slot 5": extras[-1] if extras else None, "slot 1": extras[0] if len(extras) > 1 else None}))
            remap = {nm: nm for nm in order}
            slot_pal = {nm: k for k, nm in enumerate(kept)}                       # the scene's palette number of each map palette
            BLD_COL.append([[rgb555("#%02x%02x%02x" % tuple(c)) for c in pcol(nm)] for nm in kept] + [[0, 0, 0, 0]] * (SCENE_PALS - len(kept)))
            NPALS.append(len(kept))
            # the scene: ONE size for every venue (SCENE_W x SCENE_H cells of the map), the building in it with the map's own ground and props around it (map pixels only); the name on a stripe under it
            assert bx0 <= c0 and c0 + bwc <= bx0 + SCENE_W and by0 <= r0 and r0 + bhc <= by0 + SCENE_H, (VENUES[v], "the building is not inside its scene")
            bpx = [[wim.getpixel((bx0 * 8 + x, by0 * 8 + y)) for x in range(8 * SCENE_W)] for y in range(8 * SCENE_H)]   # the map's own pixels, indices 0-3 light to dark
            bc0 = (20 - SCENE_W) // 2
            name = VENUES[v]
            tx, t0, t1 = strip(name)
            assert t1 - t0 + 1 <= 152, (name, t1 - t0 + 1)
            ids_first = len(ROWS)
            slot_of = {}                                   # a tile of the scene is put in the ring once: its later cells name that slot (0xFE00 + the slot's number in the scene)
            for j in range(SCENE_H + 1):
                full = [[BAND] * 160 for _ in range(8)]
                if j < SCENE_H:
                    for y in range(8):
                        for x in range(8 * SCENE_W):
                            full[y][8 * bc0 + x] = bpx[8 * j + y][x]
                else:
                    for y in range(8):
                        full[y] = [2] * 160
                    cxm = 80 - (t0 + t1 + 1) // 2
                    for y in range(8):
                        for x in range(len(tx[0])):
                            if tx[y][x] != BAND:
                                full[y][x + cxm] = tx[y][x]
                cells = []
                for tx_ in range(20):
                    px_ = [full[y][8 * tx_:8 * tx_ + 8] for y in range(8)]
                    flat = {p for rw in px_ for p in rw}
                    mc = bx0 + tx_ - bc0
                    sp = slot_pal[remap[wj["pal_names"][ord(wj["cell_pal"][by0 + j][mc]) - 48]]] if (j < SCENE_H and 0 <= tx_ - bc0 < SCENE_W) else 0    # the cell's scene palette
                    if j < SCENE_H and bc0 <= tx_ < bc0 + SCENE_W and len(flat) == 1:
                        cells.append(0xF000 | sp << 8 | flat.pop())             # a flat tile of the scene (the ground's colour above all): a fixed BG tile, no ring slot
                    elif len(flat) == 1 and flat == ({2} if j == SCENE_H else {BAND}):
                        cells.append(0xFFFF)                                     # the stripe (prefilled) or the page
                    else:
                        ti = tile_of(full, tx_)
                        assert ti < 4096
                        if ti in slot_of:
                            cells.append(0xE000 | sp << 8 | slot_of[ti])        # (the slot's tile is in the ring already: this cell only names it, with its own palette)
                        else:
                            slot_of[ti] = len(slot_of)
                            cells.append(ti | sp << 12)
                live = [k for k, c in enumerate(cells) if c != 0xFFFF]
                a0, a1 = (live[0], live[-1]) if live else (0, -1)
                cl = cells[a0:a1 + 1]
                ROWS.append((f"BLD{v}_{j}", a0, cl))
                EXTRA[f"BLD{v}_{j}"] = {"col": a0, "n": len(cl), "cells": cl}
            BLD_INFO.append((ids_first - ids["BLD0"], SCENE_H + 1, SCENE_H, 1, bc0, 0, [name]))
    # the stripe's colour on Color: the venue's stage palette colour 2 (biker: its bar's colour 2, the stage's is a bright green)
    vd = ROOT / "assets/approved/venues"
    band_col = []
    for t in ["saloon", "sports", "lodge", "bistro", "igloo", "factory", "biker", "teahouse", "zoo", "space"]:
        pj = json.loads((vd / f"{t}_pal.json").read_text())
        band_col.append(rgb555(pj["bar"]["hex"][2] if t == "biker" else pj["stage_a"]["hex"][2]))
    # the cast's text ring: the most tiles any 32 consecutive world rows hold (credits.c builds up to 30 rows ahead of the screen's top)
    L = LAY
    def n(name):
        return sum(1 for c in EXTRA.get(name, INFO.get(name))["cells"] if c < 0xE000)
    world = {}
    def put(y, name):
        world[y] = world.get(y, 0) + n(name)
    y0 = 8
    def card(h, g):
        nonlocal y0
        c0 = y0
        y0 += h + g
        return c0
    c0 = card(L["H_TITLE"], L["GAP_TITLE"]); put(c0, "TITLE0"); put(c0 + 2, "TITLE1")
    for key in ("SAL", "DREGS"):
        c0 = card(L["H_SD"], L["G"]); put(c0 + 10, key + "0"); put(c0 + 12, key + "1")
    peaks = {}
    for dmg in (0, 1):
        world_d = dict(world)
        yy = y0
        cnt = dict(world)
        for v in range(10):
            if CRMAP:
                items = [(VGAP.get(v, VGAP_DEF) + jj, f"BLD{v}_{jj}") for jj in range(BLD_INFO[v][1])]
                for off, name in items:
                    cnt[yy + off] = cnt.get(yy + off, 0) + n(name)
                yy += VGAP.get(v, VGAP_DEF) + BLD_INFO[v][1] + L["VPAD"] + L["G"]
                items = [(L["R_OLBL"], "LBL_OWNER"), (L["R_ONAME"], f"OWNER{v}")]
            elif CRSCENE:
                items = [(SGT + j, f"SCN{v}_{0 if dmg else 1}_{j}") for j in range(1, 18)]
            else:
                items = [(L["R_BAND"] + j, f"BAND{v}_{j}") for j in range(3)] + [(L["R_OLBL"], "LBL_OWNER"), (L["R_ONAME"], f"OWNER{v}")]
            for off, name in items:
                cnt[yy + off] = cnt.get(yy + off, 0) + n(name)
            yy += L["H_OWN"] + L["G"]
            for k, nm in enumerate("ABC"):
                if dmg and k != 1:
                    continue
                cnt[yy + L["R_PA"] + L["R_PN"] * k] = n(f"PAT{nm}{v}")
            yy += L["H_PAT"] + L["G"]
            cnt[yy + L["R_BNAME"]] = n(f"BOSS{v}")
            yy += L["H_BOSS"] + L["G"]
        top = max(cnt)
        peaks[dmg] = max(sum(cnt.get(a + i, 0) for i in range(32)) for a in range(0, top))
    assert max(peaks.values()) <= SCROLL_RING, f"the scroll's cast needs {peaks} text tiles at once, the ring has {SCROLL_RING}"
    n_all_rows = len(ROWS)
    bp, br = (POOL_BLD0, ids["BLD0"]) if (CRMAP or CRSCENE) else (len(POOL), len(ROWS))      # CRMAP: the buildings' tiles and rows are a second file (a bank of their own: the first would hold 20 KB)
    # (the default build's tables end at n_base_rows / n_base_pool)
    n_rows = n_base_rows
    flat, offs = [], []
    for name, c0, cells in ROWS:
        offs.append(len(flat))
        flat += cells
    n_flat_base = offs[n_base_rows]
    pool_b = []
    for t in POOL:
        for y in range(8):
            lo = hi = 0
            for x in range(8):
                lo |= (t[y][x] & 1) << (7 - x)
                hi |= (t[y][x] >> 1) << (7 - x)
            pool_b += [lo, hi]
    flat_all = flat
    flat = flat_all[:n_flat_base]
    f_br = offs[br] if br < len(offs) else len(flat_all)

    def arr(name, vals, ty="uint8_t"):
        return f"static const {ty} {name}[{len(vals)}] = {{ " + ", ".join(str(v) for v in vals) + " };"

    lens = [len(r[2]) if any(x != 0xFFFF for x in r[2]) else 0 for r in ROWS]
    c = ["// generated by tools/gen_credits.py -- do not edit", "#pragma bank 255", "#include <gb/gb.h>", "#include <stdint.h>", '#include "credits_text.h"', "",
         arr("ct_pool", pool_b[:n_base_pool * 16]), arr("ct_off", offs[:n_base_rows], "uint16_t"), arr("ct_cell", flat, "uint16_t"),
         arr("ct_col", [r[1] for r in ROWS[:n_base_rows]]), arr("ct_len", lens[:n_base_rows]), "",
         "#ifdef CREDITS_SCROLL   // the scrolling credits' own rows and tiles (after the others': the default build does not have them)",
         arr("ct_pool2", pool_b[n_base_pool * 16:bp * 16]), arr("ct_off2", [o - n_flat_base for o in offs[n_base_rows:br]], "uint16_t"), arr("ct_cell2", flat_all[n_flat_base:f_br], "uint16_t"),
         arr("ct_col2", [r[1] for r in ROWS[n_base_rows:br]]), arr("ct_len2", lens[n_base_rows:br]), "#endif", "",
         "// pool tile idx to BG tile `to` (one tile: a library write with the LCD on takes a twentieth of a frame)",
         "void credits_tile_put(uint16_t idx, uint8_t to) BANKED {",
         "#ifdef CREDITS_SCROLL",
         (f"    if (idx >= {POOL_SPLIT}) {{ credits_tile_put4(idx - {POOL_SPLIT}, to); return; }}\n    if (idx >= {bp}) {{ credits_tile_put3(idx - {bp}, to); return; }}" if CRMAP else ""),
         ("\n".join(f"    if (idx >= {CH[k][0]}) {{ credits_tile_put{3 + k}(idx - {CH[k][0]}, to); return; }}" for k in (2, 1, 0)) if CRSCENE else ""),
         f"    if (idx >= {n_base_pool}) {{ set_bkg_data(to, 1, ct_pool2 + ((idx - {n_base_pool}) << 4)); return; }}",
         "#endif",
         "    set_bkg_data(to, 1, ct_pool + (idx << 4));", "}", "",
         "// row r's cells: dst[0] the first column, dst[1] the count (0: nothing on the row), then the pool index of each (16 bits, 0xFFFF: empty)",
         "uint8_t credits_row_get(uint16_t r, uint8_t *dst) BANKED {",
         "    uint8_t i, n;",
         "    uint16_t *d = (uint16_t *)(dst + 2);",
         "    const uint16_t *s;",
         "#ifdef CREDITS_SCROLL",
         (f"    if (r >= {ROW_SPLIT}) return credits_row_get4(r - {ROW_SPLIT}, dst);\n    if (r >= {br}) return credits_row_get3(r - {br}, dst);" if CRMAP else ""),
         ("\n".join(f"    if (r >= {CH[k][1]}) return credits_row_get{3 + k}(r - {CH[k][1]}, dst);" for k in (2, 1, 0)) if CRSCENE else ""),
         f"    if (r >= {n_base_rows}) {{",
         f"        r -= {n_base_rows};",
         "        n = ct_len2[r]; s = ct_cell2 + ct_off2[r]; dst[0] = ct_col2[r]; dst[1] = n;",
         "        for (i = 0; i != n; i++) d[i] = s[i];",
         "        return n;",
         "    }",
         "#endif",
         "    n = ct_len[r]; s = ct_cell + ct_off[r];",
         "    dst[0] = ct_col[r]; dst[1] = n;",
         "    for (i = 0; i != n; i++) d[i] = s[i];",
         "    return n;", "}", ""]
    (out / "credits_text.c").write_text(resolve_scroll("\n".join(c)))
    if CRMAP or CRSCENE:
        def bld_file(name, tag, p0, p1, r0_, r1_):
            f0, f1 = offs[r0_], (offs[r1_] if r1_ < len(offs) else len(flat_all))
            c3 = ["// generated by tools/gen_credits.py -- do not edit (CRMAP: the buildings' scenes, a bank of their own)", "#pragma bank 255", "#include <gb/gb.h>", "#include <stdint.h>", '#include "credits_text.h"', "",
                  arr("ct_pool" + tag, pool_b[p0 * 16:p1 * 16]), arr("ct_off" + tag, [o - f0 for o in offs[r0_:r1_]], "uint16_t"), arr("ct_cell" + tag, flat_all[f0:f1], "uint16_t"),
                  arr("ct_col" + tag, [r[1] for r in ROWS[r0_:r1_]]), arr("ct_len" + tag, lens[r0_:r1_]), "",
                  f"void credits_tile_put{tag}(uint16_t idx, uint8_t to) BANKED {{ set_bkg_data(to, 1, ct_pool{tag} + (idx << 4)); }}", "",
                  f"uint8_t credits_row_get{tag}(uint8_t r, uint8_t *dst) BANKED {{", f"    uint8_t i, n = ct_len{tag}[r];", "    uint16_t *d = (uint16_t *)(dst + 2);", f"    const uint16_t *s = ct_cell{tag} + ct_off{tag}[r];",
                  f"    dst[0] = ct_col{tag}[r]; dst[1] = n;", "    for (i = 0; i != n; i++) d[i] = s[i];", "    return n;", "}", ""]
            (out / name).write_text("\n".join(c3))
        if CRMAP:
            bld_file("credits_text2.c", "3", bp, POOL_SPLIT, br, ROW_SPLIT)
            bld_file("credits_text3.c", "4", POOL_SPLIT, len(POOL), ROW_SPLIT, len(ROWS))
    if CRSCENE:
        ends = CH[1:] + [(len(POOL), len(ROWS))]
        for k in range(3):
            bld_file(f"credits_text{2 + k}.c", str(3 + k), CH[k][0], ends[k][0], CH[k][1], ends[k][1])
    if CRSCENE:
        tl, tof, tn, meta, moff, bgp, opp = [], [], [], [], [], [], []
        su, suoff = [], []                                  # each page's tiles in the order its rows first use them (v * 2 + model): the engine puts them in the ring before the rows are built

        def t2(grid):
            out_ = []
            for y in range(8):
                lo = hi = 0
                for x in range(8):
                    lo |= (grid[y][x] & 1) << (7 - x)
                    hi |= (grid[y][x] >> 1) << (7 - x)
                out_ += [lo, hi]
            return out_
        for e in SCN:
            suoff.append(len(su))
            su += e["su"]
            if e["m"] != 1:
                continue
            sc = e["sc"]
            tof.append(len(tl))
            for o in sc["objs"]:
                tl += t2(o["top"]) + (t2(o["bot"]) if o["bot"] else [0] * 16)
            tn.append(len(sc["objs"]) * 2)
            moff.append(len(meta))
            assert len(sc["objs"]) <= 40 and len(sc["opals"]) <= 7, (e["v"], len(sc["objs"]), len(sc["opals"]))
            meta += [len(sc["objs"]), len(sc["opals"]), len(sc["objs"]) * 2]
            for k, o in enumerate(sc["objs"]):
                meta += [o["x"] + 8, o["y"], 2 * k, ((1 + o["pal"]) & 7) | o["obp"] << 4]
            assert len(sc["pals"]) <= 8, (e["v"], "BG palettes", len(sc["pals"]))
            for k in range(8):
                pp = sc["pals"][k] if k < len(sc["pals"]) else [None] * 4
                bgp += [rgb555(h_) if h_ else 0 for h_ in pp]
            for k in range(7):
                pp = sc["opals"][k] if k < len(sc["opals"]) else [None] * 3
                opp += [rgb555(h_) if h_ else 0 for h_ in pp]
        sf = ["// generated by tools/gen_credits.py -- do not edit (CRSCENE: the scene pages' sprites, tiles and palettes)", "#pragma bank 255", "#include <gb/gb.h>", "#include <stdint.h>", '#include "credits_text.h"', "",
              arr("ct_stile", tl), arr("ct_stoff", tof, "uint16_t"), arr("ct_smeta", meta), arr("ct_smoff", moff, "uint16_t"), arr("ct_sbg", bgp, "uint16_t"), arr("ct_sop", opp, "uint16_t"), arr("ct_su", su, "uint16_t"), arr("ct_suoff", suoff + [len(su)], "uint16_t"), "",
              "// kind 0: object tile i (16 bytes); 1: BG palette i (4 words); 2: OBJ palette i (3 words: colours 1-3); 3: the scene's meta (n objects, OBJ palettes, tiles, then x, y in the picture, tile, flags a object); returns the tile count",
              "uint8_t credits_scene_get(uint8_t v, uint8_t kind, uint8_t i, uint8_t *dst) BANKED {",
              "    uint8_t k, n;", "    const uint8_t *s;",
              "    if (kind == 0) { s = ct_stile + ct_stoff[v] + ((uint16_t)i << 4); for (k = 0; k != 16; k++) dst[k] = s[k]; return 0; }",
              "    if (kind == 1) { s = (const uint8_t *)(ct_sbg + v * 32 + i * 4); for (k = 0; k != 8; k++) dst[k] = s[k]; return 0; }",
              "    if (kind == 2) { s = (const uint8_t *)(ct_sop + v * 21 + i * 3); for (k = 0; k != 6; k++) dst[k] = s[k]; return 0; }",
              "    if (kind == 4) { n = (uint8_t)(ct_suoff[v + 1] - ct_suoff[v]); if (i < n) { dst[0] = (uint8_t)ct_su[ct_suoff[v] + i]; dst[1] = (uint8_t)(ct_su[ct_suoff[v] + i] >> 8); } return n; }",
              "    s = ct_smeta + ct_smoff[v]; n = 3 + 4 * s[0]; k = s[2]; s += (uint16_t)i << 5;   // (32 bytes a call: a unit of the credits' loads is a fraction of a frame)",
              "    n -= i << 5; if (n > 32) n = 32;", "    for (i = 0; i != n; i++) dst[i] = s[i];", "    return k;", "}", ""]
        (out / "credits_scene.c").write_text("\n".join(sf))
    h = ["// generated by tools/gen_credits.py -- do not edit", "#ifndef CREDITS_TEXT_H", "#define CREDITS_TEXT_H", "#include <stdint.h>", "",
         f"#define CT_POOL_TILES {n_base_pool}   // unique tiles ({n_base_pool * 16} bytes), {n_rows} rows, {len(flat)} cells", f"#define CT_ROWS {n_rows}"]
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
          "void credits_tile_put(uint16_t idx, uint8_t to) BANKED;", "uint8_t credits_row_get(uint16_t r, uint8_t *dst) BANKED;", "void credits_tile_put3(uint16_t idx, uint8_t to) BANKED;", "uint8_t credits_row_get3(uint8_t r, uint8_t *dst) BANKED;", "void credits_tile_put4(uint16_t idx, uint8_t to) BANKED;", "uint8_t credits_row_get4(uint8_t r, uint8_t *dst) BANKED;", "void credits_tile_put5(uint16_t idx, uint8_t to) BANKED;", "uint8_t credits_row_get5(uint8_t r, uint8_t *dst) BANKED;", "void credits_tile_put6(uint16_t idx, uint8_t to) BANKED;", "uint8_t credits_row_get6(uint8_t r, uint8_t *dst) BANKED;", "uint8_t credits_scene_get(uint8_t v, uint8_t kind, uint8_t i, uint8_t *dst) BANKED;", ""]
    h += ["#ifdef CREDITS_SCROLL   // the scrolling credits' own rows and layout (rows of the world: tools/gen_credits.py LAY)",
          f"#define CT_LBL {ids['LBL0']}   // the label OWNER",
          f"#define CT_BAND {ids['BAND0']}   // the venue band: three rows a venue, CT_BAND + 3 v + j", f"#define CT_STRIPE {stripe}   // the stripe's tile (pool index; colour 2 all over)",
          "static const uint16_t ct_bandcol[10] = { " + ", ".join(str(c) for c in band_col) + " };   // the stripe's colour on Color (RGB555, before BRIGHTEN)"]
    if CRSCENE:
        h += [f"#define CT_SCN {ids['SCN0']}   // the scene pages' rows: 17 a (venue, model), CT_SCN + 17 (2 v + is_cgb) + j - 1", "static const uint16_t ct_solid[4] = { " + ", ".join(str(x) for x in ids["SOLID"]) + " };   // the four flat tiles' pool indices (BG ids CR_SOLID_ID + 0..3)"]
    if CRMAP:
        h += [f"#define CT_BLD {ids['BLD0']}   // the building rows (a venue's start: ct_boff)", "static const uint16_t ct_solid[4] = { " + ", ".join(str(x) for x in ids["SOLID"]) + " };   // the four flat tiles' pool indices (BG ids CR_SOLID_ID + 0..3)",
              "static const uint8_t ct_vg[10] = { " + ", ".join(str(VGAP.get(v, VGAP_DEF)) for v in range(10)) + " };   // the blank rows above a venue's scene", "static const uint8_t ct_snp[10] = { " + ", ".join(str(n) for n in NPALS) + " };   // a scene's palettes", "static const uint16_t ct_scol[10][7][4] = { " + ", ".join("{ " + ", ".join("{ " + ", ".join(str(c) for c in cols) + " }" for cols in sc) + " }" for sc in BLD_COL) + " };   // each scene's palettes (the map's own: RGB555, before BRIGHTEN), light to dark; the cells name them (credits.c CR_SCENE_SLOT)",
              "static const uint8_t ct_boff[10] = { " + ", ".join(str(b[0]) for b in BLD_INFO) + " };   // a venue's first building row, from CT_BLD",
              "static const uint8_t ct_bh[10] = { " + ", ".join(str(b[1]) for b in BLD_INFO) + " };    // the building's rows",
              "static const uint8_t ct_bs0[10] = { " + ", ".join(str(b[2]) for b in BLD_INFO) + " };   // the first row of the name's stripe, from the building's top",
              "static const uint8_t ct_bnl[10] = { " + ", ".join(str(b[3]) for b in BLD_INFO) + " };   // the name's lines (a stripe row each)",
              "static const uint8_t ct_bc0[10] = { " + ", ".join(str(b[4]) for b in BLD_INFO) + " };   // the building's first column",
              "static const uint8_t ct_bc1[10] = { " + ", ".join(str(b[5]) for b in BLD_INFO) + " };   // its end (the stripe's first column)"]
    h += [f"#define CT_{k} {v}" for k, v in LAY.items()]
    h += [f"#define CT_ROLL2_N {len(roll2)}   // the scroll's roll: a blank row after each line of an entry", f"#define CT_ROLL2_BAND {band2}   // its sprites' band (the roll's row 14, moved)",
          "static const uint8_t ct_roll2[CT_ROLL2_N] = { " + ", ".join(str(r) for r in roll2) + " };"]
    h += [f"#define CT_RING_N {SCROLL_RING}   // the cast's text ring (peak {peaks})", "#endif", "", "#endif", ""]
    (out / "credits_text.h").write_text(resolve_scroll("\n".join(h)))
    js = {"bld": [list(b[:6]) + [b[6]] for b in BLD_INFO] if CRMAP else [], "rows": INFO, "ids": ids, "roll": ROLL, "roll_ids": roll_ids, "roll2_ids": roll2, "roll2_band": band2, "venues": VENUES, "owners": OWNERS, "bosses": BOSSES, "patrons": PATRONS,
          "slot": SLOT, "pair_x": pair_x, "pat_cx": pat_cx, "look_pal": LOOK_PAL, "pal_cols": PAL_COLS, "pool": len(POOL), "ring_peak": peak, "extra": EXTRA, "layout": LAY, "ring_peaks": {str(k): v for k, v in peaks.items()}, "title": TITLE}
    (out / "credits_text.json").write_text(json.dumps(js, indent=1))
    for nm_, np_, mg_ in SCENE_REPORT:
        print(f"scene {nm_}: {np_} map palettes" + (f", extras: {mg_}" if np_ > 5 else ""))
    print(f"credits text: {n_rows} rows, {len(POOL)} tiles ({len(POOL) * 16} bytes) + {len(flat) * 2} bytes of cells, roll peak {peak}/{ROLL_POOL}, one row each")


if __name__ == "__main__":
    main()
