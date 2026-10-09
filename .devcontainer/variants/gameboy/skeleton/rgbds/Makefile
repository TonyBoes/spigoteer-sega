# RGBDS project. `make` builds build/game.gb; `make test` runs the PyBoy
# tests; `make check` runs the SameBoy accuracy gate; `make preview` renders
# every asset as an upscaled PNG under out/preview/ for a human to look at.
#
# Generated data (2bpp tiles, level .asm) lands in build/ and is never
# committed. Edit the sources in assets/, not the generated files.

NAME   := game
BUILD  := build
OUT    := out
# cartridge title, max 11 chars with -c (15 without)
TITLE  := GAME

# -n: symbol file for the tests. -c: CGB-compatible (also runs on DMG).
# -p 0xFF: pad to a full 32 KB. -v: fix header checksums. Add -m 1 for MBC1.
ASMFLAGS  := -I src -I $(BUILD) -Wall
LINKFLAGS := -n $(BUILD)/$(NAME).sym -m $(BUILD)/$(NAME).map
FIXFLAGS  := -v -p 0xFF -c -t "$(TITLE)"

SRC  := $(wildcard src/*.asm)
OBJ  := $(patsubst src/%.asm,$(BUILD)/%.o,$(SRC))
GEN  := $(BUILD)/tiles.2bpp $(BUILD)/player.2bpp $(BUILD)/level1.asm
ROM  := $(BUILD)/$(NAME).gb

.PHONY: all test check preview clean assets

all: $(ROM)

assets: $(GEN)

$(BUILD) $(OUT)/preview:
	mkdir -p $@

# Background tileset: ASCII -> indexed PNG -> 2bpp, keeping the PNG's palette
# order (-c embedded) so index 0 in the .txt is colour 0 on the hardware.
$(BUILD)/tiles.2bpp: assets/tiles/tiles.txt | $(BUILD) $(OUT)/preview
	gbsprite txt2png $< $(BUILD)/tiles.png --preview $(OUT)/preview/tiles_x8.png
	gbsprite check $(BUILD)/tiles.png
	rgbgfx -c embedded -o $@ $(BUILD)/tiles.png

# Player: 8x16 frames side by side. -Z reads the image column-major, so each
# frame's top and bottom tiles are consecutive, as 8x16 OBJ mode expects.
$(BUILD)/player.2bpp: assets/sprites/player.txt | $(BUILD) $(OUT)/preview
	gbsprite txt2png $< $(BUILD)/player.png --preview $(OUT)/preview/player_x8.png
	gbsprite check $(BUILD)/player.png --sprite
	rgbgfx -c embedded -Z -o $@ $(BUILD)/player.png

# Level: ASCII (or Tiled JSON) -> tilemap + collision + entities in ROM0.
$(BUILD)/level1.asm: assets/levels/level1.txt $(BUILD)/tiles.2bpp | $(BUILD) $(OUT)/preview
	lvl2gb build $< --format asm --section ROM0 --out $(BUILD)/level1
	lvl2gb preview $< --tileset $(BUILD)/tiles.png --out $(OUT)/preview/level1.png

$(BUILD)/%.o: src/%.asm $(GEN) | $(BUILD)
	rgbasm $(ASMFLAGS) -o $@ $<

$(ROM): $(OBJ)
	rgblink $(LINKFLAGS) -o $@ $(OBJ)
	rgbfix $(FIXFLAGS) $@

test: $(ROM)
	python3 -m pytest -q tests

check: $(ROM)
	gbcheck $(ROM) --length 10 --out $(OUT)/check

preview: $(GEN)
	@ls -1 $(OUT)/preview/

clean:
	rm -rf $(BUILD) $(OUT)
