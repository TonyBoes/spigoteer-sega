"""The mockups (every animated pixel is typed here; anim_lib only composes, previews and measures).
Index key in the typed tiles:  '.' 0 (lightest)  '-' 1  '+' 2  '#' 3 (darkest).  Timing in video frames at 60 fps; every period is a multiple of 3 (the GIFs step 3 frames = 50 ms).
Scene: the A5 map with the approved art wired in (mapctx.py): brown logs, fountain round 3, stadium option 2 + wavy flag, igloo option 1, airbase round 4i, milk bar round 4i."""
from anim_lib import E, Item, TileAnim, T, region_anims

# -------------------------------------------------------------------------------------------------------------------------------------------------
# 1  WATER: the glint tiles WA and WB (every open-water cell uses WF, WA or WB; WF stays flat).  The 2-pixel glint stairs slide 1 px left and right, never leaving the tile.
#    Ping-pong 0, -1, 0, +1; WB steps 6 frames after WA so only one 16-byte tile is rewritten at a time.
WA_L1 = T("++++++++", "++++++++", "--++++++", "++--++++", "++++--++", "++++++++", "++++++++", "++++++++")
WA_R1 = T("++++++++", "++++++++", "++--++++", "++++--++", "++++++--", "++++++++", "++++++++", "++++++++")
WB_L1 = T("++++++++", "++++++++", "++++++++", "+--+++++", "+++--+++", "++++++++", "++++++++", "++++++++")
WB_R1 = T("++++++++", "++++++++", "++++++++", "+++--+++", "+++++--+", "++++++++", "++++++++", "++++++++")


def water(a5):
    wa = a5.cells_with(T("++++++++", "++++++++", "+--+++++", "+++--+++", "+++++--+", "++++++++", "++++++++", "++++++++"))
    wb = a5.cells_with(T("++++++++", "++++++++", "++++++++", "++--++++", "++++--++", "++++++++", "++++++++", "++++++++"))
    return Item("01_water", "Water glints (shared tiles WA, WB)", a5, (272, 392),
                [TileAnim("WA", wa[0], [WA_L1, WA_R1], [0, 1, 0, 2], 15, 0), TileAnim("WB", wb[0], [WB_L1, WB_R1], [0, 2, 0, 1], 15, 6)],
                focus=(300, 404, 364, 436))


# -------------------------------------------------------------------------------------------------------------------------------------------------
# 2  WATERFALL: the four falls tiles (2 x 2 cells at 46..47, 5..6) and the splash pair (46..47, 8).  Streaks fall 5 rows per step over the 15 flowing rows (the 16th row is the
#    pool edge and stays); three frames close the loop exactly (3 x 5 = 15).  Splash: a small centred ring (new tile C) and the two arcs A and B, in turn.
FL_A1 = T("#++-++++", "#+++++-+", "#+++++-+", "#+-+++-+", "#+-+++++", "#+++++-+", "#+-+++-+", "#+-+++++")
FL_B1 = T("#+-+++++", "#++++-++", "#++++-++", "#++++-++", "#+++++++", "#+++++++", "#++-++++", "...-++++")
FL_A2 = T("#++++-++", "#++++-++", "#+++++++", "#+++++++", "#++-++++", "#++-++++", "#+++++-+", "#+++++-+")
FL_B2 = T("#+-+++-+", "#+-+++++", "#+++++-+", "#+-+++-+", "#+-+++++", "#+-+++++", "#++++-++", "...-++++")
FR_A1 = T("++-++++#", "+++++-+#", "+++++-+#", "+++-+++#", "+++-+++#", "+-+++++#", "+-+++++#", "+++++-+#")
FR_B1 = T("+++-+-+#", "+++-+++#", "+++-+++#", "+++++++#", "+++++++#", "+++++++#", "++-++++#", "++++-...")
FR_A2 = T("+++-+++#", "+++++++#", "+++++++#", "+++++++#", "++-++++#", "++-++++#", "+++++-+#", "+++++-+#")
FR_B2 = T("+++-+++#", "+++-+++#", "+-+++++#", "+-+++++#", "+++++-+#", "+++-+-+#", "+++-+++#", "++++-...")
SPL_A = T("++++++++", "++---+++", "+-+++-++", "++++++++", "++++++++", "++++--++", "+++-++-+", "++++++++")
SPL_B = T("++++++++", "++++---+", "++-+++-+", "++++++++", "+++--+++", "++-++-++", "++++++++", "++++++++")
SPL_C = T("++++++++", "++++++++", "+++--+++", "++-++-++", "++-++-++", "+++--+++", "++++++++", "++++++++")


def falls(a5):
    return Item("02_falls", "Waterfall and splash (4 + 2 tiles)", a5, (304, 0),
                [TileAnim("FL_A", (46, 5), [FL_A1, FL_A2], [0, 1, 2], 12), TileAnim("FL_B", (46, 6), [FL_B1, FL_B2], [0, 1, 2], 12),
                 TileAnim("FR_A", (47, 5), [FR_A1, FR_A2], [0, 1, 2], 12), TileAnim("FR_B", (47, 6), [FR_B1, FR_B2], [0, 1, 2], 12),
                 TileAnim("SPL_L", (46, 8), [SPL_B, SPL_C], [0, 1, 0, 2], 12, 6), TileAnim("SPL_R", (47, 8), [SPL_A, SPL_C], [0, 1, 2, 1], 12, 6)],
                focus=(360, 32, 392, 72))


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


def radar(a5):
    assert a5.tile(14 + MTN_DX, 38) == DISH_0, a5.tile(14 + MTN_DX, 38)
    return Item("05_radar", "Radar dish turning (airbase tower, round 4i)", a5, (16, 262), [TileAnim("DISH", (14 + MTN_DX, 38), [DISH_1, DISH_2, DISH_3], [0, 1, 2, 3], 15)],
                focus=(80, 302, 100, 316))


# -------------------------------------------------------------------------------------------------------------------------------------------------
# 6a LODGE CHIMNEY: the existing puff (y 163-165) is frame 0; it rises and thins, drifting right, and a new one swells at the cap.  Colour: the four cells of the smoke take the
#    palette WATER (index 0 = the same grass colour b0d080, index 1 = the foam colour e8f0d8, near white), which every 21 x 19 window round the lodge already holds (the river is in
#    it), so no window gains a palette.  Side effect: the chimney's cap row (y 167, 8 px of index 3) in those cells turns from ink 2a1608 to the water palette's brown 905830.
def smoke_lodge(a5):
    for cx in (58, 59):
        for cy in (19, 20):
            a5.pal[cy][cx] = "water"
    P0 = {(x, y): 0 for (y, x0, x1) in ((163, 470, 473), (164, 469, 474), (165, 470, 473)) for x in range(x0, x1 + 1)}

    def fr(*runs):
        d = dict(P0)
        d.update(E(*[(y, x0, x1, 1) for (y, x0, x1) in runs]))
        return d
    f1 = fr((158, 471, 474), (159, 470, 475), (160, 471, 474), (165, 471, 472))
    f2 = fr((153, 474, 476), (154, 473, 477), (155, 474, 476), (164, 470, 473), (165, 471, 472))
    f3 = fr((152, 477, 478), (163, 471, 472), (164, 470, 473), (165, 471, 472))
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
# 8a MAST LAMP (airbase tower, cell 13,38): the lamp's centre pixel is index 0 (lit) and dims one step to 1; lit 60 frames, dim 30 frames (one blink per 1.5 s, 1.3 changes a second).
def lamp(a5):
    base = a5.tile(13 + MTN_DX, 38)
    dim = tuple(base[:1]) + (base[1][:5] + "1" + base[1][6:],) + tuple(base[2:])
    return Item("08a_lamp_mast", "Mast lamp, slow blink (airbase tower)", a5, (16, 262), [TileAnim("LAMP", (13 + MTN_DX, 38), [dim], [0, 0, 1], 30)], focus=(76, 300, 100, 316))


def all_items(a5):
    return [water(a5), falls(a5), fountain(a5), bunting(a5), stadium_flag(a5), radar(a5), smoke_lodge(a5), smoke_igloo(a5), smoke_factory(a5), cows(a5), lamp(a5)]
