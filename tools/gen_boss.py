#!/usr/bin/env python3
"""Boss art -> build/boss_art.h (src/boss.c: the shared meter, the pose numbering), build/boss_<name>_art.h (each boss's
own art, #included by its own src/boss_<name>.c and nowhere else, so it lands in that file's bank), build/boss.json
(tests) and x8 previews in out/preview/.

  assets/art/boss/<boss>.txt   per boss (BOSSES below): the body poses (WALK, STOMP, GULP, WINCE, HAPPY: W x 16, BG,
                               on his bar's two wall rows), then the boss's own extra poses in his `extra` list (the
                               tells: Yeti INHALE / BLOW, the Critic's TASTE; the engine's pose numbers 5, 6, ... in
                               that order), the hand column with 1-3 held empties (HAND1..3, 8x16), the topper
                               (HAT_STILL, HAT_BOB: 8x16 OBJ) and the HUD face (ICON, 8x8). Other blocks in the file
                               are not read.
  assets/art/boss/meter.txt    the HUD meter's 3 tiles (EMPTY, HALF, FULL; 2 pips a tile), shared by every boss

The body is stored as column pairs (a column's top tile, then its bottom tile, at consecutive ids: render.c's put_col
stamps a column as t, t + 1), identical columns shared. A fight borrows variant C's BG ids and the back views for them
(src/boss.h: 162-203 and 216-233, BOSS_PAIRS_MAX 30 pairs); the build fails on more. The palette is colour 0 = the
venue's wall (set at the load), then the art's colours 1-3 (CGB BG palette 4; the topper OBJ palette 7 takes the same
1-3). Replacing a file and running make is the swap.

A boss's own header (build/boss_<name>_art.h) uses the same names in every boss (boss_art_body, boss_art_pose, ...):
src/boss_load.h's loaders read them. A boss with "ice" also gets icy copies of that venue's counter tiles
(boss_ice_src: the venue's counter tile ids, boss_ice_tiles: their icy copies, a light streak pattern generated here:
a PLACEHOLDER until the owner approves it).

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
BOSS_ICE_MAX = 2             # src/boss.h: icy counter tiles at BG 246.. (free in the story)
# per boss (the order of the hook table's ids does not matter): its art file, the C file it belongs to
# (src/boss_<name>.c), its body width (px), colours 1-3 (CGB), its extra poses (tells), and "ice": a venue whose
# counter tiles get icy copies.
BOSSES = [
    {"name": "big_tex", "width": 40, "pal": ["#F0B888", "#C83020", "#583018"], "extra": []},
    {"name": "sasquatch", "width": 32, "pal": ["#E8B878", "#5C2C14", "#140804"], "extra": []},
    {"name": "critic", "width": 32, "pal": ["#F8D0A8", "#A03070", "#201018"], "extra": ["TASTE"]},
]


def fail(msg):
    sys.exit(f"gen_boss: {msg}")


def frame(named, name, w, h, path):
    if name not in named:
        fail(f"{path.relative_to(ROOT)}: no @{name}")
    f = named[name]
    if len(f) != h or not all(len(r) == w and set(r) <= set(".-+#") for r in f):
        fail(f"{path.relative_to(ROOT)}: @{name} must be {w}x{h} in . - + #")
    return f


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


def icy(rows, k):
    """The icy copy of a counter tile (PLACEHOLDER): white (colour 0) streaks on the light counter top (colour 1) and
    glints on its front, so it reads on DMG by pattern, not only colour; k: the tile's column phase."""
    out = []
    for y, r in enumerate(rows):
        s = list(r)
        for x, c in enumerate(s):
            p = (x + 8 * k + 2 * y) % 8
            if c == "-" and ((y < 2 and p in (0, 1, 4)) or (y >= 2 and p == 0)):
                s[x] = "."
        out.append("".join(s))
    return out


def ice_tiles(theme, prev, name):
    """The venue's counter tile ids (columns 0-17 of its bar map's counter row) and their icy copies."""
    v = json.loads((ROOT / "build" / "venues.json").read_text())["venues"][theme]
    src = sorted(set(v["bar_map"][40:58]))
    if len(src) > BOSS_ICE_MAX:
        fail(f"{name}: {theme}'s counter has {len(src)} different tiles, room for {BOSS_ICE_MAX} icy ones")
    out, frames = [], []
    for k, t in enumerate(src):
        o = (t - v["bar_base"]) * 16
        f = icy(rows_of(v["bar_tiles"][o:o + 16]), k)
        frames.append(f)
        out += tile_bytes(f, 0, 0)
    png(frames, prev / f"boss_{name}_ice_x8.png", 8)
    return src, out


def boss_art(b, prev):
    path = ROOT / "assets/art/boss" / f"{b['name']}.txt"
    named = dict(blocks(path, named=True))
    w = b["width"]
    names = POSES + b["extra"]
    if len(names) > BOSS_POSES_MAX:
        fail(f"{b['name']}: {len(names)} poses, the engine has room for {BOSS_POSES_MAX}")
    poses = [frame(named, n, w, 16, path) for n in names]
    hands = [frame(named, f"HAND{k}", 8, 16, path) for k in (1, 2, 3)]
    hat = [frame(named, n, 8, 16, path) for n in ("HAT_STILL", "HAT_BOB")]
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
        a["ice_src"], a["ice"] = ice_tiles(b["ice"], prev, b["name"])
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
         carr("boss_art_hat", a["hat"]) + "   // STILL top, bottom, BOB top, bottom",
         carr("boss_art_icon", a["icon"]),
         carr("boss_art_pal", a["pal"], "uint16_t") + "   // colour 0: the venue's wall, set at the load"]
    if "ice" in a:
        h += [f"#define BOSS_ART_ICE {len(a['ice_src'])}",
              carr("boss_ice_src", a["ice_src"]) + "   // the venue's counter tile ids",
              carr("boss_ice_tiles", a["ice"]) + "   // their icy copies (PLACEHOLDER)"]
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
         carr("boss_meter_tiles", meter_bytes) + "   // EMPTY, HALF, FULL"]
    (outdir / "boss_art.h").write_text("\n".join(h) + "\n")
    for a in arts:
        (outdir / f"boss_{a['name']}_art.h").write_text(header(a))
    (outdir / "boss.json").write_text(json.dumps({"meter": meter_bytes, "bosses": arts, "poses": POSES,
                                                  "pairs_max": BOSS_PAIRS_MAX, "poses_max": BOSS_POSES_MAX}))


if __name__ == "__main__":
    main()
