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
NAVY2BLACK = False
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


def sprite_mask(oam, pad=4):
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
        meta, sgt, exp, owners = {"objs": [], "split": False}, 0, [], []
    bad = {"scan": [], "page": [], "sprites": []}
    crops = {}
    bgs = None                                             # the page's colours, the cards' and the pages': in a shared screen the blank rows change colour at the strip, which is by design
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
            if NAVY2BLACK and model == "cgb":                     # (the reference roll is the old navy build: its navy is the black of the Color roll, #080818)
                img[(img == (24, 16, 64)).all(axis=2)] = (8, 8, 24)
            oam = bytes(pb.memory[0xFE00:0xFEA0])
            scroll = st[SCROLL] | st[SCROLL + 1] << 8
            pos = st[POS] | st[POS + 1] << 8
            shist = (shist + [scroll, pos])[-6:]
            hist.append(sprite_mask(oam))
            for nm_, slot_, cd_ in (("spigoteer", 32 if meta.get("split") else 0, cards[1]), ("dregs", 36 if meta.get("split") else 4, cards[2]), ("endcard", 0, None)):      # the Spigoteer's and Dregs's sprites, pixel for pixel: the crop under their four OAM entries, every frame they are whole on the screen
                es = [(oam[4 * k], oam[4 * k + 1]) for k in range(slot_, slot_ + 4)]
                if (scroll >= (cards[-1][0] + cards[-1][1]) * 8 if cd_ is None else cd_[0] * 8 - 144 < scroll < (cd_[0] + cd_[1]) * 8) and all(16 < oy <= 144 and 8 < ox < 160 for oy, ox in es):
                    y0, y1, x0, x1 = min(oy for oy, _ in es) - 16, max(oy for oy, _ in es), min(ox for _, ox in es) - 8, max(ox for _, ox in es)
                    crops.setdefault(nm_, {}).setdefault((y1 - y0, x1 - x0, img[y0:y1, x0:x1].astype(np.uint8).tobytes()), n)
            hist[:] = hist[-3:]
            if n >= SKIP:
                tag = None
                if bgs is None:
                    u_, c_ = np.unique(img.reshape(-1, 3), axis=0, return_counts=True)
                    bgs = [tuple(int(x) for x in u_[c_.argmax()])] + [tuple(int(x) for x in exp[v][0, 0]) for v in range(len(exp))]
                inbg = lambda im: np.isin(im.astype(np.int64) @ np.array([65536, 256, 1]), [a_ * 65536 + b_ * 256 + c2_ for a_, b_, c2_ in bgs]) if meta.get("split") else np.zeros(im.shape[:2], bool)
                # scan: the previous frame, shifted by 0..3 px, with the sprites of the last three frames masked
                if prev is not None and len(hist) == 3:
                    best = None
                    for d in range(4):
                        a, b = img[0:144 - d], prev[d:144]
                        mk = hist[2][0:144 - d] | hist[1][d:144] | hist[0][d:144]
                        diff = (np.abs(a - b).sum(axis=2) > 0) & ~mk & ~(inbg(a) & inbg(b))
                        diff[:2] = False
                        for lo, hi in bosses:
                            y0 = lo - scroll
                            diff[max(0, y0 - 16):max(0, y0 + 40)] = False
                        c = int(diff.sum())
                        if best is None or c < best[0]:
                            best = (c, d, diff)
                    flat = lambda im: len(np.unique(im.reshape(-1, 3), axis=0)) <= 3           # (a palette swap while the screen shows nothing but the page colour, in one frame or two: allowed, the rule is that it only happens then)
                    if best[0] and not (flat(img) and flat(prev)):
                        ys, xs = np.nonzero(best[2])
                        bad["scan"].append((n, scroll, best[0], int(ys.min()), int(ys.max()), int(xs.min()), int(xs.max())))
                        tag = tag or "scan"
                # page and sprites
                pvis = 0
                for v, ro in enumerate(owners):
                    pt = (ro + sgt) * 8
                    best = None
                    for sc in set(shist):
                        off = pt - sc
                        if not -144 < off < 144:
                            continue
                        e = np.empty((144, 160, 3), np.int16)
                        e[:, :] = exp[v][0, 0]
                        rows = np.zeros(144, bool)
                        for y in range(144):
                            cy = y - off
                            if 0 <= cy < 144:
                                e[y] = exp[v][cy]
                                rows[y] = True
                        diff = (np.abs(img - e).sum(axis=2) > 0) & ~hist[2] & ~(inbg(img) & inbg(e))
                        if meta.get("split"):                       # (the cards above and below share the screen: the rows of the page are the page's, the others are the cards' (the cards check))
                            diff &= rows[:, None]
                        diff[:2] = False                           # (the first lines: the DMG header's BGP (cast_isr, src/main.c), and a sprite's last row at the top)
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
                    ok = True
                    nn = len(objs)
                    slots = [24 + kk if nn > 24 and kk < nn - 24 else [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 12][kk - (nn - 24) if nn > 24 else kk] for kk in range(nn)]
                    pvis = 0
                    for kk in range(nn):                        # (each object against the scroll of this frame or of the last frames: the sprite stage writes for the next frame's scroll)
                        oy, ox, ot, op = oam[4 * slots[kk]:4 * slots[kk] + 4]
                        match = False
                        for sc in set(shist):
                            ya = pt - sc + 48 + objs[kk][1]
                            if 0 < ya < 160:
                                match |= (oy, ox, ot, op) == (ya, objs[kk][0], objs[kk][2], objs[kk][3])
                            elif not meta.get("split"):
                                match |= not (0 < oy < 160)         # (in a shared screen a hidden object's slot may show the card above's or below's sprite)
                            else:
                                match = True
                        if not match and len(bad["sprites"]) < 3:
                            print("  sprite mismatch frame", n, "object", kk, "slot", slots[kk], "actual", (oy, ox, ot, op), "want y", [pt - sc + 48 + objs[kk][1] for sc in set(shist)], objs[kk])
                        ok &= match
                        if 0 < pt - scroll + 48 + objs[kk][1] < 160:
                            pvis += 1
                    if not meta.get("split"):
                        for k in range(40):
                            if k not in slots:
                                ok &= not (0 < oam[4 * k] < 160)
                    if not ok:
                        bad["sprites"].append((n, v))
                        tag = tag or "sprites"
                for ci, (cs, ch, own) in enumerate(cards):          # (every other card at every 8 px of its own scroll: what the reference build shows)
                    rel = scroll - cs * 8
                    if not own and -143 <= rel <= ch * 8 and rel % 8 == 0 and (ci, rel) not in cards_seen:
                        cards_seen[(ci, rel)] = (img.astype(np.uint8), sprite_mask(oam, 10), scroll, sum(1 for k in range(40) if 0 < oam[4 * k] < 160 and 0 < oam[4 * k + 1] < 168) - pvis)
                if tag and shots and sum(len(x) for x in bad.values()) < 40:
                    Path(shots).mkdir(parents=True, exist_ok=True)
                    Image.fromarray(img.astype(np.uint8)).save(Path(shots) / f"{model}_{n}_{tag}.png")
            prev = img
    bad["crops"] = crops
    return n, bad, cards_seen, cards, bosses, owners, meta.get("split", False), bgs


def main():
    global NAVY2BLACK
    ap = argparse.ArgumentParser()
    ap.add_argument("rom")
    ap.add_argument("build")
    ap.add_argument("--models", default="dmg,cgb")
    ap.add_argument("--shots")
    ap.add_argument("--ref-rom", help="the same roll without scene pages (CRFLOW=SMOOTH alone; CRGAPS=1 as well when the split build has CRSPLIT's card heights, which is the default now: build/ref with `CRGAPS=1 CRFLOW=SMOOTH make BUILD=out/b_ref OUT=out/o_ref unlocked`): every other card must look as it does there, at the same row of its own")
    ap.add_argument("--ref-build")
    ap.add_argument("--max-frames", type=int, default=12500)
    a = ap.parse_args()
    fail = False
    for model in a.models.split(","):
        frames, bad, seen, cards, bosses, owners, split, bgset = run(Path(a.rom), Path(a.build), model, a.shots, a.max_frames)
        crops = bad.pop("crops")
        if a.ref_rom:
            NAVY2BLACK = True
            _, rbad, rseen, rcards, rbosses, _, _, _ = run(Path(a.ref_rom), Path(a.ref_build), model, None, a.max_frames)
            NAVY2BLACK = False
            rcrops = rbad.pop("crops")
            bad["spritepix"] = [(nm_, n_) for nm_, cs_ in crops.items() for (h_, w_, b_), n_ in cs_.items() if (h_, w_, b_) not in rcrops.get(nm_, {})]      # (the Spigoteer's / Dregs's sprites, every frame, are one of the reference roll's pictures of them)
            bad["cards"] = []
            bad["sprites_late"] = []
            for (ci, rel), (img, mask, scroll, nvis) in sorted(seen.items()):
                if (ci, rel) not in rseen:
                    continue
                rimg, rmask, rscroll, rnvis = rseen[(ci, rel)]
                if nvis != rnvis:                              # (every sprite of a card is there from its first visible row, as in the roll without pages)
                    bad["sprites_late"].append((ci, rel, nvis, rnvis))
                cs, ch, _ = cards[ci]
                diff = (np.abs(img.astype(np.int16) - rimg.astype(np.int16)).sum(axis=2) > 0) & ~mask & ~rmask
                if split:
                    inb = lambda im: np.isin(im.astype(np.int64) @ np.array([65536, 256, 1]), [a_ * 65536 + b_ * 256 + c2_ for a_, b_, c2_ in bgset])
                    diff &= ~(inb(img) & inb(rimg))
                own = np.zeros(144, bool)
                for y in range(144):
                    own[y] = cs * 8 <= scroll + y < (cs + ch) * 8
                    if split and any((ro - 3) * 8 <= scroll + y < (ro - 1) * 8 or (ro + 19) * 8 <= scroll + y < (ro + 21) * 8 for ro in owners):
                        own[y] = False                              # (the strips: a blank palette change)
                diff &= own[:, None]
                diff[:2] = False
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
