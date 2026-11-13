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
