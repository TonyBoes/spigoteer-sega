"""Load symbol tables so tests can say `gb.mem("player_x")` instead of 0xC0A3.

RGBDS (`rgblink -n game.sym`) writes lines like
    00:c000 wPlayerX
GBDK (`lcc -Wl-j`, the NoICE file `game.noi`) writes lines like
    DEF _player_x 0xC0A3          (bank 0)
    DEF _level_data 0x14000       (bank 1 at 0x4000: bank in the high bits)

Both are looked up next to the ROM: game.gb -> game.sym, then game.noi.
GBDK names are stored both with and without the leading underscore.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

_SYM_LINE = re.compile(r"^\s*(?:([0-9A-Fa-f]{2,3}):)?([0-9A-Fa-f]{4})\s+(\S+)")
_NOI_LINE = re.compile(r"^\s*DEF\s+(\S+)\s+0[xX]([0-9A-Fa-f]+)")


def _parse_sym(text: str) -> dict[str, tuple[int, int]]:
    out = {}
    for line in text.splitlines():
        line = line.split(";", 1)[0]
        m = _SYM_LINE.match(line)
        if m:
            bank = int(m.group(1), 16) if m.group(1) else 0
            out[m.group(3)] = (bank, int(m.group(2), 16))
    return out


def _parse_noi(text: str) -> dict[str, tuple[int, int]]:
    out = {}
    for line in text.splitlines():
        m = _NOI_LINE.match(line)
        if not m:
            continue
        name, value = m.group(1), int(m.group(2), 16)
        bank, addr = value >> 16, value & 0xFFFF
        out[name] = (bank, addr)
        if name.startswith("_") and name[1:] not in out:
            out[name[1:]] = (bank, addr)
    return out


def load_symbols(rom_path: str | os.PathLike, explicit: str | os.PathLike | None = None) -> dict[str, tuple[int, int]]:
    """Return {name: (bank, address)}. Empty dict if no symbol file exists."""
    candidates = [Path(explicit)] if explicit else []
    stem = Path(rom_path).with_suffix("")
    candidates += [stem.with_suffix(".sym"), stem.with_suffix(".noi")]
    for p in candidates:
        if p.is_file():
            text = p.read_text(errors="replace")
            return _parse_noi(text) if p.suffix.lower() == ".noi" else _parse_sym(text)
    return {}
