"""Round 3 mountain with the angled runway (variant)."""
import mountain_a3 as M

W, H = M.W, M.H
BIOME, AT, REGION = M.BIOME, M.AT, M.REGION


def build():
    return M.build(runway=True)
