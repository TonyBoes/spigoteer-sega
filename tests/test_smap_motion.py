"""Story map walks, Color (owner 11-09): Sal never stands still between his first and last step of a leg (every leg, both ways, at double speed as shipped), and the world-pinned sprites
(the stop dot) show at the same place against the picture on every frame: the OAM and the scroll register change in the same frame. Both failed on main before this: pauses at stop 1 down/left,
stop 7 left, stop 9 right, stop 10 right; the dot 1-2 px ahead of the scroll on 14-19 frames of the stop 0 walks (normal speed, the goldens' speed)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "dev"))
import test_story_map as sm
from conftest import double_speed
from smap_motion_check import mid_walk_stops, walk_steps

SV = sm.SV
LEGS = [(s, d) for s in range(11) for d in range(4) if sm.EXITS[s][d] != 255]


@pytest.mark.parametrize("s,d", LEGS, ids=[f"stop{s}-{sm.DIRS[d]}" for s, d in LEGS])
def test_color_walk_has_no_standing_frame_between_the_first_and_last_step(s, d):
    steps = walk_steps("cgb", s, d)
    stops = mid_walk_stops(steps)
    assert not stops, f"stop {s} {sm.DIRS[d]}: Sal moved 0 px on frames {stops}: {''.join(str(min(x, 9)) for x in steps)}"


def _dot_places(stop, d, speed):
    """(SCX + dot x, SCY + dot y) of the stop dot (OAM 8, tile 62) on every frame of a walk, as the hardware has them after the frame."""
    if speed:
        with double_speed():
            gb = sm.to_map("cgb", 10, stop=stop)
    else:
        gb = sm.to_map("cgb", 10, stop=stop)
    gb.press(sm.DIRS[d], 6)
    out, started = [], False
    for fr in range(1500):
        gb.run(1, True)
        walking = gb.read("story_scratch", 520)[SV + sm.V_WALK]
        started = started or walking
        if started:
            y, x, t, _ = gb.read(0xFE00, 160)[32:36]
            if y and t == 62 and not gb.mem("vq_ready"):          # (a frame sampled between the OAM DMA and the VBlank drain of the copy list, which sets the scroll, is skipped: the picture is drawn after both)
                out.append(((gb.mem(0xFF43) + x) & 255, (gb.mem(0xFF42) + y) & 255))
        if fr > 4 and started and not walking:
            break
    return out


@pytest.mark.parametrize("speed", [False, True], ids=["normal-speed", "double-speed"])
@pytest.mark.parametrize("stop,d", [(0, 3), (0, 2), (1, 1)])
def test_color_walk_the_stop_dot_stays_on_the_picture(stop, d, speed):
    places = _dot_places(stop, d, speed)
    assert len(places) > 30
    off = sum(1 for p in places if p[0] != places[0][0])
    assert off == 0, f"stop {stop} {sm.DIRS[d]}: the dot was off the picture sideways on {off} of {len(places)} frames"
    offy = sum(1 for p in places if p[1] != places[0][1])
    assert offy == 0, f"stop {stop} {sm.DIRS[d]}: the dot was off the picture vertically on {offy} frames"
