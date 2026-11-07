"""python3 audit_anim.py [--apply] : audit of every smap_anim item (all but the falls, which falls_cave.py handles) against the integrated default map.
The items are built on a scene read from the integrated map (as anim_light.py does, with the airbase offset patched in).  Building an item APPLIES its new static art (the 'new static tiles') to
that scene, and some items carry `edits` (art new even at rest).  So the difference between the scene before and after all_items, plus every item's `edits`, is exactly the approved frame 0 art
the integrated map does not have yet.  Prints a table per item: animated cells, missing cells (the map's tile differs from the approved frame 0), and the animated tile cells the engine table
would rewrite.  With --apply the missing art is pasted into the integrated worlds (Color = typed index, DMG through the light map for water cells) by `apply_missing(W, WORLDS)` (used by mapctx)."""
import sys
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
ANIM = HERE.parent / "smap_anim"
sys.path.insert(0, str(HERE))


def load_items(mapctx):
    sys.path.insert(1, str(ANIM))
    text = (ANIM / "items.py").read_text()
    DX, DY = mapctx.AT_OVERRIDE["mountain"][0] - 9, mapctx.AT_OVERRIDE["mountain"][1] - 36
    for old, new in (("MTN_DX = -3 ", f"MTN_DX = {DX} "),
                     ("a5.tile(14 + MTN_DX, 38)", f"a5.tile(14 + MTN_DX, {38 + DY})"),
                     ("a5.tile(13 + MTN_DX, 38)", f"a5.tile(13 + MTN_DX, {38 + DY})"),
                     ("(14 + MTN_DX, 38)", f"(14 + MTN_DX, {38 + DY})"),
                     ("(13 + MTN_DX, 38)", f"(13 + MTN_DX, {38 + DY})"),
                     ("a5, (16, 262)", f"a5, (16, {262 + 8 * DY})"),
                     ("focus=(76, 300, 100, 316)", f"focus=(76, {300 + 8 * DY}, 100, {316 + 8 * DY})")):
        assert old in text, old
        text = text.replace(old, new)
    mod = types.ModuleType("items")
    mod.__file__ = str(ANIM / "items.py")
    sys.modules["items"] = mod
    exec(compile(text, str(ANIM / "items.py"), "exec"), mod.__dict__)
    return mod


def build(mapctx):
    """-> (before scene px, pal, built items, scene after).  The falls item is left out."""
    import anim_lib as A
    mod = load_items(mapctx)
    a5 = A.load_a5()
    before_px, before_pal = a5.px.copy(), [r[:] for r in a5.pal]
    its = [mod.water(a5, "vsubtle"), mod.fountain(a5), mod.bunting(a5), mod.stadium_flag(a5), mod.airbase(a5), mod.smoke_lodge(a5), mod.smoke_igloo(a5), mod.smoke_factory(a5),
           mod.cows(a5), mod.logs(a5)]
    return before_px, before_pal, its, a5


def missing(mapctx):
    """{item key: {(x, y): index}} new pixels, {item key: {(cx, cy): pal}} palette changes, plus the items"""
    import numpy as np
    before_px, before_pal, its, a5 = build(mapctx)
    diff = np.argwhere(a5.px != before_px)
    # which item made each change is not tracked by the scene: report per cell, and attribute edits by item
    px = {(int(x), int(y)): int(a5.px[y, x]) for y, x in diff}
    pal = {(cx, cy): a5.pal[cy][cx] for cy in range(a5.ch) for cx in range(a5.cw) if a5.pal[cy][cx] != before_pal[cy][cx]}
    edits = {it.key: dict(it.edits) for it in its if it.edits}
    return px, pal, edits, its, a5


LIGHT_WATER = {0: 0, 1: 0, 2: 1, 3: 2}                 # anim_light.py: on a water cell 0->0, 1->0, 2->1, 3->2 (log cells 3->3)


if __name__ == "__main__":
    import mapctx as M
    px, pal, edits, its, a5 = missing(M)
    cells = {}
    for (x, y), v in px.items():
        cells.setdefault((x // 8, y // 8), []).append(((x, y), v))
    for it in its:
        res = it.resolve()
        ac = sorted({c for (a, b, cl) in res for c in cl})
        ed = sorted({(x // 8, y // 8) for (x, y) in it.edits})
        print(f"{it.key}: {len(it.anims)} tile anims, animated cells {len(ac)}: {ac[:12]}{'...' if len(ac) > 12 else ''}")
        print("   edit cells (new even at rest):", ed)
    print("cells whose static art differs from the integrated map (after the items' statics):", len(cells))
    for c in sorted(cells):
        print("  ", c, len(cells[c]), "px")
    print("palette changes:", pal)
