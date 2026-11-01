"""The Graphics Atlas's hand-kept plan data (owner decisions), as plain data: no atlas capture, no ROM needed, so tests can import it.
build.py does `from plan_data import *`. Everything the game already says (the Saloon's looks and palette instances, slot numbers) is checked against
game_truth by self_check.py."""
# Patron names (tools/gen_credits.py PATRONS, art order A, B, C) and short descriptions where the art notes give one.
NAMES = {
    "cowboys": ["DUSTY, the cowboy", "EMMA, the singer", "GUS, the prospector", "HANK, the ranch hand", "ROSIE, the singer", "REDD, the outlaw",
                "MABEL, the lace shawl", "ARTIE, the priest"],   # the game's 8 looks in order (look 0-2 bank 0, 3-7 Color only); patron palettes below
    "sports": ["PETE, the cap fan", "NORM, the ref", "SERENA, the band fan"],
    "lumberjacks": ["CEDAR, in the cap", "WILLOW, red hair", "ASH, in the green hat"],
    "chefs": ["PIERRE", "BRIE", "BASIL"],
    "divers": ["IGGY, the parka man", "POLLY, the parka girl", "MOOSE, the big parka"],
    "robots": ["BOXY", "VOLTA", "BLIP"],
    "punks": ["PUNK, pink mohawk", "HARLEY, green bandana", "BABY, blue quiff"],
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
        q=["Q44","Q46","Q48","2026-10-21"],   # the Qn (or dated owner statement) behind this venue's plan: self_check.check_plan refuses an entry without one
        moves=[("Show dancers", "OBJ", 5, 1, "Show dancers")],
        recolour={("OBJ", 1): {1: "#FFE6CD"}},                               # the full mug's cream to the tan; the dancers share it
        open={},
        why="Owner 2026-10-21: the dancers share the full mug's palette (OBJ 1) in the tan. The 8 looks, their palettes and variants are in the game (batch 2).",
    ),
    "sports": dict(
        q=["Q16","Q45","Q49","Q58","2026-10-21","2026-10-29"],   # the Qn (or dated owner statement) behind this venue's plan: self_check.check_plan refuses an entry without one
        moves=[("PETE", "OBJ", 3, 1, "PETE, the cap fan"), ("Show dancers", "OBJ", 5, 1, "Cheerleaders"),
               ("NORM", "OBJ", 6, 0, "NORM, the ref")],
        recolour={("OBJ", 1): {1: TAN}, ("OBJ", 2): {1: TAN}, ("BG", 2): "OBJ 1", ("BG", 4): "OBJ 0"},
        open={},
        join={("OBJ", 2): ["LOUIS"], ("OBJ", 1): ["FRANK"]},   # owner 2026-10-29: LOUIS takes the reserved patron slot; FRANK shares PETE's
        field_moves=[("Keg, spout", 1, 0)],          # playfield: BG 0 takes BG 1's (keg / spout) palette and the keg / spout share it
        why="Owner 2026-10-21: OBJ 1's white pushed toward tan serves PETE and the cheerleaders; NORM uses Sal's OBJ 0; OBJ 2 gets the same push and becomes a patron palette.",
    ),
    # owner 2026-10-25: every recommended and optional merge on the Palette Merges page (tools/artifacts/palette_merges/build.py MERGES)
    "lumberjacks": dict(
        q=["Q59","Q60","2026-10-25","2026-10-29","Q86"],   # the Qn (or dated owner statement) behind this venue's plan: self_check.check_plan refuses an entry without one
        moves=[("Show dancers", "OBJ", 5, 1, "Sasquatch"), ("WILLOW", "OBJ", 6, 3, "WILLOW, red hair"), ("WILLOW", "BG", 3, 2, "WILLOW, red hair")],
        recolour={("OBJ", 7): {1: "#C08858"}, ("BG", 4): "OBJ 7"},   # Q86 (owner 2026-10-31): "Ash to medium"
        open={},
        join={("OBJ", 1): ["BOONE"]},   # owner 2026-10-29: BOONE shares the Sasquatch's palette
        why="Owner 2026-10-25: the Sasquatch shares the full mug (foam to cream); CEDAR and WILLOW share CEDAR's palette (WILLOW's navy goes).",
    ),
    "chefs": dict(
        q=["Q57","Q59","2026-10-25"],   # the Qn (or dated owner statement) behind this venue's plan: self_check.check_plan refuses an entry without one
        moves=[("PIERRE", "OBJ", 3, 0, "PIERRE"), ("BRIE", "OBJ", 6, 0, "BRIE"), ("Show dancers", "OBJ", 5, 0, "Waiter"),
               ("BRIE", "BG", 3, 2, "BRIE")],
        recolour={("BG", 2): "OBJ 0"},
        open={},
        why="Owner 2026-10-25: PIERRE, BRIE and the waiter use Sal's OBJ 0; PIERRE and BRIE walk in BG 2 in Sal's colours.",
    ),
    "divers": dict(
        q=["Q43","Q55","2026-10-25"],   # the Qn (or dated owner statement) behind this venue's plan: self_check.check_plan refuses an entry without one
        moves=[("Show dancers", "OBJ", 5, 0, "Penguin")],
        recolour={}, open={},
        why="Owner 2026-10-25: the penguin uses Sal's OBJ 0 (its orange beak and feet turn peach).",
    ),
    "punks": dict(
        q=["Q43","2026-10-25"],   # the Qn (or dated owner statement) behind this venue's plan: self_check.check_plan refuses an entry without one
        moves=[("Show dancers", "OBJ", 5, 6, "The band")],
        recolour={("BG", 3): "OBJ 6", ("OBJ", 6): {1: "#8C5A3C"}},   # Q81 (owner 2026-10-31): HARLEY's skin deep
        open={},
        why="Owner 2026-10-25: the band shares HARLEY's palette. 2026-10-31: HARLEY deep skin (Q81).",
    ),
    "ninjas": dict(
        q=["Q43","Q51","2026-10-25","2026-10-30"],   # the Qn (or dated owner statement) behind this venue's plan: self_check.check_plan refuses an entry without one
        moves=[("Show dancers", "OBJ", 5, 6, "Taiko drummer"),
               ("RONIN", "OBJ", 7, 6, "RONIN"), ("RONIN", "BG", 7, 6, "RONIN")],   # owner 2026-10-30: "ronin to sakua's palette."
        recolour={("BG", 3): "OBJ 6"},
        open={},
        why="Owner 2026-10-25: the taiko drummer shares SAKURA's palette. 2026-10-30: \"Poet and sensei to sals palette.\" (OBJ 0; BG 5 takes its colours); then RONIN to SAKURA's OBJ 6 / BG 6 and POET his own brown-shirt palette on the freed OBJ 7 / BG 7.",
    ),
    "zoo": dict(
        q=["Q43","2026-10-25"],   # the Qn (or dated owner statement) behind this venue's plan: self_check.check_plan refuses an entry without one
        moves=[("COCO", "OBJ", 3, 1, "COCO, the monkey")],
        recolour={("BG", 2): "OBJ 1"},
        open={},
        why="Owner 2026-10-25: COCO shares the full mug's palette (foam to tan).",
    ),
    "robots": dict(
        q=["Q13","Q43","2026-10-29"],   # the Qn (or dated owner statement) behind this venue's plan: self_check.check_plan refuses an entry without one
        moves=[("Show dancers", "OBJ", 5, 0, "Show dancers"),
               ("BLIP", "OBJ", 7, 4, "BLIP"), ("BLIP", "BG", 7, 4, "BLIP")],   # owner 2026-10-29: "Put blip in neka's palette by default."
        recolour={}, open={},
        add={("OBJ", 4): ("NEKA", ["#58F0F8", "#7888A0", "#101828"])},          # Color-only 4th look on the cyan pair (the one BOXY gave up)
        join={("OBJ", 7): ["TELLY"]},                                            # owner 2026-10-29: TELLY in BLIP's colours (was his own mint OBJ 5)
        why="Owner 2026-10-27/28: NEKA takes the cyan palette; TELLY is a mint robot with its own palette. Both Color only. Q13: the dancers share Sal's OBJ 0, freeing OBJ 5 for TELLY.",
    ),
    "aliens": dict(
        q=["Q35","Q37","Q43","Q53","Q68","Q69","2026-10-25"],   # the Qn (or dated owner statement) behind this venue's plan: self_check.check_plan refuses an entry without one
        add={("OBJ", 6): ("DASH", ["#F8E0C8", "#E03830", "#301818"])},     # Color-only 4th look (Q68/Q69), Stadium A's colours (assets/palettes.json sports_a); OBJ 3 or 6 is free: OBJ 6 (BG 3 is XENO's)
        moves=[("ZORP", "OBJ", 3, 1, "ZORP, eye stalks"), ("XENO", "OBJ", 6, 2, "XENO, the grey one")],
        recolour={("BG", 2): "OBJ 1"},
        open={},
        bg={"VENUS": 3},   # owner Q53 2026-10-29: the bar (BG 0) takes XENO's colours and XENO walks in it, freeing BG 3
        why="Owner 2026-10-25: ZORP shares the full mug's palette, XENO the empty mug's. Check the Space boss's OBJ 2 use. 2026-10-29: XENO walks in the bar's BG 0.",
    ),
}
# Color-only extra looks that are PLANNED, not in the game (Q68-Q78): listed in amber and counted as planned. Their art is art/<venue>_<name>.txt
# (+ _back.txt), copied from docs/dev/concepts. The game_truth / self_check "now" checks never see them: they are not in NAMES, users() or the capture.
EXTRA_LOOKS = {"aliens": ["DASH"], "robots": ["NEKA", "TELLY"]}
# The owner's new Color-only patrons (picks 2026-10-29, docs/dev/concepts/new_patrons/PICKS.md), not imported yet: planned, no OBJ slot
# yet. Fronts and backs copied into art/<venue>_<name>(_back).txt; colours are each concept's own palette.
NEW_PATRONS = {
    "sports": [("FRANK", ["#F8E0C8", "#E03830", "#301818"]), ("PIPER", ["#F0C098", "#D09850", "#182058"]), ("LOUIS", ["#F0C8A0", "#389850", "#101828"]), ("TOM", ["#A87050", "#7040B0", "#100818"]), ("MIKE", ["#A87050", "#186030", "#081008"])],
    "lumberjacks": [("BOONE", ["#F0B888", "#A8A098", "#302820"]), ("SMITH", ["#F8C090", "#988838", "#283018"]), ("ROD", ["#8C5A3C", "#488878", "#182028"]), ("INES", ["#E0A878", "#A050C0", "#281830"]),
                    ("PIP", ["#F0B888", "#A8A098", "#302820"])],   # Q66/Q67
    "chefs": [("PINOT", ["#F0F0E8", "#C88858", "#401820"]), ("NONNA", ["#F8F8F0", "#F0B888", "#202030"]), ("MIME", ["#D83040", "#F8F8F8", "#181828"]),
              ("OLIVE", ["#D8A030", "#F0D0B0", "#302018"]), ("HERB", ["#F0F0E8", "#C88858", "#401820"])],   # Q66/Q67 (owner 2026-10-30): fill to 8
    "divers": [("MUFFY", ["#E0A878", "#E85898", "#301030"]), ("CUB", ["#F0F8F8", "#E0A878", "#283050"]), ("MUSH", ["#F0F0F8", "#C08050", "#281818"]), ("FROSTI", ["#F0F0F8", "#78A8C8", "#182038"]),
               ("DENALI", ["#F0F0F8", "#C08050", "#281818"])],   # Q66/Q67
    "punks": [("DJ", ["#B07048", "#F0D040", "#181010"]), ("RAVEN", ["#F0E0F0", "#9048C0", "#180818"]), ("ROADY", ["#F0B890", "#B04828", "#181018"]),
              ("ANVIL", ["#F0B890", "#B04828", "#181018"]), ("FRINGE", ["#F0E0F0", "#9048C0", "#180818"])],   # Q66/Q67
    "ninjas": [("SENSEI", ["#F8F8F0", "#D8A070", "#302018"]), ("KON", ["#F8E8D8", "#C82838", "#181010"]), ("MONK", ["#F0C8A0", "#E07820", "#301810"]), ("POET", ["#F8E0C0", "#C89838", "#100810"]), ("HANA", ["#F8D8C0", "#30A8A0", "#182030"])],
    "zoo": [("TUCO", ["#F8F8E8", "#F89820", "#101018"]), ("ELLIE", ["#F8F8F0", "#A0A0B0", "#101010"]), ("ZIGGY", ["#F8F8F0", "#A0A0B0", "#101010"]), ("PINKY", ["#F8B0C8", "#E04880", "#301020"]),
            ("RAJA", ["#F8F8E8", "#F89820", "#101018"])],   # Q66/Q67
    "aliens": [("MOTHMA", ["#F8F0D0", "#C8A068", "#382010"]), ("GLOP", ["#D0F0F8", "#58A0F0", "#081828"]), ("LUNA", ["#F0F0F8", "#40B8A8", "#100820"]), ("VENUS", ["#C8F8F0", "#6058E0", "#180828"])],
    "robots": [("CLANK", ["#F8E8B8", "#E07838", "#201008"]), ("TOOB", ["#E8F0F8", "#9068D8", "#180830"]),
               ("PEPPER", ["#F8E8B8", "#E07838", "#201008"])],   # Q66/Q67
}
# Palette-swap picks (Q62): the OBJ slots the owner crossed out per look; every other patron OBJ slot of the venue is allowed (Color only).
VARIANT_CUTS = {"sports": {"NORM": [1, 2, 5, 6, 7], "FRANK": [2]},
                "aliens": {"ZORP": [3, 6], "XENO": [5, 6, 7], "MOTHMA": [1, 5, 6], "LUNA": [3, 6, 7], "VENUS": [3], "DASH": [1, 3]},   # owner 2026-10-30 (Q62 Space)
                "ninjas": {"SENSEI": [3, 4, 5, 6], "KAGE": [0, 7], "HANA": [0, 7], "MONK": [4], "RONIN": [0, 5], "POET": [4]},   # owner 2026-10-30 (Q62 Teahouse)
                "divers": {"FROSTI": [3, 4, 6, 7], "IGGY": [2], "MUFFY": [2], "MUSH": [2, 3, 4, 6, 7], "CUB": [3, 4, 6, 7],
                           "DENALI": [4, 6, 7], "POLLY": [2], "MOOSE": [2]},   # owner 2026-10-30 (Q69 Igloo)
                "punks": {},   # owner 2026-10-31 (Q69 Chrome Cow): "Keep all chrome cow pallets." No cuts
                "chefs": {"PIERRE": [3], "BRIE": [3], "NONNA": [3], "MIME": [0, 4, 5, 6, 7], "PINOT": [3], "HERB": [3]},   # owner 2026-10-31 (Bistro, third marked grid: BRIE 3 cut, BASIL keeps all with his new front)
                "zoo": {"COCO": [4], "TUCO": [1, 7], "RAJA": [4, 7], "PINKY": [1, 6], "BAMBOO": [1, 3, 4], "ELLIE": [3, 4],
                        "ZIGGY": [1, 4, 7], "MUDDY": [1, 3]},   # owner 2026-10-31 (Q69 Zoo, marked grid)
                "robots": {},   # owner 2026-10-31 (Q69 Factory): "Robots keep all swaps."
                "lumberjacks": {"BOONE": [5, 6, 7], "WILLOW": [5, 6, 7]}}   # owner 2026-10-31 (Q69 Lodge, marked grid)
# Owner 2026-10-29: "Auto assigned palettes to new patrons where available make suggestions for palette merges."
# Own palette where an OBJ slot and a playfield BG slot are free: (OBJ, BG, name), the concept's colours.
AUTO_OWN = {
    "sports": [(4, 4, "PIPER"), (5, 5, "TOM"), (6, 6, "MIKE")],
    "lumberjacks": [(4, 4, "SMITH"), (5, 5, "ROD"), (6, 3, "INES")],
    "chefs": [(3, 3, "MIME"), (4, 4, "OLIVE")],   # Q66 (owner 2026-10-30): the Bistro's free OBJ 4 / BG 4; HERB moved to OBJ 7 (owner 2026-10-31)
    "divers": [(4, 4, "MUFFY"), (5, 5, "MUSH")],
    "punks": [(4, 4, "RAVEN"), (5, 5, "ROADY"), (2, 2, "DJ")],   # Q83 (owner 2026-10-31): DJ yellow on the OBJ 2 the mug change freed, free BG 2
    "ninjas": [(4, 4, "HANA"), (5, 2, "MONK"), (7, 7, "POET")],   # owner 2026-10-30: MONK in his orange concept colours on the freed OBJ 5 and the free BG 2
    "zoo": [(3, 3, "TUCO"), (4, 4, "PINKY")],
    "aliens": [(3, 5, "MOTHMA"), (4, 4, "LUNA")],
    "robots": [(5, 5, "TOOB")],                 # owner 2026-10-29: "With the freed up slot, lets make Bubble Purple again."
}
# Concepts drawn in an existing patron's colours (within a few RGB steps): they share that palette, no slot spent.
AUTO_SHARE = {"chefs": {0: ["NONNA"], 7: ["PINOT", "HERB"]}, "punks": {4: ["FRINGE"], 5: ["ANVIL"]},   # Q66: FRINGE in RAVEN's, ANVIL in ROADY's
              "lumberjacks": {1: ["PIP"]},   # Q66: PIP in BOONE's (the Sasquatch's OBJ 1)
              "ninjas": {6: ["KON"], 0: ["SENSEI"]}, "zoo": {6: ["ELLIE", "ZIGGY"], 3: ["RAJA"]},
              "divers": {5: ["CUB", "DENALI"], 2: ["FROSTI"]}, "robots": {1: ["CLANK", "PEPPER"]},       # Q43 (owner 2026-10-29)
              "aliens": {4: ["GLOP"], 5: ["VENUS"]}}          # owner 2026-10-29: GLOP in LUNA's palette; VENUS on OBJ 5
# Q43: "Sensei & poet -- blend colors so closer together but matching neither." Their shared OBJ 5 palette, halfway between.
_NP_BLEND = {"POET": ["#F8D8C0", "#905830", "#100810"]}   # owner 2026-10-30: "Give poet his own with brown shirt." (colour 2: sleeves, hat brim)
_NP = {n: c for _l in NEW_PATRONS.values() for n, c in _l}
_NP.update(_NP_BLEND)
for _v, _l in AUTO_OWN.items():
    for _o, _b, _n in _l:
        PLANS[_v].setdefault("add", {})[("OBJ", _o)] = (_n, _NP[_n])
        if _b != _o:
            PLANS[_v].setdefault("bg", {})[_n] = _b
for _v, _d in AUTO_SHARE.items():
    for _o, _ns in _d.items():
        PLANS[_v].setdefault("join", {}).setdefault(("OBJ", _o), []).extend(_ns)
PLANS["ninjas"].setdefault("bg", {}).update(SENSEI=5)    # owner 2026-10-30: Sal's OBJ 0, its colours on BG 5
SWAP_PALETTES = {"chefs": ["Deep skin", "Sage"]}   # palette-only slots: swap colours for the venue's looks, no look of their own
PLANS["chefs"].setdefault("add", {})[("OBJ", 6)] = ("Deep skin", ["#FFFFF6", "#9C6038", "#201820"])   # Q70 (owner 2026-10-30): a swap palette on the free OBJ 6 / BG 6
PLANS["chefs"]["add"][("OBJ", 5)] = ("Sage", ["#D0E0A8", "#C88860", "#201820"])   # Q80 (owner 2026-10-31): sage swap palette, dark kept near-black like the others, on the freed OBJ 5 / BG 5
PLANS["chefs"].setdefault("bg", {})["NONNA"] = 2                  # PIERRE and BRIE's BG 2 (OBJ 0 is Sal's)
PLANS["lumberjacks"].setdefault("bg", {})["BOONE"] = 2          # BG 1 is the keg's: the Sasquatch colours on the free BG 2
PLANS["robots"].setdefault("bg", {})["CLANK"] = 2                 # Q43 B: the full mug's OBJ 1; BG 1 is the keg's
# A patron who shares another's OBJ palette shares that palette's BG too (owner 2026-11-01: Lodge showed -1 free BG)
PLANS["lumberjacks"]["bg"]["PIP"] = 2                            # PIP shares BOONE's OBJ 1, so BOONE's BG 2
PLANS["robots"]["bg"]["PEPPER"] = 2                              # PEPPER shares CLANK's OBJ 1, so CLANK's BG 2
for _v, _l in NEW_PATRONS.items():
    EXTRA_LOOKS.setdefault(_v, []).extend(n for n, _ in _l)
    _joined = [n for ns in PLANS[_v].get("join", {}).values() for n in ns] + [a[0] for a in PLANS[_v].get("add", {}).values()]   # given a palette slot: listed there, not as an extra
    PLANS[_v].setdefault("extras", []).extend(dict(name=n, cols=c) for n, c in _l if n not in _joined)
# Planned removals (struck through, yellow). Owner 2026-10-21: drop the enhanced looks (M14a) after the next patron revision.
DROP_ENHANCED = True
# Owner 2026-10-21: the BG palettes used above the playfield are reloaded where the playfield starts (row 5), so in the playfield
# they are free for patrons. The above-the-playfield palettes are listed in their own section.
SPLIT_PLAYFIELD = True
# Every venue (owner 2026-10-21): in the playfield the keg / spout palette moves from BG 7 to BG 1 (BG 1 is the HUD's above the playfield).
FIELD_MOVES = [("Keg, spout", 7, 1)]
import game_truth as _game_truth  # noqa: E402

SALOON_LOOKS = _game_truth.truth()["saloon"]   # the game's looks and palette instances, read from src/mirror.c sal_combo (never typed here)
# Each Saloon look's own (primary) palette instance, from the plan (owner 2026-10-22): HANK's (colours 1 and 2 swapped), DUSTY with EMMA,
# GUS with EMMA too (owner 2026-10-29), ROSIE with REDD, MABEL with ARTIE. The others in sal_combo are approved palette swaps (owner 2026-10-29: shown in their own section).
SALOON_PRIMARY = {"DUSTY": 1, "EMMA": 1, "GUS": 0, "HANK": 0, "ROSIE": 3, "REDD": 3, "MABEL": 4, "ARTIE": 4}
INST_OBJ, INST_BG = [3, 6, 7, 4, 5], [2, 3, 4, 7, 5]      # palette instance 0-4 -> OBJ slot, BG slot (the Saloon has all 5)
PATRON_SLOT = {3: 0, 6: 1, 7: 2}          # OBJ slot -> art variant A, B, C (lifted)
BG_PATRON = {2: 0, 3: 1, 4: 2}            # BG slot -> art variant (walking)
# What the engine can hold for the generated looks tables (tools/gen_looks.py): the BG slots patron palette instances may sit on. Each instance's own slot is the
# Atlas's (plan_slots.json: the BG slot listing the same patrons); BG 2, 3, 4, 7 are loaded with the level, and the Factory's chain reloads BG 5 early
# (line 31) and BG 6 late (line 39), where the playfield starts.
ENGINE_BG = {"robots": [2, 3, 4, 5, 6, 7]}
# OBJ slots a boss fight loads its own palettes into (src/boss_prototype.c: lamp OBJ 4, body OBJ 5, topper OBJ 7): a patron on one of them sits out the fight,
# and so does look 2 (the C slot's tiles are the boss's). gen_looks.py turns these into combo_boss.
BOSS_OWN_OBJ = {"robots": [4, 5, 7]}
# Jungle Zoo and Space Lounge (any boss: body BG 4 = BOSS_PAL, topper OBJ 7; the BG 4 patrons' OBJ 4 sits out too). Space: BG 0 is XENO's walking palette (the bar
# takes his colours, owner Q53), so the engine may put an instance on it; BG_PAIR: OBJ slot -> BG slot where the Atlas lists the patron on a shared BG slot (flagged:
# Space BG 3 is listed for "XENO, VENUS" with XENO's colours, but VENUS's OBJ 5 colours are the show's; she gets BG 3 in those colours, XENO the bar's BG 0).
ENGINE_BG["zoo"] = [2, 3, 4, 6, 7]
ENGINE_BG["aliens"] = [0, 2, 3, 4, 5, 6, 7]
BOSS_OWN_OBJ["zoo"] = [4, 7]
BOSS_OWN_OBJ["aliens"] = [4, 7]
BG_PAIR = {"aliens": {2: 0, 5: 3}}


# Planned art that breaks a patron rule and is shown anyway, until the artist's next pass: (venue, NAME, "front" | "back", "bottom" | "holes" | "x15").
# self_check.verify_pictures lists every other violation as an error and refuses an entry that is no longer needed. Each is a question for the owner
# or the artist, not a decision: bottom = a dark pixel on row 15 under a lighter one on row 14 (read as the old bottom outline, owner 10-29);
# holes = index 0 enclosed by the figure (a lifted patron is see-through there, unless the owner drew the gap: PLANNED_GAPS).
ART_RULE_EXCEPTIONS = {
    ("lumberjacks", "INES", "front", "bottom"): "row 15 x=14",
    ("chefs", "PINOT", "front", "bottom"): "row 15 x=4, 6, 7",
    ("chefs", "PINOT", "back", "bottom"): "row 15 x=6, 8",
    ("ninjas", "POET", "front", "bottom"): "row 15 x=12",          # the owner's drawing 2026-10-30
    ("robots", "TELLY", "front", "holes"): "(2, 1) and (3, 2) enclosed; the owner has not said it is a gap",
}
# Index-0 gaps the owner drew on purpose in planned art: (venue, NAME, side) -> {(x, y)}.
PLANNED_GAPS = {}

# PATRON_ART, the one art table: patron -> (front file, back file, source) under docs/dev/concepts/patron_pass/<venue>/ ("old" = the game's frame).
# Beyond it: art/<venue>_<name>.txt (the extras' own art) and the right-column trims; build.py art_rows / accepted / trimmed_front / back_info
# read this and nothing else for owner picks. self_check.check_art refuses a file that is missing and an entry without a source.
ART_PICKS_Q = "Q56-Q59 (owner picks 2026-10-26)"
PATRON_ART = {

    # lumberjacks, sports, robots: the owner-picked art of their later proposals is in the game (2026-10-27/28 art imports), so no entry
    "chefs": {"pierre": ("old", "old", "in the game 2026-11-01 (owner front, Q87 back)"), "brie": ("old", "old", "in the game 2026-11-01 (Q85 eyes)"), "basil": ("old", "old", "in the game 2026-11-01 (owner front, Q88 back)")},
    "punks": {"punk": ("old", "old", "Q84 (owner 2026-10-31), in the game"), "harley": ("old", "old", "Q71/Q74 (owner 2026-10-31), in the game"), "baby": ("old", "old", "Q84 (owner 2026-10-31), in the game")},
    "ninjas": {"kage": ("old", "old", ART_PICKS_Q), "sakura": ("old", "sakura_back", ART_PICKS_Q), "ronin": ("old", "ronin_v2_back", ART_PICKS_Q)},
    "zoo": {"coco": ("coco", "coco_back", ART_PICKS_Q), "bamboo": ("bamboo", "bamboo_back", ART_PICKS_Q), "muddy": ("old", "old", ART_PICKS_Q)},
    "aliens": {"zorp": ("old", "zorp_v2_back", ART_PICKS_Q), "xeno": ("old", "xeno_v2_back", ART_PICKS_Q), "glorp": ("glorp_v2", "glorp_v2_back", ART_PICKS_Q)},
}
