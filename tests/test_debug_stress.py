# The debug menu's STRESS mode (src/debug.c, DEBUG_MENU builds; owner 2026-10-28): the automated perf scenarios' worst cases as a selection, to feel
# on a phone or a cart. MODE > STRESS, PEAK: SPACE (level 10, 10 patrons), CLASSIC (CLASSIC level 12, 16), ARCADE (chapter 10 loop 4 Last call, level 40, 10).
# The run keeps the crowd at the target with the game's own spawning (patrons.c try_spawn); the player plays as usual and can lose.
import os

import pytest
from conftest import gesture, release_gesture, unlock_debug
import perf_helpers as ph
from test_debug import tap, goto, line, DEBUG, PLAYING, TITLE, MODE_CLASSIC, MODE_LEVEL, MODE_ARCADE, SAVE_LOCK_DEBUG
from test_flow import state, run_until
from test_story import to_goal

pytestmark = pytest.mark.timeout(300)
FRAMES = 1200
WALKING = 1
# peak index: (name, target patrons, play_mode, the level the run starts at, debug_from_title's bits 1-2)
CASES = [("SPACE", 10, MODE_LEVEL, 10, 1), ("CLASSIC", 16, MODE_CLASSIC, 12, 2), ("ARCADE", 10, MODE_ARCADE, 40, 3)]


def open_menu(gb):
    unlock_debug(gb)
    gesture(gb)
    release_gesture(gb)
    gb.run(3)


def start_stress(gb, idx):
    """MODE > STRESS (Left from LEVEL wraps to the last mode), PEAK on idx, A; run to the first frame of play."""
    open_menu(gb)
    goto(gb, 0)
    tap(gb, "left")
    assert line(gb, 2) == ("MODE", "STRESS")
    goto(gb, 1)
    for _ in range(idx):
        tap(gb, "right")
    assert line(gb, 4) == ("PEAK", CASES[idx][0])
    gb.press("a", 2)
    if CASES[idx][2] == MODE_ARCADE:                          # (the goal banner first: test_story.to_goal turns it)
        to_goal(gb)
        for _ in range(220):
            if state(gb) == PLAYING:
                break
            gb.run(1)
    run_until(gb, lambda: state(gb) == PLAYING, 300)
    gb.run(3)                                                 # (the menu's start returns a moment after the game state turned)
    gb.write("tip_chance", 0)


@pytest.mark.only_model('dmg')
@pytest.mark.parametrize("idx", range(3))
def test_the_stress_selection_starts_its_level_and_mode(boot, idx):
    name, target, mode, lv, bits = CASES[idx]
    start_stress(boot, idx)
    assert boot.mem("play_mode") == mode and boot.mem("level") == lv
    assert boot.mem("debug_from_title") >> 1 == bits and boot.mem("save_lock") == SAVE_LOCK_DEBUG
    assert boot.mem("debug_menu_open") == 0 and boot.mem("game_state") == PLAYING
    if mode == MODE_ARCADE:
        assert boot.mem("story_on") == 1 and boot.mem("arc_loop") == 4 and boot.mem("story_chapter") == 9
    if mode == MODE_LEVEL:
        assert boot.mem("level_dirs") & 0x3F == 0
    if mode == MODE_CLASSIC:
        assert boot.mem("bar_dirs") == 0x5


@pytest.mark.parametrize("idx", range(3))
def test_the_crowd_stays_at_its_target_with_an_idle_player(boot, idx):
    """1200 frames, nobody plays: spawns keep the patron count at the target (the scenario's own nudge keeps walkers off the tap, as
    perf_helpers.RealisticPeak: a lost life would clear the bars)."""
    name, target, mode, lv, bits = CASES[idx]
    start_stress(boot, idx)
    gb = boot
    taps = list(gb.read("bar_tap", 4))
    ph.perf_reset(gb)
    counts, hurried = [], set()
    for i in range(FRAMES):
        gb.write("lives", 3)
        st, bar, xs = gb.read("patron_state", ph.MAX_P), gb.read("patron_bar", ph.MAX_P), gb.read("patron_x", ph.MAX_P)
        for p in range(ph.MAX_P):
            if st[p] == WALKING and xs[p] >= taps[bar[p] & 3] - 12:
                ph.put(gb, "patron_x", p, taps[bar[p] & 3] - 24)
        gb.run(1)
        ph.sample(gb)
        st = gb.read("patron_state", ph.MAX_P)
        counts.append(sum(1 for v in st if v))
        hurried |= {p for p, v in enumerate(gb.read("patron_hurry", ph.MAX_P)) if v and st[p]}
    r = ph.perf_read(gb)
    steady = counts[400:]
    mean = sum(steady) / len(steady)
    print(rom_name(gb), "stress", name, "patrons mean", round(mean, 1), "min", min(steady), "max", max(counts), r, "hurried", len(hurried), flush=True)
    assert gb.mem("game_state") == PLAYING and gb.mem("lives") >= 1
    assert max(counts) <= target + 2, counts
    assert min(steady) >= target // 2 and mean >= 0.8 * target, (min(steady), mean)
    assert len(hurried) >= 1


def rom_name(gb):
    return getattr(gb, "model_name", "?")


@pytest.mark.only_model('dmg')
def test_a_plain_start_or_the_title_ends_the_stress_run(boot):
    start_stress(boot, 0)
    assert boot.mem("debug_from_title") >> 1 == 1
    open_menu(boot)                                           # (the menu opened in play keeps the run's bits while it is open ...)
    assert boot.mem("debug_from_title") >> 1 == 1 and boot.mem("debug_from_title") & 1 == 0
    goto(boot, 0)
    tap(boot, "right")                                        # (LEVEL -> STORY wraps over; any other mode's start clears them)
    tap(boot, "left")
    assert line(boot, 2) == ("MODE", "LEVEL")
    boot.press("a", 2)
    run_until(boot, lambda: state(boot) == PLAYING, 300)
    assert boot.mem("debug_from_title") >> 1 == 0 and boot.mem("level") == 1
