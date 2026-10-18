#!/usr/bin/env python3
"""Record tunes as the game plays them (build/game.gb, PyBoy sound): the full mix and the pause mix, from the tune's first tick.

    python3 tools/rec_music.py OUTDIR [--model dmg|cgb] [--tunes title susanna ballgame] [--compare PROARR_DIR]

  title      boots to the title; the whole Entertainer: one pass (10336 frames) plus 30 s, so the loop seam is heard twice (at 0:00 and 2:53)
  susanna    ARCADE level 1 (the saloon): one pass (1536 frames) plus half a second
  ballgame   ARCADE level 2 (the sports bar): one pass (1728 frames) plus half a second
Files in OUTDIR/<tune>/, each with a _24k copy (sample pairs averaged): <tune>_ingame_full.wav and <tune>_ingame_pausemix_bass_drums.wav.
The pause mix is the game's real one (src/pause.c: NR51 0xCC, bass + drums): the pause menu opened over the venue tunes; the title has no pause
menu, so there the same mix is made with the menu's own NR51 value (0xCC, held every frame).
PyBoy's sound buffer is sliced by raw_buffer_head // 2 per frame (the whole array has a stale row that crackles at 60 Hz).  Gain 800 (the
audition WAVs' gain, so levels compare).  --compare PROARR_DIR lines each recording up against tools/proarr.py's WAV of the same tune
(PROARR_DIR/title_full/title_full_full.wav, susanna/susanna_b1_full.wav, ballgame/ballgame_b1_full.wav and the pause mixes) and prints a
short-time spectrum match (tools/rec_credits.py compare()).
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
NR51, TMA = 0xFF25, 0xFF06
TUNES = {   # name: (cur_tune, frames of one pass, extra frames recorded, proarr file stem)
    "title": (0, 10336, 1800, "title_full/title_full"),
    "susanna": (5, 1536, 30, "susanna/susanna_b1"),
    "ballgame": (6, 1728, 30, "ballgame/ballgame_b1"),
}


def start(model, name):
    """A ROM playing tune `name`, stopped on the frame before its first tick (music_frames 0), sound emulation on."""
    from conftest import hold_stage_anim, title_level
    from test_sound import make_rom, run_until, state
    gb = make_rom(model)
    tune = TUNES[name][0]
    if name != "title":                      # (the title tune starts about frame 70 of the boot: it is caught on its first tick below)
        gb.run(120)
        hold_stage_anim(gb)
        title_level(gb, 1 if name == "susanna" else 2)
    for _ in range(600):
        if gb.mem("cur_tune") == tune and gb.mem16("music_frames") <= 1 and (name != "title" or gb.mem16("music_frames") == 1):
            break
        gb.run(1)
    else:
        raise SystemExit(f"{name}: the tune did not start")
    return gb


def record(model, name, mode):
    """mode 'full' or 'pause'.  Returns (int16 stereo, rate)."""
    tune, one, extra, _ = TUNES[name]
    gb = start(model, name)
    pb = gb.pb
    chunks = []
    n = one + extra
    f0 = gb.mem16("music_frames")
    for f in range(n):
        if mode == "pause" and name == "title":
            pb.memory[NR51] = 0xCC                          # (the title's first seconds are an LCD-off load that music_pump ticks: no TMA flag there)
        elif mode == "pause" and f == 0:
            gb.hold("start")                               # the menu opens on the tune's first frames (a few frames of the full mix lead the file)
        elif mode == "pause" and f == 3:
            gb.release("start")
        pb.tick(1, False, True)
        chunks.append(pb.sound.ndarray[:pb.sound.raw_buffer_head // 2].copy())
        assert gb.mem("cur_tune") == tune, f"{name}: the tune changed at frame {f}"
        if mode == "pause" and f > 8:
            assert pb.memory[NR51] == 0xCC or pb.memory[NR51] == 0x44, hex(pb.memory[NR51])
            assert name == "title" or gb.mem("game_state") == 5, "paused"
    rate = pb.sound.sample_rate
    frames = gb.mem16("music_frames")
    sfx = sum(gb.read("sfx_count", 15))
    gb.stop()
    raw = np.concatenate(chunks).astype(np.int32)
    return np.clip(raw * GAIN, -32768, 32767).astype("<i2"), rate, f0, frames, sfx


def write(path, s, rate):
    path.parent.mkdir(parents=True, exist_ok=True)
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
    ap.add_argument("--tunes", nargs="*", default=list(TUNES))
    ap.add_argument("--compare")
    args = ap.parse_args()
    out = Path(args.out)
    for name in args.tunes:
        one = TUNES[name][1]
        for mode, label in (("full", "full"), ("pause", "pausemix_bass_drums")):
            s, rate, f0, frames, sfx = record(args.model, name, mode)
            path = out / name / f"{name}_ingame_{label}.wav"
            write(path, s, rate)
            print(f"{path}: {len(s) / rate:.1f} s peak {int(np.abs(s).max())} rms {float(np.sqrt((s.astype(float) ** 2).mean())):.0f} "
                  f"(music_frames {f0} -> {frames}, {sfx} sound effects started)", flush=True)
            if args.compare:
                stem = TUNES[name][3]
                ref = Path(args.compare) / (f"{stem}_full.wav" if mode == "full" else f"{stem}_pausemix_bass_drums.wav")
                b, brate = load(ref)
                assert brate == rate, (brate, rate)
                print(f"-- {name} {label} against {ref.name}")
                compare(s, b, rate, one / 59.7275)


if __name__ == "__main__":
    main()
