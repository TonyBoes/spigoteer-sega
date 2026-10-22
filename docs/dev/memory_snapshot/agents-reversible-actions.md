---
name: agents-reversible-actions
description: subagents may only take actions that are easy for me to reverse at review; no amend/rebase/reset of their own
metadata:
  node_type: memory
  type: feedback
  originSessionId: 14228534-aec7-4761-a172-2f78e37cb357
  modified: 2026-10-12T14:57:45.401Z
---

Let subagents do only what is easy for me to reverse when I review: new commits on a branch (a fresh branch from main when moving old work over, e.g. by cherry-pick or re-applying), never amend, rebase, reset or force. Rebasing onto main and merging stay my job.

**Why:** owner, 2026-10-12, after an agent was denied `git commit --amend && git rebase main`: "i recommend only letting the agent do things that are easy for you to reverse on your review."
**How to apply:** put this in every coding agent's brief. Related: [[agent-stall-watchdog]], [[subagent-model-choice]].
