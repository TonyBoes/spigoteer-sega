# D3 (docs/minigames_bosses.md 4.3): LOG ROLL's leaping fish, the hop that dodges them, and the living Sasquatch (src/lr.c). The base game's tests stay in
# tests/test_mg_logroll.py (they switch the fish off with fish_in = 65000 where they model the log alone).
import re

import pytest
from conftest import check_golden, hold_stage_anim, logic_paused
from test_mg import MG_RESULT, frames, lines, to_play, until
from test_mg_logroll import (ART, BASE_Y, CLEAR, DROPS, FISH_FIRST, FISH_LAST, FLY, GAP0, HALF, HOP_END, HOP_LEN, KICK, LAND, LAYOUT, LR_C,
                             LS_RUN, LS_WATER, ONE, OAM_DROPS, OAM_FISH, OAM_RING, OAM_SPIG, OAM_SQ, PTS_DODGE, PTS_SEC, RAMP, SPIG_CX, SQ_CX, SQ_END,
                             SQ_LOG, SQ_SWIM, SQ_SWIM_ST, SQ_UP_LEN, STUN, TOPPLE, WARN, S_FLIPX, OBJ_DANCER, calm, finish, log_roll, oam, otile,
                             poke, run_until_state, sfx, shot, snap, tap, to_playing)  # noqa: F401

pytestmark = pytest.mark.timeout(900)

SFX_FILL, SFX_COIN, SFX_WHOOSH, SFX_BREAK, SFX_LAUNCH = 1, 6, 13, 4, 2
HOP_H = [t * (36 - t) // 9 for t in range(37)]
ARC = [round(28 * 4 * k * (48 - k) / 48 ** 2) for k in range(48)]
assert [int(x) for x in re.search(r"fish_arc\[LR_FLY\] = \{(.*?)\}", LR_C, re.S).group(1).split(",")] == ARC
assert [int(x) for x in re.search(r"hop_h\[LR_HOP_LEN \+ 1\] = \{(.*?)\}", LR_C, re.S).group(1).split(",")] == HOP_H
assert KICK == 262144


def look(gb):
    """The state and the OAM of one whole game frame (the paused frame the DMA catches up in)."""
    with logic_paused(gb):
        return snap_nopause(gb), [oam(gb, i) for i in range(OAM_RING + 2)]


def snap_nopause(gb):
    from test_mg_logroll import lr
    return lr(gb)


def leap(gb, tgt=0, direction=-1, dodge=0):
    """A calm log (no push, no input), him on it and standing, and a fish whose ripples begin now (the side and target given)."""
    calm(gb)
    gb.write("mg_timer", 2000 & 255)                  # (the clock does not run out under a long series of leaps)
    gb.write(gb.addr("mg_timer") + 1, 2000 >> 8)
    x0 = (SQ_CX - HALF) if tgt else (SPIG_CX - HALF if direction > 0 else SPIG_CX + HALF)
    poke(gb, fish_t=1, fish_tgt=tgt, fish_dir=direction, fish_x0=x0, fish_done=0, sq_dodge=dodge, fish_in=65000, st=LS_RUN, stun=0, hop_t=0,
         sq_hop=0, fall_t=0, s60=0)


def sq_frame(o):
    return (o[OAM_SQ]["tile"] - OBJ_DANCER) // 8      # the dance frame f's tiles start at OBJ_DANCER + 8 f


def run_leap(gb, limit=260):
    """(state, OAM) for each frame until the fish is gone."""
    rows = []
    for _ in range(limit):
        s, o = look(gb)
        rows.append((s, o))
        if s["fish_t"] == 0 and len(rows) > 3:
            break
        frames(gb, 1)
    return rows


def hidden(o, *idx):
    return all(o[i]["y"] == 0 for i in idx)


FISH, RING = (OAM_FISH, OAM_FISH + 1), (OAM_RING, OAM_RING + 1)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("direction", [-1, 1])
def test_a_leap_is_told_by_ripples_then_arcs_across_the_log_then_a_ring_marks_the_landing(model, direction):
    """40 frames of ripple rings at the launch point, then 48 frames of a flat arc at 2 px a frame (the fish's centre on the table's arc over the
    water line, rise / flat / fall frames, x-flipped when it flies right, OBJ palette 3 on CGB), whoosh at the leap, then a growing ring where it
    lands for 12 frames; one entry pair for the fish, one for the ring; then nothing."""
    with log_roll(model) as gb:
        to_playing(gb)
        leap(gb, 0, direction)
        x0 = SPIG_CX - HALF if direction > 0 else SPIG_CX + HALF
        fill0, whoosh0 = sfx(gb, SFX_FILL), sfx(gb, SFX_WHOOSH)
        seen = {}
        for _ in range(WARN + FLY + LAND + 6):
            s, o = look(gb)
            if s["fish_t"] == 0 and seen:
                break
            seen[s["fish_t"]] = (s, o)
            frames(gb, 1)
        assert sfx(gb, SFX_WHOOSH) == whoosh0 + 1 and sfx(gb, SFX_FILL) == fill0, "the leap's whoosh (the bubbling belongs to the schedule)"
        ring_e = [otile(e) for e in ART["ring_e"]]
        fish_e = [otile(e) for e in ART["fish_e"]]
        for t in range(2, WARN + 1):                                      # the ripples: a ring at the launch point, no fish
            s, o = seen[t]
            assert (o[OAM_RING]["x"], o[OAM_RING + 1]["x"], o[OAM_RING]["y"]) == (x0, x0 + 8, BASE_Y - 4 + 16), t
            assert o[OAM_RING]["tile"] in ring_e[0::2] and o[OAM_RING + 1]["tile"] in ring_e[1::2], t
            assert hidden(o, *FISH), t
        assert len({seen[t][1][OAM_RING]["tile"] for t in range(2, WARN + 1)}) == 3, "the ring expands and repeats"
        for k in range(FLY):                                              # the leap
            s, o = seen[WARN + 1 + k]
            cx = x0 + direction * 2 * k
            fl, fr = o[OAM_FISH], o[OAM_FISH + 1]
            assert (fl["x"], fr["x"]) == (cx, cx + 8), k
            assert fl["y"] == fr["y"] == BASE_Y - ARC[k] - 8 + 16, k
            rf = 0 if k < 16 else 1 if k < 32 else 2
            want = (fish_e[2 * rf + 1], fish_e[2 * rf]) if direction > 0 else (fish_e[2 * rf], fish_e[2 * rf + 1])
            assert (fl["tile"], fr["tile"]) == want, k
            assert bool(fl["prop"] & S_FLIPX) == (direction > 0), k
            if model == "cgb":
                assert fl["prop"] & 7 == 3 and fr["prop"] & 7 == 3
            assert hidden(o, *RING), "no ring while it flies"
        assert max(ARC) == 28
        land = x0 + direction * 2 * FLY
        for t in range(WARN + FLY + 1, WARN + FLY + LAND + 1):            # the landing ring grows
            s, o = seen[t]
            assert (o[OAM_RING]["x"], o[OAM_RING]["y"]) == (land, BASE_Y - 4 + 16) and hidden(o, *FISH), t
        sizes = [ring_e.index(seen[t][1][OAM_RING]["tile"]) // 2 for t in range(WARN + FLY + 1, WARN + FLY + LAND + 1)]
        assert sizes == sorted(sizes) and sizes[0] == 0 and sizes[-1] == 2
        s, o = look(gb)
        assert s["fish_t"] == 0 and hidden(o, *FISH, *RING)
    with log_roll(model) as gb:                                           # goldens: the ripples, the fish at the top of its arc
        hold_stage_anim(gb)
        to_playing(gb)
        leap(gb, 0, direction)
        run_until_state(gb, lambda s: s["fish_t"] == (WARN - 12 if direction < 0 else WARN + 25), 200)
        t = 30 * 60 - 3                                                   # (a timer that does not depend on the frames the run took)
        gb.write("mg_timer", t & 255)
        gb.write(gb.addr("mg_timer") + 1, t >> 8)
        frames(gb, 1)
        shot(gb, f"fish_{direction}")
        if direction < 0:
            check_golden(gb, "lr_ripples")
        else:
            check_golden(gb, "lr_fish")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_schedule_the_first_leap_and_gaps_that_shrink_with_the_clock(model):
    """The first ripples come FISH_FIRST frames into the play; after each leap's ripples the next gap is GAP0 - elapsed / 16 (+ 0..31): 360 (6 s) at the
    start, 210 (3.5 s) at the end; the first leap's ripples after 360 (6 s). The bubbling is the ripples' sound. No ripples with under FISH_LAST frames left, nor while he is in the river."""
    with log_roll(model) as gb:
        to_play(gb)
        s = snap(gb)
        assert FISH_FIRST - 8 <= s["fish_in"] <= FISH_FIRST and s["fish_t"] == 0
        calm(gb)
        for elapsed in (0, 1200, 2400):
            lo = GAP0 - (elapsed >> 4)
            poke(gb, fish_t=0, fish_in=0, elapsed=elapsed, st=LS_RUN)
            fill0 = sfx(gb, SFX_FILL)
            frames(gb, 1)
            s = snap(gb)
            assert s["fish_t"] in (1, 2) and sfx(gb, SFX_FILL) == fill0 + 1, "the ripples begin with a bubbling"
            assert lo - 2 <= s["fish_in"] <= lo + 31, (elapsed, s["fish_in"])
            assert (s["fish_tgt"], s["fish_dir"]) in ((0, -1), (0, 1), (1, 1))
        assert GAP0 - 150 > WARN + FLY + LAND, "the next ripples never begin before the last fish is gone"
        calm(gb)
        poke(gb, fish_t=0, fish_in=0, st=LS_WATER, fall_t=1)               # in the river: none begins
        frames(gb, 10)
        assert snap(gb)["fish_t"] == 0
        poke(gb, st=LS_RUN)
        gb.write("mg_timer", FISH_LAST - 10)
        gb.write(gb.addr("mg_timer") + 1, 0)
        frames(gb, 5)
        assert snap(gb)["fish_t"] == 0, "too late in the game for another"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_one_leap_in_four_is_the_sasquatchs_and_never_while_he_swims(model):
    """24 draws: the Spigoteer's from both sides, the Sasquatch's only from the left (ring at x 4); while he is in the river none is his. (The
    fish's seed is the game's: the draws are the same each run.)"""
    with log_roll(model) as gb:
        to_playing(gb)
        calm(gb)
        got = set()
        for _ in range(24):
            poke(gb, fish_t=0, fish_in=0, st=LS_RUN, sq_st=SQ_LOG, top_t=0)
            frames(gb, 1)
            s = snap(gb)
            got.add((s["fish_tgt"], s["fish_dir"], s["fish_x0"]))
        assert got == {(0, -1, SPIG_CX + HALF), (0, 1, SPIG_CX - HALF), (1, 1, SQ_CX - HALF)}, got
        for _ in range(24):
            poke(gb, fish_t=0, fish_in=0, st=LS_RUN, sq_st=SQ_SWIM_ST, top_t=5)
            frames(gb, 1)
            assert snap(gb)["fish_tgt"] == 0


# ---- the hop ------------------------------------------------------------------------------------------------------------------
def press_hop(gb, key, n=1):
    """Press `key` until the hop starts (hop_t 1); the frames it took."""
    gb.hold(key)
    for i in range(4):
        frames(gb, 1)
        if snap(gb)["hop_t"] >= 1:
            break
    gb.release(key)
    return i


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("key", ["a", "b", "up"])
def test_a_b_and_up_hop_on_the_curve_and_rest_before_the_next(model, key):
    """A press of A, B or Up: 36 frames in the air on the t (36 - t) / 9 curve (36 px up at the top), the arms-out pose, SFX_LAUNCH once, then 12
    frames of rest (a press then does nothing), then a new hop. A hold is one hop."""
    with log_roll(model) as gb:
        to_playing(gb)
        calm(gb)
        launches = sfx(gb, SFX_LAUNCH)
        gb.hold(key)
        ts, ys, tiles = [], [], []
        for i in range(HOP_END + 8):
            frames(gb, 1)
            s, o = look(gb)
            ts.append(s["hop_t"])
            ys.append(o[OAM_SPIG]["y"])
            tiles.append(o[OAM_SPIG]["tile"])
        gb.release(key)
        assert sfx(gb, SFX_LAUNCH) == launches + 1, "a hold is one hop"
        i0 = ts.index(1)
        assert ts[i0:i0 + HOP_END] == list(range(1, HOP_END + 1)) and ts[i0 + HOP_END] == 0, ts
        for t in range(1, HOP_LEN + 1):
            assert ys[i0 + t - 1] == 72 + 16 - HOP_H[t], t
            assert tiles[i0 + t - 1] == otile(ART["pose_e"][0][0]), "arms out"
        assert all(y == 72 + 16 for y in ys[i0 + HOP_LEN:i0 + HOP_END]), "back on the log for the rest"
        poke(gb, hop_t=0)                                                 # a hop, then a press during its rest
        press_hop(gb, key)
        run_until_state(gb, lambda s: s["hop_t"] == HOP_LEN + 3, 60)
        launches = sfx(gb, SFX_LAUNCH)
        gb.press(key, 2)
        frames(gb, 2)
        s = snap(gb)
        assert s["hop_t"] > HOP_LEN + 3 and sfx(gb, SFX_LAUNCH) == launches, "no hop in the rest"
        run_until_state(gb, lambda s: s["hop_t"] == 0, 60)
        press_hop(gb, key)
        assert sfx(gb, SFX_LAUNCH) == launches + 1


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_lean_physics_go_on_in_the_air_and_there_is_no_hop_in_the_river(model):
    with log_roll(model) as gb:
        to_playing(gb)
        calm(gb)
        press_hop(gb, "a")
        frames(gb, 2)
        tap(gb, "right")
        frames(gb, 200)
        assert abs(snap(gb)["px"] - 15) < 0.6, "a tap in the air is the same 15 px"
        poke(gb, lean=70 * 65536)
        frames(gb, 3)
        assert snap(gb)["st"] == LS_WATER and snap(gb)["hop_t"] == 0
        launches = sfx(gb, SFX_LAUNCH)
        gb.press("b", 2)
        frames(gb, 3)
        assert snap(gb)["hop_t"] == 0 and sfx(gb, SFX_LAUNCH) == launches, "no hop in the river"


# ---- a hit and a dodge --------------------------------------------------------------------------------------------------------
def seconds_points(rows):
    """The 100 a second the rows' time on the log earned (the score also moves with that)."""
    return PTS_SEC * ((rows[-1]["on"] - rows[0]["on"] + rows[0]["s60"]) // 60)


def leap_against(gb, start, direction=-1):
    """A fish at the Spigoteer from `direction`; a hop begins at about leap frame `start` (None: no hop). -> (hits, dodged, rows)."""
    leap(gb, 0, direction)
    s = snap(gb)
    h0, d0, f0 = s["hits"], s["dodged"], s["falls"]
    done, rows = False, []
    for _ in range(300):
        s = snap(gb)
        rows.append(s)
        if start is not None and not done and s["fish_t"] >= WARN + 1 + start:
            gb.hold("a")
            frames(gb, 1)
            gb.release("a")
            done = True
        if s["fish_t"] == 0 and len(rows) > 3:
            break
        frames(gb, 1)
    s = snap(gb)
    return s["hits"] - h0, s["dodged"] - d0, rows


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_fish_hits_a_standing_spigoteer_and_a_hop_dodges_and_scores(model):
    """No hop: the fish over him at its apex: one hit, the kick in the fish's direction (no push, no input: to the edge), SFX_BREAK, the stagger
    (STUN frames), no points. A hop during the leap: no hit, DODGE points and SFX_COIN once, nothing moves him."""
    with log_roll(model) as gb:
        to_playing(gb)
        breaks, coins = sfx(gb, SFX_BREAK), sfx(gb, SFX_COIN)
        s0 = gb.mem16("mg_score")
        hits, dodged, rows = leap_against(gb, None, -1)
        assert (hits, dodged) == (1, 0) and sfx(gb, SFX_BREAK) >= breaks + 1 and sfx(gb, SFX_COIN) == coins
        assert gb.mem16("mg_score") == s0 + seconds_points(rows)
        assert max(r["stun"] for r in rows) == STUN and [r for r in rows if r["stun"]][0]["hit_dir"] == -1
        assert min(r["px"] for r in rows) < -40 or max(r["falls"] for r in rows) >= 1, "kicked to the left"
    with log_roll(model) as gb:
        to_playing(gb)
        breaks, coins = sfx(gb, SFX_BREAK), sfx(gb, SFX_COIN)
        s0 = gb.mem16("mg_score")
        hits, dodged, rows = leap_against(gb, 4, 1)
        assert (hits, dodged) == (0, 1) and sfx(gb, SFX_BREAK) == breaks and sfx(gb, SFX_COIN) == coins + 1
        assert gb.mem16("mg_score") == s0 + PTS_DODGE + seconds_points(rows)
        assert max(abs(r["px"]) for r in rows) < 1, "not touched"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_hop_window_is_a_third_of_a_second_wide(model):
    """A hop started at each frame of the leap in turn: the dodging starts form one run (the fish is over him for 9 frames, a hop clears from 14 px
    up, which it is for 29 of its 36 frames), at least 14 frames wide and taking in the frames the bot of this file hops at; a hop long before or
    long after hits."""
    with log_roll(model) as gb:
        to_playing(gb)
        win = []
        for start in range(-26, 30):
            hits, dodged, _ = leap_against(gb, start, -1)
            assert hits + dodged == 1, (start, hits, dodged)
            if dodged:
                win.append(start)
        assert win == list(range(win[0], win[-1] + 1)), win
        assert 14 <= len(win) <= 26 and win[0] <= 4 and win[-1] >= 11, (win[0], win[-1])
        assert -26 not in win and 29 not in win


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_hit_cannot_be_leaned_against_for_12_frames_nor_hopped_and_two_taps_after_save_him(model):
    with log_roll(model) as gb:
        to_playing(gb)
        leap(gb, 0, 1)
        run_until_state(gb, lambda s: s["stun"] == STUN, 200)
        launches = sfx(gb, SFX_LAUNCH)
        gb.hold("a")
        gb.hold("left")
        frames(gb, 3)
        gb.release("a")
        gb.release("left")
        s = snap(gb)
        assert s["hop_t"] == 0 and sfx(gb, SFX_LAUNCH) == launches, "no hop while he staggers"
        assert s["vel"] > 2.5 * ONE and s["hit_dir"] == 1, "no leaning back yet: the press was ignored"
        run_until_state(gb, lambda s: s["stun"] <= STUN - 12, 40)
        v0 = snap(gb)["vel"]
        tap(gb, "left", 1)
        assert snap(gb)["vel"] < v0 - ONE // 2, "after 12 frames a tap against it counts"
        tap(gb, "left")
        run_until_state(gb, lambda s: s["stun"] == 0, 40)
        frames(gb, 2)
        s = snap(gb)
        assert s["st"] == LS_RUN and s["falls"] == 0, "two quick taps after the first 12 frames save him"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_fall_ends_the_fish_in_the_air_and_no_fish_is_drawn_in_the_river(model):
    with log_roll(model) as gb:
        to_playing(gb)
        leap(gb, 0, -1)
        run_until_state(gb, lambda s: s["fish_t"] == WARN + 10, 100)
        poke(gb, lean=70 * 65536)
        frames(gb, 2)
        s, o = look(gb)
        assert s["st"] == LS_WATER and s["fish_t"] == 0 and s["hop_t"] == 0
        assert hidden(o, *FISH, *RING), "the fish dives with the splash"
        leap(gb, 0, 1)
        poke(gb, st=LS_WATER, fall_t=5)
        frames(gb, 2)
        s, o = look(gb)
        assert hidden(o, *FISH, *RING), "nothing is drawn while he is in the river"


# ---- the Sasquatch ------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_sasquatch_treads_to_the_roll_windmills_at_a_flip_and_sways_with_the_push(model):
    """The lodge show's dance frames: treading (frames 0 2 0 3 by the bark's phase, a 1 px bob on the odd phases, mirrored when the bark rolls
    the other way), windmilling (1 2 1 3 every 4 frames) while the bark's ramp is under 12, a 3 px sway with the push."""
    with log_roll(model) as gb:
        to_playing(gb)
        calm(gb)
        for sign in (1, -1):
            poke(gb, tsgn=sign, dsr=sign * RAMP, tell=sign * RAMP, fdelay=0, fish_in=65000, flip_in=65000)
            for phase, f in enumerate((0, 2, 0, 3)):
                poke(gb, roll=(phase << 14) + 3000)
                frames(gb, 1)
                s, o = look(gb)
                assert (sq_frame(o), bool(o[OAM_SQ]["prop"] & S_FLIPX)) == (f, sign < 0), (sign, phase)
                assert o[OAM_SQ]["y"] == 88 + (phase & 1) and o[OAM_SQ]["x"] in (52 + 3 * sign, 60 + 3 * sign, 44 + 16 + 3 * sign), (phase, o[OAM_SQ])
        poke(gb, tell=0, dsr=0, tsgn=0)
        got = []
        for _ in range(16):
            poke(gb, tell=0, dsr=0, tsgn=0)
            frames(gb, 1)
            s, o = look(gb)
            got.append(sq_frame(o))
        assert set(got) == {1, 2, 3} and got.count(1) >= 6, got
        assert o[OAM_SQ]["x"] == 52 and o[OAM_SQ]["y"] == 88, "centred when the push is nothing"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_sasquatch_hops_a_fish_aimed_at_him_or_is_knocked_into_the_river(model):
    """A fish at him (from the left, ring at x 4): startled while it comes. If he dodges (sq_dodge) he hops (frame 1, on the curve) and nothing
    falls. If not, the fish stops at him (fish_t 0), SFX_BREAK, he topples into the river (the topple pose, a splash at TOPPLE), swims SQ_SWIM
    frames, climbs back in SQ_UP_LEN frames and treads again; the Spigoteer is not touched and no points move."""
    with log_roll(model) as gb:
        to_playing(gb)
        leap(gb, 1, 1, dodge=1)
        s0, breaks = gb.mem16("mg_score"), sfx(gb, SFX_BREAK)
        rows = run_leap(gb)
        pts = seconds_points([r[0] for r in rows])
        hops = [(s["sq_hop"], o[OAM_SQ]["y"]) for s, o in rows if s["sq_hop"]]
        assert [h for h, _ in hops][:3] == [1, 2, 3] and max(h for h, _ in hops) == HOP_LEN, hops
        assert all(y == 88 - HOP_H[h] for h, y in hops), "his hop is the curve"
        assert {sq_frame(o) for s, o in rows if s["sq_hop"]} == {1}
        assert {sq_frame(o) for s, o in rows if 1 < s["fish_t"] <= WARN + 11} == {3}, "startled while it comes"
        s = snap(gb)
        assert s["sq_st"] == SQ_LOG and s["hits"] == 0 and gb.mem16("mg_score") == s0 + pts and sfx(gb, SFX_BREAK) == breaks
    with log_roll(model) as gb:
        to_playing(gb)
        leap(gb, 1, 1, dodge=0)
        s0, breaks = gb.mem16("mg_score"), sfx(gb, SFX_BREAK)
        first = snap(gb)
        rows = run_leap(gb)
        s = snap(gb)
        assert s["fish_t"] == 0 and s["sq_st"] == SQ_SWIM_ST and sfx(gb, SFX_BREAK) == breaks + 1 and s["hits"] == 0 and s["falls"] == 0
        assert len(rows) < WARN + 34, "the fish ended at him"
        worst = [0]
        got = {}
        for _ in range(SQ_SWIM + SQ_UP_LEN + 6):
            s, o = look(gb)
            got[s["top_t"]] = (s, o)
            frames(gb, 1, worst)
        s, o = look(gb)
        assert s["sq_st"] == SQ_LOG and s["top_t"] == 0, "back on the log"
        assert got[TOPPLE + 1][0]["drop_t"] > 0 and any(got[TOPPLE + 1][1][OAM_DROPS + k]["y"] for k in range(4)), "the splash"
        assert got[TOPPLE][1][OAM_SQ]["y"] == 100 + 16 and got[TOPPLE][1][OAM_SQ]["prop"] & S_FLIPX, "in the river, tumbling"
        y = [got[t][1][OAM_SQ]["y"] for t in (SQ_SWIM, SQ_SWIM + 4, SQ_SWIM + 8, SQ_SWIM + SQ_UP_LEN - 1)]
        assert y[0] == 116 and y[0] > y[1] > y[2] > y[3], ("climbing", y)
        assert gb.mem16("mg_score") == s0 + seconds_points([first, snap(gb)]) and worst[0] <= 9
        assert o[OAM_SQ]["y"] == 88 and sq_frame(o) in (0, 1, 2, 3)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_swimming_sasquatch_stays_in_the_river_at_time_up(model):
    with log_roll(model) as gb:
        to_playing(gb, 3)
        calm(gb)
        poke(gb, sq_st=SQ_SWIM_ST, top_t=30)
        finish(gb)
        frames(gb, 3)
        s = snap(gb)
        assert s["sq_st"] == SQ_SWIM_ST and s["top_t"] > 30, "he goes on swimming: no second topple"
        until(gb, lambda: gb.mem("mg_phase") == MG_RESULT, 120)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_stagger_startles_the_sasquatch_and_the_spigoteer_leans_hard_away(model):
    with log_roll(model) as gb:
        to_playing(gb)
        calm(gb)
        poke(gb, tell=RAMP, tsgn=1, dsr=RAMP, stun=20, hit_dir=1)
        frames(gb, 1)
        s, o = look(gb)
        assert sq_frame(o) == 3, "he is startled"
        assert o[OAM_SPIG]["tile"] == otile(ART["pose_e"][3][0]), "the hard lean"
        assert o[OAM_SPIG]["prop"] & S_FLIPX, "hit_dir 1: a right lean is the x-flip"


# ---- lines and speed ----------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_forced_worst_scenes_with_fish_stay_within_10_a_line(model):
    """Where the new sprites could meet the splash: every leap with a hop up and the Sasquatch hopping; the Sasquatch swimming (his splash) with
    a leap going on; the Spigoteer in the river with a fish set (not drawn then) and his droplets. 9 at most."""
    with log_roll(model) as gb:
        to_playing(gb)
        worst = 0
        for tgt, direction in ((0, -1), (0, 1), (1, 1)):
            leap(gb, tgt, direction, dodge=1)
            for i in range(WARN + FLY + LAND + 2):
                if i % 9 == 0:
                    poke(gb, hop_t=14, sq_hop=14)
                frames(gb, 1)
                worst = max(worst, max(lines(gb)))
        leap(gb, 0, -1)
        poke(gb, sq_st=SQ_SWIM_ST, top_t=TOPPLE - 2)
        for i in range(WARN + FLY + LAND + 2):
            frames(gb, 1)
            worst = max(worst, max(lines(gb)))
        assert worst <= 9, worst
        poke(gb, st=LS_WATER, fall_t=1, fish_t=WARN + 30, drop_t=1, drop_x=100, sq_st=SQ_SWIM_ST, top_t=TOPPLE + 1)
        for age in range(DROPS):
            poke(gb, fall_t=1 + age // 2, fish_t=WARN + 30, top_t=TOPPLE + 1)
            frames(gb, 1)
            worst = max(worst, max(lines(gb)))
        assert worst <= 9, worst


def end_lines(gb, n, each=None):
    """(the mean and the worst end line of the logic + music over n frames, late VBlank copies, missed frames)."""
    tot, worst = 0, 0
    late0, missed0 = gb.mem16("vq_late"), gb.mem16("missed_frames")
    for i in range(n):
        if each:
            each(i)
        gb.run(1)
        v = gb.mem16("perf_end_last")
        tot += v
        worst = max(worst, v)
    return tot / n, worst, gb.mem16("vq_late") - late0, gb.mem16("missed_frames") - missed0


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_fish_cost_no_late_frame_and_few_lines(model):
    """The hazard's cost (the owner saw slowdown in this game once): 1200 frames with a fish in the air or its ripples all the time, a hop every 60
    frames and the Sasquatch hopping, against 1200 frames of the same calm log with no fish: no late frame, no refused VBlank copy, the worst
    frame ends before line 128 as before, and the fish add under 10 lines to the mean frame (7 measured) (a line is 114 cycles)."""
    with log_roll(model) as gb:
        to_play(gb)
        calm(gb)
        base = end_lines(gb, 1200)

        def each(i):
            if gb.mem(gb.addr("story_scratch") + LAYOUT["fish_t"][0]) == 0:      # no fish: start the next leap (a poke between frames)
                k = i // 150 % 3
                poke_fish(gb, (0, 0, 1)[k], (-1, 1, 1)[k])
            if i % 60 == 0:
                gb.hold("a")
            elif i % 60 == 2:
                gb.release("a")
            if i % 40 == 0:
                poke_fish(gb, None, None)
        calm(gb)
        with_fish = end_lines(gb, 1200, each)
        print(f"perf {model}: no fish mean {base[0]:.1f} worst {base[1]}; fish mean {with_fish[0]:.1f} worst {with_fish[1]}")
        assert base[2:] == (0, 0) and with_fish[2:] == (0, 0), (base, with_fish)
        assert with_fish[1] < 128 and base[1] < 128
        assert with_fish[0] - base[0] < 10, (with_fish, base)


def poke_fish(gb, tgt, direction):
    """Between frames (no pause): start a leap (tgt, direction) or just recentre the lean (None)."""
    base = gb.addr("story_scratch")
    if tgt is None:
        for i in range(8):
            gb.write(base + LAYOUT["lean"][0] + i, 0)      # lean and vel (adjacent int32s)
        return
    x0 = (SQ_CX - HALF) if tgt else (SPIG_CX - HALF if direction > 0 else SPIG_CX + HALF)
    for name, v in (("fish_t", 1), ("fish_tgt", tgt), ("fish_dir", direction & 0xFF), ("fish_x0", x0), ("fish_done", 0), ("sq_dodge", 1)):
        gb.write(base + LAYOUT[name][0], v)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("direction", [-1, 1])
@pytest.mark.parametrize("against", [False, True])
def test_a_hit_always_pushes_him_the_way_the_fish_flies_even_against_the_roll_and_his_lean(model, direction, against):
    """Owner 2026-10-15: a hit always pushes in the fish's direction. Even with the roll's push and his velocity both the other way, the velocity
    is the fish's way for every stagger frame (the roll's push waits out the stagger) and the lean moves that way until the stagger ends."""
    with log_roll(model) as gb:
        to_playing(gb)
        leap(gb, 0, direction)
        if against:                                   # a strong push and a fast lean the other way, just before it arrives
            run_until_state(gb, lambda s: s["fish_t"] == WARN + 20, 200)
            poke(gb, tsgn=-direction, dsr=-direction * RAMP, tell=-direction * RAMP, vel=-direction * 3 * ONE)
        run_until_state(gb, lambda s: s["stun"] == STUN, 200)
        lean0 = snap(gb)["lean"]
        for _ in range(STUN - 1):
            s = snap(gb)
            assert s["vel"] * direction > 0, s
            frames(gb, 1)
        assert (snap(gb)["lean"] - lean0) * direction > 0
