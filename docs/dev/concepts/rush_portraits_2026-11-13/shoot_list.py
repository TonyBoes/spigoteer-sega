"""Screenshots of the Boss Rush list in a real ROM (PyBoy, DMG and CGB), one PNG per boss: OUTDIR/<model>_<k>.png.

    GB_ROM=out/b_rushA/spigoteer-unlocked.gb python3 shoot_list.py OUTDIR      (run from the worktree root)

Uses the test suite's own helpers (tests/test_rush.py to_list / tap), so it drives the real menus. Writes nothing but the PNGs.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tests"))
os.chdir(ROOT)
import test_rush as T   # noqa: E402
from test_scores import booted   # noqa: E402

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
for model in ("dmg", "cgb"):
    with T.to_list(booted(model)) as gb:
        for k in range(len(T.BUILT)):
            gb.run(14)
            gb.screenshot(out / f"{model}_{k}.png")
            T.tap(gb, "right")
print("shot", out)
