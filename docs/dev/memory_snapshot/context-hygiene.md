---
name: context-hygiene
description: Keep the supervisor's context small - helpers do mechanical steps, handoff then /clear or /compact at milestones, contact sheets for images
metadata:
  type: feedback
  modified: 2026-10-25
---
Week to 2026-10-24: the supervisor averaged 515k tokens of context per call over 1,950 calls (45% of usage). 97% of all cost was re-reading context; output was 3%. The weekly limit ran out on Thursday.

**Why:** every call re-reads the whole conversation, so cost is context size times number of calls.
**How to apply:**
- Mechanical steps (scripts, logs, page builds, listings, syncs) go to `gb-runner`; golden diffs go to `gb-golden-check`.
- After each merge-and-report, update the handoff, then tell the owner "safe to /clear" (no agents running) or "good point to /compact" (agents running). Say so before he steps away too. He types these commands; I can't.
- Ask agents for ONE labelled contact sheet per review instead of many stills.
- Grep, then read ranges; never read PLAN.full.md or ALL_AGENT_BRIEFS.md whole.
- Backstop: `autoCompactWindow` 400000 in .claude/settings.json; CLAUDE.md "Compact instructions" say what survives.

See docs/dev/SUPERVISOR.md, "Keep the supervisor's context small". Related: [[subagent-model-choice]], [[agent-stall-watchdog]].
