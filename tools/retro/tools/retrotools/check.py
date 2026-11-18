"""`retrocheck` — run a ROM through MesenCE's cycle-accurate test runner (the accuracy gate).

    retrocheck build/sms/game.sms
    retrocheck build/game.nes --frames 900 --hold start:120-125 --print player_x,player_y
    retrocheck build/gg/game.gg --expect dead=0 --expect on_ground=1

Runs headless (under xvfb: MesenCE's GUI toolkit wants an X display even in
test-runner mode), at maximum speed, for --frames frames. Then writes a PNG of
the final frame, reads the requested variables (names come from the ROM's
.noi / .sym / .mlb), and fails on: a Mesen timeout or error, a screen that is one
flat colour, or any --expect that does not hold. Exit status 1 on failure.

MesenCE runs the real boot sequence (the Game Boy boot ROM is ~80 frames), so
compare state after boot, never absolute frame counts, against the stable-retro tests.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

from .rom import system_for
from .symbols import load_symbols

MESEN = os.environ.get("MESEN", "/opt/mesence/Mesen")
MEMTYPE = {"gb": "gameboyMemory", "sms": "smsMemory", "gg": "smsMemory", "nes": "nesMemory"}
BUTTONS = ("a", "b", "start", "select", "up", "down", "left", "right")

LUA = r"""
local frames, target = 0, %(frames)d
local holds = %(holds)s
local reads = %(reads)s
emu.addEventCallback(function()
  local pad = {}
  for _, h in ipairs(holds) do
    if frames >= h[2] and frames <= h[3] then pad[h[1]] = true end
  end
  emu.setInput(pad, 0)
end, emu.eventType.inputPolled)
emu.addEventCallback(function()
  frames = frames + 1
  if frames < target then return end
  local fh = io.open(%(png)s, "wb"); fh:write(emu.takeScreenshot()); fh:close()
  local out = {}
  for _, r in ipairs(reads) do
    out[#out + 1] = string.format('"%%s": %%d', r[1], emu.read(r[2], emu.memType.%(memtype)s, false))
  end
  local jf = io.open(%(json)s, "w"); jf:write("{" .. table.concat(out, ", ") .. "}"); jf:close()
  emu.stop(0)
end, emu.eventType.endFrame)
"""


def _lua_list(items):
    return "{" + ", ".join("{" + ", ".join(json.dumps(x) if isinstance(x, str) else str(x) for x in it) + "}"
                           for it in items) + "}"


def run(rom: Path, frames: int, holds, names, out: Path, timeout: int):
    if not Path(MESEN).is_file():
        return False, {}, [f"MesenCE not found at {MESEN} (set MESEN=)"]
    if not shutil.which("xvfb-run"):
        return False, {}, ["xvfb-run not on PATH"]
    system = system_for(rom)
    syms = load_symbols(rom)
    reads, notes = [], []
    for n in names:
        if n.startswith(("0x", "0X")):
            reads.append((n, int(n, 16)))
        elif n in syms:
            reads.append((n, syms[n][1]))
        else:
            return False, {}, [f"no symbol {n!r} in the ROM's symbol file"]
    out.mkdir(parents=True, exist_ok=True)
    png = out / f"{rom.stem}.{system}.png"
    png.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory() as td:
        js, script = Path(td) / "vars.json", Path(td) / "check.lua"
        script.write_text(LUA % dict(frames=frames, holds=_lua_list(holds), reads=_lua_list(reads),
                                     png=json.dumps(str(png.resolve())), json=json.dumps(str(js)),
                                     memtype=MEMTYPE[system]))
        cmd = ["xvfb-run", "-a", MESEN, "--testrunner", str(rom.resolve()), str(script), f"--timeout={timeout}"]
        # .NET without ICU: nothing in a test run is locale-dependent, and the
        # sbx image may not ship libicu (MesenCE aborts at start without it).
        env = dict(os.environ, DOTNET_SYSTEM_GLOBALIZATION_INVARIANT="1")
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 60, env=env)
        values = json.loads(js.read_text()) if js.is_file() else {}
    ok = r.returncode == 0
    if not ok:
        tail = (r.stdout + r.stderr).strip().splitlines()[-3:]
        notes.append(f"MesenCE exit {r.returncode}" + (" (timeout: frame target not reached)" if r.returncode == 255 else "")
                     + (": " + " | ".join(tail) if tail else ""))
    if png.is_file():
        if len(Image.open(png).convert("RGB").getcolors(2) or [0, 0]) == 1:
            ok = False
            notes.append("screen is one flat colour")
        notes.append(f"screenshot {png}")
    else:
        ok = False
        notes.append("no screenshot produced")
    return ok, values, notes


def main(argv=None):
    ap = argparse.ArgumentParser(prog="retrocheck", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rom")
    ap.add_argument("--frames", type=int, default=600, help="frames to run (default 600 = 10 s)")
    ap.add_argument("--hold", action="append", default=[], metavar="BUTTON:FROM-TO",
                    help="hold a button over a frame range, e.g. start:120-125 (repeatable)")
    ap.add_argument("--print", default="", metavar="SYM,SYM", help="variables (or 0xADDR) to read at the end")
    ap.add_argument("--expect", action="append", default=[], metavar="SYM=VALUE")
    ap.add_argument("--out", default="out/check")
    ap.add_argument("--timeout", type=int, default=120, help="seconds before MesenCE gives up")
    a = ap.parse_args(argv)

    rom = Path(a.rom)
    if not rom.is_file():
        sys.exit(f"no such ROM: {rom}")
    holds = []
    for h in a.hold:
        b, _, rng = h.partition(":")
        lo, _, hi = rng.partition("-")
        if b not in BUTTONS or not lo.isdigit():
            sys.exit(f"bad --hold {h!r}; want BUTTON:FROM-TO with BUTTON in {list(BUTTONS)}")
        holds.append((b, int(lo), int(hi or lo)))
    expects = {}
    for e in a.expect:
        k, _, v = e.partition("=")
        expects[k] = int(v, 0)
    names = list(dict.fromkeys([n for n in a.print.split(",") if n] + list(expects)))

    ok, values, notes = run(rom, a.frames, holds, names, Path(a.out), a.timeout)
    for k in reversed(names):
        if k in values:
            notes.insert(0, f"{k} = {values[k]}")
    for k, want in expects.items():
        if values.get(k) != want:
            ok = False
            notes.append(f"EXPECT FAILED: {k} = {values.get(k)}, wanted {want}")
    print(f"[{system_for(rom)}] {'OK' if ok else 'FAIL'}  (MesenCE, {a.frames} frames)")
    for n in notes:
        print("    " + n)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
