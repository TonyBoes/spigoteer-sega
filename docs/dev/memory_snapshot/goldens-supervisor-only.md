---
name: goldens-supervisor-only
description: I (the supervisor) may replace goldens after checking the diff; independent agents must not replace them
metadata:
  node_type: memory
  type: feedback
  originSessionId: 14228534-aec7-4761-a172-2f78e37cb357
  modified: 2026-10-25
---

On 2026-10-15 the owner said: "I don't care if you as a supervisor change goldens. I just don't want independent agents doing it."

**Why:** the owner wants one accountable reviewer looking at every changed picture, not agents regenerating screenshots to turn their own runs green.
**How to apply:**
- In agent briefs, tell agents NOT to replace goldens. They should list each changed golden with its diff bounding box and the reason, using a read-only script.
- I then check each diff is confined to what the change should touch, replace it myself, and name it in the commit.
- New goldens are still fine for agents to add.
- This supersedes asking the owner before each replacement. CLAUDE.md's rule still stands: never regenerate all goldens.

Repeated 2026-10-26, after an auto-mode denial stalled three branches: "You are always ok to update the goldens. Just not the agents." Standing permission: copy checked goldens without asking; a classifier denial of a golden copy is not a reason to wait on him.

Related: [[agents-reversible-actions]].

Method from 2026-10-25 (owner approved): brief `gb-golden-check` (read-only, Sonnet) with the worktree, the failing goldens and the intended change. It runs `tools/dev/golden_bbox.py` and returns a table marking each golden EXPECTED, UNEXPECTED or UNSURE, plus an old/new/diff sheet. I still copy every golden myself and name it in the commit; I open the pictures for the UNEXPECTED and UNSURE rows and decide those.
