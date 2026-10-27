# docs/minigames_bosses.md 3.10: the Mothership, the space lounge's boss (src/boss_mothership.c; art approved 2026-10-11: look A
# "silver saucer"). Phase 1: the saucer (row 40 px, step 100, push 8, gulp 24, hands 2, sip 45, meter 14 = 8 + 6): every 300
# frames of walking a 60-frame TELL (the beam on a random other bar, the antenna blinking), the wait for the earlier glasses,
# 10 frames gone, then he is on that bar at x 16 / 32 / 48. Phase 2, at meter 6: a 40-frame FLASH, then the split (the group's
# patron tiles over the saucer's, the LCD off for a frame) into three hurried mini aliens on three bars, two drinks each, served
# out wherever they stand; the saucer's hidden bar is the one without a mini. Every frame here is checked at <= 10 sprites a line.
import re

import pytest
from boss_common import (BP_HAPPY, BP_WALK, BS_ENTER, BS_JUMP, BS_OUTRO, BS_TELL, BS_WALK, Clock, EMPTY, FULL, OAM_TOPPER, OBJ_TOPPER, Own,
                         SP_FAIL, SP_OUTRO, TAP_X, art, assert_body, bar_row, check_start, fight, frames, hud, meter_tiles, mugs,
                         play, pose_cols, pour, row, still_regulars, throw, to_bar, until)
from conftest import clear_regulars, ROOT, check_golden, logic_paused, venue
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
PATRON_BASE, PATRON_TILES = 78, 152     # the group's patron tiles (BG 78-229): build/art.h PATRON_FIRST_TILE, PATRON_GROUP_TILES
LAND_X = (16, 32, 48)


def phase(gb):
    return MS.get(gb, "phase")


def quiet(gb, calm=3):
    """The regulars stand still and none come; calm 3: no passengers and no ray (the tests of the older mechanics); the entrance over."""
    still_regulars(gb)
    until(gb, lambda: MS.get(gb, "ent") == 0 and gb.mem("intro_timer") == 0 and state(gb) == PLAYING, 400)
    MS.put(gb, "calm", calm)
    if not gb.mem("patrons_live"):                   # (an empty screen calls the next regular soon, patrons.c pat_refill: the bars start empty now, so a sentinel stands in)
        wipe(gb)
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
        width=40, x=16, bar=1, step=100, push=8, gulp=34, hands=2, sip=45, meter=14, hat=12)
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
        assert gb.mem("boss_id") == C
    with fight(model, C) as gb:
        until(gb, lambda: MS.get(gb, "ent") == 0 and gb.mem("intro_timer") < 89, 200)      # (the entrance first: its own tests below)
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
        frames(gb, 3)                                # (the bar is recomposed over a few frames)
        with logic_paused(gb):                       # (a held empty may leave any frame: hold and the picture from one instant)
            hold = gb.mem("boss_hold")
            top, bottom = rows_of(gb, tb)
        assert marker_at(gb, tb) is None and hold >= 1 and gb.mem("boss_hp") == 14, "his hands went with him"
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
        frames(gb, 9)                                         # (his bar's rows reach the screen through the VBlank queue: a few frames)
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
    with fight(model, C, entrance=True) as gb:
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
        clear_regulars(gb)
        frames(gb, 3)
        assert state(gb) == GS_STORY and gb.mem("story_phase") == SP_OUTRO and gb.mem("boss_state") == BS_OUTRO
        gb.run(60)
        assert topper(gb)["y"] == 0 and gb.mem("boss_xpose") == BP_HIDE
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 120)
        gb.run(3)
        assert banner_text(gb, 1) == centred("CHAPTER CLEAR")
        run_until(gb, lambda: state(gb) == GS_STORY and gb.mem("story_scene") == post(C), 300)
        settle(gb)
        assert (gb.mem("boss_on"), gb.mem("story_progress")) == (0, C + 1)


# ---- E7: passengers, the stun ray, the entrance (owner 2026-10-15) -------------------------------------------------------------------
CALM_RAY, CALM_DROP = 1, 2
RY_IDLE, RY_CHARGE, RY_STUN = range(3)
RAY_STAY, RAY_CHARGE, RAY_STUN, RAY_BEAM, ENT_LAND, ENT_BLINK, LIVE_MAX = (int(re.search(rf"#define {n}\s+(\d+)", SRC).group(1)) for n in (
    "RAY_STAY", "RAY_CHARGE", "RAY_STUN", "RAY_BEAM", "ENT_LAND", "ENT_BLINK", "LIVE_MAX"))
SFX_COIN, SFX_LAUNCH, SFX_FILL, SFX_SHAKE, SFX_REV, SFX_KA, SFX_WHOOSH = 6, 2, 1, 8, 12, 11, 13
BT_IDLE, BT_FAIL = 0, 6


def sfx(gb, n):
    return gb.read("sfx_count", 14)[n]


def live(gb):
    """[(slot, bar, x, state, variant)] of every patron on the screen (a quiet fight: only the passengers)."""
    st, bar, x, var = gb.read("patron_state", 16), gb.read("patron_bar", 16), gb.read("patron_x", 16), gb.read("patron_variant", 16)
    return [(p, bar[p] & 3, x[p], st[p], var[p]) for p in range(15) if st[p]]       # (slot 15: wipe's sentinel)


def wipe(gb, sentinel=True):
    """Every patron off the screen, except a sentinel in slot 15 (bar 0, x 100, standing: on an empty screen the game calls the next
    regular soon, and the tests want none)."""
    with logic_paused(gb):
        for p in range(16):
            gb.write(gb.addr("patron_state") + p, 0)
        if sentinel:
            gb.write(gb.addr("patron_state") + 15, WALKING)
            gb.write(gb.addr("patron_bar") + 15, 0)
            gb.write(gb.addr("patron_x") + 15, 100)
            gb.write("patrons_live", 1)                  # (the count the next frame's refill rule reads: still the old one until update_patrons runs)
        gb.write("lists_dirty", 1)


def bare(gb, calm):
    """quiet() and the fight's start patrons gone: only what the test adds is on the screen."""
    quiet(gb, calm)
    wipe(gb)
    frames(gb, 2)


def serve(gb, slot, limit=6):
    """Glasses thrown on passenger `slot`'s bar one at a time until he is LEAVING / gone (returns how many it took)."""
    n = 0
    while n < limit:
        q = [m for m in live(gb) if m[0] == slot and m[3] != LEAVING]
        if not q:
            return n
        p, b, x, st, v = q[0]
        if st == WALKING and not mugs(gb, b, FULL):
            throw(gb, b, x + 24)
            n += 1
        frames(gb, 25)
    raise AssertionError("not served")


def land_now(gb):
    """The test hook's tell through to the landing: returns on the frame after he is on the new bar."""
    n = MS.get(gb, "jumps")
    to_tell(gb)
    until(gb, lambda: MS.get(gb, "jumps") == n + 1, MS_TELL + MS_WAITMAX + MS_GONE + 20)
    frames(gb, 1)


def arm_ray(gb, stay=RAY_STAY - 1):
    """Ray on, passengers off, the bartender's count one frame short of taking aim."""
    MS.put(gb, "calm", CALM_DROP)
    with logic_paused(gb):
        MS.put(gb, "stay", stay)
        MS.put(gb, "sbar", gb.mem("bar"))


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_every_teleport_drops_two_passengers(model):
    """Each landing releases two alien passengers (variant A / B patrons) at x 24 on two different bars that are not his new bar, with a
    chirp; none before the first landing; two more at the next landing."""
    with fight(model, C) as gb:
        bare(gb, CALM_RAY)
        assert live(gb) == [] and MS.get(gb, "drops") == 0
        coin = sfx(gb, SFX_COIN)
        land_now(gb)
        ps = live(gb)
        assert len(ps) == 2 and MS.get(gb, "drops") == 2 and sfx(gb, SFX_COIN) == coin + 1
        assert len({p[1] for p in ps}) == 2 and all(p[1] != gb.mem("boss_bar") for p in ps), ps
        assert all(p[2] in (24, 25) and p[3] == WALKING and p[4] in (0, 1) for p in ps), ps
        wipe(gb)
        land_now(gb)
        assert len(live(gb)) == 2 and MS.get(gb, "drops") == 4


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_passengers_keep_to_the_cap_and_clear_entries(model):
    """No passenger while LIVE_MAX patrons are on the screen; a bar whose entry has a patron at x < 40 gets none (the other bars do)."""
    with fight(model, C) as gb:
        bare(gb, CALM_RAY)
        with logic_paused(gb):
            for p in range(LIVE_MAX):                           # twelve walkers well along the bars (the cap is a count)
                gb.write(gb.addr("patron_state") + p, WALKING)
                gb.write(gb.addr("patron_bar") + p, [0, 2, 3][p % 3])
                gb.write(gb.addr("patron_x") + p, 100 + p)
            gb.write("lists_dirty", 1)
        land_now(gb)
        assert len(live(gb)) == LIVE_MAX and MS.get(gb, "drops") == 0, "the cap"
        n = 0
        for _ in range(8):                                      # the sentinel at the entry of bar 0: in every run its bar gets nobody
            wipe(gb)
            with logic_paused(gb):
                gb.write(gb.addr("patron_x") + 15, 30)
                gb.write("lists_dirty", 1)
            land_now(gb)
            new = live(gb)
            assert all(p[1] != 0 for p in new), "bar 0's entry was crowded"
            n += len(new)
        assert n >= 8


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_passenger_is_served_like_a_patron(model):
    """A glass thrown on a passenger's bar is caught by him, he lands near the left end, where one glass is enough (Option C: a push that
    reaches the left-edge stop serves him: he slides off without drinking); no life is lost."""
    with fight(model, C) as gb:
        bare(gb, CALM_RAY)
        land_now(gb)
        p, b, x, st, v = live(gb)[0]
        assert serve(gb, p) == 1
        assert all(m[0] != p or m[3] == LEAVING for m in live(gb)) and gb.mem("lives") == 3


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_passengers_count_for_clear_the_bar(model):
    """The meter at 0 with passengers aboard: the banner says CLEAR THE BAR and the fight goes on until both are served (one
    glass each), then the outro."""
    with fight(model, C) as gb:
        bare(gb, CALM_RAY)
        land_now(gb)
        assert len(live(gb)) == 2
        gb.write("boss_hook", 3)
        frames(gb, 3)
        assert gb.mem("boss_hp") == 0 and banner_text(gb, 0) == centred("CLEAR THE BAR")
        frames(gb, 120)
        assert state(gb) == PLAYING and gb.mem("story_phase") != SP_OUTRO and len(live(gb)) == 2
        for p, b, x, st, v in live(gb):
            serve(gb, p)
        until(gb, lambda: not any(q[3] != LEAVING for q in live(gb)), 600)
        wipe(gb, False)                                         # (the sentinel goes: the last patron to leave ends the fight)
        until(gb, lambda: state(gb) == GS_STORY and gb.mem("story_phase") == SP_OUTRO, 600)
        assert gb.mem("lives") == 3


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_split_takes_the_passengers_with_it(model):
    """The split clears the screen: the passengers are gone and the three minis are all there is."""
    with fight(model, C) as gb:
        bare(gb, CALM_RAY)
        land_now(gb)
        assert len(live(gb)) == 2
        split_now(gb)
        until(gb, lambda: phase(gb) == MP_MINIS, MS_FLASH + 30)
        frames(gb, 3)
        assert len(live(gb)) == 3 and all(p[4] == 2 for p in live(gb))


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_ray_takes_aim_after_a_long_stay_with_a_telegraph(model):
    """Standing on one bar RAY_STAY frames: the charge begins (SFX_REV), the ship glows (HAPPY), the antenna blinks, the beam column
    blinks on HIS bar under his feet (not the ship's); the bartender is free. Golden boss_mothership_charge."""
    with fight(model, C) as gb:
        bare(gb, CALM_DROP)
        to_bar(gb, 3)
        MS.put(gb, "stay", 0)
        clock = Clock(gb)
        until(gb, lambda: clock.now() >= 0 and MS.get(gb, "ray") == RY_CHARGE, RAY_STAY + 20)
        assert RAY_STAY - 4 <= clock.now() <= RAY_STAY + 4, clock.now()
        assert sfx(gb, SFX_REV) >= 1
        seen, tiles, golden = set(), set(), False
        for _ in range(RAY_CHARGE - 14):
            frames(gb, 1)
            assert MS.get(gb, "ray") == RY_CHARGE and gb.mem("boss_xpose") == BP_HAPPY
            seen.add(marker_at(gb, 3))
            assert marker_at(gb, B) is None
            tiles.add(topper(gb)["tile"])
            if MS.get(gb, "rt") == 5 and not golden:
                check_golden(gb, "boss_mothership_charge")
                golden = True
        col = (gb.mem("bartender_x") + 4) >> 3
        assert seen == {None, col} and tiles == {HAT_STILL, HAT_BOB}, (seen, col, tiles)
        gb.press("left", 4)                                     # the bartender walks as ever during the charge
        frames(gb, 2)
        assert gb.mem("bartender_x") < TAP_X and MS.get(gb, "stuns") == 0 and MS.get(gb, "ray") == RY_CHARGE


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_dodging_the_ray_by_changing_bars(model):
    """Any bar change in the charge cancels it: no stun, the beam and the glow gone, the count from 0 on the new bar; and the ship
    does not charge again until RAY_STAY frames there."""
    with fight(model, C) as gb:
        bare(gb, CALM_DROP)
        to_bar(gb, 3)
        arm_ray(gb)
        until(gb, lambda: MS.get(gb, "ray") == RY_CHARGE, 4)
        frames(gb, RAY_CHARGE - 5)
        to_bar(gb, 2)
        frames(gb, 2)
        assert MS.get(gb, "ray") == RY_IDLE and MS.get(gb, "stay") < 10 and gb.mem("boss_xpose") == 0
        assert all(marker_at(gb, b) is None for b in range(4))
        frames(gb, 120)
        assert MS.get(gb, "stuns") == 0 and MS.get(gb, "ray") == RY_IDLE and gb.mem("bartender_frame") != BT_FAIL
        gb.press("up", 2)                                       # free to move
        frames(gb, 2)
        assert gb.mem("bar") == 1


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_bartender_who_stays_is_stunned(model):
    """The beam fires at the end of the charge (SFX_KA, the GULP pose, the beam solid RAY_BEAM frames): the bartender is stunned
    RAY_STUN frames (BT_FAIL): Left / Right / Up / Down / A do nothing (no bar change, no walking, no pour), a mug on another bar keeps
    sliding; after it he is free and the count starts at 0. Golden boss_mothership_stun."""
    with fight(model, C) as gb:
        bare(gb, CALM_DROP)
        to_bar(gb, 3)
        arm_ray(gb)
        zaps = sfx(gb, SFX_KA)
        until(gb, lambda: MS.get(gb, "ray") == RY_STUN, RAY_CHARGE + 10)
        frames(gb, 1)
        assert sfx(gb, SFX_KA) == zaps + 1 and MS.get(gb, "stuns") == 1 and gb.mem("boss_xpose") == 2 and marker_at(gb, 3) is not None
        hits = gb.mem("boss_hits")
        check_golden(gb, "boss_mothership_stun")                # (the beam solid, the hatch open, the bartender's hands up)
        throw(gb, B, 100)                                       # (the pause that places it gives the keys' edge back: one frame on, then the baseline)
        frames(gb, 1)
        x0, launches, fills, whooshes = gb.mem("bartender_x"), sfx(gb, SFX_LAUNCH), sfx(gb, SFX_FILL), sfx(gb, SFX_WHOOSH)
        k = 0
        while MS.get(gb, "rt") < RAY_STUN - 14:
            gb.press("up" if k % 4 == 0 else "down" if k % 4 == 1 else "left" if k % 4 == 2 else "a", 1)
            frames(gb, 1)
            k += 1
            assert MS.get(gb, "ray") == RY_STUN
        assert k >= 10
        with logic_paused(gb):                                  # (a read between frames: the game's own frame is done)
            assert gb.mem("bar") == 3 and gb.mem("bartender_x") == x0 and gb.mem("fill_timer") == 0
        assert sfx(gb, SFX_LAUNCH) == launches and sfx(gb, SFX_FILL) == fills and sfx(gb, SFX_WHOOSH) == whooshes, "no bar change, no pour"
        assert marker_at(gb, 3) is None, "the beam is gone after RAY_BEAM frames"
        assert gb.mem("boss_hits") == hits + 1 and gb.mem("lives") == 3, "the glass kept sliding to him"
        until(gb, lambda: MS.get(gb, "ray") == RY_IDLE, 20)
        assert MS.get(gb, "stay") < 6
        frames(gb, 2)
        gb.press("up", 2)
        frames(gb, 2)
        assert gb.mem("bar") == 2 and gb.mem("bartender_frame") != BT_FAIL


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_stun_is_the_stun_length_stops_a_pour_and_holds_the_tell(model):
    """A pour in progress when the beam fires is cancelled (no glass); the stun is RAY_STUN frames from the beam; the teleport clock
    does not run during the ray."""
    with fight(model, C) as gb:
        bare(gb, CALM_DROP)
        to_bar(gb, 2)
        arm_ray(gb)
        t0 = gb.mem16("boss_special_t")
        gb.hold("a")
        frames(gb, 3)
        assert gb.mem("fill_timer") > 0
        until(gb, lambda: MS.get(gb, "ray") == RY_STUN, RAY_CHARGE + 10)
        gb.release("a")
        launches = sfx(gb, SFX_LAUNCH)
        t1 = gb.mem16("boss_special_t")
        assert t0 - t1 <= 6, "the teleport clock waited through the charge"
        n = 0
        while MS.get(gb, "ray") == RY_STUN:
            frames(gb, 1)
            n += 1
        assert RAY_STUN - 2 <= n <= RAY_STUN + 2, n
        assert sfx(gb, SFX_LAUNCH) == launches and gb.mem16("boss_special_t") >= t1 - 3 and phase(gb) == MP_WALK


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_life_lost_in_the_ray_clears_it(model):
    """A life lost in the stun: the ray is over (idle, no beam), the bartender is free after the freeze."""
    with fight(model, C) as gb:
        bare(gb, CALM_DROP)
        to_bar(gb, 3)
        arm_ray(gb)
        until(gb, lambda: MS.get(gb, "ray") == RY_STUN, RAY_CHARGE + 10)
        frames(gb, 10)
        with logic_paused(gb):
            gb.write("boss_x", 150)                             # at the tap: a life
        until(gb, lambda: state(gb) == LIFE_LOST, 10)
        until(gb, lambda: state(gb) == PLAYING, 200)
        frames(gb, 30)
        assert MS.get(gb, "ray") == RY_IDLE and all(marker_at(gb, b) is None for b in range(4)) and gb.mem("lives") == 2
        gb.press("down", 2)
        frames(gb, 2)
        assert gb.mem("bar") == 1


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_no_ray_in_phase_2_and_the_flash_ends_a_charge(model):
    """The flash (the meter at the split) ends a charge at once; the minis' phase has no ray."""
    with fight(model, C) as gb:
        bare(gb, CALM_DROP)
        to_bar(gb, 3)
        arm_ray(gb)
        until(gb, lambda: MS.get(gb, "ray") == RY_CHARGE, 4)
        frames(gb, 20)
        split_now(gb)
        frames(gb, 2)
        assert MS.get(gb, "ray") == RY_IDLE and all(marker_at(gb, b) is None for b in range(4))
        until(gb, lambda: phase(gb) == MP_MINIS, MS_FLASH + 30)
        with logic_paused(gb):
            MS.put(gb, "stay", RAY_STAY + 50)
        frames(gb, 30)
        assert MS.get(gb, "ray") == RY_IDLE and MS.get(gb, "stuns") == 0


def ent_frame(gb):
    return MS.get(gb, "ent") - 1


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_entrance_tractor_beam(model):
    """The first start: he is not on his bar (JUMP, HIDE), the beam column stands on his bar at his start x, the lights flicker (DMG BGP
    dimmed on some frames, CGB the bar palette halved on some), the hum, then he blinks in (HAPPY / hidden) and lands at ENT_LAND: WALK
    at x 16 on his bar, the beam and the dim gone, the thud, the intro's 90 frames from there. The bartender cannot move meanwhile.
    Every frame is checked at <= 10 sprites a line. Goldens boss_mothership_beam (frame 30), boss_mothership_materialise (frame 54)."""
    with fight(model, C, entrance=True) as gb:
        assert MS.get(gb, "ent") >= 1 and gb.mem("boss_state") == BS_ENTER and gb.mem("boss_xpose") == BP_HIDE
        revs, bar0, x0, shakes = sfx(gb, SFX_REV), gb.mem("bar"), gb.mem("bartender_x"), sfx(gb, SFX_SHAKE)
        dims, golden = set(), 0
        wall = cgb_palette(gb, 0) if model == "cgb" else None
        while True:
            frames(gb, 1)
            f = ent_frame(gb)
            if f < 0 or f >= ENT_LAND:
                break
            assert gb.mem("intro_timer") >= 86 and gb.mem("boss_state") == BS_ENTER
            if f < ENT_BLINK - 2:
                assert marker_at(gb, B) == R["x"] // 8 + 2, f
            elif f > ENT_BLINK + 4:
                assert marker_at(gb, B) is None, "the beam fades as he blinks in"
            dims.add(gb.mem(0xFF47) if model == "dmg" else tuple(cgb_palette(gb, 0)))
            if f % 3 == 0:
                gb.press("down" if f % 2 else "left", 1)
            assert gb.mem("bar") == bar0 and gb.mem("bartender_x") == x0, f
            if f >= 30 and golden == 0:
                check_golden(gb, "boss_mothership_beam")
                golden = 1
            if f >= 54 and golden == 1:
                check_golden(gb, "boss_mothership_materialise")
                golden = 2
        assert golden == 2 and sfx(gb, SFX_REV) == revs + 1 and len(dims) == 2, dims
        frames(gb, 3)
        assert MS.get(gb, "ent") == 0 and gb.mem("boss_state") == BS_WALK and gb.mem("boss_x") == R["x"] and sfx(gb, SFX_SHAKE) >= shakes + 1
        assert all(marker_at(gb, b) is None for b in range(4)) and 84 <= gb.mem("intro_timer") <= 89
        assert (gb.mem(0xFF47) == 0xE4) if model == "dmg" else cgb_palette(gb, 0) == wall
        assert_body(gb, C, A, R["x"], BP_WALK)
        gb.press("down", 2)                                     # the intro's 90 frames: the bartender is his own again at once
        frames(gb, 2)
        assert gb.mem("bar") == bar0 + 1
        play(gb)
        assert gb.mem("boss_hp") == 14


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_entrance_lights_change_between_frames(model):
    """The flickering lights (palette writes) land in VBlank, never mid-frame: every rendered frame of the entrance is lit uniformly. DMG: the
    HUD's top rows and the bar band below are dimmed together or not at all (a write at some scanline would tear a frame: the HUD one way,
    the rest the other, which also depended on how fast the build is); CGB: the wall of the four bars shares one colour in every frame.
    So the entrance shows exactly two looks, lit and dim."""
    with fight(model, C, entrance=True) as gb:
        looks = set()
        while ent_frame(gb) >= 0 and ent_frame(gb) < ENT_LAND:
            gb.run(1, render=True)
            im = gb.pb.screen.image.convert("L")
            px = im.load()
            if model == "dmg":
                look = (max(px[x, y] for x in range(160) for y in range(0, 7)), max(px[x, y] for x in range(160) for y in range(8, 15)),
                        max(px[x, y] for x in range(160) for y in range(137, 144)))
            else:
                look = tuple(px[1, y] for y in (48, 72, 100, 126))
                assert len(set(look)) == 1, ("a frame torn between two lights", look)
            looks.add(look)
        assert len(looks) == 2, looks


@pytest.mark.parametrize("model", ["cgb"])
def test_no_entrance_after_a_lost_life(model):
    """A life lost in the fight: he comes back at his start at once (no entrance again)."""
    with fight(model, C, entrance=True) as gb:
        bare(gb, CALM_RAY | CALM_DROP)
        with logic_paused(gb):
            gb.write("boss_x", 150)
        until(gb, lambda: state(gb) == LIFE_LOST, 10)
        until(gb, lambda: state(gb) == PLAYING, 200)
        frames(gb, 2)
        assert MS.get(gb, "ent") == 0 and gb.mem("boss_state") == BS_WALK and gb.mem("boss_x") == R["x"]


def need(gb):
    """{bar: urgency} of what each bar needs now (a bot's eyes): an empty about to be missed first (1000 + its x), then the walking patron
    nearest the tap (one with a glass already on its way is skipped), then the saucer when he has a hand free and wants a glass.
    The second dict: the bars with something to pour on."""
    u, pour_on = {}, set()
    st, bar, x = gb.read("patron_state", 16), gb.read("patron_bar", 16), gb.read("patron_x", 16)
    flying = {b: mugs(gb, b, FULL) for b in range(4)}
    for p in range(16):
        if st[p] == WALKING and not any(m[3] > x[p] for m in flying[bar[p] & 3]):
            u[bar[p] & 3] = max(u.get(bar[p] & 3, 0), x[p])
            pour_on.add(bar[p] & 3)
    bb = gb.mem("boss_bar")
    if phase(gb) == MP_WALK and gb.mem("boss_hold") + len(flying[bb]) < R["hands"] and gb.mem("boss_hp") > SPLIT_HP:
        u[bb] = max(u.get(bb, 0), 70)
        pour_on.add(bb)
    for m in mugs(gb, st=EMPTY):
        if m[3] >= TAP_X - 60:
            u[m[2]] = 1000 + m[3]
    return u, pour_on


def go_bar(gb, b):
    """to_bar, unless the keys do nothing now (a stun began meanwhile, a life was lost): the bot stands a frame."""
    try:
        to_bar(gb, b)
    except AssertionError:
        frames(gb, 1)


def bot_step(gb, lag):
    """One decision of a player who looks every `lag` frames: dodge a charge, catch an empty, serve the patron nearest the tap."""
    if lag:
        frames(gb, lag)
    ray = MS.get(gb, "ray")
    if ray == RY_STUN or state(gb) != PLAYING:
        frames(gb, 1)
        return
    (u, pour_on), cur = need(gb), gb.mem("bar")
    if ray == RY_CHARGE:
        other = {b: v for b, v in u.items() if b != cur}
        go_bar(gb, max(other, key=other.get) if other else (cur + 1) % 4)
        frames(gb, 1)
        return
    if not u:
        frames(gb, 1)
        return
    tgt = max(u, key=u.get)
    go_bar(gb, tgt)
    if gb.mem("bar") != tgt or tgt not in pour_on:                  # (standing at the tap catches the empties that come)
        frames(gb, 1)
        return
    try:
        pour(gb)
    except AssertionError:                                      # (stunned mid-pour)
        gb.release("a")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_win_the_real_fight_with_passengers_and_the_ray(model):
    """The fight as a player meets it (the level's real speeds, regulars coming, passengers at every landing, the ray on): a bot that looks
    every 6 frames, serves what is nearest the tap, catches the empties and dodges a charge brings the meter to 0: the saucer's eight
    glasses, the split, the minis' twelve. (A patron pushed to the door needs a glass timed to the frame he turns, which the bot does not
    try: the rest of the bar is cleared by hand, as test_boss.py does.) At most two lives are lost to the odd missed patron or empty;
    the outro follows."""
    with fight(model, C, entrance=True) as gb:
        until(gb, lambda: MS.get(gb, "ent") == 0 and gb.mem("intro_timer") == 0 and state(gb) == PLAYING, 400)
        clock, f, lost_at, peak = Clock(gb), 0, [], 0
        while gb.mem("boss_hp") and f < 9000 and gb.mem("lives"):
            if state(gb) == LIFE_LOST:
                lost_at.append(f)
                until(gb, lambda: state(gb) != LIFE_LOST, 400)
                continue
            bot_step(gb, 6)
            peak = max(peak, len(live(gb)))
            f = clock.now()
        print(f"mothership real fight bot: {f} frames, lives {gb.mem('lives')}, stuns {MS.get(gb, 'stuns')}, passengers {MS.get(gb, 'drops')}, "
              f"landings {MS.get(gb, 'jumps')}, peak patrons {peak}, lives lost at {lost_at}")
        assert gb.mem("boss_hp") == 0 and gb.mem("lives") >= 1 and MS.get(gb, "minis") == 0
        assert MS.get(gb, "drops") >= 1 and MS.get(gb, "jumps") >= 1 and peak <= LIVE_MAX + 3
        clear_regulars(gb)
        until(gb, lambda: state(gb) == GS_STORY and gb.mem("story_phase") == SP_OUTRO, 30)
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 160)
