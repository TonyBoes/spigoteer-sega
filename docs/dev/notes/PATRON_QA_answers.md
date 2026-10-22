# Patron questions: mug, back views, title screen

Answers from the code (main `da25974`): `src/mugs.c` (held-mug poses), `assets/approved/venues/saloon_drink.txt` (the mug
art), `src/mirror.c`, `src/classic.c`, `src/title.c`, `tools/gen_art.py` and `tests/test_cowboy_back.py`.

The mug shapes below are the **saloon's** mug. Every venue has its own drink art, but the sprite box and the positions are
the same for all.

## 1. The held mug

**The sprite.** The mug is one **8×16** sprite, but its art fills only part of that box (at most 8 px wide and 10 rows
tall). Its position is set relative to the patron's **drawn** position, so:
- it moves with him when he sways (the 2 px drinking sway) or is pushed;
- on bars where patrons come from the right, it is mirrored onto his left half.

**How it moves over time.** The pose changes every 4 frames of drinking.

| Phase | Mug | Covers in the 16×16 picture |
|---|---|---|
| Raising it (first ~12 frames) | upright, full | cols 9–15, rising from rows 7–15 to rows 4–13 |
| **Drinking**: most of the time, including the sipping loop while he waits to send the empty | **tilted at the mouth** | **rows 5–12, cols 8–15** |
| Wind-up before sending the empty | upright, empty, lowered and **drawn back to dx 4** | rows 8–15, **cols 4–11**; then swung forward to cols 10–15, and 14–15 |
| Carried while pushed back | upright, full, at the hand | rows 8–15, cols 9–15 |

**Exact shapes.** `M` marks a mug pixel. Row numbers are the patron picture's rows (0 = top).

Face height. This is the drinking pose, and the one that matters most. The mug is tilted, so it covers less than a full
8×8 block:
```
 5 ..........MM....
 6 ..........MMM.MM
 7 .........MMMMM.M
 8 ........MMMMMMMM
 9 .........MMMMMMM
10 ..........MMMMM.
11 ...........MMM..
12 ............M...
```

Hand height, carried while he is pushed back:
```
 8 ..........M.M.M.
 9 .........MMMMMM.
10 .........MMMMMM.
11 .........MMMMMMM
12 .........MMMMMM.
13 .........MMMMMM.
14 .........MMMMMM.
15 .........MMMMMMM
```

Wind-up, briefly over the **middle** of him:
```
 8 ....MMMMMM......
 9 ....MMMMMM......
10 ....MMMMMM......
11 ....MMMMMMMM....
12 ....MMMMMM.M....
13 ....MMMMMM.M....
14 ....MMMMMM.M....
15 ....MMMMMMMM....
```

**Against the assumption** "8 px wide, covering x 8–15 from about row 4 to row 11 at face height":
- The main pose is close, but it is **rows 5–12**.
- Only row 8 is the full 8 px wide; the edges are diagonal.
- So the eye area at about cols 9–11, rows 5–7 is only partly covered.
- The left half (cols 0–7) is never covered while drinking, only during the short wind-up.

## 2. Back views

- **Only the saloon's variant A must be symmetric.** This was the owner's request, and `tests/test_cowboy_back.py` enforces
  it: a mirror image about column 8, with column 0 empty. B and C have no such rule.
- **Yes, the saloon appears on mixed-direction levels.** CLASSIC wave 2's levels 14 and 15 are saloon levels with
  alternating bars (R L R L and L R L R), and from level 27 on those rows repeat.
- **On DMG with mixed directions, back views are not mirrored.** One back view serves both directions (`src/mirror.c`,
  `mir_bswap`). On CGB the flip handles it.
- **So an asymmetric back view on B or C is allowed.** It shows the same way round in both directions on DMG.
  - Making all three symmetric is the safe assumption, not a requirement.

## 3. The title screen

- **Yes.** The title's looping bar scene draws **variant A of the saloon group**, front view at shift 0, with one BG
  palette (`src/title.c`). The build refuses to make saloon A enhanced (`tools/gen_art.py`).
- **The assumption is right: no enhancement for A.** B and C are free to be enhanced.
- A is also seen in the credits cast and on other saloon screens (the story's saloon pictures and the venue's start
  screen). A new A therefore changes more goldens than a new B or C would.
