"""Scratch probe (needs the scratch engine build in build/): walks the whole loop on the real engine, all ten venues open, and saves the screen
on arrival at every stop and every 48 frames of every walk.  python3 -I probe_shots.py dmg|cgb   ->  out/a4/shots/MODEL_LEGnn_kk.png"""
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tests"))
os.chdir(ROOT)
import test_story_map as t  # noqa: E402
from PIL import Image  # noqa: E402

model = sys.argv[1]
outd = ROOT / "out" / "a4" / "shots"
outd.mkdir(parents=True, exist_ok=True)
tmp = ROOT / "out" / "a4" / "shots_tmp"
tmp.mkdir(parents=True, exist_ok=True)


def shot(gb, name):
    p = tmp / f"{name}.png"
    gb.golden(p, update=True, diff_dir=tmp)
    Image.open(p).convert("RGB").save(outd / f"{model}_{name}.png")


gb = t.to_map(model, 10, step=1, stop=0)
order = list(range(10)) + [t.TOWN]
log = []
for k, s in enumerate(order):
    nxt = order[(k + 1) % 11]
    di = [i for i in range(4) if t.EXITS[s][i] == nxt]
    assert di, (s, nxt)
    shot(gb, f"leg{k:02d}_00_arrive{s}")
    gb.press(t.DIRS[di[0]], 4)
    n = 0
    for f in range(4000):
        if not gb.read("story_scratch", 520)[t.SV + t.V_WALK]:
            break
        gb.run(1)
        if f % 48 == 47:
            n += 1
            shot(gb, f"leg{k:02d}_{n:02d}")
    gb.run(2)
    x, y = t.sal_xy(gb)
    log.append((s, nxt, f, t.cam(gb), (x, y)))
    print("leg", s, "->", nxt, "frames", f, "camera", t.cam(gb), "Sal on screen at", (x, y), flush=True)
shot(gb, "leg10_00_arrive_saloon")
