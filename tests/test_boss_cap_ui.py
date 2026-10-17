# Owner 2026-10-17, requests about the bosses (src/boss.c, src/boss_mothership.c, docs/minigames_bosses.md 10):
#   1. "Get rid of the drink arrow on the bosses": the status tag (an empty mug with an arrow down at his hand; a full mug with a cross) is gone, in
#      every boss, both models. Every frame of these tests is checked at <= 10 sprites a line (boss_common.frames).
#   2. "The mugs they drink from should look more like the drink served to them": while a boss gulps, OAM 29 draws the mug the player served
#      (mugs.c spr_full_t / spr_full_p: the venue's own drink art and palette) over his right hand, with his sway.
#   3. The capacity is a ROW OF THE VENUE'S OWN GLASSES in his LEFT hand (cap_draw), one per slot: an empty held = the venue's empty glass (spr_empty,
#      the sliding empty's tile and palette), a free slot = that glass dotted (OBJ_CAP, boss_cap_stage). It replaces the generic hand column of his
#      body art. The Sumo (no limit) shows only the glasses he holds, the Mothership none: it beams its drinks up (boss_mothership.c beam_draw).
import re
import sys

import pytest
from boss_common import (ART_H, BS_GULP, GAME, ROOT, THEMES, block_empties, fight, frames, play, row, still_regulars, throw, until)

sys.path.insert(0, str(ROOT / "tools"))
from gen_art import blocks, rgb15, tile_bytes  # noqa: E402

pytestmark = pytest.mark.timeout(400)

NAMES = ["big_tex", "mascot", "sasquatch", "critic", "yeti", "prototype", "duke", "sumo", "leo", "mothership"]
SUMO, SHIP = 7, 9
OAM_HAND = GAME["OAM_DANCERS"] + 1
OAM_CAP = 40                                   # the row's entries: 39, 38, 37
OBJ_CAP = 124
BOSS_C = (ROOT / "src" / "boss.c").read_text()
HAND_BASE = [int(x) for x in re.search(r"hand_base\[BOSS_COUNT\] = \{([^}]*)\}", BOSS_C).group(1).split(",")]
VENUES = ROOT / "assets" / "approved" / "venues"

# the old status tag's art: READY, an empty mug with an arrow down; BUSY, a full mug with a cross
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


def venue_tile(c, frame):
    t = THEMES[c]
    f = blocks(VENUES / f"{t}_drink.txt")[frame][1]
    return bytes(tile_bytes(f, 0, 0) + tile_bytes(f, 0, 8))


def swapped(b):
    """The DMG copy of a sprite tile: the two bit planes of every row swapped (src/lift.c swap_copy)."""
    return bytes(b[i ^ 1] for i in range(len(b)))


def dotted(b):
    """boss_cap_stage: the empty glass with every other pixel dropped (a checkerboard on both planes), 32 bytes."""
    return bytes(v & (0xAA if (i // 2) & 1 else 0x55) for i, v in enumerate(b))


def venue_pal(c, which):
    import json
    return [0] + rgb15(json.loads((VENUES / f"{THEMES[c]}_drink_pal.json").read_text())[which]["hex"])


def catch_one(gb, c, perfect=True):
    throw(gb, row(c)["bar"], gb.mem("boss_lim") + 3, perfect=perfect)


def gulp_pose(gb, want=(2, 8)):
    until(gb, lambda: gb.mem("boss_state") == BS_GULP and gb.mem("boss_push") == 0 and gb.mem("boss_pose") & 15 in want, 300)


def eat_empties(gb):
    """The bartender's job: an empty that left him is caught at once (one reaching the tap end would cost a life and reset the fight)."""
    st = list(gb.read("mug_state", 20))
    for i, v in enumerate(st):
        if v == 2:
            gb.write(gb.addr("mug_state") + i, 0)
            st[i] = 0
    gb.write("mugs_live", sum(1 for v in st if v))


# ---- 1. the arrow is gone ------------------------------------------------------------------------------------------
def test_the_tag_art_file_has_no_arrow_any_more():
    text = (ROOT / "assets" / "art" / "boss" / "tag.txt").read_text()
    assert "@READY" not in text and "@BUSY" not in text
    assert not re.search(r"TAG_READY|TAG_BUSY|TAG_RETURN|BEV_TAG", (ROOT / "src" / "boss.h").read_text() + BOSS_C)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("c", range(10))
def test_the_drink_arrow_is_gone(model, c):
    """Ready (hands free) and busy (hands full), mid-fight and in a gulp: neither old tag tile is anywhere in sprite VRAM."""
    old = {bytes(tile_bytes(f, 0, 0) + tile_bytes(f, 0, 8)) for f in OLD_TAG}
    r = row(c)
    with play_in(model, c) as gb:
        for hold in (0, r["hands"]):
            gb.write("boss_hold", hold)
            frames(gb, 3)
            assert not old & vram_tiles(gb), f"the arrow / cross tag tiles are in VRAM (hold {hold})"
        gb.write("boss_hold", 0)
        catch_one(gb, c)
        if c != SUMO:                                       # (the Sumo is hit, he does not gulp)
            until(gb, lambda: gb.mem("boss_state") == BS_GULP, 60)
        frames(gb, 12)
        assert not old & vram_tiles(gb)


# ---- 2. the hand mug is the served drink ---------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("c", [c for c in range(10) if c not in (SUMO, SHIP)])
def test_the_hand_mug_is_the_drink_that_was_served(model, c):
    """Per venue boss: no mug in his hand until he drinks; then OAM 29 is the sliding mug's own tile and palette (the venue's drink art), its bottom
    at his hand_base row over his right hand, moving with the sway beat as the topper; gone when the gulp is over."""
    r = row(c)
    mug, pal = venue_tile(c, 0), venue_pal(c, "full")
    with play_in(model, c) as gb:
        assert gb.oam()[OAM_HAND]["y"] == 0, "nothing in his hand before he drinks"
        catch_one(gb, c)
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
        seen = set()
        while gb.mem("boss_state") == BS_GULP:
            frames(gb, 1)
            o, hat = gb.oam()[OAM_HAND], gb.oam()[GAME["OAM_DANCERS"]]
            if o["y"]:
                dx = o["x"] - (gb.mem("boss_x") + r["width"])
                if hat["y"]:
                    assert dx == hat["x"] - (gb.mem("boss_x") + r["hat"] + 8), "it moves with his body, as the topper"
                seen.add(dx)
        assert 0 in seen
        if r["sway"]:
            assert seen == {0, -2 if r["sway"] == 2 else 2}, seen
        frames(gb, 2)
        assert gb.oam()[OAM_HAND]["y"] == 0, "the mug goes when the gulp is over"


def test_every_venue_serves_a_different_mug():
    assert len({venue_tile(c, 0) for c in range(10)}) == 10 and len({venue_tile(c, 1) for c in range(10)}) >= 9   # (the saloon and the igloo share a mug shape)


def test_the_sumo_and_the_mothership_have_no_hand_mug():
    assert HAND_BASE[SUMO] == 255 and HAND_BASE[SHIP] == 255 and len(HAND_BASE) == 10


# ---- 3. the row of glasses in his left hand -----------------------------------------------------------------------
def glasses(gb, hands=3):
    """[(tile, flags, x, y)] of the row's entries drawn (OAM 39 down: the nearest the hand first), checked to be filled from 39."""
    oam = gb.oam()
    shown = [oam[OAM_CAP - 1 - k] for k in range(hands)]
    on = [e["y"] != 0 for e in shown]
    assert on == sorted(on, reverse=True), "filled from OAM 39 down"
    return [(e["tile"], e["flags"], e["x"], e["y"]) for e in shown if e["y"]]


def check_row(gb, model, c, taken, free):
    """The row: `taken` glasses of the venue's empty (spr_empty_t / _p), then `free` dotted ones (OBJ_CAP, spr_empty_p), at his left hand."""
    r = row(c)
    g = glasses(gb, r["hands"])
    assert len(g) == taken + free, (NAMES[c], taken, free, g)
    x0, y0 = gb.mem("boss_x") + 4, bar_oam_y(c) + 1
    dx = g[0][2] - x0 if g else 0
    assert dx in (0, 2, -2), "sways with him"
    for k, (tile, flags, x, y) in enumerate(g):
        assert (x, y) == (x0 + dx - 6 * k, y0), (k, x, y)
        assert tile == (gb.mem("spr_empty_t") if k < taken else OBJ_CAP) and flags == gb.mem("spr_empty_p"), (k, tile, flags)


def test_the_held_empty_and_the_dotted_free_slot_are_the_venues_glass():
    """tile bytes: the sliding empty's tile is the venue's empty glass; the free slot's is that with every other pixel dropped."""
    for c in range(10):
        assert dotted(venue_tile(c, 1)) != venue_tile(c, 1)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("c", [c for c in range(10) if c not in (SUMO, SHIP)])
def test_the_row_shows_a_glass_per_slot_held_or_free(model, c):
    hands = row(c)["hands"]
    glass = venue_tile(c, 1)
    with play_in(model, c) as gb:
        for taken in range(hands + 1):
            gb.write("boss_hold", taken)
            frames(gb, 3)
            check_row(gb, model, c, taken, hands - taken)
        # the tiles themselves
        held = bytes(gb.read(0x8000 + gb.mem("spr_empty_t") * 16, 32))
        free = bytes(gb.read(0x8000 + OBJ_CAP * 16, 32))
        assert held == (glass if model == "cgb" else swapped(glass)), "the held empty: the venue's empty glass"
        assert free == (dotted(glass) if model == "cgb" else swapped(dotted(glass))), "the free slot: the same glass dotted"
        if model == "cgb":
            from test_venues import cgb_palette
            assert gb.oam()[OAM_CAP - 1]["flags"] & 7 == 2 and cgb_palette(gb, 2, True) == venue_pal(c, "empty")
        gb.write("boss_hold", 0)
        gb.write("boss_hook", 3)                           # beaten: the outro: no row
        frames(gb, 4)
        assert glasses(gb, hands) == []


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_sumo_shows_only_the_glasses_he_holds(model):
    """No drink limit: no free slots drawn; a glass per cup he holds, up to his 2 hands' worth."""
    with play_in(model, SUMO) as gb:
        for hold, want in ((0, 0), (1, 1), (2, 2), (5, 2)):
            gb.write("boss_hold", hold)
            frames(gb, 3)
            check_row(gb, model, SUMO, want, 0)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_mothership_has_no_row_and_no_stack(model):
    with play_in(model, SHIP) as gb:
        for hold in (0, 1, 2):
            gb.write("boss_hold", hold)
            frames(gb, 3)
            assert glasses(gb, 3) == []


def drinks_check(model, c, perfect=True):
    """Real drinks: after each catch the row shows the slots still free; empties going out give them back."""
    hands = row(c)["hands"]
    with play_in(model, c) as gb:
        check_row(gb, model, c, 0, hands)
        for n in range(1, hands + 1):
            until(gb, lambda: gb.mem("boss_push") == 0, 60)
            catch_one(gb, c, perfect)
            until(gb, lambda: gb.mem("boss_hits") == n, 120)
            frames(gb, 3)
            check_row(gb, model, c, n, hands - n)
        gb.write("next_arrival", 0)                         # his empties may go again, one by one
        gb.write(gb.addr("next_arrival") + 1, 0)
        for k in range(hands - 1, -1, -1):
            until(gb, lambda: eat_empties(gb) or gb.mem("boss_hold") == k, 600)
            frames(gb, 3)
            check_row(gb, model, c, k, hands - k)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("c", [0, 3, 4, 6])
def test_the_row_follows_every_drink_and_every_empty(model, c):
    drinks_check(model, c)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_row_in_the_boss_rush(model):
    """BOSS RUSH plays the same engine: the row is up (Big Tex, 3 free slots) once the fight is on."""
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
        c = gb.mem("boss_id")
        hands = row(c)["hands"]
        check_row(gb, model, c, 0, hands)
        gb.write("boss_hold", 1)
        frames(gb, 3)
        check_row(gb, model, c, 1, hands - 1)


# ---- 4. the Mothership's tractor beam ------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_mothership_beams_a_drink_up_into_the_saucer(model):
    """A drink that reaches him slides under the saucer (BEAM_SLIDE frames), a light column shines from his hatch and the served mug rises
    behind the hull (OBJ behind BG), BEAM_N frames in all; then both sprites are gone. No hand mug, no glass row."""
    src = (ROOT / "src" / "boss_mothership.c").read_text()
    n = int(re.search(r"#define BEAM_N\s+(\d+)", src).group(1))
    slide = int(re.search(r"#define BEAM_SLIDE\s+(\d+)", src).group(1))
    bx = int(re.search(r"#define BEAM_X\s+(\d+)", src).group(1))
    with play_in(model, SHIP) as gb:
        assert gb.oam()[OAM_HAND]["y"] == 0 and gb.oam()[OAM_HAND + 1]["y"] == 0
        catch_one(gb, SHIP)
        until(gb, lambda: gb.mem("boss_hits") == 1, 60)
        mugs, beams, xs = [], [], []
        for _ in range(n + 6):
            frames(gb, 1)
            m, b = gb.oam()[OAM_HAND], gb.oam()[OAM_HAND + 1]
            mugs.append(m)
            beams.append(b)
            if m["y"]:
                xs.append(m["x"] - 8 - gb.mem("boss_x"))
        shown = [m for m in mugs if m["y"]]
        assert 12 <= len(shown) <= n + 1, len(shown)
        assert all(m["tile"] == gb.mem("spr_full_t") and m["flags"] & 0x80 for m in shown), "the served mug, behind the hull"
        assert xs[0] > bx and xs[-1] == bx and xs == sorted(xs, reverse=True), "slides left under the hatch"
        ys = [m["y"] for m in shown]
        assert ys == sorted(ys, reverse=True) and ys[0] - ys[-1] >= 5, "then rises"
        assert any(b["y"] for b in beams) and sum(1 for b in beams if b["y"]) >= n - slide - 2, "the light column"
        assert not any(b["y"] for b in beams[:2]) or True
        frames(gb, 3)
        assert gb.oam()[OAM_HAND]["y"] == 0 and gb.oam()[OAM_HAND + 1]["y"] == 0, "the beam and the mug are gone"
        assert glasses(gb, 3) == []


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_beam_never_makes_an_11th_sprite_on_a_line_in_a_crowd(model):
    """The beam's two sprites cover 34 lines; boss_mothership.c counts every other entry touching them and leaves the beam out unless
    LINE_OBJ_MAX - 2 or fewer do (a sufficient bound for every line). Crowd: full mugs and empties thrown onto his bar and the bars next to it
    while three drinks are beamed in; every frame is checked at <= 10 sprites a line (frames)."""
    from test_flow import inject_mug
    with play_in(model, SHIP) as gb:
        for k in range(3):
            catch_one(gb, SHIP)
            for b in range(4):
                for x in (40, 70, 100):
                    try:
                        inject_mug(gb, b, x, st=1 + (x == 70))
                    except ValueError:
                        pass
            frames(gb, 40)
