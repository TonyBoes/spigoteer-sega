#!/bin/bash
# bv.sh VER: scratch-build the ROM with version VER's critic art (in out/sc, never in assets/), capture its poses
set -e
R=/workspace/.claude/worktrees/agent-af7a9596251cca7e4
V=$1
python3 $R/docs/dev/concepts/critic_pass_2026-11-03/round2/crit_tool.py build $V $R/out/sc/assets/art/boss/critic.txt
cd $R/out/sc
make > $R/out/sc_make_$V.log 2>&1
tail -1 $R/out/sc_make_$V.log
mkdir -p $R/out/rom_$V
cp build/game.gb build/game.noi $R/out/rom_$V/
cd $R
python3 out/cap.py out/rom_$V/game.gb out/cap_$V 2>&1 | tail -2
