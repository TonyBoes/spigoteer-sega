"""The approved animation art that the integrated map did not carry (stage 1l audit, audit_anim.py): the NEW STATIC tiles of smap_anim/items.py (frame 0 of the water glints, the six logs
sunk low and the six removed logs, the lodge's white smoke cells, the cow tails).  Everything is read from items.py itself (exactly as approved, nothing retyped here): the scene the items are
built on is the integrated map, building the items applies their statics to it, and the pixels that changed (plus every item's `edits`) are pasted into both data sets.
  Color: the typed index.  DMG light water: the glint and water cells read idx 1 -> 0, 2 -> 1 (anim_light.py); the log cells take the map's own DMG rows for every row the sunk pose shares with the old tile (the pose is
  the old tile shifted down 1 px) and 1 -> 0, 2 -> 1 for the new waterline foam row.  Lodge smoke and cows: the
  DMG data set keeps the same indices as Color (checked).
Switch: SMAP_NO_ANIM_STATIC=1 leaves the map as it was (needed by anim_light.py and the falls item of smap_anim, which assert the old art)."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def dmg_log_tile(new, old_c, old_d):
    """DMG light rows of a log cell's new Color tile.  The sunk pose is the old tile shifted down 1 px (items.py), so each new row that equals an old Color row takes that row's DMG row (the
    grain, end rings and wood keep exactly the DMG art the map already has; try the shifted row first); rows with no old twin are the new waterline foam (1 -> 0, 2 -> 1)."""
    out = []
    for r, row in enumerate(new):
        cand = [m for m in (r - 1, r, r + 1) if 0 <= m < 8] + list(range(8))
        m = next((m for m in cand if old_c[m] == row), None)
        out.append(old_d[m] if m is not None else "".join({"0": "0", "1": "0", "2": "1"}[c] for c in row))
    return out


def dmg_water_tile(rows):
    return ["".join({"0": "0", "1": "0", "2": "1", "3": "2"}[c] for c in r) for r in rows]


def apply(W, WORLDS, M):
    """paste into WORLDS (Color, DMG); M is the integrated map module (fully built).  Returns the set of cells changed."""
    import audit_anim as AA
    px, pal, edits, its, a5 = AA.missing(M)
    mod = sys.modules["items"]
    log_cells = set()
    for (x, y) in mod.LOGS_H_ALL:
        log_cells |= {(x, y), (x + 1, y)}
    for (x, y) in mod.LOGS_V_ALL:
        log_cells |= {(x, y), (x, y + 1)}
    allpx = dict(px)
    for e in edits.values():
        allpx.update(e)
    cells = {}
    for (x, y), v in allpx.items():
        cells.setdefault((x // 8, y // 8), {})[(x, y)] = v
    color, dmg = WORLDS
    changed = set()
    for (cx, cy), d in cells.items():
        old_c = ["".join(str(color.px[cy * 8 + j][cx * 8 + i]) for i in range(8)) for j in range(8)]
        new_c = [list(r) for r in old_c]
        for (x, y), v in d.items():
            new_c[y - cy * 8][x - cx * 8] = str(v)
        new_c = ["".join(r) for r in new_c]
        if (cx, cy) in log_cells:
            old_d = ["".join(str(dmg.px[cy * 8 + j][cx * 8 + i]) for i in range(8)) for j in range(8)]
            new_d = dmg_log_tile(new_c, old_c, old_d)
        elif color.pal[cy][cx] == "water":
            new_d = dmg_water_tile(new_c)
        else:
            new_d = new_c
        for j in range(8):
            for i in range(8):
                color.px[cy * 8 + j][cx * 8 + i] = int(new_c[j][i])
                dmg.px[cy * 8 + j][cx * 8 + i] = int(new_d[j][i])
        changed.add((cx, cy))
    for (cx, cy), p in pal.items():
        color.pal[cy][cx] = p
        dmg.pal[cy][cx] = p
        changed.add((cx, cy))
    return changed


