"""`gbsprite` — pixel art for the agent: ASCII grids in, indexed PNGs out, and checks.

ASCII format (assets/sprites/*.txt): one character per pixel.
    .  index 0  (lightest; TRANSPARENT for sprites)      0 also accepted
    -  index 1                                             1
    +  index 2                                             2
    #  index 3  (darkest)                                  3
Lines starting with ';' or '//' are comments. A blank line ends a frame; frames
are laid out left to right in the output PNG (--vertical stacks them), so a
4-frame 8x8 walk cycle becomes a 32x8 PNG that png2asset / rgbgfx split into tiles.

    gbsprite txt2png assets/sprites/player.txt build/player.png --preview out/player_x8.png
    gbsprite png2txt build/player.png                 # read a PNG back as text
    gbsprite check build/player.png --sprite          # hardware limits
    gbsprite preview build/tiles.png out/tiles_x8.png # nearest-neighbour upscale to look at

Indices map to colours by the palette (default a 4-step grey ramp, index 0
white). rgbgfx and png2asset both derive tile data from the palette order of an
indexed PNG, so index 0 here is colour 0 on the hardware.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

CHARS = {".": 0, "-": 1, "+": 2, "#": 3, "0": 0, "1": 1, "2": 2, "3": 3}
REV = ".-+#"
GREY = [(255, 255, 255), (170, 170, 170), (85, 85, 85), (0, 0, 0)]
DMG_GREEN = [(224, 248, 208), (136, 192, 112), (52, 104, 86), (8, 24, 32)]


def parse_palette(spec: str | None) -> list[tuple[int, int, int]]:
    if not spec or spec == "grey":
        return GREY
    if spec == "green":
        return DMG_GREEN
    cols = []
    for part in spec.split(","):
        h = part.strip().lstrip("#")
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        cols.append(tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)))
    if len(cols) != 4:
        sys.exit("palette needs exactly 4 colours")
    return cols


def parse_txt(text: str) -> list[list[list[int]]]:
    frames, cur = [], []
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.lstrip().startswith((";", "//")):
            continue
        if not line.strip():
            if cur:
                frames.append(cur)
                cur = []
            continue
        row = []
        for ch in line.strip():
            if ch not in CHARS:
                sys.exit(f"bad character {ch!r} in line: {line!r}")
            row.append(CHARS[ch])
        cur.append(row)
    if cur:
        frames.append(cur)
    if not frames:
        sys.exit("no pixels found")
    for i, f in enumerate(frames):
        w = {len(r) for r in f}
        if len(w) != 1:
            sys.exit(f"frame {i}: ragged rows (widths {sorted(w)})")
        if len(f) % 8 or next(iter(w)) % 8:
            sys.exit(f"frame {i}: {next(iter(w))}x{len(f)} is not a multiple of 8")
    if len({(len(f[0]), len(f)) for f in frames}) != 1:
        sys.exit("all frames must share one size")
    return frames


def frames_to_image(frames, palette, vertical=False) -> Image.Image:
    fw, fh = len(frames[0][0]), len(frames[0])
    n = len(frames)
    w, h = (fw, fh * n) if vertical else (fw * n, fh)
    im = Image.new("P", (w, h), 0)
    flat = []
    for c in palette:
        flat += c
    im.putpalette(flat)
    px = im.load()
    for i, f in enumerate(frames):
        ox, oy = (0, i * fh) if vertical else (i * fw, 0)
        for y, row in enumerate(f):
            for x, v in enumerate(row):
                px[ox + x, oy + y] = v
    return im


def image_to_indices(im: Image.Image) -> list[list[int]]:
    """Any PNG -> 0..3 per pixel. Indexed images use their index (mod 4 per palette slot);
    everything else is bucketed by luminance so a quick sketch still reads back."""
    if im.mode == "P":
        px = im.load()
        return [[px[x, y] & 3 for x in range(im.width)] for y in range(im.height)]
    g = im.convert("L").load()
    return [[3 - min(3, g[x, y] * 4 // 256) for x in range(im.width)] for y in range(im.height)]


def preview(im: Image.Image, scale: int) -> Image.Image:
    return im.convert("RGB").resize((im.width * scale, im.height * scale), Image.NEAREST)


def check(path: Path, sprite: bool, max_pals: int) -> int:
    """Validate against hardware limits per 8x8 tile. Returns problem count."""
    im = Image.open(path)
    problems = []
    if im.width % 8 or im.height % 8:
        problems.append(f"size {im.width}x{im.height} is not a multiple of 8")
    rgb = im.convert("RGBA")
    px = rgb.load()
    pal_sets = set()
    opaque_limit = 3 if sprite else 4
    for ty in range(0, im.height - im.height % 8, 8):
        for tx in range(0, im.width - im.width % 8, 8):
            cols = set()
            for y in range(ty, ty + 8):
                for x in range(tx, tx + 8):
                    r, g, b, a = px[x, y]
                    if sprite and (a < 128 or (im.mode == "P" and im.getpixel((x, y)) == 0)):
                        continue
                    cols.add((r, g, b))
            if len(cols) > opaque_limit:
                problems.append(f"tile ({tx//8},{ty//8}) uses {len(cols)} colours; limit {opaque_limit}"
                                + (" + transparent" if sprite else ""))
            pal_sets.add(frozenset(cols))
    # Greedy palette merge: tiles whose colour sets nest share a palette.
    pals: list[set] = []
    for s in sorted(pal_sets, key=len, reverse=True):
        for p in pals:
            if s <= p or len(p | s) <= opaque_limit:
                p |= s
                break
        else:
            pals.append(set(s))
    if len(pals) > max_pals:
        problems.append(f"needs about {len(pals)} palettes; hardware has {max_pals}")
    print(f"{path}: {im.width}x{im.height}, {im.width//8 * im.height//8} tiles, ~{len(pals)} palette(s)"
          + (" [sprite rules]" if sprite else ""))
    for p in problems:
        print("  PROBLEM:", p)
    return len(problems)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="gbsprite", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("txt2png")
    p.add_argument("src"); p.add_argument("dst")
    p.add_argument("--palette", help='"grey" (default), "green", or 4 hex colours "#fff,#aaa,#555,#000"')
    p.add_argument("--vertical", action="store_true")
    p.add_argument("--preview", help="also write an upscaled RGB PNG here")
    p.add_argument("--scale", type=int, default=8)

    p = sub.add_parser("png2txt")
    p.add_argument("src")
    p.add_argument("--frame-width", type=int, default=0, help="split into frames of this width (0 = whole image)")

    p = sub.add_parser("check")
    p.add_argument("src")
    p.add_argument("--sprite", action="store_true", help="sprite rules: 3 colours + transparent (index 0 / alpha)")
    p.add_argument("--max-pals", type=int, default=8)

    p = sub.add_parser("preview")
    p.add_argument("src"); p.add_argument("dst")
    p.add_argument("--scale", type=int, default=8)

    a = ap.parse_args(argv)
    if a.cmd == "txt2png":
        frames = parse_txt(Path(a.src).read_text())
        im = frames_to_image(frames, parse_palette(a.palette), a.vertical)
        Path(a.dst).parent.mkdir(parents=True, exist_ok=True)
        im.save(a.dst)
        print(f"{a.dst}: {len(frames)} frame(s) of {len(frames[0][0])}x{len(frames[0])} -> {im.width}x{im.height}")
        if a.preview:
            Path(a.preview).parent.mkdir(parents=True, exist_ok=True)
            preview(im, a.scale).save(a.preview)
            print(f"preview: {a.preview}")
        return 0
    if a.cmd == "png2txt":
        im = Image.open(a.src)
        idx = image_to_indices(im)
        fw = a.frame_width or im.width
        for fx in range(0, im.width, fw):
            for row in idx:
                print("".join(REV[v] for v in row[fx:fx + fw]))
            print()
        return 0
    if a.cmd == "check":
        return 1 if check(Path(a.src), a.sprite, a.max_pals) else 0
    if a.cmd == "preview":
        Path(a.dst).parent.mkdir(parents=True, exist_ok=True)
        preview(Image.open(a.src), a.scale).save(a.dst)
        print(a.dst)
        return 0


if __name__ == "__main__":
    sys.exit(main())
