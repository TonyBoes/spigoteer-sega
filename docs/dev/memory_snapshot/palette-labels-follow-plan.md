---
name: palette-labels-follow-plan
description: When the owner names a palette slot (BG1, OBJ2...) he means the slot as the current Palette Plan shows it, not the game today
metadata:
  type: feedback
---

When the owner names a palette slot, such as "BG1's palette", he means that slot as the current Palette Plan page shows it, not as the game uses it today.

Example: he said "BG0 gets BG1's colours" and meant the keg/spout colours that the plan had moved into BG 1. He did not mean the HUD colours that BG 1 holds in the shipped game.

**Why:** owner, 2026-10-21: "as we talk about this, I will be using palette labels from whatever the current plan shows."
**How to apply:** before acting on a palette instruction, look up the slot in tools/artifacts/palette_plan/build.py (PLANS, FIELD_MOVES), or on the published page. Don't mock up the alternative reading.

Related: [[palette-plan-artifact]].
