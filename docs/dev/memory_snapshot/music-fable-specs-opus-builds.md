---
name: music-fable-specs-opus-builds
description: "Song arrangements after batch 1: the Fable agent writes per-song spec files, Opus agents implement and record them"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 14228534-aec7-4761-a172-2f78e37cb357
  modified: 2026-10-17T22:24:14.752Z
---

From music batch 2 on (owner, 2026-10-17): the Fable arranger writes one self-contained instruction file per song (docs/proarr/specs/<song>.md on branch promusic: per-channel note grids, instruments/effects, pause-mix intent, costs, acceptance checks); an Opus agent (model "opus") implements, records (full, pause mix bass+drums, 4 stems, _24k copies) and reports. Fable does not implement those songs itself.

**Why:** owner's explicit split of design vs build for the remaining songs.
**How to apply:** when Fable reports a spec batch, spawn one Opus agent per spec batch with the spec paths; owner hears results with stems ([[music-stems-with-drafts]]). Pause mix = bass + drums.
