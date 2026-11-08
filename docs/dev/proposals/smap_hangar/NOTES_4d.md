# Round 4d: a small fighter jet in the style of the owner's reference (Q108); proposal only, no assets, no goldens

Sheet: `hangar_sheet4.png` (columns reference | 4c new 1 | jet A | jet B; rows DMG close-up x6, Color close-up x6, DMG whole x2, Color whole x2; the whole-mountain row starts with option 2 (4a) instead of the reference). The reference is `owner_jet_example.webp` (committed with this work). Sources: `src/jet_h.py` (the jet, typed runs), `src/mtn_h.py`, `src/sheet_h4.py`; hangar, apron (4 rows) and runway are round 4c's (`src/strip3_h.py`).

The jet is drawn by hand at map size (26 x 15), not traced or scaled, from the reference's look: side view facing right (the reference faces left), long pointed nose, a dark canopy with a glint forward on the back, a low swept delta wing (near wing big, far wing tip over the back), a tall swept-back tail fin with two stripes, a low tailplane, ink outline, a descent of about 12 degrees (a staircase of column groups).

- Yellow: the fin stripes use palette index 0. In the mountain piece's BASE palette index 0 is sand (the pale yellow of the runway dashes), so on Color the stripes are that pale yellow, not the reference's strong yellow; on DMG they are white. No new colour or slot. The reference's yellow intake stripe is skipped (no room, and index 0 beside the lit back made a fat blob).
- Jet A: fully out on the apron (nose over the apron, the tail fin just over the hangar's foot line). Jet B: tail still in the doors (fin and tail in the black slot, nose over the apron).
- Palettes: BASE 0 to 3 only. Nothing is Color only.

| unique DMG tiles, mountain piece | tiles |
|---|---|
| Round 3 | 86 |
| Option 2 (4a) | 93 |
| 4c new 1 (plane at 20 degrees) | 97 |
| Jet A | 99 |
| Jet B | 97 |
| (empty hangar, apron and runway, no plane) | 94 |

## Self-audit

| check | result |
|---|---|
| Hand-placed | Jet typed in `jet_h.py` (fuselage column groups, wing and fin rows, canopy). Scripts paste, render, count, lint. The reference was only looked at. |
| Clean-up | Done by eye: wing trailing edge dark strip, canopy glint, fin stripes on every other row. Lint L-doubles are not mended: jet A (12,53) and jet B (12,47), (13,48) are the fin's outline touching the black slot or the hazard lintel (false positives of an ink fill, not a thick line); jet A (22,58) is the canopy's step; jet A (30,62) is the nose tip, a deliberate sharp corner. |
| 1x comparison | Against the reference and 4c new 1: both jets read as a fighter (nose, fin, delta wing) better than 4c; B is the cleaner one (fin and nose silhouetted against the black slot). |
| Lint | PASS DMG and Color; 24 orphan pixels (round 3: 16): fin and canopy details. |
| Squint test | DMG: light delta wing and fin against black slot / dark apron read first. |

Doubts: the jet is much smaller than the reference's detail (no panel lines, no intake stripe); the fin stripes are pale yellow on Color; jet A's wing sits on the runway's top edge and is busy.
