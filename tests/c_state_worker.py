#!/usr/bin/env python3
"""One scenario of the timing-independent asm/C check on ONE ROM (GB_ROM, set by the caller): the per-game-step states, pickled.

    GB_ROM=build/game-c.gb python3 tests/c_state_worker.py <scenario> <dmg|cgb> <0|1 double speed> <out.pkl>
"""
import os
import pickle
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c_state_rig as R           # noqa: E402  (imports conftest, which reads GB_ROM)
import c_state_scen as S          # noqa: E402
from conftest import double_speed  # noqa: E402

R.install()
name, model, ds, out = sys.argv[1], sys.argv[2], sys.argv[3] == "1", sys.argv[4]
if ds and model == "cgb":
    with double_speed():
        t = S.SCENARIOS[name](model)
else:
    t = S.SCENARIOS[name](model)
with open(out, "wb") as f:
    pickle.dump({"names": t.names, "snaps": t.snaps}, f)
for tw in R.TWINS:
    try:
        tw.stop()
    except Exception:
        pass
print("ok", name, model, ds, len(t.snaps))
