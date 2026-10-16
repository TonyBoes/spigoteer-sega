# docs/minigames_bosses.md 3.9: the Sumo, the teahouse's boss (src/boss_sumo.c; art approved 2026-10-11, look 2 round 2).
# The fight is a PUSHING MATCH (owner 2026-10-15): no drink limit; the HUD meter fills with drinks and its target shrinks
# (6, 5, 4, 3, 2, 1, 1 ...); a full meter knocks him back 32 px (a stagger); he loses by RING-OUT at the bar's left end
# (x 0) and wins at the tap (x 96); he still steps on the tune's beat (192 frames) and charges (the stamp, 16 px, a cup
# cancels it); his ENTRANCE is the ring ritual (he walks in from the wall, throws salt, stamps twice: the picture shakes).
# Every frame here is checked at <= 10 sprites a line.
import re

import pytest
from boss_common import (BLANK, BP_GULP, BP_HAPPY, BP_STOMP, BP_WALK, BP_WINCE, BS_ENTER, BS_JUMP, start_entrance, BS_OUTRO, BS_SPECIAL, BS_TELL,
                         BS_WALK, Clock, EMPTY, FULL, HUD_BG, OAM_TOPPER, OBJ_TOPPER, Own, SP_FAIL, SP_OUTRO, SPOUT_X,
                         TAP_X, art, arrivals_ok, assert_body, block_empties, body, fight, frames, hud, mugs, pour, row,
                         still_regulars, throw, to_bar, until)
from conftest import clear_regulars, ROOT, check_golden, logic_paused, venue
from test_flow import GS_STORY, LEVEL_CLEAR, LIFE_LOST, PLAYING, run_until, state
from test_story import banner_text, centred, post, settle, to_goal

pytestmark = pytest.mark.timeout(300)

C = 7                                   # the teahouse
R = row(C)
A = art("sumo")
B = R["bar"]
BP_SHIKO, BP_HMPH, BP_HIDE = 5, 6, 14
SRC = (ROOT / "src" / "boss_sumo.c").read_text()
NAMES = ("SUMO_START", "SUMO_KNOCK", "SUMO_STAGGER", "SUMO_FLASH", "SUMO_OUT", "SUMO_HIT_POSE", "SUMO_EVERY", "SUMO_TELL",
         "SUMO_HOP", "SUMO_HOPS", "SUMO_HMPH", "CAP_ANY", "SOLO_BG", "SE_IN", "SE_STEP", "SE_SALT", "SE_STAMP1", "SE_LEG2",
         "SE_STAMP2", "SE_BOW", "SE_END", "SE_TAIL")
(START, KNOCK, STAGGER, FLASH, OUT, HIT_POSE, EVERY, TELL, HOP, HOPS, HMPH, CAP_ANY, SOLO, SE_IN, SE_STEP, SE_SALT, SE_STAMP1,
 SE_LEG2, SE_STAMP2, SE_BOW, SE_END, SE_TAIL) = (int(re.search(rf"#define {n}\s+(\d+)", SRC).group(1)) for n in NAMES)
SU_WALK, SU_TELL, SU_CHARGE, SU_HMPH, SU_KNOCK, SU_OUT = range(6)
SUMO = Own("sumo")
SONGS = (ROOT / "tools" / "songs.py").read_text()
SAKURA_TEMPO = int(re.search(r'song\("sakura", (\d+),', SONGS).group(1))
SFX_SERVE, SFX_SHAKE, SFX_DON, SFX_KA = 5, 8, 10, 11
SCY = 0xFF42
START_X = R["x"]
START_FRAMES = 148                        # SE_END: the ritual's length


def phase(gb):
    return SUMO.get(gb, "phase")


def quiet(gb):
    """The entrance and the intro over, PLAYING; the regulars still; no empty of his sent (nobody catches it here)."""
    still_regulars(gb)
    until(gb, lambda: SUMO.get(gb, "ent") == 0 and gb.mem("intro_timer") == 0 and state(gb) == PLAYING, 400)
    block_empties(gb)


def setx(gb, x):
    with logic_paused(gb):
        gb.write("boss_x", x)
        gb.write("boss_col", x // 8)


def sfx(gb, n):
    return gb.read("sfx_count", 13)[n]


def hit_now(gb):
    """A full mug on his catch line: caught on the second game frame (frame-exact)."""
    with logic_paused(gb):
        lim = gb.mem("boss_lim")
        assert lim
    throw(gb, B, lim)
    hits = gb.mem("boss_hits")
    frames(gb, 1)
    assert gb.mem("boss_hits") == hits, "the mug moves first (2 px a frame)"
    frames(gb, 1)
    assert gb.mem("boss_hits") == hits + 1, "caught on the second frame"


def pints(n, f):
    """The HUD row for a target of n pips with f filled."""
    out = [HUD_BG]
    for k in range(7):
        t = 2 * k
        if t + 1 < n:
            out.append(HUD_BG + (3 if f >= t + 2 else 2 if f > t else 1))
        elif t < n:
            out.append(SOLO + (1 if f > t else 0))
        else:
            out.append(BLANK)
    return out


def pose(gb):
    """His pose now (boss_pose's low nibble)."""
    return gb.mem("boss_pose") & 15


def settled(gb):
    """The knock-back over, walking again (and the meter's blink over)."""
    until(gb, lambda: phase(gb) == SU_WALK and not SUMO.get(gb, "flash"), 80)
    frames(gb, 1)


def fill_meter(gb, x=64):
    """A whole meter of cups at x (he stands there); returns when the last is caught."""
    setx(gb, x)
    for _ in range(gb.mem("boss_hp")):
        hit_now(gb)


def test_his_row_and_art():
    """His numbers (the step is two bars of the teahouse tune: 16 rows of 12 frames, which divide the tune's 1344), the
    banner lines, the approved art with SHIKO and HMPH (extra poses 5 and 6), no WRAM of his own."""
    assert {k: R[k] for k in ("width", "x", "bar", "step", "push", "gulp", "hands", "sip", "meter", "hat")} == dict(
        width=40, x=24, bar=1, step=192, push=0, gulp=0, hands=2, sip=90, meter=6, hat=16)
    assert R["step"] % (8 * SAKURA_TEMPO) == 0 and 1344 % R["step"] == 0, "whole bars, dividing the tune"
    assert (R["line1"], R["line2"]) == ("THE CHAMPION", "PUSH HIM OUT")
    assert A["poses"] == ["WALK", "STOMP", "GULP", "WINCE", "HAPPY", "SHIKO", "HMPH"]
    assert (START, KNOCK, STAGGER, CAP_ANY, EVERY, TELL, HOP * HOPS) == (6, 32, 44, 250, 480, 60, 8) and TELL >= 45
    assert KNOCK % 8 == 0 and STAGGER > KNOCK // 8 * HOP and R["x"] < KNOCK and SOLO + 2 <= 248
    assert len(A["pairs"]) <= 30
    assert "; Art: approved design" in (ROOT / "assets/art/boss/sumo.txt").read_text()
    assert not (ROOT / "assets/art/approved/boss_sumo.txt").exists()
    assert "boss_sumo" not in (ROOT / "assets/art/approved/README.md").read_text()
    assert not re.search(r"^(?:static\s+)?u?int(?:8|16)_t\s+\w+\s*(?:[;,=]|\[)", SRC, re.M), "no WRAM of his own"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_fight_follows_the_last_call(model):
    """After the teahouse's Last call: BOSS and the new lines; the entrance runs, then the Sumo stands on bar 1 at x 24 (his
    tiles, palettes), the meter of 6 pips empty, the drink limit gone, his topknot as the topper; the engine's own stomp
    timer off (boss_step 0, his period 192). Golden boss_sumo: walking, a cup on its way."""
    with fight(model, C, banner=True) as gb:
        assert banner_text(gb, 2) == centred(R["line1"]) and banner_text(gb, 3) == centred(R["line2"])
        start_entrance(to_goal(gb, boss_start=False))
        gb.run(2)
        assert SUMO.get(gb, "ent") >= 1 and gb.mem("boss_state") == BS_ENTER, "the entrance first"
        quiet(gb)
        assert (gb.mem("boss_step"), SUMO.get(gb, "period"), phase(gb)) == (0, R["step"], SU_WALK)
        assert (gb.mem("boss_cap"), gb.mem("boss_hp"), SUMO.get(gb, "cyc"), gb.mem("boss_x")) == (CAP_ANY, 6, 6, START_X)
        assert gb.mem16("boss_special_t") <= EVERY and gb.mem("boss_bar") == B
        assert_body(gb, C, A, START_X, BP_WALK)
        assert hud(gb) == pints(6, 0)
        for p, data in enumerate(A["pairs"]):
            t = 162 + 2 * p if p < 21 else 216 + 2 * (p - 21)
            assert bytes(gb.read((0x9000 if t < 128 else 0x8000) + t * 16, 32)) == bytes(data), f"body column {p}"
        o = gb.oam()[OAM_TOPPER]
        assert (o["y"], o["x"], o["tile"]) == (5 * 8 + 3 * B * 8 + 8, START_X + R["hat"] + 8, OBJ_TOPPER)
        throw(gb, B, 100)
        frames(gb, 10)
        check_golden(gb, "boss_sumo")


def test_the_one_pip_tiles_come_from_the_pints():
    """BG 246 / 247 (a one-pip target's last tile) are built from the engine's EMPTY / HALF pint: the left pip as it is,
    the right half the band's own colour."""
    with fight("cgb", C) as gb:
        meter = bytes(gb.read(0x8000 + (HUD_BG + 1) * 16, 48))
        for k, src in ((0, 0), (1, 16)):
            got = bytes(gb.read(0x8000 + (SOLO + k) * 16, 16))
            assert got == bytes((b & 0xF0) | 0x0F for b in meter[src:src + 16])
        assert got[:2] == b"\xff\xff" and got[2] & 0x0F == 0x0F and got[3] & 0x0F == 0x0F


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_meter_fills_and_the_target_shrinks(model):
    """Targets 6, 5, 4, 3, 2, 1, 1: a pint fills with each cup (boss_hp counts the cups still to go), the full meter blinks
    for FLASH frames and then the next, shorter target shows, empty. Golden boss_sumo_meter4: the 4-target half full."""
    with fight(model, C) as gb:
        quiet(gb)
        want = [6, 5, 4, 3, 2, 1, 1]
        for cycle, n in enumerate(want):
            assert (SUMO.get(gb, "cyc"), gb.mem("boss_hp"), SUMO.get(gb, "cycles")) == (n, n, cycle)
            setx(gb, 64)
            block_empties(gb)
            for f in range(n):
                hit_now(gb)
                frames(gb, 1)
                if f < n - 1:
                    assert gb.mem("boss_hp") == n - f - 1 and hud(gb) == pints(n, f + 1), (n, f)
                    if n == 4 and f == 1:
                        check_golden(gb, "boss_sumo_meter4")
            assert SUMO.get(gb, "cycles") == cycle + 1 and phase(gb) == SU_KNOCK
            assert gb.mem("boss_hp") == max(n - 1, 1) and SUMO.get(gb, "cyc") == max(n - 1, 1)
            assert gb.mem("boss_xpose") == BP_WINCE
            assert hud(gb) in (pints(n, n), [HUD_BG] + [BLANK] * 7), "the full meter blinks"
            until(gb, lambda: SUMO.get(gb, "flash") == 0, FLASH + 2)
            frames(gb, 1)
            assert hud(gb) == pints(max(n - 1, 1), 0)
            settled(gb)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_full_meter_blinks(model):
    """The blink: the full old target and a blank meter alternate (4 frames each) for FLASH frames; the engine's own catch
    rules are not his (no gulp, no push of the engine's)."""
    with fight(model, C) as gb:
        quiet(gb)
        setx(gb, 64)
        fill_meter(gb)
        seen = []
        for _ in range(FLASH):
            frames(gb, 1)
            seen.append(tuple(hud(gb)))
        assert tuple(pints(6, 6)) in seen and tuple([HUD_BG] + [BLANK] * 7) in seen
        assert gb.mem("boss_push") == 0 and gb.mem("boss_state") != 1


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_full_meter_knocks_him_back_32_px(model):
    """The meter's last cup: four 8 px hops (one per 4 frames, the WINCE pose), then he is dazed (no step, even on the beat)
    until STAGGER frames after the cup, then he walks; the charge timer starts over. A cup in the stagger fills a pip
    but never ends the meter."""
    with fight(model, C) as gb:
        quiet(gb)
        fill_meter(gb, 64)
        x0 = gb.mem("boss_x")                     # (64, or 72 when a step on the beat came in the six cups)
        assert phase(gb) == SU_KNOCK and x0 in (64, 72)
        xs = []
        for _ in range(STAGGER):
            frames(gb, 1)
            xs.append(gb.mem("boss_x"))
        assert xs[0] == x0 and xs[-1] == x0 - KNOCK, xs
        assert xs == sorted(xs, reverse=True) and len(set(xs)) == KNOCK // 8 + 1
        assert max(b - a for a, b in zip(xs, xs[1:])) == 0 or max(a - b for a, b in zip(xs, xs[1:])) == 8
        hops = [i for i in range(1, len(xs)) if xs[i] != xs[i - 1]]
        assert all(b - a == HOP for a, b in zip(hops, hops[1:])), hops
        assert phase(gb) in (SU_KNOCK, SU_WALK)
        until(gb, lambda: phase(gb) == SU_WALK, 6)
        assert gb.mem("boss_x") == x0 - KNOCK and gb.mem16("boss_special_t") >= EVERY - 6
        assert gb.mem("boss_hold") == 6, "he drank all six"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_pose_and_golden_during_the_knock_back(model):
    """The WINCE pose while he slides (his columns follow him); golden boss_sumo_knock at the second hop."""
    with fight(model, C) as gb:
        quiet(gb)
        fill_meter(gb, 64)
        until(gb, lambda: gb.mem("boss_x") <= 56, 14)
        frames(gb, 2)
        assert pose(gb) == BP_WINCE and gb.mem("boss_pose") >> 4 == 3, "WINCE, three empties in his hand"
        check_golden(gb, "boss_sumo_knock")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_at_target_1_every_cup_knocks_him_back(model):
    """Target 1: one cup fills the meter, and each knocks him back 32 px; the meter stays one pip (one-pip tile)."""
    with fight(model, C) as gb:
        quiet(gb)
        SUMO.put(gb, "cyc", 1)
        gb.write("boss_hp", 1)
        for k in range(3):
            setx(gb, 72)
            block_empties(gb)
            hit_now(gb)
            assert gb.mem("boss_hp") == 1 and phase(gb) == SU_KNOCK and SUMO.get(gb, "cycles") == k + 1
            frames(gb, 17)
            assert gb.mem("boss_x") == 72 - KNOCK
            settled(gb)
            assert hud(gb) == pints(1, 0) and hud(gb)[1] == SOLO


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_ring_out_wins(model):
    """Six cups at his start x 24: the knock-back takes him to the wall (x 0) in three hops: out. SUMO_OUT frames at the
    wall (WINCE), then boss_hp 0 and the engine's outro: he is GONE (no HAPPY, no topper), the wall where he stood, the
    crowd cheers. No life lost. Golden boss_sumo_out."""
    with fight(model, C) as gb:
        quiet(gb)
        setx(gb, 24)
        for _ in range(6):
            hit_now(gb)
        lives = gb.mem("lives")
        until(gb, lambda: phase(gb) == SU_OUT, 20)
        assert gb.mem("boss_x") == 0 and gb.mem("boss_hp") >= 1, "still on his feet"
        frames(gb, 3)
        assert_body(gb, C, A, 0, BP_WINCE, hold=3)
        check_golden(gb, "boss_sumo_out")
        serves = sfx(gb, SFX_SERVE)
        until(gb, lambda: gb.mem("boss_hp") == 0, OUT + 2)
        assert SUMO.get(gb, "out") == 1
        clear_regulars(gb)
        frames(gb, 4)
        assert gb.mem("boss_state") == BS_OUTRO and SUMO.get(gb, "out") == 1 and gb.mem("boss_xpose") == BP_HIDE
        assert sfx(gb, SFX_SERVE) > serves
        top, bottom = body(gb, R)
        wall = venue("teahouse")["bar_map"]
        assert top[:6] == wall[:6] and gb.oam()[OAM_TOPPER]["y"] == 0, "he is gone"
        assert gb.mem("lives") == lives
        assert state(gb) == GS_STORY and gb.mem("story_phase") == SP_OUTRO


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_plain_defeat_leaves_him_happy(model):
    """Beaten any way but the ring-out (the test hook: boss_hp 0): the outro's HAPPY pose, not gone."""
    with fight(model, C) as gb:
        quiet(gb)
        gb.write("boss_hook", 3)                  # (HOOK_DEFEAT: beaten the plain way: he is happy, not out)
        frames(gb, 3)
        assert gb.mem("boss_state") == BS_OUTRO and SUMO.get(gb, "out") == 0 and gb.mem("boss_xpose") == 0
        frames(gb, 2)
        assert_body(gb, C, A, gb.mem("boss_x"), BP_HAPPY)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_no_drink_limit(model):
    """Five cups in a row (every other frame): all drunk, he holds five empties (no hands rule: none passes him), boss_lim
    stays set; (the engine's cap of 2 would have let the third go past)."""
    with fight(model, C) as gb:
        quiet(gb)
        setx(gb, 56)
        for k in range(5):
            assert gb.mem("boss_lim") and gb.mem("boss_cap") == CAP_ANY
            hit_now(gb)
            frames(gb, 1)
        assert gb.mem("boss_hits") == 5 and gb.mem("boss_hold") == 5 and gb.mem("lives") == 3
        assert gb.mem("boss_hp") == 1 and gb.mem("boss_lim")
        assert not [m for m in mugs(gb, B, FULL)]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_his_empties_still_come_back(model):
    """He sends the empties back up his bar after the sip (90 frames): one per sip while the fair-empties schedule allows."""
    with fight(model, C, entrance=True) as gb:
        still_regulars(gb)
        until(gb, lambda: SUMO.get(gb, "ent") == 0 and gb.mem("intro_timer") == 0 and state(gb) == PLAYING, 400)
        setx(gb, 56)
        hit_now(gb)
        until(gb, lambda: mugs(gb, B, EMPTY), 140)
        assert gb.mem("boss_hold") == 0


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_steps_land_on_the_beat(model):
    """He steps 8 px (the STOMP pose) every 192 frames, each step on the same frame of the tune's two bars: music_frames at
    each step is the same modulo 192. With the music off: every 192 frames by his own clock."""
    with fight(model, C) as gb:
        quiet(gb)
        gb.write(gb.addr("boss_special_t") + 1, 0x7F)    # (no charge in the way: his stomps are the steps counted)
        assert gb.mem("sound_on") == 1
        seen = []
        x = gb.mem("boss_x")
        while len(seen) < 3:
            frames(gb, 1)
            if gb.mem("boss_x") != x:
                assert gb.mem("boss_x") == x + 8
                x = gb.mem("boss_x")
                seen.append(gb.mem16("music_frames"))
                frames(gb, 1)
                assert_body(gb, C, A, x, BP_STOMP)
                gb.write("boss_x", 24)                    # (back: the tap is not reached; a poke between frames)
                gb.write("boss_col", 3)
                x = 24
        assert len({(m - 1) % R["step"] for m in seen}) == 1, seen
        assert (seen[0] - 1) % R["step"] <= 1, "on the first row of the two bars"
        gb.write("sound_on", 0)
        clock = Clock(gb)
        steps = []
        while len(steps) < 3:
            frames(gb, 1)
            if gb.mem("boss_x") != x:
                x = gb.mem("boss_x")
                steps.append(clock.now())
                gb.write("boss_x", 24)
                gb.write("boss_col", 3)
                x = 24
        assert [b - a for a, b in zip(steps, steps[1:])] == [R["step"]] * 2, steps


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_cup_shows_the_hit_pose_without_a_push(model):
    """A cup that does not fill the meter: the hit pose (GULP) for a moment, no push, no stop; he keeps his x."""
    with fight(model, C) as gb:
        quiet(gb)
        setx(gb, 40)
        hit_now(gb)
        assert (gb.mem("boss_hp"), gb.mem("boss_hold"), gb.mem("boss_push"), phase(gb)) == (5, 1, 0, SU_WALK)
        frames(gb, 1)
        assert pose(gb) == BP_GULP
        assert gb.mem("boss_state") == BS_WALK and hud(gb) == pints(6, 1)
        frames(gb, HIT_POSE + 2)
        assert gb.mem("boss_x") >= 40 and gb.mem("boss_xpose") == 0


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_charge(model):
    """480 walking frames, then the stamp: 60 frames of SHIKO, he stands; then the charge: 16 px in 8 frames (two 8 px hops);
    then he walks on the beat again and the next charge is 480 frames away. """
    with fight(model, C) as gb:
        quiet(gb)
        clock = Clock(gb)
        until(gb, lambda: clock.now() and phase(gb) == SU_TELL, EVERY + 10)
        t_tell = clock.now()
        assert 0 < t_tell <= EVERY + 2
        x = gb.mem("boss_x")
        frames(gb, 2)
        assert gb.mem("boss_state") == BS_TELL
        assert_body(gb, C, A, x, BP_SHIKO)
        frames(gb, 20)
        until(gb, lambda: clock.now() and phase(gb) == SU_CHARGE, TELL + 4)
        assert TELL - 2 <= clock.now() - t_tell <= TELL + 2 and gb.mem("boss_x") == x, "he stands through the stamp"
        t_charge = clock.now()
        until(gb, lambda: clock.now() and phase(gb) == SU_WALK, 20)
        assert HOP * HOPS - 2 <= clock.now() - t_charge <= HOP * HOPS + 2
        assert gb.mem("boss_x") == x + 8 * HOPS and SUMO.get(gb, "charges") == 1
        assert gb.mem("boss_state") == BS_WALK and EVERY - 4 <= gb.mem16("boss_special_t") <= EVERY


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_stamp_golden(model):
    """Golden boss_sumo_shiko: the stamp (the tell), 22 frames in."""
    with fight(model, C) as gb:
        quiet(gb)
        until(gb, lambda: phase(gb) == SU_TELL, EVERY + 10)
        frames(gb, 22)
        check_golden(gb, "boss_sumo_shiko")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_cup_in_the_stamp_calls_the_charge_off(model):
    """A cup during the stamp: the charge is off (the HMPH pose for 30 frames, he stands), the cup fills a pip; then he walks
    and the next charge is 480 frames away; no charge happened."""
    with fight(model, C) as gb:
        quiet(gb)
        setx(gb, 40)
        gb.write("boss_hook", 1)
        until(gb, lambda: phase(gb) == SU_TELL, 4)
        frames(gb, 10)
        x = gb.mem("boss_x")
        hit_now(gb)
        assert (phase(gb), SUMO.get(gb, "cancels"), gb.mem("boss_hp")) == (SU_HMPH, 1, 5)
        frames(gb, 1)
        assert gb.mem("boss_state") == BS_SPECIAL
        assert gb.mem("boss_pose") == BP_HMPH, "HMPH (no hand column on that pose)"
        until(gb, lambda: phase(gb) == SU_WALK, HMPH + 4)
        assert gb.mem("boss_x") == x and SUMO.get(gb, "charges") == 0
        assert EVERY - 4 <= gb.mem16("boss_special_t") <= EVERY
        assert hud(gb) == pints(6, 1), "the test hook's engine meter was replaced by his"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_knock_back_ends_a_charge(model):
    """The cup that fills the meter during the stamp: no charge (the knock-back instead)."""
    with fight(model, C) as gb:
        quiet(gb)
        setx(gb, 64)
        for _ in range(5):
            hit_now(gb)
        until(gb, lambda: phase(gb) == SU_WALK, 30)
        gb.write("boss_hook", 1)
        until(gb, lambda: phase(gb) == SU_TELL, 4)
        hit_now(gb)
        assert phase(gb) == SU_KNOCK and SUMO.get(gb, "charges") == 0
        frames(gb, STAGGER + 4)
        assert phase(gb) == SU_WALK and SUMO.get(gb, "charges") == 0


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_tap_and_the_last_life(model):
    """His right edge at the tap (a step on the beat takes him there): a life; with the last one, TRY AGAIN."""
    with fight(model, C) as gb:
        quiet(gb)
        gb.write("lives", 1)
        gb.write("boss_x", SPOUT_X - R["width"] - 8)
        until(gb, lambda: state(gb) == LIFE_LOST, R["step"] + 4)
        until(gb, lambda: state(gb) == GS_STORY, 200)
        assert gb.mem("story_phase") == SP_FAIL and banner_text(gb, 1) == centred("TRY AGAIN")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_lost_life_keeps_the_meter_and_the_target(model):
    """The tap costs a life: he starts over at x 24, nothing in his hands; the meter and its target are kept (a half-filled
    meter of 5: 2 cups in); no entrance again."""
    with fight(model, C, entrance=True) as gb:
        quiet(gb)
        fill_meter(gb, 64)
        settled(gb)
        assert SUMO.get(gb, "cyc") == 5
        setx(gb, 56)
        hit_now(gb)
        hit_now(gb)
        gb.write("boss_x", SPOUT_X - R["width"])
        until(gb, lambda: state(gb) == LIFE_LOST, 4)
        until(gb, lambda: state(gb) == PLAYING, 200)
        frames(gb, 3)
        assert (gb.mem("boss_x"), gb.mem("boss_hp"), SUMO.get(gb, "cyc"), gb.mem("boss_hold"), gb.mem("lives")) == (
            START_X, 3, 5, 0, 2)
        assert hud(gb) == pints(5, 2) and phase(gb) == SU_WALK and SUMO.get(gb, "ent") == 0
        assert gb.mem("boss_cap") == CAP_ANY


# ---- the entrance ---------------------------------------------------------------------------------------------------
def ent_t(gb):
    e = SUMO.get(gb, "ent")
    return e - 2 if e >= 2 else None


def to_frame(gb, t):
    """Frame by frame (each checked at <= 10 sprites a line) to the moment the ritual has just drawn its frame t."""
    while ent_t(gb) != t:
        assert ent_t(gb) is None or ent_t(gb) <= t, (ent_t(gb), t)   # (a long frame's logic may run past the sample: t may have been passed by one)
        frames(gb, 1)
        if ent_t(gb) == t + 1:
            break


def salt_oam(gb):
    return [(o["y"], o["x"], o["tile"], o["flags"]) for o in (gb.oam()[26], gb.oam()[27]) if o["y"]]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_entrance_walks_in_and_stamps(model):
    """The first start: BS_JUMP + BP_HIDE (nobody on the bar), no topper, the intro held, nothing caught; at SE_IN he stands
    at the wall (x 0) and takes three heavy steps to x 24 (the thud each); the leg goes up (SHIKO), the stamps (STOMP) with
    the drum, the shake of the picture on the stamps' frames (SCY), the bow; then the intro's tail and the fight at x 24 with
    the engine's settings back (boss_cap, SCY 0)."""
    with fight(model, C, entrance=True) as gb:
        assert SUMO.get(gb, "ent") >= 1 and gb.mem("boss_state") == BS_ENTER and gb.mem("boss_xpose") == BP_HIDE
        assert gb.oam()[OAM_TOPPER]["y"] == 0
        for t in (3, SE_IN - 1):
            to_frame(gb, t)
            assert gb.mem("boss_state") == BS_ENTER and gb.mem("intro_timer") >= 89 and gb.mem("boss_x") == 0
            assert gb.mem("boss_cap") == 0 and gb.mem("boss_lim") == 0 and gb.mem("boss_hits") == 0
            assert gb.oam()[OAM_TOPPER]["y"] == 0 and gb.mem(SCY) == 0
            if t == 3:
                shakes, dons = sfx(gb, SFX_SHAKE), sfx(gb, SFX_DON)
                assert dons >= 1, "the drum at the start"
        to_frame(gb, SE_IN + 2)
        assert gb.mem("boss_state") == BS_ENTER and gb.mem("boss_x") == 0
        assert_body(gb, C, A, 0, BP_WALK)
        for k in (1, 2, 3):
            to_frame(gb, SE_IN + k * SE_STEP + 2)
            assert gb.mem("boss_x") == 8 * k and sfx(gb, SFX_SHAKE) == shakes + k, k
            assert_body(gb, C, A, 8 * k, BP_STOMP)
            assert gb.oam()[OAM_TOPPER]["y"] != 0
        to_frame(gb, SE_SALT + 2)
        assert_body(gb, C, A, 24, BP_SHIKO)
        assert gb.mem("boss_x") == 24
        to_frame(gb, SE_STAMP1 + 2)
        assert_body(gb, C, A, 24, BP_STOMP)
        assert sfx(gb, SFX_SHAKE) == shakes + 4 and sfx(gb, SFX_DON) == dons + 1
        scy1 = set()
        for t in range(SE_STAMP1 + 3, SE_STAMP1 + 8):
            to_frame(gb, t)
            scy1.add(gb.mem(SCY))
        assert scy1 == {0, 2}, "stamp 1 shakes the picture 2 px"
        to_frame(gb, SE_STAMP1 + 12)
        assert gb.mem(SCY) == 0 and gb.mem("boss_xpose") == BP_WALK
        to_frame(gb, SE_LEG2 + 2)
        assert_body(gb, C, A, 24, BP_SHIKO)
        to_frame(gb, SE_STAMP2 + 2)
        assert sfx(gb, SFX_SHAKE) == shakes + 5 and sfx(gb, SFX_DON) == dons + 2 and sfx(gb, SFX_KA) >= 2
        scy2 = set()
        for t in range(SE_STAMP2 + 3, SE_STAMP2 + 10):
            to_frame(gb, t)
            scy2.add(gb.mem(SCY))
        assert scy2 == {0, 3}, "stamp 2 shakes it 3 px"
        to_frame(gb, SE_BOW + 2)
        assert_body(gb, C, A, 24, BP_WALK)
        assert gb.mem("boss_lim") == 0, "still no catch"
        until(gb, lambda: SUMO.get(gb, "ent") == 0, 20)
        assert gb.mem(SCY) == 0 and gb.mem("boss_cap") == CAP_ANY and gb.mem("boss_state") == BS_WALK
        assert gb.mem("intro_timer") >= SE_TAIL - 3 and gb.mem("boss_x") == 24
        frames(gb, 3)
        assert salt_oam(gb) == []
        assert gb.mem("boss_lim") != 0 or gb.mem("intro_timer")
        quiet(gb)
        assert gb.mem("boss_x") == 24 and gb.mem("boss_hp") == 6 and gb.mem("boss_hits") == 0
        assert_body(gb, C, A, 24, BP_WALK)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_salt_flies_and_the_dust_rises(model):
    """OAM 26 / 27 (the perfect cue's and the coin's entries) carry the salt (OBJ_DUST's scatter tile, two grains arcing
    right of him) from frame SE_SALT, and the dust puffs (both feet, opening frames 0, 1, 2) at each stamp; nothing at
    other times. Goldens boss_sumo_salt (mid-toss) and boss_sumo_stamp (stamp 2's dust and shake)."""
    with fight(model, C, entrance=True) as gb:
        to_frame(gb, SE_SALT - 1)
        assert salt_oam(gb) == []
        to_frame(gb, SE_SALT + 10)
        salt = salt_oam(gb)
        assert len(salt) == 2 and all(t == 246 + 4 for _, _, t, _ in salt), salt
        assert all(x >= 24 + 40 + 8 for _, x, _, _ in salt), "right of him"
        ys = [o[0] for o in salt]
        top = 5 * 8 + 3 * B * 8 + 16
        assert all(top - 16 <= y <= top + 16 for y in ys), (ys, top)
        check_golden(gb, "boss_sumo_salt")
        to_frame(gb, SE_SALT + 19)
        assert len(salt_oam(gb)) >= 1, "the last grain still falls"
        to_frame(gb, SE_STAMP1 + 2)
        dust = salt_oam(gb)
        assert len(dust) == 2 and dust[0][3] & 0x20 and not dust[1][3] & 0x20, "one foot flipped"
        to_frame(gb, SE_STAMP2 + 6)
        t0 = {t for _, _, t, _ in salt_oam(gb)}
        to_frame(gb, SE_STAMP2 + 10)
        assert {t for _, _, t, _ in salt_oam(gb)} != t0, "the puff opens"
        check_golden(gb, "boss_sumo_stamp")
        to_frame(gb, SE_STAMP2 + 14)
        assert salt_oam(gb) == []


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_every_entrance_frame_keeps_to_ten_sprites_a_line(model):
    """Every game frame of the ritual and the intro after it (frames() checks each at <= 10 a line)."""
    with fight(model, C, entrance=True) as gb:
        for _ in range(START_FRAMES + 40):
            frames(gb, 1)
        assert SUMO.get(gb, "ent") == 0


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_player_cannot_pour_or_move_during_the_entrance(model):
    """Held at bar 0's tap as in Duke's: A and Down do nothing until the ritual is over."""
    with fight(model, C, entrance=True) as gb:
        to_frame(gb, 30)
        gb.hold("a")
        gb.press("down", 2)
        frames(gb, 20)
        gb.release("a")
        assert gb.mem("bar") == 0 and gb.mem("fill_timer") == 0 and gb.mem("boss_hits") == 0
        until(gb, lambda: SUMO.get(gb, "ent") == 0, START_FRAMES)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_retry_after_a_lost_life_has_no_entrance(model):
    with fight(model, C, entrance=True) as gb:
        quiet(gb)
        gb.write("boss_x", SPOUT_X - R["width"])
        until(gb, lambda: state(gb) == LIFE_LOST, 4)
        until(gb, lambda: state(gb) == PLAYING, 200)
        frames(gb, 3)
        assert SUMO.get(gb, "ent") == 0 and gb.mem("boss_state") == BS_WALK and gb.mem("boss_x") == START_X
        assert_body(gb, C, A, START_X, BP_WALK)
        assert gb.mem(SCY) == 0 and gb.mem("lives") == 2


@pytest.mark.parametrize("model", ["cgb"])
def test_boss_rush_starts_with_the_entrance_too(model):
    """BOSS RUSH, CHOOSE on the Sumo: the ritual runs, then the fight at x 24 with a meter of 6."""
    from test_rush import BUILT, booted, into_fight, tap, to_list, v7_image
    ram0 = v7_image([("ABC", 500)], story=2, step=1, story_tbl=[("STO", 900)])
    with booted(model, ram0) as gb:
        to_list(gb)
        for _ in range(BUILT.index(C)):
            tap(gb, "down")
        tap(gb, "a")
        into_fight(gb, entered=False)
        frames(gb, 4)
        assert gb.mem("boss_id") == C and SUMO.get(gb, "ent") >= 1 and gb.mem("boss_state") == BS_ENTER
        until(gb, lambda: SUMO.get(gb, "ent") == 0, START_FRAMES + 10)
        frames(gb, 2)
        assert gb.mem("boss_state") == BS_WALK and gb.mem("boss_x") == START_X
        assert gb.mem("boss_hp") == 6 and gb.mem("lives") == 3


@pytest.mark.parametrize("gap", [60, 100])
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_win_the_fight_by_pouring(model, gap):
    """Real pours on his bar, the bartender staying at the tap, a cup every `gap` frames at the quickest (60, 100): no life lost; every two
    arrivals of his empties >= empty_gap apart; he is rung out (the meter filled again and again, targets shrinking), the
    outro (gone), CHAPTER CLEAR, the POST_TEAHOUSE scene, the chapter saved. Reports the cups and the seconds."""
    with fight(model, C) as gb:
        quiet(gb)
        gb.write("next_arrival", 0)
        gb.write(gb.addr("next_arrival") + 1, 0)
        to_bar(gb, B)
        arrivals, seen, f = [], set(), 0
        clock = Clock(gb)
        t_start = 0
        while not SUMO.get(gb, "out") and gb.mem("boss_hp") and f < 7200:
            if gb.mem("boss_state") != BS_TELL and not mugs(gb, B, FULL) and gb.mem("fill_timer") == 0 and f - t_start >= gap:
                t_start = f
                pour(gb)
            else:
                frames(gb, 1)
            f = clock.now()
            for i, s, b, x in mugs(gb):
                if s == EMPTY and i not in seen:
                    seen.add(i)
                    arrivals.append((f + (TAP_X - x) * 2, False))
            seen &= {i for i, s, _, _ in mugs(gb, st=EMPTY)}
        print(f"BOT {model}: gap {gap}: {gb.mem('boss_hits')} cups, {clock.now() / 60:.1f} s, {SUMO.get(gb, 'cycles')} meters filled")
        assert gb.mem("lives") == 3, "no life lost: the bar was won"
        assert SUMO.get(gb, "cycles") >= 2 and gb.mem("boss_hits") <= 22
        arrivals_ok(sorted(arrivals), gb.mem("empty_gap"))
        clear_regulars(gb)
        frames(gb, 3)
        assert state(gb) == GS_STORY and gb.mem("story_phase") == SP_OUTRO and gb.mem("boss_state") == BS_OUTRO
        assert gb.mem("boss_xpose") == BP_HIDE
        gb.run(60)
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 120)
        gb.run(3)
        assert banner_text(gb, 1) == centred("CHAPTER CLEAR")
        run_until(gb, lambda: state(gb) == GS_STORY and gb.mem("story_scene") == post(C), 300)
        settle(gb)
        assert (gb.mem("boss_on"), gb.mem("story_progress")) == (0, C + 1)
