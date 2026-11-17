# The shared-screen credits roll (CRSPLIT, asm writers): the whole roll clean on both models (tools/dev/credits_roll_check.py, Color at double speed as shipped; also at most 8
# sprites on any line), and the Color roll at the tests' NORMAL speed must go on to the end card: there the swap interrupt at line 135 runs into the next frame, every update
# starts late, and a rule that moved the picture only in the VBlank froze it for good at the Igloo page (2026-11-16: the lag now moves it mid-frame, tearing the top lines).
import os
import sys

import pytest

from conftest import ROOT, locked_make, Rom

sys.path.insert(0, str(ROOT / "tools" / "dev"))

OUT = ROOT / "out" / "splitrom"
pytestmark = pytest.mark.timeout(900)


@pytest.fixture(scope="module")
def split():
    bdir = OUT / "build"
    env = dict(os.environ, CRFLOW="SMOOTH", CRSCENE="1", CRSPLIT="1", CRART="18")
    env.pop("GB_ROM", None)
    r = locked_make([f"BUILD={bdir}", f"OUT={OUT / 'o'}", "unlocked"], "splitrom", env=env)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    return bdir / "game-unlocked.gb", bdir


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_split_roll_is_clean_and_has_at_most_8_sprites_a_line(split, model):
    from credits_roll_check import run
    rom, bdir = split
    frames, bad, *_ = run(rom, bdir, model, None, 11000)
    bad.pop("crops", None)
    assert frames > 10000
    assert not {k: v[:3] for k, v in bad.items() if v}, {k: len(v) for k, v in bad.items() if v}


def test_the_color_split_roll_reaches_its_end_card_at_normal_speed(split):
    from test_credits import hold_stage_anim, title_pick, run_until, K_BONUS, K_CREDITS, SP_CREDITS, TUNE_FRAMES
    rom, _ = split
    with Rom(rom, "cgb") as gb:
        gb.run(120)
        gb.model_name = "cgb"
        hold_stage_anim(gb)
        title_pick(gb, K_BONUS, K_CREDITS)
        run_until(gb, lambda: gb.mem("story_phase") == SP_CREDITS, 20)
        run_until(gb, lambda: gb.read("story_scratch", 70)[62] == 3 or gb.mem("cur_tune") != 16, TUNE_FRAMES + 400)
        st = gb.read("story_scratch", 70)
        assert st[62] == 3, "CR->st: the roll reached its end"
        assert (st[20] | st[21] << 8) == (st[22] | st[23] << 8), "the picture is where the timeline is"
