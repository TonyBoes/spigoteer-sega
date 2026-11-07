"""python3 sheet8.py: after render_one.py for arr3, bldA, bldB: 4g | windows A | windows B; the building close-up x4 (DMG row, Color row), then the A5 map x3 (DMG row, Color row);
writes ../milkbar_sheet11.png"""
import subprocess
import sys

from PIL import Image

ROOT = '/workspace/.claude/worktrees/agent-a742552fa3a9454c1'
TMP = ROOT + '/out/mb'
MODES = (('n1', '4j silver (COW idx 1), no arrow'), ('b1', 'borrowed FACTORY silver, no arrow'), ('bA', 'A coffee sign'), ('bB', 'B diner sign'))
items = []
for kind, scale, sfx in (('close', 4, 'x4'), ('map', 3, 'x3')):
    for tag in ('DMG', 'Color'):
        for mode, label in MODES:
            f0 = f'{TMP}/r6_{mode}_close{tag}.png' if kind == 'close' else f'{TMP}/r6_{mode}_{tag}.png'
            im = Image.open(f0)
            f = f'{TMP}/r11_{kind}_{mode}_{tag}.png'
            im.resize((im.width * scale, im.height * scale), 0).save(f)
            items.append(f'{label} {kind} {tag} {sfx}={f}')
args = [sys.executable, ROOT + '/tools/dev/contact_sheet.py', ROOT + '/docs/dev/proposals/smap_milkbar/milkbar_sheet11.png', '--scale', '1', '--cols', '4',
        '--title', 'milk bar round 4k: 4j silver | building on the FACTORY palette | A coffee sign | B diner sign (cows and bottle stay white) (close-up x4, then the A5 map x3)']
subprocess.run(args + items, check=True)
