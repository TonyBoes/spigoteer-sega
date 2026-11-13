"""GUIDE ONLY (never delivered, never read by the build): a rough 2/3 box reduction of each whole boss (2 pixels per 3, both ways), printed beside the
figure so the artist can redraw it by hand into options_b.txt. Majority colour per box, ties to the darker. usage: guide_scaffold.py [name] [scale]"""
import sys
from pathlib import Path
import rp_common as c

build = Path(c.ROOT / "build")
G = ".-+#"
only = sys.argv[1:2] or c.BOSSES
for n in only:
    s = float(sys.argv[2]) if len(sys.argv) > 2 else 2 / 3
    rows, pal = c.full_boss(build, n)
    x0, x1, y0, y1 = c.bbox(rows)
    fig = [r[x0:x1 + 1] for r in rows[y0:y1 + 1]]
    h, w = len(fig), len(fig[0])
    W, H = round(w * s), round(h * s)
    out = []
    for oy in range(H):
        ya, yb = oy / s, (oy + 1) / s
        line = ""
        for ox in range(W):
            xa, xb = ox / s, (ox + 1) / s
            cnt = [0, 0, 0, 0]
            for y in range(int(ya), min(h, int(yb + 0.999))):
                for x in range(int(xa), min(w, int(xb + 0.999))):
                    ov = (min(y + 1, yb) - max(y, ya)) * (min(x + 1, xb) - max(x, xa))
                    cnt[fig[y][x]] += max(ov, 0)
            best = max(range(4), key=lambda v: (round(cnt[v], 2), v))
            line += G[best]
        out.append(line)
    print(f"== {n}: figure {w}x{h} -> {W}x{H}")
    ruler = "".join(str(i % 10) for i in range(w))
    print("   " + ruler)
    for i in range(max(h, H)):
        a = "".join(G[v] for v in fig[i]) if i < h else ""
        b = out[i] if i < H else ""
        print(f"{i:2d} {a.ljust(w + 2)} {b}")
