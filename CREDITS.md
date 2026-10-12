# Credits and licences

## Code reused

### hUGEDriver (music driver)

- Source: SuperDisk/hUGEDriver, commit `d6863d2947`, taken from the offline reference copy
  (`reference/hugedriver`, listed there as `reuse`).
- Licence: the project's README states "hUGETracker and hUGEDriver are dedicated to the public
  domain." The repository has no LICENSE file. No attribution is required; it is given here anyway.
- Copied unchanged into `third_party/hugedriver/`: `hUGEDriver.asm` (with the changes below),
  `include/hUGEDriver.h`, `include/hUGE.inc`, `include/hUGE_note_table.inc`, `include/hardware.inc`
  (the copy of gbdev's hardware.inc that ships with the driver).
- Changes made in this repository:
  - `hUGEDriver.asm`: three C-visible aliases (`_hUGE_row`, `_hUGE_tick`, `_hUGE_current_order`) beside
    the driver's own variables, so tests can watch the playback position (and `src/music.c` reads `_hUGE_row` to swing the Entertainer's row lengths), and a fourth, `_hUGE_ticks_per_row`, so
    `src/music.c` can play a tune one tick a row faster (The Chrome Cow's Last call: "the band plays faster"), and a
    fifth, `_hUGE_note_table` (the driver's period table), so `src/music.c`'s channel-1 harmony voice (music step 5)
    plays the same pitches as the driver, and two more, `_hUGE_row_break` and `_hUGE_next_order` (the pending position
    jump), so `src/music.c` can start a tune partway in (`tune_t.start`: Mountain's "She'll be" pickup).
  - `tools/rgb2sdas.py` (the driver's RGBDS-object to GBDK-object converter): accepts RGBDS 1.0.x object
    files (revision 13: section records gained a node id and line number and a flag byte; `LOW()` and
    `HIGH()` became RPN operators).
- Built by the `Makefile`: `rgbasm -DGBDK` -> `rgb2sdas.py` -> linked into ROM bank 2 with the order tables
  and `src/music.c`. The song patterns sit in ROM bank 10 and are copied into WRAM when a tune starts (the driver
  reads patterns through plain pointers and only runs from bank 2).

## Music

The compositions below are in the public domain (composers died more than 70 years ago, or the tune is a
traditional/folk melody whose authors are unknown and whose first publication is long out of copyright);
nothing is taken from the arcade game's soundtrack or any recording. The note lists of "Oh! Susanna" and the
"Galop infernal" are the owner's; the other ten tunes are melody specs in `docs/music_specs.md` (nine supplied by
the owner 2026-10-09; "Drunken Sailor", the owner's pick for The Chrome Cow, transcribed by us 2026-10-11), entered
token for token into `tools/songs.py` and checked against the spec by `tests/test_sound.py`; the sources of those
specs are listed below. The arrangement of every tune (bass line,
channel-1 harmony line, rhythm, drums, instruments) is ours. Song data is converted to hUGEDriver patterns by `tools/gen_music.py`.

| Tune | Where it plays | Composer, year | Status |
|---|---|---|---|
| "The Entertainer" (A and B sections) | title screen | Scott Joplin, 1902 | public domain |
| "Galop infernal" (the can-can) | every show (dancers' stage show) | Jacques Offenbach, 1858 (from "Orphee aux enfers") | public domain |
| "Oh! Susanna" | level 1, 11, ... (cowboys / saloon) | Stephen Foster, 1848 | public domain |
| "Take Me Out to the Ball Game" (chorus) | sports bar | Albert Von Tilzer (music), Jack Norworth (words), 1908 | public domain (US, published before 1929) |
| "She'll Be Coming 'Round the Mountain" | lumber lodge | American folk song, 19th century (from the spiritual "When the Chariot Comes") | public domain, traditional |
| "Funiculi, Funicula" (verse and chorus) | bistro | Luigi Denza, 1880 | public domain |
| "The Skaters' Waltz" (main theme) | igloo / Arctic | Emile Waldteufel, 1882 | public domain |
| "In the Hall of the Mountain King" (16 bars) | robot factory | Edvard Grieg, 1875 (from "Peer Gynt") | public domain |
| "Drunken Sailor" (verse and chorus, fast and punky) | The Chrome Cow (biker bar) | traditional English sea shanty (19th century or earlier) | public domain, traditional |
| "Sakura Sakura" | teahouse | Japanese traditional (Edo period) | public domain, traditional |
| "Pop Goes the Weasel" | jungle zoo | English folk tune, c. 1850 | public domain, traditional |
| "The Blue Danube" (first waltz theme, in C) | space lounge | Johann Strauss II, 1867 | public domain |
| Level clear jingle | level clear | original, written for this project | ours |
| Game over jingle | game over | original | ours |
| Bonus round loop | bonus round | original | ours |

### Sources of the melody specs (from `docs/music_specs.md`)

- "The Entertainer" (Joplin, 1902; A and B sections, 32 bars): checked note by note (2026-10-11) against the Mutopia
  Project's score, "The Entertainer" (`ftp/JoplinS/entertainer/entertainer.ly` in github.com/MutopiaProject/MutopiaProject,
  Mutopia-2016/11/25-263), typeset by Chris Sawer (overhauled by Simon Albrecht, 2015) from a reproduction of the
  original 1902 edition; the typesetting is placed in the **public domain**. We transcribed the melody (the lower
  note of the right hand's octaves, score bars 5-20) and the harmony of the A section into our own format; the
  earlier list (written from memory, bars 2-16 a sixteenth early and bars 12-16 wrong) was corrected. The B section
  (score bars 22-36 with the second endings of both sections, bars 21 and 38; its melody the top note of the right
  hand as written) and its harmony were transcribed the same way from the same score (2026-10-11).
- "Funiculi, Funicula" (Denza, Ricordi 1880): the verse checked bar by bar and the echo "Tu sa-ie ad-do" (bar 7)
  transcribed from Ricordi, Milan 1880, first edition, plate 47127 (IMSLP #148203, public domain) (owner-supplied
  transcription, 2026-10-11); melody otherwise from John Chambers' ABC transcription
  (trillian.mit.edu/~jc/music/abc/Italy/FuniculiFunicula.abc, via folktunefinder.com). Verse and chorus; the
  verse's modulating second half is omitted.
- "The Skaters' Waltz" (Waldteufel, 1882, Op. 183): bars 1-14 confirmed against a transcription from Luck's Music
  Library full score, plate K. & E. 5154 (IMSLP #102459, public domain) (owner-supplied transcription, 2026-10-11);
  bars 15-16 and the loop are ours. Melody list: Traditional Tune Archive (tunearch.org, "Skater's Waltz"),
  transcription by Carl Allison from Joe Buchanan's Scottish Tome; an octave above the source.
- "Take Me Out to the Ball Game" (Von Tilzer / Norworth, 1908): transcribed from York Music Co., New York, 1908,
  pp. 4-5, via the Library of Congress (public domain) (owner-supplied transcription, 2026-10-11): bars 8, 20, 25
  and 26 corrected from it, the rest confirmed. Earlier list: John Chambers' ABC
  (trillian.mit.edu/~jc/music/session/waltz/Take_Me_Out_to_the_Ball_Game.abc).
- "She'll Be Coming 'Round the Mountain": John Chambers' ABC collection (mirror of David Kidd's dulcimer
  transcription, originally everythingdulcimer.com); in print in Carl Sandburg's "The American Songbag" (1927).
  Melody rhythm and pitches from Simon Horn's MIDI (2021, CC0, Wikimedia Commons), supplied by the owner 2026-10-12.
- "Drunken Sailor" (traditional): no transcription source; the shanty's well-known melody written down by us in
  D Dorian (docs/music_specs.md tune 11), arranged fast and punky (driving root-eighths bass, every note cut short).
- "Pop Goes the Weasel": Ryan's Mammoth Collection (1882), p. 264, via John Chambers' ABC mirror on
  abcnotation.com. The chords are our harmonization.
- "The Blue Danube" (Strauss II, 1867, Op. 314): checked note by note (2026-10-11) against the Mutopia Project's
  "The Blue Danube Waltz (main theme)" (`ftp/StraussJJ/O314/blue_danube/blue_danube.ly` in
  github.com/MutopiaProject/MutopiaProject, Mutopia-2014/03/24-519), typeset by **Nikos Kouremenos** from Christian
  Mondrup's four-hand piano reduction (Werner Icking Music Archive), (c) The Mutopia Project and Nikos Kouremenos,
  licensed **Creative Commons Attribution-ShareAlike 4.0** (https://creativecommons.org/licenses/by-sa/4.0/). The
  composition is public domain; we transcribed its melody (the top note of the right hand) and harmony, in the
  score's key C, into our own note format and arrangement. The earlier list (James Kerr, "Merry Melodies" vol. 4,
  via John Chambers' ABC, in G) had wrong pitches in bars 9-14 and the wrong octave in bars 25-32.
- "In the Hall of the Mountain King" (Grieg, 1875): written from memory in the spec; bars 1-12 confirmed note for note
  and in rhythm (2026-10-11, music step 3) by the Mutopia Project's "In the Hall of the Mountain King"
  (`ftp/GriegE/O46/Dans_l_antre_du_roi_de_la_montagne/Dans_l_antre_du_roi_de_la_montagne.ly` in
  github.com/MutopiaProject/MutopiaProject, Mutopia-2013/12/07-1888), typeset by **Coyau** from The University Society's
  1918 piano edition and placed in the **public domain** by the typesetter. Bars 13-16 are a return chosen for looping
  (Grieg's continuation differs).
- "Sakura Sakura": bars 1-12 confirmed against a transcription from Sokyokushu (Collection of Japanese Koto Music),
  Ministry of Education Music Investigation Committee, 1888, NDL pid 857651, public domain (owner-supplied
  transcription, 2026-10-11); its bars 13-14 differ, ours are kept. Melody from John Chambers' ABC "Sakura (Cherry Blossom)"
  (trillian.mit.edu/~jc/music/abc/Japan/Sakura_Am.utf8.abc); chords (not used, the bass is a drone) adapted from
  Frank Nordberg's Musica Viva transcription in the same collection.
- "Galop infernal" (Offenbach, 1858): the owner's note list, confirmed note for note and in rhythm by a transcription
  from the German vocal score "Orpheus in der Unterwelt", IMSLP #26815, plate 10779 (the chorus statement, in G;
  ours is a fifth up, in D), public domain (owner-supplied transcription, 2026-10-11).

### Rhythm audit (music step 3, 2026-10-11)

The owner heard "Su-san-na" and "com-in' round the moun-tain" in even notes where the songs are sung in uneven ones.
Every melody's rhythm was compared with a public-domain score found on GitHub where one exists (fetched as data;
our notes are our own transcription, no file was copied):

- "Oh! Susanna" (Foster, 1848): Craig Sapp's Humdrum (**kern) encoding, `kern/fostr20.krn` in
  **github.com/humdrum-tools/foster-songs** (from the "Stephen Foster Song Book", Dover Publications, pp. 89-91, a
  reprint of the 19th-century editions; the repository has no licence file, the song is public domain and only its
  rhythm was read, transposed from G to C). Cross-checked: the Wikifonia lead sheet in OpenEWLD (below) and Bloomfield's
  "Songs from the Public Domain" LilyPond source (github.com/bbloomf/lilypond-songs, `Civil War/Oh! Susanna.ly`,
  dedicated to the public domain). The owner's pitches are kept; the rhythm is now the score's at sixteenth rows.
- "Drunken Sailor": the Wikifonia lead sheet "What Shall We Do with a Drunken Sailor?" in **OpenEWLD**
  (github.com/00sapo/OpenEWLD, Federico Simonetta's dataset of the public-domain lead sheets of the Wikifonia archive;
  its MusicXML files are public-domain content, the rest MIT). The chorus bars 9, 11 and 13 were fixed from it.
- "Funiculi, Funicula": the OpenEWLD lead sheet "Funiculi funicula" (as above) confirms the rhythm (one echo bar
  differs between the two sources; the spec's is kept).
- "Pop Goes the Weasel": the spec's own source, Ryan's Mammoth Collection, as encoded in the **music21** corpus
  (github.com/cuthbertLab/music21, `corpus/ryansMammoth/PopGoesTheWeasel.abc`, encoder John B. Walsh): all bars match.
- "In the Hall of the Mountain King", "The Blue Danube", "The Entertainer": the Mutopia scores listed above confirm them.
- "She'll Be Coming 'Round the Mountain": no score found on GitHub (searched the Mutopia Project, the music21 corpus,
  OpenEWLD, humdrum-tools, KernScores mirrors and public-domain LilyPond songbooks). Its rhythm and pitches are now
  Simon Horn's MIDI (2021, CC0, Wikimedia Commons), supplied by the owner 2026-10-12 (first verse, Harmonica track).
- No score found on GitHub either: "The Skaters' Waltz", "Take Me Out to the Ball Game", "Sakura Sakura" (the Mutopia
  "Sakura-Miyotote" is a different piece), "Galop infernal"; their rhythms are the specs'.
- Not used: The Session's data dump (github.com/adactio/TheSession-data) is licensed ODbL **with an added prohibition on
  processing the material with large language models**, so it is not a source for this project's AI-assisted work.

No score was found (the Mutopia Project has no Offenbach, Waldteufel, Denza or Von Tilzer) for the other tunes; their
notes are the specs'. Seamless loops (2026-10-11): the
last bar of "Oh! Susanna", the Galop, the Ball Game, the Skaters' Waltz, the Mountain King, Sakura and the bonus
loop was changed so the tune flows back into bar 1 (ours; `docs/music_specs.md` "Game loop" notes).

The old original in-game loop and the old title tune (a verse of "Oh! Susanna") were removed.

## Sound effects

Original: simple register-level effects defined in `src/music.c`.

## Art

All pixel art is original, drawn for this project as ASCII sources under `assets/` (nothing is taken from any other
game). That includes the story portraits (`assets/story/portraits/*.txt`) and the four full-screen story pictures
(`assets/story/pictures/*.txt`): the INTRO's square at night before and after the burst (`intro_before`, `intro_a`),
the FINALE's line-up (`finale_a`) and the CREDITS' morning after (`credits_b`). Their Golden Spigot (design F1, and its
ten story pieces), the small Dregs (J2) and the ten owners' heads were drawn for them.

## Tools used, not shipped

RGBDS and GBDK-2020 (build toolchain), PyBoy and SameBoy (testing), Pan Docs (hardware reference).
