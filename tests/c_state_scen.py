# The scenarios of the timing-independent asm/C check (tests/c_state_rig.py, tests/test_c_state_equiv.py). A scenario runs on ONE ROM (the one
# GB_ROM names: the worker tests/c_state_worker.py is started once per ROM) and returns that run's per-step states. Each one starts from a
# natural flow with the other tests' helpers (the real input passes through until the scenario's start condition holds), then a scripted input
# takes over at the first game step where the condition is true, the same logical step in both ROMs.
import random

import c_state_rig as R
from conftest import K_ARCADE, K_BONUS, K_MINIGAMES, K_PLAY, K_STORY, ROM, menu_tap, title_pick
from gbtools import Rom

PLAYING, TITLE = 1, 0          # game_state values (src/game.h GS_*); asserted in the rig test


def random_script(seed, combos, lo=1, hi=25):
    """A script of random holds (a function of the step only, the same in both ROMs)."""
    rnd = random.Random(seed)
    segs, state = [], {"end": 0}

    def f(step, tw):
        while state["end"] <= step:
            n = rnd.randrange(lo, hi)
            segs.append((state["end"] + n, R.mask(rnd.choice(combos))))
            state["end"] += n
        for end, m in segs:
            if step < end:
                return m
    return f


PLAY_COMBOS = [(), ("left",), ("right",), ("up",), ("down",), ("a",), ("right", "a"), ("a",), ("up", "a"), ("down", "a"), ("left", "a")]
MENU_COMBOS = [(), ("a",), ("b",), ("up",), ("down",), ("left",), ("right",), ("start",), ("a",), ("down",), ("down",)]
MAP_COMBOS = [(), ("left",), ("right",), ("up",), ("down",), ("a",), ("up", "right"), ("down", "left"), ("a",), ("b",)]


def boot(model):
    rom = Rom(ROM, model)
    rom.model_name = model
    return rom


def arcade(model, level, steps, seed):
    """ARCADE from the title at `level` (the LEVEL harness, conftest.title_level), then random play."""
    rom = boot(model)
    t = rom._twin
    t.arm(random_script(seed, PLAY_COMBOS), lambda tw: tw.mem("game_state") == PLAYING, {"tip_chance": 0, "rng_state": 77, "frame_counter": 0})
    rom.run(120)
    rom.write("sa_hold", 1)
    title_pick(rom, K_PLAY, K_ARCADE, press=False)
    rom.write("title_go", level)
    menu_tap(rom, "a")
    t.run_script(steps)
    return t


def menus(model, steps, seed):
    """From the first game step after boot: random buttons on the title and whatever it leads to (menus, settings, the list, the modes)."""
    rom = boot(model)
    t = rom._twin
    t.arm(random_script(seed, MENU_COMBOS, 1, 8), lambda tw: True, {"rng_state": 5, "frame_counter": 0})
    t.run_script(steps)
    return t


def boss(model, c, steps, seed):
    """The Last call of venue chapter c won, the level turned into his fight in place (tests/boss_common.fight); random play from his first move."""
    from boss_common import BS_WALK, fight
    R.ARM_NEXT.append((random_script(seed, PLAY_COMBOS), lambda tw: tw.mem("boss_on") == 1 and tw.mem("boss_state") == BS_WALK and tw.mem("intro_timer") == 0x30, {"tip_chance": 0, "frame_counter": 0}))
    gb = fight(model, c)
    t = gb._twin
    t.run_script(steps)
    return t


SCENARIOS = {}


def scenario(name):
    def deco(fn):
        SCENARIOS[name] = fn
        return fn
    return deco


for _lv in (1, 2, 4, 7, 9):
    SCENARIOS["arcade%d" % _lv] = (lambda lv: lambda model: arcade(model, lv, 2500, 11 + lv))(_lv)
SCENARIOS["menus"] = lambda model: menus(model, 1500, 3)
for _c in (0, 3, 6):
    SCENARIOS["boss%d" % _c] = (lambda c: lambda model: boss(model, c, 1500, 21 + c))(_c)
SCENARIOS["arcade1_alt"] = lambda model: arcade(model, 1, 2500, 99)      # (the sensitivity check: another script)


def minigame(model, k, steps, seed):
    """BONUS > MINI GAMES, the k-th game of the list, then random play (the card's own buttons included)."""
    from test_mg_list import to_list, tap
    GS_MINI = 13
    rom = boot(model)
    t = rom._twin
    t.arm(random_script(seed, PLAY_COMBOS + [("a",), ("b",), ("start",)], 1, 20), lambda tw: tw.mem("game_state") == GS_MINI,
          {"rng_state": 9, "frame_counter": 0})
    rom.run(120)
    rom.write("sa_hold", 1)
    to_list(rom)
    for _ in range(k):
        tap(rom, "down")
    tap(rom, "a")
    t.run_script(steps)
    return t


PAUSE_COMBOS = [(), ("start",), ("a",), ("b",), ("down",), ("up",), ("right",), ("left", "a"), (), ("start",), ("down",), ("a",), ("b",)]


def paused(model, c, steps, seed):
    """A boss fight with START, A, B, UP, DOWN mashed: the pause menu, his hint card (the fades that block the main loop), RESUME, QUIT."""
    from boss_common import BS_WALK, fight
    R.ARM_NEXT.append((random_script(seed, PAUSE_COMBOS, 1, 10), lambda tw: tw.mem("boss_on") == 1 and tw.mem("boss_state") == BS_WALK
                       and tw.mem("intro_timer") == 0x30, {"tip_chance": 0, "frame_counter": 0}))
    gb = fight(model, c)
    t = gb._twin
    t.run_script(steps)
    return t


for _c in (1, 4):
    SCENARIOS["pause%d" % _c] = (lambda c: lambda model: paused(model, c, 1200, 60 + c))(_c)
for _k in (0, 2, 4, 6, 8, 10, 12):
    SCENARIOS["mg%d" % _k] = (lambda k: lambda model: minigame(model, k, 1200, 40 + k))(_k)
