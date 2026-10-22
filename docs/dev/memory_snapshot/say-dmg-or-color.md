---
name: say-dmg-or-color
description: When the owner asks for a new visual feature, say whether it fits DMG too or only Color (DMG budgets are tight); keep tile margin for late DX decorations
metadata:
  type: feedback
---

For every visual feature the owner asks for, say up front whether it fits the DMG as well, or only Color/DX, and why (which budget). He expects the DMG budgets to be tight.

He also wants tile margin kept for late decorations, most likely DX-only.

**Why:** owner, 2026-10-22: "if I ask for things, you can let me know if it fits in DMG or only color, as I imagine our DMG budgets are getting tight"; "I just want to make sure we have some margin in case there is some kind of late decoration".
**How to apply:**
- Check the budget the feature uses: background tiles (bank 0/1), sprite-only tiles, OAM / per-line sprites, palettes, ROM0, WRAM.
- Prefer sprite-based designs, which can use the empty bank-1 sprite-only block on Color.
- Don't spend the bank-1 margin without saying so.

Related: [[gbc-enhanced-direction]], [[saloon-patrons-sunday]], [[palette-plan-artifact]].
