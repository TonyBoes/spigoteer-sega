"""`retrosprite` — pixel art as text, indexed PNGs, NES CHR, and hardware checks.

ASCII art (assets/**/*.txt), one character per pixel = palette index:
    .  0 (transparent for sprites)   -  1   +  2   #  3        (the 4-shade set)
    0-9 a-f  indexes 0-15 directly                             (16 colours: SMS/GG)
';' or '//' starts a comment line; a blank line ends a frame; frames go left to
right in the PNG (--vertical stacks them).

    retrosprite txt2png assets/sprites/player.txt build/player.png --preview out/preview/player_x8.png
    retrosprite txt2png art.txt art.png --palette "#000,#f00,#0f0,#00f,#fff"   # up to 16 colours
    retrosprite png2txt build/player.png --frame-width 8
    retrosprite check build/player.png --system nes --sprite
    retrosprite png2chr build/tiles.png build/player.png -o build/game.chr --c build/chr.c --pad 8192
    retrosprite preview build/tiles.png out/preview/tiles_x8.png

png2chr: NES 2bpp planar CHR, 16 bytes per 8x8 tile (8 bytes plane 0, 8 bytes
plane 1), tiles in reading order, each input PNG's tiles after the previous one's
(the tool prints where each starts); --tall emits 8x16 sprite pairs (top, bottom).
--c writes a C array placed in llvm-mos's .chr_rom section, padded with --pad.
GBDK targets don't need png2chr: png2asset converts PNGs for gb, sms and gg itself.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

LEGACY = {".": 0, "-": 1, "+": 2, "#": 3}
GREY4 = ["#ffffff", "#aaaaaa", "#555555", "#000000"]
GREY16 = [f"#{v:02x}{v:02x}{v:02x}" for v in range(255, -1, -17)]
# per system: max opaque colours per tile for BG, for sprites
LIMITS = {"gb": (4, 3), "sms": (16, 15), "gg": (16, 15), "nes": (4, 3)}


def parse_palette(spec, needed):
    if not spec or spec == "grey":
        return GREY4 if needed <= 4 else GREY16
    cols = [c.strip() for c in spec.split(",") if c.strip()]
    if len(cols) < needed:
        sys.exit(f"art uses index {needed - 1} but the palette has only {len(cols)} colours")
    if len(cols) > 16:
        sys.exit("at most 16 colours")
    return cols


def hex_rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def parse_txt(text):
    frames, cur = [], []
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith((";", "//")):
            continue
        if not line:
            if cur:
                frames.append(cur)
                cur = []
            continue
        row = []
        for ch in line:
            if ch in LEGACY:
                row.append(LEGACY[ch])
            elif ch.lower() in "0123456789abcdef":
                row.append(int(ch, 16))
            else:
                sys.exit(f"bad character {ch!r} in line {line!r}")
        cur.append(row)
    if cur:
        frames.append(cur)
    if not frames:
        sys.exit("no pixels found")
    for i, f in enumerate(frames):
        if len({len(r) for r in f}) != 1:
            sys.exit(f"frame {i}: ragged rows")
        if len(f) % 8 or len(f[0]) % 8:
            sys.exit(f"frame {i}: {len(f[0])}x{len(f)} is not a multiple of 8")
    if len({(len(f[0]), len(f)) for f in frames}) != 1:
        sys.exit("all frames must share one size")
    return frames


def frames_to_image(frames, palette, vertical=False):
    fw, fh, n = len(frames[0][0]), len(frames[0]), len(frames)
    im = Image.new("P", (fw, fh * n) if vertical else (fw * n, fh), 0)
    flat = []
    for c in palette:
        flat += hex_rgb(c)
    im.putpalette(flat)
    px = im.load()
    for i, f in enumerate(frames):
        ox, oy = (0, i * fh) if vertical else (i * fw, 0)
        for y, row in enumerate(f):
            for x, v in enumerate(row):
                px[ox + x, oy + y] = v
    return im


def indices(im):
    if im.mode == "P":
        px = im.load()
        return [[px[x, y] for x in range(im.width)] for y in range(im.height)]
    g = im.convert("L").load()  # unindexed: 4 luminance buckets, darkest = 3
    return [[3 - min(3, g[x, y] * 4 // 256) for x in range(im.width)] for y in range(im.height)]


def tiles(idx, w, h, tall=False):
    """8x8 tiles in reading order; with tall, 8x16 column pairs (top then bottom)."""
    if tall:
        order = [(tx, ty + d) for ty in range(0, h, 16) for tx in range(0, w, 8) for d in (0, 8)]
    else:
        order = [(tx, ty) for ty in range(0, h, 8) for tx in range(0, w, 8)]
    return [[[idx[ty + y][tx + x] for x in range(8)] for y in range(8)] for tx, ty in order]


def to_chr(tile):
    lo = bytes(sum(((tile[y][x] & 1) << (7 - x)) for x in range(8)) for y in range(8))
    hi = bytes(sum((((tile[y][x] >> 1) & 1) << (7 - x)) for x in range(8)) for y in range(8))
    return lo + hi


def check(path, system, sprite):
    im = Image.open(path)
    problems = []
    if im.width % 8 or im.height % 8:
        problems.append(f"size {im.width}x{im.height} is not a multiple of 8")
    idx = indices(im)
    limit = LIMITS[system][1 if sprite else 0]
    worst = 0
    for ty in range(0, im.height - im.height % 8, 8):
        for tx in range(0, im.width - im.width % 8, 8):
            used = {idx[ty + y][tx + x] for y in range(8) for x in range(8)}
            if sprite:
                used.discard(0)
            worst = max(worst, len(used))
            if len(used) > limit:
                problems.append(f"tile ({tx // 8},{ty // 8}) uses {len(used)} colours; {system} limit {limit}"
                                + (" + transparent" if sprite else ""))
            if system in ("gb", "nes") and max(used | {0}) > 3:
                problems.append(f"tile ({tx // 8},{ty // 8}) uses index {max(used)}; {system} tiles are 2bpp (0-3)")
    print(f"{path}: {im.width}x{im.height}, {(im.width // 8) * (im.height // 8)} tiles, "
          f"up to {worst} colours per tile [{system}{' sprite' if sprite else ''} rules]")
    for p in problems[:20]:
        print("  PROBLEM:", p)
    return len(problems)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="retrosprite", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("txt2png")
    p.add_argument("src"); p.add_argument("dst")
    p.add_argument("--palette", help='"grey" (default) or comma list of up to 16 hex colours')
    p.add_argument("--vertical", action="store_true")
    p.add_argument("--preview"); p.add_argument("--scale", type=int, default=8)
    p = sub.add_parser("png2txt")
    p.add_argument("src"); p.add_argument("--frame-width", type=int, default=0)
    p = sub.add_parser("check")
    p.add_argument("src"); p.add_argument("--system", choices=sorted(LIMITS), required=True)
    p.add_argument("--sprite", action="store_true")
    p = sub.add_parser("png2chr")
    p.add_argument("src", nargs="+"); p.add_argument("-o", dest="dst", required=True)
    p.add_argument("--tall", action="store_true", help="8x16 sprite order")
    p.add_argument("--c", help="also write a C file with the data in the .chr_rom section")
    p.add_argument("--name", default="chr_data")
    p.add_argument("--pad", type=int, default=0, help="pad the C array to this many bytes (8192 = one CHR bank)")
    p.add_argument("--offset", type=int, default=0, help="tile index to start at within the padded bank")
    p = sub.add_parser("preview")
    p.add_argument("src"); p.add_argument("dst"); p.add_argument("--scale", type=int, default=8)
    a = ap.parse_args(argv)

    if a.cmd == "txt2png":
        frames = parse_txt(Path(a.src).read_text())
        needed = 1 + max(v for f in frames for r in f for v in r)
        im = frames_to_image(frames, parse_palette(a.palette, needed), a.vertical)
        Path(a.dst).parent.mkdir(parents=True, exist_ok=True)
        im.save(a.dst)
        print(f"{a.dst}: {len(frames)} frame(s) of {len(frames[0][0])}x{len(frames[0])}, {needed} colour indices")
        if a.preview:
            Path(a.preview).parent.mkdir(parents=True, exist_ok=True)
            im.convert("RGB").resize((im.width * a.scale, im.height * a.scale), Image.NEAREST).save(a.preview)
            print(f"preview: {a.preview}")
        return 0
    if a.cmd == "png2txt":
        im = Image.open(a.src)
        idx = indices(im)
        fw = a.frame_width or im.width
        sym = ".-+#" if max(max(r) for r in idx) < 4 else "0123456789abcdef"
        for fx in range(0, im.width, fw):
            for row in idx:
                print("".join(sym[v] for v in row[fx:fx + fw]))
            print()
        return 0
    if a.cmd == "check":
        return 1 if check(a.src, a.system, a.sprite) else 0
    if a.cmd == "png2chr":
        data = b""
        for src in a.src:
            im = Image.open(src)
            if im.width % 8 or im.height % (16 if a.tall else 8):
                sys.exit(f"{src}: {im.width}x{im.height} does not divide into {'8x16' if a.tall else '8x8'} tiles")
            idx = indices(im)
            if max(max(r) for r in idx) > 3:
                sys.exit(f"{src}: NES CHR is 2bpp; indices above 3 found")
            print(f"  {src}: tiles start at {a.offset + len(data) // 16}")
            data += b"".join(to_chr(t) for t in tiles(idx, im.width, im.height, a.tall))
        Path(a.dst).parent.mkdir(parents=True, exist_ok=True)
        Path(a.dst).write_bytes(data)
        print(f"{a.dst}: {len(data) // 16} tiles, {len(data)} bytes")
        if a.c:
            blob = bytes(a.offset * 16) + data
            if a.pad:
                if len(blob) > a.pad:
                    sys.exit(f"{len(blob)} bytes do not fit --pad {a.pad}")
                blob += bytes(a.pad - len(blob))
            rows = [", ".join(f"0x{b:02x}" for b in blob[i:i + 16]) for i in range(0, len(blob), 16)]
            Path(a.c).write_text(f"// generated by retrosprite png2chr from {' '.join(a.src)} - do not edit\n"
                                 f"#include <stdint.h>\n__attribute__((section(\".chr_rom\"), used))\n"
                                 f"const uint8_t {a.name}[{len(blob)}] = {{\n  " + ",\n  ".join(rows) + "\n};\n")
            print(f"{a.c}: {len(blob)} bytes in .chr_rom")
        return 0
    if a.cmd == "preview":
        im = Image.open(a.src)
        Path(a.dst).parent.mkdir(parents=True, exist_ok=True)
        im.convert("RGB").resize((im.width * a.scale, im.height * a.scale), Image.NEAREST).save(a.dst)
        print(a.dst)
        return 0


if __name__ == "__main__":
    sys.exit(main())
