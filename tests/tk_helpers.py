# Taiko Pour (src/tk.c): what tests/test_mg_taiko.py needs to read and model: the game's state in the mg union (the offsets are
# parsed from struct tk_state in src/mg.h, so the header stays the one source), the chart (build/tk.json, from
# tools/taiko_chart.py) and a bot that plays it.
import json
import re

from conftest import ROOT

MG_H = (ROOT / "src" / "mg.h").read_text()
TK_C = (ROOT / "src" / "tk.c").read_text()
TK_ART_H = (ROOT / "build" / "tk_art.h").read_text()
ART = json.loads((ROOT / "build" / "tk.json").read_text())
CHART = [tuple(n) for n in ART["chart"]]          # (hit time in music frames, lane 0 A / 1 B)
TK_BG = 77 + 48                                   # MG_GAME_BG: after the medal icon
TK_OBJ = 56                                       # OBJ_MUG
MG_TAIKO = 7
TEAHOUSE = 7                                      # the venue (chapter 8)


def tk_define(name):
    return int(re.search(rf"#define {name}\s+\(?(\d+)", TK_C).group(1))


def mg_define(name):
    return int(re.search(rf"#define {name}\s+\(?(\d+)", MG_H).group(1))


def art_define(name):
    return int(re.search(rf"#define {name} (\d+)", TK_ART_H).group(1))


def _layout():
    """struct tk_state's fields: {name: (offset, elements, width, dims)}, and its size."""
    body = re.search(r"struct tk_state \{(.*?)\n\};", MG_H, re.S).group(1)
    mac = {m[0]: int(m[1]) for m in re.findall(r"#define (TK_\w+)\s+(\d+)", MG_H)}
    out, off = {}, 0
    for line in body.splitlines():
        line = line.split("//")[0].strip()
        if not line:
            continue
        m = re.match(r"(uint8_t|uint16_t)\s+(.*);", line)
        width = {"uint8_t": 1, "uint16_t": 2}[m[1]]
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


def tk(gb):
    """The game's state as a dict: scalars as ints, arrays as lists (2-D ones nested)."""
    b = gb.read("story_scratch", STATE_SIZE)
    out = {}
    for name, (off, n, width, dims) in LAYOUT.items():
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


def glyph(ch):
    """The HUD glyph tile of a character (build/art.h TILE_GLYPH_*)."""
    art_h = (ROOT / "build" / "art.h").read_text()
    return int(re.search(rf"#define TILE_GLYPH_{ch} (\d+)", art_h).group(1))


def lane_notes(lane):
    return [t for t, ln in CHART if ln == lane]


def perfect_score():
    """The score of a game with every note PERFECT: 300 + 10 per combo note (at most 10) a note, 500 a bowl of 8."""
    s = 0
    for i in range(1, len(CHART) + 1):
        s += 300 + 10 * min(i, 10)
        if i % 8 == 0:
            s += 500
    return s


def plan_for(chart=None, offset=0, skip=()):
    """{clock: keys}: press each note's key `offset` frames after its hit time (notes whose index is in `skip` are left)."""
    plan = {}
    for i, (t, lane) in enumerate(chart or CHART):
        if i in skip:
            continue
        plan.setdefault(t + offset, set()).add("ab"[lane])
    return plan


def run_bot(gb, step, plan, stop, limit=6000, hook=None):
    """Plays frame by frame: a key goes down for 2 frames when the state's clk + 2 is in `plan` (a key held now is read by the
    update after the one in progress, which has clock clk + 1: the press is judged at the clock `plan` names).
    step(gb, n) advances n frames (the caller's checked `frames`); stop(state) ends it; hook(state) sees each state."""
    for _ in range(limit):
        s = tk(gb)
        if hook:
            hook(s)
        if stop(s):
            return s
        keys = plan.get(s["clk"] + 2, ())
        for k in keys:
            gb.hold(k)
        if keys:
            step(gb, 2)
            for k in keys:
                gb.release(k)
        else:
            step(gb, 1)
    raise AssertionError("the stop condition was not reached")
