"""python3 -I measure_pass.py OUTDIR   (SMAP_TEA_PASS=1 for the pass): the stage 1 measure.py on the integrated map, with the teahouse pass swapped in when the env var is set."""
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import swap  # noqa: E402,F401
sys.argv = [str(HERE.parent / "smap_import" / "measure.py")] + sys.argv[1:]
runpy.run_path(sys.argv[0], run_name="__main__")
