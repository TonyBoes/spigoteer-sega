---
name: spigoteer-review-pages
description: How to rebuild, update and republish Spigoteer's review pages for the owner (Graphics Atlas, Pocket Player browser emulator, Open Questions, Palette Plan, Review Board), keep their sources in the repo, and present questions and pictures the way the owner wants. Use it after any merge that changes art, palettes, screens or gameplay, whenever a numbered question is asked or answered, and whenever something must be shown to the owner, even if the brief only says "update the page".
---

# Spigoteer review pages

The pages are private claude.ai Artifacts under the owner's account. `tools/artifacts/README.md` has each page's URL,
source and exact build steps; read it before building. **Always republish to the SAME URL** (pass the page's `url`), so
the owner's links keep working. If you cannot publish (no Artifact tool, as in a helper agent), build everything and
report the exact list of files to publish.

## After a merge to main
1. **Pocket Player** (if gameplay changed): pack ROMs with `tools/artifacts/pocket_player/make_roms.py` (see its
   header) next to copies of `index.html` and `wasmboy-ts-core.patched.js`. The ROM menu is `ROM_LIST` in
   `index.html`; bundled ROMs are `roms/<id>.js`. Keep "main" as the latest main unlocked build; add test ROMs when a
   question opens and remove them when it closes. Publish `index.html` with the core and `roms/*.js` as files.
2. **Graphics Atlas** (if art, palettes or screens changed): `make atlas` on main (about 2 min) writes `out/atlas/`.
   Publish `out/atlas/index.html` with every other file there, about 390 files, in two batches of at most 255; the
   second publish adds to the first. The page shows the commit it was built from.
3. **Palette Plan** (if palettes or patrons changed): after `make atlas`, run
   `python3 tools/artifacts/palette_plan/build.py`; publish `index.html` alone. Owner decisions go into PLAN and a
   LOG line in `build.py`.
4. **Open Questions** (if a question was asked or answered): update the cards, the count and the stamp.
5. Copy every changed page source and its media into `tools/artifacts/` and commit (sources must survive a lost
   session). ROM packs and atlas output are generated and not committed.

## Keep these behaviours when editing pages
- Pocket Player is WasmBoy 0.7.1's TypeScript core (GPL-3.0) with two fixes (CPL masks A to 8 bits; VBK, BCPD and OCPD
  read back). Keep them. iPhone sound: `wakeAudio()` retries inside every finished tap (touchend, click, pointerup)
  until the audio context runs. Keep it. Pocket Player is for feel tests on a phone, not accuracy.
- The Atlas is for budget decisions, not documentation: sections start collapsed with a one-line budget summary;
  explanations and tables sit behind toggles. Summary first, detail on demand, on every page.

## Questions and pictures for the owner
- A number (Qn, continuing from the last; never reused) goes ONLY on a direct question or decision for him. Findings,
  status and your own technical choices get no number. Batch questions when most agents have reported.
- Every open Qn has a card on Open Questions: a short highlighted ask, 2-3 context bullets, then its pictures or GIFs.
  Remove the card when he answers. In chat, state the question briefly and point to the page.
- GIFs do not animate in chat: motion goes on a page. Files such as ROMs cannot be downloaded from a page: send them
  in chat, and name them on the card.
- The Review Board holds reference animations only; questions live on Open Questions.
- He reads on a phone: compact grids (before | after side by side, x3), never long thin strips. Build them with
  `tools/dev/contact_sheet.py`. Pictures go right under the question they belong to.
- Bare labels on his pages: "HUD", not "HUD (score, lives)". Explanations go in chat or behind a toggle.
- For every feature, say whether it fits the DMG or is Color only.
