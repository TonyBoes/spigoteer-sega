#!/bin/bash
# Full verification chain for one branch, replacing the per-branch copies of tests_verify.sh.
#
#   tools/dev/verify.sh <worktree> <name>
#     <worktree>  path to the worktree (absolute, or relative to /workspace), e.g. .claude/worktrees/agent-a85f9c7ee230bc121
#     <name>      short label for the log, e.g. q49
#   Default stages (owner, test batches 1 and 2, 2026-11-09; about N min (pending, test batch 2)):
#     plain make (incremental, up to date when this worktree's build/ is current; FULL=1 uses make -B, a full rebuild), then three stages side by side: pytest on the asm build, make cfall, and the RUN_SLOW double speed / half
#     rate tests; make check runs right after the build (about 1 s).
#   FULL=1 tools/dev/verify.sh <worktree> <name>
#     adds the slow fade stage (RUN_SLOW=1 tests/test_fade_hw.py, about 7 min) and the release-only tests (FULL=1 is
#     visible to pytest: tests marked release_only, now test_release.py::test_make_dist, run only then). Use it for engine,
#     fade, timing or music changes, and before any release.
#   CBUILD=1 tools/dev/verify.sh <worktree> <name>
#     adds the pytest run on the C build (GB_ROM=build/game-c.gb, about 5 min). Only before a porting release, while C tests
#     are on hold. FULL=1 CBUILD=1 together is the old full run.
#   QUICK=1 is accepted and does nothing (it was the default's old name), so old briefs keep working.
#
# Log: $VERIFY_LOGDIR/<name>.log (default /workspace/out/verify; out/ is never committed). Run it in the background.
# Each stage has its own section and a "RESULT <stage>: PASS" or "RESULT <stage>: FAIL" line; the stages that run side by
# side are written out in the fixed order below when they have all finished. The last two lines are always "RESULT: PASS"
# or "RESULT: FAIL (...)" and "END" (the overall verdict waits for every stage and fails if any stage failed), so wait on
# the END marker. The log is short by design; read it whole.
#
# Why the three side-by-side stages do not clash (test batch 2, A4): after make -B every generated file is up to date, so
# make cfall only writes build/game-c.*, build/obj/game-c/ and its flags stamp; the double speed stage builds its own ROM
# in out/dsmr/ and only reads build/game.gb (the patched copies in out/dsoff/ are written by rename, same bytes);
# ptest's own `make release` writes build/release.*. Nothing shares a file, a folder or a port.

set -u
WT=${1:?usage: verify.sh <worktree> <name>}
NAME=${2:?usage: verify.sh <worktree> <name>}
case "$WT" in /*) ;; *) WT=/workspace/$WT ;; esac
LOGDIR=${VERIFY_LOGDIR:-/workspace/out/verify}
mkdir -p "$LOGDIR"
L=$LOGDIR/$NAME.log
: > "$L"
cd "$WT" || { echo "BAD_WORKTREE $WT" >> "$L"; echo "RESULT: FAIL (bad worktree)" >> "$L"; echo END >> "$L"; exit 1; }

PYTEST="python3 -m pytest -q -p no:cacheprovider"
# the parallel runner (tools/dev/ptest.py; --timeout=180 per test is its default); JOBS=1 gives the serial reference. Its last line has "N passed"/"N failed", and it prints FAILED/ERROR lines.
PTEST="python3 tools/dev/ptest.py -j ${JOBS:-8}"
now() { date +%H:%M:%S; }

echo "worktree $WT${FULL:+ (FULL)}${CBUILD:+ (CBUILD)}" >> "$L"
echo "commit $(git rev-parse --short HEAD) on $(git rev-parse --abbrev-ref HEAD)" >> "$L"

# Per-stage output goes to $P/<stage>.out; start/end times to $P/<stage>.t; "section" copies it into the log.
P=$LOGDIR/$NAME.parts
rm -rf "$P"; mkdir -p "$P"
FAILED_STAGES=""
BG_PIDS=""
cleanup() { for p in $BG_PIDS; do kill "$p" 2>/dev/null; done; }
trap 'cleanup; exit 130' INT TERM

# stage_pytest_ok <file>: no FAILED/ERROR line, no "N failed" / "N error(s)" (whole words: "xfailed" is fine), and a total with "N passed"
# (a missing total = pytest died).
stage_pytest_ok() {
  ! grep -qE '^(FAILED|ERROR) |(^|[^a-z])[0-9]+ (failed|errors?)([^a-z]|$)' "$1" && grep -qE '(^|[^a-z])[0-9]+ passed' "$1"
}
# stage_check_ok <file>: both "[dmg] OK" and "[cgb] OK" (a missing line = gbcheck died) and no [model] line with FAIL, FAILED, CRASH or HANG.
stage_check_ok() {
  [ "$(grep -cE '^\[(dmg|cgb)\] OK$' "$1")" -ge 2 ] && ! grep -qiE '^\[(dmg|cgb)\].*(^|[^a-z])(fail|failed|crash|hang)([^a-z]|$)' "$1"
}
# section <stage> <title> <ok-test>: header with the start and end times, the stage's output, its RESULT line.
section() {
  local s=$1 title=$2 okfn=$3 verdict=PASS
  echo "== $title ($(cat "$P/$s.t" 2> /dev/null))" >> "$L"
  cat "$P/$s.out" >> "$L" 2> /dev/null
  $okfn "$P/$s.out" || verdict=FAIL
  echo "RESULT $s: $verdict" >> "$L"
  [ "$verdict" = PASS ] || FAILED_STAGES="$FAILED_STAGES $s"
}
# timed <stage> <command...>: runs the command with its stdout and stderr in $P/<stage>.out and its start-end times in $P/<stage>.t.
timed() {
  local s=$1; shift
  local a; a=$(now)
  "$@" > "$P/$s.out" 2>&1
  echo "$a-$(now)" > "$P/$s.t"
}

# ---- the build: plain make (test batch 2, B3: proven equal to a clean build, with the Makefile's missing prerequisites added); FULL=1 forces make -B ----
BUILD_CMD="make"; [ -n "${FULL:-}" ] && BUILD_CMD="make -B"
a=$(now)
if $BUILD_CMD > /dev/null 2>&1; then
  { echo "== $BUILD_CMD ($a-$(now))"; echo BUILD_OK; echo "RESULT build: PASS"; } >> "$L"
else
  { echo "== $BUILD_CMD ($a-$(now))"; echo BUILD_FAIL; echo "RESULT build: FAIL"; echo "RESULT: FAIL (build)"; echo END; } >> "$L"
  rm -rf "$P"; exit 1
fi

# ---- make check: about 1 s, before the long stages start ----
check_stage() { make check 2>&1 | grep -E "\[(dmg|cgb)\]"; }
timed check check_stage

# ---- the stages that run side by side ----
cfall_stage() { make cfall > /dev/null 2>&1 && echo CFALL_OK || echo CFALL_FAIL; }
slow_stage() { RUN_SLOW=1 $PYTEST tests/test_double_speed.py tests/test_half_rate.py 2>&1 | tail -1; }
pytest_stage() { $PTEST tests 2>&1 | grep -E "^(FAILED|ERROR)|passed|failed"; }
timed cfall cfall_stage &
BG_PIDS="$!"
timed slow slow_stage &
BG_PIDS="$BG_PIDS $!"
timed pytest pytest_stage      # the longest one, in the foreground
for p in $BG_PIDS; do wait "$p"; done
BG_PIDS=""

cfall_ok() { grep -qx CFALL_OK "$1" && ! grep -qx CFALL_FAIL "$1"; }
section pytest "pytest (asm build)" stage_pytest_ok
section cfall "make cfall" cfall_ok
section check "make check" stage_check_ok

# ---- stages that follow the three above ----
if [ -n "${FULL:-}" ]; then
  fade_stage() { RUN_SLOW=1 $PYTEST tests/test_fade_hw.py 2>&1 | tail -1; }
  timed fade fade_stage
  section fade "slow: fade" stage_pytest_ok
fi

if [ -n "${CBUILD:-}" ]; then
  cbuild_stage() { GB_ROM=build/game-c.gb $PTEST tests 2>&1 | grep -E "^(FAILED|ERROR)|passed|failed"; }
  timed cbuild cbuild_stage
  section cbuild "pytest (C build)" stage_pytest_ok
fi

section slow "slow: double speed + half rate" stage_pytest_ok

# Verdict: every stage must have said PASS (the stage checks above are the old precise patterns: pytest prints "N xfailed" /
# "N xpassed" on green runs, so a bare FAIL match is wrong).
if [ -n "$FAILED_STAGES" ]; then
  echo "RESULT: FAIL (failed stages:$FAILED_STAGES)" >> "$L"
else
  echo "RESULT: PASS" >> "$L"
fi
echo END >> "$L"
rm -rf "$P"
