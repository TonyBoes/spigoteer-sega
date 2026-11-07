"""python3 -I render.py TAG OUTDIR     (SMAP_TEA_PASS=1 for the pass; TAG = before | after): writes OUTDIR/TAG_{color,dmg}_x6.png (the teahouse picture, 12 x 7 cells at cell (24, 55))
and OUTDIR/TAG_{color,dmg}_ctx_x3.png (the map around it).  Also prints the unique DMG tile count of the picture alone and of its 12 x 7 cell box on the map."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import swap  # noqa: E402,F401
sys.path.insert(0, str(HERE.parent / "smap_import"))
import mapctx as M  # noqa: E402

tag, out = sys.argv[1], Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
for cgb, n in ((True, "color"), (False, "dmg")):
    M.render(cgb, (24, 55, 36, 62), 6).save(out / f"{tag}_{n}_x6.png")
    M.render(cgb, (14, 47, 50, 64), 3).save(out / f"{tag}_{n}_ctx_x3.png")
px, _ = M.grid(True)
dpx, _ = M.grid(False)
for name, g in (("dmg", dpx), ("color", px)):
    tiles = {tuple(tuple(g[cy * 8 + j][cx * 8:cx * 8 + 8]) for j in range(8)) for cy in range(55, 62) for cx in range(24, 36)}
    print(tag, name, "unique 8x8 tiles in the 12x7 cell box:", len(tiles))
