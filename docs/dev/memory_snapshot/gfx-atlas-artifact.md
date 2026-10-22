---
name: gfx-atlas-artifact
description: "Owner wants a kept-up-to-date \"graphics atlas\" artifact (per-screen palettes/tiles/OAM/animations); regenerate + republish after merges"
metadata:
  node_type: memory
  type: project
  originSessionId: 14228534-aec7-4761-a172-2f78e37cb357
  modified: 2026-10-21T19:25:00.100Z
---

Owner, 2026-10-21: an artifact that lets him pick any screen (level per venue, menus, the map, bosses, mini-games, story, credits) and see its graphics usage, kept updated as graphics change. It shows:
- palettes in use and their colours, which change or swap, and which are permanent across levels;
- tiles used and free, by region;
- the attribute map;
- OAM and per-line sprite counts;
- animation examples.

It is built by tools/gfx_atlas/build.py (`make atlas` writes out/atlas/), generated from the real ROM in PyBoy on DMG and CGB. It is published as a multi-file artifact: index.html, data/*.js, PNGs.

Owner, 2026-10-21: the atlas is for strategy and design decisions (budgets), not technical documentation.
- Sections start collapsed, each with a one-line budget summary.
- Show constructed objects (Sal's poses and so on), with their pieces on request.
- Explanations go under info toggles. OAM tables, screenshots, counts and sources go behind "more information".
- Keep it uncluttered. Apply the same rule to any future page for him: summary first, detail on demand.

**Why:** he is revising graphics and needs one place to see the hardware budgets per screen.
**How to apply:**
- After every merge that touches art, palettes or screens, run `make atlas` on main and republish to the SAME artifact URL (same file path in this session; from a new session, find it with Artifact list and pass `url`).
- The page shows the commit it was generated from, so a stale page is visible.

Related: [[gb-pixel-art-skill]], [[gbc-enhanced-direction]].
