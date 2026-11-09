---
name: merge-before-review
description: "Owner 2026-11-09 (test batch 3, S1) - only a fix for a problem already on main may merge before the owner's review, and the report's first line must say so with the reason"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 64761c6b-46f6-4217-a6f1-457b4de3152f
  modified: 2026-11-09T22:30:03.578Z
---

A fix for a problem already on main may merge before the owner reviews it, if the report says so in its first line, with the reason. Everything else waits for his review.

**Why:** on 2026-11-09 I merged test batch 2's C1+C2 before review because it fixed a race batch 2 had put on main; the owner then wrote this rule (docs/dev/notes/test_batch3_brief_2026-11-09.md, S1).

**How to apply:** before any merge of owner-reviewed work, ask: is this fixing something already broken on main? If not, wait. If yes, merge and open the reply with that fact. Procedure in docs/dev/SUPERVISOR.md.
