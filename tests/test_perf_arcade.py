# Frame-time guard for the busiest ARCADE scene (owner perf report 2026-10-18, "fix b"): loop 4 of the space lounge's last
# shift (level 40), the realistic peak (perf_helpers.RealisticPeak: about 10 patrons and 10 mugs at the fastest row's speeds,
# new patrons sliding in, lifts, a tip or a show), the level-8 play script on the bartender, the game's own rules everywhere.
# A frame that runs past the next VBlank (end line >= 144, perf_helpers.perf_stats "late") repeats the picture once: the game
# then runs at 30 fps for that moment. Before the "fix b" work 45-50 % of this scene's frames were late (target 15-25 %).
#
# Whether a frame is late is a threshold on a number that sits right at it (the mean end line is ~135-140, the budget 144),
# and where the scene goes depends on which frames were late: one run swings by +-10 points with any change of code timing.
# So the guard pools EIGHT runs that start at different frame alignments (the deterministic PyBoy: the same build gives the
# same numbers every time) and bounds the pooled share, with a margin of about 6 points over the measured one, and the mean
# end line likewise. A real regression moves every run: the pre-"fix b" build measured 45 / 146 (DMG and CGB alike).
#
# The frame-time counter (main.c FRAME_STATS) is in the test build only (DEBUG_MENU), which is what this test runs.
import pytest
from conftest import ROM, ds_active
from gbtools import Rom
import perf_helpers as ph
from test_arcade import start_arcade
from test_story import SHIFT_STEP, win, to_goal
from test_flow import state, LEVEL_CLEAR, GS_GOAL, run_until

pytestmark = pytest.mark.timeout(300)
PLAYING = 1
ALIGNMENTS = (0, 5, 11, 23, 2, 7, 17, 29)       # frames waited after the scene's start: a different place of the frame boundary against the logic
FRAMES = 1800
# (model, target patrons): (late share limit in %, mean end line limit). Measured pooled (the eight alignments), then the limits:
#   with the asm catch scans too (src/patrons.c ASM_SCANS): dmg 8: 15.4 % / 119.3 (limits 21 / 124); cgb 8: 17.7 / 120.4 (23 / 125);
#   dmg 10: 18.6 / 123.6 (24 / 128); cgb 10: 20.6 / 124.6 (26 / 129)  (12 patrons: dmg 27.5 / 129.8, cgb 34.8 / 135.2).
#   with the asm mug code (Q63c, src/mugs.c ASM_DRAW_HELD / ASM_UPDATE_MUGS): dmg 8: 16.8 % / 121.2 (limits 22 / 125); cgb 8: 18.0 / 121.7
#   (23 / 126); dmg 10: 19.5 / 124.4 (25 / 129); cgb 10: 23.0 / 126.7 (28 / 131).
#   with the "fix b" C only: dmg 8: 24.4 / 127.5; cgb 8: 24.3 / 126.6; dmg 10: 33.1 / 135.1; cgb 10: 35.5 / 136.7 (12 patrons: 47 / 143 and 52 / 146).
# The build before "fix b": dmg 8: 34.1 / 136.3; cgb 8: 34.4 / 136.6; dmg 10: 42.7 / 143.7; cgb 10: 45.7 / 146.8.
# The owner's target for the 10-patron peak was 15-25 %; the asm pass's mug code brought it there (the catch scans of patrons.c and
# the lift / patron drawing are the next costs).
LIMITS = {("dmg", 8): (21, 124), ("cgb", 8): (23, 125),
          ("dmg", 10): (24, 128), ("cgb", 10): (26, 130)}   # cgb 10 mean end line 129 -> 130: owner Q89 2026-11-01 (the Factory's split chain)
# The all-C ROM (`make cfall`, GB_ROM=build/game-c.gb, the owner's porting reference) is slower: the limits it had before the asm mug code.
C_LIMITS = {("dmg", 8): (30, 132), ("cgb", 8): (32, 134), ("dmg", 10): (35, 138), ("cgb", 10): (41, 142)}
if ROM.stem.endswith("-c"):
    LIMITS = C_LIMITS
# Owner Q92 (2026-11-01): the Color runs at double speed, the way the game ships, and the guard measures the line the frame's LOGIC ended on.
# Late share limits stay; the mean limit is main's double-speed baseline + the margin today's limit has over main's normal-speed baseline
# (cgb 8: 49.3 + 125 - 117.5; cgb 10: 50.0 + 130 - 127.5 (130 is Q89's); the all-C ROM: see C_DS_MEAN).
DS_MEAN = {8: 56.8, 10: 52.5}
C_DS_MEAN = {8: 59.3, 10: 61.0}      # (the C ROM on main: 56.7 + 134 - 131.4 and 58.0 + 142 - 139)


def arcade_peak_gb(model):
    gb = start_arcade(model)
    to_goal(gb)
    gb.write("story_step", SHIFT_STEP[2] - 1)
    gb.write("story_chapter", 9)                  # the space lounge ...
    gb.write("arc_loop", 4)                       # ... in the 4th loop: the fastest rows
    win(gb, 0, 0)
    run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 40)
    run_until(gb, lambda: state(gb) == GS_GOAL, 800)
    to_goal(gb)
    for _ in range(220):
        if gb.mem("game_state") == PLAYING:
            break
        gb.run(1)
    assert gb.mem("game_state") == PLAYING
    return gb


def one_run(model, target, wait):
    gb = arcade_peak_gb(model)
    try:
        gb.write("intro_timer", 0)
        gb.write("tip_chance", 0)
        rp = ph.RealisticPeak(gb, target)
        rp.seed()
        gb.run(2 + wait)
        ph.perf_reset(gb)
        held = None
        for i in range(FRAMES):
            want = ph.SCRIPT[i % len(ph.SCRIPT)]
            if want != held:
                if held:
                    gb.release(held)
                if want:
                    gb.hold(want)
                held = want
            rp.tick()
            gb.run(1)
            rp.observe()
            ph.sample(gb)
            for name, v in (("lives", 3), ("served", 0), ("story_catches", 0), ("quota", 250)):
                gb.write(name, v)
        st = ph.perf_stats(gb)
        patrons = sum(rp.stats["patrons"]) / len(rp.stats["patrons"])
        return st, gb.perf_samples, patrons
    finally:
        gb.stop()


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("target", [8, 10])
def test_the_arcade_peak_is_late_on_a_bounded_share_of_its_frames(model, target):
    late = n = 0
    means = []
    crowd = []
    for wait in ALIGNMENTS:
        st, samples, patrons = one_run(model, target, wait)
        late += sum(1 for x in samples if x >= 144)
        n += len(samples)
        means.append(st["mean"])
        crowd.append(patrons)
    share = round(100.0 * late / n, 1)
    mean = round(sum(means) / len(means), 1)
    print("ARCADE PEAK", model, target, "late", share, "% of", n, "frames, mean end line", mean, "patrons", round(sum(crowd) / len(crowd), 1))
    assert sum(crowd) / len(crowd) >= 8, "the scene is a crowd (the realistic peak's own rules keep the bars full)"
    lim_share, lim_mean = LIMITS[(model, target)]
    if model == "cgb" and ds_active():
        lim_mean = (C_DS_MEAN if ROM.stem.endswith("-c") else DS_MEAN)[target]
    assert share <= lim_share and mean <= lim_mean, (share, mean, (lim_share, lim_mean))
