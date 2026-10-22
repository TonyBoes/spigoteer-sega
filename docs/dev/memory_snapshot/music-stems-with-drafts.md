---
name: music-stems-with-drafts
description: "Every music draft sent to the owner comes with per-channel solo WAVs, plainly labelled, plus a short STEMS.md"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 14228534-aec7-4761-a172-2f78e37cb357
  modified: 2026-10-17T16:23:12.547Z
---

Every time a music version or draft goes to the owner, also send one solo WAV per Game Boy channel (ch1 harmony, ch2 lead, ch3 bass/wave, ch4 drums/noise), named in plain words, with a short STEMS.md that says what each channel plays and what changed.

**Why:** the owner (not a musician) asked on 2026-10-17 to understand how the tunes are built, channel by channel.

**How to apply:** tell music agents to render stems via the harness NR51 mask (tools/promusic.py option), keep _24k copies under the 30 MB upload limit, and send the stems along with the full and pause-mix files. Related: [[pyboy-audio-stale-row]].
