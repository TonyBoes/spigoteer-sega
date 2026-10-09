# M8d: a finished drinker sips on (no frozen hold), winds up (draws the empty back, swings it forward) before sending the empty, can catch a new full mug
# while he waits (his empty goes at once), and the bartender standing on him takes the glass.
import pytest
from conftest import GAME, bar_top_y
from test_patrons import (DRINK_MIN, DRINK_WAIT, DRINK_WINDUP, DRINKING, EMPTY, FULL, HELD, MAX_M, MAX_P, PUSHED,
                          PX, TAP_X, WALKING, WINDUP, catch_frames, clear_patrons, drinker_with_mug, freeze,
                          inject_mug, mugs, put, score)
from test_smooth import OBJ_DRINK, drink_sprites
from test_sound import SFX_CATCH, sfx_count

pytestmark = pytest.mark.timeout(60)

BT_CATCH = 5
SIP_LOOP_T, DRINK_FRAMES = GAME["SIP_LOOP_T"], GAME["DRINK_FRAMES"]


def put16(gb, name, v):
    gb.write(name, v & 255)
    gb.write(gb.addr(name) + 1, v >> 8)


def state(gb, p):
    return gb.read("patron_state", MAX_P)[p], gb.read("patron_aux", MAX_P)[p]


def waiting_drinker(gb, bar, x, hold_off=500):
    """A drinker who has just finished, with an empty that may not go for hold_off frames (fair empties)."""
    clear_patrons(gb)
    freeze(gb)
    put16(gb, "next_arrival", hold_off)
    p = drinker_with_mug(gb, bar, x, DRINK_FRAMES - 1)
    gb.run(3)
    assert state(gb, p) == (DRINKING, DRINK_WAIT)
    return p


# ---- 1: no frozen hold, he sips on -------------------------------------------------------------------
def test_a_waiting_patron_keeps_sipping_and_his_mug_keeps_changing_frames(gb):
    p = waiting_drinker(gb, 1, 40)
    tiles, ys, xs = [], set(), set()
    for _ in range(150):
        gb.run(1)
        assert state(gb, p) == (DRINKING, DRINK_WAIT) and gb.read("patron_x", MAX_P)[p] == 40
        assert SIP_LOOP_T <= gb.read("patron_timer", MAX_P)[p] < DRINK_FRAMES
        ss = drink_sprites(gb)
        assert len(ss) == 1
        tiles.append((ss[0]["tile"] - OBJ_DRINK) // 2)
        ys.add(ss[0]["y"] - 16 - bar_top_y(1))
        xs.add(gb.read("patron_draw", MAX_P)[p])
    assert set(tiles) == {1, 2}, "tilted and tipped (the sipping poses), never upright-full or the lowered empty"
    assert sum(a != b for a, b in zip(tiles, tiles[1:])) >= 3, "the held mug keeps changing frames"
    assert ys == {1}, "at his mouth"
    assert xs == {40, 42}, "and he sways"


# ---- 2: the wind-up -------------------------------------------------------------------------------------
def test_the_windup_lasts_windup_frames_then_the_empty_slides(gb):
    clear_patrons(gb)
    freeze(gb)
    p = drinker_with_mug(gb, 1, 30, DRINK_FRAMES - 1)
    m = list(gb.read("patron_mug", MAX_P))[p]
    for _ in range(5):
        gb.run(1)
        if state(gb, p)[1] == DRINK_WINDUP:
            break
    assert state(gb, p) == (DRINKING, DRINK_WINDUP), "a lone patron winds up at once"
    frames, tiles, offs, drawn, xs = 0, set(), [], set(), []
    while gb.read("mug_state", MAX_M)[m] == HELD:
        ss = drink_sprites(gb)
        tiles.add((ss[0]["tile"] - OBJ_DRINK) // 2)
        offs.append((ss[0]["x"] - 8 - gb.read("patron_draw", MAX_P)[p], ss[0]["y"] - 16 - bar_top_y(1)))
        xs.append(ss[0]["x"] - 8)
        drawn.add(gb.read("patron_draw", MAX_P)[p])
        gb.run(1)
        frames += 1
        assert frames < 60
    assert WINDUP - 1 <= frames <= WINDUP + 1, frames
    assert gb.read("mug_state", MAX_M)[m] == EMPTY and state(gb, p) == (WALKING, 0)
    assert gb.read("mug_x", MAX_M)[m] in (30 + 16, 30 + 17), "the empty starts at his right edge"
    assert tiles == {3}, "the empty mug frame throughout"
    assert offs[0][1] < offs[-1][1] == 6, "lowered to his hand"
    # the pull-back: the mug is drawn back to the left, held a beat, then swung forward to the launch x
    lo = min(xs)
    assert xs[0] - lo >= 4, ("drawn back to the left by at least 4 px", xs)
    assert xs[0] - lo <= 6, "... but not more than 6"
    k = xs.index(lo)
    assert all(a >= b for a, b in zip(xs[:k + 1], xs[1:k + 1])), "easing left, never forward, until the hold"
    assert xs.count(lo) >= 4, "held a beat at the back"
    assert xs[-1] > lo + 4 and all(a <= b for a, b in zip(xs[xs.index(lo) + 1:], xs[xs.index(lo) + 2:])), "then swung forward"
    assert xs[-1] < 30 + 16, "and the slide begins from his edge"
    assert drawn == {30}, "he stands still while he winds up"


# ---- fair empties include the wind-up -------------------------------------------------------------------
def test_empties_arrive_empty_gap_apart_counting_the_windup(gb):
    """Three patrons finish together; the one nearest the tap and the one at the door (whose empty would arrive late
    enough anyway) wind up at once, the middle one sips on until his arrival is fair. Arrival = the frame the
    bartender takes the empty off the counter (its slot is freed; the score can show it a frame later)."""
    clear_patrons(gb)
    freeze(gb)
    gap = gb.mem("empty_gap")
    ps = [drinker_with_mug(gb, 0, x, DRINK_FRAMES - 1) for x in (80, 40, 0)]
    ms = [gb.read("patron_mug", MAX_P)[p] for p in ps]
    arrived, sent, prev = {}, {}, [HELD] * 3
    for f in range(500):
        gb.run(1)
        st = [gb.read("mug_state", MAX_M)[m] for m in ms]
        for k in range(3):
            if prev[k] == HELD and st[k] == EMPTY:
                sent[k] = f
            if prev[k] == EMPTY and st[k] == 0:
                arrived[k] = f
        prev = st
    assert len(arrived) == 3 and score(gb) == 300, arrived
    order = sorted(arrived.values())
    assert all(b - a >= gap for a, b in zip(order, order[1:])), arrived
    assert order[-1] - order[-2] <= gap + 2, "and no later than needed"
    assert sent[0] == sent[2] and sent[1] > sent[0], "the middle one waited"
    first = WINDUP + 2 * (TAP_X - (80 + 16))      # the nearest: wind-up, then the slide
    assert abs(arrived[0] - first) <= 2, (arrived, first)


def test_next_arrival_counts_the_windup(gb):
    clear_patrons(gb)
    freeze(gb)
    gap = gb.mem("empty_gap")
    drinker_with_mug(gb, 2, 50, DRINK_FRAMES - 1)
    gb.run(2)
    t = WINDUP + 2 * (TAP_X - (50 + 16))
    assert t + gap - 2 <= gb.mem16("next_arrival") <= t + gap


# ---- 3: a waiting patron catches a new mug ---------------------------------------------------------------
def test_a_waiting_patron_catches_a_new_mug_and_his_empty_slides_at_once(gb):
    gb.press("down", 2)                           # the bartender on bar 1, at the tap: he will catch the empty
    p = waiting_drinker(gb, 1, 96)
    put(gb, "patron_drinks", p, 1)
    old = list(gb.read("patron_mug", MAX_P))[p]
    new = inject_mug(gb, 1, 130)
    for _ in range(20):
        gb.run(1)
        if gb.read("patron_state", MAX_P)[p] == PUSHED:
            break
    assert gb.read("patron_state", MAX_P)[p] == PUSHED, "a finished drinker catches the full mug"
    assert gb.read("mug_state", MAX_M)[old] == EMPTY, "his old empty goes at once, no fair-empties wait"
    assert gb.read("mug_x", MAX_M)[old] in (96 + 16, 96 + 17)
    assert gb.read("mug_state", MAX_M)[new] == HELD and gb.read("patron_mug", MAX_P)[p] == new
    assert gb.read("patron_drinks", MAX_P)[p] == 2
    assert gb.mem16("next_arrival") >= 400, "a later empty still waits for the one already scheduled"
    assert len(mugs(gb)) == 2, "no new slot: the held mug became the empty, the caught one is held"
    s0 = score(gb)
    for _ in range(3 * PX):
        gb.run(1)
        if gb.read("patron_state", MAX_P)[p] == DRINKING:
            break
    assert gb.read("patron_state", MAX_P)[p] == DRINKING and gb.read("patron_aux", MAX_P)[p] == DRINK_MIN
    assert gb.read("patron_x", MAX_P)[p] == 96 - 2 * PX, "thirst: the 2nd drink pushes him back twice as far"
    gb.run(20)
    assert score(gb) == s0 + 100, "the bartender caught the sent empty"


def test_a_winding_up_patron_who_catches_keeps_later_empties_spaced_after_his(gb):
    clear_patrons(gb)
    freeze(gb)
    gb.press("down", 2)
    gap = gb.mem("empty_gap")
    p = drinker_with_mug(gb, 1, 96, DRINK_FRAMES - 1)
    gb.run(3)
    assert state(gb, p) == (DRINKING, DRINK_WINDUP)
    put16(gb, "next_arrival", 0)                  # (as if his own schedule had run out)
    inject_mug(gb, 1, 120)
    for _ in range(12):
        gb.run(1)
        if gb.read("patron_state", MAX_P)[p] == PUSHED:
            break
    assert gb.read("patron_state", MAX_P)[p] == PUSHED
    t = 2 * (TAP_X - (96 + 16))                   # the sent empty's travel (no wind-up)
    assert t + gap - 3 <= gb.mem16("next_arrival") <= t + gap


def test_a_patron_in_his_minimum_drink_lets_a_full_mug_pass(gb):
    clear_patrons(gb)
    freeze(gb)
    p = drinker_with_mug(gb, 2, 80, 30)
    m = inject_mug(gb, 2, 136)
    gb.run(36)
    assert gb.read("mug_state", MAX_M)[m] == FULL and gb.read("mug_x", MAX_M)[m] < 80, "it slid past him"
    assert state(gb, p) == (DRINKING, DRINK_MIN) and gb.read("patron_drinks", MAX_P)[p] == 0


# ---- 4: the bartender takes the glass --------------------------------------------------------------------
def test_the_bartender_walking_into_a_waiting_patron_takes_the_glass(gb):
    p = waiting_drinker(gb, 0, 80)               # the bartender stands at the tap on bar 0
    s0, c0 = score(gb), sfx_count(gb, SFX_CATCH)
    gb.hold("left")
    for _ in range(40):
        gb.run(1)
        if gb.read("patron_state", MAX_P)[p] != DRINKING:
            break
    bx = gb.mem("bartender_x")
    gb.run(2)
    gb.release("left")
    assert bx < 80 + 16, "overlapping him"
    assert state(gb, p) == (WALKING, 0), "he walks again"
    assert score(gb) == s0 + 100
    assert mugs(gb) == [] and gb.read("patron_mug", MAX_P)[p] == 255, "the glass is gone"
    assert sfx_count(gb, SFX_CATCH) == c0 + 1
    assert gb.mem("bartender_frame") == BT_CATCH, "the catch pose"


def test_the_bartender_takes_the_glass_during_the_windup_too(gb):
    clear_patrons(gb)
    freeze(gb)
    p = drinker_with_mug(gb, 0, 80, DRINK_FRAMES - 1)
    gb.run(3)
    assert state(gb, p) == (DRINKING, DRINK_WINDUP)
    s0 = score(gb)
    gb.hold("left")                               # 24 px to walk at 1.5 px a frame: inside the 30-frame wind-up
    for _ in range(25):
        gb.run(1)
        if state(gb, p)[0] != DRINKING:
            break
    gb.release("left")
    assert state(gb, p) == (WALKING, 0) and score(gb) == s0 + 100 and mugs(gb) == [], "taken, not sent"


def test_a_patron_finishing_under_the_bartender_hands_him_the_glass(gb):
    clear_patrons(gb)
    freeze(gb)
    p = drinker_with_mug(gb, 0, 106, DRINK_FRAMES - 1)   # overlaps the bartender at the tap (120)
    s0 = score(gb)
    gb.run(3)
    assert state(gb, p) == (WALKING, 0) and score(gb) == s0 + 100 and mugs(gb) == []


def test_the_bartender_does_not_take_a_glass_mid_drink_or_from_another_bar(gb):
    clear_patrons(gb)
    freeze(gb)
    a = drinker_with_mug(gb, 0, 106, 10)          # overlapping him, but still drinking
    b = waiting = drinker_with_mug(gb, 1, 106, DRINK_FRAMES - 1)
    put16(gb, "next_arrival", 500)
    s0 = score(gb)
    gb.run(30)
    assert state(gb, a) == (DRINKING, DRINK_MIN)
    assert state(gb, waiting) == (DRINKING, DRINK_WAIT), "bar 1: the bartender is on bar 0"
    assert score(gb) == s0 and len(mugs(gb)) == 2 and b == waiting


def test_catching_an_empty_shows_the_catch_pose(gb):
    clear_patrons(gb)
    inject_mug(gb, 0, 118, EMPTY)
    for _ in range(10):
        gb.run(1)
        if score(gb):
            break
    assert score(gb) == 100
    gb.run(2)
    assert gb.mem("bartender_frame") == BT_CATCH
    gb.run(GAME["CATCH_POSE_FRAMES"] + 2)
    assert gb.mem("bartender_frame") != BT_CATCH
