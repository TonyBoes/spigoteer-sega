# Monkey Business (src/mk.c): what tests/test_mg_monkey.py needs to read and model: the game's state in the mg union (the offsets
# are parsed from struct mk_state / mk_crate in src/mg.h, so the header stays the one source), the generated art (build/mk.json)
# and a bot that plays it.
import json
import re

from conftest import ROOT

MG_H = (ROOT / "src" / "mg.h").read_text()
MK_C = (ROOT / "src" / "mk.c").read_text()
MK_ART_H = (ROOT / "build" / "mk_art.h").read_text()
ART = json.loads((ROOT / "build" / "mk.json").read_text())
MK_BG = 77 + 48                                   # MG_GAME_BG: after the medal icon
MK_OBJ = 56                                       # OBJ_MUG
MG_MONKEY = 8
ZOO = 8                                           # the venue (chapter 9)
MC_IDLE, MC_RATTLE, MC_UP, MC_AFTER, MC_FLY = range(5)
MA_NONE, MA_HOP, MA_SHOO = range(3)
MP_NONE, MP_LEFT, MP_RIGHT, MP_SHOO = range(4)
ML_NONE, ML_SHOOED, ML_QUICK, ML_PARROT, ML_WHIFF, ML_THEFT = range(6)


def mk_define(name):
    m = re.search(rf"#define {name}\s+\(?(\d+)", MK_C) or re.search(rf"#define {name}\s+\(?(\d+)", MG_H)
    return int(m.group(1))


def art_define(name):
    return int(re.search(rf"#define {name} (\d+)", MK_ART_H).group(1))


def _layout():
    """struct mk_state's fields: {name: (offset, elements, width, dims)}, and its size (the crates array has 4-byte records)."""
    body = re.search(r"struct mk_state \{(.*?)\n\};", MG_H, re.S).group(1)
    mac = {m[0]: int(m[1]) for m in re.findall(r"#define (MK_\w+)\s+(\d+)", MG_H)}
    out, off = {}, 0
    for line in body.splitlines():
        line = line.split("//")[0].strip()
        if not line:
            continue
        m = re.match(r"(uint8_t|uint16_t|struct mk_crate)\s+(.*);", line)
        if m is None:                       # (the `struct xx_tune tn` at the end: the difficulty's tuning row, not read by the tests)
            continue
        width = {"uint8_t": 1, "uint16_t": 2, "struct mk_crate": 4}[m[1]]
        for decl in m[2].split(","):
            decl = decl.strip()
            dims = [int(d) if d.isdigit() else mac[d] for d in re.findall(r"\[(\w+)\]", decl)]
            name = re.match(r"\w+", decl)[0]
            n = 1
            for d in dims:
                n *= d
            out[name] = (off, n, width, dims)
            off += n * width
    return out, off


LAYOUT, STATE_SIZE = _layout()


def mk(gb):
    """The game's state as a dict: scalars as ints, arrays as lists (2-D ones nested); 'c' is a list of crate dicts."""
    b = gb.read("story_scratch", STATE_SIZE)
    out = {}
    for name, (off, n, width, dims) in LAYOUT.items():
        if name == "c":
            out[name] = [dict(st=b[off + 4 * i], kind=b[off + 4 * i + 1], t=b[off + 4 * i + 2], u=b[off + 4 * i + 3])
                         for i in range(n)]
            continue
        vals = [int.from_bytes(b[off + i * width:off + (i + 1) * width], "little") for i in range(n)]
        if len(dims) == 2:
            out[name] = [vals[r * dims[1]:(r + 1) * dims[1]] for r in range(dims[0])]
        else:
            out[name] = vals if dims else vals[0]
    return out


def poke(gb, **kw):
    """Scalar fields of the game's state, between two whole frames."""
    from conftest import logic_paused
    a = gb.addr("story_scratch")
    with logic_paused(gb):
        for k, v in kw.items():
            off, n, width, dims = LAYOUT[k]
            gb.write(a + off, v & 0xFF)
            if width == 2:
                gb.write(a + off + 1, (v >> 8) & 0xFF)


def poke_crate(gb, k, **kw):
    """Fields of crate k (st, kind, t, u), between two whole frames."""
    from conftest import logic_paused
    a = gb.addr("story_scratch") + LAYOUT["c"][0] + 4 * k
    with logic_paused(gb):
        for f, v in kw.items():
            gb.write(a + ("st", "kind", "t", "u").index(f), v)


def glyph(ch):
    """The HUD glyph tile of a character (build/art.h TILE_GLYPH_*)."""
    art_h = (ROOT / "build" / "art.h").read_text()
    return int(re.search(rf"#define TILE_GLYPH_{ch} (\d+)", art_h).group(1))


def deadline(c):
    """Frames until a crate's monkey grabs (None: no monkey there)."""
    if c["kind"] or c["st"] not in (MC_RATTLE, MC_UP):
        return None
    return c["u"] - c["t"] if c["st"] == MC_UP else 20 - c["t"] + c["u"]


def bot_keys(s, delay=0):
    """What a good player presses now: the key to hold ('left' / 'right' / 'a' / None) for state s. Nearest deadline first; the
    shoo starts when the lid is about to open (4 frames before: the swing lands as it does). With `careless` it also shoos the
    parrot's crate when it stands in front of it."""
    if s["act"] or s["lock"]:
        return None
    want = [(deadline(c), k) for k, c in enumerate(s["c"]) if deadline(c) is not None and (delay == 0 or (c["st"] == MC_UP and c["t"] >= delay))]
    if not want:
        return None
    want.sort()
    k = want[0][1]
    c = s["c"][k]
    if k == s["pos"]:
        if c["st"] == MC_UP or (c["st"] == MC_RATTLE and 20 - c["t"] <= 4):
            return "a"
        return None
    return "right" if k > s["pos"] else "left"


def run_bot(gb, step, stop, limit=4000, keys=bot_keys, hook=None):
    """Plays frame by frame: each state's key goes down for 2 frames (one edge). step(gb, n) advances n frames (the caller's checked
    `frames`); stop(state) ends it; hook(state) sees each state."""
    for _ in range(limit):
        s = mk(gb)
        if hook:
            hook(s)
        if stop(s):
            return s
        key = keys(s)
        if key:
            gb.hold(key)
            step(gb, 2)
            gb.release(key)
        else:
            step(gb, 1)
    raise AssertionError("the stop condition was not reached")
