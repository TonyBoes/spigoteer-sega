---
name: verify-quick-for-map-art
description: Owner Q11 (2026-11-08), updated 2026-11-09 (test batch 1, item 3): verify.sh default is the ~3 min stage set (plain make with make release and make cfall beside it; then pytest and slow ds/hr side by side); FULL=1 uses make -B, adds release-only tests and slow fade, CBUILD=1 adds the C-build pytest; QUICK=1 is a no-op alias
metadata:
  type: feedback
---
Owner 2026-11-08, Q11: "yes. Of course." to a 7-minute check for map and art changes.

**Why:** the full verify spent 7.4 min on slow fade tests (irrelevant to map/art) and 5.4 min on C-build tests that are on hold (~215 known fails, see [[c-build-speed-not-required]]).
**How to apply (2026-11-09):** brief gb-runner with plain `tools/dev/verify.sh <worktree> <name>` (the default is the old QUICK stage set, `QUICK=1` still accepted). Add `FULL=1` when src/ engine, fades, timing or music change, and before any release. Add `CBUILD=1` only before a porting release while C tests are on hold. Procedure in docs/dev/SUPERVISOR.md step 6.
