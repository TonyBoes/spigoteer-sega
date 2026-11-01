# Plan: Color-only extra looks and palette swaps in every venue (generic mechanism)

Status 2026-10-31: DESIGN ONLY. Step 1 is written; Step 2 (build it for the Robot Factory) is NOT started because the design hit a
blocker that needs an owner / supervisor decision (section 1). Nothing in src/ changed. `tools/dev/extra_combos.py` (read-only) prints the numbers below.

Baseline (this branch = main 8427e2b9 + nothing): ROM0 real free 440 B (linker map; romusage says 781), WRAM_LO 3936/4096 (160 free), WRAM_HI_0 3635/4096
(461 free), banks 1-25 16-234 B free each, ROM_26 14 872 B free (banks 27-31 are unused: 5 more banks).

## 1. The blocker: BG palette slots (what the plan needs against what the engine can do)

A patron instance is an OBJ palette (lifted) plus a matching BG palette (walking, colours 1-3 equal, colour 0 = wall). The OBJ side has 8 slots
and the plan fits. The BG side is the limit, as the Atlas says. What the engine does today:

- The Saloon has 5 instances: BG 2, 3, 4, plus BG 7 (the keg's slot; the Saloon's keg is on BG 0, so BG 7 is free) plus BG 5 through the
  mid-frame split (`SPLIT_PAL`, level.c split_arm / main.c split_isr: the stage palette above line 39, the patron palette below).
- Every OTHER venue has its keg / spout on BG 7 in the playfield (checked on the atlas capture of all 10 level screens: only the Saloon's keg is BG 0),
  so BG 7 is taken. Today's capacity outside the Saloon is **4 instances** (BG 2, 3, 4 and the split's BG 5).
- What each venue's plan needs (`python3 tools/dev/extra_combos.py`; instances = patron OBJ slots after the plan's moves / adds / joins, OBJ 0 counts
  where the plan moves a patron to Sal's colours or VARIANT_CUTS names slot 0):

| venue | looks | instances (OBJ slots) | allowed combos | BG short by |
|---|---|---|---|---|
| Saloon | 8 | 5 (built) | 36 (built) | 0 |
| Stadium (sports) | 8 | 7 (0 1 2 4 5 6 7) | 50 | 3 |
| Lodge | 8 | 6 (1 3 4 5 6 7) | 42 | 2 |
| Bistro | 8 | 6 (0 3 4 5 6 7) | 38 | 2 |
| Igloo | 8 | 6 (2 3 4 5 6 7) | 28 | 2 |
| Robot Factory | 8 | 6 (1 3 4 5 6 7) | 48 (no cuts) | 2 |
| Chrome Cow | 8 | 6 (2 3 4 5 6 7) | 48 (no cuts) | 2 |
| Teahouse | 8 | 6 (0 3 4 5 6 7) | 36 | 2 |
| Zoo | 8 | 5 (1 3 4 6 7) | 23 | 1 |
| Space Lounge | 8 | 7 (1-7) | 42 | 3 |

- The Factory (the venue of this task) needs OBJ 1 (CLANK, PEPPER: the full mug's colours), 3 (BOXY), 4 (BLIP, NEKA: cyan), 5 (TOOB), 6 (VOLTA),
  7 (TELLY: BLIP's old mint) = 6 instances, 8 looks x 6 = 48 combos. The engine gives 4 BG slots. It also needs the Factory's enhanced BOXY
  (OBJ 4 / BG 7 top row, enhance.c) dropped on Color (DROP_ENHANCED in the plan), which changes the Factory's Color pictures.
- The plan itself assumes the BG side is solved by "the BG palettes above the playfield are reloaded where the playfield starts" (plan_data
  SPLIT_PLAYFIELD) and "the keg / spout palette moves from BG 7 to BG 1" (FIELD_MOVES). Neither is built. Built, the playfield would have BG 2-7
  free for patrons (6 slots): BG 5 and BG 6 (the stage, last used on text rows 3-4 = pixel lines 31 / 39) and BG 7 (keg gone) plus 2, 3, 4,
  with BG 1 (the HUD, line 7) reloaded to the keg's colours. That is **three** mid-frame palette reloads per frame (BG 1 at about line 8-31,
  BG 5 at line 31-39, BG 6 at line 39), each in its own HBlank (8 bytes is about 48 M-cycles: one reload per HBlank is the limit, two do not
  fit), so a chain of three LYC interrupts, sharing LYC with the window's own line (banner / note), in the asm split with its C twin (perf guards
  at their limit), plus a keg / spout attribute change in every venue (venue art attribute 7 -> 1, gen_art.py abs_battr; the keg is the right
  3 columns of rows 5-16). The Space Lounge (7) and Stadium (7) need one more than that: their plans fold the keg into BG 0
  ("field_moves Keg 1 -> 0": BG 0's colours change) so BG 1 is free as well.
- None of that can be done inside ROM0's 440 B margin without measuring, and it touches the DMG-visible-never part of every venue's Color
  picture (every Color golden of the 9 venues' level screens would change where the keg colour moves; the split line's pixels).

### Options (owner / supervisor decision needed before Step 2)

A. **Build the BG restructure first**, as its own task: keg to BG 1 in all venues, the 3-reload split chain (asm + C twin), then the generic
   look/palette mechanism on top: 6 BG slots (Factory, Lodge, Bistro, Igloo, Chrome Cow, Teahouse; Zoo needs 5), the Stadium and Space Lounge
   with BG 0 / keg merged (7). Full plan honoured. Cost: 1 task for the split chain + keg move (ROM0, perf, all level goldens), then the
   mechanism.
B. **Build the generic mechanism now at 4 instances per venue** (BG 2, 3, 4, split 5; the Saloon's 5 with its BG 7), and shrink every plan to 4:
   the owner names which palettes each venue drops (for the Factory: 6 -> 4, e.g. CLANK/PEPPER on the mug's OBJ 1 and TELLY/BLIP's mint merge
   into others). The combo table generator already supports any subset (VARIANT_CUTS is the only per-pair knob; add a per-venue "instances kept"
   list in plan_data). Quick, no split work, but breaks "Robots keep all swaps".
C. **Mixed**: the generic mechanism for 4 now (B), the split chain later (A) extends the instance count only (the combo table and the
   per-venue tables grow; no engine change), so B then A loses nothing but the first round of palettes. Recommended if the owner wants extras soon.
D. A swap whose BG slot is missing could keep its OBJ palette but WALK in a neighbour's BG colours (the patron changes colour on lifting). Rejected:
   it breaks "same colours walking and lifted" and shows as a visible pop.

I stopped here on purpose: Step 2 would mean choosing among these for the owner.

## 2. How a venue's extra looks are stored (valid for every option)

- Per look 50 tiles in VRAM bank 1 (option 2: the shifted poses' empty third column shares the blank pair): 42 shifted (7 shifts x 6), 4 shift-0
  (8x16 OBJ pose: two 8x16 columns), 4 back view. Five extras = 250 tiles + the blank pair 2 = **252 of 256**; 4 tiles free. Eight looks per venue
  therefore fit exactly as in the Saloon: looks 0-2 in bank 0 (the DMG's three, unchanged), looks 3-7 in bank 1. No margin is left in bank 1 for
  late Color-only decorations; a trimmed right column (patron art keeps x=15 empty; each trimmed pixel column of a 16 px figure saves 2 tiles)
  or the 4 free tiles are the only reserve. The Factory's old enhanced-look tiles (bank 1 ids 210-211, enhance.c enh_b1) go away with the
  enhanced look and so must be gone before the layout is used there.
- The layout is the Saloon's exactly (render.c / mirror.c `pose`, game.h SALOON_X_*): look 3 + k shifted poses at ids 42 k + 6 (s - 1) (the last
  one apart), blank pair 210, shift-0 poses 212 + 4 k, back views 232 + 4 k. Rename the constants to `EXTRA_*` (same values): one layout for every venue, so
  lift_tile[], back_tile[], pose() and quick_mirror() stay venue-independent.
- ROM: one blob per venue of 5 x 800 B = 4 000 B in a data bank (the Saloon's `load_saloon_x` generalised to `load_extra_looks(g)`; blob generated by
  gen_art.py from `tools/artifacts/palette_plan/art/<venue>_<name>.txt` + `_back.txt`, in the plan's order: EXTRA_LOOKS[venue]). 9 venues = 36 KB:
  ROM_26 has 14.8 KB, banks 27-31 are free (80 KB), banks 1-25 are full (16-234 B free). Cost: 2-3 new banks, no change to bank 1-25.
  Backs that do not exist yet are stand-ins (name them in the commit; the Saloon had three).
- Art checks: names against NEW_PATRONS / EXTRA_LOOKS (renamed ones: NEKA, TELLY, TOOB; `art/robots_bubble*.txt`, `robots_telly*.txt`, `robots_toob*.txt`
  exist: the plan's TOOB is purple = the old BUBBLE concept, TELLY = mint; gen_art must map by plan name, not by file name guesswork). gen_art.py validates holes, order, right column, lifted columns.

## 3. The (look, palette) combo table: generated, never typed

`tools/dev/extra_combos.py` already derives, from plan_data.py alone, every venue's instances and each look's allowed OBJ slots
(NAMES + EXTRA_LOOKS; instances from PLANS moves / add / join; cuts from VARIANT_CUTS). Step 2 turns it into the generator:

- `tools/gen_art.py` (or a sibling `gen_looks.py` it calls) writes `build/looks.h` / `looks.c`: per venue g: `n_inst[g]`, `inst_obj[g][i]`, `inst_bg[g][i]`
  (the engine slot of each instance, chosen by the generator from the venue's free-slot list: option dependent), `combo_n[g]` and `combo[g][]` = the
  patron_variant bytes `V(look, inst)` of every allowed pair, in plan order, and `combo_boss[g][]` (the pairs that stay in a boss fight, section 5).
- Palettes: palettes.json gets one entry per instance (colours 1-3 from the plan: PLANS add / the venue's own); `patron_pal_ids` becomes N ids per venue
  (palettes.c is generated already; patron_pal_get(g, v) keeps its signature, v up to 7).
- The Saloon's `sal_combo[36]` / `sal_boss[21]` become the first rows of the generated table if cheap: `game_truth.py` parses `V(l, p)` out of src/mirror.c
  with a regex and would be repointed at the generated header (self_check keeps passing). If not cheap, the Saloon stays on its own path: say so.
- Uniform pick: `combo[r * N >> 8]`. N = 48 for the Factory is 32 + 16 (shifts only, as the Saloon's 36 = 32 + 4); a general N costs one 8x8 multiply
  (SDCC call, spawn frame only). The one random byte per spawn is unchanged (the DMG stream stays; Color's extra `next_rand()` is Color-only). Both
  tables are 1 B per combo: 48 + 40 B per venue in a banked bank (mirror.c is banked), nothing in ROM0.

## 4. How spawn / render / lift / mirror pick tiles and palettes per instance

The per-instance byte is already generic (patron_variant: bits 0-2 look, bits 3-5 `inst ^ look`, bit 6 PATRON_BANK1; 8 instances fit in 3 bits). What is
Saloon-only today and becomes per venue g (a handful of 5-8 B tables, set at the level load; all gated by `is_cgb`, the DMG never reads them):

| place | Saloon-only now | generic |
|---|---|---|
| mirror.c spawn_variant, show.c:78 | `is_cgb && !cur_group` -> saloon_variant | `is_cgb && extra_venue[g]` -> table pick |
| lift.c `lift_obj[5]`, lift_level_init `g ? 3 : 5` loop | OBJ slots of instances 0-4, loads 5 palettes only in the Saloon | `inst_obj[g][i]`, `n_inst[g]` palettes lifted (BRIGHT) |
| render.c `pal_bg[5]`, patron_attr | BG slots of instances | `inst_bg[g][i]`; the Space `XENO` special case folds into the table |
| level.c load_patron_group | loads BG 2-4, Saloon's BG 7 + load_saloon_x | loads the venue's BG patron palettes, `load_extra_looks(g)` |
| level.c start_level split_arm | Saloon only, BG 5 | any venue whose table says so (option A: up to 3 reloads) |
| render.c pal5_check / lift.c lift_pi4 / try_lift | the Saloon's instance on OBJ 5 (the show's slot) | generic: the instance whose OBJ slot is the show's (Factory: TOOB's OBJ 5, until the plan's "dancers on OBJ 0" is built) |
| mirror.c quick_mirror, render.c quick_entries | `PATRON_BANK1` look path | unchanged (venue independent) |
| lift.c lift_tile[], render.c back_tile[] | Saloon X ids | same ids per venue (layout is shared) |
| level.c swap_gus | Saloon GUS / Lodge ASH plane swap | per-look "swap planes" flag in the generated table (the Saloon's and ASH's today) |
| tip.c GUS always tips | Saloon | unchanged (GUS stays Saloon) |

The per-venue tables live in `story_scratch` region 0..69 (free in play per scratch.h; `tip2.h` uses SCR_TIP2_AT elsewhere): inst_obj + inst_bg = 16 B,
combo pointers not needed (far read from the bank at spawn). No new WRAM global. ROM0 estimate: +60-120 B (the table indirections in render.c
patron_attr, lift.c lift_level_init and draw_lifted's palette index; the asm draw_lifted reads `lift_obj` by index: the 5-byte table becomes a 8-byte one
at a pointer in story_scratch, +4-6 B in the asm and the same in the C twin). The 440 B margin survives; ROM0 margin after is to be measured and must stay >= 300 B (say so if not).

## 5. Boss fights: which looks sit out

A boss fight owns variant C's tiles (BOSS_BG_A / B regions) and reloads OBJ 7 (the topper) and some venues' OBJ 4 / OBJ 2 (Factory: OBJ 7 topper + OBJ 4
lamp; the Space and Stadium bosses own OBJ 2 / 7 per HANDOFF_art_import.md). So during a fight the pairs that use a boss-owned OBJ slot or the C look's
bank-0 tiles (look 2) are dropped from the pick (`combo_boss`, one draw, no rejection loop: tests/test_boss_in_place.py). Factory (to be confirmed against the boss's real palette use when built): BLIP (look 2) sits out and the instances on OBJ 7 (TELLY) and OBJ 4 (NEKA / BLIP) sit
out, so 7 looks x 4 instances (OBJ 1, 3, 5, 6) = 28 pairs. `combo_boss` is generated from a new per-venue `BOSS_OWN_OBJ` list in plan_data (the Saloon's sal_boss is its first row), not typed.

## 6. DMG

Unchanged by construction: every new path is behind `is_cgb`; the DMG keeps looks 0-2 and the legacy 3 palettes; tile bank 1 does not exist; spawn_variant's
DMG arithmetic and RNG stream are untouched. Test: the DMG goldens and the DMG patron tests stay byte-identical (no golden touched).

## 7. Costs and risks

- ROM0: +60-120 B (above); WRAM: +0 (story_scratch 0..69, 16 B); ROM banks: +2-3 data banks (36 KB for 9 venues, 4 KB each); VRAM bank 1: 252 / 256 tiles per venue.
- Perf: the guards are at their limit on the C ROM (`perf_arcade[10-dmg]`, `pause_card_fade`, `half_rate classic25`, see HANDOFF_batch2_steps.md). The generic path adds
  one indexed load per stamp (patron_attr) and per lift: Color-only, Color has headroom (no half-rate); measure `make cfall` + test_perf before / after.
  Option A adds three ISR entries per frame to the split chain: that is the part that needs the perf check first.
- asm twins: draw_lifted_asm (lift_obj read), split_isr / split_pal (ASM_SPLIT_PAL): keep the C versions built and tested (`make cfall`).
- Goldens: the Factory's Color level pictures change only where an extra / swapped patron appears (random spawns: tests pin spawns by poke; new goldens for a
  combo sheet); Option A changes every venue's keg colour attribute on Color (all level goldens, one by one, supervisor).
