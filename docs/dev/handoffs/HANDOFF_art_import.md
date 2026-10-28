# Handoff: owner art import (2026-10-27)

Done: Stadium A/B/C and Lodge B/C (WILLOW, ASH) on DMG and Color. Fronts from docs/dev/concepts/*_owner/proposal*/ (the owner's pixels, unfixed
variants), backs from stadium proposal_v2 and lodge proposal. assets/art/patrons/{sports,sports_back,lumberjacks,lumberjacks_back}.txt,
assets/palettes.json (sports_a/b/c, lumberjacks_c). No code, no WRAM, ROM0 453 B free (asm) unchanged.

NOT done (stopped on purpose): the Color-only 4th looks (Space Lounge astronaut, Factory NEKA). The extra-look mechanism is Saloon-only
(cur_group == 0 in mirror.c spawn_variant / show.c, sal_combo and sal_boss tables, the V() byte with PATRON_BANK1, st_tab slots, the
bank-1 tile blob and pi 0-4 palette instances in lift.c / render.c pal5_check / SPLIT_PAL, tip.c). Generalising it to two more venues means:
per-venue combo tables and boss exclusions (Space and Factory bosses own OBJ 2/7), bank-1 tile blobs and loaders per venue, per-venue
palette instance loading (BG slot per instance), and Factory's still-built enhanced BOXY on OBJ 4. Palette pairs per the plan: Space Lounge uses
OBJ 1 (ZORP), OBJ 2 (XENO), OBJ 3/6 moved, so OBJ 3 or 6 is free on paper; Factory uses its own slots and BG is the binding limit: not checked slot by slot.
Options: (a) a contained generic "group extra look" (one look 3, one palette instance, bank 1) in a separate step, with its own review of ROM0;
(b) wait for batch 3 (tile lookup table) which reshapes the tile layout; (c) put the 4th looks on the DMG-shared bank-0 path as a Color palette swap.
