---
name: branch-cleanup-list-first
description: "When tidying git branches, list exactly what will be deleted first; never delete by pattern branches this session didn't create"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 14228534-aec7-4761-a172-2f78e37cb357
  modified: 2026-10-16T01:48:08.323Z
---

On 2026-10-15 I tidied up after merges with a pattern (`worktree-agent-*`, `*-v2`, `integ*`). It also deleted seven older `worktree-agent-*` branches from earlier sessions that I had never checked.

I recovered by saving every unreachable commit tip under hidden `refs/recovered/<mmdd-HHMM>-<hash>` refs: 128 refs, including all the old stash and WIP snapshots.

**Why:** branches from earlier sessions can hold unmerged or parked work that the owner or an earlier plan wanted kept. Deleting them silently breaks the "only easy-to-reverse actions" rule ([[agents-reversible-actions]]).
**How to apply:**
- Delete only branches I created or merged in this session, by exact name.
- Print the list before deleting.
- To get something back: `git for-each-ref refs/recovered`, then `git branch <name> refs/recovered/<ref>`.
