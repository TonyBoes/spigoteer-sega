# The realistic peak on the CGB Saloon with the Color-only looks (3-7, tiles in VRAM bank 1) on screen. perf_helpers' scenarios gave
# every patron variant `p % 3`, so the looks 0-2 only: the bank-1 looks (and their OBJ palettes when lifted) were never part of a
# frame-time or object-count measurement. perf_helpers.SALOON_LOOKS makes variant_for(p) cycle all eight looks with real
# (look, palette instance) pairs; realistic_run(level=11) starts the LEVEL harness at the Saloon (loop 2: the venue, not the space lounge).
# The numeric guards are test_realistic_peak's (not raised); the existing tests are unchanged (SALOON_LOOKS is off for them).
import pytest
from gbtools import Rom
from conftest import ROM
import perf_helpers as ph
from test_perf import assert_typical, assert_music_every_frame, oam_line_counts

pytestmark = [pytest.mark.only_model("cgb"), pytest.mark.timeout(900)]
FRAMES = 1200


@pytest.fixture
def saloon_rom(monkeypatch):
    monkeypatch.setattr(ph, "SALOON_LOOKS", True)
    with Rom(ROM, "cgb") as gb:
        gb.run(120)
        gb.model_name = "cgb"
        yield gb


@pytest.fixture(params=["cgb"])
def model(request):                    # (only_model keys on the `model` parametrisation)
    return request.param


def test_the_realistic_peak_with_the_color_only_looks_on_screen(model, saloon_rom):
    gb = saloon_rom
    ticks, looks = [], set()

    def check(gb, i):
        line, n = oam_line_counts(gb)
        ticks.append((gb.mem("frame_counter"), gb.mem16("music_frames"), line, n))
        st, var = gb.read("patron_state", ph.MAX_P), gb.read("patron_variant", ph.MAX_P)
        looks.update(var[k] & 7 for k in range(ph.MAX_P) if st[k])
    r, s, lifts = ph.realistic_run(gb, FRAMES, check, level=11)
    print("saloon realistic peak", r, "looks seen", sorted(looks), "lifts", lifts, "worst line", max(t[2] for t in ticks),
          "entries", max(t[3] for t in ticks))
    assert {3, 4, 5, 6, 7} <= looks, f"the Color-only looks were not on screen: {sorted(looks)}"
    assert lifts > 0
    assert all(line <= 10 and n <= 40 for _, _, line, n in ticks), [t for t in ticks if t[2] > 10 or t[3] > 40][:5]
    assert_music_every_frame([(f, m) for f, m, _, _ in ticks])
    assert gb.mem("vq_drain_ly_max") <= gb.mem("vq_latest_ly")
    assert_typical(gb, mean=141, p90=178, p99=212)
