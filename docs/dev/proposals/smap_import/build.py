"""python3 -I build.py OUTDIR   (from the repo root) : the whole stage 1 proposal in one go.
Composes the A5 generator with every approved piece (mapctx.py) and the animation items (anim_run.py), measures, renders.  Writes only under OUTDIR (default out/smap_import).
Steps: A5 scratch generators (untracked smap_layout_a5/src), the piece scenes, numbers for DMG dark / DMG light / fountain broken, renders, animation numbers."""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "out/smap_import")
PY = [sys.executable, "-I"]


def run(args, env=None):
    import os
    e = dict(os.environ, **(env or {}))
    print("+", " ".join(map(str, args)), env or "")
    subprocess.run(PY + [str(a) for a in args], check=True, env=e, cwd=ROOT)


run([ROOT / "docs/dev/proposals/smap_layout_a5/mk_src.py"])
run([ROOT / "docs/dev/proposals/smap_layout_a5/mk_a5.py"], {"SMAP_LAYOUT": "lay_A5"})
for k in ("stadium", "igloo", "mountain", "cow", "range_a", "range_b", "range_c", "range_b2", "range_c2"):
    run([HERE / "dump_scenes.py", k, HERE / "scenes" / f"{k}.json"])
for tag, env in (("light", {}), ("broken", {"SMAP_BROKEN": "1"})):
    (OUT / tag).mkdir(parents=True, exist_ok=True)
    run([HERE / "measure.py", OUT / tag], env)
for tag, env in (("A", {}), ("C", {"SMAP_BROKEN": "1"}), ("P", {"SMAP_BEFORE_1C": "1"})):
    run([HERE / "renders.py", "crops", tag, OUT / "r"], env)
run([HERE / "renders.py", "sheet", OUT / "r"])
run([HERE / "anim_run.py", OUT / "anim"])
