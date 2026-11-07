# Color tile-id cap (1024): can the spare bit lift it? Findings 2026-11-07

Read-only investigation, main at 52eff2b1+. Nothing in src/ or tools/ changed. Numbers from a `make` in this worktree.

## Answer in one paragraph

Yes. The Color build can go to 2048 ids for **0 bytes of WRAM**: the Color engine never stores a tile id at run time (only the DMG does). But the 10-bit word is not
the only ceiling: the Color tiles live in ONE ROM bank (`smap_c_t`, 16 B each + 69 B code), so about 1018 tiles is a hard limit too. Lifting the id needs a
second tile bank. The cheaper way to get under both limits is to merge mirrored tiles with the Color attribute flip bits (about 11 percent of the ids on main's set), also Color only, also 0 RAM.

## 1. The cell word (Color; the DMG word has no palette)

| Item | Evidence |
|---|---|
| Color word: bits 0-9 tile id, 10-14 palette (0..17), bit 15 unused | tools/gen_smap_world.py:55 (TILE_MAX), :119 (`grid \| pal << 10`), :160 and :182 (fog words, same layout), :117 (`assert nt < TILE_MAX`), :194/:196 (verify_fog) |
| DMG word: bits 0-9 id only (bits 10-15 zero) | gen_smap_world.py:119 (`if cgb`), smap_d_fetch uses `w & 0x3FF` (:578) |
| Run time reads the word at 4 Color places | smap_eng.c:564 (`& 0x3FF`), :567, :643, :656 (`(uint8_t)(f->w >> 10)`: bit 15 would leak into the palette, must be masked or the layout moved) |
| Bit 15 is free on both machines | The VRAM attribute is built from the hardware palette slot and the bank bit only: smap_eng.c:586 `att = hw \| (bank ? 8 : 0)`; no flip, no priority. Fog is a separate zone byte (`z & 15`, `z >> 4`), not in the word. smap_eng.c:1203 `0x8000` is a vq-entry flag in the copy list, unrelated to cells |
| Where the map lives | Color: bank 4 (`smap_c_a`, 0x4000-0x7868 = 14440 B: cell 6144 B, zone 3072, fog lists ~3.1 KB, slotvar 1406, palettes; the pour code shares the rest). DMG: bank 7. Color tiles bank 11 (`smap_c_t`, tiles at 0x4045), DMG tiles bank 15. Each machine has its own copy of the cells |

Main today: DMG 623 ids, Color 703 (build/smap_world.json). The 970 / 1040 figures are the import branch's world (docs only; its generator file is identical to main's, so the same asserts apply).

## 2. What holds an id at run time

| Holder | Color | DMG |
|---|---|---|
| Slot table `A_TBL` (smap_priv.h:21, 220 B: 176 low bytes + 44 B of 2-bit highs, 0x3FF = free) | not used | DMG only; tbl_get/tbl_set/tbl_find (smap_eng.c:495-512), `& 0x3FF` at :608/:657/:660, smap.c:794 |
| Color resident record `A_NIB` (smap_priv.h:24, same bytes as A_TBL): 352 slots x 4 bits = the variant resident | stores (slot, variant), never an id | n/a |
| id to slot map | `smap_c_slotvar[id]` u16 = slot (9 bits) \| variant << 9, in the ROM cells bank (gen_smap_world.py:422, :578, :712) | `smap_d_hint[id]` u8 in ROM |
| story_scratch | no id anywhere | `V_ID`/`V_PWL/H` hold a DMG id for the asm |
| The only Color use of the id | `tile_load(.., t)` -> `smap_c_tile(uint16_t t)` (smap_eng.c:515-517), `t << 4` is fine up to 2047 (32752 fits u16) | |

Extra WRAM for an 11-bit Color id: **0 bytes**. Slot table is not shared in practice: the DMG model and the Color model lay different tables over the same bytes (smap_priv.h:21-24).
DMG 10-bit stays (DMG ids ~970 < 1024), so no DMG byte, branch or asm routine (`smap_dadd`, `smap_scan`, `smap_burst`) is touched.

Budgets (build from this worktree, before; unchanged by any route below): WRAM_LO 3936 / 4096 (160 free), WRAM_HI_0 3635 / 4096 (461 free).
romusage: ROM0 818 free by its column, 477 free by the linker map line (ends 0x3E23); banks 1-33 each 11-539 B free; bank 34 has 1616 free. The ROM is 35 banks.

## 3. Alternatives

| Route | WRAM | ROM | CPU / VBlank | DMG risk | Effort |
|---|---|---|---|---|---|
| **A. Flip-merge Color tiles** (canonical tile + attribute X/Y flip bits 5, 6; the flips ride in slotvar bits 11-12, `att \|= (aux >> 6) & 0x60` in add_cell). Measured on main's set: 81 of 703 Color tiles (11.5 percent) are exact flips of another (DMG: 72 of 623) | 0 | smaller: about 12 percent fewer tiles (-16 B each), slotvar same size | about 8 cycles per new cell, none in VBlank | none (Color only, behind `is_cgb`; fetch is the Color's own C routine) | small: generator canonicalisation + slot colouring on canonical tiles, 2 engine lines, tests |
| **B. 11-bit id** (word = id low 11 bits, palette << 11; masks `0x7FF`, `>> 11`) | 0 | needs a **second tile bank** (1050 x 16 = 16800 B > 16384) and a `t >= N` choice in tile_load between two BANKED loaders (about 15 B in smap_eng's bank, ROM0 untouched); slotvar grows 2 B per id (about +700 B: `smap_c_a` 14440 -> about 15140 B, still one bank, bankpack moves the pour code out) | one compare per tile load; none in VBlank | none (Color-only generator branch and Color engine lines); tests/test_story_map_world.py:82 decodes `w >> 10` and needs the new layout | medium |
| C. Use the VRAM bank bit as the 11th id bit | | | | | **does not apply**: ROM ids never reach VRAM; the bank bit already picks the slot half (slot9 >= 176, smap_eng.c:571,586) |
| D. Id to tile through a ROM table | | | | | already how it works (`slotvar`); it adds nothing |
| E. Two id spaces by area (north / south) or per-zone pools | 0 | duplicated slotvar and cells headers, shared ground tiles stored twice | fetch dispatch by row | none | **largest**: ids, slot colouring and fog are numbered globally ("first-use order over the unlock states", `state_end_c`); the colouring must stay global across the border |

## 4. ROM

Extra graphics for 1040-1050 ids over 1023: about 30 tiles x 16 = 480 B (to about 700 B counting up to 47 tiles) plus 2 B per id of slotvar (about +100 B). The real step is the bank: one tile bank holds about 1018 Color tiles (16384 - 69 code), so B needs a second bank file; A avoids it. Banks are full (most have under 100 B free), so autobank shuffles; the ROM has 35 of 64 banks used, no size change expected. ROM0 is untouched by every route (all edits are in banked generated code and smap_eng.c): keep the 477 B (linker) free.

## 5. Recommendation

1. Stage 2a (small): **Route A**, flip-merge, generator + 2 engine lines, all behind the Color branch. It cuts about 100 ids, so 1050 becomes about 930, clears both the 10-bit and the one-bank limits, and costs 0 WRAM and no ROM0.
2. Stage 2b only if headroom beyond about 1100 ids is wanted: **Route B** (repack word to id 11 bits + palette 5 bits at `>> 11`, second tile bank, split loader).
3. Not recommended: C (does not exist), D (exists), E (largest, no gain over B).
4. Gate everything with `is_cgb`; DMG: no source or data change. Run `make cfall` (nothing asm is touched), `make test`, `make check`, and a junk-poke test of the Color slotvar bits.

## Checked and inferred

Checked: the word layout and its readers (file:line above), the build numbers, the bank addresses from game.noi, the flip count on main's tile set (script over `tiles_c`).
Inferred: the import world's flip share (about 11 percent, from main's set; its 1038-id set was not generated here), that bankpack would place a 15.1 KB `smap_c_a` without growing the ROM, that a 1023-tile bank overflows (16368 + 69 B code > 16384; the import notes say 1023 passed the generator, which checks ids, not bank size).

## Addendum: Route A measured on the real import map

Method: this branch merged `worktree-agent-a54af93b56f257307` (import tip with B, cave, falls) and `worktree-agent-a83b5a5dd7379df95` (teahouse) with `--no-ff` as scratch;
`mk_src.py` + `mk_a5.py` regenerated the scratch generator; `out/flipcount.py` builds the Color and DMG models (mapctx defaults, palette table widened as measure.py does,
TILE_MAX raised to count) and merges exact pixel flips of the 8x8 tile signatures (palette is not part of a tile, so a flip merge ignores it). Not committed: out/ and the generated src/ files.

| Set | Color ids now | X | Y | XY | merges | ids after | tile bytes | vs one-bank limit 1019 tiles (16304 B + 69 B code) |
|---|---|---|---|---|---|---|---|---|
| Default (A' + B + cave + falls) | 1040 | 99 | 19 | 12 | 130 (12.5 percent) | 910 | 14560 | 1744 B (109 tiles) spare; unmerged 16640 B is 325 B over the bank |
| Default + teahouse BWD (SMAP_TEA_PASS=1 SMAP_TEA_TEX=BWD, merged cleanly, not estimated) | 1040 | 90 | 19 | 12 | 121 | 919 | 14704 | 1600 B (100 tiles) spare |
| DMG for reference (unchanged, no flips used) | 975 / 976 | | | | | | | |

The teahouse texture removes 9 flip pairs and adds no raw id here (1040 both ways), so it nets +9 ids after merging. The default 1040 is the import's 1038 plus 2 from main's newer world.

What flips can break (inferred from the engine code and the import notes; not run):
- **Animation frame tiles.** Frame 0 is the map tile and the frames are written over the tile's VRAM slot (NOTES.md:177). A flipped cell sharing a canonical tile's slot would play the same frames unflipped or mirrored by attribute, wrong for the falls, water and smoke. Rule for the generator: animated map ids are excluded from merging (or merged only among cells with the same flip). Not a count problem: the animated tiles are a few dozen.
- **Fog.** Fog ids are ordinary ids in the word (`fint`, `fword`); the flip is derived from the id through slotvar, so edge words and interior parity tiles need no change. `add_same` compares the whole word (smap_eng.c:897-898), so two ids with the same slot and different flips are never treated as the same cell.
- **Palette variants.** A variant is a nibble per slot (up to 3 tiles per slot). Flipped ids share the canonical tile's slot and variant, so colouring runs over canonical tiles only (fewer tiles, easier). The palette is per cell and independent of the flip.
- Nothing flips on DMG: the DMG word, hint table and asm are untouched.
