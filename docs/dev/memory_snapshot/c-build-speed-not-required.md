---
name: c-build-speed-not-required
description: "Owner 2026-11-01: the C build (make cfall, game-c.gb) may fail speed tests; only correctness failures matter there"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 64761c6b-46f6-4217-a6f1-457b4de3152f
  modified: 2026-11-01T21:52:21.767Z
---

Owner 2026-11-01: "I'm not terribly concerned about the c version passing all of its speed tests the reasons we're doing assembly is so that we can get the speed up. I expect for there to be slow down in the c version. Did it fail for some other reasons?"

**Why:** the asm pass exists for speed; the C build is the porting reference ([[asm-pass-keep-c]]), not a shipped ROM.
**How to apply:** in verify.sh's C-build run (now opt-in: `CBUILD=1`, 2026-11-09), speed/timing guard failures (perf, late frames, "ends on time") are expected and do not block a merge. Wrong pictures, wrong behaviour, crashes, hangs and asm/C mismatches still block. When a C-build screen differs only because the slower C code lands a mid-frame write late, say so with evidence; don't call it a speed-only failure without checking.

Owner 2026-11-01 (later): "You can hold off for running tests on the C version until we get everything imported. Right now, all I care is that the assembly version comes out correctly. We can go back and work on the C version before we put it out for porting to other platforms."
**How to apply now:** during the patron import, no C-build test runs (verify's default skips them; `CBUILD=1` is for the pre-porting release) and no C-build fixes (make cfall must still link so the C twin exists, and stays in verify's default). C-build correctness work is queued for after the import, before any porting release.
