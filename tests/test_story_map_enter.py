# Leaving the story map for another screen (owner 2026-11-05: "a flash of garbage tiles when entering a venue from the map").
#
# Every frame from the press of A until the new screen has settled is captured on the real ROM with the scene change's cover on (the tests turn the transitions off
# otherwise: conftest trans_enable), on both models, in the three cover variants (the drink, the white fade, the amber fade), on every way off the map: the next
# venue's PRE scene, PLAY at a cleared venue, RESUME and ENTER at a venue whose shift was quit, a festival game, and THE POUR-OFF. Asserted:
#   1. the old screen stays as it is while it shows: from the press until the LCD goes off the scroll registers are the ones the map had. (The flash: the map's
#      leave() sent SCX / SCY home at once, so the cover rose over a shifted picture of the 32 x 32 ring buffer, the window map's HUD rows at its top.)
#   2. the drink (variant 0): no frame before the LCD goes off shows a tile that is not the old screen's: every 8 x 8 cell above the drink's window (sprite boxes
#      left out) is a cell of the picture just before the press, or the blank white. And the first frame after the LCD comes on is all drink (the window covers the
#      screen): the new screen is never shown before it is whole.
import numpy as np
import pytest

from conftest import trans_enable, TRANS_ADDR
from test_story_map import to_map, TOWN
from test_story_map_world import sprite_mask

SMAP_RESUME = 0x08


def cells(img):
    a = np.array(img.convert("RGB"))
    return {a[y:y + 8, x:x + 8].tobytes() for y in range(0, 144, 8) for x in range(0, 160, 8)}


def window_top(regs):
    """The first line the window covers (144: none)."""
    if not regs["LCDC"] & 0x80 or not regs["LCDC"] & 0x20 or regs["WX"] > 7 or regs["WY"] >= 144:
        return 144
    return regs["WY"]


def leave(model, start, presses, variant, settle=120):
    """The map set up with `start`, the keys of `presses` ((key, frames to wait after)), the last one held and every frame after it captured: [(image, regs, oam)]."""
    gb = start(model)
    trans_enable(gb, True)
    gb.pb.memory[TRANS_ADDR] = (gb.pb.memory[TRANS_ADDR] & ~0x60) | (variant << 5)
    for k, wait in presses[:-1]:
        gb.press(k, 4)
        gb.run(wait)
    gb.run(1, True)
    before = gb.image().copy()
    regs0 = gb.regs()
    k = presses[-1][0]
    gb.pb.button_press(k)
    frames = []
    for i in range(settle):
        if i == 3:
            gb.pb.button_release(k)
        gb.run(1, True)
        frames.append((gb.image().copy(), gb.regs(), gb.oam()))
    return frames, before, regs0


def start_at(progress, stop, flags=None):
    return lambda model: to_map(model, progress, stop=stop, flags=flags)


PATHS = {
    "next_venue": (start_at(3, 3), [("a", 0)]),
    "play_cleared": (start_at(3, 1), [("a", 30), ("a", 0)]),
    "resume": (start_at(3, 3, SMAP_RESUME), [("a", 30), ("a", 0)]),
    "enter": (start_at(3, 3, SMAP_RESUME), [("a", 30), ("down", 8), ("a", 0)]),
    "festival": (start_at(3, TOWN), [("a", 30), ("a", 30), ("a", 0)]),
    "pour_off": (start_at(10, TOWN, 0x77), [("a", 30), ("down", 8), ("a", 0)]),
}


@pytest.mark.parametrize("variant", [0, 1, 2])
@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("name", list(PATHS))
def test_the_old_screen_stays_as_it_is_until_the_lcd_goes_off(model, name, variant):
    start, presses = PATHS[name]
    frames, before, regs0 = leave(model, start, presses, variant)
    off = next((i for i, f in enumerate(frames) if not f[1]["LCDC"] & 0x80), None)
    assert off is not None, "the LCD went off for the new screen"
    for i in range(off):
        r = frames[i][1]
        assert (r["SCX"], r["SCY"]) == (regs0["SCX"], regs0["SCY"]), f"frame {i}: the old screen's scroll changed while it shows"
    on = next(i for i in range(off, len(frames)) if frames[i][1]["LCDC"] & 0x80)
    first = np.array(frames[on][0].convert("RGB"))
    assert window_top(frames[on][1]) == 0 or (first == first[0, 0]).all(), "the first frame after the LCD comes on is all drink or all white: the new screen is never shown before it is whole"
    if variant or name not in ("next_venue", "pour_off"):      # (the drink is the cover of a story scene change; a Practice game or a festival game fades white: no cell test)
        return
    known = cells(before) | cells(frames[0][0]) | cells(frames[2][0]) | {bytes([255]) * 192}      # (the first frames: a panel of the map goes, the map under it is the old screen too)
    poam = []
    for i in range(off):
        im, r, oam = frames[i]
        a = np.array(im.convert("RGB"))
        m = np.zeros((144, 160), dtype=bool)
        sprite_mask(oam, m)
        sprite_mask(poam, m)
        poam = oam
        m[min(window_top(r), window_top(frames[i + 1][1])):, :] = True      # (a frame's picture shows the window one step higher than its registers say: where the top edge crosses a dark pixel of the map (the desert peaks west of the town, 11-08) that tile differs)
        for y in range(0, 144, 8):
            for x in range(0, 160, 8):
                assert m[y:y + 8, x:x + 8].any() or a[y:y + 8, x:x + 8].tobytes() in known, f"frame {i}: a foreign tile at {x},{y}"
