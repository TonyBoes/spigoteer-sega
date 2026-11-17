# Credits scene pages: handoff for the credits integrator (final set, round 18)

Updated for round 22 (every owner as the story portrait inside the credits silhouette). Branch `worktree-agent-aa21f868f71a0344f`, folder `docs/dev/concepts/credits_scenes_2026-11-13/`. Final cards: `round18/<venue>_card_{dmg,cgb}.png` (160 x 144, as the roll shows the page), sheet `round18/final_sheet_x3.png`,
per-page data `round18/data/<venue>.json`, costs `round18/costs_final.json`, proof that every card equals the approved round's: `round18/identical_to_approved.json` (14 of 20 identical pixel for pixel to the approved rounds; the Chrome Cow, Saloon and Jungle Zoo cards changed on purpose in rounds 19-22).
Nothing here touches `src/`, the Makefile or `tests/approved`.

## What you need from this branch
1. **The data**: `round18/data/<venue>.json` (venue keys: saloon, sports, lodge, bistro, igloo, factory, biker, teahouse, zoo, space). Per page:
   - `picture_cells` {x:3, y:2, w:14, h:9}: the scene box (112 x 72 px) inside the story-style 160 x 104 picture (20 x 13 cells) that sits at card y 32; box top-left on the card = (24, 64). Dark margin around it is the page background.
   - `bg_dmg` / `bg_cgb`: 9 rows x 14 cells; per cell `shades` (64 values 0-3, row-major) and `colours_by_shade` (the cell's four colours as hex, Color; null = unused). DMG and Color differ only where the venue's performers differ (the DMG show art vs the Color show art are drawn into the BG as BG art, each performer with one BG palette).
   - `owner_edge_sprites`: the owner's pixels in edge cells (cells that hold owner and room) as 8 x 8 index grids (`idx_8x8`, values 0-3, 0 transparent), `cell_x`/`cell_y` in box cells, `obp` (0 or 1), `obj_palette` (index into `obj_palettes_cgb`). `objects_8x16`: those sprites paired vertically into 8 x 16 objects (`second_cell_stacked` true = the object's lower half is the sprite one cell down; false = a blank lower half).
   - `obj_palettes_cgb(idx1..3)`: the OBJ palettes (hex, null = unused index). `dmg_obp_mapping`: OBP0 idx 1,2,3 = DMG shades 0,1,2; OBP1 idx 1,2,3 = shades 1,2,3 (set OBP0 / OBP1 to those mappings on DMG: the tiles are the same on both machines).
   - `bg_cells_owner_only`: cells entirely owner pixels (BG cells in the owner's palettes); `bg_cells_owner_fallback`: cells kept as BG owner cells to meet 8 sprites a line (Kiki's (4, 6) only).
   - `bg_palettes_cgb`: the BG palettes the page needs (shade 0..3), as packed.
2. **Or regenerate** (the generator, same code): `python3 docs/dev/concepts/credits_scenes_2026-11-13/render_q.py` (needs `assets/` and PIL; writes round18/). The default build is `scenes_final.build_final(key)`: every owner's approved choice is set there, nothing else is read from global state. Inputs: the portraits `assets/story/portraits/<owner>.txt`, the venue art `assets/approved/venues/<venue>_{stage,bar,floor,attr,bar_attr,pal}`, the show art `<venue>_show*.txt` + `<venue>_show_pal.json`, and three owner cut-outs (copied to `round18/owner_masks/`: June, Kiki, Hana).
3. **The mask rules**: the cut-out of each owner from its backdrop is `scenes_c.backdrop_mask` (open backdrop connected to the portrait's top or side edge, no dilation: the portraits draw their outline in the backdrop colour; Zizz alone is dilated by one pixel) except June, Kiki and Hana, whose masks are the owners' own pictures (`scenes_c.picture_mask`; Hana flood-filled from the picture's edge; June's picture is a zoomed crop: `JUNE_GRID`, its last column and row come from the rule). Only the mask comes from the pictures: the art colours are the game's.

## Layout and model (all ten pages)
- The owner's portrait as drawn, 56 x 56 at box pixel (0, 16): its bottom edge is the box's bottom edge; the owner is on the LEFT. The venue's room (the game's own stage / bar / floor tiles, in the venue's own palettes) is behind and to the right; the venue's show performers are BG art (their own pixels, one BG palette each, the room's commonest colour on its own shade, the performer's three colours on the other three shades light to dark).
- Cells that are entirely owner: BG, the owner's palettes. Cells that hold owner and room: the room's BG tile (the owner's outline pixels, the story background colour, are BG pixels in the room palette's nearest colour) plus the owner's other pixels as OBJ sprites (8 x 16 mode), colour 0 transparent.
- Under overhangs (brims, hat edges, hair ends, chins) the one pixel outline is two pixels thick (the second pixel, in the same colour, is BG): `scenes_f.UNDER`.

## Costs per page (final set)
| page | source round | BG tiles DMG / Color (flips merged) | BG palettes | OBJ tiles | OBJ palettes | objects | max sprites a line | edge cells as sprites | edge cells left as BG owner cells |
|---|---|---|---|---|---|---|---|---|---|
| THE SALOON (SADIE) | round 22 | 91 / 90 | 7 | 20 | 7 | 18 | 7 | 18 | 0 |
| THE STADIUM (COACH) | round 15 | 79 / 79 | 7 | 19 | 5 | 14 | 6 | 19 | 0 |
| THE LUMBER LODGE (JUNE) | round 12 | 81 / 79 | 8 | 19 | 5 | 15 | 6 | 19 | 0 |
| THE BISTRO (COLBY) | round 9 | 76 / 74 | 9 | 18 | 5 | 16 | 7 | 18 | 0 |
| THE IGLOO (AURORA) | round 9 | 82 / 81 | 8 | 17 | 4 | 13 | 7 | 17 | 0 |
| THE ROBOT FACTORY (MANAGER-BOT) | round 9 | 85 / 83 | 8 | 18 | 3 | 15 | 6 | 18 | 0 |
| THE CHROME COW (GRANNY) | round 21 | 90 / 89 | 8 | 23 | 6 | 20 | 8 | 21 | 1 |
| THE TEAHOUSE (HANA) | round 17 | 75 / 74 | 8 | 21 | 2 | 16 | 7 | 21 | 0 |
| THE JUNGLE ZOO (KIKI) | round 22 | 84 / 80 | 8 | 26 | 5 | 20 | 8 | 24 | 3 |
| THE SPACE LOUNGE (ZIZZ) | round 9 | 52 / 52 | 6 | 20 | 2 | 14 | 6 | 19 | 0 |

**Known over-limit: the Bistro needs 9 BG palettes (the room's palettes plus the owner's three plus two performers), one more than exist; it was 9 in round 9 and the owners approved the page as it is: the integrator must merge or move one palette (the performers' two BG palettes are the candidates).** Pages over the 69 free BG ids: all except Space (52).

Limits used: at most 8 sprites a line, at most 8 BG palettes (and 8 OBJ palettes), objects <= 23 (40 minus a patrons card's 16 and the hat; the engine now allocates OAM dynamically, so use 40 minus what is on screen with the page). The BG tile figure assumed 69 free ids (BG ids 77-145) in earlier rounds; several pages exceed it (see the BG tiles column): the integrator decides the slot layout.

## Palette slot changes (the room's palettes; the art is never recoloured)
- **Teahouse** (Hana, Color): slot 3 of `stage_a`, `stage_b` and `bar` = `#100818` (was `#281410`, `#281410`, `#1c0c0c`): the owner wants the outline dark blue. Side effect: the room's own darkest pixels in those palettes (wood lines, lattice, counter front edges) are navy-black instead of red-black (1158 room pixels). DMG unchanged.
- **Jungle Zoo** (Kiki, Color): slot 3 of the zoo `bar` palette = `#2c1808` (was olive `#384018`, the colour `bar_b` already has): near-black hair pockets and outline, the counter keeps its gold. Side effect: the counter front's darkest pixels across the bar band are near-black brown. DMG unchanged.
- No other palette is changed. Cells that carry the owner use the owner's own palettes (the story packs them: 3, Zizz 2).

## Page-specific edits (all are BG pixels in the room, not the owner's art)
- **Coach**: 13 room pixels under the brim tip go to the stage palette's darkest (`#101428`, DMG shade 3): portrait pixels (35,14) (36,14) (37,14) (38,14) (39,14) (38,15) and (40..46, 15). No wall blue is left under the brim (x 24-46, rows 11-15).
- **Kiki** (round 22): every colour is the story's (his mask gives the silhouette only; the two odd pixels of round 12 are dropped); her lips are the story's Color-only OBJ accents, `#d04838` (7 px) and `#a03020` (6 px): Color-only sprite pixels over the BG replacement. 8 sprites a line with them counted; three edge cells ((1,7), (4,6), (5,6)) are BG owner cells to meet that.
- **Sadie** (round 22): the story's Color-only gold OBJ accents, `#f8d048` (20 px) and `#c88820` (7 px) (the sheriff's star), as Color-only sprite pixels over the BG replacement (skin `#d8a878`); not drawn on DMG.
- **Granny** (round 21): the silhouette is her own cut-out (`owner_masks/owner_granny_mask.png`, teal (48,101,91) = room; none of her art is cut); EVERY colour is the story portrait's (`assets/story/portraits/granny.txt`): his file gives the mask only. The heart tattoo is the story's black; her lips are the story's two Color-only OBJ accents, X `#a02028` (8 px) and Z `#d84040` (4 px) around portrait (28-31, 32-34): Color-only sprite pixels (one cell, (3, 6); not drawn on DMG, where the story shows the BG replacement `#c87850`) over the BG. Audit against the story portrait: 0 colour and 0 DMG-shade mismatches inside the silhouette. At most 8 sprites a line and 8 BG palettes with the lips counted; one edge cell, (4, 6), is a BG owner cell to meet 8 a line.
- **June**: his mask, including the two blue specks inside the hat at portrait (14, 13) and (11, 15) (room shows through, as drawn).

## Audit against the story portraits (round 22)
`round22/audit/audit_story.json` (+ `<owner>_mismatch_x8.png`): for every pixel inside each credits silhouette (the outline ring excepted) the Color colour and the DMG shade against the story portrait's (its Color-only OBJ accents at their own colours): **0 colour and 0 DMG-shade mismatches for all ten owners.** The story's Color-only OBJ accents (Sadie's gold, Granny's and Kiki's lips) are Color-only sprite pixels over the BG replacement, built by `scenes_final` (`accents: True`) and `scenes_f.OVERLAY_COLOR_ONLY`; they are not drawn on DMG.

## Not in the final set
The toggles of the earlier rounds (`PAINT_ON`, `GAPFILL` except Coach's, `JUNEFILL`, `RING_PAL`, `JUNE_FIX`, `JUNE_MASK`) stay in the code, off; `scenes_final.CONFIG` is the only place the final choices are set. Older rounds can still be rebuilt by setting them by hand.
