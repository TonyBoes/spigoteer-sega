"""Check that the pipeline still reproduces the frozen snapshot (assets/smap) pixel for pixel, and write the baseline renders."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ctx
from PIL import Image

M = ctx.M
for k, f in (("px_c", "world_c.png"), ("px_d", "world_d.png")):
    im = Image.open(ctx.ROOT / "assets/smap" / f)
    d = list(im.getdata())
    w = ctx.CW * 8
    wd = M.W.WORLD if k == "px_c" else M.W.WORLD_DMG
    diff = [(i % w, i // w) for i, v in enumerate(d) if wd.px[i // w][i % w] != v]
    print(f, "differs in", len(diff), "pixels", diff[:10])
M.render(True).save(ctx.OUT / "base_c.png")
M.render(False).save(ctx.OUT / "base_d.png")
