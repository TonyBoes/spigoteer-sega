# The drink borrows BG tile ids 248-251, which are also the story bar-change puff's OBJ tiles 246-251 (src/game.h OBJ_DUST): the first puff after a transition
# was the drink's amber tile (owner 2026-10-17: "the puff is an amber box like sprites from the transition"). Transitions ON (conftest turns them off elsewhere):
# the puff's tiles after a title -> ARCADE and after a level -> level are those of a run without the transition, for every variant (TRANS bits 5-6).
import pytest

from conftest import K_ARCADE, K_PLAY, TRANS_ADDR, hold_stage_anim, title_pick, trans_enable
from test_sound import make_rom
from test_story import to_shift, win

pytestmark = pytest.mark.timeout(900)

VARIANTS = [0, 1, 2]


def boot(model, variant, on=True):
    gb = make_rom(model, None, sound=True)
    gb.run(120)
    hold_stage_anim(gb)
    trans_enable(gb, on)
    if on:
        m = gb.pb.memory
        m[TRANS_ADDR] = (m[TRANS_ADDR] & ~0x60) | (variant << 5)
    return gb


def puff_tiles(gb):
    m = gb.pb.memory
    return bytes(m[0x8000 + 246 * 16 + i] for i in range(6 * 16))


def to_arcade(gb):
    title_pick(gb, K_PLAY, K_ARCADE)
    gb.run(400)


def bar_change(gb):
    gb.press("down", 2)
    gb.run(6)


@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_first_puff_after_title_to_arcade_has_its_own_tiles(model, variant):
    tiles = []
    for on in (True, False):
        gb = boot(model, variant, on)
        to_arcade(gb)
        first = puff_tiles(gb)
        bar_change(gb)
        tiles.append((first, puff_tiles(gb)))
        gb.pb.stop(save=False)
    assert tiles[0] == tiles[1], "the puff's tiles after the transition differ from a run without it"
    assert tiles[0][0] == tiles[0][1]


@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_first_puff_after_level_to_level_has_its_own_tiles(model, variant):
    tiles = []
    for on in (True, False):
        gb = to_shift(model, 0, 0)
        trans_enable(gb, on)
        if on:
            m = gb.pb.memory
            m[TRANS_ADDR] = (m[TRANS_ADDR] & ~0x60) | (variant << 5)
        win(gb, 0, 0)
        gb.run(500)
        tiles.append(puff_tiles(gb))
        bar_change(gb)
        tiles.append(puff_tiles(gb))
        gb.pb.stop(save=False)
    assert tiles[0] == tiles[2] and tiles[1] == tiles[3] and tiles[0] == tiles[1]
