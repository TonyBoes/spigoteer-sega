# docs/minigames_bosses.md 3.10: the Mothership, the space lounge's boss (src/boss_mothership.c; art approved 2026-10-11: look A
# "silver saucer"). Phase 1: the saucer (row 40 px, step 100, push 8, gulp 24, hands 2, sip 45, meter 14 = 8 + 6): every 300
# frames of walking a 60-frame TELL (the beam on a random other bar, the antenna blinking), the wait for the earlier glasses,
# 10 frames gone, then he is on that bar at x 16 / 32 / 48. Phase 2, at meter 6: a 40-frame FLASH, then the split (the group's
# patron tiles over the saucer's, the LCD off for a frame) into three hurried mini aliens on three bars, two drinks each, served
# out wherever they stand; the saucer's hidden bar is the one without a mini. Every frame here is checked at <= 10 sprites a line.
import re

import pytest
from boss_common import (BP_HAPPY, BP_WALK, BS_JUMP, BS_OUTRO, BS_TELL, BS_WALK, Clock, EMPTY, FULL, OAM_TOPPER, OBJ_TOPPER, Own,
                         SP_FAIL, SP_OUTRO, TAP_X, art, assert_body, bar_row, check_start, fight, frames, hud, meter_tiles, mugs,
                         play, pose_cols, pour, row, still_regulars, throw, to_bar, until)
from conftest import ROOT, check_golden, logic_paused, venue
from test_boss_mascot import marker_at, rows_of
from test_flow import GS_STORY, LEVEL_CLEAR, LIFE_LOST, PLAYING, run_until, score, state
from test_story import banner_text, centred, post, settle, to_shift
from test_venues import cgb_palette

pytestmark = pytest.mark.timeout(300)

C = 9                                   # the space lounge
R = row(C)
A = art("mothership")
B = R["bar"]
SRC = (ROOT / "src" / "boss_mothership.c").read_text()
MS_EVERY, MS_TELL, MS_WAITMAX, MS_GONE, MS_FLASH, SPLIT_HP, MINI_X = (int(re.search(rf"#define {n}\s+(\d+)", SRC).group(1)) for n in (
    "MS_EVERY", "MS_TELL", "MS_WAITMAX", "MS_GONE", "MS_FLASH", "SPLIT_HP", "MINI_X"))
MP_WALK, MP_TELL, MP_WAIT, MP_GONE, MP_FLASH, MP_MINIS = range(6)
MS = Own("mothership")
HAT_STILL, HAT_BOB = OBJ_TOPPER, OBJ_TOPPER + 2
BP_HIDE = 14
NONE, WALKING, PUSHED, DRINKING, LEAVING = range(5)
PATRON_BASE, PATRON_TILES = 78, 156     # the group's patron tiles (BG 78-233): build/art.h PATRON_FIRST_TILE, PATRON_GROUP_TILES
LAND_X = (16, 32, 48)


def phase(gb):
    return MS.get(gb, "phase")


def quiet(gb):
    still_regulars(gb)
    play(gb)
    gb.write("spawn_timer", 0xFF)
    gb.write(gb.addr("spawn_timer") + 1, 0x7F)


def topper(gb):
    return gb.oam()[OAM_TOPPER]


def to_tell(gb):
    gb.write("boss_hook", 1)
    until(gb, lambda: phase(gb) == MP_TELL, 4)


def minis(gb):
    """[(slot, bar, x, state, drinks, hurry)] of the live mini aliens (variant C: only the minis use it in a fight)."""
    st, bar, x = gb.read("patron_state", 16), gb.read("patron_bar", 16), gb.read("patron_x", 16)
    var, dr, hu = gb.read("patron_variant", 16), gb.read("patron_drinks", 16), gb.read("patron_hurry", 16)
    return [(p, bar[p] & 3, x[p], st[p], dr[p], hu[p]) for p in range(16) if st[p] and var[p] == 2]


def alive(gb):
    return [m for m in minis(gb) if m[3] != LEAVING]


def patron_tiles(gb):
    """The group's patron tiles, by BG id (ids below 128 at 0x9000, the rest at 0x8800)."""
    return b"".join(bytes(gb.read((0x9000 if t < 128 else 0x8000) + t * 16, 16)) for t in range(PATRON_BASE, PATRON_BASE + PATRON_TILES))


def split_now(gb, hp=SPLIT_HP + 1):
    """In the phase 1 with the meter at `hp`, one glass: meter SPLIT_HP, the FLASH; through to the minis."""
    with logic_paused(gb):
        gb.write("boss_hp", hp)
    throw(gb, gb.mem("boss_bar"), gb.mem("boss_x") + 40 + 10)
    until(gb, lambda: phase(gb) == MP_FLASH, 30)


def to_minis(gb):
    split_now(gb)
    until(gb, lambda: phase(gb) == MP_MINIS, MS_FLASH + 30)
    frames(gb, 3)


def test_his_row_and_art():
    """Spec 3.2 / 3.10's numbers (meter 14: the doc's 8 + 6), the banner lines, the owner-approved art (look A, silver saucer) with
    the BEAM as its fx (two columns of it side by side, 4 tiles), the art folder moved, and the timings."""
    assert {k: R[k] for k in ("width", "x", "bar", "step", "push", "gulp", "hands", "sip", "meter", "hat")} == dict(
        width=40, x=16, bar=1, step=100, push=8, gulp=24, hands=2, sip=45, meter=14, hat=12)
    assert (R["line1"], R["line2"]) == ("THE MOTHERSHIP", "IT SPLITS WHEN FULL")
    assert A["poses"] == ["WALK", "STOMP", "GULP", "WINCE", "HAPPY"] and A["cols"] == 5 and len(A["pairs"]) <= 30
    assert len(A["fx"]) == 64 and A["fx"][:32] == A["fx"][32:], "the beam: one 8x16 column, doubled"
    assert (MS_EVERY, MS_TELL, MS_GONE, MS_FLASH, SPLIT_HP, MINI_X) == (300, 60, 10, 40, 6, 24)
    text = (ROOT / "assets/art/boss/mothership.txt").read_text()
    assert "; Art: approved design" in text and "silver saucer" in text and "@BEAM" in text
    assert not (ROOT / "assets/art/approved/boss_mothership.txt").exists()
    assert "boss_mothership" not in (ROOT / "assets/art/approved/README.md").read_text()
    assert not re.search(r"^(?:static\s+)?u?int(?:8|16)_t\s+\w+\s*(?:[;,=]|\[)", SRC, re.M), "no WRAM of his own"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_fight_follows_the_last_call(model):
    """After the space lounge's Last call: BOSS and his lines; the saucer on bar 1 at x 16 (his tiles, palettes, the antenna in the
    same colours), the meter of 14, walking. Golden boss_mothership: hovering, a glass on its way."""
    with fight(model, C, banner=True) as gb:
        assert banner_text(gb, 2) == centred(R["line1"]) and banner_text(gb, 3) == centred(R["line2"])
        assert gb.mem("boss_id") == C
    with fight(model, C) as gb:
        gb.run(2)
        check_start(gb, C, A, model)
        assert hud(gb) == meter_tiles(14, 14)
        quiet(gb)
        assert (phase(gb), gb.mem16("boss_special_t") > 200, gb.mem("boss_step")) == (MP_WALK, True, 100)
        throw(gb, B, 100)
        frames(gb, 10)
        check_golden(gb, "boss_mothership")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_teleport_comes_every_300_frames_of_walking(model):
    """Untouched: the tell starts 300 frames after the fight does (the clock counts the walking)."""
    with fight(model, C) as gb:
        quiet(gb)
        clock = Clock(gb)
        until(gb, lambda: clock.now() and phase(gb) == MP_TELL, MS_EVERY + 40)
        assert MS_EVERY - 6 <= clock.now() <= MS_EVERY + 6, clock.now()


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_tell_the_beam_and_the_teleport(model):
    """The tell (60 frames): the beam on a random other bar under where he will land (x 16 / 32 / 48: columns 2, 3 of his 5), the
    antenna blinking (HAT_BOB every 4 frames), he stands. Then 10 frames gone (no body, no antenna) and he is on that bar at the
    landing x, the beam gone, the meter and hands along. Golden boss_mothership_tell (the beam, the antenna lit)."""
    with fight(model, C) as gb:
        quiet(gb)
        with logic_paused(gb):
            gb.write("boss_hold", 2)
            gb.write("boss_sip_t", 0)
        to_tell(gb)
        frames(gb, 2)
        tb, land = MS.get(gb, "target"), MS.get(gb, "land")
        assert tb != B and land in LAND_X and gb.mem("boss_state") == BS_TELL
        assert marker_at(gb, tb) == land // 8 + 2, "the beam under the saucer's middle"
        assert all(marker_at(gb, b) is None for b in range(4) if b != tb)
        tiles, golden = set(), False
        t0 = MS.get(gb, "t")
        for _ in range(MS_TELL - 6):
            frames(gb, 1)
            assert phase(gb) == MP_TELL and gb.mem("boss_state") == BS_TELL and gb.mem("boss_x") == 16
            tiles.add(topper(gb)["tile"])
            if not golden and topper(gb)["tile"] == HAT_BOB and MS.get(gb, "t") > 20:
                check_golden(gb, "boss_mothership_tell")
                golden = True
        assert golden and tiles == {HAT_STILL, HAT_BOB}
        until(gb, lambda: phase(gb) == MP_GONE, 20)
        assert gb.mem("boss_state") == BS_JUMP and gb.mem("boss_bar") == B
        frames(gb, 2)
        assert topper(gb)["y"] == 0
        top, bottom = rows_of(gb, B)
        assert top[2:7] != pose_cols(A, BP_WALK) and marker_at(gb, tb) == land // 8 + 2
        until(gb, lambda: gb.mem("boss_bar") == tb, MS_GONE + 4)
        frames(gb, 3)
        assert (gb.mem("boss_x"), gb.mem("boss_state"), MS.get(gb, "jumps"), phase(gb)) == (land, BS_WALK, 1, MP_WALK)
        hold = gb.mem("boss_hold")
        assert marker_at(gb, tb) is None and hold >= 1 and gb.mem("boss_hp") == 14, "his hands went with him"
        top, bottom = rows_of(gb, tb)
        cols = pose_cols(A, BP_WALK, hold)
        assert top[land // 8:land // 8 + 5] == cols and bottom[land // 8:land // 8 + 5] == [t + 1 for t in cols]


@pytest.mark.parametrize("model", ["cgb"])
def test_he_takes_the_glass_already_on_its_way_before_he_goes(model):
    """A glass on its way at the tell's first frame (launched at the spout) reaches him inside the 60 frames: a hit (meter 13,
    pushed back, the landing x is where he lands anyway), and he teleports after it, never with a glass still on his bar. The
    wait (as the Mascot's) only matters when a glass is slower than the tell."""
    with fight(model, C) as gb:
        quiet(gb)
        throw(gb, B, 130)
        to_tell(gb)
        until(gb, lambda: phase(gb) == MP_GONE, MS_TELL + MS_WAITMAX + 4)
        assert gb.mem("boss_hits") == 1 and not mugs(gb, B, FULL) and gb.mem("boss_hp") == 13


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_catch_is_the_common_one(model):
    """A glass: meter 13, pushed 8 px (WINCE), the gulp 24 frames, one empty held."""
    with fight(model, C) as gb:
        quiet(gb)
        throw(gb, B, 16 + 40 + 12)
        until(gb, lambda: gb.mem("boss_hits") == 1, 30)
        assert gb.mem("boss_hp") == 13 and gb.mem("boss_hold") == 1 and hud(gb) == meter_tiles(13, 14)
        until(gb, lambda: gb.mem("boss_state") == BS_WALK, 60)
        assert gb.mem("boss_x") == 16 and phase(gb) == MP_WALK


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_eighth_drink_flashes_then_splits(model):
    """At meter 6 (the eighth drink): the FLASH, 40 frames (the HAPPY pose blinking with the hover; a glass thrown in it is still
    drunk, no life lost); then the split: variant C's tiles and palettes back, the saucer and its antenna gone, three minis (variant C, hurried,
    walking at x 24) on three different bars, the saucer's bar first, none on his hidden bar; the meter shows 6; push-back 16, the
    spawn interval doubled."""
    with fight(model, C) as gb:
        quiet(gb)
        spawn = gb.mem16("spawn_interval")
        old = gb.mem("boss_bar")
        split_now(gb)
        assert gb.mem("boss_hp") == SPLIT_HP
        poses, clock = set(), Clock(gb)
        throw(gb, old, 16 + 40 + 6)
        while phase(gb) == MP_FLASH:
            frames(gb, 1)
            poses.add(gb.mem("boss_pose") & 15)
            assert clock.now() < MS_FLASH + 12            # (the split's own frame is longer: the LCD off and the reload)
        assert {BP_WALK, BP_HAPPY} <= poses, poses
        assert gb.mem("boss_hits") == 2 and gb.mem("lives") == 3, "the glass thrown in the flash was drunk"
        assert MS_FLASH - 12 <= clock.now() <= MS_FLASH + 10, clock.now()
        frames(gb, 3)
        assert phase(gb) == MP_MINIS and MS.get(gb, "minis") == 3
        dead = MS.get(gb, "dead")
        ms = minis(gb)
        assert len(ms) == 3 and ms[0][1] == old, "the saucer's bar first"
        assert len({m[1] for m in ms}) == 3 and dead not in {m[1] for m in ms} and gb.mem("boss_bar") == dead
        assert all(m[2] == MINI_X and m[3] == WALKING and m[5] == 1 for m in ms)
        assert (gb.mem("boss_hp"), gb.mem("boss_state"), gb.mem("boss_xpose")) == (SPLIT_HP, BS_JUMP, BP_HIDE)
        assert hud(gb) == meter_tiles(6, 14)
        assert gb.mem("pushback_px") == 16 and gb.mem16("spawn_interval") == spawn * 2
        assert topper(gb)["y"] == 0
        top, bottom = rows_of(gb, dead)
        wall = venue("space")["bar_map"]
        assert top[0:5] == wall[0:5] and bottom[0:5] == wall[20:25]
        assert gb.mem("boss_x") == 16
    with to_shift(model, C, 0) as ref:                       # the same group's patrons in an ordinary shift
        ref_tiles = patron_tiles(ref)
        ref_pal = [cgb_palette(ref, 4), cgb_palette(ref, 7, True)] if model == "cgb" else None
    with fight(model, C) as gb:
        quiet(gb)
        to_minis(gb)
        mine = patron_tiles(gb)
        assert mine == ref_tiles, "the group's patron tiles are back (variant C's over the saucer's)"
        if model == "cgb":
            assert [cgb_palette(gb, 4), cgb_palette(gb, 7, True)] == ref_pal, "variant C's own BG 4 and OBJ 7"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_mini_is_served_by_its_second_drink_not_its_first(model):
    """A glass on a mini: drinks 1, pushed 16 px (never served at the left end by it: he drinks there), the meter 5. A second glass
    once he has finished: served out where he stands (LEAVING, counted, score), the meter 4, and he slides off and is gone."""
    with fight(model, C) as gb:
        quiet(gb)
        to_minis(gb)
        p, b, x, st, dr, hu = minis(gb)[1]
        s0 = score(gb)
        throw(gb, b, 80)
        until(gb, lambda: any(m[0] == p and m[4] == 1 for m in minis(gb)), 80)
        frames(gb, 2)
        m = next(m for m in minis(gb) if m[0] == p)
        assert m[3] in (PUSHED, DRINKING) and m[2] >= 17 and MS.get(gb, "minis") == 3
        until(gb, lambda: next(m for m in minis(gb) if m[0] == p)[3] == DRINKING, 80)
        frames(gb, 8)
        assert gb.mem("boss_hp") == 5 and hud(gb) == meter_tiles(5, 14)
        frames(gb, 90)                                       # (he has finished his drink: he catches another)
        x2 = next(m for m in minis(gb) if m[0] == p)[2]
        throw(gb, b, x2 + 24)
        until(gb, lambda: MS.get(gb, "minis") == 2, 80)
        assert next(m for m in minis(gb) if m[0] == p)[3] == LEAVING
        frames(gb, 2)
        assert gb.mem("boss_hp") == 4 and score(gb) > s0
        until(gb, lambda: not any(m[0] == p for m in minis(gb)), 120)
        assert gb.mem("boss_hp") == 4 and len(alive(gb)) == 2


@pytest.mark.parametrize("model", ["cgb"])
def test_a_mini_at_the_tap_costs_a_life_and_the_rest_come_back(model):
    """A mini reaches the tap: a life, and after the freeze the minis still to be served stand at x 24 again on bars that are not
    his hidden one; the one already served stays served."""
    with fight(model, C) as gb:
        quiet(gb)
        to_minis(gb)
        p0 = minis(gb)[0][0]
        with logic_paused(gb):                               # (one served, as by two glasses)
            gb.write(gb.addr("patron_drinks") + p0, 2)
            gb.write(gb.addr("patron_state") + p0, PUSHED)
            gb.write(gb.addr("patron_aux") + p0, 8)
        frames(gb, 3)
        assert MS.get(gb, "minis") == 2
        p1 = next(m for m in alive(gb))[0]
        with logic_paused(gb):                               # (the other walks: he is at the tap)
            gb.write("hurry_speed", 255)
            gb.write("patron_speed", 255)
            gb.write(gb.addr("patron_x") + p1, 118)
        until(gb, lambda: state(gb) == LIFE_LOST, 400)
        until(gb, lambda: state(gb) == PLAYING, 300)
        frames(gb, 3)
        assert gb.mem("lives") == 2 and MS.get(gb, "minis") == 2 and phase(gb) == MP_MINIS
        ms = alive(gb)
        assert len(ms) == 2 and all(m[2] == MINI_X and m[3] == WALKING and m[5] == 1 for m in ms)
        assert MS.get(gb, "dead") not in {m[1] for m in ms} and len({m[1] for m in ms}) == 2
        assert (gb.mem("boss_state"), gb.mem("boss_xpose"), gb.mem("boss_bar")) == (BS_JUMP, BP_HIDE, MS.get(gb, "dead"))
        assert gb.mem("boss_hp") == 4


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_life_lost_in_phase_1_puts_him_home(model):
    """A life lost after a teleport: he is back on bar 1 at x 16 walking, the meter kept, the beam gone."""
    with fight(model, C) as gb:
        quiet(gb)
        to_tell(gb)
        until(gb, lambda: gb.mem("boss_bar") != B, MS_TELL + MS_WAITMAX + MS_GONE + 10)
        gb.write("boss_x", 136 - 40)
        until(gb, lambda: state(gb) == LIFE_LOST, 6)
        until(gb, lambda: state(gb) == PLAYING, 300)
        frames(gb, 3)
        assert (gb.mem("boss_bar"), gb.mem("boss_x"), phase(gb), gb.mem("boss_hp"), gb.mem("lives")) == (B, 16, MP_WALK, 14, 2)
        assert all(marker_at(gb, b) is None for b in range(4))


@pytest.mark.parametrize("model", ["cgb"])
def test_the_minis_are_hurried_and_regulars_still_come(model):
    """The level's real speeds: a mini walks at 1.5x (hurry_speed) while a regular walks at patron_speed; a regular that comes in
    phase 2 is variant A or B, on one of the three bars that are not his hidden bar (the minis' variant never spawns)."""
    with fight(model, C) as gb:
        play(gb)
        to_minis(gb)
        sp, hs = gb.mem("patron_speed"), gb.mem("hurry_speed")
        assert hs == sp + (sp >> 1) and sp > 0
        x0 = {m[0]: m[2] for m in alive(gb)}
        with logic_paused(gb):
            gb.write("spawn_timer", 0)
            gb.write(gb.addr("spawn_timer") + 1, 0)
        frames(gb, 200)
        dead = MS.get(gb, "dead")
        moved = [m[2] - x0[m[0]] for m in alive(gb) if m[0] in x0 and m[3] == WALKING]
        assert moved and all(abs(d - 200 * hs / 256) <= 6 for d in moved), (moved, hs)
        st, var, bar = gb.read("patron_state", 16), gb.read("patron_variant", 16), gb.read("patron_bar", 16)
        regulars = [(var[p], bar[p] & 3) for p in range(16) if st[p] and p not in x0]
        assert regulars and all(v in (0, 1) and b != dead for v, b in regulars), regulars


def bot_target(gb):
    """The bar the bot should pour on now (or None): his bar while he wants a glass and a glass thrown now still reaches him
    before the next tell (a glass thrown in the tell goes past where he was and breaks: the player's risk, the Mascot's too),
    else a mini that is walking."""
    if phase(gb) == MP_WALK:
        if gb.mem("boss_hold") + len(mugs(gb, gb.mem("boss_bar"), FULL)) < R["hands"] and gb.mem16("boss_special_t") >= 70 \
                and gb.mem("boss_hp") > SPLIT_HP:
            return gb.mem("boss_bar")
    elif phase(gb) == MP_MINIS:
        for p, b, x, st, dr, hu in alive(gb):
            if st == WALKING and not mugs(gb, b, FULL):
                return b
    return None


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_win_the_fight_by_pouring(model):
    """Real pours, no hp poke (the regulars stand still and none come): the saucer's eight glasses wherever it teleports, the flash,
    the split, then every mini two glasses and every empty caught; no life lost; the outro (no saucer left to be happy), CHAPTER
    CLEAR, the POST_SPACE scene, the chapter saved."""
    with fight(model, C) as gb:
        quiet(gb)
        to_bar(gb, B)
        f, seen_split = 0, False
        clock = Clock(gb)
        while gb.mem("boss_hp") and f < 9000:
            empties = [m for m in mugs(gb, st=EMPTY) if m[3] >= TAP_X - 40]
            tb = bot_target(gb)
            if empties:
                to_bar(gb, empties[0][2])
                frames(gb, 1)
            elif tb is not None:
                to_bar(gb, tb)
                if gb.mem("bar") == tb and bot_target(gb) == tb:
                    pour(gb)
                else:
                    frames(gb, 1)
            else:
                frames(gb, 1)
            f = clock.now()
        print(f"mothership bot win: {f} frames, hits {gb.mem('boss_hits')}, jumps {MS.get(gb, 'jumps')}, lives {gb.mem('lives')}")
        assert gb.mem("boss_hits") == 8 and MS.get(gb, "minis") == 0 and gb.mem("lives") == 3
        frames(gb, 2)
        assert state(gb) == GS_STORY and gb.mem("story_phase") == SP_OUTRO and gb.mem("boss_state") == BS_OUTRO
        gb.run(60)
        assert topper(gb)["y"] == 0 and gb.mem("boss_xpose") == BP_HIDE
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 120)
        gb.run(3)
        assert banner_text(gb, 1) == centred("CHAPTER CLEAR")
        run_until(gb, lambda: state(gb) == GS_STORY and gb.mem("story_scene") == post(C), 300)
        settle(gb)
        assert (gb.mem("boss_on"), gb.mem("story_progress")) == (0, C + 1)
