"""python3 falls_frames.py OUTDIR : the four animation frames of the falls coming out of mountain B (falls_cave.py), x6, Color above DMG (light water), as a strip (falls_strip.png) and a GIF
(falls_anim.gif, 150 ms a step: the approved 9-frame step).  Only the falls cells change between frames: the two row-5 cells (rock, mouth and flow: falls_cave.cell_pixels(k)) and the two row-6
cells (the approved falls rows 8..15 on frame k, unchanged art).  The DMG preview reads the typed frame through the light map (land 0, foam 0, water 1) for the row-6 cells; the row-5 cells are
already in the light indices (igloo palette on both machines).  Run with SMAP_BIG=B."""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mapctx as M  # noqa: E402
import falls_cave as FC  # noqa: E402

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
BOX = (44, 3, 51, 9)                                           # cells 44..50, rows 3..8
S = 6
LIGHT = {0: 0, 1: 0, 2: 1}                                     # approved typed index -> DMG light water index (anim_light.py: foam to 0, water to 1)
try:
    font = ImageFont.truetype("/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf", 26)
except OSError:
    font = ImageFont.load_default()


def set_frame(k):
    px = FC.cell_pixels(k)
    for w in (M.W.WORLD, M.W.WORLD_DMG):
        for (x, y), v in px.items():
            if FC.FLOW_X0 <= x < FC.FLOW_X0 + 8 and FC.FLOW_Y0 <= y < FC.FLOW_Y0 + 4:
                w.px[y][x] = v                                # the flow window only: the rest of the ledge is the same on every frame
    for side, cx in (("L", 46), ("R", 47)):
        rows = FC.fall_rows(side, k)[8:16]
        for j, r in enumerate(rows):
            for i, c in enumerate(r):
                v = {".": 0, "-": 1, "+": 2}[c]
                M.W.WORLD.px[48 + j][cx * 8 + i] = v
                M.W.WORLD_DMG.px[48 + j][cx * 8 + i] = LIGHT[v]


frames = []
for k in range(FC.FALL_FRAMES):
    set_frame(k)
    frames.append((M.render(True, BOX, S).convert("RGB"), M.render(False, BOX, S).convert("RGB")))
w, h = frames[0][0].size
strip = Image.new("RGB", (len(frames) * (w + 12) + 12, 2 * h + 110), (30, 30, 34))
d = ImageDraw.Draw(strip)
d.text((12, 8), "falls out of the mountain, frames 0..3 (150 ms a step), x6: Color above, DMG below", fill=(255, 255, 255), font=font)
for k, (a, b) in enumerate(frames):
    x = 12 + k * (w + 12)
    d.text((x, 44), "frame %d" % k, fill=(255, 255, 255), font=font)
    strip.paste(a, (x, 80))
    strip.paste(b, (x, 90 + h))
strip.save(out / "falls_strip.png")
gif = []
for a, b in frames:
    im = Image.new("RGB", (w, 2 * h + 6), (30, 30, 34))
    im.paste(a, (0, 0))
    im.paste(b, (0, h + 6))
    gif.append(im.convert("P", palette=Image.ADAPTIVE))
gif[0].save(out / "falls_anim.gif", save_all=True, append_images=gif[1:], duration=150, loop=0)
print("frames", len(frames), "size", strip.size)
