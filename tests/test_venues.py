# M9: themed venues. Each level loads the venue of its theme (theme index = patron group): stage, bar, floor, the
# drink in place of the beer mug, the show performers, and on CGB their palettes. Expected tile ids, maps and tile
# data come from build/venues.json (tools/gen_art.py), which is cut from assets/approved/venues/.
import json
import re

import pytest
from conftest import GAME, LAYOUT, ROOT, THEMES, VENUES, bar_counter_row, bar_top_row, check_golden, level_attr, logical_tile, venue
from test_art import GROUPS, goto_group
from test_bonus import enter_bonus, pick
from test_flow import BONUS, PLAYING, run_until, state, tilemap_row
from test_patrons import DRINKING, MAX_P, hold_mug, patrons, put, set_patron

pytestmark = pytest.mark.timeout(120)

ART_H = (ROOT / "build" / "art.h").read_text()


def _gen_art():
    import importlib.util
    spec = importlib.util.spec_from_file_location("gen_art", ROOT / "tools" / "gen_art.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


gen_art_blocks = lambda path: _gen_art().blocks(path)
gen_art_tile = lambda rows, x, y: _gen_art().tile_bytes(rows, x, y)


def art(name):
    return int(re.search(rf"#define {name} (\d+)", ART_H).group(1))


OBJ_MUG = GAME["OBJ_BT_END"]
OBJ_MUG_FILL = OBJ_MUG + art("MUG_TILE_COUNT") + art("GLASS_TILE_COUNT")
OBJ_MUG_DRINK = OBJ_MUG_FILL + art("MUG_FILL_TILE_COUNT")
OBJ_DANCER = OBJ_MUG_DRINK + art("MUG_DRINK_TILE_COUNT") + art("COIN_TILE_COUNT")
SHOW_FRAMES = 704
BGPAL_PATRON, BGPAL_BAR = 2, 0
OBJPAL_MUG_FULL, OBJPAL_MUG_EMPTY, OBJPAL_DANCER = 1, 2, 5
# theme of each patron group, as the owner assigned them
GROUP_THEME = {"cowboys": "saloon", "sports": "sports", "lumberjacks": "lodge", "chefs": "bistro", "divers": "igloo",
               "robots": "factory", "punks": "biker", "ninjas": "teahouse", "zoo": "zoo", "aliens": "space"}


def w16(gb, name, v):
    gb.write(name, v & 255)
    gb.write(gb.addr(name) + 1, v >> 8)


def obj_vram(gb, first, n):
    return b"".join(bytes(gb.read(0x8000 + t * 16, 16)) for t in range(first, first + n))


def bg_vram(gb, first, n):           # LCDC bit 4 = 0: ids 0..127 at 0x9000
    return b"".join(bytes(gb.read(0x9000 + t * 16, 16)) for t in range(first, first + n))


def cgb_palette(gb, i, obj=False):
    """CGB palette RAM through BCPS/BCPD (OCPS/OCPD): 4 RGB15 colours of palette i."""
    idx, data = (0xFF6A, 0xFF6B) if obj else (0xFF68, 0xFF69)
    out = []
    for c in range(4):
        gb.write(idx, i * 8 + c * 2)
        lo = gb.read(data, 1)[0]
        gb.write(idx, i * 8 + c * 2 + 1)
        out.append(lo | gb.read(data, 1)[0] << 8)
    return out


def attr_row(gb, y):
    return [gb.pb.memory[1, 0x9800 + y * 32 + x] & 7 for x in range(20)]


def at_theme(gb, g):
    goto_group(gb, g)
    gb.write("tip_chance", 0)
    assert gb.mem("venue_id") == g
    return venue(g)


NEW_ORDER = ["saloon", "sports", "lodge", "bistro", "igloo", "factory", "biker", "teahouse", "zoo", "space"]


def test_one_order_for_every_list():
    """The 10th venue (owner 2026-10-10): The Chrome Cow is 7th, the space lounge last, in story AND arcade. One index
    means one venue everywhere: theme = patron group = arcade level row - 1 = story chapter = venue tune = pour art."""
    import sys
    sys.path.insert(0, str(ROOT / "tools"))
    import songs
    assert THEMES == NEW_ORDER
    assert GROUPS == ["cowboys", "sports", "lumberjacks", "chefs", "divers", "robots", "punks", "ninjas", "zoo", "aliens"]
    assert songs.VENUES == ["susanna", "ballgame", "mountain", "funicula", "skaters", "hall", "sailor", "sakura",
                            "weasel", "danube"]
    story = __import__("json").loads((ROOT / "build" / "story.json").read_text())
    assert [c["venue"] for c in story["chapters"]] == list(range(10))
    assert [c["suffix"] for c in story["chapters"]] == ["SALOON", "STADIUM", "LUMBER", "BISTRO", "IGLOO", "ROBOT",
                                                       "BIKER", "TEAHOUSE", "ZOO", "SPACE"]
    pour = __import__("json").loads((ROOT / "build" / "pour.json").read_text())
    assert list(pour["venues"]) == THEMES, "pour_load(chapter): the perfect pour's frames in the same order"


@pytest.mark.parametrize("group", [6, 7, 8, 9], ids=NEW_ORDER[6:])
def test_arcade_levels_7_to_10_are_the_new_order(gb, group):
    """Arcade: level 7 is The Chrome Cow (its venue, punks and Drunken Sailor), then the teahouse, the zoo, the space
    lounge; level 11 is the saloon again (test_scores, test_flow)."""
    at_theme(gb, group)
    assert gb.mem("level") == group + 1 and gb.mem("cur_group") == group
    assert gb.mem("cur_tune") == 5 + group, "TUNE_VENUE0 + the group"


def test_theme_order_follows_the_patron_groups():
    assert THEMES == [GROUP_THEME[g] for g in GROUPS]
    assert re.search(r"// venue order: (.*)", ART_H).group(1).split(", ") == THEMES
    assert THEMES[0] == "saloon", "the generic look is theme 0"


def test_the_show_tables():
    """Every venue's show table (tools/gen_art.py show_tiles): a dance (4 frames) row f is the frame laid out as the
    bartender, [8f, 8f + 2, 8f + 4, 8f + 6]; a band (6 frames) row r is frame r's four 8x16 quarters, deduplicated into
    the 32 tiles, and its tiles rebuild the frame exactly."""
    for t in THEMES:
        v = venue(t)
        tab, band = v["show_table"], v["show_band"]
        assert len(tab) == 6 and all(len(r) == 4 for r in tab), t
        assert band == (v["show_frames"] == 6), t
        assert all(0 <= x < 32 and x % 2 == 0 for r in tab for x in r), t
        if not band:
            assert tab[:4] == [[8 * f, 8 * f + 2, 8 * f + 4, 8 * f + 6] for f in range(4)], t
            continue
        shows = [r for _, r in gen_art_blocks(ROOT / "assets" / "approved" / "venues" / f"{t}_show.txt")]
        tiles = bytes(v["show"])
        for r, frame in zip(tab, shows):
            for (y0, x0), off in zip(((0, 0), (0, 8), (16, 0), (16, 8)), r):
                rows = (list(frame) + ["." * 16] * 8)[y0:y0 + 16]
                want = bytes(gen_art_tile(rows, x0, 0) + gen_art_tile(rows, x0, 8))
                assert tiles[off * 16:off * 16 + 32] == want, f"{t}: quarter at {(y0, x0)}"


def test_theme_tile_pool_holds_every_theme_and_the_bg_budget_holds():
    """Option A (owner 2026-10-10): BG ids 0..35 are one pool; the stage takes ids from 0 up, the bar + floor pack at
    the top (36 - bar_n ..), never below 23: the title draws the saloon's bar while its menu text overwrites 0..22."""
    pool, text = VENUES["pool"], VENUES["title_text_slot"]
    assert (pool, text) == (art("VENUE_POOL"), art("TITLE_TEXT_SLOT")) == (36, 23)
    assert art("TILE_STAGE_BASE") == 0 and art("TILE_GENERIC_BASE") == pool
    assert art("BAR_TILE_COUNT") == art("TILE_GENERIC_BASE") + art("GENERIC_TILE_COUNT")
    assert art("BAR_TILE_COUNT") + art("PATRON_GROUP_TILES") <= 256
    for t in THEMES:
        v = venue(t)
        assert v["stage_n"] + v["bar_n"] <= pool, t
        assert v["bar_base"] == pool - v["bar_n"] >= text, t
        assert all(0 <= i < v["stage_n"] for i in v["stage_map"]), t
        assert all(v["bar_base"] <= i < pool for i in v["bar_map"] + [v["floor_tile"]]), t
        assert set(v["stage_attr"]) <= {5, 6} and set(v["bar_attr"]) <= {0, 7}, t
        assert v["bar_attr"][2:17] == [0] * 15 and v["bar_attr"][22:37] == [0] * 15, f"{t}: wall columns on the bar palette"


@pytest.mark.parametrize("group", range(len(GROUPS)), ids=[GROUP_THEME[g] for g in GROUPS])
def test_each_level_loads_its_venue(gb, group):
    v = at_theme(gb, group)
    gb.run(2)
    first = LAYOUT["STAGE_FIRST_ROW"]
    for r in range(4):
        assert tilemap_row(gb, first + r, 0, 20) == v["stage_map"][r * 20:r * 20 + 20], f"stage row {r}"
    for b in range(4):
        assert tilemap_row(gb, bar_counter_row(b), 0, 20) == v["bar_map"][40:60], f"bar {b} counter row"
        covered = {c for p in patrons(gb) if p["bar"] == b for c in range(p["x"] >> 3, (p["x"] >> 3) + 3)}
        for r in range(2):                       # the wall rows wherever no patron stands
            row = tilemap_row(gb, bar_top_row(b) + r, 0, 20)
            assert [row[c] for c in range(20) if c not in covered] == \
                [v["bar_map"][r * 20 + c] for c in range(20) if c not in covered], f"bar {b} row {r}"
    assert tilemap_row(gb, LAYOUT["FLOOR_ROW"], 0, 20) == [v["floor_tile"]] * 20
    assert bg_vram(gb, 0, v["stage_n"]) == bytes(v["stage_tiles"])
    assert bg_vram(gb, v["bar_base"], v["bar_n"]) == bytes(v["bar_tiles"])
    assert obj_vram(gb, OBJ_MUG, 4) + obj_vram(gb, OBJ_MUG_FILL, 8) + obj_vram(gb, OBJ_MUG_DRINK, 8) == bytes(v["drink"])
    # the crash generated from this drink (gen_art crash_frames); DMG keeps it plane-swapped like the sliding drinks
    crash = bytes(v["crash"])
    if gb.model_name != "cgb":
        crash = bytes(crash[i ^ 1] for i in range(len(crash)))
    assert obj_vram(gb, OBJ_MUG + art("MUG_TILE_COUNT"), art("GLASS_TILE_COUNT")) == crash, "the venue's crash"
    assert obj_vram(gb, OBJ_DANCER, 32) == bytes(v["show"])
    if gb.model_name == "cgb":
        for r in range(4):
            assert attr_row(gb, first + r) == v["stage_attr"][r * 20:r * 20 + 20]
        for b in range(4):
            assert attr_row(gb, bar_counter_row(b)) == level_attr(group, v["bar_attr"])[40:60]
            assert attr_row(gb, bar_top_row(b) + 1)[17:20] == level_attr(group, v["bar_attr"])[37:40], "spout and keg"
        assert cgb_palette(gb, 5) == v["pal"][0] and cgb_palette(gb, 6) == v["pal"][1]
        assert cgb_palette(gb, BGPAL_BAR) == v["pal"][2]
        # (the Saloon's BG 7 holds its palette instance 3, ROSIE and REDD: the keg's slot is free there; its colour 0 is the wall, below)
        if GROUPS[group] in ("robots", "divers", "punks"):      # (the generated venues: BG 7 holds look C's palette instance (TELLY's mint, MOOSE's), loaded with the level; the keg is on BG 1)
            assert cgb_palette(gb, 7)[0] == v["pal"][2][0] and cgb_palette(gb, 7)[1:] == json.loads((ROOT / "assets" / "palettes.json").read_text())[GROUPS[group] + "_c"]["rgb15"]
        else:
            assert cgb_palette(gb, 7) == v["pal"][3] if group else cgb_palette(gb, 7)[0] == v["pal"][2][0]
        assert cgb_palette(gb, OBJPAL_MUG_FULL, obj=True)[1:] == v["pal"][4][1:]
        if GROUPS[group] != "punks":             # (the Chrome Cow's empty mug is OBJ 1 with the bit planes swapped, lift.c: its OBJ 2 is DJ's yellow)
            assert cgb_palette(gb, OBJPAL_MUG_EMPTY, obj=True)[1:] == v["pal"][5][1:]
        looks_on = re.search(r"looks_on\[\d+\] = \{ ([^}]*)\}", (ROOT / "build" / "looks_pick.h").read_text()).group(1).replace(",", "").split()
        if group and looks_on[group] == "0":     # (the Saloon and a venue with Color-only looks keep their 5th palette instance in OBJ 5 until a show takes it: render.c pal5_check)
            assert cgb_palette(gb, OBJPAL_DANCER, obj=True)[1:] == v["pal"][6][1:]
    else:
        assert gb.read(0xFF47, 1)[0] == 0xE4, "DMG: the fixed grey ramp (the venue art is luminance-ordered)"


@pytest.mark.parametrize("group", range(len(GROUPS)), ids=[GROUP_THEME[g] for g in GROUPS])
@pytest.mark.only_model("cgb")
def test_patron_palettes_take_the_venue_wall_colour(gb, group):
    v = at_theme(gb, group)
    wall = v["pal"][2][0]
    assert cgb_palette(gb, BGPAL_BAR)[0] == wall
    for k in range(3):
        assert cgb_palette(gb, BGPAL_PATRON + k)[0] == wall, f"patron palette {k}: colour 0 is the wall"
    if group == 0:                       # patron-rev-2: the Saloon's palette instances 3 and 4 (BG 7; BG 5 below the split line, SPLIT_PAL)
        assert cgb_palette(gb, 7)[0] == wall


@pytest.mark.parametrize("group", [0, 1, 4, 6, 9], ids=["saloon", "sports", "igloo", "biker", "space"])
def test_the_drink_frames_in_oam_are_the_venue_drink(gb, group):
    v = at_theme(gb, group)
    gb.write("intro_timer", 255)
    drink = bytes(v["drink"])
    frame = lambda k: drink[k * 32:k * 32 + 32]          # 8x16 frame k: 2 tiles
    # filling: OAM 4, fill frames 1..4 = drink frames 2..5
    gb.hold("a")
    gb.run(2)                                        # (the press is polled by the next frame, drawn the one after)
    seen = set()
    for _ in range(22):
        gb.run(1)
        s = [s for s in gb.visible_sprites() if OBJ_MUG_FILL <= s["tile"] < OBJ_MUG_FILL + 8]
        assert len(s) == 1
        seen.add(s[0]["tile"])
    assert seen == {OBJ_MUG_FILL + 2 * k for k in range(4)}
    assert all(obj_vram(gb, OBJ_MUG_FILL + 2 * k, 2) == frame(2 + k) for k in range(4))
    gb.release("a")
    gb.run(4)
    full = [s for s in gb.visible_sprites() if logical_tile(s["tile"]) == OBJ_MUG]   # (M13a: DMG shows a copy)
    assert len(full) == 1 and obj_vram(gb, OBJ_MUG, 2) == frame(0), "the sliding full drink"
    assert obj_vram(gb, OBJ_MUG + 2, 2) == frame(1), "the sliding empty"
    # held: a drinking patron holds frames 6..9 at his face
    i = set_patron(gb, 1, 40, state=DRINKING, timer=40)
    hold_mug(gb, i, 1)
    gb.run(3)
    held = [s for s in gb.visible_sprites() if OBJ_MUG_DRINK <= s["tile"] < OBJ_MUG_DRINK + 8]
    assert len(held) == 1
    k = (held[0]["tile"] - OBJ_MUG_DRINK) // 2
    assert obj_vram(gb, held[0]["tile"], 2) == frame(6 + k)


@pytest.mark.parametrize("group", range(len(GROUPS)), ids=[GROUP_THEME[g] for g in GROUPS])
def test_the_show_uses_the_venue_performers(gb, group):
    v = at_theme(gb, group)
    w16(gb, "show_timer", SHOW_FRAMES)
    gb.run(40)
    ds = [s for s in gb.visible_sprites() if OBJ_DANCER <= s["tile"] < OBJ_DANCER + 32]
    assert len(ds) == 12, "three performers of 4 entries"
    assert obj_vram(gb, OBJ_DANCER, 32) == bytes(v["show"])
    check_show_rows(gb, v)


def show_rows_on_screen(gb):
    """Per performer (left to right) the 4 OBJ tiles of OAM 28..39, TL TR BL BR, as offsets from OBJ_DANCER."""
    oam = gb.read(0xFE00 + 28 * 4, 48)
    return [[oam[(4 * k + i) * 4 + 2] - OBJ_DANCER for i in range(4)] for k in range(3)]


def check_show_rows(gb, v, frames=60):
    """The show table (gen_art show_tiles): a dance shows row dancer_frame on all three; a band shows performer k's
    row 2k + (beat & 1). Checked on frames whose dance step did not just change (the entries follow a frame later)."""
    table, band = v["show_table"], v["show_band"]
    seen = set()
    last = gb.mem("dancer_frame")
    for _ in range(frames):
        gb.run(1)
        f = gb.mem("dancer_frame")
        if f != last:
            last = f
            continue
        want = [table[2 * k + (f & 1)] if band else table[f] for k in range(3)]
        assert show_rows_on_screen(gb) == want, f"dance step {f}"
        seen.add(f)
    assert len(seen) >= 3, "the show moved through its steps"


def test_a_bonus_round_between_levels_restores_the_performer_tiles(gb):
    lodge = venue("lodge")
    assert obj_vram(gb, OBJ_DANCER, 32) == bytes(venue("saloon")["show"])
    enter_bonus(gb)                                  # after level 2: the cans borrow OBJ tiles 96..127
    gb.run(5)
    assert obj_vram(gb, OBJ_DANCER, 32) != bytes(venue("saloon")["show"])
    pick(gb, 1)
    run_until(gb, lambda: state(gb) == PLAYING, 400)
    assert gb.mem("level") == 3 and gb.mem("venue_id") == 2
    assert obj_vram(gb, OBJ_DANCER, 32) == bytes(lodge["show"]), "level 3 shows the lodge's performers"
    w16(gb, "show_timer", SHOW_FRAMES)
    gb.run(40)
    assert len([s for s in gb.visible_sprites() if OBJ_DANCER <= s["tile"] < OBJ_DANCER + 32]) == 12


def test_the_bonus_round_stands_in_the_venue_just_played(gb):
    v = venue("saloon")
    enter_bonus(gb)
    gb.run(5)
    assert state(gb) == BONUS
    assert tilemap_row(gb, 11, 0, 20) == [v["bar_map"][40 + 2 + (i & 15)] for i in range(20)], "counter row"
    assert tilemap_row(gb, LAYOUT["FLOOR_ROW"], 0, 20) == [v["floor_tile"]] * 20
    walls = set(v["bar_map"][2:17] + v["bar_map"][22:37])
    assert set(tilemap_row(gb, 6, 0, 20)) <= walls


@pytest.mark.parametrize("group", range(len(GROUPS)), ids=[GROUP_THEME[g] for g in GROUPS])
def test_venue_golden(gb, group):
    """A few seconds into each level: patrons walking in, a drink sliding, the bartender at the tap."""
    at_theme(gb, group)
    gb.run(150)
    gb.hold("a")
    gb.run(20)
    gb.release("a")
    gb.run(20)
    assert [p for p in patrons(gb)], "patrons on screen"
    check_golden(gb, f"venue_{THEMES[group]}")


# ---- the saloon keg, taller (owner 2026-10-09, again with the per-venue taps 2026-10-12) --------------------------------
def _bar_rows(theme):
    path = ROOT / "assets" / "approved" / "venues" / f"{theme}_bar.txt"
    return [r for r in path.read_text().splitlines() if r and not r.startswith(";")]


def _saloon_bar_rows():
    return _bar_rows("saloon")


def _spout_tip(theme):
    """Bar row of the lowest art pixel over the glass columns (x 136-143) above the counter (rows 0-15)."""
    rows = _bar_rows(theme)
    return max((y for y in range(16) for x in range(136, 144) if rows[y][x] != "."), default=-1)


def test_the_saloon_keg_is_22_px_tall():
    """Columns 18-19: the keg fills rows 2-23 of the 24-px bar (was 1-23: 1 px shorter, owner 2026-10-17, so 2 clear rows
    keep it off the next bar's keg); bar + floor still clear of the title's text ids, the bar palette only."""
    rows = _saloon_bar_rows()
    keg = [y for y in range(24) if set(rows[y][144:160]) != {"."}]
    assert keg == list(range(2, 24)), keg
    v = venue("saloon")
    assert v["bar_n"] <= VENUES["pool"] - VENUES["title_text_slot"]
    assert all(v["bar_attr"][r * 20 + c] == BGPAL_BAR for r in range(3) for c in (18, 19))


def test_the_saloon_has_a_sheriff_star():
    """The owner's own keg (2026-10-18, drawn in LibreSprite): a five-point star in light pixels, x 149-153, rows 11-14."""
    rows = _saloon_bar_rows()
    assert [rows[y][149:154] for y in range(11, 15)] == ["##-##", "-----", "#---#", "#-#-#"]


@pytest.mark.parametrize("theme", THEMES)
def test_the_spout_tip_ends_above_the_empty_glass(theme):
    """Per venue (src/mugs.c fill_dy): the glass held under the spout hangs FILL_DY below a sliding mug; its rim is
    sprite row 5 and its foam head (full frame) row 4, so the lowest spout pixel over the glass must be above bar row
    MUG_DY + FILL_DY + 4. A step of at most 3 px when the filled mug launches (4 px is borderline)."""
    from conftest import FILL_DY
    dy = FILL_DY[THEMES.index(theme)]
    assert 0 <= dy <= 3, "the launch handoff stays a 3 px step at most"
    tip = _spout_tip(theme)
    assert 0 <= tip < LAYOUT["MUG_DY"] + dy + 4, (theme, tip, dy)
    # how much stream shows above the glass is tests/test_keg_bartender.py: 2-3 px in every venue


@pytest.mark.parametrize("group", range(len(GROUPS)), ids=[GROUP_THEME[g] for g in GROUPS])
def test_the_fill_glass_hangs_the_venues_drop_below_a_mug(gb, group):
    """In the game, per venue: the glass the bartender holds is FILL_DY[venue] below where the launched mug starts, and
    the launched mug starts at MUG_DY (a step of at most 3 px at launch)."""
    from conftest import FILL_DY, fill_top_y, mug_top_y
    at_theme(gb, group)
    gb.run(30)
    gb.hold("a")
    gb.run(8)
    fill = [s for s in gb.visible_sprites() if OBJ_MUG_FILL <= s["tile"] < OBJ_MUG_FILL + 8]
    assert len(fill) == 1 and fill[0]["y"] - 16 == fill_top_y(0, group) == mug_top_y(0) + FILL_DY[group]
    gb.run(14)
    gb.release("a")
    gb.run(2)
    mug = [gb.oam()[5]]
    assert mug and mug[0]["y"] - 16 == mug_top_y(0), "the launched mug starts at the sliding height"


def test_the_saloon_spout_still_lines_up_with_the_fill(gb):
    """The spout hangs over the glass the bartender fills at SPOUT_X, its tip clear of the glass (see the per-venue
    test above); the keg tiles are on screen on every bar."""
    rows = _saloon_bar_rows()
    spout = {x for y in range(16) for x in range(128, 144) if rows[y][x] != "."}
    assert spout and min(x for x in spout if x >= GAME["SPOUT_X"]) >= GAME["SPOUT_X"]
    v = venue("saloon")
    for b in range(4):
        for r in range(2):
            assert tilemap_row(gb, bar_top_row(b) + r, 17, 3) == v["bar_map"][r * 20 + 17:r * 20 + 20], (b, r)
    gb.write("intro_timer", 255)
    gb.hold("a")
    gb.run(6)
    fill = [s for s in gb.visible_sprites() if OBJ_MUG_FILL <= s["tile"] < OBJ_MUG_FILL + 8]
    gb.release("a")
    assert len(fill) == 1 and fill[0]["x"] - 8 == GAME["SPOUT_X"] and gb.mem("bartender_x") == GAME["TAP_X"]


# ---- the breaking drink, generated from the venue's own drink (crash fix option 1, owner 2026-10-10) ----------------
@pytest.mark.parametrize("theme", ["saloon", "factory"])
def test_crash_golden(gb, theme):
    """The fall frame at both ends: a full drink off the left end (full palette), an empty off the right end (empty
    palette, mirrored), both on their side at the sliding drink's scale; one breaking glass = 2 OAM entries."""
    from test_patrons import clear_patrons, freeze, inject_mug
    g = [GROUP_THEME[n] for n in GROUPS].index(theme)
    at_theme(gb, g)
    gb.run(30)
    freeze(gb)
    clear_patrons(gb)
    gb.run(2)
    inject_mug(gb, 1, GAME["GLASS_X"], 3)
    inject_mug(gb, 2, GAME["GLASS_X_RIGHT"], 3)
    gb.run(11)                                       # mug_timer 8..15: the fall frame
    glass = OBJ_MUG + art("MUG_TILE_COUNT")
    tiles = sorted(logical_tile(s["tile"]) - glass for s in gb.visible_sprites()
                   if 0 <= logical_tile(s["tile"]) - glass < art("GLASS_TILE_COUNT"))
    assert tiles == [art("GLASS_FALL_FULL"), art("GLASS_FALL_FULL") + 2, art("GLASS_FALL_EMPTY"), art("GLASS_FALL_EMPTY") + 2]
    check_golden(gb, f"crash_{theme}")
