"""New land pieces of layout A5 on top of A4's (a4art.py: water, banks, corners, bridges, floating logs, the log pile, the placeholder boxes).
Every tile is eight strings of eight palette indices, typed by hand, DMG value first (the index is the DMG shade).

Palette 'water' (Color): 0 bank land (grass; where the river runs through the snow the same tiles take the palette 'igloo', whose index 0 is the snow),
1 foam, 2 water, 3 deep.  DMG dark water (A4): land 248, foam 168, water 88, deep 24.
DMG LIGHT water (new, the DMG data set only): land 0 (248), water 1 (168), a glint or a splash 0 (248), a rock edge 2 (88).  The foam rim has no shade
of its own there (it would be the land's), so the shore is the edge of the land, scalloped one pixel in three exactly as the dark tiles are.

Which tile goes on which water cell is the A4 lookup on the four neighbours, plus a typed rhythm for the second shore tiles and a typed dict for the falls
and the splash; the water mask itself is typed in lay_A5.py."""
from a4art import *  # noqa: F401,F403  (A4's tiles and pieces, unchanged)
import a4art
import decor

# ---- falls: two cells wide, two cells high, under the peaks; the side edges are the river bank's own (land 0, rim 1 on column 3 / 4, as BW and BE), so they continue
# into the stream and the pool pixel for pixel; foam streaks (1) fall in runs of 2 and 3 ---
FL_A = ["00012212", "00012212", "00012222", "00012122", "00012122", "00012122", "00012212", "00012222"]
FL_B = ["00012222", "00012212", "00012212", "00012222", "00012122", "00012122", "00012222", "00012222"]
FR_A = ["22121000", "22121000", "21221000", "21221000", "21221000", "22221000", "22121000", "22221000"]
FR_B = ["22221000", "21221000", "21221000", "22221000", "22121000", "22121000", "22221000", "22221000"]
# ---- the splash under the falls (two cells of the pool): foam arcs on water; every border pixel is water so that it joins flat water on all four sides ----
SPL_A = ["22222222", "22111222", "21222122", "22222222", "22222222", "22221122", "22212212", "22222222"]
SPL_B = ["22222222", "22221112", "22122212", "22222222", "22211222", "22122122", "22222222", "22222222"]
# ---- shore variants: the four banks with the rim stepping at another place (the two end columns equal the first banks', so any order joins) ---------------
BN2 = ["00000000", "00000000", "00000000", "11110011", "22221122", "22222222", "22222222", "22222222"]
BS2 = ["22222222", "22222222", "22222222", "22221122", "11110011", "00000000", "00000000", "00000000"]
BW2 = ["00012222", "00012222", "00012222", "00012222", "00001222", "00001222", "00001222", "00012222"]
BE2 = ["22221000", "22221000", "22221000", "22221000", "22210000", "22210000", "22210000", "22221000"]

# ---- the same set for DMG light water -------------------------------------------------------------------------------------------------------------------
WF_L = ["11111111"] * 8
WA_L = ["11111111", "11111111", "10011111", "11100111", "11111001", "11111111", "11111111", "11111111"]
WB_L = ["11111111", "11111111", "11111111", "11001111", "11110011", "11111111", "11111111", "11111111"]
BN_L = ["00000000", "00000000", "00000000", "00000000", "11000111", "11111111", "11111111", "11111111"]
BS_L = ["11111111", "11111111", "11111111", "11000111", "00000000", "00000000", "00000000", "00000000"]
BW_L = ["00001111", "00001111", "00000111", "00000111", "00000111", "00001111", "00001111", "00001111"]
BE_L = ["11110000", "11110000", "11100000", "11100000", "11100000", "11110000", "11110000", "11110000"]
CNW_L = ["00000000", "00000000", "00000000", "00000000", "00000001", "00000011", "00000111", "00001111"]
CNE_L = ["00000000", "00000000", "00000000", "00000000", "10000000", "11000000", "11100000", "11110000"]
CSW_L = ["00001111", "00000111", "00000011", "00000001", "00000000", "00000000", "00000000", "00000000"]
CSE_L = ["11110000", "11100000", "11000000", "10000000", "00000000", "00000000", "00000000", "00000000"]
INE_L = ["11110000", "11111000", "11111100", "11111110", "11111111", "11111111", "11111111", "11111111"]
INW_L = ["00001111", "00011111", "00111111", "01111111", "11111111", "11111111", "11111111", "11111111"]
ISE_L = ["11111111", "11111111", "11111111", "11111111", "11111110", "11111100", "11111000", "11110000"]
ISW_L = ["11111111", "11111111", "11111111", "11111111", "01111111", "00111111", "00011111", "00001111"]
BN2_L = ["00000000", "00000000", "00000000", "00000000", "11110011", "11111111", "11111111", "11111111"]
BS2_L = ["11111111", "11111111", "11111111", "11110011", "00000000", "00000000", "00000000", "00000000"]
BW2_L = ["00001111", "00001111", "00001111", "00001111", "00000111", "00000111", "00000111", "00001111"]
BE2_L = ["11110000", "11110000", "11110000", "11110000", "11100000", "11100000", "11100000", "11110000"]
FL_A_L = ["00001101", "00001101", "00001111", "00001011", "00001011", "00001011", "00001101", "00001111"]
FL_B_L = ["00001111", "00001101", "00001101", "00001111", "00001011", "00001011", "00001111", "00001111"]
FR_A_L = ["11010000", "11010000", "10110000", "10110000", "10110000", "11110000", "11010000", "11110000"]
FR_B_L = ["11110000", "10110000", "10110000", "11110000", "11010000", "11010000", "11110000", "11110000"]
SPL_A_L = ["11111111", "11000111", "10111011", "11111111", "11111111", "11110011", "11101101", "11111111"]
SPL_B_L = ["11111111", "11110001", "11011101", "11111111", "11100111", "11011011", "11111111", "11111111"]

NAMES = ["WF", "WA", "WB", "BN", "BS", "BW", "BE", "CNW", "CNE", "CSW", "CSE", "INE", "INW", "ISE", "ISW", "BN2", "BS2", "BW2", "BE2",
         "FL_A", "FL_B", "FR_A", "FR_B", "SPL_A", "SPL_B"]
DARK = {n: globals()[n] for n in NAMES}
LIGHT = {n: globals()[n + "_L"] for n in NAMES}
_BY_ID = {id(t): n for n, t in DARK.items()}

# ---- floating logs for the light water (body 0 = 248 with its grain 1, outline 3: on light water the outline carries the log) ----------------------------
LOGH_L = ["..333333333333..", ".30000000000003.", "3000010000100003", "3000000001000003", ".30000000000003.", "..333333333333.."]
LOGV_L = ["".join(LOGH_L[c][15 - r] for c in range(6)) for r in range(16)]
FLOATLOG_H_L = ("water", LOGH_L)
FLOATLOG_V_L = ("water", LOGV_L)
LIGHT_PIECE = {id(a4art.FLOATLOG_H): FLOATLOG_H_L, id(a4art.FLOATLOG_V): FLOATLOG_V_L}

# ---- the factory yard: packed earth with gravel (palette 'factory', re-tinted: 0 earth, 1 pebble and steel, 2 dark steel, 3 ink) -------------------------
# three pebble clusters of 4, 4 and 2 pixels (diagonal pairs, no 2 x 2 block), low contrast: the floor stays quiet
GRAVEL = ["00000000", "01100000", "00110000", "00000000", "00000110", "00001100", "00000000", "11000000"]
# a boulder in the snow: today's ROCK pixels (10 x 5) with the snow palette
ROCK_SNOW = ("grass", decor.ROCK[1])                      # (the boulders flanking the falls: a mossy rock on the grass bank)


def water_tile5(mask, cx, cy, W, H, dmg=False, light=False, variants=False, special=None):
    """A5: the A4 lookup, plus special cells typed by hand (falls, splash: {(x, y): name}), the second shore tiles on a typed rhythm, and the DMG light set"""
    S = LIGHT if (dmg and light) else DARK
    if special and (cx, cy) in special:
        return S[special[(cx, cy)]]
    name = _BY_ID[id(a4art.water_tile(mask, cx, cy, W, H))] if True else None
    if variants and name in ("BN", "BS", "BW", "BE") and (cx * 3 + cy * 5) % 7 in (2, 5):
        name += "2"
    return S[name]


# ---- the floating logs, redrawn (logs5.py): SMAP_LOG = old (A4's) | v1 | v2 ---------------------------------------------------------------------------
import os as _os
import logs5 as _logs5

LOGSEL = _os.environ.get("SMAP_LOG", "old")
LOG_DX, LOG_DY = (1, 1) if LOGSEL == "old" else (0, 0)         # (A4's pieces are 16 x 6 / 6 x 16 and sat one pixel in; the new ones fill their cells)
if LOGSEL in _logs5.VARIANTS:
    _h, _v = _logs5.VARIANTS[LOGSEL]
    FLOATLOG_H = ("water", _logs5.conv(_h))
    FLOATLOG_V = ("water", _logs5.conv(_v))
    FLOATLOG_H_L = ("water", _logs5.conv(_h, light=True))
    FLOATLOG_V_L = ("water", _logs5.conv(_v, light=True))
    LIGHT_PIECE = {id(FLOATLOG_H): FLOATLOG_H_L, id(FLOATLOG_V): FLOATLOG_V_L}
