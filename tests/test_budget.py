"""Memory budgets, read from the linker map (no ROM boot): CLAUDE.md says WRAM is nearly exhausted (add no new globals) and ROM0
is nearly full. Until now only a person reading `make`'s output enforced it.

The floors are the numbers of 2026-10-28 (main after patron revision 2) minus a small stated margin, so a real change that
eats bytes must raise the margin here on purpose, in a visible commit:

    WRAM_LO   free 160   (0xC000 up to _DATA's first byte: the shadow OAM's 0xA0 bytes lie below _DATA)   margin 0
    WRAM_HI_0 free 461   (the end of the last variable area up to 0xE000, where the stack's page begins)     margin 16
    ROM0 real free 453   (tools/rom0free.py: 0x4000 minus the end of the last bank-0 area)                  margin 32

These are the numbers `romusage build/game.noi` prints for WRAM_LO / WRAM_HI_0 and `make`'s "ROM0 real" line prints."""
import re

import pytest
from conftest import ROOT

MAP = ROOT / "build" / "game.map"

WRAM_LO_FREE_NOW, WRAM_LO_MARGIN = 160, 0
WRAM_HI0_FREE_NOW, WRAM_HI0_MARGIN = 461, 16
ROM0_FREE_NOW, ROM0_MARGIN = 453, 32


def areas():
    """(name, address, size) of every linker area line of the map."""
    out = []
    for line in MAP.read_text().splitlines():
        m = re.match(r"^(\.?_?\w+)\s+([0-9A-F]{8})\s+([0-9A-F]{8})\s", line)
        if m and not m[1].startswith("_HEADER"):
            out.append((m[1], int(m[2], 16), int(m[3], 16)))
    return out


def wram_numbers():
    a = [x for x in areas() if 0xC000 <= x[1] < 0xE000 and x[2]]
    assert a, "no WRAM area found in the map"
    lo = min(x[1] for x in a) - 0xC000
    hi_end = max(x[1] + x[2] for x in a)
    return lo, 0xE000 - hi_end


def rom0_free():
    end = max((adr + n for _, adr, n in areas() if adr < 0x4000 and n), default=0)
    return 0x4000 - end


@pytest.mark.skipif(not MAP.exists(), reason="needs build/game.map (make)")
def test_wram_lo_free_has_not_shrunk():
    lo, _ = wram_numbers()
    assert lo >= WRAM_LO_FREE_NOW - WRAM_LO_MARGIN, f"WRAM_LO free {lo} B, floor {WRAM_LO_FREE_NOW - WRAM_LO_MARGIN}"


@pytest.mark.skipif(not MAP.exists(), reason="needs build/game.map (make)")
def test_wram_hi_0_free_has_not_shrunk():
    _, hi = wram_numbers()
    assert hi >= WRAM_HI0_FREE_NOW - WRAM_HI0_MARGIN, (
        f"WRAM_HI_0 free {hi} B, floor {WRAM_HI0_FREE_NOW - WRAM_HI0_MARGIN}: no new WRAM globals (use the unions, story_scratch or BOSS_OWN)")


@pytest.mark.skipif(not MAP.exists(), reason="needs build/game.map (make)")
def test_rom0_real_free_has_not_shrunk():
    free = rom0_free()
    assert free >= ROM0_FREE_NOW - ROM0_MARGIN, f"ROM0 real free {free} B, floor {ROM0_FREE_NOW - ROM0_MARGIN} (tools/rom0free.py)"


@pytest.mark.skipif(not MAP.exists(), reason="needs build/game.map (make)")
def test_the_numbers_match_the_tools():
    """The map reading here equals tools/rom0free.py's (the Makefile's line)."""
    import subprocess
    out = subprocess.run(["python3", str(ROOT / "tools" / "rom0free.py"), str(MAP)], capture_output=True, text=True, check=True).stdout
    assert int(re.search(r"(\d+) bytes free", out).group(1)) == rom0_free()
