"""python3 -I render.py TAG   (env OWNER=... as ctx.py): writes out/owner1108/TAG_c.png and TAG_d.png, the whole map in Color and DMG, 1x, and lists what the world builder rejected."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ctx

tag = sys.argv[1]
M, W = ctx.M, ctx.W
M.render(True).save(ctx.OUT / f"{tag}_c.png")
M.render(False).save(ctx.OUT / f"{tag}_d.png")
for name in ("bad", "BAD"):
    for w in (W.WORLD, W.WORLD_DMG):
        b = getattr(w, name, None)
        if b:
            print("rejected pieces:", name, b)
print("stops:", {k: v for k, v in W.STOPS.items() if k in ("town", "saloon")}, "legs:", {k: v for k, v in W.LEGS.items() if "town" in k})
