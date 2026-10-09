"""`gbcheck` — run a ROM through SameBoy's headless tester as the accuracy gate.

    gbcheck build/game.gb                      # DMG and CGB, 10 emulated seconds each
    gbcheck build/game.gb --length 30 --start  # longer, and push Start/A like a player would
    gbcheck build/game.gb --models cgb --out out/check

SameBoy is cycle-accurate where PyBoy is not. The tester runs the ROM with
rendering off (fast), then writes a final-frame BMP and a log. This wrapper
converts the BMP to PNG, scans the log for the tester's own alarms
("stuck in an FF loop", stack/SP warnings, invalid opcodes) and flags a
screen that is one flat colour. Exit status 1 on any failure.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

ALARMS = ("stuck", "ff loop", "stack", "invalid", "crash", "unsafe", "weird", "overflow")


def run_one(rom: Path, model: str, length: int, start: bool, out: Path) -> tuple[bool, list[str]]:
    exe = shutil.which("sameboy_tester")
    if not exe:
        return False, ["sameboy_tester not on PATH"]
    notes: list[str] = []
    ok = True
    with tempfile.TemporaryDirectory() as td:
        work = Path(td) / rom.name
        shutil.copy(rom, work)
        cmd = [exe, f"--{model}", "--length", str(length)]
        if start:
            cmd.append("--start")
        cmd.append(str(work))
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=length * 20 + 60)
        if r.returncode != 0:
            ok = False
            notes.append(f"tester exit {r.returncode}: {r.stderr.strip()[-300:]}")
        bmp, log = work.with_suffix(".bmp"), work.with_suffix(".log")
        out.mkdir(parents=True, exist_ok=True)
        png = out / f"{rom.stem}.{model}.png"
        if bmp.is_file():
            im = Image.open(bmp).convert("RGB")
            im.save(png)
            if len(im.getcolors(2) or [0, 0]) == 1:
                ok = False
                notes.append("screen is one flat colour")
            notes.append(f"screenshot {png}")
        else:
            ok = False
            notes.append("no screenshot produced")
        if log.is_file():
            text = log.read_text(errors="replace")
            (out / f"{rom.stem}.{model}.log").write_text(text)
            for line in text.splitlines():
                if any(k in line.lower() for k in ALARMS):
                    ok = False
                    notes.append(f"log: {line.strip()}")
    return ok, notes


def main(argv=None):
    ap = argparse.ArgumentParser(prog="gbcheck", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rom")
    ap.add_argument("--models", default="dmg,cgb", help="comma list of dmg,cgb,sgb (default dmg,cgb)")
    ap.add_argument("--length", type=int, default=10, help="emulated seconds (default 10)")
    ap.add_argument("--start", action="store_true", help="push Start and A periodically, like a player")
    ap.add_argument("--out", default="out/check")
    a = ap.parse_args(argv)

    rom = Path(a.rom)
    if not rom.is_file():
        sys.exit(f"no such ROM: {rom}")
    failed = False
    for model in [m for m in a.models.split(",") if m]:
        ok, notes = run_one(rom, model, a.length, a.start, Path(a.out))
        print(f"[{model}] {'OK' if ok else 'FAIL'}")
        for n in notes:
            print(f"    {n}")
        failed |= not ok
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
