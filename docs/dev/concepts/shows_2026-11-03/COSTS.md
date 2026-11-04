# Lodge + Igloo shows, 2026-11-03: costs

All four are Color only. DMG keeps today's show at both venues.

| | L1 Jug band | L3 Fireside | I1 Waddle wave | I3 Snow show |
|---|---|---|---|---|
| Frames | 10 (0-3 today's) | 6 | 8 (0-3 today's) | 6 (0-1 today's) |
| Frame width | 16 | 16 | 24 (see I1) | 16 |
| 8x16 quarters (bank-1 pool 64) | 32 | 16 | 27 | 17 |
| OBJ palettes | 1, today's | 1, today's | 1, today's | 1, today's |
| Cells per frame (max 4) | 4 | 4 | 4 | 4 |
| Performer sprites per line | 6 | 6 | 7 (slide beats) | 6 |
| Today's performer sprites per line | 6 | 6 | 6 | 6 |
| Loop / period | 4 / 4 beats | 4 / 4 beats | 16 / 16 beats | 4 / 4 beats |
| Stage animation | today's | show-time fire, 6 frames, 192 B | today's | show-time snow, 5 frames, 160 B |
| New WRAM | 0 | 0 | 0 | 0 |
| Engine change | none | show-time anim switch | none | show-time anim switch |
| Generator change | none | show-time anim file | 16-step loops, per-step dx | show-time anim file, own tile slots |
| Built and run in the engine | yes | yes | no | yes |

## Show-time stage animation (L3 fire, I3 snow)

- Color only, behind `is_cgb`.
- At show start the venue's anim frames and script are swapped for the show's set, in the same `sa_frames` buffer (SA_BUF 224 B). At show end today's set is reloaded from ROM.
- WRAM: 0 new bytes.
- ROM: L3 adds one frame (32 B) and a 16 B script. I3 adds 160 B of frames and an 8 B script, plus an estimated 100 B of banked switch code (not written).
- L3: the fire uses the same 2 tiles as today, plus a flare frame on the beat (`!script e:6 a:6 b:6 c:6 e:6 d:6 b:6 a:6` = 4 beats).
- I3: the snow uses wall tiles 2 and 3 instead of the aurora's tiles 0 and 1. The generator must give these two tiles their own animated slot range. No new tiles. The aurora holds still during the show.
- Snow and fire are BG tiles, not sprites. OAM is full (40), so snow cannot be sprites.
- Without the switch, both shows still work with today's stage animation.

## I1 generator changes (tools/gen_art.py only)

- Loops of 16 steps. Today's limit is 1-8 steps; a period of 16 is under SHOW_PERIOD_MAX 64.
- A per-step `dx`. Records already carry x, so this is one record per (performer, frame, dx). That gives about 22 records against 12 today.
- One frame width per file. The file is all 24 wide: the 16-wide figures sit in columns 0-15, and dx +4 puts them back on today's spots.

## ROM

- Baseline worktree build: ROM0 has 447 B free (real figure from the linker map).
- Scratch build with L3 and I3 staged together: ROM0 is unchanged at 447 B free.
- Venue data in that build: +1.8 KB in ROM_29/30 (ROM_29 drops to 33 B free, ROM_30 has 13.6 KB free).
- L1 and I1 were not measured on their own.
