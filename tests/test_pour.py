# The perfect pour (story mode, src/pour.c; owner Q6): a release in the 12-frame sparkle window after the drink is
# full launches a PERFECT drink, which scores 2 x the venue's serve score when a patron catches it, with the "x2" cue
# beside the catch. Held to 28 the foam runs over (ordinary); a drink carried to another bar is ordinary. Arcade is
# unchanged: no window, no sparkle frame, no bonus, no cue.
import json

import pytest
from conftest import GAME, ROOT, check_golden
from test_flow import PLAYING, inject_mug, run_until, set_patron, state
from test_lift import oam_lines
from test_story import to_chapter

pytestmark = pytest.mark.timeout(240)

POUR = json.loads((ROOT / "build" / "pour.json").read_text())
THEMES = list(POUR["venues"])
OBJ_POUR = POUR["obj_pour"]
OBJ_CUE = OBJ_POUR + 4
OAM_FILL, OAM_CUE = GAME["OAM_FILL"], GAME["OAM_CUE"]
FILL_FRAMES, PERFECT_END = GAME["FILL_FRAMES"], GAME["PERFECT_END"]
OBJ_MUG_FILL_FULL = 56 + 4 + 16 + 3 * 2          # OBJ_MUG_FILL + fill_stage 3 * 2 (bartender 56, mug 4, glass 16)
FULL, EMPTY, HELD = 1, 2, 4
MAX_M = 20


def score(gb):
    return int.from_bytes(gb.read("score", 4), "little")


def story(model, c=0):
    """Chapter c's Opening, in play: nothing walks or spawns (intro_timer), a patron waits on bar 0 to catch."""
    gb = to_chapter(model, c)
    gb.write("intro_timer", 255)
    set_patron(gb, 0, 64)
    gb.run(2)
    assert gb.mem("bar") == 0 and gb.mem("bartender_x") == GAME["TAP_X"] and state(gb) == PLAYING
    return gb


def fill_to(gb, t, key="pour_t"):
    """Hold A at the tap until `key` reads t (the frame's end)."""
    gb.hold("a")
    run_until(gb, lambda: gb.mem(key) == t, 60)


def launched(gb):
    """The quality of the drink just launched (its mug_timer: 1 perfect, 0 ordinary), None if none was."""
    for _ in range(4):
        st, x, q = gb.read("mug_state", MAX_M), gb.read("mug_x", MAX_M), gb.read("mug_timer", MAX_M)
        new = [i for i in range(MAX_M) if st[i] == FULL and x[i] >= GAME["SPOUT_X"] - 8]
        if new:
            assert len(new) == 1
            return q[new[0]]
        gb.run(1)
    return None


def hold_release(gb, n):
    """A held for n frames (a fresh press at the tap), then let go: the launched drink's quality (None: none)."""
    gb.hold("a")
    gb.run(n)
    gb.release("a")
    gb.run(1)
    return launched(gb)


def let_go(gb):
    gb.release("a")
    gb.run(1)
    return launched(gb)


def drop_mugs(gb):
    for i in range(MAX_M):
        gb.write(gb.addr("mug_state") + i, 0)
    gb.write("mugs_live", 0)
    gb.run(2)


def first_launch(gb):
    """The fewest frames of A that launch a drink (the drink full, pour_t FILL_FRAMES on the last held frame)."""
    for n in range(FILL_FRAMES - 4, FILL_FRAMES + 4):
        q = hold_release(gb, n)
        drop_mugs(gb)
        if q is not None:
            return n
    raise AssertionError("never launched")


def pour_at(gb, t):
    """Release A so that the last held frame has pour_t t (FILL_FRAMES..): the drink's quality."""
    n = first_launch(gb) + t - FILL_FRAMES
    return hold_release(gb, n)


def catch_delta(gb):
    """Run until the drink is caught; the score it made on that frame."""
    for _ in range(120):
        s0 = score(gb)
        gb.run(1)
        if HELD in gb.read("mug_state", MAX_M):
            return score(gb) - s0
    raise AssertionError("never caught")


def fill_entry(gb):
    gb.run(1)                                     # (OAM is the shadow of the frame before)
    return gb.oam()[OAM_FILL]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("t", [FILL_FRAMES, PERFECT_END - 1])
def test_a_release_in_the_window_is_perfect_and_scores_double(model, t):
    with story(model) as gb:
        assert pour_at(gb, t) == 1
        s = gb.mem("serve_score")
        assert catch_delta(gb) == 2 * s and gb.mem("perfect_n") == 1
        gb.run(1)
        cue = gb.oam()[OAM_CUE]
        assert cue["tile"] == OBJ_CUE and 0 < cue["y"] < 160, "the x2 cue beside the catch"


def sweep(gb, k=16):
    """Qualities of the drinks released after first_launch .. + k - 1 frames of A."""
    n0, q = first_launch(gb), []
    for n in range(n0, n0 + k):
        q.append(hold_release(gb, n))
        drop_mugs(gb)
    return q


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_window_is_twelve_frames(model):
    """Of the release frames that launch a drink, the first 12 (pour_t 16..27 on the last held frame) are perfect,
    every later one ordinary."""
    with story(model) as gb:
        assert sweep(gb) == [1] * (PERFECT_END - FILL_FRAMES) + [0] * 4


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_held_to_28_the_foam_runs_over_and_the_drink_is_ordinary(model):
    with story(model) as gb:
        fill_to(gb, PERFECT_END)
        assert gb.mem("pour_q") == 0
        e = fill_entry(gb)
        assert e["tile"] == OBJ_POUR + 2, "the overflow frame"
        gb.run(30)
        assert gb.mem("pour_t") == PERFECT_END, "it stays at the overflow"
        assert let_go(gb) == 0
        assert catch_delta(gb) == 0 and gb.mem("perfect_n") == 0
        gb.run(2)
        assert gb.oam()[OAM_CUE]["y"] == 0, "no cue"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_sparkle_frame_shows_through_the_window(model):
    with story(model) as gb:
        fill_to(gb, FILL_FRAMES - 1, "fill_timer")
        e = fill_entry(gb)
        assert e["tile"] == OBJ_MUG_FILL_FULL - 2, "still filling: the ordinary fill frames"
        tiles = []
        for _ in range(PERFECT_END - FILL_FRAMES + 8):
            gb.run(1)
            tiles.append(gb.oam()[OAM_FILL]["tile"])
            if FILL_FRAMES <= gb.mem("pour_t") < PERFECT_END:
                assert gb.mem("pour_q") == 1 and gb.mem("fill_timer") == FILL_FRAMES
        # the full frame never shows: the fill frames, then 12 frames of sparkle, then the overflow for good
        k = tiles.index(OBJ_POUR)
        assert OBJ_MUG_FILL_FULL not in tiles and all(t < OBJ_POUR for t in tiles[:k])
        assert tiles[k:] == [OBJ_POUR] * (PERFECT_END - FILL_FRAMES) + [OBJ_POUR + 2] * (len(tiles) - k - 12)
        flags = gb.oam()[OAM_FILL]["flags"]
        if model == "cgb":
            assert flags & 7 == GAME["OBJPAL_MUG_FULL"]
        else:
            assert flags & 0x10, "DMG: OBP1 (the drink darkens in his hand)"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_carried_drink_is_never_perfect(model):
    with story(model) as gb:
        fill_to(gb, FILL_FRAMES + 2)
        gb.press("down", 1)                       # A still held: carried to bar 1
        assert gb.mem("bar") == 1 and gb.mem("fill_timer") == FILL_FRAMES
        assert gb.mem("pour_t") == PERFECT_END and gb.mem("pour_q") == 0
        gb.press("up", 1)                         # and back to bar 0, where the patron waits
        assert gb.mem("bar") == 0
        assert let_go(gb) == 0
        assert catch_delta(gb) == 0 and gb.mem("perfect_n") == 0


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("c", [0, 5])
def test_the_venue_s_frames_and_the_cue_are_loaded(model, c):
    with to_chapter(model, c) as gb:
        assert list(gb.read(0x8000 + OBJ_POUR * 16, 64)) == POUR["venues"][THEMES[c]]
        assert list(gb.read(0x8000 + OBJ_CUE * 16, 32)) == POUR["cue"]


def test_arcade_has_no_window_no_bonus_and_no_cue(gb):
    """Arcade pouring as before: fill_timer stops at 16, the full fill frame on OBP0, the drink ordinary."""
    gb.write("intro_timer", 255)
    set_patron(gb, 0, 64)
    gb.run(2)
    s = gb.mem("serve_score")
    fill_to(gb, FILL_FRAMES, "fill_timer")
    gb.run(30)
    assert gb.mem("fill_timer") == FILL_FRAMES and gb.mem("fill_stage") == 3 and gb.mem("pour_t") == 0
    e = fill_entry(gb)
    assert e["tile"] == OBJ_MUG_FILL_FULL and (gb.model_name == "cgb" or e["flags"] == 0)
    assert let_go(gb) == 0
    assert catch_delta(gb) == 0 and gb.mem("perfect_n") == 0 and s
    gb.run(2)
    assert gb.oam()[OAM_CUE]["y"] == 0
    assert sweep(gb) == [0] * 16, "no release frame is perfect in arcade"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_cue_never_makes_an_11th_object_on_a_line(model):
    """The cue shows beside the catch; with bar 0's lines crowded (the bartender's 4 entries, the held drink, empties
    sliding by) it is left out while a line would pass 10 objects, and comes back when there is room."""
    with story(model) as gb:
        assert pour_at(gb, FILL_FRAMES) == 1
        catch_delta(gb)
        gb.run(1)
        assert gb.oam()[OAM_CUE]["y"] and max(oam_lines(gb)) <= 10
        for k in range(6):
            inject_mug(gb, 0, 70 + 8 * k, st=EMPTY)
        shown = []
        for _ in range(30):
            gb.run(1)
            assert max(oam_lines(gb)) <= 10
            shown.append(gb.oam()[OAM_CUE]["y"] != 0)
        assert not all(shown[:5]), "crowded: left out"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_sparkle_golden(model):
    with story(model) as gb:
        fill_to(gb, FILL_FRAMES + 4)
        gb.run(1)
        check_golden(gb, "pour_sparkle")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_cue_golden(model):
    with story(model) as gb:
        assert pour_at(gb, FILL_FRAMES + 4) == 1
        catch_delta(gb)
        gb.run(1)
        check_golden(gb, "pour_cue")
