# docs/minigames_bosses.md 4.2: T-SHIRT CANNON (src/ts.c), the stadium's mini-game, on the framework (src/mg.c), as reworked in Batch D (2026-10-15):
# the screen (look A, the night game: every row of the approved art as tools/gen_ts.py laid it out, the meter's bar, the palettes, the DMG
# registers), the golf-style power meter (A starts it, it sweeps 0-63 and back, A locks and fires), the flight against a Python model of the
# integer physics for every power (the landing table of tools/cannon_table.py), the too-short / too-far OOPS, the crowd (random fans raise
# their hands for ~2 s, at most 3, always one), the scoring (PERFECT CATCH 300, the pittance 30, OOPS 0) and its messages, the reload, the 10
# shirts, the 45 s timer, medals and the bots behind their thresholds, the sprites per line, STORY / ARCADE reaching it in chapter 2,
# BONUS > MINI GAMES, what is put back when it is left.
import random

import pytest
from conftest import ROOT, check_golden, hold_stage_anim, logic_paused
from test_flow import GS_GOAL, LEVEL_CLEAR, TITLE, run_until, state, tilemap_row
from test_mg import (BLANK, GS_MGLIST, GS_MINI, MG_COUNT, MG_END, MG_PRACTICE, MG_RESULT, MG_STORY, RESULT_MIN,
                     frames, lines, mg_enter, score, text, to_play, to_result, until)
from test_mg_list import release_built  # noqa: F401  (the fixture: `make release`)
from ts_helpers import (ART, CROWD, FAN_FIRST, FAN_N, LAYOUT, MG_TSHIRT, OVER, PMAX, SHORT, SHOTS, STADIUM, STATE_SIZE, TS_BG, TS_OBJ,
                        fly, glyph, path, perfect_powers, poke, ts, ts_define)

pytestmark = pytest.mark.timeout(900)

MEDAL_NONE, MEDAL_BRONZE, MEDAL_SILVER, MEDAL_GOLD = range(4)
SEED = 0x5A17
OUT = ROOT / "out" / "ts"
S_PALETTE = 0x10
AIM, METER, FLY, RELOAD, SPENT, OUTRO = range(6)
R_NONE, R_SHORT, R_OVER, R_CROWD, R_PERFECT = range(5)
POSE_IDLE, POSE_FIRE, POSE_CHEER, POSE_MISS = range(4)
(RELOAD_LEN, TIME_S, STEP, PTS_PERFECT, PTS_CROWD, MSG_LEN, POSE_LEN, FIRE_POSE, PUFF_LEN, UP_FRAMES, UP_RAND, UP_MAX, HOLD, SPAWN, POP,
 SPENT_LEN) = (ts_define(n) for n in (
    "TS_RELOAD", "TS_TIME_S", "TS_STEP", "TS_PTS_PERFECT", "TS_PTS_CROWD", "TS_MSG_LEN", "TS_POSE_LEN", "TS_FIRE_POSE", "TS_PUFF_LEN",
    "TS_UP_FRAMES", "TS_UP_RAND", "TS_UP_MAX", "TS_HOLD", "TS_SPAWN", "TS_POP", "TS_SPENT_LEN"))
OAM_SPIG, OAM_CANNON, OAM_PUFF, OAM_SHIRT, OAM_MARK = (ts_define(n) for n in ("OAM_SPIG", "OAM_CANNON", "OAM_PUFF", "OAM_SHIRT", "OAM_MARK"))
MEDALS = (1500, 2100, 2700)                      # mg.c medal_at: bronze, silver, gold
SHORT_MAX, OVER_MIN = ART["short_max"], ART["over_min"]
MUZ = ART["muzzle"]


def game(model, mode=MG_PRACTICE, seed=SEED):
    """A booted rom on the title, then T-Shirt Cannon in practice (or `mode`)."""
    from test_scores import booted
    rom = booted(model)
    hold_stage_anim(rom)
    mg_enter(rom, MG_TSHIRT, mode, seed)
    return rom


def shot(gb, name):
    OUT.mkdir(parents=True, exist_ok=True)
    gb.screenshot(OUT / f"{name}.{gb.model_name}.png", 4)


def oam(gb, i):
    a = 0xFE00 + 4 * i
    return dict(y=gb.mem(a), x=gb.mem(a + 1), tile=gb.mem(a + 2), prop=gb.mem(a + 3))


def tap(gb, key, n=1):
    gb.hold(key)
    frames(gb, n)
    gb.release(key)
    frames(gb, 1)


def snap(gb):
    """The state as of a whole update, read in a paused frame (the VBlank copy and the OAM DMA have caught up there too)."""
    with logic_paused(gb):
        return ts(gb)


def to_aim(gb, extra=2):
    to_play(gb)
    frames(gb, extra)


def tile_bytes(gb, t):
    a = 0x9000 + t * 16 if t < 128 else 0x8000 + t * 16
    return list(gb.read(a, 16))


def bank1(gb, col, row):
    gb.pb.memory[0xFF4F] = 1
    try:
        return gb.pb.memory[0x9800 + row * 32 + col]
    finally:
        gb.pb.memory[0xFF4F] = 0


def map_row(gb, row):
    return tilemap_row(gb, row, 0, 20)


def expected_map(s):
    """The 17 map rows (rows 1-17) as the game has them: the generator's map with each fan in the frame it shows."""
    rows = [[TS_BG + t for t in ART["map"][r * 20:(r + 1) * 20]] for r in range(17)]
    for i in range(FAN_N):
        base = 2 * ((3 if i & 1 else 0) + s["fshown"][i])
        rt = 11 - (i >> 1)
        rows[rt - 1][FAN_FIRST + i] = TS_BG + ART["fan"][base]
        rows[rt][FAN_FIRST + i] = TS_BG + ART["fan"][base + 1]
    return rows


def power_for(col, k=0):
    """The k-th meter power whose shot hits the stand column `col`."""
    return [p for p in range(PMAX + 1) if fly(p)[0] == CROWD and fly(p)[1] == col][k]


def hold_fans(gb, up):
    """Between two updates: the fans with raised hands (a list of columns, or {column: frames}); the next fan is far off, nothing else can raise."""
    d = {c: 250 for c in up} if not isinstance(up, dict) else up
    poke(gb, up=[d.get(i, 0) for i in range(FAN_N)], spawn=250)


def to_wait(gb):
    """Run to the state where A starts the meter (AIM)."""
    for _ in range(400):
        if snap(gb)["st"] == AIM:
            return
        frames(gb, 1)
    raise AssertionError("no aim")


def lock(gb, p):
    """The meter at power p, A pressed for one update: the state with the shirt in the air."""
    poke(gb, st=METER, power=p, pdir=1, pt=STEP, spawn=250)
    gb.hold("a")
    frames(gb, 1)
    gb.release("a")
    s = snap(gb)
    assert s["st"] == FLY, s
    return s


def land(gb, limit=200):
    """Frames until the flight is over; returns the state at the landing."""
    for _ in range(limit):
        s = snap(gb)
        if s["st"] != FLY:
            return s
        frames(gb, 1)
    raise AssertionError("no landing")


def shoot(gb, p, up=None):
    """A whole shot at power p (the fans in `up` raised if given): the state at the landing."""
    to_wait(gb)
    if up is not None:
        hold_fans(gb, up)
    lock(gb, p)
    return land(gb)


# ---- the screen ------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_screen_and_its_art(model):
    """The intro: the banner, the HUD (the shirt icon and 10), every row of the approved art as the generator laid it out (the stage, the
    bunting, the meter's bar, the fans), the tiles and palettes, the sprites, the DMG registers."""
    with game(model) as gb:
        assert gb.mem("mg_id") == MG_TSHIRT and gb.mem("mg_mode") == MG_PRACTICE and gb.mem("mg_phase") == 0
        assert gb.mem("venue_id") == STADIUM
        frames(gb, 30)
        assert text(gb, 2) == "SHIRT CANNON" and text(gb, 3) == "A POWER THEN A FIRE"
        hud = ART["hud"]
        assert tilemap_row(gb, 0, 10, 3) == [TS_BG + hud[0], glyph("1"), glyph("0")]
        assert tilemap_row(gb, 0, 13, 3) == [BLANK] * 3, "no wind any more"
        assert hud_timer_ok(gb)
        got = [b for t in range(TS_BG, TS_BG + ART["n_bg"]) for b in tile_bytes(gb, t)]
        assert got == ART["bg"], "BG tiles"
        got = [b for t in range(TS_OBJ, TS_OBJ + ART["obj_tiles"]) for b in gb.read(0x8000 + t * 16, 16)]
        assert got == ART["obj"], "OBJ tiles"
        to_play(gb)
        frames(gb, 3)
        s = snap(gb)
        assert s["st"] == AIM and s["power"] == 0 and s["num"] == 1 and s["shots"] == 0 and s["result"] == R_NONE
        assert sum(1 for u in s["up"] if u) == 2, "two fans have their hands up from the start"
        want = expected_map(s)
        for r in range(17):
            assert map_row(gb, r + 1) == want[r], f"map row {r + 1}"
        assert text(gb, 2) == "" and text(gb, 3) == ""
        if model == "cgb":
            for r in range(17):
                assert [bank1(gb, c, r + 1) for c in range(20)] == ART["attr"][r * 20:(r + 1) * 20], f"attributes of row {r + 1}"
            assert all(bank1(gb, c, 0) == 1 for c in range(20)), "the HUD's palette"
            from test_lift import cgb_obj_palette
            from test_venues import cgb_palette
            for i, p in enumerate((0, 2, 3, 5, 6, 7)):
                assert cgb_palette(gb, p) == ART["pal_bg"][i], f"BG palette {p}"
            for i, p in enumerate((1, 2, 3)):
                assert cgb_palette(gb, p, obj=True) == ART["pal_obj"][i], f"OBJ palette {p}"
        else:
            assert gb.mem(0xFF47) == 0xE4 and gb.mem(0xFF48) == 0xD0 and gb.mem(0xFF49) == 0xE4
        # the sprites: the Spigoteer idle, the barrel, no shirt, no puff
        sp = oam(gb, OAM_SPIG)
        assert (sp["x"], sp["y"], sp["tile"]) == (12 + 8, 96 + 16, 0)
        c0, c1 = oam(gb, OAM_CANNON), oam(gb, OAM_CANNON + 1)
        assert (c0["x"], c0["y"], c0["tile"]) == (32 + 8, 104 + 16, ART["cannon"][0])
        assert (c1["x"], c1["y"], c1["tile"]) == (40 + 8, 104 + 16, ART["cannon"][1])
        assert oam(gb, OAM_SHIRT)["y"] == 0 and oam(gb, OAM_PUFF)["y"] == 0
        if model == "cgb":
            assert c0["prop"] & 7 == 3
        else:
            assert c0["prop"] & S_PALETTE


def hud_timer_ok(gb):
    from test_mg import hud_timer
    return hud_timer(gb) == "45"


def test_the_meter_bar_shows_the_red_zones_of_the_table():
    """The bar's art: 8 tiles, 64 pixel rows (a row a power step); solid red-index pixels exactly where the shot is short (0-11) or over (50-63)."""
    assert (SHORT_MAX, OVER_MIN) == (11, 50)
    assert all(fly(p)[0] == SHORT for p in range(SHORT_MAX + 1)) and all(fly(p)[0] == OVER for p in range(OVER_MIN, PMAX + 1))
    assert all(fly(p)[0] == CROWD for p in range(SHORT_MAX + 1, OVER_MIN)), "every power between hits the stand"
    cols = [c for p in range(SHORT_MAX + 1, OVER_MIN) for k, c, _ in [fly(p)]]
    assert cols == sorted(cols) and set(cols) == set(range(FAN_N)), "the power walks the landing along the stand"
    for r in range(8):                                 # the map: the bar at column 1, rows 3-10
        assert ART["map"][(2 + r) * 20 + 1] == ART["meter"][r]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_marker_blinks_at_the_bottom_until_a_starts_the_meter(model):
    with game(model) as gb:
        to_aim(gb)
        seen = set()
        for _ in range(40):
            frames(gb, 1)
            m = oam(gb, OAM_MARK)
            seen.add(m["y"] != 0)
            if m["y"]:
                assert (m["x"], m["y"], m["tile"]) == (0 + 8, 16 + (24 + PMAX - 0 - 3), ART["marker"])
        assert seen == {True, False}, "it blinks"
        assert snap(gb)["st"] == AIM and snap(gb)["shots"] == 0


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_starts_the_meter_it_sweeps_a_step_every_2_frames_and_bounces(model):
    with game(model) as gb:
        to_aim(gb)
        to_wait(gb)
        tap(gb, "a")
        s = snap(gb)
        assert s["st"] == METER and STEP == 2
        trace = []
        for _ in range(2 * 2 * (PMAX + 2) + 40):
            frames(gb, 1)
            s = snap(gb)
            assert s["st"] == METER
            trace.append(s["power"])
            m = oam(gb, OAM_MARK)
            assert (m["x"], m["y"], m["tile"]) == (8, 16 + 24 + PMAX - s["power"] - 3, ART["marker"]), s["power"]
        assert max(trace) == PMAX and min(trace[trace.index(PMAX):]) == 0, "up to the top and back down to the bottom"
        steps = [b - a for a, b in zip(trace, trace[1:]) if b != a]
        assert set(steps) == {1, -1}
        # one step per STEP frames: runs of equal values are STEP long
        runs, n = [], 1
        for a, b in zip(trace, trace[1:]):
            if a == b:
                n += 1
            else:
                runs.append(n)
                n = 1
        assert set(runs[1:]) <= {STEP, STEP + 1}, set(runs)
        up = trace.index(PMAX)
        assert all(b >= a for a, b in zip(trace[:up], trace[1:up + 1])), "monotonic up"
        assert snap(gb)["shots"] == 0, "it never fires by itself"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_locks_the_power_and_fires_puffs_poses_and_counts_the_shirt(model):
    with game(model) as gb:
        to_aim(gb)
        to_wait(gb)
        s = lock(gb, 30)
        assert (s["lastpow"], s["shots"], s["num"], s["puff"] > 0, s["pose"]) == (30, 1, 1, True, POSE_FIRE)
        assert oam(gb, OAM_PUFF)["y"] != 0 and oam(gb, OAM_SHIRT)["y"] != 0
        frames(gb, 1)
        assert tilemap_row(gb, 0, 10, 3) == [TS_BG + ART["hud"][0], glyph("0"), glyph("9")]
        sp = [oam(gb, OAM_SPIG + k) for k in range(4)]
        assert sp[0]["tile"] != 0, "the fire pose"
        frames(gb, PUFF_LEN)
        assert oam(gb, OAM_PUFF)["y"] == 0
        # A during the flight does nothing
        tap(gb, "a")
        assert snap(gb)["shots"] == 1


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_every_power_flies_as_the_model_says(model):
    """All 64 powers: the shirt is where the model puts it, lands (or is lost) on the model's frame with the model's result."""
    with game(model) as gb:
        to_aim(gb)
        for p in range(PMAX + 1):
            gb.write("mg_timer", 2000 & 0xFF)
            gb.write(gb.addr("mg_timer") + 1, 2000 >> 8)
            poke(gb, shots=0, num=1)
            to_wait(gb)
            hold_fans(gb, [])
            poke(gb, up=[0] * 10 + [250])
            kind, col, n = fly(p)
            s = lock(gb, p)
            pts = path(p)
            mid = n // 2
            frames(gb, mid - 1)
            s = snap(gb)
            assert s["st"] == FLY and abs(s["t"] - mid) <= 1 and (s["x"] >> 8, s["y"] >> 8) == pts[s["t"] - 1], (p, mid, s["t"])
            s = land(gb)
            assert s["t"] == n, (p, s["t"], n)
            want = {SHORT: R_SHORT, OVER: R_OVER}.get(kind)
            if kind == CROWD:
                assert s["st"] in (RELOAD, SPENT) and s["result"] in (R_CROWD, R_PERFECT) and s["last"] == col, (p, s)
            else:
                assert s["st"] in (RELOAD, SPENT) and s["result"] == want and s["last"] == 255, (p, s)
        assert max(lines(gb)) <= 10


# ---- scoring and messages --------------------------------------------------------------------------------------------------
def msg_row(gb):
    """Row 2 as text; the game's own '!' tile (say_bang) reads as '!'."""
    from test_mg import GLYPH_CH
    bang = TS_BG + ART["hud"][1]
    return "".join("!" if t == bang else GLYPH_CH.get(t, " ") if t != BLANK else " " for t in tilemap_row(gb, 2, 0, 20)).strip()


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_hit_on_raised_hands_is_a_perfect_catch_for_300(model):
    """The fan hit, or the one each side (a raised pair of hands reaches a column): PERFECT CATCH!, 300 points, the fan holds its hands up."""
    with game(model) as gb:
        to_aim(gb)
        total = 0
        for col, fan in ((4, 4), (4, 3), (4, 5), (0, 0), (0, 1), (10, 10), (10, 9)):
            p = power_for(col)
            before = gb.mem16("mg_score")
            s = shoot(gb, p, up={fan: 250})
            total += PTS_PERFECT
            assert (s["result"], s["last"]) == (R_PERFECT, col), (col, fan)
            assert gb.mem16("mg_score") == before + PTS_PERFECT
            frames(gb, 3)
            assert msg_row(gb) == "PERFECT CATCH!", msg_row(gb)
            assert snap(gb)["pose"] == POSE_CHEER
            poke(gb, st=AIM, spawn=250)
            frames(gb, MSG_LEN)
            assert msg_row(gb) == ""
        assert gb.mem16("mg_score") == total and snap(gb)["shots"] == 7


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_fan_that_catches_keeps_its_hands_up(model):
    with game(model) as gb:
        to_aim(gb)
        to_wait(gb)
        p = power_for(6)
        hold_fans(gb, {6: 60})
        lock(gb, p)
        n = fly(p)[2]
        frames(gb, n + 1)
        s = snap(gb)
        assert s["result"] == R_PERFECT and s["up"][6] >= HOLD - 3, s["up"]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_hit_elsewhere_in_the_crowd_is_the_pittance(model):
    """Two or more columns from every raised fan, or the hands already down: CROWD 30, 10 percent of a catch."""
    assert PTS_CROWD * 10 == PTS_PERFECT
    with game(model) as gb:
        to_aim(gb)
        total = 0
        for col, ups in ((4, {10: 250}), (4, {1: 250}), (4, {6: 250}), (8, {5: 250, 10: 250}), (0, {2: 250})):
            p = power_for(col)
            s = shoot(gb, p, up=ups)
            total += PTS_CROWD
            assert (s["result"], s["last"]) == (R_CROWD, col), (col, ups)
            assert gb.mem16("mg_score") == total
            frames(gb, 3)
            assert msg_row(gb) == "CROWD 30"
            poke(gb, st=AIM)
            frames(gb, MSG_LEN)
        # the hands come down before the shirt arrives: no catch
        p = power_for(5)
        n = fly(p)[2]
        s = shoot(gb, p, up={5: n // 2, 10: 250})
        assert s["result"] == R_CROWD and gb.mem16("mg_score") == total + PTS_CROWD


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_too_short_and_too_far_are_oops_and_score_nothing(model):
    with game(model) as gb:
        to_aim(gb)
        for p, res, word in ((0, R_SHORT, "OOPS! TOO SHORT"), (SHORT_MAX, R_SHORT, "OOPS! TOO SHORT"), (OVER_MIN, R_OVER, "OOPS! TOO FAR"),
                             (PMAX, R_OVER, "OOPS! TOO FAR")):
            s = shoot(gb, p, up=list(range(FAN_N))[:3])
            assert (s["result"], s["last"]) == (res, 255), p
            assert gb.mem16("mg_score") == 0 and score(gb) == 0, "no points"
            frames(gb, 3)
            assert msg_row(gb) == word
            assert snap(gb)["pose"] == POSE_MISS
            poke(gb, st=AIM, spawn=250)
            frames(gb, MSG_LEN)
        assert SHORT_MAX + 1 == 12 and OVER_MIN == 50


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_message_takes_row_2_in_the_hud_colours_for_70_frames_then_the_stage_is_back(model):
    with game(model) as gb:
        to_aim(gb)
        stage = [TS_BG + t for t in ART["map"][1 * 20:2 * 20]]       # map row 2
        stage_attr = ART["attr"][1 * 20:2 * 20]
        s = shoot(gb, 0)
        frames(gb, 2)
        assert msg_row(gb) == "OOPS! TOO SHORT"
        if model == "cgb":
            assert all(bank1(gb, c, 2) == 1 for c in range(20)), "the HUD colours"
        assert MSG_LEN == 70
        poke(gb, st=AIM, spawn=250)
        frames(gb, MSG_LEN - 6)
        assert msg_row(gb) == "OOPS! TOO SHORT"
        frames(gb, 10)
        assert map_row(gb, 2) == stage
        if model == "cgb":
            assert [bank1(gb, c, 2) for c in range(20)] == stage_attr


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_reload_is_40_frames(model):
    with game(model) as gb:
        to_aim(gb)
        s = shoot(gb, power_for(3))
        assert s["st"] == RELOAD and s["reload"] in (RELOAD_LEN, RELOAD_LEN - 1)
        tap(gb, "a")
        assert snap(gb)["st"] == RELOAD, "A is ignored while reloading"
        until(gb, lambda: snap(gb)["st"] == AIM, RELOAD_LEN + 2)
        s = snap(gb)
        assert s["num"] == 2 and s["power"] == 0 and RELOAD_LEN == 40


# ---- the crowd -------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_random_fans_raise_their_hands_for_about_two_seconds_at_most_three_at_once_and_always_one(model):
    with game(model) as gb:
        to_aim(gb)
        poke(gb, st=AIM)
        gb.write("mg_timer", 0xFF)
        gb.write(gb.addr("mg_timer") + 1, 0xFF)
        T = 3000
        started, lens, counts, gaps, last_start = {}, [], [], [], None
        prev = [0] * FAN_N
        cols = set()
        for f in range(T):
            frames(gb, 1)
            s = snap(gb)
            up = s["up"]
            counts.append(sum(1 for u in up if u))
            for i in range(FAN_N):
                if up[i] and not prev[i]:
                    started[i] = f
                    cols.add(i)
                    if last_start is not None:
                        gaps.append(f - last_start)
                    last_start = f
                elif not up[i] and prev[i]:
                    lens.append(f - started[i])
            prev = up
        assert max(counts) <= UP_MAX == 3 and min(counts) >= 1, (max(counts), min(counts))
        assert max(counts) == 3, "it does get busy"
        assert lens and min(lens) >= UP_FRAMES - 2 and max(lens) <= UP_FRAMES + UP_RAND + 2, (min(lens), max(lens))
        assert 100 <= UP_FRAMES and UP_FRAMES + UP_RAND <= 160, "about two seconds"
        assert len(cols) >= 9, f"random fans: {sorted(cols)}"
        assert sum(gaps) / len(gaps) < 80


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_raised_fans_show_the_hands_up_frames_that_pop_every_8_frames(model):
    with game(model) as gb:
        to_aim(gb)
        hold_fans(gb, [2, 7])
        poke(gb, up=[0, 0, 250, 0, 0, 0, 0, 250, 0, 0, 0], spawn=250)
        seq = []
        for _ in range(60):
            frames(gb, 1)
            s = snap(gb)
            seq.append((s["fshown"][2], s["fshown"][7]))
            want = expected_map(s)
            for r in range(17):
                assert map_row(gb, r + 1) == want[r], f"row {r + 1} frame {len(seq)}"
        a = [x[0] for x in seq[4:]]
        assert set(a) == {1, 2} and POP == 8
        flips = [i for i in range(1, len(a)) if a[i] != a[i - 1]]
        assert all(b - a_ == POP for a_, b in zip(flips, flips[1:])), flips
        assert [x[1] for x in seq[4:]] != a, "the fans are not in step"
        assert all(s_ == 0 for s_ in snap(gb)["fshown"][:2]), "the others sit"


# ---- the round -----------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_tenth_shirt_ends_the_round(model):
    assert SHOTS == 10
    with game(model) as gb:
        to_aim(gb)
        for n in range(SHOTS):
            to_wait(gb)
            assert tilemap_row(gb, 0, 11, 2) == [glyph(str((SHOTS - n) // 10)), glyph(str((SHOTS - n) % 10))], n
            hold_fans(gb, [])
            poke(gb, up=[250] + [0] * 10)
            lock(gb, 0)
            land(gb)
        s = snap(gb)
        assert s["st"] == SPENT and s["shots"] == SHOTS and gb.mem("mg_phase") == 2
        frames(gb, 3)
        assert tilemap_row(gb, 0, 11, 2) == [glyph("0"), glyph("0")]
        tap(gb, "a")
        assert snap(gb)["shots"] == SHOTS
        until(gb, lambda: gb.mem("mg_phase") == MG_END, SPENT_LEN + 5)
        frames(gb, 2)
        assert snap(gb)["st"] == OUTRO and oam(gb, OAM_SHIRT)["y"] == 0 and oam(gb, OAM_MARK)["y"] == 0
        until(gb, lambda: gb.mem("mg_phase") == MG_RESULT, 80)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_45_second_timer_ends_a_stalling_round(model):
    with game(model) as gb:
        to_play(gb)
        frames(gb, 2)
        assert gb.mem16("mg_timer") >= TIME_S * 60 - 4 and TIME_S == 45
        gb.write("mg_timer", 3)
        gb.write(gb.addr("mg_timer") + 1, 0)
        until(gb, lambda: gb.mem("mg_phase") == MG_END, 10)
        assert text(gb, 2) == "TIME UP"
        frames(gb, 2)
        s = snap(gb)
        assert s["st"] == OUTRO and s["shots"] == 0 and gb.mem16("mg_score") == 0
        until(gb, lambda: gb.mem("mg_phase") == MG_RESULT, 80)
        assert gb.mem("mg_medal") == MEDAL_NONE


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_time_up_with_a_shirt_in_the_air_scores_nothing_for_it(model):
    with game(model) as gb:
        to_aim(gb)
        to_wait(gb)
        hold_fans(gb, [3, 4, 5])
        lock(gb, power_for(4))
        frames(gb, 3)
        gb.write("mg_timer", 1)
        gb.write(gb.addr("mg_timer") + 1, 0)
        until(gb, lambda: gb.mem("mg_phase") == MG_END, 10)
        frames(gb, 30)
        assert gb.mem16("mg_score") == 0 and oam(gb, OAM_SHIRT)["y"] == 0


@pytest.mark.parametrize("points", [0, 299, 1499, 1500, 2099, 2100, 2699, 2700, 3000])
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_medals_by_score(model, points):
    with game(model) as gb:
        to_play(gb)
        to_result(gb, points)
        want = sum(points >= t for t in MEDALS)
        assert gb.mem("mg_medal") == want, (points, want)


def test_the_medal_thresholds_are_5_7_and_9_perfect_catches():
    assert MEDALS == (5 * PTS_PERFECT, 7 * PTS_PERFECT, 9 * PTS_PERFECT) and SHOTS * PTS_PERFECT == 3000
    mg_c = (ROOT / "src" / "mg.c").read_text()
    assert "{ 1500, 2100, 2700 },   // T-Shirt Cannon" in mg_c


# ---- the bots behind the thresholds ----------------------------------------------------------------------------------------------------
def play_bot(gb, rng=None, jitter=0, blind=False, limit=3300):
    """A player: A starts the meter; with its eyes on the fans (not `blind`) it locks the power in the middle of the nearest power window that
    catches a fan who will still have his hands up when the shirt lands, off by up to +-jitter steps (its timing error). `blind` locks at a random
    power. Returns the score at the end of the round."""
    rng = rng or random.Random(1)
    offset, blind_at = None, None
    for _ in range(limit):
        if gb.mem("mg_phase") != 2:
            break
        s = snap(gb)
        if s["st"] == AIM:
            tap(gb, "a")
            offset, blind_at = None, rng.randint(0, PMAX)
            continue
        if s["st"] == METER:
            press = False
            if blind:
                press = s["power"] == blind_at
            else:
                good = perfect_powers([u - 4 for u in s["up"]])
                if good:
                    if offset is None:
                        offset = rng.randint(-jitter, jitter) if jitter else 0
                    # the middle of the block of good powers nearest ahead of the marker
                    blocks, cur = [], [good[0]]
                    for p in good[1:]:
                        if p == cur[-1] + 1:
                            cur.append(p)
                        else:
                            blocks.append(cur)
                            cur = [p]
                    blocks.append(cur)
                    tgt = [b[len(b) // 2] for b in blocks]
                    ahead = [t for t in tgt if (t - s["power"]) * s["pdir"] >= 0]
                    t = min(ahead, key=lambda t: abs(t - s["power"])) if ahead else min(tgt, key=lambda t: abs(t - s["power"]))
                    press = s["power"] == max(0, min(PMAX, t + offset))
                else:
                    offset = None
            if press:
                gb.hold("a")
                frames(gb, 1)
                gb.release("a")
            else:
                frames(gb, 1)
            continue
        frames(gb, 1)
    return gb.mem16("mg_score")


@pytest.mark.parametrize("seed", [SEED, 0x1234])
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_player_who_watches_the_fans_wins_gold(model, seed):
    with game(model, seed=seed) as gb:
        to_play(gb)
        pts = play_bot(gb)
        assert pts >= MEDALS[2], pts


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_locking_at_random_is_not_a_medal(model):
    with game(model) as gb:
        to_play(gb)
        pts = play_bot(gb, blind=True)
        assert pts < MEDALS[0], pts


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_at_most_10_sprites_a_line_in_the_worst_frames(model):
    """The aim shows the Spigoteer 2 + cannon 2 + the marker (+ the puff); a flight the Spigoteer, the cannon, the puff, the shirt and the marker:
    forced worst frames (every state's sprites on the cannon's lines, the marker everywhere on its bar) never pass 9."""
    with game(model) as gb:
        to_aim(gb)
        worst = [0]
        for st in (AIM, METER, FLY):
            for p in range(0, PMAX + 1, 3):
                poke(gb, st=st, power=p, pdir=1, pt=5, puff=PUFF_LEN, x=(46 << 8), y=(110 << 8), vx=0, vy=0, t=3, spawn=250, pose=POSE_FIRE, pose_t=9)
                frames(gb, 2, worst)
        assert worst[0] <= 9, worst


def test_no_football_remnants_the_field_is_baseball():
    """The owner: the stadium is a baseball field; the chalk line on the grass is the foul line."""
    import re
    for f in ("src/ts.c", "tools/gen_ts.py", "tools/cannon_table.py", "assets/art/tshirt/stands.txt", "src/mg_card.c"):
        t = (ROOT / f).read_text().lower()
        assert not re.search(r"football|touchdown|yard|goal ?post|end zone|gridiron", t), f
    assert "foul line" in (ROOT / "assets/art/tshirt/stands.txt").read_text()


# ---- flow: practice, story, arcade, the list, what is put back ---------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_practice_retry_and_menu(model):
    """Practice: A on the result retries (the score from 0, the state fresh), B comes back to the list."""
    with game(model) as gb:
        to_aim(gb)
        shoot(gb, power_for(0), up=[0])
        assert gb.mem16("mg_score") == PTS_PERFECT
        to_result(gb)
        assert text(gb, 4, True, x0=4) == "A RETRY B MENU"
        gb.press("a", 2)
        run_until(gb, lambda: gb.mem("mg_phase") == 0 and gb.pb.memory[0xFF40] & 0x80, 30)
        s = ts(gb)
        assert state(gb) == GS_MINI and score(gb) == 0 and (s["shots"], s["num"], s["power"]) == (0, 1, 0)
        assert text(gb, 2) == "SHIRT CANNON"
        to_play(gb)
        to_result(gb)
        gb.press("b", 2)
        run_until(gb, lambda: state(gb) == GS_MGLIST and gb.pb.memory[0xFF40] & 0x80, 30)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_story_plays_it_in_chapter_2_and_the_last_call_has_everything_back(model):
    """Chapter 2 (the stadium): after the Happy hour, T-Shirt Cannon in MG_STORY (the score carried, the count not skippable, unlocked for
    Practice at once); the result's A CONTINUE leads to the Last call, whose VRAM and palettes are those of the Last call reached without it."""
    from test_bs import level_vram, palettes
    from test_story import to_goal, to_shift, win
    with to_shift(model, STADIUM, 2) as gb:
        gb.run(2)
        fresh, pals = level_vram(gb), palettes(gb)
    with to_shift(model, STADIUM, 1) as gb:
        assert gb.mem16("mg_unlocked") == 0
        win(gb, STADIUM, 1)
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 20)
        run_until(gb, lambda: state(gb) == GS_MINI, 300)
        run_until(gb, lambda: gb.pb.memory[0xFF40] & 0x80, 10)
        assert gb.mem("mg_id") == MG_TSHIRT and gb.mem("mg_mode") == MG_STORY and gb.mem("venue_id") == STADIUM
        assert text(gb, 2) == "SHIRT CANNON" and score(gb) > 0
        assert gb.mem16("mg_unlocked") == 1 << MG_TSHIRT
        until(gb, lambda: gb.mem("mg_phase") == MG_COUNT, 100)
        frames(gb, 3)
        gb.press("a", 1)
        assert gb.mem("mg_phase") == MG_COUNT, "no skipping in the story"
        to_play(gb)
        frames(gb, 30)
        to_result(gb)
        assert text(gb, 4, True, x0=4) == "A CONTINUE"
        until(gb, lambda: gb.mem("mg_t") >= RESULT_MIN, RESULT_MIN)
        gb.press("a", 2)
        run_until(gb, lambda: state(gb) == GS_GOAL, 60)
        gb.run(3)
        assert gb.mem("story_chapter") == STADIUM and gb.mem("story_shift") == 2 and gb.mem("story_step") == 3
        to_goal(gb)
        gb.run(2)
        assert level_vram(gb) == fresh
        assert palettes(gb) == pals


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_level_after_t_shirt_cannon_has_everything_back(model):
    """A game (a catch, a miss) -> B to the list -> the title -> a level: the level's OBJ tiles, BG 77-255, OBP0 / OBP1 and every palette
    are byte for byte those of a level started from a fresh boot."""
    from conftest import title_level
    from test_bs import level_vram, palettes
    from test_flow import PLAYING
    from test_scores import booted
    with booted(model) as gb:
        hold_stage_anim(gb)
        title_level(gb)
        run_until(gb, lambda: state(gb) == PLAYING, 60)
        gb.run(2)
        fresh, pals = level_vram(gb), palettes(gb)
    with game(model) as gb:
        to_aim(gb)
        shoot(gb, power_for(0), up=[0])
        shoot(gb, 0)
        to_result(gb)
        gb.press("b", 2)
        run_until(gb, lambda: state(gb) == GS_MGLIST and gb.pb.memory[0xFF40] & 0x80, 30)
        gb.run(3)
        gb.press("b", 2)
        run_until(gb, lambda: state(gb) == TITLE and gb.pb.memory[0xFF40] & 0x80, 30)
        gb.run(10)
        gb.press("b", 2)
        gb.run(10)
        title_level(gb)
        run_until(gb, lambda: state(gb) == PLAYING, 60)
        gb.run(62)
        assert level_vram(gb) == fresh
        assert palettes(gb) == pals


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_arcade_plays_it_in_chapter_2(model):
    """ARCADE plays the story's steps: the stadium's mini slot is T-Shirt Cannon, in MG_STORY; reaching it unlocks it."""
    from test_arcade import start_arcade
    from test_story import to_goal, win
    with start_arcade(model) as gb:
        to_goal(gb)
        gb.write("story_chapter", STADIUM)
        gb.write("story_step", 1)
        win(gb, 0, 0)
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 20)
        run_until(gb, lambda: state(gb) == GS_MINI, 400)
        run_until(gb, lambda: gb.pb.memory[0xFF40] & 0x80, 10)
        assert gb.mem("mg_id") == MG_TSHIRT and gb.mem("mg_mode") == MG_STORY and gb.mem("venue_id") == STADIUM
        assert gb.mem("save_lock") == 1 and gb.mem16("mg_unlocked") == 1 << MG_TSHIRT
        assert text(gb, 2) == "SHIRT CANNON"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_bonus_mini_games_lists_and_plays_it(model):
    """BONUS > MINI GAMES (the debug build: all unlocked): SHIRT CANNON on the second line (chapter order), its details THE STADIUM; A plays it in
    practice (score from 0); its result's B comes back to the list on it."""
    from test_mg_list import line, tap as list_tap, to_list
    from test_scores import booted
    with to_list(booted(model)) as gb:
        assert line(gb, 3).strip() == "SHIRT CANNON"
        for _ in range(1):
            list_tap(gb, "down")
        assert gb.mem("ml_sel") == 1
        assert [line(gb, r).strip() for r in range(14, 16)] == ["THE STADIUM", "NORMAL NO MEDAL YET"]
        list_tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_MINI and gb.pb.memory[0xFF40] & 0x80, 30)
        assert gb.mem("mg_id") == MG_TSHIRT and gb.mem("mg_mode") == MG_PRACTICE and score(gb) == 0
        assert text(gb, 2) == "SHIRT CANNON"
        gb.write("mg_phase", MG_RESULT)
        run_until(gb, lambda: gb.mem("overlay_on") == 1, 10)
        frames(gb, 3)
        gb.press("b", 2)
        run_until(gb, lambda: state(gb) == GS_MGLIST and gb.pb.memory[0xFF40] & 0x80, 30)
        gb.run(3)
        assert gb.mem("ml_sel") == 1 and line(gb, 3).strip() == "SHIRT CANNON"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_release_list_unlocks_it_when_reached(model, release_built):
    from test_mg_list import MG_PLANNED, line, pr_block, release_rom, tap as list_tap, to_list, with_block
    from test_scores import v7_image
    best = [0] * MG_PLANNED
    best[MG_TSHIRT] = MEDAL_SILVER
    ram = with_block(v7_image(), pr_block(1 << MG_TSHIRT, best))
    with release_rom(model, ram) as gb:
        to_list(gb)
        assert line(gb, 3) == " SHIRT CANNON SILVER" or line(gb, 3).startswith(" SHIRT CANNON")
        assert [line(gb, r).strip() for r in range(2, 3)] == ["? ? ?"] * 1
        for _ in range(1):
            list_tap(gb, "down")
        assert [line(gb, r).strip() for r in range(14, 16)] == ["THE STADIUM", "NORMAL BEST SILVER"]
        list_tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_MINI, 30)
        assert gb.mem("mg_id") == MG_TSHIRT and gb.mem("mg_mode") == MG_PRACTICE




def test_the_state_fits_the_union_and_the_tile_budget():
    assert STATE_SIZE <= 520 and LAYOUT["up"][1] == FAN_N and LAYOUT["fshown"][1] == FAN_N
    free = 256 - TS_BG                                # the framework's free BG ids: MG_GAME_BG..255
    assert ART["n_bg"] <= free - 16, (ART["n_bg"], free)   # (240-255 stay clear, as the other games)
    assert TS_OBJ + ART["obj_tiles"] <= 92, "the coin sits at OBJ 92-95"
    mx, my = ART["muzzle"]                            # the muzzle is the barrel tip of the art: inside the cannon's 16x16 box
    assert 32 <= mx < 48 and 104 <= my < 120


# ---- goldens ---------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_goldens(model):
    """The intro banner, the aim (the marker blinking), the meter sweeping, a shirt in the air, a perfect catch (PERFECT CATCH!), an OOPS, the
    result: from a seeded game, each shot taken a fixed number of frames after a press."""
    with game(model) as gb:
        frames(gb, 40)
        shot(gb, "intro")
        check_golden(gb, "ts_intro")
        to_play(gb)
        frames(gb, 4)
        hold_fans(gb, [4, 8])
        poke(gb, anim=0)
        frames(gb, 18)
        shot(gb, "aim")
        check_golden(gb, "ts_aim")
        to_wait(gb)
        tap(gb, "a")
        poke(gb, power=38, pt=2)
        frames(gb, 2)
        shot(gb, "meter")
        check_golden(gb, "ts_meter")
        lock(gb, power_for(4))
        frames(gb, 22)
        assert snap(gb)["st"] == FLY
        shot(gb, "flight")
        check_golden(gb, "ts_flight")
        s = land(gb)
        assert s["result"] == R_PERFECT
        frames(gb, 6)
        shot(gb, "cheer")
        check_golden(gb, "ts_cheer")
        poke(gb, st=AIM, spawn=250)
        shoot(gb, 0)
        frames(gb, 6)
        shot(gb, "oops")
        check_golden(gb, "ts_oops")
        to_result(gb, 2300)
        shot(gb, "result")
        check_golden(gb, "ts_result")


@pytest.mark.parametrize("seed", [SEED, 0x1234])
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_player_with_a_sloppy_thumb_still_earns_a_medal(model, seed):
    """Timing off by up to 6 meter steps (about 0.2 s): a medal, not necessarily gold."""
    with game(model, seed=seed) as gb:
        to_play(gb)
        pts = play_bot(gb, jitter=6, rng=random.Random(seed))
        assert MEDALS[0] <= pts, pts
