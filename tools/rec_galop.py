#!/usr/bin/env python3
"""Record the show tune (Galop infernal) as the game plays it: the full mix, the pause mix and per-channel stems.

    python3 tools/rec_galop.py OUTDIR [--model dmg|cgb] [--compare AUDITION_DIR] [--loops 2]

Boots build/game.gb with PyBoy's sound emulation, starts a level, triggers a show (a tip) and records `loops` passes of the show tune
(704 frames each) from its first tick.  Files in OUTDIR, each with a _24k copy (sample pairs averaged):
  galop_ingame_full.wav       every channel
  galop_ingame_pausemix.wav   the game's real pause menu open over the show (src/pause.c: NR51 0xCC, bass + drums)
  galop_ingame_chN_<label>.wav  one channel alone (NR51 poked to 0x11 / 0x22 / 0x44 / 0x88 each frame, as the audition's stems)
PyBoy's sound buffer is sliced by raw_buffer_head // 2 per frame (the whole array has a stale row that crackles at 60 Hz).
Gain 800 (the audition WAVs' gain, so levels compare).  --compare AUDITION_DIR lines each recording up against
improved_v2_galop_full.wav / improved_v2_galop_pausemix.wav there (the audition's pause mix was NR51 0x55: bass + counter-melody)
and prints a short-time spectrum match (see tools/rec_credits.py compare()).
"""
import argparse
import sys
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "tools"))
GAIN = 800
FRAMES = 704
TUNE_SHOW = 4
NR51 = 0xFF25
STEMS = ((1, 0x11, "harmony_countermelody"), (2, 0x22, "lead_melody"), (3, 0x44, "bass_wave"), (4, 0x88, "drums_noise"))


def start_show(model):
    from test_pause import rom_s
    from test_sound import start_a_show, start_game, w16
    gb = rom_s(model)
    start_game(gb)
    gb.run(400)                                   # (the show tune is copied to WRAM in the background)
    start_a_show(gb)
    assert gb.mem("cur_tune") == TUNE_SHOW
    w16(gb, "show_timer", 60000)                  # the show goes on while we record
    return gb


def record(model, loops, mode):
    """mode: 'full', 'pause' or an NR51 mask (a stem).  Returns (int16 stereo, rate)."""
    gb = start_show(model)
    pb = gb.pb
    if mode == "pause":
        gb.press("start", 2)
        gb.run(3)
        assert gb.mem("game_state") == 5, "paused"
        assert gb.mem(NR51) == 0xCC
    chunks, n = [], FRAMES * loops
    first = None
    for f in range(n + 700):
        if isinstance(mode, int):
            pb.memory[NR51] = mode
        pb.tick(1, False, True)
        chunks.append(pb.sound.ndarray[:pb.sound.raw_buffer_head // 2].copy())
        if mode == "pause":
            assert pb.memory[NR51] == 0xCC
        if first is None and mode != "pause" and gb.mem16("music_frames") > 0:
            first = len(chunks) - 1
        if first is not None and len(chunks) - first >= n:
            break
        if mode == "pause" and len(chunks) >= n:
            break
    rate = pb.sound.sample_rate
    gb.stop()
    raw = np.concatenate(chunks[first or 0:]).astype(np.int32)
    return np.clip(raw * GAIN, -32768, 32767).astype("<i2"), rate


def write(path, s, rate):
    for p, r, a in ((path, rate, s), (path.with_name(path.stem + "_24k.wav"), rate // 2, None)):
        if a is None:
            n2 = len(s) // 2 * 2
            a = s[:n2].reshape(-1, 2, 2).astype(np.int32).mean(axis=1).astype("<i2")
        with wave.open(str(p), "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(r)
            w.writeframes(a.tobytes())


def load(path):
    with wave.open(str(path), "rb") as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").reshape(-1, 2), w.getframerate()


def main():
    from rec_credits import compare
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--model", default="dmg", choices=("dmg", "cgb"))
    ap.add_argument("--loops", type=int, default=2)
    ap.add_argument("--compare")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    recs = {}
    for name, mode in (("full", "full"), ("pausemix", "pause")):
        s, rate = record(args.model, args.loops, mode)
        write(out / f"galop_ingame_{name}.wav", s, rate)
        recs[name] = s
        print(f"galop_ingame_{name}.wav {len(s) / rate:.1f} s peak {int(np.abs(s).max())} rms {float(np.sqrt((s.astype(float) ** 2).mean())):.0f}")
    for ch, mask, label in STEMS:
        s, rate = record(args.model, args.loops, mask)
        write(out / f"galop_ingame_ch{ch}_{label}.wav", s, rate)
        print(f"galop_ingame_ch{ch}_{label}.wav {len(s) / rate:.1f} s peak {int(np.abs(s).max())}")
    if args.compare:
        d = Path(args.compare)
        for name, aud in (("full", "improved_v2_galop_full.wav"), ("pausemix", "improved_v2_galop_pausemix.wav")):
            b, brate = load(d / aud)
            print(f"-- {name} against {aud}")
            compare(recs[name], b, rate, FRAMES * args.loops / 59.7275)


if __name__ == "__main__":
    main()
