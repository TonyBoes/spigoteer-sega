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


# ---- a note cut off (owner 2026-10-17, SameBoy iOS: the menu at the top of the screen, stale rows below its band) ------------------------------------
# A note (show_note: WY 24, LYC 31) ended by anything but end_note (a life lost, a scene change: overlay_on = 0) left WY and LYC on the note; the next
# window (the pause menu, a result card) then started at line 24 and ran to its LYC, showing the window map's stale rows (the debug menu's text) below the band.
# -DAUTO_NOTE (src/debug.c) cuts a note off 10 frames before START: the menu must still be the band at line 64 (its blank text row, lines 72-79, one colour).
@pytest.fixture(scope="module")
def cut_note():
    OUT.mkdir(parents=True, exist_ok=True)
    bdir = OUT / "build_note"
    cmd = ["make", f"BUILD={bdir}", "DEBUGFLAGS=-DDEBUG_MENU -DAUTO_TRANS=2 -DAUTO_NOTE -DAUTO_NOTRANS"]
    assert subprocess.run(cmd, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT).returncode == 0
    rom = OUT / "note.gb"
    rom.write_bytes((bdir / "game.gb").read_bytes())
    r = subprocess.run(["gbcheck", str(rom), "--length", "20", "--out", str(OUT / "note")], cwd=ROOT, capture_output=True, text=True)
    assert "FAIL" not in r.stdout, r.stdout
    return {m: Image.open(OUT / "note" / f"note.{m}.png").convert("RGB") for m in ("dmg", "cgb")}


def row_colours(img, y):
    return {img.getpixel((x, y)) for x in range(img.width)}


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_cut_off_note_does_not_move_the_pause_menu(cut_note, model):
    img = cut_note[model]
    for y in range(72, 80):
        assert len(row_colours(img, y)) == 1, f"line {y} is not the menu's blank row"
    assert len(row_colours(img, 30)) > 1 and len(row_colours(img, 130)) > 1, "the scene above and below the band is not the window"


# ---- Last call turning into the boss fight, on SameBoy (owner 2026-10-17: the level is rebuilt mid-play behind the cover) ---------------------------------
# src/story.c boss_in_place: LCD off behind the drink / white fade, his tiles and palettes loaded, the HUD columns rewritten, the tune restarted, then the banner, his
# entrance and (first time) his HOW TO PLAY card by itself. A palette or VRAM write that PyBoy accepts but an accurate LCD drops would show only here.
# -DAUTO_BOSS=n (src/debug.c auto_boss): boot -> STORY chapter 1's Last call -> quota poked met, bars poked empty -> he comes in IN PLACE (owner 2026-10-18: no cover, no
# LCD-off swap, no banner: his tiles stream in through the VBlank queue, his entrance plays) -> (1: his card opens by itself the frame after the entrance, A turns and
# closes it; 2: his card marked seen first) -> 120 game frames into the fight everything is frozen: the last frame (at 26 s) is a still picture whatever the fades took.
# The run with no transition and the LCD-off card (-DAUTO_NOTRANS -DCARD_FADE=0) is the reference: the card's fades and its exit must leave pixel for pixel the same picture,
# and so must the run that never showed the card.
# The ROM reads a start delay in frames from its free byte 0x3FFF, so runs of whole seconds with different delays land on every frame of the entrance
# (tools/boss_capture.py): in the run with no card (2) no frame from the level through his entrance may be white, flat or short of colours: the swap is invisible.
BOSS_VARIANTS = {"ref": "-DAUTO_BOSS=1 -DAUTO_NOTRANS -DCARD_FADE=0", "fade": "-DAUTO_BOSS=1", "seen": "-DAUTO_BOSS=2", "white": "-DAUTO_BOSS=1 -DTRANS_DEFAULT=2"}


@pytest.fixture(scope="module")
def boss_shots():
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = {}
    for name, flags in BOSS_VARIANTS.items():
        bdir = OUT / f"build_boss_{name}"
        cmd = ["make", f"BUILD={bdir}", f"DEBUGFLAGS=-DDEBUG_MENU {flags}"]
        jobs[name] = (bdir, subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT))
    out = {}
    for name, (bdir, p) in jobs.items():
        assert p.wait() == 0, f"build {name} failed"
        rom = OUT / f"boss_{name}.gb"
        rom.write_bytes((bdir / "game.gb").read_bytes())
        shot = OUT / f"boss_{name}"
        r = subprocess.run(["gbcheck", str(rom), "--length", "26", "--out", str(shot)], cwd=ROOT, capture_output=True, text=True)
        assert "FAIL" not in r.stdout, r.stdout
        for m in ("dmg", "cgb"):
            out[name, m] = Image.open(shot / f"boss_{name}.{m}.png").convert("RGB")
    return out


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("var", ["fade", "seen", "white"])
def test_the_boss_fight_after_the_swap_and_the_card_is_the_picture_without_them(boss_shots, var, model):
    a = boss_shots["ref", model]
    assert len(a.getcolors()) > 3, "the fight, not a blank screen"
    b = boss_shots[var, model]
    assert set(a.getdata()) == set(b.getdata()), "the same colours"
    # (a regular walking in at the left edge is a game frame or so apart between runs of different fades: the picture must be the same everywhere but that entry zone)
    box = Image.frombytes("L", a.size, bytes(abs(x - y) for x, y in zip(a.convert("L").tobytes(), b.convert("L").tobytes()))).getbbox()
    assert box is None or (box[0] >= 0 and box[2] <= 40 and box[1] >= 40), f"differs in {box}"



def frame_at(rom_bytes, model, secs, delay):
    """The SameBoy frame `secs` whole seconds into a run of the AUTO_BOSS ROM started `delay` frames late (byte 0x3FFF)."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        rom = Path(td) / "r.gb"
        b = bytearray(rom_bytes)
        b[0x3FFF] = delay if delay else 0xFF
        rom.write_bytes(b)
        subprocess.run(["sameboy_tester", f"--{model}", "--length", str(secs), str(rom)], capture_output=True, timeout=600)
        return Image.open(rom.with_suffix(".bmp")).convert("RGB")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_boss_comes_in_with_no_white_or_blank_frame(boss_shots, model):
    """In-place entrance on SameBoy, frame by frame: every frame sampled from the level through his tiles streaming in and his entrance (seconds 7-9, a frame
    in three) is a whole scene, never a white cover, a flat screen or a picture short of colours: nothing was written outside VBlank and nothing was faded."""
    import numpy as np
    rom = (OUT / "boss_seen.gb").read_bytes()
    seen = 0
    fin = np.asarray(boss_shots["seen", model])
    base = float((fin == 255).all(axis=2).mean())         # (a DMG scene is mostly the lightest shade: a white frame is far above this)
    for secs in (7, 8, 9):
        for delay in range(0, 60, 3):
            a = np.asarray(frame_at(rom, model, secs, delay))
            white = float((a == 255).all(axis=2).mean())
            colours = len({tuple(c) for c in a.reshape(-1, 3)})
            assert white < base + 0.15, f"a white frame ({white:.2f}) at {secs} s, delay {delay}"
            assert colours >= 4, f"a flat frame ({colours} colours) at {secs} s, delay {delay}"
            seen += 1
    assert seen == 60
