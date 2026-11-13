"""GUIDE ONLY (never delivered, never read by the build): lists the rows and columns of a boss's whole figure that differ least from a neighbour (candidates for
deleting by hand), and previews a deletion the artist chose: seam.py NAME [rows=a,b,c] [cols=x,y,z]. The artist then retypes and cleans the result into options_b.txt."""
import sys
from pathlib import Path
import rp_common as c

build = Path(c.ROOT / "build")
G = ".-+#"
n = sys.argv[1]
args = dict(a.split("=") for a in sys.argv[2:])
rows, pal = c.full_boss(build, n)
x0, x1, y0, y1 = c.bbox(rows)
fig = [r[x0:x1 + 1] for r in rows[y0:y1 + 1]]
h, w = len(fig), len(fig[0])
if "rows" not in args and "cols" not in args:
    print(f"{n}: figure {w}x{h}")
    print("   " + "".join(str(i % 10) for i in range(w)))
    for i, r in enumerate(fig):
        d = sum(1 for x in range(w) if i and fig[i - 1][x] != r[x])
        print(f"{i:2d} {''.join(G[v] for v in r)}  diff-above {d}")
    print("col diffs vs left neighbour:", [sum(1 for y in range(h) if x and fig[y][x - 1] != fig[y][x]) for x in range(w)])
else:
    dr = {int(v) for v in args.get("rows", "").split(",") if v}
    dc = {int(v) for v in args.get("cols", "").split(",") if v}
    for i, r in enumerate(fig):
        if i in dr:
            continue
        print("".join(G[v] for x, v in enumerate(r) if x not in dc))
