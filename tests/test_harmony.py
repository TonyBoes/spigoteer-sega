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
CHECKED = [n for n in WITH_HARMONY if "harm_tune" in songs.SONGS[n]]    # (the credits tune's thirds are the draft's own: tests/test_credits.py)


def harm_regs(name):
    """(NR11 duty bits, NR12) of the tune's two harmony instruments."""
    return {(gm.HARM_INST[k][0] & 0xC0, gm.HARM_INST[k][1]) for k in songs.SONGS[name]["ch1_inst"]}


def total_rows(name):
    return gm.build(name, songs.SONGS[name], False)["total"]


# ---- the lines themselves (no emulator) -----------------------------------------------------------------------------
@pytest.mark.parametrize("name", CHECKED)
def test_the_harmony_stays_in_key_under_the_melody_and_lasts_the_tune(name):
    t = songs.SONGS[name]
    ev = gm.harm_events(name, t, total_rows(name))     # (asserts: as many rows as the tune, so it loops with it)
    assert ev and any(note is not None for _, note, _ in ev)
    probs = H.check(t["harm_tune"], t["ch1"])
    assert not probs, f"{name}: " + "; ".join(probs[:6])


@pytest.mark.parametrize("name", CHECKED)
def test_the_harmony_does_not_double_the_melody(name):
    """Never the melody in unison for long: at most a tenth of the tune's rows have the harmony on the melody's pitch."""
    t = songs.SONGS[name]
    tune = t["harm_tune"]
    same = sum(1 for s, n, p in H.timeline(t["ch1"]) if p is not None for r in range(s, s + n) if tune.mel[r] == p)
    assert same <= total_rows(name) // 10, f"{name}: {same} rows in unison with the melody"


def test_galops_harmony_is_a_counter_melody_a_third_or_sixth_under_the_melody():
    """Galop infernal (the shows, the owner's v2 arrangement): the channel-1 harmony is the 50% "voice", a line in the melody's own
    rhythm under it (thirds and sixths, chord tones under the held and stabbed bars), the whole 16 bars (64 rows), no clash with
    tools/harmony.py's check, and every note below the melody's note on the same row."""
    assert "galop" in WITH_HARMONY, "the Galop has its harmony"
    t = songs.SONGS["galop"]
    assert t["ch1_inst"] == ("voice", "voice") and total_rows("galop") == 64
    assert H.check(t["harm_tune"], t["ch1"]) == []
    tune = t["harm_tune"]
    tl = [(s, n, p) for s, n, p in H.timeline(t["ch1"]) if p is not None]
    assert len(tl) == 50, len(tl)   # (a repeated stab note ties into one)
    for s, n, p in tl:
        assert p < tune.mel[s] and tune.mel[s] - p in (3, 4, 8, 9, 5, 7, 6, 10, 12, 15, 16), (s, H.name_of(p), H.name_of(tune.mel[s]))


def test_harmony_instruments_sit_under_the_melody_and_the_effects():
    """The harmony's volume is 4-5 (song lead and lead 8, legato lead 6), its duty 12.5%, 25% or (harm50, the Entertainer's thirds) 50%, always
    quieter than the melody's volume (ring50, the credits tune's ringing last chord, is 9: under its ring lead's 12); the channel-1 effects are volume 8-12, so an effect is always louder than the line it interrupts."""
    music_c = (ROOT / "src" / "music.c").read_text()
    effects = [int(v, 16) for v in re.findall(r"\{ 0, 0x[0-9A-F]{2}, (0x[0-9A-F]{2}), N\(", music_c)]
    assert len(effects) == 7 and min(e >> 4 for e in effects) >= 8, effects
    for k, (duty, env) in gm.HARM_INST.items():
        assert duty in (0x00, 0x40, 0x80), (k, hex(duty))
        if k in ("voice", "vstab"):   # the show tune's counter-melody voice, and the unused arpeggio-stab voice: volume 6 (a line that carries the pause mix)
            assert env >> 4 == 6 and not env & 8, (k, hex(env))
            continue
        if k == "ring50":       # the credits tune's final chord rings (owner's pick of draft D3c): volume 9, a slow decay, under the "ring" lead (12)
            assert env >> 4 == 9 and not env & 8 and env >> 4 < gm.DUTY[songs.DUTY_RING - 1][2] >> 4, hex(env)
            continue
        assert 3 <= env >> 4 <= 5 and not env & 8, (k, hex(env))
        assert env >> 4 < gm.DUTY[gm.LEAD_LEGATO - 1][2] >> 4 <= gm.DUTY[0][2] >> 4


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
    tab = re.search(r"harm_tab\[TUNE_ALL\] = \{(.*?)\};", data).group(1).split(", ")
    want = [f"harm_{n}" if gm.SOURCE.get(n) in WITH_HARMONY else "NULL" for n in gm.TUNES]
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


@pytest.mark.parametrize("sfx,duty,env,frames", [(SFX_COIN, 0x80, 0xC1, 15), (SFX_EXTRA, 0x40, 0xD2, 33)])
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
    for sfx, env, frames in ((SFX_COIN, 0xC1, 15), (SFX_EXTRA, 0xD2, 33), (SFX_COIN, 0xC1, 15)):
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


def test_mountains_harmony_starts_in_step_with_the_melody_at_the_pickup(srom):
    """Mountain's first play begins on song row 248 (the "She'll be" pickup, songs.py start=).  The harmony must begin on
    the same row of its own line: every frame, channel 1 holds what the line has at the driver's row (the pad's envelope
    and the event's pitch, or the silent 0x08 for a rest), through the pickup, the wrap to row 0 and into bar 1."""
    from test_jukebox import hold_stage_anim, tap, to_jukebox
    t = songs.SONGS["mountain"]
    assert t["ch1"] and t["start"] == 248
    ev = gm.harm_events("mountain", t, total_rows("mountain"))
    line = []                                            # the event covering each song row
    for n, note, _ in ev:
        line += [note] * n
    env = gm.HARM_INST[t["ch1_inst"][0]][1]
    tune = TUNE_VENUE0 + songs.VENUES.index("mountain")
    hold_stage_anim(srom)
    srom.write("tune_unlocked", 0xFF)
    srom.write(srom.addr("tune_unlocked") + 1, 0xFF)
    to_jukebox(srom)
    while srom.mem("jb_sel") != tune:
        tap(srom, "down")
    srom.press("a", 2)
    assert srom.mem("cur_tune") == tune
    srom.write("music_frames", 0)
    srom.write(srom.addr("music_frames") + 1, 0)
    started, checked, rows_seen, pickup = False, 0, [], []
    for _ in range(80 + 40 * t["tempo"]):
        srom.pb.memory[NR51] = 0x11                      # channel 1 only: the harmony
        srom.run(1)
        srom.pb.memory[NR51] = 0x11
        if not started:
            if srom.mem16("music_frames") == 0:
                continue
            started = True
        row = srom.mem("hUGE_current_order") // 2 * 64 + srom.mem("hUGE_row")
        if srom.mem("hUGE_tick") == 0:                   # (the driver steps its row counter on a row's last tick)
            row = rows_seen[-1] if rows_seen else row
        rows_seen.append(row)
        note = line[row]
        if note is None:
            assert srom.mem(NR12) == 0x08, (row, hex(srom.mem(NR12)))
        else:
            assert srom.mem(NR12) == env, (row, hex(srom.mem(NR12)))
            if row == 248 and len(pickup) < 8 * t["tempo"]:
                pickup.append(srom.pb.sound.ndarray.copy())
        checked += 1
    srom.pb.memory[NR51] = 0xFF
    from check_music import detect
    want = 440 * 2 ** ((line[248] + 36 - 69) / 12)
    flat = np.concatenate(pickup).astype(float).mean(axis=1)
    heard = detect(flat, srom.pb.sound.sample_rate, 100, 1500)
    assert abs(heard - want) / want < 0.04, f"the harmony's first note is {heard:.0f} Hz, the line's row 248 is {want:.0f}"
    assert rows_seen[0] == 248 and 0 in rows_seen and rows_seen[-1] >= 24, rows_seen[:3] + rows_seen[-3:]
    assert checked >= 30 * t["tempo"]


# ---- the owner's harmony picks (demos of 2026-10-12): which voice sounds in which bars -----------------------------------
# ("pad" held, "harm" thirds, "stab" stabs: gm.HARM_INST names; a rest takes no instrument, so only bars with notes count)
PICKED_SECTIONS = {
    "ballgame": [((1, 16), "pad"), ((17, 32), "harm")],        # held, then thirds
    "hall": [((1, 16), "harm")],                                # thirds all through
    "danube": [((1, 24), "harm"), ((25, 32), "pad")],           # thirds, the closing phrase held
    "weasel": [((1, 8), "stab"), ((9, 16), "harm")],            # stabs, then thirds
}


def instrument_by_bar(name):
    t = songs.SONGS[name]
    bar = t["harm_tune"].bar
    ev = gm.harm_events(name, t, total_rows(name))
    by_bar, row = {}, 0
    for n, note, inst in ev:
        for r in range(row, row + n):
            if note is not None:
                by_bar.setdefault(r // bar + 1, set()).add(t["ch1_inst"][inst])
        row += n
    return by_bar


@pytest.mark.parametrize("name", sorted(PICKED_SECTIONS))
def test_the_picked_harmony_sections_use_their_voices(name):
    by_bar = instrument_by_bar(name)
    for (a, b), inst in PICKED_SECTIONS[name]:
        for bar in range(a, b + 1):
            assert by_bar.get(bar, {inst}) == {inst}, f"{name} bar {bar}: {by_bar.get(bar)} not {inst}"
        assert any(by_bar.get(bar) for bar in range(a, b + 1)), f"{name} bars {a}-{b} have notes"


@pytest.mark.parametrize("name", sorted(PICKED_SECTIONS))
def test_thirds_follow_every_melody_note_held_is_a_note_a_bar_and_stabs_are_four_a_bar(name):
    """Thirds (grid 1, no merging): a note starts on every melody note start; pad: a moving inner voice, three notes a bar at most (batch 1;
    it was one note a bar before); stabs: four a 6/8 bar."""
    t = songs.SONGS[name]
    tune = t["harm_tune"]
    starts = {s for s, n, p in H.timeline(t["ch1"]) if p is not None}
    for (a, b), inst in PICKED_SECTIONS[name]:
        rows = range((a - 1) * tune.bar, b * tune.bar)
        have = [r for r in rows if r in starts]
        if inst == "harm":
            missed = [r for r in rows if r in tune.onsets and tune.mel[r] is not None and r not in starts]
            assert not missed, f"{name} {a}-{b}: melody notes without a third: {missed[:6]}"
        elif inst == "pad":
            assert 0 < len(have) <= 3 * (b - a + 1), f"{name} {a}-{b}: the pad's inner voice, three notes a bar at most (batch 1: it moves under the long notes)"
        else:
            assert len(have) == (b - a + 1) * 4, f"{name} {a}-{b}: stabs, four a 6/8 bar"


@pytest.mark.parametrize("name", ["hall", "danube", "ballgame", "weasel"])
def test_the_picked_lines_never_cross_above_the_melody(name):
    t = songs.SONGS[name]
    tune = t["harm_tune"]
    for s, n, p in H.timeline(t["ch1"]):
        if p is not None:
            assert all(tune.mel[r] is None or p <= tune.mel[r] for r in range(s, s + n)), f"{name}: row {s} {H.name_of(p)} above the melody"


def test_the_funiculi_tempo_is_swung_126_bpm_and_its_harmony_is_unchanged():
    """Rows of 10 and 9 frames (swing 0xAA like the Entertainer, 9.5 on average): a dotted quarter of 3 rows is 28.5 frames
    = 126.3 bpm; GAME_BPM says 126.  The harmony is the verse in thirds, the chorus held (as before)."""
    s = songs.SONGS["funicula"]
    assert s["tempo"] == 10 and s["swing"] == 0xAA and songs.GAME_BPM["funicula"] == 126
    avg = s["tempo"] - bin(s["swing"]).count("1") / 8
    assert abs(3600 / (avg * 3) - 126) < 1
    assert gm.row_starts(10, 0xAA, 150)[-1] == 1425, "150 rows: 75 of 10 frames and 75 of 9"
    src = (ROOT / "build" / "music_data.c").read_text()
    assert "groove_venue3[] = {6, 170," in src
    assert re.search(r"\{&song_venue3, 1, 1425, ", src)
    by_bar = instrument_by_bar("funicula")
    assert by_bar.get(1) == {"harm"} and by_bar.get(18) == {"pad"}
