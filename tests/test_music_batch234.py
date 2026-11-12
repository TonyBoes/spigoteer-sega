# Music batches 2-4 (owner-approved 2026-10-17; docs/proarr/BATCH_2.md, BATCH_3.md, BATCH_4.md and specs/ on branch promusic): the pro arrangements of
# the lodge, the bistro, the igloo, the factory, the Chrome Cow, the teahouse, the zoo and the space lounge, the three jingles' instruments and the
# credits tune's held bass.  The generated notes equal a pinned digest (taken from tools/proarr.py, since removed; re-pin to change them; the format of test_music_batch1.py;
# a wave instrument's definition is compared without an empty subpattern: proarr's held bass has one, ours has none).
import hashlib
import json
import re
import sys

import pytest
from conftest import ROM, ROOT
from gbtools import Rom
from test_credits import BUILD, K_BONUS, K_CREDITS, SP_CREDITS, dn, hold_stage_anim, rom_bank, rom_bytes, run_until, title_pick
from test_sound import TUNE_VENUE0, goto_group, make_rom, start_game

sys.path.insert(0, str(ROOT / "tools"))
import gen_music as gm       # noqa: E402
import harmony as H          # noqa: E402
import songs                 # noqa: E402

PROARR_DIGEST = {
    "mountain": "92568920b5ca9d3cd93f88c90ea72392778c373942ed0a5bd33dbfbde350f217",
    "funicula": "a9c9e4ffb48e5282f3d89ca225fd07e33717db1e1906ec4ca6a55a05c4b181f9",
    "skaters": "e254edcadbbac3aff1ce4287a81d8ea672e5f548a791858ab83006283b6e8428",
    "hall": "c7351846b768a12f0f4b3b14be8a11c7eebff9cea8a4c518c0725659ee5dc284",
    "sailor_b3": "a8dd610c594f7e03301285b4b7f476a711e0b957566ed9afe75526341928fb93",
    "sailor_b3d": "28ed6bb0d1f61d4785c0326e424b3844297986ce1ff17df4d37d2e5232931262",
    "sakura": "38896962c15c6d6069cd557b94c88dd27130c5cec33b9c45ad0d21f193581391",
    "weasel": "36d160ee8ff12326c5025e6e8cd879226eca636405672eff37b156cbd3124386",
    "danube": "f5160eb474f328b4be47071e9b57fef897b5ca2755690d84f16b373fc03aae1a",
    "credits": "f9f63964c029d1113e9349535c857255968f41cc0cb71192c457456ac9724689",       # the brass lead (CREDITS_B4=1)
    "clear": "e1f92054abecbb3bcee2ff89143b8104948dc2802619f258fb7b6b6e7b8a6f4d",
    "over": "beab595b30400ce1bc0b809751e64f53aa3cfc155b235ca90248d4105950e133",
    "bonus": "1a655f3be5e09db68d0d388acdbbe6a137af95ab1ed208f2a1fe7777d58ae4df",
}
GROUP = {n: i for i, n in enumerate(songs.VENUES)}


def definition(c, inst):
    if inst == 0:
        return None
    ins = list(({2: gm.DUTY, 3: gm.WAVE, 4: gm.NOISE}[c])[inst - 1])
    if c == 3:
        ins[2] = gm.WAVES[ins[2]]
        if len(ins) == 4 and ins[3] == 0:
            ins = ins[:3]
    return json.dumps([("DUTY", "WAVE", "NOISE")[c - 2], ins])


def digest(source, t, jingle=False):
    b = gm.build(source, t, jingle)
    chans = (2, 3, 4) if source != "credits" else (2, 3)
    rows = {c: [[(None if n == gm.REST else n, definition(c, i), e) for n, i, e in chunk] for chunk in b["per"][c]] for c in chans}
    letters = {v: k for k, v in gm.DRUM_ID.items()}
    harm = gm.harm_bytes(t, gm.harm_events(source, t, b["total"])) if t.get("ch1") else []
    g = [] if jingle else (gm.groove_rows(source, t) or [])
    d = {"rows": rows, "harm": harm, "groove": [letters.get(x) if x else None for x in g]}
    return hashlib.sha256(json.dumps(json.loads(json.dumps(d)), sort_keys=True).encode()).hexdigest()


def sailor_variant(variant):
    mel, fx = songs.sailor_arp() if variant == "b3d" else (" ".join(songs.SAI_BARS), None)
    return dict(songs.SONGS["sailor"], ch2=mel, fx_map=fx)


@pytest.mark.parametrize("name", ["mountain", "funicula", "skaters", "hall", "sakura", "weasel", "danube"])
def test_the_generated_notes_are_proarrs(name):
    assert digest(name, songs.SONGS[name]) == PROARR_DIGEST[name]


def test_the_sailor_is_the_arpeggio_variant_and_one_line_switches_to_the_plain_riff():
    """songs.SAILOR_VARIANT = "b3d" (the owner's pick) or None: both builds equal proarr's (sailor_b3d / sailor_b3)."""
    assert songs.SAILOR_VARIANT == "b3d"
    assert songs.SAILOR_LASTCALL_SAFE, "the one effect row dropped so that the Last call's tempo stays within 18 lines (songs.py)"
    assert digest("sailor", songs.SONGS["sailor"]) == digest("sailor", sailor_variant("b3d")) != PROARR_DIGEST["sailor_b3d"]
    songs.SAILOR_LASTCALL_SAFE = False
    try:
        exact = digest("sailor", sailor_variant("b3d"))                 # proarr's b3d, to the byte
        full_fx = songs.sailor_arp()[1]
    finally:
        songs.SAILOR_LASTCALL_SAFE = True
    assert exact == PROARR_DIGEST["sailor_b3d"]
    assert set(full_fx) - set(songs.SONGS["sailor"]["fx_map"]) == {8 * 7 + 5, 8 * 15 + 5}, "only row 5 of bars 8 and 16 differs"
    assert digest("sailor", sailor_variant(None)) == PROARR_DIGEST["sailor_b3"]
    fx = songs.SONGS["sailor"]["fx_map"]
    assert {e for lst in fx.values() for _, e in lst} == {0x37, 0x58, 0x59}, "the arpeggios (hUGE 0xy) on the shouted held notes"
    assert all(r % 8 not in (0, 4) for r in fx), "each note's first row is plain: the flutter joins from its second row"


@pytest.mark.parametrize("name", ["clear", "over", "bonus"])
def test_the_jingles_are_proarrs(name):
    assert digest(name, gm.JINGLES[name], True) == PROARR_DIGEST[name]


def test_the_credits_are_proarrs_brass_lead_with_the_held_bass_and_the_one_line_fallback():
    t = songs.SONGS["credits"]
    assert songs.CREDITS_LEAD == songs.LEAD_PRO and t["inst"] == gm.LEAD_PRO
    assert digest("credits", t) == PROARR_DIGEST["credits"]
    assert digest("credits", dict(t, inst=1)) != PROARR_DIGEST["credits"], "the lead is in the digest: the one-line fallback (CREDITS_LEAD) changes the rows"
    b = gm.build("credits", t, False)
    assert {ins for chunk in b["per"][3] for note, ins, eff in chunk if note != gm.REST} == {gm.BASS_HELD}, "every bass note is the held one"
    assert t["fx_map"] == {574: [(3, 0xC05)], 576: [(3, 0xC02)]}


def test_the_arrangements_have_no_harmony_clash_and_the_basses_follow_the_chords():
    for n in ("MTN", "FUN", "SKT", "HALL", "SAK", "DAN", "WEA", "SAI"):
        assert getattr(songs, n + "_HARM_CHECK") == [], n
    for n in ("MTN", "SAK", "WEA", "SAI"):
        assert getattr(songs, n + "_BASS_CHECK") == ([], []), n
    # the anticipations are the specs' own leads (E into A, B into G x5, D into G)
    assert songs.FUN_BASS_CHECK == ([], ["bar 19: E3 (Dm) anticipates A7, then A2"])
    assert songs.SKT_BASS_CHECK[0] == [] and len(songs.SKT_BASS_CHECK[1]) == 5 and songs.DAN_BASS_CHECK == ([], ["bar 6: D3 (C) anticipates G7, then G2"])
    assert songs.HALL_BASS_ONSETS, "the Hall's bass moves on the melody's onsets (the theme in the bass)"
    # the Sakura bass stays on the scale (A B C D E F)
    pcs = {H.midi(tok.split(":")[0]) % 12 for tok in songs.SAK_BASS.split() if not tok.startswith("r")}
    assert pcs <= {H.midi(x + "4") % 12 for x in "ABCDEF"}, pcs
    for name, rows in (("mountain", 256), ("funicula", 150), ("skaters", 192), ("hall", 128), ("sailor", 128), ("sakura", 112), ("weasel", 96), ("danube", 192)):
        t = songs.SONGS[name]
        assert H.nrows(t["ch2"]) == H.nrows(t["ch3"]) == H.nrows(t["ch1"]) == rows, name


def test_the_grooves_and_the_fallbacks():
    g = {n: len(gm.groove_rows(n, songs.SONGS[n])) for n in ("funicula", "skaters", "danube", "sailor", "sakura", "ballgame")}
    assert g == {"funicula": 30, "skaters": 24, "danube": 24, "sailor": 32, "sakura": 16, "ballgame": 24}
    assert all(not songs.SONGS[n]["ch4"] for n in ("funicula", "skaters", "danube", "sailor", "sakura"))
    # the fallbacks (a shorter groove: less of bank 2) keep the song a whole number of grooves
    for name, alt in (("funicula", songs.FUN_GROOVE_1BAR), ("danube", songs.DAN_GROOVE_1BAR), ("sailor", songs.SAI_GROOVE_2BAR)):
        t = dict(songs.SONGS[name], groove=alt)
        assert gm.build(name, t, False)["total"] % len(gm.groove_rows(name, t)) == 0
    # the drum patterns: one pattern a tune (Mountain: the 4-bar fill in every order; Hall: 8 bars twice; the zoo 16 bars of its own)
    assert len({k for k in gm.build("mountain", songs.SONGS["mountain"], False)["per"][4]}) == 1
    assert len({k for k in gm.build("hall", songs.SONGS["hall"], False)["per"][4]}) == 1


def test_the_rom_has_the_harmony_in_bank_24_the_blobs_in_10_and_sakura_runs_1344_frames():
    data = (BUILD / "music_data.c").read_text()
    assert gm.HARM_BANK == 24 and re.search(r"#define HARM_BANK 24\b", (ROOT / "src" / "music.h").read_text())
    for name in ("mountain", "funicula", "skaters", "hall", "sailor", "sakura", "danube", "weasel"):
        t = songs.SONGS[name]
        tune = f"venue{GROUP[name]}"
        b = gm.build(name, t, False)
        h = bytes(gm.harm_bytes(t, gm.harm_events(name, t, b["total"]), t.get("start", 0)))   # (the pickup tune Mountain: its track is stored from row 248 on)
        assert rom_bank(f"harm_{tune}") == 24 and rom_bytes(f"harm_{tune}", len(h)) == h, name
        assert rom_bank(f"blob_{tune}") == 10, name
        pats = []
        for c in (1, 2, 3, 4):
            for k in b["per"][c]:
                if k != gm.EMPTY and k not in pats:
                    pats.append(k)
        assert rom_bytes(f"blob_{tune}", len(pats) * gm.SLOT_BYTES) == b"".join(dn(k) for k in pats), name
    # the Sumo and Taiko Pour count the Sakura tune's pass: 14 bars of 8 rows at 12 frames
    assert re.search(r"\{&song_venue7, 1, 1344, ", data)
    assert gm.pass_frames(112, 12) == 1344


@pytest.mark.only_model('dmg')
@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("group", [2, 3, 4, 5, 6, 7, 8, 9])
def test_the_pause_mix_of_each_new_venue_tune_is_bass_and_drums(model, group):
    """src/pause.c: NR51 0xCC (0x44 while an effect holds channel 4) set by music_tick while TMA bit 1 is on: bass (3) and drums (4) only."""
    with make_rom(model) as gb:
        gb.run(120)
        start_game(gb)
        if group:
            goto_group(gb, group)
        gb.write("intro_timer", 255)
        assert gb.mem("cur_tune") == TUNE_VENUE0 + group
        gb.run(60)
        nr51, noise, wave = set(), set(), set()
        for _ in range(240):
            gb.write(0xFF06, gb.mem(0xFF06) | 2)
            gb.run(1)
            nr51.add(gb.mem(0xFF25))
            noise.add(gb.mem(0xFF22))
            wave.add(gb.mem(0xFF1C))
        assert nr51 <= {0xCC, 0x44} and 0xCC in nr51, (songs.VENUES[group], nr51)
        assert len(noise) > 1, f"{songs.VENUES[group]}: the drums play in the pause mix"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_sailor_plays_at_the_last_calls_tempo_and_the_groove_keeps_in_step(model):
    """music_fast (the Last call): one frame a row less (8), a pass of 128 rows is 1024 frames, and every kick of the 32-row groove starts on a row's first frame (40 a pass)."""
    with make_rom(model) as gb:
        gb.run(120)
        start_game(gb)
        goto_group(gb, 6)
        gb.write("intro_timer", 255)
        gb.write("music_fast", 1)
        gb.run(1)
        goto_group(gb, 6)                  # (the level's music_play restarts the tune: a speed change restarts it)
        gb.write("intro_timer", 255)
        gb.write("music_fast", 1)
        for _ in range(200):               # the restart: the preload, then the song
            gb.run(1)
            if gb.mem("music_frames") < 4 and gb.mem("cur_tune") == TUNE_VENUE0 + 6:
                break
        gb.write("music_fast", 1)
        assert gb.mem("cur_tune") == TUNE_VENUE0 + 6
        kicks, row_starts, prev_row, prev_nr43, rows_seen = [], set(), None, None, []
        order_starts = []
        for f in range(1024 * 2 + 40):
            row = (gb.mem("hUGE_current_order"), gb.mem("hUGE_row"))
            gb.run(1)
            now = (gb.mem("hUGE_current_order"), gb.mem("hUGE_row"))
            nr43 = gb.mem(0xFF22)
            if now != row:
                row_starts.add(f)
                if now == (0, 0):
                    order_starts.append(f)
            if nr43 == 0x37 and prev_nr43 != 0x37:
                kicks.append(f)
            prev_nr43 = nr43
        # (the driver's row counter moves the frame after the row's notes play: a hit is one frame from a row change, always the same way)
        assert {min(abs(f - r) for r in row_starts) for f in kicks} == {1}, "every groove hit is on a row start"
        assert 2 * 40 - 4 <= len(kicks) <= 2 * 40 + 4, len(kicks)         # (10 kicks in each of the 4 32-row grooves of a pass, 2 passes)
        assert len(order_starts) >= 2 and order_starts[1] - order_starts[0] in (128 * 8, 128 * 8 + 1), order_starts


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_credits_bass_is_held_and_the_ending_fades_100_50_25(model):
    """The held bass keeps NR32 at 100 % (0x20) through the tune; at rows 574 and 576 the last chord steps to 50 % (0x40) and 25 % (0x60); the tune ends."""
    t = songs.SONGS["credits"]
    start, cur = [0], 15
    for r in range(579):
        cur = t["tempo_map"].get(r, cur)
        start.append(start[-1] + cur)
    with make_rom(model) as gb:         # (sound emulated: the APU registers are only live then)
        gb.run(120)
        hold_stage_anim(gb)
        title_pick(gb, K_BONUS, K_CREDITS)
        run_until(gb, lambda: gb.mem("story_phase") == SP_CREDITS, 20)
        gb.run(2)
        assert gb.mem("cur_tune") == 15
        raw, frames = [], 0
        c0 = gb.pb._cycles()
        while gb.mem("cur_tune") == 15 and frames < 9100:
            raw.append((gb.mem(0xFF1C) & 0x60, frames))           # (NR32 bits 5-6: the wave channel's output level, 1 = 100 %, 2 = 50 %, 3 = 25 %)
            gb.run(1)
            frames = int((gb.pb._cycles() - c0) / 70224)
        seq = []                                                   # runs of at least 3 frames (a roll's fade can blank the register for one)
        for i, (v, f) in enumerate(raw):
            if f > 300 and (not seq or seq[-1][0] != v) and all(w == v for w, _ in raw[i:i + 3]):
                seq.append((v, f))
        vols = [v for v, _ in seq]
        assert vols[0] == 0x20 and 0x40 in vols and 0x60 in vols and vols.index(0x40) < vols.index(0x60), seq
        assert set(vols[:vols.index(0x40)]) <= {0x20, 0x00} and 0x40 not in vols[:vols.index(0x40)], "100 % (the held bass) all the way to the last chord"
        assert not any(v in (0x40, 0x60) for v, f in seq if f < start[574] - 6), "no pluck steps before the last chord"
        steps = {v: f for v, f in seq}
        assert abs(steps[0x40] - start[574]) <= 6 and abs(steps[0x60] - start[576]) <= 6, (seq, start[574], start[576])
