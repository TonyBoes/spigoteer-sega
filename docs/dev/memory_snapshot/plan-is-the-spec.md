---
name: plan-is-the-spec
description: "The Graphics Atlas patron plan already decides palette layout (slots, keg move, splits); implement it, never ask the owner to re-decide it"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 64761c6b-46f6-4217-a6f1-457b4de3152f
  modified: 2026-11-01T05:52:53.743Z
---

When importing patrons, every palette/slot question is already answered by the plan on the Graphics Atlas (tools/artifacts/palette_plan/plan_data.py: PLANS, FIELD_MOVES keg BG 7 -> BG 1, SPLIT_PLAYFIELD, AUTO_OWN/AUTO_SHARE, per-look BG numbers). Engineering conflicts in carrying it out (windows on BG 1, ROM0, ISR timing) are ours to solve.

**Why:** 2026-11-01 I asked Q90 ("keg in bar colours?") to free palettes; owner: "Stop. Why are you trying to figure out how to free up pallets? All of the information for that was already in the Patreon plan in the Atlas."

**How to apply:** brief workers to implement the Atlas plan exactly (read its BG assignment per look, not a count by OBJ slot). Only go to the owner when the plan itself cannot be built within a hard rule (perf guard, budget), with numbers. See [[palette-labels-follow-plan]], [[think-before-relaying]].

Owner, after: "This is why we made the Atlas in the first place ... This is what I've been working on for entire week. I have no idea why you ignored all of my work." Every patron/palette brief starts from the per-venue table in docs/dev/queue_briefs/extra_looks_slots.md (regenerate it from the Atlas if the plan changes); check an agent's question against the Atlas before it reaches the owner.
