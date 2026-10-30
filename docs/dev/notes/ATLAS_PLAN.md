# Keeping the Atlas current and correct (plan, 2026-10-29)

Owner: "You for real need to figure out how to keep the atlas up to date and correct. Please make a plan."

## What went wrong (2026-10-29 alone)
1. GUS showed unswapped in his own palette: a second art source (right-column trimmed fronts) overrode the swap,
   and the self-check compares lists, not pictures.
2. SALOON_LOOKS / SALOON_PRIMARY are hand copies of src/mirror.c: stale twice (self-check caught it, after the fact).
3. Owner-accepted proposals (FRANK, LOUIS, PIPER, POET, MUFFY) reached the plan art late: a manual copy step.
4. Publishing is five manual steps (make atlas, build.py, self-check, diff image refs, publish list); skipping one
   leaves a stale or partial page.
5. Art for one patron can come from four places (assets/, art/, patron_pass ACCEPTED, right_column TRIM) with
   ad-hoc precedence.

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

## Order
Steps 4 and 6 first (cheap, stop staleness now), then 1 and 5 (correctness), then 2 and 3 (cleanup).
One gb-worker, about a day; Color/DMG: page only, no game change.
