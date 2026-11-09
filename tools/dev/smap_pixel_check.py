#!/usr/bin/env python3
"""Read-only: assert the story map's picture is pixel-identical to a git ref (default main), on Color and DMG, except in the cells listed with --allow x,y.

    python3 tools/dev/smap_pixel_check.py [--ref main] [--allow X,Y ...]

Renders both worlds (assets/smap/world_c.png + world_d.png + the cell palettes' RGB) to RGB and compares them pixel by pixel; prints the differing cells (or "identical").
Exit status 1 if any cell outside --allow differs.  Writes nothing.
"""
import argparse
import io
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent.parent
MERGE = {"forest": "grass", "desert": "saloon", "factory_b": "factory", "tea_b": "tea", "town3": "town5"}     # (tools/smap_world/world2.py)


def blob(ref, name):
    if ref is None:
        return (ROOT / "assets" / "smap" / name).read_bytes()
    return subprocess.run(["git", "-C", str(ROOT), "show", f"{ref}:assets/smap/{name}"], check=True, capture_output=True).stdout


def render(ref):
    js = json.loads(blob(ref, "world.json"))
    names, rgb, cp = js["pal_names"], js["pal_rgb"], js["cell_pal"]
    ci = Image.open(io.BytesIO(blob(ref, "world_c.png")))
    di = Image.open(io.BytesIO(blob(ref, "world_d.png")))
    w, h = ci.size
    cpx, dpx = list(ci.getdata()), list(di.getdata())
    dshade = js["dmg_shade"]
    col = Image.new("RGB", (w, h))
    out = []
    for y in range(h):
        for x in range(w):
            pal = rgb[names[ord(cp[y >> 3][x >> 3]) - 48]]
            out.append(tuple(pal[cpx[y * w + x]]))
    col.putdata(out)
    dmg = Image.new("L", (w, h))
    dmg.putdata([dshade[v] for v in dpx])
    return col, dmg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="main")
    ap.add_argument("--allow", action="append", default=[])
    a = ap.parse_args()
    allow = {tuple(int(v) for v in s.split(",")) for s in a.allow}
    bc, bd = render(a.ref)
    nc, nd = render(None)
    bad = set()
    for name, p, q in (("Color", bc, nc), ("DMG", bd, nd)):
        if p.size != q.size:
            print(name, "size differs", p.size, q.size); sys.exit(1)
        pp, qq = list(p.getdata()), list(q.getdata())
        w = p.size[0]
        for i, (u, v) in enumerate(zip(pp, qq)):
            if u != v:
                bad.add((name, (i % w) >> 3, (i // w) >> 3))
    out = sorted(b for b in bad if (b[1], b[2]) not in allow)
    if out:
        print("DIFFERENT cells:", out[:20], len(out)); sys.exit(1)
    print("identical to", a.ref, "(Color and DMG)" + (f", {len(bad)} allowed cell(s) differ" if bad else ""))


main()
