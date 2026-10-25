---
name: subagent-model-choice
description: "Spawn agents by type: gb-worker/gb-artist/gb-golden-check on Sonnet, gb-runner on Haiku; Opus/Fable only when the owner names them; ~3 at once"
metadata:
  type: feedback
  modified: 2026-10-25
---
Spawn agents by their `.claude/agents/` type, not as general-purpose agents with a model argument:
- `gb-worker` (Sonnet, own worktree): every code and feature brief.
- `gb-artist` (Sonnet, own worktree, gb-pixel-art skill preloaded): every art brief.
- `gb-golden-check` (Sonnet, read-only): golden diffs before the supervisor replaces them.
- `gb-runner` (Haiku, no edits): verify runs, atlas and Pocket Player builds, orphan checks, cleanup lists, docs sync.

Opus or Fable only when the owner names them (e.g. the music Fable-spec / Opus-build split); then pass the model on that call and say why.

Concurrency: about 3 agents at once. (The 2026-10-15..17 exception, when the owner let agents fan out freely, is over.)

History: owner 2026-10-18, "back to three agents at a time. Sonnet only unless specified". Owner 2026-10-25 approved Haiku for the mechanical gb-runner jobs.

**Why:** the owner pays for tokens and controls the budget.
**How to apply:** check the date before fanning out wide. Related: [[agent-stall-watchdog]], [[context-hygiene]].
