# The effects added for Taiko Pour's drum (SFX_DON, SFX_KA) and Duke's engine (SFX_REV). SFX_DON / SFX_KA are the noise layer
# on channel 4 under the pulse drum src/tk.c plays itself (default sound balance D3, src/music.h TAIKO_VARIANT: the player's hits
# are the lead, the tune sits behind them); SFX_REV is on channel 4 too. Started by a request bit (sfx_req, bit id - 1) and
# stepped by src/music.c voice_tick, one frame per count.
import numpy as np
import pytest
from test_harmony import request
from test_sound import NR52, sgb, srom  # noqa: F401  (fixtures)

pytestmark = pytest.mark.timeout(120)
NR12, NR22, NR42, NR43, NR51 = 0xFF12, 0xFF17, 0xFF21, 0xFF22, 0xFF25
SFX_DON, SFX_KA, SFX_REV = 10, 11, 12
MASK_TAIKO = 0x70                    # music.h TK_NOGROOVE | TK_NOHARM | TK_NOMELODY (the driver's channel-2 bit toggles in D3)


def trace(gb, sfx, n):
    """(NR42, NR43) after each of n frames, from the request on (the effect's first step is written in frame 1)."""
    request(gb, sfx)
    out = []
    for _ in range(n):
        gb.run(1)
        out.append((gb.mem(NR42), gb.mem(NR43)))
    return out


def settle(gb):
    gb.run(300)          # (the title's own sounds are over)


@pytest.mark.only_model('dmg')
def test_don_noise_is_a_short_knock(sgb):
    settle(sgb)
    t = trace(sgb, SFX_DON, 6)
    assert [x[1] for x in t[:2]] == [0x62, 0x74] and all(x[0] == 0xC1 for x in t[:2]), t
    assert t[2][0] == 0, "2 frames in all: the pulse body (src/tk.c) carries the drum, the noise is its knock"


@pytest.mark.only_model('dmg')
def test_ka_noise_is_a_tick(sgb):
    settle(sgb)
    t = trace(sgb, SFX_KA, 6)
    assert [x[1] for x in t[:3]] == [0x10, 0x09, 0x09] and all(x[0] == 0xC1 for x in t[:3]), t
    assert t[3][0] == 0, "3 frames in all: short enough for eighth-note pairs 12 frames apart"


def taiko_rom(model, music):
    """Taiko Pour in practice with sound emulation (registers read back), the tune on or off."""
    from conftest import hold_stage_anim
    from test_mg import MG_PRACTICE, mg_enter
    from test_sound import make_rom
    from tk_helpers import MG_TAIKO
    gb = make_rom(model)
    gb.run(120)
    hold_stage_anim(gb)
    if not music:
        gb.write("sound_on", 0)
    mg_enter(gb, MG_TAIKO, MG_PRACTICE, 0x5A17)
    return gb


def hit(gb, lane):
    """A hit as src/tk.c hit() makes one (flash_t, the request), poked between two frames."""
    from tk_helpers import LAYOUT
    gb.write(gb.addr("story_scratch") + LAYOUT["flash_t"][0] + lane, 8)
    request(gb, SFX_KA if lane else SFX_DON)


def spectrum_peak(x, lo, hi, rate=48000):
    x = x.astype(float).mean(axis=1) if x.ndim > 1 else x.astype(float)
    f = np.abs(np.fft.rfft(x * np.hanning(len(x)), 1 << 15))
    fr = np.fft.rfftfreq(1 << 15, 1 / rate)
    band = (fr >= lo) & (fr <= hi)
    return fr[band][f[band].argmax()]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_hits_are_pulse_drums_on_the_melody_channels(model):
    """The pulse body of the drum (src/tk.c drum): a DON triggers channel 1 (D3; channel 2 is the melody's) at full volume (envelope 0xF2) and its pitch
    falls from the knock through ~120 Hz to ~85 Hz; a KA is a short click (a high period, ~2 kHz). Music off, so only the
    hits sound; the audio is the check (the period registers are write-only)."""
    from test_mg import to_play
    from test_sound import audio_frames
    with taiko_rom(model, music=False) as gb:
        to_play(gb)
        hit(gb, 0)
        gb.run(2)
        assert gb.mem(NR12) == 0xF2, "the drum is on channel 1 at volume 15"
        assert gb.mem(NR22) != 0xF2, "and not on channel 2 (the melody's)"
        a = audio_frames(gb, 10)
        assert spectrum_peak(a[len(a) // 4:], 60, 400, gb.pb.sound.sample_rate) < 260, "a thump: the pitch is down in the drum's range"
        assert np.abs(a).max() >= 15, "and loud: one full-volume pulse (D3)"
        gb.run(30)
        hit(gb, 1)
        k = audio_frames(gb, 4)
        assert spectrum_peak(k, 800, 6000, gb.pb.sound.sample_rate) > 1200, "a KA is a high click"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_hits_stand_over_the_tune(model):
    """The point of the rework: a DON is louder than the tune behind it (the bass line only) by a clear margin: its loudest
    samples against the loudest of the tune alone just before."""
    from test_mg import to_play
    from test_sound import audio_frames
    with taiko_rom(model, music=True) as gb:
        to_play(gb)
        gb.run(11)
        base = np.abs(audio_frames(gb, 60)).max()
        hit(gb, 0)
        loud = np.abs(audio_frames(gb, 8)).max()
        assert loud >= 1.6 * base, (loud, base)       # (was 2 x, then 1.8 x: the drum's loudest sample is 40 to 44 against the tune's 23 depending on the exact cycle the logic writes its registers on,
                                                      # which any change in the code moves; the claim is that a DON clearly stands over the tune)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_backing_steps_aside_and_comes_back(model):
    """While Taiko Pour runs (D3): the tune's drum groove and the channel-1 harmony are out and the melody is only let through
    on the first row of each half bar (rows 0 mod 4: the driver's channel-2 mute bit is clear on exactly those row-start ticks),
    the bass and melody are on the right side only (NR51 0x9F); leaving it (the result's B) puts all of it back."""
    from test_mg import GS_MGLIST, MG_RESULT, frames, to_play, until
    from test_flow import run_until, state
    with taiko_rom(model, music=True) as gb:
        to_play(gb)
        assert gb.mem("hUGE_mute_mask") & MASK_TAIKO == MASK_TAIKO and gb.mem(NR51) == 0x9F
        open_rows, shut_rows = set(), set()
        for _ in range(200):
            gb.run(1)
            if gb.mem("hUGE_tick") == 1:                 # (a row's first tick has just been played)
                (shut_rows if gb.mem("hUGE_mute_mask") & 2 else open_rows).add(gb.mem("hUGE_row") % 4)
        assert open_rows == {0}, open_rows
        assert shut_rows == {1, 2, 3}, shut_rows
        gb.write("mg_phase", MG_RESULT)
        until(gb, lambda: gb.mem("overlay_on") == 1, 20)
        frames(gb, 2)
        assert gb.mem("hUGE_mute_mask") & MASK_TAIKO == MASK_TAIKO
        gb.press("b", 2)
        run_until(gb, lambda: state(gb) == GS_MGLIST and gb.pb.memory[0xFF40] & 0x80, 30)
        gb.run(5)
        assert gb.mem("hUGE_mute_mask") & 0x72 == 0, "the melody, groove and harmony are back"
        assert gb.mem(NR51) == 0xFF


@pytest.mark.only_model('dmg')
def test_rev_climbs_for_fifty_frames(sgb):
    settle(sgb)
    t = trace(sgb, SFX_REV, 54)
    steps = [x[1] for x in t[:49]]
    runs = [(v, steps.count(v)) for v in dict.fromkeys(steps)]
    assert runs == [(0x4B, 9), (0x4A, 10), (0x3B, 10), (0x3A, 10), (0x39, 10)], runs   # (the first step shares its frame with the request)
    assert all(x[0] == 0xD0 for x in t[:49]) and t[49][0] == 0, "49 frames, then the DAC is off"


def test_the_tunes_drum_groove_steps_aside_in_taiko_pour():
    """The player's drums replace the teahouse tune's own channel-4 groove while Taiko Pour is up (src/music.h TK_NOGROOVE, set by src/tk.c):
    from the tune's first frames to just before the first note, no drum is written to channel 4 (NR42 / NR43 never change)."""
    from conftest import hold_stage_anim
    from test_mg import MG_PRACTICE, mg_enter
    from test_sound import make_rom
    from tk_helpers import MG_TAIKO, tk
    gb = make_rom("dmg")                # (with sound: the sound registers read back)
    gb.run(120)
    hold_stage_anim(gb)
    mg_enter(gb, MG_TAIKO, MG_PRACTICE, 0x5A17)
    for _ in range(600):
        if tk(gb)["clk"] >= 1:
            break
        gb.run(1)
    seen = set()
    for _ in range(110):
        gb.run(1)
        seen.add((gb.mem(NR42), gb.mem(NR43)))
    assert 100 < tk(gb)["clk"] < 285, "the tune is running, the first note (frame 288) not yet played"
    assert len(seen) == 1, f"channel 4 was written: {seen}"
