# The show tune, Galop infernal, in the owner-approved "v2" arrangement (tools/songs.py, tools/gen_music.py; the audition was
# tools/promusic.py on branch promusic): a counter-melody harmony, a walking bass on a full-amplitude wave plucked by a table,
# a brass lead with a duty attack and a delayed vibrato (a table), a drum kit in a channel-4 pattern with fills, plain two-note stabs.
# The ROM's tune data is the generator's output; no other tune's data changed; the real driver plays the tables.
import filecmp
import sys

import pytest
from conftest import ROOT
from test_credits import BUILD, dn, rom_bank, rom_bytes
from test_pause import NR51, rom_s
from test_sound import start_a_show, start_game, w16

sys.path.insert(0, str(ROOT / "tools"))
import gen_music as gm      # noqa: E402
import songs                # noqa: E402
pytestmark = pytest.mark.only_model('dmg')   # model_equiv.py: DMG and Color proven equal for every test here

TUNE_SHOW = 4
NR21, NR32, NR43 = 0xFF16, 0xFF1C, 0xFF22


def galop():
    t = songs.SONGS["galop"]
    return t, gm.build("show", t, False)


def test_the_show_tune_in_the_rom_is_the_generators_output(tmp_path, monkeypatch):
    t, b = galop()
    monkeypatch.setattr(sys, "argv", ["gen_music", str(tmp_path)])
    gm.main()
    for f in ("music_data.c", "music_pat10.c", "music_pat22.c", "music_pat23.c", "music_pat24.c"):
        assert filecmp.cmp(tmp_path / f, BUILD / f, shallow=False), f + " is stale"
    pats = []
    for c in (1, 2, 3, 4):
        for k in b["per"][c]:
            if k != gm.EMPTY and k not in pats:
                pats.append(k)
    assert len(pats) == 3, "melody, bass and drums: 576 B (it was 384)"
    assert rom_bytes("blob_show", 3 * gm.SLOT_BYTES) == b"".join(dn(k) for k in pats)
    h = bytes(gm.harm_bytes(t, gm.harm_events("show", t, b["total"])))
    assert len(h) == 106 and rom_bytes("harm_show", len(h)) == h and rom_bank("harm_show") == gm.HARM_BANK
    data = (BUILD / "music_data.c").read_text()
    assert "unsigned char mus_buf_b[576]" in data
    assert "{&song_show, 1, 704, 2, 10, blob_show, 576, NULL, 0}" in data, "no groove: the drums are a pattern"


def test_the_arrangement_is_the_audition_v2():
    t, b = galop()
    assert t["inst"] == gm.LEAD_PRO and t["groove"] == "" and t["ch1_inst"] == ("voice", "voice")
    assert gm.DUTY[gm.LEAD_PRO - 1] == (0x08, 0x80, 0xA5, "sp_lead") and gm.WAVE[gm.BASS_PRO - 1] == (0, 0x20, 0, "sp_bass")
    assert [len(gm.SUBPAT[k]) for k in ("sp_lead", "sp_bass", "sp_kick", "sp_snare")] == [16, 16, 3, 2]
    nib = [x for byte in gm.WAVES[0] for x in (byte >> 4, byte & 15)]
    assert min(nib) <= 3 and max(nib) >= 12, "the new bass wave spans 2..13 of 0..15 (the old triangle 4..11)"
    # the bass's table steps NR32 100 % (7 ticks), 50 % (5), 25 % (3), then off: 0xC05, 0xC02, 0xC00
    assert [e for _, _, e in gm.SUBPAT["sp_bass"] if e] == [0xC05, 0xC02, 0xC00]
    # the drum pattern: kick, closed hat, snare, closed hat; open hat closing bar 8; a snare double closing bar 16
    k, t_, n, o = (gm.NOISE_NOTE[c] for c in "btno")
    drums = [row[0] for row in b["per"][4][0]]
    assert drums[:4] == [k[0], t_[0], n[0], t_[0]] and drums[28:32] == [k[0], t_[0], n[0], o[0]] and drums[60:64] == [k[0], t_[0], n[0], n[0]]
    # the other tunes keep their groove or pattern drums (all on the one kit since music batch 0)
    assert all(songs.SONGS[s]["groove"] or songs.SONGS[s]["ch4"] for s in songs.SONGS if s not in ("credits",))
    # "vstab" and the arpeggio route stay available for another song
    assert gm.HARM_INST["vstab"] == (0x40, 0x62) and "ARPEGGIO CHORD STABS" in (ROOT / "tools" / "gen_music.py").read_text()


def test_no_other_tune_changed(tmp_path, monkeypatch):
    """Every other tune's patterns, harmony and instruments are what they were: only the show's blob, order table, buffer B and the
    appended instruments differ from the generator's output before this arrangement (git: the old galop's rows are gone)."""
    data = (BUILD / "music_data.c").read_text()
    for name in ("title", "venue0", "venue1", "venue2", "venue3", "venue4", "venue5", "venue6", "venue7", "venue8", "venue9"):
        assert f"{name}_order_cnt" in data
    for g in ("entertainer", "ballgame", "funicula", "skaters", "sakura", "danube", "sailor"):
        assert songs.SONGS[g]["groove"], g
    assert "static const unsigned char groove_show" not in data and data.count("static const unsigned char groove_") == 7


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_real_driver_plays_the_tables_and_the_pause_mix_is_bass_and_drums(model):
    with rom_s(model) as gb:
        start_game(gb)
        gb.run(400)
        start_a_show(gb)
        assert gb.mem("cur_tune") == TUNE_SHOW
        w16(gb, "show_timer", 60000)
        nr32, nr21, nr43 = set(), set(), set()
        for _ in range(704):
            gb.run(1)
            nr32.add(gb.mem(NR32) & 0x60); nr21.add(gb.mem(NR21) & 0xC0); nr43.add(gb.mem(NR43))
        assert {0x20, 0x40, 0x60} <= nr32, "the bass pluck: 100, 50 and 25 % (" + str(sorted(nr32)) + ")"
        assert {0x40, 0x80} <= nr21, "the lead starts at 50 % duty and settles to 25 %"
        assert {0x37, 0x57, 0x77, 0x27, 0x00} <= nr43, sorted(hex(v) for v in nr43)   # the kick drops over three ticks, the snare cracks then has its body
        gb.press("start", 2)
        gb.run(3)
        assert gb.mem("game_state") == 5 and gb.mem(NR51) == 0xCC, "paused: bass and drums only"
        gb.run(120)
        assert gb.mem("cur_tune") == TUNE_SHOW and gb.mem(NR51) == 0xCC
