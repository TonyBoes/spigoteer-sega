---
name: verify-quick-for-map-art
description: Owner Q11 (2026-11-08): map/art branches use QUICK=1 tools/dev/verify.sh (~7 min); full 20-min verify only for engine/fade/timing changes and releases
metadata:
  type: feedback
---
Owner 2026-11-08, Q11: "yes. Of course." to a 7-minute check for map and art changes.

**Why:** the full verify spent 7.4 min on slow fade tests (irrelevant to map/art) and 5.4 min on C-build tests that are on hold (~215 known fails, see [[c-build-speed-not-required]]).
**How to apply:** brief gb-runner with `QUICK=1 tools/dev/verify.sh <worktree> <name>` for map/art/asset-only branches; the full run when src/ engine, fades, timing or music change, and before any release. Procedure in docs/dev/SUPERVISOR.md step 6.
