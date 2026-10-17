# Owner 2026-10-17, three requests about the bosses (src/boss.c, assets/art/boss/tag.txt, docs/minigames_bosses.md 10):
#   1. "Get rid of the drink arrow on the bosses": the status tag (an empty mug with an arrow down at his hand; a full mug with a cross) is
#      gone, in every boss, both models. Every frame of these tests is checked at <= 10 sprites a line (boss_common.frames).
#   2. "The mugs they drink from should look more like the drink served to them": while a boss gulps, OAM 29 draws the mug the player served
#      (mugs.c spr_full_t / spr_full_p: the venue's own drink art and palette) over his hand column, with his sway; his GULP pose has no mug.
#   3. The capacity indicator: how many more drinks he can hold, in three looks (-DBOSS_CAP_UI=1 mug row, 2 belly gauge, 3 HUD counter; the
#      default look is src/boss.h's). The tests read it back from OAM / the HUD after every drink, for the default build and, when
#      out/test_roms/spigoteer-bosscap<n>-unlocked.gb exist (make bosscap), for all three looks.
import re
import sys
from pathlib import Path

import pytest
import test_sound
from boss_common import (BS_GULP, GAME, ROOT, THEMES, ART_H, block_empties, fight, frames, play, row, still_regulars, throw, until)

sys.path.insert(0, str(ROOT / "tools"))
from gen_art import blocks, rgb15, tile_bytes  # noqa: E402

pytestmark = pytest.mark.timeout(400)

NAMES = ["big_tex", "mascot", "sasquatch", "critic", "yeti", "prototype", "duke", "sumo", "leo", "mothership"]
SUMO = 7
OAM_HAND = GAME["OAM_DANCERS"] + 1
OAM_CAP = 40                                   # the indicator's entries: 39, 38, 37
OBJ_CAP = 124
BOSS_H = (ROOT / "src" / "boss.h").read_text()
BOSS_C = (ROOT / "src" / "boss.c").read_text()
DEFAULT_UI = int(re.search(r"#define BOSS_CAP_UI (\d)", BOSS_H).group(1))
HAND_BASE = [int(x) for x in re.search(r"hand_base\[BOSS_COUNT\] = \{([^}]*)\}", BOSS_C).group(1).split(",")]
GLYPH_X = int(re.search(r"#define TILE_GLYPH_X (\d+)", ART_H).group(1))
GLYPH_0 = int(re.search(r"#define TILE_GLYPH_0 (\d+)", ART_H).group(1))
ROMS = ROOT / "out" / "test_roms"
BOSS_BANK = (ROOT / "assets" / "art" / "boss")

# the old status tag's art (assets/art/boss/tag.txt before this change): READY, an empty mug with an arrow down; BUSY, a full mug with a cross
OLD_TAG = [
    ["######..", "#----#..", "#----###", "#----#.#", "#----#.#", "#----###", "#----#..", "######..",
     "...##...", "...##...", "...##...", ".######.", "..####..", "...##...", "........", "........"],
    ["######..", "#----#..", "#++++###", "#++++#.#", "#++++#.#", "#++++###", "#++++#..", "######..",
     "##....##", ".##..##.", "..####..", ".##..##.", "##....##", "........", "........", "........"],
]


def bar_oam_y(c):
    return (5 + 3 * row(c)["bar"]) * 8 + 16


def play_in(model, c):
    gb = fight(model, c)
    still_regulars(gb)
    play(gb)
    block_empties(gb)
    frames(gb, 3)
    return gb


def vram_tiles(gb):
    mem = bytes(gb.read(0x8000, 0x1000))
    return {mem[i:i + 16] for i in range(0, 0x1000, 16)}


# ---- 1. the arrow is gone ------------------------------------------------------------------------------------------
def test_the_tag_art_file_has_no_arrow_any_more():
    names = [n for n, _ in blocks(BOSS_ART_TAG, named=True)]
    assert "READY" not in names and "BUSY" not in names
    assert not re.search(r"TAG_READY|TAG_BUSY|TAG_RETURN|BEV_TAG", BOSS_H + BOSS_C)


BOSS_ART_TAG = BOSS_BANK / "tag.txt"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("c", range(10))
def test_the_drink_arrow_is_gone(model, c):
    """Ready (hands free) and busy (hands full), mid-fight and in a gulp: neither old tag tile is anywhere in sprite VRAM, and nothing is
    drawn over his hand column but the indicator's own look."""
    old = {bytes(tile_bytes(f, 0, 0) + tile_bytes(f, 0, 8)) for f in OLD_TAG}
    r = row(c)
    with play_in(model, c) as gb:
        for hold in (0, r["hands"]):
            gb.write("boss_hold", hold)
            frames(gb, 3)
            assert not old & vram_tiles(gb), f"the arrow / cross tag tiles are in VRAM (hold {hold})"
            hat = gb.oam()[GAME["OAM_DANCERS"]]
            for e in gb.oam():
                if e["y"] and e["y"] == hat["y"] and e["x"] == gb.mem("boss_x") + r["width"]:
                    assert DEFAULT_UI != 1 or e["tile"] in (OBJ_CAP, OBJ_CAP + 2), e     # (the mug row's first icon sits there: the one allowed)
        gb.write("boss_hold", 0)
        throw(gb, r["bar"], gb.mem("boss_lim") + 3, perfect=True)
        if c != SUMO:                                       # (the Sumo is hit, he does not gulp)
            until(gb, lambda: gb.mem("boss_state") == BS_GULP, 60)
        frames(gb, 12)
        assert not old & vram_tiles(gb)


# ---- 2. the hand mug is the served drink ---------------------------------------------------------------------------
def served_mug(c):
    """The venue's full mug: its 8x16 tile bytes and CGB palette (assets/approved/venues/<theme>_drink*)."""
    t = THEMES[c]
    f = blocks(ROOT / "assets" / "approved" / "venues" / f"{t}_drink.txt")[0][1]
    pal = __import__("json").loads((ROOT / "assets" / "approved" / "venues" / f"{t}_drink_pal.json").read_text())["full"]["hex"]
    return bytes(tile_bytes(f, 0, 0) + tile_bytes(f, 0, 8)), [0] + rgb15(pal)


def swapped(b):
    """The DMG copy of a sprite tile: the two bit planes of every row swapped (src/lift.c swap_copy)."""
    return bytes(b[i ^ 1] for i in range(len(b)))


def catch_one(gb, c, perfect=False):
    r = row(c)
    throw(gb, r["bar"], gb.mem("boss_lim") + 3, perfect=perfect)


def gulp_pose(gb, want=(2, 8)):
    """Until he gulps in the common pose (boss_pose 2: GULP, 8: BP_SWAY) with the push-back over."""
    until(gb, lambda: gb.mem("boss_state") == BS_GULP and gb.mem("boss_push") == 0 and gb.mem("boss_pose") & 15 in want, 300)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("c", [c for c in range(10) if c != SUMO])
def test_the_hand_mug_is_the_drink_that_was_served(model, c):
    """Per venue boss: no mug in his hand until he drinks; then OAM 29 is the sliding mug's own tile and palette (the venue's drink art),
    its bottom at his hand_base row over his hand column, moving 2 px with the sway beat; his GULP pose itself has no mug of its own."""
    r = row(c)
    mug, pal = served_mug(c)
    with play_in(model, c) as gb:
        assert gb.oam()[OAM_HAND]["y"] == 0, "nothing in his hand before he drinks"
        catch_one(gb, c, perfect=True)
        gulp_pose(gb, (2,))
        frames(gb, 2)
        o = gb.oam()[OAM_HAND]
        assert o["y"] == bar_oam_y(c) + HAND_BASE[c] - 14, o
        assert o["tile"] == gb.mem("spr_full_t") and o["flags"] == gb.mem("spr_full_p"), "the sliding mug's tile and attributes"
        data = bytes(gb.read(0x8000 + o["tile"] * 16, 32))
        if model == "cgb":
            assert o["flags"] & 7 == 1 and data == mug, "the venue's drink art, its palette"
            from test_venues import cgb_palette
            assert cgb_palette(gb, 1, True) == pal
        else:
            assert o["flags"] == 0 and data == swapped(mug), "DMG: the mug's own copy (bit planes swapped, OBP0)"
        # the whole gulp: the mug moves exactly as the topper does (the sway beat), and is gone when he is not drinking
        seen, away = set(), 0
        while gb.mem("boss_state") == BS_GULP:
            frames(gb, 1)
            o, hat = gb.oam()[OAM_HAND], gb.oam()[GAME["OAM_DANCERS"]]
            if o["y"]:
                assert o["tile"] == gb.mem("spr_full_t") and o["y"] == bar_oam_y(c) + HAND_BASE[c] - 14
                dx = o["x"] - (gb.mem("boss_x") + r["width"])
                if hat["y"]:
                    assert dx == hat["x"] - (gb.mem("boss_x") + r["hat"] + 8), "it moves with his body, as the topper"
                seen.add(dx)
            else:
                away += 1
        assert 0 in seen
        if r["sway"]:
            assert seen == {0, -2 if r["sway"] == 2 else 2}, seen
        frames(gb, 2)
        assert gb.oam()[OAM_HAND]["y"] == 0, "the mug goes when the gulp is over"


def test_every_venue_serves_a_different_mug():
    mugs = {served_mug(c)[0] for c in range(10)}
    assert len(mugs) == 10


def test_the_sumo_drinks_nothing():
    """The teahouse's boss is hit by the cup (no gulp): no hand mug is ever drawn for him."""
    assert HAND_BASE[SUMO] == 255 and len(HAND_BASE) == 10


# ---- 3. the capacity indicator -------------------------------------------------------------------------------------
def read_cap(gb, ui, hands=3):
    """(free, total) as the screen shows them: the first `hands` entries from OAM 39 down (looks 1 and 2: ROOM tile 124 / TAKEN 126; total =
    the entries drawn), or look 3's HUD counter "xN" in HUD columns 10-11 (total: None). (None, 0): no indicator."""
    from test_flow import tilemap_row
    oam = gb.oam()
    if ui == 3:
        t = tilemap_row(gb, 0, 10, 2)
        if t[0] != GLYPH_X:
            assert oam[OAM_CAP - 1]["y"] == 0, "no counter text, no mug"
            return None, 0
        o = oam[OAM_CAP - 1]
        assert (o["y"], o["x"], o["tile"]) == (16, 80, OBJ_CAP), o
        return t[1] - GLYPH_0, None
    shown = [oam[OAM_CAP - 1 - k] for k in range(hands)]
    on = [e["y"] != 0 for e in shown]
    assert on == sorted(on, reverse=True), "filled from OAM 39 down"
    cells = [e for e in shown if e["y"]]
    assert all(e["tile"] in (OBJ_CAP, OBJ_CAP + 2) for e in cells), cells
    if not cells:
        return None, 0
    return sum(e["tile"] == OBJ_CAP for e in cells), len(cells)


def check_geometry(gb, ui, c, total):
    r = row(c)
    oam = gb.oam()
    x, hat = gb.mem("boss_x"), oam[GAME["OAM_DANCERS"]]
    for k in range(total):
        e = oam[OAM_CAP - 1 - k]
        if ui == 1:
            assert (e["y"], e["x"]) == (bar_oam_y(c) - 8, x + r["width"] + 8 * k), (k, e)       # over his hand column, left to right
        elif ui == 2:
            assert (e["y"], e["x"]) == (bar_oam_y(c) - 4 * k, x), (k, e)                              # to his left, from his body's bottom up


def cap_cases(ui):
    """Venue bosses with a drink limit, shown: (c, hands). The Sumo has no limit and shows nothing."""
    return [(c, row(c)["hands"]) for c in range(10) if c != SUMO]


def poke_check(model, c, ui):
    r = row(c)
    hands = r["hands"]
    with play_in(model, c) as gb:
        for taken in range(hands + 1):
            gb.write("boss_hold", taken)
            frames(gb, 3)
            free, total = read_cap(gb, ui, hands)
            assert free == hands - taken and total in (hands, None), (NAMES[c], taken, free, total)
            if ui != 3:
                check_geometry(gb, ui, c, hands)
        gb.write("boss_hold", 0)
        gb.write("boss_hook", 3)                           # beaten: the outro: no indicator
        frames(gb, 4)
        assert read_cap(gb, ui, hands) == (None, 0)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("c", [c for c in range(10) if c != SUMO])
def test_the_indicator_shows_the_free_hands(model, c):
    poke_check(model, c, DEFAULT_UI)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_sumo_has_no_indicator(model):
    with play_in(model, SUMO) as gb:
        for hold in (0, 1, 2):
            gb.write("boss_hold", hold)
            frames(gb, 3)
            assert read_cap(gb, DEFAULT_UI, 3) == (None, 0)


def eat_empties(gb):
    """The bartender's job: an empty that left him is caught at once (an empty that reached the tap end would cost a life and reset the fight)."""
    st = list(gb.read("mug_state", 20))
    for i, v in enumerate(st):
        if v == 2:
            gb.write(gb.addr("mug_state") + i, 0)
            st[i] = 0
    gb.write("mugs_live", sum(1 for v in st if v))


def drinks_check(model, c, ui, perfect=False):
    """Real drinks: after each catch the indicator shows the hands still free; empties going out give them back."""
    r = row(c)
    hands = r["hands"]
    with play_in(model, c) as gb:
        assert read_cap(gb, ui, hands)[0] == hands
        for n in range(1, hands + 1):
            until(gb, lambda: gb.mem("boss_push") == 0, 60)
            catch_one(gb, c, perfect)
            until(gb, lambda: gb.mem("boss_hits") == n, 120)
            frames(gb, 3)
            free, total = read_cap(gb, ui, hands)
            assert free == hands - n and total in (hands, None), (NAMES[c], n, free, total)
            assert gb.mem("boss_hold") == n
        if c != 3:
            assert gb.mem("boss_lim") == 0, "hands full: a drink would slide past"   # (the Critic's queue keeps his limit open: BEV_ROOM says full)
        gb.write("next_arrival", 0)                         # his empties may go again, one by one
        gb.write(gb.addr("next_arrival") + 1, 0)
        for k in range(hands - 1, -1, -1):
            until(gb, lambda: eat_empties(gb) or gb.mem("boss_hold") == k, 600)
            frames(gb, 3)
            assert read_cap(gb, ui, hands)[0] == hands - k, (NAMES[c], k)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("c", [0, 4, 6])
def test_the_indicator_follows_every_drink_and_every_empty(model, c):
    drinks_check(model, c, DEFAULT_UI)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_indicator_follows_the_critics_perfect_drink(model):
    drinks_check(model, 3, DEFAULT_UI, perfect=True)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_indicator_in_the_boss_rush(model):
    """BOSS RUSH plays the same engine: the indicator is up (Big Tex, 3 free) once the fight is on."""
    from test_flow import GS_GOAL, run_until, state
    from test_rush import into_fight, tap, to_list
    from test_scores import booted, v7_image
    with booted(model, v7_image([("ABC", 500)], story=2, step=1, story_tbl=[("STO", 900)])) as gb:
        to_list(gb)
        tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_GOAL, 60)
        gb.run(3)
        into_fight(gb)
        gb.write("patron_speed", 0)
        gb.write("hurry_speed", 0)
        until(gb, lambda: gb.mem("intro_timer") == 0, 400)
        block_empties(gb)
        frames(gb, 3)
        hands = row(gb.mem("boss_id"))["hands"]
        free, total = read_cap(gb, DEFAULT_UI, hands)
        assert free == hands and total in (hands, None)
        gb.write("boss_hold", 1)
        frames(gb, 3)
        assert read_cap(gb, DEFAULT_UI, hands)[0] == hands - 1


# ---- the three looks, each from its own debug build (make bosscap) --------------------------------------------------
@pytest.fixture(params=[1, 2, 3])
def look(request, monkeypatch):
    rom = ROMS / f"spigoteer-bosscap{request.param}-unlocked.gb"
    if not rom.is_file():
        pytest.skip(f"{rom.name} is not built (make bosscap)")
    monkeypatch.setattr(test_sound, "ROM", rom)           # (every helper boots through test_sound.make_rom)
    return request.param


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("c", [0, 3, 9])
def test_each_look_shows_the_free_hands(look, model, c):
    poke_check(model, c, look)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_each_look_follows_big_texs_drinks(look, model):
    drinks_check(model, 0, look)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_each_look_follows_the_critics_perfect_drink(look, model):
    drinks_check(model, 3, look, perfect=True)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_each_look_leaves_no_arrow_and_a_venue_mug(look, model):
    old = {bytes(tile_bytes(f, 0, 0) + tile_bytes(f, 0, 8)) for f in OLD_TAG}
    mug, _ = served_mug(0)
    with play_in(model, 0) as gb:
        assert not old & vram_tiles(gb)
        catch_one(gb, 0)
        gulp_pose(gb, (2,))
        o = gb.oam()[OAM_HAND]
        assert o["tile"] == gb.mem("spr_full_t") and bytes(gb.read(0x8000 + o["tile"] * 16, 32)) in (mug, swapped(mug))
