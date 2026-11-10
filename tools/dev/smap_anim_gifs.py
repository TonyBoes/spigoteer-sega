#!/usr/bin/env python3
"""Maintainer tool: the story map's tile animations from the REAL ROM (build/game.gb), one GIF per item, DMG left and Color right, plus the stills of a contact sheet.

    python3 tools/dev/smap_anim_gifs.py [OUTDIR]          # default out/smap_anim/

For every item: the ROM is put on the map at the stop that shows it (progress 10, the fountain working), left to settle, and 256 frames (the animation loop, V_TICK) are read from the
screen, cropped to the item (world pixel box, followed through the camera) and saved as <item>.gif (x4, every second frame, 33 ms: the loop closes) and as stills <item>.<model>.<k>.png
(x1, four evenly spaced frames).  Prints the flicker numbers: the share of the crop's pixels that change between two frames, and the largest step in a pixel's brightness (0..255) at the DMG's shades.
Color runs at double speed as shipped.  Nothing here is a test.
"""
import contextlib
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))
import test_story_map as sm  # noqa: E402
from conftest import double_speed  # noqa: E402
from test_story_map_world import SV, V_CAMX, V_CAMY, var  # noqa: E402

# key, label, stop, world pixel box (x0, y0, x1, y1)
ITEMS = [
    ("01_water", "01 water glints", 3, (360, 56, 392, 88)),
    ("02_falls", "02 falls, foam lip, cascade", 3, (352, 16, 392, 80)),
    ("03_fountain", "03 fountain", 10, (208, 176, 256, 216)),
    ("04a_bunting", "04a bunting", 10, (192, 152, 264, 176)),
    ("04b_stadium_flag", "04b stadium flag", 1, (40, 0, 88, 32)),
    ("05_airbase", "05 radar dish and mast lamp", 9, (48, 272, 104, 312)),
    ("06a_smoke_lodge", "06a lodge smoke", 4, (448, 136, 496, 176)),
    ("06b_smoke_factory", "06b factory smoke", 5, (408, 288, 504, 320)),
    ("06c_smoke_igloo", "06c igloo smoke", 3, (432, 24, 480, 64)),
    ("07_cow_tail", "07 cow tails", 6, (424, 398, 488, 424)),
    ("09_logs", "09 logs", 4, (352, 150, 392, 256)),
    ("10_runway_lights", "10 runway lights", 9, (64, 320, 160, 352)),
]
SCALE = 4
LUM = (0.299, 0.587, 0.114)


def capture(model, stop, box):
    ctx = double_speed() if model == "cgb" else contextlib.nullcontext()
    with ctx:
        gb = sm.to_map(model, 10, stop=stop)
    gb.run(80)
    frames = []
    for _ in range(256):
        gb.run(1, True)
        sc = gb.read("story_scratch", 520)
        cx, cy = var(sc, V_CAMX), var(sc, V_CAMY)
        x0, y0, x1, y1 = box[0] - cx, box[1] - cy, box[2] - cx, box[3] - cy
        im = gb.image().convert("RGB")
        assert 0 <= x0 and 0 <= y0 and x1 <= 160 and y1 <= 144, (stop, box, (cx, cy), "the box is not on the screen")
        frames.append(im.crop((x0, y0, x1, y1)))
    return frames


def flicker(frames):
    a = [np.asarray(f).astype(float) for f in frames]
    worst_share, worst_step = 0.0, 0.0
    for i in range(len(a)):
        d = a[(i + 1) % len(a)] - a[i]
        ch = np.any(d != 0, axis=2)
        worst_share = max(worst_share, float(ch.mean()))
        worst_step = max(worst_step, float(np.abs(d @ np.array(LUM)).max()))
    return worst_share, worst_step


def main(out):
    out.mkdir(parents=True, exist_ok=True)
    print(f"{'item':22} {'model':5} {'changed px / frame (max)':>26} {'biggest brightness step':>24}")
    for key, label, stop, box in ITEMS:
        sets = {m: capture(m, stop, box) for m in ("dmg", "cgb")}
        for m, fr in sets.items():
            share, step = flicker(fr)
            print(f"{key:22} {m:5} {share * 100:25.1f}% {step:24.0f}")
            for k in range(4):
                fr[k * 64].save(out / f"{key}.{m}.{k}.png")
        w, h = sets["dmg"][0].size
        ims = []
        for i in range(0, 256, 2):
            sheet = Image.new("RGB", (w * SCALE * 2 + 8, h * SCALE), (40, 40, 40))
            sheet.paste(sets["dmg"][i].resize((w * SCALE, h * SCALE), Image.NEAREST), (0, 0))
            sheet.paste(sets["cgb"][i].resize((w * SCALE, h * SCALE), Image.NEAREST), (w * SCALE + 8, 0))
            ims.append(sheet)
        ims[0].save(out / f"{key}.gif", save_all=True, append_images=ims[1:], duration=33, loop=0, disposal=1)
    print("written to", out)


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "out" / "smap_anim")
