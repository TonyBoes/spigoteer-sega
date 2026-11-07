#!/usr/bin/env python3
"""Renders layout A5 with the town's fountain swapped.   python3 -I run.py OPT OUTDIR [SCRIPT]      SCRIPT = a script of the A5 proposal folder (default eval_layout.py, or probe_presnap.py); OPT = cur (A5 as approved), 1 or 2
Scratch: needs docs/dev/proposals/smap_layout_a5/src built by mk_src.py and mk_a5.py (they write the untracked world2.py, pal.py ...)."""
import os
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
A5 = ROOT / "docs" / "dev" / "proposals" / "smap_layout_a5"
opt, out = sys.argv[1], sys.argv[2]
os.environ.update(SMAP_LAYOUT="lay_A5", SMAP_FOG="none", SMAP_WATERDMG="light", SMAP_FOUNTAIN=opt)
sys.path.insert(0, str(A5 / "src"))
sys.path.append(str(ROOT / "tools" / "smap_world"))
if opt != "cur":
    sys.path.insert(0, str(HERE / "src"))
    import lay_A5
    lay_A5.VENUES["town"] = ("v_town_fx", lay_A5.VENUES["town"][1])
script = sys.argv[3] if len(sys.argv) > 3 else "eval_layout.py"
spath = HERE / script if (HERE / script).exists() else A5 / script
sys.argv = [str(spath), "lay_A5", out] if script == "metrics.py" else [str(spath), "lay_A5", "--out", out]
runpy.run_path(str(spath), run_name="__main__")
