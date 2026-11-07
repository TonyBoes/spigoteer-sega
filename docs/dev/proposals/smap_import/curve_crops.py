"""python3 curve_crops.py TAG OUTDIR  (env SMAP_CURVE=24|32|40|56|80|96|120|fit, SMAP_STADIUM_BUSH_X=40 for r32 and up as mapctx.py): writes the crops of one configuration (Q115):
  TAG_stadium_close_{color,dmg}.png   the stadium gate bend (cells 0..7 x 9..17) at x6
  TAG_stadium_ctx_{color,dmg}.png     it in context (cells 0..15 x 8..23) at x3
  TAG_big0_{color,dmg}.png, TAG_big1_{...}.png   the two biggest bends: (37, 28) NE (cells 21..38 x 27..44) and (0, 45) NW (cells 0..13 x 44..58), x4
  TAG_whole_{color,dmg}.png           the whole map at x2
Only reads; writes under OUTDIR."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mapctx as M  # noqa: E402

tag, out = sys.argv[1], Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
for cgb in (True, False):
    n = "color" if cgb else "dmg"
    M.render(cgb, (0, 9, 8, 18), 6).save(out / f"{tag}_stadium_close_{n}.png")
    M.render(cgb, (0, 8, 16, 24), 3).save(out / f"{tag}_stadium_ctx_{n}.png")
    M.render(cgb, (21, 27, 39, 45), 4).save(out / f"{tag}_big0_{n}.png")
    M.render(cgb, (0, 44, 14, 58), 4).save(out / f"{tag}_big1_{n}.png")
    M.render(cgb, scale=2).save(out / f"{tag}_whole_{n}.png")
if hasattr(M, "CURVE_LAID"):
    print(tag, "laid", [(b, r) for b, r, _ in M.CURVE_LAID])
    print(tag, "skipped", [(b, w[0]) for b, w in M.CURVE_SKIPPED])
