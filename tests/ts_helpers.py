# T-Shirt Cannon (src/ts.c): what tests/test_mg_tshirt.py needs to read and model: the game's state in the mg union (the offsets are
# parsed from struct ts_state in src/mg.h, so the header stays the one source), the art / physics numbers (build/ts.json, from
# tools/gen_ts.py and tools/cannon_table.py) and a Python model of the flight and the wave.
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
ANGLES = ART["angles"]
FAN_FIRST, FAN_N = 9, 11
SHOTS = 12


def ts_define(name):
    return int(re.search(rf"#define {name}\s+\(?(\d+)", TS_C).group(1))


def _layout():
    """struct ts_state's fields: {name: (offset, elements, width, dims)}, and its size."""
    body = re.search(r"struct ts_state \{(.*?)\n\};", MG_H, re.S).group(1)
    out, off = {}, 0
    for line in body.splitlines():
        line = line.split("//")[0].strip()
        if not line:
            continue
        m = re.match(r"(uint8_t|uint16_t|int8_t|int16_t)\s+(.*);", line)
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
    """Scalar fields of the game's state, between two whole frames."""
    from conftest import logic_paused
    a = gb.addr("story_scratch")
    with logic_paused(gb):
        for k, v in kw.items():
            off, n, width, dims, signed = LAYOUT[k]
            gb.write(a + off, v & 0xFF)
            if width == 2:
                gb.write(a + off + 1, (v >> 8) & 0xFF)


def glyph(ch):
    art_h = (ROOT / "build" / "art.h").read_text()
    return int(re.search(rf"#define TILE_GLYPH_{ch} (\d+)", art_h).group(1))


# ---- the model: the game's integer physics --------------------------------------------------------------------
def look(a):
    """Barrel look of angle index a (0..10)."""
    return 0 if a <= 2 else 1 if a <= 5 else 2 if a <= 8 else 3


def top_row(c):
    return 11 - (c - FAN_FIRST) // 2


def fly(a, k):
    """-> (fan index 0..10 or None, frames) for angle index a and wind k, the game's integer physics."""
    mx, my = ART["muzzle"][look(a)]
    x, y = mx << 8, my << 8
    vx, vy = ART["vel"][a]
    for t in range(1, 400):
        x += vx
        y += vy
        vy += ART["grav"]
        vx += k
        c = (x >> 8) >> 3
        if FAN_FIRST <= c < FAN_FIRST + FAN_N:
            top = top_row(c) * 8
            if top <= (y >> 8) < top + 16:
                return c - FAN_FIRST, t
        if (x >> 8) >= ART["out_x"] or (y >> 8) >= ART["land_y"]:
            return None, t
    return None, 400


def path(a, k):
    """The shirt's centre (screen px) each frame of the flight."""
    mx, my = ART["muzzle"][look(a)]
    x, y = mx << 8, my << 8
    vx, vy = ART["vel"][a]
    out = []
    for t in range(1, 400):
        x += vx
        y += vy
        vy += ART["grav"]
        vx += k
        out.append((x >> 8, y >> 8))
        n = fly_end(x, y)
        if n:
            break
    return out


def fly_end(x, y):
    c = (x >> 8) >> 3
    if FAN_FIRST <= c < FAN_FIRST + FAN_N:
        top = top_row(c) * 8
        if top <= (y >> 8) < top + 16:
            return True
    return (x >> 8) >= ART["out_x"] or (y >> 8) >= ART["land_y"]


def wave_interval(num):
    return 20 if num <= 4 else 16 if num <= 8 else 12


def points(i, wave):
    """Points of a catch in fan i with the wave centred on `wave`."""
    if i is None:
        return 0
    if wave - 1 <= i <= wave + 1:
        return 300
    if i == wave - 2 or i == wave + 2:
        return 100
    return 0
