#!/usr/bin/env python3
"""Story map sprites and constants (owner-approved v14 sprites, 2026-10-18; the scrolling world, 2026-11-04, is tools/gen_smap_world.py):
assets/story_map/obj_*.png -> build/smap_art.h (included by src/smap.c), build/smap.json (tests).

assets/story_map/obj_*.png   the UFO 24x16, the open / locked stop dots, the "!" and the gold arrow (right, 8x8): index 0 transparent, 1-3 the
                             sprite's colours. Sal has no tiles of his own on the map: he is drawn with the bartender's boot-time OBJ tiles
                             (OBJ palette 0), the game's own front frames.
OBJ: 8x16 mode (the game's): every sprite column of 8 px is a pair of tiles (top, bottom; an 8x8 sprite has a blank bottom), pair k at
OBJ ids OB + 2k, OB + 2k + 1 (OB = 56 in src/smap.c). The gold arrow comes in the three orientations a column pair can show (right, up, down;
left is the right one flipped).
OBJ colours: DMG OBP0 0xD0 (colour 1 shade 0, 2 shade 1, 3 shade 3), CGB OBJ palettes 2-4, 6, 7 (ufo, open dot, locked dot, arrow, "!").
BG: the world's tiles are tools/gen_smap_world.py's; the greyed menu letters sit at BG ids DIM_BASE.. (src/smap.c makes them from the font).
"""
import json
import os
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "story_map"
DIM_BASE = 233           # the greyed letters' ids (DIM_N of them): just above the picture's pool (ids 0-35, 93-232), below the transition drink's 248-251 (src/trans.c)
DIM_N = 9


def rgb555(c):
    return (c[0] >> 3) | ((c[1] >> 3) << 5) | ((c[2] >> 3) << 10)


def load_p(name):
    im = Image.open(SRC / name)
    assert im.mode == "P", name
    pal = im.getpalette()
    return im, [tuple(pal[i * 3:i * 3 + 3]) for i in range(len(pal) // 3)]


def enc(tile):          # 8 rows of 8 colour indices -> 16 bytes
    out = []
    for row in tile:
        lo = hi = 0
        for x, v in enumerate(row):
            lo |= (v & 1) << (7 - x)
            hi |= (v >> 1) << (7 - x)
        out += [lo, hi]
    return out


def main(build, preview):
    build = Path(build)
    build.mkdir(parents=True, exist_ok=True)

    def spr(name):
        im, pal = load_p(name)
        assert pal[0][:3] == (255, 0, 255), name
        return [[im.getpixel((x, y)) for x in range(im.width)] for y in range(im.height)], [pal[1], pal[2], pal[3]]

    ufo, ufo_p = spr("obj_ufo.png")
    dop, dop_p = spr("obj_dot_open.png")
    dlk, dlk_p = spr("obj_dot_locked.png")
    bang, bang_p = spr("obj_bang.png")
    arr, arr_p = spr("obj_arrow.png")
    assert (len(ufo), len(ufo[0])) == (16, 24)
    for a in (dop, dlk, bang, arr):
        assert (len(a), len(a[0])) == (8, 8)
    # the arrow's other directions: its transpose points down; flipped, up (the right arrow, drawn as the artist drew it, flips for left)
    arr_d = [[arr[x][y] for x in range(8)] for y in range(8)]
    arr_u = arr_d[::-1]
    pairs = []          # (name, top rows, bottom rows)

    def cols(name, im):
        for c in range(len(im[0]) // 8):
            top = [r[c * 8:c * 8 + 8] for r in im[:8]]
            bot = [r[c * 8:c * 8 + 8] for r in im[8:16]] if len(im) > 8 else [[0] * 8 for _ in range(8)]
            pairs.append((f"{name}{c}", top, bot))
    cols("ufo", ufo); cols("dot_open", dop); cols("dot_locked", dlk); cols("bang", bang)
    cols("arrow_r", arr); cols("arrow_u", arr_u); cols("arrow_d", arr_d)
    # the clouds (assets/story_map/clouds.txt, typed by hand: A 16x16, B and C 24x16; '.' clear, 1-3 the colours): 8-px columns as the sprites above, ids after the arrows
    small = (SRC / "clouds_small.txt").read_text() if os.environ.get("CLOUDS", "") in ("C", "D") else ""   # (the denser test builds add one shape: Q)
    for line in ((SRC / "clouds.txt").read_text() + "\n" + small).splitlines():
        if line.startswith("@"):
            cname, crows = line[1:].strip(), []
        elif line and not line.startswith(";"):
            crows.append([0 if ch == "." else int(ch) for ch in line.strip()])
            if len(crows) == 16:
                assert len(crows[0]) in (8, 16, 24) and all(len(r) == len(crows[0]) for r in crows), cname
                cols("cloud" + cname, crows)
    obj = []
    pid = {}
    for i, (nm, top, bot) in enumerate(pairs):
        pid[nm] = i * 2
        obj += enc(top) + enc(bot)
    # OBJ palettes 2, 3, 4, 6, 7 (0 is the bartender's, Sal's, boot-time and never touched here; 1 and 5 are the cards' / the coin's)
    obj_pals = [("ufo", ufo_p), ("dot_open", dop_p), ("dot_locked", dlk_p), ("arrow", arr_p), ("bang", bang_p)]

    def carr(name, vals, per=16, typ="uint8_t"):
        s = f"static const {typ} {name}[{len(vals)}] = {{\n"
        for i in range(0, len(vals), per):
            s += "    " + ", ".join(f"0x{v:02X}" for v in vals[i:i + per]) + ",\n"
        return s + "};\n"

    assert len(obj) // 16 <= 42, "the map's OBJ tiles (OB = 56) must end before id 98, where the beam's art starts (cameo.c CAM_SPACE_BASE)"
    h = ["// generated by tools/gen_smap.py -- do not edit", "#ifndef SMAP_ART_H", "#define SMAP_ART_H", ""]
    h.append(f"#define SMAP_DIM_BASE {DIM_BASE}   // BG ids of the greyed letters (smap.c), SMAP_DIM_N of them")
    h.append(f"#define SMAP_DIM_N {DIM_N}")
    h.append(f"#define SMAP_OBJ_TILES {len(obj) // 16}")
    h.append(f"#define SMAP_CLOUD_TILES {2 * sum(1 for n in pid if n.startswith('cloud'))}   // the clouds' tiles are the last ones")
    for nm, v in pid.items():
        h.append(f"#define SOB_{nm.upper()} {v}")
    h.append("")
    h.append(carr("smap_obj_tiles", obj))
    h.append("static const uint16_t smap_obj_pal[5][4] = {   // OBJ palettes 2, 3, 4, 6, 7: ufo, open dot, locked dot, arrow, \"!\" (colour 0 unused)")
    for _, p in obj_pals:
        h.append("    { 0, " + ", ".join(f"0x{rgb555(c):04X}" for c in p) + " },")
    h.append("};")
    h.append(f"static const uint16_t smap_cloud_pal[4] = {{ 0, 0x{rgb555((248, 248, 248)):04X}, 0x{rgb555((176, 200, 240)):04X}, 0x{rgb555((112, 144, 200)):04X} }};   // OBJ palette 1 (Color): the clouds (DMG: OBP1 0x90)")
    variant = os.environ.get("CLOUDS", "")
    if variant in ("C", "D"):       # the denser test builds' cloud table (src/smap_cloud.c, assets/story_map/cloud_layout.txt, tools/dev/cloud_layout.py): sorted by row, row starts, x / 4, shape | flip << 7
        cur, rows = None, []
        for line in (SRC / "cloud_layout.txt").read_text().splitlines():
            if line.startswith("@"):
                cur = line[1:].strip()
            elif line and not line.startswith("#") and cur == variant:
                r, pos, sh, fl = line.split()
                rows.append((int(r), int(pos), "ABCQ".index(sh), int(fl)))
        rows.sort(key=lambda t: (t[0], t[1]))
        assert rows and all(p % 4 == 0 and p < 512 for _, p, _, _ in rows)
        W4 = [4, 6, 6, 4]                      # a shape's width in 4 px units
        recs, start = [], []
        assert max(t[0] for t in rows) < 35           # (the world: 512 x 560 px, 35 rows of 16 px: SMAPW_CH 70 cells)
        for r in range(36):
            start.append(len(recs))
            for t in rows:
                if t[0] == r:
                    recs += [t[1] // 4, (t[3] << 7) | (t[2] << 4) | W4[t[2]]]
        assert len(recs) < 256
        h.append("#ifdef SMAP_CLOUD_TABLE")
        h.append(f"#define SCL_N {len(rows)}")
        h.append("#define SCL_ROWS 35")
        h.append(carr("scl_rowstart", start, 36).replace("static ", ""))      # (byte offsets into scl_rec; the asm reads them by name)
        h.append(carr("scl_rec", recs).replace("static ", ""))               # (per cloud: x / 4, flip << 7 | shape << 4 | width in 4 px units)
        h.append("const uint8_t scl_tile[4] = { " + ", ".join(f"OB + SOB_CLOUD{c}0" for c in "ABCQ") + " };")
        h.append("#endif")
    h.append("#endif")
    (build / "smap_art.h").write_text("\n".join(h) + "\n")
    (build / "smap.json").write_text(json.dumps({
        "dim_base": DIM_BASE, "dim_n": DIM_N, "obj_pal": [[0] + [rgb555(c) for c in p] for _, p in obj_pals],
        "obj_pairs": pid, "obj_hex": bytes(obj).hex(), "obj_bytes": len(obj)}, indent=1))
    print(f"smap: {len(obj) // 16} OBJ tiles ({len(obj)} bytes)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "build", sys.argv[2] if len(sys.argv) > 2 else "out/preview")
