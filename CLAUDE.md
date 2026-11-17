# Spigoteer (Game Boy / Game Boy Color, GBDK C with an assembly pass)

DMG compatible, Color enhanced. Offline container: the firewall allows only GitHub, npm and the Anthropic API, and
everything you need is local. The owner pushes to GitHub himself.

**Toolchain, asset formats, hardware limits and the `reference/` library are in the `gb-toolchain` skill**
(`.claude/skills/gb-toolchain/SKILL.md`). Load it before asset, palette, level, hardware or reference work.

## Rules that are not negotiable

1. **Done means committed, and the verify run passes** (`tools/dev/verify.sh`, run by `gb-runner`), on both DMG and CGB.
   While working, run only the tests for the area you touch (`make test F=<file>` or `make test K=<expr>`), plus
   `make` and `make check`; the verify run is the one full run. A ROM that builds is not a ROM that works. Run the
   tests; do not reason about whether they would pass.
2. **Reference material has a licence rule. Read `$GAMEBOY_DOC/reference/MANIFEST.md`
   before opening anything under `reference/`.** `study` repositories are
   commercial disassemblies: learn how they do things and write your own
   code. Copy no code, graphics, music, text, maps or data from them, and do
   not "adapt" a routine line by line. `reuse` repositories are open source
   and reusable under the licence in their directory, with attribution.
3. **Replacing a golden screenshot is a visible decision, and only the supervisor makes it.** Add new goldens
   freely. When a test fails because the picture changed on purpose, leave the failure in, and name the golden, its
   diff bounding box and why in the commit message and report. Never regenerate all goldens to make a red run green.
4. Generated files under `build/` and `out/` are never committed and never
   edited. Sources live under `src/` and `assets/`.
5. Publishing (itch.io, GitHub releases, flashing a cart) happens outside
   this container. Build the artifact, say where it is, stop.

## Project rules (the owner's standing rules: they bind the supervisor and every agent)

- **Git: reversible actions only.** New commits on your own branch. Never amend, rebase, reset, stash or force; never
  `checkout -- .` or `git rm`. One git command at a time. Merging and rebasing onto main are the supervisor's job.
- **Permission denials:** if a command is DENIED, do not retry it, work around it or ask the owner to run it: stop and
  report. "Too complex to verify" (long heredocs, compound commands) is not a denial: use the Write/Edit tools and
  plain single commands, and carry on.
- **Goldens:** add new ones freely. Only the supervisor replaces an existing golden. Agents list each changed golden
  with its diff bounding box (from a read-only script that writes nothing under `tests/golden/`) and the reason, and
  commit with those failures left in, saying so.
- **Budgets:** WRAM is nearly exhausted: add NO new WRAM globals; use the existing unions, `story_scratch` or
  `BOSS_OWN`. Report `WRAM_LO` / `WRAM_HI_0` and `romusage` before and after. ROM0 has 494 B free in the default build (`build/game.gb`, with the debug menu; the tightest, so the rule means this one): keep it, never let it shrink. Measure it with the `ROM0 real: ... bytes free` line that `make` prints (`python3 tools/rom0free.py build/game.map`, from the linker map: _CODE, _HOME, _INITIALIZER, _GSINIT, _GSFINAL against 0x4000); `romusage`'s ROM_0 free column (835 B today) overstates it by 341 B. `build/release.gb` (no debug menu) has 821 B and `build/game-c.gb` 90 B: not the budget.
  Never raise a perf guard; if one fails, stop and report.
- **Assembly:** only within the authorised asm pass, behind a define. Every asm routine keeps its C version built
  (`make cfall`) and tested. Never delete the C path.
- **DMG and Color:** gate Color-only features behind `is_cgb` and leave the DMG path unchanged. For any visual
  feature, say whether it fits the DMG or only Color, and which budget it uses.
- **Shared machine:** other agents work in parallel in their own worktrees. Touch only what your task needs; keep
  scratch files in your worktree's `out/`; kill any pytest or profiler you start.
- **Commits:** `git add <files>` (never `-a`); write the message to a file and use `git commit -F`. It must end with
  the attribution lines the session gives (`Co-Authored-By: ...` and `Claude-Session: <this session's URL>`; the
  URL changes per session, so the supervisor puts the current lines in each brief).
- **Your part is done** when it is committed, with your targeted tests and `make check` green on DMG and CGB; the
  branch is done per rule 1. Report the commits, the goldens, the budget numbers, the preview
  paths and anything you are unsure about.
- **Owner decisions:** When the owner gives a rule, decision or plan, save it to its file in the same turn (memory note
  for standing rules, QUEUE for plans) before replying, and say where it was saved. Conversation is not storage.

## The loop

    make            # assets -> data, per-object compile (8 jobs) and link, bank usage: ~15 s clean, < 1 s after a .c edit;
                    # make OBJ=0 is the old one-shot lcc call (~75 s), the byte-identical reference build
    make test       # full pytest on DMG and CGB, 8 shards via tools/dev/ptest.py (~4 min); JOBS=1 for the serial run.
                    # Targeted (preferred while working): make test K=<expr> (pytest -k) or make test F=<file>
    make check      # SameBoy, DMG + CGB, screenshots in out/check/
    make preview    # every asset as an x8 PNG in out/preview/ (look at them)
    make cfall      # the C reference build of every asm routine

Full branch verification, run only by a `gb-runner` agent: `tools/dev/verify.sh <worktree> <name>` (default stages
about 2.5 min (2 min 29 s measured): plain `make` (`make -B` when the branch changes the Makefile or a generator) with `make release` and `make cfall` beside it, `make check`, then pytest and the double speed / half rate tests side by side; `FULL=1` uses `make -B`, builds the three ROMs with `OBJ=0` too and fails on any sha1 difference, adds the slow fade stage and the release-only tests, `CBUILD=1` adds the C-build pytest).

Test and build commands (`make`, `make test`, `make check`, `pytest`) pass through a hook: if the output is long you
see the failures, errors and the last lines, plus the path of the full log. Open the full log only when that is not
enough. Don't pipe test commands through `tail` or `head`: the hook already trims the output.

## Gotchas that have bitten this project

- PyBoy is for driving and asserting; SameBoy is the timing truth. PyBoy zeroes RAM that real hardware leaves as
  junk: clear hand-placed bytes in `main()` and test with a junk poke.
- PyBoy audio: slice the buffer to `raw_buffer_head // 2` each frame, or recordings crackle.
- Palette RAM and VRAM are only safe to write with the LCD off or in VBlank/HBlank; mid-frame writes corrupt silently.
- `hardware.inc` v6 renamed everything (`LCDC_ON`, `IE_VBLANK`...); never paste pret constants. More in the skill.
- `pgrep -f` matches its own loop. Wait on a PID or a log line.

## Context habits (the owner pays for every token re-read)

- Find with `grep -n`, then read the lines you need; do not read large files whole. `docs/dev/notes/PLAN.full.md` is
  history: grep it.
- Do not re-read a file that is already in your context.
- Show images as ONE labelled contact sheet (`tools/dev/contact_sheet.py`), not file by file.
- Keep reports short: results, numbers, paths, doubts. Do not restate the brief.

## Compact instructions

When compacting, keep: the owner's exact words on open asks and decisions; open question numbers; each running
agent's ID, task, branch and worktree; what is merged and what is pending; goldens replaced and why; the next steps.
Drop tool output, file contents and image descriptions: they can be re-read.

## Where things live

Project skills (they load when a task needs them): `gb-toolchain`, `spigoteer-music`, `spigoteer-patrons`,
`spigoteer-minigames`, `spigoteer-review-pages`, plus the owner's `gb-pixel-art`. Shared scripts in `tools/dev/`:
`verify.sh`, `watch_agents.sh`, `contact_sheet.py`, `golden_bbox.py` (read-only golden diffs).


`docs/dev/`: `SUPERVISOR.md` (the supervisor's procedure), `notes/QUEUE.md`, `LESSONS.md`, handoffs,
`memory_snapshot/`. Review pages and how to republish them: `tools/artifacts/README.md`.
