"""Prepare the scaled inputs and build the concept folder's contact sheets with tools/dev/contact_sheet.py (convert + preview only).
    make_sheets.py DEST_DIR"""
import subprocess, sys
from pathlib import Path
from PIL import Image

T = Path(__file__).resolve().parent
TOWN = T.parent
REPO = T.parents[2]
sys.path.insert(0, str(T))
from render_v2 import parse, render   # noqa: E402
import master as M                    # noqa: E402
import keys as K                      # noqa: E402

DEST = Path(sys.argv[1])
IN = TOWN / "sheet_in"
IN.mkdir(exist_ok=True)
CS = REPO / "tools/dev/contact_sheet.py"
OLD = Path("/workspace/out/story_scenes")
CAP = TOWN / "cap"
PICS = {"intro_before": ("00_INTRO_00", "INTRO_00"), "intro_a": ("00_INTRO_10", "INTRO_10"),
        "finale_a": ("21_FINALE_A_00", "FINALE_A_00"), "credits_b": ("23_CREDITS_00", "CREDITS_00")}
LABEL = {"intro_before": "INTRO p1", "intro_a": "INTRO p11", "finale_a": "FINALE p1", "credits_b": "CREDITS p1"}


def up(im, s):
    return im.resize((im.width * s, im.height * s), Image.NEAREST)


def sheet(out, items, cols, title):
    args = [sys.executable, str(CS), str(out), "--scale", "1", "--cols", str(cols), "--title", title]
    args += [f"{lab}={p}" for lab, p in items]
    print(subprocess.run(args, capture_output=True, text=True).stdout.strip())


def save(im, name):
    p = IN / name
    im.save(p)
    return p


# ---- 1. the master: one set of pixels, three palette sets (x3), and 1x ----
g = ["".join(r) for r in M.master()]
items = []
for name, kt in (("night", K.NIGHT), ("day", K.DAY), ("dawn", K.DAWN)):
    key = {c: (v[0], v[1]) for c, v in kt.items()}
    items.append((f"{name} Color x3", save(render(key, g, 3), f"m_{name}_cgb3.png")))
    items.append((f"{name} DMG x3", save(render(key, g, 3, dmg=True, grey=False), f"m_{name}_dmg3.png")))
strip = Image.new("RGB", (160 * 3 + 16, 104 * 2 + 8), (40, 40, 40))
for i, (name, kt) in enumerate((("night", K.NIGHT), ("day", K.DAY), ("dawn", K.DAWN))):
    key = {c: (v[0], v[1]) for c, v in kt.items()}
    strip.paste(render(key, g, 1), (i * 168, 0))
    strip.paste(render(key, g, 1, dmg=True, grey=False), (i * 168, 112))
items.append(("1x: night, day, dawn (Color over DMG)", save(strip, "m_strip1.png")))
sheet(DEST / "sheet_master.png", items, 2, "Town master: one set of pixels, three palette sets")

# ---- 2. the proposal set: per picture 1x in-game (scratch ROM capture), x4 Color, x4 DMG ----
items = []
for n, (_, cap) in PICS.items():
    key, pix = parse(TOWN / "pics" / f"{n}.txt")
    items += [(f"{LABEL[n]} 1x Color (ROM)", CAP / "cgb" / f"{cap}.png"), (f"{LABEL[n]} 1x DMG (ROM)", CAP / "dmg" / f"{cap}.png"),
              (f"{n} x4 Color", save(render(key, pix, 4), f"{n}_cgb4.png")),
              (f"{n} x4 DMG", save(render(key, pix, 4, dmg=True, grey=False), f"{n}_dmg4.png"))]
sheet(DEST / "sheet_pictures.png", items, 4, "Square pictures from the town master (scratch ROM, 1x) and the pictures at x4")

# ---- 3. before | after, Color over DMG, x3 (picture rows 0-12 of the ROM captures), plus 1x strips ----
crop = lambda p: Image.open(p).convert("RGB").crop((0, 0, 160, 104))
strips = {}
for tag, root in (("before", lambda m, n: OLD / m / f"{PICS[n][0]}.png"), ("after", lambda m, n: CAP / m / f"{PICS[n][1]}.png")):
    for m in ("cgb", "dmg"):
        s = Image.new("RGB", (4 * 168 - 8, 104), (40, 40, 40))
        for i, n in enumerate(PICS):
            s.paste(crop(root(m, n)), (i * 168, 0))
        strips[(tag, m)] = save(s, f"strip_{tag}_{m}.png")
items = [("1x before Color", strips[("before", "cgb")]), ("1x after Color", strips[("after", "cgb")]),
         ("1x before DMG", strips[("before", "dmg")]), ("1x after DMG", strips[("after", "dmg")])]
for n, (old, cap) in PICS.items():
    for m, mm in (("cgb", "Color"), ("dmg", "DMG")):
        items.append((f"{LABEL[n]} before {mm} x3", save(up(crop(OLD / m / f"{old}.png"), 3), f"{n}_before_{m}3.png")))
        items.append((f"{LABEL[n]} after {mm} x3", save(up(crop(CAP / m / f"{cap}.png"), 3), f"{n}_after_{m}3.png")))
sheet(DEST / "sheet_before_after.png", items, 2, "Before | after (ROM captures, picture rows): Color over DMG")

# ---- 4. the festival venue: the Pour-Off golden (unchanged) next to the day square's top, x3 ----
items = []
for m, mm in (("cgb", "Color"), ("dmg", "DMG")):
    v = Image.open(REPO / f"tests/golden/po_perfect.{m}.png").convert("RGB").crop((0, 8, 160, 48))
    f = Image.open(CAP / m / "FINALE_A_00.png").convert("RGB").crop((0, 0, 160, 72))
    items.append((f"Pour-Off venue (golden po_perfect) {mm} x3", save(up(v, 3), f"venue_{m}3.png")))
    items.append((f"FINALE square top {mm} x3", save(up(f, 3), f"finale_top_{m}3.png")))
sheet(DEST / "sheet_venue_check.png", items, 2, "Festival venue check: unchanged venue vs the day square")
