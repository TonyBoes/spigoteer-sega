#!/usr/bin/env python3
"""Build the Graphics Atlas page (formerly the OBJ Palette Plan) (tools/artifacts/palette_plan/index.html).

    python3 tools/artifacts/palette_plan/build.py [ATLAS_DATA_DIR] [OUT_HTML]

The per-venue colours come from the graphics atlas data (`make atlas` writes out/atlas/data/). The plan itself (planned
use per slot, the ideas list, the log) is hand-kept in PLAN below: edit it when the owner decides something, rebuild,
republish (see tools/artifacts/README.md). The patron thumbnails go to img/ next to OUT_HTML and are published with the
page as files. The published page is wrapped in a skeleton with img{max-width:100%}, which shrinks an image in an
auto-width table cell to nothing: .pimg keeps a fixed 48 px size and max-width: none.

Per venue, after the boss: Dancers, Kegs, Stage, Floor (scene_pieces / scene_sections: assets/approved/venues/<prefix>_*, in the planned
colours). Each picture downloads its piece as an editable indexed PNG (img/scene_<venue>_<piece>_1x.png); scene_split.py reads an
edited one back (see its docstring for the palette index rule). boss_split.py does the same for the boss sheets.
"""
import hashlib
import html
import json
import os
import re
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
    ("2026-10-26", "Tile pictures: hover or tap a tile for its outline and number."),
    ("2026-10-26", "Patron revision batch 1 in the game: the accepted art for 8 venues and the palette merges (colours shared; no slots freed yet)."),
    ("2026-10-26", "This page is now the Graphics Atlas; the old atlas page is retired."),
    ("2026-10-26", "OBJ 7: \"Boss: hat\" was in every venue; now each lists its own boss's topper (crest, horns, lamp...), reloaded in his colours for the fight."),
    ("2026-10-26", "Tile grid sorted by what the tiles are: every frame assembled as drawn (Sal, mugs, glass, coin, dancers, sparkle), patron poses and back per look, the screen as drawn, digits and letters in order; the VRAM order behind a toggle."),
    ("2026-10-26", "Tile grid per venue: the atlas tile sheets with repeated pairs, tiles and blanks outlined."),
    ("2026-10-26", "Boss notes cut to two sentences on his actions and a list of which poses use sprites."),
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


def regions(rec):
    """(sprite-only 0-127, shared 128-255, BG-only 256-383) empty tiles (not loaded, not referenced) of one atlas tile record."""
    lo, use = rec["loaded"], rec["use"]
    return tuple(sum(1 for i in range(a, a + 128) if lo[i] == "0" and use[i] == "0") for a in (0, 128, 256))


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
    lv = load("level_" + key)
    c = lv["cgb"]
    bs = load("boss_%d" % (len(venues) + 1))                    # the same venue's boss fight (boss_N = VENUES order)
    tiles = dict(b0=regions(c["tiles"][0]), b1=regions(c["tiles"][1]), d=regions(lv["dmg"]["tiles"][0]), bb=regions(bs["cgb"]["tiles"][0]))
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
    venues.append(dict(key=key, name=name, pal=pal, bg=bgp, used=used, looks=looks, free=free, above=above, field=field, keg7=keg7, tiles=tiles))

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
w('<title>Graphics Atlas</title>')
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
.bdesc { margin: 0 0 8px; padding-left: 1.1em; font-size: 13px; } .bdesc b { font-family: var(--mono); font-size: 12px; }
.bact { margin: 0 0 6px; max-width: 68ch; font-size: 14px; }
.poses { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 12px; }
.poses figure { margin: 0; }
.poses figcaption { font: 600 11px var(--body); color: var(--muted); margin-top: 3px; letter-spacing: .04em; }
.dl { display: block; border-radius: 3px; }
.crop { display: block; max-width: none; border-radius: 3px; background-repeat: no-repeat; image-rendering: pixelated; image-rendering: crisp-edges; }
.dl:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.pimg.none { display: grid; place-items: center; color: var(--muted); border: 1px dashed var(--rule, #888); box-sizing: border-box; }
.muted { color: var(--muted); font-style: italic; }
.ph2 { display: flex; align-items: end; justify-content: space-between; gap: 10px; flex-wrap: wrap; }
.copymd { font: 600 13px var(--body); padding: 5px 10px; border-radius: 8px; border: 1px solid var(--accent); background: var(--card); color: var(--accent); cursor: pointer; }
.copymd:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.tgrid { display: flex; flex-wrap: wrap; gap: 12px; } .tgrid figure { margin: 0; max-width: 100%; } .tgrid figcaption { font-size: 13px; font-weight: 600; margin-bottom: 4px; }
.tgimg { display: block; max-width: 100%; height: auto; image-rendering: pixelated; }
#tout { position: absolute; z-index: 50; pointer-events: none; box-sizing: border-box; border: 2px solid #fff; outline: 1px solid #000; }
#ttip { position: absolute; z-index: 60; pointer-events: none; font-size: 12px; line-height: 1.4; padding: 4px 8px; border-radius: 6px; background: var(--ink); color: var(--ground); white-space: nowrap; box-shadow: 0 2px 8px rgba(0,0,0,.3); }
.tdet { font-size: 13px; color: var(--muted); margin: 8px 0 0; } .tdet summary { cursor: pointer; font-weight: 600; } .tdet ul { margin: 4px 0 0; padding-left: 1.2em; }
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


def boss_blocks(name, path=None):
    """[(block name, rows)] of assets/art/boss/<name>.txt (or of `path`) in file order."""
    out, cur = [], None
    for l in open(path or os.path.join(ROOT, "assets/art/boss/%s.txt" % name)).read().splitlines():
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
    # every body pose as the game shows it: the body on the bar plus every sprite drawn in that pose (src/boss.c boss_draw: the topper, the
    # capacity mugs, the hand mug; the boss files: tell effects), fight colours (the planned ones for the venue's slots). boss_notes.py has the data.
    import boss_notes as BN

    def planned(kind, slot, prefix=None):
        for q in parts:
            if q.get("kind") == kind and q.get("slot") == slot and q.get("colours") and (prefix is None or q["part"].startswith(prefix)):
                return q["colours"]
        return eff(m[("OBJ", slot)] if kind == "OBJ" else field[slot])[1:]
    red = next((q["colours"] for q in parts if q.get("kind") == "OBJ" and q.get("slot") == 4 and q.get("colours")), top)
    CK = dict(body=body, top=top, red=red, ring=planned("OBJ", 5, "Topper"), mug=planned("OBJ", 1), cap=planned("OBJ", 2))
    wall4 = lambda k: eff(field[0] if k == "bar" else field[7])
    files = {name: dict(allb), "leo_fx": dict(boss_blocks("", os.path.join(ROOT, "assets/art/leo_fx.txt"))),
             "mascot": dict(boss_blocks("mascot")), "tag": dict(boss_blocks("", os.path.join(ROOT, "assets/art/boss/tag.txt")))}
    for k in ("mascot", "critic", "yeti", "prototype", "mothership", "sasquatch", "leo"):
        files.setdefault(k, dict(boss_blocks(k)))
    drink = frames(os.path.join(VD, "%s_drink.txt" % SCENE[v["key"]]))[0]          # the venue's drink art, frame 1: the sliding full mug

    def rows_of(f, bn):
        return drink if f == "mug" else files[f][bn]

    def bbox(rows):
        ys = [y for y, r in enumerate(rows) if any(c in "-+#" for c in r)]
        xs = [x for r in rows for x, c in enumerate(r) if c in "-+#"]
        return (min(xs), min(ys), max(xs) + 1, max(ys) + 1) if xs else (0, 0, 1, 1)

    def pic(label, pose, o):
        """item list of one picture: (rows, x, y, colour key, behind). Body first."""
        o = dict(BN.OVR.get(name, {}).get(pose, {}), **o)
        rows = blocks[pose]
        bw = max(len(r) for r in rows)
        items = [(rows, (width - bw) // 2, 0, "body", False)]
        hand = HAND_BASE_ = BN.HAND_BASE[name]
        hat = o.get("hat", ("HAT_BOB" if pose == "STOMP" else "HAT_STILL", "top"))
        if hat and hat[0] in blocks:
            items.append((blocks[hat[0]], hat_dx, -8, hat[1], False))
        h = BN.HANDS[name]
        caps = o.get("caps", None if pose == "HAPPY" else ((h - 1, 1) if h > 1 else (0, 1)))
        for k in range((caps[0] + caps[1]) if caps else 0):
            items.append((files["tag"]["TAKEN" if k < caps[0] else "ROOM"], width - 8 + 8 * k, -8, "cap", False))
        if pose == "GULP" and HAND_BASE_ is not None and o.get("hand", True):
            items.append((drink, width - 8, HAND_BASE_ - 14, "mug", False))
        for f, bn, x, y, ck, behind in o.get("add", []):
            items.append((rows_of(f, bn) if f == "mug" else files[f][bn], x, y, ck, behind))
        return label, items

    pics = [pic(pn, pn, {}) for pn in ["WALK", "STOMP", "GULP", "WINCE", "HAPPY"] + BN.EXTRA[name]]
    pics += [pic(lb, base, o) for lb, base, o in BN.ADD.get(name, [])]
    x0 = y0 = 0; x1, y1 = width, 16
    y0 = -8
    for lb, items in pics:
        for rows, x, y, ck, behind in items:
            bx0, by0, bx1, by1 = bbox(rows)
            x0, y0, x1, y1 = min(x0, x + bx0), min(y0, y + by0), max(x1, x + bx1), max(y1, y + by1)
    cw, ch = x1 - x0, y1 - y0
    sc = 3

    def paint(im, rows, x, y, cols, ox, oy):
        for yy, r in enumerate(rows):
            for xx, c in enumerate(r):
                if c in "-+#" and 0 <= x - ox + xx < im.width and 0 <= y - oy + yy < im.height:
                    im.putpixel((x - ox + xx, y - oy + yy), hex2(cols["-+#".index(c)]))
    poses = []
    for lb, items in pics:
        im = Image.new("RGB", (cw, ch), hex2(wall))
        for rows, x, y, ck, behind in sorted(items, key=lambda it: not it[4]):
            if behind:                                  # drawn behind the body: paint it first, the body's pixels go over it
                paint(im, rows, x, y, CK[ck], x0, y0)
        for rows, x, y, ck, behind in items:
            if not behind:
                paint(im, rows, x, y, CK[ck], x0, y0)
        rel = "img/boss_%s_%s.png" % (name, lb.lower().replace(" ", "_"))
        im.resize((cw * sc, ch * sc), Image.NEAREST).save(os.path.join(os.path.dirname(OUT), rel), "PNG")
        poses.append((lb, rel, cw * sc, ch * sc, True))
    for lb, tiles, ck, sw_ in BN.SIDE.get(name, []):    # what lives on another bar or on the counter: its own small picture
        if ck in ("bar", "bg7"):
            c4 = wall4(ck); bgc, cols = c4[0], c4[1:]
        else:
            bgc, cols = wall, CK[ck]
        th = max(len(files[f][bn]) for f, bn, _, _ in tiles)
        im = Image.new("RGB", (sw_, th), hex2(bgc))
        for f, bn, x, y in tiles:
            paint(im, files[f][bn], x, y, cols, 0, 0)
        rel = "img/boss_%s_side_%s.png" % (name, lb.lower())
        im.resize((sw_ * sc, th * sc), Image.NEAREST).save(os.path.join(os.path.dirname(OUT), rel), "PNG")
        poses.append((lb, rel, sw_ * sc, th * sc, False))
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
    h.append('<p class="bact">%s</p>' % esc(BN.ACTS.get(name, "")))
    h.append('<ul class="bdesc">%s</ul>' % "".join("<li><b>%s</b> %s</li>" % (esc(l), esc(t)) for l, t in BN.SPR.get(name, [])))
    h.append('<div class="poses">')
    for lb, rel, pw, ph, isdl in poses:
        img = '<img class="bimg" alt="%s %s" width="%d" height="%d" src="%s">' % (esc(info.get("boss", name)), esc(lb.lower()), pw, ph, rel)
        if isdl:
            img = ('<a class="dl" href="%s" download="boss_%s_sheet.png" data-file="boss_%s_sheet.png" title="Download every %s block, editable">%s</a>'
                   % (dl, name, name, esc(info.get("boss", name)), img))
        h.append('<figure>%s<figcaption>%s</figcaption></figure>' % (img, esc(lb)))
    h.append('</div>')
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


# ---- Scene pieces: the show dancers, the keg, the stage and the floor (assets/approved/venues/<prefix>_*; tools/gen_art.py venues()) ----
# Venue key -> file prefix (= gen_art THEMES). Each piece is shown in the PLANNED colours the cards show (model m / field_model).
SCENE = dict(cowboys="saloon", sports="sports", lumberjacks="lodge", chefs="bistro", divers="igloo", robots="factory",
             punks="biker", ninjas="teahouse", zoo="zoo", aliens="space")
VD = os.path.join(ROOT, "assets/approved/venues")
POOL = 36                                     # gen_art VENUE_POOL: the stage's ids from 0 up, the bar + floor at the top
SCENE_ORDER = [("dancers", "Dancers"), ("kegs", "Kegs"), ("stage", "Stage"), ("floor", "Floor")]


def src_lines(path):
    """[(line number, text)] of a plain art file: no blank lines, no ';' comments."""
    return [(n, l.rstrip()) for n, l in enumerate(open(path).read().splitlines(), 1) if l.strip() and not l.startswith(";")]


def src_blocks(path):
    """[(first line number, rows)] of a file of blank-line separated blocks (';' comments skipped), like gen_art blocks()."""
    out, cur, n0 = [], [], 0
    for n, l in enumerate(open(path).read().splitlines() + [""], 1):
        l = l.rstrip()
        if l.startswith(";"):
            continue
        if not l:
            if cur:
                out.append((n0, cur)); cur = []
            continue
        if not cur:
            n0 = n
        cur.append(l)
    return out


def src_anim(path):
    """<prefix>_anim.txt -> (slots [(col,row)], frames [[name, first line, [8 rows, each a list of 8-px columns]]]), file order."""
    slots, frames = [], []
    for n, l in enumerate(open(path).read().splitlines(), 1):
        l = l.rstrip()
        if not l or l.startswith(";"):
            continue
        if l.startswith("!slots"):
            slots = [tuple(int(a) for a in p.split(",")) for p in l.split()[1:]]
        elif l.startswith("!"):
            continue
        elif l.startswith("@"):
            frames.append([l[1:], n, []])
        elif frames:
            frames[-1][2].append(l.split())
    return slots, frames


def cut_tiles(rows, w, h):
    return [[tuple(rows[ty * 8 + y][tx * 8:tx * 8 + 8] for y in range(8)) for tx in range(w)] for ty in range(h)]


def id_ranges(ids):
    ids = sorted(set(ids)); out = []
    for i in ids:
        if out and out[-1][1] == i - 1:
            out[-1][1] = i
        else:
            out.append([i, i])
    return ", ".join(str(a) if a == b else "%d-%d" % (a, b) for a, b in out)


def find_slot(field, item, default):
    for sl in range(8):
        if any(x[0].startswith(item) for x in field[sl]["oth"]):
            return sl
    return default


def dancer_slot(v):
    for start, kind, fr, to, label in PLANS.get(v["key"], {}).get("moves", []):
        if start == "Show dancers":
            return to
    return 5


def piece_layout(p):
    """([(x, y)] of each block on the editable sheet, (w, h)): blocks in file order in rows of at most p['width'] px, GAP px apart."""
    pos, x, y, rh, w = [], 0, 0, 0, 0
    for b in p["blocks"]:
        bw, bh = len(b["rows"][0]), len(b["rows"])
        if x and x + bw > p["width"]:
            x, y, rh = 0, y + rh + GAP, 0
        pos.append((x, y)); x += bw + GAP; rh = max(rh, bh); w = max(w, x - GAP)
    return pos, (w, y + rh)


def scene_pieces(v, m, field):
    """{piece: dict} for one venue. A piece: blocks [dict(label, rows, grid (slot per 8x8 tile), line)], pal {slot: 4 hex},
    multi (PNG index = slot*4 + colour, else the colour), trans, width (sheet flow width), sc (sheet scale), ds (shown scale),
    attr_of_slot {slot: source attribute value}, parts (the table rows)."""
    key, t = v["key"], SCENE[v["key"]]
    P = lambda s: os.path.join(VD, "%s_%s" % (t, s))
    wall = v["bg"][0][0]
    out = {}

    def part(label, ids, kind, sl, cols):
        return dict(part=label, n=len(set(ids)), ids=id_ranges(ids), kind=kind, slot=sl, cols=cols)

    # Dancers: <t>_show.txt, 4 frames (one dance) or 6 (a band), 16x24, OBJ palette, colour 0 transparent. 32 OBJ tiles.
    ds = dancer_slot(v)
    oc = eff(m[("OBJ", ds)])
    fr = src_blocks(P("show.txt"))
    quarters = []
    if len(fr) != 4:                                            # a band: 8x16 quarters, deduplicated (gen_art show_tiles)
        for _, f in fr:
            f = list(f) + ["." * 16] * 8
            for y0, x0 in ((0, 0), (0, 8), (16, 0), (16, 8)):
                q = tuple(r[x0:x0 + 8] for r in f[y0:y0 + 16])
                if q not in quarters:
                    quarters.append(q)
    ntiles = 32 if len(fr) == 4 else 2 * len(quarters)
    out["dancers"] = dict(
        file=P("show.txt"), multi=False, trans=True, width=200, sc=4, ds=4, pal={ds: [wall] + oc[1:]}, attr_of_slot={},
        blocks=[dict(label="pose %d" % (i + 1), rows=rows, grid=[[ds] * 2] * 3, line=n) for i, (n, rows) in enumerate(fr)],
        parts=[dict(part="Dancers", n=ntiles, ids="0-%d" % (ntiles - 1), kind="OBJ", slot=ds, cols=oc[1:])])

    # Stage: <t>_stage.txt 160x32 + <t>_attr.txt (0 BG 5, 1 BG 6) + the animation frames of <t>_anim.txt (one 8-px column per distinct slot tile).
    sattr = [[int(ch) for ch in r] for _, r in src_lines(P("attr.txt"))]
    srows = [r for _, r in src_lines(P("stage.txt"))]
    sg = cut_tiles(srows, 20, 4)
    grid = [[5 + a for a in r] for r in sattr]
    slots, frames = src_anim(P("anim.txt"))
    keys = []
    for c, r in slots:
        if sg[r][c] not in keys:
            keys.append(sg[r][c])
    suniq, sid = [], [[None] * 20 for _ in range(4)]
    for r in range(4):
        for c in range(20):
            if sg[r][c] not in keys:
                if sg[r][c] not in suniq:
                    suniq.append(sg[r][c])
                sid[r][c] = suniq.index(sg[r][c])
    a_first = len(suniq)
    for r in range(4):
        for c in range(20):
            if sg[r][c] in keys:
                sid[r][c] = a_first + keys.index(sg[r][c])
    colslot = []
    for k in keys:
        c, r = next((c, r) for c, r in slots if sg[r][c] == k)
        colslot.append(grid[r][c])
    blocks = [dict(label="stage", rows=srows, grid=grid, line=0, ds=2)]
    for i, (name, n, rows) in enumerate(frames):
        blocks.append(dict(label="frame %d" % (i + 1), rows=["".join(cs) for cs in rows], grid=[colslot], line=n, name=name))
    parts = []
    for anim in (False, True):
        for sl in (5, 6):
            ids = [sid[r][c] for r in range(4) for c in range(20) if grid[r][c] == sl and (sg[r][c] in keys) == anim]
            if ids:
                parts.append(part("Stage, animated" if anim else "Stage", ids, "BG", sl, eff(m[("BG", sl)])))
    out["stage"] = dict(file=P("stage.txt"), multi=True, trans=False, width=160, sc=4, ds=4,
                        pal={5: eff(m[("BG", 5)]), 6: eff(m[("BG", 6)])}, attr_of_slot={5: 0, 6: 1}, blocks=blocks, parts=parts,
                        anim=P("anim.txt"), attr=P("attr.txt"))

    # Keg: the bar piece that holds it, bar columns 17-19 (pixels 136-159, the spout and the keg), all 3 rows, with <t>_bar_attr.txt.
    bar = [r for _, r in src_lines(P("bar.txt"))]
    battr = [[int(ch) for ch in r] for _, r in src_lines(P("bar_attr.txt"))]
    wslot = find_slot(field, "Bar, wall", 0)
    kslot = find_slot(field, "Keg, spout", wslot)
    amap = {0: wslot, 1: kslot}
    bg_ = cut_tiles(bar, 20, 3)
    floor = tuple(r for _, r in src_lines(P("floor.txt")))
    buniq = []
    for row in bg_:
        for tl in row:
            if tl not in buniq:
                buniq.append(tl)
    if floor not in buniq:
        buniq.append(floor)
    sp = os.path.join(ROOT, "assets/art/splash/%s.txt" % t)
    if os.path.exists(sp):
        spl = tuple(r for _, r in src_lines(sp))
        if spl not in buniq:
            buniq.append(spl)
    base = POOL - len(buniq)
    kgrid = [[amap[battr[y][c]] for c in (17, 18, 19)] for y in range(3)]
    kparts = []
    has1 = any(battr[y][c] for y in range(3) for c in (17, 18, 19))
    for a, label in ((1, "Keg, spout"), (0, "Counter, wall" if has1 else "Keg, spout")):   # the Saloon's keg is on the bar's palette
        ids = [base + buniq.index(bg_[y][c]) for y in range(3) for c in (17, 18, 19) if battr[y][c] == a]
        if ids:
            kparts.append(part(label, ids, "BG", amap[a], eff(field[amap[a]])))
    pal = {wslot: eff(field[wslot]), kslot: eff(field[kslot])}
    out["kegs"] = dict(file=P("bar.txt"), multi=len(pal) > 1, trans=False, width=200, sc=6, ds=6, pal=pal,
                       attr_of_slot={kslot: 1, wslot: 0} if kslot != wslot else {},
                       blocks=[dict(label="keg", rows=[r[136:160] for r in bar], grid=kgrid, line=0)],
                       parts=kparts, attr=P("bar_attr.txt"))

    # Floor: <t>_floor.txt 8x8, drawn across the floor row in the bar palette.
    out["floor"] = dict(file=P("floor.txt"), multi=False, trans=False, width=200, sc=8, ds=8, pal={wslot: eff(field[wslot])}, attr_of_slot={},
                        blocks=[dict(label="tile", rows=list(floor), grid=[[wslot]], line=0)],
                        parts=[part("Floor", [base + buniq.index(floor)], "BG", wslot, eff(field[wslot]))])
    for p in out.values():
        p["pos"], p["size"] = piece_layout(p)
    return out


def piece_pixel(b, x, y):
    """(slot, colour 0-3) of a block's pixel."""
    return b["grid"][y // 8][x // 8], ".-+#".index(b["rows"][y][x])


def piece_png(p):
    """The editable indexed PNG of a piece: index = slot*4 + colour when the piece uses several palettes, else the colour."""
    from PIL import Image
    (w, h), pos = p["size"], p["pos"]
    gap = min(p["pal"]) * 4 if p["multi"] else 0
    im = Image.new("P", (w, h), gap)
    pl = [0] * (3 * (32 if p["multi"] else 4))
    for sl, cols in p["pal"].items():
        for c in range(4):
            o = 3 * ((sl * 4 if p["multi"] else 0) + c)
            pl[o:o + 3] = list(hex2(cols[c]))
    im.putpalette(pl)
    for b, (bx, by) in zip(p["blocks"], pos):
        for y, r in enumerate(b["rows"]):
            for x in range(len(r)):
                sl, c = piece_pixel(b, x, y)
                im.putpixel((bx + x, by + y), (sl * 4 if p["multi"] else 0) + c)
    return im


def piece_display(p, wall):
    """The same sheet in plain RGB, x p['sc'], gaps (and a dancer's colour 0) in the wall colour."""
    from PIL import Image
    (w, h), pos = p["size"], p["pos"]
    im = Image.new("RGB", (w, h), hex2(wall))
    for b, (bx, by) in zip(p["blocks"], pos):
        for y, r in enumerate(b["rows"]):
            for x in range(len(r)):
                sl, c = piece_pixel(b, x, y)
                im.putpixel((bx + x, by + y), hex2(p["pal"][sl][c]))
    return im.resize((w * p["sc"], h * p["sc"]), Image.NEAREST)


# ---- Tile grid (owner 2026-10-26: "the same kind of tile grid" as the atlas; then "arrange the tiles more logically so it is
# easier for me to sort through them"). The VRAM tile sheets as loaded now. Sorted view first: each thing in its own labelled
# row, sprites assembled from their 8x16 pairs (Sal, dancers: 16x32 frames, column-major; the mugs and effects pair by pair),
# patrons per look as their 8 shifted 24x16 poses and the 16x16 back view, BG art in rows of 16. The raw grids (ids 0-383 per
# bank, 16 a row) sit behind a toggle. Pink = a repeated 8x16 sprite pair (ids 0-127, pairs only), red = a repeated tile,
# yellow = an extra blank (the first copy of each is not marked).
PAT_FIRST, PAT_S0, PAT_BACK = 78, 128, 140     # build/art.h PATRON_FIRST_TILE, PATRON_SHIFT0_OFS, PATRON_TILES_PER_GROUP (BG ids; option 2: the blank pair at 126)


def bgslot(t):
    """Atlas slot (0-383) of BG id t (signed mode: 0-127 at 256-383, 128-255 shared)."""
    t &= 255
    return t if t >= 128 else 256 + t


def tile_sheets(v, model, b):
    from PIL import Image
    lv = load("level_" + v["key"])
    G = {(255, 255, 255): 0, (170, 170, 170): 1, (85, 85, 85): 2, (0, 0, 0): 3}
    tb, pk = lv[model]["tiles"][b], lv[model]["pack"]
    src = Image.open(os.path.join(os.path.dirname(DATA), pk["png"])).convert("RGB")
    gx, gy = pk["sheets"][b]["gray"]
    cx, cy = pk["sheets"][b]["colour" if model == "cgb" else "gray"]
    T = [tuple(tuple(G.get(src.getpixel((gx + (t % 16) * 8 + x, gy + (t // 16) * 8 + y)), 0) for x in range(8)) for y in range(8))
         for t in range(384)]
    sheet = src.crop((cx, cy, cx + 128, cy + 192))
    live = [tb["use"][t] != "0" or tb["loaded"][t] == "1" for t in range(384)]
    blank = tuple(tuple([0] * 8) for _ in range(8))
    mark, seen, part = {}, {}, {}              # slot -> outline colour (a pair marks both its tiles); slot -> the slot it repeats
    for t in range(384):
        if not live[t] or (t < 128 and t % 2):
            continue
        k = ("p", T[t], T[t + 1]) if t < 128 else ("t", T[t])
        if k in seen:
            if t < 128:
                mark[t] = mark[t + 1] = (255, 60, 200)
                part[t], part[t + 1] = seen[k], seen[k] + 1
            else:
                mark[t] = (255, 210, 0) if T[t] == blank else (255, 60, 60)
                part[t] = seen[k]
        seen.setdefault(k, t)
    return sheet, live, mark, part


GLYPH_DIGITS = list(range(36, 46))            # BG ids, build/art.h TILE_GLYPH_*: 0-9
GLYPH_LETTERS = [56, 65, 47, 66, 50, 71, 60, 59, 52, 72, 67, 51, 61, 68, 48, 57, 73, 49, 46, 58, 62, 53, 69, 74, 70, 75]   # A-Z in order
OBJ_LABEL = {"Mug: full": "Mug", "Mug: empty": "Mug", "Mug: drinking": "Drink in hand", "Perfect-pour sparkle": "Pour sparkle",
             "PERFECT cue": "Pour sparkle", "DMG mug copy": "DMG mug copies"}


def obj_figures(v, model):
    """Every non-patron object of the venue, assembled from its OAM pieces as drawn (x, y, tile, bank, xflip, yflip ...), grouped by
    kind. A pose whose tiles are all in a shown pose already (the mirrored copy of it) is left out. -> {label: [figure]}"""
    lv = load("level_" + v["key"])[model]
    groups, shown = {}, {}
    for o in lv["objs"]:
        if o["kind"].startswith("Patron"):
            continue
        lab = OBJ_LABEL.get(o["kind"], o["kind"])
        fig, slots = [], set()
        for x, y, t, bank, xf, yf in [pc[:6] for pc in o["pieces"]]:
            if bank:
                continue
            top, bot = (t + 1, t) if yf else (t, t + 1)
            fig += [(top, x // 8, y // 8, xf, yf), (bot, x // 8, y // 8 + 1, xf, yf)]
            slots |= {t, t + 1}
        if not fig or slots <= shown.setdefault(lab, set()):
            continue
        shown[lab] |= slots
        groups.setdefault(lab, []).append(fig)
    return groups


def tile_groups(v, model, live):
    """[(label, [figure or None for a line break], pad)]; a figure is [(slot, col, row, xflip, yflip)]. Order: sprites, patrons,
    the screen and the BG tiles, the HUD and the glyphs, then whatever is still loaded and not placed."""
    lv = load("level_" + v["key"])[model]
    placed = set()
    out = []

    def rng(figs):
        s = [t - 256 if t >= 256 else t for f in figs if f for t, *_ in f]       # BG ids (slots 256-383 are ids 0-127)
        return "%d-%d" % (min(s), max(s)) if min(s) != max(s) else str(min(s))

    def add(label, figs, pad=4, ids=True, marks=True):
        figs = [f for f in figs if f is None or f]
        if not figs:
            return
        for f in figs:
            placed.update(t for t, *_ in (f or []))
        out.append(((label + " " + rng(figs)) if ids else label, figs, pad, marks))

    pair = lambda t: [(t, 0, 0, 0, 0), (t + 1, 0, 1, 0, 0)]
    og = obj_figures(v, model)
    for lab, figs in sorted(og.items(), key=lambda kv: min(t for f in kv[1] for t, *_ in f)):
        add(lab, figs)
    add("Dust puff", [pair(t) for t in (246, 248, 250)])
    add("Boss HUD", [[(t, 0, 0, 0, 0)] for t in range(252, 256)], 2)
    # patrons: per look, the 8 shifted 24x16 poses (3 wide, 2 tall, column-major) in two lines, then the 16x16 back view
    for vi, nm in enumerate("ABC"):
        figs = []
        for sh in range(8):
            t0 = PAT_FIRST + (PAT_S0 + vi * 4 if sh == 0 else vi * 42 + (sh - 1) * 6)
            figs.append([(bgslot(t0 + k if sh or k < 4 else PAT_FIRST + PAT_S0 - 2 + k - 4), k // 2, k % 2, 0, 0) for k in range(6)])   # (shift 0: its 3rd column is the shared blank pair)
            if sh == 3:
                figs.append(None)
        t0 = PAT_FIRST + PAT_BACK + vi * 4
        figs.append([(bgslot(t0 + k), k // 2, k % 2, 0, 0) for k in range(4)])
        add("Patron " + nm, figs)
    # the screen as drawn (a representative frame's BG map), then the venue pool tiles it does not use
    scr = lv["attr"]["slot"]
    fig = [(sl, c, r, 0, 0) for r, row in enumerate(scr) for c, sl in enumerate(row)]
    add("Screen", [fig], 0, ids=False, marks=False)
    add("Pool, not on screen", [[(256 + t, 0, 0, 0, 0)] for t in range(36) if live[256 + t] and 256 + t not in placed], 2)
    add("Digits", [[(256 + t, 0, 0, 0, 0)] for t in GLYPH_DIGITS], 2)
    add("Letters", [[(256 + t, 0, 0, 0, 0)] for t in GLYPH_LETTERS[:13]] + [None] + [[(256 + t, 0, 0, 0, 0)] for t in GLYPH_LETTERS[13:]], 2)
    add("HUD, panels", [[(256 + t, 0, 0, 0, 0)] for t in (54, 55)] + [[(256 + 63, 0, 0, 0, 0), (256 + 64, 0, 1, 0, 0)], [(256 + 76, 0, 0, 0, 0)]], 2)
    # whatever is loaded and still not placed
    rest = [pair(t) for t in list(range(0, 128, 2)) + list(range(234, 256, 2)) if (live[t] or live[t + 1]) and t not in placed and t + 1 not in placed]
    add("Other sprites", rest)
    rest = [[(t, 0, 0, 0, 0)] for t in range(128, 384) if live[t] and t not in placed]
    add("Other BG", rest, 2)
    return out


def _flip(im, xf, yf):
    from PIL import Image
    if xf:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    if yf:
        im = im.transpose(Image.FLIP_TOP_BOTTOM)
    return im


def ver(m):
    f = os.path.join(os.path.dirname(OUT), m.group(0))
    try:
        return "%s?v=%s" % (m.group(0), hashlib.sha1(open(f, "rb").read()).hexdigest()[:10])
    except OSError:
        return m.group(0)


TILEMAP = {}      # image path -> {"b": VRAM bank, "r": [[x, y, slot, repeated slot or -1]]}: every 24x24 tile square in natural pixels


def tile_grid(v):
    from PIL import Image, ImageDraw, ImageFont
    S = 3
    out = []
    lv = load("level_" + v["key"])
    for model, b, label in (("cgb", 0, "Color bank 0"), ("cgb", 1, "Color bank 1"), ("dmg", 0, "DMG")):
        if b >= len(lv[model]["tiles"]):
            continue
        sheet, live, mark, part = tile_sheets(v, model, b)
        # the raw grid
        GUT = 30
        im = Image.new("RGB", (GUT + 128 * S, 192 * S), (40, 40, 40))
        im.paste(sheet.resize((128 * S, 192 * S), Image.NEAREST), (GUT, 0))
        dr = ImageDraw.Draw(im)
        for r in range(24):
            dr.text((2, r * 8 * S + 6), str(r * 16), fill=(220, 220, 220))
        for t, c in mark.items():
            dr.rectangle((GUT + (t % 16) * 8 * S, (t // 16) * 8 * S, GUT + (t % 16 + 1) * 8 * S - 1, (t // 16 + 1) * 8 * S - 1), outline=c, width=2)
        for y in (128, 256):
            dr.line((GUT, y // 16 * 8 * S, GUT + 128 * S, y // 16 * 8 * S), fill=(255, 255, 255), width=2)
        rel = "img/tiles_%s_%s%d.png" % (v["key"], model, b)
        TILEMAP[rel] = {"b": b, "r": [[GUT + (t % 16) * 8 * S, (t // 16) * 8 * S, t, part.get(t, -1)] for t in range(384)]}
        im.save(os.path.join(os.path.dirname(OUT), rel), "PNG")
        # the sorted view (bank 0 only: bank 1 holds no venue tiles yet)
        srel = None
        if b == 0:
            W = 160 * S
            fnt = ImageFont.load_default(size=12)
            groups = tile_groups(v, model, live)
            tile = lambda t, xf, yf: _flip(sheet.crop(((t % 16) * 8, (t // 16) * 8, (t % 16) * 8 + 8, (t // 16) * 8 + 8)), xf, yf).resize((8 * S, 8 * S), Image.NEAREST)
            rows = []
            for glabel, figs, pad, gmarks in groups:
                x = y = rh = 0
                placed = []
                for f in figs:
                    if f is None:
                        x, y, rh = 0, y + rh + max(pad, 2) * S, 0
                        continue
                    fw = (max(c for _, c, _, _, _ in f) + 1) * 8 * S
                    fh = (max(r for _, _, r, _, _ in f) + 1) * 8 * S
                    if x and x + fw > W:
                        x, y, rh = 0, y + rh + max(pad, 2) * S, 0
                    placed.append((f, x, y)); x += fw + pad * S; rh = max(rh, fh)
                rows.append((glabel, placed, y + rh, gmarks))
            H = sum(18 + h + 8 for _, _, h, _ in rows)
            rects = []
            im = Image.new("RGB", (W, H), (40, 40, 40))
            dr = ImageDraw.Draw(im)
            y0 = 0
            for glabel, placed, h, gmarks in rows:
                dr.text((0, y0 + 1), glabel, fill=(150, 150, 150), font=fnt)
                y0 += 18
                for f, fx, fy in placed:
                    for t, c, r, xf, yf in f:
                        px, py = fx + c * 8 * S, y0 + fy + r * 8 * S
                        im.paste(tile(t, xf, yf), (px, py))
                        rects.append([px, py, t, part.get(t, -1)])
                        if not live[t]:
                            dr.rectangle((px, py, px + 8 * S - 1, py + 8 * S - 1), fill=(60, 60, 60))
                        if gmarks and t in mark:
                            dr.rectangle((px, py, px + 8 * S - 1, py + 8 * S - 1), outline=mark[t], width=2)
                y0 += h + 8
            srel = "img/tiles_%s_%s_sorted.png" % (v["key"], model)
            TILEMAP[srel] = {"b": 0, "r": rects}
            im.save(os.path.join(os.path.dirname(OUT), srel), "PNG")
        out.append((label, rel, srel))
    fig = lambda label, rel: ('<figure><figcaption>%s</figcaption><img class="tgimg" src="%s" alt="%s %s tiles"></figure>'
                              % (label, rel, esc(v["name"]), label))
    h = ['<div class="ph2"><h2>Tile grid</h2></div><p class="foot"><span style="color:#ff3cc8">Pink</span> repeated sprite pair · '
         '<span style="color:#ff3c3c">Red</span> repeated tile · <span style="color:#e0b000">Yellow</span> extra blank · Grey unused · A tile shows in every picture it belongs to; mirrored poses once</p><div class="tgrid">']
    h += [fig(label, srel) for label, rel, srel in out if srel]
    h.append('</div><details class="tdet"><summary>VRAM order</summary><div class="tgrid">')
    h += [fig(label, rel) for label, rel, srel in out]
    h.append("</div></details>")
    return "".join(h)


def scene_sections(v, m, field):
    pieces = scene_pieces(v, m, field)
    wall = v["bg"][0][0]
    odir = os.path.dirname(OUT)
    os.makedirs(os.path.join(odir, "img"), exist_ok=True)
    h = []
    for name, title in SCENE_ORDER:
        p = pieces[name]
        stem = "img/scene_%s_%s" % (v["key"], name)
        piece_display(p, wall).save(os.path.join(odir, stem + ".png"), "PNG")
        piece_png(p).save(os.path.join(odir, stem + "_1x.png"), "PNG", **({"transparency": 0} if p["trans"] else {}))
        fname = "%s_%s.png" % (v["key"], name)
        w_, h_ = p["size"]
        h.append('<div class="ph2"><h2>%s</h2></div><div class="poses">' % title)
        figs = []
        for b, (bx, by) in zip(p["blocks"], p["pos"]):
            ds = b.get("ds", p["ds"])
            figs.append((b["label"], len(b["rows"][0]) * ds, len(b["rows"]) * ds,
                         "background-size:%dpx %dpx;background-position:-%dpx -%dpx" % (w_ * ds, h_ * ds, bx * ds, by * ds)))
        if name == "floor":
            figs.append(("row", 160 * 2, 16, "background-size:%dpx %dpx;background-position:0 0;background-repeat:repeat-x" % (8 * 2, 8 * 2)))
        for label, bw, bh, st in figs:
            h.append('<figure><a class="dl" href="%s_1x.png" download="%s" data-file="%s" title="Download %s, editable">'
                     '<span class="crop" role="img" aria-label="%s %s %s" style="width:%dpx;height:%dpx;background-image:url(%s.png);%s"></span></a>'
                     '<figcaption>%s</figcaption></figure>'
                     % (stem, fname, fname, esc(title.lower()), esc(v["name"]), esc(title.lower()), esc(label), bw, bh, stem, st, esc(label)))
        h.append('</div><div class="tbl"><table class="pt"><thead><tr><th>Part</th><th>Tiles</th><th>Ids</th><th>Palette</th><th>Colours</th></tr></thead><tbody>')
        for q in p["parts"]:
            cols = q["cols"] if q["kind"] == "BG" else q["cols"][-3:]
            sw_ = "".join('<button type="button" class="sw" style="background:%s" data-hex="%s" title="%s"></button>' % (c, c, c) for c in cols)
            h.append('<tr><td>%s</td><td class="slotc">%d</td><td class="slotc">%s</td><td class="slotc">%s %d</td><td>%s</td></tr>'
                     % (esc(q["part"]), q["n"], esc(q["ids"]), q["kind"], q["slot"], sw_))
        h.append('</tbody></table></div>')
    return "".join(h)


# ---- Planned tile counts (owner 2026-10-26: "the amount of tiles represented by the plan, not current") ----
# Starts from the atlas capture (the game now), then the plan's tile deltas. Sources: QUEUE.md "Saloon 8 patron looks" (52 tiles a look;
# option 2, the shared blank column: 50; looks A-C bank 0, D-H bank 1, one back view at bank-0 ids 242-245), PATRON_SPEC.md (48 shifted + 4 back).
LOOK_NOW, LOOK_OPT2 = 52, 50        # tiles per look: now, option 2
LOOKS_NOW = 3                       # looks every venue has in the game today (the enhanced ROSIE / BOXY are palettes, not looks)
BACK_B0 = 4                         # the one back view at bank-0 ids 242-245 once there are looks in bank 1
FIGHT_LOOKS = 2                     # looks A and B stay loaded in a boss fight; the boss borrows look C's tiles (boss.h BOSS_BG_A / BOSS_BG_B)


def planned_tiles(v, n):
    """Planned tile counts of venue v with n looks in the plan, split by VRAM region (sprite-only 0-127; BG-reachable 128-383 = shared + BG-only).
    Patron looks are BG tiles, so only BG-reachable ids can take them."""
    t = v["tiles"]; sal = v["key"] == "cowboys"
    q = "" if sal else " ?"                                   # the Saloon's numbers are decided in QUEUE; elsewhere the same rule is assumed
    n = max(n, LOOKS_NOW); extra = n - LOOKS_NOW
    save = LOOKS_NOW * (LOOK_NOW - LOOK_OPT2)                 # option 2 on looks A-C
    fsave = FIGHT_LOOKS * (LOOK_NOW - LOOK_OPT2)
    b0 = BACK_B0 if extra else 0
    b1 = extra * LOOK_OPT2
    enh = 2 if v["key"] in ("cowboys", "robots") else 0         # the dropped enhanced look's 2 bank-1 lift tiles (ids 210, 211: enhance.c enh_b1)
    sp = lambda r: r[0]
    bg = lambda r: r[1] + r[2]
    o = dict(sp=sp(t["b0"]), bg=bg(t["b0"]) + save - b0, sp1=sp(t["b1"]), bg1=bg(t["b1"]) - b1 + enh,
             fbg=bg(t["bb"]) + fsave - b0, dbg=bg(t["d"]) + save)
    o["used"] = 384 - o["sp"] - o["bg"]
    o["dused"] = 384 - t["d"][0] - o["dbg"]
    nowtxt = "Game now: bank 0 free %d sprite-only + %d BG (used %d); bank 1 free %d sprite-only + %d BG; boss fight free BG %d; DMG free BG %d (used %d)." % (
        sp(t["b0"]), bg(t["b0"]), 384 - sum(t["b0"]), sp(t["b1"]), bg(t["b1"]), bg(t["bb"]), bg(t["d"]), 384 - sum(t["d"]))
    L = [nowtxt,
         "Free means empty (not loaded, not referenced in the capture) and reachable: sprite-only ids 0-127, BG ids 128-383 (shared 128-255 + BG-only 256-383). Looks are BG tiles, so only BG counts for them.",
         "Looks in the plan: %d (now %d)%s." % (n, LOOKS_NOW, "" if n != LOOKS_NOW else "; no more are planned here ?"),
         "-%d per look, option 2, x %d looks (A-C): +%d free BG in bank 0 and on DMG%s." % (LOOK_NOW - LOOK_OPT2, LOOKS_NOW, save, "" if sal else " ?")]
    if extra:
        L.append("+%d looks x %d in bank 1 (BG ids): bank 1 free BG -%d%s." % (extra, LOOK_OPT2, b1, q))
        L.append("One back view in bank 0 (ids 242-245): bank 0 free BG -%d, boss fight -%d%s." % (b0, b0, q))
        L.append("Back views of the other new looks share that one ?")
        L.append("New looks are Color only: DMG unchanged.")
    L.append("Boss fight: the capture, +%d for option 2 on the two looks that stay loaded (A, B; the boss borrows C's tiles), -%d back view%s." % (fsave, b0, q))
    if sal:
        L.append("QUEUE fit-check (Saloon, 16-px art): normal play bank 0 about 23, bank 1 6. Here: bank 0 %d = %d now + %d option 2 - %d back view: matches. Bank 1 %d = %d now - %d looks + %d lift tiles of the dropped ROSIE: matches." % (
            o["bg"], bg(t["b0"]), save, b0, o["bg1"], bg(t["b1"]), b1, enh))
        L.append("QUEUE fit-check: Big Tex fight bank 0 about 6, bank 1 6. Here: bank 0 %d = %d in the capture + %d - %d; bank 1 %d. Bank 1 matches. Bank 0 is %d above the estimate: the capture already has the boss in look C's place, and no sprite-only tile is counted, so it is none of the three suspects; the source of the 6 is not recorded ?" % (
            o["fbg"], bg(t["bb"]), fsave, b0, o["bg1"], o["fbg"] - 6))
        L.append("The first version of this page counted sprite-only ids as free (that was the whole gap: bank 0 showed 41 = 18 sprite-only + 23 BG).")
    if v["key"] in ("cowboys", "robots"):
        L.append("Enhanced look dropped (%s): its 2 bank-1 lift tiles (ids 210, 211, loaded by enhance_load) are freed: bank 1 free BG +%d%s." % ("ROSIE" if sal else "BOXY", enh, q))
    L.append("Dancers moved to other palettes and palette variants: 0 tiles.")
    o["lines"] = L
    return o


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
    tl = planned_tiles(v, len(ident) + len(reserved))
    w('<div class="stat"><b>%d</b><span>tiles used</span></div>' % tl["used"])
    w('<div class="stat"><b>%d</b><span>free BG</span></div>' % tl["bg"])
    w('<div class="stat"><b>%d</b><span>free sprite-only</span></div>' % tl["sp"])
    w('<div class="stat"><b>%d</b><span>free bank 1 BG</span></div>' % tl["bg1"])
    w('<div class="stat"><b>%d</b><span>free bank 1 sprite-only</span></div>' % tl["sp1"])
    w('<div class="stat"><b>%d</b><span>boss fight free BG</span></div>' % tl["fbg"])
    w('<div class="stat"><b>%d</b><span>tiles used DMG</span></div>' % tl["dused"])
    w('<div class="stat"><b>%d</b><span>free BG DMG</span></div>' % tl["dbg"])
    w('</div><details class="tdet"><summary>Tile breakdown, planned</summary><ul>%s</ul></details>' % "".join("<li>%s</li>" % esc(x) for x in tl["lines"]))
    w('<h2>Sprite palettes</h2><div class="grid">')
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
    w(scene_sections(v, m, field))
    w(tile_grid(v))
    w('</section>')
w('<p class="foot">This is the plan. <span style="color:var(--now)">Green</span>: patrons as in the game today. <span style="color:var(--plan)">Yellow</span>: planned changes. Click a colour to copy it. '
  'From the atlas, main %s, %s.</p>' % (esc(commit), LOG[-1][0]))
w('</div><div id="toast" role="status" aria-live="polite" hidden></div>')
w('<script type="application/json" id="tmap">%s</script>' % json.dumps(TILEMAP, separators=(",", ":")).replace("</", "<\\/"))
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
w("""<script>
(function () {
  var map = {}, out, tip, cur = null;
  try { map = JSON.parse(document.getElementById("tmap").textContent); } catch (e) {}
  function name(m, s) {
    if (m.b) return "bank 1 \u00b7 " + s;
    return s < 128 ? "OBJ " + s : s < 256 ? "Tile " + s : "BG " + s + " \u00b7 " + (s - 256);
  }
  function hide() { cur = null; if (out) out.hidden = true; if (tip) tip.hidden = true; }
  function show(img, e) {
    var m = map[(img.getAttribute("src") || "").split("?")[0]];
    if (!m || !img.naturalWidth) return hide();
    var b = img.getBoundingClientRect(), k = b.width / img.naturalWidth, x = (e.clientX - b.left) / k, y = (e.clientY - b.top) / k, r = null, i;
    for (i = 0; i < m.r.length; i++) { var q = m.r[i]; if (x >= q[0] && x < q[0] + 24 && y >= q[1] && y < q[1] + 24) { r = q; break; } }
    if (!r) return hide();
    if (!out) {
      out = document.createElement("div"); out.id = "tout"; document.body.appendChild(out);
      tip = document.createElement("div"); tip.id = "ttip"; tip.setAttribute("role", "tooltip"); document.body.appendChild(tip);
    }
    var sx = window.pageXOffset, sy = window.pageYOffset;
    out.hidden = tip.hidden = false;
    out.style.left = (b.left + sx + r[0] * k) + "px"; out.style.top = (b.top + sy + r[1] * k) + "px";
    out.style.width = out.style.height = (24 * k) + "px";
    tip.textContent = name(m, r[2]) + (r[3] >= 0 ? " = " + r[3] : "");
    var w = tip.offsetWidth, l = Math.min(Math.max(4, b.left + r[0] * k), document.documentElement.clientWidth - w - 4), t = b.top + r[1] * k - tip.offsetHeight - 6;
    if (t < 4) t = b.top + (r[1] + 24) * k + 6;
    tip.style.left = (l + sx) + "px"; tip.style.top = (t + sy) + "px";
    cur = img;
  }
  document.addEventListener("pointermove", function (e) { var i = e.target.closest && e.target.closest("img.tgimg"); if (i && e.pointerType === "mouse") show(i, e); else if (cur && e.pointerType === "mouse") hide(); });
  document.addEventListener("pointerdown", function (e) { var i = e.target.closest && e.target.closest("img.tgimg"); if (i) show(i, e); else hide(); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") hide(); });
})();
</script>""")
for i, x in enumerate(S):         # a changed picture gets a new URL: img/<file>.png -> img/<file>.png?v=<first 10 hex of its sha1>
    if "id=\"tmap\"" not in x:
        S[i] = re.sub(r'img/[A-Za-z0-9_.-]+\.png(?![?\w])', ver, x)
open(OUT, "w").write("\n".join(S) + "\n")
print("wrote", OUT)
