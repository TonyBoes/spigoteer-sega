#!/usr/bin/env python3
"""Story map (owner-approved v14 art, 2026-10-18): assets/story_map/*.png -> build/smap_art.h (included by src/smap.c, so the data and
the code share a bank), build/smap.json (tests), out/preview/smap_*.png (the screen rebuilt from the generated data: LOOK at these).

assets/story_map/map_bg_only_indexed.png   the whole 160x144 background, palette index = BG palette * 4 + colour (the artist's tooling's output)
assets/story_map/map_bg_only_dmg_indexed.png   the same picture as DMG shades (colour index only: checked against the first)
assets/story_map/obj_*.png                 Sal 16x16, the UFO 24x16, the open / locked stop dots, the "!" and the gold arrow (right, 8x8):
                                           index 0 transparent, 1-3 the sprite's colours

BG: every 8x8 cell is a tile (colour indices 0-3, no flips: DMG has none) in one of eight CGB palettes; identical tiles are stored once.
The tiles sit in the BG ids the font leaves free (the generic tiles and the story font take 36..92: build/art.h, build/story.h), 0..35 then
93 up; the last DIM_N ids of the screen are the dim letters src/smap.c makes for a greyed menu line.
OBJ: 8x16 mode (the game's): every sprite column of 8 px is a pair of tiles (top, bottom; an 8x8 sprite has a blank bottom), pair k at
OBJ ids 2k, 2k + 1. The gold arrow comes in the three orientations a column pair can show (right, up, down; left is the right one flipped).
OBJ colours: DMG OBP0 0xD0 (colour 1 shade 0, 2 shade 1, 3 shade 3: the pictures' DMG mapping), CGB OBJ palettes 1-6.
"""
import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "story_map"
FONT_END = 93            # the first BG id after the generic tiles (36..76) and the story font (77..92)
DIM_BASE = 240           # the greyed letters' ids (DIM_N of them)
DIM_N = 9
TW, TH = 20, 18


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
    build, preview = Path(build), Path(preview)
    build.mkdir(parents=True, exist_ok=True)
    preview.mkdir(parents=True, exist_ok=True)
    bg, bgpal = load_p("map_bg_only_indexed.png")
    dm, dmpal = load_p("map_bg_only_dmg_indexed.png")
    assert bg.size == (160, 144) and dm.size == (160, 144)
    # --- the background -----------------------------------------------------------------------------------------
    pal_cols = [[bgpal[p * 4 + i] for i in range(4)] for p in range(8)]
    tiles, tile_id, cell_tile, cell_pal = [], {}, [], []
    for ty in range(TH):
        for tx in range(TW):
            t, pals = [], set()
            for y in range(8):
                row = []
                for x in range(8):
                    v = bg.getpixel((tx * 8 + x, ty * 8 + y))
                    pals.add(v // 4)
                    row.append(v % 4)
                t.append(tuple(row))
            assert len(pals) == 1, f"cell {tx},{ty} mixes palettes {pals}"
            # the DMG picture must be the same colour indices
            for y in range(8):
                for x in range(8):
                    assert dm.getpixel((tx * 8 + x, ty * 8 + y)) == t[y][x], f"DMG picture differs at {tx * 8 + x},{ty * 8 + y}"
            t = tuple(t)
            if t not in tile_id:
                tile_id[t] = len(tiles)
                tiles.append(t)
            cell_tile.append(tile_id[t])
            cell_pal.append(pals.pop())
    n = len(tiles)
    pool = list(range(0, 36)) + list(range(FONT_END, DIM_BASE))
    assert n <= len(pool), f"{n} tiles do not fit the {len(pool)} free BG ids"
    ids = pool[:n]
    # contiguous id ranges (each one set_bkg_data call; 128 is where the 0x8800 block starts)
    ranges, k = [], 0
    while k < n:
        j = k
        while j + 1 < n and ids[j + 1] == ids[j] + 1 and ids[j + 1] != 128:
            j += 1
        ranges.append((ids[k], k, j - k + 1))
        k = j + 1
    data = []
    for t in tiles:
        data += enc(t)
    cmap = [ids[t] for t in cell_tile]
    # --- the sprites ----------------------------------------------------------------------------------------------
    def spr(name):
        im, pal = load_p(name)
        assert pal[0][:3] == (255, 0, 255), name
        return [[im.getpixel((x, y)) for x in range(im.width)] for y in range(im.height)], [pal[1], pal[2], pal[3]]

    sal, sal_p = spr("obj_sal.png")
    ufo, ufo_p = spr("obj_ufo.png")
    dop, dop_p = spr("obj_dot_open.png")
    dlk, dlk_p = spr("obj_dot_locked.png")
    bang, bang_p = spr("obj_bang.png")
    arr, arr_p = spr("obj_arrow.png")
    assert (len(sal), len(sal[0])) == (16, 16) and (len(ufo), len(ufo[0])) == (16, 24)
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
    cols("sal", sal); cols("ufo", ufo); cols("dot_open", dop); cols("dot_locked", dlk); cols("bang", bang)
    cols("arrow_r", arr); cols("arrow_u", arr_u); cols("arrow_d", arr_d)
    obj = []
    pid = {}
    for i, (nm, top, bot) in enumerate(pairs):
        pid[nm] = i * 2
        obj += enc(top) + enc(bot)
    # OBJ palettes 1..6 (0 is the bartender's: boot, never touched here); the same order on the sprite sheet
    obj_pals = [("sal", sal_p), ("ufo", ufo_p), ("dot_open", dop_p), ("dot_locked", dlk_p), ("arrow", arr_p), ("bang", bang_p)]
    # --- the header -----------------------------------------------------------------------------------------------
    def carr(name, vals, per=16, typ="uint8_t", hexw=2):
        s = f"static const {typ} {name}[{len(vals)}] = {{\n"
        for i in range(0, len(vals), per):
            s += "    " + ", ".join(f"0x{v:0{hexw}X}" for v in vals[i:i + per]) + ",\n"
        return s + "};\n"

    h = ["// generated by tools/gen_smap.py -- do not edit", "#ifndef SMAP_ART_H", "#define SMAP_ART_H", ""]
    h.append(f"#define SMAP_NTILES {n}   // unique BG tiles of the picture (no flips: DMG has none)")
    h.append(f"#define SMAP_NRANGES {len(ranges)}   // smap_range[]: first BG id, first tile, count (each one a set_bkg_data call)")
    h.append(f"#define SMAP_DIM_BASE {DIM_BASE}   // BG ids of the greyed letters (smap.c), SMAP_DIM_N of them")
    h.append(f"#define SMAP_DIM_N {DIM_N}")
    h.append(f"#define SMAP_LAST_ID {max(ids)}")
    h.append(f"#define SMAP_OBJ_TILES {len(obj) // 16}")
    for nm, v in pid.items():
        h.append(f"#define SOB_{nm.upper()} {v}")
    h.append("")
    h.append("static const uint8_t smap_range[SMAP_NRANGES][3] = {" + ", ".join("{%d, %d, %d}" % r for r in ranges) + "};")
    h.append(carr("smap_tiles", data))
    h.append(carr("smap_map", cmap, 20))
    h.append(carr("smap_attr", cell_pal, 20))
    h.append(carr("smap_obj_tiles", obj))
    h.append("static const uint16_t smap_bg_pal[8][4] = {")
    for p in pal_cols:
        h.append("    { " + ", ".join(f"0x{rgb555(c):04X}" for c in p) + " },")
    h.append("};")
    h.append("static const uint16_t smap_obj_pal[6][4] = {   // OBJ palettes 1..6: sal, ufo, open dot, locked dot, arrow, bang (colour 0 unused)")
    for _, p in obj_pals:
        h.append("    { 0, " + ", ".join(f"0x{rgb555(c):04X}" for c in p) + " },")
    h.append("};")
    h.append("#endif")
    (build / "smap_art.h").write_text("\n".join(h) + "\n")
    # --- tests / previews ------------------------------------------------------------------------------------------
    (build / "smap.json").write_text(json.dumps({
        "ntiles": n, "ids": ids, "ranges": ranges, "map": cmap, "attr": cell_pal, "tiles_hex": bytes(data).hex(),
        "bg_pal": [[rgb555(c) for c in p] for p in pal_cols], "obj_pal": [[0] + [rgb555(c) for c in p] for _, p in obj_pals],
        "obj_pairs": pid, "obj_hex": bytes(obj).hex(), "tile_bytes": len(data), "obj_bytes": len(obj)}, indent=1))
    id_to_tile = {ids[i]: tiles[i] for i in range(n)}
    for model in ("cgb", "dmg"):
        im = Image.new("RGB", (160, 144))
        for ty in range(TH):
            for tx in range(TW):
                t = id_to_tile[cmap[ty * TW + tx]]
                p = cell_pal[ty * TW + tx]
                for y in range(8):
                    for x in range(8):
                        v = t[y][x]
                        im.putpixel((tx * 8 + x, ty * 8 + y), pal_cols[p][v] if model == "cgb" else tuple([[248, 168, 88, 24][v]] * 3))
        im.resize((640, 576), Image.NEAREST).save(preview / f"smap_{model}_x4.png")
    print(f"smap: {n} BG tiles in ids {ranges}, {len(obj) // 16} OBJ tiles, bytes: tiles {len(data)}, map {len(cmap)}, attr {len(cell_pal)}, obj {len(obj)}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "build", sys.argv[2] if len(sys.argv) > 2 else "out/preview")
