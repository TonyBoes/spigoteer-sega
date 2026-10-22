---
name: wait-loop-pgrep
description: never wait on pgrep -f <name> inside a shell whose own command line contains <name>; it self-matches forever
metadata:
  node_type: memory
  type: feedback
  originSessionId: 14228534-aec7-4761-a172-2f78e37cb357
  modified: 2026-10-11T12:14:34.474Z
---

A loop like `until ! pgrep -f "pytest"; do sleep 10; done` never ends, because pgrep matches the loop's own shell command line. Two of these ran for 8.5 h before the user asked what the long-running scripts were (2026-10-11).

**Why:** the user saw the stray processes and had to ask about them.
**How to apply:** wait on a PID (`while kill -0 $pid`), on a done-marker in the log, or use `pgrep -f "[p]ytest"`. Prefer run_in_background, which notifies on its own. Related: [[agent-stall-watchdog]].
