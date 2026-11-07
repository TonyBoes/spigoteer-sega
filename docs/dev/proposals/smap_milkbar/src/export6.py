"""python3 export6.py: run with MB_PASTURE=1; writes the two round 4f canvases as indexed PNGs (DMG and Color) into out/mb/lint for the skill's lint"""
import export as E

import cow_a5 as A

for a in (1, 2, 3):
    E.write(f'arr{a}', A.build(a))
for s in 'AB':
    E.write('bld' + s, A.build(3, s))
for r in (1, 2, 3):
    E.write(f'roof{r}', A.build(3, 'A', r))
for n in (1, 2):
    E.write(f'new{n}', A.build(3, 'A', 2, n))
for n, nm in ((3, 'signA'), (4, 'signB'), (5, 'signB2')):
    E.write(nm, A.build(3, 'A', 2, n, borrow='factory'))
