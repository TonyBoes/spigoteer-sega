# Music step 5: the channel-1 harmony (owner: "use the silent channel 1 for music: a harmony line / counter-melody on every
# tune that steps aside whenever a sound effect needs channel 1 and comes back cleanly afterwards; effects must stay louder
# than the music and never be cut by it").  The lines are tools/songs.py harmony() calls (made with tools/harmony.py),
# packed by tools/gen_music.py (harm_<tune>, bank HARM_BANK) and played by src/music.c harm_tick, not by hUGEDriver: a
# fourth pattern per order would not fit WRAM (buffer A is 8 patterns, the 4-order tunes would need 12).
import re
import sys

import numpy as np
import pytest
from conftest import ROOT
from test_sound import NR52, TUNE_VENUE0, audio_frames, sgb, srom  # noqa: F401  (fixtures)

sys.path.insert(0, str(ROOT / "tools"))
import gen_music as gm       # noqa: E402
import harmony as H          # noqa: E402
import songs                 # noqa: E402

pytestmark = pytest.mark.timeout(180)

NR10, NR11, NR12, NR51 = 0xFF10, 0xFF11, 0xFF12, 0xFF25
SFX_COIN, SFX_EXTRA = 6, 9
WITH_HARMONY = [n for n, t in songs.SONGS.items() if t.get("ch1")]


def harm_regs(name):
    """(NR11 duty bits, NR12) of the tune's two harmony instruments."""
    return {(gm.HARM_INST[k][0] & 0xC0, gm.HARM_INST[k][1]) for k in songs.SONGS[name]["ch1_inst"]}


def total_rows(name):
    return gm.build(name, songs.SONGS[name], False)["total"]


# ---- the lines themselves (no emulator) -----------------------------------------------------------------------------
@pytest.mark.parametrize("name", WITH_HARMONY)
def test_the_harmony_stays_in_key_under_the_melody_and_lasts_the_tune(name):
    t = songs.SONGS[name]
    ev = gm.harm_events(name, t, total_rows(name))     # (asserts: as many rows as the tune, so it loops with it)
    assert ev and any(note is not None for _, note, _ in ev)
    probs = H.check(t["harm_tune"], t["ch1"])
    assert not probs, f"{name}: " + "; ".join(probs[:6])


@pytest.mark.parametrize("name", WITH_HARMONY)
def test_the_harmony_does_not_double_the_melody(name):
    """Never the melody in unison for long: at most a tenth of the tune's rows have the harmony on the melody's pitch."""
    t = songs.SONGS[name]
    tune = t["harm_tune"]
    same = sum(1 for s, n, p in H.timeline(t["ch1"]) if p is not None for r in range(s, s + n) if tune.mel[r] == p)
    assert same <= total_rows(name) // 10, f"{name}: {same} rows in unison with the melody"


def test_harmony_instruments_sit_under_the_melody_and_the_effects():
    """The harmony's volume is 4-5 (song lead and lead 8, legato lead 6), its duty 12.5% or 25% (the melody's 50%);
    the channel-1 effects are volume 8-12, so an effect is always louder than the line it interrupts."""
    music_c = (ROOT / "src" / "music.c").read_text()
    effects = [int(v, 16) for v in re.findall(r"\{ 0, 0x[0-9A-F]{2}, (0x[0-9A-F]{2}), N\(", music_c)]
    assert len(effects) == 7 and min(e >> 4 for e in effects) >= 8, effects
    for k, (duty, env) in gm.HARM_INST.items():
        assert duty in (0x00, 0x40), (k, hex(duty))
        assert 3 <= env >> 4 <= 5 and not env & 8, (k, hex(env))
        assert env >> 4 < gm.LEGATO_ENV >> 4 <= gm.DUTY[4][2] >> 4


def test_the_harmony_track_format():
    """header (duty A, envelope A, duty B, envelope B), events (note | 0x80 for instrument B, rows 1..255), 0 0."""
    for name in WITH_HARMONY:
        t = songs.SONGS[name]
        ev = gm.harm_events(name, t, total_rows(name))
        b = gm.harm_bytes(t, ev)
        assert b[:4] == [x for k in t["ch1_inst"] for x in gm.HARM_INST[k]]
        assert b[-2:] == [0, 0] and len(b) == 4 + 2 * len(ev) + 2
        for i in range(4, len(b) - 2, 2):
            assert 1 <= b[i + 1] <= 255 and ((b[i] & 0x7F) < 72 or b[i] == gm.HARM_REST)
    h = (ROOT / "src" / "music.h").read_text()
    assert f"#define HARM_BANK {gm.HARM_BANK}" in h and f"#define HARM_REST 0x{gm.HARM_REST:02X}" in h
    data = (ROOT / "build" / "music_data.c").read_text()
    tab = re.search(r"harm_tab\[TUNE_COUNT\] = \{(.*?)\};", data).group(1).split(", ")
    want = [f"harm_{n}" if gm.SOURCE.get(n) in WITH_HARMONY else "NULL" for n in gm.ORDER]
    assert tab == want


# ---- in the ROM: level 1 (Oh! Susanna) --------------------------------------------------------------------------------
def regs(gb):
    return gb.mem(NR11) & 0xC0, gb.mem(NR12)


def request(gb, sfx):
    a = gb.addr("sfx_req")
    bit = 1 << (sfx - 1)
    gb.write(a, gb.mem(a) | (bit & 0xFF))
    gb.write(a + 1, gb.mem(a + 1) | (bit >> 8))


def playing_harmony(sgb):
    if "susanna" not in WITH_HARMONY:
        pytest.skip("Oh! Susanna has no harmony yet")
    sgb.write("intro_timer", 255)
    sgb.run(20)
    assert sgb.mem("cur_tune") == TUNE_VENUE0
    return harm_regs("susanna")


def test_the_harmony_plays_on_channel_1_between_effects(sgb):
    inst = playing_harmony(sgb)
    seen, nr12 = set(), set()
    for _ in range(240):
        sgb.write("intro_timer", 255)
        sgb.run(1)
        seen.add(regs(sgb))
        nr12.add(sgb.mem(NR12))
    assert inst & seen, f"the harmony's instruments on channel 1 ({inst}), seen {seen}"
    assert nr12 <= {e for _, e in inst} | {0x08}, f"only the harmony's envelopes or a silent rest (0x08): {nr12}"


@pytest.mark.parametrize("sfx,duty,env,frames", [(SFX_COIN, 0x80, 0xC1, 13), (SFX_EXTRA, 0x40, 0xD2, 33)])
def test_the_harmony_steps_aside_for_an_effect_and_comes_back(sgb, sfx, duty, env, frames):
    """While the effect sounds, every frame channel 1 holds the effect's duty and envelope (the music writes nothing:
    the effect is not cut); then the harmony comes back on its own instrument.  The DAC is never switched off (NR12 is
    never 0x00: no click), and the effect's end leaves volume 0 (0x08) until the harmony strikes again."""
    inst = playing_harmony(sgb)
    request(sgb, sfx)
    sgb.run(1)
    trace = []
    for _ in range(frames - 1):
        sgb.write("intro_timer", 255)
        trace.append(regs(sgb))
        sgb.run(1)
    assert all(r == (duty, env) for r in trace), f"the effect's registers held: {trace}"
    after = []
    for _ in range(12 * songs.SONGS["susanna"]["tempo"]):       # a bar and a half: the line strikes a note in it
        sgb.write("intro_timer", 255)
        sgb.run(1)
        after.append(regs(sgb))
    assert all(r[1] != 0 for r in trace + after), "channel 1's DAC stays on"
    assert after[0][1] in {0x08} | {e for _, e in inst}, after[:3]
    assert inst & set(after), f"the harmony is back on channel 1: {after}"
    assert {r[1] for r in after} <= {e for _, e in inst} | {0x08}


def test_effects_on_channel_1_are_never_cut_by_the_harmony(sgb):
    """Two effects in a row and an extra life during a harmony note: each runs its whole length on its own registers."""
    playing_harmony(sgb)
    for sfx, env, frames in ((SFX_COIN, 0xC1, 13), (SFX_EXTRA, 0xD2, 33), (SFX_COIN, 0xC1, 13)):
        request(sgb, sfx)
        sgb.run(1)
        for _ in range(frames - 1):
            assert sgb.mem(NR12) == env
            sgb.run(1)
        sgb.run(5)


def test_the_harmony_is_audible_and_quieter_than_the_melody(sgb):
    """Channel 2 routed to the left output only, channel 1 to the right only (NR51 0x21), over the same two bars: the
    harmony is there (RMS of the samples), and below the melody."""
    playing_harmony(sgb)
    chunks = []
    for _ in range(16 * songs.SONGS["susanna"]["tempo"]):
        sgb.write("intro_timer", 255)
        sgb.pb.memory[NR51] = 0x21
        chunks.append(audio_frames(sgb, 1))
    a = np.concatenate(chunks).astype(float)
    rms = [float(np.sqrt(((x - x.mean()) ** 2).mean())) for x in (a[:, 1], a[:, 0])]   # channel 1, channel 2
    assert rms[0] > 0.5, f"channel 1 plays the harmony (RMS ch1 {rms[0]:.2f}, ch2 {rms[1]:.2f})"
    assert rms[0] < rms[1], f"the harmony sits under the melody (RMS ch1 {rms[0]:.2f}, ch2 {rms[1]:.2f})"
