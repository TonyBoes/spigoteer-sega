"""Almost-out patrons (owner 2026-10-17: "1 out of 7 patrons should stop just shy of sliding out and drink if it is their first drink. This
can be adjusted for difficulty level later on.").

A patron whose FIRST mug would carry him off the left edge (a push that reaches the left-edge stop) has a 1 in N chance (level.c
almost_one_in, N = 7 now, per play mode and difficulty; CLASSIC 0 = never, it stays authentic) of stopping at ENTRY_X instead, where he
drinks and comes back as any returning patron. Later mugs serve him as before. The roll is the game's own deterministic RNG:
`next_rand() % N == 0`, the first number drawn when the mug lands."""
import pytest
from conftest import GAME, logic_paused
from test_patrons import (DRINKING, ENTRY_X, MAX_P, PUSHED, WALKING, clear_patrons, inject_mug, mugs, put, set_patron)
from test_tips import w16, xorshift

pytestmark = pytest.mark.timeout(120)

LEAVING = 4
N = 7
MODE_STORY, MODE_CLASSIC, MODE_LEVEL = 1, 2, 3


def first_mug(gb, rng, drinks=0, x=60, mode=None):
    """A patron at x (a push of 250 px: it would serve him) takes a mug with the generator at `rng`; returns his state once the catch is done."""
    clear_patrons(gb)
    gb.write("intro_timer", 0)
    w16(gb, "spawn_timer", 0xFFFF)
    gb.write("quota", 200)
    gb.write("tip_chance", 0)
    with logic_paused(gb):
        if mode is not None:
            gb.write("play_mode", mode)
        gb.write("pushback_px", 250)
        gb.write("rng_state", rng)
        i = set_patron(gb, 1, x)
        put(gb, "patron_drinks", i, drinks)
        inject_mug(gb, 1, x + 6)
    gb.run(60)                                            # (the push to the left end takes 44 frames: then he drinks, or slides out)
    return i, gb.read("patron_state", MAX_P)[i]


def predicted(rng):
    return xorshift(rng) % N == 0


STATES = [5 * n + 1 for n in range(50)]


def test_one_in_seven_first_drinkers_stop_at_the_door_and_the_rest_are_served(gb):
    want = [predicted(s) for s in STATES]
    assert 4 <= sum(want) <= 12, sum(want)                # (about 50 / 7)
    got = []
    for s in STATES:
        i, st = first_mug(gb, s)
        got.append(st == DRINKING)                        # stopped at the door, rather than LEAVING
        if st == DRINKING:
            assert gb.read("patron_x", MAX_P)[i] == ENTRY_X, "just shy of the edge"
    assert got == want


def test_a_mug_that_would_not_serve_him_is_pushed_and_he_drinks_as_always(gb):
    for st in STATES[:10]:
        clear_patrons(gb)
        with logic_paused(gb):
            gb.write("pushback_px", 24)
            gb.write("rng_state", st)
            gb.write("tip_chance", 0)
            w16(gb, "spawn_timer", 0xFFFF)
            gb.write("intro_timer", 0)
            i = set_patron(gb, 1, 100)
            inject_mug(gb, 1, 106)
        gb.run(40)
        assert gb.read("patron_state", MAX_P)[i] == DRINKING and gb.read("patron_x", MAX_P)[i] == 100 - 24


def test_only_the_first_drink_can_stop_him_short(gb):
    for s in STATES:
        _, st = first_mug(gb, s, drinks=1)
        assert st == LEAVING, "a second mug serves him as it always did"


def test_a_stopped_patron_drinks_and_comes_back_as_a_returning_patron_who_is_served_by_the_next_mug(gb):
    s = next(s for s in STATES if predicted(s))
    i, st = first_mug(gb, s)
    assert st == DRINKING
    assert gb.read("patron_state", MAX_P)[i] == DRINKING
    assert gb.read("patron_drinks", MAX_P)[i] == 1 and gb.mem("served") == 0, "no serve yet"
    gb.run(300)
    assert gb.read("patron_state", MAX_P)[i] == WALKING and [m["state"] for m in mugs(gb)] != [], "his empty went and he walks on"
    x = gb.read("patron_x", MAX_P)[i]
    with logic_paused(gb):
        for m in range(len(mugs(gb)) + 8):
            put(gb, "mug_state", m, 0)
        gb.write("mugs_live", 0)
        inject_mug(gb, 1, x + 6)
    s0 = gb.mem("served")
    gb.run(120)
    assert gb.mem("served") == s0 + 1, "the second mug served him: it slid him off"


@pytest.mark.parametrize("mode", [MODE_STORY, MODE_LEVEL])
def test_the_chance_is_on_in_story_arcade_and_the_harness(gb, mode):
    s = next(s for s in STATES if predicted(s))
    _, st = first_mug(gb, s, mode=mode)
    assert st == DRINKING


def test_classic_keeps_the_original_patron_nobody_stops_short(gb):
    """CLASSIC (owner kept it authentic): the table's row is 0, whatever the generator holds."""
    for s in STATES:
        _, st = first_mug(gb, s, mode=MODE_CLASSIC)
        assert st == LEAVING


@pytest.mark.only_model('dmg')
def test_the_tune_table_defaults_to_one_in_seven_everywhere_but_classic(gb):
    from test_story import BANKS, ROM
    t = gb.addr("almost_one_in")
    rom = ROM.read_bytes()
    base = BANKS["b_push_for"] * 0x4000 + t - 0x4000      # (level.c is in a switched bank, which is not mapped now)
    rows = [list(rom[base + 4 * r: base + 4 * r + 4]) for r in range(5)]
    assert rows == [[N] * 4, [N] * 4, [0] * 4, [N] * 4, [N] * 4], rows
