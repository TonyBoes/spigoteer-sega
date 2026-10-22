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
free_now = sum(1 for v in venues for s in v["free"] if s == 4)
planned_free = sum(1 for p in PLAN if p["status"] == "free")

S = []
w = S.append
w('<title>OBJ Palette Plan</title>')
w('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>')
w('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Silkscreen&family=IBM+Plex+Sans:wght@400;600&family=IBM+Plex+Mono:wght@400;600&display=swap">')
w("""<style>
/* Layout: summary numbers, then the slot-by-slot plan (the working table), the background side, the ideas, the venue swatches, the log. */
:root {
  --ground: #eef0f2; --card: #fbfcfd; --ink: #1d2126; --muted: #5d6670; --rule: #d3d9df; --accent: #1f6f8b;
  --fixed: #6c7480; --patron: #2f7d4f; --free: #b26a00; --idea: #6a4fb0;
  --display: "Silkscreen", "IBM Plex Mono", ui-monospace, monospace;
  --body: "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, Menlo, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { color-scheme: dark;
  --ground: #14171b; --card: #1c2026; --ink: #e6eaee; --muted: #9aa4ae; --rule: #313840; --accent: #5fb6d4;
  --fixed: #9aa4ae; --patron: #6cc68f; --free: #f0a944; --idea: #b39cf0; } }
:root[data-theme="dark"] { color-scheme: dark;
  --ground: #14171b; --card: #1c2026; --ink: #e6eaee; --muted: #9aa4ae; --rule: #313840; --accent: #5fb6d4;
  --fixed: #9aa4ae; --patron: #6cc68f; --free: #f0a944; --idea: #b39cf0; }
html, body { background: var(--ground); color: var(--ink); }
body { font-family: var(--body); font-size: 15px; line-height: 1.5; padding-inline: 16px; padding-block: 24px 48px; }
.wrap { max-width: 980px; margin: 0 auto; display: grid; gap: 22px; }
h1 { font-family: var(--display); font-size: 26px; margin: 0; text-wrap: balance; }
h2 { font-family: var(--display); font-size: 16px; margin: 0; letter-spacing: .04em; text-wrap: balance; }
.lede { margin: 6px 0 0; color: var(--muted); max-width: 70ch; }
.stamp { font-family: var(--mono); font-size: 12px; color: var(--muted); margin: 6px 0 0; }
section { display: grid; gap: 10px; }
.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 10px; }
.stat { background: var(--card); border: 1px solid var(--rule); border-radius: 10px; padding: 12px 14px; display: grid; gap: 2px; }
.stat b { font-family: var(--display); font-size: 24px; font-variant-numeric: tabular-nums; }
.stat span { color: var(--muted); font-size: 13px; }
.rule { background: var(--card); border-left: 4px solid var(--accent); border-radius: 6px; padding: 10px 14px; margin: 0; max-width: 80ch; }
.tbl { overflow-x: auto; background: var(--card); border: 1px solid var(--rule); border-radius: 10px; }
table { border-collapse: collapse; width: 100%; font-size: 14px; }
th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--rule); vertical-align: top; }
th { font-size: 12px; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); font-weight: 600; white-space: nowrap; }
tr:last-child td { border-bottom: 0; }
td.slot { font-family: var(--mono); font-weight: 600; white-space: nowrap; }
td.num { font-variant-numeric: tabular-nums; text-align: center; }
td .note { color: var(--muted); font-size: 13px; display: block; margin-top: 3px; }
.pill { display: inline-block; font-size: 12px; font-weight: 600; padding: 1px 8px; border-radius: 99px; border: 1px solid currentColor; white-space: nowrap; }
.s-fixed { color: var(--fixed); } .s-patron { color: var(--patron); } .s-free { color: var(--free); } .s-idea { color: var(--idea); }
.sw { width: 18px; height: 18px; border: 1px solid rgba(0,0,0,.35); border-radius: 3px; padding: 0; margin: 0 2px 0 0; cursor: pointer; vertical-align: middle; }
.sw:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
.venue td.vn { white-space: nowrap; font-weight: 600; }
.cell { display: grid; gap: 3px; min-width: 64px; }
.cell small { color: var(--muted); font-size: 11px; line-height: 1.25; }
.cell.unused small { color: var(--free); font-weight: 600; }
.ideas { display: grid; gap: 10px; }
.idea { background: var(--card); border: 1px solid var(--rule); border-radius: 10px; padding: 12px 14px; display: grid; gap: 6px; }
.idea h3 { margin: 0; font-size: 15px; }
.idea dl { margin: 0; display: grid; grid-template-columns: max-content 1fr; gap: 2px 12px; font-size: 13px; }
.idea dt { color: var(--muted); } .idea dd { margin: 0; }
.log li { font-size: 14px; } .log { margin: 0; padding-left: 1.2em; }
#toast { position: fixed; left: 50%; bottom: calc(16px + env(safe-area-inset-bottom, 0px)); transform: translateX(-50%); background: var(--ink); color: var(--ground); font-family: var(--mono); font-size: 13px; padding: 6px 12px; border-radius: 6px; }
@media (prefers-reduced-motion: no-preference) { #toast { transition: opacity .2s; } }
</style>""")
w('<div class="wrap">')
w('<header><h1>OBJ palette plan</h1><p class="lede">Planning sheet for freeing Color sprite palettes so new patrons can get their own. '
  'Tell me a decision in chat and I update the plan, the counts and the log. Click any colour to copy its hex.</p>'
  '<p class="stamp">Colours from the atlas, main %s · updated %s</p></header>' % (esc(commit), LOG[-1][0]))

w('<section aria-label="Summary"><div class="stats">')
w('<div class="stat"><b>%d</b><span>patron looks per venue now (OBJ 3, 6, 7), plus an enhanced look in 2 venues</span></div>' % 3)
w('<div class="stat"><b>%d</b><span>looks per venue wanted (Q11)</span></div>' % TARGET_LOOKS)
w('<div class="stat"><b>%d of 10</b><span>venues with a sprite palette free now (OBJ 4)</span></div>' % free_now)
w('<div class="stat"><b>0</b><span>background palettes free in any venue</span></div>')
w('</div></section>')

w('<p class="rule"><strong>The catch:</strong> a patron walking along the bar is drawn in the <em>background</em>, and only becomes a sprite when '
  'it is lifted over another patron. So every patron look needs <strong>one sprite palette and one background palette</strong> with the same three colours. '
  'Freeing sprite palettes alone does not add a patron; the background side has to free one too, or the new look has to share a background palette that already has its colours.</p>')

w('<section><h2>The plan, slot by slot</h2><div class="tbl"><table><thead><tr><th>Slot</th><th>Used now</th><th>Planned</th>'
  '<th>Patron looks</th><th>BG partner</th><th>Status</th></tr></thead><tbody>')
labels = dict(fixed="Fixed", patron="Patron", free="Free / partly free", idea="Candidate")
for p in PLAN:
    w('<tr><td class="slot">OBJ %d</td><td>%s%s</td><td>%s</td><td class="num">%s</td><td>%s</td><td><span class="pill s-%s">%s</span></td></tr>' % (
        p["slot"], esc(p["now"]), ('<span class="note">%s</span>' % esc(p["note"])) if p["note"] else "", esc(p["planned"]),
        p["looks"], esc(p["bg"]), p["status"], labels[p["status"]]))
tot = sum(p["looks"] for p in PLAN)
w('<tr><td class="slot">Total</td><td colspan="2">Patron looks in the plan, per venue</td><td class="num"><strong>%d</strong></td>'
  '<td colspan="2">%d more needed for %d looks</td></tr>' % (tot, TARGET_LOOKS - tot, TARGET_LOOKS))
w('</tbody></table></div></section>')

w('<section><h2>Background palettes (each new patron needs one)</h2><div class="tbl"><table><thead><tr><th>Slot</th><th>Used for</th><th>Notes</th></tr></thead><tbody>')
for s, n, d in BG:
    w('<tr><td class="slot">BG %d</td><td>%s</td><td>%s</td></tr>' % (s, esc(n), esc(d)))
w('</tbody></table></div></section>')

w('<section><h2>Ways to free palettes</h2><p class="lede" style="margin:0">Options, not decisions. Each says what it frees on each side and what it costs.</p><div class="ideas">')
for i in IDEAS:
    w('<article class="idea"><h3>%d. %s</h3><dl><dt>Sprite side</dt><dd>%s</dd><dt>Background side</dt><dd>%s</dd><dt>Cost</dt><dd>%s</dd><dt>To check</dt><dd>%s</dd></dl></article>' % (
        i["n"], esc(i["title"]), esc(i["obj"]), esc(i["bg"]), esc(i["cost"]), esc(i["verify"])))
w('</div></section>')

w('<section><h2>Every venue, OBJ 0–7 now</h2><p class="lede" style="margin:0">Colours 1–3 of each palette (colour 0 is see-through). '
  'Orange label: nothing uses that slot during play.</p><div class="tbl"><table class="venue"><thead><tr><th>Venue</th>')
for s in range(8):
    w('<th>OBJ %d</th>' % s)
w('</tr></thead><tbody>')
short = {"Patron A (entering / leaving)": "Patron A", "Patron A (lifted)": "Patron A", "Patron A (lifted, enhanced)": "Patron A+",
         "Patron B (entering / leaving)": "Patron B", "Patron B (lifted)": "Patron B", "Patron B (lifted, enhanced)": "Patron B+",
         "Patron C (entering / leaving)": "Patron C", "Patron C (lifted)": "Patron C", "Mug: full": "full mug", "Mug: empty": "empty mug",
         "Fill glass": "fill glass", "Breaking glass": "glass", "Mug: drinking": "", "Perfect-pour sparkle": "", "PERFECT cue": "",
         "Tip coin": "coin", "Sal": "Sal", "Dancers": "dancers"}
for v in venues:
    w('<tr><td class="vn">%s</td>' % esc(v["name"]))
    for s in range(8):
        u = v["used"].get(s)
        lab = ", ".join(sorted({short.get(k, k) for k in u} - {""})) if u else "unused"
        w('<td><div class="cell%s">%s<small>%s</small></div></td>' % ("" if u else " unused", swatches(v["pal"].get(s, ["#000000"] * 4)), esc(lab)))
    w('</tr>')
w('</tbody></table></div></section>')

w('<section><h2>Log</h2><ul class="log">')
for d, t in reversed(LOG):
    w('<li><strong>%s</strong> %s</li>' % (esc(d), esc(t.format(commit=commit))))
w('</ul></section></div><div id="toast" role="status" aria-live="polite" hidden></div>')
w("""<script>
(function () {
  var toast = document.getElementById("toast"), timer;
  document.addEventListener("click", function (e) {
    var b = e.target.closest(".sw"); if (!b) return;
    var hex = b.getAttribute("data-hex");
    function shown(msg) { toast.textContent = msg; toast.hidden = false; clearTimeout(timer); timer = setTimeout(function () { toast.hidden = true; }, 1400); }
    try { navigator.clipboard.writeText(hex).then(function () { shown("Copied " + hex); }, function () { shown(hex); }); } catch (err) { shown(hex); }
  });
})();
</script>""")
open(OUT, "w").write("\n".join(S) + "\n")
print("wrote", OUT)
