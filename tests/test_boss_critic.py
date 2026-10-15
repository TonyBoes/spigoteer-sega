# docs/minigames_bosses.md 3.6: the Food Critic, the bistro's boss (src/boss_critic.c; art approved 2026-10-11).
# The fight follows the bistro's Last call: his row (32 px, step 110, push 16, gulp 60, hands 1, sip 90, meter 8), the
# perfect pour as his only currency (the story's window, 12 frames long in his fight: releases at pour_t 27..38), a
# sloppy drink tasted (the TASTE pose, 30 frames) and sent back as a MUG_RETURN the bartender catches like an empty,
# drinks waved back while he is busy (never an unseen break), the fair schedule for returns and empties alike, a
# missed return breaking at the right end, and the win. Every frame here is checked at <= 10 sprites a line.
import pytest
from boss_common import (BP_GULP, BP_HAPPY, BP_WALK, BS_GULP, BS_OUTRO, BS_SPECIAL, EMPTY, FULL, RETURN, SP_OUTRO,
                         TAP_X, art, arrivals_ok, assert_body, block_empties, check_start, fight, frames, hud,
                         meter_tiles, mugs, play, row, still_regulars, throw, to_bar, until)
from conftest import clear_regulars, GAME, ROOT, check_golden
from test_flow import GS_STORY, LEVEL_CLEAR, LIFE_LOST, PLAYING, run_until, state
from test_pour import drop_mugs, first_launch, hold_release
from test_story import banner_text, centred, post, settle, to_goal

pytestmark = pytest.mark.timeout(300)

C = 3                                   # the bistro
R = row(C)
A = art("critic")
B = R["bar"]
BP_TASTE = 5
SRC = (ROOT / "src" / "boss_critic.c").read_text()
CRIT_WIN, CRIT_TASTE, CRIT_QUEUE = (int(__import__("re").search(rf"#define {n}\s+(\d+)", SRC).group(1))
                                    for n in ("CRIT_WIN", "CRIT_TASTE", "CRIT_QUEUE"))
WIN0 = GAME["POUR_WIN_START"]
FILL_FRAMES = 16


def test_his_row_and_art():
    """Spec 3.2 / 3.6's numbers, the banner lines of spec 7, his approved art with the TASTE pose (extra pose 5), the
    window and the taste in his file."""
    assert {k: R[k] for k in ("width", "x", "bar", "step", "push", "gulp", "hands", "sip", "meter", "hat")} == dict(
        width=32, x=16, bar=1, step=110, push=16, gulp=84, hands=1, sip=90, meter=8, hat=9)
    assert (R["line1"], R["line2"]) == ("THE CRITIC DINES", "PERFECT POURS ONLY")
    assert A["poses"] == ["WALK", "STOMP", "GULP", "WINCE", "HAPPY", "TASTE"] and A["cols"] == 4
    assert (CRIT_WIN, CRIT_TASTE, CRIT_QUEUE) == (12, 30, 3)
    assert "; Art: approved design" in (ROOT / "assets/art/boss/critic.txt").read_text()
    assert not (ROOT / "assets/art/approved/boss_critic.txt").exists()


def quiet(gb):
    """In play, nobody else moving, the bartender at his bar's tap."""
    still_regulars(gb)
    play(gb)
    to_bar(gb, B)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_fight_follows_the_last_call(model):
    """After the bistro's Last call: BOSS and his lines; the Critic on bar 1 at x 16, his tiles and palettes, a meter
    of 8, the beret's stalk as the topper; the perfect window is 12 frames in his fight. Golden boss_critic: a perfect
    drink savoured (the GULP pose), the meter at 7."""
    with fight(model, C, banner=True) as gb:
        assert banner_text(gb, 2) == centred(R["line1"]) and banner_text(gb, 3) == centred(R["line2"])
        to_goal(gb)
        gb.run(2)
        check_start(gb, C, A, model)
        assert gb.mem("pour_win") == CRIT_WIN
        quiet(gb)
        throw(gb, B, 72, perfect=True)
        until(gb, lambda: gb.mem("boss_hits") == 1, 30)
        until(gb, lambda: not gb.mem("boss_push"), 20)
        frames(gb, 2)
        assert gb.mem("boss_hp") == 7 and gb.mem("boss_state") == BS_GULP
        assert_body(gb, C, A, gb.mem("boss_x"), BP_GULP)
        assert hud(gb) == meter_tiles(7, 8)
        check_golden(gb, "boss_critic")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_his_window_is_twelve_frames(model):
    """Real pours at his tap: the last held frame at pour_t 26 is ordinary, 27 and 38 perfect (the 12-frame window
    from the story's start, 27), 39 ordinary (the overflow)."""
    with fight(model, C) as gb:
        quiet(gb)
        n0 = first_launch(gb)
        got = {}
        for t in (WIN0 - 1, WIN0, WIN0 + CRIT_WIN - 1, WIN0 + CRIT_WIN):
            got[t] = hold_release(gb, n0 + t - FILL_FRAMES)
            drop_mugs(gb)
        assert got == {WIN0 - 1: 0, WIN0: 1, WIN0 + CRIT_WIN - 1: 1, WIN0 + CRIT_WIN: 0}, got


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_sloppy_drink_is_tasted_and_sent_back(model):
    """A sloppy drink: no meter, no score for it; he TASTEs it for 30 frames (the TASTE pose, he stands: no stomp),
    then it comes back up the bar as a MUG_RETURN (drawn as the full drink) from his right edge at 1 px a frame, and the
    bartender at the tap catches it like an empty (no life). Golden boss_critic_taste: the tell."""
    with fight(model, C) as gb:
        quiet(gb)
        x0 = gb.mem("boss_x")
        throw(gb, B, 72)
        until(gb, lambda: gb.mem("crit_sloppy") == 1, 30)
        assert gb.mem("boss_hp") == 8 and gb.mem("boss_hits") == 0 and gb.mem("boss_state") == BS_SPECIAL
        tasting = 0
        for f in range(CRIT_TASTE + 10):
            frames(gb, 1)
            if gb.mem("crit_taste"):
                tasting += 1
            if f == 10:
                assert_body(gb, C, A, gb.mem("boss_x"), BP_TASTE)
                check_golden(gb, "boss_critic_taste")
            if mugs(gb, B, RETURN):
                break
        assert CRIT_TASTE - 3 <= tasting <= CRIT_TASTE, tasting
        assert gb.mem("boss_x") == x0, "he stands while he tastes"
        until(gb, lambda: mugs(gb, B, RETURN), 30)
        (i, _, _, x), = mugs(gb, B, RETURN)
        assert 0 <= x - (gb.mem("boss_x") + R["width"]) <= 2
        fc, xs = gb.mem("frame_counter"), [x]
        for _ in range(30):
            frames(gb, 1)
            xs.append(gb.read("mug_x", 20)[i])
        n = (gb.mem("frame_counter") - fc) & 255
        assert abs(xs[-1] - xs[0] - n) <= 1, (n, xs)
        sprites = [o for o in gb.oam() if o["y"] and abs(o["x"] - (xs[-1] + 8)) <= 2]
        assert any(o["tile"] == gb.mem("spr_full_t") for o in sprites), "drawn as the full drink"
        catches, score = gb.read("sfx_count", 9)[3], int.from_bytes(gb.read("score", 4), "little")
        until(gb, lambda: gb.read("mug_state", 20)[i] != RETURN, 120)
        frames(gb, 2)
        assert gb.read("sfx_count", 9)[3] == catches + 1 and gb.mem("lives") == 3, "caught like an empty"
        assert int.from_bytes(gb.read("score", 4), "little") - score == GAME["EMPTY_SCORE"]
        assert gb.mem("boss_hp") == 8 and gb.mem("boss_xpose") == 0


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_busy_he_waves_drinks_back_on_the_fair_schedule(model):
    """A perfect drink savoured: he holds his glass (hands 1). Two more drinks reach him meanwhile, a perfect one too:
    both waved back (no meter, no tasting), sent as returns; his glass and the two returns reach the tap end at least
    the level's gap apart, every one caught (no life, nothing breaks behind him); the meter at 7."""
    with fight(model, C) as gb:
        quiet(gb)
        breaks = gb.read("sfx_count", 9)[4]
        throw(gb, B, 60, perfect=True)
        until(gb, lambda: gb.mem("boss_hits") == 1, 30)
        throw(gb, B, 80, perfect=True)
        throw(gb, B, 110)
        arrivals, seen, f = [], set(), 0
        while (f < 60 or gb.mem("boss_hold") or gb.mem("boss_queue") or mugs(gb, B, RETURN)
               or mugs(gb, B, EMPTY)) and f < 900:
            frames(gb, 1)
            f += 1
            for i, s, b, x in mugs(gb, B):
                if s in (EMPTY, RETURN) and (i, s) not in seen:      # (a slot freed by a caught return and used by his
                    seen.add((i, s))                                  # empty in the same frame is a new mug: slot AND state)
                    arrivals.append((f + (TAP_X - x) * (1 if s == RETURN else 2), s))
            seen &= {(i, s) for i, s, _, _ in mugs(gb, B) if s in (EMPTY, RETURN)}
            if f == 40:
                assert gb.mem("crit_waved") == 2 and gb.mem("crit_sloppy") == 0, "both waved back, none tasted"
        assert sorted(s for _, s in arrivals) == [EMPTY, RETURN, RETURN], arrivals
        arrivals_ok(sorted((a, False) for a, _ in arrivals), gb.mem("empty_gap"))
        assert gb.read("sfx_count", 9)[4] == breaks and gb.mem("lives") == 3 and gb.mem("boss_hp") == 7


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_full_queue_lets_a_drink_pass_and_a_missed_return_breaks(model):
    """His glass held and 3 drinks waiting to go back (nothing may go: the schedule blocked): he catches nothing, the
    next drink slides past him and breaks (a life); after the freeze his hands and queue are empty. A return the
    bartender is not there for slides off the right end and breaks: a life."""
    with fight(model, C) as gb:
        quiet(gb)
        block_empties(gb)
        throw(gb, B, 60, perfect=True)
        until(gb, lambda: gb.mem("boss_hits") == 1, 30)
        for k in range(CRIT_QUEUE):
            throw(gb, B, 70)
            until(gb, lambda: gb.mem("crit_waved") == k + 1, 40)
        assert gb.mem("boss_queue") == CRIT_QUEUE and gb.mem("boss_lim") == 0
        throw(gb, B, 70)
        until(gb, lambda: state(gb) == LIFE_LOST, 60)
        assert gb.mem("lives") == 2 and gb.mem("boss_hp") == 7
        until(gb, lambda: state(gb) == PLAYING, 200)
        frames(gb, 2)
        assert (gb.mem("boss_hold"), gb.mem("boss_queue"), gb.mem("crit_taste")) == (0, 0, 0)
        play(gb)
        to_bar(gb, 3)
        throw(gb, B, 72)
        until(gb, lambda: mugs(gb, B, RETURN), 80)
        until(gb, lambda: state(gb) == LIFE_LOST, 200)
        assert gb.mem("lives") == 1


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_eight_perfect_drinks_satisfy_him(model):
    """Eight perfect drinks (each when his hands are free): the meter to 0, the outro (HAPPY), CHAPTER CLEAR, the
    POST_BISTRO scene, the chapter saved."""
    with fight(model, C) as gb:
        quiet(gb)
        for hp in range(7, -1, -1):
            gb.write("boss_hold", 0)
            until(gb, lambda: gb.mem("boss_state") != BS_GULP and not gb.mem("boss_push"), 110)
            throw(gb, B, 72, perfect=True)
            until(gb, lambda: gb.mem("boss_hp") == hp, 30)
        clear_regulars(gb)
        frames(gb, 3)
        assert state(gb) == GS_STORY and gb.mem("story_phase") == SP_OUTRO and gb.mem("boss_state") == BS_OUTRO
        gb.run(60)
        assert_body(gb, C, A, gb.mem("boss_x"), BP_HAPPY)
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 120)
        gb.run(3)
        assert banner_text(gb, 1) == centred("CHAPTER CLEAR")
        run_until(gb, lambda: state(gb) == GS_STORY and gb.mem("story_scene") == post(C), 300)
        settle(gb)
        assert (gb.mem("boss_on"), gb.mem("story_progress")) == (0, C + 1)
