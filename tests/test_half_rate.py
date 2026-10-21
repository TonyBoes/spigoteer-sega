# The DMG's 30 fps mode (src/half.c, main.c update(); owner 2026-10-21): the logic runs in every VBlank, the drawing in every second one, so the
# heaviest levels keep the game's speed and rules and only the picture updates every other VBlank. HRAM 0xFFF4: bit 0 on, bits 1-2 the debug menu's
# choice (0 AUTO, 1 FORCE ON, 2 FORCE OFF). AUTO is on for the CLASSIC rows whose peak crowd was late on more than 30 % of the DMG's frames.
import pytest
from gbtools import Rom

import conftest as C
import perf_helpers as ph
from conftest import ROM, gesture, release_gesture, unlock_debug
from test_classic_mode import classic_at
from test_overlap import MAX_P, picture_problems
from test_perf import oam_line_counts

pytestmark = pytest.mark.timeout(300)

HALF = 0xFFF4
ON, FORCE_ON, FORCE_OFF = 1, 1 << 1 | 1, 2 << 1         # (the byte to poke: bit 0 is the level's, recomputed at the next level load)
PLAYING, DEBUG = 1, 7


def dmg():
    gb = Rom(ROM, "dmg")
    gb.run(120)
    gb.model_name = "dmg"
    C.hold_stage_anim(gb)
    return gb


def is_on(gb):
    return gb.mem(HALF) & ON


def drive(gb, script, i):
    """The level-8 script bot's key for frame i."""
    want = script[i % len(script)]
    held = getattr(gb, "_held", None)
    if want != held:
        if held:
            gb.release(held)
        if want:
            gb.hold(want)
        gb._held = want


# ---- the rules are the same ----------------------------------------------------------------------------------------------------
SCALARS = ["frame_counter", "joy", "joy_prev", "bartender_x", "bar", "fill_timer", "slide_timer", "catch_pose", "score", "lives", "served", "spawned", "spawn_timer",
           "rng_state", "tip_timer", "show_timer", "patrons_live", "mugs_live", "intro_timer", "game_state", "level", "quota"]
ARRAYS = [("patron_state", 16), ("patron_bar", 16), ("patron_x", 16), ("patron_frac", 16), ("patron_timer", 16), ("patron_drinks", 16),
          ("patron_dist", 16), ("patron_hurry", 16), ("mug_state", 20), ("mug_bar", 20), ("mug_timer", 20)]


def state(gb):
    s = []
    for n in SCALARS:
        try:
            s.append((n, gb.mem16(n) if n in ("spawn_timer", "tip_timer", "show_timer") else gb.mem(n)))
        except KeyError:
            pass
    s.extend((n, bytes(gb.read(n, k))) for n, k in ARRAYS)
    # (a mug in a patron's hand has its x written by the drawing code, mugs.c draw_held, a free slot keeps its last one, and no rule reads either: only a sliding or breaking mug's x is state)
    ms = gb.read("mug_state", 20)
    s.append(("mug_x_live", bytes(x if ms[i] in (1, 2, 3) else 0 for i, x in enumerate(gb.read("mug_x", 20)))))
    return s


def unflagged_shares(s):
    """The pairs of BG patrons (not lifted) of one bar whose tile columns meet, where one of them is not flagged (patron_ovl, src/lift.c: the chooser
    lifts one of two that share a column; when the budgets say no, the pair stays on the BG and is flagged OVL_SHARED / OVL_TOP)."""
    cols = {}
    for p in range(MAX_P):
        d, l = s["patron_draw"][p], s["patron_lift"][p]
        if not s["patron_state"][p] or d == 255 or ((l & 3) and not (l & 0x80)):
            continue
        c = (d & 0x7F) >> 3 if d & 0x80 else d >> 3
        cols[p] = (s["patron_bar"][p] & 3, set(range(c, c + (3 if d & 7 and not d & 0x80 else 2))))
    bad = []
    for p, (bp, cp) in cols.items():
        for q, (bq, cq) in cols.items():
            if p < q and bp == bq and cp & cq and not (s["patron_ovl"][p] and s["patron_ovl"][q]):
                bad.append((p, q, bp, sorted(cp), sorted(cq), s["patron_ovl"][p], s["patron_ovl"][q]))
    return bad


def level8(force, lv=8):
    gb = dmg()
    ph.start_game(gb)
    if lv > 1:
        ph.goto_level(gb, lv)
    gb.write("intro_timer", 0)
    gb.write("tip_chance", 255)
    gb.run(20)                                          # (the level load's long frames are over: both rates start in step)
    gb.write(HALF, force)
    return gb


@pytest.mark.parametrize("lv", [1, 2, 8])
def test_the_game_state_after_every_step_is_the_same_as_at_60_fps(lv):
    """Level 8 (its own spawns, the bartender on the level-8 script: fills, serves, bar changes), 900 frames, once at 60 fps and once forced to 30 fps:
    every game step ends in the same state (positions, timers, the score, the random generator): the logic runs in every VBlank with that
    VBlank's input, whether the picture follows or not. Neither run is late at this level, so frame i is step i in both."""
    a, b = level8(FORCE_OFF, lv), level8(FORCE_ON, lv)
    assert not is_on(a) and is_on(b)
    steps = ([], [])
    for gb, snaps in zip((a, b), steps):                 # the state where each step ends (vq_frame_end), in order
        addr = gb.addr("vq_frame_end")
        gb.pb.hook_register(addr >> 16, addr & 0xFFFF, lambda _, gb=gb, snaps=snaps: snaps.append(state(gb)), None)
    for i in range(900):
        for gb in (a, b):
            drive(gb, ph.SCRIPT, i)
            gb.run(1)
    assert len(steps[0]) >= 850 and abs(len(steps[0]) - len(steps[1])) <= 2, (len(steps[0]), len(steps[1]))
    same = 0
    for k, (sa, sb) in enumerate(zip(*steps)):
        # (a served patron sliding out stands still until his BG copy is off the screen: patrons.c leaving_step waits for the copy list, which
        # goes out with the picture: up to a step later at 30 fps. He lags a step until he is gone; nothing else depends on it.)
        if any(dict(s)["patron_state"][i] == 4 for s in (sa, sb) for i in range(16)):
            continue
        assert sa == sb, (k, [(x, y) for x, y in zip(sa, sb) if x != y])
        same += 1
    assert same >= 0.7 * len(steps[0]), same
    assert a.mem("served") > 0 or a.mem("score") > 0, "the script bot plays"
    a.stop(); b.stop()


def test_the_picture_follows_every_second_step_only():
    """In 30 fps the OAM (the bartender walking) changes on every second frame at most; at 60 fps on every one."""
    seen = {}
    for name, force in (("60", FORCE_OFF), ("30", FORCE_ON)):
        gb = level8(force)
        gb.write("tip_chance", 0)
        gb.hold("left")
        gb.run(10)
        xs = []
        for _ in range(40):
            gb.run(1)
            xs.append(gb.oam()[0]["x"])
        changes = sum(1 for p, q in zip(xs, xs[1:]) if p != q)
        seen[name] = changes
        gb.stop()
    assert seen["60"] >= 35 and 15 <= seen["30"] <= 22, seen


# ---- the music keeps its tempo ------------------------------------------------------------------------------------------------
def music_ticks(gb, frames, step=lambda i: None):
    """The music engine's ticks over `frames` emulator frames (music_frames' per-frame steps; a tune that restarts shows as a jump back and is not counted)."""
    last, n = gb.mem16("music_frames"), 0
    for i in range(frames):
        step(i)
        gb.run(1)
        m = gb.mem16("music_frames")
        if 0 <= m - last <= 3:
            n += m - last
        last = m
    return n


def test_music_ticks_per_second_are_equal():
    """The music ticks once a VBlank: 600 frames of play tick it ~600 times in 30 fps as at 60 fps (a light level), and on CLASSIC's heaviest level
    30 fps keeps the tempo where 60 fps drops frames (and so ticks)."""
    ticks = {}
    for name, force in (("60", FORCE_OFF), ("30", FORCE_ON)):
        gb = level8(force)
        ticks[name] = music_ticks(gb, 600)
        gb.stop()
    assert abs(ticks["30"] - ticks["60"]) <= 1 and ticks["60"] >= 590, ticks
    heavy = {}
    for name, force in (("auto", 0), ("off", FORCE_OFF)):
        gb = dmg()
        gb.write(HALF, force)
        classic_at(gb, 25)
        gb.write("intro_timer", 0)
        rp = ph.ClassicPeak(gb, 16)
        rp.seed()
        gb.run(2)

        def step(i):
            drive(gb, ph.SCRIPT, i)
            rp.tick()
        heavy[name] = music_ticks(gb, 600, step)
        gb.stop()
    assert heavy["auto"] >= 590, heavy
    assert heavy["off"] < 450, heavy                   # (the control: 60 fps at that level loses a third of the music's time)


# ---- the heaviest levels run at the game's speed ---------------------------------------------------------------------------------
@pytest.mark.parametrize("scene", ["classic25", "classic9", "level10"])
def test_the_heaviest_levels_run_at_60_game_steps_a_second_and_keep_the_budgets(scene):
    """The peak crowds (perf_helpers: ClassicPeak up to 16 patrons at CLASSIC level 25's / 9's bar caps, AUTO; RealisticPeak 10 patrons on the LEVEL
    harness's level 10, forced on), 1500 frames: the game takes >= 99.5 % of the steps the VBlanks allow (60 fps alone: 55-90 % late, ~32 steps a
    second on CLASSIC), and every picture keeps the budgets: never more than 10 objects on a line or 40 in all, and the crowd chooser keeps up: after at most 10 %
    of the pictures does a pair of BG patrons share a tile column without the chooser's flags (OVL_*), for at most 8 pictures running."""
    gb = dmg()
    if scene == "level10":
        ph.start_game(gb)
        ph.goto_fastest(gb)
        gb.write("tip_chance", 0)
        gb.write("intro_timer", 0)
        gb.write(HALF, int(__import__('os').environ.get('FORCE', FORCE_ON)))
        rp = ph.RealisticPeak(gb, 10)
    else:
        lv = int(scene[7:])
        classic_at(gb, lv)
        gb.write("intro_timer", 0)
        gb.write("tip_chance", 0)
        rp = ph.ClassicPeak(gb, 16)
    assert is_on(gb) or scene == 'level10'
    rp.seed()
    gb.run(2)
    snaps = []                                          # the patron state after every DRAWN step (the picture follows those)
    FIELDS = ("patron_state", "patron_bar", "patron_draw", "patron_variant", "patron_lift", "patron_ovl", "patron_x")
    a = gb.addr("vq_frame_end")

    def cb(_):
        if gb.mem("frame_counter") & 1 == 0 or not is_on(gb):            # (counted after the step: even = the odd step just drew)
            snaps.append({f: list(gb.read(f, MAX_P)) for f in FIELDS})
    gb.pb.hook_register(a >> 16, a & 0xFFFF, cb, None)
    games, worst_line, worst_n, last, seen = 0, 0, 0, gb.mem("frame_counter"), None
    pics, shared_pics, run, longest = 0, 0, {}, 0
    for i in range(1500):
        drive(gb, ph.SCRIPT, i)
        rp.tick()
        gb.run(1)
        rp.observe()
        games += (gb.mem("frame_counter") - last) & 255
        last = gb.mem("frame_counter")
        line, n = oam_line_counts(gb)
        if getattr(gb, "poked_mug", False):             # (the scenario's own poke, drawn uncounted: perf_helpers.ClassicPeak)
            line = min(line, 10)
        worst_line, worst_n = max(worst_line, line), max(worst_n, n)
        if snaps and snaps[-1] is not seen:             # (a drawn step: its picture is out; the crowd chooser has just run)
            seen = snaps[-1]
            if len(snaps) > 30:                         # (the seeded crowd is drawn in first)
                now = {(b[0], b[1]) for b in unflagged_shares(seen)}
                pics += 1
                shared_pics += bool(now)
                run = {k: run.get(k, 0) + 1 for k in now}
                longest = max([longest] + list(run.values()))
    s = rp.stats
    print(scene, "steps", games, "of 1500 frames; patrons mean", round(sum(s["patrons"]) / len(s["patrons"]), 1), "worst line", worst_line, "entries", worst_n)
    print("  pictures with a BG pair sharing a column unflagged:", shared_pics, "of", pics, "; longest run of pictures for one pair:", longest)
    assert shared_pics <= 0.10 * pics and longest <= 8, (shared_pics, pics, longest)   # (at 60 fps and late the same crowds: 9-40 % of the pictures, runs of 36-217)
    assert games >= 1500 * 0.995, games
    assert worst_line <= 10 and worst_n <= 40, (worst_line, worst_n)
    assert max(s["patrons"]) >= 9 and len(snaps) > 600
    assert gb.mem("vq_drain_ly_max") <= gb.mem("vq_latest_ly")
    gb.stop()


@pytest.mark.parametrize("lv", [1, 4, 5, 6, 7, 8, 16, 26, 27, 31, 32])
def test_auto_is_on_for_the_measured_classic_rows_only(lv):
    """AUTO: CLASSIC rows 5 and 7-26 are on (their peak crowd is late on more than 30 % of the frames at 60 fps), rows 1-4 and 6 are off; level 27 on
    plays wave 2's rows again (level 27 = row 14, 31 = row 18, 32 = row 19: on)."""
    gb = dmg()
    classic_at(gb, lv)
    row = lv
    while row > 26:
        row -= 13
    assert is_on(gb) == (1 if row == 5 or row >= 7 else 0), (lv, row, is_on(gb))
    gb.stop()


def test_the_level_harness_is_never_on_by_itself():
    gb = level8(0)
    assert not is_on(gb)
    gb.stop()


@pytest.mark.parametrize("lv,force,want", [(25, 2, 0), (1, 1, 1), (25, 1, 1), (25, 0, 1)])
def test_the_menus_choice_decides_the_next_level_load(lv, force, want):
    """FORCE OFF holds on a row AUTO turns on, FORCE ON on one it leaves off (the byte the debug menu writes, before the level loads)."""
    gb = dmg()
    gb.write(HALF, force << 1)
    classic_at(gb, lv)
    assert is_on(gb) == want
    gb.stop()


# ---- the debug menu's line -------------------------------------------------------------------------------------------------------
def test_the_debug_menu_toggles_auto_on_off(boot):
    """The menu's last line "30 FPS" (every mode): Right goes AUTO, ON, OFF and round, Left back; the level being played follows at once on the
    DMG (the CGB shows NO CGB and never changes). The choice also decides the next level's load."""
    from test_debug import goto, line, tap
    gb = boot
    ph.start_game(gb)
    ph.goto_level(gb, 8)
    unlock_debug(gb)
    gesture(gb)
    release_gesture(gb)
    gb.run(3)
    assert gb.mem("game_state") == DEBUG
    goto(gb, 4)
    assert line(gb, 10) == ("30 FPS", "NO CGB" if boot.model_name == "cgb" else "AUTO")
    choice = lambda: (gb.mem(HALF) >> 1) & 3
    if boot.model_name == "cgb":
        tap(gb, "right")
        assert choice() == 0 and not is_on(gb) and line(gb, 10)[1] == "NO CGB"
        return
    assert choice() == 0 and not is_on(gb)
    tap(gb, "right")
    assert line(gb, 10) == ("30 FPS", "ON") and choice() == 1 and is_on(gb)
    tap(gb, "right")
    assert line(gb, 10) == ("30 FPS", "OFF") and choice() == 2 and not is_on(gb)
    tap(gb, "right")
    assert line(gb, 10) == ("30 FPS", "AUTO") and choice() == 0 and not is_on(gb)     # (level 8 of the harness: AUTO is off)
    tap(gb, "left")
    assert line(gb, 10) == ("30 FPS", "OFF") and not is_on(gb)
    tap(gb, "left")
    assert line(gb, 10) == ("30 FPS", "ON") and is_on(gb)
    gb.press("b", 2)                                    # back to the game, 30 fps on: the picture follows every second step
    gb.run(6)
    assert gb.mem("game_state") == PLAYING and is_on(gb)
    f = gb.mem("frame_counter")
    gb.run(20)
    assert (gb.mem("frame_counter") - f) & 255 == 20     # (the game still takes a step every VBlank)


def test_the_cgb_never_runs_at_30_fps():
    """Even forced on, a CGB (its double speed is the other fix) keeps HALF_ON clear and takes a step and a picture every VBlank."""
    gb = Rom(ROM, "cgb")
    gb.run(120)
    gb.model_name = "cgb"
    gb.write(HALF, FORCE_ON)
    classic_at(gb, 25)
    assert not is_on(gb)
    gb.write("intro_timer", 0)
    xs = set()
    gb.hold("left")
    for _ in range(40):
        gb.run(1)
        xs.add(gb.oam()[0]["x"])
    assert gb.mem(HALF) & ON == 0
    gb.stop()
