# Venue twists (docs/story.md "Chapters"). The mosh pit: The Chrome Cow's twist, chapter 7's Happy hour and Last call
# (docs/minigames_bosses.md section 9; src/mosh.c with its ROM0 hooks in src/patrons.c), and the band that plays faster
# in its Last call (src/music.c music_fast). Section 9.6 lists the tests; numbers in the docstrings refer to it.
import pytest
from conftest import GAME, LAYOUT, ROOT, VENUES, bar_counter_row, title_level
from test_flow import LIFE_LOST, PLAYING, most_per_scanline, run_until, state, tilemap_row
from test_patrons import (DRINK_MIN, DRINKING, FULL, LEAVING, MAX_P, PUSHED, WALKING, clear_patrons, inject_mug, put,
                          set_patron)
from test_story import SHIFTS, to_shift

pytestmark = pytest.mark.timeout(240)

BIKER = 6                                  # The Chrome Cow's chapter / venue index (chapter 7)
CONTACT, SHOVE, STAGGER, SPLASH = 12, 16, 30, 30
LIMIT = {1: 88, 2: 72}                     # Happy hour, Last call
ENTRY_X, FAR_X = GAME["ENTRY_X"], GAME["PATRON_FAR_X"]
PUSH = 32                                  # level row 7: push-back 4 columns (the first drink)


def xs(gb):
    return list(gb.read("patron_x", MAX_P))


def sts(gb):
    return list(gb.read("patron_state", MAX_P))


def quiet(gb):
    """No walking (the intro delay), no spawns, no tips: only what the test sets up moves."""
    clear_patrons(gb)
    for i in range(MAX_P):
        for n in ("patron_shove", "patron_stag", "patron_mosh"):
            put(gb, n, i, 0)
    gb.write("intro_timer", 255)
    gb.write("spawn_timer", 255)
    gb.write(gb.addr("spawn_timer") + 1, 255)
    gb.write("tip_chance", 0)
    gb.run(2)


def walk_on(gb):
    """Walkers walk again (a shoved one walks on at his own speed once his stagger is over)."""
    gb.write("intro_timer", 0)


def serve(gb, p, bar):
    """A full glass right at p's left edge + 4: caught on the next frames, a push of PUSH px (his first drink)."""
    inject_mug(gb, bar, xs(gb)[p] + 4, FULL)


def until_pushed(gb, p, limit=10):
    run_until(gb, lambda: sts(gb)[p] == PUSHED, limit)


@pytest.fixture(params=["dmg", "cgb"])
def hh(request):
    """Chapter 7's Happy hour, in play, emptied."""
    with to_shift(request.param, BIKER, 1) as gb:
        quiet(gb)
        yield gb


# ---- the data and the gating (9.6 test 8) --------------------------------------------------------------------------
def test_the_twist_data():
    """Only The Chrome Cow's Happy hour (the mosh pit, limit 88) and Last call (the mosh pit, limit 72, and the band
    plays faster) carry a twist."""
    for c, row in enumerate(SHIFTS):
        for k, sh in enumerate(row):
            want = {(BIKER, 1): (1, 88), (BIKER, 2): (3, 72)}.get((c, k), (0, 0))
            assert (sh["twist"], sh["mosh_limit"]) == want, (c, k)
    assert VENUES["venues"]["biker"]["splash_tile"], "The Chrome Cow's bar set has the splash tile"
    assert all(not v["splash_tile"] for t, v in VENUES["venues"].items() if t != "biker")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("k", [0, 1, 2])
def test_the_mosh_pit_is_on_in_happy_hour_and_last_call_only(model, k):
    with to_shift(model, BIKER, k) as gb:
        on = k > 0
        assert gb.mem("mosh_on") == on and gb.mem("mosh_limit") == (LIMIT[k] if on else 0)
        assert gb.mem("music_fast") == (k == 2), "the band plays faster in the Last call only"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_off_in_arcade_and_in_other_chapters(model):
    from test_scores import booted
    with booted(model) as gb:
        title_level(gb)
        run_until(gb, lambda: state(gb) == PLAYING, 60)
        from test_art import goto_group
        goto_group(gb, BIKER)                    # arcade level 7: The Chrome Cow, plain rules
        assert gb.mem("cur_group") == BIKER and gb.mem("mosh_on") == 0 and gb.mem("music_fast") == 0
    with to_shift(model, BIKER + 1, 1) as gb:    # the teahouse's Happy hour
        assert gb.mem("mosh_on") == 0 and gb.mem("music_fast") == 0


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_off_in_a_boss_fight(model):
    """A boss fight plays by the same rules everywhere: boss_goal's twist is 0 (the saloon's, the one built so far,
    after The Chrome Cow's Last call turned it on)."""
    from test_story import BOSS_STEP, beat_the_boss, to_goal, win
    with to_shift(model, BIKER, 2) as gb:
        assert gb.mem("mosh_on") == 1
    with to_shift(model, 0, 2) as gb:
        win(gb, 0, 2)
        run_until(gb, lambda: gb.mem("story_step") == BOSS_STEP and state(gb) != PLAYING, 400)
        to_goal(gb)
        assert gb.mem("boss_on") == 1 and gb.mem("mosh_on") == 0 and gb.mem("music_fast") == 0


# ---- the rule (9.6 tests 1-5, 7) -------------------------------------------------------------------------------------
def test_bump_shove_stagger_walk_on(hh):
    """Test 1: Q walking at x 40, P at x 60 catches a glass: when P.x - Q.x <= 12, Q goes 16 px in 8 frames, holds
    30 frames, then walks on; P finishes his push and drinks."""
    gb = hh
    q = set_patron(gb, 1, 40)
    p = set_patron(gb, 1, 60)
    serve(gb, p, 1)
    until_pushed(gb, p)
    trace = []
    for _ in range(PUSH + 50):
        gb.run(1)
        trace.append((xs(gb)[p], xs(gb)[q], gb.mem(gb.addr("patron_stag") + q)))
    start = next(i for i, (px, qx, _) in enumerate(trace) if qx != 40)
    assert trace[start - 1][0] - 40 <= CONTACT, "bumped when they touch, not before"
    assert [qx for _, qx, _ in trace[start:start + 8]] == [42, 44, 46, 48, 50, 52, 54, 56], "16 px in 8 frames"
    assert trace[start + 8][1] == 56 and trace[start + 7][2] == STAGGER, "then he staggers"
    assert all(qx == 56 for _, qx, _ in trace[start + 7:start + 7 + STAGGER]), "on the spot for 30 frames"
    assert gb.mem("mosh_count") == 1
    assert sts(gb)[p] == DRINKING and xs(gb)[p] == 60 - PUSH, "P not slowed: his whole push, then he drinks"
    walk_on(gb)
    gb.run(200)
    assert xs(gb)[q] > 56, "walks on at his own speed"


def test_one_shove_per_bump_and_per_push(hh):
    """Tests 2-3: two walkers behind P (x 44 and x 30): only the first he meets is shoved, and only once; P passes
    the second."""
    gb = hh
    a = set_patron(gb, 2, 44)
    b = set_patron(gb, 2, 30)
    p = set_patron(gb, 2, 60)
    serve(gb, p, 2)
    until_pushed(gb, p)
    gb.run(PUSH + 40)
    assert xs(gb)[a] == 44 + SHOVE and xs(gb)[b] == 30, "the first is shoved 16 px in all, the second not at all"
    assert gb.mem("mosh_count") == 1 and gb.mem(gb.addr("patron_mosh") + p) == 1


def test_no_chains(hh):
    """Test 4: Q's shove carries him into a drinker R ahead of him (planted; his first sips let the glass slide on to
    P): R does not move and nobody else is bumped (a shove is not a push)."""
    gb = hh
    q = set_patron(gb, 0, 52)
    r = set_patron(gb, 0, 80, state=DRINKING, timer=10, aux=DRINK_MIN)
    p = set_patron(gb, 0, 76)
    serve(gb, p, 0)
    until_pushed(gb, p)
    gb.run(PUSH + 40)
    assert xs(gb)[q] == 52 + SHOVE and xs(gb)[q] + 16 > xs(gb)[r] == 80, "Q overlaps R, R stays"
    assert gb.mem("mosh_count") == 1 and gb.mem(gb.addr("patron_shove") + r) == 0


@pytest.mark.parametrize("qx, want", [(70, 86), (80, 88), (88, 88), (90, 90)])
def test_the_limit(hh, qx, want):
    """Test 5: a shove never takes Q past x 88 in Happy hour; at or past it he is only jostled (the bump is used)."""
    gb = hh
    q = set_patron(gb, 3, qx)
    p = set_patron(gb, 3, min(qx + 8, 110))
    serve(gb, p, 3)
    until_pushed(gb, p)
    gb.run(PUSH + 50)
    assert xs(gb)[q] == want and gb.mem("mosh_count") == 1 and gb.mem(gb.addr("patron_mosh") + p) == 1


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_last_call_limit_is_72(model):
    with to_shift(model, BIKER, 2) as gb:
        quiet(gb)
        q = set_patron(gb, 1, 64)
        p = set_patron(gb, 1, 72)
        serve(gb, p, 1)
        until_pushed(gb, p)
        gb.run(PUSH + 50)
        assert xs(gb)[q] == 72 and gb.mem("mosh_count") == 1


@pytest.mark.parametrize("who", ["drinking", "pushed", "leaving", "entering", "watching"])
def test_never_bumped(hh, who):
    """Test 7: drinkers, pushed and leaving patrons, one still entering (patron_aux > 0) and one watching the show."""
    gb = hh
    kw = {"drinking": dict(state=DRINKING, timer=5, aux=DRINK_MIN), "pushed": dict(state=PUSHED, aux=4),
          "leaving": dict(state=LEAVING), "entering": dict(aux=8), "watching": dict()}[who]
    q = set_patron(gb, 1, 48, **kw)
    if who == "watching":
        put(gb, "patron_dist", q, 1)
    p = set_patron(gb, 1, 60)
    serve(gb, p, 1)
    until_pushed(gb, p)
    gb.run(16)
    assert gb.mem("mosh_count") == 0 and gb.mem(gb.addr("patron_shove") + q) == 0


# ---- the cue (9.6 test 10) ---------------------------------------------------------------------------------------------
def test_the_counter_splash(hh):
    """Test 10: the counter-row tile under the contact column is the splash for 30 frames, then the bar's own again."""
    gb = hh
    v = VENUES["venues"]["biker"]
    q = set_patron(gb, 2, 40)
    p = set_patron(gb, 2, 60)
    serve(gb, p, 2)
    until_pushed(gb, p)
    row = bar_counter_row(2)
    seen = []
    for _ in range(PUSH + 20):
        gb.run(1)
        seen.append(tilemap_row(gb, row, 0, 17))
    hit = [i for i, r in enumerate(seen) if v["splash_tile"] in r]
    assert hit and len(hit) in (SPLASH - 1, SPLASH, SPLASH + 1), len(hit)
    col = seen[hit[0]].index(v["splash_tile"])
    assert col == 52 >> 3 or col == 53 >> 3, "under the contact (P's left edge)"
    assert seen[-1] == v["bar_map"][40:57], "the counter is back"
    assert gb.mem("sfx_count") is not None


# ---- fairness (9.6 tests 6, 11, 12) ------------------------------------------------------------------------------------
def drop_empties(gb):
    """Empties sliding back are taken off the bar (as if the bartender caught them): only walkers can cost a life."""
    st = gb.read("mug_state", 20)
    for i, m in enumerate(st):
        if m == 2:
            put(gb, "mug_state", i, 0)
            gb.write("mugs_live", max(0, gb.mem("mugs_live") - 1))


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("k", [1, 2])
def test_a_shove_never_costs_a_life(model, k):
    """Test 6 (every 8 px): P at 32..104, Q behind him; P served, then Q served as soon as P drinks: no walker reaches
    the tap in the next 300 frames (no life lost; the empties are taken off) and Q never passes the limit."""
    with to_shift(model, BIKER, k) as gb:
        for px in range(32, 105, 8):
            for qx in range(ENTRY_X, px + 1, 8):
                quiet(gb)
                gb.write("lives", 3)
                gb.write("served", 0)                    # (the shift's goal is never met here)
                q = set_patron(gb, 1, qx)
                p = set_patron(gb, 1, px) if qx != px else None
                if p is None:
                    continue
                walk_on(gb)
                serve(gb, p, 1)
                until_pushed(gb, p)
                run_until(gb, lambda: sts(gb)[p] != PUSHED, PUSH + 10)
                if sts(gb)[q] == WALKING:
                    serve(gb, q, 1)
                for _ in range(300):
                    gb.run(1)
                    drop_empties(gb)
                    assert state(gb) != LIFE_LOST, (px, qx)
                    if sts(gb)[q] == WALKING and gb.mem(gb.addr("patron_shove") + q):
                        assert xs(gb)[q] <= LIMIT[k], (px, qx)
                assert gb.mem("lives") == 3, (px, qx)


def scene(gb, mosh):
    """The same scripted scene with the mosh pit on or off: P served with Q behind him (shoved when it is on), P drinks
    and sends his empty; returns what the rules count (the fair-empties schedule, served, score) and the bumps."""
    quiet(gb)
    gb.write("level", 1)                         # (no early drinkers: the random draw would differ with the pit on and off)
    gb.write("mosh_on", mosh)
    gb.write("mosh_count", 0)
    gb.write("next_arrival", 0)
    gb.write(gb.addr("next_arrival") + 1, 0)
    set_patron(gb, 0, 40)
    p = set_patron(gb, 0, 60)
    walk_on(gb)
    serve(gb, p, 0)
    until_pushed(gb, p)
    out = []
    for i in range(300):
        gb.run(1)
        drop_empties(gb)
        out.append(gb.mem16("next_arrival"))
    return out, gb.mem("served"), int.from_bytes(gb.read("score", 4), "little"), gb.mem("mosh_count")


def schedule(na):
    """The fair-empties schedule from a trace of next_arrival (one sample a frame): each time it is pushed up, the frame
    it then points at (the sample's index + its value)."""
    return [i + v for i, (u, v) in enumerate(zip([0] + na, na)) if v > u]


def same_schedule(a, b):
    """Equal, but for the sampling: a game frame that ends late shows a count one frame later (PyBoy samples after the
    video frame), which moves a point by at most one."""
    return len(a) == len(b) and all(abs(x - y) <= 1 for x, y in zip(a, b))


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_fair_empties_score_and_served_do_not_change(model):
    """Tests 11-12: next_arrival (the fair-empties schedule), served and the score are the same with and without the
    shove in the same scripted scene (a shove moves a walker, never a drinker)."""
    with to_shift(model, BIKER, 1) as gb:
        gb.write("served", 0)
        s0 = int.from_bytes(gb.read("score", 4), "little")
        on = scene(gb, 1)
        assert on[3] == 1, "the scene has its shove"
        gb.write("served", 0)
        a = gb.addr("score")
        for i in range(4):
            gb.write(a + i, (s0 >> (8 * i)) & 255)
        off = scene(gb, 0)
        assert off[3] == 0
        assert schedule(on[0]) and same_schedule(schedule(on[0]), schedule(off[0])), "the same empties, due alike"
        assert on[1] == off[1] and on[2] - s0 == off[2] - s0, "served and the score"


# ---- sprites (9.6 test 9) ----------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_mosh_on_all_four_bars_keeps_the_sprite_budgets(model):
    """Test 9: a bump on every bar at once (four shoves through four pushes, more than one bartender can serve): every
    frame <= 10 objects on a line, no shove step puts three patrons on one tile column, the music never skips a tick and
    no VRAM write happens outside VBlank. A stress test like test_perf's piles: some game frames run late (measured:
    DMG 15, CGB 16 of 72, end LY 163-174; the same scene without the mosh pit 2 / 157), a regression guard here."""
    import perf_helpers as ph
    from test_perf import assert_music_every_frame
    with to_shift(model, BIKER, 2) as gb:
        quiet(gb)
        pairs = []
        for b in range(4):
            q = set_patron(gb, b, 36 + 4 * b)
            p = set_patron(gb, b, 56 + 4 * b)
            pairs.append((p, q, b))
        for p, q, b in pairs:
            serve(gb, p, b)
        gb.run(3)
        ph.perf_reset(gb)
        ticks = []
        for _ in range(PUSH + 40):
            gb.run(1)
            ticks.append((gb.mem("frame_counter"), gb.mem16("music_frames")))
            assert most_per_scanline(gb) <= 10
            for b in range(4):
                cols = {}
                for i, (s, x) in enumerate(zip(sts(gb), xs(gb))):
                    if s and gb.read("patron_bar", MAX_P)[i] == b and x >= ENTRY_X:
                        for c in range(x >> 3, (x >> 3) + (2 if x & 7 == 0 else 3)):
                            cols[c] = cols.get(c, 0) + 1
                assert max(cols.values(), default=0) <= 2 + 1, cols
        assert gb.mem("mosh_count") == 4
        r = ph.perf_read(gb)
        print(model, "mosh on four bars", r)
        assert_music_every_frame(ticks)
        assert gb.mem("vq_drain_ly_max") <= gb.mem("vq_latest_ly")
        assert r["missed"] <= 22 and r["end"] <= 190, r


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_mosh_on_two_bars_keeps_the_frame_time(model):
    """What one bartender can make: two pushes into two walkers on two bars at once, with walkers on the other two;
    no game frame runs late (but the first, the test's own set-up frame) and none ends past the target line."""
    import perf_helpers as ph
    with to_shift(model, BIKER, 2) as gb:
        quiet(gb)
        pairs = [(set_patron(gb, b, 56 + 4 * b), set_patron(gb, b, 36 + 4 * b), b) for b in range(4)]
        for p, q, b in pairs[:2]:
            serve(gb, p, b)
        gb.run(3)
        ph.perf_reset(gb)
        gb.run(PUSH + 40)
        r = ph.perf_read(gb)
        assert gb.mem("mosh_count") == 2
        assert r["missed"] <= 2 and r["end"] <= 160, r   # (measured DMG 1 / 136, CGB 2 / 158)


# ---- the band plays faster in the Last call ------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_band_plays_faster_in_the_last_call(model):
    """Drunken Sailor at 9 frames a row (200 bpm); in The Chrome Cow's Last call 8 (225): the driver's tempo and the
    music engine's frames per row."""
    from test_story import to_shift as ts
    with ts(model, BIKER, 1) as gb:
        assert gb.mem("cur_tune") == 5 + BIKER and gb.mem("hUGE_ticks_per_row") == 9
    with ts(model, BIKER, 2) as gb:
        assert gb.mem("cur_tune") == 5 + BIKER and gb.mem("hUGE_ticks_per_row") == 8
