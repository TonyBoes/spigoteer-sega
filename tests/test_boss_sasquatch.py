# docs/minigames_bosses.md 3.5: the Sasquatch, the lumber lodge's boss (src/boss_sasquatch.c; art approved 2026-10-11).
# The fight follows the lodge's Last call (gen_story BUILT_SLOTS): his row (32 px, step 90, push 8, gulp 8, hands 2,
# sip 0, meter 12), his empties at 1 px a frame on his bar only, the hands rule (the third coffee breaks), the fair
# schedule (the level's gap from a regular's empty, his own 80 between his own), a win by real pours and the tap.
# Every frame of every fight here is checked at <= 10 sprites a line (boss_common.frames).
import pytest
from boss_common import (BP_GULP, Clock, BP_HAPPY, BP_WALK, BP_WINCE, BS_GULP, BS_OUTRO, EMPTY, FULL, SP_OUTRO, SPOUT_X,
                         TAP_X, art, assert_body, block_empties, check_start, fight, frames, hud, meter_tiles, mugs,
                         play, pour, row, still_regulars, throw, to_bar, until, arrivals_ok)
from conftest import check_golden
from test_flow import GS_STORY, LEVEL_CLEAR, LIFE_LOST, PLAYING, inject_mug, run_until, state
from test_story import banner_text, centred, post, settle

pytestmark = pytest.mark.timeout(300)

C = 2                                   # the lumber lodge
R = row(C)
A = art("sasquatch")
B = R["bar"]
OWN_GAP = 80


def test_his_row_and_art():
    """Spec 3.2 / 3.5's numbers, the banner lines of spec 7, his approved art (5 poses, no extra), the fast-empty
    bar and his own gap in his file."""
    assert {k: R[k] for k in ("width", "x", "bar", "step", "push", "gulp", "hands", "sip", "meter", "hat")} == dict(
        width=32, x=16, bar=2, step=90, push=8, gulp=8, hands=2, sip=0, meter=12, hat=12)
    assert (R["line1"], R["line2"]) == ("NO SUCH THING", "12 COFFEES FAST")
    assert A["poses"] == ["WALK", "STOMP", "GULP", "WINCE", "HAPPY"] and A["cols"] == 4
    from conftest import ROOT
    assert "; Art: approved design" in (ROOT / "assets/art/boss/sasquatch.txt").read_text()
    assert not (ROOT / "assets/art/approved/boss_sasquatch.txt").exists()
    src = (ROOT / "src/boss_sasquatch.c").read_text()
    assert "boss_fast_empty = 1;" in src and "#define SASQ_GAP  80" in src


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_fight_follows_the_last_call(model):
    """After the lodge's Last call: BOSS and his two lines, the lives carried, no tips; then the Sasquatch on bar 2 at
    x 16 (his tiles and palettes), the HUD's face and a meter of 12 (6 tiles), the crest over his head. Golden
    boss_sasquatch: mid-fight, one coffee down, its empty sliding back fast."""
    with fight(model, C, banner=True) as gb:
        assert banner_text(gb, 1) == centred("BOSS")
        assert banner_text(gb, 2) == centred(R["line1"]) and banner_text(gb, 3) == centred(R["line2"])
        assert gb.mem("lives") == 3 and gb.mem("tip_chance") == 0
        assert all(b != B for b in gb.read("pat_buf", 8))
        from test_story import to_goal
        to_goal(gb)
        gb.run(2)
        check_start(gb, C, A, model)
        still_regulars(gb)
        play(gb)
        throw(gb, B, 72)
        until(gb, lambda: gb.mem("boss_hits") == 1, 30)
        until(gb, lambda: mugs(gb, B, EMPTY), 30)
        frames(gb, 24)
        assert hud(gb) == meter_tiles(11, 12)
        check_golden(gb, "boss_sasquatch")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_his_empties_slide_back_at_1px_a_frame_on_his_bar_only(model):
    """He gulps for 8 frames (GULP pose) and sends the empty at once (sip 0) from his right edge; it slides 1 px every
    frame; an empty on another bar at the same time still slides 0.5 px a frame; the bartender at his tap catches it."""
    with fight(model, C) as gb:
        still_regulars(gb)
        play(gb)
        to_bar(gb, B)
        inject_mug(gb, 0, 40, st=EMPTY)
        throw(gb, B, 72)
        until(gb, lambda: gb.mem("boss_hits") == 1, 30)
        frames(gb, 1)
        assert gb.mem("boss_state") == BS_GULP or gb.mem("boss_push")
        until(gb, lambda: mugs(gb, B, EMPTY), 20)
        (i, _, _, x0), = mugs(gb, B, EMPTY)
        assert 0 <= x0 - (gb.mem("boss_x") + R["width"]) <= 2, "sent from his right edge (seen a frame or two on)"
        other0 = [x for _, _, _, x in mugs(gb, 0, EMPTY)][0]
        xs, others, fc = [x0], [other0], gb.mem("frame_counter")
        for _ in range(40):
            frames(gb, 1)
            xs.append(gb.read("mug_x", 20)[i])
            others.append([x for _, _, _, x in mugs(gb, 0, EMPTY)][0])
        n = (gb.mem("frame_counter") - fc) & 255            # game frames (PyBoy's frame may end mid-logic: a sample
        assert abs(xs[-1] - xs[0] - n) <= 1, (n, xs)         # can see the step before boss_mugs' extra pixel)
        assert all(0 <= b - a <= 2 for a, b in zip(xs, xs[1:])), xs
        assert abs(others[-1] - others[0] - n // 2) <= 1, "0.5 px a frame on the other bar"
        catches = gb.read("sfx_count", 9)[3]
        until(gb, lambda: gb.read("mug_state", 20)[i] != EMPTY, 120)
        frames(gb, 2)
        assert gb.read("sfx_count", 9)[3] == catches + 1 and gb.mem("lives") == 3, "caught at the tap"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_two_in_his_hands_and_the_third_coffee_breaks(model):
    """Holding two (his hand column shows them) he catches nothing: the third coffee slides past him and breaks at the
    left end (a life), the meter at 10; after the freeze he starts again at x 16 with empty hands."""
    with fight(model, C) as gb:
        still_regulars(gb)
        play(gb)
        block_empties(gb)
        for x in (60, 100):
            throw(gb, B, x)
        until(gb, lambda: gb.mem("boss_hits") == 2, 60)
        until(gb, lambda: gb.mem("boss_state") != BS_GULP and not gb.mem("boss_push"), 60)
        assert gb.mem("boss_hold") == 2 and gb.mem("boss_lim") == 0
        assert_body(gb, C, A, gb.mem("boss_x"), BP_WALK, 2)
        throw(gb, B, 80)
        until(gb, lambda: state(gb) == LIFE_LOST, 60)
        assert gb.mem("boss_hp") == 10 and gb.mem("boss_hits") == 2 and gb.mem("lives") == 2
        until(gb, lambda: state(gb) == PLAYING, 200)
        frames(gb, 2)
        assert (gb.mem("boss_x"), gb.mem("boss_hold"), gb.mem("boss_hp")) == (R["x"], 0, 10)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_fair_schedule_with_a_regulars_empty_due(model):
    """A regular's empty scheduled (next_arrival 150: due at the tap end 150 - gap frames from now): his empty waits
    until it arrives no sooner than the level's gap after it, and goes on the first frame it may. A regular's next one
    then keeps the level's gap from his (next_arrival = his travel + empty_gap). His next own empty only needs 80 after
    his own (less than the lodge's gap)."""
    with fight(model, C) as gb:
        still_regulars(gb)
        play(gb)
        gap = gb.mem("empty_gap")
        assert gap > OWN_GAP
        clock = Clock(gb)
        gb.write("next_arrival", 200)                       # (a regular's empty due at the tap end at 200 - gap)
        gb.write(gb.addr("next_arrival") + 1, 0)
        throw(gb, B, 60)
        first = sent(gb, clock)
        assert 200 <= first <= 203, first
        assert abs(gb.mem16("next_arrival") - (first - clock.now() + gap)) <= 2, \
            "a regular's next keeps the level's gap from his"
        throw(gb, B, 70)
        second = sent(gb, clock)
        assert OWN_GAP - 2 <= second - first <= OWN_GAP + 3 < gap, (first, second, gap)


def sent(gb, clock, limit=400):
    """Wait for his next empty to leave his hands (boss_hold drops, the empty just spawned at his right edge): its
    arrival at the tap end, in clock frames (its x when seen, at 1 px a frame)."""
    hold = gb.mem("boss_hold")
    for _ in range(limit):
        frames(gb, 1)
        clock.now()
        h = gb.mem("boss_hold")
        if h < hold:
            x = min(m[3] for m in mugs(gb, B, EMPTY))
            return clock.now() + (TAP_X - x)
        hold = max(hold, h)
    raise AssertionError("no empty sent")

@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_win_the_fight_by_pouring(model):
    """Real pours on bar 2, the bartender staying at the tap for the fast empties: 12 coffees and he is satisfied;
    every empty caught (no life lost), his empties' arrivals at least his own gap apart; the outro (HAPPY), CHAPTER
    CLEAR, the POST_LUMBER scene, the chapter saved."""
    with fight(model, C) as gb:
        still_regulars(gb)
        play(gb)
        to_bar(gb, B)
        arrivals, seen, f = [], set(), 0
        while gb.mem("boss_hp") and f < 5000:
            if gb.mem("boss_hold") + len(mugs(gb, B, FULL)) < R["hands"]:
                f += pour(gb)
            else:
                frames(gb, 1)
                f += 1
            for i, s, b, x in mugs(gb):
                if s == EMPTY and i not in seen:
                    seen.add(i)
                    arrivals.append((f + (TAP_X - x) * (1 if b == B else 2), b == B))
            seen &= {i for i, s, _, _ in mugs(gb, st=EMPTY)}
        assert gb.mem("boss_hits") == 12 and gb.mem("lives") == 3
        arrivals_ok(sorted(arrivals), gb.mem("empty_gap"), OWN_GAP)
        frames(gb, 1)
        assert state(gb) == GS_STORY and gb.mem("story_phase") == SP_OUTRO and gb.mem("boss_state") == BS_OUTRO
        gb.run(60)
        assert_body(gb, C, A, gb.mem("boss_x"), BP_HAPPY)
        assert all(s == 0 for s in gb.read("mug_state", 20))
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 120)
        gb.run(3)
        assert banner_text(gb, 1) == centred("CHAPTER CLEAR")
        run_until(gb, lambda: state(gb) == GS_STORY and gb.mem("story_scene") == post(C), 300)
        settle(gb)
        assert (gb.mem("boss_on"), gb.mem("story_progress")) == (0, C + 1)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_push_back_and_the_tap(model):
    """A coffee pushes him back 8 px (one hop: WINCE); unhit he stomps 8 px every 90 frames; his right edge at the tap
    costs a life and he starts over at x 16 with his meter kept."""
    with fight(model, C) as gb:
        still_regulars(gb)
        play(gb)
        xs = []
        for _ in range(2 * R["step"] + 2):
            x = gb.mem("boss_x")
            frames(gb, 1)
            if gb.mem("boss_x") != x:
                xs.append(gb.mem("boss_x"))
        assert xs == [R["x"] + 8, R["x"] + 16]
        throw(gb, R["bar"], 90)
        until(gb, lambda: gb.mem("boss_hits") == 1, 30)
        until(gb, lambda: not gb.mem("boss_push"), 10)
        assert gb.mem("boss_x") == R["x"] + 8
        until(gb, lambda: gb.mem("boss_state") != BS_GULP, 20)
        block_empties(gb)
        gb.write("boss_x", SPOUT_X - R["width"] - 8)
        until(gb, lambda: state(gb) == LIFE_LOST, R["step"] + 2)
        assert gb.mem("lives") == 2 and gb.mem("boss_hp") == 11
        until(gb, lambda: state(gb) == PLAYING, 200)
        frames(gb, 3)
        assert (gb.mem("boss_x"), gb.mem("boss_hp"), gb.mem("boss_hold")) == (R["x"], 11, 0)
        assert_body(gb, C, A, R["x"], BP_WALK)
        assert hud(gb) == meter_tiles(11, 12)
