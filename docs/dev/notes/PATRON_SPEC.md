# Bar patron specification

The general rules every Spigoteer bar patron must meet, whatever the venue or character. The rules come from the
engine (`tools/gen_art.py`, `src/render.c`, `src/lift.c`, `src/enhance.c`, `src/mirror.c`, `src/mugs.c`) as of main `da25974`.
The build checks the ones marked **[checked]** and refuses art that breaks them.

## 1. What a patron group is

- A group is **3 patrons**, called variants **A, B and C**. They appear together in one venue.
- Each variant has exactly **two pictures**:
  - **Front view**: what you see almost all the time (walking, being pushed, drinking).
  - **Back view**: shown only while the patron turns to watch the stage show.
- There are **no animation frames**.
  - Walking, being pushed and leaving are the same picture sliding sideways.
  - Drinking is shown by the held mug sprite and a small sway (section 6).
  - Don't design for poses that don't exist.

## 2. Size and framing

| | Front view | Back view |
|---|---|---|
| Canvas | **16 × 16 px** exactly **[checked]** | **16 × 16 px** exactly **[checked]** |
| Facing | 3/4 view, **facing right** (toward the bartender) | from behind |
| Tiles at rest | 2 × 2 (8×8 tiles) | 2 × 2 |

- The bottom row meets the counter, so the figure is cut off at the chest or shoulders. A patron is a head-and-shoulders bust standing behind the bar.
- Patrons move 1 px at a time, so the engine pre-shifts each front view to all 8 pixel offsets inside a **24 × 16** footprint (3 × 2 tiles). Draw only the 16 × 16 picture; the shifting is automatic.
- The tile budget is fixed per group: 3 fronts × 48 shifted tiles + 3 backs × 4 tiles = **156 tiles**. Art that is bigger, or has more pictures, does not fit.

## 3. Colours

### Every variant
- **4 indices**, written in the house ASCII format: `.` = 0, `-` = 1, `+` = 2, `#` = 3, one character per pixel.
- **Index 0 is the venue's wall colour**, not a colour of the patron.
  - On the background it shows the wall.
  - When the patron is lifted to a sprite, index 0 is transparent.
  - The two must look identical, so index 0 may only be used for "nothing here".
- **No index 0 enclosed inside the figure [checked]**, i.e. no holes. When lifted, a hole shows whatever is behind him, including another patron.
- **3 colours of his own** (indices 1–3), ordered **light → dark** **[checked]**: 1 lightest, 3 darkest.
- On the DMG the indices are fixed shades: 1 light grey, 2 dark grey, 3 black, with the wall as shade 0.
- Each variant's colours are its own palette entry, `<group>_a / _b / _c` in `assets/palettes.json`. Colour 0 is not listed there; it is the venue's.

### CGB
- The hardware allows one palette per 8×8 tile, and the whole variant uses one palette, so **one patron = 3 colours + the wall**.
- When lifted, a patron is two 8×16 sprites drawn in matching sprite palettes. They look identical to the background version.

### Optional: an "enhanced" variant (more colours)
A variant may use **two palettes**: the top tile row (rows 0–7) uses the venue's shared second bar palette, and the bottom row (rows 8–15) uses its own. Header line in the art file: `; @rows <v> S own`.

Rules **[checked]**:
- A colour that appears in both rows keeps the **same index** in both.
- Both palettes are ordered light → dark.
- **When lifted**, each 8-px-wide column (x 0–7 and x 8–15) is one sprite, so each column may hold **at most 3 colours across both rows**. Those colours must all be in one sprite palette: the variant's own, or the group's extra palette `<group>_x`.
- **Variant A of the group shown on the title screen cannot be enhanced** (the title draws it with one palette).

In practice this restricts where skin, hair and clothing colours can sit. Plan the colour layout before drawing.

## 4. Readability requirements

- **The three must be told apart at a glance by silhouette and value**, not by colour alone. The DMG has no colour, and the player reads them while sliding mugs at speed.
- **Readable on the DMG against a white wall**, with every shade used by the figure.
- **Neighbouring features must differ in value**, e.g. beard and skin, hat and hair, collar and chin. Two adjacent masses in neighbouring shades merge into one shape on the DMG.
- **Faces**:
  - About 4–6 px tall between hat or hair and collar.
  - Eyes must stay readable.
  - Avoid a skin block that tapers to a point with a hard outline on every step (the "arrowhead" face).
- **Patrons overlap.** Walkers pass each other, and pushed patrons slide through others. The patron in front is drawn whole over the other, so each silhouette needs a clear edge against another patron, not only against the wall.
- **Mirroring.** On some levels patrons walk from the right, and the whole picture is **flipped horizontally**. Nothing may depend on facing right: no lettering, no asymmetric detail that reads wrong when flipped.
- **Back views on the DMG with mixed directions** are **not** mirrored, so the same back view is used for both directions. A **symmetric back view** (mirror image about column 8, with column 0 empty) is safest and is required for some variants (e.g. the saloon's A, `tests/test_cowboy_back.py`).

## 5. Lifted (sprite) form

- A patron who overlaps another is drawn as **two 8 × 16 sprites**, from his front view at shift 0. Back views are never lifted.
- It must match the background version pixel for pixel. That is why index 0 means transparent and why holes are banned.
- **Sprite budget**: each lifted patron uses 2 of the 10 sprites allowed per scanline, so this is a design constraint, not an art one. The art just needs to look the same either way.

## 6. Things drawn on or around him

- **The held mug.** While drinking he holds a mug sprite (8 px wide) over the **right half of his figure** (x 8–15).
  - Most of the drinking time it is raised to **face height**; while being carried back it sits at **hand height**.
  - His eyes and the left side of his face stay visible. Design the face so it still reads when the right half is covered.
- **Sway.** While drinking, his picture shifts **2 px** right and back every 12 frames. Only the position changes.
- **Movement.**
  - He steps 1 px at a time (2 px on some DMG levels).
  - Pushed back at 1 px a frame.
  - He enters and leaves at the left edge of the screen.
- **Watching the show.** He shuffles to a tile boundary and turns to his back view.

## 7. Files and checks

- Art:
  - `assets/art/patrons/<group>.txt`: three 16 × 16 front views a, b, c, a blank line between them.
  - `assets/art/patrons/<group>_back.txt`: the three back views.
  - Comment lines start with `;`.
- Palettes: `assets/palettes.json` → `<group>_a`, `<group>_b`, `<group>_c` (3 colours each, light → dark), plus `<group>_x` if an enhanced variant needs it.
- **`make`** runs `tools/gen_art.py`, which validates sizes, holes, palette order, the enhanced rules and the lifted columns. It stops with a message naming the problem.
- **`make preview`** writes x8 previews to `out/preview/`.
- **The owner's art skill** (`~/.claude/skills/gb-pixel-art/`) applies to every patron: hand-placed pixels, its QA checklist and `scripts/gb_art_lint.py`.

## 8. The held mug, in detail

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

## 9. Back views and mirrored levels

- **Only the saloon's variant A must be symmetric.** This was the owner's request, and `tests/test_cowboy_back.py` enforces
  it: a mirror image about column 8, with column 0 empty. B and C have no such rule.
- **Yes, the saloon appears on mixed-direction levels.** CLASSIC wave 2's levels 14 and 15 are saloon levels with
  alternating bars (R L R L and L R L R), and from level 27 on those rows repeat.
- **On DMG with mixed directions, back views are not mirrored.** One back view serves both directions (`src/mirror.c`,
  `mir_bswap`). On CGB the flip handles it.
- **So an asymmetric back view on B or C is allowed.** It shows the same way round in both directions on DMG.
  - Making all three symmetric is the safe assumption, not a requirement.

## 10. The title screen

- **Yes.** The title's looping bar scene draws **variant A of the saloon group**, front view at shift 0, with one BG
  palette (`src/title.c`). The build refuses to make saloon A enhanced (`tools/gen_art.py`).
- **The assumption is right: no enhancement for A.** B and C are free to be enhanced.
- A is also seen in the credits cast and on other saloon screens (the story's saloon pictures and the venue's start
  screen). A new A therefore changes more goldens than a new B or C would.

## 11. What is behind a patron (the wall, index 0)

The patron's index 0 is the venue's wall colour. **It is light on the DMG and dark on the CGB**, so every figure must read
against both.

| Venue | CGB wall (index 0) | DMG wall |
|---|---|---|
| saloon | #2c5060 dark teal | white (shade 0) |
| sports | #384058 dark slate | white |
| lodge | #6a4a30 dark brown | white |
| bistro | #2a5a58 dark teal | white |
| igloo | #4a4078 dark violet | white |
| factory | #503028 dark red-brown | white |
| biker | #3a2a48 dark purple | white |
| teahouse | #4a6a58 dark green | white |
| zoo | #234e5c dark teal | white |
| space | #202a58 dark navy | white |

The CGB walls come from `assets/approved/venues/<venue>_pal.json`, entry `bar`, hex[0]. On the DMG, play uses BGP 0xE4,
so index 0 is always white.

What this means for the art:
- **DMG:** the dark outline (index 3) gives a strong silhouette against white. The light shades (1, 2) inside it must
  still separate from each other.
- **CGB:** the wall is dark, often about as dark as the patron's darkest colour. A dark outline next to a dark wall
  loses the silhouette, so the figure's edge has to read through its lighter masses: face, hat brim, shoulders and
  beard. Check every figure on its venue's CGB wall, not only on white.
- Never pick a patron colour close to its venue's wall colour.

## 12. Quality examples

Picture: `patron_quality_examples.png`, beside this file. Low is on the left and high on the right; CGB is on top and
DMG below.

**Low quality.** Round 1, saloon A "trail hand". A script added a 1 px outline to filled shapes. The face is a skin block
that tapers to the chin, with a hard dark step on every row: the "arrowhead" face. It also has no light or shade on the
face.
```
.....######.....
....#++++++#....
....#++#+++#....
..###+-#+++###..
.#++########++#.
#++++++++++++++#
.##############.
...###---#--#-#.
...###---------#
...###-----##-#.
....##------##..
...###+####+###.
..#++++####++++#
.#+++++#--#+++++
#+++++##++#+++++
################
```

**High quality.** Round 2, "prospector". Every pixel is hand-placed and there is a clean-up log. Hat, face and beard are
three different values (dark, mid, light), separated on the DMG too. The beard is cut flat at the counter, with no V
chin. The eyes are 2 px tall with a white catchlight. The owner's verdict: "much improved".
```
....###.###.....
....##+++###....
...##########...
...#++++++++#...
.##############.
.#.#++++++++#.#.
...#-+-#++-#+#..
...#-++#+++#++#.
...#-+-----++#..
..#--+++++---#..
..#----------#..
.##---+------##.
#++#--+---+-#++#
####--+---+-####
####------+-####
################
```
