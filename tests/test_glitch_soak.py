"""The glitch hunt (owner 2026-11-01: "go ahead and hunt for them"): every frame of a soak on every venue is checked against what the game's own state says belongs on the
screen (tests/glitch_lib.py: the bars' cells, the rows outside them, the sprites), not against a golden and not on chosen frames. The two bugs the owner saw
(a turned patron's attributes; the palette chain in fades) were both missed by tests that looked at chosen frames.

What the soak does (tests/glitch_soak.py): the game's own spawns, walks, drinks, push-backs and exits, plus a seeded stream of served mugs (pushes through the patrons
behind, lifts and drops on overlap), tips and the shows after them (and their ends), spaced groups of patrons put on a bar, and the pause card. Color runs at double speed
(the shipped mode) with junk in the shadow rows. Mirrored (R) bars, the boss entrance and fight, and the Saloon's Color-only looks are in too (the Saloon is venue 0; the other
venues' extra looks are drawn as they come). The fades are test_fade_chain.py's every-frame check.

The bugs it found (each fails here on the build before the fixes: GB_ROM=<that ROM>; the EXTRA seeds are the ones that showed them):
  1. Color: the chooser's flag changes (md_g, the one-patron path of choose_bar) composed tiles without attributes: a patron's 3rd column, or a wall tile, stood in the wrong palette until
     the next compose of its columns (venue 5 seed 1, venue 1 seed 7, venue 4 seed 13)
  2. Color: a step to shift 1 of a patron who overlaps another (OVL_TOP) was a tiles-only quick redraw, his new 3rd column was the other's cell: its attribute stayed the other's for
     40 frames and more (venue 3 seed 10): such a step now goes through a span, like his step to shift 0
  3. Color: a lifted patron dropping onto the BG (begin_drop / force_drop) was redrawn tiles-only until the chooser had flagged the overlap
  4. limit, not fixed: a span chunk is refused whole when the frame's budget cannot take its full width, bar 0 first: a turned or arriving patron on a crowded bar waits up to ~30 frames
     (LATE below). Serving the bars in turn broke the boss tests' bar order, narrower chunks fail the DMG perf guards.
Left alone (class A lasts up to LAG_A frames): a cell in the wrong attribute for a few frames while a quick redraw and the chunked span of the same patron cross.

RUN_SLOW=1 runs the long set (more seeds, more frames).
"""
import contextlib
import os
import collections

import pytest
from conftest import double_speed
from glitch_lib import Watch
from glitch_soak import Soak, boot
from test_story import to_shift, to_boss_banner, to_goal

SLOW = bool(os.environ.get("RUN_SLOW"))
pytestmark = pytest.mark.timeout(900)

LATE = {"cgb": 40, "dmg": 10 ** 6}      # (class B: a redraw this many frames late; a DMG's frames run late far more often, its late redraws are not judged here)
FRAMES = 2400
SEEDS = [1, 2]
EXTRA = [(1, 7), (3, 10), (4, 13)]       # (seeds that found a bug on the build before the fixes: 1/2/3 each name a venue and a seed in the table of bugs above)


def check(gb, w, model):
    late = LATE[model]
    bad = [f for f in w.found if not (f[1] == "B-late" and f[2]["frames"] < late) and not (f[1] == "B-late" and model == "dmg")]
    assert not bad, ("picture glitches (frame, kind, detail)", len(bad), collections.Counter(f[1] for f in bad), bad[:6])
    if model == "cgb":
        assert w.max_streak <= late, ("a cell stayed wrong for", w.max_streak, "frames")


@pytest.mark.parametrize("model", ["cgb", "dmg"])
@pytest.mark.parametrize("group,seed", [(g, sd) for g in range(10) for sd in SEEDS] + EXTRA)
def test_every_frame_of_a_soak_on_a_venue_shows_only_what_belongs(model, group, seed):
    gb = boot(model, group, seed)
    try:
        w = Soak(gb, seed).run(FRAMES)
        assert w.frames_checked >= FRAMES
        check(gb, w, model)
    finally:
        gb.stop()


@pytest.mark.parametrize("model", ["cgb", "dmg"])
@pytest.mark.parametrize("dirs,group", [(0xF, 0), (0x5, 3), (0xA, 5), (0x3, 8)])
def test_every_frame_of_a_soak_on_mirrored_bars_shows_only_what_belongs(model, dirs, group):
    gb = boot(model, group, 3, dirs=dirs)
    try:
        w = Soak(gb, 3).run(FRAMES)
        check(gb, w, model)
    finally:
        gb.stop()


@pytest.mark.parametrize("model", ["cgb", "dmg"])
@pytest.mark.parametrize("c", range(10))
def test_every_frame_of_a_boss_entrance_and_fight_shows_only_what_belongs(model, c):
    cm = double_speed() if model == "cgb" else contextlib.nullcontext()
    with cm:
        gb = to_shift(model, c, 2)
    try:
        gb.run(5)
        w = Watch(gb)
        to_boss_banner(gb, c)
        w.adopt_ghosts()                    # (the test's own clear_bars leaves the served patrons' figures in the map)
        w.step(300)
        to_goal(gb)
        Soak(gb, c, events=("serve", "pause"), watch=w).run(1200)
        assert gb.mem("boss_on")
        check(gb, w, model)
    finally:
        gb.stop()


@pytest.mark.skipif(not SLOW, reason="the long soak: RUN_SLOW=1")
@pytest.mark.parametrize("model", ["cgb", "dmg"])
@pytest.mark.parametrize("group", range(10))
def test_the_long_soak(model, group):
    for seed in range(10, 16):
        gb = boot(model, group, seed)
        try:
            w = Soak(gb, seed).run(12000)
            check(gb, w, model)
        finally:
            gb.stop()
