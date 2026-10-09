# Credits and licences

## Code reused

### hUGEDriver (music driver)

- Source: SuperDisk/hUGEDriver, commit `d6863d2947`, taken from the offline reference copy
  (`reference/hugedriver`, listed there as `reuse`).
- Licence: the project's README states "hUGETracker and hUGEDriver are dedicated to the public
  domain." The repository has no LICENSE file. No attribution is required; it is given here anyway.
- Copied unchanged into `third_party/hugedriver/`: `hUGEDriver.asm` (with the one change below),
  `include/hUGEDriver.h`, `include/hUGE.inc`, `include/hUGE_note_table.inc`, `include/hardware.inc`
  (the copy of gbdev's hardware.inc that ships with the driver).
- Changes made in this repository:
  - `hUGEDriver.asm`: three C-visible aliases (`_hUGE_row`, `_hUGE_tick`, `_hUGE_current_order`) beside
    the driver's own variables, so tests can watch the playback position.
  - `tools/rgb2sdas.py` (the driver's RGBDS-object to GBDK-object converter): accepts RGBDS 1.0.x object
    files (revision 13: section records gained a node id and line number and a flag byte; `LOW()` and
    `HIGH()` became RPN operators).
- Built by the `Makefile`: `rgbasm -DGBDK` -> `rgb2sdas.py` -> linked into fixed ROM bank 2 with the
  song data and `src/music.c`.

## Music

All melodies are original or public domain; nothing is taken from the arcade game's soundtrack or any
other copyrighted work. The note data is our own (`tools/gen_music.py`).

| Tune | Source |
|---|---|
| Title | The verse of "Oh! Susanna" (Stephen Foster, 1848, public domain), entered from memory. It may deviate from the published melody in small details. The arrangement (accompaniment, rhythm, instruments) is ours. |
| In-game loop | Original, written for this project. |
| Level clear jingle | Original. |
| Game over jingle | Original. |
| Bonus round loop | Original. |

## Sound effects

Original: simple register-level effects defined in `src/music.c`.

## Tools used, not shipped

RGBDS and GBDK-2020 (build toolchain), PyBoy and SameBoy (testing), Pan Docs (hardware reference).
