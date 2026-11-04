# Lodge shows L6 "Bigfoot sighting" and L7 "Axe toss", 2026-11-04: costs

Color only. The DMG keeps today's lodge show. Proposals: nothing under `src/` or `assets/` changed; both were built and run in a scratch copy
(this worktree's `out/rc` = main + the Igloo round 2 glide block + the two changes below). Pictures: `lodge_L6.gif`, `lodge_L7.gif` (real engine,
Color at double speed, stage area x3, real speed), `lodge_L6_frames.png`, `lodge_L7_frames.png`, `lodge_L6_contact.png`, `lodge_L7_contact.png`.

| | L6 Bigfoot sighting | L7 Axe toss |
|---|---|---|
| Frames | 9, 16x24 | 11, 24x24 (the Sasquatch in columns 0-15, the axe in the prop cell, columns 16-23) |
| Today's frames reused pixel-exact | rows 0-13 of dance frames 0 and 1 (frames 2, 3, 4) | dance frames 0 and 1 (frames 0, 1) |
| 8x16 quarters (bank-1 pool 64) | 22 | 30 |
| Cells per frame (max 4) | 4 | 2-4 (the jump: 2 for the body + 1 for the axe) |
| OBJ palettes | 1, today's | 1, today's |
| OBJ entries per line, worst (limit 10) | 6, measured in the engine on lines 8-39 | 8, measured in the engine on lines 14-23 at a catch (the thrower's body 2 + axe 1, the catcher at its paw 2 + axe 1, the lead 2) |
| Lines used | 8-31; patrons start at 40 | 8-31 |
| Loop | 32 beats = 128 rows, a row every 3 frames | 32 beats = 128 rows |
| Color block + pool | 1523 B + 704 B | 1811 B + 960 B |
| Banked ROM, whole build vs the same build without a lodge Color show | +2449 B | +2993 B |
| ROM0 | 447 B free before and after (linker map) | 447 B free |
| New WRAM | 0 (`_DATA` 7547 B before and after) | 0 |
| Perf, lodge, Color double speed, patrons walking, one show (581 frames; the guards' end-line metric) | mean 26.6, p90 56, worst 87, 0 late | mean 26.5, p90 56, worst 87, 0 late |
| Same build, today's lodge dance | mean 20.7, p90 48, worst 78, 0 late | |
| Engine change beyond the glide block | the camera flash (below), +421 B banked | none |
| Generator change beyond the glide block | the flash bit | the prop cell |

For reference the Igloo round 2 measured worst 75 (I1b), factory 79, bistro 82 on its build. The lodge had only 4 patrons in the measurement
(the level caps them).

## L6: the camera flash is a palette flash (Color), through the show wash

- Data: performer 0's `"flash"` list (one 0|1 per row) sets bit 15 of performer 0's record offset in that row (`tools/gen_art.py`). Offsets are below 0x8000.
- `src/show_ext.c` show_ext_draw masks the bit off and, on a flash row, clears `SHOWLT_STAMP` (an existing story_scratch byte), so main.c calls
  `lights_frame` on the next frame (it calls every frame while the stamp is 0).
- `src/lights.c` lights_frame, steady part of the show only (not in the 16-frame fades): `show_ext_flash()` reads the current row's bit; on a flash
  row it builds the same 16-byte buffer (BG palettes 5 and 6, `SHOWLT_BUF`) with every colour 3/4 of the way to white
  (`0x7FFF - (((0x7FFF - c) >> 2) & 0x1CE7)`, no multiply), keeps the stamp at 0 and asks for the write. The first frame after the flash rows finds
  the stamp stale and rebuilds the beat's tint.
- **VBlank rule:** nothing new touches palette RAM. The colours go into the buffers the wash already uses: `SHOWLT_BUF` (written by render.c
  pal5_write in the VBlank) and the split's `SPLIT_STG` / `SPLIT_E_STG` (put back by main.c split_vbl3 in the VBlank). Same path as the tint.
- **Against the wash:** the flash replaces the tint for its rows only; HUD, bars, patrons and performers (other palettes) are untouched, so the
  Sasquatches stand dark against a white stage: the photo. Measured in the capture: 6 frames white (2 rows), one frame after the row starts.
- Only when the wash runs: Color at double speed (`DS_NOW`), as shipped. Built from the stage colours through `BRIGHTEN`, so SCREEN BRIGHT applies.
- Twice a loop: rows 32-33 (all three up, two duck, the middle one caught with its arms up) and rows 88-89 (the middle stump caught mid-step,
  its head popped up).
- Not a sprite burst: OAM 28-39 are the performers' and the rest is full; a burst would also need cells the 16x24 stump frames do not have.

## L7: the prop cell (generator only, no engine change)

- A performer row may carry `"prop": [px, py]`. The record's column-2 cells (the third 8x16 column of a 24-wide frame) move by px
  (mirrored when flipped) and py; records are per (performer, frame, flip, px, py). The engine copies finished OAM entries as today.
- The axe flies from the thrower's paw to the catcher's paw drawn by the **thrower's** record the whole way (7 points, 14 px a row, an arc of 4 px,
  turned 0/90/180/270 degrees a row), and the catcher jumps on the last point, where both draw it in the same place. So the
  one-performer-a-frame redraw never shows two axes or none at a hand-over. A thrower stays up 9 rows (27 frames): from its catch until the axe it threw is caught.
- Why the jump: a standing Sasquatch is 4 cells, so a performer can only carry the axe as a 5th sprite while it is in the air (body in rows 0-15 =
  2 cells). That is also why the volley never stops: whoever has the axe is in the air (see doubts).
- Choreography (128 rows): 4 volley halves; swap A (rows 32-39: the one holding the axe leaps across with it, the other leaps the other way, they cross
  over the middle one, who ducks); 5 halves from the swapped ends; swap B (rows 80-87) back; 5 halves. The lead raises its hatchet, chops (the log
  splits, chips fly) and ducks with its paws over its head while the axe passes over the middle (every 8 rows).

## Tests on the scratch builds (make test: 6215-6216 passed)

Failures that importing either show would need test changes for (not perf guards; all perf guards passed):

- `tests/test_mg_logroll_fish.py` (3 tests, DMG and Color): `sq_frame` assumes dance frame f's tiles at `OBJ_DANCER + 8 f`. A Color file needs
  `"performers"` in `lodge_show_pal.json` (the DMG block, today's dance), and that lays the DMG show tiles out as de-duplicated quarters. The log-roll
  partner draws from `venue.show_tile` (the legacy rows), so the game is right; the helper must read `venue.show_tile`.
- `tests/test_venues.py::test_a_bonus_round_between_levels_restores_the_performer_tiles[cgb]`: counts 12 sprites with bank-0 dancer tiles at level 3
  (the lodge); a Color show uses its bank-1 pool. Same for any lodge Color show.
- L6: `tests/test_show_wash.py::...dim_and_tinted_during_a_show[lodge]` samples frame 607, a flash row. The test needs to skip flash rows.
- L7: `tests/test_show_obj5.py` (2) expects 12 dancer entries; the jump frames use 3 or 2.

## Diff: src/show_ext.c (on top of the glide block)

```diff
@@ includes
 #include "music.h"
+#include "showlights.h"
@@ show_ext_draw, the glide branch
         far_copy(r, p + 3 + (s << 3) + s + (k << 1) + k, 3, venue_bank);
+        if (r[1] & 0x80) {                     // (bit 15 of performer 0's offset: a camera-flash row, src/lights.c: the wash builds the flash from the next frame)
+            r[1] &= 0x7F;
+            SHOWLT_STAMP = 0;
+        }
         off = r[0] | (uint16_t)r[1] << 8;
@@ after show_ext_draw
+// Is the glide block's current row a camera-flash row (bit 15 of performer 0's record offset)? src/lights.c asks while a show plays on Color.
+uint8_t show_ext_flash(void) BANKED {
+    uint8_t e = dance_tick / 3, b;
+    uint16_t s = DANCE_STEP;
+    if (!(venue.show_band & 0x40)) return 0;
+    if (e > 3) e = 3;
+    s = (s << 2) + e;
+    far_copy(&b, ext_block() + 3 + (s << 3) + s + 1, 1, venue_bank);
+    return b & 0x80;
+}
```

## Diff: src/showlights.h

```diff
 void lights_frame(void) BANKED;                    // src/lights.c: once a frame while a show plays (main.c, after the music tick)
+uint8_t show_ext_flash(void) BANKED;               // src/show_ext.c: the glide row is a camera-flash row (non-zero)
```

## Diff: src/lights.c

```diff
     if (t > LT_FADE && t <= SHOW_FRAMES - LT_FADE) {                       // steady
-        if (SHOWLT_STAMP == u + 1) {
+        if ((venue.show_band & 0x40) && show_ext_flash()) {                // a camera-flash row (a glide show, src/show_ext.c): the stage near white; stamp 0 keeps the calls coming every frame, and the first frame after the flash builds the tint again
+            SHOWLT_STAMP = 0;
+            u = 0xFF;
+        } else if (SHOWLT_STAMP == u + 1) {
@@
-    tn = lt_tint[u];
-    for (i = 0; i < 3; i++) m[i] = 32 - (uint8_t)(MUL8(32 - tn[i], lvl) >> 4);
+    if (u != 0xFF) {
+        tn = lt_tint[u];
+        for (i = 0; i < 3; i++) m[i] = 32 - (uint8_t)(MUL8(32 - tn[i], lvl) >> 4);
+    }
@@
             uint16_t c = BRIGHTEN(q[i]);
-            c = (MUL8(c & 31, m[0]) >> 5) | ((MUL8((c >> 5) & 31, m[1]) >> 5) << 5) | ((MUL8((c >> 10) & 31, m[2]) >> 5) << 10);
+            if (u == 0xFF) c = 0x7FFF - (((0x7FFF - c) >> 2) & 0x1CE7);       // (the flash: every channel 3/4 of the way to white, no borrow between channels)
+            else c = (MUL8(c & 31, m[0]) >> 5) | ((MUL8((c >> 5) & 31, m[1]) >> 5) << 5) | ((MUL8((c >> 10) & 31, m[2]) >> 5) << 10);
```

## Diff: tools/gen_art.py (on top of the glide block)

```diff
@@ show_block
+    def prop_at(p, s):
+        pr = p.get("prop")
+        return tuple(pr[s]) if pr else (0, 0)
+
@@
-            key = (k, f, flip_at(p, s % len(p["loop"])))
+            key = (k, f, flip_at(p, s % len(p["loop"]))) + prop_at(p, s % len(p["loop"]))
@@
-            off = head + 16 * recs[(k, p["loop"][i], flip_at(p, i))]
+            off = head + 16 * recs[(k, p["loop"][i], flip_at(p, i)) + prop_at(p, i)]
+            if glide and k == 0 and p.get("flash") and p["flash"][i]:     # a camera-flash row (Color, src/lights.c): bit 15 of performer 0's offset
+                assert off < 0x8000 and len(p["flash"]) == period, f"{t}: flash: one 0|1 per row"
+                off |= 0x8000
@@
-    for k, f, flip in order:
+    for k, f, flip, px, py in order:
@@
-                body += [1 + 16 * r, x, tile_of(q), bank_bit | (0x20 if flip else 0)]
+                y = 1 + 16 * r
+                if c == 2:                  # a prop cell (a 24-wide glide show's third column): moved by the row's "prop" [px, py] (px mirrored when flipped)
+                    x, y = (x + (-px if flip else px)) & 255, y + py      # (the engine adds the performer's x modulo 256)
+                    assert 1 <= y <= 17, f"{t}: prop cell of frame {f} off the stage band (y {y})"
+                body += [y, x, tile_of(q), bank_bit | (0x20 if flip else 0)]
```

## To import (for the supervisor, after the owner picks)

1. The glide block diffs (`../COSTS.md`), then the diffs above (the flash only for L6; the prop cell only for L7).
2. `assets/approved/venues/lodge_show_cgb.txt` = the picked file; in `lodge_show_pal.json` add `"performers"` (three `{"loop": [0, 1, 2, 3], "flip": 0}`,
   today's dance) and `"performers_cgb"` (the JSON line in the file's header).
3. The test changes above, plus tests for the flash (bit decode, the white buffer, back to the tint) or the prop cell (record x/y, mirrored px).
