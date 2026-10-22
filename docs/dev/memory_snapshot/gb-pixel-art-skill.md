---
name: gb-pixel-art-skill
description: "Owner's gb-pixel-art skill (installed ~/.claude/skills/gb-pixel-art); brief every art agent to follow it"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 14228534-aec7-4761-a172-2f78e37cb357
  modified: 2026-10-21T01:20:25.212Z
---

On 2026-10-18 the owner supplied his own skill, `gb-pixel-art` (the uploaded .skill zip). I installed it at `~/.claude/skills/gb-pixel-art/` and kept a copy in the session scratchpad.

The skill contains:
- hardware and palette rules, and a per-asset pipeline;
- a QA checklist, plus `scripts/gb_art_lint.py` and `scripts/tiled_preview.py`. Both only read images and write PNGs; I reviewed them.

An agent using it drew a map igloo that the owner called "much better" than ours. It is saved as scratchpad `story_map/map_igloo_owner_v1.png`: 24x24, 4 colours, 9 tiles.

**Why:** our agents' art was repeatedly judged crude or unlike the game. The owner's skill produced the quality he wants.
**How to apply:**
- In every art brief (sprites, tiles, map pieces, boss art), tell the agent to read `~/.claude/skills/gb-pixel-art/SKILL.md` and the references it names, follow its pipeline, and run its lint script. A new session also lists it as a skill.
- Use the owner's igloo as the quality bar for map art.
- Owner 2026-10-18: his igloo agent was told to draw from scratch. Art agents should not feel bound by earlier drafts' designs. Keep only the owner's rulings on content and the hardware budgets.

2026-10-21: the owner updated the skill (v2: briefs.md template, section 9 self-audit table, portraits.md, figures 19-20, portrait_check.py). I installed it and backed up the old copy in scratchpad skill_v2/old_installed.
- His skill agent's process rule: use the briefs.md template.
- For a batch, ask for ONE figure first, and check its self-audit table (rows 1-3: hand-placed, clean-up log, 1x comparison) and its 1x preview beside the quality bar myself before approving the rest.
- Patron spec for briefs: scratchpad PATRON_SPEC.md.

2026-10-20 saloon patron round 1 failure, so put these in every art brief:
- The agent auto-outlined with a script and mirrored the back views. Its faces came out "arrowhead shaped": tapering skin blocks plus a hard 1 px outline on every step.
- It skipped part of the skill's reading.
- Rules to state: every pixel hand-placed (scripts may only convert, preview, lint and build); read every reference and figure; separate adjacent features by DMG value (the prospector's beard blended into his face).
- Owner's art verdicts: "all of the women are worse"; the outlaw was strongest.
- He takes skill-compliance failures back to his own skill-building agent, so report deviations with quotes.

Related: [[art-in-house]], [[story-map-decisions]].
