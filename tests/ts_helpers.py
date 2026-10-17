# T-Shirt Cannon (src/ts.c): what tests/test_mg_tshirt.py needs to read and model: the game's state in the mg union (the offsets are
# parsed from struct ts_state in src/mg.h, so the header stays the one source), the art / physics numbers (build/ts.json, from
# tools/gen_ts.py and tools/cannon_table.py) and a Python model of the flight.
import json
import re

from conftest import ROOT

MG_H = (ROOT / "src" / "mg.h").read_text()
TS_C = (ROOT / "src" / "ts.c").read_text()
ART = json.loads((ROOT / "build" / "ts.json").read_text())
TS_ART_H = (ROOT / "build" / "ts_art.h").read_text()
TS_BG = 77 + 48                                   # MG_GAME_BG: after the medal icon
TS_OBJ = 56
MG_TSHIRT = 1
STADIUM = 1                                       # the venue (chapter 2)
FAN_FIRST, FAN_N = 9, 11
PMAX = ART["pmax"]
SHORT, CROWD, OVER = 0, 1, 2


def ts_define(name):
    return int(re.search(rf"#define {name}\s+\(?(\d+)", TS_C).group(1))


SHOTS = ts_define("TS_SHOTS")


def _layout():
    """struct ts_state's fields: {name: (offset, elements, width, dims, signed)}, and its size."""
    body = re.search(r"struct ts_state \{(.*?)\n\};", MG_H, re.S).group(1)
    out, off = {}, 0
    for line in body.splitlines():
        line = line.split("//")[0].strip()
        if not line:
            continue
        m = re.match(r"(uint8_t|uint16_t|int8_t|int16_t)\s+(.*);", line)
        if m is None:                       # (the `struct xx_tune tn` at the end: the difficulty's tuning row, not read by the tests)
            continue
        width = {"uint8_t": 1, "uint16_t": 2, "int8_t": 1, "int16_t": 2}[m[1]]
        signed = m[1].startswith("int")
        for decl in m[2].split(","):
            decl = decl.strip()
            dims = [int(d) for d in re.findall(r"\[(\d+)\]", decl)]
            name = re.match(r"\w+", decl)[0]
            n = 1
            for d in dims:
                n *= d
            out[name] = (off, n, width, dims, signed)
            off += n * width
    return out, off


LAYOUT, STATE_SIZE = _layout()


def ts(gb):
    """The game's state as a dict: scalars as ints (signed where the field is), arrays as lists (2-D ones nested)."""
    b = gb.read("story_scratch", STATE_SIZE)
    out = {}
    for name, (off, n, width, dims, signed) in LAYOUT.items():
        vals = [int.from_bytes(b[off + i * width:off + (i + 1) * width], "little", signed=signed) for i in range(n)]
        if len(dims) == 2:
            out[name] = [vals[r * dims[1]:(r + 1) * dims[1]] for r in range(dims[0])]
        else:
            out[name] = vals if dims else vals[0]
    return out


def poke(gb, **kw):
    """Fields of the game's state, between two whole frames: scalars as ints, byte arrays (up, fshown) as lists."""
    from conftest import logic_paused
    a = gb.addr("story_scratch")
    with logic_paused(gb):
        for k, v in kw.items():
            off, n, width, dims, signed = LAYOUT[k]
            if isinstance(v, (list, tuple)):
                for i, x in enumerate(v):
                    gb.write(a + off + i, x & 0xFF)
                continue
            gb.write(a + off, v & 0xFF)
            if width == 2:
                gb.write(a + off + 1, (v >> 8) & 0xFF)


def glyph(ch):
    art_h = (ROOT / "build" / "art.h").read_text()
    return int(re.search(rf"#define TILE_GLYPH_{ch} (\d+)", art_h).group(1))


# ---- the model: the game's integer physics --------------------------------------------------------------------
ANGLES = ART["angles"]                            # 45, 52, 60, 68 degrees (the four barrel looks)
START_ANGLE = ART["start_angle"]


def top_row(c):
    return 11 - (c - FAN_FIRST) // 2


def fly(a, p):
    """-> (SHORT | CROWD | OVER, fan column 0..10 or 0, frames of flight, 1 if the shirt was falling at the hit) for angle index a, power p: the
    generator's table of the game's integer physics."""
    return tuple(ART["table"][a][p])


def path(a, p):
    """The shirt's centre (screen px) each frame of the flight at angle a, power p."""
    mx, my = ART["muzzles"][a]
    x, y = mx << 8, my << 8
    vx, vy = ART["vel"][a][p]
    out = []
    for _ in range(fly(a, p)[2]):
        x += vx
        y += vy
        vy += ART["grav"]
        out.append((x >> 8, y >> 8))
    return out


def perfect_powers(up, a):
    """The powers at angle a that catch a fan with raised hands (falling shirt, the fan or a neighbour up), given the frames `up` each fan has
    them up left, if the shirt lands while they still are."""
    out = []
    for p in range(PMAX + 1):
        k, c, n, fall = fly(a, p)
        if k == CROWD and fall and any(0 <= c + d < FAN_N and up[c + d] > n for d in (0, -1, 1)):
            out.append(p)
    return out
