"""Round 4 mountain builds: round 3's mountain, tower, mast and dish exactly (base3.tower, mountain_a.mountain); only the hangar differs, with or without the strip.
raised=True: the base (hangar, tower) stands 8 px behind the mountain's foot line, foot y 55 (round 3's runway variant did the same), which frees the last 16 rows for the
apron, the runway and the plane (round 4b)."""
import sys

sys.path.insert(0, '/workspace/.claude/worktrees/agent-a958d884767ee8afe/docs/dev/proposals/smap_hangar/src')
sys.path.insert(1, '/workspace/.claude/worktrees/agent-a958d884767ee8afe/docs/dev/proposals/smap_venue_redesign3/src')
import base3 as B  # noqa: E402
import common as C  # noqa: E402
import hangar_h as H  # noqa: E402
import mountain_a as MA  # noqa: E402
import plane_h as PL  # noqa: E402
import strip_h as SH  # noqa: E402
from canvas import Canvas  # noqa: E402

W, HT = 200, 72
BIOME, AT, REGION = 'desert', (1, 34), (0, 0, 24, 8)


def build(which, runway=False, plane=None, tone='2', raised=False):
    c = Canvas("mountain_" + which, "saloon", W, HT)
    c.palrect(0, 0, 56, 72, "base")
    MA.mountain(c)
    yf = 55 if raised else MA.YF
    if which == 'r3':
        B.hangar(c, 0, yf)
    elif which == 'h1':
        H.hangar1(c, 0, yf)
    elif which == 'h2e':                       # option 2 with an empty hangar (no plane inside)
        C.paste(c, 0, yf - 15, H.H2)
    else:
        H.hangar2(c, 0, yf)
    B.tower(c, 38, yf)
    if runway == 'c':
        import strip3_h
        strip3_h.strip3(c)
    elif runway and raised:
        SH.strip2(c, tone)
    elif runway:
        H.strip(c, tone=tone)
    if plane in ('J1', 'J2'):                   # round 4d jets: J1 fully out on the apron (x 6, y 52), J2 tail still in the doors (x 6, y 46)
        import jet_h
        C.paste(c, 6, 52 if plane == 'J1' else 46, jet_h.pose())
    elif plane in ('P1', 'P2'):                  # round 4c planes: x 8, y 46 (the tail in the slot)
        import plane2_h
        C.paste(c, 8, 46, plane2_h.pose(plane))
    elif plane:                                 # the taxiing plane, pasted over the apron and the runway (x 10, y 56)
        C.paste(c, 10 if plane == 'A' else 8, 56, PL.pose(plane))
    return c
