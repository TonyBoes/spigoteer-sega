# M2: filling and sliding full mugs, breaking at the left end, lives, game over.
import pytest
from conftest import check_golden

pytestmark = pytest.mark.timeout(60)

MAX_MUGS = 24
FREE, FULL, EMPTY, BREAKING = 0, 1, 2, 3


def mugs(gb):
    """(state, bar, x) of every non-free slot."""
    out = []
    for i in range(MAX_MUGS):
        st = gb.read("mug_state", MAX_MUGS)[i]
        if st:
            out.append((st, gb.read("mug_bar", MAX_MUGS)[i], gb.read("mug_x", MAX_MUGS)[i]))
    return out


def inject(gb, bar, x, state=FULL):
    """Put a mug straight into the pool (a full bar of mugs is not reachable by
    filling alone: a mug breaks in ~60 frames and filling takes 26)."""
    states = gb.read("mug_state", MAX_MUGS)
    i = list(states).index(0)
    gb.write(gb.addr("mug_state") + i, state)
    gb.write(gb.addr("mug_bar") + i, bar)
    gb.write(gb.addr("mug_x") + i, x)
    gb.write(gb.addr("mug_timer") + i, 0)
    gb.write("mugs_live", gb.mem("mugs_live") + 1)


def fill_and_launch(gb, frames=30):
    gb.hold("a")
    gb.run(frames)
    gb.release("a")
    gb.run(2)   # the release is polled by the next update; its result shows a frame later


def test_tap_of_a_launches_nothing(gb):
    gb.press("a", 5)
    gb.run(5)
    assert gb.mem("mugs_live") == 0
    assert gb.mem("fill_timer") == 0


def test_hold_then_release_launches_one_mug_that_slides_left(gb):
    gb.hold("a")
    gb.run(10)
    assert gb.mem("bartender_frame") == 3, "fill pose"
    assert gb.mem("mugs_live") == 0
    gb.run(20)
    gb.release("a")
    gb.run(2)
    assert gb.mem("mugs_live") == 1
    (state, b, x0), = mugs(gb)
    assert (state, b) == (FULL, 0)
    assert gb.mem("bartender_frame") == 4, "slide pose after launch"
    for n in range(1, 6):
        gb.run(1)
        (_, _, x), = mugs(gb)
        assert x == x0 - 2 * n
    gb.run(10)
    assert gb.mem("bartender_frame") == 0, "back to idle"


def test_release_before_full_launches_nothing(gb):
    gb.hold("a")
    gb.run(23)
    gb.release("a")
    gb.run(3)
    assert gb.mem("mugs_live") == 0


def test_a_away_from_tap_does_nothing(gb):
    gb.press("left", 10)
    gb.hold("a")
    gb.run(40)
    gb.release("a")
    gb.run(2)
    assert gb.mem("mugs_live") == 0
    assert gb.mem("fill_timer") == 0
    assert gb.mem("bartender_frame") == 0


def test_a_held_while_walking_back_to_tap_does_not_fill(gb):
    gb.press("left", 10)
    gb.hold("a")
    gb.press("right", 12)
    assert gb.mem("at_tap") == 1
    gb.run(40)
    gb.release("a")
    gb.run(2)
    assert gb.mem("mugs_live") == 0


@pytest.mark.parametrize("button", ["left", "up", "down"])
def test_moving_while_filling_cancels(gb, button):
    gb.hold("a")
    gb.run(10)
    assert gb.mem("fill_timer") > 0
    gb.press(button, 1 if button != "left" else 2)
    assert gb.mem("fill_timer") == 0
    gb.run(30)
    gb.release("a")
    gb.run(2)
    assert gb.mem("mugs_live") == 0


def test_mug_breaks_at_left_end_and_costs_a_life(gb):
    assert gb.mem("lives") == 3
    fill_and_launch(gb)
    gb.run(100)
    assert gb.mem("lives") == 2
    assert not gb.mem("game_over")
    gb.run(40)
    assert gb.mem("mugs_live") == 0, "slot freed after the glass animation"


def test_breaking_state_is_visible_then_frees(gb):
    fill_and_launch(gb)
    seen = set()
    for _ in range(120):
        gb.run(1)
        seen |= {s for s, _, _ in mugs(gb)}
    assert seen == {FULL, BREAKING}


def test_two_mugs_on_different_bars(gb):
    fill_and_launch(gb)
    gb.press("down", 1); gb.press("down", 1)
    assert gb.mem("bar") == 2
    fill_and_launch(gb)
    ms = mugs(gb)
    assert sorted(b for _, b, _ in ms) == [0, 2]
    before = {b: x for _, b, x in ms}
    gb.run(5)
    after = {b: x for _, b, x in mugs(gb)}
    assert all(after[b] == before[b] - 10 for b in before)


def test_per_bar_cap(gb):
    for k in range(5):
        inject(gb, 0, 130 - 8 * k)
    fill_and_launch(gb, 26)
    assert len([m for m in mugs(gb) if m[1] == 0]) == 6
    gb.run(1)
    fill_and_launch(gb, 26)           # 7th: refused while the six are still sliding
    assert len([m for m in mugs(gb) if m[0] == FULL and m[1] == 0]) <= 6
    assert gb.mem("mugs_live") <= 6


def test_cap_is_per_bar(gb):
    for k in range(6):
        inject(gb, 0, 130 - 8 * k)
    gb.press("down", 2)
    fill_and_launch(gb, 26)
    assert sorted({b for _, b, _ in mugs(gb)}) == [0, 1], "bar 1 still accepts a mug"


def test_three_breaks_end_the_game(gb):
    for _ in range(3):
        fill_and_launch(gb)
        gb.run(5)
    gb.run(130)
    assert gb.mem("lives") == 0
    assert gb.mem("game_over") == 1
    x = gb.mem("bartender_x")
    gb.press("left", 10)
    assert gb.mem("bartender_x") == x, "gameplay frozen"


def test_sprites_per_scanline_with_six_mugs(gb):
    for k in range(5):
        inject(gb, 0, 130 - 8 * k)
    fill_and_launch(gb, 26)
    assert len([m for m in mugs(gb) if m[0] == FULL]) == 6
    spr = gb.visible_sprites()
    assert len(spr) == 4 + 6
    counts = [0] * 144
    for s in spr:
        top = s["y"] - 16
        for line in range(max(top, 0), min(top + 16, 144)):
            counts[line] += 1
    assert max(counts) <= 10, max(counts)
    gb.press("left", 10)
    assert len(gb.visible_sprites()) == 10


def test_unused_oam_entries_hidden(gb):
    fill_and_launch(gb)
    assert len(gb.visible_sprites()) == 5


def test_mug_sliding_golden(gb):
    fill_and_launch(gb)
    gb.run(25)
    assert len(mugs(gb)) == 1
    check_golden(gb, "mug_sliding")
