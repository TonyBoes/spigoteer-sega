# Tapper GB: plan

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
  shifted by 0/2/4/6 px so they move smoothly in 2 px steps by swapping
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
- Bartender always faces left (toward the bar) while filling.
- Empties slide back slower: 1 -> 0.5 px/frame (full mugs stay 2).
- Bartender walks slower (2 -> 1.5 px/frame) with a calmer cycle: walk1, idle, walk2, idle.
- Counter runs all the way to the door (cols 0-1); the door shrinks to the wall rows, so patrons never show their missing legs.
- Patrons pre-shifted at every pixel (8 shifts, 144 BG tiles per group) instead of 2 px steps.
- Art (proposals for approval first): bartender mustache; patrons in 3/4 view facing right.
