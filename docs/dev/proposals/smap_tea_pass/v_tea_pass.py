"""The Teahouse, 96 x 56, QUALITY PASS (proposal; drop-in for tools/smap_world/v_tea.py, same build(dmg) signature).
Same building, footprint, palettes (TEA, TEA_B), sign-free, door, roofs, lantern, stones, tree.  Every row below is typed by hand; the changes against v_tea.py are marked  # PASS.
Palettes TEA: 0 moss, 1 paper, 2 dark wood and roof, 3 ink.  TEA_B (the tree, the right 16 columns): 0 moss, 1 blossom, 2 deep pink, 3 ink.
Light from the top left, like the lodge, saloon and bistro beside it: lit left slopes of the roofs, bright top plane on the veranda."""
import os

from canvas import Canvas, piece

W, H = 96, 56
PAL = "tea"

# Round 5 door (level BWD): a sliding shoji leaf, half open: ink outline x34, wood frame, 5 px paper panes in rows of 4 like the wall panels (rails at y33 38 43 48), the dark interior in the
# 4 px strip on the right.  Same 12 x 21 footprint and cells as the curtain it replaces.
DOOR_PANE = "3:1 2:1 1:5 2:1 3:4"
DOOR_RAIL = "3:1 2:7 3:4"
DOOR = piece("3:12", (DOOR_PANE, 4), DOOR_RAIL, (DOOR_PANE, 4), DOOR_RAIL, (DOOR_PANE, 4), DOOR_RAIL, (DOOR_PANE, 4), DOOR_RAIL)
# Round 6 door (level BWN): a split noren, two cream panels hung from a rod at the top of the opening, a 2 px slit between them, the dark interior under the hem and through the slit.
# Rod y29, heading tape y30, panels y31-37 (right column shade 2 = the fold/shadow side, light from the top left), hem stitch y38, cloth y39, soft hem y40 with rounded outer corners.
NOREN2 = piece("3:12", "3:1 2:10 3:1", "3:1 2:10 3:1", ("3:1 1:3 2:1 3:2 1:3 2:1 3:1", 7), "3:1 2:4 3:2 2:4 3:1", "3:1 1:4 3:2 1:4 3:1",
               "3:2 2:3 3:2 2:3 3:2", ("3:12", 8))
def _rw(t):
    return " ".join(f"{ch}:1" for ch in t) if t.isdigit() else t


def P(*specs):
    """piece() that also takes a row typed as its 12 digits"""
    return piece(*[(_rw(a[0]), a[1]) if isinstance(a, tuple) else _rw(a) for a in specs])


# Round 7 curtain concepts (12 x 21 opening, x34..45, y28..48; typed rows, 3 ink, 2 brown, 1 cream; every row 12 wide).  Keys SMAP_TEA_TEX = C1 C2 C3 C4.
# C1 wide single noren: cream cloth across the opening, rod y29, heading tape y30, a brown disc mark (6 x 6) centred, shade-2 fold on the right, split only in the bottom third (y39-43), hem y43.
_C1_PLAIN = "311111111123"
_C1_MARK_END = "311122221123"
_C1_MARK_MID = "311222222123"
_C1_SPLIT = "311113311123"
C1 = P("3:12", "3:1 1:10 3:1", "3:1 2:10 3:1", _C1_PLAIN, _C1_MARK_END, (_C1_MARK_MID, 4), _C1_MARK_END, _C1_PLAIN, (_C1_SPLIT, 5), "322223322223", ("3:12", 5))
# C2 darker three-panel noren: brown cloth (shade 2) with an ink fold on the right of each panel and ink slits, two cream stripes, hangs to 3/4 of the opening (y43), the middle panel one row shorter.
_C2 = "312231231223"
C2 = P("3:12", "3:1 1:10 3:1", (_C2, 2), "311131131113", (_C2, 6), "311131131113", (_C2, 3), "312233331223", ("3:12", 5))
# C3 flap tied back: one cream flap drawn from the rod down to the right jamb, gathered in a column of folds and tied with a brown cord (y36), flaring below the tie to the hem (y43); the left of the doorway is open and dark.
C3 = P("3:12", "3:1 1:10 3:1", "311111111113", "331111111123", "333311111123", "333333111123", ("333333121123", 2), "333332222223", ("333331121123", 5), "333311211213", "333322222223", ("3:12", 5))
# C4 eave-wide valance (level C4): the plain dark open doorway here, and a short brown noren (rows y28-30 with a cream hem stripe, ink slits every 8 px) across the whole front under the beam (see valance()).
C4 = P("3:12", ("3:12", 20))
NOREN = piece("3:12", ("3:1 2:4 3:2 2:4 3:1", 8), ("3:12", 12))
LANT = piece(".:3 3:2 .:3", ".:1 3:6 .:1", "3:1 2:6 3:1", "3:8", ".:1 3:1 1:4 3:1 .:1", ".:1 3:1 1:4 3:1 .:1", ".:1 3:6 .:1",
             ".:2 3:1 2:2 3:1 .:2", ".:2 3:1 2:2 3:1 .:2", ".:2 3:1 2:2 3:1 .:2", "3:8", "3:8")
STONE = piece(".:1 3:6 .:1", "3:1 1:6 3:1", ".:1 3:6 .:1")
TREE = piece(".:5 3:6 .:5", ".:3 3:2 1:6 3:2 .:3", ".:2 3:1 1:3 0:2 1:5 3:1 .:2", ".:1 3:1 1:2 0:1 1:7 2:2 3:1 .:1",
             "3:1 1:9 2:5 3:1", "3:1 1:6 0:1 1:3 2:4 3:1", "3:1 1:5 2:9 3:1", ".:1 3:1 2:12 3:1 .:1", ".:2 3:2 2:8 3:2 .:2",
             ".:4 3:8 .:4", (".:6 3:1 2:2 3:1 .:6", 8), ".:4 3:8 .:4")


def build(dmg=False):
    c = Canvas("tea", PAL, W, H)
    c.palrect(80, 0, 96, 56, "tea_b")
    # ---- the upper roof.  PASS: a ridge cap (row 1), the ink outline now runs along the top of every step (4 4 4 4 3 2 px, was one ink px per row, so the
    # roof had no outline between its corners), the lit cream on the left slope tapers 2 3 3 2 2 1 1 instead of a constant 2 px band hugging the edge ----------
    c.row(1, "0:37 3:6 0:53")                                             # PASS ridge cap
    c.row(2, "0:36 3:1 1:2 2:4 3:1 0:52")
    c.row(3, "0:32 3:4 1:3 2:5 3:4 0:48")                                 # PASS
    c.row(4, "0:28 3:4 1:3 2:13 3:4 0:44")                                # PASS
    c.row(5, "0:24 3:4 1:2 2:22 3:4 0:40")                                # PASS
    c.row(6, "0:20 3:4 1:2 2:30 3:4 0:36")                                # PASS
    c.row(7, "0:17 3:3 1:1 2:39 3:3 0:33")                                # PASS
    c.row(8, "0:15 3:2 1:1 2:45 3:2 0:31")                                # PASS
    c.row(9, "0:16 3:48 0:32")                                            # PASS: the upper roof's eave gets its bottom outline (was only under the wall, 26..53)
    # ---- the upper wall (unchanged) ---------------------------------------------------------------------------------------------
    for y in range(10, 16):
        c.row(y, "0:26 3:1 2:1 1:11 2:2 1:11 2:1 3:1 0:42")
    c.row(16, "0:26 3:28 0:42")
    # ---- the lower roof, with curled eaves.  PASS: same outline and taper as above ------------------------------------------------------
    c.row(17, "0:20 3:6 2:28 3:6 0:36")                                   # PASS top edge either side of the upper wall
    c.row(18, "0:16 3:4 1:3 2:37 3:4 0:32")                               # PASS
    c.row(19, "0:12 3:4 1:3 2:45 3:4 0:28")                               # PASS
    c.row(20, "0:9 3:3 1:2 2:54 3:3 0:25")                                # PASS
    c.row(21, "0:7 3:2 1:2 2:60 3:2 0:23")                                # PASS
    c.row(22, "0:5 3:2 1:1 2:65 3:2 0:21")                                # PASS
    c.row(23, "0:4 3:1 1:1 2:69 3:1 0:20")                                # PASS
    for x, y in ((3, 22), (76, 22), (2, 21), (77, 21)):
        c.put(x, y, "3")
    c.row(24, "0:4 3:72 0:20")
    # ---- the lower wall: a beam, paper panels with a lattice, posts ----------------------------------------------------------------------
    c.row(25, "0:12 3:56 0:28")
    for y in (26, 27):
        c.row(y, "0:12 3:1 2:54 3:1 0:28")
    for y in range(28, 49):
        if y in (33, 38, 43, 48):                                        # PASS: rails 33 38 43 48, panels 5 4 4 4 (was rails 33 39: panels 5 5 9); the rail at 48 is a sill
            c.row(y, "0:12 3:1 2:2 2:17 2:2 1:12 2:2 2:17 2:2 3:1 0:28")
        else:
            c.row(y, "0:12 3:1 2:2 1:8 2:1 1:8 2:2 1:12 2:2 1:8 2:1 1:8 2:2 3:1 0:28")
    lvl = os.environ.get("SMAP_TEA_TEX", "A")
    new = lvl in ("BWD", "BWN", "C1", "C2", "C3", "C4")
    c.paste(34, 28, {"BWN": NOREN2, "BWD": DOOR, "C1": C1, "C2": C2, "C3": C3, "C4": C4}.get(lvl, NOREN))
    if lvl == "C4":
        valance(c)
    # ---- the veranda.  PASS: row 50 is the lit top plane (paper), row 51 the dark front face, so the deck reads as a platform ---------------
    c.row(49, "0:6 3:68 0:22")
    c.row(50, "0:6 3:1 1:66 3:1 0:22")                                    # PASS
    c.row(51, "0:6 3:1 2:66 3:1 0:22")
    c.row(52, "0:6 3:68 0:22")
    c.paste(34, 53, STONE)
    c.paste(50 if dmg else 48, 53, STONE)                     # DMG: both stepping stones on the same phase of the 8 px grid
    if new:
        c.paste(73, 36, LANT)                                             # round 5: the second lantern, same 8 px column phase as the first (x 1 and x 73), same row phase (36 and 44)
    c.paste(1, 36, LANT)                                                  # PASS: two rows higher, its base no longer fuses with the veranda's left end
    # ---- the cherry tree (unchanged) ---------------------------------------------------------------------------------------------------
    c.paste(80, 34, TREE)
    texture(c, os.environ.get("SMAP_TEA_TEX", "A"), dmg)
    return c


# ---- TEXTURE (owner: "better, but needs more texture").  A hand-typed 8 px course tile, repeated across the roofs on the absolute 8 px column grid, so every interior roof
# cell of a course row is the same tile (the cost is a handful of ids, not one per cell).  Each course is a shadow joint (ink, 6 px, gap 2) with the next course's joint
# shifted 4 px (staggered like shingles), 3 rows apart; the lit side stays the cream taper at the left slope (light from the top left).  A dash is painted only if the
# whole dash and 2 px either side are roof body (2), so the ink outline, the taper and the eaves stay clean.
JOINT_A, JOINT_B = "33333322", "33223333"
CAP_A, CAP_B = "11222222", "22221122"          # a 2 px lit cap under the left end of each joint (paper shade, the course's lit top edge), same 4 px shift
ROOF_UP = {4: JOINT_A, 5: CAP_A, 7: JOINT_B}              # upper roof rows y
ROOF_LO = {19: JOINT_A, 20: CAP_A, 22: JOINT_B, 23: CAP_B}          # lower roof rows y


# ---- OPTION B: kawara tile ribs.  An 8 px tile typed by hand: RIB_ROW is the body of a roof row (a lit cream pixel left of an ink rib line every 4 px, light from the top
# left), END_ROW the eave row (round tile ends: light and dark pixels alternating).  Ribs run down the slope; painted only on roof body pixels, so outlines and the left-slope
# taper stay clean.  Posts stay plain.
RIB_ROW, END_ROW = "22132213", "13131313"
RIBS_UP, ENDS_UP = range(3, 8), 8
RIBS_LO, ENDS_LO = range(17, 23), 23


def ribs(c):
    for rows, end in ((RIBS_UP, ENDS_UP), (RIBS_LO, ENDS_LO)):
        for y in list(rows) + [end]:
            pat = END_ROW if y == end else RIB_ROW
            r = c.px[y]
            keep = list(r)
            for x in range(1, W - 1):
                if pat[x % 8] == "2":
                    continue
                if keep[x] != "2":
                    continue
                if pat[x % 8] == "1" and keep[x + 1] != "2":      # a lit pixel only beside its rib
                    continue
                r[x] = pat[x % 8]


# ---- WALLS (owner: "ribs look good but walls need some texture too").  Only inside cells that already own a tile; the repeated cells (the panel pairs at x24..31 and x48..55, the
# veranda ends) get the same pixels in both.  Quiet: long thin grain lines in ink on the 2 px wood members (a line flows around a knot by one jog), a bottom row of ordered
# 1/2 dither on every shoji panel (paper shade), nothing on the door.  (Posts: see walls().)
def walls(c):
    px = c.px
    # posts: a thin lit grain line (paper shade) down the outer column of each wall post (x13, x66) that jogs one column in around a knot, and down the door-side column of the door
    # posts (x33, x46); the lit line is what stays quiet against the dark wood and the outline
    for x, jog in ((13, 14), (66, 65)):
        for y in range(29, 47):
            px[y][jog if (jog and y in (36, 37)) else x] = "1"
    # panels: a quiet shade at the bottom of each paper panel, a sparse ordered 1/2 dither (every 4th pixel), light from the top left
    for y in (32, 37, 42, 47):
        for x in range(15, 65):
            if px[y][x] == "1" and x % 4 == 0 and not 34 <= x <= 45:      # not on the door
                px[y][x] = "2"


def valance(c):
    """C4: a short noren along the whole front, x16..63, rows y28..31 under the beam: brown cloth, a cream hem stripe on the third row, an ink slit at every x divisible by 8.
    The pattern repeats on the 8 px grid, so the two cells x24..31 and x48..55 that share a tile still do."""
    for x in range(16, 64):
        slit = x % 8 == 0
        c.px[28][x] = "3" if slit else "2"
        c.px[29][x] = "3" if slit else "2"
        c.px[30][x] = "3" if slit else "1"
        c.px[31][x] = "3" if slit else "2"


def texture(c, level, dmg):
    if level == "none":
        return
    if level in ("B", "BW", "BWD", "BWN", "C1", "C2", "C3", "C4"):
        ribs(c)
        light_b = True
        if level in ("BW", "BWD", "BWN", "C1", "C2", "C3", "C4"):
            walls(c)
    else:
        light_b = False
    for rows in (() if light_b else (ROOF_UP, ROOF_LO)):
        for y, pat in rows.items():
            if level == "light" and "1" in pat:
                continue
            ink = "3" if "3" in pat else "1"
            r = c.px[y]
            keep = list(r)
            x = 0
            while x < W:
                if pat[x % 8] != ink:
                    x += 1
                    continue
                x1 = x
                while x1 < W and pat[x1 % 8] == ink:
                    x1 += 1
                ok = x1 - x >= 2 and x >= 2 and all(keep[xx] == "2" for xx in range(x - 2, min(W, x1 + 2)))
                if ok and not (rows is ROOF_LO and x < 48 and x1 > 32):      # under the tower (x32..47): its shadow, left plain; those two cells already share a tile with the rest of the map
                    for xx in range(x, x1):
                        r[xx] = ink
                x = x1
    if level == "light":
        return
    # wall posts: grain, short dark dashes in the inner column of each post, staggered left and right (posts are x13-14 and x65-66); option B leaves the posts plain
    for x, ys in (() if light_b else ((14, (29, 30, 31, 32, 36, 37, 41, 42, 44, 45, 46, 47)), (65, (30, 31, 34, 35, 36, 40, 41, 42, 46, 47)))):
        for y in ys:
            c.px[y][x] = "3"
    # the veranda: board ends every 16 px, a shade-2 notch on the lit top plane and an ink notch on the front face in the same column
    for x in (38, 54, 70):
        c.px[50][x] = "2"
        c.px[51][x] = "3"
    # stepping stones: a shadow on the lower right (2), the lit left stays paper
    for sx in (34, 50 if dmg else 48):
        c.px[54][sx + 5] = "2"
        c.px[54][sx + 6] = "2"
