# docs/minigames_bosses.md 3.11: Leo the Lion, the jungle zoo's boss (src/boss_leo.c; art approved 2026-10-11, round 2:
# the patron lion scaled up, crowned). The fight follows the zoo's Last call: his row (32 px, step 80, push 8, gulp 30,
# hands 2, sip 60, meter 14) and his roar every 420 frames of walking: the tell (60 frames: the INHALE pose and "!!" in
# the column right of him; he stands), the roar (30 frames: the ROAR pose; every regular walker pushed back 16 px
# without a serve, every drinker in his minimum drink finishing now, his own held empty free to go: all of it within
# the fair-empties schedule), then he walks again. Every frame here is checked at <= 10 sprites a line.
import re

import pytest
from boss_common import (BP_HAPPY, BP_WALK, BS_OUTRO, BS_SPECIAL, BS_TELL, BS_WALK, Clock, EMPTY, FULL, Own, SP_FAIL,
                         SP_OUTRO, SPOUT_X, TAP_X, art, arrivals_ok, assert_body, bar_row, check_start, fight, frames,
                         hud, meter_tiles, mugs, play, pour, row, still_regulars, throw, to_bar, until)
from conftest import clear_regulars, ROOT, check_golden, logic_paused, venue
from test_flow import GS_STORY, LEVEL_CLEAR, LIFE_LOST, PLAYING, run_until, score, set_patron, state, tilemap_row
from test_story import banner_text, centred, post, settle, to_goal

pytestmark = pytest.mark.timeout(300)

C = 8                                   # the jungle zoo
R = row(C)
A = art("leo")
B = R["bar"]
BP_INHALE, BP_ROAR = 5, 6
SRC = (ROOT / "src" / "boss_leo.c").read_text()
EVERY, TELL, ROAR, PUSH = (int(re.search(rf"#define {n}\s+(\d+)", SRC).group(1)) for n in (
    "LEO_EVERY", "LEO_TELL", "LEO_ROAR", "LEO_PUSH"))
LP_WALK, LP_TELL, LP_ROAR = range(3)
LEO = Own("leo")
BANG = 246
WALKING, PUSHED, DRINKING = 1, 2, 3
ENTRY_X = 16
WALL = venue("zoo")["bar_map"]


def phase(gb):
    return LEO.get(gb, "phase")


def bang_shown(gb):
    """The "!!" in the column right of him (top 246, bottom 247), and the venue's wall everywhere else right of him."""
    y, k = bar_row(R), gb.mem("boss_x") // 8 + 4
    top, bottom = tilemap_row(gb, y, 0, 20), tilemap_row(gb, y + 1, 0, 20)
    if (top[k], bottom[k]) == (BANG, BANG + 1):
        return True
    assert (top[k], bottom[k]) == (WALL[k], WALL[20 + k]), (k, top, bottom)
    return False


def quiet(gb):
    still_regulars(gb)
    play(gb)


def test_his_row_and_art():
    """Spec 3.2 / 3.11's numbers (meter 14) and timings, the banner lines of spec 7, his approved art (the patron lion
    with a crown) with INHALE and ROAR (extra poses 5 and 6) and the "!!" block (BANG, 8x16) of his own."""
    assert {k: R[k] for k in ("width", "x", "bar", "step", "push", "gulp", "hands", "sip", "meter", "hat")} == dict(
        width=32, x=16, bar=2, step=80, push=8, gulp=30, hands=2, sip=60, meter=14, hat=6)
    assert (R["line1"], R["line2"]) == ("LEO THE LION", "14 COCONUTS NO FEAR")
    assert A["poses"] == ["WALK", "STOMP", "GULP", "WINCE", "HAPPY", "INHALE", "ROAR"]
    assert (EVERY, TELL, ROAR, PUSH) == (420, 60, 30, 16) and TELL >= 45
    assert len(A["tiles"]) == 32 and len(A["pairs"]) <= 30
    assert "; Art: approved design" in (ROOT / "assets/art/boss/leo.txt").read_text()
    assert not (ROOT / "assets/art/approved/boss_leo.txt").exists()
    assert "boss_leo" not in (ROOT / "assets/art/approved/README.md").read_text()
    assert not re.search(r"^(?:static\s+)?u?int(?:8|16)_t\s+\w+\s*(?:[;,=]|\[)", SRC, re.M), "no WRAM of his own"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_fight_follows_the_last_call(model):
    """After the zoo's Last call: BOSS and his lines; Leo on bar 2 at x 16 (his tiles, palettes, the "!!" at BG
    246-247), the meter of 14 (all 7 HUD tiles), his crown as the topper. Golden boss_leo: walking, a coconut on its
    way."""
    with fight(model, C, banner=True) as gb:
        assert banner_text(gb, 2) == centred(R["line1"]) and banner_text(gb, 3) == centred(R["line2"])
        to_goal(gb)
        gb.run(2)
        check_start(gb, C, A, model)
        assert bytes(gb.read(0x8000 + BANG * 16, 32)) == bytes(A["tiles"])
        assert hud(gb) == meter_tiles(14, 14)
        assert (phase(gb), gb.mem16("boss_special_t")) == (LP_WALK, EVERY)
        assert not bang_shown(gb)
        quiet(gb)
        throw(gb, B, 100)
        frames(gb, 10)
        check_golden(gb, "boss_leo")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_roar_tell_and_timing(model):
    """420 walking frames, then the tell: 60 frames of INHALE with "!!" right of him, he stands (no stomp); the roar:
    30 frames of ROAR (the SFX), he stands; then the "!!" goes, he walks and the next roar is 420 frames away. Golden
    boss_leo_roar (the roar, the "!!" up)."""
    with fight(model, C) as gb:
        quiet(gb)
        clock = Clock(gb)
        until(gb, lambda: clock.now() and phase(gb) == LP_TELL, EVERY + 10)
        t_tell = clock.now()
        assert EVERY - 2 <= t_tell <= EVERY + 2, t_tell
        frames(gb, 2)
        assert gb.mem("boss_state") == BS_TELL and bang_shown(gb)
        x = gb.mem("boss_x")
        assert_body(gb, C, A, x, BP_INHALE)
        shakes = gb.read("sfx_count", 9)[8]
        until(gb, lambda: clock.now() and phase(gb) == LP_ROAR, TELL + 4)
        t_roar = clock.now()
        assert TELL - 2 <= t_roar - t_tell <= TELL + 2 and gb.mem("boss_x") == x, "he stands through the tell"
        frames(gb, 2)
        assert gb.mem("boss_state") == BS_SPECIAL and bang_shown(gb) and LEO.get(gb, "roars") == 1
        assert gb.read("sfx_count", 9)[8] == shakes + 1, "the roar's sound"
        assert_body(gb, C, A, x, BP_ROAR)
        check_golden(gb, "boss_leo_roar")
        until(gb, lambda: clock.now() and phase(gb) == LP_WALK, ROAR + 4)
        assert ROAR - 2 <= clock.now() - t_roar <= ROAR + 2 and gb.mem("boss_x") == x, "he stands through the roar"
        frames(gb, 2)
        assert not bang_shown(gb) and gb.mem("boss_state") == BS_WALK
        assert_body(gb, C, A, x, BP_WALK)
        assert EVERY - 4 <= gb.mem16("boss_special_t") <= EVERY
        until(gb, lambda: gb.mem("boss_x") != x, R["step"] + 2)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_push_back_in_the_tell_takes_the_bang_along(model):
    """A hit during the tell: the GULP / WINCE poses, the push-back 8 px, the "!!" moving with him (nothing left at its
    old place), then the INHALE pose again until the roar."""
    with fight(model, C) as gb:
        quiet(gb)
        until(gb, lambda: gb.mem("boss_x") >= 32, 2 * R["step"] + 4)
        gb.write("boss_hook", 1)
        until(gb, lambda: phase(gb) == LP_TELL, 4)
        frames(gb, 2)
        x = gb.mem("boss_x")
        assert bang_shown(gb)
        throw(gb, B, x + 40)
        until(gb, lambda: gb.mem("boss_hits") == 1, 30)
        until(gb, lambda: gb.mem("boss_x") == x - 8, 20)
        frames(gb, 2)
        assert bang_shown(gb), "the !! moved with him"
        until(gb, lambda: gb.mem("boss_state") == BS_TELL and not gb.mem("boss_push"), 40)
        frames(gb, 2)
        assert phase(gb) == LP_TELL and bang_shown(gb)
        assert_body(gb, C, A, x - 8, BP_INHALE, hold=0)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_roar_pushes_walkers_back_without_a_serve(model):
    """Walkers on bars 0, 1 and 3 (one 8 px from the left end): the roar pushes each back 16 px at the push-back's
    1 px a frame (8 px for the one near the end: never past ENTRY_X, so nobody is served), no score, no served count, no
    mug; then they walk on."""
    with fight(model, C) as gb:
        quiet(gb)
        with logic_paused(gb):
            gb.write("spawn_timer", 0xFF)
            gb.write(gb.addr("spawn_timer") + 1, 0x7F)          # (no new regular in the way)
            before = set(i for i, s in enumerate(gb.read("patron_state", 16)) if s)
            for b, x in ((0, 60), (1, 24), (3, 100)):
                set_patron(gb, b, x)
        slots = [i for i, s in enumerate(gb.read("patron_state", 16)) if s and i not in before]
        assert len(slots) == 3
        x0 = {i: gb.read("patron_x", 16)[i] for i in slots}
        sc, served = score(gb), gb.mem("served")
        gb.write("boss_hook", 1)
        until(gb, lambda: phase(gb) == LP_ROAR, TELL + 4)
        frames(gb, 1)
        st = gb.read("patron_state", 16)
        assert all(st[i] == PUSHED for i in slots) and LEO.get(gb, "pushed") >= 3
        frames(gb, PUSH + 4)
        st, px, mug = gb.read("patron_state", 16), gb.read("patron_x", 16), gb.read("patron_mug", 16)
        for i in slots:
            assert px[i] == max(x0[i] - PUSH, ENTRY_X), (i, x0[i], px[i])
            assert st[i] == WALKING and mug[i] == 255, "walking on, no mug"
        assert (score(gb), gb.mem("served")) == (sc, served), "no serve"
        assert LEO.get(gb, "mask") == 0


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_roar_hurries_four_drinkers_within_the_fair_schedule(model):
    """Four regulars drinking (two on bar 0, one each on bars 1 and 3) and an empty in Leo's hands when he roars: each
    drinker finishes at once and every empty (theirs and his) goes only when the fair-empties schedule lets it, so
    every two arrive at the tap end >= empty_gap apart; all of them go long before their drinks would have ended."""
    with fight(model, C) as gb:
        quiet(gb)
        with logic_paused(gb):
            gb.write("spawn_timer", 0xFF)
            gb.write(gb.addr("spawn_timer") + 1, 0x7F)
            before = set(i for i, s in enumerate(gb.read("patron_state", 16)) if s)
            for b, x in ((0, 40), (0, 88), (1, 64), (3, 72)):
                set_patron(gb, b, x)
        slots = [i for i, s in enumerate(gb.read("patron_state", 16)) if s and i not in before]
        throw(gb, B, 70)                                          # Leo catches one: an empty in his hands
        until(gb, lambda: gb.mem("boss_hits") == 1, 30)
        gb.write("boss_hook", 1)
        frames(gb, 2)
        for b, x in ((0, 40), (0, 88), (1, 64), (3, 72)):
            throw(gb, b, x + 30)
        until(gb, lambda: all(gb.read("patron_state", 16)[i] == DRINKING for i in slots), 60)
        assert phase(gb) == LP_TELL and gb.mem("boss_hold") == 1
        until(gb, lambda: phase(gb) == LP_ROAR, TELL + 4)
        clock = Clock(gb)
        assert LEO.get(gb, "hurried") == 4
        gap = gb.mem("empty_gap")
        arrivals, seen = [], set()
        while len(arrivals) < 5 and clock.now() < 6 * gap + 200:
            frames(gb, 1)
            f = clock.now()
            for i, s, b, x in mugs(gb, st=EMPTY):
                if i not in seen:
                    seen.add(i)
                    arrivals.append((f + (TAP_X - x) * 2, b == B))
                    with logic_paused(gb):                       # (gone: no break at the tap end, no life)
                        gb.write(gb.addr("mug_state") + i, 0)
                        gb.write("mugs_live", gb.mem("mugs_live") - 1)
        assert len(arrivals) == 5, arrivals
        arrivals.sort()
        arrivals_ok(arrivals, gap)
        assert gb.mem("lives") == 3 and gb.mem("boss_hold") == 0
        assert arrivals[0][0] < 90 + 200, "the first empty went long before a 90-frame drink would have ended"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_life_lost_in_the_tell_ends_the_roar(model):
    """His right edge at the tap during the tell: a life; after the freeze he is back at x 16 walking, no "!!", the
    next roar 420 frames away, his meter kept."""
    with fight(model, C) as gb:
        quiet(gb)
        gb.write("boss_hook", 1)
        until(gb, lambda: phase(gb) == LP_TELL, 4)
        frames(gb, 2)
        gb.write("boss_x", SPOUT_X - R["width"])
        until(gb, lambda: state(gb) == LIFE_LOST, 4)
        until(gb, lambda: state(gb) == PLAYING, 200)
        frames(gb, 3)
        assert (phase(gb), gb.mem("boss_x"), gb.mem("boss_hp"), gb.mem("lives")) == (LP_WALK, R["x"], 14, 2)
        assert not bang_shown(gb) and gb.mem16("boss_special_t") == EVERY
        assert_body(gb, C, A, R["x"], BP_WALK)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_last_life_lost_is_try_again(model):
    """The last life at the tap: TRY AGAIN (the venue restarts at its Opening, the next fight with a full meter)."""
    with fight(model, C) as gb:
        quiet(gb)
        gb.write("lives", 1)
        gb.write("boss_x", SPOUT_X - R["width"])
        until(gb, lambda: state(gb) == LIFE_LOST, 4)
        until(gb, lambda: state(gb) == GS_STORY, 200)
        assert gb.mem("story_phase") == SP_FAIL and banner_text(gb, 1) == centred("TRY AGAIN")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_win_the_fight_by_pouring(model):
    """Real pours on his bar through a roar, the bartender staying at the tap: 14 coconuts and he is satisfied; no
    life lost; every two arrivals of the empties >= empty_gap apart; the outro (the purr: HAPPY), no "!!"; CHAPTER
    CLEAR, the POST_ZOO scene, the chapter saved."""
    with fight(model, C) as gb:
        quiet(gb)
        to_bar(gb, B)
        arrivals, seen, f, phases = [], set(), 0, set()
        clock = Clock(gb)
        while gb.mem("boss_hp") and f < 6000:
            if gb.mem("boss_hold") + len(mugs(gb, B, FULL)) < R["hands"]:
                pour(gb)
            else:
                frames(gb, 1)
            f = clock.now()
            phases.add(phase(gb))
            for i, s, b, x in mugs(gb):
                if s == EMPTY and i not in seen:
                    seen.add(i)
                    arrivals.append((f + (TAP_X - x) * 2, False))
            seen &= {i for i, s, _, _ in mugs(gb, st=EMPTY)}
        assert gb.mem("boss_hits") == 14 and gb.mem("lives") == 3
        assert LP_ROAR in phases, "the fight went through a roar"
        arrivals_ok(sorted(arrivals), gb.mem("empty_gap"))
        clear_regulars(gb)
        frames(gb, 3)
        assert state(gb) == GS_STORY and gb.mem("story_phase") == SP_OUTRO and gb.mem("boss_state") == BS_OUTRO
        gb.run(60)
        assert_body(gb, C, A, gb.mem("boss_x"), BP_HAPPY)
        assert not bang_shown(gb)
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 120)
        gb.run(3)
        assert banner_text(gb, 1) == centred("CHAPTER CLEAR")
        run_until(gb, lambda: state(gb) == GS_STORY and gb.mem("story_scene") == post(C), 300)
        settle(gb)
        assert (gb.mem("boss_on"), gb.mem("story_progress")) == (0, C + 1)
