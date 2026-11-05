"""The palette check (round 3): for every unlock state (the town only, then 1 to 10 venues in story order) and every 21 x 19 window,
the number of distinct BG palettes.  Prints the worst per state and where; the limit is 8 (CGB hardware)."""
import world2 as W

CW, CH = W.CW, W.CH


def worst(w):
    best, at, allw = 0, None, []
    for y0 in range(CH - 18):
        for x0 in range(CW - 20):
            s = {w.pal[y][x] for y in range(y0, y0 + 19) for x in range(x0, x0 + 21)}
            allw.append(len(s))
            if len(s) > best:
                best, at = len(s), (x0, y0, sorted(s))
    return best, at, allw


if __name__ == "__main__":
    top = 0
    for p in range(0, 11):
        rev = {"town"} | set(W.ORDER[:p])
        w = W.with_fog(W.WORLD, rev) if p < 10 else W.WORLD
        b, at, allw = worst(w)
        top = max(top, b)
        print(f"{p:2d} venues open: worst window {b} palettes at cell {at[:2]}; windows over 8: {sum(1 for n in allw if n > 8)}   {at[2] if b > 8 else ''}")
    print("worst of all states:", top)
