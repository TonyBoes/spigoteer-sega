"""quick look at the base area (cells 0 to 7) of the round 2 and round 3 mountains, with the runway variant"""
import common as C
import mountain_a as MA
import mountain_a3 as M3
import mountain_a3r as M3R


def previews():
    out = []
    for lab, m in (("r2", MA), ("r3", M3), ("r3run", M3R)):
        c = m.build()
        print(lab, 'tiles', C.tile_count(c, (0, 0, 24, 8)), 'base cells only', C.tile_count(c, (0, 0, 6, 8)))
        out.append((lab, c, 'desert', (1, 34)))
    return out
