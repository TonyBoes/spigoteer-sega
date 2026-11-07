"""Hand-placed strata on the 8 px grid.  rows = {y: string}, one letter per cell from cell x0 // 8 on:
a = dash over lit rock in cell columns 0-4, b = columns 3-7, c = columns 1-6, S = a short dark mark on shaded rock (columns 2-4), . = none.
Only rock (1 / 2) is touched, never ink.  The letters are my choice, cell by cell."""


def strata(c, rows, x0=0):
    for y, s in rows.items():
        for k, ch in enumerate(s):
            cx = x0 // 8 + k
            for i in range(8):
                x = cx * 8 + i
                if x >= c.w:
                    continue
                px = c.px[y][x]
                if ch == "a" and i < 5 and px == "1":
                    c.px[y][x] = "2"
                elif ch == "b" and i >= 3 and px == "1":
                    c.px[y][x] = "2"
                elif ch == "c" and 1 <= i <= 6 and px == "1":
                    c.px[y][x] = "2"
                elif ch == "S" and 2 <= i <= 4 and px == "2":
                    c.px[y][x] = "3"
