# Seamless loops: every looping tune flows from its last bar back into bar 1 without a hole in the melody.
# Computed from the generated song rows (tools/gen_music.py, the same rows the ROM plays) and the melody instrument's
# volume envelope, so it needs no emulator.  A melody note "sounds" from its row until the first of: its note cut
# (the Exx effect gen_music writes for staccato notes and before rests / repeated notes), the next note, or its
# envelope falling below half its starting volume (the pulse channel's hardware envelope: one step every
# period/64 s).  A long held note on the song lead (NR12 0x85) is down to half volume after 0.39 s, so a last
# note held for a bar and more leaves an audible hole before bar 1 even when no rest is written.
import sys

import pytest
from conftest import ROOT

sys.path.insert(0, str(ROOT / "tools"))
import gen_music as gm       # noqa: E402
import songs                 # noqa: E402

MAX_LOOP_SILENCE = 0.25      # seconds of melody silence allowed where the tune wraps to bar 1
FPS = 59.7275                # DMG/CGB frame rate (the driver ticks once a frame)


def audible_frames(env):
    """Frames until a pulse note with envelope register `env` (NR12) falls below half its starting volume
    (None: it never does: a rising or constant envelope)."""
    v0, down, period = env >> 4, not (env & 8), env & 7
    if not down or period == 0 or v0 == 0:
        return None
    steps = v0 - (v0 + 1) // 2 + 1                  # volume v0 - steps < ceil(v0 / 2)
    return steps * period * FPS / 64


def melody_spans(rows, tempo):
    """[(start frame, end frame)] of each melody note over one pass (end may run past the pass: the note carries
    over the wrap until the next note starts)."""
    n_frames = len(rows) * tempo
    starts = [r for r, (note, inst, eff) in enumerate(rows) if note != gm.REST]
    spans = []
    for k, r in enumerate(starts):
        note, inst, eff = rows[r]
        start = r * tempo
        nxt = starts[k + 1] * tempo if k + 1 < len(starts) else n_frames + starts[0] * tempo
        end = nxt
        for rr in range(r, (nxt + tempo - 1) // tempo):       # the first note cut in this note's rows
            e = rows[rr % len(rows)][2]
            if (e & 0xF00) == 0xE00 and rr * tempo + (e & 0xFF) > start:
                end = min(end, rr * tempo + (e & 0xFF))
                break
        fade = audible_frames(gm.DUTY[inst - 1][2])
        if fade is not None:
            end = min(end, start + fade)
        spans.append((start, end))
    return spans, n_frames


def played_rows(b, channel=2, short=()):
    """The rows a pass plays: the short orders (the streamed title's intro and bridge: 32 rows, then rests behind a pattern break) lose their
    unplayed half."""
    rows = [row for chunk in b["per"][channel] for row in chunk]
    for o in sorted(short, reverse=True):
        del rows[o * 64 + 32:(o + 1) * 64]
    return rows[:b["total"]]


def loop_silence(name, t, legacy):
    """Seconds of melody silence across the wrap from the last row back to row 0."""
    b = gm.build(name, t, legacy)
    rows = played_rows(b, 2, t.get("short_orders") or ())
    spans, n = melody_spans(rows, b["tempo"])
    last_end = max(e for s, e in spans)
    first = spans[0][0] + n
    return max(0.0, first - last_end) / FPS


def looping_tunes():
    out = [(n, songs.SONGS[n], False) for n in songs.SONGS if n != gm.CREDITS]      # (the credits tune plays once)
    out += [(n, t, True) for n, t in gm.JINGLES.items() if t["loop"]]
    return out


@pytest.mark.parametrize("name,t,legacy", looping_tunes(), ids=[n for n, _, _ in looping_tunes()])
def test_every_looping_tune_flows_back_into_bar_1(name, t, legacy):
    s = loop_silence(name, t, legacy)
    # the Sailor's arpeggio variant (owner-picked 2026-10-17) plays the last bar's two long notes on the decaying lead: a heuristic 0.37 s
    limit = 0.4 if name == "sailor" and songs.SAILOR_VARIANT == "b3d" else MAX_LOOP_SILENCE
    # Swipesy (the story map's tune, owner-approved as it stands): the score's last bar ends on a held note and a two-row rest (0.37 s at 11 frames a row), and bar 1 starts on the
    # same note: the rest is the piece's own, the owner heard it in both passes of the audition
    # The Easy Winners' fast draft (the soundtrack's bonus track, the audition as it was heard): the same, 0.33 s (a two-row rest at 9 frames, swung)
    if name in ("swipesy", "ewfast"):
        limit = 0.4
    assert s <= limit, f"{name}: {s:.2f} s of melody silence before the loop returns to bar 1"


def test_the_silence_measure_sees_a_held_last_note_and_a_trailing_rest():
    lead = {"tempo": 10, "ch2": "C5:2 D5:2 E5:16", "ch3": "C3:20", "ch4": "", "inst": gm.LEAD_PRO, "gap": True, "stac_all": None}
    # E5 starts at frame 40 and is below half volume 6 steps x 5/64 s later (28.1 frames: the brass lead, volume 10); the pass is 200 frames
    assert loop_silence("t", lead, False) == pytest.approx((200 - 40 - 6 * 5 * FPS / 64) / FPS, abs=0.01)
    rest = dict(lead, ch2="C5:2 D5:2 E5:2 r:14")
    assert loop_silence("t", rest, False) > 2
    tight = dict(lead, ch2="C5:2 D5:2 E5:14 G4:2")
    assert loop_silence("t", tight, False) < MAX_LOOP_SILENCE
    assert gm.JINGLES["bonus"]["loop"] and not gm.JINGLES["clear"]["loop"], "only the bonus jingle loops"


# ---- the pattern break that ends a tune whose length is not a whole number of 64-row patterns ----------------------
# hUGEDriver keeps the break row plus one (row_break 0 = no break), so the generator writes D01 for "next order, row 0".
# With D00 nothing happened: Oh! Susanna (96 rows) ran 32 empty rows (8 s of dead air) before its loop, and Funiculi,
# Sakura, Pop Goes the Weasel and the bonus jingle had their own silent tails.
def built_tunes():
    out = [(n, gm.build(n, songs.SONGS[n], False)) for n in songs.SONGS]
    out += [(n, gm.build(n, t, True)) for n, t in gm.JINGLES.items()]
    return out


def test_a_tune_ending_inside_a_pattern_breaks_to_row_0_of_the_next_order():
    short = 0
    for name, b in built_tunes():
        last = b["total"] - 1 + 32 * len(songs.SONGS[name].get("short_orders", ()) if name in songs.SONGS else ())
        o, r = divmod(last, 64)
        effs = [b["per"][c][o][r][2] for c in (1, 2, 3, 4)]
        if last % 64 != 63:
            short += 1
            assert gm.BREAK_TO_ROW0 in effs, f"{name}: no pattern break on its last row"
        assert 0xD00 not in effs, f"{name}: D00 does not break in hUGEDriver"
        breaks = [(c, i, j) for c in (1, 2, 3, 4) for i, chunk in enumerate(b["per"][c]) for j, row in enumerate(chunk)
                  if (row[2] & 0xF00) == 0xD00]
        shorts = songs.SONGS[name].get("short_orders", ()) if name in songs.SONGS else ()     # (the title's intro and bridge break after 32 rows)
        assert len(breaks) <= 1 + len(shorts), f"{name}: {breaks}"
        assert {(i, j) for c, i, j in breaks if (i, j) != (o, r)} == {(i, 31) for i in shorts}, f"{name}: {breaks}"
    assert short >= 4, "funicula, sakura, weasel and the jingles end inside a pattern"


def test_pop_goes_the_weasel_wraps_to_bar_1_without_the_empty_rows(gb):
    """In the ROM: the zoo tune (96 rows = 1.5 orders) plays order 1 (hUGE_current_order 2) for 32 rows only, then
    order 0 from row 0 again.  (This watched Oh! Susanna until music step 3: at sixteenth rows it is 192 rows, three
    whole orders, and no longer ends inside a pattern.)"""
    from test_art import goto_group
    goto_group(gb, 8)
    assert gb.mem("cur_tune") == 5 + 8 and songs.VENUES[8] == "weasel", "the zoo's tune (TUNE_VENUE0 + 8)"
    t = songs.SONGS["weasel"]["tempo"]
    seen = []
    for _ in range(96 * t + 3 * t):
        gb.write("intro_timer", 255)                  # no patrons: the level lasts as long as the tune is watched
        gb.run(1)
        seen.append((gb.mem("hUGE_current_order"), gb.mem("hUGE_row")))
    in_last = [r for o, r in seen if o == 2]
    assert in_last and max(in_last) == 31, f"order 1 ran to row {max(in_last) if in_last else None}"
    i = max(k for k, (o, r) in enumerate(seen) if o == 2)
    assert seen[i + 1] == (0, 0), f"after the last row: {seen[i + 1]}"


@pytest.mark.only_model('dmg')
def test_oh_susanna_plays_its_three_orders_and_wraps_to_bar_1(gb):
    """In the ROM: the saloon tune (192 sixteenth rows = three whole orders) runs order 2 (hUGE_current_order 4) to row
    63, then order 0 from row 0 again."""
    assert gb.mem("cur_tune") == 5, "the saloon's tune (TUNE_VENUE0)"
    t = songs.SONGS["susanna"]["tempo"]
    seen = []
    for _ in range(192 * t + 3 * t):
        gb.write("intro_timer", 255)
        gb.run(1)
        seen.append((gb.mem("hUGE_current_order"), gb.mem("hUGE_row")))
    in_last = [r for o, r in seen if o == 4]
    assert in_last and max(in_last) == 63, f"order 2 ran to row {max(in_last) if in_last else None}"
    i = max(k for k, (o, r) in enumerate(seen) if o == 4)
    assert seen[i + 1] == (0, 0), f"after the last row: {seen[i + 1]}"
