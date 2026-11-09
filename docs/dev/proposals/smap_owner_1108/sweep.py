"""python3 -I sweep.py FLAGS ENVVAR v1,v2,... [x0 y0 x1 y1]  : runs measure.py for each value of ENVVAR (e.g. OWNER_SHIFT) with OWNER=FLAGS and prints a one-line summary each."""
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[3] / "out" / "owner1108"
flags, var, vals = sys.argv[1], sys.argv[2], sys.argv[3].split(",")
box = sys.argv[4:8]
KEYS = ("dmg_path_windows_worst", "dmg_worst_21x19", "dmg_worst_22x20", "pal_worst_21x19", "pal_windows_over_8", "color_ids", "dmg_tiles", "table_entries")
for v in vals:
    tag = f"{flags.replace(',', '')}_{var}{v}"
    env = dict(os.environ, OWNER=flags, **{var: v})
    r = subprocess.run([sys.executable, "-I", str(HERE / "measure.py"), tag] + box, env=env, capture_output=True, text=True)
    if r.returncode:
        print(v, "FAILED", r.stderr[-300:])
        continue
    d = json.loads((OUT / f"numbers_{tag}.json").read_text())
    print(var, v, {k: d[k] for k in KEYS})
