#!/bin/bash
# Full verification chain for one branch, replacing the per-branch copies of tests_verify.sh.
#
#   tools/dev/verify.sh <worktree> <name>
#     <worktree>  path to the worktree (absolute, or relative to /workspace), e.g. .claude/worktrees/agent-a85f9c7ee230bc121
#     <name>      short label for the log, e.g. q49
#
# Log: /workspace/out/verify/<name>.log (out/ is never committed). Run it in the background; it takes about 20 min.
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
step() { echo "== $1 ($(date +%H:%M:%S))" >> "$L"; }

echo "worktree $WT" >> "$L"
echo "commit $(git rev-parse --short HEAD) on $(git rev-parse --abbrev-ref HEAD)" >> "$L"

step "make -B"
if make -B > /dev/null 2>&1; then echo BUILD_OK >> "$L"; else
  echo BUILD_FAIL >> "$L"; echo "RESULT: FAIL (build)" >> "$L"; echo END >> "$L"; exit 1; fi

step "make cfall"
make cfall > /dev/null 2>&1 && echo CFALL_OK >> "$L" || echo CFALL_FAIL >> "$L"

step "pytest (asm build)"
$PYTEST tests --timeout=180 --timeout-method=thread 2>&1 | grep -E "^(FAILED|ERROR)|passed|failed" >> "$L"

step "make check"
make check 2>&1 | grep -E "\[(dmg|cgb)\]" >> "$L"

step "slow: fade"
RUN_SLOW=1 $PYTEST tests/test_fade_hw.py 2>&1 | tail -1 >> "$L"

step "pytest (C build)"
GB_ROM=build/game-c.gb $PYTEST tests --timeout=180 --timeout-method=thread 2>&1 | grep -E "^(FAILED|ERROR)|passed|failed" >> "$L"

step "slow: double speed + half rate"
RUN_SLOW=1 $PYTEST tests/test_double_speed.py tests/test_half_rate.py 2>&1 | tail -1 >> "$L"

# Verdict. Precise patterns only: pytest prints "N xfailed" / "N xpassed" on green runs, so a bare FAIL match is wrong.
#  - BUILD_FAIL / CFALL_FAIL markers
#  - pytest short-summary lines that start with FAILED or ERROR
#  - pytest totals with "N failed" or "N error(s)" as whole words (not "xfailed")
#  - make check lines whose verdict word is FAIL, FAILED, CRASH or HANG
#  - all four pytest steps must have printed a total with "passed" (a missing total = pytest died)
#  - make check must print both "[dmg] OK" and "[cgb] OK" (gbtools/check.py prints exactly "[model] OK" or "[model] FAIL";
#    a missing line = gbcheck died)
FLAGS=$(grep -nE '^(BUILD_FAIL|CFALL_FAIL)$|^(FAILED|ERROR) |(^|[^a-z])[0-9]+ (failed|errors?)([^a-z]|$)' "$L")
FLAGS="$FLAGS
$(grep -niE '^\[(dmg|cgb)\].*(^|[^a-z])(fail|failed|crash|hang)([^a-z]|$)' "$L")"
SUITES=$(grep -cE '(^|[^a-z])[0-9]+ passed' "$L")
CHECKS=$(grep -cE '^\[(dmg|cgb)\] OK$' "$L")
FLAGS=$(printf '%s\n' "$FLAGS" | grep .)
if [ -n "$FLAGS" ] || [ "$SUITES" -lt 4 ] || [ "$CHECKS" -lt 2 ]; then
  N=$(printf '%s\n' "$FLAGS" | grep -c .)
  echo "RESULT: FAIL ($N flagged lines; $SUITES of 4 pytest totals; $CHECKS of 2 make check OKs)" >> "$L"
else
  echo "RESULT: PASS" >> "$L"
fi
echo END >> "$L"
