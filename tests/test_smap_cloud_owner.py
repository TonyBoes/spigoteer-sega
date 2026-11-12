# The clouds' cl_off() (src/smap_cloud.c) hides the pool (OAM 3-18) and OAM 39; smap_pal_back() and leave() call it as the map is left. CL_ON is OAM 39's x byte, which another screen
# (a boss fight, the Boss Rush, a mini-game) may leave non-zero or use as a sprite, so cl_off must act only while the map owns the OAM: src/smap.c cloud_gone() tests smap_flags F_PALS (set
# by smap_enter on a Color, cleared by the first screen after the map). Here junk sits in OAM 39 and in OAM 3-18 on those screens while they change (smap_pal_back runs on every screen
# change) and cl_off is never entered; on the map's own exit it is (the control: the hook works).
import re

import pytest
import test_story_map as sm
from conftest import ROOT, double_speed
from test_flow import PLAYING, run_until, state
from test_pause import open_pause, quit_yes
import test_rush as rs


def hook_cl_off(gb):
    noi = (ROOT / "build" / "game.noi").read_text()
    v = int(re.search(r"DEF _cl_off (0x[0-9A-F]+)", noi).group(1), 16)
    hits = []
    gb.pb.hook_register(v >> 16, v & 0xFFFF, lambda ctx: hits.append(1), None)
    return hits


def junk(gb):
    so = gb.addr("shadow_OAM")
    gb.pb.memory[so + 39 * 4 + 1] = 0x77                          # OAM 39's x: "the clouds are on" to a careless reader
    for i in range(3, 19):
        for k, v in enumerate((200 + i, 40 + i, 90 + i, 0x01)):
            gb.pb.memory[so + i * 4 + k] = v


def test_cl_off_never_runs_on_a_boss_fight_or_the_boss_rush_screens():
    """The Boss Rush list, a rush fight (a boss fight), its pause and the quit: junk in OAM 39 and 3-18 throughout; cl_off is not entered."""
    with double_speed():
        gb = rs.booted("cgb")
        hits = hook_cl_off(gb)
        rs.to_list(gb)
        junk(gb)
        rs.tap(gb, "a")
        rs.into_fight(gb, entered=False)
        junk(gb)
        gb.run(40)
        open_pause(gb)
        junk(gb)
        quit_yes(gb)
        junk(gb)
        gb.run(60)
        assert not hits, "cl_off ran on a screen that is not the map"


def test_cl_off_runs_when_the_map_is_left():
    """The control: leaving the map to a venue (smap_pal_back / leave) does enter cl_off."""
    with double_speed():
        gb = sm.to_map("cgb", 0, stop=0)
        hits = hook_cl_off(gb)
        sm.tap(gb, "a", 2)
        gb.run(40)
        assert hits, "cl_off was not entered when the map was left"
