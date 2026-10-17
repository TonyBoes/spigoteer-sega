#!/usr/bin/env python3
"""The asm build and the C-fallback build must lay out RAM identically (asm pass, src/asm_cfg.h).

usage: data_layout_check.py [asm_rom [c_rom]]     (default build/game.gb build/game-c.gb)

Checks, from each ROM's .noi and .map:
  - every data symbol (address 0xC000 and up: WRAM, HRAM, IO) is the same in both .noi files, name for name;
  - the _DATA and _INITIALIZED area sizes (and start addresses) in the .map are the same;
  - the symbols the .map lists in RAM are the same.
The differential rig (tests/asm_rig.py) compares WRAM diffs as offsets, which is only valid while this passes.
Exit 0 when identical, 1 with the differences listed.
"""
import re
import sys
from pathlib import Path


def noi_data(path):
    d = {}
    for line in open(path):
        m = re.match(r"DEF (\S+) 0x([0-9A-Fa-f]+)", line)
        if m and int(m[2], 16) & 0xFFFF >= 0xC000 and (int(m[2], 16) >> 16) == 0:
            d[m[1]] = int(m[2], 16)
    return d


def map_areas(path):
    """area name -> [(addr, size)] for the data areas, and every RAM global in the map's symbol tables."""
    areas, syms = {}, {}
    for line in open(path, errors="replace"):
        m = re.match(r"^(_DATA|_INITIALIZED|_BSS|_HRAM\w*)\s+([0-9A-F]{8})\s+([0-9A-F]{8})", line)
        if m:
            areas.setdefault(m[1], []).append((int(m[2], 16), int(m[3], 16)))
            continue
        for v, g in re.findall(r"\b([0-9A-F]{8})\s+(_\w+)", line):
            if 0xC000 <= int(v, 16) <= 0xFFFF:
                syms[g] = int(v, 16)
    return areas, syms


def diff(label, a, b, out):
    for k in sorted(set(a) | set(b)):
        if a.get(k) != b.get(k):
            out.append(f"{label}: {k}: asm {a.get(k) if k in a else 'absent'} vs c {b.get(k) if k in b else 'absent'}")


def main(argv):
    asm = Path(argv[1] if len(argv) > 1 else "build/game.gb")
    cc = Path(argv[2] if len(argv) > 2 else "build/game-c.gb")
    bad = []
    na, nc = noi_data(asm.with_suffix(".noi")), noi_data(cc.with_suffix(".noi"))
    diff(".noi symbol", {k: hex(v) for k, v in na.items()}, {k: hex(v) for k, v in nc.items()}, bad)
    aa, sa = map_areas(asm.with_suffix(".map"))
    ac, sc = map_areas(cc.with_suffix(".map"))
    for area in ("_DATA", "_INITIALIZED"):
        if area not in aa or area not in ac:
            bad.append(f"{area}: missing from a .map")
        elif aa[area] != ac[area]:
            bad.append(f"{area}: asm {[(hex(x), n) for x, n in aa[area]]} vs c {[(hex(x), n) for x, n in ac[area]]}")
    diff(".map symbol", {k: hex(v) for k, v in sa.items()}, {k: hex(v) for k, v in sc.items()}, bad)
    if bad:
        print("DATA LAYOUT DIFFERS between", asm, "and", cc)
        print("\n".join(bad[:60]))
        return 1
    print(f"data layout identical: {len(na)} .noi data symbols, {len(sa)} .map RAM symbols,",
          " ".join(f"{a} {aa[a][0][1]} B" for a in ("_DATA", "_INITIALIZED")))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
