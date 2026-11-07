"""PLACEHOLDER (not art): the baseball park, 16 x 10 cells, assumed 70 distinct tiles.  A5: the table has no 'stadium' palette any more (see NOTES), the box borrows grass."""
import a5art


def build(dmg=False):
    return a5art.Box(16, 10, "grass", 70)
