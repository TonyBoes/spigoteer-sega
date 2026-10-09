# Debug level select: hold START + SELECT ~30 frames (title or play) -> a banner "LEVEL nn"; Left/Right change it,
# A starts that level from scratch, B closes. Only in DEBUG_MENU builds (the normal build); `make release` has none.
import subprocess

import pytest
from conftest import ROOT

pytestmark = pytest.mark.timeout(120)

TITLE, PLAYING, PAUSED = 0, 1, 5
COMBO = 30


def combo(gb, frames=COMBO + 2):
    gb.hold("start")
    gb.hold("select")
    gb.run(frames)


def release_combo(gb):
    gb.release("start")
    gb.release("select")
    gb.run(2)


def banner_text(gb):
    return [t & 0xFF for t in gb.bg_tilemap(True)[1][:20]]


def test_the_combo_opens_the_menu_on_the_title(boot):
    combo(boot)
    assert boot.mem("debug_menu_open") == 1 and boot.mem("debug_level") == 1
    assert boot.mem("game_state") not in (TITLE, PLAYING), "paused: its own state"
    assert boot.mem("overlay_on") == 1
    release_combo(boot)
    assert boot.mem("debug_menu_open") == 1


def test_a_short_start_still_starts_the_game_and_select_still_toggles_music(boot):
    s0 = boot.mem("sound_on")
    boot.press("select", 3)
    boot.run(5)
    assert boot.mem("sound_on") == 1 - s0 and boot.mem("debug_menu_open") == 0
    boot.press("select", 3)
    boot.press("start", 2)
    boot.run(20)
    assert boot.mem("game_state") == PLAYING and boot.mem("debug_menu_open") == 0


def test_holding_the_combo_a_little_is_not_enough(boot):
    combo(boot, COMBO - 5)
    assert boot.mem("debug_menu_open") == 0
    release_combo(boot)
    boot.run(10)
    assert boot.mem("debug_menu_open") == 0 and boot.mem("game_state") == TITLE


def test_the_combo_on_the_title_does_not_leave_the_music_toggled(boot):
    s0 = boot.mem("sound_on")
    boot.hold("select")
    boot.run(2)
    boot.hold("start")
    boot.run(COMBO + 2)
    assert boot.mem("debug_menu_open") == 1
    assert boot.mem("sound_on") == s0
    release_combo(boot)


def test_left_right_change_the_level_and_wrap(boot):
    combo(boot)
    release_combo(boot)
    n = []
    for b in ("right", "right", "left", "left", "left"):
        boot.press(b, 2)
        n.append(boot.mem("debug_level"))
    assert n == [2, 3, 2, 1, 18], "wraps below 1"
    boot.press("right", 2)
    assert boot.mem("debug_level") == 1, "and above 18"
    boot.press("up", 2)
    boot.press("down", 2)
    assert boot.mem("debug_level") == 1


def test_the_box_shows_the_level(boot):
    combo(boot)
    release_combo(boot)
    boot.press("right", 2)
    boot.press("right", 2)
    boot.run(3)
    from test_flow import tile_id
    txt = banner_text(boot)
    want = [tile_id("GLYPH_" + c) for c in "L" "E" "V" "E" "L"] + [tile_id("HUD_BLANK"), tile_id("GLYPH_0"), tile_id("GLYPH_3")]
    start = (20 - 8) // 2
    assert txt[start:start + 8] == want, txt


@pytest.mark.parametrize("lvl", [1, 5, 12])
def test_a_starts_that_level_from_scratch(boot, lvl):
    combo(boot)
    release_combo(boot)
    for _ in range(lvl - 1):
        boot.press("right", 2)
    boot.press("a", 2)
    boot.run(15)       # the level load takes a few frames (LCD off)
    assert boot.mem("debug_menu_open") == 0 and boot.mem("game_state") == PLAYING
    assert boot.mem("level") == lvl and boot.mem("cur_group") == (lvl - 1) % 9, "its venue"
    assert boot.mem("lives") == 3 and boot.mem("score") == 0 and boot.mem("overlay_on") == 0
    boot.run(30)
    assert boot.mem("game_state") == PLAYING


def test_the_combo_in_play_pauses_then_a_starts_a_level_fresh(gb):
    gb.write("lives", 1)
    gb.write("score", 77)
    combo(gb)
    assert gb.mem("debug_menu_open") == 1
    x = gb.mem("bartender_x")
    gb.run(20)
    assert gb.mem("bartender_x") == x, "paused while open"
    release_combo(gb)
    gb.press("right", 2)
    assert gb.mem("debug_level") == 2
    gb.press("a", 2)
    gb.run(15)
    assert gb.mem("game_state") == PLAYING and gb.mem("level") == 2 and gb.mem("cur_group") == 1
    assert gb.mem("lives") == 3 and gb.mem("score") == 0 and gb.mem("debug_menu_open") == 0


def test_b_closes_and_play_resumes(gb):
    fc = gb.mem("intro_timer")
    combo(gb)
    release_combo(gb)
    gb.press("b", 2)
    assert gb.mem("debug_menu_open") == 0 and gb.mem("game_state") == PLAYING and gb.mem("overlay_on") == 0
    gb.run(10)
    assert gb.mem("game_state") == PLAYING and gb.mem("level") == 1
    assert gb.mem("intro_timer") != fc or gb.mem("intro_timer") == 0, "the game runs again"


def test_b_returns_to_the_title(boot):
    combo(boot)
    release_combo(boot)
    boot.press("b", 2)
    boot.run(5)
    assert boot.mem("debug_menu_open") == 0 and boot.mem("game_state") == TITLE and boot.mem("overlay_on") == 0
    boot.press("start", 2)
    boot.run(20)
    assert boot.mem("game_state") == PLAYING, "the title still works"


def test_b_with_the_combo_still_held_does_not_reopen(gb):
    combo(gb)
    gb.press("b", 2)
    gb.run(COMBO + 10)
    assert gb.mem("debug_menu_open") == 0 and gb.mem("game_state") == PLAYING
    release_combo(gb)


def test_short_start_pauses_normally(gb):
    gb.press("start", 3)
    gb.run(3)
    assert gb.mem("game_state") == PAUSED and gb.mem("debug_menu_open") == 0
    gb.press("start", 3)
    gb.run(3)
    assert gb.mem("game_state") == PLAYING


def test_the_release_build_has_no_debug_menu():
    subprocess.run(["make", "release"], cwd=ROOT, check=True, capture_output=True)
    noi = (ROOT / "build" / "release.noi").read_text()
    assert "debug_menu_open" not in noi and "debug_level" not in noi
    assert "debug_menu_open" in (ROOT / "build" / "game.noi").read_text()


def test_the_combo_works_from_any_menu_item_and_the_menu_survives(boot):
    from test_flow import SEL_MUSIC, music_line, title_text_row
    boot.press("up", 2)                                   # the cursor on MUSIC
    assert boot.mem("title_sel") == SEL_MUSIC
    s0 = boot.mem("sound_on")
    boot.hold("select")
    boot.run(2)
    boot.hold("start")
    boot.run(COMBO + 2)
    assert boot.mem("debug_menu_open") == 1 and boot.mem("sound_on") == s0, "neither START nor SELECT toggled it"
    release_combo(boot)
    boot.press("b", 2)
    boot.run(3)
    assert boot.mem("game_state") == TITLE and boot.mem("title_sel") == SEL_MUSIC
    assert music_line(boot) == title_text_row("music_on" if s0 else "music_off")
    boot.press("down", 2)                                 # wraps to ARCADE
    boot.press("a", 2)
    boot.run(20)
    assert boot.mem("game_state") == PLAYING and boot.mem("level") == 1
