"""python3 -I sheets.py [A|B|C ...]    builds the owner's contact sheets into docs/dev/proposals/smap_owner_1108/ (sheet_A_desert_peaks.png, sheet_B_town.png, sheet_C_tea_house.png).

Each panel is a crop of a whole-map render of the pipeline (render.py: the cell palettes of world.json, the DMG shades), cut on cell boundaries, scaled x3 (x6 for close-ups) with nearest neighbour,
under a caption bar in a large bold font (the owner reads on a phone).  The panels go through tools/dev/contact_sheet.py (--scale 1: the panels are already scaled, so the captions stay sharp),
two columns: NOW on the left, AFTER on the right.  Colour is the palette's raw RGB (no emulator colour correction); DMG is the four neutral grays the project uses.
Renders needed (run on demand): base, a1, a2, b123, c, c3."""
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUT = ROOT / "out" / "owner1108"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
RENDERS = {"base": "", "a1": "A1", "a2": "A2", "b123": "B1,B2,B3", "c": "C", "c3": "C3"}


def ensure(tag):
    if not (OUT / f"{tag}_c.png").exists() or os.environ.get("FRESH"):
        subprocess.run([sys.executable, "-I", str(HERE / "render.py"), tag], env=dict(os.environ, OWNER=RENDERS[tag]), check=True, stdout=subprocess.DEVNULL)


def panel(tag, mode, box, scale, caption, sub=None):
    """crop `box` (cells x0 y0 x1 y1, x1 and y1 excluded) of a render, scale it, put a caption bar on top"""
    ensure(tag)
    im = Image.open(OUT / f"{tag}_{'c' if mode == 'C' else 'd'}.png").convert("RGB")
    x0, y0, x1, y1 = box
    im = im.crop((x0 * 8, y0 * 8, x1 * 8, y1 * 8)).resize(((x1 - x0) * 8 * scale, (y1 - y0) * 8 * scale), Image.NEAREST)
    big = ImageFont.truetype(FONT, 30)
    small = ImageFont.truetype(FONT, 22)
    bar_h = 44 + (30 if sub else 0)
    out = Image.new("RGB", (im.width, im.height + bar_h), (30, 30, 30))
    d = ImageDraw.Draw(out)
    d.text((8, 5), caption, fill=(255, 255, 255), font=big)
    if sub:
        d.text((8, 44), sub, fill=(255, 220, 120), font=small)
    out.paste(im, (0, bar_h))
    return out


def sheet(name, panels, title):
    files = []
    for i, p in enumerate(panels):
        f = OUT / f"panel_{name}_{i}.png"
        p.save(f)
        files.append("=" + str(f))
    out = HERE / f"sheet_{name}.png"
    subprocess.run([sys.executable, str(ROOT / "tools" / "dev" / "contact_sheet.py"), str(out), "--scale", "1", "--cols", "2"] + files, check=True)
    print(out)


def sheet_a():
    box = (0, 28, 30, 45)
    P = []
    for arr, tag in (("A1", "a1"), ("A2", "a2")):
        sub = {"A1": "three peaks apart, every cactus stays", "A2": "a ridge of two, two singles; one cactus moves"}[arr]
        P += [panel("base", "C", box, 3, "NOW  Color"), panel(tag, "C", box, 3, f"{arr}  Color", sub)]
        P += [panel("base", "D", box, 3, "NOW  DMG"), panel(tag, "D", box, 3, f"{arr}  DMG", sub)]
    sheet("A_desert_peaks", P, "A")


def sheet_b():
    wide = (14, 14, 47, 37)
    pave_b, pave_a = (28, 24, 44, 33), (20, 24, 36, 33)
    awn_b, awn_a = (36, 22, 44, 29), (28, 22, 36, 29)
    P = [panel("base", "C", wide, 3, "NOW  Color"), panel("b123", "C", wide, 3, "AFTER  Color", "town 8 cells west, paved to the fronts and across the road"),
         panel("base", "D", wide, 3, "NOW  DMG"), panel("b123", "D", wide, 3, "AFTER  DMG"),
         panel("base", "C", pave_b, 5, "NOW  paving"), panel("b123", "C", pave_a, 5, "AFTER  paving", "cobbles meet the fronts, a band south of the road"),
         panel("base", "C", awn_b, 8, "NOW  awning"), panel("b123", "C", awn_a, 8, "AFTER  awning", "left edge, hem row, fringe"),
         panel("base", "D", awn_b, 8, "NOW  awning DMG"), panel("b123", "D", awn_a, 8, "AFTER  awning DMG")]
    sheet("B_town", P, "B")


def sheet_c():
    tea = (22, 54, 38, 63)
    west, east = (31, 41, 42, 49), (46, 41, 57, 49)
    P = [panel("base", "C", tea, 5, "NOW  tea house"), panel("c", "C", tea, 5, "AFTER  tea house", "whole house on the town palette (C)"),
         panel("base", "C", west, 6, "NOW  west bend"), panel("c", "C", west, 6, "AFTER  west bend", "grass, not cream"),
         panel("base", "C", east, 6, "NOW  east bend"), panel("c", "C", east, 6, "AFTER  east bend", "grass, not cream"),
         panel("base", "C", tea, 5, "NOW  tea house"), panel("c3", "C", tea, 5, "OPTION C3  east end only", "keeps the house colours; lantern and tree change")]
    sheet("C_tea_house", P, "C")


if __name__ == "__main__":
    want = sys.argv[1:] or ["A", "B", "C"]
    for w in want:
        {"A": sheet_a, "B": sheet_b, "C": sheet_c}[w]()
