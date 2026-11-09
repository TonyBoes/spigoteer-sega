"""The road's palettes (Color): every road cell tinted by the palette it uses, with a legend.  python3 tools/artifacts/map_atlas/road_palettes.py OUT.png"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import static as S

st = S.Static()
CW, CH = S.CW, S.CH
road = st.piece == st.piece_names.index("Roads")
TINT = {"town1": (230, 40, 40), "town1@g": (40, 200, 60), "town1@n": (60, 160, 255), "town1@z": (255, 0, 255)}
base = Image.open(sys.argv[2] if len(sys.argv) > 2 else "out/map_atlas/img/map_color.png").convert("RGB").resize((CW * 16, CH * 16), Image.NEAREST)
a = np.array(base).astype(float)
cnt = {}
for y in range(CH):
    for x in range(CW):
        if not road[y, x]:
            a[y * 16:(y + 1) * 16, x * 16:(x + 1) * 16] = a[y * 16:(y + 1) * 16, x * 16:(x + 1) * 16] * 0.35 + 30
            continue
        n = st.names[st.pal[y, x]]
        cnt[n] = cnt.get(n, 0) + 1
        t = TINT.get(n)
        if t:
            blk = a[y * 16:(y + 1) * 16, x * 16:(x + 1) * 16]
            blk[:2, :] = t; blk[-2:, :] = t; blk[:, :2] = t; blk[:, -2:] = t
im = Image.fromarray(a.clip(0, 255).astype(np.uint8))
F = lambda n: ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", n)
leg = Image.new("RGB", (im.width, 380), (30, 30, 34))
d = ImageDraw.Draw(leg)
d.text((20, 15), "Road cells by palette (Color)", fill=(255, 255, 255), font=F(40))
for i, (n, t) in enumerate(TINT.items()):
    d.rectangle((20 + (i % 2) * 500, 85 + (i // 2) * 70, 70 + (i % 2) * 500, 135 + (i // 2) * 70), outline=t, width=6)
    d.text((90 + (i % 2) * 500, 85 + (i // 2) * 70), "%s  %d cells" % (n, cnt.get(n, 0)), fill=(255, 255, 255), font=F(40))
others = [("%s %d" % (n, c)) for n, c in sorted(cnt.items(), key=lambda kv: -kv[1]) if n not in TINT]
d.text((20, 240), "No box (road edge on the land's own palette):", fill=(255, 210, 90), font=F(28))
d.text((20, 280), ", ".join(others[:5]), fill=(255, 210, 90), font=F(28))
d.text((20, 320), ", ".join(others[5:]), fill=(255, 210, 90), font=F(28))
out = Image.new("RGB", (im.width, im.height + leg.height))
out.paste(leg, (0, 0)); out.paste(im, (0, leg.height))
out.save(sys.argv[1])
print(out.size, cnt)
