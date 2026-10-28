#!/usr/bin/env python3
"""Read out/junit/*.xml (from tools/dev/test_runall.py): slowest tests, time and outcomes per file, skip reasons grouped.
Read-only; prints to stdout.   usage: tools/dev/test_junit_report.py [N]"""
import sys, glob, collections, re
import xml.etree.ElementTree as ET

N = int(sys.argv[1]) if len(sys.argv) > 1 else 30
cases = []
perfile = collections.defaultdict(lambda: collections.Counter())
skips = collections.defaultdict(list)
for x in sorted(glob.glob(sys.argv[2] if len(sys.argv) > 2 else "out/junit/test_*.xml")):
    for tc in ET.parse(x).getroot().iter("testcase"):
        f = (tc.get("classname") or x).split(".")[1] if "." in (tc.get("classname") or "") else x
        t = float(tc.get("time") or 0)
        st = "pass"
        for ch in tc:
            if ch.tag == "skipped":
                st = "xfail" if ch.get("type") == "pytest.xfail" else "skip"
                skips[(f, re.sub(r"\s+", " ", (ch.get("message") or ""))[:110])].append(tc.get("name"))
            elif ch.tag in ("failure", "error"):
                st = "fail"
        cases.append((t, f, tc.get("name"), st))
        perfile[f][st] += 1
        perfile[f]["time"] += t
print("TOTAL cases", len(cases), "time(sum)", round(sum(c[0] for c in cases)), collections.Counter(c[3] for c in cases))
print("\nSLOWEST", N)
for t, f, n, st in sorted(cases, reverse=True)[:N]:
    print(f"{t:7.1f} {f}::{n} {st}")
print("\nPER FILE (sum of case time, cases, skip, fail)")
for f, c in sorted(perfile.items(), key=lambda kv: -kv[1]["time"]):
    print(f"{c['time']:7.1f} {sum(c[k] for k in ('pass','skip','xfail','fail')):5d} sk={c['skip']:3d} xf={c['xfail']} fail={c['fail']} {f}")
print("\nSKIPS grouped")
for (f, m), names in sorted(skips.items(), key=lambda kv: -len(kv[1])):
    print(f"{len(names):4d} {f}: {m}")
