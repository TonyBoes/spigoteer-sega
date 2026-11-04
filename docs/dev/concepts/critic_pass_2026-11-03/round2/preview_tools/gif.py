#!/usr/bin/env python3
"""gif.py ROM VER OUT.gif: a cycle from the real ROM (walk, catch, gulp, hold), Color over DMG, x5, every 2nd frame.
The empty glass of HOLD / HOLDHOP is the sprite the engine does not draw yet: mocked over the hand for a proposal (not for `cur`)."""
import os
import sys
from pathlib import Path

ROM, VER, OUTF = sys.argv[1], sys.argv[2], sys.argv[3]
os.environ["GB_ROM"] = str(Path(ROM).resolve())
sys.path.insert(0, "/workspace/.claude/worktrees/agent-af7a9596251cca7e4/tests")
from PIL import Image, ImageDraw  # noqa: E402
from boss_common import fight, frames, row, throw, block_empties, still_regulars, play, to_bar, until  # noqa: E402

C = 3
B = row(C)["bar"]
Y0 = (5 + 3 * B) * 8 - 16
CROP = (8, Y0 + 6, 72, Y0 + 36)
GE = ["........", "........", "........", "........", ".#-..-#.", ".#....#.", ".#....#.", ".#....#.", ".#....#.", "..#..#..", "...##...", "...##...", "...##...", "...##...", ".######.", "........"]
PAL = {"cgb": {"-": (0xF0, 0xF0, 0xF8), "+": (0xC8, 0xD0, 0xE0), "#": (0x30, 0x30, 0x48)}, "dmg": {"-": (255, 255, 255), "+": (153, 153, 153), "#": (0, 0, 0)}}
S = 5


def run(model):
    out = []
    with fight(model, C) as gb:
        still_regulars(gb); play(gb); to_bar(gb, B); block_empties(gb)

        def rec(label):
            im = gb.image().convert("RGB")
            xp = gb.mem("boss_xpose")
            if VER != "cur" and xp in (6, 7):
                bx = gb.mem("boss_x")
                dy = 1 if xp == 7 else 0
                for y, r in enumerate(GE):
                    for x, c in enumerate(r):
                        if c != ".":
                            im.putpixel((bx + 24 + x, Y0 + 16 - 2 + dy + y), PAL[model][c])
            im = im.crop(CROP).resize((64 * S, 30 * S), Image.NEAREST)
            ImageDraw.Draw(im).text((3, 2), f"{VER} {model} {label}", fill=(255, 255, 0) if model == "cgb" else (255, 0, 0))
            out.append(im)

        for _ in range(48):
            frames(gb, 2); rec("WALK")
        throw(gb, B, 72, perfect=True)
        n = 0
        while gb.mem("boss_state") != 1 and n < 60:
            frames(gb, 2); rec("CATCH"); n += 1
        n = 0
        while gb.mem("boss_state") == 1 and n < 80:
            frames(gb, 2); rec("GULP"); n += 1
        for _ in range(90):
            frames(gb, 2); rec("HOLD")
    return out


a, b = run("cgb"), run("dmg")
n = min(len(a), len(b))
fr = []
for i in range(n):
    im = Image.new("RGB", (64 * S, 60 * S + 4), (60, 60, 60))
    im.paste(a[i], (0, 0))
    im.paste(b[i], (0, 30 * S + 4))
    fr.append(im.convert("P", palette=Image.ADAPTIVE, colors=64))
fr[0].save(OUTF, save_all=True, append_images=fr[1:], duration=34, loop=0, optimize=True)
print(OUTF, n, "frames")
