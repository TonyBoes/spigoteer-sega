# M3: patrons (background tiles), full-mug catches, empty mugs, lives, level clear.
# Situations are set up by poking state through symbol addresses, as in test_mugs.
import pytest
from conftest import bar_top_row, bar_top_y, check_golden

pytestmark = pytest.mark.timeout(60)

MAX_P, MAX_M = 16, 24
NONE, WALKING, PUSHED, DRINKING = 0, 1, 2, 3
FREE, FULL, EMPTY, BREAKING = 0, 1, 2, 3
STEP, PUSHBACK, SERVE = 64, 4, 50     # level 1 values (level_table in main.c): 8 px per STEP frames, PUSHBACK*8 px back
PX = 8 * PUSHBACK
HELD = 4
SPACING = 32
START_BARS = [0, 2]                   # level 1 starts with patrons on these bars (start_mask 0x5)


import re as _re
from conftest import ROOT as _ROOT
_ART_H = (_ROOT / "build" / "art.h").read_text()
BASE = int(_re.search(r"#define BAR_TILE_COUNT (\d+)", _ART_H).group(1))
BG_TILES_TOTAL = BASE + int(_re.search(r"#define PATRON_TILES_PER_GROUP (\d+)", _ART_H).group(1))


def put(gb, name, i, v):
    gb.write(gb.addr(name) + i, v)


def patrons(gb):
    st = gb.read("patron_state", MAX_P)
    return [dict(i=i, state=st[i], bar=gb.read("patron_bar", MAX_P)[i], x=gb.read("patron_x", MAX_P)[i],
                 variant=gb.read("patron_variant", MAX_P)[i], timer=gb.read("patron_timer", MAX_P)[i])
            for i in range(MAX_P) if st[i]]


def drawn_tiles(variant, x, bar):
    """(column, [row0 ids, row1 ids]) the tilemap must show for a patron drawn at x (2 px granularity)."""
    x &= 0xFE
    first = BASE + variant * 24 + ((x >> 1) & 3) * 6
    return x >> 3, [[first + r * 3 + k for k in range(3)] for r in range(2)]


def map_ids(gb, bar, col):
    tm = gb.bg_tilemap()
    return [[t & 0xFF for t in tm[bar_top_row(bar) + r][col:col + 3]] for r in range(2)]


def mugs(gb):
    st = gb.read("mug_state", MAX_M)
    return [dict(i=i, state=st[i], bar=gb.read("mug_bar", MAX_M)[i], x=gb.read("mug_x", MAX_M)[i])
            for i in range(MAX_M) if st[i]]


def score(gb):
    return int.from_bytes(gb.read("score", 4), "little")


def clear_patrons(gb):
    for i in range(MAX_P):
        put(gb, "patron_state", i, 0)
    gb.write("patrons_live", 0)


def set_patron(gb, bar, x, state=WALKING, timer=0, variant=0, aux=0, frac=0):
    i = list(gb.read("patron_state", MAX_P)).index(0)
    for n, v in (("patron_state", state), ("patron_bar", bar), ("patron_x", x), ("patron_variant", variant),
                 ("patron_timer", timer), ("patron_aux", aux), ("patron_frac", frac), ("patron_draw", 255),
                 ("patron_mug", 255)):
        put(gb, n, i, v)
    gb.write("patrons_live", gb.mem("patrons_live") + 1)
    return i


def hold_mug(gb, patron, mug_bar_, state_timer=0):
    """Give `patron` a held mug (state 4) the way a catch does."""
    i = list(gb.read("mug_state", MAX_M)).index(0)
    for n, v in (("mug_state", HELD), ("mug_bar", mug_bar_), ("mug_x", 0), ("mug_timer", 0), ("mug_patron", patron)):
        put(gb, n, i, v)
    put(gb, "patron_mug", patron, i)
    gb.write("mugs_live", gb.mem("mugs_live") + 1)
    return i


def inject_mug(gb, bar, x, state=FULL):
    i = list(gb.read("mug_state", MAX_M)).index(0)
    for n, v in (("mug_state", state), ("mug_bar", bar), ("mug_x", x), ("mug_timer", 0)):
        put(gb, n, i, v)
    gb.write("mugs_live", gb.mem("mugs_live") + 1)
    return i


def freeze(gb):
    """Patrons neither move nor spawn for a long while (the intro delay)."""
    gb.write("intro_timer", 255)


def spawn_now(gb):
    """spawn_timer is 16-bit (level 1 spawns every 300 frames): zero both bytes."""
    gb.write("spawn_timer", 0)
    gb.write(gb.addr("spawn_timer") + 1, 0)


def go(gb):
    """Patrons move now, and no new ones spawn."""
    gb.write("intro_timer", 0)
    gb.write("spawn_timer", 255)


def test_boot_has_one_patron_on_each_start_bar(gb):
    ps = patrons(gb)
    assert len(ps) == 2 and gb.mem("patrons_live") == 2 and gb.mem("spawned") == 2
    assert sorted(p["bar"] for p in ps) == START_BARS == [b for b in range(4) if gb.mem("start_mask") >> b & 1]
    assert all(p["x"] == 0 and p["state"] == WALKING for p in ps)
    assert not gb.is_blank()


def test_patron_walks_8_px_per_step_time(gb):
    go(gb)
    gb.run(1)
    x0 = [p["x"] for p in patrons(gb)]
    gb.run(STEP)
    assert [p["x"] - a for p, a in zip(patrons(gb), x0)] == [8, 8]
    gb.run(STEP)
    assert [p["x"] - a for p, a in zip(patrons(gb), x0)] == [16, 16]


def test_intro_delay_holds_patrons(gb):
    assert gb.mem("intro_timer") > 0
    gb.run(10)
    assert all(p["x"] == 0 for p in patrons(gb))


def test_patron_waits_behind_another(gb):
    clear_patrons(gb)
    go(gb)
    a = set_patron(gb, 0, 72, state=DRINKING, timer=60)   # drinks for 30 more frames, standing still
    b = set_patron(gb, 0, 40)                             # exactly SPACING behind: may not step closer
    gb.run(25)
    assert gb.read("patron_x", MAX_P)[b] == 40, "blocked"
    gb.run(STEP)                                          # the drinker walks on; b follows at SPACING
    xa, xb = gb.read("patron_x", MAX_P)[a], gb.read("patron_x", MAX_P)[b]
    assert xa > 72 and xb > 40 and SPACING <= xa - xb <= SPACING + 1


def test_blocked_by_a_drinking_patron(gb):
    clear_patrons(gb)
    go(gb)
    set_patron(gb, 1, 72, state=DRINKING)
    b = set_patron(gb, 1, 40)
    gb.run(60)
    assert gb.read("patron_x", MAX_P)[b] == 40


def test_served_near_the_door_is_removed_and_scores(gb):
    freeze(gb)                     # the boot patrons: one on bars 0 and 2 at x = 0, drawn
    inject_mug(gb, 0, 18)          # reaches bar 0's patron (x 0-15) two frames later
    gb.run(12)
    ps = patrons(gb)
    assert sorted(p["bar"] for p in ps) == [2], "bar 0's patron left"
    assert score(gb) == SERVE
    assert list(gb.read("score_digits", 6)) == [0, 0, 0, 0, 5, 0]
    assert mugs(gb) == [], "the held mug is freed when its patron leaves"
    check_golden(gb, "served")


def test_served_further_in_is_pushed_back_then_drinks_and_returns_an_empty(gb):
    clear_patrons(gb)
    freeze(gb)
    p = set_patron(gb, 1, 64)
    inject_mug(gb, 1, 80)
    gb.run(3)
    assert gb.read("patron_state", MAX_P)[p] == PUSHED
    assert score(gb) == 0
    assert [m["state"] for m in mugs(gb)] == [HELD], "the caught mug stays with the patron"
    gb.run(PX + 4)
    assert gb.read("patron_x", MAX_P)[p] == 64 - PX
    assert gb.read("patron_state", MAX_P)[p] == DRINKING
    assert [m["state"] for m in mugs(gb)] == [HELD]
    gb.run(95)
    ms = mugs(gb)
    assert len(ms) == 1 and ms[0]["state"] == EMPTY and ms[0]["bar"] == 1
    assert gb.read("patron_state", MAX_P)[p] == WALKING
    x = ms[0]["x"]
    assert x >= (64 - PX) + 16
    gb.run(10)
    assert mugs(gb)[0]["x"] == x + 10, "1 px per frame to the right"


def test_pushed_patron_stops_at_the_patron_behind(gb):
    clear_patrons(gb)
    freeze(gb)
    behind = set_patron(gb, 3, 16)
    p = set_patron(gb, 3, 64)
    inject_mug(gb, 3, 80)
    gb.run(40)
    assert gb.read("patron_x", MAX_P)[behind] == 16
    assert gb.read("patron_x", MAX_P)[p] == 16 + SPACING, "keeps the spacing"
    assert gb.read("patron_state", MAX_P)[p] == DRINKING


def test_bartender_catches_an_empty_mug(gb):
    clear_patrons(gb)
    inject_mug(gb, 0, 120, EMPTY)
    gb.run(15)
    assert len(mugs(gb)) == 1 and mugs(gb)[0]["x"] > 120
    gb.run(15)
    assert mugs(gb) == []
    assert score(gb) == 100
    assert gb.mem("lives") == 3


def test_bartender_on_another_bar_misses_the_empty(gb):
    clear_patrons(gb)
    gb.press("down", 2)
    inject_mug(gb, 0, 130, EMPTY)
    gb.run(30)
    assert score(gb) == 0
    assert gb.mem("lives") == 2, "missed empty costs a life"
    assert [m["state"] for m in mugs(gb)] == [BREAKING]
    spr = gb.visible_sprites()
    assert any(s["x"] >= 144 + 8 and s["y"] - 16 < bar_top_y(1) for s in spr), "glass at the right end of bar 0"
    gb.run(40)
    assert mugs(gb) == []


def test_bartender_away_from_the_mug_misses_it(gb):
    clear_patrons(gb)
    gb.press("left", 20)                 # x = 104
    inject_mug(gb, 0, 130, EMPTY)
    gb.run(40)
    assert score(gb) == 0 and gb.mem("lives") == 2


def test_patron_reaching_the_tap_costs_a_life(gb):
    clear_patrons(gb)
    go(gb)
    set_patron(gb, 0, 127, frac=255)
    gb.run(4)
    assert patrons(gb) == []
    assert gb.mem("lives") == 2


def test_three_patrons_at_the_tap_on_one_frame_cost_one_life(gb):
    # was "end the game" while one incident could cost several lives; game over is covered in test_flow
    clear_patrons(gb)
    go(gb)
    for b in range(3):
        set_patron(gb, b, 127, frac=255)
    gb.run(5)
    assert gb.mem("lives") == 2 and gb.mem("game_over") == 0


def test_full_mug_slides_past_a_drinking_patron(gb):
    clear_patrons(gb)
    freeze(gb)
    drinker = set_patron(gb, 2, 80, state=DRINKING)
    walker = set_patron(gb, 2, 32)
    inject_mug(gb, 2, 136)
    gb.run(25)
    assert gb.read("patron_state", MAX_P)[drinker] == DRINKING
    assert gb.read("patron_state", MAX_P)[walker] == WALKING
    assert [m["state"] for m in mugs(gb)] == [FULL]
    gb.run(40)
    assert gb.read("patron_state", MAX_P)[walker] in (PUSHED, DRINKING)
    assert gb.read("patron_state", MAX_P)[drinker] == DRINKING
    assert [m["state"] for m in mugs(gb)] == [HELD], "the walker holds it, the drinker's hands are full"


def test_rightmost_patron_catches_first(gb):
    clear_patrons(gb)
    freeze(gb)
    a = set_patron(gb, 0, 96)
    b = set_patron(gb, 0, 48)
    inject_mug(gb, 0, 136)
    gb.run(40)
    assert gb.read("patron_state", MAX_P)[a] == PUSHED or gb.read("patron_state", MAX_P)[a] == DRINKING
    assert gb.read("patron_state", MAX_P)[b] == WALKING


def test_level_clear(gb):
    assert gb.mem("level_clear") == 0
    freeze(gb)
    gb.write("quota", 2)                 # the two start patrons are the whole level
    for b in START_BARS:
        inject_mug(gb, b, 16)
    gb.run(8)
    assert patrons(gb) == []
    assert score(gb) == 2 * SERVE + 1000          # M4: the screen-clear bonus
    assert gb.mem("level_clear") == 1


def test_level_not_clear_while_quota_remains(gb):
    clear_patrons(gb)
    freeze(gb)
    gb.run(5)
    assert gb.mem("spawned") < gb.mem("quota")
    assert gb.mem("level_clear") == 0


def test_spawning_stops_at_quota(gb):
    clear_patrons(gb)
    gb.write("quota", 3)                 # the 2 start patrons count: one more may spawn
    gb.write("intro_timer", 0)
    spawn_now(gb)
    gb.run(30)
    assert gb.mem("spawned") == 3 and len(patrons(gb)) == 1
    p = patrons(gb)[0]
    assert p["x"] <= 8 and p["state"] == WALKING
    spawn_now(gb)
    gb.run(300)
    assert gb.mem("spawned") == 3


def test_spawn_waits_for_a_free_door(gb):
    clear_patrons(gb)
    for b in range(4):
        set_patron(gb, b, 24, state=DRINKING)    # 24 < 32: door crowded everywhere
    gb.write("intro_timer", 0)
    spawn_now(gb)
    gb.write("spawned", 4)
    gb.run(60)
    assert gb.mem("spawned") == 4


def test_four_patrons_stepping_together_fit_in_vblank(gb):
    go(gb)
    for b in (1, 3):                     # level 1 starts on two bars; add the other two so four move together
        set_patron(gb, b, 0)
    for p in patrons(gb):                # all four at x = 7 and about to take the pixel that crosses into column 1
        put(gb, "patron_x", p["i"], 7)
        put(gb, "patron_frac", p["i"], 255)
        put(gb, "patron_draw", p["i"], 6)
    gb.write("hud_dirty", 3)             # HUD redraw in the same frame
    gb.run(8)
    assert all(p["x"] == 8 for p in patrons(gb))
    # The drain is budgeted: VBlank is 4560 cycles ~ 17.8 DIV ticks and the update starts
    # ~1000-1400 cycles in, so a drain longer than 12 ticks (3072 cycles) is a tear risk.
    ticks = gb.mem("drain_ticks_max")
    assert 0 < ticks <= 12, f"VRAM drain took {ticks} DIV ticks"
    assert gb.mem("hud_dirty") == 0
    # every bar has its patron redrawn at x = 8 (column 1) within a few frames (the budget spreads them out)
    for p in patrons(gb):
        col, ids = drawn_tiles(p["variant"], 8, p["bar"])
        assert col == 1 and map_ids(gb, p["bar"], 1) == ids, f"bar {p['bar']} patron drawn at columns 1-3"


def test_patron_tiles_reach_vram(gb):
    for p in patrons(gb):
        col, ids = drawn_tiles(p["variant"], 0, p["bar"])
        assert map_ids(gb, p["bar"], col) == ids, "3x2 patron tiles at columns 0-2, shift 0"
    # a known pixel position shows the matching pre-shifted tiles; the old columns are wall again
    go(gb)
    i = patrons(gb)[0]["i"]
    put(gb, "patron_x", i, 45)
    gb.run(5)
    p = patrons(gb)[0]
    col, ids = drawn_tiles(p["variant"], p["x"], p["bar"])
    assert (col, (p["x"] & 0xFE) >> 1 & 3) == (5, 2), "x 45 -> drawn at 44: column 5, shift 4 px"
    assert map_ids(gb, p["bar"], col) == ids
    tm = gb.bg_tilemap()
    assert all((t & 0xFF) < BASE for t in tm[bar_top_row(p["bar"])][0:5]), "nothing left behind at columns 0-4"


def test_patrons_golden(gb):
    gb.run(400)
    assert gb.mem("spawned") > 2
    check_golden(gb, "patrons")


def test_level_1_starts_on_exactly_the_configured_bars(gb):
    assert gb.mem("level") == 1 and gb.mem("start_mask") == 0x5 and gb.mem("start_per_bar") == 1
    assert sorted((p["bar"], p["x"]) for p in patrons(gb)) == [(0, 0), (2, 0)]
    tm = gb.bg_tilemap()
    base = int(__import__("re").search(r"BAR_TILE_COUNT (\d+)", (__import__("conftest").ROOT / "build" / "art.h").read_text()).group(1))
    for b in range(4):                           # patron tiles (ids >= BAR_TILE_COUNT) drawn on bars 0 and 2 only
        assert ((tm[bar_top_row(b)][0] & 0xFF) >= base) == (b in START_BARS), b


def test_level_1_patron_takes_at_least_15_s_to_reach_the_tap(gb):
    """From the door to the tap with no service: the first life is lost no earlier than 15 s (900 frames)."""
    gb.write("intro_timer", 0)                   # count from the first step, not from the intro (a conservative bound)
    for n in range(1, 1400):
        gb.run(1)
        if gb.mem("lives") < 3:
            break
    assert gb.mem("lives") == 2, "a patron eventually reaches the tap"   # both arrive together: still one life
    assert n >= 15 * 60, f"patron crossed in {n} frames ({n / 60:.1f} s)"


def test_two_patrons_reaching_the_tap_on_one_frame_cost_one_life(gb):
    clear_patrons(gb)
    go(gb)
    set_patron(gb, 0, 127, frac=255)
    set_patron(gb, 2, 127, frac=255)
    gb.run(4)
    assert gb.mem("lives") == 2 and gb.mem("game_state") == 2


def test_mug_breaking_and_patron_arriving_on_one_frame_cost_one_life(gb):
    clear_patrons(gb)
    go(gb)
    set_patron(gb, 0, 127, frac=255)
    inject_mug(gb, 1, 17)                # breaks at the left end on the next frame
    gb.run(6)
    assert gb.mem("lives") == 2 and gb.mem("game_state") == 2
    gb.run(30)
    assert gb.mem("lives") == 2
