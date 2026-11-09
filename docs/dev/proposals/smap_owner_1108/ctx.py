"""Shared set-up for the 11-08 owner proposals: the integrated map exactly as tools/dev/smap_snapshot.py builds it (working fountain), with the proposals switched on by env OWNER
(a comma list of flags; none = the map as frozen in assets/smap), plus helpers to render it and to compare it with the snapshot.  Read-only: writes nothing but what callers save.

  OWNER=A1 | A2        desert peaks (prop_a.py), arrangement 1 or 2
  OWNER=B1,B2,B3       the town: awning, paving, move west (owner_pre.py; OWNER_SHIFT=cells, default 10)
  OWNER=C | C2 | C3    the road-bend wedges on grass (prop_c.py); C: the whole tea house on town1@g, C2: only the two cacti dropped (west bend only), C3: the cacti dropped and the east end of the house on town1@g"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PROP = ROOT / "docs" / "dev" / "proposals"
OUT = ROOT / "out" / "owner1108"
OUT.mkdir(parents=True, exist_ok=True)
FLAGS = set(filter(None, os.environ.get("OWNER", "").replace(" ", "").split(",")))
sys.path.insert(0, str(ROOT / "tools" / "dev"))
import smap_snapshot as S  # noqa: E402

os.environ.update(S.MAP_ENV)
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(PROP / "smap_tea_pass"))
import swap  # noqa: E402,F401
sys.path.insert(0, str(PROP / "smap_import"))
if FLAGS & {"A1", "A2"}:
    os.environ["SMAP_DESERT_PIECES"] = "cacti"              # the five scattered desert peaks are not laid: prop_a.py lays the new ones
if FLAGS & {"B1", "B2", "B3", "B4"}:
    os.environ["SMAP_PRE_WORLD"] = "owner_pre"
if "B2" in FLAGS and not FLAGS & {"A1", "A2"}:
    os.environ["SMAP_SKIP_DESERT"] = "cone"                 # the paved band south of the road covers the top of the old desert peak "cone" (cells 22..24 x 31..33): it is not laid
if FLAGS & {"C", "C2", "C3"}:
    import roads_round as RR                                # the south-middle bends take the grass palette (town1@g) like the other bends (prop_c.py): C both, C2 the west one only
    for k in ((37, 46),) if "C2" in FLAGS else ((37, 46), (50, 46)):
        RR.OUTER_PAL.pop(k, None)
    RR.INNER.pop((35, 44), None)
import mapctx as M  # noqa: E402

W = M.W
CW, CH = W.CW, W.CH
if FLAGS & {"A1", "A2"}:
    import prop_a
    PLACED_A = prop_a.apply(W, M.PAL, "A1" if "A1" in FLAGS else "A2")
if FLAGS & {"C", "C2", "C3"}:
    import prop_c
    CHANGED_C = prop_c.apply(W, M.PAL, sorted(FLAGS & {"C", "C2", "C3"})[0])
if "B4" in FLAGS:
    import owner_pre
    ROUNDED_B = owner_pre.post(W)
