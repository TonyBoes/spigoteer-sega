#!/usr/bin/env python3
"""Every C function's (bank, address), statics included, for one built ROM: the rig (tests/asm_rig.py) and the profiler need them
and the linker's .noi lists globals only.

usage: asm_symtab.py [rom]            (default build/game.gb; build/game-c.gb works the same)

Each src/*.c is compiled again with the flags of that ROM's build (build/<variant>.flags) to a listing in
out/symtab/<variant>/lst/, the label offsets inside each module's area are read from it, and a global's absolute address in the
.noi anchors the area (a static's address = a global's address - its offset + the static's offset). Writes
out/symtab/<variant>/symtab.json: {"name" or "module:name": [bank, address, module]}, and the statics of data areas in
data.json: {"module:_name": address} (WRAM statics such as mugs.c _oam_next). Nothing under build/ is touched.
"""
import glob
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAB = re.compile(r"^\s+([0-9A-F]{8})\s+\d+\s+(_[A-Za-z_]\w*)(::?)\s*$")
AREA = re.compile(r"^\s+\d+\s+\.area\s+(\S+)")


def noi(path):
    d = {}
    for line in open(path):
        m = re.match(r"DEF (\S+) 0x([0-9A-Fa-f]+)", line)
        if m:
            d[m[1]] = int(m[2], 16)
    return d


def variant_of(rom):
    return Path(rom).stem


def compile_lists(rom, lst_dir):
    flags = (ROOT / "build" / f"{variant_of(rom)}.flags").read_text().split()
    flags = [f for f in flags if not f.startswith(("-Wl-", "-Wm-"))] + ["-Wm-yc", "-Wm-yt0x1B", "-autobank"]
    hu = ROOT / "third_party" / "hugedriver" / "include"
    lst_dir.mkdir(parents=True, exist_ok=True)

    def one(src):
        o = lst_dir / (Path(src).stem + ".o")
        subprocess.run(["lcc", *flags, f"-I{ROOT}/build", f"-I{ROOT}/src", f"-I{hu}", "-c", "-o", str(o), src],
                       cwd=lst_dir, check=True, capture_output=True)

    with ThreadPoolExecutor(os.cpu_count() or 4) as ex:
        list(ex.map(one, sorted(glob.glob(str(ROOT / "src" / "*.c")))))


def build(rom, lst_dir):
    N = noi(Path(rom).with_suffix(".noi"))
    funcs, data, bad = {}, {}, []
    for lst in sorted(glob.glob(str(lst_dir / "*.lst"))):
        mod = os.path.basename(lst)[:-4]
        area, labs, pend = None, [], None
        for line in open(lst, errors="replace"):
            m = AREA.match(line)
            if m:
                area, pend = m[1], None
                continue
            m = LAB.match(line)
            if m and area:
                pend = (area, m[2], m[3] == "::", int(m[1], 16))
                continue
            if pend and re.match(r"^\s+[0-9A-F]{8}\s", line):
                is_data = re.search(r"\.(db|dw|ascii|asciz|byte|word|ds)\b", line)
                labs.append(pend + (("data",) if is_data else ()))
                pend = None
        for ar in {a for a, *_ in labs}:
            L = [x for x in labs if x[0] == ar]
            anchors = [(x[1], x[3]) for x in L if x[2] and x[1] in N]
            if not anchors:
                if ar.startswith("_CODE"):
                    bad.append((mod, ar))
                continue
            base = N[anchors[0][0]] - anchors[0][1]
            for n, off in anchors[1:]:
                if N[n] - off != base:
                    bad.append((mod, ar, n, "mismatch"))
            for x in L:
                full = base + x[3]
                if ar.startswith("_CODE") and len(x) == 4:    # a data table is never a function (a hook would patch the ROM)
                    funcs[x[1] if x[2] else f"{mod}:{x[1]}"] = (full >> 16, full & 0xFFFF, mod)
                elif ar in ("_DATA", "_INITIALIZED"):
                    data[f"{mod}:{x[1]}"] = full & 0xFFFF
    # GBDK library code: the _HOME area of the map (code only)
    home = None
    for line in open(Path(rom).with_suffix(".map"), errors="replace"):
        m = re.match(r"^_HOME\s+([0-9A-F]{8})\s+([0-9A-F]{8})", line)
        if m:
            home = (int(m[1], 16), int(m[1], 16) + int(m[2], 16))
            break
    known = {(b, a) for b, a, _ in funcs.values()}
    for n, v in N.items():
        if home and n.startswith("_") and home[0] <= v < home[1] and (v >> 16, v & 0xFFFF) not in known and n not in funcs:
            funcs[n] = (0, v & 0xFFFF, "gbdk")
    return funcs, data, bad


def main(argv):
    rom = Path(argv[1] if len(argv) > 1 else ROOT / "build" / "game.gb")
    out = ROOT / "out" / "symtab" / variant_of(rom)
    lst = out / "lst"
    compile_lists(rom, lst)
    funcs, data, bad = build(rom, lst)
    (out / "symtab.json").write_text(json.dumps({k: list(v) for k, v in funcs.items()}))
    (out / "data.json").write_text(json.dumps(data))
    print(f"{out}: {len(funcs)} functions, {len(data)} data labels, {len(bad)} problems")
    for b in bad[:20]:
        print("  ", b)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
