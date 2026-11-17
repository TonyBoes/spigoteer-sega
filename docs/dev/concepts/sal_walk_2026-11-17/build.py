#!/usr/bin/env python3
"""Sal's walk proposals: splice the hand-typed arm strips of arms.txt into the owner's bartender.txt frames, write the proposal
frame files, x8 stills with the changed pixels marked, and the walking GIFs beside Dregs. It only converts and previews: every
pixel of the arms is typed in arms.txt. Run from the repo root:  python3 docs/dev/concepts/sal_walk_2026-11-17/build.py"""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent


def frames(path):
    out, cur = [], None
    for line in path.read_text().split("\n"):
        if line.startswith(";"):
            continue
        if not line.strip():
            if cur:
                out.append(cur); cur = None
            continue
        (cur := cur or []).append(line)
    if cur:
        out.append(cur)
    return out


def strips(path):
    d, cur = {}, None
    for line in path.read_text().split("\n"):
        if line.startswith("@"):
            cur = d.setdefault(line[1:].strip(), [])
        elif cur is not None and line.strip() and not line.startswith(";"):
            cur.append(line.split())
    return d


sal = frames(ROOT / "assets/art/bartender.txt")          # idle, walk1, walk2, fill, fail
dregs = frames(ROOT / "assets/art/dregs/dregs.txt")
S = strips(OUT / "arms.txt")


def splice(frame, st):
    f = [list(r) for r in frame]
    assert len(st) == 9
    for i, (l, r) in enumerate(st):
        assert len(l) == 4 and len(r) == 4, (i, l, r)
        f[10 + i][0:4] = l
        f[10 + i][12:16] = r
    return ["".join(r) for r in f]


PROPS = {}
for p in ("P1", "P2", "P3", "P4", "P5"):
    PROPS[p] = [sal[0], splice(sal[1], S[p + "_walk1"]), splice(sal[2], S[p + "_walk2"]), sal[3], sal[4]]
    # sanity: nothing but x 0-3 / 12-15 of rows 10-18 may differ from the owner's frames
    for k in (1, 2):
        for y in range(24):
            for x in range(16):
                if PROPS[p][k][y][x] != sal[k][y][x]:
                    assert 10 <= y <= 18 and (x < 4 or x >= 12), (p, k, x, y)
    txt = ["; Sal's walk, proposal %s: the owner's bartender.txt with arms.txt's strips in walk1 / walk2 (NOT imported)" % p]
    for f in PROPS[p]:
        txt += f + [""]
    (OUT / f"bartender_{p}.txt").write_text("\n".join(txt))

# palettes. Sal: index 1 cream, 2 skin, 3 ink (assets/palettes.json "bartender"). Dregs (src/po.c dregs_pal): skin, grey, ink.
SAL_C = {"-": (248, 248, 240), "+": (240, 184, 136), "#": (32, 32, 48)}
DREGS_C = {"-": (240, 216, 160), "+": (176, 160, 184), "#": (32, 24, 40)}
DMG = {"-": (200, 200, 200), "+": (110, 110, 110), "#": (10, 10, 10)}   # OBP 0xE4: shade 1 light, 2 dark, 3 black
BGC = {"C": (48, 56, 72), "D": (232, 232, 232)}                     # Color backdrop / DMG backdrop (a plain wall)


def draw(frame, pal, scale, bg, marks=None):
    h, w = len(frame), len(frame[0])
    im = Image.new("RGB", (w * scale, h * scale), bg)
    d = ImageDraw.Draw(im)
    for y, r in enumerate(frame):
        for x, c in enumerate(r):
            if c in pal:
                d.rectangle([x * scale, y * scale, (x + 1) * scale - 1, (y + 1) * scale - 1], fill=pal[c])
    if marks:
        for (x, y) in marks:
            d.rectangle([x * scale, y * scale, (x + 1) * scale - 1, (y + 1) * scale - 1], outline=(255, 0, 255), width=max(1, scale // 8))
    return im


def changed(a, b):
    return [(x, y) for y in range(len(a)) for x in range(len(a[0])) if a[y][x] != b[y][x]]


# x8 stills: current | proposal with the changed pixels marked, for walk1 and walk2, both proposals, DMG and Color.
CELL = 16 * 8
tiles = []
rows = []
for p in ("P1", "P2", "P3", "P4", "P5"):
    for k, name in ((1, "walk1"), (2, "walk2")):
        for model, pal, bg in (("DMG", DMG, BGC["D"]), ("Color", SAL_C, BGC["C"])):
            rows.append((p, name, model, draw(sal[k], pal, 8, bg), draw(PROPS[p][k], pal, 8, bg, changed(sal[k], PROPS[p][k]))))
            n = len(changed(sal[k], PROPS[p][k]))
            print(f"{p} {name}: {n} pixels changed")
from PIL import ImageFont
font = ImageFont.load_default()
for p in ("P1", "P2", "P3", "P4", "P5"):
    rs = [r for r in rows if r[0] == p]
    W = CELL * 2 + 40 + 120
    H = (24 * 8 + 22) * len(rs) + 8
    sheet = Image.new("RGB", (W, H), (40, 40, 40))
    sd = ImageDraw.Draw(sheet)
    y = 4
    for (_, name, model, a, b) in rs:
        sd.text((10, y), f"{name} {model}: owner now | {p} (changed boxed)", fill=(235, 235, 235), font=font)
        sheet.paste(a, (10, y + 14)); sheet.paste(b, (30 + CELL, y + 14))
        y += 24 * 8 + 22
    sheet.save(OUT / f"sal_walk_{p}_stills_x8.png")

# GIFs at x6: [Sal now | Sal proposal | Dregs] on a DMG row and a Color row; the cycle is the game's walk1, idle, walk2, idle, 10 frames each.
CYC = [1, 0, 2, 0]
SC = 6
for p in ("P1", "P2", "P3", "P4", "P5"):
    gifs = []
    for ph in CYC:
        panels = [(sal[ph], DMG, SAL_C)] + ([(PROPS["P4"][ph], DMG, SAL_C)] if p == "P5" else []) + [(PROPS[p][ph], DMG, SAL_C), (dregs[ph], DMG, DREGS_C)]
        W = len(panels) * (16 * SC + 12) + 12
        H = 2 * (24 * SC + 12) + 12
        im = Image.new("RGB", (W, H), (40, 40, 40))
        for ri, (bg_d, bg_c) in enumerate(((BGC["D"], DMG), (BGC["C"], None))):
            for ci, (fr, pal_dmg, pal_col) in enumerate(panels):
                pal = pal_dmg if ri == 0 else pal_col
                bg = BGC["D"] if ri == 0 else BGC["C"]
                im.paste(draw(fr, pal, SC, bg), (12 + ci * (16 * SC + 12), 12 + ri * (24 * SC + 12)))
        gifs.append(im)
    # one shared palette so no colour jumps between frames (no flashing)
    base = gifs[0].quantize(colors=64, method=Image.Quantize.MEDIANCUT)
    fr = [g.quantize(palette=base, dither=Image.Dither.NONE) for g in gifs]
    fr[0].save(OUT / f"sal_walk_{p}.gif", save_all=True, append_images=fr[1:], duration=170, loop=0, disposal=1)
print("done")
