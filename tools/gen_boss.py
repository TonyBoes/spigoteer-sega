#!/usr/bin/env python3
"""Boss art -> build/boss_art.h (src/boss.c: the shared meter, the pose numbering), build/boss_<name>_art.h (each boss's
own art, #included by its own src/boss_<name>.c and nowhere else, so it lands in that file's bank), build/boss.json
(tests) and x8 previews in out/preview/.

  assets/art/boss/<boss>.txt   per boss (BOSSES below): the body poses (WALK, STOMP, GULP, WINCE, HAPPY: W x 16, BG,
                               on his bar's two wall rows), then the boss's own extra poses in his `extra` list (the
                               tells: Yeti INHALE / BLOW, the Critic's TASTE; the engine's pose numbers 5, 6, ... in
                               that order), the hand column with 1-3 held empties (HAND1..3, 8x16), the topper
                               (HAT_STILL, HAT_BOB: 8x16 OBJ) and the HUD face (ICON, 8x8), and his `tiles` (8x16 BG
                               blocks of his special's own, e.g. Leo's "!!": boss_art_tiles, loaded at BG 246..).
                               Other blocks in the file are not read.
  assets/art/boss/meter.txt    the HUD meter's 3 tiles (EMPTY, HALF, FULL; 2 pips a tile), shared by every boss

The body is stored as column pairs (a column's top tile, then its bottom tile, at consecutive ids: render.c's put_col
stamps a column as t, t + 1), identical columns shared. A fight borrows variant C's BG ids and the back views for them
(src/boss.h: 162-203 and 216-233, BOSS_PAIRS_MAX 30 pairs); the build fails on more. The palette is colour 0 = the
venue's wall (set at the load), then the art's colours 1-3 (CGB BG palette 4; the topper OBJ palette 7 takes the same
1-3). Replacing a file and running make is the swap.

A boss's own header (build/boss_<name>_art.h) uses the same names in every boss (boss_art_body, boss_art_pose, ...):
src/boss_load.h's loaders read them. A boss with "ice" also gets icy copies of that venue's counter tiles
(boss_ice_src: the venue's counter tile ids, boss_ice_tiles: their icy copies, the art file's ICE_A / ICE_B: the
owner-approved "icicles"; boss_spark_tiles: its SPARK1-4 sparkle frames).

For the bosses that move (boss wave 2; PLAN.md "Boss hooks as built"):
  - an `extra` pose narrower than his width (the Mascot's 16x16 dust puffs PUFF1 / PUFF2) is centred in it, the columns
    either side plain wall (colour 0): a pose like any other, stamped where he stands;
  - `fx`: [(block, boss)]: a 16x8 block (the landing MARKER) read from that boss's art file (his own, or another's:
    the Prototype's marker is the Mascot's), on a bar's lower wall row under 8 rows of plain wall: 2 column pairs
    (boss_art_fx, BOSS_ART_FX tiles), which src/boss_load.h loads at BOSS_MARK_BG (248-251). An 8x16 block (the
    Mothership's BEAM) covers both wall rows and is doubled side by side: the same two column pairs;
  - `hats`: extra 8x16 topper frames after HAT_STILL / HAT_BOB (the Prototype's lamp: LAMP_RING, LAMP_X), loaded with
    them from OBJ_TOPPER (BOSS_ART_HAT_TILES tiles in all);
  - `conveyor`: a venue whose counter gets the art file's CONV_A / CONV_B (8x8, 2 animation frames: boss_conv_tiles,
    BOSS_ART_CONV; the owner-approved K5 stripes on the front + K6 arrows on the top; colours 1-3 are BG palette 7's, see
    src/boss_prototype.c) over the venue's counter tiles (boss_conv_src).

Adding a boss: one BOSSES entry (and its art file). Usage: gen_boss.py outdir previewdir
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_art import blocks, png, rgb15, tile_bytes  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
POSES = ["WALK", "STOMP", "GULP", "WINCE", "HAPPY"]   # every boss's, the engine's pose numbers 0-4 (src/boss.h BP_*)
BOSS_POSES_MAX = 8           # src/boss.h: the 5 common poses + up to 3 extra (tells) per boss
SWAY_PX = 2                  # the drinking sway's shift: the patrons' (src/patrons.c drawn_x: +2 px on alternate beats)
BOSS_PAIRS_MAX = 30         # src/boss.h: 21 pairs at 162-203 + 9 at 216-233
BOSS_SPARK_N = 4             # the sparkle frames (BG 248-251: the Yeti has no landing marker)
BOSS_ICE_MAX = 2             # src/boss.h: icy counter tiles at BG 246.. (free in the story)
BOSS_FX_MAX = 4              # src/boss.h: the landing marker's 2 column pairs at BG 248-251 (BOSS_MARK_BG)
BOSS_HATS_MAX = 10           # topper frames (8x16) at OBJ 96..115 (the Critic: STILL, BOB, the cloche, the glint, the bubbles)
# per boss (the order of the hook table's ids does not matter): its art file, the C file it belongs to
# (src/boss_<name>.c), its body width (px), colours 1-3 (CGB), its extra poses (tells), and "ice": a venue whose
# counter tiles get icy copies.
BOSSES = [
    {"name": "big_tex", "width": 40, "pal": ["#F0B888", "#C83020", "#583018"], "extra": []},
    {"name": "sasquatch", "width": 32, "pal": ["#E8B878", "#5C2C14", "#140804"], "extra": ["DUCK", "BURST1", "BURST2"],
     "hats": ["HAT_DUCK"], "fx": [("MARKER", "sasquatch")], "nosway": True},   # (29 pairs of 30: a shifted GULP needs 4 more)
    {"name": "critic", "width": 32, "pal": ["#F8D0A8", "#A03070", "#201018"], "extra": ["TASTE", "HOLD", "HOLDHOP"],
     "hats": ["CLOCHE_END", "CLOCHE_MID", "GLINT", "NO_L", "NO_R", "BAD_L", "BAD_R"]},
    {"name": "yeti", "width": 32, "pal": ["#F8F8F8", "#80B0E8", "#182040"], "extra": ["INHALE", "BLOW"],
     "ice": "igloo"},
    {"name": "sumo", "width": 40, "pal": ["#F0A878", "#F0F0E0", "#282048"], "extra": ["SHIKO", "HMPH"], "nosway": True},
    {"name": "leo", "width": 32, "pal": ["#F8D060", "#C86018", "#301808"], "extra": ["INHALE", "ROAR"],
     "tiles": ["BANG"]},
    {"name": "mascot", "width": 32, "pal": ["#F8E8C8", "#D02828", "#201018"], "extra": ["CROUCH", "PUFF1", "PUFF2"],
     "fx": [("MARKER", "mascot")], "spr": [("BALL", 16, 16)]},
    {"name": "prototype", "width": 32, "pal": ["#E8F0F8", "#F87818", "#182030"], "extra": ["RED"],
     "hats": ["LAMP_RING", "LAMP_X"], "fx": [("MARKER", "mascot")], "conveyor": "factory",
     "spr": [("CHAIN", 8, 16), ("HOOK", 16, 16), ("SPARK1", 8, 16), ("SPARK2", 8, 16)]},
    {"name": "duke", "width": 40, "pal": ["#F8E0C8", "#D06030", "#201018"], "extra": ["TELL1", "TELL2"],
     "entrance": "duke_entrance"},
    {"name": "mothership", "width": 40, "pal": ["#E8F0F8", "#E040B0", "#200828"], "extra": [], "fx": [("BEAM", "mothership")]},
]
# The entrance's OBJ tiles (src/boss_duke.c): a fight borrows 32 ids (OBJ 96-127); the entrance, which plays before the first
# drink exists, borrows 36 more (OBJ 56-91, reloaded afterwards from the venue's own drink tiles). 8x16 pairs: 18 low, 16 high.
ENT_LOW, ENT_HIGH = 18, 16
ENT_LOW_ID, ENT_HIGH_ID = 56, 96      # the pool's OBJ ids
ENT_ORDER = ["BIKE", "DUST1", "DUST2", "DUST3", "RIDE", "SMOKE1", "SMOKE2", "HELM", "HOP"]   # the pool is filled in this order
ENT_LATE = ["BIKE", "DUST1", "DUST2", "DUST3"]          # still on screen after the landing: their tiles are reloaded last
ENT_EARLY = ["RIDE", "SMOKE1", "SMOKE2"]                # gone by the vault: the topper's ids (pairs 18, 19) may be theirs only
SPR_TILE0, SPR_PAIRS_MAX = 108, 10   # an entrance's own sprites (E8: the Mascot's ball, the Prototype's crane): OBJ 108..127, free in a fight
BOSS_TILES_MAX = 3         # "tiles": a boss's own 8x16 BG blocks (Leo's "!!"), at BG 246.. like the ice (6 ids)


def fail(msg):
    sys.exit(f"gen_boss: {msg}")


def frame(named, name, w, h, path):
    if name not in named:
        fail(f"{path.relative_to(ROOT)}: no @{name}")
    f = named[name]
    if len(f) != h or not all(len(r) == w and set(r) <= set(".-+#") for r in f):
        fail(f"{path.relative_to(ROOT)}: @{name} must be {w}x{h} in . - + #")
    return f


def padded(f, w):
    """A pose narrower than his width, centred: plain wall (colour 0) columns either side."""
    fw = len(f[0])
    left = ((w - fw) // 2) // 8 * 8
    return ["." * left + r + "." * (w - fw - left) for r in f]


def conveyor_tiles(theme, prev, name, named, path):
    """The venue's counter tile ids (columns 0-17) and the 2 conveyor frames, the art file's CONV_A / CONV_B (8x8)."""
    v = json.loads((ROOT / "build" / "venues.json").read_text())["venues"][theme]
    src = sorted(set(v["bar_map"][40:58]))
    frames = [frame(named, n, 8, 8, path) for n in ("CONV_A", "CONV_B")]
    png(frames, prev / f"boss_{name}_conveyor_x8.png", 8)
    return src, [x for f in frames for x in tile_bytes(f, 0, 0)]


def column(f, x):
    return tuple(tile_bytes(f, x, 0) + tile_bytes(f, x, 8))


def carr(name, data, t="uint8_t"):
    return f"static const {t} {name}[{len(data)}] = {{ " + ", ".join(f"0x{b:02X}" for b in data) + " };"


def rows_of(data):
    """16 tile bytes -> 8 rows of . - + #"""
    out = []
    for r in range(8):
        lo, hi = data[2 * r], data[2 * r + 1]
        out.append("".join(".-+#"[((lo >> (7 - c)) & 1) | (((hi >> (7 - c)) & 1) << 1)] for c in range(8)))
    return out


def ice_tiles(theme, prev, name, named, path):
    """The venue's counter tile ids (columns 0-17 of its bar map's counter row), their icy tiles (the art file's ICE_A for
    the lower id, which the even columns hold, and ICE_B) and the sparkle frames SPARK1-4 (ICE_A with a glint)."""
    v = json.loads((ROOT / "build" / "venues.json").read_text())["venues"][theme]
    src = sorted(set(v["bar_map"][40:58]))
    if len(src) > BOSS_ICE_MAX:
        fail(f"{name}: {theme}'s counter has {len(src)} different tiles, room for {BOSS_ICE_MAX} icy ones")
    if len(src) != 2 or v["bar_map"][40:58] != [src[0], src[1]] * 9:
        fail(f"{name}: {theme}'s counter must alternate two tiles (even columns the lower id): ICE_A / ICE_B, the sparkles")
    ice = [frame(named, n, 8, 8, path) for n in ("ICE_A", "ICE_B")]
    spark = [frame(named, f"SPARK{k}", 8, 8, path) for k in range(1, BOSS_SPARK_N + 1)]
    png(ice + spark, prev / f"boss_{name}_ice_x8.png", 8)
    return src, [x for f in ice for x in tile_bytes(f, 0, 0)], [x for f in spark for x in tile_bytes(f, 0, 0)]


def sway_pose(f, w):
    """The drinking sway (owner 2026-10-17: the patrons' technique): his GULP shifted SWAY_PX px sideways, drawn on every other
    beat of the patrons' sway (src/boss.c sip_beat). BG art is whole tiles, so the shifted copy is its own column pairs. It
    moves right like the patrons (1) unless that clips more ink off his right edge than a move left clips off his left (2:
    Duke, whose mug is at the right edge); what leaves the body's width is cut. Returns (direction, rows)."""
    d = SWAY_PX
    right = ["." * d + r[:w - d] for r in f]
    left = [r[d:] + "." * d for r in f]

    def ink(g):
        return sum(c != "." for r in g for c in r)
    return (1, right) if ink(left) <= ink(right) else (2, left)


def boss_art(b, prev):
    path = ROOT / "assets/art/boss" / f"{b['name']}.txt"
    named = dict(blocks(path, named=True))
    w = b["width"]
    names = POSES + b["extra"]
    if len(names) > BOSS_POSES_MAX:
        fail(f"{b['name']}: {len(names)} poses, the engine has room for {BOSS_POSES_MAX}")
    poses = []
    for n in names:
        fw = len(named[n][0]) if n in named else w
        if fw == w:
            poses.append(frame(named, n, w, 16, path))
        elif n in POSES or fw % 8 or fw > w:
            fail(f"{path.relative_to(ROOT)}: @{n} must be {w} px wide (an extra pose: or a narrower multiple of 8)")
        else:
            poses.append(padded(frame(named, n, fw, 16, path), w))
    hands = [frame(named, f"HAND{k}", 8, 16, path) for k in (1, 2, 3)]
    hat = [frame(named, n, 8, 16, path) for n in ["HAT_STILL", "HAT_BOB"] + b.get("hats", [])]
    if len(hat) > BOSS_HATS_MAX:
        fail(f"{b['name']}: {len(hat)} topper frames, room for {BOSS_HATS_MAX}")
    icon = frame(named, "ICON", 8, 8, path)
    pairs, index = [], {}

    def pair(col):
        if col not in index:
            index[col] = len(pairs)
            pairs.append(col)
        return index[col]

    sway = None if b.get("nosway") else sway_pose(named["GULP"], w)
    pose_map = [[pair(column(p, x)) for x in range(0, w, 8)] for p in poses]
    sway_map = [pair(column(sway[1], x)) for x in range(0, w, 8)] if sway else None
    hand_map = [pose_map[0][-1]] + [pair(column(h, 0)) for h in hands]
    if len(pairs) > BOSS_PAIRS_MAX:
        fail(f"{b['name']}: {len(pairs)} different body columns, the fight has room for {BOSS_PAIRS_MAX}")
    hat_tiles = []
    for f in hat:
        hat_tiles += tile_bytes(f, 0, 0) + tile_bytes(f, 0, 8)
    png(poses + ([sway[1]] if sway else []), prev / f"boss_{b['name']}_x8.png", 8)
    png(hands + hat, prev / f"boss_{b['name']}_hand_hat_x8.png", 8, transparent=True)
    png([icon], prev / f"boss_{b['name']}_icon_x8.png", 8)
    a = {"name": b["name"], "width": w, "cols": w // 8, "pairs": [list(p) for p in pairs], "poses": names,
         "pose": pose_map, "hand": hand_map, "hat": hat_tiles, "icon": tile_bytes(icon, 0, 0),
         "pal": rgb15(["#000000"] + b["pal"]), "art": {n: p for n, p in zip(names, poses)},
         "sway": sway[0] if sway else 0, "sway_map": sway_map, "sway_art": sway[1] if sway else None}
    if "ice" in b:
        if "fx" in b:
            fail(f"{b['name']}: the sparkles use BG 248-251, the landing marker's ids")
        a["ice_src"], a["ice"], a["spark"] = ice_tiles(b["ice"], prev, b["name"], named, path)
    if b.get("tiles"):
        if len(b["tiles"]) > BOSS_TILES_MAX or "ice" in b:
            fail(f"{b['name']}: room for {BOSS_TILES_MAX} blocks of his own at BG 246.. (and none with ice)")
        own = [frame(named, n, 8, 16, path) for n in b["tiles"]]
        a["tiles"] = [x for f in own for x in tile_bytes(f, 0, 0) + tile_bytes(f, 0, 8)]
        png(own, prev / f"boss_{b['name']}_tiles_x8.png", 8)
    if "fx" in b:
        fx, frames = [], []
        for block, owner in b["fx"]:
            fpath = ROOT / "assets/art/boss" / f"{owner}.txt"
            fnamed = dict(blocks(fpath, named=True))
            if len(fnamed.get(block, [])) == 16:     # an 8x16 block (the Mothership's BEAM): both wall rows, two columns wide
                f = [r + r for r in frame(fnamed, block, 8, 16, fpath)]
            else:
                f = ["." * 16] * 8 + frame(fnamed, block, 16, 8, fpath)   # (the lower wall row)
            frames.append(f)
            fx += list(column(f, 0) + column(f, 8))
        if len(fx) // 16 > BOSS_FX_MAX:
            fail(f"{b['name']}: {len(fx) // 16} fx tiles, room for {BOSS_FX_MAX}")
        png(frames, prev / f"boss_{b['name']}_fx_x8.png", 8)
        a["fx"] = fx
    if "conveyor" in b:
        a["conv_src"], a["conv"] = conveyor_tiles(b["conveyor"], prev, b["name"], named, path)
    if "entrance" in b:
        a["ent"] = entrance(b, prev)
    if "spr" in b:
        a["spr"] = sprites(b, named, path, prev)
    return a


def sprites(b, named, path, prev):
    """An entrance's own sprite frames (the art file's blocks, `spr`: [(name, w, h)]) cut into 8x16 cells (equal cells share a
    tile pair; no mirroring, so a frame's X flip stays the code's): the pairs (top tile, bottom tile: 32 bytes each, OBJ
    SPR_TILE0 + 2 * pair) and per frame its cells (dx, dy, pair)."""
    pairs, index, frames = [], {}, {}
    for n, w, h in b["spr"]:
        f = frame(named, n, w, h, path)
        cells = []
        for y in range(0, h, 16):
            for x in range(0, w, 8):
                k = tuple(f[y + j][x:x + 8] for j in range(16))
                if all(set(r) == {"."} for r in k):
                    continue
                if k not in index:
                    index[k] = len(pairs)
                    pairs.append(tile_bytes(f, x, y) + tile_bytes(f, x, y + 8))
                cells.append((x, y, index[k]))
        frames[n] = cells
    if len(pairs) > SPR_PAIRS_MAX:
        fail(f"{b['name']}: the entrance's sprites need {len(pairs)} tile pairs, OBJ 108-127 has {SPR_PAIRS_MAX}")
    png([frame(named, n, w, h, path) for n, w, h in b["spr"]], prev / f"boss_{b['name']}_entrance_x8.png", 8, transparent=True)
    return {"pairs": [list(p) for p in pairs], "frames": frames}


def entrance(b, prev):
    """Duke's entrance frames (assets/art/<entrance>.txt: RIDE, BIKE 48x32, HOP 24x32, DUST1-3, SMOKE1-2, HELM 8x16) cut into
    8x16 OBJ cells on an 8 x 16 grid, equal cells (and mirrored ones, with the X flip) sharing a tile pair. Returns the pairs
    (32 bytes each, top tile then bottom) and, per frame, its cells (dx, dy, pair, flip)."""
    path = ROOT / "assets/art" / f"{b['entrance']}.txt"
    named = dict(blocks(path, named=True))
    size = {"RIDE": (48, 32), "BIKE": (48, 32), "HOP": (24, 32), "HELM": (8, 16)}
    pairs, index, frames = [], {}, {}

    def key(f, x, y):
        return tuple(f[y + j][x:x + 8] for j in range(16))

    for n in ENT_ORDER:
        w, h = size.get(n, (8, 16))
        f = frame(named, n, w, h, path)
        cells = []
        for y in range(0, h, 16):
            for x in range(0, w, 8):
                k = key(f, x, y)
                if all(set(r) == {"."} for r in k):
                    continue
                m = tuple(r[::-1] for r in k)
                if k in index:
                    p, fl = index[k], 0
                elif m in index:
                    p, fl = index[m], 1
                else:
                    p, fl = len(pairs), 0
                    index[k] = p
                    pairs.append(tile_bytes(f, x, y) + tile_bytes(f, x, y + 8))
                cells.append((x, y, p, fl))
        frames[n] = cells
    if len(pairs) > ENT_LOW + ENT_HIGH:
        fail(f"{b['name']}: the entrance needs {len(pairs)} tile pairs, the pool has {ENT_LOW + ENT_HIGH}")
    late = {c[2] for n in ENT_LATE for c in frames[n]}
    if max(late) >= ENT_LOW:
        fail(f"{b['name']}: the entrance's late frames (the bike, the dust) must fit the low pairs (OBJ 56-91)")
    topper = {c[2] for n in frames if n not in ENT_EARLY for c in frames[n]}
    if topper & {ENT_LOW, ENT_LOW + 1}:
        fail(f"{b['name']}: OBJ 96-99 (the topper's ids, reloaded at the vault) are used by a frame that is still on screen")
    png([frame(named, n, *size.get(n, (8, 16)), path) for n in ENT_ORDER], prev / "boss_duke_entrance_x8.png", 8, transparent=True)
    return {"pairs": [list(p) for p in pairs], "frames": frames}


def header(a):
    """build/boss_<name>_art.h: the boss's own data under the common names src/boss_load.h reads."""
    h = [f"// generated by tools/gen_boss.py from assets/art/boss/{a['name']}.txt -- do not edit; #included by "
         f"src/boss_{a['name']}.c only (its bank)",
         f"// {len(a['pairs'])} body columns (top tile, bottom tile), {a['cols']} wide; poses: " + ", ".join(a["poses"]),
         f"#define BOSS_ART_PAIRS {len(a['pairs'])}",
         f"#define BOSS_ART_POSES {len(a['poses'])}",
         f"#define BOSS_ART_COLS {a['cols']}",
         carr("boss_art_body", [x for p in a["pairs"] for x in p]),
         f"static const uint8_t boss_art_pose[BOSS_ART_POSES][BOSS_ART_COLS] = {{ "
         + ", ".join("{ " + ", ".join(str(v) for v in row) + " }" for row in a["pose"]) + " };",
         carr("boss_art_hand", a["hand"]) + "   // the hand column holding 0..3 empties"]
    if a["sway"]:
        h += [f"#define BOSS_ART_SWAY {a['sway']}   // his drinking sway moves him right (1) or left (2): the row's `sway`",
              "static const uint8_t boss_art_sway[BOSS_ART_COLS] = { " + ", ".join(str(v) for v in a["sway_map"]) + " };"
              f"   // his GULP shifted {SWAY_PX} px: the pose BP_SWAY"]
    h += [
         f"#define BOSS_ART_HAT_TILES {len(a['hat']) // 16}",
         carr("boss_art_hat", a["hat"]) + "   // STILL top, bottom, BOB top, bottom (then his `hats`)",
         carr("boss_art_icon", a["icon"]),
         carr("boss_art_pal", a["pal"], "uint16_t") + "   // colour 0: the venue's wall, set at the load"]
    if "ice" in a:
        h += [f"#define BOSS_ART_ICE {len(a['ice_src'])}",
              carr("boss_ice_src", a["ice_src"]) + "   // the venue's counter tile ids",
              carr("boss_ice_tiles", a["ice"]) + "   // their icy copies (ICE_A, ICE_B)",
              f"#define BOSS_ART_SPARK {BOSS_SPARK_N}",
              carr("boss_spark_tiles", a["spark"]) + "   // the sparkle frames (SPARK1-4)"]
    if "tiles" in a:
        h += [f"#define BOSS_ART_TILES {len(a['tiles']) // 32}   // his own 8x16 BG blocks (top, bottom) for BG 246..",
              carr("boss_art_tiles", a["tiles"])]
    if "fx" in a:
        h += [f"#define BOSS_ART_FX {len(a['fx']) // 16}", carr("boss_art_fx", a["fx"]) + "   // the landing marker"]
    if "ent" in a:
        e = a["ent"]
        names = list(e["frames"])
        flat = [c for n in names for c in e["frames"][n]]
        first = [0]
        for n in names:
            first.append(first[-1] + len(e["frames"][n]))
        h += [f"#define BOSS_ART_ENT_PAIRS {len(e['pairs'])}   // the entrance's 8x16 tile pairs: the first {ENT_LOW} at OBJ 56.., the rest at OBJ 96..",
              carr("boss_ent_tiles", [x for p in e["pairs"] for x in p]),
              "// entrance frames: " + ", ".join(f"{n} {i}" for i, n in enumerate(names))]
        h += [f"#define ENT_{n} {i}" for i, n in enumerate(names)]
        h += [carr("boss_ent_first", first) + "   // each frame's first cell (and the next one's: its end)",
              carr("boss_ent_cells", [v for c in flat for v in (c[0], c[1], ENT_LOW_ID + 2 * c[2] if c[2] < ENT_LOW
                                                               else ENT_HIGH_ID + 2 * (c[2] - ENT_LOW), 0x20 if c[3] else 0)])
              + "   // per cell: dx, dy, its OBJ tile id (the pool: 56.. for the first 18 pairs, 96.. for the rest), S_FLIPX when mirrored"]
    if "spr" in a:
        e = a["spr"]
        names = list(e["frames"])
        flat = [c for n in names for c in e["frames"][n]]
        first = [0]
        for n in names:
            first.append(first[-1] + len(e["frames"][n]))
        h += [f"#define BOSS_ART_SPR_PAIRS {len(e['pairs'])}   // the entrance's own 8x16 tile pairs, at OBJ {SPR_TILE0} + 2 * pair",
              f"#define BOSS_SPR_TILE0 {SPR_TILE0}",
              carr("boss_spr_tiles", [x for p in e["pairs"] for x in p])]
        h += [f"#define SPR_{n} {i}" for i, n in enumerate(names)]
        h += [carr("boss_spr_first", first) + "   // each frame's first cell (and the next one's: its end)",
              carr("boss_spr_cells", [v for c in flat for v in c]) + "   // per cell: dx, dy, its tile pair"]
    if "conv" in a:
        h += [f"#define BOSS_ART_CONV {len(a['conv']) // 16}", f"#define BOSS_ART_CONV_SRC {len(a['conv_src'])}",
              carr("boss_conv_tiles", a["conv"]) + "   // the conveyor's 2 frames (CONV_A, CONV_B)",
              carr("boss_conv_src", a["conv_src"]) + "   // the venue's counter tile ids they replace"]
    return "\n".join(h) + "\n"


def main():
    outdir, prev = Path(sys.argv[1]), Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True); prev.mkdir(parents=True, exist_ok=True)
    mpath = ROOT / "assets/art/boss/meter.txt"
    mnamed = dict(blocks(mpath, named=True))
    meter = [frame(mnamed, n, 8, 8, mpath) for n in ("EMPTY", "HALF", "FULL")]
    meter_bytes = [x for f in meter for x in tile_bytes(f, 0, 0)]
    png(meter, prev / "boss_meter_x8.png", 8)
    tpath = ROOT / "assets/art/boss/tag.txt"          # the status tag (src/boss.c only: build/boss_tag_art.h)
    tnamed = dict(blocks(tpath, named=True))
    tag = [frame(tnamed, n, 8, 16, tpath) for n in ("READY", "BUSY")]
    tag_bytes = [x for f in tag for x in tile_bytes(f, 0, 0) + tile_bytes(f, 0, 8)]
    png(tag, prev / "boss_tag_x8.png", 8, transparent=True)
    (outdir / "boss_tag_art.h").write_text("// generated by tools/gen_boss.py from assets/art/boss/tag.txt -- do not edit; #included by src/boss.c only\n"
                                          + carr("boss_tag_tiles", tag_bytes) + "   // READY, BUSY: 8x16 each\n")
    names = [b["name"] for b in BOSSES]
    if len(set(names)) != len(names):
        fail("a boss is listed twice")
    files = {p.stem for p in (ROOT / "assets/art/boss").glob("*.txt")} - {"meter", "tag"}
    if files != set(names):
        fail(f"assets/art/boss/ and BOSSES differ: {sorted(files ^ set(names))}")
    arts = [boss_art(b, prev) for b in BOSSES]
    h = ["// generated by tools/gen_boss.py from assets/art/boss/*.txt -- do not edit; #included by src/boss.c",
         f"#define BOSS_POSES_MAX {BOSS_POSES_MAX}   // " + ", ".join(POSES) + ", then each boss's extra poses",
         f"#define BOSS_PAIRS_MAX {BOSS_PAIRS_MAX}",
         f"#define BOSS_ICE_MAX {BOSS_ICE_MAX}",
         f"#define BOSS_FX_MAX {BOSS_FX_MAX}",
         f"#define BOSS_HATS_MAX {BOSS_HATS_MAX}",
         "#ifdef BOSS_WANT_METER   // (only src/boss.c and src/boss_sumo.c use it: a copy in every module that includes boss.h was 528 B)",
         carr("boss_meter_tiles", meter_bytes) + "   // EMPTY, HALF, FULL",
         "#endif"]
    (outdir / "boss_art.h").write_text("\n".join(h) + "\n")
    for a in arts:
        (outdir / f"boss_{a['name']}_art.h").write_text(header(a))
    (outdir / "boss.json").write_text(json.dumps({"meter": meter_bytes, "bosses": arts, "poses": POSES,
                                                  "pairs_max": BOSS_PAIRS_MAX, "poses_max": BOSS_POSES_MAX}))


if __name__ == "__main__":
    main()
