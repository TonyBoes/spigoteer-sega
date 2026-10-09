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
- Built by the `Makefile`: `rgbasm -DGBDK` -> `rgb2sdas.py` -> linked into ROM bank 2 with the order tables
  and `src/music.c`. The song patterns sit in ROM bank 3 and are copied into WRAM when a tune starts (the driver
  reads patterns through plain pointers and only runs from bank 2).

## Music

The compositions below are in the public domain (composers died more than 70 years ago, or the tune is a
traditional/folk melody whose authors are unknown and whose first publication is long out of copyright);
nothing is taken from the arcade game's soundtrack or any recording. No score or MIDI file was copied: the
note data in `tools/songs.py` was entered from memory, so it may deviate from the published melodies in small
details (see the caveats in PLAN.md). The arrangement of every tune (bass line, rhythm, drums, instruments) is
ours. Song data is converted to hUGEDriver patterns by `tools/gen_music.py`.

| Tune | Where it plays | Composer, year | Status |
|---|---|---|---|
| "The Entertainer" (opening A strain) | title screen | Scott Joplin, 1902 | public domain |
| "Galop infernal" (the can-can) | every show (dancers' stage show) | Jacques Offenbach, 1858 (from "Orphee aux enfers") | public domain |
| "Oh! Susanna" | level 1, 10, ... (cowboys / saloon) | Stephen Foster, 1848 | public domain |
| "Take Me Out to the Ball Game" (chorus) | sports bar | Albert Von Tilzer (music), Jack Norworth (words), 1908 | public domain (US, published before 1929) |
| "She'll Be Coming 'Round the Mountain" | lumber lodge | American folk song, 19th century (from the spiritual "When the Chariot Comes") | public domain, traditional |
| "Funiculi, Funicula" (chorus) | bistro | Luigi Denza, 1880 | public domain |
| "The Skaters' Waltz" (main theme) | igloo / Arctic | Emile Waldteufel, 1882 | public domain |
| "In the Hall of the Mountain King" | robot factory | Edvard Grieg, 1875 (from "Peer Gynt") | public domain |
| "Sakura Sakura" | teahouse | Japanese traditional (Edo period) | public domain, traditional |
| "The Blue Danube" (first waltz theme) | space lounge | Johann Strauss II, 1866 | public domain |
| "Pop Goes the Weasel" | jungle zoo | English folk tune, c. 1850 | public domain, traditional |
| Level clear jingle | level clear | original, written for this project | ours |
| Game over jingle | game over | original | ours |
| Bonus round loop | bonus round | original | ours |

The old original in-game loop and the old title tune (a verse of "Oh! Susanna") were removed.

## Sound effects

Original: simple register-level effects defined in `src/music.c`.

## Tools used, not shipped

RGBDS and GBDK-2020 (build toolchain), PyBoy and SameBoy (testing), Pan Docs (hardware reference).
