# docs/minigames_bosses.md 3.8: the Prototype, the robot factory's boss (src/boss_prototype.c; art approved 2026-10-11, look B
# "the hauler"). The fight follows the factory's Last call: his row (32 px, step 100, push 8, gulp 20, hands 2, sip 45,
# meter 12) and his cycle of 460 frames: GREEN 240 (a lamp solid, he takes batteries), YELLOW 60 (the lamp a ring, the tell,
# he still takes one), RED 150 (the lamp an X, the RED pose, his bar's conveyor runs right: every full battery on his bar
# turns round, one that reaches him bounces, the fair-empties schedule is pushed past their arrivals; the last 60 frames show
# the landing marker on the next bar), then 10 frames away and he appears on the marked bar at the same x. Every frame here is
# checked at <= 10 sprites a line.
import re

import pytest
from boss_common import (skip_entrance, BP_HAPPY, BP_WALK, BS_JUMP, BS_OUTRO, BS_SPECIAL, BS_TELL, BS_WALK, Clock, EMPTY, FULL, OAM_TOPPER,
                         OBJ_TOPPER, Own, RETURN, SP_FAIL, SP_OUTRO, TAP_X, art, assert_body, bar_row, check_start, fight,
                         frames, hud, meter_tiles, mugs, play, pose_cols, pour, row, still_regulars, throw, to_bar, until)
from conftest import keg_bg, level_attr, clear_regulars, ROOT, check_golden, logic_paused, venue
from test_boss_mascot import marker_at, rows_of
from test_flow import GS_STORY, LEVEL_CLEAR, LIFE_LOST, PLAYING, run_until, set_patron, score, state, tilemap_row
from test_story import banner_text, centred, post, settle, to_goal
from test_venues import attr_row, cgb_palette

pytestmark = pytest.mark.timeout(300)

C = 5                                   # the robot factory
R = row(C)
A = art("prototype")
B = R["bar"]
BP_RED = 5
SRC = (ROOT / "src" / "boss_prototype.c").read_text()
T_YELLOW, T_RED, T_MARK, T_RIDE, T_LAND, CONV_EVERY = (int(re.search(rf"#define {n}\s+(\d+)", SRC).group(1)) for n in (
    "T_YELLOW", "T_RED", "T_MARK", "T_RIDE", "T_LAND", "CONV_EVERY"))
P = Own("prototype")
CONV = 246
HAT_RING, HAT_X = 4, 6
FACTORY = venue("factory")["bar_map"]
BELT = set(int(x, 16) for x in re.findall(r"0x[0-9A-Fa-f]+", re.search(r"boss_conv_src\[\d+\] = \{([^}]*)\}",
                                                       (ROOT / "build" / "boss_prototype_art.h").read_text()).group(1)))
LEAVING = 4


def RGB(r, g, b):
    return r | g << 5 | b << 10


def t_of(gb):
    return P.get(gb, "t")


def quiet(gb):
    still_regulars(gb)
    play(gb)
    gb.write("spawn_timer", 0xFF)
    gb.write(gb.addr("spawn_timer") + 1, 0x7F)


def to_t(gb, t):
    """The cycle at frame t (a poke between two frames), his state as the cycle's start gives."""
    with logic_paused(gb):
        P.put(gb, "t", t - 1)


def counter(gb, bar):
    return tilemap_row(gb, 5 + 3 * bar + 2, 0, 20)


def belt_row(frame):
    return [CONV + frame if FACTORY[40 + k] in BELT else FACTORY[40 + k] for k in range(18)] + FACTORY[58:60]


def lamp(gb):
    o = gb.oam()[OAM_TOPPER]
    return o["tile"] - OBJ_TOPPER, o["flags"] & 7


def start_red(gb):
    """Into RED at t = T_RED (frames after the poke: the state of the cycle's start of RED)."""
    to_t(gb, T_RED)
    frames(gb, 2)
    assert T_RED <= t_of(gb) <= T_RED + 3


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_his_row_and_art(model):
    """Spec 3.2 / 3.8's numbers and the cycle's timings, the banner lines of spec 7, his approved art (look B, the hauler)
    with the RED pose (extra pose 5), the lamp's 3 shapes (HAT frames 0-3, the ring and X), the Mascot's marker, the
    conveyor's 2 tiles (K5 stripes + K6 arrows, below); no WRAM of his own."""
    assert {k: R[k] for k in ("width", "x", "bar", "step", "push", "gulp", "hands", "sip", "meter", "hat")} == dict(
        width=32, x=16, bar=2, step=100, push=8, gulp=30, hands=2, sip=45, meter=12, hat=8)
    assert (R["line1"], R["line2"]) == ("GREEN MEANS GO", "RED MEANS STOP")
    assert A["poses"] == ["WALK", "STOMP", "GULP", "WINCE", "HAPPY", "RED"]
    assert (T_YELLOW, T_RED - T_YELLOW, T_RIDE - T_RED, T_LAND - T_RIDE, T_RIDE - T_MARK) == (240, 60, 150, 10, 60)
    assert len(A["hat"]) == 128 and len(A["fx"]) == 64 and len(A["conv"]) == 32 and BELT
    assert "; Art: approved design" in (ROOT / "assets/art/boss/prototype.txt").read_text()
    assert not (ROOT / "assets/art/approved/boss_prototype.txt").exists()
    assert "boss_prototype" not in (ROOT / "assets/art/approved/README.md").read_text()
    assert not re.search(r"^(?:static\s+)?u?int(?:8|16)_t\s+\w+\s*(?:[;,=]|\[)", SRC, re.M), "no WRAM of his own"


def tile_bytes(rows):
    """8 rows of . - + # (colours 0-3) as the 16 bytes of a 2bpp tile."""
    out = []
    for r in rows:
        v = [".-+#".index(c) for c in r]
        out += [sum((x & 1) << (7 - i) for i, x in enumerate(v)), sum((x >> 1) << (7 - i) for i, x in enumerate(v))]
    return out


# The owner-approved conveyor (2026-10-12): the front (rows 4-7) K5's yellow / black "/" hazard stripes, the top (rows 0-2) K6's
# steel with small yellow arrowheads that shift between the two frames, row 3 the dark edge. '-' yellow, '+' steel, '#' dark.
CONV_A = ["-+++-+++", "--++--++", "-+++-+++", "########", "----####", "---####-", "--####--", "########"]
CONV_B = ["++-+++-+", "++--++--", "++-+++-+", "########", "----####", "---####-", "--####--", "########"]
KEG = 7                                 # BGPAL_BAR_B: the keg's yellow / steel / dark, the belt's palette


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_conveyor_is_the_approved_k5_stripes_and_k6_arrows(model):
    """The 2 conveyor tiles (BG 246-247) are exactly K5's front + K6's top; the front is the same in both frames and the
    arrows move; CGB: the keg's palette (BG 1 below the stage) holds yellow, steel and dark, the same colours the tiles were drawn in.
    DMG: the shades 153 / 85 / 0 are the bar's own greys under the same indices."""
    assert A["conv"] == tile_bytes(CONV_A) + tile_bytes(CONV_B)
    assert CONV_A[4:] == CONV_B[4:] and CONV_A[:3] != CONV_B[:3]
    with fight(model, C) as gb:
        quiet(gb)
        assert bytes(gb.read(0x8000 + CONV * 16, 32)) == bytes(A["conv"])
        if model == "cgb":
            raw = [gb.read(gb.addr("story_scratch") + 270 + i, 1)[0] for i in range(8)]       # (the keg's slot is BG 1 on the level screen: below the stage the mid-frame chain writes KEG_PAL into it)
            pal = [raw[2 * i] | raw[2 * i + 1] << 8 for i in range(4)]
            assert pal[1:] == [RGB(31, 27, 9), RGB(15, 17, 20), RGB(2, 3, 5)], pal


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_fight_follows_the_last_call(model):
    """After the factory's Last call: BOSS and his lines; the Prototype on bar 2 at x 16 (his tiles, palettes, the lamp's
    frames, the marker and conveyor tiles), the meter of 12, GREEN (the solid lamp). Golden boss_prototype: GREEN, a
    battery on its way."""
    with fight(model, C, banner=True) as gb:
        skip_entrance(to_goal(gb))
        gb.run(2)
        check_start(gb, C, A, model)
        assert bytes(gb.read(0x8000 + 248 * 16, 64)) == bytes(A["fx"])
        assert bytes(gb.read(0x8000 + CONV * 16, 32)) == bytes(A["conv"])
        assert hud(gb) == meter_tiles(12, 12) and t_of(gb) <= 3
        assert counter(gb, B) == FACTORY[40:60], "the plain counter"
        quiet(gb)
        throw(gb, B, 100)
        frames(gb, 10)
        check_golden(gb, "boss_prototype")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_cycle_green_yellow_red_ride(model):
    """GREEN: walks, the lamp solid. YELLOW (frame 240): the lamp a ring, he stands. RED (300): the X, the RED pose, the
    chevrons on his bar's counter row stepping every 6 frames; from 390 the marker on the next bar at his columns; at 450 the
    counter is plain again and he is gone for 10 frames; at 460 he is on the marked bar at the same x, GREEN. Golden
    boss_prototype_red (RED, the conveyor, the X lamp)."""
    with fight(model, C) as gb:
        quiet(gb)
        until(gb, lambda: t_of(gb) >= 30, 40)
        assert lamp(gb)[0] in (0, 2) and gb.mem("boss_state") in (BS_WALK, 1)
        to_t(gb, T_YELLOW)
        frames(gb, 3)
        x = gb.mem("boss_x")
        assert lamp(gb)[0] == HAT_RING and gb.mem("boss_state") == BS_TELL
        assert_body(gb, C, A, x, BP_WALK)
        if model == "cgb":
            assert [cgb_palette(gb, p, True)[2] for p in (7, 5, 4)] == [RGB(5, 27, 5), RGB(31, 25, 0), RGB(31, 3, 3)]
            assert cgb_palette(gb, 5, True)[1] == A["pal"][1] and lamp(gb)[1] == 5
        frames(gb, 40)
        assert gb.mem("boss_x") == x, "he stands in the yellow"
        to_t(gb, T_RED)
        frames(gb, 2)
        assert gb.mem("boss_state") == BS_SPECIAL and lamp(gb)[0] == HAT_X
        frames(gb, 1)                    # (the frame the state changes is a heavy one, logic to line ~107; with the mid-frame chain's VBlank handler the body's redraw is drained a frame later than it was)
        assert_body(gb, C, A, x, BP_RED)
        until(gb, lambda: counter(gb, B) == belt_row(0) or counter(gb, B) == belt_row(1), 8)
        if model == "cgb":
            assert attr_row(gb, 5 + 3 * B + 2) == [keg_bg(5)] * 20, "the belt in the keg's palette (the keg's own columns are 7 too)"
        seen = [counter(gb, B)]
        for _ in range(3):
            f0 = counter(gb, B)
            until(gb, lambda: counter(gb, B) != f0, CONV_EVERY + 4)
            seen.append(counter(gb, B))
        assert seen[0] == seen[2] and seen[1] == seen[3] and seen[0] != seen[1], "two frames, alternating"
        check_golden(gb, "boss_prototype_red")
        assert all(marker_at(gb, b) is None for b in range(4))
        to_t(gb, T_MARK)
        frames(gb, 14)
        tb = next(b for b in range(4) if marker_at(gb, b) is not None)
        assert tb != B and marker_at(gb, tb) == x // 8, "the marker on the next bar at his columns"
        to_t(gb, T_RIDE)
        until(gb, lambda: gb.mem("boss_state") == BS_JUMP, 4)
        frames(gb, 3)
        until(gb, lambda: counter(gb, B) == FACTORY[40:60], 8)
        frames(gb, 2)
        if model == "cgb":
            assert attr_row(gb, 5 + 3 * B + 2) == level_attr(5, venue("factory")["bar_attr"])[40:60], "the counter's palette back"
        top, bottom = rows_of(gb, B)
        assert gb.oam()[OAM_TOPPER]["y"] == 0
        assert top[x // 8:x // 8 + 4] != pose_cols(A, BP_WALK), "his body is gone"
        until(gb, lambda: gb.mem("boss_bar") == tb, T_LAND - T_RIDE + 4)
        until(gb, lambda: marker_at(gb, tb) is None, 12)
        frames(gb, 6)
        assert (gb.mem("boss_x"), gb.mem("boss_state"), t_of(gb) < 30) == (x, BS_WALK, True)
        top, bottom = rows_of(gb, tb)
        cols = pose_cols(A, BP_WALK)
        assert top[x // 8:x // 8 + 4] == cols and bottom[x // 8:x // 8 + 4] == [t + 1 for t in cols]
        assert counter(gb, tb) == FACTORY[40:60] and lamp(gb)[0] in (0, 2)
        assert gb.mem("lives") == 3


@pytest.mark.parametrize("model", ["cgb"])
def test_the_belts_tiles_and_palette_change_in_the_same_frame(model):
    """RED's start: the 18 counter attributes become palette 7 in the very frame the counter tiles become the belt, never
    a frame earlier (the old blip: the plain counter tiles in the keg's palette for one frame) or later. Every frame from
    just before T_RED to a few frames in: palette 7 on the counter if and only if the counter tiles are the belt's."""
    with fight(model, C) as gb:
        quiet(gb)
        to_t(gb, T_RED - 6)
        seen = []
        for _ in range(20):
            frames(gb, 1)
            tiles = counter(gb, B)[:18]
            attrs = attr_row(gb, 5 + 3 * B + 2)[:18]
            belt = any(t in (CONV, CONV + 1) for t in tiles)
            sevens = attrs == [keg_bg(5)] * 18
            assert belt == sevens, (t_of(gb), tiles, attrs)
            seen.append(belt)
        assert not seen[0] and seen[-1] and seen.index(True) > 0, "the belt starts inside the window"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_battery_launched_at_the_start_of_yellow_is_caught(model):
    """A battery on its way at yellow's first frame (launched at the spout) still reaches him in the yellow (the 60 frames
    outlast the 44 it needs): a hit, the meter 11."""
    with fight(model, C) as gb:
        quiet(gb)
        to_t(gb, T_YELLOW)
        frames(gb, 1)
        throw(gb, B, 136)
        until(gb, lambda: gb.mem("boss_hits") == 1, 60)
        assert t_of(gb) < T_RED and gb.mem("boss_hp") == 11


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_red_turns_the_batteries_round_and_bounces_those_that_arrive(model):
    """At RED every full battery on his bar becomes a MUG_RETURN moving right 1 px a frame; the regular's-empty schedule
    (next_arrival) is pushed past the last one's arrival plus empty_gap; a battery that reaches him in RED bounces the same
    way (no hit, the meter and his place unchanged); returned batteries stay >= 32 frames apart; the bartender at the tap
    catches them all as empties (no life lost)."""
    with fight(model, C) as gb:
        quiet(gb)
        to_bar(gb, B)
        to_t(gb, T_RED - 10)
        frames(gb, 2)
        throw(gb, B, 104)
        throw(gb, B, 72)
        frames(gb, 1)
        x = gb.mem("boss_x")
        u0 = [(i, bx) for i, s, b, bx in mugs(gb, B, FULL)]
        assert len(u0) == 2
        until(gb, lambda: t_of(gb) >= T_RED, 40)
        frames(gb, 2)
        rs = mugs(gb, B, RETURN)
        assert len(rs) == 2 and not mugs(gb, B, FULL), "both batteries turned round"
        before = {i: bx for i, _, _, bx in rs}
        fc = gb.mem("frame_counter")
        frames(gb, 10)
        n = (gb.mem("frame_counter") - fc) & 255          # (game frames: one emulator frame may hold none when a frame ran long)
        after = {i: bx for i, _, _, bx in mugs(gb, B, RETURN)}
        assert n >= 9 and all(after[i] - before[i] == n for i in before), "1 px a frame to the right"
        xs = sorted(after.values())
        assert xs[1] - xs[0] >= 32
        gap = gb.mem("empty_gap")
        last = max(TAP_X - bx for bx in after.values())
        assert gb.mem16("next_arrival") >= last + gap - 12, (gb.mem16("next_arrival"), last, gap)
        throw(gb, B, 60)                                  # a battery that arrives during RED
        until(gb, lambda: not any(s == FULL for _, s, _, _ in mugs(gb, B)), 40)
        assert gb.mem("boss_hits") == 0 and gb.mem("boss_hp") == 12 and gb.mem("boss_x") == x and gb.mem("lives") == 3
        assert len(mugs(gb, B, RETURN)) == 3, "it bounced"
        run_until(gb, lambda: not mugs(gb, B, RETURN), 300)
        assert gb.mem("lives") == 3


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_landing_scares_the_regulars_without_score(model):
    """A regular on the marked bar when he rides there is leaving at the landing (no score, nothing served)."""
    with fight(model, C) as gb:
        quiet(gb)
        to_t(gb, T_MARK)
        frames(gb, 3)
        tb = next(b for b in range(4) if marker_at(gb, b) is not None)
        with logic_paused(gb):
            before = set(i for i, s in enumerate(gb.read("patron_state", 16)) if s)
            set_patron(gb, tb, 90)
        slots = [i for i, s in enumerate(gb.read("patron_state", 16)) if s and i not in before]
        sc, served = score(gb), gb.mem("served")
        until(gb, lambda: gb.mem("boss_bar") == tb, T_LAND - T_MARK + 4)
        frames(gb, 1)
        st = gb.read("patron_state", 16)
        assert all(st[i] in (LEAVING, 0) for i in slots) and LEAVING in st
        frames(gb, 120)
        assert (score(gb), gb.mem("served")) == (sc, served) and gb.mem("lives") == 3


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_life_lost_in_red_restores_the_counter_and_brings_him_home(model):
    """A life lost in RED: the conveyor gone, the marker gone, after the freeze he is on bar 2 at x 16 in GREEN, the
    meter kept."""
    with fight(model, C) as gb:
        quiet(gb)
        start_red(gb)
        frames(gb, 10)
        assert counter(gb, B) in (belt_row(0), belt_row(1))
        gb.write("boss_x", 128 - R["width"] + 8)
        until(gb, lambda: state(gb) == LIFE_LOST, 8)
        until(gb, lambda: state(gb) == PLAYING, 200)
        frames(gb, 12)
        assert (gb.mem("boss_bar"), gb.mem("boss_x"), gb.mem("boss_state"), gb.mem("lives"), gb.mem("boss_hp")) == (
            B, R["x"], BS_WALK, 2, 12)
        assert t_of(gb) < 20 and counter(gb, B) == FACTORY[40:60] and lamp(gb)[0] in (0, 2)
        if model == "cgb":
            assert attr_row(gb, 5 + 3 * B + 2) == level_attr(5, venue("factory")["bar_attr"])[40:60], "the counter's palette back"
        assert all(marker_at(gb, b) is None for b in range(4))


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
    """Real pours following him bar to bar, only early enough in the cycle that every battery arrives before RED (60 + 44
    frames of margin), his empties on a bar he left caught first: 12 batteries and he is satisfied; no hp poke, no life
    lost; he rode at least once; the outro (HAPPY), the counter plain, no marker; CHAPTER CLEAR, the POST_ROBOT scene, the
    chapter saved."""
    with fight(model, C) as gb:
        quiet(gb)
        f, clock = 0, Clock(gb)
        while gb.mem("boss_hp") and f < 9000:
            left = [b for _, s, b, _ in mugs(gb) if s in (EMPTY, RETURN) and b != gb.mem("boss_bar")]
            to_bar(gb, left[0] if left else gb.mem("boss_bar"))
            bb = gb.mem("boss_bar")
            if (gb.mem("bar") == bb and t_of(gb) < T_YELLOW - 44 and gb.mem("boss_state") != BS_JUMP
                    and gb.mem("boss_hold") + len(mugs(gb, bb, FULL)) < R["hands"]):
                pour(gb)
            else:
                frames(gb, 1)
            f = clock.now()
        assert gb.mem("boss_hits") == 12 and gb.mem("lives") == 3, (gb.mem("boss_hits"), gb.mem("lives"), f)
        clear_regulars(gb)
        frames(gb, 3)
        assert state(gb) == GS_STORY and gb.mem("story_phase") == SP_OUTRO and gb.mem("boss_state") == BS_OUTRO
        gb.run(60)
        top, bottom = rows_of(gb, gb.mem("boss_bar"))
        k, cols = gb.mem("boss_x") // 8, pose_cols(A, BP_HAPPY)
        assert top[k:k + 4] == cols and bottom[k:k + 4] == [t + 1 for t in cols]
        assert all(marker_at(gb, b) is None for b in range(4)) and counter(gb, gb.mem("boss_bar")) == FACTORY[40:60]
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 120)
        gb.run(3)
        assert banner_text(gb, 1) == centred("CHAPTER CLEAR")
        run_until(gb, lambda: state(gb) == GS_STORY and gb.mem("story_scene") == post(C), 300)
        settle(gb)
        assert (gb.mem("boss_on"), gb.mem("story_progress")) == (0, C + 1)
