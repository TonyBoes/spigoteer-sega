# docs/minigames_bosses.md 3.4: the Mascot, the stadium's boss (src/boss_mascot.c; art approved 2026-10-11: the red foam bull
# "Stampede"). The fight follows the stadium's Last call: his row (32 px, step 100, push 8, gulp 24, hands 2, sip 45,
# meter 10) and his leap every 300 frames of walking: the tell (60 frames: the CROUCH pose, the crown one row lower, the
# dust marker on a random other bar at 16 / 32 / 48), the wait for every earlier mug on his bar, the air (20 frames: two
# dust puffs where he stood, no topper), the landing (his body on the target bar, its regulars scared off without a
# score, spawning kept off that bar). Every frame here is checked at <= 10 sprites a line.
import re

import pytest
from boss_common import (BP_HAPPY, BP_WALK, BS_JUMP, BS_OUTRO, BS_TELL, BS_WALK, Clock, EMPTY, FULL, OAM_TOPPER,
                         OBJ_TOPPER, Own, SP_FAIL, SP_OUTRO, art, assert_body, bar_row, check_start, fight, frames, hud,
                         meter_tiles, mugs, play, pose_cols, pour, row, still_regulars, throw, to_bar, until)
from conftest import clear_regulars, ROOT, check_golden, logic_paused, venue
from test_flow import GS_STORY, LEVEL_CLEAR, LIFE_LOST, PLAYING, run_until, set_patron, score, state, tilemap_row
from test_story import banner_text, centred, post, settle, to_goal

pytestmark = pytest.mark.timeout(300)

C = 1                                   # the stadium
R = row(C)
A = art("mascot")
B = R["bar"]
BP_CROUCH, BP_PUFF1, BP_PUFF2 = 5, 6, 7
SRC = (ROOT / "src" / "boss_mascot.c").read_text()
EVERY, TELL, WAITMAX, AIR = (int(re.search(rf"#define {n}\s+(\d+)", SRC).group(1)) for n in (
    "MASCOT_EVERY", "MASCOT_TELL", "MASCOT_WAITMAX", "MASCOT_AIR"))
MP_WALK, MP_TELL, MP_WAIT, MP_AIR = range(4)
M = Own("mascot")
MARK = 248
LEAVING = 4
WALL = venue("sports")["bar_map"]


def phase(gb):
    return M.get(gb, "phase")


def quiet(gb):
    still_regulars(gb)
    play(gb)


def rows_of(gb, bar):
    y = 5 + 3 * bar
    return tilemap_row(gb, y, 0, 20), tilemap_row(gb, y + 1, 0, 20)


def marker_at(gb, bar):
    """The columns of the marker on `bar` (its two column pairs from BG 248), or None."""
    top, bottom = rows_of(gb, bar)
    hits = [k for k in range(19) if (bottom[k], bottom[k + 1], top[k], top[k + 1]) == (MARK + 1, MARK + 3, MARK, MARK + 2)]
    return hits[0] if hits else None


def to_tell(gb):
    """The tell, started by the test hook, two frames in."""
    gb.write("boss_hook", 1)
    until(gb, lambda: phase(gb) == MP_TELL, 4)
    frames(gb, 2)


def no_spawns(gb):
    gb.write("spawn_timer", 0xFF)
    gb.write(gb.addr("spawn_timer") + 1, 0x7F)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_his_row_and_art(model):
    """Spec 3.2 / 3.4's numbers and timings, the banner lines of spec 7, his approved art (the red bull) with CROUCH,
    PUFF1 and PUFF2 (extra poses 5-7), the marker (4 BG tiles) and the crown as the topper; no WRAM of his own."""
    assert {k: R[k] for k in ("width", "x", "bar", "step", "push", "gulp", "hands", "sip", "meter", "hat")} == dict(
        width=32, x=16, bar=1, step=100, push=8, gulp=24, hands=2, sip=45, meter=10, hat=8)
    assert (R["line1"], R["line2"]) == ("THE MASCOT JUMPS", "FOLLOW HIM 10 MUGS")
    assert A["poses"] == ["WALK", "STOMP", "GULP", "WINCE", "HAPPY", "CROUCH", "PUFF1", "PUFF2"]
    assert (EVERY, TELL, AIR) == (300, 60, 20) and WAITMAX >= 44
    assert len(A["pairs"]) <= 30 and len(A["fx"]) == 64
    assert "; Art: approved design" in (ROOT / "assets/art/boss/mascot.txt").read_text()
    assert not (ROOT / "assets/art/approved/boss_mascot.txt").exists()
    assert "boss_mascot" not in (ROOT / "assets/art/approved/README.md").read_text()
    assert not re.search(r"^(?:static\s+)?u?int(?:8|16)_t\s+\w+\s*(?:[;,=]|\[)", SRC, re.M), "no WRAM of his own"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_fight_follows_the_last_call(model):
    """After the stadium's Last call: BOSS and his lines; the Mascot on bar 1 at x 16 (his tiles, palettes, the marker's
    tiles at BG 248-251), the meter of 10, the tuft as the topper. Golden boss_mascot: walking, a mug on its way."""
    with fight(model, C, banner=True) as gb:
        assert banner_text(gb, 2) == centred(R["line1"]) and banner_text(gb, 3) == centred(R["line2"])
        to_goal(gb)
        gb.run(2)
        check_start(gb, C, A, model)
        assert bytes(gb.read(0x8000 + MARK * 16, 64)) == bytes(A["fx"])
        assert hud(gb) == meter_tiles(10, 10)
        assert (phase(gb), gb.mem16("boss_special_t")) == (MP_WALK, EVERY)
        assert all(marker_at(gb, b) is None for b in range(4))
        quiet(gb)
        throw(gb, B, 100)
        frames(gb, 10)
        check_golden(gb, "boss_mascot")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_leap_tell_air_and_landing(model):
    """300 walking frames, then the tell: the CROUCH pose with the crown one row down and the marker on the target bar at
    its landing columns (16 / 32 / 48), he stands; after the 60 frames the air: the puffs where he stood, no topper, no
    catch; after 20 frames he is on the target bar at the landing x, the marker gone, the old bar's wall back, the next
    leap 300 frames away. Golden boss_mascot_crouch (the tell)."""
    with fight(model, C) as gb:
        quiet(gb)
        no_spawns(gb)
        clock = Clock(gb)
        until(gb, lambda: clock.now() and phase(gb) == MP_TELL, EVERY + 10)
        t_tell = clock.now()
        assert EVERY - 2 <= t_tell <= EVERY + 2, t_tell
        frames(gb, 2)
        x, tb, land = gb.mem("boss_x"), M.get(gb, "target"), M.get(gb, "land")
        assert tb != B and land in (16, 32, 48)
        assert gb.mem("boss_state") == BS_TELL
        assert_body(gb, C, A, x, BP_CROUCH)
        assert marker_at(gb, tb) == land // 8, "the marker on the target bar"
        o = gb.oam()[OAM_TOPPER]
        assert o["tile"] == OBJ_TOPPER + 2 and o["y"] == bar_row(R) * 8 + 8, "the crown one row down"
        check_golden(gb, "boss_mascot_crouch")
        until(gb, lambda: phase(gb) == MP_AIR, TELL + WAITMAX)
        t_air = clock.now()
        assert TELL - 2 <= t_air - t_tell <= TELL + 4 and gb.mem("boss_x") == x, "he stands through the tell"
        frames(gb, 2)
        assert gb.mem("boss_state") == BS_JUMP and gb.oam()[OAM_TOPPER]["y"] == 0, "no topper in the air"
        assert_body(gb, C, A, x, BP_PUFF1)
        assert marker_at(gb, tb) == land // 8
        frames(gb, AIR // 2)
        assert_body(gb, C, A, x, BP_PUFF2)
        until(gb, lambda: gb.mem("boss_bar") == tb, AIR + 4)
        assert AIR - 2 <= clock.now() - t_air <= AIR + 4
        frames(gb, 2)
        assert (gb.mem("boss_bar"), gb.mem("boss_x"), gb.mem("boss_state")) == (tb, land, BS_WALK)
        until(gb, lambda: marker_at(gb, tb) is None, 12)
        frames(gb, 6)
        top, bottom = rows_of(gb, tb)
        cols = pose_cols(A, BP_WALK)
        k = land // 8
        assert top[k:k + 4] == cols and bottom[k:k + 4] == [t + 1 for t in cols], "his body on the target bar"
        old_top, old_bottom = rows_of(gb, B)
        assert old_top == WALL[0:20] and old_bottom == WALL[20:40], "the old bar's wall is back"
        assert EVERY - 30 <= gb.mem16("boss_special_t") <= EVERY
        assert M.get(gb, "leaps") == 1 and gb.mem("lives") == 3


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_landing_scares_regulars_without_score_and_spawns_stay_off(model):
    """Two regulars on the target bar during the tell: at the landing both are leaving (no score, nothing served, no
    penalty). The regulars' arrivals never name the target bar during the tell nor his bar afterwards."""
    with fight(model, C) as gb:
        quiet(gb)
        no_spawns(gb)
        to_tell(gb)
        tb = M.get(gb, "target")
        with logic_paused(gb):
            before = set(i for i, s in enumerate(gb.read("patron_state", 16)) if s)
            set_patron(gb, tb, 60)
            set_patron(gb, tb, 100)
        slots = [i for i, s in enumerate(gb.read("patron_state", 16)) if s and i not in before]
        assert len(slots) == 2 and all(gb.read("patron_bar", 16)[i] == tb for i in slots)
        sc, served = score(gb), gb.mem("served")
        until(gb, lambda: gb.mem("boss_bar") == tb, TELL + WAITMAX + AIR + 6)
        frames(gb, 1)
        st = gb.read("patron_state", 16)
        assert all(st[i] in (LEAVING, 0) for i in slots) and LEAVING in st, st   # (a leaving regular may be gone already)
        until(gb, lambda: all(gb.read("patron_state", 16)[i] == 0 for i in slots), 120)
        assert (score(gb), gb.mem("served")) == (sc, served) and gb.mem("lives") == 3
        n = int(re.search(r"#define STORY_PAT_MAX\s+(\d+)", (ROOT / "build" / "story.h").read_text()).group(1))
        assert all(p & 3 != tb for p in gb.read("pat_buf", n)), "no regular is due on the bar he landed on"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_he_waits_for_a_mug_thrown_before_the_tell(model):
    """A mug launched the frame before the tell is caught (a hit, the meter 9) before he leaps; a mug thrown during the
    crouch is not waited for: he leaves and it slides to the left end and breaks (a life)."""
    with fight(model, C) as gb:
        quiet(gb)
        no_spawns(gb)
        throw(gb, B, 136)
        gb.write("boss_hook", 1)
        until(gb, lambda: phase(gb) == MP_TELL, 4)
        until(gb, lambda: phase(gb) == MP_AIR, TELL + WAITMAX + 4)
        assert gb.mem("boss_hits") == 1 and gb.mem("boss_hp") == 9, "the earlier mug was caught before the leap"
        assert not [m for m in mugs(gb, B, FULL)]
        until(gb, lambda: gb.mem("boss_bar") != B, AIR + 4)
        assert gb.mem("lives") == 3
    with fight(model, C) as gb:
        quiet(gb)
        no_spawns(gb)
        to_tell(gb)
        frames(gb, 20)
        throw(gb, B, 136)
        until(gb, lambda: phase(gb) == MP_AIR, TELL + WAITMAX + 4)
        assert gb.mem("boss_hits") == 0, "he left before it reached him"
        until(gb, lambda: gb.mem("lives") == 2, 120)
        assert gb.mem("boss_hp") == 10


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_hit_in_the_tell_pushes_him_and_the_landing_x_stays(model):
    """A hit during the tell: GULP / WINCE, pushed back 8 px on his bar, the CROUCH pose again until the leap; the landing
    still happens at the chosen x on the chosen bar."""
    with fight(model, C) as gb:
        quiet(gb)
        no_spawns(gb)
        until(gb, lambda: gb.mem("boss_x") >= 32, 2 * R["step"] + 4)
        to_tell(gb)
        x, tb, land = gb.mem("boss_x"), M.get(gb, "target"), M.get(gb, "land")
        throw(gb, B, x + 40)
        until(gb, lambda: gb.mem("boss_hits") == 1, 30)
        until(gb, lambda: gb.mem("boss_x") == x - 8, 20)
        until(gb, lambda: phase(gb) == MP_AIR, TELL + WAITMAX + 4)
        until(gb, lambda: gb.mem("boss_bar") == tb, AIR + 4)
        frames(gb, 2)
        until(gb, lambda: marker_at(gb, tb) is None, 12)
        assert gb.mem("boss_x") == land


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_life_lost_in_the_air_brings_him_home(model):
    """A life lost while he is away (the tap check on his home bar is not reached, so the life is a broken mug): after the
    freeze he is on bar 1 at x 16, walking, no marker, the meter kept, the next leap 300 frames away."""
    with fight(model, C) as gb:
        quiet(gb)
        no_spawns(gb)
        to_tell(gb)
        until(gb, lambda: phase(gb) == MP_AIR, TELL + WAITMAX + 4)
        frames(gb, 3)
        throw(gb, B, 20)                                     # (no catcher on his bar: it breaks at the left end)
        until(gb, lambda: state(gb) == LIFE_LOST, 60)
        until(gb, lambda: state(gb) == PLAYING, 200)
        frames(gb, 3)
        assert (gb.mem("boss_bar"), gb.mem("boss_x"), gb.mem("boss_state"), gb.mem("lives"), gb.mem("boss_hp")) == (
            B, R["x"], BS_WALK, 2, 10)
        until(gb, lambda: all(marker_at(gb, b) is None for b in range(4)), 20)
        assert phase(gb) == MP_WALK
        assert gb.mem16("boss_special_t") == EVERY
        assert_body(gb, C, A, R["x"], BP_WALK)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_last_life_lost_is_try_again(model):
    """The last life at the tap: TRY AGAIN."""
    with fight(model, C) as gb:
        quiet(gb)
        gb.write("lives", 1)
        gb.write("boss_x", 128 - R["width"] + 8)
        until(gb, lambda: state(gb) == LIFE_LOST, 8)
        until(gb, lambda: state(gb) == GS_STORY, 200)
        assert gb.mem("story_phase") == SP_FAIL and banner_text(gb, 1) == centred("TRY AGAIN")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_win_the_fight_by_pouring(model):
    """Real pours, the bartender following him bar to bar (pouring only while he walks, so nothing is thrown into a
    crouch): 10 mugs and he is satisfied; no hp poke, no life lost; he leapt at least once; the outro (HAPPY), the marker
    gone; CHAPTER CLEAR, the POST_STADIUM scene, the chapter saved."""
    with fight(model, C) as gb:
        quiet(gb)
        f, clock = 0, Clock(gb)
        while gb.mem("boss_hp") and f < 7000:
            left = [b for _, s, b, _ in mugs(gb) if s == EMPTY and b != gb.mem("boss_bar")]
            to_bar(gb, left[0] if left else gb.mem("boss_bar"))      # (his empties left on the bar he leapt from first)
            if gb.mem("bar") == gb.mem("boss_bar") and phase(gb) == MP_WALK and gb.mem("boss_hold") + len(mugs(gb, gb.mem("boss_bar"), FULL)) < R["hands"]:
                pour(gb)
            else:
                frames(gb, 1)
            f = clock.now()
        assert gb.mem("boss_hits") == 10 and gb.mem("lives") == 3, (gb.mem("boss_hits"), gb.mem("lives"), f)
        assert M.get(gb, "leaps") >= 1, "the fight went through a leap"
        clear_regulars(gb)
        frames(gb, 3)
        assert state(gb) == GS_STORY and gb.mem("story_phase") == SP_OUTRO and gb.mem("boss_state") == BS_OUTRO
        gb.run(60)
        assert_body_on(gb, A, BP_HAPPY)
        assert all(marker_at(gb, b) is None for b in range(4))
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 120)
        gb.run(3)
        assert banner_text(gb, 1) == centred("CHAPTER CLEAR")
        run_until(gb, lambda: state(gb) == GS_STORY and gb.mem("story_scene") == post(C), 300)
        settle(gb)
        assert (gb.mem("boss_on"), gb.mem("story_progress")) == (0, C + 1)


def assert_body_on(gb, a, pose):
    top, bottom = rows_of(gb, gb.mem("boss_bar"))
    k, cols = gb.mem("boss_x") // 8, pose_cols(a, pose)
    assert top[k:k + len(cols)] == cols and bottom[k:k + len(cols)] == [t + 1 for t in cols]
