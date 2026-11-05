"""Runs the skill's tiled_preview.py on every patch from tilepatch.py and stacks the previews into one sheet (previews only)."""
import subprocess
import sys
from pathlib import Path

from PIL import Image

SRC = Path(sys.argv[1])
SCRIPT = Path.home() / ".claude/skills/gb-pixel-art/scripts/tiled_preview.py"
outs = []
for p in sorted(SRC.glob("*.png")):
    if p.name.startswith("prev_"):
        continue
    o = SRC / f"prev_{p.name}"
    r = subprocess.run(["python3", str(SCRIPT), str(p), "--repeat", "4", "--scale", "2", "--out", str(o)], capture_output=True, text=True)
    print(p.name, r.returncode, r.stdout.strip()[:100], r.stderr.strip()[:100])
    outs.append(o)
ims = [Image.open(o) for o in outs]
w = max(i.width for i in ims)
cols = 3
rows = (len(ims) + cols - 1) // cols
cw, ch = w, max(i.height for i in ims)
sheet = Image.new("RGB", (cols * (cw + 6), rows * (ch + 6)), (40, 40, 40))
for k, im in enumerate(ims):
    sheet.paste(im, ((k % cols) * (cw + 6), (k // cols) * (ch + 6)))
sheet.save(SRC / "tiled_sheet.png")
print(sheet.size)
