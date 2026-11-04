"""Crop the town kit's repeating units from the 1x day master and run the skill's tiled_preview on each.   kit_tiles.py X1DIR"""
import subprocess, sys
from pathlib import Path
from PIL import Image

TP = Path.home() / ".claude/skills/gb-pixel-art/scripts/tiled_preview.py"
d = Path(sys.argv[1])
im = Image.open(d / "master_day_cgb.png")
units = {"roof": (32, 32, 40, 48), "frieze": (72, 56, 80, 72), "bunting": (0, 0, 16, 8), "cobble": (0, 88, 8, 104),
         "awning": (32, 64, 40, 72), "shopwin": (32, 72, 48, 80)}
for n, box in units.items():
    p = d / f"kit_{n}.png"
    im.crop(box).save(p)
    r = subprocess.run([sys.executable, str(TP), "--repeat", "4", "--scale", "4", "--out", str(d / f"kit_{n}_tiled.png"), str(p)],
                       capture_output=True, text=True)
    print(n, r.returncode, (r.stdout + r.stderr).strip()[:200])
