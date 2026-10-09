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
nothing is taken from the arcade game's soundtrack or any recording. The note lists of "Oh! Susanna" and the
"Galop infernal" are the owner's; the other nine tunes are the owner's melody specs in `docs/music_specs.md`
(supplied 2026-10-09), entered token for token into `tools/songs.py` and checked against the spec by
`tests/test_sound.py`; the sources of those specs are listed below. The arrangement of every tune (bass line,
rhythm, drums, instruments) is ours. Song data is converted to hUGEDriver patterns by `tools/gen_music.py`.

| Tune | Where it plays | Composer, year | Status |
|---|---|---|---|
| "The Entertainer" (A section) | title screen | Scott Joplin, 1902 | public domain |
| "Galop infernal" (the can-can) | every show (dancers' stage show) | Jacques Offenbach, 1858 (from "Orphee aux enfers") | public domain |
| "Oh! Susanna" | level 1, 10, ... (cowboys / saloon) | Stephen Foster, 1848 | public domain |
| "Take Me Out to the Ball Game" (chorus) | sports bar | Albert Von Tilzer (music), Jack Norworth (words), 1908 | public domain (US, published before 1929) |
| "She'll Be Coming 'Round the Mountain" | lumber lodge | American folk song, 19th century (from the spiritual "When the Chariot Comes") | public domain, traditional |
| "Funiculi, Funicula" (verse and chorus) | bistro | Luigi Denza, 1880 | public domain |
| "The Skaters' Waltz" (main theme) | igloo / Arctic | Emile Waldteufel, 1882 | public domain |
| "In the Hall of the Mountain King" (16 bars) | robot factory | Edvard Grieg, 1875 (from "Peer Gynt") | public domain |
| "Sakura Sakura" | teahouse | Japanese traditional (Edo period) | public domain, traditional |
| "The Blue Danube" (first waltz theme, in G) | space lounge | Johann Strauss II, 1867 | public domain |
| "Pop Goes the Weasel" | jungle zoo | English folk tune, c. 1850 | public domain, traditional |
| Level clear jingle | level clear | original, written for this project | ours |
| Game over jingle | game over | original | ours |
| Bonus round loop | bonus round | original | ours |

### Sources of the melody specs (from `docs/music_specs.md`)

- "The Entertainer" (Joplin, 1902; A section, 16 bars): written from memory of the 1902 John Stark & Son
  edition (public domain; scans on IMSLP, "The Entertainer (Joplin, Scott)"). Pitches of bars 1-11 were checked
  against pianoletternotes.blogspot.com (an arrangement, not the source and not credited as one).
  **Bars 12-16 are low confidence: the pitch order may be off; check them against the 1902 score.**
- "Funiculi, Funicula" (Denza, Ricordi 1880): melody from John Chambers' ABC transcription
  (trillian.mit.edu/~jc/music/abc/Italy/FuniculiFunicula.abc, via folktunefinder.com). Verse and chorus; the
  verse's modulating second half is omitted.
- "The Skaters' Waltz" (Waldteufel, 1882, Op. 183): Traditional Tune Archive (tunearch.org, "Skater's Waltz"),
  transcription by Carl Allison from Joe Buchanan's Scottish Tome; an octave above the source.
- "Take Me Out to the Ball Game" (Von Tilzer / Norworth, 1908): John Chambers' ABC
  (trillian.mit.edu/~jc/music/session/waltz/Take_Me_Out_to_the_Ball_Game.abc).
- "She'll Be Coming 'Round the Mountain": John Chambers' ABC collection (mirror of David Kidd's dulcimer
  transcription, originally everythingdulcimer.com); in print in Carl Sandburg's "The American Songbag" (1927).
- "Pop Goes the Weasel": Ryan's Mammoth Collection (1882), p. 264, via John Chambers' ABC mirror on
  abcnotation.com. The chords are our harmonization.
- "The Blue Danube" (Strauss II, 1867, Op. 314): James Kerr, "Merry Melodies" vol. 4 (Glasgow, c. 1870s-80s),
  p. 42 #387, transcribed to ABC by John Chambers (abcnotation.com), in the transposed key G. The chords are our
  harmonization.
- "In the Hall of the Mountain King" (Grieg, 1875): **no transcription source; written from memory. Verify
  against the Peer Gynt Suite No. 1 score on IMSLP (the 1888 C.F. Peters edition is public domain) before
  crediting a source.** Bars 1-8 high confidence, bars 9-12 moderate, bars 13-16 are a return chosen for
  looping (Grieg's continuation differs).
- "Sakura Sakura": melody from John Chambers' ABC "Sakura (Cherry Blossom)"
  (trillian.mit.edu/~jc/music/abc/Japan/Sakura_Am.utf8.abc); chords (not used, the bass is a drone) adapted from
  Frank Nordberg's Musica Viva transcription in the same collection.

The old original in-game loop and the old title tune (a verse of "Oh! Susanna") were removed.

## Sound effects

Original: simple register-level effects defined in `src/music.c`.

## Tools used, not shipped

RGBDS and GBDK-2020 (build toolchain), PyBoy and SameBoy (testing), Pan Docs (hardware reference).
