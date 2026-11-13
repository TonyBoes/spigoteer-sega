#!/usr/bin/env python3
"""The Boss Rush list's portraits (src/rush.c): each boss's WHOLE fight figure (body pose 0 and his topper's upper half), centred in the list's window by what is
DRAWN, both ways -> BUILD/rush_portraits.h.

Usage: gen_rush_portraits.py BUILD_DIR (after tools/gen_boss.py: it reads BUILD/boss_<name>_art.h, and src/boss.c for the topper's x).
The window's backdrop is 6 x 4 tiles (48 x 32 px). A figure is the topper's STILL frame (8 x 16, its upper 8 rows stick out above the body, as src/boss.c draws it)
over the body (16 rows, WALK): up to 24 rows. It is shifted by whole pixels so that the middle of his drawn pixels (colour index not 0) falls on the middle of the
48 x 32 (both within half a pixel: asserted). Nothing but a position is decided here: every pixel is the boss's own, from assets/art/boss/*.txt.
Each picture is packed by content: only its non-blank 8x8 tiles (at most the 24 cells) and a 6 x 4 map of them; src/rush.c streams the selected boss's tiles
into a spare slot of BG ids and shows them when they are all there. Also the DMG's "??" for a locked boss (picture 10), from the story font's hand-drawn
question mark (assets/tiles/story.txt, @glyph_quest), its drawn pixels in colour 3, centred the same way, and each boss's three colours for the Color
silhouette-or-colour palette.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOSSES = ["big_tex", "mascot", "sasquatch", "critic", "yeti", "prototype", "duke", "sumo", "leo", "mothership"]   # venue order (src/rush.c boss_name)
WIN_COLS = 6                                    # tile columns of the backdrop
WIN_ROWS = 4                                    # tile rows of the backdrop
MID_X = WIN_COLS * 8 // 2                       # 24
MID_Y = WIN_ROWS * 8 // 2                       # 16
H = 16
HAT_STILL_BYTES = 32                            # the topper's STILL frame: an 8x16 OBJ, top tile then bottom tile, the first 32 bytes of boss_art_hat


def body_pixels(build, name):
    """Pose 0 of boss `name` as 16 rows of pixel indices (8 * columns wide), and his three colours (RGB15)."""
    text = (build / f"boss_{name}_art.h").read_text()
    cols = int(re.search(r"#define BOSS_ART_COLS (\d+)", text).group(1))
    body = [int(x, 16) for x in re.search(r"boss_art_body\[\d+\] = \{([^}]*)\}", text).group(1).replace("\n", " ").split(",") if x.strip()]
    pose0 = [int(x) for x in re.search(r"boss_art_pose\[[^\]]*\]\[[^\]]*\] = \{ \{([^}]*)\}", text).group(1).split(",")][:cols]
    pal = [int(x, 16) for x in re.search(r"boss_art_pal\[4\] = \{([^}]*)\}", text).group(1).split(",")]
    assert len(pose0) == cols
    rows = [[0] * (8 * cols) for _ in range(H)]
    for c, p in enumerate(pose0):
        for t in range(2):                      # the pair's top and bottom tile
            base = (2 * p + t) * 16
            for y in range(8):
                lo, hi = body[base + 2 * y], body[base + 2 * y + 1]
                for x in range(8):
                    rows[8 * t + y][8 * c + x] = ((lo >> (7 - x)) & 1) | (((hi >> (7 - x)) & 1) << 1)
    return rows, pal[1:4]


def hat_dx(name):
    """The topper's x from his left edge: src/boss.c rows[venue].hat_dx (the tenth number of the row; BOSSES is in venue order)."""
    text = (ROOT / "src" / "boss.c").read_text()
    rows = dict((int(m[0]), int(m[10])) for m in re.findall(r"\[(\d)\] = \{" + r"\s*(\d+)," * 11, text))
    return rows[BOSSES.index(name)]


def figure_pixels(build, name):
    """The whole figure as the fight shows him: 24 rows (the topper's 8 rows above the body, then the body's 16), the topper over the body (colour 0 is clear)."""
    body, pal = body_pixels(build, name)
    text = (build / f"boss_{name}_art.h").read_text()
    d = [int(x, 16) for x in re.search(r"boss_art_hat\[\d+\] = \{([^}]*)\}", text).group(1).split(",")][:HAT_STILL_BYTES]
    rows = [[0] * len(body[0]) for _ in range(8)] + [list(r) for r in body]
    dx = hat_dx(name)
    for y in range(16):
        for x in range(8):
            lo, hi = d[(y // 8) * 16 + 2 * (y % 8)], d[(y // 8) * 16 + 2 * (y % 8) + 1]
            v = ((lo >> (7 - x)) & 1) | (((hi >> (7 - x)) & 1) << 1)
            if v:
                rows[y][dx + x] = v
    return rows, pal


def quest_pixels():
    """The "??" as 16 rows of indices: the font's question mark twice, drawn pixels in colour 3, its rows centred on the 16."""
    lines = (ROOT / "assets" / "tiles" / "story.txt").read_text().splitlines()
    i = lines.index("@glyph_quest")
    g = [ln.strip() for ln in lines[i + 1:i + 9]]
    assert len(g) == 8 and all(len(r) == 8 for r in g)
    drawn = [[0 if ch == "#" else 3 for ch in r] for r in g]
    ys = [y for y, r in enumerate(drawn) if any(r)]
    oy = 8 - (ys[0] + ys[-1] + 1) // 2
    rows = [[0] * 16 for _ in range(H)]
    for y, r in enumerate(drawn):
        rows[y + oy][0:8] = r
        rows[y + oy][8:16] = r
    return rows


def place(rows):
    """Shift by whole pixels so the middle of the drawn pixels is the window's middle (48 x 32); returns the 32 rows and the centre errors (x, y) in px."""
    xs = [x for r in rows for x, v in enumerate(r) if v]
    ys = [y for y, r in enumerate(rows) if any(r)]
    x0, x1, y0, y1 = min(xs), max(xs), ys[0], ys[-1]
    dx, dy = MID_X - (x0 + x1 + 1) // 2, MID_Y - (y0 + y1 + 1) // 2
    assert dx >= 0 and x1 + dx < WIN_COLS * 8 and y0 + dy >= 0 and y1 + dy < WIN_ROWS * 8, (dx, dy)
    out = [[0] * (WIN_COLS * 8) for _ in range(WIN_ROWS * 8)]
    for y, r in enumerate(rows):
        for x, v in enumerate(r):
            if v:
                out[y + dy][x + dx] = v
    return out, abs((x0 + x1 + 1) / 2 + dx - MID_X), abs((y0 + y1 + 1) / 2 + dy - MID_Y)


def packed(grid):
    """A picture's non-blank tiles (16 bytes each, in order of first use) and its map: 6 x 4 entries, 0 blank, else 1 + the tile's index in the list."""
    uniq, data, m = {}, [], []
    for ty in range(WIN_ROWS):
        for tx in range(WIN_COLS):
            t = tuple(tuple(grid[8 * ty + y][8 * tx + x] for x in range(8)) for y in range(8))
            if not any(any(r) for r in t):
                m.append(0)
                continue
            if t not in uniq:
                uniq[t] = len(uniq)
                for r in t:
                    lo = hi = 0
                    for v in r:
                        lo, hi = (lo << 1) | (v & 1), (hi << 1) | (v >> 1)
                    data += [lo, hi]
            m.append(uniq[t] + 1)
    return data, m, len(uniq)


def array(name, data, per=16, t="uint8_t"):
    return f"static const {t} {name} = {{\n" + ",\n".join(", ".join(str(b) for b in data[i:i + per]) for i in range(0, len(data), per)) + "\n};\n"


def main():
    build = Path(sys.argv[1])
    out = ["// generated by tools/gen_rush_portraits.py from the boss art headers, src/boss.c and assets/tiles/story.txt -- do not edit; #included by src/rush.c only (its bank)",
           "// Picture d (0..9 a boss, 10 the DMG's \"??\"): rush_cnt[d] tiles from tile rush_off[d] of rush_tiles (his non-blank 8x8 tiles, in order of first use);",
           "// rush_map[24 * d + 6 * row + column]: the window's 6 x 4 backdrop cells, 0 blank, else 1 + the tile's index in his list; rush_colour[3 * v]: his colours 1-3 (RGB15)",
           f"#define RUSH_PORTRAITS {len(BOSSES)}", "#define RUSH_MAP_W 24   // a picture's map: 6 columns x 4 rows", "#define RUSH_SLOT 24    // tiles a picture may take (the window's cells)"]
    tiles, off, cnt, maps, colour, worst, pics = [], [], [], [], [], 0.0, []
    for name in BOSSES:
        rows, pal = figure_pixels(build, name)
        grid, ex, ey = place(rows)
        assert ex <= 0.5 and ey <= 0.5, (name, ex, ey)
        worst = max(worst, ex, ey)
        pics.append(grid)
        colour += pal
    qc, ex, ey = place_quest()
    pics.append(qc)
    for grid in pics:
        data, m, n = packed(grid)
        assert n <= WIN_COLS * WIN_ROWS
        off.append(len(tiles) // 16)
        cnt.append(n)
        tiles += data
        maps += m
    assert len(tiles) // 16 < 256
    out.append(array("rush_tiles[%d]" % len(tiles), tiles, 24))
    out.append(array("rush_off[%d]" % len(off), off, 16))
    out.append(array("rush_cnt[%d]" % len(cnt), cnt, 16))
    out.append(array("rush_map[%d]" % len(maps), maps, 24))
    out.append(f"static const uint16_t rush_colour[{len(BOSSES)} * 3] = {{ " + ", ".join(str(c) for c in colour) + " };\n")
    (build / "rush_portraits.h").write_text("\n".join(out))
    print(f"rush_portraits.h: {len(BOSSES)} bosses, {len(tiles) // 16} tiles, worst centring error {worst} px")


def place_quest():
    """The "??" on the window: its drawn pixels centred both ways (it is 16 rows high: the middle two of the four tile rows)."""
    q = quest_pixels()
    rows = [[0] * (WIN_COLS * 8) for _ in range(WIN_ROWS * 8)]
    for y, r in enumerate(q):
        rows[y + 8][:16] = r
    grid, ex, ey = place(rows)
    assert ex <= 0.5 and ey <= 0.5, ("quest", ex, ey)
    return grid, ex, ey


if __name__ == "__main__":
    main()
