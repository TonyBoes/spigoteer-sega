---
name: worktree-base-stale
description: "Agent worktrees start from the last pushed commit, not local main; brief agents to fast-forward to main first"
metadata:
  node_type: memory
  type: project
  originSessionId: 64761c6b-46f6-4217-a6f1-457b4de3152f
  modified: 2026-10-28T11:35:38.055Z
---

2026-10-28: isolated agent worktrees were created from an old commit (52eff2b), missing unpushed main work (skill rules, concept files, ptest). Two agents worked from stale skills (the v3 artist missed the gaps rule; the v4 artist missed the "Back views" section).

**Why:** the owner pushes himself, so origin lags local main by dozens of commits.
**How to apply:** every agent brief starts with "first run `git merge --ff-only main` in your worktree" (one command, reversible). Related: [[agents-reversible-actions]].
