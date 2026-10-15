# Spigoteer: mini-games, bosses and the Pour-Off (design spec)

Status: design proposal for the owner, 2026-10-10. Nothing here is built. Art in this document is a list of what
must be drawn; every piece goes to the owner as a proposal first. Story text changes are suggestions only
(docs/story.md is not edited by this document).

Note (planner, 2026-10-10): this spec was written while the story shifts (M11d) were being built. They are now in:
SRAM v4 with the step reached already exists (PLAN.md "Story shifts as built"), and the mini-game / boss slots are in
the chapter sequence. Where section 2.2 proposes its own segment index and SRAM v4 layout, follow the built version.

Note (2026-10-10, owner-approved; built 2026-10-11): a 10th venue, **The Chrome Cow** (a biker bar that serves only
milk, owner Granny Throttle), is chapter 7, before the teahouse; and the space lounge moves to the end (owner,
same day). Built: the venue, its story chapter, the new order, the save migration (SRAM version 6) and the mosh pit
(section 9); Duke (3.12) and Milk Run (4.10) are not built yet (their slots are skipped like the other unbuilt ones). The order: saloon, stadium, lodge, bistro, igloo, factory, The Chrome Cow, teahouse 8, zoo 9, space 10,
in story and arcade. Its boss **Duke**
is section 3.12, its mini-game **Milk Run** section 4.10 and its twist, the **mosh pit**, section 9. They are numbered
last so the existing section references stay; the summary tables list them in chapter order. The engine checklist
for a 10th venue is docs/venue10_impact.md. Owner (2026-10-11): the name **The Chrome Cow** is final; questions 11
(mosh pit in Last call: on) and 12 (its tune: "Drunken Sailor", fast and punky) are answered in section 8.

Structure the owner approved, per chapter:

    PRE scene -> Opening shift -> Happy hour (venue twist on) -> MINI-GAME -> Last call -> BOSS -> POST scene

Losing retries only that shift. Practice mode (title menu) unlocks each shift, mini-game and boss as story mode
reaches them. The finale adds a Pour-Off against Dregs.

This document covers the ten mini-games, the ten bosses, the Pour-Off and the shared code they need. Opening
shift, Happy hour and Last call are the existing bar engine (the twists are M11b part 2) and are only mentioned
where a boss or mini-game touches them.

## 0. Ground truth this spec is built on (measured 2026-10-10, `make`)

| item | value | source |
|---|---|---|
| ROM | 128 KB, MBC5 + RAM (`-Wm-yt0x1B -Wm-yoA -autobank`); banks 1-6 have 15-132 B free, bank 7 5819 B | romusage |
| ROM0 real free | 1708 B (game.gb) | tools/rom0free.py |
| WRAM | `_DATA` runs 0xC0A0-0xD8A1 (6145 B) + 15 B initialised, ends 0xD8B0. The stack grows down from 0xE000. So ~1.87 KB lies between the data and the stack top, minus the stack's depth. romusage's "WRAM_LO 160 B free" is only the 0xC000-0xCFFF half. | build/game.map |
| BG tile ids in play | 0-35 venue pool, 36-76 HUD/shared, 77 unused, 78-233 patrons (A shifts 78-119, B 120-161, C 162-203, shift-0 poses A 204, B 210, C 216, back views 222-233), 234-239 free, 240-251 DMG plane-swapped mug copies (OBJ), 252-255 free | game.h, PLAN.md M13a |
| OBJ tile ids in play | 0-55 bartender (7 frames x 8), 56-95 drink / crash / coin, 96-127 show performers; ids 128+ share VRAM with BG 128+ | game.h |
| OAM in play | 0-3 bartender, 4 fill, 5-25 mugs (lifted patrons count down from 25), 27 coin, 28-39 dancers | game.h |
| CGB BG palettes | 0 bar, 1 HUD, 2-4 patrons A/B/C, 5-6 stage, 7 bar_b (keg; enhanced row palette S) | game.h |
| CGB OBJ palettes | 0 bartender, 1 full drink, 2 empty / glass, 3/6/7 lifted patrons A/B/C, 4 enhanced X, 5 coin / show | game.h |
| Bar geometry | bar b top y = 40 + 24 b; rows: 2 wall rows (patrons, BG) + 1 counter row. Mugs are 8x16 OBJ at top+4..top+19. The bartender is 4 entries, 2 per line, top..top+31 (his lower entries reach 8 lines into bar b+1) | layout.h, render.c |
| Per-line budget today | bartender 2 + fill 1 + 6 mugs (MUGS_PER_BAR) + coin 1 = 10; lifted patrons are admitted by lift.c only while the estimate stays <= 10 | game.h, lift.c |
| Speeds | full mug 2 px/f, empty 0.5 px/f, walk 1.5 px/f, fill 16 frames; patrons 8 px per 64 (L1) .. 52 (L9) frames; EMPTY_GAP 120 (L1) .. 80 (L9) | game.h, level.c |
| Existing mini-game pattern | src/bonus2.c: own bank, venue backdrop, banner rows 2-3 in HUD colours, OBJ 96-127 and BG ids from 77 borrowed, `bonus_phase` 4 ends any round (test poke), level load restores everything | bonus2.c |

Two consequences drive most of the hardware choices below:

1. The level screen is already at 10 objects on a bar's mug lines. A boss cannot be a big OBJ metasprite on a
   bar without lowering the mug cap. **Bosses are BG figures** (zero sprites on their lines), with one 8x16 OBJ
   "topper" (hat, crown, ears, dome) that pokes above the bar. Section 3.1 counts it line by line.
2. VRAM is full in play. A boss fight loads only patron variants A and B for the regulars, which frees variant C's
   48 tiles, the 12 back views (no show in boss fights) and the spare ids: **66 BG ids for the boss** (70 with
   252-255). The space boss is the exception (section 3.10).

WRAM is less tight than the brief assumed (about 1.3 KB really free once a generous 512 B stack is allowed for),
but the plan still shares memory: all mini-game state and the Pour-Off live in one union laid over story.c's
cut-scene backdrop buffer (`bd_map` + `bd_attr`, 520 B, used only while a cut-scene shows). Boss state (~40 B)
stays separate because it must survive a life lost.

## 1. Summary

### 1.1 Mini-games

| # | Venue | Name | Skill | Controls | Length | Main change from the pitch |
|---|---|---|---|---|---|---|
| 1 | Saloon | Quick Draw | reaction + reading | A or B | ~30 s | added the A-or-B sign from round 3 and feints, so it is a choice reaction, not a single press; early press = foul |
| 2 | Stadium | T-Shirt Cannon | aim (4 angles) + golf-style power meter + picking the fan with raised hands | Up / Down aim, A start meter, A lock + fire | 10 shots, <= 45 s | meter with red oops zones; raised fans last 2 s, reach one column each side; build-time reach table |
| 3 | Lumber | Log Roll | balance, timing of corrections, dodging | Left/Right taps; A / B / Up hop | 40 s | falls are not game over (3 s penalty); drift changes are telegraphed; holding does nothing (taps only); fish leap across the log (D3, 4.3), told by ripples, dodged by a hop |
| 4 | Bistro | Order Up! | memory | D-pad, one direction per dish | ~45 s | dishes sit at their D-pad direction on screen; a strike replays the same order |
| 5 | Igloo | Marshmallow Drop | timing, leading a moving target | A | 45 s | the claw moves at constant speed on a rail (not a pendulum); marshmallows fall straight down; 4th marshmallow overflows |
| 6 | Robot | Battery Sort | categorise under pressure | Left / Right (Down from item 16) | 45 s | the front battery waits on a diverter for a shrinking window; a 3rd bin (scrap) arrives mid-game |
| 7 | Chrome Cow (PROPOSAL) | Milk Run (4.10) | lane dodging + delivery timing | Up/Down lane, Right/Left speed, A top toss, B bottom toss | 70 s (D4 rework) | mostly BG: the street scrolls (SCX), obstacles and milk boxes are BG tiles; every gate leaves a lane free |
| 8 | Teahouse | Taiko Pour | rhythm | A (top lane), B (bottom lane) | ~45 s | two lanes instead of one (readable on DMG, fits 10 per line) |
| 9 | Zoo | Monkey Business | reaction + positioning | Left/Right, A | 45 s | one row of 5 crates, the Spigoteer hops between them; lids rattle before a pop; a parrot decoy from 15 s |
| 10 | Space | Asteroid Delivery | inertia steering, route reading | D-pad thrust | 45 s | asteroids drift in horizontal lanes (Frogger-like); soft-delivery speed limit; no gravity, just drift |

### 1.2 Bosses

| # | Venue | Boss | Meter | Special | Main change from the pitch |
|---|---|---|---|---|---|
| 1 | Saloon | Big Tex | 8 | none (tutorial boss), 40 px wide, owns his bar | "fills a bar" = he owns one bar; regulars use the other three |
| 2 | Stadium | The Mascot | 10 | jumps bars every 5 s; crouch + landing marker tell | waits for mugs already thrown before the crouch; scares regulars off the bar he lands on |
| 3 | Lumber | Sasquatch | 12 | drinks instantly, empties back at 1 px/f, holds max 2 | "hands full" rule so spamming has a cost |
| 4 | Bistro | The Food Critic | 8 | only perfect pours count; sloppy ones come back full | perfect = released within 12 frames of full (new fill window, only shown in this fight); busy critic returns mugs instead of letting them break |
| 5 | Igloo | The Yeti | 12 | icy breath: his bar goes icy for 3 s, every mug on it 2x | timed window with a visible tell; icy also speeds your mugs (risk / reward) |
| 6 | Robot | The Prototype | 12 | green / yellow / red cycle; red reverses his conveyor; switches bars after red | reworked: "conveyor runs backwards" is the red phase, with a yellow tell |
| 7 | Chrome Cow (PROPOSAL) | Duke (3.12) | 12 | no stomp: idles, revs 50 frames, lurches 16 px; a glass resets his idle, a glass during the rev stalls him | "revs between serves" became a rule with a readable answer |
| 8 | Teahouse | Sumo Champion | 8 (was 12: owner decision 2026-10-12, the bot lands ~1 cup per 100 frames) | single hits do not push him; chained hits (<= 80 frames apart) do; charge on a tell, cancelled by a hit | "barely moves" became the chain rule |
| 9 | Zoo | Leo the Lion (crowned) | 14 (PROPOSAL, zoo 9th: 12) | roar: walkers jump back 16 px, drinkers send empties early | "empties fly" still obeys fair-empties spacing |
| 10 | Space | The Mothership | 6 + 3 x 2 (PROPOSAL, space last: 8 + 3 x 2) | teleports; at 0 it splits into 3 small aliens (2 drinks each) | splits once (not on every hit, which would flood the bars) |
| F | Finale | Pour-Off vs Dregs | first to 20 | race to serve a shared crowd from opposite ends | own module, own simple patron/mug rules |

Flagged as weakest after fixing: **Quick Draw** (thin by nature; fine as a 30 s breather), **Asteroid Delivery**
(inertia steering needs playtest tuning) and **The Food Critic** (adds a timing rule to the core pour; may feel
fussy). Highest technical risk: **Taiko Pour** (sync to hUGEDriver rows), **the Mothership** (tile budget) and the
**Pour-Off** (second bartender, mirrored rules).

### 1.3 Worst-case hardware numbers

| screen | worst objects on one line | OAM entries | new BG tiles | new OBJ tiles | CGB palettes used (BG / OBJ) | WRAM |
|---|---|---|---|---|---|---|
| Quick Draw | 6 | 12 | ~31 | ~52 | 6 / 4 | 16 B |
| T-Shirt Cannon | 6 | 11 | ~37 | ~28 | 6 / 3 | 40 B |
| Log Roll | 9 | 19 | ~30 | ~86 (Sasquatch reused) | 5 / 5 | ~60 B (in the mg union) |
| Order Up! | 4 | 4 | ~100 (portrait incl.) | 0 (waiter reused) | 8 / 1 | 20 B |
| Marshmallow Drop | 9 | 14 | ~20 | ~30 | 5 / 3 | 30 B |
| Battery Sort | 8 | 12 | ~41 | ~4 (+ factory drink reuse) | 7 / 4 | 45 B |
| Milk Run (PROPOSAL) | 6 | ~8 | ~38 | ~26 | 5 / 3 | 40 B |
| Taiko Pour | 7 | 19 | ~30 | ~8 (+ teahouse show reuse) | 6 / 4 | 35 B |
| Asteroid Delivery | 6 | 23 | ~35 | ~12 (+ space drink reuse) | 6 / 3 | 45 B |
| Monkey Business | 8 | 13 | ~30 | ~30 | 6 / 4 | 25 B |
| any boss fight | 10 (unchanged cap; topper fits, section 3.1) | 40 (unchanged; topper uses OAM 26) | <= 66 (Mothership 23) | <= 32 (ids 96-127) | BG 4 + OBJ 5 and 7 freed for the boss | 40 B |
| Pour-Off | 10 (mug cap 4 per bar) | 26 | ~44 (36 patron + 8 keg) | ~40 (Dregs) | 8 / 6 | ~130 B |

ROM: roughly 60 KB more in total (section 6). The ROM grows from 128 KB to 256 KB; `-Wm-yoA` sizes it, no flag
change. ROM0: about 200-250 B of hooks out of 1708 B free.

## 2. Shared infrastructure

### 2.1 The mini-game framework (`src/mg.c`, banked, plus one file per game)

Flow, in every mode:

    mg_enter(id, mode)  LCD off: hide OAM, vq_reset, HUD row (score), the game's own screen (its enter function)
      MG_INTRO   90 frames: two-row banner (name, one-line instruction), as bonus2.c does on rows 2-3
      MG_COUNT   60 frames: "READY" then "GO" on the banner rows (skippable with A in practice only)
      MG_PLAY    the game's update function runs; the HUD timer counts down if the game has one
      MG_END     <= 60 frames: the game's own outro (the stranger falls over, the Sasquatch splashes...)
      MG_RESULT  window overlay, 5 rows like the chapter goal banner: name / score / medal / prompt
                 story: "A CONTINUE" (>= 60 frames shown first); practice: "A RETRY B MENU"
    mg_update() returns 1 when the player leaves the result

- `GS_MINI` (13) is a new game state; main.c's switch calls `mg_update(pressed)` (banked) for it: ~20 B ROM0.
- Each game provides `xx_enter()` and `xx_update(pressed)` (BANKED, own file, `#pragma bank 255`). mg.c dispatches
  with a switch (no banked function pointers).
- Text: a ROM0 helper `mg_say(row, const char *s)` (~60 B) centres a string from HUD glyphs into a WRAM buffer and
  queues it. It must be in ROM0 because the strings live in each game's own bank (the rule in PLAN.md: banked code
  never passes a pointer to its own ROM data into another switchable bank; a ROM0 callee is fine because the
  caller's bank stays mapped). bonus2.c's `text()` / `banner()` move here; bonus2 then calls it too.
- Timer: HUD columns 16-19, 'T' + seconds, the story HUD's format (story.c `hud_goal`).
- Medals: each game has three score thresholds (bronze / silver / gold, tables below). The result shows the medal
  word (GOLD / SILVER / BRONZE / NO MEDAL) from HUD glyphs and a medal icon (4x4 BG tiles, 32x32, 3 looks; as built).
- Score: points go through `add_score()` as they are earned (as the bonus rounds do), so the HUD stays live.
- RNG: `mg_seed` (16 bit) is set at entry from `next_rand()`; tests poke `mg_seed_force` (non-zero: use it) before
  entry. Each game runs its own small LFSR from it, so the bar game's RNG sequence is not disturbed.
- Test hooks common to all: `mg_id`, `mg_phase`, `mg_timer` (frames left), `mg_score`, `mg_medal` (0-3). Poking
  `mg_phase = MG_RESULT` ends any game (the bonus rounds' "phase 4" convention).
- Restore: every resource borrowed (OBJ 56-127, BG 77-255, palettes 2-7 BG and 1-7 OBJ, OBP1 on DMG) is put back by
  the next level load, exactly as after a bonus round. mg.c does not restore anything itself. A test asserts this
  after each game (the M14a pattern: bank-1 tiles, OBJ 4, BG 7 after each round).
- Music: the venue's tune (Taiko Pour: see 4.7). Effects through the existing SFX ids where they fit; new SFX:
  DRAW bell, fan cheer, splash, four order tones, taiko don / ka, thud, roar, beep (short, channel 1 / 4).

Resources a mini-game may use (no patrons, no mugs, no show while it runs):

| resource | free for a mini-game |
|---|---|
| BG tile ids | 77-255 (179 ids; 128-255 are shared with OBJ 128-255). 0-35 too if the game does not keep the venue backdrop. CGB VRAM bank 1 (384 more) only for CGB-only polish, never for gameplay. |
| OBJ tile ids | 56-127 (72 ids) plus any of 128-255 not used as BG. 0-55 stay the Spigoteer's. |
| OAM | all 40 (0-3 by convention the Spigoteer when he is on screen) |
| CGB BG palettes | 0 and 5-7 hold the venue backdrop if kept; 1 HUD; 2-4 free (7 too if the keg is not shown) |
| CGB OBJ palettes | 0 Spigoteer; 1-7 free |
| DMG | BGP as in play; OBP0 0xD0 / OBP1 free per game (Tip Shower already sets 0xE0) |
| WRAM | the `mg` union (section 2.4), <= 128 B per game |

### 2.2 Where mini-games and bosses sit in story mode

story.c today plays one level per chapter (`chapter_start` -> `enter_level_screen`). The new chapter is a list of
five segments: OPEN, HAPPY, MINI, LAST, BOSS. A segment index `story_seg` (0-4) joins `story_chapter`.

- OPEN / HAPPY / LAST: the existing level with goal banner and goals (part 2 of M11b decides their goals and twists).
- MINI: `mg_enter(chapter, MG_STORY)`. **Mini-games never block the story** (recommended, open question 1): any
  result continues. Medal bonus: gold 3000, silver 1500, bronze 500 points; a gold medal also gives the boss shift
  one extra life (4 instead of 3) for that chapter's first boss attempt. A banner before the game says what is at
  stake ("GOLD MEDAL / EXTRA LIFE FOR THE BOSS").
- BOSS: the venue's level screen in boss mode (section 3). A failed boss attempt shows TRY AGAIN and restarts the
  boss segment only (meter full again), as chapter goals restart today.
- Save: SRAM v4. Byte 34 stays "chapters cleared" (0..9, 10 = Pour-Off won; with The Chrome Cow, as built: SRAM
  v6, 0..10, 11 = Pour-Off won, migrations from v1-v5 in src/save.c); the reserved byte 35 becomes
  `story_seg` of the first chapter not cleared, so CONTINUE resumes at the shift the player reached (not at the
  PRE scene) and Practice knows what is unlocked. Practice best scores: 10 x 5 segments x 3 B = 150 B (11 x 5 x 3 = 165 B with ten chapters) after the
  checksum area (new checksum range). Migration v3 -> v4: seg 0.

### 2.3 Practice mode

- Title menu gains PRACTICE once story mode has cleared its first segment (progress > 0 or seg > 0). Rows: ARCADE / STORY / CONTINUE / PRACTICE / MUSIC: the title's text rows move up one
  (rows 4/6/8/10/12, HI row 14): a title.c layout change, `MENU_STRINGS` gains "PRACTICE".
  (Bonus menu, 2026-10-10: the title now also has BONUS and its HI line on row 0; PRACTICE's rows: PLAN.md "Bonus menu and soundtrack as built".)
  (Owner, 2026-10-11: the title menu is PLAY / BONUS / SETTINGS with submenus; PRACTICE becomes BONUS's second item,
  after SOUNDTRACK, so the top level and its rows do not change: PLAN.md "Title submenus as built".)
  (As built 2026-10-11: BONUS's second item is MINI GAMES, the mini-games reached in STORY or ARCADE with their best
  medals, saved in the block at SRAM 0x40; the chapter / segment screen below, for shifts and bosses, is not built:
  PLAN.md "Quick Draw and BONUS > MINI GAMES as built".)
- Practice screen (new, banked, HUD style like the scores table): rows 3-12 list the chapter's five segments, the
  chapter number and venue name on row 2; Left/Right changes chapter (1-9, then FINALE; 1-10 with The Chrome Cow), Up/Down the segment, A
  starts it. Locked segments show "- - -". The best score is on the right.
- A practice run is one segment with 3 lives, score from 0, never enters the top 5. At the end: result window with
  "A RETRY  B MENU". Boss segments show the boss's meter progress when lost ("TEX 3 OF 8").
- Mini-game practice has one setting (the story's). Replays are the practice; no difficulty select (open question 7).

### 2.4 Shared WRAM

    union mg_ram {                      // laid over story.c's bd_map/bd_attr (520 B, cut-scenes only)
        struct qd_state qd;             // each <= 128 B, sizes in section 4
        ...
        struct po_state po;             // Pour-Off, ~130 B
    };

story.c exports the buffer as `story_scratch[520]` and the mini-game files use `#define MG ((union mg_ram *)story_scratch)`.
Nothing in a mini-game or the Pour-Off runs during a cut-scene, and a cut-scene's `scene_enter` rewrites the buffer
from scratch with the LCD off, so the overlay is safe. A static assert checks `sizeof(union mg_ram) <= 520`.
Boss state is **not** in the union (the TRY AGAIN banner is a story.c phase; keep the two apart): `boss_*` globals,
~40 B, in boss.c.

### 2.5 The boss engine (`src/boss.c`, banked; hooks in ROM0)

One engine, ten parameter rows (with Duke) plus a per-boss "special" function. The bar game runs as usual (the regulars, the
bartender, mugs, fair empties, lives); the boss is one more actor on one bar.

Rules common to every boss:

- **The boss owns his bar.** No regular spawns on it, and when a boss arrives on a bar (start, jump, teleport) the
  regulars on it are scared off: each slides out to the left as a leaving patron (`lift_leave` path) with no score
  and no served count; a full mug in his hand leaves with him. Empties already sliding on that bar keep sliding.
- **Position** `boss_x` is a multiple of 8 (the body is BG). He advances one 8 px "stomp" every `step` frames
  (a 2-pose bob: pose B for 8 frames on each stomp, SFX thud). Push-back is in 8 px hops, one hop per 4 frames.
- **Catching**: a full mug on his bar that reaches `boss_x + width - 4` is caught, unless his hands are full (see
  below). A catch: meter -1 (unless a special says otherwise), push-back `push` px, gulp pose for `gulp` frames
  (no advance meanwhile), the mug is freed (his drink is drawn in his BG pose, not as a mug sprite), and he now
  holds one empty.
- **Drinking shake (E1, owner 2026-10-14)**: while he gulps (no push-back, no special's pose) his body alternates the
  GULP pose (mug up) and WALK every `SWAY_FRAMES` (12), the patrons' sway beat, and the topper (a sprite) shifts the
  patrons' 2 px on the odd beats. The gulps are 30-50% longer than the first build (the table in 3.2; the Sumo has none).
- **Status tag (E1, owner 2026-10-14: "it's not clear what status he is in")**: one 8x16 sprite (OAM 29, OBJ 124-127,
  `assets/art/boss/tag.txt`, his own colours) above his hand column, where a drink reaches him. READY: an empty mug and
  an arrow down at his hand (a hand is free: `boss_lim`). BUSY: a full mug and a cross (hands full: a drink slides
  past). The BUSY tag shaking side to side: he sends what reaches him back (the Critic while he holds a glass, tastes or
  has a drink to send back). Hidden in the intro, in the outro, and while he is away (BS_JUMP / BP_HIDE). A special
  overrides it through the `BEV_TAG` event (return TAG_x + 1; TAG_OFF + 1 hides it). The hat has the line budget first.
- **Hands**: he holds at most `hands` empties. Each held empty is sent (spawn_mug(EMPTY) at his right edge) after
  `sip` frames **and** only when the fair-empties schedule allows (`next_arrival`, `empty_gap`, the same rule as
  patrons.c, computed with his own empty speed). With full hands a mug reaching him is not caught: it slides on
  past him (in front of the BG figure) and breaks at the left end (a life), as a full mug passing a busy patron does. His pose shows how many
  he holds (0, 1, 2 steins), so the danger is visible.
- **The tap**: if his right edge reaches the tap end (`boss_x + width >= 136`) the player loses a life (as a patron
  reaching the tap does). After the life-lost pause he restarts at his start x on his current bar, meter kept.
- **Win** (owner, 2026-10-13: the fight ends only when the bar is clear): meter 0 -> he is beaten (his happy pose, or
  gone), the banner CLEAR THE BAR shows for 90 frames, no regular spawns any more, and the fight goes on (a patron at
  the tap still costs a life) until no regular is left (`patrons_live` 0: served or cleared). Only then: the boss's happy pose and a 120-frame outro (he burps a bubble, waves, hands over the piece),
  all regulars stop, remaining mugs vanish, CHAPTER CLEAR as today, then the POST scene.
- **Lose**: lives 0 -> TRY AGAIN, boss segment restarts with the meter full.
- **Regulars**: the chapter's level row (speed, hurry, push-back, serve score, empty gap) on the bars without the
  boss; spawn interval x 1.5; quota 255; patron variants A and B only (`try_spawn` masks variant 2 when `boss_on`).
  No tips, no show (tip_chance 0).
- **Specials** run on their own timers, always with a tell of >= 45 frames that is drawn on the BG (pose change,
  marker tiles), never only as a sound.

The HUD in a boss fight: score 1-6 and lives 9-11 as always; column 12 a boss face icon (8x8), columns 13-19 the
meter as 7 tiles of 2 pips each (14 pips max; tiles: empty, half, full). Level digits are not shown.

```
    01234567890123456789
 00 .999999..UUU@MMMMMMM     9 score, U lives, @ boss icon, M meter (2 pips per tile)
```

ROM0 hooks (all small; each is one test of a WRAM flag on a path that already exists):

| where | what | ~ROM0 |
|---|---|---|
| patrons.c `catch_full` | nobody caught it and the bar is `boss_bar` -> `boss_catch(i)` (banked) | 25 B |
| patrons.c `try_spawn` | skip `boss_bar`; variant 2 -> 0 or 1 when `boss_on` | 20 B |
| render.c `stamp_bar` | `b == boss_bar` -> stamp the boss's columns from `boss_tiles[2][5]` / `boss_attr` (WRAM, written by boss.c) after the patrons | 50 B |
| mugs.c step functions | per-bar speed masks `mug_fast` (full +1 px/f) and `empty_fast` (empty every frame), for the Yeti and the Sasquatch | 30 B |
| mugs.c | `MUG_RETURN`: moves right like an empty but draws the full-drink tile (Critic, Prototype); caught like an empty, breaks at the right end | 40 B |
| main.c | `GS_MINI` case; `boss_frame()` after `play_frame` when `boss_on` (as `story_play`); fill timer keeps counting past FILL_FRAMES and its value at launch is kept for the Critic | 40 B |
| total | | ~205 B of 1708 |

Everything else (the boss's movement, specials, HUD meter, topper sprite, the reset after a life) is in boss.c and
in main_cold.c's banked `reset_actors` (one call to `boss_reset()`).

Boss tiles and palettes at the level load (LCD off, level.c `start_level` in boss mode):

- BG ids 162-203 and 216-239 (66) + 252-255 (4): the boss's poses, HUD icon + meter tiles (4), marker / effect
  tiles. Loaded by `boss_load(id)` from the boss's own bank. `load_patron_tiles` skips variant C and the back views.
- OBJ ids 96-127 (32): the topper's frames and any boss OBJ effect (no show in boss fights).
- CGB BG palette 4 (variant C's): the boss body. Colour 0 = the venue wall (set like the patron palettes, so the
  body's transparent pixels are the wall). OBJ palette 7 (lifted variant C): the topper. OBJ palette 5 (coin/show,
  unused): one effect palette; render.c's `pal5_check` must not rewrite it while `boss_on`.
- DMG: the body is BG greys (index order = brightness, as every asset); the topper uses OBP1 0xE4 like lifted
  patrons, so it shades exactly like the body.

Test hooks (every boss): `boss_on`, `boss_id`, `boss_bar`, `boss_x`, `boss_hp`, `boss_hold`, `boss_state`
(walk, gulp, tell, special, jump, outro), `boss_t` (frames in state), `boss_special_t` (frames to the next special),
`boss_hook` (poke 1 = start the special's tell now, 2 = meter to 1, 3 = defeat now), plus the per-boss variables
named in section 3. Bar choices use `next_rand()`, so a test that sets the RNG state gets the same jumps. A new
tests/test_boss.py runs each boss: hit, push, hands-full pass-through, tap = life, reset keeps the meter, special
fires on time with its tell, defeat outro, TRY AGAIN restarts with a full meter, budgets (<= 10 per line every
frame, the test_perf helper), and the restore of variant C / back views at the next level load.

## 3. Bosses

### 3.1 Why BG, and the line count with the topper

A boss as an OBJ metasprite 32 px wide puts 4 entries on each of his lines. His bar's mug lines already carry the
bartender (2), the fill (1) and up to 6 mugs: 13. Keeping him OBJ would mean capping his bar at 3 mugs and dropping
lifted patrons on that bar, and a bar-jumping boss would cross other bars' lines in flight. As BG he costs nothing
on any line, and the render code already composes a bar's two wall rows from tiles (patrons are BG for the same
reason). The price: he moves in 8 px steps. For heavy, stomping bosses this reads as weight, not jerkiness
(arcade-style), and push-back hops of 8 px read clearly.

The body is 4 or 5 tiles wide and 2 tall (32x16 or 40x16), on his bar's two wall rows, behind the counter like a
patron; the counter hides his legs. To look bigger than a patron he gets one 8x16 OBJ entry, the **topper** (OAM
26, unused since the door puff went), whose upper 8 rows stick out above the bar: hat crown, ears, crest, dome,
crown. Its lower 8 rows are transparent.

Line count, boss on bar b (T = his bar's top y; the topper covers T-8 .. T+7):

| lines | what can be there | worst |
|---|---|---|
| T-8 .. T-5 (bar b-1's counter, upper half) | bar b-1: bartender 2, fill 1, mugs 6; topper 1 | **10** |
| T-4 .. T-1 | bartender (on b-1) 2, topper 1 | 3 |
| T .. T+3 | bartender (b-1's lower half or on b) 2, topper 1 | 3 |
| T+4 .. T+7 | bartender 2, fill 1, mugs of bar b 6, topper 1 | **10** |
| T+8 .. T+19 | bartender 2, fill 1, mugs 6 (one spare: the only place a boss OBJ effect may go) | 9 |
| bar b-1's patron lines (T-24 .. T-9) | unchanged: the topper does not reach them, so lift.c's estimate is unchanged | as today |
| bar 0 boss | the topper is on stage row 4 (lines 32-39); dancers are off in boss fights | 3 |

Edge case: a glass breaking on bar b-1 is 2 entries; with 5 other mugs, the bartender filling on b-1 and the topper
that is 11. boss.c hides the topper on frames where bar b-1 holds 6 mug entries or more (the cached per-bar count
lift.c keeps). The hat blinking off for a few frames is acceptable; 11 on a line is not.

No regular stands on the boss's bar, so no lifted patron is ever on his lines.

### 3.2 Common numbers

| boss | width | start x | step (frames per 8 px) | push per hit | gulp | hands | sip (frames before an empty) | his empty speed | meter |
|---|---|---|---|---|---|---|---|---|---|
| Big Tex | 40 | 16 | 120 | 16 | 58 | 3 | 60 | 0.5 | 8 |
| Mascot | 32 | 16 | 100 | 8 | 34 | 2 | 45 | 0.5 | 10 |
| Sasquatch | 32 | 16 | 90 | 8 | 20 | 2 | 0 (gap only) | 1.0 | 12 |
| Food Critic | 32 | 16 | 110 | 16 (perfect only) | 84 | 1 | 90 | 0.5 | 8 |
| Yeti | 32 | 16 | 100 | 8 | 44 | 2 | 60 | 0.5 (1.0 on ice) | 12 |
| Prototype | 32 | 16 | 100 | 8 | 30 | 2 | 45 | 0.5 | 12 |
| Duke (PROPOSAL) | 40 | 16 | no stomp: idle 150 / 120 / 90, rev 50, lurch 16 px in 8 frames | 16 | 30 | 2 | 45 | 0.5 | 12 |
| Sumo | 40 | 16 | 90 (on the drum beat) | 0 single / 8 chained | 0 | 2 | 90 | 0.5 | 12 |
| Mothership | 32 | 16 | 100 | 8 | 34 | 2 | 45 | 0.5 | 6, then 3 minis x 2 |
| Leo | 32 | 16 | 80 | 8 | 44 | 2 | 60 | 0.5 | 14 |

Distance from the start (right edge 48 or 56) to the tap (136): 11 stomps for a 32 px boss, 10 for Tex and the
Sumo. Unhit, Big Tex reaches the tap in 1200 frames (20 s), Leo in 880 (14.7 s), Duke (40 px, lurches only) in
about 1040 (17.3 s). Every boss is pinned at the left
by a player who lands one mug per (step / stomps per hit) frames: e.g. Leo needs one hit per 80 frames to hold his
ground, Big Tex one per 240.

Fight length (estimated, a competent player who also keeps the regulars served): Tex 40-50 s, Mascot 60 s,
Sasquatch 50-60 s, Critic 50-70 s, Yeti 60 s, Prototype 70 s, Duke 55-65 s, Sumo 60 s, Mothership 75 s (two phases), Leo 75 s.

Fair-empties check for every boss: his empties enter the same `next_arrival` schedule as the regulars', computed with
his empty speed, so two empties never arrive at the tap end closer than the level's `empty_gap` (80-120 frames),
whoever sent them. Hands make spamming cost something: a burst of throws leaves him holding empties he may not send
yet, and the next mug passes him and breaks.

### 3.3 Big Tex (Saloon)

Play: a giant cowboy stomps up the bar. Each sarsaparilla that reaches him knocks him back two hops. Eight and he is
satisfied. Regulars come on the other three bars as in the chapter's opening shift (slower spawns).

Rules: the common rules with the table's row. No special. Hands 3 (generous: the tutorial boss forgives a burst of
three throws). He starts on bar 1 (the second bar, so the topper overlaps a counter, which teaches the hat).

Entrance (E8, built 2026-10-15, a proposal for the owner to judge; src/boss_big_tex.c): "the swagger". On the fight's first start he
walks in from the left edge of the screen (spurs jingle: SFX_COIN every 16 frames), stops at his bar, bows and tips his hat (the
hat lifts 6 px; SFX_SERVE the cheer), 138 frames, then the 90-frame intro. Sprites from his own body tiles (no new art); input held.
Not built: riding in on a horse.

Why it is fun and fair: it teaches the boss rules (meter, push-back, hands, the tap) with no twist. Skill: keeping
the boss pinned while not neglecting three bars of regulars. Spam check: 3 quick throws are fine, the 4th passes him
(his pose shows three steins) and breaks: the lesson of the hands rule, early. Unwinnable states: none; unhit he
needs 20 s to reach the tap.

Hardware:

```
    01234567890123456789
 00 .999999..UUU@MMMMMMM
 01 ssssssssssssssssssss    saloon stage (bar cat animates)
 02 ssssssssssssssssssss
 03 ssssssssssssssssssss
 04 ssssssssssssssssssss
 05 wwwwwwwwwwppp.wwwwKK    bar 0: regulars (BG)
 06 wwwwwwwwwwppp.wwwwKK
 07 cccc^cccccccccccccKK    ^ Tex's hat crown: the topper (OBJ, OAM 26)
 08 wwTTTTTwwwwwwwwwwwKK    bar 1: Big Tex, BG 5x2 at boss_x 16 (cols 2-6); no regulars on this bar
 09 wwTTTTTwwwwwwwwBBwKK    B the Spigoteer (OBJ) at the tap
 10 cccccccccmccccBBccKK    m a full mug sliding to Tex
 11 wwwwwppp.wwwwwwwwwKK    bar 2 regulars
 12 wwwwwppp.wwwwwwwwwKK
 13 ccccccccccccccccccKK
 14 wwwwwwwwwwwwwwwwwwKK    bar 3 regulars
 15 wwwwwwwwwwwwwwwwwwKK
 16 ccccccccccccccccccKK
 17 ffffffffffffffffffff
```

- OAM: as in play; topper 26. Worst line 10 (3.1). BG ids: 5 poses x 10 tiles = 50 at most (walk A, stomp B, gulp,
  hit wince, happy), less where the lower row repeats (~42) + 4 HUD = 46 of 66. OBJ: topper 2 frames x 2 tiles = 4.
- CGB: BG 4 (hat brown, skin, shirt red; colour 0 wall), OBJ 7 (hat). DMG: hat and shirt dark, skin light, an
  outline of colour 3 against the wall.
- WRAM: the boss block only. ROM: boss.c common ~3 KB code; Tex data ~0.9 KB (tiles 46 x 16 B = 736 B + table).

Art: Big Tex body 40x16 in 5 poses (walk A, stomp B, gulp with a stein raised, wince, happy with a burp bubble);
stein-count variants of the upper row (0-3 steins: arms) are the poses' upper rows, ~8 extra tiles; hat crown 8x8
(2 frames: still, bob); HUD face icon 8x8; meter tiles (empty, half, full pip; shared by all bosses).

Plugs into: everything above is the boss engine; Tex has no special function. Test: tests/test_boss.py
`test_big_tex_*` (8 hits win, hands 3, tap costs a life and he restarts with his meter).

Story fit: Sadie's saloon has a regular too big for any stool; Tex is the piano mover who got the handle stuck in
her piano. Suggested PRE_SALOON page (SADIE): `WATCH FOR BIG` / `TEX. HE DRINKS` / `A WHOLE BARREL.`

### 3.4 The Mascot (Stadium)

Play: the team mascot (a big foam bulldog suit) bounces from bar to bar. He crouches, a landing marker appears on
another bar, he leaps, lands with a thud and scares that bar's fans off. You follow him.

Entrance (E8, built 2026-10-15, a proposal for the owner to judge; src/boss_mascot.c, art BALL in assets/art/boss/mascot.txt): "fired
from the T-shirt cannon". The landing marker shows on his spot, the cannon fires (SFX_WHOOSH) and he tumbles in from the top-left as a
spinning red ball, falls on the marker, bounces once, lands (thud) crouching and cheers (HAPPY pose, SFX_SERVE): 124 frames, then
the 90-frame intro. Input held. Not built: a cartwheel across the bar.

Rules: common row. Special every 300 frames of standing (5 s):
1. Tell 60 frames: crouch pose; a 2-tile dust marker appears on the target bar's wall at the landing columns
   (target = random other bar, landing x random of 16 / 32 / 48). The target bar stops spawning.
2. He leaps only when the tell has run **and** every full mug that was already on his bar when the tell began has
   reached him (at most ~44 frames more: a mug launched at x 136 reaches x 48 in 44 frames). Mugs thrown during the
   crouch are the player's risk: if he leaves first they slide to the left end and break.
3. Air time 20 frames: body erased (2 frames of a BG dust puff), topper hidden.
4. Landing: body stamped on the target bar with a thud; its regulars are scared off (no score, no penalty); his hands
   and meter go with him; a held empty is sent from the new bar when the schedule allows.

Why fun and fair: the skill is reading the tell and redirecting (bar switching is instant) while not throwing into a
bar he is leaving. The marker shows where, the crouch shows when. Changed from the pitch: he waits for mugs thrown
before his crouch, so no throw made in good faith is wasted; landing clears regulars because a BG boss cannot share
his columns with BG patrons (also funny: the fans scatter). Spam: throws into the crouch break; a stream on a bar he
has just landed on is fine. Luck: the target is random, but the 60-frame tell makes it fair.

Hardware: as Tex. Marker tiles 2 + dust puff 2 BG; poses walk A/B, gulp, crouch, happy = 5 x 8 = 40 + 4 HUD + 4 =
48 BG; topper = ears (2 frames) 4 OBJ tiles. No sprite in the air (an OBJ crossing other bars could make 11 on a
line). CGB BG 4: suit (team colour, white muzzle, dark outline); OBJ 7 ears. DMG: suit mid grey, muzzle white.

Art: Mascot body 32x16 x 5 poses (walk A, stomp B, gulp, crouch, cheer); ears 8x8 x 2; dust marker 16x8; puff
16x16 (2 frames, shared with the Prototype and the Mothership as their own looks); HUD icon.

Plugs into: boss engine + `mascot_special`; vars `boss_target_bar`, `boss_land_x`. Tests: tell length, waits for
pre-tell mugs (a mug launched 1 frame before the tell is caught), a mug launched during the tell breaks if it
arrives after the leap, landing scares regulars without score, spawning suppressed on his bar.

Story fit: Coach Blitz's team mascot is the one who found the spout at second base. PRE_STADIUM page (COACH):
`AND WATCH OUR` / `MASCOT. HE JUMPS` / `BARS FOR FUN.`

### 3.5 Sasquatch (Lumber lodge)

Play: the big hairy fella. He downs a coffee instantly and sends the empty back twice as fast as anyone else.

Rules: common row; gulp 8 frames (the "instant" drink), sip 0: the empty goes as soon as the fair schedule allows,
at 1.0 px/f (`empty_fast` bit of his bar). Hands 2: holding two, the third coffee passes him and breaks. His own
`empty_gap` is 80 frames, the game's floor (the lodge level's 108 would make him mostly a holder); regulars' empties
still keep the level's gap from his.

Gone to the woods (built, E2; owner: "he goes invisible for a bit and shows up in another row"): every 360 frames of
walking he ducks behind the counter (DUCK pose, only crest, brow and eyes show; he stands, still drinks a coffee that
reaches him; at least 36 frames), then waits until no full mug is in his last 8 px of approach and no empty is sliding
back on his bar (at most 150 more frames: nothing is lost to his leaving). He vanishes (BS_JUMP + BP_HIDE: no catch,
no empty, no topper) for 66 frames; the target bar (any other, x 16/32/48) shows his blinking FOOTPRINTS (the landing
marker slot) from the first frame, and the regulars are steered off both bars. He pops up there (BURST2, 14 frames, the
thud; regulars on that bar scared off with no penalty), meter and held empties with him. A mug thrown at his empty bar
while he is away breaks at its left end (a life): the bar is visibly bare. A lost life puts him home (bar 2, x 16).
So the player must read the footprints and carry the bartender to the new row, not just pour faster.
Entrance (BEV_INTRO, BG only; fires on the fight's first start like Duke's; `sasq.ent = 1` starts it for a later
arrival): three thuds, a fist through the back wall (BURST1), him roaring out in splinters (BURST2), WALK at x 16, 60
frames, the intro's 90 frames after; the bartender is held at bar 0 meanwhile. Rejected idea: swinging in on a rafter
vine (a sprite pool like Duke's bike; too much OAM). Poses 8 (5 + DUCK, BURST1, BURST2), column pairs 29 of 30.

Why fun and fair: Tapper's core skill (catch the empty you caused) at speed. From x 48 a fast empty takes 88 frames
to the tap: visible, catchable after an instant bar switch. The hands rule plus the fast empty means the best
rhythm is throw, switch away, come back for the empty: a real juggling pattern. Readable: his empties move visibly
faster; the pose shows steins held. Spam: two quick throws are fine, the third breaks.

Hardware: as Tex. Poses walk A/B, gulp, hold-1, hold-2 (upper row only), happy: ~40 BG + 4 HUD. Topper: the head
crest (2 frames). CGB BG 4 brown fur / tan face; DMG mid / light.

Art: Sasquatch body 32x16 (walk A, stomp B, gulp, upper-row variants holding 1 and 2 mugs, happy wave); crest 8x8
x 2; icon. The lodge show's Sasquatch dancer is a 16x24 OBJ; the boss is a new, bigger drawing in the same style.

Plugs into: boss engine with `empty_fast` mask. Tests: empty speed 1.0 on his bar only, hands-full pass-through,
schedule respected with a regular's empty due at the same time.

Story fit: June: "no such thing". He is just thirsty. POST_LUMBER narrator page: `THE SASQUATCH` /
`DRANK 12 COFFEES` / `IN 12 SECONDS.`

### 3.6 The Food Critic (Bistro)

Play: a monocled critic with a notebook. He only accepts a perfect pour; a sloppy glass is tasted and sent back.

New pour rule (only in this fight): after the mug is full (fill_timer 16) the bartender has a 12-frame window:
released at fill frames 16-27 the drink is PERFECT (the fill sprite shows a sparkle frame from 16 to 27); held to
28 or more it over-pours (the fill sprite shows foam running over the rim from 28). Regulars accept both. The
quality bit travels with the mug (a spare high bit of `mug_bar`, or a 20-byte `mug_q[]` if no bit is free).

Rules: a PERFECT drink: meter -1, push 16, gulp 60 (savouring, notebook pose). A SLOPPY drink: no meter change, he
tastes it (30 frames, frown pose) and sends it back as a `MUG_RETURN` (the full drink sliding right at 1 px/f),
which the player must catch like an empty (missing it costs a life at the right end). Hands 1: while he holds a
glass or tastes, any arriving drink is waved straight back as a `MUG_RETURN` instead of breaking behind him
(changed from the default so a busy critic never causes an unseen break).

Why fun and fair: a timing skill layered on the usual juggling; the window is 200 ms and shown on the mug itself,
and the punishment (one more thing to catch) is mild and visible. Carrying a full mug to another bar takes longer
than the window: carried drinks are sloppy, a choice the player can see. Flagged: it changes how pouring feels;
playtest the window (12 frames is the proposal; 16 if it frustrates). Spam: spammed pours are mostly sloppy and
come back.

Hardware: as Tex, plus 2 extra fill frames (sparkle, overflow) = 2 OBJ 8x16 = 4 tiles in 96-127 (the show slot;
the topper takes 4 more). Returned drinks reuse the full-drink tiles (OBJ 1 palette). BG poses: walk A/B, savour,
taste-frown, happy = 40 + 4 HUD. Topper: beret (with monocle glint frame). CGB BG 4 black jacket / white shirt /
skin; DMG fine (high contrast).

Art: critic body 32x16 x 5 poses; beret 8x8 x 2; mug sparkle frame and overflow frame per venue drink? Only the
bistro's wine glass is needed (8x16 each). Icon.

Plugs into: main.c keeps counting `fill_timer` past 16 (cap 255) and stores the quality at launch; mugs.c
`MUG_RETURN`; boss.c `critic_catch`. Tests: release at 16, 27 -> perfect; 28 -> sloppy; sloppy returns at 1 px/f
and is caught by the bartender; a return reaching x 152 costs a life; hands-1 wave-back; regulars accept both.

Story fit: Colby's dinner rush has a famous critic in it. PRE_BISTRO page (COLBY): `TONIGHT A FOOD` /
`CRITIC VISITS.` / `POUR PERFECTLY!`

**As built, readable states and entrance (2026-10-15, owner playtest: "hard to tell what status he was in")**: his rule is unchanged
(a drink reaching him while he holds a glass, tastes, or has returns waiting is waved back, perfect or not), but each state now has its
own look: FREE = WALK / STOMP (a smile, the open palm out over a checked napkin); SAVOURING = GULP; HOLDING his empty = the HOLD /
HOLDHOP poses (eye shut, the empty glass in hand); TASTING / sending back = TASTE. A drink waved back shows TASTE for 24 frames and a
speech bubble beside him ("NO!" for a perfect drink that came too soon, "BAD" for a sloppy one; a sloppy one he tastes shows "BAD"
too); the banner window is not used (it covers his bar). Wine's perfect moment: the sparkle frame is redrawn (glowing bowl, glints) and
SFX_COIN dings as the 12-frame window opens (only in his fight). Entrance on the fight's first start: a silver cloche slides along his
counter, a bell dings, the lid flies off and he is there (BEV_LOAD / BEV_INTRO / BEV_DRAW like Duke's; src/boss_critic.c).

### 3.7 The Yeti (Igloo)

Play: a shaggy, friendly Yeti. Every few seconds he takes a big breath and blows: his whole bar ices over and every
mug on it slides twice as fast for three seconds.

Rules: common row. Special every 360 frames:
1. Tell 50 frames: inhale pose (cheeks puffed); frost creeps along his bar's counter from his side (the counter
   row's tiles swap to icy ones, 4 columns per 12 frames, through the VBlank queue).
2. ICY 180 frames: on his bar full mugs move 3 px/f (`mug_fast`), empties 1 px/f (`empty_fast`); he does not
   advance. If he holds an empty he sends it at the start of ICY if the schedule allows.
3. Thaw: the counter tiles swap back (18 columns, 2 frames).

As built (E4, owner 2026-10-15 "I don't see how the icy bar is a help or a hindrance"): the ice's trade-off is the
FROZEN TAP. While his bar is icy (ICY phase) the tap on HIS bar is frozen: pressing A at it starts a fill that is
cancelled the same frame (a thud), so no mug can be launched at him for the 180 frames; the other bars pour as ever, and
the tell still pours. The blow adds a whoosh and the banner "TAP FROZEN" for 40 frames. Help: he stands still (no stomp),
a mug already on his bar rides the ice at 3 px/f and lands sooner, the bartender gets a breather to serve the regulars.
Hindrance: nothing can be poured at him, and his empties come back at 1 px/f to a bartender who must be at his tap. The
player's choice each breath: one last mug before the frost, or go serve the other bars and be back for the empties.
Rejected: a slippery bartender floor (needs ROM0 and punishes the other bars), mugs overshooting him (a life lost for a
speed the player could not judge; mugs.c shared with Leo and the Critic).

Entrance (E4, the FROST FRONT; no new art, no sprites, YP_ENTER, BEV_LOAD / BEV_INTRO as Duke's): the wall is bare
(BS_JUMP, BP_HIDE) while the counter frosts over left to right in 30 frames with a whoosh and the sparkles; at frame 40 he
steps out of the frost in the BLOW pose (a thud); at 70 the frost thaws; at 72 he walks (intro_timer is held until then, the
first breath is 360 frames after). Not built: the SNOW BURST (sprite puffs bursting out of the wall; needs OBJ tiles
borrowed over the topper's and Duke's reload dance).

Why fun and fair: risk and reward in one window. On ice your drinks reach him faster (more hits), but his empties
come back fast too. The frost creeping along the counter is a clear, slow tell, readable on DMG by pattern (ice
streaks), not only colour. Changed from the pitch: "speeds up mugs" applies to both directions, which makes the
icy window something you want to use rather than only survive. Fair: a 1 px/f empty from x 48 still needs 88
frames.

Hardware: as Tex, plus the icy counter: the igloo counter row uses N distinct tiles (2-3); icy copies of each = 3
BG ids. Poses walk A/B, gulp, inhale, blow, happy (6 x 8 = 48) + 4 HUD + 3 ice = 55 of 66. Topper: horns.
CGB BG 4 white fur / ice-blue face / dark; the icy counter keeps the bar palette 0 (white streaks are colour 1 of
the igloo bar). DMG: icy = light streak pattern.

Art: Yeti body 32x16 x 6 poses; horns 8x8 x 2; icy versions of the igloo counter tiles; icon.

Plugs into: boss engine + `yeti_special`, `mug_fast` / `empty_fast` masks, a counter-row writer (vq_add of 18
tiles). Vars `boss_icy` (frames left). Tests: speeds on his bar only and only while icy; counter tiles icy then
restored; tell length; empties scheduled correctly at 1 px/f.

Story fit: Aurora's guests came in from the cold; one of them is very big and very fluffy. PRE_IGLOO page (AURORA):
`OUR YETI IS A` / `DEAR. BUT HIS` / `BREATH IS ICY.`

### 3.8 The Prototype (Robot factory)

Play: Manager-Bot's experimental robot, a big walking charging cabinet. A lamp on its antenna cycles green, yellow,
red. Green: it takes batteries. Red: its bar's conveyor runs backwards and sends everything on it back to you. After
each red it rides the conveyor to another bar.

Entrance (E8, built 2026-10-15, a proposal for the owner to judge; src/boss_prototype.c, art CHAIN / HOOK / SPARK1 / SPARK2 in
assets/art/boss/prototype.txt): "lowered by the crane, then powers up". The overhead crane lowers him by his lamp onto his bar (clunk),
lets go and rises away; the lamp is the red X, blinks to yellow (SFX_COIN) with sparks flying, and lights solid green (SFX_EXTRA):
124 frames, then the 90-frame intro. His body is sprites made from his own body tiles; on CGB it wears the yellow lamp's OBJ
palette until the BG body takes over (all 8 OBJ palettes are in use in his fight). Input held. Not built: assembling from parts
on the conveyor.

Rules: common row. Cycle: GREEN 240 frames (normal), YELLOW 60 (tell; still accepts), RED 150:
- at RED start every full battery on its bar becomes a `MUG_RETURN` moving right at 1 px/f; a full battery that
  reaches it during RED bounces back the same way;
- the counter's conveyor chevrons on its bar point right and animate (BG tile rewrite, 1 tile every 6 frames);
- the last 60 frames of RED show a landing marker on the next bar (as the Mascot's); at the end of RED it moves
  there (vanish 10 frames, appear) and scares that bar's regulars off; GREEN again.
- At RED start the fair-empties schedule is pushed past the returning batteries' arrivals plus `empty_gap`, so no
  regular's empty is due at the same moment.

Why fun and fair: the skill is leading your throws against a cycle: a battery needs up to 44 frames to reach it, so
throws must stop during YELLOW (60 frames > 44: a throw at the start of yellow still lands). Returned batteries are
spaced at least 32 px apart (fill time), so they arrive >= 32 frames apart and standing at the tap catches them all.
Changed from the pitch: "switches bars, conveyor runs backwards" is now one readable cycle with a yellow warning
instead of two independent surprises. DMG readability: the lamp's shape changes (solid / blinking / X), the chest
screen shows an arrow (accept) or an X (reject), and the chevrons point the way mugs move.

Hardware: as Tex. BG: poses walk A/B, gulp, green screen, red screen (upper row only), happy = ~44 + conveyor
chevrons 2 directions x 2 frames = 4 + marker 2 + HUD 4 = 54. Topper: antenna lamp; CGB OBJ 7 rewritten per phase in
VBlank (green / yellow / red; a `boss_pal_req` like `pal5_req`); DMG: lamp shapes, 3 frames = 6 OBJ tiles.

Art: Prototype body 32x16 (cabinet on treads, screen face) x 5 poses + 2 screen icons; antenna lamp 8x8 x 3
(solid, ring, X); conveyor counter tiles with chevrons (left / right, 2 animation frames each, matching the factory
counter); marker; icon.

Plugs into: boss engine, `MUG_RETURN`, counter-row writer, the fair-empties push. Vars `boss_light` (0 green, 1
yellow, 2 red). Tests: a battery launched at yellow's first frame is caught; at red every full on its bar turns
round; returned batteries arrive >= 32 frames apart; a regular's empty is not scheduled inside the return window;
bar switch after red with marker 60 frames before.

Story fit: Manager-Bot's newest model needs a full charge before its debut. PRE_ROBOT page (MANAGER-BOT):
`WARNING: THE` / `PROTOTYPE. GREEN:` / `FEED IT. RED: NO.`

### 3.9 Sumo Champion (Teahouse)

*Rebuilt 2026-10-15 as a pushing match (src/boss_sumo.c, tests/test_boss_sumo.py; owner: "the sumo fight feels pretty plain ... maybe there are no drink limits? He has to be pushed out of the bar to lose and he only gets knocked back a little after the drink meter completes, then it resets minus 1, until he is knocked back with every throw"). The first design (single hits do not push, a chain of hits pushes 8 px, meter 8) is gone.*

Play: the grand champion shuffles toward the tap on the drum beat, and there is no stopping him with a few cups: he drinks
everything you send. Every cup fills a pint on the HUD; when the meter is full the crowd roars and he is shoved back
along the bar, a big stagger. The meter then starts over one pint shorter (6, 5, 4, 3, 2, 1), until at one pint every cup
knocks him back. Shove him out of the bar's left end (a ring-out) and you win; let him reach the tap and you lose a life.
Now and then he stamps for a charge; a cup during the stamp calls the charge off.

Rules: width 40; he starts at x 24 (three cells from the wall, 72 px from the tap); he steps 8 px on every second bar
of the teahouse tune (192 frames; music_frames, his own clock with the music off; Practice's HARD 144). No drink limit and
no hands rule (boss_cap 250): every cup that reaches him is drunk, no gulp; his empties come back one per sip (90 frames)
through the fair-empties schedule as for every boss. boss_hp = the cups still to fill this meter (>= 1), `cyc` its length
(6 down to 1). The full meter blinks (24 frames), then he is knocked back 32 px in four hops (WINCE), dazed (no steps) for
44 frames in all, the charge timer starts over. Ring-out: the hop that takes him to x 0 starts a 24-frame stagger at the wall
(WINCE, drum), then boss_hp 0: the engine's outro with him GONE (BP_HIDE, no topper), not happy. Charge: every 480 walking frames,
a 60-frame stamp (SHIKO, he stands; any cup calls it off: HMPH), then 16 px in 8 frames (was 24). A knock-back also ends it.

HUD: the meter's pints fill left to right; its length is the target. Odd targets end in a one-pip tile (BG 246 / 247, built at
load from the engine's EMPTY / HALF pint: the left pip as drawn, the right half the band's colour).

Tuning (model: steady cups with +-30 % jitter, the charge cancelled by a cup in its stamp; numbers per cup interval, frames):
interval 70 / 90 / 110 / 130 / 150 / 180: wins 100 / 100 / 100 / 97 / 51 / 5 %, in 11 / 13 / 18 / 20 / 21 / 22 cups
(about 13 / 20 / 33 / 43 / 53 s). A cup every 6 seconds loses to the tap; one every 1.2 to 1.8 s wins in 13-18 cups. The
real-pour bot of the tests (a cup at the quickest every 60 / 100 frames) rings him out in 11 cups / 12.7 s and 18 cups / 32.1 s.

ENTRANCE, "the ring ritual" (BEV_LOAD arms it for the first start; BEV_INTRO runs 148 frames with the intro held, the player held
as in Duke's; BEV_DRAW draws two sprites, OAM 26 / 27): the bar empty; at frame 20 he walks in from the left wall in three heavy steps
(x 0 to 24); at 68 he lifts a leg (SHIKO) and throws salt (two grains of OBJ_DUST's scatter tile arcing over the counter); at 88
the first stamp (STOMP, the picture shakes 2 px for 6 frames, dust at both feet, drum DON); at 104 the other leg; at 120 the second,
harder stamp (3 px for 10 frames, DON + KA); at 136 a bow; at 148 the ritual is over and the intro's 30 last frames run. No new art
(the salt and dust are the dust puff's frames) and no new sound effects (SFX_DON, SFX_KA, SFX_SHAKE).
Not built: the noren-curtain entrance (he rises from a kneel behind the cloth and claps twice).

Hardware: as Tex; 40 px body. Poses WALK, STOMP, GULP (the hit), WINCE (the knock-back and the wall), HAPPY, SHIKO, HMPH.
Topper: topknot. CGB BG 4 skin / mawashi dark blue / outline. DMG: skin light, belt dark.

Plugs into: boss engine; the beat comes from music.c's music_frames (the pause menu freezes the tune, so it freezes him:
tests/test_pause.py). State: sumo_t in BOSS_OWN (test hooks sumo.phase, cyc, cycles, knock, out, ent, cancels, charges);
the HUD row is staged in story_scratch + 300 (Duke's entrance staging area; no WRAM).

Story fit: the teahouse's guest of honour. PRE_TEAHOUSE page (HANA): `THE CHAMPION` / `IS THIRSTY. KEEP` /
`THE TEA FLOWING.` (unchanged); the banner's lines are THE CHAMPION / PUSH HIM OUT.

### 3.10 The Mothership (Space lounge)

*Built 2026-10-12 (src/boss_mothership.c; changes for the engine in PLAN.md "Mothership as built": the split reloads variant C's tiles with the LCD off for a frame, the minis come in at x 24 and the saucer stays hidden on the bar without a mini).*

Play: a thirsty flying saucer hovers at a bar, beaming beakers aboard. It teleports between bars. Fill it and it
splits into three small aliens who run for the tap; each wants two beakers.

Rules, phase 1: common row, meter 6. Teleport every 300 frames: tell 60 frames (a beam column of BG tiles on the
target bar's wall), waits for pre-tell beakers as the Mascot does, vanishes 10 frames, appears. Phase 2 (meter 0):
a 40-frame flash pose, the saucer's tiles are erased and three mini aliens (patron variant C of the alien group,
which only the minis use) are added at x 16 on three different bars (its bar first). Minis are ordinary patrons
with `patron_hurry` set (1.5x the level's speed), push-back 16 per catch, and served out after their second drink
wherever they stand (a "mini" flag, checked where a drink ends). The HUD meter shows the 6 drinks left. All three
served: win. A mini reaching the tap costs a life like any patron; after the reset the remaining minis come back
in at x 16.

Why fun and fair: two different phases in one fight; phase 2 is classic Tapper with three fast patrons, a good
penultimate test (PROPOSAL, space last: it is now the last boss and the final test of the tour, with phase 1's meter
raised from 6 to 8 so its 14 drinks are the most of any boss; Leo, now 9th, drops from 14 to 12). Changed from the pitch: it splits once at the end of phase 1, not on every hit (splitting every
hit would put up to 18 extra patrons on screen and blow the lift and line budgets). Regulars keep coming in phase 2
at half the rate.

Hardware: the tight one. Variant C stays loaded (the minis), so only the back views (222-233), 234-239 and 252-255
are free: 22 ids + id 77 = 23. Body: hover (8), hit (8), the beam column (2 tiles: top, bottom), HUD icon + 3 meter
tiles (4) = 22 of 23. No second hover pose: the topper (the dome) animates instead (OBJ, 3 frames, lights
chasing). Regulars use variants A and B as in every boss fight; C is reserved for the minis.
CGB BG 4 saucer silver / glow green / dark; OBJ 7 dome. Both slots belong to variant C in normal play, so at the
split (the saucer and dome are gone by then) boss.c writes alien C's BG 4 and OBJ 7 palettes back in the next VBlank,
before the minis are drawn. DMG: saucer light with a dark rim; minis are the regular alien C art (readable as
patrons). Minis can be lifted like any patron (lift budgets unchanged).

**E7 additions (owner 2026-10-15: "the mothership gimmick isn't very threatening"), phase 1 only; the header of src/boss_mothership.c has the detail.**
- Passengers: every landing releases two alien passengers (ordinary variant A / B patrons) at x 24 on the two least busy bars that are not his
  (a crowded entry is skipped; none while 12 patrons are live). Served like any patron (CLEAR THE BAR counts them); the split clears them.
- Stun ray: the bartender on one bar 270 frames (4.5 s; reset by any bar change and each landing): a 60-frame charge (HAPPY pose, antenna
  blinking, SFX_REV, the beam column blinking on HIS bar under his feet, faster in the second half), then, if he is still on that bar, the beam
  fires (GULP pose, SFX_KA) and he is stunned 90 frames (BT_FAIL: no walking, bar change or pouring; mugs keep sliding). Any bar change in the
  charge dodges it. The teleport clock waits through the ray. Phase 2 (the minis) has no ray; the split is kept as the climax.
- Entrance (first start, BEV_LOAD / BEV_INTRO as Duke's): the beam column lights on his bar, the room lights flicker (CGB the bar palette halves,
  DMG BGP), a hum, then he blinks in as the beam fades and lands (64 frames), then the intro's 90.

Art: saucer body 32x16 x 2 poses (hover, hit flash); dome 8x8 x 3 (lights); beam column 8x16 (2 tiles); icon.
The minis are the existing alien C patron.

Plugs into: boss engine + `mothership_special` + `add_patron` for the minis + a `patron_mini` bit (or reuse
`patron_hurry` bit 1). Vars `boss_phase2`, `boss_minis` (bit per mini alive). Tests: split at meter 0, minis
hurried, served after 2 drinks, life lost re-adds the remaining minis, BG ids within 23.

Story fit: Zizz's mothership is parked behind the lounge and is very thirsty after the long bus ride. PRE_SPACE page
(ZIZZ): `MY MOTHERSHIP IS` / `PARCHED. IT SPLITS` / `WHEN IT IS FULL.`

### 3.11 Leo the Lion (Jungle zoo)

Play: Leo, wearing the golden crown, pads toward the tap. He roars now and then, and the roar is a wind: it blows every
full mug sliding on any bar back toward the bartender (E6, owner 2026-10-15: "the lion's roar doesn't seem to do anything").

Rules: common row, meter 14. Roar every 420 frames:
1. Tell 60 frames: inhale pose (mane puffs out), two "!" BG tiles beside his head on his bar's wall. This is the player's
   second to stop throwing and park the bartender at the tap (a mug thrown as the tell begins reaches Leo in about 40
   frames, before the roar).
2. Roar 30 frames (roar pose, SFX_SHAKE): every regular walker on every bar is pushed back 16 px (the push-back
   movement, no serve), and a shockwave starts at his right edge and sweeps right along all four bars at 5 px a frame
   (about 27 frames to the tap end): gold arcs, one a bar (a thinner trailing one joins while fewer than 4 mugs are alive),
   OAM 29-36. Every FULL mug the front passes (on any bar, one thrown while the front is at the spout too) becomes a
   MUG_RETURN (the Critic's sent-back drink: 1 px a frame to the right): the bartender catches it at that bar's tap end
   like an empty (EMPTY_SCORE, nothing for Leo's meter), or it goes past the tap end and breaks (a life). He does not
   advance during tell and roar. Nothing else changed: no empties are hurried, his own held empty keeps its schedule.
3. The "!" tiles go.

Why fun and fair: it punishes spamming mugs (every mug in flight on any bar comes back at you, and the ones on the bars the
bartender is not on must be run down in time, 30-90 frames of travel) but costs nothing for waiting: Leo stands still through
the 90 frames of tell and roar, so stopping to catch is a clean answer. Rejected: stunning the bartender (a state the player
cannot read), knocking the glass from his hand (invisible), the old "drinkers send early" (a wave of empties on top of blown
mugs was unfair, and nobody saw it). A screen shake was left out: the play screen never scrolls and a scroll left set by a
pause-and-quit would shift the title.

ENTRANCE (E6, on the fight's first start like Duke's, BEV_INTRO): a flaming circus hoop appears over the left end of his bar
(8 frames), Leo flies in from off the left edge in a 28-frame arc through it (his ROAR pose as sprites, 30 px up at the top),
lands on his bar at x 16 (36 frames in), roars with the wave as a picture only, and the hoop is gone; the clock to the first
roar starts 30 frames later. The bartender is held at bar 0's tap and nothing is poured while it plays. Not built: prowling
in from the left and roaring at the screen.

Hardware: as Tex. Poses walk A/B, gulp, inhale, roar, purr = 6 x 8 = 48 + "!" 2 + HUD 4 = 54. Topper: the golden
crown (OBJ 7: gold; it is the piece the story is about, so it is the one topper that must look good). DMG: crown
light with dark outline over a mid-grey mane.

Art: Leo body 32x16 x 6 poses (respecting the owner's lion notes: a mane framing the whole head, ears, a cat
muzzle, no bald-man look); crown 8x8 x 2 (glint); "!" 8x8; icon. E6: the wave's two arcs (8x16) and the hoop (16x32, two
flames) in assets/art/leo_fx.txt (tools/gen_leo_fx.py -> build/leo_fx_art.h: 10 tile pairs at OBJ 104-123, Leo's colours;
the leap is his ROAR pose drawn as sprites). PROPOSAL pending the owner's eye.

Plugs into: boss engine, src/boss_leo.c only (no engine change). Its state is the struct leo_t in BOSS_OWN. Tests
(tests/test_boss_leo.py): walkers pushed 16 px without score, the blast on every bar, a blown mug caught or broken, the
tell's timing and time to react, the arcs' drawing, the entrance, <= 10 sprites a line on every frame.

Story fit: PRE_ZOO already puts the crown on Leo. PRE_ZOO page (KIKI): `LEO WANTS A` / `DRINK FIRST. HE` /
`ROARS. STAY CALM.` POST_ZOO's "the lion approaches... and purrs" is his defeat outro (the purr pose).

### 3.12 Duke (The Chrome Cow, chapter 7)

APPROVED and BUILT 2026-10-12 with one owner change: he stands behind the bar like Big Tex, with NO bike in the fight (the
bike is for his entrance, not built); the bike behaviours became a throttle-twist tell (REV) and a standing lurch (see PLAN.md
"Duke as built"). The text below is the original proposal. Numbered last so the references to 3.1-3.11 stay; in chapter order he
is the seventh boss.

Play: Duke, the gang leader, rolls in on his motorcycle with his gang and orders "the biggest milkshake in town".
Every full glass of milk that reaches him tops up his shake and pushes him back. Between serves he sits there
revving, then the bike lurches forward, far faster than any patron walks. His helmet is the topper.

Rules: the common rules with the 3.2 row; his movement replaces the steady stomp:
1. **Idle**: after his last catch, his last lurch or his entry he idles I frames: I = 150 while his meter is 12-9,
   120 at 8-5 and 90 at 4-1 (the shake is nearly full and he gets impatient). The idle pose shakes with the engine
   (2 poses, 8 frames each).
2. **Rev** (the tell, 50 frames): rev pose (leaning over the handlebars), exhaust puffs animating on the BG behind
   the bike (2 tiles), the helmet topper shaking 1 px every 4 frames (its OAM y only), SFX rev on channel 4.
3. **Lurch**: 16 px in 8 frames (two 8 px hops, one per 4 frames: 2 px/f, about 17 times a chapter-7 walker's
   ~0.12 px/f), then idle again from 0.
- A catch: meter -1, push 16 px (two hops, one per 4 frames, the common rule), gulp 20 frames, and the idle clock
  starts again from 0. A catch **during the rev stalls him**: the lurch is off, a 20-frame stall pose with a puff of
  black smoke (2 BG tiles), then idle from 0. A steady stream of glasses keeps him from ever lurching, and a rev has
  one clear answer: land a glass now.
- Hands 2, sip 45, his empty speed 0.5, meter 12. The HUD meter is his shake filling up (the shared pip tiles; the
  boss icon is a shake glass).
- The tap: as every boss, his right edge reaching 136 costs a life; after the pause he rolls in again at x 16, meter
  kept. His entry: a 30-frame skid pose with a dust puff at x 16 (the puff tiles shared with the Mascot).
- His gang: the regulars on the three free bars are the venue's punks, arriving in the venue's Last call "chord"
  pattern (three bars at once, then a breather) at the boss fight's 1.5x interval; the chord's bars are the three
  free ones. No mosh pit in the boss fight (section 9.4: bosses play by the same rules everywhere).

Numbers: unhit, he first lurches at frame 200 (150 + 50), then every 208 frames (150 idle + 50 rev + 8 lurch); from
his right edge at 56 to the tap at 136 is 80 px, 5 lurches: the fifth ends at frame 1040 (17.3 s; his 30-frame entry
not counted), between Tex (20 s) and Leo (14.7 s). One glass every 200 frames or sooner pins him (no lurch at
all) and pushes him 16 px each time, so the
pressure in the fight comes from the gang's chords on the other bars, with Duke as the clock you must keep feeding.
At meter 4-1 that window shrinks to 140 frames.

Why fun and fair: the owner's "between serves he revs" becomes a rhythm rule with a readable answer. Keep the glasses
coming and he never lurches; let him rev and you have 50 frames to land one: a glass from the spout reaches his
right edge at x 56 in 40 frames ((136 - 56) / 2), so a throw on the rev's first frame always lands in time unless his
hands are full. Readable on DMG by shape (the lean, exhaust puffs, the helmet shake), never only by sound. Spam: hands
2, the third glass of a burst passes him and breaks, and with full hands a glass during the rev cannot stall him
(it breaks behind him), so spamming early costs the counter-play later. Lurches are always 16 px and always after a
50-frame rev: no lurch is ever a surprise. Changed from the pitch: "lurches forward faster than a normal patron" is
the lurch's speed (2 px/f); his average advance stays in the range of the other bosses so the fight stays fair.

Hardware: as Tex (3.3), with a 40x16 body (rider on his bike, 5 tiles wide; the counter hides the wheels).
- BG ids: rider rows (upper) idle A, idle B, rev, gulp, hold-1, hold-2, stall, happy = 8 x 5 = 40; bike rows (lower)
  still, rev (exhaust pipe glowing), lurch (speed lines) = 3 x 5 = 15; exhaust puff 2, black smoke 2, HUD shake icon
  + meter tiles 4: 63 of 66.
- OBJ: the helmet topper, OAM 26, 8x16 (upper 8 rows the helmet dome, lower 8 transparent), 2 frames (still, visor up
  for the defeat outro) = 4 tiles in 96-127. The rev shake moves its OAM y; no extra frame. Puffs and smoke are BG,
  so the worst line stays 10 (section 3.1, unchanged), and the topper hides on frames where the bar above holds 6
  mug entries or more, as every topper.
- CGB: BG 4 leather black, chrome grey, skin (colour 0 the wall); OBJ 7 the helmet (red with a white stripe). DMG:
  leather dark, chrome light, the helmet light with a dark outline under OBP1 0xE4.
- WRAM: the boss block plus `boss_idle` (frames, 16 bit) and `boss_rev` (frames into the rev, 0 none): 3 B. ROM ~1.2 KB
  code + ~1.1 KB tiles (67 x 16 B).

Art (proposals first): Duke on his bike 40x16: big beard, sleeveless leather vest with a cow patch on the back, a
"MOM" heart on his arm (tough talk, sweet heart, like Granny); 8 rider poses, 3 bike poses as above; helmet 8x8 x 2;
exhaust puff 8x8 x 2; black smoke 8x8 x 2; the shake-glass HUD icon. The defeat outro: visor up, a milk mustache, a
polite thumbs up to Granny.

Plugs into: the boss engine with `step` 0 meaning "no stomp" (one test in boss.c's walk) and `duke_special` for the
idle / rev / lurch cycle; `boss_catch` restarts the idle and stalls a rev; the arrival pattern for the regulars
(`pat_len` / `pat_bar`, as story shifts set it). Vars `boss_idle`, `boss_rev`. Tests (tests/test_boss.py
`test_duke_*`): idle length per meter band (150 / 120 / 90); a 50-frame rev, then exactly 16 px in 8 frames; a catch
during the rev stalls him (no movement for 20 frames, then idle from 0); a catch restarts the idle; glasses every
190 frames never let him lurch; unhit he reaches the tap at frame 1040 +- 8, costs a life and restarts at x 16 with
the meter kept; with full hands a glass during the rev passes him and breaks (no stall); the regulars arrive in
chords on the three free bars; no mosh-pit shove in the fight (`mosh_on` 0); <= 10 objects on every line every
frame (the test_perf helper).

Story fit: suggested PRE_BIKER page (GRANNY): `DUKE'S GANG RIDES` / `IN TONIGHT. HE` / `WANTS A BIG SHAKE.`

## 4. Mini-games

Sketch legend used below: `9` score digits, `H` other HUD glyphs, `s` venue stage (with its animation), `w` wall,
`c` counter, `f` floor, `K` keg, `P` the Spigoteer (OBJ 16x24), `t` banner text (rows 2-3 during the intro).
Lower-case letters are BG, upper-case are sprites unless the note says otherwise. Every screen is 20x18 tiles.

### 4.1 Quick Draw (Saloon)

As built (2026-10-11, src/qd.c; PLAN.md "Quick Draw and BONUS > MINI GAMES as built"): the rules and numbers below,
on the owner-approved art (assets/art/quickdraw/). Where the build follows the approved mock-up instead of this
section: the pips sit on row 12 (the Kid's left, the player's right), not on the HUD row; the badge is a light letter
in a dark disc. A press during the first 60 frames (QS_READY) is ignored (the foul rule starts with the wait). Sounds reuse existing SFX (bell
SFX_CATCH, pop SFX_SERVE, foul SFX_BREAK, too slow SFX_LIFE, tumbleweed SFX_SHAKE, caw SFX_LAUNCH).
The soda duel (owner-approved 2026-10-11) replaces the cork pop and the fumble: both shake their bottles through the
banner and freeze at DRAW!; the winner sprays a stream of soda (BG tiles on the wall's row) across the gap and the
loser gets soaked (splash, then drips) without dropping anything; a foul fizzes over the player's own bottle. PLAN.md
has the details.
The badge (owner 2026-10-11): A is a light letter in a dark disc; B is a cream letter in a blue disc on CGB (BG
palette 3) and a dark letter in a light disc on DMG, so the two never look alike. The fumble poses are gone.

Play: the Sarsaparilla Kid challenges the new bartender. Both stand with a bottle in the holster. A big DRAW! sign
flips up with a bell; whoever pops the cork first wins the round. First to three.

Rules and numbers:
- Round: the banner "ROUND n" / "WAIT FOR THE SIGN" (nothing reads as a countdown, so nobody presses early) for 60 frames and on through a wait W = 90 + rand(0..210) frames (1.5-5 s), then DRAW!.
- The DRAW! sign carries a button badge. Rounds 1-2: always A. Rounds 3-5: A or B (random). The player must press
  the shown button (a fresh press; A held through the sign does not count).
- The Kid draws R frames after DRAW!: rounds 1-5 R = 34, 30, 30, 28, 26 (566 ms down to 433 ms; rounds 3-5 are a
  two-way choice, which costs a human ~100 ms more than a simple reaction).
- Player presses the right button at t <= R frames after DRAW!: the round is his (a tie at t == R is his). No press
  by R: the Kid's. Any press before DRAW!, or the wrong button after it: FOUL, the Kid's round.
- Feints from round 3: once during the wait (never in the last 30 frames before DRAW!) a tumbleweed rolls across
  the floor or a crow lands on the sign (sprites, with their own sound). They look nothing like the sign flipping.
- After each round: both poses (winner pops the cork, loser fumbles), "YOU 0.32" or "FOUL" for 60 frames ('.' from
  the story font tiles).
- Score: 500 per round won + (R - t) x 20 speed bonus; match won +2000. Medal: GOLD 3-0, SILVER won 3-1 / 3-2,
  BRONZE lost with >= 1 round, else none.
- Length: a round ~345 frames (60 + 195 average wait + ~30 + 60): 3-5 rounds + walk-in and outro = 25-35 s.
- Ramp: R falls and the A/B choice and feints arrive in round 3; one setting for story and practice.

Why fun and fair: reaction and reading with a clear, loud cue. Mashing loses (any early press is a foul). The random
wait is not luck: the outcome is the reaction. Ties go to the player. The badge letter is 16x16, black on white, so
DMG reads it. Weak even after fixing: it is thin (five decisions); it works as a 30 s breather between shifts and
should stay short.

Hardware:

```
    01234567890123456789
 00 .999999..ooo...xxx..    o your rounds, x the Kid's (pip tiles)
 01 ssssssssssssssssssss    saloon stage, bar cat
 02 ssssssssssssssssssss
 03 ssssssssssssssssssss
 04 ssssssssssssssssssss
 05 wwwwwwwwwwwwwwwwwwww
 06 wwwwddrraawwiiwbbwww    d r a w i = DRAW! 2x2 tiles per letter (BG), b = A/B badge (BG, 2x2)
 07 wwwwddrraawwiiwbbwww
 08 wwwwwwwHHHHHHwwwwwww    WAIT FOR THE SIGN / FOUL / YOU 0.32 (HUD glyphs)
 09 wwwwwwwwwwwwwwwwwwww
 10 cccccccccccccccccccc    the saloon counter (venue_backdrop, counter row 10)
 11 ffffffffffffffffffff
 12 ffffffffffffffffffff
 13 fffXXffffffffffPPfff    X the Kid (OBJ 16x24), P the Spigoteer
 14 fffXXffffffffffPPfff
 15 fffXXffffTTffffPPfff    T tumbleweed (OBJ 16x16), feint
 16 ffffffffffffffffffff
 17 ffffffffffffffffffff
```

- Worst line: Kid 2 + Spigoteer 2 + tumbleweed 2 = 6 (the crow on the sign row: 2). OAM 4 + 4 + 2 + 2 = 12.
- OBJ tiles: the Kid 3 frames (stand, draw, fumble) x 8 = 24; Spigoteer draw and fumble poses 2 x 8 = 16;
  tumbleweed 2 x 4 = 8; crow 2 x 2 = 4: 52 in 56-127 (72). BG: DRAW! 20, badges 2 x 4 = 8, pips 2, '.' 1 = 31.
- CGB: BG 0/5/6/7 venue, 1 HUD, 2 sign (cream board, red letters); OBJ 0 Spigoteer, 3-4 the Kid, 6 tumbleweed /
  crow. DMG: sign black on white.
- WRAM ~16 B (round, wins x2, phase, t, W, R, badge, feint kind / t / x, press t). ROM ~1.5 KB code + ~1.3 KB art.

Art: the Sarsaparilla Kid 16x24 (stand, draw with cork popping, fumble); Spigoteer draw and fumble poses (the same
frame size as bartender.txt); DRAW! letters 16x16 x 5; badges A and B 16x16; tumbleweed 16x16 x 2; crow 8x16 x 2;
round pip (won / not yet).

Plugs into: mg framework; reuses venue_backdrop and the saloon stage animation. Test hooks: `qd_round`,
`qd_wins[2]`, `qd_state`, `qd_wait` (poke to 1 to skip the wait), `qd_badge`, `qd_r`, `qd_t`. Tests: an early press
is a foul; the wrong badge is a foul; a press at R wins, at R + 1 loses; feints never inside the last 30 frames;
best of 5 stops at 3.

Story fit: suggested PRE_SALOON page (SADIE): `AND IF THE KID` / `CHALLENGES YOU,` / `DRAW FAST!`

### 4.2 T-Shirt Cannon (Stadium)

Play: the seventh-inning stretch at a baseball stadium (the chalk line on the grass is the foul line). The Spigoteer mans the T-shirt cannon on
the field; the stands rise to the right. **Reworked 2026-10-15 (Batch D, the owner's playtest: "looks great, but isn't fun")**: a golf-style power
meter replaces the wind; random fans raise their hands to catch the shirt instead of the wave. **Follow-up F1 (the owner: "I intended for the aim
mechanic to stay")**: Up / Down aim the barrel again, together with the meter.

Rules and numbers (src/ts.c, tools/cannon_table.py simulates the same integer physics):
- 10 shirts, <= 45 s. After a shot lands 40 frames reload.
- Controls: **Up / Down aim** the barrel through 4 angles (45, 52, 60, 68 degrees = the four barrel looks; once a press, a step every 8 frames
  held; also while the cannon reloads), then **A starts the power meter, A again locks the power and fires** (the angle is locked from A on). The
  meter is a vertical bar at the left of the sky (BG column 1, rows 3-10: 64 pixel rows, one a power step) and an arrow marker (a sprite) sweeps
  it 0..63 and back, one step every 2 frames (126 up, 126 down), until A (it never stops by itself). The bar is red at both ends: power 0-10 and
  58-63 are OOPS at every angle (generated from the landing table; the build fails when they differ). At the steeper angles more powers are OOPS
  (short 0-15 at 68 degrees, over from 50 at 60); the marker turns hollow (red on the CGB) in exactly the powers that are OOPS at the aimed angle.
  While A has not started it, the marker blinks at the bottom.
- What the angle does (the D1 agent found that the landing barely moves with the angle, so the angle needed its own job): the power for a column
  shifts only 3-8 steps between 45 and 68 degrees, but **a shirt that is still rising when it hits the stand cannot be caught**. At 45 degrees
  21 of the 47 stand powers are hits on the way up (no catch); at 52, 60 and 68 degrees every hit is a falling shirt. A lob also flies longer
  (47 / 58 / 74 / 93 frames at most: a fan's hands may come down first), has a bigger short zone and narrower windows, a flat shot is quick and
  forgiving about the power but cannot catch the odd columns at all. Every fan can be caught at 3 or 4 angles, each with its own power (fan 6: powers
  36-41 at 52 degrees, 35-41 at 60, 39-46 at 68), so a raised pair of hands has more than one way in.
  The wind is dropped (a second noise on a timing meter nobody can read in 45 s).
- Flight (8.8 fixed point): from the muzzle of the barrel look ((44,107) (44,106) (43,105) (41,105)), speed v = 224 + 13 p px/f (0.88 .. 4.07);
  with vh = v >> 3, vx = (vh cos) >> 5, vy = -((vh sin) >> 5) (cos, sin = 256 cos, 256 sin of the angle: the game multiplies 8 x 8 bits), gravity
  1/16 px/f^2; the shirt's height is signed (a steep shot flies above the screen). The shirt hits the **crowd** when its centre is in a stand
  column (9-19) at or below the column's fan top (11 - (c - 9) / 2 rows) and above the ad boards (y 104); it is **short** at the ad boards or
  down at y 124 (the grass), **over** past x 168. Per angle the build prints the zones, the falling windows and the reach table
  (python3 tools/cannon_table.py).
- The crowd: no wave. Random fans raise their hands (arms up, hands open, two frames that alternate every 8 frames: they pop up and down) for
  120-151 frames (2.0-2.5 s); at most 3 at once; a new one every 50-81 frames, and at once when none is up (always one, two at the start).
- Score: a raised pair of hands reaches one column each side, so a hit in column c with a raised fan in c-1, c or c+1 **and a falling shirt** is
  a **PERFECT CATCH**, 300 points (that fan keeps his hands up 40 frames more; COIN sound; the Spigoteer cheers). Any other hit of the crowd:
  **30 points** (the pittance, 10 %; message CROWD 30, or TOO FLAT! 30 when the shirt was rising near a raised fan). Short or over: an **OOPS** (OOPS! TOO SHORT / OOPS! TOO FAR), 0 points, the miss pose. Messages take the banner row 2
  in the HUD colours for 70 frames.
- Medals (10 x 300 = 3000 at most) unchanged by the aim: BRONZE >= 1500 (5 perfect catches), SILVER >= 2100 (7), GOLD >= 2700 (9). Bots (test
  harness, 3 seeds): perfect timing 3000 at every angle; timing off by up to 3 steps 3000 at 60 degrees; off by up to 6 steps 2430-2730 at 60,
  2460-3000 at 68 and only 1350-1860 at 45 (flat is harder for the catch); locking at a random power 780-1290 (no medal).
- Length: 10 x (meter ~1-2 s + flight ~1 s + 40 reload) ~ 35 s.

Why fun and fair: one decision (when to lock the meter) with a clear picture (the red ends, the raised hands, the landing walks up the stand with
the power), and a target that moves (who has his hands up, for two seconds). The reach of the hands makes every target at least 5 power steps
wide (10 frames, 0.17 s) and the build fails otherwise (tools/cannon_table.py). A shirt that hits the crowd always scores something, so the
wrong guess costs 270, not the shot; only the red ends of the meter score nothing.

Hardware:

```
    01234567890123456789
 00 .999999..HHH...HHH..    score, shirts left (the wind number is gone)
 01 kkkkkkkkkkkkkkkkkkkk    k sky / stadium lights
 02 kkkkkkkkkkkkkkkkkkkk    (the message row: OOPS!, PERFECT CATCH!)
 03 kmkkkkkkkkkkkkkkkkkk    m power meter bar (BG 1x8, rows 3-10, red ends)
 04 kkkkkkkkkkkkkkkkkkkk
 05 kkkkkkkkkkkkkkkkkkkk
 06 kkkkkkkkkkkkkkkkkkkn    n fans (BG 1x2: sitting / standing, 2 looks), rising to the right
 07 kkkkkkkkkkkkkkkkknnn
 08 kkkkkkkkkkkkkkknnnbb    b bleachers
 09 kkkkkkkkkkkkknnnbbbb
 10 kkkkkkkkkkknnnbbbbbb
 11 kkkkkkkkknnnbbbbbbbb
 12 kkkkkkkkknbbbbbbbbbb
 13 kkkPPCCkkbbbbbbbbbbb    C the cannon (OBJ 16x16, 4 barrel looks)
 14 gggPPCCggbbbbbbbbbbb    g grass
 15 gggPPggggggggggggggg
 16 gggggggggggggggggggg
 17 gggggggggggggggggggg
```

- Worst line: Spigoteer 2 + cannon 2 + one preview dot + the shirt = 6. OAM: 4 + 2 + 3 dots + shirt 1 + muzzle puff
  1 = 11.
- OBJ tiles: cannon 4 looks x 4 = 16, shirt 4 spin frames x 2 = 8, dot 2, puff 2 = 28. BG: fans 2 looks x 2 states
  x 2 tiles = 8, bleachers 3, sky / grass / lights 6, windsock 5 x 4 = 20 = 37.
- CGB: BG 0 sky, 1 HUD, 2-3 fan looks (team colours), 4 bleachers / grass, 5 windsock; OBJ 0 Spigoteer, 1 cannon,
  2 shirt. DMG: standing fans show arms up (shape), the shirt is white with a dark outline.
- WRAM ~40 B (angle, wind, shots, reload, shirt x / y / vx / vy in 8.8, state, wave column / direction / timer,
  11 fan bits, cheer timer). ROM ~2 KB code + ~1 KB art + the 55-entry landing table.

Art: cannon on a stand 16x16 (4 barrel angles); rolled T-shirt 8x8 (4 spin frames); stadium fans 8x16 sitting and
standing, 2 looks (reuse the stadium stage's cheering-section style); bleacher tiles; windsock 16x16 x 5; dot;
muzzle puff.

Plugs into: mg framework only. Test hooks: `tc_angle`, `tc_wind`, `tc_shots`, `tc_wave`, `tc_x`, `tc_y`,
`tc_last` (landing column). Tests: the reachability table; same input -> same landing (determinism); wave speed per
stage; 12 shots end the round.

Story fit: PRE_STADIUM page (COACH): `IN THE STRETCH,` / `FIRE SHIRTS INTO` / `THE WAVE!`

### 4.3 Log Roll (Lumber lodge)

Approved by the owner and built (2026-10-12; look A, the daytime river; PLAN.md "Log Roll as built": the 24x24 poses, the reused lodge Sasquatch, the streamed bark tiles, a 180-frame fall, the flip told 30 frames early by a delayed push).

Play: lunchtime log rolling on the river. The Spigoteer and a big hairy partner (no such thing) stand on a spinning
log. The log's spin pushes him off balance; tap Left/Right to lean against it. Stay up for 40 seconds.

Rules and numbers (8.8 fixed point, "lean" = the balance marker's offset in px, fall beyond +-64):
- Each frame: `vel += drift`; `vel -= vel / 16` (damping); `lean += vel`.
- A **press** of Left gives `vel -= 1.0`, Right `vel += 1.0` (holding does nothing more). One tap moves the lean
  about 16 px in total, a quarter of the way to a fall, so two quick taps over-correct: the skill is in the dose.
- Drift magnitude ramps from 0.025 to 0.045 px/f^2 over the 40 s; its sign flips every 120-240 frames (seeded).
  A flip ramps over 30 frames and is told by the log's bark animation slowing and reversing, plus a creak. Holding
  the lean at the centre needs 1.5 taps/s at the start and 2.7 taps/s at the end.
- Fall: |lean| > 64 -> splash, 180 frames (3 s) in the water and climbing back, lean 0. The timer keeps running;
  only time on the log scores.
- Score: 100 per second on the log, +1000 with no fall. Medal: GOLD 40 s on the log, SILVER >= 34, BRONZE >= 25.
- Length: 40 s + intro / outro (the partner topples in at the end if the player is up) ~ 45 s.

Why fun and fair: a balance game where the danger is always visible on the meter and in the pose, and the change of
direction is announced half a second early. Mashing both directions cancels out (drift wins); hammering one way
over-corrects and falls. Not game over on a fall, so a slip at 10 s does not end a 40 s game in frustration.
Luck: the flip times are random but told.

Hardware:

```
    01234567890123456789
 00 .999999..HHH....HHH.    score, falls, T + seconds
 01 pppppppppppppppppppp    p pines / snow (BG)
 02 pppppppppppppppppppp
 03 pppppppppppppppppppp
 04 pppppppppppppppppppp
 05 eeeeeeeeeeeeeeeeeeee    e far bank
 06 eeeeeeeeeeeeeeeeeeee
 07 rrrrrrrrrrrrrrrrrrrr    r river (BG, 2-tile ripple animation)
 08 rrrrrrrrrrrrrrrrrrrr
 09 rrrrrrQQrrrrPPrrrrrr    Q the partner (OBJ 16x24: the lodge show's Sasquatch dancer frames), P Spigoteer
 10 rrrrrrQQrrrrPPrrrrrr
 11 rrrrrrQQrrrrPPrrrrrr
 12 rrrlllllllllllllrrrr    l the log (BG; bark stripes rewritten to show the roll)
 13 rrrlllllllllllllrrrr
 14 rrrrrrrrrrrrrrrrrrrr
 15 rrrrrrrrrrrrrrrrrrrr
 16 rr[mmmmmmm|mmmmmm]rr    balance meter (BG, centre mark, danger ends) + marker (OBJ, 1 entry)
 17 rrrrrrrrrrrrrrrrrrrr
```

- Worst line: Spigoteer 2 + partner 2 + splash droplets 4 = 8. OAM 4 + 4 + 1 + 4 = 13.
- OBJ tiles: Spigoteer 5 lean poses x 8 = 40 (56-95), splash / climb 2 x 8 = 16 (ids >= 128), droplets 4 (bonus
  art), marker 2; the partner is the lodge show's Sasquatch, already at 96-127 from the chapter's level load (reuse,
  no new art). BG: pines / bank / river ~14, log 6 (+ 4 roll frames streamed), meter 6 = ~30.
- CGB: BG 0 pines, 1 HUD, 2 river, 3 log, 4 meter; OBJ 0 Spigoteer, 5 the Sasquatch (show palette), 1 droplets,
  2 marker. DMG: meter black on white; lean poses differ in silhouette.
- WRAM ~20 B. ROM ~1.5 KB code + ~1.5 KB art.

Art: Spigoteer balancing poses 16x24 x 5 (hard left, left, centre, right, hard right, feet running), splash and
climb-back 16x24 x 2; log 112x16 with 4 roll frames of the bark; pines / snow / river tiles; balance meter tiles.

Plugs into: mg framework; reuses the lodge show performer and bonus droplets. Test hooks: `lr_lean`, `lr_vel`,
`lr_drift`, `lr_falls`, `lr_on` (frames on the log). Tests: one tap's total displacement ~16 px; no input falls in
< 3 s at the end drift; alternating taps every frame fall (mash); a flip is told 30 frames ahead.

Story fit: PRE_LUMBER page (JUNE): `LUNCH IS LOG` / `ROLLING. YOUR` / `PARTNER IS... UH.`

**D3 as built (2026-10-15): the leaping fish, the hop and the living Sasquatch** (owner: "the game needs something more ... frogs or fish
jumping out of the water to dodge"; "the sasquatch doesn't move on the log").
- Controls: Left / Right as before; **A, B or Up hops** (a press; 36 frames in the air, peak 36 px on the t (36 - t) / 9 curve, then 12 frames
  of rest). No hop in the river or while staggering.
- The fish: one at a time. 40 frames of **ripple rings** on the water at its launch point (SFX_FILL once), then a flat leap, 96 px in 48 frames
  (2 px a frame, the apex 28 px over the water line at y 118, rise / flat / fall frames, SFX_WHOOSH), then a splash ring where it lands for 12
  frames. It is aimed at the Spigoteer (x 104, from the left with its ring at x 56 or from the right with its ring at x 152) or, one leap in
  four, at the Sasquatch (x 52, from the left, ring at x 4; never while he is in the river). The apex is over the target, so the fish crosses
  the target at the same height whichever side it came from: |fish x - target x| < 10 for 9 frames, and a hop clears it from 14 px up (it is
  that high for 29 of its 36 frames), so a hop started from 3 frames before the leap to 17 frames into it dodges (about 0.35 s of window,
  tests/test_mg_logroll_fish.py).
- A hit on the Spigoteer kicks his velocity 4 px a frame in the fish's direction (about 64 px of lean of the 64 to the edge unless he leans back),
  a 24-frame stagger (the hard-lean pose, no hop, **no Left / Right for the first 12 frames**), SFX_BREAK. Two quick taps after the 12 frames
  save him from a calm log; with the push on the fish's side it is a fall (3 s as ever). A dodge: **+150 points**, SFX_COIN.
- Schedule: first ripples 360 frames in, then every `360 - elapsed / 16 (+ 0..31)` frames (360 at the start, 210 at the end: 6 s -> 3.5 s; a hit always kicks him the way the fish flies and the roll's push waits out the stagger),
  never with under 90 frames left nor in the river. The fish has its own xorshift (`fseed`, from `mg_seed`): `mg_rand` is not called, so the
  flips' sequence is unchanged. A fall ends the fish in the air (it dives with the splash).
- The Sasquatch (the lodge show's four dance frames, no new art): treads on the log (frames 0 2 0 3 by the bark's roll phase, a 1 px bob on
  the odd phases, mirrored by the roll's direction, swaying up to 3 px with the push), windmills (1 2 1 3 every 4 frames) while a flip is
  being told (the bark's ramp under 12), is startled (frame 3) while a fish comes for him or the Spigoteer is hit, hops a fish aimed at him
  half the time (frame 1, the same curve), and otherwise is knocked into the river (the fish stops at him): the topple pose and a splash, 150
  frames swimming, 12 climbing back. His falls are flavour only: the score and the medal do not depend on him. At time up he still topples in
  if he is on the log.
- Medals unchanged (seconds on the log: GOLD 40, SILVER 34, BRONZE 25; a fall costs 3 s). Scripted human-like players (10-14 frame reaction, a tap
  every 12-16 frames at best, some missed): ignoring the fish 28-40 s (mean 34: silver), hopping 75 % of the leaps 34-40 s (mean 39), a bot that
  hops every leap 37-40 s. Score: 100 a second on the log, +150 a dodge, +1000 with no fall.
- Sprites: OAM 15-16 the fish, 17-18 a ring (19 entries in all); worst line 9, as before (the splash scenes; the fish and rings are never up
  while he is in the river). OBJ palette 3 on CGB (cream, orange, dark). Art: assets/art/logroll/fish.txt (3 frames 16x16), ring.txt (3 frames
  16x8). State: struct lr_state grew by 17 bytes inside the mg union (no new global).
- Card: two pages ("LEFT RIGHT: LEAN / AGAINST THE ROLL / A OR B: HOP / OVER THE FISH", "WATCH THE RIPPLES / A FISH LEAPS SOON / HIT: YOU
  WOBBLE / STAY UP 40 SECONDS").

### 4.4 Order Up! (Bistro)

Play: Chef Colby calls an order, dish by dish. Each dish sits on the table at a D-pad direction around the plate.
Repeat the order with the D-pad. Each round adds one dish to the same order (Simon).

Rules and numbers:
- 4 dishes: Up = cheese wheel, Right = baguette, Down = soup bowl, Left = grapes. Each has a tone (Up C6, Right G5,
  Left E5, Down C5) and lights up (inverted 16x16 tile set) when called or pressed.
- Round r = 1..7, order length r + 2 (3..9), one sequence for the whole game, extended by one each round.
- Calling: each dish lit for 24 frames with 8 dark between (rounds 1-3), 20 / 6 (4-5), 16 / 6 (6-7). It also shows
  big in Colby's speech bubble.
- Input: "YOUR TURN". Per dish 150 frames (resets after each correct press). A wrong press or a timeout is a strike:
  "SENT BACK", the same order is called again (not a new one). 3 strikes end the game.
- Round cleared: "ORDER UP!" + bell, 200 x r. Each correct press 50. No strikes at all +1000.
- Medal: GOLD round 7 cleared, SILVER round 5, BRONZE round 3.
- Length: a full clear calls 42 dishes and takes 42 presses: ~18 s + ~17 s + 7 transitions x 1.5 s ~ 45-50 s.

Why fun and fair: memory under mild time pressure, a proven format. Three cues per dish (position, picture,
tone), so a player who cannot hear or cannot tell the greys apart still has two. Mashing: any wrong press is a
strike. Luck: none beyond the order itself; a strike replays the same order so a slip is not punished twice.

Hardware:

```
    01234567890123456789
 00 .999999..xxx...HHH..    score, strikes, round
 01 ssssssssssssssssssss    bistro stage (oven flame animates)
 02 ssssssssssssssssssss
 03 ssssssssssssssssssss
 04 ssssssssssssssssssss
 05 qqqqqqwwwwwwwwwwwwww    q Colby's framed portrait (the story portrait, BG)
 06 qqqqqqwwwwuuwwwwwwww    u the Up dish (2x2)
 07 qqqqqqwwwwuuwwwwwwww
 08 qqqqqqwwllooggwwwwww    l Left dish, o plate, g Right dish
 09 qqqqqqwwllooggwwwwww
 10 qqqqqqwwwwddwwwwwwww    d Down dish
 11 bbbbbbbwwwddwwwwwwww    b speech bubble with the called dish (2x2 inside)
 12 bbbbbbbwwwwwwwwwwwww
 13 bbbbbbbwwwwwwwwwwwww
 14 wwwwwwwwwwwwwwwwwwww
 15 wwwwwwwwwwwwwwwwwwww
 16 ww.o.o.o.o.o.o.o.o.w    order strip: one pip per dish of this round (done / to do)
 17 ffffffffffffffffffff
```

- Sprites: none needed (all BG). Optional: the plate-spinning waiter (bistro show, reuse) dancing at the right
  when a round clears: 4 entries. Worst line 4. OAM 4.
- BG tiles: dishes 4 x 4 x 2 states = 32, plate 4, bubble 6, pips 2, the portrait (story_portraits accessor, LCD
  off: up to 49 + frame 8) = ~100 of 179.
- CGB: BG 0 wall, 1 HUD, 2-3 dishes, 4 the portrait's palette, 5-6 stage, 7 bubble / plate (the keg is not shown).
  DMG: four different silhouettes; lit = inverted.
- WRAM ~20 B (seq[9], len, idx, t, strikes, round, phase). ROM ~1.2 KB code + ~0.8 KB art + 4 tone SFX.

Art: four dishes 16x16, each normal and lit; plate 16x16; speech bubble pieces; order pips (to do / done); Colby's
portrait is the story portrait (placeholder until M11c).

Plugs into: mg framework; the story portrait loader (banked accessor, LCD off). Test hooks: `ou_seq[9]`, `ou_len`,
`ou_idx`, `ou_strikes`, `ou_round`, `ou_phase`. Tests: sequence extends by one and keeps its prefix; a strike
replays the same order; the per-dish timeout; 3 strikes end it; timing per round.

Story fit: PRE_BISTRO page (COLBY): `ORDER UP! REPEAT` / `MY ORDERS. NO` / `CHEESY MISTAKES.`

### 4.5 Marshmallow Drop (Igloo)

**Reworked 2026-10-15 (batch D2, after the owner's playtest: "significantly harder than all of the other mini games"; PLAN.md "Marshmallow Drop as built"
has the numbers).** Play: the player steers the marshmallow arm (LEFT / RIGHT, a little momentum) and drops with A. Six cocoa mugs loop round the
conveyor (a mug leaving at the right comes back at the left) until each holds three marshmallows. The supply is fixed: 6 x 3 + 1 = 19 (shown in the
HUD), so a perfect game (**gold**: all six full, 3600 points) may miss once. A miss, a full mug included, falls on to the belt and splats there. Ends:
every mug full, supply out, or 60 s. SILVER 2400, BRONZE 1200. The sections below are the original proposal (the rail moved by itself) and are kept for
the look and the sprite budget; the rules above replace its "Rules and numbers".


Built (2026-10-12; PLAN.md "Marshmallow Drop as built"): the hybrid look with aurora window W1 and its tile shimmer; the reload counts 24 frames after a landing, points are banked as marshmallows land. The text below is the design as proposed.

Play: cocoa mugs ride a conveyor under a marshmallow dispenser that slides along a rail. Press A to drop. Three
marshmallows make a perfect cocoa; a fourth splashes.

Rules and numbers:
- The dispenser moves left-right on a rail, x 16..136, at a constant 1.0 px/f (0-15 s), 1.25 (15-30 s), 1.5
  (30-45 s), reversing at the ends. Changed from the pitch: a constant-speed rail, not a swinging pendulum (two
  eased motions at once are hard to read at 1x; the swing stays as a 2-frame wobble in the art).
- A drops the marshmallow straight down at 2 px/f (no sideways speed): 22 frames from the rail to a mug's rim.
  One in the air at a time; the next is loaded 24 frames after the drop.
- Mugs ride right at 0.5 px/f (0-15 s), 0.75, 1.0 px/f; spacing 48-72 px (seeded), never under 48 (so at most
  4 mugs, even partly visible ones, share the screen: 10 sprites a line is the limit, see below).
- A hit: the marshmallow's centre within the mug's 12 px opening. Mugs show 0-3 marshmallows; the 4th splashes
  cocoa (-100, that mug scores nothing more).
- A mug leaving at the right scores 100 per marshmallow, +300 for exactly three ("PERFECT COCOA").
- 45 s. About 30 mugs pass but at most ~58 drops are possible, so the player chooses: finish mugs to three for the
  bonus, or spread. Medal: GOLD >= 6000, SILVER >= 4000, BRONZE >= 2000 (tune in playtest).

Why fun and fair: timing and leading: the drop takes 22 frames, so you release when the mug is ~11-22 px short of
the dispenser. Everything moves at a constant speed, so the lead is learnable. Mashing: one marshmallow at a time
plus the reload means mashing drops about one a second at random spots, most miss, and a mash on a full mug
splashes. No luck: spacing is random but never too tight.

Hardware:

```
    01234567890123456789
 00 .999999........HHH..    score, T + seconds
 01 ssssssssssssssssssss    igloo stage (aurora animates)
 02 ssssssssssssssssssss
 03 ssssssssssssssssssss
 04 ssssssssssssssssssss
 05 =========DD=========    = rail (BG); D the dispenser (OBJ 16x16) + its marshmallow (OBJ)
 06 wwwwwwwwwDDwwwwwwwww
 07 wwwwwwwwwwwwwwwwwwww
 08 wwwwwwwwwwMwwwwwwwww    M a falling marshmallow (OBJ)
 09 wwwwwwwwwwwwwwwwwwww
 10 wwwwwwwwwwwwwwwwwwww
 11 wwwwwwwwwwwwwwwwwwww
 12 wwwUUwwwwwwUUwwwwwUU    U cocoa mugs on the belt (OBJ 16x16), moving right
 13 wwwUUwwwwwwUUwwwwwUU
 14 >>>>>>>>>>>>>>>>>>>>    conveyor (BG, 2 tiles animated)
 15 ffffffffffffffffffff
 16 ffffffffffffffffffff
 17 ffffffffffffffffffff
```

- Worst line: 4 mugs x 2 (spacing >= 48 px over the 175 px where a mug is at least partly visible: 4 at most;
  a mug at OAM x 0 still counts on its line) + the falling marshmallow = 9. Dispenser line: 2 + 1 = 3. OAM <= 14.
- OBJ tiles: dispenser 2 x 4 = 8, marshmallow 2, mug 5 states (0-3, splash) x 4 = 20 = 30. BG: rail 2, belt 3,
  floor 2, labels ~10 = ~20.
- CGB: BG 0 wall, 1 HUD, 2 belt, 5-6 stage; OBJ 3 dispenser, 1 cocoa mug (the igloo's full-drink palette),
  6 marshmallow. DMG: marshmallows white on dark cocoa.
- WRAM ~30 B. ROM ~1.3 KB code + ~0.8 KB art.

Art: dispenser 16x16 (2 wobble frames); marshmallow 8x8; cocoa mug 16x16 with 0, 1, 2, 3 marshmallows and a
splash; rail and conveyor tiles.

Plugs into: mg framework. Test hooks: `md_claw_x`, `md_drop_y`, `md_mug_x[5]`, `md_mug_n[5]`, `md_speed`. Tests:
fall time 22 frames; a hit inside the opening and a miss 1 px outside; the 4th splashes; spacing never < 48.

Story fit: PRE_IGLOO page (AURORA): `MARSHMALLOWS GO` / `IN EVERY MUG.` / `THREE IS PERFECT.`

### 4.6 Battery Sort (Robot factory)

Play: batteries roll in on a belt and stop on a diverter. Left sends a charged one to the CHARGE bin, Right a dead
one to RECYCLE, a broken one Down to SCRAP (all three bins from the very first battery, owner 2026-10-15). The belt speeds up as you go.

Rules and numbers:
- The front battery waits on the diverter for at most D frames: D = 120 at the start, -8 every 4 correct sorts, never
  under 40 (667 ms, above a 3-choice reaction time of ~500 ms). Batteries behind it queue 16 px apart, visible.
- Belt speed (refills the queue): 0.75 px/f, +0.125 every 6 correct sorts, max 2.0; batteries enter 24 px apart.
- Correct: the battery flies into its bin (arc, 20 frames), 100 + 10 x streak (streak bonus capped at 200).
  Wrong bin or D runs out: a strike (buzzer, the bin spits it onto the floor). 3 strikes or 45 s end it.
- Mix (D5a, 2026-10-15): the first three batteries are one of each kind (charged, dead, broken) so the player sees every bin
  and direction at once; then 30% broken, the rest charged / dead 50 / 50. No mid-game banner, no pause: the chute is open
  from the start and the HOW TO PLAY card explains Down.
- A strike never eats the next battery's time: a wrong bin is judged when the battery lands (24 frames after the sort), by
  when the next battery has been waiting up to 24 frames; at the strike its wait is restored to the full D.
- Medal: GOLD >= 6000, SILVER >= 4000, BRONZE >= 2000. A fast, clean player sorts ~50 in 45 s.

Why fun and fair: categorise under rising pressure, with the next five visible so you can read ahead. Mashing
Left/Right is wrong half the time: three strikes come fast. No luck. Readability on DMG: the factory's full and
empty batteries are already light-bodied (charged, 4 bright bars) and dark-bodied (dead, 1 bar); broken ones are
bent with a blinking spark, a different silhouette.

Hardware:

```
    01234567890123456789
 00 .999999..xxx....HHH.    score, strikes, T + seconds
 01 ssssssssssssssssssss    factory stage (gear animates)
 02 ssssssssssssssssssss
 03 ssssssssssssssssssss
 04 ssssssssssssssssssss
 05 wwwwwwwwwwwwwwwwwwww
 06 wwwwwwwwwwwwwwwwwwww
 07 wwwwwwwwwwwwwwwwwwww
 08 IIIIIIIIIwwwwwwwwwww    I batteries (OBJ 8x16) queued on the belt
 09 >>>>>>>>>vvwwwwwwwww    > belt (BG, animated), v diverter (BG 2x2, arrow states)
 10 wwwwwwwwwvvwwwwwwwww
 11 wwwwwwwwwwwwwwwwwwww
 12 wnnnnnnwwwwwwrrrrrrw    n CHARGE bin (bolt sign), r RECYCLE bin
 13 wnnnnnnwwwwwwrrrrrrw
 14 wnnnnnnwkkkkwrrrrrrw    k SCRAP chute (open from the start since D5a)
 15 wnnnnnnwkkkkwrrrrrrw
 16 wnnnnnnwkkkkwrrrrrrw
 17 ffffffffffffffffffff
```

- Worst line (the belt): 5 queued + 1 entering + 1 flying + 1 spark = 8. OAM ~12.
- OBJ tiles: charged and dead batteries are the factory drink's full and empty frames, already loaded (OBJ 56-59;
  the game borrows only 60-127); broken battery 2, spark 2 = 4 new. BG: belt 3, diverter 3 states x 4 = 12, bins
  2 x 8 = 16, chute 6, signs ~4 = ~41.
- CGB: BG 0 wall, 1 HUD, 2 belt, 3 bins, 4 signs, 5-6 stage; OBJ 1 / 2 the factory drink palettes (charged lime,
  dead red), 3 broken, 4 spark. DMG: light vs dark body, as the bar game.
- WRAM ~45 B (queue of 8: type + x, diverter state, D, speed, strikes, streak, flying x / y / target, count).
  ROM ~1.3 KB code + ~1 KB art.

Art: broken battery 8x16 (bent, scorched), spark 8x8 (2 frames), diverter with left / right / down arrows, bins
with a bolt sign and a recycle sign, scrap chute (closed / open), belt tiles.

Plugs into: mg framework; reuses the factory drink tiles. Test hooks: `bs_queue[8]`, `bs_front`, `bs_window`,
`bs_speed`, `bs_strikes`, `bs_sorted`. Tests: each type to its bin; timeout strike; D never under 40; broken only
from 16; the chute banner pauses the belt.

Story fit: PRE_ROBOT page (MANAGER-BOT): `SORT CHARGED` / `LEFT. DEAD RIGHT.` / `DO NOT MIX.` (Chapter 6's goal is
already about recycling batteries.)

### 4.7 Taiko Pour (Teahouse)

Built (2026-10-12; PLAN.md "Taiko Pour as built"): look B, the tune plays at 12 frames a row (not 15), 112 notes from frame 288, a missed note is dropped at x < 6, the HUD cups counter has two digits, OBJ palette 7 for the pot. The text below is the design as proposed.

D6a (2026-10-15, owner: "too many notes too fast"): NORMAL is now a thinned chart of 76 notes (quarter-note rows only, no pairs, never two notes within 24 frames, 2-3 a bar in round 1, 3 in round 2, 4 in round 3), windows PERFECT 4 / GOOD 8 / REACH 11 frames, medals by accuracy GOLD 90% / SILVER 70% / BRONZE 50% (derived from scripted bots; batchD d6_tuning DESIGN.md). The first chart (112 notes, windows 3/6/10, SILVER 75%) is HARD: tools/taiko_chart.py GRIDS["hard"], kept for the difficulty table; the tuning constants are the NORMAL block at the top of src/tk.c.

Play: the taiko drummer sets the beat of "Sakura Sakura". Notes slide along two lanes to the hit marks: A for the
top lane (the drum's face, "don"), B for the bottom lane (the rim, "ka"). Good hits pour tea; eight fill a cup for
a guest.

Rules and numbers:
- Notes move left at 1.5 px/f from x 160 to the hit mark at x 24: 91 frames (1.5 s) of look-ahead.
- Windows: PERFECT +-3 frames (+-50 ms), GOOD +-6 (+-100 ms), else MISS. A press with no note in that lane within
  +-10 frames is a SPILL (-50, combo reset).
- Chart: the venue tune at its game tempo (15 frames a row, rows are eighth notes, 120 bpm); notes on beats and some
  eighths, never two notes in a lane closer than 22 px (one eighth). ~88 notes in ~45 s after a 4-beat count-in.
  Rounds of density: bars 1-8 quarter notes, A only; 9-16 both lanes; 17-24 eighth-note pairs.
- Score: PERFECT 300, GOOD 100, + combo (10 per note in the combo, max 100); each 8 GOOD-or-better = a cup served
  (+500). Medal by accuracy (PERFECT 1, GOOD 0.5): GOLD >= 90%, SILVER >= 75%, BRONZE >= 50%.
- Sync: notes are placed from the music driver's song position (row x 15 + tick), not from a frame count, so a late
  frame never drifts the chart. music.c exports `song_pos` (frames since the song started).
- Music OFF in the title menu: this game plays the tune anyway and restores the setting after (open question 4);
  the lane borders also flash on each beat as a visual metronome.

Why fun and fair: rhythm, with generous GB-sized windows and look-ahead. Two lanes instead of one: on DMG two note
types in one lane at 8 px would be hard to tell apart at 1x, and 16 px notes in one lane would put 12 sprites on a
line at eighth-note density. Mashing: spills cost points and reset the combo, so mashing scores below zero.

Hardware:

```
    01234567890123456789
 00 .999999..HHH....HHH.    score, combo, accuracy
 01 ssssssssssssssssssss    teahouse stage (lanterns animate)
 02 ssssssssssssssssssss
 03 ssssssssssssssssssss
 04 ssssssssssssssssssss
 05 wwwwwwwwwwwwwwwwwwww
 06 llaa--N---N----N----    lane A (BG): aa = hit mark "A", N notes (OBJ 8x16)
 07 llaa--N---N----N----
 08 wwwwwwwwwwwwwwwwwwww
 09 llbb----N-----N-----    lane B: bb = hit mark "B"
 10 llbb----N-----N-----
 11 wwwwwwwwwwwwwwwwwwww
 12 wwRRwwwwwwwwwuuuuwww    R the drummer (OBJ, the teahouse show performer), u tea cup on a tray (BG)
 13 wwRRwwwwwwwwwuuuuwww
 14 wwRRwwwwwwwwwuuuuwww
 15 ffffffffffffffffffff
 16 ffffffffffffffffffff
 17 ffffffffffffffffffff
```

- Worst line: a lane: <= 6 notes + hit flash 1 = 7. Drummer lines: 2 + steam 1. OAM: 12 notes + 2 flashes + drummer
  4 + 1 = 19.
- OBJ tiles: don note (filled disc) 2, ka note (ring with a notch) 2, flashes 2 x 2 = 4: 8 new; the drummer is the
  teahouse show performer already at 96-127 (reuse). BG: lanes 4, hit marks 2 x 4 = 8, cup on tray 4 fill states
  x 4 = 16, beat-flash border 2 = ~30.
- CGB: BG 0 wall, 1 HUD, 2 lanes, 3 cup, 5-6 stage; OBJ 1 don (red), 2 ka (blue), 3 flash, 5 drummer (show).
- WRAM ~35 B (chart index, next note time, 12 live notes x (x, lane), combo, hits, cup). ROM ~1.5 KB code + the
  chart (~180 B) + ~0.6 KB art. A tool, tools/taiko_chart.py, writes the chart from a text grid aligned to the
  song's rows.

Art: two note shapes 8x8, hit flash 8x8 x 2, lane and hit-mark tiles, a tea cup on a tray (4 fill states).

Plugs into: mg framework; music.c gains `song_pos`; reuses the show performer. Test hooks: `tk_note`, `tk_hits`,
`tk_perfect`, `tk_combo`, `tk_spills`, plus `song_pos` (poke to jump). Tests: a press at the note's frame +-3 is
PERFECT, +-6 GOOD, +-7 MISS; spill rule; chart never closer than 22 px; sync holds over a forced 3-frame lag.

Story fit: PRE_TEAHOUSE page (HANA): `THE DRUM SETS` / `THE POUR. A AND B` / `ON THE BEAT.`

### 4.8 Asteroid Delivery (Space lounge)

D6c (2026-10-15, owner: too hard): NORMAL has 7 rocks (lanes 0, 2, 4 hold one), speed steps x1.25 at 4 deliveries and x1.5 at 8, a blinking edge arrow 40 frames before a rock comes in (OAM 28-32, new art edge.txt), the lit porthole's whole 24 px ledge delivers on any touch at any speed (no WHOA), and medals 4 / 6 / 8 deliveries (pilot-derived; batchD d6_tuning DESIGN.md). The first values (10 rocks, x1.5 / x2 at 3 / 6, a +-8 px zone and 0.75 px a frame touch, medals 3 / 5 / 7) are HARD: noted beside the NORMAL block at the top of src/ad.c.

Play: Zizz's guests wait in three portholes at the top. A glowing beaker appears on the bar at the bottom; steer it
up through drifting asteroid lanes and hand it gently to the alien whose porthole is lit.

Rules and numbers (8.8 fixed point):
- D-pad (8-way) thrust: each held axis adds 1/32 px/f^2; drag `v -= v / 32` per frame; each axis capped at
  1.25 px/f. Released, the beaker drifts and slows (about 1 s to half speed). No gravity (changed from "low
  gravity": in a top-down field gravity would only mean "everything falls down", which fights the route reading).
- Asteroids (16x16) drift horizontally in 5 lanes, 2 per lane, wrapping; lane speeds 0.25, 0.375, 0.5, 0.375, 0.25
  px/f, alternating directions; x1.5 after 3 deliveries, x2 after 6. Within a lane, rocks are >= 56 px apart, so
  there is always a gap of >= 40 px.
- Delivery: the beaker touches the lit porthole's hand zone (16x8) with both speeds <= 0.75 px/f: +500 + a time
  bonus (frames under a 10 s par / 10). Too fast: "WHOA", it bounces (v = -v / 2), nothing lost.
- A rock hit: the beaker spills (tumbles 30 frames), a new one appears on the bar after 60 frames. Nothing else
  is lost but time.
- The next porthole lights at random (seeded), never the same one twice in a row.
- 45 s. Medal by deliveries: GOLD 7, SILVER 5, BRONZE 3.

Why fun and fair: route reading (Frogger lanes) plus steering with momentum and a soft landing. Lanes make the
danger readable at 1x; gaps are guaranteed. Mashing / holding everything gives no thrust. Flagged after fixing:
inertia steering is the most likely to feel bad on a small screen; the drag value (1/32) and the speed cap are the
knobs, and it needs a playtest. If it still frustrates, fall back to direct steering at 1 px/f with only a short
glide.

Hardware:

```
    01234567890123456789
 00 .999999..HHH....HHH.    score, delivered, T + seconds
 01 ********************    * starfield (BG)
 02 *oo*******oo*****oo*    o portholes with an alien (BG; the space patrons' shift-0 art), lit one framed
 03 *oo*******oo*****oo*
 04 **AA**********AA****    lane 1: A asteroids (OBJ 16x16), drifting right
 05 **AA**********AA****
 06 *******AA********AA*    lane 2, drifting left
 07 *******AA********AA*
 08 AA*********AA*******    lane 3
 09 AA*********AA*******
 10 *****AA*********AA**    lane 4
 11 *****AA*********AA**
 12 ***AA*******AA******    lane 5
 13 ***AA*******AA******
 14 ********************
 15 *********Y**********    Y the beaker (OBJ 8x16: the space drink) on its launch spot
 16 cccccccccccccccccccc    the space lounge's counter (backdrop)
 17 ffffffffffffffffffff
```

- Worst line: one lane: 2 rocks x 2 + beaker 1 + thrust puff 1 = 6 (lanes are exactly 16 px, rocks never cross
  into another lane). OAM: 20 rocks + beaker + puff + an arrow over the lit porthole = 23.
- OBJ tiles: rock 2 looks x 4 = 8, puff 2, arrow 2 = 12 new; the beaker is the space drink's full frame (already at
  56). BG: stars 4, porthole frame and lit frame 8, the three aliens' shift-0 poses (18, reloaded from the patron
  bank or still in VRAM from the level), labels ~5 = ~35.
- CGB: BG 0 space, 1 HUD, 2-4 the aliens' patron palettes, 7 porthole frame; OBJ 1 beaker (space drink palette),
  3 rocks, 6 puff. DMG: rocks mid grey with dark outline on a dark sky with light stars: rocks get a light rim.
- WRAM ~45 B (beaker x / y / vx / vy 8 B, state, 10 rocks x 2 B, lane speeds, porthole, counters). ROM ~1.8 KB
  code + ~0.5 KB art.

Art: asteroids 16x16 (2 looks), thrust puff 8x8, arrow 8x8, porthole frame (dark, lit), starfield tiles. The
aliens and the beaker are existing art.

Plugs into: mg framework; `patron_load` (banked) for the three shift-0 poses. Test hooks: `ad_x`, `ad_y`, `ad_vx`,
`ad_vy`, `ad_dock`, `ad_done`, `ad_rock_x[10]`. Tests: thrust / drag numbers; a slow touch delivers, a fast one
bounces; rock gaps >= 40 px in every lane at every frame; no two docks the same in a row.

Story fit: PRE_SPACE page (ZIZZ): `DELIVER BEAKERS` / `PAST THE ROCKS.` / `GENTLY!`

### 4.9 Monkey Business (Jungle zoo)

Built (2026-10-12; PLAN.md "Monkey Business as built"): reading 1 with G1 (green crates and awning), at most one runner on screen, medals GOLD 8000 / SILVER 5000 / BRONZE 2500, the parrot's -200 never below 0, the list name MONKEY BIZ. The text below is the design as proposed.

D6b (2026-10-15, owner: too hard, and a run with no parrots): NORMAL gives more reaction time (U 120 falling to 75, pop interval 84 falling to 42, caps 2 until 30 s then 3), always has parrots (pop 4 is a parrot, then never more than 10 pops without one, on top of the random 1 in 6 from 10 s) and its medals are 3000 / 5200 / 7500 (derived from human-speed scripted bots; batchD d6_tuning DESIGN.md). The first values (U 90 -> 45, interval 60 -> 24, caps 2 -> 3 at 20 s, parrots from 15 s, medals 2500 / 5000 / 8000) are HARD: noted beside the NORMAL block at the top of src/mk.c.

Play: five supply crates on the counter. Monkeys pop out of them to grab coconuts from Kiki's pile. Hop to the crate
and shoo the monkey (gently, with a feather duster) before it grabs one. Don't shoo the parrot.

Rules and numbers:
- The Spigoteer stands in front of crate k (0-4, 32 px apart). Left / Right hops one crate in 6 frames (held:
  repeats every 10 frames). A: an 8-frame shoo at crate k.
- A pop: the crate's lid rattles for 20 frames (BG tile swap), the monkey peeks (6 frames) and stays up U frames,
  then grabs a coconut and runs off with it. U = 90 frames at the start, falling linearly to 45 at 30 s.
- Pop interval 60 frames at the start, 24 at the end; at most 2 monkeys up before 20 s, 3 after.
- Reachability rule (the fairness fix): a pop at crate j is scheduled only if the greedy path (nearest deadline
  first, 6 frames a hop, 8 frames to shoo) reaches every monkey that will be up with >= 8 frames to spare. If not,
  another crate is tried, or the pop waits.
- A shoo with a monkey up (peeking counts): shooed, 100, +100 if within 20 frames of the lid opening. A shoo with
  nothing there: a whiff and a 12-frame lockout.
- The parrot (from 15 s, 1 pop in 6): it rises the same way; shooing it costs -200 (squawk); left alone it flies
  off by itself.
- 8 coconuts. Ends at 45 s or when the pile is empty; +200 per coconut left.
- Medal: GOLD >= 4000, SILVER >= 2500, BRONZE >= 1200 (tune).

Why fun and fair: reaction plus positioning (whack-a-mole with travel), and a reading check (monkey or parrot).
The lid rattle tells where 20 frames early; the scheduler never asks for the impossible. Mashing: whiffs lock you
out for 12 frames and the parrot punishes blind shooing. Luck: pops are random, but always reachable.

Hardware:

```
    01234567890123456789
 00 .999999..HHH....HHH.    score, coconuts left, T + seconds
 01 ssssssssssssssssssss    zoo stage (parrot animates)
 02 ssssssssssssssssssss
 03 ssssssssssssssssssss
 04 ssssssssssssssssssss
 05 wwwwwwwwwwwwwwwwkkkk    k Kiki's coconut pile (BG, shrinks as coconuts go)
 06 wwwwwwwwwwwwwwwwkkkk
 07 wwwwwwwwwwwwwwwwwwww
 08 wMMwwwwwwwwwwMMwwwww    M monkeys / the parrot popping up (OBJ 16x16)
 09 wMMwwwwwwwwwwMMwwwww
 10 wbbwwbbwwbbwwbbwwbbw    b crates (BG 2x2, lid rattle frames)
 11 wbbwwbbwwbbwwbbwwbbw
 12 cccccccccccccccccccc    the zoo counter
 13 wwwwwwwwwwwwwPPwwwww    P the Spigoteer in front of crate 3
 14 wwwwwwwwwwwwwPPwwwww
 15 wwwwwwwwwwwwwPPwwwww
 16 ffffffffffffffffffff
 17 ffffffffffffffffffff
```

- Worst line (the monkeys' rows): 3 monkeys x 2 + a running monkey's coconut 1 + the shoo puff 1 = 8. The
  Spigoteer's rows: 2 + duster 1. OAM ~13.
- OBJ tiles: monkey 3 frames (peek, up, run with coconut) x 4 = 12, parrot 2 x 4 = 8, coconut (the zoo drink's
  full frame, reuse), Spigoteer shoo pose 8, puff 2 = 30. BG: crate 4 + lid rattle 2, pile 6 states, labels = ~30.
- CGB: BG 0 wall, 1 HUD, 2 crates, 3 pile, 5-6 stage; OBJ 0 Spigoteer, 3 monkey, 6 parrot, 1 coconut. DMG: the
  monkey (round ears, curled tail) and the parrot (beak, crest, long tail) differ in silhouette.
- WRAM ~25 B (5 crates x (state, timer), position, hop timer, lockout, coconuts, pop timer, seed). ROM ~1.5 KB code
  + ~0.8 KB art.

Art: monkey 16x16 (peek, up, running with a coconut), parrot 16x16 (2 frames), crate 16x16 with a rattling lid
frame, coconut pile (8 down to 0 in 6 looks), Spigoteer shoo pose with a feather duster (16x24), puff.

Plugs into: mg framework. Test hooks: `mb_pos`, `mb_crate[5]`, `mb_timer[5]`, `mb_coconuts`, `mb_lock`. Tests: the
scheduler never creates an unreachable set (a scripted perfect bot clears 45 s without a steal at every seed in a
sweep); whiff lockout; the parrot penalty; the 20-frame rattle before every pop.

Story fit: PRE_ZOO already says WATCH THE MONKEYS. THEY LOVE TO STEAL A COCONUT; no change needed.

### 4.10 Milk Run (The Chrome Cow, chapter 7)

Approved by the owner and built (2026-10-12; PLAN.md "Milk Run as built": the HUD stays on row 0 with a raster split instead of a bottom window). Numbered last so the references to 4.1-4.9 stay; in chapter order it
is the seventh mini-game.

**Reworked 2026-10-15 (batch D4, after the owner's playtest: "let's give the player more control"; PLAN.md "Milk Run rework as built" has the numbers).**
Controls now: UP / DOWN change lane, RIGHT held speeds the street up and LEFT held slows it (1.0 .. 2.5 px a frame, start 1.5; let go and the speed
stays), **A tosses a crate to the top kerb and B to the bottom kerb from any lane** (the old "toss from the top / bottom lane only" rule is gone).
The bike starts with 10 crates; **two milk-bottle pickups** stand in the road (each +3 crates, a bob and a lane of its own; a gate near one never
blocks its lane); **a bump spills 2 crates (3 at 2.0 px a frame or faster) and takes the speed away** (back to 1.0 and no throttle while the bike
wobbles). The speed is a trade-off: the course is the 12 boxes and ends when the last is out of reach (ROUTE DONE, +20 points for each whole second
left; the clock is 70 s), so a fast run pays more, but gates arrive faster, the lead of a toss is longer (speed x 16 frames) and a bump costs more.
Medals are by the score now: BRONZE 3000, SILVER 4500, GOLD 6000 (scripted runs in the PLAN section). The HOW TO PLAY card is three pages (driving, tossing,
bottles / bumps / bonus). A two-cell speed gauge sits in the HUD (columns 14-15). The text below is the original design; its "Rules and numbers" are
replaced by the paragraph above where they differ (speed ramp, toss lanes, 12 crates, 45 s, medals by deliveries).

Play: Granny lends the Spigoteer her motorcycle, its sidecar stacked with milk crates. Seen from above, he rides along
a three-lane street that scrolls past, dodging potholes and traffic cones, and tosses a crate onto each milk box on
the kerb as it goes by.

Rules and numbers (8.8 fixed point):
- The bike stays at screen x 24-47 (columns 3-5). Up / Down changes lane in 8 frames (16 px at 2 px/f); one press
  during a change is queued. The street scrolls left at 1.5 px/f, +0.25 every 10 s, 2.5 px/f from 40 s.
- Obstacles are BG tiles on the road: potholes (16x16) and traffic cones (8x16, set in pairs). They come in **gates**:
  a gate blocks 1 or 2 of the 3 lanes, never all 3. The fairness rule: the next gate is at least v x (8 x L + 20 +
  12) px ahead, where L is the number of lanes the bike must cross to get from a free lane of this gate to a free
  lane of the next (0-2), 20 frames is reaction and 12 the bike's length at speed; e.g. L = 2 at 2.5 px/f is 120 px.
  The generator (seeded RNG) only places a gate that passes the check.
- Milk boxes stand on the kerbs: the top kerb beside lane 1, the bottom kerb beside lane 3. 12 boxes in the run, one
  every ~3.5 s, sides at random but never two on one side closer than 64 px. A box is never placed beside a gate that
  blocks its kerb lane, so a delivery never forces a crash.
- A: toss a crate toward the kerb beside the bike's lane (lane 1 up, lane 3 down). In lane 2, A does nothing (he
  shrugs; nothing lost). The crate arcs 16 frames. Landing within 8 px of a box's centre: PERFECT, 500; within 16 px:
  delivered, 300; anywhere else the crate is lost on the pavement.
- A crash (the bike's 16x12 hit box touches an obstacle tile): the bike wobbles 30 frames, one crate falls off (lost),
  the speed drops one step (not below 1.5), then 60 frames of blinking invulnerability. Nothing else is lost.
- 12 crates in the sidecar. At the end each crate left is +100. 45 s.
- Medal by deliveries: GOLD 10, SILVER 7, BRONZE 4.

Why fun and fair: lane dodging with a delivery-timing layer: read the gates and boxes ahead and plan the lane changes
so you are in the kerb lane as a box comes by. 112 px of street are visible ahead of the bike: at 2.5 px/f that is 45
frames, more than the worst case needs (a two-lane change, 16 frames, plus 20 of reaction). Every gate is passable and no box sits
beside a blocked kerb lane: a clean run exists at every seed (a bot test checks it). Mashing A loses crates; holding
Up or Down parks the bike in a kerb lane, where the gates catch it. Luck: the street is random, but the fairness rule
bounds it.

Hardware:

```
    01234567890123456789
 00 hhhhhhhhhhhhhhhhhhhh    h houses, fences, trees (BG; rows 0-16 scroll together with SCX)
 01 hhhhhhhhhhhhhhhhhhhh
 02 hhhhhhhhhhhhhhhhhhhh
 03 kkkkkkkkkkkkkkmmkkkk    k top kerb; m a milk box (BG 2x2)
 04 kkkkkkkkkkkkkkmmkkkk
 05 rrrrrrrrrrrrrrrrrrrr    lane 1 (r road; the dashed lane line is drawn in the lane tiles)
 06 rrrrrrrrrrrrrrrrrrrr
 07 rrrBBBrrrroorrrrrrrr    lane 2: B the Spigoteer on the bike with the sidecar (OBJ, 3 x 8x16); o a pothole (BG 2x2)
 08 rrrBBBrrrroorrrrrrrr
 09 rrrrrrrrrrrrrrrrrcrr    lane 3; c a traffic cone (BG 1x2)
 10 rrrrrrrrrrrrrrrrrcrr
 11 kkkkkkkkkmmkkkkkkkkk    bottom kerb, another milk box
 12 kkkkkkkkkmmkkkkkkkkk
 13 hhhhhhhhhhhhhhhhhhhh
 14 hhhhhhhhhhhhhhhhhhhh
 15 hhhhhhhhhhhhhhhhhhhh
 16 hhhhhhhhhhhhhhhhhhhh
 17 .999999..HHH....HHH.    the HUD in the window (WY 136): score, crates left, T + seconds; it never scrolls
```

- Worst line (a lane's 16 lines): bike 3 + a tossed crate 1 + crash stars 2 = 6. Obstacles and boxes are BG: zero
  sprites. OAM ~8 (bike 3, crate 1, stars 2, a PERFECT pop 2).
- Scrolling: SCX moves rows 0-16; the HUD lives in the window at row 17 (WY 136, WX 7), so there is no raster split.
  Every 8 px of scroll the map column about to come in at the right ((SCX >> 3) + 21, mod 32) is written: 17 tiles
  and, on CGB, 17 attributes, from a generated street column in WRAM. A map column is vertical (stride 32), not a
  vq_add row, so mg.c gains `mg_put_column`, written in VBlank (34 bytes, ~350 cycles); at 2.5 px/f a column is due
  every 3.2 frames, never two in one frame. The intro banner and the result window move the window as in every
  mini-game; the street stops scrolling while they show.
- Tiles: BG road 2 (plain, dashed), kerb 2, milk box empty 4 + with a crate 4, pothole 4, cone 2, houses / fences /
  trees ~20: ~38. OBJ: the bike with rider and sidecar 3 frames (ride A / B, wobble) x 6 = 18, crate 2 arc frames x 2 =
  4, crash stars 2, PERFECT pop 2: ~26 in 56-127.
- CGB: BG 0 road and kerb, 1 HUD, 2 houses, 3 milk boxes and crates, 4 potholes and cones; OBJ 0 the Spigoteer, 1 the
  bike's chrome and sidecar, 3 crate. DMG: cones light with a dark stripe, potholes dark, boxes outlined; the bike is
  readable by silhouette.
- WRAM ~40 B (scroll 16 bit, speed 8.8, lane / target / change timer, crates, delivered, 4 gates x (x, lane mask), 3
  boxes x (x, side), the crate's x / y / t, wobble and invulnerable timers, generator state); the 34-byte column
  buffer also in the `mg` union. ROM ~1.8 KB code + ~1 KB art.

Art (proposals first): the Spigoteer on Granny's motorcycle with a sidecar of milk crates, from above at a slight
angle, 24x16 (ride A, ride B, wobble); a milk crate 8x16 (2 arc frames); milk box (empty, with a crate); pothole;
traffic cone; kerb and road tiles; houses, fences and trees for the verges; crash stars; PERFECT pop.

Plugs into: the mg framework, plus two small additions any later scrolling game can reuse: `mg_put_column` and a
window-HUD option (the HUD on window row 17 instead of BG row 0). Music: the venue's tune. Test hooks: `mr_lane`,
`mr_scroll`, `mr_speed`, `mr_crates`, `mr_done`, `mr_gate_x[4]`, `mr_gate_m[4]`, `mr_box_x[3]`, `mr_box_side[3]`,
`mr_inv`. Tests: a scripted bot (lanes planned from the gate and box queues) delivers all 12 without a crash at every
seed of a sweep (the fairness rule); every gate leaves a lane free and keeps its spacing at every speed; no box beside
a gate that blocks its kerb lane; a toss within 8 px is PERFECT, within 16 delivered, else the crate is lost, and in
lane 2 nothing happens; a crash costs one crate and one speed step and gives 60 frames of invulnerability; the column
coming in is in VRAM before SCX shows it (checked every frame); the window HUD never moves; <= 10 objects on every
line every frame.

Story fit: suggested PRE_BIKER page (GRANNY): `TAKE MY BIKE AND` / `RUN THE MILK. MIND` / `THE POTHOLES!`

## 5. The Pour-Off (finale, vs Dregs)

Play: back in Fizzwater, the nine pieces (ten with The Chrome Cow) click together, and Dregs asks for one last, friendly contest: who pours the
festival's first drink. Both bartenders work the same four bars from opposite ends, the Spigoteer on the right as
always, Dregs on the left. Thirsty townsfolk sit along the middle of the bars. A drink that reaches a thirsty
person first scores for whoever slid it. First to 20.

Rules and numbers:
- Seats: three per bar at x 40, 72, 104 (symmetric about the screen centre, so every seat is as far from Dregs's
  spout, x 16, as its mirror seat is from the player's, x 136). Patrons do not walk; they pop in on a free seat
  every 50 frames at the start, 35 at the end, at most 2 per bar (8 on screen).
- Patience: 480 frames. In the last 120 they sway (impatient); at 0 they leave and nobody scores.
- A full drink slides at 2 px/f (Dregs's to the right). The first thirsty patron whose 16 px it meets catches it:
  +1 for the bartender who slid it. The patron drinks 60 frames (held mug sprite) and slides the empty back to the
  same bartender at 1 px/f, then leaves his seat.
- A full drink that meets no thirsty patron reaches the far end and the other bartender takes it off the counter
  (no score, no penalty, a "THANKS!" pop): a wasted throw costs only time.
- Two drinks going opposite ways on one bar pass each other.
- Your empties: catch them as always (on that bar, overlapping); one reaching x 152 breaks and costs a life
  (3 lives; 0 = you lose). Dregs's empties: he catches them if he gets there; one he misses breaks at his end:
  Dregs -1 point and he slips (60 frames out of action).
- At most 4 mugs per bar (both directions, sliding and held). A drink that does not fit stays in the bartender's
  hand (he keeps the full mug under the spout until there is room): nothing is lost silently.
- Win: you reach 20 first. Lose: Dregs reaches 20, or your lives run out. A loss restarts the Pour-Off only.
- Length: ~40 patrons served between the two of you, one every ~45 frames on average: 40-60 s.

Dregs (the CPU), one decision at a time, all from the seeded RNG:
1. If one of his empties will reach his end within 40 frames, switch to that bar and wait to catch it (10-frame
   reaction delay; he can miss when two arrive close together on different bars).
2. Otherwise pick the thirsty patron with the shortest slide from his spout that none of his drinks in flight is
   already heading for. One pick in 8 goes to a contested seat (one the player is likely to take) or to a patron
   about to leave: comic waste.
3. Think delay 30 frames at 0 points, falling to 18 at 15 points; rubber band: +8 frames if he leads by 4 or more,
   -6 if he trails by 4 or more. Then fill (16 frames) and slide.
Tuning target: a player who keeps a steady rhythm wins by 3-6; a player who ignores empties loses. All knobs are in
one table (`po_tune`), exposed to tests.

Why fun and fair: Tapper's core loop turned into a race, against a visible, comic opponent with readable habits.
The geometry is mirrored, so neither side has a shorter slide to the same seat. Contested seats are a real decision
(you win the race only if your drink arrives first). Spam is limited by the fill time, the 4-per-bar cap and the
empties every serve sends back. Dregs stays a comic rival: his mistakes are slapstick (slips, waving at the wrong
patron), and the finale's apology follows the race whoever wins. Luck: seat choice is random, the same for both.

Hardware:

```
    01234567890123456789
 00 .999999..UUU.HHHHHHH    score, lives, "YOU 12 DG 10" (HUD glyphs)
 01 ssssssssssssssssssss    festival stage (the restored spigot on its fountain) or the saloon's
 02 ssssssssssssssssssss
 03 ssssssssssssssssssss
 04 ssssssssssssssssssss
 05 KKsDDppwwppwwppPPsKK    bar 0: K kegs (left one mirrored), s spouts, D Dregs (OBJ), P you (OBJ)
 06 KKsDDppwwppwwppPPsKK    p seated patrons (BG) on seats at cols 5-6, 9-10, 13-14
 07 KKcDDccccccccccPPcKK
 08 KKswwppwwwwwwppwwsKK    bar 1
 09 KKswwppwwwwwwppwwsKK
 10 KKccccccccccccccccKK
 11 KKswwwwwwppwwwwwwsKK    bar 2
 12 KKswwwwwwppwwwwwwsKK
 13 KKccccccccccccccccKK
 14 KKswwppwwppwwwwwwsKK    bar 3
 15 KKswwppwwppwwwwwwsKK
 16 KKccccccccccccccccKK
 17 ffffffffffffffffffff
```

Dregs stands at cols 3-4 (x 24, the mirror of the player's TAP_X 120), his spout is col 2, his keg cols 0-1.

- Worst line: Spigoteer 2 + his fill 1 + Dregs 2 + his fill 1 + 4 mugs (sliding or held) = 10. No lifts: seated
  patrons never overlap (seats 32 px apart). OAM: 4 + 4 + 2 fills + 16 mugs max = 26.
- Tiles: patrons need only the shift-0 pose and one sway shift (2 px) per variant: 3 x 12 = 36 BG (the bar game's
  144-tile shifted set is not loaded). Dregs 5 frames (idle, fill, slide, catch, slip) x 8 = 40 OBJ at ids >= 128
  (free because of the small patron set). Mirrored keg and spout for the left end: ~8 BG (DMG cannot flip BG tiles;
  CGB could use the X-flip attribute, but one path for both is simpler). Score glyphs exist.
- CGB: BG 0 bar, 1 HUD, 2-4 the three patron variants, 5-6 stage, 7 both kegs; OBJ 0 Spigoteer, 1-2 drinks, 3 Dregs,
  4 Dregs's second palette if his art needs it, 5 effects ("THANKS!", slip stars).
- DMG: Dregs's sprite is mirrored art of a different silhouette (lanky, crooked bow tie), not just a palette swap.
- WRAM ~130 B in the `mg` union: 12 seats x 3 B, 16 mugs x 3 B (x, bar + direction + state, owner), Dregs's AI
  ~16 B, scores, timers.
- ROM ~5 KB code (its own bartender update for two bartenders, its own mug and seat rules) + ~2 KB art.

Crowd: the finale should show the whole tour. Recommended: one variant from each of three groups (cowboy A, chef
B, alien C, say), loaded per variant (a small loader change: `patron_load` takes a group per variant). The owner
picks the three (open question 5).

Art: Dregs 16x24 x 5 (idle, filling, sliding, catching, slipping), in the bartender's frame layout and mirrored
(faces right); mirrored keg + spout; the festival stage (20x4, <= 24 tiles, the restored Golden Spigot on the
fountain, bunting) if the owner wants a new stage, otherwise the saloon's; "THANKS!" pop 16x8; score HUD layout.

Plugs into: a new module `src/pouroff.c` (banked) with its own frame function, using `draw_bartender`'s layout for
both bartenders (a second copy for Dregs), venue_backdrop / draw_venue, the drink tiles of the chosen venue, and the
mg framework's result window. It does not touch patrons.c, mugs.c or lift.c (different rules, fewer objects: a
separate module is cheaper and safer than special cases in the hot code). The player's controls follow play_frame's
rules (move, snap to the tap, hold A to fill, release to slide); play_frame's input part becomes a function both
can call (ROM0, no size change) or pouroff.c keeps a copy (~200 B, banked). Test hooks: `po_you`, `po_dregs`,
`po_seat[12]`, `po_mug_x[16]`, `po_dregs_bar`, `po_dregs_state`, `po_think`, `po_tune[]`. Tests: mirrored travel
times equal; first-arrival scoring on a contested seat; a pass-through full is taken by the other bartender; the
4-mug cap holds the drink in hand; Dregs catches an empty that reaches his end when he is there, slips when not; a
scripted "perfect" player wins and an idle player loses.

Story fit: suggested split of FINALE into FINALE_A (the pieces click, Dregs challenges), the Pour-Off, FINALE_B
(the apology and the glass of water, unchanged). New pages, after THE GOLDEN SPIGOT SHONE ONCE MORE!:

    DREGS          HOLD IT! WHO / POURS FIRST? I / SAY: A POUR-OFF!
    SPIGOTEER      FIRST TO 20 / SERVES. YOU'RE ON, / DREGS.

and FINALE_B opens with:

    DREGS          I LOST FAIR AND / SQUARE. SORRY I / BROKE IT.

followed by the existing YOU POUR FIRST. YOU EARNED IT. (its first line SORRY I BROKE IT. then repeats and should
be dropped from that page).

**Built** 2026-10-12: in the saloon (owner Q5, no festival stage), FINALE_A / the Pour-Off / FINALE_B as above (docs/story.md, "proposed, pending owner
approval" for the three new pages), Dregs's sprite set a PROPOSAL pending owner approval; the crowd is the saloon's cowboy and cowgirl plus a chef
from the bistro. See PLAN.md "Pour-Off as built" for the numbers that differ from this section (think delays 27 / 16, the 28 s game).

## 6. Build order, sizes and risks

Sizes: S = up to a day of agent work with tests, M = a few days, L = a week or more. Art proposals for each item go
to the owner first; code can start on placeholder art (generated silhouettes, as the story portraits did).

| step | what | size | ROM (approx.) | risks |
|---|---|---|---|---|
| 1 ✅ | Segment flow in story.c (OPEN / HAPPY / MINI / LAST / BOSS), SRAM v4 (seg byte, migration), GS_MINI, mg.c framework (intro banner, count-in, timer, result window, medals), `mg_say` in ROM0, the `mg` union over story's backdrop buffer; one stub game | M | 3 KB + ~80 B ROM0 | **Built** (PLAN.md "Mini-game framework as built"; the segment flow and SRAM v4 came with the story shifts): ~3.1 KB in bank 6, 57 B ROM0, +72 B WRAM; stub game GREEN LIGHT; the story's mini slots stay NOT_BUILT until real games exist |
| 2 ✅ | Boss engine + Big Tex (placeholder art): ROM0 hooks (catch, spawn mask, stamp, GS hooks), boss tiles / palettes at load, HUD meter, topper with the line-count guard, reset after a life, TRY AGAIN, tests | L | 4 KB + ~205 B ROM0 | **Built** (PLAN.md "Boss engine as built"): 3.6 KB (boss.c + art), 101 B ROM0, +42 B WRAM; the saloon's boss slot is on in the story, the others stay NOT_BUILT; the topper is OAM 28 (OAM 26 became the perfect pour's cue), the game-state hooks are banked (story.c, pour.c), Tex's art is a placeholder |
| 3 | Quick Draw ✅, Order Up!, Battery Sort (simple, mostly BG) | S each | 3 KB each | Order Up!'s portrait loader from another bank (LCD off, banked accessor: fine). **Quick Draw built** 2026-10-11 with the BONUS > MINI GAMES list (PLAN.md "Quick Draw and BONUS > MINI GAMES as built") |
| 4 | Bosses without movement: Sasquatch ✅ (S, `empty_fast`), Critic ✅ (M, fill window + `MUG_RETURN`), Yeti ✅ (M, `mug_fast` + counter writer), Leo (M, roar walks the patron list), Sumo (M, beat from music.c) | S-M each | 1-1.5 KB each | the Critic changes main.c's fill timer (ROM0, hot input path): measure; Leo's roar must keep fair empties (test with 4 drinkers). **Wave 1 built** 2026-10-12 (PLAN.md "Boss hooks as built" and the three bosses after it): one banked file per boss through boss.c's hook table; the fast mugs and `MUG_RETURN` are banked (boss.c boss_mugs), not ROM0 masks; the Critic uses the story's perfect pour (12 frames long in his fight), so main.c's fill timer is unchanged; ROM0 cost 0 B |
| 5 | Monkey Business (M, scheduler), Marshmallow Drop (M) | M | 3 KB each | the reachability scheduler needs a seed sweep test |
| 6 | Bosses that move between bars: Mascot (M), Prototype (M-L, cycle + returns + conveyor tiles), Mothership (L, phase 2 with patrons, 23-tile budget) | M-L | 1.5-2 KB each | landing must scare regulars through the existing leave path without score; the Mothership's tile budget is exact |
| 7 | Log Roll (M), T-Shirt Cannon (M-L, landing table tool), Asteroid Delivery (M-L, feel) | M-L | 3-4 KB each | physics feel needs owner playtests; the cannon's reachability table must pass for every wind |
| 8 | Taiko Pour | L | 3 KB + chart | sync to hUGEDriver rows (`song_pos`), chart tool, the music-off rule |
| 9 ✅ | Pour-Off | L | 7 KB | second bartender and mirrored rules in a separate module; AI tuning; a mixed-group patron loader. **Built** 2026-10-12 in the saloon (owner Q5), ~10 KB in one new bank (PLAN.md "Pour-Off as built") |
| 10 | Practice menu (title row, chapter / segment list, best scores in SRAM) | M | 2 KB | title.c's bank is nearly full: the practice screen gets its own bank; the title menu's rows move (golden title / title_continue replaced on purpose) |
| 11 | The Chrome Cow (the 10-venue engine change and the mosh pit twist are built, 2026-10-11: ~120 B ROM0 for the hooks, measured): Milk Run (M, 4.10: column streamer, window HUD), Duke (M, 3.12: idle / rev / lurch, chord regulars) | M | ~5 KB | Milk Run is the first scrolling mini-game |

Order rationale: the framework and the boss engine carry everything else and hold the real risks (ROM0, VRAM,
line budgets), so they go first with the simplest content (Big Tex, the BG-only mini-games). Physics and rhythm
games go late because they need owner playtests to tune.

Totals (nine venues; The Chrome Cow's Duke and Milk Run add ~5 KB): ~60 KB of new code and data (ROM 128 KB -> 256 KB, automatic), ~205 B + ~80 B of ROM0 (of 1708 B), WRAM:
boss ~40 B new, everything else in the existing 520 B buffer.

Project-wide risks:
- **Art volume**: 10 bosses (~45 tiles each) + 10 mini-game sets + Dregs + the festival stage. Proposals first, so
  art is on the critical path. Placeholder art (silhouettes in the right palettes) lets code and tests proceed.
- **Goldens**: new goldens per mini-game and boss (add freely). The title menu change replaces `title` /
  `title_continue` goldens on purpose (say so in that commit).
- **Performance**: a boss fight has fewer regulars (3 bars), no show and no tips, so it is lighter than the
  realistic peak; test_perf gains a boss scenario per moving boss (Mascot, Prototype, Mothership phase 2).
- **The 10-per-line rule**: every mini-game screen above has a counted worst line; tests assert <= 10 per line every
  frame (the test_perf helper), in each mini-game and boss test.

## 7. Suggested story text (for docs/story.md; not applied)

All lines are <= 18 characters in the allowed character set, 3 lines a page, existing speakers only. Each adds one
page to the named scene; place it before the scene's last page unless noted.

| scene | speaker | page |
|---|---|---|
| PRE_SALOON | SADIE | AND IF THE KID / CHALLENGES YOU, / DRAW FAST! |
| PRE_SALOON | SADIE | WATCH FOR BIG / TEX. HE DRINKS / A WHOLE BARREL. |
| PRE_STADIUM | COACH | IN THE STRETCH, / FIRE SHIRTS INTO / THE WAVE! |
| PRE_STADIUM | COACH | AND WATCH OUR / MASCOT. HE JUMPS / BARS FOR FUN. |
| PRE_LUMBER | JUNE | LUNCH IS LOG / ROLLING. YOUR / PARTNER IS... UH. |
| POST_LUMBER | NARRATOR | THE SASQUATCH / DRANK 12 COFFEES / IN 12 SECONDS. (before HANDED IT OVER) |
| PRE_BISTRO | COLBY | ORDER UP! REPEAT / MY ORDERS. NO / CHEESY MISTAKES. |
| PRE_BISTRO | COLBY | TONIGHT A FOOD / CRITIC VISITS. / POUR PERFECTLY! |
| PRE_IGLOO | AURORA | MARSHMALLOWS GO / IN EVERY MUG. / THREE IS PERFECT. |
| PRE_IGLOO | AURORA | OUR YETI IS A / DEAR. BUT HIS / BREATH IS ICY. |
| PRE_ROBOT | MANAGER-BOT | SORT CHARGED / LEFT. DEAD RIGHT. / DO NOT MIX. |
| PRE_ROBOT | MANAGER-BOT | WARNING: THE / PROTOTYPE. GREEN: / FEED IT. RED: NO. |
| PRE_BIKER (PROPOSAL) | GRANNY | TAKE MY BIKE AND / RUN THE MILK. MIND / THE POTHOLES! |
| PRE_BIKER (PROPOSAL) | GRANNY | DUKE'S GANG RIDES / IN TONIGHT. HE / WANTS A BIG SHAKE. |
| PRE_TEAHOUSE | HANA | THE DRUM SETS / THE POUR. A AND B / ON THE BEAT. |
| PRE_TEAHOUSE | HANA | THE CHAMPION / IS THIRSTY. KEEP / THE TEA FLOWING. |
| PRE_SPACE | ZIZZ | DELIVER BEAKERS / PAST THE ROCKS. / GENTLY! |
| PRE_SPACE | ZIZZ | MY MOTHERSHIP IS / PARCHED. IT SPLITS / WHEN IT IS FULL. |
| PRE_ZOO | KIKI | LEO WANTS A / DRINK FIRST. HE / ROARS. STAY CALM. |
| FINALE (split) | DREGS, SPIGOTEER | see section 5 |

Boss intro banners (the goal banner's two lines, HUD glyphs only, <= 20 characters, no punctuation):

| boss | line 1 | line 2 |
|---|---|---|
| Big Tex | BIG TEX RIDES IN | QUENCH HIM 8 MUGS |
| Mascot | THE MASCOT JUMPS | FOLLOW HIM 10 MUGS |
| Sasquatch | NO SUCH THING | 12 COFFEES FAST |
| Food Critic | THE CRITIC DINES | PERFECT POURS ONLY |
| Yeti | THE YETI IS COLD | 12 COCOAS ON ICE |
| Prototype | GREEN MEANS GO | RED MEANS STOP |
| Duke (PROPOSAL) | DUKE AND HIS GANG | 12 GLASSES OF MILK |
| Sumo | THE CHAMPION | PUSH HIM OUT |
| Mothership | THE MOTHERSHIP | FILL IT THEN SPLIT |
| Leo | LEO THE LION | 14 COCONUTS NO FEAR |

The chapters table in story.md would gain two columns (mini-game, boss); gen_story.py's CHAPTERS check would need the
same change when the segment flow is built.

## 8. Open questions for the owner

**Owner's answers (2026-10-10):**
- Q1: mini-games do not gate the story; the medal idea is approved.
- Q2: undecided; the owner decides after playing them all.
- Q4: with MUSIC OFF, Taiko Pour stays silent (no tune), but it needs a clear visual timing cue: the beat flash on
  the lane borders, a drum that pulses on every beat and the 4-beat count-in shown on screen. Sync must not depend
  on hearing the tune (run the driver muted so `song_pos` keeps counting, or an equivalent frame clock).
- Q5: the Pour-Off is in the saloon (no new festival stage).
- Q7: yes, Practice gets a HARD toggle.
- Q8: the stranger in Quick Draw is the Sarsaparilla Kid (the new character; Dregs keeps his "always one scene
  late" gag).
- Q10: regulars keep coming during boss fights, more slowly.
- Lives (owner, supersedes Q3 / Q9 and "retry only the shift"): story mode gives **3 lives per venue**. They carry
  through Opening, Happy hour, the mini-game, Last call and the boss; they are not refilled between shifts. A gold
  medal in the venue's mini-game earns +1 life. Losing the last life restarts the venue from its Opening shift
  (goal banner, 3 lives, no PRE scene). Breaking a venue's strict rule (stadium: a fan reaches the tap; teahouse: a
  broken cup) costs 2 lives instead of 1. CONTINUE after quitting mid-venue starts that venue over (lives are not
  saved); shifts reached stay unlocked for Practice. A boss keeps his damage after a lost life; a venue restart
  starts him over. Arcade is unchanged: 3 lives for the whole run.
- Q6 (owner): the perfect pour is part of pouring in **story mode everywhere** (every shift, mini-game excepted,
  and every boss), not only the Critic's fight. Arcade pouring is unchanged. Releasing A during the sparkle window
  serves a PERFECT drink worth extra points (proposal: the serve score doubled for that drink, with a small
  "PERFECT" cue); held past it the foam runs over (no bonus); a carried drink is never perfect. Regulars accept any
  drink; only the Food Critic sends a sloppy one back. Needs a sparkle and an overflow frame for each venue's drink
  (art proposals first). Build it after the story lives change (both touch main.c).

1. **Do mini-games gate the story?** Recommendation: no. Any result continues; medals give points and a gold medal
   gives one extra life in that chapter's boss fight. (The alternative, retry until bronze, makes a weak mini-game
   a wall.)
2. **New mini-games in arcade?** You said the three existing bonus rounds stay in arcade. Should the nine (ten) new ones
   also join arcade's bonus rotation (after every even level), or stay story / practice only? Recommendation: story
   and practice only for now.
3. **Teahouse rule in the boss fight**: chapter 7's goal (chapter 8's with The Chrome Cow) is "not one broken cup". Should a broken cup also fail the
   Sumo fight? Recommendation: no, lives only (bosses play by the same rule everywhere).
4. **Taiko Pour with MUSIC OFF**: play the tune anyway during that game (recommended), or a click track?
5. **Pour-Off setting and crowd**: a new Fizzwater festival stage (one more stage art job) or the saloon? Which
   three patrons make the festival crowd (one variant from each of three groups)?
6. **The Critic's pour window**: 12 frames proposed. Should the sparkle / overflow frames show only in that fight
   (recommended) or become part of pouring everywhere (a small new skill in the whole game)?
7. **Practice difficulty**: one setting (the story's) for every mini-game and boss, or a HARD toggle in practice
   for replay value?
8. **The stranger in Quick Draw**: the Sarsaparilla Kid (new character, recommended), or Dregs in a fake mustache
   (breaks his "always one scene late" gag)?
9. **Boss lives**: 3 per attempt like the chapter goals (recommended), plus the gold-medal bonus life?
10. **Regulars during bosses**: they keep coming (slower) on the other bars (recommended: the boss alone is too
    easy), or boss fights are one-on-one?

PROPOSAL (2026-10-10), new questions for The Chrome Cow:

**Owner's answers (2026-10-11):**
- The name **The Chrome Cow** is final.
- Q11: the mosh pit is on in Last call too ("sure, we'll try it"): Happy hour and Last call (limit x 72 there).
- Q12: the owner wants "fast punky or shanty": the tune is **"Drunken Sailor"** (traditional sea shanty, public
  domain), played fast and punky; a melody spec in docs/music_specs.md like the others when the venue is built.
  Last call plays it 15 % faster ("the band plays faster").
- Title menu (not a numbered question): PLAY / BONUS / SETTINGS, each a submenu. PLAY: [CONTINUE] / STORY / ARCADE;
  BONUS: SOUNDTRACK (PRACTICE planned as its second item); SETTINGS: MUSIC ON-OFF. MUSIC stays a setting (it does
  not move into BONUS) and BONUS opens a submenu, no longer the soundtrack directly (PLAN.md "Title submenus as
  built").

11. **Mosh pit in Last call?** Answered (owner, 2026-10-11): on in Last call too (the shove then stops 48 px from
    the tap instead of 32).
12. **The Chrome Cow's tune**: answered (owner, 2026-10-11): "Drunken Sailor" (traditional sea shanty, public
    domain), fast and punky. Last call plays it 15 % faster ("the band plays faster").
13. **Saves past chapter 6** when the 10th venue ships: a save that had reached the teahouse or later goes back to
    the start of The Chrome Cow (recommended: the story never skips the drip tray, and the finale's "ten pieces"
    stays true), or keeps its count and skips the new chapter? Details in docs/venue10_impact.md.
14. **Boss ramp with the space lounge last**: the Mothership becomes the last boss and Leo the 9th. Recommended:
    the Mothership's phase 1 meter 6 -> 8 (8 + 3 x 2 = 14 drinks, the most) and Leo's 14 -> 12, so the last fight
    stays the biggest; or keep both as designed? Asteroid Delivery becomes the last mini-game (its medal thresholds
    stay; it is already the hardest to steer).

## 9. Venue twists: the mosh pit (The Chrome Cow, chapter 7)

Owner-approved; BUILT 2026-10-11 (src/mosh.c, the hooks in src/patrons.c, tests/test_twists.py; on in chapter 7's
Happy hour and Last call). The venue twists are M11b part 2 (docs/story.md "Chapters": each changes one parameter or
adds one small behaviour). This is the only one designed in this document, because it is
the one deliberate exception to a rule the whole engine relies on: everywhere else patrons overlap and never shove
(M13b).

The owner's words: "a [patron] pushes back into another one [and that one] gets shoved forward. You have to clear
the back one first while the front one drinks."

### 9.1 How patrons move today (src/patrons.c)

- A walker's `patron_x` (his left edge, 0-127) grows toward the tap at `patron_speed` (1/256 px a frame; hurried
  walkers 1.5x). At `PATRON_FAR_X` 120 he has reached the tap: `walker_pixel` removes him and calls `lose_life()`.
  Walkers pass each other and drinkers (they overlap); a step waits only if it would put three patrons on one tile
  column (`col_scan`).
- A full mug is caught by the bar's rightmost catcher (`catch_full`): a walker, or a drinker who has finished
  (DRINK_WAIT / DRINK_WINDUP). A drinker still in DRINK_MIN (his first DRINK_FRAMES, 90) lets a mug slide past him
  to whoever is behind.
- `caught()` makes him PATRON_PUSHED with `patron_aux` = `push_for(p)` (level.c): pushback_px (32 px at pushback_cols 4,
  the same for every drink), all of him off the screen (x + 16) to serve, else stopped on the screen at ENTRY_X 16 at the
  latest, and from level 2 a quarter or half push for early drinkers: `push_px` moves him 1 px a frame toward the left end,
  through anyone in his way (lift.c lifts one over the other). When the push is used up he drinks where he stands
  (`start_drinking`); a push that carries him off serves him out, counted (score, tip) when he has left the screen.
- After DRINK_FRAMES he sends the empty when the fair-empties schedule allows, then walks on.

### 9.2 The rule

- **Bump**: a PUSHED patron P (moving left) bumps a walker Q of the same bar behind him when, after P's 1 px step,
  0 <= P.x - Q.x <= MOSH_CONTACT = 12 px (their 16 px figures overlap by 4 px: visibly touching). Only a plain
  walker can be bumped: Q walking, fully on the screen (`patron_aux` 0, x >= ENTRY_X), not watching the show
  (`patron_dist` 0) and not being shoved already. Drinkers, pushed and leaving patrons are never bumped: a drinker is
  planted, a pushed one is already moving.
- **Shove**: Q goes forward, toward the tap, SHOVE_PX = 16 px (one figure's width) at 2 px a frame (8 frames, about
  17 times a chapter-7 walker's ~0.12 px/f: unmistakable), then staggers on the spot for SHOVE_STAGGER = 30 frames before
  walking on at his own speed. Net, a shove gains him about 16 - 30 x 0.12 = 12 px over not being shoved, roughly 100
  frames of walking.
- **One shove per bump**: P shoves at most one patron per push (the first he bumps): a DONE bit in `patron_mosh[P]`,
  cleared when `caught()` starts a push and set by the shove (or by a jostle, below). Q cannot be bumped again while
  his shove or stagger runs. A shove is not a push: Q moving forward bumps nobody, so there are no chains. P is not
  slowed: he finishes his push and drinks as usual.
- **Where a shove stops**: (a) Q's left edge never passes MOSH_LIMIT: x 88 in Happy hour, x 72 in Last call (32 / 48
  px short of PATRON_FAR_X). A Q already at or past the limit is only jostled: the bump cue plays, he does not move,
  and it still counts as P's one bump. (b) A shove step obeys `walker_pixel`'s column rule: a step that would put
  three patrons on one tile column ends the shove there (the rest is dropped). (c) The stagger holds Q for 30 frames
  after every shove.
- **The fairness rule: a shove never costs a life by itself.** From the limit a shoved patron still has 32 px (48 in
  Last call) to walk: at chapter 7's speeds (a level-7 row, ~0.12 px/f) about 270 frames in Happy hour (180 for a
  hurried walker) and at least 240 in Last call (+15 % speed, 48 px, hurried), plus the 30-frame stagger. A full glass from the spout reaches a
  patron at the limit in 16 frames ((136 - 104) / 2). Every shoved patron can be served with seconds to spare.
- Untouched: the fair-empties schedule (a shove moves a walker, never a drinker, so no empty's timing changes), the
  served count, the score and tips (a shove is not a serve), and the lives rule.

The play it creates (the owner's "clear the back one first while the front one drinks"): serving the front patron F
when Q walks close behind him (within F's push plus 12 px) shoves Q forward. So serve F early, before Q catches up,
or, once F is drinking (his first 90 frames let your next glass slide past him), serve Q first: Q is pushed back,
away from F, and when F walks on and takes his second glass (a 64 px push) nobody is left behind him to shove.

### 9.3 How it reads

Patrons are BG figures, and a new patron pose would cost 48 tiles a variant (8 pre-shifts x 6), more than the venue
has, so the cue is motion, sound and one BG mark, with no sprite added on any line (lift.c's per-line estimate is
unchanged):
- the shove itself: 16 px in 8 frames, among walkers that move 1 px every ~8 frames;
- a **milk splash on the counter** at the bump: the counter-row tile under the contact column swaps to a splash tile
  for 30 frames (the counter-row writer the Yeti uses, 3.7; on DMG white drops on the counter, readable by shape);
- a short thud plus a "hey!" noise blip on channel 4;
- the venue sells it: mohawks and studs, and Granny names it in the PRE scene (AND MIND THE MOSH PIT. SERVE THE BACK
  ONES FIRST.).

### 9.4 Where it applies

| shift | mosh pit |
|---|---|
| Opening shift | off: the venue is taught first |
| Happy hour | **on**: the chapter's twist, as in every venue |
| Last call | **on** (limit x 72; owner, 2026-10-11, question 11) |
| mini-game, boss | off: bosses play by the same rules everywhere (Duke's gang arrives in chords instead) |
| arcade | off: arcade keeps the plain rules, as with every twist |

Last call's chord pattern sends its three patrons to three different bars, so the pattern never stacks two arrivals
on one bar: bunching on a bar comes only from how the player serves.

### 9.5 Engine (as designed; as built: see the end of this section)

- Twist id `TWIST_MOSH` in gen_story's per-shift twist byte (0 for every shift today) -> `story_twist`; story.c sets
  a WRAM flag `mosh_on` and `mosh_limit` (88 / 72) at the shift start; every other shift, arcade and the boss fight
  clear it.
- patrons.c (ROM0): in `push_px(p)`, after the step, when `mosh_on` and P's DONE bit is clear, scan `bar_list[b]`
  (short: 1-4 entries) for a bumpable walker with 0 <= P.x - Q.x <= 12 (~45 B). In `walking_step(p)`: while
  `patron_shove[p]` > 0 move 2 px (with the col_scan check) instead of walking, then count `patron_stag[p]` down
  (~40 B). `caught()` clears the DONE bit (~6 B). About 90 B of ROM0 in all; with `mosh_on` 0 the only cost is one
  test in `push_px`.
- WRAM: `patron_shove[16]`, `patron_stag[16]`, `patron_mosh[16]` (48 B; or packed into one array). Test hooks:
  `mosh_on`, `mosh_limit`, `mosh_count` (shoves this shift), `patron_shove[]`, `patron_stag[]`.
- The counter splash: one tile id in The Chrome Cow's bar set (its 36-id venue pool must leave one free), queued
  with `vq_add` at the bump and put back after 30 frames.
- Lifts: Q passes through P during the shove (P goes left, Q right). That is the crossing the M13b chooser already
  handles for a pushed patron sliding through a walker; the column rule keeps the lift budget.
- Perf: the scan only runs for pushed patrons while `mosh_on` (a few a frame at most); test_perf gains a mosh
  scenario (bumps on all four bars at once).

As built (2026-10-11): as above, with these choices. The twist is a bit field in goal_t.twist (TWIST_MOSH; also
TWIST_FAST_TUNE, the band playing faster in the Last call) with the shift's limit in goal_t.pad, both from gen_story's
TWISTS / MOSH_LIMIT; story.c calls mosh_set at every shift start (0 in the Opening, a boss fight and arcade). Of
several walkers in reach, the nearest (highest x) is bumped. The shove runs in walking_step (also during the intro
delay); ROM0 hooks: walking_step, push_px, caught, init_patron and update_patrons (the splash timer), about 120 B in
all, each behind one test of mosh_on. The cue: the splash tile is assets/art/splash/biker.txt (the owner-approved
option B, 2026-10-11), gen_art adds it to the venue's bar set (venue.splash_tile, 34 of the 36 pool
ids); the sound is the existing channel-4 rattle (SFX_SHAKE: sfx_req had no ninth bit then; it is 16 bits since the extra-life cue, SFX_EXTRA, so the mosh pit could
get its own effect). Perf: two moshes at once keep
every frame on time; four bars at once (more than one bartender can serve) run some frames late (test_twists).

### 9.6 Tests (tests/test_twists.py, as built)

1. Bump and shove: bar 1, Q walking at x 40, P at x 60 catches a glass (push 32): when P.x - Q.x <= 12, Q.x grows
   by exactly 16 in 8 frames, holds for 30 frames, then walks on; P finishes his push and drinks.
2. One shove per bump: P and Q overlap for several frames; Q moves 16 px in total, once.
3. One shove per push: two walkers behind P (x 44 and x 30): only the first bumped is shoved; P passes the second.
4. No chains: Q's shove carries him over a walker R ahead of him; R does not move.
5. The limit: Q at x 80 stops at 88; Q at x 90 does not move (jostle only, P's bump used up); in Last call the
   limit is 72.
6. The fairness sweep: for every P start x 32-104 and Q x 16..P.x in steps of 4 on one bar, after one serve of P
   and one of Q, no life is lost in the next 300 frames, and Q never passes the limit.
7. Never bumped: drinkers, pushed, leaving, entering (`patron_aux` > 0) and show-distracted patrons.
8. Gating: off in the Opening shift, in arcade and in the boss fight; on in Happy hour and (once approved) Last
   call.
9. During every shove `col_scan` stays below 3, and every line keeps <= 10 objects every frame in a scripted mosh on
   all four bars (the test_perf helper).
10. The counter splash: the tile under the contact column is the splash for 30 frames, then the bar's own again.
11. Fair empties: `next_arrival` is the same with and without a shove in the same scripted scene.
12. Score, served and tips are the same with and without shoves.

## Practice difficulty (2026-10-15, owner: "put in the selection but make every difficulty level the same right now")

BONUS > MINI GAMES offers EASY / NORMAL / HARD for every game on the list (the ten venue games, the three bonus rounds; the debug stub too).
LEFT and RIGHT cycle them (RIGHT: EASY, NORMAL, HARD, round; SELECT goes forward too); the header's right side names the mode ("MINI GAMES  HARD"),
the info lines read "<MODE> BEST GOLD" / "<MODE> NO MEDAL YET" and the keys line "A GO B BACK L R MODE", and the list's medal column is that mode's.
The mode is chosen once for the whole list and outlasts a game and a visit to the title. A game reads it as `MG_DIFF` (mg.h: two bits of
`mg_mode`, 0 NORMAL, 1 HARD, 2 EASY; no WRAM of its own); STORY and ARCADE pass `MG_STORY` and always play NORMAL.
Every game plays exactly the same in the three modes for now (tests/test_difficulty.py runs each game 420 frames from a fixed seed and keys in
each mode and compares its whole state). Milk Run's HARD tuning (start 2.0 px, floor 1.75, 3 crates a bump) and the stub's are kept as named
constants but switched off (`MR_IS_HARD`, `STUB_IS_HARD` are 0; make them `(MG_DIFF == MG_D_HARD)` to bring them back). Medal thresholds are one
table for all three modes (mg.c `medal_tbl[MG_DIFF]`, three pointers to the same table); a mode that gets its own thresholds gets its own table;
the games with their own medal function read `MG_DIFF` there.
Saving: a medal per game per mode. The ten games' byte in the "MGP2" block holds NORMAL in bits 0-1, HARD in 2-3, EASY in 4-5 (an older save has
bits 4-5 clear: its medals are NORMAL's, EASY has none; a byte above 63 makes the block bad: nothing loads). The bonus rounds keep NORMAL in
"MGB1" (byte 5) and EASY / HARD in a new six-byte block "MD" at 0x7A (the last gap before the tables: magic, EASY medals, HARD medals, checksum,
complement; a block that does not check out, as in every older save, reads as no EASY or HARD medals and touches nothing else).
