---
name: color-perf-double-speed
description: "Owner Q92 2026-11-01: Color speed checks run at double speed (as shipped); DMG checks stay strict"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 64761c6b-46f6-4217-a6f1-457b4de3152f
  modified: 2026-11-01T15:02:50.405Z
---

Owner 2026-11-01, Q92: "A" = the Color ([cgb]) speed checks run at double speed, the way the game ships (owner Q8 2026-10-21 "double speed in"; src/main_cold.c cpu_fast; conftest patches ROM 0x3FFE to 0 only for goldens/old tests). DMG speed checks are unchanged and strict.

**Why:** no Color player runs at normal speed; a normal-speed [cgb] failure (Q91, withdrawn) is not a real limit.
**How to apply:** measure and guard Color perf at double speed; never call a Color-only perf failure a hard limit until measured at double speed. Goldens stay at normal speed. Still never loosen a guard without the owner. See [[plan-is-the-spec]], [[gbc-enhanced-direction]].
