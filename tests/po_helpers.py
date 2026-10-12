# The Pour-Off (src/po.c): what tests/test_pouroff.py needs to read: the game's state in the mg union (the offsets are parsed from
# struct po_state in src/po.h, so the header stays the one source), the sprites on a line, and a bot that plays the race.
import re

from conftest import ROOT

PO_H = (ROOT / "src" / "po.h").read_text()
PO_C = (ROOT / "src" / "po.c").read_text()
MG_POUROFF = 11
SEATS, MUGS, WIN = 12, 16, 20
SEAT_X = [40, 72, 104]
TAP_X, SPOUT_X, SPOUT_D, DREGS_X = 120, 136, 16, 24
PS_EMPTY, PS_THIRSTY, PS_DRINKING = range(3)
PM_FREE, PM_FULL, PM_HELD, PM_EMPTY, PM_BREAK = range(5)
PD_IDLE, PD_THINK, PD_FILL, PD_SLIDE, PD_WAIT = range(5)
PR_PLAY, PR_WIN, PR_DREGS, PR_LIVES = range(4)
PT_THINK0, PT_THINK15, PT_LEAD, PT_TRAIL, PT_REACT, PT_AHEAD, PT_COMIC, PT_SLIP = range(8)
BT_IDLE, BT_WALK1, BT_WALK2, BT_FILL, BT_SLIDE, BT_CATCH, BT_FAIL = range(7)


def po_define(name):
    return int(re.search(rf"#define {name}\s+\(?(\d+)", PO_C).group(1))


def _fields(struct):
    """struct {name}'s fields in order: [(name, count, width)] (uint8_t only; arrays [N] or [N][M] by number or PO_ macro)."""
    body = re.search(rf"struct {struct} \{{(.*?)\n\}};", PO_H, re.S).group(1)
    mac = {m[0]: int(m[1]) for m in re.findall(r"#define (PO_\w+)\s+(\d+)", PO_H)}
    out = []
    for line in body.splitlines():
        line = line.split("//")[0].strip()
        if not line:
            continue
        m = re.match(r"(uint8_t|struct \w+)\s+(.*);", line)
        for decl in m[2].split(","):
            decl = decl.strip()
            dims = [int(d) if d.isdigit() else mac[d] for d in re.findall(r"\[(\w+)\]", decl)]
            n = 1
            for d in dims:
                n *= d
            out.append((re.match(r"\w+", decl)[0], m[1], n, dims))
    return out


def _layout(struct, base=0):
    """{field: (offset, count, dims, struct type or None)}, size."""
    out, off = {}, base
    for name, typ, n, dims in _fields(struct):
        if typ == "uint8_t":
            out[name] = (off, n, dims, None)
            off += n
        else:
            sub, size = _layout(typ.split()[1])
            out[name] = (off, n, dims, (typ.split()[1], sub, size))
            off += n * size
    return out, off - base


LAYOUT, STATE_SIZE = _layout("po_state")


def _read(raw, layout, off0=0):
    out = {}
    for name, (off, n, dims, sub) in layout.items():
        if sub is None:
            vals = list(raw[off0 + off:off0 + off + n])
        else:
            _, sublayout, size = sub
            vals = [_read(raw, sublayout, off0 + off + i * size) for i in range(n)]
        if len(dims) == 2 and sub is None:
            vals = [vals[r * dims[1]:(r + 1) * dims[1]] for r in range(dims[0])]
        out[name] = vals if (dims or sub is not None and n > 1) else vals[0]
    return out


def po(gb):
    """The game's state as a dict (arrays as lists, the structs as dicts), as of a whole game frame: PyBoy's frame ends a few
    lines into the game's logic, so a plain read can see a frame half done (a mug being made); one frame is run paused first
    (conftest.logic_paused: the game's logic skips it). A key pressed or released just before is seen by the frame before it."""
    from conftest import logic_paused
    with logic_paused(gb):
        return _read(gb.read("story_scratch", STATE_SIZE), LAYOUT)


def offset(path):
    """Offset in the state of a field: 'res', 'y.x', 'd.score', 'seat.3.st' (a struct array element), 'mug.0.x', 'tune.4'."""
    parts = path.split(".")
    lay, off = LAYOUT, 0
    i = 0
    while True:
        o, n, dims, sub = lay[parts[i]]
        off += o
        i += 1
        if sub is None:
            if dims and len(parts) > i:
                off += int(parts[i])
            return off
        _, lay, size = sub
        if n > 1:
            off += int(parts[i]) * size
            i += 1


def pokes(gb, items):
    """Poke bytes ({path: value}) between two whole frames (one paused frame, however many)."""
    from conftest import logic_paused
    a = gb.addr("story_scratch")
    with logic_paused(gb):
        for path, v in items.items():
            gb.write(a + offset(path), v & 0xFF)


def poke(gb, path, value):
    pokes(gb, {path: value})


def seat_set(gb, bar, k, st=PS_THIRSTY, t=240, v=0, who=0):
    i = bar * 3 + k
    pokes(gb, {f"seat.{i}.st": st, f"seat.{i}.t": t, f"seat.{i}.v": v, f"seat.{i}.who": who, f"seat.{i}.sh": 0, f"seat.{i}.dirty": 1})


def mug_set(gb, i, st, x, bar, own, aux=0):
    pokes(gb, {f"mug.{i}.st": st, f"mug.{i}.x": x, f"mug.{i}.bar": bar, f"mug.{i}.own": own, f"mug.{i}.aux": aux})


def quiet(gb, frames=255):
    """No new patrons for a while."""
    poke(gb, "spawn_t", frames)


def po_win(gb):
    """The race is won (the state says so) and the framework goes to its result phase: what a won race leaves behind."""
    poke(gb, "res", PR_WIN)
    gb.write("mg_phase", 4)                              # MG_RESULT: mg.c leaves the Pour-Off for FINALE_B


def oam(gb, i):
    a = 0xFE00 + 4 * i
    return dict(y=gb.mem(a), x=gb.mem(a + 1), tile=gb.mem(a + 2), prop=gb.mem(a + 3))


# ---- a bot that plays the race -------------------------------------------------------------------------------------------------------
def _claims(s, bar, own):
    """How many of `own`'s full drinks are in flight on `bar` (each takes the next thirsty seat ahead of it)."""
    return sum(1 for m in s["mug"] if m["st"] == PM_FULL and m["own"] == own and m["bar"] == bar)


def pick_seat(s, ahead_skip=True, react=0):
    """The bot's target: the thirsty seat with the shortest slide from the Spigoteer's spout that none of his drinks in flight is
    heading for, and Dregs's drinks will not reach first. -> (bar, k) or None."""
    best = None
    for b in range(4):
        m = _claims(s, b, 0)
        seats = [k for k in (2, 1, 0) if s["seat"][b * 3 + k]["st"] == PS_THIRSTY
                 and 2 * (240 - s["seat"][b * 3 + k]["t"]) >= react]      # (a human sees a new patron after a moment)
        if m >= len(seats):
            continue
        k = seats[m]
        px = SEAT_X[k]
        # Dregs's drinks: the one that will take this seat is the (dm)th thirsty one from the left; skip it when his is closer
        dm = _claims(s, b, 1)
        left = [kk for kk in (0, 1, 2) if s["seat"][b * 3 + kk]["st"] == PS_THIRSTY]
        if ahead_skip and dm and k in left[:dm]:
            continue
        dist = SPOUT_X - (px + 16)
        if best is None or dist < best[0]:
            best = (dist, b, k)
    return None if best is None else best[1:]


def bot_keys(s, state):
    """The keys to hold this frame (a set of 'up', 'down', 'a'). `state` is the bot's memory (a dict)."""
    y = s["y"]
    keys = set()
    # an empty of his coming up on another bar: go there (the glass under the spout goes along when A stays down)
    urgent = None
    for m in s["mug"]:
        if m["st"] == PM_EMPTY and m["own"] == 0:
            eta = max(0, TAP_X - m["x"])
            if urgent is None or eta < urgent[0]:
                urgent = (eta, m["bar"])
    want = None
    soon = urgent is not None and urgent[0] <= state.get("lead", 16)
    if soon:
        want = urgent[1]
    if y["fill"] and not soon:
        if 27 <= y["pour_t"] < 32 or (not state.get("perfect", True) and y["fill"] >= 16):
            return keys                                   # released: the drink slides
        keys.add("a")
        return keys
    if want is None and not y["hold"]:
        t = pick_seat(s, react=state.get("react", 0))
        if t is not None:
            want = t[0]
    if want is None:
        return keys
    if y["bar"] != want:
        n = (want - y["bar"]) % 4
        keys.add("down" if n <= 2 else "up")
        if y["fill"] >= 16:
            keys.add("a")
        return keys
    if not soon and not y["fill"] and not y["hold"] and y["catch_pose"] == 0 and not state.get("cool"):
        keys.add("a")
    return keys


class Bot:
    """Plays frame by frame: reads the state, holds the keys bot_keys wants. state: {"perfect": aim for the sparkle window,
    "lead": frames before an empty reaches the tap that the bot goes to its bar}."""
    def __init__(self, gb, **state):
        self.gb, self.state, self.held, self.s = gb, {"perfect": True, **state}, set(), None

    def step(self, n=1, each=None):
        for _ in range(n):
            s = po(self.gb)
            if self.s is not None and self.s["y"]["fill"] and not s["y"]["fill"]:
                self.state["cool"] = self.state.get("lag", 0)        # (a human's pause after a throw)
            elif self.state.get("cool"):
                self.state["cool"] -= 1
            keys = bot_keys(s, self.state)
            if keys & self.held & {"up", "down"}:        # (a bar change needs a fresh press: let go for a frame)
                keys = keys - {"up", "down"}
            for k in self.held - keys:
                self.gb.release(k)
            for k in keys - self.held:
                self.gb.hold(k)
            self.held = keys
            self.gb.run(1)
            self.s = s
            if each:
                each(self.gb)

    def release_all(self):
        for k in self.held:
            self.gb.release(k)
        self.held = set()
