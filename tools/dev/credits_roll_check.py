#!/usr/bin/env python3
"""Whole-roll check of the scrolling credits (CRSCENE=1 builds; the CRFLOW=SMOOTH roll): EVERY frame of the real roll, DMG or Color.

    python3 tools/dev/credits_roll_check.py ROM BUILD_DIR [--models dmg,cgb] [--shots OUTDIR] [--max-frames N]

BUILD_DIR is the build's directory (credits_text.json, credits_pages.npz: tools/gen_credits.py writes both). Checks, per frame:

  scan     no pixel of the picture changes except by the scroll (the previous frame shifted by the scroll's px): half-built rows, scrambled tiles, a palette
           that moves on the screen. Sprites' boxes and the bosses' body rows (their animation) are masked.
  page     while any row of a scene page's 18 rows is in view, the whole screen is that page as generated (rows as built by gen_credits.py, palettes as
           intended) and nothing else: the blank rows around it are the page colour, so no other card is on the screen with it. Sprite boxes are masked here.
  sprites  while a page is in view its OAM entries are exactly the page's objects (x, tile, flags; y from the scroll), and no other entry is visible.

Prints the frames that fail, grouped, and exits 1 if there are any. Reads the ROM; writes only --shots.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "tools" / "dev"))

from credits_shots import start      # noqa: E402

SCROLL, POS, ST, PH = 20, 22, 62, 38
SKIP = 75            # frames: the fade in


def layout(build):
    lay = json.loads((build / "credits_text.json").read_text())["layout"]
    w = 8
    heights = [(lay["H_TITLE"], lay["GAP_TITLE"]), (lay["H_SD"], lay["G"]), (lay["H_SD"], lay["G"])]
    for v in range(10):
        heights += [(lay["H_OWN"], lay["G"]), (lay["H_PAT"], lay["G"]), (lay["H_BOSS"], lay["G"])]
    owners, bosses, cards = [], [], []
    for i, (h, g) in enumerate(heights):
        if i >= 3 and (i - 3) % 3 == 0:
            owners.append(w)
        if i >= 3 and (i - 3) % 3 == 2:
            bosses.append(((w + lay["R_BBODY"]) * 8, (w + lay["R_BBODY"] + 2) * 8))
        cards.append((w, h, i >= 3 and (i - 3) % 3 == 0))
        w += h + g
    return lay, owners, bosses, cards


def sprite_mask(oam, pad=3):
    m = np.zeros((144, 160), bool)
    for k in range(40):
        oy, ox = oam[4 * k], oam[4 * k + 1]
        if 0 < oy < 160 and 0 < ox < 168:
            m[max(0, oy - 16 - pad - 1):max(0, oy + pad), max(0, ox - 8 - pad):max(0, ox + pad)] = True
    return m


def run(rom, build, model, shots, max_frames):
    lay, owners, bosses, cards = layout(build)
    cards_seen = {}
    m = 1 if model == "cgb" else 0
    if (build / "credits_pages.npz").exists():
        pages = np.load(build / "credits_pages.npz")
        meta = json.loads(str(pages["meta"]))
        sgt = meta["sgt"]
        exp = [pages[f"p{v}_{m}"].astype(np.int16) for v in range(10)]
    else:                                          # (a build without scene pages: the scan only)
        meta, sgt, exp, owners = {"objs": []}, 0, [], []
    bad = {"scan": [], "page": [], "sprites": []}
    with start(rom, model) as gb:
        pb = gb.pb
        prev = None
        hist = []
        shist = []
        n = 0
        for n in range(max_frames):
            pb.tick(1, True)
            st = gb.read("story_scratch", 70)
            if gb.mem("story_phase") != 8 or (st[ST] == 3 and (st[PH] | st[PH + 1] << 8) >= 40):
                break
            img = np.asarray(pb.screen.image.convert("RGB")).astype(np.int16)
            oam = bytes(pb.memory[0xFE00:0xFEA0])
            scroll = st[SCROLL] | st[SCROLL + 1] << 8
            pos = st[POS] | st[POS + 1] << 8
            shist = (shist + [scroll, pos])[-6:]
            hist.append(sprite_mask(oam))
            hist[:] = hist[-3:]
            if n >= SKIP:
                tag = None
                for ci, (cs, ch, own) in enumerate(cards):          # (every other card at every 8 px of its own scroll: what the reference build shows)
                    rel = scroll - cs * 8
                    if not own and -143 <= rel <= ch * 8 and rel % 8 == 0 and (ci, rel) not in cards_seen:
                        cards_seen[(ci, rel)] = (img.astype(np.uint8), hist[2].copy(), scroll)
                # scan: the previous frame, shifted by 0..3 px, with the sprites of the last three frames masked
                if prev is not None and len(hist) == 3:
                    best = None
                    for d in range(4):
                        a, b = img[0:144 - d], prev[d:144]
                        mk = hist[2][0:144 - d] | hist[1][d:144] | hist[0][d:144]
                        diff = (np.abs(a - b).sum(axis=2) > 0) & ~mk
                        for lo, hi in bosses:
                            y0 = lo - scroll
                            diff[max(0, y0 - 16):max(0, y0 + 40)] = False
                        c = int(diff.sum())
                        if best is None or c < best[0]:
                            best = (c, d, diff)
                    flat = lambda im: len(np.unique(im.reshape(-1, 3), axis=0)) <= 2           # (a palette swap while the screen shows nothing but the page colour, in one frame or two: allowed, the rule is that it only happens then)
                    if best[0] and not (flat(img) and flat(prev)):
                        ys, xs = np.nonzero(best[2])
                        bad["scan"].append((n, scroll, best[0], int(ys.min()), int(ys.max()), int(xs.min()), int(xs.max())))
                        tag = tag or "scan"
                # page and sprites
                for v, ro in enumerate(owners):
                    pt = (ro + sgt) * 8
                    best = None
                    for sc in set(shist):
                        off = pt - sc
                        if not -144 < off < 144:
                            continue
                        e = np.empty((144, 160, 3), np.int16)
                        e[:, :] = exp[v][0, 0]
                        for y in range(144):
                            cy = y - off
                            if 0 <= cy < 144:
                                e[y] = exp[v][cy]
                        diff = (np.abs(img - e).sum(axis=2) > 0) & ~hist[2]
                        diff[0] = False                            # (line 0 is drawn with the DMG header's BGP: cast_isr, src/main.c)
                        c = int(diff.sum())
                        if best is None or c < best[0]:
                            best = (c, sc, diff)
                    if best is None:
                        continue
                    if best[0]:
                        ys, xs = np.nonzero(best[2])
                        bad["page"].append((n, v, best[0], int(ys.min()), int(ys.max()), int(xs.min()), int(xs.max())))
                        if shots and len(bad["page"]) <= 3:
                            Path(shots).mkdir(parents=True, exist_ok=True)
                            Image.fromarray(np.where(best[2][:, :, None], 255, 0).astype(np.uint8).repeat(3, axis=2)).save(Path(shots) / f"{model}_{n}_pagediff.png")
                        tag = tag or "page"
                    objs = meta["objs"][v]
                    ok = False
                    for sc in set(shist):
                        off = pt - sc
                        good = True
                        for k in range(40):
                            oy, ox, ot, op = oam[4 * k:4 * k + 4]
                            if k < len(objs):
                                ya = off + 32 + 16 + objs[k][1]
                                want = ya if 0 < ya < 160 else None
                                if want is None:
                                    good &= not (0 < oy < 160)
                                else:
                                    good &= (oy, ox, ot, op) == (want, objs[k][0], objs[k][2], objs[k][3])
                            else:
                                good &= not (0 < oy < 160)
                        ok |= good
                    if not ok:
                        bad["sprites"].append((n, v))
                        tag = tag or "sprites"
                if tag and shots and sum(len(x) for x in bad.values()) < 40:
                    Path(shots).mkdir(parents=True, exist_ok=True)
                    Image.fromarray(img.astype(np.uint8)).save(Path(shots) / f"{model}_{n}_{tag}.png")
            prev = img
    return n, bad, cards_seen, cards, bosses


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rom")
    ap.add_argument("build")
    ap.add_argument("--models", default="dmg,cgb")
    ap.add_argument("--shots")
    ap.add_argument("--ref-rom", help="the same roll without scene pages (CRFLOW=SMOOTH alone): every other card must look as it does there, at the same row of its own")
    ap.add_argument("--ref-build")
    ap.add_argument("--max-frames", type=int, default=12500)
    a = ap.parse_args()
    fail = False
    for model in a.models.split(","):
        frames, bad, seen, cards, bosses = run(Path(a.rom), Path(a.build), model, a.shots, a.max_frames)
        if a.ref_rom:
            _, _, rseen, rcards, rbosses = run(Path(a.ref_rom), Path(a.ref_build), model, None, a.max_frames)
            bad["cards"] = []
            for (ci, rel), (img, mask, scroll) in sorted(seen.items()):
                if (ci, rel) not in rseen:
                    continue
                rimg, rmask, rscroll = rseen[(ci, rel)]
                cs, ch, _ = cards[ci]
                diff = (np.abs(img.astype(np.int16) - rimg.astype(np.int16)).sum(axis=2) > 0) & ~mask & ~rmask
                own = np.zeros(144, bool)
                for y in range(144):
                    own[y] = cs * 8 <= scroll + y < (cs + ch) * 8
                diff &= own[:, None]
                diff[0] = False
                for lo, hi in bosses:
                    y0 = lo - scroll
                    diff[max(0, y0 - 16):max(0, y0 + 40)] = False
                if diff.any():
                    bad["cards"].append((ci, rel, int(diff.sum())))
        print(f"{model}: {frames} frames; " + " ".join(f"{k} {len(v)}" for k, v in bad.items()) + (f"  ({sum(1 for k in seen if k in rseen)} card views compared with the reference)" if a.ref_rom else ""))
        for kind, rows in bad.items():
            if rows:
                fail = True
                print(f"  {kind}: first", rows[:8])
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
