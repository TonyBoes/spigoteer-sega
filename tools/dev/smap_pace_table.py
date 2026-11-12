#!/usr/bin/env python3
"""Per-leg pace table of the DMG story-map walk (owner 11-11: the stutter): frames, px/frame, 0 px frames mid-stretch, longest run of one pace, late frames, logic p90 / worst.

    GB_ROM=out/base_game.gb GB_NOI=out/base_game.noi python3 tools/dev/smap_pace_table.py dmg     # main's ROM
    python3 tools/dev/smap_pace_table.py dmg                                                      # build/game.gb

Prints one line a leg (stop:direction), then the totals, and each leg's pace string with --strings.  The sampled pace (every emulated frame) is what the owner sees: a frame the game drops shows as a 0 px frame."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "dev"))
import smap_walk_numbers as wn  # noqa: E402
import smap_motion_check as mc  # noqa: E402

tw = wn.tw


def paces(log):
    """Sal's px per frame, one value per frame after the first (the log is one record a frame: V_LAG, frame end, logic lines, fx, fy)."""
    return [abs(b[3] - a[3]) + abs(b[4] - a[4]) for a, b in zip(log, log[1:])]


def stats(log, p=None):
    """`p`: the pace sampled on every emulated frame (smap_motion_check.walk_steps): a frame the game drops (its logic ran past the VBlank) shows as a 0 there, not in the hook's log."""
    p = p or paces(log)
    moving = [i for i, v in enumerate(p) if v]
    mid = [i for i in range(moving[0], moving[-1] + 1) if not p[i]] if moving else []
    run = best = 0
    prev = None
    for v in p[moving[0]:moving[-1] + 1] if moving else []:
        run = run + 1 if v == prev else 1
        prev = v
        best = max(best, run)
    lines = sorted(r[2] for r in log[2:])
    return dict(frames=len(p) + 1, px=sum(p), zero=len(mid), run=best, late=sum(1 for r in log if r[1] >= 154), lines=lines, p=p)


def main(argv):
    model = argv[0] if argv else "dmg"
    noi = Path(os.environ.get("GB_NOI", ROOT / "build" / "game.noi")).read_text()
    tot = dict(frames=0, px=0, zero=0, late=0)
    alll = []
    print("leg      frames  px/f   zero  run  late  p90 worst")
    for s, d in [(s, d) for s in range(11) for d in range(4) if wn.sm.EXITS[s][d] != 255]:
        st = stats(wn.walk_log(model, s, d, noi), mc.walk_steps(model, s, d))
        ln = st["lines"]
        print(f"{s:2d}:{d}    {st['frames']:6d}  {st['px'] / st['frames']:.3f}  {st['zero']:4d}  {st['run']:3d}  {st['late']:4d}  {ln[len(ln) * 9 // 10]:3d}  {ln[-1]:3d}")
        if "--strings" in argv:
            print("   ", "".join(str(min(v, 9)) for v in st["p"]))
        for k in tot:
            tot[k] += st[k]
        alll += ln
    alll.sort()
    print(f"TOTAL    {tot['frames']:6d}  {tot['px'] / tot['frames']:.3f}  {tot['zero']:4d}        {tot['late']:4d}  {alll[len(alll) * 9 // 10]:3d}  {alll[-1]:3d}")


if __name__ == "__main__":
    main(sys.argv[1:])
