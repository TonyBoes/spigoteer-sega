#!/usr/bin/env python3
"""Marshmallow Drop art (src/mm.c, docs/minigames_bosses.md 4.5; the owner-approved hybrid with aurora window W1, 2026-10-12)
-> build/mm_art.h (src/mm.c's bank), build/mm.json (tests) and x8 previews out/preview/mm_*_x8.png.

  assets/art/marshmallow/scene.txt      BG: the whole 160x144 screen (window frame 0, belt phase 0), no letters: rows 1-17 cut into
                                        tiles; HUD-palette cells of rows 1-4 (the sign's panel) are the framework's glyph tiles
                                        (map value 255); row 0 col 9 is the HUD tally icon
  assets/art/marshmallow/scene_pal.txt  the CGB BG palette of each cell (18 rows x 20)
  assets/art/marshmallow/window.txt     the aurora window, 3 shimmer frames 48x32 (shown 0, 1, 2, 1); frame 0 equals the scene's
  assets/art/marshmallow/belt.txt       the conveyor tile, 2 phases (the map row 14 swaps between them)
  assets/art/marshmallow/cup.txt        OBJ: tin cup 16x16, 0-3 marshmallows, splash 1, 2
  assets/art/marshmallow/pail.txt       OBJ: the hoist-pail dropper 16x16, 2 swing frames
  assets/art/marshmallow/puff.txt       OBJ: the marshmallow 8x8, 2 spin frames (an 8x16 entry with a blank lower half)
  assets/art/marshmallow/pop.txt        OBJ: the perfect-cocoa pop 16x16, 2 frames
  assets/art/marshmallow/splat.txt      OBJ: a marshmallow splat on the belt (16x8 in the top of 16x16), 3 frames (D2 rework)
All BG tiles are deduplicated together (the palette is per map cell); OBJ entries are 8x16 (top, bottom tile), deduplicated.
Usage: gen_mm.py outdir previewdir
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_art import blocks, png, tile_bytes  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "assets/art/marshmallow"
HEADER = "; Art: approved design (owner 2026-10-12)"


def frames(name, n, w, h, header=HEADER):
    path = ART / f"{name}.txt"
    if not path.read_text().startswith(header):
        sys.exit(f"gen_mm: assets/art/marshmallow/{name}.txt: the first line must start with '{header}'")
    fr = [r for _, r in blocks(path)]
    if len(fr) != n or not all(len(f) == h and all(len(r) == w and set(r) <= set(".-+#") for r in f) for f in fr):
        sys.exit(f"gen_mm: assets/art/marshmallow/{name}.txt: needs {n} frames of {w}x{h} in . - + #")
    return fr


def carr(name, data, typ="uint8_t"):
    return f"static const {typ} {name}[{len(data)}] = {{ " + ", ".join(f"0x{b:02X}" for b in data) + " };"


def main():
    outdir, prev = Path(sys.argv[1]), Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True)
    prev.mkdir(parents=True, exist_ok=True)
    scene = frames("scene", 1, 160, 144)[0]
    win = frames("window", 3, 48, 32)
    belt = frames("belt", 2, 8, 8)
    cup = frames("cup", 6, 16, 16)
    pail = frames("pail", 2, 16, 16)
    puff = frames("puff", 2, 8, 8)
    pop = frames("pop", 2, 16, 16)
    splat = frames("splat", 3, 16, 16, "; Art: new for the D2 rework")   # (not yet owner-judged)
    pal = [l for l in (ART / "scene_pal.txt").read_text().splitlines() if l and not l.startswith(";")]
    if len(pal) != 18 or any(len(l) != 20 or set(l) - set("01234567") for l in pal):
        sys.exit("gen_mm: scene_pal.txt: needs 18 rows of 20 palette digits")

    tiles, idx = [], {}

    def tid(rows, x, y):
        t = tuple(tile_bytes(rows, x, y))
        if t not in idx:
            idx[t] = len(tiles)
            tiles.append(t)
        return idx[t]

    cmap, cpal = [], []
    for r in range(1, 18):
        for c in range(20):
            p = int(pal[r][c])
            glyph = p == 1                       # the sign's panel (and nothing else uses the HUD palette below row 0)
            if glyph and not 1 <= r <= 4:
                sys.exit(f"gen_mm: scene_pal.txt: HUD palette outside the sign at row {r} col {c}")
            cmap.append(255 if glyph else tid(scene, c * 8, r * 8))
            cpal.append(p)
    icon = tid(scene, 9 * 8, 0)
    if int(pal[0][9]) != 1:
        sys.exit("gen_mm: the tally icon must be on the HUD palette")
    # the window (cols 1-6, rows 1-4): frames 0, 1, 2; frame 0 must be the scene's
    wmap = []
    for f in win:
        wmap.append([tid(f, c * 8, r * 8) for r in range(4) for c in range(6)])
    for r in range(4):
        for c in range(6):
            if cmap[r * 20 + 1 + c] != wmap[0][r * 6 + c]:
                sys.exit("gen_mm: window.txt frame 0 differs from scene.txt")
    b0, b1 = tid(belt[0], 0, 0), tid(belt[1], 0, 0)
    if any(cmap[13 * 20 + c] != b0 for c in range(1, 19)):
        sys.exit("gen_mm: the scene's conveyor (row 14, columns 1-18) must be belt.txt phase 0")
    bg = [b for t in tiles for b in t]
    n_bg = len(tiles)

    ents = []

    def entry(rows, ex):
        lo = tile_bytes(rows, ex, 0)
        hi = tile_bytes(rows, ex, 8) if len(rows) >= 16 else [0] * 16
        e = tuple(lo + hi)
        if e not in ents:
            ents.append(e)
        return ents.index(e)

    cups = [[entry(f, 0), entry(f, 8)] for f in cup]
    pails = [[entry(f, 0), entry(f, 8)] for f in pail]
    puffs = [entry(f, 0) for f in puff]
    pops = [[entry(f, 0), entry(f, 8)] for f in pop]
    splats = [[entry(f, 0), entry(f, 8)] for f in splat]
    obj = [b for e in ents for b in e]
    lines = [
        "// generated by tools/gen_mm.py from assets/art/marshmallow/*.txt -- do not edit; #included by src/mm.c",
        f"#define MM_BG_TILES {n_bg}   // from MM_BG: every BG tile of the scene, the window's 3 shimmer frames and 2 belt phases",
        f"#define MMB_ICON {icon}      // the HUD tally icon",
        f"#define MMB_BELT0 {b0}", f"#define MMB_BELT1 {b1}",
        f"#define MM_OBJ_ENTRIES {len(ents)}   // 8x16 entries: mm_obj_tiles holds 2 tiles each; mm.c places them (otile)",
        f"#define MM_OBJ_TILES {2 * len(ents)}",
        carr("mm_map", cmap), carr("mm_pal", cpal),
        carr("mm_win", [t for w in wmap for t in w]),
        carr("mm_cup", [e for p in cups for e in p]), carr("mm_pail", [e for p in pails for e in p]),
        carr("mm_puff", puffs), carr("mm_pop", [e for p in pops for e in p]),
        carr("mm_splat", [e for p in splats for e in p]),
        carr("mm_bg_tiles", bg), carr("mm_obj_tiles", obj), ""]
    (outdir / "mm_art.h").write_text("\n".join(lines))
    (outdir / "mm.json").write_text(json.dumps({
        "bg": bg, "obj": obj, "n_bg": n_bg, "n_obj_entries": len(ents), "map": cmap, "pal": cpal, "win": wmap,
        "icon": icon, "belt": [b0, b1], "cup": cups, "pail": pails, "puff": puffs, "pop": pops, "splat": splats}))
    png([scene], prev / "mm_scene_x4.png", 4)
    png(win, prev / "mm_window_x8.png", 8)
    png(cup + pail + puff + pop + splat, prev / "mm_sprites_x8.png", 8, transparent=True)
    print(f"gen_mm: {n_bg} BG tiles, {len(ents)} OBJ entries")


if __name__ == "__main__":
    main()
