"""Mockup 2 composite: POST_LUMBER page 2 ("THE SASQUATCH HANDED IT OVER") with the venue's crowd and the Sasquatch.
Every pasted pixel is existing approved game art: the patrons are copied pixel-exact from the game's own screenshot
(tests/golden/patrons_lumberjacks), the Sasquatch's HAPPY pose is transcribed from assets/art/boss/sasquatch.txt with the
colours the game itself shows him in (read from tests/golden/boss_sasquatch). Nothing new is drawn. Writes out/sc/m2_*.png."""
from PIL import Image
import numpy as np

W = '/workspace/.claude/worktrees/agent-ae298ef8ab3b98795/'
G = W + 'tests/golden/'
S = '/workspace/out/story_scenes/'


def pose(name):
    lines = open(W + 'assets/art/boss/sasquatch.txt').read().split('\n')
    i = lines.index('@' + name)
    return [l for l in lines[i + 1:i + 17]]


WALK, HAPPY, HAT = pose('WALK'), pose('HAPPY'), pose('HAT_STILL')[:8]


def find(gd, sc, art, region):
    """Offset where the art's '#' pixels all show one colour that the backdrop lacks there."""
    x0, y0, x1, y1 = region
    for oy in range(y0, y1):
        for ox in range(x0, x1):
            cols = {}
            ok = True
            for y, row in enumerate(art):
                for x, c in enumerate(row):
                    if c == '.':
                        continue
                    px = tuple(gd[oy + y, ox + x])
                    if cols.setdefault(c, px) != px:
                        ok = False
                        break
                if not ok:
                    break
            if ok and len(set(cols.values())) == len(cols):
                return ox, oy, cols
    raise SystemExit('not found')


for m in ('cgb', 'dmg'):
    sc = np.array(Image.open(S + f'{m}/06_POST_LUMBER_01.png').convert('RGB'))
    out = sc.copy()
    pat = np.array(Image.open(G + f'patrons_lumberjacks.{m}.png').convert('RGB'))
    boss = np.array(Image.open(G + f'boss_sasquatch.{m}.png').convert('RGB'))
    # the crowd: every pixel where the game's screenshot differs from the empty backdrop, bars 1-2 only (rows 40-79),
    # leaving out the game's Sal (columns 120-135) and the HUD
    d = (np.abs(pat.astype(int) - sc.astype(int)).sum(2) > 0)
    for y in range(40, 80):
        for x in range(0, 112):
            if d[y, x]:
                out[y, x] = pat[y, x]
    # bar 3 (the Spigoteer's): one lumberjack at the far left, copied from the game's bar 3 (rows 88-103, x 16-31)
    for y in range(88, 104):
        for x in range(16, 32):
            if d[y, x]:
                out[y, x] = pat[y, x]
    # the Sasquatch: colours as the game shows him
    ox, oy, cols = find(boss, sc, WALK, (8, 80, 40, 92))
    bx, by = 64, oy                        # same wall rows as in his fight, moved right towards the Spigoteer
    for y, row in enumerate(HAPPY):
        for x, c in enumerate(row):
            if c != '.':
                out[by + y, bx + x] = cols[c]
    for y, row in enumerate(HAT):          # his cone, 12 px from his left edge (hat_dx 12), on the row above
        for x, c in enumerate(row):
            if c != '.':
                out[by - 8 + y, bx + 12 + x] = cols['+' if c == '+' else '#']
    Image.fromarray(out).save(W + f'out/sc/m2_after_{m}.png')
    Image.fromarray(sc).save(W + f'out/sc/m2_before_{m}.png')
    print(m, 'boss at', ox, oy, cols)
