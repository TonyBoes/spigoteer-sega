"""Zen garden PROPOSAL (round 5): a raked gravel bed 32 x 16 px (4 x 2 cells) laid over the map at cells (36..39, 58..59), east of the blossom tree.  Applied only by overlay.apply() when
SMAP_TEA_GARDEN=1; scen_A5 and the import's scenery are not edited (any scenery cell in the box is simply overwritten in the scratch world).
Palette tea@g (the tea house's: 0 ground, 1 cream gravel, 2 brown, 3 ink).  Light from the top left.
Typed by hand: the border as run rows, the gravel field as rows + typed coordinate lists for the rake lines and the rings round the rocks, three typed rocks."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "tools" / "smap_world"))
from art import R  # noqa: E402

CELL = (36, 58)
W, H = 32, 16

# border: ink outline, a 1 px brown curb inside it, rounded corners
BORDER_TOP = ["0:2 3:28 0:2", "0:1 3:1 2:28 3:1 0:1"]
BORDER_SIDE = "3:1 2:1 {} 2:1 3:1"
BORDER_BOT = ["0:1 3:1 2:28 3:1 0:1", "0:2 3:28 0:2"]

ROCK1 = ["..3333..", ".312223.", "31122223", "32222223", ".322223.", "..3333.."]       # at interior (4, 3)
ROCK2 = [".3333.", "312223", "322223", ".3333."]                                          # at interior (19, 4)
ROCK3 = [".33.", "3223"]                                                                  # at interior (14, 5)
RING1 = [(3, 2), (12, 2), (3, 9), (12, 9)] + [(2, y) for y in range(3, 9)] + [(13, y) for y in range(3, 9)]
RING2 = [(x, 2) for x in range(19, 25)] + [(x, 9) for x in range(19, 25)] + [(18, 3), (25, 3), (18, 8), (25, 8)] + [(17, y) for y in range(4, 8)] + [(26, y) for y in range(4, 8)]
LINES = [(x, 1) for x in range(0, 17)] + [(x, 10) for x in range(0, 17)] + \
        [(x, y) for y in (4, 7) for x in list(range(0, 3)) + list(range(13, 18)) + [26, 27]]


def interior():
    g = [["1"] * 28 for _ in range(12)]
    for x, y in LINES + RING1 + RING2:
        g[y][x] = "0"
    for rock, (ox, oy) in ((ROCK1, (4, 3)), (ROCK2, (19, 4)), (ROCK3, (14, 5))):
        for j, row in enumerate(rock):
            for i, ch in enumerate(row):
                if ch != ".":
                    g[oy + j][ox + i] = ch
    return ["".join(r) for r in g]


def rows():
    out = [R(s, W) for s in BORDER_TOP]
    for r in interior():
        out.append(R(BORDER_SIDE.format("".join(f"{c}:1 " for c in r).strip()), W))
    out += [R(s, W) for s in BORDER_BOT]
    assert len(out) == H and all(len(r) == W for r in out)
    return out


def apply(M):
    """overwrite the box in both worlds (Color and DMG pixels, Color palette tea@g)"""
    rs = rows()
    for w in (M.W.WORLD, M.W.WORLD_DMG):
        for j, r in enumerate(rs):
            for i, ch in enumerate(r):
                w.px[CELL[1] * 8 + j][CELL[0] * 8 + i] = int(ch)
    for cy in range(CELL[1], CELL[1] + 2):
        for cx in range(CELL[0], CELL[0] + 4):
            M.W.WORLD.pal[cy][cx] = "tea@g"
            M.W.WORLD_DMG.pal[cy][cx] = "tea@g"


if __name__ == "__main__":
    for r in rows():
        print("".join(r).replace("0", "."))
