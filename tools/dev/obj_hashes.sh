#!/bin/bash
# Proof script for the per-object build (test batch 3, A2/A3): builds game, release and cfall in a fresh BUILD dir and prints the sha1 of each ROM.
#   tools/dev/obj_hashes.sh <builddir> <jobs> [oneshot]
# With "oneshot" it uses the default one-shot lcc build (the reference), otherwise OBJ=1 with OBJJOBS=<jobs>. Run from the repo root;
# <builddir> and <builddir>_out are deleted first. Every hash must be the same for every <jobs> and <builddir>, and equal to the one-shot's.
cd "$(dirname "$0")/../.." || exit 1
B=${1:?builddir}; J=${2:?jobs}; MODE=${3:-obj}
rm -rf "$B" "${B}_out"
if [ "$MODE" = oneshot ]; then ARGS=(); else ARGS=(OBJ=1 OBJJOBS="$J"); fi
echo "load before: $(cut -d' ' -f1-3 /proc/loadavg)"
s=$(date +%s)
make "${ARGS[@]}" BUILD="$B" OUT="${B}_out" "$B/game.gb" release cfall > "$B.log" 2>&1
rc=$?
echo "rc=$rc mode=$MODE jobs=$J dir=$B wall=$(( $(date +%s) - s ))s load after: $(cut -d' ' -f1-3 /proc/loadavg)"
sha1sum "$B/game.gb" "$B/release.gb" "$B/game-c.gb"
