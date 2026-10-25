---
name: spigoteer-minigames
description: How to build, change and test a Spigoteer mini-game in the shared framework (src/mg.c, the mg union, per-game generators, story and Practice modes, medals, HARD, the Practice pictures), from an owner-approved proposal. Use it for any task that touches a mini-game, the MINI GAMES / Practice list, medals, mini-game art or tests, even if the brief only names one game (Quick Draw, Order Up!, Battery Sort, Milk Run, Taiko Pour and the rest).
---

# Spigoteer mini-games

The design of each game is its section in `docs/minigames_bosses.md`. The framework and every built game are
documented in `PLAN.md`: read "Mini-game framework as built" and the "<Game> as built" section of the newest similar
game (Milk Run, `src/mr.c` + `tools/gen_mr.py`, also shows a raster split and the OBP0 restore). Grep PLAN.md for
the headings; don't read it whole.

## The framework in brief
- `GS_MINI`: `main.c` calls the banked `mg_update(pressed)`. Each game is `xx_enter()` / `xx_update(pressed)` in its
  own file, dispatched by a switch on `mg_game` (no banked function pointers). Per-game tables in `mg.c`: name,
  instruction, `medal_at`.
- Phases: INTRO (banner) → COUNT (READY, GO) → PLAY (the game's update; timer on the HUD) → END (outro) → RESULT
  (window with score and medal).
- Modes: `MG_STORY`, `MG_PRACTICE`, and the `MG_HARD` flag. Practice starts the score from 0 and offers retry; in the
  story, mini-games never block progress.
- Medals: three thresholds per game on `mg_score` (`medal_at`). What a medal is worth (points, lives) has changed
  since the framework was built: the story-map rulings (2026-10-18) make each festival gold in the current story run
  +1 Pour-Off life (capped at +3) and add medal points at the end of the story. Check PLAN.md and the
  `story-map-decisions` memory before touching rewards.
- Helpers (banked, `mg.c`): `mg_points`, `mg_finish`, `mg_rand` (own xorshift; the bar's RNG untouched),
  `mg_spigoteer`, `mg_number`; `mg_say` (ROM0) for HUD-glyph text. `mg_seed_force` makes runs reproducible in tests.

## Rules for a new or changed game
- **State lives in the `mg` union** over `story_scratch` (static size assert). No new WRAM globals.
- **Code and art are banked.** New banks are fine (the ROM auto-sizes). ROM0 is tight: add nothing there unless
  unavoidable, and say why.
- **At most 10 sprites on any line, every frame.** Test it over whole bot runs and a forced worst case.
- Import the approved art pixel-exact. Proposal mock-ups came from a Python renderer, not the ROM: make the real game
  match the mock-up, and apply any spec changes or engine rules listed in the proposal's notes. Document them in
  PLAN.md "<Game> as built".
- Other agents may be building other games: touch shared files (`mg.c`, `mg_list.c`, `gen_story.py`, `PLAN.md`,
  `test_mg_list.py`) minimally so merges stay easy.

## Tests (pattern: `tests/test_mg_milkrun.py`)
Start, controls, scoring, win and lose, medals, Practice, HARD if the spec has it, and sprites per line. Add goldens
for the key screens on DMG and CGB after looking at them. The MINI GAMES list goldens will change: list them with
their bounding boxes (`tools/dev/golden_bbox.py`).

## Practice pictures
- One picture per game, dropped into `assets/art/practice/<game>.png`. The generator and streaming loader are on main
  (4b618dd). `make` writes `out/preview/practice_<game>_x4.png`.
- Keep each picture under 56 tiles.
- Show pictures in the real engine with a scratch build, not pasted onto an old screenshot:
  `make BUILD=out/b_real OUT=out/o_real PRACTICE_ART_DIRS=<folder>`.
- Art follows `gb-pixel-art` (`gb-artist`); proposals first.

## Deliver for the owner
Key screens as one contact sheet (CGB over DMG, x3) via `tools/dev/contact_sheet.py`, and a short gameplay GIF
(under about 2 MB) for the Review Board or Open Questions page.
