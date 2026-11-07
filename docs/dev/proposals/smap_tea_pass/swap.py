"""Import this BEFORE mapctx / measure to build the map with the teahouse quality pass:   SMAP_TEA_PASS=1 python3 -I ...
(`import swap` puts v_tea_pass in place of v_tea in sys.modules; without the env var nothing changes.  The default map output is untouched.)
To adopt the pass for real: copy v_tea_pass.py over tools/smap_world/v_tea.py."""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if os.environ.get("SMAP_AP") == "1":                       # the approved map, option A' (stage 1h): four long bends at r32, the other eight at r24 with trims, mountain A, all extras
    os.environ.setdefault("SMAP_CURVE", "radii")
    os.environ.setdefault("SMAP_RADII", "0,11:32!;0,45:32!;37,28:32!;63,11:32!;0,29:24!;0,63:24!;37,46:24!;50,28:24!;50,46:24!;63,29:24!;63,45:24!;63,63:24!")
    os.environ.setdefault("SMAP_BIG", "A")
    os.environ.setdefault("SMAP_STADIUM_BUSH_X", "40")
if os.environ.get("SMAP_TEA_PASS") in ("1", "v1"):          # 1 = texture pass (SMAP_TEA_TEX=full|light|none), v1 = bf8d13ff fixes only
    sys.path.insert(0, str(HERE.parents[3] / "tools" / "smap_world"))
    sys.path.insert(0, str(HERE))
    if os.environ["SMAP_TEA_PASS"] == "v1":
        import v_tea_pass_v1 as v_tea_pass
    else:
        import v_tea_pass
    sys.modules["v_tea"] = v_tea_pass
