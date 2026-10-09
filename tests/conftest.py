# Shared fixtures. GB_ROM overrides the ROM path; GB_UPDATE_GOLDEN=1 rewrites goldens.
import os
from pathlib import Path

import pytest
from gbtools import Rom

ROOT = Path(__file__).resolve().parent.parent
ROM = Path(os.environ.get("GB_ROM", ROOT / "build" / "game.gb"))
GOLDEN = ROOT / "tests" / "golden"
UPDATE = os.environ.get("GB_UPDATE_GOLDEN") == "1"


# ---- test hook: the game rebuilds its per-bar patron lists only when a patron arrives or leaves (M8a perf).
# A test that writes patron_state or patron_bar between frames changes that membership behind the game's back,
# so it must set `lists_dirty`; the next frame then rebuilds the lists. Every write through Rom.write (so every
# helper in every test file, perf_helpers included) is checked here and sets the hook when it touches those two
# arrays: no helper can forget it.
LIST_FIELDS = ("patron_state", "patron_bar")
MAX_PATRONS = 16
_rom_write = Rom.write


def mark_lists_dirty(gb):
    """Tell the game the patron lists must be rebuilt (after poking patron_state / patron_bar)."""
    _rom_write(gb, "lists_dirty", 1)


def _list_ranges(gb):
    r = gb.__dict__.get("_list_ranges")
    if r is None:
        r = []
        for name in LIST_FIELDS:
            try:
                a = gb.addr(name)
            except KeyError:                    # a ROM without the hook (not this game)
                continue
            r.append((a, a + MAX_PATRONS))
        gb._list_ranges = r
    return r


def _write(gb, ref, value):
    _rom_write(gb, ref, value)
    a = gb.addr(ref)
    if any(lo <= a < hi for lo, hi in _list_ranges(gb)):
        mark_lists_dirty(gb)


Rom.write = _write


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
    boot.write("tip_chance", 0)      # tips are M5; the M1-M4 tests and goldens must not see a coin (test_tips sets it)
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


# ---- game tunables: parsed from src/game.h (plain numeric defines only) ----
GAME = {m.group(1): int(m.group(2)) for m in _re.finditer(r"#define (\w+)\s+(\d+)\b", (ROOT / "src" / "game.h").read_text())}
