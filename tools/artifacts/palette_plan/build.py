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
    dict(slot=0, now="Sal, tip coin", planned="Same", looks=0, bg="-", status="fixed",
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
    ("2026-10-31", "Q69 Lodge (owner's marked grid): swaps cut: BOONE OBJ 5, 6, 7; WILLOW OBJ 5, 6, 7. Everyone else keeps all. Q69 closed: every venue's swaps decided. Color only."),
    ("2026-10-31", "Q87 (owner): \"C, but center his head on his body.\" PIERRE's new back = option C with the head moved 1 px left (docs/dev/concepts/patron_pass/chefs/pierre_owner_back.txt). DMG and Color; held for the game."),
    ("2026-10-31", "Q86 (owner): \"Ash to medium, rod to dark.\" Lodge OBJ 7 (ASH) skin #946A00 -> #C08858; ROD's OBJ 5 skin #F8C090 -> #8C5A3C. Color only; ASH's DMG greys unchanged; held for the game."),
    ("2026-10-31", "Owner drew a new PIERRE front (outlined toque, white moustache and beard): patron_pass/chefs/pierre_owner.txt; back still the game's; held. DMG and Color."),
    ("2026-10-31", "Q69 (owner): \"Robots keep all swaps.\" Robot Factory: no cuts. Color only."),
    ("2026-10-31", "Q85 (owner): \"Taller eyes help. Yes.\" PIERRE and BRIE get 2 px eyes (patron_pass/chefs/*_eyes.txt); into the game when the patron hold lifts. DMG and Color."),
    ("2026-10-31", "Q69 (owner, marked grid): Zoo cuts COCO 4; TUCO 1, 7; RAJA 4, 7; PINKY 1, 6; BAMBOO 1, 3, 4; ELLIE 3, 4; ZIGGY 1, 4, 7; MUDDY 1, 3. Color only."),
    ("2026-10-31", "Q69 (owner, marked grid): Bistro cuts PIERRE, NONNA and HERB in OBJ 3 (MIME's palette); every other swap stays. Color only."),
    ("2026-10-31", "Q69 (owner): \"Keep all chrome cow pallets. They all look good alternate looks across all.\" Chrome Cow: no swap cuts. Color only."),
    ("2026-10-31", "Q82 (owner): \"Ziggy b\". ZIGGY = pass A, face stripe moved down level with the eye; back pass A. Color only."),
    ("2026-10-31", "Q83 (owner): \"Do yellow.\" DJ gets his own palette #B07048 #F0D040 #181010 (medium skin, yellow) on the Chrome Cow OBJ 2 / BG 2 once the mug change frees OBJ 2. Q81 (owner): HARLEY's OBJ 6 to deep skin, after the mug change. Color only."),
    ("2026-10-31", "Q82 (owner): \"Ellie a, ziggy a but fix eyes.\" ELLIE = pass A (rounder head, trunk tip). ZIGGY eye fix shown for a pick. Color only."),
    ("2026-10-31", "Q80 (owner): \"I like the sage, but let's leave the background color as the black like it is for the others.\" New Bistro swap palette Sage on OBJ 5 / BG 5: #D0E0A8 #C88860 #201820. Color only."),
    ("2026-10-31", "Q71/Q74, Q79 (owner): HARLEY (woodcarver, bare arms, tank with buttons), PIERRE (shirt SB) and BRIE (shirt CUR), faces 1 px taller, imported into the game. DMG and Color."),
    ("2026-10-31", "Q76 (owner): \"Olive works as a name.\" ARTISTE renamed OLIVE (art/chefs_olive*.txt); same art and mustard palette, OBJ 4 / BG 4. Color only."),
    ("2026-10-31", "Q72 (owner): \"Now I want the artist in the mustard.\" ARTISTE OBJ 4 / BG 4 = #D8A030 #F0D0B0 #302018 (4b). Color only."),
    ("2026-10-31", "Owner: MIME's palette reordered so his white is colour 2 (the skin slot) and red colour 1: #D83040 #F8F8F8 #181828; his art's colours 1 and 2 swapped, so he looks the same. Shared with others, their skin is his white. Color only."),
    ("2026-10-31", "Owner: \"Put herb in a pallete that has his skin as the tan.\" HERB now shares PINOT and BASIL's OBJ 7 (#F0F0E8 #C88858 #401820, tan skin in colour 2); OBJ 5 / BG 5 free again. Color only."),
    ("2026-10-31", "Q75 (owner): \"Per anvil, let's use option a, but make the patch on his back red only.\" ANVIL shirt = A (dark vest, bare arms); back patch all red. Head unchanged. Color only."),
    ("2026-10-31", "Owner: \"Critics named Herb. He's a waiter.\" CRITIC renamed HERB (art/chefs_herb*.txt); same art, palette and slot (OBJ 5 / BG 5). Color only."),
    ("2026-10-30", "Q72 (owner): \"Tan is good for critic.\" OBJ 5 / BG 5 = #F8F8F0 #D09060 #201818 (5b). OBJ 4 still open. Color only."),
    ("2026-10-30", "Owner: ARTISTE had the skin/accent reversal: her colours 1 and 2 swapped (art and palette), skin now in colour 2 like every Bistro look; she looks the same. OBJ 4 = #D04858 #F0D0B0 #283868. Color only."),
    ("2026-10-30", "Q70 (owner): Bistro's free OBJ 6 / BG 6 becomes a deep-skin chef palette #FFFFF6 #9C6038 #201820, a swap palette for the Bistro looks. Color only."),
    ("2026-10-30", "Q69 Igloo (owner's marked grid): swaps cut: FROSTI OBJ 3, 4, 6, 7; IGGY 2; MUFFY 2; MUSH 2, 3, 4, 6, 7; CUB 3, 4, 6, 7; DENALI 4, 6, 7; POLLY 2; MOOSE 2. Color only."),
    ("2026-10-30", "Q68 (owner): back views. ARTISTE and DENALI kept; redrawn backs picked: CRITIC A, ANVIL A, RAJA B, PEPPER A, PIP B. FRINGE back: C (second redraw)."),
    ("2026-10-30", "Q66/Q67 (owner): every venue to 8 patrons, Color only. Bistro: ARTISTE (OBJ 4 / BG 4) and the food critic CRITIC (OBJ 5 / BG 5), own new palettes. Chrome Cow: ANVIL in ROADY's, FRINGE (with VEIL's shirt) in RAVEN's. Lodge: PIP in BOONE's. Igloo: DENALI, the St Bernard rescue dog, in MUSH's. Zoo: RAJA, the tiger, in TUCO's. Factory: PEPPER in CLANK's. Quality pass approved (\"These look good.\")."),
    ("2026-10-30", "Q62 Teahouse (owner's marked grid): swaps cut: SENSEI OBJ 3, 4, 5, 6 (keeps 7); KAGE 0, 7; HANA 0, 7; MONK 4; RONIN 0, 5; POET 4. SAKURA and KON keep all. Color only. Q62 closed."),
    ("2026-10-30", "Q65 (owner): \"New Kon\", drawn by the owner: KON's front replaced in the plan art (Color only); the mask proposals A, B, C are set aside. Back unchanged."),
    ("2026-10-30", "Owner: \"Poet replacement\" (drawn by the owner): POET's front replaced in the plan art (Color only). Back unchanged."),
    ("2026-10-30", "Q62 Space (owner's marked grid): swaps cut: ZORP OBJ 3, 6; XENO 5, 6, 7; MOTHMA 1, 5, 6; LUNA 3, 6, 7; VENUS 3; DASH 1, 3. GLOP and GLORP keep all. Color only."),
    ("2026-10-30", "Owner: \"make his skin the same as hanas.\" POET colour 1 (skin) #F4D0A8 -> #F8D8C0, HANA's (Color only)."),
    ("2026-10-30", "Owner: \"somewhere between those two.\" POET colour 1 (skin) #F0C090 -> #F4D0A8, halfway from #F8E0C0 (Color only)."),
    ("2026-10-30", "Owner: \"poet less pale.\" POET colour 1 (skin) #F8E0C0 -> #F0C090 (Color only)."),
    ("2026-10-30", "Owner: \"monk skin less orange?\" MONK colour 1 (skin) #E8B878 -> #F0C8A0 (Color only)."),
    ("2026-10-30", "Owner: \"ronin to sakua's palette.  Give poet his own with brown shirt.\" RONIN moves to SAKURA's OBJ 6 / BG 6 (Color only; the DMG is unchanged); POET leaves Sal's OBJ 0 for his own OBJ 7 / BG 7, colour 2 brown #905830."),
    ("2026-10-30", "Owner: \"Replacements\" (5 fronts drawn by the owner): KAGE, SAKURA, RONIN in the game (DMG and Color); SENSEI and MONK in the plan art. Backs unchanged."),
    ("2026-10-30", "Owner: \"Change the whole picture. not just the color.\" RONIN's front is the owner's drawing (second version), in the game for DMG and Color; the back is unchanged."),
    ("2026-10-30", "Owner sent RONIN recoloured: OBJ 7 colour 2 #A82830 -> #902000 (rust). In the game (ninjas_c)."),
    ("2026-10-30", "Owner (Q64): \"The Atlas says BG2 is free.\" MONK gets his own orange palette (concept colours #E8B878 #E07820 #301810) on OBJ 5 and BG 2."),
    ("2026-10-30", "Owner: \"Poet and sensei to sals palette.\" Teahouse: POET and SENSEI share Sal's OBJ 0 (BG 5 takes its colours); their blended OBJ 5 is free."),
    ("2026-10-30", "Owner (Q63): \"No sensei swap.\" SENSEI keeps his colour order."),
    ("2026-10-30", "Owner (Q62, Stadium): crossed out NORM in OBJ 1, 2, 5, 6, 7 (keeps OBJ 0 and 4) and FRANK in OBJ 2; every other Stadium swap kept (VARIANT_CUTS). \"Shift pipers gold a bit more skin toned\": OBJ 4 colour 2 #D8A028 -> #D09850."),
    ("2026-10-30", "Owner (Q63): \"Norm swap doesn't work if I want him to actually be a referee.\" NORM keeps his own palette (OBJ 0) only: no colour swap, no palette variants."),
    ("2026-10-30", "Owner: \"Make zorp and glorps light colors a bit more white.\" ZORP colour 1 #F0F898 -> #F8F8C0 (the full mug shares it), GLORP colour 1 #88F8F0 -> #B8F8F0 (the boss fight's mini aliens too)."),
    ("2026-10-29", "Owner: \"Name him Mike.\" The Stadium basketball player (working name BALLER) is MIKE."),
    ("2026-10-29", "Owner (Q59): PINOT \"fix b is good\": white shirt and dark bib apron (no stripes). (Q60): \"I don't love them, But I'll just work on them manually from here. Smith b. Boon's suspenders were great. Willows back hair looked better, but needed another pass. Ines back is great.\" SMITH B, BOONE's suspenders and INES (front + back, OBJ 6 / BG 3, purple) in the plan; ROD and WILLOW left to the owner."),
    ("2026-10-29", "Q53 in the game: the Space Lounge bar (BG 0) has XENO's colours and XENO walks in BG 0; BG 3 is free (planned for VENUS)."),
    ("2026-10-29", "Owner (Q58): approved. Stadium: a basketball player (BALLER, working name) on OBJ 6 / BG 6 in forest #A87050 #186030 #081008; TOM's own palette is now purple #A87050 #7040B0 #100818 (Black, no pixel change). Approved swaps: BALLER in TOM's purple, TOM in BALLER's forest."),
    ("2026-10-29", "Owner (Q57): Bistro noses \"Better\": PIERRE, BRIE, BASIL take the face pass with noses. PINOT \"started looking like a referee\": back to the artist."),
    ("2026-10-29", "Owner picks: FRANK (apron, hot-dog logo) and LOUIS (batting helmet, face A) (Q49), PIPER (band uniform) (Q45), POET's face pass (Q51), MUFFY's face (Q55; the other Igloo faces discarded). Plan art updated."),
    ("2026-10-29", "Owner (Q53): \"It works. Use it to free the slot.\" Space Lounge: the bar takes XENO's colours, XENO walks in BG 0; BG 3 is freed for VENUS (game change in progress)."),
    ("2026-10-29", "Owner (Q48), on the every-look-every-palette sheet: moss off EMMA, MABEL, ARTIE (and GUS); added DUSTY in ROSIE's and MABEL's, EMMA in HANK's and MABEL's, GUS in ROSIE's and MABEL's, HANK in ROSIE's, ROSIE in MABEL's. 36 combinations in the game."),
    ("2026-10-29", "Owner (Q46): \"Swap gus.\" On Color GUS's colours 1 and 2 are swapped (skin in colour 1, like every Saloon look); his own palette is HANK's, EMMA's is a swap. ROSIE's red a little more orange (#C04A2C), owner: \"So the hair color looks more natural.\""),
    ("2026-10-29", "Owner (Q44): \"Moss, keep all except gus.\" GUS's old palette (OBJ 7 / BG 4) is now moss #F6BD94 #5A7B4A #182018, in the game; every Saloon look but GUS may spawn in it (DUSTY and HANK added, GUS dropped). The credits draw GUS in his own palette, EMMA's."),
    ("2026-10-29", "Owner: \"I don't need tiles used in atlas. Only those free.\" The two tiles-used stats are gone."),
    ("2026-10-29", "Owner: \"I want gus to share emma's palette. And I want hank's palette to be emma's palette, but with the color for emma's skin in the spot where [hank's jacket] is, and the color of emma's hair where [hank's] skin is.\" GUS's own palette is EMMA's OBJ 6 (his OBJ 7 stays a swap and Big Tex's); HANK's OBJ 3 / BG 2 = #8B5231 #FFD5BD #221B1A (was #8B5231 #FFE6CD #392918), in the game."),
    ("2026-10-29", "Fix: outside the Saloon, Color bank 1 holds only another screen's leftover tiles (level.c loads the Saloon's looks there only in the Saloon); the atlas counted them as used. They are free: about 254 bank-1 BG tiles per venue."),
    ("2026-10-29", "Owner: \"Having all of the first row of pixels cleared in the patrons should free up some tiles.\" (the right column, x=15). Tile stats count 2 fewer per look: the shift-1 pose fits 2 tile columns (engine change needed)."),
    ("2026-10-29", "Owner: \"with the saloon, and the ones to come when I get there, only show the primary patron palettes up top. Have a second section for approved palette swaps somewhere below.\" Cards and the Patrons table show each look's own palette (the plan's: HANK OBJ 3, DUSTY and EMMA OBJ 6, GUS OBJ 7, ROSIE and REDD OBJ 4, MABEL and ARTIE OBJ 5, in the game's numbers); the other sal_combo palettes are in Palette swaps. Fixes ARTIE's back showing his beard and skin swapped (it was drawn in HANK's swapped palette)."),
    ("2026-10-29", "Owner: \"Make sure all of the backs in the atlas are current.\" 11 backs (BRIE, BASIL, PUNK, HARLEY, BABY, RONIN, COCO, BAMBOO, ZORP, XENO, GLORP) showed the old pass files with the bottom outline; they now show the game's. NEKA, TELLY and DASH lose the bottom outline like the rest (front and back). MABEL's back is the game's, kept."),
    ("2026-10-29", "Owner: stats tiles at the top turn red when the planned patrons and content do not fit a limit (palettes still to assign count against the free ones; tiles below 0 free). GLOP's back fish mirrored (owner)."),
    ("2026-10-29", "Owner renamed patrons: TOOB -> TELLY, BUBBLE -> TOOB, MUSHER -> MUSH, YETI -> FROSTI, TRAPPER -> BOONE, RANGER -> SMITH, ANGLER -> ROD, SOMMELIER -> PINOT, SLICK -> BABY, SPIKE -> PUNK, BIKER -> ROADY, BANDIT -> HARLEY, SKATER -> HANA, KITSUNE -> KON, MOTH -> MOTHMA, Astronaut -> DASH, BLOB -> GLOP, VIXEN_B -> LUNA, VIXEN_D -> VENUS, SLUGGER -> LOUIS, BUGLE -> PIPER, GRIDIRON -> TOM. Older log lines keep the old names."),
    ("2026-10-29", "Q16/Q17 Owner: \"Q17 looks good. Put in atlas as planned.\" 25 fronts with the right pixel column cleared shown as planned fronts (amber); not in the game yet."),
    ("2026-10-29", "Owner: \"Put blip in neka's palette by default.\" Factory: BLIP moves to NEKA's OBJ 4 / BG 4 (Color only); TOOB keeps the green OBJ 7 / BG 7 with the boss."),
    ("2026-10-29", "Owner: \"TOOB looks good in blips colors. Lets make that change.\" Factory: TOOB shares BLIP's OBJ 7 / BG 7; owner: \"With the freed up slot, lets make Bubble Purple again.\" BUBBLE back in his own purple on OBJ 5 / BG 5. Space BLOB front: the fish bones one pixel row lower (owner)."),
    ("2026-10-29", "Owner: \"Vixen D: Use Obj 5. Blob: Use Vixen B palette.\" Space: OBJ 4 / BG 4 is VIXEN_B's palette with BLOB; VIXEN_D shares the show dancers' OBJ 5 (no BG free yet)."),
    ("2026-10-29", "Q43 (owner): \"Musher, none--instead move cub to musher's palette. Yeti: a. Clank: B. Bubble: A. Sensei & poet -- blend colors so closer together but matching neither. Rest: I will look at palettes myself. Leave them unassigned.\" Igloo OBJ 5 is MUSHER's palette with CUB; YETI in the empty mug's OBJ 2 / BG 2. Factory CLANK in the full mug's OBJ 1 / BG 2, BUBBLE with NEKA. Teahouse SENSEI and POET share a blend on OBJ 5. MONK, VIXEN_B, VIXEN_D unassigned."),
    ("2026-10-29", "Owner: \"Auto assigned palettes to new patrons where available make suggestions for palette merges.\" Own palettes: Stadium BUGLE 4, GRIDIRON 5; Lodge RANGER 4, ANGLER 5; Bistro MIME 3; Igloo MUFFY 4, CUB 5; Chrome Cow RAVEN 4, BIKER 5; Teahouse SKATER 4, POET 5; Zoo TUCO 3, PINKY 4; Space MOTH OBJ 3 / BG 5, BLOB 4. Same colours, shared: NONNA with PIERRE, SOMMELIER with BASIL, DJ with SLICK, KITSUNE with SAKURA, ELLIE and ZIGGY with BAMBOO. TRAPPER's BG on BG 2. Merges suggested (Q43) for MUSHER, YETI, CLANK, BUBBLE, SENSEI, MONK, VIXEN_B, VIXEN_D."),
    ("2026-10-29", "Owner: \"Trapper can use Sasquatch palette\" Lumber Lodge: TRAPPER in OBJ 1 with the Sasquatch and the full mug."),
    ("2026-10-29", "Owner: \"Put slugger in the reserved patron color slot in stadium. Frank shares Pete's palette.\" Stadium: SLUGGER in OBJ 2, FRANK in OBJ 1 with PETE."),
    ("2026-10-29", "Owner: \"None of my new patrons are in the atlas.\" The 32 picked Color-only patrons (Stadium 4, Lodge 3, Bistro 3, Igloo 4, Chrome Cow 3, Teahouse 5, Zoo 4, Space 4, Factory 2) added as planned looks with their backs; palettes to assign."),
    ("2026-10-28", "Planned Color-only extra looks added (amber): Space Lounge Astronaut (Stadium A colours), Robot Factory NEKA (cyan) and TOOB (mint); front and back as accepted by the owner."),
    ("2026-10-27", "Saloon looks in the game (batch 2, Color): the 8 looks; built with EMMA on OBJ 6 and MABEL/ARTIE on OBJ 5 (the plan's 5 and 6 swapped)."),
    ("2026-10-27", "Factory: BOXY yellow on Color; the cyan palette goes to NEKA, a Color-only 4th robot (owner art)."),
    ("2026-10-28", "Q13 Owner: \"Dancers share.\" Factory dancers share Sal's OBJ 0; TOOB takes OBJ 5 / BG 5."),
    ("2026-10-28", "Factory: the mint robot is TOOB, a Color-only extra robot with its own palette (owner art)."),
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
    if key != "cowboys":       # bank 1 outside the Saloon: level.c loads nothing there, so tiles loaded but unused are another screen's leftovers: free
        u1 = c["tiles"][1]["use"]
        tiles["b1"] = tuple(sum(1 for i in range(a_, a_ + 128) if u1[i] == "0") for a_ in (0, 128, 256))
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

def _git(*a):
    return subprocess.run(["git", "-C", ROOT] + list(a), capture_output=True, text=True).stdout.strip()


# The page stamp: the game commit the capture was made from (data/index.js) and the last commit that touched the plan (not the page's own output).
commit = load("index")["commit"]
plan_commit = _git("log", "-1", "--format=%h", "--", "tools/artifacts/palette_plan/build.py", "tools/artifacts/palette_plan/game_truth.py",
                   "tools/artifacts/palette_plan/self_check.py", "tools/artifacts/palette_plan/art", "docs/dev/concepts") or "unknown"

from plan_data import *  # noqa: E402,F401,F403  (NAMES, PLANS, EXTRA_LOOKS, NEW_PATRONS, SALOON_*, INST_*, ... : the hand-kept plan)


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
        if v["key"] == "cowboys":
            pat = [n[i] for i, (_, ps) in enumerate(SALOON_LOOKS) if any(INST_OBJ[p] == s for p in ps)]
        if s == 4 and e is not None and not DROP_ENHANCED:
            pat = [n[e] + " (left half, lifted)"]
        other = {0: ["Sal", "Tip coin"], 1: ["Full mug", "Fill glass", "Breaking glass", "Pour sparkle"],
                 2: ["Empty mug", "Breaking glass", "Boss: capacity mugs"], 5: ["Show dancers"], 7: ["Boss fight: " + TOPPER[v["key"]]]}.get(s, [])
        if v["key"] == "punks" and s in (1, 2):          # the Chrome Cow draws its empty mug, glass and capacity mugs in OBJ 1 on CGB (2026-10-31)
            other = ["Full mug", "Fill glass", "Breaking glass", "Pour sparkle", "Empty mug", "Boss: capacity mugs"] if s == 1 else []
    else:
        pat = [n[BG_PATRON[s]]] if s in BG_PATRON else []
        if v["key"] == "cowboys":
            pat = [n[i] for i, (_, ps) in enumerate(SALOON_LOOKS) if any(INST_BG[p] == s for p in ps)]
        if s == 7 and e is not None and not DROP_ENHANCED:
            pat = [n[e] + " (top row)"]
        other = {0: ["Bar, wall"] + ([] if v["keg7"] else ["Keg, spout"]), 1: ["HUD"], 4: ["Boss body"], 5: ["Stage"], 6: ["Stage"],
                 7: ["Keg, spout"] if v["keg7"] else []}.get(s, [])
    return pat, other


def event_swapped(key):
    """OBJ slots whose colours differ between the capture's events (the Saloon's OBJ 5: patron B, then the show dancers)."""
    vals = {}
    for e in load("level_" + key)["cgb"]["ev"]["events"]:
        for sp in e["slots"]:
            vals.setdefault(sp["slot"], set()).add(json.dumps(sp["values"]))
    return {sl for sl, x in vals.items() if len(x) > 1}


def model(v):
    """slot -> dict(pat=[(text, planned)], oth=[...], cols, new={i: hex}, freed) for ("OBJ"|"BG", s); the plan applied."""
    m = {}
    for kind in ("OBJ", "BG"):
        for sl in range(8):
            pat, oth = users(kind, v, sl)
            m[(kind, sl)] = dict(pat=[(x, False) for x in pat], oth=[(x, False) for x in oth],
                                 cols=(v["pal"] if kind == "OBJ" else v["bg"]).get(sl, ["#000000"] * 4), new={}, freed=False, open=None)
    for sl in event_swapped(v["key"]):
        m[("OBJ", sl)]["evswap"] = True
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
    free = not pat and not [x for x in oth if not x[0].startswith("Boss")] and not d["open"] and not d.get("swaps")
    body = ""
    if pat or d["open"]:
        body += '<ul class="pat">%s%s</ul>' % ("".join('<li class="%s">%s</li>' % ("plan" if p else "now", esc(t)) for t, p in pat),
                                              ('<li class="plan open">%s</li>' % esc(d["open"])) if d["open"] else "")
    if d.get("evswap") and not hide_cols:
        body += '<p class="swp">event swap</p>'
    if d.get("swaps") and not hide_cols:
        body += '<p class="swp">%d swap%s</p>' % (d["swaps"], "" if d["swaps"] == 1 else "s")
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


SLOTS = []                      # (venue, plan OBJ slot, patron, colours) for the unique-slot check
DUAL = []                       # (venue, patron, "OBJ"|"BG", plan slot, game slot) where the page shows both numbers
S = []
w = S.append
w('<title>Atlas</title>')
w('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>')
w('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Silkscreen&family=IBM+Plex+Sans:wght@400;600&family=IBM+Plex+Mono:wght@400;600&display=swap">')
w("""<style>
/* Layout: venue tabs, then that venue's sprite palettes (swatches + who uses them), then its background palettes. */
:root {
  --ground: #eef0f2; --card: #fbfcfd; --ink: #1d2126; --muted: #5d6670; --rule: #d3d9df; --accent: #1f6f8b; --free: #985a00; --now: #23824a; --plan: #7f6200; --over: #c0362c;
  --display: "Silkscreen", "IBM Plex Mono", ui-monospace, monospace;
  --body: "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, Menlo, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { color-scheme: dark;
  --ground: #14171b; --card: #1c2026; --ink: #e6eaee; --muted: #9aa4ae; --rule: #313840; --accent: #5fb6d4; --free: #f0a944; --now: #6cd18f; --plan: #f2d24b; --over: #ff7b6e; } }
:root[data-theme="dark"] { color-scheme: dark;
  --ground: #14171b; --card: #1c2026; --ink: #e6eaee; --muted: #9aa4ae; --rule: #313840; --accent: #5fb6d4; --free: #f0a944; --now: #6cd18f; --plan: #f2d24b; --over: #ff7b6e; }
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
li::marker { color: var(--muted); }
.freep { margin: 0; color: var(--free); font-weight: 600; font-size: 13px; }
.freep.plan { color: var(--plan); }

.chgp { margin: 0; color: var(--plan); font-size: 12px; }
li.open { font-style: italic; }
.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 8px; }
.stat { background: var(--card); border: 1px solid var(--rule); border-radius: 10px; padding: 10px 12px; display: grid; gap: 2px; }
.stat b { font-family: var(--display); font-size: 24px; font-variant-numeric: tabular-nums; }
.stat span { color: var(--muted); font-size: 13px; }
.stat.plan b { color: var(--plan); }
.stat.over { border-color: var(--over); }
.swp { margin: 0; color: var(--muted); font-size: 12px; }
.stat.over b, .stat.over span { color: var(--over); }
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
.pt td.pic:has(.pp:nth-child(2)) { width: 340px; min-width: 0; max-width: 100%; box-sizing: border-box; }
.pics { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.pp { display: flex; gap: 2px; flex-wrap: wrap; align-items: center; max-width: 100%; }
.plab { flex-basis: 100%; font-family: var(--mono); font-size: 12px; color: var(--muted); }
.btag { font-size: 12px; font-style: italic; }
.btag.plan { color: var(--plan); }
.swg { display: inline-flex; margin-right: 6px; }
.bimg { image-rendering: pixelated; image-rendering: crisp-edges; display: block; max-width: 100%; height: auto; border-radius: 4px; }
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
html, body { overflow-x: clip; }
.wrap > *, .panel { min-width: 0; }
@media (max-width: 640px) {
  .tbl { overflow-x: visible; }
  table.pt, .pt thead, .pt tbody, .pt tr, .pt td { display: block; width: auto; }
  .pt thead { display: none; }
  .pt tr { padding: 8px 10px; border-bottom: 1px solid var(--rule); }
  .pt tr:last-child { border-bottom: 0; }
  .pt td { border: 0; padding: 2px 0; overflow-wrap: anywhere; }
  .pt td[data-label]:not([data-label=""])::before { content: attr(data-label); display: block; font-size: 11px; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); }
  .pt td.pic { width: auto; min-width: 0; }
  .pt td.slotc { white-space: normal; }
}
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


# The art precedence, in one place (plan_data.ART, then art/<venue>_<name>.txt, then the game): ART picks (files under PASS), the right-column
# trim (docs/dev/concepts/right_column, unless the pick is a later _face pass), the game's own art. GUS's Color plane swap comes after all of them.
PASS = os.path.join(ROOT, "docs/dev/concepts/patron_pass")


def accepted(v, name):
    """(front rows, back rows or None) of the patron's latest accepted art."""
    first = name.split(",")[0].strip().lower()
    names = [n.split(",")[0].strip().lower() for n in NAMES[v["key"]]]
    old = lambda suf: frames(os.path.join(ROOT, "assets/art/patrons/%s%s.txt" % (v["key"], suf)))[names.index(first)]
    if name in EXTRA_LOOKS.get(v["key"], []):
        return art_rows(v, name), frames(os.path.join(ART, "%s_%s_back.txt" % (v["key"], first)))[0]
    pick = PATRON_ART.get(v["key"], {}).get(first)
    if pick:
        get = lambda f, suf: old(suf) if f == "old" else frames(os.path.join(PASS, v["key"], f + ".txt"))[0]
        return get(pick[0], ""), get(pick[1], "_back")
    front = art_rows(v, name)
    back = old("_back") if first in names else None
    return front, back

PICS = []        # every thumbnail written: (img path, rows, colours, wall, source "game" | "plan", venue, patron, side): self_check.verify_pictures reads it back
GAME_ART = []    # (venue, look, game text front, game text back, captured front, captured back): self_check.verify_pictures


def thumb(rows, cols, wall, name, src="plan", who=None, palplan=False):
    """img/<name>_1x.png beside OUT: a 16x16 view, indexed (colour 0 the wall, transparent), shown x3 by CSS and downloaded
    as is (one file per picture: the artifact holds at most 512 files). Returns its relative path."""
    from PIL import Image
    rel = "img/%s_1x.png" % name
    path = os.path.join(os.path.dirname(OUT), "img/%s.png" % name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    one = Image.new("P", (16, 16), 0)                 # the 1x download: indexed, colour 0 the wall, 1-3 light to dark
    one.putpalette(sum((list(hex2(c)) for c in [wall] + list(cols)), []))
    for y, r in enumerate(rows[:16]):
        for x, ch in enumerate(r[:16]):
            if ch in "-+#":
                one.putpixel((x, y), "-+#".index(ch) + 1)
    one.save(path[:-4] + "_1x.png", "PNG", transparency=0)
    PICS.append(dict(rel=rel, rows=list(rows), cols=list(cols), wall=wall, src=src, who=who, palplan=palplan))
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

    for name, to in PLANS.get(v["key"], {}).get("bg", {}).items():          # held for that patron while the others are renumbered
        if empty(field[to]):
            field[to] = dict(field[to], open="(held)")
    pats = [(t, sl) for sl in range(8) for t, _ in m[("OBJ", sl)]["pat"]] + [(m[("OBJ", sl)]["open"], sl) for sl in range(8) if m[("OBJ", sl)]["open"]]
    if v["key"] == "cowboys":
        pats = []                                   # the game's own BG slots (users(), SALOON_LOOKS): nothing to renumber
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
    for name, to in PLANS.get(v["key"], {}).get("bg", {}).items():          # a patron's BG away from its OBJ number
        o = next(sl for sl in range(8) if any(x[0] == name for x in m[("OBJ", sl)]["pat"]))
        oc = eff(m[("OBJ", o)])
        if field[to].get("open") == "(held)":
            field[to]["open"] = None
        if field[to]["pat"]:
            field[to]["pat"] = field[to]["pat"] + [(name, True)]
        else:
            put(to, (name, True), [eff(field[0])[0]] + oc[1:], "OBJ %d" % o)
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
    return sheet, live, mark, part, T


def rgb15(c):
    """The colour the game screenshots show for a 15-bit word (PyBoy: each 5-bit channel << 3)."""
    return ((c & 31) << 3, ((c >> 5) & 31) << 3, ((c >> 10) & 31) << 3)


GREY = [(255, 255, 255), (170, 170, 170), (85, 85, 85), (0, 0, 0)]
_TD = {}


def tile_data(v, model):
    """{bank: (sheet, live, mark, part, T)} of a venue's captured VRAM, cached."""
    k = (v["key"], model)
    if k not in _TD:
        lv = load("level_" + v["key"])
        _TD[k] = {b: tile_sheets(v, model, b) for b in range(len(lv[model]["tiles"]))}
    return _TD[k]


def bg_pals(v):
    """[8 palettes of 4 RGB] of the Color capture's BG palette RAM (the representative frame the screen map comes from)."""
    lv = load("level_" + v["key"])["cgb"]
    return [[rgb15(c) for c in p["rep"]] for p in lv["pal"]["bg"]]


def pal_map(v):
    """{(bank, slot): sorted BG palettes it was drawn with anywhere in the Color capture}."""
    ev = load("level_" + v["key"])["cgb"].get("ev") or {}
    out = {}
    for p, lst in (ev.get("bg_by_pal") or {}).items():
        for b, t in lst:
            out.setdefault((b, t), set()).add(int(p))
    return out


def render_tile(v, model, bank, slot, xf=0, yf=0, pal=None):
    """One 8x8 RGB tile. pal: None (grey), (4 RGB colours, is_obj); an OBJ palette's colour 0 shows the venue's wall."""
    from PIL import Image
    sheet, live, mark, part, T = tile_data(v, model)[bank]
    if model == "dmg" or pal is None:
        if model == "dmg":
            im = sheet.crop(((slot % 16) * 8, (slot // 16) * 8, (slot % 16) * 8 + 8, (slot // 16) * 8 + 8))
        else:
            im = Image.new("RGB", (8, 8))
            im.putdata([GREY[i] for row in T[slot] for i in row])
    else:
        cols, obj = pal
        if obj:
            cols = [bg_pals(v)[0][0]] + list(cols[1:])
        im = Image.new("RGB", (8, 8))
        im.putdata([cols[i] for row in T[slot] for i in row])
    return _flip(im, xf, yf)


def screen_composite(v, model):
    """The 160x144 background layer as the capture's attribute map and VRAM draw it (bank, palette, flips honoured; no sprites)."""
    from PIL import Image
    lv = load("level_" + v["key"])[model]
    A = lv["attr"]
    pals = bg_pals(v) if model == "cgb" else None
    im = Image.new("RGB", (160, 144))
    for r in range(18):
        for c in range(20):
            sl = A["slot"][r][c]
            if sl < 0:
                continue
            if model == "cgb":
                f = int(A["flags"][r][c], 16)
                t = render_tile(v, model, (f >> 2) & 1, sl, f & 1, (f >> 1) & 1, (pals[int(A["pal"][r][c])], False))
            else:
                t = render_tile(v, model, 0, sl)
            im.paste(t, (c * 8, r * 8))
    return im


GLYPH_DIGITS = list(range(36, 46))            # BG ids, build/art.h TILE_GLYPH_*: 0-9
GLYPH_LETTERS = [56, 65, 47, 66, 50, 71, 60, 59, 52, 72, 67, 51, 61, 68, 48, 57, 73, 49, 46, 58, 62, 53, 69, 74, 70, 75]   # A-Z in order
OBJ_LABEL = {"Mug: full": "Mug", "Mug: empty": "Mug", "Mug: drinking": "Drink in hand", "Perfect-pour sparkle": "Pour sparkle",
             "PERFECT cue": "Pour sparkle", "DMG mug copy": "DMG mug copies"}


def obj_figures(v, model):
    """Every non-patron object of the venue, assembled from its OAM pieces as drawn (x, y, tile, bank, xflip, yflip ...), grouped by
    kind. A pose whose tiles are all in a shown pose already (the mirrored copy of it) is left out. -> {label: [figure]}"""
    lv = load("level_" + v["key"])[model]
    groups, shown = {}, {}
    opal = [[rgb15(c) for c in p["rep"]] for p in lv["pal"]["obj"]] if model == "cgb" else None
    evs = {e["label"].lower(): e for e in ((load("level_" + v["key"])["cgb"].get("ev") or {}).get("events") or [])} if model == "cgb" else {}
    for o in lv["objs"]:
        if o["kind"].startswith("Patron"):
            continue
        lab = OBJ_LABEL.get(o["kind"], o["kind"])
        fig, slots = [], set()
        cols = None
        if opal:                                   # the object's own OBJ palette (a captured event's values where it has them: the show's dancers)
            cols = list(opal[o["slots"][0]])
            ev = evs.get(o["kind"].lower())
            for sv in (ev["slots"] if ev else []):
                if sv["slot"] == o["slots"][0] and len(sv["values"]) == 1:
                    cols = [rgb15(c) for c in sv["values"][0]]
        pl_ = (cols, True) if cols else None
        for x, y, t, bank, xf, yf in [pc[:6] for pc in o["pieces"]]:
            if bank:
                continue
            top, bot = (t + 1, t) if yf else (t, t + 1)
            fig += [(top, x // 8, y // 8, xf, yf, 0, pl_), (bot, x // 8, y // 8 + 1, xf, yf, 0, pl_)]
            slots |= {t, t + 1}
        if not fig or slots <= shown.setdefault(lab, set()):
            continue
        shown[lab] |= slots
        groups.setdefault(lab, []).append(fig)
    return groups


def tile_groups(v, model, live, b=0):
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
            placed.update(e[0] for e in (f or []) if len(e) < 6 or e[5] == b)
        out.append(((label + " " + rng(figs)) if ids else label, figs, pad, marks))

    pair = lambda t: [(t, 0, 0, 0, 0), (t + 1, 0, 1, 0, 0)]
    if b == 0:
        og = obj_figures(v, model)
        for lab, figs in sorted(og.items(), key=lambda kv: min(t for f in kv[1] for t, *_ in f)):
            add(lab, figs)
        add("Dust puff", [pair(t) for t in (246, 248, 250)])
        add("Boss HUD", [[(t, 0, 0, 0, 0)] for t in range(252, 256)], 2)
    # patrons: per look, the 8 shifted 24x16 poses (3 wide, 2 tall, column-major) in two lines, then the 16x16 back view (2x2, ROW-major:
    # render.c put_back_col: column c is tiles t, t + 2 and column c + 1 is t + 1, t + 3). Bank 0 holds looks A-C; the Saloon's Color-only
    # looks D-H are in bank 1 (art.h SALOON_X_S0 / SALOON_X_BACK / SALOON_X_LAST).
    last_pref = []

    def look(label, pref, shifted, s0, back):
        figs = []
        votes = {}                                  # the look's palette: the one most of its tiles were drawn with in the capture
        for t in [shifted(sh) + k for sh in range(1, 8) for k in range(6)] + [s0 + k for k in range(4)] + [back + k for k in range(4)]:
            for p_ in pal_map(v).get((b, bgslot(t)), ()):
                votes[p_] = votes.get(p_, 0) + 1
        if votes:
            pref = max(votes, key=lambda p_: (votes[p_], -p_))
        elif pref is None and last_pref:                # not drawn in the capture (ARTIE, look H): he shares MABEL's (look G's) palette in the game
            pref = last_pref[-1]
        last_pref.append(pref)
        for sh in range(8):
            if sh == 0:
                ids = [s0 + k for k in range(4)] + [PAT_FIRST + PAT_S0 - 2 + k for k in range(2)]
            else:
                ids = [shifted(sh) + k for k in range(6)]
            figs.append([(bgslot(t), k // 2, k % 2, 0, 0, b, ("bgpref", pref)) for k, t in enumerate(ids)])
            if sh == 3:
                figs.append(None)
        figs.append([(bgslot(back + k), k % 2, k // 2, 0, 0, b, ("bgpref", pref)) for k in range(4)])
        add(label, figs)
    if b == 0:
        for vi, nm in enumerate("ABC"):
            look("Patron " + nm, 2 + vi, lambda sh, vi=vi: PAT_FIRST + vi * 42 + (sh - 1) * 6, PAT_FIRST + PAT_S0 + vi * 4,
                 PAT_FIRST + PAT_BACK + vi * 4)
    elif v["key"] == "cowboys":
        for k, nm in enumerate("DEFGH"):
            look("Patron " + nm, None, lambda sh, k=k: ((7 * k + sh - 1) * 6) if 7 * k + sh - 1 < 34 else 246, 206 + 4 * k, 226 + 4 * k)
    # the screen as drawn (a representative frame's BG map: bank, palette and flips as the attribute map has them), then the pool tiles
    if b == 0:
        A = lv["attr"]
        pals = bg_pals(v) if model == "cgb" else None
        fig = []
        for r, row in enumerate(A["slot"]):
            for c, sl in enumerate(row):
                if sl < 0:
                    continue
                if model == "cgb":
                    f = int(A["flags"][r][c], 16)
                    fig.append((sl, c, r, f & 1, (f >> 1) & 1, (f >> 2) & 1, (pals[int(A["pal"][r][c])], False)))
                else:
                    fig.append((sl, c, r, 0, 0))
        add("Screen", [fig], 0, ids=False, marks=False)
    if b == 0:
        add("Pool, not on screen", [[(256 + t, 0, 0, 0, 0)] for t in range(36) if live[256 + t] and 256 + t not in placed], 2)
        add("Digits", [[(256 + t, 0, 0, 0, 0)] for t in GLYPH_DIGITS], 2)
        add("Letters", [[(256 + t, 0, 0, 0, 0)] for t in GLYPH_LETTERS[:13]] + [None] + [[(256 + t, 0, 0, 0, 0)] for t in GLYPH_LETTERS[13:]], 2)
        add("HUD, panels", [[(256 + t, 0, 0, 0, 0)] for t in (54, 55)] + [[(256 + 63, 0, 0, 0, 0), (256 + 64, 0, 1, 0, 0)], [(256 + 76, 0, 0, 0, 0)]], 2)
    # whatever is loaded and still not placed
    rest = [pair(t) for t in list(range(0, 128, 2)) + list(range(234, 256, 2)) if (live[t] or live[t + 1]) and t not in placed and t + 1 not in placed]
    if b == 0:
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
        sheet, live, mark, part, _T = tile_sheets(v, model, b)
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
        if b == 0 or any(c != "0" for c in lv[model]["tiles"][b]["use"]):      # bank 1: only where the game draws from it (elsewhere it holds junk)
            W = 160 * S
            fnt = ImageFont.load_default(size=12)
            groups = tile_groups(v, model, live, b)
            pm = pal_map(v) if model == "cgb" else {}
            pals = bg_pals(v) if model == "cgb" else None

            def tile(e):
                t, _c, _r, xf, yf = e[:5]
                bank = e[5] if len(e) > 5 else b
                pal = e[6] if len(e) > 6 else None
                if model == "cgb":
                    if isinstance(pal, tuple) and pal and pal[0] == "bgpref":       # a patron look: its own BG palette where it was drawn with it
                        ps = pm.get((bank, t), set())
                        n = pal[1] if pal[1] is not None else (min(ps) if ps else None)
                        pal = (pals[n], False) if n is not None else None
                    elif pal is None and (bank, t) in pm:
                        pal = (pals[min(pm[(bank, t)])], False)
                return render_tile(v, model, bank, t, xf, yf, pal).resize((8 * S, 8 * S), Image.NEAREST)
            rows = []
            for glabel, figs, pad, gmarks in groups:
                x = y = rh = 0
                placed = []
                for f in figs:
                    if f is None:
                        x, y, rh = 0, y + rh + max(pad, 2) * S, 0
                        continue
                    fw = (max(e[1] for e in f) + 1) * 8 * S
                    fh = (max(e[2] for e in f) + 1) * 8 * S
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
                    for e in f:
                        t, c, r = e[:3]
                        own = len(e) < 6 or e[5] == b                 # a Screen cell from the other VRAM bank has no entry in this sheet
                        px, py = fx + c * 8 * S, y0 + fy + r * 8 * S
                        im.paste(tile(e), (px, py))
                        if own:
                            rects.append([px, py, t, part.get(t, -1)])
                        if own and not live[t]:
                            dr.rectangle((px, py, px + 8 * S - 1, py + 8 * S - 1), fill=(60, 60, 60))
                        if own and gmarks and t in mark:
                            dr.rectangle((px, py, px + 8 * S - 1, py + 8 * S - 1), outline=mark[t], width=2)
                y0 += h + 8
            srel = "img/tiles_%s_%s%s_sorted.png" % (v["key"], model, "" if b == 0 else b)
            TILEMAP[srel] = {"b": b, "r": rects}
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
X15 = 2                             # owner 2026-10-29: column x=15 clear on every patron: the shift-1 pose fits 2 tile columns too (its 3rd = the shared blank)
SALOON_NOW = 8                      # the Saloon's looks in the game (src/mirror.c sal_combo)
LOOKS_NOW = 3                       # looks every venue has in the game today (the enhanced ROSIE / BOXY are palettes, not looks)
BACK_B0 = 4                         # the one back view at bank-0 ids 242-245 once there are looks in bank 1
FIGHT_LOOKS = 2                     # looks A and B stay loaded in a boss fight; the boss borrows look C's tiles (boss.h BOSS_BG_A / BOSS_BG_B)


def planned_tiles(v, n):
    """Planned tile counts of venue v with n looks in the plan, split by VRAM region (sprite-only 0-127; BG-reachable 128-383 = shared + BG-only).
    Patron looks are BG tiles, so only BG-reachable ids can take them."""
    t = v["tiles"]; sal = v["key"] == "cowboys"
    q = "" if sal else " ?"                                   # the Saloon's numbers are decided in QUEUE; elsewhere the same rule is assumed
    lnow = SALOON_NOW if sal else LOOKS_NOW                   # looks in the game today (the Saloon has all 8 since batch 2)
    n = max(n, lnow); extra = n - lnow
    save = LOOKS_NOW * (LOOK_NOW - LOOK_OPT2)                 # option 2 on looks A-C
    fsave = FIGHT_LOOKS * (LOOK_NOW - LOOK_OPT2)
    b0 = BACK_B0 if extra else 0
    b1 = extra * (LOOK_OPT2 - X15)
    xs0 = LOOKS_NOW * X15                                   # the cleared right column on looks A-C (bank 0, DMG)
    xs1 = (SALOON_NOW - LOOKS_NOW) * X15 if sal else 0      # and on the Saloon's 5 bank-1 looks
    enh = 2 if v["key"] == "robots" else 0         # the dropped enhanced look's 2 bank-1 lift tiles (ids 210, 211: enhance.c enh_b1)
    sp = lambda r: r[0]
    bg = lambda r: r[1] + r[2]
    o = dict(sp=sp(t["b0"]), bg=bg(t["b0"]) + save + xs0 - b0, sp1=sp(t["b1"]), bg1=bg(t["b1"]) - b1 + enh + xs1,
             fbg=bg(t["bb"]) + fsave + FIGHT_LOOKS * X15 - b0, dbg=bg(t["d"]) + save + xs0)
    o["used"] = 384 - o["sp"] - o["bg"]
    o["dused"] = 384 - t["d"][0] - o["dbg"]
    nowtxt = "NOW: bank 0 free %d sprite-only + %d BG (used %d); bank 1 free %d sprite-only + %d BG; boss fight free BG %d; DMG free BG %d (used %d)." % (
        sp(t["b0"]), bg(t["b0"]), 384 - sum(t["b0"]), sp(t["b1"]), bg(t["b1"]), bg(t["bb"]), bg(t["d"]), 384 - sum(t["d"]))
    L = [nowtxt,
         "Free means empty (not loaded, not referenced in the capture) and reachable: sprite-only ids 0-127, BG ids 128-383 (shared 128-255 + BG-only 256-383). Looks are BG tiles, so only BG counts for them.",
         "Looks in the plan: %d (now %d)%s." % (n, lnow, "" if n != lnow else "; no more are planned here ?"),
         "-%d per look, option 2, x %d looks (A-C): +%d free BG in bank 0 and on DMG%s." % (LOOK_NOW - LOOK_OPT2, LOOKS_NOW, save, "" if sal else " ?")]
    L.append("-%d per look, right column x=15 clear (the shift-1 pose's 3rd tile column is the shared blank too): +%d free BG in bank 0 and on DMG, +%d in a boss fight%s ?"
             % (X15, xs0, FIGHT_LOOKS * X15, (", +%d in bank 1" % xs1) if xs1 else ""))
    if extra:
        L.append("+%d looks x %d in bank 1 (BG ids): bank 1 free BG -%d%s." % (extra, LOOK_OPT2 - X15, b1, q))
        L.append("One back view in bank 0 (ids 242-245): bank 0 free BG -%d, boss fight -%d%s." % (b0, b0, q))
        L.append("Back views of the other new looks share that one ?")
        L.append("New looks are Color only: DMG unchanged.")
    L.append("Boss fight: the capture, +%d for option 2 on the two looks that stay loaded (A, B; the boss borrows C's tiles), -%d back view%s." % (fsave, b0, q))
    if v["key"] == "robots":
        L.append("Enhanced look dropped (BOXY): its 2 bank-1 lift tiles (ids 210, 211, loaded by enhance_load) are freed: bank 1 free BG +%d%s." % (enh, q))
    L.append("Dancers moved to other palettes and palette variants: 0 tiles.")
    o["lines"] = L
    return o


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import game_truth  # noqa: E402
import self_check  # noqa: E402

def game_front(v, i):
    """Look i's front as in the game (cowboys.txt 0-2, saloon_x.txt 0-4 for the Saloon)."""
    if v["key"] == "cowboys":
        return frames(os.path.join(ROOT, "assets/art/patrons/%s.txt" % ("cowboys" if i < 3 else "saloon_x")))[i if i < 3 else i - 3]
    return accepted(v, NAMES[v["key"]][i])[0]


# Planned fronts with column x=15 cleared (owner Q16/Q17 2026-10-29), not imported yet: docs/dev/concepts/right_column/
TRIM = os.path.join(ROOT, "docs/dev/concepts/right_column")


def trimmed_front(v, i, cur):
    """Look i's planned x=15-cleared front, or None when there is none or it equals the current front."""
    g, k = ("saloon_x", i - 3) if v["key"] == "cowboys" and i >= 3 else (v["key"], i)
    pick = PATRON_ART.get(v["key"], {}).get(NAMES[v["key"]][i].split(",")[0].strip().lower())
    if pick and pick[0].endswith("_face"):          # a later face pass (x=15 already clear) supersedes the trimmed front (owner Q57 2026-10-29)
        return None
    if cur and all(r[15] == "." for r in cur):      # the game's front already keeps x=15 clear (e.g. the owner's RONIN 2026-10-30): a trim is stale
        return None
    f = os.path.join(TRIM, g + ".txt")
    if not os.path.exists(f):
        return None
    rows = frames(f)[k]
    return rows if rows != cur else None


def back_info(v, i):
    """(rows, tag) of look i's back view: the game's current back (tag "stand-in" if it is one), or the owner-picked back
    not yet imported (tag "planned"), which replaces it."""
    label, rows, standin = game_truth.backs(v["key"])[i]
    pick = PATRON_ART.get(v["key"], {}).get(NAMES[v["key"]][i].split(",")[0].strip().lower())
    if pick and pick[1] != "old":
        prows = frames(os.path.join(PASS, v["key"], pick[1] + ".txt"))[0]
        if prows[:15] != rows[:15]:            # row 15 only: the pick is in the game, with the 10-29 bottom outline dropped
            return prows, "planned"
    return rows, ("stand-in" if standin else "")


def captured_look(v, i):
    """(front rows, back rows) of look i as the game's VRAM holds them in the atlas capture (Color model): 16 strings of 16 chars in the house
    alphabet . - + #, or None for a view whose tiles were not loaded. Looks A-C are bank 0; the Saloon's D-H are bank 1 (art.h SALOON_X_S0 / SALOON_X_BACK).
    The front is the shift-0 pose (4 tiles, column-major); the back is 4 tiles, row-major (render.c put_back_col)."""
    if v["key"] == "cowboys" and i >= 3:
        b, s0, back = 1, 206 + 4 * (i - 3), 226 + 4 * (i - 3)
    else:
        b, s0, back = 0, PAT_FIRST + PAT_S0 + i * 4, PAT_FIRST + PAT_BACK + i * 4
    _, live, _, _, T = tile_data(v, "cgb")[b]
    out = []
    for base, pos in ((s0, lambda k: (k // 2, k % 2)), (back, lambda k: (k % 2, k // 2))):
        sl = [bgslot(base + k) for k in range(4)]
        if not all(live[s] for s in sl):
            out.append(None)
            continue
        g = [[0] * 16 for _ in range(16)]
        for k, s in enumerate(sl):
            c, r = pos(k)
            for y in range(8):
                for x in range(8):
                    g[r * 8 + y][c * 8 + x] = T[s][y][x]
        out.append(["".join(".-+#"[p] for p in row) for row in g])
    return tuple(out)


def back_rows_by_look(v):
    n = len(game_truth.truth()["saloon"]) if v["key"] == "cowboys" else 3
    return [back_info(v, i)[0] for i in range(n)]


SHOWN = set()                      # (venue, look, palette instance) of every thumbnail pair written below

self_check.verify_plan(sys.modules["plan_data"], ROOT)
self_check.verify_now(globals())

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
            if t not in SWAP_PALETTES.get(v["key"], ()):     # a swap palette holds a slot but is no look of its own
                ident.append(dict(name=t, obj=sl, planned=planned))
        if d["open"]:
            reserved.append(dict(name=d["open"], obj=sl, planned=True))
    for r in ident + reserved:
        b = next((sl for sl in range(8) if any(x[0] == r["name"] for x in field[sl]["pat"])), None)
        if b is not None:
            r["bg"] = b
            if field[b]["new"] or b != r["obj"]:
                r["planned"] = r["planned"] or bool(field[b]["new"])
    rows, swaps = [], []
    md = "### %s: patron palettes (plan, %s)\n\n| Patron | Palette colours (1, 2, 3) | OBJ | BG | DMG |\n|---|---|---|---|---|\n" % (v["name"], LOG[0][0])
    sal = v["key"] == "cowboys"
    GT = game_truth.truth()
    if sal:                         # the game's looks, one row each: palette instances from src/mirror.c, not the OBJ slots of the plan
        ident = [dict(name=NAMES["cowboys"][i], look=i, planned=False) for i in range(len(SALOON_LOOKS))]
        reserved = []
    ident += [dict(name=x["name"], planned=True, obj=None, cols=x["cols"]) for x in PLANS.get(v["key"], {}).get("extras", [])]
    for r in ident + reserved:
        d = m[("OBJ", r["obj"])] if not sal and r["obj"] is not None else None
        if sal:
            ps = game_truth.ordered_instances(r["look"], SALOON_LOOKS[r["look"]][1])
            prim = SALOON_PRIMARY[r["name"].split(",")[0].strip()]
            ps = [prim] + [p_ for p_ in ps if p_ != prim]                                # the look's own palette first
            groups = [[hexc(c) for c in GT["inst"]["cowboys"][p]] for p in ps]
            cols = groups[0]
            sw = "".join('<button type="button" class="sw" style="background:%s" data-hex="%s" title="%s"></button>' % (c, c, c) for c in cols)
            bg = str(INST_BG[ps[0]])
            obj_txt = str(INST_OBJ[ps[0]])
            vtxt = ", ".join(str(x) for x in sorted({INST_OBJ[p] for p in ps}))
            dtxt = "DMG" if r["look"] < 3 else ""
        elif d is None:                                   # a planned extra look with no OBJ slot yet
            cols = r["cols"]
            sw = "".join('<button type="button" class="sw" style="background:%s" data-hex="%s" title="%s"></button>' % (c, c, c) for c in cols)
            bg = '<span class="muted">to assign</span>'
            obj_txt = vtxt = '<span class="muted">to assign</span>'
            dtxt = ""
        else:
            cols = [d["new"].get(k, d["cols"][k]) for k in (1, 2, 3)]
            sw = "".join('<button type="button" class="sw" style="background:%s" data-hex="%s" title="%s"></button>' % (c, c, c) for c in cols)
            bg = ("BG %d" % r["bg"]) if "bg" in r else '<span class="muted">to assign</span>'
            obj_txt = str(r["obj"])
            var = PLANS.get(v["key"], {}).get("variants", {}).get(r["name"].split(",")[0].strip())
            vtxt = ", ".join(str(x) for x in var) if var else str(r["obj"])
            dm = PLANS.get(v["key"], {}).get("dmg")
            dtxt = ("DMG" if r["name"].split(",")[0].strip() in dm else "") if dm else "DMG"
        first = r["name"].split(",")[0].strip().lower()
        idx = r["look"] if sal else next((k_ for k_, n_ in enumerate(NAMES[v["key"]]) if n_.split(",")[0].strip().lower() == first), None)
        ftag = ""
        cap_f = cap_b = None
        fsrc = bsrc = "plan"
        if idx is None:                                   # a reserved patron: not in the game yet, its art is the plan's
            fr, bk = accepted(v, r["name"])
            btag = "planned" if bk else ""
        else:
            # A look the game ships is drawn from the capture's VRAM tiles (what the ROM really holds, GUS's plane swap included). The plan's art
            # (an accepted pick, a right-column trim) replaces it only where it differs, and then says so. The Color game swaps GUS's colours 1 and
            # 2 at load (src/level.c swap_gus), so any planned GUS art is swapped the same way, whichever file it came from.
            cap_f, cap_b = captured_look(v, idx)
            pf = game_front(v, idx) if sal else accepted(v, r["name"])[0]
            pb, btag = back_info(v, idx)
            tr = trimmed_front(v, idx, pf)
            if tr:
                pf = tr
            if (sal or v["key"] == "lumberjacks") and idx == 2:
                swap12 = lambda g: [x.translate(str.maketrans("-+", "+-")) for x in g] if g else g
                pf, pb = swap12(pf), swap12(pb)
            GAME_ART.append((v["key"], idx, game_front(v, idx) if sal else frames(os.path.join(ROOT, "assets/art/patrons/%s.txt" % v["key"]))[idx],
                             game_truth.backs(v["key"])[idx][1], cap_f, cap_b))
            fr, fsrc = (cap_f, "game") if cap_f and pf == cap_f else (pf, "plan")
            if fsrc == "plan" and cap_f:
                ftag = "planned front"
            bk, bsrc = (cap_b, "game") if cap_b and (pb == cap_b or btag != "planned") else (pb, "plan")
            if btag == "planned" and bsrc == "game":
                btag = ""                                  # the pick is already in the game
        palplan = (not sal) and d is not None and idx is not None and (r["obj"] != GT["obj_of"][idx] or bool(d["new"]))   # the plan recolours or moves it: its colours are not the capture's
        combos = [(cols, "")]                              # (colours, file suffix) per palette the game spawns the look in; the own palette first
        if sal:
            combos = [([hexc(c) for c in GT["inst"]["cowboys"][p]], "" if n_ == 0 else "_o%d" % INST_OBJ[p]) for n_, p in enumerate(ps)]
        img = ""
        if len(combos) > 1:
            swaps.append((r["name"], first, fr, bk, combos[1:], ps[1:] if sal else [None] * (len(combos) - 1), fsrc, bsrc, idx))
        for n_, (ccols, suf) in enumerate(combos[:1]):
            pair = ""
            for rows_, side in ((fr, "front"), (bk, "back")):
                if rows_:
                    rel = thumb(rows_, ccols, v["bg"][0][0], "%s_%s%s_%s" % (v["key"], first, suf, side), fsrc if side == "front" else bsrc, (v["key"], r["name"], idx, side, ps[n_] if sal else idx), palplan)
                    pair += ('<a class="dl" href="%s" download="%s_%s.png" data-file="%s_%s.png" title="Download %s %s (16x16)">'
                             '<img class="pimg" alt="%s %s" width="48" height="48" style="background:%s" src="%s"></a>'
                             % (rel, first + suf, side, first + suf, side, esc(first.upper()), side, esc(r["name"]), side, v["bg"][0][0], rel))
                else:
                    pair += '<span class="pimg none">-</span>'
            if sal:
                SHOWN.add((v["key"], r["look"], ps[n_]))
                pair += '<span class="plab">OBJ %d</span>' % INST_OBJ[ps[n_]]
            img += '<div class="pp">%s</div>' % pair
        if ftag:
            img += '<span class="btag plan">%s</span>' % ftag
        if btag:
            img += '<span class="btag %s">%s</span>' % ("plan" if btag == "planned" else "muted", btag)
        img = '<div class="pics">%s</div>' % img
        if not sal and idx is not None:
            SHOWN.add((v["key"], idx, idx))
        if r["name"] in EXTRA_LOOKS.get(v["key"], []):
            dtxt = "Color only"
        if not sal and r["obj"] is not None:
            SLOTS.append((v["key"], r["obj"], r["name"], tuple(c.upper() for c in cols)))
        obj_cell = obj_txt if obj_txt.startswith("<") else "OBJ " + obj_txt
        if not sal and idx is not None and idx < len(GT["obj_of"]) and d is not None:      # the plan moves it: both numbers, plan first
            gobj, gbg = GT["obj_of"][idx], GT["bg_of"][idx]
            if r["obj"] != gobj:
                obj_cell = "plan OBJ %s / game OBJ %d" % (obj_txt, gobj)
                DUAL.append((v["key"], r["name"], "OBJ", r["obj"], gobj))
            if "bg" in r and r["bg"] != gbg:
                bg = "plan BG %s / game BG %d" % (r["bg"], gbg)
                DUAL.append((v["key"], r["name"], "BG", r["bg"], gbg))
        rows.append(dict(html=(img, "plan" if r["planned"] else "now", esc(r["name"]), sw, obj_cell, bg, vtxt, dtxt)))
        md += "| %s%s | %s | OBJ %s | %s | %s |\n" % (r["name"], " (planned)" if r["planned"] else "", " ".join("`%s`" % c for c in cols), re.sub("<[^>]+>", "", obj_txt),
                                                (str(bg) if str(bg).startswith(("BG", "plan")) else "BG %s" % bg) if (sal or "bg" in r) else "to assign", dtxt or "Color only")
    nx = len(EXTRA_LOOKS.get(v["key"], []))
    w('<div class="stat"><b>%d</b><span>identified patrons</span></div>' % (len(ident) - nx))
    if nx:
        w('<div class="stat plan"><b>%d</b><span>planned extra looks, Color only</span></div>' % nx)
    w('<div class="stat"><b>%d</b><span>reserved patrons</span></div>' % len(reserved))
    # Owner 2026-10-29: a tile turns red when the plan does not fit the limit. Patrons still "to assign" take a free palette each.
    need_o = 0 if sal else sum(1 for r in ident + reserved if r.get("obj") is None)
    need_b = 0 if sal else sum(1 for r in ident + reserved if "bg" not in r)
    def stat(n, label, over=False):
        w('<div class="stat%s"><b>%d</b><span>%s</span></div>' % (" over" if over else "", n, label))
    stat(len(ofree) - need_o, "free OBJ palettes", len(ofree) < need_o)
    stat(len(bfree) - need_b, "free BG palettes", len(bfree) < need_b)
    tl = planned_tiles(v, len(ident) + len(reserved))
    for k, label in (("bg", "free BG"), ("sp", "free sprite-only"), ("bg1", "free bank 1 BG"), ("sp1", "free bank 1 sprite-only"), ("fbg", "boss fight free BG")):
        stat(tl[k], label, tl[k] < 0)
    stat(tl["dbg"], "free BG DMG", tl["dbg"] < 0)
    w('</div><details class="tdet"><summary>Tile breakdown, planned</summary><ul>%s</ul></details>' % "".join("<li>%s</li>" % esc(x) for x in tl["lines"]))
    w('<h2>Sprite palettes</h2><div class="grid">')
    if sal:                                        # the cards list each look on its own palette only; swaps are counted
        prim = {nm.split(",")[0]: (INST_OBJ[SALOON_PRIMARY[nm.split(",")[0]]], INST_BG[SALOON_PRIMARY[nm.split(",")[0]]]) for nm in NAMES["cowboys"]}
        for kind, src in (("OBJ", lambda sl: m[("OBJ", sl)]), ("BG", lambda sl: field[sl])):
            for sl in range(8):
                d = src(sl)
                keep = [x for x in d["pat"] if prim.get(x[0].split(",")[0], (sl, sl))[0 if kind == "OBJ" else 1] == sl]
                d["swaps"] = len(d["pat"]) - len(keep)
                d["pat"] = keep
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
    w('<div class="tbl"><table class="pt"><thead><tr><th></th><th>Patron</th><th>Palette colours</th><th>OBJ</th><th>BG</th><th>Also on</th></tr></thead><tbody>')
    for r in rows:
        h = r["html"]
        w('<tr><td class="pic">%s</td><td class="%s">%s</td><td>%s</td><td class="slotc">%s</td><td class="slotc">%s</td><td class="slotc">%s</td></tr>' % (h[:6] + h[7:]))
    w('</tbody></table></div>')
    if swaps:                                      # owner 2026-10-29: approved palette swaps in their own section, below the primaries
        w('<h2>Palette swaps</h2><div class="tbl"><table class="pt"><thead><tr><th>Patron</th><th>Swaps</th></tr></thead><tbody>')
        for name, first_, fr_, bk_, cmb, pis, fsrc_, bsrc_, idx_ in swaps:
            cells = ""
            for (ccols, suf), pi in zip(cmb, pis):
                pair = ""
                for rows_, side in ((fr_, "front"), (bk_, "back")):
                    if rows_:
                        rel = thumb(rows_, ccols, v["bg"][0][0], "%s_%s%s_%s" % (v["key"], first_, suf, side), fsrc_ if side == "front" else bsrc_, (v["key"], name, idx_, side, pi))
                        pair += '<img class="pimg" alt="%s %s" width="48" height="48" style="background:%s" src="%s">' % (esc(name), side, v["bg"][0][0], rel)
                if pi is not None:
                    SHOWN.add((v["key"], NAMES["cowboys"].index(name), pi))
                    pair += '<span class="plab">OBJ %d / BG %d</span>' % (INST_OBJ[pi], INST_BG[pi])
                cells += '<div class="pp">%s</div>' % pair
            w('<tr><td class="now">%s</td><td class="pic"><div class="pics">%s</div></td></tr>' % (esc(name), cells))
        w('</tbody></table></div>')
    w(boss_section(v, m, field))
    w(scene_sections(v, m, field))
    w(tile_grid(v))
    w('</section>')
self_check.verify_shown(globals())
self_check.verify_slots(globals())
self_check.verify_primary(globals())
self_check.verify_pictures(globals())
w('<p class="foot">This is the plan. <span style="color:var(--now)">Green</span>: patrons as in the game today. <span style="color:var(--plan)">Yellow</span>: planned changes. Click a colour to copy it. '
  'Game %s, plan %s, %s.</p>' % (esc(commit), esc(plan_commit), LOG[-1][0]))
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
  document.querySelectorAll("table.pt").forEach(function (t) {
    var hs = Array.prototype.map.call(t.querySelectorAll("thead th"), function (h) { return h.textContent.trim(); });
    t.querySelectorAll("tbody tr").forEach(function (r) { Array.prototype.forEach.call(r.children, function (c, i) { if (hs[i]) c.setAttribute("data-label", hs[i]); }); });
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
