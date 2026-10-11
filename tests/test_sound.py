# M7: music (hUGEDriver), sound effects, the saved hi score and the MUSIC ON/OFF switch.
# Register and audio checks need PyBoy's sound emulation, which the shared Rom wrapper leaves off
# (its sound registers read 0), so `sound_rom` swaps in a PyBoy with sound_emulated=True.
import sys
from io import BytesIO

import numpy as np
import pytest
from conftest import GAME, K_SETTINGS, MENU_SETTLE, ROM, ROOT, title_arcade, title_pick
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
TUNE_COUNT = TUNE_VENUE0 + 10
TUNE_GAME = TUNE_VENUE0          # level 1: the cowboys' "Oh! Susanna"
TUNE_NONE = 255
MUG_EMPTY, PATRON_PUSHED = 2, 2
NR50, NR51, NR52 = 0xFF24, 0xFF25, 0xFF26

sys.path.insert(0, str(ROOT / "tools"))
import gen_music as gm       # noqa: E402  (the song sources: what each tune should play)
import songs                 # noqa: E402
from check_music import detect, note_hz      # noqa: E402

GS_LEVEL_CLEAR = 3
GS_SCORES = 10


def sfx_count(gb, i):
    return gb.read("sfx_count", SFX_COUNT)[i]


def new_pyboy(model, ram=None, sound=True):
    return PyBoy(str(ROM), window="null", sound_emulated=sound, cgb=(model == "cgb"), log_level="ERROR",
                 ram_file=BytesIO(ram) if ram is not None else None)


def make_rom(model, ram=None, sound=True):
    """A Rom whose emulator has sound on and optionally a cartridge RAM image (the .sav contents)."""
    rom = Rom(ROM, model)
    rom.pb.stop(save=False)
    rom.pb = new_pyboy(model, ram, sound)
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
    title_arcade(rom)
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


def test_empty_caught(gb):
    gb.write("intro_timer", 255)
    inject_mug(gb, 0, gb.mem("bartender_x"), st=MUG_EMPTY)
    gb.run(2)
    assert gb.mem("last_sfx") == SFX_CATCH and sfx_count(gb, SFX_CATCH) == 1


def test_glass_break_and_life_lost(gb):
    gb.write("intro_timer", 255)
    inject_mug(gb, 1, 17)                       # a full mug about to leave the left end
    run_until(gb, lambda: state(gb) == LIFE_LOST, 20)
    assert sfx_count(gb, SFX_BREAK) == 1 and sfx_count(gb, SFX_LIFE) == 1
    assert gb.mem("last_sfx") == SFX_LIFE


def test_patron_reaching_the_tap_costs_a_life_without_a_break_sound(gb):
    lose_a_life(gb)
    assert sfx_count(gb, SFX_LIFE) == 1 and sfx_count(gb, SFX_BREAK) == 0


def test_patron_served_at_the_left_end(gb):
    gb.write("intro_timer", 255)
    set_patron(gb, 0, GAME["ENTRY_X"], pstate=PATRON_PUSHED)
    put(gb, "patron_aux", gb.read("patron_state", 16).index(PATRON_PUSHED), 4)
    gb.run(2)
    assert gb.mem("last_sfx") == SFX_SERVE and sfx_count(gb, SFX_SERVE) == 1


def test_coin_collected(gb):
    gb.write("intro_timer", 255)
    gb.write("tip_bar", gb.mem("bar"))
    gb.write("tip_x", gb.mem("bartender_x"))
    gb.write("tip_timer", 100)
    gb.run(2)
    assert gb.mem("last_sfx") == SFX_COIN and sfx_count(gb, SFX_COIN) == 1


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
    assert seen == 0xE, f"channels 2, 3 and 4 play the title tune, 1 stays free (NR52 channel bits seen: {seen:#x})"


def test_music_is_audible_and_changes(srom):
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


def test_sfx_drive_channel_1_and_4_and_end(sgb):
    sgb.write("intro_timer", 255)
    sgb.hold("a")
    sgb.run(3)
    assert sgb.mem(NR52) & 1, "fill sound on channel 1"
    sgb.release("a")
    sgb.run(60)
    assert not sgb.mem(NR52) & 1, "channel 1 is silent again once the effect ends (music does not use it)"
    inject_mug(sgb, 1, 17)
    run_until(sgb, lambda: sfx_count(sgb, SFX_BREAK) == 1, 6)
    sgb.run(1)
    assert sgb.mem(NR52) & 8, "the break is a burst on the noise channel (4)"


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


def test_jingle_stops_by_itself(srom):
    start_game(srom)
    srom.write("level", 1)
    clear_level(srom)
    assert srom.mem("cur_tune") == TUNE_CLEAR
    run_until(srom, lambda: srom.mem("cur_tune") != TUNE_CLEAR, 200)
    assert srom.mem("cur_tune") == TUNE_NONE and state(srom) == LEVEL_CLEAR, "the jingle ends before the next screen"
    assert silent(audio_frames(srom, 10))


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
    rows = gm.rows_for(2, t["ch2"], 1, tempo, False, t.get("gap", True), t.get("stac_all"))
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
        k = row * tempo + 1
        if mfs[0] >= k or mfs[-1] < k + ln * tempo + 2:
            continue                                    # not entirely inside what was recorded
        f0 = next(f for f in range(len(mfs)) if mfs[f] >= k) + 1
        # (a long note's volume envelope has faded to near silence well before its last rows: listen to its first 3 rows
        # at most, or the pitch found is the noise floor's, which moves with the music tick's line in the frame)
        hear = min(ln, 3) * tempo
        a, b = int((f0 + 0.2 * hear) * spf), int((f0 + 0.8 * hear) * spf)
        want = note_hz(n)
        got = detect(flat[a:b], rate, want * 0.6, want * 1.7)
        checked.append((row, want, got))
        if not got or abs(12 * np.log2(got / want)) > 0.6:
            wrong.append((row, want, got))
    assert len(checked) >= min_notes, f"only {len(checked)} notes of {source} were inside the recording"
    return checked, wrong


def test_the_title_plays_the_entertainer(srom):
    assert srom.mem("cur_tune") == TUNE_TITLE
    checked, wrong = melody_check(srom, "entertainer", 280)
    assert not wrong, f"title melody differs from The Entertainer's note list: {wrong}"


SUSANNA_SPEC = """C4:1 D4:1
E4:1 G4:1 G4:1 A4:1 G4:1 E4:1 C4:1 D4:1 E4:1 E4:1 D4:1 C4:1 D4:2 C4:1 D4:1
E4:1 G4:1 G4:1 A4:1 G4:1 E4:1 C4:1 D4:1 E4:1 E4:1 D4:1 D4:1 C4:2 C4:1 D4:1
E4:1 G4:1 G4:1 A4:1 G4:1 E4:1 C4:1 D4:1 E4:1 E4:1 D4:1 C4:1 D4:2 C4:1 D4:1
E4:1 G4:1 G4:1 A4:1 G4:1 E4:1 C4:1 D4:1 E4:1 E4:1 D4:1 D4:1 C4:4
F4:2 F4:2 A4:2 A4:2 G4:1 G4:1 E4:1 C4:1 D4:2 C4:1 D4:1
E4:1 G4:1 G4:1 A4:1 G4:1 E4:1 C4:1 D4:1 E4:1 E4:1 D4:1 D4:1 C4:4"""


def test_the_oh_susanna_song_data_is_the_owners_note_list():
    assert songs.SONGS["susanna"]["ch2"].split() == SUSANNA_SPEC.split()
    assert songs.SONGS["susanna"]["tempo"] == 15, "120 bpm quarter = 15 frames per eighth-note row"
    bass = songs.SONGS["susanna"]["ch3"].replace("!", "").split()
    assert bass[:5] == ["r:2", "C3:2", "G2:2", "C3:2", "G2:2"] and bass[-1] == "C3:4", "boom-chick, final bar a whole-bar root"
    assert songs.SONGS["susanna"]["ch4"].split()[-2:] == ["K:1", "r:3"], "final bar: kick then rests"


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
    """The spec bars with the two documented adaptations: Pop Goes the Weasel's last rest is the D4 pickup, the
    Blue Danube holds the first note of an 'X R Y' bar through the rest.  (Pickup lines are not bars: they are the
    first-time-only lead-ins, left out so that the loop is seamless.)"""
    bars = list(bars)
    if name == "weasel":
        assert bars[-1].endswith("R:1")
        bars[-1] = bars[-1][:-3] + "D4:1"
    if name == "danube":
        for i, b in enumerate(bars):
            tk = b.split()
            if len(tk) == 3 and tk[1] == "R:2" and tk[0].endswith(":2"):
                bars[i] = tk[0][:-2] + ":4 " + tk[2]
    return bars


# the spec's tempo (the game plays songs.GAME_BPM where that lists the tune): beats per minute and song rows per beat
SPEC_BPM_ROWS = {"funicula": (92, 3), "skaters": (160, 2), "ballgame": (168, 2), "mountain": (160, 2), "weasel": (100, 3),
                 "danube": (160, 2), "hall": (120, 2), "sakura": (100, 2), "entertainer": (90, 4), "galop": (160, 2),
                 "sailor": (200, 2)}


def test_the_tunes_are_the_specs_token_for_token():
    specs = parse_specs()
    assert sorted(specs) == sorted(SPEC_TUNES.values())
    for name, (bars, chords) in specs.items():
        s = songs.SONGS[name]
        want = " ".join(spec_bars_for_the_game(name, bars)).split()
        assert [t.rstrip("!") for t in s["ch2"].split()] == want, f"{name}: melody differs from docs/music_specs.md"
        per_bar = songs.BAR_ROWS[name]
        for ch in ("ch2", "ch3"):                       # every bar adds up (ties included), melody and bass
            rows = gm.merge_ties(s[ch]).split()
            assert sum(int(t.split(":")[1].rstrip("!")) for t in rows) == per_bar * len(bars), f"{name} {ch} length"
        bpm, rows_per_beat = SPEC_BPM_ROWS[name]
        bpm = songs.GAME_BPM.get(name, bpm)             # the owner-approved game tempo (the spec's where none is listed)
        ideal = 3600 / bpm / rows_per_beat
        assert abs(s["tempo"] - ideal) / ideal < 0.05, f"{name} tempo {s['tempo']} vs {ideal:.1f} frames per row (game tempo {bpm} bpm)"
        if name in ("hall", "sakura"):
            continue                                    # root ostinato / drone, not chords
        bass = s["ch3"].replace("!", "").split()
        i = 0
        for chord in chords:                            # the bass plays the bar's chord: its root on the downbeat
            assert bass[i].split(":")[0] == songs.CHORD[chord.split("/")[0]][0], f"{name}: chord {chord} vs bass {bass[i]}"
            n = 0
            while n < per_bar:
                n += int(bass[i].split(":")[1])
                i += 1
            assert n == per_bar


def test_hall_of_the_mountain_king_is_staccato_over_a_root_ostinato():
    s = songs.SONGS["hall"]
    assert s["stac_all"] == (1, 2)
    bass = s["ch3"].replace("!", "").split()
    assert set(bass[:32]) == {"B2:2"} and set(bass[32:48]) == {"F#2:2"} and set(bass[48:]) == {"B2:2"}
    rows = gm.rows_for(2, s["ch2"], 1, s["tempo"], False, True, s["stac_all"])
    cuts = [eff for _, _, eff in rows if (eff & 0xF00) == 0xE00]
    assert len(cuts) > 80 and set(c & 0xFF for c in cuts) >= {7}, "a 1-row note is cut after 7 of its 15 ticks"


def test_ties_fold_into_the_previous_note():
    assert gm.merge_ties("C5:2 ~:3 D5:1 ~:1") == "C5:5 D5:2"
    assert gm.merge_ties("R:2 C5:1! ~:2") == "r:2 C5:3!"


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
    return music_line(gb)          # the title's MUSIC line (SETTINGS' only line, row 9)


def test_select_toggles_the_music(srom):
    title_pick(srom, K_SETTINGS)   # (SELECT works on any menu level; SETTINGS shows the line)
    srom.run(MENU_SETTLE)
    assert srom.mem("sound_on") == 1 and music_text(srom) == title_text_row("music_on")
    srom.press("select", 2)
    srom.run(2)
    assert srom.mem("sound_on") == 0 and music_text(srom) == title_text_row("music_off")
    f = srom.mem16("music_frames")
    srom.run(30)
    assert srom.mem16("music_frames") == f, "the driver is not ticking while the music is off"
    assert silent(audio_frames(srom, 10)), "silent (the driver cuts the notes)"
    srom.press("select", 2)
    srom.run(2)
    assert srom.mem("sound_on") == 1 and music_text(srom) == title_text_row("music_on")
    srom.run(30)
    assert srom.mem(NR52) & 0x06, "the title tune is back"


def test_music_off_persists_into_the_game_but_effects_still_play(srom):
    srom.press("select", 2)
    start_game(srom)
    srom.write("intro_timer", 255)
    srom.hold("a")
    srom.run(3)
    assert srom.mem("sound_on") == 0 and srom.mem("last_sfx") == SFX_FILL
    assert srom.mem(NR52) & 1, "effects are not part of the music switch"
    assert not srom.mem(NR52) & 0x0A and srom.mem("cur_tune") == TUNE_GAME, "the music channels are cut"


def test_select_does_nothing_outside_the_title(gb):
    gb.press("select", 2)
    gb.run(2)
    assert gb.mem("sound_on") == 1


# ---- saved hi score (M10b: the top-5 table; SRAM version 6 since the 10th venue: "TPR6", 5 x (3 initials, 3-byte
# score), the story progress at 34, the step reached at 35, the unlocked tunes at 36-37, checksum at 38) ----
SAVE_SUM = 38
def earn_fifty_and_lose(rom):
    start_game(rom)
    rom.write("intro_timer", 255)
    inject_mug(rom, 0, GAME["ENTRY_X"] + 8)
    rom.run(6)
    assert score(rom) == 50
    for n in range(3):
        lose_a_life(rom)
        if n < 2:
            run_until(rom, lambda: state(rom) == PLAYING, 200)
    run_until(rom, lambda: state(rom) == GAME_OVER, 200)
    assert hi_score(rom) == 50


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_hi_score_survives_a_reset(model):
    rom = make_rom(model, sound=False)
    rom.run(120)
    assert hi_score(rom) == 0, "a fresh cartridge starts at 0"
    earn_fifty_and_lose(rom)
    ram = save_ram(rom)
    assert ram[:4] == b"TPR6" and ram[4:7] == b"AAA" and int.from_bytes(ram[7:10], "little") == 50
    with make_rom(model, ram, sound=False) as again:     # power cycle with the same battery RAM
        again.run(120)
        assert hi_score(again) == 50
        assert hi_shown(again) == hi_tiles("000050"), "the title shows the saved HI"
        assert [d for d in again.read("hi_digits", 6)] == [0, 0, 0, 0, 5, 0]


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


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_invalid_save_data_loads_as_zero(model):
    rom = make_rom(model, sound=False)
    rom.run(120)
    earn_fifty_and_lose(rom)
    good = save_ram(rom)
    cases = {
        "bad signature": corrupt(good, lambda r: r.__setitem__(0, ord("X"))),
        "flipped score bit": corrupt(good, lambda r: r.__setitem__(7, r[7] ^ 0x01)),
        "bad checksum": corrupt(good, lambda r: r.__setitem__(SAVE_SUM, (r[SAVE_SUM] + 1) & 255)),
        "bad complement": corrupt(good, lambda r: r.__setitem__(SAVE_SUM + 1, r[SAVE_SUM + 1] ^ 0xFF)),
        "blank": bytes(len(good)),
        "garbage": bytes((i * 37 + 11) & 255 for i in range(len(good))),
    }

    def with_checksum(r):                       # a well-formed record whose score is absurd (>= 1,000,000)
        r[7:10] = (2_000_000).to_bytes(3, "little")
        c = (0x5A + sum(r[:SAVE_SUM])) & 255
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
    frames = [int(x) for x in re.findall(r"\{&song_\w+, \d, (\d+), \d+, \d+, \w+, \d+, \w+\}", src)]
    assert len(frames) == TUNE_COUNT and all(60 <= f <= 2400 for f in frames), frames
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
            assert m and int(m.group(1)) == len(g) and int(m.group(2)) == t["tempo"], f"{name}: groove table in music_data.c"
    assert len(gm.drum_kit()) == 3


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
    # melody: every pulse instrument at volume <= 8 (it was 10 / 9 / 12 / 9 / 10); the song lead and the lead are 8 or less
    for n, (sweep, duty, env) in enumerate(gm.DUTY, 1):
        assert vol(env) <= (12 if n in (3, 4) else 8), (n, hex(env))   # 3 plink and 4 thin are short jingle voices
    assert vol(gm.DUTY[4][2]) == 8 and vol(gm.DUTY[0][2]) == 8, "song lead and lead: volume 8"
    # bass: wave output 100% (NR32 0x20), triangle samples scaled to half range so it is not buzzy
    assert gm.WAVE[0][1] == 0x20, "bass at 100% output"
    nib = [x for b in gm.WAVES[0] for x in (b >> 4, b & 15)]
    assert len(nib) == 32 and 3 <= min(nib) <= 5 and 10 <= max(nib) <= 12, nib
    assert all(abs(a - b) <= 1 for a, b in zip(nib, nib[1:] + nib[:1])), "a smooth triangle, no jumps"
    # drums: quiet kit (the groove kit) at volume 8 / 7 / 6, loud kit unchanged
    assert [vol(gm.NOISE[i][0]) for i in (3, 4, 5)] == [8, 7, 6]
    assert [vol(gm.NOISE[i][0]) for i in (0, 1, 2)] == [8, 6, 3]
    # the generated tables (what the ROM really has) carry the same numbers
    src = (ROOT / "build" / "music_data.c").read_text()
    assert re.search(r"hUGEWaveInstr_t wave_inst\[\] = \{\s*\{0,32,0,", src)
    duty = re.search(r"duty_inst\[\] = \{(.*?)\};", src, re.S).group(1)
    assert "{8,128,131,0,128}" in duty and "{8,128,133,0,128}" in duty
    # sound effects stay clearly louder than the melody: channel 1 effects are volume 8-12, the rattle/crash noise 9-13
