"""Build the before | after sheets (x3, Color over DMG) and the 1x sheet from out/shots/{before,after}. Usage: python3 sheets.py WT
(WT = the worktree; reads WT/out/shots, writes the PNGs next to this file)."""
import os
import subprocess
import sys

WT = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
B, A = os.path.join(WT, 'out/shots/before'), os.path.join(WT, 'out/shots/after')
CS = os.path.join(WT, 'tools/dev/contact_sheet.py')
SETS = {
    'sheet_sasquatch.png': ('SASQUATCH cameo (his game poses HAPPY, DUCK, cone; the intro valve). Pairs: before | after, Color row over DMG row, x3',
                            [('PRE_LUMBER', 3, 40), ('PRE_LUMBER', 4, 40), ('POST_LUMBER', 2, 60), ('POST_LUMBER', 2, 150),
                             ('POST_LUMBER', 3, 40), ('POST_LUMBER', 4, 40)]),
    'sheet_leo.png': ('LEO cameo (his game poses WALK, HAPPY, crown). Pairs: before | after, Color row over DMG row, x3',
                      [('PRE_ZOO', 4, 40), ('POST_ZOO', 1, 40), ('POST_ZOO', 2, 40), ('POST_ZOO', 3, 40)]),
    'sheet_ufo.png': ('UFO beam-up (the story-map UFO + a new hand-drawn beam). Pairs: before | after, Color row over DMG row, x3',
                      [('PRE_SPACE', 1, 36), ('PRE_SPACE', 1, 60), ('PRE_SPACE', 1, 130), ('PRE_SPACE', 2, 60)]),
}


def f(d, m, s, p, t):
    return os.path.join(d, f'{m}_{s}_p{p}_t{t}.png')


allx1 = []
for out, (title, shots) in SETS.items():
    items = []
    for i in range(0, len(shots), 2):
        pair = shots[i:i + 2]
        for m, name in (('cgb', 'Color'), ('dmg', 'DMG')):
            for s, p, t in pair:
                lab = f'{s} p{p} f{t}'
                items += [f'{name} BEFORE {lab}={f(B, m, s, p, t)}', f'{name} AFTER {lab}={f(A, m, s, p, t)}']
                if m == 'cgb':
                    allx1.append(f'{s} p{p} f{t}={f(A, "cgb", s, p, t)}')
                    allx1.append(f'DMG={f(A, "dmg", s, p, t)}')
            if len(pair) == 1:
                pass
    subprocess.run(['python3', CS, os.path.join(HERE, out), '--scale', '3', '--cols', '4', '--title', title] + items, check=True)
subprocess.run(['python3', CS, os.path.join(HERE, 'sheet_1x.png'), '--scale', '1', '--cols', '6',
                '--title', 'AFTER at 1x (in-game size): Color, DMG'] + allx1, check=True)
