# The spigot pours (owner 2026-10-15: "the spigots should pour out the drink when the bartender is filling a glass").
# tools/gen_art.py pour_stream bakes a 2 px stream into each venue's three filling frames of the glass held under the spout
# (drink frames 2-4) and a hanging bead into the full frame (5): no OAM entry, no tile, no code. The tests check the art
# against the approved sources (the stream sits under the spout, in empty pixels, in drink colours), then the running game
# on both models: the stream shows only while A fills the glass, in the colour of that venue's drink, mirrored with the
# glass on an R bar, and the sprites per line stay within 10.
import re

import pytest
from conftest import GAME, LAYOUT, ROOT, THEMES, VENUES, title_level
from test_lift import oam_lines

pytestmark = pytest.mark.timeout(240)

VDIR = ROOT / "assets" / "approved" / "venues"
OAM_FILL, FILL_FRAMES = GAME["OAM_FILL"], GAME["FILL_FRAMES"]
CI = {".": 0, "-": 1, "+": 2, "#": 3}
FLIP = 0x20


def art_frames(t):
    """The venue's approved drink frames 2..5 (the filling glass: empty, a third, two thirds, full) as rows of characters."""
    txt = (VDIR / f"{t}_drink.txt").read_text()
    out = []
    for b in re.split(r"\n\s*\n", txt.strip()):
        rows = [r.strip() for r in b.splitlines() if r.strip() and not r.startswith((";", "//"))]
        if rows:
            out.append(rows)
    return out[2:6]


def built_frames(t):
    """The same four frames as built (the venue's OBJ tile bytes in build/venues.json): 16 rows of 8 colour indexes."""
    data = VENUES["venues"][t]["drink"]
    frames = []
    for f in range(2, 6):
        rows = [[0] * 8 for _ in range(16)]
        for half in range(2):                       # a frame is two tiles: top, low
            base = (f * 2 + half) * 16
            for y in range(8):
                lo, hi = data[base + 2 * y], data[base + 2 * y + 1]
                for x in range(8):
                    rows[half * 8 + y][x] = ((lo >> (7 - x)) & 1) | (((hi >> (7 - x)) & 1) << 1)
        frames.append(rows)
    return frames


def stream_pixels(t, k):
    """[(row, col)] of frame k's pixels that the stream added to the approved art."""
    built, orig = built_frames(t)[k], art_frames(t)[k]
    return [(r, c) for r in range(16) for c in range(8) if built[r][c] != CI[orig[r][c]]]


def nozzle(t):
    """The spout's lowest run in the bar art: its screen columns (x 136-143)."""
    bar = [r for r in (VDIR / f"{t}_bar.txt").read_text().splitlines() if r.strip() and not r.startswith((";", "//"))]
    for y in range(15, -1, -1):
        xs = [x for x in range(136, 144) if bar[y][x] != "."]
        if xs:
            return xs


@pytest.mark.parametrize("t", THEMES)
def test_stream_art_sits_under_the_spout(t):
    xs = nozzle(t)
    centre = (xs[0] + xs[-1]) / 2 - 136
    built = built_frames(t)
    for k in range(3):                              # empty, a third, two thirds: a continuous stream, 2 columns wide
        d = stream_pixels(t, k)
        cols = {c for _, c in d}
        assert len(cols) == 2 and abs(sum(cols) / 2 - centre) <= 1.5, (t, k, cols, centre)
        assert min(r for r, _ in d) <= 5 and len(d) >= 3, (t, k, d)
        assert all(art_frames(t)[k][r][c] == "." and built[k][r][c] in (1, 2) for r, c in d), "empty pixels only, drink colours"
    assert len(stream_pixels(t, 3)) <= 1, "the full glass: at most the hanging bead"
    assert len({tuple(map(tuple, b)) for b in built[:3]}) == 3, "the three filling frames differ (the flow animates)"


def start(gb, lv, dirs=None):
    """Level lv of the LEVEL harness, bartender idle at the tap of bar 0, nobody walking in."""
    if dirs is not None:
        gb.write("level_dirs", dirs)
    title_level(gb, lv)
    gb.run(40)
    gb.write("tip_chance", 0)
    gb.write("intro_timer", 255)
    gb.run(30)
    assert gb.mem("bar") == 0 and gb.mem("bartender_x") == gb.mem("tap_now") and gb.mem("fill_timer") == 0


def px(gb, o, r, c):
    """The screen pixel under the fill sprite's art pixel (row r, col c), honouring its X flip."""
    x = o["x"] - 8 + (7 - c if o["flags"] & FLIP else c)
    return gb.image().convert("RGB").getpixel((x, o["y"] - 16 + r))


def beer_colour(gb, t):
    """The venue's drink colour, read off the full glass (the sprite must be at stage 3)."""
    assert gb.mem("fill_stage") == 3
    full = built_frames(t)[3]
    r, c = next((r, c) for r in range(16) for c in range(8) if full[r][c] == 2)
    return px(gb, gb.oam()[OAM_FILL], r, c)


def stream_beer_site(t, k=0):
    """A stream pixel of frame k drawn in the drink colour (index 2), from the middle of the stream."""
    d = [(r, c) for r, c in stream_pixels(t, k) if built_frames(t)[k][r][c] == 2]
    return d[len(d) // 2]


@pytest.mark.parametrize("lv", range(1, 11))
def test_stream_shows_only_while_pouring_in_the_drinks_colour(boot, lv):
    t = THEMES[lv - 1]
    start(boot, lv)
    assert boot.oam()[OAM_FILL]["y"] == 0, "A not held: no glass, no stream"
    boot.hold("a")
    boot.run(3)
    assert boot.mem("fill_timer") and boot.mem("fill_stage") == 0
    o = boot.oam()[OAM_FILL]
    assert o["y"], "the filling glass is drawn"
    r, c = stream_beer_site(t)
    got = px(boot, o, r, c)
    boot.run(FILL_FRAMES)                           # the glass is full: the stream has stopped
    beer = beer_colour(boot, t)
    assert got == beer, f"{t}: the stream is the drink's colour {beer}, not {got}"
    boot.release("a")
    boot.run(2)
    assert boot.mem("fill_timer") == 0 and boot.oam()[OAM_FILL]["y"] == 0, "released: the glass, and its stream, are gone"


def test_stream_is_mirrored_on_an_r_bar(boot):
    t = THEMES[0]
    start(boot, 1, dirs=0x1)                        # bar 0 runs the other way
    assert boot.mem("bar_dirs") & 1
    boot.hold("a")
    boot.run(3)
    o = boot.oam()[OAM_FILL]
    assert o["flags"] & FLIP, "an R bar's glass is flipped, and the baked stream with it"
    r, c = stream_beer_site(t)
    got = px(boot, o, r, c)
    boot.run(FILL_FRAMES)
    assert got == beer_colour(boot, t)


def test_sprites_per_line_unchanged_while_pouring(boot):
    start(boot, 10)
    boot.hold("a")
    worst = 0
    for _ in range(60):
        boot.run(1)
        worst = max(worst, max(oam_lines(boot)))
    assert worst <= GAME["LINE_OBJ_MAX"]
