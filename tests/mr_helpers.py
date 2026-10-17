# Milk Run (src/mr.c): what tests/test_mg_milkrun.py needs to read and model: the game's state in the mg union (the
# offsets are parsed from struct mr_state in src/mg.h, so the header stays the one source), a Python model of the street
# (mg_rand's xorshift, the gate and box generator, the columns' tiles) and a bot that rides it.
import json
import re

from conftest import ROOT

MG_H = (ROOT / "src" / "mg.h").read_text()
MR_C = (ROOT / "src" / "mr.c").read_text()
MR_ART_H = (ROOT / "build" / "mr_art.h").read_text()
ART = json.loads((ROOT / "build" / "mr.json").read_text())
MR_BG = 77 + 48                                 # MG_GAME_BG: after the medal icon
MR_OBJ = 56                                     # OBJ_MUG
MG_MILKRUN = 6
BIKER = 6                                       # the venue (chapter 7)
NO_BOX = 0xFFFF
GATE, BOX, FULL, BOTTOM = 0x80, 0x40, 0x02, 0x01


def mr_define(name):
    return int(re.search(rf"#define {name}\s+\(?(\d+)", MR_C).group(1))


def art_define(name):
    return int(re.search(rf"#define {name} (\d+)", MR_ART_H).group(1))


def _macros():
    return {m[0]: int(m[1]) for m in re.findall(r"#define (MR_\w+)\s+(\d+)", MG_H)}


def _layout():
    """struct mr_state's fields: {name: (offset, elements, width, dims)}, and its size."""
    body = re.search(r"struct mr_state \{(.*?)\n\};", MG_H, re.S).group(1)
    mac = _macros()
    out, off = {}, 0
    for line in body.splitlines():
        line = line.split("//")[0].strip()
        if not line:
            continue
        m = re.match(r"(struct mr_toss|uint8_t|int8_t|uint16_t)\s+(.*);", line)
        if m is None:                       # (the `struct xx_tune tn` at the end: the difficulty's tuning row, not read by the tests)
            continue
        width = {"struct mr_toss": 3, "uint8_t": 1, "int8_t": 1, "uint16_t": 2}[m[1]]
        for decl in m[2].split(","):
            decl = decl.strip()
            dims = [mac.get(d, None) if not d.isdigit() else int(d) for d in re.findall(r"\[(\w+)\]", decl)]
            name = re.match(r"\w+", decl)[0]
            n = 1
            for d in dims:
                n *= d
            out[name] = (off, n, width, dims, m[1])
            off += n * width
    return out, off


LAYOUT, STATE_SIZE = _layout()
TOSS_AT = LAYOUT["toss"][0]


def mr(gb):
    """The game's state as a dict: scalars as ints, arrays as lists (the tosses as dicts, the 2-D ones nested)."""
    b = gb.read("story_scratch", STATE_SIZE)
    out = {}
    for name, (off, n, width, dims, typ) in LAYOUT.items():
        if typ == "struct mr_toss":
            out[name] = [dict(t=b[off + 3 * i], side=b[off + 3 * i + 1], y0=b[off + 3 * i + 2]) for i in range(n)]
            continue
        vals = []
        for i in range(n):
            v = int.from_bytes(b[off + i * width:off + (i + 1) * width], "little", signed=(typ == "int8_t"))
            vals.append(v)
        if len(dims) == 2:
            out[name] = [vals[r * dims[1]:(r + 1) * dims[1]] for r in range(dims[0])]
        else:
            out[name] = vals if dims else vals[0]
    return out


def poke(gb, **kw):
    """Scalar fields (and `fkind` / `fcol` slots as (slot, value) pairs) of the game's state, between two whole frames."""
    from conftest import logic_paused
    a = gb.addr("story_scratch")
    with logic_paused(gb):
        for k, v in kw.items():
            off, n, width, dims, typ = LAYOUT[k]
            if n > 1:
                slot, v = v
                gb.write(a + off + slot * width, v & 0xFF)
                if width == 2:
                    gb.write(a + off + slot * width + 1, v >> 8)
            else:
                gb.write(a + off, v & 0xFF)
                if width == 2:
                    gb.write(a + off + 1, (v >> 8) & 0xFF)


# ---- mg_rand and the street's generator (src/mr.c gen_gate / gen_box / make_column) ---------------------------------
class Rng:
    def __init__(self, seed):
        self.s = seed

    def __call__(self):
        s = self.s
        s ^= (s << 7) & 0xFFFF
        s ^= s >> 9
        s ^= (s << 8) & 0xFFFF
        self.s = s
        return s & 0xFF


GATE_BEFORE, GATE_AFTER = mr_define("GATE_BEFORE"), mr_define("GATE_AFTER")
MR_BOXES = mr_define("MR_BOXES")
PICK_COLS = (mr_define("MR_PICK1"), mr_define("MR_PICK2"))
PICK_BEFORE, PICK_AFTER = mr_define("MR_PICK_BEFORE"), mr_define("MR_PICK_AFTER")


def pick_lanes(seed):
    """The pickups' lanes mr_enter takes from the seed (no mg_rand)."""
    a = ((seed >> 8) ^ seed) & 0xFF
    return a % 3, (a % 3 + 1 + ((seed >> 4) & 1)) % 3


def crossing(prev, mask):
    best = 2
    for a in range(3):
        if (prev >> a) & 1:
            continue
        for b in range(3):
            if (mask >> b) & 1:
                continue
            best = min(best, abs(a - b))
    return best


def near(g, b):
    return g + GATE_BEFORE >= b and g <= b + GATE_AFTER


class Street:
    """The street of a seed: the features a stream of columns 0, 1, 2, ... makes live (in the order they join)."""

    def __init__(self, seed):
        self.r = Rng(seed)
        self.pk_lane = pick_lanes(seed)
        self.feats = []                          # (column, kind) in the order they went live
        self.made = 0
        self.bcol, self.bside = NO_BOX, 0
        self.gen_gate(24, 0)
        self.gen_box(0xFFFC)
        self.next = 0

    def gen_gate(self, prev, prev_kind):
        mask = 1 + self.r() % 6
        pot = self.r() & 7
        l = crossing(prev_kind & 7, mask)
        col = (prev + ((20 * l + 87) >> 3) + (self.r() & 15)) & 0xFFFF
        if self.bcol != NO_BOX and near(col, self.bcol):
            mask &= ~(4 if self.bside else 1)
        for p in range(2):
            if col + PICK_BEFORE >= PICK_COLS[p] and col <= PICK_COLS[p] + PICK_AFTER:
                mask &= ~(1 << self.pk_lane[p])
        self.gcol = col
        self.gkind = (GATE | (pot << 3) | mask) if mask else 0

    def box_hits(self, col, side):
        return self.gkind and near(self.gcol, col) and (self.gkind >> (2 if side else 0)) & 1

    def gen_box(self, prev):
        col = (prev + 34 + (self.r() & 31)) & 0xFFFF
        side = self.r() & 1
        while self.box_hits(col, side):
            if not self.box_hits(col, side ^ 1):
                side ^= 1
            else:
                col += 6
        self.bcol, self.bside = col, side
        self.made += 1

    def stream_to(self, c):
        """Stream the columns up to and including c (what mr_enter's 22 and the per-frame stream() have done)."""
        while self.next <= c:
            n = self.next
            while self.gcol <= n:
                g, k = self.gcol, self.gkind
                if k:
                    self.feats.append((g, k))
                self.gen_gate(g, k)
            while self.bcol <= n:
                self.feats.append((self.bcol, BOX | (BOTTOM if self.bside else 0)))
                if self.made < MR_BOXES:
                    self.gen_box(self.bcol)
                else:
                    self.bcol = NO_BOX
            self.next += 1

    def gates(self):
        return [(c, k) for c, k in self.feats if k & GATE]

    def boxes(self):
        return [(c, k) for c, k in self.feats if k & BOX]


def column_tiles(c, feats):
    """The 17 tiles and 17 CGB palettes (map rows 1-17) of world column c given the live features (src/mr.c make_column)."""
    t = [0] * 17
    a = [0] * 17
    top, bot = ART["top_t"], ART["bot_t"]
    ti, bi = (c % art_define("MR_TOP_N")) * 3, (c % art_define("MR_BOT_N")) * 4
    for i in range(3):
        t[i], a[i] = MR_BG + top[ti + i], ART["top_p"][ti + i]
    t[3], t[4] = MR_BG + art_define("MRB_SLAB"), MR_BG + art_define("MRB_KERB_TOP")
    for i in range(5, 11):
        t[i] = MR_BG + art_define("MRB_ROAD0")
    if c % 2 == 0:
        t[7] = t[9] = MR_BG + art_define("MRB_ROAD1")
    t[11], t[12] = MR_BG + art_define("MRB_KERB_BOT"), MR_BG + art_define("MRB_SLAB")
    for i in range(4):
        t[13 + i], a[13 + i] = MR_BG + bot[bi + i], ART["bot_p"][bi + i]
    for col, k in feats:
        d = c - col
        if d not in (0, 1):
            continue
        if k & GATE:
            for lane in range(3):
                if not (k >> lane) & 1:
                    continue
                r = 5 + 2 * lane
                if (k >> (3 + lane)) & 1:
                    t[r], t[r + 1] = MR_BG + art_define("MRB_POT") + d, MR_BG + art_define("MRB_POT") + 2 + d
                else:
                    t[r], t[r + 1] = MR_BG + art_define("MRB_CONE"), MR_BG + art_define("MRB_CONE") + 1
                    a[r] = a[r + 1] = 7
        else:
            r = 11 if k & BOTTOM else 3
            f = MR_BG + art_define("MRB_BOX") + 4 * ((2 if k & BOTTOM else 0) + (1 if k & FULL else 0))
            t[r], t[r + 1] = f + d, f + 2 + d
            a[r] = a[r + 1] = 3
    return t, a


def lane_top(lane):
    return 48 + 16 * lane


# ---- a bot that rides the street (the spec's "a clean run exists at every seed") ---------------------------------------------
HX0, HX1 = 24 + 4, 24 + 4 + 16                  # the bike's hit box in screen x (BIKE_X + 4 .. + 20)


def free_lanes(kind):
    return [l for l in range(3) if not (kind >> l) & 1]


def speed16(s):
    return s["spd"]


def px_after(s, n):
    """The scroll n frames from this state (the street's sub-pixel accumulation, as mr_update)."""
    px, f, spd = s["px"], s["frac"], speed16(s)
    for _ in range(n):
        f += spd
        px += f >> 4
        f &= 15
    return px


def next_box(s):
    """The nearest box that can still take a crate: (column, kerb lane, centre x) or None."""
    px, best = s["px"], None
    for c, k in zip(s["fcol"], s["fkind"]):
        if k & BOX and not k & FULL and c * 8 + 8 + 16 > px + 34 + 20:
            if best is None or c < best[0]:
                best = (c, 2 if k & BOTTOM else 0, c * 8 + 8)
    return best


def next_pickup(s):
    """The nearest pickup not taken and not past the bike: (column, lane) or None."""
    for k in range(2):
        if not (s["pk_got"] >> k) & 1 and PICK_COLS[k] * 8 + 8 > s["px"] + HX0:
            return PICK_COLS[k], s["pk_lane"][k]
    return None


AIM_TOL = 5                                    # how close (px) the bot waits for the aim to be
AIM_OFF = 0                                    # px right of a box's centre the bot aims at (a sloppy player's error; 0 is PERFECT)


def plan(s, with_pick):
    """The lane to be in now: a path of lanes over the events ahead (the live gates, and the next bottle when with_pick), each lane
    free for the whole stretch the bike's hit box overlaps the event, the changes (8 frames a lane) fitting in the gaps between
    them. Returns (lane to go to, ok)."""
    px, v = s["px"], speed16(s)
    ev = []                                        # (px where it starts, px where it ends, the lanes allowed)
    for c, k in zip(s["fcol"], s["fkind"]):
        if k & GATE and c * 8 + 16 > px + HX0:
            ev.append((c * 8 - HX1, c * 8 + 16 - HX0, set(free_lanes(k))))
    pick = next_pickup(s) if with_pick else None
    if pick and pick[0] * 8 - px < 220:
        ev.append((pick[0] * 8 - HX1 + 1, pick[0] * 8 - HX1 + 5, {pick[1]}))      # (it is taken the moment the hit box touches it)
    ev.sort(key=lambda e: (e[0], e[1]))
    lane0 = s["lane"]
    cur_end, state = px, {lane0: None}             # lane after the events so far -> the first event's lane on that path
    for st, en, allowed in ev:
        nxt = {}
        for lane, first in state.items():
            for l in allowed:
                gap = max(0.0, st - max(cur_end, px)) * 16 / v           # frames between the last event's end and this one's start
                need = 8 * abs(l - lane) + (2 if l != lane else 0)
                ok = (l == lane) if st <= px else gap >= need           # (active now: no change)
                if ok:
                    nf = l if first is None else first
                    if l not in nxt or abs(nf - lane0) < abs(nxt[l] - lane0):
                        nxt[l] = nf
        if not nxt:
            return None, False
        state, cur_end = nxt, en
    firsts = [f for f in state.values() if f is not None]
    if not firsts:
        return lane0, True
    return min(firsts, key=lambda l: (abs(l - lane0), l)), True


def bot(s, deliver=True, collect=True):
    """What the bot does this frame: (the lane it wants or None to hold, the toss now: None, "a" (top kerb) or "b" (bottom))."""
    px = s["px"]
    gates = sorted((c, k) for c, k in zip(s["fcol"], s["fkind"]) if k & GATE)
    if any(c * 8 < px + HX1 and c * 8 + 16 > px + HX0 for c, k in gates):
        want = None                                # inside a gate: stay in the free lane
    else:
        ahead = [(c, k) for c, k in gates if c * 8 + 16 > px + HX0]
        free = free_lanes(ahead[0][1]) if ahead else [0, 1, 2]
        want, ok = plan(s, collect)
        if not ok:
            want, ok = plan(s, False)
        if not ok:
            want = min(free, key=lambda l: (abs(l - s["lane"]), l))
    toss = None
    if deliver and s["crates"] and s["inv"] <= 60:
        box = next_box(s)
        side = 1 if box and box[1] == 2 else 0
        if box and not any(t["t"] and t["side"] == side for t in s["toss"]) and abs(box[2] + AIM_OFF - (px_after(s, 17) + 34)) <= AIM_TOL:
            toss = "b" if side else "a"            # (one crate in the air a box; A the top kerb, B the bottom)
    return want, toss
