#!/usr/bin/env python3
"""Build the OBJ Palette Plan page (tools/artifacts/palette_plan/index.html).

    python3 tools/artifacts/palette_plan/build.py [ATLAS_DATA_DIR] [OUT_HTML]

The per-venue colours come from the graphics atlas data (`make atlas` writes out/atlas/data/). The plan itself (planned
use per slot, the ideas list, the log) is hand-kept in PLAN below: edit it when the owner decides something, rebuild,
republish (see tools/artifacts/README.md). The patron thumbnails go to img/ next to OUT_HTML and are published with the
page as files. The published page is wrapped in a skeleton with img{max-width:100%}, which shrinks an image in an
auto-width table cell to nothing: .pimg keeps a fixed 48 px size and max-width: none.
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
    ("2026-10-26", "OBJ 7: \"Boss: hat\" was in every venue; now each lists its own boss's topper (crest, horns, lamp...), reloaded in his colours for the fight."),
    ("2026-10-25", "Lumber Lodge: the Sasquatch shares the full mug (OBJ 1: #F6E6C5 #834A29 #291010); WILLOW shares CEDAR's palette (OBJ 3)."),
    ("2026-10-25", "Bistro: PIERRE, BRIE and the waiter use Sal's OBJ 0; PIERRE and BRIE walk in BG 2 in Sal's colours."),
    ("2026-10-25", "Igloo: the penguin uses Sal's OBJ 0."),
    ("2026-10-25", "Chrome Cow: the band shares BANDIT's OBJ 6 (#F6BD94 #4ACD4A #100810)."),
    ("2026-10-25", "Teahouse: the taiko drummer shares SAKURA's OBJ 6 (#FFEEDE #CD2939 #181010)."),
    ("2026-10-25", "Jungle Zoo: COCO shares the full mug, OBJ 1 (#F6D5A4 #8B5229 #291808)."),
    ("2026-10-25", "Space Lounge: ZORP shares the full mug, OBJ 1 (#F6FF9C #4ACD62 #102020); XENO the empty mug, OBJ 2 (#E6E6EE #9CA4B4 #101018)."),
    ("2026-10-25", "Owner: take every recommended and optional merge on the Palette Merges page."),
    ("2026-10-22", "Saloon: GUS's OBJ 3 variant cut; he spawns in OBJ 5 and 7."),
    ("2026-10-22", "Saloon DMG: EMMA replaces ROSIE (see-through pupils look wrong on DMG). EMMA's pupils are now her outline colour."),
    ("2026-10-22", "Saloon DMG: DUSTY, ROSIE (the singer) and GUS are the bank-0 looks on both systems; GUS takes the boss-overwritten slot. HANK goes to bank 1 (Color only). The DMG keeps its original palettes."),
    ("2026-10-22", "Saloon: palette variants per patron (30 recolours; correction: GUS keeps his own OBJ 7, his OBJ 6 is cut). HANK's art and OBJ 3 have colours 1 and 2 swapped."),
    ("2026-10-22", "Saloon: OBJ 6 (MABEL, ARTIE) outline darker, #303038 to #1A1A20."),
    ("2026-10-22", "Saloon names: the Prospector is GUS, the prospector; ARTIE is a priest."),
    ("2026-10-22", "Saloon: DUSTY and EMMA share OBJ 5 / BG 5 on #FFD5BD #8B5231 #221B1A; HANK keeps OBJ 3 / BG 3 alone."),
    ("2026-10-22", "Saloon: the brown-haired singer is named EMMA."),
    ("2026-10-22", "Saloon: the Outlaw is named REDD."),
    ("2026-10-22", "Saloon: OBJ 4 (ROSIE, Outlaw) is ROSIE's skin #F8D0B0, the Outlaw file's red #BB2F32, ROSIE's outline #202030."),
    ("2026-10-22", "Saloon: the Outlaw (owner's recolour, red and navy) shares ROSIE's OBJ 4 / BG 4; OBJ 7 keeps his former palette for the Prospector and Big Tex."),
    ("2026-10-21", "Saloon: ARTIE (owner set 2 C, the bald old prospector) shares MABEL's palette on OBJ 6 / BG 6."),
    ("2026-10-21", "Saloon names: patron B is now MABEL (grey hair, black lace shawl); ROSIE is now the red-dress singer on OBJ 4."),
    ("2026-10-21", "Saloon: ROSIE redrawn by the owner (grey hair, dark dress): skin #FFCCAA, grey #A9A9A9, dark #303038 (stored as #FFCEAD, #ADADAD in 15-bit)."),
    ("2026-10-21", "Saloon: ROSIE's grey is the darker #303038."),
    ("2026-10-21", "Saloon: ROSIE's colour 3 to dark grey #4C4C58, so her hair is grey (her outline too); her pink shawl and dress stay."),
    ("2026-10-21", "Saloon: the brown-haired singer (owner's concept) on OBJ 5 / BG 5 with her own palette."),
    ("2026-10-21", "Saloon: OBJ 1 colour 1 to #FFE6CD and the show dancers share OBJ 1; OBJ 5 free."),
    ("2026-10-21", "Saloon: the Saloon singer (owner's concept, v3) on OBJ 4 / BG 4 with her own palette; the wall colour shows through at her eyes."),
    ("2026-10-21", "Saloon: the Prospector shares the Outlaw's palette on OBJ 7 / BG 7 (was his own on OBJ 4); OBJ 4 and BG 4 free."),
    ("2026-10-21", "Saloon: the Outlaw (original round 1) on OBJ 7 / BG 7 with his own palette; Big Tex's body and hat take the Outlaw's palette (replaces the reserved Big Tex-coloured patron)."),
    ("2026-10-21", "Saloon: the Prospector (saved candidate Prospector 1) on OBJ 4 / BG 4 with his own palette."),
    ("2026-10-21", "Saloon: a reserved patron in Big Tex's body colours on OBJ 7 / BG 7 (his fight loads the same colours there, so this patron can stay in it)."),
    ("2026-10-21", "Saloon: HANK's hat to #FFE6CD and DUSTY shares HANK's palette, in slot 3 (OBJ 3 / BG 3) so neither sits out boss fights; OBJ 7 and BG 7 are the boss's alone."),
    ("2026-10-21", "Fix: the Saloon's keg / spout already use the bar palette (BG 0), so they do not move to BG 1 there; BG 1 is free in the Saloon's playfield."),
    ("2026-10-21", "Owner: where possible a patron's BG palette number matches its OBJ number (A 3/3, B 6/6, C 7/7; Stadium PETE 1/1, SERENA 6/6, reserved 2/2). The boss body pairs with the topper's OBJ 7 in BG 7."),
    ("2026-10-21", "Stadium: BG 0 takes BG 1's palette (the keg / spout's; only its darkest colour differs) and the keg / spout share BG 0; BG 1 free in the playfield."),
    ("2026-10-21", "Every venue: the keg / spout palette moves from BG 7 to BG 1 in the playfield; BG 7 is free there."),
    ("2026-10-21", "Stadium: the tan is the lighter #FFE6CD (owner pick over #FFD5AC), for OBJ 1 and OBJ 2."),
    ("2026-10-21", "Stadium: OBJ 1 and OBJ 2 white pushed toward tan; PETE and the cheerleaders share OBJ 1, NORM uses OBJ 0, OBJ 2 open for a new patron. Frees OBJ 3, 5, 7."),
    ("2026-10-21", "Owner: background palettes used above the playfield (HUD BG 1, stage BG 5, 6) are reloaded where the playfield starts; in the playfield they are free for patrons."),
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
    rows = c["attr"]["pal"]
    above = sorted({int(ch) for r in rows[:5] for ch in r})          # layout.h: HUD_ROW 0, stage rows 1-4, BAR_FIRST_ROW 5
    field = sorted({int(ch) for r in rows[5:] for ch in r})
    keg7 = any(r[x] == "7" for r in rows[5:] for x in (17, 18, 19))   # the keg / spout columns on BG 7 (the Saloon's are on BG 0)
    venues.append(dict(key=key, name=name, pal=pal, bg=bgp, used=used, looks=looks, free=free, above=above, field=field, keg7=keg7))

commit = subprocess.run(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()

# Patron names (tools/gen_credits.py PATRONS, art order A, B, C) and short descriptions where the art notes give one.
NAMES = {
    "cowboys": ["DUSTY, the cowboy", "MABEL, the lace shawl", "HANK, the ranch hand"],   # owner 2026-10-21: variant B renamed MABEL
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
# Owner plans per venue. moves: (text the item starts with, kind, from slot, to slot, shown as); recolour: {(kind, slot): {index: hex}};
# open: {(kind, slot): label} a palette offered to a new patron. Planned items and colours are drawn in yellow.
TAN = "#FFE6CD"   # the Stadium's white push (owner 2026-10-21: the lighter tan, over #FFD5AC: "a better balance")
PLANS = {
    "cowboys": dict(
        moves=[("HANK", "OBJ", 7, 3, "HANK, the ranch hand"), ("Show dancers", "OBJ", 5, 1, "Show dancers"),
               ("DUSTY", "OBJ", 3, 5, "DUSTY, the cowboy")],                   # owner 2026-10-22: DUSTY joins EMMA
        recolour={("OBJ", 3): {1: "#8B5231", 2: "#FFE6CD", 3: "#392918"},   # HANK's art and palette with colours 1 and 2 swapped (he looks the same)   # HANK's palette, his hat (colour 1) in the cheerleaders' tan
                  ("OBJ", 1): {1: "#FFE6CD"},                               # the full mug's cream to the tan; the dancers share it
                  ("OBJ", 6): {1: "#FFCEAD", 2: "#ADADAD", 3: "#1A1A20"},  # MABEL (was ROSIE), redrawn by the owner: grey hair, black lace shawl                               # ROSIE's hair (and outline) dark grey; her shawl and dress stay pink
                  },
        open={},
        add={("OBJ", 7): ("GUS, the prospector", ["#D8C098", "#B85838", "#281810"]),   # the Outlaw's former palette, kept by the Prospector; Big Tex takes it too
             ("OBJ", 4): ("ROSIE, the singer", ["#F8D0B0", "#BB2F32", "#202030"]),   # owner 2026-10-22: ROSIE's skin and outline, the Outlaw file's red   # owner's concept (set 2 B, v3: the wall shows through at her eyes)
             ("OBJ", 5): ("EMMA, the singer", ["#FFD5BD", "#8B5231", "#221B1A"])},   # owner 2026-10-22: shared with DUSTY
        dmg=["DUSTY", "EMMA", "GUS"],          # owner 2026-10-22: the DMG's three (bank 0, both systems); GUS in the boss-overwritten slot
        # owner 2026-10-22: the palettes each patron may spawn in (recolours of the same tiles; HANK's art has colours 1 and 2 swapped).
        variants={"HANK": [3, 5, 6], "ROSIE": [3, 4, 5, 7], "REDD": [3, 4, 5, 6, 7], "DUSTY": [3, 5], "EMMA": [4, 5, 7],
                  "MABEL": [3, 4, 5, 6, 7], "ARTIE": [3, 4, 5, 6, 7], "GUS": [5, 7]},
        join={("OBJ", 4): ["REDD, the outlaw"],                                          # owner 2026-10-22: the Outlaw (owner's recolour) shares ROSIE's palette
              ("OBJ", 6): ["ARTIE, the priest"]},                       # owner set 2 C (bald, grey beard) shares MABEL's palette
        why="Owner 2026-10-21: HANK's hat to the cheerleaders' skin (#FFE6CD); DUSTY uses HANK's palette. Kept in slot 3 so both stay in boss fights (the boss takes 7).",
    ),
    "sports": dict(
        moves=[("PETE", "OBJ", 3, 1, "PETE, the cap fan"), ("Show dancers", "OBJ", 5, 1, "Cheerleaders"),
               ("NORM", "OBJ", 7, 0, "NORM, the ref")],
        recolour={("OBJ", 1): {1: TAN}, ("OBJ", 2): {1: TAN}, ("BG", 2): "OBJ 1", ("BG", 4): "OBJ 0"},
        open={("OBJ", 2): "Reserved patron"},
        field_moves=[("Keg, spout", 1, 0)],          # playfield: BG 0 takes BG 1's (keg / spout) palette and the keg / spout share it
        why="Owner 2026-10-21: OBJ 1's white pushed toward tan serves PETE and the cheerleaders; NORM uses Sal's OBJ 0; OBJ 2 gets the same push and becomes a patron palette.",
    ),
    # owner 2026-10-25: every recommended and optional merge on the Palette Merges page (tools/artifacts/palette_merges/build.py MERGES)
    "lumberjacks": dict(
        moves=[("Show dancers", "OBJ", 5, 1, "Sasquatch"), ("WILLOW", "OBJ", 6, 3, "WILLOW, red hair"), ("WILLOW", "BG", 3, 2, "WILLOW, red hair")],
        recolour={("OBJ", 1): {1: "#F6E6C5", 2: "#834A29", 3: "#291010"}},
        open={},
        why="Owner 2026-10-25: the Sasquatch shares the full mug (foam to cream); CEDAR and WILLOW share CEDAR's palette (WILLOW's navy goes).",
    ),
    "chefs": dict(
        moves=[("PIERRE", "OBJ", 3, 0, "PIERRE"), ("BRIE", "OBJ", 6, 0, "BRIE"), ("Show dancers", "OBJ", 5, 0, "Waiter"),
               ("BRIE", "BG", 3, 2, "BRIE")],
        recolour={("BG", 2): "OBJ 0"},
        open={},
        why="Owner 2026-10-25: PIERRE, BRIE and the waiter use Sal's OBJ 0; PIERRE and BRIE walk in BG 2 in Sal's colours.",
    ),
    "divers": dict(
        moves=[("Show dancers", "OBJ", 5, 0, "Penguin")],
        recolour={}, open={},
        why="Owner 2026-10-25: the penguin uses Sal's OBJ 0 (its orange beak and feet turn peach).",
    ),
    "punks": dict(
        moves=[("Show dancers", "OBJ", 5, 6, "The band")],
        recolour={("OBJ", 6): {1: "#F6BD94", 2: "#4ACD4A", 3: "#100810"}, ("BG", 3): "OBJ 6"},
        open={},
        why="Owner 2026-10-25: the band shares BANDIT's palette.",
    ),
    "ninjas": dict(
        moves=[("Show dancers", "OBJ", 5, 6, "Taiko drummer")],
        recolour={("OBJ", 6): {1: "#FFEEDE", 2: "#CD2939", 3: "#181010"}, ("BG", 3): "OBJ 6"},
        open={},
        why="Owner 2026-10-25: the taiko drummer shares SAKURA's palette.",
    ),
    "zoo": dict(
        moves=[("COCO", "OBJ", 3, 1, "COCO, the monkey")],
        recolour={("OBJ", 1): {1: "#F6D5A4", 2: "#8B5229", 3: "#291808"}, ("BG", 2): "OBJ 1"},
        open={},
        why="Owner 2026-10-25: COCO shares the full mug's palette (foam to tan).",
    ),
    "aliens": dict(
        moves=[("ZORP", "OBJ", 3, 1, "ZORP, eye stalks"), ("XENO", "OBJ", 6, 2, "XENO, the grey one")],
        recolour={("OBJ", 1): {1: "#F6FF9C", 2: "#4ACD62", 3: "#102020"}, ("OBJ", 2): {1: "#E6E6EE", 2: "#9CA4B4", 3: "#101018"},
                  ("BG", 2): "OBJ 1", ("BG", 3): "OBJ 2"},
        open={},
        why="Owner 2026-10-25: ZORP shares the full mug's palette, XENO the empty mug's. Check the Space boss's OBJ 2 use.",
    ),
}
# Planned removals (struck through, yellow). Owner 2026-10-21: drop the enhanced looks (M14a) after the next patron revision.
DROP_ENHANCED = True
# Owner 2026-10-21: the BG palettes used above the playfield are reloaded where the playfield starts (row 5), so in the playfield
# they are free for patrons. The above-the-playfield palettes are listed in their own section.
SPLIT_PLAYFIELD = True
# Every venue (owner 2026-10-21): in the playfield the keg / spout palette moves from BG 7 to BG 1 (BG 1 is the HUD's above the playfield).
FIELD_MOVES = [("Keg, spout", 7, 1)]
PATRON_SLOT = {3: 0, 6: 1, 7: 2}          # OBJ slot -> art variant A, B, C (lifted)
BG_PATRON = {2: 0, 3: 1, 4: 2}            # BG slot -> art variant (walking)


def enh_variant(v):
    """The art variant (0 A, 1 B) of the venue's enhanced look, or None."""
    u = v["used"].get(4)
    if not u:
        return None
    return 1 if any("Patron B" in k for k in u) else 0


# What each boss's topper sprite (OBJ 7, reloaded with his colours for the fight) is: assets/art/boss/<boss>.txt
TOPPER = dict(cowboys="hat crown", sports="forelock", lumberjacks="crest", chefs="beret stalk", divers="horns",
              robots="beacon lamp", punks="helmet", ninjas="topknot", zoo="crown", aliens="antenna")


def users(kind, v, s):
    """(patrons now, non-patrons) for one palette."""
    n = NAMES[v["key"]]
    e = enh_variant(v)
    if kind == "OBJ":
        pat = [n[PATRON_SLOT[s]]] if s in PATRON_SLOT else []
        if s == 4 and e is not None and not DROP_ENHANCED:
            pat = [n[e] + " (left half, lifted)"]
        other = {0: ["Sal", "Tip coin", "Pour sparkle", "PERFECT cue"], 1: ["Full mug", "Fill glass", "Breaking glass"],
                 2: ["Empty mug", "Breaking glass", "Boss: capacity mugs"], 5: ["Show dancers"], 7: ["Boss fight: " + TOPPER[v["key"]]]}.get(s, [])
    else:
        pat = [n[BG_PATRON[s]]] if s in BG_PATRON else []
        if s == 7 and e is not None and not DROP_ENHANCED:
            pat = [n[e] + " (top row)"]
        other = {0: ["Bar, wall"] + ([] if v["keg7"] else ["Keg, spout"]), 1: ["HUD"], 4: ["Boss body"], 5: ["Stage"], 6: ["Stage"],
                 7: ["Keg, spout"] if v["keg7"] else []}.get(s, [])
    return pat, other


def model(v):
    """slot -> dict(pat=[(text, planned)], oth=[...], cols, new={i: hex}, freed) for ("OBJ"|"BG", s); the plan applied."""
    m = {}
    for kind in ("OBJ", "BG"):
        for sl in range(8):
            pat, oth = users(kind, v, sl)
            m[(kind, sl)] = dict(pat=[(x, False) for x in pat], oth=[(x, False) for x in oth],
                                 cols=(v["pal"] if kind == "OBJ" else v["bg"]).get(sl, ["#000000"] * 4), new={}, freed=False, open=None)
    if DROP_ENHANCED and enh_variant(v) is not None and not m[("OBJ", 4)]["pat"]:
        m[("OBJ", 4)]["freed"] = True
    pl = PLANS.get(v["key"])
    if pl:
        for start, kind, fr, to, label in pl["moves"]:
            src = m[(kind, fr)]
            for lst in ("pat", "oth"):
                hit = [x for x in src[lst] if x[0].startswith(start)]
                if hit:
                    src[lst] = [x for x in src[lst] if x not in hit]
                    m[(kind, to)][lst].append((label, True))
            if not src["pat"] and not [x for x in src["oth"] if not x[0].startswith("Boss")]:
                src["freed"] = True
        for key, ch in pl["recolour"].items():
            if isinstance(ch, str):                       # "OBJ n": take that palette's planned colours 1-3
                k2, n2 = ch.split(); o = m[(k2, int(n2))]
                src = [o["new"].get(i, o["cols"][i]) for i in range(4)]
                m[key]["new"] = {i: src[i] for i in (1, 2, 3) if src[i] != m[key]["cols"][i]}
                m[key]["match"] = ch
            else:
                m[key]["new"] = dict(ch)
        for key, label in pl["open"].items():
            m[key]["open"] = label
        for key, (label, hexes) in pl.get("add", {}).items():
            m[key]["pat"].append((label, True))
            m[key]["new"] = {i + 1: h for i, h in enumerate(hexes) if h != m[key]["cols"][i + 1]}
            m[key]["freed"] = False
            m[key]["quiet"] = True                  # a new palette: no "was" note
        for key, names in pl.get("join", {}).items():
            for nm in names:
                m[key]["pat"].append((nm, True))
    return m


def card(kind, sl, d, skip0, hide_cols=False):
    pat, oth = d["pat"], d["oth"]
    if hide_cols:
        pat, oth = [], []
    free = not pat and not [x for x in oth if not x[0].startswith("Boss")] and not d["open"]
    body = ""
    if pat or d["open"]:
        body += '<ul class="pat">%s%s</ul>' % ("".join('<li class="%s">%s</li>' % ("plan" if p else "now", esc(t)) for t, p in pat),
                                              ('<li class="plan open">%s</li>' % esc(d["open"])) if d["open"] else "")
    if oth and not free:
        body += '<ul class="oth">%s</ul>' % "".join('<li%s>%s</li>' % (' class="plan"' if p else "", esc(t)) for t, p in oth)
    if free:
        body = '<p class="freep%s">Free</p>' % (" plan" if (d["freed"] or hide_cols) else "")
        if oth:
            body += '<ul class="oth">%s</ul>' % "".join("<li>%s</li>" % esc(t) for t, p in oth)
    cols = d["cols"]
    sw = ""
    if not hide_cols and not (free and d["freed"]):
        sw = "".join(('<button type="button" class="sw%s" style="background:%s" data-hex="%s" title="%s"></button>')
                     % (" chg" if i in d["new"] else "", d["new"].get(i, cols[i]), d["new"].get(i, cols[i]),
                        ("was " + cols[i] + ", planned " + d["new"][i]) if i in d["new"] else cols[i])
                     for i in range(1 if skip0 else 0, 4))
    moved = (d.get("quiet") and not str(d.get("match") or "").startswith("OBJ")) or (str(d.get("match") or "").startswith("BG") and len(d["new"]) == 4)
    if d["new"] and not moved:
        note = ("colours as %s" % d["match"]) if d.get("match") else ", ".join("colour %d: %s &rarr; %s" % (i, cols[i], d["new"][i]) for i in sorted(d["new"]))
        body += '<p class="chgp">%s</p>' % note
    return ('<div class="pal%s"><div class="ph"><span class="slot">%s %d</span><span class="sws">%s</span></div>%s</div>'
            % (" free" if free else "", kind, sl, sw, body))


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
h2 { font-size: 12px; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); margin: 28px 0 10px; }
.ph2 h2 { margin-top: 28px; }
.ph2 { margin-bottom: 10px; } .ph2 h2 { margin-bottom: 0; }
.panel > .stats { margin-top: 4px; }
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

.chgp { margin: 0; color: var(--plan); font-size: 12px; }
li.open { font-style: italic; }
.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 8px; }
.stat { background: var(--card); border: 1px solid var(--rule); border-radius: 10px; padding: 10px 12px; display: grid; gap: 2px; }
.stat b { font-family: var(--display); font-size: 24px; font-variant-numeric: tabular-nums; }
.stat span { color: var(--muted); font-size: 13px; }
.sw { width: 20px; height: 20px; border: 1px solid rgba(0,0,0,.35); border-radius: 3px; padding: 0; margin-left: 2px; cursor: pointer; }
.tbl { overflow-x: auto; background: var(--card); border: 1px solid var(--rule); border-radius: 10px; }
table.pt { border-collapse: collapse; width: 100%; font-size: 14px; }
.pt th, .pt td { text-align: left; padding: 6px 10px; border-bottom: 1px solid var(--rule); vertical-align: middle; }
.pt th { font-size: 12px; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); }
.pt tr:last-child td { border-bottom: 0; }
.pt td.now { color: var(--now); font-weight: 600; } .pt td.plan { color: var(--plan); font-weight: 600; }
.pt td.slotc { font-family: var(--mono); white-space: nowrap; }
.pimg { image-rendering: pixelated; image-rendering: crisp-edges; display: block; border-radius: 3px; width: 48px; height: 48px; max-width: none; }
.pt td.pic { width: 100px; min-width: 100px; padding-block: 4px; }
.pics { display: flex; gap: 4px; }
.bimg { image-rendering: pixelated; image-rendering: crisp-edges; display: block; max-width: none; border-radius: 4px; }
.dl.boss { display: inline-block; margin-bottom: 10px; }
.dl { display: block; border-radius: 3px; }
.dl:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.pimg.none { display: grid; place-items: center; color: var(--muted); border: 1px dashed var(--rule, #888); box-sizing: border-box; }
.muted { color: var(--muted); font-style: italic; }
.ph2 { display: flex; align-items: end; justify-content: space-between; gap: 10px; flex-wrap: wrap; }
.copymd { font: 600 13px var(--body); padding: 5px 10px; border-radius: 8px; border: 1px solid var(--accent); background: var(--card); color: var(--accent); cursor: pointer; }
.copymd:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.foot { color: var(--muted); font-size: 12px; margin: 6px 0 0; }
#toast { position: fixed; left: 50%; bottom: calc(16px + env(safe-area-inset-bottom, 0px)); transform: translateX(-50%); background: var(--ink); color: var(--ground); font: 13px var(--mono); padding: 6px 12px; border-radius: 6px; }
</style>""")
w('<div class="wrap"><div class="tabs" role="tablist" aria-label="Venues">')
for i, v in enumerate(venues):
    w('<button type="button" class="tab" role="tab" id="t-%s" aria-controls="p-%s" aria-selected="%s">%s</button>'
      % (v["key"], v["key"], "true" if i == 0 else "false", esc(v["name"].replace("The ", ""))))
w('</div>')
ART = os.path.join(os.path.dirname(os.path.abspath(__file__)), "art")


def frames(path):
    out, cur = [], []
    for l in open(path).read().splitlines():
        if l.startswith(";"):
            continue
        if not l.strip():
            if cur:
                out.append(cur); cur = []
        else:
            cur.append(l)
    if cur:
        out.append(cur)
    return out


def art_rows(v, name):
    """The patron's front view as house ASCII: the planned art in art/<venue>_<name>.txt, else the game's assets/art/patrons."""
    first = name.split(",")[0].strip().lower()
    f = os.path.join(ART, "%s_%s.txt" % (v["key"], first))
    if os.path.exists(f):
        return frames(f)[0]
    names = [n.split(",")[0].strip().lower() for n in NAMES[v["key"]]]
    if first in names:
        return frames(os.path.join(ROOT, "assets/art/patrons/%s.txt" % v["key"]))[names.index(first)]
    return None


# The latest accepted art per patron (owner picks 2026-10-26, Q56-Q59): (front, back) files under the patron pass folder,
# "old" = the game's frame. The Saloon: art/ fronts; backs the game's for its 3 looks, the others still to draw.
PASS = os.path.join(ROOT, "docs/dev/concepts/patron_pass")
ACCEPTED = {
    "lumberjacks": {"cedar": ("cedar_owner", "cedar_back"), "willow": ("willow", "willow_back"), "ash": ("old", "ash_v2_back")},
    "sports": {"pete": ("pete", "pete_back"), "serena": ("old", "serena_v2_back"), "norm": ("old", "norm_v2_back")},
    "chefs": {"pierre": ("old", "old"), "brie": ("old", "brie_v2_back"), "basil": ("basil", "basil_back")},
    "robots": {"boxy": ("boxy", "boxy_back"), "volta": ("volta", "volta_back"), "blip": ("blip", "blip_back")},
    "punks": {"spike": ("spike", "spike_back"), "bandit": ("bandit", "bandit_back"), "slick": ("slick", "slick_back")},
    "ninjas": {"kage": ("old", "old"), "sakura": ("sakura", "sakura_back"), "ronin": ("old", "ronin_v2_back")},
    "zoo": {"coco": ("coco", "coco_back"), "bamboo": ("bamboo", "bamboo_back"), "muddy": ("old", "old")},
    "aliens": {"zorp": ("old", "zorp_v2_back"), "xeno": ("old", "xeno_v2_back"), "glorp": ("glorp_v2", "glorp_v2_back")},
}


def accepted(v, name):
    """(front rows, back rows or None) of the patron's latest accepted art."""
    first = name.split(",")[0].strip().lower()
    names = [n.split(",")[0].strip().lower() for n in NAMES[v["key"]]]
    old = lambda suf: frames(os.path.join(ROOT, "assets/art/patrons/%s%s.txt" % (v["key"], suf)))[names.index(first)]
    pick = ACCEPTED.get(v["key"], {}).get(first)
    if pick:
        get = lambda f, suf: old(suf) if f == "old" else frames(os.path.join(PASS, v["key"], f + ".txt"))[0]
        return get(pick[0], ""), get(pick[1], "_back")
    front = art_rows(v, name)
    back = old("_back") if first in names else None
    return front, back

def thumb(rows, cols, wall, name):
    """img/<name>.png beside OUT: a 16x16 front view, x4, in the given colours. Returns its relative path."""
    from PIL import Image
    im = Image.new("RGB", (16, 16), hex2(wall))
    for y, r in enumerate(rows[:16]):
        for x, ch in enumerate(r[:16]):
            if ch in "-+#":
                im.putpixel((x, y), hex2(cols["-+#".index(ch)]))
    rel = "img/%s.png" % name
    path = os.path.join(os.path.dirname(OUT), rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.resize((64, 64), Image.NEAREST).save(path, "PNG")
    one = Image.new("P", (16, 16), 0)                 # the 1x download: indexed, colour 0 the wall, 1-3 light to dark
    one.putpalette(sum((list(hex2(c)) for c in [wall] + list(cols)), []))
    for y, r in enumerate(rows[:16]):
        for x, ch in enumerate(r[:16]):
            if ch in "-+#":
                one.putpixel((x, y), "-+#".index(ch) + 1)
    one.save(path[:-4] + "_1x.png", "PNG", transparency=0)
    return rel


# Bosses: venue -> (art file, body width, topper x). The fight's palette map is boss_palettes.json (from src/boss*.c).
BOSS = dict(cowboys=("big_tex", 40, 16), sports=("mascot", 32, 8), lumberjacks=("sasquatch", 32, 12), chefs=("critic", 32, 9),
            divers=("yeti", 32, 9), robots=("prototype", 32, 8), punks=("duke", 40, 16), ninjas=("sumo", 40, 16),
            zoo=("leo", 32, 6), aliens=("mothership", 40, 12))
BOSS_PAL = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "boss_palettes.json")))
SHEET_W, GAP = 168, 8                         # the editable sheet: blocks in file order, rows of at most 168 px, 8 px apart


def boss_blocks(name):
    """[(block name, rows)] of assets/art/boss/<name>.txt in file order."""
    out, cur = [], None
    for l in open(os.path.join(ROOT, "assets/art/boss/%s.txt" % name)).read().splitlines():
        if l.startswith("@"):
            cur = (l[1:].split()[0], []); out.append(cur)
        elif cur is not None and l and not l.startswith(";"):
            cur[1].append(l)
        elif not l.strip():
            cur = None
    return out


def boss_layout(blocks):
    """[(x, y)] of each block on the editable sheet, and the sheet's size. Deterministic: the split reads it back."""
    pos, x, y, rh, w = [], 0, 0, 0, 0
    for _, rows in blocks:
        bw, bh = max(len(r) for r in rows), len(rows)
        if x and x + bw > SHEET_W:
            x, y, rh = 0, y + rh + GAP, 0
        pos.append((x, y)); x += bw + GAP; rh = max(rh, bh); w = max(w, x - GAP)
    return pos, (w, y + rh)


def boss_section(v, m, field):
    from PIL import Image
    if v["key"] not in BOSS:
        return ""
    name, width, hat_dx = BOSS[v["key"]]
    info = BOSS_PAL.get(v["key"], {})
    wall = v["bg"][0][0]
    parts = info.get("parts", [])
    body = next((p["colours"] for p in parts if p.get("kind") == "BG" and p.get("slot") == 4 and p.get("colours")), None)
    top = next((p["colours"] for p in parts if p.get("kind") == "OBJ" and p.get("slot") == 7 and p.get("colours")), None) or body
    blocks = dict(boss_blocks(name))
    allb = boss_blocks(name)
    tops = {"HAT_STILL", "HAT_BOB", "HAT_POP0", "HAT_POP1", "HAT_POP2", "HAT_POP3", "HAT_DUCK", "LAMP_RING", "LAMP_X"}
    # the fight as built: WALK on the bar, the topper's upper 8 rows above it
    im = Image.new("RGB", (width, 24), hex2(wall))
    for y, r in enumerate(blocks["WALK"][:16]):
        for x, ch in enumerate(r[:width]):
            if ch in "-+#":
                im.putpixel((x, y + 8), hex2(body["-+#".index(ch)]))
    for y, r in enumerate(blocks["HAT_STILL"][:16]):
        for x, ch in enumerate(r[:8]):
            if ch in "-+#" and 0 <= hat_dx + x < width:
                im.putpixel((hat_dx + x, y), hex2(top["-+#".index(ch)]))
    rel = "img/boss_%s.png" % name
    im.resize((width * 4, 96), Image.NEAREST).save(os.path.join(os.path.dirname(OUT), rel), "PNG")
    # the editable sheet: every block, indexed; colour 0 the wall, 1-3 the body, 4-6 the topper's own colours if different
    pos, (sw, sh) = boss_layout(allb)
    sheet = Image.new("P", (sw, sh), 0)
    pal = [wall] + body + (top if top != body else [])
    sheet.putpalette(sum((list(hex2(c)) for c in pal), []))
    for (bn, rows), (bx, by) in zip(allb, pos):
        off = 4 if (bn in tops and top != body) else 1
        for y, r in enumerate(rows):
            for x, ch in enumerate(r):
                if ch in "-+#":
                    sheet.putpixel((bx + x, by + y), "-+#".index(ch) + off)
    dl = "img/boss_%s_sheet.png" % name
    sheet.save(os.path.join(os.path.dirname(OUT), dl), "PNG", transparency=0)
    h = ['<div class="ph2"><h2>Boss: %s</h2></div>' % esc(info.get("boss", name))]
    h.append('<a class="dl boss" href="%s" download="boss_%s_sheet.png" data-file="boss_%s_sheet.png" title="Download every %s block, editable">'
             '<img class="bimg" alt="%s as built" width="%d" height="96" src="%s"></a>' % (dl, name, name, esc(info.get("boss", name)), esc(info.get("boss", name)), width * 4, rel))
    h.append('<div class="tbl"><table class="pt"><thead><tr><th>Part</th><th>Palette</th><th>Colours</th><th>When</th><th>Tiles</th></tr></thead><tbody>')
    for p in parts:
        cols = p.get("colours")
        if p["part"].startswith("Topper") and p["slot"] == 7 and v["key"] != "robots":
            p = dict(p, part="Topper: " + TOPPER[v["key"]])
        if not cols:                              # the venue's own slot: its planned colours, as the cards above show them
            d = m[("OBJ", p["slot"])] if p["kind"] == "OBJ" else field[p["slot"]]
            cols = eff(d)[1:]
        sw_ = "".join('<button type="button" class="sw" style="background:%s" data-hex="%s" title="%s"></button>' % (c, c, c) for c in cols) if cols else esc(p.get("note", ""))
        h.append('<tr><td>%s</td><td class="slotc">%s %s</td><td>%s</td><td>%s</td><td>%s</td></tr>'
                 % (esc(p["part"]) + (" ?" if p.get("unsure") else ""), p["kind"], p["slot"], sw_, esc(p.get("when", "")), esc(str(p.get("tiles", "")))))
    h.append('</tbody></table></div>')
    return "".join(h)

def hex2(h):
    return (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16))


def eff(d):
    return [d["new"].get(i, d["cols"][i]) for i in range(4)]


def empty(d):
    return not d["pat"] and not d["oth"] and not d.get("open")


def field_model(v, m):
    """The playfield's BG slots under the plan: global and per-venue moves, then patrons renumbered so BG n matches OBJ n where it can."""
    field = {sl: dict(m[("BG", sl)]) for sl in range(8)}
    for sl in v["above"]:
        if sl not in v["field"]:
            field[sl] = dict(pat=[], oth=[], cols=field[sl]["cols"], new={}, freed=True, open=None)
    for item, fr, to in FIELD_MOVES:
        src = field[fr]; c = eff(src)
        if not any(x[0].startswith(item) for x in src["oth"]):
            continue
        src["oth"] = [x for x in src["oth"] if not x[0].startswith(item)]
        if empty(src):
            src.update(freed=True, new={})
        field[to] = dict(pat=[], oth=[(item, True)], cols=field[to]["cols"], new={i: c[i] for i in range(4)}, freed=False, open=None, quiet=True)
    for item, fr, to in PLANS.get(v["key"], {}).get("field_moves", []):
        src = field[fr]; c = eff(src)
        src["oth"] = [x for x in src["oth"] if not x[0].startswith(item)]
        dst = dict(field[to])
        dst["new"] = {i: c[i] for i in range(4) if c[i] != dst["cols"][i]}
        dst["oth"] = dst["oth"] + [(item, True)]
        field[to] = dst
        if empty(src):
            field[fr] = dict(pat=[], oth=[], cols=src["cols"], new={}, freed=True, open=None)

    def put(to, entry, colours, match, other=None):
        d = field[to]
        other = (other or []) + [x for x in d["oth"] if x[0].startswith("Boss")]
        field[to] = dict(pat=[entry] if entry else [], oth=other, cols=d["cols"],
                         new={i: colours[i] for i in range(4) if colours[i] != d["cols"][i]}, freed=False, open=None, quiet=True, match=match)

    def take(fr, name):
        d = field[fr]
        d["pat"] = [x for x in d["pat"] if x[0] != name]
        if empty(d):
            field[fr] = dict(pat=[], oth=[], cols=d["cols"], new={}, freed=True, open=None)

    pats = [(t, sl) for sl in range(8) for t, _ in m[("OBJ", sl)]["pat"]] + [(m[("OBJ", sl)]["open"], sl) for sl in range(8) if m[("OBJ", sl)]["open"]]
    for _ in range(4):
        for name, o in pats:
            b = next((sl for sl in range(8) if any(x[0] == name for x in field[sl]["pat"])), None)
            if b == o:
                continue
            if field[o]["pat"] or [x for x in field[o]["oth"] if not x[0].startswith("Boss")] or field[o].get("open"):
                mates = {t for t, so in pats if so == o and t != name}
                if field[o]["pat"] and all(x[0] in mates for x in field[o]["pat"]):
                    field[o]["pat"] = field[o]["pat"] + [(name, True)]
                    if b is not None:
                        take(b, name)
                continue
            if b is None:          # a reserved patron: its OBJ colours, the wall's colour 0
                oc = eff(m[("OBJ", o)])
                put(o, (name, True), [eff(field[0])[0]] + oc[1:], "OBJ %d" % o)
            else:
                d = field[b]
                put(o, (name, True), eff(d), d.get("match") if str(d.get("match", "")).startswith("OBJ") else None)
                take(b, name)
    objof = {t: so for t, so in pats}
    for sl in range(8):
        names = [x[0] for x in field[sl]["pat"]]
        if not names or names[0] not in objof:
            continue
        o = objof[names[0]]
        if m[("OBJ", o)]["new"]:
            oc = eff(m[("OBJ", o)]); d = field[sl]
            want = [eff(d)[0]] + oc[1:]
            d["new"] = {k: want[k] for k in range(4) if want[k] != d["cols"][k]}
            d["match"] = "OBJ %d" % o
            if not d.get("quiet"):
                d["quiet"] = True
    bb = next((sl for sl in range(8) if any(x[0] == "Boss body" for x in field[sl]["oth"])), None)
    if bb is not None and bb != 7:                 # the boss's body pairs with his topper's OBJ 7
        if empty(field[7]) or (field[7]["pat"] and not field[7]["oth"]):
            field[7]["oth"] = field[7]["oth"] + [("Boss body", True)]
            if not field[7]["pat"]:
                field[7].update(freed=True, new={})
            field[bb]["oth"] = [x for x in field[bb]["oth"] if x[0] != "Boss body"]
            if empty(field[bb]):
                field[bb] = dict(pat=[], oth=[], cols=field[bb]["cols"], new={}, freed=True, open=None)
    return field


for i, v in enumerate(venues):
    m = model(v)
    field = field_model(v, m)
    ofree = [sl for sl in range(8) if card("OBJ", sl, m[("OBJ", sl)], True).find('class="pal free"') >= 0]
    bfree = [sl for sl in range(8) if not field[sl]["pat"] and not field[sl].get("open") and not [x for x in field[sl]["oth"] if not x[0].startswith("Boss")]]
    w('<section class="panel" role="tabpanel" id="p-%s" aria-labelledby="t-%s"%s>' % (v["key"], v["key"], "" if i == 0 else " hidden"))
    w('<h1>%s</h1><div class="stats">' % esc(v["name"]))
    ident, reserved = [], []
    for sl in range(8):
        d = m[("OBJ", sl)]
        for t, planned in d["pat"]:
            ident.append(dict(name=t, obj=sl, planned=planned))
        if d["open"]:
            reserved.append(dict(name=d["open"], obj=sl, planned=True))
    for r in ident + reserved:
        b = next((sl for sl in range(8) if any(x[0] == r["name"] for x in field[sl]["pat"])), None)
        if b is not None:
            r["bg"] = b
            if field[b]["new"] or b != r["obj"]:
                r["planned"] = r["planned"] or bool(field[b]["new"])
    rows = []
    md = "### %s: patron palettes (plan, %s)\n\n| Patron | Palette colours (1, 2, 3) | OBJ | BG | Spawns in OBJ (and matching BG) | DMG |\n|---|---|---|---|---|---|\n" % (v["name"], LOG[0][0])
    for r in ident + reserved:
        d = m[("OBJ", r["obj"])]
        cols = [d["new"].get(k, d["cols"][k]) for k in (1, 2, 3)]
        sw = "".join('<button type="button" class="sw" style="background:%s" data-hex="%s" title="%s"></button>' % (c, c, c) for c in cols)
        bg = ("BG %d" % r["bg"]) if "bg" in r else '<span class="muted">to assign</span>'
        fr, bk = accepted(v, r["name"])
        first = r["name"].split(",")[0].strip().lower()
        img = ""
        for rows_, side in ((fr, "front"), (bk, "back")):
            if rows_:
                rel = thumb(rows_, cols, v["bg"][0][0], "%s_%s_%s" % (v["key"], first, side))
                img += ('<a class="dl" href="%s" download="%s_%s.png" data-file="%s_%s.png" title="Download %s %s (16x16)">'
                        '<img class="pimg" alt="%s %s" width="48" height="48" src="%s"></a>'
                        % (rel[:-4] + "_1x.png", first, side, first, side, esc(first.upper()), side, esc(r["name"]), side, rel))
            else:
                img += '<span class="pimg none">-</span>'
        img = '<div class="pics">%s</div>' % img
        rows.append(dict(html=(img, "plan" if r["planned"] else "now", esc(r["name"]), sw, r["obj"], bg)))
        var = PLANS.get(v["key"], {}).get("variants", {}).get(r["name"].split(",")[0].strip())
        vtxt = ", ".join(str(x) for x in var) if var else str(r["obj"])
        dm = PLANS.get(v["key"], {}).get("dmg")
        dtxt = ("DMG" if r["name"].split(",")[0].strip() in dm else "") if dm else "DMG"
        rows[-1]["html"] = rows[-1]["html"] + (vtxt, dtxt)
        md += "| %s%s | %s | OBJ %d | %s | %s | %s |\n" % (r["name"], " (planned)" if r["planned"] else "", " ".join("`%s`" % c for c in cols), r["obj"],
                                                ("BG %d" % r["bg"]) if "bg" in r else "to assign", vtxt, dtxt or "Color only")
    w('<div class="stat"><b>%d</b><span>identified patrons</span></div>' % len(ident))
    w('<div class="stat"><b>%d</b><span>reserved patrons</span></div>' % len(reserved))
    w('<div class="stat"><b>%d</b><span>free OBJ palettes</span></div>' % len(ofree))
    w('<div class="stat"><b>%d</b><span>free BG palettes</span></div>' % len(bfree))
    w('</div><h2>Sprite palettes</h2><div class="grid">')
    for sl in range(8):
        w(card("OBJ", sl, m[("OBJ", sl)], True))
    w('</div><h2>Background palettes, playfield</h2><div class="grid">')
    for sl in range(8):
        w(card("BG", sl, field[sl], False))
    w('</div><h2>Background palettes, above the playfield (HUD and stage)</h2><div class="grid">')
    for sl in v["above"]:
        d = dict(m[("BG", sl)]); d["pat"] = []
        w(card("BG", sl, d, False))
    w('</div><div class="ph2"><h2>Patrons</h2><button type="button" class="copymd" data-md="%s">Copy table as Markdown</button></div>' % esc(md))
    w('<div class="tbl"><table class="pt"><thead><tr><th></th><th>Patron</th><th>Palette colours</th><th>OBJ</th><th>BG</th><th>Spawns in</th><th>Also on</th></tr></thead><tbody>')
    for r in rows:
        w('<tr><td class="pic">%s</td><td class="%s">%s</td><td>%s</td><td class="slotc">OBJ %d</td><td class="slotc">%s</td><td class="slotc">%s</td><td class="slotc">%s</td></tr>' % r["html"])
    w('</tbody></table></div>')
    w(boss_section(v, m, field))
    w('</section>')
w('<p class="foot">This is the plan. <span style="color:var(--now)">Green</span>: patrons as in the game today. <span style="color:var(--plan)">Yellow</span>: planned changes. Click a colour to copy it. '
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
    var m = e.target.closest(".copymd");
    if (m) {
      var md = m.getAttribute("data-md");
      var done = function () { toast.textContent = "Table copied as Markdown"; toast.hidden = false; clearTimeout(timer); timer = setTimeout(function () { toast.hidden = true; }, 1600); };
      var fallback = function () { var t = document.createElement("textarea"); t.value = md; t.style.position = "fixed"; t.style.opacity = "0"; document.body.appendChild(t); t.select();
        var ok = false; try { ok = document.execCommand("copy"); } catch (x) {} document.body.removeChild(t);
        if (ok) done(); else { toast.textContent = "Copy blocked here: select the table instead"; toast.hidden = false; clearTimeout(timer); timer = setTimeout(function () { toast.hidden = true; }, 2400); } };
      try { navigator.clipboard.writeText(md).then(done, fallback); } catch (x) { fallback(); }
      return;
    }
    var a = e.target.closest(".dl");
    if (a) {
      e.preventDefault();
      var say = function (m) { toast.textContent = m; toast.hidden = false; clearTimeout(timer); timer = setTimeout(function () { toast.hidden = true; }, 2000); };
      var dl = window.claude && window.claude.use ? window.claude.use("downloads") : Promise.resolve(null);
      Promise.all([dl, fetch(a.getAttribute("href")).then(function (r) { return r.blob(); })]).then(function (x) {
        if (!x[0]) { window.open(a.getAttribute("href"), "_blank"); return; }
        return x[0].save({ filename: a.getAttribute("data-file"), data: x[1] }).then(function () { say("Saved " + a.getAttribute("data-file")); },
          function (err) { if (err && err.code !== "declined") say("Download unavailable here"); });
      }).catch(function () { say("Download unavailable here"); });
      return;
    }
    var b = e.target.closest(".sw"); if (!b) return;
    var hex = b.getAttribute("data-hex");
    function shown(m) { toast.textContent = m; toast.hidden = false; clearTimeout(timer); timer = setTimeout(function () { toast.hidden = true; }, 1400); }
    try { navigator.clipboard.writeText(hex).then(function () { shown("Copied " + hex); }, function () { shown(hex); }); } catch (err) { shown(hex); }
  });
})();
</script>""")
open(OUT, "w").write("\n".join(S) + "\n")
print("wrote", OUT)
