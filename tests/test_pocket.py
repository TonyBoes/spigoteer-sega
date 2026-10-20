"""The pocketed tip (owner's playtest notes 2026-10-18; src/pocket.c): a tip picked up during a show is kept (one slot, the coin icon at HUD
column 9) and B starts a show from it. ARCADE and STORY only; CLASSIC and the LEVEL harness are as they were. Emptied at a level's end,
kept through a lost life."""
import pytest
from conftest import GAME, K_CLASSIC, K_PLAY, logic_paused, title_pick
from test_arcade import finish_step, start_arcade
from test_flow import PLAYING, lose_a_life, run_until, state, tilemap_row, tile_id
from test_hud import art_bytes, vram_tile
from test_patrons import clear_patrons, set_patron, put, inject_mug, MAX_P
from test_scores import booted
from test_story import to_goal
from test_tips import SHOW_FRAMES, TIP_SCORE, coin_sprites, dancer_sprites, started, w16

pytestmark = pytest.mark.timeout(240)

BLANK, ICON = tile_id("HUD_BLANK"), 255
COL = 9
MODELS = ["dmg", "cgb"]


def score(gb):
    return int.from_bytes(gb.read("score", 4), "little")


def arcade(model):
    gb = start_arcade(model)
    to_goal(gb)
    gb.run(2)
    quiet(gb)
    return gb


def quiet(gb):
    clear_patrons(gb)
    gb.write("intro_timer", 0)
    w16(gb, "spawn_timer", 0xFFFF)
    w16(gb, "story_timer", 0)
    gb.write("quota", 200)
    gb.write("tip_chance", 255)


def hud9(gb):
    return tilemap_row(gb, 0, COL, 1)[0]


def pocket(gb):
    return gb.mem("tip_pocket")


def drop_coin_here(gb):
    """A coin under the bartender (he picks it up on the next frame)."""
    with logic_paused(gb):
        gb.write("tip_bar", gb.mem("bar"))
        gb.write("tip_x", gb.mem("bartender_x") + 4)
        w16(gb, "tip_timer", 200)
    gb.run(3)


def pick_up_a_tip(gb):
    drop_coin_here(gb)
    assert gb.mem16("tip_timer") == 0


def start_a_show(gb):
    pick_up_a_tip(gb)
    started(gb)
    assert gb.mem16("show_timer") > 0 and pocket(gb) == BLANK


def press_b(gb):
    gb.press("b", 2)
    gb.run(3)


def end_show(gb):
    with logic_paused(gb):
        w16(gb, "show_timer", 1)
    gb.run(4)
    assert gb.mem16("show_timer") == 0


@pytest.mark.parametrize("model", MODELS)
def test_the_pocket_is_on_and_empty_in_arcade_and_shows_nothing(model):
    with arcade(model) as gb:
        assert pocket(gb) == BLANK and hud9(gb) == BLANK


@pytest.mark.parametrize("model", MODELS)
def test_a_tip_during_a_show_is_pocketed_not_wasted(model):
    with arcade(model) as gb:
        start_a_show(gb)
        s0, t0 = score(gb), gb.mem16("show_timer")
        pick_up_a_tip(gb)
        assert pocket(gb) == ICON, "the second tip is in the pocket"
        assert score(gb) == s0 + TIP_SCORE, "it still scores"
        assert 0 < gb.mem16("show_timer") < t0, "and the show is not restarted"
        gb.run(2)
        assert hud9(gb) == ICON
        assert vram_tile(gb, ICON) == art_bytes("assets/art/hud_icons.txt", "pocket")
        assert tilemap_row(gb, 0, 7, 2)[0] == tile_id("HUD_HEAD"), "the lives are where they were"


@pytest.mark.parametrize("model", MODELS)
def test_a_tip_with_no_show_running_starts_one_and_pockets_nothing(model):
    with arcade(model) as gb:
        pick_up_a_tip(gb)
        started(gb)
        assert pocket(gb) == BLANK and hud9(gb) == BLANK


@pytest.mark.parametrize("model", MODELS)
def test_a_tip_drops_during_a_show_only_while_the_pocket_is_empty(model):
    with arcade(model) as gb:
        start_a_show(gb)
        serve_one(gb, 90)
        assert gb.mem16("tip_timer") > 0 and len(coin_sprites(gb)) == 1, "empty pocket: a patron served during the show may tip"
        pick_up_a_tip(gb)
        assert pocket(gb) == ICON
        gb.write("tip_chance", 255)
        serve_one(gb, 60, expect_tip=False)
        assert gb.mem16("tip_timer") == 0 and not coin_sprites(gb), "pocket full: as before, no tip during a show"


def serve_one(gb, x, expect_tip=True):
    with logic_paused(gb):
        gb.write("pushback_px", 250)
        gb.write("tip_chance", 255)
        w16(gb, "spawn_timer", 0xFFFF)
        i = set_patron(gb, 2, x)
        put(gb, "patron_drinks", i, 1)
        inject_mug(gb, 2, x + 6)
    if expect_tip:
        run_until(gb, lambda: gb.mem16("tip_timer") > 0, 30)
    else:
        s0 = gb.mem("served")
        run_until(gb, lambda: gb.mem("served") > s0, 300)
    gb.run(2)


@pytest.mark.parametrize("model", MODELS)
def test_b_starts_a_show_from_the_pocket_and_empties_it(model):
    with arcade(model) as gb:
        start_a_show(gb)
        pick_up_a_tip(gb)
        assert pocket(gb) == ICON
        end_show(gb)
        gb.run(2)
        press_b(gb)
        assert gb.mem16("show_timer") > SHOW_FRAMES - 30, "a fresh show"
        assert pocket(gb) == BLANK
        gb.run(3)
        assert hud9(gb) == BLANK, "the icon is gone"


@pytest.mark.parametrize("model", MODELS)
def test_b_does_nothing_with_an_empty_pocket_or_during_a_show(model):
    with arcade(model) as gb:
        press_b(gb)
        assert gb.mem16("show_timer") == 0 and pocket(gb) == BLANK, "empty pocket, no show"
        start_a_show(gb)
        pick_up_a_tip(gb)
        t0 = gb.mem16("show_timer")
        press_b(gb)
        assert pocket(gb) == ICON and gb.mem16("show_timer") < t0, "during a show: the pocket keeps its tip, the show runs on"
        gb.run(2)
        assert hud9(gb) == ICON


@pytest.mark.parametrize("model", MODELS)
def test_b_does_not_move_the_bartender_or_pause(model):
    with arcade(model) as gb:
        x, bar = gb.mem("bartender_x"), gb.mem("bar")
        press_b(gb)
        assert (gb.mem("bartender_x"), gb.mem("bar")) == (x, bar) and state(gb) == PLAYING
        gb.press("start", 2)
        gb.run(3)
        assert state(gb) != PLAYING, "START still pauses"


@pytest.mark.parametrize("model", MODELS)
def test_the_pocket_empties_at_the_level_s_end(model):
    with arcade(model) as gb:
        start_a_show(gb)
        pick_up_a_tip(gb)
        assert pocket(gb) == ICON
        finish_step(gb)
        assert pocket(gb) == BLANK and hud9(gb) == BLANK, "the clear screen shows no icon"


@pytest.mark.parametrize("model", MODELS)
def test_a_lost_life_keeps_the_pocket(model):
    with arcade(model) as gb:
        start_a_show(gb)
        pick_up_a_tip(gb)
        lose_a_life(gb)
        run_until(gb, lambda: state(gb) == PLAYING, 400)
        gb.run(3)
        assert pocket(gb) == ICON and hud9(gb) == ICON and gb.mem16("show_timer") == 0
        gb.write("intro_timer", 0)
        press_b(gb)
        assert gb.mem16("show_timer") > 0 and pocket(gb) == BLANK, "and B uses it after the life"


@pytest.mark.parametrize("model", MODELS)
def test_a_new_level_starts_with_an_empty_pocket(model):
    with arcade(model) as gb:
        start_a_show(gb)
        pick_up_a_tip(gb)
        finish_step(gb)
        run_until(gb, lambda: state(gb) == PLAYING, 600) if state(gb) != PLAYING else None
        for _ in range(60):
            if state(gb) == PLAYING:
                break
            gb.press("a", 2)
            gb.run(20)
        assert pocket(gb) in (0, BLANK) and hud9(gb) == BLANK


@pytest.mark.parametrize("model", MODELS)
def test_classic_is_unchanged(model):
    with booted(model) as gb:
        title_pick(gb, K_PLAY, K_CLASSIC)
        run_until(gb, lambda: state(gb) == PLAYING, 30)
        quiet(gb)
        gb.write("tip_first", 0)
        assert pocket(gb) == 0 and hud9(gb) == BLANK
        pick_up_a_tip(gb)
        started(gb)
        serve_one(gb, 90, expect_tip=False)
        assert gb.mem16("tip_timer") == 0, "no tip during a show"
        pick_up_a_tip(gb)
        assert pocket(gb) == 0 and hud9(gb) == BLANK
        end_show(gb)
        press_b(gb)
        assert gb.mem16("show_timer") == 0, "B does nothing"


def test_the_harness_is_unchanged(boot):
    from conftest import title_level
    title_level(boot)
    run_until(boot, lambda: state(boot) == PLAYING, 60)
    assert pocket(boot) == 0
