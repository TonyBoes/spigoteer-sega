# Spigoteer, Sega port (Game Gear / Master System from the Game Boy GBDK C source)

You are Codex, the only agent in this repo, running in a Docker Sandboxes microVM in clone mode: this is a private
clone, and the owner (Tony) fetches your commits from the host and pushes them himself. You cannot push. The network
is a host-side policy you cannot change.

**This file takes precedence over `CLAUDE.md`.** That file describes the Claude Code workflow on the Game Boy game
(supervisor, subagents, skills, hooks). Its project rules are restated here; its mechanics do not apply to you.

**Start of every session:** read `docs/dev/memory_snapshot/MEMORY.md` and the notes it links (the owner's standing
rules), the newest `docs/dev/notes/HANDOFF_*.md`, then `docs/dev/PORT_PLAN.md` and `docs/dev/notes/PORT_LOG.md`.
First session only: set up per `docs/dev/SANDBOX_SETUP_SEGA.md` and run its checks.

**Reference docs you read on demand** (they were written as Claude skills; for you they are plain files):
`.claude/skills/gb-toolchain/SKILL.md` (toolchain, asset formats, Game Boy hardware limits, the `reference/`
library) before asset, palette, level, hardware or reference work; the other `.claude/skills/spigoteer-*/SKILL.md`
when a task touches music, patrons, minigames or review pages.

## Rules that are not negotiable

1. **Done means committed, and the gates pass.** For the Game Boy build: `tools/dev/verify.sh /workspace <name>`
   → `RESULT: PASS` (you run it yourself; there is no runner agent). For each Sega target that exists: its
   `make test` and `retrocheck` pass. While working, run only the tests for the area you touch
   (`make test F=<file>` / `K=<expr>`), plus `make` and `make check`. A ROM that builds is not a ROM that works.
   Run the tests; do not reason about whether they would pass.
2. **Reference material has a licence rule.** Read `$GAMEBOY_DOC/reference/MANIFEST.md` and
   `$SEGA_DOC/reference/MANIFEST.md` before opening anything under them. `study` repositories are commercial
   disassemblies: learn how they do things and write your own code; copy no code, graphics, music, text, maps or
   data, and do not "adapt" a routine line by line. `reuse` repositories are reusable under the licence in their
   directory, with attribution.
3. **Only the owner replaces an existing golden.** Add new goldens freely. When a test fails because the picture
   changed on purpose, leave the failure in, and name the golden, its diff bounding box
   (`tools/dev/golden_bbox.py`, read-only) and why, in the commit message and report. Never regenerate goldens to
   make a red run green.
4. Generated files under `build/` and `out/` are never committed or edited. Sources live under `src/` and `assets/`.
5. Publishing (itch.io, GitHub releases, flashing a cart) happens outside this sandbox. Build, say where, stop.

## Project rules (the owner's standing rules)

- **Git: reversible actions only.** New commits on your own branch (`sega-port`, or a branch per phase). Never amend,
  rebase, reset, stash or force; never `checkout -- .` or `git rm`. One git command at a time. Merging to main is the
  owner's job.
- **Blocked or refused:** a 403 or "Approval required" from the network, or any hook or tool refusing something: do
  not retry or work around it. Stop and report the exact host or message.
- **Budgets (the Game Boy build):** WRAM is nearly exhausted: add NO new WRAM globals; use the existing unions,
  `story_scratch` or `BOSS_OWN`. ROM0 has 494 B free in `build/game.gb` (with the debug menu, the tightest): measure
  with the `ROM0 real: ... bytes free` line `make` prints (`tools/rom0free.py`), not `romusage`'s ROM_0 column, which
  overstates it by 341 B. It must never shrink. Report WRAM_LO / WRAM_HI_0 / ROM0 / `romusage` before and after. The
  Sega targets have their own budgets: record them in `PORT_LOG.md` from their first build. Never raise a perf
  guard; if one fails, stop and report.
- **Assembly:** only within the authorised asm pass, behind a define. Every asm routine keeps its C version built
  (`make cfall`) and tested. Never delete the C path. Game Boy asm (SM83) does not run on Z80 targets: the C path is
  what the Sega builds use.
- **DMG and Color:** gate Color-only features behind `is_cgb` and leave the DMG path unchanged. For any visual
  feature, say which consoles it fits and which budget it uses.
- **Commits:** `git add <files>` (never `-a`); write the message to a file and `git commit -F <file>`. End every
  message with `Agent: Codex (sbx sandbox spigoteer-sega)`. Identity is in git config; never write the owner's email
  address into a file.
- **Your part is done** when it is committed with the gates green. Report the commits, goldens, budget numbers,
  preview paths and anything you are unsure about.
- **Owner decisions:** you have no persistent memory. When the owner gives a standing rule, add it to the right
  file in `docs/dev/memory_snapshot/` and commit it before replying; plans go in `docs/dev/notes/QUEUE.md`; port
  decisions in `PORT_LOG.md`. Say where you saved it. Conversation is not storage.
- **Port decisions are the owner's** where `PORT_PLAN.md` marks them (HUD redesign, colour beyond the Game Boy
  Color look, the audio driver and every re-arranged tune, the Master System layout). Stop there with options and
  previews; do not pick one and build it.

## The loop

    make            # Game Boy: ~15 s clean, < 1 s after a .c edit; ends with "ROM0 real: ... bytes free"
    make test       # Game Boy pytest, DMG and CGB, sharded (~4 min). Targeted: make test K=<expr> / F=<file>
    make check      # SameBoy, DMG + CGB
    make preview    # assets as x8 PNGs in out/preview/
    make cfall      # the C reference build of every asm routine
    tools/dev/verify.sh /workspace <name>     # the full Game Boy gate (~2.5 min); log in out/verify/<name>.log

Sega targets (as `PORT_PLAN.md` adds them to the Makefile), and the harness that tests them:

    retrotest run build/gg/spigoteer.gg --frames 120 --print <var> --out out/gg.png
    retrocheck build/gg/spigoteer.gg --frames 600 --print <var> --expect <var>=<n>
    from retrotools import Rom            # pytest driver, like PyBoy; symbols from the .noi

`retrotest`/`Rom` (stable-retro) is fast and not cycle-accurate; `retrocheck` (MesenCE) is the timing truth, as
SameBoy is for Game Boy. MesenCE runs boot sequences that stable-retro skips: assert state after boot, never
absolute frame counts. `retrosprite` converts ASCII or PNG art (16-colour aware) and checks per-console limits.

There is no output-trimming hook. Send long output to a log and read the failures:
`make test > out/logs/test.log 2>&1; echo $?` then `grep -nE 'FAIL|Error|assert' out/logs/test.log | head -40`.

## Gotchas

Game Boy (from `CLAUDE.md`): PyBoy is for driving, SameBoy is timing truth; PyBoy zeroes RAM that hardware leaves as
junk (clear hand-placed bytes in `main()`, test with a junk poke). PyBoy audio: slice to `raw_buffer_head // 2`.
Palette RAM and VRAM only with the LCD off or in VBlank/HBlank. `hardware.inc` v6 renamed everything. `pgrep -f`
matches its own loop.

Sega (each verified on GBDK 4.5.0):

- **Game Gear tile maps:** `set_bkg_tiles`/`set_tile_map` add the GG's visible-window offset (6,3 tiles) themselves.
  Do NOT add `DEVICE_SCREEN_X/Y_OFFSET` to their coordinates. Sprite positions do not get it: use
  `DEVICE_SPRITE_PX_OFFSET_X/Y` (48,23 on GG; 0,-1 on SMS). Adding it to both shifts the screen by (6,3).
- **No sprite flips** on SMS/GG: guard with `#if HARDWARE_SPRITE_CAN_FLIP_X`.
- 2bpp Game Boy tiles load on SMS/GG through `set_2bpp_palette(COMPAT_PALETTE(...))` before `set_bkg_data`.
- **8 sprites per line**, not 10.
- **SMS input in `retrocheck` needs the `Sms` controller line** in `/opt/mesence/settings.json`; without it input is
  silently ignored (Game Gear and Game Boy controls are built in).
- `tools/retro/gbdk-skeleton/` shows every one of these working on gb, sms and gg.

## Context habits (the owner pays for every token re-read)

- Find with `grep -n`, then read the lines you need; do not read large files whole. `docs/dev/notes/PLAN.full.md` is
  history: grep it.
- Do not re-read a file already in your context.
- Show images as ONE labelled contact sheet (`tools/dev/contact_sheet.py`), not file by file.
- Keep reports short: results, numbers, paths, doubts. Do not restate the brief.

## Where things live

`docs/dev/PORT_PLAN.md` (the plan), `docs/dev/notes/PORT_LOG.md` (state, budgets, decisions — create it in
Phase 0), `docs/dev/SANDBOX_SETUP_SEGA.md`, `docs/dev/memory_snapshot/`, `docs/dev/notes/QUEUE.md`, `LESSONS.md`,
handoffs. Shared scripts in `tools/dev/`; the SMS/GG harness in `tools/retro/`. Game Boy references in
`$GAMEBOY_DOC/reference/`; SMS/GG references in `$SEGA_DOC/reference/`.
