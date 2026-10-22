---
name: agent-stall-watchdog
description: Always arm a stall watchdog on background subagents; the user has caught stuck agents several times
metadata:
  type: feedback
---
When launching a background subagent, arm a Monitor that alerts if its transcript (~/.claude/projects/-workspace/<session>/subagents/agent-<id>.jsonl) has no activity for ~15 min, and re-arm it every 30 min.

**Why:** the user had to ask about stuck agents four times; once an agent hung for 5.5 h on a single tool call after a permission denial.
**How to apply:** brief agents not to retry denied commands, and give each one an explicit stopping point. Check the watchdog rather than waiting for the user to notice.
