# GBDK-2020 project. `make` builds build/game.gb; `make test` runs the PyBoy
# tests; `make check` runs the SameBoy accuracy gate; `make preview` renders
# every asset as an upscaled PNG under out/preview/ for a human to look at.
#
# Generated C for assets lands in build/ and is never committed. Edit the
# sources in assets/, not the generated files.

NAME     := game
BUILD    := build
OUT      := out
LCC      := lcc
# -Wa-l listing, -Wl-m map, -Wl-j NoICE symbols (build/game.noi -> tests read
# variables by name), -Wm-yc CGB-compatible (runs on DMG and CGB),
# -Wm-yn cartridge title (max 15 chars), -Wm-yt MBC type if you need banks.
LCCFLAGS := -Wa-l -Wl-m -Wl-j -Wm-yc -Wm-ynTAPPER
# MBC5 + GBDK autobanking (M4.7): the pre-shifted patron tiles (~10 KB) live in build/patrons.c
# under `#pragma bank 255`; bankpack places it in a switchable bank. -Wm-yoA sizes the ROM.
LCCFLAGS += -Wm-yt0x19 -Wm-yoA -autobank

SRC      := $(wildcard src/*.c)
GEN      := $(BUILD)/art.c $(BUILD)/patrons.c $(BUILD)/palettes.c
ROM      := $(BUILD)/$(NAME).gb

.PHONY: all test check preview clean assets

all: $(ROM)

assets: $(GEN)

$(BUILD) $(OUT)/preview:
	mkdir -p $@

# Tile and sprite data: bar.txt (BG tiles), bartender.txt and mug.txt (8x16 OBJ
# tiles, padded so each bartender frame is 4 OAM entries) -> build/art.c/.h.
# Also writes x8 previews to out/preview/.
$(BUILD)/art.c $(BUILD)/art.h: tools/gen_art.py assets/tiles/bar.txt assets/art/bartender.txt assets/art/mug.txt assets/art/mug_fill.txt assets/art/mug_drink.txt assets/art/glass.txt $(wildcard assets/art/patrons/*.txt) | $(BUILD) $(OUT)/preview
	python3 tools/gen_art.py $(BUILD) $(OUT)/preview

$(BUILD)/patrons.c: $(BUILD)/art.c
	@test -f $@

# CGB palettes: assets/palettes.json -> build/palettes.c/.h
$(BUILD)/palettes.c $(BUILD)/palettes.h: tools/palettes2c.py assets/palettes.json | $(BUILD)
	python3 tools/palettes2c.py assets/palettes.json $(BUILD)

$(ROM): $(SRC) $(GEN) $(BUILD)/art.h $(BUILD)/palettes.h
	$(LCC) $(LCCFLAGS) -I$(BUILD) -o $@ $(SRC) $(GEN)
	@romusage $(BUILD)/$(NAME).noi 2>/dev/null | head -12 || true

test: $(ROM)
	python3 -m pytest -q tests

check: $(ROM)
	gbcheck $(ROM) --length 10 --out $(OUT)/check

preview: $(GEN)
	@ls -1 $(OUT)/preview/

clean:
	rm -rf $(BUILD) $(OUT)
