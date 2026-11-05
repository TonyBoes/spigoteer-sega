"""The phone-sized sheet: the two Color maps at 1x and the five screens at x3 side by side, through tools/dev/contact_sheet.py."""
import subprocess
from pathlib import Path

from PIL import Image

R3 = Path(__file__).resolve().parents[1]
TMP = Path("/tmp/claude-1000/-workspace/64761c6b-46f6-4217-a6f1-457b4de3152f/scratchpad/w")
items = []
for st in ("early", "late"):
    im = Image.open(R3 / f"map_{st}_cgb_x2.png")
    p = TMP / f"m1_{st}.png"
    im.resize((im.width // 2, im.height // 2), Image.NEAREST).save(p)
    items.append(f"{st} map={p}")
for name, label in (("town_early", "town"), ("saloon_desert", "TAPS"), ("igloo_edge", "igloo"), ("space_corner", "space"), ("cow_east", "chrome cow")):
    items.append(f"{label}={R3 / f'view_{name}_x3.png'}")
cs = R3.parents[4] / "tools" / "dev" / "contact_sheet.py"
subprocess.run(["python3", str(cs), str(R3 / "sheet.png"), "--scale", "1", "--cols", "3", "--title", "Story map round 4 (maps x1, screens x3, Color over DMG)"] + items, check=True)
