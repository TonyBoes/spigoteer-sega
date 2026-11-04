#!/usr/bin/env python3
"""quick.py FILE.txt OUT.png [scale] [names,...]: poses of a block file, CGB over DMG at scale and 1x (x3), no glass."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw

CGB = {".": (40, 88, 88), "-": (0xF8, 0xD0, 0xA8), "+": (0xA0, 0x30, 0x70), "#": (0x20, 0x10, 0x18)}
DMG = {".": (255, 255, 255), "-": (153, 153, 153), "+": (85, 85, 85), "#": (0, 0, 0)}


def blocks(path):
    res, cur, name = {}, [], None
    for ln in Path(path).read_text().splitlines() + [""]:
        if ln.startswith("@"):
            name = ln[1:].strip(); cur = []
        elif ln.strip() == "" or ln.startswith(";"):
            if cur and name:
                res[name] = cur
                cur = []
        else:
            cur.append(ln)
    return res


GE = ["........", "........", "........", "........", ".#-..-#.", ".#....#.", ".#....#.", ".#....#.", ".#....#.", "..#..#..", "...##...", "...##...", "...##...", "...##...", ".######.", "........"]
GF = ["........", "........", "........", "........", ".#-..-#.", ".#....#.", ".#....#.", ".#++++#.", ".#+-++#.", "..#++#..", "...##...", "...##...", "...##...", "...##...", ".######.", "........"]
TILT = [r.strip()[::-1] for r in open("/workspace/.claude/worktrees/agent-a781dd25b24512d04/assets/approved/venues/bistro_tilt.txt") if r.strip() and not r.startswith(";")]
GC = {"-": (0xF0, 0xF0, 0xF8), "+": (0xC8, 0xD0, 0xE0), "#": (0x30, 0x30, 0x48)}
GCF = {"-": (0xF8, 0xF0, 0xF0), "+": (0xB0, 0x18, 0x40), "#": (0x30, 0x10, 0x20)}
GD = {"-": (255, 255, 255), "+": (153, 153, 153), "#": (0, 0, 0)}
MOCK = {}


def draw(rows, pal, s, name=None):
    rows = [r.ljust(32, ".") for r in rows]
    im = Image.new("RGB", (32 * s, len(rows) * s), pal["."])
    d = ImageDraw.Draw(im)
    for y, r in enumerate(rows):
        for x, c in enumerate(r):
            d.rectangle([x * s, y * s, (x + 1) * s - 1, (y + 1) * s - 1], fill=pal[c])
    if name in ("HOLD", "GULP", "GULP_UP"):
        cg = pal["."] == (40, 88, 88)
        if name == "HOLD":
            spr, ox, oy, gp = GE, 24, -2, GC if cg else GD
        elif name == "GULP":
            spr, ox, oy, gp = TILT, 10, 4, GCF if cg else GD
        else:
            spr, ox, oy, gp = GF, 24, -2, GCF if cg else GD
        for y, r in enumerate(spr):
            for x, c in enumerate(r):
                if c != "." and 0 <= oy + y < len(rows):
                    d.rectangle([(ox + x) * s, (oy + y) * s, (ox + x + 1) * s - 1, (oy + y + 1) * s - 1], fill=gp[c])
    return im


if __name__ == "__main__":
    f, out = sys.argv[1], sys.argv[2]
    s = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    b = blocks(f)
    names = sys.argv[4].split(",") if len(sys.argv) > 4 else [n for n in b if len(b[n]) == 16 and not n.startswith("HAT")]
    cols = 3
    cw, ch = 32 * s + 6, 16 * s * 2 + 6 + 16 * 3 * 2
    n = len(names)
    im = Image.new("RGB", (cols * cw, ((n + cols - 1) // cols) * (ch)), (80, 80, 80))
    for k, nm in enumerate(names):
        x0, y0 = (k % cols) * cw, (k // cols) * ch
        im.paste(draw(b[nm], CGB, s, nm), (x0, y0))
        im.paste(draw(b[nm], DMG, s, nm), (x0, y0 + 16 * s))
        one = draw(b[nm], CGB, 3, nm)
        im.paste(one, (x0, y0 + 32 * s + 4))
        im.paste(draw(b[nm], DMG, 3, nm), (x0 + 32 * 3 + 6, y0 + 32 * s + 4))
        ImageDraw.Draw(im).text((x0 + 3, y0 + 2), nm, fill=(255, 255, 0))
    im.save(out)
