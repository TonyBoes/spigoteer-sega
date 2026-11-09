#!/bin/bash
# variant builds both ways: one-shot (os) and OBJ=1 (obj); prints sha1 + time
# (test batch 3, A1 proof) the test builds' variants, one-shot vs OBJ=1: tests/test_show_ext.py (needs out/showcgb_src/factory.txt: run that test once
# first), tests/test_practice_art.py and the double speed test's -DAUTO_MR build. Prints sha1 and time; each pair must have the same hash.
cd "$(dirname "$0")/../.." || exit 1
export SPIGOTEER_TEST_SHOW_CGB="factory=$PWD/out/showcgb_src/factory.txt"
run() { # label builddir extra-args...
  l=$1; b=$2; shift 2
  rm -rf $b ${b}_out
  s=$(date +%s)
  make "$@" BUILD=$b OUT=${b}_out $b/game.gb > $b.log 2>&1; rc=$?
  echo "$l rc=$rc $(( $(date +%s) - s ))s load $(cut -d' ' -f1 /proc/loadavg) $(sha1sum $b/game.gb | cut -c1-40)"
}
for mode in os obj; do
  if [ $mode = obj ]; then O="OBJ=1"; else O=""; fi
  run "show_ext  $mode" out/v_show_$mode $O
  run "practice  $mode" out/v_pa_$mode $O PRACTICE_ART_DIRS=tests/data/practice_art
  run "dsmr      $mode" out/v_ds_$mode $O "DEBUGFLAGS=-DDEBUG_MENU -DAUTO_MR"
done
