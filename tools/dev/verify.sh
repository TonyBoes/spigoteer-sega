#!/bin/bash
# Full verification chain for one branch, replacing the per-branch copies of tests_verify.sh.
#
#   tools/dev/verify.sh <worktree> <name>
#     <worktree>  path to the worktree (absolute, or relative to /workspace), e.g. .claude/worktrees/agent-a85f9c7ee230bc121
#     <name>      short label for the log, e.g. q49
#   Default stages (owner, test batches 1 and 2, 2026-11-09; about 3 min):
#     plain make (incremental; make -B instead with FULL=1, or when the branch, its uncommitted changes or its untracked files touch the
#     Makefile or a generator under tools/, see build_mode below; the log has a "build mode:" line with the reason), then make release and make cfall beside make, then side by side pytest on the asm build and the RUN_SLOW double speed / half
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
# Skips (batch 3, S2): tools/dev/skip_baseline.txt (the supervisor's file) holds the expected asm pytest skips (56); more skips, or a skipped ID not listed, adds "(skips 58 > 56)" after RESULT and lists the IDs in a "skipped tests" section. Never a failure.
# Log: $VERIFY_LOGDIR/<name>.log (default /workspace/out/verify; out/ is never committed). Run it in the background.
# Each stage has its own section and a "RESULT <stage>: PASS" or "RESULT <stage>: FAIL" line; the stages that run side by
# side are written out in the fixed order below when they have all finished. The last two lines are always "RESULT: PASS"
# or "RESULT: FAIL (...)" and "END" (the overall verdict waits for every stage and fails if any stage failed), so wait on
# the END marker. The log is short by design; read it whole.
#
# Why the stages do not clash (test batch 2, A4, corrected in C2b): make, make release and make cfall run side by side and the pytest stage
# starts only when all three are done (pytest reads build/game.gb, build/release.gb and build/game-c.gb; an earlier version ran cfall beside
# pytest and the C-ROM tests skipped or read a stale ROM). Beside pytest only the double speed stage runs: it builds its own ROM in out/dsmr/
# and only reads build/game.gb (the patched copies in out/dsoff/ are written by rename, same bytes). make check runs before them.
# C2: `make prep` first, then `make` and `make release` at the same time: both only read the generated files and write their own
# build/<variant>.* and build/obj/<variant>/ (own hUGEDriver.o copy, own lcc tempdir, own flags stamp, own link log).

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
# Fix 1 (owner, after batch 2): plain make is only trusted while the build rules and generators are unchanged. The branch (git diff main...HEAD),
# the uncommitted changes and untracked files are checked: if any of them is the Makefile or a "generator file", the build is make -B.
# Generator files = every tools/ path that make itself names, i.e. the scripts its recipes run (tools/gen_*.py, palettes2c.py, ...) and every
# tools/ prerequisite of its build/ rules (gen_art.py, harmony.py, taiko_chart.py, cannon_table.py, tools/smap_world/*, tools/artifacts/palette_plan/*,
# tools/dev/extra_combos.py, the B3a additions ...), read from `make -pn all` (wildcards already expanded), so the list follows the Makefile.
# A tools/ module a generator imports without the Makefile naming it would be missed; the import closure of every generator was checked in
# batch 2 (A2): none.
build_mode() {  # prints "<command>|<reason>"
  [ -n "${FULL:-}" ] && { echo "make -B|FULL=1"; return; }
  local changed gens hit
  git rev-parse --verify -q "${VERIFY_BASE:-main}" > /dev/null 2>&1 || { echo "make -B|no main branch to compare with"; return; }
  changed=$( { git diff --name-only "${VERIFY_BASE:-main}...HEAD"; git diff --name-only HEAD; git ls-files --others --exclude-standard; } 2> /dev/null | sort -u)
  # only the rules whose target is under build/ (the generated files): not make test (ptest.py), atlas, map-atlas, dist
  gens=$(make -pn all 2> /dev/null | awk '/^[^#\t.][^:=]*:/ { t = ($0 ~ /^build\//) } t' | grep -oE 'tools/[A-Za-z0-9_./-]+' | sort -u)
  [ -z "$gens" ] && { echo "make -B|could not read the generator list from make"; return; }
  hit=$(printf '%s\n' "$changed" | grep -Fx -e Makefile -f <(printf '%s\n' "$gens") | head -5 | tr '\n' ' ')
  if [ -n "$hit" ]; then echo "make -B|changed vs main: $hit"; else echo "make|no change to the Makefile or a generator vs main"; fi
}
MODE=$(build_mode)
BUILD_CMD=${MODE%%|*}
if [ -n "${VERIFY_MODE_ONLY:-}" ]; then echo "$MODE"; exit 0; fi
echo "build mode: $BUILD_CMD (${MODE#*|})" >> "$L"
# Test batch 2 follow-up, C2: `make release` (ptest's prebuild, about 75 s) runs beside `make` instead of after it. Both need the same generated
# sources, so `make prep` (the Makefile target: every prerequisite of every ROM except the lcc step) runs first and once, with -B when the
# mode says so; then the ROMs are rebuilt at the same time by two plain makes that find everything current and write only their own files
# (build/game.*, build/obj/game/ against build/release.*, build/obj/release/). Under -B the two ROMs are removed first, so lcc really reruns.
kill_tree() {  # kill_tree <pid>: the process and everything below it
  local c; for c in $(pgrep -P "$1" 2> /dev/null); do kill_tree "$c"; done
  kill "$1" 2> /dev/null
}
cleanup() { for p in $BG_PIDS $REL_PID $CF_PID; do kill_tree "$p"; done; }
REL_PID=""; CF_PID=""
build_fail() { { echo "== $BUILD_CMD ($a-$(now))"; echo BUILD_FAIL; echo "RESULT build: FAIL"; echo "RESULT: FAIL (build)"; echo END; } >> "$L"; cleanup; rm -rf "$P"; exit 1; }
a=$(now)
PREP_CMD="make prep"; [ "$BUILD_CMD" = "make -B" ] && PREP_CMD="make -B prep"
$PREP_CMD > /dev/null 2>&1 || build_fail
[ "$BUILD_CMD" = "make -B" ] && rm -f build/game.gb build/release.gb build/game-c.gb
release_stage() { make release 2>&1 | tail -15; [ "${PIPESTATUS[0]}" -eq 0 ] && echo RELEASE_OK || echo RELEASE_FAIL; }
timed release release_stage &
REL_PID=$!
# C2b: pytest reads build/game-c.gb (test_asm_*, test_mugs_asm, test_catch_asm, test_story_map_world skip without it, and read a stale or
# half-written one if make cfall runs beside them), so the C ROM is built here too, beside make and make release, and pytest starts only
# when all three are done. Its files (build/game-c.*, build/obj/game-c/, build/game-c.flags, build/game-c_link.log) are its own.
cfall_stage() { make cfall 2>&1 | tail -15; [ "${PIPESTATUS[0]}" -eq 0 ] && echo CFALL_OK || echo CFALL_FAIL; }
timed cfall cfall_stage &
CF_PID=$!
if make > /dev/null 2>&1; then
  { echo "== $BUILD_CMD ($a-$(now))"; echo BUILD_OK; echo "RESULT build: PASS"; } >> "$L"
else
  build_fail
fi

# ---- make check: about 1 s, before the long stages start ----
check_stage() { make check 2>&1 | grep -E "\[(dmg|cgb)\]"; }
timed check check_stage

# ---- the stages that run side by side ----
slow_stage() { RUN_SLOW=1 $PYTEST tests/test_double_speed.py tests/test_half_rate.py 2>&1 | tail -1; }
pytest_stage() { $PTEST tests 2>&1 | grep -E "^(FAILED|ERROR)|passed|failed"; }
timed slow slow_stage &
BG_PIDS="$!"
wait "$REL_PID"; REL_PID=""      # the release and C builds (started beside make) must be finished: pytest reads build/release.gb and build/game-c.gb
wait "$CF_PID"; CF_PID=""
release_ok() { grep -qx RELEASE_OK "$1" && ! grep -qx RELEASE_FAIL "$1"; }
cfall_ok() { grep -qx CFALL_OK "$1" && ! grep -qx CFALL_FAIL "$1" && [ -s build/game-c.gb ]; }   # C2b guard: a C ROM must exist (make cfall said it is current)
if ! release_ok "$P/release.out" || ! cfall_ok "$P/cfall.out"; then   # pytest never starts without them (it would skip or read stale ROMs)
  release_ok "$P/release.out" || section release "make release" release_ok
  cfall_ok "$P/cfall.out" || section cfall "make cfall" cfall_ok
  echo "RESULT: FAIL (failed stages:$FAILED_STAGES)" >> "$L"; echo END >> "$L"
  cleanup; rm -rf "$P"; exit 1
fi
timed pytest pytest_stage      # the longest one, in the foreground
for p in $BG_PIDS; do wait "$p"; done
BG_PIDS=""

section release "make release" release_ok
section pytest "pytest (asm build)" stage_pytest_ok
section cfall "make cfall" cfall_ok
section check "make check" stage_check_ok
# Test batch 3, S2: the skip baseline (tools/dev/skip_baseline.txt, owned by the supervisor). More skips than it, or a skipped ID it does not list,
# never fails the run: it goes after "RESULT: PASS" and the newly skipped IDs are listed in their own section.
SKIP_NOTE=""
skip_rp=$(sed -n 's/.*; results \([^ ]*\)$/\1/p' "$P/pytest.out" 2> /dev/null | tail -1)   # ptest's last line ends "; results <path>"
if [ -n "$skip_rp" ] && [ -f "$skip_rp" ]; then
  python3 tools/dev/skipcheck.py "$skip_rp" > "$P/skips.out" 2>&1 || echo "SKIPS: skipcheck failed" >> "$P/skips.out"
else
  echo "SKIPS: no results file in the pytest output, skip baseline not checked" > "$P/skips.out"
fi
echo "== skipped tests vs tools/dev/skip_baseline.txt" >> "$L"; cat "$P/skips.out" >> "$L"
skip_head=$(grep -m1 "^SKIPS" "$P/skips.out")
case "$skip_head" in
  *">"*|*"new IDs"*) SKIP_NOTE=" (${skip_head/SKIPS/skips})" ;;   # more skips than the baseline, or an unlisted ID
  "SKIPS: "*) SKIP_NOTE=" (skip baseline not checked)" ;;
esac                                                              # equal, or fewer without a new ID: only the section line

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
  echo "RESULT: FAIL (failed stages:$FAILED_STAGES)$SKIP_NOTE" >> "$L"
else
  echo "RESULT: PASS$SKIP_NOTE" >> "$L"
fi
echo END >> "$L"
rm -rf "$P"
