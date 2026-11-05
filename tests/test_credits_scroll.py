# The scrolling credits variant (make BUILD=out/b_scroll OUT=out/o_scroll CREDITS=SCROLL unlocked; src/credits.c "the scrolling credits").
# It is a playtest build of its own, not the default ROM: these tests skip when that ROM has not been built.
import pytest
from pathlib import Path

from conftest import K_BONUS, K_CREDITS, ROOT, hold_stage_anim, title_pick
from gbtools import Rom
from test_flow import run_until

SCROLL_ROM = ROOT / "out" / "b_scroll" / "game-unlocked.gb"
SCROLL, NEXT, GC, GL, LIVE = 20, 22, 43, 44, 48            # struct cr_state's fields (scroll variant)

pytestmark = pytest.mark.skipif(not SCROLL_ROM.exists(), reason="the CREDITS=SCROLL ROM is not built")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_cast_scrolls_one_pixel_every_two_frames_with_no_fade(model):
    with Rom(SCROLL_ROM, model) as gb:
        gb.run(120)
        hold_stage_anim(gb)
        title_pick(gb, K_BONUS, K_CREDITS)
        run_until(gb, lambda: gb.mem("story_phase") == 8, 40)
        run_until(gb, lambda: gb.read("story_scratch", 64)[LIVE] == 1, 400)       # (built behind the white, faded in once)
        bgp = gb.pb.memory[0xFF47]
        last = None
        for _ in range(900):
            gb.run(1)
            st = gb.read("story_scratch", 64)
            s = st[SCROLL] | st[SCROLL + 1] << 8
            assert last is None or 0 <= s - last <= 2
            assert gb.pb.memory[0xFF42] == s & 255                                 # SCY follows
            if model == "dmg":
                assert gb.pb.memory[0xFF47] == bgp                                 # no fade: BGP never moves
            last = s
        assert last >= 350 and st[GC] >= 4                                         # about 450 px in 900 frames, several cards on
