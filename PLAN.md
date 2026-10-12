# Spigoteer: plan

(Working title was "Tapper GB". The owner named the game **Spigoteer**; "Tapper" is a Bally Midway
trademark and must not appear in the shipped game.)

A Game Boy / Game Boy Color clone of the arcade game *Tapper*, written in C on
GBDK-2020. It runs on both DMG and CGB, and CGB gets the full-colour art from
`upload/`.

Done for every milestone means `make && make test && make check` pass on DMG
and CGB, and the new behaviour has a test.

## Game rules (from `upload/tapper.txt`)

- There are 4 bars. The bartender stands at the tap on the **right** end.
  Patrons enter on the **left** and walk right.
- **Up/Down** moves the bartender to the tap of the next bar, and wraps from
  the top bar to the bottom one. **Left/Right** walks along the bar.
- **Hold A** at the tap to fill a mug. When it is full, it slides left.
- When a full mug reaches a patron who is paying attention, the patron
  catches it and is pushed back toward the left. A patron pushed back to the
  left end leaves (served; no doors since 2026-10-09: he slides off the screen's left edge). A patron who stays drinks for a while, then sends the
  empty mug sliding right.
- You lose a life when:
  - a full mug reaches the left end without anyone catching it,
  - an empty mug passes the right end before the bartender catches it, or
  - a patron reaches the right end.
- Catching an empty means the bartender's position overlaps the mug on the
  same bar.
- A level is cleared when every bar is empty. New patrons keep arriving on a
  timer until each level's quota has been spawned.
- After a full row is cleared, a patron sometimes leaves a tip. Picking it up
  starts the dancers, and patrons who are distracted ignore mugs and stop
  walking for a while.
- Scoring: serve 50/75/100/150 (depends on the theme), empty caught 100,
  tip 1500, screen clear 1000, bonus win 3000.
- Bonus round: a shell game with 6 cans, one of them unshaken.

## Screen layout (160x144 = 20x18 tiles)

Revised after the owner's first playtest (M4.5–M4.7):

| rows | content |
|---|---|
| 0 | HUD: score, lives, level (one row) |
| 1–4 | stage: back wall with our own bar sign; dancers perform here (M5) |
| 5+3b … 7+3b | bar `b` (0..3): 2 rows of back wall where patrons stand, 1 combined counter row (top + front) where mugs slide |
| 17 | floor |

- Columns 0–17 are the counter (0–1 were the door until 2026-10-09; the wall now runs to the left edge), and columns 18–19 the tap.
- **Patrons are background tiles** (16x16 on a 3x2-tile footprint), pre-drawn
  shifted by 0..7 px (M8b; was 0/2/4/6) so they move in 1 px steps by swapping
  tilemap entries only. This keeps them out of the 10-sprites-per-line budget.
  Colour 0 of each patron BG palette is the wall colour, so the tiles need no
  transparency. Drinking is a mug sprite raised to the patron's face.
- **Tap grace:** A within 16 px of the tap snaps the bartender to it and starts
  a fill; the mug fills visibly in his hand.
- **Sprites** use 8x16 OBJ mode:
  - bartender, 16x24: 4 entries
  - mugs: **1 entry each**. The 16 px mugs in the upload are redrawn 8 px
    wide, so one bar line can hold the bartender plus 8 mugs.
  - breaking glass, tip coin, sparkles
- The global cap is 40 OAM entries: bartender 4, mugs 24 (6 per bar), and
  the rest for effects.
- **CGB palettes:**
  - BG: wall/counter, HUD, 3 patron variants of the current theme, tip.
    That is at most 7 of 8.
  - OBJ: bartender, full mug, empty mug/glass, coin, sparkle. That is 5 of 8.
- On **DMG**, the colour indices are ordered by brightness, so the art reads
  correctly on the grey ramp.

## Themes and levels

The levels use the patron groups from the sprite sheet: cowboys, sports fans,
lumberjacks, chefs, divers, robots, ninjas, aliens, and zoo animals (finale).
Each level is a row in a const table with these fields:

- patron group
- patrons at the start of each bar
- quota
- spawn interval
- walk speed
- push-back distance
- serve score

## Milestones

| # | milestone | proof |
|---|---|---|
| M0 ✅ | GBDK skeleton in place; art from `upload/` extracted to ASCII sources and palettes | `make test check` green; `out/preview/art/*` looks right |
| M1 ✅ | Bar scene: HUD frame, 4 bars, bartender at a tap; moves up/down with wrap and walks left/right; CGB palettes and DMG greys | tests on `bar`, `bartender_x`; goldens `scene` |
| M2 ✅ | Mugs: hold A to fill, release when full to slide; break at the left end; lives decrement; glass animation | tests on `mug_*`, `lives` |
| M3 ✅ | Patrons: spawn, walk, catch, push-back, leave, drink, return empty; bartender catches empties; patron at the end costs a life | tests per rule above |
| M4 ✅ | Game flow: score + HUD digits, death pause and bar reset, level clear, title, game over, level table and themes | tests on `game_state`, `level`, `score` |
| M4.5 | Owner feedback: easier start, tap grace + snap, fill animation | tests, golden `filling` |
| M4.6 | Re-layout: 1-row HUD, stage, 3-row bars | all goldens replaced on purpose |
| M4.7 | Smooth patrons (pre-shifted tiles), drinking animation | tests |
| M5 | Tips and dancers on the stage | tests |
| M6 | Bonus round (can shell game) | tests |
| M7 | Sound effects + music (hUGEDriver, reuse/MIT, attributed), polish | `make check` |

The ROM stays 32 KB with no MBC until it no longer fits. When it outgrows
that, switch to MBC5 (`-Wm-yt0x19`, `-autobank`).

## Owner playtest 2 (queued as M8, after M7)

- Tap grace 16 -> 32 px.
- Bartender faces the tap (right) while filling, holding the mug under a spout that reaches left from the keg; he turns left as he slides it (owner's choice).
- Empties slide back slower: 1 -> 0.5 px/frame (full mugs stay 2).
- Bartender walks slower (2 -> 1.5 px/frame) with a calmer cycle: walk1, idle, walk2, idle.
- Counter runs all the way to the door (cols 0-1); the door shrinks to the wall rows, so patrons never show their missing legs.
- Patrons pre-shifted at every pixel (8 shifts, 144 BG tiles per group) instead of 2 px steps.
- Art (proposals for approval first): bartender mustache; patrons in 3/4 view facing right.

## Owner playtest 2b (also M8)

- Spout from the keg pouring into the mug while it fills.
- A full mug (A still held) can be carried to another bar with Up/Down; releasing A there slides it.
- Faster fill: 24 -> 16 frames.
- Art round 3 (proposals in the session scratchpad, owner approves before import): balanced mustache; cowboy without far ear; sports fan redesigned (the foam finger was later removed by the owner); slot B of every group except zoo is a woman; all patrons 3/4 view facing right.

## Owner music notes (queued after the perf pass)

- Gameplay track: "Oh! Susanna" (Foster, 1848, PD) per the owner's spec (key C, 2/4, ~120 bpm,
  pickup + A A' A A' + chorus + ending; boom-chick bass on ch3; kick/snare verses, hats in chorus).
  Melody on ch2 because ch1 carries SFX.
- Title track: "The Entertainer" (Joplin, 1902, PD), opening A theme, ragtime bass.
- Show music: "Galop Infernal" (Offenbach, 1858, PD, the can-can) plays during the dancers' show,
  then the gameplay track resumes.

## Dancers turn heads (M8)

Distracted patrons turn toward the stage: on show start each distracted patron shuffles (<= 4 px)
to the nearest 8 px column and switches to a back-view frame (only stationary, so only shift 0 is
needed: 3 variants x 4 tiles = 12 BG tiles per group). Back-view art: <group>_back.txt.

## Fair empties (M8, owner request)

Never make it impossible to catch every returning empty. A patron who has finished drinking
holds the empty until sending it keeps arrivals at the tap spaced apart: its predicted arrival
time ((tap_x - x) / empty speed, in frames) must be >= last scheduled arrival + EMPTY_GAP.
EMPTY_GAP comes from the level table, shrinking with level (about 120 frames at L1 to a floor of
~45 frames), never below what an instant bar switch plus a short walk needs. Spacing by arrival,
not by throw, because a patron near the tap throws later but arrives sooner.

## Themed venues (owner request; art in progress, wired in M9 after M8)

Per level theme: a stage (20x4 tiles, <= 20 unique tiles loaded over the stage tile ids at level
start, <= 2 CGB palettes), a bar palette (wall/counter, no door: the wall's speck pattern runs to the left edge; wall = colour 0 behind patrons), and
a drink replacing the mug (10 OBJ frames: full, empty, 4 fill, 4 drink poses, loaded over the mug
tile ids; own full/empty OBJ palettes). Saloon/beer (original TAPS stage + curtains), stadium concession/soda, lumber lodge/coffee,
bistro/wine, igloo/cocoa, robot factory/oil can, teahouse/green tea, space lounge/glowing
beaker, jungle zoo/coconut.
Themed shows: the dancers' 32 OBJ tiles are reloaded per theme (3 performers, 16x24, 4 frames):
can-can (saloon), cheerleaders (sports), Sasquatch (lumber), plate-spinning waiters (bistro),
penguins (igloo), breakdancing robots (factory), taiko drummers (teahouse), alien band (space),
flamingo chorus line (zoo).
Show music per theme (all public domain): teahouse "Sakura Sakura" (traditional), igloo "The Skaters'
Waltz" (Waldteufel, 1882), sports bar "Take Me Out to the Ball Game" (Von Tilzer, 1908); every
other theme plays the "Galop Infernal". Show tunes are short loops (~8-12 s) for the 6 s show.
REVISED (owner chose venue theme songs): each venue has its own public-domain gameplay tune;
every show plays the "Galop Infernal". Saloon "Oh! Susanna" (owner's spec); sports bar "Take Me Out
to the Ball Game"; lumber lodge "She'll Be Coming 'Round the Mountain"; bistro "Funiculi,
Funicula"; igloo "The Skaters' Waltz"; robot factory "In the Hall of the Mountain King"; teahouse
"Sakura Sakura"; space lounge "The Blue Danube"; jungle zoo "Pop Goes the Weasel"; title "The
Entertainer". (Proposed to the owner; non-owner picks may still change.)

## Rename (done in M8c)

Title screen logo "SPIGOTEER" (own lettering, wider than today's TAPPER: 9 letters), cartridge
header title SPIGOTEER, credits/README text. The saloon's TAPS stage sign stays (it's the
bar's name, not the game's). Idea: bartender pouring from a spigot under the logo.

## Music as built (M7 revisit)

Done: title "The Entertainer", "Galop infernal" for every show, ten venue tunes since the 10th venue (table in CREDITS.md; tune
index TUNE_VENUE0 + patron group), jingles unchanged. hUGEDriver only reads patterns through plain pointers in
the bank it runs from, so song patterns live in ROM bank 10 (bank 3 until music step 2) and src/music.c copies a song into WRAM (buffer A:
title or venue tune; buffer B: the show tune, copied once in the background) a slice per frame before it
starts; bank 2 keeps the driver, order tables, instruments and jingles. Sources: tools/songs.py; pitch check:
tools/check_music.py (routes one channel to the output and prints expected vs detected pitch).
Caveat: the melodies were written from memory and nobody has listened to them; the owner's Oh! Susanna and the
given Entertainer note list are exact, the rest (especially the Galop, Funiculi, the later phrases of the
ball-game and mountain tunes, Skaters' Waltz, Blue Danube) are best-effort and need an ear check.
Music step 1 (2026-10-11): The Entertainer and the Blue Danube checked note by note against Mutopia Project scores
and corrected (the Danube now in the score's C major); no score found for the others (notes unchanged). Every
looping tune flows back into bar 1 (last bars of Susanna, Galop, Ball Game, Skaters, Mountain King, Sakura and the
bonus loop changed); tests/test_music_loops.py keeps the melody silence at the loop point <= 0.25 s.
Owner verdict on step 1: the Entertainer and Blue Danube fixes sound right; Sakura (lively, 150 bpm) approved as is.
Music step 2 (2026-10-11, the owner's listening notes):
- Dead air at the loop (Oh! Susanna "cuts off and goes dead"): gen_music wrote D00 as the pattern break on the last row
  of a tune that ends inside a 64-row pattern, but hUGEDriver stores the break row plus one (row_break 0 = no break),
  so D00 did nothing and the last pattern ran on through its empty rows: Susanna 32 rows (8 s) of silence, Funiculi
  42 rows, Weasel 32, Sakura 16, the bonus loop 16, before the loop. Now D01 (gen_music.BREAK_TO_ROW0); the notes
  are unchanged, and the ending (C on "knee", then the C D pickup) leads straight into bar 1. Tests: every short
  tune has D01 on its last row; in the ROM Susanna's last order stops at row 31 and order 0 row 0 follows.
- Halting sung phrases ("Su-san-na", "She'll be com-ing"): the song lead's envelope (NR12 0x85, half volume after
  0.39 s) made every note a plucked syllable that died away before the next, loudest where a pitch repeats, plus a
  1-frame cut before each repeat. songs.song(legato=n): the melody plays on the legato lead (instrument 6, NR12 0x60:
  volume 6 held, no envelope; melody RMS 3.0 vs 3.35 / 3.09 before), notes of different pitch run into each other,
  a repeated pitch is cut n = SUNG_ARTIC = 3 frames early (heard as a new syllable), a note before a rest still
  stops at the rest. On for Susanna and Mountain only; the other tunes' patterns are byte-identical except the D01.
- The Entertainer: A section (second ending: C, E F F# up) + B section (score bars 22-36 and the second ending
  bar 38, D D# back to bar 1), 32 bars = 34 s, from the same Mutopia score. Buffer A 6 -> 8 patterns (WRAM +384 B,
  ~1 KB left above the stack's measured use). The pattern blobs moved from bank 3 (39 B free) to bank 10
  (gen_music.BLOB_BANKS, build/music_pat10.c: 12288 B, 4 KB free); the autobanker refilled bank 3 with banked code.
- Title tune hitch at the attract switches (title -> top-5 table -> title): each switch is an LCD-off load inside
  one main-loop pass and the music ticks once a pass, so the tune stood still ~9 frames into the table (six_digits:
  12 SDCC 32-bit divisions per score, ~1 frame each score) and ~12-15 back to the title (tiles, venue, backdrop).
  save.c split6 (powers of ten, no division) for the table; music_pump() (music.c) between the load steps of
  title_enter, scores_table / screen_begin, load_venue and venue_backdrop ticks the music when the timer (TAC 4096
  Hz, polled, no interrupt; music_tick zeroes TIMA) says a frame (69 counts) has passed. Now the tune never stands
  still more than 2 frames (test_sound). hi_pick keeps its division (a faster one shifts the debug_story golden by
  a lag frame). The mini-game retry's reload is a frame longer on CGB (10) with the music ticking through it.
- Extra-life cue (owner request): SFX_EXTRA, the ninth effect (sfx_req widened to 16 bits; sfx_count +1 byte), played
  by story.c extra_life when a life is really added (not at four lives): C6 E6 G6 C7, G6 C7, G6 C7 held, 33 frames on
  channel 1 (25% pulse, NR12 0xD2), the effects' channel, so the music plays on; while it sounds no other channel-1
  effect cuts it (sfx_start). Test: tests/test_arcade.py (DMG + CGB). Bank 2: 30 B free.
- tools/check_music.py: the LEVEL harness starts at level g + 1 for venue g (the old level-clear trick reached the
  wrong venue for even groups since the 10th venue); a staccato note is measured over the part that sounds.

Music step 3 (2026-10-11, rhythm; owner: "comin'" and "the mountain" are bunched when sung, "Oh Sue-zan-uh" is not four
even notes): the specs were written in even eighths/quarters without a score, and the grids were too coarse for a dotted
eighth. Every melody's rhythm was compared with a public-domain score on GitHub where one exists (sources in CREDITS.md
"Rhythm audit"; The Session's data dump is not used: its licence forbids processing with LLMs).
- Oh! Susanna: Foster's rhythm (humdrum-tools/foster-songs fostr20.krn, Dover's Foster Song Book): sixteenth rows (8 a
  bar of 2/4), 8 frames/row = quarter 112.5 (was 15/eighth = 120; the score says MM 114); 96 -> 192 rows = 3 whole orders
  (no pattern break), blob 6 -> 7 patterns. Sixteenth pickups, dotted "with my ban-jo" / "Lou'-si-an-a", the chorus
  "Oh! Su-san-na, oh" = q q | e q e (the owner's list lacked the third A), bar 16 a quarter and a quarter rest.
- Round the Mountain: no score found anywhere on GitHub; sixteenth rows (16 a bar), 6 frames/row = quarter 150
  (GAME_BPM; spec 160 = 5.6 frames; was 11/eighth = 163.6), 128 -> 256 rows = 4 orders, blob 5 -> 8 patterns (buffer A
  stays 8). Rhythm from the owner's description: "com-in' round the" X:2 X:6 X:6 X:2, "moun-tain when she" X:3 Y:5 Z:4
  W:4; stressed syllables stay on beats 1 and 3. Needs the owner's ear.
- Drunken Sailor: chorus "Hur-ray and up she ri-ses" = q, dotted e, s (bars 9, 11, 13; OpenEWLD lead sheet).
- Confirmed by a score: Entertainer, Blue Danube, Mountain King (bars 1-12, Mutopia), Weasel (Ryan's, music21 corpus),
  Funiculi (OpenEWLD; one echo bar differs between sources, kept). No score found: Skaters, Ball Game, Sakura, Galop.
  Jingles are ours. Legato switch unchanged (sung tunes, 3-frame break before a repeated pitch); loops seamless.
- Bank 10 blobs 12288 -> 13056 B (3328 free); bank 2 30 -> 6 B free (two more orders); WRAM unchanged.
- tests/test_perf.py assert_music_every_frame: a tune that restarts at 0 while the previous sample was 0 too (the
  bigger Susanna blob moves the level-1 load by a frame) counts as a restart.

Drums and game tempos (after M9): owner-approved game tempos (tools/songs.py GAME_BPM; spec tempo stays in docs/music_specs.md):
entertainer 8 frames/row = 112.5 bpm, sakura 12 = 150 (lively arrangement, owner-approved 2026-10-11; was 15 = 120), funicula 11 = 109 (dotted quarter), skaters/danube/ballgame 9 = 200.
Drums for the title, ballgame, funicula, skaters, sakura and danube are a `groove` (songs.py song(..., groove=)): a 6-8
row loop in bank 2 that src/music.c's groove_tick plays on channel 4 in step with the driver's rows (kit registers derived
from the quiet kit in gen_music.drum_kit); a sound effect on channel 4 wins. A shared hUGEDriver pattern would not do: 64
rows is not a whole number of 3/4 or 6/8 bars, so the beat would shift at each order, and the 32-bar tunes fill the
6-pattern buffer A. WRAM cost 4 bytes; the jingles now share empty_pat (bank 2 gained ~130 bytes net free).

Mix (owner: the melody drowned the bass and drums): bass wave NR32 0x40 -> 0x20 (100% output) with the triangle's samples
scaled to half range (gen_music.BASS_AMP 0.5, 4..11) so it stays smooth; song lead 0xA5 -> 0x85, lead 0xA3 -> 0x83, soft lead
0x93 -> 0x73, plink 0xC1 -> 0xA1; thin stays 0xC1 (was 0x91, raised so the bonus melody leads the louder bass); quiet drum kit
6/5/4 -> 8/7/6 (the groove kit follows). Measured per channel with PyBoy (RMS, int8 scale): melody 4.3 -> 3.4, bass 2.5 -> 3.8,
drums 0.9 -> 1.5. tests/test_sound.py pins the registers. Effects (channel 1 volume 8-12, noise 9-13) stay above the melody.

Music step 5 (2026-10-12, owner: "use the silent channel 1 for music: a harmony line / counter-melody on every tune that steps
aside whenever a sound effect needs channel 1 and comes back cleanly afterwards; effects stay louder and are never cut"):
- Engine: hUGEDriver does NOT play channel 1. Each order would need a fourth WRAM pattern (192 B): buffer A (8 patterns)
  would grow to 12 (+768 B of the ~930 B of WRAM left), the show buffer by one. Instead a tune's harmony is a compact
  event list, 2 bytes an event (note | 0x80 for instrument B, rows), with a 4-byte header (duty and envelope of two
  instruments) and a 0 0 end, in bank 10 next to the pattern blobs (gen_music.harm_bytes, harm_<tune>; harm_tab[] in
  bank 2), played by src/music.c harm_tick after the driver's tick, in step with its rows like the groove (it follows
  hUGE_ticks_per_row, so music_fast too). The driver's channel-1 mute bit stays set while a tune plays (set directly at
  start_song: no note cut), so only harm_tick and the effects write channel 1. An event is read through harm_peek
  (src/musicload.c, ROM0: two bytes from bank 10); periods come from the driver's own note table (exported as
  hUGE_note_table, CREDITS.md). 1036 B of harmony for the 12 tunes; bank 10 13056 -> 14092 B (2292 free); WRAM +11 B.
- Yielding: while an effect owns channel 1 (voice[0].busy) harm_tick writes nothing, so an effect is never cut. A
  channel-1 effect now ends with NR12 0x08 + trigger (volume 0, DAC on) instead of NR12 0 (DAC off), and a harmony
  rest does the same, so channel 1's DAC never switches (no click; NR52 bit 0 stays set). When the effect ends, a
  harmony note with more than a row to go is struck again on the next frame, otherwise the next event brings the voice
  back. Cost: up to 2 lines more on a row's first frame (PyBoy, LY at music_tick's entry and exit: title 11 -> 13).
  The realistic peak's DMG missed-frames guard went 150 -> 165 (158 measured; P6 plus 12 dummy register reads in the music
  tick gives the same 158: the scenario's timing spread).
- Instruments (gen_music.HARM_INST), all volume 5 against the melody's 8 (legato 6) and the effects' 8-12: "harm" 25%
  0x57 (slow decay), "pad" 12.5% 0x50 (held), "stab" 25% 0x52 (quick decay), "pluck" 12.5% 0x55.
- Arrangement: tools/harmony.py (follow: a voice a third / sixth below the melody, at most one note a grid step;
  guide: one held chord tone a chord or bar, third or seventh first, nearest to the last; stabs: off-beat chord tones),
  from each tune's own chords (*_CHORDS in songs.py, the score sources there), in key, no second / seventh / tritone
  against a melody note on a beat (a dominant seventh's own tritone allowed), little unison. Per tune in songs.py.
- Mix (PyBoy RMS, one loop per tune, int8 scale): harmony 1.0-1.65 against the melody 2.7-3.5, bass 3.6-4.0, drums
  1.3-2.0 (melody, bass and drums unchanged). Tests: tests/test_harmony.py (the lines against their tunes, the format,
  the instruments' volumes; in the ROM: the harmony on channel 1, an effect's registers held for its whole length, the
  harmony back after it, NR12 never 0, channel 1 under channel 2); tools/check_music.py --channels 1 checks its pitches.

## M8b as built

Approved art imported (assets/art is now the source of truth; tools/extract_art.py refuses to overwrite it
without --force). Patrons: 8 shifts x 3 variants x 6 tiles = 144 BG tiles + 12 back-view tiles per group,
one generated file per group (build/patrons_<g>.c, autobanked; build/patron_load.c switches banks). BG ids:
scene 0-89, patrons 90-233, back views 234-245 (246 of 256; BG in the signed 0x8800 mode, OBJ ids < 128,
both checked by #error in game.h). A 1 px step within a patron's own 3 columns is a "quick" redraw (6 tile
ids copied from a ROM0 id table, no compose) — walking at every pixel would otherwise have cost ~6 lines
of frame time. Distracted patrons shuffle (<= 4 px, 1 px/frame, never into PATRON_SPACING, never onto the
tap end) to a multiple of 8 and show their back view (patron_draw bit 7 = DRAW_BACK, mirrored in
patron_facing[]); a patron who cannot get there keeps facing the bar until the show ends.

## Owner playtest 3 (M8c, after M8b)

- Show lasts one Galop loop (~576 frames, 9.6 s) instead of 360.
- Thirst: each patron counts drinks; push-back distance = pushback_px x (drinks so far, starting at
  1), so the 2nd drink pushes twice as far and the 3rd three times; clumps break up.

As built (M8c): SHOW_FRAMES 576; patron_drinks[] (reset in add_patron) scales the push-back (pushback_px x drinks,
capped at 255 px). Title logo SPIGOTEER: assets/tiles/title.txt, 8 letters x 4 tiles generated from stroke shapes,
loaded over the patron tile ids by enter_title (the level load's load_patron_tiles restores them); BAR_TILE_COUNT
dropped by the 20 old title tiles, so BG ids in use are now 70 scene + 156 patron = 226 of 256. Header title SPIGOTEER.

## M9 as built (themed venues)

Art: assets/approved/venues/<theme>_* (owner-approved). tools/gen_art.py cuts each theme into build/venue_<theme>.c
(one autobanked file: stage/bar tiles, 20x4 stage map + attributes, 20x3 bar map + attributes, floor id, 20 drink OBJ
tiles, 32 show OBJ tiles, 7 palettes), build/venue_load.c (venue_fetch: far_copy of the theme's venue_t into WRAM) and
build/venues.json (the tests' reference); the build fails if a theme's stage needs more than 20 tiles or its bar +
floor more than 16. Theme index = patron group (saloon 0 ... zoo 8). BG ids: venue stage slot 0-19, venue bar slot
20-35 (since the graphics overhaul one pool 0-35, see "Graphics overhaul as built"), shared HUD tiles 36-71, patrons 72-215, back views 216-227 (228 of 256); title lettering still loads over the
patron range on the title only. OBJ: the drink loads over the mug ids (56-59 full/empty, 76-83 fill, 84-91 drink),
the performers over the dancer ids (96-127). CGB BG palettes: 0 bar, 1 HUD, 2-4 patrons (colour 0 = the venue's wall),
5/6 stage A/B, 7 bar B (keg/spout). src/venue.c (banked): load_venue (tiles, palettes, base_tile/base_attr that
render.c restores under patrons), draw_venue (stage, counters, floor), venue_backdrop (title in the saloon, bonus
round in the venue just played). The breaking-glass shards stay the generic ones in every venue.

## Owner playtest 4 (queued)

- Difficulty: flatter curve. Level 6 should play like the old level 3, level 9 like the old
  level 5; speed plateaus there. Ramp spawn rate, start patrons, push-back and empty_gap gently too.
  (After M8d, which touches the same code.)
- Music: game tempos (Entertainer 112, Sakura 120, Funiculi 112 dotted q, Skaters 192, Danube 192,
  Ball Game 192) and drums back on every tune (shared drum pattern). Galop: waiting for the
  owner's spec; the current one was written from memory and sounds wrong.

## Door fix (queued after the difficulty pass)

Patrons spawn at x = 16 (right of the 16 px door) and leave (served) when pushed back past x = 16,
so they never overlap the door tiles. Door swings: a short open/shut tile swap per venue if the
bar tile slot has room, otherwise a small dust-puff sprite at the doorway on enter/leave. Walk
speeds rescaled so crossing times are unchanged (level-1 crossing still >= 15 s).

## Modes, title, story, bonus rounds (owner, 2026-10-09)

Owner's picks: story premise "The Golden Spigot"; new bonus rounds Perfect Pour and Tip Shower;
title animation = logo fills with foam, then a bar-scene loop below it; arcade extras = top-5
table with initials + loop banner/harder loops.

| # | milestone |
|---|---|
| M10a | Title menu: no stripe bands, all text centred; ARCADE / STORY / MUSIC ON-OFF with a mug cursor. Animation: logo fills with foam letter by letter (drips, bubbles), then a loop below it: bartender slides a mug to a patron who drinks and sends it back. |
| M10b | Arcade mode: endless loop of the venues (ten since The Chrome Cow); "LOOP n" banner; each loop a bit harder up to a ceiling; top-5 high scores with 3-letter initials in SRAM (replaces the single hi score). Done (see M10b as built). |
| M11a | Story script: "The Golden Spigot" - the legendary spigot that pours any drink shattered into 9 pieces; each venue owner gives one to a bartender who keeps their crowd happy. Written as docs/story.md for owner approval before any code. |
| M11b | Text engine + full font + cut-scene system (still picture + portrait + text box, A to advance), chapter goals per venue (serve N, no broken glass...), venue twists, save/continue in SRAM. ROM likely grows to 256 KB. Part 1 done (see M11b story engine as built); the twists are part 2. |
| M11c | Story art: portraits (Spigoteer, the venue owners (ten with Granny Throttle), villain if any), cut-scene pictures. Owner approves. |
| M11d | Story shifts: each chapter plays its venue as Opening shift, Happy hour, [mini-game slot], Last call, [boss slot]; per-shift goals, speeds and arrival patterns; retry one shift; SRAM v4 with the step reached. Done (see Story shifts as built). Then the owner's lives rule: 3 lives per venue, a venue restart, strict rules cost 2, the gold-medal life API (see Story lives as built). |
| M11e (in progress) | The story's mini-games and bosses (filling the two slots of every chapter's sequence), a Practice mode (replay any reached shift / mini-game / boss, with best scores), and the Pour-Off. Design in docs/minigames_bosses.md. Step 1, the mini-game framework with a stub game, is done (see Mini-game framework as built); the mini slots stay NOT_BUILT until real games exist. Step 2, the boss engine + Big Tex on placeholder art, is done (see Boss engine as built); the saloon's boss slot is on in the story, the other venues' stay NOT_BUILT. Step 4 has begun: the Sasquatch, the Food Critic and the Yeti are built (see Boss hooks as built and the three bosses after it), each boss in its own banked file. Step 3 has begun: Quick Draw (the saloon) is built and plays in STORY and ARCADE, and the title's BONUS > MINI GAMES is the Practice list for the built mini-games (see Quick Draw and BONUS > MINI GAMES as built). Next: Order Up!, Battery Sort. |
| M12 | Bonus rounds: Perfect Pour (hold A to fill to the line; foam keeps rising) and Tip Shower (catch coins in a tray, dodge tomatoes); rotate with the shake-up. Shake-up lose result: soda geyser up, droplets everywhere. Done (see M12 as built). |

## M12 as built (bonus rounds)

- Rotation: `bonus_kind = (bonus_round - 1) % 3`: 1st shake-up, 2nd Perfect Pour, 3rd Tip Shower, again. The shake-up's
  swaps and speed count shake-ups ((bonus_round + 2) / 3), not rounds. The new rounds are `src/bonus2.c` (banked);
  `bonus.c` hands over. Every round ends in `bonus_phase` 4 for 130 frames, so one poke ends any round in the tests.
- Both use the venue backdrop, a two-row banner (rows 2-3, HUD colours) with the name and "FILL TO THE LINE" /
  "CATCH THE TIPS" for 1.5 s, OBJ tiles 96-127 (performers), BG ids from 72 and BG palette 2 (patrons), OBJ palettes
  6-7; the level load restores all of them. DMG: Tip Shower sets OBP1 to 0xE0 and puts 0xC4 back at the end.
- Perfect Pour: a 16x40 glass on the BG (interior colour 0, solid 8 px base); the beer and foam are sprites drawn behind
  BG colours 1-3, so they show only inside the glass, and the 1 px fill line (BG colour 2) stays visible over them.
  Hold A: 1 px of beer every 4 frames with a 3 px head; release: the head rises 4 px more (1 px / 8 frames). Final
  level vs the line: +-1 PERFECT 3000, +-4 GOOD 1500, past the 32 px rim SPILL (foam heap over the rim, streaks down
  the outside), else TOO LOW / TOO HIGH. Three glasses, each line different (six heights, 12-27 px). Max 9 sprites a line.
- Tip Shower: tray (24 px, 3 entries) over the bartender's head, 1.75 px per frame; at most 7 falling items (coins
  25% tomatoes, 0.75-1.75 px per frame, new one every 14-29 frames) so no line passes 10. Coin on a clean tray +100;
  a tomato dirties the tray for 60 frames (no catches, no life lost). 20 s timer, "TIME UP / BONUS nnnn". No counter row.

## M10b as built (arcade mode)

- Loops: after level 9 the venues come round again; level L plays venue (L - 1) % 9 with that row of the level table,
  in loop `arcade_loop` = (L - 1) / 9 + 1 (level 10 = saloon, loop 2; 19 = loop 3; the HUD keeps counting L10, L11...;
  the level number still stops at 99). Before the first level of loop 2, 3, ... the window banner "LOOP n" shows for
  120 frames in its own state (GS_LOOP = 8): the level is drawn, nothing moves, then the level's usual 90-frame intro.
  Bonus rounds keep their rule (after every even level) and rotation.
- Difficulty per loop k = min(loop - 1, 3) on top of the row (main.c start_level): walk speed + 10 % per loop (cap +30 %,
  patron_speed; step_frames stays the row's), spawn interval - 8 % per loop (cap -24 %), empty gap - 5 frames per loop
  but never below 80. Quota, start patrons, push-back and serve score stay the row's. So level 10 (cowboys, loop 2) is
  easier than level 9 again, arcade style; loop 4 and later play the same (the ceiling). Before M10b, levels past 9
  used the level-9 row's speeds; tests/test_art.py goto_group now reaches even groups as level g + 1 (from the bonus
  round's last frame) instead of g + 10.
- Top 5 (src/save.c, now autobanked): SRAM version 2 = "TPR2", 5 x (3 initials A-Z / space, 3-byte LE score <= 999999),
  best first, checksum (0x5A + bytes 0..33) and complement at 34/35. Loading checks signature, checksum, letters,
  range and order; anything else is an empty table. A valid version-1 save ("TPR1") becomes entry 1 as "SPG" and is
  written back as version 2 at boot (`save_migrated` = 1). WRAM working copy: top_names[15] + top_scores[5] (35 B);
  hi_score / hi_digits mirror entry 1 (the title's HI line). A tie goes below the older entry; 0 never enters.
- Game over: the score goes into the table at once as "AAA" and is saved (`new_rank`, 5 = no entry); the GAME OVER
  banner goes on after START / A or 240 frames: to the initials (GS_INITIALS = 9) if it made the top 5, else the table
  (GS_SCORES = 10). Initials: Up / Down step A..Z, space (wrapping), Left / Right move (wrapping), A or START saves and
  shows the table. The table: 5 s or A / B / START, then the title.
- From the title: 20 s (1200 frames) without a key shows the table (attract style; the M10a menu is unchanged), then
  the title again (the logo animates afresh, the title tune plays on).
- Screens (src/scores.c, banked): the HUD style, full screen: the dark band, a panel line at rows 1 and 16, HUD glyphs
  centred ("HIGH SCORES" row 3, entries "1 ABC 012345" rows 6-14; "NEW HIGH SCORE" row 3, the score row 5,
  "ENTER INITIALS" row 8, the letters at columns 8/10/12 of row 11, a cursor bar under the current one on row 12).
  bar.txt gained J, Q, X, Z and the cursor bar (BAR_TILE_COUNT 72 -> 77: the patron range is 77-232, the title's
  limit follows it, the puff's OBJ tiles moved to 234).

## M10a as built (title screen)

- `src/title.c` (banked, own bank with its art from `build/title_art.h`); `main.c` only calls `title_enter()` /
  `title_update()` / `title_music_toggle()`. ROM_0 went from 640 to ~1.3 KB free.
- Layout: logo rows 2-3; menu ARCADE row 6, STORY row 8, MUSIC ON/OFF row 10, HI row 12; the bar scene on bar 3's
  rows (14-15 wall, 16 counter). Rows 4-13 are the plain wall colour (no specks, no bands).
- Text: `tools/gen_art.py title_art()` pre-renders each menu string from the HUD glyphs with a 1 px drop shadow; an
  odd-length string is drawn 4 px right inside one more tile, so every line is centred to the pixel (STORY,
  MUSIC OFF, COMING SOON included). The HI line is a small two-letter "HI" tile + space + 6 muted digits (8 tiles).
  CGB: own text palette (cream on the saloon wall, dark shadow), the selected line gold; DMG: black text, grey shadow.
- Logo: 5 fill states per letter (empty outline, 4 / 8 / 12 px of beer with a foam band and a frothy head, final
  art); letters start 8 frames apart, 4 frames per state; drips under P, O and the second E; one sparkle sweep.
- Scene: the bartender (sprites, bar 3) slides a saloon mug to a cowboy patron (BG tiles), who drinks, winds up and
  sends the empty back; ~4 s loop. Bubbles rise past the logo every 1-2 s. At most 4 sprites on any line.
- BG ids on the title: menu text over the venue stage slot (0-19) and after the fill states; lettering, fill states
  and patron over the patron range (72-225). OBJ effects over the show performers' tiles. The level load restores all.
- Story: "COMING SOON" over the STORY line for 60 frames (the story mode is M11).

## Story art decision (owner): hybrid

FULL custom pictures only for the intro (KA-SPLOOSH), the finale (first pour) and the credits gag;
every other scene uses the LIGHTER style (the venue's in-game stage + bar as the backdrop, the
Spigoteer's normal sprite, a framed speaker portrait above a full-width 3x18 text box; 56x56 since the portrait study,
see "Story portraits as built"). Portraits for every speaker (assets/story/portraits/*.txt).

## Overlapping patrons (M13, owner 2026-10-09)
Patrons must overlap and pass, as in arcade Tapper; one patron shoving another is rejected (the interim
"chain shove" stall fix was dropped). Design, measurements and owner decisions: docs/overlap_design.md.
Owner decisions: occasional hurried patron (~1 in 4 from L3, ~1.5x); redraw the igloo door for the door
entrance; CGB frees palettes both ways (coin shares with the show AND glass/puff use the drink palette);
DMG glass shards may swap light/white. Steps: M13a plumbing (pixel-identical lift), M13b rules, M13c door.

## M13a as built (lifted-patron plumbing; no rule changes)
- Tiles (Option A): each patron group is stored column by column from PATRON_FIRST_TILE = 78 (BAR_TILE_COUNT rounded up
  to even; id 77 is unused in play), shifts 1-7 first (v * 42 + (s - 1) * 6), the shift-0 poses last at 204/210/216
  (PATRON_SHIFT0_OFS 126), back views 222-233 as before. render.c stamp3 / put_col / id_seq / stamp_tile and title.c's
  scene patron follow the layout; the puff stays at OBJ 234.
- State (src/lift.c, bank 5): patron_lift[16] (0 BG, 1 OBJ, 2 OBJ behind BG, | 0x80 dropping), lift_n[4], lift_total;
  test hook lift_hook_p / lift_hook_op (1 lift, 2 lift behind BG, 3 drop) / lift_hook_res (1 done, 2 refused).
  lift_frame() runs only while someone is lifted or the hook is set; draw_lifted() fills OAM 25 down; draw_mugs ends at
  26 - 2 * lift_total. A lifted patron's BG footprint is plain wall drawn with his own palette's colour 0 (PATRON_BLANK,
  the 3rd column of his shift-0 pose), so the wall's specks stay hidden and the picture does not change.
- Ordering: a lift writes the sprite and queues the BG erase at the head of the frame's copy list (bg_urgent: up to two
  3-column spans outside the budget), so both reach the screen in the same VBlank; never while vq_held or his BG copy
  is pending. A drop queues the BG stamp first and keeps the sprite until it is out (>= 1 frame). A forced drop (more
  than 10 objects estimated on the bar's patron lines, or mugs + lifted entries > 19 of 21) swaps BG copy and sprite
  in one VBlank when this frame's list can take it, else it is an ordinary drop.
- Palettes: CGB OBJ 2 = glass + puff (the venue's empty drink), 3/6/7 = patron variants, 5 = show or coin (render.c
  pal5_check asks, the VBlank handler writes), 4 spare; bonus2 loads its tap palette into 3 and the coin into 5.
  DMG: OBP1 = 0xE4 in play (0xC4 on the title / bonus), sliding mugs, held empty and puff on OBP0 from bit-plane-swapped
  copies at OBJ 240-251 made at level load; glass shards on OBP0 with light grey and white swapped (accepted).
- start_level() and the level table moved from main.c to src/level.c (bank 5): ROM0 had no room for M13a.
- Known for M13b: on DMG the lower X wins between sprites, so a lifted patron covers a mug / the bartender to his right
  where both are opaque; on CGB the coin (OAM 27) and puff (26) are behind lifted patrons.

## M13b as built (the overlap rules)
- Rules (src/patrons.c): `push_px` no longer stops behind anyone: every caught mug moves the catcher back his full
  push-back (pushback_px x drinks) unless he goes out through the door (the owner's stalled clump). Walkers pass slower
  walkers and drinkers: `walker_pixel` waits only when the step from a multiple of 8 would take him into a tile column
  two other patrons already cover (`col_scan`). Real columns: c = draw >> 3, c + 1, and c + 2 unless at shift 0 or in a
  back view. Spacing rules reviewed: blocked_ahead is gone; the spawn check keeps PATRON_SPACING clear of the door
  (M13c changes it); the show shuffle (`watch_step`, now in src/show.c) may land next to or on walkers but never on
  another watcher (neither can be lifted) nor make three in a column; `start_show` does not distract a walker who shares
  a column with a watcher already.
- Speeds: `patron_hurry[16]`, `hurry_speed` = patron_speed x 1.5 (after the arcade loop's +10 %/loop, so loops and
  caps apply). From level 3 (loops included) `try_spawn` makes 1 in 4 spawns hurried (`next_rand() & 3`, drawn only
  when hurry_speed != 0: levels 1-2 keep their random sequence). Start patrons never hurry.
- Retune (src/level.c): the step column of levels 3-9 is x 12/11 so the average door-to-tap time is unchanged
  (3/4 at v and 1/4 at 1.5 v average 11/12 of a v walker's time): 59 58 57 56 53 51 48 -> 64 63 62 61 58 56 52; a hurried
  walker then walks like step 43 (L3) .. 35 (L9). Levels 1-2, quota, spawn, push-back and the empty gap are unchanged.
  Not compensated (playtest): passing (a walker no longer queues behind a slow one) makes a crowded bar a little harder.
- Chooser (src/lift.c, bank 5): runs for a bar when `ovl_touch` (a patron whose footprint meets another's changed
  columns or grew from 2 to 3 real columns), a drop, the show or a waiting lift asks (ovl_dirty). Greedy left to
  right over the BG patrons sorted by column; a pair sharing a real column lifts the higher priority one (pushed 4 >
  hurried walker 3 > walker 2 > drinker 1; never a watcher, a back view or one being dropped; ties: the right one).
  Lifted patrons stay up while they cover a BG patron and drop after LIFT_CLEAR_FRAMES (8) clear frames (and x >=
  DOOR_X). A lift now also works on the frame the patron moved: the urgent span is c-1..c+3.
- Fallback (budgets: LIFT_MAX 4, LIFT_PER_BAR 2, mugs + lifted entries <= 19, <= 10 objects on the bar's lines; or this
  frame's copy list): the pair stays on the BG, the would-be lifted one has OVL_TOP (drawn last; the bar is composed in
  two passes), the covered one OVL_SHARED (no quick redraw), a shift-0 patron whose empty 3rd column lies on another's
  figure OVL_TWO (stamps 2 columns, no quick redraw); a TOP patron at shift 0 also stamps 2 columns. Retried next frame
  (copy list) or 16 frames later (budgets). Flags that change make their columns composed again.
- DMG held-mug clamp (src/mugs.c `draw_held`): a lifted holder's mug at dx 8 (16 in the last throw pose) on DMG.
- Catching unchanged (rightmost catcher whose 16 px contain the mug); fair empties unchanged.
- Cost: on the Game Boy one line is 114 machine cycles, and an SDCC loop over 16-20 slots costs 5-15 lines whatever it
  does, so the per-frame loops are hand-written: `lifted_scan`, `est_mugs` (cached until mugs_live / mug_events move),
  `draw_lifted_asm`, the chooser's `gather_asm` / `choose_asm`. The chooser looks at one bar only on a frame past line
  48, at none past line 80 (at least every 4th frame), the rest next frame. `queue_bar` charges 8 more units per patron
  beyond 2 on a bar (composing stamps them all). ROM: show.c (start/end_show, watch_step, place_start_patrons) moved out
  of ROM0 (autobanked); ovl_touch is banked; ROM0 ends at 0x3E18 (488 B free by the map; romusage says 829), bank 5 ~80 B free.
- GBDK vsync race (the M13a worst-case-pile spike, 182/187 -> 218/223): not M13a's code. GBDK's wait_vbl_done clears
  its flag then halts; a VBlank interrupt between the two sets the flag before the halt and the CPU sleeps until the
  next interrupt (the banner LYC at line 86). M13a's pile had one frame ending at line 143, which slept until line 87
  and then ran ~130 lines of logic (end LY 217/223). main.c `frame_wait()` checks the flag with interrupts off and
  halts with IME 0 (wakes on any pending interrupt, which is taken after the ei).
- Perf (PyBoy, end LY / missed): level 8 script DMG 90 / 0, CGB 100 / 0 (M13a 94 / 95); worst-case pile DMG 208, CGB
  206 (M13a 218/223), but 205 / 212 of 600 frames late (M13a 44 / 50; guard now end <= 220, late <= 230, see the
  review note below); level 9 script (2400 frames) DMG 100, CGB 108, 0 missed; NEW level-9 overlap
  scenario (perf_helpers.OverlapCase: pushes through pairs on every bar, 4 mugs per bar): DMG 175 / 229 late of 1200,
  CGB 180 / 264 late, <= 9 objects per line, <= 24 entries. The owner's target for it (0 missed, end LY <= 118) is NOT met:
  with the chooser and lifts switched off the same load already runs median 84, worst 134 (12 patrons and 16 mugs:
  update_patrons ~25 lines, draw_mugs ~25, update_mugs ~13); with them median ~117. test_perf asserts the object
  budgets every frame and a regression guard (end <= 200, missed <= 320).
- Tests: tests/test_overlap.py (slide-through and pass with a structural picture check every frame: BG ids per
  column, empty columns, lifted sprites; drop after clear; hurried 1 in 4 from L3 at 1.5x; the three-in-a-column wait;
  the budget fallback; three in a column by a push; priorities; catch order; empties from an overlapped drinker; DMG
  dx); test_patrons (clump repro: served over and over, the row clears; slide through; rewritten waiting tests);
  test_tips (shuffle rules); test_perf (overlap scenario); test_smooth's every-pixel test samples at vq_frame_end.
  Screenshots: out/m13b/slide_through.*.png, pass.*.png.
- Known compromises: DMG lower X wins between sprites, so a lifted patron covers mugs / the bartender / the held mug of
  a BG patron to his right (only his own mug is clamped); CGB coin and puff are behind lifted patrons; in the fallback a
  TOP patron at shift 0 leaves his 3rd column as venue wall (its specks show) instead of his own wall colour; on a
  frame past line 80 the chooser waits (up to 4 frames) and a new overlap is drawn by the old flags meanwhile.
- Review (worst-case pile, missed frames): M13a 44 / 50 late of 600, M13b 205 / 212, median logic LY 109 -> 130.
  Where it goes (PERF_SECTIONS, DIV ticks a frame; ~1.8 ticks a line): mugs 45 -> 49, patrons 67 -> 64, lift_frame
  0 -> 25 (chooser ~13: one bar every ~4 frames at ~50 ticks, gather + conflicts + loops; the call and bookkeeping ~7),
  queue 14 -> 31, mug drawing 61 -> 68. Not frame_wait (vsync instead: 205 / 213). With the chooser off (no flags,
  plain BG compose) the pile still runs 113 / 117 late: in M13a the pile's walkers stood blocked, in M13b they pass, so
  far more patrons move and are redrawn (queue 14 -> 27 even without flags) and catch more mugs. Tried and measured
  without effect: deferring the chooser on late frames down to line 40, skipping it while vq_held, skipping try_lift
  when OAM is full, charging more queue budget to crowded / two-pass bars (all 190-213 late). Getting back to ~60
  would need the per-patron and per-mug frame work itself cheaper (update_patrons, update_mugs / catch, draw_mugs,
  the BG compose: a hand-written rewrite of those paths), not more overlap tuning. Real play is unaffected (level 8 / 9
  scripts 0 late). The pile guard is tightened to the M13b level.

## M13c as built (door entrance) and the realistic-peak perf test
- Spawn (src/patrons.c try_spawn): blocked_behind(b, SPAWN_X + PATRON_SPACING); the patron is added at SPAWN_X = 0 and
  lifted at once behind the BG (lift.c `lift_spawn`: try_lift with LIFT_BEHIND, OAM X 8, counted in every budget); if the
  lift is refused (LIFT_MAX / LIFT_PER_BAR / OAM / 10 per line / this frame's copy list) he is taken back and the spawn
  retried SPAWN_RETRY frames later. No entry puff. He walks EMERGE_SPEED (64/256 px) while x < DOOR_X, then the level's
  (or hurried) speed: door-to-tap time from x 16 unchanged. At x == DOOR_X LIFT_BEHIND becomes LIFT_OBJ (in front); the
  M13b drop rules then apply (clear 8 frames, x >= DOOR_X). He may catch a mug while emerging (served out at once; his
  sprite goes the frame the puff starts). start_show never distracts a patron in the doorway.
- The door is never drawn over: render.c put_col / stamp3 never stamp columns < DOOR_COLS, and a patron with draw < DOOR_X
  gets no quick redraw. A BG patron in the doorway (only after a forced drop) is therefore clipped at the door, which is
  pixel-identical to the behind-BG sprite because no door has colour 0. try_lift lifts anyone with x < DOOR_X as LIFT_BEHIND.
- Igloo door redrawn (owner decision): its 82 colour-0 pixels (wall purple around the dome) became colour 3 (dark blue),
  nothing else changed; bar tiles still 16. Previews out/m13c/igloo_door_{before,after}.{cgb,dmg}.png. Every venue's door
  has no colour 0 (test). LCDC bit 0 is on in play and the door attributes have bit 7 clear (test).
- Forced drop on a held frame (vq_held): the sprite now goes at once and the BG copy follows with the next list (he is
  missing a frame or two) instead of an ordinary drop that kept 11 objects on a line for a frame.
- main.c: OAM DMA is disabled while the sprites are redrawn (DISABLE_OAM_DMA / ENABLE_OAM_DMA around the draw calls): a
  frame that overran into VBlank DMA'd a half-drawn OAM (the realistic peak showed 11 objects on a line that way).
- Perf (PyBoy, end LY / missed): level 8 script DMG 91 / 0, CGB 101 / 0; level 9 script (2400) DMG 100 / 0, CGB 109 / 0;
  REALISTIC PEAK (new, perf_helpers.RealisticPeak: ~7.5 patrons, <= 3 full, <= 3 empty, up to 7 held, tip or show,
  emergence, lifts) DMG 190 / 65 of 1200, CGB 208 / 88: the owner target (0 missed, end <= 118) is NOT met; asserted
  as a strict xfail plus a regression guard; budgets (<= 10 per line, <= 40) and the music hold. Where it goes (sections
  build, median DIV ticks, ~1.8 a line): update_patrons ~36, draw_mugs + draw_lifted ~43, lift_frame ~29, update_mugs ~23,
  queue_vram ~15, music ~14. Stress tests: level-9 overlap DMG 171 / 259, CGB 176 / 299; pile DMG 220 / 229, CGB 221 / 232
  (guard 230 / 245: its replacement walkers at x 0 are now doorway patrons, composed at every pixel).
- Known: on CGB (always) and DMG (x < 4) an emerging patron's sprite masks the serve-out puff of another patron on the same
  bar where his pixels are; an emerging patron overlapping a BG patron at columns 2-3 is behind him, then in front at x 16.

## No doors (owner 2026-10-09) as built, and a taller saloon keg
- Art: every venue's bar has no door; columns 0-1 of the wall rows continue the wall's 64 px speck pattern (tiles the wall
  already used), the counter row was already full width. Bar + floor tiles per venue: 12 of 16 in every venue (saloon 14,
  space 15, the rest 16 before). The igloo's M13c door redraw went with its door. gen_art checks the wall rows from column 0.
  The door puff is gone (assets/art/puff.txt, OBJ 234-239, DMG copies 246-251, OAM 26 now unused, puff_bar / puff_timer).
- Entering (src/patrons.c, src/lift.c): a new patron spawns at SPAWN_X 0 with patron_aux = 16 px of him beyond the left edge,
  lifted at once as LIFT_EDGE (replaces LIFT_BEHIND: a sprite in front of the BG drawn patron_aux px left of patron_x, OAM X
  wrapping below 8 so the screen edge clips him; no BG footprint at all, so columns 0-2 keep the venue's tiles; never
  dropped while any of him is off screen). He walks EMERGE_SPEED 128/256 px a frame (32 px in 64 frames, the door's
  emergence time) until ENTRY_X 16 (was DOOR_X), where he becomes LIFT_OBJ and drops to the BG by the M13b rules; the
  level's speed and the level table are unchanged (entry-to-tap time as before, L1 >= 15 s). No catch while patron_aux > 0.
  Spawn check, sprite budgets and SPAWN_RETRY as in M13c (the copy list no longer refuses an EDGE lift: he has no BG copy).
- Leaving: pushed back to ENTRY_X he is served at once (score, tip, served count: PATRON_LEAVING), lifted as LIFT_EDGE (a BG
  one waits in place until his BG copy is off screen, which the sprite covers exactly; an already lifted one keeps his
  sprite), slides out at PUSH_SPEED with his mug in his hand past x 0 (patron_aux counts the px gone) and is removed 32
  frames later. No sprite room: he goes at once (as before, without the puff). Level clear waits for him to be gone.
- Forced drops pick an EDGE patron last; one partly off screen cannot drop: an entering one is taken back (spawned again
  later), a leaving one goes. An entering one wholly on screen (x 0-15) drops like anyone (render.c no longer clips
  columns 0-1). LCDC bit 0 / OAM priority are no longer used by the patrons.
- Saloon keg: 20 px tall (rows 4-23 of the bar, was 8-23): rim moved up 4 px, 3 more stave rows; spout, pipe and nozzle
  unchanged (nozzle over SPOUT_X, the fill glass). Previews out/doors/keg_{before,after}.png (CGB left, DMG right).
- Cost: lift_leave runs the chooser only if he had overlap flags, lift_spawn never; draw_lifted_asm stops after lift_total
  patrons. Perf (PyBoy, end LY / missed): level 8 script DMG 107 / 0, CGB 111 / 0 (M13c 91 / 101: a served patron is now a
  sprite for 32 frames and the serve frame lifts him); level 9 overlap DMG 175 / 268, CGB 179 / 299; realistic peak DMG
  187 / 59, CGB 193 / 99 (strict xfail stays); pile DMG 278 / 244, CGB 278 / 245 (same distribution as M13c, guard 290 / 260).

## Patron review decisions (owner, 2026-10-09)
Review: session scratchpad patron_review/REVIEW.md. Owner approved the redraw order (alien A; wall-contrast palette
fixes; zoo trio to 3/4 (the 3/4 rule applies to the zoo) and the samurai; own silhouettes for cowboy C and
lumberjack C; small pixel fixes; outline pass to <= ~45% dark). Lion: must not read as "a bald man with a shawl";
no protruding forehead, a mane framing the whole head, ears, a cat muzzle. Eskimos: the lighter re-indexed
redraw; the third Eskimo gets a beard. Round 6 is proposals first; the owner approves before import.
Still open: the enhanced-variant engine work (one 4-colour-plus patron per group) and keg recolours outside the saloon.
Owner (later, same day): keg recolours outside the saloon are OK, to make room for enhanced patrons. All art is done by
our own agents; the external artist hand-off package is no longer in use.

## M14a as built (enhanced patron variants: engine + the cowgirl)
- Rule (patron review rec. 7): an ENHANCED variant draws its top tile row with one BG palette and its bottom row with
  another (holds at every pre-shift: rows never move), and lifted its left 8x16 column with one OBJ palette and its right
  column with another; every quadrant's colours are in its row palette and its column palette, so lifted == BG pixel for
  pixel. Columns whose colours sit at other indices in their OBJ palette draw re-indexed copies of their two tiles from
  CGB VRAM bank 1 (same ids, OAM attribute bit 3). DMG: unchanged (bank-0 tiles, greys by index, BG / OBP1 E4).
- Slots: row palette S = the venue's bar_b (BG 7: the keg / spout palette where a venue has one; a venue without one
  gets one). Extra OBJ palette X = palettes.json <group>_x in OBJ 4 (OBJPAL_ENH, was the spare). Title, bonus rounds:
  nothing uses BG 7 attributes in the saloon or OBJ 4 / VRAM bank-1 tile data; every level load sets them again (tests).
  | venue | BG 7 | OBJ 4 |
  |---|---|---|
  | saloon | bar_b NEW = S of the cowgirl: wall / skin #f0b890 / hair #985830 / dark #2c1808 (no keg uses it: attrs all 0) | cowboys_x rose #d86098 / hair / dark |
  | the 8 others | their bar_b (keg / spout), unchanged | unused (no enhanced variant yet) |
  No keg colour changed in M14a (the saloon keg is on the bar palette; no other group is enhanced yet). Keg recolours
  come with the other groups' picks (owner approved), each shown before / after.
- Art: '; @rows <a|b|c> <own|S> <own|S>' in assets/art/patrons/<g>.txt and <g>_back.txt marks the enhanced variant and its
  top / bottom row palettes. tools/gen_art.py enhanced_group validates every variant of every group (each lifted column
  <= 3 colours, all in one OBJ palette of A / B / C / X; for enhanced frames: a colour in both rows keeps its index, rows
  light to dark, no index 0 inside the figure; S needs a venue bar_b; cowboys A, the title's patron, cannot be enhanced),
  refuses art that breaks it with the reason, and writes build/patron_enh.h (tables + bank-1 tiles, src/enhance.c's bank)
  and build/patron_enh.json (tests); preview out/preview/patrons_<g>_<v>_enhanced_x8.png (shifts 0-7, lifted, back, DMG).
  palettes2c: PATRON_X_IDS.
- Engine: src/enhance.c (bank 6) enhance_load(g) at level load (LCD off, after lift_level_init): pat_row[8] / back_row[8]
  (top [v], bottom [4 + v]), lift_prop[8] (left [v], right [4 + v]), OBJ 4, the bank-1 tiles. render.c stamp_look /
  stamp_back set cz_pal (top) and cz_palb (bottom); stamp3 / put_col / put_back_col write them per row; stamp_blank uses
  the own palette for both (colour 0 only). lift.c draw_lifted_asm reads the right entry's attributes from lift_prop[4 + v]
  (4 instructions). level.c calls enhance_load.
- Cowgirl (cowboys B) = review mock-up 4.1, re-indexed (skin 1, hair / rose 2, dark 3): cowboys_b is now skin #f0b890 /
  rose #d86098 / dark #2c1808 (BG 3, bottom row; OBJ 6, right column, bank 0); top row S; left column X from bank 1.
  Back view: the review's cowgirl_back (top S brown hair, bottom her own palette).
- Tests: tests/test_enhanced.py (all 8 shifts lifted while swaying == BG, CGB + DMG; zero changed pixels through lift /
  drop; row attributes front + back; OAM attributes / bank bit CGB, never on DMG; bank-1 tiles and OBJ 4 / BG 7 after the
  title and after each of the three bonus rounds; validator accepts the cowgirl, rejects a bad quadrant, a column no OBJ
  palette holds, a shared colour at another index and an index-0 hole). test_lift's per-group M13a equivalence runs for
  every group (enhanced or not); its OAM check reads the per-column attributes. Note: four BG patrons swaying on one frame
  make the copy list spill into the next VBlank in one game and not the other (a frame's lag, any variant), so the new
  test staggers their sway timers.
- Perf (PyBoy, end LY / missed): level 8 script DMG 107 / 0, CGB 111 / 0 (unchanged); realistic peak DMG 188 / 56, CGB
  194 / 99 (was 187 / 59, 193 / 99); level 9 overlap DMG 172 / 279, CGB 188 / 294 (was 175 / 268, 179 / 299); pile DMG
  278 / 244, CGB 279 / 245. ROM0 573 -> 526 free by romusage (render.c per-row attributes, X palette); enhance.c in bank 6.

## Stage animation as built (owner decisions 2026-10-10)
- Proposal: session scratchpad stage_anim/PROPOSAL.md. Owner: stadium keeps ONE scoreboard, option A1 (a cheering section,
  four fans A/B/A/B, stage_b) replaces the second board; stadium animates BOTH the scoreboard bulbs (2-phase chase, then a
  "goal" flash) and the crowd's cheer (the two fan tiles swap), on alternating cycles (bulbs 192 frames, cheer 96). Lodge
  log fire (always moving), bistro oven flame, igloo aurora, factory gear, teahouse lanterns, space porthole, zoo
  parrot as proposed. Saloon: no animation (neon S rejected); adding `saloon_anim.txt` later is a data-only change.
- Source: assets/approved/venues/<t>_anim.txt (optional per venue): `!slots c,r ...` (every animated map position),
  `!script name:hold ...` (looped, holds 6..255 frames), `@name` frames of 8 rows, one 8-px column per distinct slot
  tile. tools/gen_art.py stage_anim() checks @base == the stage at the slots, no static position repeats an animated
  tile, every frame used, <= 6 animated tiles, <= 4 tiles changed per step, the stage still <= 20 tiles; it gives the
  animated tiles their own ids, LAST and contiguous (static 0..s-1, animated s..s+k-1), and compiles each step to
  (frame * k, lo, hi, hold): the tile range that differs from the previous step's frame (step 0 also vs the stage).
  Output: venue_t gains anim_frames / anim_script / sizes / anim_first / anim_k; art.h SA_BUF (400, sports: 5 frames x 5
  tiles) and SA_SCRIPT (108); venues.json "anim"; preview out/preview/venue_<t>_anim_x3.gif.
- Engine (src/venue.c, banked): stage_anim_start() from init_scene (LCD off, every level screen) far_copies the frames
  and script into WRAM (sa_frames, the drain runs from the VBlank interrupt with any bank mapped) and starts at step 0;
  vq_reset() (every screen change: title, bonus, scores, level load) clears sa_on, so the title's text tiles over stage
  ids 0.. and the bonus rounds are never touched. main.c, once per frame unless PAUSED: `sa_on > sa_hold && !--sa_timer`
  -> stage_anim_step() (banked): the new step's tile range is merged with a still-pending one (copied from the new
  frame), so a late update is never lost or queued twice. render.c queue_stage (ROM0): one queue entry of <= 2 tiles
  (32 B, cost n + 3 = 35 units) from sa_frames to 0x9000 + 16 * id; a 3-tile change goes out over 2 frames. Priority:
  urgent spans first; with nothing else pending it always goes; else after the bars if qv_cost + 35 <= VQ_BUDGET, else
  sa_wait++; after SA_MAX_WAIT (3) refusals it goes before the quick redraws and bars. Nothing in vq_vbl / vq_exec changed.
- `sa_hold` (WRAM): tests freeze the stage on its current frame. conftest's boot fixture (and test_lift's boot_play) set
  it, so every existing golden keeps the stage's frame 0; tests/test_stage_anim.py turns it off. test_perf runs with the
  animation ON.
- ROM0: the debug level select's box (debug_open / debug_step / debug_show) moved to src/debug.c (bank 255) to make room;
  debug_watch stays in main.c. romusage ROM0 526 -> 503 "free" (romusage overstates ROM0 by ~380 B: the real margin is
  ~120 B; a build at 341 by romusage overflowed into bank 1). Bank 6 1316 -> 3781 used (autobank moved files around).
- Goldens replaced (stadium art: one scoreboard, crowd in the second one's place, owner request): venue_sports, level2,
  patrons_sports (dmg + cgb); each differs only at x 88-119, y 16-31. New: stage_anim_<venue> (8 venues x 2 models).
- Tests: tests/test_stage_anim.py: gen_art invariants; per venue 2 script periods (max 1100 frames) in play: only the
  animated ids change, each tile always matches the script within SA_MAX_WAIT + 3 frames, every frame shows, tilemap and
  attributes unchanged, no late drain; sa_hold freezes and releases; the saloon never animates (sa_on 0); pause freezes;
  bonus round: sa_on 0 and stage ids unchanged, the next level starts on frame 0; title text untouched; one scoreboard.
- Perf (PyBoy, test_perf, end LY / missed, before -> after): level 8 script DMG 107 / 0 -> 108 / 0, CGB 111 / 0 -> 115 / 0;
  level 9 overlap DMG 172 / 279 -> 182 / 284, CGB 188 / 294 -> 189 / 293; realistic peak DMG 188 / 56 -> 191 / 69, CGB
  194 / 99 -> 194 / 127. The realistic peak is chaotic (frame timing feeds back into lifts and redraws): over 6 RNG seeds
  the mean missed frames are DMG 27.5 base / 30.0 new with sa_hold / 32.3 animating, CGB 40.2 / 43.5 / 46.8 (seed spread
  CGB 22-81), so the animation costs a few late frames per 1200 at the peak and the fixed-seed jump is mostly noise.
  Guards unchanged and passing.

## ROM0 cleanup as built (2026-10-10)
- Measuring ROM0: do NOT trust romusage's ROM_0 "free" column; it overstates ROM0 by ~341 B here (its own accounting of
  the 0x0000-0x01FF header area and areas differs from the linker). The real margin is 0x4000 minus the end of the last relocatable area the linker
  places in ROM0 (_CODE from 0x0200, then _HOME, _INITIALIZER, _GSINIT, _GSFINAL) in build/game.map. `make` now prints it
  (tools/rom0free.py) after romusage, for game.gb and release.gb. Cross-checked by padding: a ROM0 const array of exactly
  the reported size links clean, one byte more gives the linker's "Possible overflow from Bank 0 into Bank 1". That is only
  a WARNING (the ROM is built, bank 1 silently corrupted: the 44b9bed overflow); the Makefile now fails the build on it.
- Real ROM0 free: 162 B before (romusage said 503), 1827 B after (romusage 2168); release.gb 1939 B.
- Moved: build/palettes.c is `#pragma bank 255` (autobanked); its table and patron_pal_ids are static and read only
  through the BANKED pal_get(id, dst) / patron_pal_get(g, v, dst) in the same file, which copy one palette into a WRAM
  buffer (tools/palettes2c.py generates them). Callers (main_cold, level, lift, enhance, title, bonus2) use those; the
  per-frame slot-5 switch in render.c reads `coin_pal` (WRAM, copied at boot) instead of the table. New palettes cost
  ROM0 nothing. src/main_cold.c (bank 255): boot_init (was main.c init), load_cgb_palettes, win_init, draw_hud,
  init_scene, glyph_for, reset_actors, enter_level_screen, start_new_game, resume_after_life, enter_game_over,
  enter_level_clear. Declared BANKED in game.h. Stays in ROM0 (main.c): the far-copy helpers (they switch banks), lcd_isr
  (LCD interrupt), show_overlay (callers pass strings from their own bank) + hide_banner_sprites (per frame with a
  banner), prep_hud / add_score / lose_life (mid-frame), the frame loop. enter_game_over passes the "AAA" initials to
  top_insert (another bank) from the stack, not as a literal. Banked code must never pass a pointer to its own ROM data
  to a function in another switchable bank.
- Not moved (hot or bank-switching): render.c, patrons.c, mugs.c, build/patron_load.c, musicload.c; write_all_bars shares
  render.c's static compose code. Bank 6 holds main_cold (now 4456 used); banks 1, 4, 5 are near full after autobanking.
- Perf (PyBoy, scratchpad perf.py = test_perf scenarios; end LY / missed, before = after, identical to the frame):
  level 8 script DMG 108 / 0, CGB 115 / 0; level 9 overlap DMG 182 / 284, CGB 189 / 293; realistic peak DMG 191 / 69,
  CGB 194 / 127; realistic peak over 7 RNG seeds, mean missed DMG 70.1 / 70.1, CGB 95.4 / 95.4.
- Goldens: none changed.

## Patron round 7 decisions (owner, 2026-10-10)

Proposals in scratchpad patron_round7 (round 6 is the base). Import waits until every patron is approved: one big
graphics overhaul. Picks: lion face L2 (broad muzzle); cowboy C thin-brim hat with face F2 (jaw beard + moustache);
lumberjack C face G3 (default); Eskimo ruff dots tan; Eskimo A sky-blue parka; Eskimo C olive parka; headband fan
ponytail option. Alien A and the darker-than-45% patrons stay as they are. Enhanced (round 8b, owner 2026-10-10): robot A as
drawn; lumberjack A axe, chef C towel, geisha pins as props only on the round-7 look; headband fan gets an accessory;
no enhanced Eskimo, referee, alien or panda (their kegs stay). Then the import. Saloon stage: no neon; owner picked the ginger bar cat (scratchpad saloon_cat/B_ginger: tail
swings over the stage lip, blink, ear flick; curtains become one repeated fold tile; stage_b colour 0 -> #f09848),
imported with the graphics overhaul. Story mode and portraits on hold until the owner reviews
docs/story.md. Music mix on hold. No speed milestone unless the owner sees slowdown.

## Graphics overhaul as built (2026-10-10)
Owner-approved import of the final patron set, the tile-pool change it needed and the saloon bar cat. Three commits:
- Venue tile pool, option A (owner approved; its own commit, zero golden changes): BG ids 0-35 are one pool per venue.
  The stage takes ids from 0 up (animated tiles last and contiguous, as before); the bar + floor pack at the top of the
  pool, venue.bar_base = 36 - bar_n .. 35, so bar ids never fall in 0-19, which the title's menu text overwrites while it
  shows the saloon's bar. gen_art fails a venue with stage_n + bar_n > 36 or bar_base < 20 (TITLE_TEXT_SLOT). Every bar
  uses 12 tiles today, so a stage may use up to 24. tools/gen_art.py VENUE_POOL / TITLE_TEXT_SLOT replace STAGE_SLOT /
  BAR_SLOT; venue_t gains bar_base; load_venue loads the bar at venue.bar_base; art.h VENUE_POOL, TITLE_TEXT_SLOT
  (TILE_BAR_BASE, STAGE_TILE_SLOT, BAR_TILE_SLOT removed; TILE_GENERIC_BASE still 36); venues.json "pool",
  "title_text_slot", per venue "bar_base". render.c's bar maps already held absolute ids. Tests: test_venues (pool
  layout, bar ids at the top and >= 20: the title-safety assert), bar VRAM at bar_base (test_venues, test_bonus),
  test_bartender, test_stage_anim reads the whole pool (0-35).
- Patrons (scratchpad patron_round8/r8b/final/assets, the drop-in set): all nine groups' fronts and backs (round 6
  redraws / outline pass, the round 7 owner picks), palettes.json, factory_pal.json. Diffed against the repo first: the
  repo's assets had not changed since the proposal's base (94c39cd) and the other 8 venue palettes were identical, so
  nothing newer was reverted and no hand merge was needed. Enhanced set: the cowgirl (unchanged) and robot A (hazard
  stripes on the left arm, top row own / bottom row S, robots_x in OBJ 4, no bank-1 tiles). The factory keg is steel
  (bar_b #f8d848 / #7888a0 / #101828; the old yellow / blue under _was); no other keg changed. Lumberjack A axe, chef C
  towel, geisha pins and the headband fan's accessory were not done (the quadrant rule would change faces; r8b
  CHANGES.md part 2). test_enhanced: "only the cowboys are enhanced" became test_the_enhanced_set_is_the_cowgirl_and_robot_a,
  plus r8b's generalised lift tests for every enhanced variant other than the cowgirl (who keeps her own).
- Saloon bar cat (owner pick B_ginger): saloon_anim.txt (tail swing over the stage lip, blink, ear flick; slots (14,1)
  (13,3), 7 frames, 392-frame loop), saloon_attr.txt (the cat's 4 tiles on stage_b), saloon_pal.json (stage_b colour 0
  -> #f09848, the ginger coat; 1-3 = stage_a's). With option A the curtains keep their ORIGINAL four tiles (cols 0, 1,
  18, 19, rows 0-2), not B_ginger's single repeated fold: the saloon stage is 23 tiles (21 static + 2 animated), the bar
  12 at 24-35. test_stage_anim: the saloon joined the animated set; test_the_saloon_does_not_animate became
  test_the_saloon_bar_cat (slots, stage_b attributes, own colour 0, four different curtain tiles, <= 24 tiles, level 1
  animates). New golden stage_anim_saloon.
- Goldens replaced, every one viewed (old vs new sheets): patron commit (dmg + cgb, differences only in the bar rows
  y 40-135, the factory also in the keg): patrons, patrons_<9 groups>, venue_<9>, stage_anim_<8 animated before>, show,
  show_backs, title, title_anim, level2, gameover, loop_banner, bonus_after. Cat commit (dmg + cgb, differences only
  at x 106-119, y 17-38, the cat and its tail): drinking, filling, gameover, loop_banner, mug_sliding, patrons,
  patrons_cowboys, pause, scene, served, show, show_backs, spout_fill, stage, venue_saloon, walking; new
  stage_anim_saloon. Option A commit: none.
- ROM: real ROM0 free 1827 B (game.gb) / 1939 B (release.gb), unchanged. Banks after: 1 51, 2 93, 3 155, 4 236, 5 383
  free (romusage; bank 5 was 45, autobank moved data), 6 11123 free. WRAM unchanged (SA_BUF still 400: the saloon's
  frames are 224 B).
- Perf (PyBoy, scratchpad perf.py; end LY / missed): level 8 script DMG 108 / 0, CGB 115 / 0; level 9 overlap DMG
  182 / 284, CGB 189 / 293; realistic peak DMG 191 / 69, CGB 194 / 127; over 7 seeds mean missed DMG 70.1, CGB 95.4.
  Identical to the ROM0 cleanup numbers.

## Crash at the drink's scale as built (owner pick option 1, 2026-10-10)
- Owner: the crashing mug was too wide next to the sliding one. Each venue's breaking drink is now generated by
  tools/gen_art.py crash_frames() from its own <t>_drink.txt: tip = frame 8 (the drinking pose, 8x16), fall = frame 1
  (full, left end, OBJ 1, four drops) or frame 2 (empty, right end, OBJ 2, drawn mirrored with S_FLIPX) turned 90
  degrees (16x16, 2 entries), then the shared assets/art/glass_shards.txt (shatter, settle; '+' = the drink's colour).
  assets/art/glass.txt retired. 16 tiles appended to each venue_<t>_drink (36), loaded by load_venue at the same
  OBJ 60-75 (GLASS_TIP/FALL_FULL/FALL_EMPTY/SHATTER/SETTLE ids in art.h); main_cold no longer loads glass tiles.
  DMG: lift_level_init plane-swaps OBJ 60-75 in place, so the crash shades match the sliding drinks on OBP0 (the old
  "shards light/white swapped" compromise is gone; OBJPAL_GLASS / spr_glass_p removed). A breaking glass still
  reserves 2 OAM entries (the second hidden on 1-entry frames). Any new drink gets its crash for free.
- Tests: test_venues checks every venue's crash tiles in VRAM (plane-swapped on DMG); new test_crash_golden (fall
  frame, both ends) with new goldens crash_saloon, crash_factory (dmg + cgb). No existing golden changed.
- ROM: real ROM0 free 1827 -> 1757 B (game.gb), release.gb 1869 B; +256 B per venue bank. Banks free (romusage):
  1 51, 2 105, 3 155, 4 14, 5 199, 6 9457.
- Perf (scratchpad perf.py): level 8 DMG 108 / 0, CGB 115 / 0; level 9 DMG 182 / 284, CGB 189 / 293; realistic peak
  7-seed mean missed DMG 70.3, CGB 95.1 (was 70.1 / 95.4): unchanged within noise.

## Factory battery as built (owner pick variant A, AA cell + charging station, 2026-10-10)
- Drop-ins from scratchpad factory_battery/A_aa: factory_drink.txt (AA cell 6x15: charging lights 4 lime bars bottom
  up; empty = dark body, one red bar; frames 7-8 sideways, nub at the robot's face), factory_drink_pal.json (full lime
  #a0f860 / copper #e08828 / dark #181410; empty red #f85838 / grey #a0a8b0 / dark #201c20), factory_bar.txt +
  factory_bar_attr.txt (the keg becomes a charging station at cols 18-19, BG 7 = bar_b only: bolt screen, lamps; a
  plug on col 17 row 0; col 17 row 1 plain wall). factory_pal.json kept as main has it (the drop-in differed only in
  its _note). Diffed against main first: the bar art had not changed since the proposal's base; with the option-A pool
  the factory is stage 16 + bar 12 = 28 <= 36, bar_base 24.
- With the generated crash the battery crashes as a battery (tip = the sideways cell, fall = the cell on its side).
  The empty battery's crash at the right end is dark on the dark station (reads, but low contrast).
- Goldens replaced (dmg + cgb, all differences in the bar rows y 40-127): venue_factory, stage_anim_factory,
  patrons_robots (the station replaces the keg; venue_factory also the sliding battery), crash_factory (the crash is
  now a battery).
- ROM / perf: identical to the crash commit (ROM0 1757 B free, release 1869 B; drink data only changes in the factory
  bank).

## M11b story engine as built (part 1, 2026-10-10)
The story mode of docs/story.md: script pipeline, story font, cut-scenes, chapter goals, save / continue. The optional
per-chapter twists are part 2 (hook below). Portraits and pictures are placeholders until the M11c art study.
- Script pipeline: tools/gen_story.py parses docs/story.md (scene headings, the script blocks, the chapters table) into
  build/story_data.c (script, scene table, names, goals, story font, picture slots) and build/story_portraits.c, both
  `#pragma bank 255` with static data read only through BANKED accessors in the same file (copy into WRAM, or write VRAM
  with the LCD off), plus build/story.h (SC_* scene ids, ST_* font ids, the budget, portrait_t / scene_hdr_t / goal_t)
  and build/story.json (tests). The build fails on: a line over 18 characters, more than 3 lines a page, a character
  outside A-Z 0-9 . , ! ? ' - : space, an unknown speaker, a scene title over 20, scene order, a chapter goal in
  gen_story's CHAPTERS that disagrees with the table's engine column, a goal banner line outside the HUD glyphs, any
  portrait / scene over the budget below. Size: 21 scenes, 123 pages, 5451 characters = 5943 B of script (length-
  prefixed lines, speaker byte per page) + 609 B scene table / scene titles + 450 B goals; uncompressed (ROM is not
  short: compression was not needed).
- Font: the HUD glyphs are the font (A-Z 0-9, space = TILE_HUD_BLANK, light text on the dark band, BG palette 1). The 7
  missing glyphs (. , ! ? ' - :) are assets/tiles/story.txt in the same style (1 px strokes, columns 1-5, rows 1-7), with
  the portrait frame (8 tiles, a gold moulding) and the narrator's spigot icon: 16 tiles loaded at BAR_TILE_COUNT (77)
  only while a cut-scene shows (ids the patrons use in play; every level load puts the patrons back).
- Cut-scene ("hybrid lighter"): load_venue + draw_venue + write_all_bars with nobody on the bars, the scene title on the
  HUD row, the Spigoteer's normal sprite (OAM 0-3, BT_IDLE, facing the bar) at bar 1's tap, the stage animation running;
  a framed portrait (default: picture at column 2, frame bottom on row 12); the text box rows 13-17: the top panel
  carries the speaker's name (the narrator: the spigot icon), 3 lines x 18 at columns 1-18 of rows 14-16, bottom panel.
  INTRO / FINALE / CREDITS: a picture slot (rows 0-12, its own tiles at ids 0..35, palettes 0/5-7 free there; now a
  generated placeholder card: frame, spigot, the scene title, its id, "PICTURE SLOT") instead of the venue, no sprite.
  Buttons: the page types on, one character a frame (spaces free); A or B shows the rest of the page at once, then the
  next page; START skips the rest of the scene. Music: the venue's tune (the title tune on picture scenes).
- Portrait slot parameters (build time, assets/story/portraits.json -> portrait_t; nothing hard-coded in src/story.c):
  size w x h tiles up to 7x7 (56x56), the picture's screen tile x, y (the frame takes one tile around it, all inside
  rows 0-12), 1-3 CGB BG palettes (slots 2, 3, 4) with a per-tile palette map ('attr'), an optional OBJ overlay layer
  (8x16 cells, '.' transparent, px offset from the picture, up to 16 entries, at most 8 on a line, CGB OBJ palettes
  3, 4, 6, 7 = up to 4, DMG OBP0/OBP1). The two approved 32x32 portraits (Spigoteer, Sadie) use one palette each; the
  other nine speakers get generated placeholders: a hatched 32x32 background with a silhouette and a rim light (one
  tinted palette each) and the speaker's name as a 4-sprite OBJ overlay tag (so the overlay path is exercised;
  MANAGER-BOT shows MGR-BOT). out/preview/story_portrait_*.png.
- Cut-scene budget (a venue backdrop on screen):
  BG tile ids: 0-35 the venue pool (stage + bar), 36-76 HUD glyphs / panels, 77-92 the story font, 93-255 free for the
  scene's portraits = 163 tiles for all its portrait speakers together (at most 3 per scene: every scene's speakers are
  loaded when it starts, LCD off). 3 x 49 (three 56x56) = 147 fits; today's scenes use at most 33. BG 128-255 share VRAM
  with OBJ 128-255, but a cut-scene's OBJ ids all stay below 128. CGB VRAM bank 1 is untouched (another 384 tiles: room
  for richer portraits / pictures).
  OBJ tile ids: 0-55 the Spigoteer, 56-95 drinks / coin (unused on a cut-scene, not reclaimed), 96-127 = 32 tiles for the
  scene's overlays (the show performers' slot; load_venue puts them back).
  CGB BG palettes: 0 wall / counter, 1 HUD / text box / frame, 5-6 stage, 7 keg stay the venue's: 3 free (2, 3, 4), so a
  portrait has at most 3 BG palettes; a 4th colour set has to come from the OBJ overlay. CGB OBJ palettes: 0 the
  Spigoteer; 3, 4, 6, 7 free = up to 4 overlay palettes (1, 2 the drinks could be freed too; 5 stays the coin / show's,
  render.c tracks it). Picture scenes have BG palettes 0, 5, 6, 7 free as well (4 for the picture).
  OAM: 0-3 the Spigoteer, 4-19 the overlay; per line at most 8 overlay sprites + the Spigoteer's 2.
  Speaker change (LCD on): the old frame is wiped back to the backdrop (a WRAM copy of rows 0-12 read with the LCD off),
  2 rows a frame through the VBlank queue; then at the top of the next frame (VBlank) the new palettes, then the new
  frame 2 rows a frame (a 56x56 framed portrait: 5 + 5 frames). The text types on meanwhile; the page can only be
  turned once the swap is done.
  WRAM: story.c ~1.3 KB (backdrop copy 520 B, portrait struct 227 B, composed frame 162 B, page / box / banner buffers).
- Story flow (src/story.c, banked; GS_STORY = 11 cut-scene or TRY AGAIN, GS_GOAL = 12): title STORY -> INTRO -> per
  chapter c: PRE scene -> the venue's level (level = c + 1: the arcade level row c, no loop difficulty, no bonus
  rounds) with a goal banner first (window rows 0-4: panel, CHAPTER n, two goal lines, panel; LYC moved to BANNER_WY + 38
  while it shows; 3 s or A / START) -> on success CHAPTER CLEAR (enter_level_clear + its 1000 bonus) -> progress saved ->
  POST scene -> chapter c + 1. After chapter 9's POST: FINALE, CREDITS, the title. [10th venue, 2026-10-11: chapter 10's.]
  Goals (gen_story CHAPTERS, checked against the chapters table): 1 serve 15; 2 serve 20 and no patron reaches the tap;
  3 serve 18; 4 serve 20 within 120 s; 5 serve 20 within 120 s; 6 catch 25 empties (a glass taken from a patron counts,
  it scores as a caught empty); 7 clear the level (the row's quota) with no broken glass; 8 serve 25; 9 serve 30.
  Serve / catch chapters set quota 255, so patrons keep coming until the goal is met. Counters: `served` (the engine's);
  catches and breaks are deltas of sfx_count[SFX_CATCH] / sfx_count[SFX_BREAK] (no change to the hot code); a life lost
  with no glass broken that frame is a patron at the tap. The timer runs only in play, not during the level's intro
  freeze. HUD in story: columns 12-14 the goal letter (S serve, C catch) and what is left, 16-19 'T' + seconds on timed
  chapters (over L0n). Main loop hooks (ROM0): story_play() after play_frame when story_on, GS_LEVEL_CLEAR's end calls
  story_level_done(), GS_STORY / GS_GOAL call story_update(); enter_game_over (banked) calls story_fail() in story mode.
  Failure (superseded by "Story lives as built"): lives work as in arcade (3 per attempt, lose_life as always); losing the last one, breaking the chapter's
  rule (2: a patron at the tap, 7: a broken glass: lives forced to 0, the freeze plays out) or the timer running out shows
  TRY AGAIN (2.5 s or A / START), then the chapter restarts at its goal banner (no PRE scene) with 3 lives. The score
  carries on through the story and never enters the top 5.
  Twists hook: goal_t.twist (0 for all nine then; built for The Chrome Cow: see 10th venue as built) is copied to story_twist at chapter start; part 2 applies it there and in
  story_play.
- Save (src/save.c): SRAM version 3 "TPR3" = version 2's table at 4..33, 34 story progress (chapters cleared 0..9), 35
  reserved 0, checksum 0x5A + bytes 0..35 at 36, complement 37; progress > 9 is invalid. Migration at boot, written back
  at once: version 2 keeps its table, progress 0 (save_migrated = 2); version 1 as before (SPG, save_migrated = 1). The
  progress is saved when a chapter's clear is over (before its POST scene). Title: CONTINUE when 1 <= progress <= 8: the
  menu becomes ARCADE / STORY / CONTINUE / MUSIC at rows 5 / 7 / 9 / 11, HI on row 13 (without a save the title is
  unchanged: rows 6 / 8 / 10, HI 12). CONTINUE starts at the PRE scene of the first chapter not cleared; STORY always
  starts over at the INTRO (the save then follows the new run). A finished story (progress 9) shows no CONTINUE.
  "CONTINUE" took the place of "COMING SOON" in gen_art's MENU_STRINGS (the M10a message is gone).
- Story text (owner change, factory battery): chapter 6 goal "Recycle 25 batteries" (twist: full batteries), PRE_ROBOT
  picture / art list: a big lightning-bolt sign, page 4: MY WORKERS NEED / POWER. RECYCLE 25 / EMPTY BATTERIES.
- ROM: 128 KB (banks 0-7; -Wm-yoA sizes it, no flag change). Autobank packs the story data + portraits into bank 1,
  story.c next to title.c in bank 2, main_cold moved to bank 7. Free after (romusage): 1 132, 2 38, 3 15, 4 39, 5 47,
  6 262, 7 5819 B. Real ROM0 free 1757 -> 1708 B (game.gb), 1869 -> 1821 B (release.gb): the main.c hooks.
- Perf (scratchpad perf.py, arcade, unchanged): level 8 DMG 108 / 0, CGB 115 / 0; level 9 overlap DMG 182 / 284, CGB
  189 / 293; realistic peak 7-seed mean missed DMG 70.1, CGB 95.0.
- Tests: tests/test_story.py (script build: lengths, charset, speakers, the md table, failing builds; the budget; the
  intro from the title; typing, A / B / START; the venue scene, portrait and frame; the speaker swap and the narrator's
  wipe; the goal banner and HUD counter; every chapter's success and failure (and the restart); real catches; the
  clock; finale / credits / title; save across a reset and CONTINUE; v2 -> v3 migration, v3 loading). test_flow:
  the COMING SOON test became test_story_starts_the_story_mode; test_scores / test_sound read version 3.
  New goldens (dmg + cgb): story_portrait (PRE_SALOON, Sadie), story_placeholder (POST_SALOON, Dregs with its
  overlay tag), story_narrator (INTRO, the picture slot), story_goal (chapter 1's banner), title_continue. No existing
  golden changed.

## Story shifts as built (M11d, owner-approved, 2026-10-10)
Each chapter plays its venue several times in a row, as shifts with rising difficulty and their own arrival patterns.
- Chapter flow: PRE scene -> Opening shift -> Happy hour -> [mini-game slot] -> Last call -> [boss slot] -> POST scene.
  The sequence is data (tools/gen_story.py SEQUENCE -> build/story_data.c st_seq, 5 steps per chapter, one byte each:
  kind << 4 | index, kinds SHIFT 0 / MINI 1 / BOSS 2; STEP_SKIP 0x80 = not built yet, from gen_story's NOT_BUILT). The
  engine (src/story.c next_step) passes over a skipped step. Adding the mini-games / bosses = their mode in story.c
  step_start (dispatch on the step's kind; today every playable step is a shift) + taking the kind out of NOT_BUILT.
- Shift goals (gen_story SHIFTS: Opening and Last call per chapter; the Happy hour is the CHAPTERS row, unchanged):
  goal_t (52 B, one per chapter x shift = 27, 1404 B) = type, count, flags, secs, twist, pattern, walk %, spawn %,
  quota (G_CLEAR: patrons in the shift, 0 the row's), pad, two banner lines. Validated at build time (check_shifts):
  banner lines <= 20 in the HUD glyphs, "CHAPTER n " + the shift's name <= 20, counts 1-99 (two HUD digits), walk
  70-130 %, spawn 70-150 %, Opening slower (walk < 100 < spawn) at 40-60 % of the Happy hour's goal size, Last call
  faster (walk > 100 > spawn) with a goal no smaller and its own pattern, the Last call patterns all different (ten now),
  every shift the chapter's kind of goal (type + flags), a timed goal that enough patrons reach in time (the row's
  start patrons + spawns in the timer >= 1.3 x the goal; the rows parsed from src/level.c), every pattern within
  0.9-1.15 patrons per interval. docs/story.md has a "Shifts" table (in-world / engine per shift, the Last call's
  arrivals); gen_story fails when an engine cell or a pattern disagrees with the data.

  | # | Opening (walk 85 %, spawn 115 %) | Happy hour (row) | Last call | walk / spawn | arrivals |
  |---|---|---|---|---|---|
  | 1 | serve 8 | serve 15 | serve 18 | 110 / 90 | stairs down 1, 2, 3, 4 |
  | 2 | serve 10, none at the tap | serve 20, none at the tap | serve 22, none at the tap | 105 / 95 | all bars at once (4 x 12 frames, then 4 I) |
  | 3 | serve 9 | serve 18 | serve 20 | 115 / 85 | flood bar 2 (2, 1, 2, 3, 2, 4) |
  | 4 | serve 10 in 75 s | serve 20 in 120 s | serve 22 in 120 s | 115 / 85 | pairs (1+3, 2 I, 2+4, 2 I) |
  | 5 | serve 10 in 75 s | serve 20 in 120 s | serve 22 in 120 s | 115 / 85 | zigzag 1, 3, 2, 4, 3, 1, 4, 2 |
  | 6 | catch 12 | catch 25 | catch 28 | 115 / 85 | stairs up 4, 3, 2, 1 |
  | 7 | 7 guests, no break | the row's 13, no break | 15 guests, no break | 115 / 85 | flood bar 4 (4, 1, 4, 2, 4, 3) |
  | 8 | serve 12 | serve 25 | serve 28 | 120 / 80 | inside out (2+3, 2 I, 1+4, 2 I) |
  | 9 | serve 15 | serve 30 | serve 32 | 120 / 80 | stampede (1-4 at once, 4 I, 4-1 at once, 4 I) |

  (Bars numbered 1 top .. 4 bottom here; 0-3 in the data.) The Happy hour keeps the row's speeds and normal arrivals.
- Pace (story.c shift_pace, after enter_level_screen): patron_speed x walk / 100, hurry_speed re-derived (1.5x, from
  level 3 as in level.c), spawn_interval x spawn / 100 (and spawn_timer), a clear goal's quota. resume_after_life keeps
  them (it does not reload the row).
- Arrival patterns (patrons.c try_spawn / update_patrons, ROM0): pat_len 0 = today's random bar every spawn_interval
  (the arcade's RNG sequence is unchanged); else the next patron goes to pat_bar, and after each spawn the BANKED
  pat_done() (story.c) moves the pattern on, sets the next pat_bar and returns the entry's wait (code n the interval
  I, s PAT_SHORT = 12 frames, d 2 I, b 4 I; pat_wait[4] computed per shift). A blocked spawn (crowded left end, no
  lift room) retries SPAWN_RETRY later with the same entry, so the order holds. Patterns are data (gen_story
  PATTERNS: <= 8 entries of bar | wait << 4, read with story_pattern_get into story.c's pat_buf). start_new_game
  clears pat_len (arcade, debug menu). Per-frame cost: none (only a spawn frame tests pat_len).
- Banner: the existing 5-row layout; row 1 is now "CHAPTER n " + the shift (OPENING / HAPPY HOUR / LAST CALL, from
  STORY_SHIFT_NAMES in build/story.h), centred; "CHAPTER 1 OPENING SHIFT" would be 23 characters, so the word SHIFT is
  left out [owner 2026-10-11: row 1 is the shift's name alone, OPENING SHIFT / HAPPY HOUR / LAST CALL / BOSS, no
  chapter number: see 10th venue as built]. A won shift shows SHIFT CLEAR (CHAPTER CLEAR when no playable step is left), with the level bonus.
- Retry (superseded by "Story lives as built": lives per venue, a venue restart): a failed goal shows TRY AGAIN, then
  the same shift's banner with 3 lives (no PRE scene, no earlier shift); served / catches / timer start over; the score
  carries on. The twist hook is per shift now (goal_t.twist -> story_twist
  at every shift start; 0 everywhere).
- Save (src/save.c), SRAM version 4 "TPR4": 0-3 magic, 4-33 the top 5 (as v2 / v3), 34 chapters cleared (0-9), 35 the
  step reached in the next chapter (0-4; must be 0 when 9 chapters are cleared [10th venue, 2026-10-11: 10, SRAM v6]), 36 checksum 0x5A + bytes 0-35, 37 its
  complement. The progress is saved when a shift's clear is over: (chapter, the next step in the raw sequence, even a
  skipped slot: when the mini-games ship, such a save resumes at the mini-game), or (chapter + 1, 0) after the last.
  CONTINUE (title) shows when chapters 1-8 are cleared or a step is reached in chapter 1; it resumes at the first
  playable step from the one reached (straight to its goal banner), or at the PRE scene when the step is 0. Reached
  (for a later Practice mode): step s of chapter k when k < chapters cleared, or k == chapters cleared and s <= the step
  reached. Migration at boot, written back at once: version 3 keeps its table and chapters, step 0 (save_migrated = 3;
  CONTINUE still opens the PRE scene of the first chapter not cleared); version 2 / 1 as before. Practice best scores
  are not stored yet: they go in their own block from 0x40 with its own magic and checksum (no version bump, and a bad
  block loses only the bests); 45 steps x 3 B = 135 B.
  Superseded by SRAM version 5 "TPR5" (the soundtrack's unlocks at 36-37, checksum at 38): see "Bonus menu and
  soundtrack as built".
- Tuning (scratchpad bot.py: a greedy bartender playing each shift through the real inputs, the game deterministic):
  an instant server (serves walkers as they enter) wins the 24 serve / clear shifts without losing a life (on the
  factory's catch goal it never gets an empty back: a patron served at the left end leaves); a late server (serves only
  walkers past x 48, re-plans every 30 frames) wins all 27, loses a life only in chapter 9's Last call (the zoo then); the latest one
  (x 56) loses no life in any Opening or Happy hour, but loses lives in 5 of the 9 Last calls and fails two (2 and 9).
  Pressure for the late server, Happy hour -> Last call: busy 58 -> 64 % (ch 1) .. 80 -> 77 % (ch 9), the furthest
  walker x 76 -> 76 (1), 117 -> 114 (3), 94 -> 119 (4), 98 -> 119 (5), 95 -> 119 (6), 97 -> 117 (7), 110 -> 119 (9).
  Chapter 2's Last call was 110 / 90 at first: the x 48 server failed it in 24 s (a burst of four plus the no-tap rule),
  so it plays at 105 / 95.
- ROM: real ROM0 free 1708 -> 1671 B (game.gb), 1821 -> 1784 B (release.gb): 37 B for the pattern test in try_spawn and
  the pat_done call (the first version kept the pattern in ROM0: 87 B). Banks after (romusage): 1 97, 2 50, 3 45, 4 54,
  5 47, 6 121, 7 4102 B free.
- Perf (scratchpad perf.py, PyBoy; end LY / missed): arcade unchanged to the frame, old = new: level 8 script DMG 108 / 0,
  CGB 115 / 0; realistic peak (1200 frames) DMG 168 / 43, CGB 176 / 49. Story with the x 48 bot: chapter 9 Happy hour
  DMG 170 / 3, CGB 177 / 3 (4000 frames); its Last call DMG 159 / 7, CGB 168 / 17 (1720 frames): no higher peak, a few
  more missed frames from the burstier crowds (fewer per frame than the arcade's realistic peak).
- Tests (tests/test_story.py): the shift data (half / as written / harder, nine patterns, the sequence with its skipped
  slots); failing builds (a shifts-table mismatch, a last call not harder, shared patterns, a timer too short); the
  opening banner and HUD (golden story_goal); a Last call banner (new golden story_last_call, chapter 9; chapter 10 since the 10th venue); every chapter
  plays Opening -> Happy hour -> Last call -> POST with each banner, goal, quota, timer, interval, pattern and walking
  speed, SHIFT CLEAR / CHAPTER CLEAR, the save after each shift; a failed Last call (every chapter) and a failed Opening
  retry only that shift; every Last call's pattern spawns its bars in order with its waits; CONTINUE at a shift after a
  reset, from the mini-game slot (to the Last call), after a cleared chapter (golden title_continue unchanged); STORY
  starts over from the INTRO; v2 -> v4, v3 -> v4 (CONTINUE at the PRE scene), v4 loading and rejecting a bad step.
  test_scores / test_sound read version 4 (v4_image, parse_save). Golden changed on purpose: story_goal (dmg + cgb),
  the banner now says CHAPTER 1 OPENING and the opening's goal SERVE 8 COWBOYS (HUD S08) [10th venue, 2026-10-11: OPENING SHIFT].

## Story portraits as built (approved style S3, 2026-10-10)
The owner approved the portrait study's style S3: 56x56 busts (7x7 tiles), up to 3 CGB BG palettes, an optional 1-OBJ
accent. The final cast is imported pixel-exact: all 11 speakers and two variants (13 portraits); no placeholders left.
- Sources: assets/story/portraits/<name>.txt, the approved final set (portraits/final/src/portrait_<name>.txt) byte for
  byte: spigoteer, spigoteer_cozy, sadie, dregs, dregs_sorry, managerbot, coach, june, colby, aurora, hana, zizz, kiki.
  Spigoteer, Sadie and Manager-Bot were already in the game and are unchanged (identical files). dregs.txt is now the
  "sheepish" drawing (owner's choice for his main portrait; it replaced the round 3b Dregs). Owner's final picks
  (re-imported): Aurora's snorkel parka + scarf, Colby's neckerchief, Dregs's slimmer shoulders, the sorry Dregs's arm
  connected; Coach, June, Hana and Kiki enlarged to the cast's scale with skin shading, Kiki's textured helmet and hair
  edge. Format: portrait-v2
  (docs/story.md "Portraits": `@size`, `@maxpal`, `@key` = char, DMG shade, #rrggbb, name, optional `obj=<base>`; then
  the pixels). assets/story/portraits.json points every speaker at his art with x 2, y 6.
- Variants (data, not scene checks): portraits.json `"variants": {NAME: {art, from, to}}` on a speaker; `from` / `to` are
  'SCENE' or 'SCENE:page' (pages from 1, inclusive, script order; no `to`: the end of the game). gen_story
  assign_portraits resolves each page's portrait id; the build fails on a range naming no scene / page, a given page
  that is not the speaker's, two variants on one page, a variant no page uses. As built:
  SPIGOTEER COZY from PRE_IGLOO:3 (his "IT'S... VERY COZY." right after Aurora knits it on page 2) to the end: every
  Spigoteer page of PRE_IGLOO .. FINALE (he has no CREDITS page). DREGS SORRY FINALE:4 .. FINALE:4, his apology "SORRY I
  BROKE IT." (his only FINALE page, so "the apology" and "all his FINALE pages" are the same page).
- Portrait ids: a speaker's index = his main portrait; variants after the speakers (12 SPIGOTEER COZY, 13 DREGS SORRY;
  11 NARRATOR has none). The script stores the portrait id per page (no extra byte); story_page_get returns the speaker
  (st_pid_spk, for the name tag) in dst[0] and the portrait id in dst[55]. story.c: story_pid (the page's portrait),
  story_cur = the portrait id on screen; a page whose portrait differs (another speaker or the same speaker's variant)
  swaps. Scene headers list portrait ids (at most 3 a scene: a variant is one more).
- Placeholders removed: gen_story's placeholder() / FONT3 / "tint" and the old repo-format art path (palettes / attr /
  overlay in the json) are gone; a speaker without portrait-v2 art fails the build ("no art for X"), so do the old keys.
  The INTRO / FINALE / CREDITS picture-slot placeholders are a different thing and stay.
- Converter (tools/gen_story.py parse_v2 / read_v2): the DMG shade of each key is its BG colour index (one tile set for
  both models); per tile the shade -> colour map, packed into the fewest CGB palettes by an exact search; the obj= keys
  become a CGB-only overlay (colours 1-3 of one OBJ palette, greedy 8x16 cells). The build fails on two colours on one
  shade in a tile, more palettes than @maxpal / 3, more than 3 overlay colours, more than 44 unique tiles (new).
- Engine (src/story.c, banked; ROM0 untouched): a picture whose bottom row is 12 stands on the text box: the frame has
  no bottom row, so it is cols 1-9, rows 5-12 and the wipe / swap covers those 8 rows. CGB BG palettes 2-4.
- Budget (build/story.json; scene_budget fails the build on any overflow): unique tiles (exact, no flips) Spigoteer 42,
  cozy 42, Sadie 44, Dregs 34, sorry 38, Coach 38, June 38, Colby 37, Aurora 42, Manager-Bot 37, Hana 39, Zizz 35, Kiki 38
  (<= 44); 3 CGB BG palettes each (Zizz 2). Per scene (all its portraits loaded at its start, then swapped by tile map)
  at most 124 BG tiles of the 163 free (ids 93-255): FINALE (Sadie 44 + sorry Dregs 38 + cozy Spigoteer 42); next
  POST_SALOON 120, POST_IGLOO 118, POST_TEAHOUSE 115; a PRE scene 77-86. OBJ: Sadie's star only (2 OBJ tiles). 27 different direct swaps in
  the script (no narrator between).
- ROM: real ROM0 free 1641 -> 1641 B (game.gb), 1754 -> 1754 B (release.gb). The ROM grew from 128 KB to 256 KB
  (-Wm-yoA: 9 banks used, bank 8 new); autobank repacked: banks free after (game.gb, romusage) 1 137, 2 116, 3 15,
  4 159, 5 47, 6 40, 7 112, 8 14304 B (before: 1 93, 2 195, 3 116, 4 51, 5 68, 6 187, 7 2006). The portraits
  (story_portraits.c) are in bank 1.
- Tests (tests/test_story.py): test_every_page_shows_its_portrait walks every page of INTRO, all PRE / POST scenes and
  the FINALE on DMG and CGB (a POST scene: the Opening won as the chapter's last step): each page's portrait pixel for
  pixel from its source (DMG shade / CGB RGB15 colour, so the palettes in force), its frame on the box, its tile map the
  scene's own copy (nothing of the previous portrait left), the name tag, the overlay count; a narrator page wipes the
  frame back to the backdrop (the venue, or the picture slot); the swaps seen are every direct pair of those scenes (27
  in all). Also: the variant rules from the script, bad variant ranges fail, no art fails, the scene budget fails at one
  tile less than the busiest scene, the converter round trip for all 13.
  Goldens: story_placeholder (POST_SALOON page 3, Dregs) is renamed story_dregs and changed: Dregs's portrait replaced
  by the owner's choice (the sheepish drawing). New: story_aurora (PRE_IGLOO p1), story_spigoteer_cozy (PRE_IGLOO p3),
  story_zizz (PRE_SPACE p3), story_dregs_sorry (FINALE p4). story_portrait, story_spigoteer, story_managerbot,
  story_narrator unchanged.

## Story lives as built (owner's rule, 2026-10-10)
The owner's lives rule (docs/minigames_bosses.md section 8) replaces "retry only the failed shift". Arcade is unchanged.
- Lives: 3 per venue (chapter). story.c venue_start sets them when the chapter's first playable step (Opening) starts;
  shift_start no longer touches them, so they carry Opening -> Happy hour -> [mini-game] -> Last call -> [boss] and
  are never refilled between shifts.
- The last life lost (enter_game_over -> story_fail, as before) shows TRY AGAIN, then the venue restarts at the
  Opening's goal banner with 3 lives (no PRE scene; story_restarts counts them for tests). The score carries on, as it
  did on a retry: story scores never enter the top 5, so restoring the venue's start score would buy nothing, and a
  score that never goes back is easier to read.
- The clock (chapters 4, 5): the time running out costs a life (story.c's choice; the owner's rule does not cover it)
  and that shift is played again from its banner with the lives left; when it was the last life, the venue restarts.
  So a timed shift can no longer be retried for free.
- Strict rules (chapter 2: a patron at the tap, F_NO_TAP; chapter 7, the teahouse (chapter 8 since the 10th venue): a broken glass, F_NO_BREAK) no longer fail the
  shift. story_play sees the life lost that frame (life_lost, plus a break that frame or not) and takes a second one
  (only one when one was left; 0 sets game_over and the venue restarts after the freeze). The cue: show_overlay("2 LIVES
  LOST") in the banner window over the freeze (resume_after_life now clears overlay_on, so it goes with the freeze), and
  the lost mugs (story_pen: 2, or 1) blink together, 8 frames on / 8 off, through the 120-frame freeze
  (story_life_frame, banked, called from main.c's GS_LIFE_LOST case only in story mode; its last frame puts the HUD
  back). The other way to lose a life in those chapters (a break in 2, a patron at the tap in 7) costs 1 as usual.
  New golden story_two_lives (chapter 2's Happy hour, the frame the two lost mugs light up).
- Banners (gen_story SHIFTS / CHAPTERS, docs/story.md tables, every shift of the two chapters): line 2 states the cost,
  "FAN AT TAP COSTS TWO" (chapter 2) and "BROKEN CUP COSTS TWO" (chapter 7), line 1 keeps the goal (SERVE 10 FANS /
  SERVE 20 FANS / 22 FANS RUSH IN; SERVE 7 GUESTS / SERVE EVERY GUEST / SERVE 15 GUESTS). The banner has no story font
  (HUD glyphs only: no '-' or ':'), so "-2 LIVES" could not be written. The tables' engine cells now read "..., a fan
  at the tap costs 2 lives" / "..., a broken glass costs 2 lives" (gen_story's md-table check follows). Owner-approved
  script change: COACH's page in PRE_STADIUM is now LET ONE FAN REACH / YOUR TAP AND IT / COSTS TWO LIVES!, HANA's in
  PRE_TEAHOUSE SERVE WITH CARE. / ONE BROKEN CUP / COSTS TWO LIVES. (POST_TEAHOUSE said NOT ONE CUP BROKEN, which was
  no longer always true: decided, see "Story page text variants as built".)
- Gold medal: story_bonus_life() (BANKED, story.c) adds a life up to MAX_LIVES 4 and redraws the HUD; the mini-game
  framework calls it on a gold medal. Tests call it directly (test_story.call_banked: a stub below SP that calls
  ___sdcc_bcall_ehl and returns to the interrupted PC).
- HUD: lives_tiles is 4 tiles at columns 8-11 (render.c queues 4, main_cold draw_lives draws 4). Columns 9-11 are lives
  1-3 exactly as before; column 8 (blank in every HUD so far, between the score and the mugs) holds the 4th, bonus,
  mug, which is the first to go. Arcade never has more than 3, so its HUD and every golden are unchanged; the story
  goal counter keeps columns 12-14. New golden story_bonus_life (4 mugs, chapter 1's Opening).
- Save / CONTINUE: lives are not saved. Byte 35 keeps its version-4 meaning and values (a step of the chapter not yet
  cleared, 0-4) but is now the furthest step reached there: story_level_done saves max(reached, the next step) while
  the chapter is the saved one, so a venue restart and the shifts won again never lower it (Practice unlocks from it).
  CONTINUE starts the first chapter not cleared over: its Opening banner with 3 lives when a step of it was reached
  (byte 35 > 0; the PRE scene was seen), else its PRE scene. No SRAM version bump: the bytes, their ranges and the
  checks are unchanged and a version-3 migration (step 0) still means "the PRE scene"; an old v4 save with a step
  simply resumes at the venue's start, which is the new rule.
- Boss engine (built: "Boss engine as built"): a boss keeps his damage after a lost life (the meter is not refilled by
  resume_after_life); only a venue restart (lives 0) starts him over, with the venue. The boss fight uses the venue's
  lives (no refill on entering it), the gold-medal life included.
- ROM: real ROM0 free 1671 -> 1641 B (game.gb), 1784 -> 1754 B (release.gb), 30 B: prep_hud's 4th tile, the 4-tile
  HUD queue and the story_life_frame call in GS_LIFE_LOST. Banks after (romusage, game.gb): 1 93, 2 195, 3 116, 4 51,
  5 68, 6 187, 7 2006 B free.
- Tests (tests/test_story.py): lives carry across shifts; the last life lost in every chapter's Last call restarts the
  venue at its Opening with 3 lives, keeps the step reached (also after winning the Opening again) and the score; three
  lives lost in the Opening; time up costs a life and retries the shift, the last one the venue; chapters 2 and 7, every
  shift: the banner line, 2 lives, "2 LIVES LOST", the blink, the shift going on with 1, the next break restarting the
  venue; the other cause costs 1; story_bonus_life gives 4 (HUD 4 mugs), capped at 4, carried into the next shift, the
  bonus mug lost first; CONTINUE mid-venue starts at the Opening with 3 lives; CONTINUE from step 2 / 3 keeps the step
  reached; arcade keeps 3 lives for the run (not refilled at level 2, column 8 empty). to_shift now reaches a shift
  through CONTINUE (the Opening) and one SHIFT CLEAR. The retry-only-the-shift tests and the CONTINUE-at-a-shift tests
  were replaced. New goldens story_two_lives and story_bonus_life (dmg + cgb). Golden changed on purpose:
  story_last_call (dmg + cgb): the banner is the same, but the test now reaches chapter 9's Last call by winning its
  Opening first (CONTINUE starts the venue over), so the HUD score shows the Opening's 1000 clear bonus and one patron
  sprite differs (the arrivals moved on).

## Story page text variants as built (owner's decision, 2026-10-10)
Hana's POST_TEAHOUSE page 1 depends on the teahouse run: NOT ONE CUP / BROKEN. THAT IS / RARE. THANK YOU. when no cup
broke, SO FEW CUPS / BROKEN. THAT IS / RARE. THANK YOU. otherwise (both fit: no rewrap).
- Data, not a strcmp: docs/story.md writes a variant as a block "SPEAKER IF CONDITION" right after the page it replaces
  ("Script format" there). gen_story CONDITIONS names the conditions (ids 1-8; only GLASS_BROKEN = 1 so far); the
  script stores a variant before its page as portrait id | 0x80, the condition id (one byte), its 3 lines. The page's
  speaker and portrait stay the page's. Fails the build: an unknown condition, a variant with no page above it or of
  another speaker, the same text as its page, two variants with one condition on a page (and the usual line checks).
  build/story.h has COND_GLASS_BROKEN 0x01; build/story.json gives each page its "variants" and the "conditions".
- Engine (src/story.c, banked): story_conds (1 byte WRAM) holds a bit per condition; story_page_get(s, p, conds, dst)
  returns the first variant whose bit is set, else the page. GLASS_BROKEN is set in story_play on exactly the strict
  rule's event (a life lost with a glass broken that frame: the code path that charges chapter 7's two lives; in any
  shift of any venue) and cleared by venue_start, i.e. the start of every venue attempt: the first entry from its PRE
  scene, the restart after the last life, CONTINUE. So POST_TEAHOUSE sees the attempt that ended in it.
- ROM: real ROM0 free 1605 -> 1605 B (game.gb), 1718 -> 1718 B (release.gb). Bank 4 (story.c, story_data.c) 144 -> 24 B
  free: the script 5947 -> 5994 B (the variant page, 47 B), the rest the variant walk in story_page_get and the flag.
- Tests (tests/test_story.py): the variant data and docs/story.md agree; six bad variants fail the build; chapter 7
  cleanly (Opening won, then the venue) -> NOT ONE (new goldens story_hana_not_one, dmg + cgb); a cup broken in the
  Opening, kept through the Happy hour -> SO FEW (new goldens story_hana_so_few); cups broken in an attempt that lost
  its last life are forgotten by the restart -> NOT ONE.

## Perfect pour as built (owner Q6, 2026-10-10; art is a PROPOSAL until the owner approves it)
Part of pouring in every story shift (later every boss; the mini-games are excepted). Arcade is unchanged: none of the
new code runs there (pour_frame / perfect_catch are called only when story_on, pour_q stays 0), its fill_timer, fill
frames, scores and VRAM are as before, and no existing golden changed.
- Window (owner, four rounds: 16..27 "too easy" (opened the moment the drink was full); 24..29 "still a bit too
  easy"; 32..36 "length right, should happen sooner"; now 27..31): fill_timer (main.c) still stops at FILL_FRAMES
  16. src/pour.c pour_frame (banked, called from main.c's draw block in story mode, after every other sprite) keeps
  pour_t: 16 on the frame the drink is full, +1 a frame while A is held, up to the window's end. A release launches
  with the last held frame's pour_t:
    16..26  full, settling (11 frames, 183 ms, the plain full drink): ordinary, no bonus, no overflow
    27..31  the sparkle window, POUR_WIN_START 27, pour_win POUR_WIN_LEN 5 (83 ms): PERFECT
    32..    the overflow: ordinary
  The press-to-release time for a perfect drink is 27-31 frames (450-517 ms). Releasing on the first full frame, or
  while it settles, is never perfect (the scripted sweep checks every release frame). Note: a reaction to "full" of
  11-15 frames (183-250 ms) lands in the window; the owner chose this start by playing (24 too easy, 32 too late).
  Practice HARD hook: pour_win is WRAM, set to POUR_WIN_LEN by pour_load at every shift start; HARD writes
  POUR_WIN_HARD 3 after it (same start, 27..29; tested). A full drink carried to another bar (A held through Up/Down)
  jumps to the overflow at once: ordinary.
- Look: pour_t 16..26 the plain full drink (draw_fill's, unchanged), 27..31 the venue's SPARKLE frame in his hand, 32+
  its OVERFLOW frame (OAM 4 over draw_fill's full drink; CGB the full-drink palette 1; DMG OBP1, so the drink also
  darkens in his hand when the window opens and the light foam shows on the white wall).
- Quality: pour_q (WRAM) -> spawn_mug writes it into the new full mug's mug_timer (0 before: mug_timer is unused while a
  full mug slides; it becomes the empty's step phase / the glass timer later, both reset as before). No new array.
  WRAM: pour_q, pour_t, pour_win, cue_t / x / y, perfect_n, pour_bar: 8 B.
- Score: patrons.c caught() calls perfect_catch(i) in story mode; a mug_timer of 1 scores 2 x serve_score on the spot
  (saloon 50 -> +100). The serve (the patron pushed out) still scores serve_score as always; regulars take any drink.
  perfect_n counts perfect catches (tests; a later results screen).
- Cue (the owner's pick after four tries: round 1's twinkle over x2, a redrawn dark-on-light x2, a 4-sprite PERFECT
  word over x2, round 1's again; final: "the x2 by itself"): assets/art/pour_cue.txt, one 8x16 OBJ: the "x2" badge
  alone (dark badge, light text) in its lower half, where it always was (rows 8-14: at the caught drink's height on
  the counter, which reads better than the twinkle's spot at face height; the top half is blank), OAM 26 (unused since the door puff), the full-drink palette (DMG OBP0), 16 px right of the caught mug
  on its 16 lines, 48 frames, blinking the last 16. Sprites per line: pour_frame counts every other OAM entry
  touching any of those 16 lines (an upper bound per line) and leaves the cue out on a frame where that is 10 or
  more, so it is never an 11th object (test: bartender 4 + held drink + 6 empties on the bar: the cue goes, no line
  passes 10). The lift estimate (lift.c) is untouched: the cue gives way, never a patron. The show's OAM 28-39 are
  not used.
- Tiles: the drink's own OBJ slots (56-59, 60-75 crash, 76-83 fill, 84-91 drink) are full, so the 2 new frames + the
  cue sit at OBJ 234-239 (sparkle 234-235, overflow 236-237, cue 238-239): OBJ ids >= 128 share VRAM with BG ids >= 128,
  the patrons use BG 78-233 and the DMG copies OBJ 240-245 (246-255 free); game.h fails the build on an overlap. A
  cut-scene's portraits overwrite that range, so story.c shift_start loads them (pour_load(chapter), LCD off) at every
  shift start; arcade never loads them.
- Art (easy to swap): assets/art/pour/<venue>.txt, 2 frames 8x16 each (SPARKLE, OVERFLOW) in the venue's full-drink
  colours, drawn over its full frame (round 2: the lumber lodge's twinkles are cream; the brown ones vanished on its
  brown wall), and assets/art/pour_cue.txt; tools/gen_pour.py -> build/pour_art.h (src/pour.c's bank), build/pour.json
  (tests), out/preview/pour_<venue>_x8.png. Replacing the files and running make is the whole swap. Proposal sheets
  (scratchpad perfect_pour/): proposal.png (round 1), proposal2.png (round 2), proposal3.png (the PERFECT word, not
  taken).
- ROM: real ROM0 free 1641 -> 1605 B (game.gb), 1754 -> 1718 B (release.gb): 36 B for the three hooks (spawn_mug's
  pour_q, caught's story test + call, the draw block's story test + call); the later rounds cost ROM0 nothing.
  pour.c + its 608 B of tiles autobank to bank 7 (2006 -> 1039 B free). Perf: arcade runs the same code paths (one
  story_on test per frame and per catch); story adds a banked call per frame and the cue's 40-entry count while it
  shows.
- Tests (tests/test_pour.py, DMG + CGB): every release frame swept: the first launching release (the first full
  frame) and the 10 settling ones ordinary, the next 5 perfect, then ordinary; HARD (pour_win 3) 3 perfect at the same
  start; releases at pour_t 27 and 31 score 2 x serve_score at the catch with the cue; past the window it runs over
  (overflow frame, stays there) and scores nothing extra, no cue; the frames in his hand: fill, plain full x11, sparkle
  x5, then the overflow, palette 1 / OBP1; carried -> ordinary; the venue's frames and the cue in VRAM (chapters 1,
  6); arcade: no pour_t, the old full fill frame on OBP0, no bonus, no cue, no perfect release frame; the 10-per-line
  limit with the cue. Goldens pour_sparkle, pour_cue (dmg + cgb, new with this feature; pour_cue shows the x2 alone,
  the owner's final pick). No golden from before the perfect pour changed.

## Mini-game framework as built (M11e step 1, docs/minigames_bosses.md 2.1, 2026-10-10)
The framework every story mini-game will run in, with one stub game that proves it. The story's mini slots stay
NOT_BUILT (gen_story) until real games exist; the story side is ready for them.
- Already there (M11d / story lives): the segment flow PRE -> Opening -> Happy hour -> [mini] -> Last call -> [boss] ->
  POST (story.c step_start / next_step), SRAM v4 with byte 35 the furthest step reached. Not redone.
- GS_MINI (13): main.c's switch calls the banked mg_update(pressed); 1 = it left (the next screen is up), as GS_STORY.
- src/mg.c (bank 255; autobank put it in bank 6 with the stub): mg_enter(id, mode) with the LCD off: everything hidden,
  patrons / mugs / tip / show cleared, the venue loaded (id = the venue / chapter; MG_STUB 9 uses the saloon), the HUD
  glyphs, the medal icon at BG MG_BG 77..124, the HUD (score; columns 16-19 the timer or blank, no level number), the
  venue's plain backdrop (counter row 11), the CGB attributes of the HUD row, the banner rows 2-3 and the result window,
  the game's enter (its BG from MG_GAME_BG 125), the banner (name, instruction), the venue's tune, GS_MINI.
  Phases (mg_phase): MG_INTRO 90 frames (the banner) -> MG_COUNT 60 (READY, GO at 30; A skips it in practice only) ->
  MG_PLAY (the game's update; the timer counts mg_timer down, the HUD 'T' + 3 digits on each new second, story.c
  hud_goal's format; at 0 "TIME UP" and MG_END) -> MG_END 60 frames (the game's update still runs: its outro) ->
  MG_RESULT: the window rows 32-37 (panel, name, SCORE n, the medal word + its points, the prompt, panel; the text
  centred in columns 4-19, mg_say's row shifted 2 columns before the VBlank copies it; the 4x4 icon at columns 0-3 of
  rows 1-4), queued 2 rows a frame (40 B, the bonus rounds' per-frame size), then shown (overlay_on, LYC at
  BANNER_WY + 46 for its 48 px). Story: "A CONTINUE", A taken once it has shown 60 frames (mg_t >= 63), then
  story_level_done: the next step (Last call), the save, whatever the medal (owner: mini-games never block the story).
  Practice: "A RETRY B MENU", A = mg_enter again (score from 0), B = the title for now (the practice menu is step 10).
  Leaving puts back the window's rows 32-34 (panel, blank, panel) and their attributes, and LYC = BANNER_LYC; nothing
  else: the next level load restores the rest, as after a bonus round.
- Modes: MG_STORY 0, MG_PRACTICE 1, | MG_HARD 2 (owner Q7's HARD toggle: the flag the games read; the stub's HARD has
  shorter waits and steeper points). Practice starts the score from 0; the story's carries on.
- Medals: per game three thresholds on mg_score (medal_at[game]; the stub 1500 / 3000 / 4000). The result adds the
  medal's points to the score (bronze 500, silver 1500, gold 3000, spec 2.2) and, in the story, a gold medal calls
  story_bonus_life() (owner: +1 life for the venue, at most 4; no boss-only life). The icon: assets/art/mg_medal.txt,
  3 looks of 32x32 (a round medal numbered 1 / 2 / 3, no ribbon; approved by the owner 2026-10-11, option A; 48 tiles,
  MG_ICON_N = 4 in mg.h) on the HUD band; CGB
  BG palette 4 = the medal's metal (gold, silver, bronze; the HUD's own colours for no medal), written at the top of
  the result's first frame; DMG: the BG greys. tools/gen_mg.py -> build/mg_art.h, out/preview/mg_medal_x8.png.
- Helpers for the games (BANKED, mg.c): mg_points(n) (mg_score + add_score: the HUD stays live), mg_finish() (-> END),
  mg_rand() (16-bit xorshift on mg_seed; the bar's RNG untouched), mg_spigoteer(x, y, frame, left) (OAM 0-3),
  mg_number(dst, n). RNG: mg_seed = mg_seed_force when non-zero (tests), else two next_rand() bytes at entry. Each game
  is xx_enter() / xx_update(pressed) in its own file, dispatched by a switch on mg_game (no banked function pointers);
  until a venue's own game is built its id plays the stub. Per-game tables in mg.c: name, instruction, medal_at.
- mg_say(row, s) (ROM0, main.c, ~150 B): a string centred in HUD glyphs into one of 4 WRAM row buffers (round robin:
  at most 4 lines a frame), queued, or written at once while the LCD is off; it returns the buffer (the result patches
  the icon in). ROM0 because the strings stay in each caller's own bank (the rule: no pointer to banked ROM data into
  another switchable bank; a ROM0 callee keeps the caller's bank mapped): it holds. show_overlay is now mg_say(33, s) +
  its flags. bonus.c (make_text / say) and bonus2.c (text / sayA / sayB / banner's text) use it; their buffers are gone
  (WRAM: show_overlay's 20, bonus2's 40, bonus.c's 20). bonus2's '!' comes from say_bang (main_cold.c glyph_for, set
  by bonus2_enter to its own tile, 0 = blank); glyph_for also maps J Q X Z now. Bonus-round goldens unchanged.
- WRAM union (src/mg.h): story.c's bd_map + bd_attr are now one exported story_scratch[STORY_SCRATCH] (520 B, game.h;
  story.c checks STORY_PIC_ROWS * 40 == STORY_SCRATCH); union mg_ram { struct stub_state stub; } over it through
  MG = (union mg_ram *)story_scratch, with a static size assert (a negative array size on overflow). Safe: no cut-scene
  runs during a mini-game, and every scene_enter rewrites the buffer.
- Story side (story.c): step_start dispatches on the step's kind: STEP_MINI -> mg_enter(story_chapter, MG_STORY), else
  a shift. next_step also plays a STEP_SKIP step whose bit is set in story_unskip (1 B WRAM, a test hook; 0 in play),
  which is how the test marks the mini slot built. Nothing else changes until gen_story takes MINI out of NOT_BUILT.
- The stub game, GREEN LIGHT (src/mg_stub.c, bank 6): a lamp (BG 2x2 at columns 9-10, rows 6-7, CGB BG palette 2;
  assets/art/mg_lamp.txt, placeholder) shows red 45-108 frames (HARD 30-93), then green; A on green scores
  1000 - 20 x the reaction frames (HARD 30), at least 100 ("920 POINTS"); A on red TOO SOON, none within 60 frames TOO
  SLOW (0 each). 5 rounds, a 30 s timer. The Spigoteer stands at x 72 (catch pose on a hit, fail pose on a miss).
  State: struct stub_state, 20 B of the union (tests read story_scratch + 0..4: state, round, t, wait, react).
- Test hooks: mg_id, mg_mode, mg_phase, mg_t, mg_timer, mg_score, mg_medal, mg_seed, mg_seed_force, story_unskip;
  poking mg_phase = MG_RESULT ends any game (the bonus rounds' phase-4 convention).
- ROM: real ROM0 free 1605 -> 1548 B (game.gb), 1718 -> 1661 B (release.gb): 57 B = mg_say over the old show_overlay
  (~40 B net) and the GS_MINI case. mg.c + mg_stub.c (+ the 2 art headers) ~3.1 KB in bank 6; autobank repacked:
  banks free after (game.gb, romusage) 1 205, 2 116, 3 232, 4 298, 5 47, 6 11, 7 195, 8 9480 B.
- WRAM: +72 B (_DATA 6183 -> 6255): mg_say's 4 x 20 + its index, say_bang, the mg_* hooks (14), the result's buffers
  (55: score / medal text, a panel row, the timer row), story_unskip; minus the 80 B of text buffers it replaced. The
  games' own state costs nothing (the union).
- Perf: arcade untouched (one more case label in the state switch; show_overlay does what it did); a mini-game frame is
  light (the stub: a few compares, at most 2 text rows + a lamp row queued).
- Tests (tests/test_mg.py, DMG + CGB; every frame checked at <= 10 sprites a line with test_bonus.lines): the whole flow
  in practice (banner, READY / GO, five rounds, the points rule, the timer counting, WELL DONE, the result window's rows,
  gold, score + 3000, no life in practice); RETRY (score from 0) and MENU (the title); A skips the count in practice,
  not in story; TOO SOON / TOO SLOW; HARD; mg_seed_force repeats a game; the timer ends the play (TIME UP, T000); the
  medal thresholds at 0 / 1499 / 1500 / 2999 / 3000 / 3999 / 4000 / 5000 (word, points, icon tiles in VRAM, CGB
  palette 4 and its attributes, the HUD colours with no medal); mg_say in ROM0 and the bonus rounds on it; the union
  over story_scratch; MENU then arcade with everything back (venue rows, show OBJ tiles, patron tiles, window rows, LYC,
  OBP1 0xE4, the saloon's bank-1 tiles and extra palettes); the mini slots still NOT_BUILT; a built mini slot (story_unskip)
  plays after the Happy hour (mg_enter(0, MG_STORY)), A CONTINUE only after 60 frames, gold = 4 lives (and none = 3: the
  story goes on either way), then the Last call's banner with the lives carried, step 3 saved as reached, and the
  restore checks after the Last call's level load. tests call mg_enter through a PyBoy hook on vq_frame_end that diverts
  the CPU once into a stub (the two byte arguments on the stack, ___sdcc_bcall_ehl) between two frames.
  New goldens (dmg + cgb): mg_intro (the banner), mg_result (practice, gold), mg_story_gold (story, gold, 4 mugs). No
  existing golden changed. Screens of each phase: out/mg/{intro,count,play,result,result_gold,story_intro,
  story_result}.{dmg,cgb}.png.

## Boss engine as built (M11e step 2, docs/minigames_bosses.md 2.5 / 3.1-3.3, 2026-10-10; Big Tex's art is a PLACEHOLDER)
One engine with a parameter row per boss and a per-boss special hook; Big Tex (the saloon) is the only row so far, and the
saloon's boss slot is played in the story (gen_story BUILT_SLOTS = {"BOSS": {"SALOON"}}; the other eight boss slots stay
STEP_SKIP until their bosses exist). Chapter 1 is now Opening -> Happy hour -> Last call (SHIFT CLEAR) -> the fight
(CHAPTER CLEAR) -> POST_SALOON.
- src/boss.c (bank 255; autobank put it in bank 2, 3.6 KB with its art): rows[BOSS_COUNT] (BOSS_COUNT 10 in game.h, one
  row per venue: the 10th venue adds a row, not a constant; a row with width 0 is not built and plays row 0's, which is
  what the story_unskip test hook gets for another venue's slot): width, start x, bar, step (frames per 8 px stomp), push
  (px per catch), gulp, hands, sip, meter, the topper's x, the art, the banner's two goal lines. Tex: 40, 16, bar 1, 120,
  16, 40, 3, 60, 8 (spec 3.2), "BIG TEX RIDES IN" / "QUENCH HIM 8 MUGS" (spec 7). boss_special() is the per-boss hook (a
  switch on boss_id later; empty for Tex).
- Story (story.c, banked; nothing in ROM0): step_start calls boss_set(chapter) for a STEP_BOSS step and boss_set(BOSS_NONE)
  for any other (story_level_done and start_new_game turn it off too); the fight then runs through shift_start like a
  shift: boss_goal fills story_goal (type G_BOSS 3, walk 100 %, spawn BOSS_SPAWN_PCT 150 %, the two lines), the banner's
  first line is "CHAPTER n BOSS" ("BOSS" since 2026-10-11), boss_begin after shift_pace. story_play calls boss_frame every PLAYING frame (not the
  frame a life went); when it reports the meter empty: story_phase SP_OUTRO (5), GS_STORY, boss_outro for 120 frames (the
  HAPPY pose, the mugs and the fill gone, the regulars frozen, the hat bobbing), then story_win: CHAPTER CLEAR with the
  level bonus, the POST scene, the chapter saved as cleared. hud_goal draws nothing for G_BOSS.
- Lives (owner's rule): the venue's lives carry into the fight (a gold medal's 4th included; no refill). A lost life: the
  freeze, then reset_actors -> boss_reset: he starts again at x 16 on his bar with empty hands, his meter kept. The last
  life: TRY AGAIN, the venue restarts at its Opening (venue_start -> step_start -> boss off); the next fight starts with a
  full meter. The strict rules (chapters 2 and 7) are not wired into fights yet: boss_goal's flags are 0 (the stadium and
  teahouse rows will need F_NO_TAP / F_NO_BREAK).
- Rules (spec 2.5): he stomps 8 px every `step` frames (the STOMP pose for 8 frames, SFX_SHAKE as the thud; nothing moves
  during the level's 90-frame intro); his right edge at SPOUT_X (136) costs a life. A full mug on his bar at mug_x <=
  boss_x + W - 4 is caught (boss_lim = boss_x + W - 3, 0 while his hands are full): the mug is freed, serve_score (and a
  perfect pour's bonus and cue: perfect_catch, the story's rule in every fight), meter -1, push-back 16 px in 8 px hops
  every 4 frames (WINCE) down to his start x at most, GULP until 40 frames are over (no stomp), one more empty held. With
  full hands (3) the mug slides past him (over the BG figure) and breaks at the left end. Each held empty goes `sip` (60)
  frames after the catch or the last one sent, and only when the fair-empties schedule allows (its travel from his right
  edge at 0.5 px a frame >= next_arrival; then next_arrival = travel + empty_gap: the patrons' rule), spawn_mug at his
  right edge. His hand column shows the empties he holds (0-3; WALK / STOMP / WINCE). Unhit, Tex reaches the tap in 1200
  frames.
- Regulars (owner Q10): the level row's speeds on the other bars; boss_begin draws an 8-entry arrival pattern (the story's
  pat_buf / pat_len, wait code 0) over the three other bars with next_rand(), pat_wait[0] = the spawn interval x 1.5 (the
  saloon: 450 frames; its Happy hour 300); patrons.c try_spawn (ROM0) turns variant C into A or B while boss_on
  (rng_state & 1), show.c place_start_patrons skips his bar and does the same; tip_chance 0 (no tip, so no show), back
  to TIP_CHANCE_DEFAULT when the fight is over.
- Picture: his body is BG on his bar's two wall rows (render.c compose_bar stamps boss_cols over the bar after its
  patrons: one compare per composed bar; stamp_boss = put_col per column, top tile t, bottom t + 1, BG palette boss_pal);
  boss.c marks only what changes (a pose: tile ids of his columns; a move: the span between the old and new columns,
  attributes too). The topper (the hat's crown, one 8x16 OBJ, its upper half above his bar): OAM 28 (the dancers' first
  entry: no show in a fight; spec 2.5 said OAM 26, which the perfect pour's cue took since), OBJ tiles 96-99, CGB OBJ
  palette 7 (his colours 1-3), DMG OBP1 0xE4. Drawn by boss_draw from pour_frame (story, after every other sprite of the
  frame): every other OAM entry is counted on the four 4-line bands of the topper's 16 lines it touches (an upper bound
  per line; spec 3.1's bands); a band already at 10 leaves the topper out that frame.
- VRAM / palettes at the level load (main_cold.c enter_level_screen: boss_load after start_level, LCD off): his body's
  column pairs over variant C's shifted tiles (BG 162-203, 21 pairs), then its shift-0 pose + the back views (216-233, 9
  pairs), the HUD face + the meter's EMPTY / HALF / FULL at 252-255, the topper at OBJ 96-99; CGB BG palette 4 = the
  venue's wall + his colours 1-3, OBJ palette 7 his colours 1-3. The pour frames at OBJ 234-239 stay (a fight has the
  perfect pour). The next level load (any venue's) puts back all of it: load_patron_group (every variant, the back
  views, BG palettes 2-4), load_venue (the show's OBJ tiles), lift_level_init (OBJ palettes 3 / 6 / 7, OBP1 0xE4),
  draw_hud (the HUD row), start_mask from the level row (boss.c never writes it).
- HUD: score 1-6 and lives 8-11 as always, column 12 his face, 13-19 the meter (2 pips a tile; Tex's 8 = 4 tiles, the
  rest blank), redrawn on every catch through the VBlank queue (boss_hud); no goal counter, no level number.
- Art (assets/art/boss/, tools/gen_boss.py -> build/boss_art.h, build/boss.json, out/preview/boss_*_x8.png): big_tex.txt
  (WALK, STOMP, GULP, WINCE, HAPPY 40x16; HAND1-3 8x16; HAT_STILL / HAT_BOB 8x16; ICON 8x8) and meter.txt (EMPTY, HALF,
  FULL), each headed "PLACEHOLDER: art proposal pending owner approval": a generated silhouette (hat, moustache, red
  shirt, belt, steins) in the right palettes; the real art goes to the owner separately. The body is stored as column
  pairs, identical columns shared (Tex 25 of BOSS_PAIRS_MAX 30; the build fails on more). Colours (gen_boss BOSSES): skin
  #F0B888, shirt #C83020, hat #583018; DMG greys by index (skin light, shirt dark, hat and outline black). Replacing the
  files and running make is the swap.
- Test hooks (spec 2.5): boss_on, boss_id, boss_bar, boss_x, boss_hp, boss_hold, boss_state (0 walk, 1 gulp, 5 outro),
  boss_t, boss_special_t, boss_hook (2 = meter to 1, 3 = satisfied now; 1, the special's tell, has nothing to do yet),
  boss_lim, boss_pose, boss_push, boss_hits, boss_step / boss_hands, boss_hard (Practice's HARD toggle, owner Q7: a
  quarter shorter step, one hand fewer; set before the fight's step starts; the practice menu is step 10).
- ROM0 (real, tools/rom0free.py): 1548 -> 1447 B free (game.gb), 1661 -> 1560 B (release.gb): 101 B (the spec estimated
  ~205): catch_full's test + banked call and try_spawn's variant mask (patrons.c, 53 B), compose_bar's compare + stamp_boss
  (render.c, 48 B). Every other hook is banked: reset_actors / enter_level_screen / start_new_game / boot_init
  (main_cold.c), story.c, pour_frame (pour.c), place_start_patrons (show.c). Banks after (romusage, game.gb): 1 205, 2
  211, 3 232, 4 179, 5 47, 6 64, 7 934, 8 4884 B free.
- WRAM: +42 B (_DATA 6255 -> 6297): the boss state (spec ~40 B) and his HUD row.
- Perf: arcade gains one compare per composed bar (render.c), one per catch_full call and one per spawn. The CGB
  realistic-peak scenario (test_perf, a timing-sensitive script) then showed a 4th full mug in flight on one frame (the
  scripted bartender's own launch on top of the scenario's 3; frame timing decides which frame it lands on): its sanity
  check is full_max <= 4 now; frame time unchanged within that noise (CGB end LY 194 -> 195, missed 96 -> 104 of 1200;
  DMG identical to the frame, 192 / 69). A fight (scratchpad perf.py: real pours, the regulars walking, 1500 frames): DMG
  end LY 138, 0 missed; CGB end LY 161, 9 missed. The spec's test_perf plan has a boss scenario only for the moving
  bosses (Mascot, Prototype, Mothership phase 2); none for Tex.
- Tests (tests/test_boss.py, DMG + CGB; every frame of every fight checked at <= 10 sprites a line): the table (10 rows,
  Tex's row, only the saloon built, the placeholder headers); the fight after the Last call (banner, lives carried, no
  tips, the arrival pattern, the spawn interval, VRAM tiles / palettes / OBP1, the HUD, the topper); a win by real pours
  (the hands rule, his empties' arrivals >= empty_gap apart and caught, the outro, CHAPTER CLEAR, POST_SALOON, the save,
  then the stadium's Opening with everything back); the meter after each catch (and a perfect pour's bonus on him);
  stomps every 120 frames (the STOMP pose, the hat's bob), push-back hops and the gulp, pinned at his start; full hands
  let a mug pass and break (the meter kept, the reset after the freeze); the tap costs a life and he starts over with his
  damage kept and nothing of him left near the tap; the last life: TRY AGAIN, the Opening, and VRAM / palettes / OBP1 /
  HUD / his bar's wall exactly as a fresh Opening's; regulars every 450 frames on the other bars only, variants A / B, no
  tips; the topper left out at the 10th sprite and back at 9; HARD; another venue's slot (story_unskip) plays row 0.
  tests/test_story.py: chapter 1's sequence now has the fight (beat_the_boss: its banner, boss_hook 3); its Last call
  says SHIFT CLEAR, the boss step is saved as reached. New goldens boss_fight (dmg + cgb: Tex mid-fight, the meter at 5
  of 8). No existing golden changed. Screens: out/boss/{start,mid,meter,win,lose}.{dmg,cgb}.png.

## Boss hooks as built (wave 1 structure, 2026-10-12; docs/minigames_bosses.md 2.5, section 6 step 4)
Each boss lives in his own banked file, so bosses can be built in parallel. What a new boss touches:
1. `src/boss_<name>.c` (`#pragma bank 255`): `#include "boss.h"`, his generated art `"boss_<name>_art.h"`, then
   `"boss_load.h"`; one dispatcher `uint8_t boss_<name>(uint8_t ev, uint8_t arg) BANKED` that answers BEV_SET with
   `boss_art_set()` and BEV_LOAD with `boss_art_load()` (his pose table into boss_map, his tiles and palettes), and does his
   special on the other events. His own state stays in his file (test hooks: plain globals).
2. `src/boss.c`: his row of `rows[]` (spec 3.2's numbers and the banner lines) and his row of the hook table
   (`boss_call`: `case <row>: return boss_<name>(ev, arg);`); `src/boss.h`: his dispatcher's prototype.
3. `tools/gen_boss.py` BOSSES: one entry (name, width, CGB colours 1-3, `extra` poses in his art file's order of
   use; `ice`: a venue whose counter tiles get icy copies) and his art at `assets/art/boss/<name>.txt` (the build fails
   when the folder and the list differ).
4. `tools/gen_story.py` BUILT_SLOTS["BOSS"]: his venue's suffix (STORY and ARCADE both play the slot then).
- Events (src/boss.h): BEV_SET (boss_set), BEV_LOAD (LCD off, the level loaded), BEV_RESET (the level's start and
  after a life), BEV_BEGIN (the banner up), BEV_FRAME (every PLAYING frame after the intro, after the engine's walk /
  push / empties, before his pose and catch limit), BEV_CATCH (arg = the mug; 1 = he took it himself), BEV_TELL
  (boss_hook 1), BEV_OUTRO (the outro's first frame). 0 from any = the common rules.
- Knobs a special may turn (WRAM, boss.c; reset by boss_set): boss_xpose (an extra pose, BP_EXTRA.., shown over WALK /
  STOMP / GULP; only WINCE and HAPPY show over it), boss_queue / boss_cap (he catches while boss_hold + boss_queue <
  boss_cap; boss_cap = boss_hands), boss_own_gap (his empties' gap after his own last one), boss_window (an empty or a
  return goes only if it arrives within that many frames), boss_fast_full / boss_fast_empty (his bar's full mugs 3 px
  a frame, empties 1 px a frame) and boss_returns (MUG_RETURN mugs on his bar). The engine's state (boss_state,
  boss_t, boss_hold, boss_sip_t, boss_special_t, ...) is global for the boss files. A boss state other than BS_WALK /
  BS_GULP (BS_TELL, BS_SPECIAL) means he stands: no stomp, his step timer kept.
- Helpers: `boss_send(kind)` (one MUG_EMPTY / MUG_RETURN from his right edge when the fair-empties schedule,
  boss_own_gap and boss_window allow; its travel at its own speed), `boss_width()`.
- His bar's extra mug rules are in boss.c `boss_mugs` (banked, run from boss_frame after update_mugs moved the mugs):
  a fast full mug 1 px more, a fast empty 1 px on the frames its own step did not move it, a MUG_RETURN (mug_state 5:
  mugs.c draws it as a full mug and counts it, but does not step it) 1 px a frame right, caught by the bartender as an
  empty, breaking past the right end. No ROM0 code: a first try with per-bar speed tests in mugs.c's full_step /
  empty_step cost 30 B of ROM0 and pushed test_perf's worst pile, overlap and realistic-peak scenarios over their
  guards (one compare per mug per frame everywhere), so it went.
- Art: tools/gen_boss.py writes build/boss_art.h (the meter, BOSS_POSES_MAX 8, BOSS_PAIRS_MAX 30, BOSS_ICE_MAX 2) and
  per boss build/boss_<name>_art.h under common names (boss_art_body / pose / hand / hat / icon / pal, BOSS_ART_*),
  #included only by his own file: his art sits in his file's bank. Extra poses (gen_boss `extra`) follow the five
  common ones (BP_EXTRA = 5, 6, ...). Big Tex moved to src/boss_big_tex.c (his art only; no special); nothing of
  him changed (golden boss_fight and every test_boss test unchanged).
- ROM: ROM0 unchanged. Every boss file autobanks (see "Boss wave 1 ROM" below).

## The Sasquatch as built (lumber lodge boss, docs/minigames_bosses.md 3.5, 2026-10-12)
- src/boss_sasquatch.c, rows[2]: 32 px, start 16, bar 2, step 90, push 8, gulp 8, hands 2, sip 0, meter 12, topper
  at 12 (his crest); "NO SUCH THING" / "12 COFFEES FAST". Art: the owner's approved look A round 2
  (assets/art/boss/sasquatch.txt, moved from assets/art/approved/; 22 column pairs; colours face #E8B878, fur
  #5C2C14, outline #140804).
- His empties slide back at 1 px a frame on his bar only (boss_fast_empty), each one as soon as the schedule allows
  (sip 0); between two of his own the gap is SASQ_GAP 80 (boss_own_gap), the regulars' empties keep the level's gap
  (the lodge's 108) from his and his from theirs. Holding two, the third coffee passes him and breaks. No special.
- Story and ARCADE: gen_story BUILT_SLOTS["BOSS"] gains LUMBER; chapter 3 is Opening -> Happy hour -> Last call
  (SHIFT CLEAR) -> the fight (CHAPTER CLEAR) -> POST_LUMBER. No existing golden changed (no test plays the lodge
  past its Last call).
- Tests (tests/test_boss_sasquatch.py, DMG + CGB, every frame <= 10 sprites a line; helpers in tests/boss_common.py):
  his row and art; the fight's start (banner, VRAM, palettes, HUD meter 12, topper); his empties 1 px a frame on his
  bar while another bar's go 0.5, caught at the tap; two in his hands and the third breaks (a life, he restarts with
  his meter); a regular's empty due: his waits for the level's gap and goes on the first frame it may, his next own
  one 80 after; a win by real pours (every empty caught, his arrivals >= 80 apart, the outro, CHAPTER CLEAR,
  POST_LUMBER, saved); stomps every 90, push-back, the tap. New goldens boss_sasquatch (dmg + cgb).

## The Food Critic as built (bistro boss, docs/minigames_bosses.md 3.6, 2026-10-12)
- src/boss_critic.c, rows[3]: 32 px, start 16, bar 1, step 110, push 16, gulp 60, hands 1, sip 90, meter 8, topper at
  9 (the beret's stalk); "THE CRITIC DINES" / "PERFECT POURS ONLY". Art: the owner's approved look 2 "the gourmand",
  round 5 (assets/art/boss/critic.txt, moved from assets/art/approved/; 17 column pairs with TASTE, extra pose 5).
- Perfect = the story's perfect pour (src/pour.c, mug_timer 1), not the spec's older 16..27 window (written before the
  perfect pour existed): the owner tuned that window's start to 27 in four rounds, so the start stays; its length in
  his fight is CRIT_WIN 12 frames (the spec's 12; boss BEV_BEGIN writes pour_win after pour_load), so releases at
  pour_t 27..38 are perfect, the sparkle frame showing all of it. Every shift keeps the owner's 5.
- A perfect drink while he is free: the common catch (the perfect bonus and cue included). A sloppy one while free:
  no meter, no score; he TASTEs it for 30 frames (the TASTE pose; BS_SPECIAL, he stands), then sends it back as a
  MUG_RETURN (the full drink, 1 px a frame) which the bartender catches like an empty (EMPTY_SCORE); past the right
  end it breaks (a life). While busy (his glass held, tasting, or a return waiting) every drink, perfect or not, is
  waved back (a return, no tasting; boss_queue, at most CRIT_QUEUE 3 waiting: the TASTE pose shows while any wait);
  past that (his glass + 3) a drink slides past him and breaks. Returns and his glass go by boss_send: the fair
  schedule holds for both. Test hooks crit_taste, crit_sloppy, crit_waved.
- Story and ARCADE: BUILT_SLOTS["BOSS"] gains BISTRO (chapter 4 ends with the fight, then POST_BISTRO). No existing
  golden changed.
- Tests (tests/test_boss_critic.py, DMG + CGB, every frame <= 10 sprites a line): row and art; the fight's start
  (pour_win 12); the window by real pours (pour_t 26 ordinary, 27 and 38 perfect, 39 ordinary); a sloppy drink
  tasted for 30 frames (he stands), sent back from his right edge at 1 px a frame, drawn as the full drink, caught
  for EMPTY_SCORE; busy, two drinks (one perfect) waved back, his glass and both returns >= empty_gap apart, nothing
  breaks; a full queue lets the next drink pass and break, a missed return breaks at the right end; eight perfect
  drinks win (outro, CHAPTER CLEAR, POST_BISTRO). New goldens boss_critic (savouring) and boss_critic_taste (the
  TASTE tell), dmg + cgb. tests/boss_common.py throw() now pokes between two game frames (logic_paused): a mid-frame
  poke could see update_mugs recount mugs_live to 0 and the mug never moved.

## The Yeti as built (igloo boss, docs/minigames_bosses.md 3.7, 2026-10-12)
- src/boss_yeti.c, rows[4]: 32 px, start 16, bar 2, step 100, push 8, gulp 30, hands 2, sip 60, meter 12, topper at
  9 (his horns); "THE YETI IS COLD" / "12 COCOAS ON ICE". Art: the owner's approved look 1 round 2
  (assets/art/boss/yeti.txt, moved from assets/art/approved/; 26 column pairs with INHALE and BLOW, extra poses 5, 6).
- Icy breath every YETI_EVERY 360 frames of walking (boss_special_t): the tell, 50 frames: INHALE, he stands
  (BS_TELL), the frost creeps along his bar's counter from the left end, 4 columns every 12 frames (the VBlank queue),
  all 18 counter columns icy when it ends; the ice, 180 frames (boss_icy): BLOW for 30 frames, then his standing
  pose (BS_SPECIAL, no stomp), full mugs on his bar 3 px a frame and empties 1 px a frame (boss_fast_full /
  boss_fast_empty, boss.c boss_mugs; only his bar); a held empty may go at once; the thaw: the counter back in 2
  frames (9 columns a frame); then he walks and counts 360 again. A catch in the tell or on the ice shows GULP /
  WINCE as usual; the tell's or the ice's state comes back after the gulp. boss_hook 1 starts the tell.
- Fair empties across the speed change: an empty goes only if it reaches the tap end before the ice starts or ends
  (boss_window: walking, special_t + the tell; in the tell and the thaw 0; on the ice, its frames left), so every trip
  is at one speed and arrives when the schedule booked it.
- The icy counter: tools/gen_boss.py `ice: "igloo"` makes icy copies of the igloo's two counter tiles (white streaks
  on the light counter top, glints on its front: readable on DMG by pattern) at BG 246-247 (free in the story; the
  ids the mirror engine borrows only in CLASSIC). It is a PLACEHOLDER pattern pending the owner's look
  (out/preview/boss_yeti_ice_x8.png). A lost life, the outro and the next level load put the counter back.
- Story and ARCADE: BUILT_SLOTS["BOSS"] gains IGLOO (chapter 5 ends with the fight, then POST_IGLOO). No existing
  golden changed.
- Tests (tests/test_boss_yeti.py, DMG + CGB, every frame <= 10 sprites a line): row, art, the icy tiles; the fight's
  start (VRAM 246-247, the counter as drawn); the breath's timing (tell after 360, 50 frames, the frost at 4 / 8 / 12
  / 16 columns 12 frames apart, all 18 at the ice, BLOW 30 frames, ice 180, he stands, thaw in 2 frames, walking
  again); the speeds on his bar only and only on the ice (full 2 -> 3, empty 0.5 -> 1, bars 0 and 3 unchanged); a
  held empty kept back 60 frames before the tell, sent at the ice's start and home before the thaw; a life lost on
  the ice thaws the counter; a win by real pours through the ice (arrivals >= empty_gap, the outro thaws, CHAPTER
  CLEAR, POST_IGLOO). New goldens boss_yeti, boss_yeti_inhale (the tell), boss_yeti_blow (the blow), dmg + cgb.

## Boss wave 1 ROM and WRAM (2026-10-12, game.gb, on top of Modes P6)
- ROM0 unchanged by the whole wave: 811 B free after P6 (tools/rom0free.py). Every boss byte is banked (autobank:
  the engine and the boss files land wherever bankpack finds room; banks 1-10 are full now, bank 11 has 15.8 KB
  free, so the next bosses go there). romusage free: 1 78, 2 21, 3 148, 4 31, 5 166, 6 282, 7 52, 8 1, 9 15,
  10 452, 11 15864 B.
- WRAM: +20 B (the engine's knobs 13, the Critic 3, the Yeti 4). The pose table (boss_map, boss_hand, 44 B) and a
  boss file's own buffer (BOSS_OWN, 20 B: the Yeti's icy counter row) lie over the end of story_scratch (the cut-scene
  backdrop buffer; no cut-scene, mini-game or title list runs during a fight; each fight fills them again). They were
  WRAM of their own at first: 62 B more pushed the game's variables into the stack's way (the stack starts right above
  them): the GBDK library's __map_tile_offset, the last variable, was overwritten in Quick Draw's practice entry
  (set_bkg_tiles then drew every tile 15 ids lower; test_qd / test_mg failed). Stack room above the variables is now
  654 B (P6 alone: 671; with the 62 B: 591, too little). Watch it: every new WRAM byte comes out of the stack.

## Mode-aware debug select as built (owner request, 2026-10-10)

The START + SELECT debug select (DEBUG_MENU builds only; `make release` still has none: build/release.noi names no
debug symbol) now selects in the mode it was opened in. src/debug.c (banked) does it all; main.c's combo watch is
unchanged; src/story.c gains one function at its end under `#ifdef DEBUG_MENU` (story_debug_start).
- Which mode: in story play (story_on) -> story; on the title the item under the cursor decides: STORY or CONTINUE ->
  story, any other item (ARCADE, BONUS, MUSIC) -> arcade; in arcade play -> arcade, as before ("LEVEL nn", 1..18,
  Left/Down and Right/Up, A = start_new_game).
- Story positions: a chapter's PRE scene, then the steps of the story's sequence the engine can play (story_step_get;
  a STEP_SKIP step only when story_unskip has its bit, so the mini-game slot appears once mini-games are built or the
  test hook names it, and the boss slot likewise), then its POST scene. Banner "STORY c LABEL" in HUD glyphs: PRE, OPEN,
  HAPPY, MINI, LAST, BOSS, POST (e.g. "STORY 3 HAPPY"). Left/Right change the chapter (1-9, wrapping; the position
  kept, or the next playable one), Up/Down the position (wrapping). Starting points: STORY -> chapter 1 PRE; CONTINUE ->
  the saved chapter at its first playable step when a step was reached, else its PRE scene (as CONTINUE itself); in
  story play -> the chapter and step being played.
- A starts it with the story's rules (story_debug_start): story_on, a fresh score, story_conds cleared, the venue's 3
  lives (from any step: as venue_start), the step itself through step_start (a shift: its goal banner, speeds,
  patterns, perfect pour; a mini-game slot: mg_enter), or the PRE / POST scene through scene_enter; afterwards the
  story runs on as usual (a lost venue restarts at its Opening, a POST scene leads to the next chapter's PRE).
- Decision: a story run started from the debug select writes NOTHING to SRAM. save.c's save_lock (set by debug.c on
  A, cleared by title_enter) makes story_save and tune_heard return at once: no chapters cleared or step reached, no
  soundtrack unlocks. The owner's real progress (CONTINUE) survives a playtest jump, and the jukebox never unlocks
  a song that was not earned. (An arcade start from the box is unaffected: the top 5 saves as always.)
- B closes the box as before. GS_DEBUG is opened from GS_TITLE / GS_PLAYING / GS_PAUSED only (a cut-scene's START
  skips it, so the combo cannot start there).
- Tests (tests/test_debug.py, the old arcade tests unchanged): positions and wrapping from STORY (the unbuilt slots
  passed over), an unskipped MINI offered, A on chapter 3 Happy hour / chapter 7 Last call / chapter 1 Opening lands
  on that shift's goal banner with the story's rules (venue, 3 lives, score 0, goal type) and winning it leaves SRAM
  byte for byte as it was (progress and unlocks untouched); A on PRE / POST plays that scene; CONTINUE starts at the
  saved chapter; in story play it opens at the current chapter and step and B resumes the shift; on BONUS it is the
  arcade box; a built boss step (after the boss engine: chapter 1's Big Tex) is offered as "STORY 1 BOSS" and A starts
  the fight through step_start / boss_set, its CHAPTER CLEAR and POST scene follow, SRAM untouched. The expected
  positions come from build/story.json "steps" (built per chapter). New golden: debug_story (dmg + cgb: the title with
  "STORY 3 HAPPY").
- Cost: ROM0 none (all banked); WRAM +3 B (debug_story / debug_chapter / debug_pos, debug builds only) + save_lock.

## Bonus menu and soundtrack as built (owner request, 2026-10-10)

- Title menu: ARCADE / STORY / [CONTINUE] / BONUS / MUSIC ON-OFF. BONUS always shows (owner's recommendation taken):
  every song but the title tune is locked at first. The HI line moved to row 0 (where the game's own score sits in
  play): a column of five items needs rows 5-13. Rows: 4 items 6/8/10/12, 5 items (with CONTINUE) 5/7/9/11/13
  (title.c MENU_ROW: centred on row 9, every other row). Room for one more: PRACTICE as a 6th item starts the column
  at row 4 (right under the logo) and ends it on row 14, above the counter between the scene's patron and the
  bartender (the same rows docs/minigames_bosses.md 2.3 planned); with CONTINUE absent it is a 5th item and fits rows
  5-13. The menu's text tiles: BONUS costs 5 tiles of the title's pool; 5 ids are left below the scene patron
  (TT_PATRON_BASE 224 of 233), enough for PRACTICE (its letters but P are already aligned tiles). K_* moved to game.h
  (debug.c reads the item under the cursor). Goldens replaced on purpose: title, title_anim, title_continue.
- BONUS goes straight to the soundtrack (decision: a one-item submenu is a press for nothing; when a second extra
  exists, BONUS becomes a list with SOUNDTRACK first). Superseded 2026-10-11 by the owner's submenus: BONUS opens a
  submenu, SOUNDTRACK its first item (see "Title submenus as built" below). src/jukebox.c, its own autobanked file; GS_JUKEBOX (main.c: one
  case line).
- The screen, scores-table style (light HUD glyphs + the story font's punctuation on the dark band, HUD palette): row 0
  SOUNDTRACK, row 1 a panel line; rows 2-11 the list, 10 lines visible, scrolling to keep the selection on screen
  (14 tunes today); the name at columns 1-18, the mug cursor (OAM 0, as the title's) left of it, the playing tune's mug
  icon at column 19, blinking (16 frames on, 16 off); rows 12 / 17 panel lines around the selected tune's details,
  rows 13-16: its full title (word-wrapped to two lines), the credit (composer, year), where the game plays it. A
  locked tune lists as "? ? ?" and its details read "? ? ?", LOCKED, PLAY STORY MODE. Rows are rebuilt into
  story_scratch (no cut-scene runs here) and queued 4 a frame.
- Names: tools/songs.py SOUNDTRACK, keyed by song (entertainer, galop, susanna, ...) and the three jingles, so the 10th
  venue tune inserted before the teahouse needs one entry there and in VENUES: gen_music.py writes
  build/jukebox_names.h in its ORDER (music.h's tune order), checks 18-character lines and the charset, and the header
  fails the compile unless its count equals TUNE_COUNT. The list is sized by TUNE_COUNT everywhere.
- Keys: Up/Down select (wrapping), A or START plays the selected tune from its start (a locked one: nothing), B stops
  the playing tune, or with nothing playing goes back to the title (title_enter: the title tune again). Entering the
  screen stops the title tune, so the first B leaves. cur_tune is the tune playing (a jingle clears it when it ends,
  and its icon goes).
- MUSIC OFF (decision): a tune chosen in the player plays anyway (the player sets sound_on and remembers it,
  jb_forced); leaving puts the music off again (music_set_on(0)), so the title stays silent and still reads MUSIC OFF.
- Unlock rule as built (save.c): the title tune always; any tune once it plays in story mode (music_play calls
  tune_heard when story_on: a venue tune at its PRE scene, or on CONTINUE straight into the venue; LEVEL CLEAR at the
  first shift won; GAME OVER at the first TRY AGAIN); clearing chapter 1 also unlocks all four jingles (BONUS and the
  SHOW galop never play in a story: no bonus rounds, and a show only after a tip); story_save also ORs in what the
  progress implies (progress_unlocks: the cleared chapters' venues, the next one's when a step was reached, the
  jingles from chapter 1). A new unlock is saved at once. Unlocks are permanent: a new story resets bytes 34-35 at its
  first save, never 36-37. Debug-select story runs unlock nothing (save_lock).
- SRAM version 5 "TPR5" (src/save.c; superseded by version 6 with the 10th venue): 0-3 magic, 4-33 the top 5 (as v2-v4), 34 chapters cleared (0-9), 35 the step
  reached in the next chapter (0-4; 0 when 9 are cleared), 36-37 the unlocked tunes (16-bit LE, bit t = TUNE_t; bit 0
  forced on at load; bits above TUNE_COUNT kept: room for the 10th venue tune), 38 checksum 0x5A + bytes 0-37, 39 its
  complement. Migration at boot, written back at once: version 4 keeps everything and gets progress_unlocks(progress,
  step reached) (save_migrated = 4); version 3 / 2 / 1 as before (save_migrated 3 / 2 / 1) with the unlocks their
  progress implies (none but the title for 2 and 1). Anything that does not check out (magic, checksum over 0-37,
  progress range, the table) is an empty save with only the title tune.
- Hooks: music.c music_play (bank 2) gained one line (`if (story_on) tune_heard(tune);`, before the MUSIC OFF check so
  a muted story unlocks too); title.c's title_enter clears save_lock.
- Cost: ROM0 -18 B (the GS_JUKEBOX case): 1548 -> 1530 B free (game.gb), 1661 -> 1643 B (release.gb). WRAM +17 B
  (_DATA 6255 -> 6272; release 6250 -> 6264): tune_unlocked 2, save_lock 1, the jukebox's 7 (jb_sel, jb_top,
  jb_forced, jb_shown, jb_t, jb_dirty), title_items / title_rows 4 -> 6 each (+4), debug.c's 3 (debug builds). SRAM +2 B
  (40 B used). jukebox.c + the names header ~2.1 KB banked (autobank).
- Tests (tests/test_jukebox.py, DMG + CGB): the names follow music.h / songs.py; BONUS on the menu with and without a
  save; Up/Down select, wrap and scroll (cursor on the line); a fresh cartridge lists only THE ENTERTAINER, the rest
  "? ? ?" and a locked tune does not play; every name once unlocked, the details of the last; A plays (cur_tune), the
  icon blinks, B stops, B returns to the title; a jingle stops by itself and its icon goes; MUSIC OFF plays here and is
  off again after; <= 10 sprites a line; a venue unlocks at its PRE scene and is saved at once; LEVEL CLEAR unlocks at
  the first win; clearing chapter 1 unlocks the jingles; unlocks survive a new story's first save and a reset; v4 ->
  v5 migration at five progress points; the progress rule; v5 loads its mask and rejects a bad checksum / mask outside
  it / bad progress. tests/test_scores.py has v5_image / progress_unlocks / saved_tunes; the older SRAM tests now
  expect version 5 written back. New golden: jukebox (dmg + cgb: OH! SUSANNA playing, some tunes locked).


## Title submenus as built (owner, 2026-10-11)

Owner: "use a sub menu scheme. Top level - play, bonus, settings". This answers where MUSIC goes (a setting, not
into BONUS) and what BONUS opens (a submenu, not the soundtrack directly).
- Top level PLAY / BONUS / SETTINGS (rows 7 / 9 / 11). A or START opens the item's submenu in the same place (the
  logo, the HI line, the bar scene and the bubbles go on untouched); B in a submenu goes back to the top level with
  the cursor on the item it came from; B on the top level does nothing. Up / Down wrap in every menu.
- PLAY: [CONTINUE] / STORY / ARCADE. Decision: CONTINUE first when a story save exists (the likeliest choice for a
  returning player, so A, A resumes), then STORY, ARCADE last; without a save STORY / ARCADE (rows 8 / 10), with it
  rows 7 / 9 / 11. BONUS: SOUNDTRACK (row 9); PRACTICE goes in as its second item when it is built, so the top
  level never changes. SETTINGS: MUSIC ON-OFF (row 9), the same toggle and session behaviour as before (not saved
  to SRAM, as before); SELECT still toggles the music on any menu level.
- The soundtrack player's B comes back to the BONUS submenu (title_back = TM_BONUS, used once by title_enter); every
  other way to the title (game over, the top-5 table, the story's credits, a mini-game's B) opens the top level.
- Debug select (src/debug.c unchanged in code): it reads the item under the cursor, so PLAY's STORY / CONTINUE open
  the story box; PLAY's ARCADE, the top level (PLAY included: no mode is chosen yet, and the arcade box is what
  every non-story item gave before) and the BONUS / SETTINGS submenus open the arcade box. B leaves the menu as it
  was.
- src/title.c (banked): title_menu (TM_*), title_back, title_dirty (rows to redraw) beside title_sel / title_items /
  title_n / title_rows; K_* gained K_PLAY / K_SETTINGS / K_SOUNDTRACK and TM_* is new (game.h). menu_open() builds a
  menu and marks the old and new rows; menu_frame() queues them within the VBlank drain's budget, at most two 20-byte
  copies a frame (a CGB text row is tiles + attributes; a blank row needs no attributes), none on a frame whose cursor
  move already queued two: a switch takes 2-5 frames. (Three rows a frame broke the drain budget tests: 14-20 DIV
  ticks against 12.) New text PLAY, SETTINGS, SOUNDTRACK (tools/gen_art.py MENU_STRINGS): TT_PATRON_BASE 224 -> 229 of
  233, 4 ids left.
- Cost: ROM0 none (1429 B free in game.gb, 1542 B in release.gb, before and after). WRAM +37 B (_DATA 6314 ->
  6351; release 6306 -> 6343): menu line buffers 3 x 20 + a blank row, title_menu / title_back / title_dirty, minus
  the old row_story / row_music / music_row and title_items / title_rows 6 -> 3.
- Tests: conftest.py has the menu helpers (title_pick, title_arcade, menu_to, menu_tap, K_* / TM_*); every test that
  started a game with START on the title now goes PLAY > ARCADE. tests/test_flow.py: the top level centred, Up / Down
  wrap, each submenu opens in place and B returns with the cursor on its item, CONTINUE only with a save (first,
  rows 7-11), START works as A, the MUSIC toggle in SETTINGS and SELECT on any level, the redraw within the drain
  budget; test_jukebox.py: BONUS > SOUNDTRACK opens the player and B comes back to BONUS; test_debug.py: the box
  follows PLAY's cursor (STORY / ARCADE / the top level). New goldens title_play, title_bonus, title_settings.
  Replaced on purpose (the menu's text only): title, title_anim, title_continue (now the PLAY submenu with a save),
  debug_story (the PLAY submenu behind the box).

## 10th venue as built (The Chrome Cow and the new order, owner decisions 2026-10-10 / 11)

The checklist was docs/venue10_impact.md (81 items); what differs from it is listed there under "As built".
- The order, story and arcade: 1 saloon, 2 stadium, 3 lumber lodge, 4 bistro, 5 igloo, 6 robot factory, 7 The Chrome
  Cow (theme biker, patron group punks, owner Granny Throttle, piece the drip tray, tune "Drunken Sailor"), 8 teahouse,
  9 jungle zoo, 10 space lounge. One index still means one venue everywhere (group = theme = level row - 1 = chapter
  = tune = pour art); every list follows it. The level rows stay with the position: row 7 is new (midway between 6
  and 8), the zoo plays the old row 8's numbers, the space lounge the last (hardest) row. Arcade loop 2 starts at
  level 11 (LOOP 2 banner), loop 3 at 21; DEBUG_LEVELS 20; the debug box prints STORY 10.
- Story: 10 chapters, 23 scenes, 146 pages (script 7082 B); docs/story.md folded the proposal in (PRE/POST_BIKER, the
  new pages of INTRO / POST_SALOON / PRE_TEAHOUSE / POST_TEAHOUSE / PRE_ZOO / POST_ZOO / PRE_SPACE / POST_SPACE /
  FINALE, the space lounge's scenes after the zoo's). Chapter 7: 10 / 22 / 24 punks, its Last call the new "chord"
  pattern; the zoo 12 / 25 / 28; the space lounge 15 / 30 / 32 with +25 % / -25 %. The goal banner's first line is
  the shift's name alone (OPENING SHIFT, HAPPY HOUR, LAST CALL, BOSS).
- The band (show engine): every venue has a show table (gen_art show_tiles, venue.show_tile, +25 B WRAM); a 6-frame
  show is a band of three different performers deduplicated into 16 8x16 quarters (32 OBJ tiles), performer k shows
  row 2k + (beat & 1); a 4-frame show stays one dance for all three.
- Twists (goal_t.twist bits, gen_story TWISTS): the mosh pit (src/mosh.c, docs/minigames_bosses.md section 9) in
  chapter 7's Happy hour (limit x 88) and Last call (x 72); TWIST_FAST_TUNE in the Last call: Drunken Sailor 9 -> 8
  frames a row (music_fast, hUGEDriver's exported ticks_per_row). Off in the Opening, boss fights and arcade.
- Save: SRAM version 6 "TPR6" (layout as v5, chapters 0..10). Versions 3-5 counted nine chapters in the old order:
  progress p <= 5 kept with its step, p >= 6 -> 6 with step 0 (a complete old story continues at The Chrome Cow);
  a v5's unlocks move to the new tune order (old venue tunes 6, 7, 8 -> 7, 9, 8). save_migrated = the old version.
- ROM: ROM0 free 1429 -> 1531 B (game.gb; release.gb 1644): +47 B the show table in draw_dancers, -315 B
  build/patron_load.c's per-group switch moved to a banked file (bkg_data_far maps the group's bank), +~120 B the
  mosh pit's hooks. ROM grows to 16 banks (bank 9 half free); bank 2 (music) 299 B free.
- Perf (PyBoy): the fastest row is level 10 now, reached from level 9's clear (no bonus round): realistic peak DMG
  199 / 99, CGB 215 / 130 missed of 1200 (the scenario keeps up to 10 patrons from that start); overlap stress DMG
  186 / 301, CGB 184 / 326 (guard 340: the mosh hooks' tests of mosh_on cost a little for every walker); worst pile
  unchanged (~287 / 250). A mosh on two bars at once keeps every frame on time; on four at once some frames run late.
- Tests: 1369 passing (test_twists.py new, 51); the new order in both modes, the band table, the save migrations,
  the banner. tests/conftest.py: the patron-list poke hook clears lists_ok as well (a poke can land mid-frame), and
  logic_paused() for set-ups that must start on one game frame.
- Not built (as the checklist allows): Duke (3.12) and Milk Run (4.10): their slots are skipped like every unbuilt
  boss and mini-game (the boss table has room: BOSS_COUNT 10). The counter splash tile is a placeholder.

## Three modes P1-P2 as built (owner decisions 2026-10-11; plan: the modes proposal, sections 1, 3, 4, 5)

- **P1**: `play_mode` (src/story.c; game.h MODE_ARCADE / MODE_STORY / MODE_CLASSIC / MODE_LEVEL). MODE_LEVEL is the old
  10-level rotation (loops, LOOP banner, a bonus round after even levels), kept only as the test harness and the debug
  select's "LEVEL nn" box. The title's test hook `title_go` (a level number) starts it on the next title frame;
  tests/conftest.py `title_level(rom, lv)` presses exactly the keys PLAY > ARCADE took, so every gameplay test and
  golden starts on the same frame as before (the suite was unchanged golden for golden at the P1 commit).
- **PLAY menu**: [CONTINUE] / STORY / ARCADE / CLASSIC (4 lines: rows 6-12; 3 without a save: 7-11). "CLASSIC" needed 4
  more title tiles: the title may now use BG ids up to 239 (the perfect pour's OBJ ids 234-239 are loaded at a story
  shift's start and never used on the title; tools/gen_art.py TITLE_TILE_END). CLASSIC starts the old rotation as a
  stand-in until CLASSIC is built (P5), with extra lives and its own top 5; the debug box on it is the LEVEL box.
- **ARCADE** (Q1 option A, Q2 the story's rules): the story's engine with `story_arc = 1`. PLAY > ARCADE: the saloon's
  Opening shift banner (no scene, no portrait, no text); each venue's playable steps in story order (shifts, a mini-game
  or a boss fight once built; STEP_SKIP passed over); after its last step VENUE CLEAR, a bonus round (rotating as
  before), the next venue. 3 lives for the whole run (venue_start leaves them), a gold medal +1 as in the story, extra
  lives at 20,000 and every 40,000 after (main.c add_score -> story.c extra_life; at most 4; ARCADE and CLASSIC only).
  A timed goal's clock costs a life and retries the shift (TRY AGAIN) while lives are left; the last life is the normal
  GAME OVER -> initials -> the ARCADE top 5. After the space lounge: the saloon again with "LOOP n" before its first
  banner (SP_LOOP, 120 frames or A), level = (loop - 1) * 10 + chapter + 1 so start_level's loop maths (and the HUD's
  L nn) apply; the difficulty stops growing after loop 4. Nothing is saved or unlocked (save_lock). Debug: PLAY's
  ARCADE (or ARCADE play) opens "ARCADE c STEP" (the steps only).
- **Story score** (owner 2026-10-11): it resets to 0 when the lives run out (TRY AGAIN, the venue again); a lost life
  or a timed retry keeps it. When the credits end it goes into the STORY top 5 (initials, the table); not from a
  debug-select run.
- **SRAM version 7** (src/save.c): main block at 0 ("TPR7", progress, step, tunes, checksum); 0x40 still reserved for
  Practice; one top 5 per mode at 0x80 ARCADE ("HSA1"), 0xC0 STORY ("HSS1"), 0x100 CLASSIC ("HSC1"), each with its own
  checksum, so a bad block empties only that table. Versions 3-6 migrate their story progress and unlocks; every old
  top 5 is dropped (Q4); versions 1-2 load as a fresh cartridge. The title's HI line shows the table of the mode under
  PLAY's cursor (CONTINUE / STORY: STORY's), ARCADE's elsewhere; the idle attract cycles ARCADE, STORY, CLASSIC; the
  table screen's header names the mode ("ARCADE HIGH SCORES", 19 characters at most).

## Three modes P3-P4 as built (the mirror engine; owner decisions 2026-10-11; plan: the modes proposal 2.3-2.5, C1-C4, C12)

Debug-only when built; P5 (below) is CLASSIC on the title.
- **Rule**: a bar marked R in `bar_dirs` (bit b = bar b, top 0) has its patrons coming from the right and its keg on the
  left. Every rule stays in bar-local x (patron_x, mug_x, bartender_x, TAP_X ... unchanged; tests read local values);
  an R bar is only **drawn** mirrored. With every bar L the picture is what it was (no golden changed).
- **BG** (render.c): an R bar's shadow rows hold the screen picture: local column c at screen column 19 - c, every tile
  flipped. restore_base copies the R bar's base rows (`base_rtile` / `base_rattr` in `base_all`, screen order, made at
  load), put_col / put_back_col write at 19 - c, queue_chunk / queue_urgent queue screen columns [20 - x1, 20 - x0); dirty
  spans stay local, so bg_pending, the budgets and the drain are unchanged. Quick redraws on an R bar: `quick_mirror`
  (banked) writes the 6 ids mirrored into the shadow and they are queued from there. The counter row: venue.c draws
  `ctr_rtile` / `ctr_rattr`. Stage and HUD are never mirrored.
- **Sprites**: everything is still drawn at bar-local X; `mirror_oam` (mirror.c, hand-written, called after the frame's
  drawing with OAM DMA off) moves each entry of an R bar to 168 - X and toggles its attributes (S_FLIPX; a lifted
  patron's toggle is 0 on a DMG level with every bar R, whose tiles are flipped already). An entry's bar comes from its Y
  ((Y - 52) / 24: everything lies from 1 line above to 16 lines below its bar's OAM Y); only the entries in use are
  looked at (0..oam_used-1, the lifted ones, the coin; the bartender's 0-3 only when draw_bartender rewrote them,
  render.c `bt_new`).
- **Input** (main.c): Left / Right swap on an R bar (Left walks to the tap); `facing` stays local.
- **Tiles** (mirror.c `mirror_load`, every level load after the venue and patron tiles; the title calls it with 0):
  - CGB: the X-flip attribute (BG bit 5, OAM S_FLIPX) does all of it, patrons, back views, keg and counter.
  - DMG, every bar R (C12, the whole screen flips): the group's 156 patron tiles are bit-reversed in place.
  - DMG, mixed (owner option (a)): patrons are drawn at even x only (`draw_mask` 0xFE on patron_draw: 2 px steps, all
    three looks both ways); the R set (the even shifts flipped) is put in the odd shifts' slots (R shift s at the slot of
    L shift s + 1), `st_tab` (WRAM, was the ROM0 stamp_tile) maps (direction, variant, shift) to the first tile; back
    views are shared and drawn unmirrored on an R bar (`mir_bswap`); a lifted patron on an R bar is the L shift-0 pose
    with the OAM flip. Option (b) (1 px steps, the looks split 2 / 1) would change only mirror.c's dmg_mixed and st_tab's
    R half (which pose goes to which slot) and the spawn's choice of variant per direction.
  - DMG, any R bar: each wall / counter tile of the bar rows that is not its own mirror image gets a flipped copy in a
    free id (77, 246-255, then 234-239; 252-255 and 234-239 are the story's boss HUD and perfect pour). Every venue fits
    (`mir_short` 0, tested per venue).
- **Harness and debug**: `level_dirs` (test hook; the title resets it) gives the LEVEL harness its directions for every
  level of the run; the debug select's LEVEL box steps CLASSIC's eight layouts with SELECT and shows them ("LEVEL 07
  RRLL"). Found on the way: SDCC 4.5 miscompiled the first version of that loop (kept the counter in L and loaded HL
  with an address inside the loop); debug.c has the workaround.
- **Tests**: tests/test_classic.py: the R picture pixel-identical to the all-L picture mirrored (every bar R and six mixed
  layouts, both models, walkers at odd shifts, drinkers, a back view, a lifted patron, a pushed one, mugs, coin,
  bartender), BG ids by column with CGB bit 5, the DMG tile schemes and each venue's flipped keg tiles, mugs / bartender
  / lifted entries at 168 - X and flipped, Left walks to the tap, the life-loss rules and the glass at the right ends,
  empties caught at the left keg, a served patron leaving past the right edge, the debug box. New goldens:
  classic_flip (sports, RRRR), classic_split (The Chrome Cow, RRLL), classic_alt (space lounge, RLRL), dmg + cgb.
  tests/test_overlap.py (two set-ups) and test_windup.py (arrivals in game frames) no longer depend on where the
  emulator's frame boundary falls inside the game's logic (the new code moved it by a few cycles).
- **ClassicPeak** (tests/test_perf.py test_classic_peak, perf_helpers.ClassicPeak: CLASSIC level 12's layout R L R L at
  the fastest row's speeds, three patrons a bar to begin with, new ones as fast as the patrons' end lets them, up to 16;
  a measurement and a loose guard, nothing tuned). PyBoy, 1200 frames, end LY / missed frames:

  | scenario | DMG | CGB |
  |---|---|---|
  | RealisticPeak before P3 (12e8d45) | 199 / 99 | 215 / 130 |
  | RealisticPeak now (every bar L) | 202 / 107 | 217 / 133 |
  | ClassicPeak, every bar L | 283 / 335 (patrons mean 11.0, max 14) | 289 / 402 (11.8, max 14) |
  | ClassicPeak, R L R L | 329 / 440 (11.5, max 14) | 315 / 575 (14.6, max 16) |

  Never more than 10 objects on a line, at most 36 entries, the music never skips a tick, no VRAM write outside VBlank.
  The patron count depends on the frame timing (late frames change who catches what), so the two rows are not the same
  load. Per frame (a -DPERF_SECTIONS build, median DIV ticks, ~1.8 a line; ~14.5-15.5 patrons): every bar L logic ~287
  (DMG) / ~301 (CGB), R L R L ~329 / ~318; of the difference mirror_oam is ~21 ticks (~12 lines) and the mirrored
  compose ~3. The DMG runs at ~30 fps in these moments, as the plan expected; the cheap next step for the mirror's own
  cost is mirror_oam (writing mirrored X in the mug and lifted-patron writers costs ~260 B of ROM0 instead). CGB double
  speed is not in this phase.
- **Known compromises**: DMG sprites overlapping sprites: the lower X wins (then the lower OAM index), and mirroring
  turns X round, so where two sprites overlap on an R bar the other one can be on top (the tests leave those pixels
  out); DMG mixed levels: 2 px steps and unmirrored back views on R bars; an R level costs ~6-15 % more logic a frame
  at the peak, so a heavy frame can run late there and not on an all-L level.
- **ROM**: ROM0 1498 -> 1151 B free (game.gb; release.gb 1264): render.c ~+260 B (the mirrored compose, quick-redraw
  hook), main.c ~+45 B (input, the mirror_oam call), patrons.c ~+17 B (draw_mask); mirror.c, the debug box and the
  venue / title / level hooks are banked (bank 9: 5170 -> 3386 B free). WRAM +290 B (st_tab, the R base and counter
  rows, mirror_oam's tables).
- **For P5**: start_level calls `mirror_load(play_mode == MODE_LEVEL ? level_dirs : 0)`: CLASSIC passes its row's dirs
  (after load_venue, load_patron_group, lift_level_init, enhance_load; before place_start_patrons). Caps (C5) go in
  try_spawn; everything else of CLASSIC is local-x rules and needs nothing from the mirror. A per-bar tap position (P6,
  slanted bars) only needs per-bar base rows (base_all is shared by the four bars today; +160 B WRAM per-bar), the
  mirror itself is per column and per OAM X.

## Three modes P5 as built (CLASSIC playable; owner decisions 2026-10-11; plan: the modes proposal 2.1, 2.2, C5-C9, C13, T3-T7)

PLAY > CLASSIC now plays CLASSIC's own table (src/classic.c, banked), no longer the old 10-level rotation (that stays only
as the LEVEL harness, MODE_LEVEL). Slanted bars and the end-of-level antics are P6.
- **Table** (`classic_table[26]`, 9 B a row): setting (saloon 0 / stadium 1 / The Chrome Cow 6 / space lounge 9, serve
  50 / 75 / 100 / 150), the guide's directions and per-bar caps, and our quota / spawn / step / push-back / empty gap
  (the plan's 2.2 numbers, to tune in playtest). `start_level` (level.c) asks `classic_row()` first: in CLASSIC it fills a
  level_cfg_t (now in game.h) from the row, and the rest of the load is the harness's code (speeds, hurried walkers from
  level 3, the loop maths); `mirror_load` gets the row's directions. Level 27 = row 14 again, every 13 levels; each repeat
  uses the loop rule as a loop (walk +10 %, spawn -8 %, gap -5, 3 repeats at most). Every bar starts with one patron.
  No LOOP banner in CLASSIC (enter_level_screen shows it for MODE_LEVEL only); the HUD's L nn counts on to 99.
- **Caps** (C5, patrons.c try_spawn, ROM0): the random bar, or the next one round with room (`bar_n[b] < bar_cap[b]`;
  bar_cap 255 in the other modes, so their random sequence is untouched); every bar full: retried in SPAWN_RETRY frames.
  A served patron sliding out still counts until he is off the screen.
- **Bonus rounds** (C8): main.c asks `classic_bonus_due()` (levels 2, 5, 9, 13, 15, 18, 22, 26, then those of 14..26
  every 13 levels: 28, 31, 35, 39, 41 ...). Always the can shake-up (bonus_kind 0); round n swaps 6 + n times at 32 - 2n
  frames a swap (30, 28, ... 14 at round 9, then it stays there); WINNER 3000 every time.
- **Tips** (C9): `tip_first` = 2 at a CLASSIC level's load; send_empty counts the level's empties down and the 2nd one
  calls `classic_tip(p)`: the coin centred under the sender (tip_x = his x + 4) on his bar. maybe_tip leaves no tip
  before that one; later tips as before (tip_chance at a serve).
- **In-level ramp** (the guide; owner: now, not P6): `ramp_t` counts 600 frames of play (update_patrons, not during the
  intro); each step spawn -6 % and walk +5 % (hurried walkers too) of the level's own values, 3 steps at most; the
  pending spawn timer is cut to the new interval. A lost life (resume_after_life) puts the level's values back and starts
  the count again.
- **Lives / scores** (C7, T7): extra lives at 20,000 then every 40,000, at most 4 (start_new_game sets extra_at for
  MODE_CLASSIC, as the stand-in did). GAME OVER -> initials -> "CLASSIC HIGH SCORES". The CLASSIC block's magic is now
  "HSC2" (save.c tbl_ver): the stand-in's "HSC1" block loads as an empty table; ARCADE / STORY keep "HSA1" / "HSS1".
- **Debug**: PLAY's cursor on CLASSIC (or CLASSIC play) opens "CLASSIC nn" (1..26, wrapping; in play a repeat shows its
  row's number); A starts a CLASSIC game there (3 lives, score 0). A CLASSIC game over from it goes into the CLASSIC table
  as an ARCADE debug run does into ARCADE's. The LEVEL box (SELECT steps the layouts) is unchanged. Test hook: title_go
  = 0x80 | level starts CLASSIC at that level.
- **Tests** (1560 -> 1629 passing, 25 skipped, 2 xfailed, both models): tests/test_classic_mode.py (71): the table read
  out of build/game.gb equals the guide (settings, directions, caps, bonus levels, venues, serve scores); PLAY > CLASSIC
  starts level 1; 13 levels load their rows; level 27 / 40 / 53 / 66 = row 14, faster each repeat up to 3; caps never
  exceeded under a flood (levels 1, 4, 6) and reached; serves score 50 / 75 / 100 / 150 (wave 2 too); the extra life at
  20,000 and the cap of 4; bonus after exactly the listed levels (1-42), always the shake-up, quicker and longer each
  round (9 rounds); the first tip at the 2nd empty under its sender, no tip before it; the ramp's three steps and its
  reset at a lost life; level 12 crowded for 3000 frames (ClassicPeak's second bartender on the real level): <= 10
  objects a line, <= 40 in all, <= 4 a bar; game over -> initials -> the CLASSIC table, saved as "HSC2"; an "HSC1" block
  loads empty; the CLASSIC box. Changed on purpose: test_flow (PLAY > CLASSIC starts CLASSIC's level 1: a patron on
  every bar), test_debug (PLAY's CLASSIC opens the CLASSIC box), test_scores (TBL_MAGIC "HSC2"). New goldens (dmg + cgb):
  classic_start, classic_level3 (the whole screen flipped, in play), classic_bonus, scores_classic. No existing golden
  changed.
- **Perf**: not tuned. ClassicPeak (test_perf) runs on the harness's level 10 row with RLRL and caps off, so its numbers
  in "Three modes P3-P4 as built" stand; the real table's level 12 (spawn 170, step 53) is slower than that row (210 /
  52 with the scenario's own forced spawns), and levels 23-26 (130 / 44) are the fastest rows, not measured yet.
- **ROM**: ROM0 real free 1134 -> 1006 B (game.gb), 1247 -> 1119 B (release.gb): try_spawn's caps, send_empty's hook,
  update_patrons' ramp tick, maybe_tip's test, main.c's bonus choice. Banked: classic.c (~1.0 KB, bank 9: 7973 -> 6929 B
  free), level.c +102 B (bank 5: 254 -> 152 free), the rest in their own banks. WRAM +~15 B.
- **Deviations from the guide**: patrons come to a quota per level (our engine), not "until the level is cleared";
  speeds, quotas and spawn rates are ours; the bonus round's speed-up stops at round 9 (14 frames a swap); a leaving
  patron counts against his bar's cap until he is off the screen; no "WAVE 2" banner; space bar 150 (the guide's
  figure).

## Three modes P6 as built: slanted bars (owner decisions 2026-10-12; plan: the modes proposal C11)

- **Rule** (the guide: "the bars become trapezoidal in later levels, each lower bar slightly longer"): a `taper` column in
  `classic_table` (now 10 B a row): 1 on levels 10-13 and all of wave 2 (and so every repeat), 0 elsewhere (0 turns a
  level's bars straight; TAPER_MAX 1). Bar b's tap end moves (3 - b) * taper columns in: the top bar's keg 3 columns in,
  then 2, 1, the bottom bar's at the edge. The patrons still come in at the screen edge; the wall beyond the keg (wall
  rows and the counter row) is plain wall. On an R bar it is mirrored with the rest.
- **Engine**: `bar_tap[b]` (mirror.c, WRAM) is bartender_x at bar b's fill position (TAP_X - 8 k); `mirror_load` takes the
  taper in bits 4-5 of its dirs (classic_row passes `dirs | taper << 4`; the LEVEL harness's `level_dirs` takes it too, a
  test hook; the title's mirror_load(0) puts every bar straight). Every tap rule reads the bar's own tap: the walker who
  reaches it costs a life (walker_pixel), the empty's schedule (empty_travel), the show's shuffle limit (show.c), the
  bartender's snap / walk limit / TAP_GRACE / at_tap (main.c), "at the tap he catches any empty" and the spout's fill
  glass and launch (mugs.c, through `tap_now` = bar_tap[bar], set at the start of every play frame), an empty off the
  tap end (BAR_MUG_END) and its breaking glass (BAR_GLASS_X); reset_actors starts him at bar_tap[0]. The boss fight and
  the story's scene keep TAP_X (straight bars outside CLASSIC). Cheap pre-tests (x > MUG_RIGHT_END - 24, x >= FAR_X - 24)
  spare the hot loops the lookup in the common case.
- **BG**: the base rows (`base_all`) and the counter row (`ctr_all`, WRAM, new) are BASE_W = 23 wide: the venue's 20
  columns + 3 of plain wall (the wall rows' columns 2-4). An L bar shifted k columns shows the window from column k (the
  wall from column k, the spout and keg at 17 - k .. 19 - k, plain wall after); an R bar the mirrored row from 3 - k.
  `bar_bofs[b]` is the window; restore_base (render.c) and draw_venue use it, copy_2rows' source stride is 23. No new
  tile ids (the DMG's flipped copies are the same tiles: `mir_short` 0).
- **Tests** (tests/test_taper.py, 69 on both models): the table's taper column (10-26); each level's taps (1, 9, 10, 12,
  13, 14, 23, 26, 27); taper 0 = every tap TAP_X, every window 0; the title puts the bars straight; the wall rows, keg and
  counter at each bar's columns (L, RLRL, RRRR: CGB ids and attributes, DMG flipped tile data); the slanted R picture is
  the slanted L picture mirrored (RRRR and RLRL scenes, 30 frames, both models); at each bar's tap on L, RRRR and RLRL
  levels: the snap, the walk limit, the fill glass and the launch under the bar's spout; a walker costs a life at his
  bar's tap; the bartender at the tap catches an empty past him; an empty off the top bar's near end breaks at
  tap + 33 with its glass at the bar's end (mirrored on R); a full mug off the far end unchanged; fair empties count the
  bar's own distance. Changed: test_classic (base_all's new layout; two catches read one frame later: PyBoy's frame can
  end between the mug's state and its life / score), test_classic_mode (ROW_SIZE 10). New goldens (dmg + cgb):
  classic_taper (CLASSIC level 13, L R L R), classic_taper_r (level 23, R R R R). No existing golden changed.
- **Perf guards** (not tuned): the per-bar lookups moved the chaotic scenarios a little; three guards were at their
  measured value before and are re-based with the numbers in tests/test_perf.py: worst-case pile end 290 -> 300 and
  missed 260 -> 270 (now DMG 292 / 257, CGB 291 / 255), the level-10 overlap missed 340 -> 360 (DMG 184 / 338, CGB
  189 / 348), the realistic peak 230 / 140 -> 240 / 150 (DMG 204 / 141, CGB 231 / 115).
- **ROM**: ROM0 real free 1006 -> 835 B (game.gb), 1119 -> 948 B (release.gb): the per-bar lookups in mugs.c, patrons.c,
  main.c and render.c (~170 B; on hot paths, so not banked). Banked: mirror.c / venue.c / classic.c +~150 B. WRAM +~85 B
  (base_all 160 -> 184, ctr_all 92 for the old 40, bar_tap, bar_bofs, tap_now).

## Three modes P6 as built: the end-of-level antics (owner decisions 2026-10-12; plan: the modes proposal C10)

- **What**: after LEVEL CLEAR in CLASSIC only, the bartender, where he stands, tosses a glass; one of six endings at
  random: 0 backheel and smash; 1 backheel and hurt foot (four hops); 2 the glass hits a dove, which falls on his head;
  3 the glass lands upside down on his head; 4 it crashes on his head (dazed, the stars twinkle, he sways); 5 he drinks
  two beers instead. Storyboards and timings as approved (the shared toss 52 frames: toss pose 12, rise ~32 px easing
  out with the glass tumbling 30, apex 10; each ending within 210 frames). Art: assets/art/antics/antics.txt (kick, hop,
  dazed, drinking) and antics_fx.txt (the dove, the stars), moved out of assets/art/approved/ ("; Art: approved design
  (owner 2026-10-11)"); tools/gen_antics.py -> build/antics_art.h (32 OBJ tiles; DAZED's and DRINK's bottom halves are
  checked to be bartender_idle's / bartender_fail's, whose entries are reused). The glass, the shards, the full mug and
  its drinking frames are the venue's own.
- **Flow** (src/antics.c, banked; ROM0: main.c's GS_LEVEL_CLEAR asks `antics_frame()` in CLASSIC instead of counting
  CLEAR_FRAMES; main_cold.c's enter_level_clear calls `antics_start()`): 60 frames of the LEVEL CLEAR banner and jingle
  (the banner covers bar 1's rows and hides sprites there), then the banner goes and the ending plays (210), then 30
  frames on its last picture: 300 frames in CLASSIC (other modes keep 150). Then the bonus round or the next level as
  before. The 32 tiles go over the show's (OBJ_DANCER) during the banner, 8 a frame through GBDK's set_sprite_data
  (it waits for STAT mode 0/1 per byte: safe with the LCD on); the next level load (or the bonus round) puts the
  show's back. OAM: 0-3 him, 5 the glass / shards, 6 the dove, 7-8 the stars or the two beers; at most 6 on a line.
  Drawn at bar-local x and mirrored on an R bar (168 - X, S_FLIPX), so slanted and mirrored bars need nothing more.
- **Random**: `antics_rng`, the antics' own xorshift byte, stepped once a clear: the game's next_rand sequence is not
  touched, so the bonus round after a clear plays exactly as it did (classic_bonus golden unchanged). Test hook
  `antics_force` 1..6 plays ending n - 1; `antics_end` is the ending.
- **Tests** (tests/test_antics.py, 42 on both models): each ending (forced) plays, moves him, takes the banner away,
  ends with the clear (300 frames + the next level's load), never more than 10 sprites a line, the antics' tiles in VRAM
  during the clear and the show's tiles back on the next level; after a bonus round the next level's tiles equal a fresh
  load's; the ending varies over clears and next_rand is untouched; on an R bar (level 3, bottom bar) every entry is
  mirrored and flipped; level 13 (slanted, L R L R) on every bar within 10 a line. New goldens (dmg + cgb): antics_bird,
  antics_beer, antics_dazed. No existing golden changed.
- **ROM**: ROM0 real free 835 -> 811 B (game.gb), 948 -> 924 B (release.gb): the two hooks. antics.c + its tiles
  ~2.3 KB banked (autobank put it in bank 1). WRAM +8 B.

### P6 perf: ClassicPeak on CLASSIC's own busiest rows (measured, not tuned)

tests/test_perf.py test_classic_peak_real_rows: perf_helpers.ClassicPeak started on CLASSIC's own level (its row's
speeds, directions, caps 4 and the slanted bars; the scenario is now taper-aware: walkers are put back 24 px short of
their bar's own tap, the second bartender's mugs start at the bar's spout) for 1200 frames, PyBoy, end LY / missed
frames, patrons mean:

| level (layout) | DMG | CGB |
|---|---|---|
| 12 (R L R L, slanted) | 322 / 368 (10.95) | 364 / 471 (12.96) |
| 23, 24 (R R R R, slanted; step 45) | 294 / 568 (13.6) | 293 / 576 (13.52) |
| 25, 26 (R R R R, slanted; step 44) | 296 / 579 (13.65) | 309 / 584 (13.64) |
| harness ClassicPeak R L R L (P4's scenario) | 266 / 573 (15.06) | 320 / 579 (15.17) |
| harness ClassicPeak every bar L | 267 / 479 (12.65) | 250 / 514 (13.97) |

(23 = 24 and 25 = 26: the rows differ only in the spawn interval, which the scenario overrides.) The busiest rows run
late on 30-50 % of their frames on both models, as P4 measured for the harness row; the budgets hold (<= 10 objects a
line, <= 40 entries, the music never skips a tick, no VRAM write outside VBlank). Guards only: end <= 450, missed <= 900.
The scenario's second bartender now serves only the bars the player is not on, and the line checks leave out the two
frames after it pokes a mug in: PyBoy can land that poke inside the next frame's logic after lift.c's line estimate,
which then draws it uncounted (an 11th object on level 12's lines in two runs; a real launch is counted first).

## Quick Draw and BONUS > MINI GAMES as built (M11e step 3, docs/minigames_bosses.md 4.1 / 2.3, 2026-10-11)

The saloon's mini-game on the framework, playing in STORY and ARCADE, and the planned Practice feature as the title's
BONUS > MINI GAMES. The art is the owner-approved proposal (2026-10-11): the Sarsaparilla Kid look B with round 3's
stray-pixel fix, the Spigoteer's duel poses, the bottle (round 2's: cork up, tilted fumble), tumbleweed, crow, the
DRAW! sign and the pips, in assets/art/quickdraw/ ("; Art: approved design (owner 2026-10-11)").
- **Ids** (src/mg.h): a mini-game id is a game, not a venue: MG_QUICKDRAW 0, MG_TSHIRT 1 ... MG_ASTEROID 9 (one per
  planned game, MG_PLANNED 10, the Practice block's bit / medal index), MG_STUB 16. mg.c has each game's venue
  (mg_venue[]) and the reverse (venue_mg[], mg_of_venue(), which story.c's step_start now calls). The old MG_STUB 9 was
  also venue 9 (the space lounge since the 10th venue) and ids >= 9 loaded the saloon: fixed (a test enters id 9 and
  gets the space lounge, MG_STUB the saloon). A planned id not built yet still plays the stub, in its own venue.
- **Story / arcade**: gen_story BUILT_SLOTS gains MINI: SALOON, so chapter 1's mini slot (after the Happy hour) plays
  Quick Draw in MG_STORY mode (the score carries on, A CONTINUE, a gold medal +1 life), in STORY and in ARCADE.
- **Rules** (src/qd.c, the spec's numbers): per round "ROUND n" / WAIT FOR THE SIGN 60 frames (a press then is ignored: the pause
  between rounds), the same banner through a wait W = 90 + 0..210 frames, then DRAW! (the sign flips to its face with the badge,
  SFX_CATCH as the bell). Badge A in rounds 1-2, A or B in 3-5. R = 34 30 30 28 26. The badge's button on frame t <= R
  after DRAW! wins (a tie at R is the player's; R + 1 is TOO SLOW: the Kid drew); only a fresh press counts (a button
  held from the first 60 frames through DRAW! is no press); A or B during the wait, or the other button after DRAW!: FOUL. Feints
  from round 3, one a round, 48 frames, ending >= 30 frames before DRAW!: a tumbleweed rolling along the floor
  (SFX_SHAKE) or a crow dropping onto the sign, cawing (SFX_LAUNCH) and leaving. After a round 60 frames: the poses
  (the soda duel below; first built as the winner's cork popping and the loser fumbling), the pips, "YOU 0.32" (hundredths, the story font's '.' tile
  patched into mg_say's queued row) / FOUL / TOO SLOW (SFX_SERVE / SFX_BREAK / SFX_LIFE). First to three: YOU WIN /
  THE KID WINS and "3 TO n" through MG_END (the Kid cheers and the Spigoteer slumps when the Kid wins), then the result.
  Points: 500 a round + (R - t) x 20, the match +2000. Medal (qd_medal, not mg_score thresholds; mg.c asks the game):
  GOLD 3-0, SILVER 3-1 / 3-2, BRONZE lost with a round, else none. No timer. No HARD setting (the spec gives Quick
  Draw one setting for story and practice; MG_HARD stays for games that define one).
- **Screen**: the framework's saloon backdrop; the sign at columns 3-16, rows 6-9 (CGB BG palette 2: cream, tan, red,
  dark; DMG black on white); the pips on row 12 (the Kid's columns 2-4, the player's 15-17, BG palette 0); the Kid at
  x 20 (OBJ palettes 3 / 4, DMG OBP1 0xE4, set at entry since the title leaves 0xC4) and the Spigoteer at x 124 (his
  duel poses as bartender frames 7-9 through mg_spigoteer), y 112; the bottle beside the hand (OBJ palette 1). OAM 0-3
  him, 4-7 the Kid, 8-9 the bottles, 10-11 tumbleweed, 12 crow; worst line 8. Tiles: BG 125-163 (39), OBJ 56-91 (his
  poses, bottle, tumbleweed), 96-127 (the Kid), 164-167 (the crow): all reloaded by the next level load. Not OBJ 92-95:
  the coin is loaded once at boot (mg.h's resource note said 56-127; corrected). State: struct qd_state in the mg union
  (tests read story_scratch + 0..15: st, round, wins x2, wait (16-bit), badge, r, t, res, react, feint, feint_at
  (16-bit), feint_t, fx).
- **BONUS > MINI GAMES** (src/mg_list.c, GS_MGLIST): BONUS is SOUNDTRACK / MINI GAMES (rows 8 / 10; "MINI GAMES" needs
  no new title tiles). The list in the soundtrack player's style: row 0 MINI GAMES, the games from row 2 (the name at
  column 1, the best medal's word at 13), the details on rows 13-16 (the name, the venue, BEST GOLD / NO MEDAL YET,
  A PLAY  B BACK). Up / Down wrap; A or START plays the game in MG_PRACTICE (score from 0, "A RETRY B MENU": A retries,
  B now comes back to the list); B goes back to the BONUS submenu with the cursor on MINI GAMES (title_back_sel). A
  game not reached lists as "? ? ?" (as the soundtrack's locked tunes) with ? ? ? / LOCKED / REACH IT IN STORY / OR
  ARCADE, and A does nothing. The DEBUG_MENU build (`make`) lists QUICK DRAW and the stub GREEN LIGHT, both unlocked;
  `make release` lists Quick Draw alone with the real rule.
- **SRAM** (src/save.c, still version 7; the block at 0x40 that was reserved): "MGP1", 4-5 the mini-games reached (LE,
  bit g = MG_*), 6-15 the best medal per planned game, 16 checksum (0x5A + bytes 0-15), 17 its complement. A game is
  reached when STORY or ARCADE starts it (mg_enter in MG_STORY mode: ARCADE's save_lock 1 does not stop it, the owner's
  rule); its best medal is any mode's. A debug-select run records nothing: debug.c's save_lock is now SAVE_LOCK_DEBUG
  (2), and only the Practice block tells 1 from 2. The stub is never saved. Written only when a bit or a medal changes
  (mg_record); a bad block (magic, checksum, a medal above GOLD, a bit at or above MG_PLANNED) loads as nothing reached
  and leaves the other blocks alone.
- **ROM / WRAM**: ROM0 real free 1498 -> 1481 B (game.gb), 1611 -> 1594 B (release.gb): the GS_MGLIST case. Banked
  ~6.4 KB (qd.c + its art, mg_list.c, the save code, the id tables); autobank opened bank 10 (11 banks, still a 256 KB
  ROM). WRAM +16 B (mg_unlocked, mg_best[10], title_back_sel, the list's 3); Quick Draw's state is in the union.
- **Tests** (1403 -> 1468 passing): tests/test_qd.py (44: the screen and its art in VRAM, palettes and attributes; a
  round, its points and the '.'; R wins and R + 1 loses; TOO SLOW; early A or B is a foul, READY ignores presses; the
  wrong badge; a held button; best of five to three with the six medal cases, the score lines and the outro poses;
  seeded rounds (waits, R, badges, feints only from round 3, both kinds); feints frame by frame never with fewer than
  30 frames left, their sounds; after Quick Draw a level's VRAM is byte for byte a fresh boot's); tests/test_mg_list.py
  (19: BONUS's items, the debug list, A plays / RETRY / B back / B to BONUS, the release list locked and unlocked, the
  stub not in the release list, story reaching it unlocks and saves it with its medal, a worse medal never lowers the
  best, ARCADE unlocks too while a debug-select run does not, practice and the stub unlock nothing, five bad blocks).
  Changed: test_mg (ids; B goes to the list; the story slot is Quick Draw; the stadium's unskipped slot plays the stub
  in the stadium), test_story / test_arcade (finish_mini / past_mini through the saloon's mini-game), test_flow /
  test_jukebox (BONUS's two items), test_debug (save_lock 2). New goldens (dmg + cgb): qd_intro, qd_draw, qd_you_win,
  qd_foul, qd_feint, qd_kid_cheer, qd_result, mg_list, mg_list_locked. Replaced on purpose: title_bonus (BONUS gains
  MINI GAMES), mg_story_gold (the saloon's story slot is Quick Draw now, not the stub), mg_result (the stub's practice
  run: the frames its rounds 3-5 see the test's A on moved with the code layout; only the score digits differ).
- **The soda duel** (owner-approved 2026-10-11, replacing the cork pop and the fumble; art in assets/art/quickdraw/
  shake_bodies, shake_bottle, aim_bottle, stream, wet; pop.txt and its 4 tiles removed): through the banner both
  shake a bottle in the fist (the STAND bodies without the holstered bottle; the Kid every 4 frames, the Spigoteer
  every 5); at DRAW! both freeze. The round's winner (the Kid on TOO SLOW) takes his DRAW pose with a level, uncorked
  bottle and sprays a stream drawn as BG tiles on the wall's row 15 between them (3 columns a frame, flowing, cut off
  from his end from frame 36, the wall back from its copy by frame 40); the loser holds his bottle as ever, foam
  SPLASH over his head from frame 4, then DRIP A / B. A FOUL fizzes over the player's own bottle (FIZZ, a foam column,
  SPLASH, drips); the Kid stands. YOU WIN: the Spigoteer aiming, no stream, the Kid dripping; THE KID WINS: the Kid's
  cheer, the Spigoteer dripping. mg_spigoteer takes a starting OAM slot, so qd gives the slots in draw order (wet 0-1,
  foam 2, bottles 3-4, aimed bottle 5-6, the Spigoteer 7-10, the Kid 11-14, tumbleweed 15-16, crow 17): no re-sort.
  Worst line 9. OBJ tiles: 56-87 (his poses, tumbleweed), 96-127 (the Kid), 164-206 (crow, the duel's 34 OBJ tiles and
  the stream's 5 BG tiles, the same VRAM); 92-95 (the coin) untouched. State: anim and the 40 stream-row bytes (the
  wall's copy, the row shown) in struct qd_state. Tests (test_qd.py, 54): the shake and its freeze, the stream crossing
  and clearing with the wall tile for tile the same before and after (the player's and the Kid's spray), the wet
  loser, the foul's fizz, the end poses, a whole match frame by frame at <= 9 sprites a line. Goldens replaced:
  qd_intro, qd_draw, qd_you_win, qd_foul, qd_feint, qd_kid_cheer, qd_result, mg_story_gold; new: qd_spray,
  qd_kid_spray, qd_foul_fizz, qd_match_won.
- Spec gaps: the badge art is a letter in a dark disc, not "black on white" as 4.1's text says (the approved art
  decides); the pips are on row 12 (the approved mock-up), not the HUD row the spec's sketch shows; with no new SFX
  allowed the bell, pop, caw and rustle reuse SFX_CATCH / SFX_SERVE / SFX_LAUNCH / SFX_SHAKE; Practice's 2.3 chapter
  / segment screen (shifts and bosses) is not built: MINI GAMES lists the mini-games only.

## Battery Sort as built (M11e, docs/minigames_bosses.md 4.6, 2026-10-12)

The robot factory's mini-game on the framework (src/bs.c), in STORY and ARCADE (gen_story BUILT_SLOTS MINI gains
ROBOT) and in BONUS > MINI GAMES. The art is the owner-approved proposal (2026-10-12): the gauge cells (option A: the
factory drink's own full / empty frames, OBJ 56-59, no tiles of their own), the light steel bins, belt, diverter,
signs, chute lid, strike lamps, broken battery, spark, WRONG cross, in assets/art/battery/ ("; Art: approved design
(owner 2026-10-12)"); tools/gen_bs.py -> build/bs_art.h, build/bs.json, out/preview/bs_*_x8.png (it checks cells.txt
against the drink and the cross's mirror symmetry; the bin's and lid's tiles deduplicated: 44 BG tiles).
- **Rules** (the spec's numbers): the front battery waits on the diverter's flap D frames (120, -8 every 4 right sorts,
  never under 40); Left CHARGE (charged), Right RECYCLE (dead), Down SCRAP (broken; nothing while the chute is closed).
  The belt 0.75 px a frame + 0.125 every 6 right sorts, at most 2.0 (1/8 px units); batteries enter 24 px apart from
  x -8, queue 16 px apart from x 76. A right sort counts when it is made (the next D, the speed); its points come when
  it lands (24 frames: 4 into the diverter behind its tiles, 16 arcing out of the port or falling through the mouth,
  4 sinking behind the bin's rim): 100 + 10 x the streak (bonus at most 200), sparks over the bin, the catch pose. A
  wrong bin: a strike on landing (the cross blinks over the bin 40 frames, the battery spat onto the floor as the
  drink's lying frame); D running out: a strike, the cross over the diverter, the battery drops in. 3 strikes (THREE
  STRIKES) or 45 s (TIME UP) end it; up to 3 batteries in the air. Types: 50/50 from mg_rand; the 16th always broken,
  from the 17th 20%. When the first broken one reaches the flap the lid slides away and SCRAP CHUTE OPEN / BROKEN ONES
  DOWN shows 60 frames with the belt, the wait and the timer stopped. Medals on mg_score: 2000 / 4000 / 6000. One
  setting (no HARD). SFX: sort LAUNCH, right CATCH, strike BREAK, chute SHAKE, third strike LIFE.
- **Screen**: the framework's factory backdrop, its counter row 11 made wall (row 9's tiles); the banner rows 2-3 are
  wall while no banner shows (a row a frame through the queue, tiles and CGB attributes; the HUD band only for the
  chute's banner, THREE STRIKES and TIME UP; the wall back at MG_END frame 40). Belt row 8 columns 0-8 (one tile id,
  4 frames); diverter columns 9-10 rows 8-10; bins rows 12-16 at columns 1 / 8 / 15; strike lamps HUD 9-11 (8 blank);
  the Spigoteer at x 100, y 112 in bartender frames (IDLE, FILL, FILL flipped, SLIDE, CATCH, FAIL; the outro FAIL or
  CATCH: the antics are not loaded). CGB BG 2 diverter + chute, 3 CHARGE, **5 RECYCLE** (not the proposal's 4: the
  result window rewrites palette 4 with the medal while the bins' lower rows still show); OBJ 3 broken, 4 spark,
  5 cross; DMG OBP1 0xE4. OAM 0-3 him, 4-5 cross, 6-7 sparks, 8 spat, 9-11 in the air, 12 the belt spark (front-most
  broken only), 13-20 the queue (x <= -8 parked at y 0). Worst line 8 (the whole-game test). Tiles: BG 125-168, OBJ
  60-67 (over the crash frames; the level load puts them back).
- **List**: BATTERY SORT / THE ROBOT FACTORY, between QUICK DRAW and the stub; the medal column moved to 14 (the name is
  12 letters). Release lists Quick Draw and Battery Sort with the unlock rule.
- **ROM / WRAM**: bs.c + art ~4 KB, autobank (banks 1-10 nearly full, 11 has room); no new WRAM (state in the mg union, struct bs_state,
  tests read story_scratch + offsets); after the boss wave the stack has 654 B (s__HEAP 0xDD72 to 0xE000).
- **Tests** tests/test_bs.py (40): screen and art, the belt and the banner rows, each type to its bin with its path,
  a wrong bin, a timeout, the window and speed table, the chute at 16 and the pause, the seeded types (a Python model
  of mg_rand), three strikes, time up, points and medals, a whole game at <= 8 sprites a line, the level after with
  VRAM and palettes as a fresh boot's, the story's factory slot with the Last call as one reached without it, ARCADE,
  the list (debug and release). Changed: test_mg_list (the list's lines, column 14), test_story (the chapter loop's
  mini slot is the chapter's venue's game). Goldens new: bs_intro, bs_play, bs_correct, bs_wrong, bs_scrap_open,
  bs_result; replaced: mg_list, mg_list_locked (the list gains BATTERY SORT).
- Spec gaps: the counter row and the band are wall in play (the mock-ups); the instruction reads LEFT FULL RIGHT DEAD
  (20 letters, the mock-up); the 16th battery is always broken (the chute's banner always has its reason).

## Order Up! as built (M11e, docs/minigames_bosses.md 4.4, 2026-10-12)

The bistro's mini-game on the framework, in STORY and ARCADE (gen_story BUILT_SLOTS MINI gains BISTRO: chapter 4's slot
after the Happy hour) and in BONUS > MINI GAMES (second line, THE BISTRO; the unlock rule as Quick Draw's: reached in
STORY / ARCADE, SRAM bit 3; the debug build lists all). Art: the owner-approved proposal (2026-10-12) in
assets/art/orderup/ ("; Art: approved design (owner 2026-10-12)"): dish look B "big food", Chef Colby (a 16x24 sprite,
4 poses), the cloche, the bubble, the pips, the strikes and '!', the steam, the X; the bistro show's waiter dances on
ORDER UP! (approved option).
- **Rules** (src/ou.c, the spec's numbers): four dishes at their D-pad directions round the cloche (UP cheese, RIGHT
  baguette, DOWN soup, LEFT grapes). Round r = 1..7 calls an order of r + 2 dishes: one seeded sequence (mg_rand) grown
  by one dish a round. ROUND r / LISTEN; the empty bubble 20 frames; each dish lit on the cross and big in Colby's
  bubble (Colby calling) L frames, then G dark: 24 / 8 (rounds 1-3), 20 / 6 (4-5), 16 / 6 (6-7). YOUR TURN: 150
  frames a press (again after each right one). Right: 50, its pip, the dish lit and the Spigoteer serving 14 frames.
  Wrong, or the time out: a strike (HUD), SENT BACK 64 frames (the X over the wrong dish, lit, or over the cloche on a
  timeout; Colby cross with 2 steam puffs, the Spigoteer's shrug), then the same order called again (not grown). The
  order served: ORDER UP! / "200r POINTS" 72 frames (the cloche lifted / set down every 12, Colby pleased, the cheer,
  the waiter). 3 strikes: THREE STRIKES / ORDERS SERVED n; round 7 served: ALL ORDERS SERVED (+1000 and NO STRIKES 1000
  with no strike at all). Medal by rounds served (ou_medal; mg.c asks it as qd_medal): GOLD 7, SILVER 5, BRONZE 3. No
  timer, one setting. A perfect game: 42 x 50 + 200 x 28 + 1000 = 8700.
- **Screen**: the framework's bistro backdrop (it uses BG palette 0 only on rows 1-17: the spec's open check, tested);
  the cross at columns 10-15, rows 5-10; the bubble at columns 3-6, rows 4-7, its tail 3-4 of row 8 (the wall under it
  saved at entry and put back); the pips on row 12 centred at column 13; the strikes at HUD columns 16-18 (mg.c now
  blanks the timer's place before the game's enter, so a game may draw there). CGB BG palettes 2 3 5 6 the dishes
  (colour 0 the wall's), 7 the lit dish (rewritten per light-up at the top of a frame while still in VBlank, LY
  144-151, with no tile using it: the old dish goes dark first, the new one lights a frame later), 4 left to the medal.
  OBJ: Colby palettes 3 / 4, the X 6, the waiter the show's 5; DMG OBP0 0xD0, OBP1 0xC4 (the X, the waiter; the level
  load puts 0xE4 back). OAM 0-1 X, 2-3 steam, 4-7 Colby, 8-11 the Spigoteer, 12-15 the waiter: worst line 4. Tiles:
  BG 125-181 (57: the spec's 56 + one blank for the empty bubble), OBJ 56-87 (Colby's 4 tops share one bottom); the
  coin's 92-95 untouched. say_bang = the '!' tile; mg_leave now clears say_bang. State: struct ou_state in the mg union
  (tests read story_scratch + 0..28).
- **Sounds**: no new SFX (as Quick Draw): the dish tones are UP SFX_COIN, RIGHT SFX_CATCH, DOWN SFX_LAUNCH, LEFT
  SFX_SHAKE; the bell SFX_SERVE; SENT BACK SFX_BREAK. Spec gap: 4.4's four pitched tones (C6 G5 E5 C5) need SFX
  entries in music.c (bank 2, 21 B free); position and picture still tell the dishes apart.
- **Tests** (tests/test_ou.py, 38): the screen and its art, palettes and attributes; a round called dish by dish; the
  timings of all seven rounds frame by frame and the growth keeping the prefix; right presses, ORDER UP! with the
  waiter; SENT BACK and the same order called again; the 150-frame press time and the timeout's X on the cloche;
  presses ignored while calling; a perfect game (8700, GOLD, <= 4 sprites a line); three strikes after 0-6 rounds with
  each medal; no +1000 after a strike; seeded orders; the list; STORY reaching it in the bistro, then the Last call's
  VRAM (both banks), BG palettes and DMG registers as a fresh Last call's (BG tile 77 aside: no level's; OBJ palette 4
  aside: the chefs have no extra palette, so no bistro sprite uses it); ARCADE reaching it. Changed: test_mg_list (the
  list's new line, release unlock for Order Up!), test_story (the mini slot's id is the venue's). New goldens (dmg +
  cgb): ou_intro, ou_call, ou_turn, ou_sent_back, ou_orderup, ou_result. Replaced on purpose: mg_list and
  mg_list_locked (the list gains ORDER UP / a second "? ? ?" line).
- **ROM / WRAM** (rebased on the boss wave and Battery Sort): ROM0 unchanged (811 B real free); ou.c + its art
  (~4.4 KB) went to bank 4 with autobank repacking (banks free after, romusage: 1 78, 2 21, 3 148, 4 20, 5 27, 6 9,
  7 25, 8 6, 9 9, 10 120, 11 5473 B). WRAM: +0 B (the game's state is in the mg union; no new globals): the variables
  still end at 0xDD72, 654 B of stack room.
- **With Battery Sort** (merged first): mg.c's games G_STUB, G_QD, G_BS, G_OU; the MINI GAMES list in the chapters'
  order: QUICK DRAW, ORDER UP, BATTERY SORT (+ GREEN LIGHT in the debug build), so test_bs's list tests find Battery
  Sort on the third line; mg_list / mg_list_locked replaced again (the ORDER UP line).
- Test-harness note: a 1-frame D-pad tap can fall between two joypad reads right after a frame with a long VBlank copy
  (the logic moves against PyBoy's frame cut); test_ou holds presses 2 frames.

## Leo and Sumo as built (docs/minigames_bosses.md 3.11 / 3.9, 2026-10-12)
Both follow "Boss hooks as built": a dispatcher `uint8_t boss_<name>(uint8_t ev, uint8_t arg) BANKED` in its own
`src/boss_<name>.c` (case 7 Teahouse = the Sumo, case 8 Jungle zoo = Leo in boss.c), state in a struct in the 20 B
BOSS_OWN buffer, so **no new WRAM global** (WRAM_LO / WRAM_HI_0 unchanged: 3936 / 3454 B used). Their slots are built
in gen_story BUILT_SLOTS (BOSS: TEAHOUSE, ZOO). Art: `assets/art/boss/{sumo,leo}.txt` (moved out of `approved/`);
gen_boss BOSSES gained both, plus a `tiles` key (a boss's own 8x16 BG blocks at BG 246.., max 3; Leo's "!!"). Engine
additions in boss.c: `boss_advance()` (one 8 px stomp for a boss that moves himself; `boss_step` 0 turns the engine's
stomp timer off) and the boss column stamp clears columns past his width (a special's column).
- **Sumo** (40 px, bar 1, step 96, push 0, gulp 0, hands 2, sip 90, **meter 8**): steps on the teahouse tune's beat (96
  frames = one bar of "sakura"; his own clock with the music off), 14 B state (sumo_t). A single hit never pushes him; a
  chained hit (within 80 frames of the last) pushes 8 px; his HUD face blinks while a chain is live. Every 480 walking
  frames the SHIKO stamp tells for 60 frames (a hit cancels it: the HMPH pose), else he charges 24 px in 12 frames. The
  spec's counter-dust tiles are skipped (no approved art; SHIKO is the tell).
  **Difficulty (owner decision 2026-10-12): the meter is 8, not the spec's 12.** The test bot lands about 1 cup per 100
  frames and, unhit, he reaches the tap after 10 steps (960 frames); at 12 cups he got to about 11 of 12 and was likely
  unbeatable. `test_win_the_fight_by_pouring` plays the real 8-cup fight (no hp poke): the bot wins it, no life lost,
  at least one chained hit. Goldens: boss_sumo, boss_sumo_shiko (new, DMG+CGB).
- **Leo** (32 px, step 80, push 8, gulp 30, hands 2, sip 60, meter 14), 8 B state (leo_t). Every 420 walking frames: a
  60 frame INHALE tell with "!!" in his 5th column, then a 30 frame ROAR that pushes every regular walker back 16 px (no
  score, no thirst) and makes drinkers in their minimum drink finish now; empties still obey the fair-empties spacing
  (next_arrival / empty_gap). Goldens: boss_leo, boss_leo_roar (new, DMG+CGB).
- ROM (romusage, main b575841 -> now): bank 11 12505 -> 16235 B used, new bank 12 520 B; banks 1 / 6 / 8 / 10 repacked
  by the linker (16306 -> 16251, 16297 -> 16364, 16378 -> 16227, 16114 -> 16172); the rest unchanged. Tightest free:
  bank 9 10 B, bank 4 20, bank 6 20.
