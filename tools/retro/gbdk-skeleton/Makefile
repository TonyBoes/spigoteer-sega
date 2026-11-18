# GBDK-2020 project built for several consoles from one source.
#   make                 all targets: build/gb/game.gb build/sms/game.sms build/gg/game.gg
#   make TARGETS=gg      just one
#   make test            stable-retro tests, every target
#   make check           MesenCE accuracy gate, every target
#   make preview         upscaled asset previews in out/preview/
#
# Assets are converted ONCE to 2bpp Game Boy format (build/assets/) and compiled
# into every target; on SMS/GG, set_2bpp_palette() colours them at load time.
# Generated files are never committed. Edit assets/, not build/.

NAME    := game
TARGETS ?= gb sms gg
BUILD   := build
OUT     := out
LCC     := lcc
# -Wl-j: .noi symbols for tests. -Wm-yc: GB build runs on DMG and CGB.
FLAGS_gb  := -msm83:gb -Wm-yc
FLAGS_sms := -mz80:sms
FLAGS_gg  := -mz80:gg
EXT_gb  := gb
EXT_sms := sms
EXT_gg  := gg

A    := $(BUILD)/assets
GEN  := $(A)/tiles.c $(A)/player.c $(A)/level1.c
ROMS := $(foreach t,$(TARGETS),$(BUILD)/$(t)/$(NAME).$(EXT_$(t)))

.PHONY: all test check preview clean

all: $(ROMS)

$(A) $(OUT)/preview:
	mkdir -p $@

$(A)/tiles.c: assets/tiles/tiles.txt | $(A) $(OUT)/preview
	retrosprite txt2png $< $(A)/tiles.png --preview $(OUT)/preview/tiles_x8.png
	retrosprite check $(A)/tiles.png --system gb
	png2asset $(A)/tiles.png -o $@ -map -tiles_only -noflip -keep_duplicate_tiles -keep_palette_order

$(A)/player.c: assets/sprites/player.txt | $(A) $(OUT)/preview
	retrosprite txt2png $< $(A)/player.png --preview $(OUT)/preview/player_x8.png
	retrosprite check $(A)/player.png --system gb --sprite
	png2asset $(A)/player.png -o $@ -map -tiles_only -noflip -keep_duplicate_tiles -keep_palette_order

$(A)/level1.c: assets/levels/level1.txt $(A)/tiles.c | $(OUT)/preview
	retrolevel build $< --system gb --format c --out $(A)/level1
	retrolevel preview $< --tileset $(A)/tiles.png --out $(OUT)/preview/level1.png

define ROM_RULE
$(BUILD)/$(1)/$(NAME).$(EXT_$(1)): src/main.c $(GEN)
	mkdir -p $(BUILD)/$(1)
	$(LCC) $(FLAGS_$(1)) -Wl-j -Wm-yn"$(NAME)" -I$(A) -o $$@ src/main.c $(GEN)
endef
$(foreach t,$(TARGETS),$(eval $(call ROM_RULE,$(t))))

test: $(ROMS)
	TARGETS="$(TARGETS)" python3 -m pytest -q tests

check: $(ROMS)
	@fail=0; for r in $(ROMS); do retrocheck $$r --frames 600 --print player_x,player_y,on_ground --expect dead=0 --out $(OUT)/check || fail=1; done; exit $$fail

preview: $(GEN)
	@ls -1 $(OUT)/preview/

clean:
	rm -rf $(BUILD) $(OUT)
