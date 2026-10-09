#!/usr/bin/env python3
"""Render a ROM's audio to a WAV with PyBoy's sound emulation and print the strongest pitch per window.

    dump_audio.py build/game.gb out/audio/title.wav --frames 600
    dump_audio.py build/game.gb out/audio/game.wav --frames 900 --press start:2 --skip 120

Pitch tracking is a plain FFT peak: a sanity check of the song data (are the notes where they
should be), not a substitute for listening.
"""
import argparse
import wave
from pathlib import Path

import numpy as np
from pyboy import PyBoy


def capture(rom, frames, presses, skip, model="dmg"):
    pb = PyBoy(str(rom), window="null", sound_emulated=True, cgb=(model == "cgb"), log_level="ERROR")
    pb.set_emulation_speed(0)
    chunks = []
    pb.tick(skip, False, True)
    for name, n in presses:
        pb.button_press(name)
        pb.tick(n, False, True)
        pb.button_release(name)
    for _ in range(frames):
        pb.tick(1, False, True)
        chunks.append(pb.sound.ndarray.copy())
    rate = pb.sound.sample_rate
    pb.stop(save=False)
    return np.concatenate(chunks), rate


def peaks(samples, rate, window=0.25):
    mono = samples.astype(float).mean(axis=1)
    n = int(rate * window)
    out = []
    for i in range(0, len(mono) - n, n):
        seg = mono[i:i + n] - mono[i:i + n].mean()
        if np.abs(seg).max() < 2:
            out.append((i / rate, 0.0))
            continue
        spec = np.abs(np.fft.rfft(seg * np.hanning(n)))
        freqs = np.fft.rfftfreq(n, 1 / rate)
        spec[freqs < 60] = 0
        out.append((i / rate, float(freqs[spec.argmax()])))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rom")
    ap.add_argument("wav")
    ap.add_argument("--frames", type=int, default=600)
    ap.add_argument("--skip", type=int, default=0, help="frames to run before capturing")
    ap.add_argument("--press", action="append", default=[], help="button:frames, before capturing")
    ap.add_argument("--model", default="dmg")
    a = ap.parse_args()
    presses = [(p.split(":")[0], int(p.split(":")[1])) for p in a.press]
    s, rate = capture(a.rom, a.frames, presses, a.skip, a.model)
    Path(a.wav).parent.mkdir(parents=True, exist_ok=True)
    with wave.open(a.wav, "wb") as w:
        w.setnchannels(2); w.setsampwidth(1); w.setframerate(rate)
        w.writeframes((s.astype(np.int16) + 128).astype(np.uint8).tobytes())
    print(f"{a.wav}: {len(s) / rate:.2f}s, rms {np.sqrt((s.astype(float) ** 2).mean()):.1f}")
    print(" ".join(f"{t:.2f}s:{f:.0f}Hz" for t, f in peaks(s, rate)))


if __name__ == "__main__":
    main()
