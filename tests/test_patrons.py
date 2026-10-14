# M3: patrons (background tiles), full-mug catches, empty mugs, lives, level clear.
# Situations are set up by poking state through symbol addresses, as in test_mugs.
import pytest
from conftest import GAME, bar_top_row, bar_top_y, check_golden

pytestmark = pytest.mark.timeout(60)

MAX_P, MAX_M = 16, 20
NONE, WALKING, PUSHED, DRINKING, LEAVING = 0, 1, 2, 3, 4   # LEAVING: served, sliding out past the left edge
FREE, FULL, EMPTY, BREAKING = 0, 1, 2, 3
WINDUP = GAME["WINDUP_FRAMES"]        # M8d: a finished drinker winds up this long before his empty slides
DRINK_MIN, DRINK_WAIT, DRINK_WINDUP = 0, 1, 2   # patron_aux while DRINKING (M8d)
STEP, PUSHBACK, SERVE = 64, 4, 50     # level 1 values (level_table in main.c): 8 px per STEP frames, PUSHBACK*8 px back
PX = 8 * PUSHBACK
FAR_X = GAME["PATRON_FAR_X"]          # M8a: 120, a walker here has reached the bartender's end
HELD = 4
SPACING = 32
ENTRY_X = GAME["ENTRY_X"]                # patrons are BG figures from here (left of it they enter / leave as sprites); a push of PX serves one at x <= PX - 16
START_BARS = [0, 2]                   # level 1 starts with patrons on these bars (start_mask 0x5)


import re as _re
from conftest import ROOT as _ROOT
_ART_H = (_ROOT / "build" / "art.h").read_text()
BASE = int(_re.search(r"#define PATRON_FIRST_TILE (\d+)", _ART_H).group(1))           # M13a: BAR_TILE_COUNT rounded up to even
SHIFT0_OFS = int(_re.search(r"#define PATRON_SHIFT0_OFS (\d+)", _ART_H).group(1))     # the shift-0 poses come last (OBJ-able)
SHIFTED = int(_re.search(r"#define PATRON_TILES_PER_GROUP (\d+)", _ART_H).group(1))     # M8b: 3 x 8 shifts x 6 = 144
BACK_BASE = BASE + SHIFTED                                                                # then 3 back views x 4 tiles
BG_TILES_TOTAL = BASE + int(_re.search(r"#define PATRON_GROUP_TILES (\d+)", _ART_H).group(1))


def put(gb, name, i, v):
    gb.write(gb.addr(name) + i, v)


def patrons(gb):
    st = gb.read("patron_state", MAX_P)
    return [dict(i=i, state=st[i], bar=gb.read("patron_bar", MAX_P)[i], x=gb.read("patron_x", MAX_P)[i],
                 variant=gb.read("patron_variant", MAX_P)[i], timer=gb.read("patron_timer", MAX_P)[i])
            for i in range(MAX_P) if st[i]]


def drawn_tiles(variant, x, bar):
    """(column, [row0 ids, row1 ids]) the tilemap must show for a patron drawn at x (M8b: 1 px, 8 shifts)."""
    first = pose_first(variant, x & 7)
    return x >> 3, [[first + 2 * k + r for k in range(3)] for r in range(2)]


def pose_first(variant, shift):
    """M13a (Option A): first tile id of a pose; stored column by column (column k: + 2k top, + 2k + 1 bottom), shifts
    1..7 first (variant * 42 + (shift - 1) * 6), the three shift-0 poses last (SHIFT0_OFS + variant * 6)."""
    return BASE + (SHIFT0_OFS + variant * 6 if shift == 0 else variant * 42 + (shift - 1) * 6)


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


def set_patron(gb, bar, x, state=WALKING, timer=0, variant=0, aux=0, frac=0, hurry=0):
    i = list(gb.read("patron_state", MAX_P)).index(0)
    for n, v in (("patron_state", state), ("patron_bar", bar), ("patron_x", x), ("patron_variant", variant),
                 ("patron_timer", timer), ("patron_aux", aux), ("patron_frac", frac), ("patron_draw", 255),
                 ("patron_mug", 255), ("patron_drinks", 0), ("patron_hurry", hurry), ("patron_dist", 0)):
        put(gb, n, i, v)
    gb.write("patrons_live", gb.mem("patrons_live") + 1)
    return i


def lineup(gb, spec):
    """M8b: {bar: [(x, variant, distracted)]}. Put patrons at those places. The level's own start patrons are moved there (not replaced: the game then
    redraws the columns they leave, and no stale figure stays in the tilemap); the rest are added."""
    pool = {}
    for p in sorted((p for p in patrons(gb)), key=lambda p: p["i"]):
        pool.setdefault(p["bar"], []).append(p["i"])
    slots = {}
    for b, row in spec.items():
        for x, v, d in row:
            if pool.get(b):
                i = pool[b].pop(0)
                draw = gb.read("patron_draw", MAX_P)[i]
                put(gb, "patron_x", i, x)
                put(gb, "patron_variant", i, v)
                if draw >> 3 == x >> 3:          # same columns, maybe another variant: a redraw with the CGB palette
                    put(gb, "patron_draw", i, 255)   # attributes too (a variant never changes in the game itself)
            else:
                i = set_patron(gb, b, x, variant=v)
            put(gb, "patron_dist", i, d)
            slots[(b, x)] = (i, v, d)
    assert not any(pool.values()), "a start patron has no place in the lineup"
    return slots


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
    assert all(p["x"] == ENTRY_X and p["state"] == WALKING for p in ps)
    assert not gb.is_blank()


def test_patron_walks_7_px_per_step_time(gb):
    go(gb)
    gb.run(1)
    x0 = [p["x"] for p in patrons(gb)]
    gb.run(STEP)
    assert [p["x"] - a for p, a in zip(patrons(gb), x0)] == [7, 7]     # door fix: speed x 13/15 (28/256 px per frame)
    gb.run(STEP)
    assert [p["x"] - a for p, a in zip(patrons(gb), x0)] == [14, 14]


def test_intro_delay_holds_patrons(gb):
    assert gb.mem("intro_timer") > 0
    gb.run(10)
    assert all(p["x"] == ENTRY_X for p in patrons(gb))


def test_a_walker_walks_up_to_and_past_a_drinker(gb):
    """M13b (was: he waited PATRON_SPACING behind): a walker closes in on a drinker and walks on through him; the
    drinker drinks on where he stands."""
    clear_patrons(gb)
    go(gb)
    a = set_patron(gb, 0, 72, state=DRINKING, timer=0)    # drinks (sways) on the spot for 90 frames
    b = set_patron(gb, 0, 40)
    gb.run(25)
    assert gb.read("patron_x", MAX_P)[b] > 40, "not blocked 32 px behind him"
    put(gb, "patron_frac", b, 0)
    for _ in range(40):                                   # (a fast walk: 1 px a frame)
        gb.write("patron_speed", 255)
        gb.run(1)
    xb = gb.read("patron_x", MAX_P)[b]
    assert xb > 72, "walked past the drinker"
    assert gb.read("patron_x", MAX_P)[a] == 72 and gb.read("patron_state", MAX_P)[a] == DRINKING


def test_walkers_pass_a_drinking_patron_one_column_at_a_time(gb):
    """M13b (was: blocked by a drinker): two walkers behind one drinker; the first passes; the second, a step behind
    the first, waits only while stepping would put three patrons in one tile column."""
    clear_patrons(gb)
    go(gb)
    d = set_patron(gb, 1, 74, state=DRINKING, timer=0)    # (x 74, swaying to 76: always columns 9-11)
    w1 = set_patron(gb, 1, 60)
    w2 = set_patron(gb, 1, 56)
    cols = []
    for _ in range(80):
        gb.write("patron_speed", 128)
        gb.run(1)
        dr = gb.read("patron_draw", MAX_P)
        cols.append(max(sum(1 for p in (d, w1, w2) if dr[p] != 255 and real_cols(dr[p]).__contains__(c)) for c in range(20)))
    assert max(cols) <= 2, "never three patrons in a tile column"
    assert gb.read("patron_x", MAX_P)[w1] > 74 + 8, "the first walker passed the drinker"


def real_cols(d):
    """The tile columns a patron drawn at d really covers (M13b: 2 at shift 0 and in a back view, else 3)."""
    c = (d & 0x7F) >> 3
    return range(c, c + (3 if d & 7 else 2))


def test_served_near_entry_x_scores_slides_out_and_is_removed(gb):
    freeze(gb)                     # the boot patrons: one on bars 0 and 2 at x = ENTRY_X, drawn
    inject_mug(gb, 0, ENTRY_X + 18)          # reaches bar 0's patron (x 16-31) two frames later
    gb.run(12)
    assert [p["state"] for p in patrons(gb) if p["bar"] == 0] == [LEAVING], "served: sliding out past the left edge"
    assert score(gb) == 0 and gb.mem("served") == 0, "(it counts when he is off the screen)"
    gb.run(30)
    ps = patrons(gb)
    assert sorted(p["bar"] for p in ps) == [2], "bar 0's patron left"
    assert mugs(gb) == [], "the held mug is freed when its patron is gone"
    assert score(gb) == SERVE and gb.mem("served") == 1
    assert list(gb.read("score_digits", 6)) == [0, 0, 0, 0, 5, 0]
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
    gb.run(95 + WINDUP)                           # M8d: the wind-up comes before the empty slides
    ms = mugs(gb)
    assert len(ms) == 1 and ms[0]["state"] == EMPTY and ms[0]["bar"] == 1
    assert gb.read("patron_state", MAX_P)[p] == WALKING
    x = ms[0]["x"]
    assert x >= (64 - PX) + 16
    gb.run(10)
    assert mugs(gb)[0]["x"] == x + 5, "M8a: 0.5 px per frame to the right"


def catch_once(gb, p, bar):
    """Inject a full mug at the patron's left edge + 4 and run until the push is over and he drinks."""
    inject_mug(gb, bar, gb.read("patron_x", MAX_P)[p] + 4)
    gb.run(3)
    assert gb.read("patron_state", MAX_P)[p] == PUSHED
    for _ in range(400):
        gb.run(1)
        if gb.read("patron_state", MAX_P)[p] != PUSHED:
            break


def test_every_mug_pushes_the_same_distance(gb):
    """Owner 2026-10-13 (the arcade's rule): no thirst multiplier. The 1st, 2nd and 3rd mug each push a patron
    pushback_px (32 px on level 1) back; he walks on in between (frozen here: skip the drink by poking his state)."""
    clear_patrons(gb)
    freeze(gb)
    p = set_patron(gb, 1, 120)
    x = 120
    for n in (1, 2, 3):
        catch_once(gb, p, 1)
        assert gb.read("patron_drinks", MAX_P)[p] == n
        assert gb.read("patron_x", MAX_P)[p] == x - PX, (n, "the same push every time")
        x -= PX
        put(gb, "patron_state", p, WALKING)                # skip the drink: walk resumes (frozen, so he stays put)
        gb.run(2)
        for i in range(MAX_M):                              # drop the returned empty
            put(gb, "mug_state", i, FREE)
        gb.write("mugs_live", 0)


def test_a_mid_bar_patron_needs_several_mugs_and_is_served_off_the_screen(gb):
    """x 60 on level 1: 60 -> 28 -> (a push that would leave 12 px of him on the screen stops him at ENTRY_X, 16) -> the
    third mug carries him off: served. Nothing counts until he is off the screen."""
    clear_patrons(gb)
    freeze(gb)
    p = set_patron(gb, 1, 60)
    gb.run(3)
    xs = []
    for n in range(3):
        if n == 2:
            inject_mug(gb, 1, gb.read("patron_x", MAX_P)[p] + 4)
            gb.run(8)
            break
        catch_once(gb, p, 1)
        xs.append(gb.read("patron_x", MAX_P)[p])
        assert gb.read("patron_state", MAX_P)[p] == DRINKING and score(gb) == 0
        put(gb, "patron_state", p, WALKING)
        gb.run(2)
        for i in range(MAX_M):
            put(gb, "mug_state", i, FREE)
        gb.write("mugs_live", 0)
    assert xs[:2] == [60 - PX, ENTRY_X], xs
    assert gb.read("patron_state", MAX_P)[p] == LEAVING, "the third mug: served out"
    assert gb.mem("served") == 0 and score(gb) == 0
    gb.run(2 * ENTRY_X + 8)
    assert gb.read("patron_state", MAX_P)[p] == NONE, "slid out past the left edge"
    assert gb.mem("served") == 1 and score(gb) == SERVE


def test_a_serve_happens_only_off_the_screen(gb):
    """The push serves a patron only if x + 16 <= push (level 1: x <= 16). At x = 17 it would leave a pixel on the
    screen: he stops at ENTRY_X and drinks, unserved; at x = 16 the same mug takes him off."""
    for x, served in ((ENTRY_X + 1, False), (ENTRY_X, True)):
        clear_patrons(gb)
        freeze(gb)
        gb.write("served", 0)
        p = set_patron(gb, 1, x)
        gb.run(3)
        inject_mug(gb, 1, x + 4)
        gb.run(3 + PX + 4)
        st = gb.read("patron_state", MAX_P)[p]
        if served:
            assert st in (LEAVING, NONE)
            gb.run(2 * ENTRY_X + 8)
            assert gb.mem("served") == 1 and score(gb) == SERVE
        else:
            assert st == DRINKING and gb.read("patron_x", MAX_P)[p] == ENTRY_X
            assert gb.mem("served") == 0 and score(gb) == 0


def test_the_hard_rows_push_24_px(gb):
    """The two hardest rows (zoo, space lounge) push 24 px a mug: a patron at ENTRY_X + 4 is stopped at ENTRY_X, drinking,
    unserved; the next mug serves him (one at the old door is always served, so no patron is ever stuck)."""
    from test_edge import goto_level
    goto_level(gb, 9)
    assert gb.mem("pushback_px") == 24
    clear_patrons(gb)
    freeze(gb)
    gb.write("level", 1)                              # (no early drinkers: the zoo is level 9)
    p = set_patron(gb, 1, ENTRY_X + 4)
    gb.run(3)
    inject_mug(gb, 1, ENTRY_X + 8)
    gb.run(3 + 12)
    assert gb.read("patron_state", MAX_P)[p] == DRINKING and gb.read("patron_x", MAX_P)[p] == ENTRY_X and gb.mem("served") == 0
    put(gb, "patron_state", p, WALKING)
    for i in range(MAX_M):
        put(gb, "mug_state", i, FREE)
    gb.write("mugs_live", 0)
    gb.run(2)
    inject_mug(gb, 1, ENTRY_X + 4)
    gb.run(3 + 2 * ENTRY_X + 12)
    assert gb.read("patron_state", MAX_P)[p] == NONE and gb.mem("served") == 1


def test_some_patrons_drink_early(gb):
    """From level 2 a patron may take only a quarter or a half of the push and drink at once (never on level 1).
    Many mugs on fresh patrons at x 120: some stop after PX / 4 or PX / 2, the rest slide the whole PX; on level 1 none."""
    def trial(level, n=40):
        out = []
        gb.write("level", level)
        for k in range(n):
            clear_patrons(gb)
            freeze(gb)
            for i in range(MAX_M):
                put(gb, "mug_state", i, FREE)
            gb.write("mugs_live", 0)
            p = set_patron(gb, 1, 120)
            inject_mug(gb, 1, 124)
            gb.run(3 + PX + 4)
            out.append(120 - gb.read("patron_x", MAX_P)[p])
        return out
    first = trial(1)
    assert set(first) == {PX}, first
    later = trial(10)
    assert set(later) <= {PX, PX // 2, PX // 4}, later
    assert PX in later and (PX // 2 in later or PX // 4 in later), later


def test_a_new_patron_starts_thirsty_again(gb):
    clear_patrons(gb)
    freeze(gb)
    p = set_patron(gb, 1, 100)
    put(gb, "patron_drinks", p, 3)
    put(gb, "patron_state", p, NONE); gb.write("patrons_live", 0)
    spawn_now(gb)
    gb.write("intro_timer", 0)
    gb.run(5)
    assert all(d == 0 for d in gb.read("patron_drinks", MAX_P)), "spawned patrons reset their drink count"


def test_pushed_patron_slides_through_the_patron_behind(gb):
    """M13b (was: he stopped at PATRON_SPACING from the patron behind and got no push-back): he slides back his full
    push-back through the patron behind, who stays where he is; both are drawn (one of them lifted)."""
    clear_patrons(gb)
    freeze(gb)
    behind = set_patron(gb, 3, 24)
    p = set_patron(gb, 3, 64)
    inject_mug(gb, 3, 80)
    gb.run(3 + PX + 6)
    assert gb.read("patron_x", MAX_P)[behind] == 24 and gb.read("patron_state", MAX_P)[behind] == WALKING
    assert gb.read("patron_x", MAX_P)[p] == 64 - PX, "full push-back, through him"
    assert gb.read("patron_state", MAX_P)[p] == DRINKING


def clump(gb, bar, xs):
    """Patrons at xs on `bar`, the first nearest the left end."""
    return [set_patron(gb, bar, x, variant=k % 3) for k, x in enumerate(xs)]


def test_the_front_of_a_clump_is_pushed_back_through_it(gb):
    """The owner's stall: a clump of walkers PATRON_SPACING apart; the front one caught a mug and (blocked by the one
    behind) drank in place, every time, and the row never moved. M13b: he slides back his full push-back through the
    others, nobody else moves (no shoving), and a drinker in his minimum drink drinks on."""
    clear_patrons(gb)
    freeze(gb)
    back, mid, front = clump(gb, 1, [40, 40 + SPACING, 40 + 2 * SPACING])
    put(gb, "patron_state", mid, DRINKING)            # a drinker in his minimum drink
    put(gb, "patron_timer", mid, 10)
    inject_mug(gb, 1, 40 + 2 * SPACING + 4)
    gb.run(3 + PX + 4)
    xs, st = gb.read("patron_x", MAX_P), gb.read("patron_state", MAX_P)
    assert xs[front] == 40 + 2 * SPACING - PX, "the front patron gets his full push-back"
    assert st[front] == DRINKING
    assert xs[mid] == 40 + SPACING and st[mid] == DRINKING and gb.read("patron_aux", MAX_P)[mid] == DRINK_MIN
    assert xs[back] == 40 and st[back] == WALKING, "nobody is shoved"
    assert gb.mem("served") == 0


def test_a_patron_pushed_while_overlapping_drinks_and_is_drawn_where_he_stands(gb):
    clear_patrons(gb)
    freeze(gb)
    back, front = clump(gb, 2, [60, 60 + SPACING])
    gb.run(2)
    inject_mug(gb, 2, 60 + SPACING + 4)
    gb.run(3 + PX + 4)
    xs = gb.read("patron_x", MAX_P)
    assert xs[front] == 60 + SPACING - PX == 60 and xs[back] == 60, "he ends on top of the one behind"
    assert gb.read("patron_state", MAX_P)[back] == WALKING
    lift = gb.read("patron_lift", MAX_P)
    assert (lift[front] & 3) or (lift[back] & 3), "one of them is drawn as a sprite"
    bg = back if lift[front] & 3 else front
    d = gb.read("patron_draw", MAX_P)[bg]
    col, ids = drawn_tiles(gb.read("patron_variant", MAX_P)[bg], d, 2)
    assert map_ids(gb, 2, col) == ids, "the other one is on the BG where he stands"


def test_a_clump_served_over_and_over_is_cleared(gb):
    """Serve the front patron of a clump whenever he can catch (walking, or a finished drinker per M8d): the row must
    clear (before M13b the front one caught every mug in place and the row never moved)."""
    clear_patrons(gb)
    go(gb)
    gb.write("spawned", gb.mem("quota"))              # no new patrons
    gb.write("tip_chance", 0)
    lives = gb.mem("lives")
    clump(gb, 1, [16, 16 + SPACING, 16 + 2 * SPACING, 16 + 3 * SPACING])
    max_front, catches = 0, 0
    for f in range(3000):
        st, xs, aux = gb.read("patron_state", MAX_P), gb.read("patron_x", MAX_P), gb.read("patron_aux", MAX_P)
        live = [i for i in range(MAX_P) if st[i] and gb.read("patron_bar", MAX_P)[i] == 1]
        if not live:
            break
        front = max(live, key=lambda i: xs[i])
        max_front = max(max_front, xs[front])
        ms = gb.read("mug_state", MAX_M)
        for i in range(MAX_M):                        # the bartender's side is not under test: drop the empties
            if ms[i] == EMPTY:
                put(gb, "mug_state", i, FREE)
                gb.write("mugs_live", gb.mem("mugs_live") - 1)
        if FULL not in ms and (st[front] == WALKING or (st[front] == DRINKING and aux[front] != DRINK_MIN)):
            x0 = xs[front]
            inject_mug(gb, 1, x0 + 4)
            gb.run(3)
            if gb.read("patron_state", MAX_P)[front] in (PUSHED, LEAVING, NONE):
                catches += 1
                for _ in range(PX + 2):                # every catch moves him back (or out)
                    gb.run(1)
                    if gb.read("patron_state", MAX_P)[front] != PUSHED:
                        break
                st2, x2 = gb.read("patron_state", MAX_P)[front], gb.read("patron_x", MAX_P)[front]
                assert st2 in (NONE, LEAVING) or x2 <= max(x0 - PX, ENTRY_X), (f, x0, x2, st2)   # (a push that falls short stops at ENTRY_X)
            continue
        gb.run(1)
    else:
        raise AssertionError(f"bar 1 never cleared; front patron at x {max_front}")
    assert gb.mem("lives") == lives, "nobody reached the tap"
    assert gb.mem("served") == 4 and catches >= 4


def test_bartender_catches_an_empty_mug(gb):
    clear_patrons(gb)
    inject_mug(gb, 0, 104, EMPTY)                 # M8a: 16 px from the bartender at the fill position (x 120)
    gb.run(15)
    assert len(mugs(gb)) == 1 and mugs(gb)[0]["x"] > 104
    gb.run(25)
    assert mugs(gb) == []
    assert score(gb) == 100
    assert gb.mem("lives") == 3


def test_bartender_on_another_bar_misses_the_empty(gb):
    clear_patrons(gb)
    gb.press("down", 2)
    inject_mug(gb, 0, 130, EMPTY)
    gb.run(50)                                    # M8a: 0.5 px per frame, 23 px to the right end
    assert score(gb) == 0
    assert gb.mem("lives") == 2, "missed empty costs a life"
    assert [m["state"] for m in mugs(gb)] == [BREAKING]
    spr = gb.visible_sprites()
    assert any(s["x"] >= 144 + 8 and s["y"] - 16 < bar_top_y(1) for s in spr), "glass at the right end of bar 0"
    gb.run(40)
    assert mugs(gb) == []


def test_bartender_away_from_the_mug_misses_it(gb):
    clear_patrons(gb)
    gb.press("left", 20)                 # x = 90
    inject_mug(gb, 0, 130, EMPTY)
    gb.run(60)
    assert score(gb) == 0 and gb.mem("lives") == 2


def test_patron_reaching_the_tap_costs_a_life(gb):
    clear_patrons(gb)
    go(gb)
    set_patron(gb, 0, FAR_X - 1, frac=255)
    gb.run(4)
    assert patrons(gb) == []
    assert gb.mem("lives") == 2


def test_three_patrons_at_the_tap_on_one_frame_cost_one_life(gb):
    # was "end the game" while one incident could cost several lives; game over is covered in test_flow
    clear_patrons(gb)
    go(gb)
    for b in range(3):
        set_patron(gb, b, FAR_X - 1, frac=255)
    gb.run(5)
    assert gb.mem("lives") == 2 and gb.mem("game_over") == 0


def test_full_mug_slides_past_a_drinking_patron(gb):
    clear_patrons(gb)
    freeze(gb)
    drinker = set_patron(gb, 2, 80, state=DRINKING)
    walker = set_patron(gb, 2, 48)
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
        inject_mug(gb, b, ENTRY_X + 8)
    gb.run(8 + 2 * ENTRY_X + 2)                    # (served at ENTRY_X, they slide out past the left edge)
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
    assert 0 <= p["x"] <= 8 and p["state"] == WALKING        # (sliding in from the left edge, x 0 -> 16)
    spawn_now(gb)
    gb.run(300)
    assert gb.mem("spawned") == 3


def test_spawn_waits_for_a_free_left_end(gb):
    clear_patrons(gb)
    for b in range(4):
        set_patron(gb, b, 24, state=DRINKING)    # 24 < 32: the left end crowded everywhere
    gb.write("intro_timer", 0)
    spawn_now(gb)
    gb.write("spawned", 4)
    gb.run(60)
    assert gb.mem("spawned") == 4


def test_four_patrons_stepping_together_fit_in_vblank(gb):
    go(gb)
    for b in (1, 3):                     # level 1 starts on two bars; add the other two so four move together
        set_patron(gb, b, ENTRY_X)
    for p in patrons(gb):                # all four at x = 23 and about to take the pixel that crosses into column 3
        put(gb, "patron_x", p["i"], ENTRY_X + 7)
        put(gb, "patron_frac", p["i"], 255)
        put(gb, "patron_draw", p["i"], ENTRY_X + 7)
    gb.write("hud_dirty", 3)             # HUD redraw in the same frame
    gb.run(8)
    assert all(p["x"] == ENTRY_X + 8 for p in patrons(gb))
    # The drain is budgeted: VBlank is 4560 cycles ~ 17.8 DIV ticks and the update starts
    # ~1000-1400 cycles in, so a drain longer than 12 ticks (3072 cycles) is a tear risk.
    ticks = gb.mem("drain_ticks_max")
    assert 0 < ticks <= 12, f"VRAM drain took {ticks} DIV ticks"
    assert gb.mem("hud_dirty") == 0
    # every bar has its patron redrawn at x = 24 (column 3) within a few frames (the budget spreads them out)
    for p in patrons(gb):
        col, ids = drawn_tiles(p["variant"], ENTRY_X + 8, p["bar"])
        assert col == 3 and map_ids(gb, p["bar"], 3) == ids, f"bar {p['bar']} patron drawn at columns 3-5"


def test_patron_tiles_reach_vram(gb):
    for p in patrons(gb):
        col, ids = drawn_tiles(p["variant"], ENTRY_X, p["bar"])
        assert col == 2 and map_ids(gb, p["bar"], col) == ids, "3x2 patron tiles at columns 2-4, shift 0"
    # a known pixel position shows the matching pre-shifted tiles; the old columns are wall again
    go(gb)
    i = patrons(gb)[0]["i"]
    put(gb, "patron_x", i, 45)
    gb.run(5)
    p = patrons(gb)[0]
    col, ids = drawn_tiles(p["variant"], p["x"], p["bar"])
    assert (col, p["x"] & 7) == (5, 5), "x 45 -> drawn at 45: column 5, shift 5 px"
    assert gb.read("patron_draw", MAX_P)[i] == 45
    assert map_ids(gb, p["bar"], col) == ids
    tm = gb.bg_tilemap()
    assert all((t & 0xFF) < BASE for t in tm[bar_top_row(p["bar"])][0:5]), "nothing left behind at columns 0-4 (bare wall tiles)"


def test_patrons_golden(gb):
    gb.run(400)
    assert gb.mem("spawned") > 2
    check_golden(gb, "patrons")


def test_level_1_starts_on_exactly_the_configured_bars(gb):
    assert gb.mem("level") == 1 and gb.mem("start_mask") == 0x5 and gb.mem("start_per_bar") == 1
    assert sorted((p["bar"], p["x"]) for p in patrons(gb)) == [(0, ENTRY_X), (2, ENTRY_X)]
    tm = gb.bg_tilemap()
    base = int(__import__("re").search(r"BAR_TILE_COUNT (\d+)", (__import__("conftest").ROOT / "build" / "art.h").read_text()).group(1))
    for b in range(4):                           # patron tiles (ids >= BAR_TILE_COUNT) drawn on bars 0 and 2 only
        assert ((tm[bar_top_row(b)][ENTRY_X >> 3] & 0xFF) >= base) == (b in START_BARS), b


def test_level_1_patron_takes_at_least_15_s_to_reach_the_tap(gb):
    """From ENTRY_X to the tap with no service: the first life is lost no earlier than 15 s (900 frames)."""
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
    set_patron(gb, 0, FAR_X - 1, frac=255)
    set_patron(gb, 2, FAR_X - 1, frac=255)
    gb.run(4)
    assert gb.mem("lives") == 2 and gb.mem("game_state") == 2


def test_mug_breaking_and_patron_arriving_on_one_frame_cost_one_life(gb):
    clear_patrons(gb)
    go(gb)
    set_patron(gb, 0, FAR_X - 1, frac=255)
    inject_mug(gb, 1, 17)                # breaks at the left end on the next frame
    gb.run(6)
    assert gb.mem("lives") == 2 and gb.mem("game_state") == 2
    gb.run(30)
    assert gb.mem("lives") == 2


# ---- M8a: half-speed empties, fair empties ---------------------------------------------------------
TAP_X = GAME["TAP_X"]


def test_empties_move_one_px_every_second_frame(gb):
    clear_patrons(gb)
    freeze(gb)
    gb.press("down", 2)                           # the bartender is on bar 1; the empty is on bar 3
    m = inject_mug(gb, 3, 40, EMPTY)
    xs = []
    for _ in range(20):
        gb.run(1)
        xs.append(gb.read("mug_x", MAX_M)[m])
    steps = [b - a for a, b in zip([40] + xs, xs)]
    assert steps == [0, 1] * 10, steps
    full = inject_mug(gb, 3, 100, FULL)
    gb.run(1)
    x0 = gb.read("mug_x", MAX_M)[full]
    gb.run(5)
    assert gb.read("mug_x", MAX_M)[full] == x0 - 10, "full mugs stay at 2 px per frame"


def drinker_with_mug(gb, bar, x, timer):
    p = set_patron(gb, bar, x, state=DRINKING, timer=timer)
    hold_mug(gb, p, bar)
    return p


def catch_frames(gb, frames):
    """Frame numbers on which an empty was caught (the score rises by 100)."""
    out, s = [], score(gb)
    for f in range(frames):
        gb.run(1)
        n = score(gb)
        if n != s:
            assert n - s == 100
            out.append(f)
            s = n
    return out


def test_two_patrons_finishing_at_once_send_empties_that_arrive_empty_gap_apart(gb):
    clear_patrons(gb)
    freeze(gb)                                    # nobody walks; drinking and empties go on
    gap = gb.mem("empty_gap")
    assert gap == 120, "level 1"
    near = drinker_with_mug(gb, 0, 70, 89)        # both finish on the next frame
    far = drinker_with_mug(gb, 0, 20, 89)
    gb.run(2)
    aux = gb.read("patron_aux", MAX_P)
    assert aux[near] == DRINK_WINDUP, "the one nearer the bartender winds up to send his empty at once (M8d)"
    assert aux[far] == DRINK_WAIT, "the other sips on: his empty would arrive too soon after the first"
    t_near = WINDUP + 2 * (TAP_X - (70 + 16))     # M8d: the arrival counts the wind-up
    assert t_near - 2 <= gb.mem16("next_arrival") - gap <= t_near, "next_arrival = his arrival + empty_gap"
    caught = catch_frames(gb, 400)
    assert len(caught) == 2, caught
    assert caught[1] - caught[0] >= gap, caught
    assert caught[1] - caught[0] <= gap + 2, "and no later than needed"


def test_a_patron_waiting_to_send_his_empty_sips_on_and_does_not_walk_on(gb):
    """M8d (was: holds the empty frozen in the last pose): he keeps drinking, the timer looping over the sipping
    poses, stays put, then winds up and sends the empty when its arrival is fair."""
    clear_patrons(gb)
    gb.write("intro_timer", 0)                    # walkers walk now
    gb.write("spawn_timer", 255)
    gb.write("next_arrival", 250)                 # an empty has just been scheduled: nothing may arrive for a while
    gb.write(gb.addr("next_arrival") + 1, 0)
    p = drinker_with_mug(gb, 2, 40, 89)
    m = list(gb.read("patron_mug", MAX_P))[p]
    gb.run(2)                                     # (he finishes on the game's next frame)
    for _ in range(58):
        gb.run(1)
        assert gb.read("patron_state", MAX_P)[p] == DRINKING and gb.read("patron_x", MAX_P)[p] == 40
        assert gb.read("patron_aux", MAX_P)[p] == DRINK_WAIT
        assert GAME["SIP_LOOP_T"] <= gb.read("patron_timer", MAX_P)[p] < GAME["DRINK_FRAMES"], "sipping on"
        assert gb.read("mug_state", MAX_M)[m] == HELD
    t = WINDUP + 2 * (TAP_X - 56)                 # his empty's arrival, wind-up included
    gb.run(250 - 60 - t + 2)
    assert gb.read("patron_aux", MAX_P)[p] == DRINK_WINDUP and gb.read("mug_state", MAX_M)[m] == HELD
    gb.run(WINDUP + 2)
    assert gb.read("patron_state", MAX_P)[p] == WALKING and gb.read("mug_state", MAX_M)[m] == EMPTY


def test_a_lone_patron_is_never_held_back(gb):
    clear_patrons(gb)
    freeze(gb)
    p = drinker_with_mug(gb, 1, 30, 89)
    gb.run(2)
    assert gb.read("patron_aux", MAX_P)[p] == DRINK_WINDUP, "winds up at once (M8d)"
    gb.run(WINDUP)
    assert gb.read("patron_state", MAX_P)[p] == WALKING and [m["state"] for m in mugs(gb)] == [EMPTY]


# ---- quick refill: an empty screen brings the next patron within about half a second (owner 2026-10-13) ------------------
REFILL = GAME["REFILL_FRAMES"]


def due_in(gb, frames):
    gb.write("intro_timer", 0)
    gb.write("quota", 50)
    gb.write("spawn_timer", frames & 255)
    gb.write(gb.addr("spawn_timer") + 1, frames >> 8)


def test_an_empty_screen_refills_within_about_30_frames(gb):
    clear_patrons(gb)
    due_in(gb, 250)                                   # (level 1 waits 300 frames between patrons)
    n0 = gb.mem("spawned")
    gb.run(REFILL + 6)
    assert gb.mem("spawned") == n0 + 1, "the next patron came in about half a second, not 250 frames"


def test_a_screen_with_a_patron_does_not_refill_early(gb):
    clear_patrons(gb)
    set_patron(gb, 1, 60)
    due_in(gb, 250)
    n0 = gb.mem("spawned")
    gb.run(REFILL + 60)
    assert gb.mem("spawned") == n0, "only an empty screen pulls the spawn forward"


def test_a_patron_still_sliding_out_counts_as_on_the_screen(gb):
    clear_patrons(gb)
    freeze(gb)
    p = set_patron(gb, 1, ENTRY_X)
    gb.run(3)
    inject_mug(gb, 1, ENTRY_X + 8)
    gb.run(3)
    assert gb.read("patron_state", MAX_P)[p] == LEAVING
    due_in(gb, 250)
    n0 = gb.mem("spawned")
    gb.run(REFILL - 12)                               # (he needs about 32 frames to be fully off: no spawn before that)
    assert gb.mem("spawned") == n0 and gb.read("patron_state", MAX_P)[p] == LEAVING
    gb.run(80)
    assert gb.mem("spawned") == n0 + 1, "off the screen: the bar is empty, the refill runs"


def test_no_quick_refill_after_a_patterns_breather(gb):
    """A story arrival pattern's breather ('b', wait code 3) is deliberate: an empty screen does not cut it short; a normal
    wait (code 0) does."""
    for code, comes in ((3, False), (0, True)):
        clear_patrons(gb)
        gb.write("pat_len", 2)
        gb.write("pat_pos", 1)
        put(gb, "pat_buf", 0, (code << 4) | 2)           # the entry just played (pat_pos - 1) ...
        put(gb, "pat_buf", 1, 1)
        gb.write("pat_bar", 1)
        due_in(gb, 250)
        n0 = gb.mem("spawned")
        gb.run(REFILL + 20)
        assert (gb.mem("spawned") > n0) == comes, (code, gb.mem("spawned") - n0)
    gb.write("pat_len", 0)
