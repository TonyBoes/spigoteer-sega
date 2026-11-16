#!/usr/bin/env python3
"""Every owner scene page of the real roll against the artist's approved composite, pixel for pixel (CRSCENE=1 builds, Color and DMG).

    python3 tools/dev/credits_pages_vs_approved.py ROM BUILD_DIR [--models dmg,cgb] [--approved DIR] [--sheet OUT.png] [--shots DIR]

The page is captured from the running roll at the scroll where its 18 rows fill the screen (CRSPLIT builds: the page sits at its card's row SGT; the jump
builds hold the page there as well). DIR holds <venue>_card_<cgb|dmg>.png (160 x 144): the artist's round 6 (docs/dev/concepts/credits_scenes_2026-11-13/round6 on
branch worktree-agent-aa21f868f71a0344f; render_f.py makes them). Prints, per venue and model, the differing pixels (count and bounding box); exits 1 if any
differs. --sheet writes an x8 contact sheet of the differences (crop around each venue's differing pixels: roll | approved | diff). Reads the ROM, writes only --sheet / --shots."""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "tools" / "dev"))
sys.path.insert(0, str(ROOT / "tools" / "credits_scenes"))
from credits_shots import start      # noqa: E402
import scenes_f as F                 # noqa: E402

import os      # noqa: E402
DEFAULT = ROOT / "tests" / "approved" / ("credits_pages" if os.environ.get("CRART") == "7" else "credits_pages8")      # (copies of the artist's round-8 cards; CRART=7: round 6/7's)
# Known, with the numbers: the Color pages of lodge, bistro, igloo, factory and biker cannot have the approved cream letters on the band and navy behind the owner's name: their cells need 7 BG palettes
# besides the stage palette (a whole palette [cream, band, free, navy] makes 9; tools/gen_credits.py free_palette proves it), the hardware has 8. Bistro's accordionist is an OBJ (the approved
# composite draws her into the BG with a ninth palette and moves the room's pixels in her cells).
CAPACITY = {"lodge", "bistro", "igloo", "factory", "biker"}
OBJ_PERF = {"bistro"}
NOFREE = {"bistro", "factory"}      # round 8, Color: every BG palette of these pages is full (4 colours of art), so there is no entry for the navy margin: the margins keep the stage colour


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rom")
    ap.add_argument("build")
    ap.add_argument("--models", default="dmg,cgb")
    ap.add_argument("--approved", default=str(DEFAULT))
    ap.add_argument("--sheet")
    ap.add_argument("--shots")
    a = ap.parse_args()
    build, appr = Path(a.build), Path(a.approved)
    h = (build / "credits_text.h").read_text()
    import re
    ostart = [int(x) for x in re.search(r"ct_ostart\[10\] = \{([^}]*)\}", h).group(1).split(",")]
    sgt = int(re.search(r"#define CT_SGT (\d+)", h).group(1))
    keys = [v.key for v in F.VENUES]
    fail, rows, known = False, [], []
    for model in a.models.split(","):
        gb = start(a.rom, model)
        targets = {(ostart[v] + sgt) * 8 + 1: v for v in range(10)}      # (SCY one above the first line of row 0: the roll draws a line below its row, a 1-px offset of the generator that the approved composites do not have either way: see the report)
        got = {}
        for n in range(14000):
            gb.pb.tick(1, True)
            st = gb.read("story_scratch", 30)
            sc = st[20] | st[21] << 8
            sc = next((t for t in targets if abs(t - sc) <= 1 and gb.pb.memory[0xFF42] == t & 255), None)      # (the screen shows SCY, which the update writes a frame before the roll's own count)
            if sc is not None and targets[sc] not in got:
                got[targets[sc]] = (np.asarray(gb.pb.screen.image.convert("RGB")).astype(int), bytes(gb.pb.memory[0xFE00:0xFEA0]))
                if len(got) == 10:
                    break
        for v in range(10):
            ap_ = np.asarray(Image.open(appr / f"{keys[v]}_card_{model}.png").convert("RGB")).astype(int)
            if v not in got:
                print(f"{model} {keys[v]}: page never captured")
                fail = True
                continue
            img = got[v][0]
            d = (np.abs(img - ap_).sum(axis=2) > 0)
            c = int(d.sum())
            if c:
                pic_ = int(d[32:136].sum())
                text_ = int(d[8:32].sum() + d[136:].sum())
                bad_ = bool((pic_ and keys[v] not in OBJ_PERF and not (model == "cgb" and keys[v] in NOFREE)) or (text_ and not (model == "cgb" and keys[v] in CAPACITY)))
                if not bad_:
                    known.append((model, keys[v]))
                ys, xs = np.nonzero(d)
                pic = int(d[32:136].sum())
                print(f"{model} {keys[v]:9s}: {c} px differ, y {ys.min()}-{ys.max()} x {xs.min()}-{xs.max()}; in the picture (lines 32-135) {pic}, venue name band (8-31) {int(d[8:32].sum())}, owner name (136-143) {int(d[136:].sum())}")
                fail = fail or bad_
                rows.append((f"{model} {keys[v]} {c}px", img, ap_, d))
                if a.shots:
                    Path(a.shots).mkdir(parents=True, exist_ok=True)
                    Image.fromarray(img.astype(np.uint8)).save(Path(a.shots) / f"{model}_{keys[v]}_roll.png")
            else:
                print(f"{model} {keys[v]:9s}: identical")
    if a.sheet and rows:
        S = 3
        W = 160 * S
        sheet = Image.new("RGB", (W * 3 + 16, (144 * S + 14) * len(rows)), (40, 40, 40))
        dr = ImageDraw.Draw(sheet)
        for i, (lab, img, ap_, d) in enumerate(rows):
            y0 = i * (144 * S + 14)
            dr.text((2, y0 + 1), lab + ": roll | approved | diff (red)", fill=(235, 235, 235))
            diff = np.where(d[:, :, None], np.array([255, 0, 0]), (ap_ // 3))
            for j, im in enumerate((img, ap_, diff)):
                sheet.paste(Image.fromarray(im.astype(np.uint8)).resize((W, 144 * S), Image.NEAREST), (j * (W + 8), y0 + 14))
        sheet.save(a.sheet)
    if known:
        print("known (see the header): " + ", ".join(f"{m} {k}" for m, k in known))
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
