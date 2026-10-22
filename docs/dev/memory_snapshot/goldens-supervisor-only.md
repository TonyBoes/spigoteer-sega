---
name: goldens-supervisor-only
description: I (the supervisor) may replace goldens after checking the diff; independent agents must not replace them
metadata:
  node_type: memory
  type: feedback
  originSessionId: 14228534-aec7-4761-a172-2f78e37cb357
  modified: 2026-10-15T18:33:52.131Z
---

On 2026-10-15 the owner said: "I don't care if you as a supervisor change goldens. I just don't want independent agents doing it."

**Why:** the owner wants one accountable reviewer looking at every changed picture, not agents regenerating screenshots to turn their own runs green.
**How to apply:**
- In agent briefs, tell agents NOT to replace goldens. They should list each changed golden with its diff bounding box and the reason, using a read-only script.
- I then check each diff is confined to what the change should touch, replace it myself, and name it in the commit.
- New goldens are still fine for agents to add.
- This supersedes asking the owner before each replacement. CLAUDE.md's rule still stands: never regenerate all goldens.

Related: [[agents-reversible-actions]].
