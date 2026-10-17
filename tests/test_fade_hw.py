# The palette fades (src/trans.c F1 / F2) on an accurate LCD: SameBoy, not PyBoy.
#
# PyBoy lets palette RAM and VRAM be read and written at any time; a real LCD (and SameBoy) returns 0xFF for reads and drops writes in mode 3. The fade read the
# scene's colours back with C loops that overran the VBlank, so on a flash cart the colours that came back were part 0xFF bytes: "sprites off colour".
# tests/test_trans_fade.py (PyBoy) could not see it.
#
# Test-only ROMs drive themselves (src/main.c -DAUTO_TRANS=n: n 1 title -> STORY -> NORMAL, n 2 title -> ARCADE; -DAUTO_NOTRANS: the same with the
# transitions off). They are built in out/fadehw_<name>/ (a separate BUILD dir: build/game.gb stays the real ROM), run by gbcheck for 14 emulated seconds
# on DMG and CGB, and the last frame is compared:
#   story  : the final frame is identical to the no-transition frame (a still picture; sprites included);
#   arcade : a live scene (the patrons move, so the pixels differ): the set of colours on the screen is the same.
# Slow (six builds, ~2 minutes in parallel): RUN_SLOW=1 python3 -m pytest tests/test_fade_hw.py
import os
import subprocess
from pathlib import Path

import pytest
from PIL import Image

from conftest import ROOT

pytestmark = [pytest.mark.timeout(1500),
              pytest.mark.skipif(not os.environ.get("RUN_SLOW"), reason="slow: six builds and twelve SameBoy runs (RUN_SLOW=1)")]

OUT = ROOT / "out" / "fadehw"
ROUTES = {"story": 1, "arcade": 2}
VARIANTS = {"off": "-DAUTO_NOTRANS", "f1": "-DTRANS_DEFAULT=1", "f2": "-DTRANS_DEFAULT=2"}


@pytest.fixture(scope="module")
def shots():
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = {}
    for route, n in ROUTES.items():
        for var, flag in VARIANTS.items():
            name = f"{route}_{var}"
            bdir = OUT / f"build_{name}"
            cmd = ["make", f"BUILD={bdir}", f"DEBUGFLAGS=-DDEBUG_MENU -DAUTO_TRANS={n} {flag}"]
            jobs[name] = (bdir, subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT))
            if len(jobs) % 3 == 0:                  # three builds at a time
                for _, p in list(jobs.values())[-3:]:
                    p.wait()
    out = {}
    for name, (bdir, p) in jobs.items():
        assert p.wait() == 0, f"build {name} failed"
        rom = OUT / f"{name}.gb"
        rom.write_bytes((bdir / "game.gb").read_bytes())
        shot = OUT / name
        r = subprocess.run(["gbcheck", str(rom), "--length", "14", "--out", str(shot)], cwd=ROOT, capture_output=True, text=True)
        assert "FAIL" not in r.stdout, r.stdout
        for m in ("dmg", "cgb"):
            out[name, m] = Image.open(shot / f"{name}.{m}.png").convert("RGB")
    return out


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("var", ["f1", "f2"])
def test_story_picture_after_the_fade_is_the_picture_without_it(shots, var, model):
    a, b = shots["story_off", model], shots[f"story_{var}", model]
    assert a.tobytes() == b.tobytes(), f"differs in {Image.frombytes('L', a.size, bytes(abs(x - y) for x, y in zip(a.tobytes(), b.tobytes()))).getbbox()}"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("var", ["f1", "f2"])
def test_arcade_scene_colours_after_the_fade_are_the_scenes(shots, var, model):
    a, b = shots["arcade_off", model], shots[f"arcade_{var}", model]
    assert set(a.getdata()) == set(b.getdata())
