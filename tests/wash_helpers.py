"""The show stage's wash (src/lights.c) as the tests see it: the tint table read from the source, and the colours the stage can wear while a show plays."""
import re

from conftest import ROOT, venue as venue_art

SRC = (ROOT / "src" / "lights.c").read_text()
TINTS = [[int(x) for x in m.groups()] for m in re.finditer(r"\{\s*(\d+),\s*(\d+),\s*(\d+)\s*\},\s*//", SRC)]
FADE = int(re.search(r"#define LT_FADE\s+(\d+)", SRC).group(1))
BEAT = 12
STEP = BEAT * int(re.search(r"#define LT_BEATS\s+(\d+)", SRC).group(1))
SHOW_FRAMES = 704


def chan(c, k, lvl):
    return (c * (32 - (((32 - k) * lvl) >> 4))) >> 5


def dim(w, tint, lvl):
    t = TINTS[tint]
    return chan(w & 31, t[0], lvl) | chan((w >> 5) & 31, t[1], lvl) << 5 | chan((w >> 10) & 31, t[2], lvl) << 10


def wash_colours(group):
    """Every colour the venue's two stage palettes (BG 5 and 6) can show during a show, any tint, any fade level: a picture of the stage with the wash on is made of these (and the lit ones)."""
    pal = venue_art(group)["pal"]
    return {dim(int(w), t, l) for p in (pal[0], pal[1]) for w in p for t in range(4) for l in range(FADE + 1)}
