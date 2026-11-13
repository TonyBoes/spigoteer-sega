"""Contact sheets for the Boss Rush portrait proposals. Cells are made here (big labels), the sheet is assembled by tools/dev/contact_sheet.py.

    make_sheets.py base                      the portraits as they show now: DMG | Color | the whole figure, with the rows lost
    make_sheets.py OPT SHOTDIR [LINE ...]    one option: DMG | Color per boss from the screenshots in out/rush_shots/SHOTDIR (shoot_list.py)
Run from the worktree root (reads out/rush_shots, build/). Writes out/rush_sheets/.
"""
import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rp_common as c   # noqa: E402

ROOT = c.ROOT
SHOTS = ROOT / "out" / "rush_shots"
OUT = ROOT / "out" / "rush_sheets"
OUT.mkdir(parents=True, exist_ok=True)
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BG, FG, SUB = (40, 40, 40), (245, 245, 245), (200, 200, 120)
BACK_CGB = (3, 1, 1)
WIN = (48, 48, 112, 96)          # the list's window (8 x 6 tiles) on the 160 x 144 screen
WIN_PLUS = (36, 44, 124, 100)    # the window with a margin


def font(sz, bold=True):
    return ImageFont.truetype(FONT_B if bold else FONT_R, sz)


def cell(title, sub, panels, gap=10, pad=8):
    w = sum(p.width for p in panels) + gap * (len(panels) - 1) + 2 * pad
    h = max(p.height for p in panels) + 2 * pad + 56
    im = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(im)
    d.text((pad, 4), title, fill=FG, font=font(24))
    d.text((pad, 32), sub, fill=SUB, font=font(15, False))
    x = pad
    for p in panels:
        im.paste(p, (x, 56 + pad))
        x += p.width + gap
    return im


def crop(path, box, scale):
    im = Image.open(path).convert("RGB").crop(box)
    return im.resize((im.width * scale, im.height * scale), Image.NEAREST)


def figure_panel(name, scale):
    """The whole figure in his Color colours on the list's backdrop, the 16 rows the list shows now outlined in red."""
    rows, pal = c.full_boss(ROOT / "build", name)
    cols = [(224, 184, 112)] + [c.rgb15(v) for v in pal]
    w = len(rows[0])
    im = Image.new("RGB", (w * scale, 24 * scale), cols[0])
    d = ImageDraw.Draw(im)
    for y, r in enumerate(rows):
        for x, v in enumerate(r):
            if v:
                d.rectangle([x * scale, y * scale, (x + 1) * scale - 1, (y + 1) * scale - 1], fill=cols[v])
    d.rectangle([0, 8 * scale, w * scale - 1, 24 * scale - 1], outline=(255, 0, 0))
    return im


def assemble(name, cells, cols):
    paths = []
    for i, cl in enumerate(cells):
        p = OUT / f"cell_{name}_{i:02d}.png"
        cl.save(p)
        paths.append(f" ={p}")          # (a blank contact_sheet label: the cells carry their own big ones)
    out = OUT / f"{name}.png"
    subprocess.run([sys.executable, str(ROOT / "tools/dev/contact_sheet.py"), str(out), "--scale", "1", "--cols", str(cols)] + paths, check=True)
    return out


def lost_top(name):
    rows, _ = c.full_boss(ROOT / "build", name)
    return 8 - c.bbox(rows)[2]


def base():
    cells = []
    for k, n in enumerate(c.BOSSES):
        rows, _ = c.full_boss(ROOT / "build", n)
        lt = lost_top(n)
        r15 = sum(1 for v in rows[23] if v)
        sub = f"loses {lt} rows at the top, 0 at the bottom (flat cut: {r15}/{len(rows[0])} px on last row)"
        cells.append(cell(c.NAMES[n], sub, [crop(SHOTS / "base" / f"dmg_{k}.png", WIN, 4), crop(SHOTS / "base" / f"cgb_{k}.png", WIN, 4), figure_panel(n, 4)]))
    return assemble("now", cells, 1)


def option(label, shotdir, lines):
    cells = []
    for k, n in enumerate(c.BOSSES):
        cells.append(cell(c.NAMES[n], lines.get(n, ""), [crop(SHOTS / shotdir / f"dmg_{k}.png", WIN_PLUS, 3), crop(SHOTS / shotdir / f"cgb_{k}.png", WIN_PLUS, 3)]))
    return assemble(label, cells, 2)


if __name__ == "__main__":
    if sys.argv[1] == "base":
        print(base())
    else:
        extra = dict(a.split("=", 1) for a in sys.argv[3:])
        print(option(sys.argv[1], sys.argv[2], extra))
