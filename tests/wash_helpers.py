"""The show stage's wash (src/lights.c) as the tests see it: the tint table read from the source, and the colours the stage can wear while a show plays."""
import re

from conftest import ROOT, venue as venue_art

SRC = (ROOT / "src" / "lights.c").read_text()
TINTS = [[int(x) for x in m.groups()] for m in re.finditer(r"\{\s*(\d+),\s*(\d+),\s*(\d+)\s*\},\s*//", SRC)]
FADE = int(re.search(r"#define LT_FADE\s+(\d+)", SRC).group(1))
BEAT = 12
STEP = BEAT * int(re.search(r"#define LT_BEATS\s+(\d+)", SRC).group(1))
SHOW_FRAMES = 704
BLEND = int(re.search(r"#define LT_BLEND\s+(\d+)", SRC).group(1))   # frames a tint takes to fade into the next (lights.c)


def chan(c, k, lvl):
    return (c * (32 - (((32 - k) * lvl) >> 4))) >> 5


def dim(w, tint, lvl):
    t = TINTS[tint]
    return chan(w & 31, t[0], lvl) | chan((w >> 5) & 31, t[1], lvl) << 5 | chan((w >> 10) & 31, t[2], lvl) << 10


def tint_at(el, left):
    """The tint's three factors (32nds) `el` frames into the show, as lights_frame builds them: the step's tint, or part way from the last one's during its first BLEND frames (the first step fades in from the lit stage instead)."""
    n = ((el >> 3) * 43) >> 7
    k = el - 24 * n if n else BLEND
    tn = TINTS[n & 3]
    if k >= BLEND:
        return tn
    tp = TINTS[(n - 1) & 3]
    if left > FADE:
        k = max(k if k & 1 else k - 1, 0)       # (a blend alone builds on its odd frames only, the even ones show the last build; in the last FADE frames it builds every frame)
    return [(tp[i] * (BLEND - k) + tn[i] * k) >> 4 for i in range(3)]


def dim_el(w, el, left):
    """What the wash makes of the lit colour `w` `el` frames into a show with `left` frames to go (fades and blends together)."""
    lvl = min(FADE, el, FADE if left > FADE else left - 1)
    t = tint_at(el, left)
    return chan(w & 31, t[0], lvl) | chan((w >> 5) & 31, t[1], lvl) << 5 | chan((w >> 10) & 31, t[2], lvl) << 10


def wash_colours(group):
    """Every colour the venue's two stage palettes (BG 5 and 6) can show during a show, any tint, any fade level: a picture of the stage with the wash on is made of these (and the lit ones)."""
    pal = venue_art(group)["pal"]
    out = {dim(int(w), t, l) for p in (pal[0], pal[1]) for w in p for t in range(4) for l in range(FADE + 1)}
    for el in range(0, SHOW_FRAMES):                      # (and every blend between two tints)
        for p in (pal[0], pal[1]):
            out.update(dim_el(int(w), el, SHOW_FRAMES - el) for w in p)
    return out
