"""The palette map (round 3): one fixed BG palette slot (0-7) per palette name, so that no two palettes that meet in any 21 x 19 window, in any
unlock state, share a slot.  A palette is written into its slot (8 bytes, VBlank) when the window first needs it.  Prints the table."""
import itertools

import pal
import world2 as W

CW, CH = W.CW, W.CH


def names_per_window():
    seen = set()
    for p in range(0, 11):
        v = W.with_fog(W.WORLD, {"town"} | set(W.ORDER[:p])) if p < 10 else W.WORLD
        for y0 in range(CH - 18):
            for x0 in range(CW - 20):
                seen.add(frozenset(v.pal[y][x] for y in range(y0, y0 + 19) for x in range(x0, x0 + 21)))
    return seen


def colour(groups, nodes, k=8):
    adj = {n: set() for n in nodes}
    for g in groups:
        for a, b in itertools.combinations(g, 2):
            adj[a].add(b)
            adj[b].add(a)
    order = sorted(nodes, key=lambda n: -len(adj[n]))
    slot = {}

    def go(i):
        if i == len(order):
            return True
        n = order[i]
        for s in range(k):
            if all(slot.get(m) != s for m in adj[n]):
                slot[n] = s
                if go(i + 1):
                    return True
                del slot[n]
        return False

    return slot if go(0) else None, adj


def state_groups(p):
    v = W.with_fog(W.WORLD, {"town"} | set(W.ORDER[:p])) if p < 10 else W.WORLD
    return {frozenset(v.pal[y][x] for y in range(y0, y0 + 19) for x in range(x0, x0 + 21)) for y0 in range(CH - 18) for x0 in range(CW - 20)}


if __name__ == "__main__":
    # one slot table per unlock state (the map screen is entered with the LCD off, so the table can change between states)
    for p in range(0, 11):
        groups = state_groups(p)
        nodes = sorted({n for g in groups for n in g})
        slot, adj = colour(groups, nodes)
        print(f"state {p:2d}: {len(nodes)} palettes, largest window set {max(len(g) for g in groups)}, " + ("colourable in 8 slots" if slot else "NOT colourable"))
        if slot and p in (5, 10):
            for n in sorted(slot, key=lambda n: (slot[n], n)):
                print(f"    slot {slot[n]}  {n:12s} " + " ".join("%02x%02x%02x" % tuple(c) for c in pal.get(n)))
