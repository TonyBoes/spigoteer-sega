# Music batch 0 (owner-approved 2026-10-17, docs/proarr/BATCH_0.md on branch promusic): ONE drum kit for the groove player and the pattern
# drums (gen_music.KIT, NR43 values), and the brass lead / held twin / plucked bass for every tune.  Pinned values here are the spec's.
import re
import sys

import pytest
from conftest import ROOT
from conftest import K_BONUS, K_CREDITS, hold_stage_anim, title_pick
from test_credits import BUILD, SP_CREDITS
from test_flow import run_until
from test_sound import TUNE_VENUE0, make_rom, sgb, srom  # noqa: F401  (fixtures)

sys.path.insert(0, str(ROOT / "tools"))
import gen_music as gm       # noqa: E402
import songs                 # noqa: E402

NR32, NR43 = 0xFF1C, 0xFF22

# letter -> (NR42, 7-bit flag, NR41 length or None, NR43 steps without the flag): the spec's kit (BATCH_0.md)
SPEC_KIT = {   # the "-3" research kit, tom R3, rim R2 (owner 2026-11-12)
    "b": (0x71, 0, None, [0x37, 0x57, 0x77]),
    "n": (0x91, 0, None, [0x35, 0x57, 0x16]),
    "t": (0x61, 0, 52, [0x06]),
    "o": (0x53, 0, None, [0x15]),
    "m": (0x82, 0, 18, [0x44, 0x55, 0x56]),
    "x": (0x71, 8, 55, [0x14]),
}


def driver_steps(letter):
    """NR43 the driver writes on the ticks of a drum letter: the note's poly, then the table's offsets from it (hUGEDriver subpattern
    rows run one per tick; the instrument's 7-bit flag ORs bit 3)."""
    note, inst = gm.NOISE_NOTE[letter]
    ins = gm.NOISE[inst - 1]
    flag = 0x08 if ins[1] & 0x80 else 0
    if len(ins) < 3:
        return [gm.driver_poly(note) | flag]
    return [gm.driver_poly(note + (n - 36)) | flag for n, _, _ in gm.SUBPAT[ins[2]]]


def test_the_generated_kit_is_the_spec():
    assert gm.KIT_ORDER == "bntomx" and [gm.DRUM_ID[c] for c in gm.KIT_ORDER] == [1, 2, 3, 4, 5, 6]
    assert len(gm.NOISE) == 6 and len(gm.drum_kit()) == 6
    for i, letter in enumerate(gm.KIT_ORDER):
        env, flag, length, steps = SPEC_KIT[letter]
        row = gm.drum_kit()[i]
        want = [v | flag for v in steps]
        assert row == (length or 0, env, want[0], 0x80 | (0x40 if length is not None else 0),
                       (want + [want[-1]] * 2)[1], (want + [want[-1]] * 2)[2]), letter
        assert gm.NOISE[i][0] == env and bool(gm.NOISE[i][1] & 0x80) == bool(flag), letter
        assert gm.NOISE_NOTE[letter][1] == i + 1
    # the generated C: six groove rows, the noise instruments
    src = (BUILD / "music_data.c").read_text()
    assert "const unsigned char drum_kit[6][6] = {{0x00,0x71,0x37,0x80,0x57,0x77}, {0x00,0x91,0x35,0x80,0x57,0x16}, " \
           "{0x34,0x61,0x06,0xC0,0x06,0x06}, {0x00,0x53,0x15,0x80,0x15,0x15}, {0x12,0x82,0x44,0xC0,0x55,0x56}, {0x37,0x71,0x1C,0xC0,0x1C,0x1C}};" in src
    assert "extern const unsigned char drum_kit[6][6];" in (ROOT / "src" / "music.h").read_text()
    assert not (ROOT / "tools" / "gen_music.py").read_text().count("def noise_poly")


@pytest.mark.parametrize("letter", "bntomx")
def test_the_driver_writes_the_kits_nr43_values_and_the_groove_rows_are_the_same_bytes(letter):
    env, flag, length, steps = SPEC_KIT[letter]
    want = [v | flag for v in steps]
    assert driver_steps(letter) == want, "the pattern route (note + table)"
    row = gm.drum_kit()[gm.KIT_ORDER.index(letter)]
    route = [row[2], row[4], row[5]]
    assert route[:len(want)] == want and set(route[len(want):]) <= {want[-1]}, "the groove route (hit + two frames)"


def test_every_tune_uses_the_shared_instruments():
    assert (gm.LEAD_PRO, gm.LEAD_LEGATO, gm.BASS_PRO, gm.BASS_HELD) == (6, 7, 1, 2)
    assert gm.DUTY[5] == (0x08, 0x80, 0xA5, "sp_lead") and gm.DUTY[6] == (0x08, 0x80, 0x80, "sp_lead")
    assert gm.WAVE == [(0, 0x20, 0, "sp_bass"), (0, 0x20, 0), (0, 0x40, 0, "sp_kickbass")] and gm.KICK_BODY == 3 and len(gm.WAVES) == 1 and len(gm.DUTY) == 7
    for name, t in songs.SONGS.items():
        assert t["inst"] == (gm.LEAD_LEGATO if t["legato"] else gm.LEAD_PRO), name
        b = gm.build(name, t, False)
        assert {ins for chunk in b["per"][3] for note, ins, eff in chunk if note != gm.REST} <= {gm.BASS_PRO, gm.BASS_HELD, gm.KICK_BODY}, name
    for name, t in gm.JINGLES.items():
        b = gm.build(name, t, True)
        assert {ins for chunk in b["per"][3] for note, ins, eff in chunk if note != gm.REST} == {gm.BASS_HELD if name == "over" else gm.KICK_BODY if name == "bonus" else gm.BASS_PRO}, name   # (batch 4: the game-over bass is held; the bonus loop's bass is all on its kicks: the kick body)
    # nothing of the old kits or waves is left
    assert not any(k.startswith("sp_") and k in ("sp_hollow", "sp_old") for k in gm.SUBPAT)
    for letter in "KSHksh":
        assert letter not in gm.NOISE_NOTE


def nr43_run(gb, frames):
    seq = []
    for _ in range(frames):
        gb.run(1)
        v = gb.mem(NR43)
        if not seq or seq[-1] != v:
            seq.append(v)
    return seq


def contains(seq, sub):
    return any(seq[i:i + len(sub)] == sub for i in range(len(seq) - len(sub) + 1))


def test_the_groove_route_in_the_game_steps_the_kick_and_the_snare(srom):
    assert srom.mem("cur_tune") == 0
    seq = nr43_run(srom, 300)        # the title: kick, hat, snare, hat
    assert contains(seq, [0x37, 0x57, 0x77]), [hex(v) for v in seq]
    assert contains(seq, [0x35, 0x57, 0x16]) and 0x06 in seq


@pytest.mark.only_model('dmg')
def test_the_pattern_route_in_the_game_steps_the_kick_and_the_snare(sgb):
    sgb.run(300)
    assert sgb.mem("cur_tune") == TUNE_VENUE0
    seq = nr43_run(sgb, 300)         # Oh! Susanna: a pattern tune
    assert contains(seq, [0x37, 0x57, 0x77]), [hex(v) for v in seq]
    assert contains(seq, [0x35, 0x57, 0x16])


def test_the_credits_last_chord_fades_100_50_25_percent():
    """hUGEDriver reads the LOW nibble of Cxy for the wave channel: 0xC50 and 0xC20 both gave 25 %."""
    t = songs.SONGS["credits"]
    assert t["fx_map"] == {702: [(3, 0xC05)], 704: [(3, 0xC02)]}
    b = gm.build("credits", t, False)
    rows = [r for chunk in b["per"][3] for r in chunk]
    assert rows[702][2] == 0xC05 and rows[704][2] == 0xC02
    last = [(i, r) for i, r in enumerate(rows) if r[0] != gm.REST and r[2] != 0xC05][-1]
    assert last[1][1] == gm.BASS_HELD, "the last chord's bass is held (the pluck table would be silent before its fade)"
    start = gm.pass_frames(699, 14, 0, t["tempo_map"])
    with make_rom("cgb") as gb:                 # (sound on: the APU registers read back)
        gb.run(120)
        hold_stage_anim(gb)
        title_pick(gb, K_BONUS, K_CREDITS)
        run_until(gb, lambda: gb.mem("story_phase") == SP_CREDITS, 20)
        while gb.mem16("music_frames") < start - 3:
            gb.run(1)
        seq = []
        while gb.mem("cur_tune") == 15 and gb.mem16("music_frames") < gm.pass_frames(707, 14, 0, t["tempo_map"]) - 2:
            gb.run(1)
            v = gb.mem(NR32) & 0x60
            if not seq or seq[-1] != v:
                seq.append(v)
    assert contains(seq, [0x20, 0x40, 0x60]) and 0x20 in seq[:3], [hex(v) for v in seq]   # (then the tune ends: the channel goes quiet)
