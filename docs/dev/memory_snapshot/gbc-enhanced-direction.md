---
name: gbc-enhanced-direction
description: "Owner direction 2026-10-21 - stay DMG compatible but GBC enhanced (gated features, DX icon); keep 1 px patron steps"
metadata:
  node_type: memory
  type: project
  originSessionId: 14228534-aec7-4761-a172-2f78e37cb357
  modified: 2026-10-21T02:57:07.091Z
---

Owner decisions, 2026-10-21:
- Patrons keep 1 px movement. He played a 2 px-step ROM; measured, 2 px gave no ARCADE gain and about -5 points late frames on CLASSIC 25.
- "More patrons on GBC": extra patron looks on Color only (VRAM bank 1, mid-screen palette reloads). DMG keeps 3 looks.
- The game stays DMG compatible but becomes GBC enhanced:
  - some features are gated off on DMG;
  - possibly a "DX" icon on the title menu when running on a GBC.
- He asked for an investigation of what that looks like and what to consider, music in particular. The candidate features are double-speed CPU, HDMA, WRAM banks and BG priority.
- The investigation report goes to scratchpad gbc_enhanced/REPORT.md, with a double-speed test ROM.

Owner answers 2026-10-21, renumbered Q8-Q18:
- Q8: double speed in. It feels a bit faster: no more lag, and no more music sag.
- Q9: wants to feel a DMG ROM capped at 30 fps; built.
- Q10 (decided after A/B recordings): the music stays at 60 Hz. Sailor sounded worse at 120 Hz and the title was no better. The music120-demo branch is shelved.
- Q11: 6 looks per venue on Color, at least 5.
- Q12 (decided): the new Color patron looks get their OWN palettes. The owner will free or reuse OBJ palettes himself so their sprite forms match. The atlas keeps a per-level 'free OBJ palettes' table.
- Q37 (decided): the tip coin uses Sal's palette (OBJ 0), not the mug's (which changes per venue); OBJ 5 then holds only the show palette. Q30 is dropped.
- Q13: new-look art waits until his pixel skill is refined. Saloon only for now.
- Q14: extra looks may show in boss fights only if they cost no performance.
- Q15: DX badge under the logo's right end; go.
- Q16: GBA brighter palettes, maybe, as a selectable menu option.
- Q17: wants to see a counter-lip depth example.
- Q18: sound meters "sounds cool".

**Why:** a compromise that keeps DMG players while using GBC hardware for variety and performance.
**How to apply:** design GBC-only features behind is_cgb gates with an unchanged DMG path, and say what the DMG player loses. Any GBC-only perf gain (double speed) does not excuse DMG regressions. Related: [[three-modes-decisions]], [[perf-no-long-loops]].

Extra patrons (owner, restated 2026-10-22): the new patron looks (Q11, up to about 8 per venue) are COLOR-ONLY. The DMG keeps the original 3 patrons per venue. The extras' tiles go in CGB VRAM bank 1, which the DMG lacks. I had forgotten this once and raised DMG tile limits again, so check it before raising DMG concerns about extra patrons.
