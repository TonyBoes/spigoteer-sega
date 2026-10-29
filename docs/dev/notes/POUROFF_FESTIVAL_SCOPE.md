# Pour-Off festival stage: scoping (2026-10-29, read-only; nothing in src/ or assets/ changed)

Owner: "For pour off, I want to make a festival stage that has the clown, and a mix of patrons from other stages."
Numbers are from build/game.noi, build/game.map, build/art.h, build/venues.json of main at 52eff2b1 (`make` run in this worktree).
"Assumed" marks what I did not run.

## 1. Venue

| Question | Answer |
|---|---|
| How Po gets its venue | `mg.c prelude()` returns `mg_venue[id]` for id < MG_PLANNED (10), else 0. Po (id 11) gets venue 0, the saloon. `mg_begin` calls `load_venue(0)` (venue.c): `venue_fetch(0)` copies the saloon `venue_t` into WRAM (`venue`), stage tiles to BG ids 0.., bar tiles to ids 23..35 (`bar_base` = 36 - bar_n), drink/show OBJ tiles, CGB palettes (BG 0, 5, 6, 7 and OBJ mug pals). Then `po_enter` (bank 9) reads `venue.stage_map/stage_attr/bar_tiles/pal`. |
| Bank | Saloon venue data: bank 0x18 (`venue_saloon`, about 4.4 KB incl. drink/show/anim). `po_enter` bank 9 (56 B free). Patron groups: cowboys 0x15, chefs 0x16. |
| Saloon numbers | stage_n 23, bar_n 13, pool 36 (VENUE_POOL). |
| Stage rows 1-4 only? | Stage-only is possible and cheap (below). Rows 5-16 are 4 bars built from `venue.bar_map` (2 wall rows + counter) with the keg/spout in columns 17-19 mirrored by `flip_tile`. A festival bar, wall or keg needs the 13 bar tiles (208 B), `bar_map`+`bar_attr` (120 B) and the floor tile; the left keg copies and the patron wall colour (`p[0] = venue.pal[VENUE_PAL_BAR][0]`) follow automatically. |
| Colour-only reskin | Palette overrides (`venue.pal[STAGE_A/STAGE_B/BAR/BAR_B]`, 8 B each, then `venue_pals()`) change the whole Color look at about 32 B. DMG stays grey (art is luminance-ordered). |
| Generator | `tools/gen_art.py venues()` reads `assets/approved/venues/<t>_{stage,attr,bar,bar_attr,floor,pal,drink,drink_pal,show,show_pal,tilt[,anim]}.txt/json` per `THEMES` entry into `build/venue_<t>.c` + `venue_load.c` (a `switch` in `venue_fetch`) + `venues.json`. |
| A venue that is not one of the 10? | Not by index: `THEMES` order = patron group index = level_table index (`load_venue(cur_group)`); an 11th entry would work in `venue_fetch` and `mg_venue`, but `THEMES`/`VENUES` also size `gen_pour.py`'s `pour_venue_tiles[VENUES]` (needs `assets/art/pour/festival.txt`) and tests assert the 10-entry order (`test_venues.py` lines 91, 100, 113-115; `conftest.THEMES`; `boss_common.THEMES`). Also needs every required venue file (drink, show, tilt: copies of the saloon's, about 2-4.4 KB ROM). |
| Recommended | An overlay, not an 11th theme: Po keeps venue 0 (drink, show, pour art, mugs, tests of mugs) and in `po_enter`, after `load_venue`, copies festival stage tiles over BG ids 0..22 (at most 23 ids: bar tiles own 23..35), `venue.stage_map/stage_attr` (80+80 B in the WRAM `venue` copy, so the banner "put back" code `S.wall/S.wattr` follows for free), and on Color the stage palettes. Optional second step: same for the 13 bar tiles + `bar_map/bar_attr` (the bar_tiles pointer is in ROM; Po copies from `venue.bar_tiles`, so Po would load festival ones through its own pointer). ROM for the stage overlay: tiles 23 x 16 = 368 B + 160 B maps + 16 B pals + about 100 B code = about 650 B. Generator: a small `OVERLAYS = ["festival"]` pass in `gen_art.py` reusing the stage-dedupe code of `venues()` (files `assets/approved/venues/festival_{stage,attr,pal}...`). Stage animation is not run in Po. |

## 2. Crowd budget in the Pour-Off

Per look today: 12 BG tiles (shift-0 pose 4 + blank pair 2 + shift-2 sway pose 6). Po picks `s->v = mg_rand() % 3`; palette `BGPAL_PATRON + v`.

| | Free now | Looks |
|---|---|---|
| BG tile ids, both modes | 77-85 flipped kegs (9); 86-121 the 3 looks (36); 122-127 free (6, `po_fits`: `PO_PAT + 36 <= MG_GAME_BG + 3` = 128); OBJ owns 128-189 (Dregs 128-183, DMG mug copies 184-189); 190-219 free and 221-233 free (220 is the HUD hourglass; Marshmallow, the game with the most BG tiles, ends at 219; Po loads none there: assumed, extend `po_fits` and test) = 30 + 13 = 43. | 12 a look contiguous: ids 86-121 (3, existing), 190-219 (2), 221-233 (1) = **6 looks**. With the blank pair shared (10 a look, 2 once): 86-127 (4), 190-219 (3), 221-233 (1) = **8 looks**, but it needs a per-look base table (today `PO_PAT + v * 12`). |
| CGB bank 1 | BG tile ids in bank 1 are free in Po (Saloon level already keeps 5 looks there: `patron_tiles_saloon_x`, `SALOON_X_S0` 206..255). Tiles are not the limit on Color. | tile-wise 8+ |
| DMG colours | One BGP for all; the art is index 1-3 ordered light to dark, so every look reads by value on the same grey ramp. No palette limit on DMG: it is tile-limited (6 looks at 12, 8 at 10). | 6-8 |
| CGB BG palettes | Slots: 0 bar, 1 HUD, 2-4 the 3 looks, 5-6 the stage (saloon stage uses a few tiles of 6), 7 `BGPAL_BAR_B` (keg/spout: the saloon's `bar_attr` is all 0, so 7 is unused in Po; the Saloon level already uses it as look 3). | now 3; **4 with 7**; **5 with 6 too** if the festival stage is drawn with one palette (5); a 6th by the mid-frame split (`split_isr`, level.c only today, armed for the Saloon level; it rewrites BG pal 5 below the stage). The split on the mini-game banner path is the risky part: not recommended first. |
| Looks beyond the palette count | A seat's attribute chooses any palette for any tile set, but a wrong palette recolours the look. Two looks share one palette if their 3 colours are close (palette variants, spec section 3). Needs art checking. | 6-8 tile looks on 4-5 palettes only where colours agree |

So: DMG 6 (8 with the shared blank), Color 4 to 5 true-colour looks (5 = needs the festival stage on a single stage palette). `po_crowd` is a 3-row (group, variant) table and `BGPAL_PATRON + s->v` in `po.c` (lines 98, 149-160, 273-275) must become a table of (group, variant, tile base, palette slot).

## 3. Loading patrons from any group

- Today `po.c` references only `patron_tiles_cowboys` and `patron_tiles_chefs` (`BANKREF`s) and `load_crowd` picks one of two with `if (g == 3)`.
- Layout is identical for all 10 groups (same `PATRON_SHIFT0_OFS` 128, `PATRON_BLANK_OFS` 126, `PATRON_TILES_PER_GROUP` 140, look v shift-2 pose at `v * 42 + 6`): any of the 30 base looks (10 groups x 3 variants) is loadable with no new ROM data, only a lookup table group -> (pointer, bank): 10 x 3 B plus about 80 B code = about 120 B. Palettes: `patron_pal_get(g, v)` (bank 0x19) already serves all groups for v 0-2; for v 3+ it hard-codes the Saloon's `cowboys_d/e`, so use v 0-2 of other groups (assets/palettes.json `<group>_a/b/c`).
- Group blobs: 2432 B each (152 tiles); cowboys/sports/lumberjacks bank 0x15, chefs/divers/punks/robots 0x16, ninjas/zoo 0x17, aliens 0x18. `po_enter` calls `bkg_data_far` 3 times a look (LCD off), so it is bank-switch only, no ROM cost per look.
- Color-only extras: only the Saloon has any (`patron_tiles_saloon_x`, bank 0xF, 4032 B = 5 looks x 806 B, loaded by `load_saloon_x(part)` into fixed bank-1 ids 206..255 by `tile_copy`). None exist for other venues yet. To use them in Po, add a generated accessor (pointer + bank + pose offsets) and load into any chosen bank-1 id with `VBK_REG`: about 100 B. Extras for other groups, once made, cost about 806 B per look in a new bank (not Po's).
- The clown (BIGWIG v2, `docs/dev/concepts/new_patrons/v2/redo.txt`, skin #f8c8a0 / red #e04040 / blue #2838a0, 16x16 front): not in `assets/art/patrons/`. Cheapest for Po: a Po-only pack through `gen_art.py`'s existing shifter producing just shift-0 + shift-2 poses (10 tiles + the shared blank = 160 B a look, 192 B at 12) plus 1 `palettes.json` entry (8 B). No back view is needed (Po patrons do not walk or turn). If it is also wanted as a Stadium/anywhere extra later, the full 50-tile look is about 806 B (then Po reads from that).
- ROM room: banks are packed full (romusage: ROM_1..9, 21-24 under 70 B free; ROM_25 1142 B free; ROM_10 206, 13 215, 19 234; ROM0 453 B real free by the linker map, 794 by romusage). `po.c` is autobank (bank 9, 56 B free): +about 250 B (table, loader, overlay code) will make bankpack move something, which it does automatically. The image is 32 banks (header 0x148 = 04, 512 KB) with 26 banks used, so 6 empty banks exist; bankpack uses them when needed (assumed; not tried). ROM is not the limiting budget; WRAM and palettes are.

## 4. WRAM

No new globals. `po_state` is 514 B of the 520 B `story_scratch` (`STORY_SCRATCH`, mg union): 6 B free (seat 58..142, mug 142..222, sbuf/sattr 72 B each, hud 7, wall/wattr/hattr 140, pend 1; the asserts `po_off_a` and `tests/po_helpers.py` fix offsets up to `mug`, so new bytes append at the end). The crowd needs no new state: the seat's `v` byte already holds the look (0..N-1; only the `% 3` and tables change). Tile bases and palette slots come from ROM tables. If more is needed: `hattr[20]` is a constant fill (BGPAL_HUD) and could be dropped (about 20 B), or the sbuf/sattr could be written straight to the VBlank queue. WRAM now: WRAM_LO 3936/4096 (160 free), WRAM_HI_0 3635/4096 (461 free); unchanged by this note. HRAM/`BOSS_OWN` are not needed.

## 5. Tests and goldens that a festival stage would touch

- Goldens: all six Po stills change on DMG and Color (12 files): `po_intro`, `po_win`, `po_lose_lives`, `po_dregs_wins`, `po_perfect`, `po_slip` (stage rows 1-4 = pixel rows 8-39; crowd columns of the bars when seats are filled; the bars/palettes if the bar or palettes change). The seat look order changes with `% N` (the same one `mg_rand()` call per spawn, so the timing is unchanged, only which look appears). Mugs/Dregs/HUD stay. `story_pic_finale_a` / `story_pic_finale_contest` change only if the finale pictures or text change: the finale pages say "THE POUR-OFF WILL BE AT SADIE'S SALOON." (`test_story.py` line 811, story data): an owner text decision (the story map already has a FESTIVAL SQUARE stop).
- Test files: `tests/test_pouroff.py` (37 tests; the stage/bar checks use `SALOON[...]` lines 39, 162-191, 380; the crowd test lines 27-31, 239-248 hard-codes `BG_PAT=86`, `CROWD` and the palettes), `tests/po_helpers.py` (offsets), and mentions in `test_barchange.py`, `test_pause.py`, `test_story.py`. An 11th theme would also break `test_venues.py` (THEMES order, 10 story venues), `boss_common.py`, `conftest.py` and the pour-art test; the overlay avoids all of those.
- Perf guard: Po has no listed guard here; the load runs with the LCD off. Not measured.

## 6. Recommended plan

| Step | What | DMG / Color | Budget |
|---|---|---|---|
| 1 | Generalise the crowd: `po_crowd` becomes a table (group, variant, tile base, BG palette slot); loader reads any of the 10 groups' pointers/banks; `mg_rand() % PO_LOOKS`. Start with 6 looks: the 3 now plus 3 from other stages (stage-art owner picks). Extend `po_fits` for ids 190-219 / 221-233. | DMG 6 looks (tiles), Color 4 palettes (2, 3, 4, 7) | +about 150 B ROM, 0 WRAM |
| 2 | Palettes: slot 7 for look 4; festival stage drawn on one palette frees 6 for look 5. Check shared-palette pairs by picture (one contact sheet at 1x and x4, DMG and Color). | Color only | 0 |
| 3 | The festival stage overlay (rows 1-4 tiles <= 23, map, attr, 2 palettes) from new files in `assets/approved/venues/festival_*` via a small `gen_art.py` pass; applied in `po_enter` after `load_venue`. Art through the `gb-artist` agent (proposal first, per the owner's rule). Optional: Color-only palette reskin of the bars (about 32 B) so the DMG path is unchanged. | stage tiles both (DMG grey); recolour Color only | about 650 B ROM, 0 WRAM |
| 4 | The clown: a Po-only look from the BIGWIG v2 concept (shift-0 + shift-2 only; `palettes.json` entry). Place it on both (4 indices read on the DMG ramp), or Color-only per the owner's extras rule, with a base look on DMG in its place: owner call. | open | about 200 B ROM |
| 5 | Optional later: festival bars/keg (13 tiles + maps, about 330 B); a 6th Color palette by the mid-frame split (risky, skip until needed); Color-only extras from other groups once they exist (about 806 B each, about 100 B loader). | Color only | ROM only |
| 6 | Tests: rewrite the crowd/stage asserts in `test_pouroff.py`, add a test for each look's tiles/palette and a junk-poke check; list the 12 changed goldens with `tools/dev/golden_bbox.py` for the supervisor; update story text only if the owner agrees. `make test`, `make check`, `make cfall` (no asm touched). | both | |

Open owner questions (not asked here): is the clown on DMG too; what the finale text should say if the venue is no longer Sadie's saloon; which three other stages' patrons.

## Owner decisions (2026-10-29)

- Q20: the festival is a whole room (stage, wall, bar, colours), not just the stage.
- Q21: "you suggest": the clown in every game (DMG and Color, a Pour-Off-only pack) plus a rotating mix from DUSTY, PETE,
  CEDAR, PIERRE, IGGY, BOXY, SPIKE, KAGE, COCO, ZORP (6 looks per game on DMG, 4-5 on Color).
- Q22: yes, the finale line becomes "THE POUR-OFF WILL BE AT FESTIVAL SQUARE." Change it in the same build as the
  festival room (story_pic_finale goldens move then).
- Q26: "a is better, but include background buildings from the story scenes. Don't need giant booth. Change color so
  less like stadium." A2 in docs/dev/concepts/festival_room/A2/.
