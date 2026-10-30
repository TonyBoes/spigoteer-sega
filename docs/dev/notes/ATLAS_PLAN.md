# Keeping the Atlas current and correct (plan, 2026-10-29)

Owner: "You for real need to figure out how to keep the atlas up to date and correct. Please make a plan."
Then: "Ok, but look at our past atlas failures too. This isn't the first mistake."

## Failure history (10-21 .. 10-29, 30 owner-visible failures; full table in out/atlas_failures.md)
| Cause | Count | Examples |
|---|---|---|
| Hand copy of game data drifted | 3 | boss hat in OBJ 7 (10-26), saloon colour coding (10-28), SALOON_LOOKS twice (10-29) |
| Stale capture / not republished | 4 | rebuilt on older main five times (10-26..27), browser cache |
| Art source precedence | 4 | backs with the old bottom outline, GLOP fish, GUS unswapped (10-29) |
| Accepted pick not copied into the plan | 3 | Palette Merges picks, 32 new patrons, FRANK..MUFFY |
| Missing patron or content | 4 | space/robot chapters, all new patrons, current backs, whole-level palettes |
| Plan slot vs game slot numbering | 3 | "BG1" read as the game's slot; renumbered BG slots clashing |
| Wrong palette claim | 3 | OBJ 5 "show dancers" (event-swapped), first-listed palette shown |
| Page shows game state, owner wants plan | 3 | "reflect my plan, not once it's dropped", planned tile counts |
| Rendering / phone layout | 2 | empty sprite column (img collapse), horizontal scroll at phone width |
| Information overload / unwanted stats | 4 | "TOO MUCH INFORMATION", tiles-used cards |
| Publish problems | 3 | live title reverted, delete needed two tries, 512-file limit |

Pattern: every failure is a manual step skipped or a second copy of a fact. Nothing checked the page as the owner sees it.

## The fix
1. **Game looks are drawn from the game.** For every look the game ships, the thumbnail comes from the atlas
   capture (the real VRAM tiles and palette RAM the emulator saw), not from text art. Swaps, palettes, recolours
   and engine tricks (GUS's plane swap) are then right by construction. Text art is used only for planned,
   not-yet-imported looks.
2. **No hand copies of game data.** SALOON_LOOKS and the per-look palette lists come from game_truth (sal_combo,
   palettes.json, render.c rules); the plan only holds decisions the game doesn't have yet.
3. **One art table for planned looks.** A single ART table (patron -> front file, back file, source Qn) replaces
   art/ + ACCEPTED + TRIM precedence. Answering an art Qn means: update that row, rebuild, publish, in the same commit.
4. **One command.** `make atlas-page`: rebuilds the capture only when src/ or assets/ changed since the capture's
   commit, runs build.py and the self-check, writes the publish list (changed/removed images), and refuses to
   finish on any self-check error. The page stamp shows the game commit and the plan commit.
5. **Picture-level self-check.** For each game look and palette: the page's thumbnail must equal the captured pixels.
   For each planned look: the art file must pass the patron rules (x=15, row 15, holes).
6. **Drift fails the tests.** A fast pytest runs the self-check (no emulator) so `make test` goes red when the plan
   contradicts the game, e.g. a spawn-table change without a plan update.
7. **Supervisor checklist** (spigoteer-review-pages skill): after any merge touching assets/, palettes or patron code,
   and after every art pick: `make atlas-page`, look at a contact sheet of the changed thumbnails, publish, commit.

Added after the failure review (gaps the first seven steps did not cover):

8. **Every pick has a row.** The self-check fails if a patron accepted in any `docs/dev/concepts/*/PICKS.md`, or an
   answered Qn about art or palettes, has no ART or PLANS row. PLANS entries carry their Qn.
9. **Plan first, labelled.** The page shows the planned state by default. Any number or swatch that shows the game
   as it is now carries a NOW label; the self-check refuses unlabelled ones.
10. **Both slot numbers.** Where the plan renumbers a slot, show "plan OBJ 5 / game OBJ 6". The self-check fails
    on two looks sharing a plan slot in one venue.
11. **Check the page as the owner sees it.** A headless render of index.html at 360 px: no horizontal scroll, every
    image has a real width. Before publishing, read the live page and keep its title; check the file count limit.
12. **Event-swapped palettes.** The capture records palettes that game events reload; the page labels them per event.
13. **Verify deletes and renames** with a page `list` afterwards.
14. **Page rules list** in tools/artifacts/README.md (bare labels, free tiles only, summary first, no extra stats),
    checked by eye on the contact sheet before each publish.

## Order
Steps 4, 6 and 8 first (cheap, stop staleness and missed picks now), then 1, 5 and 11 (correctness of the
pictures), then 9, 10, 12 (plan vs game clarity), then 2, 3, 13, 14 (cleanup).
One gb-worker, one to two days; Color/DMG: page only, no game change.
