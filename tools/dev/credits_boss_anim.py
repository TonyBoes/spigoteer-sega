#!/usr/bin/env python3
"""How each boss card animates in the real roll (a CRSPLIT build): the body's pose changes while he is fully on screen, DMG or Color.

    python3 tools/dev/credits_boss_anim.py ROM BUILD_DIR [--model cgb] [--gifs OUTDIR]

Per boss: the frames his body rows (the card's rows R_BBODY, +1) are fully on the screen, the pose changes in them (the map row's tile ids change), the poses in order, and the
pixels that change over the changes (the body box, sprites not masked: the topper bobs). --gifs writes OUTDIR/boss_<n>.gif, the card as it scrolls (every 2nd frame from the
frame the body row enters to the frame it leaves, x2). Reads the ROM, writes only OUTDIR."""
import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "tools" / "dev"))
from credits_roll_check import layout, SCROLL, ST, PH   # noqa: E402
from credits_shots import start                        # noqa: E402

NAMES = ["BIG TEX", "THE MASCOT", "SASQUATCH", "THE CRITIC", "THE YETI", "PROTOTYPE", "DUKE", "SUMO CHAMP", "LEO THE LION", "MOTHERSHIP"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rom")
    ap.add_argument("build")
    ap.add_argument("--model", default="cgb")
    ap.add_argument("--gifs")
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()
    lay, owners, bosses, cards = layout(Path(a.build))
    stat = {v: {"frames": 0, "rows": [], "chg": 0, "px": 0} for v in range(10)}
    frames = {v: [] for v in range(10)}
    prev = {}
    with start(a.rom, a.model) as gb:
        pb = gb.pb
        for n in range(13000):
            pb.tick(1, True)
            st = gb.read("story_scratch", 70)
            if gb.mem("story_phase") != 8 or (st[ST] == 3 and (st[PH] | st[PH + 1] << 8) >= 40):
                break
            scroll = st[SCROLL] | st[SCROLL + 1] << 8
            for v in range(10):
                w, h, _ = cards[3 + 3 * v + 2]
                top = (w + lay["R_BBODY"]) * 8 - scroll
                if not (-16 <= top and top + 16 <= 144):
                    continue
                row = (w + lay["R_BBODY"]) & 31
                ids = bytes(pb.memory[0x9800 + row * 32 + c] for c in range(20))
                s = stat[v]
                s["frames"] += 1
                if s["rows"] == [] or s["rows"][-1] != ids:
                    s["rows"].append(ids)
                    s.setdefault("log", []).append((s["frames"], top))
                    s["chg"] += 1
                img = np.asarray(pb.screen.image.convert("RGB")).astype(np.int16)
                if v in prev:
                    pi, pt = prev[v]
                    # (the body box moves 1 px per 2 frames with the scroll: compare in the card's own coordinates)
                    d = pt - top
                    if d == 0:
                        s["px"] += int((img[max(top, 0):top + 16] != pi[max(top, 0):top + 16]).any(axis=2).sum())
                prev[v] = (img, top)
                if a.gifs and n % 2 == 0:
                    frames[v].append(Image.fromarray(img.astype(np.uint8)))
    print("%-13s %7s %6s %9s" % ("boss", "frames", "poses", "px/steady"))
    for v in range(10):
        s = stat[v]
        print("%-13s %7d %6d %9d   (%.1f s on screen, one pose change every %.0f frames)" % (NAMES[v], s["frames"], s["chg"] - 1, s["px"], s["frames"] / 60.0, s["frames"] / max(1, s["chg"] - 1)))
    if a.verbose:
        for v in range(10):
            print(NAMES[v], "changes at (frame on screen, body top y):", stat[v].get("log"))
    if a.gifs:
        out = Path(a.gifs)
        out.mkdir(parents=True, exist_ok=True)
        for v in range(10):
            fr = [f.resize((320, 288), Image.NEAREST) for f in frames[v]]
            if fr:
                fr[0].save(out / f"boss_{v}.gif", save_all=True, append_images=fr[1:], duration=33, loop=0)


if __name__ == "__main__":
    main()
