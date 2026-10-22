#!/usr/bin/env python3
"""Build the OBJ Palette Plan page (tools/artifacts/palette_plan/index.html).

    python3 tools/artifacts/palette_plan/build.py [ATLAS_DATA_DIR] [OUT_HTML]

The per-venue colours come from the graphics atlas data (`make atlas` writes out/atlas/data/). The plan itself (planned
use per slot, the ideas list, the log) is hand-kept in PLAN below: edit it when the owner decides something, rebuild,
republish (see tools/artifacts/README.md).
"""
import html
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DATA = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "out/atlas/data")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")

VENUES = [("cowboys", "The Saloon"), ("sports", "The Stadium"), ("lumberjacks", "The Lumber Lodge"), ("chefs", "The Bistro"),
          ("divers", "The Igloo"), ("robots", "The Robot Factory"), ("punks", "The Chrome Cow"), ("ninjas", "The Teahouse"),
          ("zoo", "The Jungle Zoo"), ("aliens", "The Space Lounge")]
TARGET_LOOKS = 6   # owner Q11: 6 looks per venue on Color (at least 5)

# ---- The plan (hand-kept). status: fixed | patron | free | idea ----
PLAN = [
    dict(slot=0, now="Sal, tip coin, sparkle, PERFECT cue", planned="Same", looks=0, bg="-", status="fixed",
         note="Same colours in every venue. A new patron drawn in Sal's colours could share it at no cost (idea 4)."),
    dict(slot=1, now="Full mug, fill glass, breaking glass, sparkle", planned="Same", looks=0, bg="-", status="fixed",
         note="The venue's drink colours. Could merge with OBJ 2 (idea 3)."),
    dict(slot=2, now="Empty mug, breaking glass; in boss fights also the boss's sprite parts", planned="Same", looks=0, bg="-",
         status="fixed", note="Could merge with OBJ 1 (idea 3)."),
    dict(slot=3, now="Patron A", planned="Patron A", looks=1, bg="BG 2", status="patron", note=""),
    dict(slot=4, now="Extra palette of an enhanced look: Saloon patron B, Robot Factory patron A. Unused in the other 8 venues",
         planned="Same", looks=0, bg="BG 7 (shared with the bar's keg/spout)", status="free",
         note="Free in 8 venues today, but a patron there still needs a BG palette, and none is free."),
    dict(slot=5, now="Show dancers (only during the show)", planned="Same", looks=0, bg="-", status="idea",
         note="Idle during normal play. Could hold a patron and switch to the dancers when the show starts (idea 2)."),
    dict(slot=6, now="Patron B", planned="Patron B", looks=1, bg="BG 3", status="patron", note=""),
    dict(slot=7, now="Patron C", planned="Patron C", looks=1, bg="BG 4", status="patron",
         note="Boss fights take over OBJ 7 and BG 4 for the boss, so patron C sits out boss fights."),
]

BG = [
    (0, "Bar", "Counter, wall, most of the screen"),
    (1, "HUD", "Score, lives, meters"),
    (2, "Patron A", "Walking at the bar (OBJ 3 when lifted)"),
    (3, "Patron B", "Walking at the bar (OBJ 6 when lifted)"),
    (4, "Patron C", "Walking at the bar (OBJ 7 when lifted); the boss's body in boss fights"),
    (5, "Stage A", "The venue's stage"),
    (6, "Stage B", "The venue's stage"),
    (7, "Bar B", "Keg / spout; also an enhanced look's row (Saloon, Robot Factory)"),
]

IDEAS = [
    dict(n=1, title="Use OBJ 4 where it's idle", obj="+1 in 8 venues", bg="needs 1", cost="None on the sprite side",
         verify="Which BG palette the new look walks in"),
    dict(n=2, title="Let a patron use OBJ 5 outside the show", obj="+1 in every venue", bg="needs 1",
         cost="A palette swap when the show starts and ends (VBlank, cheap)",
         verify="Whether patrons stay on screen during the show. If they do, the patron in OBJ 5 would turn dancer-coloured"),
    dict(n=3, title="Merge the full and empty mug palettes (OBJ 1 + 2)", obj="+1 in every venue", bg="no change",
         cost="Mug, glass and breaking-glass art redrawn to share 3 colours; boss sprite parts move with them",
         verify="Whether the drink colour and the empty glass still read on all 10 venues"),
    dict(n=4, title="Draw a new patron in Sal's colours (OBJ 0)", obj="+1 look, no slot spent", bg="needs a BG palette with Sal's colours",
         cost="That patron is limited to Sal's skin, white and navy", verify="Art"),
    dict(n=5, title="Free a BG palette: one stage palette instead of two (BG 5 + 6)", obj="-", bg="+1 in every venue",
         cost="Stage art redrawn to one palette per venue", verify="Stage art per venue"),
    dict(n=6, title="Free a BG palette: HUD shares the bar palette (BG 1 into BG 0)", obj="-", bg="+1 in every venue",
         cost="HUD drawn in the bar's colours", verify="HUD readability"),
]

LOG = [
    ("2026-10-21", "Owner: drop the enhanced looks (Saloon ROSIE, Robot Factory BOXY) after the next patron revision; frees OBJ 4 there."),
    ("2026-10-21", "Page started from main {commit}. Plan = current use; nothing decided yet."),
]


def load(name):
    t = open(os.path.join(DATA, name + ".js")).read()
    i = t.index("= {", t.index('ATLAS["')) + 2
    return json.loads(t[i:t.rindex("}") + 1])


def hexc(c):
    r, g, b = c & 31, (c >> 5) & 31, (c >> 10) & 31
    return "#%02X%02X%02X" % (r * 255 // 31, g * 255 // 31, b * 255 // 31)


def esc(s):
    return html.escape(str(s))


def swatches(cols, skip0=True):
    return "".join('<button type="button" class="sw" style="background:%s" data-hex="%s" title="%s"></button>' % (h, h, h)
                   for h in (cols[1:] if skip0 else cols))


venues = []
for key, name in VENUES:
    c = load("level_" + key)["cgb"]
    pal = {p["slot"]: [hexc(x) for x in p["rep"]] for p in c["pal"]["obj"]}
    bgp = {p["slot"]: [hexc(x) for x in p["rep"]] for p in c["pal"]["bg"]}
    used = {}
    for o in c["objs"]:
        for s in o["slots"]:
            used.setdefault(s, set()).add(o["kind"])
    looks = 3 + (1 if used.get(4) else 0)
    free = [s for s in range(8) if not used.get(s)]
    venues.append(dict(key=key, name=name, pal=pal, bg=bgp, used=used, looks=looks, free=free))

commit = subprocess.run(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()

# Patron names (tools/gen_credits.py PATRONS, art order A, B, C) and short descriptions where the art notes give one.
NAMES = {
    "cowboys": ["DUSTY, the cowboy", "ROSIE, the cowgirl", "HANK, the ranch hand"],
    "sports": ["PETE, the cap fan", "SERENA, the band fan", "NORM, the ref"],
    "lumberjacks": ["CEDAR, in the cap", "WILLOW, red hair", "ASH, in the green hat"],
    "chefs": ["PIERRE", "BRIE", "BASIL"],
    "divers": ["IGGY, the parka man", "POLLY, the parka girl", "MOOSE, the big parka"],
    "robots": ["BOXY", "VOLTA", "BLIP"],
    "punks": ["SPIKE, pink mohawk", "BANDIT, green bandana", "SLICK, blue quiff"],
    "ninjas": ["KAGE", "SAKURA", "RONIN"],
    "zoo": ["COCO, the monkey", "BAMBOO, the panda", "MUDDY, the hippo"],
    "aliens": ["ZORP, eye stalks", "XENO, the grey one", "GLORP, the squid"],
}
# Planned changes (owner decisions), per venue: {("OBJ"|"BG", slot): ["patron name", ...]} drawn in yellow.
PLANNED = {}
# Planned removals (struck through, yellow). Owner 2026-10-21: drop the enhanced looks (M14a) after the next patron revision.
DROP_ENHANCED = True
PATRON_SLOT = {3: 0, 6: 1, 7: 2}          # OBJ slot -> art variant A, B, C (lifted)
BG_PATRON = {2: 0, 3: 1, 4: 2}            # BG slot -> art variant (walking)


def enh_variant(v):
    """The art variant (0 A, 1 B) of the venue's enhanced look, or None."""
    u = v["used"].get(4)
    if not u:
        return None
    return 1 if any("Patron B" in k for k in u) else 0


def users(kind, v, s):
    """(patrons now, non-patrons) for one palette."""
    n = NAMES[v["key"]]
    e = enh_variant(v)
    if kind == "OBJ":
        pat = [n[PATRON_SLOT[s]]] if s in PATRON_SLOT else []
        if s == 4 and e is not None:
            pat = [n[e] + " (left half, lifted)"]
        other = {0: ["Sal", "Tip coin", "Pour sparkle", "PERFECT cue"], 1: ["Full mug", "Fill glass", "Breaking glass"],
                 2: ["Empty mug", "Breaking glass", "Boss: capacity mugs"], 5: ["Show dancers"], 7: ["Boss: hat (topper)"]}.get(s, [])
    else:
        pat = [n[BG_PATRON[s]]] if s in BG_PATRON else []
        if s == 7 and e is not None:
            pat = [n[e] + " (top row)"]
        other = {0: ["Bar, wall"], 1: ["HUD"], 4: ["Boss body"], 5: ["Stage"], 6: ["Stage"], 7: ["Keg, spout"]}.get(s, [])
    return pat, other


def pal_card(kind, v, s, cols, skip0):
    pat, other = users(kind, v, s)
    plan = PLANNED.get(v["key"], {}).get((kind, s), [])
    drop = [x for x in pat if DROP_ENHANCED and ("(left half, lifted)" in x or "(top row)" in x)]
    free = not (pat or other or plan)
    freed = not free and not [x for x in pat if x not in drop] and not other and not plan
    body = ""
    if pat or plan:
        body += '<ul class="pat">%s%s</ul>' % ("".join(('<li class="plan"><s>%s</s> (dropping)</li>' if x in drop else '<li class="now">%s</li>') % esc(x) for x in pat),
                                              "".join('<li class="plan">%s</li>' % esc(x) for x in plan))
    if other:
        body += '<ul class="oth">%s</ul>' % "".join("<li>%s</li>" % esc(x) for x in other)
    if free:
        body = '<p class="freep">Free</p>'
    if freed:
        body += '<p class="freep plan">Free once the enhanced look is dropped</p>'
    return ('<div class="pal%s"><div class="ph"><span class="slot">%s %d</span><span class="sws">%s</span></div>%s</div>'
            % (" free" if free else "", kind, s, swatches(cols, skip0), body))


S = []
w = S.append
w('<title>OBJ Palette Plan</title>')
w('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>')
w('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Silkscreen&family=IBM+Plex+Sans:wght@400;600&family=IBM+Plex+Mono:wght@400;600&display=swap">')
w("""<style>
/* Layout: venue tabs, then that venue's sprite palettes (swatches + who uses them), then its background palettes. */
:root {
  --ground: #eef0f2; --card: #fbfcfd; --ink: #1d2126; --muted: #5d6670; --rule: #d3d9df; --accent: #1f6f8b; --free: #b26a00; --now: #23824a; --plan: #9a7400;
  --display: "Silkscreen", "IBM Plex Mono", ui-monospace, monospace;
  --body: "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, Menlo, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { color-scheme: dark;
  --ground: #14171b; --card: #1c2026; --ink: #e6eaee; --muted: #9aa4ae; --rule: #313840; --accent: #5fb6d4; --free: #f0a944; --now: #6cd18f; --plan: #f2d24b; } }
:root[data-theme="dark"] { color-scheme: dark;
  --ground: #14171b; --card: #1c2026; --ink: #e6eaee; --muted: #9aa4ae; --rule: #313840; --accent: #5fb6d4; --free: #f0a944; --now: #6cd18f; --plan: #f2d24b; }
html, body { background: var(--ground); color: var(--ink); }
body { font-family: var(--body); font-size: 15px; line-height: 1.45; padding-inline: 16px; padding-block: 16px 40px; }
.wrap { max-width: 900px; margin: 0 auto; display: grid; gap: 14px; }
.tabs { display: flex; flex-wrap: wrap; gap: 6px; }
.tab { font: 600 13px var(--body); padding: 6px 10px; border-radius: 8px; border: 1px solid var(--rule); background: var(--card); color: var(--ink); cursor: pointer; }
.tab[aria-selected="true"] { background: var(--accent); border-color: var(--accent); color: var(--card); }
.tab:focus-visible, .sw:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
h1 { font-family: var(--display); font-size: 22px; margin: 4px 0 0; text-wrap: balance; }
.sum { margin: 0; color: var(--muted); font-size: 14px; }
.sum b { color: var(--ink); }
h2 { font-size: 12px; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); margin: 8px 0 0; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 8px; }
.pal { background: var(--card); border: 1px solid var(--rule); border-radius: 8px; padding: 8px 10px; display: grid; gap: 4px; }
.pal.free { border-color: var(--free); border-style: dashed; }
.ph { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.slot { font: 600 14px var(--mono); }
.pal ul { margin: 0; padding-left: 1.1em; font-size: 13px; }
.pal ul.pat { font-weight: 600; }
.pal ul + ul { border-top: 1px solid var(--rule); padding-top: 3px; margin-top: 2px; }
li.now { color: var(--now); } li.plan { color: var(--plan); }
.freep { margin: 0; color: var(--free); font-weight: 600; font-size: 13px; }
.freep.plan { color: var(--plan); }
.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 8px; }
.stat { background: var(--card); border: 1px solid var(--rule); border-radius: 10px; padding: 10px 12px; display: grid; gap: 2px; }
.stat b { font-family: var(--display); font-size: 24px; font-variant-numeric: tabular-nums; }
.stat span { color: var(--muted); font-size: 13px; }
.sw { width: 20px; height: 20px; border: 1px solid rgba(0,0,0,.35); border-radius: 3px; padding: 0; margin-left: 2px; cursor: pointer; }
.foot { color: var(--muted); font-size: 12px; margin: 6px 0 0; }
#toast { position: fixed; left: 50%; bottom: calc(16px + env(safe-area-inset-bottom, 0px)); transform: translateX(-50%); background: var(--ink); color: var(--ground); font: 13px var(--mono); padding: 6px 12px; border-radius: 6px; }
</style>""")
w('<div class="wrap"><div class="tabs" role="tablist" aria-label="Venues">')
for i, v in enumerate(venues):
    w('<button type="button" class="tab" role="tab" id="t-%s" aria-controls="p-%s" aria-selected="%s">%s</button>'
      % (v["key"], v["key"], "true" if i == 0 else "false", esc(v["name"].replace("The ", ""))))
w('</div>')
for i, v in enumerate(venues):
    ofree = [s for s in range(8) if not any(users("OBJ", v, s))]
    bfree = [s for s in range(8) if not any(users("BG", v, s))]
    looks = 3
    w('<section class="panel" role="tabpanel" id="p-%s" aria-labelledby="t-%s"%s>' % (v["key"], v["key"], "" if i == 0 else " hidden"))
    w('<h1>%s</h1><div class="stats">' % esc(v["name"]))
    w('<div class="stat"><b>%d</b><span>patrons now%s</span></div>' % (looks, " (one has an enhanced look, dropping)" if enh_variant(v) is not None else ""))
    w('<div class="stat"><b>%d</b><span>patrons wanted (Q11)</span></div>' % TARGET_LOOKS)
    pfree = ofree + ([4] if DROP_ENHANCED and enh_variant(v) is not None else [])
    w('<div class="stat"><b>%s</b><span>free sprite palettes%s</span></div>' % (
        ("%d &rarr; <span style=\"color:var(--plan)\">%d</span>" % (len(ofree), len(pfree))) if len(pfree) != len(ofree) else str(len(ofree)),
        (": " + ", ".join("OBJ %d" % x for x in pfree)) if pfree else ""))
    w('<div class="stat"><b>%d</b><span>free background palettes</span></div>' % len(bfree))
    w('</div><h2>Sprite palettes</h2><div class="grid">')
    for s in range(8):
        w(pal_card("OBJ", v, s, v["pal"].get(s, ["#000000"] * 4), True))
    w('</div><h2>Background palettes</h2><div class="grid">')
    for s in range(8):
        w(pal_card("BG", v, s, v["bg"].get(s, ["#000000"] * 4), False))
    w('</div></section>')
w('<p class="foot"><span style="color:var(--now)">Green</span>: patrons now. <span style="color:var(--plan)">Yellow</span>: planned. Click a colour to copy it. '
  'From the atlas, main %s, %s.</p>' % (esc(commit), LOG[-1][0]))
w('</div><div id="toast" role="status" aria-live="polite" hidden></div>')
w("""<script>
(function () {
  var tabs = [].slice.call(document.querySelectorAll(".tab")), toast = document.getElementById("toast"), timer;
  function pick(t, focus) {
    tabs.forEach(function (x) { var on = x === t; x.setAttribute("aria-selected", on); x.tabIndex = on ? 0 : -1;
      document.getElementById(x.getAttribute("aria-controls")).hidden = !on; });
    if (focus) t.focus();
    try { localStorage.setItem("venue", t.id); } catch (e) {}
  }
  tabs.forEach(function (t, i) {
    t.addEventListener("click", function () { pick(t); });
    t.addEventListener("keydown", function (e) {
      var d = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
      if (d) { e.preventDefault(); pick(tabs[(i + d + tabs.length) % tabs.length], true); }
    });
  });
  try { var s = localStorage.getItem("venue"); var t = s && document.getElementById(s); if (t) pick(t); else pick(tabs[0]); } catch (e) { pick(tabs[0]); }
  document.addEventListener("click", function (e) {
    var b = e.target.closest(".sw"); if (!b) return;
    var hex = b.getAttribute("data-hex");
    function shown(m) { toast.textContent = m; toast.hidden = false; clearTimeout(timer); timer = setTimeout(function () { toast.hidden = true; }, 1400); }
    try { navigator.clipboard.writeText(hex).then(function () { shown("Copied " + hex); }, function () { shown(hex); }); } catch (err) { shown(hex); }
  });
})();
</script>""")
open(OUT, "w").write("\n".join(S) + "\n")
print("wrote", OUT)
