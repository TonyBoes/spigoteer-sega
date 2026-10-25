---
name: gb-toolchain
description: Reference for this container's Game Boy toolchain and asset pipeline - RGBDS, GBDK-2020, gbtest/gbtools probes, gbcheck, gbsprite ASCII art format, lvl2gb levels, CGB palette packing, hardware limits (OAM, VRAM, palettes), the offline Pan Docs and manuals under $GAMEBOY_DOC, and which reference/ repos to study or reuse. Use it whenever a task touches assets, sprites, tiles, palettes, levels, a tool's flags, hardware limits, or anything under reference/, even if the brief does not name the tool.
---

# Game Boy toolchain reference (moved out of CLAUDE.md, 2026-10-25)

The non-negotiable rules stay in CLAUDE.md; this is the reference half. `reference/` still requires reading `$GAMEBOY_DOC/reference/MANIFEST.md` first.

## What is installed

| Tool | Use |
|---|---|
| `rgbasm` `rgblink` `rgbfix` `rgbgfx` (RGBDS 1.0.3) | assembly toolchain; `rgbgfx -r` reverses tiles to PNG |
| `lcc` `png2asset` `romusage` `gbcompress` `bankpack` (GBDK-2020 4.5.0, `$GBDK_HOME`) | C toolchain on SDCC; `romusage build/game.noi` for bank budgets |
| `gbtest` | run a ROM headlessly from the shell: press buttons, print variables, screenshot (`gbtest --help`) |
| `python3 -c "from gbtools import Rom"` | the same, from pytest (`tests/` in the skeleton shows the pattern) |
| `gbcheck` | SameBoy accuracy gate: DMG and CGB, crash/hang detection, final-frame PNG |
| `gbsprite` | ASCII pixel art -> indexed PNG; PNG -> ASCII; hardware-limit check; x8 previews |
| `lvl2gb` | ASCII or Tiled JSON level -> C or asm data; PNG preview with entities |
| `mgbdis` | disassembler for ROMs you are allowed to study |
| `sameboy_tester` | the raw tester `gbcheck` wraps |
| `convert` (ImageMagick), Pillow, numpy, pytest | image wrangling and tests |

Hardware reference, all offline, under `$GAMEBOY_DOC`:

- `pandocs/` — **Pan Docs**, the hardware reference. Start with `Specifications.md`, `Tile_Data.md`, `OAM.md`, `Rendering_Internals.md`, `Interrupts.md`, `Joypad_Input.md`, `Memory_Map.md`, `MBCs.md`.
- `gb-asm-tutorial/` — RGBDS tutorial, worked examples.
- `gb-opcodes/` — SM83 instruction table as JSON.
- `rgbds-man/` — RGBDS man pages as text (`rgbasm.5` is the language, `gbz80.7` the instruction set).
- `gbdk-manual.txt` — GBDK manual; GBDK headers are in `/opt/gbdk/include/gb/`, examples in `/opt/gbdk/examples/gb/`.
- `/usr/local/include/gameboy/hardware.inc` — register and flag names (v6; see gotchas).
- `reference/` — source of real games and libraries, indexed in `reference/MANIFEST.md`.

## Starting a project

An empty workspace gets one of the skeletons. Both are the same small
platformer (gravity, variable jump, coyote time, one-way platforms, hazards,
entities) with assets authored as ASCII and 14 tests that pass on DMG and CGB:

    cp -r /opt/gameboy/skeleton/gbdk/.  /workspace/     # C on GBDK
    cp -r /opt/gameboy/skeleton/rgbds/. /workspace/     # assembly on RGBDS
    make && make test && make check

Choose C for most games; it is far faster to write and the compiler is good.
Choose assembly when the project is about squeezing the hardware (raster
effects, large scrolling worlds, music drivers) or the owner asked for it.

## The loop

    make                       # assets -> data, compile, link, bank usage
    make test                  # pytest on both models; goldens in tests/golden/
    make check                 # SameBoy: DMG + CGB, 10 emulated seconds, screenshots in out/check/
    make preview               # every asset as an x8 PNG in out/preview/ — LOOK at these

Quick probes without writing a test:

    gbtest run build/game.gb --frames 120 --print player_x,player_y --out out/boot.png
    gbtest run build/game.gb --frames 120 --press right:30 --press a:12 --print player_y --out out/jump.png
    gbtest watch build/game.gb --frames 300 --print player_y,player_vy --every 10
    gbtest oam build/game.gb --frames 120          # sprite table + LCD registers
    gbtest symbols build/game.gb --filter player

`gbtest run --out` writes an x4 PNG. Read it with the image viewer; a screen
that is one flat colour almost always means the LCD was never turned on, the
tilemap was never written, or a palette is all-white.

Tests read variables **by name** from `build/game.noi` (GBDK) or
`build/game.sym` (RGBDS). Keep state in plain globals / exported WRAM labels
so this keeps working. If PyBoy and SameBoy disagree, SameBoy is right:
PyBoy is for driving and asserting, not for timing.

Boot takes about 70 frames; the skeleton tests run 120 before asserting.

## Assets

### Sprites and tiles (`gbsprite`)

Author in `assets/**/*.txt`, one character per pixel:
`.` 0 lightest / transparent for sprites, `-` 1, `+` 2, `#` 3 darkest;
blank line between frames; frames go left to right in the PNG. The Makefile
converts, validates (`gbsprite check --sprite` for sprites) and previews.

Hardware you must design within:
- DMG: 4 shades. Sprites get 3 + transparent (colour 0 never draws).
- CGB: 8 BG palettes and 8 OBJ palettes of 4 colours, 15-bit RGB. One
  palette per 8x8 tile.
- Sprites are 8x8 or 8x16 (mode set for the whole game). Anything bigger is
  a metasprite you assemble from several OAM entries. **An 8x16 sprite is
  ONE OAM entry** that draws tiles n and n+1.
- 40 OAM entries, **10 per scanline** — more than 10 on a line and the rest
  vanish. Flicker tricks exist; design around it first.
- VRAM holds 256 tiles for BG (384 counting the shared block) and 256 for
  OBJ on DMG; CGB doubles it with bank 1.

When the owner hands over reference art: a pixel-exact indexed PNG at 8x8
multiples goes straight through `gbsprite check` and the converters. A
sketch, photo or high-res illustration does **not** get quantised
automatically — redraw it at pixel scale as ASCII with the reference open,
preview at x8, iterate, and leave the preview in `out/preview/` for the
owner to judge. `gbsprite png2txt` reads any PNG back as ASCII. Colour art
for CGB is packed into palettes by the converters themselves:
`rgbgfx -n 8 -p out.pal -a out.attrmap -t out.tilemap in.png` (one palette
id per tile in the attrmap) or `png2asset in.png -map -use_map_attributes`.
Both refuse art that needs more than 8 palettes; `gbsprite check` says why.

### Levels (`lvl2gb`)

`assets/levels/<name>.txt`, one character per 8x8 tile:
`.` empty, `#` solid, `=` one-way platform, `^` hazard, `H` ladder;
entities `S` spawn, `E` enemy, `C` collectible, `X` exit. Extend the legend
with `<name>.legend.json`. Output: `<name>_tiles[]`, `<name>_collision[]`
(0 none, 1 solid, 2 platform, 3 hazard, 4 ladder), `<name>_entities[]`
(type, tile x, tile y) and `WIDTH`/`HEIGHT` constants; asm gets the same as
`LevelName…` labels. The Makefile also writes `out/preview/<name>.png`.

Tiled JSON (what the owner may hand over): orthogonal, 8x8 tiles, tile
layers `tiles` and `collision` (collision tileset in the order solid,
platform, hazard, ladder), object layer `entities` with a class per object,
CSV encoding. `lvl2gb txt level.json` prints it as ASCII so you can read it.

Maps wider or taller than 32 tiles exceed the hardware tilemap; the engine
has to stream columns or rows in during VBlank (`wario-land` and
`kirbys-dream-land` in `reference/` show the technique). `lvl2gb` says so in
the header and refuses maps that cannot fit a bank uncompressed. The
skeleton's `ColAt` multiplies by 20; change it with the level width.

## Where to look in `reference/` (study only unless marked reuse)

| Need | Look at |
|---|---|
| responsive platformer physics, sub-pixel velocity, scrolling | `wario-land` (bit-perfect, labelled), `super-mario-land`, `super-mario-land-2`, `kirbys-dream-land` |
| C-side action game, metasprites, GBDK idioms | `tobutobugirl-dx` (reuse, MIT), `super-princess-2092` + `zgb` (reuse) |
| banking, text engines, map compression, save RAM | `pokered`, `pokecrystal` |
| top-down action, entity systems | `links-awakening`, `oracles` |
| physics at 60 fps, CGB double speed | `pokemon-pinball` |
| music | `hugedriver` (reuse, MIT; both toolchains), `gbt-player` (reuse) |
| sound effects | `fxhammer`, `vgm2gbsfx` (reuse) |
| text with proportional fonts | `gb-vwf` (reuse) |
| project layout for RGBDS | `gb-boilerplate`, `gb-starter-kit` (reuse) |
| a whole game in one sitting | `tetris` |

`metroid-2` is raw disassembler output with few labels; low value.

## Gotchas

- **hardware.inc v6 renamed everything**: `LCDC_ON`, `LCDC_BLOCK21`,
  `LCDC_OBJ_16`, `JOYP_GET_BUTTONS`, `IE_VBLANK`, `OAM_XFLIP`,
  `BGPI_AUTOINC`. The pret disassemblies use the old names (`LCDCF_ON`,
  `P1F_GET_BTN`, `IEF_VBLANK`); do not paste their constants.
- GBDK symbols carry a leading underscore in `.noi` (`_player_x`); `gbtools`
  accepts both spellings.
- `lvl2gb --format asm` defaults to `SECTION … ROMX`; a 32 KB no-MBC cart
  needs `--section ROM0` (the skeleton does this).
- Palette RAM and VRAM are only safely written with the LCD off or during
  VBlank/HBlank. Writing them mid-frame corrupts the picture silently.
- `rgbfix -c` + `-t` limits the title to 11 characters; without `-c`, 15.
- `make test` runs every test on both DMG and CGB. A test that only makes
  sense on one model can check `gb.model_name`.
- The firewall blocks everything but GitHub, npm and the Anthropic API.
  There is nothing to fetch; everything is local. If you think you need
  the network, you need `$GAMEBOY_DOC` instead.
