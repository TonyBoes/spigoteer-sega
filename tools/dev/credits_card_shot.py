#!/usr/bin/env python3
"""One frame of a card of the real roll, DMG and Color: the frame where the card's row R stands at screen row ROW (the roll moves a px every 2 frames, so within 1 px).

    python3 tools/dev/credits_card_shot.py ROM BUILD_DIR OUT_DIR CARD:ROWINCARD:SCREENY [...] [--models dmg,cgb]

CARD is the card's index in the roll (0 title, 1 Spigoteer, 2 Dregs, 3 + 3 v the owner of venue v, 4 + 3 v its patrons, 5 + 3 v its boss). Writes OUT_DIR/<model>_c<CARD>.png
(160 x 144). Reads the ROM, writes only OUT_DIR."""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "tools" / "dev"))
from credits_roll_check import layout, SCROLL, ST, PH   # noqa: E402
from credits_shots import start                        # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rom")
    ap.add_argument("build")
    ap.add_argument("out")
    ap.add_argument("want", nargs="+")
    ap.add_argument("--models", default="dmg,cgb")
    a = ap.parse_args()
    lay, owners, bosses, cards = layout(Path(a.build))
    want = {}
    for s in a.want:
        c, r, y = (int(x) for x in s.split(":"))
        want[c] = cards[c][0] * 8 + r * 8 - y            # (the scroll at which the card's row r is at screen y)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for model in a.models.split(","):
        with start(a.rom, model) as gb:
            pb = gb.pb
            done = set()
            for n in range(13000):
                pb.tick(1, True)
                st = gb.read("story_scratch", 70)
                if gb.mem("story_phase") != 8 or (st[ST] == 3 and (st[PH] | st[PH + 1] << 8) >= 40):
                    break
                scroll = st[SCROLL] | st[SCROLL + 1] << 8
                for c, sc in want.items():
                    if c not in done and scroll >= sc:
                        pb.screen.image.convert("RGB").save(out / f"{model}_c{c}.png")
                        done.add(c)
                if len(done) == len(want):
                    break


if __name__ == "__main__":
    main()
