"""python3 anim_run.py OUTDIR : runs the approved animation build (smap_anim/build.py: items.py, anim_lib.py, unchanged) on the INTEGRATED map (this folder's mapctx.py) instead of
its own A5 + scenes world.  Writes the GIFs, strips and report.json / groups.json / combined.json to OUTDIR (scratch, not for commit).
The animation art is not touched.  Two things follow the integrated map and are patched into items.py's TEXT before it runs (each replacement is asserted):
  - the airbase is pasted at cell (4, 34), not (6, 36): MTN_DX -3 becomes -5 and the airbase item's row 38 / view y / focus y move up 2 cells (16 px);
  - nothing else (every other animated cell sits where it did)."""
import sys
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
ANIM = HERE.parent / "smap_anim"
sys.path.insert(0, str(HERE))
import mapctx  # noqa: E402,F401  (cached in sys.modules: smap_anim's own mapctx.py is never imported)

sys.path.insert(1, str(ANIM))
text = (ANIM / "items.py").read_text()
DX, DY = mapctx.AT_OVERRIDE["mountain"][0] - 9, mapctx.AT_OVERRIDE["mountain"][1] - 36       # the piece was dumped for (9, 36)
for old, new in (("MTN_DX = -3 ", f"MTN_DX = {DX} "),
                 ("a5.tile(14 + MTN_DX, 38)", f"a5.tile(14 + MTN_DX, {38 + DY})"),
                 ("a5.tile(13 + MTN_DX, 38)", f"a5.tile(13 + MTN_DX, {38 + DY})"),
                 ("(14 + MTN_DX, 38)", f"(14 + MTN_DX, {38 + DY})"),
                 ("(13 + MTN_DX, 38)", f"(13 + MTN_DX, {38 + DY})"),
                 ("a5, (16, 262)", f"a5, (16, {262 + 8 * DY})"),
                 ("focus=(76, 300, 100, 316)", f"focus=(76, {300 + 8 * DY}, 100, {316 + 8 * DY})")):
    assert old in text, old
    text = text.replace(old, new)
mod = types.ModuleType("items")
mod.__file__ = str(ANIM / "items.py")
sys.modules["items"] = mod
exec(compile(text, str(ANIM / "items.py"), "exec"), mod.__dict__)

import runpy  # noqa: E402
sys.argv = [str(ANIM / "build.py"), sys.argv[1]]
runpy.run_path(str(ANIM / "build.py"), run_name="__main__")
