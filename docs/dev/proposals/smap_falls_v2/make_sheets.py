"""python3 make_sheets.py IMGDIR OUTDIR : composes the owner's sheets from render_one.py's frames (IMGDIR/<key>_*.png, key = now, A, B).  Big bold labels, nearest-neighbour scaling, Color above DMG.
    sheet_wide.png      the wide window (cells 24..63 x rows 0..12) x4: NOW, A, B stacked (one column), Color above DMG
    sheet_close.png     the x6 close-up of the interface, falls steps 0..3 as rows, NOW | A | B as the three columns, Color above DMG
    falls_v2.gif        the 180-frame loop at 50 ms, NOW | A | B, Color above DMG, x6 close-up (one shared palette: no colour flicker between frames)
The stock tools/dev/contact_sheet.py labels with PIL's tiny default font, unreadable on the owner's phone (memory: sheet labels readable), so the labels are drawn here with DejaVu Bold."""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

img, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
BG, FG, ACC = (30, 30, 34), (255, 255, 255), (255, 214, 90)
FB = "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"
try:
    F_BIG, F_MID = ImageFont.truetype(FB, 54), ImageFont.truetype(FB, 38)
except OSError:
    F_BIG = F_MID = ImageFont.load_default()
KEYS = ["now", "A", "B"]
NAMES = {"now": "NOW  cave mouth", "A": "A  cleft up the flank", "B": "B  notch under the snow"}
SHORT = {"now": "NOW", "A": "A", "B": "B"}
G = 14


def load(key, name, t=None):
    p = img / (f"{key}_{name}.png" if t is None else f"{key}_{name}_{t:03d}.png")
    return Image.open(p).convert("RGB")


def up(im, s):
    return im.resize((im.width * s, im.height * s), Image.NEAREST)


# ---- wide window -------------------------------------------------------------------------------------------------------------------------------------------------------------------------
S = 4
wide = {k: (up(load(k, "wide_c"), S), up(load(k, "wide_d"), S)) for k in KEYS}
w, h = wide["now"][0].size
sheet = Image.new("RGB", (w + 2 * G, 3 * (2 * h + 3 * G + 150) + 110), BG)
d = ImageDraw.Draw(sheet)
d.text((G, 14), "WIDE WINDOW x4   Color above DMG", fill=FG, font=F_BIG)
y = 100
for k in KEYS:
    d.text((G, y), NAMES[k], fill=ACC, font=F_BIG)
    y += 70
    d.text((G, y), "COLOR", fill=FG, font=F_MID)
    y += 50
    sheet.paste(wide[k][0], (G, y))
    y += h + G
    d.text((G, y), "DMG", fill=FG, font=F_MID)
    y += 50
    sheet.paste(wide[k][1], (G, y))
    y += h + 2 * G
sheet = sheet.crop((0, 0, sheet.width, y))
sheet.save(out / "sheet_wide.png")
print("sheet_wide", sheet.size)

# ---- close-up strip ----------------------------------------------------------------------------------------------------------------------------------------------------------------------
S = 6
TS = [9 * k + 6 for k in range(4)]
cw, ch = load("now", "close_c", TS[0]).size
cw, ch = cw * S, ch * S
W = 3 * cw + 4 * G
sheet = Image.new("RGB", (W, 110 + 4 * (2 * ch + 3 * G + 60) + 60), BG)
d = ImageDraw.Draw(sheet)
d.text((G, 14), "CLOSE-UP x6   Color above DMG", fill=FG, font=F_BIG)
for ci, k in enumerate(KEYS):
    d.text((G + ci * (cw + G), 76), SHORT[k], fill=ACC, font=F_BIG)
y0 = 150
for ri, t in enumerate(TS):
    yy = y0 + ri * (2 * ch + 3 * G + 60)
    d.text((G, yy), "falls step %d" % ri, fill=FG, font=F_MID)
    for ci, k in enumerate(KEYS):
        x = G + ci * (cw + G)
        sheet.paste(up(load(k, "close_c", t), S), (x, yy + 50))
        sheet.paste(up(load(k, "close_d", t), S), (x, yy + 50 + ch + G))
sheet = sheet.crop((0, 0, sheet.width, y0 + 4 * (2 * ch + 3 * G + 60)))
sheet.save(out / "sheet_close.png")
print("sheet_close", sheet.size)

# ---- GIF ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
frames = []
for t in range(0, 180, 3):
    f = Image.new("RGB", (W, 80 + 2 * ch + G + 10), BG)
    dd = ImageDraw.Draw(f)
    for ci, k in enumerate(KEYS):
        x = G + ci * (cw + G)
        dd.text((x, 8), SHORT[k], fill=ACC, font=F_BIG)
        f.paste(up(load(k, "close_c", t), S), (x, 76))
        f.paste(up(load(k, "close_d", t), S), (x, 76 + ch + G))
    frames.append(f)
pal = frames[0].quantize(colors=48, method=Image.Quantize.MEDIANCUT)
for f in frames[1:6]:                                   # one palette that holds every colour of the loop
    pass
allc = Image.new("RGB", (frames[0].width, frames[0].height * 4))
for i in range(4):
    allc.paste(frames[i * 15], (0, i * frames[0].height))
pal = allc.quantize(colors=64, method=Image.Quantize.MEDIANCUT)
q = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in frames]
q[0].save(out / "falls_v2.gif", save_all=True, append_images=q[1:], duration=50, loop=0, optimize=False)
print("gif", frames[0].size, len(q))
