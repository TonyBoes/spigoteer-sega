"""Typing helpers for hand-drawn grids (round 2).

A row is typed as a run list:  "0:6 3:1 (1:3 2:1)*3 =3013"
    c:n          n pixels of colour index c
    (...)*n      the group repeated n times (not nested)
    =digits      those pixels exactly as typed
Every row must add up to the picture's width (checked).  Nothing here decides a pixel: it only saves typing.
"""
import re

_GROUP = re.compile(r"\(([^()]*)\)\*(\d+)")


def _expand(spec):
    spec = _GROUP.sub(lambda m: " ".join([m.group(1)] * int(m.group(2))), spec)
    out = []
    for tok in spec.split():
        if tok.startswith("="):
            out.append(tok[1:])
        else:
            c, n = tok.split(":")
            out.append(c * int(n))
    return "".join(out)


def R(spec, w=None):
    s = _expand(spec)
    if w is not None:
        assert len(s) == w, f"row is {len(s)} wide, wanted {w}: {spec}"
    return s


class Pic:
    """rows of equal width, a palette key, and a name; cut into cells by the world builder"""

    def __init__(self, name, pal, w):
        self.name, self.pal, self.w, self.rows = name, pal, w, []

    def add(self, spec, n=1):
        r = R(spec, self.w)
        self.rows += [r] * n
        return self

    def raw(self, row):
        assert len(row) == self.w, f"{self.name}: raw row {len(row)} wide, wanted {self.w}: {row}"
        self.rows.append(row)
        return self

    def done(self, h=None):
        assert len(self.rows) % 8 == 0 and self.w % 8 == 0, f"{self.name}: {self.w}x{len(self.rows)} is not whole cells"
        if h is not None:
            assert len(self.rows) == h, f"{self.name}: {len(self.rows)} rows, wanted {h}"
        return self
