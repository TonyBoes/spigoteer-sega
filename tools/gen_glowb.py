#!/usr/bin/env python3
"""GLOW=B prototype (owner 2026-10-17, "a glow around fire and other light sources"): writes the bistro's halo assets
  assets/approved/venues/bistro_stage_glowb.txt and bistro_anim_glowb.txt
from bistro_stage / _anim. Run by hand (the outputs are committed); tools/gen_art.py reads them when GLOW=B.

The halo: the two stage tiles beside the oven's lower half (map (11,2) and (14,2), the flame's rows) become animated tiles of
their own (they keep the wall's palette A; no new colours) and an ordered dither lightens the wall around the hearth, strongest
at the oven's edge and fading over 6 px; the intensity follows the flame's frame (base 2, tall 4, lean 3, low 1) so the halo
flickers with the fire. Tiles: +2 unique stage tiles (22 + 13 of the venue pool's 36), 4 animated tiles (at most 6).
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VD = ROOT / "assets/approved/venues"
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]
LEVEL = {"base": 2, "tall": 4, "lean": 3, "low": 1}


def rows_of(path):
    return [l.rstrip("\n") for l in path.read_text().splitlines() if l and not l.startswith(";")]


def halo(tile, lvl, left):
    out = []
    for y in range(8):
        row = ""
        for x in range(8):
            ch = tile[y][x]
            dx = (7 - x) if left else x
            c = (lvl + 2 - 0.9 * dx) / 4 * (0.65 + 0.35 * y / 7)
            lit = c > (BAYER[y & 3][x & 3] + 0.5) / 16
            if lit and ch == "+":
                ch = "-"
            elif lit and ch == "-" and c > 0.5:
                ch = "."
            row += ch
        out.append(row)
    return out


def main():
    stage = rows_of(VD / "bistro_stage.txt")
    tl = [stage[16 + y][88:96] for y in range(8)]
    tr = [stage[16 + y][112:120] for y in range(8)]
    base_l, base_r = halo(tl, LEVEL["base"], True), halo(tr, LEVEL["base"], False)
    head = (VD / "bistro_stage.txt").read_text().splitlines()[0]
    out = [head.replace("unique 8x8 tiles: 20", "unique 8x8 tiles: 22 (GLOW=B: the halo tiles at (11,2) and (14,2), bistro_anim_glowb.txt)")]
    grid = [list(r) for r in stage]
    for y in range(8):
        for x in range(8):
            grid[16 + y][88 + x] = base_l[y][x]
            grid[16 + y][112 + x] = base_r[y][x]
    out += ["".join(r) for r in grid]
    (VD / "bistro_stage_glowb.txt").write_text("\n".join(out) + "\n")

    anim = (VD / "bistro_anim.txt").read_text().splitlines()
    o, cur = [], None
    for line in anim:
        if line.startswith("!slots"):
            line = "!slots 12,2 13,2 11,2 14,2"
        if line.startswith("@"):
            cur = line[1:]
            o.append(line)
            n = 0
            continue
        if cur and line.strip() and not line.startswith(";") and not line.startswith("!"):
            if n == 0:
                hl, hr = halo(tl, LEVEL[cur], True), halo(tr, LEVEL[cur], False)
            line = line + " " + hl[n] + " " + hr[n]
            n += 1
        o.append(line)
    o.insert(1, "; GLOW=B (tools/gen_glowb.py): the two halo tiles beside the oven (11,2) and (14,2) follow the flame: intensity base 2, tall 4, lean 3, low 1.")
    (VD / "bistro_anim_glowb.txt").write_text("\n".join(o) + "\n")


if __name__ == "__main__":
    main()
