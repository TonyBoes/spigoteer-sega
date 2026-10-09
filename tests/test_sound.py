# M7: music (hUGEDriver), sound effects, the saved hi score and the MUSIC ON/OFF switch.
# Register and audio checks need PyBoy's sound emulation, which the shared Rom wrapper leaves off
# (its sound registers read 0), so `sound_rom` swaps in a PyBoy with sound_emulated=True.
from io import BytesIO

import numpy as np
import pytest
from conftest import ROM
from gbtools import Rom
from pyboy import PyBoy
from test_bonus import PH_SHAKE, enter_bonus, to_phase
from test_flow import (BONUS, GAME_OVER, LEVEL_CLEAR, LIFE_LOST, PLAYING, TITLE, clear_level, hi_score,
                       inject_mug, lose_a_life, put, run_until, score, set_patron, state, tile_id, tilemap_row)

pytestmark = pytest.mark.timeout(120)

SFX_NONE, SFX_FILL, SFX_LAUNCH, SFX_CATCH, SFX_BREAK, SFX_SERVE, SFX_COIN, SFX_LIFE, SFX_SHAKE, SFX_COUNT = range(10)
TUNE_TITLE, TUNE_GAME, TUNE_CLEAR, TUNE_OVER, TUNE_BONUS, TUNE_COUNT = range(6)
TUNE_NONE = 255
MUG_EMPTY, PATRON_PUSHED = 2, 2
NR50, NR51, NR52 = 0xFF24, 0xFF25, 0xFF26


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
    rom.press("start", 2)
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
    """Run n frames and return the stereo samples produced (int8, shape (samples, 2))."""
    chunks = []
    for _ in range(n):
        rom.run(1)
        chunks.append(rom.pb.sound.ndarray.copy())
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


def test_patron_served_out_the_door(gb):
    gb.write("intro_timer", 255)
    set_patron(gb, 0, 0, pstate=PATRON_PUSHED)
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
    assert srom.mem16("music_frames") == frames0 + 120, "driver ticked once per frame"
    assert srom.mem("hUGE_row") != row0, "the song advances"
    assert seen == 0x6, f"channels 2 and 3 play the title tune, 1 and 4 stay free (NR52 channel bits seen: {seen:#x})"


def test_music_is_audible_and_changes(srom):
    a = audio_frames(srom, 60).astype(float)
    b = audio_frames(srom, 60).astype(float)
    assert a.std() > 2 and b.std() > 2, "not silent"
    mono_a, mono_b = a.mean(axis=1), b.mean(axis=1)
    fa = np.abs(np.fft.rfft(mono_a - mono_a.mean())).argmax()
    fb = np.abs(np.fft.rfft(mono_b - mono_b.mean())).argmax()
    assert fa != fb, "pitch moves from one second to the next (a melody, not a drone)"


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
    assert srom.mem("cur_tune") == TUNE_GAME
    row = srom.mem16("music_frames")
    srom.run(5)
    assert srom.mem16("music_frames") == row + 5, "a looping tune keeps going"
    clear_level(srom)
    assert srom.mem("cur_tune") == TUNE_CLEAR
    run_until(srom, lambda: state(srom) == PLAYING, 400)
    assert srom.mem("cur_tune") == TUNE_GAME


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
    srom.press("start", 2)
    run_until(srom, lambda: state(srom) == TITLE, 30)
    assert srom.mem("cur_tune") == TUNE_TITLE


def test_bonus_round_has_its_own_tune(srom):
    start_game(srom)
    enter_bonus(srom)
    assert srom.mem("cur_tune") == TUNE_BONUS


# ---- MUSIC ON / OFF -------------------------------------------------------------------------
def music_text(gb):
    return tilemap_row(gb, 14, 5, 9)


def glyphs(s):
    return [tile_id("HUD_BLANK") if c == " " else tile_id("GLYPH_" + c) for c in s]


def test_select_toggles_the_music(srom):
    assert srom.mem("sound_on") == 1 and music_text(srom) == glyphs("MUSIC ON ")
    srom.press("select", 2)
    srom.run(2)
    assert srom.mem("sound_on") == 0 and music_text(srom) == glyphs("MUSIC OFF")
    f = srom.mem16("music_frames")
    srom.run(30)
    assert srom.mem16("music_frames") == f, "the driver is not ticking while the music is off"
    assert silent(audio_frames(srom, 10)), "silent (the driver cuts the notes)"
    srom.press("select", 2)
    srom.run(2)
    assert srom.mem("sound_on") == 1 and music_text(srom) == glyphs("MUSIC ON ")
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


# ---- saved hi score --------------------------------------------------------------------------
def earn_fifty_and_lose(rom):
    start_game(rom)
    rom.write("intro_timer", 255)
    inject_mug(rom, 0, 8)
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
    assert ram[:4] == b"TPR1" and int.from_bytes(ram[4:8], "little") == 50
    with make_rom(model, ram, sound=False) as again:     # power cycle with the same battery RAM
        again.run(120)
        assert hi_score(again) == 50
        assert tilemap_row(again, 12, 8, 6) == glyphs("000050"), "the title shows the saved HI"
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
        assert save_ram(again)[:10] == ram[:10], "SRAM unchanged when the hi score is not beaten"


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
        "flipped score bit": corrupt(good, lambda r: r.__setitem__(4, r[4] ^ 0x01)),
        "bad checksum": corrupt(good, lambda r: r.__setitem__(8, (r[8] + 1) & 255)),
        "bad complement": corrupt(good, lambda r: r.__setitem__(9, r[9] ^ 0xFF)),
        "blank": bytes(len(good)),
        "garbage": bytes((i * 37 + 11) & 255 for i in range(len(good))),
    }

    def with_checksum(r):                       # a well-formed record whose score is absurd (>= 1,000,000)
        r[4:8] = (2_000_000).to_bytes(4, "little")
        c = (0x5A + sum(r[:8])) & 255
        r[8], r[9] = c, c ^ 0xFF
    cases["out of range"] = corrupt(good, with_checksum)
    for name, ram in cases.items():
        with make_rom(model, ram, sound=False) as again:
            again.run(120)
            assert hi_score(again) == 0, name
            assert tilemap_row(again, 12, 8, 6) == glyphs("000000"), name


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
    """build/music_data.c is generated: every tune's pass length is a whole number of rows."""
    import re
    from conftest import ROOT
    src = (ROOT / "build" / "music_data.c").read_text()
    frames = [int(x) for x in re.findall(r"\{&song_\w+, \d, (\d+)\}", src)]
    assert len(frames) == TUNE_COUNT and all(60 <= f <= 1800 for f in frames), frames
