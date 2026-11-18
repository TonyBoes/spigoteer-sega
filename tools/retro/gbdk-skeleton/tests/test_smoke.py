# Same behaviours as the nes/gameboy skeletons, same numbers, on every target: the game logic
# is identical, only the hardware layer differs. Every assertion reads a label
# from build/<target>/game.noi, so renaming a variable breaks a test instead of passing.
import pytest
from conftest import check_golden

pytestmark = pytest.mark.timeout(60)


def test_boots_to_spawn(rom):
    assert not rom.is_blank(), "nothing drawn"
    assert rom.mem("player_x") == 24 and rom.mem("player_y") == 72
    assert rom.mem("on_ground") == 1 and rom.mem("dead") == 0
    check_golden(rom, "boot")


def test_walks_right_and_left(rom):
    x0 = rom.mem("player_x")
    rom.press("right", 10)
    assert rom.mem("player_x") == x0 + 10, "1 px per frame"
    rom.press("left", 5)
    assert rom.mem("player_x") == x0 + 5
    assert rom.mem("facing") == 1


def test_walls_stop_movement(rom):
    rom.press("left", 60)
    assert rom.mem("player_x") == 8, "stopped by the left wall tile"


def test_jump_rises_then_lands(rom):
    y0 = rom.mem("player_y")
    rom.hold("a")
    rom.run(12)
    assert rom.mem("player_y") < y0 - 8, "rising"
    assert rom.mem("on_ground") == 0
    rom.release("a")
    rom.run(60)
    assert rom.mem("player_y") == y0 and rom.mem("on_ground") == 1, "landed back where it started"


def test_variable_jump_height(rom):
    y0 = rom.mem("player_y")
    rom.press("a", 2); rom.run(20)
    short = max(0, y0 - rom.mem("player_y"))
    rom.run(60)
    rom.hold("a"); rom.run(22); rom.release("a")
    tall = y0 - rom.mem("player_y")
    assert tall > short, f"held jump ({tall}) should go higher than a tap ({short})"


def test_walking_off_ledge_falls_to_floor(rom):
    rom.press("right", 40)
    rom.run(60)
    assert rom.mem("player_y") == 120 and rom.mem("on_ground") == 1
    check_golden(rom, "fell")


def test_hazard_kills(rom):
    rom.press("right", 40); rom.run(60)
    assert rom.mem("dead") == 0
    rom.press("right", 15); rom.run(2)
    assert rom.mem("dead") == 1
