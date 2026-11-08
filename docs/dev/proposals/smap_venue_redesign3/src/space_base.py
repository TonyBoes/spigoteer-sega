"""The air base made tiny, typed: a small quonset dome (28 wide, 15 tall), a slim control tower (cab 12 wide, shaft 8 wide, 30 tall) with an aerial, and a post of
fence.  Palette BASE: 0 sand, 1 steel, 2 navy, 3 ink.  Light from the top left.  Everything stands on the ground row yf (the row under its feet is the last of the piece)."""
import common as C
import kit as K

DOOR = C.G("__33333333__", "_3222222223_", "322222222223", ("322222222223", 5))
AERIAL = C.G("3_____", "3_____", "3_____", "33333_", "3_____", "3_____")


def dome(c, x, yf):
    """x = left edge; the dome spans x to x + 27, rows yf - 14 to yf"""
    y0 = yf - 14
    cx = x + 14
    hw = [7, 10, 12, 13, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14]
    C.silh(c, y0, hw, cx, lambda xx, yy, k: "1" if xx < cx + 5 else "2")
    for k in (4, 8):
        for xx in range(x + 2, cx + 4):
            if (xx % 8) < 5:
                c.px[y0 + k][xx] = "2"
    K.hl(c, yf, x, x + 28, "3")
    C.paste(c, cx - 6, yf - 7, DOOR)
    K.hl(c, y0 + 1, x + 8, x + 12, "0")
    K.hl(c, y0 + 2, x + 4, x + 7, "0")


def tower(c, x, yf):
    """x = left edge of the shaft (8 wide); the cab is 12 wide, starts 2 px to the left of the shaft"""
    top = yf - 30
    K.box(c, x - 2, top, x + 10, top + 7, "3", "1")
    K.hl(c, top + 2, x - 1, x + 9, "0")
    K.hl(c, top + 3, x - 1, x + 9, "2")
    K.hl(c, top + 4, x - 1, x + 9, "2")
    K.rect(c, x, top + 7, x + 8, yf + 1, "1")
    K.vl(c, x, top + 7, yf + 1, "3")
    K.vl(c, x + 7, top + 7, yf + 1, "3")
    K.rect(c, x + 4, top + 8, x + 7, yf, "2")
    for y in range(top + 10, yf - 2, 8):
        K.hl(c, y, x + 1, x + 4, "2")
    K.hl(c, yf, x, x + 8, "3")
    K.vl(c, x + 4, top - 8, top, "3")
    K.hl(c, top - 5, x + 2, x + 7, "3")
