#!/bin/bash
# Full verification chain for one branch, replacing the per-branch copies of tests_verify.sh.
#
#   tools/dev/verify.sh <worktree> <name>
#     <worktree>  path to the worktree (absolute, or relative to /workspace), e.g. .claude/worktrees/agent-a85f9c7ee230bc121
#     <name>      short label for the log, e.g. q49
#   Default stages (owner, test batch 1, 2026-11-09; about 7 min): make -B, make cfall, pytest on the asm build, make check,
#     and the RUN_SLOW double speed / half rate tests.
#   FULL=1 tools/dev/verify.sh <worktree> <name>
#     adds the slow fade stage (RUN_SLOW=1 tests/test_fade_hw.py, about 7 min). Use it for engine, fade, timing or music
#     changes, and before any release.
#   CBUILD=1 tools/dev/verify.sh <worktree> <name>
#     adds the pytest run on the C build (GB_ROM=build/game-c.gb, about 5 min). Only before a porting release, while C tests
#     are on hold. FULL=1 CBUILD=1 together is the old full run (about 20 min).
#   QUICK=1 is accepted and does nothing (it was the default's old name), so old briefs keep working.
#
# Log: /workspace/out/verify/<name>.log (out/ is never committed). Run it in the background.
# The last two lines are always "RESULT: PASS" or "RESULT: FAIL (...)" and "END", so wait on the END marker.
# The log is short by design; read it whole.

set -u
WT=${1:?usage: verify.sh <worktree> <name>}
NAME=${2:?usage: verify.sh <worktree> <name>}
case "$WT" in /*) ;; *) WT=/workspace/$WT ;; esac
LOGDIR=/workspace/out/verify
mkdir -p "$LOGDIR"
L=$LOGDIR/$NAME.log
: > "$L"
cd "$WT" || { echo "BAD_WORKTREE $WT" >> "$L"; echo "RESULT: FAIL (bad worktree)" >> "$L"; echo END >> "$L"; exit 1; }

PYTEST="python3 -m pytest -q -p no:cacheprovider"
# the parallel runner (tools/dev/ptest.py; --timeout=180 per test is its default); JOBS=1 gives the serial reference. Its last line has "N passed"/"N failed", and it prints FAILED/ERROR lines.
PTEST="python3 tools/dev/ptest.py -j ${JOBS:-8}"
step() { echo "== $1 ($(date +%H:%M:%S))" >> "$L"; }

echo "worktree $WT${FULL:+ (FULL)}${CBUILD:+ (CBUILD)}" >> "$L"
echo "commit $(git rev-parse --short HEAD) on $(git rev-parse --abbrev-ref HEAD)" >> "$L"

step "make -B"
if make -B > /dev/null 2>&1; then echo BUILD_OK >> "$L"; else
  echo BUILD_FAIL >> "$L"; echo "RESULT: FAIL (build)" >> "$L"; echo END >> "$L"; exit 1; fi

step "make cfall"
make cfall > /dev/null 2>&1 && echo CFALL_OK >> "$L" || echo CFALL_FAIL >> "$L"

step "pytest (asm build)"
$PTEST tests 2>&1 | grep -E "^(FAILED|ERROR)|passed|failed" >> "$L"

step "make check"
make check 2>&1 | grep -E "\[(dmg|cgb)\]" >> "$L"

if [ -n "${FULL:-}" ]; then
step "slow: fade"
RUN_SLOW=1 $PYTEST tests/test_fade_hw.py 2>&1 | tail -1 >> "$L"
fi

if [ -n "${CBUILD:-}" ]; then
step "pytest (C build)"
GB_ROM=build/game-c.gb $PTEST tests 2>&1 | grep -E "^(FAILED|ERROR)|passed|failed" >> "$L"
fi

step "slow: double speed + half rate"
RUN_SLOW=1 $PYTEST tests/test_double_speed.py tests/test_half_rate.py 2>&1 | tail -1 >> "$L"

# Verdict. Precise patterns only: pytest prints "N xfailed" / "N xpassed" on green runs, so a bare FAIL match is wrong.
#  - BUILD_FAIL / CFALL_FAIL markers
#  - pytest short-summary lines that start with FAILED or ERROR
#  - pytest totals with "N failed" or "N error(s)" as whole words (not "xfailed")
#  - make check lines whose verdict word is FAIL, FAILED, CRASH or HANG
#  - every pytest step that ran (2 by default, +1 for FULL=1, +1 for CBUILD=1) must have printed a total with "passed" (a missing total = pytest died)
#  - make check must print both "[dmg] OK" and "[cgb] OK" (gbtools/check.py prints exactly "[model] OK" or "[model] FAIL";
#    a missing line = gbcheck died)
FLAGS=$(grep -nE '^(BUILD_FAIL|CFALL_FAIL)$|^(FAILED|ERROR) |(^|[^a-z])[0-9]+ (failed|errors?)([^a-z]|$)' "$L")
FLAGS="$FLAGS
$(grep -niE '^\[(dmg|cgb)\].*(^|[^a-z])(fail|failed|crash|hang)([^a-z]|$)' "$L")"
SUITES=$(grep -cE '(^|[^a-z])[0-9]+ passed' "$L")
NSUITES=2; [ -n "${FULL:-}" ] && NSUITES=$((NSUITES+1)); [ -n "${CBUILD:-}" ] && NSUITES=$((NSUITES+1))
CHECKS=$(grep -cE '^\[(dmg|cgb)\] OK$' "$L")
FLAGS=$(printf '%s\n' "$FLAGS" | grep .)
if [ -n "$FLAGS" ] || [ "$SUITES" -lt $NSUITES ] || [ "$CHECKS" -lt 2 ]; then
  N=$(printf '%s\n' "$FLAGS" | grep -c .)
  echo "RESULT: FAIL ($N flagged lines; $SUITES of $NSUITES pytest totals; $CHECKS of 2 make check OKs)" >> "$L"
else
  echo "RESULT: PASS" >> "$L"
fi
echo END >> "$L"
