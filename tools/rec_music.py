#!/usr/bin/env python3
"""Record tunes as the game plays them (build/game.gb, PyBoy sound): the full mix and the pause mix, from the tune's first tick.

    python3 tools/rec_music.py OUTDIR [--model dmg|cgb] [--tunes title susanna ballgame] [--compare PROARR_DIR]

  title      boots to the title; the whole Entertainer: one pass (10336 frames) plus 30 s, so the loop seam is heard twice (at 0:00 and 2:53)
  susanna    ARCADE level 1 (the saloon): one pass (1536 frames) plus half a second
  ballgame   ARCADE level 2 (the sports bar): one pass (1728 frames) plus half a second
  mountain funicula skaters hall sailor sakura weasel danube   ARCADE levels 3-10: one pass plus half a second (music batches 2-4; the pause mix
             is the real pause menu's)
  sailor_fast   the Sailor with music_fast set (the Last call: a frame a row less)
  clear over bonus   the jingles, started from the soundtrack player (BONUS > SOUNDTRACK); the full mix only (the bonus loop twice)
  credits    BONUS > CREDITS: the whole credits tune plus its last 20 s (credits_ingame_full_end20s.wav); the full mix only
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
    "mountain": (7, 1024, 30, "mountain/mountain_b2"),
    "funicula": (8, 1425, 30, "funicula/funicula_b2"),
    "skaters": (9, 1728, 30, "skaters/skaters_b2"),
    "hall": (10, 1920, 30, "hall/hall_b3"),
    "sailor": (11, 1152, 30, "sailor/sailor_b3d"),          # (proarr has no b3d pause mix: the stem file names b3's, whose bass and drums are the same)
    "sakura": (12, 1344, 30, "sakura/sakura_b3"),
    "weasel": (13, 1152, 30, "weasel/weasel_b4"),
    "danube": (14, 1728, 30, "danube/danube_b4"),
    "sailor_fast": (11, 1024, 30, "sailor/sailor_b3_fast"),
    "clear": (1, 112, 30, "jingles/clear_b4"),
    "over": (2, 252, 30, "jingles/over_b4"),
    "bonus": (3, 480, 30, "jingles/bonus_b4"),
    "credits": (15, 8732, 30, "credits/credits_b4"),
}
JINGLES = ("clear", "over", "bonus")
LEVEL = {n: i + 1 for i, n in enumerate(["susanna", "ballgame", "mountain", "funicula", "skaters", "hall", "sailor", "sakura", "weasel", "danube"])}


def start(model, name):
    """A ROM playing tune `name`, stopped on the frame before its first tick (music_frames 0), sound emulation on."""
    from conftest import hold_stage_anim, title_level
    from test_sound import make_rom, run_until, state
    gb = make_rom(model)
    tune = TUNES[name][0]
    if name in JINGLES or name == "credits":
        from conftest import K_BONUS, K_CREDITS, title_pick
        from test_flow import run_until
        gb.run(120)
        hold_stage_anim(gb)
        if name == "credits":
            title_pick(gb, K_BONUS, K_CREDITS)
            run_until(gb, lambda: gb.mem("story_phase") == 8, 40)
        else:
            from test_jukebox import tap, to_jukebox
            gb.write("tune_unlocked", 0xFF)
            gb.write(gb.addr("tune_unlocked") + 1, 0xFF)
            to_jukebox(gb)
            while gb.mem("jb_sel") != tune:
                tap(gb, "right")
            gb.press("a", 2)
    elif name != "title":                    # (the title tune starts about frame 70 of the boot: it is caught on its first tick below)
        gb.run(120)
        hold_stage_anim(gb)
        if name == "sailor_fast":
            from test_art import goto_group
            title_level(gb, LEVEL["sailor"])
            gb.run(40)
            gb.write("music_fast", 1)
            goto_group(gb, 6)                # (the level's music_play restarts the tune at the new speed)
            gb.write("music_fast", 1)
            gb.write("intro_timer", 255)
        else:
            title_level(gb, LEVEL[name])
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
        assert f >= one - 8 or gb.mem("cur_tune") == tune, f"{name}: the tune changed at frame {f}"   # (a jingle or the credits ends with their pass)
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
            if mode == "pause" and (name in JINGLES or name == "credits"):
                continue
            s, rate, f0, frames, sfx = record(args.model, name, mode)
            path = out / name / f"{name}_ingame_{label}.wav"
            write(path, s, rate)
            if name == "credits":
                write(path.with_name(f"{name}_ingame_{label}_end20s.wav"), s[-20 * rate:], rate)
            print(f"{path}: {len(s) / rate:.1f} s peak {int(np.abs(s).max())} rms {float(np.sqrt((s.astype(float) ** 2).mean())):.0f} "
                  f"(music_frames {f0} -> {frames}, {sfx} sound effects started)", flush=True)
            if args.compare:
                stem = TUNES[name][3]
                ref = Path(args.compare) / (f"{stem}_full.wav" if mode == "full" else f"{stem}_pausemix_bass_drums.wav")
                if name in JINGLES:
                    ref = Path(args.compare) / f"{stem}.wav"
                if not ref.exists():                       # (proarr has no b3d pause mix: the plain Sailor's, whose bass and drums are the same)
                    ref = ref.with_name(ref.name.replace("b3d", "b3"))
                b, brate = load(ref)
                assert brate == rate, (brate, rate)
                print(f"-- {name} {label} against {ref.name}")
                compare(s, b, rate, one / 59.7275)


if __name__ == "__main__":
    main()
