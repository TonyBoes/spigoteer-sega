# Story map audit against the owner's decisions (2026-11-08, read-only)

Main audited: `main` at 90abfc1f (the map is the frozen snapshot from stage 2, 52b1d9cf: `assets/smap/world_c.png`, `world_d.png`, `world.json`).
Main rendered with `world.json` palettes: `/workspace/out/audit/main_color_x2.png`, `/workspace/out/audit/main_dmg_x2.png` (x1: `main_color.png`, `main_dmg.png`; cell palettes: `main_cellpal.txt`).
QUEUE line numbers are for `docs/dev/notes/QUEUE.md` on main (807/808 lines). Rows follow each thread to its last decision.

Status key: IN = in main as approved; MISSING = approved, not in main; PARTIAL = part in; WRONG = in main but differs from the approval; NOT BUILT = an approved feature that was planned for a later stage.

## Table

| # | item | owner's words (QUEUE line) | approved state + source | in main? | evidence |
|---|---|---|---|---|---|
| 1 | Scrolling map, direction A | "I like A." (424) | one big scrolling map, town in the middle, Sal walks the roads, camera follows | IN | 64x70 map, smap_eng.c |
| 2 | Sal on the map | "Sal's full-size sprite" (428); "always have him face the camera. No side view" (431) | full-size Sal, front frames only | IN | merged 2c50aac8; tests green |
| 3 | Walk speed / bob / pacing | "Map movement should be faster" (499); "bobbling effect" (521); "he bobs more slowly" (552) | fast walk, 1 px bob, step every 10 frames | IN | c7104811, 20f87ff7, b9da3d8e; story_map_scroll_walking goldens |
| 4 | Story starts in town | "Sal should start the map on the town" (487) | first map at the town stop | IN | a51e0560, test_story_map_enter.py |
| 5 | UFO beam-up on the map | "needs to do so on the map" (519) | beam at the space stop | IN | 20f87ff7; test_story_map.py:871-904 |
| 6 | Buildings keep their character | "I don't want the buildings to all look the same with a different sign" (525) | every venue unique | IN | whole-map render |
| 7 | Land kit | Q92 "Yes, take it." (562) | land part of smap_land_town | IN | 7f868ac0 is an ancestor of main |
| 8 | Fog | "Fog is not an important feature... it can be cut" (564) | fog cut | IN | gen_smap_world.py:44 "the cloud is cut" |
| 9 | Town as a venue map piece | Q91 (561); Q93 "Option 1, filled in." (567) | town option 1, plaza filled (57ef16d8) | IN | render; 1m audit: pixel-exact |
| 10 | Route: same loop order, no crossroads, no dead ends | (568-570) | layout A5 | IN | world.json legs; test_every_stop_is_reachable |
| 11 | Layout A + logic pass, coherent biomes, igloo in a real snowfield | Q94 "The igloo needs to logically be in a snowy place" (574) | A5 + snowfield (1d) | IN | render: igloo in the top-right snowfield under the ranges |
| 12 | Flat colour pads round venues on Color | Q94 "And the blank color outlines around various locations." (574) | none on Color (plan at 574: "no flat colour pads around venues on Color") | PARTIAL | town fixed (A5 town1@g); STILL PADS: stadium (row 13), bistro cream pads round the sign and the terrace, the snow pad round big mountain B on the grass, the cream road-bend wedges (cow bend, the south-middle bends), the factory's earth-yard block. sheet_02, sheet_03 |
| 13 | Level order | "reverse the lodge and bistro" (576); Q97 "igloo before lodge yes." (588) | saloon, stadium, bistro, igloo, lodge, factory, cow, tea, zoo, space | IN | world.json order; 1cee2d3c |
| 14 | Igloo redesign | Q95 "igloo and milk bar both option 1" (580); Q110 "the new igloo I approved" (643) | igloo option 1 (COCOA sign, chimney, penguin), a326fa 12f9fb70 igloo_sheet.png | IN | crops/igloo_color.png matches option 1 |
| 15 | Milk bar (the Chrome Cow) | Q95 (580), Q98 "A with C's sign... parking lot" (584), Q100 (595), Q105 (608), Q106 rounds (620-668), "Milk bar looks good now." (679) | sheet14 "raised + left", body on base, lot on the road, cow across the road, pasture (a742552 353dde97) | IN | crops/milkbar_color.png = sheet14 right column |
| 16 | Zoo redesign | Q94 "the zoo need[s] redesigns" (574); Q95 "option one... a couple of the accessory ideas from option two" (580); Q98 "Zoo: c, thinner giraffe neck" (584); "Zoo: B thin." (596) | round 3 zoo B, thin neck: lion-pillar brick gate, ZOO sign, iron gate, bamboo, croc bush, giraffe with the 4-6 px neck, fence. Branch worktree-agent-abcad1a5d685b3e59 ca2989fd, docs/dev/proposals/smap_venue_redesign3/zoo_sheet.png, src/zoo_b3.py. 45 DMG tiles, palettes ZOO + ZOOGATE | MISSING | main still has the old A5 zoo (green box gate, tools/smap_world/v_zoo.py); never in the import brief. sheet_01 |
| 17 | Space mountain (big desert mountain) dominant, base tiny | Q95 "the mountain is much more important than the military base" (580); Q98 "Mountain: A. but It shouldn't be a cross on the tower" (584) | round 3 mountain A with mast + radar (abcad1) then hangar rounds | IN | crops/airbase_color.png = hangar_sheet9 |
| 18 | Hangar / jet / runway | Q100 "no runway... little plane" (593); Q102 (601); Q108 jet rounds (614, 641): "just nudge the plane slightly to the right" | hangar 4i e898c707: ribbed hangar, empty doorway, level jet on sand, long 6-row runway | IN | moved to cell (4,34) in stage 1 (supervisor-approved forced choice) |
| 19 | Range pieces: horizontal, peak variants | Q95 "accessory mountain tiles" (580); "a little bit of variation in mountain tiles. Don't need mountain above bistro." (713) | round 3 peaks in two snowy tiers B/C, 4 variants, range A removed | IN | render (top-right ranges, nothing above the bistro) |
| 20 | Range pieces placed vertically | Q98 "versions that look good placed vertically" (584); "Vertical mountain ranges were looking better!" (597) | round 3 vertical column/zigzag (smap_venue_redesign3/range_vertical_sheet.png, src/mtn_vert.py) | PARTIAL | the art is approved but no vertical range is placed anywhere on the map (no placement was ever decided). sheet_04 |
| 21 | Stadium as a ballpark, no scoreboard sign | Q96 "I definitely don't want it being like a sign" (580) | ballpark, no scoreboard | IN | render |
| 22 | Stadium option 2 + flag | Q100 "work some more on the stands... pennants" (594); Q103 "option 2 with an added flag" (602); "Flag is too flat" (605); Q104 "flag at stadium looks great" (618) | final 2 + rippled static flag (ad92c4 8950c018) | IN | crops/stadium_color.png (stands, bunting, flag) |
| 23 | Stadium BLEND onto the map | Q110 "The baseball stadium needs some care to blend into the map." (661); Q112 "I prefer the blend version" (686) | BLEND, stadium_map_sheet2: PARK index 0 = map grass b0d080, PARK index 1 = map field 6aa048, symmetric foul lines, walkway + gate | WRONG | world.json `park` = [d0d8e0, 68b048, c09050, 101428], the pre-blend colours: pale grey-blue pads under the diamond and a darker-green right-hand wedge (the 5 GRASS cells no longer match the field). DMG matches. This is the owner's "outline of stadium". mapctx.py:143 sets the blend colours but they did not reach the snapshot. sheet_02 |
| 24 | River from the top mountains, logs lodge -> factory, organic lake, factory palette, town edges | Q95 (580); Q99 "The river should come all the way out of the top mountains. And the lake towards the bottom should avoid looking rectangular." (586) | layout A5 (a9eca06 2b2fce68) | IN | render |
| 25 | Factory ground looks natural | Q99 "Think about the ground around the factory... how can it look more natural" (586) | A5 retint (earth yard, green-grey steel); supervisor flagged "the factory yard is still a rectangle" (590), never re-asked | PARTIAL | the earth yard is still a block with a straight edge on the grass; the 11-07 seams rule (729) was not applied to it. sheet_03 |
| 26 | DMG water light | Q101 "water light on dmg is good." (592); "I thought the water was going to be lighter on the dmg" (742) | light water only | IN | main_dmg render |
| 27 | Town pixel touches | Q101 "town pixel touches look pretty good now. few quibbles." (592) | 172 touches in | IN, with an open point | the quibbles were asked for and never named |
| 28 | Logs as wood, single, fewer, sunk | "logs in water read as ice blocks" (624); Q111 "lodge single logs are better" (632); "Fewer logs" (686); "Logs are fine." (706) | 6 v1 logs, brown, half submerged (dc5c1781) | IN (static) | 6 log cells sunk, the removed 6 are water (checked cells 45,43 / 48,33) |
| 29 | Falls seam | "fix the outline so it matches color and lines up" (648) | seam fix, A5 3rd commit | IN | |
| 30 | Bridges with raised sides | (693); "New bridges look good." (701) | parapets + shadow (2b2fce68) | IN | crops/bridge_color.png |
| 31 | Map fountain miniature, broken and working | (591); "for most of the game, the fountain will be broken" (612); centred (615); 107 "Looks good" (628); awning ink (645) | fountain round 3 + 8608d684; broken until the repair | IN | 1m audit pixel-exact; world.json repair cells; smap.c:799 state 11 |
| 32 | Lodge smoke not tan | Q110 "use a different, not tan palette for the lodge smoke" (643) | white puff, water palette | IN (frame 0) | cells (58,19)(59,19) in palette water |
| 33 | Stadium lamps | "Don't like the stadium lamp effect." (643) | dropped | IN (absent) | |
| 34 | Sprite clouds | "sprite clouds drifted across the map" (711); Q114 "clouds need to stay where they are in relation to map not sal" (720); "Clouds look good." (725) | rev 2, world-pinned, 5 clouds in 4 lanes, OAM 23-35, tiles 74-89 (worktree-agent-a67fbd137dc004f62 c2355d3d, docs/dev/proposals/smap_clouds/) | NOT BUILT | planned for stage 3; branch not merged; no cloud code in src/smap*. sheet_06 |
| 35 | Road corners smooth | "Round the corners" (713); "make all rounded" (720); "smooth. Not just rounded." (727); Q115 "the 24 radius would be the minimum" (732); "115) a is good" (756) | A': 4 long bends r32, the rest r24 with trims (b7fe45af) | IN | render. The Color cream wedges at some bends are in row 12 |
| 36 | Dithered seams where two areas meet | "I want that applied to all the areas where two things meet" (729); "The grass dithering patchiness looks better now." (734) | stepped seams (1b2d8bd2) | PARTIAL | approved seams are in; seams added after them are straight: big mountain B's snow pad on the grass (y 5-7), the factory yard. sheet_03 |
| 37 | Small desert mountains + big mountain near the top | (734); Q117 "I like b more, but waterfall should be coming out of mountain" (763) | desert peaks; mountain B (cfa7dda3) | IN | render |
| 38 | Desert across the road + cactus | "Have the desert cross the road a bit. A cactus tile would be nice." (738) | spill + cacti, cactus palette | IN | render |
| 39 | Fewer round trees near the zoo, more bamboo | (744) | s1e_zoo.png "after" | IN | crops/zoo1_color.png matches s1e_zoo after |
| 40 | Overlapping tree tiles | "we need overlapping tree tiles" (746) | pine + round clusters (A' "all extras") | IN | render |
| 41 | Teahouse | pass (740); Q116 ribs + walls (761); lantern/doors (766); "Zen garden doesn't fit remove." (775); Q118 fabric flap (783); "No slit curtain looks fine." (796) | C1S d73ad77f: ribs, walls, wide noren without slit, 2 lanterns, no garden | IN | crops/tea_color.png = sheet_c1s_x6 right column |
| 42 | Falls out of the mountain, foam | "What happened to the foam" (769); falls higher (785); Q120 "Falls A will do for now" (794) | falls A f9d94afa + approved foam/lip | IN (static) | crops/falls_color.png = sheet_wide A. Owner may revisit |
| 43 | Map animations (all items) | Q104 "animate it in the game" (621); Q110 "all animations look good" (643), follow-ups (661-706), "Logs are fine." (706) | 11 items, dc5c1781 (+ falls A cascade cells, f9d94afa) | NOT BUILT (frame 0 IN) | stage 3 never started; see the animation list below. sheet_05, sheet_05b |
| 44 | Blinking lights | Q110 "Why no intentionally blinking lights?" (623) | plan: mast lamp + runway lights; delivered only the mast lamp (merged into the airbase item, 661) | PARTIAL | runway lights were never drawn or shown; the owner approved "all animations" without them |
| 45 | Stop framing at venues | Q121 "good idea. Do it." (806) | per-stop resting view, tag/panel on the side away from the venue | NOT BUILT | approved after the merge; no code in src/smap* |
| 46 | Color tile cap | "Have it check" (773) | flip-merge on Color (e3d19a93) | IN | stage 2a |

Counts (46 rows): IN 36 (rows 1-11, 13-15, 17-19, 21-22, 24, 26-33, 35, 37-42, 46), PARTIAL 5 (12, 20, 25, 36, 44), WRONG 1 (23), MISSING 1 (16), NOT BUILT 3 (34, 43, 45), with row 27 IN but holding an unanswered point.

## What an import must do (non-IN rows)

1. **Zoo B thin (row 16), MISSING.** Paste round 3 zoo B (`smap_venue_redesign3/src/zoo_b3.py` on ca2989fd, which is already an ancestor of main, so the source is on main) at the zoo venue (3,55) in place of the A5 zoo, keeping the approved bamboo and tree thinning round it. Cost: DMG ~45 tiles for the piece (the old zoo is smaller: measure the net); Color: one more palette, ZOOGATE (the round 3 notes say "zoo ZOO + ZOOGATE unmerged") = a 23rd table entry in story_scratch (stage 1e said about 4 B spare and the clouds want 1) and the zoo windows must stay at 8 palettes (the zoo windows already hold zoo, town1@z, grass, tea@g, water...: measure). Color ids: +~45 before flip-merge (main ~936 of ~1019). Worst DMG view at the zoo is not the worst map view (170 is top right), but measure.
2. **Stadium blend palette (row 23), WRONG.** Set world.json `park` to [b0d080, 6aa048, c09050, 101428] as approved (mapctx.py:143 intends that; find why the snapshot kept the pre-blend values, then re-snapshot or patch the snapshot tool). Color only, 0 tiles, 0 ids, 0 palettes (it changes an existing entry). Changes Color story-map goldens only if they show the stadium (none of the current story_map_* goldens do, by name; check).
3. **Colour pads (row 12) and straight seams (row 36), PARTIAL.** Bistro: cream pads round the sign and the terrace (palette `bistro`, index 0 cream; the A3 notes put the bistro halo at 278 px): move the cells that carry only ground + art to `bistro@g` or retype the art so the cream is not ground. Big mountain B: the `igloo` snow pad on the grass round its foot (rows 5-7, x 30-45): either a grass-index-0 mountain palette (one more table entry) or dither the snow/grass seam like the approved seams (a few DMG tiles). Road bends: cream wedges outside/inside the bends near (37,46), (50,46) and the cow bend (the 1e/1h "compromises", palette-limited). Factory yard: a dithered earth/grass seam. All Color only except seam dithering (a few DMG tiles each). Ask the owner which pads he means before redrawing; at least the stadium and bistro are certain.
4. **Vertical range pieces (row 20), PARTIAL.** Art approved, never placed. Needs an owner decision on where (Q95 suggested next to the big mountain and up round the igloo). Cost 13-15 DMG tiles per column; the top right already has the worst DMG view (170-171 of 176; 6 one-pixel DMG trims were needed there), so placing them there is risky on DMG.
5. **Blinking runway lights (row 44), PARTIAL.** Never drawn. Ask whether he still wants them.
6. **Animations (row 43) and clouds (row 34): stage 3.** See below. Costs: ROM images ~104 + 12 (falls A cascade); own tile ids +14 (lodge 2, factory 2, cows 2, logs 8) + the falls A cells; every animated cell must be pinned out of the flip-merge, but world.json `anim_cells` pins only the 3 falls A cells today (tools/dev/smap_snapshot.py FALLS_ANIM_CELLS; world_snap.py "none until the tile animation"), so pinning the other ~70 animated cells will raise the Color id count (main ~936; cap ~1019): measure. DMG VBlank peak 6 tiles (96 B, igloo view) on a walk already at 143/145 (Color) of the guard. Clouds: OAM 23-35, sprite tiles 74-89, OBJ palette 1 on Color / OBP1 on DMG, a clock byte in story_scratch (238 in the proposal) that clashed with the palette-table re-lay: re-check after the 22-entry table.
7. **Stop framing (row 45): code task**, no RAM per the plan; DMG and Color.
8. **Town quibbles (row 27)**: never named; ask.

Cost summary. DMG tiles: zoo (+net of ~45-old), seam dithers (few), vertical ranges (13-15 each, top-right risk). Color ids: zoo (+~45), pinned animation cells (unknown, likely tens), the 14+ own animation ids. Palettes: ZOOGATE (+1 table entry, window check), maybe a grass-index mountain palette (+1). Stadium fix: none.

## Animations

(a) Frame-0 static art that should be in main: checked by cell and by the stage 1l/1m audits (docs/dev/proposals/smap_import/NOTES.md "Stage 1l"): all IN.
(b) The moving part: none built (no animation table in src/smap*, stage 3 never started).

| # | item | frames source | frame 0 in main? | moving part |
|---|---|---|---|---|
| 01 | water glints, very subtle (WA, WB; 40 cells) | smap_anim items.py, dc5c1781 (owner "very subtle water please", 681) | IN | NOT BUILT |
| 02 | falls: foam streaks, churning foam lip, pool glints | dc5c1781 + 635e2b97 foam; falls A cascade cells (47,3) (46,4) (47,4), f9d94afa smap_falls_v2 | IN | NOT BUILT |
| 03 | fountain streams (working state only) | dc5c1781 03_fountain | IN | NOT BUILT |
| 04a | town bunting | dc5c1781 | IN | NOT BUILT |
| 04b | stadium flag wave, 3 frames | dc5c1781 (owner Q104 "animate it in the game", 621) | IN | NOT BUILT |
| 05 | airbase radar dish + mast lamp, one set | dc5c1781 (owner "merge the mast lamp and radar", 661); cells moved with the airbase to (8,36) (9,36) | IN | NOT BUILT |
| 06a | lodge smoke, white not tan | dc5c1781 | IN | NOT BUILT |
| 06b | factory smoke (2 cells start from blank sky: need own ids) | dc5c1781 | IN (blank) | NOT BUILT |
| 06c | igloo chimney smoke | dc5c1781 | IN | NOT BUILT |
| 07 | cow tails | dc5c1781 | IN | NOT BUILT |
| 09 | 6 logs, half-submerged, 1 px sink bob, own phases | dc5c1781 (owner "Logs are fine.", 706) | IN | NOT BUILT |
| - | sprite clouds | c2355d3d smap_clouds (not on main) | n/a | NOT BUILT |
| - | stadium lamps | dropped by the owner (643) | absent, correct | - |
| - | runway lights | never drawn | - | see row 44 |

## Sheets (in /workspace/out/audit/)

- `sheet_01_zoo.png` approved zoo B thin | main now (Color, DMG), x4
- `sheet_02_stadium.png` approved BLEND | main now (Color, DMG), x3 from the approved sheet
- `sheet_03_pads.png` main now: bistro pads, factory yard, road-bend wedges, big mountain snow pad, x3
- `sheet_04_range_vertical.png` approved vertical pieces | main ranges and desert, x3
- `sheet_05_animations.png` approved frame strips (dc5c1781), `sheet_05b_anim_main_static.png` main's static frame 0, x3
- `sheet_06_clouds.png` approved clouds (c2355d3d) | main has none
- whole map: `main_color_x2.png`, `main_dmg_x2.png`; crops in `crops/`

## Not resolved

- Why the PARK blend colours did not reach world.json (mapctx.py:143 sets them; the snapshot reads `M.PAL.get(n)`): not traced; I did not rerun the pipeline.
- Which "blank color outlines" the owner means beyond the stadium; the list in row 12 is my reading of the Color render.
- Whether the vertical range pieces were meant to be placed (no placement was ever proposed).
- In-game check: I read the data the generator uses (gen_smap_world.py takes pal_rgb from world.json); I did not run the ROM to the stadium.
