#!/usr/bin/env python3
"""Compare the skipped tests of a ptest run with the supervisor's baseline (tools/dev/skip_baseline.txt).

    skipcheck.py <results.txt> [baseline]

Prints, always exiting 0 (a skip warning never fails verify):
  line 1  "SKIPS <n> vs <baseline>: OK" | "SKIPS <n> > <baseline>" | "SKIPS <n> < <baseline>"  (+ ", new IDs" when an ID is not in the list)
  then    "newly skipped: <id>" for every skipped ID not in the baseline list, "no longer skipped: <id>" for listed IDs that ran.
verify.sh puts "(skips 58 > 56)" after RESULT: PASS when line 1 is not OK-and-fewer-or-equal-without-new-IDs.
Fewer skips is only a note (the supervisor lowers the baseline).
"""
import sys
from pathlib import Path


def load_baseline(p):
    count, ids = None, set()
    for ln in Path(p).read_text().splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        if ln.startswith("count "):
            count = int(ln.split()[1])
        else:
            ids.add(ln)
    return count, ids


def main(argv):
    res = Path(argv[1])
    base = argv[2] if len(argv) > 2 else str(Path(__file__).with_name("skip_baseline.txt"))
    count, ids = load_baseline(base)
    skipped = set()
    for ln in res.read_text().splitlines():
        if ln.startswith("skipped "):
            skipped.add(ln[len("skipped "):])
    n = len(skipped)
    new = sorted(skipped - ids)
    gone = sorted(ids - skipped)
    if n > count:
        head = f"SKIPS {n} > {count}"
    elif n < count:
        head = f"SKIPS {n} < {count}"
    else:
        head = f"SKIPS {n} vs {count}: OK"
    if new and n <= count:
        head += ", new IDs"
    print(head)
    for i in new:
        print(f"newly skipped: {i}")
    for i in gone:
        print(f"no longer skipped: {i}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
