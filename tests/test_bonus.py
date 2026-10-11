# M6: the bonus round (can shell game). Situations are reached by poking level/level_clear.
import re

import pytest
from conftest import GAME, ROOT, check_golden, title_arcade, venue
ENTRY_X = GAME["ENTRY_X"]
from test_flow import (BONUS, LEVEL_CLEAR, PLAYING, clear_level, patrons, run_until, score, state, tile_id,
                       tilemap_row)

pytestmark = pytest.mark.timeout(120)

PH_SHOW, PH_SHAKE, PH_SWAP, PH_CHOOSE, PH_RESULT = range(5)
CF_STILL, CF_BURST, CF_OPEN = 0, 3, 4
SLOTS = [16 + 24 * i for i in range(6)]
ART_C = (ROOT / "build" / "art.c").read_text()
ART_H = (ROOT / "build" / "art.h").read_text()
OBJ_BONUS = 96
OBJ_CURSOR = OBJ_BONUS + 10                          # after the 5 can frames
GEYSER_TILES = range(OBJ_CURSOR + 2, OBJ_CURSOR + 14, 2)   # 3 left halves, 3 right halves
DROP_TILES = range(OBJ_CURSOR + 14, OBJ_CURSOR + 20, 2)    # tall, round, splat


def array(name):
    body = re.search(rf"const uint8_t {name}\[\d+\] = \{{(.*?)\}};", ART_C, re.S).group(1)
    return bytes(int(h, 16) for h in re.findall(r"0x([0-9A-F]{2})", body))


def art(name):
    return int(re.search(rf"#define {name} (\d+)", ART_H).group(1))


def can_pos(gb):
    return list(gb.read("can_pos", 6))


def phase(gb):
    return gb.mem("bonus_phase")


def enter_bonus(gb, level=2, rounds_before=0):
    gb.write("bonus_round", rounds_before)
    gb.write("level", level)
    gb.write("level_clear", 1)
    run_until(gb, lambda: state(gb) == BONUS, 400)


def to_phase(gb, ph, limit=2000):
    run_until(gb, lambda: phase(gb) == ph, limit)


def lines(gb):
    """Sprites per scanline from raw OAM (8x16 mode)."""
    counts = [0] * 160
    for s in gb.visible_sprites():
        for y in range(max(s["y"] - 16, 0), min(s["y"], 144)):
            counts[y] += 1
    return counts


def pick(gb, slot):
    to_phase(gb, PH_CHOOSE)
    gb.write("bonus_cursor", slot)
    gb.run(2)
    gb.press("a", 2)
    assert phase(gb) == PH_RESULT


def test_clearing_level_1_does_not_enter_the_bonus_round(gb):
    clear_level(gb)
    seen = set()
    for _ in range(250):
        gb.run(1)
        seen.add(state(gb))
    assert BONUS not in seen and state(gb) == PLAYING and gb.mem("level") == 2 and gb.mem("bonus_round") == 0


@pytest.mark.parametrize("lvl,after", [(2, 3), (4, 5)])
def test_clearing_even_levels_enters_the_bonus_round(gb, lvl, after):
    enter_bonus(gb, lvl)
    assert gb.mem("bonus_round") == 1 and phase(gb) == PH_SHOW and gb.mem("level") == lvl
    gb.run(5)
    assert not gb.is_blank()
    assert sorted(can_pos(gb)) == SLOTS
    pick(gb, 0)
    run_until(gb, lambda: state(gb) == PLAYING, 300)
    assert gb.mem("level") == after


def test_round_numbers_after_nine(gb):
    for lvl, expect in ((9, False), (10, True), (11, False), (12, True)):
        gb.write("level", lvl)
        gb.write("level_clear", 1)
        run_until(gb, lambda: state(gb) in (PLAYING, BONUS) and state(gb) != LEVEL_CLEAR, 400)
        assert (state(gb) == BONUS) == expect, lvl
        if expect:
            gb.write("bonus_phase", PH_RESULT)
            gb.write("bonus_timer", 129)
            run_until(gb, lambda: state(gb) == PLAYING, 40)
        gb.run(5)


def test_the_calm_can_is_never_shaken(gb):
    enter_bonus(gb)
    calm = gb.mem("bonus_calm_can")
    assert gb.mem("bonus_calm") == calm and calm < 6
    shaken_order = []
    while phase(gb) < PH_SWAP:
        gb.run(1)
        flags = list(gb.read("can_shake", 6))
        assert sum(flags) <= 1, "one can at a time"
        assert flags[calm] == 0
        assert gb.read("can_frame", 6)[calm] == CF_STILL
        for i, f in enumerate(flags):
            if f and i not in shaken_order:
                shaken_order.append(i)
    assert sorted(shaken_order) == [i for i in range(6) if i != calm], "the other five, each once"
    assert list(gb.read("can_shaken", 6)) == [0 if i == calm else 1 for i in range(6)]
    assert gb.read("can_frame", 6) == bytes(6), "all still again"


def test_shake_order_is_random_across_rounds(gb):
    orders = set()
    for r in range(3):
        enter_bonus(gb, 2)
        order, last = [], None
        while phase(gb) < PH_SWAP:
            gb.run(1)
            f = list(gb.read("can_shake", 6))
            if any(f) and f.index(1) != last:
                last = f.index(1)
                order.append(last)
        orders.add(tuple(order))
        gb.write("bonus_phase", PH_RESULT); gb.write("bonus_timer", 129)
        run_until(gb, lambda: state(gb) == PLAYING, 40)
        gb.run(2)
    assert len(orders) > 1


def test_swaps_preserve_positions_and_track_the_calm_can(gb):
    enter_bonus(gb)
    calm = gb.mem("bonus_calm_can")
    to_phase(gb, PH_SWAP)
    total = gb.mem("bonus_swaps_total")
    assert total == 7                              # 6 + round 1
    dur = gb.mem("bonus_swap_dur")
    done, moved_frames, hops = 0, 0, 0
    base_y = None
    while phase(gb) == PH_SWAP:
        gb.run(1)
        if gb.mem("bonus_moving"):
            moved_frames += 1
            cans = [s for s in gb.visible_sprites() if s["tile"] in range(96, 106, 2)]
            ys = [s["y"] for s in cans]
            if ys and min(ys) < max(ys):
                hops += 1                         # one can is up in the air
        else:
            assert sorted(can_pos(gb)) == SLOTS, "at rest the six slots are exactly filled"
            slot = gb.mem("bonus_calm")
            assert can_pos(gb)[calm] == SLOTS[slot], "bonus_calm follows the calm can"
            sc = list(gb.read("slot_can", 6))
            assert sorted(sc) == list(range(6)) and sc[slot] == calm
        done = gb.mem("bonus_swaps_done")
    assert done == total and moved_frames >= total * dur - 2 and hops >= total * (dur // 2)
    assert phase(gb) == PH_CHOOSE


def test_swaps_speed_up_from_the_third_round(gb):
    durs = []
    for r in (0, 3, 6, 9):                           # M12: rounds 1, 4, 7, 10 are the shake-ups (the others pour and catch tips)
        enter_bonus(gb, 2, rounds_before=r)
        assert gb.mem("bonus_kind") == 0
        durs.append(gb.mem("bonus_swap_dur"))
        gb.write("bonus_phase", PH_RESULT); gb.write("bonus_timer", 129)
        run_until(gb, lambda: state(gb) == PLAYING, 40)
        gb.run(2)
    assert durs[0] == durs[1] == 30 and durs[2] < 30 and durs[3] < durs[2]


def test_cursor_moves_with_left_and_right(gb):
    enter_bonus(gb)
    to_phase(gb, PH_CHOOSE)
    start = gb.mem("bonus_cursor")
    gb.press("right", 3)
    assert gb.mem("bonus_cursor") == start + 1
    gb.press("left", 3); gb.press("left", 3)
    assert gb.mem("bonus_cursor") == start - 1
    for _ in range(10):
        gb.press("left", 3)
    assert gb.mem("bonus_cursor") == 0
    arrows = [s for s in gb.visible_sprites() if s["tile"] == OBJ_CURSOR]
    assert len(arrows) == 1 and arrows[0]["x"] - 8 == SLOTS[0]


def test_picking_the_calm_can_wins_3000(gb):
    enter_bonus(gb)
    before = score(gb)
    to_phase(gb, PH_CHOOSE)
    pick(gb, gb.mem("bonus_calm"))
    assert gb.mem("bonus_won") == 1 and score(gb) == before + 3000
    gb.run(10)
    assert gb.read("can_frame", 6)[gb.mem("bonus_calm_can")] == CF_OPEN
    assert tile_id("GLYPH_W") in tilemap_row(gb, 4, 0, 20)
    assert tilemap_row(gb, 0, 1, 6) != [tile_id("GLYPH_0")] * 6, "HUD shows the new score"
    gb.run(40)
    check_golden(gb, "bonus_win")
    run_until(gb, lambda: state(gb) == PLAYING, 300)
    assert score(gb) == before + 3000


def _lose_setup(gb):
    enter_bonus(gb)
    before = score(gb)
    to_phase(gb, PH_CHOOSE)
    pick(gb, (gb.mem("bonus_calm") + 1) % 6)
    assert gb.mem("bonus_won") == 0 and score(gb) == before
    picked = gb.mem("bonus_picked")
    assert picked != gb.mem("bonus_calm_can")
    return before, picked


def test_picking_another_can_shoots_a_geyser_then_rains_soda_over_the_screen(gb):
    before, picked = _lose_setup(gb)
    can_x = can_pos(gb)[picked]
    can_top = GAME["CAN_TOP"] if "CAN_TOP" in GAME else 72
    bt_fail = 6 * art("BARTENDER_TILES_PER_FRAME")
    geyser_top, peak_t = 999, 0
    drops_seen, xs, ys, on_bartender = set(), set(), set(), 0
    worst = 0
    geyser_xs = set()
    max_geyser_sprites = 0
    drop_ys_by_frame = []
    for t in range(1, 125):
        gb.run(1)
        sp = gb.visible_sprites()
        worst = max(worst, max(lines(gb)))
        geys = [s for s in sp if s["tile"] in GEYSER_TILES]
        drops = [s for s in sp if s["tile"] in DROP_TILES]
        if geys:
            top = min(s["y"] for s in geys) - 16
            if top < geyser_top:
                geyser_top, peak_t = top, t
            geyser_xs |= {s["x"] - 8 for s in geys}
        for s in drops:
            xs.add(s["x"] - 8 + 4); ys.add(s["y"] - 16 + 8)
            if 70 <= s["x"] - 8 + 4 <= 90 and 112 <= s["y"] - 8 <= 140:
                on_bartender += 1
        if gb.mem("bonus_timer") == 40:
            held = [s["y"] for s in geys]
            assert len(geys) >= 8 and all(abs(s["x"] - 8 - can_x) <= 12 for s in geys), "full column right above the can"
            assert not drops or min(s["y"] for s in drops) > 0
        assert any(s["tile"] == bt_fail for s in sp), "bartender stays in the fail frame"
        assert not [s for s in sp if s["tile"] == OBJ_CURSOR], "no arrow in the way of the geyser"
    assert state(gb) == BONUS, "still in the ~2 s result"
    # a column rises straight up from the can: well above the can top, and always over the can's own x
    assert geyser_top <= can_top - 40, geyser_top
    assert all(can_x - 8 <= x <= can_x + 8 for x in geyser_xs)
    assert 14 <= peak_t <= 30, "it peaks within the first half second"
    # then the rain: drops all over the screen width, from the top half down to the floor
    assert min(xs) <= 30 and max(xs) >= 130, (min(xs), max(xs))
    assert min(ys) < 60 and max(ys) >= 130
    assert on_bartender >= 3, "a few drops land on the bartender"
    assert worst <= 10
    run_until(gb, lambda: state(gb) == PLAYING, 300)
    assert score(gb) == before and gb.mem("lives") == 3


def test_lose_result_golden(gb):
    before, picked = _lose_setup(gb)
    gb.run(47)
    assert gb.read("can_frame", 6)[picked] == CF_BURST
    assert gb.mem("bonus_timer") < 60
    check_golden(gb, "bonus_lose")
    # drops are in the air at the golden
    assert [s for s in gb.visible_sprites() if s["tile"] in DROP_TILES]


def test_drops_fall_with_gravity_and_drift_sideways(gb):
    _lose_setup(gb)
    gb.run(20)
    # gravity: the first drop (OAM entry 14) leaves the geyser head, drifts sideways and falls faster and faster
    ys, xs = [], []
    for _ in range(40):
        gb.run(1)
        e = bytes(gb.read("shadow_OAM", 160))[14 * 4:14 * 4 + 4]
        if e[0] and e[2] in DROP_TILES[:2]:
            ys.append((gb.mem("bonus_timer"), e[0])); xs.append(e[1])
    assert len(ys) >= 25, "the drop is in flight for a good while"
    ys = [y for _, y in ys]
    steps = [b - a for a, b in zip(ys, ys[1:])]
    assert steps[0] <= 0 < steps[-1], steps    # up first, then down
    assert all(b >= a - 1 for a, b in zip(steps, steps[1:])), f"never slows down (1 px of rounding) {steps}"
    assert abs(xs[-1] - xs[0]) >= 20, "and drifts sideways"


def test_lose_result_never_exceeds_ten_sprites_on_a_line_at_any_frame(gb):
    for cursor_off in (1, 2, 3):
        enter_bonus(gb)
        to_phase(gb, PH_CHOOSE)
        gb.write("bonus_cursor", (gb.mem("bonus_calm") + cursor_off) % 6)
        gb.run(2)
        gb.press("a", 2)
        for _ in range(126):
            gb.run(1)
            assert max(lines(gb)) <= 10
            assert len(gb.visible_sprites()) <= 40
        gb.write("bonus_timer", 129)
        run_until(gb, lambda: state(gb) == PLAYING, 40)
        gb.run(2)


def test_golden_mid_swap(gb):
    enter_bonus(gb)
    run_until(gb, lambda: gb.mem("bonus_phase") == PH_SWAP and gb.mem("bonus_swaps_done") == 1 and gb.mem("bonus_moving"), 1500)
    gb.run(14)
    assert gb.mem("bonus_moving")
    check_golden(gb, "bonus_swap")


def test_scanline_limit_holds_for_a_whole_round(gb):
    enter_bonus(gb)
    worst = 0
    wrong_done = False
    for n in range(2200):
        gb.run(1)
        if phase(gb) == PH_CHOOSE and not wrong_done:
            wrong_done = True
            gb.write("bonus_cursor", (gb.mem("bonus_calm") + 3) % 6)
            gb.run(2)
            gb.press("a", 2)
        worst = max(worst, max(lines(gb)))
        assert len(gb.visible_sprites()) <= 40
        if state(gb) == PLAYING:
            break
    assert state(gb) == PLAYING
    assert worst <= 10


def test_next_level_loads_and_the_bar_scene_is_intact(gb):
    enter_bonus(gb)
    pick(gb, 1)
    run_until(gb, lambda: state(gb) == PLAYING, 300)
    gb.run(20)
    assert gb.mem("level") == 3 and gb.mem("cur_group") == 2 and gb.mem("overlay_on") == 0
    assert patrons(gb) == [(b, ENTRY_X) for b in range(4)]
    assert tilemap_row(gb, 0, 17, 3) == [tile_id("GLYPH_L"), tile_id("GLYPH_0"), tile_id("GLYPH_3")]
    # bar rows are the level 3 venue's (the lodge): counter row of bar 0 = row 7, floor row 17 (M9)
    lodge = venue("lodge")
    assert tilemap_row(gb, 7, 0, 20) == lodge["bar_map"][40:60]
    assert tilemap_row(gb, 17, 0, 20) == [lodge["floor_tile"]] * 20
    # tile data: the shared BG set and the venue's, and the OBJ tiles the bonus round borrowed are the lodge's
    # show performers again
    bg = array("bar_tiles")
    vram = b"".join(bytes(gb.read(0x9000 + t * 16, 16)) for t in range(art("TILE_GENERIC_BASE"), art("BAR_TILE_COUNT")))
    assert vram == bg
    vt = b"".join(bytes(gb.read(0x9000 + (lodge["bar_base"] + t) * 16, 16)) for t in range(lodge["bar_n"]))
    assert vt == bytes(lodge["bar_tiles"])
    obj = b"".join(bytes(gb.read(0x8000 + t * 16, 16)) for t in range(96, 96 + 32))
    assert obj == bytes(lodge["show"])
    check_golden(gb, "bonus_after")


def test_new_game_resets_the_round_count(boot):
    boot.write("bonus_round", 5)
    title_arcade(boot)
    run_until(boot, lambda: state(boot) == PLAYING, 30)
    assert boot.mem("bonus_round") == 0
