# The spawn picks are random from run to run (owner 2026-11-01: "it doesn't feel random", Pete in Sal's palette five times in a round).
# Cause: the 8-bit xorshift (255 states) was seeded once at power-on and never mixed, so every run replayed the same sequence, and since the next
# state is a function of the last one each (look, palette) pair was followed by only about 5 of the Stadium's 50 pairs. The fix: the DIV counter at
# the key that starts a game seeds rng_state (src/title.c rng_mix) and the pick takes DIV too (src/mirror.c spawn_variant). ROM byte 0x3FFD, the tests'
# switch (0 in every test ROM), switches both off so the tests' fixed seeds stay; these tests load the ROM as built.
# Played here as a player would (arcade, random keys), the Stadium (group 1), the spawn timer forced to 0 so a run has hundreds of spawns.
import collections
import random
import re

import pytest
from conftest import ROM, ROOT, double_speed, seeding, title_arcade
from gbtools import Rom
from test_flow import run_until, state
from test_story import to_goal, win

pytestmark = pytest.mark.parametrize("model", ["dmg", "cgb"])
GS_GOAL, GS_BONUS = 12, 6
PICKS_PER_RUN = 450      # accepted spawns


def spawn_variant_hook():
    m = re.search(r"DEF _spawn_variant 0x([0-9A-F]+)", (ROOT / "build" / "game.noi").read_text())
    a = int(m.group(1), 16)
    return a >> 16, a & 0xFFFF


def play_picks(model, wait, frames, seed=1, group=1):
    """The variant bytes of the patrons that spawned in `group` (arcade), the title key pressed `wait` frames later than usual."""
    rnd = random.Random(seed)
    picks = []
    with double_speed(), seeding(), Rom(ROM, model) as gb:   # (the ROM as built: the tests' byte 0x3FFD switches the mixing off)
        gb.run(120 + wait)
        title_arcade(gb)
        run_until(gb, lambda: state(gb) == GS_GOAL, 60)
        gb.run(3)
        to_goal(gb)
        if group:
            gb.write("story_chapter", group - 1)
            gb.write("story_step", 3)
            win(gb, group - 1, 0)
            run_until(gb, lambda: state(gb) == GS_BONUS, 400)
            gb.write("bonus_phase", 4)
            gb.write("bonus_timer", 129)
            run_until(gb, lambda: state(gb) == GS_GOAL, 800)
            gb.run(3)
            to_goal(gb)
        assert gb.mem("cur_group") == group
        gb.run(60)
        pend = []
        bank, addr = spawn_variant_hook()
        gb.pb.hook_register(bank, addr, lambda _: pend.append(list(gb.read("patron_state", 16))), None)
        for fr in range(frames):
            if fr % 30 == 0:
                gb.write("lives", 9)
                gb.write("served", 0)
                if gb.mem("quota") < 200:
                    gb.write("quota", 200)
            gb.write("spawn_timer", 0)
            if rnd.random() < 0.05:                   # (a player's keys: each new key seeds the generator with DIV)
                gb.press(rnd.choice(["a", "up", "down", "left"]), 2)
            else:
                gb.run(1)
            if pend:
                before = pend.pop()
                now = list(gb.read("patron_state", 16))
                v = gb.read("patron_variant", 16)
                new = [v[i] for i in range(16) if now[i] and not before[i]]
                if new and not gb.mem("boss_on"):
                    picks.append(new[0])
            if len(picks) >= PICKS_PER_RUN:
                break
    return picks


def test_the_seed_switch_byte_is_the_free_rom0_padding(model):
    assert ROM.read_bytes()[0x3FFD] == 0xFF, "0xFF as built: the DIV mixing is on (every test ROM has it 0, conftest.seeding())"


def chi2(picks, n_pairs):
    c = collections.Counter(picks)
    e = len(picks) / n_pairs
    return sum((x - e) ** 2 / e for x in c.values()) + (n_pairs - len(c)) * e, len(c)


def avg_successors(picks):
    succ = collections.defaultdict(set)
    for a, b in zip(picks, picks[1:]):
        succ[a].add(b)
    return sum(len(s) for s in succ.values()) / len(succ)


@pytest.mark.timeout(300)
def test_two_title_timings_give_different_spawn_sequences(model):
    a = play_picks(model, 0, 3000)
    b = play_picks(model, 37, 3000)
    n = min(len(a), len(b), 12)
    assert n >= 8
    assert a[:n] != b[:n], "the first spawns of two runs differ when the player pressed the key at another moment"


@pytest.mark.only_model("cgb")
@pytest.mark.timeout(600)
def test_the_stadium_picks_are_uniform_and_not_locked_to_a_few_successors(model):
    picks = []
    for wait, seed in ((0, 1), (37, 2), (171, 3), (90, 4), (213, 5)):
        picks += play_picks("cgb", wait, 90000, seed)
    assert len(picks) >= 1000, len(picks)
    x2, distinct = chi2(picks, 50)
    assert distinct == 50, "every one of the Stadium's 50 (look, palette) pairs comes up"
    assert x2 < 95, f"chi-square {x2:.0f} over 49 degrees of freedom: the picks are near uniform"
    assert avg_successors(picks) > 12, f"a pair is followed by {avg_successors(picks):.1f} of the 50 (the 8-bit generator alone gave about 5)"
    run = collections.Counter()
    for i in range(0, len(picks) - 29, 15):
        run[max(collections.Counter(picks[i:i + 30]).values())] += 1
    assert max(run) <= 6, f"no pair repeats implausibly often in 30 spawns: {dict(run)}"


@pytest.mark.only_model("dmg")
@pytest.mark.timeout(300)
def test_the_dmg_picks_stay_uniform_among_its_three_looks(model):
    picks = play_picks("dmg", 0, 40000) + play_picks("dmg", 53, 40000, 2)
    c = collections.Counter(p & 7 for p in picks)
    assert set(c) == {0, 1, 2} and len(picks) >= 300, (c, len(picks))
    x2, _ = chi2([p & 7 for p in picks], 3)
    assert x2 < 14, (dict(c), x2)
