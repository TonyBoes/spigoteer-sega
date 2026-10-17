#!/usr/bin/env python3
"""ASCII art -> GBDK tile data (build/art.c, build/art.h) + x8 previews.

  bar.txt        shared BG tiles (HUD glyphs, panel): '@name' blocks, cut into 8x8 tiles row-major, loaded after
                 the venue slots (TILE_GENERIC_BASE).
  bartender.txt  7 frames 16x24 -> per frame 4 OAM entries of 8x16 (2 columns x
                 2 rows; the bottom row is 8 px of art + 8 px transparent pad),
                 8 tiles per frame: [c0 top, c0 top-low, c1 top, c1 top-low,
                 c0 bot, pad, c1 bot, pad].
  glass_shards.txt, coin.txt, can/foam/cursor.txt   the crash shards (tip/fall come from each drink), the tip, the bonus round.
  pour.txt, tap.txt, pour_glass.txt, tips.txt   (M12) Perfect Pour and Tip Shower -> build/bonus2_art.h (src/bonus2.c).
  approved/venues/<t>_*  (M9) per theme: stage 160x32 + palette slots, bar 160x24 + floor 8x8 + palette slots, drink
                 (10 frames 8x16 = full, empty, fill x4, drink x4: replaces the old mug / mug_fill / mug_drink art),
                 show (4 frames 16x24: replaces dancer.txt), palettes -> build/venue_<t>.c, see venues().
  patrons/<g>.txt       3 variants 16x16 per group -> build/patrons_<g>.c (one file per group, each placed in a
                        switchable bank by autobank): each variant pre-shifted right by 0..7 px inside a 24x16
                        footprint (3x2 tiles, colour 0 background) = 144 tiles,
  patrons/<g>_back.txt  then 3 back views 16x16 (shift 0 only, 2x2 tiles) = 12 tiles.
                        build/patron_load.c (banked) has load_patron_tiles(g, first).
                        M14a: '; @rows <v> <top> <bottom>' header lines make variant v (a/b/c) an ENHANCED variant
                        (see enhanced_group): build/patron_enh.h (src/enhance.c) + build/patron_enh.json (tests).
Usage: gen_art.py outdir previewdir
"""
import json
import re
import sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
PATRON_GROUPS = ["cowboys", "sports", "lumberjacks", "chefs", "divers", "robots", "punks", "ninjas", "zoo", "aliens"]
PATRON_SHIFTS = 8
# M9 themed venues, one per patron group, in PATRON_GROUPS order (theme index = group index; saloon = theme 0)
THEMES = ["saloon", "sports", "lodge", "bistro", "igloo", "factory", "biker", "teahouse", "zoo", "space"]
# BG ids 0..VENUE_POOL-1: one pool for a venue's stage and bar tiles (option A, owner 2026-10-10). The stage takes ids
# from 0 up (animated tiles last), the bar + floor pack at the top (VENUE_POOL - bar_n ..), so stage_n + bar_n <= the
# pool. The title's menu text overwrites ids 0..TITLE_TEXT_SLOT-1 while it shows the saloon's bar: bar ids stay above.
# (22 since BOSS RUSH, 2026-10-12: its 5 new text tiles did not fit under TITLE_TILE_END; 23 since SETTINGS > BAR SNAP, 2026-10-16: the saloon has 13; every other venue's bar + floor has
# at most 12 tiles, so ids 20-21 were stage ids only, and the title shows no stage.)
# The glass held under the spout hangs FILL_DY px lower than a sliding mug, per venue (owner's per-venue tap picks, 2026-10-12).
# Packed into venue.show_band bits 1-2 (WRAM-free: the venue struct is WRAM already; src/mugs.c draw_fill reads it). The
# check below keeps every venue's spout tip above the glass in every fill frame: the glass's rim is sprite row 5 and the full
# drink's foam head row 4, the sprite top MUG_DY + FILL_DY below the bar's top row, so the lowest art pixel over the glass
# (x 136-143, rows 0-15) must be above row MUG_DY + FILL_DY + 4. At most 3 (the launch handoff is a step of that many px).
FILL_DY = {"saloon": 3, "sports": 2, "lodge": 0, "bistro": 0, "igloo": 2, "factory": 0, "biker": 3, "teahouse": 2, "zoo": 2, "space": 3}
# Lettering on a tap (owner 2026-10-12: POP on the stadium's base, MOO on the biker's churn) must not read backwards on an R
# (mirrored) bar, which draws every bar tile flipped. LETTER_BOX = (x0, y0, x1, y1) of the lettering in the bar art (pixels,
# inclusive): the box is mirrored in place to make the R bar's version of the art, and the tiles that differ ("twins", at most 4)
# go in a trailer after the bar tiles in the venue's bank: n, 4 L tile ids, then n x 16 bytes. src/mirror.c mirror_load copies
# them into free BG ids on a level with an R bar (the DMG flipped) and the R rows use them in place of the L lettering tiles, so
# the bar's flip shows the text the right way round. They are not in the venue's tile pool.
LETTER_BOX = {"sports": (147, 18, 157, 22), "biker": (145, 14, 158, 18)}
VENUE_POOL, TITLE_TEXT_SLOT = 36, 23
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



# ---- the spigot pours (owner 2026-10-15: "the spigots should pour out the drink when the bartender is filling a glass") ----
# The stream is baked into the venue's three filling frames (drink frames 2-4: empty, a third, two thirds; src/mugs.c
# draw_fill shows them while A is held and the glass is not yet full), so it costs no OAM entry, no tile and no code, is
# mirrored with the glass on an R bar, and takes the drink's own colours (OBJ palette 1 on CGB, OBP0 on DMG). It is 2 px wide
# under the middle of the spout's lowest pixel row (bar art x 136-143) and runs from the pixel under the spout tip down
# over the glass's empty pixels (its rim and walls stay in front) to the drink's surface (the first '+') or the glass's floor; the flow animates because its light
# streaks shift 2 px with every filling frame. The full frame (5) shows the stream cut off: one bead hanging at the tip.
STREAM_W = 2


def pour_stream(drinks, bar, fdy, mug_dy):
    """The venue's 10 drink frames with the stream drawn into the fill frames 2-4 and a bead into the full frame 5."""
    rows = [(y, [x for x in range(136, 144) if bar[y][x] != "."]) for y in range(16)]
    tip, xs = [(y, r) for y, r in rows if r][-1]
    cx = xs[0] + len(xs) // 2 - 1            # the left column of the stream: centred under the spout's lowest run (bar x)
    interior = sorted({c for f in drinks[2:6] for row in f for c, p in enumerate(row) if p == "+"})
    left = min(max(cx - 136, interior[0]), interior[-1] - STREAM_W + 1)
    r0 = tip + 1 - (mug_dy + fdy)            # the sprite row under the spout tip
    assert 0 <= r0 <= 5, f"spout tip row {tip} vs the fill glass: the stream would start on sprite row {r0}"
    floor = max(r for r, row in enumerate(drinks[5]) if "+" in row)      # the glass's lowest drink row: the stream goes no lower
    out = [[list(r) for r in f] for f in drinks]
    for k, fi in enumerate((2, 3, 4)):
        f = out[fi]
        for c in range(left, left + STREAM_W):
            for r in range(r0, floor + 1):
                p = f[r][c]
                if p == "+":
                    break
                if p == ".":
                    f[r][c] = "-" if c == left and (r + 2 * k) % 4 < 2 and r > r0 else "+"
    bead = out[5]
    if bead[r0][left] == "." and bead[r0 + 1][left] == ".":
        bead[r0][left] = "+"                # (hanging drip: the stream has stopped)
    return [["".join(r) for r in f] for f in out]


# ---- the show performers, per venue (<t>_show.txt, frames 16x24; 32 OBJ tiles at OBJ_DANCER, 8x16 entries) ----
# Two kinds of show, one engine (src/render.c draw_dancers): every venue gets a table of SHOW_ROWS rows x 4 tile offsets
# (from OBJ_DANCER: the top-left, top-right, bottom-left, bottom-right 8x16 entries of a 16x24 figure, its bottom 8 px
# a transparent pad) and a band flag.
#  - a dance (DANCE_FRAMES = 4 frames): all three dancers dance the same frame, row = the dance frame (0-3); the tiles
#    are the frames laid out as the bartender (8 a frame), so row f is [8f, 8f + 2, 8f + 4, 8f + 6]; rows 4-5 unused.
#  - a band (BAND_FRAMES = 6 frames: performer k's pose A, then B, k = 0..2 left to right): performer k shows row
#    2k + (beat & 1). The 6 frames are cut into 8x16 quarters and deduplicated (a pose changes only the quarters it must)
#    into at most 16 quarters = the same 32 tiles; row = the frame's 4 quarters (TL TR BL BR), quarter q at tiles 2q, 2q+1.
DANCE_FRAMES, BAND_FRAMES, SHOW_ROWS, SHOW_QUARTERS = 4, 6, 6, 16


def show_tiles(t, shows):
    """-> (32 OBJ tiles as bytes, band flag, SHOW_ROWS x 4 tile offsets). Fails on a band that needs over 16 quarters."""
    if len(shows) == DANCE_FRAMES:
        tab = [[8 * f, 8 * f + 2, 8 * f + 4, 8 * f + 6] for f in range(DANCE_FRAMES)]
        return obj_tiles([list(f) + ["." * 16] * 8 for f in shows], 16), 0, tab + tab[:SHOW_ROWS - DANCE_FRAMES]
    quarters, tab = [], []
    for f in shows:
        f = list(f) + ["." * 16] * 8
        row = []
        for y0, x0 in ((0, 0), (0, 8), (16, 0), (16, 8)):
            q = tuple(r[x0:x0 + 8] for r in f[y0:y0 + 16])
            if q not in quarters:
                quarters.append(q)
            row.append(2 * quarters.index(q))
        tab.append(row)
    if len(quarters) > SHOW_QUARTERS:
        sys.exit(f"gen_art: venue {t}: the band needs {len(quarters)} 8x16 quarters, at most {SHOW_QUARTERS} (32 OBJ tiles)")
    quarters += [tuple(["." * 8] * 16)] * (SHOW_QUARTERS - len(quarters))
    return obj_tiles([list(q) for q in quarters], 8), 1, tab


# ---- the breaking drink (crash), per venue: generated from the venue's own drink so it matches the sliding one ----
# 16 OBJ tiles at OBJ_GLASS (8x16 entries, column-major as obj_tiles): tip 0-1 (the venue's tilted "drink" pose, frame 8
# of <t>_drink.txt), fall full 2-5 and fall empty 6-9 (the full / empty frame turned 90 degrees, mouth left, 16x16), the
# shared shards: shatter 10-11, settle 12-13 (assets/art/glass_shards.txt), 14-15 unused. src/mugs.c draw_glass mirrors
# them at the right end; the base sits on the sliding drink's base row (CRASH_BASE).
GLASS_TILES = 16
CRASH_BASE = 14


def _crop(f):
    ys = [y for y, r in enumerate(f) if r.strip(".")]
    xs = [x for x in range(len(f[0])) if any(r[x] != "." for r in f)]
    return [r[min(xs):max(xs) + 1] for r in f[min(ys):max(ys) + 1]]


def _paste(w, h, src, x0, y0, base=None):
    d = [list(r) for r in (base or ["." * w] * h)]
    for y, r in enumerate(src):
        for x, ch in enumerate(r):
            if ch != "." and 0 <= y0 + y < h and 0 <= x0 + x < w:
                d[y0 + y][x0 + x] = ch
    return ["".join(r) for r in d]


def crash_frames(drinks, shards):
    """[tip 8x16, fall full 16x16, fall empty 16x16, shatter 8x16, settle 8x16] for one venue's 10 drink frames."""
    def tip(src):
        c = _crop(src)
        assert len(c[0]) <= 8 and len(c) <= CRASH_BASE + 1
        return _paste(8, 16, c, (8 - len(c[0])) // 2, CRASH_BASE + 1 - len(c))

    def fall(src, spill):
        c = _crop(src)
        c = ["".join(c[y][len(c[0]) - 1 - x] for y in range(len(c))) for x in range(len(c[0]))]   # 90 deg, mouth left
        assert len(c[0]) <= 16 and len(c) <= CRASH_BASE + 1, "a drink taller than 16 px cannot lie in 16x16"
        x0 = 16 - len(c[0]) - (1 if len(c[0]) < 15 else 0)
        y0 = CRASH_BASE + 1 - len(c)
        f = _paste(16, 16, c, x0, y0)
        if spill:            # the drink leaving the mouth: four drops in the drink's own colours
            my = y0 + len(c) // 2
            for dx, dy, ch in ((-2, -1, "+"), (-3, 1, "+"), (-5, 0, "-"), (-4, 2, "-")):
                f = _paste(16, 16, [ch], x0 + dx, my + dy, f)
        return f
    return [tip(drinks[7]), fall(drinks[0], True), fall(drinks[1], False)] + shards


def crash_tiles(drinks, shards):
    tip, ff, fe, sh, st = crash_frames(drinks, shards)
    fe = [r[8:] + r[:8] for r in fe]          # columns swapped: draw_glass mirrors it at the right end with S_FLIPX
    out = obj_tiles([tip], 8) + obj_tiles([ff], 16) + obj_tiles([fe], 16) + obj_tiles([sh], 8) + obj_tiles([st], 8)
    out += [0] * (GLASS_TILES * 16 - len(out))
    assert len(out) == GLASS_TILES * 16
    return out


def load_shards():
    sh = [r for _, r in blocks(ROOT / "assets/art/glass_shards.txt")]
    assert len(sh) == 2 and all(len(f) == 16 and all(len(r) == 8 for r in f) for f in sh), "glass_shards.txt: 2 frames 8x16"
    return sh


SA_MAX_K = 6          # animated tiles per stage (a step's update goes out 2 tiles per VBlank, src/render.c queue_stage)
SA_MAX_RANGE = 4      # tiles one step may change (at most 2 VBlanks)
SA_MIN_HOLD = 6       # frames a step is shown at least


def parse_anim(path):
    """assets/approved/venues/<t>_anim.txt (optional): '!slots c,r ...' (every animated map position), '!script
    name:hold ...' (looped), then '@name' frames: 8 rows, one 8-px column per distinct slot tile (in order of first
    appearance among the slots), columns separated by spaces. Returns (slots, script, frames{name: [tile, ...]})."""
    slots, script, frames, cur = None, None, {}, None
    for n, line in enumerate(path.read_text().splitlines(), 1):
        line = line.rstrip()
        if not line or line.startswith(";"):
            continue
        if line.startswith("!slots"):
            slots = [tuple(int(v) for v in p.split(",")) for p in line.split()[1:]]
        elif line.startswith("!script"):
            script = [(p.split(":")[0], int(p.split(":")[1])) for p in line.split()[1:]]
        elif line.startswith("@"):
            cur = line[1:]
            if cur in frames:
                sys.exit(f"gen_art: {path.name}:{n}: frame @{cur} defined twice")
            frames[cur] = []
        elif cur is not None:
            cols = line.split()
            if not all(len(c) == 8 and set(c) <= set(".-+#") for c in cols):
                sys.exit(f"gen_art: {path.name}:{n}: a frame row is 8-px columns of '.-+#' separated by spaces")
            frames[cur].append(cols)
        else:
            sys.exit(f"gen_art: {path.name}:{n}: unexpected line before the first @frame")
    if not slots or not script or "base" not in frames:
        sys.exit(f"gen_art: {path.name}: needs !slots, !script and an @base frame")
    out = {}
    for name, rows in frames.items():
        if len(rows) != 8 or len({len(r) for r in rows}) != 1:
            sys.exit(f"gen_art: {path.name}: frame @{name} is not 8 rows of the same number of columns")
        out[name] = [tuple(r[c] for r in rows) for c in range(len(rows[0]))]
    return slots, script, out


def stage_anim(t, path, sgrid):
    """Validate theme t's stage animation against its stage tiles (sgrid, 4 x 20) and compile it.
    Returns dict: slots, keys (the k distinct animated base tiles), frames (used frame names, base first),
    data (frames x k x 16 bytes), steps [(frame * k, lo, hi, hold)]: tiles lo..hi-1 change on that step."""
    slots, script, frames = parse_anim(path)
    name = path.name
    keys = []
    for c, r in slots:
        if not (0 <= c < 20 and 0 <= r < 4):
            sys.exit(f"gen_art: {name}: slot {c},{r} is outside the 20x4 stage")
        if sgrid[r][c] not in keys:
            keys.append(sgrid[r][c])
    k = len(keys)
    if k > SA_MAX_K:
        sys.exit(f"gen_art: {name}: {k} distinct animated tiles, at most {SA_MAX_K}")
    for r in range(4):
        for c in range(20):
            if (c, r) not in slots and sgrid[r][c] in keys:
                sys.exit(f"gen_art: {name}: position {c},{r} has the same tile as an animated slot but is not in "
                         "!slots (it would stay still while its twins move): list it, or change its pixels")
    for fn, cols in frames.items():
        if len(cols) != k:
            sys.exit(f"gen_art: {name}: frame @{fn} has {len(cols)} columns, the slots have {k} distinct tiles")
    if frames["base"] != keys:
        bad = [i for i in range(k) if frames["base"][i] != keys[i]]
        sys.exit(f"gen_art: {name}: @base column(s) {bad} differ from the stage's tiles at the slots")
    for fn, hold in script:
        if fn not in frames:
            sys.exit(f"gen_art: {name}: !script uses @{fn}, which is not defined")
        if not SA_MIN_HOLD <= hold <= 255:
            sys.exit(f"gen_art: {name}: !script {fn}:{hold}: holds are {SA_MIN_HOLD}..255 frames")
    used = ["base"] + [fn for fn, _ in script if fn != "base"]
    used = list(dict.fromkeys(used))
    unused = set(frames) - set(used)
    if unused:
        sys.exit(f"gen_art: {name}: frames never used by !script: {sorted(unused)}")
    data = []
    for fn in used:
        for tl in frames[fn]:
            data += tile_bytes(list(tl), 0, 0)

    def diff(a, b):
        d = [i for i in range(k) if frames[a][i] != frames[b][i]]
        return (d[0], d[-1] + 1) if d else None

    steps = []
    for i, (fn, hold) in enumerate(script):
        rngs = [diff(script[i - 1][0], fn)]
        if i == 0:
            rngs.append(diff("base", fn))       # the first pass starts from the stage's own tiles (load_venue)
        rngs = [x for x in rngs if x]
        lo, hi = (min(x[0] for x in rngs), max(x[1] for x in rngs)) if rngs else (0, 0)
        if hi - lo > SA_MAX_RANGE:
            sys.exit(f"gen_art: {name}: step {i} ({fn}) changes tiles {lo}..{hi - 1}: at most {SA_MAX_RANGE} per step")
        steps.append((used.index(fn) * k, lo, hi, hold))
    return {"slots": slots, "keys": keys, "k": k, "frames": used, "data": data, "steps": steps,
            "script": [(used.index(fn), hold) for fn, hold in script], "tiles": frames}


def venues(outdir, prev):
    """assets/approved/venues/<t>_* -> build/venue_<t>.c (one banked file per theme: tiles, maps, palettes),
    build/venue_load.c (venue_fetch: copies theme t's venue_t into WRAM), build/venues.json (for the tests) and
    out/preview/venue_<t>_x3.png. Returns the art.h lines. Fails the build if a theme exceeds its tile slots."""
    import json
    vd = ROOT / "assets/approved/venues"
    shards = load_shards()
    h = ["// ---- M9 themed venues (tools/gen_art.py venues()): theme index = patron group index ----",
         f"#define VENUES {len(THEMES)}", "// venue order: " + ", ".join(THEMES),
         "#define VENUE_PAL_STAGE_A 0", "#define VENUE_PAL_STAGE_B 1", "#define VENUE_PAL_BAR 2",
         "#define VENUE_PAL_BAR_B 3", "#define VENUE_PAL_DRINK_FULL 4", "#define VENUE_PAL_DRINK_EMPTY 5",
         "#define VENUE_PAL_SHOW 6", f"#define VENUE_PALS {len(VENUE_PALS)}",
         f"#define VENUE_BGPAL_STAGE_A {PAL_STAGE_A}", f"#define VENUE_BGPAL_STAGE_B {PAL_STAGE_B}",
         f"#define VENUE_BGPAL_BAR {PAL_BAR}", f"#define VENUE_BGPAL_BAR_B {PAL_BAR_B}",
         "#define VENUE_DRINK_TILES 20   // full, empty (OBJ_MUG), fill x4 (OBJ_MUG_FILL), drink x4 (OBJ_MUG_DRINK); the crash follows (OBJ_GLASS)",
         "typedef struct {",
         "    const uint8_t *stage_tiles, *bar_tiles, *drink_tiles, *show_tiles;   // in the venue's own bank",
         "    uint8_t stage_n, bar_n, bar_base, floor_tile;   // bar_base = VENUE_POOL - bar_n",
         f"    uint8_t stage_map[{STAGE_ROWS * 20}], stage_attr[{STAGE_ROWS * 20}];   // screen rows 1-4: BG tile ids, CGB attributes",
         f"    uint8_t bar_map[{BAR_ROWS * 20}], bar_attr[{BAR_ROWS * 20}];       // one bar: 2 wall rows + counter row",
         f"    uint16_t pal[VENUE_PALS][4];                 // RGB15; VENUE_PAL_* order",
         "    const uint8_t *anim_frames, *anim_script;    // stage animation (src/venue.c), in the venue's own bank",
         "    uint16_t anim_frames_n;                      // bytes of anim_frames (0: the stage does not move)",
         "    uint8_t anim_script_n, anim_first, anim_k;   // script bytes; first animated stage id, animated tiles",
         "    uint8_t show_band;                           // bit 0: 0 one dance for all three (row = dance frame), 1 a band; bits 1-2: FILL_DY (src/mugs.c)",
         f"    uint8_t show_tile[{SHOW_ROWS}][4];             // per row: OBJ tile offsets from OBJ_DANCER, TL TR BL BR",
         "    uint8_t splash_tile;                         // the counter splash's BG id (assets/art/splash; 0: none)",
         "} venue_t;",
         f"#define SHOW_ROWS {SHOW_ROWS}                 // a band's performer k shows row 2k + (beat & 1) (src/render.c)",
         "extern venue_t venue;            // the current level's venue (WRAM copy, src/venue.c)",
         "extern uint8_t venue_bank;       // ROM bank of its tile data",
         "void venue_fetch(uint8_t t) BANKED;   // build/venue_load.c: copy theme t into venue / venue_bank", ""]
    load = ["// generated by tools/gen_art.py -- do not edit", "#include <gb/gb.h>", '#include "art.h"',
            "#pragma bank 255", "void far_copy(void *dst, const void *src, uint16_t n, uint8_t bank);   // src/main.c (ROM0)", ""]
    cases, info = [], {"pool": VENUE_POOL, "title_text_slot": TITLE_TEXT_SLOT, "tile_stage_base": 0,
                       "themes": THEMES, "venues": {}}
    sa_buf, sa_scr = 16, 4
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
        # row is a full row, the spout is the lower wall row's column 17 (SPOUT_X 136), the keg columns 18-19. No door
        # (owner 2026-10-09): the wall runs to the left edge, columns 0-16
        for y in range(16):
            assert set(bar[y][0:136]) <= {".", "-"}, f"{t}_bar.txt: wall row pixel row {y} has more than colour 0 + specks"
        for r in range(2):
            assert all(battr[r][c] == 0 for c in range(0, 17)), f"{t}_bar_attr.txt: wall columns 0-16 must use the bar palette"
        pal = json.loads((vd / f"{t}_pal.json").read_text())
        dpal = json.loads((vd / f"{t}_drink_pal.json").read_text())
        spal = json.loads((vd / f"{t}_show_pal.json").read_text())
        pals = [pal["stage_a"]["hex"], pal["stage_b"]["hex"], pal["bar"]["hex"], pal.get("bar_b", pal["bar"])["hex"]]
        assert all(len(x) == 4 for x in pals), f"{t}_pal.json: BG palettes need 4 colours"
        assert pals[3][0].lower() == pals[2][0].lower(), f"{t}_pal.json: bar_b colour 0 must be the wall colour"
        assert all(len(x) == 3 for x in (dpal["full"]["hex"], dpal["empty"]["hex"], spal["obj"]["hex"]))
        pal15 = [rgb15(x) for x in pals] + [[0] + rgb15(dpal["full"]["hex"]), [0] + rgb15(dpal["empty"]["hex"]),
                                            [0] + rgb15(spal["obj"]["hex"])]
        # stage: unique tiles -> ids TILE_STAGE_BASE..; the animated tiles (<t>_anim.txt) get their own ids, last and
        # contiguous (never merged with a static tile), so one copy entry rewrites them
        sgrid, suniq = cut(stage, 20, 4), []
        apath = vd / f"{t}_anim.txt"
        anim = stage_anim(t, apath, sgrid) if apath.exists() else None
        akeys = anim["keys"] if anim else []
        smap = []
        for r, row in enumerate(sgrid):
            for c, tile in enumerate(row):
                if tile in akeys:
                    smap.append(-1 - akeys.index(tile))
                    continue
                if tile not in suniq:
                    suniq.append(tile)
                smap.append(suniq.index(tile))
        a_first = len(suniq)
        smap = [a_first - 1 - i if i < 0 else i for i in smap]
        suniq += akeys
        fdy = FILL_DY[t]
        mug_dy = int(re.search(r"#define MUG_DY\s+(\d+)", (ROOT / "src" / "layout.h").read_text()).group(1))
        tip = max((y for y in range(16) for x in range(136, 144) if bar[y][x] != "."), default=-1)
        if not 0 <= fdy <= 3 or not 0 <= tip < mug_dy + fdy + 4:
            sys.exit(f"gen_art: venue {t}: the spout tip is on bar row {tip} but the fill glass (FILL_DY {fdy}) starts its foam head "
                     f"on row {mug_dy + fdy + 4}: shorten the spout or raise FILL_DY (at most 3)")
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
        # an optional counter splash (assets/art/splash/<t>.txt, 8x8, the bar palette): a venue twist's cue drawn over
        # a counter-row tile (the mosh pit, src/mosh.c), loaded with the bar set; venue.splash_tile 0: none
        spath = ROOT / "assets/art/splash" / f"{t}.txt"
        sid = None
        if spath.exists():
            sp = tuple(plain_rows(spath))
            assert len(sp) == 8 and all(len(r) == 8 for r in sp), f"{spath}: not 8x8"
            if sp not in buniq:
                buniq.append(sp)
            sid = buniq.index(sp)
        alt = []                            # (index of the L tile in buniq, its pre-mirrored twin)
        if t in LETTER_BOX:
            x0, y0, x1, y1 = LETTER_BOX[t]
            rrows = [list(r) for r in bar]
            for y in range(y0, y1 + 1):
                rrows[y][x0:x1 + 1] = bar[y][x0:x1 + 1][::-1]
            for lrow, rrow in zip(bgrid, cut(["".join(r) for r in rrows], 20, 3)):
                for lt, rt in zip(lrow, rrow):
                    if lt == rt:
                        continue
                    assert all(a != buniq.index(lt) or b == rt for a, b in alt), f"{t}: one L lettering tile with two R twins"
                    if (buniq.index(lt), rt) not in alt:
                        alt.append((buniq.index(lt), rt))
            assert 0 < len(alt) <= 4, f"{t}: {len(alt)} lettering tiles"
        if len(suniq) + len(buniq) > VENUE_POOL:
            sys.exit(f"gen_art: venue {t}: stage has {len(suniq)} unique tiles ({a_first} static + {len(akeys)} "
                     f"animated) and bar + floor {len(buniq)}: the pool holds {VENUE_POOL}")
        bar_base = VENUE_POOL - len(buniq)
        if bar_base < TITLE_TEXT_SLOT:      # the title shows the saloon bar while its text overwrites ids 0..19
            sys.exit(f"gen_art: venue {t}: bar + floor have {len(buniq)} unique tiles; at most "
                     f"{VENUE_POOL - TITLE_TEXT_SLOT} keep them clear of the title's text ids 0..{TITLE_TEXT_SLOT - 1}")
        stile = []
        for tile in suniq:
            stile += tile_bytes(list(tile), 0, 0)
        btile = []
        for tile in buniq:
            btile += tile_bytes(list(tile), 0, 0)
        btrail = [len(alt)] + [bar_base + a for a, _ in alt] + [0] * (4 - len(alt))
        for _, rt in alt:
            btrail += tile_bytes(list(rt), 0, 0)
        drinks = [r for _, r in blocks(vd / f"{t}_drink.txt")]
        assert len(drinks) == 10 and all(len(f) == 16 and all(len(r) == 8 for r in f) for f in drinks), f"{t}_drink.txt: 10 frames 8x16"
        shows = [r for _, r in blocks(vd / f"{t}_show.txt")]
        assert len(shows) in (DANCE_FRAMES, BAND_FRAMES) and all(len(f) == 24 and all(len(r) == 16 for r in f) for f in shows), \
            f"{t}_show.txt: {DANCE_FRAMES} frames 16x24 (one dancer, all three dance it) or {BAND_FRAMES} (a band of three)"
        dtile = obj_tiles(pour_stream(drinks, bar, fdy, mug_dy), 8) + crash_tiles(drinks, shards)
        stiles, band, show_tab = show_tiles(t, shows)
        assert len(dtile) == (20 + GLASS_TILES) * 16 and len(stiles) == 32 * 16
        abs_smap = list(smap)
        abs_bmap = [bar_base + i for i in bmap]
        abs_sattr = [PAL_STAGE_B if a else PAL_STAGE_A for r in sattr for a in r]
        abs_battr = [PAL_BAR_B if a else PAL_BAR for r in battr for a in r]
        sym = f"venue_{t}"

        ascript = [b for st in anim["steps"] for b in st] + [0, 0, 0, 0] if anim else []
        sa_buf = max(sa_buf, len(anim["data"]) if anim else 0)
        sa_scr = max(sa_scr, len(ascript))

        def arr(vals):
            return "{ " + ", ".join(str(v) for v in vals) + " }"
        vc = ["// generated by tools/gen_art.py from assets/approved/venues/" + t + "_* -- do not edit",
              "#include <gb/gb.h>", '#include "art.h"', "#pragma bank 255", f"BANKREF({sym})", "",
              fmt(f"{sym}_stage", stile).replace("const uint8_t", "static const uint8_t"),
              fmt(f"{sym}_bar", btile + btrail).replace("const uint8_t", "static const uint8_t"),
              fmt(f"{sym}_drink", dtile).replace("const uint8_t", "static const uint8_t"),
              fmt(f"{sym}_show", stiles).replace("const uint8_t", "static const uint8_t"),
              ] + ([fmt(f"{sym}_anim_frames", anim["data"]).replace("const uint8_t", "static const uint8_t"),
                    fmt(f"{sym}_anim_script", ascript).replace("const uint8_t", "static const uint8_t")] if anim else []) + [
              f"const venue_t {sym} = {{",
              f"    {sym}_stage, {sym}_bar, {sym}_drink, {sym}_show,",
              f"    {len(suniq)}, {len(buniq)}, {bar_base}, {bar_base + fid},",
              f"    {arr(abs_smap)},", f"    {arr(abs_sattr)},", f"    {arr(abs_bmap)},", f"    {arr(abs_battr)},",
              "    { " + ", ".join(arr(x) for x in pal15) + " },",
              (f"    {sym}_anim_frames, {sym}_anim_script, {len(anim['data'])}, {len(ascript)}, {a_first}, {anim['k']},"
               if anim else "    0, 0, 0, 0, 0, 0,"),
              f"    {band | fdy << 1}, {{ " + ", ".join(arr(r) for r in show_tab) + " },", f"    {bar_base + sid if sid is not None else 0}",
              "};", ""]
        (outdir / f"{sym}.c").write_text("\n".join(vc))
        load += [f"BANKREF_EXTERN({sym})", f"extern const venue_t {sym};"]
        cases.append(f"    case {ti}: far_copy(&venue, &{sym}, sizeof venue, BANK({sym})); venue_bank = BANK({sym}); break;")
        info["venues"][t] = {"stage_n": len(suniq), "bar_n": len(buniq), "bar_base": bar_base, "floor_tile": bar_base + fid,
                             "splash_tile": bar_base + sid if sid is not None else 0,
                             "stage_map": abs_smap, "stage_attr": abs_sattr, "bar_map": abs_bmap, "bar_attr": abs_battr,
                             "pal": pal15, "drink": dtile[:20 * 16], "crash": dtile[20 * 16:], "show": stiles,
                             "show_band": band, "fill_dy": fdy, "bar_alt": [bar_base + a for a, _ in alt], "bar_alt_tiles": [tile_bytes(list(rt), 0, 0) for _, rt in alt], "show_table": show_tab, "show_frames": len(shows), "stage_tiles": stile, "bar_tiles": btile,
                             "anim": {"first": a_first, "k": anim["k"], "slots": anim["slots"], "names": anim["frames"],
                                      "frames": [anim["data"][i * anim["k"] * 16:(i + 1) * anim["k"] * 16]
                                                 for i in range(len(anim["frames"]))],
                                      "script": anim["script"], "steps": anim["steps"]} if anim else None}
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
                k = tid - bar_base
                put(i % 20, 5 + 3 * b + i // 20, btile[k * 16:k * 16 + 16], bgpal[abs_battr[i]])
        for x in range(20):
            put(x, 17, btile[fid * 16:fid * 16 + 16], pal15[2])
        im.resize((480, 432), Image.NEAREST).save(prev / f"venue_{t}_x3.png")
        if anim:      # the stage rows animating at real timing (CGB colours), x3
            gif = []
            for fi, hold in anim["script"]:
                fr = anim["data"][fi * anim["k"] * 16:(fi + 1) * anim["k"] * 16]
                for i, tid in enumerate(abs_smap):
                    j = tid - a_first
                    put(i % 20, 1 + i // 20, fr[j * 16:j * 16 + 16] if j >= 0 else stile[tid * 16:tid * 16 + 16],
                        bgpal[abs_sattr[i]])
                gif.append((im.crop((0, 8, 160, 40)).resize((480, 96), Image.NEAREST), round(hold * 1000 / 59.73)))
            gif[0][0].save(prev / f"venue_{t}_anim_x3.gif", save_all=True, append_images=[g for g, _ in gif[1:]],
                           duration=[d for _, d in gif], loop=0)
        png(drinks, prev / f"venue_{t}_drink_x8.png", 8, transparent=True)
        png(crash_frames(drinks, shards), prev / f"venue_{t}_crash_x8.png", 8, transparent=True)
        png(shows, prev / f"venue_{t}_show_x8.png", 8, transparent=True)
    load += ["", "venue_t venue;", "uint8_t venue_bank;", "",
             "// theme t (0..VENUES-1) -> venue (WRAM) and venue_bank; switches to the theme's bank only inside far_copy",
             "void venue_fetch(uint8_t t) BANKED {", "    switch (t) {"] + cases + ["    }", "}", ""]
    h += [f"#define SA_BUF {sa_buf}       // bytes: the largest stage animation's frames (WRAM copy, src/venue.c)",
          f"#define SA_SCRIPT {sa_scr}     // bytes: the longest stage animation script (4 per step + terminator)", ""]
    (outdir / "venue_load.c").write_text("\n".join(load))
    (outdir / "venues.json").write_text(json.dumps(info))
    return h


# ---- M10a title screen (src/title.c #includes build/title_art.h, so the data lives in that file's bank) ----
TITLE_WORD = "SPIGOTEER"
TITLE_LETTERS = "SPIGOTER"            # the order of the @title_* blocks in title.txt
LOGO_FILL = [0, 4, 8, 12]             # px of beer in the fill states before the final art (5 steps per letter)
MENU_STRINGS = {"arcade": "ARCADE", "story": "STORY", "music_on": "MUSIC ON", "music_off": "MUSIC OFF",
                "continue": "CONTINUE",       # M11b: CONTINUE (story save) replaced M10a's "COMING SOON"
                "bonus": "BONUS",             # the top level's BONUS submenu
                "play": "PLAY", "settings": "SETTINGS",   # the top level: PLAY / BONUS / SETTINGS (owner 2026-10-11)
                "soundtrack": "SOUNDTRACK",   # BONUS's soundtrack player (src/jukebox.c)
                "classic": "CLASSIC",         # PLAY's fourth mode (the three modes, owner 2026-10-11)
                "minigames": "MINI GAMES",  # BONUS's second item, the Practice list (src/mg_list.c)
                "bossrush": "BOSS RUSH",
                "bar_snap": "BAR SNAP",  # SETTINGS' second line (src/title.c K_BARCHANGE; SNAP is the default)
                "bar_keep": "BAR KEEP",     # BONUS's third item (src/rush.c)
                "erase": "ERASE DATA",      # SETTINGS' third line (K_ERASE): even lengths reuse the other lines' glyph tiles
                "debug": "DEBUG MENU",      # SETTINGS' DEBUG line (K_DEBUG, unlocked only)
                "erase_q": "ERASE ALL DATA",  # the confirm prompt's label line (K_ERASEQ)
                "no": "NO", "yes": "YES ",
                "credits": "CREDITS ",      # BONUS's fourth item: the credits roll (src/credits.c)
                "easy": "EASY", "normal": "NORMAL", "hard": "HARD",   # PLAY > STORY (new): the difficulty prompt (K_EASY, K_NORMAL, K_HARD) ...
                "cap_easy": "HALF POINTS ", "cap_normal": "NORMAL POINTS ", "cap_hard": "EXTRA POINTS"}   # ... and the caption under each (K_CAP_*)
PATRON_RANGE = 156                    # BG ids of the patron range (8 shifts x 3 variants x 6 + 12 back views) the title may use
# ... and past it the perfect pour's OBJ ids 234-239 (loaded at a story shift's start, never shown on the title: its
# sprites are the bartender, the mug, the drink frames and the effects, all below 128); the DMG copies start at 240
# 242 since the STORY difficulty prompt (2026-10-16): the title may use the two ids of the DMG mug copies 240-241 (lift.c swap_copy makes them at every level start; the title's sprites are all below 128);
# 244 since its captions (2026-10-17): 242-243 too (the sliding empty mug's copy: the same swap_copy)
TITLE_TILE_END = 244


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

    low_px = []                            # text tiles go to the venue pool first (ids 0..19: no stage on the title)

    def tid(px, low=False):
        kk = key(px)
        if kk in final:                    # identical to a lettering tile: reuse it
            return final[kk]
        if kk not in pool:
            if low and len(low_px) < TITLE_TEXT_SLOT:
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
    dot_px = [[0] * 8 for _ in range(8)]   # the version's full stop ("0.9": col 18 of the HI row): 2x2 px, muted like the digits, with their shadow
    for y in (5, 6):
        for x in (3, 4):
            dot_px[y + 1][x + 1] = 1
    for y in (5, 6):
        for x in (3, 4):
            dot_px[y][x] = 2
    dot_tile = tid(dot_px, True)
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
    if patron_base + 4 > TITLE_TILE_END:         # the end of the patron range and the perfect pour's ids
        sys.exit(f"gen_art: title tiles end at {patron_base + 4}, past {TITLE_TILE_END} (fill {n_fill}, all {n_total})")

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
           f"#define TT_LOW_COUNT {len(low_px)}   // menu text tiles at ids 0.. (the venue pool: no stage on the title)",
           f"#define TT_PATRON_BASE {patron_base}", f"#define TT_BLANK {blank}", f"#define TT_HI {hi_tile}", f"#define TT_DOT {dot_tile}",
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
        "extra_base": first, "blank": blank, "hi": hi_tile, "dot": dot_tile, "digits": digits, "text": text, "word": TITLE_WORD,
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
    assert len(tips) == 4 and [len(f[0]) for f in tips] == [32, 32, 8, 8] and all(len(f) == 16 for f in tips)
    tips_frames = [[r[i:i + 8] for r in tips[k]] for k in (0, 1) for i in (0, 8, 16, 24)] + tips[2:]
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


# ---- M14a enhanced patron variants (patron review, recommendation 7) ----
# A patron's BG palette is chosen per 8x8 tile, and the rows of his 3x2 footprint never move (bar tops are multiples of
# 8), so a variant may use one BG palette on its top tile row (figure rows 0-7) and another on the bottom row (8-15) at
# every pre-shift. Lifted, he is two 8x16 entries (figure x 0-7 and x 8-15), one OBJ palette each. An enhanced variant
# is lift-exact when every quadrant's colours are in its row palette AND its column's OBJ palette:
#   rows: own = the variant's own palette (BG 2 + v), S = the venue's bar_b palette (BG 7, shared with the keg/spout:
#         a venue without bar_b needs one, colour 0 = the wall; the saloon's keg does not use it);
#   columns: any patron OBJ palette of the group (A/B/C = OBJ 3/6/7, their BG palettes' colours) or the group's extra
#         <group>_x (OBJ 4, palettes.json). A column whose pixels keep their art index in that palette uses the normal
#         tiles (bank 0); otherwise gen_art writes a re-indexed copy of the column's two tiles that src/enhance.c loads
#         into CGB VRAM bank 1 at the same ids (OAM attribute bit 3). DMG draws the bank-0 tiles in greys by index (BG and
#         OBP1 = E4), unchanged.
# The art stays index art; the validator below refuses art that breaks the rule, with the reason.
BGPAL_PATRON, BGPAL_S = 2, PAL_BAR_B
OBJPAL_VARIANT, OBJPAL_X, OAM_BANK1 = [3, 6, 7], 4, 0x08
VARIANT_PALS = {"zoo": ["zoo_monkey", "zoo_panda", "zoo_hippo"]}


class ArtError(Exception):
    pass


def r15(h):
    r, g, b = (int(h[i:i + 2], 16) for i in (1, 3, 5))
    return (r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10)


def c_hex(c):
    return "#%02x%02x%02x" % ((c & 31) << 3, ((c >> 5) & 31) << 3, ((c >> 10) & 31) << 3)


def c_lum(c):
    return 0.2126 * (c & 31) + 0.7152 * ((c >> 5) & 31) + 0.0722 * ((c >> 10) & 31)


def row_specs(path):
    """'; @rows <v> <top> <bottom>' header lines of an art file -> {variant index: (top, bottom)}, each 'own' or 'S'."""
    out = {}
    for line in path.read_text().splitlines():
        if line.startswith("; @rows"):
            w = line.split()
            if len(w) != 5 or w[2] not in ("a", "b", "c") or not {w[3], w[4]} <= {"own", "S"}:
                raise ArtError(f"{path.name}: '{line}': want '; @rows <a|b|c> <own|S> <own|S>'")
            out["abc".index(w[2])] = (w[3], w[4])
    return out


def index0_holes(art):
    """Index-0 pixels the figure encloses (not reachable from the 16x16 border through index 0)."""
    todo = [(x, y) for y in range(16) for x in range(16) if (x in (0, 15) or y in (0, 15)) and art[y][x] == "."]
    seen = set(todo)
    while todo:
        x, y = todo.pop()
        for xx, yy in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= xx < 16 and 0 <= yy < 16 and (xx, yy) not in seen and art[yy][xx] == ".":
                seen.add((xx, yy))
                todo.append((xx, yy))
    return [(x, y) for y in range(16) for x in range(16) if art[y][x] == "." and (x, y) not in seen]


def check_rows(name, art, top, bot):
    """An enhanced frame's row palettes (3 RGB15 each, art indices 1-3): a colour in both keeps its index (the DMG grey
    and the art stay the same across row 8), each is ordered light to dark (DMG), and no index 0 lies inside the figure
    (a lifted patron would be see-through there)."""
    for i, c in enumerate(top):
        if c in bot and bot.index(c) != i:
            raise ArtError(f"{name}: colour {c_hex(c)} is index {i + 1} in the top-row palette but {bot.index(c) + 1} in "
                           "the bottom-row one (a colour both rows use must keep its index)")
    for pal, which in ((top, "top"), (bot, "bottom")):
        if not c_lum(pal[0]) > c_lum(pal[1]) > c_lum(pal[2]):
            raise ArtError(f"{name}: the {which}-row palette {[c_hex(c) for c in pal]} is not ordered light to dark (DMG)")
    h = index0_holes(art)
    if h:
        raise ArtError(f"{name}: index 0 inside the figure at (x, y) {h[:6]}: a lifted patron would be see-through there")


def lift_columns(name, art, top, bot, objpals, own):
    """The two 8x16 columns of the shift-0 pose (x 0-7, x 8-15) as lifted: per column (OAM attribute, None or the 32 bytes
    of its re-indexed tile pair for VRAM bank 1). objpals: {OBJ slot: [3 RGB15]}; own: the variant's own slot (tried
    first). Raises ArtError when a column needs more than 3 colours or its colours are in no OBJ palette."""
    out = []
    for cx, side in ((0, "left"), (8, "right")):
        px = [(x, y, IDX[art[y][x]]) for y in range(16) for x in range(cx, cx + 8) if IDX[art[y][x]]]

        def colour(y, i):
            return (top if y < 8 else bot)[i - 1]
        cols = sorted({colour(y, i) for _, y, i in px})
        quad = {q: sorted({c_hex(colour(y, i)) for x, y, i in px if (y >= 8) == q}) for q in (0, 1)}
        if len(cols) > 3:
            raise ArtError(f"{name}: the {side} column (x {cx}-{cx + 7}) has {len(cols)} colours (top quadrant "
                           f"{quad[0]}, bottom {quad[1]}); a lifted 8x16 entry shows 3: each quadrant's colours must be in "
                           "its row palette and in one OBJ palette for the whole column")
        order = [own] + [k for k in objpals if k != own]
        same = [k for k in order if all(objpals[k][i - 1] == colour(y, i) for _, y, i in px)]
        if same:
            out.append((same[0], None))
            continue
        fit = [k for k in order if set(cols) <= set(objpals[k])]
        if not fit:
            have = {k: [c_hex(c) for c in v] for k, v in objpals.items()}
            raise ArtError(f"{name}: the {side} column (x {cx}-{cx + 7}) needs {[c_hex(c) for c in cols]} (top quadrant "
                           f"{quad[0]}, bottom {quad[1]}), which no OBJ palette of the group holds ({have}); put them in "
                           f"<group>_x (OBJ {OBJPAL_X}, assets/palettes.json)")
        k = fit[0]
        rows = ["".join(".-+#"[objpals[k].index(colour(y, IDX[art[y][x]])) + 1] if IDX[art[y][x]] else "."
                        for x in range(cx, cx + 8)) for y in range(16)]
        out.append((k | OAM_BANK1, tile_bytes(rows, 0, 0) + tile_bytes(rows, 0, 8)))
    return out


def enhanced_group(gi, g, fronts, backs, pj):
    """Group g's row palettes / lift attributes per variant, validated. Returns (table of 24 bytes: front top[4], front
    bottom[4], back top[4], back bottom[4], lifted left column attribute[4], right[4] (variant 3 = variant 0, never
    used); bank-1 columns [(variant, column k 0/1, 32 bytes)]; per enhanced variant the palettes for the preview)."""
    t = THEMES[gi]
    vp = json.loads((ROOT / f"assets/approved/venues/{t}_pal.json").read_text())
    wall = r15(vp["bar"]["hex"][0])
    s_pal = [r15(h) for h in vp["bar_b"]["hex"][1:]] if "bar_b" in vp else None
    own = [[r15(h) for h in pj[n]["hex"]] for n in VARIANT_PALS.get(g, [f"{g}_{v}" for v in "abc"])]
    objpals = {OBJPAL_VARIANT[v]: own[v] for v in range(3)}
    if f"{g}_x" in pj:
        objpals[OBJPAL_X] = [r15(h) for h in pj[f"{g}_x"]["hex"]]
    fs = row_specs(ROOT / f"assets/art/patrons/{g}.txt")
    bs = row_specs(ROOT / f"assets/art/patrons/{g}_back.txt")
    if gi == 0 and 0 in fs:
        raise ArtError(f"{g}.txt: variant a is the title scene's patron (src/title.c: one BG palette); it cannot be enhanced")

    def pal(v, which, fname):
        if which == "own":
            return BGPAL_PATRON + v, own[v]
        if s_pal is None:
            raise ArtError(f"{fname}: variant {'abc'[v]} uses S, the venue's bar_b palette (BG {BGPAL_S}), but "
                           f"{t}_pal.json has no bar_b: add one (colour 0 = the wall {vp['bar']['hex'][0]})")
        return BGPAL_S, s_pal
    tab = [0] * 24
    b1, looks = [], {}
    for v in range(3):
        (ft, fp), (fb, fq) = (pal(v, w, f"{g}.txt") for w in fs.get(v, ("own", "own")))
        (bt, bp), (bb, bq) = (pal(v, w, f"{g}_back.txt") for w in bs.get(v, ("own", "own")))
        name = f"{g}.txt variant {'abc'[v]}"
        if v in fs:
            check_rows(name, fronts[v], fp, fq)
        if v in bs:
            check_rows(f"{g}_back.txt variant {'abc'[v]}", backs[v], bp, bq)
        cols = lift_columns(name, fronts[v], fp, fq, objpals, OBJPAL_VARIANT[v])
        tab[v], tab[4 + v], tab[8 + v], tab[12 + v] = ft, fb, bt, bb
        tab[16 + v], tab[20 + v] = cols[0][0], cols[1][0]
        for k, (_, data) in enumerate(cols):
            if data is not None:
                b1.append((v, k, data))
        if v in fs or v in bs:
            looks[v] = {"front": (fp, fq), "back": (bp, bq), "lift": [objpals[a & 7] for a, _ in cols],
                        "lift_rows": [d for _, d in cols], "wall": wall}
    for k in range(6):
        tab[k * 4 + 3] = tab[k * 4]
    return tab, b1, looks


def enhanced_preview(path, art, back, look):
    """x8: the BG copy at shifts 0-7 (24x16 each, true CGB colours on the wall), the lifted pose, the back view, DMG."""
    def rgb(c):
        return ((c & 31) << 3, ((c >> 5) & 31) << 3, ((c >> 10) & 31) << 3)
    wall = rgb(look["wall"])
    frames = []
    for s in range(PATRON_SHIFTS):
        im = Image.new("RGB", (24, 16), wall)
        for y in range(16):
            for x in range(16):
                i = IDX[art[y][x]]
                if i:
                    im.putpixel((s + x, y), rgb(look["front"][y >= 8][i - 1]))
        frames.append(im)
    im = Image.new("RGB", (16, 16), wall)                 # lifted: each column through its OBJ palette and tiles
    for k in range(2):
        data = look["lift_rows"][k]
        for y in range(16):
            for x in range(8):
                if data is None:
                    i = IDX[art[y][k * 8 + x]]
                else:
                    o = (y // 8) * 16 + (y % 8) * 2
                    i = ((data[o] >> (7 - x)) & 1) | (((data[o + 1] >> (7 - x)) & 1) << 1)
                if i:
                    im.putpixel((k * 8 + x, y), rgb(look["lift"][k][i - 1]))
    frames.append(im)
    im = Image.new("RGB", (16, 16), wall)
    for y in range(16):
        for x in range(16):
            i = IDX[back[y][x]]
            if i:
                im.putpixel((x, y), rgb(look["back"][y >= 8][i - 1]))
    frames.append(im)
    for a in (art, back):
        im = Image.new("RGB", (16, 16))
        for y in range(16):
            for x in range(16):
                im.putpixel((x, y), GREY[IDX[a[y][x]]])
        frames.append(im)
    W = sum(f.width + 2 for f in frames)
    out = Image.new("RGB", (W, 16), (255, 0, 255))
    x0 = 0
    for f in frames:
        out.paste(f, (x0, 0))
        x0 += f.width + 2
    out.resize((W * 8, 128), Image.NEAREST).save(path)


def main():
    try:
        _main()
    except ArtError as e:
        sys.exit(f"gen_art: {e}")


def _main():
    outdir, prev = Path(sys.argv[1]), Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True); prev.mkdir(parents=True, exist_ok=True)
    c = ["// generated by tools/gen_art.py -- do not edit", "#include <gb/gb.h>", '#include "art.h"',
         "// the tile data lives in a switchable ROM bank (autobank) to keep the fixed bank free for code; main.c copies",
         "// it to VRAM through bkg_data() / spr_data(), which switch to BANK(art_tiles)",
         "#pragma bank 255", "BANKREF(art_tiles)", ""]
    h = ["// generated by tools/gen_art.py -- do not edit", "#ifndef ART_H", "#define ART_H",
         "#include <stdint.h>", ""]

    # ---- BG tileset: fixed venue slots (stage, bar) first, then the shared tiles of bar.txt ----
    h += [f"#define TILE_STAGE_BASE 0        // the venue pool: stage ids from 0 up, bar ids venue.bar_base..{VENUE_POOL - 1}",
          f"#define VENUE_POOL {VENUE_POOL}           // (load_venue); stage_n + bar_n <= VENUE_POOL",
          f"#define TITLE_TEXT_SLOT {TITLE_TEXT_SLOT}      // the title's menu text ids 0.. (never a bar id)",
          f"#define TILE_GENERIC_BASE {VENUE_POOL}   // the shared tiles below (bar_tiles[])", ""]
    gbase = VENUE_POOL
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
    # HUD icons of a shift (assets/art/hud_icons.txt): FLAG, MUGCHECK, CATCH, one tile each, loaded at BG ids the scene's
    # other tiles do not use (src/main_cold.c hud_icons_load, src/story.c)
    ic = []
    for i, (name, rows) in enumerate(blocks(ROOT / "assets/art/hud_icons.txt", named=True)):
        assert len(rows) == 8 and all(len(r) == 8 for r in rows), f"hud_icons {name}: not 8x8"
        h.append(f"#define HUD_ICON_{name.upper()} {i}   // index in hud_icon_tiles[]")
        ic += tile_bytes(rows, 0, 0)
    h += ["extern const uint8_t hud_icon_tiles[];   // FLAG, MUGCHECK, CATCH (16 bytes each)", ""]
    c.append(fmt("hud_icon_tiles", ic))
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
    # ---- glass (breaking drink): generated per venue (crash_frames, loaded with the venue's drink); ids only here ----
    h[-2:-2] = ["#define GLASS_FRAMES 4", f"#define GLASS_TILE_COUNT {GLASS_TILES}",
                "#define GLASS_TIP 0", "#define GLASS_FALL_FULL 2", "#define GLASS_FALL_EMPTY 6",
                "#define GLASS_SHATTER 10", "#define GLASS_SETTLE 12", ""]

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

    # ---- show performers (M9): per venue a dance of 4 frames 16x24 or a band of 6 (<t>_show.txt, show_tiles) ----
    h[-2:-2] = ["#define DANCER_FRAMES 4", "#define DANCER_TILE_COUNT 32", ""]

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
    cats = [r for _, r in blocks(ROOT / "assets/art/cat_walk.txt")]      # level 3's bar cat: 4 walk frames (2 leg steps x tail down / up), 16x16
    assert len(cats) == 4 and all(len(f) == 16 and len(f[0]) == 16 for f in cats)
    cats = [h for f in cats for h in ([r[:8] for r in f], [r[8:] for r in f])]     # per frame: left, right (8x16 entries)
    bt2 = []
    for f in cans + low + geys + drops + cats:
        bt2 += tile_bytes(f, 0, 0) + tile_bytes(f, 0, 8)
    bh = ["// generated by tools/gen_art.py -- do not edit", "#define CAN_FRAMES 5", "#define CAN_TILE_COUNT 10",
          "#define GEYSER_FRAMES 6", "#define DROP_FRAMES 3", "#define CAT_FRAMES 4", f"#define BONUS_TILE_COUNT {len(bt2) // 16}", ""]
    bh.append(fmt("bonus_tiles", bt2).replace("const uint8_t", "static const uint8_t"))
    (outdir / "can_tiles.h").write_text("\n".join(bh))
    png(cans, prev / "can_x8.png", 8, transparent=True)
    png(low, prev / "cursor_x8.png", 8, transparent=True)
    png(geys + drops, prev / "geyser_droplets_x8.png", 8, transparent=True)
    png(cats, prev / "cat_walk_x8.png", 8, transparent=True)

    # ---- the Practice list's scroll arrows (up, down) -> build/list_arrows.h, #included by src/mg_list.c ----
    arr = [r for _, r in blocks(ROOT / "assets/art/list_arrows.txt")]
    assert len(arr) == 2 and all(len(f) == 16 and len(f[0]) == 8 for f in arr)   # 8x16 OBJ entries
    at = []
    for f in arr:
        at += tile_bytes(f, 0, 0) + tile_bytes(f, 0, 8)
    (outdir / "list_arrows.h").write_text("// generated by tools/gen_art.py -- do not edit\n"
                                          + fmt("list_arrow_tiles", at).replace("const uint8_t", "static const uint8_t"))
    png(arr, prev / "list_arrows_x8.png", 8, transparent=True)

    # ---- the Practice list's keys-line buttons (A, B, right) -> build/list_keys.h (BG tiles, light on the HUD band) ----
    keys = [r for _, r in blocks(ROOT / "assets/art/list_keys.txt")]
    assert len(keys) == 3 and all(len(f) == 8 and len(f[0]) == 8 for f in keys)
    kt = []
    for f in keys:
        kt += tile_bytes(f, 0, 0)
    (outdir / "list_keys.h").write_text("// generated by tools/gen_art.py -- do not edit\n"
                                        + fmt("list_key_tiles", kt).replace("const uint8_t", "static const uint8_t"))
    png(keys, prev / "list_keys_x8.png", 8)

    # ---- the full-screen lists' wood-wall tiles (seam, header edge, three medal icons) -> build/list_skin.h ----
    skin = [r for _, r in blocks(ROOT / "assets/art/list_skin.txt")]
    assert len(skin) == 4 and all(len(f) == 8 and len(f[0]) == 8 for f in skin)
    st = []
    for f in skin:
        st += tile_bytes(f, 0, 0)
    (outdir / "list_skin.h").write_text("// generated by tools/gen_art.py -- do not edit\n"
                                        + fmt("list_skin_tiles", st).replace("const uint8_t", "static const uint8_t"))
    png(skin, prev / "list_skin_x8.png", 8)

    bonus2_art(outdir, prev)

    # ---- patrons: per group 3 variants x 8 shifts x (3x2 tiles), then 3 back views x (2x2 tiles) ----
    # The 16x16 patron is pasted at x offset 0..7 into a 24x16 canvas of colour 0 (the wall colour in the
    # patron palettes), so a patron moves in 1 px steps by swapping tilemap entries only. The back views
    # (patrons watching the show) only stand on a multiple of 8 px, so they need no shifts and no 3rd column.
    # M13a (Option A): each pose is stored column by column (top, bottom, next column ...) from an even first id
    # (PATRON_FIRST_TILE), shifts 1..7 first (v * 42 + (s - 1) * 6), the three shift-0 poses last (126 + v * 6, ids >= 128,
    # even), so a patron lifted to OBJ draws his shift-0 pose as two 8x16 entries straight from the BG copy: tiles t, t + 2.
    per_group = 3 * PATRON_SHIFTS * 6
    back_tiles = 3 * 4
    shift0_ofs = 3 * (PATRON_SHIFTS - 1) * 6
    patron_first = (n + 1) & ~1

    def pose_ofs(v, s):
        return shift0_ofs + v * 6 if s == 0 else v * (PATRON_SHIFTS - 1) * 6 + (s - 1) * 6
    assert patron_first + shift0_ofs >= 128 and (patron_first + shift0_ofs) % 2 == 0
    load = ["// generated by tools/gen_art.py -- do not edit", "#include <gb/gb.h>", '#include "art.h"', "#pragma bank 255",
            "void bkg_data_far(uint8_t first, uint8_t n, const uint8_t *d, uint8_t bank);   // src/main.c (ROM0)",
            "void spr_data_far(uint8_t first, uint8_t n, const uint8_t *d, uint8_t bank);   // src/main.c (ROM0)", ""]
    cases, cases0 = [], []
    pj = json.loads((ROOT / "assets/palettes.json").read_text())
    enh_tab, enh_b1, enh_json = [], [], {}
    for gi, g in enumerate(PATRON_GROUPS):
        vs = [r for _, r in blocks(ROOT / f"assets/art/patrons/{g}.txt")]
        assert len(vs) == 3 and all(len(v) == 16 and all(len(r) == 16 for r in v) for v in vs), g
        bs = [r for _, r in blocks(ROOT / f"assets/art/patrons/{g}_back.txt")]
        assert len(bs) == 3 and all(len(v) == 16 and all(len(r) == 16 for r in v) for v in bs), g + "_back"
        poses, shifted_rows = [None] * per_group, []
        for vi, v in enumerate(vs):
            for s in range(PATRON_SHIFTS):
                canvas = ["." * s + v[y] + "." * (24 - 16 - s) for y in range(16)]
                o = pose_ofs(vi, s)
                for k, tx in enumerate((0, 8, 16)):
                    poses[o + 2 * k] = tile_bytes(canvas, tx, 0)
                    poses[o + 2 * k + 1] = tile_bytes(canvas, tx, 8)
                shifted_rows.append(canvas)
        assert all(t is not None for t in poses)
        pt = [b for t in poses for b in t]
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
        cases.append(f"    case {gi}: bkg_data_far(first, PATRON_GROUP_TILES, {sym}, BANK({sym})); break;")
        cases0.append(f"    case {gi}: spr_data_far(first, 3, {sym} + (PATRON_SHIFT0_OFS + v * 6 + 3 * h) * 16, BANK({sym})); break;")
        png(vs + bs, prev / f"patrons_{g}_x8.png", 8)
        tab, b1, looks = enhanced_group(gi, g, vs, bs, pj)        # (M14a) validates every variant's lifted columns
        enh_tab.append(tab)
        enh_b1.append([(patron_first + pose_ofs(v, 0) + 2 * k, data) for v, k, data in b1])
        enh_json[g] = {"tab": tab, "bank1": {str(t): d for t, d in enh_b1[-1]}, "enhanced": sorted(looks)}
        for v, look in looks.items():
            enhanced_preview(prev / f"patrons_{g}_{'abc'[v]}_enhanced_x8.png", vs[v], bs[v], look)
        if g == PATRON_GROUPS[0]:
            png(shifted_rows[:PATRON_SHIFTS], prev / "patrons_shifted_x8.png", 8)
    load += ["", "// LCD off (or VBlank) only: the group's 156 BG tiles to ids first..first+155",
             "// (a switchable bank of its own: bkg_data_far, in ROM0, maps the group's bank while it copies)",
             "void load_patron_tiles(uint8_t g, uint8_t first) BANKED {", "    switch (g) {"]
    load += cases + ["    }", "}", ""]
    load += ["// the credits' cast cards (src/credits.c): half h (3 tiles: the first or the last 3 of its 6) of variant v's shift-0 pose of the group as OBJ tiles first..first+2",
             "void load_patron_pose0(uint8_t g, uint8_t first, uint8_t v, uint8_t h) BANKED {", "    switch (g) {"] + cases0 + ["    }", "}", ""]
    (outdir / "patron_load.c").write_text("\n".join(load))
    eh = ["// generated by tools/gen_art.py (enhanced_group) -- do not edit; #included by src/enhance.c (its bank)",
          "// per group: BG palette slot of the front view's top tile row [v], bottom row [4 + v], the back view's top [8 + v],",
          "// bottom [12 + v]; the lifted pose's OAM attributes (CGB) left column [16 + v], right column [20 + v] (bit 3: VRAM bank 1)",
          f"static const uint8_t enh_tab[{len(PATRON_GROUPS)}][24] = {{"]
    eh += ["    { " + ", ".join(map(str, t)) + " },   // " + g for t, g in zip(enh_tab, PATRON_GROUPS)]
    eh += ["};", "// per group: re-indexed lifted columns for CGB VRAM bank 1: { first tile id, 2 tiles (32 bytes) } each"]
    for g, cols in zip(PATRON_GROUPS, enh_b1):
        if cols:
            data = [b for t, d in cols for b in [t] + d]
            eh.append(fmt(f"enh_b1_{g}", data).replace("const uint8_t", "static const uint8_t"))
    eh.append(f"static const uint8_t enh_b1_n[{len(PATRON_GROUPS)}] = {{ " + ", ".join(str(len(c)) for c in enh_b1) + " };")
    eh.append(f"static const uint8_t * const enh_b1[{len(PATRON_GROUPS)}] = {{ "
              + ", ".join(f"enh_b1_{g}" if c else "0" for g, c in zip(PATRON_GROUPS, enh_b1)) + " };")
    (outdir / "patron_enh.h").write_text("\n".join(eh) + "\n")
    (outdir / "patron_enh.json").write_text(json.dumps(enh_json))
    h[-2:-2] = [f"#define PATRON_GROUPS {len(PATRON_GROUPS)}",
                f"#define PATRON_SHIFTS {PATRON_SHIFTS}",
                f"#define PATRON_FIRST_TILE {patron_first}   // BG id of a group's first patron tile (even: BAR_TILE_COUNT rounded up)",
                f"#define PATRON_SHIFT0_OFS {shift0_ofs}   // the three shift-0 poses: PATRON_FIRST_TILE + this + v * 6 (ids >= 128, even)",
                f"#define PATRON_TILES_PER_GROUP {per_group}   // 3 variants x 8 shifts x 6 tiles (3x2)",
                f"#define PATRON_BACK_TILES {back_tiles}   // then 3 back views x 4 tiles (2x2), shift 0 only",
                f"#define PATRON_GROUP_TILES {per_group + back_tiles}",
                "// tile of (variant v, shift s, row r, column k), column-major: pose + k * 2 + r, pose = s ? v * 42 + (s - 1) * 6 : 126 + v * 6;",
                "// back view of v: PATRON_TILES_PER_GROUP + v * 4 + r * 2 + k",
                "// group order: " + ", ".join(PATRON_GROUPS),
                "void load_patron_tiles(uint8_t g, uint8_t first) BANKED;   // build/patron_load.c",
                "void load_patron_pose0(uint8_t g, uint8_t first, uint8_t v, uint8_t h) BANKED;   // build/patron_load.c: half h (3 tiles) of variant v's shift-0 pose as OBJ tiles (the credits cast)", ""]

    (outdir / "art.h").write_text("\n".join(h))
    (outdir / "art.c").write_text("\n".join(c))


if __name__ == "__main__":
    main()
