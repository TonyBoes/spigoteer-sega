"""python3 measure.py OUTDIR   (env SMAP_WATERDMG=light|dark, SMAP_BROKEN=1 as mapctx.py)
Runs the A5 scratch generator (smap_layout_a5/src/gen_smap_world.py: tile pools, window checks, palette checks, slot plans) on the INTEGRATED world with its palette table widened to
the palettes the map really uses, and prints / saves the numbers: DMG and Color tiles, worst 21 x 19 and 22 x 20 windows (limit 176), palettes per window (8 max, windows over),
table entries.  Writes the generator's output (a scratch engine data set, not for commit) to OUTDIR/build.  Nothing under assets/ or src/."""
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mapctx as M  # noqa: E402
import numpy as np  # noqa: E402

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
import gen_smap_world as G  # noqa: E402

used = sorted({M.W.WORLD.pal[y][x] for y in range(M.CH) for x in range(M.CW)})
A5_TABLE = list(G.PAL_NAMES)
extra = [n for n in used if n not in A5_TABLE]
G.PAL_NAMES[:] = A5_TABLE + extra                         # A5's 18 entries, then what the approved pieces add (PARK for the stadium, `base` for the airbase and the milk bar)
unused = [n for n in G.PAL_NAMES if n not in used]

import os as _os
G.TILE_MAX = int(_os.environ.get("SMAP_TILE_MAX", str(G.TILE_MAX)))          # the cell word's 10-bit tile id: 1024 in the engine; a scratch run may raise it to count a map that would not fit
cg, dm = G.Model(True), G.Model(False)
n21, at21 = dm.window_max(21, 19)
n22, at22 = dm.window_max(22, 20)
pal_grid = cg.pals[10]
worst = Counter()
over = 0
at_p = None
best = 0
for y0 in range(M.CH - 18):
    for x0 in range(M.CW - 20):
        n = len(np.unique(pal_grid[y0:y0 + 19, x0:x0 + 21]))
        worst[n] += 1
        if n > 8:
            over += 1
        if n > best:
            best, at_p = n, (x0, y0)
best22 = max(len(np.unique(pal_grid[y0:y0 + 20, x0:x0 + 22])) for y0 in range(M.CH - 19) for x0 in range(M.CW - 21))
res = {
    "water": "light" if M.LIGHT else "dark", "fountain": "broken" if M.BROKEN else "working",
    "dmg_tiles": dm.nt, "dmg_worst_21x19": n21, "dmg_worst_21x19_at": at21, "dmg_worst_22x20": n22, "dmg_worst_22x20_at": at22,
    "dmg_max_uses_22x20": dm.max_uses(22, 20),
    "color_tiles": cg.nt, "palettes_worst_21x19": best, "palettes_worst_at": at_p, "palettes_worst_22x20": best22, "windows_over_8": over,
    "palette_histogram": dict(sorted(worst.items())),
    "table_entries_used": len(used), "table_A5": len(A5_TABLE), "table_added": extra, "table_names": G.PAL_NAMES, "table_unused": unused,
    "cell_choices": [[list(c), a, b] for c, a, b in M.CHOICES],
}
try:                                                       # the full generator: slot plans, budgets (exit 1 if a window is over)
    G.main(str(out / "build"), str(out / "preview"))
    info = json.load(open(out / "build" / "smap_world.json"))
    res["color_slots"] = info["slots_c"]
    res["generator_ok"] = True
except (SystemExit, AssertionError) as _e:             # AssertionError: a tile id above 1023 reached the fog check (the Color map does not fit the 10-bit tile id)
    res["generator_ok"] = False
    res["generator_error"] = repr(_e)
json.dump(res, open(out / "numbers.json", "w"), indent=1, default=str)
print(json.dumps({k: v for k, v in res.items() if k not in ("table_names", "palette_histogram")}, default=str))
