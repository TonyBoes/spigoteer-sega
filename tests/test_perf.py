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
    """16 patrons, 20 mugs (full/empty/breaking/held), tip, show, serves, at level 9 speeds: more than the game
    can produce. It drops frames, but the music never skips a tick and no VRAM write happens outside VBlank."""
    ph.start_game(rom)
    ph.goto_level(rom, 8)
    rom.write("level", 9)
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
    assert r["missed"] <= 280, r
    assert r["end"] <= 230, r


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
