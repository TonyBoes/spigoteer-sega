# M9: themed venues. Each level loads the venue of its theme (theme index = patron group): stage, bar, floor, the
# drink in place of the beer mug, the show performers, and on CGB their palettes. Expected tile ids, maps and tile
# data come from build/venues.json (tools/gen_art.py), which is cut from assets/approved/venues/.
import re

import pytest
from conftest import GAME, LAYOUT, ROOT, THEMES, VENUES, bar_counter_row, bar_top_row, check_golden, logical_tile, venue
from test_art import GROUPS, goto_group
from test_bonus import enter_bonus, pick
from test_flow import BONUS, PLAYING, run_until, state, tilemap_row
from test_patrons import DRINKING, MAX_P, hold_mug, patrons, put, set_patron

pytestmark = pytest.mark.timeout(120)

ART_H = (ROOT / "build" / "art.h").read_text()


def art(name):
    return int(re.search(rf"#define {name} (\d+)", ART_H).group(1))


OBJ_MUG = art("BARTENDER_TILE_COUNT")
OBJ_MUG_FILL = OBJ_MUG + art("MUG_TILE_COUNT") + art("GLASS_TILE_COUNT")
OBJ_MUG_DRINK = OBJ_MUG_FILL + art("MUG_FILL_TILE_COUNT")
OBJ_DANCER = OBJ_MUG_DRINK + art("MUG_DRINK_TILE_COUNT") + art("COIN_TILE_COUNT")
SHOW_FRAMES = 704
BGPAL_PATRON, BGPAL_BAR = 2, 0
OBJPAL_MUG_FULL, OBJPAL_MUG_EMPTY, OBJPAL_DANCER = 1, 2, 5
# theme of each patron group, as the owner assigned them
GROUP_THEME = {"cowboys": "saloon", "sports": "sports", "lumberjacks": "lodge", "chefs": "bistro", "divers": "igloo",
               "robots": "factory", "ninjas": "teahouse", "aliens": "space", "zoo": "zoo"}


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


def test_theme_order_follows_the_patron_groups():
    assert THEMES == [GROUP_THEME[g] for g in GROUPS]
    assert re.search(r"// venue order: (.*)", ART_H).group(1).split(", ") == THEMES
    assert THEMES[0] == "saloon", "the generic look is theme 0"


def test_theme_tile_pool_holds_every_theme_and_the_bg_budget_holds():
    """Option A (owner 2026-10-10): BG ids 0..35 are one pool; the stage takes ids from 0 up, the bar + floor pack at
    the top (36 - bar_n ..), never below 20: the title draws the saloon's bar while its menu text overwrites 0..19."""
    pool, text = VENUES["pool"], VENUES["title_text_slot"]
    assert (pool, text) == (art("VENUE_POOL"), art("TITLE_TEXT_SLOT")) == (36, 20)
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


@pytest.mark.parametrize("group", range(9), ids=[GROUP_THEME[g] for g in GROUPS])
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
    assert obj_vram(gb, OBJ_DANCER, 32) == bytes(v["show"])
    if gb.model_name == "cgb":
        for r in range(4):
            assert attr_row(gb, first + r) == v["stage_attr"][r * 20:r * 20 + 20]
        for b in range(4):
            assert attr_row(gb, bar_counter_row(b)) == v["bar_attr"][40:60]
            assert attr_row(gb, bar_top_row(b) + 1)[17:20] == v["bar_attr"][37:40], "spout and keg"
        assert cgb_palette(gb, 5) == v["pal"][0] and cgb_palette(gb, 6) == v["pal"][1]
        assert cgb_palette(gb, BGPAL_BAR) == v["pal"][2] and cgb_palette(gb, 7) == v["pal"][3]
        assert cgb_palette(gb, OBJPAL_MUG_FULL, obj=True)[1:] == v["pal"][4][1:]
        assert cgb_palette(gb, OBJPAL_MUG_EMPTY, obj=True)[1:] == v["pal"][5][1:]
        assert cgb_palette(gb, OBJPAL_DANCER, obj=True)[1:] == v["pal"][6][1:]
    else:
        assert gb.read(0xFF47, 1)[0] == 0xE4, "DMG: the fixed grey ramp (the venue art is luminance-ordered)"


@pytest.mark.parametrize("group", range(9), ids=[GROUP_THEME[g] for g in GROUPS])
def test_patron_palettes_take_the_venue_wall_colour(gb, group):
    v = at_theme(gb, group)
    if gb.model_name != "cgb":
        pytest.skip("CGB palettes")
    wall = v["pal"][2][0]
    assert cgb_palette(gb, BGPAL_BAR)[0] == wall
    for k in range(3):
        assert cgb_palette(gb, BGPAL_PATRON + k)[0] == wall, f"patron palette {k}: colour 0 is the wall"


@pytest.mark.parametrize("group", [0, 1, 4, 7], ids=["saloon", "sports", "igloo", "space"])
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


@pytest.mark.parametrize("group", range(9), ids=[GROUP_THEME[g] for g in GROUPS])
def test_the_show_uses_the_venue_performers(gb, group):
    v = at_theme(gb, group)
    w16(gb, "show_timer", SHOW_FRAMES)
    gb.run(40)
    ds = [s for s in gb.visible_sprites() if OBJ_DANCER <= s["tile"] < OBJ_DANCER + 32]
    assert len(ds) == 12, "three performers of 4 entries"
    assert obj_vram(gb, OBJ_DANCER, 32) == bytes(v["show"])


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


@pytest.mark.parametrize("group", range(9), ids=[GROUP_THEME[g] for g in GROUPS])
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


# ---- the saloon keg, 4 px taller (owner 2026-10-09) --------------------------------------------------------------------
def _saloon_bar_rows():
    path = ROOT / "assets" / "approved" / "venues" / "saloon_bar.txt"
    return [r for r in path.read_text().splitlines() if r and not r.startswith(";")]


def test_the_saloon_keg_is_20_px_tall():
    """Columns 18-19: the keg fills rows 4-23 of the 24-px bar (was 8-23), its top 4 px clear of the bar above's
    falling glass (3 lines); bar + floor still clear of the title's text ids, the bar palette only."""
    rows = _saloon_bar_rows()
    keg = [y for y in range(24) if set(rows[y][144:160]) != {"."}]
    assert keg == list(range(4, 24)), keg
    v = venue("saloon")
    assert v["bar_n"] <= VENUES["pool"] - VENUES["title_text_slot"]
    assert all(v["bar_attr"][r * 20 + c] == BGPAL_BAR for r in range(3) for c in (18, 19))


def test_the_saloon_spout_still_lines_up_with_the_fill(gb):
    """The spout is unchanged: the pipe (rows 10-12) runs from the keg into column 17 and the nozzle (rows 13-15) hangs
    inside column 17, over the glass the bartender fills at SPOUT_X; the keg tiles are on screen on every bar."""
    rows = _saloon_bar_rows()
    nozzle = {x for y in (13, 14, 15) for x in range(128, 144) if rows[y][x] != "."}
    assert nozzle and min(nozzle) >= GAME["SPOUT_X"] and max(nozzle) < GAME["SPOUT_X"] + 8, sorted(nozzle)
    assert all(rows[y][136] != "." and rows[y][144] != "." for y in (10, 11, 12)), "the pipe joins the keg"
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
    assert min(nozzle) >= fill[0]["x"] - 8 and max(nozzle) < fill[0]["x"], "the nozzle is over the glass"
