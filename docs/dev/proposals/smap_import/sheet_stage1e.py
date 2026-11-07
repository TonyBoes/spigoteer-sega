"""python3 sheet_stage1e.py SRCDIR OUTDIR : the stage 1e sheets from the x3 crops v_zt.py / v_des.py wrote (SRCDIR = out/smap_import).  Each sheet is rows of 'before | after' pairs,
Color pair on the left half... one row per area, Color row then DMG row.  Big labels."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

SRC, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
try:
    FONT = ImageFont.truetype("/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf", 26)
except OSError:
    FONT = ImageFont.load_default()
BG = (30, 30, 34)


def pair_sheet(name, areas, left="BEFORE", right="AFTER"):
    """areas: list of (title, file_a, file_b) with {k} replaced by c / d"""
    blocks = []
    for title, fa, fb in areas:
        for k, kn in (("c", "COLOR"), ("d", "DMG")):
            pa, pb = SRC / fa.format(k=k), SRC / fb.format(k=k)
            if pa.exists() and pb.exists():
                blocks.append(("%s  %s   %s | %s" % (title, kn, left, right), Image.open(pa).convert("RGB"), Image.open(pb).convert("RGB")))
    if not blocks:
        return
    w = max(a.width + b.width + 16 for _, a, b in blocks) + 32
    h = sum(max(a.height, b.height) + 48 for _, a, b in blocks) + 16
    out = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(out)
    y = 12
    for label, a, b in blocks:
        d.text((16, y), label, fill=(255, 255, 255), font=FONT)
        out.paste(a, (16, y + 40))
        out.paste(b, (16 + a.width + 16, y + 40))
        y += max(a.height, b.height) + 48
    out.save(OUT / name)


pair_sheet("s1e_trees.png", [("trees east pines", "zt_t1b_{k}.png", "zt_t1a_{k}.png"), ("trees lawn round", "zt_t2b_{k}.png", "zt_t2a_{k}.png"),
                              ("trees north pines", "zt_t3b_{k}.png", "zt_t3a_{k}.png")])
pair_sheet("s1e_zoo.png", [("zoo and teahouse", "zt_zb_{k}.png", "zt_za_{k}.png")])
pair_sheet("s1e_desert.png", [("desert", "des_before_{k}.png", "des_after_{k}.png")])
pair_sheet("s1e_bigmountain.png", [("big mountain", "zt_bigA_{k}.png", "zt_bigB_{k}.png")], left="A", right="B")


def whole(name, tag, title):
    a, b = SRC / "cc" / f"{tag}_whole_color.png", SRC / "cc" / f"{tag}_whole_dmg.png"
    if not (a.exists() and b.exists()):
        return
    A, B = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    out = Image.new("RGB", (A.width + B.width + 48, A.height + 56), BG)
    d = ImageDraw.Draw(out)
    d.text((16, 10), title + "   COLOR | DMG (light water)", fill=(255, 255, 255), font=FONT)
    out.paste(A, (16, 48))
    out.paste(B, (32 + A.width, 48))
    out.save(OUT / name)


whole("s1e_whole_c40_A.png", "c40A", "everything on, bends r40 with fallback, big mountain A")
whole("s1e_whole_c40_B.png", "c40B", "everything on, bends r40 with fallback, big mountain B")
whole("s1e_whole_s32_A.png", "s32A", "everything on, four long bends at r32, mountain A (generator passes)")
whole("s1e_whole_Ap.png", "Ap", "A': four long bends r32, all others r24 with trims, all extras, mountain A")
whole("s1e_whole_Cp.png", "Cp", "C': (0,45) r96, three long r40, others r24 with trims, bamboo, cacti, spill, A")
whole("s1e_whole_Cp_pine.png", "Cp_pine", "C' plus the pine clusters")


def trims(name):
    rows = []
    for k, note in (("lodge", "lodge"), ("cow", "cow fence")):
        for cgb, kn in (("color", "COLOR"), ("dmg", "DMG")):
            a, b = SRC / "cc" / f"before_{k}_{cgb}.png", SRC / "cc" / f"after_{k}_{cgb}.png"
            if a.exists() and b.exists():
                rows.append(("%s  %s  r8 | r24 trim" % (note, kn), Image.open(a).convert("RGB"), Image.open(b).convert("RGB")))
    w = max(a.width + b.width + 16 for _, a, b in rows) + 32
    h = sum(max(a.height, b.height) + 48 for _, a, b in rows) + 16
    out = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(out)
    y = 12
    for label, a, b in rows:
        d.text((16, y), label, fill=(255, 255, 255), font=FONT)
        out.paste(a, (16, y + 40))
        out.paste(b, (16 + a.width + 16, y + 40))
        y += max(a.height, b.height) + 48
    out.save(OUT / name)


trims("s1e_trims.png")
