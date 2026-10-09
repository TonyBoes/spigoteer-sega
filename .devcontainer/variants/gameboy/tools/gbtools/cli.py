"""`gbtest` — poke at a ROM from the shell without writing a test.

    gbtest run build/game.gb --frames 120 --out out/boot.png
    gbtest run build/game.gb --frames 60 --press right:30 --press a:4 --print player_x,player_y --out out/jump.png
    gbtest symbols build/game.gb
    gbtest oam build/game.gb --frames 120
    gbtest watch build/game.gb --frames 300 --print player_x --every 10

--press NAME:FRAMES actions run in order after the initial --frames, each
followed by --settle frames (default 1). Screens are saved at --scale (default 4,
so the agent can read them; 1 for goldens).
"""
from __future__ import annotations

import argparse
import sys

from .rom import BUTTONS, Rom


def _add_common(p):
    p.add_argument("rom")
    p.add_argument("--model", choices=["auto", "dmg", "cgb"], default="auto")
    p.add_argument("--frames", type=int, default=120, help="frames to run before anything else (default 120 = 2 s)")


def cmd_run(a):
    with Rom(a.rom, a.model) as gb:
        gb.run(a.frames)
        for spec in a.press:
            name, _, n = spec.partition(":")
            if name not in BUTTONS:
                sys.exit(f"unknown button {name!r}")
            gb.press(name, int(n) if n else 1)
            gb.run(a.settle)
        _print_syms(gb, a.print)
        if a.out:
            print("screenshot:", gb.screenshot(a.out, a.scale))
        if a.blank_check and gb.is_blank():
            print("WARNING: screen is a single colour (nothing drawn?)")
            return 2
    return 0


def cmd_watch(a):
    with Rom(a.rom, a.model) as gb:
        names = [s for s in a.print.split(",") if s]
        print("frame", *names, sep="\t")
        for _ in range(0, a.frames, a.every):
            gb.run(a.every)
            print(gb.frame, *[gb.mem(n) for n in names], sep="\t")
    return 0


def cmd_symbols(a):
    with Rom(a.rom, a.model) as gb:
        if not gb.symbols:
            print("no .sym/.noi next to the ROM (RGBDS: rgblink -n; GBDK: lcc -Wl-j)")
            return 1
        for name, (bank, addr) in sorted(gb.symbols.items(), key=lambda kv: kv[1]):
            if a.filter and a.filter.lower() not in name.lower():
                continue
            print(f"{bank:02x}:{addr:04x}  {name}")
    return 0


def cmd_oam(a):
    with Rom(a.rom, a.model) as gb:
        gb.run(a.frames)
        for i, s in enumerate(gb.oam()):
            vis = "" if 0 < s["y"] < 160 and 0 < s["x"] < 168 else "  (off-screen)"
            print(f"{i:2d}  y={s['y']:3d} x={s['x']:3d} tile={s['tile']:3d} flags={s['flags']:08b}{vis}")
        print("regs:", gb.regs())
    return 0


def _print_syms(gb, spec):
    for name in [s for s in spec.split(",") if s]:
        v = gb.mem(name)
        print(f"{name} = {v} (0x{v:02x})")


def gbtest_main(argv=None):
    ap = argparse.ArgumentParser(prog="gbtest", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("run", help="run, press buttons, print symbols, screenshot")
    _add_common(p)
    p.add_argument("--press", action="append", default=[], metavar="BUTTON[:FRAMES]")
    p.add_argument("--settle", type=int, default=1)
    p.add_argument("--print", default="", metavar="SYM,SYM")
    p.add_argument("--out", help="PNG path")
    p.add_argument("--scale", type=int, default=4)
    p.add_argument("--blank-check", action="store_true", help="exit 2 if the screen is one flat colour")
    p.set_defaults(fn=cmd_run)

    p = sub.add_parser("watch", help="print symbol values every N frames")
    _add_common(p)
    p.add_argument("--print", required=True, metavar="SYM,SYM")
    p.add_argument("--every", type=int, default=10)
    p.set_defaults(fn=cmd_watch)

    p = sub.add_parser("symbols", help="list the symbol table")
    _add_common(p)
    p.add_argument("--filter")
    p.set_defaults(fn=cmd_symbols)

    p = sub.add_parser("oam", help="dump sprite attribute memory and LCD registers")
    _add_common(p)
    p.set_defaults(fn=cmd_oam)

    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(gbtest_main())
