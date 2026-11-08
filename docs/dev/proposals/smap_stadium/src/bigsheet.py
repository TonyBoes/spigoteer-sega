"""python3 bigsheet.py: stadium_map_sheet2.png, 2 columns (approved | after), DMG row then Color row, x3, big bold labels (phone), plus the whole map Color x1 (approved | after).
Run mkimgs.py before and after first (it writes out/stad/tmp/map_{before,after}_{crop,whole}_*.png)."""
import sys

from PIL import Image, ImageDraw, ImageFont

import mapctx as M

T = str(M.ROOT) + '/out/stad/tmp/'
OUT = str(M.ROOT) + '/docs/dev/proposals/smap_stadium/'
BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'


def font(n):
    try:
        return ImageFont.truetype(BOLD, n)
    except OSError:
        return ImageFont.load_default()


def labelled(path, text, scale, size=34):
    im = Image.open(path).convert('RGB')
    im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
    out = Image.new('RGB', (im.width, im.height + size + 14), (30, 30, 30))
    d = ImageDraw.Draw(out)
    d.text((10, 6), text, font=font(size), fill=(255, 255, 255))
    out.paste(im, (0, size + 14))
    return out


def grid(cells, cols, title, pad=14, tsize=40):
    w = max(c.width for c in cells)
    h = max(c.height for c in cells)
    rows = (len(cells) + cols - 1) // cols
    out = Image.new('RGB', (cols * (w + pad) + pad, rows * (h + pad) + pad + tsize + 20), (30, 30, 30))
    ImageDraw.Draw(out).text((pad, 10), title, font=font(tsize), fill=(255, 255, 255))
    for i, c in enumerate(cells):
        out.paste(c, (pad + (i % cols) * (w + pad), tsize + 30 + pad + (i // cols) * (h + pad)))
    return out


cells = [labelled(T + 'map_before_crop_d.png', 'APPROVED  DMG', 3), labelled(T + 'map_after_crop_d.png', 'AFTER  DMG', 3),
         labelled(T + 'map_before_crop_c.png', 'APPROVED  COLOR', 3), labelled(T + 'map_after_crop_c.png', 'AFTER  COLOR', 3)]
grid(cells, 2, 'STADIUM ON THE MAP').save(OUT + 'stadium_map_sheet2.png')
whole = [labelled(T + 'map_before_whole_c.png', 'APPROVED  whole map x1', 1, 24), labelled(T + 'map_after_whole_c.png', 'AFTER  whole map x1', 1, 24)]
grid(whole, 2, 'WHOLE MAP COLOR', tsize=28).save(OUT + 'stadium_map_whole_x1_2.png')
print('ok')
