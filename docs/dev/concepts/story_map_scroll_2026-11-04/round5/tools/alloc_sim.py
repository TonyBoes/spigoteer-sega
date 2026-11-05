"""Round 5: the dynamic tile-slot allocator, simulated frame by frame along every walk (all 22 directed legs of world2.LEGS) in the late world.
Walk: Sal 3 px a frame, 30 still frames at the start, the round-2 camera follow (step = gap >> 2, 1 to 4 px), here held back whenever a tile the next
view needs is not yet in VRAM.  Allocator: SLOTS slots, a tile is looked up by id; a slot is free when its tile is not in the view the camera has now
or will have next frame; the free slot whose tile was needed longest ago is taken (LRU).  Look-ahead: the lines beyond the view in the direction of
travel, up to LA lines, nearest first, only into free slots.  The VBlank queue drains BUDGET bytes a frame: a loaded tile costs 16, a new map line
costs one byte per cell (DMG) or two (Color: id + attribute).
python3 alloc_sim.py [dmg|color] [LA] [lru|rr]   (rr: the first free slot after a rotating pointer, no ages: what the engine would keep in RAM)"""
import sys
from collections import defaultdict

import render2 as R
import stats2 as S
import world2 as W

MODE = sys.argv[1] if len(sys.argv) > 1 else "dmg"
LA = int(sys.argv[2]) if len(sys.argv) > 2 else 4
POLICY = sys.argv[3] if len(sys.argv) > 3 else "lru"
SLOTS = 176 if MODE == "dmg" else 352
BUDGET = 86
MAPB = 1 if MODE == "dmg" else 2
CW, CH = W.CW, W.CH
world = W.WORLD_DMG if MODE == "dmg" else W.WORLD
sg = S.sig_grid(world)
ids = {}
G = [[ids.setdefault(sg[y][x], len(ids)) for x in range(CW)] for y in range(CH)]


def view_cells(X, Y):
    return range(X // 8, (X + 159) // 8 + 1), range(Y // 8, (Y + 143) // 8 + 1)


def tiles_of(X, Y):
    xs, ys = view_cells(X, Y)
    return {G[y][x] for y in ys for x in xs}


class Vram:
    def __init__(self):
        self.slot_of = {}            # tile id -> slot
        self.tile_in = [None] * SLOTS
        self.used = [0] * SLOTS      # frame the tile was last needed
        self.loads = 0
        self.evictions = 0
        self.ptr = 0

    def free_slot(self, keep, frame):
        if POLICY == "rr":
            for k in range(SLOTS):
                s = (self.ptr + k) % SLOTS
                t = self.tile_in[s]
                if t is None or t not in keep:
                    self.ptr = (s + 1) % SLOTS
                    return s
            return None
        best, bs = None, None
        for s in range(SLOTS):
            t = self.tile_in[s]
            if t is None:
                return s
            if t in keep:
                continue
            if best is None or self.used[s] < best:
                best, bs = self.used[s], s
        return bs

    def load(self, t, keep, frame):
        s = self.free_slot(keep, frame)
        if s is None:
            return False
        old = self.tile_in[s]
        if old is not None:
            del self.slot_of[old]
            self.evictions += 1
        self.tile_in[s] = t
        self.slot_of[t] = s
        self.used[s] = frame
        self.loads += 1
        return True


def lines_ahead(X, Y, dx, dy):
    """the cells of the LA lines beyond the view in the direction of travel, nearest line first"""
    xs, ys = view_cells(X, Y)
    out = []
    for k in range(1, LA + 1):
        if dx:
            cx = xs[-1] + k if dx > 0 else xs[0] - k
            if 0 <= cx < CW:
                out.append([(cx, y) for y in ys])
        if dy:
            cy = ys[-1] + k if dy > 0 else ys[0] - k
            if 0 <= cy < CH:
                out.append([(x, cy) for x in xs])
    return out


def walk(a, b):
    pts = W.leg_points(a, b)
    cam = list(R.view_cam(a))
    v = Vram()
    for t in tiles_of(*cam):
        v.load(t, set(), 0)
    v.loads = 0
    seq = [pts[0]] * 30 + pts[1:] + [pts[-1]] * 30
    frame, stall, run, longest = 0, 0, 0, 0
    maxb, sumb, nmove, minfree = 0, 0, 0, SLOTS
    d0 = W.exit_dir(a, b)
    hint = {"R": (1, 0), "L": (-1, 0), "D": (0, 1), "U": (0, -1)}[d0]       # the first direction of the leg, known while Sal stands at the stop
    for p in seq:
        frame += 1
        tgt = R.clampcam(p[0] - 80, p[1] - 12 - 72)
        step = []
        for k in (0, 1):
            gap = tgt[k] - cam[k]
            s = max(1, min(4, abs(gap) >> 2)) if gap else 0
            step.append(s if gap > 0 else -s)
        if step[0] or step[1]:
            hint = ((step[0] > 0) - (step[0] < 0), (step[1] > 0) - (step[1] < 0))
        nxt = (cam[0] + step[0], cam[1] + step[1])
        have = tiles_of(*cam)
        need = tiles_of(*nxt)
        keep = have | need
        for t in keep:
            if t in v.slot_of:
                v.used[v.slot_of[t]] = frame
        minfree = min(minfree, SLOTS - len(keep))
        bytes_ = 0
        newcells = 0
        if nxt != tuple(cam):
            xs0, ys0 = view_cells(*cam)
            xs1, ys1 = view_cells(*nxt)
            newcells = len({(x, y) for x in xs1 for y in ys1} - {(x, y) for x in xs0 for y in ys0})
        missing = [t for t in need if t not in v.slot_of]
        mapb = newcells * MAPB
        ready = True
        for t in missing:
            if bytes_ + 16 <= BUDGET and v.load(t, keep, frame):
                bytes_ += 16
            ready = False                              # the tile arrives in this frame's VBlank: the view may use it next frame
        if ready:
            cam[0], cam[1] = nxt
            bytes_ += mapb
        # look-ahead into free slots with what is left of the budget
        for line in lines_ahead(cam[0], cam[1], *hint):
            for (x, y) in line:
                t = G[y][x]
                if t not in v.slot_of and bytes_ + 16 <= BUDGET:
                    if v.load(t, keep | {G[yy][xx] for (xx, yy) in line}, frame):
                        bytes_ += 16
        moving = bool(step[0] or step[1])
        if moving:
            nmove += 1
            sumb += bytes_
            maxb = max(maxb, bytes_)
            if not ready:
                stall += 1
                run += 1
                longest = max(longest, run)
            else:
                run = 0
    return dict(frames=len(seq), moving=nmove, stall=stall, longest=longest, maxb=maxb, meanb=sumb / max(nmove, 1), minfree=minfree, loads=v.loads,
                evict=v.evictions)


if __name__ == "__main__":
    print(f"{MODE.upper()} allocator, {SLOTS} slots, look-ahead {LA} lines, budget {BUDGET} B/frame; late world")
    tot = defaultdict(int)
    for (a, b) in sorted(W.LEGS):
        for (p, q) in ((a, b), (b, a)):
            r = walk(p, q)
            print(f"{p:8s}-> {q:8s} moving {r['moving']:3d}  stalled {r['stall']:3d} (longest {r['longest']:2d})  max {r['maxb']:3d} B  mean {r['meanb']:5.1f} B  "
                  f"min free {r['minfree']:3d}  loads {r['loads']:4d}  evictions {r['evict']:4d}")
            for k in ("moving", "stall"):
                tot[k] += r[k]
            tot["longest"] = max(tot["longest"], r["longest"])
            tot["maxb"] = max(tot["maxb"], r["maxb"])
            tot["minfree"] = min(tot.get("minfree", 999), r["minfree"])
    print("TOTAL moving frames", tot["moving"], "stalled", tot["stall"], f"({100 * tot['stall'] / tot['moving']:.1f}%)", "longest stall", tot["longest"],
          "max bytes in a frame", tot["maxb"], "min free slots", tot["minfree"])
