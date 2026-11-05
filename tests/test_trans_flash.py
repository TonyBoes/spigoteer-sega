# No flash in the scene-change cover (src/trans.c): owner 2026-11-05, "the end flash is not fixed". The cover's LCD-off blank is white, so the drink
# whitens before the LCD goes off and darkens after it comes on (an ordered dither, a quarter a step); the fades ramp on each side. Across every
# variant (TRANS bits 5-6: 0 the drink, 1 white fade, 2 fade through amber) and both models, the screen's mean brightness has no excursion of more
# than 30/255 that lasts 1-3 frames and comes back (a blink), from the frame before the cover to the settled scene.
import numpy as np
import pytest

from conftest import K_PLAY, K_STORY, TRANS_ADDR, menu_tap, title_pick
from test_trans_fade import boot

pytestmark = pytest.mark.timeout(900)

LIMIT = 30


def brightness(gb):
    return float(np.asarray(gb.image().convert("L")).mean())


def blinks(ser, limit=LIMIT, longest=3):
    """(frame, size) of every 1..longest frame excursion above or below both neighbours' levels by more than `limit`."""
    out = []
    for i in range(len(ser)):
        for n in range(1, longest + 1):
            j = i + n + 1
            if j >= len(ser):
                break
            mid = ser[i + 1:j]
            if min(mid) > max(ser[i], ser[j]) + limit:
                out.append((i + 1, min(mid) - max(ser[i], ser[j])))
            if max(mid) < min(ser[i], ser[j]) - limit:
                out.append((i + 1, min(ser[i], ser[j]) - max(mid)))
    return out


def test_the_detector_sees_a_blink_and_not_a_ramp():
    assert blinks([50, 50, 200, 50, 50])
    assert blinks([200, 200, 20, 20, 200])
    assert not blinks([50, 90, 130, 170, 210, 255, 255, 255, 255, 255, 255, 210, 170, 130, 90, 50])


@pytest.mark.parametrize("variant", [0, 1, 2])
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_scene_change_cover_has_no_flash(model, variant):
    gb = boot(model, variant)
    title_pick(gb, K_PLAY, K_STORY, press=False)
    menu_tap(gb, "a")
    ser = [brightness(gb)]
    gb.press("a", 2)
    seen = False
    for n in range(160):
        gb.run(1, True)                                   # (rendered: gb.image() would otherwise tick a second frame)
        ser.append(brightness(gb))
        seen = seen or bool(gb.pb.memory[TRANS_ADDR] & 7)
    assert seen, "the cover ran"
    assert not blinks(ser), "blinks (frame, size): %s; series %s" % (blinks(ser), [int(x) for x in ser])
    if variant == 0:                                  # the drink: its whitening and darkening are ramps, not a cut (the old swaps jumped 100+ in a frame)
        worst = max(abs(b - a) for a, b in zip(ser, ser[1:]))
        assert worst <= 60, "the drink's largest frame-to-frame step is %d; series %s" % (worst, [int(x) for x in ser])
