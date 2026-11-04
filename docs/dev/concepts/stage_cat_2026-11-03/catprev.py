#!/usr/bin/env python3
"""Preview only (reads the approved stage, writes nothing under assets/ or src/): the saloon stage cat, current vs proposals.

  catprev.py show VERSION [FRAME]      print the cat's 16x24 patch (x104-119, y8-31) as text, default frame base
  catprev.py sheet OUT.png             contact sheet: stage strip x3 (DMG over Color) + detail x8, current and every vN.txt
  catprev.py gif VERSION OUT.gif       x3, Color over DMG, the saloon_anim.txt !script (tail, blink, ear flick)
  catprev.py png VERSION OUT.png [FRAME]  the full 160x32 stage with that cat, 4-shade indexed (for the lint)

A version file holds the cat's 4 tiles as 8x8 grids: "@static" = tiles (13,2) and (14,2) side by side (y16-23, "C D");
@A_base @A_blink @A_ear = tile (14,1), the head (y8-15); @B_hang @B_left @B_right @B_flick = tile (13,3), the tail over
the stage lip (y24-31). The seven saloon_anim.txt frames pair them (FRAMES below): the animation tiles stay the same 7.
Colours: stage_a / stage_b from saloon_pal.json (the cat's 4 tiles use stage_b), DMG shades as in the engine.
"""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
VD = ROOT / "assets/approved/venues"
IDX = {".": 0, "-": 1, "+": 2, "#": 3}
DMG = [(255, 255, 255), (170, 170, 170), (85, 85, 85), (0, 0, 0)]
# saloon_anim.txt frame -> (head tile variant, tail tile variant)
FRAMES = {"base": ("A_base", "B_hang"), "left": ("A_base", "B_left"), "right": ("A_base", "B_right"),
          "hang_blink": ("A_blink", "B_hang"), "flick": ("A_base", "B_flick"), "left_blink": ("A_blink", "B_left"),
          "hang_ear": ("A_ear", "B_hang")}
CAT_TILES = {(14, 1): "A", (13, 2): "C", (14, 2): "D", (13, 3): "B"}


def frames_of(ver):
    """frame name -> (head block, tail block): the version's own '; FRAME name = HEAD TAIL' lines, else FRAMES."""
    own = {}
    p = HERE / f"{ver}.txt"
    if p.exists():
        for l in p.read_text().split("\n"):
            if l.startswith("; FRAME "):
                n, _, rest = l[8:].partition("=")
                h, t = rest.split()
                own[n.strip()] = (h, t)
    return own or FRAMES


def own_script(ver):
    p = HERE / f"{ver}.txt"
    if p.exists():
        for l in p.read_text().split("\n"):
            if l.startswith("; SCRIPT:"):
                return [(a.split(":")[0], int(a.split(":")[1])) for a in l[9:].split()]
    return None


def hexrgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def blocks(path):
    out, cur = {}, None
    for line in Path(path).read_text().split("\n"):
        if line.startswith("@"):
            cur = out.setdefault(line[1:].strip(), [])
        elif cur is not None and line.strip() and line[0] not in ";!":
            cur.append(line.rstrip())
    return out


def stage_rows():
    return [l.rstrip("\n") for l in (VD / "saloon_stage.txt").read_text().split("\n") if l and not l.startswith(";")]


def stage_pixels(ver, frame="base"):
    """160x32 grid of (index, tile palette 0/1) with the cat's 4 tiles replaced from the version file."""
    rows = [list(r) for r in stage_rows()]
    b = blocks(HERE / f"{ver}.txt")
    for y, ln in enumerate(b["static"]):
        c, d = ln.split(" ")
        rows[16 + y][104:112], rows[16 + y][112:120] = list(c), list(d)
    ah, bt = frames_of(ver)[frame]
    for y in range(8):
        rows[8 + y][112:120], rows[24 + y][104:112] = list(b[ah][y]), list(b[bt][y])
    return rows


def stage_img(ver, cgb, frame="base"):
    pal = json.loads((VD / "saloon_pal.json").read_text())
    pa = [hexrgb(h) for h in pal["stage_a"]["hex"]]
    pb = [hexrgb(h) for h in pal["stage_b"]["hex"]]
    rows = stage_pixels(ver, frame)
    im = Image.new("RGB", (160, 32))
    for y in range(32):
        for x in range(160):
            v = IDX[rows[y][x]]
            cat = (x // 8, y // 8) in CAT_TILES
            im.putpixel((x, y), ((pb if cat else pa)[v]) if cgb else DMG[v])
    return im


def crop(im, scale, x0=72, x1=152):
    return im.crop((x0, 0, x1, 32)).resize(((x1 - x0) * scale, 32 * scale), Image.NEAREST)


def detail(ver, cgb, scale=8):
    return stage_img(ver, cgb).crop((100, 8, 124, 32)).resize((24 * scale, 24 * scale), Image.NEAREST)


def versions():
    return ["current"] + sorted(p.stem for p in HERE.glob("v[0-9]*.txt"))


NAMES = {"current": "CURRENT"}


def label_of(ver):
    for l in (HERE / f"{ver}.txt").read_text().split("\n"):
        if l.startswith("; NAME:"):
            return l[7:].strip()
    return ver


def sheet(out, only=None):
    tmp = HERE / "_tmp"
    tmp.mkdir(exist_ok=True)
    items = []
    for v in (only or versions()):
        lab = "CURRENT" if v == "current" else f"{v.upper()} {label_of(v)}"
        strip = Image.new("RGB", (80 * 3, 32 * 3 * 2 + 4), (40, 40, 40))
        strip.paste(crop(stage_img(v, False), 3), (0, 0))
        strip.paste(crop(stage_img(v, True), 3), (0, 32 * 3 + 4))
        det = Image.new("RGB", (24 * 6 * 2 + 4, 24 * 6), (40, 40, 40))
        det.paste(detail(v, False, 6), (0, 0))
        det.paste(detail(v, True, 6), (24 * 6 + 4, 0))
        one = Image.new("RGB", (24 * 2 + 2 + 80, 32), (40, 40, 40))
        one.paste(stage_img(v, False).crop((72, 0, 152, 32)), (0, 0))
        one.paste(stage_img(v, True).crop((72, 0, 152, 32)), (82, 0))
        cell = Image.new("RGB", (max(strip.width, det.width, one.width * 1), strip.height + det.height + 32 + 12), (40, 40, 40))
        cell.paste(strip, (0, 0))
        cell.paste(det, (0, strip.height + 4))
        cell.paste(stage_img(v, False).crop((72, 0, 152, 32)), (0, strip.height + det.height + 8))
        cell.paste(stage_img(v, True).crop((72, 0, 152, 32)), (84, strip.height + det.height + 8))
        p = tmp / f"{v}.png"
        cell.save(p)
        items.append(f"{lab}={p}")
    subprocess.run([sys.executable, str(ROOT / "tools/dev/contact_sheet.py"), out, "--scale", "1", "--cols", str(min(3, len(items))),
                    "--title", "Saloon stage cat: x3 strip DMG over Color; x6 detail DMG|Color; 1x DMG|Color"] + items, check=True)
    for p in tmp.glob("*.png"):
        p.unlink()
    tmp.rmdir()


def script(ver=None):
    if ver and own_script(ver):
        return own_script(ver)
    for l in (VD / "saloon_anim.txt").read_text().split("\n"):
        if l.startswith("!script"):
            return [(a.split(":")[0], int(a.split(":")[1])) for a in l.split()[1:]]


def gif(ver, out):
    cache, frames, durs = {}, [], []
    for fr, hold in script(ver):
        if fr not in cache:
            im = Image.new("RGB", (240, 200), (40, 40, 40))
            im.paste(crop(stage_img(ver, True, fr), 3), (0, 0))
            im.paste(crop(stage_img(ver, False, fr), 3), (0, 104))
            cache[fr] = im.quantize(256, dither=Image.Dither.NONE)
        frames.append(cache[fr])
        durs.append(round(hold * 1000 / 60 / 10) * 10)
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=durs, loop=0)


def frame_sheet(ver, out, scale=8):
    """Every frame of a version at x8, Color over DMG, labelled, in order of first use in its script."""
    from PIL import ImageDraw
    names = list(dict.fromkeys(["base"] + [f for f, _ in script(ver)]))
    w = 24 * scale
    im = Image.new("RGB", (len(names) * (w + 6), 2 * w + 10 + 16), (40, 40, 40))
    d = ImageDraw.Draw(im)
    for i, n in enumerate(names):
        x = i * (w + 6)
        for r, cgb in enumerate((True, False)):
            im.paste(stage_img(ver, cgb, n).crop((100, 8, 124, 32)).resize((w, w), Image.NEAREST), (x, r * (w + 4)))
        d.text((x + 2, 2 * w + 10), f"{i}: {n}", fill=(255, 255, 255))
    im.save(out)


def main():
    m = sys.argv[1]
    if m == "show":
        rows = stage_pixels(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "base")
        for y in range(8, 32):
            print("%2d" % y, "".join(rows[y][104:120]))
    elif m == "build":  # build vN : vN_canvas.txt (hand-drawn 16x16 composites) -> vN.txt (tile grids), a pure transcription
        v = sys.argv[2]
        cb = blocks(HERE / f"{v}_canvas.txt")
        hdr = [l for l in (HERE / f"{v}_canvas.txt").read_text().split("\n") if l.startswith(";")]
        for k in ("base", "blink", "ear"):
            assert all(len(r) == 16 for r in cb[k]), (k, [len(r) for r in cb[k]])
        assert len(cb["base"]) == 16 and len(cb["blink"]) == 8 and len(cb["ear"]) == 8
        for k in ("B_hang", "B_left", "B_right", "B_flick"):
            assert len(cb[k]) == 8 and all(len(r) == 8 for r in cb[k]), k
        out = hdr + ["", "@static"]
        for y in range(8, 16):
            out.append(cb["base"][y][:8] + " " + cb["base"][y][8:])
        for name, key in (("A_base", "base"), ("A_blink", "blink"), ("A_ear", "ear")):
            out += ["", "@" + name] + [cb[key][y][8:] for y in range(8)]
        for name in ("B_hang", "B_left", "B_right", "B_flick"):
            out += ["", "@" + name] + cb[name]
        (HERE / f"{v}.txt").write_text("\n".join(out) + "\n")
    elif m == "zoom":  # zoom OUT.png SCALE VERSION... : detail at SCALE, DMG|Color, one pair per version
        sc = int(sys.argv[3])
        vs = sys.argv[4:]
        w = 24 * sc
        im = Image.new("RGB", (len(vs) * (2 * w + 12), w), (40, 40, 40))
        for i, v in enumerate(vs):
            im.paste(detail(v, False, sc), (i * (2 * w + 12), 0))
            im.paste(detail(v, True, sc), (i * (2 * w + 12) + w + 4, 0))
        im.save(sys.argv[2])
    elif m == "big":  # big OUT.png VERSION... : x10 detail, DMG|Color, base frame
        vs = sys.argv[3:]
        im = Image.new("RGB", (len(vs) * (240 * 2 + 12), 240), (40, 40, 40))
        for i, v in enumerate(vs):
            im.paste(detail(v, False, 10), (i * 492, 0))
            im.paste(detail(v, True, 10), (i * 492 + 246, 0))
        im.save(sys.argv[2])
    elif m == "sheet":
        sheet(sys.argv[2], sys.argv[3:] or None)
    elif m == "frames":  # frames VERSION OUT.png: every frame x8, Color over DMG
        frame_sheet(sys.argv[2], sys.argv[3])
    elif m == "gif":
        gif(sys.argv[2], sys.argv[3])
    elif m == "png":
        rows = stage_pixels(sys.argv[2], sys.argv[4] if len(sys.argv) > 4 else "base")
        im = Image.new("P", (160, 32))
        im.putpalette([c for s in DMG for c in s])
        for y in range(32):
            for x in range(160):
                im.putpixel((x, y), IDX[rows[y][x]])
        im.save(sys.argv[3])


if __name__ == "__main__":
    main()
