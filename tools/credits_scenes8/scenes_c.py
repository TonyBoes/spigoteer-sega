"""Credits scene pages, second round (owner Q62): the OWNER in the foreground, large, off-centre, cut by the picture's bottom edge, the venue staged behind
and beside them, overlapped by them. No frame, no box.

What is drawn, and by whom:
  * the owner: the owner's portrait art, copied; cut out of its own backdrop (the mask: the dark backdrop pixels that touch the box's edge through open dark
    ground, plus a one pixel rim; the dark pixels inside the hair and clothes stay), and EXTENDED downward by hand (the EXT rows below: 24 rows of pixels typed
    by me, a base row continued with my edits) so that the crop falls on the picture's bottom edge;
  * the venue behind: the venue's own approved in-game tiles (stage wall, sign, ledge, lane, counter, keg / kettle / canister: copied tile for tile, the same
    arrangement as the game's bar, receding: wall at the back, ledge, lane, counter, floor), plus a few hand-drawn tiles (the counter front);
  * depth: the whole backdrop is stepped one DMG shade darker than the game draws it (0->1, 1->2, 2->3: the game's own card remap, credits.c cr_remap), so the
    owner is the brightest, most contrasted thing; every pixel of the page uses the OWNER'S palettes only (no palette of the venue), so a cell that holds part of
    the owner and part of the room has one palette.
"""
from scenes_lib import *
from scenes_a import SALOON_BAR_KIT, IGLOO_BAR_KIT, SPACE_BAR_KIT

# the owners' palettes (the story packs them: assets/story/portraits, the three / two palettes each portrait needs)
OWN_PALS = {
    "sadie": [["#f8e0b0", "#d8a878", "#903820", "#281818"], ["#f8e0b0", "#c06040", "#903820", "#281818"], ["#f8e0b0", "#f8a068", "#c06038", "#281818"]],
    "aurora": [["#e8d0a0", "#88d8c0", "#388888", "#201828"], ["#e8d0a0", "#f0b080", "#388888", "#201828"], ["#d06890", "#f0b080", "#783058", "#201828"]],
    "zizz": [["#b8f8d8", "#48b898", "#382058", "#181830"], ["#b8f8d8", "#48b898", "#e04888", "#181830"]],
}
SCENE_PAL = {"sadie": 0, "aurora": 0, "zizz": 0}      # the palette the room's own cells use (the owner's first)
DIM = {0: 1, 1: 2, 2: 3, 3: 3}


class Rows(list):
    name = ""


# round 7 mask audit. The portraits draw the figure's outline in the BACKDROP colour, so the pixels next to the figure are its outline and are kept (no dilation of
# the mask). Zizz has no outline (its blob edge is mint against a purple backdrop): its mask keeps the one pixel dilation, so no purple halo is left.
DILATE = {"zizz"}
# hand lists, (x, y) in the portrait: KEEP = removed by the rule but part of the owner; REMOVE = kept by the rule but backdrop. Empty: the audit found none to list.
KEEP, REMOVE = {}, {}


def read_raw(name):
    key, rows, mode, acc = {}, Rows(), None, {}
    rows.name = name
    for ln in (PORT / f"{name}.txt").read_text().splitlines():
        if ln.startswith("@key"):
            mode = "k"
        elif ln.startswith("@pixels"):
            mode = "p"
        elif ln.startswith(";") or ln.startswith("@") or not ln.strip():
            continue
        elif mode == "k":
            p = ln.split()
            key[p[0]] = (int(p[1]), p[2])
            if len(p) > 4 and p[4].startswith("obj="):
                acc[p[0]] = p[4][4:]
        elif mode == "p":
            rows.append("".join(acc.get(c, c) for c in ln))
    return key, rows


def backdrop_mask(rows):
    """True where the portrait's backdrop is: open dark ground (3 x 3 all backdrop) connected to the box edge, dilated by one pixel"""
    n = 56
    bg = rows[0][0]
    d = lambda x, y: (rows[y][x] == bg) if 0 <= x < n and 0 <= y < n else True
    opn = [[all(d(x + i, y + j) for i in (-1, 0, 1) for j in (-1, 0, 1)) for x in range(n)] for y in range(n)]
    seed, stack = set(), [(x, y) for x in range(n) for y in range(n) if (x in (0, n - 1) or y in (0, n - 1)) and opn[y][x]]
    while stack:
        x, y = stack.pop()
        if (x, y) in seed or not (0 <= x < n and 0 <= y < n) or not opn[y][x]:
            continue
        seed.add((x, y))
        stack += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    # (round 7: no dilation, except Zizz: see DILATE.)
    m = [[False] * n for _ in range(n)]
    for (x, y) in seed:
        if getattr(rows, "name", "") in DILATE:
            for i in (-1, 0, 1):
                for j in (-1, 0, 1):
                    if 0 <= x + i < n and 0 <= y + j < n and rows[y + j][x + i] == bg:
                        m[y + j][x + i] = True
        else:
            m[y][x] = True
    # only backdrop that is connected to the portrait's TOP or SIDE background counts: a masked region that touches only the bottom edge, or nothing, is body
    # (dark clothes at the bottom edge), and is given back to the owner
    seen, keep = set(), set()
    for y0 in range(n):
        for x0 in range(n):
            if m[y0][x0] and (x0, y0) not in seen:
                comp, st = [], [(x0, y0)]
                seen.add((x0, y0))
                while st:
                    x, y = st.pop()
                    comp.append((x, y))
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        a, b = x + dx, y + dy
                        if 0 <= a < n and 0 <= b < n and m[b][a] and (a, b) not in seen:
                            seen.add((a, b))
                            st.append((a, b))
                if any(y == 0 or x in (0, n - 1) for x, y in comp):
                    keep.update(comp)
    out = [[(x, y) in keep for x in range(n)] for y in range(n)]
    for x, y in KEEP.get(getattr(rows, "name", ""), ()):
        out[y][x] = False
    for x, y in REMOVE.get(getattr(rows, "name", ""), ()):
        out[y][x] = True
    return out


def silhouette_check(name, rows, mask):
    """every pixel of the portrait that is not backdrop-coloured, and every backdrop-coloured pixel enclosed by the figure (not 4-connected through backdrop-coloured
    pixels to the top or a side edge), must be kept (not masked). Returns (figure pixels, enclosed dark pixels kept, masked pixels on the bottom row)"""
    n = 56
    bg = rows[0][0]
    reach, st = set(), [(x, y) for x in range(n) for y in range(n - 1) if (y == 0 or x in (0, n - 1)) and rows[y][x] == bg]
    while st:
        x, y = st.pop()
        if (x, y) in reach or not (0 <= x < n and 0 <= y < n) or rows[y][x] != bg:
            continue
        reach.add((x, y))
        st += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    fig = enc = 0
    for y in range(n):
        for x in range(n):
            if rows[y][x] != bg:
                fig += 1
                assert not mask[y][x], (name, "figure pixel masked", x, y)
            elif (x, y) not in reach:
                enc += 1
                assert not mask[y][x], (name, "enclosed dark pixel masked", x, y)
    return fig, enc, sum(1 for x in range(n) if mask[n - 1][x])


def extend(rows, edits, n=24):
    """n rows below the portrait: its last row continued straight down (the cloth carries on), then MY edits: {row index: [(x, "chars"), ...]} typed pixel runs"""
    base = rows[55]
    out = []
    for y in range(n):
        r = list(base)
        for x, s in edits.get(y, []):
            r[x:x + len(s)] = list(s)
        out.append("".join(r))
    assert all(len(r) == 56 for r in out)
    return out


# Sadie: a brick-red belt with a cream buckle across the cut (rows 12-13, over the vest and shirt), a button down the shirt
SADIE_EDITS = {
    12: [(30, "ccccccccccc"), (41, "ccccccccccccc")], 13: [(30, "ccccccccccc"), (41, "ccccccccccccc")],
    3: [(34, "e")], 8: [(34, "e")], 17: [(34, "e")], 21: [(34, "e")],
}
# Aurora: the parka's chest pocket (teal outline), the zip line down the middle of the scarf's end
AURORA_EDITS = {
    4: [(4, "ddddddddddd")], 5: [(4, "d"), (14, "d")], 6: [(4, "d"), (14, "d")], 7: [(4, "d"), (14, "d")], 8: [(4, "d"), (14, "d")], 9: [(4, "ddddddddddd")],

}


class Scene:
    """a 160 x 104 picture of shades (the room) with the owner on top; colours per cell from the owner's palettes"""

    def __init__(self, name, owner):
        self.name, self.owner = name, owner
        self.sh = [[3] * PW for _ in range(PH)]           # the room's shades
        self.fig = {}                                     # (x, y) -> (shade, hex) of the owner's pixels

    def room_tile(self, cx, cy, t, dim=True):
        for y in range(8):
            for x in range(8):
                s = t[y][x][0] if isinstance(t[y][x], tuple) else t[y][x]
                self.sh[cy * 8 + y][cx * 8 + x] = DIM[s] if dim else s

    def place_owner(self, px0, py0, ext_edits):
        key, rows = read_raw(self.owner)
        mask = backdrop_mask(rows)
        full = rows + (extend(rows, ext_edits) if ext_edits is not None else [])
        n = len(full)
        for y in range(n):
            for x in range(56):
                if y < 56 and mask[y][x]:
                    continue
                if y >= 56 and full[y][x] == rows[0][0]:
                    continue
                gx, gy = px0 + x, py0 + y
                if 0 <= gx < PW and 0 <= gy < PH:
                    self.fig[(gx, gy)] = key[full[y][x]]
        # the dark pixels inside the owner but cut by the mask rim at the box sides: nothing more

    def build(self):
        pals = OWN_PALS[self.owner]
        page = Page(self.name, (0, "#000000"))
        for cy in range(13):
            for cx in range(20):
                m = {}
                for y in range(8):
                    for x in range(8):
                        f = self.fig.get((cx * 8 + x, cy * 8 + y))
                        if f:
                            if m.setdefault(f[0], f[1]) != f[1]:
                                raise SystemExit(f"{self.name}: cell ({cx},{cy}) holds two colours of shade {f[0]}")
                if m:
                    p = next((p for p in pals if all(p[s] == h for s, h in m.items())), None)
                    assert p, (self.name, cx, cy, m)
                else:
                    p = pals[SCENE_PAL[self.owner]]
                for y in range(8):
                    for x in range(8):
                        f = self.fig.get((cx * 8 + x, cy * 8 + y))
                        page.px[cy * 8 + y][cx * 8 + x] = f if f else (self.sh[cy * 8 + y][cx * 8 + x], p[self.sh[cy * 8 + y][cx * 8 + x]])
        return page


def lib_for(venue, bar_kit):
    st = venue_tiles(venue, "stage", "stage_a")
    bar = venue_tiles(venue, "bar", "bar")
    kb = {str(i): (i, "#000000") for i in range(4)}
    k = kit(kb, bar_kit)
    return st, bar, k


def lay(scene, venue, rows, bar_kit):
    st, bar, kk = lib_for(venue, bar_kit)
    for cy, line in enumerate(rows):
        toks = line.split()
        assert len(toks) == 20, (venue, cy, len(toks))
        for c, t in enumerate(toks):
            if t == "w":
                t = "S2_0" if (c + cy) % 2 == 0 else "S3_0"
            elif t == "g":
                t = f"S{c % 2}_3"
            elif t == "b":
                t = f"B{c}_{cy - 7}"
            if t[0] in "SB" and t[1:2].isdigit():
                a, b = t[1:].split("_")
                tile = (st if t[0] == "S" else bar)[(int(a), int(b))]
            else:
                tile = kk[t]
            scene.room_tile(c, cy, tile)


SAL_ROWS = [
    "S0_0 S1_0 w w w w w w w w w w w w w w w w S18_0 S19_0",
    "S0_1 S1_1 w w S7_0 S8_0 S9_0 S10_0 S11_0 S12_0 w w w w w w w w S18_1 S19_1",
    "S0_2 S1_2 w w S7_1 S8_1 S9_1 S10_1 S11_1 S12_1 w w w w w w w w S18_2 S19_2",
    "S0_0 S1_0 w w S7_2 S8_2 S9_2 S10_2 S11_2 S12_2 w w w w w w w w S18_0 S19_0",
    "S0_1 S1_1 w w w w w w w w w w w w w w w w S18_1 S19_1",
    "S0_2 S1_2 w w w w w w w w w w w w w w w w S18_2 S19_2",
    "S0_0 S1_0 w w w w w S14_1 w w w w w w w w w w S18_0 S19_0",
    "S0_1 S1_1 w w w w S13_2 S14_2 w w w w w w w w w w S18_1 S19_1",
    "g g g g g g g S13_3 g g g g g g g g g g g g",
    "B0_0 B17_0 B18_0 B19_0 B1_0 B1_0 B1_0 B8_0 B1_0 B1_0 B1_0 B1_0 B1_0 B1_0 B1_0 B1_0 B1_0 B1_0 B1_0 B1_0",
    "B0_1 B17_1 B18_1 B19_1 B2_1 B2_1 B2_1 B2_1 B2_1 B2_1 B2_1 B2_1 B2_1 B2_1 B2_1 B2_1 B2_1 B2_1 B2_1 B2_1",
    "B0_2 B17_2 B18_2 B19_2 B1_2 B0_2 B1_2 B0_2 B1_2 B0_2 B1_2 B0_2 B1_2 B0_2 B1_2 B0_2 B1_2 B0_2 B1_2 B0_2",
    "F1 F2 F1 F2 F1 F2 F1 F2 F1 F2 F1 F2 F1 F2 F1 F2 F1 F2 F1 F2",
]


IGL_ROWS = [
    "S0_0 S1_0 S0_0 S1_0 S0_0 S1_0 S0_0 S1_0 S0_0 S1_0 S0_0 S1_0 S0_0 S1_0 S0_0 S1_0 S0_0 S1_0 S0_0 S1_0",
    "S0_1 S0_1 S0_1 S3_1 S3_1 S0_1 S3_1 S0_1 S3_1 S5_1 S6_1 S7_1 S8_1 S0_1 S3_1 S0_1 S3_1 S0_1 S0_1 S0_1",
    "S0_1 S0_1 S0_1 S3_1 S3_1 S0_1 S3_1 S0_1 S3_1 S5_2 S6_2 S7_2 S8_2 S0_1 S3_1 S0_1 S3_1 S0_1 S0_1 S0_1",
    "S0_1 S0_1 S0_1 S3_1 S3_1 S0_1 S3_1 S0_1 S3_1 S0_1 S3_1 S3_1 S0_1 S0_1 S3_1 S0_1 S3_1 S0_1 S0_1 S0_1",
    "S0_1 S0_1 S0_1 S3_1 S3_1 S0_1 S3_1 S0_1 S3_1 S0_1 S3_1 S3_1 S0_1 S0_1 S3_1 S0_1 S3_1 S0_1 S0_1 S0_1",
    "S0_1 S0_1 S0_1 S3_1 S3_1 S0_1 S3_1 S0_1 S3_1 S0_1 S3_1 S3_1 S0_1 S0_1 S3_1 S0_1 S3_1 S0_1 S0_1 S0_1",
    "S0_1 S0_1 S0_1 S3_1 S3_1 S0_1 S3_1 S0_1 S3_1 S0_1 S3_1 S3_1 S0_1 S0_1 S3_1 S12_1 S13_1 S14_1 S0_1 S0_1",
    "S0_1 S0_1 S0_1 S3_1 S3_1 S0_1 S3_1 S0_1 S3_1 S0_1 S3_1 S3_1 S0_1 S0_1 S11_2 S12_2 S13_2 S0_1 S0_1 S0_1",
    "g g g g g g g g g g g g g g g S12_3 S13_3 g g g",
    "B0_0 B1_0 B1_0 B1_0 B1_0 B1_0 B1_0 B1_0 B8_0 B1_0 B1_0 B1_0 B1_0 B1_0 B1_0 B1_0 B1_0 B17_0 B18_0 B19_0",
    "B0_1 B2_1 B2_1 B2_1 B2_1 B2_1 B2_1 B2_1 B2_1 B2_1 B2_1 B2_1 B2_1 B2_1 B2_1 B2_1 B2_1 B17_1 B18_1 B19_1",
    "B0_2 B1_2 B0_2 B1_2 B0_2 B1_2 B0_2 B1_2 B0_2 B1_2 B0_2 B1_2 B0_2 B1_2 B0_2 B1_2 B0_2 B17_2 B18_2 B19_2",
    "F1 F2 F1 F2 F1 F2 F1 F2 F1 F2 F1 F2 F1 F2 F1 F2 F1 F2 F1 F2",
]
SPA_ROWS = [
    "S0_0 S1_0 S0_0 S1_0 S0_0 S1_0 S0_0 S1_0 S0_0 S1_0 S0_0 S1_0 S0_0 S1_0 S0_0 S1_0 S0_0 S1_0 S0_0 S1_0",
    "S0_1 S3_1 S0_1 S3_1 S0_1 S3_1 S0_1 S3_1 S0_1 S3_1 S0_1 S3_1 S0_1 S3_1 S0_1 S3_1 S0_1 S3_1 S0_1 S3_1",
    "S0_1 S3_1 S0_1 S3_1 S0_1 S3_1 S0_1 S3_1 S0_1 S3_1 S0_1 S3_1 S0_1 S3_1 S0_1 S3_1 S0_1 S3_1 S0_1 S3_1",
    "S0_1 S3_1 S0_1 S3_1 S0_1 S3_1 S0_1 S3_1 S12_1 S13_1 S0_1 S3_1 S0_1 S3_1 S0_1 S3_1 S0_1 S3_1 S0_1 S3_1",
    "S0_1 S3_1 S0_1 S3_1 S0_1 S3_1 S0_1 S3_1 S12_2 S13_2 S0_1 S3_1 S0_1 S3_1 S0_1 S3_1 S0_1 S3_1 S0_1 S3_1",
    "S0_1 S3_1 S0_1 S5_1 S6_1 S3_1 S0_1 S3_1 S0_1 S3_1 S0_1 S3_1 S0_1 S3_1 S0_1 S3_1 S0_1 S3_1 S0_1 S3_1",
    "S0_1 S3_1 S0_1 S5_2 S6_2 S3_1 S0_1 S3_1 S0_1 S3_1 S0_1 S3_1 S0_1 S3_1 S0_1 S3_1 S0_1 S3_1 S0_1 S3_1",
    "S0_1 S3_1 S0_1 S3_1 S0_1 S3_1 S0_1 S3_1 S0_1 S3_1 S0_1 S3_1 S0_1 S3_1 S0_1 S3_1 S0_1 S3_1 S0_1 S3_1",
    "g g g g g g g g g g g g g g g g g g g g",
    "B0_0 B1_0 B1_0 B1_0 B1_0 B1_0 B1_0 B1_0 B8_0 B1_0 B1_0 B1_0 B1_0 B1_0 B1_0 B1_0 B1_0 B17_0 B18_0 B19_0",
    "B0_1 B2_1 B2_1 B2_1 B2_1 B2_1 B2_1 B2_1 B2_1 B2_1 B2_1 B2_1 B2_1 B2_1 B2_1 B2_1 B2_1 B17_1 B18_1 B19_1",
    "B0_2 B1_2 B0_2 B1_2 B0_2 B1_2 B0_2 B1_2 B0_2 B1_2 B0_2 B1_2 B0_2 B1_2 B0_2 B1_2 B0_2 B17_2 B18_2 B19_2",
    "F1 F2 F1 F2 F1 F2 F1 F2 F1 F2 F1 F2 F1 F2 F1 F2 F1 F2 F1 F2",
]


def igloo():
    s = Scene("igloo_C", "aurora")
    lay(s, "igloo", IGL_ROWS, IGLOO_BAR_KIT)
    s.place_owner(0, 24, AURORA_EDITS)
    return s.build()


def space():
    s = Scene("space_C", "zizz")
    lay(s, "space", SPA_ROWS, SPACE_BAR_KIT)
    s.place_owner(96, 16, None)
    return s.build()


def saloon():
    s = Scene("saloon_C", "sadie")
    lay(s, "saloon", SAL_ROWS, SALOON_BAR_KIT)
    s.place_owner(104, 24, SADIE_EDITS)
    return s.build()


if __name__ == "__main__":
    import sys
    out = Path(sys.argv[1])
    for fn, v, o in ((saloon, "saloon", "SADIE"), (igloo, "igloo", "AURORA"), (space, "space", "ZIZZ")):
        p = fn()
        for cgb in (False, True):
            page_card(p, v, o, cgb).save(out / f"C_{v}_{'cgb' if cgb else 'dmg'}.png")
        print(v, p.unique_tiles(), len(p.palettes()[0]))
