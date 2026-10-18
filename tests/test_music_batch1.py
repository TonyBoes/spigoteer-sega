# Music batch 1 and the whole-Entertainer title (owner-approved 2026-10-17; docs/proarr/BATCH_1.md, BATCH_TITLE_FULL.md and specs/title_full.md on
# branch promusic): the title, Oh! Susanna and Take Me Out to the Ball Game are the pro arrangements; the title is the full 173 s looping piece,
# streamed through buffer A like the credits tune.  The generated notes equal tools/proarr.py's (promusic), pinned by digest below.
import hashlib
import json
import re
import sys

import pytest
from conftest import ROM, ROOT
from gbtools import Rom
from test_credits import dn, rom_bank, rom_bytes
from test_music_loops import played_rows
from test_sound import TUNE_VENUE0, make_rom

sys.path.insert(0, str(ROOT / "tools"))
import gen_music as gm       # noqa: E402
import harmony as H          # noqa: E402
import songs                 # noqa: E402

BUILD = ROOT / "build"
ORDER_BYTES = 2 * gm.SLOT_BYTES
ORDERS = 20
FRAMES = 10336               # 1216 rows: 608 of 9 frames and 608 of 8 (swing 0xAA): 173 s

# sha256 of {rows (channels 2, 3, 4 per order, every instrument resolved to its definition), harmony bytes, groove letters} as proarr.py
# (promusic, TITLE_B2_8VA=1) built them: gen_music's output for the same tune must be the same notes (tools/music_rig.py dumps are in the commit message)
PROARR_DIGEST = {
    "susanna": "a00922535b9bc85bddfc06ba4f6d8aea0665829a8ea6b0a996cba66c0fd7e06b",
    "ballgame": "945c3f26d1ab7fd8060bdec3d399eb41adbefaf39f5ad9d5bc44b31817ce0c87",
    "title": "84f7cd65de486d9bfd5ff97a7c43e1f84d43f9fa1e05e2ebcda7b7431948fee8",
}


def definition(c, inst):
    if inst == 0:
        return None
    ins = list(({2: gm.DUTY, 3: gm.WAVE, 4: gm.NOISE}[c])[inst - 1])
    if c == 3:
        ins[2] = gm.WAVES[ins[2]]       # (the wave itself: proarr numbered its waveforms differently)
    return json.dumps([("DUTY", "WAVE", "NOISE")[c - 2], ins])


def digest(name, source):
    t = songs.SONGS[source]
    b = gm.build(source, t, False)
    chans = (2, 3, 4) if name != "title" else (2, 3)
    rows = {c: [[(None if n == gm.REST else n, definition(c, i), e) for n, i, e in chunk] for chunk in b["per"][c]] for c in chans}
    letters = {v: k for k, v in gm.DRUM_ID.items()}
    d = {"rows": rows, "harm": gm.harm_bytes(t, gm.harm_events(source, t, b["total"])),
         "groove": [letters.get(x) if x else None for x in gm.groove_rows(source, t) or []]}
    return hashlib.sha256(json.dumps(json.loads(json.dumps(d)), sort_keys=True).encode()).hexdigest()


@pytest.mark.parametrize("name,source", [("susanna", "susanna"), ("ballgame", "ballgame"), ("title", "entertainer")])
def test_the_generated_notes_are_proarrs(name, source):
    assert digest(name, source) == PROARR_DIGEST[name]


def test_the_arrangements_have_no_harmony_clash_and_the_basses_follow_the_chords():
    assert not songs.SUS_HARM_CHECK and not songs.TMO_HARM_CHECK
    assert all(not p for p in songs.ENT_HARM_CHECK.values()) and set(songs.ENT_HARM_CHECK) == set(songs.ENT_SECTIONS)
    probs, antic = songs.ENT_BASS_CHECK
    # the intro's run is the left hand doubling the melody in octaves (6 notes outside G7 that do not step, on purpose); the 4 anticipations
    # are the spec's own leads (the trio's B into E7, the D strain's D into G7)
    assert len(probs) == 6 and all(int(re.search(r"row (\d+)", p).group(1)) < 24 for p in probs), probs
    assert len(antic) == 4, antic
    for name, rows in (("entertainer", 8 * 152), ("susanna", 192), ("ballgame", 192)):
        t = songs.SONGS[name]
        assert H.nrows(t["ch2"]) == H.nrows(t["ch3"]) == H.nrows(t["ch1"]) == rows


def test_the_title_is_the_whole_entertainer_in_20_streamed_orders():
    t = songs.SONGS["entertainer"]
    b = gm.build("title", t, False)
    assert (b["total"], b["n_orders"], b["tempo"], t["swing"]) == (1216, ORDERS, 9, 0xAA)
    assert gm.pass_frames(b["total"], 9, 0xAA) == FRAMES and t["short_orders"] == (0, 15)
    assert all(k == gm.EMPTY for c in (1, 4) for k in b["per"][c]) and not t["ch4"]
    # the intro (order 0) and the bridge (order 15) play 32 rows: a pattern break on row 31 (melody channel), rests behind it
    for o in (0, 15):
        assert b["per"][2][o][31][2] == gm.BREAK_TO_ROW0 and all(r == (gm.REST, 0, 0) for c in (2, 3) for r in b["per"][c][o][32:])
    assert sum(1 for c in (2, 3) for ch in b["per"][c] for r in ch if (r[2] & 0xF00) == 0xD00) == 2
    # order 16 starts the D strain on its F4; the loop wraps from order 19 to the intro's D5
    assert b["per"][2][16][0][0] == gm.note_no("F4") and b["per"][2][0][0][0] == gm.note_no("D5")
    # played rows: the sections add up to the spec's 152 bars
    assert sum(x["rows"] for x in songs.ENT_SECS) == 1216 and [x["rows"] // 8 for x in songs.ENT_SECS] == [4, 16, 16, 16, 16, 16, 16, 16, 4, 16, 16]
    assert len(played_rows(b, 2, t["short_orders"])) == 1216
    # the groove: 38 four-bar grooves a pass, the fill (snare and open hat) on the last bar of each
    g = gm.groove_rows("title", t)
    assert len(g) == 32 and 1216 % 32 == 0 and g[-1] == gm.DRUM_ID["o"] and g[-2] == gm.DRUM_ID["n"] and g[-4] == gm.DRUM_ID["n"]
    assert 1216 // 32 == 38
    # B2 is an octave above B1 (Joplin's 8va); the trio is in F (B-flat chords), the D strain starts on F4
    secs = {x["name"]: x for x in songs.ENT_SECS}
    assert secs["B2"]["mel"].startswith(H.transpose(" ".join(songs.ENT_BARS[16:31]), 1)) and secs["B1"]["mel"].startswith(" ".join(songs.ENT_BARS[16:31]))
    assert "Bb" in secs["C1"]["chords"] and secs["C1"]["key"] == secs["C2"]["key"] == "F"


def test_the_title_blob_and_harmony_are_in_bank_23_and_the_jingles_left_bank_2():
    data = (BUILD / "music_data.c").read_text()
    assert f"{{&song_title, 1, {FRAMES}, 3, 23, blob_title, 1536, groove_title, 0}}" in data, "looping, streamed (buf 3), bank 23, 4 orders first, a groove"
    assert "title_order_cnt = 40;" in data
    for c in (2, 3):
        want = ", ".join(f"&mus_buf_a[{((o & 3) * 2 + c - 2) * gm.SLOT_BYTES}]" for o in range(ORDERS))
        assert f"title_order{c}[] = {{{want}}}" in data
    for c in (1, 4):
        assert f"title_order{c}[] = {{{', '.join(['empty_pat'] * ORDERS)}}}" in data
    b = gm.build("title", songs.SONGS["entertainer"], False)
    blob = b"".join(dn(b["per"][c][o]) for o in range(ORDERS) for c in (2, 3))
    assert len(blob) == ORDERS * ORDER_BYTES == 7680
    assert rom_bank("blob_title") == rom_bank("harm_title") == gm.TITLE_BANK == 23
    assert rom_bytes("blob_title", len(blob)) == blob
    h = bytes(gm.harm_bytes(songs.SONGS["entertainer"], gm.harm_events("title", songs.SONGS["entertainer"], 1216)))
    assert len(h) == 1644
    assert rom_bytes("harm_title", len(h)) == h
    # the jingles' patterns: bank 24, copied to buffer A (buf 1) when they start
    for name, n, frames, loop in (("clear", 3, 112, 0), ("over", 3, 252, 0), ("bonus", 4, 240, 1)):
        assert f"{{&song_{name}, {loop}, {frames}, 1, 24, blob_{name}, {n * gm.SLOT_BYTES}, " in data, name
        assert rom_bank(f"blob_{name}") == gm.JINGLE_BANK == 24
    assert "_p0[]" not in data, "no jingle pattern is left in bank 2"
    # the other tunes' harmony stays in bank 10; the ROM's streaming constants are the generator's
    assert rom_bank("harm_venue0") == rom_bank("harm_show") == 10
    h_ = (ROOT / "src" / "music.h").read_text()
    assert "#define STREAM_TICK        3" in h_ and "#define STREAM_COPY_ROWS   8" in h_
    music_c = (ROOT / "src" / "music.c").read_text()
    assert "hUGE_tick == STREAM_TICK" in music_c and "hUGE_tick == 1" not in music_c, "the copy rides on tick 3, not the row tick's own call"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_title_streams_and_loops_the_buffer_holds_the_blob_at_every_order_over_two_passes(model):
    b = gm.build("title", songs.SONGS["entertainer"], False)
    blob = b"".join(dn(b["per"][c][o]) for o in range(ORDERS) for c in (2, 3))
    order = lambda j: blob[(j % ORDERS) * ORDER_BYTES:(j % ORDERS + 1) * ORDER_BYTES]
    with Rom(ROM, model) as gb:
        gb.run(120)
        buf = gb.addr("mus_buf_a")

        def slot_is(j):
            return bytes(gb.read(buf + (j & 3) * ORDER_BYTES, ORDER_BYTES)) == order(j)

        assert gb.mem("cur_tune") == 0 and gb.mem("sound_on") == 1
        starts, done, checks, frames, seen = [], set(), 0, 0, []
        while frames < 2 * FRAMES + 400:
            o, row = gb.mem("hUGE_current_order") // 2, gb.mem("hUGE_row")
            assert gb.mem("cur_tune") == 0, f"the title stopped or changed at frame {frames}"
            if not starts or starts[-1] != o:
                starts.append(o)
                assert all(slot_is(j) for j in (o, o + 1)), f"order {o} (start {len(starts)}): it and the next are in the buffer"
                if len(starts) > 1:
                    assert slot_is(o - 1) if o else slot_is(ORDERS - 1), f"order {o}: the order just played is intact"
                checks += 1
            if row == 12 and (len(starts), o) not in done:       # the copy of order o + 2 (rows 2-9) is finished
                done.add((len(starts), o))
                assert all(slot_is(j) for j in range(o - 1 if len(starts) > 1 else 0, o + 3)), f"during order {o} (start {len(starts)}): orders {o - 1}..{o + 2}"
                checks += 1
            gb.run(1)
            frames += 1
        wrapped = [i for i, (a, c) in enumerate(zip(starts, starts[1:])) if c < a]
        assert starts[:ORDERS] == list(range(ORDERS)) and starts[ORDERS:2 * ORDERS] == list(range(ORDERS)), starts
        assert len(wrapped) >= 2 and checks >= 4 * ORDERS, (wrapped, checks)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_pause_mix_of_the_title_is_bass_and_drums_and_the_stream_goes_on(model):
    """The pause menu's mix (src/pause.c: NR51 0xCC, set by music_tick while TMA bit 1 is on) over the title: bass and drums, the intro's
    run in octaves over the kit, the walking bass after it; the streaming copy is unaffected (the buffer still holds the next orders)."""
    b = gm.build("title", songs.SONGS["entertainer"], False)
    blob = b"".join(dn(b["per"][c][o]) for o in range(ORDERS) for c in (2, 3))
    with make_rom(model) as gb:
        gb.run(120)
        assert gb.mem("cur_tune") == 0
        a = 0xFF06                                           # TMA
        nr51, wave_writes, noise, last = set(), 0, set(), None
        for f in range(700):                                 # the intro and a bar and a half of A
            gb.write(a, gb.mem(a) | 2)
            gb.run(1)
            nr51.add(gb.mem(0xFF25))
            noise.add(gb.mem(0xFF22))
            note = gb.mem(0xFF1C)                           # NR32: the bass's pluck steps its volume 100 / 50 / 25 % / off on every note
            wave_writes += note != last
            last = note
        assert nr51 <= {0xCC, 0x44}, nr51
        assert wave_writes > 30 and {0x37, 0x57, 0x77} <= noise, (wave_writes, noise)
        o = gb.mem("hUGE_current_order") // 2
        buf = gb.addr("mus_buf_a")
        for j in (o, o + 1):
            assert bytes(gb.read(buf + (j & 3) * ORDER_BYTES, ORDER_BYTES)) == blob[j * ORDER_BYTES:(j + 1) * ORDER_BYTES]
