"""python3 sheet13.py: after render_one.py for cB and dB (env MB_TEAFIX=1 MB_PASTURE=1): two columns, B as picked | B after the pass; per row: DMG close-up x4, DMG map x3, Color close-up x4,
Color map x3.  Big bold labels (the owner reads it on a phone).  Writes ../milkbar_sheet13.png"""
from PIL import Image, ImageDraw, ImageFont

ROOT = '/workspace/.claude/worktrees/agent-a742552fa3a9454c1'
TMP = ROOT + '/out/mb'
MODES = (('cB', 'B as picked'), ('dB', 'B after pass'))
FONT = ImageFont.load_default(size=40)
BIG = ImageFont.load_default(size=46)
PAD = 16
BG, FG = (30, 30, 34), (255, 255, 255)

rows = []
for tag in ('DMG', 'Color'):
    for kind, scale, nm in (('close', 4, 'close-up x4'), ('map', 3, 'map x3')):
        ims = []
        for mode, _ in MODES:
            f = f'{TMP}/r6_{mode}_close{tag}.png' if kind == 'close' else f'{TMP}/r6_{mode}_{tag}.png'
            im = Image.open(f)
            ims.append(im.resize((im.width * scale, im.height * scale), 0))
        rows.append((f'{tag} {nm}', ims))
colw = max(im.width for _, ims in rows for im in ims)
W = PAD * 3 + colw * 2
H = PAD
H += 60 + sum(52 + max(im.height for im in ims) + PAD for _, ims in rows)
sheet = Image.new('RGB', (W, H), BG)
d = ImageDraw.Draw(sheet)
y = PAD
for k, (_, name) in enumerate(MODES):
    d.text((PAD + k * (colw + PAD), y), name, fill=FG, font=BIG)
y += 60
for label, ims in rows:
    d.text((PAD, y), label, fill=FG, font=FONT)
    y += 52
    for k, im in enumerate(ims):
        sheet.paste(im, (PAD + k * (colw + PAD), y))
    y += max(im.height for im in ims) + PAD
sheet.save(ROOT + '/docs/dev/proposals/smap_milkbar/milkbar_sheet13.png')
print(sheet.size)
