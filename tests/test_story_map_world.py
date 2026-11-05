# The scrolling story map's world (src/smap.c the screen, src/smap_eng.c the streaming engine, tools/gen_smap_world.py the world: the 64 x 48 cell map, the
# legs Sal walks, the unlock states' clouds). What is checked here:
#   - the built data: every 21 x 19 window of every state fits the DMG's 176 tile slots and the Color's 8 BG palettes, on the way Sal can walk too; every stop
#     is reachable from the town along the legs;
#   - the picture: the first view at every stop is the world's render (the tile ids on the screen are the world's tiles, in the world's palettes), at three
#     unlock states;
#   - the walk: every leg both ways on both models, frame by frame, the screen is the world's render at the scroll the frame shows (apart from the sprites): the
#     camera never shows a tile that is not loaded;
#   - the C twin (ASM_SMAP): the same walks on build/game-c.gb;
#   - the cost: the walk's worst frames on a DMG, and on a Color at double speed (owner Q92).
import contextlib
import json
import sys

import numpy as np
import pytest
import test_sound
import test_story_map as sm
from conftest import ROOT, double_speed
from test_flow import run_until

pytestmark = pytest.mark.timeout(600)

WORLD = json.loads((ROOT / "build" / "smap_world.json").read_text())
STOPS, EXITS, LEGS = WORLD["stops"], WORLD["exits"], WORLD["legs"]
DIRS = ("up", "down", "left", "right")
TOWN = 10
C_ROM = ROOT / "build" / "game-c.gb"
DMG_GREY = {0: (255, 255, 255), 1: (153, 153, 153), 2: (85, 85, 85), 3: (0, 0, 0)}
SV = 396                                                  # story_scratch + the map's variables (src/smap_priv.h S_V)
V_WY, V_WH, V_CAMX, V_CAMY, V_FX, V_FY, V_WALK = 8, 9, 12, 14, 16, 18, 20


# ---- the built data -----------------------------------------------------------------------------------------------------------------------------------------
def test_every_stop_is_reachable_from_the_town_along_the_legs():
    seen, todo = {TOWN}, [TOWN]
    while todo:
        s = todo.pop()
        for t in EXITS[s]:
            if t != 255 and t not in seen:
                seen.add(t)
                todo.append(t)
    assert seen == set(range(11))
    for a, b, pts in LEGS:
        assert [pts[0], pts[-1]] == [STOPS[a], STOPS[b]], (a, b)
        assert all(p[0] == q[0] or p[1] == q[1] for p, q in zip(pts, pts[1:])), f"leg {a}-{b} has a slanted piece"
        assert b in EXITS[a] and a in EXITS[b], (a, b)
    assert sum(1 for s in range(11) for t in EXITS[s] if t != 255) == 2 * len(LEGS)


def test_no_window_of_the_built_data_is_over_the_budgets():
    sys.path.insert(0, str(ROOT / "tools"))
    import gen_smap_world as g
    dm, cg = g.Model(False), g.Model(True)
    stops, legs, _, _ = g.geometry()
    assert dm.window_max(21, 19)[0] <= 176, "a view's tiles fit the DMG's 176 slots"
    assert cg.palette_max(21, 19)[0] <= 8, "a view's palettes fit the Color's 8 BG palette slots"
    assert WORLD["vars_max"] <= 15 and WORLD["uses_max_22x20"] <= 255 and WORLD["slots_c"] <= 352
    worst_t = worst_p = 0
    for p in range(1, 11):
        for (c0, c1, r0, r1) in g.path_windows(stops, legs):          # (the camera's view on every pixel of the way, a line more on every side)
            worst_t = max(worst_t, len(np.unique(dm.grids[p][r0:r1 + 1, c0:c1 + 1])))
            worst_p = max(worst_p, len(np.unique(cg.pals[p][r0:r1 + 1, c0:c1 + 1])))
    assert worst_t <= 176, worst_t
    assert worst_p <= 9, worst_p                                       # (the 9th palette waits for a line to drop: the camera holds a frame)


# ---- the world as the screen shows it -------------------------------------------------------------------------------------------------------------------------
def tile_idx(b):
    a = np.frombuffer(b, dtype=np.uint8).reshape(8, 2)
    return np.unpackbits(a[:, 0:1], axis=1) | (np.unpackbits(a[:, 1:2], axis=1) << 1)


def world_image(model, state):
    """The whole 512 x 384 world as it looks in unlock state `state` (1..10), from the built tables."""
    cgb = model == "cgb"
    disp = WORLD["disp_c" if cgb else "disp_d"][state - 1]
    tiles = bytes.fromhex(WORLD["tiles_c" if cgb else "tiles_d"])
    cache, im = {}, np.zeros((384, 512, 3), dtype=np.uint8)
    for c, w in enumerate(disp):
        key = (w & 0x3FF, w >> 10)
        if key not in cache:
            ix = tile_idx(tiles[key[0] * 16:key[0] * 16 + 16])
            cols = [((v & 31) << 3, ((v >> 5) & 31) << 3, ((v >> 10) & 31) << 3) for v in WORLD["pal"][key[1]]] if cgb else [DMG_GREY[i] for i in range(4)]
            cache[key] = np.array(cols, dtype=np.uint8)[ix]
        y, x = divmod(c, 64)
        im[y * 8:y * 8 + 8, x * 8:x * 8 + 8] = cache[key]
    return im


def sprite_mask(oam, m):
    for o in oam:
        if o["y"]:
            y0, x0 = o["y"] - 16, o["x"] - 8
            m[max(0, y0):max(0, y0 + 16), max(0, x0):max(0, x0 + 8)] = True


class Watch:
    """Frame by frame: the screen against the world's render at the scroll the frame shows. The scroll registers are written in VBlank, the frame is read after
    it: the candidates are this frame's and the last one's value (within 12 pixels of the camera the engine says); the sprites of this frame and the last do not
    count, nor does the name tag's window (this frame's and the last one's rows). The first frame has no last one: any scroll within the 12 pixels."""

    def __init__(self, gb, model, progress):
        self.gb, self.img = gb, world_image(model, min(progress + 1, 10))
        self.prev, self.poam, self.frames, self.bad = gb.regs(), [], 0, []
        sc = gb.read("story_scratch", 520)
        self.pwin = (sc[SV + V_WY], sc[SV + V_WH])
        self.skip_first = False

    def frame(self):
        gb = self.gb
        gb.run(1, True)                                           # (rendered: image() would else run one more frame)
        scr = np.array(gb.image())
        r, pr = gb.regs(), self.prev
        self.prev = r
        sc = gb.read("story_scratch", 520)
        vx, vy = sc[SV + V_CAMX] | sc[SV + V_CAMX + 1] << 8, sc[SV + V_CAMY] | sc[SV + V_CAMY + 1] << 8
        co = gb.oam()
        m = np.zeros((144, 160), dtype=bool)
        sprite_mask(co, m)
        sprite_mask(self.poam, m)
        self.poam = co
        wins = [w for w in (self.pwin, (sc[SV + V_WY], sc[SV + V_WH])) if w[1]]
        if wins:
            m[min(w[0] for w in wins):max(w[0] + w[1] for w in wins), :] = True
        self.pwin = (sc[SV + V_WY], sc[SV + V_WH])
        first = self.frames == 0
        xs = [x for x in range(max(vx - 12, 0), vx + 13) if first or x & 255 in (r["SCX"], pr["SCX"])]
        ys = [y for y in range(max(vy - 12, 0), vy + 13) if first or y & 255 in (r["SCY"], pr["SCY"])]
        self.frames += 1
        best = None
        for x in xs:
            for y in ys:
                if x + 160 > 512 or y + 144 > 384:
                    continue
                n = int((np.any(self.img[y:y + 144, x:x + 160] != scr, axis=2) & ~m).sum())
                if best is None or n < best[0]:
                    best = (n, x, y)
        if (best is None or best[0]) and not (first and self.skip_first):      # (the press ran frames the sprites of which are not known)
            self.bad.append((self.frames, best, (vx, vy), (r["SCX"], r["SCY"])))
        return sc


def var(sc, n):
    return sc[SV + n] | sc[SV + n + 1] << 8


# ---- the first view ---------------------------------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("progress, stops", [(10, range(11)), (3, (0, 3, TOWN)), (0, (0, TOWN))])
def test_the_first_view_at_a_stop_is_the_worlds_picture(model, progress, stops):
    for s in stops:
        gb = sm.to_map(model, progress, stop=s)
        w = Watch(gb, model, progress)
        w.frame()
        w.frame()
        assert not w.bad, (model, progress, s, w.bad)
        assert gb.mem("smap_stop") == s


# ---- the walk ---------------------------------------------------------------------------------------------------------------------------------------------------
LEG_WALKS = [(s, d) for s in range(11) for d in range(4) if EXITS[s][d] != 255]


def walk(model, s, d, progress=10, double=False):
    """From stop s, press direction d and watch every frame until Sal stands still at the next stop. -> (Watch, frames, holds, lines of the logic per frame)"""
    with double_speed() if double else contextlib.nullcontext():
        gb = sm.to_map(model, progress, stop=s)
    w = Watch(gb, model, progress)
    w.skip_first = True
    gb.press(DIRS[d], 4)
    lines, holds, last = [], 0, None
    for f in range(1500):
        sc = w.frame()
        lines.append(gb.mem16("perf_logic_last"))
        fx = (var(sc, V_FX), var(sc, V_FY))
        holds += bool(sc[SV + V_WALK]) and fx == last
        last = fx
        if f > 4 and not sc[SV + V_WALK]:
            break
    return gb, w, lines, holds


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("s, d", LEG_WALKS)
def test_walking_a_leg_never_shows_a_tile_that_is_not_loaded(model, s, d):
    gb, w, lines, holds = walk(model, s, d)
    assert gb.mem("smap_stop") == EXITS[s][d], "Sal arrives at the stop the leg leads to"
    assert w.frames < 1200, w.frames
    assert not w.bad, w.bad[:4]
    gb.run(58)                                                   # (the region settles and the picture is still the world's)
    w.frame()                                                    # (this one only gives the sprite mask its frame before: the arrows bob by 1 px)
    w.bad.clear()
    w.frame()
    assert not w.bad, w.bad[:4]


@pytest.mark.parametrize("s, d", [(0, 3), (3, 1), (5, 0), (10, 2)])
def test_the_c_twin_of_the_asm_walks_the_same(monkeypatch, s, d):
    """ASM_SMAP: the asm burst and scan against the C code of the same lines (build/game-c.gb, make cfall), on a DMG (the asm is DMG-only)."""
    if not C_ROM.exists():
        pytest.skip("needs build/game-c.gb (make cfall)")
    monkeypatch.setattr(test_sound, "ROM", C_ROM)
    gb, w, lines, holds = walk("dmg", s, d)
    assert gb.mem("smap_stop") == EXITS[s][d]
    assert not w.bad, w.bad[:4]


# ---- the cost ---------------------------------------------------------------------------------------------------------------------------------------------------
# The logic's lines per frame (perf_logic_last: 154 lines a frame) over every leg, bounds taken from the measured walks and never to be raised: the DMG's worst
# frame (a job abort or a load) and the Color's at double speed (owner Q92). A hold is a walking frame on which Sal did not move (the stream was behind).
PERF = {"dmg": dict(worst=139, p90=110, holds=0.014), "cgb": dict(worst=84, p90=72, holds=0.0)}


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_walks_cost_stays_within_the_measured_bounds(model):
    allv, holds, frames = [], 0, 0
    for s, d in LEG_WALKS:
        gb, w, lines, h = walk(model, s, d, double=model == "cgb")
        assert not w.bad, (s, d, w.bad[:3])
        allv += lines[2:]
        holds += h
        frames += len(lines)
    allv.sort()
    b = PERF[model]
    assert allv[-1] <= b["worst"], allv[-5:]
    assert allv[len(allv) * 9 // 10] <= b["p90"], allv[len(allv) * 9 // 10]
    assert holds <= b["holds"] * frames, (holds, frames)
