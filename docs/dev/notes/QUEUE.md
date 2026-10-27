# Queue (max 3 agents, Sonnet unless the owner names a model). Updated 2026-10-20 03:05.

MAIN at 9a17af9 has: the owner's 14 portraits; the wooly cap (text + finale picture); the credits backdrop by shade; the marimba perfect-pour sound with the streak (x2 bonus from the 3rd); pocketed tips (B); the Mothership VBlank palette fix; the asm catch scans; the boss icons; map START menu; Dregs line; asm draw_held/update_mugs.

OPEN QUESTIONS TO THE OWNER:
- Sal: investigate a second CGB sprite palette (top/bottom split)? (asked)

OWED / LATER:
- PATRON HOLD LIFTED 2026-10-26: "Let's just go ahead and implement what patron changes we have so far so we can get everything current."
  - Batch 1 MERGED a60033f (with dmg-mixed-b).
  - Batch 2 RUNNING 2026-10-26 (agent ae175bbfbeda4049c, branch patron-rev-2): Saloon 8 looks (option 2, variants, GUS in the C slot), renames,
    drop the enhanced looks. Saloon backs: drafts in docs/dev/concepts/{dusty_hank,rosie,outlaw}_sprite; EMMA, ARTIE, GUS have none (stand-ins, listed).
- Patron design pass: CLOSED for agents 2026-10-26. Picks from rounds 1-2 recorded; the rest stay old and the owner edits them by hand. Brief and list: docs/dev/queue_briefs/patron_pass_2026-10-25.md.
- Medal-points value proposal (Q59e).
- Map critique round after his playtest (left lane, parallel town legs, cow, lodge, menu text spacing incl. Dregs's 20-wide lines, arrow direction).
- Palette audit leftovers: boss.c ld_step CGB palette stream mid-frame; smap_pal_back and dgag pats not verified with the LCD off.
- Lift glitch: documented as an xfail; not fixed (needs a VBlank-priority rework).
- Arcade speed: stopped at ~20% late at 10 patrons (owner may revisit caps).
- Coin and lights pal5_req: a coin in the same frame as the Mothership lights would be dropped. No coins in that fight, but it is an unstated assumption.

NEXT AFTER THE SAL IMPORT MERGES (owner approved 2026-10-20):
- Match Sal's other art to the owner's new sprite (sal_pack_owner/): Lift Rush (assets/art/logroll/spigoteer.txt, 24x24), Quick Draw (assets/art/quickdraw/spig.txt), CLASSIC antics (assets/art/antics/antics.txt, the 4 poses' non-copied rows).
- Use the gb-pixel-art skill. Previews first, plus editable PNGs; the owner approves before the build.

## Agent queue (2026-10-21; start each as a slot frees, ~3 agents at once)
Running: double speed (real, for main) | scratch-memory audit | 6-looks prototype ROMs (shared vs own colours)
Queued, in order:
1. DMG half-rate (30 fps) mode, logic twice / draw once, AUTO per level + debug toggle. Brief: queue_briefs/half_rate_dmg.md
2. 120 Hz music tick side-by-side recordings (owner Q10). Brief: queue_briefs/music_120hz_demo.md
3. Outlaw clean-up (the ORIGINAL round-1 outlaw; clean-up, NOT a redraw). Brief: queue_briefs/outlaw_cleanup.md
4. DX badge under the logo's right end (art via the skill's briefs.md template, one asset; code: 3 OBJ, CGB only)
5. Counter-lip "in front of sprites" example (owner wants to SEE it first; mock-up ROM + screenshots)
6. Sound meters in the soundtrack player (CGB PCM12/34)
7. GBA brighter palettes as a selectable menu option
Saloon potentials saved (saloon_patrons/potentials): prospector 1 and 2, singer, rancher, the ORIGINAL round-1 outlaw. Not imported.
Waiting on owner: Q9 fairness (likely settled by half-rate)

- 2026-10-21 Q10: the music stays at 60 Hz (owner). The music120-demo branch is shelved, not merged.
- 2026-10-21: Q21/Q22 keep the ORIGINAL outlaw (no clean-up, no proposals). Q23: drop the counter lip. Q28: BRIGHT curve approved, plus a first-boot GBA prompt (queued). Q29: a logo-size DX in the logo's font (agent running). Q27: owner needs it animated, so it went on the Review Board.
Queued next: GBA first-boot screen prompt (brief: queue_briefs/gba_first_boot.md), built on the GBA bright branch after the test-robust fix.

Queued next (top): browser emulator artifact (brief: queue_briefs/browser_emulator.md). Then republish it after merges, like the atlas.
- 2026-10-21 answers:
  - Q25: the DX stamps on after the last drip, with a thunk + sparkle SFX (agent picks from DON/COIN/PERFECT combos).
  - Q26: a GBA shows the DX.
  - Q32: option D (fill + foam cycle), 2 px more top margin.
  - Q33: one-line menu mock-ups for the soundtrack, practice list and boss rush. ILLUSTRATIONS QUEUED FOR AFTER SATURDAY 2026-10-24 (owner's tokens reset).
  - Q34: the label is "GBA COLOR MODE", the options "STANDARD" / "ORIGINAL GBA", with no caption line.

Queued next: the atlas shows everything a level can use (all events). Brief: queue_briefs/atlas_everything_in_level.md
- 2026-10-21 Q38-Q42 (one-line menus):
  - The selection line must stand out; trim redundant info; channel icons and stacked, gap-free visualiser bars.
  - Difficulty on SELECT is fine.
  - Soundtrack: A plays; A on the playing tune stops it; B always exits; moving does not play.
  - DMG visualiser via a driver hook only if cheap.
  - Boss Rush keeps the fight sprites, visually centred.
  - Mock-up round 2 is running.
- 2026-10-21 Q44: style A chosen. The practice screen drops its instructions; the art gets the space; the medal icon is stacked above its text (round 3 running).
- 2026-10-21 Q43: the DX look is approved (logo style, effect D, flash). Only the stamp sound is still being reworked.
- 2026-10-21 Q45: build the one-line menus for real now (agent running); the practice art comes after Saturday.

## Drop the enhanced patron looks (owner 2026-10-21) — AFTER the next patron revision
Owner: "I want to drop enhanced palettes after this next revision [for patrons]. It doesn't give me enough to be worth the trouble it causes."
Remove M14a enhanced variants: src/enhance.c, the row palettes (render.c pat_row/back_row), lift_prop per-column attributes, OBJ 4 (OBJPAL_ENH) load,
CGB VRAM bank-1 re-indexed lift tiles, tools/gen_art.py enhanced_group + validator, '@rows' notes in assets/art/patrons/cowboys.txt and robots.txt.
ROSIE (Saloon B) and BOXY (Robot Factory A) go back to one BG + one OBJ palette each. Frees OBJ 4 in all 10 venues; BG 7 back to keg/spout only.
Check: Prototype boss lamp uses OBJ 4 (OBJPAL_ENH) for red — keep that slot loaded for the boss. Goldens: Saloon/Robot CGB screens with those patrons.
Then: palette plan page DROP_ENHANCED -> done (remove the strike-through), make atlas, republish.

## Saloon patron renames (owner 2026-10-21), for the patron import
- Patron B ROSIE becomes MABEL (new art: grey hair, black lace shawl). The ROSIE name moves to the red-dress singer (OBJ 4).
- Update tools/gen_credits.py PATRONS and any story text that names ROSIE.
- Owner 2026-10-21: MABEL's back view (Claude's lace-shawl proposal) needs a major quality pass with the gb-pixel-art skill before submission.
- ARTIE (owner set 2 C) joins the Saloon, sharing MABEL's palette (OBJ 6 / BG 6).
- Saloon credits (when imported): add REDD (the outlaw), EMMA (the brown-haired singer), GUS (the prospector), ARTIE (the priest); MABEL and ARTIE are also new names, and ROSIE moves to the singer.

## Saloon 8 patron looks, BUILD on Sunday 2026-10-25 or later (owner: after his tokens reset)
Q51: the owner will "probably" pick OPTION 2. The unshifted front pose's empty 3rd column points at the shared blank tile, saving 2 tiles per look (10 over looks D-H). That turns the exact bank-1 fit into about 10 spare. Confirm with him before building.
Fit-check findings (agent report 2026-10-22):
- Tiles: 52 tiles per look. A-C stay in bank 0; D-H go in bank 1, with one back view at bank-0 ids 242-245.
- Big Tex still overwrites look C's tiles, so HANK sits out the fight. 7 of 8 looks are available there.
- ROM0: do NOT grow id_seq (+240 B). Route the L-bar quick redraw through the shadow rows (mirror.c quick_mirror pattern) and measure its speed.
- lift.c draw_lifted_asm: change and #3 to and #7, and use 8-entry tables. It has no C twin, so add one (asm-pass-keep-c rule).
- Spawn: CGB-only rand & 7 from the same next_rand() call (DMG stream unchanged). A per-venue look-count table.
- The DMG is untouched (3 looks).
Inputs: the Palette Plan (tools/artifacts/palette_plan/build.py, PLANS["cowboys"]) and the art in scratchpad saloon_patrons/potentials, dusty_hank_sprite, rosie_sprite, outlaw_sprite.
Back views still to draw: DUSTY, HANK, MABEL (placeholder), ROSIE, EMMA, ARTIE, REDD (recoloured).
- Owner 2026-10-22 decisions for the Sunday build:
  - Do the option-2 rewrite: the shared blank column for shift 0. It is no longer "probably".
  - GUS, the prospector (the OBJ 7 patron) takes the look-C tile slot, which the boss body overwrites. He sits out boss fights. HANK leaves that slot after the update, so 7 looks stay in the fight.
  - Expected spare, CGB Saloon, 16-px art (estimate):
    - normal play: bank 0 about 23, bank 1 6;
    - Big Tex fight: bank 0 about 6, bank 1 6.
    - With 15-px art: bank 1 16, bank 0 about 29.
  - Measure all of these in the build.
- Owner 2026-10-22: Saloon palette VARIANTS, i.e. recolours of the same tiles chosen per patron at spawn. The allowed OBJ (and matching BG) slots are in PLANS["cowboys"]["variants"] in build.py.
  - 30 combinations; GUS spawns in OBJ 5 and 7 only (his OBJ 3, 4 and 6 variants are cut). 29 combinations.
  - Needs HANK's art and OBJ 3 with colours 1 and 2 swapped (done in palette_plan/art/cowboys_hank.txt).
  - Code: a per-patron-instance palette (lift OBJ attribute and BG row attributes), not per look.
  - Reference grid: tools/artifacts/palette_plan/saloon_variants_grid.png.
- Owner 2026-10-22: KEEP MARGIN for late decorations, most likely DX/Color-only. Optional margin steps for the Sunday build:
  - Move the story perfect-pour sprites (OBJ_POUR 234-239) and the dust puff (OBJ_DUST 234/246) out of the shared block.
    - CGB: to bank 1's empty sprite-only block (OAM bit 3).
    - DMG: to bank-0 sprite-only tiles 40-55 (16 free).
    - That frees 12 shared-block tiles in bank 0, which can hold 3 back views of the new looks, taking the bank-1 margin from 6 to about 18.
  - Boss sprite parts: the atlas says every boss's sprite tiles are already sprite-only (6-10 tiles each). Their shared-block tiles (234-255) are body BG tiles and cannot move. Nothing to gain there.
  - 15-px-wide new looks would add 10 more.
- Owner 2026-10-26, Q62: DMG mixed-direction levels switch to mirror.c option (b): 1 px steps, A and B on L bars, C on R bars (branch dmg-mixed-b). Q61: option A MERGED 0943d35 (pour 40-45, dust 46-51; shared 234-239, 246-251 free; Sal pairs not shared, ROM cost); B waits for the patron revision.
- Owner 2026-10-26, Q63: "the 45 degree tilt is enough. But looks good." Side frame dropped (5d95c4b), goldens replaced. MERGED a60033f: patron-rev-1 (batch 1) + dmg-mixed-b. boss-mug-tilt waits: C-build perf guard [9-cgb] 6 late/356; agent aaa34daeb5d66de8b making hand_draw cheaper. Then batch 2.
- Owner 2026-10-22, DMG: the DMG keeps the original palettes (they all collapse to shades anyway). For the Saloon, the DMG three are DUSTY, EMMA and GUS (EMMA replaced ROSIE: her see-through pupils looked possessed on DMG).
  - These are the bank-0 looks on BOTH systems (one layout). GUS takes the slot the boss overwrites, so he sits out boss fights on both.
  - HANK goes to bank 1 and is Color only.
  - Variants and new looks are Color only.
  - Check the DMG renders: HANK's colour-slot swap doesn't matter on DMG, since he isn't on DMG.

## Credits remake: DEFERRED (owner 2026-10-22)
- Do not touch the credits until EVERY patron is in, the boss graphics changes are done, and the owner confirms both are LOCKED.
- When the credits are remade:
  - Patrons appear in their own (original) palettes, as listed in the Palette Plan, not in variant recolours.
  - The names follow the plan (Saloon: DUSTY, HANK, ROSIE the singer, REDD, EMMA, MABEL, ARTIE, GUS).
  - tools/gen_credits.py PATRONS and the credits' patron band change with it.
- The earlier "Saloon credits (when imported)" notes in this queue belong to this deferred task.
- Owner 2026-10-22: GUS ALWAYS TIPS, in ARCADE and STORY only; CLASSIC is unchanged. (He is "the rarest patron"; a prospector with gold.)
  - In src/patrons.c maybe_tip, skip the tip_chance roll for GUS. Ideally draw no random number either, to keep the other patrons' sequences stable. Check whether goldens move.
- Owner 2026-10-25: AT MOST TWO TIPS AT ONCE (was one). "We should probably make it the rule that there can only be two tips at a time no more than that."
  - Build with the patron revision (the coin moves to OBJ 0 with Sal, so the show no longer blocks it). A second coin slot; its state goes in an existing union, no new WRAM global.
  - GUS's always-tip then only misses when two coins are already out.
  - The existing limits still apply (one tip on the counter at a time, none during the show). The proposed default is A: if a coin is already there, he simply doesn't tip that time. B (wait until clear) and C (replace the coin) are alternatives; the owner hasn't answered.
  - Rarity (owner 2026-10-22): NO extra weighting. On Color, spawns pick uniformly among the allowed (look, palette) combinations, so GUS (2 of 29) is naturally rare. On DMG, 3 equal looks.

## 2026-10-24 (the owner's tokens reset): "Hold off on patron changes still, but resume other things we're holding on."
- 2026-10-25 Q52 answered: the 3 Practice pictures' style is approved ("these all look great"). The teapot in Taiko Pour needs work, and so does the in-game
  pouring teapot (assets/art/taiko/teapot.txt frames 1-2 read as a round blob; the level frame 0 stays as is). Own 1-tile frame assumed (not answered).
- RUNNING: teapot tilt/pour redraw proposals (2 options; scratchpad teapot/proposals/). Then the Taiko picture uses the new pour frame.
- RUNNING: Practice pictures set 1 (shirtcannon, logroll, orderup, marshmallows, batterysort + Milk Run quality pass) and set 2 (monkeybusiness,
  asteroids, shakeup, perfectpour, tipshower); scratchpad practice_art/set1, set2.
- MERGED 2026-10-24 (4b618dd): the Practice art generator + streaming loader (assets/art/practice/<game>.png drops in).
- STILL HELD: all patron work (the Saloon 8 looks build, renames, enhanced removal, back views), and the credits (deferred until locked).
- 2026-10-25 MERGED (95f3705): SETTINGS v5 + every title menu one row down (Q49); teapot B (Q53, stream 107/122); all 13 Practice pictures (Q54) with
  .txt sources; the list turns the LCD on just after a music tick (the picture load had moved the phase). Pocket Player main refreshed, settings ROM retired.
- WAITING ON THE OWNER: Big Tex on DUSTY/EMMA's palette? (GUS's tip: answered 2026-10-25, two tips at once, see the Saloon section.)
- ON HOLD (owner 2026-10-25): Boss Rush busts (64x40). "I don't want to do any boss rush busts until I finish the patron planning. I will look at the boss graphics then."
- Owner 2026-10-25: PALETTE MERGES for the other 8 venues, all 7 recommended + both optional (Palette Merges page,
  tools/artifacts/palette_merges/build.py MERGES; now in the Palette Plan PLANS + LOG). Color only; DMG unchanged.
  Part of the patron revision (still held): Bistro PIERRE/BRIE/waiter -> Sal's OBJ 0; Teahouse drummer -> SAKURA OBJ 6;
  Chrome Cow band -> BANDIT OBJ 6; Lodge Sasquatch -> full mug OBJ 1, WILLOW -> CEDAR OBJ 3; Zoo COCO -> OBJ 1;
  Space ZORP -> OBJ 1, XENO -> OBJ 2 (check the Space boss's OBJ 2); Igloo penguin -> Sal's OBJ 0.
