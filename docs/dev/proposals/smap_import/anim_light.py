"""python3 anim_light.py OUTDIR : the water animations on the DMG LIGHT water (owner Q101), checked against the dark water they were typed for.  The approved items (smap_anim/items.py, unchanged) are typed
for the dark water: land 0, foam or glint 1, water 2, rock edge and log wood 3.  The DMG light set has land 0, water 1, glints and foam 0, rock edge 2 (a5art.py, "the same set for DMG light
water"), and the light logs have a body of 0 and an outline of 3.  So the light frames are the same typed frames read through a map of the index: on a water cell 0 -> 0, 1 -> 0, 2 -> 1,
3 -> 2, on a log cell 0 -> 0, 1 -> 0, 2 -> 1, 3 -> 3.  This is a PREVIEW of what the DMG tile bytes would be; stage 2 would type the DMG frame set from it.  Writes, under OUTDIR, one strip per
item (frames at 6 steps of the loop, dark | light, x4) and numbers.json (the lightest-to-water contrast per item, a luminance step in DMG shades 248 168 88 24)."""
import json
import sys
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
ANIM = HERE.parent / "smap_anim"
sys.path.insert(0, str(HERE))
import mapctx  # noqa: E402,F401

sys.path.insert(1, str(ANIM))
text = (ANIM / "items.py").read_text()
DX, DY = mapctx.AT_OVERRIDE["mountain"][0] - 9, mapctx.AT_OVERRIDE["mountain"][1] - 36
for old, new in (("MTN_DX = -3 ", f"MTN_DX = {DX} "),
                 ("a5.tile(14 + MTN_DX, 38)", f"a5.tile(14 + MTN_DX, {38 + DY})"),
                 ("a5.tile(13 + MTN_DX, 38)", f"a5.tile(13 + MTN_DX, {38 + DY})"),
                 ("(14 + MTN_DX, 38)", f"(14 + MTN_DX, {38 + DY})"),
                 ("(13 + MTN_DX, 38)", f"(13 + MTN_DX, {38 + DY})"),
                 ("a5, (16, 262)", f"a5, (16, {262 + 8 * DY})"),
                 ("focus=(76, 300, 100, 316)", f"focus=(76, {300 + 8 * DY}, 100, {316 + 8 * DY})")):
    assert old in text, old
    text = text.replace(old, new)
mod = types.ModuleType("items")
mod.__file__ = str(ANIM / "items.py")
sys.modules["items"] = mod
exec(compile(text, str(ANIM / "items.py"), "exec"), mod.__dict__)

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
import anim_lib as A  # noqa: E402

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
SHADE = [248, 168, 88, 24]
WATER_MAP = [0, 0, 1, 2]
LOG_MAP = [0, 0, 1, 3]
a5 = A.load_a5()
log_cells = set()
for (x, y) in mod.LOGS_H_ALL:
    log_cells |= {(x, y), (x + 1, y)}
for (x, y) in mod.LOGS_V_ALL:
    log_cells |= {(x, y), (x, y + 1)}


FALLS_CELLS = {(46, 5), (47, 5), (46, 6), (47, 6)}              # the falls column itself (the pool below keeps the light map)


def render(item, px, box, light, scale, falls_dark=False):
    x0, y0, x1, y1 = box
    out = np.zeros((y1 - y0, x1 - x0, 3), dtype=np.uint8)
    for Y in range(y0, y1):
        for X in range(x0, x1):
            v = int(px[Y, X])
            cell = (X // 8, Y // 8)
            if light and not (falls_dark and cell in FALLS_CELLS) and item.scene.pal[cell[1]][cell[0]] == "water":
                v = (LOG_MAP if cell in log_cells else WATER_MAP)[v]
            out[Y - y0, X - x0] = SHADE[v]
    return Image.fromarray(out).resize(((x1 - x0) * scale, (y1 - y0) * scale), Image.NEAREST)


font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
numbers = {}
sheets = []
for it in mod.all_items(a5):
    if it.key not in ("01_water", "02_falls", "09_logs"):
        continue
    res = it.resolve()
    L = it.loop_len()
    ts = list(range(0, L, 3))
    box = it.focus
    # frames whose picture differs from the previous one, six of them spread over the loop
    pics = []
    for t in ts:
        px = it.state(t, res)
        pics.append((t, render(it, px, box, True, 1).tobytes()))
    distinct = [t for k, (t, b) in enumerate(pics) if k == 0 or b != pics[k - 1][1]]
    pick = [distinct[int(i * (len(distinct) - 1) / 5)] for i in range(6)] if len(distinct) >= 6 else distinct
    pick = sorted(set(pick))
    scale = 4 if (box[2] - box[0]) <= 64 else 3
    cols = []
    for t in pick:
        px = it.state(t, res)
        d = render(it, px, box, False, scale)
        l = render(it, px, box, True, scale)
        extra = it.key == "02_falls"
        col = Image.new("RGB", (d.width, d.height * (3 if extra else 2) + 16), (30, 30, 30))
        col.paste(d, (0, 0))
        col.paste(l, (0, d.height + 8))
        if extra:
            col.paste(render(it, px, box, True, scale, falls_dark=True), (0, 2 * d.height + 16))
        cols.append(col)
    W = sum(c.width for c in cols) + 10 * (len(cols) - 1)
    strip = Image.new("RGB", (max(W, 1000), cols[0].height + 56), (30, 30, 30))
    ImageDraw.Draw(strip).text((10, 10), "%s  top: dark water as typed   middle: DMG light water%s   frames %s of %d" % (it.key, "   bottom: falls kept as typed" if it.key == "02_falls" else "", pick, L), font=font, fill=(255, 255, 255))
    x = 0
    for c in cols:
        strip.paste(c, (x, 56))
        x += c.width + 10
    strip.save(OUT / f"anim_light_{it.key}.png")
    # numbers: the largest pixel step between a frame and the rest pose on the light render (DMG shades), and the water / glint step
    base = np.asarray(render(it, it.state(0, res), box, True, 1)).astype(int)[..., 0]
    worst = 0
    for t in ts:
        cur = np.asarray(render(it, it.state(t, res), box, True, 1)).astype(int)[..., 0]
        worst = max(worst, int(np.abs(cur - base).max()))
    numbers[it.key] = dict(frames_distinct=len(distinct), loop=L, max_change_from_rest_dmg_light=worst)
json.dump(numbers, open(OUT / "anim_light.json", "w"), indent=1)
print(numbers)
