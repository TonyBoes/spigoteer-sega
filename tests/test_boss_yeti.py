# docs/minigames_bosses.md 3.7: the Yeti, the igloo's boss (src/boss_yeti.c; art approved 2026-10-11, look 1 round 2).
# The fight follows the igloo's Last call: his row (32 px, step 100, push 8, gulp 30, hands 2, sip 60, meter 12) and
# his icy breath every 360 frames of walking: the tell (50 frames: the INHALE pose, the frost creeping along his
# bar's counter 4 columns every 12 frames), the ice (180 frames: the BLOW pose for 30, full mugs 3 px a frame and
# empties 1 px a frame on his bar only, he stands), the thaw (the counter back in 2 frames); the fair schedule across
# the speed change; a life lost on the ice; the win. Every frame here is checked at <= 10 sprites a line.
# E4 (owner 2026-10-15): the ice's trade-off, the FROZEN TAP (nothing can be poured at him on his icy bar; the banner
# TAP FROZEN, a thud on a blocked press; the other bars and the tell pour as ever), and the entrance, the FROST FRONT
# (the wall bare, the counter frosts over, he steps out of the frost in the BLOW pose, it thaws, he walks).
import re

import pytest
from boss_common import (BP_HAPPY, BP_WALK, BS_GULP, BS_OUTRO, BS_SPECIAL, BS_TELL, Clock, EMPTY, FULL, SP_OUTRO,
                         SPOUT_X, TAP_X, art, arrivals_ok, assert_body, body, pair_id, check_start, fight, frames, mugs, play, pour, row,
                         still_regulars, throw, to_bar, until)
from conftest import clear_regulars, ROOT, check_golden, venue
from test_flow import GS_STORY, LEVEL_CLEAR, LIFE_LOST, PLAYING, inject_mug, run_until, state, tilemap_row
from test_story import banner_text, centred, post, settle, to_goal

pytestmark = pytest.mark.timeout(300)

C = 4                                   # the igloo
R = row(C)
A = art("yeti")
B = R["bar"]
BP_INHALE, BP_BLOW = 5, 6
BS_JUMP, BP_HIDE, BS_ENTER = 4, 14, 7
SFX_LAUNCH, SFX_SHAKE, SFX_WHOOSH = 2, 8, 13
SRC = (ROOT / "src" / "boss_yeti.c").read_text()
EVERY, TELL, ICY, BLOW, CREEP, CREEP_COLS, ICE_COLS = (int(re.search(rf"#define {n}\s+(\d+)", SRC).group(1)) for n in (
    "YETI_EVERY", "YETI_TELL", "YETI_ICY", "YETI_BLOW", "YETI_CREEP", "YETI_CREEP_COLS", "ICE_COLS"))
BANNER, ENT_FROST, ENT_APPEAR, ENT_THAW, ENT_LAND = (int(re.search(rf"#define {n}\s+(\d+)", SRC).group(1)) for n in (
    "YETI_BANNER", "ENT_FROST", "ENT_APPEAR", "ENT_THAW", "ENT_LAND"))
YP_WALK, YP_TELL, YP_ICY, YP_THAW, YP_ENTER = range(5)
COUNTER_ROW = 5 + 3 * B + 2
ICE_BG = 246
SPARK_BG, SPARK_N = 248, 2          # the sparkle frames' tiles (SPARK1-4), at most SPARK_N glinting columns at once
I2 = ["--------", "--------", "++++++++", "########", "--------", "--------"]     # the approved icicles' rows 0-5
I2_A_LOW, I2_B_LOW = [".+-+..+.", "..+....."], [".+--+.+.", "..++...."]       # (rows 6-7 of tile A, of tile B)
VENUE_COUNTER = venue("igloo")["bar_map"][40:60]
ICY_COUNTER = [ICE_BG + A["ice_src"].index(t) if t in A["ice_src"] else t for t in VENUE_COUNTER[:ICE_COLS]]


def counter(gb):
    return tilemap_row(gb, COUNTER_ROW, 0, 20)


def tile_rows(data):
    return ["".join(".-+#"[((data[2 * r] >> (7 - c)) & 1) | (((data[2 * r + 1] >> (7 - c)) & 1) << 1)] for c in range(8))
            for r in range(8)]


def sparkles(gb):
    """{column: glint frame 0-3} of the counter columns showing a sparkle tile."""
    return {n: t - SPARK_BG for n, t in enumerate(counter(gb)) if SPARK_BG <= t < SPARK_BG + 4}


def icy_cols(gb):
    """How many counter columns from the left are icy (and the rest as the venue draws them); a sparkle counts as icy."""
    c = [ICE_BG if SPARK_BG <= t < SPARK_BG + 4 else t for t in counter(gb)]
    n = 0
    while n < ICE_COLS and c[n] == ICY_COUNTER[n]:
        n += 1
    assert c[n:] == VENUE_COUNTER[n:], c
    return n


def test_his_row_and_art():
    """Spec 3.2 / 3.7's numbers and timings, the banner lines of spec 7, his approved art with INHALE and BLOW (extra
    poses 5 and 6), the icy copies of the igloo's two counter tiles (the owner-approved I2 icicles) and the 4 sparkle frames."""
    assert {k: R[k] for k in ("width", "x", "bar", "step", "push", "gulp", "hands", "sip", "meter", "hat")} == dict(
        width=32, x=16, bar=2, step=100, push=8, gulp=44, hands=2, sip=60, meter=12, hat=9)
    assert (R["line1"], R["line2"]) == ("THE YETI IS COLD", "12 COCOAS ON ICE")
    assert A["poses"] == ["WALK", "STOMP", "GULP", "WINCE", "HAPPY", "INHALE", "BLOW"]
    assert (EVERY, TELL, ICY, CREEP, CREEP_COLS, ICE_COLS) == (360, 50, 180, 12, 4, 18) and TELL >= 45
    assert len(A["ice_src"]) == 2 and set(VENUE_COUNTER[:ICE_COLS]) == set(A["ice_src"]) and len(A["ice"]) == 32
    assert tile_rows(A["ice"][:16]) == I2 + I2_A_LOW and tile_rows(A["ice"][16:]) == I2 + I2_B_LOW, "the I2 icicles"
    assert len(A["spark"]) == 64
    for k in range(4):                      # a glint changes rows 0-5 of tile A only: the icicles stay, white on the band
        r = tile_rows(A["spark"][16 * k:16 * k + 16])
        assert r[6:] == I2_A_LOW and r[:6] != I2 and "." not in "".join(r[:6]), k
    assert all(a != b for a, b in zip(ICY_COUNTER, VENUE_COUNTER))
    assert "; Art: approved design" in (ROOT / "assets/art/boss/yeti.txt").read_text()
    assert not (ROOT / "assets/art/approved/boss_yeti.txt").exists()


def sfx(gb, i):
    return gb.read("sfx_count", 14)[i]


def entrance_over(gb):
    until(gb, lambda: gb.mem("yeti_phase") != YP_ENTER and state(gb) == PLAYING, 200)


def quiet(gb):
    still_regulars(gb)
    play(gb)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_fight_follows_the_last_call(model):
    """After the igloo's Last call: BOSS and his lines; the Yeti on bar 2 at x 16 (his tiles, palettes, the icy
    counter tiles at BG 246-247, the sparkle frames 248-251), the meter of 12, his horns as the topper, the counter as the igloo draws it. Golden
    boss_yeti: walking, a cocoa on its way."""
    with fight(model, C, banner=True) as gb:
        assert banner_text(gb, 2) == centred(R["line1"]) and banner_text(gb, 3) == centred(R["line2"])
        to_goal(gb)
        gb.run(2)
        check_start(gb, C, A, model)
        assert bytes(gb.read(0x8000 + ICE_BG * 16, 32)) == bytes(A["ice"])
        assert bytes(gb.read(0x8000 + SPARK_BG * 16, 64)) == bytes(A["spark"])
        assert counter(gb) == VENUE_COUNTER
        assert (gb.mem("yeti_phase"), gb.mem16("boss_special_t")) == (YP_WALK, EVERY)
        quiet(gb)
        throw(gb, B, 100)
        frames(gb, 10)
        check_golden(gb, "boss_yeti")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_breath_tell_ice_and_thaw(model):
    """360 walking frames, then the tell: 50 frames of INHALE (he stands: no stomp), the frost creeping from the left 4
    columns every 12 frames, every counter column icy when the ice starts; the ice: BLOW for 30 frames, then his
    standing pose, 180 frames (boss_icy), his bar fast; the thaw: the counter back in 2 frames; then he walks and the
    next breath is 360 frames away. Goldens boss_yeti_inhale and boss_yeti_blow (the tell and the blow)."""
    with fight(model, C) as gb:
        quiet(gb)
        clock = Clock(gb)
        until(gb, lambda: clock.now() and gb.mem("yeti_phase") == YP_TELL, EVERY + 10)   # (the clock read every frame)
        t_tell = clock.now()
        assert EVERY - 2 <= t_tell <= EVERY + 2, t_tell
        assert gb.mem("boss_state") == BS_TELL
        x = gb.mem("boss_x")
        seen = {}
        while gb.mem("yeti_phase") == YP_TELL:
            frames(gb, 1)
            t = clock.now() - t_tell
            if gb.mem("yeti_phase") != YP_TELL:
                break
            n = icy_cols(gb)
            seen.setdefault(n, t)
            if t == 2:
                assert_body(gb, C, A, gb.mem("boss_x"), BP_INHALE)
            if t == 25:
                check_golden(gb, "boss_yeti_inhale")
        t_icy = clock.now()
        assert TELL - 2 <= t_icy - t_tell <= TELL + 2, t_icy - t_tell
        assert gb.mem("boss_x") == x, "he stands through the tell"
        steps = sorted(seen.items())
        assert [n for n, _ in steps][:4] == [4, 8, 12, 16], steps
        assert all(abs((b - a) - CREEP) <= 2 for (_, a), (_, b) in zip(steps, steps[1:4])), steps
        frames(gb, 2)
        assert icy_cols(gb) == ICE_COLS and gb.mem("boss_state") == BS_SPECIAL
        assert (gb.mem("boss_fast_full"), gb.mem("boss_fast_empty")) == (1, 1)
        assert_body(gb, C, A, gb.mem("boss_x"), BP_BLOW)
        check_golden(gb, "boss_yeti_blow")
        until(gb, lambda: gb.mem("boss_xpose") == 0, BLOW + 4)
        assert BLOW - 3 <= clock.now() - t_icy <= BLOW + 2
        frames(gb, 2)
        assert_body(gb, C, A, gb.mem("boss_x"), BP_WALK)
        until(gb, lambda: clock.now() and gb.mem("yeti_phase") != YP_ICY, ICY)
        t_thaw = clock.now()
        assert ICY - 2 <= t_thaw - t_icy <= ICY + 2 and gb.mem("boss_x") == x, "he stands on the ice"
        until(gb, lambda: gb.mem("yeti_phase") == YP_WALK, 4)
        frames(gb, 2)
        assert counter(gb) == VENUE_COUNTER, "thawed"
        assert (gb.mem("boss_fast_full"), gb.mem("boss_fast_empty"), gb.mem("boss_icy")) == (0, 0, 0)
        assert gb.mem("boss_state") == 0 and EVERY - 4 <= gb.mem16("boss_special_t") <= EVERY
        until(gb, lambda: gb.mem("boss_x") != x, R["step"] + 2)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_sparkles_twinkle_only_on_the_ice(model):
    """None before or in the tell; on the ice at most 2 columns glint at once, all on even columns, each running its
    frames 0-3 in order, columns varying; (the game's RNG is not used); none after the thaw (counter as the venue draws it).
    A lost life mid-sparkle clears them too."""
    with fight(model, C) as gb:
        quiet(gb)
        frames(gb, 120)
        assert not sparkles(gb)
        gb.write("boss_hook", 1)
        while gb.mem("yeti_phase") != YP_ICY:
            frames(gb, 1)
            assert not sparkles(gb), "none in the tell"
        cols, most, last = set(), 0, {}
        while gb.mem("yeti_phase") == YP_ICY:
            frames(gb, 1)
            sp = sparkles(gb)
            cols |= set(sp)
            most = max(most, len(sp))
            assert len(sp) <= SPARK_N and all(c % 2 == 0 and c < ICE_COLS for c in sp), sp
            for c, f in sp.items():
                assert f in (last.get(c, f), last.get(c, f) + 1), (c, f, last)
            last = sp
        assert most == SPARK_N and len(cols) >= 5, (most, sorted(cols))
        until(gb, lambda: gb.mem("yeti_phase") == YP_WALK, 4)
        frames(gb, 2)
        assert not sparkles(gb) and counter(gb) == VENUE_COUNTER
        frames(gb, 20)
        assert not sparkles(gb) and counter(gb) == VENUE_COUNTER
        # the next breath, a life lost while a sparkle glints: counter and sparkles all back
        gb.write("boss_hook", 1)
        until(gb, lambda: gb.mem("yeti_phase") == YP_ICY, TELL + 4)
        until(gb, lambda: len(sparkles(gb)) > 0, 60)
        gb.write("boss_x", SPOUT_X - R["width"])
        until(gb, lambda: state(gb) == LIFE_LOST, 4)
        until(gb, lambda: state(gb) == PLAYING, 200)
        frames(gb, 3)
        assert not sparkles(gb) and counter(gb) == VENUE_COUNTER


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_ice_speeds_his_bar_only_and_only_while_icy(model):
    """Walking: a full mug on his bar slides 2 px a frame. On the ice: 3 px a frame on his bar, still 2 on bar 0; an
    empty on his bar 1 px a frame (0.5 on bar 3). After the thaw: 2 and 0.5 again."""
    with fight(model, C) as gb:
        quiet(gb)
        block = gb.mem16("boss_special_t")

        def speeds(n=12):
            """px per game frame of a full mug on his bar and on bar 0, and of an empty on his bar and on bar 3"""
            gb.write("boss_hold", 0)
            throw(gb, B, 140)
            throw(gb, 0, 140)
            inject_mug(gb, B, 70, st=EMPTY)
            inject_mug(gb, 3, 70, st=EMPTY)
            frames(gb, 1)
            x0 = {(b, s): x for i, s, b, x in mugs(gb)}
            clock = Clock(gb)
            frames(gb, n)
            t = clock.now()
            x1 = {(b, s): x for i, s, b, x in mugs(gb)}
            out = [round((x0[k] - x1[k]) / t, 1) for k in ((B, FULL), (0, FULL))]
            out += [round((x1[k] - x0[k]) / t, 1) for k in ((B, EMPTY), (3, EMPTY))]
            for i, s, b, x in mugs(gb):
                gb.write(gb.addr("mug_state") + i, 0)
            gb.write("mugs_live", 0)
            frames(gb, 2)
            return out

        assert block > 30
        assert speeds() == [2.0, 2.0, 0.5, 0.5]
        gb.write("boss_hook", 1)                     # the tell now
        until(gb, lambda: gb.mem("yeti_phase") == YP_ICY, TELL + 4)
        frames(gb, 2)
        assert speeds() == [3.0, 2.0, 1.0, 0.5]
        until(gb, lambda: gb.mem("yeti_phase") == YP_WALK, ICY + 4)
        frames(gb, 2)
        assert speeds() == [2.0, 2.0, 0.5, 0.5]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_his_empties_keep_to_one_speed_and_the_schedule(model):
    """A held empty never sets off when it would still be on its way as the ice starts (or ends): walking 60 frames
    before the tell he holds it (a 0.5 px trip from x 48 is 144 frames); at the ice's start it goes at once, at 1 px a
    frame, and reaches the tap end before the thaw; the arrivals of everything sent stay >= empty_gap apart."""
    with fight(model, C) as gb:
        quiet(gb)
        to_bar(gb, B)
        gb.write("boss_special_t", 60)
        gb.write(gb.addr("boss_special_t") + 1, 0)
        throw(gb, B, 70)
        until(gb, lambda: gb.mem("boss_hits") == 1, 30)
        clock = Clock(gb)
        while gb.mem("yeti_phase") != YP_ICY:
            assert not mugs(gb, B, EMPTY), "an empty that would cross the ice's start"
            frames(gb, 1)
            assert clock.now() < 200
        t_icy = clock.now()
        until(gb, lambda: mugs(gb, B, EMPTY), 10)
        (i, _, _, x), = mugs(gb, B, EMPTY)
        t_sent = clock.now()
        assert t_sent - t_icy <= 3 and gb.mem("boss_hold") == 0
        assert t_sent + (TAP_X - x) <= t_icy + ICY, "its whole trip on the ice"
        catches = gb.read("sfx_count", 9)[3]
        until(gb, lambda: gb.read("mug_state", 20)[i] != EMPTY, 120)
        frames(gb, 2)
        assert gb.read("sfx_count", 9)[3] == catches + 1 and gb.mem("yeti_phase") == YP_ICY


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_life_lost_on_the_ice_thaws_the_counter(model):
    """His right edge at the tap while the ice is on: a life; after the freeze he is back at x 16 walking, the counter
    as the igloo draws it, his bar slow again, the next breath 360 frames away, his meter kept."""
    with fight(model, C) as gb:
        quiet(gb)
        gb.write("boss_hook", 1)
        until(gb, lambda: gb.mem("yeti_phase") == YP_ICY, TELL + 4)
        frames(gb, 2)
        assert icy_cols(gb) == ICE_COLS
        gb.write("boss_x", SPOUT_X - R["width"])
        until(gb, lambda: state(gb) == LIFE_LOST, 4)
        until(gb, lambda: state(gb) == PLAYING, 200)
        frames(gb, 3)
        assert counter(gb) == VENUE_COUNTER
        assert (gb.mem("yeti_phase"), gb.mem("boss_x"), gb.mem("boss_hp"), gb.mem("lives")) == (YP_WALK, R["x"], 12, 2)
        assert (gb.mem("boss_fast_full"), gb.mem("boss_fast_empty"), gb.mem16("boss_special_t")) == (0, 0, EVERY)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_win_the_fight_by_pouring(model):
    """Real pours on his bar through two breaths (the ice included), the bartender staying at the tap: 12 cocoas and
    he is satisfied; no life lost; every two arrivals of his empties >= empty_gap apart; the outro thaws the counter;
    CHAPTER CLEAR, the POST_IGLOO scene, the chapter saved."""
    with fight(model, C) as gb:
        quiet(gb)
        to_bar(gb, B)
        arrivals, seen, f, phases = [], set(), 0, set()
        clock = Clock(gb)
        while gb.mem("boss_hp") and f < 6000:
            ph = gb.mem("yeti_phase")
            can = ph == YP_WALK and gb.mem16("boss_special_t") > 40 or ph == YP_TELL and gb.mem("yeti_t") < 20 or ph == YP_THAW
            if can and gb.mem("boss_hold") + len(mugs(gb, B, FULL)) < R["hands"]:
                pour(gb)
            else:
                frames(gb, 1)
            f = clock.now()
            phases.add(gb.mem("yeti_phase"))
            fast = gb.mem("boss_fast_empty")
            for i, s, b, x in mugs(gb):
                if s == EMPTY and i not in seen:
                    seen.add(i)
                    arrivals.append((f + (TAP_X - x) * (1 if fast and b == B else 2), False))
            seen &= {i for i, s, _, _ in mugs(gb, st=EMPTY)}
        assert gb.mem("boss_hits") == 12 and gb.mem("lives") == 3
        assert YP_ICY in phases, "the fight went through the ice"
        arrivals_ok(sorted(arrivals), gb.mem("empty_gap"))
        clear_regulars(gb)
        frames(gb, 3)
        assert state(gb) == GS_STORY and gb.mem("story_phase") == SP_OUTRO and gb.mem("boss_state") == BS_OUTRO
        gb.run(60)
        assert_body(gb, C, A, gb.mem("boss_x"), BP_HAPPY)
        assert counter(gb) == VENUE_COUNTER
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 120)
        gb.run(3)
        assert banner_text(gb, 1) == centred("CHAPTER CLEAR")
        run_until(gb, lambda: state(gb) == GS_STORY and gb.mem("story_scene") == post(C), 300)
        settle(gb)
        assert (gb.mem("boss_on"), gb.mem("story_progress")) == (0, C + 1)


def wall_bare(gb):
    """His two wall rows hold none of his body tiles (the igloo's wall as the venue draws it)."""
    top, low = body(gb, R)
    ids = {pair_id(p) + k for p in range(len(A["pairs"])) for k in (0, 1)}
    return not (set(top[:12]) & ids or set(low[:12]) & ids)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_entrance_is_a_frost_front(model):
    """The fight's start: the wall bare (BS_JUMP, BP_HIDE, nothing caught), the counter frosting over left to right
    (never back until the thaw) with a whoosh, he steps out of the frost in the BLOW pose at ENT_APPEAR, the frost
    thaws at ENT_THAW, he WALKS at ENT_LAND with the intro's 90 frames from there and the first breath EVERY away;
    every frame is checked at <= 10 sprites a line (frames()). Golden boss_yeti_entrance: the BLOW, the frost on."""
    with fight(model, C, entrance=True) as gb:
        gb.run(2)
        whoosh = sfx(gb, SFX_WHOOSH)
        assert gb.mem("yeti_phase") == YP_ENTER and gb.mem("boss_state") == BS_ENTER and gb.mem("boss_xpose") == BP_HIDE
        assert wall_bare(gb)
        most = 0
        while gb.mem("yeti_phase") == YP_ENTER:
            t = gb.mem("yeti_t")
            if t < ENT_APPEAR:
                assert gb.mem("boss_state") == BS_ENTER and wall_bare(gb)
                assert gb.mem("boss_hp") == 12 and gb.mem("intro_timer") >= 89, "held until he walks"
            n = sum(1 for a, b in zip(counter(gb), ICY_COUNTER) if a == b or SPARK_BG <= a < SPARK_BG + 4)
            if ENT_THAW + 2 <= t < ENT_LAND:
                assert counter(gb) == VENUE_COUNTER, "thawed"
            assert n >= most or t >= ENT_THAW, (t, n, most)
            most = max(most, n)
            if t == ENT_FROST + 3:
                assert icy_cols(gb) == ICE_COLS and sfx(gb, SFX_WHOOSH) >= 1
            if t == ENT_APPEAR + 3:
                assert_body(gb, C, A, R["x"], BP_BLOW)
                assert gb.mem("boss_state") != BS_JUMP and gb.mem("boss_x") == R["x"]
                check_golden(gb, "boss_yeti_entrance")
            if t == ENT_THAW + 4:
                assert_body(gb, C, A, R["x"], BP_WALK)
            frames(gb, 1)
        assert most >= ICE_COLS - 2, "the frost reached the whole counter"
        frames(gb, 2)
        assert gb.mem("boss_state") == 0 and gb.mem("boss_hp") == 12 and counter(gb) == VENUE_COUNTER
        assert gb.mem("intro_timer") in range(80, 90)
        assert gb.mem("boss_fast_full") == 0
        quiet(gb)
        assert EVERY - 3 <= gb.mem16("boss_special_t") <= EVERY
        throw(gb, B, 100)
        until(gb, lambda: gb.mem("boss_hits") == 1, 40)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_tap_freezes_on_the_ice(model):
    """The ice's trade-off. Walking and in the tell the tap on his bar pours (a mug launches); on the ice it does not: A
    for 30 frames and no mug is launched, no fill shows, a thud sounds once per press; the banner TAP FROZEN shows
    for BANNER frames, with the blow's whoosh; another bar pours as ever; after the thaw his tap pours again."""
    with fight(model, C) as gb:
        quiet(gb)
        to_bar(gb, B)
        pour(gb)
        gb.write("boss_hook", 1)                                # the tell: the tap still pours
        until(gb, lambda: gb.mem("yeti_phase") == YP_TELL, 4)
        pour(gb, 20)                                             # (inside the tell's 50 frames)
        whoosh = sfx(gb, SFX_WHOOSH)
        until(gb, lambda: gb.mem("yeti_phase") == YP_ICY, TELL + 4)
        frames(gb, 2)
        assert sfx(gb, SFX_WHOOSH) == whoosh + 1 and gb.mem("overlay_on") == 1
        assert banner_text(gb, 1) == centred("TAP FROZEN"), banner_text(gb, 1)
        shakes, launches = sfx(gb, SFX_SHAKE), sfx(gb, SFX_LAUNCH)
        gb.hold("a")
        frames(gb, 3)
        assert gb.mem("fill_timer") == 0 and gb.mem("fill_stage") == 0
        frames(gb, 27)
        assert gb.mem("fill_timer") == 0
        gb.release("a")
        frames(gb, 5)
        assert sfx(gb, SFX_LAUNCH) == launches, "nothing launched at him"
        assert sfx(gb, SFX_SHAKE) == shakes + 1, "a thud for the one press"
        until(gb, lambda: gb.mem("overlay_on") == 0, BANNER)
        assert gb.mem("yeti_phase") == YP_ICY
        to_bar(gb, 0)
        launches = sfx(gb, SFX_LAUNCH)
        pour(gb)
        assert sfx(gb, SFX_LAUNCH) == launches + 1, "another bar pours as ever"
        to_bar(gb, B)
        until(gb, lambda: gb.mem("yeti_phase") == YP_WALK, ICY + 4)
        frames(gb, 2)
        launches = sfx(gb, SFX_LAUNCH)
        pour(gb)
        assert sfx(gb, SFX_LAUNCH) == launches + 1, "thawed: his tap pours"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_mug_on_his_bar_rides_the_ice_to_him(model):
    """The help side of the ice: a full mug on his bar when the blow comes slides at 3 px a frame and he drinks it while
    the tap is frozen (a hit, the meter down)."""
    with fight(model, C) as gb:
        quiet(gb)
        to_bar(gb, B)
        gb.write("boss_hook", 1)
        until(gb, lambda: gb.mem("yeti_phase") == YP_ICY, TELL + 4)
        hp = gb.mem("boss_hp")
        throw(gb, B, 150)
        until(gb, lambda: gb.mem("boss_hits") == 1, 40)
        assert gb.mem("boss_hp") == hp - 1 and gb.mem("yeti_phase") == YP_ICY
