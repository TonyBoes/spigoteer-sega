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
    ("ranges_ab", (16, 0, 48, 7), "smap_venue_redesign3/range_horizontal_sheet.png", "Range B (snowy) with peak variants; range A removed", False),
    ("ranges_c", (47, 0, 64, 7), "smap_venue_redesign3/range_vertical_sheet.png", "Range C (snowy) with peak variants, over the igloo and the river source", False),
    ("lodge",(52, 16, 64, 28), None, "Lodge chimney smoke (static art at rest)", False),
    ("factory", (50, 34, 64, 47), None, "Factory stacks (static art at rest)", False),
]


# stage 1c before | after close-ups: road corners (x4) and the ranges (x3); P_ files are the stage 1b state (env SMAP_BEFORE_1C=1)
COMPROMISE = [(35, 44), (37, 46), (50, 46), (52, 44), (61, 27), (61, 47)]       # corners shown again at x6: shared or existing palettes, or art next to the kerb


def corner_cells():
    """all 24 corner centres: outer corners at their cell, inner corners at their ground cell (diagonal to the junction cell), in the order outer then inner"""
    import mapctx as M
    import roads_round as R
    outer, inner = R.classify(M.W.WORLD.roads)
    cs = [(cx, cy) for cx, cy, _ in outer]
    cs += [(jx + (1 if "e" in k else -1), jy + (1 if "s" in k else -1)) for jx, jy, k in inner]
    return cs


def box_at(c, half, lim=64):
    x0 = min(max(c[0] - half, 0), lim - 2 * half)
    y0 = min(max(c[1] - half, 0), lim - 2 * half)
    return (x0, y0, x0 + 2 * half, y0 + 2 * half)
RANGE_BOXES = [(16, 0, 48, 7), (47, 0, 64, 7)]


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
        for i, c in enumerate(corner_cells()):
            M.render(cgb, box_at(c, 3), scale=4).save(out / f"{tag}_corner{i}_{n}.png")
        for i, c in enumerate(COMPROMISE):
            M.render(cgb, box_at(c, 2), scale=6).save(out / f"{tag}_comp{i}_{n}.png")
        for i, box in enumerate(RANGE_BOXES):
            M.render(cgb, box, scale=3).save(out / f"{tag}_range{i}_{n}.png")


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


def sheet_1c(out):
    """before | after for the stage 1c changes: road corners x4 and the ranges x3 (two columns, big labels)"""
    out = Path(out)
    L = lambda f: Image.open(out / f).convert("RGB")
    # corners: 3 per row, Color over DMG, before | after; 24 corners in two files (12 each)
    ncor = 24
    for part in range(2):
        sheets = []
        for r in range(4):
            cols = []
            for tag, name in (("P", "BEFORE"), ("A", "AFTER")):
                cells = []
                for i in range(part * 12 + 3 * r, part * 12 + 3 * r + 3):
                    cells.append(stack_v([L(f"{tag}_corner{i}_color.png"), L(f"{tag}_corner{i}_dmg.png")], gap=8))
                cols.append(label(stack_h(cells, gap=10), name + " x4", 34))
            lab = "Corners %d to %d of 24" % (part * 12 + 3 * r + 1, part * 12 + 3 * r + 3)
            sheets.append(label(stack_h(cols, gap=24), lab, 40, bg=(70, 40, 90)))
        stack_v(sheets, gap=30).save(out / ("sheet_1c_corners.png" if part == 0 else "sheet_1c_corners_2.png"))
    # the corners with a compromise (palette or art), x6: before | after, Color over DMG
    cols = []
    for tag, name in (("P", "BEFORE"), ("A", "AFTER")):
        cells = [stack_v([L(f"{tag}_comp{i}_color.png"), L(f"{tag}_comp{i}_dmg.png")], gap=8) for i in range(len(COMPROMISE))]
        rows = [stack_h(cells[:3], gap=10), stack_h(cells[3:], gap=10)]
        cols.append(label(stack_v(rows, gap=14), name + " x6", 34))
    label(stack_h(cols, gap=24), "Compromise corners", 40, bg=(70, 40, 90)).save(out / "sheet_1c_compromise.png")
    # ranges: before | after, Color over DMG
    rows = []
    for i, name in enumerate(("Range B", "Range C")):
        cols = []
        for tag, nm in (("P", "BEFORE"), ("A", "AFTER")):
            cols.append(label(stack_v([L(f"{tag}_range{i}_color.png"), L(f"{tag}_range{i}_dmg.png")], gap=8), nm + " x3", 34))
        rows.append(label(stack_h(cols, gap=24), name if i else "Ranges: A removed, B with peak variants", 40, bg=(70, 40, 90)))
    stack_v(rows, gap=30).save(out / "sheet_1c_ranges.png")


def sheet(out):
    out = Path(out)
    L = lambda f: Image.open(out / f).convert("RGB")
    if (out / "P_corner0_color.png").exists():
        sheet_1c(out)
    # ---- whole map: three renders, x2 each, labelled ----
    ims = [label(L("A_whole_color.png"), "COLOR", 44), label(L("A_whole_dmg.png"), "DMG", 44)]       # DMG is the light water (owner Q101): the dark water is gone from every sheet
    stack_h(ims).save(out / "sheet_whole_map.png")
    stack_h(ims).save(out / "sheet_whole_map_row.png")
    # ---- pieces: row = [approved sheet | integrated close-up], column width 780 each ----
    COLW = 780
    rows = []
    for key, box, appr, text, water in PIECES:
        tag = "C" if key == "town_broken" else "A"
        cols = [label(L(f"{tag}_{key}_color.png"), "COLOR", 30), label(L(f"{tag}_{key}_dmg.png"), "DMG", 30)]
        mine = stack_v(cols) if key == "ranges_ab" else stack_h(cols)
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
