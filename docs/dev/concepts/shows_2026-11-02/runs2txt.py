#!/usr/bin/env python3
"""Editor aid, not an art tool: turns a hand-written run list into the 16-wide grid text (the pixels are the ones typed).

  runs2txt.py IN.runs OUT.txt

A frame is 24 lines, frames are separated by a blank line. A line lists runs `c:text` separated by spaces (c = the
column in hex 0-f, text = the pixels written from that column on: `.` transparent, `-` `+` `#` the indices 1 2 3);
later runs overwrite earlier ones; a lone `.` is an empty row. Lines starting with `;` are comments. A line that is
already a 16-char row is passed through, so grids and runs can be mixed.
"""
import sys
from pathlib import Path

src = Path(sys.argv[1])
out, cur, nframes = [], [], 0


def flush():
    global cur, nframes
    if cur:
        nframes += 1
        if len(cur) != 24:
            sys.exit(f"{src}: frame {nframes} has {len(cur)} rows, not 24")
        out.extend(cur)
        out.append("")
        cur = []


for ln, line in enumerate(src.read_text().splitlines(), 1):
    line = line.rstrip()
    if line.startswith(";"):
        continue
    if not line.strip():
        flush()
        continue
    if len(line) == 16 and " " not in line and ":" not in line:
        cur.append(line)
        continue
    row = ["."] * 16
    if line.strip() != ".":
        for run in line.split():
            col, txt = run.split(":", 1)
            c = int(col, 16)
            for i, ch in enumerate(txt):
                if c + i > 15:
                    sys.exit(f"{src}:{ln}: run {run} leaves the 16 px")
                row[c + i] = ch
    cur.append("".join(row))
flush()
Path(sys.argv[2]).write_text("\n".join(out))
