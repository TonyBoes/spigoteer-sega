"""Rev 4 contact sheets: today | rev 4, DMG and Color, x3. Run: python3 render_rev4.py (from anywhere). Writes rev4/*.png."""
import re, sys, os
D = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, D)
from PIL import Image, ImageDraw
import data, rev2, rev4
ROOT = os.path.abspath(os.path.join(D, "../../../.."))
OUT = os.path.join(D, "rev4"); os.makedirs(OUT, exist_ok=True)

# ---- glyph and icon tiles ('.' = colour 0 ... '#' = colour 3 of the HUD palette)
tiles = {}
for f in ("assets/tiles/bar.txt", "assets/tiles/story.txt"):
    cur = None
    for ln in open(f"{ROOT}/{f}"):
        ln = ln.rstrip("\n")
        if ln.startswith("@"): cur = ln[1:].strip().split()[0]; tiles[cur] = []
        elif cur and re.fullmatch(r"[.\-+#]{8}", ln): tiles[cur].append(ln)
# the capacity mugs: tag.txt ROOM / TAKEN, the top 8 rows (the art sits there). Sprite colours 1,2,3 (DMG OBP0: white, light grey, black) ->
# the card's colours 0,1,3 (light text, mid, dark band); transparent -> the band (3).
SPR = {".": "#", "-": ".", "+": "-", "#": "#"}
cap = {}; cur = None
for ln in open(f"{ROOT}/assets/art/boss/tag.txt"):
    ln = ln.rstrip("\n")
    if ln.startswith("@"): cur = ln[1:].strip(); cap[cur] = []
    elif cur and re.fullmatch(r"[.\-+#]{8}", ln) and len(cap[cur]) < 8: cap[cur].append("".join(SPR[c] for c in ln))
tiles["\x01"], tiles["\x02"] = cap["ROOM"], cap["TAKEN"]
PUNCT = {".": "glyph_period", ",": "glyph_comma", "!": "glyph_excl", "?": "glyph_quest", "'": "glyph_apos", "-": "glyph_hyphen", ":": "glyph_colon"}
def tile_of(c):
    if c in tiles: return tiles[c]
    if c == " ": return tiles["hud_blank"]
    return tiles[PUNCT[c]] if c in PUNCT else tiles["glyph_" + c]
# DMG: the render's shades; Color: the HUD palette of main_cold.c hud_palette (RGB15 31,29,22 / 24,20,10 / 29,20,4 / 3,2,8)
rgb = lambda r, g, b: (r * 255 // 31, g * 255 // 31, b * 255 // 31)
PAL = {"dmg": {".": (232, 240, 208), "-": (160, 176, 136), "+": (96, 112, 88), "#": (28, 40, 32)},
       "cgb": {".": rgb(31, 29, 22), "-": rgb(24, 20, 10), "+": rgb(29, 20, 4), "#": rgb(3, 2, 8)}}
OK = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,!?'-:\x01\x02")
ICONS = {"\x01", "\x02"}

def draw_row(im, row, text, col, x0=None):
    n = len(text)
    if x0 is None: x0 = (20 - n) // 2
    for i in range(20):
        t = tile_of(text[i - x0]) if 0 <= i - x0 < n else tiles["hud_blank"]
        for y, ln in enumerate(t):
            for x, ch in enumerate(ln): im.putpixel((i * 8 + x, row * 8 + y), col[ch])

def card(name, lines, prompt, mode):
    col = PAL[mode]; im = Image.new("RGB", (160, 144), col["#"]); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 159, 143], outline=(200, 168, 64))
    draw_row(im, 1, "HOW TO PLAY", col); d.line([8, 17, 151, 17], fill=(120, 130, 100))
    draw_row(im, 5, name, col); d.line([8, 53, 151, 53], fill=(120, 130, 100))
    blk = max([len(l) for l in lines if set(l) & ICONS] or [0])
    for k, l in enumerate(lines):   # an icon line: the icon lines form a left-aligned block
        draw_row(im, 7 + 2 * k, l, col, (20 - blk) // 2 if set(l) & ICONS else None)
    d.line([8, 121, 151, 121], fill=(120, 130, 100)); draw_row(im, 16, prompt, col)
    return im

# ---- today's texts, from the source
src = open(ROOT + "/src/mg_card.c").read(); cur1, cur2 = {}, {}
for m in re.finditer(r'/\* (B_[A-Z]+)\s*\*/ \{ "([^"]*)", \{ "([^"]*)", "([^"]*)", "([^"]*)", "([^"]*)" \} \}', src):
    cur1[m.group(1)] = [m.group(i) for i in range(3, 7)]
for m in re.findall(r'\{ MG_BOSS_CARD \+ (\d), \{ "([^"]*)", "([^"]*)", "([^"]*)", "([^"]*)" \} \}', src): cur2[int(m[0])] = list(m[1:])

bosses = []
for b in data.B:
    r = rev4.R4[b["key"]]
    held = r == rev4.HELD
    if r == "REV3": r = tuple(rev2.R2[b["key"]][:2])
    bosses.append(dict(key=b["key"], name=b["name"], n=b["id"] + 1, held=held, c1=cur1[b["key"]], c2=cur2[b["id"]],
                       n1=None if held else r[0], n2=None if held else r[1]))
mx = 0
for b in bosses:
    for k in ("n1", "n2"):
        for l in (b[k] or []):
            assert len(l) <= 18 and set(l) <= OK, (b["key"], l); mx = max(mx, len(l))
    assert len(b["name"]) <= 18
print("max line", mx)

S = 3; W = 160 * S; G = 12
def lab(d, x, y, s, f=(235, 235, 235)): d.text((x, y), s, fill=f)
def boss_sheet(b, mode):
    im = Image.new("RGB", (2 * W + 3 * G, 2 * (14 + 144 * S + 8) + 20), (40, 40, 40)); d = ImageDraw.Draw(im); y = 4
    lab(d, G, y, "%d. %s  (%s)" % (b["n"], b["name"], "DMG" if mode == "dmg" else "Color"), (255, 220, 120)); y += 16
    for pg in (1, 2):
        old = b["c1"] if pg == 1 else b["c2"]; new = b["n1"] if pg == 1 else b["n2"]
        last = pg == 2 or not (b["held"] or b["n2"])
        pr_old = "PRESS A" if pg == 2 else "NEXT"
        pr_new = "PRESS A" if last else "NEXT"
        lab(d, G, y, "today, page %d" % pg)
        if b["held"]: rl = "HELD: today's text, page %d" % pg
        elif new: rl = "rev 4, page %d" % pg
        else: rl = "rev 4: no page 2"
        lab(d, 2 * G + W, y, rl); y += 14
        im.paste(card(b["name"], old, pr_old, mode).resize((W, 144 * S), Image.NEAREST), (G, y))
        if b["held"]: right = card(b["name"], old, pr_old, mode)
        elif new: right = card(b["name"], new, pr_new, mode)
        else: right = Image.new("RGB", (160, 144), (40, 40, 40))
        im.paste(right.resize((W, 144 * S), Image.NEAREST), (2 * G + W, y)); y += 144 * S + 8
    return im.crop((0, 0, im.width, y))

parts = []
for b in bosses:
    pair = [boss_sheet(b, "dmg"), boss_sheet(b, "cgb")]
    im = Image.new("RGB", (pair[0].width, pair[0].height + pair[1].height), (40, 40, 40))
    im.paste(pair[0], (0, 0)); im.paste(pair[1], (0, pair[0].height))
    im.save(f"{OUT}/q_{b['n']}_{b['key'][2:].lower()}.png"); parts.append(im)
allim = Image.new("RGB", (parts[0].width, sum(p.height for p in parts)), (40, 40, 40)); y = 0
for p in parts: allim.paste(p, (0, y)); y += p.height
allim.save(f"{OUT}/all_bosses.png"); print(allim.size)
