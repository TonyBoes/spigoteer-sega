# Artifact pages: sources and how to restore them

The project's review pages are published as private claude.ai Artifacts under the owner's account. Their sources live
here, so any page can be rebuilt and republished if a working session is lost. To update a live page and keep its link,
publish with that page's URL as `url`.

| Page | URL | Source | How it is made |
|---|---|---|---|
| Pocket Player (browser emulator) | https://claude.ai/artifact/HepE9Kkxm3sLz8HYeuEQo2 | `tools/artifacts/pocket_player/` | Pack the ROMs with `make_roms.py` (see its header) into an output folder next to a copy of `index.html` and `wasmboy-ts-core.patched.js`, then publish `index.html` with `wasmboy-ts-core.patched.js` and `roms/*.js` as files. The ROM menu is the `ROM_LIST` array in `index.html`. |
| Open Questions | https://claude.ai/artifact/Fdq4kaVWUSrAJH8XZJrm8d | `tools/artifacts/open_questions/` | A hand-kept page: one card per open question, with its media in `media/`. Publish `index.html` with the media files. |
| Graphics Atlas (formerly OBJ Palette Plan) | https://claude.ai/artifact/Ekc9oYWEQb4APdLTaqXG4H | `tools/artifacts/palette_plan/` | `make atlas-page` (re-runs `make atlas` only if `src/` or `assets/` changed since the capture, then build.py, the self-check and the 360 px check) rebuilds `index.html` and writes `out/atlas_page/pub.json`: the files to publish (`index.html` plus the `img/*.png` whose `?v=` hash differs from the last publish, `published.json`; run `atlas_page.py --mark-published` after publishing) and the ones removed; publish those, nothing else, and check the 512-file limit it prints. The plan is hand-kept in `tools/artifacts/palette_plan/plan_data.py` (PLANS with their Qn, PATRON_ART, the Saloon's primary palettes, ART_RULE_EXCEPTIONS); the log and ideas in `LOG` / `IDEAS` in build.py; the venue colours come from the atlas data. `build.py` also writes the patron sprites to `img/`. Publish `index.html` with `img/*.png` as files. |
| Palette Merges | https://claude.ai/artifact/5N6u6w7ir7y3dosAMdPH43 | `tools/artifacts/palette_merges/` | `python3 tools/artifacts/palette_merges/build.py` (after `make atlas`) writes `index.html` and `img/`. The proposed merges are hand-kept in `MERGES` in build.py. Publish `index.html` with `img/*.png` as files. |

## Page rules (every page, every update; owner reads on a phone)

Check these before each publish:
1. **No sideways scroll at 360 px wide.** Nothing wider than the screen: images get `max-width: 100%; height: auto`
   (pixel art keeps `image-rendering: pixelated`); a fixed-size crop or picture is at most 320 px. Tables with more than
   3 columns turn into stacked cards under 640 px (each cell labelled with its column name), never an inner scroll box.
   Long ids and hex wrap (`overflow-wrap: anywhere`). Tooltips are clamped to the screen. 16 px side gutter.
2. **Colour has a meaning, and it is the same everywhere.** green = in the game now, amber/yellow = planned, orange
   dashed = free slot, red = over a limit (Atlas stats tiles, owner 2026-10-29), accent blue = links and selected tabs. Nothing else gets a colour. Bullet markers stay neutral
   (muted); only the text of a now/planned item is coloured.
3. **Contrast:** text at least 4.5:1 against its card and the page ground, in light AND dark mode (check the token
   pairs with a contrast script when a colour changes).
4. **Bare labels** ("HUD", not "HUD (score, lives)"); explanations in chat or behind a toggle; summary first, detail
   collapsed.
5. **Tap targets** at least 32 px; nothing that only works on hover (hover info also opens on tap).
6. Every colour is a `:root` token, redefined for dark mode (both the media query and `[data-theme="dark"]`).
7. **Free tiles only**, no tiles-used stats; no new visible clutter. The page shows the plan; anything that is the game's state carries
   a NOW label, and where the plan moves a slot both numbers show ("plan OBJ 5 / game OBJ 6").
8. A picture is the game's real tiles in its real palette, or the plan's art with a "planned" tag: never a redrawn game look.
9. Before a publish: `make atlas-page` reports 0 self-check errors, look at a `tools/dev/contact_sheet.py` sheet of the changed
   thumbnails, read the live page's title (never overwrite a title you have not read), and after a delete or rename confirm it with `list`.

## Deleted pages: the Old Atlas and the Review Board

Both pages were deleted from the owner's account on 2026-10-29. Their links no longer work; do not republish them.
- Old Atlas (was https://claude.ai/artifact/RLQysU9fNNbcZR2TS8x5XZ): retired 2026-10-26, when the Palette Plan page took
  the name Graphics Atlas.
- Review Board (was https://claude.ai/artifact/SHg2h5cuTDMN5qrKfiFRho): its old source stays in `tools/artifacts/review_board/`.
  Large items for an open question (animations, big sheets) now go on that question's Open Questions card.
 `make atlas` (`tools/gfx_atlas/`) still runs, because the Graphics Atlas and Palette
Merges builds read its `out/atlas/data`.

## Pocket Player notes

- The emulator is WasmBoy 0.7.1's TypeScript core (GPL-3.0, https://github.com/torch2424/wasmboy), with two small fixes.
  The file header lists both:
  - CPL masks A to 8 bits; without it every joypad read is empty.
  - The Color registers VBK, BCPD and OCPD read back; without them there is no Color detection and the colours are wrong.
- iPhone sound: Safari only unlocks Web Audio when a sound is played inside a finished tap (touchend / click / pointerup).
  The page's `wakeAudio()` retries that on every such event until the audio context runs. Keep this behaviour when
  editing the page.
- ROM .js files are generated and not committed. Rebuild them from the game's own ROMs.
- Download ROM (menu, owner 2026-11-05): uses the `downloads` capability, declared on the artifact (`capabilities: {downloads: true}`; a
  redeploy that omits `capabilities` keeps it). `.gb` is not an allowed download type, so the page saves `<rom>.zip` (stored, the .gb inside).

## Keeping these copies current

When a page changes, update its source here in the same change: the page HTML, plus the media for the two hand-kept
pages. The ROM packs and the atlas output are generated and are not committed.

## Story Scenes
https://claude.ai/artifact/2zVytB94Mn2Z3NeiyP1XKi. Source: tools/artifacts/story_scenes/index.html. Rebuild: capture with out/story_scenes/cap.py (gb-runner), copy pages to out/story_page/img/, regenerate index.html, publish with root out/story_page and every img/*.png.
