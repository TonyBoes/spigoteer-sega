---
name: one-full-test-run
description: "Owner Q12 (2026-11-08) - one full test run per change; agents run targeted tests, verify is the full run, main reruns only if other merges landed"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 64761c6b-46f6-4217-a6f1-457b4de3152f
  modified: 2026-11-09T03:40:24.269Z
---

One full test run per change. Agents run only the tests for the area they touch while working (plus `make` and `make check`); the verify run (QUICK for map/art, see [[verify-quick-for-map-art]]) is the single full run; after a fast-forward merge of the verified tip, no rerun on main. Rerun on main once only when other merges landed in between.

**Why:** owner asked why work got slower; each change was running the full suite 4-6 times (~25-45 min). Owner: "q12) yes".

**How to apply:** put "targeted tests only; verify does the full run" in every gb-worker brief; procedure in docs/dev/SUPERVISOR.md steps 6-7.
