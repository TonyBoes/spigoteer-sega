"""Round 4 | round 5 sheet from the two scratch-ROM capture sets (picture rows), Color over DMG, x3, plus 1x strips.
Preview only (crops and nearest-neighbour scaling; tools/dev/contact_sheet.py lays it out).   make_r5_sheet.py OUT.png"""
import subprocess, sys
from pathlib import Path
from PIL import Image

T = Path(__file__).resolve().parent
TOWN = T.parent
REPO = T.parents[2]
IN = TOWN / "sheet_in_r5"
IN.mkdir(exist_ok=True)
R2, R3 = TOWN / "cap_r4", TOWN / "cap_r5"
PAGES = [("INTRO p1", "INTRO_00"), ("INTRO p11", "INTRO_10"), ("FINALE p1", "FINALE_A_00"), ("CREDITS p1", "CREDITS_00")]
crop = lambda p: Image.open(p).convert("RGB").crop((0, 0, 160, 104))


def save(im, name):
    p = IN / name
    im.save(p)
    return p


items = []
for m, mm in (("cgb", "Color"), ("dmg", "DMG")):
    for tag, root in (("round 4", R2), ("round 5", R3)):
        s = Image.new("RGB", (4 * 168 - 8, 104), (40, 40, 40))
        for i, (_, f) in enumerate(PAGES):
            s.paste(crop(root / m / f"{f}.png"), (i * 168, 0))
        items.append((f"1x {tag} {mm}", save(s, f"strip_{tag[-1]}_{m}.png")))
for lab, f in PAGES:
    for m, mm in (("cgb", "Color"), ("dmg", "DMG")):
        for tag, root in (("round 4", R2), ("round 5", R3)):
            im = crop(root / m / f"{f}.png")
            items.append((f"{lab} {tag} {mm} x3", save(im.resize((480, 312), Image.NEAREST), f"{f}_{tag[-1]}_{m}3.png")))
args = [sys.executable, str(REPO / "tools/dev/contact_sheet.py"), sys.argv[1], "--scale", "1", "--cols", "2",
        "--title", "Town round 4 | round 5 (scratch ROM captures, picture rows): Color over DMG"]
args += [f"{l}={p}" for l, p in items]
print(subprocess.run(args, capture_output=True, text=True).stdout.strip())
