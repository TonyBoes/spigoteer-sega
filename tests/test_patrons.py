# M3: patrons (background tiles), full-mug catches, empty mugs, lives, level clear.
# Situations are set up by poking state through symbol addresses, as in test_mugs.
import pytest
from conftest import check_golden

pytestmark = pytest.mark.timeout(60)

MAX_P, MAX_M = 16, 24
NONE, WALKING, PUSHED, DRINKING = 0, 1, 2, 3
FREE, FULL, EMPTY, BREAKING = 0, 1, 2, 3
STEP, PUSHBACK, SERVE = 40, 4, 50     # level 1 values (level_table in main.c)


def put(gb, name, i, v):
    gb.write(gb.addr(name) + i, v)


def patrons(gb):
    st = gb.read("patron_state", MAX_P)
    return [dict(i=i, state=st[i], bar=gb.read("patron_bar", MAX_P)[i], col=gb.read("patron_col", MAX_P)[i],
                 variant=gb.read("patron_variant", MAX_P)[i], timer=gb.read("patron_timer", MAX_P)[i])
            for i in range(MAX_P) if st[i]]


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


def set_patron(gb, bar, col, state=WALKING, timer=0, variant=0, aux=0):
    i = list(gb.read("patron_state", MAX_P)).index(0)
    for n, v in (("patron_state", state), ("patron_bar", bar), ("patron_col", col), ("patron_variant", variant),
                 ("patron_timer", timer), ("patron_aux", aux)):
        put(gb, n, i, v)
    gb.write("patrons_live", gb.mem("patrons_live") + 1)
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


def go(gb):
    """Patrons move now, and no new ones spawn."""
    gb.write("intro_timer", 0)
    gb.write("spawn_timer", 255)


def test_boot_has_one_patron_per_bar(gb):
    ps = patrons(gb)
    assert len(ps) == 4 and gb.mem("patrons_live") == 4 and gb.mem("spawned") == 4
    assert sorted(p["bar"] for p in ps) == [0, 1, 2, 3]
    assert all(p["col"] == 0 and p["state"] == WALKING for p in ps)
    assert not gb.is_blank()


def test_patron_advances_one_column_per_step(gb):
    go(gb)
    for p in patrons(gb):
        put(gb, "patron_timer", p["i"], 0)
    gb.run(STEP - 6)
    assert all(p["col"] == 0 for p in patrons(gb))
    gb.run(10)
    assert all(p["col"] == 1 for p in patrons(gb))
    gb.run(STEP)
    assert all(p["col"] == 2 for p in patrons(gb))


def test_intro_delay_holds_patrons(gb):
    assert gb.mem("intro_timer") > 0
    start = patrons(gb)
    gb.run(10)
    assert patrons(gb) == start or all(p["col"] == 0 for p in patrons(gb))


def test_patron_waits_behind_another(gb):
    clear_patrons(gb)
    go(gb)
    a = set_patron(gb, 0, 8)      # in front
    b = set_patron(gb, 0, 4)      # 4 behind: stepping would leave a gap of only 3 columns
    gb.run(30)
    assert gb.read("patron_col", MAX_P)[b] == 4, "blocked"
    gb.run(30)
    assert gb.read("patron_col", MAX_P)[a] == 9
    assert gb.read("patron_col", MAX_P)[b] == 5, "follows once there is room"


def test_blocked_by_a_drinking_patron(gb):
    clear_patrons(gb)
    go(gb)
    set_patron(gb, 1, 9, state=DRINKING)
    b = set_patron(gb, 1, 5, timer=STEP)
    gb.run(60)
    assert gb.read("patron_col", MAX_P)[b] == 5


def test_served_near_the_door_is_removed_and_scores(gb):
    freeze(gb)                     # the boot patrons: one per bar at column 0, drawn
    inject_mug(gb, 1, 18)          # reaches bar 1's patron (columns 0-1) two frames later
    gb.run(12)
    ps = patrons(gb)
    assert sorted(p["bar"] for p in ps) == [0, 2, 3], "bar 1's patron left"
    assert score(gb) == SERVE
    assert list(gb.read("score_digits", 6)) == [0, 0, 0, 0, 5, 0]
    assert mugs(gb) == [], "catching frees the mug"
    check_golden(gb, "served")


def test_served_further_in_is_pushed_back_then_drinks_and_returns_an_empty(gb):
    clear_patrons(gb)
    freeze(gb)
    p = set_patron(gb, 1, 8)
    inject_mug(gb, 1, 80)
    gb.run(3)
    assert gb.read("patron_state", MAX_P)[p] == PUSHED
    assert score(gb) == 0
    gb.run(4 * PUSHBACK + 4)
    assert gb.read("patron_col", MAX_P)[p] == 8 - PUSHBACK
    assert gb.read("patron_state", MAX_P)[p] == DRINKING
    assert mugs(gb) == []
    gb.run(95)
    ms = mugs(gb)
    assert len(ms) == 1 and ms[0]["state"] == EMPTY and ms[0]["bar"] == 1
    assert gb.read("patron_state", MAX_P)[p] == WALKING
    x = ms[0]["x"]
    assert x >= (8 - PUSHBACK) * 8 + 16
    gb.run(10)
    assert mugs(gb)[0]["x"] == x + 10, "1 px per frame to the right"


def test_pushed_patron_stops_at_the_patron_behind(gb):
    clear_patrons(gb)
    freeze(gb)
    behind = set_patron(gb, 3, 2)
    p = set_patron(gb, 3, 8)
    inject_mug(gb, 3, 80)
    gb.run(40)
    assert gb.read("patron_col", MAX_P)[behind] == 2
    assert gb.read("patron_col", MAX_P)[p] == 2 + 4, "keeps the spacing"
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
    assert any(s["x"] >= 144 + 8 and s["y"] - 16 < 56 for s in spr), "glass at the right end of bar 0"
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
    set_patron(gb, 0, 15, timer=STEP)
    gb.run(4)
    assert patrons(gb) == []
    assert gb.mem("lives") == 2


def test_three_patrons_at_the_tap_end_the_game(gb):
    clear_patrons(gb)
    go(gb)
    for b in range(3):
        set_patron(gb, b, 15, timer=STEP)
    gb.run(5)
    assert gb.mem("lives") == 0 and gb.mem("game_over") == 1


def test_full_mug_slides_past_a_drinking_patron(gb):
    clear_patrons(gb)
    freeze(gb)
    drinker = set_patron(gb, 2, 10, state=DRINKING)
    walker = set_patron(gb, 2, 4)
    inject_mug(gb, 2, 136)
    gb.run(25)
    assert gb.read("patron_state", MAX_P)[drinker] == DRINKING
    assert gb.read("patron_state", MAX_P)[walker] == WALKING
    assert [m["state"] for m in mugs(gb)] == [FULL]
    gb.run(40)
    assert gb.read("patron_state", MAX_P)[walker] in (PUSHED, DRINKING)
    assert gb.read("patron_state", MAX_P)[drinker] == DRINKING
    assert mugs(gb) == []


def test_rightmost_patron_catches_first(gb):
    clear_patrons(gb)
    freeze(gb)
    a = set_patron(gb, 0, 12)
    b = set_patron(gb, 0, 6)
    inject_mug(gb, 0, 136)
    gb.run(40)
    assert gb.read("patron_state", MAX_P)[a] == PUSHED or gb.read("patron_state", MAX_P)[a] == DRINKING
    assert gb.read("patron_state", MAX_P)[b] == WALKING


def test_level_clear(gb):
    assert gb.mem("level_clear") == 0
    freeze(gb)
    gb.write("quota", 4)                 # the four start patrons are the whole level
    for b in range(4):
        inject_mug(gb, b, 16)
    gb.run(8)
    assert patrons(gb) == []
    assert score(gb) == 4 * SERVE + 1000          # M4: the screen-clear bonus
    assert gb.mem("level_clear") == 1


def test_level_not_clear_while_quota_remains(gb):
    clear_patrons(gb)
    freeze(gb)
    gb.run(5)
    assert gb.mem("spawned") < gb.mem("quota")
    assert gb.mem("level_clear") == 0


def test_spawning_stops_at_quota(gb):
    clear_patrons(gb)
    gb.write("quota", 5)
    gb.write("intro_timer", 0)
    gb.write("spawn_timer", 0)
    gb.run(30)
    assert gb.mem("spawned") == 5 and len(patrons(gb)) == 1
    p = patrons(gb)[0]
    assert p["col"] <= 1 and p["state"] == WALKING
    gb.write("spawn_timer", 0)
    gb.run(300)
    assert gb.mem("spawned") == 5


def test_spawn_waits_for_a_free_door(gb):
    clear_patrons(gb)
    for b in range(4):
        set_patron(gb, b, 3, state=DRINKING)     # 3 < 4: door crowded everywhere
    gb.write("intro_timer", 0)
    gb.write("spawn_timer", 0)
    gb.write("spawned", 4)
    gb.run(60)
    assert gb.mem("spawned") == 4


def test_four_patrons_stepping_together_fit_in_vblank(gb):
    go(gb)
    for p in patrons(gb):
        put(gb, "patron_timer", p["i"], STEP)
    gb.write("hud_dirty", 3)             # HUD redraw in the same frame
    gb.run(8)
    assert all(p["col"] == 1 for p in patrons(gb))
    # The drain is budgeted: VBlank is 4560 cycles ~ 17.8 DIV ticks and the update starts
    # ~1000-1400 cycles in, so a drain longer than 12 ticks (3072 cycles) is a tear risk.
    ticks = gb.mem("drain_ticks_max")
    assert 0 < ticks <= 12, f"VRAM drain took {ticks} DIV ticks"
    assert gb.mem("hud_dirty") == 0
    # every bar has its patron redrawn at column 1 within a few frames (the budget spreads them out)
    tm = gb.bg_tilemap()
    for b in range(4):
        assert tm[2 + 4 * b][1] != tm[2 + 4 * b][3], f"bar {b} patron drawn at columns 1-2"


def test_patron_tiles_reach_vram(gb):
    tm = gb.bg_tilemap()
    base = gb.mem("patron_variant")  # noqa: F841 (variant of slot 0 is not needed here)
    for b in range(4):
        ids = {t & 0xFF for t in tm[2 + 4 * b][0:2] + tm[3 + 4 * b][0:2]}
        assert len(ids) == 4, "2x2 patron tiles at columns 0-1"
    # after a step the old column is wall/door again and the new position holds the patron
    go(gb)
    for p in patrons(gb):
        put(gb, "patron_timer", p["i"], STEP)
    gb.run(5)
    tm = gb.bg_tilemap()
    for b in range(4):
        assert tm[2 + 4 * b][1] != tm[2 + 4 * b][3], "patron now spans columns 1-2"


def test_patrons_golden(gb):
    gb.run(400)
    assert gb.mem("spawned") > 4
    check_golden(gb, "patrons")
