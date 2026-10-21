#!/usr/bin/env python3
"""The graphics atlas generator: `make atlas` (python3 tools/gfx_atlas/build.py [--only id,id] [--models dmg,cgb] [--out dir]).

Drives build/game.gb in PyBoy to every screen listed in scenes.py on DMG and CGB, samples a window of frames on each, and writes
out/atlas/: index.html (page.html), data/<screen>.js (one global per screen), data/index.js, data/summary.js, img/*.png|gif.
Deterministic: the same ROM gives the same files (the only varying text is the "generated from commit" line in data/index.js).
"""
import argparse
import json
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tests"))

import analyze as A      # noqa: E402
import capture as C      # noqa: E402


def js(name, obj):
    return "window.ATLAS = window.ATLAS || {}; window.ATLAS[%s] = %s;\n" % (json.dumps(name), json.dumps(obj, separators=(",", ":"), sort_keys=True))


def run_screen(scr, model, assets, window, step):
    """Reach the screen, sample it, return (record, sidecar) or (None, error text)."""
    rom = None
    try:
        got = scr["fn"](model)
        rom, driver = got if isinstance(got, tuple) else (got, None)
        cgb = model == "cgb"
        samples = []
        n = scr.get("window", window)
        for i in range(n):
            if driver:
                driver(rom, i)
            sampling = i % step == 0
            rom.run(1, sampling)
            if sampling:
                img = rom.pb.screen.image.convert("RGB").copy()
                samples.append(C.take(rom, cgb, i, img))
        rec, side = A.analyze(samples, model, assets, "img/%s.%s" % (scr["id"], model), scr["id"], step)
        return rec, side
    except Exception:
        return None, traceback.format_exc()
    finally:
        if rom is not None:
            try:
                rom.stop()
            except Exception:
                pass


PACK_X = 168        # packed image: the still at x 0, then the tile sheets (bank 0 grey, bank 0 colour, bank 1 grey, bank 1 colour) 136 px apart
SPR_X = PACK_X + 4 * 136   # the sprite cells (transparent ground): one row of 8x16 cells per palette, 16 px apart
PACK_ROW = 200      # a model's row of the packed image: DMG at y 0, CGB at y 200


def pack(out, sid, recs, side):
    """One PNG per screen holding both models' still and tile sheets (a published version may hold only ~500 files)."""
    from PIL import Image
    im = Image.new("RGBA", (SPR_X + A.SPR_CAP * 8, 2 * PACK_ROW), (0, 0, 0, 255))
    im.paste((0, 0, 0, 0), (SPR_X, 0, im.width, im.height))
    for model, rec in recs.items():
        y0 = PACK_ROW if model == "cgb" else 0
        sd = side[(sid, model)]
        im.paste(sd["still_img"], (0, y0))
        sheets = []
        for bnk, (g, c) in enumerate(sd["sheet_imgs"]):
            gx, cx = PACK_X + bnk * 2 * 136, PACK_X + (bnk * 2 + 1) * 136
            im.paste(g, (gx, y0))
            im.paste(c, (cx, y0))
            sheets.append(dict(gray=[gx, y0], colour=[cx, y0]))
        for g in rec["spr"]["groups"]:
            for i, e in enumerate(side[(sid, model)]["spr"].get(g["slot"], [])[:A.SPR_CAP]):
                im.paste(e["img"], (SPR_X + i * 8, y0 + g["slot"] * 16))
        rec["spr"]["at"] = [SPR_X, y0]
        rec["pack"] = dict(png="img/%s.png" % sid, still=[0, y0], sheets=sheets, w=im.width, h=im.height)
    A.save_png(im, out / "img" / ("%s.png" % sid))


def git_info():
    try:
        h = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], text=True).strip()
        d = subprocess.check_output(["git", "-C", str(ROOT), "log", "-1", "--format=%cd", "--date=format:%Y-%m-%d %H:%M"], text=True).strip()
        dirty = subprocess.check_output(["git", "-C", str(ROOT), "status", "--porcelain", "--", "src", "assets", "tools/gen_art.py"], text=True).strip()
        return h + ("+local changes" if dirty else ""), d
    except Exception:
        return "unknown", ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="comma list of screen ids")
    ap.add_argument("--models", default="dmg,cgb")
    ap.add_argument("--out", default=str(ROOT / "out" / "atlas"))
    ap.add_argument("--window", type=int, default=180, help="frames sampled per screen (3 s)")
    ap.add_argument("--step", type=int, default=3, help="sample every N frames")
    a = ap.parse_args()
    out = Path(a.out)
    only = [x for x in a.only.split(",") if x]
    models = a.models.split(",")
    import scenes
    screens = [s for s in scenes.SCREENS if not only or s["id"] in only]
    if not only and out.exists():
        shutil.rmtree(out)
    (out / "data").mkdir(parents=True, exist_ok=True)
    (out / "img").mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    index, side, report, failures = [], {}, {}, []
    for scr in screens:
        entry = dict(id=scr["id"], group=scr["group"], name=scr["name"], note=scr.get("note", ""), models={})
        rec_all = {}
        for model in models:
            rec, res = run_screen(scr, model, out, a.window, a.step)
            if rec is None:
                failures.append((scr["id"], model, res))
                entry["models"][model] = False
                print("  FAIL %-22s %s: %s" % (scr["id"], model, res.strip().splitlines()[-1]), flush=True)
                continue
            rec_all[model] = rec
            side[(scr["id"], model)] = res
            entry["models"][model] = True
        if rec_all:
            pack(out, scr["id"], rec_all, side)
            (out / "data" / (scr["id"] + ".js")).write_text(js(scr["id"], dict(id=scr["id"], name=scr["name"], group=scr["group"], note=scr.get("note", ""),
                                                                               **rec_all)))
        index.append(entry)
        print("  ok   %-22s %s" % (scr["id"], ",".join(m for m in models if entry["models"].get(m))), flush=True)
    import summary
    summ = summary.build(screens, side, models, out)
    h, d = git_info()
    for w in summ.get("free", {}).get("warnings", []):
        print("  WARNING free-palette table: " + w)
    (out / "data" / "summary.js").write_text(js("summary", summ))
    (out / "data" / "index.js").write_text(js("index", dict(screens=index, commit=h, date=d, regions=A.REGIONS,
                                                           roles=summary.roles())))
    page = (HERE / "page.html").read_text()
    (out / "index.html").write_text(page)                                  # (a fragment: the host adds the document skeleton)
    (out / "standalone.html").write_text('<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"></head>\n<body>\n'
                                         + page + "</body></html>\n")        # (the same page as a whole document, for opening the folder directly)
    size = sum(f.stat().st_size for f in out.rglob("*") if f.is_file())
    print("\natlas: %d screens x %s, %d failures, %.1f MB in %s (%.0f s)" % (len(index), "/".join(models), len(failures), size / 1e6, out, time.time() - t0))
    for sid, model, tb in failures:
        print("--- %s %s\n%s" % (sid, model, tb))
    return 1 if failures and not only else 0


if __name__ == "__main__":
    sys.exit(main())
