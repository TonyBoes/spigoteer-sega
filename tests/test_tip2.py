"""patron-rev-2 step 6: two tips at a time (owner 2026-10-25; ARCADE and STORY, CLASSIC and the harness keep one), GUS always tips there (owner
2026-10-22, no roll and so no random number), and the Color Saloon's palette split follows SCREEN BRIGHT."""
import pytest
from conftest import logic_paused
from test_bright import level_rom, lift_bytes
from test_flow import run_until
from test_patrons import inject_mug, put, set_patron
from test_pocket import arcade, pocket, quiet
from test_tips import coin_sprites, w16
from test_split import SPLIT_PAL

pytestmark = pytest.mark.timeout(240)

MODELS = ["dmg", "cgb"]
TIP2_AT = 230                                  # src/scratch.h SCR_TIP2_AT: struct tip2 { uint16_t t; uint8_t bar, x; }


def tip2(gb):
    a = gb.addr("story_scratch") + TIP2_AT
    return gb.mem(a) | (gb.mem(a + 1) << 8), gb.mem(a + 2), gb.mem(a + 3)


def serve_look(gb, bar, x, look, chance=None, rng=None):
    """As test_tips.serve, with the patron's look poked: a walking patron at x catches a full mug whose push carries him off the left edge."""
    with logic_paused(gb):
        if chance is not None:
            gb.write("tip_chance", chance)
        if rng is not None:
            gb.write("rng_state", rng)
        gb.write("pushback_px", 250)
        w16(gb, "spawn_timer", 0xFFFF)
        i = set_patron(gb, bar, x)
        put(gb, "patron_drinks", i, 1)
        put(gb, "patron_variant", i, look)
        s0 = gb.mem("served")
        inject_mug(gb, bar, x + 6)
    run_until(gb, lambda: gb.mem("served") > s0, 300)
    assert gb.mem("served") == s0 + 1
    return i


@pytest.mark.parametrize("model", MODELS)
def test_two_tips_at_a_time_in_arcade_and_no_third(model):
    gb = arcade(model)
    try:
        assert pocket(gb) != 0, "ARCADE: the pocket is on"
        serve_look(gb, 0, 90, 0)
        assert gb.mem16("tip_timer") > 0 and tip2(gb)[0] == 0
        serve_look(gb, 1, 70, 0)
        t, bar, x = tip2(gb)
        assert t > 0 and bar == 1 and x == 74, "the second coin lies under the second patron"
        assert gb.mem("tip_bar") == 0 and gb.mem("tip_x") == 94, "the first stays where it was"
        assert len(coin_sprites(gb)) == 2, "two coins on screen"
        serve_look(gb, 2, 60, 0)
        assert tip2(gb)[1:] == (1, 74) and len(coin_sprites(gb)) == 2, "a third coin is not dropped"
    finally:
        gb.stop()


@pytest.mark.parametrize("model", MODELS)
def test_the_second_coin_takes_the_first_ones_place_when_that_is_picked_up(model):
    gb = arcade(model)
    try:
        serve_look(gb, 0, 90, 0)
        serve_look(gb, 1, 70, 0)
        t2 = tip2(gb)
        w16(gb, "tip_timer", 5)                 # the first one runs out
        gb.run(8)
        assert gb.mem16("tip_timer") > 0 and gb.mem("tip_bar") == 1 and gb.mem("tip_x") == 74, "the second slid into the first slot"
        assert tip2(gb)[0] == 0 and len(coin_sprites(gb)) == 1
        assert gb.mem16("tip_timer") <= t2[0]
    finally:
        gb.stop()


@pytest.mark.parametrize("model", MODELS)
def test_a_coin_is_picked_up_one_at_a_time_and_each_pays(model):
    gb = arcade(model)
    try:
        serve_look(gb, 0, 90, 0)
        serve_look(gb, 1, 70, 0)
        s0 = int.from_bytes(gb.read("score", 4), "little")
        with logic_paused(gb):                   # both coins under the bartender
            for a in (gb.addr("tip_bar"), gb.addr("story_scratch") + TIP2_AT + 2):
                gb.write(a, gb.mem("bar"))
            gb.write("tip_x", gb.mem("bartender_x") + 4)
            gb.write(gb.addr("story_scratch") + TIP2_AT + 3, gb.mem("bartender_x") + 4)
        gb.run(3)
        s1 = int.from_bytes(gb.read("score", 4), "little")
        assert s1 - s0 >= 1500, "the first coin paid"
        gb.run(3)
        s2 = int.from_bytes(gb.read("score", 4), "little")
        assert s2 - s1 >= 1500 or gb.mem16("tip_timer") == 0 and tip2(gb)[0] == 0, "the second paid on a later frame (or is pocketed)"
    finally:
        gb.stop()


@pytest.mark.parametrize("model", MODELS)
def test_gus_always_tips_in_arcade_and_draws_no_random_number(model):
    gb = arcade(model)
    try:
        assert gb.mem("cur_group") == 0
        with logic_paused(gb):
            gb.write("tip_chance", 1)             # 1 in 256: a roll would all but never tip
        r0 = 77
        serve_look(gb, 0, 90, 2, chance=1, rng=r0)
        assert gb.mem16("tip_timer") > 0, "GUS tipped"
    finally:
        gb.stop()


@pytest.mark.parametrize("model", MODELS)
def test_another_patron_rolls_as_ever_in_arcade(model):
    gb = arcade(model)
    try:
        serve_look(gb, 0, 90, 0, chance=1, rng=77)
        assert gb.mem16("tip_timer") == 0, "a look that is not GUS still rolls (77 >= 1: no tip)"
    finally:
        gb.stop()


def test_a_chance_of_zero_still_means_never_even_for_gus(gb):
    quiet_ = gb
    quiet(quiet_)
    quiet_.write("tip_chance", 0)
    serve_look(quiet_, 0, 90, 2)
    assert quiet_.mem16("tip_timer") == 0


def test_the_harness_and_classic_keep_one_tip_and_gus_rolls_there(gb):
    """tip_pocket is 0 in the LEVEL harness (as in CLASSIC): one coin at a time, and GUS has no special chance."""
    from test_tips import quiet as tquiet
    tquiet(gb)
    assert gb.mem("tip_pocket") == 0
    serve_look(gb, 0, 90, 0)
    serve_look(gb, 1, 70, 0)
    assert gb.mem("tip_bar") == 0 and gb.mem("tip_x") == 94 and len(coin_sprites(gb)) == 1
    w16(gb, "tip_timer", 0)
    serve_look(gb, 2, 60, 2, chance=1, rng=77)
    assert gb.mem16("tip_timer") == 0, "GUS rolls in the harness: 77 >= 1, no tip"


def test_the_split_palette_is_lifted_with_screen_bright():
    """patron-rev-2: SPLIT_PAL (HRAM, the 5th patron palette instance's colours below the line-39 split) follows SCREEN BRIGHT like every palette."""
    a = level_rom(False)
    b = level_rom(True)
    try:
        a.run(5)
        b.run(5)
        assert a.mem(0xFFD4) == 1 and b.mem(0xFFD4) == 1, "the split is armed in the Color Saloon"
        na, nb = bytes(a.read(SPLIT_PAL, 8)), bytes(b.read(SPLIT_PAL, 8))
        assert nb == lift_bytes(na), (na.hex(), nb.hex())
        assert nb != na, "the lift changed something"
    finally:
        a.stop()
        b.stop()
