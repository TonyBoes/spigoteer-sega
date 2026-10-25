---
name: agent-stall-watchdog
description: Arm tools/dev/watch_agents.sh for background subagents; it wakes the session only on a real stall
metadata:
  type: feedback
  modified: 2026-10-25
---
When launching background subagents, run `tools/dev/watch_agents.sh 15 <agent-id>...` with the Bash tool in the background. It stays silent and exits (waking the session) only when an agent's transcript (~/.claude/projects/-workspace/<session>/subagents/agent-<id>.jsonl) has had no activity for 15 min. Restart it with the current list whenever an agent starts or finishes; it stops the previous copy through out/watchdog.pid.

Replaced 2026-10-25: re-arming a Monitor every 30 min. Each re-arm and each check was a full supervisor turn, re-reading about 500k tokens of context.

**Why:** the owner had to ask about stuck agents four times; once an agent hung for 5.5 h on a single tool call after a permission denial. He also pays for every supervisor turn.
**How to apply:** brief agents not to retry denied commands, and give each one an explicit stopping point. Trust the watchdog rather than polling.
