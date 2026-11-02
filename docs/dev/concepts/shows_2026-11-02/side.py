#!/usr/bin/env python3
"""side.py FILE: print a show file's frames side by side with row numbers (reading aid)."""
import sys
from pathlib import Path

fr, cur = [], []
for l in Path(sys.argv[1]).read_text().splitlines() + [""]:
    if l.startswith(";"):
        continue
    if l.strip() == "":
        if cur:
            fr.append(cur)
            cur = []
    else:
        cur.append(l.rstrip())
print("    " + " ".join(f"{'F' + str(i):<16}" for i in range(len(fr))))
for y in range(max(len(f) for f in fr)):
    print(f"{y:2d}  " + " ".join(f[y] if y < len(f) else " " * 16 for f in fr))
