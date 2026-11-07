# Story map import round (2026-11-07)

Owner approved every piece below (QUEUE.md 11-06/11-07). Implement as written; do not redesign. Stop at the end of
each stage and report to the supervisor; do not start the next stage until told.

## Approved pieces and where they live

| Piece | Branch (tip) | Notes |
|---|---|---|
| A5 layout, single logs v1, waterfall seam fix, bridges with raised sides | worktree-agent-a9eca06ceee777aa2 | SMAP_LOG=v1, SMAP_BRIDGE default (new) |
| Animations + their static art (very subtle water, falls with churning foam lip, pond glints (arcs removed), 6 logs half-submerged with bob, airbase dish+lamp, bunting, stadium flag, lodge/factory/igloo smoke, cow tails, fountain streams) | worktree-agent-a3023453466f37744 (dc5c1781) | docs/dev/proposals/smap_anim/ (items.py, NOTES.md). Stadium lamps dropped. |
| Milk bar: sign B, raised + 4 px left, building body on `base`, tea cell (34,59) on tea@g | worktree-agent-a742552fa3a9454c1 (tip, sheet14) | lot sits on the road: generator venue-over-road assert needs a lot exemption; lot walkable |
| Stadium: final 2 + wavy flag, BLEND onto the map (sheet2) | worktree-agent-ad92c4ce81f826634 at 8950c018 | use BLEND (8950c018), NOT the PLAZA commit a2bbbc76 after it. PARK needs a 19th palette-table entry: re-lay story_scratch per smap_priv.h:24-29 (agent's NOTES.md) |
| Fountain round 3: centred, two side streams, dry tap, low lilac wall, broken + working states | worktree-agent-a9bde35169ec4c32e (8608d684, includes ceeafd0a + awning ink border) | broken for most of the game, working after the repair (story progress) |
| Airbase 4i, jet nudged right | worktree-agent-a958d884767ee8afe (e898c707, nudge included) | |
| Igloo option 1 (COCOA sign, chimney, penguin) | worktree-agent-a326fa4ec4c6f3e7f | |

## Stage 1: one integrated proposal (no engine changes)

1. New branch from main (ff-merge main first). Merge the branches above `--no-ff`, resolving conflicts toward the
   approved state of each piece. Where two branches change the same cell, the table's later row does NOT win by
   default: check which piece owns the cell.
2. Render the whole map (DMG dark water, DMG light water, Color) and a close-up x3 of every piece above next to its
   approved sheet. Contact sheet, big bold labels, at most 2 columns, at least 1000 px wide.
3. Report: whole-map DMG tiles, worst 21x19 / 22x20 view (limit 176), palettes per window (8 max, 0 over), table
   entries (19 with PARK), animation images and tile ids, DMG VBlank peak per view. List every cell where the merge
   had to choose.

## Stage 2 (after review): engine import

Taller-map engine constants; the 19th palette entry (story_scratch re-lay, no new WRAM global); map data from the
generator into assets; milk bar lot exemption; fountain state by story progress; level order saloon, stadium, bistro,
igloo, lodge, factory, cow, tea, zoo, space (chapter numbers/titles, unlocks, stops, save mapping, tests; check
difficulty and music per chapter and ASK before any music change). Goldens: new ones freely; list changed ones with
bbox, supervisor replaces.

## Stage 3 (after review): map tile animation

Engine table (tile id, frame list, period, phase) rewriting BG tiles in VBlank while Sal walks. Measure DMG first
(the walk is already tight: see QUEUE 11-05/11-06 map speed notes); never raise a perf guard. Color can use GDMA.

## Rules

CLAUDE.md project rules. Report WRAM_LO / WRAM_HI_0 and romusage before and after; ROM0 has ~745 B free, keep it.
DMG and Color: say which. `make test` + `make check` green on DMG and CGB at stages 2 and 3.
