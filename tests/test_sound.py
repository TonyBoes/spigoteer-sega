# M7: music (hUGEDriver), sound effects, the saved hi score and the MUSIC ON/OFF switch.
# Register and audio checks need PyBoy's sound emulation, which the shared Rom wrapper leaves off
# (its sound registers read 0), so `sound_rom` swaps in a PyBoy with sound_emulated=True.
import re
import sys
from io import BytesIO

import numpy as np
import pytest
from conftest import GAME, K_SETTINGS, MENU_SETTLE, ROM, ROOT, title_level, title_pick, with_cards
from gbtools import Rom
from pyboy import PyBoy
from test_art import goto_group
from test_bonus import PH_SHAKE, enter_bonus, to_phase
from test_flow import (BONUS, GAME_OVER, LEVEL_CLEAR, LIFE_LOST, PLAYING, TITLE, clear_level, hi_score,
                       hi_shown, hi_tiles, inject_mug, lose_a_life, music_line, put, run_until, score, set_patron, state,
                       tile_id, tilemap_row, title_text_row)

pytestmark = pytest.mark.timeout(120)

SFX_NONE, SFX_FILL, SFX_LAUNCH, SFX_CATCH, SFX_BREAK, SFX_SERVE, SFX_COIN, SFX_LIFE, SFX_SHAKE, SFX_COUNT = range(10)
TUNE_TITLE, TUNE_CLEAR, TUNE_OVER, TUNE_BONUS, TUNE_SHOW, TUNE_VENUE0 = range(6)
TUNE_COUNT = TUNE_VENUE0 + 10          # (the venue tunes' end: TUNE_VENUE_END; music.h's TUNE_COUNT is 18 now)
TUNE_GAME = TUNE_VENUE0          # level 1: the cowboys' "Oh! Susanna"
TUNE_NONE = 255
MUG_EMPTY, PATRON_PUSHED = 2, 2
NR50, NR51, NR52 = 0xFF24, 0xFF25, 0xFF26

sys.path.insert(0, str(ROOT / "tools"))
import gen_music as gm       # noqa: E402  (the song sources: what each tune should play)
import songs                 # noqa: E402
import harmony as H          # noqa: E402
from check_music import detect, note_hz      # noqa: E402

GS_LEVEL_CLEAR = 3
GS_SCORES = 10


def sfx_count(gb, i):
    return gb.read("sfx_count", SFX_COUNT)[i]


def new_pyboy(model, ram=None, sound=True, cards=True):
    """cards: the cartridge has every HOW TO PLAY card seen (conftest.with_cards); False: as given."""
    if cards:
        ram = with_cards(ram)
    return PyBoy(str(ROM), window="null", sound_emulated=sound, cgb=(model == "cgb"), log_level="ERROR",
                 ram_file=BytesIO(ram) if ram is not None else None)


def make_rom(model, ram=None, sound=True, cards=True):
    """A Rom whose emulator has sound on and optionally a cartridge RAM image (the .sav contents)."""
    rom = Rom(ROM, model)
    rom.pb.stop(save=False)
    rom.pb = new_pyboy(model, ram, sound, cards)
    rom.pb.set_emulation_speed(0)
    rom.model_name = model
    return rom


def save_ram(rom):
    """Stop the emulator and return the battery RAM it would have written to the .sav file."""
    buf = BytesIO()
    rom.pb.stop(save=True, ram_file=buf)
    rom.pb = None
    return buf.getvalue()


def start_game(rom):
    title_level(rom)
    run_until(rom, lambda: state(rom) == PLAYING, 30)
    rom.write("tip_chance", 0)
    while rom.mem("intro_timer") > 44:
        rom.run(1)


@pytest.fixture(params=["dmg", "cgb"])
def srom(request):
    """Title screen with sound emulation on, once per model."""
    rom = make_rom(request.param)
    rom.run(120)
    yield rom
    rom.stop()


@pytest.fixture
def sgb(srom):
    start_game(srom)
    return srom


def silent(samples):
    return samples.astype(float).std() < 0.5


def audio_frames(rom, n):
    """Run n frames and return the stereo samples produced (int8, shape (samples, 2)). The last sample of each frame's
    buffer is left out: PyBoy takes it at the frame boundary, and with the wave channel's DAC on (muted, volume code 0)
    it can read a stray 16 there depending only on where the frame ends in the CPU's cycles, i.e. on the code layout."""
    chunks = []
    for _ in range(n):
        rom.run(1)
        chunks.append(rom.pb.sound.ndarray[:-1].copy())
    return np.concatenate(chunks)


# ---- sound effects: each trigger starts its effect --------------------------------------
@pytest.mark.only_model('dmg')
def test_filling_and_launching(gb):
    gb.write("intro_timer", 255)
    gb.hold("a")
    gb.run(2)
    assert gb.mem("last_sfx") == SFX_FILL and sfx_count(gb, SFX_FILL) == 1
    gb.run(30)
    assert sfx_count(gb, SFX_FILL) == 1, "one fill sound per fill"
    gb.release("a")
    gb.run(2)
    assert gb.mem("last_sfx") == SFX_LAUNCH and sfx_count(gb, SFX_LAUNCH) == 1


@pytest.mark.only_model('dmg')
def test_empty_caught(gb):
    gb.write("intro_timer", 255)
    inject_mug(gb, 0, gb.mem("bartender_x"), st=MUG_EMPTY)
    gb.run(2)
    assert gb.mem("last_sfx") == SFX_CATCH and sfx_count(gb, SFX_CATCH) == 1


@pytest.mark.only_model('dmg')
def test_glass_break_and_life_lost(gb):
    gb.write("intro_timer", 255)
    inject_mug(gb, 1, 17)                       # a full mug about to leave the left end
    run_until(gb, lambda: state(gb) == LIFE_LOST, 20)
    assert sfx_count(gb, SFX_BREAK) == 1 and sfx_count(gb, SFX_LIFE) == 1
    assert gb.mem("last_sfx") == SFX_LIFE


@pytest.mark.only_model('dmg')
def test_patron_reaching_the_tap_costs_a_life_without_a_break_sound(gb):
    lose_a_life(gb)
    assert sfx_count(gb, SFX_LIFE) == 1 and sfx_count(gb, SFX_BREAK) == 0


@pytest.mark.only_model('dmg')
def test_patron_served_at_the_left_end(gb):
    gb.write("intro_timer", 255)
    set_patron(gb, 0, GAME["ENTRY_X"], pstate=PATRON_PUSHED)
    put(gb, "patron_aux", gb.read("patron_state", 16).index(PATRON_PUSHED), 4)
    gb.run(2)
    assert gb.mem("last_sfx") == SFX_SERVE and sfx_count(gb, SFX_SERVE) == 1


@pytest.mark.only_model('dmg')
def test_coin_collected(gb):
    gb.write("intro_timer", 255)
    gb.write("tip_bar", gb.mem("bar"))
    gb.write("tip_x", gb.mem("bartender_x"))
    gb.write("tip_timer", 100)
    gb.run(2)
    assert gb.mem("last_sfx") == SFX_COIN and sfx_count(gb, SFX_COIN) == 1


@pytest.mark.only_model('dmg')
def test_can_shake_in_the_bonus_round(gb):
    enter_bonus(gb)
    before = sfx_count(gb, SFX_SHAKE)
    to_phase(gb, PH_SHAKE)
    gb.run(10)
    assert sfx_count(gb, SFX_SHAKE) > before and gb.mem("last_sfx") == SFX_SHAKE


# ---- the hardware really is being driven -----------------------------------------------
def test_sound_is_on_and_the_title_tune_plays(srom):
    nr52 = srom.mem(NR52)
    assert nr52 & 0x80, "APU on"
    assert srom.mem(NR51) == 0xFF and srom.mem(NR50) == 0x77
    assert srom.mem("cur_tune") == TUNE_TITLE
    row0, frames0 = srom.mem("hUGE_row"), srom.mem16("music_frames")
    seen = 0
    for _ in range(120):
        srom.run(1)
        seen |= srom.mem(NR52) & 0x0F
    # (on a row's first frame the tick can land just after the frame boundary PyBoy stops at: the count may lag by one)
    assert abs(srom.mem16("music_frames") - (frames0 + 120)) <= 1, "driver ticked once per frame"
    assert srom.mem("hUGE_row") != row0, "the song advances"
    want = 0xF if songs.SONGS["entertainer"]["ch1"] else 0xE      # music step 5: channel 1 plays the harmony
    assert seen == want, f"channels 1 (harmony), 2, 3 and 4 play the title tune (NR52 channel bits seen: {seen:#x})"


def test_music_is_audible_and_changes(srom):
    audio_frames(srom, 290)          # (the title's 4-bar intro is the same run three times: listen to the tune proper)
    a = audio_frames(srom, 60).astype(float)
    b = audio_frames(srom, 60).astype(float)
    assert a.std() > 2 and b.std() > 2, "not silent"
    mono_a, mono_b = a.mean(axis=1), b.mean(axis=1)
    # the two seconds have different spectra (a melody over a bass, not one held drone): the magnitude spectra up to 2 kHz
    # correlate less than a repeating drone would (the louder bass can hold one note, the melody dominates the peaks)
    sa = np.abs(np.fft.rfft(mono_a - mono_a.mean()))[:2000]
    sb = np.abs(np.fft.rfft(mono_b - mono_b.mean()))[:2000]
    corr = float(np.dot(sa, sb) / (np.linalg.norm(sa) * np.linalg.norm(sb)))
    assert corr < 0.9, f"the music changes from one second to the next (spectra correlate {corr:.2f})"


@pytest.mark.only_model('dmg')
def test_sfx_drive_channel_1_and_4_and_end(sgb):
    sgb.write("intro_timer", 255)
    sgb.hold("a")
    sgb.run(3)
    assert sgb.mem(NR52) & 1, "fill sound on channel 1"
    sgb.release("a")
    sgb.run(60)
    # music step 5: the effect's end leaves channel 1 at volume 0 with its DAC on (NR12 0x08, no click), and the level
    # tune's harmony takes the channel back (tests/test_harmony.py); before, the music did not use it and NR52 bit 0 cleared
    harm = {gm.HARM_INST[k][1] for k in songs.SONGS["susanna"]["ch1_inst"] or ()}
    assert sgb.mem(0xFF12) in {0x08} | harm, f"the effect let go of channel 1 (NR12 {sgb.mem(0xFF12):#x})"
    inject_mug(sgb, 1, 17)
    run_until(sgb, lambda: sfx_count(sgb, SFX_BREAK) == 1, 6)
    sgb.run(1)
    assert sgb.mem(NR52) & 8, "the break is a burst on the noise channel (4)"


NR12, NR32, NR42, NR43 = 0xFF12, 0xFF1C, 0xFF21, 0xFF22
SFX_PERFECT, SFX_EXTRA_ID = 15, 9
MUTE3 = 4                                   # hUGE_mute_mask bit 2: the driver leaves channel 3 alone
NO_WAVE = 100                               # hUGE_current_wave after hUGE_reset_wave: the next bass note reloads its wave
D5, FS5, A5, D6 = 587.33, 739.99, 880.0, 1174.66
TONE = 2 ** (1 / 6)


def request_perfect(sgb, streak):
    """Ask for the perfect pour's marimba with pour_streak `streak` (what launch_mug has just set) and let one music tick take it."""
    sgb.write("pour_streak", streak)
    sgb.write(sgb.addr("sfx_req") + 1, 0x40)
    sgb.run(1)


def track(sgb, streak, frames):
    """Request the marimba, then the pitch of each of the next `frames` frames (FFT of what the speaker plays: the period registers are write-only), Hz.
    One frame's audio is the last frame's notes as much as this one's (where in the frame the music ticks decides, and it moves with the loop's work), so
    the notes are looked for as runs of frames, never at fixed frames."""
    sgb.run(40)
    sgb.write("pour_streak", streak)
    sgb.write(sgb.addr("sfx_req") + 1, 0x40)
    rate = sgb.pb.sound.sample_rate
    return [detect(audio_frames(sgb, 1).astype(float).mean(axis=1), rate, 500, 3000) for _ in range(frames)]


def labels(trk, notes, tol=0.04):
    """Each frame's pitch as the index of the wanted note it is within tol of, -1 for a frame between two notes (or of a retrigger's click)."""
    return [next((k for k, w in enumerate(notes) if abs(hz / w - 1) < tol), -1) for hz in trk]


def assert_notes(trk, notes, tol=0.04):
    """Every wanted note is heard for at least 2 frames, and they come in order."""
    lab = labels(trk, notes, tol)
    firsts = []
    for k in range(len(notes)):
        assert lab.count(k) >= 2, (k, notes[k], lab, [round(h) for h in trk])
        firsts.append(lab.index(k))
    assert firsts == sorted(firsts), (lab, [round(h) for h in trk])
    return lab


PERFECT_NOTES = (D5, FS5, A5)
X2_NOTES = tuple(n * TONE ** 2 for n in (D5, FS5, A5, D6))


@pytest.mark.only_model('dmg')
def test_the_perfect_pour_is_a_soft_marimba_on_the_wave_channel(sgb):
    """SFX_PERFECT (15; owner's pick 2026-10-20): D5 F#5 A5 on channel 3 (the wave channel), each note plucked by the wave volume stepping 100% 50% 25% (NR32
    0x20 0x40 0x60), 20 frames, then the channel is let go (NR32 0). Nothing on channel 1: the tune's harmony is not played over by a sustained note."""
    sgb.write("intro_timer", 255)
    assert_notes(track(sgb, 1, 22), PERFECT_NOTES)
    sgb.run(40)
    request_perfect(sgb, 1)
    vol = []
    for _ in range(24):
        vol.append(sgb.mem(NR32) & 0x60)
        sgb.run(1)
    assert vol[0] == 0x20 and 0x40 in vol and 0x60 in vol, vol
    assert vol.index(0x40) < vol.index(0x60), "plucked"
    assert sgb.mem("hUGE_mute_mask") & MUTE3 == 0, "then let go"


VOICE_FREQ, VOICE_STEP = 5, 3          # voice_t: busy, def (2), step, left, freq (2), slide


def struck(sgb, streak, frames):
    """Request the marimba and return the wave-channel periods the driver strikes (what it writes to NR33/NR34: those registers are write-only, so the
    driver's own note state, voice[0], is read after every frame), one entry per note, in order. Exact, and independent of where in a frame the music
    ticks and so of the code layout."""
    sgb.run(40)
    sgb.write("pour_streak", streak)
    sgb.write(sgb.addr("sfx_req") + 1, 0x40)
    notes, last = [], None
    for _ in range(frames):
        sgb.run(1)
        v = sgb.read("voice", 7)
        if v[0] and v[VOICE_STEP] != last:
            last = v[VOICE_STEP]
            if v[VOICE_FREQ] | v[VOICE_FREQ + 1] << 8:
                notes.append(v[VOICE_FREQ] | v[VOICE_FREQ + 1] << 8)
    return notes


def wave_hz(period):
    """The pitch of the wave channel's 32-sample wave at an 11-bit period."""
    return 65536 / (2048 - period)


def assert_pitches(periods, wanted):
    """Each struck period is the wanted note to within the period's own step (the 11-bit period cannot hit a pitch exactly: 1.8% at D6, a semitone is 5.9%)."""
    assert len(periods) == len(wanted), (periods, wanted)
    for p, w in zip(periods, wanted):
        assert abs(wave_hz(p) / w - 1) < 0.012, (periods, [round(wave_hz(q)) for q in periods], wanted)


@pytest.mark.only_model('dmg')
def test_the_marimba_climbs_a_whole_tone_on_the_second_perfect_pour_and_the_x2_sound_is_the_same_every_time(sgb):
    """Streak 1: the base pitch; 2: one whole tone up; 3: the x2 sound (D5 F#5 A5 D6, then a soft repeat), two whole tones up, and identical on every
    later perfect pour (the streak stays at 3). The pitches are the periods the driver writes to NR33/NR34 (exact, so a semitone's slip fails and the code
    layout cannot); the speaker's FFT is only a coarse check that they are what is heard."""
    sgb.write("intro_timer", 255)
    assert_pitches(struck(sgb, 1, 22), PERFECT_NOTES)
    assert_pitches(struck(sgb, 2, 22), [n * TONE for n in PERFECT_NOTES])
    x2 = [struck(sgb, 3, 30) for _ in range(3)]
    assert_pitches(x2[0], X2_NOTES + X2_NOTES[-1:])         # (D5 F#5 A5 D6, then the soft repeat of D6)
    assert x2[1] == x2[2] == x2[0], x2                      # the same periods every time: no further climbing
    heard = track(sgb, 3, 30)                               # the speaker agrees, coarsely
    assert_notes(heard, X2_NOTES, tol=0.04)
    sgb.run(40)
    request_perfect(sgb, 3)
    n = 0
    while sgb.mem("hUGE_mute_mask") & MUTE3 and n < 40:
        sgb.run(1)
        n += 1
    assert 24 <= n <= 30, f"the x2 sound lasts {n + 1} frames, under half a second"


@pytest.mark.only_model('dmg')
def test_the_marimba_hands_channel_3_back_and_the_bass_reloads_its_wave(sgb):
    """The wave channel is the tunes' bass: while the marimba sounds the driver is told to leave it alone (mute mask bit 2) and, when it ends, the mask clears
    and the driver is made to reload its wave (hUGE_current_wave 100) at the next bass note, when the id is the bass's again."""
    sgb.write("intro_timer", 255)
    sgb.run(200)
    bass = sgb.mem("hUGE_current_wave")
    assert bass != NO_WAVE and sgb.mem("hUGE_mute_mask") & MUTE3 == 0
    request_perfect(sgb, 3)
    assert sgb.mem("hUGE_mute_mask") & MUTE3, "the driver leaves channel 3 alone while the marimba sounds"
    sgb.run(40)
    assert sgb.mem("hUGE_mute_mask") & MUTE3 == 0, "handed back"
    assert sgb.mem("hUGE_current_wave") == NO_WAVE, "the driver reloads the bass wave"
    sgb.run(300)
    assert sgb.mem("hUGE_current_wave") == bass, "with the next bass note"


@pytest.mark.only_model('dmg')
def test_a_channel_1_effect_cuts_the_marimba_and_the_marimba_cuts_one(sgb):
    """The marimba shares the channel-1 effect slot: a catch ping cutting it hands channel 3 back at once; the marimba starting over a ping lets channel 1
    go (NR12 0x08); and the extra life's fanfare is never cut by it."""
    sgb.write("intro_timer", 255)
    sgb.run(30)
    request_perfect(sgb, 1)
    sgb.run(3)
    assert sgb.mem("hUGE_mute_mask") & MUTE3
    sgb.write(sgb.addr("sfx_req"), 1 << (SFX_CATCH - 1))
    sgb.run(1)
    assert sgb.mem("hUGE_mute_mask") & MUTE3 == 0, "cut by the ping: channel 3 handed back"
    assert sgb.mem("hUGE_current_wave") == NO_WAVE
    sgb.run(40)
    sgb.write(sgb.addr("sfx_req"), 1 << (SFX_CATCH - 1))
    sgb.run(2)
    assert sgb.mem(NR12) != 0x08 and sgb.mem(NR12) != 0
    request_perfect(sgb, 1)
    assert sgb.mem(NR12) == 0x08, "the marimba cut the ping: channel 1 let go"
    assert sgb.mem("hUGE_mute_mask") & MUTE3 and sgb.mem(NR32) & 0x60 == 0x20
    sgb.run(40)
    sgb.write(sgb.addr("sfx_req") + 1, 1 << (SFX_EXTRA_ID - 1 - 8))
    sgb.run(2)
    nr12 = sgb.mem(NR12)
    request_perfect(sgb, 1)
    assert sgb.mem(NR12) == nr12 and nr12 != 0x08 and sgb.mem("hUGE_mute_mask") & MUTE3 == 0, "the extra life is not cut short, no marimba over it"


@pytest.mark.only_model('dmg')
def test_a_marimba_sounding_when_the_game_pauses_plays_out_on_the_pause_mix(sgb):
    """Paused, NR51 is 0xCC (bass and drums: channels 3 and 4): the marimba, on channel 3, stays audible, runs out and hands the channel back as usual
    (the pause keeps ticking the effects), and RESUME gives the full mix."""
    from test_pause import PAUSED, tap
    sgb.write("intro_timer", 255)
    sgb.run(30)
    request_perfect(sgb, 3)
    sgb.run(3)
    tap(sgb, "start", 3)
    assert state(sgb) == PAUSED and sgb.mem(0xFF25) == 0xCC
    sgb.run(60)
    assert sgb.mem(0xFF25) == 0xCC and sgb.mem("hUGE_mute_mask") & MUTE3 == 0, "ran out"
    tap(sgb, "start", 3)
    assert state(sgb) == PLAYING and sgb.mem(0xFF25) == 0xFF


@pytest.mark.only_model('dmg')
def test_music_yields_channel_4_to_an_effect_then_takes_it_back(sgb):
    sgb.write("intro_timer", 255)
    sgb.run(30)                                         # the in-game tune has a noise percussion line
    assert sgb.mem("cur_tune") == TUNE_GAME
    mask = 0
    for _ in range(40):
        sgb.run(1)
        mask |= sgb.mem(NR52) & 8
    assert mask, "the game tune plays percussion on channel 4"
    inject_mug(sgb, 1, 17)
    run_until(sgb, lambda: sfx_count(sgb, SFX_BREAK) == 1, 10)
    assert sgb.mem("hUGE_mute_mask") & 8, "driver told to leave channel 4 alone while the effect plays"
    sgb.run(60)
    assert not sgb.mem("hUGE_mute_mask") & 8, "and gets it back afterwards"


# ---- which tune plays when ---------------------------------------------------------------
@pytest.mark.only_model('dmg')
def test_tunes_follow_the_game_state(srom):
    assert srom.mem("cur_tune") == TUNE_TITLE
    start_game(srom)
    assert srom.mem("cur_tune") == TUNE_VENUE0, "level 1 is the saloon: Oh! Susanna"
    row = srom.mem16("music_frames")
    srom.run(5)
    assert abs(srom.mem16("music_frames") - (row + 5)) <= 1, "a looping tune keeps going"
    clear_level(srom)
    assert srom.mem("cur_tune") == TUNE_CLEAR
    run_until(srom, lambda: state(srom) == PLAYING, 400)
    assert srom.mem("cur_tune") == TUNE_VENUE0 + 1, "level 2 is the sports bar: its own tune"


def test_the_title_tune_plays_on_smoothly_across_the_attract_tables(srom):
    """Owner: the title tune hitched when the idle title switched to a top-5 table and back.  The switches are LCD-off
    loads of several frames inside one main-loop pass, and the music ticks once a pass: the top-5 table took ~9
    frames (six_digits' 32-bit divisions), the title ~12 (tiles, venue, backdrop).  Now split6 has no division and
    the loads call music_pump between their steps (the timer, polled): over title -> table -> title the tune never
    restarts, never stands still for more than 2 frames, and loses at most a few frames in all."""
    assert srom.mem("cur_tune") == TUNE_TITLE
    a = srom.addr("title_idle")
    for cycle in range(2):                                  # ARCADE's table, then STORY's
        srom.write(a, 1195 & 255)
        srom.write(a + 1, 1195 >> 8)
        mf, states = [], []
        for _ in range(330):
            srom.run(1)
            mf.append(srom.mem16("music_frames"))
            states.append(state(srom))
            assert srom.mem("cur_tune") == TUNE_TITLE
        assert GS_SCORES in states and states[-1] == TITLE, "the table showed and the title came back"
        steps = [b - a_ for a_, b in zip(mf, mf[1:])]
        assert min(steps) >= 0, "the tune restarted"
        still = longest = 0
        for d in steps:
            still = still + 1 if d == 0 else 0
            longest = max(longest, still)
        assert longest <= 2, f"the tune stood still for {longest} frames"
        assert mf[-1] - mf[0] >= len(mf) - 1 - 6, f"{len(mf) - 1} frames, the tune moved {mf[-1] - mf[0]}"


@pytest.mark.only_model('dmg')
def test_jingle_stops_by_itself(srom):
    start_game(srom)
    srom.write("level", 1)
    clear_level(srom)
    assert srom.mem("cur_tune") == TUNE_CLEAR
    run_until(srom, lambda: srom.mem("cur_tune") != TUNE_CLEAR, 200)
    assert srom.mem("cur_tune") == TUNE_NONE and state(srom) == LEVEL_CLEAR, "the jingle ends before the next screen"
    assert silent(audio_frames(srom, 10))


@pytest.mark.only_model('dmg')
def test_game_over_and_bonus_tunes(srom):
    start_game(srom)
    for n in range(3):
        lose_a_life(srom)
        if n < 2:
            run_until(srom, lambda: state(srom) == PLAYING, 200)
    run_until(srom, lambda: state(srom) == GAME_OVER, 200)
    assert srom.mem("cur_tune") == TUNE_OVER
    srom.press("start", 2)                      # M10b: a score of 0 makes no entry: the top-5 table, then the title
    run_until(srom, lambda: state(srom) == GS_SCORES, 30)
    srom.run(2)
    srom.press("start", 2)
    run_until(srom, lambda: state(srom) == TITLE, 30)
    assert srom.mem("cur_tune") == TUNE_TITLE


@pytest.mark.only_model('dmg')
def test_bonus_round_has_its_own_tune(srom):
    start_game(srom)
    enter_bonus(srom)
    assert srom.mem("cur_tune") == TUNE_BONUS


# ---- the right song plays: its melody is heard on channel 2 ------------------------------------------
def melody_check(rom, source, frames=260, min_notes=6):
    """Run `frames` frames with only channel 2 routed to the speakers and compare the pitch heard inside each melody note
    of song `source` (tools/songs.py) with the pitch the song says.  Returns (checked, wrong) lists of (row, Hz wanted, Hz heard)."""
    t = songs.SONGS[source]
    tempo = t["tempo"]
    swing = t.get("swing", 0)
    rows = gm.rows_for(2, t["ch2"], 1, tempo, False, t.get("gap", True), t.get("stac_all"), t.get("legato"), swing)
    at = gm.row_starts(tempo, swing, 2 * len(rows))         # the frame at which each row starts (a swung row is a frame short)
    notes = []
    for i, (n, _, _) in enumerate(rows):
        if n != gm.REST:
            j = i + 1
            while j < len(rows) and rows[j][0] == gm.REST:
                j += 1
            notes.append((i, j - i, n))
    chunks, mfs = [], []
    for _ in range(frames):
        rom.pb.memory[NR51] = 0x22
        rom.run(1)
        rom.pb.memory[NR51] = 0x22
        chunks.append(rom.pb.sound.ndarray.copy())
        mfs.append(rom.mem16("music_frames"))
        if len(mfs) > 1 and mfs[-1] < mfs[-2]:        # the song looped (or another tune started): stop there
            chunks.pop(); mfs.pop()
            break
    rom.pb.memory[NR51] = 0xFF
    flat = np.concatenate(chunks).astype(float).mean(axis=1)
    spf = len(flat) / len(chunks)
    rate = rom.pb.sound.sample_rate
    checked, wrong = [], []
    for row, ln, n in notes:
        r0 = (row - t.get("start", 0)) % len(rows)                     # (a tune with a start row begins there)
        k = at[r0] + 1
        if mfs[0] >= k or mfs[-1] < k + (at[r0 + ln] - at[r0]) + 2:
            continue                                    # not entirely inside what was recorded
        f0 = next(f for f in range(len(mfs)) if mfs[f] >= k) + 1
        # (a long note's volume envelope has faded to near silence well before its last rows: listen to its first 3 rows
        # at most, or the pitch found is the noise floor's, which moves with the music tick's line in the frame)
        hear = at[r0 + min(ln, 3)] - at[r0]
        a, b = int((f0 + 0.2 * hear) * spf), int((f0 + 0.8 * hear) * spf)
        want = note_hz(n)
        got = detect(flat[a:b], rate, want * 0.6, want * 1.7)
        checked.append((row, want, got))
        if not got or abs(12 * np.log2(got / want)) > 0.6:
            wrong.append((row, want, got))
    assert len(checked) >= min_notes, f"only {len(checked)} notes of {source} were inside the recording"
    return checked, wrong


@pytest.mark.only_model('dmg')
def test_the_title_plays_the_entertainer(srom):
    assert srom.mem("cur_tune") == TUNE_TITLE
    checked, wrong = melody_check(srom, "entertainer", 280)
    assert not wrong, f"title melody differs from The Entertainer's note list: {wrong}"


def row_lengths(rom, frames):
    """Frames each driver row lasted, from hUGE_row, over `frames` frames of whatever tune is playing (whole rows only)."""
    rows = []
    for _ in range(frames):
        rom.run(1)
        rows.append(rom.mem("hUGE_row"))
    marks = [i for i in range(1, len(rows)) if rows[i] != rows[i - 1]]
    return [b - a for a, b in zip(marks, marks[1:])], [rows[m] for m in marks]


@pytest.mark.only_model('dmg')
def test_the_swung_title_plays_rows_of_alternating_length(srom):
    """The Entertainer is swung (songs 'swing' 0xAA, src/music.c tick): rows of 9, 8, 9, 8 ... frames, the mask's bit
    (row mod 8) = a frame short; a tune without a swing (the venue tunes) keeps its tempo on every row."""
    assert srom.mem("cur_tune") == TUNE_TITLE
    s = songs.SONGS["entertainer"]
    assert s["swing"] == 0xAA and s["tempo"] == 9
    srom.run(60)
    lens, rows = row_lengths(srom, 200)
    assert len(lens) >= 16
    want = [s["tempo"] - ((s["swing"] >> (r % 8)) & 1) for r in rows[:-1]]
    assert lens == want, (lens, rows)
    assert set(lens) == {8, 9} and abs(sum(lens) / len(lens) - 8.5) < 0.1
    # the drums header carries the mask and the pass length counts the short rows
    src = (ROOT / "build" / "music_data.c").read_text()
    assert "groove_title[] = {32, 170," in src, "the 4-bar groove (music batch 1)"
    assert re.search(r"\{&song_title, 1, 10336, 3, 23, ", src), "1216 rows: 608 of 9 frames and 608 of 8, streamed from bank 23"
    assert gm.row_starts(9, 0xAA, 1216)[-1] == 10336
    assert gm.row_starts(8, 0, 256)[-1] == 2048, "no swing: tempo x rows"


SUSANNA_SPEC = """E4:1 G4:1 G4:1 A4:1 G4:1 E4:1 C4:1 D4:1 E4:1 E4:1 D4:1 C4:1 D4:2 C4:1 D4:1
E4:1 G4:1 G4:1 A4:1 G4:1 E4:1 C4:1 D4:1 E4:1 E4:1 D4:1 D4:1 C4:2 C4:1 D4:1
E4:1 G4:1 G4:1 A4:1 G4:1 E4:1 C4:1 D4:1 E4:1 E4:1 D4:1 C4:1 D4:2 C4:1 D4:1
E4:1 G4:1 G4:1 A4:1 G4:1 E4:1 C4:1 D4:1 E4:1 E4:1 D4:1 D4:1 C4:4
F4:2 F4:2 A4:2 A4:2 G4:1 G4:1 E4:1 C4:1 D4:2 C4:1 D4:1
E4:1 G4:1 G4:1 A4:1 G4:1 E4:1 C4:1 D4:1 E4:1 E4:1 D4:1 D4:1 C4:2 C4:1 D4:1"""


# Foster's rhythm (music step 3): the score (humdrum-tools/foster-songs fostr20.krn, in G there) bar by bar in C, one
# row a sixteenth.  Bar 16 is the score's quarter and quarter rest; bar 24 (the score's too) is bar 8's turnaround so
# the loop's pickup leads into bar 1.
SUSANNA_FOSTER = [
    "E4:2 G4:2 G4:2 A4:2", "G4:2 E4:2 C4:3 D4:1", "E4:2 E4:2 D4:2 C4:2", "D4:6 C4:1 D4:1",
    "E4:2 G4:2 G4:3 A4:1", "G4:2 E4:2 C4:3 D4:1", "E4:2 E4:2 D4:2 D4:2", "C4:6 C4:1 D4:1",
    "E4:2 G4:2 G4:2 A4:2", "G4:2 E4:2 C4:3 D4:1", "E4:2 E4:2 D4:2 C4:2", "D4:6 C4:1 D4:1",
    "E4:2 G4:2 G4:3 A4:1", "G4:2 E4:2 C4:3 D4:1", "E4:2 E4:2 D4:2 D4:2", "C4:4 r:4",
    "F4:4 F4:4", "A4:2 A4:4 A4:2", "G4:2 G4:2 E4:2 C4:2", "D4:6 C4:1 D4:1",
    "E4:2 G4:2 G4:2 A4:2", "G4:2 E4:2 C4:3 D4:1", "E4:2 E4:2 D4:2 D4:2", "C4:6 C4:1 D4:1",
]


def test_oh_susanna_is_the_owners_notes_in_fosters_rhythm():
    """The owner's notes (every pitch as listed, plus the score's third A of "san-na, oh"; it starts on bar 1 and the last bar is the C4 C4 D4 turnaround of the
    second verse line, tests/test_music_loops.py) in the rhythm of Foster's score at sixteenth rows: the sixteenth
    pickups, the dotted "with my ban-jo", the chorus "Oh! Su-san-na, oh" as quarter quarter | eighth quarter eighth
    (the owner: "zan-uh grouped closer together"), and the quarter rest before the chorus."""
    s = songs.SONGS["susanna"]
    assert s["ch2"].split() == " ".join(SUSANNA_FOSTER).split()
    pitches = lambda text: [t.split(":")[0] for t in text.split() if not t.startswith("r:")]
    owner = pitches(SUSANNA_SPEC)
    k = len(pitches(" ".join(SUSANNA_FOSTER[:17]))) + 2       # bar 18's third A: "san-na, OH don't you cry"
    assert pitches(s["ch2"]) == owner[:k] + ["A4"] + owner[k:], "the owner's pitches, plus the score's 'oh'"
    assert songs.BAR_ROWS["susanna"] == 8 and all(
        sum(int(t.split(":")[1]) for t in bar.split()) == 8 for bar in SUSANNA_FOSTER), "2/4 in sixteenth rows"
    assert SUSANNA_FOSTER[17] == "A4:2 A4:4 A4:2" and SUSANNA_FOSTER[16] == "F4:4 F4:4"
    assert s["tempo"] == 8, "8 frames per sixteenth row = quarter 112.5 (the score's MM 114; the eighth rows were 120)"
    bass = s["ch3"].replace("!", "").split()
    assert bass[:3] == ["C3:4", "G2:4", "C3:4"] and bass[-3:] == ["C3:4", "G2:2", "B2:2"], "boom-chick, the last bar walks B into bar 1 (batch 1)"
    assert sum(int(t.split(":")[1]) for t in bass) == 192
    assert s["ch4"].split()[-6:] == ["b:2", "t:2", "n:1", "n:1", "m:1", "m:1"], "the snare and tom roll leads the last bar into bar 1"
    b = gm.build("venue0", s, False)
    assert b["total"] == 192 and b["n_orders"] == 3


def test_the_entertainer_plays_its_b_section_before_it_loops():
    """Owner: "I kind of wish the next section of The Entertainer was there before it looped back".  ENT_BARS: 32 bars: the A
    section with its second ending (E F F# up into the B section's G), then the B section, whose second ending's D D#
    pickup leads back to bar 1.  The title is now the whole piece (tests/test_music_batch1.py): 1216 rows in 20 streamed orders, bank 23."""
    s = songs.SONGS["entertainer"]
    assert len(songs.ENT_BARS) == 32 == len(songs.ENT_CHORDS)
    # (the melody is written an octave below the spec: the owner's "1b", 2026-10-12)
    assert songs.ENT_BARS[15].endswith("E4:1 F4:1 F#4:1") and songs.ENT_BARS[16].startswith("G4:2 A4:1 G4:2")
    assert songs.ENT_BARS[31].endswith("D4:1 D#4:1") and songs.ENT_BARS[0].startswith("E4:1")
    b = gm.build("title", s, False)
    assert b["total"] == 152 * 8 and b["n_orders"] == 20
    assert gm.BLOB_BANKS == (10,) and gm.STREAMED["title"] == 23
    pat = (ROOT / "build" / "music_pat23.c").read_text()
    assert "#pragma bank 23" in pat and "blob_title[]" in pat and "harm_title[]" in pat
    data = (ROOT / "build" / "music_data.c").read_text()
    assert "unsigned char mus_buf_a[1536];" in data, "buffer A holds 8 patterns: four orders of the streamed title"


# ---- sung tunes are legato (owner: "every syllable is being enunciated robotically") -------------------------------
def melody_cuts(s):
    """[(pitch, rows, next pitch or None for a rest, frame of its note cut within the note or None)] of a song's melody."""
    tempo, swing = s["tempo"], s.get("swing", 0)
    rows = gm.rows_for(2, s["ch2"], s["inst"], tempo, False, s["gap"], s["stac_all"], s["legato"], swing)
    at = gm.row_starts(tempo, swing, len(rows) + 1)
    toks = gm.merge_ties(s["ch2"]).split()
    out, row = [], 0
    for k, tok in enumerate(toks):
        name, n = tok.rstrip("!").split("/")[0].split(":")
        n = int(n)
        if name != "r":
            nxt = toks[k + 1].split(":")[0] if k + 1 < len(toks) else toks[0].split(":")[0]
            cut = next((at[rr] - at[row] + (rows[rr][2] & 0xFF) for rr in range(row, row + n)
                        if (rows[rr][2] & 0xF00) == 0xE00), None)
            out.append((name, n, None if nxt == "r" else nxt, cut))
        row += n
    return out


def test_sung_tunes_hold_their_notes_and_only_articulate_a_repeated_syllable():
    """Oh! Susanna and She'll Be Coming 'Round the Mountain: the song lead's decay (NR12 0x85, half volume after 0.39 s)
    made every note a plucked syllable, loudest where a pitch repeats ("Su-san-na", "She'll be com-ing").  They now play
    on the legato lead (a held volume, no envelope) and each note runs into the next; a repeated pitch is cut
    songs.SUNG_ARTIC frames early so the new syllable is heard, a note before a rest one frame early (rests stay)."""
    lead = gm.DUTY[songs.LEGATO_LEAD - 1]
    assert lead[2] & 7 == 0 and 5 <= lead[2] >> 4 <= 8, "a held volume, no louder than the song lead"
    assert lead[1] == gm.DUTY[gm.LEAD_PRO - 1][1] and lead[3] == "sp_lead", "the brass lead's 50% pulse and its attack and vibrato table, held"
    for name in ("susanna", "mountain"):
        s = songs.SONGS[name]
        assert s["legato"] == songs.SUNG_ARTIC and s["inst"] == songs.LEGATO_LEAD and not s["stac_all"]
        kinds = set()
        for pitch, n, nxt, cut in melody_cuts(s):
            ticks = n * s["tempo"]                  # (the sung tunes are not swung)
            if nxt == pitch:
                assert cut == ticks - songs.SUNG_ARTIC, (name, pitch, n, cut)
                kinds.add("repeat")
            elif nxt is None:
                assert cut == ticks - 1, (name, pitch, n, cut)
            else:
                assert cut is None, f"{name}: {pitch} -> {nxt} must run into the next note (cut at {cut})"
                kinds.add("legato")
        assert kinds == {"repeat", "legato"}
    # every other tune keeps its own articulation
    assert [n for n, s in songs.SONGS.items() if s["legato"]] == ["susanna", "mountain"]


# ---- the tunes entered from docs/music_specs.md ------------------------------------------------------
SPEC_TUNES = {1: "funicula", 2: "skaters", 3: "ballgame", 4: "mountain", 5: "weasel", 6: "danube", 7: "hall",
              8: "sakura", 9: "entertainer", 10: "galop", 11: "sailor"}


def parse_specs():
    """docs/music_specs.md -> {song name: (bar token strings, chord per bar)}."""
    import re
    text = (ROOT / "docs" / "music_specs.md").read_text()
    parts = re.split(r"\n-{60}\n(\d+)\. ", text)
    out = {}
    for i in range(1, len(parts), 2):
        bars, chords = [], []
        for line in parts[i + 1].split("\n"):
            m = re.match(r"\s*(\d+) \| (.*?)\s*\| (\S+)\s*$", line)
            if m:
                assert int(m.group(1)) == len(bars) + 1
                bars.append(m.group(2).strip())
                chords.append(m.group(3))
        out[SPEC_TUNES[int(parts[i])]] = (bars, chords)
    return out


def spec_bars_for_the_game(name, bars):
    """The spec bars with the documented adaptation: Pop Goes the Weasel's last rest is the D4 pickup.  (Pickup lines
    are not bars: they are the first-time-only lead-ins, left out so that the loop is seamless.)"""
    bars = list(bars)
    if name == "entertainer":          # the owner's "1b": the melody an octave lower than the spec (songs.ENT_BARS)
        bars = [re.sub(r"([A-G]#?)(\d)", lambda m: m.group(1) + str(int(m.group(2)) - 1), b) for b in bars]
    if name == "weasel":
        assert bars[-1].endswith("R:1")
        bars[-1] = bars[-1][:-3] + "D4:1"
    return bars


# the spec's tempo (the game plays songs.GAME_BPM where that lists the tune): beats per minute and song rows per beat
SPEC_BPM_ROWS = {"funicula": (92, 3), "skaters": (160, 2), "ballgame": (168, 2), "mountain": (160, 4), "weasel": (100, 3),
                 "danube": (160, 2), "hall": (120, 2), "sakura": (100, 2), "entertainer": (90, 4), "galop": (160, 2),
                 "sailor": (200, 2)}


def test_the_tunes_are_the_specs_token_for_token():
    specs = parse_specs()
    assert sorted(specs) == sorted(SPEC_TUNES.values())
    for name, (bars, chords) in specs.items():
        s = songs.SONGS[name]
        want = " ".join(spec_bars_for_the_game(name, bars)).split()
        if name == "entertainer":      # the title is the whole piece now: its A and B strains are ENT_BARS (the spec's 32 bars)
            assert [t.rstrip("!").split("/")[0] for t in " ".join(songs.ENT_BARS).split()] == want and songs.ENT_CHORDS == chords
            s = dict(s, ch2=" ".join(songs.ENT_BARS), ch3=songs.oompah(songs.ENT_CHORDS, 8))
        assert [t.rstrip("!").split("/")[0] for t in s["ch2"].split()] == want, f"{name}: melody differs from docs/music_specs.md"
        per_bar = songs.BAR_ROWS[name]
        for ch in ("ch2", "ch3"):                       # every bar adds up (ties included), melody and bass
            rows = gm.merge_ties(s[ch]).split()
            assert sum(int(t.split(":")[1].rstrip("!").split("/")[0]) for t in rows) == per_bar * len(bars), f"{name} {ch} length"
        bpm, rows_per_beat = SPEC_BPM_ROWS[name]
        bpm = songs.GAME_BPM.get(name, bpm)             # the owner-approved game tempo (the spec's where none is listed)
        ideal = 3600 / bpm / rows_per_beat
        avg = s["tempo"] - bin(s.get("swing", 0)).count("1") / 8      # a swung tune's average row (the mask is per 8 rows)
        assert abs(avg - ideal) / ideal < 0.05, f"{name} tempo {avg} vs {ideal:.1f} frames per row (game tempo {bpm} bpm)"
        if name in ("hall", "sakura"):
            continue                                    # root ostinato / Sakura's own bass figure (its test below)
        bass = s["ch3"].replace("!", "").split()
        i = 0
        for chord in chords:                            # the bass plays the bar's chord: its root on the downbeat
            assert bass[i].split(":")[0] == songs.CHORD[chord.split("/")[0]][0], f"{name}: chord {chord} vs bass {bass[i]}"
            n = 0
            while n < per_bar:
                n += int(bass[i].split(":")[1].split("/")[0])
                i += 1
            assert n == per_bar


def test_hall_of_the_mountain_king_is_staccato_over_a_root_ostinato():
    s = songs.SONGS["hall"]
    assert s["stac_all"] == (1, 2)
    # music batch 3: the bass is the theme itself an octave (two in the F# answer, bars 9-12) below the melody, note for note
    assert songs.HALL_BASS_ONSETS and H.nrows(s["ch3"]) == H.nrows(s["ch2"]) == 128
    assert all(t.endswith("!") for t in s["ch3"].split())
    rows = gm.rows_for(2, s["ch2"], 1, s["tempo"], False, True, s["stac_all"])
    cuts = [eff for _, _, eff in rows if (eff & 0xF00) == 0xE00]
    assert len(cuts) > 80 and set(c & 0xFF for c in cuts) >= {7}, "a 1-row note is cut after 7 of its 15 ticks"


def test_sakura_is_lively_a_bouncing_bass_on_the_chords_under_a_detached_melody():
    """The owner kept Sakura and asked for a livelier arrangement: 150 bpm (approved), every melody note detached, a
    syncopated bass on each bar's chord (not a drone), a taiko-like two-bar groove of kicks, rim (hat) and snare."""
    s = songs.SONGS["sakura"]
    assert s["tempo"] == 12 and s["stac_all"] == (3, 4)
    bass = s["ch3"].split()
    assert len({t.split(":")[0] for t in bass}) >= 6, "a moving bass, not two drone notes"
    i = 0
    for bar, chord in enumerate(songs.SAK_CHORDS):      # (batch 3: the bar's riff ends in the scale's own falls into the next chord)
        assert bass[i].split(":")[0] == songs.SAK_BASS_NOTES[chord][0], f"bar {bar + 1}: the root on the downbeat"
        n = 0
        while n < 8:
            n += int(bass[i].split(":")[1].rstrip("!"))
            i += 1
        assert n == 8
    assert i == len(bass)
    g = gm.groove_rows("sakura", s)
    assert len(g) == 16 and g.count(gm.DRUM_ID["b"]) >= 5 and gm.DRUM_ID["n"] in g and gm.DRUM_ID["x"] in g and gm.DRUM_ID["m"] in g   # (batch 3: don = kick, ka = rim, the tom tom snare snare close)


def test_ties_fold_into_the_previous_note():
    assert gm.merge_ties("C5:2 ~:3 D5:1 ~:1") == "C5:5 D5:2"
    assert gm.merge_ties("R:2 C5:1! ~:2") == "r:2 C5:3!"


@pytest.mark.only_model('dmg')
def test_level_1_plays_oh_susanna(sgb):
    assert sgb.mem("cur_tune") == TUNE_VENUE0 and sgb.mem("cur_group") == 0
    sgb.write("intro_timer", 255)
    checked, wrong = melody_check(sgb, "susanna", 240)
    assert not wrong, f"gameplay melody differs from Oh! Susanna: {wrong}"


def goto_level(rom, level):
    """The level-clear state about to move on to `level` (which must be even, so no bonus round comes between)."""
    assert level % 2 == 0
    rom.write("level", level - 1)
    rom.write("game_state", GS_LEVEL_CLEAR)
    rom.write("state_timer", 149)
    rom.run(1)
    run_until(rom, lambda: state(rom) == PLAYING, 30)


@pytest.mark.only_model('dmg')
@pytest.mark.parametrize("group", range(10))
def test_every_venue_plays_its_own_song(sgb, group):
    """Level L shows patron group (L-1) % 10: each group has its own tune (songs.VENUES[group]), played from its first
    note."""
    if group:                                           # (level 1 is where the fixture already is)
        goto_group(sgb, group)
    sgb.write("intro_timer", 255)
    assert sgb.mem("cur_group") == group and sgb.mem("cur_tune") == TUNE_VENUE0 + group
    source = songs.VENUES[group]
    sgb.run(30)
    checked, wrong = melody_check(sgb, source, 330, min_notes=3)
    assert not wrong, f"{source}: {wrong}"


def w16(rom, name, v):
    rom.write(name, v & 255)
    rom.write(rom.addr(name) + 1, v >> 8)


def start_a_show(rom):
    rom.write("intro_timer", 255)
    rom.write("tip_chance", 0)
    rom.write("tip_bar", rom.mem("bar"))
    rom.write("tip_x", rom.mem("bartender_x"))
    rom.write("tip_timer", 100)
    rom.run(2)


@pytest.mark.only_model('dmg')
def test_a_show_plays_the_galop_and_the_level_tune_resumes_from_its_start(sgb):
    sgb.run(400)                                        # long enough for the show tune to have been copied in the background
    assert sgb.mem("cur_tune") == TUNE_VENUE0
    start_a_show(sgb)
    assert sgb.mem16("show_timer") > 0 and sgb.mem("cur_tune") == TUNE_SHOW
    w16(sgb, "show_timer", 2000)                       # keep the show going while the melody is checked
    checked, wrong = melody_check(sgb, "galop", 200)
    assert not wrong, f"show melody differs from the Galop infernal: {wrong}"
    w16(sgb, "show_timer", 3)
    run_until(sgb, lambda: sgb.mem("cur_tune") != TUNE_SHOW, 10)
    sgb.run(1)                                          # (PyBoy's frame edge can fall inside the music_play call)
    assert sgb.mem16("show_timer") == 0 and sgb.mem("cur_tune") == TUNE_VENUE0, "the show is over: the level's tune again"
    assert sgb.mem16("music_frames") < 5, "...from its start"
    checked, wrong = melody_check(sgb, "susanna", 150, min_notes=3)
    assert not wrong, wrong


@pytest.mark.only_model('dmg')
def test_a_show_that_ends_with_a_lost_life_gives_the_level_tune_back(sgb):
    sgb.run(400)
    start_a_show(sgb)
    assert sgb.mem("cur_tune") == TUNE_SHOW
    lose_a_life(sgb)
    run_until(sgb, lambda: state(sgb) == PLAYING, 200)
    assert sgb.mem("cur_tune") == TUNE_VENUE0 and sgb.mem16("show_timer") == 0
    sgb.run(30)
    assert sgb.mem16("music_frames") > 0 and sgb.mem(NR52) & 0x06, "and it is audible"


def test_the_show_tune_waits_for_nothing_when_a_show_starts(sgb):
    """The show tune is copied to WRAM while the level plays, so a show starts it at once (no silent gap)."""
    sgb.run(400)
    start_a_show(sgb)
    sgb.run(3)
    assert sgb.mem("cur_tune") == TUNE_SHOW and sgb.mem16("music_frames") >= 2


# ---- MUSIC ON / OFF -------------------------------------------------------------------------
def music_text(gb):
    return music_line(gb)          # the title's MUSIC line (SETTINGS' first line, row 8)


@pytest.mark.only_model('dmg')
def test_select_toggles_the_music(srom):
    srom.run(200)                  # (past the DX badge's stamp sound on a Color, SFX that the music switch does not silence)
    title_pick(srom, K_SETTINGS)   # (SELECT works on any menu level; SETTINGS shows the line)
    srom.run(MENU_SETTLE)
    assert srom.mem("sound_on") == 1 and music_text(srom) == title_text_row("on")
    srom.press("select", 2)
    srom.run(2)
    assert srom.mem("sound_on") == 0 and music_text(srom) == title_text_row("off")
    f = srom.mem16("music_frames")
    srom.run(30)
    assert srom.mem16("music_frames") == f, "the driver is not ticking while the music is off"
    assert silent(audio_frames(srom, 10)), "silent (the driver cuts the notes)"
    srom.press("select", 2)
    srom.run(2)
    assert srom.mem("sound_on") == 1 and music_text(srom) == title_text_row("on")
    srom.run(30)
    assert srom.mem(NR52) & 0x06, "the title tune is back"


@pytest.mark.only_model('dmg')
def test_music_off_persists_into_the_game_but_effects_still_play(srom):
    srom.press("select", 2)
    start_game(srom)
    srom.write("intro_timer", 255)
    srom.hold("a")
    srom.run(3)
    assert srom.mem("sound_on") == 0 and srom.mem("last_sfx") == SFX_FILL
    assert srom.mem(NR52) & 1, "effects are not part of the music switch"
    assert not srom.mem(NR52) & 0x0A and srom.mem("cur_tune") == TUNE_GAME, "the music channels are cut"


@pytest.mark.only_model('dmg')
def test_select_does_nothing_outside_the_title(gb):
    gb.press("select", 2)
    gb.run(2)
    assert gb.mem("sound_on") == 1


# ---- saved hi score (M10b: the top-5 table; SRAM version 7 since the three modes: the ARCADE table's block at 0x80,
# "HSA1", 5 x (3 initials, 3-byte score), checksum at +34; the LEVEL harness's game overs go into it) ----
TBL = 0x80
SAVE_SUM = TBL + 34
def earn_fifty_and_lose(rom):
    start_game(rom)
    rom.write("intro_timer", 255)
    inject_mug(rom, 0, GAME["ENTRY_X"] + 8)
    rom.run(45)                                   # (served when he is off the screen)
    assert score(rom) == 50
    for n in range(3):
        lose_a_life(rom)
        if n < 2:
            run_until(rom, lambda: state(rom) == PLAYING, 200)
    run_until(rom, lambda: state(rom) == GAME_OVER, 200)
    assert hi_score(rom) == 50


@pytest.mark.only_model('dmg')
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_hi_score_survives_a_reset(model):
    rom = make_rom(model, sound=False)
    rom.run(120)
    assert hi_score(rom) == 0, "a fresh cartridge starts at 0"
    earn_fifty_and_lose(rom)
    ram = save_ram(rom)
    assert ram[:4] == b"TPR7" and ram[TBL:TBL + 4] == b"HSA1"
    assert ram[TBL + 4:TBL + 7] == b"AAA" and int.from_bytes(ram[TBL + 7:TBL + 10], "little") == 50
    with make_rom(model, ram, sound=False) as again:     # power cycle with the same battery RAM
        again.run(120)
        assert hi_score(again) == 50
        assert hi_shown(again) == hi_tiles("000050"), "the title shows the saved HI"
        assert [d for d in again.read("hi_digits", 6)] == [0, 0, 0, 0, 5, 0]


@pytest.mark.only_model('dmg')
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_lower_score_does_not_overwrite_the_saved_hi(model):
    rom = make_rom(model, sound=False)
    rom.run(120)
    earn_fifty_and_lose(rom)
    ram = save_ram(rom)
    with make_rom(model, ram, sound=False) as again:
        again.run(120)
        start_game(again)
        for n in range(3):
            lose_a_life(again)
            if n < 2:
                run_until(again, lambda: state(again) == PLAYING, 200)
        run_until(again, lambda: state(again) == GAME_OVER, 200)
        assert hi_score(again) == 50
        assert save_ram(again)[:SAVE_SUM + 2] == ram[:SAVE_SUM + 2], "SRAM unchanged when the score makes no entry"


def corrupt(ram, edit):
    ram = bytearray(ram)
    edit(ram)
    return bytes(ram)


@pytest.mark.only_model('dmg')
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_invalid_save_data_loads_as_zero(model):
    rom = make_rom(model, sound=False)
    rom.run(120)
    earn_fifty_and_lose(rom)
    good = save_ram(rom)
    cases = {
        "bad signature": corrupt(good, lambda r: r.__setitem__(TBL, ord("X"))),
        "flipped score bit": corrupt(good, lambda r: r.__setitem__(TBL + 7, r[TBL + 7] ^ 0x01)),
        "bad checksum": corrupt(good, lambda r: r.__setitem__(SAVE_SUM, (r[SAVE_SUM] + 1) & 255)),
        "bad complement": corrupt(good, lambda r: r.__setitem__(SAVE_SUM + 1, r[SAVE_SUM + 1] ^ 0xFF)),
        "blank": bytes(len(good)),
        "garbage": bytes((i * 37 + 11) & 255 for i in range(len(good))),
    }

    def with_checksum(r):                       # a well-formed record whose score is absurd (>= 1,000,000)
        r[TBL + 7:TBL + 10] = (2_000_000).to_bytes(3, "little")
        c = (0x5A + sum(r[TBL:SAVE_SUM])) & 255
        r[SAVE_SUM], r[SAVE_SUM + 1] = c, c ^ 0xFF
    cases["out of range"] = corrupt(good, with_checksum)
    for name, ram in cases.items():
        with make_rom(model, ram, sound=False) as again:
            again.run(120)
            assert hi_score(again) == 0, name
            assert hi_shown(again) == hi_tiles("000000"), name


# ---- frame discipline --------------------------------------------------------------------------
def test_no_frame_is_skipped_with_music_and_effects_running(sgb):
    """600 frames of busy play: frame_counter advances by exactly 1 every frame, and the drain stays short."""
    sgb.write("intro_timer", 0)
    sgb.write("tip_chance", 255)
    last = sgb.mem("frame_counter")
    script = ["a"] * 30 + [None] * 6 + ["down"] + ["left"] * 12 + ["right"] * 12 + ["a"] * 26 + [None] * 4 + ["up"]
    held = None
    for i in range(600):
        want = script[i % len(script)]
        if want != held:
            if held: sgb.release(held)
            if want: sgb.hold(want)
            held = want
        sgb.run(1)
        sgb.write("lives", 3)                   # keep the run going: no game over, no level change
        sgb.write("quota", 250)
        now = sgb.mem("frame_counter")
        assert (now - last) & 255 == 1, f"state {state(sgb)} frame {i}: frame_counter {last} -> {now}"
        last = now
    assert sum(sgb.read("sfx_count", SFX_COUNT)) > 5, "effects did play during the run"
    assert 0 < sgb.mem("drain_ticks_max") <= 12
    assert sgb.mem16("music_late") <= 30, "the music tick is postponed only on the few frames that are nearly full"


def test_all_tunes_have_a_tempo_that_fits_their_frames():
    """build/music_data.c is generated: every tune's pass length is sane, venue tunes loop 15-30 s, the show tune 8-12 s."""
    import re
    from conftest import ROOT
    src = (ROOT / "build" / "music_data.c").read_text()
    frames = [int(x) for x in re.findall(r"\{&song_\w+, \d, (\d+), \d+, \d+, \w+, \d+, \w+, \d+\}", src)]
    assert len(frames) == TUNE_COUNT + 3, "the title .. venues, then the map's, the credits and the bonus Easy Winners (src/music.h TUNE_MAP, TUNE_CREDITS, TUNE_EWFAST)"
    assert frames.pop() == gm.pass_frames(704, 9, 0xAA) == 5984, "the bonus Easy Winners: 704 rows with the title's swing, 99.7 s, looping (tests/test_music_batch5.py)"
    t = songs.SONGS["credits"]
    assert frames.pop() == gm.pass_frames(707, t["tempo"], 0, t["tempo_map"]) == 10700, "the credits tune: 178.3 s (15 frames a row since 11-13; 9986 at 14) with its ritard, played once (tests/test_credits.py)"
    assert frames.pop() == 8448, "the story map's Swipesy: 768 rows of 11 frames, 140.8 s, looping (tests/test_music_batch5.py)"
    assert frames[TUNE_TITLE] == gm.pass_frames(1216, 9, 0xAA) == 10336, "the title: the whole Entertainer, 173 s, looping (tests/test_music_batch1.py)"
    frames[TUNE_TITLE] = 60
    assert all(60 <= f <= 2400 for f in frames), frames
    venue = frames[TUNE_VENUE0:]
    assert all(15 * 60 <= f <= 36 * 60 for f in venue), f"venue tunes loop for 15-36 s (the owner specs are up to 32 bars of a waltz): {venue}"
    assert 8 * 60 <= frames[TUNE_SHOW] <= 12 * 60, "the show tune loops for 8-12 s"


def test_title_and_every_venue_tune_have_drums():
    """Channel 4 is not silent in the title and the ten venue tunes: a pattern with percussion notes, or a groove
    (src/music.c plays it) with a kick or snare, which divides the tune's length evenly and sits in the tune's own tempo."""
    import re
    src = (ROOT / "build" / "music_data.c").read_text()
    tunes = {"entertainer": "title", **{v: f"venue{i}" for i, v in enumerate(songs.VENUES)}}
    for name, tune in tunes.items():
        t = songs.SONGS[name]
        built = gm.build(name, t, False)
        pattern_hits = sum(1 for chunk in built["per"][4] for note, inst, eff in chunk if note != gm.REST)
        g = gm.groove_rows(name, t)
        assert pattern_hits or (g and (1 in g or 2 in g)), f"{name}: no drums"
        if g:
            assert built["total"] % len(g) == 0, f"{name}: the groove must fit the song a whole number of times"
            m = re.search(r"groove_%s\[\] = \{(\d+), (\d+)," % tune, src)
            assert m and int(m.group(1)) == len(g) and int(m.group(2)) == (t.get("swing", 0) or t["tempo"]), \
                f"{name}: groove table in music_data.c (its second byte: the tempo, or a swing mask over 15)"
    assert len(gm.drum_kit()) == 6 and all(len(r) == 6 for r in gm.drum_kit()), "the one kit: b n t o m x, six register bytes each"


def sample_channel4(rom, frames):
    on = 0
    for _ in range(frames):
        rom.run(1)
        on += bool(rom.mem(NR52) & 8)
    return on


def test_the_title_tune_plays_drums(srom):
    assert srom.mem("cur_tune") == TUNE_TITLE
    assert sample_channel4(srom, 120) > 10, "the title's groove sounds on channel 4"


@pytest.mark.parametrize("group", range(10))
def test_every_venue_tune_sounds_on_channel_4(sgb, group):
    if group:
        goto_group(sgb, group)
    sgb.write("intro_timer", 255)
    assert sgb.mem("cur_tune") == TUNE_VENUE0 + group
    assert sample_channel4(sgb, 150) > 10, f"{songs.VENUES[group]}: channel 4 is silent"


# ---- mix balance (owner: the melody drowned the bass and drums) -------------------------------------------
def test_music_mix_balance_bass_and_drums_sit_under_a_quieter_melody():
    """Measured with PyBoy (RMS per channel solo): melody ~3 vs bass ~3.9 vs drums ~1.5, before the rebalance 4.3 / 2.5 / 1.0.
    This pins the instrument registers so a later change cannot silently put the melody back on top."""
    import re
    vol = lambda env: env >> 4
    # melody: the brass lead (10, every tune's lead since music batch 0) and the plink / thin / ring jingle voices (12) are the loud ones; the rest 8 or less
    for n, (sweep, duty, env, *_) in enumerate(gm.DUTY, 1):
        assert vol(env) <= (12 if n in (3, 4, songs.DUTY_RING) else 10 if n == gm.LEAD_PRO else 8), (n, hex(env))   # 3 plink and 4 thin are short jingle voices; the ring is the credits tune's last chord only
    assert vol(gm.DUTY[0][2]) == 8 and vol(gm.DUTY[gm.LEAD_LEGATO - 1][2]) == 8, "lead and the sung tunes' held lead: volume 8"
    # bass: wave output 100% (NR32 0x20), the pro bass wave spans the full 4-bit range (6 dB louder than the old half-height triangle)
    assert gm.WAVE[0][1] == 0x20 and len(gm.WAVE) == 3, "bass at 100% output; the plucked bass, its held twin and the kick body (starts at 50 %)"
    assert gm.WAVE[2] == (0, 0x40, 0, "sp_kickbass")
    nib = [x for b in gm.WAVES[0] for x in (b >> 4, b & 15)]
    assert len(nib) == 32 and min(nib) <= 3 and max(nib) >= 12, nib
    assert all(abs(a - b) <= 3 for a, b in zip(nib, nib[1:] + nib[:1])), "a smooth wave, no jumps"
    # drums: the one kit b n t o m x (proarr batch 0)
    assert [vol(gm.NOISE[i][0]) for i in range(6)] == [7, 9, 6, 5, 8, 7]
    # the generated tables (what the ROM really has) carry the same numbers
    src = (ROOT / "build" / "music_data.c").read_text()
    assert re.search(r"hUGEWaveInstr_t wave_inst\[\] = \{\s*\{0,32,0,", src)
    duty = re.search(r"duty_inst\[\] = \{(.*?)\};", src, re.S).group(1)
    assert "{8,128,131,0,128}" in duty and "{8,128,128,sp_lead,128}" in duty and "{8,128,165,sp_lead,128}" in duty
    # sound effects stay clearly louder than the melody: channel 1 effects are volume 8-12, the rattle/crash noise 9-13
