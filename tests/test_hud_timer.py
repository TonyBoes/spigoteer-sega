# The mini-games' HUD timer: the hourglass tile (BG id MG_HOURGLASS) must hold the hourglass art in every game that shows a timer
# (owner 2026-10-15: "on the log roll, the timer sprite is wrong"), on both models, once play has begun.
import re

import pytest
from conftest import ROOT
from test_flow import tilemap_row
from test_mg import HOURGLASS, MG_PLAY, MG_PRACTICE, frames, mg_enter, until
from test_pause import GAMES, MODES, rom_s

pytestmark = pytest.mark.timeout(300)

ART = (ROOT / "build" / "mg_art.h").read_text()
HOURGLASS_BYTES = bytes(int(x, 16) for x in re.search(r"hourglass_tile\[16\] = \{([^}]*)\}", ART).group(1).split(","))


def bg_tile(gb, t):
    return bytes(gb.read((0x9000 if t < 128 else 0x8000) + t * 16, 16))


# The games whose Practice HUD shows no timer (found by booting each once: row[1] is not the hourglass). The test asserts
# both ways, so a game that gains or loses a timer fails here and the list is updated, instead of a silent skip.
NO_TIMER = {0, 3, 7, 11, 12, 13, 14}


@pytest.mark.parametrize("model", MODES)
@pytest.mark.parametrize("gid", GAMES)
def test_the_hud_hourglass_tile_is_the_hourglass_art_in_every_game_with_a_timer(model, gid):
    with rom_s(model) as gb:
        mg_enter(gb, gid, MG_PRACTICE)
        until(gb, lambda: gb.mem("mg_phase") == MG_PLAY, 400)
        frames(gb, 20)
        row = tilemap_row(gb, 0, 16, 4)
        assert (row[1] == HOURGLASS) == (gid not in NO_TIMER), f"game {gid}: timer shown is {row[1] == HOURGLASS} ({row})"
        if gid in NO_TIMER:
            return
        assert bg_tile(gb, HOURGLASS) == HOURGLASS_BYTES
