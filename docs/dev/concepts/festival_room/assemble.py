#!/usr/bin/env python3
"""Transcribes a hand-drawn tile library (X/tiles.txt) into the venue files the build reads (stage.txt, bar.txt, attr.txt,
bar_attr.txt, floor.txt). It places NO pixel of its own: every pixel is in a "@NAME" 8x8 block drawn by hand, and the
maps ("=stage" 20x4 names, "=bar" 20x3 names) only say which drawn tile goes where.

    python3 assemble.py A        # reads A/tiles.txt, writes A/stage.txt A/bar.txt A/attr.txt A/bar_attr.txt A/floor.txt
Symbols: . - + #  = colour 0..3 (as the venues' files).  Unique-tile counts are printed (the budget: stage 23, bar 13 incl. floor).
In a map line, "name" or "name:1" (palette attribute 1 = stage_b / bar_b; default 0).
"""
import sys
from pathlib import Path

here = Path(__file__).resolve().parent


def parse(path):
    tiles, maps, figs, cur, mode = {}, {}, {}, None, None
    for raw in Path(path).read_text().splitlines():
        line = raw.rstrip()
        if line.startswith(";") or not line.strip():
            continue
        if line.startswith("@@"):                      # a drawn figure of w x h pixels (multiples of 8): cut into NAME_<row><col> tiles
            cur = line[2:].strip()
            figs[cur] = []
            mode = "fig"
        elif line.startswith("@"):
            cur = line[1:].strip()
            tiles[cur] = []
            mode = "tile"
        elif line.startswith("="):
            cur = line[1:].strip()
            maps[cur] = []
            mode = "map"
        elif mode == "fig":
            assert set(line) <= set(".-+#"), f"{cur}: bad row {line!r}"
            figs[cur].append(line)
        elif mode == "tile":
            assert len(line) == 8 and set(line) <= set(".-+#"), f"{cur}: bad row {line!r}"
            tiles[cur].append(line)
        else:
            maps[cur].append(line.split())
    for n, f in figs.items():
        assert len(f) % 8 == 0 and all(len(r) == len(f[0]) and len(r) % 8 == 0 for r in f), f"figure {n}: size must be a multiple of 8"
        for r in range(len(f) // 8):
            for c in range(len(f[0]) // 8):
                tiles[f"{n}_{r}{c}"] = [f[r * 8 + y][c * 8:c * 8 + 8] for y in range(8)]
    for n, t in tiles.items():
        assert len(t) == 8, f"tile {n}: {len(t)} rows"
    return tiles, maps


def main(d):
    tiles, maps = parse(here / d / "tiles.txt")
    out = here / d
    used = {"stage": set(), "bar": set()}
    for key, w, h, fn in (("stage", 20, 4, "stage.txt"), ("bar", 20, 3, "bar.txt")):
        m = maps[key]
        assert len(m) == h and all(len(r) == w for r in m), f"{key} map must be {w}x{h}"
        rows, attr = [], []
        for r in m:
            names, at = [], []
            for tok in r:
                nm, _, a = tok.partition(":")
                assert nm in tiles, f"unknown tile {nm}"
                names.append(nm)
                at.append(a or "0")
                used[key].add(tuple(tiles[nm]))
            attr.append("".join(at))
            for y in range(8):
                rows.append("".join(tiles[n][y] for n in names))
        hdr = {"stage": f"; festival stage {d}: 160x32, \".-+#\" = colour 0..3 (colour 0 is a real colour); no text.",
               "bar": f"; festival bar {d}: 160x24, two wall rows + counter row; keg cols 18-19, spout col 17 (the left end is mirrored by the engine)."}[key]
        (out / fn).write_text(hdr + "\n" + "\n".join(rows) + "\n")
        (out / ("attr.txt" if key == "stage" else "bar_attr.txt")).write_text(
            f"; palette per {key} tile, 20x{h}: 0 = {'stage_a' if key == 'stage' else 'bar'}, 1 = {'stage_b' if key == 'stage' else 'bar_b'}\n" + "\n".join(attr) + "\n")
    used["bar"].add(tuple(tiles["FLOOR"]))
    (out / "floor.txt").write_text("; floor row tile 8x8\n" + "\n".join(tiles["FLOOR"]) + "\n")
    # keep the first header line honest
    bar = (out / "bar.txt").read_text().splitlines()
    bar[0] += f" unique tiles incl. floor: {len(used['bar'])}"
    (out / "bar.txt").write_text("\n".join(bar) + "\n")
    st = (out / "stage.txt").read_text().splitlines()
    st[0] += f" unique 8x8 tiles: {len(used['stage'])}"
    (out / "stage.txt").write_text("\n".join(st) + "\n")
    print(d, "stage tiles", len(used["stage"]), "(max 23)  bar tiles incl floor", len(used["bar"]), "(max 13)")


if __name__ == "__main__":
    main(sys.argv[1])
