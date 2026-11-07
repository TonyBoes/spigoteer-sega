"""Import this FIRST: puts the A5 layout's scratch world generator (docs/dev/proposals/smap_layout_a5/src: world2, pal, lay_A5) in front of tools/smap_world, so
common.py and every renderer here see the A5 map.  Run docs/dev/proposals/smap_layout_a5/mk_src.py and mk_a5.py once first (they write the scratch files)."""
import os
import sys

ROOT = '/workspace/.claude/worktrees/agent-a742552fa3a9454c1'
os.environ.setdefault('SMAP_LAYOUT', 'lay_A5')
os.environ.setdefault('SMAP_FOG', 'none')
sys.path.insert(0, ROOT + '/docs/dev/proposals/smap_layout_a5/src')
sys.path.insert(1, ROOT + '/tools/smap_world')
