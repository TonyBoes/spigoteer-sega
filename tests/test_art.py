# M8b: the owner-approved art (3/4-view patrons, back views) in every patron group, on both models.
import pytest
from conftest import check_golden
from test_flow import PLAYING, run_until, state
from test_patrons import BACK_BASE, MAX_P, drawn_tiles, lineup, map_ids

pytestmark = pytest.mark.timeout(60)

GROUPS = ["cowboys", "sports", "lumberjacks", "chefs", "divers", "robots", "punks", "ninjas", "zoo", "aliens"]
GS_LEVEL_CLEAR = 3
GS_BONUS = 6


def w16(gb, name, v):
    gb.write(name, v & 255)
    gb.write(gb.addr(name) + 1, v >> 8)


def goto_group(gb, group):
    """Level group + 1, the first loop's level of patron group `group` ((level - 1) % 10). An odd level before it is
    left from its last level-clear frame; an even one (followed by a bonus round) from the bonus round's last frame.
    (Before M10b an even level was reached as group + 10, which had the same speeds then; it is loop 2 now.)"""
    level = group + 1
    gb.write("level", level - 1)
    if group % 2:
        gb.write("game_state", GS_LEVEL_CLEAR)
        gb.write("state_timer", 149)
    else:
        gb.write("bonus_kind", 0)
        gb.write("bonus_phase", 4)
        gb.write("bonus_timer", 129)
        gb.write("game_state", GS_BONUS)
    gb.run(1)
    run_until(gb, lambda: state(gb) == PLAYING, 30)
    assert gb.mem("cur_group") == group and gb.mem("level") == level


# bar: [(x, variant, distracted)]: fronts at shift 0 and at odd shifts, and the three back views on bar 3 (the first
# column from ENTRY_X: left of it patrons are only sprites, entering or leaving).
LINEUP = {
    0: [(16, 0, 0), (40, 1, 0), (80, 2, 0)],
    1: [(29, 0, 0), (51, 1, 0), (93, 2, 0)],
    2: [(20, 2, 0), (45, 0, 0), (86, 1, 0)],
    3: [(24, 0, 1), (48, 1, 1), (88, 2, 1)],
}


@pytest.mark.parametrize("group", range(len(GROUPS)), ids=GROUPS)
def test_patrons_golden_per_group(gb, group):
    goto_group(gb, group)
    gb.write("tip_chance", 0)
    gb.write("intro_timer", 255)                 # nobody walks
    gb.write("quota", 200)
    w16(gb, "spawn_timer", 0xFFFF)
    spec = LINEUP
    if group == 0 and gb.model_name == "cgb":    # the Color Saloon's GUS wears his own palette, instance 0 (his tiles' colours 1 and 2 are swapped)
        spec = {b: [(x, 2 | 2 << 3 if v == 2 else v, d) for x, v, d in row] for b, row in LINEUP.items()}
    slots = lineup(gb, spec)
    gb.run(30)                                   # 12 redraws: the VBlank budget spreads them over a few frames
    for (b, x), (i, v, d) in slots.items():
        v &= 7
        if d:
            assert gb.read("patron_facing", MAX_P)[i] == 1
            t = BACK_BASE + v * 4
            assert [r[:2] for r in map_ids(gb, b, x >> 3)] == [[t, t + 1], [t + 2, t + 3]]
        else:
            col, ids = drawn_tiles(v, x, b)
            assert map_ids(gb, b, col) == ids
    check_golden(gb, f"patrons_{GROUPS[group]}")
