---
name: perf-no-long-loops
description: Owner sees no slowdown in play; small perf tweaks OK, no hours-long optimization loops unless they report a problem
metadata:
  type: feedback
---
Do not schedule a speed milestone or long optimization loops. Small, cheap perf tweaks are fine.

**Why:** owner playtested 2026-10-10 and saw no slowdown; called long perf work a waste of tokens until they see a problem.
**How to apply:** keep perf guards in tests, measure new features, but only optimize when a feature regresses the numbers or the owner reports slowdown. Related: [[no-throwaway-fixes]].
