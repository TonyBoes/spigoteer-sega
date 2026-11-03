import re, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image, ImageDraw
import data
import rev2
rev2.apply(data)   # revision 2 texts over data.py's reasons and banners

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../.."))   # repo root; run: python3 render.py
OUT = os.path.dirname(os.path.abspath(__file__))
os.makedirs(OUT, exist_ok=True)

# ---- glyphs
tiles = {}
for f in ("assets/tiles/bar.txt", "assets/tiles/story.txt"):
    cur = None
    for ln in open(f"{ROOT}/{f}"):
        ln = ln.rstrip("\n")
        if ln.startswith("@"):
            cur = ln[1:].strip().split()[0]; tiles[cur] = []
        elif cur and re.fullmatch(r"[.\-+#]{8}", ln):
            tiles[cur].append(ln)
PUNCT = {".": "glyph_period", ",": "glyph_comma", "!": "glyph_excl", "?": "glyph_quest", "'": "glyph_apos", "-": "glyph_hyphen", ":": "glyph_colon"}
def tile_of(c):
    if c == " ": return tiles["hud_blank"]
    if c in PUNCT: return tiles[PUNCT[c]]
    return tiles["glyph_" + c]
COL = {".": (232, 240, 208), "-": (160, 176, 136), "+": (96, 112, 88), "#": (28, 40, 32)}

def draw_row(im, row, text, width=20):
    n = len(text); x0 = (width - n) // 2
    for i in range(width):
        t = tile_of(text[i - x0]) if 0 <= i - x0 < n else tiles["hud_blank"]
        for y, ln in enumerate(t):
            for x, ch in enumerate(ln):
                im.putpixel((i * 8 + x, row * 8 + y), COL[ch])

def card(name, lines, prompt, title="HOW TO PLAY"):
    im = Image.new("RGB", (160, 144), COL["#"])
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 159, 143], outline=(200, 168, 64))
    draw_row(im, 1, title); d.line([8, 17, 151, 17], fill=(120, 130, 100))
    draw_row(im, 5, name); d.line([8, 53, 151, 53], fill=(120, 130, 100))
    for k, l in enumerate(lines): draw_row(im, 7 + 2 * k, l)
    d.line([8, 121, 151, 121], fill=(120, 130, 100))
    draw_row(im, 16, prompt)
    return im

def banner(l1, l2, word="BOSS"):
    im = Image.new("RGB", (160, 40), COL["#"])
    for r, t in enumerate((word, l1, l2)): draw_row(im, r + 1, t)
    ImageDraw.Draw(im).line([0, 8, 159, 8], fill=(200, 168, 64)); ImageDraw.Draw(im).line([0, 39, 159, 39], fill=(200, 168, 64))
    return im

# ---- current text, read from the source
src = open(ROOT + "/src/mg_card.c").read()
cur1, cur2 = {}, {}
for m in re.finditer(r'/\* (B_[A-Z]+)\s*\*/ \{ "([^"]*)", \{ "([^"]*)", "([^"]*)", "([^"]*)", "([^"]*)" \} \}', src):
    cur1[m.group(1)] = [m.group(i) for i in range(3, 7)]
mores = re.findall(r'\{ MG_BOSS_CARD \+ (\d), \{ "([^"]*)", "([^"]*)", "([^"]*)", "([^"]*)" \} \}', src)
for m in mores: cur2[int(m[0])] = list(m[1:])
bsrc = open(ROOT + "/src/boss.c").read()
curb = {}
for m in re.finditer(r'\[(\d)\] = \{[^"]*"([^"]*)", "([^"]*)" \}', bsrc): curb[int(m.group(1))] = (m.group(2), m.group(3))

# ---- check
OK = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,!?'-:")
mxc = mxb = 0
for b in data.B:
    for k in ("p1", "p2", "p3"):
        for l in (b[k] or []):
            assert len(l) <= 18 and set(l) <= OK, (b["key"], l); mxc = max(mxc, len(l))
    for l in b["banner"]: assert len(l) <= 20 and set(l) <= OK, l; mxb = max(mxb, len(l))
    assert len(b["name"]) <= 18
print("max card", mxc, "max banner", mxb)

# ---- text file
out = []
w = out.append
w("BOSS INSTRUCTION TEXTS: REVIEW AND PROPOSAL (2026-11-03)")
w("Branch review/boss-texts. PROPOSAL ONLY: no source was changed. Owner ask 2026-11-03: \"the text instructions for big tex seem a little incoherent. Can you review all of the boss instructions?\"")
w("")
w("LIMITS (read from the code)")
w("- Card page (src/mg_card.c, drawn by mg_card_page / line()): a title (the boss name, at most 18 letters) and EXACTLY 4 lines, on rows 7, 9, 11, 13 (a blank row between). A line is at most 18 glyphs (20 minus the frame's two columns); a longer line is drawn over the frame, as the pending-card banners were, so never use it. An empty line \"\" is allowed (it draws a blank row), but the layout looks best with all four used.")
w("- Pages: a card may have 1-3 pages (page 1 in cards[], the others in more[]). The prompt reads NEXT on all but the last page.")
w("- Glyphs on a card (mg_card.c glyph()): A-Z, 0-9, space, and . , ! ? ' - :  Nothing else (no % / + = ; \" ( ) & #). Lower case does not exist. Digits come from the HUD set.")
w("- Banner (story.c banner_build / centre): the word BOSS, then line1 and line2 of boss.c rows[], each at most 20 glyphs (the window row), the same character set (st_glyph: A-Z 0-9 . , ! ? ' - :). Header comment in boss.c says '<= 20'. Nothing else is shown at the fight start; the HOW TO PLAY card opens by itself the first time a boss appears (page 1; NEXT turns the page) and from the pause menu.")
w("- Checked all proposed lines with a script: max card line %d, max banner line %d; every character is in the set above." % (mxc, mxb))
w("")
w("WHERE BOSS INSTRUCTION TEXT LIVES")
w("1. src/mg_card.c cards[] (page 1) and more[] (page 2), card id MG_BOSS_CARD + boss id: the pause menu's HOW TO PLAY in a fight and the first-appearance card (boss.c HOOK_CARD / pause_boss_card). THE TEXT THIS REVIEW COVERS.")
w("2. src/boss.c rows[] line1/line2: the banner at the fight's start (and in BOSS RUSH). Six of ten are pinned by tests (test_boss_mascot.py:73, _mothership.py:96, _sasquatch.py:46, _duke.py:78, _sumo.py:113, _prototype.py:87): a changed banner needs its test line changed in the same commit.")
w("3. In-fight notes: boss_yeti.c show_note(\"TAP FROZEN\") (40 frames at the blow) and boss.c show_note(\"CLEAR THE BAR\"), plus the Critic's speech bubbles NO! / BAD (art). Fine as they are.")
w("4. src/rush.c: boss_name[] and venue_name[] only; the BOSS RUSH list has no instruction text.")
w("5. docs/minigames_bosses.md 3.3-3.12: design text, not shown in the game; no 'hint' lines exist as such. Its 'Suggested story text' (section 7) and docs/story.md PRE_*/POST_* scenes are story only, they teach no boss rules (the old suggested PRE_SALOON 'WATCH FOR BIG TEX' is not in the script).")
w("6. tests: tests/test_mg_card.py pins the Log Roll card only; the boss cards are not pinned by text, so the changes need no golden for them. Any card screenshot golden would show a changed card as a diff (the check list for the commit that applies this).")
w("")
w("THE WORST PROBLEMS")
w("a. 'EMPTY MUG: THROW / FULL MUG: BUSY' is a leftover of the status tag that the owner had removed on 2026-10-17. What it now means is the capacity indicator (one mug icon per hand, bright = room, dark = he holds an empty), and the words 'EMPTY' and 'FULL' are the reverse of what the player sees (a bright mug is the empty one: room). It sits on 8 of 10 second pages and so crowds out the facts that differ per boss.")
w("b. The Critic's page 2 still says 'SHAKING: SENT BACK'. There is no shaking tag any more.")
w("c. Several lines break inside a phrase ('A MUG AT HIS OLD / BAR BREAKS', 'A MUG WHILE HE / REVS STALLS HIM', 'THEN POPS UP WHERE / FOOTPRINTS BLINK'), and 'NO SUCH THING' (Sasquatch's banner) and 'NO FEAR' (Leo's) tell a first-time player nothing.")
w("d. (Revision 1 also proposed life-loss lines; the owner ruled 2026-11-03 that losing a life is normal play and needs no card line. Revision 2 has none: grep the proposed pages for LIFE, BREAK, LOSE.)")
w("e. Big Tex's banner says 'RIDES IN'; he walks in (riding a horse is listed as not built).")
w("f. Sumo's card never says how to win (ring-out at the left end). Sasquatch has no goal line.")
w("")
w("PROPOSED STRUCTURE")
w("- REVISION 2 (owner 2026-11-03: no line about losing a life). Page 1: the goal and the boss's trick. Page 2: the details and what to watch for. Every boss has 2 pages; no page uses fewer than 4 lines.")
w("- The shared icon page 3 is DROPPED: it only taught something the player can see (mugs fill up beside him) once the 'it breaks' line went. The one thing the icons say that is not obvious, 'all dark: a mug now is wasted', is kept ONLY on Big Tex's page 2, where the player first meets them:")
for l in data.ICONS: w("      " + l)
w("  The 'EMPTY MUG: THROW / FULL MUG: BUSY' lines are gone from every other boss. Page count unchanged from today (2 each), so no new more[] entries.")
w("- The banner is the goal in two lines: line 1 the boss or his trick, line 2 the number to beat.")
w("")
w("=" * 78)
for b in data.B:
    i = b["id"]
    w("%d. %s (card id MG_BOSS_CARD + %d, rows[%d])" % (i + 1, b["name"], i, i))
    w("CURRENT page 1:")
    for l in cur1[b["key"]]: w("    " + l)
    w("CURRENT page 2:")
    for l in cur2[i]: w("    " + l)
    w("CURRENT banner:   %s  /  %s" % curb[i])
    w("PROPOSED page 1:")
    for l in b["p1"]: w("    " + l)
    w("PROPOSED page 2:")
    for l in b["p2"]: w("    " + l)
    if b["p3"]:
        w("PROPOSED page 3: the shared icon page (see above)")
    else:
        w("PROPOSED page 3: none")
    w("PROPOSED banner: %s  /  %s%s" % (b["banner"][0], b["banner"][1], "   (unchanged)" if tuple(b["banner"]) == curb[i] else ""))
    w("WHY:")
    for r in b["why"]: w("  - " + r)
    w("CODE VS DOC:")
    for r in b["dis"]: w("  - " + r)
    w("-" * 78)
w("")
w("COMMON CODE VS DOC NOTES")
w("- docs/minigames_bosses.md section 3.2's table and section 1.2 are the original design; section 10 and the code are the built game. Disagreements: Sumo (step 192 not 90, start x 24 not 16, meter 6 shrinking not 12, ring-out), Mothership (meter 8 + 6 not 6, minis at x 24, passengers and the stun ray are E7), Yeti ('icy mugs 2x' is 3 px/frame), Leo (the roar is a wind, not 'walkers jump back'), Duke (no bike in the fight).")
w("- Both the status tag and the 'READY / BUSY / shaking' wording survive only in docs 2.5 as history ('gone, owner 2026-10-17'): the cards were never updated.")
w("")
w("WHAT I CHECKED AND WHAT I ASSUMED")
w("- Checked in code: each boss file's header and constants (EVERY, TELL, WAIT, STAY, KNOCK values), boss.c rows[] and the engine's rules (catch, hands, breaking, the tap, indicator in cap_draw / room_free), mg_card.c's renderer and glyph set, story.c's banner.")
w("- Assumed: the full mug passing a busy boss breaks and costs a life (doc 2.5: 'breaks at the left end (a life)'); a missed empty or returned mug costs a life at the tap end (the common rule, code comments in boss_critic.c and boss_leo.c say 'a life if it gets past'). I did not run the game to see each card; the renders are from the font tiles (assets/tiles/bar.txt and story.txt), not from SameBoy.")
w("- Unsure: whether the Critic's sparkle looks white (card says SPARKLES; the old text said GLOWS WHITE, from an art decision I could not find in code); the Critic's perfect pour needs the A button released (assumed from pour.c comments 'released in the sparkle window').")
w("- Not covered: the drink word per venue (sarsaparilla, coffee, cocoa, batteries, milk, coconuts, drinks) is used where the card has room and 'MUG' elsewhere; the banners already name the drink.")
open(OUT + "/PROPOSAL.txt", "w").write("\n".join(out) + "\n")

# ---- contact sheet (phone friendly): per boss, CURRENT left, PROPOSED right, x2; page 1, page 2, then the banners
S = 2
W = 160 * S
G = 10
sheet_w = 2 * W + 3 * G
BH = 144 * S + 14 + 6
def boss_h(b): return 2 * BH + 40 * S + 14 + 14
sheet = Image.new("RGB", (sheet_w, 30 + sum(boss_h(b) for b in data.B) + 144 * S + 60), (40, 40, 40))
d = ImageDraw.Draw(sheet)
d.text((G, 8), "Boss HOW TO PLAY: CURRENT (left) vs PROPOSED (right), x2, from the game's font tiles", fill=(235, 235, 235))
y = 30
for b in data.B:
    i = b["id"]
    d.text((G, y), b["name"], fill=(255, 220, 120)); y += 14
    pairs = [("page 1", card(b["name"], cur1[b["key"]], "NEXT"), card(b["name"], b["p1"], "NEXT")),
             ("page 2", card(b["name"], cur2[i], "PRESS A"), card(b["name"], b["p2"], "NEXT" if b["p3"] else "PRESS A"))]
    for lab, a_, p_ in pairs:
        d.text((G, y), "current " + lab, fill=(235, 235, 235)); d.text((2 * G + W, y), "proposed " + lab, fill=(235, 235, 235)); y += 14
        sheet.paste(a_.resize((W, 144 * S), Image.NEAREST), (G, y)); sheet.paste(p_.resize((W, 144 * S), Image.NEAREST), (2 * G + W, y)); y += 144 * S + 6
    d.text((G, y), "current banner", fill=(235, 235, 235)); d.text((2 * G + W, y), "proposed banner", fill=(235, 235, 235)); y += 14
    sheet.paste(banner(*curb[i]).resize((W, 40 * S), Image.NEAREST), (G, y)); sheet.paste(banner(*b["banner"]).resize((W, 40 * S), Image.NEAREST), (2 * G + W, y)); y += 40 * S + 14
sheet = sheet.crop((0, 0, sheet_w, y))
os.makedirs(ROOT + "/out", exist_ok=True)
sheet.save(ROOT + "/out/boss_text_sheet.png"); sheet.save(OUT + "/boss_text_sheet.png")
print(sheet.size)
