# The tip's coin (owner report 11-13, a block instead of a coin): its VRAM tiles are the coin art's in every venue and with two coins out, and
# the sprites show the coin's tiles.
import re

import pytest
from conftest import ROOT
from test_art import goto_group
from test_pocket import arcade
from test_tip2 import serve_look
from test_tips import OBJ_COIN, coin_sprites

pytestmark = pytest.mark.timeout(120)

_ART_C = (ROOT / "build" / "art.c").read_text()


def coin_art():
    body = _ART_C[_ART_C.index("coin_tiles"):]
    body = body[body.index("{") + 1:body.index("}")]
    return bytes(int(x, 0) for x in re.findall(r"0x[0-9a-fA-F]+", body))


def vram_coin(gb):
    return bytes(gb.read(0x8000 + 16 * OBJ_COIN, 64))


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_arcade_two_coins_shot(model):
    gb = arcade(model)
    try:
        serve_look(gb, 0, 90, 0)
        serve_look(gb, 1, 70, 0)
        gb.run(5)
        sp = coin_sprites(gb)
        assert len(sp) == 2 and all(s["tile"] in (OBJ_COIN, OBJ_COIN + 2) for s in sp), sp
        assert vram_coin(gb) == coin_art(), "the coin's tiles in VRAM are the art's"
    finally:
        gb.stop()


@pytest.mark.parametrize("group", range(10))
def test_coin_tiles_every_venue(gb, group):
    goto_group(gb, group)
    gb.run(400)
    assert vram_coin(gb) == coin_art(), f"venue {group}: the coin's tiles in VRAM are not the art"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_coin_tiles_after_the_soundtrack_then_arcade(model):
    """The owner's path (11-13): the SOUNDTRACK player, a tune playing, B back to the title, then ARCADE: the coin is still the art."""
    from test_arcade import booted, title_arcade, state, run_until, hold_stage_anim, GS_GOAL
    from test_jukebox import to_jukebox, tap
    from test_flow import TITLE
    from conftest import MENU_SETTLE
    rom = booted(model, None)
    try:
        hold_stage_anim(rom)
        to_jukebox(rom)
        tap(rom, "a")
        rom.run(120)
        tap(rom, "a")
        tap(rom, "b")
        run_until(rom, lambda: state(rom) == TITLE, 30)
        rom.run(MENU_SETTLE)
        tap(rom, "b")
        rom.run(MENU_SETTLE)
        assert vram_coin(rom) == coin_art(), "coin tiles after the soundtrack"
        title_arcade(rom)
        run_until(rom, lambda: state(rom) == GS_GOAL, 60)
        rom.run(200)
        assert vram_coin(rom) == coin_art(), "coin tiles in ARCADE after the soundtrack"
    finally:
        rom.stop()


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_coin_tiles_after_the_story_intro_and_map(model):
    """The owner's report (11-13): a new STORY game, the intro's pictures and portraits and the map borrow BG ids 92-95, the coin's VRAM:
    at the first shift the coin tiles are the art again (the venue load puts them back)."""
    from test_story import start_story, through_the_map, skip_scene, SP_MAP, GS_STORY, GS_GOAL, state
    gb = start_story(model)
    try:
        for _ in range(40):
            if state(gb) == GS_GOAL:
                break
            if gb.mem("story_phase") == SP_MAP and state(gb) == GS_STORY:
                through_the_map(gb)
            else:
                skip_scene(gb)
        assert state(gb) == GS_GOAL, "the first shift's banner"
        gb.press("a", 2)
        gb.run(30)
        assert vram_coin(gb) == coin_art(), "coin tiles at the first story shift"
    finally:
        gb.stop()
