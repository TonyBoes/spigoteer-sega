#!/usr/bin/env python3
"""The frames of the credits' end and the scene change to the title, as the game plays them (transitions ON).

    python3 tools/dev/credits_end_frames.py ROM cgb|dmg FIRST_FRAME LAST_FRAME OUT.png

The tests' Rom sets HRAM 0xFFF1 bit 7 (TR_OFF), which turns the scene change (the drink, the fade through amber) off: the end is then a cut to the LCD-off white, which
the game never shows. This script clears the bit, runs the roll (credits_shots.start: Color at double speed) and prints the frames where the mean brightness steps by 6
or more; OUT.png is a contact sheet of about sixty frames from FIRST to LAST. Reads the ROM, writes only OUT.png."""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "tools" / "dev"))
from credits_shots import start      # noqa: E402


def main():
    gb = start(sys.argv[1], sys.argv[2])
    gb.pb.memory[0xFFF1] = gb.pb.memory[0xFFF1] & 0x7F          # transitions ON, as the game plays
    a, b = int(sys.argv[3]), int(sys.argv[4])
    fr = []
    for n in range(b):
        gb.pb.tick(1, True)
        if n >= a:
            fr.append((n, np.asarray(gb.pb.screen.image.convert("RGB")).astype(int)))
    last = None
    for n, f in fr:
        m = int(f.mean())
        if last is None or abs(m - last) >= 6:
            u, c = np.unique(f.reshape(-1, 3), axis=0, return_counts=True)
            print(n, "mean", m, "dominant", tuple(int(v) for v in u[c.argmax()]), "colours", len(u))
        last = m
    sel = list(range(0, len(fr), max(1, len(fr) // 60)))[:60]
    cols = 10
    sheet = Image.new("RGB", (cols * 82, ((len(sel) + cols - 1) // cols) * 74), (255, 0, 255))
    d = ImageDraw.Draw(sheet)
    for k, i in enumerate(sel):
        x, y = (k % cols) * 82, (k // cols) * 74
        sheet.paste(Image.fromarray(fr[i][1].astype(np.uint8)).resize((80, 72), Image.NEAREST), (x, y))
        d.text((x + 1, y), str(fr[i][0]), fill=(255, 255, 0))
    sheet.save(sys.argv[5])


if __name__ == "__main__":
    main()
