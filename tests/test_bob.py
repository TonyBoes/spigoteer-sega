# Walk bob: the bartender's sprites rise 1 px on the passing pose of the walk cycle.
import pytest

pytestmark = pytest.mark.timeout(60)


def ys(gb):
    return [s["y"] for s in gb.visible_sprites()][:4]


def test_walk_bob_is_one_pixel_in_sync_with_the_walk_frames(gb):
    rest = ys(gb)[0]
    idle_tile = gb.visible_sprites()[0]["tile"]
    for _ in range(2):                                    # idle for a while: no bob
        gb.run(10)
        assert ys(gb)[0] == rest
    gb.hold("left")
    gb.run(3)                                             # input latency
    seen = set()
    for _ in range(35):
        gb.run(1)
        y = ys(gb)
        up = rest - y[0]
        assert up in (0, 1) and y[1] == y[0] and y[2] - y[0] == 16 and y[3] == y[2]
        assert up == (gb.visible_sprites()[0]["tile"] == idle_tile), "up exactly on the passing (idle) pose of the walk"
        seen.add((gb.visible_sprites()[0]["tile"] != idle_tile, up))
    assert seen == {(False, 1), (True, 0)}, seen
    gb.release("left")
    gb.run(2)
    assert ys(gb)[0] == rest, "back at rest height when he stops"


def test_no_bob_while_filling(gb):
    rest = ys(gb)[0]
    gb.hold("a")
    for _ in range(35):
        gb.run(1)
        assert ys(gb)[0] == rest
