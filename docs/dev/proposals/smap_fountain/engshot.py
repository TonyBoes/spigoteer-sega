"""Real-engine screenshots of the town stop (all venues open, camera on the town), from a scratch ROM.
GB_ROM=path/to/rom.gb python3 -I engshot.py TAG dmg|cgb      -> out/fountain_engine/TAG_MODEL.png (160 x 144, x1)"""
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "tests"))
os.chdir(ROOT)
import test_story_map as t  # noqa: E402
from PIL import Image  # noqa: E402

tag, model = sys.argv[1], sys.argv[2]
outd = ROOT / "out" / "fountain_engine"
outd.mkdir(parents=True, exist_ok=True)
tmp = outd / "tmp"
tmp.mkdir(exist_ok=True)
gb = t.to_map(model, 10, step=1, stop=t.TOWN)
gb.run(60)
p = tmp / f"{tag}_{model}.png"
gb.golden(p, update=True, diff_dir=tmp)
Image.open(p).convert("RGB").save(outd / f"{tag}_{model}.png")
print(outd / f"{tag}_{model}.png")
