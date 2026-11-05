"""Sal at full size, 16 x 24, exactly the in-game sprite (assets/art/bartender.txt): '.' clear, '-' light (OBJ colour 1), '+' skin (2), '#' dark (3).
Round 3: he always faces the camera. Every direction uses the game's own front frames, idle / walk1 / walk2, read from the file, unchanged.
No side or back view, no flip, no new art."""
from salsrc import frames

_g = frames()
DOWN = {"stand": _g[0], "step1": _g[1], "step2": _g[2]}
POSES = {"D": DOWN, "R": DOWN, "L": DOWN, "U": DOWN}
