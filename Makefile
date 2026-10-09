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
LCCFLAGS := -Wa-l -Wl-m -Wl-j -Wm-yc -Wm-ynSPIGOTEER
# MBC5+RAM+BATTERY (0x1B, one 8 KB SRAM bank for the hi score, M7) + GBDK autobanking (M4.7): the pre-shifted patron tiles (M8b: 9 x 2.5 KB) live in build/patrons_<group>.c, one file per group
# under `#pragma bank 255` (all nine would not fit one bank); bankpack places each in a switchable bank. -Wm-yoA sizes the ROM.
LCCFLAGS += -Wm-yt0x1B -Wm-ya1 -Wm-yoA -autobank

SRC      := $(wildcard src/*.c)
PATRON_GROUPS := cowboys sports lumberjacks chefs divers robots ninjas aliens zoo
PATRON_C := $(foreach g,$(PATRON_GROUPS),$(BUILD)/patrons_$(g).c) $(BUILD)/patron_load.c
GEN      := $(BUILD)/art.c $(PATRON_C) $(BUILD)/palettes.c $(BUILD)/music_data.c $(BUILD)/music_pat3.c
# hUGEDriver (public domain, third_party/hugedriver): assembled with RGBDS, converted to a GBDK object by
# rgb2sdas.py, placed in ROM bank 2 next to the order tables and src/music.c (all `#pragma bank 2`); the song patterns are
# in bank 3 (build/music_pat3.c) and src/music.c copies them to WRAM, see tools/gen_music.py.
HUGE     := third_party/hugedriver
HUGE_OBJ := $(BUILD)/hUGEDriver.o
BONUS_H  := $(BUILD)/can_tiles.h
ROM      := $(BUILD)/$(NAME).gb

.PHONY: all test check preview clean assets

all: $(ROM)

assets: $(GEN)

$(BUILD) $(OUT)/preview:
	mkdir -p $@

# Tile and sprite data: bar.txt (BG tiles), bartender.txt and mug.txt (8x16 OBJ
# tiles, padded so each bartender frame is 4 OAM entries) -> build/art.c/.h.
# Also writes x8 previews to out/preview/.
$(BUILD)/art.c $(BUILD)/art.h: tools/gen_art.py assets/tiles/bar.txt assets/tiles/title.txt assets/art/bartender.txt assets/art/mug.txt assets/art/mug_fill.txt assets/art/mug_drink.txt assets/art/glass.txt assets/art/coin.txt assets/art/dancer.txt assets/art/can.txt assets/art/foam.txt assets/art/cursor.txt $(wildcard assets/art/patrons/*.txt) | $(BUILD) $(OUT)/preview
	python3 tools/gen_art.py $(BUILD) $(OUT)/preview

$(PATRON_C) $(BUILD)/can_tiles.h: $(BUILD)/art.c
	@test -f $@

# CGB palettes: assets/palettes.json -> build/palettes.c/.h
$(BUILD)/palettes.c $(BUILD)/palettes.h: tools/palettes2c.py assets/palettes.json | $(BUILD)
	python3 tools/palettes2c.py assets/palettes.json $(BUILD)

# Music: tune sources in tools/gen_music.py + tools/songs.py -> build/music_data.c (bank 2: order tables, jingles) and
# build/music_pat3.c (bank 3: the pattern blobs src/music.c copies into WRAM)
$(BUILD)/music_data.c: tools/gen_music.py tools/songs.py src/music.h | $(BUILD)
	python3 tools/gen_music.py $(BUILD)

$(BUILD)/music_pat3.c: $(BUILD)/music_data.c
	@true

$(BUILD)/hUGEDriver.obj: $(HUGE)/hUGEDriver.asm $(wildcard $(HUGE)/include/*) | $(BUILD)
	rgbasm -i $(HUGE)/ -DGBDK -o $@ $<

$(HUGE_OBJ): $(BUILD)/hUGEDriver.obj $(HUGE)/tools/rgb2sdas.py
	python3 $(HUGE)/tools/rgb2sdas.py -c _CODE_2 -o $@ $<

$(ROM): $(SRC) $(GEN) $(BONUS_H) $(BUILD)/art.h $(BUILD)/palettes.h $(HUGE_OBJ) $(HUGE)/include/hUGEDriver.h
	$(LCC) $(LCCFLAGS) -I$(BUILD) -Isrc -I$(HUGE)/include -o $@ $(SRC) $(GEN) $(HUGE_OBJ)
	@romusage $(BUILD)/$(NAME).noi 2>/dev/null | head -12 || true

test: $(ROM)
	python3 -m pytest -q tests

check: $(ROM)
	gbcheck $(ROM) --length 10 --out $(OUT)/check

preview: $(GEN)
	@ls -1 $(OUT)/preview/

clean:
	rm -rf $(BUILD) $(OUT)
