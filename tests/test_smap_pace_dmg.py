"""Story map walks, DMG (owner 11-11, the stutter): Sal's pace was 2,2,2,1,1,0 once per cell line on every stretch, quiet or busy (the region led the view by one line, so the next line was never
loaded in time at 2 px a frame, and walk_step paused 1 frame in 2-4).  Now each stretch loads as many lines ahead as the route plan's tile slots allow (tools/smap_world/route.py
choose_leads, smapw_leg_lead), and where the loader still cannot keep up the pace is an even cadence of 1s and 2s.  On every leg, both ways:
  - no 0 px frame between Sal's first and last step (a lone 1 at the ends is the ease);
  - the pace never changes by more than 1 px between two frames (2 -> 0 and 0 -> 2 are the stutter);
  - the lookahead is on: a quiet leg keeps a steady 2 px for most of its length (a run of 30 or more frames on the legs the plan gives 4+ lines)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "dev"))
import test_story_map as sm
from test_story_map_world import LEG_WALKS
from smap_motion_check import mid_walk_stops, walk_steps

LEGS = LEG_WALKS
QUIET = [(0, 3), (1, 2), (7, 2), (8, 3)]          # legs whose stretches the plan gives 5 or 6 lines ahead


@pytest.fixture(scope="module")
def steps():
    return {}


def _steps(cache, s, d):
    if (s, d) not in cache:
        cache[(s, d)] = walk_steps("dmg", s, d)
    return cache[(s, d)]


@pytest.mark.parametrize("s,d", LEGS, ids=[f"stop{s}-{sm.DIRS[d]}" for s, d in LEGS])
def test_dmg_walk_never_stands_still_and_the_pace_changes_by_one_at_most(steps, s, d):
    p = _steps(steps, s, d)
    stops = mid_walk_stops(p)
    txt = "".join(str(min(x, 9)) for x in p)
    assert not stops, f"stop {s} {sm.DIRS[d]}: Sal moved 0 px on frames {stops}: {txt}"
    jerks = [i for i, (a, b) in enumerate(zip(p, p[1:])) if abs(a - b) > 1]
    assert not jerks, f"stop {s} {sm.DIRS[d]}: the pace jumps by 2 px at frames {jerks}: {txt}"


@pytest.mark.parametrize("s,d", QUIET, ids=[f"stop{s}-{sm.DIRS[d]}" for s, d in QUIET])
def test_dmg_quiet_legs_keep_a_steady_two_pixels(steps, s, d):
    p = _steps(steps, s, d)
    best = run = 0
    for v in p:
        run = run + 1 if v == 2 else 0
        best = max(best, run)
    assert best >= 30, f"stop {s} {sm.DIRS[d]}: the longest run of 2 px frames is {best}: {''.join(str(min(x, 9)) for x in p)}"
