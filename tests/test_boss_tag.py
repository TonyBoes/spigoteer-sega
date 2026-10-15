# Batch E1 (owner 2026-10-14 playtest), every boss, both models: (1) the drinking shake: while a boss gulps, his body
# alternates GULP / WALK every SWAY_FRAMES like the patrons' sway beat and his topper shifts their 2 px; (2) slower
# drinking: every row's gulp is >= 1.3x what it was (the Sumo's stays 0: he has no gulp); (3) the status tag: one 8x16
# sprite (OAM 29, OBJ 124-127) above his hand column: READY (a hand is free), BUSY (hands full), shaking BUSY (the
# Critic sends a drink back), gone in the intro and the outro. Every frame is checked at <= 10 sprites a line.
import re

import pytest
from boss_common import (BP_GULP, BP_WALK, BS_GULP, GAME, ROOT, THEMES, art, assert_body, block_empties, fight, frames,
                         play, row, still_regulars, throw, until)
from conftest import clear_regulars
from test_flow import PLAYING, state

pytestmark = pytest.mark.timeout(300)

NAMES = ["big_tex", "mascot", "sasquatch", "critic", "yeti", "prototype", "duke", "sumo", "leo", "mothership"]
OLD_GULP = [40, 24, 8, 60, 30, 20, 20, 0, 30, 24]
OAM_TOPPER = GAME["OAM_DANCERS"]
OAM_TAG = OAM_TOPPER + 1
OBJ_TAG = 124
SWAY = int(re.search(r"#define SWAY_FRAMES\s+(\d+)", (ROOT / "src" / "game.h").read_text()).group(1))
TAGS = [int(x, 16) for x in re.findall(r"0x([0-9A-F]{2})", (ROOT / "build" / "boss_tag_art.h").read_text())]
TAG_READY, TAG_BUSY = 0, 2


def test_every_gulp_is_at_least_30_percent_longer():
    for c, old in enumerate(OLD_GULP):
        g = row(c)["gulp"]
        assert (g == 0) if old == 0 else g * 100 >= old * 130, (c, old, g)


def test_the_tag_art_is_two_8x16_tiles_pairs():
    assert len(TAGS) == 64 and any(TAGS[:32]) and any(TAGS[32:])


def play_in(model, c):
    gb = fight(model, c)
    still_regulars(gb)
    play(gb)
    block_empties(gb)
    return gb


def tag(gb):
    return gb.oam()[OAM_TAG]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("c", range(10))
def test_the_drinking_shake(model, c):
    """He gulps (boss_state GULP, no push-back, no special pose): GULP while (boss_t / SWAY) is even, WALK while odd;
    the topper sits 2 px right on the odd beats, as a patron's sway."""
    r, a = row(c), art(NAMES[c])
    with play_in(model, c) as gb:
        if r["gulp"] <= SWAY:
            pytest.skip("no second beat in his gulp")
        gb.write("boss_xpose", 0)
        gb.write("boss_hold", 0)
        gb.write("boss_state", BS_GULP)
        gb.write("boss_t", 0)
        seen = set()
        while gb.mem("boss_state") == BS_GULP and gb.mem("boss_t") < r["gulp"] - 1:
            frames(gb, 1)
            t = gb.mem("boss_t")
            if gb.mem("boss_state") != BS_GULP:
                break
            beat = (t // SWAY) & 1
            x = gb.mem("boss_x")
            assert_body(gb, c, a, x, BP_WALK if beat else BP_GULP)
            assert gb.oam()[OAM_TOPPER]["x"] == x + r["hat"] + 8 + (2 if beat else 0), (t, beat)
            seen.add(beat)
        assert seen == {0, 1}, "both beats happened"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("c", range(10))
def test_the_tag_ready_busy_and_gone(model, c):
    r = row(c)
    gb = fight(model, c)
    still_regulars(gb)
    with gb:
        for _ in range(200):                                     # (the intro: no tag; Duke's entrance too)
            if gb.mem("intro_timer") == 0 and state(gb) == PLAYING:
                break
            frames(gb, 1)
            assert tag(gb)["y"] == 0, "no tag in the intro"
        block_empties(gb)
        frames(gb, 3)
        o, hat = tag(gb), gb.oam()[OAM_TOPPER]
        assert gb.mem("boss_lim") != 0
        assert (o["y"], o["x"], o["tile"]) == (hat["y"], gb.mem("boss_x") + r["width"], OBJ_TAG), "READY above his hand column"
        assert bytes(gb.read(0x8000 + OBJ_TAG * 16, 64)) == bytes(TAGS), "the tag's tiles are in VRAM"
        assert o["tile"] - OBJ_TAG == TAG_READY
        if model == "cgb":
            assert o["flags"] & 7 == 7                            # OBJ palette 7: his own colours
        gb.write("boss_hold", gb.mem("boss_cap"))                # hands full: a drink would slide past
        frames(gb, 2)
        if c == 7:                                               # the Sumo has no drink limit (E5): always READY (his BEV_TAG)
            assert tag(gb)["tile"] == OBJ_TAG + TAG_READY and tag(gb)["y"] == hat["y"]
        else:
            assert gb.mem("boss_lim") == 0
            assert tag(gb)["tile"] == OBJ_TAG + TAG_BUSY and tag(gb)["y"] == hat["y"]
        gb.write("boss_hold", 0)
        frames(gb, 2)
        assert tag(gb)["tile"] == OBJ_TAG + TAG_READY
        gb.write("boss_hook", 3)                                 # beaten: the outro, no tag
        frames(gb, 3)
        assert tag(gb)["y"] == 0


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_critic_waving_a_drink_back_shakes_the_tag(model):
    """The Critic's busy states (tasting, a held glass, a drink waiting to go back) are the shaking BUSY tag; free, READY."""
    with play_in(model, 3) as gb:
        frames(gb, 3)
        assert tag(gb)["tile"] == OBJ_TAG + TAG_READY
        base = gb.mem("boss_x") + row(3)["width"]
        gb.write("boss_hold", 1)                                 # (a held glass: anything is sent back)
        frames(gb, 2)
        xs = []
        for _ in range(24):
            frames(gb, 1)
            o = tag(gb)
            assert o["tile"] == OBJ_TAG + TAG_BUSY
            xs.append(o["x"] - base)
        assert set(xs) == {-2, 2}, xs
        gb.write("boss_hold", 0)
        frames(gb, 2)
        assert tag(gb)["tile"] == OBJ_TAG + TAG_READY and tag(gb)["x"] == base
        throw(gb, row(3)["bar"], 72)                             # a sloppy drink reaches him: tasted, then sent back
        until(gb, lambda: gb.mem("crit_taste") > 0, 40)
        frames(gb, 2)
        assert tag(gb)["tile"] == OBJ_TAG + TAG_BUSY
        assert {tag(gb)["x"] - gb.mem("boss_x") - row(3)["width"]} <= {-2, 2}


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_tag_in_a_real_catch(model):
    """Big Tex has 3 hands: the tag stays READY after one catch (a hand is free), BUSY at the third."""
    r = row(0)
    with play_in(model, 0) as gb:
        for n in (1, 2, 3):
            gb.write("boss_x", r["x"])
            throw(gb, r["bar"], r["x"] + r["width"] - 4 + 8)
            until(gb, lambda: gb.mem("boss_hits") == n, 20)
            frames(gb, 3)
            assert tag(gb)["tile"] == OBJ_TAG + (TAG_BUSY if n == 3 else TAG_READY), n


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_tag_and_the_shake_in_the_boss_rush(model):
    """BOSS RUSH plays the same engine: the tag (READY) is up once the fight is on, and a gulp shakes the topper."""
    from test_rush import into_fight, tap, to_list
    from test_flow import GS_GOAL, run_until
    from test_scores import booted, v7_image
    with booted(model, v7_image([("ABC", 500)], story=2, step=1, story_tbl=[("STO", 900)])) as gb:
        to_list(gb)
        tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_GOAL, 60)
        gb.run(3)
        into_fight(gb)
        gb.write("patron_speed", 0)
        gb.write("hurry_speed", 0)
        until(gb, lambda: gb.mem("intro_timer") == 0, 400)     # (Big Tex's entrance, E8, comes first)
        block_empties(gb)
        frames(gb, 3)
        assert tag(gb)["y"] != 0 and tag(gb)["tile"] == OBJ_TAG + TAG_READY
        gb.write("boss_state", BS_GULP)
        gb.write("boss_t", SWAY)
        frames(gb, 1)
        hat = gb.oam()[OAM_TOPPER]["x"]
        assert hat == gb.mem("boss_x") + row(gb.mem("boss_id"))["hat"] + 8 + 2
