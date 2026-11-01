---
name: record-decisions-immediately
description: "Write every owner decision, plan and procedure down in the same reply (Atlas / QUEUE.md / memory) and check them before briefing or asking"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 64761c6b-46f6-4217-a6f1-457b4de3152f
  modified: 2026-11-01T06:07:12.320Z
---

Owner 2026-11-01: "write every standing decision and plan into the queue or memory notes as soon as i make it. You keep forgetting plans that we've made and procedures I want you to follow. The Atlas has been an absolute mess. And whenever it came time to follow it, you didn't follow it. I need to know how we're going to prevent this in the future."

**Why:** I briefed the patron import without his Atlas plan, relayed already-decided questions (Q90), and the Atlas itself showed wrong numbers (Lodge -1 free BG, INES on two BG palettes) that nobody caught.

**How to apply:** the procedure is in docs/dev/SUPERVISOR.md, "Owner decisions and plans: write first, then follow":
1. Same reply, before acting: patron/palette/art decision -> Atlas (plan_data.py + build.py LOG, republish); plan/task -> QUEUE.md; standing rule/procedure -> memory note. Quote him. Commit.
2. Before every brief: grep QUEUE.md + memory index for the topic; patron/palette briefs start from docs/dev/queue_briefs/extra_looks_slots.md ("implement as written").
3. Before asking him: check QUEUE, memory, Atlas; ask only on a hard limit, with numbers.
4. When the Atlas looks wrong: fix the generator and add a self-check.
See [[plan-is-the-spec]], [[think-before-relaying]].

Owner 2026-11-01 (exact rule, now in CLAUDE.md project rules and SUPERVISOR.md): "When the owner gives a rule, decision or plan, save it to its file in the same turn (memory note for standing rules, QUEUE for plans) before replying, and say where it was saved. Conversation is not storage."
