#!/usr/bin/env python3
"""Numbers for the zoo bamboo proposals (read-only: writes only under out/).

    python3 docs/dev/proposals/smap_zoo_bamboo/measure.py DIR

DIR holds world_c.png / world_d.png (a variant).  Each variant is run through the build's own generator (tools/gen_smap_world.py main, the route-plan proof included) with the world module pointed at
DIR, into scratch output directories, and the result lines are printed: Color tiles / slots, DMG tiles, worst 21x19 and 22x20 DMG window, palettes per window, and whether the proof passed.
"""
import contextlib
import io
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tools" / "smap_world"))
sys.path.insert(0, str(ROOT / "tools"))
import world_snap as W  # noqa: E402

d = Path(sys.argv[1]).resolve()
W.ASSETS = d
cp = W.WORLD.pal
W.WORLD = W.World("world_c.png", cp)
W.WORLD_DMG = W.World("world_d.png", [r[:] for r in cp])
import gen_smap_world as G  # noqa: E402

buf = io.StringIO()
tmp = tempfile.mkdtemp(prefix="zoomeasure_", dir=str(ROOT / "out"))
try:
    with contextlib.redirect_stdout(buf):
        G.main(tmp + "/b", tmp + "/p")
    ok = "PASS"
except Exception as e:  # noqa: BLE001
    ok = "FAIL " + repr(e)
txt = buf.getvalue()
last = [ln for ln in txt.splitlines() if ln.startswith("smap world: Color")]
pw = [ln for ln in txt.splitlines() if "path windows: DMG worst" in ln]
pr = [ln for ln in txt.splitlines() if "route plan: proved" in ln]
print(d.name, ok)
print("  ", last[-1] if last else "(no summary)")
print("  ", pw[0] if pw else "")
print("  ", pr[-1] if pr else "(route plan not proved)")
