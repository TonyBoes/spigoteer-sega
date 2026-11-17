# The C twin of the credits' palette split (src/credits_split.c, ASM_CR_SPLIT=0) must give the same roll as the asm build: every frame of the shared-screen roll, on both models
# (tools/dev/credits_roll_check.py: no picture pixel changes but by the scroll, every page is the page as generated, its sprites are its own). Every asm routine keeps a working,
# tested C version (CLAUDE.md): the C writers took two lines a palette where the asm takes one, the swap ran into the VBlank and its drain was skipped, and a map row never
# reached the screen (2026-11-16). The ROM is the CRSPLIT build with the C writers, built once into out/ctwin.
import os
import sys

import pytest

from conftest import ROOT, locked_make

sys.path.insert(0, str(ROOT / "tools" / "dev"))

OUT = ROOT / "out" / "ctwin"
pytestmark = pytest.mark.timeout(900)


@pytest.fixture(scope="module")
def ctwin():
    bdir = OUT / "build"
    env = dict(os.environ, CRFLOW="SMOOTH", CRSCENE="1", CRSPLIT="1", CRCFLAGS="-DASM_CR_SPLIT=0")
    env.pop("GB_ROM", None)
    r = locked_make([f"BUILD={bdir}", f"OUT={OUT / 'o'}", "unlocked"], "ctwin", env=env)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    rom = bdir / "game-unlocked.gb"
    assert "DEF _cr_split_isr " in rom.with_suffix(".noi").read_text()
    return rom, bdir


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_c_twin_of_the_split_gives_a_clean_roll(ctwin, model):
    from credits_roll_check import run
    rom, bdir = ctwin
    frames, bad, *_ = run(rom, bdir, model, None, 11000)
    bad.pop("crops", None)
    assert frames > 10000
    assert not {k: v[:3] for k, v in bad.items() if k in ("scan", "page", "sprites", "perline") and v}, {k: len(v) for k, v in bad.items() if v}
