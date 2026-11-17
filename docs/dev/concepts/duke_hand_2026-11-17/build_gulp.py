#!/usr/bin/env python3
"""Splice gulp_arm.txt's hand-typed strips (GULP rows 2-14, body columns 24-39) into the approved duke.txt (the version before the
first arm fix, git 67f0e4bd^) and write duke_P1.txt / duke_P2.txt into the directory given (default: next to this file).
Converts only: every pixel of the arm is typed in gulp_arm.txt.   usage: build_gulp.py OLD_DUKE.txt [OUTDIR]"""
import sys
from pathlib import Path

here = Path(__file__).resolve().parent
old = Path(sys.argv[1]).read_text().split("\n")
out = Path(sys.argv[2]) if len(sys.argv) > 2 else here
strips, cur = {}, None
for line in (here / "gulp_arm.txt").read_text().split("\n"):
    if line.startswith("@"):
        cur = strips.setdefault(line[1:].strip(), [])
    elif cur is not None and line and not line.startswith(";"):
        cur.append(line)
g = old.index("@GULP")
for name, rows in strips.items():
    assert len(rows) in (13, 14) and all(len(r) == 16 for r in rows), name
    first = 2 if len(rows) == 13 else 1          # 14 rows: the strip starts at GULP row 1 (a thumb above the fist)
    new = list(old)
    for i, r in enumerate(rows):
        row = new[g + 1 + first + i]
        assert len(row) == 40
        new[g + 1 + first + i] = row[:24] + r
    (out / f"duke_{name}.txt").write_text("\n".join(new))
print("ok")
