#!/usr/bin/env python3
"""Split an edited boss sheet (the Palette Plan's download, img/boss_<name>_sheet.png) back into house-ASCII blocks.

    python3 tools/artifacts/palette_plan/boss_split.py <name> <edited.png>   -> prints each changed block, @NAME + rows

The layout is build.py's boss_layout (blocks in file order, rows of at most 168 px, 8 px apart), so block sizes must
not change. Colours map back by palette index: 0 the wall '.', 1-3 and 4-6 (the topper's own colours) '-', '+', '#'.
It writes nothing: the supervisor pastes the blocks into assets/art/boss/<name>.txt.
"""
import os, sys
from PIL import Image

name, path = sys.argv[1:3]
sys.argv = sys.argv[:1]                           # build.py reads its own argv (the atlas dir)
here = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(here, "build.py")).read()
ns = {"__file__": os.path.join(here, "build.py")}
exec(src.rsplit("\nfor i, v in enumerate(venues):", 1)[0], ns)   # all but the page loop (the tabs loop before it only writes S)
blocks = ns["boss_blocks"](name)
pos, _ = ns["boss_layout"](blocks)
im = Image.open(path)
if im.mode != "P":
    sys.exit("expected the indexed PNG the page gives (mode P); got %s" % im.mode)
for (bn, rows), (bx, by) in zip(blocks, pos):
    w = max(len(r) for r in rows)
    new = ["".join(".-+#"[(im.getpixel((bx + x, by + y)) - 1) % 3 + 1] if im.getpixel((bx + x, by + y)) else "." for x in range(w))
           for y in range(len(rows))]
    if new != [r.ljust(w, ".") for r in rows]:
        print("@" + bn); print("\n".join(new)); print()
