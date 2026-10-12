# Asteroid Delivery (src/ad.c): what tests/test_mg_asteroid.py needs to read and model: the game's state in the mg union (the
# offsets are parsed from struct ad_state in src/mg.h, so the header stays the one source), a Python model of the beaker and
# the rocks (the same integer arithmetic as ad.c: thrust, cap, drag, walls, the dock, the rocks' cores) and a bot that flies
# it by a search over that model.
import heapq
import json
import re

from conftest import ROOT

MG_H = (ROOT / "src" / "mg.h").read_text()
AD_C = (ROOT / "src" / "ad.c").read_text()
AD_ART_H = (ROOT / "build" / "ad_art.h").read_text()
ART = json.loads((ROOT / "build" / "ad.json").read_text())
AD_BG = 77 + 48                                 # MG_GAME_BG: after the medal icon
MG_ASTEROID = 9
SPACE = 9                                       # the venue (chapter 10)
OBJ_BEAKER = 56                                 # the venue's drink frame 0 (OBJ_MUG)


def ad_define(name):
    return int(re.search(rf"#define {name}\s+\(?(0x[0-9A-Fa-f]+|\d+)", AD_C).group(1), 0)


def art_define(name):
    return int(re.search(rf"#define {name} (\d+)", AD_ART_H).group(1))


def _layout():
    """struct ad_state's fields: {name: (offset, elements, width, signed)}, and its size."""
    body = re.search(r"struct ad_state \{(.*?)\n\};", MG_H, re.S).group(1)
    macros = {"AD_ROCKS": int(re.search(r"#define AD_ROCKS\s+(\d+)", MG_H).group(1))}
    out, off = {}, 0
    for line in body.splitlines():
        line = line.split("//")[0].strip()
        if not line:
            continue
        m = re.match(r"(uint8_t|int8_t|uint16_t|int16_t)\s+(.*);", line)
        width = 2 if "16" in m[1] else 1
        for decl in m[2].split(","):
            decl = decl.strip()
            dims = [macros.get(d) if not d.isdigit() else int(d) for d in re.findall(r"\[(\w+)\]", decl)]
            n = 1
            for d in dims:
                n *= d
            out[re.match(r"\w+", decl)[0]] = (off, n, width, m[1].startswith("int"), dims)
            off += n * width
    return out, off


LAYOUT, STATE_SIZE = _layout()


def ad(gb):
    """The game's state as a dict: scalars as ints, arrays as lists (the 2-D ones nested)."""
    b = gb.read("story_scratch", STATE_SIZE)
    out = {}
    for name, (off, n, width, signed, dims) in LAYOUT.items():
        vals = [int.from_bytes(b[off + i * width:off + (i + 1) * width], "little", signed=signed) for i in range(n)]
        out[name] = [vals[r * dims[1]:(r + 1) * dims[1]] for r in range(dims[0])] if len(dims) == 2 else (vals if dims else vals[0])
    return out


def poke(gb, **kw):
    """Scalar fields (or `rx` as (index, value)) of the game's state, between two whole frames."""
    from conftest import logic_paused
    a = gb.addr("story_scratch")
    with logic_paused(gb):
        for k, v in kw.items():
            off, n, width, signed, dims = LAYOUT[k]
            if n > 1:
                i, v = v
                off += i * width
            gb.write(a + off, v & 0xFF)
            if width == 2:
                gb.write(a + off + 1, (v >> 8) & 0xFF)


# ---- the model --------------------------------------------------------------------------------------------------------------
AS_FLY, AS_TUMBLE, AS_GAP, AS_OUT = range(4)
LOOP = 176 << 8
LANE_SPEED = [[64, 96, 128, 96, 64], [96, 144, 192, 144, 96], [128, 192, 256, 192, 128]]
PORTHOLE_CX = [20, 76, 132]
THRUST, CAP, SLOW = 8, 320, 192
X_MIN, X_MAX, Y_MAX, Y_MIN, Y_MIN_DOCK = 4, 156, 120, 28, 24
LANE_TOP0 = 32


def drag(v):
    d = (v >> 5) if v > 0 else ((-v) >> 5)
    if not d and v:
        d = 1
    return v - d if v > 0 else v + d


def axis(v, t):
    if t:
        v = max(-CAP, min(CAP, v + t * THRUST))
    return drag(v)


def rocks_step(rx, spd):
    out = []
    for k, x in enumerate(rx):
        sp = LANE_SPEED[spd][k >> 1]
        if not (k >> 1) & 1:
            x += sp
            if x >= LOOP:
                x -= LOOP
        else:
            if x < sp:
                x += LOOP
            x -= sp
        out.append(x)
    return out


def hit(x, y, rx, m=0):
    """The beaker's body (x +- 3, y + 3 .. y + 15) against a rock's core (rx + 2 .. + 14 on the screen, lane top + 2 .. + 14)."""
    bx, by = x >> 8, y >> 8
    for k, r in enumerate(rx):
        ry = LANE_TOP0 + 16 * (k >> 1)
        if by + 3 - m >= ry + 14 or by + 15 + m <= ry + 2:
            continue
        sx = (r >> 8) - 16
        if bx + 3 + m <= sx + 2 or bx - 3 - m >= sx + 14:
            continue
        return True
    return False


def beaker_step(x, y, vx, vy, tx, ty, lit):
    """One frame of ad.c's beaker(): -> (x, y, vx, vy, event) with event None, 'deliver', 'whoa' (it has bounced) or None;
    the rocks are tested by the caller with `hit` (after the rocks moved)."""
    vx, vy = axis(vx, tx), axis(vy, ty)
    x, y = x + vx, y + vy
    if x < X_MIN << 8:
        x, vx = X_MIN << 8, 0
    elif x > X_MAX << 8:
        x, vx = X_MAX << 8, 0
    bx = x >> 8
    zx = PORTHOLE_CX[lit] - 8
    ymin = Y_MIN_DOCK if (bx + 3 > zx and bx < zx + 19) else Y_MIN
    if y > Y_MAX << 8:
        y, vy = Y_MAX << 8, 0
    elif y < ymin << 8:
        y, vy = ymin << 8, 0
    ev = None
    if y < Y_MIN << 8:
        if abs(vx) <= SLOW and abs(vy) <= SLOW:
            ev = "deliver"
        else:
            vx = -(vx >> 1)
            vy = -(vy >> 1) if vy < 0 else (vy >> 1)
            y = Y_MIN << 8
            ev = "whoa"
    return x, y, vx, vy, ev


def read_model(s):
    return dict(x=s["x"], y=s["y"], vx=s["vx"], vy=s["vy"], rx=list(s["rx"]), spd=s["spd"], lit=s["lit"])


# ---- the bot: a best-first search over (position, velocity, time) ------------------------------------------------------------
KEYS = [(tx, ty) for ty in (-1, 0, 1) for tx in (-1, 0, 1)]
HOLD = 4                                       # frames a choice is held


def plan(m, horizon=800, limit=120000, margin=1, prev=(0, 0)):
    """A list of (tx, ty) macro steps (each held HOLD frames) that delivers without a hit, or None. (`prev` is unused: the game
    sees a held key on the very frame it is pressed.)
    """
    rx0 = [list(m["rx"])]

    def rocks(t):                              # the rocks t frames on (cached)
        while len(rx0) <= t:
            rx0.append(rocks_step(rx0[-1], m["spd"]))
        return rx0[t]

    gx = PORTHOLE_CX[m["lit"]] << 8
    start = (m["x"], m["y"], m["vx"], m["vy"], prev)

    def h(x, y):
        dy = max(0, y - (26 << 8))
        return max(dy / 256 / 0.95, abs(x - gx) / 256 / 0.95)

    heap = [(h(start[0], start[1]) * 1.5, 0, start, None)]
    seen = {}
    parent = {}
    n = 0
    while heap and n < limit:
        f, t, st, key = heapq.heappop(heap)
        n += 1
        x, y, vx, vy, pk = st
        for (tx, ty) in KEYS:
            cx, cy, cvx, cvy = x, y, vx, vy
            ok, ev = True, None
            for i in range(HOLD):
                kx, ky = tx, ty
                cx, cy, cvx, cvy, ev = beaker_step(cx, cy, cvx, cvy, kx, ky, m["lit"])
                if hit(cx, cy, rocks(t + i + 1), margin) and ev != "deliver":
                    ok = False
                    break
                if ev == "whoa":
                    ok = False
                    break
                if ev == "deliver":
                    break
            if not ok:
                continue
            node = (t + HOLD, cx, cy, cvx, cvy, (tx, ty))
            if ev == "deliver":
                path = [(tx, ty)]
                k = key
                while k is not None:
                    path.append(parent[k][1])
                    k = parent[k][0]
                return path[::-1]
            q = (t + HOLD) // 8, cx >> 10, cy >> 10, cvx >> 6, cvy >> 6, tx, ty
            if q in seen or t + HOLD > horizon:
                continue
            seen[q] = 1
            parent[node] = (key, (tx, ty))
            heapq.heappush(heap, (t + HOLD + h(cx, cy) * 1.5, t + HOLD, (cx, cy, cvx, cvy, (tx, ty)), node))
    return None
