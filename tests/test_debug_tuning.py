# The debug menu's TUNING page (src/debug.c tune_knob[]; owner 2026-11-03): MODE > TUNING lists single-number knobs to change while testing, session only.
# First knobs: COINS (tip_chance: OFF, 1 IN 2 .. 1 IN 16, ALWAYS; the default 1 IN 8 = TIP_CHANCE_DEFAULT) and GUS ALWAYS (ON / OFF: GUS, the Saloon's look 2,
# always tips in ARCADE and STORY). The values live in debug_from_title's bits 3-7 (0 = the default), so boss.c can put the tuned chance back after a fight.
import pytest
from conftest import GAME, gesture, release_gesture, unlock_debug
from test_boss import ROW, SPOUT_X, to_fight, frames, until
from test_flow import GS_STORY, LIFE_LOST, state
from test_debug import DEBUG, PLAYING, goto, line, row_text, tap
from test_pocket import arcade
from test_story import try_again
from test_tip2 import serve_look

pytestmark = pytest.mark.timeout(300)

COINS = ["OFF", "1 IN 2", "1 IN 3", "1 IN 4", "1 IN 5", "1 IN 6", "1 IN 8", "1 IN 10", "1 IN 12", "1 IN 16", "ALWAYS"]
CHANCE = [0, 128, 85, 64, 51, 43, 32, 26, 21, 16, 255]
DEFAULT = GAME["TIP_CHANCE_DEFAULT"]
SP_FAIL = 4


def open_tuning(gb):
    """The menu (any mode) on its TUNING page: MODE one step Left from the first, or Right until it shows."""
    unlock_debug(gb)
    gesture(gb)
    release_gesture(gb)
    gb.run(3)
    goto(gb, 0)
    for _ in range(8):
        if line(gb, 2)[1] == "TUNING":
            return
        tap(gb, "right")
    raise AssertionError("no TUNING page")


def set_coins(gb, label):
    goto(gb, 1)
    for _ in range(len(COINS)):
        if line(gb, 4)[1] == label:
            return
        tap(gb, "right")
    raise AssertionError(label)


def tune(gb, label=None, gus=None):
    open_tuning(gb)
    if label:
        set_coins(gb, label)
    if gus is not None:
        goto(gb, 2)
        while line(gb, 6)[1] != gus:
            tap(gb, "right")
    gb.press("b", 2)
    gb.run(30)


def test_the_page_lists_its_knobs_with_the_defaults_and_nothing_starts(boot):
    open_tuning(boot)
    assert line(boot, 2) == ("MODE", "TUNING")
    assert line(boot, 4) == ("COINS", "1 IN 8") and line(boot, 6) == ("GUS ALWAYS", "ON")
    assert row_text(boot, 15).strip() == "THIS SESSION ONLY"
    assert boot.mem("debug_from_title") & 0xF8 == 0, "the defaults are all zero bits: a power-on needs no setting"
    boot.press("a", 2)                                   # (A closes it: nothing to start)
    boot.run(30)
    assert boot.mem("debug_menu_open") == 0 and boot.mem("game_state") == 0


def test_coins_steps_both_ways_wraps_and_sets_tip_chance_at_once(boot):
    open_tuning(boot)
    goto(boot, 1)
    for k in range(7, 11):
        tap(boot, "right")
        assert line(boot, 4) == ("COINS", COINS[k]) and boot.mem("tip_chance") == CHANCE[k]
    tap(boot, "right")                                   # ALWAYS wraps to OFF
    assert line(boot, 4)[1] == "OFF" and boot.mem("tip_chance") == 0
    tap(boot, "left")
    assert line(boot, 4)[1] == "ALWAYS" and boot.mem("tip_chance") == 255
    for k in range(9, -1, -1):
        tap(boot, "left")
        assert line(boot, 4)[1] == COINS[k] and boot.mem("tip_chance") == CHANCE[k]


def test_the_values_survive_closing_and_reopening_and_a_mode_switch(boot):
    open_tuning(boot)
    set_coins(boot, "1 IN 3")
    goto(boot, 2)
    tap(boot, "right")
    assert line(boot, 6) == ("GUS ALWAYS", "OFF")
    goto(boot, 0)
    tap(boot, "right")                                   # (TUNING -> STRESS or LEVEL: any other mode)
    tap(boot, "left")
    assert line(boot, 4) == ("COINS", "1 IN 3") and line(boot, 6) == ("GUS ALWAYS", "OFF")
    boot.press("b", 2)
    boot.run(30)
    open_tuning(boot)
    assert line(boot, 4) == ("COINS", "1 IN 3") and line(boot, 6) == ("GUS ALWAYS", "OFF")
    assert boot.mem("tip_chance") == 85


def test_the_other_modes_lines_are_unchanged_and_the_start_bit_stays(boot):
    open_tuning(boot)
    set_coins(boot, "ALWAYS")
    goto(boot, 0)
    while line(boot, 2)[1] != "LEVEL":
        tap(boot, "right")
    assert [line(boot, y)[0] for y in (2, 4, 6, 8)] == ["MODE", "LEVEL", "BARS", "BAR CHANGE"]
    assert boot.mem("debug_from_title") & 1 == 1, "opened on the title"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_coins_always_and_off_decide_a_served_patron_s_tip(model):
    gb = arcade(model)
    try:
        gb.write("tip_chance", 0)
        tune(gb, "ALWAYS")
        assert gb.mem("game_state") == PLAYING and gb.mem("tip_chance") == 255
        serve_look(gb, 0, 90, 0)
        assert gb.mem16("tip_timer") > 0, "ALWAYS: a regular tipped, with no tip_chance poked"
        gb.write("tip_timer", 0)
        gb.write(gb.addr("tip_timer") + 1, 0)
        tune(gb, "OFF")
        assert gb.mem("tip_chance") == 0
        serve_look(gb, 1, 70, 0)
        assert gb.mem16("tip_timer") == 0, "OFF: no coin"
    finally:
        gb.stop()


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_gus_always_off_makes_him_roll_like_the_others(model):
    gb = arcade(model)
    try:
        tune(gb, "1 IN 16", gus="OFF")
        assert gb.mem("tip_chance") == 16
        serve_look(gb, 0, 90, 2, rng=77)
        assert gb.mem16("tip_timer") == 0, "GUS rolled (77 >= 16): no tip"
        tune(gb, gus="ON")
        serve_look(gb, 1, 70, 2, rng=77)
        assert gb.mem16("tip_timer") > 0, "GUS ALWAYS ON: he tips with no roll"
    finally:
        gb.stop()


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_tuned_chance_comes_back_after_a_boss_fight_ends(model):
    """boss_begin sets tip_chance 0 and boss_set(BOSS_NONE) restores it: here a lost fight (TRY AGAIN restarts the venue; boss_on goes)."""
    with to_fight(model) as gb:
        assert gb.mem("boss_on") == 1 and gb.mem("tip_chance") == 0
        gb.write("debug_from_title", (3 ^ 6) << 3)       # COINS 1 IN 4 (list index 3, stored xor 6, in bits 3-6): as a tuned fight would find it
        frames(gb, 2)
        gb.write("lives", 1)
        gb.write("boss_x", SPOUT_X - ROW["width"] - 8)
        gb.write("intro_timer", 0)
        until(gb, lambda: state(gb) == LIFE_LOST, ROW["step"] + 2)
        until(gb, lambda: state(gb) == GS_STORY, 200)
        try_again(gb)
        assert gb.mem("boss_on") == 0 and gb.mem("tip_chance") == 64, "the tuned 1 IN 4, not the default"
        assert gb.mem("debug_from_title") >> 3 == 3 ^ 6


def test_an_untouched_page_leaves_the_default_after_a_fight(model="cgb"):
    with to_fight(model) as gb:
        assert gb.mem("debug_from_title") == 0
        gb.write("lives", 1)
        gb.write("boss_x", SPOUT_X - ROW["width"] - 8)
        gb.write("intro_timer", 0)
        until(gb, lambda: state(gb) == LIFE_LOST, ROW["step"] + 2)
        until(gb, lambda: state(gb) == GS_STORY, 200)
        try_again(gb)
        assert gb.mem("tip_chance") == DEFAULT


def test_the_page_picture(boot):
    """A new golden: the TUNING page with COINS on 1 IN 3 and GUS ALWAYS OFF (the cursor on the GUS line)."""
    from conftest import check_golden
    open_tuning(boot)
    set_coins(boot, "1 IN 3")
    goto(boot, 2)
    tap(boot, "right")
    boot.run(4)
    check_golden(boot, "debug_tuning")
