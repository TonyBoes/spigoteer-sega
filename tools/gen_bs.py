#!/usr/bin/env python3
"""Battery Sort art (src/bs.c, docs/minigames_bosses.md 4.6; approved by the owner 2026-10-12) -> build/bs_art.h
(src/bs.c's bank), build/bs.json (tests) and x8 previews out/preview/bs_*_x8.png.

  assets/art/battery/belt.txt        BG: the belt, 4 frames 8x8
  assets/art/battery/diverter.txt    BG: flap, screen idle / left / right / down, base: 6 frames 16x8 (2 tiles each)
  assets/art/battery/bin.txt         BG: the bin, 32x40 (CHARGE, RECYCLE and the SCRAP chute; the sign goes at its
                                     columns 1-2, rows 1-2): its unique tiles only, and the 4x5 map of them
  assets/art/battery/chute_lid.txt   BG: the chute's lid (closed), the bin's top row 32x8: unique tiles + a 4-tile map
  assets/art/battery/signs.txt       BG: bolt, recycle, warning: 3 frames 16x16 (TL, TR, BL, BR)
  assets/art/battery/hud_strike.txt  BG: the HUD strike lamps, empty and struck, 8x8
  assets/art/battery/cells.txt       the charged / dead cells: the factory drink's full and empty frames (option A,
                                     approved: no tiles of their own; checked equal to the drink, OBJ 56-59 in play)
  assets/art/battery/broken.txt      OBJ: the broken battery, 8x16
  assets/art/battery/spark.txt       OBJ: the spark, 2 frames 8x16 (art in the top 8 rows)
  assets/art/battery/xmark.txt       OBJ: the WRONG cross, 2 halves 8x16; only the left is stored (the right is its
                                     X-flip, checked)

Usage: gen_bs.py outdir previewdir
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_art import blocks, png, tile_bytes  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "assets/art/battery"
HEADER = "; Art: approved design (owner 2026-10-12)"


def frames(name, n, w, h):
    path = ART / f"{name}.txt"
    if not path.read_text().startswith(HEADER):
        sys.exit(f"gen_bs: assets/art/battery/{name}.txt: the first line must be '{HEADER}'")
    fr = [r for _, r in blocks(path)]
    if len(fr) != n or not all(len(f) == h and all(len(r) == w and set(r) <= set(".-+#") for r in f) for f in fr):
        sys.exit(f"gen_bs: assets/art/battery/{name}.txt: needs {n} frames of {w}x{h} in . - + #")
    return fr


def tiles_rowmajor(f):
    out = []
    for ty in range(0, len(f), 8):
        for tx in range(0, len(f[0]), 8):
            out.append(tuple(tile_bytes(f, tx, ty)))
    return out


def obj_pair(f):
    """An 8x16 frame -> its OBJ entry's two tiles (top, bottom)."""
    return list(tile_bytes(f, 0, 0)) + list(tile_bytes(f, 0, 8))


def carr(name, data):
    return f"static const uint8_t {name}[{len(data)}] = {{ " + ", ".join(f"0x{b:02X}" for b in data) + " };"


def main():
    outdir, prev = Path(sys.argv[1]), Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True); prev.mkdir(parents=True, exist_ok=True)
    belt = frames("belt", 4, 8, 8)
    div = frames("diverter", 6, 16, 8)
    binf = frames("bin", 1, 32, 40)[0]
    lid = frames("chute_lid", 1, 32, 8)[0]
    signs = frames("signs", 3, 16, 16)
    strike = frames("hud_strike", 2, 8, 8)
    cells = frames("cells", 2, 8, 16)
    broken = frames("broken", 1, 8, 16)
    spark = frames("spark", 2, 8, 16)
    xmark = frames("xmark", 2, 8, 16)

    drink = [r for _, r in blocks(ROOT / "assets/approved/venues/factory_drink.txt")]
    if cells != drink[:2]:
        sys.exit("gen_bs: cells.txt must be the factory drink's full and empty frames (option A: OBJ 56-59 in play)")
    if [r[::-1] for r in xmark[0]] != xmark[1]:
        sys.exit("gen_bs: xmark.txt: the right half must be the left half mirrored (drawn with X flip)")
    if any(r != "." * 8 for f in spark for r in f[8:]):
        sys.exit("gen_bs: spark.txt: the art goes in the top 8 rows (8x16 entries: the bottom tile is blank)")

    bg = []                                      # BG tiles in order; the bin's and the lid's deduplicated
    for f in belt:
        bg += tile_bytes(f, 0, 0)
    for f in div:
        bg += tile_bytes(f, 0, 0) + tile_bytes(f, 8, 0)
    # the bin: its 4x5 cells, the sign's 2x2 (columns 1-2, rows 1-2) left out
    uniq, bin_map = [], []
    for k, t in enumerate(tiles_rowmajor(binf)):
        r, c = divmod(k, 4)
        if 1 <= r <= 2 and 1 <= c <= 2:
            bin_map.append(255)
            continue
        if t not in uniq:
            uniq.append(t)
        bin_map.append(uniq.index(t))
    n_bin = len(uniq)
    lid_map = []
    for t in tiles_rowmajor(lid):
        if t not in uniq:
            uniq.append(t)
        lid_map.append(uniq.index(t))
    if lid_map[1] != lid_map[2]:
        sys.exit("gen_bs: chute_lid.txt: the middle two tiles must repeat")
    n_lid = len(uniq) - n_bin
    bg_bin = len(bg) // 16
    for t in uniq:
        bg += list(t)
    bg_signs = len(bg) // 16
    for f in signs:
        for t in tiles_rowmajor(f):
            bg += list(t)
    bg_strike = len(bg) // 16
    for f in strike:
        bg += tile_bytes(f, 0, 0)
    n_bg = len(bg) // 16

    obj = obj_pair(broken[0]) + obj_pair(spark[0]) + obj_pair(spark[1]) + obj_pair(xmark[0])

    (outdir / "bs_art.h").write_text("\n".join([
        "// generated by tools/gen_bs.py from assets/art/battery/*.txt -- do not edit; #included by src/bs.c (its bank)",
        f"#define BS_BG_TILES {n_bg}   // from BS_BG: belt, diverter, bin + lid (deduplicated), signs, strike lamps",
        "#define BSB_BELT 0       // 4 frames",
        "#define BSB_FLAP 4       // the diverter's flap: 2 tiles (left, right)",
        "#define BSB_SCREEN 6     // its screen: 4 states x 2 (IDLE, LEFT, RIGHT, DOWN)",
        "#define BSB_BASE 14      // its base: 2 tiles",
        f"#define BSB_BIN {bg_bin}      // the bin's {n_bin} unique tiles, then the lid's {n_lid} (bs_bin_map / bs_lid_map)",
        f"#define BSB_SIGN {bg_signs}     // 3 signs x 4 (TL, TR, BL, BR): BOLT, RECYCLE, WARNING",
        f"#define BSB_STRIKE {bg_strike}   // the HUD lamps: EMPTY, STRUCK",
        "#define BS_OBJ_TILES 8   // OBJ 8x16 pairs: BROKEN, SPARK small, SPARK big, the cross's left half",
        "#define BSO_BROKEN 0", "#define BSO_SPARK 2", "#define BSO_CROSS 6",
        "// the bin's 4x5 cells (row-major) as offsets from BSB_BIN; 255: the sign's 2x2 at columns 1-2, rows 1-2",
        carr("bs_bin_map", bin_map),
        carr("bs_bg_tiles", bg), carr("bs_obj_tiles", obj), ""]))
    (outdir / "bs.json").write_text(json.dumps({"bg": bg, "obj": obj, "bin_map": bin_map, "lid_map": lid_map,
                                                "n_bin": n_bin, "n_lid": n_lid}))
    png(belt, prev / "bs_belt_x8.png", 8)
    png(div, prev / "bs_diverter_x8.png", 8)
    png([binf], prev / "bs_bin_x8.png", 8)
    png([lid], prev / "bs_chute_lid_x8.png", 8)
    png(signs, prev / "bs_signs_x8.png", 8)
    png(strike, prev / "bs_hud_strike_x8.png", 8)
    png(cells + broken, prev / "bs_cells_x8.png", 8, transparent=True)
    png(spark, prev / "bs_spark_x8.png", 8, transparent=True)
    png(xmark, prev / "bs_xmark_x8.png", 8, transparent=True)


if __name__ == "__main__":
    main()
