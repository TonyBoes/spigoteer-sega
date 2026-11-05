"""A hand-drawn picture assembled from typed rows and typed pieces.

base rows are typed with art.R (runs); pieces (windows, doors, barrels, ...) are typed grids pasted at hand-chosen x, y;
'.' inside a piece is transparent.  Nothing here fills a shape or decides a colour."""
from art import R


class Canvas:
    def __init__(self, name, pal, w, h, bg="0"):
        self.name, self.pal, self.w, self.h = name, pal, w, h
        self.px = [[bg] * w for _ in range(h)]
        self.rects = []                      # (x0, y0, x1, y1, palette) in pixels, whole cells; the default palette is `pal`

    def rows(self, y0, specs):
        """specs: list of (run spec, repeat count)"""
        y = y0
        for spec, n in specs:
            s = R(spec, self.w)
            for _ in range(n):
                assert y < self.h, f"{self.name}: row {y} is below the picture"
                self.px[y] = list(s)
                y += 1
        return y

    def row(self, y, spec):
        self.px[y] = list(R(spec, self.w))

    def paste(self, x, y, piece):
        for j, r in enumerate(piece):
            for i, c in enumerate(r):
                if c != ".":
                    X, Y = x + i, y + j
                    assert 0 <= X < self.w and 0 <= Y < self.h, f"{self.name}: piece goes off the picture at {X},{Y}"
                    self.px[Y][X] = c

    def put(self, x, y, c):
        self.px[y][x] = c

    def palrect(self, x0, y0, x1, y1, pal):
        assert x0 % 8 == 0 and y0 % 8 == 0 and x1 % 8 == 0 and y1 % 8 == 0
        self.rects.append((x0, y0, x1, y1, pal))

    def cellpals(self):
        if hasattr(self, "cellpal_grid"):
            return self.cellpal_grid
        g = [[self.pal] * (self.w // 8) for _ in range(self.h // 8)]
        for x0, y0, x1, y1, p in self.rects:
            for cy in range(y0 // 8, y1 // 8):
                for cx in range(x0 // 8, x1 // 8):
                    g[cy][cx] = p
        return g

    def out(self):
        assert self.w % 8 == 0 and self.h % 8 == 0, f"{self.name} is {self.w}x{self.h}"
        return ["".join(r) for r in self.px]


def piece(*specs, w=None):
    """a piece typed as run specs, one per row (a (spec, n) tuple repeats the row)"""
    rows = []
    for s in specs:
        if isinstance(s, tuple):
            rows += [R(s[0], w)] * s[1]
        else:
            rows.append(R(s, w))
    return rows
