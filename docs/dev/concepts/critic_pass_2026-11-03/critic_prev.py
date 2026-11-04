#!/usr/bin/env python3
"""Preview and build helper for the Food Critic pass (preview only: reads a version file, writes under out/ or this folder;
never touches assets/ or src/).  Every pixel is in the version files (hand-placed grids); this script only converts them.

  critic_prev.py build VER OUT.txt     a full assets/art/boss/critic.txt for a SCRATCH build: the version's hand-drawn poses
                                       (@WALK @GULP @WINCE @HAPPY @TASTE @HOLD and the topper) + every other block of the
                                       current critic.txt unchanged; @STOMP and @HOLDHOP are the same art one row lower
                                       (as in the current file: a pure offset, bottom row dropped, top row blank)
  critic_prev.py pairs VER|cur         gen_boss's unique 8x16 body column pairs (limit 29) per pose
  critic_prev.py sheet VER OUT.png     every pose, Color over DMG, x6, glass sprite mocked where the engine would draw it
  critic_prev.py png VER OUT.png       all poses as one 4-shade indexed PNG (for gb_art_lint.py)
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import gen_boss as g  # noqa: E402  (read only: blocks(), column(), sway_pose())

CUR = ROOT / "assets/art/boss/critic.txt"
DRAWN = ["WALK", "GULP", "WINCE", "HAPPY", "TASTE", "HOLD"]
ORDER = ["WALK", "STOMP", "GULP", "WINCE", "HAPPY", "TASTE", "HOLD", "HOLDHOP"]
CGB = {".": (40, 88, 88), "-": (0xF8, 0xD0, 0xA8), "+": (0xA0, 0x30, 0x70), "#": (0x20, 0x10, 0x18)}   # the wall as the bistro's (a capture)
DMG = {".": (255, 255, 255), "-": (153, 153, 153), "+": (85, 85, 85), "#": (0, 0, 0)}                  # BGP as captured from the ROM
# the bistro's empty wine glass (assets/approved/venues/bistro_drink.txt frame 2, palette bistro_drink_empty) and the full one (frame 1)
GLASS_EMPTY = ["........", "........", "........", "........", ".#-..-#.", ".#....#.", ".#....#.", ".#....#.", ".#....#.", "..#..#..",
               "...##...", "...##...", "...##...", "...##...", ".######.", "........"]
GLASS_FULL = ["........", "........", "........", "........", ".#-..-#.", ".#....#.", ".#....#.", ".#++++#.", ".#+-++#.", "..#++#..",
              "...##...", "...##...", "...##...", "...##...", ".######.", "........"]
G_CGB_E = {"-": (0xF0, 0xF0, 0xF8), "+": (0xC8, 0xD0, 0xE0), "#": (0x30, 0x30, 0x48)}
G_CGB_F = {"-": (0xF8, 0xF0, 0xF0), "+": (0xB0, 0x18, 0x40), "#": (0x30, 0x10, 0x20)}
G_DMG = {"-": (255, 255, 255), "+": (153, 153, 153), "#": (0, 0, 0)}
HAND_BASE = 12      # src/boss.c hand_base for the Critic: the mug's foot (its sprite row 14) on body row 12


def version_path(v):
    p = Path(v)
    return CUR if v == "cur" else (p if p.exists() else HERE / f"{v}.txt")


def load(v):
    """pose name -> 16 rows of 32 chars (STOMP / HOLDHOP derived)"""
    named = dict(g.blocks(version_path(v), named=True))
    if v == "cur":
        return {n: named[n] for n in ORDER}
    out = {}
    for n in DRAWN:
        rows = named[n]
        assert len(rows) == 16 and all(len(r) <= 32 for r in rows), f"{v} @{n}: must be 16 rows of at most 32, got {len(rows)} rows, widths {[len(r) for r in rows]}"
        out[n] = [r.ljust(32, ".") for r in rows]       # (a row may stop early: the wall to its right)
    out["STOMP"] = ["." * 32] + out["WALK"][:15]
    out["HOLDHOP"] = ["." * 32] + out["HOLD"][:15]
    return {n: out[n] for n in ORDER}


def topper(v):
    named = dict(g.blocks(version_path(v), named=True))
    return named["HAT_STILL"], named["HAT_BOB"]


def build(v, out):
    """the current critic.txt with the version's poses (and topper) replacing the same-named blocks."""
    poses = load(v)
    named = dict(g.blocks(version_path(v), named=True))
    lines, skip = [], False
    for ln in CUR.read_text().split("\n"):
        if ln.startswith("@"):
            n = ln[1:].strip()
            skip = n in poses or (n in ("HAT_STILL", "HAT_BOB") and n in named)
            if skip:
                rows = poses[n] if n in poses else named[n]
                lines.append(ln)
                lines += rows
                continue
        elif skip:
            if ln.strip() == "" or ln.startswith(";"):
                skip = False
            else:
                continue
        lines.append(ln)
    Path(out).write_text("\n".join(lines))
    print("wrote", out)


def pairs(v, quiet=False):
    poses = load(v)
    idx, per = {}, {}
    for n in ORDER:
        per[n] = [idx.setdefault(g.column(poses[n], x), len(idx)) for x in range(0, 32, 8)]
    sw = g.sway_pose(poses["GULP"], 32, None)
    per["SWAY"] = [idx.setdefault(g.column(sw[1], x), len(idx)) for x in range(0, 32, 8)]
    if not quiet:
        print(v, "unique pairs:", len(idx), "of 29 (sway dir", sw[0], ")")
        for n, p in per.items():
            print(f"  {n:8s}", p)
    return len(idx)


def draw_pose(rows, pal, scale, dx=0, dy=0):
    im = Image.new("RGB", (32 * scale, 20 * scale), pal["."])
    d = ImageDraw.Draw(im)
    for y, r in enumerate(rows):
        for x, c in enumerate(r):
            d.rectangle([x * scale, (y + 2) * scale, (x + 1) * scale - 1, (y + 3) * scale - 1], fill=pal[c])
    return im


def paste_glass(im, scale, kind, cgb, oy=0, ox=0, upto=None):
    """the engine's glass sprite over the hand column: x 24 (boss_x + width - 8 + ox), foot (sprite row 14) on body row HAND_BASE + oy"""
    g_rows = GLASS_FULL if kind == "full" else GLASS_EMPTY
    pal = (G_CGB_F if kind == "full" else G_CGB_E) if cgb else G_DMG
    d = ImageDraw.Draw(im)
    for y, r in enumerate(g_rows):
        for x, c in enumerate(r):
            if c == ".":
                continue
            px, py = 24 + x + ox, (HAND_BASE - 14 + y + oy) + 2
            d.rectangle([px * scale, py * scale, (px + 1) * scale - 1, (py + 1) * scale - 1], fill=pal[c])


# which poses get a glass sprite in the proposal: (kind, dy)
GLASS = {"HOLD": ("empty", 0), "HOLDHOP": ("empty", 1), "HAPPY": ("full", -3), "GULP": ("full", 0)}


def sheet(v, out, scale=6, glass=True):
    poses = load(v)
    cw, ch = 32 * scale + 8, 20 * scale + 8
    im = Image.new("RGB", (4 * cw, 2 * 2 * ch + 4), (90, 90, 90))
    for k, n in enumerate(ORDER):
        for m, (pal, cg) in enumerate(((CGB, True), (DMG, False))):
            t = draw_pose(poses[n], pal, scale)
            if glass and v != "cur" and n in GLASS:
                paste_glass(t, scale, GLASS[n][0], cg, GLASS[n][1])
            ImageDraw.Draw(t).text((2, 2), n, fill=(255, 255, 0) if cg else (255, 0, 0))
            im.paste(t, ((k % 4) * cw + 4, (k // 4) * 2 * ch + m * ch + 4))
    im.save(out)


def pose(v, names, out, scale=8):
    """names (comma list) of version v beside the current art's same pose, Color and DMG, at `scale` and at 1x (x2 shown)."""
    names = names.split(",")
    scale = int(scale)
    tiles = []
    for n in names:
        for ver in ("cur", v):
            rows = load(ver)[n]
            for pal, cg in ((CGB, True), (DMG, False)):
                t = draw_pose(rows, pal, scale)
                if ver != "cur" and n in GLASS:
                    paste_glass(t, scale, GLASS[n][0], cg, GLASS[n][1])
                one = draw_pose(rows, pal, 1)
                if ver != "cur" and n in GLASS:
                    paste_glass(one, 1, GLASS[n][0], cg, GLASS[n][1])
                one = one.resize((one.width * 3, one.height * 3), Image.NEAREST)
                ImageDraw.Draw(t).text((2, 2), f"{ver} {n}", fill=(255, 255, 0) if cg else (255, 0, 0))
                tiles.append((t, one))
    tw = tiles[0][0].width
    cols = 4
    rows_n = (len(tiles) + cols - 1) // cols
    th = tiles[0][0].height + tiles[0][1].height + 4
    im = Image.new("RGB", (cols * (tw + 4), rows_n * (th + 4)), (90, 90, 90))
    for i, (t, one) in enumerate(tiles):
        x, y = (i % cols) * (tw + 4), (i // cols) * (th + 4)
        im.paste(t, (x, y))
        im.paste(one, (x, y + t.height + 2))
    im.save(out)


def png(v, out):
    poses = load(v)
    im = Image.new("P", (32 * 8, 16 * 2), 0)
    im.putpalette([255, 255, 255, 170, 170, 170, 85, 85, 85, 0, 0, 0] + [0] * 756)
    for k, n in enumerate(ORDER):
        for y, r in enumerate(poses[n]):
            for x, c in enumerate(r):
                im.putpixel(((k % 8) * 32 + x if False else x, 0), 0)
    # one pose per image is what the lint wants: write a 32x(16*8) strip, poses stacked
    strip = Image.new("P", (32, 16 * len(ORDER)), 0)
    strip.putpalette([255, 255, 255, 170, 170, 170, 85, 85, 85, 0, 0, 0] + [0] * 756)
    for k, n in enumerate(ORDER):
        for y, r in enumerate(poses[n]):
            for x, c in enumerate(r):
                strip.putpixel((x, k * 16 + y), ".-+#".index(c))
    strip.save(out)


if __name__ == "__main__":
    cmd, a = sys.argv[1], sys.argv[2:]
    if cmd == "build":
        build(*a)
    elif cmd == "pairs":
        pairs(*a)
    elif cmd == "sheet":
        sheet(*a)
    elif cmd == "pose":
        pose(*a)
    elif cmd == "png":
        png(*a)
