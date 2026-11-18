"""Symbol files -> {name: (bank, cpu_address)}, looked up next to the ROM.

  game.noi  GBDK / SDCC (NoICE):  DEF _player_x 0xC0A3        bank in bits 16+
  game.sym  RGBDS / WLA-DX:       00:c0a3 wPlayerX
  game.mlb  Mesen labels (llvm-mos writes these): R:20:player_x
            R = NES internal RAM (CPU $0000-$07FF), W/S = PRG RAM at $6000,
            G = register (CPU address), P = PRG ROM (offset, not a CPU address)

GBDK names are stored with and without their leading underscore.
"""
from __future__ import annotations

import re
from pathlib import Path

_SYM = re.compile(r"^\s*(?:([0-9A-Fa-f]{2,3}):)?([0-9A-Fa-f]{4})\s+(\S+)")
_NOI = re.compile(r"^\s*DEF\s+(\S+)\s+0[xX]([0-9A-Fa-f]+)")
_MLB = re.compile(r"^([A-Za-z]{1,2}):([0-9A-Fa-f]+)(?:-[0-9A-Fa-f]+)?:([^:]+)")
_MLB_BASE = {"R": 0x0000, "W": 0x6000, "S": 0x6000, "G": 0x0000}


def _parse_sym(text):
    out = {}
    for line in text.splitlines():
        m = _SYM.match(line.split(";", 1)[0])
        if m:
            out[m.group(3)] = (int(m.group(1), 16) if m.group(1) else 0, int(m.group(2), 16))
    return out


def _parse_noi(text):
    out = {}
    for line in text.splitlines():
        m = _NOI.match(line)
        if m:
            v = int(m.group(2), 16)
            out[m.group(1)] = (v >> 16, v & 0xFFFF)
            if m.group(1).startswith("_"):
                out.setdefault(m.group(1)[1:], (v >> 16, v & 0xFFFF))
    return out


def _parse_mlb(text):
    out = {}
    for line in text.splitlines():
        m = _MLB.match(line.strip())
        if m and m.group(1).upper() in _MLB_BASE:
            out[m.group(3).strip()] = (0, _MLB_BASE[m.group(1).upper()] + int(m.group(2), 16))
    return out


def symbol_file(rom_path):
    """The symbol file next to the ROM, if any. llvm-mos names it <stem>.mlb."""
    p = Path(rom_path)
    for cand in (p.with_suffix(".sym"), p.with_suffix(".noi"), p.with_suffix(".mlb"), Path(str(p) + ".mlb")):
        if cand.is_file():
            return cand
    return None


def load_symbols(rom_path, explicit=None):
    p = Path(explicit) if explicit else symbol_file(rom_path)
    if not p or not p.is_file():
        return {}
    text = p.read_text(errors="replace")
    return {".noi": _parse_noi, ".mlb": _parse_mlb}.get(p.suffix.lower(), _parse_sym)(text)
