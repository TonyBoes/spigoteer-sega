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
LCCFLAGS := -Wa-l -Wl-m -Wl-j -Wm-yc -Wm-yn"$(NAME)"

SRC      := $(wildcard src/*.c)
GEN      := $(BUILD)/tiles.c $(BUILD)/player.c $(BUILD)/level1.c
ROM      := $(BUILD)/$(NAME).gb

.PHONY: all test check preview clean assets

all: $(ROM)

assets: $(GEN)

$(BUILD) $(OUT)/preview:
	mkdir -p $@

# Background tileset: ASCII -> indexed PNG -> tile data, in id order (map mode
# keeps empty and duplicate tiles so ids match lvl2gb's legend).
$(BUILD)/tiles.c: assets/tiles/tiles.txt | $(BUILD) $(OUT)/preview
	gbsprite txt2png $< $(BUILD)/tiles.png --preview $(OUT)/preview/tiles_x8.png
	gbsprite check $(BUILD)/tiles.png
	png2asset $(BUILD)/tiles.png -o $@ -map -tiles_only -noflip -keep_duplicate_tiles -keep_palette_order

# Player: 8x16 frames side by side; index 0 is transparent.
$(BUILD)/player.c: assets/sprites/player.txt | $(BUILD) $(OUT)/preview
	gbsprite txt2png $< $(BUILD)/player.png --preview $(OUT)/preview/player_x8.png
	gbsprite check $(BUILD)/player.png --sprite
	png2asset $(BUILD)/player.png -o $@ -tiles_only -noflip -keep_duplicate_tiles -keep_palette_order -spr8x16 -sw 8 -sh 16 -sprite_no_optimize

# Level: ASCII (or Tiled JSON) -> tilemap + collision + entities, plus a preview.
$(BUILD)/level1.c: assets/levels/level1.txt $(BUILD)/tiles.c | $(BUILD) $(OUT)/preview
	lvl2gb build $< --format c --out $(BUILD)/level1
	lvl2gb preview $< --tileset $(BUILD)/tiles.png --out $(OUT)/preview/level1.png

$(ROM): $(SRC) $(GEN)
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
