#!/usr/bin/env python3
"""ASCII art -> GBDK tile data (build/art.c, build/art.h) + x8 previews.

  bar.txt        shared BG tiles (HUD glyphs, panel): '@name' blocks, cut into 8x8 tiles row-major, loaded after
                 the venue slots (TILE_GENERIC_BASE).
  bartender.txt  7 frames 16x24 -> per frame 4 OAM entries of 8x16 (2 columns x
                 2 rows; the bottom row is 8 px of art + 8 px transparent pad),
                 8 tiles per frame: [c0 top, c0 top-low, c1 top, c1 top-low,
                 c0 bot, pad, c1 bot, pad].
  glass.txt, coin.txt, can/foam/cursor.txt   the breaking glass, the tip, the bonus round.
  pour.txt, tap.txt, pour_glass.txt, tips.txt   (M12) Perfect Pour and Tip Shower -> build/bonus2_art.h (src/bonus2.c).
  approved/venues/<t>_*  (M9) per theme: stage 160x32 + palette slots, bar 160x24 + floor 8x8 + palette slots, drink
                 (10 frames 8x16 = full, empty, fill x4, drink x4: replaces the old mug / mug_fill / mug_drink art),
                 show (4 frames 16x24: replaces dancer.txt), palettes -> build/venue_<t>.c, see venues().
  patrons/<g>.txt       3 variants 16x16 per group -> build/patrons_<g>.c (one file per group, each placed in a
                        switchable bank by autobank): each variant pre-shifted right by 0..7 px inside a 24x16
                        footprint (3x2 tiles, colour 0 background) = 144 tiles,
  patrons/<g>_back.txt  then 3 back views 16x16 (shift 0 only, 2x2 tiles) = 12 tiles.
                        build/patron_load.c (fixed bank) has load_patron_tiles(g, first).
Usage: gen_art.py outdir previewdir
"""
import json
import sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
PATRON_GROUPS = ["cowboys", "sports", "lumberjacks", "chefs", "divers", "robots", "ninjas", "aliens", "zoo"]
PATRON_SHIFTS = 8
# M9 themed venues, one per patron group, in PATRON_GROUPS order (theme index = group index; saloon = theme 0)
THEMES = ["saloon", "sports", "lodge", "bistro", "igloo", "factory", "teahouse", "space", "zoo"]
STAGE_SLOT, BAR_SLOT = 20, 16            # fixed BG id slots a venue's stage / bar tiles load over
STAGE_ROWS, BAR_ROWS = 4, 3              # screen rows 1-4; per bar 2 wall rows + the counter row
# CGB BG palette slots (= src/game.h BGPAL_*): stage_a, stage_b, bar, bar_b
PAL_STAGE_A, PAL_STAGE_B, PAL_BAR, PAL_BAR_B = 5, 6, 0, 7
VENUE_PALS = ["stage_a", "stage_b", "bar", "bar_b", "drink_full", "drink_empty", "show"]
IDX = {".": 0, "-": 1, "+": 2, "#": 3, "0": 0, "1": 1, "2": 2, "3": 3}
GREY = [(255, 255, 255), (170, 170, 170), (85, 85, 85), (0, 0, 0)]


def blocks(path, named=False):
    """Parse blocks of pixel rows separated by blank lines. Returns [(name, rows)]."""
    res, cur, name = [], [], None
    for line in path.read_text().splitlines() + [""]:
        line = line.rstrip()
        if line.startswith(("//",)) or (line.startswith(";")):
            continue
        if named and line.startswith("@"):
            if cur:
                res.append((name, cur)); cur = []
            name = line[1:]
            continue
        if line == "":
            if cur:
                res.append((name, cur)); cur = []
                if not named:
                    name = None
            continue
        cur.append(line)
    return res


def tile_bytes(rows, x0, y0):
    out = []
    for y in range(8):
        lo = hi = 0
        for x in range(8):
            v = IDX[rows[y0 + y][x0 + x]]
            lo |= (v & 1) << (7 - x)
            hi |= (v >> 1) << (7 - x)
        out += [lo, hi]
    return out


def fmt(name, data):
    lines = []
    for i in range(0, len(data), 16):
        lines.append("    " + ", ".join(f"0x{b:02X}" for b in data[i:i + 16]) + ",")
    return f"const uint8_t {name}[{len(data)}] = {{\n" + "\n".join(lines) + "\n};\n"


def png(rows_list, path, scale, transparent=False):
    """rows_list: list of frames (each a list of row strings) laid left to right."""
    h = max(len(f) for f in rows_list)
    w = sum(len(f[0]) + 1 for f in rows_list)
    im = Image.new("RGB", (w, h), (255, 0, 255) if transparent else (255, 255, 255))
    x0 = 0
    for f in rows_list:
        for y, r in enumerate(f):
            for x, c in enumerate(r):
                if transparent and c == ".":
                    im.putpixel((x0 + x, y), (200, 230, 255))
                else:
                    im.putpixel((x0 + x, y), GREY[IDX[c]])
        x0 += len(f[0]) + 1
    im.resize((w * scale, h * scale), Image.NEAREST).save(path)


def rgb15(hexs):
    out = []
    for h in hexs:
        r, g, b = (int(h[i:i + 2], 16) for i in (1, 3, 5))
        out.append((r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10))
    return out


def plain_rows(path):
    return [l.rstrip() for l in path.read_text().splitlines() if l.strip() and not l.startswith(";")]


def cut(rows, w, h):
    """rows -> h x w grid of 8x8 tiles (each a tuple of 8 strings)."""
    return [[tuple(rows[ty * 8 + y][tx * 8:tx * 8 + 8] for y in range(8)) for tx in range(w)] for ty in range(h)]


def obj_tiles(frames, w):
    """8x16 entries column by column: per frame [c0 top, c0 low, c1 top, c1 low, ...] (as the bartender)."""
    out = []
    for f in frames:
        for ty in range(0, len(f), 16):
            for cx in range(0, w, 8):
                out += tile_bytes(f, cx, ty) + tile_bytes(f, cx, ty + 8)
    return out


def venues(outdir, prev):
    """assets/approved/venues/<t>_* -> build/venue_<t>.c (one banked file per theme: tiles, maps, palettes),
    build/venue_load.c (venue_fetch: copies theme t's venue_t into WRAM), build/venues.json (for the tests) and
    out/preview/venue_<t>_x3.png. Returns the art.h lines. Fails the build if a theme exceeds its tile slots."""
    import json
    vd = ROOT / "assets/approved/venues"
    h = ["// ---- M9 themed venues (tools/gen_art.py venues()): theme index = patron group index ----",
         f"#define VENUES {len(THEMES)}", "// venue order: " + ", ".join(THEMES),
         "#define VENUE_PAL_STAGE_A 0", "#define VENUE_PAL_STAGE_B 1", "#define VENUE_PAL_BAR 2",
         "#define VENUE_PAL_BAR_B 3", "#define VENUE_PAL_DRINK_FULL 4", "#define VENUE_PAL_DRINK_EMPTY 5",
         "#define VENUE_PAL_SHOW 6", f"#define VENUE_PALS {len(VENUE_PALS)}",
         f"#define VENUE_BGPAL_STAGE_A {PAL_STAGE_A}", f"#define VENUE_BGPAL_STAGE_B {PAL_STAGE_B}",
         f"#define VENUE_BGPAL_BAR {PAL_BAR}", f"#define VENUE_BGPAL_BAR_B {PAL_BAR_B}",
         "#define VENUE_DRINK_TILES 20   // full, empty (OBJ_MUG), fill x4 (OBJ_MUG_FILL), drink x4 (OBJ_MUG_DRINK)",
         "typedef struct {",
         "    const uint8_t *stage_tiles, *bar_tiles, *drink_tiles, *show_tiles;   // in the venue's own bank",
         "    uint8_t stage_n, bar_n, floor_tile;",
         f"    uint8_t stage_map[{STAGE_ROWS * 20}], stage_attr[{STAGE_ROWS * 20}];   // screen rows 1-4: BG tile ids, CGB attributes",
         f"    uint8_t bar_map[{BAR_ROWS * 20}], bar_attr[{BAR_ROWS * 20}];       // one bar: 2 wall rows + counter row",
         f"    uint16_t pal[VENUE_PALS][4];                 // RGB15; VENUE_PAL_* order",
         "} venue_t;",
         "extern venue_t venue;            // the current level's venue (WRAM copy, src/venue.c)",
         "extern uint8_t venue_bank;       // ROM bank of its tile data",
         "void venue_fetch(uint8_t t) BANKED;   // build/venue_load.c: copy theme t into venue / venue_bank", ""]
    load = ["// generated by tools/gen_art.py -- do not edit", "#include <gb/gb.h>", '#include "art.h"',
            "#pragma bank 255", "void far_copy(void *dst, const void *src, uint16_t n, uint8_t bank);   // src/main.c (ROM0)", ""]
    cases, info = [], {"stage_slot": STAGE_SLOT, "bar_slot": BAR_SLOT, "tile_stage_base": 0, "tile_bar_base": STAGE_SLOT,
                       "themes": THEMES, "venues": {}}
    for ti, t in enumerate(THEMES):
        stage = plain_rows(vd / f"{t}_stage.txt")
        bar = plain_rows(vd / f"{t}_bar.txt")
        floor = plain_rows(vd / f"{t}_floor.txt")
        assert len(stage) == 32 and all(len(r) == 160 for r in stage), f"{t}_stage.txt: not 160x32"
        assert len(bar) == 24 and all(len(r) == 160 for r in bar), f"{t}_bar.txt: not 160x24"
        assert len(floor) == 8 and all(len(r) == 8 for r in floor), f"{t}_floor.txt: not 8x8"
        sattr = [[int(ch) for ch in r] for r in plain_rows(vd / f"{t}_attr.txt")]
        battr = [[int(ch) for ch in r] for r in plain_rows(vd / f"{t}_bar_attr.txt")]
        assert len(sattr) == 4 and all(len(r) == 20 and set(r) <= {0, 1} for r in sattr), f"{t}_attr.txt: not 20x4 of 0/1"
        assert len(battr) == 3 and all(len(r) == 20 and set(r) <= {0, 1} for r in battr), f"{t}_bar_attr.txt: not 20x3 of 0/1"
        # the engine's layout: patrons stand on the wall rows (flat colour 0 + specks of 1, bar palette), the counter
        # row is a full row, the spout is the lower wall row's column 17 (SPOUT_X 136), the keg columns 18-19
        for y in range(16):
            assert set(bar[y][16:136]) <= {".", "-"}, f"{t}_bar.txt: wall row pixel row {y} has more than colour 0 + specks"
        for r in range(2):
            assert all(battr[r][c] == 0 for c in range(2, 17)), f"{t}_bar_attr.txt: wall columns 2-16 must use the bar palette"
        pal = json.loads((vd / f"{t}_pal.json").read_text())
        dpal = json.loads((vd / f"{t}_drink_pal.json").read_text())
        spal = json.loads((vd / f"{t}_show_pal.json").read_text())
        pals = [pal["stage_a"]["hex"], pal["stage_b"]["hex"], pal["bar"]["hex"], pal.get("bar_b", pal["bar"])["hex"]]
        assert all(len(x) == 4 for x in pals), f"{t}_pal.json: BG palettes need 4 colours"
        assert pals[3][0].lower() == pals[2][0].lower(), f"{t}_pal.json: bar_b colour 0 must be the wall colour"
        assert all(len(x) == 3 for x in (dpal["full"]["hex"], dpal["empty"]["hex"], spal["obj"]["hex"]))
        pal15 = [rgb15(x) for x in pals] + [[0] + rgb15(dpal["full"]["hex"]), [0] + rgb15(dpal["empty"]["hex"]),
                                            [0] + rgb15(spal["obj"]["hex"])]
        # stage: unique tiles -> ids TILE_STAGE_BASE..
        sgrid, suniq = cut(stage, 20, 4), []
        smap = []
        for row in sgrid:
            for tile in row:
                if tile not in suniq:
                    suniq.append(tile)
                smap.append(suniq.index(tile))
        bgrid, buniq = cut(bar, 20, 3), []
        bmap = []
        for row in bgrid:
            for tile in row:
                if tile not in buniq:
                    buniq.append(tile)
                bmap.append(buniq.index(tile))
        ftile = tuple(floor)
        if ftile not in buniq:
            buniq.append(ftile)
        fid = buniq.index(ftile)
        if len(suniq) > STAGE_SLOT:
            sys.exit(f"gen_art: venue {t}: stage has {len(suniq)} unique tiles, the slot holds {STAGE_SLOT}")
        if len(buniq) > BAR_SLOT:
            sys.exit(f"gen_art: venue {t}: bar + floor have {len(buniq)} unique tiles, the slot holds {BAR_SLOT}")
        stile = []
        for tile in suniq:
            stile += tile_bytes(list(tile), 0, 0)
        btile = []
        for tile in buniq:
            btile += tile_bytes(list(tile), 0, 0)
        drinks = [r for _, r in blocks(vd / f"{t}_drink.txt")]
        assert len(drinks) == 10 and all(len(f) == 16 and all(len(r) == 8 for r in f) for f in drinks), f"{t}_drink.txt: 10 frames 8x16"
        shows = [r for _, r in blocks(vd / f"{t}_show.txt")]
        assert len(shows) == 4 and all(len(f) == 24 and all(len(r) == 16 for r in f) for f in shows), f"{t}_show.txt: 4 frames 16x24"
        dtile = obj_tiles(drinks, 8)
        stiles = obj_tiles([list(f) + ["." * 16] * 8 for f in shows], 16)
        assert len(dtile) == 20 * 16 and len(stiles) == 32 * 16
        abs_smap = [STAGE_SLOT * 0 + i for i in smap]
        abs_bmap = [STAGE_SLOT + i for i in bmap]
        abs_sattr = [PAL_STAGE_B if a else PAL_STAGE_A for r in sattr for a in r]
        abs_battr = [PAL_BAR_B if a else PAL_BAR for r in battr for a in r]
        sym = f"venue_{t}"

        def arr(vals):
            return "{ " + ", ".join(str(v) for v in vals) + " }"
        vc = ["// generated by tools/gen_art.py from assets/approved/venues/" + t + "_* -- do not edit",
              "#include <gb/gb.h>", '#include "art.h"', "#pragma bank 255", f"BANKREF({sym})", "",
              fmt(f"{sym}_stage", stile).replace("const uint8_t", "static const uint8_t"),
              fmt(f"{sym}_bar", btile).replace("const uint8_t", "static const uint8_t"),
              fmt(f"{sym}_drink", dtile).replace("const uint8_t", "static const uint8_t"),
              fmt(f"{sym}_show", stiles).replace("const uint8_t", "static const uint8_t"),
              f"const venue_t {sym} = {{",
              f"    {sym}_stage, {sym}_bar, {sym}_drink, {sym}_show,",
              f"    {len(suniq)}, {len(buniq)}, {STAGE_SLOT + fid},",
              f"    {arr(abs_smap)},", f"    {arr(abs_sattr)},", f"    {arr(abs_bmap)},", f"    {arr(abs_battr)},",
              "    { " + ", ".join(arr(x) for x in pal15) + " }", "};", ""]
        (outdir / f"{sym}.c").write_text("\n".join(vc))
        load += [f"BANKREF_EXTERN({sym})", f"extern const venue_t {sym};"]
        cases.append(f"    case {ti}: far_copy(&venue, &{sym}, sizeof venue, BANK({sym})); venue_bank = BANK({sym}); break;")
        info["venues"][t] = {"stage_n": len(suniq), "bar_n": len(buniq), "floor_tile": STAGE_SLOT + fid,
                             "stage_map": abs_smap, "stage_attr": abs_sattr, "bar_map": abs_bmap, "bar_attr": abs_battr,
                             "pal": pal15, "drink": dtile, "show": stiles, "stage_tiles": stile, "bar_tiles": btile}
        # preview: the venue as the game draws it (stage, 4 bars, floor; CGB colours), x3
        im = Image.new("RGB", (160, 144), (0, 0, 0))
        def put(tx, ty, tb, pal):
            for y in range(8):
                lo, hi = tb[y * 2], tb[y * 2 + 1]
                for x in range(8):
                    v = ((lo >> (7 - x)) & 1) | (((hi >> (7 - x)) & 1) << 1)
                    c = pal[v]
                    im.putpixel((tx * 8 + x, ty * 8 + y), ((c & 31) << 3, ((c >> 5) & 31) << 3, ((c >> 10) & 31) << 3))
        bgpal = {PAL_STAGE_A: pal15[0], PAL_STAGE_B: pal15[1], PAL_BAR: pal15[2], PAL_BAR_B: pal15[3]}
        for i, tid in enumerate(abs_smap):
            put(i % 20, 1 + i // 20, stile[tid * 16:tid * 16 + 16], bgpal[abs_sattr[i]])
        for b in range(4):
            for i, tid in enumerate(abs_bmap):
                k = tid - STAGE_SLOT
                put(i % 20, 5 + 3 * b + i // 20, btile[k * 16:k * 16 + 16], bgpal[abs_battr[i]])
        for x in range(20):
            put(x, 17, btile[fid * 16:fid * 16 + 16], pal15[2])
        im.resize((480, 432), Image.NEAREST).save(prev / f"venue_{t}_x3.png")
        png(drinks, prev / f"venue_{t}_drink_x8.png", 8, transparent=True)
        png(shows, prev / f"venue_{t}_show_x8.png", 8, transparent=True)
    load += ["", "venue_t venue;", "uint8_t venue_bank;", "",
             "// theme t (0..VENUES-1) -> venue (WRAM) and venue_bank; switches to the theme's bank only inside far_copy",
             "void venue_fetch(uint8_t t) BANKED {", "    switch (t) {"] + cases + ["    }", "}", ""]
    (outdir / "venue_load.c").write_text("\n".join(load))
    (outdir / "venues.json").write_text(json.dumps(info))
    return h


# ---- M10a title screen (src/title.c #includes build/title_art.h, so the data lives in that file's bank) ----
TITLE_WORD = "SPIGOTEER"
TITLE_LETTERS = "SPIGOTER"            # the order of the @title_* blocks in title.txt
LOGO_FILL = [0, 4, 8, 12]             # px of beer in the fill states before the final art (5 steps per letter)
MENU_STRINGS = {"arcade": "ARCADE", "story": "STORY", "music_on": "MUSIC ON", "music_off": "MUSIC OFF",
                "soon": "COMING SOON"}
TITLE_TILE_LIMIT = 228                # BG ids up to the end of the patron range (the puff's OBJ tiles follow)


def _px_tile_bytes(px):
    out = []
    for y in range(8):
        lo = hi = 0
        for x in range(8):
            lo |= (px[y][x] & 1) << (7 - x)
            hi |= (px[y][x] >> 1) << (7 - x)
        out += [lo, hi]
    return out


def title_art(outdir, prev, base, ttiles, bg):
    """Logo fill states, the menu text (pre-rendered and exactly centred: an odd-length string is drawn 4 px to the
    right inside one more tile, so it centres to the pixel on the 20-column grid), the HI line glyphs and the
    effect sprites -> build/title_art.h + build/title.json (tile ids for the tests) + previews."""
    import json
    letters = {}
    for k, (name, rows) in enumerate(blocks(ROOT / "assets/tiles/title.txt", named=True)):
        letters[name[len("title_"):].upper()] = (k, [[IDX[ch] for ch in r] for r in rows])
    first = base + len(ttiles) // 16
    pool, pool_px = {}, []
    QUAD = ((0, 0), (0, 8), (8, 0), (8, 8))

    def key(px):
        return tuple(tuple(r) for r in px)
    final = {}
    for L, (k, rows) in letters.items():
        for q, (ty, tx) in enumerate(QUAD):
            final.setdefault(key([r[tx:tx + 8] for r in rows[ty:ty + 8]]), base + k * 4 + q)

    low_px = []                            # text tiles go to the venue's stage slot first (ids 0..19: no stage on the title)

    def tid(px, low=False):
        kk = key(px)
        if kk in final:                    # identical to a lettering tile: reuse it
            return final[kk]
        if kk not in pool:
            if low and len(low_px) < STAGE_SLOT:
                pool[kk] = len(low_px)
                low_px.append(px)
            else:
                pool[kk] = first + len(pool_px)
                pool_px.append(px)
        return pool[kk]

    # logo: per letter (title.txt order) and fill state, the 4 tile ids (top-left, top-right, bottom-left, bottom-right)
    fill_map, previews = [], []
    for L in TITLE_LETTERS:
        k, rows = letters[L]
        states = []
        for si, f in enumerate(LOGO_FILL):
            line = 16 - f                  # first liquid row
            px = []
            for y in range(16):
                r = []
                for x in range(16):
                    v = rows[y][x]
                    if v in (1, 2):        # inside the letter
                        if f and line <= y < line + 2:
                            v = 1                                          # foam
                        elif f and y == line - 1:
                            v = 1 if (x + si) % 3 else 0                   # frothy head
                        elif f and y >= line + 2:
                            v = 1 if (x * 5 + y * 3) % 17 == 0 else 2   # beer, a bubble here and there
                        else:
                            v = 0                                          # empty: the wall shows through
                    r.append(v)
                px.append(r)
            states.append([tid([r[tx:tx + 8] for r in px[ty:ty + 8]]) for ty, tx in QUAD])
            previews.append(px)
        states.append([base + k * 4 + q for q in range(4)])
        previews.append(rows)
        fill_map.append(states)
    n_fill = len(pool_px)

    # menu text: the HUD glyphs of bar.txt ('.' = text) at rows 0-6, columns 1-5 of the cell, 1 px drop shadow (colour 1)
    def glyph(ch):
        g = bg["glyph_" + ch]
        return [[1 if g[y][x] == "." else 0 for x in range(8)] for y in range(1, 8)]

    def render(s, col=3, centre=True):
        n = len(s)
        odd = centre and n & 1             # (a single glyph for the HI digits is never shifted)
        w = 8 * (n + odd)
        x0 = 4 if odd else 0
        px = [[0] * w for _ in range(8)]
        for pas in (0, 1):                 # shadows first, then the text over them
            for i, ch in enumerate(s):
                if ch == " ":
                    continue
                g = glyph(ch)
                for y in range(7):
                    for x in range(8):
                        if g[y][x]:
                            X = x0 + 8 * i + x
                            if pas == 0:
                                px[y + 1][X + 1] = 1
                            else:
                                px[y][X] = col
        return px, w // 8

    blank = tid([[0] * 8 for _ in range(8)], True)
    text, strip_prev = {}, []
    for k2, s in MENU_STRINGS.items():
        px, nt = render(s)
        text[k2] = {"col": (20 - nt) // 2, "tiles": [tid([r[t * 8:t * 8 + 8] for r in px], True) for t in range(nt)],
                    "x": (20 - nt) // 2 * 8 + (4 if len(s) & 1 else 0) + 1}   # screen x of the first text pixel
        strip_prev.append(px)
    digits = [tid(render(d, 2, False)[0], True) for d in "0123456789"]
    # "HI" as one small tile (3x5 letters, muted): the HI line is HI + space + 6 digits = 8 tiles, centred
    hi_px = [[0] * 8 for _ in range(8)]
    for y, r in enumerate(["#.#.###", "#.#..#.", "###..#.", "#.#..#.", "#.#.###"]):
        for x, ch in enumerate(r):
            if ch == "#":
                if hi_px[y + 3][x + 1] == 0:
                    hi_px[y + 3][x + 1] = 1
    for y, r in enumerate(["#.#.###", "#.#..#.", "###..#.", "#.#..#.", "#.#.###"]):
        for x, ch in enumerate(r):
            if ch == "#":
                hi_px[y + 2][x] = 2
    hi_tile = tid(hi_px, True)
    strip_prev.append(hi_px)
    n_total = len(pool_px)
    patron_base = first + n_total            # 4 tiles of the scene's patron (copied from the cowboys group at run time)
    if patron_base + 4 > TITLE_TILE_LIMIT:
        sys.exit(f"gen_art: title tiles end at {patron_base + 4}, past {TITLE_TILE_LIMIT} (fill {n_fill}, all {n_total})")

    # effect sprites: 8x8 frames in the top half of 8x16 entries
    fx = [r for _, r in blocks(ROOT / "assets/art/title_fx.txt")]
    assert len(fx) == 6 and all(len(f) == 8 and all(len(r) == 8 for r in f) for f in fx), "title_fx.txt: 6 frames 8x8"
    fxt = []
    for f in fx:
        fxt += tile_bytes(f + ["." * 8] * 8, 0, 0) + tile_bytes(f + ["." * 8] * 8, 0, 8)

    def carr(name, vals):
        return f"static const uint8_t {name}[{len(vals)}] = {{ " + ", ".join(str(v) for v in vals) + " };"
    ext, low = [], []
    for px in pool_px:
        ext += _px_tile_bytes(px)
    for px in low_px:
        low += _px_tile_bytes(px)
    out = ["// generated by tools/gen_art.py (title_art) -- do not edit; #included by src/title.c (its bank)",
           f"#define TT_EXTRA_BASE {first}", f"#define TT_EXTRA_COUNT {n_total}   // logo fill states + menu text tiles",
           f"#define TT_LOW_COUNT {len(low_px)}   // menu text tiles at ids 0.. (the stage slot)",
           f"#define TT_PATRON_BASE {patron_base}", f"#define TT_BLANK {blank}", f"#define TT_HI {hi_tile}",
           f"#define TT_LOGO_STATES {len(LOGO_FILL) + 1}", f"#define TT_FX_TILES {len(fxt) // 16}", "",
           fmt("title_tiles", ttiles).replace("const uint8_t", "static const uint8_t"),
           fmt("tt_extra_tiles", ext).replace("const uint8_t", "static const uint8_t"),
           fmt("tt_low_tiles", low).replace("const uint8_t", "static const uint8_t"),
           fmt("tt_fx_tiles", fxt).replace("const uint8_t", "static const uint8_t"),
           carr("tt_word", [TITLE_LETTERS.index(ch) for ch in TITLE_WORD]) + "   // SPIGOTEER -> tt_logo index",
           f"static const uint8_t tt_logo[{len(TITLE_LETTERS)}][{len(LOGO_FILL) + 1}][4] = {{"]
    for st in fill_map:
        out.append("    { " + ", ".join("{ " + ", ".join(str(v) for v in q) + " }" for q in st) + " },")
    out.append("};")
    for k2, t in text.items():
        out.append(carr(f"tt_{k2}", [t["col"], len(t["tiles"])] + t["tiles"]) + "   // column, count, tile ids")
        out.append(f"#define TT_X_{k2.upper()} {t['x']}   // screen x of its first text pixel")
    out += [carr("tt_digit", digits), ""]
    (outdir / "title_art.h").write_text("\n".join(out))
    (outdir / "title.json").write_text(json.dumps({
        "extra_base": first, "blank": blank, "hi": hi_tile, "digits": digits, "text": text, "word": TITLE_WORD,
        "logo": {L: fill_map[i] for i, L in enumerate(TITLE_LETTERS)}, "patron_base": patron_base, "fill_tiles": n_fill}))
    # previews: each letter's fill states (columns: letters, rows: states), the menu strings
    S = len(LOGO_FILL) + 1
    im = Image.new("RGB", (len(TITLE_LETTERS) * 17, S * 17), (255, 0, 255))
    for i, px in enumerate(previews):
        L, s = divmod(i, S)
        for y in range(16):
            for x in range(16):
                im.putpixel((L * 17 + x, s * 17 + y), GREY[px[y][x]])
    im.resize((im.width * 8, im.height * 8), Image.NEAREST).save(prev / "title_logo_fill_x8.png")
    w = max(len(p[0]) for p in strip_prev)
    im = Image.new("RGB", (w, 9 * len(strip_prev)), (255, 0, 255))
    for i, px in enumerate(strip_prev):
        for y in range(8):
            for x in range(len(px[0])):
                im.putpixel((x, i * 9 + y), GREY[px[y][x]])
    im.resize((im.width * 8, im.height * 8), Image.NEAREST).save(prev / "title_menu_x8.png")
    png(fx, prev / "title_fx_x8.png", 8, transparent=True)


# ---- M12 bonus rounds Perfect Pour and Tip Shower: build/bonus2_art.h, #included by src/bonus2.c (its bank) ----
POUR_TARGETS = [12, 15, 18, 21, 24, 27]     # fill line heights, px above the glass interior's bottom (interior: 32 px)


def bonus2_art(outdir, prev):
    pour = [r for _, r in blocks(ROOT / "assets/art/pour.txt")]
    assert len(pour) == 8 and all(len(f) == 16 and len(f[0]) == 8 for f in pour), "pour.txt: 8 frames of 8x16"
    taps = [r for _, r in blocks(ROOT / "assets/art/tap.txt")]
    assert len(taps) == 2 and all(len(f) == 16 and all(len(r) == 24 for r in f) for f in taps), "tap.txt: 2 frames of 24x16"
    part = lambda f, i: [r[i:i + 8] for r in f]
    assert part(taps[0], 0) == part(taps[1], 0) and part(taps[0], 16) == part(taps[1], 16), "tap: only the middle differs"
    # frame order (src/bonus2.c F_*): beer, half, foam, dome, streak, head, tap A, tap B closed, tap B pulled, tap C, stream, arrow
    pour = pour[:6] + [part(taps[0], 0), part(taps[0], 8), part(taps[1], 8), part(taps[0], 16)] + pour[6:]
    gl = [r for _, r in blocks(ROOT / "assets/art/pour_glass.txt")]
    glass, bang = gl
    assert len(glass) == 40 and all(len(r) == 16 for r in glass)
    assert len(bang) == 8 and all(len(r) == 8 for r in bang)
    tips = [r for _, r in blocks(ROOT / "assets/art/tips.txt")]
    assert len(tips) == 4 and [len(f[0]) for f in tips] == [24, 24, 8, 8] and all(len(f) == 16 for f in tips)
    tips_frames = [[r[i:i + 8] for r in tips[k]] for k in (0, 1) for i in (0, 8, 16)] + tips[2:]
    pt = []
    for f in pour:
        pt += tile_bytes(f, 0, 0) + tile_bytes(f, 0, 8)
    tt = []
    for f in tips_frames:
        tt += tile_bytes(f, 0, 0) + tile_bytes(f, 0, 8)
    # BG: the glass (2x5 tiles, row-major), then per target its two line tiles, then '!'
    bg = []
    for ty in range(5):
        for tx in range(2):
            bg += tile_bytes(glass, tx * 8, ty * 8)
    line_row, line_glass = [], []
    for t in POUR_TARGETS:
        y = 32 - t
        g = [r for r in glass]
        g[y] = g[y][:2] + "+" * 12 + g[y][14:]
        line_row.append(y // 8)
        line_glass.append(g)
        for tx in range(2):
            bg += tile_bytes(g, tx * 8, (y // 8) * 8)
    bg += tile_bytes(bang, 0, 0)
    h = ["// generated by tools/gen_art.py (bonus2_art) -- do not edit; #included by src/bonus2.c (its bank)",
         "#define POUR_OBJ_TILES %d" % (len(pt) // 16), "#define TIPS_OBJ_TILES %d" % (len(tt) // 16),
         "#define B2_BG_TILES %d   // glass 0-9, line tiles 10.., '!' last" % (len(bg) // 16),
         "#define B2_BANG %d" % (len(bg) // 16 - 1),
         "#define POUR_TARGETS %d" % len(POUR_TARGETS), ""]
    h.append(fmt("pour_obj_tiles", pt).replace("const uint8_t", "static const uint8_t"))
    h.append(fmt("tips_obj_tiles", tt).replace("const uint8_t", "static const uint8_t"))
    h.append(fmt("b2_bg_tiles", bg).replace("const uint8_t", "static const uint8_t"))
    h.append("static const uint8_t pour_target_px[POUR_TARGETS] = { %s };" % ", ".join(map(str, POUR_TARGETS)))
    h.append("static const uint8_t pour_line_row[POUR_TARGETS] = { %s };   // glass tile row holding the line"
             % ", ".join(map(str, line_row)))
    (outdir / "bonus2_art.h").write_text("\n".join(h) + "\n")
    (outdir / "bonus2.json").write_text(json.dumps({"pour_targets": POUR_TARGETS, "line_row": line_row}))
    png(pour[:6] + pour[10:], prev / "pour_x8.png", 8, transparent=True)
    png(taps, prev / "tap_x8.png", 8, transparent=True)
    png([glass] + line_glass[:1] + [bang], prev / "pour_glass_x8.png", 8)
    png(tips_frames, prev / "tips_x8.png", 8, transparent=True)


def main():
    outdir, prev = Path(sys.argv[1]), Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True); prev.mkdir(parents=True, exist_ok=True)
    c = ["// generated by tools/gen_art.py -- do not edit", "#include <gb/gb.h>", '#include "art.h"',
         "// the tile data lives in a switchable ROM bank (autobank) to keep the fixed bank free for code; main.c copies",
         "// it to VRAM through bkg_data() / spr_data(), which switch to BANK(art_tiles)",
         "#pragma bank 255", "BANKREF(art_tiles)", ""]
    h = ["// generated by tools/gen_art.py -- do not edit", "#ifndef ART_H", "#define ART_H",
         "#include <stdint.h>", ""]

    # ---- BG tileset: fixed venue slots (stage, bar) first, then the shared tiles of bar.txt ----
    h += [f"#define TILE_STAGE_BASE 0        // {STAGE_SLOT} ids: the level's venue stage tiles (load_venue)",
          f"#define STAGE_TILE_SLOT {STAGE_SLOT}",
          f"#define TILE_BAR_BASE {STAGE_SLOT}       // {BAR_SLOT} ids: the venue's bar, door, keg, spout and floor tiles",
          f"#define BAR_TILE_SLOT {BAR_SLOT}",
          f"#define TILE_GENERIC_BASE {STAGE_SLOT + BAR_SLOT}   // the shared tiles below (bar_tiles[])", ""]
    gbase = STAGE_SLOT + BAR_SLOT
    bg, tiles, names = blocks(ROOT / "assets/tiles/bar.txt", named=True), [], []
    for name, rows in bg:
        assert len({len(r) for r in rows}) == 1, f"{name}: ragged rows"
        W, H = len(rows[0]), len(rows)
        assert W % 8 == 0 and H % 8 == 0, f"{name}: not a multiple of 8x8"
        h.append(f"#define TILE_{name.upper()} {gbase + len(tiles) // 16}")
        for ty in range(H // 8):
            for tx in range(W // 8):
                tiles += tile_bytes(rows, tx * 8, ty * 8)
    n_generic = len(tiles) // 16
    n = gbase + n_generic
    assert n <= 256
    h += [f"#define GENERIC_TILE_COUNT {n_generic}",
          f"#define BAR_TILE_COUNT {n}   // all scene tiles (venue slots + shared): the patron tiles start here",
          "extern const uint8_t bar_tiles[];   // GENERIC_TILE_COUNT tiles, loaded at TILE_GENERIC_BASE", ""]
    c.append(fmt("bar_tiles", tiles))
    # title lettering (assets/tiles/title.txt): ids BAR_TILE_COUNT.. at title time only, over the patron tiles
    ttiles = []
    for name, rows in blocks(ROOT / "assets/tiles/title.txt", named=True):
        assert len(rows) == 16 and all(len(r) == 16 for r in rows), f"{name}: not 16x16"
        h.append(f"#define TILE_{name.upper()} {n + len(ttiles) // 16}")
        for ty in range(2):
            for tx in range(2):
                ttiles += tile_bytes(rows, tx * 8, ty * 8)
    h += [f"#define TITLE_TILE_COUNT {len(ttiles) // 16}   // data in build/title_art.h (src/title.c's bank)", ""]
    title_art(outdir, prev, n, ttiles, dict(bg))
    # preview: tiles in a grid of 16 per row
    cols = 16
    im = Image.new("RGB", (cols * 9, ((n_generic + cols - 1) // cols) * 9), (255, 0, 255))
    for t in range(n_generic):
        for y in range(8):
            lo, hi = tiles[t * 16 + y * 2], tiles[t * 16 + y * 2 + 1]
            for x in range(8):
                v = ((lo >> (7 - x)) & 1) | (((hi >> (7 - x)) & 1) << 1)
                im.putpixel(((t % cols) * 9 + x, (t // cols) * 9 + y), GREY[v])
    im.resize((im.width * 8, im.height * 8), Image.NEAREST).save(prev / "bar_tiles_x8.png")

    # ---- bartender ----
    frames = [r for _, r in blocks(ROOT / "assets/art/bartender.txt")]
    assert len(frames) == 7 and all(len(f) == 24 and len(f[0]) == 16 for f in frames)
    bt, padded = [], []
    blank = ["." * 8] * 8
    for f in frames:
        pad = [r for r in f] + ["." * 16] * 8          # 16x32 with transparent pad
        padded.append(pad)
        for ty in (0, 16):                              # top entry row, bottom entry row
            for cx in (0, 8):
                bt += tile_bytes(pad, cx, ty) + tile_bytes(pad, cx, ty + 8)
        # reorder: entries must be c0top, c1top, c0bot, c1bot -> already (ty outer, cx inner)
    h += ["#define BARTENDER_FRAMES 7", "#define BARTENDER_TILES_PER_FRAME 8",
          f"#define BARTENDER_TILE_COUNT {len(bt) // 16}", "extern const uint8_t bartender_tiles[];", ""]
    c.append(fmt("bartender_tiles", bt))
    png(padded, prev / "bartender_x8.png", 8, transparent=True)

    # ---- drinks (M9): the mug / fill / drink OBJ tiles come from each venue's <t>_drink.txt (load_venue) ----
    h += [f"#define MUG_FRAMES 2", "#define MUG_TILE_COUNT 4", "", "#endif", ""]
    h[-2:-2] = ["#define MUG_FILL_FRAMES 4", "#define MUG_FILL_TILE_COUNT 8", ""]
    # ---- glass (breaking mug): 4 frames 16x16 = 2 OAM entries of 8x16 each ----
    glass = [r for _, r in blocks(ROOT / "assets/art/glass.txt")]
    assert len(glass) == 4 and all(len(f) == 16 and len(f[0]) == 16 for f in glass)
    gt = []
    for f in glass:
        for cx in (0, 8):
            gt += tile_bytes(f, cx, 0) + tile_bytes(f, cx, 8)
    h[-2:-2] = ["#define GLASS_FRAMES 4", "#define GLASS_TILES_PER_FRAME 4",
                f"#define GLASS_TILE_COUNT {len(gt) // 16}", "extern const uint8_t glass_tiles[];", ""]
    c.append(fmt("glass_tiles", gt))
    png(glass, prev / "glass_x8.png", 8, transparent=True)

    h[-2:-2] = ["#define MUG_DRINK_FRAMES 4", "#define MUG_DRINK_TILE_COUNT 8", ""]
    # ---- coin (tip): 8x8 art in the lower half of an 8x16 entry; frame 1 swaps the two body shades (glint) ----
    coin = [r for _, r in blocks(ROOT / "assets/art/coin.txt")][0]
    assert len(coin) == 8 and len(coin[0]) == 8
    swap = str.maketrans("-+", "+-")
    coin_frames = [["." * 8] * 8 + coin, ["." * 8] * 8 + [r.translate(swap) for r in coin]]
    ct = []
    for f in coin_frames:
        ct += tile_bytes(f, 0, 0) + tile_bytes(f, 0, 8)
    h[-2:-2] = ["#define COIN_FRAMES 2", f"#define COIN_TILE_COUNT {len(ct) // 16}",
                "extern const uint8_t coin_tiles[];", ""]
    c.append(fmt("coin_tiles", ct))
    png(coin_frames, prev / "coin_x8.png", 8, transparent=True)

    # ---- door puff: 3 frames of 8x16 (one OAM entry), OBJ ids after the patron BG range (OBJ ids 228+ share no BG tile) ----
    puff = [r for _, r in blocks(ROOT / "assets/art/puff.txt")]
    assert len(puff) == 3 and all(len(f) == 16 and len(f[0]) == 8 for f in puff)
    pt = []
    for f in puff:
        pt += tile_bytes(f, 0, 0) + tile_bytes(f, 0, 8)
    h[-2:-2] = ["#define PUFF_FRAMES 3", f"#define PUFF_TILE_COUNT {len(pt) // 16}",
                "extern const uint8_t puff_tiles[];", ""]
    c.append(fmt("puff_tiles", pt))
    png(puff, prev / "puff_x8.png", 8, transparent=True)

    # ---- show performers (M9): 4 frames 16x24 per venue (<t>_show.txt), laid out like the bartender ----
    h[-2:-2] = ["#define DANCER_FRAMES 4", "#define DANCER_TILES_PER_FRAME 8", "#define DANCER_TILE_COUNT 32", ""]

    h[-2:-2] = venues(outdir, prev)

    # ---- bonus round art -> build/can_tiles.h, #included by src/bonus.c so it lives in that file's ROM bank ----
    # tile order: 5 can frames (2 tiles each), 1 cursor (8x8 art in the lower half of an 8x16 entry),
    # 3 geyser left halves + 3 right halves, 3 droplet frames (the lose result)
    cans = [r for _, r in blocks(ROOT / "assets/art/can.txt")]
    assert len(cans) == 5 and all(len(f) == 16 and len(f[0]) == 8 for f in cans)
    curs = [r for _, r in blocks(ROOT / "assets/art/cursor.txt")]
    assert len(curs) == 1 and len(curs[0]) == 8 and len(curs[0][0]) == 8
    low = [["." * 8] * 8 + f for f in curs]
    geys = [r for _, r in blocks(ROOT / "assets/art/geyser.txt")]
    drops = [r for _, r in blocks(ROOT / "assets/art/droplets.txt")]
    assert len(geys) == 3 and all(len(f) == 16 and len(f[0]) == 16 for f in geys)
    assert len(drops) == 3 and all(len(f) == 16 and len(f[0]) == 8 for f in drops)
    geys = [[r[:8] for r in f] for f in geys] + [[r[8:] for r in f] for f in geys]    # 3 left halves, then 3 right halves
    bt2 = []
    for f in cans + low + geys + drops:
        bt2 += tile_bytes(f, 0, 0) + tile_bytes(f, 0, 8)
    bh = ["// generated by tools/gen_art.py -- do not edit", "#define CAN_FRAMES 5", "#define CAN_TILE_COUNT 10",
          "#define GEYSER_FRAMES 6", "#define DROP_FRAMES 3", f"#define BONUS_TILE_COUNT {len(bt2) // 16}", ""]
    bh.append(fmt("bonus_tiles", bt2).replace("const uint8_t", "static const uint8_t"))
    (outdir / "can_tiles.h").write_text("\n".join(bh))
    png(cans, prev / "can_x8.png", 8, transparent=True)
    png(low, prev / "cursor_x8.png", 8, transparent=True)
    png(geys + drops, prev / "geyser_droplets_x8.png", 8, transparent=True)

    bonus2_art(outdir, prev)

    # ---- patrons: per group 3 variants x 8 shifts x (3x2 tiles, row-major), then 3 back views x (2x2 tiles) ----
    # The 16x16 patron is pasted at x offset 0..7 into a 24x16 canvas of colour 0 (the wall colour in the
    # patron palettes), so a patron moves in 1 px steps by swapping tilemap entries only. The back views
    # (patrons watching the show) only stand on a multiple of 8 px, so they need no shifts and no 3rd column.
    per_group = 3 * PATRON_SHIFTS * 6
    back_tiles = 3 * 4
    load = ["// generated by tools/gen_art.py -- do not edit", "#include <gb/gb.h>", '#include "art.h"', ""]
    cases = []
    for gi, g in enumerate(PATRON_GROUPS):
        vs = [r for _, r in blocks(ROOT / f"assets/art/patrons/{g}.txt")]
        assert len(vs) == 3 and all(len(v) == 16 and all(len(r) == 16 for r in v) for v in vs), g
        bs = [r for _, r in blocks(ROOT / f"assets/art/patrons/{g}_back.txt")]
        assert len(bs) == 3 and all(len(v) == 16 and all(len(r) == 16 for r in v) for v in bs), g + "_back"
        pt, shifted_rows = [], []
        for v in vs:
            for s in range(PATRON_SHIFTS):
                canvas = ["." * s + v[y] + "." * (24 - 16 - s) for y in range(16)]
                for ty in (0, 8):
                    for tx in (0, 8, 16):
                        pt += tile_bytes(canvas, tx, ty)
                shifted_rows.append(canvas)
        for v in bs:
            for ty in (0, 8):
                for tx in (0, 8):
                    pt += tile_bytes(v, tx, ty)
        assert len(pt) == (per_group + back_tiles) * 16
        sym = f"patron_tiles_{g}"
        pc = ["// generated by tools/gen_art.py -- do not edit", "#include <gb/gb.h>", '#include "art.h"',
              "#pragma bank 255", f"BANKREF({sym})", "", fmt(sym, pt)]
        (outdir / f"patrons_{g}.c").write_text("\n".join(pc))
        load += [f"BANKREF_EXTERN({sym})", f"extern const uint8_t {sym}[];"]
        cases.append(f"    case {gi}: SWITCH_ROM(BANK({sym})); set_bkg_data(first, PATRON_GROUP_TILES, {sym}); break;")
        png(vs + bs, prev / f"patrons_{g}_x8.png", 8)
        if g == PATRON_GROUPS[0]:
            png(shifted_rows[:PATRON_SHIFTS], prev / "patrons_shifted_x8.png", 8)
    load += ["", "// LCD off (or VBlank) only: the group's 156 BG tiles to ids first..first+155",
             "void load_patron_tiles(uint8_t g, uint8_t first) {", "    uint8_t saved = CURRENT_BANK;", "    switch (g) {"]
    load += cases + ["    }", "    SWITCH_ROM(saved);", "}", ""]
    (outdir / "patron_load.c").write_text("\n".join(load))
    h[-2:-2] = [f"#define PATRON_GROUPS {len(PATRON_GROUPS)}",
                f"#define PATRON_SHIFTS {PATRON_SHIFTS}",
                f"#define PATRON_TILES_PER_GROUP {per_group}   // 3 variants x 8 shifts x 6 tiles (3x2)",
                f"#define PATRON_BACK_TILES {back_tiles}   // then 3 back views x 4 tiles (2x2), shift 0 only",
                f"#define PATRON_GROUP_TILES {per_group + back_tiles}",
                "// tile of (variant v, shift s, row r, column k): v * 48 + s * 6 + r * 3 + k;",
                "// back view of v: PATRON_TILES_PER_GROUP + v * 4 + r * 2 + k",
                "// group order: " + ", ".join(PATRON_GROUPS),
                "void load_patron_tiles(uint8_t g, uint8_t first);   // build/patron_load.c", ""]

    (outdir / "art.h").write_text("\n".join(h))
    (outdir / "art.c").write_text("\n".join(c))


main()
