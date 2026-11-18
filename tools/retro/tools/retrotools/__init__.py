"""retrotools — test harness for GB/GBC, SMS, Game Gear and NES ROMs.

    from retrotools import Rom
    with Rom("build/sms/game.sms") as r:
        r.run(120)
        r.press("right", frames=30)
        assert r.mem("player_x") > 16

Driver: stable-retro (fast, deterministic, headless). Gate: `retrocheck`, which
runs MesenCE's cycle-accurate test runner. When they disagree, MesenCE is right.
"""
from .rom import Rom, SYSTEMS, system_for
from .symbols import load_symbols

__all__ = ["Rom", "SYSTEMS", "system_for", "load_symbols"]
__version__ = "0.1.0"
