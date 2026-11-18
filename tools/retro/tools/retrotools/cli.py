"""`retrotest` — poke at a ROM from the shell (stable-retro driver; fast, not cycle-accurate).

    retrotest run build/sms/game.sms --frames 120 --print player_x --out out/boot.png
    retrotest run build/game.nes --frames 120 --press right:30 --press a:12 --print player_y
    retrotest watch build/gg/game.gg --frames 300 --print player_y --every 10
    retrotest symbols build/game.nes --filter player
"""
from __future__ import annotations

import argparse
import sys

from .rom import Rom


def main(argv=None):
    ap = argparse.ArgumentParser(prog="retrotest", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("run", "watch", "symbols"):
        p = sub.add_parser(name)
        p.add_argument("rom")
        p.add_argument("--frames", type=int, default=120)
        if name == "run":
            p.add_argument("--press", action="append", default=[], metavar="BUTTON[:FRAMES]")
            p.add_argument("--settle", type=int, default=1)
            p.add_argument("--print", default="")
            p.add_argument("--out")
            p.add_argument("--scale", type=int, default=3)
            p.add_argument("--blank-check", action="store_true", help="exit 2 if the screen is one flat colour")
        if name == "watch":
            p.add_argument("--print", required=True)
            p.add_argument("--every", type=int, default=10)
        if name == "symbols":
            p.add_argument("--filter")
    a = ap.parse_args(argv)
    with Rom(a.rom) as r:
        if a.cmd == "symbols":
            if not r.symbols:
                print("no .noi/.sym/.mlb next to the ROM")
                return 1
            for n, (bank, addr) in sorted(r.symbols.items(), key=lambda kv: kv[1]):
                if not a.filter or a.filter.lower() in n.lower():
                    print(f"{bank:02x}:{addr:04x}  {n}")
            return 0
        if a.cmd == "watch":
            names = [n for n in a.print.split(",") if n]
            print("frame", *names, sep="\t")
            for _ in range(0, a.frames, a.every):
                r.run(a.every)
                print(r.frame, *[r.mem(n) for n in names], sep="\t")
            return 0
        r.run(a.frames)
        for spec in a.press:
            b, _, n = spec.partition(":")
            r.press(b, int(n) if n else 1)
            r.run(a.settle)
        for n in [n for n in a.print.split(",") if n]:
            print(f"{n} = {r.mem(n)}")
        if a.out:
            print("screenshot:", r.screenshot(a.out, a.scale))
        if a.blank_check and r.is_blank():
            print("WARNING: screen is one flat colour")
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
