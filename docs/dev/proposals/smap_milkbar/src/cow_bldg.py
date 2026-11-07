"""Milk bar round 4h (owner, after Q106): "fix the doors on the bar to fit more in the building. Also--do the windows need to be pink?"
restyle(base, style) redraws the body below the MILK BAR board (x 33..94, y 40..55 of the 96 x 72 piece) by hand: the doors sit inside the wall (a chrome
wall strip each side, an ink frame, a chrome head, two leaves split by a 1 px ink line, handles, an ink threshold) and the windows are not pink.
Palette COW: 0 meadow, 1 chrome, 2 pink (the board's stripe and the trim row y 41 only), 3 ink.
Style 'A': dark glass (ink with a chrome diagonal glint, chrome rims).  Style 'B': light glass (index 0, the lightest on both machines, with ink frame and a chrome glint)."""

# one window, 8 wide x 8 high (period 8), y 42..49: A has its mullion in column 7 (chrome), B in column 0 (ink)
PANE_A = ["33333333", "11111111", "33333331", "33133331", "33313331", "33331331", "33333331", "11111111"]
PANE_B = ["33333333", "30000000", "30100000", "30010000", "30001000", "30000000", "30000000", "33333333"]
WIN_X0, WIN_X1 = 36, 76                         # five panes, x 36..75
DOOR_X = 79                                      # the door's frame, 15 wide: x 79..93


def door_rows(glass, glint, handle):
    """y 42..55 of the door, 15 columns: c0 ink frame, c1 chrome jamb, c2..5 glass, c6 chrome stile, c7 ink split, c8 chrome stile, c9..12 glass, c13 jamb, c14 ink"""
    rail = "3" + "1" * 6 + "3" + "1" * 6 + "3"
    out = ["3" * 15, rail]                                   # y 42 ink frame top (level with the window tops), y 43 chrome head
    for j in range(5):                                       # y 44..48 glass: a 2 px glint on each leaf, a 2 px handle low by the stile
        gl, gr = list(glass * 4), list(glass * 4)
        if j in (0, 1):
            gl[j] = glint
            gr[j + 1] = glint
        if j in (3, 4):
            gl[3] = handle
            gr[0] = handle
        out.append("31" + "".join(gl) + "1" + "3" + "1" + "".join(gr) + "13")
    out += [rail, rail, "3" * 15]                            # y 49, 50 chrome rail, y 51 ink: the same line as under the windows
    out += [rail] * 3                                        # y 52..54 chrome panel
    out.append("3" * 15)                                     # y 55 threshold
    assert len(out) == 14 and all(len(r) == 15 for r in out), [len(r) for r in out]
    return out


def restyle(base, style):
    px = base.px
    pane = PANE_A if style == 'A' else PANE_B
    for y in range(42, 56):                                  # the wall: chrome, ink at both edges
        for x in range(33, 95):
            px[y][x] = "1"
    for x in range(32, 95):                                  # the pink trim row stays; y 40 ink
        px[40][x] = "3"
        px[41][x] = "2"
    for x in range(WIN_X0, WIN_X1):
        for j in range(8):
            px[42 + j][x] = pane[j][(x - WIN_X0) % 8]
        px[50][x] = "1"
        px[51][x] = "3"
    if style == 'B':
        for j in range(8):
            px[42 + j][WIN_X1] = "3"                         # the closing ink edge of the last pane
    for x in range(32, 95):                                  # the base band under windows and door
        px[52][x] = "3" if x < DOOR_X else "1"
        px[53][x] = "1"
        px[54][x] = "1"
        px[55][x] = ("3" if (x % 8) < 4 else "1") if x < DOOR_X else "1"
    for y in range(42, 56):
        px[y][32] = "3"
        px[y][95] = "3"
    glass, glint, handle = ("3", "1", "1") if style == 'A' else ("0", "1", "3")
    for j, r in enumerate(door_rows(glass, glint, handle)):
        for i, ch in enumerate(r):
            px[42 + j][DOOR_X + i] = ch
    return base
