# Marshmallow Drop (src/mm.c): what tests/test_mg_marshmallow.py needs to read: the game's state in the mg union (the offsets are
# parsed from struct mm_state in src/mg.h, so the header stays the one source), the art (build/mm.json, from tools/gen_mm.py)
# and a bot that plays.
import json
import re

from conftest import ROOT

MG_H = (ROOT / "src" / "mg.h").read_text()
MM_C = (ROOT / "src" / "mm.c").read_text()
MM_ART_H = (ROOT / "build" / "mm_art.h").read_text()
ART = json.loads((ROOT / "build" / "mm.json").read_text())
MM_BG = 77 + 48                                 # MG_GAME_BG: after the medal icon
MG_MARSHMALLOW = 4
IGLOO = 4                                       # the venue (chapter 5)
WIDTH = {"uint8_t": 1, "int8_t": 1, "uint16_t": 2, "int16_t": 2}


def mm_define(name):
    return int(re.search(rf"#define {name}\s+\(?(-?\d+)", MM_C).group(1))


def art_define(name):
    return int(re.search(rf"#define {name} (\d+)", MM_ART_H).group(1))


def _layout():
    """struct mm_state's fields: {name: (offset, elements, width, dims, type)}, and its size."""
    body = re.search(r"struct mm_state \{(.*?)\n\};", MG_H, re.S).group(1)
    mac = {m[0]: int(m[1]) for m in re.findall(r"#define (MM_\w+)\s+(\d+)", MG_H)}
    out, off = {}, 0
    for line in body.splitlines():
        line = line.split("//")[0].strip()
        if not line:
            continue
        m = re.match(r"(uint8_t|int8_t|uint16_t|int16_t)\s+(.*);", line)
        if m is None:                       # (the `struct xx_tune tn` at the end: the difficulty's tuning row, not read by the tests)
            continue
        for decl in m[2].split(","):
            decl = decl.strip()
            dims = [int(d) if d.isdigit() else mac[d] for d in re.findall(r"\[(\w+)\]", decl)]
            name = re.match(r"\w+", decl)[0]
            n = 1
            for d in dims:
                n *= d
            out[name] = (off, n, WIDTH[m[1]], dims, m[1])
            off += n * WIDTH[m[1]]
    return out, off


LAYOUT, STATE_SIZE = _layout()


def mm(gb):
    """The game's state as a dict: scalars as ints, arrays as lists (2-D ones nested)."""
    b = gb.read("story_scratch", STATE_SIZE)
    out = {}
    for name, (off, n, width, dims, typ) in LAYOUT.items():
        vals = [int.from_bytes(b[off + i * width:off + (i + 1) * width], "little", signed=typ.startswith("i"))
                for i in range(n)]
        if len(dims) == 2:
            out[name] = [vals[r * dims[1]:(r + 1) * dims[1]] for r in range(dims[0])]
        else:
            out[name] = vals if dims else vals[0]
    return out


def poke(gb, **kw):
    """Fields of the game's state, between two whole frames: a scalar's value, or (slot, value) for an array's element."""
    from conftest import logic_paused
    a = gb.addr("story_scratch")
    with logic_paused(gb):
        for k, v in kw.items():
            off, n, width, dims, typ = LAYOUT[k]
            if n > 1:
                slot, v = v
                off += slot * width
            v &= (1 << (8 * width)) - 1
            for i in range(width):
                gb.write(a + off + i, (v >> (8 * i)) & 0xFF)


def glyph(ch):
    """The HUD glyph tile of a character (build/art.h TILE_GLYPH_*)."""
    art_h = (ROOT / "build" / "art.h").read_text()
    return int(re.search(rf"#define TILE_GLYPH_{ch} (\d+)", art_h).group(1))
