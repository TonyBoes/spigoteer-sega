"""Import this FIRST: puts the A5 layout's scratch world generator (docs/dev/proposals/smap_layout_a5/src: world2, pal, lay_A5) in front of tools/smap_world, so
common.py and every renderer here see the A5 map.  Run docs/dev/proposals/smap_layout_a5/mk_src.py and mk_a5.py once first (they write the scratch files).
env MB_PASTURE=1 (proposal copy only, nothing in the repo's layout files changes): the hay field is removed (lay.FIELDS = [], the four hay bales taken out of
lay.SCENERY) and the cow venue becomes a one-cell stub, so that the renderer can paste the milk bar piece (and its pasture) over the world afterwards."""
import os
import sys

ROOT = '/workspace/.claude/worktrees/agent-a742552fa3a9454c1'
os.environ.setdefault('SMAP_LAYOUT', 'lay_A5')
os.environ.setdefault('SMAP_FOG', 'none')
sys.path.insert(0, ROOT + '/docs/dev/proposals/smap_layout_a5/src')
sys.path.insert(1, ROOT + '/tools/smap_world')
sys.path.insert(2, ROOT + '/docs/dev/proposals/smap_milkbar/src')

if os.environ.get('MB_PASTURE') == '1':
    import decor
    import lay_A5 as lay
    lay.FIELDS = []
    lay.SCENERY = [s for s in lay.SCENERY if s[0] is not decor.HAY]
    lay.VENUES = dict(lay.VENUES)
    lay.VENUES['cow'] = ('cow_stub', lay.VENUES['cow'][1])

if os.environ.get('MB_SILVER') == '1':                       # proposal only: COW index 1 (chrome e8e0f0) becomes a silver; nothing else in the palette table changes
    import pal as _pal
    _pal.PALS['cow'][1] = 'b0b8c8'
