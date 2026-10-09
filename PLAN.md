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
  catches it and is pushed back toward the left. A patron pushed past the
  door leaves (served). A patron who stays drinks for a while, then sends the
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

- Columns 0–1 are the door, columns 2–17 the counter, and columns 18–19 the tap.
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
- Art round 3 (proposals in the session scratchpad, owner approves before import): balanced mustache; cowboy without far ear; sports fan redesigned (foam finger in jersey colour); slot B of every group except zoo is a woman; all patrons 3/4 view facing right.

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
start, <= 2 CGB palettes), a bar palette (wall/counter/door; wall = colour 0 behind patrons), and
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

Done: title "The Entertainer", "Galop infernal" for every show, nine venue tunes (table in CREDITS.md; tune
index TUNE_VENUE0 + patron group), jingles unchanged. hUGEDriver only reads patterns through plain pointers in
the bank it runs from, so song patterns live in ROM bank 3 and src/music.c copies a song into WRAM (buffer A:
title or venue tune; buffer B: the show tune, copied once in the background) a slice per frame before it
starts; bank 2 keeps the driver, order tables, instruments and jingles. Sources: tools/songs.py; pitch check:
tools/check_music.py (routes one channel to the output and prints expected vs detected pitch).
Caveat: the melodies were written from memory and nobody has listened to them; the owner's Oh! Susanna and the
given Entertainer note list are exact, the rest (especially the Galop, Funiculi, the later phrases of the
ball-game and mountain tunes, Skaters' Waltz, Blue Danube) are best-effort and need an ear check.

Drums and game tempos (after M9): owner-approved game tempos (tools/songs.py GAME_BPM; spec tempo stays in docs/music_specs.md):
entertainer 8 frames/row = 112.5 bpm, sakura 15 = 120, funicula 11 = 109 (dotted quarter), skaters/danube/ballgame 9 = 200.
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
20-35, shared HUD tiles 36-71, patrons 72-215, back views 216-227 (228 of 256); title lettering still loads over the
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
| M10b | Arcade mode: endless loop of the nine venues; "LOOP n" banner; each loop a bit harder up to a ceiling; top-5 high scores with 3-letter initials in SRAM (replaces the single hi score). Done (see M10b as built). |
| M11a | Story script: "The Golden Spigot" - the legendary spigot that pours any drink shattered into 9 pieces; each venue owner gives one to a bartender who keeps their crowd happy. Written as docs/story.md for owner approval before any code. |
| M11b | Text engine + full font + cut-scene system (still picture + portrait + text box, A to advance), chapter goals per venue (serve N, no broken glass...), venue twists, save/continue in SRAM. ROM likely grows to 256 KB. |
| M11c | Story art: portraits (Spigoteer, nine venue owners, villain if any), cut-scene pictures. Owner approves. |
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
Spigoteer's normal sprite, a framed 32x32 speaker portrait above a full-width 3x18 text box).
Portraits for every speaker (assets/approved/story/portrait_*.txt; Spigoteer and Sadie done).

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
