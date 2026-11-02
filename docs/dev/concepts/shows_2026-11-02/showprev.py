#!/usr/bin/env python3
"""Preview only: transcribes the hand-drawn grids, decides no pixels.

  showprev.py gif   THEME OUT.gif FILE...   GIF x4 at game speed, files side by side, Colour row over DMG row
  showprev.py sheet THEME OUT.png FILE...   every frame x4 on the venue's stage, Colour over DMG, one row per file
  showprev.py chk   FILE                    print frame count and the 8x16 quarter count (the gen_art band rule)

The stage is the venue's own stage art with stage_a / stage_b palettes (attr map); performers at screen x 24, 72, 120,
top at y 8 (feet on the stage's last pixel row), as src/rom0_relief.c draws them. DMG: BGP $E4, OBP0 $D0
(index 1 white, 2 light grey, 3 black). A dance shows frame (beat % 4) on all three; a band (6 frames) shows
performer k frame 2k + (beat & 1). One beat = 12 game frames.
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[4]
VD = ROOT / "assets/approved/venues"
IDX = {".": 0, "-": 1, "+": 2, "#": 3}
DMG_BG = [(255, 255, 255), (170, 170, 170), (85, 85, 85), (0, 0, 0)]
DMG_OBJ = [None, (255, 255, 255), (170, 170, 170), (0, 0, 0)]
import os
X4 = int(os.environ.get("SCALE", "4"))


def blocks(path):
    res, cur = [], []
    for line in Path(path).read_text().splitlines() + [""]:
        line = line.rstrip()
        if line.startswith(";"):
            continue
        if line == "":
            if cur:
                res.append(cur)
                cur = []
            continue
        cur.append(line)
    return res


def hexrgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def plain(p):
    return [l for l in Path(p).read_text().splitlines() if l and not l.startswith(";")]


def stage_img(t, cgb):
    rows, attr = plain(VD / f"{t}_stage.txt"), plain(VD / f"{t}_attr.txt")
    pal = json.loads((VD / f"{t}_pal.json").read_text())
    pa, pb = [[hexrgb(h) for h in pal[k]["hex"]] for k in ("stage_a", "stage_b")]
    im = Image.new("RGB", (160, 32))
    for y in range(32):
        for x in range(160):
            v = IDX[rows[y][x]]
            im.putpixel((x, y), (pb if attr[y // 8][x // 8] == "1" else pa)[v] if cgb else DMG_BG[v])
    return im


def scene(t, frames, beat, cgb, base):
    im = base.copy()
    pal = [hexrgb(h) for h in json.loads((VD / f"{t}_show_pal.json").read_text())["obj"]["hex"]]
    band = len(frames) == 6
    for k, x0 in enumerate((24, 72, 120)):
        f = frames[2 * k + (beat & 1)] if band else frames[beat % 4]
        for y, r in enumerate(f):
            for x, c in enumerate(r):
                v = IDX[c]
                if v:
                    im.putpixel((x0 + x, 8 + y), pal[v - 1] if cgb else DMG_OBJ[v])
    return im


def stack(t, frames, beat, bases):
    a, b = scene(t, frames, beat, True, bases[0]), scene(t, frames, beat, False, bases[1])
    im = Image.new("RGB", (160, 66), (40, 40, 40))
    im.paste(a, (0, 0))
    im.paste(b, (0, 34))
    return im.resize((160 * X4, 66 * X4), Image.NEAREST)


def quarters(frames):
    qs = []
    for f in frames:
        f = list(f) + ["." * 16] * 8
        for y0, x0 in ((0, 0), (0, 8), (16, 0), (16, 8)):
            q = tuple(r[x0:x0 + 8] for r in f[y0:y0 + 16])
            if q not in qs:
                qs.append(q)
    return len(qs)


def check(path):
    fr = blocks(path)
    pass
    for n, f in enumerate(fr):
        bad = [(y, r) for y, r in enumerate(f) if len(r) != 16 or not set(r) <= set(".-+#")]
        assert len(f) == 24 and not bad, f"{path}: frame {n}: {len(f)} rows; bad rows {bad}"
    return fr


def fig_frames(frames, cgb, t, bases, label=None):
    """every frame as its own 16x24 panel on the stage's wall colour, x4"""
    return None


def zoom(t, out, files, z=14):
    """design aid: frames x14 on the venue's stage-wall colour with a pixel grid and a ruler (Colour only)"""
    pal = [hexrgb(h) for h in json.loads((VD / f"{t}_show_pal.json").read_text())["obj"]["hex"]]
    pj = json.loads((VD / f"{t}_pal.json").read_text())
    wall = hexrgb(pj["stage_a"]["hex"][1])
    frames = [f for p in files for f in check(p)]
    W = len(frames) * (16 * z + 10) + 20
    im = Image.new("RGB", (W, 24 * z + 20), (40, 40, 40))
    d = ImageDraw.Draw(im)
    for i, f in enumerate(frames):
        x0 = 20 + i * (16 * z + 10)
        d.rectangle([x0, 14, x0 + 16 * z, 14 + 24 * z], fill=wall)
        for y, r in enumerate(f):
            for x, c in enumerate(r):
                v = IDX[c]
                if v:
                    d.rectangle([x0 + x * z, 14 + y * z, x0 + x * z + z - 1, 14 + y * z + z - 1], fill=pal[v - 1])
        for x in range(17):
            d.line([x0 + x * z, 14, x0 + x * z, 14 + 24 * z], fill=(90, 90, 90) if x % 4 else (150, 150, 150))
            if x < 16:
                d.text((x0 + x * z + 3, 2), "%x" % x, fill=(255, 255, 0))
        for y in range(25):
            d.line([x0, 14 + y * z, x0 + 16 * z, 14 + y * z], fill=(90, 90, 90) if y % 4 else (150, 150, 150))
        for y in range(24):
            if i == 0:
                d.text((2, 14 + y * z + 1), str(y), fill=(255, 255, 0))
    im.save(out)


def main():
    cmd, t = sys.argv[1], sys.argv[2]
    if cmd == "asm":      # asm OUT HEADER.txt PART... : concatenate hand-drawn parts (own work) into one show file
        head = Path(sys.argv[3]).read_text() if Path(sys.argv[3]).exists() else ""
        body = "\n".join(Path(p).read_text().strip("\n") + "\n" for p in sys.argv[4:])
        Path(t).write_text(head + body)
        print(len(blocks(t)), "frames,", quarters(blocks(t)), "quarters")
        return
    if cmd == "zoom":
        zoom(t, sys.argv[3], sys.argv[4:])
        return
    if cmd == "chk":
        fr = check(t)
        print(len(fr), "frames", quarters(fr) if len(fr) == 6 else "(dance)", "quarters")
        return
    out, files = sys.argv[3], sys.argv[4:]
    bases = (stage_img(t, True), stage_img(t, False))
    sets = [(Path(f).stem, check(f)) for f in files]
    if cmd == "gif":
        frames_out = []
        for beat in range(24):          # 24 beats: dances cycle 4 frames, bands alternate A/B
            row = [stack(t, fr, beat, bases) for _, fr in sets]
            w = sum(r.width for r in row) + 8 * (len(row) - 1)
            im = Image.new("RGB", (w, row[0].height + 14), (40, 40, 40))
            x = 0
            d = ImageDraw.Draw(im)
            for (name, _), r in zip(sets, row):
                im.paste(r, (x, 14))
                d.text((x + 2, 1), name, fill=(235, 235, 235))
                x += r.width + 8
            frames_out.append(im.quantize(256, dither=Image.Dither.NONE))
        frames_out[0].save(out, save_all=True, append_images=frames_out[1:], duration=12 * 1000 // 60 * 1, loop=0)
        return
    if cmd == "sheet":
        # one row per file: the frames' figures (colour over DMG), x4, each on the stage strip behind the performer
        rows = []
        for name, fr in sets:
            pal = [hexrgb(h) for h in json.loads((VD / f"{t}_show_pal.json").read_text())["obj"]["hex"]]
            panels = []
            for f in fr:
                pn = Image.new("RGB", (20 * 1, 1))   # placeholder replaced below
                cell = Image.new("RGB", (24, 66), (40, 40, 40))
                for cgb, y0 in ((True, 0), (False, 34)):
                    b = bases[0 if cgb else 1].crop((20, 8, 44, 32)) if False else bases[0 if cgb else 1].crop((8, 8, 32, 32))
                    cell.paste(b, (0, y0))
                    for y, r in enumerate(f):
                        for x, c in enumerate(r):
                            v = IDX[c]
                            if v:
                                cell.putpixel((4 + x, y0 + y), pal[v - 1] if cgb else DMG_OBJ[v])
                panels.append(cell.resize((24 * X4, 66 * X4), Image.NEAREST))
            w = sum(p.width + 6 for p in panels)
            row = Image.new("RGB", (w, panels[0].height + 14), (40, 40, 40))
            d = ImageDraw.Draw(row)
            d.text((2, 1), name, fill=(235, 235, 235))
            x = 0
            for i, p in enumerate(panels):
                row.paste(p, (x, 14))
                d.text((x + 2, 16), str(i), fill=(255, 255, 0))
                x += p.width + 6
            rows.append(row)
        W = max(r.width for r in rows)
        sheet = Image.new("RGB", (W, sum(r.height + 4 for r in rows)), (40, 40, 40))
        y = 0
        for r in rows:
            sheet.paste(r, (0, y))
            y += r.height + 4
        sheet.save(out)


main()
