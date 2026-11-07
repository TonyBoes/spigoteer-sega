"""python3 export6.py: run with MB_PASTURE=1; writes the two round 4f canvases as indexed PNGs (DMG and Color) into out/mb/lint for the skill's lint"""
import export as E

import cow_a5 as A

for a in (1, 2):
    E.write(f'arr{a}', A.build(a))
