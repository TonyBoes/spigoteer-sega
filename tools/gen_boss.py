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
    (boss_art_fx, BOSS_ART_FX tiles), which src/boss_load.h loads at BOSS_MARK_BG (248-251);
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
BOSS_PAIRS_MAX = 30          # src/boss.h: 21 pairs at 162-203 + 9 at 216-233
BOSS_SPARK_N = 4             # the sparkle frames (BG 248-251: the Yeti has no landing marker)
BOSS_ICE_MAX = 2             # src/boss.h: icy counter tiles at BG 246.. (free in the story)
BOSS_FX_MAX = 4              # src/boss.h: the landing marker's 2 column pairs at BG 248-251 (BOSS_MARK_BG)
BOSS_HATS_MAX = 4            # topper frames (8x16) at OBJ 96..103
# per boss (the order of the hook table's ids does not matter): its art file, the C file it belongs to
# (src/boss_<name>.c), its body width (px), colours 1-3 (CGB), its extra poses (tells), and "ice": a venue whose
# counter tiles get icy copies.
BOSSES = [
    {"name": "big_tex", "width": 40, "pal": ["#F0B888", "#C83020", "#583018"], "extra": []},
    {"name": "sasquatch", "width": 32, "pal": ["#E8B878", "#5C2C14", "#140804"], "extra": []},
    {"name": "critic", "width": 32, "pal": ["#F8D0A8", "#A03070", "#201018"], "extra": ["TASTE"]},
    {"name": "yeti", "width": 32, "pal": ["#F8F8F8", "#80B0E8", "#182040"], "extra": ["INHALE", "BLOW"],
     "ice": "igloo"},
    {"name": "sumo", "width": 40, "pal": ["#F0A878", "#F0F0E0", "#282048"], "extra": ["SHIKO", "HMPH"]},
    {"name": "leo", "width": 32, "pal": ["#F8D060", "#C86018", "#301808"], "extra": ["INHALE", "ROAR"],
     "tiles": ["BANG"]},
    {"name": "mascot", "width": 32, "pal": ["#F8E8C8", "#D02828", "#201018"], "extra": ["CROUCH", "PUFF1", "PUFF2"],
     "fx": [("MARKER", "mascot")]},
    {"name": "prototype", "width": 32, "pal": ["#E8F0F8", "#F87818", "#182030"], "extra": ["RED"],
     "hats": ["LAMP_RING", "LAMP_X"], "fx": [("MARKER", "mascot")], "conveyor": "factory"},
    {"name": "duke", "width": 40, "pal": ["#F8E0C8", "#D06030", "#201018"], "extra": ["TELL1", "TELL2"]},
]
BOSS_TILES_MAX = 3           # "tiles": a boss's own 8x16 BG blocks (Leo's "!!"), at BG 246.. like the ice (6 ids)


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

    pose_map = [[pair(column(p, x)) for x in range(0, w, 8)] for p in poses]
    hand_map = [pose_map[0][-1]] + [pair(column(h, 0)) for h in hands]
    if len(pairs) > BOSS_PAIRS_MAX:
        fail(f"{b['name']}: {len(pairs)} different body columns, the fight has room for {BOSS_PAIRS_MAX}")
    hat_tiles = []
    for f in hat:
        hat_tiles += tile_bytes(f, 0, 0) + tile_bytes(f, 0, 8)
    png(poses, prev / f"boss_{b['name']}_x8.png", 8)
    png(hands + hat, prev / f"boss_{b['name']}_hand_hat_x8.png", 8, transparent=True)
    png([icon], prev / f"boss_{b['name']}_icon_x8.png", 8)
    a = {"name": b["name"], "width": w, "cols": w // 8, "pairs": [list(p) for p in pairs], "poses": names,
         "pose": pose_map, "hand": hand_map, "hat": hat_tiles, "icon": tile_bytes(icon, 0, 0),
         "pal": rgb15(["#000000"] + b["pal"]), "art": {n: p for n, p in zip(names, poses)}}
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
            f = ["." * 16] * 8 + frame(dict(blocks(fpath, named=True)), block, 16, 8, fpath)   # (the lower wall row)
            frames.append(f)
            fx += list(column(f, 0) + column(f, 8))
        if len(fx) // 16 > BOSS_FX_MAX:
            fail(f"{b['name']}: {len(fx) // 16} fx tiles, room for {BOSS_FX_MAX}")
        png(frames, prev / f"boss_{b['name']}_fx_x8.png", 8)
        a["fx"] = fx
    if "conveyor" in b:
        a["conv_src"], a["conv"] = conveyor_tiles(b["conveyor"], prev, b["name"], named, path)
    return a


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
         carr("boss_art_hand", a["hand"]) + "   // the hand column holding 0..3 empties",
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
    names = [b["name"] for b in BOSSES]
    if len(set(names)) != len(names):
        fail("a boss is listed twice")
    files = {p.stem for p in (ROOT / "assets/art/boss").glob("*.txt")} - {"meter"}
    if files != set(names):
        fail(f"assets/art/boss/ and BOSSES differ: {sorted(files ^ set(names))}")
    arts = [boss_art(b, prev) for b in BOSSES]
    h = ["// generated by tools/gen_boss.py from assets/art/boss/*.txt -- do not edit; #included by src/boss.c",
         f"#define BOSS_POSES_MAX {BOSS_POSES_MAX}   // " + ", ".join(POSES) + ", then each boss's extra poses",
         f"#define BOSS_PAIRS_MAX {BOSS_PAIRS_MAX}",
         f"#define BOSS_ICE_MAX {BOSS_ICE_MAX}",
         f"#define BOSS_FX_MAX {BOSS_FX_MAX}",
         f"#define BOSS_HATS_MAX {BOSS_HATS_MAX}",
         carr("boss_meter_tiles", meter_bytes) + "   // EMPTY, HALF, FULL"]
    (outdir / "boss_art.h").write_text("\n".join(h) + "\n")
    for a in arts:
        (outdir / f"boss_{a['name']}_art.h").write_text(header(a))
    (outdir / "boss.json").write_text(json.dumps({"meter": meter_bytes, "bosses": arts, "poses": POSES,
                                                  "pairs_max": BOSS_PAIRS_MAX, "poses_max": BOSS_POSES_MAX}))


if __name__ == "__main__":
    main()
