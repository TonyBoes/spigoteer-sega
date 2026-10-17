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


# ---- the pause card's fades (src/pause.c CARD_FADE, src/trans.c pal_fast) on SameBoy -----------------------------------------------------------
# pal_fast reads palette RAM and VRAM outside VBlank (STAT mode checked before and after each colour); PyBoy cannot see a read gone wrong in mode 3.
# -DAUTO_CARD=n (src/main.c): boot -> BOSS RUSH's first fight (patrons, his entrance) -> START, DOWN, A: the HOW TO PLAY card -> (1: B back to the menu; 2: the card stays),
# the last frame at 14 s. With the fades (default) and with the LCD-off cut (-DCARD_FADE=0) the picture must be the same, pixel for pixel: the menu after the card closed
# (1) and the card's own colours after the fade-in (2).
CARD_VARIANTS = {"closed_fade": "-DAUTO_CARD=1", "closed_cut": "-DAUTO_CARD=1 -DCARD_FADE=0",
                 "open_fade": "-DAUTO_CARD=2", "open_cut": "-DAUTO_CARD=2 -DCARD_FADE=0"}


@pytest.fixture(scope="module")
def card_shots():
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = {}
    for name, flags in CARD_VARIANTS.items():
        bdir = OUT / f"build_card_{name}"
        cmd = ["make", f"BUILD={bdir}", f"DEBUGFLAGS=-DDEBUG_MENU {flags}"]
        jobs[name] = (bdir, subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT))
    out = {}
    for name, (bdir, p) in jobs.items():
        assert p.wait() == 0, f"build {name} failed"
        rom = OUT / f"card_{name}.gb"
        rom.write_bytes((bdir / "game.gb").read_bytes())
        shot = OUT / f"card_{name}"
        r = subprocess.run(["gbcheck", str(rom), "--length", "24", "--out", str(shot)], cwd=ROOT, capture_output=True, text=True)
        assert "FAIL" not in r.stdout, r.stdout
        for m in ("dmg", "cgb"):
            out[name, m] = Image.open(shot / f"card_{name}.{m}.png").convert("RGB")
    return out


def same_picture(a, b):
    assert a.tobytes() == b.tobytes(), f"differs in {Image.frombytes('L', a.size, bytes(abs(x - y) for x, y in zip(a.convert('L').tobytes(), b.convert('L').tobytes()))).getbbox()}"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_pause_menu_after_the_card_closed_is_the_picture_of_the_cut(card_shots, model):
    a = card_shots["closed_cut", model]
    assert len(a.getcolors()) > 3, "a busy scene, not a blank screen"
    same_picture(a, card_shots["closed_fade", model])


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_card_after_the_fade_in_has_its_own_colours(card_shots, model):
    a = card_shots["open_cut", model]
    assert len(a.getcolors()) > 3, "the card, not a white screen"
    same_picture(a, card_shots["open_fade", model])
