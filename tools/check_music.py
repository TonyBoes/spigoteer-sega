#!/usr/bin/env python3
"""Pitch check for every tune: render the ROM's audio with only one sound channel routed to the
output (NR51), find the dominant pitch inside each melody note, and print it beside the note the
song source says should sound.  A sanity check of the song data and the driver, not a listening test.

    check_music.py                     # all tunes, first 8 bars, melody (ch2) and bass (ch3)
    check_music.py ballgame --bars 4   # one tune
    check_music.py --model cgb

Run `make` first (build/game.gb).
"""
import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import gen_music as gm  # noqa: E402
import songs  # noqa: E402
from gbtools import Rom  # noqa: E402
from pyboy import PyBoy  # noqa: E402

NR51 = 0xFF25
SOLO = {2: 0x22, 3: 0x44, 4: 0x88}
STATE_LEVEL_CLEAR = 3
TUNE_SHOW = 4           # music.h: TUNE_TITLE, CLEAR, OVER, BONUS, SHOW, VENUE0..9
TUNE_VENUE0 = 5


def note_hz(n):
    """hUGE note index -> Hz (index 0 is C2 = 65.41 Hz)."""
    return 65.406 * 2 ** (n / 12)


def note_name(hz):
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    n = int(round(12 * np.log2(hz / 65.406)))
    return f"{names[n % 12]}{2 + n // 12}"


def open_rom(model):
    rom = Rom(ROOT / "build" / "game.gb", model)
    rom.pb.stop(save=False)
    rom.pb = PyBoy(str(ROOT / "build" / "game.gb"), window="null", sound_emulated=True, cgb=(model == "cgb"),
                   log_level="ERROR")
    rom.pb.set_emulation_speed(0)
    return rom


def capture(model, source, solo, frames):
    """Returns (list of per-frame sample arrays, per-frame music_frames, first frame of the tune's first pass)."""
    rom = open_rom(model)
    rom.run(100)
    target = None
    names = ["entertainer"] + songs.VENUES
    idx = {n: i for i, n in enumerate(names)}
    if source == "entertainer":
        target = 0
        rom.pb.stop(save=False)
        rom = open_rom(model)           # from the very start of the ROM: the title tune starts at boot
    elif source == "galop":
        target = TUNE_SHOW
        start_arcade(rom)
        rom.run(60)
        rom.write("intro_timer", 255)
        rom.write("tip_chance", 0)
    else:
        g = songs.VENUES.index(source)
        target = TUNE_VENUE0 + g
        start_arcade(rom)
        if g != 0:
            rom.run(30)
            L = g + 1 if (g + 1) % 2 == 0 else g + 10      # level L is the one after a clear of an odd level
            rom.write("level", L - 1)
            rom.write("game_state", STATE_LEVEL_CLEAR)
            rom.write("state_timer", 149)
    chunks, mfs, tunes_seen = [], [], []
    for f in range(frames):
        if source == "galop" and f == 30:             # the tip lies where the bartender stands: picked up, the show starts
            rom.write("tip_bar", rom.mem("bar"))
            rom.write("tip_x", rom.mem("bartender_x"))
            rom.write("tip_timer", 100)
        rom.pb.memory[NR51] = SOLO[solo]
        if source not in ("entertainer", "galop"):
            rom.write("intro_timer", 255)             # no patrons come: the level lasts as long as the tune is checked
        rom.run(1)
        rom.pb.memory[NR51] = SOLO[solo]
        if source == "galop" and rom.mem("show_timer") and rom.mem("show_timer") < 200:
            rom.write("show_timer", 2000)             # let the show run long enough for 8 bars
        chunks.append(rom.pb.sound.ndarray.copy())
        mfs.append(rom.mem16("music_frames"))
        tunes_seen.append(rom.mem("cur_tune"))
    rate = rom.pb.sound.sample_rate
    rom.pb.stop(save=False)
    start = next(f for f in range(frames) if tunes_seen[f] == target and mfs[f] == 1)
    return chunks, mfs, start, rate


def detect(seg, rate, lo, hi):
    seg = seg - seg.mean()
    if np.abs(seg).max() < 1:
        return 0.0
    n = len(seg)
    pad = 1 << int(np.ceil(np.log2(n * 16)))
    spec = np.abs(np.fft.rfft(seg * np.hanning(n), pad))
    freqs = np.fft.rfftfreq(pad, 1 / rate)
    spec[(freqs < lo) | (freqs > hi)] = 0
    return float(freqs[spec.argmax()])


def check(model, source, bars, solo):
    t = songs.SONGS[source]
    tempo = t["tempo"]
    legacy = False
    text = t["ch2"] if solo == 2 else t["ch3"]
    rows = gm.rows_for(solo, text, 1, tempo, legacy, t.get("gap", True), t.get("stac_all"))
    # note list: (row, rows long, hUGE note index)
    notes = []
    for i, (n, ins, eff) in enumerate(rows):
        if n != gm.REST:
            j = i + 1
            while j < len(rows) and rows[j][0] == gm.REST:
                j += 1
            notes.append((i, j - i, n))
    per_bar = songs.BAR_ROWS[source]
    last_row = bars * per_bar
    notes = [x for x in notes if x[0] < last_row]
    frames = (last_row * tempo) + 150
    chunks, mfs, start, rate = capture(model, source, solo, start_frames(frames, source))
    # frame index where row r begins sounding: the tick that starts row r is call r*tempo+1; its sound is heard from the next frame
    def first_frame(row):
        k = row * tempo + 1
        return next(f for f in range(start, len(mfs)) if mfs[f] >= k)
    flat = np.concatenate(chunks).astype(float).mean(axis=1)
    spf = len(np.concatenate(chunks)) / len(chunks)       # samples per frame
    out, bad = [], 0
    for row, ln, n in notes:
        f0 = first_frame(row) + 1
        a = int((f0 + 0.2 * ln * tempo) * spf)
        b = int((f0 + 0.8 * ln * tempo) * spf)
        exp = note_hz(n) / (2 if solo == 3 else 1)      # the wave channel sounds an octave below the pulse one
        got = detect(flat[a:b], rate, exp * 0.6, exp * 1.7)
        ok = got > 0 and abs(12 * np.log2(got / exp)) < 0.6          # within a half semitone
        bad += not ok
        out.append((row // per_bar + 1, row % per_bar, ln, note_name(exp), exp, got, ok))
    return out, bad


def gm_name(n):
    return note_name(note_hz(n))


def start_arcade(rom):
    """From the title: the old 10-level rotation (the LEVEL harness, MODE_LEVEL) at level 1, through the title's test
    hook title_go (src/title.c; PLAY > ARCADE plays the story's sequence since the three modes)."""
    rom.write("title_go", 1)
    rom.run(8)


def start_frames(frames, source):
    return frames + (200 if source != "entertainer" else 0) + 120


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tunes", nargs="*", default=["entertainer", "galop"] + songs.VENUES)
    ap.add_argument("--bars", type=int, default=8)
    ap.add_argument("--model", default="dmg")
    ap.add_argument("--channels", default="2,3")
    ap.add_argument("-v", action="store_true", help="print every note, not just the summary")
    a = ap.parse_args()
    total_bad = 0
    for source in a.tunes:
        for solo in [int(c) for c in a.channels.split(",")]:
            res, bad = check(a.model, source, a.bars, solo)
            total_bad += bad
            label = {2: "melody ch2", 3: "bass ch3"}[solo]
            print(f"== {source}: {label}, first {a.bars} bars, {len(res)} notes, {bad} off ==")
            if a.v or bad:
                print("  bar row len  expected(Hz)  detected(Hz)  note")
                for bar, r, ln, name, exp, got, ok in res:
                    if a.v or not ok:
                        print(f"  {bar:3d} {r:3d} {ln:3d}  {name:>4s} {exp:7.1f}   {got:7.1f}  {note_name(got) if got else '-':>4s} {'' if ok else '<-- MISMATCH'}")
    return 1 if total_bad else 0


if __name__ == "__main__":
    sys.exit(main())
