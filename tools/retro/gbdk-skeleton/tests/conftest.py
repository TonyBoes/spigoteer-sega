# Shared fixtures: every test runs once per built target (TARGETS="gb sms gg").
# GB_UPDATE_GOLDEN=1 rewrites goldens. Tests drive stable-retro (fast);
# `make check` gates the same ROMs in MesenCE.
import os
from pathlib import Path

import pytest
from retrotools import Rom

ROOT = Path(__file__).resolve().parent.parent
EXT = {"gb": "gb", "sms": "sms", "gg": "gg"}
TARGETS = os.environ.get("TARGETS", "gb sms gg").split()
GOLDEN = ROOT / "tests" / "golden"
UPDATE = os.environ.get("GB_UPDATE_GOLDEN") == "1"


@pytest.fixture(params=TARGETS)
def rom(request):
    path = ROOT / "build" / request.param / f"game.{EXT[request.param]}"
    if not path.is_file():
        pytest.skip(f"{path} not built")
    with Rom(path) as r:
        r.run(120)
        yield r


def check_golden(rom, name):
    ok = rom.golden(GOLDEN / f"{name}.{rom.system}.png", update=UPDATE, diff_dir=ROOT / "out" / "diff")
    assert ok, f"screen differs from golden {name}.{rom.system}.png (see out/diff/). Intentional? GB_UPDATE_GOLDEN=1 make test"
