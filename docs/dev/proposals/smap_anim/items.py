"""The eleven mockups (every animated pixel is typed here; anim_lib only composes, previews and measures).
Index key in the typed tiles:  '.' 0 (lightest)  '-' 1  '+' 2  '#' 3 (darkest).  Timing in video frames at 60 fps; every period is a multiple of 3 (the GIFs step 3 frames = 50 ms).
Scenes: 'a5' is the whole A5 map; 'mountain' and 'stadium' are the round-3 pieces over their biome's ground (A5's map still has boxes there)."""
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
# 3  FOUNTAIN (placeholder on today's fountain; another artist redraws it).  Water jet: the four sparkle pixels (index 0) blink in two groups, the basin glint slides.
#    Group A = rows 188 and 195, group B = rows 192 and 199 (absolute y); a sparkle "off" is the jet's own index 1.
def fountain(a5):
    A_OFF = E((304, 188, 1), (307, 195, 1))
    B_OFF = E((306, 192, 1), (308, 199, 1))
    # basin glint (cell 38,25): base glint = (309,204) and (307,205),(308,205); one step right, one step left (typed per pixel)
    G0 = {k: 1 for k in [(309, 204), (307, 205), (308, 205)]}
    G_R = dict(G0); G_R.update(E((310, 204, 0), (308, 205, 0), (309, 205, 0)))
    G_L = dict(G0); G_L.update(E((308, 204, 0), (306, 205, 0), (307, 205, 0)))
    f1 = dict(A_OFF); f1.update(G_R)
    f2 = dict(B_OFF); f2.update(G_L)
    return Item("03_fountain", "Town fountain, repaired (placeholder)", a5, (240, 136),
                region_anims(a5, {}, [f1, f2], [0, 1, 0, 2], 12, 0, "fountain"), focus=(288, 172, 320, 212))


# -------------------------------------------------------------------------------------------------------------------------------------------------
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
# 4b STADIUM PENNANTS.  The round-3 stadium has no pennants: two flagpoles are added on the back stand (x 81 and 105, standing on the roof line y 56), a pennant of index 1 each.
#    The pole tile and the flag tile are the same on both poles (shared); the flag's tip rises, rests, drops.
def pennants(st):
    ed = {}
    for px_ in (81, 105):
        for y in range(40, 56):
            ed[(px_, y)] = 3
    flag0 = [(41, 2, 3), (42, 2, 5), (43, 2, 7), (44, 2, 5), (45, 2, 3)]          # (y, x0 local, x1 local) of F0, local to the pole's x - 1
    flag1 = [(41, 2, 4), (42, 2, 6), (43, 2, 5), (44, 2, 3), (45, 2, 2)]
    flag2 = [(41, 2, 2), (42, 2, 3), (43, 2, 5), (44, 2, 6), (45, 2, 4)]
    def flag(frame, poles=(81, 105)):
        d = {}
        for px_ in poles:
            for (y, a, b) in frame:
                for x in range(a, b + 1):
                    d[(px_ - 1 + x, y)] = 1
        return d
    static = dict(ed)
    static.update(flag(flag0))
    f1 = {k: 0 for k in flag(flag0, (81,))}; f1.update(flag(flag1, (81,)))
    f2 = {k: 0 for k in flag(flag0, (81,))}; f2.update(flag(flag2, (81,)))
    # the flag cell of the two poles is the same image: animate by content (only_at False) on the first pole's cell
    an = region_anims(st, static, [f1, f2], [0, 1, 0, 2], 15, 0, "pennant", only_at=False)
    return Item("04b_pennants", "Stadium pennants (new art: the piece has none)", st, (16, 16), an, edits=static, focus=(72, 36, 120, 60))


# -------------------------------------------------------------------------------------------------------------------------------------------------
# 5  RADAR DISH on the space mountain's tower (one tile, cell 11,9): face-on, turning, edge-on, back (darker inside, pin on the other side).  Pin and post stay on the same column.
DISH_1 = T("........", "........", ".....#..", "...###..", "..#.--#.", "..#---#.", "...###..", "....#...")
DISH_2 = T("........", "........", "....#...", "...###..", "...#-#..", "...#-#..", "...###..", "....#...")
DISH_3 = T("........", "........", "...#....", "...###..", "..#+++#.", "..#+++#.", "...###..", "....#...")


def radar(mt):
    return Item("05_radar", "Radar dish turning (space mountain tower)", mt, (24, 24), [TileAnim("DISH", (11, 9), [DISH_1, DISH_2, DISH_3], [0, 1, 2, 3], 15)],
                focus=(76, 64, 104, 90))


# -------------------------------------------------------------------------------------------------------------------------------------------------
# 6a LODGE CHIMNEY: today's puff (6 x 3, index 1, y 163-165) is frame 0.  The puff rises and thins, drifting right, and a new one swells at the cap.
def smoke_lodge(a5):
    for cx in (58, 59):                                   # the two cells above the puff take the lodge palette (attribute only, index 0 = the same grass colour)
        a5.pal[19][cx] = "lodge"
    P0 = {(x, y): 0 for (y, x0, x1) in ((163, 470, 473), (164, 469, 474), (165, 470, 473)) for x in range(x0, x1 + 1)}

    def fr(*runs):
        d = dict(P0)
        d.update(E(*[(y, x0, x1, 1) for (y, x0, x1) in runs]))
        return d
    f1 = fr((158, 471, 474), (159, 470, 475), (160, 471, 474), (165, 471, 472))
    f2 = fr((153, 474, 476), (154, 473, 477), (155, 474, 476), (164, 470, 473), (165, 471, 472))
    f3 = fr((152, 477, 478), (163, 471, 472), (164, 470, 473), (165, 471, 472))
    return Item("06a_smoke_lodge", "Lodge chimney smoke", a5, (352, 120), region_anims(a5, {}, [f1, f2, f3], [0, 1, 2, 3], 15, 0, "lodge"), focus=(456, 148, 488, 172))


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
# 7  COW TAIL (milk bar, the cow whose body ends at x 415; the second cow likewise, 8 px right and 10 px down).  The cow has no tail today: a 4-px tail with a pink tuft is
#    added at rest (hanging straight), then swings out right, further out, back.  Two cows, offset in time.
def cows(a5):
    def tail(x, y, shape):
        if shape == 0:
            return E((x, y, 3), (x, y + 1, 3), (x, y + 2, 3), (x, y + 3, 3), (x, y + 4, 2))
        if shape == 1:
            return E((x, y, 3), (x, y + 1, 3), (x + 1, y + 2, 3), (x + 1, y + 3, 3), (x + 1, y + 4, 2))
        return E((x, y, 3), (x + 1, y + 1, 3), (x + 2, y + 2, 3), (x + 2, y + 3, 3), (x + 3, y + 4, 2))

    def build(x, y):
        f = []
        for s in (1, 2):
            d = {(x + dx, y + dy): 0 for dx in range(4) for dy in range(5)}
            d.update(tail(x, y, s))
            f.append(d)
        return tail(x, y, 0), f
    s1, f1 = build(416, 464)
    s2, f2 = build(424, 474)
    static = dict(s1)
    static.update(s2)
    # f1 touches cow 1's cell only, f2 cow 2's (the clear runs reset to 0 only where the tail was; base pixels there are 0 except the bike pixels of cow 2's cell,
    # which are not in the 4 x 5 box x 424..427, y 474..478: checked by the stats)
    an = (region_anims(a5, static, f1, [0, 0, 0, 1, 2, 1], 12, 0, "cow1") + region_anims(a5, static, f2, [0, 0, 0, 1, 2, 1], 12, 18, "cow2"))
    return Item("07_cow_tail", "Cow tail swish (new tail art)", a5, (352, 416), an, edits=static, focus=(396, 456, 432, 484))


# -------------------------------------------------------------------------------------------------------------------------------------------------
# 8a MAST LAMP (space mountain): the lamp's centre pixel is index 0 (lit) and dims one step to 1; lit 60 frames, dim 30 frames (one blink per 1.5 s, 1.3 changes a second).
LAMP_DIM = T("........", "....#-#.", "........", "........", "........", "........", "........", "........")


def lamp(mt):
    base = mt.tile(10, 9)
    dim = tuple(base[:1]) + (base[1][:5] + "1" + base[1][6:],) + tuple(base[2:])
    return Item("08a_lamp_mast", "Mast lamp, slow blink (space mountain)", mt, (24, 24), [TileAnim("LAMP", (10, 9), [dim], [0, 0, 1], 30)], focus=(76, 64, 104, 90))


# 8b STADIUM LIGHT TOWERS: each head has two rows of four lamps (index 0 in ink).  The top row dims one step (index 1) for 48 frames, the bottom row later: slow twinkle,
#    1.25 changes a second.  Both towers use the same head tile.
def mastlights(st):
    head = st.tile(6, 6)
    top = tuple([head[0], head[1].replace("0", "1"), head[2]] + list(head[3:]))
    bot = tuple(list(head[:3]) + [head[3].replace("0", "1")] + list(head[4:]))
    return Item("08b_lamps_stadium", "Stadium light-tower lamps (slow twinkle)", st, (16, 16), [TileAnim("HEAD", (6, 6), [top, bot], [0, 1, 0, 2], 48)], focus=(40, 40, 64, 60))


def all_items(a5, mt, st):
    return [water(a5), falls(a5), fountain(a5), bunting(a5), pennants(st), radar(mt), smoke_lodge(a5), smoke_factory(a5), cows(a5), lamp(mt), mastlights(st)]
