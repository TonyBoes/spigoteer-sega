"""python3 view.py TAG [blank]: renders the stadium neighbourhood (cells 0..36 x 0..20) DMG and Color at x3 into out/stad/tmp/ctx_TAG_{d,c}.png ('blank' drops the piece's blank cells)"""
import sys

import mapctx as M
from mapctx import W

O = str(M.ROOT) + '/out/stad/tmp/'
tag = sys.argv[1]
M.apply(drop_blank=len(sys.argv) > 2)
box = (0, 0, 36, 20)
M.render(W.WORLD, True, box).resize((36 * 24, 20 * 24)).save(O + f'ctx_{tag}_c.png')
M.render(W.WORLD_DMG, False, box).resize((36 * 24, 20 * 24)).save(O + f'ctx_{tag}_d.png')
