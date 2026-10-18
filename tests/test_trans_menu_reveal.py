# The quick fade must reveal a FULLY BUILT screen (owner playtest 2026-10-18: "When entering the debug menu, garbage tiles from the title menu show
# briefly after transition"). The cause was the debug menu's window being shown after DISPLAY_ON: the reveal ran inside DISPLAY_ON, so it faded in
# the title's screen (with the menu's tiles loaded over it) and the menu popped in on the frame after.
# Every menu leg of tests/test_trans_menu.py (and the debug menu's open and close) is recorded frame by frame; each frame from the first lit one after
# the LCD was off, once it has some contrast, is compared with the settled screen after contrast normalising (the fade lerps the colours towards white,
# so the picture is the same shape): a frame showing another screen differs by far more than the animation does.
import pytest
from PIL import Image

import test_trans_menu as tm
from conftest import TRANS_ADDR, gesture, release_gesture, with_unlock
from test_flow import TITLE, run_until, state
from test_menu_music import lcd_on
from test_sound import make_rom

pytestmark = pytest.mark.timeout(900)

LIMIT = 0.12          # mean difference (0..1) of the normalised luminance; a wrong screen is 0.3+, the title's animation under 0.05
MIN_RANGE = 40        # luminance levels a frame must span to be compared (the first white frames carry no picture)


def lum(im):
    return Image.frombytes("RGB", (160, 144), im).convert("L")


def norm(im):
    px = list(lum(im).tobytes())
    lo, hi = min(px), max(px)
    return [(p - lo) / (hi - lo or 1) for p in px], hi - lo


def worst_reveal_diff(frames, final):
    """The largest difference between a revealed frame (LCD on after an LCD-off frame, contrast enough) and the settled screen."""
    ref, rng = norm(final)
    assert rng >= MIN_RANGE, "the settled screen has no picture"
    worst, seen_off, compared = 0.0, False, 0
    for on, im in frames:
        if not on:
            seen_off = True
            continue
        if not seen_off:
            continue
        px, r = norm(im)
        if r < MIN_RANGE:
            continue
        d = sum(abs(a - b) for a, b in zip(px, ref)) / len(px)
        worst, compared = max(worst, d), compared + 1
    assert compared >= 3, "the reveal showed no picture to compare"
    return worst


def record(gb, press, ready, hold=None):
    """Press `press` (2 frames), record every frame until `ready` and the fade is over, then 30 more for the settled screen."""
    frames = []
    gb.pb.button_press(press)
    for i in range(tm.MAX_FRAMES):
        gb.run(1)
        if i == 1:
            gb.pb.button_release(press)
        frames.append((lcd_on(gb), gb.image().tobytes()))
        if i > 3 and ready() and not gb.pb.memory[TRANS_ADDR] & 0x1F and lcd_on(gb):
            break
    else:
        raise AssertionError("never settled")
    gb.run(30)
    return frames, gb.image().tobytes()


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_debug_menu_opens_and_closes_on_a_built_screen(model):
    gb = tm.boot(model, with_unlock())
    gesture(gb, taps=2)                          # (SELECT stays held; the third START opens it)
    frames, final = record(gb, "start", lambda: state(gb) == 7)
    d = worst_reveal_diff(frames, final)
    assert d < LIMIT, f"opening: the reveal showed another screen ({d:.3f})"
    release_gesture(gb)
    gb.run(30)
    frames, final = record(gb, "b", lambda: state(gb) == TITLE)
    d = worst_reveal_diff(frames, final)
    assert d < LIMIT, f"closing: the reveal showed another screen ({d:.3f})"
    gb.pb.stop(save=False)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("scenario", list(tm.MENU_SCENARIOS))
def test_every_menu_leg_reveals_a_built_screen(model, scenario, monkeypatch):
    results = []

    def go(gb, legs, name, press, ready, cont=True, mute_after=False, silent_ok=False):
        run_until(gb, lambda: tm.settled(gb), tm.MAX_FRAMES)
        gb.run(8)
        if press is None:                        # (the idle title -> scores: no key)
            frames, n = [], 0
            while n < tm.MAX_FRAMES:
                gb.run(1)
                n += 1
                frames.append((lcd_on(gb), gb.image().tobytes()))
                if ready() and tm.settled(gb):
                    break
            gb.run(30)
            final = gb.image().tobytes()
        else:
            frames, final = record(gb, press, ready)
        results.append((name, worst_reveal_diff(frames, final)))

    monkeypatch.setattr(tm, "go", go)
    with make_rom(model, None, sound=True) as gb:
        gb.run(120)
        tm.hold_stage_anim(gb)
        gb.run(240)
        tm.trans_enable(gb, True)
        tm.MENU_SCENARIOS[scenario](gb, [])
    assert results
    bad = [(n, round(d, 3)) for n, d in results if d >= LIMIT]
    assert not bad, bad
