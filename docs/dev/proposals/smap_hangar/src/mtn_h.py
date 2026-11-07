"""Round 4 mountain builds: round 3's mountain, tower, mast and dish exactly (base3.tower, mountain_a.mountain); only the hangar differs, with or without the strip."""
import sys

sys.path.insert(0, '/workspace/.claude/worktrees/agent-a958d884767ee8afe/docs/dev/proposals/smap_hangar/src')
sys.path.insert(1, '/workspace/.claude/worktrees/agent-a958d884767ee8afe/docs/dev/proposals/smap_venue_redesign3/src')
import base3 as B  # noqa: E402
import common as C  # noqa: E402
import hangar_h as H  # noqa: E402
import mountain_a as MA  # noqa: E402
from canvas import Canvas  # noqa: E402

W, HT = 200, 72
BIOME, AT, REGION = 'desert', (1, 34), (0, 0, 24, 8)


def build(which, runway=False):
    c = Canvas("mountain_" + which, "saloon", W, HT)
    c.palrect(0, 0, 56, 72, "base")
    MA.mountain(c)
    yf = MA.YF
    if which == 'r3':
        B.hangar(c, 0, yf)
    elif which == 'h1':
        H.hangar1(c, 0, yf)
    else:
        H.hangar2(c, 0, yf)
    B.tower(c, 38, yf)
    if runway:
        H.strip(c)
    return c
