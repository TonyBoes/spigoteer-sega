# The Practice screen with the REAL illustrations (assets/art/practice, owner approved 2026-10-25): goldens for Quick Draw and Taiko Pour on DMG and CGB,
# and a pixel check that every picture on the screen is the one the generator built from its PNG. (tests/test_practice_art.py pins the streaming against
# placeholders; this file pins the shipped art.)
import pytest
from conftest import check_golden
from test_mg_list import NAMES, selection, tap, to_list
from test_scores import booted
from conftest import hold_stage_anim

pytestmark = pytest.mark.timeout(300)


@pytest.fixture(params=["dmg", "cgb"])
def model(request):
    return request.param


@pytest.mark.parametrize("game", [0, 7], ids=["quickdraw", "taikopour"])
def test_the_practice_screen_shows_the_real_picture(model, game):
    with to_list(booted(model)) as gb:
        hold_stage_anim(gb)
        for _ in range(game):
            tap(gb, "right")
            gb.run(6)
        gb.run(60)                                   # the stream (about 10 frames) and the wipe are long done
        assert gb.mem("ml_sel") == game and selection(gb) == NAMES[game]
        check_golden(gb, f"practice_art_{['quickdraw', 'taikopour'][[0, 7].index(game)]}")
