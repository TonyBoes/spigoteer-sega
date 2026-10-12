# docs/minigames_bosses.md 3.9: the Sumo, the teahouse's boss (src/boss_sumo.c; art approved 2026-10-11, look 2 round 2).
# The fight follows the teahouse's Last call: his row (40 px, step 96 frames on the beat, push 0 single / 8 chained,
# gulp 0, hands 2, sip 90, meter 8); he steps on the teahouse tune's beat (music_frames; his own clock with the music
# off); a hit always counts and pushes him only within 80 frames of the previous one (the chain, the HUD face blinking);
# a charge every 480 frames of walking (the SHIKO stamp for 60 frames, then 24 px in 12 frames), called off by a hit in
# the stamp (the HMPH pose). Every frame here is checked at <= 10 sprites a line.
import re

import pytest
from boss_common import (BP_GULP, BP_HAPPY, BP_STOMP, BP_WALK, BS_OUTRO, BS_SPECIAL, BS_TELL, BS_WALK, Clock, EMPTY,
                         FULL, HUD_BG, Own, SP_FAIL, SP_OUTRO, SPOUT_X, TAP_X, art, arrivals_ok, assert_body, check_start,
                         fight, frames, hud, meter_tiles, mugs, play, pour, row, still_regulars, throw, to_bar, until)
from conftest import ROOT, check_golden, logic_paused
from test_flow import GS_STORY, LEVEL_CLEAR, LIFE_LOST, PLAYING, run_until, state, tilemap_row
from test_story import banner_text, centred, post, settle, to_goal

pytestmark = pytest.mark.timeout(300)

C = 7                                   # the teahouse
R = row(C)
A = art("sumo")
B = R["bar"]
BP_SHIKO, BP_HMPH = 5, 6
SRC = (ROOT / "src" / "boss_sumo.c").read_text()
CHAIN, PUSH, HIT_POSE, EVERY, TELL, HOP, HOPS, HMPH, BLINK = (int(re.search(rf"#define {n}\s+(\d+)", SRC).group(1))
                                                              for n in ("SUMO_CHAIN", "SUMO_PUSH", "SUMO_HIT_POSE",
                                                                        "SUMO_EVERY", "SUMO_TELL", "SUMO_HOP",
                                                                        "SUMO_HOPS", "SUMO_HMPH", "SUMO_BLINK"))
SU_WALK, SU_TELL, SU_CHARGE, SU_HMPH = range(4)
SUMO = Own("sumo")
SONGS = (ROOT / "tools" / "songs.py").read_text()
SAKURA_TEMPO = int(re.search(r'song\("sakura", (\d+),', SONGS).group(1))
BLANK_HUD = int(re.search(r"#define TILE_HUD_BLANK (\d+)", (ROOT / "build" / "art.h").read_text()).group(1))


def phase(gb):
    return SUMO.get(gb, "phase")


def quiet(gb):
    still_regulars(gb)
    play(gb)


def hit_now(gb):
    """A full mug on his catch line: caught on the second game frame (frame-exact)."""
    gb.write("boss_hold", 0)
    with logic_paused(gb):
        lim = gb.mem("boss_lim")
        assert lim
    throw(gb, B, lim)
    hits = gb.mem("boss_hits")
    frames(gb, 1)
    assert gb.mem("boss_hits") == hits, "the mug moves first (2 px a frame)"
    frames(gb, 1)
    assert gb.mem("boss_hits") == hits + 1, "caught on the second frame"


def walked_to(gb, x):
    """Wait for his steps until he stands at x or beyond (walking)."""
    until(gb, lambda: gb.mem("boss_x") >= x and gb.mem("boss_state") == BS_WALK, 6 * R["step"])


def test_his_row_and_art():
    """Spec 3.2 / 3.9's numbers (the step is the teahouse tune's bar: 8 rows of 12 frames, his steps land on the
    beat), the banner lines of spec 7, his approved art with SHIKO and HMPH (extra poses 5 and 6), no WRAM of his own."""
    assert {k: R[k] for k in ("width", "x", "bar", "step", "push", "gulp", "hands", "sip", "meter", "hat")} == dict(
        width=40, x=16, bar=1, step=96, push=0, gulp=0, hands=2, sip=90, meter=8, hat=16)
    assert R["step"] % SAKURA_TEMPO == 0 and (R["step"] - R["step"] // 4) % SAKURA_TEMPO == 0, "whole rows (HARD too)"
    assert (R["line1"], R["line2"]) == ("THE CHAMPION", "KEEP THE TEA FLOWING")
    assert A["poses"] == ["WALK", "STOMP", "GULP", "WINCE", "HAPPY", "SHIKO", "HMPH"]
    assert (CHAIN, PUSH, EVERY, TELL, HOP * HOPS, 8 * HOPS) == (80, 8, 480, 60, 12, 24) and TELL >= 45
    assert len(A["pairs"]) <= 30
    assert "; Art: approved design" in (ROOT / "assets/art/boss/sumo.txt").read_text()
    assert not (ROOT / "assets/art/approved/boss_sumo.txt").exists()
    assert "boss_sumo" not in (ROOT / "assets/art/approved/README.md").read_text()
    assert not re.search(r"^(?:static\s+)?u?int(?:8|16)_t\s+\w+\s*(?:[;,=]|\[)", SRC, re.M), "no WRAM of his own"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_fight_follows_the_last_call(model):
    """After the teahouse's Last call: BOSS and his lines; the Sumo on bar 1 at x 16 (his tiles, palettes), the meter
    of 8, his topknot as the topper; the engine's own stomp timer off (boss_step 0, his period 96). Golden boss_sumo:
    walking, a cup on its way."""
    with fight(model, C, banner=True) as gb:
        assert banner_text(gb, 2) == centred(R["line1"]) and banner_text(gb, 3) == centred(R["line2"])
        to_goal(gb)
        gb.run(2)
        check_start(gb, C, A, model)
        assert (gb.mem("boss_step"), SUMO.get(gb, "period"), phase(gb)) == (0, R["step"], SU_WALK)
        assert gb.mem16("boss_special_t") == EVERY
        quiet(gb)
        throw(gb, B, 100)
        frames(gb, 10)
        check_golden(gb, "boss_sumo")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_steps_land_on_the_beat(model):
    """He steps 8 px (the STOMP pose) every 96 frames, each step on the same frame of the tune's bar: music_frames at
    each step is the same modulo 96; unhit, he reaches the tap after 10 steps. With the music off: every 96 frames by
    his own clock."""
    with fight(model, C) as gb:
        quiet(gb)
        assert gb.mem("sound_on") == 1
        seen = []
        x = gb.mem("boss_x")
        while len(seen) < 4:
            frames(gb, 1)
            if gb.mem("boss_x") != x:
                assert gb.mem("boss_x") == x + 8
                x = gb.mem("boss_x")
                seen.append(gb.mem16("music_frames"))
                frames(gb, 1)
                assert_body(gb, C, A, x, BP_STOMP)
        assert len({(m - 1) % R["step"] for m in seen}) == 1, seen
        assert all(b - a == R["step"] for a, b in zip(seen, seen[1:])), seen
        assert (seen[0] - 1) % R["step"] <= 1, "on the bar's first row"
        gb.write("sound_on", 0)
        gb.write(gb.addr("boss_special_t") + 1, 0x7F)    # (no charge in the way: his stomps are the steps counted)
        clock = Clock(gb)
        steps = []
        while len(steps) < 3:
            frames(gb, 1)
            if gb.mem("boss_x") != x:
                x = gb.mem("boss_x")
                steps.append(clock.now())
        assert [b - a for a, b in zip(steps, steps[1:])] == [R["step"]] * 2, steps


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_single_hit_counts_but_does_not_push(model):
    """A first hit: meter -1, one empty held, the hit pose (GULP) for a moment, but no push and no stop: he keeps his
    x and steps on the next beat."""
    with fight(model, C) as gb:
        quiet(gb)
        walked_to(gb, 32)
        x = gb.mem("boss_x")
        hit_now(gb)
        assert (gb.mem("boss_hp"), gb.mem("boss_hold"), gb.mem("boss_push")) == (7, 1, 0)
        assert (SUMO.get(gb, "singles"), SUMO.get(gb, "chained"), SUMO.get(gb, "chain")) == (1, 0, 1)
        frames(gb, 1)
        assert_body(gb, C, A, x, BP_GULP)
        assert gb.mem("boss_state") == BS_WALK, "no gulp: he keeps going"
        frames(gb, 20)
        assert gb.mem("boss_x") >= x
        assert hud(gb)[1:] == meter_tiles(7, 8)[1:]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_chain(model):
    """A hit 80 frames after the last one is chained: meter -1 and a push 8 px back (WINCE); one 81 frames after is
    not: the chain had run out. While a chain is live his HUD face blinks (8 frames on, 8 off); after it, it stays."""
    with fight(model, C) as gb:
        quiet(gb)
        walked_to(gb, 48)
        hit_now(gb)                                           # the first: single
        until(gb, lambda: SUMO.get(gb, "chain") == 8 + 1, 20)
        assert hud(gb)[0] == BLANK_HUD, "blinking"
        until(gb, lambda: SUMO.get(gb, "chain") == 16 + 1, 20)
        assert hud(gb)[0] == HUD_BG
        until(gb, lambda: SUMO.get(gb, "chain") == CHAIN - 1, CHAIN)   # (the catch comes 2 frames on: the 80th)
        x = gb.mem("boss_x")
        hit_now(gb)                                           # 80 frames on: chained
        assert (SUMO.get(gb, "chained"), gb.mem("boss_hp"), gb.mem("boss_push")) == (1, 6, PUSH)
        until(gb, lambda: gb.mem("boss_x") == x - 8 and not gb.mem("boss_push"), 20)
        until(gb, lambda: SUMO.get(gb, "chain") == CHAIN + 1, CHAIN + 4)   # 81 frames since the chained hit
        frames(gb, 2) if False else None
        assert hud(gb)[0] == HUD_BG, "the chain ran out: the face stays"
        hit_now(gb)
        assert (SUMO.get(gb, "singles"), SUMO.get(gb, "chained"), gb.mem("boss_hp"), gb.mem("boss_push")) == (
            2, 1, 5, 0)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_charge(model):
    """480 walking frames, then the stamp: 60 frames of SHIKO, he stands; then the charge: 24 px in 12 frames (three
    8 px hops); then he walks on the beat again and the next charge is 480 frames away. Golden boss_sumo_shiko (the
    tell)."""
    with fight(model, C) as gb:
        quiet(gb)
        clock = Clock(gb)
        until(gb, lambda: clock.now() and phase(gb) == SU_TELL, EVERY + 10)
        t_tell = clock.now()
        assert EVERY - 2 <= t_tell <= EVERY + 2, t_tell
        frames(gb, 2)
        x = gb.mem("boss_x")
        assert gb.mem("boss_state") == BS_TELL
        assert_body(gb, C, A, x, BP_SHIKO)
        frames(gb, 20)
        check_golden(gb, "boss_sumo_shiko")
        until(gb, lambda: clock.now() and phase(gb) == SU_CHARGE, TELL + 4)
        t_charge = clock.now()
        assert TELL - 2 <= t_charge - t_tell <= TELL + 2 and gb.mem("boss_x") == x, "he stands through the stamp"
        until(gb, lambda: clock.now() and phase(gb) == SU_WALK, 20)
        assert HOP * HOPS - 2 <= clock.now() - t_charge <= HOP * HOPS + 2
        assert gb.mem("boss_x") == x + 8 * HOPS and SUMO.get(gb, "charges") == 1
        assert gb.mem("boss_state") == BS_WALK and EVERY - 4 <= gb.mem16("boss_special_t") <= EVERY


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_hit_in_the_stamp_calls_the_charge_off(model):
    """A hit during the stamp: the charge is off (the HMPH pose for 30 frames, he stands), the hit counts; then he walks
    and the next charge is 480 frames away; no charge happened."""
    with fight(model, C) as gb:
        quiet(gb)
        gb.write("boss_hook", 1)
        until(gb, lambda: phase(gb) == SU_TELL, 4)
        frames(gb, 10)
        x = gb.mem("boss_x")
        hit_now(gb)
        assert (phase(gb), SUMO.get(gb, "cancels"), gb.mem("boss_hp")) == (SU_HMPH, 1, 7)
        frames(gb, 1)
        assert gb.mem("boss_state") == BS_SPECIAL
        assert_body(gb, C, A, x, BP_HMPH)
        until(gb, lambda: phase(gb) == SU_WALK, HMPH + 4)
        assert gb.mem("boss_x") == x and SUMO.get(gb, "charges") == 0
        assert EVERY - 4 <= gb.mem16("boss_special_t") <= EVERY
        frames(gb, TELL + 20)
        assert phase(gb) == SU_WALK and SUMO.get(gb, "charges") == 0


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_full_hands_let_the_third_cup_pass(model):
    """Two quick cups (chained) fill his hands (2, sip 90): the third passes him and breaks at the left end (a life); he
    starts over at x 16 with his meter kept."""
    with fight(model, C) as gb:
        quiet(gb)
        walked_to(gb, 32)
        hit_now(gb)
        throw(gb, B, gb.mem("boss_lim") + 1)
        until(gb, lambda: gb.mem("boss_hits") == 2, 4)
        assert gb.mem("boss_hold") == 2 and gb.mem("boss_lim") == 0
        throw(gb, B, 100)
        until(gb, lambda: state(gb) == LIFE_LOST, 120)
        until(gb, lambda: state(gb) == PLAYING, 200)
        frames(gb, 3)
        assert (gb.mem("boss_x"), gb.mem("boss_hp"), gb.mem("boss_hold"), gb.mem("lives")) == (R["x"], 6, 0, 2)
        assert hud(gb)[0] == HUD_BG and phase(gb) == SU_WALK


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
def test_win_the_fight_by_pouring(model):
    """Real pours on his bar, the bartender staying at the tap: the 8 cups and he is satisfied; no life lost; some hits
    chained; every two arrivals of his empties >= empty_gap apart; the outro (HAPPY), the face back on the HUD;
    CHAPTER CLEAR, the POST_TEAHOUSE scene, the chapter saved."""
    with fight(model, C) as gb:
        quiet(gb)
        to_bar(gb, B)
        # (the bot pours a cup about every 100 frames, a hair slower than his sip 90 + the 50-frame flight, so it
        #  chains rarely: 12 cups out-lasted the pins, so he is 8 (owner decision); this shows 8 is beatable)
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
        assert gb.mem("boss_hits") == 8 and gb.mem("lives") == 3
        assert SUMO.get(gb, "chained") >= 1
        arrivals_ok(sorted(arrivals), gb.mem("empty_gap"))
        frames(gb, 1)
        assert state(gb) == GS_STORY and gb.mem("story_phase") == SP_OUTRO and gb.mem("boss_state") == BS_OUTRO
        gb.run(60)
        assert_body(gb, C, A, gb.mem("boss_x"), BP_HAPPY)
        assert hud(gb)[0] == HUD_BG
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 120)
        gb.run(3)
        assert banner_text(gb, 1) == centred("CHAPTER CLEAR")
        run_until(gb, lambda: state(gb) == GS_STORY and gb.mem("story_scene") == post(C), 300)
        settle(gb)
        assert (gb.mem("boss_on"), gb.mem("story_progress")) == (0, C + 1)
