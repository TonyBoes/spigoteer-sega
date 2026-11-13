"""x6 DMG renders of every boss's whole figure (topper + body) into out/rush_prev/full_<name>.png, with the 16 rows the list shows boxed."""
from pathlib import Path
from PIL import Image, ImageDraw
import rp_common as c

build = Path(c.ROOT / "build")
out = Path(c.ROOT / "out" / "rush_prev")
out.mkdir(parents=True, exist_ok=True)
S = 6
for n in c.BOSSES:
    rows, pal = c.full_boss(build, n)
    w = len(rows[0])
    im = Image.new("RGB", (w * S, 24 * S), c.DMG[0])
    d = ImageDraw.Draw(im)
    for y, r in enumerate(rows):
        for x, v in enumerate(r):
            d.rectangle([x * S, y * S, x * S + S - 1, y * S + S - 1], fill=c.DMG[v])
    d.line([0, 8 * S, w * S, 8 * S], fill=(255, 0, 0))
    im.save(out / f"full_{n}.png")
print("ok")
