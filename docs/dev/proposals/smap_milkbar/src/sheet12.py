"""python3 sheet8.py: after render_one.py for arr3, bldA, bldB: 4g | windows A | windows B; the building close-up x4 (DMG row, Color row), then the A5 map x3 (DMG row, Color row);
writes ../milkbar_sheet12.png"""
import subprocess
import sys

from PIL import Image

ROOT = '/workspace/.claude/worktrees/agent-a742552fa3a9454c1'
TMP = ROOT + '/out/mb'
MODES = (('bA', 'A on factory'), ('cA', 'A on base, tea cell (34,59) merged'))
items = []
for kind, scale, sfx in (('close', 4, 'x4'), ('map', 3, 'x3')):
    for tag in ('DMG', 'Color'):
        for mode, label in MODES:
            f0 = f'{TMP}/r6_{mode}_close{tag}.png' if kind == 'close' else f'{TMP}/r6_{mode}_{tag}.png'
            im = Image.open(f0)
            f = f'{TMP}/r12_{kind}_{mode}_{tag}.png'
            im.resize((im.width * scale, im.height * scale), 0).save(f)
            items.append(f'{label} {kind} {tag} {sfx}={f}')
args = [sys.executable, ROOT + '/tools/dev/contact_sheet.py', ROOT + '/docs/dev/proposals/smap_milkbar/milkbar_sheet12.png', '--scale', '1', '--cols', '2',
        '--title', 'milk bar round 4k: A coffee sign, building on factory | on base (tea cell merged); then the tea house cell before/after x6']
for tag in ('before', 'after'):
    im = Image.open(f'{TMP}/r12_tea_{tag}.png')
    f = f'{TMP}/r12x6_tea_{tag}.png'
    im.resize((im.width * 6, im.height * 6), 0).save(f)
    items.append(f'tea house cells (33..35, 58..60) {tag} Color x6={f}')
subprocess.run(args + items, check=True)
