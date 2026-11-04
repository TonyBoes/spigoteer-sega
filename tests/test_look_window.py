# The Color spawn rule (owner 2026-11-04: "a patron type can't come out unless three other patron types have come out for it ... I'm not talking about
# palettes, I'm talking about the actual designs ... That would obviously be color only."): a patron's look (patron_variant & 7; the palette instances of one
# design are the same look) is never one of the last 3 looks that spawned in the venue. src/mirror.c pick_x asks build/looks.c looks_accept, which keeps the
# last 3 looks in story_scratch[65..69] (src/scratch.h LOOK_HIST) and start_level clears them; the DMG's pick (r % 3) is untouched.
# These play the story's venues as built (no seed mixing: the fixed seeds are the tests'), the spawn timer forced to 0 so a run has hundreds of spawns.
import random

import pytest
from boss_common import fight
from test_flow import PLAYING, run_until, state
from test_story import to_chapter

pytestmark = pytest.mark.timeout(600)
HIST_AT = 65            # src/scratch.h SCR_LOOKH_AT
WINDOW = 3


def record(gb, frames, resync=True):
    """Looks (variant & 7) of the patrons that spawned over `frames` frames of play (the bars kept busy: lives and the quota topped up, a player's keys),
    as runs of consecutive spawns. A lost life places the start patrons again, and a slot freed and refilled in one frame is not a spawn the picture of
    the slots shows: a run ends there (resync) and the next begins a few frames on."""
    runs, looks, rnd, pend = [], [], random.Random(1), []
    lv, sp, quiet = gb.mem("lives"), gb.mem("spawned"), 0
    for fr in range(frames):
        if fr % 30 == 0:
            gb.write("lives", 9)
            gb.write("served", 0)
            if gb.mem("quota") < 200:
                gb.write("quota", 200)
        gb.write("spawn_timer", 0)
        before = list(gb.read("patron_state", 16))
        if rnd.random() < 0.05:                  # (a player's keys: mugs go out, patrons are served and leave)
            gb.press(rnd.choice(["a", "up", "down", "left"]), 2)
        else:
            gb.run(1)
        now = list(gb.read("patron_state", 16))
        v = gb.read("patron_variant", 16)
        new = [v[i] & 7 for i in pend]            # (read a frame after the slot filled: the frame can end inside add_patron, with the state set and the variant not yet)
        pend = [i for i in range(16) if now[i] and not before[i]]
        lv, last_lv, sp, last_sp = gb.mem("lives"), lv, gb.mem("spawned"), sp
        if resync and (lv < last_lv or len(new) > 1 or sp + 1 < last_sp):   # (the start patrons, all placed on one frame, after a lost life, or the count taken back)
            runs.append(looks)
            looks, quiet = [], fr + 4
        if resync and fr < quiet:
            continue
        looks += new
    return runs + [looks]


def check_window(runs, boss=False):
    looks = [k for r in runs for k in r]
    assert len(looks) >= 100, len(looks)
    for r in runs:
        for i, k in enumerate(r):
            assert k not in r[max(0, i - WINDOW):i], (i, r[max(0, i - 6):i + 1])
    assert len(set(looks)) >= (6 if boss else 7), "every allowed look comes up: %s" % sorted(set(looks))


@pytest.mark.parametrize("model", ["cgb"])
@pytest.mark.parametrize("c", [0, 1, 4, 7])      # the Saloon (chapter 0) and generated venues
def test_no_look_repeats_within_three_spawns(model, c):
    with to_chapter(model, c) as gb:
        assert gb.mem("cur_group") == c
        run_until(gb, lambda: state(gb) == PLAYING and gb.mem("intro_timer") == 0, 300)
        h = [k for k in gb.read(gb.addr("story_scratch") + HIST_AT, 3) if k != 255]    # (the start patrons, placed after start_level cleared the history, are distinct looks too)
        assert len(set(h)) == len(h) and all(k < 8 for k in h), h
        check_window(record(gb, 30000))


@pytest.mark.parametrize("model", ["cgb"])
@pytest.mark.parametrize("c", [0, 1])
def test_no_look_repeats_within_three_spawns_in_a_boss_fight(model, c):
    with fight(model, c) as gb:
        assert gb.mem("boss_on")
        check_window(record(gb, 30000), boss=True)


# The DMG's spawn sequence for the fixed test seed, taken from the build before the rule (GB_ROM=that build): the DMG path is unchanged.
DMG_SEQ = {
    0: [0, 1, 0, 2, 0, 1, 1, 1, 2, 0, 0, 0, 1, 1, 2, 1, 0, 1, 1, 1, 2, 0, 1, 0, 0, 1, 0, 0, 0, 2, 1, 1, 1, 0, 0, 2, 1, 1, 0, 2],
    1: [1, 2, 1, 2, 1, 2, 1, 1, 0, 2, 2, 0, 1, 2, 2, 2, 1, 0, 2, 1, 0, 1, 2, 2, 1, 0, 0, 2, 0, 0, 1, 0, 0, 2, 0, 2, 0, 0, 0, 1, 1],
}


@pytest.mark.parametrize("model", ["dmg"])
@pytest.mark.parametrize("c", [0, 1])
def test_the_dmg_spawn_sequence_for_the_fixed_seed_is_unchanged(model, c):
    with to_chapter(model, c) as gb:
        run_until(gb, lambda: state(gb) == PLAYING and gb.mem("intro_timer") == 0, 300)
        got = record(gb, 3000, resync=False)[0]
    assert got[:len(DMG_SEQ[c])] == DMG_SEQ[c] and len(got) >= len(DMG_SEQ[c]), got   # (the DMG still repeats a look back to back)
