"""python3 sheet6.py: after render_one.py has run for 4e, arr1 and arr2, joins them (4e | arrangement 1 | arrangement 2), DMG row then Color row, x3, into ../milkbar_sheet7.png"""
import subprocess
import sys

TMP = '/workspace/.claude/worktrees/agent-a742552fa3a9454c1/out/mb'
ROOT = '/workspace/.claude/worktrees/agent-a742552fa3a9454c1'
from PIL import Image

items = []
for tag in ('DMG', 'Color'):
    for mode, label in (('arr1', 'arrangement 1'), ('arr3', 'new: building one cell west, cow and sign swapped')):
        im = Image.open(f'{TMP}/r6_{mode}_{tag}.png')
        f = f'{TMP}/r7x3_{mode}_{tag}.png'
        im.resize((im.width * 3, im.height * 3), 0).save(f)
        items.append(f'{label} {tag} x3={f}')
args = [sys.executable, ROOT + '/tools/dev/contact_sheet.py', ROOT + '/docs/dev/proposals/smap_milkbar/milkbar_sheet7.png', '--scale', '1', '--cols', '2',
        '--title', 'milk bar round 4g in the A5 map: arrangement 1 | new (red tick = Sal stop)']
subprocess.run(args + items, check=True)
