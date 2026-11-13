"""x8 DMG render of each option-B grid beside the whole figure (x4), into out/rush_prev/b_<name>.png; prints each grid's size and any problem."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw
import rp_common as c

HERE = Path(__file__).resolve().parent
build = Path(c.ROOT / "build")
out = Path(c.ROOT / "out" / "rush_prev")
out.mkdir(parents=True, exist_ok=True)


def load_b(path=HERE / "options_b.txt"):
    grids, cur = {}, None
    for ln in path.read_text().splitlines():
        if ln.startswith(";") or not ln.strip():
            continue
        if ln.startswith("@"):
            cur = ln[1:].strip()
            grids[cur] = []
        else:
            assert set(ln) <= set(".-+#"), (cur, ln)
            grids[cur].append(ln.rstrip())
    return grids


if __name__ == "__main__":
    grids = load_b()
    only = sys.argv[1:] or list(grids)
    for n in only:
        g = grids[n]
        w = max(len(r) for r in g)
        bad = [i for i, r in enumerate(g) if len(r) != w]
        print(n, "rows", len(g), "width", w, "OK" if len(g) == 16 else "NOT 16 ROWS", "ragged rows %s" % bad if bad else "")
        full, pal = c.full_boss(build, n)
        fw = len(full[0])
        S, F = 8, 4
        im = Image.new("RGB", (w * S + 16 + fw * F, 24 * F + 8), c.DMG[0])
        d = ImageDraw.Draw(im)
        for y, r in enumerate(g):
            for x, ch in enumerate(r):
                v = ".-+#".index(ch)
                d.rectangle([x * S, y * S, x * S + S - 1, y * S + S - 1], fill=c.DMG[v])
        for y, r in enumerate(full):
            for x, v in enumerate(r):
                d.rectangle([w * S + 16 + x * F, y * F, w * S + 16 + x * F + F - 1, y * F + F - 1], fill=c.DMG[v])
        im.save(out / f"b_{n}.png")
