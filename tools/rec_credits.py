#!/usr/bin/env python3
"""Record the credits roll's audio (the credits tune, src/credits.c) to a WAV, as the game plays it.

    python3 tools/rec_credits.py out/d3c_ingame.wav [--model dmg|cgb] [--compare audition.wav]

Boots build/game.gb with PyBoy's sound emulation, opens BONUS > CREDITS, and records every frame until the credits tune has
ended (a bit longer with --tail seconds).  PyBoy's sound buffer is sliced by raw_buffer_head // 2 per frame: the whole array
has one stale row per frame that crackles at 60 Hz (the same fix as tools/dump_audio.py).  16-bit stereo, a fixed gain of 1000
(the one tools/music_drafts.py used for the audition WAVs, so volumes compare).

--compare: lines the recording up against another WAV (the draft's audition of the tune) by the first audible sample and prints how
closely they match over the tune's length.  The recording is taken without the roll's picture or any key presses besides the menu's.
"""
import argparse
import sys
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
GAIN = 1000
TUNE_CREDITS = 15


def record(model, tail):
    from conftest import K_BONUS, K_CREDITS, hold_stage_anim, title_pick
    from test_flow import run_until
    from test_sound import make_rom
    gb = make_rom(model)
    gb.run(120)
    hold_stage_anim(gb)
    title_pick(gb, K_BONUS, K_CREDITS)
    run_until(gb, lambda: gb.mem("story_phase") == 8, 40)
    pb = gb.pb
    chunks, frames = [], 0
    while True:
        pb.tick(1, False, True)
        chunks.append(pb.sound.ndarray[:pb.sound.raw_buffer_head // 2].copy())
        frames += 1
        if gb.mem("cur_tune") != TUNE_CREDITS or frames > 9500:
            break
    rate = pb.sound.sample_rate
    for _ in range(int(tail * 60)):
        pb.tick(1, False, True)
        chunks.append(pb.sound.ndarray[:pb.sound.raw_buffer_head // 2].copy())
    pb.stop(save=False)
    return np.concatenate(chunks).astype(np.int16), rate, frames


def save(path, s, rate):
    s = np.clip(s.astype(np.int64) * GAIN, -32768, 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(s.tobytes())
    return s


def load(path):
    with wave.open(str(path), "rb") as w:
        rate = w.getframerate()
        a = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").reshape(-1, 2)
    return a, rate


def xcorr_peak(u, v, maxlag):
    """The lag L (v[i + L] ~ u[i]) in -maxlag..maxlag with the highest cross-correlation, by FFT."""
    n = 1 << int(np.ceil(np.log2(len(u) + len(v))))
    c = np.fft.irfft(np.fft.rfft(v, n) * np.conj(np.fft.rfft(u, n)), n)
    lags = np.concatenate([np.arange(0, maxlag + 1), np.arange(-maxlag, 0)])
    vals = np.concatenate([c[:maxlag + 1], c[n - maxlag:]])
    return int(lags[np.argmax(vals)])


def compare(a, b, rate, seconds):
    """a, b: int16 stereo.  Lines b up on a by their loudness envelopes, then compares `seconds` by short-time
    magnitude spectra (4096-sample windows): two recordings of the same notes agree there even where the square waves' phases differ
    (the audition ROM starts the tune a fraction of a frame apart, so the samples themselves are never identical)."""
    x = a.astype(np.float64).mean(axis=1)
    y = b.astype(np.float64).mean(axis=1)
    k, span = 64, 20 * rate
    env = lambda z: np.convolve(np.abs(z[:span]), np.ones(k) / k, "same")[::k]
    lag = xcorr_peak(env(x), env(y), 2 * rate // k) * k           # (to within 64 samples, 1.3 ms: a window is 85 ms)
    n = min(len(x), len(y) - max(lag, 0), int(seconds * rate)) if lag >= 0 else min(len(x) + lag, len(y), int(seconds * rate))
    xa, ya = (x[:n], y[lag:lag + n]) if lag >= 0 else (x[-lag:-lag + n], y[:n])
    W = 4096
    win = np.hanning(W)
    cs, ex, ey = [], 0.0, 0.0
    for s in range(0, n - W, W):
        u = np.abs(np.fft.rfft(xa[s:s + W] * win))
        v = np.abs(np.fft.rfft(ya[s:s + W] * win))
        ex += float(np.abs(xa[s:s + W]).sum())
        ey += float(np.abs(ya[s:s + W]).sum())
        if u.sum() > 1e3 or v.sum() > 1e3:
            cs.append(float((u * v).sum() / np.sqrt((u * u).sum() * (v * v).sum() + 1e-9)))
    cs = np.array(cs)
    print(f"compared {n / rate:.1f} s (the other recording is {lag / rate:+.3f} s later): short-time spectrum cosine over {len(cs)} "
          f"windows mean {cs.mean():.4f}, worst {cs.min():.4f}, windows above 0.95: {(cs > 0.95).mean() * 100:.1f} %; loudness ratio {ex / ey:.4f}")
    return float(cs.mean()), float(cs.min())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--model", default="dmg", choices=("dmg", "cgb"))
    ap.add_argument("--tail", type=float, default=0.5, help="seconds recorded after the tune ends")
    ap.add_argument("--compare")
    ap.add_argument("--seconds", type=float, default=145.3, help="length compared (the tune is 9986 frames = 166.4 s of PyBoy audio; what follows it is the title tune)")
    args = ap.parse_args()
    s, rate, frames = record(args.model, args.tail)
    s = save(args.out, s, rate)
    print(f"{args.out}: {len(s) / rate:.1f} s ({frames} frames of tune), {rate} Hz")
    if args.compare:
        other, orate = load(args.compare)
        assert orate == rate, (orate, rate)
        compare(s, other, rate, args.seconds)


if __name__ == "__main__":
    main()
