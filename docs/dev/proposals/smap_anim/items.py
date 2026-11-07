"""The mockups (every animated pixel is typed here; anim_lib only composes, previews and measures).
Index key in the typed tiles:  '.' 0 (lightest)  '-' 1  '+' 2  '#' 3 (darkest).  Timing in video frames at 60 fps; every period is a multiple of 3 (the GIFs step 3 frames = 50 ms).
Scene: the A5 map with the approved art wired in (mapctx.py): brown logs, fountain round 3, stadium option 2 + wavy flag, igloo option 1, airbase round 4i, milk bar round 4i."""
from anim_lib import E, Item, TileAnim, T, region_anims

# -------------------------------------------------------------------------------------------------------------------------------------------------
# 1  WATER: the glint tiles WA and WB (every open-water cell uses WF, WA or WB; WF stays flat).  The 2-pixel glint stairs slide 1 px left and right, never leaving the tile.
#    Ping-pong with holds: rest, rest, -1, rest, rest, +1; WB steps half a period after WA so only one 16-byte tile is rewritten at a time.
# SUBTLE (owner: "the water glints could be more subtle"): fewer and smaller glints, slower.  Two strengths, both typed here.  Glint = index 1 on index 2 water: one DMG step; on Color the
# only lighter entry of the water palette is e8f0d8 (no mid shade sits between 58a0d8 and white, so contrast cannot drop on Color without a new palette: fewer pixels and a slower
# pace are the levers).  The static tiles WA and WB themselves carry fewer glints (new art for every WA/WB cell), 3 images each as before: the ROM cost is the same.
#   subtle      WA: a 2 px dash + 1 px (3 px, was 6), WB: one 2 px dash (2 px, was 4); steps every 24 frames, holding still 2 of every 3 steps.
#   very subtle WA: one 2 px dash, WB: one single pixel; steps every 30 frames, same hold.
WATER_OLD_A = T("++++++++", "++++++++", "+--+++++", "+++--+++", "+++++--+", "++++++++", "++++++++", "++++++++")
WATER_OLD_B = T("++++++++", "++++++++", "++++++++", "++--++++", "++++--++", "++++++++", "++++++++", "++++++++")
WS = dict(
    subtle=dict(A=[T("++++++++", "++++++++", "+--+++++", "++++++++", "++++++++", "++++++-+", "++++++++", "++++++++"),
                   T("++++++++", "++++++++", "--++++++", "++++++++", "++++++++", "+++++-++", "++++++++", "++++++++"),
                   T("++++++++", "++++++++", "++--++++", "++++++++", "++++++++", "+++++++-", "++++++++", "++++++++")],
                B=[T("++++++++", "++++++++", "++++++++", "++++++++", "+++--+++", "++++++++", "++++++++", "++++++++"),
                   T("++++++++", "++++++++", "++++++++", "++++++++", "++--++++", "++++++++", "++++++++", "++++++++"),
                   T("++++++++", "++++++++", "++++++++", "++++++++", "++++--++", "++++++++", "++++++++", "++++++++")], period=24),
    vsubtle=dict(A=[T("++++++++", "++++++++", "++++++++", "++--++++", "++++++++", "++++++++", "++++++++", "++++++++"),
                    T("++++++++", "++++++++", "++++++++", "+--+++++", "++++++++", "++++++++", "++++++++", "++++++++"),
                    T("++++++++", "++++++++", "++++++++", "+++--+++", "++++++++", "++++++++", "++++++++", "++++++++")],
                 B=[T("++++++++", "++++++++", "++++++++", "++++++++", "++++++++", "++++-+++", "++++++++", "++++++++"),
                    T("++++++++", "++++++++", "++++++++", "++++++++", "++++++++", "+++-++++", "++++++++", "++++++++"),
                    T("++++++++", "++++++++", "++++++++", "++++++++", "++++++++", "+++++-++", "++++++++", "++++++++")], period=30))


def water(a5, strength="vsubtle"):
    w = WS[strength]
    wa = a5.cells_with(WATER_OLD_A)
    wb = a5.cells_with(WATER_OLD_B)
    edits = {}
    for cells, tile in ((wa, w["A"][0]), (wb, w["B"][0])):
        for cx, cy in cells:
            for j, r in enumerate(tile):
                for i, c in enumerate(r):
                    edits[(cx * 8 + i, cy * 8 + j)] = int(c)
    p = w["period"]
    seq = [0, 0, 1, 0, 0, 2]
    seqb = [0, 0, 2, 0, 0, 1]
    return Item("01_water", f"Water glints, {strength.replace('vsubtle', 'very subtle')} (shared tiles WA, WB)", a5, (272, 392),
                [TileAnim("WA", wa[0], [w["A"][1], w["A"][2]], seq, p, 0), TileAnim("WB", wb[0], [w["B"][1], w["B"][2]], seqb, p, p // 2)],
                edits=edits, focus=(300, 404, 364, 436))


# -------------------------------------------------------------------------------------------------------------------------------------------------
# 2  WATERFALL, REDRAWN as a drop (owner: "the waterfall at this point reads more like river than a falls. bottom probably needs foam").  environments.md 11: "Waterfalls: 1-px vertical
#    streaks of a lighter shade at varied lengths and speeds, edges that jitter by 1 px, and an impact of sparkle pixels plus ripple rings." / "Droplets and foam: compact at rest, a
#    stretched streak mid-flight, compact on landing."  The four falls tiles (2 x 2 cells at 46..47, 5..6) are now mostly FOAM (index 1) with the water (index 2) showing as long
#    vertical streaks between it, and the pool's first two cells (46..47, 7), rows 0-5, carry a churning foam band: solid across the pool at its top (it spills 3 px wider than the falls
#    on each side), breaking into foam holes, bubbles and a few spray pixels below.  Kept pixel-exact: the bank rims (land 0, rim 1) at both sides of every falls row and of the pool's
#    four widening rows; pool rows 6-7 of the foot cells (they join the splash cells below); the splash cells themselves.  NEW STATIC ART: the 4 falls tiles + 2 foot tiles change on the map.
#    Falls: the 12 flowing rows (0-11) fall 3 rows a step, 4 frames, 9 video frames a step (the aliasing note: a step must stay smaller than the gaps between streaks); the lower four
#    rows (12-15) are a fixed foam lead-in.  Foot band: bubbles move gently, one picture held 18 frames, 3 pictures.  Splash (pool, below): ring and arcs in turn on the same 36 frames.
#    Falls columns f0..f7 (f0 = left tile col 4 ... f3 = col 7; f4 = right tile col 0 ... f7 = col 3), '-' foam / '+' water, rows 0-11 of frame 0 (typed):
FALL_COLS = ["++-+++-+++-+", "-------++--+", "++---+++---+", "----++-----+", "--+++----++-", "+++---++---+", "-----+++---+", "+++-++-+++-+"]
FALL_FOOT = ["+--+---+", "+------+", "+-----+-", "--------"]                  # rows 12-15, f0..f7
FALL_STEP, FALL_FRAMES = 3, 4
SPL_A = T("++++++++", "++---+++", "+-+++-++", "++++++++", "++++++++", "++++--++", "+++-++-+", "++++++++")
SPL_B = T("++++++++", "++++---+", "++-+++-+", "++++++++", "+++--+++", "++-++-++", "++++++++", "++++++++")
SPL_C = T("++++++++", "++++++++", "+++--+++", "++-++-++", "++-++-++", "+++--+++", "++++++++", "++++++++")
# the foot cells (pool rows 0-5), bubbling: A is the static picture; '.' land, '-' foam or rim, '+' water; rows 6-7 are the pool's own water
FOOT_L = [T("...-----", "..------", ".-------", "--+---+-", "+-++-+-+", "+++-+++-", "++++++++", "++++++++"),
          T("...-----", "..------", ".------+", "-+----+-", "++-+-+-+", "++-+++-+", "++++++++", "++++++++"),
          T("...-----", "..------", ".-----+-", "--+--+--", "+-+++-+-", "+++++-++", "++++++++", "++++++++")]
FOOT_R = [T("-----...", "------..", "-------.", "-+---+--", "-+-++-++", "++-+++-+", "++++++++", "++++++++"),
          T("-----...", "------..", "-----+-.", "+-----+-", "-++-+-++", "+++-++-+", "++++++++", "++++++++"),
          T("-----...", "------..", "-+-----.", "-+--+---", "+-++-++-", "++++-+++", "++++++++", "++++++++")]


def fall_rows(side, k):
    """16 tile rows (8 px each) of one falls column pair on frame k: foam moves DOWN, 3 rows a step"""
    cols = range(0, 4) if side == "L" else range(4, 8)
    out = []
    for r in range(16):
        row = list("...-++++" if side == "L" else "++++-...")
        for i, f in enumerate(cols):
            if r < 12:
                foam = FALL_COLS[f][(r - FALL_STEP * k) % 12] == "-"
            else:
                foam = FALL_FOOT[r - 12][f] == "-"
            if foam:
                row[4 + i if side == "L" else i] = "-"
        out.append("".join(row))
    return out


def fall_tiles():
    f = {}
    for side, (n_a, n_b) in (("L", ("FL_A", "FL_B")), ("R", ("FR_A", "FR_B"))):
        for k in range(FALL_FRAMES):
            rows = fall_rows(side, k)
            f[(n_a, k)] = T(*rows[:8])
            f[(n_b, k)] = T(*rows[8:])
    return f


def falls(a5):
    f = fall_tiles()
    cells = (("FL_A", (46, 5)), ("FL_B", (46, 6)), ("FR_A", (47, 5)), ("FR_B", (47, 6)))
    old_rim = {n: a5.tile(*c) for n, c in cells}
    for n, c in cells:                                                              # the bank rim columns must be exactly the map's (seam-fix art)
        for j in range(8):
            rim = (0, 1, 2, 3) if n[1] == "L" else (4, 5, 6, 7)
            assert all(old_rim[n][j][i] == f[(n, 0)][j][i] for i in rim), (n, j)
    foot_old = {c: a5.tile(*c) for c in ((46, 7), (47, 7))}
    for j in (0, 1, 2, 3):                                                          # the pool's widening rim, rows 0-3, kept
        for i in range(8):
            if foot_old[(46, 7)][j][i] in "01" and i < 4:
                assert FOOT_L[0][j][i] == foot_old[(46, 7)][j][i] or (j, i) in ((0, 3), (1, 2), (2, 1), (3, 0)), ("L", j, i)
    for j in (6, 7):
        assert FOOT_L[0][j] == foot_old[(46, 7)][j] and FOOT_R[0][j] == foot_old[(47, 7)][j]
    for n, (cx, cy) in cells:
        pass
    new_static = {(46, 5): f[("FL_A", 0)], (46, 6): f[("FL_B", 0)], (47, 5): f[("FR_A", 0)], (47, 6): f[("FR_B", 0)], (46, 7): FOOT_L[0], (47, 7): FOOT_R[0]}
    for (cx, cy), tile in new_static.items():                                       # NEW STATIC ART on the shared scene (every item that shows the falls sees it)
        for j, r in enumerate(tile):
            for i, c in enumerate(r):
                a5.px[cy * 8 + j, cx * 8 + i] = int(c)
    seq = list(range(FALL_FRAMES))
    an = [TileAnim(n, c, [f[(n, k)] for k in range(1, FALL_FRAMES)], seq, 9) for n, c in cells]
    bseq = [0, 0, 1, 1, 0, 0, 2, 2]
    an += [TileAnim("FOOT_L", (46, 7), [FOOT_L[1], FOOT_L[2]], bseq, 9, 3), TileAnim("FOOT_R", (47, 7), [FOOT_R[1], FOOT_R[2]], bseq, 9, 3)]
    an += [TileAnim("SPL_L", (46, 8), [SPL_B, SPL_C], [0, 1, 0, 2], 9, 3), TileAnim("SPL_R", (47, 8), [SPL_A, SPL_C], [0, 2, 0, 1], 9, 6)]
    return Item("02_falls", "Waterfall (foam drop) and splash pool", a5, (304, 0), an, focus=(352, 32, 400, 80))


# -------------------------------------------------------------------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------------------------------------------------------------------
# 3  FOUNTAIN, the approved centred one (smap_fountain/src/v_town_fx.py, round 3, working state): two thin spill streams (x 290-291 and 301-302, y 193-200, mirror images about x 296)
#    fall from the bowl's rim into the basin.  A glint (index 0) runs down each stream, 2 rows a step, in a 3-step loop (y 196, 198, 194); the two basin glints at y 201 slide 1 px
#    toward the middle and back, 12 frames apart from the streams.
def fountain(a5):
    s0 = {(290, 196): 1, (302, 196): 1}
    f1 = dict(s0)
    f1.update(E((290, 198, 0), (302, 198, 0)))
    f2 = dict(s0)
    f2.update(E((290, 194, 0), (302, 194, 0)))
    g0 = {(x, 201): 1 for x in (289, 290, 291, 301, 302, 303)}
    g1 = dict(g0)
    g1.update(E((201, 290, 292, 0), (201, 300, 302, 0)))
    an = region_anims(a5, {}, [f1, f2], [0, 1, 2], 12, 0, "streams") + region_anims(a5, {}, [g1], [0, 0, 1], 12, 6, "basin")
    return Item("03_fountain", "Town fountain: two streams and basin (approved round 3)", a5, (232, 136), an, focus=(280, 172, 316, 208))

# 4a BUNTING (town, y 162): flags P (index 2) and Q (index 3) hang from the string; the lower two rows of each flag swing 1 px right, back, 1 px left, back.  Q swings the
#    opposite way and 6 frames later.  P and Q are shared tiles (3 cells each); the end flag shares the swing but sits in a tile with the hall's roof, so it is its own tile.
P_R = T("........", "........", "########", "..+++++.", "....+++.", ".....+..", "........", "........")
P_L = T("........", "........", "########", "..+++++.", "..+++...", "...+....", "........", "........")
Q_R = T("........", "........", "########", "..#####.", "....#-#.", ".....#..", "........", "........")
Q_L = T("........", "........", "########", "..#####.", "..#-#...", "...#....", "........", "........")
END_R = T("........", "........", "########", "..+++++.", "....+++.", ".....+..", "..######", "..#-----")
END_L = T("........", "........", "########", "..+++++.", "..+++...", "...+....", "..######", "..#-----")


def bunting(a5):
    return Item("04a_bunting", "Town bunting", a5, (232, 136),
                [TileAnim("P", (33, 20), [P_R, P_L], [0, 1, 0, 2], 15, 0), TileAnim("Q", (34, 20), [Q_L, Q_R], [0, 1, 0, 2], 15, 6),
                 TileAnim("END", (39, 20), [END_R, END_L], [0, 1, 0, 2], 15, 0, only_at=True)],
                focus=(256, 154, 328, 172))


# -------------------------------------------------------------------------------------------------------------------------------------------------


# -------------------------------------------------------------------------------------------------------------------------------------------------
# 4b STADIUM, the approved one (smap_stadium: option 2, curved bowl, final 2 home dirt, wavy flag): the flag's three hand-drawn frames (FLAG_FRAMES in park_s2.py) are the animation; the
#    two flag cells differ per frame, the pole cell does not.  Wave period 6 columns, 2 columns a frame, so 3 frames close the loop.
def stadium_flag(a5):
    import mapctx as M
    s = M.SCENES["stadium"]
    ax, ay = s["at"]
    an = []
    for key in s["frames"][0]:
        t0 = tuple(s["frames"][0][key][0])
        t1, t2 = tuple(s["frames"][1][key][0]), tuple(s["frames"][2][key][0])
        if t0 != t1 or t0 != t2:
            i, j = map(int, key.split(","))
            an.append(TileAnim(f"flag({ax + i},{ay + j})", (ax + i, ay + j), [t1, t2], [0, 1, 2], 9, 0, only_at=True))
    return Item("04b_stadium_flag", "Stadium: the wavy flag (approved stadium)", a5, (0, 0), an, focus=(40, 4, 80, 28))


# -------------------------------------------------------------------------------------------------------------------------------------------------
# 5  RADAR DISH on the airbase tower (approved round 4i; cell 14,38): face-on, turning, edge-on, back (darker inside, pin on the other side).  Pin and post stay on their column.
DISH_0 = T("........", "........", "....#...", "..#####.", ".#.----#", ".#-----#", "..#####.", "....#...")
DISH_1 = T("........", "........", ".....#..", "...###..", "..#.--#.", "..#---#.", "...###..", "....#...")
DISH_2 = T("........", "........", "....#...", "...###..", "...#-#..", "...#-#..", "...###..", "....#...")
DISH_3 = T("........", "........", "...#....", "...###..", "..#+++#.", "..#+++#.", "...###..", "....#...")


MTN_DX = -3                       # mapctx.AT_OVERRIDE["mountain"] is (6, 36); the piece was dumped for (9, 36)


# AIRBASE = radar dish (cell 14,38) + mast lamp (cell 13,38) as ONE animation (owner: merge them): one loop of 120 video frames, one table entry.  The dish steps every 15 frames
#    through its four views twice; the lamp (the centre pixel is index 0 = lit) dims one step to index 1 for the last 2 of the 8 dish steps, so it blinks once every 2 s (2 changes
#    in 2 s = 1 a second).  The lamp's two writes sit 6 frames off the dish steps, so a frame never rewrites more than one of the two tiles.
def airbase(a5):
    assert a5.tile(14 + MTN_DX, 38) == DISH_0, a5.tile(14 + MTN_DX, 38)
    base = a5.tile(13 + MTN_DX, 38)
    dim = tuple(base[:1]) + (base[1][:5] + "1" + base[1][6:],) + tuple(base[2:])
    return Item("05_airbase", "Airbase: radar dish turning and mast lamp blinking (one frame set, round 4i art)", a5, (16, 262),
                [TileAnim("DISH", (14 + MTN_DX, 38), [DISH_1, DISH_2, DISH_3], [0, 1, 2, 3, 0, 1, 2, 3], 15),
                 TileAnim("LAMP", (13 + MTN_DX, 38), [dim], [0, 0, 0, 0, 0, 0, 1, 1], 15, 6)], focus=(76, 300, 100, 316))


# -------------------------------------------------------------------------------------------------------------------------------------------------
# 6a LODGE CHIMNEY (second fix): the chimney cap row (y 167, 8 px of ink) must keep its colour, and it shares the cells (58,20), (59,20) with the old tan puff (y 163-165).  No palette
#    already in the lodge windows has grass as index 0, a near-white index 1 AND the lodge's ink as index 3, so the smoke leaves those two cells: the tan puff is erased (the cells keep
#    the lodge palette and the cap exactly as approved) and the white smoke lives in the two cells above, (58,19) and (59,19), y 152-159, on the palette WATER (index 0 = the grass colour
#    b0d080, index 1 = e8f0d8), which every 21 x 19 window round the lodge already holds.  Cost: the rest puff floats 7 px above the cap (y 157-159) instead of sitting on it.
def smoke_lodge(a5):
    for cx in (58, 59):
        a5.pal[19][cx] = "water"
    for (y, x0, x1) in ((163, 469, 474), (164, 469, 474), (165, 469, 474)):         # the old tan puff goes (index 0 = grass)
        for x in range(x0, x1 + 1):
            a5.px[y, x] = 0
    for (y, x0, x1) in ((157, 470, 473), (158, 469, 474), (159, 470, 473)):         # the rest puff, index 1 = white smoke
        for x in range(x0, x1 + 1):
            a5.px[y, x] = 1

    def fr(*runs):
        d = {(x, y): 0 for (y, x0, x1) in ((157, 470, 473), (158, 469, 474), (159, 470, 473)) for x in range(x0, x1 + 1)}
        d.update(E(*[(y, x0, x1, 1) for (y, x0, x1) in runs]))
        return d
    f1 = fr((153, 471, 474), (154, 470, 475), (155, 471, 474), (159, 471, 472))
    f2 = fr((152, 474, 475), (153, 473, 476), (158, 471, 472), (159, 470, 473))
    f3 = fr((157, 471, 472), (158, 470, 473), (159, 470, 473))
    return Item("06a_smoke_lodge", "Lodge chimney smoke (white, not tan)", a5, (352, 120), region_anims(a5, {}, [f1, f2, f3], [0, 1, 2, 3], 15, 0, "lodge"), focus=(456, 148, 488, 172))


# 6c IGLOO CHIMNEY (the approved igloo, option 1: stove pipe with a 6 x 4 puff in ice colours, indices 1 and 2): the puff is frame 0 in cell (56, 5).  The puff cannot rise out of the piece
#    (the cell row above is the range box on A5's map), so it swells in place: a small puff at the cap, a medium one, the full one, then it breaks up into wisps.
IG_1 = T("........", "........", "...--...", "..-++-..", ".######.", ".#--++#.", ".######.", "..#-+#..")
IG_2 = T("........", "...--...", "..----..", ".-+++++.", ".######.", ".#--++#.", ".######.", "..#-+#..")
IG_3 = T("..-..-..", "...-....", "........", "........", ".######.", ".#--++#.", ".######.", "..#-+#..")


def smoke_igloo(a5):
    return Item("06c_smoke_igloo", "Igloo chimney smoke (approved igloo)", a5, (352, 0), [TileAnim("IGLOO", (56, 5), [IG_1, IG_2, IG_3], [1, 2, 0, 3], 15, 0, only_at=True)],
                focus=(432, 24, 472, 64))

# 6b FACTORY STACKS (two): each existing puff is frame 0.  Right stack: free sky above.  Left stack: log piles stand right above it, so its smoke drifts LEFT of them (x <= 423).
def smoke_factory(a5):
    PR = {(x, y): 0 for (y, x0, x1) in ((305, 483, 486), (306, 481, 488), (307, 483, 486)) for x in range(x0, x1 + 1)}
    PL = {(x, y): 0 for (y, x0, x1) in ((304, 423, 426), (305, 421, 428), (306, 423, 426)) for x in range(x0, x1 + 1)}

    def fr(base, *runs):
        d = dict(base)
        d.update(E(*[(y, x0, x1, 1) for (y, x0, x1) in runs]))
        return d
    r1 = fr(PR, (301, 484, 486), (302, 483, 487), (303, 484, 486), (306, 484, 485))
    r2 = fr(PR, (297, 485, 486), (298, 484, 487), (299, 485, 486), (305, 483, 486), (306, 484, 485))
    r3 = fr(PR, (296, 486, 487), (305, 483, 486), (306, 482, 487), (307, 484, 485))
    l1 = fr(PL, (300, 418, 420), (301, 417, 421), (302, 418, 420), (305, 424, 425))
    l2 = fr(PL, (296, 417, 418), (297, 416, 419), (298, 417, 418), (304, 423, 426), (305, 424, 425))
    l3 = fr(PL, (304, 423, 426), (305, 422, 427), (306, 424, 425))
    an = region_anims(a5, {}, [r1, r2, r3], [0, 1, 2, 3], 15, 0, "factory R") + region_anims(a5, {}, [l1, l2, l3], [0, 1, 2, 3], 15, 6, "factory L")
    return Item("06b_smoke_factory", "Factory stack smoke (two stacks)", a5, (352, 232), an, focus=(412, 290, 492, 312))


# -------------------------------------------------------------------------------------------------------------------------------------------------


# -------------------------------------------------------------------------------------------------------------------------------------------------
# 7  COW TAILS on the approved milk bar (round 4h/4i: pasture with two cows, a lawn cow).  The cows have no tail today.  A 4-px tail with a pink tuft is added at the rear (the rear edge of a
#    cow is its 14th column, the tail starts one pixel right of it): hanging, then swinging out right and back, resting between flicks.  Pasture cow 1 (x 428..441, top y 394) and
#    pasture cow 2 (x 462..475, top y 412; the tail starts 2 rows lower so it stays in one tile) are animated, 18 frames apart.  The lawn cow (x 401..414) stands one pixel from the
#    bottle sign's pole, so there is no room for a swing and it stays as it is.
def cows(a5):
    def tail(x, y, shape):
        if shape == 0:
            return E((x, y, 3), (x, y + 1, 3), (x, y + 2, 3), (x, y + 3, 2))
        if shape == 1:
            return E((x, y, 3), (x, y + 1, 3), (x + 1, y + 2, 3), (x + 1, y + 3, 2))
        return E((x, y, 3), (x + 1, y + 1, 3), (x + 2, y + 2, 3), (x + 3, y + 3, 2))

    def build(x, y):
        f = []
        for s in (1, 2):
            d = {(x + dx, y + dy): 0 for dx in range(4) for dy in range(4)}
            d.update(tail(x, y, s))
            f.append(d)
        return tail(x, y, 0), f
    s1, f1 = build(442, 396)
    s2, f2 = build(476, 416)
    static = dict(s1)
    static.update(s2)
    an = region_anims(a5, static, f1, [0, 0, 0, 1, 2, 1], 12, 0, "cow1") + region_anims(a5, static, f2, [0, 0, 0, 1, 2, 1], 12, 18, "cow2")
    return Item("07_cow_tail", "Cow tail swish (pasture cows, new tail art)", a5, (352, 352), an, edits=static, focus=(424, 390, 484, 424))




# -------------------------------------------------------------------------------------------------------------------------------------------------
# 9  LOGS BOB (owner: "can we make the logs bob in the water?"): the 12 v1 single logs (7 across, 5 upright) float on flat water (WF), so their cells carry no water glints and need no
#    shared frame set with the glints.  A across log (2 cells, 16 x 8) sinks 1 px and comes back; an upright log (2 cells, 8 x 16) rises 1 px and comes back (its bottom row is the last
#    row of its cell, so sinking would have to write the cell below; rising only needs its own two cells).  The log moves with its ripple (across) and the water refills the row it leaves.
#    One step every 36 frames (0.6 s), rest for 3 steps, down 1, up 1: a 180-frame loop (the same as the water glints), 2 changes in 3 s; every step lands off the falls (9) and water (15) steps.  A tile id is rewritten once for every log that shares it, so the logs are split into
#    three phase groups A, B, C (own tile ids per group, same 2 pictures): the groups bob 30 or more frames apart and a step never rewrites more than 2 tiles.
LOG_HL = T("22222222", "22233333", "22331113", "22333333", "22333311", "22233333", "21122222", "22222222")
LOG_HR = T("22222222", "33333332", "33331113", "33331313", "13331113", "33333332", "22222112", "22222222")
LOG_HL_B = T("22222222", "22222222", "22233333", "22331113", "22333333", "22333311", "22233333", "21122222")
LOG_HR_B = T("22222222", "22222222", "33333332", "33331113", "33331313", "13331113", "33333332", "22222112")
LOG_VT = T("21122222", "22222222", "22333222", "23333322", "23133322", "23133322", "23133322", "23333322")
LOG_VB = T("23331322", "23331322", "23331322", "23333322", "23111322", "23131322", "23111322", "22333222")
LOG_VT_B = T("22222222", "22333222", "23333322", "23133322", "23133322", "23133322", "23333322", "23331322")
LOG_VB_B = T("23331322", "23331322", "23333322", "23111322", "23131322", "23111322", "22333222", "22222222")
LOGS_H = {"A": [(48, 33), (42, 52), (44, 68)], "B": [(54, 33), (43, 57)], "C": [(57, 32), (42, 65)]}        # left cell of each across log
LOGS_V = {"A": [(46, 20), (45, 43)], "B": [(46, 29), (45, 46)], "C": [(46, 36)]}                         # top cell of each upright log
LOG_PH_H = {"A": 6, "B": 66, "C": 120}
LOG_PH_V = {"A": 12, "B": 75, "C": 141}


def logs(a5):
    an = []
    for g, lst in LOGS_H.items():
        for (x, y) in lst:
            assert a5.tile(x, y) == LOG_HL and a5.tile(x + 1, y) == LOG_HR, (x, y)
        an.append(TileAnim(f"H{g}_L", lst[0], [LOG_HL_B], [0, 0, 0, 1, 0], 36, LOG_PH_H[g], cells_list=tuple(lst)))
        an.append(TileAnim(f"H{g}_R", (lst[0][0] + 1, lst[0][1]), [LOG_HR_B], [0, 0, 0, 1, 0], 36, LOG_PH_H[g], cells_list=tuple((x + 1, y) for x, y in lst)))
    for g, lst in LOGS_V.items():
        for (x, y) in lst:
            assert a5.tile(x, y) == LOG_VT and a5.tile(x, y + 1) == LOG_VB, (x, y)
        an.append(TileAnim(f"V{g}_T", lst[0], [LOG_VT_B], [0, 0, 0, 1, 0], 36, LOG_PH_V[g], cells_list=tuple(lst)))
        an.append(TileAnim(f"V{g}_B", (lst[0][0], lst[0][1] + 1), [LOG_VB_B], [0, 0, 0, 1, 0], 36, LOG_PH_V[g], cells_list=tuple((x, y + 1) for x, y in lst)))
    return Item("09_logs", "Floating logs bobbing (v1 logs, three phase groups)", a5, (336, 224), an, focus=(376, 232, 480, 296))


def all_items(a5):
    return [water(a5, "vsubtle"), falls(a5), fountain(a5), bunting(a5), stadium_flag(a5), airbase(a5), smoke_lodge(a5), smoke_igloo(a5), smoke_factory(a5), cows(a5), logs(a5)]
