"""Floating logs, redrawn by hand (owner: "logs in water read as ice blocks").  Symbols typed by me: '3' bark and rim (dark wood), 'b' a bark line, 'd' the end-grain
disc (a dark dot in the middle), 'r' a ripple, '.' water (transparent).  A conversion table turns the symbols into indices:
  Color and DMG dark water: b d r -> 1  ('water' palette: 1 = foam cream, 3 = wood brown 905830; DMG 168 on 24, the water is 88)
  DMG light water:          b -> 2 (88), d r -> 0 (248); the water is 168, the rim and body 3 (24)
A piece is a whole number of cells (H 16 x 8, V 8 x 16) and sits on the cell corner.  Variant 1: one log with its end disc.  Variant 2: a pair, ends opposite."""

H1 = ["................",
      "...333333333333.",
      "..33bbb33333ddd3",
      "..3333333333d3d3",
      "..3333bbb333ddd3",
      "...333333333333.",
      ".rr..........rr.",
      "................"]
V1 = [".rr.....",
      "........",
      "..333...",
      ".33333..",
      ".3b333..",
      ".3b333..",
      ".3b333..",
      ".33333..",
      ".333b3..",
      ".333b3..",
      ".333b3..",
      ".33333..",
      ".3ddd3..",
      ".3d3d3..",
      ".3ddd3..",
      "..333..."]
H2 = ["..333333333333..",
      ".3dd3333bbb333..",
      ".3dd3333333333..",
      "..333333333333..",
      "...333333333333.",
      "..33bbb333333dd3",
      "..33333333333dd3",
      "...333333333333."]
_A = [".33.", "3dd3", "3dd3", "3333", "3b33", "3b33", "3333", "3333", "33b3", "33b3", "3333", "3333", "3333", ".33.", "....", "...."]
_B = ["....", "....", ".33.", "3333", "33b3", "33b3", "3333", "3333", "3b33", "3b33", "3333", "3333", "3333", "3dd3", "3dd3", ".33."]
V2 = [a + b for a, b in zip(_A, _B)]

for _p, _w, _h in ((H1, 16, 8), (V1, 8, 16), (H2, 16, 8), (V2, 8, 16)):
    assert len(_p) == _h and all(len(r) == _w for r in _p), (_w, _h, [len(r) for r in _p])


def conv(rows, light=False):
    t = {"3": "3", "b": "2" if light else "1", "d": "0" if light else "1", "r": "0" if light else "1", ".": "."}
    return ["".join(t[c] for c in r) for r in rows]


VARIANTS = {"v1": (H1, V1), "v2": (H2, V2)}
