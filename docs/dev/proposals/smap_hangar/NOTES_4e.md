# Round 4e: jet B cleaned up by hand

Source: src/jet2_h.py (typed runs), wired as keys K1 (level) and K2 (about 7 degrees) in src/mtn_h.py, sheet by src/sheet_h5.py, sheet hangar_sheet5.png.
Hangar, apron, runway unchanged. Tail in the doors, origin (6, 46).

- K1 level: horizontal fuselage, 5 rows tall at the tail, 3 rows in the middle, one-row needle nose; outline steps one pixel per step; delta wing with vertical trailing edge and leading edge in runs of 2; fin stripes kept.
- K2 slope: fuselage drops one row every 8 columns (x 10, x 18), top and bottom parallel, symmetric nose cone.

Unique DMG tiles of the mountain piece: option 2 (4a) 93, jet B (4d) 97, K1 97, K2 97 (round 3 with no runway 86). Palettes BASE + SALOON (2 of 8).
Lint: PASS. L-doubles: jet B 2 (hangar), K1 4, K2 6, the extra ones at the steps where the canopy outline meets the fuselage outline. Orphans 22-24 (sand dashes of the background, same as before).
