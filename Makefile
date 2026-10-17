# GBDK-2020 project. `make` builds build/game.gb; `make test` runs the PyBoy
# tests; `make check` runs the SameBoy accuracy gate; `make preview` renders
# every asset as an upscaled PNG under out/preview/ for a human to look at.
#
# Generated C for assets lands in build/ and is never committed. Edit the
# sources in assets/, not the generated files.

NAME     := game
# The release number, set here only: MAJOR.MINOR, each one digit (the title's top-right corner, the header's version byte, dist/ names).
VERSION  := 0.9
VER_MAJOR := $(word 1,$(subst ., ,$(VERSION)))
VER_MINOR := $(word 2,$(subst ., ,$(VERSION)))
BUILD    := build
OUT      := out
LCC      := lcc
# -Wa-l listing, -Wl-m map, -Wl-j NoICE symbols (build/game.noi -> tests read
# variables by name), -Wm-yc CGB-compatible (runs on DMG and CGB),
# -Wm-yn cartridge title (max 15 chars), -Wm-yt MBC type if you need banks.
LCCFLAGS := -Wa-l -Wl-m -Wl-j -Wm-yc -Wm-yj -Wm-ynSPIGOTEER -Wm-yp0x14C=$(shell echo $$(($(VER_MAJOR)*10+$(VER_MINOR)))) -DVERSION_MAJOR=$(VER_MAJOR) -DVERSION_MINOR=$(VER_MINOR)
# MBC5+RAM+BATTERY (0x1B, one 8 KB SRAM bank for the hi score, M7) + GBDK autobanking (M4.7): the pre-shifted patron tiles (M8b: 10 x 2.5 KB) live in build/patrons_<group>.c, one file per group
# under `#pragma bank 255` (all ten would not fit one bank); bankpack places each in a switchable bank. -Wm-yoA sizes the ROM.
LCCFLAGS += -Wm-yt0x1B -Wm-ya1 -Wm-yoA -autobank

# DEBUG_MENU: the playtest build (rush.c / mg_list.c list every boss and mini-game unlocked); `make release` leaves it out. The debug MENU itself
# (src/debug.c) is in both, locked until its unlock is saved (SETTINGS' Konami code, src/debug.c konami_step). An always-unlocked build for
# testing by hand: make DEBUGFLAGS="-DDEBUG_MENU -DDEBUG_UNLOCKED"
DEBUGFLAGS := -DDEBUG_MENU
LCCFLAGS += $(DEBUGFLAGS)

SRC      := $(wildcard src/*.c)
PATRON_GROUPS := cowboys sports lumberjacks chefs divers robots punks ninjas zoo aliens
PATRON_C := $(foreach g,$(PATRON_GROUPS),$(BUILD)/patrons_$(g).c) $(BUILD)/patron_load.c
# M9 themed venues (theme index = patron group): stage, bar, floor, drink, show and palettes per theme, one banked file each
VENUES   := saloon sports lodge bistro igloo factory biker teahouse zoo space
VENUE_C  := $(foreach t,$(VENUES),$(BUILD)/venue_$(t).c) $(BUILD)/venue_load.c
# M11b story mode: the script (docs/story.md), the portraits and the story font -> two banked files (tools/gen_story.py)
STORY_C  := $(BUILD)/story_data.c $(BUILD)/story_portraits.c $(BUILD)/story_pictures.c
GEN      := $(BUILD)/art.c $(PATRON_C) $(VENUE_C) $(BUILD)/palettes.c $(BUILD)/music_data.c $(BUILD)/music_pat10.c $(BUILD)/music_pat22.c $(STORY_C) $(BUILD)/credits_text.c
# hUGEDriver (public domain, third_party/hugedriver): assembled with RGBDS, converted to a GBDK object by
# rgb2sdas.py, placed in ROM bank 2 next to the order tables and src/music.c (all `#pragma bank 2`); the song patterns are
# in bank 10 (build/music_pat10.c) and src/music.c copies them to WRAM, see tools/gen_music.py.
HUGE     := third_party/hugedriver
HUGE_OBJ := $(BUILD)/hUGEDriver.o
# each boss's own art header (tools/gen_boss.py: build/boss_<name>_art.h, #included by src/boss_<name>.c only)
BOSS_H   := $(foreach b,$(filter-out meter,$(basename $(notdir $(wildcard assets/art/boss/*.txt)))),$(BUILD)/boss_$(b)_art.h)
BONUS_H  := $(BUILD)/can_tiles.h $(BUILD)/list_arrows.h $(BUILD)/list_keys.h $(BUILD)/list_skin.h $(BUILD)/title_art.h $(BUILD)/bonus2_art.h $(BUILD)/patron_enh.h $(BUILD)/story.h $(BUILD)/pour_art.h $(BUILD)/mg_art.h $(BUILD)/mg_card_art.h $(BUILD)/mg_stub_art.h $(BUILD)/qd_art.h $(BUILD)/ou_art.h $(BUILD)/boss_art.h $(BOSS_H) $(BUILD)/leo_fx_art.h $(BUILD)/jukebox_names.h $(BUILD)/antics_art.h $(BUILD)/trans_art.h $(BUILD)/credits_text.h
BONUS_H  += $(BUILD)/bs_art.h $(BUILD)/mr_art.h $(BUILD)/lr_art.h $(BUILD)/ad_art.h $(BUILD)/tk_art.h $(BUILD)/mm_art.h $(BUILD)/mk_art.h $(BUILD)/ts_art.h
ROM      := $(BUILD)/$(NAME).gb

.PHONY: all test check preview clean assets release dist unlocked

all: $(ROM)

assets: $(GEN)

$(BUILD) $(OUT)/preview:
	mkdir -p $@

# Tile and sprite data: bar.txt (shared BG tiles), bartender.txt (8x16 OBJ tiles, padded so each bartender frame is
# 4 OAM entries), the patrons, and the venues (assets/approved/venues: stage, bar, drink, show per theme)
# -> build/art.c/.h, build/patrons_*.c, build/venue_*.c, build/venues.json. Also writes x8 previews to out/preview/.
$(BUILD)/art.c $(BUILD)/art.h: tools/gen_art.py assets/tiles/bar.txt assets/tiles/title.txt assets/art/bartender.txt assets/art/glass_shards.txt assets/art/coin.txt assets/art/can.txt assets/art/geyser.txt assets/art/cat_walk.txt assets/art/droplets.txt assets/art/cursor.txt assets/art/title_fx.txt assets/art/pour.txt assets/art/tap.txt assets/art/pour_glass.txt assets/art/tips.txt assets/art/hud_icons.txt assets/art/list_arrows.txt assets/art/list_keys.txt assets/art/list_skin.txt $(wildcard assets/art/patrons/*.txt) $(wildcard assets/art/splash/*.txt) $(wildcard assets/approved/venues/*) | $(BUILD) $(OUT)/preview
	python3 tools/gen_art.py $(BUILD) $(OUT)/preview

$(PATRON_C) $(VENUE_C) $(BUILD)/can_tiles.h $(BUILD)/list_arrows.h $(BUILD)/list_keys.h $(BUILD)/list_skin.h $(BUILD)/title_art.h $(BUILD)/bonus2_art.h $(BUILD)/patron_enh.h: $(BUILD)/art.c
	@test -f $@

# Story mode (M11b): the script is validated here (line length, charset, speakers, the chapter goals, the cut-scene
# tile budget); the build fails on any error. Also writes build/story.json (tests) and out/preview/story_*.png.
$(STORY_C) $(BUILD)/story.h: tools/gen_story.py tools/gen_art.py docs/story.md assets/story/portraits.json assets/tiles/story.txt $(wildcard assets/story/portraits/*.txt) $(wildcard assets/story/pictures/*.txt) src/main_cold.c $(BUILD)/art.h | $(BUILD) $(OUT)/preview
	python3 tools/gen_story.py $(BUILD) $(OUT)/preview

# The credits' pre-rendered text (src/credits.c): every cast label and roll line cut into centred tiles -> build/credits_text.c (banked), .h, .json (tests)
$(BUILD)/credits_text.c $(BUILD)/credits_text.h: tools/gen_credits.py tools/gen_art.py assets/tiles/bar.txt assets/tiles/story.txt | $(BUILD)
	python3 tools/gen_credits.py $(BUILD)

# Perfect pour (story): per-venue sparkle / overflow frames and the catch cue -> build/pour_art.h (src/pour.c's bank),
# build/pour.json (tests), out/preview/pour_<t>_x8.png
$(BUILD)/pour_art.h: tools/gen_pour.py tools/gen_art.py $(wildcard assets/art/pour/*.txt) assets/art/pour_cue.txt assets/art/dust.txt $(wildcard assets/approved/venues/*_drink.txt) | $(BUILD) $(OUT)/preview
	python3 tools/gen_pour.py $(BUILD) $(OUT)/preview

# Mini-game framework (src/mg.c), its stub game (src/mg_stub.c) and Quick Draw (src/qd.c): the medal icon (approved), the
# lamp (a placeholder), Quick Draw's art (approved) -> build/qd_art.h too, Order Up!'s (approved) -> build/ou_art.h
# -> build/mg_art.h, build/mg_stub_art.h, build/mg.json (tests), out/preview/mg_*_x8.png
$(BUILD)/mg_art.h $(BUILD)/mg_card_art.h $(BUILD)/mg_stub_art.h $(BUILD)/qd_art.h $(BUILD)/ou_art.h: tools/gen_mg.py tools/gen_art.py assets/art/mg_medal.txt assets/art/mg_lamp.txt assets/art/mg_hourglass.txt assets/art/mg_card.txt $(wildcard assets/art/quickdraw/*.txt) $(wildcard assets/art/orderup/*.txt) assets/tiles/story.txt | $(BUILD) $(OUT)/preview
	python3 tools/gen_mg.py $(BUILD) $(OUT)/preview

# Battery Sort (src/bs.c; docs/minigames_bosses.md 4.6): its approved art -> build/bs_art.h, build/bs.json (tests),
# out/preview/bs_*_x8.png
$(BUILD)/bs_art.h: tools/gen_bs.py tools/gen_art.py $(wildcard assets/art/battery/*.txt) assets/approved/venues/factory_drink.txt | $(BUILD) $(OUT)/preview
	python3 tools/gen_bs.py $(BUILD) $(OUT)/preview

# Milk Run (src/mr.c; docs/minigames_bosses.md 4.10): its approved art -> build/mr_art.h, build/mr.json (tests),
# out/preview/mr_*_x8.png
$(BUILD)/mr_art.h: tools/gen_mr.py tools/gen_art.py $(wildcard assets/art/milkrun/*.txt) | $(BUILD) $(OUT)/preview
	python3 tools/gen_mr.py $(BUILD) $(OUT)/preview

# Log Roll (src/lr.c; docs/minigames_bosses.md 4.3): its approved art (look A) -> build/lr_art.h, build/lr.json (tests),
# out/preview/lr_*_x8.png
$(BUILD)/lr_art.h: tools/gen_lr.py tools/gen_art.py $(wildcard assets/art/logroll/*.txt) | $(BUILD) $(OUT)/preview
	python3 tools/gen_lr.py $(BUILD) $(OUT)/preview

# Asteroid Delivery (src/ad.c; docs/minigames_bosses.md 4.8): its approved art -> build/ad_art.h, build/ad.json (tests),
# out/preview/ad_*_x8.png
$(BUILD)/ad_art.h: tools/gen_ad.py tools/gen_art.py $(wildcard assets/art/asteroid/*.txt) assets/palettes.json assets/approved/venues/space_pal.json | $(BUILD) $(OUT)/preview
	python3 tools/gen_ad.py $(BUILD) $(OUT)/preview


# Taiko Pour (src/tk.c; docs/minigames_bosses.md 4.7): its approved art (look B) and chart (tools/taiko_chart.py) ->
# build/tk_art.h, build/tk.json (tests), out/preview/tk_*_x8.png
$(BUILD)/tk_art.h: tools/gen_tk.py tools/taiko_chart.py tools/gen_art.py $(wildcard assets/art/taiko/*.txt) | $(BUILD) $(OUT)/preview
	python3 tools/gen_tk.py $(BUILD) $(OUT)/preview

# Marshmallow Drop (src/mm.c; docs/minigames_bosses.md 4.5): its approved art (the hybrid, window W1) -> build/mm_art.h,
# build/mm.json (tests), out/preview/mm_*_x8.png
$(BUILD)/mm_art.h: tools/gen_mm.py tools/gen_art.py $(wildcard assets/art/marshmallow/*.txt) | $(BUILD) $(OUT)/preview
	python3 tools/gen_mm.py $(BUILD) $(OUT)/preview

# Monkey Business (src/mk.c; docs/minigames_bosses.md 4.9): its approved art -> build/mk_art.h, build/mk.json (tests),
# out/preview/mk_*_x8.png
$(BUILD)/mk_art.h: tools/gen_mk.py tools/gen_art.py $(wildcard assets/art/monkey/*.txt) | $(BUILD) $(OUT)/preview
	python3 tools/gen_mk.py $(BUILD) $(OUT)/preview

# T-Shirt Cannon (src/ts.c; docs/minigames_bosses.md 4.2): its approved art (look A + A1) and the landing table (tools/cannon_table.py,
# which fails the build when the fairness rule breaks) -> build/ts_art.h, build/ts.json (tests), out/preview/ts_*_x8.png
$(BUILD)/ts_art.h: tools/gen_ts.py tools/cannon_table.py tools/gen_art.py $(wildcard assets/art/tshirt/*.txt) | $(BUILD) $(OUT)/preview
	python3 tools/gen_ts.py $(BUILD) $(OUT)/preview

BONUS_H  += $(BUILD)/po_art.h
# The Pour-Off (src/po.c; docs/minigames_bosses.md section 5): Dregs's bartender frames (a PROPOSAL, pending owner approval)
# -> build/po_art.h, build/po.json (tests), out/preview/po_dregs_x8.png
$(BUILD)/po_art.h: tools/gen_po.py tools/gen_art.py $(wildcard assets/art/dregs/*.txt) | $(BUILD) $(OUT)/preview
	python3 tools/gen_po.py $(BUILD) $(OUT)/preview

BONUS_H  += $(BUILD)/dgag_art.h
# Dregs's late-arrival gags (src/dgag.c; docs/story.md "Dregs's exits"): new PROPOSAL art in assets/art/dgag plus the Pour-Off's Dregs, the
# Monkey Business monkey and the dust puff -> build/dgag_art.h, build/dgag.json (tests), out/preview/dgag_x8.png
$(BUILD)/dgag_art.h: tools/gen_dgag.py tools/gen_art.py $(wildcard assets/art/dgag/*.txt) assets/art/dregs/dregs.txt assets/art/monkey/monkey.txt assets/art/dust.txt | $(BUILD) $(OUT)/preview
	python3 tools/gen_dgag.py $(BUILD) $(OUT)/preview

preview: $(BUILD)/bs_art.h $(BUILD)/mr_art.h $(BUILD)/tk_art.h $(BUILD)/mm_art.h $(BUILD)/mk_art.h $(BUILD)/ts_art.h

# The boss engine (src/boss.c): each boss's body poses (and extra poses), held empties, topper and HUD face, and the HUD
# meter -> build/boss_art.h (the meter), build/boss_<name>_art.h (each boss's own, in his src/boss_<name>.c's bank),
# build/boss.json (tests), out/preview/boss_*_x8.png (build/venues.json: the Yeti's icy counter is made from the igloo's)
$(BUILD)/boss_art.h $(BOSS_H): tools/gen_boss.py tools/gen_art.py $(wildcard assets/art/boss/*.txt) assets/art/duke_entrance.txt $(BUILD)/art.h | $(BUILD) $(OUT)/preview
	python3 tools/gen_boss.py $(BUILD) $(OUT)/preview

# Leo's roar wave and entrance sprites (src/boss_leo.c) -> build/leo_fx_art.h, build/leo_fx.json (tests), out/preview/leo_fx_x8.png
$(BUILD)/leo_fx_art.h: tools/gen_leo_fx.py tools/gen_art.py assets/art/leo_fx.txt assets/art/boss/leo.txt | $(BUILD) $(OUT)/preview
	python3 tools/gen_leo_fx.py $(BUILD) $(OUT)/preview

# CLASSIC's end-of-level antics (src/antics.c): the bartender's four poses, the dove and the stars (approved 2026-10-11)
# -> build/antics_art.h, build/antics.json (tests), out/preview/antics_*_x8.png
$(BUILD)/antics_art.h: tools/gen_antics.py tools/gen_art.py $(wildcard assets/art/antics/*.txt) assets/art/bartender.txt | $(BUILD) $(OUT)/preview
	python3 tools/gen_antics.py $(BUILD) $(OUT)/preview

# The scene transition's fizzy drink (src/trans.c): eight BG tiles -> build/trans_art.h, build/trans.json (tests), out/preview/fizz_*_x8.png
$(BUILD)/trans_art.h: tools/gen_trans.py tools/gen_art.py assets/art/fizz.txt | $(BUILD) $(OUT)/preview
	python3 tools/gen_trans.py $(BUILD) $(OUT)/preview

# CGB palettes: assets/palettes.json -> build/palettes.c/.h
$(BUILD)/palettes.c $(BUILD)/palettes.h: tools/palettes2c.py assets/palettes.json | $(BUILD)
	python3 tools/palettes2c.py assets/palettes.json $(BUILD)

# Music: tune sources in tools/gen_music.py + tools/songs.py -> build/music_data.c (bank 2: order tables, jingles) and
# build/music_pat10.c (bank 10: the pattern blobs src/music.c copies into WRAM)
$(BUILD)/music_data.c: tools/gen_music.py tools/songs.py src/music.h | $(BUILD)
	python3 tools/gen_music.py $(BUILD)

$(BUILD)/music_pat10.c: $(BUILD)/music_data.c
	@true

# build/music_pat22.c: the credits tune's pattern blob (bank 22, with its harmony; streamed into the buffer: src/music.c)
$(BUILD)/music_pat22.c: $(BUILD)/music_data.c
	@true

# the soundtrack player's names (tools/songs.py SOUNDTRACK, in music.h's tune order) -> build/jukebox_names.h (src/jukebox.c)
$(BUILD)/jukebox_names.h: $(BUILD)/music_data.c
	@test -f $@

$(BUILD)/hUGEDriver.obj: $(HUGE)/hUGEDriver.asm $(wildcard $(HUGE)/include/*) | $(BUILD)
	rgbasm -i $(HUGE)/ -DGBDK -o $@ $<

$(HUGE_OBJ): $(BUILD)/hUGEDriver.obj $(HUGE)/tools/rgb2sdas.py
	python3 $(HUGE)/tools/rgb2sdas.py -c _CODE_2 -o $@ $<

# Each ROM variant (game, release, game-unlocked) is linked with its own scratch directory and depends on a flags stamp.
# Why: bankpack rewrites its input objects in place, so a shared build/hUGEDriver.o was touched (and could be rewritten while
# another build was reading it) by every variant's link; the lcc temp files lived in the shared /tmp; and a ROM did not depend
# on the flags at all, so a changed DEBUGFLAGS/LCCFLAGS reused the old ROM. Now build/obj/<variant>/ holds a private copy of
# the hUGEDriver object and the lcc temp files (-tempdir), and build/<variant>.flags (rewritten only when the flags change)
# is a prerequisite of the ROM.
ROM_DEPS := $(SRC) $(GEN) $(BONUS_H) $(BUILD)/art.h $(BUILD)/palettes.h $(HUGE_OBJ) $(HUGE)/include/hUGEDriver.h

.PHONY: FORCE
FORCE:

# $(call flags_stamp,variant,flags)
define flags_stamp
$(BUILD)/$(1).flags: FORCE | $(BUILD)
	@printf '%s\n' '$(2)' | cmp -s - $$@ || printf '%s\n' '$(2)' > $$@
endef

# $(call rom_rule,variant,rom,flags,extra check line or empty): one lcc invocation, log in build/<variant>_link.log
define rom_rule
$(call flags_stamp,$(1),$(3))
$(2): $(ROM_DEPS) $(BUILD)/$(1).flags
	mkdir -p $(BUILD)/obj/$(1)
	cp $(HUGE_OBJ) $(BUILD)/obj/$(1)/hUGEDriver.o
	$(LCC) $(3) -tempdir=$(BUILD)/obj/$(1) -I$(BUILD) -Isrc -I$(HUGE)/include -o $$@ $(SRC) $(GEN) $(BUILD)/obj/$(1)/hUGEDriver.o > $(BUILD)/$(1)_link.log 2>&1; rc=$$$$?; cat $(BUILD)/$(1)_link.log; test $$$$rc -eq 0 || { rm -f $$@; false; }
	@! grep -q "overflow from Bank 0" $(BUILD)/$(1)_link.log || { rm -f $$@; echo "ROM0 overflowed into bank 1 (see PLAN.md, ROM0 cleanup)"; false; }
	$(4)
	@romusage $(basename $(2)).noi 2>/dev/null | head -12 || true
	@python3 tools/rom0free.py $(basename $(2)).map
endef

$(eval $(call rom_rule,game,$(ROM),$(LCCFLAGS),@true))

# build/release.gb: the same flags without the debug menu (build/release.noi must not name its symbols)
RELEASE  := $(BUILD)/release.gb
release: $(RELEASE)
$(eval $(call rom_rule,release,$(RELEASE),$(filter-out $(DEBUGFLAGS),$(LCCFLAGS)),@grep -q debug_menu_open $(BUILD)/release.noi || { echo "release build lost the debug menu (it ships locked: src/debug.c)"; false; }))

# build/game-unlocked.gb: the playtest build with the debug menu always unlocked (for a flash cart); build/game.gb is untouched
UNLOCKED := $(BUILD)/$(NAME)-unlocked.gb
unlocked: $(UNLOCKED)
$(eval $(call rom_rule,$(NAME)-unlocked,$(UNLOCKED),$(filter-out $(DEBUGFLAGS),$(LCCFLAGS)) -DDEBUG_MENU -DDEBUG_UNLOCKED,@true))

# dist/: the release ROM (rebuilt from the sources; the debug menu ships locked, see DEBUGFLAGS) named by VERSION, its SHA-256,
# RELEASE.txt, licenses/ and CREDITS.md. Nothing is published (CLAUDE.md rule 5).
DIST := dist
dist:
	rm -f $(RELEASE)
	$(MAKE) $(RELEASE)
	rm -rf $(DIST)
	mkdir -p $(DIST)
	cp $(RELEASE) $(DIST)/spigoteer-v$(VERSION).gb
	cd $(DIST) && sha256sum spigoteer-v$(VERSION).gb > spigoteer-v$(VERSION).gb.sha256
	python3 tools/dist_info.py $(RELEASE) $(VERSION) > $(DIST)/RELEASE.txt
	cp -r licenses $(DIST)/licenses
	cp CREDITS.md $(DIST)/CREDITS.md
	@ls -l $(DIST)

test: $(ROM)
	python3 -m pytest -q tests

check: $(ROM)
	gbcheck $(ROM) --length 10 --out $(OUT)/check

preview: $(GEN) $(BUILD)/pour_art.h $(BUILD)/mg_art.h $(BUILD)/boss_art.h $(BUILD)/antics_art.h $(BUILD)/trans_art.h
	@ls -1 $(OUT)/preview/

clean:
	rm -rf $(BUILD) $(OUT)
