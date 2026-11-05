"""Scenery pieces for the biomes: (palette, rows); '.' is clear, so the ground tile shows through.
The pine, the round tree, the bush and the spruce are the ones drawn for the lodge, zoo and igloo vignettes (same pixels)."""
from canvas import piece
import v_lodge
import v_zoo
import v_igloo

PINE = ("grass", v_lodge.PINE)                                    # 16 x 18
ROUND = ("grass", v_zoo.CANOPY + v_zoo.TRUNK)                     # 16 x 19 (a round tree in the grass greens)
BUSH = ("grass", v_zoo.CANOPY)                                    # 16 x 10
JUNGLE_TREE = ("zoo", v_zoo.CANOPY + v_zoo.TRUNK)
JUNGLE_BUSH = ("zoo", v_zoo.CANOPY)
SPRUCE = ("igloo", v_igloo.SPRUCE)                                # 16 x 13
MOUND = ("igloo", v_igloo.DRIFT)                                  # 24 x 9

ROCK = ("saloon", piece(".:2 3:5 .:3", ".:1 3:1 1:5 3:1 .:2", ".:1 3:1 1:3 2:4 3:1", "3:1 2:8 3:1", ".:1 3:8 .:1"))        # 10 x 5
ROCK_S = ("saloon", piece(".:1 3:4 .:1", "3:1 1:2 2:2 3:1", ".:1 3:4 .:1"))                                                # 6 x 3
TUMBLE = ("saloon", piece(".:3 2:4 .:3", ".:1 2:2 .:4 2:2 .:1", "2:1 .:1 2:2 .:2 2:2 .:1 2:1", "2:1 .:2 2:1 .:2 2:1 .:2 2:1",
                          ".:1 2:2 .:4 2:2 .:1", ".:3 2:4 .:3"))                                                          # 10 x 6
_DOOR = ["3333333333", "3122222213", "3212222123", "3221221223", "3222112223", "3222112223", "3221221223", "3212222123", "3122222213", "3333333333"]
BARN = ("farm", piece(".:8 3:8 .:8", ".:5 3:1 2:12 3:1 .:5", ".:3 3:1 2:16 3:1 .:3", ".:1 3:1 2:20 3:1 .:1", "3:1 2:22 3:1", "3:24",
                       ("3:1 1:3 2:1 1:3 2:1 1:3 2:1 1:3 2:1 1:3 2:1 1:2 3:1", 4),
                       *["3:1 1:3 2:1 1:2 =" + d + " 1:2 2:1 1:3 3:1" for d in _DOOR]))                                    # 24 x 20
HAY = ("farm", piece(".:2 3:8 .:2", ".:1 3:1 1:8 3:1 .:1", "3:1 1:2 2:6 1:2 3:1", "3:1 1:2 2:6 1:2 3:1", "3:1 1:10 3:1", ".:1 3:10 .:1"))   # 12 x 6
