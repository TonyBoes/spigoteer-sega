# M1: bar scene + bartender movement. Every assertion reads a named variable
# from build/game.noi; every test runs on DMG and CGB (see conftest.gb).
from conftest import check_golden

pytestmark = __import__("pytest").mark.timeout(60)

TAP_X, LEFT_LIMIT = 144, 16


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
    assert gb.mem("bartender_x") == TAP_X - 20, "2 px per frame"
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
    assert gb.mem("bartender_frame") == 0
    seen = []
    gb.hold("left")
    for _ in range(24):
        gb.run(1)
        seen.append(gb.mem("bartender_frame"))
    gb.release("left")
    assert set(seen) == {1, 2}, seen
    assert seen[:8] == [1] * 8 and seen[8:16] == [2] * 8 and seen[16:24] == [1] * 8, seen
    gb.run(2)
    assert gb.mem("bartender_frame") == 0, "idle when still"


def test_bar_change_snaps_to_tap(gb):
    gb.press("left", 30)
    assert gb.mem("bartender_x") == TAP_X - 60
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
        assert max(s["y"] - 16 for s in spr) == (3 + 4 * b) * 8 + 16, "bottom entry row"
        assert min(s["y"] - 16 for s in spr) == (3 + 4 * b) * 8
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
    assert gb.mem("bar") == 2 and gb.mem("bartender_x") == TAP_X - 40
    check_golden(gb, "walking")
