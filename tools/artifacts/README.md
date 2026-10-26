# Artifact pages: sources and how to restore them

The project's review pages are published as private claude.ai Artifacts under the owner's account. Their sources live
here, so any page can be rebuilt and republished if a working session is lost. To update a live page and keep its link,
publish with that page's URL as `url`.

| Page | URL | Source | How it is made |
|---|---|---|---|
| Graphics Atlas | https://claude.ai/artifact/RLQysU9fNNbcZR2TS8x5XZ | `tools/gfx_atlas/` | `make atlas` writes `out/atlas/` (about 2 min). Publish `out/atlas/index.html` with every other file under `out/atlas/` as files. That is about 390 files, so publish in two batches of at most 255; each later publish adds to the files already there. |
| Pocket Player (browser emulator) | https://claude.ai/artifact/HepE9Kkxm3sLz8HYeuEQo2 | `tools/artifacts/pocket_player/` | Pack the ROMs with `make_roms.py` (see its header) into an output folder next to a copy of `index.html` and `wasmboy-ts-core.patched.js`, then publish `index.html` with `wasmboy-ts-core.patched.js` and `roms/*.js` as files. The ROM menu is the `ROM_LIST` array in `index.html`. |
| Open Questions | https://claude.ai/artifact/Fdq4kaVWUSrAJH8XZJrm8d | `tools/artifacts/open_questions/` | A hand-kept page: one card per open question, with its media in `media/`. Publish `index.html` with the media files. |
| OBJ Palette Plan | https://claude.ai/artifact/Ekc9oYWEQb4APdLTaqXG4H | `tools/artifacts/palette_plan/` | `python3 tools/artifacts/palette_plan/build.py` (after `make atlas`) rebuilds `index.html`. The plan, ideas and log are hand-kept in `PLAN` / `IDEAS` / `LOG` in build.py; the venue colours come from the atlas data. `build.py` also writes the patron sprites to `img/`. Publish `index.html` with `img/*.png` as files. |
| Review Board (an open question's items too big for Open Questions; empty when none) | https://claude.ai/artifact/SHg2h5cuTDMN5qrKfiFRho | `tools/artifacts/review_board/` | Hand-kept, like Open Questions. |

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
