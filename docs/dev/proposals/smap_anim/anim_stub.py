"""A one-cell stand-in for a venue whose approved picture is pasted over the world afterwards by mapctx.py (preview only)."""
from canvas import Canvas


def build(dmg=False):
    return Canvas("stub", "grass", 8, 8)
