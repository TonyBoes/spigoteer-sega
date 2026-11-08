"""A one-cell stand-in for the cow venue (proposal renderer only): the real piece is pasted over the world after it is built."""
from canvas import Canvas


def build(dmg=False):
    return Canvas("cow_stub", "cow", 8, 8)
