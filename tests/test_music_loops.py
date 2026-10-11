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


def loop_silence(name, t, legacy):
    """Seconds of melody silence across the wrap from the last row back to row 0."""
    b = gm.build(name, t, legacy)
    rows = [row for chunk in b["per"][2] for row in chunk][:b["total"]]
    spans, n = melody_spans(rows, b["tempo"])
    last_end = max(e for s, e in spans)
    first = spans[0][0] + n
    return max(0.0, first - last_end) / FPS


def looping_tunes():
    out = [(n, songs.SONGS[n], False) for n in songs.SONGS]
    out += [(n, t, True) for n, t in gm.JINGLES.items() if t["loop"]]
    return out


@pytest.mark.parametrize("name,t,legacy", looping_tunes(), ids=[n for n, _, _ in looping_tunes()])
def test_every_looping_tune_flows_back_into_bar_1(name, t, legacy):
    s = loop_silence(name, t, legacy)
    assert s <= MAX_LOOP_SILENCE, f"{name}: {s:.2f} s of melody silence before the loop returns to bar 1"


def test_the_silence_measure_sees_a_held_last_note_and_a_trailing_rest():
    lead = {"tempo": 10, "ch2": "C5:2 D5:2 E5:16", "ch3": "C3:20", "ch4": "", "inst": 5, "gap": True, "stac_all": None}
    # E5 starts at frame 40 and is below half volume 5 steps x 5/64 s later (23.3 frames); the pass is 200 frames
    assert loop_silence("t", lead, False) == pytest.approx((200 - 40 - 5 * 5 * FPS / 64) / FPS, abs=0.01)
    rest = dict(lead, ch2="C5:2 D5:2 E5:2 r:14")
    assert loop_silence("t", rest, False) > 2
    tight = dict(lead, ch2="C5:2 D5:2 E5:14 G4:2")
    assert loop_silence("t", tight, False) < MAX_LOOP_SILENCE
    assert gm.JINGLES["bonus"]["loop"] and not gm.JINGLES["clear"]["loop"], "only the bonus jingle loops"
