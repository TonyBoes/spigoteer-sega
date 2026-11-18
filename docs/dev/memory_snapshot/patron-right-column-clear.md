---
name: patron-right-column-clear
description: Owner rule 2026-10-28 — patron front views keep the rightmost pixel column (x=15) empty
metadata:
  node_type: memory
  type: feedback
  originSessionId: 64761c6b-46f6-4217-a6f1-457b4de3152f
  modified: 2026-10-29T03:32:20.876Z
---

Owner, 2026-10-28: "Also on all patrons, try to keep the right most row of pixels clear." (he means the rightmost column, x=15, of the 16x16 front).

**Why:** not stated; likely ties to tile saving (a trimmed column saves pre-shift tiles, see "option 2" in the spigoteer-patrons skill) and spacing on the bar.

**How to apply:** every new or redrawn patron front keeps x=15 as index 0. Put it in every patron art brief. Q16 (2026-10-29) "yes": the current in-game fronts get it too, proposals first (docs/dev/concepts/right_column/). Related: [[art-another-pass-default]].
