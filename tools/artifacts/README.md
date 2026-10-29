# Artifact pages: sources and how to restore them

The project's review pages are published as private claude.ai Artifacts under the owner's account. Their sources live
here, so any page can be rebuilt and republished if a working session is lost. To update a live page and keep its link,
publish with that page's URL as `url`.

| Page | URL | Source | How it is made |
|---|---|---|---|
| Pocket Player (browser emulator) | https://claude.ai/artifact/HepE9Kkxm3sLz8HYeuEQo2 | `tools/artifacts/pocket_player/` | Pack the ROMs with `make_roms.py` (see its header) into an output folder next to a copy of `index.html` and `wasmboy-ts-core.patched.js`, then publish `index.html` with `wasmboy-ts-core.patched.js` and `roms/*.js` as files. The ROM menu is the `ROM_LIST` array in `index.html`. |
| Open Questions | https://claude.ai/artifact/Fdq4kaVWUSrAJH8XZJrm8d | `tools/artifacts/open_questions/` | A hand-kept page: one card per open question, with its media in `media/`. Publish `index.html` with the media files. |
| Graphics Atlas (formerly OBJ Palette Plan) | https://claude.ai/artifact/Ekc9oYWEQb4APdLTaqXG4H | `tools/artifacts/palette_plan/` | `python3 tools/artifacts/palette_plan/build.py` (after `make atlas`) rebuilds `index.html`. The plan, ideas and log are hand-kept in `PLAN` / `IDEAS` / `LOG` in build.py; the venue colours come from the atlas data. `build.py` also writes the patron sprites to `img/`. Publish `index.html` with `img/*.png` as files. |
| Palette Merges | https://claude.ai/artifact/5N6u6w7ir7y3dosAMdPH43 | `tools/artifacts/palette_merges/` | `python3 tools/artifacts/palette_merges/build.py` (after `make atlas`) writes `index.html` and `img/`. The proposed merges are hand-kept in `MERGES` in build.py. Publish `index.html` with `img/*.png` as files. |

## Page rules (every page, every update; owner reads on a phone)

Check these before each publish:
1. **No sideways scroll at 360 px wide.** Nothing wider than the screen: images get `max-width: 100%; height: auto`
   (pixel art keeps `image-rendering: pixelated`); a fixed-size crop or picture is at most 320 px. Tables with more than
   3 columns turn into stacked cards under 640 px (each cell labelled with its column name), never an inner scroll box.
   Long ids and hex wrap (`overflow-wrap: anywhere`). Tooltips are clamped to the screen. 16 px side gutter.
2. **Colour has a meaning, and it is the same everywhere.** green = in the game now, amber/yellow = planned, orange
   dashed = free slot, accent blue = links and selected tabs. Nothing else gets a colour. Bullet markers stay neutral
   (muted); only the text of a now/planned item is coloured.
3. **Contrast:** text at least 4.5:1 against its card and the page ground, in light AND dark mode (check the token
   pairs with a contrast script when a colour changes).
4. **Bare labels** ("HUD", not "HUD (score, lives)"); explanations in chat or behind a toggle; summary first, detail
   collapsed.
5. **Tap targets** at least 32 px; nothing that only works on hover (hover info also opens on tap).
6. Every colour is a `:root` token, redefined for dark mode (both the media query and `[data-theme="dark"]`).

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

## Keeping these copies current

When a page changes, update its source here in the same change: the page HTML, plus the media for the two hand-kept
pages. The ROM packs and the atlas output are generated and are not committed.
