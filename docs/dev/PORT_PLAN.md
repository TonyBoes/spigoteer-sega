# Spigoteer Sega port: plan

Goal: Spigoteer on Game Gear, then Master System, from the same C source as the Game Boy game, which keeps building
and passing its tests throughout. Work phase by phase; do not start a phase until the previous one's gate passes.

Measured on the Game Boy source at the fork (`git grep -l`, .c/.h files):

| Game Boy dependency | Files | SMS/GG reality |
|---|---|---|
| `gb/gb.h`, `gb/cgb.h` includes | 71, 47 | GBDK's `<gbdk/platform.h>` covers both |
| Palette registers and CGB palettes | 26, 36 | 2 palettes of 16 colours (GG: 12-bit colour, SMS: 6-bit) |
| Sprite flips | 21 | **SMS/GG cannot flip sprites**: mirrored tiles, which cost VRAM |
| LCD/STAT interrupts (mid-screen effects) | 13 | a VDP line-counter interrupt; different timing and abilities |
| Window layer | 9 | **no window layer**; scroll-lock of top rows, sprites, or a line interrupt split |
| hUGEDriver, sound registers | 7, 7 | different sound chip (SN76489 PSG: 3 square + 1 noise) |
| Sprites per line | — | 8 per line (Game Boy: 10) |

Game Gear first: its visible screen is 160x144, the Game Boy's, so layouts carry over. Master System (256x192) last.

## Phase 0 — baseline

The sandbox is set up per `docs/dev/SANDBOX_SETUP_SEGA.md`; the Game Boy verify run passes; ROM0 free, WRAM and
`romusage` are recorded in `docs/dev/notes/PORT_LOG.md` as the baseline. **Gate:** `verify.sh` PASS.

## Phase 1 — platform layer, Game Boy unchanged

Move every Game Boy-specific call behind a small platform layer (`src/platform/`): palettes, sprite flip, the
window/HUD, LCD effects, audio, and anything else Phase 2 trips over. Includes become `<gbdk/platform.h>` plus the
layer's header. On Game Boy the layer must compile to what the code did before.

Work file group by file group, committing each. **Gate after every commit:** the Game Boy build and its tests are
unchanged — targeted tests while working, `verify.sh` at the end of the phase; ROM0 free never shrinks; no new WRAM
globals; no golden replaced. If the layer costs ROM0 bytes, stop and report rather than squeezing elsewhere.

## Phase 2 — Game Gear compiles and boots

Add a `gg` target to the Makefile beside the existing variants (`build/gg/spigoteer.gg`, `lcc -mz80:gg`, `.noi`
symbols). Stub what has no port yet: audio silent, HUD absent, LCD effects off, flips ignored. **Gate:** it builds;
`retrotest` shows the title screen; first stable-retro tests (boot, title, start a game) pass; `retrocheck` OK.
New goldens under `tests/golden/gg/`.

## Phase 3 — Game Gear parity, one stub at a time

Replace each stub with a real implementation, smallest first: palettes, then flips (mirrored tiles), then LCD
effects, then the HUD. Port the gameplay tests to the GG build as each area lands. **Gate per area:** its tests pass
on GG, the Game Boy verify run still passes.

**Owner decisions — stop and ask, with options and previews, before building:**

- **HUD:** how the window-layer screens are redone (scroll-lock rows, sprites, or a split), shown as GG mock-up
  screenshots side by side with the Game Boy ones.
- **Colour:** the GG has 16-colour palettes. Default to the Game Boy Color look; anything beyond that is the owner's
  call, shown as a contact sheet.

## Phase 4 — audio

A PSG music and sound-effects driver (devkitSMS ships PSGlib; check its licence in `LICENSES.txt`) and the tunes
re-arranged for 3 square channels + noise. **Owner decision:** the driver, and approval of each re-arranged tune
(recordings, not descriptions). The `spigoteer-music` skill and the tunes' credits still apply.

## Phase 5 — Master System

256x192 screen: every layout needs a decision (centre the 160x144 game, or use the space). **Owner decision**
before any code. Then an `sms` target, its tests, its gate.

## Throughout

- Log each phase's state, budgets and open questions in `docs/dev/notes/PORT_LOG.md`, committed.
- MesenCE is the timing truth for SMS/GG, as SameBoy is for Game Boy. stable-retro, like PyBoy, zeroes RAM that real
  hardware leaves as junk.
- `tools/retro/gbdk-skeleton/` shows each cross-platform pattern working on gb, sms and gg: the Game Gear
  tile-map offset, `set_2bpp_palette`, the flip guard.
