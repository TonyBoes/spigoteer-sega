"""The story map's tile animations (stage 3, owner go 11-09): the moving part of the 11 approved items (docs/dev/proposals/smap_anim, items.py at dc5c1781, the falls A cascade of
smap_falls_v2 f9d94afa) and the runway lights (owner Q13), as the generator and the engine take them.

Every animation is one GROUP: a set of map cells that show one tile image, the group's frame images (8 x 8, indices 0..3: image 0 is the tile as the map holds it, the rest are
typed here or the same pixels with the typed edits) and a schedule of 256 ticks: key[t] = the image the tile shows from tick t on.  The engine's clock is the map's frame counter
V_TICK (a byte), so the loop is 256 frames = 4.27 s and every item is retimed to close at 256 (a whole number of steps per loop: the step is the approved period to within 1 frame in
10 or so; the water is slower, the owner asked for "very subtle").  The engine writes a group's tile in VRAM when its image changes (an event), only when the tile is resident.

Frame art: every animated pixel is typed here (T(...) rows, E(...) runs) or kept from the map itself.  Nothing is drawn by code.  Index key in typed tiles: '.' 0 '-' 1 '+' 2 '#' 3.

DMG: the DMG data set (world_d.png) is the Color set's pixels with light water, hand trims and a few shifted puffs, so a group's DMG images are derived from the DMG tile at the same
cell, not copied from Color:
  - items with the same pixels in both sets (smoke, fountain, bunting, flag, radar, cow tails, runway lights, the cascade): the same frames (asserted equal bases);
  - water items (the glints, the falls, the foam lip): the cells that change take the DMG water mapping (Color foam 1 -> DMG 0, Color water 2 -> DMG 1), the rest stays the DMG tile;
  - logs: the same row moves as Color, applied to the DMG tile (the DMG log's body shades differ);
  - the factory's rest puffs sit elsewhere in the DMG set (hand trim, tile merge): the smoke's frames are moved with them.
"""

LOOP = 256


def T(*rows):
    assert len(rows) == 8 and all(len(r) == 8 for r in rows), rows
    m = {".": 0, "-": 1, "+": 2, "#": 3, "0": 0, "1": 1, "2": 2, "3": 3}
    return tuple(m[c] for r in rows for c in r)


def E(*items):
    """typed pixel edits: (y, x0, x1, v) a run on row y, (x, y, v) one pixel: {(x, y): v}"""
    d = {}
    for it in items:
        if len(it) == 4:
            y, x0, x1, v = it
            for x in range(x0, x1 + 1):
                d[(x, y)] = v
        else:
            d[(it[0], it[1])] = it[2]
    return d


def clock(S, seq, ph=0):
    """the step clock: S steps in the 256 ticks (S a multiple of len(seq): the loop closes), step i shows seq[i % len(seq)]; ph ticks are added to the tick"""
    assert S % len(seq) == 0, (S, seq)
    return lambda t: seq[(((t + ph) % LOOP) * S // LOOP) % len(seq)]


class Group:
    def __init__(self, item, name, cells, imgs_c, imgs_d, key, note=""):
        self.item, self.name, self.cells = item, name, list(cells)
        self.imgs = {"c": list(imgs_c), "d": list(imgs_d)}
        self.key = list(key)                             # image index per tick (the same in both data sets)
        self.note = note
        for m in "cd":
            assert len(self.imgs[m]) == len(self.imgs["c"]) and all(len(i) == 64 for i in self.imgs[m]), name
            assert max(self.key) < len(self.imgs[m]), name
        assert len(self.key) == LOOP

    def still(self, m):
        """True when the group's frames are all the same picture in data set m (a DMG cell the puff never reaches): no animation there"""
        return all(i == self.imgs[m][0] for i in self.imgs[m])

    def events(self):
        """[(tick, image index)]: where the image changes (the loop wraps)"""
        return [(t, self.key[t]) for t in range(LOOP) if self.key[t] != self.key[t - 1]]


def tile(w, cx, cy):
    return tuple(w.px[cy * 8 + j][cx * 8 + i] for j in range(8) for i in range(8))


def with_edits(base, cx, cy, ed, shift=(0, 0)):
    """the 64 pixels of cell (cx, cy) with the pixel edits ed (world pixel coordinates, moved by shift) applied"""
    out = list(base)
    for (x, y), v in ed.items():
        x, y = x + shift[0], y + shift[1]
        if x // 8 == cx and y // 8 == cy:
            out[(y % 8) * 8 + x % 8] = v
    return tuple(out)


def delta(base_c, frame_c, base_d, mapping):
    """the DMG image of a Color frame: where the frame differs from the Color base the pixel takes mapping[Color value], elsewhere the DMG tile is kept"""
    return tuple((mapping[f] if f != c else d) for c, f, d in zip(base_c, frame_c, base_d))


WATER_MAP = {0: 0, 1: 0, 2: 1, 3: 3}                     # Color index -> DMG index where a water pixel changes (foam 1 -> 0, water 2 -> 1)


def build(WC, WD):
    """all the groups, from the Color and the DMG data sets (tools/smap_world/world_snap.py WORLD / WORLD_DMG)"""
    G = []
    tc = lambda cx, cy: tile(WC, cx, cy)
    td = lambda cx, cy: tile(WD, cx, cy)
    cw, ch = len(WC.px[0]) // 8, len(WC.px) // 8

    def cells_like(w, sig):
        return [(x, y) for y in range(ch) for x in range(cw) if tile(w, x, y) == sig]

    # ---- 01 water: the glint tiles WA and WB (every cell showing them), very subtle --------------------------------------------------------------------------------------------------
    WA = [T("++++++++", "++++++++", "++++++++", "++--++++", "++++++++", "++++++++", "++++++++", "++++++++"),
          T("++++++++", "++++++++", "++++++++", "+--+++++", "++++++++", "++++++++", "++++++++", "++++++++"),
          T("++++++++", "++++++++", "++++++++", "+++--+++", "++++++++", "++++++++", "++++++++", "++++++++")]
    WB = [T("++++++++", "++++++++", "++++++++", "++++++++", "++++++++", "++++-+++", "++++++++", "++++++++"),
          T("++++++++", "++++++++", "++++++++", "++++++++", "++++++++", "+++-++++", "++++++++", "++++++++"),
          T("++++++++", "++++++++", "++++++++", "++++++++", "++++++++", "+++++-++", "++++++++", "++++++++")]
    assert tc(46, 8) == WA[0] and tc(47, 8) == WB[0]
    d46, d47 = td(46, 8), td(47, 8)
    wa_cells, wb_cells = cells_like(WC, WA[0]), cells_like(WC, WB[0])
    assert cells_like(WD, d46) == wa_cells and cells_like(WD, d47) == wb_cells, "the DMG water glint cells differ from the Color ones"
    G.append(Group("01_water", "WA", wa_cells, WA, [d46] + [delta(WA[0], f, d46, WATER_MAP) for f in WA[1:]], [clock(6, [0, 0, 1, 0, 0, 2], 0)(t) for t in range(LOOP)]))
    G.append(Group("01_water", "WB", wb_cells, WB, [d47] + [delta(WB[0], f, d47, WATER_MAP) for f in WB[1:]], [clock(6, [0, 0, 2, 0, 0, 1], 21)(t) for t in range(LOOP)]))

    # ---- 02 falls: four falls tiles (foam moves down 3 rows a step), the foam lip's two cells (lip x pond glint), the cascade inside the mountain -------------------------------------
    FALL_COLS = ["++-+++-+++-+", "-------++--+", "++---+++---+", "----++-----+", "--+++----++-", "+++---++---+", "-----+++---+", "+++-++-+++-+"]
    FALL_FOOT = ["+--+---+", "+------+", "+-----+-", "--------"]

    def fall_rows(side, k):
        cols = range(0, 4) if side == "L" else range(4, 8)
        out = []
        for r in range(16):
            row = list("...-++++" if side == "L" else "++++-...")
            for i, f in enumerate(cols):
                foam = FALL_COLS[f][(r - 3 * k) % 12] == "-" if r < 12 else FALL_FOOT[r - 12][f] == "-"
                if foam:
                    row[4 + i if side == "L" else i] = "-"
            out.append("".join(row))
        return out
    for nm, side, half, cell, ph in (("FL_A", "L", 0, (46, 5), 0), ("FL_B", "L", 1, (46, 6), 255), ("FR_A", "R", 0, (47, 5), 254), ("FR_B", "R", 1, (47, 6), 253)):
        imgs = [T(*fall_rows(side, k)[half * 8:half * 8 + 8]) for k in range(4)]
        assert imgs[0] == tc(*cell), nm
        bd = td(*cell)
        G.append(Group("02_falls", nm, [cell], imgs, [bd] + [delta(imgs[0], f, bd, WATER_MAP) for f in imgs[1:]], [clock(28, [0, 1, 2, 3], ph)(t) for t in range(LOOP)]))
    LIP_L = [dict(r1="..------", r2=".-------", r3="--+--+-+", r5="++++++++"), dict(r1="..------", r2=".-------", r3="---+--+-", r5="+++-++++"),
             dict(r1="..------", r2=".-------", r3="-----+--", r5="++-+++-+"), dict(r1="..------", r2=".-----+-", r3="--+---+-", r5="+-++++++")]
    LIP_R = [dict(r1="------..", r2="-------.", r3="++-+--+-", r4="++++++++", r5="++++++++"), dict(r1="------..", r2="-------.", r3="-+-+----", r4="++++-+++", r5="++++++++"),
             dict(r1="------..", r2="-------.", r3="-+--+-+-", r4="+++++-++", r5="++++++-+"), dict(r1="------..", r2="-------.", r3="++-+--+-", r4="++++++++", r5="+++++++-")]
    GL_L = ["++--++++", "+--+++++", "+++--+++"]
    GL_R = ["++++-+++", "+++-++++", "+++++-++"]

    def foot(side, k, g):
        if side == "L":
            l = LIP_L[k]
            return T("...-----", l["r1"], l["r2"], l["r3"], GL_L[g], l["r5"], "++++++++", "++++++++")
        l = LIP_R[k]
        return T("-----...", l["r1"], l["r2"], l["r3"], l["r4"], l["r5"], GL_R[g], "++++++++")
    for side, cell, gph, gseq, lph in (("L", (46, 7), 0, [0, 0, 1, 0, 0, 2], 249), ("R", (47, 7), 21, [0, 0, 2, 0, 0, 1], 248)):
        lipk, gk = clock(28, [0, 1, 2, 3], lph), clock(6, gseq, gph)
        keys = [(lipk(t), gk(t)) for t in range(LOOP)]
        order = [(0, 0)]
        for kk in keys:
            if kk not in order:
                order.append(kk)
        imgs = [foot(side, *kk) for kk in order]
        assert imgs[0] == tc(*cell), side
        bd = td(*cell)
        G.append(Group("02_falls", "FOOT_" + side, [cell], imgs, [bd] + [delta(imgs[0], f, bd, WATER_MAP) for f in imgs[1:]], [order.index(kk) for kk in keys]))
    # the cascade: the flowing-water pixels of falls A inside the mountain (cells (47,3) (46,4) (47,4), igloo palette): foam 0 / water 1, the approved streak columns, 3 rows a step (falls_cascade.json)
    G.extend(cascade(WC, WD, tc, td))

    # ---- 03 fountain (the working state): two spill streams and two basin glints.  The town stands 8 cells west of the proposal's scene: x - 64 ------------------------------------------
    S = (-64, 0)
    s0 = {(290, 196): 1, (302, 196): 1}
    f1 = dict(s0)
    f1.update(E((290, 198, 0), (302, 198, 0)))
    f2 = dict(s0)
    f2.update(E((290, 194, 0), (302, 194, 0)))
    g0 = {(x, 201): 1 for x in (289, 290, 291, 301, 302, 303)}
    g1 = dict(g0)
    g1.update(E((201, 290, 292, 0), (201, 300, 302, 0)))
    for nm, frames, seqs, ph in (("stream", [f1, f2], [0, 1, 2], 0), ("basin", [g1], [0, 0, 1], 6)):
        cells = sorted({((x + S[0]) // 8, (y + S[1]) // 8) for f in frames for (x, y) in f})
        for (cx, cy) in cells:
            b = tc(cx, cy)
            imgs = [b] + [with_edits(b, cx, cy, f, S) for f in frames]
            G.append(Group("03_fountain", f"{nm}({cx},{cy})", [(cx, cy)], imgs, imgs, [clock(21, seqs, ph)(t) for t in range(LOOP)]))
    # the streams' glint pixel at frame 0 must be where the map has it (the offset is right): index 0 at (226, 196) and (238, 196)
    assert WC.px[196][226] == 0 and WC.px[196][238] == 0, "fountain offset"

    # ---- 04a bunting: P (3 cells), Q (3 cells), the end flag (1 cell) --------------------------------------------------------------------------------------------------------------
    P_R = T("........", "........", "########", "..+++++.", "....+++.", ".....+..", "........", "........")
    P_L = T("........", "........", "########", "..+++++.", "..+++...", "...+....", "........", "........")
    Q_R = T("........", "........", "########", "..#####.", "....#-#.", ".....#..", "........", "........")
    Q_L = T("........", "........", "########", "..#####.", "..#-#...", "...#....", "........", "........")
    END_R = T("........", "........", "########", "..+++++.", "....+++.", ".....+..", "..######", "..#-----")
    END_L = T("........", "........", "########", "..+++++.", "..+++...", "...+....", "..######", "..#-----")
    for nm, cells, frames, ph in (("P", [(25, 20), (27, 20), (29, 20)], [P_R, P_L], 0), ("Q", [(26, 20), (28, 20), (30, 20)], [Q_L, Q_R], 6), ("END", [(31, 20)], [END_R, END_L], 0)):
        b = tc(*cells[0])
        assert all(tc(*c) == b and td(*c) == b for c in cells), nm
        assert b not in frames
        G.append(Group("04a_bunting", nm, cells, [b] + frames, [b] + frames, [clock(16, [0, 1, 0, 2], ph)(t) for t in range(LOOP)]))

    # ---- 04b stadium flag: the two flag cells, three hand-drawn frames (approved stadium) ---------------------------------------------------------------------------------------------
    FLAG = {(7, 1): [T("33300033", "11133311", "00011103", "33322030", "00033300", "00000000", "33333333", "00000000"),
                     T("33333000", "11111333", "00000111", "33333223", "00000330", "00000000", "33333333", "00000000"),
                     T("33003330", "11331113", "00110001", "33223333", "00330000", "00000000", "33333333", "00000000")],
            (8, 1): [T("30000000", "13000000", "33000000", "00000000", "00000000", "00000000", "33330000", "00003333"),
                     T("33000000", "13000000", "30000000", "00000000", "00000000", "00000000", "33330000", "00003333"),
                     T("00000000", "33000000", "13000000", "30000000", "00000000", "00000000", "33330000", "00003333")]}
    for cell, fr in FLAG.items():
        assert tc(*cell) == fr[0] and td(*cell) == fr[0], cell
        G.append(Group("04b_stadium_flag", f"flag{cell}", [cell], fr, fr, [clock(27, [0, 1, 2], 0)(t) for t in range(LOOP)]))

    # ---- 05 airbase: the radar dish (4 views) and the mast lamp (blinks) as one set; the dish at (9, 36), the lamp beside it at (8, 36) -------------------------------------------------
    DISH_0 = T("........", "........", "....#...", "..#####.", ".#.----#", ".#-----#", "..#####.", "....#...")
    DISH_1 = T("........", "........", ".....#..", "...###..", "..#.--#.", "..#---#.", "...###..", "....#...")
    DISH_2 = T("........", "........", "....#...", "...###..", "...#-#..", "...#-#..", "...###..", "....#...")
    DISH_3 = T("........", "........", "...#....", "...###..", "..#+++#.", "..#+++#.", "...###..", "....#...")
    assert tc(9, 36) == DISH_0 and td(9, 36) == DISH_0
    G.append(Group("05_airbase", "DISH", [(9, 36)], [DISH_0, DISH_1, DISH_2, DISH_3], [DISH_0, DISH_1, DISH_2, DISH_3], [clock(16, [0, 1, 2, 3, 0, 1, 2, 3], 0)(t) for t in range(LOOP)]))
    lamp = tc(8, 36)
    assert td(8, 36) == lamp and lamp[1 * 8 + 5] == 0, "the lamp's lit pixel"
    dim = list(lamp)
    dim[1 * 8 + 5] = 1
    G.append(Group("05_airbase", "LAMP", [(8, 36)], [lamp, tuple(dim)], [lamp, tuple(dim)], [clock(16, [0, 0, 0, 0, 0, 0, 1, 1], 6)(t) for t in range(LOOP)]))

    # ---- 06a lodge smoke (white): the two cells above the chimney cap ----------------------------------------------------------------------------------------------------------------
    def rest_puff():
        return {(x, y): 0 for (y, x0, x1) in ((157, 470, 473), (158, 469, 474), (159, 470, 473)) for x in range(x0, x1 + 1)}

    def lfr(*runs):
        d = rest_puff()
        d.update(E(*[(y, x0, x1, 1) for (y, x0, x1) in runs]))
        return d
    la = [lfr((153, 471, 474), (154, 470, 475), (155, 471, 474), (159, 471, 472)), lfr((152, 474, 475), (153, 473, 476), (158, 471, 472), (159, 470, 473)),
          lfr((157, 471, 472), (158, 470, 473), (159, 470, 473))]
    edited(G, "06a_smoke_lodge", "lodge", WC, WD, la, [0, 1, 2, 3], 16, 0, (0, 0), None)

    # ---- 06c igloo chimney smoke -------------------------------------------------------------------------------------------------------------------------------------------------------
    IG_1 = T("........", "........", "...--...", "..-++-..", ".######.", ".#--++#.", ".######.", "..#-+#..")
    IG_2 = T("........", "...--...", "..----..", ".-+++++.", ".######.", ".#--++#.", ".######.", "..#-+#..")
    IG_3 = T("..-..-..", "...-....", "........", "........", ".######.", ".#--++#.", ".######.", "..#-+#..")
    ib = tc(56, 5)
    assert td(56, 5) == ib
    G.append(Group("06c_smoke_igloo", "IGLOO", [(56, 5)], [ib, IG_1, IG_2, IG_3], [ib, IG_1, IG_2, IG_3], [clock(16, [1, 2, 0, 3], 0)(t) for t in range(LOOP)]))

    # ---- 06b factory smoke: two stacks; the rest puffs of the DMG set stand elsewhere (rows >= 304: right stack (-1, -1), left stack (+3, 0)) ----------------------------------------------
    PR = {(x, y): 0 for (y, x0, x1) in ((305, 483, 486), (306, 481, 488), (307, 483, 486)) for x in range(x0, x1 + 1)}
    PL = {(x, y): 0 for (y, x0, x1) in ((304, 423, 426), (305, 421, 428), (306, 423, 426)) for x in range(x0, x1 + 1)}

    def ffr(base, *runs):
        d = dict(base)
        d.update(E(*[(y, x0, x1, 1) for (y, x0, x1) in runs]))
        return d
    fr_r = [ffr(PR, (301, 484, 486), (302, 483, 487), (303, 484, 486), (306, 484, 485)), ffr(PR, (297, 485, 486), (298, 484, 487), (299, 485, 486), (305, 483, 486), (306, 484, 485)),
            ffr(PR, (296, 486, 487), (305, 483, 486), (306, 482, 487), (307, 484, 485))]
    fr_l = [ffr(PL, (300, 418, 420), (301, 417, 421), (302, 418, 420), (305, 424, 425)), ffr(PL, (296, 417, 418), (297, 416, 419), (298, 417, 418), (304, 423, 426), (305, 424, 425)),
            ffr(PL, (304, 423, 426), (305, 422, 427), (306, 424, 425))]
    edited(G, "06b_smoke_factory", "factoryR", WC, WD, fr_r, [0, 1, 2, 3], 16, 0, (0, 0), lambda x, y: (x - 1, y - 1) if y >= 304 else (x, y), stagger=1)
    edited(G, "06b_smoke_factory", "factoryL", WC, WD, fr_l, [0, 1, 2, 3], 16, 6, (0, 0), lambda x, y: (x + 3, y) if y >= 304 else (x, y), stagger=1)

    # ---- 07 cow tails (the pasture cows; the tail at rest is in the map) ---------------------------------------------------------------------------------------------------------------
    def tail(x, y, shape):
        if shape == 0:
            return E((x, y, 3), (x, y + 1, 3), (x, y + 2, 3), (x, y + 3, 2))
        if shape == 1:
            return E((x, y, 3), (x, y + 1, 3), (x + 1, y + 2, 3), (x + 1, y + 3, 2))
        return E((x, y, 3), (x + 1, y + 1, 3), (x + 2, y + 2, 3), (x + 3, y + 3, 2))

    def cow(x, y):
        out = []
        for s in (1, 2):
            d = {(x + dx, y + dy): 0 for dx in range(4) for dy in range(4)}
            d.update(tail(x, y, s))
            out.append(d)
        return out
    for nm, (x, y), ph in (("cow1", (442, 396), 0), ("cow2", (476, 416), 18)):
        assert all(WC.px[py][px] == v for (px, py), v in tail(x, y, 0).items()), "the tail at rest is in the map"
        edited(G, "07_cow_tail", nm, WC, WD, cow(x, y), [0, 0, 0, 1, 2, 1], 18, ph, (0, 0), None)

    # ---- 09 logs: 6 logs low in the water bobbing 1 px, each with its own phase; both cells of a log together --------------------------------------------------------------------------------
    G.extend(logs(WC, WD, tc, td))

    # ---- NEW: runway lights (owner Q13): lights along the airbase runway that fade slowly on and off ------------------------------------------------------------------------------------
    G.extend(runway(WC, WD, tc, td))
    for g in G:                                                  # (the schedule: the cells of one picture a tick apart, each bundle shifted so that no view holds more than two events at a tick)
        d = INNER.get(g.name, 0) + SHIFT.get(bundle(g), 0)
        g.key = [g.key[(t - d) % LOOP] for t in range(LOOP)]
    return G


def bundle(g):
    """the groups that keep their relative timing (one picture): the schedule shifts them together"""
    n, it = g.name, g.item
    if it == "02_falls":
        return "falls"
    if it in ("03_fountain", "06b_smoke_factory", "07_cow_tail"):
        return n.split("(")[0]
    if it == "04a_bunting":
        return "bunt_Q" if n == "Q" else "bunt_PE"
    if it in ("04b_stadium_flag", "06a_smoke_lodge"):
        return it
    if it == "06c_smoke_igloo":
        return "IGLOO"
    if it == "09_logs":
        return n[:2]
    if it == "10_runway_lights":
        return "rwy"
    return n


# a tick later than the group's own clock: the second cell of a picture changes one tick after the first (the DMG writes two tiles a frame; one frame of a part-changed picture is not seen)
INNER = {"lodge(59,19)": 1, "HA_R": 1, "HB_R": 1, "HC_R": 1, "VA_B": 1, "VB_B": 1, "VC_B": 1, "stream(29,24)": 1, "basin(29,25)": 1, "flag(8, 1)": 1, "END": 1}
# the bundles' start shifts in ticks (tools/dev/smap_anim_phases.py chose them: the fewest ticks with more than two events in any view the camera can show)
SHIFT = {'06a_smoke_lodge': 3, 'VA': 1, 'WA': 2, 'WB': 1, 'falls': 6}


def edited(G, item, name, WC, WD, frames, seq, S, ph, shift_c, fn_d, stagger=0):
    """one group per cell touched by the frame edits (frame k >= 1 = the map's pixels with edits[k - 1] on top); the DMG frames take fn_d(x, y) -> (x, y) to move an edit (None: same)"""
    tc = lambda cx, cy: tile(WC, cx, cy)
    td = lambda cx, cy: tile(WD, cx, cy)
    cells = sorted({(x // 8, y // 8) for f in frames for (x, y) in f})
    fd = [({(fn_d(x, y) if fn_d else (x, y)): v for (x, y), v in f.items()}) for f in frames]
    for n, (cx, cy) in enumerate(cells):
        key = [clock(S, seq, ph - n * stagger)(t) for t in range(LOOP)]          # (stagger: the cells of one puff change a tick apart: the DMG writes two tiles a frame)
        bc, bd = tc(cx, cy), td(cx, cy)
        ic = [bc] + [with_edits(bc, cx, cy, f) for f in frames]
        idd = [bd] + [with_edits(bd, cx, cy, f) for f in fd]
        if not fn_d:
            assert bc == bd, (name, cx, cy)
        G.append(Group(item, f"{name}({cx},{cy})", [(cx, cy)], ic, idd, key))
    # DMG edits may land in cells the Color ones do not touch (a moved puff): they would be missed
    dcells = sorted({(x // 8, y // 8) for f in fd for (x, y) in f})
    assert set(dcells) <= set(cells), (name, dcells, cells)


CASC_PH = {(46, 4): 252, (47, 3): 251, (47, 4): 250}


def cascade(WC, WD, tc, td):
    """falls A's flowing water inside the mountain: foam 0 / water 1 on the approved streak columns, 3 rows a step, 4 frames, 4 ticks after the column's step"""
    import json
    from pathlib import Path
    data = json.loads((Path(__file__).resolve().parent / "falls_cascade.json").read_text())
    FALL_COLS = ["++-+++-+++-+", "-------++--+", "++---+++---+", "----++-----+", "--+++----++-", "+++---++---+", "-----+++---+", "+++-++-+++-+"]
    out = []
    for key, pts in sorted(data.items()):
        cx, cy = map(int, key.split(","))
        base = list(tc(cx, cy))
        imgs = []
        for k in range(4):
            im = list(base)
            for (x, y, c) in pts:
                f = (x - 372) % 8 if c == "w" else ord(c) - 97
                im[(y % 8) * 8 + x % 8] = 0 if FALL_COLS[f][(y - 40 - 3 * k) % 12] == "-" else 1
            imgs.append(tuple(im))
        assert imgs[0] == tuple(base) and imgs[0] == td(cx, cy), ("cascade frame 0", cx, cy)
        out.append(Group("02_falls", f"CASC({cx},{cy})", [(cx, cy)], imgs, imgs, [clock(28, [0, 1, 2, 3], CASC_PH[(cx, cy)])(t) for t in range(LOOP)]))
    return out


def logs(WC, WD, tc, td):
    """the six logs the map holds (3 across: left cell, 3 upright: top cell), each tile pair with its own phase (ticks); frame 1 = the log 1 px lower (rows moved, the waterline fixed)"""
    HL, HR = (42, 52), (43, 52)
    out = []
    ph_h = {"A": ((42, 52), 39), "B": ((43, 57), 36), "C": ((44, 68), 75)}
    ph_v = {"A": ((46, 20), 6), "B": ((46, 29), 24), "C": ((45, 43), 3)}
    key = lambda ph: [clock(12, [0, 0, 0, 1, 1, 1], ph)(t) for t in range(LOOP)]

    def hshift(t):
        """across log, one cell: rows 0-2 water (row 0), rows 3-5 = rows 2-4, the waterline (6) and 7 stay"""
        return tuple(v for r in (0, 0, 0, 2, 3, 4, 6, 7) for v in t[r * 8:r * 8 + 8])
    for g, ((x, y), ph) in ph_h.items():
        for dx, side in ((0, "L"), (1, "R")):
            c = (x + dx, y)
            bc, bd = tc(*c), td(*c)
            out.append(Group("09_logs", f"H{g}_{side}", [c], [bc, hshift(bc)], [bd, hshift(bd)], key(ph)))
    for g, ((x, y), ph) in ph_v.items():
        top, bot = (x, y), (x, y + 1)
        tcT, tcB, tdT, tdB = tc(*top), tc(*bot), td(*top), td(*bot)

        def vt(t_top):
            return tuple(t_top[0:8]) + tuple(t_top[0:56])                    # new top: row 0 water, rows 1.. = old rows 0..6

        def vb(t_top, t_bot):
            return tuple(t_top[56:64]) + tuple(t_bot[0:48]) + tuple(t_bot[56:64])      # new bottom: its row 0 = the top's last row, rows 1-6 = old rows 0-5, the waterline (7) stays
        out.append(Group("09_logs", f"V{g}_T", [top], [tcT, vt(tcT)], [tdT, vt(tdT)], key(ph)))
        out.append(Group("09_logs", f"V{g}_B", [bot], [tcB, vb(tcT, tcB)], [tdB, vb(tdT, tdB)], key(ph)))
    return out


# the runway lights (owner Q13: lights that FADE slowly on and off, never flash or cut).  A light is a 2 px wide dash on the runway's steel edge line (row 3 of the cell) with a glow on the
# navy row below it (row 4); the unlit runway is the map's own tile.  Only the base palette's four steps are used (index 3 ink, 2 navy, 1 steel, 0 sand-yellow, the colour of the runway's
# dashes), and every level changes a light pixel by ONE step: L1 the glow row 2 -> 1, L2 the edge line 1 -> 0 (lit), L3 the glow 1 -> 0 (full).  On Color those are the palette's steps, on the DMG
# the four shades: one shade at a time, the same picture on both, so the DMG fades (in four shades) too.  Each level lasts a step of the loop (21 ticks, 0.36 s); a light takes three steps up
# (1.1 s), holds two, three down and rests three; the three cell groups run a third of the loop apart so a glow travels along the runway.  Nothing ever changes by more than one step.
def runway(WC, WD, tc, td):
    base = tc(10, 42)
    R = [tc(x, 42) for x in range(9, 28)]
    assert all(r == R[0] for r in R) and all(td(x, 42) == R[0] for x in range(9, 28)), "the runway cells are not all alike"
    rows = [base[j * 8:(j + 1) * 8] for j in range(8)]
    assert rows[3] == (1,) * 8 and rows[4] == (2,) * 8 and rows[2] == (3,) * 8, rows

    def light(level):
        im = list(base)
        for x in (4, 5):
            im[4 * 8 + x] = {0: 2, 1: 1, 2: 1, 3: 0}[level]
            im[3 * 8 + x] = {0: 1, 1: 1, 2: 0, 3: 0}[level]
        return tuple(im)
    imgs = [base, light(1), light(2), light(3)]
    groups = (("A", [10, 16, 22], 0), ("B", [12, 18, 24], 85), ("C", [14, 20, 26], 170))
    seq = [0, 0, 0, 1, 2, 3, 3, 3, 2, 1, 0, 0]
    return [Group("10_runway_lights", f"RWY_{n}", [(x, 42) for x in xs], imgs, imgs, [clock(12, seq, ph)(t) for t in range(LOOP)]) for n, xs, ph in groups]
