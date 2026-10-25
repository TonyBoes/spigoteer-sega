---
name: spigoteer-music
description: How Spigoteer's music is arranged, built, recorded, delivered and integrated (hUGEDriver on GBDK) - the Fable-spec / Opus-build split, the pause mix, the shared kit and instruments, CPU and bank limits, PyBoy recording, stems and the owner's listening files. Use it for any task that touches a song, arrangement, instrument, drum kit, jingle, music CPU or bank budget, audio recording, stems, or the soundtrack player, even if the brief only names a tune.
---

# Spigoteer music

Standing decisions are dated; newer owner words in the brief, `docs/dev/notes/QUEUE.md` or memory win.

## Who does what (owner, 2026-10-17)
- **Arranger (Fable, only when the owner names it):** writes one self-contained spec per song,
  `docs/proarr/specs/<song>.md` on branch `promusic`: per-channel note grids, instruments and effects, the pause-mix
  intent, costs and acceptance checks. Conventions, the kit, the instruments and the build/record/deliver procedure
  are in `docs/proarr/specs/README.md`. Fable does not build those songs.
- **Builder (Opus, per the owner's split):** implements and records each spec on `promusic`, reusing
  `tools/proarr.py` and the batch pattern in `docs/proarr/BATCH_<n>.md`.
- **Integrator (`gb-worker`, Sonnet):** ports owner-approved auditions into `tools/songs.py` and `tools/gen_music.py`.
  Never merge `promusic`.
- Audition work never touches `src/`, `tools/songs.py` or `tests/golden/`.

## Musical rules
- Every tune is a public-domain melody: keep the melody as it is. Harmony, bass and drums are our own arrangement.
  Write nothing from memory of any recording or game.
- **Pause mix = bass (ch3, wave) + drums (ch4, noise) only, NR51 0xCC.** It must be a pleasing groove on its own;
  the melody (ch2) and harmony (ch1) drop out when paused.
- Use the shared kit and instruments from batch 0 (`LEAD_PRO`, `BASS_PRO`, the corrected noise kit). Note any song
  where another voice would suit it better rather than silently changing it.
- The arpeggio-stab flutter "doesn't blend" (owner): use it only where it truly fits.
- The music stays at 60 Hz (Q10, after A/B recordings; the 120 Hz branch is shelved). CGB double speed does not
  change music pacing.
- Spec ambiguous or a check fails: make the smallest faithful fix and record it under "Builder notes" in the spec.
  Do not silently redesign.

## Limits (measure, don't estimate)
- Every tune's worst `music_tick` call must stay at or under **18 lines**, measured in game over a whole pass with
  the per-call meter (`tests/test_music_cpu.py` covers every tune).
- Banks are tight (bank 10 and bank 2 especially); streamed songs and jingle patterns live in higher banks. Pattern
  drums cost 192 B per order: where bytes are tight, prefer the groove player with a better kit.
- Report every bank, ROM0 and WRAM before and after.
- Sakura stays **1344 frames a pass**: the Sumo and Taiko Pour depend on it.
- The credits end and fade correctly (NR32 100 / 50 / 25 %).

## Recording
- PyBoy: after each 1-frame tick take `pb.sound.ndarray[:pb.sound.raw_buffer_head // 2]`, not the whole array (a
  stale row makes recordings crackle at about 60 Hz). `tools/dump_audio.py` does this correctly; old scratchpad
  recorders did not.
- Run `make` after any merge before single tests or recordings, or they use a stale `build/`.
- Integrated tunes: record in game and compare against the audition WAVs.

## What the owner gets with every version (he is not a musician)
For each song, in the folder the brief names:
- `<song>_original_full.wav`, `<song>_original_pausemix_bass_drums.wav`
- `<song>_<ver>_full.wav`, `<song>_<ver>_pausemix_bass_drums.wav`
- four stems: `<song>_<ver>_ch1_harmony`, `_ch2_melody`, `_ch3_bass`, `_ch4_drums` (solo via the NR51 mask:
  `promusic.py stems` or `music_drafts.py STEMS=1`)
- a `_24k` copy of every file, made by averaging sample pairs, so each is under the 30 MB upload limit
- `STEMS.md`: what each channel plays and what changed, in plain words
- `BATCH_<n>.md`: a plain-words paragraph per song (what changed and why) plus its ROM and CPU cost

Deliver in batches of 3-4 songs, most-heard first (title, first venues, menus), and stop after each batch for the
owner's feedback. Anything he must decide goes on the Open Questions page (see `spigoteer-review-pages`).

## Acceptance checks for a build
The harmony check, row counts, the `music_tick` worst case, no clipping, and register traces where the spec asks.

## Where the code is
`src/music.c`; `tools/songs.py`, `gen_music.py`, `harmony.py`, `check_music.py`, `trace_music.py`, `music_rig.py`,
`rec_music.py`, `dump_audio.py`; on `promusic`: `tools/proarr.py`, `docs/proarr/`.
