---
name: pyboy-audio-stale-row
description: "PyBoy sound.ndarray returns one stale row per frame (801 for 800); slice [:raw_buffer_head // 2] or recordings crackle"
metadata:
  node_type: memory
  type: reference
  originSessionId: 14228534-aec7-4761-a172-2f78e37cb357
  modified: 2026-10-12T16:47:19.151Z
---

When recording audio with PyBoy (any mp3 for the owner), take `pb.sound.ndarray[:pb.sound.raw_buffer_head // 2]` after each 1-frame tick, not the whole ndarray. The whole array has a stale 801st row every frame, which made every music mp3 before 2026-10-12 crackle at ~60 Hz. tools/dump_audio.py was fixed in 5032c4f; the scratchpad recorders (music5..music10 rec scripts) still have the bug, while music11/scripts/rec11.py is clean.

Also: rebuild (`make`) in /workspace after a merge before running single tests, or they run against a stale build/ (happened 2026-10-12).
