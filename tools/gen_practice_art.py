#!/usr/bin/env python3
"""Practice screen illustrations (BONUS > MINI GAMES, src/mg_list.c): assets/art/practice/<game>.png -> banked data + build/practice_art.h.

usage: gen_practice_art.py BUILD_DIR PREVIEW_DIR [--dirs DIR ...] [--max-tiles N]

Per game (the order of ml_game in src/mg_list.c, GAMES below) the first DIR that has <game>.png wins; a game with no PNG anywhere has no picture and
the screen shows the empty frame. The default DIRS is assets/art/practice (the real art); tests/data/practice_art holds the test-only placeholders and is
used only by a build that asks for it (make PRACTICE_ART_DIRS=tests/data/practice_art), never mixed into the real art.

Input: 80 x 64 px (10 x 8 tiles), indexed (mode P), colour indices 0-3 only (index 0 lightest ... 3 darkest by the art's own convention: the DMG shows the
index through BGP, the CGB shows the first four palette entries as its one palette). Cells are de-duplicated (no flips: the DMG has none).
Fails the build, naming the file, when: the size is not 80 x 64, the image is not indexed, a pixel uses an index over 3, or a picture needs more than
MAX_TILES (80, the ids ML_ART_T..255 of src/mg_list.c) unique tiles. More than 56 unique tiles is only a warning (the aim: the stream takes about
a frame per 5 tiles).

Output:
  build/practice_art_a.c, build/practice_art_b.c   `#pragma bank 255` data (autobank places each in a switchable bank); pictures are packed first-fit
                                                   into two files so no file passes 15 KB. Each picture is one array pa_<game>:
                                                   [0] n tiles, [1..8] the CGB palette (4 x RGB15, little endian), [9..88] the 10 x 8 map in slots 0..n-1
                                                   (row-major), [89..] n x 16 bytes of tiles
  build/practice_art.h                             for src/mg_list.c: PA_N, pa_ptr[] / pa_bank() per game (0 / 0 for a game without a picture)
  build/practice_art.json                          for the tests (per game: tiles, map, palette, file)
  PREVIEW_DIR/practice_<game>_x4.png               the picture rebuilt from the generated data (LOOK at these)
"""
import argparse
import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
GAMES = ["quickdraw", "shirtcannon", "logroll", "orderup", "marshmallows", "batterysort", "milkrun", "taikopour",
         "monkeybusiness", "asteroids", "shakeup", "perfectpour", "tipshower"]
W, H = 80, 64
TW, TH = W // 8, H // 8
MAX_TILES = 80          # ML_ART_T..255 in src/mg_list.c
AIM_TILES = 56
FILE_BUDGET = 15000     # bytes of picture data a file may take (a bank is 16 KB; the other files autobank puts beside it need room)


class ArtError(Exception):
    pass


def rgb555(c):
    return (c[0] >> 3) | ((c[1] >> 3) << 5) | ((c[2] >> 3) << 10)


def enc(cell):          # 8 rows of 8 colour indices -> 16 bytes (2bpp, the Game Boy's planes)
    out = []
    for row in cell:
        lo = hi = 0
        for x, v in enumerate(row):
            lo |= (v & 1) << (7 - x)
            hi |= (v >> 1) << (7 - x)
        out += [lo, hi]
    return bytes(out)


def convert(path, max_tiles):
    """One PNG -> {tiles: [16-byte...], map: [80 slots], pal: [4 RGB15]}; raises ArtError with the file named."""
    im = Image.open(path)
    if im.size != (W, H):
        raise ArtError(f"{path}: {im.size[0]} x {im.size[1]} px, it must be exactly {W} x {H} (10 x 8 tiles)")
    if im.mode != "P":
        raise ArtError(f"{path}: mode {im.mode}, it must be an indexed PNG (mode P) with colour indices 0-3")
    px = im.load()
    used = {px[x, y] for y in range(H) for x in range(W)}
    if max(used) > 3:
        raise ArtError(f"{path}: uses colour index {max(used)}; only the indices 0-3 (4 colours) are allowed")
    pal = im.getpalette() or []
    pal += [0] * (12 - len(pal))
    cols = [tuple(pal[i * 3:i * 3 + 3]) for i in range(4)]
    tiles, seen, cmap = [], {}, []
    for ty in range(TH):
        for tx in range(TW):
            cell = tuple(tuple(px[tx * 8 + x, ty * 8 + y] for x in range(8)) for y in range(8))
            if cell not in seen:
                seen[cell] = len(tiles)
                tiles.append(cell)
            cmap.append(seen[cell])
    if len(tiles) > max_tiles:
        raise ArtError(f"{path}: {len(tiles)} unique 8x8 tiles after de-duplication, at most {max_tiles} fit "
                       f"(BG ids 176-255); redraw it with more repeated cells (the aim is {AIM_TILES} or fewer)")
    return {"tiles": tiles, "map": cmap, "pal": [rgb555(c) for c in cols], "rgb": cols}


def blob(p):
    b = bytearray([len(p["tiles"])])
    for c in p["pal"]:
        b += bytes([c & 255, c >> 8])
    b += bytes(p["map"])
    for t in p["tiles"]:
        b += enc(t)
    return bytes(b)


def c_array(name, data):
    s = f"const uint8_t {name}[{len(data)}] = {{\n"
    for i in range(0, len(data), 16):
        s += "    " + ", ".join(f"0x{v:02X}" for v in data[i:i + 16]) + ",\n"
    return s + "};\n"


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("build")
    ap.add_argument("preview")
    ap.add_argument("--dirs", nargs="*", default=[str(ROOT / "assets" / "art" / "practice")])
    ap.add_argument("--max-tiles", type=int, default=MAX_TILES)
    a = ap.parse_args(argv)
    build, preview = Path(a.build), Path(a.preview)
    build.mkdir(parents=True, exist_ok=True)
    preview.mkdir(parents=True, exist_ok=True)
    pics, errors = {}, []
    for g in GAMES:
        for d in a.dirs:
            f = Path(d) / f"{g}.png"
            if f.is_file():
                try:
                    pics[g] = convert(f, a.max_tiles)
                    pics[g]["file"] = str(f)
                    if len(pics[g]["tiles"]) > AIM_TILES:
                        print(f"practice art: {g} has {len(pics[g]['tiles'])} unique tiles (aim {AIM_TILES}: about {-(-len(pics[g]['tiles']) // 5)} frames to stream)")
                except ArtError as e:
                    errors.append(str(e))
                break
    if errors:
        sys.exit("practice art: " + "\n".join(errors))
    # first-fit into two files
    files, used = {"a": [], "b": []}, {"a": 0, "b": 0}
    for g in GAMES:
        if g not in pics:
            continue
        n = len(blob(pics[g]))
        for k in "ab":
            if used[k] + n <= FILE_BUDGET:
                files[k].append(g)
                used[k] += n
                break
        else:
            sys.exit(f"practice art: the pictures do not fit two banks ({used['a']} + {used['b']} B, {g} needs {n}): shrink some of them")
    for k in "ab":
        s = ["// generated by tools/gen_practice_art.py -- do not edit", "#pragma bank 255", "#include <gb/gb.h>", "#include <stdint.h>", ""]
        for g in files[k]:
            s.append(f"BANKREF(pa_{g})")
            s.append(c_array(f"pa_{g}", blob(pics[g])))
        if not files[k]:
            s.append("const uint8_t pa_unused_" + k + " = 0;")   # (an empty file: nothing to place)
        (build / f"practice_art_{k}.c").write_text("\n".join(s) + "\n")
    h = ["// generated by tools/gen_practice_art.py -- do not edit", "#ifndef PRACTICE_ART_H", "#define PRACTICE_ART_H", "",
         f"#define PA_N {len(GAMES)}   // pictures (the 13 games of ml_game, in order; a game without a PNG has pa_ptr 0)", ""]
    for g in GAMES:
        if g in pics:
            h.append(f"extern const uint8_t pa_{g}[];")
            h.append(f"BANKREF_EXTERN(pa_{g})")
    h.append("")
    h.append("static const uint8_t *const pa_ptr[PA_N] = { " + ", ".join(f"pa_{g}" if g in pics else "0" for g in GAMES) + " };")
    h.append("static uint8_t pa_bank(uint8_t i) {")
    h.append("    switch (i) {")
    for i, g in enumerate(GAMES):
        if g in pics:
            h.append(f"    case {i}: return BANK(pa_{g});")
    h.append("    }")
    h.append("    return 0;")
    h.append("}")
    h.append("#endif")
    (build / "practice_art.h").write_text("\n".join(h) + "\n")
    (build / "practice_art.json").write_text(json.dumps({
        "games": GAMES,
        "pictures": {g: {"file": p["file"], "ntiles": len(p["tiles"]), "map": p["map"], "pal": p["pal"], "tiles_hex": b"".join(enc(t) for t in p["tiles"]).hex()}
                     for g, p in pics.items()}}, indent=1))
    for g, p in pics.items():
        im = Image.new("RGB", (W, H))
        for i, t in enumerate(p["map"]):
            cell = p["tiles"][t]
            for y in range(8):
                for x in range(8):
                    im.putpixel(((i % TW) * 8 + x, (i // TW) * 8 + y), p["rgb"][cell[y][x]])
        im.resize((W * 4, H * 4), Image.NEAREST).save(preview / f"practice_{g}_x4.png")
    print("practice art: " + (", ".join(f"{g} {len(p['tiles'])}" for g, p in pics.items()) or "no pictures (the empty frame)")
          + f"; data {used['a']} + {used['b']} B")


if __name__ == "__main__":
    main(sys.argv[1:])
