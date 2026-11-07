"""Import this BEFORE mapctx / measure to build the map with the teahouse quality pass:   SMAP_TEA_PASS=1 python3 -I ...
(`import swap` puts v_tea_pass in place of v_tea in sys.modules; without the env var nothing changes.  The default map output is untouched.)
To adopt the pass for real: copy v_tea_pass.py over tools/smap_world/v_tea.py."""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if os.environ.get("SMAP_TEA_PASS") == "1":
    sys.path.insert(0, str(HERE.parents[3] / "tools" / "smap_world"))
    sys.path.insert(0, str(HERE))
    import v_tea_pass
    sys.modules["v_tea"] = v_tea_pass
