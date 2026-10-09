# Shared fixtures. GB_ROM overrides the ROM path; GB_UPDATE_GOLDEN=1 rewrites goldens.
import os
from pathlib import Path

import pytest
from gbtools import Rom

ROOT = Path(__file__).resolve().parent.parent
ROM = Path(os.environ.get("GB_ROM", ROOT / "build" / "game.gb"))
GOLDEN = ROOT / "tests" / "golden"
UPDATE = os.environ.get("GB_UPDATE_GOLDEN") == "1"


PLAYING = 1
OLD_INTRO_LEFT = 44    # intro_timer the M1-M3 fixture had after 120 frames; kept so old tests see the same timing


@pytest.fixture(params=["dmg", "cgb"])
def boot(request):
    """A booted ROM sitting on the title screen, once per hardware model."""
    with Rom(ROM, request.param) as rom:
        rom.run(120)
        rom.model_name = request.param
        yield rom


@pytest.fixture
def gb(boot):
    """Gameplay: boot, press START, then run until the intro delay is where the M1-M3 tests expect it."""
    boot.press("start", 2)
    for _ in range(30):
        if boot.mem("game_state") == PLAYING:
            break
        boot.run(1)
    assert boot.mem("game_state") == PLAYING
    while boot.mem("intro_timer") > OLD_INTRO_LEFT:
        boot.run(1)
    return boot


def check_golden(gb, name):
    """Compare the screen with tests/golden/<name>.<model>.png; diffs land in out/diff/."""
    ok = gb.golden(GOLDEN / f"{name}.{gb.model_name}.png", update=UPDATE, diff_dir=ROOT / "out" / "diff")
    assert ok, f"screen differs from golden {name}.{gb.model_name}.png (see out/diff/). Intentional? GB_UPDATE_GOLDEN=1 make test"


# ---- screen layout: parsed from src/layout.h so a layout tweak needs no test edits ----
import re as _re

_LAYOUT_H = (ROOT / "src" / "layout.h").read_text()
LAYOUT = {m.group(1): int(m.group(2)) for m in _re.finditer(r"#define (\w+)\s+(\d+)\b", _LAYOUT_H)}


def bar_top_row(b):
    return LAYOUT["BAR_FIRST_ROW"] + LAYOUT["BAR_ROW_STRIDE"] * b


def bar_counter_row(b):
    return bar_top_row(b) + LAYOUT["BAR_COUNTER_DROW"]


def bar_top_y(b):
    return bar_top_row(b) * 8


def mug_top_y(b):
    """Screen y of the top of a mug / fill / glass sprite on bar b."""
    return bar_top_y(b) + LAYOUT["MUG_DY"]
