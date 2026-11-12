"""Rendering helpers: DMG greys, nearest-neighbour scaling, big labels (the owner reads on a phone)."""
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import lib

GREY = np.array([248, 168, 88, 24], dtype=np.uint8)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def font(n):
    return ImageFont.truetype(FONT, n)


def world_px(dm):
    """(CH*8, CW*8) shades of the finished map (state 11), as the build's Model holds it"""
    return np.array(dm.world.px, dtype=np.uint8) if False else np.array(lib.model().world.px, dtype=np.uint8)


def new_world(dm, arr):
    """pixels of the finished map after the id map arr (id -> representative id): every cell shows its representative's block"""
    sigs = np.array([list(s) for s in dm.sigs], dtype=np.uint8)
    g = arr[dm.grids[lib.G.NSTATE]]
    out = np.zeros((lib.CH * 8, lib.CW * 8), dtype=np.uint8)
    for y in range(lib.CH):
        for x in range(lib.CW):
            out[y * 8:y * 8 + 8, x * 8:x * 8 + 8] = sigs[g[y, x]].reshape(8, 8)
    return out


def grey(px):
    return GREY[px]


def scale(rgb, k):
    return np.kron(rgb, np.ones((k, k, 1), dtype=np.uint8)) if rgb.ndim == 3 else np.kron(rgb, np.ones((k, k), dtype=np.uint8))


def overlay(old, new, colour=(230, 40, 40), dim=True):
    """today's pixels in DMG greys, dimmed, with the pixels that changed painted in a flag colour (rgb array)"""
    rgb = np.stack([grey(old)] * 3, axis=-1).astype(np.uint8)
    if dim:
        rgb = (rgb * 0.55 + 255 * 0.45).astype(np.uint8)
    rgb[old != new] = colour
    return rgb


def panel(rgb_img, label, k, size=26, sub=None, pad=10):
    """a labelled panel: big label strip over the image scaled k times"""
    im = Image.fromarray(scale(rgb_img, k))
    f = font(size)
    h = size + 16 + (size - 6 if sub else 0)
    out = Image.new("RGB", (im.width, im.height + h), (255, 255, 255))
    d = ImageDraw.Draw(out)
    d.text((4, 4), label, fill=(0, 0, 0), font=f)
    if sub:
        d.text((4, size + 8), sub, fill=(70, 70, 70), font=font(size - 8))
    out.paste(im, (0, h))
    return out


def row(panels, gap=14, bg=(200, 200, 200)):
    w = sum(p.width for p in panels) + gap * (len(panels) + 1)
    h = max(p.height for p in panels) + 2 * gap
    out = Image.new("RGB", (w, h), bg)
    x = gap
    for p in panels:
        out.paste(p, (x, gap))
        x += p.width + gap
    return out


def stack(images, gap=14, bg=(200, 200, 200), title=None, size=34):
    """title: a string, or a list of strings (one line each, the first at `size`, the rest smaller)"""
    w = max(i.width for i in images)
    lines = [title] if isinstance(title, str) else (title or [])
    th = (size + 20 + (len(lines) - 1) * (size * 2 // 3 + 8)) if lines else 0
    h = sum(i.height for i in images) + th
    out = Image.new("RGB", (w, h), bg)
    yy = 10
    for k, ln in enumerate(lines):
        fs = size if k == 0 else size * 2 // 3
        ImageDraw.Draw(out).text((12, yy), ln, fill=(0, 0, 0), font=font(fs))
        yy += fs + 8
    y = th
    for i in images:
        out.paste(i, (0, y))
        y += i.height
    return out
