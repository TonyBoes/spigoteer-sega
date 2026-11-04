#!/bin/bash
# bv.sh LABEL SRC: scratch-build the ROM with SRC's critic art (a block file, or "cur"; built in out/sc, never in assets/),
# then capture its poses with cap.py into out/cap_LABEL
set -e
R=/workspace/.claude/worktrees/agent-a781dd25b24512d04
L=$1
V=$2
T=$R/docs/dev/concepts/critic_pass_2026-11-03/round4
python3 $T/crit_tool.py build $V $R/out/sc/assets/art/boss/critic.txt
cd $R/out/sc
make > $R/out/sc_make_$L.log 2>&1
tail -1 $R/out/sc_make_$L.log
mkdir -p $R/out/rom_$L
cp build/game.gb build/game.noi $R/out/rom_$L/
cd $R
python3 $T/preview_tools/cap.py out/rom_$L/game.gb out/cap_$L 2>&1 | tail -2
