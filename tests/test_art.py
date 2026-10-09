# M8b: the owner-approved art (3/4-view patrons, back views) in every patron group, on both models.
import pytest
from conftest import check_golden
from test_flow import PLAYING, run_until, state
from test_patrons import BACK_BASE, MAX_P, drawn_tiles, lineup, map_ids

pytestmark = pytest.mark.timeout(60)

GROUPS = ["cowboys", "sports", "lumberjacks", "chefs", "divers", "robots", "ninjas", "aliens", "zoo"]
GS_LEVEL_CLEAR = 3


def w16(gb, name, v):
    gb.write(name, v & 255)
    gb.write(gb.addr(name) + 1, v >> 8)


def goto_group(gb, group):
    """The level that shows patron group `group` ((level - 1) % 9), reached from a level-clear state whose level
    is odd, so no bonus round comes between."""
    level = group + 1 if group % 2 else group + 10
    gb.write("level", level - 1)
    gb.write("game_state", GS_LEVEL_CLEAR)
    gb.write("state_timer", 149)
    gb.run(1)
    run_until(gb, lambda: state(gb) == PLAYING, 30)
    assert gb.mem("cur_group") == group and gb.mem("level") == level


# bar: [(x, variant, distracted)]: fronts at shift 0 and at odd shifts, and the three back views on bar 3
LINEUP = {
    0: [(0, 0, 0), (40, 1, 0), (80, 2, 0)],
    1: [(13, 0, 0), (51, 1, 0), (93, 2, 0)],
    2: [(4, 2, 0), (45, 0, 0), (86, 1, 0)],
    3: [(8, 0, 1), (48, 1, 1), (88, 2, 1)],
}


@pytest.mark.parametrize("group", range(len(GROUPS)), ids=GROUPS)
def test_patrons_golden_per_group(gb, group):
    goto_group(gb, group)
    gb.write("tip_chance", 0)
    gb.write("intro_timer", 255)                 # nobody walks
    gb.write("quota", 200)
    w16(gb, "spawn_timer", 0xFFFF)
    slots = lineup(gb, LINEUP)
    gb.run(30)                                   # 12 redraws: the VBlank budget spreads them over a few frames
    for (b, x), (i, v, d) in slots.items():
        if d:
            assert gb.read("patron_facing", MAX_P)[i] == 1
            t = BACK_BASE + v * 4
            assert [r[:2] for r in map_ids(gb, b, x >> 3)] == [[t, t + 1], [t + 2, t + 3]]
        else:
            col, ids = drawn_tiles(v, x, b)
            assert map_ids(gb, b, col) == ids
    check_golden(gb, f"patrons_{GROUPS[group]}")
