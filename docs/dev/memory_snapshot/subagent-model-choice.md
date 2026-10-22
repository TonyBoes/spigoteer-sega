---
name: subagent-model-choice
description: "Default ALL agents to Sonnet, Opus only by exception; usually ~3 at once, but the owner lifted the cap for 2026-10-15..17"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 14228534-aec7-4761-a172-2f78e37cb357
  modified: 2026-10-18T18:07:13.353Z
---

Default every subagent to Sonnet. Use Opus only by exception, and say why.

Concurrency:
- Usually about 3 agents at once, because they spend the owner's tokens.
- Exception: on 2026-10-15 the owner said "I can do as many agents as I need for the next two days." Until the end of 2026-10-17, fan out freely: one agent per independent job. They stay Sonnet.
- After 2026-10-17, go back to about 3 at once. Owner confirmed 2026-10-18: "back to three agents at a time. Sonnet only unless specified" (Fable/Opus only when he names them, e.g. the music Fable-spec / Opus-build split).

**Why:** the owner pays for tokens and controls the budget.
**How to apply:** pass model "sonnet" on every Agent call. Check the date before fanning out wide. Related: [[agent-stall-watchdog]].
