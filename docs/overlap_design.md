# Overlapping patrons (M13): design

Owner decision (2026-10-09): patrons must overlap as in arcade Tapper. Pushed patrons slide back through
others; walkers move at different speeds and pass one another. One patron shoving another is not acceptable.
The design comes from a measurement spike on HEAD 9548d80. Probe scripts are in the session scratchpad (overlap/).

## Approach: hybrid "lift"
Patrons stay BG tiles while alone. When two would share a tile column, one is lifted to OBJ (16x16 = two 8x16
entries) until clear, then dropped back to BG.

## Measured facts
- **Bar geometry.** Bar b's top line is T = 40 + 24b. Patrons occupy T..T+15 and the counter T+16..T+23.
- **Objects that reach into the next bar.** The bartender's bottom pair covers lines 0-7 of the bar below
  (the patrons' heads). A breaking glass covers lines 0-2 of the bar below.
- **Worst sprite count per line, level-8 script:** 5 (bartender 2, coin, fill, puff). Total OAM peak 8.
- **Worst sprite count per line, worst-case pile:** already 11 on bar 0 today. The rules allow bartender 2 +
  fill + 6 mugs + coin + puff = 11.
- **Lift budget.** Measured play leaves room for 2 lifted patrons per bar. Cap 2 per bar, plus a per-frame
  load check: allow a lift if load + 2 <= 10, force a drop if the load goes over. Mugs never lose entries.
- **OAM.** Today: bartender 0-3, fill 4, mugs 5-25, puff 26, coin 27, dancers 28-39. Mugs count up from 5,
  lifted patrons down from 25, at most 4 lifted (8 entries). Refuse a lift if mug entries + 2(L+1) > 21.
- **Perf baseline.** Level 8: logic peak LY 71 (DMG) / 75 (CGB), end LY 93, 0 missed frames.
  - A lift or drop is one 3-column span, about 13-17 lines on that frame, capped by VQ_BUDGET.
  - A lifted patron costs about 1 line per frame and makes no BG redraws, so a lifted slide is cheaper than
    the BG slide is today.

## Tiles (Option A)
- **Current layout.** Patron BG tiles are ids 77-232 in the signed map. 77-127 sit at 0x9000, which OBJ
  cannot address. They are stored row by row.
- **Reorder.** Store each group column by column from an even base (78). Put the three shift-0 poses last
  (ids 204-221: >= 128, even). A lifted patron then draws 8x16 tiles t and t+2 directly from the BG copy.
  - Only shift 0 is needed as OBJ, because OAM X gives every pixel position and the sway.
  - Lifted patrons never use back views (a lifted patron is not distracted by the show).
- **Code to update.** render.c `stamp3`, `put_col`, `id_seq` / `stamp_tile`, and title.c's patron copy at
  TT_PATRON_BASE.
- **Free ids.** Ids 240-251 stay free for the DMG copies below.

## Palettes
- **CGB (owner: do both, to keep a spare).**
  - The tip coin moves into slot 5 and shares it with the show. They are never on screen together: one
    palette write in VBlank when a tip appears or a show starts.
  - Glass and puff use the venue's empty-drink palette (slot 2), freeing slot 3.
  - Patron variants then use OBJ palettes 3, 6 and 7, with slot 4 spare.
  - Colours 1-3 copy the BG patron palette; colour 0 is transparent.
- **DMG (owner: accept the shard swap).**
  - OBP1 = 0xE4 for patrons.
  - Today's OBP1 users move to OBP0 with byte-swapped tile copies made at level load. These are the sliding
    mug (4), the held empty (2) and the puff (6): 12 tiles at ids 240-251.
  - Glass shards (16 tiles) don't fit, so they show light and white swapped on DMG. Accepted.

## Rules

> **Update 2026-10-17:** the lift, drop and collision rules below stand. The *push* rule they assume (full push-back x drinks, served when carried out through the
> door) was replaced on 2026-10-13 by a fixed push per mug (32 px, 24 on the two hardest rows) and on 2026-10-16 by **Option C**: a push that reaches the
> left-edge stop serves the patron, who keeps sliding off and counts when off the screen (every mode, CLASSIC included; PLAN.md "Patron clearing, Option C").
> Perf: the crowd path (`draw_held`, patron steps, lift loops) is the one place that still runs late frames; its assembly pass is the last open perf item.
- **Collision.** Columns overlap when |c1 - c2| < width, where c = draw >> 3 and width is 2 at shift 0,
  else 3.
- **Choosing who lifts.** The lifted set makes the remaining BG patrons column-disjoint (greedy, left to
  right). Priority: pushed, faster walker, walker, emerging, drinker. Never lift a distracted or back-view
  patron.
- **Drop.** He shares no column with a BG patron (sharing with another lifted one is fine), x >= DOOR_X, and
  8 clear frames have passed (hysteresis).
  - On drop, queue the BG stamp first and keep the sprite one more frame.
  - On lift, show the sprite at once, then erase the BG copy.
  - Wait while vq_held.
- **Pushed patrons.** They slide through anyone and stop only at the door (served). A push that ends on top of
  someone: he drinks lifted and drops when clear.
- **Walkers.** They pass slower walkers and drinkers freely. A walker waits only if a step would put three
  patrons in one tile column.
- **Speeds (owner: occasional fast patron).**
  - Most walkers move at the level speed.
  - From level 3, about 1 in 4 spawns is "hurried" at ~1.5x, so passing is visible within seconds.
  - Retune the level table so difficulty stays about where it is.
- **Catching.** Unchanged: the rightmost catcher whose 16 px contain the mug catches it. Empties start at
  x + 16.
- **Drawing order.** A lifted patron is always in front of BG patrons.
  - On DMG the lower X wins, so a lifted holder would hide his own mug: use dx 8 for the carry and throw
    poses, and dx 16 for the last throw pose.
- **Budget exhausted.** The pair stays in BG, the would-be lifted patron is drawn last (covers the other), and
  quick redraws are off for shared columns.
- **Tests whose expected behaviour changes:** test_patrons.py around lines 162, 174 and 270 (waiting
  behind), test_tips.py 331 and 342 (the show shuffle), test_door.py 48 and 59 (the spawn point, in M13c).

## Door entrance (M13c; superseded 2026-10-09: no doors, see PLAN.md "No doors as built")
- **Spawn.** At x = 0 (OAM X 8), lifted with the OAM priority bit: hidden behind door colours 1-3, shown over
  colour 0.
  - Needs LCDC bit 0 = 1, and the door's BG attributes must have bit 7 clear (check the generated ones).
- **Emerging.** Emerge speed is 64/256 px per frame. He drops to BG at x >= 16 when clear. No puff on entry.
  - Door-to-tap time from x = 16 is unchanged.
  - The spawn check becomes blocked_behind(b, SPAWN_X + PATRON_SPACING).
  - He may catch a mug while emerging.
- **Serve-out.** Hide the sprite before the puff starts. On DMG a hidden lower-X sprite still blanks the puff
  and shards.
- **Igloo.** Its door has 82 colour-0 pixels (snow, rows 0-3). Owner: redraw the igloo door so it is solid
  and show it to the owner.

## Milestones
- **M13a: plumbing, no rule changes.**
  - Contents: the tile reorder, palettes as above, the patron_lift[16] / lift_n[4] state, BG composition
    skipping lifted patrons, draw_lifted() from OAM 25 down, the draw_mugs limit, the load estimate, and a
    test hook to force a lift.
  - Tests:
    - Lifted equals BG pixel for pixel for all 27 group/variant combinations, at rest and swaying, on DMG
      and CGB.
    - Zero changed pixels across every frame of a lift and of a drop.
    - All existing goldens unchanged, except the accepted DMG shard swap and the glass/puff palette change
      (listed individually).
    - Mugs never lose OAM entries.
    - The 10-per-line forced drop works.
    - test_perf unchanged.
- **M13b: rules.**
  - Contents: speeds and hurried patrons, sliding through, passing, the lift chooser, the BG fallback, the
    DMG mug dx clamp.
  - Tests:
    - A pushed patron slides through a walker and both stay visible.
    - A hurried walker passes a slower one.
    - A clump in front of the bar no longer stalls: every caught mug moves the catcher back.
    - The three-patron fallback.
    - Catch order, and empties from an overlapped drinker.
    - The tests listed under Rules rewritten.
    - A level-9 overlap perf scenario: 0 missed frames, end LY <= 118, <= 10 per line, <= 40 entries.
- **M13c: door entrance,** with the igloo door redraw. Tests: door tiles never change, the visible part grows
  with x, BG by x >= 16, door-to-tap time unchanged, catch while emerging, 10 per line at the door.
