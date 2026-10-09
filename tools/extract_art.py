#!/usr/bin/env python3
"""Extract the owner's pixel art (upload/) into gbsprite ASCII + assets/palettes.json.

Run:  python3 -I tools/extract_art.py [--verify] [--force]

assets/art/ (and assets/palettes.json) is now the SOURCE OF TRUTH: since M8b it holds hand-made, owner-approved
art (3/4-view patrons, back views, the bartender's mustache, palette overrides) that upload/ does not have. This
script was the one-off M0 import; it refuses to overwrite any existing assets/art file or assets/palettes.json
unless given --force (which throws the hand-made art away; --verify then checks the round trip).
Index scheme: 0 '.' transparent, 1 '-' lightest, 2 '+' middle, 3 '#' darkest,
ordered per sprite by luminance (0.299R+0.587G+0.114B), not by map label.  palettes.json lists hex/rgb15 in INDEX order 1,2,3
(light, mid, dark).
"""
import json, os, sys
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHEET1 = os.path.join(ROOT, "upload/gbc_bar_sprites_native.png")
SHEET2 = os.path.join(ROOT, "upload/gbc_bartender_native.png")
CH = ".-+#"

def pal(s):  # "dark mid light" as in the map
    return s.split()

# (palette key, sheet, x, y, w, h, [dark, mid, light])
SPR = []
def add(k, sh, x, y, w, h, p): SPR.append((k, sh, x, y, w, h, pal(p)))

PATRONS = {
 "divers": [("a","#182040 #C87830 #B8E8F8"),("b","#202018 #B85840 #C8F0D0"),("c","#101830 #8890A8 #F8F0C0")],
 "robots": [("a","#101828 #7888A0 #58F0F8"),("b","#281810 #B88848 #F8D058"),("c","#102010 #58A068 #F87070")],
 "lumberjacks": [("a","#382010 #D03028 #F8C090"),("b","#182038 #3060C8 #D89870"),("c","#102810 #389040 #A06848")],
 "chefs": [("a","#302018 #F0B888 #F8F8F8"),("b","#281810 #A06840 #F8F8F8"),("c","#201010 #683820 #F8F0E0")],
 "cowboys": [("a","#301808 #A06030 #F8C898"),("b","#281808 #C89850 #C08860"),("c","#382818 #E8E0C8 #885030")],
 "aliens": [("a","#102010 #58C048 #F8F878"),("b","#200830 #9050C8 #F8F8F8"),("c","#301008 #E87830 #88F8F0")],
 "ninjas": [("a","#080810 #283868 #F8C8A0"),("b","#180808 #A01818 #C89068"),("c","#101010 #787888 #906040")],
 "sports": [("a","#200808 #E02828 #F8C8A0"),("b","#081028 #2858D8 #B07850"),("c","#082008 #28A038 #704828")],
 "zoo": [("monkey","#281808 #885028 #E8C090"),("panda","#101010 #F8F8F0 #A0A0B0"),("lion","#301808 #C86018 #F8D060")],
}
GROUPS = {}  # file -> list of keys
for row, (g, vs) in enumerate(PATRONS.items()):
    GROUPS["patrons/" + g] = []
    for i, (v, p) in enumerate(vs):
        k = f"{g}_{v}"
        add(k, 1, 16 * i, 16 * row, 16, 16, p)
        GROUPS["patrons/" + g].append(k)
add("mug_full", 1, 0, 144, 16, 16, "#382010 #E89820 #F8F0D0")
add("mug_empty", 1, 16, 144, 16, 16, "#283040 #A8C8E0 #F8F8F8")
add("coin", 1, 32, 144, 8, 8, "#483010 #E0B020 #F8F0A0")
add("sparkle", 1, 48, 144, 8, 8, "#000000 #F8F8F8 #F8E070")
add("counter", 1, 64, 144, 8, 8, "#381808 #985020 #D89050")
BT = "#202030 #F8F8F0 #F0B888"
BNAMES = ["idle", "walk1", "walk2", "fill", "slide", "catch", "fail"]
GROUPS["bartender"] = []
for i, n in enumerate(BNAMES):
    add("bartender_" + n, 2, 16 * i, 0, 16, 24, BT); GROUPS["bartender"].append("bartender_" + n)
GNAMES = ["tip", "fall", "shatter", "settle"]
GROUPS["glass"] = []
for i, n in enumerate(GNAMES):
    add("glass_" + n, 2, 16 * i, 24, 16, 16, "#283040 #A8C8E0 #F8F8F8"); GROUPS["glass"].append("glass_" + n)
GROUPS["mug16"] = ["mug_full", "mug_empty"]
for k in ("coin", "sparkle", "counter"): GROUPS[k] = [k]

def lum(c): return 0.299*c[0] + 0.587*c[1] + 0.114*c[2]

def by_lum(p):
    """[dark, mid, light] from the map -> (light, mid, dark) sorted by luminance."""
    return sorted((rgb(c) for c in p), key=lum, reverse=True)

def rgb(h): h = h.lstrip("#"); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
def rgb15(c): return (c[0] >> 3) | ((c[1] >> 3) << 5) | ((c[2] >> 3) << 10)

def pal_key(k):
    if k.startswith("bartender_"): return "bartender"
    if k.startswith("glass_"): return "glass"
    return k

def extract(img, spr):
    k, sh, x, y, w, h, p = spr
    light, mid, dark = by_lum(p)
    cols = {1: light, 2: mid, 3: dark}
    rows, bad = [], 0
    for yy in range(h):
        r = ""
        for xx in range(w):
            R, G, B, A = img.getpixel((x + xx, y + yy))
            if A < 128: r += "."; continue
            best = None
            for i, c in cols.items():
                d = (R-c[0])**2 + (G-c[1])**2 + (B-c[2])**2
                if best is None or d < best[0]: best = (d, i)
            if best[0]: bad += 1
            r += CH[best[1]]
        rows.append(r)
    return rows, bad

def render(rows, p):
    light, mid, dark = by_lum(p)
    cols = {"-": light, "+": mid, "#": dark}
    im = Image.new("RGBA", (len(rows[0]), len(rows)))
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            im.putpixel((x, y), (0, 0, 0, 0) if ch == "." else cols[ch] + (255,))
    return im

def parse_txt(path):
    frames, cur = [], []
    for line in open(path):
        line = line.rstrip("\n")
        if line.startswith(";") or line.startswith("//"): continue
        if not line.strip():
            if cur: frames.append(cur); cur = []
        else: cur.append(line.strip())
    if cur: frames.append(cur)
    return frames

def main():
    verify = "--verify" in sys.argv
    imgs = {1: Image.open(SHEET1).convert("RGBA"), 2: Image.open(SHEET2).convert("RGBA")}
    by = {s[0]: s for s in SPR}
    data, palettes, total_bad = {}, {}, 0
    print(f"{'sprite':22} {'mismatched px':>13}")
    for s in SPR:
        rows, bad = extract(imgs[s[1]], s)
        data[s[0]] = rows; total_bad += bad
        print(f"{s[0]:22} {bad:13d}")
        palettes.setdefault(pal_key(s[0]), s[6])
    print(f"total mismatched pixels: {total_bad}")
    outdir = os.path.join(ROOT, "assets/art")
    force = "--force" in sys.argv
    targets = [os.path.join(outdir, f + ".txt") for f in GROUPS] + [os.path.join(ROOT, "assets/palettes.json")]
    exist = [t for t in targets if os.path.exists(t)]
    if exist and not force:
        print("refusing to overwrite hand-made art (assets/art is the source of truth):")
        for t in exist: print("  " + os.path.relpath(t, ROOT))
        print("pass --force to replace them with the upload/ extraction")
        sys.exit(2)
    for f, keys in GROUPS.items():
        path = os.path.join(outdir, f + ".txt")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            fh.write(f"; generated by tools/extract_art.py from upload/ -- do not edit by hand\n")
            fh.write(f"; frames: {', '.join(keys)}\n")
            fh.write(f"; palette key(s): {', '.join(sorted({pal_key(k) for k in keys}))} (see assets/palettes.json)\n")
            fh.write("\n\n".join("\n".join(data[k]) for k in keys) + "\n")
    out = {}; changed = []
    for name, p in palettes.items():
        cs = by_lum(p)
        out[name] = {"hex": ["#%02x%02x%02x" % c for c in cs],
                     "rgb15": [rgb15(c) for c in cs]}
        if cs != [rgb(p[2]), rgb(p[1]), rgb(p[0])]: changed.append(name)
    with open(os.path.join(ROOT, "assets/palettes.json"), "w") as fh:
        json.dump({"_note": "hex/rgb15 in gbsprite index order 1,2,3 = light, mid, dark; index 0 transparent",
                   **out}, fh, indent=1); fh.write("\n")
    print("palettes reordered vs map labels:", ", ".join(changed) or "none")
    print(f"wrote {len(GROUPS)} ascii files and assets/palettes.json")
    if verify:
        bad_total = 0; n = 0
        for f, keys in GROUPS.items():
            frames = parse_txt(os.path.join(outdir, f + ".txt"))
            assert len(frames) == len(keys), f
            for k, fr in zip(keys, frames):
                s = by[k]
                got = render(fr, s[6])
                ref = imgs[s[1]].crop((s[2], s[3], s[2] + s[4], s[3] + s[5]))
                diff = sum(1 for a, b in zip(list(got.get_flattened_data()), list(ref.get_flattened_data()))
                           if (a[3] < 128 and b[3] < 128) is False and a != b)
                bad_total += diff; n += 1
                if diff: print(f"VERIFY diff {k}: {diff}px")
        print(f"verify: {n} sprites round-tripped, {bad_total} differing pixels")
        sys.exit(1 if bad_total else 0)

main()
