import sys, re
sys.path.insert(0, 'tools')
from pathlib import Path
import gen_rush_portraits as g
build = Path('build')
HATDX = dict(big_tex=16, mascot=8, sasquatch=12, critic=9, yeti=9, prototype=8, duke=16, sumo=16, leo=6, mothership=12)


def hat_px(name):
    t = (build / f"boss_{name}_art.h").read_text()
    d = [int(x, 16) for x in re.search(r"boss_art_hat\[\d+\] = \{([^}]*)\}", t).group(1).split(",")]
    rows = [[0] * 8 for _ in range(16)]
    for tl in range(2):
        for y in range(8):
            lo, hi = d[tl * 16 + 2 * y], d[tl * 16 + 2 * y + 1]
            for x in range(8):
                rows[tl * 8 + y][x] = ((lo >> (7 - x)) & 1) | (((hi >> (7 - x)) & 1) << 1)
    return rows


for n in g.BOSSES:
    body, pal = g.body_pixels(build, n)
    h = hat_px(n)
    print("==", n, "w", len(body[0]), "hat_dx", HATDX[n], "hat rows with px:", [y for y, r in enumerate(h) if any(r)])
    for y, r in enumerate(h):
        if any(r):
            print("%2d" % y, " " * HATDX[n] + "".join(".-+#"[v] for v in r))
    print("body:")
    for y, r in enumerate(body):
        print("%2d" % y, "".join(".-+#"[v] for v in r))
