"""Tiled previews (4 x 4 repeats) of my repeating tiles, through the skill's tiled_preview.py."""
import subprocess
import sys
from pathlib import Path

from PIL import Image

import kit
from world import PAL, DMG_SHADE

OUT = Path(__file__).resolve().parents[1] / "master" / "tiled"
OUT.mkdir(exist_ok=True)
items = {"road_H": (1, kit.ROAD["H"]), "road_V": (1, kit.ROAD["V"]), "cobble": (4, kit.COBBLE["1"]), "fog_puff": (0, kit.FOG["PA"]),
         "fog_plain": (0, kit.FOG["F"]), "fence": (3, kit.FENCE), "runway": (1, kit.RUNWAY["D"]), "bunting_A": (4, kit.BUNT["A"])}
files = []
for n, (pal, rows) in items.items():
    im = Image.new("P", (8, 8))
    im.putpalette([c for col in PAL[pal] for c in col] + [0] * (768 - 12))
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            im.putpixel((i, j), int(ch))
    p = OUT / f"{n}.png"
    im.save(p)
    files.append(p)
script = Path.home() / ".claude/skills/gb-pixel-art/scripts/tiled_preview.py"
for p in files:
    subprocess.run([sys.executable, str(script), str(p), "--repeat", "4", "--scale", "4", "--out", str(p.with_name(p.stem + "_tiled.png"))],
                   check=True)
tiles = [Image.open(p.with_name(p.stem + "_tiled.png")).convert("RGB") for p in files]
W = sum(t.width for t in tiles[:4]) + 30
sheet = Image.new("RGB", (W, tiles[0].height * 2 + 10), (40, 40, 40))
x = 0
for i, t in enumerate(tiles):
    sheet.paste(t, ((i % 4) * (t.width + 6), (i // 4) * (t.height + 6)))
sheet.save(OUT / "tiled_all.png")
print(sheet.size)
