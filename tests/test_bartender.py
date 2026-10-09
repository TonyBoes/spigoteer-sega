# M1: bar scene + bartender movement. Every assertion reads a named variable
# from build/game.noi; every test runs on DMG and CGB (see conftest.gb).
from conftest import GAME, LAYOUT, bar_top_y, check_golden

pytestmark = __import__("pytest").mark.timeout(60)

TAP_X, LEFT_LIMIT = GAME["TAP_X"], GAME["LEFT_LIMIT"]     # M8a: the fill position, just left of the spout (120)


def test_boots(gb):
    assert not gb.is_blank(), "nothing drawn"
    assert gb.mem("bar") == 0
    assert gb.mem("bartender_x") == TAP_X
    assert gb.mem("at_tap") == 1
    assert gb.mem("facing") == 0
    assert gb.mem("bartender_frame") == 0, "idle"
    assert len(gb.visible_sprites()) == 4, "bartender is 4 OAM entries"
    check_golden(gb, "scene")


def test_down_walks_bars_and_wraps(gb):
    for expected in (1, 2, 3, 0):
        gb.press("down", 2)
        assert gb.mem("bar") == expected
        assert gb.mem("bartender_x") == TAP_X


def test_up_wraps_to_bottom_bar(gb):
    gb.press("up", 2)
    assert gb.mem("bar") == 3
    gb.press("up", 2)
    assert gb.mem("bar") == 2


def test_up_down_is_edge_triggered(gb):
    gb.hold("down")
    gb.run(30)
    gb.release("down")
    assert gb.mem("bar") == 1, "holding down moves one bar only"


def test_walk_left_and_right(gb):
    gb.press("left", 10)
    assert gb.mem("bartender_x") == TAP_X - 15, "1.5 px per frame"
    assert gb.mem("facing") == 0
    assert gb.mem("at_tap") == 0
    gb.press("right", 10)
    assert gb.mem("bartender_x") == TAP_X
    assert gb.mem("facing") == 1
    assert gb.mem("at_tap") == 1


def test_clamped_at_both_ends(gb):
    gb.press("left", 100)
    assert gb.mem("bartender_x") == LEFT_LIMIT
    gb.press("left", 5)
    assert gb.mem("bartender_x") == LEFT_LIMIT
    gb.press("right", 100)
    assert gb.mem("bartender_x") == TAP_X
    gb.press("right", 5)
    assert gb.mem("bartender_x") == TAP_X


def test_walk_animation_alternates(gb):
    """M8a: a calmer cycle, walk1, idle, walk2, idle, 10 frames each."""
    assert gb.mem("bartender_frame") == 0
    seen = []
    gb.hold("left")
    for _ in range(50):
        gb.run(1)
        seen.append(gb.mem("bartender_frame"))
    gb.release("left")
    n = GAME["WALK_STEP_FRAMES"]
    assert n == 10
    assert seen[:4 * n] == [1] * n + [0] * n + [2] * n + [0] * n, seen
    assert seen[4 * n:5 * n] == [1] * n, "and around again"
    gb.run(2)
    assert gb.mem("bartender_frame") == 0, "idle when still"


def test_bar_change_snaps_to_tap(gb):
    gb.press("left", 30)
    assert gb.mem("bartender_x") == TAP_X - 45
    gb.press("up", 2)
    assert gb.mem("bar") == 3
    assert gb.mem("bartender_x") == TAP_X
    assert gb.mem("facing") == 0
    gb.press("right", 1)  # facing right, then snap again
    gb.press("down", 2)
    assert gb.mem("facing") == 0


def test_bartender_sprite_position(gb):
    for b in range(4):
        spr = gb.visible_sprites()
        xs = sorted({s["x"] - 8 for s in spr})
        assert xs == [TAP_X, TAP_X + 8]
        assert max(s["y"] - 16 for s in spr) == bar_top_y(b) + 16, "bottom entry row"
        assert min(s["y"] - 16 for s in spr) == bar_top_y(b), "top entry row: 24 px tall, feet on the counter row"
        gb.press("down", 2)


def test_facing_right_flips_sprite(gb):
    gb.press("left", 20)
    gb.press("right", 5)
    spr = gb.visible_sprites()
    assert all(s["flags"] & 0x20 for s in spr), "X-flip when facing right"
    gb.press("left", 5)
    assert not any(s["flags"] & 0x20 for s in gb.visible_sprites())


def test_at_most_10_sprites_per_scanline(gb):
    for b in range(4):
        for walk in ("left", "right"):
            gb.press(walk, 12)
            counts = [0] * 144
            for s in gb.visible_sprites():
                top = s["y"] - 16
                for line in range(max(top, 0), min(top + 16, 144)):
                    counts[line] += 1
            assert max(counts) <= 2, f"bartender must use at most 2 entries per line, got {max(counts)}"
            assert max(counts) <= 10
        gb.press("down", 2)


def test_walking_golden(gb):
    gb.press("down", 2)
    gb.press("down", 2)
    gb.press("left", 20)
    assert gb.mem("bar") == 2 and gb.mem("bartender_x") == TAP_X - 30
    check_golden(gb, "walking")


# ---- M4.6 layout: HUD row, stage rows 1-4, three-row bars, floor ------------------------
import re as _re
from conftest import ROOT as _ROOT, bar_counter_row, bar_top_row, mug_top_y

_ART_H = (_ROOT / "build" / "art.h").read_text()


def _tile(name):
    return int(_re.search(rf"#define TILE_{name} (\d+)", _ART_H).group(1))


def _row(gb, y, x0=0, n=20):
    return [t & 0xFF for t in gb.bg_tilemap()[y][x0:x0 + n]]


def test_bars_have_their_counter_rows_at_the_layout_rows(gb):
    assert [bar_counter_row(b) for b in range(4)] == [7, 10, 13, 16], "layout.h: bars at rows 5+3b..7+3b"
    for b in range(4):
        assert _row(gb, bar_counter_row(b), 0, 18) == [_tile("COUNTER")] * 18, f"bar {b} counter row (M8a: from column 0)"
        assert _row(gb, bar_counter_row(b), 18, 2) == [_tile("TAP") + 4, _tile("TAP") + 5]
        assert _tile("COUNTER") not in _row(gb, bar_top_row(b), 0, 18) + _row(gb, bar_top_row(b) + 1, 0, 18)
    assert _row(gb, LAYOUT["FLOOR_ROW"]) == [_tile("FLOOR")] * 20


def test_stage_rows_hold_the_sign_and_the_platform_edge(gb):
    first, last = LAYOUT["STAGE_FIRST_ROW"], LAYOUT["STAGE_LAST_ROW"]
    assert (LAYOUT["HUD_ROW"], first, last, LAYOUT["BAR_FIRST_ROW"]) == (0, 1, 4, 5)
    assert _row(gb, first, 7, 6) == [_tile("SIGN") + i for i in range(6)], "sign centred (cols 7-12)"
    assert _row(gb, first + 1, 7, 6) == [_tile("SIGN") + 6 + i for i in range(6)]
    assert _row(gb, last, 2, 16) == [_tile("STAGE_EDGE")] * 16, "platform edge"
    assert _row(gb, first)[0] == _tile("CURTAIN_L0") and _row(gb, first)[19] == _tile("CURTAIN_R1")


def test_no_sprites_on_the_stage_rows_during_play(gb):
    stage_bottom = (LAYOUT["STAGE_LAST_ROW"] + 1) * 8        # first pixel row below the stage
    hud_bottom = (LAYOUT["HUD_ROW"] + 1) * 8

    def check(where):
        for s in gb.visible_sprites():
            top = s["y"] - 16
            assert top >= stage_bottom, f"{where}: sprite at y {top} overlaps the HUD/stage"
            assert top + 16 > hud_bottom

    check("idle")
    for b in range(4):
        gb.press("down", 2)
        gb.hold("a")
        gb.run(10)
        check(f"filling on bar {b}")
        gb.run(20)
        gb.release("a")
        gb.run(2)
        check(f"launched on bar {b}")
    gb.run(150)                                              # mugs slide, break, patrons walk
    check("later")
    gb.press("up", 2)
    check("walking up")
    assert mug_top_y(0) >= stage_bottom


def test_stage_golden(gb):
    gb.run(30)
    check_golden(gb, "stage")


# ---- M8a: counter to the door, the spout, walking speed ------------------------------------
def test_counter_runs_to_the_door_and_the_door_is_on_the_wall_rows_only(gb):
    door = _tile("DOOR")
    for b in (1, 3):                                          # level 1 has no patron at these doors
        assert _row(gb, bar_top_row(b), 0, 2) == [door, door + 1], f"bar {b} door, upper wall row"
        assert _row(gb, bar_top_row(b) + 1, 0, 2) == [door + 2, door + 3], f"bar {b} door, lower wall row"
    for b in range(4):
        assert _row(gb, bar_counter_row(b), 0, 2) == [_tile("COUNTER")] * 2, f"bar {b}: counter at columns 0-1"
    assert _tile("TAP") - door == 4, "the door block is 2x2 tiles (16x16): no third door row any more"


def test_spout_reaches_over_column_17_on_the_lower_wall_row(gb):
    for b in range(4):
        assert _row(gb, bar_top_row(b) + 1, 17, 1) == [_tile("SPOUT")], f"bar {b}"
        assert _row(gb, bar_top_row(b), 17, 1) == [_tile("WALL")], "the upper wall row above the spout is plain wall"
        assert _row(gb, bar_top_row(b), 18, 2) == [_tile("TAP"), _tile("TAP") + 1]
    assert GAME["SPOUT_X"] == 17 * 8 and GAME["TAP_X"] == GAME["SPOUT_X"] - 16


def test_walk_speed_is_one_and_a_half_px_per_frame(gb):
    xs = [gb.mem("bartender_x")]
    gb.hold("left")
    for _ in range(20):
        gb.run(1)
        xs.append(gb.mem("bartender_x"))
    gb.release("left")
    steps = [a - b for a, b in zip(xs, xs[1:])]
    assert sorted(set(steps)) == [1, 2] and sum(steps) == 30, steps
    assert all(a != b for a, b in zip(steps, steps[1:])), "1 and 2 px alternate"
    gb.hold("right")
    gb.run(30)
    gb.release("right")
    assert gb.mem("bartender_x") == TAP_X, "the fill position is the right end of the walk"
