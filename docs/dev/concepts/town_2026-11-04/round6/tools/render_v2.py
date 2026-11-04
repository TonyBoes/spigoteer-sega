#!/usr/bin/env python3
"""Render a portrait-v2 picture source (key + pixel grid) to PNGs. Transcription/preview only: no pixel is decided here.

    render_v2.py SRC.txt OUTPREFIX [--scale N]
writes OUTPREFIX_cgb.png and OUTPREFIX_dmg.png (nearest neighbour), and prints unique-tile count and colours per tile.
"""
import sys
from PIL import Image

DMG = [(224, 248, 208), (136, 192, 112), (52, 104, 86), (8, 24, 32)]
GREY = [(255, 255, 255), (170, 170, 170), (85, 85, 85), (0, 0, 0)]


def parse(path):
    key, pix, sec, meta = {}, [], None, {}
    for ln in open(path).read().split('\n'):
        if ln.startswith(';'):
            continue
        if ln.startswith('@size'):
            meta['w'], meta['h'] = map(int, ln.split()[1:3])
        elif ln.startswith('@key'):
            sec = 'key'
        elif ln.startswith('@pixels'):
            sec = 'pix'
        elif ln.startswith('@'):
            continue
        elif sec == 'key' and ln.strip():
            p = ln.split()
            key[p[0]] = (int(p[1]), p[2])
        elif sec == 'pix':
            if not ln.strip():
                break
            pix.append(ln)
    return key, pix


def hexrgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def render(key, pix, scale=1, dmg=False, grey=True):
    h, w = len(pix), len(pix[0])
    im = Image.new('RGB', (w, h))
    for y, r in enumerate(pix):
        for x, c in enumerate(r):
            s, hx = key[c]
            im.putpixel((x, y), (GREY if grey else DMG)[s] if dmg else hexrgb(hx))
    return im.resize((w * scale, h * scale), Image.NEAREST) if scale != 1 else im


def stats(key, pix):
    h, w = len(pix), len(pix[0])
    tiles, maps, bad = set(), [], []
    for ty in range(h // 8):
        for tx in range(w // 8):
            m, t = {}, []
            for y in range(ty * 8, ty * 8 + 8):
                row = []
                for x in range(tx * 8, tx * 8 + 8):
                    s, hx = key[pix[y][x]]
                    if m.setdefault(s, hx) != hx:
                        bad.append((tx, ty, s))
                    row.append(s)
                t.append(tuple(row))
            tiles.add(tuple(t))
            maps.append(tuple(sorted(m.items())))
    return len(tiles), maps, bad


if __name__ == '__main__':
    src, out = sys.argv[1], sys.argv[2]
    sc = int(sys.argv[sys.argv.index('--scale') + 1]) if '--scale' in sys.argv else 1
    key, pix = parse(src)
    render(key, pix, sc).save(out + '_cgb.png')
    render(key, pix, sc, dmg=True).save(out + '_dmg.png')
    n, maps, bad = stats(key, pix)
    print(f'{src}: {len(pix[0])}x{len(pix)} unique tiles {n}; tile clashes {len(set(bad))} {sorted(set(bad))[:12]}')
