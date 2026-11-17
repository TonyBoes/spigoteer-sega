#!/usr/bin/env python3
"""Where each boss card's ink stands against the screen's centre (x 80), DMG and Color, from the real roll (a CRSCENE / CRSPLIT build).

    python3 tools/dev/credits_boss_centre.py ROM BUILD_DIR [--models dmg,cgb] [--sheet OUT.png] [--json OUT.json]

Per boss: the body's ink box (his tiles and the topper sprite, every frame of the roll that has the whole card above his name on the screen: his three poses
are in it) and the name's ink box, as the union over those frames and as the range of the per-frame centres; the offset is the box's centre minus 80 (px, +
right). --sheet writes a labelled contact sheet of one frame of each boss (x2). Reads the ROM, writes only --sheet / --json."""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "tools" / "dev"))
from credits_roll_check import layout, SCROLL, ST, PH   # noqa: E402
from credits_shots import start                        # noqa: E402

NAMES = ["BIG TEX", "THE MASCOT", "SASQUATCH", "THE CRITIC", "THE YETI", "PROTOTYPE", "DUKE", "SUMO CHAMP", "LEO THE LION", "MOTHERSHIP"]


def box(img, bg, y0, y1):
    a = (img[y0:y1] != bg).any(axis=2)
    cols = np.where(a.any(axis=0))[0]
    return (int(cols[0]), int(cols[-1])) if len(cols) else None


def measure(rom, build, model):
    lay, owners, bosses, cards = layout(build)
    res = {}
    samples = {}
    with start(rom, model) as gb:
        pb = gb.pb
        for n in range(13000):
            pb.tick(1, True)
            st = gb.read("story_scratch", 70)
            if gb.mem("story_phase") != 8 or (st[ST] == 3 and (st[PH] | st[PH + 1] << 8) >= 40):
                break
            scroll = st[SCROLL] | st[SCROLL + 1] << 8
            for v in range(10):
                w, h, _ = cards[3 + 3 * v + 2]
                top = w * 8 - scroll
                body_y0 = max(0, top)
                nm_y = (w + lay["R_BNAME"]) * 8 - scroll
                if top < -8 or nm_y < 0 or nm_y + 8 > 144:
                    continue
                img = np.asarray(pb.screen.image.convert("RGB")).astype(np.int16)
                bg = img[nm_y + 4, 2]                                   # (the blank row's colour: the card's background)
                b = box(img, bg, body_y0, nm_y)
                nm = box(img, bg, nm_y, nm_y + 8)
                r = res.setdefault(v, {"body": [], "name": []})
                if b:
                    r["body"].append(b)
                if nm:
                    r["name"].append(nm)
                if v not in samples or (len(r["body"]) % 40 == 20 and len(samples.get((v, "x"), [])) < 3):
                    samples.setdefault((v, "x"), []).append(Image.fromarray(img.astype(np.uint8)))
                    samples.setdefault(v, samples[(v, "x")][0])
    out = {}
    for v, r in res.items():
        ent = {}
        for k in ("body", "name"):
            bs = r[k]
            if not bs:
                continue
            lo, hi = min(b[0] for b in bs), max(b[1] for b in bs)
            cs = [(b[0] + b[1] + 1) / 2 for b in bs]
            ent[k] = {"x0": lo, "x1": hi, "off": (lo + hi + 1) / 2 - 80, "frame_off_min": min(cs) - 80, "frame_off_max": max(cs) - 80, "frames": len(bs)}
        out[v] = ent
    return out, samples


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rom")
    ap.add_argument("build")
    ap.add_argument("--models", default="dmg,cgb")
    ap.add_argument("--sheet")
    ap.add_argument("--json")
    a = ap.parse_args()
    allres = {}
    sheets = {}
    for model in a.models.split(","):
        out, samples = measure(Path(a.rom), Path(a.build), model)
        allres[model] = out
        sheets[model] = samples
        print(model)
        print("  %-13s %-26s %-26s" % ("boss", "body x0-x1 off (frame range)", "name x0-x1 off"))
        for v in sorted(out):
            b, n = out[v].get("body"), out[v].get("name")
            print("  %-13s %3d-%3d %+5.1f (%+5.1f..%+5.1f)   %3d-%3d %+5.1f" % (NAMES[v], b["x0"], b["x1"], b["off"], b["frame_off_min"], b["frame_off_max"], n["x0"], n["x1"], n["off"]))
    if a.json:
        Path(a.json).write_text(json.dumps(allres, indent=1))
    if a.sheet:
        W, H = 160 * 2, 144 * 2
        sheet = Image.new("RGB", (W * 5, (H + 14) * 4), (40, 40, 40))
        d = ImageDraw.Draw(sheet)
        for mi, model in enumerate(a.models.split(",")):
            for v in range(10):
                im = sheets[model].get(v)
                if im is None:
                    continue
                x, y = (v % 5) * W, (mi * 2 + v // 5) * (H + 14)
                sheet.paste(im.resize((W, H), Image.NEAREST), (x, y + 14))
                d.text((x + 3, y + 1), "%s %s" % (model.upper(), NAMES[v]), fill=(255, 255, 255))
                d.line([(x + 80 * 2, y + 14), (x + 80 * 2, y + 14 + H)], fill=(255, 0, 255))
        sheet.save(a.sheet)


if __name__ == "__main__":
    main()
