"""Round 2: key changes (calmer day, fountain value) and compose edits. One-off patch."""
from pathlib import Path

T = Path(__file__).resolve().parent
p = T / "keys.py"
s = p.read_text()


def rep(old, new):
    global s
    assert s.count(old) == 1, old[:70]
    s = s.replace(old, new)


# night: the hall is the town's silhouette
rep('''    "B": (3, "#140c24", "wall (silhouette)"),''', '''    "B": (3, "#140c24", "wall (silhouette)"),
    "H": (3, "#140c24", "hall wall behind the fountain (silhouette)"),''')
# day
rep('''    "B": (2, "#a090b0", "wall (the venue's lilac)"),
    "R": (1, "#e88860", "roof tiles (sunlit terracotta)"),
    "r": (2, "#b05840", "roof course (terracotta shade)"),''', '''    "B": (2, "#a090b0", "wall (the venue's lilac)"),
    "H": (2, "#a090b0", "hall wall behind the fountain (the wall's lilac, plain)"),
    "R": (1, "#f0b888", "roof tiles (light terracotta: the skin colour's slot)"),
    "r": (2, "#a090b0", "roof course (the wall's lilac)"),''')
rep('''    "d": (1, "#f0b888", "door wood (light oak: the skin colour's slot)"),''', '''    "d": (3, "#201828", "door (dark opening)"),''')
rep('''"m": (2, "#a090b0", "stone (the wall's lilac)"),''', '''"m": (0, "#fff0b0", "stone (sunlit pale stone, lighter than every wall)"),''')
# dawn: the hall behind the fountain goes dark (backlit), so the stone reads against it
rep('''    "B": (2, "#6a5070", "wall (backlit violet)"),''', '''    "B": (2, "#6a5070", "wall (backlit violet)"),
    "H": (3, "#301828", "hall wall behind the fountain (backlit, dark)"),''')
p.write_text(s)

p = T / "compose.py"
s = p.read_text()
rep('''FINALE_FIX = [(120, 64, 127, 71, "b", "W", "the jet's last water above Sal's hand foams white (water and skin are both DMG 1 by day)"),
              (128, 64, 143, 71, "y", "B", "Sal's cap shading takes the wall's lilac on Color (DMG unchanged: both 2): the hall and gable walls are behind it")]''',
    '''FINALE_FIX = [(120, 64, 127, 71, "b", "W", "the jet's last water above Sal's hand foams white (water and skin are both DMG 1 by day)"),
              (141, 53, 159, 90, "m", "B", "Dregs's jacket keeps its lilac (DMG 2): by day the stone key is the fountain's pale stone")]''')
p.write_text(s)
print("ok")
