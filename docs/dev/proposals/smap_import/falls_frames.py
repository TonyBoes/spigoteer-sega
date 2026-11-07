"""python3 falls_frames.py OUTDIR : the falls coming out of mountain B (falls_cave.py) beside the APPROVED falls (smap_anim 02_falls), x6, Color above DMG (light water), as a strip
(falls_strip.png, falls steps 0..3) and a GIF (falls_anim.gif, 50 ms a picture, the whole 180-frame loop of the approved items: falls 4 steps of 9 video frames, the foam lip churn 6 frames
after each step, the pool glints on their 30-frame pace).  Left: the falls out of the cave (the column below the mouth is the approved art: streaks, foot rows, churning foam lip, glints).
Right: the approved falls as typed, on a plain bank (its top 4 rows are hidden in the cave on the left).  DMG: the approved typed frames read through falls_cave.LIGHT (foam and land 0, water 1):
streaks, lip and glints are light on the water's mid grey.  Run with SMAP_BIG=B."""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mapctx as M  # noqa: E402
import falls_cave as FC  # noqa: E402

I = FC._items
out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
BOX = (44, 4, 51, 9)                                           # cells 44..50, rows 4..8
S = 6
try:
    font = ImageFont.truetype("/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf", 22)
except OSError:
    font = ImageFont.load_default()
WORLDS = (M.W.WORLD, M.W.WORLD_DMG)
CELLS = [(cx, cy) for cy in range(BOX[1], BOX[3]) for cx in range(BOX[0], BOX[2])]


def put(cx, cy, tile):
    """tile: 8 strings of approved typed indices -> both worlds (DMG through LIGHT)"""
    for w in WORLDS:
        for j, r in enumerate(tile):
            for i, c in enumerate(r):
                v = {".": 0, "-": 1, "+": 2}.get(c, None)
                v = int(c) if v is None else v
                w.px[cy * 8 + j][cx * 8 + i] = FC.to_dmg(v, cx, cy, i) if w is WORLDS[1] else v


def lower(t):
    """the cells of rows 6..8 at video frame t: approved falls streaks + foot rows, lip churn, glints"""
    k = (t // 9) % 4
    for side, cx in (("L", 46), ("R", 47)):
        put(cx, 6, FC.fall_rows(side, k)[8:])
        g = (I.GSEQ_L if side == "L" else I.GSEQ_R)[((t + I.FOOT_PH[0 if side == "L" else 1]) // 30) % 6]
        put(cx, 7, I.foot_tile(side, ((t - I.LIP_PH) // 9) % 4, g))
    w = I.WS["vsubtle"]
    put(46, 8, w["A"][[0, 0, 1, 0, 0, 2][(t // 30) % 6]])
    put(47, 8, w["B"][[0, 0, 2, 0, 0, 1][((t + 15) // 30) % 6]])


def cave_state(t):
    k = (t // 9) % 4
    for w in WORLDS:
        for (x, y), v in FC.cell_pixels(k).items():
            if FC.FLOW_X0 <= x < FC.FLOW_X0 + 8 and FC.FLOW_Y0 <= y < FC.FLOW_Y0 + 4:
                w.px[y][x] = v                                # the flow window only: the rest of the ledge is the same on every frame
    lower(t)


def ref_state(t):
    pal = M.W.WORLD.pal[6][44]
    palw = M.W.WORLD.pal[6][46]
    for (cx, cy) in CELLS:
        if cy <= 5:
            for w in WORLDS:
                w.pal[cy][cx] = pal
                for j in range(8):
                    for i in range(8):
                        w.px[cy * 8 + j][cx * 8 + i] = 0
    k = (t // 9) % 4
    for side, cx in (("L", 46), ("R", 47)):
        put(cx, 5, FC.fall_rows(side, k)[:8])
        for w in WORLDS:
            w.pal[5][cx] = palw
    lower(t)


def snapshot():
    return [({(x, y): w.px[y][x] for (cx, cy) in CELLS for y in range(cy * 8, cy * 8 + 8) for x in range(cx * 8, cx * 8 + 8)}, {c: w.pal[c[1]][c[0]] for c in CELLS}) for w in WORLDS]


def restore(sn):
    for w, (px, pl) in zip(WORLDS, sn):
        for (x, y), v in px.items():
            w.px[y][x] = v
        for (cx, cy), p in pl.items():
            w.pal[cy][cx] = p


def pics(t):
    """(cave color, cave dmg, approved color, approved dmg) at video frame t"""
    sn = snapshot()
    cave_state(t)
    a = (M.render(True, BOX, S).convert("RGB"), M.render(False, BOX, S).convert("RGB"))
    restore(sn)
    ref_state(t)
    b = (M.render(True, BOX, S).convert("RGB"), M.render(False, BOX, S).convert("RGB"))
    restore(sn)
    return a + b


# strip: falls steps 0..3 (video frames 9k + 6: the lip has just stepped too)
cols = [pics(9 * k + 6) for k in range(4)]
w, h = cols[0][0].size
G = 10
strip = Image.new("RGB", (4 * (w + G) + G, 4 * (h + G) + 90), (30, 30, 34))
d = ImageDraw.Draw(strip)
d.text((G, 6), "falls out of the mountain (top two rows) and the approved falls 02_falls (bottom two rows), falls steps 0..3, x6", fill=(255, 255, 255), font=font)
d.text((G, 38), "rows: cave Color, cave DMG light water, approved Color, approved DMG light water", fill=(200, 200, 200), font=font)
for k, c in enumerate(cols):
    for r in range(4):
        strip.paste(c[r], (G + k * (w + G), 74 + r * (h + G)))
strip.save(out / "falls_strip.png")

# GIF: the 180-frame loop, 50 ms a picture; left cave, right approved, Color above DMG
gif = []
for t in range(0, 180, 3):
    a, b, c, e = pics(t)
    im = Image.new("RGB", (2 * w + G, 2 * h + G), (30, 30, 34))
    im.paste(a, (0, 0))
    im.paste(b, (0, h + G))
    im.paste(c, (w + G, 0))
    im.paste(e, (w + G, h + G))
    gif.append(im.convert("P", palette=Image.ADAPTIVE))
gif[0].save(out / "falls_anim.gif", save_all=True, append_images=gif[1:], duration=50, loop=0)
print("strip", strip.size, "gif frames", len(gif), "size", gif[0].size)
