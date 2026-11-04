#!/usr/bin/env python3
"""Read-only: the fountain (compose.fountain mask) in each picture against intro_before's, pixel keys compared;
prints the count and bounding box of the differences (spigot state, Sal and his glass are story props).
    audit_fountain.py PICDIR"""
import sys
from pathlib import Path

T = Path(__file__).resolve().parent
sys.path.insert(0, str(T))
from render_v2 import parse   # noqa: E402
from compose import fountain  # noqa: E402

d = Path(sys.argv[1])
ref = parse(d / "intro_before.txt")[1]
for n in ("intro_a", "finale_a", "credits_b"):
    p = parse(d / f"{n}.txt")[1]
    diff = [(x, y) for y in range(104) for x in range(160) if fountain(x, y) and p[y][x] != ref[y][x]]
    if not diff:
        print(n, "same")
        continue
    xs, ys = [x for x, _ in diff], [y for _, y in diff]
    rows = {}
    for x, y in diff:
        rows.setdefault(y // 8, []).append(x)
    print(n, len(diff), "bbox", min(xs), min(ys), max(xs), max(ys),
          "by cell row:", {r: (min(v), max(v), len(v)) for r, v in sorted(rows.items())})
