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

# Playtest variants (owner 2026-10-17), the default is the shipped art / no glow; each is built into its own directory so the default build is untouched:
#   make BUILD=out/b_tipA OUT=out/o_tipA TIP=A unlocked   TIP=A|B|C: the tip as a coin stack / a bill with coins / a bill alone (tools/gen_art.py, assets/art/tip/)
TIP      ?=
export TIP
ifneq ($(TIP),)
LCCFLAGS += -DTIP_VARIANT_$(TIP)
endif
# Playtest variants (owner 2026-10-17), off by default; each is built into its own directory so the default build is untouched:
#   make BUILD=out/b_glowA OUT=out/o_glowA GLOW=A unlocked  GLOW=A: the bistro oven's CGB palette pulse (src/glow.c); GLOW=B: a halo in the BG tiles
#                                                         around it and a flicker (assets/approved/venues/bistro_*_glowb.txt, tools/gen_art.py)
GLOW     ?=
export GLOW
ifneq ($(GLOW),)
LCCFLAGS += -DGLOW_$(GLOW)
endif

# Playtest variant (owner 2026-11-05): the credits as one continuous scroll instead of a fade between cards (src/credits.c "the scrolling credits"):
#   make BUILD=out/b_scroll OUT=out/o_scroll CREDITS=SCROLL unlocked
CREDITS  ?=
export CREDITS
ifeq ($(CREDITS),SCROLL)
LCCFLAGS += -DCREDITS_SCROLL
endif

SRC      := $(sort $(wildcard src/*.c))
PATRON_GROUPS := cowboys sports lumberjacks chefs divers robots punks ninjas zoo aliens
PATRON_C := $(foreach g,$(PATRON_GROUPS),$(BUILD)/patrons_$(g).c) $(BUILD)/patrons_saloon_x.c $(BUILD)/patrons_robots_x.c $(BUILD)/patrons_divers_x.c $(BUILD)/patrons_punks_x.c $(BUILD)/patrons_ninjas_x.c $(BUILD)/patron_load.c
PATRON_C += $(foreach v,sports lumberjacks chefs zoo aliens,$(BUILD)/patrons_$(v)_x.c)   # (the Atlas extras of the Stadium, the Lodge and the Bistro: assets/art/patrons/<venue>_x.txt)
# M9 themed venues (theme index = patron group): stage, bar, floor, drink, show and palettes per theme, one banked file each
VENUES   := saloon sports lodge bistro igloo factory biker teahouse zoo space festival
VENUE_C  := $(foreach t,$(VENUES),$(BUILD)/venue_$(t).c) $(BUILD)/venue_load.c
# M11b story mode: the script (docs/story.md), the portraits and the story font -> two banked files (tools/gen_story.py)
STORY_C  := $(BUILD)/story_data.c $(BUILD)/story_portraits.c $(BUILD)/story_pictures.c $(BUILD)/story_motion.c
PRACTICE_C := $(BUILD)/practice_art_a.c $(BUILD)/practice_art_b.c
GEN      := $(BUILD)/art.c $(PRACTICE_C) $(PATRON_C) $(VENUE_C) $(BUILD)/palettes.c $(BUILD)/looks.c $(BUILD)/music_data.c $(BUILD)/music_pat10.c $(BUILD)/music_pat22.c $(BUILD)/music_pat23.c $(BUILD)/music_pat24.c $(STORY_C) $(BUILD)/credits_text.c
# hUGEDriver (public domain, third_party/hugedriver): assembled with RGBDS, converted to a GBDK object by
# rgb2sdas.py, placed in ROM bank 2 next to the order tables and src/music.c (all `#pragma bank 2`); the song patterns are
# in bank 10 (build/music_pat10.c) and src/music.c copies them to WRAM, see tools/gen_music.py.
HUGE     := third_party/hugedriver
HUGE_OBJ := $(BUILD)/hUGEDriver.o
# each boss's own art header (tools/gen_boss.py: build/boss_<name>_art.h, #included by src/boss_<name>.c only)
BOSS_H   := $(foreach b,$(filter-out meter tag,$(basename $(notdir $(wildcard assets/art/boss/*.txt)))),$(BUILD)/boss_$(b)_art.h)
BONUS_H  := $(BUILD)/can_tiles.h $(BUILD)/list_keys.h $(BUILD)/list_skin.h $(BUILD)/title_art.h $(BUILD)/bonus2_art.h $(BUILD)/story.h $(BUILD)/pour_art.h $(BUILD)/mg_art.h $(BUILD)/mg_card_art.h $(BUILD)/mg_stub_art.h $(BUILD)/qd_art.h $(BUILD)/ou_art.h $(BUILD)/boss_art.h $(BOSS_H) $(BUILD)/leo_fx_art.h $(BUILD)/jukebox_names.h $(BUILD)/antics_art.h $(BUILD)/trans_art.h $(BUILD)/credits_text.h
BONUS_H  += $(BUILD)/practice_art.h
BONUS_H  += $(BUILD)/bs_art.h $(BUILD)/mr_art.h $(BUILD)/lr_art.h $(BUILD)/ad_art.h $(BUILD)/tk_art.h $(BUILD)/mm_art.h $(BUILD)/mk_art.h $(BUILD)/ts_art.h
ROM      := $(BUILD)/$(NAME).gb

.PHONY: all test check preview clean assets release dist unlocked cfall atlas atlas-page map-atlas

all: $(ROM)

assets: $(GEN)

$(BUILD) $(OUT)/preview:
	mkdir -p $@

# Tile and sprite data: bar.txt (shared BG tiles), bartender.txt (8x16 OBJ tiles, padded so each bartender frame is
# 4 OAM entries), the patrons, and the venues (assets/approved/venues: stage, bar, drink, show per theme)
# -> build/art.c/.h, build/patrons_*.c, build/venue_*.c, build/venues.json. Also writes x8 previews to out/preview/.
$(BUILD)/art.c $(BUILD)/art.h: tools/gen_art.py assets/tiles/bar.txt assets/tiles/title.txt assets/art/bartender.txt assets/art/glass_shards.txt assets/art/coin.txt assets/art/can.txt assets/art/geyser.txt assets/art/cat_walk.txt assets/art/droplets.txt assets/art/cursor.txt assets/art/title_fx.txt assets/art/dx_badge.txt assets/art/pour.txt assets/art/tap.txt assets/art/pour_glass.txt assets/art/tips.txt assets/art/hud_icons.txt assets/art/list_keys.txt assets/art/list_skin.txt $(wildcard assets/art/tip/*.txt) $(wildcard assets/art/patrons/*.txt) $(wildcard assets/art/splash/*.txt) $(wildcard assets/approved/venues/*) | $(BUILD) $(OUT)/preview
	python3 tools/gen_art.py $(BUILD) $(OUT)/preview

$(PATRON_C) $(VENUE_C) $(BUILD)/can_tiles.h $(BUILD)/list_keys.h $(BUILD)/list_skin.h $(BUILD)/title_art.h $(BUILD)/bonus2_art.h: $(BUILD)/art.c
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
$(BUILD)/po_art.h: tools/gen_po.py tools/gen_art.py $(wildcard assets/art/dregs/*.txt) $(wildcard assets/art/pouroff/*.txt) | $(BUILD) $(OUT)/preview
	python3 tools/gen_po.py $(BUILD) $(OUT)/preview

# The one-line menus' shared tiles (src/oneline.c; SOUNDTRACK, MINI GAMES, BOSS RUSH): the hand-placed grids in assets/art -> build/ol_tiles.h
BONUS_H  += $(BUILD)/ol_tiles.h
$(BUILD)/ol_tiles.h: tools/gen_ol_tiles.py assets/art/ol_tiles.txt assets/art/ol_icons.txt | $(BUILD)
	python3 tools/gen_ol_tiles.py $(BUILD)

# The Practice screen's illustrations (src/mg_list.c; assets/art/practice/README.md): one 80 x 64 indexed PNG a game -> de-duplicated tiles, a 10 x 8 map and a CGB palette
# in two banked data files + build/practice_art.h, build/practice_art.json (tests), out/preview/practice_<game>_x4.png. A game without a PNG shows the empty frame.
# PRACTICE_ART_DIRS: where the PNGs are looked for, first hit wins. The default is the real art alone; the tests build a ROM of their own from the placeholder
# cards (make BUILD=out/b_pa OUT=out/o_pa PRACTICE_ART_DIRS=tests/data/practice_art out/b_pa/game.gb), so placeholders never ship.
PRACTICE_ART_DIRS ?= assets/art/practice
$(BUILD)/practice_art_a.c $(BUILD)/practice_art_b.c $(BUILD)/practice_art.h $(BUILD)/practice_art.json &: tools/gen_practice_art.py $(foreach d,$(PRACTICE_ART_DIRS),$(wildcard $(d)/*.png)) | $(BUILD) $(OUT)/preview
	python3 tools/gen_practice_art.py $(BUILD) $(OUT)/preview --dirs $(PRACTICE_ART_DIRS)

# The Boss Rush list's portraits (src/rush.c): each boss's sprite centred by its drawn pixels -> build/rush_portraits.h (tools/gen_rush_portraits.py)
BONUS_H  += $(BUILD)/rush_portraits.h
$(BUILD)/rush_portraits.h: tools/gen_rush_portraits.py assets/tiles/story.txt $(BOSS_H) | $(BUILD)
	python3 tools/gen_rush_portraits.py $(BUILD)

BONUS_H  += $(BUILD)/cameo_art.h
# Story cameos (src/cameo.c): the Sasquatch / Leo poses, the valve and the map UFO transcribed to OBJ tiles + the hand-placed beam
# (assets/art/cameo/beam.txt) -> build/cameo_art.h
$(BUILD)/cameo_art.h: tools/gen_cameo.py assets/art/cameo/beam.txt assets/art/cameo/valve.txt assets/art/boss/sasquatch.txt assets/art/boss/leo.txt assets/story_map/obj_ufo.png | $(BUILD)
	python3 tools/gen_cameo.py $(BUILD)

BONUS_H  += $(BUILD)/dgag_art.h $(BUILD)/smap_art.h
# Dregs's late-arrival gags (src/dgag.c; docs/story.md "Dregs's exits"): new PROPOSAL art in assets/art/dgag plus the Pour-Off's Dregs, the
# Monkey Business monkey and the dust puff -> build/dgag_art.h, build/dgag.json (tests), out/preview/dgag_x8.png
$(BUILD)/dgag_art.h: tools/gen_dgag.py tools/gen_art.py $(wildcard assets/art/dgag/*.txt) assets/art/dregs/dregs.txt assets/art/monkey/monkey.txt assets/art/dust.txt | $(BUILD) $(OUT)/preview
	python3 tools/gen_dgag.py $(BUILD) $(OUT)/preview

# The story map (src/smap.c; the owner-approved v14 sprites, 2026-10-18): assets/story_map/obj_*.png -> build/smap_art.h (OBJ tiles and palettes),
# build/smap.json (tests)
$(BUILD)/smap_art.h: tools/gen_smap.py assets/story_map/clouds.txt assets/story_map/clouds_big.txt assets/story_map/cloud_layout.txt $(wildcard assets/story_map/*.png) | $(BUILD) $(OUT)/preview
	python3 tools/gen_smap.py $(BUILD) $(OUT)/preview

# The story map's scrolling world (owner 2026-11-04, Q76 / Q78): the concept's hand-typed 64 x 48 cell world (tools/smap_world/) -> four banked data files
# (Color and DMG: cells, cloud, slot plan / allocator hints, tiles) with their accessors, build/smap_world.h (the stops, the legs), build/smap_world.json
# (tests), out/preview/smap_world_*.png. The build fails when a window is over the tile or palette budget.
SMAPW_C := $(BUILD)/smap_wc_a.c $(BUILD)/smap_wc_t.c $(BUILD)/smap_wd_a.c $(BUILD)/smap_wd_t.c $(BUILD)/smap_an.c
GEN      += $(SMAPW_C)
BONUS_H  += $(BUILD)/smap_world.h
$(SMAPW_C) $(BUILD)/smap_world.h $(BUILD)/smap_world.json &: tools/gen_smap_world.py $(wildcard tools/smap_gear.json) $(wildcard tools/smap_world/world_snap.py) $(wildcard tools/smap_world/anims.py) $(wildcard tools/smap_world/falls_cascade.json) $(wildcard assets/smap/*) $(wildcard assets/story_map/world/*.txt) | $(BUILD) $(OUT)/preview
	python3 tools/gen_smap_world.py $(BUILD) $(OUT)/preview

# Prerequisites the generators read that their rules above do not list (test batch 2, B3: found by logging every file each generator opens during
# `make -B` and comparing with the rules). Without them an incremental `make` kept stale generated files after editing one of these.
$(BUILD)/art.c: assets/tiles/story.txt src/layout.h tools/artifacts/palette_plan/plan_slots.json
$(BUILD)/boss_art.h: $(wildcard assets/approved/venues/*_tilt.txt)
$(BUILD)/credits_text.c: $(wildcard assets/approved/venues/*_pal.json) $(wildcard assets/art/patrons/*_x.txt) $(wildcard tools/artifacts/palette_plan/*.py) tools/artifacts/palette_plan/plan_slots.json
$(BUILD)/looks.c: src/game.h tools/artifacts/palette_plan/plan_slots.json
$(BUILD)/smap_world.h: src/order.h
$(BUILD)/story_data.c: assets/tiles/bar.txt src/level.c
$(BUILD)/music_data.c: tools/harmony.py

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

# The Color-only extra looks' (look, palette) combination tables and instance slots: generated from the Graphics Atlas plan (tools/gen_looks.py)
$(BUILD)/looks.c $(BUILD)/looks.h $(BUILD)/looks_pick.h: tools/gen_looks.py tools/dev/extra_combos.py $(wildcard tools/artifacts/palette_plan/*.py) assets/palettes.json src/mirror.c $(BUILD)/palettes.c | $(BUILD)
	python3 tools/gen_looks.py $(BUILD)

# Music: tune sources in tools/gen_music.py + tools/songs.py -> build/music_data.c (bank 2: order tables, jingles) and
# build/music_pat10.c (bank 10: the pattern blobs src/music.c copies into WRAM)
$(BUILD)/music_data.c: tools/gen_music.py tools/songs.py src/music.h | $(BUILD)
	python3 tools/gen_music.py $(BUILD)

$(BUILD)/music_pat10.c: $(BUILD)/music_data.c
	@true

# build/music_pat22.c: the credits tune's pattern blob (bank 22, with its harmony; streamed into the buffer: src/music.c)
$(BUILD)/music_pat22.c: $(BUILD)/music_data.c
	@true

# build/music_pat23.c: the title tune's blob and harmony (bank 23, streamed like the credits'); build/music_pat24.c: the jingles' patterns (bank 24)
$(BUILD)/music_pat23.c $(BUILD)/music_pat24.c: $(BUILD)/music_data.c
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
ROM_DEPS := $(SRC) $(wildcard src/*.h) $(GEN) $(BONUS_H) $(BUILD)/art.h $(BUILD)/palettes.h $(BUILD)/looks.h $(BUILD)/looks_pick.h $(HUGE_OBJ) $(HUGE)/include/hUGEDriver.h

.PHONY: FORCE
FORCE:

# $(call flags_stamp,variant,flags)
define flags_stamp
$(BUILD)/$(1).flags: FORCE | $(BUILD)
	@printf '%s\n' '$(2)' | cmp -s - $$@ || printf '%s\n' '$(2)' > $$@
endef

# $(call rom_rule,variant,rom,flags,extra check line or empty): one lcc invocation, log in build/<variant>_link.log
# prep: everything every ROM variant needs except the lcc/link step (generated sources, headers, hUGEDriver object, the game and
# release flags stamps). tools/dev/verify.sh runs it first and once, so `make` and `make release` can then run at the same time:
# both find all their prerequisites current and write only their own build/<variant>.* files and build/obj/<variant>/.
.PHONY: prep
prep: $(ROM_DEPS) $(BUILD)/game.flags $(BUILD)/release.flags

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

# ---- the per-object build, the DEFAULT since test batch 3 (D1; owner): `make OBJ=0` selects the old one-shot lcc call (the reference). OBJ is exported, so the tests' `make BUILD=...` variant builds follow ----
# With OBJ=1 (the default) each C file is compiled to its own object by tools/dev/objs.mk (OBJJOBS jobs at a time,
# 8 by default, per build; sdcc's -MMD header dependencies, so a header edit recompiles only its includers), then ONE lcc link step links the
# objects in the one-shot call's order (SRC, then GEN, then the hUGEDriver object: a fixed list, never the order the jobs finish in). The objects
# are copied to build/obj/<variant>/link/ first: bankpack rewrites its input objects in place (the a0e50dc0 lesson), and the compile objects
# in build/obj/<variant>/o/ must stay pristine for the next incremental build. Every variant in every BUILD directory has its own object
# directory; no object is shared between builds. The ROM is byte-identical to the one-shot ROM (batch 3 report, A3).
OBJ     ?= 1
OBJJOBS ?= 8
export OBJ
define rom_rule_obj
$(call flags_stamp,$(1),$(3))
$(2): $(ROM_DEPS) $(BUILD)/$(1).flags
	mkdir -p $(BUILD)/obj/$(1)/o
	$(MAKE) -f tools/dev/objs.mk -j$(OBJJOBS) --no-print-directory OBJD=$(BUILD)/obj/$(1)/o STAMP=$(BUILD)/$(1).flags BUILD=$(BUILD) LCC=$(LCC) FLAGS='$(3)' SRCS='$(SRC) $(GEN)'
	rm -rf $(BUILD)/obj/$(1)/link
	mkdir -p $(BUILD)/obj/$(1)/link
	cp $(foreach s,$(SRC) $(GEN),$(BUILD)/obj/$(1)/o/$(basename $(notdir $(s))).o) $(HUGE_OBJ) $(BUILD)/obj/$(1)/link/
	$(LCC) $(3) -tempdir=$(BUILD)/obj/$(1)/link -I$(BUILD) -Isrc -I$(HUGE)/include -o $$@ $(foreach s,$(SRC) $(GEN),$(BUILD)/obj/$(1)/link/$(basename $(notdir $(s))).o) $(BUILD)/obj/$(1)/link/hUGEDriver.o > $(BUILD)/$(1)_link.log 2>&1; rc=$$$$?; cat $(BUILD)/$(1)_link.log; test $$$$rc -eq 0 || { rm -f $$@; false; }
	@! grep -q "overflow from Bank 0" $(BUILD)/$(1)_link.log || { rm -f $$@; echo "ROM0 overflowed into bank 1 (see PLAN.md, ROM0 cleanup)"; false; }
	$(4)
	@romusage $(basename $(2)).noi 2>/dev/null | head -12 || true
	@python3 tools/rom0free.py $(basename $(2)).map
endef
ROM_RULE := $(if $(filter 1,$(OBJ)),rom_rule_obj,rom_rule)

$(eval $(call $(ROM_RULE),game,$(ROM),$(LCCFLAGS),@true))

# build/release.gb: the same flags without the debug menu (build/release.noi must not name its symbols)
RELEASE  := $(BUILD)/release.gb
release: $(RELEASE)
$(eval $(call $(ROM_RULE),release,$(RELEASE),$(filter-out $(DEBUGFLAGS),$(LCCFLAGS)),@grep -q debug_menu_open $(BUILD)/release.noi || { echo "release build lost the debug menu (it ships locked: src/debug.c)"; false; }))

# build/game-unlocked.gb: the playtest build with the debug menu always unlocked (for a flash cart); build/game.gb is untouched
UNLOCKED := $(BUILD)/$(NAME)-unlocked.gb
unlocked: $(UNLOCKED)

$(eval $(call $(ROM_RULE),$(NAME)-unlocked,$(UNLOCKED),$(filter-out $(DEBUGFLAGS),$(LCCFLAGS)) -DDEBUG_MENU -DDEBUG_UNLOCKED,@true))

# build/game-c.gb: the same ROM as build/game.gb with every asm candidate built from its C version (-DASM_PASS=0, src/asm_cfg.h).
# The C is the reference the owner may port; `GB_ROM=build/game-c.gb python3 -m pytest -q tests` runs the whole suite on it.
CFALL := $(BUILD)/$(NAME)-c.gb
cfall: $(CFALL)
$(eval $(call $(ROM_RULE),$(NAME)-c,$(CFALL),$(LCCFLAGS) -DASM_PASS=0,@true))

# The default build as a debug ROM for review (the bosses' capacity mug row above and to the right, the hand mugs, the Mothership's beam):
# out/test_roms/spigoteer-bosscap-unlocked.gb with its .noi beside it (tests/test_boss_cap_ui.py needs no ROM of its own).
.PHONY: bosscap
bosscap: unlocked
	mkdir -p $(OUT)/test_roms
	cp $(UNLOCKED) $(OUT)/test_roms/spigoteer-bosscap-unlocked.gb
	cp $(BUILD)/$(NAME)-unlocked.noi $(OUT)/test_roms/spigoteer-bosscap-unlocked.noi

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

# JOBS=1 is the old serial run; otherwise tools/dev/ptest.py shards the tests over JOBS pytest processes (same results, see its docstring)
JOBS ?= 8
# Targeted runs: make test K='<pytest -k expression>' and/or make test F=<test file>. Without them, the whole suite as before.
test: $(ROM)
ifeq ($(JOBS),1)
	python3 -m pytest -q $(if $(K),-k '$(K)') $(or $(F),tests)
else
	python3 tools/dev/ptest.py -j $(JOBS) $(if $(K),-k '$(K)') $(or $(F),tests)
endif

check: $(ROM)
	gbcheck $(ROM) --length 10 --out $(OUT)/check

preview: $(GEN) $(BUILD)/pour_art.h $(BUILD)/mg_art.h $(BUILD)/boss_art.h $(BUILD)/antics_art.h $(BUILD)/trans_art.h
	@ls -1 $(OUT)/preview/

# The graphics atlas (tools/gfx_atlas): every screen on DMG and CGB, palettes / tiles / attributes / sprites -> out/atlas/index.html (+ data/, img/).
# One command, deterministic; reads build/game.gb (run `make` first). Open out/atlas/standalone.html locally.
atlas: $(ROM)
	python3 tools/gfx_atlas/build.py

# The Graphics Atlas page, publishable: rebuilds the capture only when src/ or assets/ changed since its commit, runs build.py + the self-check
# + the 360 px page check, writes out/atlas_page/pub.json (the files to publish). Fails on any self-check error. Needs a built ROM for `make atlas`.
atlas-page:
	python3 tools/artifacts/palette_plan/atlas_page.py

# The Map Atlas review page (owner 11-08): needs a built ROM (`make`); writes out/map_atlas/ (index.html + img/*.png) from tools/artifacts/map_atlas/.
map-atlas:
	python3 tools/artifacts/map_atlas/build.py

clean:
	rm -rf $(BUILD) $(OUT)
