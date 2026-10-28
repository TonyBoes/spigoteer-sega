#!/usr/bin/env python3
"""Run every tests/test_*.py as its own pytest process (N at a time), junit XML per file in out/junit/.
Read-only for the repo: writes only under out/. Used by the test review (per-test durations, skip reasons).
usage: tools/dev/test_runall.py [-j 8]"""
import subprocess, sys, pathlib, concurrent.futures as cf, time

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "out" / "junit"
OUT.mkdir(parents=True, exist_ok=True)
jobs = int(sys.argv[sys.argv.index("-j") + 1]) if "-j" in sys.argv else 8


def run(f):
    t = time.time()
    with open(OUT / (f.stem + ".log"), "w") as log:
        subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={OUT / (f.stem + '.xml')}",
                        "--timeout=1500", str(f)], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    return f.name, time.time() - t


files = sorted((ROOT / "tests").glob("test_*.py"))
with cf.ThreadPoolExecutor(jobs) as ex:
    for name, dt in ex.map(run, files):
        print(f"{dt:7.1f}s {name}", flush=True)
(OUT / "ALLDONE").write_text("done")
