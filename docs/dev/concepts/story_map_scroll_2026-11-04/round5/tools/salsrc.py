"""Read Sal's real in-game frames (assets/art/bartender.txt) and show them."""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[6]


def frames(name="assets/art/bartender.txt"):
    fr, cur = [], []
    for l in (ROOT / name).read_text().splitlines():
        if l.startswith(";"):
            continue
        if not l.strip():
            if cur:
                fr.append(cur)
                cur = []
            continue
        cur.append(l)
    if cur:
        fr.append(cur)
    return fr


if __name__ == "__main__":
    fr = frames()
    print(len(fr), [len(f) for f in fr])
    col = {'.': (0, 200, 0), '-': (248, 248, 240), '+': (240, 184, 136), '#': (32, 32, 48)}
    im = Image.new("RGB", (len(fr) * 20, 24), (80, 120, 80))
    for i, f in enumerate(fr):
        for y, r in enumerate(f):
            for x, c in enumerate(r):
                im.putpixel((i * 20 + x, y), col[c])
    im.resize((im.width * 8, im.height * 8), 0).save("/tmp/claude-1000/-workspace/64761c6b-46f6-4217-a6f1-457b4de3152f/scratchpad/w/sal.png")
