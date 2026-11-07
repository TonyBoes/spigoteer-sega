"""Renders of the INTEGRATED map (mapctx.py).   Two modes:
  python3 renders.py crops TAG OUTDIR     one process per configuration (env SMAP_WATERDMG=light, SMAP_BROKEN=1 as mapctx.py): writes OUTDIR/TAG_whole_{color,dmg}.png (x2) and
                                          OUTDIR/TAG_{piece}_{color,dmg}.png (x3 close-ups of every approved piece's region)
  python3 renders.py sheet OUTDIR         assembles the labelled sheets from those files and the approved sheets: whole-map sheet and the piece sheets (two columns:
                                          the approved sheet | the integrated close-up, big bold labels)
Only reads; writes under OUTDIR."""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
PROP = HERE.parent
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# the pieces: key -> (cell box x0, y0, x1, y1 (exclusive), the approved sheet, label, water: show the DMG light-water column too)
PIECES = [
    ("falls", (41, 2, 54, 14), "smap_layout_a5/sheet_falls_all.png", "A5 falls: foam lip, pond glints, stream bridge", True),
    ("logs_up", (40, 16, 52, 32), "smap_layout_a5/sheet_logs_river.png", "Single logs v1, half-submerged: river north", True),
    ("logs_low", (38, 50, 50, 70), "smap_layout_a5/sheet_logs_river.png", "Single logs v1, half-submerged: river south", True),
    ("bridge_lake", (47, 29, 61, 38), "smap_layout_a5/sheet_bridges.png", "Bridges with raised sides: the mill pond bridge", True),
    ("bridge_big", (35, 58, 49, 67), "smap_layout_a5/sheet_bridges.png", "Bridges with raised sides: the lake bridge", True),
    ("town", (29, 16, 47, 30), "smap_fountain/sheet_centred.png", "Town: fountain round 3 (working state), bunting, awning ink border", False),
    ("town_broken", (29, 16, 47, 30), "smap_fountain/sheet_broken.png", "Town: fountain BROKEN state", False),
    ("stadium", (0, 0, 15, 13), "smap_stadium/stadium_map_sheet2.png", "Stadium: final 2 + wavy flag, BLEND onto the map", False),
    ("igloo", (47, 2, 64, 15), "smap_venue_redesign/igloo_sheet.png", "Igloo option 1: COCOA sign, chimney, penguin", False),
    ("airbase", (2, 31, 31, 46), "smap_hangar/hangar_sheet9.png", "Airbase 4i, jet nudged right (on the map at cell 4, 34)", False),
    ("milkbar", (46, 45, 64, 66), "smap_milkbar/milkbar_sheet14.png", "Milk bar: sign B raised + 4 px left, body on base, tea cell", False),
    ("lodge", (52, 16, 64, 28), None, "Lodge chimney smoke (static art at rest)", False),
    ("factory", (50, 34, 64, 47), None, "Factory stacks (static art at rest)", False),
]


def crops(tag, out):
    sys.path.insert(0, str(HERE))
    import mapctx as M
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for cgb in (True, False):
        n = "color" if cgb else "dmg"
        M.render(cgb, scale=2).save(out / f"{tag}_whole_{n}.png")
        for key, box, _, _, _ in PIECES:
            M.render(cgb, box, scale=3).save(out / f"{tag}_{key}_{n}.png")


def font(n):
    return ImageFont.truetype(FONT, n)


def label(im, text, size=34, bg=(30, 30, 30), fg=(255, 255, 255)):
    """image with a big bold label bar on top"""
    f = font(size)
    h = size + 22
    out = Image.new("RGB", (im.width, im.height + h), bg)
    d = ImageDraw.Draw(out)
    d.text((12, 8), text, font=f, fill=fg)
    out.paste(im, (0, h))
    return out


def fit(im, w):
    if im.width == w:
        return im
    return im.resize((w, max(1, round(im.height * w / im.width))), Image.LANCZOS if im.width > w else Image.NEAREST)


def stack_h(ims, gap=14, bg=(30, 30, 30)):
    H = max(i.height for i in ims)
    W = sum(i.width for i in ims) + gap * (len(ims) - 1)
    o = Image.new("RGB", (W, H), bg)
    x = 0
    for i in ims:
        o.paste(i, (x, 0))
        x += i.width + gap
    return o


def stack_v(ims, gap=18, bg=(30, 30, 30)):
    W = max(i.width for i in ims)
    H = sum(i.height for i in ims) + gap * (len(ims) - 1)
    o = Image.new("RGB", (W, H), bg)
    y = 0
    for i in ims:
        o.paste(i, (0, y))
        y += i.height + gap
    return o


def sheet(out):
    out = Path(out)
    L = lambda f: Image.open(out / f).convert("RGB")
    # ---- whole map: three renders, x2 each, labelled ----
    ims = [label(L("A_whole_color.png"), "COLOR", 44), label(L("A_whole_dmg.png"), "DMG DARK WATER", 44), label(L("B_whole_dmg.png"), "DMG LIGHT WATER", 44)]
    stack_v([stack_h(ims[:2]), ims[2]]).save(out / "sheet_whole_map.png")
    stack_h(ims).save(out / "sheet_whole_map_row.png")
    # ---- pieces: row = [approved sheet | integrated close-up], column width 780 each ----
    COLW = 780
    rows = []
    for key, box, appr, text, water in PIECES:
        tag = "C" if key == "town_broken" else "A"
        cols = [label(L(f"{tag}_{key}_color.png"), "COLOR", 30), label(L(f"{tag}_{key}_dmg.png"), "DMG" + (" DARK" if water else ""), 30)]
        if water:
            cols.append(label(L(f"B_{key}_dmg.png"), "DMG LIGHT", 30))
        mine = stack_h(cols)
        mine = fit(mine, COLW) if mine.width > COLW else mine
        left = label(fit(Image.open(PROP / appr).convert("RGB"), COLW), "APPROVED SHEET", 30) if appr else label(Image.new("RGB", (COLW, 60), (60, 60, 60)), "no sheet: see the animation strips", 30)
        row = stack_h([left, mine], gap=20)
        rows.append(label(row, text, 40, bg=(70, 40, 90)))
    # split into sheets of a manageable height
    groups, cur, h = [], [], 0
    for r in rows:
        if cur and h + r.height > 3200:
            groups.append(cur)
            cur, h = [], 0
        cur.append(r)
        h += r.height + 30
    groups.append(cur)
    for i, g in enumerate(groups, 1):
        stack_v(g, gap=30).save(out / f"sheet_pieces_{i}.png")
    print("sheets:", len(groups) + 2)


if __name__ == "__main__":
    if sys.argv[1] == "crops":
        crops(sys.argv[2], sys.argv[3])
    else:
        sheet(sys.argv[2])
