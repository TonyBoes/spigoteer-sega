#!/usr/bin/env python3
"""Palette Merges page: the Saloon / Stadium palette-sharing moves tried on the other 8 venues, before and after.

    make atlas && python3 tools/artifacts/palette_merges/build.py

Reads the venues' palettes the way the Palette Plan does (out/atlas/data, via tools/artifacts/palette_plan/build.py) and
the art from assets/. Writes index.html and img/<id>_before.png, img/<id>_after.png here. Publish index.html with img/*.png.
"""
import html, os, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
PP = os.path.join(ROOT, "tools/artifacts/palette_plan/build.py")
SHOW = {"lumberjacks": "lodge", "chefs": "bistro", "divers": "igloo", "robots": "factory", "punks": "biker",
        "ninjas": "teahouse", "zoo": "zoo", "aliens": "space"}

# One card per proposed merge, best first. items: (art, frame, the OBJ slot it uses now); merged: colours 1-3 after.
MERGES = [
    dict(id="bistro_sal", venue="chefs", rank="Recommended", title="PIERRE, BRIE and the waiter into Sal's palette",
         frees="OBJ 3, 5, 6 · BG 3", items=[("sal", 0, 0), ("patron", 0, 3), ("patron", 1, 6), ("show", 0, 5)],
         merged=["#FFFFF6", "#F6BD8B", "#202031"],
         notes=["Like NORM at the Stadium. Their palettes are already almost Sal's.",
                "PIERRE and BRIE walk in one BG palette in Sal's colours.",
                "BRIE's skin gets a shade lighter."]),
    dict(id="tea_show", venue="ninjas", rank="Recommended", title="Taiko drummer shares SAKURA's palette",
         frees="OBJ 5", items=[("show", 0, 5), ("patron", 1, 6)], merged=["#FFEEDE", "#CD2939", "#181010"],
         notes=["Like the Saloon dancers. Same red and outline; the cream and white meet in the middle."]),
    dict(id="biker_show", venue="punks", rank="Recommended", title="The band shares BANDIT's palette",
         frees="OBJ 5", items=[("show", 0, 5), ("show", 2, 5), ("show", 4, 5), ("patron", 1, 6)],
         merged=["#F6BD94", "#4ACD4A", "#100810"],
         notes=["Both are skin, green and near-black already."]),
    dict(id="lodge_show", venue="lumberjacks", rank="Recommended", title="Sasquatch shares the full mug's palette",
         frees="OBJ 5", items=[("show", 0, 5), ("mug", 0, 1)], merged=["#F6E6C5", "#834A29", "#291010"],
         notes=["Like the Saloon: the foam goes cream, the beer a touch lighter.",
                "The fill glass, breaking glass and sparkle use the same palette."]),
    dict(id="space_xeno", venue="aliens", rank="Recommended", title="XENO shares the empty mug's palette",
         frees="OBJ 6", items=[("patron", 1, 6), ("mug", 1, 2)], merged=["#E6E6EE", "#9CA4B4", "#101018"],
         notes=["Like OBJ 2 at the Stadium. Both are greys already.",
                "He still walks in his own BG palette.",
                "Check: the Space boss also uses OBJ 2."]),
    dict(id="zoo_coco", venue="zoo", rank="Recommended", title="COCO shares the full mug's palette",
         frees="OBJ 3", items=[("patron", 0, 3), ("mug", 0, 1)], merged=["#F6D5A4", "#8B5229", "#291808"],
         notes=["Like PETE at the Stadium. Same brown and outline; the foam goes tan.",
                "He still walks in his own BG palette."]),
    dict(id="space_zorp", venue="aliens", rank="Recommended", title="ZORP shares the full mug's palette",
         frees="OBJ 3", items=[("patron", 0, 3), ("mug", 0, 1)], merged=["#F6FF9C", "#4ACD62", "#102020"],
         notes=["Same green family. ZORP gets a little paler, the drink a little yellower.",
                "He still walks in his own BG palette."]),
    dict(id="lodge_ab", venue="lumberjacks", rank="Optional", title="CEDAR and WILLOW share one palette",
         frees="OBJ 6 · BG 3", items=[("patron", 0, 3), ("patron", 1, 6)], merged=["#FFC594", "#D53129", "#291820"],
         notes=["Like DUSTY and EMMA. Same skin and red.", "WILLOW loses her navy: her dress turns near-black."]),
    dict(id="igloo_show", venue="divers", rank="Optional", title="Penguin into Sal's palette",
         frees="OBJ 5", items=[("sal", 0, 0), ("show", 0, 5)], merged=["#FFFFF6", "#F6BD8B", "#202031"],
         notes=["White and navy match. The orange beak and feet turn peach."]),
]
REJECTED = [
    ("Igloo", "IGGY and POLLY: the two parkas become the same blue."),
    ("Robot Factory", "The dancing robot and the full mug: the robot turns lime green. Dropping BOXY's enhanced look already frees OBJ 4 there."),
    ("Teahouse", "RONIN with SAKURA: his face turns white."),
    ("Chrome Cow", "The full and empty mugs hold the same three colours in a different order. Sharing would need the mug art redrawn."),
]
VENUE_NAME = {"lumberjacks": "Lumber Lodge", "chefs": "Bistro", "divers": "Igloo", "robots": "Robot Factory",
              "punks": "Chrome Cow", "ninjas": "Teahouse", "zoo": "Jungle Zoo", "aliens": "Space Lounge"}
# OBJ palettes free for new looks today (OBJ 4; the Factory's once BOXY's enhanced look goes) and after the recommended / optional merges
GAIN = [("lumberjacks", 1, 1, 1), ("chefs", 1, 3, 0), ("divers", 1, 0, 1), ("robots", 1, 0, 0), ("punks", 1, 1, 0),
        ("ninjas", 1, 1, 0), ("zoo", 1, 1, 0), ("aliens", 1, 2, 0)]


def venues():
    src = open(PP).read()
    ns = {"__file__": PP}
    argv, sys.argv = sys.argv, [PP]
    exec(compile(src[:src.index("\nS = []")], PP, "exec"), ns)
    sys.argv = argv
    return {v["key"]: v for v in ns["venues"]}


def frames(path):
    out, cur = [], []
    for l in open(path).read().splitlines():
        if l.startswith(";"):
            continue
        if not l.strip():
            if cur: out.append(cur); cur = []
        else:
            cur.append(l)
    if cur: out.append(cur)
    return out


def art(venue, kind, n):
    return frames({"patron": f"{ROOT}/assets/art/patrons/{venue}.txt", "show": f"{ROOT}/assets/approved/venues/{SHOW[venue]}_show.txt",
                   "mug": f"{ROOT}/assets/art/mug.txt", "sal": f"{ROOT}/assets/art/bartender.txt"}[kind])[n]


def h2(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def snap(h):     # the CGB's 15-bit colours
    return "#%02X%02X%02X" % tuple((c * 31 + 127) // 255 * 255 // 31 for c in h2(h))


def sprite(rows, cols, wall):
    im = Image.new("RGB", (max(len(r) for r in rows), len(rows)), h2(wall))
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            if ch in "-+#":
                im.putpixel((x, y), h2(cols["-+#".index(ch)]))
    return im


def strip(sprites, wall, path, scale=3):
    W = sum(i.width for i in sprites) + 4 * (len(sprites) + 1)
    H = max(i.height for i in sprites) + 8
    sheet = Image.new("RGB", (W, H), h2(wall))
    x = 4
    for i in sprites:
        sheet.paste(i, (x, H - 4 - i.height)); x += i.width + 4
    sheet.resize((W * scale, H * scale), Image.NEAREST).save(path)
    return W * scale, H * scale


def esc(s):
    return html.escape(str(s))


def swatch(cols):
    return '<span class="sw">%s</span>' % "".join('<i style="background:%s" title="%s"></i>' % (c, c) for c in cols)


def main():
    V = venues()
    os.makedirs(os.path.join(HERE, "img"), exist_ok=True)
    cards = []
    for m in MERGES:
        v = V[m["venue"]]
        wall = v["bg"][0][0]
        merged = [snap(c) for c in m["merged"]]
        own = [v["pal"][s][1:] for _, _, s in m["items"]]
        arts = [art(m["venue"], k, n) for k, n, _ in m["items"]]
        wb, hb = strip([sprite(a, c, wall) for a, c in zip(arts, own)], wall, os.path.join(HERE, "img/%s_before.png" % m["id"]))
        wa, ha = strip([sprite(a, merged, wall) for a in arts], wall, os.path.join(HERE, "img/%s_after.png" % m["id"]))
        uniq = []
        for (k, n, s), c in zip(m["items"], own):
            if (s, c) not in uniq:
                uniq.append((s, c))
        before_sw = "".join('<span class="pal"><b>OBJ %d</b>%s</span>' % (s, swatch(c)) for s, c in uniq)
        cards.append(f'''<article class="card" id="{m["id"]}">
  <div class="head"><span class="venue">{esc(VENUE_NAME[m["venue"]])}</span><span class="rank {m["rank"].lower()}">{m["rank"]}</span></div>
  <h2>{esc(m["title"])}</h2>
  <p class="frees">Frees <b>{esc(m["frees"])}</b></p>
  <div class="pair">
    <figure><figcaption>Before</figcaption><div class="stage"><img src="img/{m["id"]}_before.png" width="{wb}" height="{hb}" alt="Before"></div><div class="pals">{before_sw}</div></figure>
    <figure><figcaption>After</figcaption><div class="stage"><img src="img/{m["id"]}_after.png" width="{wa}" height="{ha}" alt="After"></div><div class="pals"><span class="pal"><b>Shared</b>{swatch(merged)}</span></div></figure>
  </div>
  <ul>{"".join("<li>%s</li>" % esc(n) for n in m["notes"])}</ul>
</article>''')
    rows = "".join('<tr><td>%s</td><td class="n">%d</td><td class="n">%s</td><td class="n">%s</td></tr>'
                   % (esc(VENUE_NAME[k]), a, ("+%d" % b) if b else "–", ("+%d" % c) if c else "–") for k, a, b, c in GAIN)
    rej = "".join("<li><b>%s</b> %s</li>" % (esc(a), esc(b)) for a, b in REJECTED)
    commit = os.popen("git -C %s rev-parse --short HEAD" % ROOT).read().strip()
    page = TEMPLATE.replace("{CARDS}", "\n".join(cards)).replace("{ROWS}", rows).replace("{REJ}", rej).replace("{COMMIT}", commit)
    open(os.path.join(HERE, "index.html"), "w").write(page)
    print("wrote", os.path.join(HERE, "index.html"), len(MERGES), "merges")


TEMPLATE = """<title>Spigoteer Palette Merges</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Silkscreen&family=IBM+Plex+Sans:wght@400;600&family=IBM+Plex+Mono:wght@400;600&display=swap">
<style>
/* Layout: summary table first, then one card per merge (before | after, side by side; stacked on a phone). Same look as the other review pages. */
:root {
  --ground: #f2efe7; --card: #fffdf8; --ink: #22201c; --muted: #6b6459; --rule: #dcd4c5; --amber: #a9661a;
  --good: #3f7a3a; --opt: #8a6a1c; --stage: #2a2a2e;
  --display: "Silkscreen", "IBM Plex Mono", ui-monospace, monospace;
  --body: "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, Menlo, monospace;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) { color-scheme: dark;
    --ground: #16171a; --card: #1f2125; --ink: #ebe5d9; --muted: #a39b8e; --rule: #33363b; --amber: #e6a44c; --good: #7cc274; --opt: #e0bd62; }
}
:root[data-theme="dark"] { color-scheme: dark;
  --ground: #16171a; --card: #1f2125; --ink: #ebe5d9; --muted: #a39b8e; --rule: #33363b; --amber: #e6a44c; --good: #7cc274; --opt: #e0bd62; }
html, body { background: var(--ground); color: var(--ink); }
body { font-family: var(--body); font-size: 15px; line-height: 1.55; padding-block: 24px 48px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }
.wrap { max-width: 900px; margin: 0 auto; display: grid; gap: 20px; }
h1 { font-family: var(--display); font-size: 26px; margin: 0; text-wrap: balance; }
.lede { margin: 4px 0 0; color: var(--muted); max-width: 66ch; }
.stamp { font-family: var(--mono); font-size: 12px; color: var(--muted); margin: 6px 0 0; }
h2 { margin: 0; font-size: 18px; text-wrap: balance; }
.sum { background: var(--card); border: 1px solid var(--rule); border-radius: 12px; padding: 14px 16px; display: grid; gap: 10px; min-width: 0; }
.tbl { overflow-x: auto; }
table { border-collapse: collapse; font-size: 14px; width: 100%; }
th, td { text-align: left; padding: 5px 8px; border-bottom: 1px solid var(--rule); }
th { font-weight: 600; color: var(--muted); font-size: 12px; letter-spacing: .04em; text-transform: uppercase; }
td.n, th.n { text-align: center; font-variant-numeric: tabular-nums; }
.card { background: var(--card); border: 1px solid var(--rule); border-radius: 12px; padding: 16px; display: grid; gap: 10px; min-width: 0; }
.head { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.venue { font-family: var(--display); font-size: 13px; color: var(--amber); letter-spacing: .06em; }
.rank { font-size: 12px; font-weight: 600; padding: 1px 8px; border-radius: 99px; border: 1px solid currentColor; }
.rank.recommended { color: var(--good); }
.rank.optional { color: var(--opt); }
.frees { margin: 0; font-family: var(--mono); font-size: 13px; color: var(--muted); }
.frees b { color: var(--ink); }
.pair { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
@media (max-width: 640px) { .pair { grid-template-columns: 1fr; } }
figure { margin: 0; display: grid; gap: 6px; min-width: 0; }
figcaption { font-size: 12px; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); }
.stage { background: var(--stage); border-radius: 8px; padding: 6px; overflow-x: auto; }
.stage img { display: block; max-width: none; height: auto; image-rendering: pixelated; image-rendering: crisp-edges; }
.pals { display: flex; flex-wrap: wrap; gap: 6px 12px; font-family: var(--mono); font-size: 12px; color: var(--muted); }
.pal { display: inline-flex; align-items: center; gap: 6px; }
.pal b { font-weight: 600; }
.sw { display: inline-flex; border: 1px solid var(--rule); border-radius: 4px; overflow: hidden; }
.sw i { width: 16px; height: 16px; display: block; }
.card ul, .sum ul { margin: 0; padding-left: 1.2em; display: grid; gap: 3px; max-width: 70ch; }
.sum p { margin: 0; max-width: 70ch; }
</style>

<div class="wrap">
  <header>
    <h1>Palette merges</h1>
    <p class="lede">Your Saloon and Stadium moves, tried on the other eight venues: a patron into Sal's or a mug's palette, the show into a patron's, two patrons into one. Color only; the DMG keeps its palettes.</p>
    <p class="stamp">2026-10-25 · main {COMMIT}</p>
  </header>

  <section class="sum">
    <h2>Free OBJ palettes for new looks</h2>
    <div class="tbl"><table>
      <thead><tr><th>Venue</th><th class="n">Today</th><th class="n">Recommended</th><th class="n">Optional</th></tr></thead>
      <tbody>{ROWS}</tbody>
    </table></div>
    <p>Each venue has 3 looks now. Today's free palette is OBJ 4 (at the Robot Factory, once BOXY's enhanced look is dropped). In the playfield BG 5, 6 and 7 are free, so the BG side has room for 6 looks.</p>
  </section>

{CARDS}

  <section class="sum">
    <h2>Looked at, not recommended</h2>
    <ul>{REJ}</ul>
  </section>
</div>
"""

if __name__ == "__main__":
    main()
