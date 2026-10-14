# The can shake-up's three levels in Practice (owner 2026-10-14): BONUS > MINI GAMES > CAN SHAKE-UP. Level 1 at the old first-shake-up pace,
# each further level faster (swap frames 30, 22, 14; 7, 9, 11 swaps), level 3 with a distraction (a bartender strolls along behind the cans
# during the swaps, OAM 30-33). 1000 points a level: 1, 2, 3 cleared = bronze, silver, gold (src/mg.h BONUS_SHAKE_*); a wrong pick ends the run
# and keeps what was earned. ARCADE and CLASSIC play their one round as before (tests/test_bonus.py, test_classic_mode.py).
import pytest
from conftest import check_golden, hold_stage_anim
from test_bonus import enter_bonus, lines, to_phase
from test_flow import run_until
from test_mg import GS_MINI, MG_PRACTICE, mg_enter, text
from test_mg_bonus import medal_of  # noqa: F401
from test_mg_list import MEDAL_BRONZE, MEDAL_GOLD, MEDAL_NONE, MEDAL_SILVER, MG_SHAKEUP
from test_scores import booted

PH_SHOW, PH_SHAKE, PH_SWAP, PH_CHOOSE, PH_RESULT = range(5)
WALK_OAM = range(30, 34)
MEDALS = [MEDAL_NONE, MEDAL_BRONZE, MEDAL_SILVER, MEDAL_GOLD]


def start(gb):
    mg_enter(gb, MG_SHAKEUP, MG_PRACTICE)
    gb.run(3)
    gb.press("a", 2)               # (the card seen: the banner, A skips it)
    gb.run(2)


def pick(gb, right):
    run_until(gb, lambda: gb.mem("bonus_phase") == PH_CHOOSE, 2000)
    calm = gb.mem("bonus_calm")
    gb.write("bonus_cursor", calm if right else (calm + 1) % 6)
    gb.run(2)
    gb.press("a", 2)
    assert gb.mem("bonus_won") == (1 if right else 0)


def next_level(gb, lv):
    run_until(gb, lambda: gb.mem("bonus_round") == lv and gb.mem("bonus_phase") == PH_SHOW, 300)


def walker(gb):
    o = gb.oam()
    return [o[i] for i in WALK_OAM if 0 < o[i]["y"] < 160]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("cleared", [0, 1, 2, 3])
def test_levels_cleared_give_the_medal_and_a_miss_keeps_it(model, cleared):
    """Clear `cleared` levels, then miss (or after level 3 the round ends by itself): none / bronze / silver / gold, the score 1000 a level."""
    with booted(model) as gb:
        mg_enter(gb, MG_SHAKEUP, MG_PRACTICE)
        gb.press("a", 2)
        for lv in range(1, cleared + 1):
            assert gb.mem("bonus_round") == lv
            pick(gb, True)
            if lv < 3:
                next_level(gb, lv + 1)
                assert text(gb, 4) == "LEVEL %d" % (lv + 1)
        if cleared < 3:
            pick(gb, False)
        run_until(gb, lambda: gb.mem("overlay_on") == 1, 400)
        gb.run(3)
        assert gb.mem("mg_medal") == MEDALS[cleared] and gb.mem16("mg_score") == 1000 * cleared
        assert text(gb, 2, True, x0=4) == "SCORE %d" % (1000 * cleared)
        assert max(lines(gb)) <= 10


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_each_level_swaps_faster_and_more_often(model):
    """Swap frames 30, 22, 14 and 7, 9, 11 swaps (measured: the frames the first swap is in flight)."""
    with booted(model) as gb:
        mg_enter(gb, MG_SHAKEUP, MG_PRACTICE)
        gb.press("a", 2)
        for lv, (dur, total) in enumerate([(30, 7), (22, 9), (14, 11)], 1):
            run_until(gb, lambda: gb.mem("bonus_phase") == PH_SWAP, 600)
            assert gb.mem("bonus_swap_dur") == dur and gb.mem("bonus_swaps_total") == total
            run_until(gb, lambda: gb.mem("bonus_moving") == 1, 100)
            n = 0
            while gb.mem("bonus_moving"):
                gb.run(1)
                n += 1
            assert n in (dur, dur + 1), (lv, n)
            pick(gb, True)
            if lv < 3:
                next_level(gb, lv + 1)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_distraction_walks_in_level_3_only(model):
    """Levels 1 and 2: nothing in OAM 30-33 during the swaps. Level 3: a bartender walks left to right behind the cans (OAM index above
    the cans'), <= 10 sprites a line all the way, gone before the choice."""
    with booted(model) as gb:
        hold_stage_anim(gb)
        mg_enter(gb, MG_SHAKEUP, MG_PRACTICE)
        gb.press("a", 2)
        for lv in (1, 2, 3):
            xs, top = [], 0
            run_until(gb, lambda: gb.mem("bonus_phase") == PH_SWAP, 600)
            while gb.mem("bonus_phase") == PH_SWAP:
                gb.run(1)
                w = walker(gb)
                if lv < 3:
                    assert not w
                elif w:
                    assert len(w) == 4
                    xs.append(w[0]["x"])
                    assert max(lines(gb)) <= 10
            if lv == 3:
                assert len(xs) > 40 and xs == sorted(xs) and xs[0] < 24 and xs[-1] > 100, xs[:3]
                assert not walker(gb)
                pick(gb, True)
            else:
                pick(gb, True)
                next_level(gb, lv + 1)


def test_arcade_and_classic_keep_their_single_round(gb):
    """ARCADE round 3 (the shake-up's n = 1 pace: 30 frames, 7 swaps) shows no walker; a win there ends the round (no second level)."""

    enter_bonus(gb, 2, rounds_before=0)
    assert gb.mem("bonus_swap_dur") == 30 and gb.mem("bonus_swaps_total") == 7
    to_phase(gb, PH_SWAP)
    for _ in range(80):
        gb.run(1)
        assert not walker(gb)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_screenshots(model):
    """Level 3 mid-shuffle with the walker, and the gold result (x3 previews: out/ by hand)."""
    with booted(model) as gb:
        hold_stage_anim(gb)
        mg_enter(gb, MG_SHAKEUP, MG_PRACTICE)
        gb.press("a", 2)
        for lv in (1, 2):
            pick(gb, True)
            next_level(gb, lv + 1)
        run_until(gb, lambda: gb.mem("bonus_phase") == PH_SWAP and gb.mem("bonus_swaps_done") >= 4 and walker(gb), 800)
        check_golden(gb, "shakeup_level3_walker")
        pick(gb, True)
        run_until(gb, lambda: gb.mem("overlay_on") == 1, 400)
        gb.run(60)
        check_golden(gb, "shakeup_gold_result")
