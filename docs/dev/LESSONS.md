# Lessons and tools from Spigoteer

A running record of what worked, what didn't, and the tools built along the way. It's written to carry over to the next Game
Boy project. Kept up to date during development; the newest items are added under the right heading.

## Working together (owner + Claude + agents)

- **One supervisor, several worker agents.** The supervisor briefs agents that work in git worktrees, then verifies, merges
  and replaces goldens itself. Agents never replace goldens; they list them with the bounding box of the change.
- **Default agents to the cheaper model, about 3 at a time.** Use the strongest model only by exception (music builds,
  hard engine work). This saves the owner's tokens.
- **Agents take reversible git actions only.** New commits and branches; no amend, rebase or reset. On a permission
  denial they stop and report; they never work around it.
- **Before relaying a layout request, draw the whole screen as a text mock-up and check it.** Three misreads came from
  "per item" vs "whole screen" ambiguity (the boss indicator, the two-row SETTINGS).
- **Number only real questions (Qn), and batch them.** Put the picture or sound right next to each question, so the owner
  never has to search the chat.
- **Show, don't describe.** For any visual choice, send mock-ups. Render them in the real scene (on the venue wall, at the
  bar, at 1x) as well as enlarged. The owner can't see GIFs animate in chat, so put animations in a page.
- **Bare labels on review pages.** No explanatory parentheses or captions inside stat boxes or names; explanations go
  in chat or behind a toggle. Summary first, detail on demand.
- **Palette names follow the plan.** Once a planning page exists, "BG1" or "OBJ 2" means the slot as the plan shows it.
- **Art always gets another quality pass** unless the owner says it is locked. A pass is not a redraw: never redesign
  something the owner said they liked. Ask how the owner reads a figure before touching it.
- **For every feature request, say whether it fits the DMG too or only Color**, and which budget it uses.
- **The owner tests judgement only** (look, sound, feel). Verify mechanics ourselves before asking.
- **Subagents may not be able to load a skill by name** ("Unknown skill"). Give the skill's path in the brief, so they
  can read SKILL.md and its references directly.

## Verification

- **Done means:** `make -B`, `make cfall` (the C reference build), the full pytest suite on both models, `make check`
  (SameBoy, DMG + CGB), the slow tests (`RUN_SLOW=1`), and the suite again on the C build (`GB_ROM=build/game-c.gb`).
- **Replace goldens one by one, only after checking each diff's bounding box** against the intended change. Never
  regenerate all of them. Name each replaced golden, and the reason, in the commit message.
- **PyBoy is for driving and asserting; SameBoy is the timing truth.** PyBoy zeroes RAM that real hardware leaves as
  junk, so clear hand-placed bytes in main() and test with a junk poke.
- **PyBoy audio:** slice the sound buffer to `raw_buffer_head // 2` each frame, or recordings crackle.
- **Waiting on processes:** `pgrep -f` matches its own loop. Wait on a PID or a log line. Finished agents can leave CPU
  hogs behind, so check `ps` after agent batches.
- **Fragile tests:** assert on driver or game state (variables by name) rather than on audio FFTs or exact frame
  timing, and feed input by game step rather than by frame.
- **Checking a layout-shift golden:** compare the new picture with the old golden moved by the intended offset. What is
  left over should be only animated sprites (sparkles, the logo drip). It turned 24 goldens into a two-minute check.
- **Show art in the real engine, not pasted into a screenshot.** Agents' pastes went onto stale list layouts twice. A
  build flag that points the generator at a scratch folder (`make BUILD=out/b_real PRACTICE_ART_DIRS=...`) gives true
  screenshots without touching assets/.

## Game Boy / Game Boy Color techniques that paid off

- **Patrons as background tiles, lifted to sprites only when they overlap.** Background patrons cost no sprites. Each
  patron look stores 8 pre-shifted copies of its front pose (3x2 tiles each, 48 tiles) plus a 4-tile back view, so it
  moves pixel by pixel on a tile grid. Lifting uses the unshifted copy as two 8x16 sprites.
- **Tile budget per patron look:** 52 tiles; 50 if the unshifted copy's empty third column shares one blank tile
  ("option 2"). Every pixel column trimmed from a 16-px figure saves 2 more.
- **VRAM blocks:** tiles 0-127 are sprite-only, 128-255 are shared, 256-383 are background-only. Count the background
  budget (256) separately from the sprite-only block. On CGB, bank 1's sprite-only block is a free 128-tile pool for
  sprite features.
- **Palettes:** 8 BG + 8 OBJ on CGB, but per screen, and they can be reloaded mid-frame. Reloading at the playfield's
  top line frees the HUD and stage palettes for the playfield. Every walking patron needs a matching OBJ + BG pair
  (same colours 1-3); keep their numbers equal where possible.
- **Free variety: palette swaps on the same tiles.** Several patrons can share one palette, and a patron can spawn in
  another loaded palette. Arranging the art so that skin sits in the same colour slot everywhere multiplies looks
  (8 looks gave 30 variants in the Saloon) at zero tile cost. Swap colour slots in one figure's art if that's needed
  to line skin up.
- **The wall colour is a free 4th colour.** Colour 0 shows the background through, which works for pupils or gaps in
  clothing. Beware: a lifted sprite shows whatever is behind it.
- **Boss bodies are background tiles, with a sprite "topper".** The body overwrites one patron slot's tiles; give
  that slot to a patron who can sit out boss fights.
- **Palette cycling** (2 bytes per colour in VBlank) is the cheapest animation: glow, fire, water, the DX shimmer.
- **CGB double speed** for performance, with a DMG half-rate mode (logic twice, draw once) for fairness. Music stays at
  60 Hz pacing.
- **DMG compatible, Color enhanced.** Gate Color-only features behind `is_cgb` and keep the DMG path unchanged. Say
  what the DMG player loses.
- **An asm pass keeps a buildable C version of every routine** (`make cfall`), as a porting reference and a test
  oracle.

## Tools built (all in the repo)

| Tool | What it does |
|---|---|
| `tools/gfx_atlas/` (`make atlas`) | A per-screen graphics atlas: palettes, tiles per bank and region, OAM and sprites per line, objects as whole figures, free-palette tables. Generated from the real ROM on DMG and CGB, and published as a review page. |
| `tools/artifacts/palette_plan/` | The palette planner: per venue, the planned OBJ/BG palettes, patrons with pictures, variants, a free-slot count, and a Markdown export for agents. The plan is data in `build.py`. |
| `tools/artifacts/pocket_player/` | A browser Game Boy emulator page (patched WasmBoy core, iOS audio unlock, ROM menu) for testing on a phone. `make_roms.py` packs ROMs. |
| `tools/artifacts/open_questions/`, `review_board/` | The open questions page with media, and a reference animation board. |
| `tools/gen_*.py` | Asset generators: art, music, story, credits, mini-games, boss data, menus. |
| `tests/` + `gbtools` | pytest on both models: variables by name, goldens with a bounding-box report (`GB_GOLDEN_REPORT`). |
| `tools/boss_perf.py`, `data_layout_check.py`, `asm_symtab.py` | Performance, data-layout and symbol checks. |

See `tools/artifacts/README.md` for the review pages' links and how to republish them.

## Process notes for the next game

- Decide the palette plan, the tile budget per entity, and the DMG/Color split before drawing lots of art. Most
  late changes in Spigoteer were palette or tile reshuffles.
- Make generated review pages (atlas, planner) early. They answer budget questions in seconds, and the owner uses
  them to make decisions.
- Keep notes in the repo (`docs/dev/`), not only in a session's scratch space. Session files are lost with the session.
- Agents with `isolation: worktree` must write deliverables to a path git does not ignore (e.g. `docs/dev/concepts/...`), never only `out/`: a worktree whose only changes are ignored files is deleted when the agent finishes. CEDAR's first pass (2026-10-25) was lost that way and recovered from the agent's transcript.
- Handing a half-done branch to a fresh agent (2026-10-26): `gb-worker` always runs in its own worktree and is denied
  git in another agent's tree. Commit the old tree's work as a WIP commit (say NOT GREEN, list the failures, add a
  handoff under `docs/dev/handoffs/`), then tell the new agent to merge that branch into its own.
- Long-running agents that keep stopping mid-test (context past ~150k) waste turns: stop them, WIP-commit, start fresh.
- **Commit messages (2026-11-01, twice in one day):** a failed Write to msg.txt followed by `git commit -F` in the same response commits the previous message. Never send the commit in the same response as the Write of its message; check the Write succeeded first.
- **Mini-game glitches the tests could not see (2026-11-03):** (1) the mini-game tests enter a game with `mg_enter` straight from the title, where BG palette 1 is still the HUD's; a player comes from BONUS > MINI GAMES, whose practice picture loads its palette into BG 0 or 1, so cards, HUD, result window and medal boxes drew in the list's colours. Test the player's route (`tests/test_mg_palette.py`). (2) The owner plays on the Pocket Player (WasmBoy), whose `executeFrame` returns after a fixed cycle count on whatever line the LCD has reached (LY 51 at double speed on a Color), not at VBlank: anything moving sideways is sheared at that line. SameBoy and PyBoy never show it. `tools/dev/wasmboy_frames.js` runs a ROM on that core headless (`--raw` shows the shear); `tools/mg_capture.py` gets timed SameBoy stills of a mini-game from an `-DAUTO_MG` build.
