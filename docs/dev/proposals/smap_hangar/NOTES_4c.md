# Round 4c: the 4a side-view plane redrawn bigger, half out of the doors (proposal only; no assets, no goldens)

Sheet: `hangar_sheet3.png` (columns option 2 (4a) | new 1 | new 2; rows DMG close-up x6, Color close-up x6, DMG whole x2, Color whole x2). Sources: `src/plane2_h.py` (both planes, typed runs), `src/strip3_h.py` (apron and runway), `src/mtn_h.py`, `src/sheet_h3.py`.

- Plane: 22 px long, nose right and down, a fuselage staircase of column groups ("outline, lit back, body, body, shade, outline"), pointed nose, swept tail fin, canopy dome with a glint, a far wing tip over the back and a near wing hanging down and back. New 1: groups of 3 columns (about 20 degrees). New 2: groups of 2 columns (about 30 degrees). Tail in the black slot, nose over the apron (New 2: onto the runway's edge).
- Hangar and tower stay 8 px higher (foot y 55). Apron now 4 rows (x 2 to 31); runway 9 rows (x 1 to 50) keeps going right.
- Tarmac stays navy (Color) / dark grey (DMG): the plane (lit 0, body 1) separates from it; grey tarmac (index 1) would make the plane body vanish on DMG, so not used.
- Palettes: BASE 0 to 3 only, the piece's existing 2 palettes. Nothing Color only.

| unique DMG tiles, mountain piece | tiles |
|---|---|
| Round 3 | 86 |
| Option 2 (4a) | 93 |
| New hangar, apron and runway, empty | 94 |
| New 1 | 97 |
| New 2 | 97 |

Plane +3 over the empty strip; +4 over option 2 (4a); +11 over round 3.

## Self-audit

| check | result |
|---|---|
| Hand-placed | Plane runs typed in `plane2_h.py`; strip typed in `strip3_h.py`. Scripts paste, render, count, lint. |
| Clean-up | Done: lint L-doubles mended by hand (fin tip off the hazard lintel, nose top off the foot line). The earlier 4b planes (5 L-doubles) are dropped. |
| 1x comparison | Against the 4a side-view plane: the new planes read as a plane with wing, tail fin, canopy and nose, at a diagonal; the 4a plane is still the cleaner, more compact picture. |
| Lint | PASS DMG and Color, no L-doubles left; 22 to 23 orphan pixels (round 3: 16): fin and wing tips, canopy glint. |
| Squint | DMG: white wing and lit back against the black slot read first; New 1 reads better than New 2 (New 2's wing is a bump on the fuselage). |

Doubts: the plane crosses the hangar's foot line and the apron edge, which makes its lower half busy; New 2's near wing is the roughest part.
