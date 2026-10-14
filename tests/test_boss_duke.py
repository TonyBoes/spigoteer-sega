# docs/minigames_bosses.md 3.12: Duke, the Chrome Cow's boss (src/boss_duke.c; art approved 2026-10-12, round 6: H2's
# leather back with H1's forked braided beard). Owner change: he STANDS behind the bar like Big Tex, no bike in the fight.
# His row (40 px, step 0, push 16, gulp 20, hands 2, sip 45, meter 12); IDLE (150 / 120 / 90 frames by the meter), the REV
# tell (50 frames: the throttle twist, TELL1 / TELL2, the helmet jumping), the LURCH (16 px in 8 frames), a catch (restarts
# the idle) and a catch during the rev (the stall). Every frame here is checked at <= 10 sprites a line.
# His ENTRANCE (owner-approved 2026-10-12, X1 "skid and vault"): on the fight's first start he rides in, skids, revs and vaults
# off his chopper (frames 0-61, BS_JUMP + BP_HIDE), lands at x 16 (frame 62) and the intro's 90 frames start there; the
# empty bike rolls on behind him; the drinks' tiles (OBJ 56-91) are borrowed and come back; a retry after a lost life has none.
import re

import pytest
from boss_common import (BP_HAPPY, BP_WALK, BP_STOMP, BS_JUMP, BS_OUTRO, BS_SPECIAL, BS_TELL, BS_WALK, Clock, EMPTY, FULL, OBJ_TOPPER,
                         OAM_TOPPER, Own, block_empties, SP_FAIL, SP_OUTRO, SPOUT_X, TAP_X, art, arrivals_ok, assert_body, check_start,
                         fight, frames, hud, meter_tiles, mugs, play, pour, row, still_regulars, throw, to_bar, until)
from conftest import clear_regulars, ROOT, check_golden, logic_paused, venue
from test_bonus import lines
from test_flow import GS_GOAL, GS_STORY, LEVEL_CLEAR, LIFE_LOST, PLAYING, run_until, score, state
from test_story import banner_text, centred, post, settle, to_goal, to_shift, win

pytestmark = pytest.mark.timeout(300)

C = 6                                   # the biker bar (The Chrome Cow)
R = row(C)
A = art("duke")
B = R["bar"]
BP_TELL1, BP_TELL2 = 5, 6
SRC = (ROOT / "src" / "boss_duke.c").read_text()
IDLE_HI, IDLE_MID, IDLE_LO, REV, HOP, LURCH, STALL = (int(re.search(rf"#define {n}\s+(\d+)", SRC).group(1)) for n in (
    "IDLE_HI", "IDLE_MID", "IDLE_LO", "DUKE_REV", "DUKE_HOP", "DUKE_LURCH", "DUKE_STALL"))
DP_IDLE, DP_REV, DP_LURCH, DP_STALL = range(4)
DUKE = Own("duke")
HAT_STILL, HAT_BOB = OBJ_TOPPER, OBJ_TOPPER + 2
ENT_LAND, ENT_GONE, ENT_TOPPER, ENT_REVSFX = (int(re.search(rf"#define {n}\s+(\d+)", SRC).group(1)) for n in (
    "ENT_LAND", "ENT_GONE", "ENT_TOPPER", "ENT_REVSFX"))
BP_HIDE = 14
INTRO = 90
SFX_SHAKE, SFX_REV = 8, 12
ENT_ART = A["ent"]
OBJ_LO, OBJ_HI = 56, 96                 # the entrance's tile pool: 18 pairs at OBJ 56.., 16 at OBJ 96..


def phase(gb):
    return DUKE.get(gb, "phase")


def quiet(gb):
    still_regulars(gb)
    play(gb)


def idle_from_zero(gb, hp=None):
    """Between two game frames: his idle clock at 0 (and his meter set)."""
    with logic_paused(gb):
        DUKE.put(gb, "t", 0)
        if hp is not None:
            gb.write("boss_hp", hp)


def one_lurch(gb):
    """The rev now (the test hook), through the lurch: he is 16 px further right (x 32), idling from 0."""
    gb.write("boss_hook", 1)
    until(gb, lambda: phase(gb) == DP_REV, 4)
    until(gb, lambda: phase(gb) == DP_LURCH, REV + 4)
    until(gb, lambda: phase(gb) == DP_IDLE, LURCH + 4)
    frames(gb, 2)
    assert gb.mem("boss_x") == 32


def topper(gb):
    return gb.oam()[OAM_TOPPER]


def test_his_row_and_art():
    """Spec 3.2 / 3.12's numbers (step 0: no stomp), the banner lines, the owner-approved art (H2's body, H1's beard) with
    TELL1 and TELL2 (extra poses 5 and 6), and the timings."""
    assert {k: R[k] for k in ("width", "x", "bar", "step", "push", "gulp", "hands", "sip", "meter", "hat")} == dict(
        width=40, x=16, bar=1, step=0, push=16, gulp=20, hands=2, sip=45, meter=12, hat=16)
    assert (R["line1"], R["line2"]) == ("THE BIGGEST SHAKE", "12 MILKS FOR DUKE")
    assert A["poses"] == ["WALK", "STOMP", "GULP", "WINCE", "HAPPY", "TELL1", "TELL2"] and A["cols"] == 5
    assert (IDLE_HI, IDLE_MID, IDLE_LO, REV, HOP * 2, LURCH, STALL) == (150, 120, 90, 50, 8, 8, 20)
    assert len(A["pairs"]) <= 30
    text = (ROOT / "assets/art/boss/duke.txt").read_text()
    assert "; Art: approved design" in text and "no bike" in text
    assert not re.search(r"^(?:static\s+)?u?int(?:8|16)_t\s+\w+\s*(?:[;,=]|\[)", SRC, re.M), "no WRAM of his own"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_fight_follows_the_last_call(model):
    """After the biker bar's Last call: BOSS and his lines; Duke on bar 1 at x 16 (his tiles, palettes, the helmet in its own
    colours), the meter of 12, idling. The regulars come in the venue's chord on the three other bars, no mosh pit.
    Golden boss_duke: idling, a glass on its way."""
    with fight(model, C, banner=True) as gb:
        assert banner_text(gb, 2) == centred(R["line1"]) and banner_text(gb, 3) == centred(R["line2"])
        pat = list(gb.read("pat_buf", 8))
        assert gb.mem("pat_len") == 6
        assert {p & 3 for p in pat[:6]} == {0, 2, 3}, pat
        assert [p >> 4 for p in pat[:6]] == [1, 1, 3, 1, 1, 3], "three at once, a breather, three more"
    with fight(model, C) as gb:
        gb.run(2)
        assert gb.mem("mosh_on") == 0
        until(gb, lambda: DUKE.get(gb, "ent") == 0 and state(gb) == PLAYING, 200)     # (the entrance first: the tests below)
        check_start(gb, C, A, model)
        assert hud(gb) == meter_tiles(12, 12)
        quiet(gb)
        assert (phase(gb), gb.mem("boss_step")) == (DP_IDLE, 0)
        throw(gb, B, 100)
        frames(gb, 10)
        check_golden(gb, "boss_duke")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("hp,want", [(12, IDLE_HI), (9, IDLE_HI), (8, IDLE_MID), (5, IDLE_MID), (4, IDLE_LO), (1, IDLE_LO)])
def test_the_idle_lasts_by_the_meter(model, hp, want):
    """Idle 150 frames at meter 12-9, 120 at 8-5, 90 at 4-1 (counted from his idle clock at 0 to the first frame of the
    rev). The idle pose alternates WALK / STOMP every 8 frames and he does not move."""
    with fight(model, C) as gb:
        quiet(gb)
        idle_from_zero(gb, hp=hp)
        clock = Clock(gb)
        seen = set()
        while phase(gb) == DP_IDLE:
            frames(gb, 1)
            if phase(gb) == DP_IDLE and clock.now() < 40:
                seen.add(gb.mem("boss_pose") & 15)
            assert clock.now() < want + 10
        assert want - 2 <= clock.now() <= want + 2, (hp, clock.now())
        assert seen == {BP_WALK, BP_STOMP} and gb.mem("boss_x") == 16


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_rev_tell_and_the_lurch(model):
    """The rev: 50 frames of TELL1 / TELL2 (8 frames each), he stands (BS_TELL), the helmet jumps 1 px (HAT_BOB, then
    HAT_STILL) every 4 frames; then the lurch: exactly 16 px in 8 frames, 8 px then 8 px 4 frames later (TELL2, BS_SPECIAL),
    then the idle again from 0. Golden boss_duke_tell (TELL1)."""
    with fight(model, C) as gb:
        quiet(gb)
        idle_from_zero(gb, hp=12)
        clock = Clock(gb)
        revs, shakes = gb.read("sfx_count", 13)[12], gb.read("sfx_count", 13)[8]       # SFX_REV (12), SFX_SHAKE (8: the landing's thud was before)
        until(gb, lambda: clock.now() and phase(gb) == DP_REV, IDLE_HI + 10)
        t0 = clock.now()
        assert IDLE_HI - 2 <= t0 <= IDLE_HI + 2
        poses, tiles, golden = [], [], False
        for k in range(REV - 2):
            frames(gb, 1)
            assert phase(gb) == DP_REV and gb.mem("boss_state") == BS_TELL and gb.mem("boss_x") == 16
            poses.append(gb.mem("boss_pose") & 15)
            tiles.append(topper(gb)["tile"])
            if not golden and poses[-1] == BP_TELL1 and tiles[-1] == HAT_STILL and k > 10:
                assert_body(gb, C, A, 16, BP_TELL1)
                check_golden(gb, "boss_duke_tell")
                golden = True
        assert golden and set(poses) == {BP_TELL1, BP_TELL2} and set(tiles) == {HAT_STILL, HAT_BOB}
        runs = [len(m.group(0)) for m in re.finditer(r"(.)\1*", "".join(chr(65 + p) for p in poses))]
        assert max(runs) <= 8 and min(runs[1:-1]) >= 7, runs      # (8-frame poses)
        assert gb.read("sfx_count", 13)[12] == revs + 1 and gb.read("sfx_count", 13)[8] == shakes, "the rev's sound (SFX_REV, not the shake)"
        until(gb, lambda: phase(gb) == DP_LURCH, 6)
        t1 = clock.now()
        assert REV - 2 <= t1 - t0 <= REV + 2, t1 - t0
        xs = []
        for _ in range(LURCH):
            xs.append(gb.mem("boss_x"))
            assert gb.mem("boss_state") == BS_SPECIAL and gb.mem("boss_pose") & 15 == BP_TELL2
            frames(gb, 1)
        frames(gb, 2)
        assert phase(gb) == DP_IDLE and gb.mem("boss_x") == 16 + 16, (xs, gb.mem("boss_x"))
        assert xs == [24] * HOP + [32] * HOP, xs                      # (8 px at once, 8 px more 4 frames later)
        assert DUKE.get(gb, "lurches") == 1 and DUKE.get(gb, "t") <= 4
        assert gb.mem("boss_state") == BS_WALK


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_catch_restarts_the_idle(model):
    """A glass in the idle: meter -1, pushed 16 px (two hops, he is at x 56), the gulp 20 frames, and the idle clock from
    0: the rev comes a full idle (meter 11: 150) after the catch."""
    with fight(model, C) as gb:
        quiet(gb)
        one_lurch(gb)
        idle_from_zero(gb, hp=12)
        frames(gb, 100)
        assert DUKE.get(gb, "t") >= 98
        throw(gb, B, 32 + 40 + 20)
        clock = Clock(gb)
        until(gb, lambda: gb.mem("boss_hits") == 1, 30)
        assert gb.mem("boss_hp") == 11 and DUKE.get(gb, "t") <= 3, "the idle clock from 0"
        until(gb, lambda: gb.mem("boss_x") == 16, 20)
        t_c = clock.now()
        until(gb, lambda: clock.now() and phase(gb) == DP_REV, IDLE_HI + 10)
        assert IDLE_HI - 6 <= clock.now() - t_c + 8 <= IDLE_HI + 6, clock.now() - t_c
        assert gb.mem("boss_x") == 16 and DUKE.get(gb, "stalls") == 0


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_catch_in_the_rev_stalls_him(model):
    """A glass during the rev: no lurch (he does not move forward for the 20 frames of the stall: WINCE while pushed, then
    GULP), the meter -1, then the idle from 0 (the next rev a whole idle later)."""
    with fight(model, C) as gb:
        quiet(gb)
        one_lurch(gb)
        idle_from_zero(gb, hp=12)
        until(gb, lambda: phase(gb) == DP_REV, IDLE_HI + 10)
        frames(gb, 10)
        throw(gb, B, 32 + 40 + 6)
        until(gb, lambda: gb.mem("boss_hits") == 1, 30)
        assert phase(gb) == DP_STALL and DUKE.get(gb, "stalls") == 1
        x0, t0 = gb.mem("boss_x"), 0
        assert DUKE.get(gb, "lurches") == 1                 # (the one lurch before)
        clock = Clock(gb)
        xs = [x0]
        while phase(gb) == DP_STALL:
            frames(gb, 1)
            xs.append(gb.mem("boss_x"))
            assert clock.now() < STALL + 6
        assert STALL - 2 <= clock.now() <= STALL + 2 and max(xs) <= x0 and xs[-1] == 16, xs
        frames(gb, 2)
        assert DUKE.get(gb, "lurches") == 1 and phase(gb) == DP_IDLE and gb.mem("boss_hp") == 11
        clock = Clock(gb)
        until(gb, lambda: clock.now() and phase(gb) == DP_REV, IDLE_HI + 10)
        assert IDLE_HI - 6 <= clock.now() <= IDLE_HI + 6


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_glass_in_every_rev_never_lets_him_lurch(model):
    """A glass in each rev (about every 190-210 frames: stall 20 + idle 150 + 30 into the rev; his hands emptied for each, so
    this is the rhythm alone) stalls it, and he never lurches."""
    with fight(model, C) as gb:
        quiet(gb)
        idle_from_zero(gb, hp=12)
        block_empties(gb)                        # (no empty is sent: nobody catches it here)
        for n in range(4):
            until(gb, lambda: phase(gb) == DP_REV, 200)
            frames(gb, 30)                       # (the glass lands in his rev)
            with logic_paused(gb):
                gb.write("boss_hold", 0)
            throw(gb, B, gb.mem("boss_x") + 40 + 10)
            until(gb, lambda: gb.mem("boss_hits") == n + 1, 40)
            frames(gb, 25)
            assert phase(gb) == DP_IDLE
        assert DUKE.get(gb, "lurches") == 0 and DUKE.get(gb, "revs") == 4 and DUKE.get(gb, "stalls") == 4
        assert gb.mem("boss_hp") == 8 and gb.mem("lives") == 3


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_unhit_he_reaches_the_tap_and_the_life_is_lost(model):
    """Unhit: the first lurch at frame ~200 (150 + 50), then one every 208, five lurches; his right edge at the tap
    (frame ~1040): a life, then he is back at x 16 idling with the meter kept."""
    with fight(model, C) as gb:
        quiet(gb)
        idle_from_zero(gb)
        clock = Clock(gb)
        firsts = []
        until(gb, lambda: clock.now() and (DUKE.get(gb, "lurches") > len(firsts) and not firsts.append(clock.now()))
              or state(gb) == LIFE_LOST, 1200)
        assert 192 <= firsts[0] <= 208, firsts
        until(gb, lambda: clock.now() and state(gb) == LIFE_LOST, 1200)
        t = clock.now()
        assert 1030 <= t <= 1056, t
        assert DUKE.get(gb, "lurches") == 5
        until(gb, lambda: state(gb) == PLAYING, 200)
        frames(gb, 3)
        assert (gb.mem("boss_x"), gb.mem("boss_hp"), gb.mem("lives"), phase(gb)) == (R["x"], 12, 2, DP_IDLE)
        assert_body(gb, C, A, R["x"], BP_WALK)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_life_lost_in_the_rev_ends_it(model):
    """His right edge at the tap in the rev: a life; after the freeze he idles at x 16 again."""
    with fight(model, C) as gb:
        quiet(gb)
        gb.write("boss_hook", 1)
        until(gb, lambda: phase(gb) == DP_REV, 4)
        frames(gb, 2)
        gb.write("boss_x", SPOUT_X - R["width"])
        until(gb, lambda: state(gb) == LIFE_LOST, 4)
        until(gb, lambda: state(gb) == PLAYING, 200)
        frames(gb, 3)
        assert (phase(gb), gb.mem("boss_x"), gb.mem("boss_hp"), gb.mem("lives")) == (DP_IDLE, R["x"], 12, 2)
        assert gb.mem("boss_xpose") == 0 and topper(gb)["tile"] == HAT_STILL


@pytest.mark.parametrize("model", ["cgb"])
def test_with_full_hands_a_glass_in_the_rev_passes_him_and_does_not_stall(model):
    """Both hands full during the rev: a glass thrown at him is not caught (boss_lim 0): it slides through to his left and
    no stall, no hit; the rev goes on."""
    with fight(model, C) as gb:
        quiet(gb)
        gb.write("boss_hook", 1)
        until(gb, lambda: phase(gb) == DP_REV, 4)
        with logic_paused(gb):
            gb.write("boss_hold", 2)
            gb.write("next_arrival", 0xFF)
            gb.write(gb.addr("next_arrival") + 1, 0x7F)
        x = gb.mem("boss_x")
        throw(gb, B, x + 40 + 12)
        frames(gb, 20)
        assert gb.mem("boss_hits") == 0 and DUKE.get(gb, "stalls") == 0 and phase(gb) == DP_REV
        left = [m for m in mugs(gb, B, FULL)]
        assert left and left[0][3] < x + 40 - 4, left


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_win_the_fight_by_pouring(model):
    """Real pours on his bar (no hp poke), the bartender at the tap: 12 milks and he is satisfied; no life lost; every two
    empties arrive >= empty_gap apart; the outro (HAPPY); CHAPTER CLEAR, the POST_BIKER scene, the chapter saved."""
    with fight(model, C) as gb:
        quiet(gb)
        to_bar(gb, B)
        arrivals, seen, f = [], set(), 0
        clock = Clock(gb)
        while gb.mem("boss_hp") and f < 6000:
            if gb.mem("boss_hold") + len(mugs(gb, B, FULL)) < R["hands"]:
                pour(gb)
            else:
                frames(gb, 1)
            f = clock.now()
            for i, s, b, x in mugs(gb):
                if s == EMPTY and i not in seen:
                    seen.add(i)
                    arrivals.append((f + (TAP_X - x) * 2, False))
            seen &= {i for i, s, _, _ in mugs(gb, st=EMPTY)}
        print(f"duke bot win: {f} frames, hits {gb.mem('boss_hits')}, revs {DUKE.get(gb, 'revs')}, "
              f"lurches {DUKE.get(gb, 'lurches')}, stalls {DUKE.get(gb, 'stalls')}, lives {gb.mem('lives')}")
        assert gb.mem("boss_hits") == 12 and gb.mem("lives") == 3
        arrivals_ok(sorted(arrivals), gb.mem("empty_gap"))
        clear_regulars(gb)
        frames(gb, 3)
        assert state(gb) == GS_STORY and gb.mem("story_phase") == SP_OUTRO and gb.mem("boss_state") == BS_OUTRO
        gb.run(60)
        assert_body(gb, C, A, gb.mem("boss_x"), BP_HAPPY)
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 120)
        gb.run(3)
        assert banner_text(gb, 1) == centred("CHAPTER CLEAR")
        run_until(gb, lambda: state(gb) == GS_STORY and gb.mem("story_scene") == post(C), 300)
        settle(gb)
        assert (gb.mem("boss_on"), gb.mem("story_progress")) == (0, C + 1)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_regulars_come_in_chords_on_the_other_bars(model):
    """With the regulars live: every one that appears is on bars 0, 2 or 3 (never his), and in 900 frames the three free
    bars all get some."""
    with fight(model, C) as gb:
        play(gb)
        bars, seen = set(), set()
        for _ in range(900):
            frames(gb, 1)
            for i, s in enumerate(gb.read("patron_state", 16)):
                if s and i not in seen:
                    seen.add(i)
                    bars.add(gb.read("patron_bar", 16)[i] & 3)
            if state(gb) != PLAYING:
                break
        assert bars <= {0, 2, 3} and len(bars) >= 2, bars


# ---- the entrance ----------------------------------------------------------------------------------------------------
def ent_t(gb):
    """The entrance frame the game has reached (0-based), None when it is not running (or not begun)."""
    e = DUKE.get(gb, "ent")
    return e - 2 if e >= 2 else None


def sfx(gb, n):
    return gb.read("sfx_count", 13)[n]


def entrance_oam(gb):
    """The entries the entrance may use (OAM 5-24): (y, x, tile, flags) of the ones on."""
    return [(o["y"], o["x"], o["tile"], o["flags"]) for o in gb.oam()[5:25] if o["y"]]


def to_frame(gb, t):
    """Frame by frame (each checked at <= 10 sprites a line) to the moment the entrance has just drawn its frame t."""
    while ent_t(gb) != t:
        assert ent_t(gb) is None or ent_t(gb) < t, (ent_t(gb), t)
        frames(gb, 1)


def frames_to_first_beat(gb):
    """From now (his idle clock at 0, the intro running) to the first frame of his own clock (duke.t 1), in game frames (the
    landing frame itself overruns by a few lines: an emulator frame can hold none)."""
    clock = Clock(gb)
    while DUKE.get(gb, "t") == 0:
        frames(gb, 1)
        assert clock.now() < INTRO + 5
    return clock.now()


def poke_a_life_lost(gb):
    gb.write("boss_x", SPOUT_X - R["width"])
    until(gb, lambda: state(gb) == LIFE_LOST, 4)
    until(gb, lambda: state(gb) == PLAYING, 200)


def bar_row(r):
    return 5 + 3 * r["bar"]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_entrance_plays_on_the_first_start_only(model):
    """The first start: BS_JUMP with no body (BP_HIDE), no topper, nothing caught, the intro held at INTRO until frame 62, the
    rev's sound once (SFX_REV from frame 28, the shake once at the landing); then he is on his bar, WALK at x 16, and the
    intro runs its 90 frames from there. After a lost life: no entrance, he is there at once, the intro runs from its start."""
    with fight(model, C) as gb:
        assert DUKE.get(gb, "ent") >= 1 and gb.mem("boss_state") == BS_JUMP and gb.mem("boss_xpose") == BP_HIDE
        revs, shakes = sfx(gb, SFX_REV), sfx(gb, SFX_SHAKE)
        assert gb.oam()[OAM_TOPPER]["y"] == 0, "no topper before he lands"
        for t in (5, ENT_REVSFX - 1, ENT_REVSFX + 2, ENT_LAND - 1):
            to_frame(gb, t)
            assert gb.mem("boss_state") == BS_JUMP and gb.mem("intro_timer") >= INTRO - 1, "the intro is held"
            assert gb.mem("boss_hp") == 12 and gb.mem("boss_hits") == 0 and gb.mem("boss_lim") == 0, "he catches nothing"
            assert gb.oam()[OAM_TOPPER]["y"] == 0
            assert sfx(gb, SFX_REV) == revs + (t >= ENT_REVSFX + 2), t
        frames(gb, 1)
        assert gb.mem("boss_state") == BS_WALK and gb.mem("intro_timer") == INTRO - 1, "he lands: the intro's 90 frames start"
        assert sfx(gb, SFX_SHAKE) == shakes + 1 and sfx(gb, SFX_REV) == revs + 1
        n_landing = frames_to_first_beat(gb)
        assert INTRO - 2 <= n_landing <= INTRO, n_landing       # (89 game frames: the sampling is up to one frame off)
        assert DUKE.get(gb, "ent") == 0 and sfx(gb, SFX_REV) == revs + 1
        assert entrance_oam(gb) == [], "the entrance's entries are all off"
        still_regulars(gb)
        play(gb)
        poke_a_life_lost(gb)
        assert DUKE.get(gb, "ent") == 0 and gb.mem("boss_state") == BS_WALK and gb.mem("boss_x") == R["x"]
        assert gb.mem("boss_xpose") == 0 and gb.mem("lives") == 2
        until(gb, lambda: gb.mem("intro_timer") == INTRO - 1, 3)
        assert abs(frames_to_first_beat(gb) - n_landing) <= 1, "the same frames to the first beat as after a retry's start (the old start)"
        assert entrance_oam(gb) == []


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_hand_off_lands_him_at_x16_in_his_idle(model):
    """Frame 62: boss_to_bar(1, 16): his BG body (WALK) at x 16 on his bar, the idle clock at 0, the topper over his head;
    the empty bike carries on right behind him (its lower row of entries has the BG-priority bit, the upper row does not)."""
    with fight(model, C) as gb:
        to_frame(gb, ENT_LAND - 1)
        assert gb.mem("boss_x") == R["x"] and gb.mem("boss_pose") & 15 == BP_HIDE
        assert not any(o[3] & 0x80 for o in entrance_oam(gb)), "no priority bit before the landing"
        frames(gb, 2)
        assert gb.mem("boss_state") == BS_WALK and gb.mem("boss_bar") == B and gb.mem("boss_x") == R["x"]
        assert (phase(gb), DUKE.get(gb, "t"), gb.mem("boss_xpose")) == (DP_IDLE, 0, 0)
        assert_body(gb, C, A, R["x"], BP_WALK)
        o = gb.oam()[OAM_TOPPER]
        assert (o["y"], o["x"], o["tile"]) == (bar_row(R) * 8 + 8, R["x"] + R["hat"] + 8, HAT_STILL)
        bike = entrance_oam(gb)
        assert sum(1 for e in bike if e[3] & 0x80) >= 5 and any(not e[3] & 0x80 for e in bike), bike
        assert gb.mem("boss_hold") == 0 and gb.mem("boss_hp") == 12
        frames(gb, 30)
        assert gb.mem("boss_x") == R["x"] and phase(gb) == DP_IDLE


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_every_entrance_frame_keeps_to_ten_sprites_a_line(model):
    """Every game frame of the entrance and the intro that follows (frames() checks each at <= 10 a line; the budget is
    used: 10 at the most crowded). The bartender, held at bar 0's tap, is out of sight for the vault (frames 46-61: the empty
    bike's 6 a line, Duke's 3 and his helmet make 10 without him) and back after."""
    with fight(model, C) as gb:
        worst, y0 = 0, gb.oam()[0]["y"]
        for _ in range(ENT_GONE + 40):
            frames(gb, 1)
            worst = max(worst, max(lines(gb)))
            t = ent_t(gb)
            if t is None:
                continue
            bt = [o["y"] for o in gb.oam()[:4]]
            if ENT_LAND - 14 <= t <= ENT_LAND - 2:      # (the edges of the vault: OAM memory may be a frame behind the logic)
                assert not any(bt), (t, bt)
            elif t <= ENT_LAND - 18 or t >= ENT_LAND + 2:
                assert all(bt), (t, bt)
            assert bt[0] in (0, y0) and bt[2] in (0, y0 + 16), "at bar 0's tap"
        assert worst == 10, worst


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_player_cannot_pour_or_move_during_the_entrance(model):
    """Input is held off until the bike has gone and the drinks' tiles are back: Down and A change nothing (no glass, the
    bartender at bar 0's tap); afterwards the bartender is his again."""
    with fight(model, C) as gb:
        gb.hold("down")
        gb.hold("a")
        y0 = gb.oam()[0]["y"]
        for _ in range(ENT_GONE - 10):
            frames(gb, 1)
            assert gb.oam()[0]["y"] in (0, y0) and not mugs(gb) and gb.oam()[4]["y"] == 0, ent_t(gb)
        gb.release("down")
        gb.release("a")
        until(gb, lambda: DUKE.get(gb, "ent") == 0, 40)
        frames(gb, 2)
        to_bar(gb, 2)
        assert gb.mem("bar") == 2


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_tile_pool_is_borrowed_and_given_back(model):
    """The entrance's tile pairs sit at OBJ 56-91 and 96-127 while it plays; the topper's OBJ 96-99 are his own again from
    frame 50 (the rev's frames are gone); the drinks' OBJ 56-91 (mug, crash glass, fill, drink: the venue's own) are back after
    the bike has gone, the coin's 92-95 never changed; CGB: OBJ 5 holds his body's colours."""
    v = venue(C)
    drinks = bytes(v["drink"][:64]) + bytes(v["crash"]) + bytes(v["drink"][64:])
    pairs = ENT_ART["pairs"]
    assert len(pairs) <= 34
    with fight(model, C) as gb:
        coin = bytes(gb.read(0x8000 + 92 * 16, 64))
        to_frame(gb, 10)
        for k, p in enumerate(pairs):
            at = OBJ_LO + 2 * k if k < 18 else OBJ_HI + 2 * (k - 18)
            assert bytes(gb.read(0x8000 + at * 16, 32)) == bytes(p), f"pair {k} at OBJ {at}"
        assert bytes(gb.read(0x8000 + 92 * 16, 64)) == coin
        if model == "cgb":
            from test_venues import cgb_palette
            assert cgb_palette(gb, 5, True)[1:] == A["pal"][1:], "OBJ 5: his body's colours"
        to_frame(gb, ENT_TOPPER + 3)
        assert bytes(gb.read(0x8000 + OBJ_TOPPER * 16, len(A["hat"]))) == bytes(A["hat"]), "the topper's tiles are back"
        to_frame(gb, ENT_GONE - 1)
        assert bytes(gb.read(0x8000 + OBJ_LO * 16, 36 * 16)) != drinks
        until(gb, lambda: DUKE.get(gb, "ent") == 0, 40)
        frames(gb, 2)
        assert bytes(gb.read(0x8000 + OBJ_LO * 16, 36 * 16)) == drinks, "the drinks are back"
        assert bytes(gb.read(0x8000 + 92 * 16, 64)) == coin
        assert bytes(gb.read(0x8000 + OBJ_TOPPER * 16, len(A["hat"]))) == bytes(A["hat"])


def named_blocks(path):
    out, name, cur = {}, None, []
    for ln in path.read_text().splitlines() + [""]:
        if ln.startswith(";"):
            continue
        if ln.startswith("@"):
            name, cur = ln[1:], []
        elif ln == "" and name and cur:
            out[name], name = cur, None
        elif name:
            cur.append(ln)
    return out


def test_the_riders_face_is_the_boss_face_and_the_empty_bike_is_complete():
    """The entrance's rider carries the boss's head pixel for pixel (the face rows 0-4 of WALK, cols 12-27, and his forked
    beard, cream beads and all) at the same scale in RIDE and HOP; his helmet sprite is the boss's own dome (HAT_STILL rows 2-7);
    BIKE has its own seat, tank and frame and no ginger (that is Duke's)."""
    boss, ent = named_blocks(ROOT / "assets/art/boss/duke.txt"), named_blocks(ROOT / "assets/art/duke_entrance.txt")
    walk = boss["WALK"]
    for frame, x in (("RIDE", 10), ("HOP", 3)):
        for r in range(5):
            assert ent[frame][6 + r][x:x + 16] == walk[r][12:28], (frame, r)
        assert "--######--" in ent[frame][6 + 13] and "--######--" in ent[frame][6 + 14], "the forked beard's cream beads"
    assert ent["HELM"][8:14] == boss["HAT_STILL"][2:8] and all(set(r) == {"."} for r in ent["HELM"][:8] + ent["HELM"][14:])
    bike = ent["BIKE"]
    assert not any("+" in r for r in bike), "no ginger on the bike"
    assert sum(r[2:15].count("#") for r in bike[13:18]) >= 30 and any("-" in r[2:15] for r in bike[13:18]), "a black seat"
    assert sum(r[15:35].count("-") for r in bike[9:16]) >= 40, "a cream tank"
    assert bike[18][14:33] == "#" * 19 and set(bike[19][14:33]) == {"-"} and bike[20][14:33] == "#" * 19, "the backbone"
    assert all(set(r) == {"."} for r in bike[:5])
    assert any("+" in r for r in ent["RIDE"][11:22]), "the rider's chaps are in RIDE, not in BIKE"


def fight_hard(model, c):
    """The fight's play with Practice's HARD toggle set (boss_hard) before it starts."""
    gb = to_shift(model, c, 2)
    gb.write("boss_hard", 1)
    win(gb, c, 2)
    run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 20)
    gb.run(3)
    run_until(gb, lambda: state(gb) == GS_GOAL, 300)
    gb.run(3)
    return to_goal(gb)


@pytest.mark.parametrize("model", ["cgb"])
def test_practice_hard_starts_with_the_entrance_too(model):
    """Practice's HARD toggle (boss_hard before the fight): the entrance plays, then he is there with one hand fewer."""
    with fight_hard(model, C) as gb:
        assert gb.mem("boss_hard") == 1 and DUKE.get(gb, "ent") >= 1 and gb.mem("boss_state") == BS_JUMP
        to_frame(gb, ENT_LAND)
        frames(gb, 2)
        assert gb.mem("boss_state") == BS_WALK and gb.mem("boss_x") == R["x"] and gb.mem("boss_hands") == 1
        assert INTRO - 5 <= frames_to_first_beat(gb) <= INTRO - 2


@pytest.mark.parametrize("model", ["cgb"])
def test_boss_rush_starts_with_the_entrance_too(model):
    """BOSS RUSH, CHOOSE on Duke: the same entrance, he lands at x 16 and the fight is the usual one (89 frames to his first
    beat, the meter 12)."""
    from test_rush import BUILT, booted, into_fight, tap, to_list, v7_image
    ram0 = v7_image([("ABC", 500)], story=2, step=1, story_tbl=[("STO", 900)])
    with booted(model, ram0) as gb:
        to_list(gb)
        for _ in range(BUILT.index(C)):
            tap(gb, "down")
        tap(gb, "a")
        into_fight(gb)
        assert gb.mem("boss_id") == C and DUKE.get(gb, "ent") >= 1 and gb.mem("boss_state") == BS_JUMP
        to_frame(gb, ENT_LAND)
        frames(gb, 2)
        assert gb.mem("boss_state") == BS_WALK and gb.mem("boss_x") == R["x"]
        assert_body(gb, C, A, R["x"], BP_WALK)
        assert INTRO - 5 <= frames_to_first_beat(gb) <= INTRO - 2
        assert gb.mem("boss_hp") == 12 and DUKE.get(gb, "ent") == 0 and gb.mem("lives") == 3


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_entrance_goldens(model):
    """Golden boss_duke_entrance_ride: frame 22 (skidding, the dust behind the rear tyre); boss_duke_entrance_vault: frame 52
    (Duke in the air, the empty bike rolling away, the bartender out of sight)."""
    with fight(model, C) as gb:
        to_frame(gb, 22)
        check_golden(gb, "boss_duke_entrance_ride")
        to_frame(gb, 52)
        check_golden(gb, "boss_duke_entrance_vault")
