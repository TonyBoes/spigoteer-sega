#!/bin/bash
# Incremental-correctness proof for the per-object build (test batch 3, A4), run after a scratch edit:
#   tools/dev/obj_incremental.sh <label>
# Builds game.gb and game-c.gb incrementally in build/ (OBJ=1, whatever objects it already has), then from scratch in out/b_clean (OBJ=1),
# and prints both times (with the load) and whether the sha1 of each ROM matches. build/ must have been built (OBJ=1) before the edit.
cd "$(dirname "$0")/../.." || exit 1
L=${1:-edit}
load() { cut -d' ' -f1 /proc/loadavg; }
s=$(date +%s.%N); l1=$(load)
make OBJ=1 build/game.gb cfall > out/inc_$L.log 2>&1; rc1=$?
t1=$(awk "BEGIN{printf \"%.1f\", $(date +%s.%N) - $s}")
rm -rf out/b_clean out/b_clean_out
s=$(date +%s.%N); l2=$(load)
make OBJ=1 BUILD=out/b_clean OUT=out/b_clean_out out/b_clean/game.gb cfall > out/clean_$L.log 2>&1; rc2=$?
t2=$(awk "BEGIN{printf \"%.1f\", $(date +%s.%N) - $s}")
for r in game game-c; do
  a=$(sha1sum build/$r.gb | cut -c1-12); b=$(sha1sum out/b_clean/$r.gb | cut -c1-12)
  if [ "$a" = "$b" ]; then m=MATCH; else m=DIFFER; fi
  echo "$L $r: incremental $a clean $b $m"
done
echo "$L: incremental rc=$rc1 ${t1}s (load $l1), clean rc=$rc2 ${t2}s (load $l2), objects recompiled incrementally: $(grep -c '  CC ' out/inc_$L.log)"
