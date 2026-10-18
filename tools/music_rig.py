#!/usr/bin/env python3
"""Music CPU rig: the real src/music.c + src/musicload.c + hUGEDriver + the generated build/music_*.c in a bare ROM (tools/music_harness), one
music_tick a frame, each call metered with DIV.  Used to check that no tick of any tune runs past MUSIC_LATEST_LY (18 lines).

    python3 tools/music_rig.py build              # out/rig/aud.gb from build/ (run `make` first)
    python3 tools/music_rig.py cost [TUNE ...]    # per-call cost over one whole pass of each tune (default: every tune that was changed)
    python3 tools/music_rig.py cost --warm title  # ... with the show tune already in buffer B, as in the game
    python3 tools/music_rig.py cost --passes=2 title   # two passes: the loop seam is covered

TUNE is a name from gen_music.TUNES (title, clear, over, bonus, show, venue0..9, credits).  A line is 114 M-cycles; the budget is 18 lines
(2052 M-cycles); DIV counts 64 M-cycles, so the meter's resolution is 64.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import gen_music as gm      # noqa: E402

RIG = ROOT / "out" / "rig"
LINE = 114
DEFAULT = ["title", "clear", "over", "bonus", "show", "venue0", "venue1", "credits"]


def build():
    RIG.mkdir(parents=True, exist_ok=True)
    for f in ("main.c", "stubs.c"):
        shutil.copy(ROOT / "tools" / "music_harness" / f, RIG / f)
    for f in ("music.c", "musicload.c"):
        shutil.copy(ROOT / "src" / f, RIG / f)
    shutil.copy(ROOT / "build" / "hUGEDriver.o", RIG / "hUGEDriver.o")      # (bankpack rewrites its inputs in place)
    for f in ["music_data.c"] + sorted(p.name for p in (ROOT / "build").glob("music_pat*.c")):
        shutil.copy(ROOT / "build" / f, RIG / f)
    files = ["main.c", "stubs.c", "music.c", "musicload.c", "music_data.c"] + sorted(p.name for p in RIG.glob("music_pat*.c"))
    cmd = ["lcc", "-Wa-l", "-Wl-m", "-Wl-j", "-Wm-yt0x19", "-Wm-yo32", "-autobank", f"-I{ROOT / 'src'}", f"-I{RIG}",
           f"-I{ROOT}/third_party/hugedriver/include", "-o", str(RIG / "aud.gb")] + [str(RIG / f) for f in files] + [str(RIG / "hUGEDriver.o")]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        print(r.stdout[-2000:], r.stderr[-3000:])
        raise SystemExit("lcc failed")


def tune_table():
    """{tune name: (index, frames)} from build/music_data.c's tunes[]."""
    txt = (ROOT / "build" / "music_data.c").read_text()
    body = txt[txt.index("const tune_t tunes[TUNE_ALL] = {"):]
    rows = re.findall(r"\{&song_\w+, (\d+), (\d+), ", body)
    assert len(rows) == len(gm.TUNES)
    return {n: (i, int(r[1])) for i, (n, r) in enumerate(zip(gm.TUNES, rows))}


def boot():
    from pyboy import PyBoy
    noi = (RIG / "aud.noi").read_text()
    addr = {k: int(re.search(rf"DEF _{k} (0x[0-9A-Fa-f]+)", noi).group(1), 16)
            for k in ("aud_req", "aud_nr51", "cur_tune", "aud_cyc_sum", "aud_cyc_max", "aud_cyc_last", "music_frames")}
    pb = PyBoy(str(RIG / "aud.gb"), window="null", sound_emulated=False, log_level="ERROR")
    pb.set_emulation_speed(0)
    for _ in range(300):
        pb.tick(1, False, False)
        if pb.memory[addr["cur_tune"]] == 255:
            break
    pb.tick(5, False, False)
    return pb, addr


def cost_calls(name, warm=False, frames=None, passes=1):
    """Per CALL cost of music_tick over `passes` passes of tune `name`: aud_cyc_max is cleared every emulator frame, so a frame in which two
    calls complete (the rig's frame boundary drifts through the tick) still shows its dearer call.  warm: the show tune is in buffer B first."""
    idx, pf = tune_table()[name]
    pb, addr = boot()
    mf = addr["music_frames"]
    if warm:
        pb.memory[addr["aud_req"]] = tune_table()["show"][0]
        pb.tick(120, False, False)
    pb.memory[addr["aud_req"]] = idx
    for _ in range(60):
        pb.tick(1, False, False)
        if pb.memory[addr["cur_tune"]] == idx and 0 < (pb.memory[mf] | (pb.memory[mf + 1] << 8)) < 3:
            break
    frames = frames or pf * passes
    lo, hi = addr["aud_cyc_sum"], addr["aud_cyc_sum"] + 1
    per, total, prev = [], 0, pb.memory[lo] | (pb.memory[hi] << 8)
    for _ in range(frames):
        pb.memory[addr["aud_cyc_max"]] = 0
        pb.tick(1, False, False)
        per.append(pb.memory[addr["aud_cyc_max"]] * 64)
        cur = pb.memory[lo] | (pb.memory[hi] << 8)
        total += (cur - prev) & 0xFFFF
        prev = cur
    pb.stop(save=False)
    worst = max(per)
    return dict(tune=name, warm=warm, frames=frames, mean_mcycles=round(total * 64 / frames), worst_mcycles=worst,
                mean_lines=round(total * 64 / frames / LINE, 1), worst_lines=round(worst / LINE, 1), worst_frame=per.index(worst),
                calls_over_16_lines=sum(1 for c in per if c > 16 * LINE), calls_over_18_lines=sum(1 for c in per if c > 18 * LINE))


def main():
    cmd, args = (sys.argv[1] if len(sys.argv) > 1 else "cost"), sys.argv[2:]
    if cmd == "build":
        build()
        return
    warm = "--warm" in args
    passes = next((int(a.split("=")[1]) for a in args if a.startswith("--passes=")), 1)
    names = [a for a in args if not a.startswith("--")] or DEFAULT
    if not (RIG / "aud.gb").exists():
        build()
    for n in names:
        for w in ((False, True) if (not warm and n != "show") else (warm,)):
            print(cost_calls(n, w, passes=passes), flush=True)


if __name__ == "__main__":
    main()
