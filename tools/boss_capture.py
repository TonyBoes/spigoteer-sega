#!/usr/bin/env python3
"""Frames of the AUTO_BOSS ROM (src/debug.c auto_boss) around Last call turning into Big Tex's fight, on SameBoy.

gbcheck / sameboy_tester save only the last frame of a whole-second run. The AUTO_BOSS ROM reads a start delay (frames) from the free ROM0 byte
0x3FFF (0xFF: none), so a run of S seconds with delay d shows the game frame S * 59.7 - d frames after the start: patching the byte and running
again walks through the entrance one frame at a time. This script does that for a range of delays and lengths, on DMG and CGB, in parallel.

    make BUILD=out/cap/b0 DEBUGFLAGS="-DDEBUG_MENU -DAUTO_BOSS=1"
    tools/boss_capture.py out/cap/b0/game.gb out/cap/frames --secs 6 7 8 9 --delays 0 2 4 ... 58 [--sheet]

Writes <out>/<model>_s<secs>_d<delay>.png (x1) and, with --sheet, <out>/<model>_sheet_s<secs>.png: those frames side by side in order of delay.
"""
import argparse
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw


def one(rom_bytes, model, secs, delay, out):
    with tempfile.TemporaryDirectory() as td:
        rom = Path(td) / "r.gb"
        b = bytearray(rom_bytes)
        b[0x3FFF] = delay if delay else 0xFF
        rom.write_bytes(b)
        subprocess.run(["sameboy_tester", f"--{model}", "--length", str(secs), str(rom)], capture_output=True, timeout=600)
        bmp = rom.with_suffix(".bmp")
        png = out / f"{model}_s{secs}_d{delay:02d}.png"
        Image.open(bmp).convert("RGB").save(png)
        return png


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rom")
    ap.add_argument("out")
    ap.add_argument("--secs", type=int, nargs="+", default=[8, 9])
    ap.add_argument("--delays", type=int, nargs="+", default=list(range(0, 60, 4)))
    ap.add_argument("--models", default="dmg,cgb")
    ap.add_argument("--sheet", action="store_true")
    ap.add_argument("--jobs", type=int, default=6)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    data = Path(a.rom).read_bytes()
    jobs = [(m, s, d) for m in a.models.split(",") for s in a.secs for d in a.delays]
    with ThreadPoolExecutor(a.jobs) as ex:
        res = list(ex.map(lambda j: (j, one(data, j[0], j[1], j[2], out)), jobs))
    if a.sheet:
        for m in a.models.split(","):
            for s in a.secs:
                ims = [(d, Image.open(p)) for (mm, ss, d), p in res if mm == m and ss == s]
                ims.sort(key=lambda t: t[0])
                cols = 6
                rows = (len(ims) + cols - 1) // cols
                sheet = Image.new("RGB", (cols * 164, rows * 148), (40, 40, 40))
                for i, (d, im) in enumerate(ims):
                    x, y = (i % cols) * 164, (i // cols) * 148
                    sheet.paste(im, (x + 2, y + 2))
                    ImageDraw.Draw(sheet).text((x + 4, y + 4), f"d{d}", fill=(255, 0, 255))
                sheet.save(out / f"{m}_sheet_s{s}.png")
    print(f"{len(res)} frames in {out}")


if __name__ == "__main__":
    sys.exit(main())
