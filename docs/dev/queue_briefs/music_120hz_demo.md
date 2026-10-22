BRIEF (queued 2026-10-21, 2nd in the queue; model: Opus, per the music-builds memory)

Spigoteer (GBDK-2020; hUGEDriver music). Work in your own worktree. Read /workspace/CLAUDE.md, then obey scratchpad/decisions/rules_code.txt. Throwaway: nothing is merged.

The owner wants SIDE-BY-SIDE RECORDINGS to judge a "120 Hz music tick" on the Game Boy Color. Today hUGEDriver runs once per frame (60 Hz). Effects such as vibrato, pitch slides (portamento), volume fades/envelopes and arpeggios update once per driver tick. With CGB double speed there is CPU to run the driver twice per frame. Build that, so the effects update 120 times a second while notes, tempo and pitch stay the same.

1. Base: the double-speed work. Use the latest double-speed branch: the real implementation if it's merged by then, else exp/THROWAWAY-gbc-doublespeed at de47256.
2. Make a throwaway CGB build that calls the driver twice per frame, with each song's ticks-per-row doubled, so row timing (tempo) is identical. Check how hUGE handles the speed / ticks-per-row value, and whether any effect parameters are per-tick amounts that must be halved to sound the same (e.g. slide speed, vibrato rate). The goal is the SAME musical intent, only smoother.
3. Record, with PyBoy audio, 20-30 s of the same passage at 60 Hz and at 120 Hz, from 4 tunes that use the most effects: grep the song data for vibrato/portamento/volume slides, and pick the title tune if it qualifies.
   - Memory note: when capturing PyBoy audio, slice the buffer per frame as ndarray[:raw_buffer_head//2], or the recording crackles.
   - Output mp3 (and wav), named <tune>_60hz.mp3 / <tune>_120hz.mp3.
   - Also make a short A/B file per tune: 8 s of 60 Hz, a click, then the same 8 s at 120 Hz.
4. Also a demo ROM: /workspace/out/test_roms/spigoteer-music120-demo.gb. SELECT on the soundtrack player toggles 60/120, if that's easy; otherwise 120 only.
5. Put everything in scratchpad/music120/, with a short NOTES.md:
   - what changed;
   - which effects differ audibly, by your own analysis (e.g. a pitch trace of a vibrato note at 60 vs 120);
   - the CPU cost per frame;
   - the risks (the DMG stays at 60).
Kill every process you start.
