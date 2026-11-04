#!/usr/bin/env python3
"""Check (read-only) composed pictures: unique tiles, clashes, CGB palettes as gen_story packs them (HUD BG1 allowed),
palettes outside / inside the portrait frame rect. Writes x3 previews.   check.py PICDIR OUTDIR"""
import sys
from pathlib import Path
from PIL import Image

T = Path(__file__).resolve().parent
sys.path.insert(0, str(T))
sys.path.insert(0, str(T.parents[2] / "tools"))
from render_v2 import parse, render, stats      # noqa: E402
import gen_story as GS                           # noqa: E402

LIMIT = {"intro_before": 151, "intro_a": 151 - 34, "finale_a": 146, "credits_b": 199}
FRAME = (1, 4, 9, 12)       # portrait frame cells: cols 1-9, rows 4-12


def packs(key, pix, cells):
    hud = GS.hud_palette()
    maps = []
    for (tx, ty) in cells:
        m = {}
        for y in range(ty * 8, ty * 8 + 8):
            for x in range(tx * 8, tx * 8 + 8):
                s, hx = key[pix[y][x]]
                m[s] = hx
        maps.append(m)
    fits = lambda m: all(hud[s] == GS.q5(c) for s, c in m.items())
    um = []
    for m in maps:
        t = tuple(sorted(m.items()))
        if not fits(m) and t not in um:
            um.append(t)
    big = list(dict.fromkeys(m for m in um if not any(set(m) < set(o) for o in um)))
    try:
        return GS.pack_palettes([dict(m) for m in big])[0] if big else []
    except TypeError:
        print('    >8 palettes; distinct maps:', len(big))
        for m in big:
            print('      ', m)
        return [None] * 9


if __name__ == "__main__":
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    for name in LIMIT:
        p = src / f"{name}.txt"
        if not p.exists():
            continue
        key, pix = parse(p)
        n, maps, bad = stats(key, pix)
        allc = [(x, y) for y in range(13) for x in range(20)]
        inside = [(x, y) for (x, y) in allc if FRAME[0] <= x <= FRAME[2] and FRAME[1] <= y <= FRAME[3]]
        outside = [c for c in allc if c not in inside]
        pa, po = packs(key, pix, allc), packs(key, pix, outside)
        print(f"{name}: tiles {n} / {LIMIT[name]}  clashes {sorted(set(bad))[:8]}  pals all {len(pa)}  outside-frame {len(po)}")
        for q in pa:
            q and print("   ", dict(sorted(q.items())))
        render(key, pix, 3).save(out / f"{name}_cgb.png")
        render(key, pix, 3, dmg=True).save(out / f"{name}_dmg.png")
