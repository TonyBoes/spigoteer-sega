#!/usr/bin/env python3
"""Screenshots of the real scrolling credits (PyBoy, the ROM as built): frames at a stop's hold, per venue card, DMG and Color.

    python3 tools/dev/credits_shots.py ROM OUTDIR TAG [--venues 0,4,9] [--cards owner,patrons,boss] [--at 120] [--glide]

Writes OUTDIR/TAG_<model>_v<venue>_<card>.png (160x144). With --glide also a frame in the middle of the glide into each stop (the
roll's speed: 4 px a frame). Reads the ROM; writes only OUTDIR.  Needs tests/ on the path (conftest, gbtools).
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))

from conftest import K_BONUS, K_CREDITS, double_speed, hold_stage_anim, title_pick   # noqa: E402
from gbtools import Rom                                                            # noqa: E402
from test_flow import run_until                                                    # noqa: E402

K, ST, PH, LIVE = 61, 62, 38, 44        # struct cr_state (tests/test_credits_scroll.py)


def start(rom, model):
    if model == "cgb":
        with double_speed():
            gb = Rom(Path(rom), model)
    else:
        gb = Rom(Path(rom), model)
    gb.run(120)
    hold_stage_anim(gb)
    title_pick(gb, K_BONUS, K_CREDITS)
    run_until(gb, lambda: gb.mem("story_phase") == 8, 40)
    run_until(gb, lambda: gb.read("story_scratch", 70)[LIVE] == 1, 600)
    return gb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rom")
    ap.add_argument("outdir")
    ap.add_argument("tag")
    ap.add_argument("--venues", default="0,4,9")
    ap.add_argument("--cards", default="venue,owner,patrons,boss")
    ap.add_argument("--at", type=int, default=100, help="frames into the hold")
    ap.add_argument("--glide", action="store_true")
    ap.add_argument("--map", action="store_true", help="the CRMAP build: four cards a venue (venue, owner, patrons, boss)")
    ap.add_argument("--models", default="dmg,cgb")
    a = ap.parse_args()
    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    kinds = a.cards.split(",")
    want = {}
    kds = ("venue", "owner", "patrons", "boss") if a.map else ("owner", "patrons", "boss")
    for v in map(int, a.venues.split(",")):
        for j, kd in enumerate(kds):
            if kd in kinds:
                want[3 + len(kds) * v + j] = (v, kd)
    for model in a.models.split(","):
        with start(a.rom, model) as gb:
            done = set()
            last_k = None
            for _ in range(14000):
                gb.run(1)
                st = gb.read("story_scratch", 70)
                k, s, ph = st[K], st[ST], st[PH] | st[PH + 1] << 8
                if a.glide and s == 1 and k in want and (k, "g") not in done and ph == 24:
                    v, kd = want[k]
                    gb.image().convert("RGB").save(out / f"{a.tag}_{model}_v{v}_{kd}_in.png")
                    done.add((k, "g"))
                if s == 0 and k in want and k not in done and ph == a.at:
                    v, kd = want[k]
                    gb.image().convert("RGB").save(out / f"{a.tag}_{model}_v{v}_{kd}.png")
                    done.add(k)
                if st[ST] == 3 or (k > max(want) and len([d for d in done if not isinstance(d, tuple)]) == len(want)):
                    break
            print(model, "shots", len([d for d in done if not isinstance(d, tuple)]), "of", len(want))


if __name__ == "__main__":
    main()
