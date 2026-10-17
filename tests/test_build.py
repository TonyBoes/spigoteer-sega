# Build system: the ROM variants (game, release, game-unlocked) must not disturb each other (Makefile: per-variant scratch
# directory, flags stamps). Runs make / make release / make / make unlocked in a scratch copy of the sources and checks that
# every ROM boots to the title and that build/game.gb is byte-identical before and after building the others.
import hashlib
import shutil
import subprocess

import pytest
from gbtools import Rom

from conftest import ROOT

COPY = ["Makefile", "src", "assets", "tools", "third_party", "docs", "licenses", "CREDITS.md", "PLAN.md", "CLAUDE.md"]


def make(cwd, *args):
    r = subprocess.run(["make", *args], cwd=cwd, capture_output=True, text=True)
    assert r.returncode == 0, f"make {' '.join(args)}\n{r.stdout[-3000:]}\n{r.stderr[-2000:]}"
    return r.stdout


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def boots_to_title(path):
    for model in ("dmg", "cgb"):
        with Rom(path, model) as gb:
            gb.run(400)
            assert not gb.is_blank(), f"{path.name} on {model}: blank screen after 400 frames"
            assert gb.mem("game_state") is not None


@pytest.mark.slow
def test_variants_do_not_disturb_each_other(tmp_path):
    for name in COPY:
        src = ROOT / name
        if src.is_dir():
            shutil.copytree(src, tmp_path / name, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy(src, tmp_path / name)
    b = tmp_path / "build"

    make(tmp_path)
    game = digest(b / "game.gb")
    boots_to_title(b / "game.gb")

    make(tmp_path, "release")
    assert digest(b / "game.gb") == game, "make release changed build/game.gb"
    boots_to_title(b / "release.gb")
    assert digest(b / "release.gb") != game, "release must differ from the playtest build"

    out = make(tmp_path)
    assert digest(b / "game.gb") == game, "make after make release produced a different game.gb"
    assert "lcc" not in out, "game.gb was up to date; a plain make after make release must not relink it"
    boots_to_title(b / "game.gb")

    make(tmp_path, "unlocked")
    assert digest(b / "game.gb") == game, "make unlocked changed build/game.gb"
    boots_to_title(b / "game-unlocked.gb")
    assert digest(b / "game-unlocked.gb") != game

    # a flag change forces a rebuild, and changing it back restores the identical ROM
    out = make(tmp_path, "DEBUGFLAGS=-DDEBUG_MENU -DDEBUG_UNLOCKED")
    assert "lcc" in out and digest(b / "game.gb") == digest(b / "game-unlocked.gb")
    make(tmp_path)
    assert digest(b / "game.gb") == game
