# Modes P3 / P4 (the three-modes plan, CLASSIC): bars whose patrons come from the right. Every rule keeps working in
# bar-local x (0 = the patrons' end, TAP_X the tap); a bar marked R (level_dirs / bar_dirs bit b) is only DRAWN mirrored:
# its BG columns reversed with every tile flipped (CGB: attribute bit 5; DMG: flipped tile data), its sprites at OAM X
# 168 - X with S_FLIPX toggled, and Left / Right swap there. src/mirror.c, render.c, main.c (input), docs in PLAN.md.
#
# The LEVEL harness runs a level with given directions through the test hook `level_dirs` (the debug box's SELECT does
# the same). Mirror checks compare two runs of the same scene, one with every bar L: an R bar's picture must be the L
# one mirrored, pixel for pixel; the HUD and the stage are never mirrored.
import pytest
from gbtools import Rom
from PIL import Image, ImageChops, ImageOps

from conftest import (GAME, LAYOUT, ROM, bar_counter_row, bar_top_row, bar_top_y, check_golden, hold_stage_anim, logic_paused,
                      title_level, venue, venue_rows)
from test_patrons import (BASE, BACK_BASE, DRINKING, EMPTY, FULL, HELD, MAX_M, MAX_P, PUSHED, SHIFT0_OFS, WALKING,
                          clear_patrons, freeze, hold_mug, inject_mug, pose_first, put, score, set_patron)

pytestmark = pytest.mark.timeout(120)

S_FLIPX = 0x20
TAP_X, FAR_X, ENTRY_X = GAME["TAP_X"], GAME["PATRON_FAR_X"], GAME["ENTRY_X"]
MUG_START_X, MUG_RIGHT_END = GAME["SPOUT_X"], GAME["MUG_RIGHT_END"]
PLAYING, LIFE_LOST = 1, 2
OBJ_BASE = BASE + SHIFT0_OFS
ALL_R, SPLIT, ALT = 0xF, 0x3, 0x5          # RRRR (the whole screen), RRLL (top half R), RLRL (alternating)
BASE_W = 23                                # src/game.h: 20 + 3 * TAPER_MAX (P6)
FREE_IDS = [246, 247, 248, 249, 250, 251, 77, 252, 253, 254, 255, 234, 235, 236, 237, 238, 239]   # src/mirror.c


def rev(b):
    return int(f"{b:08b}"[::-1], 2)


def flipped(data):
    return bytes(rev(b) for b in data)


def tile_data(gb, t):
    a = (0x9000 + t * 16) if t < 128 else (0x8000 + t * 16)
    return bytes(gb.read(a, 16))


def is_r(dirs, b):
    return (dirs >> b) & 1


def start(gb, dirs, lv=1):
    """The LEVEL harness at level lv with the bars' directions `dirs` (bit b: bar b is R)."""
    gb.write("level_dirs", dirs)
    title_level(gb, lv)
    for _ in range(80):
        if gb.mem("game_state") == PLAYING:
            break
        gb.run(1)
    assert gb.mem("game_state") == PLAYING and gb.mem("bar_dirs") == dirs
    gb.write("tip_chance", 0)
    gb.run(2)                                    # (a key held at once after the menu's A would not be seen as a press)
    return gb


def new_rom(model):
    gb = Rom(ROM, model)
    gb.__enter__()
    gb.run(120)
    gb.model_name = model
    hold_stage_anim(gb)
    return gb


def pair(model, dirs, lv=1):
    """Two runs of level lv: every bar L, and `dirs`; their intro timers in step."""
    a, b = start(new_rom(model), 0, lv), start(new_rom(model), dirs, lv)
    for x, y in ((a, b), (b, a)):
        while x.mem("intro_timer") > y.mem("intro_timer"):
            x.run(1)
    return a, b


def close(*gbs):
    for gb in gbs:
        gb.__exit__(None, None, None)


# ---- a scene put on all four bars at once (deterministic: the same pokes and frames in both runs) -------------------
def walker(gb, spare, b, x, v):
    """A walker on bar b at x: in the slot of one of the level's start patrons on that bar while there is one (his
    patron_draw is kept, so the game redraws the columns he leaves: no stale figure stays in the tilemap)."""
    if not spare.get(b):
        return set_patron(gb, b, x, variant=v)
    p = spare[b].pop()
    for n, val in (("patron_state", WALKING), ("patron_x", x), ("patron_variant", v), ("patron_timer", 0), ("patron_aux", 0),
                   ("patron_frac", 0), ("patron_mug", 255), ("patron_drinks", 0), ("patron_hurry", 0), ("patron_dist", 0)):
        put(gb, n, p, val)
    return p


def scene(gb, even=False, lifted=True, watcher_bar=1, pushed=True):
    """Walkers at several shifts, drinkers holding mugs, a watcher in his back view, a lifted patron, a pushed one sliding
    back, full and empty mugs, the tip coin, the bartender on bar 1 left of the tap. even: every x even (a DMG mixed level
    draws patrons at even x only) and nobody moves."""
    o = 0 if even else 1
    with logic_paused(gb):
        st, br = gb.read("patron_state", MAX_P), gb.read("patron_bar", MAX_P)
        spare = {}                                  # (the start patrons stay live until their slots are used: set_patron
        for q in range(MAX_P):                      # takes the first free slot)
            if st[q]:
                spare.setdefault(br[q], []).append(q)
        for m in range(MAX_M):
            put(gb, "mug_state", m, 0)
        gb.write("mugs_live", 0)
        freeze(gb)
        walker(gb, spare, 0, 20 + o, 0)                            # walkers: shift 5 (4 when even), and 4
        walker(gb, spare, 0, 60, 2)
        w = walker(gb, spare, watcher_bar, 48, 1)                   # turns to watch the show (a multiple of 8)
        put(gb, "patron_dist", w, 1)
        lp = walker(gb, spare, 1, 96 + o * 2, 2)                    # lifted by the test hook
        walker(gb, spare, 2, 30, 1)
        walker(gb, spare, 3, 74 + o * 3, 0)
        assert not any(spare.values()), spare
        d = set_patron(gb, 0, 92, state=DRINKING, timer=40, variant=1)
        hold_mug(gb, d, 0)
        if pushed:
            p = set_patron(gb, 2, 70, state=PUSHED, aux=24, variant=0)
            hold_mug(gb, p, 2)
        d3 = set_patron(gb, 3, 26, state=DRINKING, timer=0, variant=2)
        hold_mug(gb, d3, 3)
        gb.write("patrons_live", sum(1 for v in gb.read("patron_state", MAX_P) if v))
        if not even:
            inject_mug(gb, 3, 100, FULL)                            # slides left (the walker at 77 catches it, is pushed)
        inject_mug(gb, 2, 100, EMPTY)                               # slides right
        inject_mug(gb, 0, 120, EMPTY)
        gb.write("bar", 1)
        gb.write("bartender_x", 64)
        gb.write("facing", 1)
        gb.write("tip_timer", 200)
        gb.write(gb.addr("tip_timer") + 1, 0)
        gb.write("tip_bar", 0)
        gb.write("tip_x", 42)
        gb.write("show_timer", 0)
    if lifted:
        gb.write("lift_hook_p", lp)
        gb.write("lift_hook_op", 1)
    return lp


BT_DY = LAYOUT["BT_DY"]


def bar_crop(gb, b, dy=0):
    y = bar_top_y(b)
    return gb.image().convert("RGB").crop((0, y + dy, 160, y + 24))


def sprite_overlaps(gb):
    """DMG: a mask (white) of the screen pixels two or more sprites cover. There the lower X wins (then the lower OAM
    index), which mirroring turns round: a known compromise, so those pixels are left out of the comparison (PLAN.md)."""
    cnt = {}
    for o in gb.oam():
        if not o["y"] or o["y"] >= 160 or not o["x"] or o["x"] >= 168:
            continue
        for y in range(max(0, o["y"] - 16), min(144, o["y"])):
            for x in range(max(0, o["x"] - 8), min(160, o["x"])):
                cnt[(x, y)] = cnt.get((x, y), 0) + 1
    m = Image.new("L", (160, 144), 0)
    for (x, y), n in cnt.items():
        if n > 1:
            m.putpixel((x, y), 255)
    return m


class Mirror:
    """Run b (dirs) shows run a (all L) with its R bars mirrored, pixel for pixel; HUD and stage the same. (DMG: not
    where sprites overlap, see sprite_overlaps.) Run b's frame may show a frame late (an R level costs some lines a
    frame more: a heavy frame can miss its VBlank there and not in run a), so a bar may match a's picture of this frame
    or of the one before."""
    def __init__(self, a, b, dirs):
        self.a, self.b, self.dirs, self.prev = a, b, dirs, None

    def check(self):
        a, b = self.a, self.b
        bad = []
        top = (0, 0, 160, bar_top_y(0))
        if ImageChops.difference(a.image().convert("RGB").crop(top), b.image().convert("RGB").crop(top)).getbbox():
            bad.append("hud/stage")
        ovl = sprite_overlaps(a) if a.model_name == "dmg" else None
        now = [(bar_crop(a, k, BT_DY), ovl) for k in range(4)]   # (without the bar's first BT_DY rows: the bartender above hangs his feet over them, mirrored by his bar, not this one)
        for k in range(4):
            got = bar_crop(b, k, BT_DY)
            if is_r(self.dirs, k):
                got = ImageOps.mirror(got)
            boxes = []
            for want, m in (now[k],) + ((self.prev[k],) if self.prev else ()):
                d = ImageChops.difference(want, got).convert("L")
                if m is not None:
                    y = bar_top_y(k)
                    d = ImageChops.subtract(d, m.crop((0, y + BT_DY, 160, y + 24)))
                boxes.append(d.getbbox())
            if all(boxes):
                bad.append((k, boxes[0]))
        self.prev = now
        return bad


def run_both(a, b, n):
    """n frames of both runs, kept on the same game frame: an R level costs some lines more a frame (mirror_oam, the
    mirrored compose), so a heavy frame can run late in one run and not in the other; the one behind catches up."""
    for _ in range(n):
        a.run(1, render=True)          # (rendered: image() would run one more frame)
        b.run(1, render=True)
        for _ in range(4):
            fa, fb = a.mem("frame_counter"), b.mem("frame_counter")
            if fa == fb:
                break
            (a if ((fb - fa) & 255) < 128 else b).run(1, render=True)


# ---- every bar L is the default, and nothing changes -----------------------------------------------------------------
def test_every_bar_is_l_unless_asked(gb):
    assert gb.mem("bar_dirs") == 0 and gb.mem("level_dirs") == 0 and gb.mem("draw_mask") == 0xFF
    assert list(gb.read("bar_sfp", 8)) == [0] * 8


def test_the_title_puts_every_bar_back_to_l(boot):
    start(boot, ALL_R)
    boot.write("game_state", 4)                       # GS_GAME_OVER: on to the initials / the table, then the title
    for _ in range(600):
        boot.press("start", 2)
        boot.run(3)
        if boot.mem("game_state") == 0:
            break
    assert boot.mem("game_state") == 0
    assert boot.mem("bar_dirs") == 0 and boot.mem("level_dirs") == 0


# ---- the picture: R bars are the L picture mirrored ------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_whole_screen_flip_is_the_l_picture_mirrored(model):
    """Every bar R: walkers at odd shifts, drinkers and their mugs, a watcher's back view, a lifted patron, a pushed one
    sliding, full and empty mugs, the coin, the bartender, the keg: every bar row is the all-L picture mirrored, on
    every one of 40 frames; HUD and stage unchanged."""
    a, b = pair(model, ALL_R)
    try:
        lp = scene(a)
        assert scene(b) == lp
        run_both(a, b, 6)
        assert a.mem("lift_hook_res") == 1 and b.mem("lift_hook_res") == 1
        mi = Mirror(a, b, ALL_R)
        mi.check()                                  # (the pictures of the frame before: either may match)
        for f in range(40):
            run_both(a, b, 1)
            bad = mi.check()
            assert not bad, (f, bad)
        assert b.mem("mir_short") == 0
    finally:
        close(a, b)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("dirs", [SPLIT, 0xC, ALT, 0xA, 0x9, 0x6])
def test_mixed_levels_mirror_only_their_r_bars(model, dirs):
    """Mixed levels: the R bars mirrored, the L bars as they are. (DMG: patrons at even x, the scene keeps them there;
    a back view is not mirrored on the DMG, so the watcher stands on an L bar.)"""
    wb = next(k for k in range(4) if not is_r(dirs, k))
    a, b = pair(model, dirs)
    try:
        scene(a, even=True, watcher_bar=wb, pushed=False)
        scene(b, even=True, watcher_bar=wb, pushed=False)
        run_both(a, b, 6)
        assert b.mem("draw_mask") == (0xFE if model == "dmg" else 0xFF)
        mi = Mirror(a, b, dirs)
        mi.check()                                  # (the pictures of the frame before: either may match)
        for f in range(30):
            run_both(a, b, 1)
            bad = mi.check()
            assert not bad, (f, bad)
        assert b.mem("mir_short") == 0
    finally:
        close(a, b)


# ---- BG geometry: a patron at local x on an R bar --------------------------------------------------------------------
def r_tiles(gb, dirs, v, s):
    """First tile of variant v at shift s on an R bar (st_tab's R half)."""
    return gb.read("st_tab", 64)[32 | (v << 3) | s]


@pytest.mark.parametrize("dirs", [ALL_R, ALT])
def test_a_patron_at_local_x_is_drawn_at_screen_columns_19_minus_c(boot, dirs):
    gb = start(boot, dirs)
    xs = (17, 34, 51, 66) if dirs == ALL_R else (16, 34, 50, 66)
    with logic_paused(gb):
        clear_patrons(gb)
        freeze(gb)
        for b, x in enumerate(xs):
            set_patron(gb, b, x, variant=b % 3)
    gb.run(8)
    tm = gb.bg_tilemap()
    mixed_dmg = gb.model_name == "dmg" and dirs not in (0, ALL_R)
    for b, x in enumerate(xs):
        v, c, s = b % 3, x >> 3, x & 7
        rows = [[t & 0xFF for t in tm[bar_top_row(b) + r][:20]] for r in range(2)]
        if is_r(dirs, b):
            t = r_tiles(gb, dirs, v, s)
            if mixed_dmg:
                assert t == pose_first(v, (s & 6) + 1), "DMG mixed: R shift s (even) in the slot of shift s + 1"
            else:
                assert t == pose_first(v, s)
            for k in range(3):
                assert rows[0][19 - c - k] == t + 2 * k and rows[1][19 - c - k] == t + 2 * k + 1, (b, k, rows)
            if gb.model_name == "cgb":
                for r in range(2):
                    for k in range(3):
                        attr = gb.pb.memory[1, 0x9800 + (bar_top_row(b) + r) * 32 + 19 - c - k]
                        assert attr & S_FLIPX, (b, r, k, attr)
        else:
            t = pose_first(v, s & 6 if mixed_dmg else s)
            assert rows[0][c:c + 3] == [t, t + 2, t + 4] and rows[1][c:c + 3] == [t + 1, t + 3, t + 5], (b, rows)


def test_dmg_whole_screen_flip_flips_the_patron_tiles_in_place(boot):
    if boot.model_name != "dmg":
        pytest.skip("DMG only (CGB flips by attribute)")
    from test_flow import patron_group_tiles
    gb = start(boot, ALL_R, 2)                        # the sports group
    data = patron_group_tiles(1)
    n = len(data) // 16
    vram = b"".join(tile_data(gb, BASE + t) for t in range(n))
    assert vram == flipped(data)
    assert list(gb.read("bar_sfp", 8)) == [S_FLIPX] * 4 + [0] * 4, "lifted patrons: the tiles are flipped already"


def test_dmg_mixed_level_holds_both_directions_at_even_shifts(boot):
    if boot.model_name != "dmg":
        pytest.skip("DMG only")
    from test_flow import patron_group_tiles
    gb = start(boot, SPLIT, 2)
    data = patron_group_tiles(1)
    rom_tile = lambda t: data[(t - BASE) * 16:(t - BASE + 1) * 16]
    for v in range(3):
        for s in (0, 2, 4, 6):
            l, r = pose_first(v, s), pose_first(v, s + 1)
            for k in range(6):
                assert tile_data(gb, l + k) == rom_tile(l + k), (v, s, k, "L kept")
                assert tile_data(gb, r + k) == flipped(rom_tile(l + k)), (v, s, k, "R = L flipped")
    for t in range(BACK_BASE, BACK_BASE + 12):
        assert tile_data(gb, t) == rom_tile(t), "back views shared, not flipped"
    assert gb.mem("draw_mask") == 0xFE and gb.mem("mir_bswap") == 1
    assert list(gb.read("bar_sfp", 8)) == [S_FLIPX, S_FLIPX, 0, 0] * 2, "lifted: the L pose with the OAM flip"


def test_dmg_mixed_back_view_on_an_r_bar_is_drawn_unmirrored(boot):
    if boot.model_name != "dmg":
        pytest.skip("DMG only")
    gb = start(boot, SPLIT)
    with logic_paused(gb):
        clear_patrons(gb)
        freeze(gb)
        w = set_patron(gb, 0, 48, variant=1)
        put(gb, "patron_dist", w, 1)
    gb.run(8)
    assert gb.read("patron_draw", MAX_P)[w] == 0x80 | 48
    tm = gb.bg_tilemap()
    t = BACK_BASE + 4
    rows = [[x & 0xFF for x in tm[bar_top_row(0) + r][:20]] for r in range(2)]
    c = 48 >> 3
    assert rows[0][18 - c:20 - c] == [t, t + 1] and rows[1][18 - c:20 - c] == [t + 2, t + 3], rows


@pytest.mark.parametrize("theme", range(10))
def test_dmg_every_venue_gets_flipped_keg_and_counter_tiles(boot, theme):
    """DMG, an R bar: every bar-row tile that is not its own mirror image gets a flipped copy in a free id (none is left
    unflipped); the wall rows and the counter row are the venue's, reversed, with those ids."""
    if boot.model_name != "dmg":
        pytest.skip("DMG only")
    gb = start(boot, ALL_R, theme + 1)
    assert gb.mem("cur_group") == theme and gb.mem("mir_short") == 0
    m = venue_rows(theme, "bar_map")
    twins = dict(zip(venue(theme)["bar_alt"], venue(theme)["bar_alt_tiles"]))
    tm = gb.bg_tilemap()
    for r in range(3):
        row = [t & 0xFF for t in tm[bar_top_row(3) + r][:20]] if r == 2 else None
        for c in range(20):
            src = m[r][c]
            if r < 2:
                got = gb.read("base_all", 4 * 2 * BASE_W)[2 * 2 * BASE_W + r * BASE_W + 3 + 19 - c]   # base_rtile (screen order;
                #                                    P6: BASE_W wide, a straight bar's window from column 3 of an R row)
            else:
                got = row[19 - c]
            if src in twins:                            # the tap's lettering: the pre-mirrored twin, flipped (gen_art.py LETTER_BOX)
                assert got in FREE_IDS and tile_data(gb, got) == flipped(bytes(twins[src])), (r, c, src, got)
            elif tile_data(gb, src) == flipped(tile_data(gb, src)):
                assert got == src
            else:
                assert got in FREE_IDS and tile_data(gb, got) == flipped(tile_data(gb, src)), (r, c, src, got)


def test_cgb_r_bar_rows_carry_the_flip_attribute(boot):
    if boot.model_name != "cgb":
        pytest.skip("CGB only")
    gb = start(boot, SPLIT)
    m, at = venue_rows(0, "bar_map"), venue_rows(0, "bar_attr")
    tm = gb.bg_tilemap()
    for b in range(4):
        for r in range(3):
            y = bar_top_row(b) + r
            for c in range(6 if r < 2 else 0, 20):           # (the start patrons stand at local columns 2-4)
                sc = 19 - c if is_r(SPLIT, b) else c
                assert tm[y][sc] & 0xFF == m[r][c]
                attr = gb.pb.memory[1, 0x9800 + y * 32 + sc]
                assert attr == at[r][c] ^ (S_FLIPX if is_r(SPLIT, b) else 0), (b, r, c, attr)


# ---- sprites ---------------------------------------------------------------------------------------------------------
def entries(gb):
    return [dict(k=k, **o) for k, o in enumerate(gb.oam()) if o["y"]]


@pytest.mark.parametrize("dirs", [ALL_R, ALT])
def test_mugs_and_the_bartender_are_mirrored_and_flipped(boot, dirs):
    gb = start(boot, dirs)
    with logic_paused(gb):
        clear_patrons(gb)
        freeze(gb)
        for m in range(MAX_M):
            put(gb, "mug_state", m, 0)
        gb.write("mugs_live", 0)
        full = inject_mug(gb, 0, 90, FULL)
        empty = inject_mug(gb, 1, 40, EMPTY)
        gb.write("bar", 0)
        gb.write("bartender_x", 64)
        gb.write("facing", 0)
    gb.run(1)
    gb.run(1)
    mx = gb.read("mug_x", MAX_M)
    oam = gb.oam()
    for i, b in ((full, 0), (empty, 1)):
        want = 160 - mx[i] if is_r(dirs, b) else mx[i] + 8
        hit = [o for o in oam if o["y"] == bar_top_y(b) + 16 + LAYOUT["MUG_DY"] and abs(o["x"] - want) <= 2]   # (OAM shows the last frame)
        assert len(hit) == 1, (i, want, oam[5:12])
        assert bool(hit[0]["flags"] & S_FLIPX) == bool(is_r(dirs, b))
    # the bartender (bar 0 is R in both layouts), 16 px wide at local x: screen 144 - x, art facing flipped
    bt = oam[0:4]
    xs = sorted({o["x"] for o in bt})
    assert xs == [144 - 64 + 8, 144 - 64 + 16], bt
    assert all(o["flags"] & S_FLIPX for o in bt), "facing left (local) is drawn facing right"


def test_a_lifted_patron_on_an_r_bar_is_two_mirrored_entries(boot):
    gb = start(boot, ALT)
    with logic_paused(gb):
        clear_patrons(gb)
        freeze(gb)
        p = set_patron(gb, 0, 50, variant=1)
        q = set_patron(gb, 1, 50, variant=1)
    gb.run(2)
    for s in (p, q):
        gb.write("lift_hook_p", s)
        gb.write("lift_hook_op", 1)
        gb.run(3)
        assert gb.mem("lift_hook_res") == 1
    gb.run(2)
    oam = entries(gb)
    for s, b in ((p, 0), (q, 1)):
        d = gb.read("patron_draw", MAX_P)[s]
        mine = sorted((o["x"], o["tile"], o["flags"]) for o in oam if o["y"] == bar_top_y(b) + 16 and o["tile"] >= OBJ_BASE)
        t = OBJ_BASE + 6
        if is_r(ALT, b):
            assert [(x, tt) for x, tt, _ in mine] == [(152 - d, t + 2), (160 - d, t)], mine     # right column on the left
            flip = gb.model_name == "cgb" or True                                               # (ALT is mixed: OAM flip on both)
            assert all(bool(f & S_FLIPX) == flip for _, _, f in mine), mine
        else:
            assert [(x, tt) for x, tt, _ in mine] == [(d + 8, t), (d + 16, t + 2)], mine
            assert not any(f & S_FLIPX for _, _, f in mine), mine


# ---- input ------------------------------------------------------------------------------------------------------------
def test_left_on_an_r_bar_walks_to_the_tap(boot):
    gb = start(boot, ALT)
    gb.write("intro_timer", 255)
    gb.write("bar", 0)
    gb.write("bartender_x", 60)
    gb.hold("left")
    gb.run(20)
    gb.release("left")
    x = gb.mem("bartender_x")
    assert x > 60 and gb.mem("facing") == 1, "R bar: Left walks toward the tap (local right)"
    gb.hold("left")
    gb.run(80)
    gb.release("left")
    assert gb.mem("bartender_x") == TAP_X
    gb.press("down", 2)                              # bar 1 is L: the keys as they always were
    gb.run(2)
    assert gb.mem("bar") == 1 and gb.mem("bartender_x") == TAP_X
    gb.hold("left")
    gb.run(10)
    gb.release("left")
    assert gb.mem("bartender_x") < TAP_X and gb.mem("facing") == 0
    gb.press("up", 2)
    gb.run(2)
    gb.hold("right")
    gb.run(10)
    gb.release("right")
    assert gb.mem("bar") == 0 and gb.mem("bartender_x") < TAP_X, "R bar: Right walks away from the tap"


def test_a_fills_and_launches_at_the_left_keg(boot):
    gb = start(boot, ALL_R)
    gb.write("intro_timer", 255)
    gb.hold("a")
    gb.run(30)
    oam = gb.oam()
    assert oam[4]["y"] and oam[4]["x"] == 168 - (MUG_START_X + 8) and oam[4]["flags"] & S_FLIPX, "the fill glass under the left spout"
    gb.release("a")
    gb.run(3)
    full = [i for i, s in enumerate(gb.read("mug_state", MAX_M)) if s == FULL]
    assert len(full) == 1
    x = gb.read("mug_x", MAX_M)[full[0]]
    assert x < MUG_START_X and any(o["y"] and abs(o["x"] - (160 - x)) <= 2 for o in gb.oam()[5:26]), "it slides right on screen"


# ---- the rules on an R bar (all local; the picture mirrored) ------------------------------------------------------------
def test_a_walker_reaching_the_tap_costs_a_life_on_an_r_bar(boot):
    gb = start(boot, ALL_R)
    with logic_paused(gb):
        clear_patrons(gb)
        set_patron(gb, 2, FAR_X - 2)
        gb.write("intro_timer", 0)
        gb.write("spawn_timer", 255)
    lives = gb.mem("lives")
    for _ in range(200):
        gb.run(1)
        if gb.mem("lives") < lives:
            break
    assert gb.mem("lives") == lives - 1 and gb.mem("game_state") == LIFE_LOST


def glass_entries(gb):
    lo = GAME.get("OAM_FILL", 4) + 1
    return [o for o in gb.oam()[lo:26] if o["y"] and 0 < o["tile"] < 128]


def test_a_full_mug_off_the_far_end_breaks_at_the_right_edge(boot):
    gb = start(boot, ALL_R)
    with logic_paused(gb):
        clear_patrons(gb)
        freeze(gb)
        m = inject_mug(gb, 1, 24, FULL)
    lives = gb.mem("lives")
    for _ in range(20):
        gb.run(1)
        if gb.read("mug_state", MAX_M)[m] == 3:
            break
    assert gb.read("mug_state", MAX_M)[m] == 3 and gb.mem("lives") == lives - 1
    gb.run(2)
    xs = [o["x"] for o in gb.oam()[5:26] if o["y"]]
    assert xs and min(xs) >= 168 - 24 - 8, ("the glass breaks at the screen's right edge (the far end)", xs)


def test_an_empty_off_the_tap_end_breaks_at_the_left_keg(boot):
    gb = start(boot, ALL_R)
    with logic_paused(gb):
        clear_patrons(gb)
        freeze(gb)
        gb.write("bar", 0)
        gb.write("bartender_x", 40)               # away from the tap: he does not catch it
        m = inject_mug(gb, 2, MUG_RIGHT_END - 4, EMPTY)
    lives = gb.mem("lives")
    for _ in range(30):
        gb.run(1)
        if gb.read("mug_state", MAX_M)[m] == 3:
            break
    gb.run(1)                                     # (PyBoy's frame can end between the mug's state and the life)
    assert gb.read("mug_state", MAX_M)[m] == 3 and gb.mem("lives") == lives - 1
    gb.run(1)
    xs = [o["x"] for o in gb.oam()[5:26] if o["y"]]
    assert xs and max(xs) <= 40, ("the glass breaks at the left (keg) end", xs)


def test_an_empty_is_caught_at_the_left_keg(boot):
    gb = start(boot, ALL_R)
    with logic_paused(gb):
        clear_patrons(gb)
        freeze(gb)
        gb.write("bar", 3)
        gb.write("bartender_x", TAP_X)
        m = inject_mug(gb, 3, 100, EMPTY)
    s0 = score(gb)
    seen = []
    for _ in range(80):
        gb.run(1)
        o = [e for e in gb.oam()[5:26] if e["y"]]
        seen += [e["x"] for e in o]
        if gb.read("mug_state", MAX_M)[m] == 0:
            break
    gb.run(1)                                     # (PyBoy's frame can end between the catch and its score)
    assert gb.read("mug_state", MAX_M)[m] == 0 and score(gb) - s0 == 100 and gb.mem("lives") == 3
    assert seen and min(seen) < 60 and max(seen) <= 160 - 100, "it slid left on screen, to the keg"


def test_a_served_patron_leaves_past_the_right_edge(boot):
    gb = start(boot, ALL_R)
    with logic_paused(gb):
        clear_patrons(gb)
        freeze(gb)
        p = set_patron(gb, 1, ENTRY_X + 6, state=PUSHED, aux=24)
        hold_mug(gb, p, 1)
    s0 = score(gb)
    xs = []
    for _ in range(60):
        gb.run(1)
        xs += [o["x"] for o in gb.oam()[18:26] if o["y"] == bar_top_y(1) + 16]
        if gb.read("patron_state", MAX_P)[p] == 0:
            break
    assert score(gb) - s0 == GAME.get("SERVE", 50) or score(gb) > s0
    assert xs and min(xs) >= 168 - 32 and max(xs) >= 160, ("he slides out past the right edge", sorted(set(xs)))


# ---- goldens: the three CLASSIC layouts (level numbers of the classic table, played through the LEVEL harness) -----------
def golden_scene(boot, dirs, lv):
    gb = start(boot, dirs, lv)
    scene(gb, even=True, watcher_bar=next(k for k in range(4) if not is_r(dirs, k)) if dirs != ALL_R else 1)
    gb.run(30)
    return gb


def test_golden_classic_flip(boot):
    """Classic level 3 (sports, RRRR: the whole screen flips) = the harness's sports level with every bar R."""
    check_golden(golden_scene(boot, ALL_R, 2), "classic_flip")


def test_golden_classic_split(boot):
    """Classic level 6 (the punk bar, RRLL: the top half R) = the harness's Chrome Cow level."""
    check_golden(golden_scene(boot, SPLIT, 7), "classic_split")


def test_golden_classic_alt(boot):
    """Classic level 12 (the space bar, RLRL: fully alternating) = the harness's space lounge level."""
    check_golden(golden_scene(boot, ALT, 10), "classic_alt")


# ---- the debug select: the LEVEL box's SELECT steps the bars' directions -------------------------------------------------
def test_the_level_box_select_steps_the_directions_and_a_starts_with_them(boot):
    from test_debug import combo, release_combo, win_row
    from test_flow import tile_id
    combo(boot)
    release_combo(boot)
    assert boot.mem("debug_menu_open") == 1 and boot.mem("level_dirs") == 0
    seen = []
    for _ in range(8):
        boot.press("select", 2)
        boot.run(4)
        seen.append(boot.mem("level_dirs"))
    assert seen == [0xF, 0x3, 0xC, 0x9, 0x6, 0x5, 0xA, 0x0], "LLLL, RRRR, RRLL, LLRR, RLLR, LRRL, RLRL, LRLR, top bar first"
    for _ in range(2):
        boot.press("select", 2)
        boot.run(4)
    assert boot.mem("level_dirs") == 0x3
    row = win_row(boot, 6)
    r, l = tile_id("GLYPH_R"), tile_id("GLYPH_L")
    assert row[12:16] == [r, r, l, l], ("the BARS line reads RRLL", row)
    boot.press("a", 2)
    for _ in range(80):
        boot.run(1)
        if boot.mem("game_state") == PLAYING:
            break
    assert boot.mem("game_state") == PLAYING and boot.mem("bar_dirs") == 0x3 and boot.mem("play_mode") == 3


# ---- lettering on the taps reads the right way round on an R bar (owner 2026-10-12: POP, MOO) ------------------------
# The R bar is the L picture mirrored, except the lettering: its pixels there are the L ones translated to the mirrored place,
# not mirrored (tools/gen_art.py LETTER_BOX, twin tiles loaded by mirror_load into free BG ids).
LETTER_BOX = {1: (147, 18, 157, 22), 6: (145, 14, 158, 18)}       # theme: pixel box in the L bar (sports POP, biker MOO)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("theme", sorted(LETTER_BOX))
@pytest.mark.parametrize("dirs", [ALL_R, SPLIT, ALT])
def test_lettering_on_an_r_bar_matches_the_l_text(model, theme, dirs):
    x0, y0, x1, y1 = LETTER_BOX[theme]
    a, b = pair(model, dirs, theme + 1)
    try:
        run_both(a, b, 4)
        assert b.mem("mir_short") == 0
        n = 0
        for k in range(1, 4):                       # (bar 0 holds the bartender at the left tap)
            if not is_r(dirs, k):
                continue
            n += 1
            la = bar_crop(a, k).crop((x0, y0, x1 + 1, y1 + 1))
            rb = bar_crop(b, k).crop((159 - x1, y0, 160 - x0, y1 + 1))       # the box mirrored in the screen
            assert ImageChops.difference(la.convert("RGB"), rb.convert("RGB")).getbbox() is None, (k, "the text reads backwards")
            plain = ImageOps.mirror(la)
            assert ImageChops.difference(plain.convert("RGB"), rb.convert("RGB")).getbbox() is not None, "(a text that is its own mirror image proves nothing)"
        assert n
    finally:
        close(a, b)
