#!/usr/bin/env python3
"""ASCII art -> GBDK tile data (build/art.c, build/art.h) + x8 previews.

  bar.txt        shared BG tiles (HUD glyphs, panel): '@name' blocks, cut into 8x8 tiles row-major, loaded after
                 the venue slots (TILE_GENERIC_BASE).
  bartender.txt  7 frames 16x24 -> per frame 4 OAM entries of 8x16 (2 columns x
                 2 rows; the bottom row is 8 px of art + 8 px transparent pad),
                 8 tiles per frame: [c0 top, c0 top-low, c1 top, c1 top-low,
                 c0 bot, pad, c1 bot, pad].
  glass.txt, coin.txt, can/foam/cursor.txt   the breaking glass, the tip, the bonus round.
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
    h += [f"#define TITLE_TILE_COUNT {len(ttiles) // 16}", "extern const uint8_t title_tiles[];", ""]
    c.append(fmt("title_tiles", ttiles))
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

    # ---- show performers (M9): 4 frames 16x24 per venue (<t>_show.txt), laid out like the bartender ----
    h[-2:-2] = ["#define DANCER_FRAMES 4", "#define DANCER_TILES_PER_FRAME 8", "#define DANCER_TILE_COUNT 32", ""]

    h[-2:-2] = venues(outdir, prev)

    # ---- bonus round art -> build/can_tiles.h, #included by src/bonus.c so it lives in that file's ROM bank ----
    # tile order: 5 can frames (2 tiles each), 2 foam frames, 1 cursor (8x8 art in the lower half of an 8x16 entry)
    cans = [r for _, r in blocks(ROOT / "assets/art/can.txt")]
    assert len(cans) == 5 and all(len(f) == 16 and len(f[0]) == 8 for f in cans)
    foams = [r for _, r in blocks(ROOT / "assets/art/foam.txt")]
    assert len(foams) == 2 and all(len(f) == 8 and len(f[0]) == 8 for f in foams)
    curs = [r for _, r in blocks(ROOT / "assets/art/cursor.txt")]
    assert len(curs) == 1 and len(curs[0]) == 8 and len(curs[0][0]) == 8
    low = [["." * 8] * 8 + f for f in foams + curs]
    bt2 = []
    for f in cans + low:
        bt2 += tile_bytes(f, 0, 0) + tile_bytes(f, 0, 8)
    bh = ["// generated by tools/gen_art.py -- do not edit", "#define CAN_FRAMES 5", "#define CAN_TILE_COUNT 10",
          "#define FOAM_FRAMES 2", f"#define BONUS_TILE_COUNT {len(bt2) // 16}", ""]
    bh.append(fmt("bonus_tiles", bt2).replace("const uint8_t", "static const uint8_t"))
    (outdir / "can_tiles.h").write_text("\n".join(bh))
    png(cans, prev / "can_x8.png", 8, transparent=True)
    png(low, prev / "foam_cursor_x8.png", 8, transparent=True)

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
