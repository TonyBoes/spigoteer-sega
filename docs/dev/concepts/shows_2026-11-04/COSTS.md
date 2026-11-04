# Igloo show I1b "Waddle wave" round 2, 2026-11-04: costs

Color only. The DMG keeps today's igloo show. Proposal: nothing under `src/` or `assets/` changed; the engine and generator change below was built and run in a scratch copy only.

| | I1 (round 1) | I1b (this round) |
|---|---|---|
| Frames | 8 (0-3 today's) | 11 (0-7 round 1, pixel-exact; new: 8 dive, 9 slide with spray B, 10 slide slowing) |
| Frame width | 24 | 24 |
| 8x16 quarters (bank-1 pool 64) | 27 | 33 |
| OBJ palettes | 1, today's | 1, today's |
| Cells per frame (max 4) | 4 | 4 |
| OBJ entries per line, worst (limit 10) | 7 (previewer) | 8, measured in the engine on lines 24-39 (two slides crossing, 3 + 3, plus the middle penguin standing, 2). Nothing else uses lines 8-39; patrons start at line 40 |
| Loop | 16 beats | 16 beats = 64 rows, a row every 3 frames |
| Slides per loop | 1 (left to middle) | 4: bar B both ends at once (L to R and R to L, crossing), bar C middle to left, bar D middle to right. 3 of the 4 bars have slides |
| Slide motion | 12 px a beat (every 12 frames) | x updated every 3 frames (20 a second), eased: 13, 12, 11 ... 4, 3 px per update |
| New WRAM | 0 | 0 |
| Built and run in the engine | no | yes (scratch copy, Color at double speed) |

## Choreography (rows.txt in the header's JSON; 4 rows a beat)

- Bar A (beats 0-3): the waddle wave ripples L, M, R, today's poses.
- Bar B (beats 4-7): L and R crouch, dive and belly-slide across from both ends; they cross under the middle spot while M hops (tuck) over them; they get up on the far spots.
- Bar C (beats 8-11): M slides off to the left end (flipped); the left one leapfrogs (tuck, flipped) over it to the middle; R cheers.
- Bar D (beats 12-15): the middle one slides off to the right end; the right one leapfrogs over it to the middle; L cheers. Beat 15 leads into the ripple.
- Every penguin ends on a spot. The penguins are identical, so performer k does not have to return to its own spot: at the wrap each spot already shows a standing penguin and the next beat's pose.

## How the smoother slide works (engine change, not in-between frames)

Today the Color show reads one row a beat. I1b uses a "glide block": 4 rows a beat, each row giving each performer a record (frame, flip) and a signed x shift. The engine already redraws one performer a frame (rom0_relief.c dancers_step); in a glide block the draw of performer 2 bumps `dancer_frame`, so render.c's existing quick check starts the next round. Each performer is then redrawn every 3 frames, reading row `DANCE_STEP * 4 + dance_tick / 3`. Frames 8-10 are extra poses (the take-off stretch, a second spray, a slowing slide), not in-betweens for spacing.

- Changed files: `src/show_ext.c` (show_ext_draw, show_ext_next) and `tools/gen_art.py` (show_block; venue.show_band bit 6). `rom0_relief.c` (bank 21, 7 B free) and `render.c` are untouched.
- Flip: per row (the OAM flag, as today's per-performer flip). Records are now per (performer, frame, flip); the existing venues' blocks come out byte-identical.
- DMG path: unchanged. The glide branch is behind `is_cgb && (venue.show_band & 0x40)`; venues without a glide block read nothing extra. (A first version read the period byte on every draw for every Color-block venue; that extra far_copy made tests/test_show_resume_attrs.py fail at the zoo, so the flag moved to show_band bit 6.)
- Per-performer lag: the round robin means the right performer's change shows up to 2 frames after the left one's. Visible only as a tiny stagger.

## Measured (scratch copy, Color at double speed as shipped)

- ROM0: 447 B free before and after (linker map). No ROM0 code.
- Banked: +2527 B in all. Code: show_ext.c +78 B (0x326 to 0x374, autobanked). Igloo data +2449 B (venue_igloo moved from bank 29 to bank 4 by bankpack): the DMG per-performer block 219 B (today's dance, a Color file needs it), the Color glide block 1171 B (64 rows of 9 B, 37 records), the pool 1056 B (33 quarters, bank-1 ids 0-65, one segment) + 3 B.
- WRAM: WRAM_LO 160 B free and WRAM_HI_0 461 B free, both unchanged.
- Perf, the guards' metric (logic end line), igloo with 5 patrons walking, one whole show (581 sampled frames): mean 24.7, p90 54, worst 75, no late frames. Today's igloo dance: mean 19.1, p90 45, worst 73. For reference, the factory and bistro Color shows on the same build: worst 79 and 82. The glide redraws a performer every frame for the whole show, so the mean goes up; the worst frame does not.
- `make test` on the scratch build: 6220 passed, 4 failed. 3 are `test_atlas_page.py`, which also fail on an unchanged copy (the scratch copy has no docs/dev). 1 is real: `tests/test_debug.py::test_a_starts_that_level_from_scratch[cgb-5]`. Level 5 is the igloo; with a bank-1 pool its load takes 17 frames, the same as bistro, factory and space already do, and the test waits 15. Importing I1b needs that wait raised (a test change, not a perf guard). All perf guards passed.
- Capture: tests' play() + start() on Color at double speed, every frame of one loop (192 frames, from beat 0 of the 2nd loop). GIF: stage area x3; GIF delays come in 10 ms steps, so every 6th frame is dropped and the rest show 20 ms each (50 shown a second = 60 game frames a second, real speed).

## I1c (round 3): slower slides

Owner 2026-11-04 on igloo_I1b.gif: "they could probably slide a little bit slower with the penguins." Files: igloo_show_I1c_cgb.txt, igloo_I1c.gif (real engine, double speed, stage x3).

- Same frames as I1b (no new art), same choreography: both-ends crossing slide with the hop, then the two leapfrogs. No slide dropped. **The loop is longer: 20 beats (80 rows) instead of 16.** Bar B is 6 beats and bars C and D are 5 beats each.
- Long slide (96 px, both ends at once): 17 rows = 51 frames, was 11 rows = 33 frames (about 1.5x). It moves 10, 9, 8, 8, 7, 7, 6, 6, 5, 5, 4, 4, 3, 3, 3, 3, 2 px per update, so the top speed is 9 px an update after the take-off, down from 13.
- Short slides (48 px): 11 rows = 33 frames, was 7 rows = 21 frames (about 1.6x). They move 6, 5, 5, 4, 4, 3, 3, 2, 2, 1 px per update, so the top speed is 6, down from 9.
- The hop and the leapfrogs are retimed to the slower slides: the middle penguin's tuck lasts 7 rows (it was 5), and the leaps move about 12 px a row (they were 14).
- Every penguin ends on a spot, and the wrap is a normal beat change, as in I1b.

| | I1b | I1c |
|---|---|---|
| 8x16 quarters (bank-1 pool 64) | 33 | 33 |
| OBJ entries per line, worst (limit 10) | 8 | 8, measured on lines 24-39 over a whole show |
| Glide block | 1171 B (64 rows) | 1315 B (80 rows, 37 records) |
| Igloo show data | +2449 B | +2593 B |
| Banked ROM in all, with show_ext.c +78 B | +2527 B | +2671 B |
| ROM0 | 447 B free, unchanged | 447 B free, unchanged |
| WRAM | 0 new (WRAM_LO 160 free, WRAM_HI_0 461 free) | same |
| Perf: logic end line, igloo show, 5 patrons, double speed | worst 75, mean 24.7, no late frames | worst 75, mean 24.7, no late frames |
| `make test` (scratch) | 6220 passed; 3 atlas (copy artifact) + test_debug level 5 load wait | same |

## To import (for the supervisor, after the owner picks)

1. Apply the two diffs below.
2. `assets/approved/venues/igloo_show_cgb.txt` = the picked file (igloo_show_I1c_cgb.txt, or igloo_show_I1b_cgb.txt); in `igloo_show_pal.json` add `"performers"` (three `{"loop": [0, 1, 2, 3], "flip": 0}`, today's dance) and `"performers_cgb"` (the JSON line in the file's header).
3. Raise the wait in test_debug.py's level-start test (15 to 20 frames). Add tests for the glide block (row decoding, flip per row, the 3-frame redraw).

## Diff: src/show_ext.c

```diff
--- a/src/show_ext.c
+++ b/src/show_ext.c
@@ -5,6 +5,7 @@
 // and then the pool section that load_venue puts into bank 1 (LCD off).
 // Block: [0..1] size, [2] beat period, then per beat a row of 6 bytes (performer k's record offset at 2k), then the 16-byte records: 4 finished OAM entries
 // (y + 1 or 0, x from the figure's left edge, tile, prop) that the draw copies into shadow OAM and offsets by the performer's place. Beat = DANCE_STEP (0..period-1).
+// A glide block (Color only; venue.show_band bit 6, its period byte = beats | 0x80): 4 rows a beat of 9 bytes (performer k's record offset and a signed x shift at 3k), so a performer moves every 3 frames.
 // No WRAM: the block is read from the venue's bank on each change.
 #pragma bank 255
 #include <gb/gb.h>
@@ -32,14 +33,25 @@
 // (rom0_relief.c dancers_step): the beat's row names the record, the record is copied into shadow OAM and moved to the performer's place.
 void show_ext_draw(uint8_t sig, uint8_t k) BANKED {
     uint16_t off, s = DANCE_STEP;
-    uint8_t e, x, flags;
+    uint8_t e, x, flags, r[3];
     const uint8_t *p = ext_block();
     OAM_item_t *o = shadow_OAM + OAM_DANCERS + (k << 2);
+    x = ext_x[k];
+    r[0] = 0;
+    if (is_cgb && (venue.show_band & 0x40)) {   // a glide block (Color, gen_art.py): 4 rows a beat, one every 3 frames (dance_tick / 3), each performer's 3 bytes: record offset, x shift
+        if (k == 2) dancer_frame = (dancer_frame + 1) & 3;     // (a new look: render.c draws all three again from the next frame, one a frame, so each is redrawn every 3 frames)
+        e = dance_tick / 3;
+        if (e > 3) e = 3;
+        s = (s << 2) + e;
+        far_copy(r, p + 3 + (s << 3) + s + (k << 1) + k, 3, venue_bank);
+        off = r[0] | (uint16_t)r[1] << 8;
+        x += r[2];
+        r[0] = 0x80;
+    }
     if (!(sig & (1 << k))) { o[0].y = o[1].y = o[2].y = o[3].y = 0; return; }
-    far_copy(&off, p + 3 + (s << 2) + (s << 1) + (k << 1), 2, venue_bank);
+    if (!(r[0] & 0x80)) far_copy(&off, p + 3 + (s << 2) + (s << 1) + (k << 1), 2, venue_bank);
     far_copy(o, p + off, 16, venue_bank);
     flags = is_cgb ? (OBJX_ON ? ext_pal[k] : OBJPAL_DANCER) : 0;
-    x = ext_x[k];
     for (e = 0; e < 4; e++, o++) {
         if (!o->y) continue;
         o->y += EXT_OAM_Y - 1;
@@ -52,7 +64,7 @@
 void show_ext_next(void) BANKED {
     uint8_t per, i = DANCE_STEP + 1;
     far_copy(&per, ext_block() + 2, 1, venue_bank);
-    DANCE_STEP = i >= per ? 0 : i;
+    DANCE_STEP = i >= (per & 0x7F) ? 0 : i;
     dancer_frame = (dancer_frame + 1) & 3;
 }
 
```

## Diff: tools/gen_art.py

```diff
--- a/tools/gen_art.py
+++ b/tools/gen_art.py
@@ -247,6 +247,7 @@
 SHOW_LOOP_LENS = tuple(range(1, 9))
 SHOW_MAX_FRAMES = 27
 SHOW_PERIOD_MAX = 64                 # the beat rows: 6 bytes a beat
+SHOW_GLIDE_BEATS = 32                # a glide block's beats (4 rows of 9 bytes a beat; DANCE_STEP * 4 + 3 < 256)
 OBJ_DANCER = 96                      # src/game.h (src/show_ext.c checks it)
 SHOW_BANK1_FREE = {"biker": [(0, 56), (76, 8), (92, 36)]}   # OBJ ids free in VRAM bank 1 in a level: all but the Chrome Cow's copies of the mug and the glass (src/lift.c swap_bank1: 56..75, 84..91)
 SHOW_BANK1_ALL = [(0, 128)]
@@ -270,32 +271,52 @@
 
 
 def show_block(t, perf, cells, w, tile_of, bank_bit):
-    """The block bytes (see above). tile_of(quarter) -> tile byte (bank 0: OBJ_DANCER + the offset)."""
+    """The block bytes (see above). tile_of(quarter) -> tile byte (bank 0: OBJ_DANCER + the offset).
+    A glide block (Color only: every performer has "dx"): "loop" is a row every 3 frames (4 a beat; the three of one length, a multiple of 4, at most
+    4 * SHOW_GLIDE_BEATS), "dx" a signed x shift per row (-128..127), "flip" 0|1 or one per row; the period byte is the beats | 0x80 and a row is
+    9 bytes (performer k's record offset at 3k, its x shift at 3k + 2), a record per (performer, frame, flip) (src/show_ext.c)."""
     import math
     assert len(perf) == 3, f"{t}: performers: 3 (left, middle, right)"
     nf = len(cells)
     assert 1 <= nf <= SHOW_MAX_FRAMES, f"{t}: show frames {nf} (1..{SHOW_MAX_FRAMES})"
-    period = 1
-    for k, p in enumerate(perf):
-        loop = p["loop"]
-        assert len(loop) in SHOW_LOOP_LENS and all(0 <= f < nf for f in loop), f"{t}: performer {k}: a loop of 1-8 frame ids < {nf}"
-        period = period * len(loop) // math.gcd(period, len(loop))
-    assert period <= SHOW_PERIOD_MAX, f"{t}: the three loops' lengths {[len(p['loop']) for p in perf]} meet only every {period} beats (at most {SHOW_PERIOD_MAX})"
+    glide = all("dx" in p for p in perf)
+    assert glide or not any("dx" in p for p in perf), f"{t}: a glide show gives every performer a dx"
+
+    def flip_at(p, s):
+        fl = p.get("flip", 0)
+        return int(bool(fl[s] if isinstance(fl, list) else fl))
+    if glide:
+        n = len(perf[0]["loop"])
+        assert bank_bit and n % 4 == 0 and 4 <= n <= 4 * SHOW_GLIDE_BEATS, f"{t}: a glide show (Color only): rows in fours, at most {4 * SHOW_GLIDE_BEATS}"
+        for k, p in enumerate(perf):
+            fl = p.get("flip", 0)
+            assert len(p["loop"]) == n and len(p["dx"]) == n and (not isinstance(fl, list) or len(fl) == n), f"{t}: performer {k}: loop, dx (and a flip list) of {n} rows"
+            assert all(0 <= f < nf for f in p["loop"]) and all(-128 <= d <= 127 for d in p["dx"]), f"{t}: performer {k}: frame ids < {nf}, dx -128..127"
+        period, stride = n, 9
+    else:
+        period, stride = 1, 6
+        for k, p in enumerate(perf):
+            loop = p["loop"]
+            assert len(loop) in SHOW_LOOP_LENS and all(0 <= f < nf for f in loop), f"{t}: performer {k}: a loop of 1-8 frame ids < {nf}"
+            period = period * len(loop) // math.gcd(period, len(loop))
+        assert period <= SHOW_PERIOD_MAX, f"{t}: the three loops' lengths {[len(p['loop']) for p in perf]} meet only every {period} beats (at most {SHOW_PERIOD_MAX})"
     recs, order = {}, []
     for k, p in enumerate(perf):
-        for f in p["loop"]:
-            if (k, f) not in recs:
-                recs[(k, f)] = len(order)
-                order.append((k, f))
-    head = 3 + 6 * period
+        for s in range(period):
+            f = p["loop"][s % len(p["loop"])]
+            key = (k, f, flip_at(p, s % len(p["loop"])))
+            if key not in recs:
+                recs[key] = len(order)
+                order.append(key)
+    head = 3 + stride * period
     rows = []
     for s in range(period):
         for k, p in enumerate(perf):
-            off = head + 16 * recs[(k, p["loop"][s % len(p["loop"])])]
-            rows += [off & 255, off >> 8]
+            i = s % len(p["loop"])
+            off = head + 16 * recs[(k, p["loop"][i], flip_at(p, i))]
+            rows += [off & 255, off >> 8] + ([p["dx"][i] & 255] if glide else [])
     body = []
-    for k, f in order:
-        flip = bool(perf[k].get("flip"))
+    for k, f, flip in order:
         cl = cells[f]
         for e in range(4):
             if e < len(cl):
@@ -305,7 +326,7 @@
             else:
                 body += [0, 0, 0, 0]
     size = head + len(body)
-    return [size & 255, size >> 8, period] + rows + body
+    return [size & 255, size >> 8, (period >> 2) | 0x80 if glide else period] + rows + body
 
 
 def show_ext(t, shows, perf, cgb_path, cgb_perf, bank1):
@@ -551,7 +572,7 @@
          "    const uint8_t *anim_frames, *anim_script;    // stage animation (src/venue.c), in the venue's own bank",
          "    uint16_t anim_frames_n;                      // bytes of anim_frames (0: the stage does not move)",
          "    uint8_t anim_script_n, anim_first, anim_k;   // script bytes; first animated stage id, animated tiles",
-         "    uint8_t show_band;                           // bit 0: 0 one dance for all three (row = dance frame), 1 a band; bits 1-2: FILL_DY (src/mugs.c); bit 3: three show palettes (Color); bit 4: a per-performer show block follows the tiles (src/show_ext.c); bit 5: with a Color block + its bank 1 pool",
+         "    uint8_t show_band;                           // bit 0: 0 one dance for all three (row = dance frame), 1 a band; bits 1-2: FILL_DY (src/mugs.c); bit 3: three show palettes (Color); bit 4: a per-performer show block follows the tiles (src/show_ext.c); bit 5: with a Color block + its bank 1 pool; bit 6: the Color block is a glide block (src/show_ext.c)",
          f"    uint8_t show_tile[{SHOW_ROWS}][4];             // per row: OBJ tile offsets from OBJ_DANCER, TL TR BL BR",
          "    uint8_t splash_tile;                         // the counter splash's BG id (assets/art/splash; 0: none)",
          "} venue_t;",
@@ -723,7 +744,7 @@
               "    { " + ", ".join(arr(x) for x in pal15) + " },",
               (f"    {sym}_anim_frames, {sym}_anim_script, {len(anim['data'])}, {len(ascript)}, {a_first}, {anim['k']},"
                if anim else "    0, 0, 0, 0, 0, 0,"),
-              f"    {band | fdy << 1 | (8 if len(show_pals) == 3 else 0) | (16 if perf is not None else 0) | (32 if ext_info and "c_block" in ext_info else 0)}, {{ " + ", ".join(arr(r) for r in show_tab) + " },", f"    {bar_base + sid if sid is not None else 0}",
+              f"    {band | fdy << 1 | (8 if len(show_pals) == 3 else 0) | (16 if perf is not None else 0) | (32 if ext_info and "c_block" in ext_info else 0) | (64 if ext_info and ext_info.get("c_block") and ext_info["c_block"][2] & 0x80 else 0)}, {{ " + ", ".join(arr(r) for r in show_tab) + " },", f"    {bar_base + sid if sid is not None else 0}",
               "};", ""]
         (outdir / f"{sym}.c").write_text("\n".join(vc))
         load += [f"BANKREF_EXTERN({sym})", f"extern const venue_t {sym};"]
```
