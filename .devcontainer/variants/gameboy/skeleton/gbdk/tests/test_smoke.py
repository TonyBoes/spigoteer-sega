# The smallest useful test set. Every assertion reads a named variable from
# build/game.noi, so renaming a global breaks a test instead of silently
# passing. Add a test for every behaviour you add.
from conftest import check_golden

pytestmark = __import__("pytest").mark.timeout(60)


def test_boots_to_spawn(gb):
    assert not gb.is_blank(), "nothing drawn"
    assert gb.mem("player_x") == 24 and gb.mem("player_y") == 72
    assert gb.mem("on_ground") == 1
    assert gb.mem("dead") == 0
    assert len(gb.visible_sprites()) == 1, "one 8x16 OAM entry"
    check_golden(gb, "boot")


def test_walks_right_and_left(gb):
    x0 = gb.mem("player_x")
    gb.press("right", 10)
    assert gb.mem("player_x") == x0 + 10, "1 px per frame"
    gb.press("left", 5)
    assert gb.mem("player_x") == x0 + 5
    assert gb.mem("facing") == 1


def test_walls_stop_movement(gb):
    gb.press("left", 60)
    assert gb.mem("player_x") == 8, "stopped by the left wall tile"


def test_jump_rises_then_lands(gb):
    y0 = gb.mem("player_y")
    gb.hold("a")
    gb.run(12)
    assert gb.mem("player_y") < y0 - 8, "rising"
    assert gb.mem("on_ground") == 0
    gb.release("a")
    gb.run(60)
    assert gb.mem("player_y") == y0 and gb.mem("on_ground") == 1, "landed back where it started"


def test_variable_jump_height(gb):
    y0 = gb.mem("player_y")
    gb.press("a", 2); gb.run(20)
    short = y0 - gb.mem("player_y") if gb.mem("player_y") < y0 else 0
    gb.run(60)
    gb.hold("a"); gb.run(22); gb.release("a")
    tall = y0 - gb.mem("player_y")
    assert tall > short, f"held jump ({tall}) should go higher than a tap ({short})"


def test_walking_off_ledge_falls_to_floor(gb):
    gb.press("right", 40)
    gb.run(60)
    assert gb.mem("player_y") == 120 and gb.mem("on_ground") == 1
    check_golden(gb, "fell")


def test_hazard_kills(gb):
    gb.press("right", 40); gb.run(60)      # off the ledge, on the floor, left of the spikes
    assert gb.mem("dead") == 0
    gb.press("right", 15); gb.run(2)
    assert gb.mem("dead") == 1
