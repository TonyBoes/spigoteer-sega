"""The owner's contact sheet for reuse.py: the families that could be unified, as they stand now (Color row, DMG row), one panel per family, then tools/dev/contact_sheet.py at x3.
Panels are drawn at 1x with big baked text (about 30 to 40 px tall on the x3 sheet); nothing here edits the map."""
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import reuse as R

ROOT = R.ROOT
W = R.W
NAMES = R.NAMES
PANELS = R.OUT / "reuse_panels"
BG, FG, DIM, TAG = (40, 40, 44), (245, 245, 245), (190, 190, 200), (250, 210, 120)
GAP = 6


def font(size, bold=False):
    for f in (("/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf") if bold else
              ("/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")):
        if Path(f).exists():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def render(e, which, box, scale=1):
    """the whole cells covering the pixel box (x, y, w, h) of Color ('C') or DMG ('D')"""
    x, y, w, h = box
    cx0, cy0, cx1, cy1 = x // 8, y // 8, (x + w - 1) // 8, (y + h - 1) // 8
    im = Image.new("RGB", ((cx1 - cx0 + 1) * 8, (cy1 - cy0 + 1) * 8))
    px = im.load()
    img = e.C if which == "C" else e.D
    for cy in range(cy0, cy1 + 1):
        for cx in range(cx0, cx1 + 1):
            cols = [(v, v, v) for v in W.DMG_SHADE] if which == "D" else [tuple(c) for c in W.RGB[NAMES[e.P[cy, cx]]]]
            for j in range(8):
                for i in range(8):
                    px[(cx - cx0) * 8 + i, (cy - cy0) * 8 + j] = cols[int(img[cy * 8 + j, cx * 8 + i])]
    return im.resize((im.width * scale, im.height * scale), Image.NEAREST) if scale > 1 else im


def row(images):
    h = max(i.height for i in images)
    out = Image.new("RGB", (sum(i.width for i in images) + GAP * (len(images) + 1), h), BG)
    x = GAP
    for im in images:
        out.paste(im, (x, 0))
        x += im.width + GAP
    return out


def panel(title, lines, rows, name):
    ft, fs, fr = font(13, True), font(9), font(10, True)
    wd = max([r.width for r, _ in rows] + [int(ft.getlength(title)) + 4] + [int(fs.getlength(t)) + 4 for t in lines]) + 2 * GAP
    h = 22 + 12 * len(lines) + sum(r.height + 14 for r, _ in rows) + GAP
    out = Image.new("RGB", (wd, h), BG)
    d = ImageDraw.Draw(out)
    d.text((GAP, 2), title, fill=FG, font=ft)
    for i, t in enumerate(lines):
        d.text((GAP, 21 + 12 * i), t, fill=DIM, font=fs)
    y = 22 + 12 * len(lines)
    for r, tag in rows:
        d.text((GAP, y), tag, fill=TAG, font=fr)
        out.paste(r, (0, y + 13))
        y += r.height + 14
    PANELS.mkdir(parents=True, exist_ok=True)
    p = PANELS / (name + ".png")
    out.save(p)
    return p


def pick(inst, n):
    """n instances, different pixel phases (x, y mod 8) first"""
    seen, out = set(), []
    for t in inst:
        ph = (t[0] % 8, t[1] % 8)
        if ph not in seen:
            seen.add(ph)
            out.append(t)
    for t in inst:
        if t not in out:
            out.append(t)
    return out[:n]


def fam_panel(e, name, title, lines, groups, nmax, extra_rows=()):
    rc, rd = [], []
    for inst in groups:
        for (x, y, w, h, p) in pick(inst, nmax):
            rc.append(render(e, "C", (x, y, w, h)))
            rd.append(render(e, "D", (x, y, w, h)))
    rows = [(row(rc), "COLOR"), (row(rd), "DMG")] + list(extra_rows)
    return panel(title, lines, rows, name)


def make(e0, instC, instD, fam, Rj, sim):
    out = []
    sn = Rj["families"]

    def saved(n, k):
        s = sn.get(n, {}).get("snap", {}).get(k)
        return s["color_saved" if k == "C" else "dmg_saved"] if s else 0
    out.append(fam_panel(e0, "1_pine", "1  PINE, %d copies" % len(instC["PINE"]), ["same drawing at %d pixel offsets;" % len(sn["PINE"]["phases_c"]),
                         "one offset saves Color %d, DMG %d tiles" % (saved("PINE", "C"), saved("PINE", "D")), "5 of the copies shown"], [instC["PINE"]], 5))
    out.append(fam_panel(e0, "2_round", "2  ROUND TREE, BUSH", ["tree x%d at %d offsets, bush x%d (the tree's crown)" % (len(instC["ROUND"]), len(sn["ROUND"]["phases_c"]), len(instC["BUSH"])),
                         "one offset saves Color %d, DMG %d tiles" % (saved("ROUND", "C"), saved("ROUND", "D"))], [instC["ROUND"], instC["BUSH"]], 3))
    out.append(fam_panel(e0, "3_spruce", "3  PINE and SNOW SPRUCE", ["two drawings of a conifer (16x18, 16x13)", "pine in the spruce's place: no gain, window 174 to 180"],
                         [instC["PINE"][:1], instC["SPRUCE"]], 3))
    rk = pick(instC["ROCK"], 4)
    out.append(fam_panel(e0, "4_peaks", "4  PEAKS and ROCKS", ["peaks: snow and desert share the same tiles, only the palette differs", "rocks x%d: grass and sand share the same tiles" % len(instC["ROCK"]), "nothing to save in either"],
                         [instC["PEAK_A"][:1], instC["PEAK_B"], instC["PEAK_C"], instC["PEAK_D"]], 1,
                         extra_rows=[(row([render(e0, "C", (x, y, w, h)) for x, y, w, h, p in rk]), "COLOR rocks"), (row([render(e0, "D", (x, y, w, h)) for x, y, w, h, p in rk]), "DMG rocks")]))
    # 5 cactus, now and on the grass palette
    cacti = [t for n in ("CACTUS_S", "CACTUS_S2", "CACTUS_B", "CACTUS_Q") for t in instC[n][:1]]
    ai, bi = NAMES.index("cactus"), NAMES.index("grass")
    em = R.merge_edit(e0, ai, bi, R.palette_distance(ai, bi)[1])
    out.append(panel("5  CACTUS palette", ["9 cells have a palette of their own", "dropping it frees 157 of 397 eight-palette windows"],
                     [(row([render(e0, "C", (x, y, w, h)) for x, y, w, h, p in cacti]), "COLOR now"), (row([render(em, "C", (x, y, w, h)) for x, y, w, h, p in cacti]), "COLOR on grass palette"),
                      (row([render(e0, "D", (x, y, w, h)) for x, y, w, h, p in cacti]), "DMG")], "5_cactus"))
    fi, gi = NAMES.index("factory"), NAMES.index("grass")
    ef = R.merge_edit(e0, fi, gi, R.palette_distance(fi, gi)[1])
    fx, fy = W.VENUES["factory"][1]
    box = (fx * 8, fy * 8, 80, 56)
    out.append(panel("6  FACTORY palette", ["77 cells; merging it into grass clears the east bend's", "8-palette windows (82 of 82) but recolours the yard"],
                     [(row([render(e0, "C", box), render(ef, "C", box)]), "COLOR now, then on the grass palette")], "6_factory"))
    # 7 near twins and 8 stray pixels, DMG, tiles at x2
    def tiles(groups, n):
        imgs = []
        for g in groups[:n]:
            cs = g[2]
            imgs.append(row([render(e0, "D", (c[0][0] * 8, c[0][1] * 8, 8, 8), 2) for c in cs[:5]]))
        return imgs
    ed, grd, cd, pd_ = R.near_simulate(e0, "D", 4, False)
    flat = bytes(64)
    pairs = sorted((g for g in grd if g[0] != flat and sum(1 for v in g[0] if v) >= 20), key=lambda g: -len(g[1]))
    rows7 = []
    for g in pairs[:4]:
        ims = [render(e0, "D", (c[0][0] * 8, c[0][1] * 8, 8, 8), 2) for c in g[2][:5]]
        rows7.append((row(ims), "base + %s px different" % ", ".join(str(v) for v in g[3][:4])))
    out.append(panel("7  NEAR TWINS (DMG)", ["tiles that differ by 1 to 4 pixels", "each row: the tile kept, then its twins"], rows7, "7_twins"))
    ed2, grd2, _, _ = R.near_simulate(e0, "D", 2, False, centre=flat)
    st = [g for g in grd2 if g[0] == flat]
    ims = []
    if st:
        for mem, cells in list(zip(st[0][1], st[0][2][1:]))[:9]:
            cx, cy = cells[0]
            ims.append(render(e0, "D", (cx * 8, cy * 8, 8, 8), 2))
    out.append(panel("8  STRAY PIXELS (DMG)", ["%d tiles hold 1 to 2 stray pixels on flat ground" % (len(st[0][1]) if st else 0), "mostly the dots that round road bends and cut tree tips;", "folding them into the flat tile removes those dots"],
                     [(row(ims), "the tiles (x2)")], "8_stray"))
    cmd = [sys.executable, str(ROOT / "tools" / "dev" / "contact_sheet.py"), str(R.OUT / "reuse_sheet.png"), "--scale", "3", "--cols", "2", "--title", "Story map: shapes that repeat"]
    cmd += [" =%s" % p for p in out]
    subprocess.run(cmd, check=True)
    print("sheet", R.OUT / "reuse_sheet.png")
