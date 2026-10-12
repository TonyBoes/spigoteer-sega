# Frame-time tests. The game records the scanline each frame's work ended on (perf_*), and counts frames that
# began outside VBlank or skipped one (missed_frames). Scenarios come from perf_helpers.py (state poked through
# symbol addresses). PyBoy's instruction timing is what is measured here; `make check` runs SameBoy as well.
import pytest
from gbtools import Rom
import re
from conftest import ROM, ROOT, bar_top_row
import perf_helpers as ph

BASE = int(re.search(r"#define PATRON_FIRST_TILE (\d+)", (ROOT / "build" / "art.h").read_text()).group(1))   # first patron tile

pytestmark = pytest.mark.timeout(300)
LEVEL8_FRAMES, WORST_FRAMES = 1200, 600
END_LY_TARGET = 118   # M8a: was 125; the bar lists are no longer rebuilt every frame


@pytest.fixture(params=["dmg", "cgb"])
def rom(request):
    with Rom(ROM, request.param) as gb:
        gb.run(120)
        gb.model_name = request.param
        yield gb


def assert_music_every_frame(ticks):
    """The driver ticked once per game frame (frame_counter, mod 256), never postponed: the running difference
    stays within the one tick a mid-frame sample can see."""
    f0, m0 = ticks[0]
    for f, m in ticks[1:]:
        if m < m0:
            f0, m0 = f, m                            # a tune restarted
            continue
        assert abs((m - m0) - ((f - f0) & 255)) <= 1 or (f - f0) & 255 > 200, (f0, f, m0, m)
        if (f - f0) & 255 > 200:
            f0, m0 = f, m


def test_level8_script_never_misses_a_frame(rom):
    ph.start_game(rom)
    ph.goto_level(rom, 8)
    rom.write("intro_timer", 0)
    ph.perf_reset(rom)
    ticks = []
    ph.play_script(rom, LEVEL8_FRAMES, keep=lambda gb, i: ticks.append((gb.mem("frame_counter"), gb.mem16("music_frames"))))
    r = ph.perf_read(rom)
    print(rom.model_name, "level 8 script", r)
    assert r["missed"] == 0, r
    assert r["end"] <= END_LY_TARGET, r
    assert_music_every_frame(ticks)
    assert rom.mem16("vq_late") == 0, "no drain was ever refused"
    assert 144 <= rom.mem("vq_drain_ly_max") <= rom.mem("vq_latest_ly"), "drains start early in VBlank"


def test_worst_case_pile(rom):
    """STRESS TEST beyond reachable play (the realistic peak is test_realistic_peak): 16 patrons, 20 mugs
    (full/empty/breaking/held), tip, show, serves, at level 10 speeds (the fastest row): more than the game can produce. It drops frames,
    but the music never skips a tick and no VRAM write happens outside VBlank."""
    ph.start_game(rom)
    ph.goto_level(rom, 10)                       # the last row, the fastest (the space lounge since the 10th venue)
    rom.write("intro_timer", 0)
    rom.write("tip_chance", 255)
    wc = ph.WorstCase(rom)
    wc.seed()
    rom.run(2)
    ph.perf_reset(rom)
    ticks = []
    for _ in range(WORST_FRAMES):
        wc.tick()
        rom.run(1)
        ticks.append((rom.mem("frame_counter"), rom.mem16("music_frames")))
    r = ph.perf_read(rom)
    print(rom.model_name, "worst case", r)
    assert_music_every_frame(ticks)
    assert rom.mem("vq_drain_ly_max") <= rom.mem("vq_latest_ly")
    # Not a target, a regression guard at the measured level: this pile needs more than one frame per frame
    # (measured: end LY ~190-200, ~200-230 of 600 frames late; before the rework: end ~540, missed ~185 with the
    # music tick skipped on late frames. M8a, lists kept incrementally: DMG end 176 / 48 late, CGB 227 / 67 late;
    # the CGB end is one frame whose start lands badly against VBlank, the rest stay under ~180).
    # M13a (b0b67f5): DMG 218 / 44 late, CGB 223 / 50 late (median logic LY 109).
    # M13b: DMG 208 / 205 late, CGB 206 / 212 late (median 130): the pile's walkers no longer queue behind each
    # other but pass, so far more patrons move and are redrawn every frame (queue ~14 -> ~27 DIV ticks a frame, mugs
    # and their drawing ~+10 with the extra catches), and every column change in the bunched crowd wakes the lift
    # chooser (~25 ticks a frame; no lift is possible here: the 20 mugs leave no OAM). Switching the chooser off alone
    # gives 113 / 117 late. Guard at the M13b level with a short margin.
    # M13c: DMG 220 / 229 late, CGB 221 / 232 late: the pile's replacement walkers are put at x 0, in the doorway, where
    # a BG patron is now clipped at the door (composed at every pixel, no quick redraws) and walks at EMERGE_SPEED.
    # No doors (2026-10-09): replacements are put at ENTRY_X 16 (where a BG patron may stand); served ones in the pile
    # find no sprite room (the 20 mugs) and go at once. DMG 278 / 244 late, CGB 278 / 245 late. The distribution is the
    # M13c one (DMG median end LY 157 vs 159, 90th percentile 188 vs 189, measured with the same script on both builds);
    # the worst frame is a pair of frames whose start lands badly against VBlank (logic LY ~270), which the same script
    # also shows on the M13c build (264, 255 late) though not in this test's run of it. Guard at the new level.
    assert r["missed"] <= 260, r
    assert r["end"] <= 290, r


def patron_cols(gb, bar):
    """Tile ids of the bar's two wall rows (BG map)."""
    tm = gb.bg_tilemap()
    return [[t & 0xFF for t in tm[bar_top_row(bar) + r][:20]] for r in range(2)]


def test_vram_queue_is_drained_only_inside_vblank(rom):
    """A frame whose drain would start outside VBlank keeps its copy list for the next VBlank: the BG map is not
    touched meanwhile, nothing is lost, and nothing more is queued on top. (The window the drain may start in is
    the variable vq_latest_ly; moving it below 144 makes every LY 'outside VBlank'.)"""
    ph.start_game(rom)
    rom.write("tip_chance", 0)
    rom.write("intro_timer", 255)                 # nobody moves on his own
    st = list(rom.read("patron_state", 16))
    p = st.index(1)
    bar = rom.read("patron_bar", 16)[p]
    rom.run(2)
    before = patron_cols(rom, bar)
    latest = rom.mem("vq_latest_ly")
    rom.write("vq_latest_ly", 0)                  # from now on no LY counts as VBlank
    ph.put(rom, "patron_x", p, 64)                # the patron jumps: columns 0-2 and 8-10 change
    late0 = rom.mem16("vq_late")
    rom.write("hud_dirty", 3)
    for _ in range(10):
        rom.run(1)
        assert patron_cols(rom, bar) == before, "no BG write while the drain is refused"
        assert rom.mem("vq_held") == 1 and rom.mem("vq_count") <= 12
    assert rom.mem16("vq_late") - late0 >= 9
    rom.write("vq_latest_ly", latest)
    rom.run(3)
    after = patron_cols(rom, bar)
    assert rom.mem("vq_held") == 0 and rom.mem16("vq_late") - late0 <= 11
    assert all(t < BASE for t in after[0][0:3]), "the old columns are wall again"
    assert all(t >= BASE for t in after[0][8:11]) and after != before, "the patron is drawn at x 64 (columns 8-10)"


# ---- M13b: the overlap scenario on the fastest row (level 10) ------------------------------------------------------------------------------
OVERLAP_FRAMES = 1200


def oam_line_counts(gb):
    c = [0] * 144
    n = 0
    for s in gb.oam():
        if not s["y"] or s["y"] >= 160:
            continue
        n += 1
        y = s["y"] - 16
        for line in range(max(0, y), min(144, y + 16)):
            c[line] += 1
    return max(c), n


def test_level9_overlap_scenario(rom):
    """STRESS TEST beyond reachable play (12 patrons, 16 mugs; the realistic peak is test_realistic_peak).
    Level 10 (the fastest row; level 9 before the 10th venue), on every bar a pushed patron sliding back through a pair of overlapping walkers, 4 mugs per bar
    (perf_helpers.OverlapCase), 1200 frames: never more than 10 objects on a line or 40 in all, the music never skips a
    tick, no VRAM write outside VBlank.

    The owner's frame-time target for this scenario (0 missed frames, end LY <= END_LY_TARGET) is NOT met (M13b): 12
    patrons and 16 mugs cost more than a frame in this engine whatever the overlap code does (measured with the chooser
    and lifts switched off: median end LY 84, worst 134, 1 frame late; with them: median ~117, worst ~185, ~20 % of
    frames late). What is asserted on frame time is a regression guard at the measured level, like the worst-case pile."""
    worst = {"line": 0, "entries": 0}
    ticks = []

    def check(gb, i):
        line, n = oam_line_counts(gb)
        worst["line"] = max(worst["line"], line)
        worst["entries"] = max(worst["entries"], n)
        assert line <= 10 and n <= 40, (i, line, n)
        ticks.append((gb.mem("frame_counter"), gb.mem16("music_frames")))
    r = ph.overlap_run(rom, OVERLAP_FRAMES, check)
    print(rom.model_name, "level 10 overlap", r, worst, "lifts", rom.mem("lift_lifts"), "forced", rom.mem("lift_forced"))
    assert_music_every_frame(ticks)
    assert rom.mem("vq_drain_ly_max") <= rom.mem("vq_latest_ly")
    assert rom.mem("lift_lifts") > 0, "the scenario lifts patrons"
    # (guard; the target is END_LY_TARGET and 0, see above. M13b 175 / 229, 180 / 264; M13c 171 / 259, 176 / 299;
    # no doors: DMG 175 / 268, CGB 179 / 299; 10th venue, the aliens' row from level 9's clear: DMG 172 / 289, CGB
    # 193 / 310; the mosh pit's ROM0 hooks (a test of mosh_on for every walker and pushed patron, off here): DMG
    # 186 / 301, CGB 184 / 326)
    assert r["end"] <= 200 and r["missed"] <= 340, r


# ---- M13c: the realistic peak of play -------------------------------------------------------------------------------
REALISTIC_FRAMES = 1200
_realistic = {}


def realistic(rom):
    """Run the scenario once per model (both tests below read the result)."""
    if rom.model_name not in _realistic:
        worst = {"line": 0, "entries": 0}
        ticks = []

        def check(gb, i):
            line, n = oam_line_counts(gb)
            worst["line"] = max(worst["line"], line)
            worst["entries"] = max(worst["entries"], n)
            ticks.append((gb.mem("frame_counter"), gb.mem16("music_frames"), line, n, i))
        r, s, lifts = ph.realistic_run(rom, REALISTIC_FRAMES, check)
        n = len(s["patrons"])
        summary = dict(patrons_mean=round(sum(s["patrons"]) / n, 2), patrons_max=max(s["patrons"]), mugs_max=max(s["mugs"]),
                       full_max=max(s["full"]), empty_max=max(s["empty"]), held_max=max(s["held"]),
                       mugs_mean=round(sum(s["mugs"]) / n, 2), edge_frames=s["edge"], leaving_frames=s["leaving"],
                       hurried=len(s["hurried"]),
                       tip=s["tip"], show=s["show"], both=s["both"], spawned=s["spawned"], lifts=lifts)
        print(rom.model_name, "realistic peak", r, worst, summary)
        _realistic[rom.model_name] = (r, worst, summary, ticks, rom.mem("vq_drain_ly_max") <= rom.mem("vq_latest_ly"))
    return _realistic[rom.model_name]


def test_realistic_peak(rom):
    """Level 10 (the fastest row) at the most real play produces, kept up as a steady state for REALISTIC_FRAMES
    frames: never more than 10 objects on a line or 40 in all, the music never skips a tick, no VRAM write outside VBlank.

    Why this is the peak (the game's own limits on the fastest row, level 10, the space lounge since the 10th venue (it
    was level 9, the zoo): spawn interval 210 frames, quota 16, step 52 frames per 8 px, empty gap 80 frames):
      - patrons: one arrives every 210 frames and takes ~11 s from the left end to the tap, pushes keep them in longer:
        about 8 on screen at once; hurried ones (1 in 4) among them, pushed ones sliding back through the others (lifts),
        new ones sliding in from the left edge and served ones sliding out past it (sprites);
      - full mugs: one bartender fills for 16 frames and a mug slides ~104 px at 2 px a frame (~52 frames): at most 3 in
        flight;
      - empties: fair empties keep their arrivals >= 80 frames apart and one slides ~200 frames: at most 3 at once;
      - held mugs: one per drinker (~4 of the 8);
      - a tip lies on the counter OR the show runs (picking a tip up starts the show), never both on screen.
    perf_helpers.RealisticPeak keeps that up. The frame-time target (0 missed, end LY <= END_LY_TARGET) is NOT met: see
    test_realistic_peak_frame_time_target (strict xfail) for the measured numbers. Here: a regression guard at the
    measured level. The level-10 overlap scenario and the worst-case pile are stress tests beyond reachable play."""
    r, worst, summary, ticks, drain_ok = realistic(rom)
    # the scenario is what it says (empties: 3 at most before each frame; one more may be sent during it; full mugs:
    # the scenario keeps 3 in flight at most before each frame, and the scripted bartender's own launch may make a 4th:
    # which frames that happens on depends on the frame timing, so a few cycles more or less anywhere in the frame can
    # show it, as the boss engine's ROM0 compares did on CGB)
    assert 7 <= summary["patrons_mean"] <= 9 and summary["patrons_max"] <= 10, summary
    assert summary["full_max"] <= 4 and summary["empty_max"] <= 4 and 8 <= summary["mugs_max"] <= 11, summary
    assert summary["edge_frames"] > 0 and summary["leaving_frames"] > 0 and summary["spawned"] >= 3 and summary["hurried"] >= 2, summary
    assert summary["lifts"] > 0 and summary["tip"] > 0 and summary["show"] > 0 and summary["both"] == 0, summary
    # the budgets, every frame
    assert all(line <= 10 and n <= 40 for _, _, line, n, _ in ticks), [t for t in ticks if t[2] > 10 or t[3] > 40][:5]
    assert_music_every_frame([(f, m) for f, m, _, _, _ in ticks])
    assert drain_ok
    # regression guard (measured M13c: DMG end 190-195 / 59-65 missed, CGB 208 / 88 missed of 1200; no doors, served
    # patrons sliding out as sprites: DMG 187 / 59, CGB 193 / 99. 10th venue: the row is reached straight from level 9's
    # clear (no bonus round), the aliens' art, and the scenario keeps up to 10 patrons (it ran at 9: from this start its
    # mean fell to 6.4-6.8, under the ~8 the arithmetic above gives): DMG 198 / 95, CGB 208 / 126)
    assert r["end"] <= 230 and r["missed"] <= 140, r


@pytest.mark.xfail(strict=True, reason="owner target NOT met at the realistic peak (PyBoy; no doors): DMG end LY ~187, "
                   "~59 of 1200 frames missed; CGB end LY ~193, ~99 missed. Per frame (M13c) (median, DIV ticks, ~1.8 a line): "
                   "update_patrons ~35, draw_mugs + draw_lifted ~43, lift_frame ~29, update_mugs ~22, queue_vram ~15. "
                   "Meeting it needs those paths cheaper, not tuning; this test turns XPASS (fails) once it is met.")
def test_realistic_peak_frame_time_target(rom):
    r = realistic(rom)[0]
    assert r["missed"] == 0 and r["end"] <= END_LY_TARGET, r


# ---- Modes P4: CLASSIC's busiest layout (level 12: R L R L, every bar's cap 4) --------------------------------------------
CLASSIC_FRAMES = 1200


@pytest.mark.parametrize("dirs", [0x5, 0x0])
def test_classic_peak(rom, dirs):
    """A MEASUREMENT, not a target (owner 2026-10-11: fit as many patrons as possible, tune nothing yet): CLASSIC level
    12's layout (R L R L, up to 4 patrons a bar) at the fastest row's speeds, perf_helpers.ClassicPeak; dirs 0 is the
    same scenario with every bar L, for comparison. The budgets hold every frame (<= 10 objects a line, <= 40 in all),
    the music never skips a tick, no VRAM write outside VBlank. The frame time is only guarded against getting much worse
    (numbers in PLAN.md, "Three modes P3-P4 as built"; it runs late on a third or more of its frames on both models)."""
    ticks = []

    def check(gb, i):
        line, n = oam_line_counts(gb)
        ticks.append((gb.mem("frame_counter"), gb.mem16("music_frames"), line, n))
    r, s, lifts = ph.realistic_run(rom, CLASSIC_FRAMES, check, target=16, dirs=dirs, cls=ph.ClassicPeak)
    n = len(s["patrons"])
    mean = round(sum(s["patrons"]) / n, 2)
    print(rom.model_name, "classic peak", hex(dirs), r, "patrons mean", mean, "max", max(s["patrons"]),
          "mugs max", max(s["mugs"]), "lifts", lifts, "worst line", max(t[2] for t in ticks), "entries", max(t[3] for t in ticks))
    assert rom.mem("bar_dirs") == dirs
    assert 10 <= mean and max(s["patrons"]) <= 16, (mean, max(s["patrons"]))
    assert all(line <= 10 and k <= 40 for _, _, line, k in ticks), [t for t in ticks if t[2] > 10 or t[3] > 40][:5]
    assert_music_every_frame([(f, m) for f, m, _, _ in ticks])
    assert rom.mem("vq_drain_ly_max") <= rom.mem("vq_latest_ly")
    # guard only (measured P4, PyBoy: R L R L DMG end 329 / 440 missed of 1200, CGB 315 / 575; every bar L DMG 283 / 335,
    # CGB 289 / 402; the scenario's patron count depends on the frame timing: mean 11-14.6 of up to 16)
    assert r["end"] <= 450 and r["missed"] <= 900, r
