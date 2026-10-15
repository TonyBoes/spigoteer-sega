# E9: a boss round opens as a normal shift (the warm-up) and the boss enters after it; F12: the bartender's trick (CLASSIC's
# end-of-level antics, src/antics.c) in Story after the Happy hour. src/boss.c (BS_WARM, entrance_start, boss_pre, fight_start),
# src/main_cold.c enter_level_clear. Boss tests of the fights themselves start the fight at once (test_story.to_goal: boss_hook 4).
import re

import pytest
from boss_common import (BP_WALK, BS_WALK, BS_WALKIN, BS_WARM, art, assert_body, body, fight, frames, hud, meter_tiles, mugs,
                         play, row, still_regulars, throw, until)
from conftest import ROOT, venue
from test_flow import GS_GOAL, LEVEL_CLEAR, PLAYING, run_until, state
from test_story import banner_text, centred, to_chapter, to_shift, win

pytestmark = pytest.mark.timeout(400)

SRC = (ROOT / "src" / "boss.c").read_text()
WARM_FRAMES, WARM_AVOID, WARM_WAIT, WALK_STEP = (int(re.search(rf"#define {n}\s+(\d+)", SRC).group(1)) for n in (
    "WARM_FRAMES", "WARM_AVOID", "WARM_WAIT", "WALK_STEP"))
BOSS_NONE = 255
C = 0                                   # the saloon: Big Tex has no entrance of his own (the fallback walk-in)
R = row(C)
A = art("big_tex")
INTRO = 90


def special_t(gb):
    return gb.mem("boss_special_t") | gb.mem(gb.addr("boss_special_t") + 1) << 8


def put_special_t(gb, v):
    gb.write("boss_special_t", v & 255)
    gb.write(gb.addr("boss_special_t") + 1, v >> 8)


def patrons_on(gb, b):
    st, pb = gb.read("patron_state", 16), gb.read("patron_bar", 16)
    return [p for p in range(16) if st[p] and pb[p] & 3 == b]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_round_opens_as_a_normal_shift(model):
    """The fight's first frames: BS_WARM, his bar is a plain bar (boss_bar BOSS_NONE, no body on it, no topper, no HUD meter), the
    warm-up counts WARM_FRAMES down only once the intro is over, and regulars come to EVERY bar, his included."""
    with fight(model, C, warm=True) as gb:
        assert gb.mem("boss_on") == 1 and gb.mem("boss_state") == BS_WARM and gb.mem("boss_bar") == BOSS_NONE
        assert special_t(gb) == WARM_FRAMES
        frames(gb, 5)
        assert special_t(gb) == WARM_FRAMES, "not counted during the intro"
        play(gb)
        frames(gb, 30)
        assert WARM_FRAMES - 32 <= special_t(gb) < WARM_FRAMES
        top, bottom = body(gb, R)
        wall = venue("saloon")["bar_map"]
        assert top == wall[:20] and bottom == wall[20:40], "no body on his bar"
        assert gb.oam()[28]["y"] == 0, "no topper"
        assert hud(gb) != meter_tiles(R["meter"], R["meter"]), "no meter yet"
        for i in range(8):                           # (the arrivals are drawn at random: send the next ones to his bar)
            gb.write(gb.addr("pat_buf") + i, R["bar"])
        gb.write("pat_bar", R["bar"])
        for _ in range(1500):
            frames(gb, 1)
            if patrons_on(gb, R["bar"]) or state(gb) != PLAYING:
                break
        assert gb.mem("boss_state") == BS_WARM and patrons_on(gb, R["bar"]), "a regular on his bar, as on any"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_warm_up_ends_with_the_entrance_and_then_the_boss_rules_apply(model):
    """Time up: the fallback entrance (BS_WALKIN: Tex has none of his own): the bar freezes (intro_timer held), mugs are cleared,
    his body comes in from the left edge column by column, steps on to x 16, then the banner (his first line) stays through the
    intro's beat and the fight starts: meter, HUD face, hands rules; a full mug is only caught from then on."""
    with fight(model, C, warm=True) as gb:
        play(gb)
        still_regulars(gb)
        throw(gb, 2, 100)
        put_special_t(gb, 1)
        gb.write("boss_t", 255)                      # (no grace wait: the bar and the mugs are not what this test is about)
        until(gb, lambda: gb.mem("boss_state") != BS_WARM, 5)
        assert gb.mem("boss_state") == BS_WALKIN and gb.mem("boss_bar") == R["bar"] and gb.mem("intro_timer") >= INTRO - 1
        assert not mugs(gb), "the mugs are cleared"
        assert gb.mem("boss_lim") == 0 and gb.mem("boss_hp") == R["meter"]
        cols_seen = []
        wall = venue("saloon")["bar_map"]
        for _ in range(WALK_STEP * 12):
            frames(gb, 1)
            if gb.mem("boss_state") != BS_WALKIN:
                break
            assert gb.mem("intro_timer") >= INTRO - 2, "the bar holds still while he walks in"
            top, _ = body(gb, R)
            cols_seen.append(sum(1 for k in range(20) if top[k] != wall[k]))
        assert gb.mem("boss_state") == BS_WALK and gb.mem("boss_x") == R["x"]
        assert cols_seen[0] <= 1 and max(cols_seen) >= R["width"] // 8, cols_seen
        assert all(b - a <= 1 or a == 0 for a, b in zip(cols_seen, cols_seen[1:])), "one column at a time"
        frames(gb, 2)
        assert gb.mem("intro_timer") >= INTRO - 3, "the intro's beat follows the landing"
        assert hud(gb) == meter_tiles(R["meter"], R["meter"]), "his meter and face are up"
        assert_body(gb, C, A, R["x"], BP_WALK)
        until(gb, lambda: gb.mem("intro_timer") == 0, INTRO)
        frames(gb, 3)
        assert gb.mem("overlay_on") == 0, "the banner goes with the first move"
        throw(gb, R["bar"], 100)
        until(gb, lambda: gb.mem("boss_hits") == 1, 120)
        assert gb.mem("boss_hp") == R["meter"] - 1 and gb.mem("boss_hold") >= 1


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_entrance_waits_for_his_bar_to_empty(model):
    """A regular standing on his bar when the time is up: the entrance waits (BS_WARM) up to WARM_WAIT frames, then he enters and the
    straggler is gone."""
    with fight(model, C, warm=True) as gb:
        play(gb)
        for i in range(8):
            gb.write(gb.addr("pat_buf") + i, R["bar"])
        gb.write("pat_bar", R["bar"])
        for _ in range(3000):
            frames(gb, 1)
            if patrons_on(gb, R["bar"]) or state(gb) != PLAYING:
                break
        assert patrons_on(gb, R["bar"])
        still_regulars(gb)
        put_special_t(gb, 1)
        gb.write("boss_t", 0)
        frames(gb, WARM_WAIT - 20)
        assert gb.mem("boss_state") == BS_WARM and patrons_on(gb, R["bar"]), "he waits"
        until(gb, lambda: gb.mem("boss_state") != BS_WARM, 40)
        assert not patrons_on(gb, R["bar"]), "his bar is empty when he comes in"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_no_new_regular_for_his_bar_in_the_last_seconds(model):
    with fight(model, C, warm=True) as gb:
        play(gb)
        put_special_t(gb, WARM_AVOID + 3)
        frames(gb, 6)
        assert special_t(gb) < WARM_AVOID
        pb = gb.read("pat_buf", 8)
        assert all(b & 3 != R["bar"] for b in pb), pb


@pytest.mark.parametrize("model", ["cgb"])
def test_boss_rush_has_no_warm_up(model):
    """BOSS RUSH: the entrance starts on the first frame (his bar free of regulars, he is hidden until he walks in)."""
    from test_rush import BUILT, booted, into_fight, tap, to_list, v7_image
    ram0 = v7_image([("ABC", 500)], story=2, step=1, story_tbl=[("STO", 900)])
    with booted(model, ram0) as gb:
        to_list(gb)
        for _ in range(BUILT.index(C)):
            tap(gb, "down")
        tap(gb, "a")
        into_fight(gb, entered=False)
        until(gb, lambda: gb.mem("boss_state") != BS_WARM, 5)
        assert gb.mem("boss_state") == BS_WALKIN and gb.mem("boss_bar") == R["bar"]
        assert not patrons_on(gb, R["bar"])
        until(gb, lambda: gb.mem("boss_state") == BS_WALK, 80)
        assert gb.mem("boss_x") == R["x"] and gb.mem("boss_hp") == R["meter"]


# ---- F12: the trick in Story after the Happy hour -------------------------------------------------------------------
def antics_t(gb):
    return gb.mem("antics_t") | gb.mem(gb.addr("antics_t") + 1) << 8


def clear_of(gb, c, k):
    win(gb, c, k)
    run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 20)
    gb.run(3)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_no_trick_after_the_opening_shift(model):
    with to_chapter(model, 0) as gb:
        clear_of(gb, 0, 0)
        gb.run(20)
        assert gb.mem("state_timer") < 100 and antics_t(gb) == 0
        run_until(gb, lambda: state(gb) == GS_GOAL, 250)


@pytest.mark.parametrize("k", [1, 2])
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_trick_plays_after_the_happy_hour_and_the_last_call(model, k):
    with to_shift(model, 0, k) as gb:
        clear_of(gb, 0, k)
        gb.run(20)
        assert gb.mem("state_timer") == 255 and 20 <= antics_t(gb) <= 30, "the trick runs"
        gb.run(200)
        assert antics_t(gb) >= 200 and state(gb) == LEVEL_CLEAR
        run_until(gb, lambda: state(gb) != LEVEL_CLEAR, 400)
        assert antics_t(gb) >= 300
        run_until(gb, lambda: state(gb) in (GS_GOAL, 13) and gb.mem("state_timer") == 0, 400)   # the next step (GS_MINI: the slot after the Happy hour)
        assert gb.mem("state_timer") == 0
