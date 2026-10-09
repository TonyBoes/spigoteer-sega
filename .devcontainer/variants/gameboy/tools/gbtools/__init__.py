"""gbtools — helpers for Claude Code working on Game Boy / Game Boy Color ROMs.

    from gbtools import Rom
    with Rom("build/game.gb") as gb:
        gb.run(120)
        gb.press("right", frames=30)
        assert gb.mem("player_x") > 16
        gb.screenshot("out/after.png")

See CLAUDE.md in the project for the workflow; `gbtest --help`, `gbsprite --help`,
`lvl2gb --help`, `gbcheck --help` for the command-line tools.
"""
from .rom import Rom, BUTTONS
from .symbols import load_symbols

__all__ = ["Rom", "BUTTONS", "load_symbols"]
__version__ = "0.1.0"
