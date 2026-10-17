#!/usr/bin/env python3
"""Phase classifier for a golden that no longer matches (asm pass, PLAN.md 6.2). Read-only: writes nothing under tests/golden/.

usage: golden_phase.py [--out DIR] <pytest arguments>        e.g.  golden_phase.py tests/test_boss_critic.py -k waved
       golden_phase.py --compare DIR                          classify the pictures already in DIR

Runs the tests three times with GB_PHASE_PROBE=DIR and GB_PHASE_SHIFT=0, -1, +1: every golden taken with conftest.check_golden_game
then writes the picture of the game frame the test shoots (.0), one earlier (.m1) and one later (.p1) and does not assert. (-1 is not
possible when the shot follows an until_game: that picture is then missing and the class can only be "same", "phase shift +1" or "changed".) Each picture set is compared with the stored golden:
  same           the shot at the test's game frame is the golden
  phase shift -1 / +1   the golden is the picture one game frame earlier / later: a timing shift, not a change of the picture
  changed        none of the three match: the picture itself changed (a real difference), with the bounding box of the difference
A golden shot with the old check_golden (per emulator frame) is not probed: convert it with game_frames / until_game first.
Exit 0 always (it classifies; the supervisor decides).
"""
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "tests" / "golden"


def bbox(a, b):
    if a.size != b.size:
        return "size differs"
    d = ImageChops.difference(a, b).getbbox()
    return None if d is None else f"({d[0]},{d[1]})-({d[2]},{d[3]})"


def classify(d: Path):
    rows = []
    for p0 in sorted(d.glob("*.0.png")):
        stem = p0.name[:-6]                                  # <name>.<model>
        g = GOLDEN / f"{stem}.png"
        if not g.exists():
            rows.append((stem, "new golden (no stored picture)", ""))
            continue
        ref = Image.open(g).convert("RGB")
        pic = {k: Image.open(d / f"{stem}.{k}.png").convert("RGB") for k in ("m1", "0", "p1") if (d / f"{stem}.{k}.png").exists()}
        if "0" not in pic:
            continue
        for k in ("m1", "p1"):
            pic.setdefault(k, Image.new("RGB", (1, 1)))
        if bbox(ref, pic["0"]) is None:
            rows.append((stem, "same", ""))
        elif bbox(ref, pic["m1"]) is None:
            rows.append((stem, "phase shift -1 (the golden is one game frame earlier)", bbox(ref, pic["0"])))
        elif bbox(ref, pic["p1"]) is None:
            rows.append((stem, "phase shift +1 (the golden is one game frame later)", bbox(ref, pic["0"])))
        else:
            rows.append((stem, "changed", bbox(ref, pic["0"])))
    return rows


def main(argv):
    out = ROOT / "out" / "phase"
    args = argv[1:]
    if args[:1] == ["--out"]:
        out, args = Path(args[1]), args[2:]
    if args[:1] == ["--compare"]:
        out, args = Path(args[1]), []
    elif args:
        for f in (p for k in ("m1.png", "m1.na", "0.png", "p1.png") for p in out.glob(f"*.{k}")) if out.exists() else []:
            f.unlink()
        for shift in ("0", "-1", "1"):
            env = dict(os.environ, GB_PHASE_PROBE=str(out), GB_PHASE_SHIFT=shift)
            subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *args], cwd=ROOT, env=env)
    rows = classify(out)
    if not rows:
        print("no probed goldens in", out)
    for stem, kind, box in rows:
        print(f"{stem:40s} {kind}  bbox vs golden: {box or '-'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
