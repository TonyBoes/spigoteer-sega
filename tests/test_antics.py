# Modes P6: CLASSIC's end-of-level antics (src/antics.c; art assets/art/antics/, owner-approved 2026-10-11). After LEVEL
# CLEAR in CLASSIC the bartender tosses a glass; one of six endings at random (its own random byte antics_rng; the test
# hook antics_force 1..6 plays ending n - 1): 0 backheel and smash, 1 backheel and hurt foot, 2 the dove, 3 the glass
# hat, 4 crash on the head (dazed, stars), 5 two beers. The clear: 60 frames of the banner, the ending (210), 30 on its
# last picture; the 32 OBJ tiles go over the show's while the level is clear and the next level load puts them back.
import json

import pytest
from conftest import ROM, ROOT, check_golden
from gbtools import Rom
from test_classic_mode import classic_at
from test_flow import BONUS, LEVEL_CLEAR, PLAYING, run_until, state
from test_patrons import MAX_P, inject_mug
from test_sound import srom  # noqa: F401  (the sound-emulated ROM: PyBoy keeps the APU registers readable only then)

pytestmark = pytest.mark.timeout(240)

ANT_WAIT, ANT_PRE, ANT_LEN, ANT_HOLD = 60, 42, 210, 30      # (ANT_PRE: the beat before the trick, owner 2026-10-15)
CLEAR = ANT_WAIT + ANT_PRE + ANT_LEN + ANT_HOLD
ANT_TILES = bytes(json.loads((ROOT / "build" / "antics.json").read_text())["tiles"])
OBJ_DANCER = 92 + 4                      # OBJ_COIN (92) + COIN_TILE_COUNT: game.h
ENDINGS = ["smash", "foot", "bird", "hat", "crash", "beer"]


def obj_tiles(gb, first, n):
    return bytes(gb.read(0x8000 + first * 16, n * 16))


def clear_level(gb, force=0, bar=None, x=None):
    """Serve every patron of the level (quota = the ones spawned) so it clears the real way; antics_force first."""
    gb.write("antics_force", force)
    gb.write("intro_timer", 255)
    gb.write("quota", gb.mem("spawned"))
    gb.write("pushback_px", 255)                      # (a mug serves from anywhere: the push carries a patron off the screen)
    if bar is not None:
        gb.write("bar", bar)
        gb.write("bartender_x", x)
    st, br, px = gb.read("patron_state", MAX_P), gb.read("patron_bar", MAX_P), gb.read("patron_x", MAX_P)
    for p in range(MAX_P):
        if st[p]:
            inject_mug(gb, br[p], px[p] + 8)
    run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 200)
    assert state(gb) == LEVEL_CLEAR
    return gb


def line_counts(gb):
    c = [0] * 144
    for s in gb.oam():
        if not s["y"] or s["y"] >= 160 or not s["x"] or s["x"] >= 168:
            continue
        for line in range(max(0, s["y"] - 16), min(144, s["y"])):
            c[line] += 1
    return max(c)


@pytest.mark.parametrize("n", range(6), ids=ENDINGS)
def test_each_ending_plays_and_ends_within_the_clear(boot, n):
    classic_at(boot, 1)
    show = obj_tiles(boot, OBJ_DANCER, 32)
    clear_level(boot, force=n + 1)
    assert boot.mem("antics_end") == n
    frames, worst, seen_poses = 0, 0, set()
    while state(boot) == LEVEL_CLEAR and frames < CLEAR + 30:
        boot.run(1)
        frames += 1
        worst = max(worst, line_counts(boot))
        if frames == 20:
            assert obj_tiles(boot, OBJ_DANCER, 32) == ANT_TILES, "the antics' tiles over the show's"
        if ANT_WAIT + ANT_PRE + 2 < frames < ANT_WAIT + ANT_PRE + ANT_LEN:
            assert boot.mem("overlay_on") == 0, "the banner goes for the antics"
            seen_poses.add(boot.oam()[0]["tile"])
    assert frames <= CLEAR + 15, ("the clear ends on time (+ the next level's load, LCD off)", frames)
    assert worst <= 10
    assert len(seen_poses) >= 2, "he moves"
    run_until(boot, lambda: state(boot) in (PLAYING, BONUS), 60)
    assert state(boot) == PLAYING and boot.mem("level") == 2, "level 1: no bonus round, the next level"
    assert obj_tiles(boot, OBJ_DANCER, 32) == show, "the next level load puts the show's tiles back"


def test_the_bonus_round_after_the_antics_has_its_own_tiles_and_the_level_after_the_show_s(boot):
    classic_at(boot, 2)
    show = obj_tiles(boot, OBJ_DANCER, 32)
    clear_level(boot, force=3)
    run_until(boot, lambda: state(boot) == BONUS, CLEAR + 30)
    assert state(boot) == BONUS
    boot.write("bonus_phase", 4)
    boot.write("bonus_timer", 200)
    run_until(boot, lambda: state(boot) == PLAYING, 600)
    assert state(boot) == PLAYING and boot.mem("level") == 3
    # (level 3 is the stadium: compare with the venue's own show tiles as a fresh load leaves them)
    with Rom(ROM, boot.model_name) as gb:
        gb.run(120)
        gb.model_name = boot.model_name
        classic_at(gb, 3)
        assert obj_tiles(boot, OBJ_DANCER, 32) == obj_tiles(gb, OBJ_DANCER, 32)
    assert show != ANT_TILES


def test_the_ending_is_random_and_leaves_the_game_s_random_sequence_alone(boot):
    classic_at(boot, 1)
    got = []
    for k in range(8):
        boot.write("level", 1 if k % 2 == 0 else 3)        # (no bonus round after either)
        r0 = boot.mem("rng_state")
        boot.write("level_clear", 1)
        run_until(boot, lambda: state(boot) == LEVEL_CLEAR, 30)
        got.append(boot.mem("antics_end"))
        assert boot.mem("rng_state") == r0, "the clear draws nothing from next_rand"
        run_until(boot, lambda: state(boot) == PLAYING, CLEAR + 30)
    assert len(set(got)) >= 3, got


@pytest.mark.parametrize("n", range(6), ids=ENDINGS)
def test_on_an_r_bar_the_antics_are_mirrored(boot, n):
    """CLASSIC level 3 (RRRR): every entry of the antics at 168 - X with S_FLIPX toggled, as the play's sprites; never more
    than 10 a line, on the bottom bar too."""
    classic_at(boot, 3)
    clear_level(boot, force=n + 1, bar=3, x=40)
    boot.run(ANT_WAIT + ANT_PRE + 30)
    bt = boot.oam()[0:4]
    xs = sorted(o["x"] for o in bt if o["y"])
    assert xs[0] == 168 - (40 + 16) and xs[-1] == 168 - (40 + 8), bt
    assert all(o["flags"] & 0x20 for o in bt if o["y"])
    worst = 0
    for _ in range(ANT_LEN):
        boot.run(1)
        worst = max(worst, line_counts(boot))
    assert worst <= 10


@pytest.mark.parametrize("bar", [0, 1, 2, 3])
def test_every_bar_and_the_slanted_ones(boot, bar):
    """Level 13 (slanted, L R L R): wherever he stands, every ending stays within 10 sprites a line (the bird and the glass
    fly up into the stage above the top bar)."""
    classic_at(boot, 13)
    tap = boot.read("bar_tap", 4)[bar]
    clear_level(boot, force=3 if bar < 2 else 5, bar=bar, x=tap)
    worst = 0
    for _ in range(CLEAR - 2):
        boot.run(1)
        worst = max(worst, line_counts(boot))
    assert worst <= 10


# ---- goldens -----------------------------------------------------------------------------------------------------------
def golden_at(boot, n, frame):
    classic_at(boot, 1)
    clear_level(boot, force=n + 1)
    boot.run(ANT_WAIT + ANT_PRE + frame)      # (the goldens are the ending's own frames: after the beat)
    return boot


def test_golden_antics_bird(boot):
    """The dove, stunned, on his head and the glass's shards on the counter (ending 2, frame 52 + 50)."""
    check_golden(golden_at(boot, 2, 102), "antics_bird")


def test_golden_antics_beer(boot):
    """Two beers: the second gulp, the first empty on the counter (ending 5, frame 120)."""
    check_golden(golden_at(boot, 5, 120), "antics_beer")


def test_golden_antics_dazed(boot):
    """Crashed on his head: dazed, the stars, the shards (ending 4, frame 52 + 60)."""
    check_golden(golden_at(boot, 4, 112), "antics_dazed")


# ---- the beat before the trick, the drumroll, the cymbal and the hold (owner 2026-10-15) ---------------------------------
NR42, NR43 = 0xFF21, 0xFF22
CYMBAL = (0xF3, 0x19)
# the frame of the ending (counted from the beat's start) on which the result happens and the cymbal crashes
RESULT = {0: ANT_PRE + 52 + 28, 1: ANT_PRE + 52 + 38, 2: ANT_PRE + 52 + 24, 3: ANT_PRE + 52 + 24, 4: ANT_PRE + 52 + 20,
          5: ANT_PRE + 160}


def play_clear(gb, n):
    """Run a forced ending to the end of the clear; per frame (antics_t of the frame just run, (NR42, NR43), game state)."""
    classic_at(gb, 1)
    clear_level(gb, force=n + 1)
    log = []
    while state(gb) == LEVEL_CLEAR and len(log) < CLEAR + 30:
        t0 = int.from_bytes(bytes(gb.read("antics_t", 2)), "little")
        gb.run(1)
        if state(gb) != LEVEL_CLEAR or (log and t0 < log[-1][0]):
            break                                       # (a new clear's antics_t starts again at 0)
        log.append((t0, (gb.mem(NR42), gb.mem(NR43)),
                    (gb.mem("lives"), gb.mem("score"), bytes(gb.read("patron_state", MAX_P)), bytes(gb.read("patron_x", MAX_P)),
                     gb.mem("bartender_x"), gb.mem("bar"))))
    return log


@pytest.mark.parametrize("n", range(6), ids=ENDINGS)
def test_the_beat_the_drumroll_the_cymbal_and_the_holds(srom, n):
    log = play_clear(srom, n)
    by_t = {t: (regs, st) for t, regs, st in log}
    # the clear's length: banner 60, beat 42, ending 210, hold 30
    assert len(log) >= CLEAR - 3 and len(log) <= CLEAR + 15, len(log)   # (+ the next level load)
    # the beat: the banner is gone and the picture holds still (he poses with the glass, no frame differs)
    beat = [t for t in by_t if ANT_WAIT <= t < ANT_WAIT + ANT_PRE]
    assert len(beat) == ANT_PRE
    # the drumroll: hits (NR42 / NR43 changing) only inside the beat, every second frame from beat frame 4, 18 of them,
    # the volume (NR42's high nibble) never falling
    hits, prev = [], None
    for t in sorted(by_t):
        regs = by_t[t][0]
        if prev is not None and regs != prev and t < ANT_WAIT + ANT_PRE + 8 and regs != CYMBAL:
            hits.append(t)
        prev = regs
    in_beat = [t for t in hits if ANT_WAIT <= t <= ANT_WAIT + ANT_PRE]
    assert 17 <= len(in_beat) <= 19, hits
    assert in_beat[0] - ANT_WAIT in range(4, 7) and in_beat[-1] - ANT_WAIT <= ANT_PRE - 1, in_beat
    vols = [by_t[t][0][0] >> 4 for t in in_beat]
    assert vols == sorted(vols) and vols[-1] >= 14 and vols[0] <= 6, vols
    # no drumroll before the beat
    assert not [t for t in hits if t < ANT_WAIT]
    # the cymbal: the first CYMBAL write lands on the result frame, and only there
    cym = [t for t in sorted(by_t) if by_t[t][0] == CYMBAL]
    assert cym, "a cymbal crash"
    assert abs(cym[0] - (ANT_WAIT + RESULT[n])) <= 2, (cym[0] - ANT_WAIT, RESULT[n])
    # a hold after the result: at least ANT_HOLD frames (0.5 s) before play resumes
    assert CLEAR - (cym[0] + 1) >= ANT_HOLD, (CLEAR, cym[0])
    # the hold before the trick: the roll is over before the trick starts, with a beat of at least 0.5 s
    assert ANT_PRE >= 30


@pytest.mark.parametrize("n", range(6), ids=ENDINGS)
def test_the_state_is_frozen_through_the_clear(boot, n):
    """Nothing moves in a clear but the antics (the patrons are all served, no mug flies, the clock is not running): lives,
    score, patrons, where he stands and which bar do not change from the first frame of the clear to its end, so the
    longer beat and hold cost the player nothing."""
    log = play_clear(boot, n)
    first = log[1][2]
    for t, regs, st in log[1:]:
        if t >= CLEAR - 2:
            break                                       # (the last frame is the next level's load)
        assert st == first, (t, st, first)
