"""Sal at full size, 16 x 24, as the in-game sprite (assets/art/bartender.txt): '.' clear, '-' light (OBJ colour 1), '+' skin (2), '#' dark (3).
DOWN is the game's own idle / walk1 / walk2 frames, read from the file, unchanged.
The game has no side or back view, so these six are NEW, drawn by hand for the map (right-facing side, and the back): stand and two steps each.
LEFT is the right-facing side drawn with the hardware's horizontal flip (OAM x-flip, no extra tiles)."""
from salsrc import frames

_g = frames()
DOWN = {"stand": _g[0], "step1": _g[1], "step2": _g[2]}

# the head and the neck of the right-facing view, then the torso and legs per phase
SIDE_HEAD = [
    "....#######.....",
    "...#########....",
    "...####++###....",
    "...###+++++#....",
    "...##++-#++++...",
    "...##+++++++#+..",
    "...###+#####....",
    "....########....",
    ".....+++++......",
    "......+++.......",
]
SIDE_TORSO_STAND = [
    "....#-#####.....",
    "...##-##--##....",
    "...#--#---##....",
    "...#-##--###....",
    "...#-#---###....",
    "...#-#######....",
    "...++######+....",
    "....#-----#.....",
    "....########....",
    "....########....",
]
SIDE_LEGS = {
    "stand": ["....###.###.....", "....###.###.....", "....###.###.....", "....####.####..."],
    "step1": ["...####.####....", "..###.....###...", "..###......###..", ".####......#####"],
    "step2": ["....#######.....", ".....#####......", ".....#####......", "....#########..."],
}
# arms: the near arm swings opposite to the forward leg: step1 forward arm back, step2 forward arm forward
SIDE_ARM = {
    "stand": {},
    "step1": {11: "...#-#--#-#.....", 12: "...#-##-#-#.....", 16: "..++######......"},
    "step2": {11: "...##-##--##+...", 12: "...#--#---##++..", 16: "...++######.++.."},
}

BACK_HEAD = [
    "...########.....",
    "....########....",
    "....########....",
    "....########....",
    "...+########+...",
    "...+########+...",
    "....########....",
    "....########....",
    "....##++++##....",
    ".....#----#.....",
]
BACK_TORSO = [
    "...##########...",
    "..#-#######-#...",
    "..#-###--###-#..",
    "..#-###--###-#..",
    "..#-########-#..",
    "..#-########-#..",
    "..++########++..",
    "..###------###..",
    "....########....",
    "....########....",
]
BACK_LEGS = {
    "stand": ["....###..###....", "....###..###....", "....###..###....", "...####..####..."],
    "step1": ["....###..###....", "....###..###....", "...####..###....", ".........####..."],
    "step2": ["....###..###....", "....###..###....", "....###..####...", "...####........."],
}
BACK_ARM = {"stand": {}, "step1": {16: "..+##########+.."}, "step2": {16: "..+##########+.."}}


def side(phase):
    rows = SIDE_HEAD + list(SIDE_TORSO_STAND)
    for y, r in SIDE_ARM[phase].items():
        rows[y] = r
    rows += SIDE_LEGS[phase]
    assert len(rows) == 24 and all(len(r) == 16 for r in rows), [len(r) for r in rows]
    return rows


def back(phase):
    rows = BACK_HEAD + list(BACK_TORSO)
    for y, r in BACK_ARM[phase].items():
        rows[y] = r
    rows += BACK_LEGS[phase]
    assert len(rows) == 24 and all(len(r) == 16 for r in rows)
    return rows


SIDE = {p: side(p) for p in ("stand", "step1", "step2")}
BACK = {p: back(p) for p in ("stand", "step1", "step2")}
POSES = {"D": DOWN, "R": SIDE, "L": SIDE, "U": BACK}
