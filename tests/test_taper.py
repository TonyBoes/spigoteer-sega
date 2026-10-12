# Modes P6: CLASSIC's slanted (trapezoid) bars. A level's `taper` column (src/classic.c; 1 on levels 10-13 and all of wave
# 2) moves bar b's tap end (3 - b) * taper tile columns in from the screen edge: the top bar's keg 3 columns in, then 2, 1,
# the bottom bar's at the edge; the patrons still come in at the screen edge, the wall beyond the keg is plain wall. Every
# rule that used TAP_X / SPOUT_X / MUG_RIGHT_END / GLASS_X_RIGHT / PATRON_FAR_X uses the bar's own tap (bar_tap[b], set
# by mirror.c mirror_load from bits 4-5 of its dirs); an R bar is drawn mirrored as ever. With taper 0 nothing changes
# (every existing golden is the check). The LEVEL harness takes a taper through the test hook level_dirs (bits 4-5).
import pytest
from PIL import ImageChops

from conftest import (GAME, LAYOUT, bar_counter_row, bar_top_row, bar_top_y, check_golden, hold_stage_anim, logic_paused,
                      title_level, venue_rows)
from test_classic import (MAX_M, MAX_P, Mirror, close, entries, flipped, new_rom, run_both, scene, tile_data)
from test_classic_mode import built_rows, classic_at
from test_patrons import (DRINKING, EMPTY, FULL, PUSHED, clear_patrons, freeze, hold_mug, inject_mug, put, score,
                          set_patron)

pytestmark = pytest.mark.timeout(240)

TAP_X, SPOUT_X, MUG_RIGHT_END, GLASS_X_RIGHT = GAME["TAP_X"], GAME["SPOUT_X"], GAME["MUG_RIGHT_END"], GAME["GLASS_X_RIGHT"]
PLAYING, LIFE_LOST = 1, 2
TAPER = 0x10                       # level_dirs / mirror_load: taper 1 in bits 4-5
BASE_W = 23
S_FLIPX = 0x20


def taps(t):
    return [TAP_X - 8 * t * (3 - b) for b in range(4)]


def is_r(dirs, b):
    return (dirs >> b) & 1


def start_t(gb, dirs, lv=1):
    """The LEVEL harness at level lv with `dirs` (bits 0-3 the R bars, bits 4-5 the taper)."""
    gb.write("level_dirs", dirs)
    title_level(gb, lv)
    for _ in range(80):
        if gb.mem("game_state") == PLAYING:
            break
        gb.run(1)
    assert gb.mem("game_state") == PLAYING and gb.mem("bar_dirs") == dirs & 0xF
    gb.write("tip_chance", 0)
    gb.run(2)
    return gb


# ---- the table and the per-bar taps --------------------------------------------------------------------------------------
def test_the_table_slants_levels_10_to_26():
    for lv, row in enumerate(built_rows(), 1):
        assert row["taper"] == (1 if lv >= 10 else 0), lv


@pytest.mark.parametrize("lv", [1, 9, 10, 12, 13, 14, 23, 26, 27])
def test_each_level_sets_its_bars_taps(boot, lv):
    classic_at(boot, lv)
    t = 1 if lv >= 10 else 0
    assert list(boot.read("bar_tap", 4)) == taps(t)
    assert boot.mem("bartender_x") == taps(t)[0] and boot.mem("bar") == 0, "he starts at the top bar's tap"


def test_taper_0_leaves_every_bar_straight(gb):
    """The harness (and every mode but CLASSIC's slanted levels): every tap at TAP_X, every window at column 0."""
    assert list(gb.read("bar_tap", 4)) == [TAP_X] * 4 and list(gb.read("bar_bofs", 4)) == [0] * 4


def test_the_title_puts_the_bars_straight_again(boot):
    classic_at(boot, 23)
    assert list(boot.read("bar_tap", 4)) == taps(1)
    boot.write("game_state", 4)                       # GS_GAME_OVER: on to the initials / the table, then the title
    for _ in range(600):
        boot.press("start", 2)
        boot.run(3)
        if boot.mem("game_state") == 0:
            break
    assert boot.mem("game_state") == 0
    assert list(boot.read("bar_tap", 4)) == [TAP_X] * 4 and list(boot.read("bar_bofs", 4)) == [0] * 4


# ---- the picture -------------------------------------------------------------------------------------------------------
def window(theme):
    """The venue's three bar rows BASE_W wide, as load_venue builds them (columns 20.. plain wall: the wall rows' columns
    2..; the counter row's from the upper wall row)."""
    m, a = venue_rows(theme, "bar_map"), venue_rows(theme, "bar_attr")
    rows = []
    for r in range(3):
        src = r if r < 2 else 0
        rows.append(([m[r][c] for c in range(20)] + [m[src][c - 18] for c in range(20, BASE_W)],
                     [a[r][c] for c in range(20)] + [a[src][c - 18] for c in range(20, BASE_W)]))
    return rows


@pytest.mark.parametrize("dirs", [0, 0x5, 0xF])
def test_walls_keg_and_counter_at_each_bars_columns(boot, dirs):
    """Bar b shifted k = 3 - b columns: local column c shows the venue's column c + k (its keg at 17 - k .. 19 - k, plain
    wall beyond); an R bar the same mirrored (screen column 19 - c, flipped: CGB attribute bit 5, DMG flipped tile data).
    The wall rows from column 6 (the start patrons stand left of it), the counter row whole."""
    gb = start_t(boot, TAPER | dirs, 10)
    theme = gb.mem("cur_group")
    w = window(theme)
    tm = gb.bg_tilemap()
    cgb = gb.model_name == "cgb"
    for b in range(4):
        k = 3 - b
        for r in range(3):
            y = bar_top_row(b) + r
            want_t, want_a = w[r]
            for c in range(6 if r < 2 else 0, 20):
                src = want_t[c + k]
                sc = 19 - c if is_r(dirs, b) else c
                got = tm[y][sc] & 0xFF
                if cgb:
                    attr = gb.pb.memory[1, 0x9800 + y * 32 + sc]
                    assert got == src and attr == want_a[c + k] ^ (S_FLIPX if is_r(dirs, b) else 0), (b, r, c)
                elif is_r(dirs, b):
                    assert tile_data(gb, got) == flipped(tile_data(gb, src)), (b, r, c, src, got)
                else:
                    assert got == src, (b, r, c)
    assert gb.mem("mir_short") == 0


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("dirs", [0xF, 0x5])
def test_a_slanted_r_bar_is_the_slanted_l_bar_mirrored(model, dirs):
    """The scene of test_classic (walkers, drinkers, a watcher, a lifted patron, mugs, the coin, the bartender) on slanted
    bars: an R bar's picture is the L picture mirrored, pixel for pixel."""
    a, b = start_t(new_rom(model), TAPER, 10), start_t(new_rom(model), TAPER | dirs, 10)
    try:
        for x, y in ((a, b), (b, a)):
            while x.mem("intro_timer") > y.mem("intro_timer"):
                x.run(1)
        mixed = dirs != 0xF                       # (as test_classic: DMG mixed levels draw patrons at even x, no pushed one,
        lp = [scene(g, even=mixed, watcher_bar=1, pushed=not mixed) for g in (a, b)]   # the watcher on an L bar)
        for g in (a, b):                          # (bar 0's empty at 120 is past the top bar's end: keep it on its bar)
            with logic_paused(g):
                ms = g.read("mug_state", MAX_M)
                for i in range(MAX_M):
                    if ms[i] == EMPTY and g.read("mug_bar", MAX_M)[i] == 0:
                        put(g, "mug_x", i, 84)
        run_both(a, b, 4)
        mi = Mirror(a, b, dirs)
        mi.check()
        for f in range(30):
            run_both(a, b, 1)
            bad = mi.check()
            assert not bad, (f, bad)
        assert lp[0] == lp[1]
    finally:
        close(a, b)


# ---- the rules at each bar's own tap, L and R --------------------------------------------------------------------------
DIRS = [TAPER, TAPER | 0xF, TAPER | 0x5]


def quiet(gb):
    with logic_paused(gb):
        clear_patrons(gb)
        freeze(gb)
        for m in range(MAX_M):
            put(gb, "mug_state", m, 0)
        gb.write("mugs_live", 0)


@pytest.mark.parametrize("dirs", DIRS)
def test_the_bartender_snaps_walks_and_fills_at_each_bars_tap(boot, dirs):
    gb = start_t(boot, dirs)
    quiet(gb)
    tap = list(gb.read("bar_tap", 4))
    assert tap == taps(1)
    for b in range(4):
        if b:
            gb.press("down", 2)
            gb.run(2)
        assert gb.mem("bar") == b and gb.mem("bartender_x") == tap[b], b
        toward = "left" if is_r(dirs, b) else "right"
        away = "right" if is_r(dirs, b) else "left"
        gb.hold(away); gb.run(12); gb.release(away); gb.run(1)
        assert gb.mem("bartender_x") < tap[b]
        gb.hold(toward); gb.run(40); gb.release(toward); gb.run(1)
        assert gb.mem("bartender_x") == tap[b], "he walks no further than his bar's tap"
        gb.hold("a")
        gb.run(24)
        o = gb.oam()[4]
        sx = tap[b] + 16 + 8
        assert o["y"] and o["x"] == (168 - sx if is_r(dirs, b) else sx), (b, o)
        gb.release("a")
        gb.run(2)
        full = [i for i, s in enumerate(gb.read("mug_state", MAX_M)) if s == FULL]
        assert len(full) == 1 and gb.read("mug_bar", MAX_M)[full[0]] == b
        x = gb.read("mug_x", MAX_M)[full[0]]
        assert tap[b] + 16 - 6 <= x < tap[b] + 16, ("launched under the bar's spout", b, x)
        quiet(gb)


@pytest.mark.parametrize("dirs", DIRS)
def test_a_walker_costs_a_life_at_his_bars_tap(boot, dirs):
    gb = start_t(boot, dirs)
    for b in (0, 2):
        tap = gb.read("bar_tap", 4)[b]
        with logic_paused(gb):
            clear_patrons(gb)
            p = set_patron(gb, b, tap - 2)
            gb.write("intro_timer", 0)
            gb.write("spawn_timer", 255)
        lives = gb.mem("lives")
        seen = []
        for _ in range(200):
            gb.run(1)
            seen.append(gb.read("patron_x", MAX_P)[p])
            if gb.mem("lives") < lives:
                break
        assert gb.mem("lives") == lives - 1 and max(seen) <= tap, (b, tap, seen[-3:])
        gb.run(130)                                 # (the freeze, then play again)
        assert gb.mem("game_state") == PLAYING


@pytest.mark.parametrize("dirs", DIRS)
def test_an_empty_is_caught_at_the_bars_tap(boot, dirs):
    gb = start_t(boot, dirs)
    quiet(gb)
    b = 0
    tap = gb.read("bar_tap", 4)[b]
    with logic_paused(gb):
        gb.write("bar", b)
        gb.write("bartender_x", tap)
        m = inject_mug(gb, b, tap + 10, EMPTY)         # past him: only "at the tap he catches any empty" takes it
    s0 = score(gb)
    for _ in range(40):
        gb.run(1)
        if gb.read("mug_state", MAX_M)[m] == 0:
            break
    gb.run(1)
    assert gb.read("mug_state", MAX_M)[m] == 0 and score(gb) - s0 == 100 and gb.mem("lives") == 3


@pytest.mark.parametrize("dirs", DIRS)
def test_an_empty_off_the_near_end_breaks_past_the_bars_keg(boot, dirs):
    """The top bar (3 columns in): an empty the bartender misses breaks at x > tap + 32 (not at MUG_RIGHT_END), the glass
    at the bar's own end (GLASS_X_RIGHT - 24), mirrored on an R bar."""
    gb = start_t(boot, dirs)
    quiet(gb)
    b = 0
    tap = gb.read("bar_tap", 4)[b]
    assert tap + 32 < MUG_RIGHT_END
    with logic_paused(gb):
        gb.write("bar", 2)
        gb.write("bartender_x", 40)
        m = inject_mug(gb, b, tap + 28, EMPTY)
    lives = gb.mem("lives")
    xs = []
    for _ in range(30):
        gb.run(1)
        xs.append(gb.read("mug_x", MAX_M)[m])
        if gb.read("mug_state", MAX_M)[m] == 3:
            break
    gb.run(1)
    assert gb.read("mug_state", MAX_M)[m] == 3 and gb.mem("lives") == lives - 1
    assert gb.read("mug_x", MAX_M)[m] == tap + 33, xs
    gb.run(1)
    gx = [o["x"] for o in gb.oam()[5:26] if o["y"] and abs(o["y"] - (bar_top_y(b) + 16)) < 24]
    lo = tap + (GLASS_X_RIGHT - TAP_X) + 8 + 8          # glass_dx 8..16 from the bar's end cell, + OAM's 8
    want = [x for x in range(lo, lo + 17)]
    if is_r(dirs, b):
        want = [168 - x for x in want]
    assert gx and all(x in want for x in gx), (gx, want)


@pytest.mark.parametrize("dirs", DIRS)
def test_a_full_mug_off_the_far_end_is_unchanged(boot, dirs):
    gb = start_t(boot, dirs)
    quiet(gb)
    with logic_paused(gb):
        m = inject_mug(gb, 0, 24, FULL)
    lives = gb.mem("lives")
    for _ in range(20):
        gb.run(1)
        if gb.read("mug_state", MAX_M)[m] == 3:
            break
    gb.run(1)
    assert gb.read("mug_state", MAX_M)[m] == 3 and gb.mem("lives") == lives - 1 and gb.read("mug_x", MAX_M)[m] < 16


def test_fair_empties_count_the_bars_own_distance(boot):
    """empty_travel: an empty sent on the top bar has 24 px less to go; the schedule (next_arrival) says so."""
    gb = start_t(boot, TAPER)
    quiet(gb)
    got = []
    for b in (0, 3):
        with logic_paused(gb):
            clear_patrons(gb)
            gb.write("next_arrival", 0)
            gb.write(gb.addr("next_arrival") + 1, 0)
            gb.write("bar", 1 if b == 0 else 2)
            gb.write("bartender_x", 20)
            p = set_patron(gb, b, 40, state=DRINKING, timer=89, variant=0)
            hold_mug(gb, p, b)
        gb.run(3)
        got.append(gb.mem16("next_arrival"))
    tap = taps(1)
    a0, a3 = got
    assert a3 - a0 == (tap[3] - tap[0]) * 2, got


# ---- goldens: CLASSIC levels 13 (L R L R) and 23 (R R R R), slanted ------------------------------------------------------
def golden_play(boot, lv):
    gb = classic_at(boot, lv)
    hold_stage_anim(gb)
    tap = list(gb.read("bar_tap", 4))
    with logic_paused(gb):
        clear_patrons(gb)
        freeze(gb)
        for m in range(MAX_M):
            put(gb, "mug_state", m, 0)
        gb.write("mugs_live", 0)
        gb.write("tip_chance", 0)
        set_patron(gb, 0, 24, variant=0)
        set_patron(gb, 0, tap[0] - 30, variant=2)
        d = set_patron(gb, 1, 40, state=DRINKING, timer=40, variant=1)
        hold_mug(gb, d, 1)
        set_patron(gb, 2, 64, variant=1)
        p = set_patron(gb, 3, 50, state=PUSHED, aux=16, variant=0)
        hold_mug(gb, p, 3)
        inject_mug(gb, 2, tap[2] - 10, FULL)
        inject_mug(gb, 1, tap[1] - 30, EMPTY)
        gb.write("bar", 3)
        gb.write("bartender_x", tap[3])
        gb.write("facing", 0)
    gb.run(20)
    return gb


def test_golden_classic_taper(boot):
    """CLASSIC level 13 (the space bar, L R L R), slanted."""
    check_golden(golden_play(boot, 13), "classic_taper")


def test_golden_classic_taper_r(boot):
    """CLASSIC level 23 (the space bar, R R R R: the whole screen flipped), slanted."""
    check_golden(golden_play(boot, 23), "classic_taper_r")
