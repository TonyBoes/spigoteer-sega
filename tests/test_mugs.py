# M2: filling and sliding full mugs, breaking at the left end, lives, game over.
import pytest
from conftest import GAME, LAYOUT, bar_counter_row, bar_top_y, check_golden, mug_top_y

pytestmark = pytest.mark.timeout(60)

MAX_MUGS = 20
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


def no_patrons(gb):
    """Take the patrons off the bars so a mug can reach the left end (M3 patrons would catch it)."""
    for i in range(16):
        gb.write(gb.addr("patron_state") + i, 0)
    gb.write("patrons_live", 0)


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
    gb.run(GAME["FILL_FRAMES"] - 1)
    gb.release("a")
    gb.run(3)
    assert gb.mem("mugs_live") == 0


def test_a_away_from_tap_does_nothing(gb):
    gb.press("left", 30)                         # 45 px: outside the 32 px grace
    gb.hold("a")
    gb.run(40)
    gb.release("a")
    gb.run(2)
    assert gb.mem("mugs_live") == 0
    assert gb.mem("fill_timer") == 0
    assert gb.mem("bartender_frame") == 0


def test_a_held_while_walking_back_to_tap_does_not_fill(gb):
    gb.press("left", 30)
    gb.hold("a")
    gb.press("right", 32)
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
    no_patrons(gb)
    assert gb.mem("lives") == 3
    fill_and_launch(gb)
    gb.run(100)
    assert gb.mem("lives") == 2
    assert not gb.mem("game_over")
    gb.run(40)
    assert gb.mem("mugs_live") == 0, "slot freed after the glass animation"


def test_breaking_state_is_visible_then_frees(gb):
    no_patrons(gb)
    fill_and_launch(gb)
    seen = set()
    for _ in range(120):
        gb.run(1)
        seen |= {s for s, _, _ in mugs(gb)}
    assert seen == {FULL, BREAKING}


def test_two_mugs_on_different_bars(gb):
    no_patrons(gb)                    # (the first mug would reach a start patron at the door before the second is launched)
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
    no_patrons(gb)
    for n in range(3):
        no_patrons(gb)                             # M4: a lost life re-places the start patrons
        fill_and_launch(gb)
        for _ in range(250):                       # M4: each lost life freezes play, so wait it out
            gb.run(1)
            if gb.mem("lives") == 2 - n and gb.mem("game_state") != 2:
                break
    gb.run(5)
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


# ---- tap grace + snap, fill animation (owner feedback after playing) ------------------------
TAP_X, TAP_GRACE, SPOUT_X = GAME["TAP_X"], GAME["TAP_GRACE"], GAME["SPOUT_X"]    # M8a: 120, 32, 136
ART_H = (__import__("conftest").ROOT / "build" / "art.h").read_text()


def _define(name):
    return int(__import__("re").search(rf"#define {name} (\d+)", ART_H).group(1))


OBJ_MUG = _define("BARTENDER_TILE_COUNT")
OBJ_MUG_FILL = OBJ_MUG + _define("MUG_TILE_COUNT") + _define("GLASS_TILE_COUNT")
FILL_OAM = 4
FILL_FRAMES_N = GAME["FILL_FRAMES"]          # M8a: 16


def fill_sprite(gb):
    """The fill sprite's OAM entry (index 4) if it is on screen, else None."""
    e = gb.oam()[FILL_OAM]
    return e if 0 < e["y"] < 160 else None


def test_a_within_grace_snaps_to_the_tap_and_starts_filling(gb):
    gb.press("left", 20)                         # M8a: 30 px left of the fill position, inside the 32 px grace
    assert gb.mem("bartender_x") == TAP_X - 30 and gb.mem("at_tap") == 0
    gb.press("a", 1)
    gb.run(1)
    assert gb.mem("bartender_x") == TAP_X and gb.mem("at_tap") == 1 and gb.mem("facing") == 0, \
        "a tap of A snaps him there; he faces the bar again when it is let go"
    gb.hold("a")
    gb.run(3)
    assert gb.mem("fill_timer") > 0 and gb.mem("bartender_frame") == 3 and gb.mem("facing") == 1
    gb.release("a")


def test_grace_boundary_is_32_px(gb):
    gb.write("bartender_x", TAP_X - TAP_GRACE)  # exactly TAP_GRACE px away (not reachable in 1.5 px strides)
    gb.write("at_tap", 0)
    gb.hold("a")
    gb.run(2)
    assert gb.mem("bartender_x") == TAP_X and gb.mem("fill_timer") > 0
    gb.release("a")
    gb.run(3)
    gb.write("bartender_x", TAP_X - TAP_GRACE - 1)   # 33 px: outside
    gb.run(1)
    gb.hold("a")
    gb.run(2)
    assert gb.mem("bartender_x") == TAP_X - TAP_GRACE - 1 and gb.mem("fill_timer") == 0
    gb.release("a")


def test_a_beyond_the_grace_does_nothing(gb):
    gb.press("left", 30)
    assert gb.mem("bartender_x") == TAP_X - 45
    gb.hold("a")
    gb.run(40)
    gb.release("a")
    gb.run(2)
    assert gb.mem("bartender_x") == TAP_X - 45, "no snap"
    assert gb.mem("fill_timer") == 0 and gb.mem("mugs_live") == 0 and fill_sprite(gb) is None


def test_a_held_into_the_grace_zone_does_not_snap(gb):
    gb.press("left", 30)
    gb.hold("a")
    gb.run(2)
    gb.press("right", 14)                        # held A walks him to 24 px from the tap: a fresh press is needed
    assert gb.mem("bartender_x") == TAP_X - 24 and gb.mem("fill_timer") == 0
    gb.run(10)
    assert gb.mem("bartender_x") == TAP_X - 24 and gb.mem("fill_timer") == 0
    gb.release("a")


def test_snapped_fill_launches_a_mug(gb):
    gb.press("left", 5)
    gb.hold("a")
    gb.run(30)
    gb.release("a")
    gb.run(2)
    assert gb.mem("mugs_live") == 1 and gb.mem("bartender_x") == TAP_X


def test_fill_sprite_shows_while_filling_and_steps_through_the_frames(gb):
    assert fill_sprite(gb) is None
    gb.hold("a")
    gb.run(2)                                    # OAM DMA shows a frame late
    seen, tiles = [], []
    for _ in range(FILL_FRAMES_N + 4):
        gb.run(1)
        e = fill_sprite(gb)
        assert e is not None, "visible for the whole fill"
        seen.append(gb.mem("fill_stage"))
        tiles.append(e["tile"])
    assert seen == sorted(seen) and sorted(set(seen)) == [0, 1, 2, 3], seen
    assert tiles[-1] == OBJ_MUG_FILL + 3 * 2 and tiles[0] == OBJ_MUG_FILL
    assert [t for i, t in enumerate(tiles) if i == 0 or t != tiles[i - 1]] == [OBJ_MUG_FILL + 2 * s for s in range(4)]
    e = fill_sprite(gb)
    assert e["x"] - 8 == SPOUT_X and e["y"] - 16 == mug_top_y(0), "under the spout, in his hand, on the counter surface of bar 0"
    # launch: the fill sprite goes, the sliding mug starts from the same spot
    gb.release("a")
    gb.run(2)
    assert fill_sprite(gb) is None or fill_sprite(gb)["tile"] == OBJ_MUG
    assert gb.mem("fill_stage") == 0 and gb.mem("fill_timer") == 0
    (_, _, x), = mugs(gb)
    assert x == SPOUT_X - 2 * 2 or x == SPOUT_X - 2 * 3
    assert len(gb.visible_sprites()) == 5


def test_fill_sprite_follows_the_bar_and_goes_when_cancelled(gb):
    gb.press("down", 2)
    gb.hold("a")
    gb.run(8)
    e = fill_sprite(gb)
    assert e["y"] - 16 == mug_top_y(1)
    gb.press("left", 2)
    assert gb.mem("fill_timer") == 0 and fill_sprite(gb) is None
    gb.release("a")


def test_sprites_per_scanline_with_six_mugs_and_the_fill_sprite(gb):
    for k in range(6):
        inject(gb, 0, 130 - 8 * k)
    gb.hold("a")
    gb.run(10)
    assert fill_sprite(gb) is not None
    spr = gb.visible_sprites()
    assert len(spr) == 4 + 1 + 6
    counts = [0] * 144
    for s in spr:
        top = s["y"] - 16
        for line in range(max(top, 0), min(top + 16, 144)):
            counts[line] += 1
    assert max(counts) <= 10, max(counts)
    gb.release("a")


def test_filling_golden(gb):
    gb.hold("a")
    for _ in range(40):
        gb.run(1)
        if gb.mem("fill_stage") == 2:
            break
    assert gb.mem("fill_stage") == 2 and fill_sprite(gb) is not None
    check_golden(gb, "filling")


# ---- M8a: fill pose at the spout, carrying a full mug, half-speed empties ------------------------------
def bartender_flipped(gb):
    """True when all 4 bartender entries are X-flipped (facing right)."""
    return all(e["flags"] & 0x20 for e in gb.oam()[:4])


def test_fill_frames_is_16(gb):
    gb.hold("a")
    gb.run(2)
    t0 = gb.mem("fill_timer")
    gb.run(FILL_FRAMES_N)
    assert FILL_FRAMES_N == 16 and gb.mem("fill_timer") == FILL_FRAMES_N and gb.mem("fill_stage") == 3
    assert t0 < FILL_FRAMES_N
    gb.release("a")


def test_he_faces_the_tap_while_filling_and_turns_left_to_slide_the_mug(gb):
    assert gb.mem("facing") == 0
    gb.hold("a")
    gb.run(4)
    assert gb.mem("facing") == 1 and gb.mem("bartender_frame") == 3, "facing right (the tap), fill pose"
    gb.run(1)
    assert bartender_flipped(gb), "the sprite is flipped toward the tap"
    e = fill_sprite(gb)
    assert e["x"] - 8 == SPOUT_X == gb.mem("bartender_x") + 16, "the mug is in his hand, under the spout"
    gb.run(FILL_FRAMES_N)
    gb.release("a")
    gb.run(2)
    assert gb.mem("facing") == 0 and gb.mem("bartender_frame") == 4, "turned left, slide pose"
    gb.run(1)
    assert not bartender_flipped(gb)
    (state, b, x), = mugs(gb)
    assert (state, b) == (FULL, 0) and x < SPOUT_X, "the mug slides left from under the spout"


def test_spout_fill_golden(gb):
    gb.hold("a")
    for _ in range(40):
        gb.run(1)
        if gb.mem("fill_stage") == 2:
            break
    gb.run(1)
    assert gb.mem("facing") == 1 and fill_sprite(gb) is not None
    check_golden(gb, "spout_fill")
    gb.release("a")


def test_a_full_mug_is_carried_to_another_bar_and_launched_there(gb):
    gb.hold("a")
    gb.run(FILL_FRAMES_N + 4)
    assert gb.mem("fill_timer") == FILL_FRAMES_N
    gb.press("down", 2)                          # A still held: he takes the full mug along
    assert gb.mem("bar") == 1 and gb.mem("bartender_x") == TAP_X
    assert gb.mem("fill_timer") == FILL_FRAMES_N and gb.mem("facing") == 1 and gb.mem("bartender_frame") == 3
    gb.press("down", 2)                          # and on to bar 2
    gb.run(1)
    assert gb.mem("bar") == 2 and gb.mem("fill_timer") == FILL_FRAMES_N
    assert fill_sprite(gb)["y"] - 16 == mug_top_y(2), "the full mug moved with him"
    assert gb.mem("mugs_live") == 0, "nothing launched yet"
    gb.release("a")
    gb.run(2)
    (state, b, x), = mugs(gb)
    assert (state, b) == (FULL, 2), "launched on the bar he carried it to"
    assert gb.mem("facing") == 0


def test_up_down_before_the_mug_is_full_still_cancels(gb):
    gb.hold("a")
    gb.run(FILL_FRAMES_N // 2)
    gb.press("up", 2)
    assert gb.mem("bar") == 3 and gb.mem("fill_timer") == 0
    gb.run(20)
    gb.release("a")
    gb.run(2)
    assert gb.mem("mugs_live") == 0


def test_walking_left_with_a_full_mug_cancels_and_right_cannot_move_him(gb):
    gb.hold("a")
    gb.run(FILL_FRAMES_N + 4)
    gb.press("right", 4)                         # the fill position is the right end of his walk: nothing moves
    assert gb.mem("bartender_x") == TAP_X and gb.mem("fill_timer") == FILL_FRAMES_N
    gb.press("left", 2)
    assert gb.mem("fill_timer") == 0 and gb.mem("bartender_x") < TAP_X
    gb.release("a")
    gb.run(2)
    assert gb.mem("mugs_live") == 0, "the cancelled mug is not launched"
