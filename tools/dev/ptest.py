#!/usr/bin/env python3
"""Dependency-free parallel pytest runner (pytest-xdist is not installed and PyPI is blocked).

    tools/dev/ptest.py [-j N] [--timeout SECS] [--log FILE] [--record] [--no-prebuild] [pytest args...]

Collects the tests the way pytest would (`--collect-only`, so -k / -m / paths / node ids work), splits them into N
shards balanced by the per-test timings in tests/durations.json, runs N `python3 -m pytest` processes at once and
merges the results: every FAILED / ERROR line, the totals, one combined log. Exit status is non-zero if any shard
failed, was killed, or collected nothing it should have. GB_ROM and the rest of the environment pass through.

Shard safety: each shard gets PTEST_WORKER=<k> (and PTEST_SHARDS=<n>) in its environment, and its own junit file and
log under out/ptest/<run>/. Tests that must not run twice at once are pinned to shard 0 of phase 1 (PINNED below).
Whole files are kept in one unit unless a file is too big for a shard; then it is cut into contiguous chunks.

    --record   after the run, rewrite tests/durations.json from this run's per-test times (run it serially, -j 1, on a
               quiet machine; the file only balances shards, it never changes a result).
    PTEST_TIMEOUT_METHOD=signal / PTEST_TEST_TIMEOUT=SECS (env): the per-test timeout method and limit (default thread, 180). The C-build stage uses signal:
               a hung test then fails alone; the thread method kills the whole shard process and loses its junit file and every result in it.

    -j 1       the same collection and merge with a single shard: the serial reference for comparing result sets.

Result sets: out/ptest/<run>/results.txt has one "<outcome> <nodeid>" line per test, sorted: diff two runs' files.
Ctrl-C, SIGTERM and --timeout kill every child process group (no orphans).
"""
import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DURATIONS = ROOT / "tests" / "durations.json"
# Test files that touch a shared resource outside out/ (the dist/ directory, make's shared build tree) and so run on one shard only.
PINNED = {"tests/test_release.py"}
DEFAULT_TIMEOUT_PER_TEST = ["--timeout=180", "--timeout-method=thread"]

children = []
logs = []


def kill_all(*_):
    for p in children:
        if p.poll() is None:
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass


def on_signal(signum, _frame):
    kill_all()
    print(f"\nptest: signal {signum}, children killed", file=sys.stderr)
    sys.exit(130)


def release_users():
    """Test files that read build/release.gb or run `make release` (test_build works in a scratch copy, test_release is the dist test)."""
    pat = re.compile(r"release_built|release\.gb|\"release\"")
    return {f"tests/{p.name}" for p in (ROOT / "tests").glob("*.py") if pat.search(p.read_text())} - PINNED - {"tests/test_build.py"}


def collect(pytest_args):
    r = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider", *pytest_args],
                       cwd=ROOT, capture_output=True, text=True)
    ids = [ln.strip() for ln in r.stdout.splitlines() if "::" in ln and not ln.startswith((" ", "="))]
    if r.returncode not in (0, 5) or not ids:
        sys.stdout.write(r.stdout[-3000:] + r.stderr[-2000:])
        sys.exit("ptest: collection failed")
    return ids


def plan(ids, jobs, dur):
    """Units (contiguous runs of node ids of one file, with a weight), then LPT into `jobs` shards."""
    tests = dur.get("tests", {})
    files = dur.get("files", {})
    counts = dur.get("counts", {})
    # A test the file does not list is new (--record lists every test, small ones too), so it is planned as slow, not as 0.05 s:
    # the file's known average per test (at least NEW_MIN), or NEW_FILE for a file the record never saw.
    NEW_MIN, NEW_FILE = 1.0, 5.0

    def w(i):
        if i in tests:
            return tests[i]
        if not counts:                           # an old-format file: nothing says which tests are small, keep the old guess
            return dur.get("default", 0.05)
        f = i.split("::")[0]
        if f in counts and counts[f]:
            return max(files.get(f, 0) / counts[f], NEW_MIN)
        return NEW_FILE

    by_file = {}
    for i in ids:
        by_file.setdefault(i.split("::")[0], []).append(i)
    total = sum(w(i) for i in ids)
    target = total / jobs
    units = []                                   # (weight, [ids], pinned)
    for f, lst in by_file.items():
        fw = sum(w(i) for i in lst)
        if f in PINNED or jobs == 1 or fw <= target * 0.45:
            units.append((fw, lst, f in PINNED))
            continue
        chunk, cw = [], 0.0
        for i in lst:
            chunk.append(i)
            cw += w(i)
            if cw >= target * 0.35:
                units.append((cw, chunk, False))
                chunk, cw = [], 0.0
        if chunk:
            units.append((cw, chunk, False))
    shards = [[0.0, []] for _ in range(jobs)]
    pinned_shard = 0
    for wt, lst, pinned in (u for u in units if u[2]):
        shards[pinned_shard][0] += wt
        shards[pinned_shard][1].append(lst)
    for wt, lst, _p in sorted((u for u in units if not u[2]), key=lambda u: -u[0]):
        s = min(shards, key=lambda s: s[0])
        s[0] += wt
        s[1].append(lst)
    return shards


def parse_junit(path):
    """{nodeid: (outcome, seconds)} from a shard's junit file; outcome is passed / failed / error / skipped."""
    out = {}
    if not path.is_file():
        return out
    for tc in ET.parse(path).getroot().iter("testcase"):
        cls = tc.get("classname", "")
        parts = cls.split(".")
        k = next((n for n, p in enumerate(parts) if p.startswith("test_")), None)
        if k is None:
            continue
        nid = "/".join(parts[:k]) + "/" + parts[k] + ".py::" + "::".join(parts[k + 1:] + [tc.get("name")])
        nid = nid.lstrip("/")
        oc = "passed"
        for ch in tc:
            if ch.tag in ("failure", "error"):
                oc = "failed" if ch.tag == "failure" else "error"
            elif ch.tag == "skipped":
                oc = "skipped"
        t = float(tc.get("time") or 0)
        if nid in out:                          # a test that failed in call and teardown shows twice
            o0, t0 = out[nid]
            oc = o0 if o0 in ("failed", "error") else oc
            t += t0
        out[nid] = (oc, t)
    return out


def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("-j", "--jobs", type=int, default=int(os.environ.get("JOBS", "8")))
    ap.add_argument("--timeout", type=float, default=0, help="kill everything after this many seconds")
    ap.add_argument("--log", default=None)
    ap.add_argument("--record", action="store_true")
    ap.add_argument("--no-prebuild", action="store_true")
    ap.add_argument("-h", "--help", action="store_true")
    a, rest = ap.parse_known_args()
    if a.help:
        print(__doc__)
        return 0
    jobs = max(1, a.jobs)
    pytest_args = rest or ["tests"]
    if not any(x.startswith("--timeout") for x in pytest_args):
        # PTEST_TIMEOUT_METHOD=signal (the C-build stage): a hung test fails alone. The default "thread" method kills the whole shard process
        # (os._exit), which loses that shard's junit file and every result in it: the "coverage differs between runs" of the C-build runs.
        pytest_args += ["--timeout=" + os.environ.get("PTEST_TEST_TIMEOUT", "180"), "--timeout-method=" + os.environ.get("PTEST_TIMEOUT_METHOD", "thread")]

    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)
    t0 = time.time()
    run = time.strftime("%Y%m%d-%H%M%S") + f"-{os.getpid()}"
    rdir = ROOT / "out" / "ptest" / run
    rdir.mkdir(parents=True, exist_ok=True)

    if jobs > 1 and not a.no_prebuild:
        # `make release` is run by several test files; built once here it is a no-op for them, so shards never rebuild build/ together.
        r = subprocess.run(["make", "release"], cwd=ROOT, capture_output=True, text=True)
        if r.returncode:
            print("ptest: make release failed\n" + r.stdout[-1500:] + r.stderr[-1500:])
            return 2

    dur = json.loads(DURATIONS.read_text()) if DURATIONS.is_file() else {}
    ids = collect(pytest_args)
    # Two phases: `make dist` (tests/test_release.py) deletes and rebuilds build/release.gb, which the files in release_users() read or
    # `make release` themselves, so those run after it; everything else, dist included, runs together in phase 1.
    users = release_users()
    phases = [[i for i in ids if i.split("::")[0] not in users], [i for i in ids if i.split("::")[0] in users]]
    deadline = t0 + a.timeout if a.timeout else None
    # options only: the selection comes from each shard's argsfile of node ids
    opts = [x for x in pytest_args if not ("::" in x or (ROOT / x).exists())]
    results, rc, shard_info, timed_out = {}, 0, [], False
    for ph, pids in enumerate(phases):
        if not pids or timed_out:
            continue
        shards = plan(pids, jobs, dur)
        print(f"ptest: phase {ph + 1}: {len(pids)} tests, {jobs} shard(s); est. " + " ".join(f"{s[0]:.0f}s" for s in shards), flush=True)
        procs = []
        for k, (wt, units) in enumerate(shards):
            lst = [i for u in units for i in u]
            if not lst:
                continue
            name = f"p{ph + 1}s{k}"
            af = rdir / f"{name}.args"
            af.write_text("\n".join(lst) + "\n")
            env = dict(os.environ, PTEST_WORKER=str(k), PTEST_SHARDS=str(len(shards)), PTEST_PHASE=str(ph + 1), PYTHONUNBUFFERED="1")
            log = open(rdir / f"{name}.log", "w")
            cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-rfE", f"--junitxml={rdir / f'{name}.xml'}", *opts, f"@{af}"]
            p = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            children.append(p)
            procs.append((name, k, p, log, wt))
        while any(p.poll() is None for _, _, p, _, _ in procs):
            time.sleep(0.5)
            if deadline and time.time() > deadline:
                timed_out = True
                kill_all()
                break
        for name, k, p, log, wt in procs:
            p.wait()
            log.close()
            res = parse_junit(rdir / f"{name}.xml")
            results.update(res)
            logs.append(rdir / f"{name}.log")
            shard_info.append(f"{name}:{sum(t for _o, t in res.values()):.0f}s/{wt:.0f}s")
            if p.returncode not in (0, 1, 5):
                rc = max(rc, 2)
                print(f"ptest: shard {name} ended abnormally (exit {p.returncode}); see {rdir / f'{name}.log'}")
            elif p.returncode == 1:
                rc = max(rc, 1)
    missing = [i for i in ids if i not in results]
    count = {}
    for oc, _t in results.values():
        count[oc] = count.get(oc, 0) + 1
    (rdir / "results.txt").write_text("".join(f"{results[i][0]} {i}\n" for i in sorted(results)))
    # combined log
    combined = Path(a.log) if a.log else rdir / "combined.log"
    with open(combined, "w") as c:
        for lg in logs:
            c.write(f"===== {lg.stem} =====\n" + lg.read_text())
    bad = sorted(i for i, (oc, _t) in results.items() if oc in ("failed", "error"))
    for i in bad:
        print(f"{results[i][0].upper() if results[i][0] == 'failed' else 'ERROR'} {i}")
    wall = time.time() - t0
    try:
        load = os.getloadavg()[0]
    except OSError:
        load = -1
    print("ptest: shard test seconds / estimate: " + " ".join(shard_info))
    summ = ", ".join(f"{n} {k}" for k, n in sorted(count.items()))
    print(f"ptest: {summ}; {len(missing)} not reported; {wall:.0f}s wall, load {load:.1f}; log {combined}; results {rdir / 'results.txt'}")
    if timed_out:
        print("ptest: TIMEOUT, children killed")
        rc = max(rc, 3)
    if missing and not timed_out:
        print(f"ptest: {len(missing)} collected tests have no result, e.g. {missing[:3]}")
        rc = max(rc, 2)
    if bad:
        rc = max(rc, 1)

    if a.record:
        allt = {i: t for i, (_o, t) in results.items()}
        small = sorted(t for t in allt.values() if t < 0.1)
        tests = {i: round(t, 2) for i, t in allt.items()}      # every test, so a test missing from the file is known to be new
        counts = {}
        for i in allt:
            counts[i.split("::")[0]] = counts.get(i.split("::")[0], 0) + 1
        files = {}
        for i, t in tests.items():
            f = i.split("::")[0]
            files[f] = round(files.get(f, 0) + t, 2)
        for i, t in allt.items():
            if t < 0.1:
                f = i.split("::")[0]
                files[f] = round(files.get(f, 0) + t, 2)
        DURATIONS.write_text(json.dumps({"note": "seconds per test, from `tools/dev/ptest.py -j 1 --record` (balances shards only)",
                                         "default": round(small[len(small) // 2], 3) if small else 0.05, "total": round(sum(files.values()), 1), "files": dict(sorted(files.items(), key=lambda kv: -kv[1])), "counts": dict(sorted(counts.items())),
                                         "tests": dict(sorted(tests.items()))}, indent=0, separators=(",", ":")) + "\n")
        print(f"ptest: wrote {DURATIONS}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
