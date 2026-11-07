"""Typing shorthands for the round-2 venue proposals. They save typing runs; they decide nothing: every call is one run or one block of rows I chose
(rect = the same typed run repeated over rows; hl/vl = one typed run).  Letters are my 5-row font."""
import common as C

FONT = {"M": ["10001", "11011", "10101", "10001", "10001"], "I": ["111", "010", "010", "010", "111"], "L": ["100", "100", "100", "100", "111"],
        "K": ["101", "101", "110", "101", "101"], "B": ["110", "101", "110", "101", "110"], "A": ["010", "101", "111", "101", "101"],
        "R": ["110", "101", "110", "101", "101"], "Z": ["111", "001", "010", "100", "111"], "O": ["111", "101", "101", "101", "111"],
        "P": ["110", "101", "110", "100", "100"], "S": ["011", "100", "010", "001", "110"], "D": ["110", "101", "101", "101", "110"],
        "U": ["101", "101", "101", "101", "111"], "T": ["111", "010", "010", "010", "010"], "H": ["101", "101", "111", "101", "101"],
        "E": ["111", "100", "110", "100", "111"], "N": ["101", "111", "111", "111", "101"], "G": ["011", "100", "101", "101", "011"],
        "F": ["111", "100", "110", "100", "100"], "Y": ["101", "101", "010", "010", "010"], "C": ["011", "100", "100", "100", "011"],
        "W": ["10001", "10001", "10101", "11011", "10001"], "V": ["101", "101", "101", "101", "010"], "J": ["001", "001", "001", "101", "010"]}


def rect(c, x0, y0, x1, y1, v):
    """x1, y1 exclusive"""
    for y in range(y0, y1):
        for x in range(x0, x1):
            c.px[y][x] = v


def hl(c, y, x0, x1, v):
    for x in range(x0, x1):
        c.px[y][x] = v


def vl(c, x, y0, y1, v):
    for y in range(y0, y1):
        c.px[y][x] = v


def box(c, x0, y0, x1, y1, edge, fill):
    rect(c, x0, y0, x1, y1, fill)
    hl(c, y0, x0, x1, edge)
    hl(c, y1 - 1, x0, x1, edge)
    vl(c, x0, y0, y1, edge)
    vl(c, x1 - 1, y0, y1, edge)


def text(c, x, y, s, v, gap=1, space=3):
    for ch in s:
        if ch == " ":
            x += space
            continue
        for j, r in enumerate(FONT[ch]):
            for i, b in enumerate(r):
                if b == "1":
                    c.px[y + j][x + i] = v
        x += len(FONT[ch][0]) + gap
    return x


def width(s, gap=1, space=3):
    w = 0
    for ch in s:
        w += space if ch == " " else len(FONT[ch][0]) + gap
    return w - gap


def grid(c, x, y, rows):
    """paste typed rows ('_' or '.' transparent)"""
    C.paste(c, x, y, rows)
