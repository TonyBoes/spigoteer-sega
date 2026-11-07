"""The bridges of A5, raised sides (owner: "bridges should have raised size or something, so its not like a simple rope bridge across the river and lake").
Palette 'town1' (the road's): 0 cream, 1 terracotta, 2 lilac, 3 ink.  Every tile typed by hand.

East-west deck (the lake, the stream by the pool): two cells high, 16 px.  From the top: ink outline, a lit cream cap, the parapet's face (lilac, an ink post every
4 px), the face's foot (lilac); eight rows of planks (terracotta, lilac joint every 4 px); then the near parapet: cap, face with posts, foot, ink outline.
The two end cells close the parapet with an ink end and start the deck with a lilac threshold column.  North-south deck (the mill race): the same turned,
typed separately; the left parapet on the left, the right one on the right; the end cells close the parapets with an ink row.
A 1 px shadow runs on the water along the east or south side of each deck (light from the top left): typed tiles, the bank or water tile with its first row (or first
column) in the 'deep' index (DMG dark: 24; light water: 88).

Tile sets: T B TL BL TR BR (east-west), L R Lt Rt Lb Rb (north-south)."""

T = ["33333333", "00000000", "22322232", "22222222", "11121112", "11121112", "11121112", "11121112"]
B = ["11121112", "11121112", "11121112", "11121112", "00000000", "22322232", "22222222", "33333333"]
TL = ["33333333", "30000000", "32322232", "32222222", "21121112", "21121112", "21121112", "21121112"]
BL = ["21121112", "21121112", "21121112", "21121112", "30000000", "32322232", "32222222", "33333333"]
TR = ["33333333", "00000003", "22322223", "22222223", "11121112", "11121112", "11121112", "11121112"]
BR = ["11121112", "11121112", "11121112", "11121112", "00000003", "22322223", "22222223", "33333333"]
L = ["30221111", "30221111", "30321111", "30222222", "30221111", "30221111", "30321111", "30222222"]
R = ["11110223", "11110223", "11110323", "22220223", "11110223", "11110223", "11110323", "22220223"]
Lt = ["33332222"] + L[1:]
Rt = ["22223333"] + R[1:]
Lb = L[:7] + ["33332222"]
Rb = R[:7] + ["22223333"]
TILES = {"T": T, "B": B, "TL": TL, "BL": BL, "TR": TR, "BR": BR, "L": L, "R": R, "Lt": Lt, "Rt": Rt, "Lb": Lb, "Rb": Rb}

# ---- the shadow tiles: the first row (south side of a deck) or the first column (east side) in the 'deep' index; typed rows and columns ------------------------
# dark set: land 0, rim 1, water 2, shadow 3.   light set: land 0, water 1, shadow 2.
SH_ROW = {"CSW": "00013333", "ISW": "33333333", "WF": "33333333", "BE": "33331000", "BW": "00013333"}
SH_ROW_L = {"CSW": "00002222", "ISW": "22222222", "WF": "22222222", "BE": "22220000", "BW": "00002222"}
SH_COL = {"BN": "00013333", "WF": "33333333", "BS": "33331000"}
SH_COL_L = {"BN": "00002222", "WF": "22222222", "BS": "22220000"}


def shadow_tiles(base, light):
    """new tiles {name: rows}: base is the dict of the water tiles of that set"""
    out = {}
    for n, row in (SH_ROW_L if light else SH_ROW).items():
        out[n + "_S"] = [row] + list(base[n][1:])
    for n, col in (SH_COL_L if light else SH_COL).items():
        out[n + "_V"] = ["".join([col[j]] + list(base[n][j][1:])) for j in range(8)]
    return out


# which cell takes which shadow tile (typed): the water cells south of the lake bridge and the stream bridge, the cells east of the mill race bridge
SHADOW_CELLS = {(38, 64): "CSW_S", (39, 64): "ISW_S", (40, 64): "WF_S", (41, 64): "WF_S", (42, 64): "WF_S", (43, 64): "WF_S", (44, 64): "WF_S", (45, 64): "WF_S",
                (46, 64): "WF_S", (47, 64): "BE_S", (46, 13): "BW_S", (47, 13): "BE_S", (52, 32): "BN_V", (52, 33): "WF_V", (52, 34): "BS_V"}
