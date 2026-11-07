"""overlay.apply(): after `import mapctx`, lay the zen garden proposal over the scratch worlds when SMAP_TEA_GARDEN=1 (nothing else changes; the default map output is untouched)."""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def apply():
    if os.environ.get("SMAP_TEA_GARDEN") == "1":
        import garden
        import mapctx as M
        garden.apply(M)
