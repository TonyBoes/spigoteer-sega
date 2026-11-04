"""Frame-by-frame checks of the walk GIFs: smooth scroll, no flashing."""
from pathlib import Path

from PIL import Image, ImageSequence

OUT = Path(__file__).resolve().parents[1]
for m in ("cgb", "dmg"):
    gif = Image.open(OUT / f"walk_{m}.gif")
    frames = [f.convert("L").copy() for f in ImageSequence.Iterator(gif)]
    dur = gif.info.get("duration")
    means = [sum(f.getdata()) / (f.width * f.height) for f in frames]
    d = [abs(a - b) for a, b in zip(means, means[1:])]
    # flashing = whole-frame brightness jumping; WCAG-style: no more than 3 big swings in a second
    big = [i for i, v in enumerate(d) if v > 6]
    # scroll smoothness: how many pixels the picture moves between frames (best horizontal shift 0..8 on the middle band)
    def shift(a, b):
        best, bs = 10 ** 12, 0
        for s in range(-8, 9):
            e = 0
            for y in range(48, 96, 4):
                ra = [a.getpixel((x, y)) for x in range(60, 400, 2)]
                rb = [b.getpixel((x + s, y)) for x in range(60, 400, 2)]
                e += sum(abs(p - q) for p, q in zip(ra, rb))
            if e < best:
                best, bs = e, s
        return bs
    shifts = [shift(a, b) // 3 for a, b in zip(frames[::6], frames[6::6])]
    print(f"{m}: {len(frames)} frames, {dur} ms each = {len(frames) * dur / 1000:.2f} s; mean luminance {min(means):.1f}..{max(means):.1f};"
          f" biggest frame-to-frame change {max(d):.2f} (of 255); frames over 6: {big}; scroll px (sampled, per 6 frames, 1x): {shifts}")
