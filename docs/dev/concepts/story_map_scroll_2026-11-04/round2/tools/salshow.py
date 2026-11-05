"""Preview Sal's poses: python3 salshow.py -> scratch sal_poses.png (x8, Color on top, DMG below)."""
from PIL import Image

from salwalk import POSES

S = "/tmp/claude-1000/-workspace/64761c6b-46f6-4217-a6f1-457b4de3152f/scratchpad/w/"
COL = {'-': (248, 248, 240), '+': (240, 184, 136), '#': (32, 32, 48)}
DMG = {'-': 248, '+': 168, '#': 24}


def sheet(k=8):
    order = [("D", "stand"), ("D", "step1"), ("D", "step2"), ("R", "stand"), ("R", "step1"), ("R", "step2"), ("U", "stand"), ("U", "step1"), ("U", "step2")]
    out = Image.new("RGB", (len(order) * 18 * k, 2 * 26 * k), (96, 128, 96))
    for i, (d, p) in enumerate(order):
        for m in (0, 1):
            for y, r in enumerate(POSES[d][p]):
                for x, c in enumerate(r):
                    if c == '.':
                        continue
                    v = COL[c] if m == 0 else (DMG[c],) * 3
                    for a in range(k):
                        for b in range(k):
                            out.putpixel((i * 18 * k + x * k + a + k, m * 26 * k + y * k + b + k), v)
    return out


if __name__ == "__main__":
    sheet().save(S + "sal_poses.png")
