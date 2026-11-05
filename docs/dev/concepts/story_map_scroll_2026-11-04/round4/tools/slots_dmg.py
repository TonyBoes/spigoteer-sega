"""Slots a fixed tile -> slot plan needs for the DMG data set (late world through the merge table).
python3 slots_dmg.py MERGE.json"""
import json
import sys

import render2 as R
import slots as SL
import stats2 as S

mp = {tuple(tuple(r) for r in a): tuple(tuple(r) for r in b) for a, b in json.load(open(sys.argv[1]))}
sg = S.sig_grid(R.LATE)
tg = [[mp.get(t, t) for t in r] for r in sg]
print("DMG trimmed late world: tiles, slots needed (greedy), max conflicts:", SL.slots(tg))
