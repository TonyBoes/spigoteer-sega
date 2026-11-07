"""Dumps the round-3 mountain and stadium pieces (typed grids of docs/dev/proposals/smap_venue_redesign3/src) over their biome's ground as JSON scenes that anim.py loads:
{name: {"px": rows of index strings, "pal": cell palette names (rows), "colors": {palette: [4 rgb]}, "origin": [x, y] of the piece in the scene (px)}}.
Run (plain python, not -I, the round-3 modules import each other):  python3 r3dump.py OUT.json
Only reads the typed pieces; nothing is drawn here."""
import json
import sys
from pathlib import Path

R3 = Path(__file__).resolve().parents[1] / "smap_venue_redesign3" / "src"
sys.path.insert(0, str(R3))
import common as C  # noqa: E402
import mountain_a3  # noqa: E402
import park_a3  # noqa: E402

MARGIN = 6
out = {}
for name, m in (("mountain", mountain_a3), ("stadium", park_a3)):
    c = m.build()
    cs = C.cells(c)
    cw, ch = c.w // 8, c.h // 8
    gp = C.BIOME[m.BIOME][0]
    px = [[0] * ((cw + 2 * MARGIN) * 8) for _ in range((ch + 2 * MARGIN) * 8)]
    pal = []
    for j in range(-MARGIN, ch + MARGIN):
        row = []
        for i in range(-MARGIN, cw + MARGIN):
            if (i, j) in cs and cs[(i, j)][0] != C.BLANK:
                t, p = cs[(i, j)]
                p = C.W.MERGE.get(p, p)
            else:
                t, p = C.ground_cell(m.BIOME, m.AT[0] + i, m.AT[1] + j), gp
            row.append(p)
            for y in range(8):
                for x in range(8):
                    px[(j + MARGIN) * 8 + y][(i + MARGIN) * 8 + x] = int(t[y][x])
        pal.append(row)
    names = sorted({p for r in pal for p in r})
    out[name] = {"px": ["".join(map(str, r)) for r in px], "pal": pal, "colors": {n: [list(map(int, col)) for col in C.P.get(n)] for n in names},
                 "origin": [MARGIN * 8, MARGIN * 8], "biome": m.BIOME}
Path(sys.argv[1]).write_text(json.dumps(out))
print({k: (len(v["px"][0]), len(v["px"])) for k, v in out.items()})
