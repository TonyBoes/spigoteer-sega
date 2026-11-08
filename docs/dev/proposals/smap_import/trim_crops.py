"""python3 trim_crops.py TAG OUTDIR  (env SMAP_CURVE=24, SMAP_CURVE_TRIM=1 or not, as mapctx.py): x4 crops of the three bends the r24 patch cannot take without trimming art (Q115):
the factory yard (bend (50, 46)), the lodge's wood pile ((63, 29)) and the cow pen fence ((63, 45)).  With SMAP_CURVE_TRIM=1 the road is written over the art only where it covers it (the art
keeps every pixel outside the road's letters); prints how many art pixels that removes."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mapctx as M  # noqa: E402

tag, out = sys.argv[1], Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
BOXES = {"factory": (46, 40, 58, 49), "lodge": (55, 24, 64, 33), "cow": (55, 41, 64, 50)}
for cgb in (True, False):
    n = "color" if cgb else "dmg"
    for k, b in BOXES.items():
        M.render(cgb, b, 4).save(out / f"{tag}_{k}_{n}.png")
tr = getattr(M, "CURVE_TRIMMED", [])
per = {}
for (c, x, y) in tr:
    per[c] = per.get(c, 0) + 1
print(tag, "trimmed art pixels per cell", per)
