# No music_tick call of a changed tune may run past MUSIC_LATEST_LY's budget: 18 lines (2052 M-cycles; src/music.h).  tools/music_rig.py builds
# the real src/music.c + src/musicload.c + hUGEDriver + the generated build/music_*.c into a bare ROM and meters every call with DIV
# (64 M-cycles a count) over whole passes: per CALL (a frame in which two calls complete still shows the dearer one).
import re
import sys

import pytest
from conftest import ROOT

sys.path.insert(0, str(ROOT / "tools"))
import music_rig as rig      # noqa: E402

LIMIT_LINES = 18
LIMIT = LIMIT_LINES * rig.LINE      # 2052 M-cycles


@pytest.fixture(scope="module")
def built():
    rig.build()
    assert re.search(r"#define MUSIC_LATEST_LY 120\b", (ROOT / "src" / "music.h").read_text()), "18 lines = 120 + 18 + 4 lines of VBlank"


# ("map": Swipesy, warm only: it never starts cold, the title tune has run before it and loaded the show tune; cold its first calls reach 2176 M-cycles, 19.1 lines,
# with the kick body on its bass, 2048 without it: the song dict key "no_kick_body" in tools/songs.py is the switch)
TUNES = [("title", 3), ("clear", 1), ("over", 1), ("bonus", 4), ("show", 2)] + [(f"venue{i}", 2) for i in range(10)] + [("credits", 1), ("map", 2)]


@pytest.mark.parametrize("tune,passes", TUNES)
def test_no_call_of_any_tune_is_over_18_lines(built, tune, passes):
    # in the game the show tune is in buffer B before any other tune but the title at power-on starts (a tick that starts its 96-byte preload
    # slices cannot meet another tune's first frames): cold is the title's, and the show's own, case; the rest are measured warm.  (Every tune
    # of the game since music batches 2-4: the sailor's arpeggios, the Hall's and the Mountain's 18.0 / 17.4 included.)
    for warm in ((False, True) if tune == "title" else (False,) if tune == "show" else (True,)):
        r = rig.cost_calls(tune, warm=warm, passes=passes)
        assert r["worst_mcycles"] <= LIMIT and not r["calls_over_18_lines"], r
        assert r["mean_lines"] < 12, r        # (a whole pass: the average call is far under the worst)
        assert r["load_worst_mcycles"] <= 5000, r      # the pattern copy's frames (384 bytes a frame, the last one starts the tune): as every tune's start


def test_the_sailor_at_the_last_calls_tempo_is_within_18_lines_too():
    """music_fast (a story shift's Last call): a row is a frame shorter, the same notes in less time (tools/music_rig.py cost_calls(fast=True))."""
    r = rig.cost_calls("venue6", warm=True, passes=2, fast=True)
    assert r["frames"] == 2048 and r["worst_mcycles"] <= LIMIT and not r["calls_over_18_lines"], r
