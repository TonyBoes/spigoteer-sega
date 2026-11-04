#!/usr/bin/env python3
"""Authoring notation -> grid .txt. A convenience for typing, not a drawing tool: every run below is a pixel decision made by hand.

  rl.py IN.rl OUT.txt

IN.rl: '@NAME' starts a block; each following non-empty line is one pixel row written as runs separated by spaces:
'3.' = three wall pixels, '#' = one outline, '8-' = eight skin, '+' plum.  A row shorter than the block width is padded with
wall.  '|' starts a comment.  A line '=NAME' copies that block's rows (my own finished rows; '=FILE:NAME' takes them from
FILE.rl); a line 'rN: runs' then replaces row N (0-15) of the current block.  Lines starting with ';' are copied through.
The topper blocks (HAT_*) are 8 wide, copied as typed.
"""
import re
import sys
from pathlib import Path

W = 32
HERE = Path(__file__).resolve().parent


def row(line):
    out = ""
    for tok in line.split("|")[0].split():
        m = re.fullmatch(r"(\d*)([.\-+#])", tok)
        if not m:
            sys.exit(f"bad run {tok!r} in {line!r}")
        out += m.group(2) * int(m.group(1) or 1)
    if len(out) > W:
        sys.exit(f"row wider than {W} ({len(out)}): {line!r}")
    return out.ljust(W, ".")


def parse(path):
    items, blocks, cur = [], {}, None          # items: ('text', str) | ('block', name)
    for line in Path(path).read_text().splitlines():
        if line.startswith(";") or not line.strip():
            items.append(("text", line))
            continue
        if line.startswith("@"):
            cur = line[1:].strip()
            blocks[cur] = []
            items.append(("text", line))
            items.append(("block", cur))
            continue
        if line.startswith("="):
            ref = line[1:].split("|")[0].strip()
            src = blocks
            if ":" in ref:
                f, ref = ref.split(":")
                src = parse(HERE / f"{f}.rl")[1]
            blocks[cur] += list(src[ref])
            continue
        m = re.match(r"r(\d+):\s*(.*)", line)
        if m:
            blocks[cur][int(m.group(1))] = row(m.group(2))
            continue
        blocks[cur].append(line.strip() if cur.startswith("HAT_") else row(line))
    return items, blocks


def main(src, dst):
    items, blocks = parse(src)
    out = []
    for k, v in items:
        out += [v] if k == "text" else blocks[v]
    Path(dst).write_text("\n".join(out) + "\n")


if __name__ == "__main__":
    main(*sys.argv[1:3])
