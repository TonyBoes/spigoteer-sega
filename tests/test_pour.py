# The perfect pour (story mode, src/pour.c; owner Q6, rounds 2-3): the drink is full at 16 and settles (plain full
# frame, a release is ordinary); a release in the 5-frame sparkle window 27..31 launches a PERFECT drink, which scores
# 2 x the venue's serve score when a patron catches it, with the x2 cue beside the catch. From 32 the foam runs over
# (ordinary); a drink carried to another bar is ordinary. Arcade is unchanged: no window, no sparkle, no bonus, no cue.
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
OBJ_CUE = POUR["obj_pour_cue"]
OAM_FILL, OAM_CUE = GAME["OAM_FILL"], GAME["OAM_CUE"]
FILL_FRAMES = GAME["FILL_FRAMES"]
WIN0, WIN, HARD = GAME["POUR_WIN_START"], GAME["POUR_WIN_LEN"], GAME["POUR_WIN_HARD"]
END = WIN0 + WIN                                  # the first overflow frame
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


def launched(gb, raw=False):
    """The quality of the drink just launched (its mug_timer: 1 perfect, 3 perfect and the 3rd+ in a row, 0 ordinary; raw=False: 1 / 0 only),
    None if none was."""
    for _ in range(4):
        st, x, q = gb.read("mug_state", MAX_M), gb.read("mug_x", MAX_M), gb.read("mug_timer", MAX_M)
        new = [i for i in range(MAX_M) if st[i] == FULL and x[i] >= GAME["SPOUT_X"] - 8]
        if new:
            assert len(new) == 1
            return q[new[0]] if raw else q[new[0]] & 1
        gb.run(1)
    return None


def hold_release(gb, n, raw=False):
    """A held for n frames (a fresh press at the tap), then let go: the launched drink's quality (None: none)."""
    gb.write("intro_timer", 255)                  # (long sweeps: nobody walks to the tap meanwhile)
    gb.hold("a")
    gb.run(n)
    gb.release("a")
    gb.run(1)
    return launched(gb, raw)


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


def pour_at(gb, t, raw=False):
    """Release A so that the last held frame has pour_t t (FILL_FRAMES..): the drink's quality."""
    n = first_launch(gb) + t - FILL_FRAMES
    return hold_release(gb, n, raw)


def catch_delta(gb):
    """Run until the drink is caught; the score it made on that frame."""
    for _ in range(120):
        s0 = score(gb)
        gb.run(1)
        if HELD in gb.read("mug_state", MAX_M):
            return score(gb) - s0
    raise AssertionError("never caught")


def assert_cue(gb):
    """The x2 cue (one 8x16 entry, OAM 26) beside the catch."""
    cue = gb.oam()[OAM_CUE]
    assert cue["tile"] == OBJ_CUE and 0 < cue["y"] < 160, "the x2 cue beside the catch"


def fill_entry(gb):
    gb.run(1)                                     # (OAM is the shadow of the frame before)
    return gb.oam()[OAM_FILL]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("t", [WIN0, END - 1])
def test_a_release_in_the_window_is_perfect_and_scores_double(model, t):
    with story(model) as gb:
        assert pour_at(gb, t) == 1
        s = gb.mem("serve_score")
        assert catch_delta(gb) == 2 * s and gb.mem("perfect_n") == 1
        gb.run(1)
        assert_cue(gb)


SFX_LAUNCH, SFX_PERFECT, SFX_N = 2, 15, 16        # src/music.h


def sfx(gb, i):
    return gb.read("sfx_count", SFX_N)[i]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_perfect_release_chimes_instead_of_the_launch_sound(model):
    """Owner playtest 2026-10-18: a perfect pour plays a soft chime (SFX_PERFECT) INSTEAD of the launch's sweep; every other release (settling, the
    overflow) still plays SFX_LAUNCH and no chime."""
    with story(model) as gb:
        n0 = first_launch(gb)
        for n in range(n0, n0 + END - FILL_FRAMES + 4):
            l0, p0 = sfx(gb, SFX_LAUNCH), sfx(gb, SFX_PERFECT)
            q = hold_release(gb, n)
            drop_mugs(gb)
            assert q is not None
            assert (sfx(gb, SFX_PERFECT) - p0, sfx(gb, SFX_LAUNCH) - l0) == ((1, 0) if q else (0, 1)), (n - n0, q)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_chime_request_bit_is_dispatched(model):
    """SFX_PERFECT is request bit 14 (the high byte of sfx_req, the table's last row): the next music tick takes it (the sound itself: tests/test_sound.py)."""
    with story(model) as gb:
        gb.write(gb.addr("sfx_req") + 1, 1 << (SFX_PERFECT - 1 - 8))
        gb.run(1)
        assert gb.read("sfx_req", 2) == b"\0\0", "dispatched by the tick"


def slide_tiles(gb, perfect, frames=40):
    """Release a drink (perfect or settling-ordinary) and follow its OAM entry while it slides: [tile of the entry each frame], the entries in use."""
    first_launch(gb)
    n = first_launch(gb) + (WIN0 - FILL_FRAMES if perfect else 0)
    q = hold_release(gb, n)
    assert q == (1 if perfect else 0)
    tiles, used, mug_t = [], [], gb.mem("spr_full_t")
    for _ in range(frames):
        gb.run(1)
        if HELD in gb.read("mug_state", MAX_M):
            break
        oam = gb.oam()
        used.append(sum(1 for e in oam if 0 < e["y"] < 160))
        i = next((k for k in range(MAX_M) if gb.read("mug_state", MAX_M)[k] == FULL), None)
        if i is None:
            continue
        mx = gb.read("mug_x", MAX_M)[i]
        hit = [e for e in oam if 0 < e["y"] < 160 and abs(e["x"] - mx - 9) <= 1 and      # (the OAM shows the frame before: 2 px behind)
                e["tile"] in (mug_t, OBJ_POUR)]
        if hit:
            tiles.append(hit[0]["tile"])
    return tiles, used



@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_perfect_mug_sparkles_while_it_slides_and_an_ordinary_one_does_not(model):
    """Owner playtest 2026-10-18: the mug's entry swaps to the sparkle frame (OBJ_POUR) for 3 frames of 8; no entry is added, so no line gets a sprite."""
    with story(model) as gb:
        set_patron(gb, 0, 20)                         # (far away: the slide is long)
        gb.run(2)
        tiles, used_p = slide_tiles(gb, True)
        assert len(tiles) >= 16
        sparkle = tiles.count(OBJ_POUR)
        assert 0.25 * len(tiles) <= sparkle <= 0.5 * len(tiles), (sparkle, len(tiles))
        assert any(t != OBJ_POUR for t in tiles), "it is a plain mug in between"
        runs = "".join("S" if t == OBJ_POUR else "." for t in tiles).split(".")
        assert max(len(r) for r in runs) <= 3, "a twinkle is 3 frames of 8, never a steady sparkle"
        drop_mugs(gb)
        gb.write("pour_q", 0)
        tiles, used_o = slide_tiles(gb, False)
        assert len(tiles) >= 16 and OBJ_POUR not in tiles, "an ordinary mug never sparkles"
        assert max(used_p) <= max(used_o) + 1, "the perfect mug is one entry like the other"


def sweep(gb, k=16):
    """Qualities of the drinks released after first_launch .. + k - 1 frames of A."""
    n0, q = first_launch(gb), []
    for n in range(n0, n0 + k):
        q.append(hold_release(gb, n))
        drop_mugs(gb)
    return q


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_releasing_when_full_is_not_perfect_a_timed_release_is(model):
    """The owner's "too easy" check, scripted over every release frame. Of the releases that launch a drink, the
    first (A let go on the first full frame, pour_t 16) and the next 10 (settling, 16..26) are ordinary; the 5 of the
    window (27..31) are perfect; every later one is ordinary (overflow)."""
    with story(model) as gb:
        q = sweep(gb, END - FILL_FRAMES + 4)
        assert q[0] == 0, "releasing on the first full frame is not perfect"
        assert q == [0] * (WIN0 - FILL_FRAMES) + [1] * WIN + [0] * 4


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_hard_window_is_narrower(model):
    """Practice's HARD toggle (later): pour_win = POUR_WIN_HARD after the shift start; same start, 3 frames (27..29)."""
    with story(model) as gb:
        gb.write("pour_win", HARD)
        q = sweep(gb, END - FILL_FRAMES + 4)
        assert q == [0] * (WIN0 - FILL_FRAMES) + [1] * HARD + [0] * (WIN - HARD + 4)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_held_past_the_window_the_foam_runs_over_and_the_drink_is_ordinary(model):
    with story(model) as gb:
        fill_to(gb, END)
        assert gb.mem("pour_q") == 0
        e = fill_entry(gb)
        assert e["tile"] == OBJ_POUR + 2, "the overflow frame"
        gb.run(30)
        assert gb.mem("pour_t") == END, "it stays at the overflow"
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
        for _ in range(END - FILL_FRAMES + 8):
            gb.run(1)
            tiles.append(gb.oam()[OAM_FILL]["tile"])
            t = gb.mem("pour_t")
            assert gb.mem("pour_q") == (WIN0 <= t < END)
        # the fill frames, the plain full drink while it settles (8 frames), the sparkle (6), then the overflow for good
        k = tiles.index(OBJ_MUG_FILL_FULL)
        assert all(t < OBJ_MUG_FILL_FULL for t in tiles[:k])
        assert tiles[k:] == ([OBJ_MUG_FILL_FULL] * (WIN0 - FILL_FRAMES) + [OBJ_POUR] * WIN
                             + [OBJ_POUR + 2] * (len(tiles) - k - (END - FILL_FRAMES)))
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
        assert gb.mem("pour_t") == END and gb.mem("pour_q") == 0
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
        assert pour_at(gb, WIN0) == 1
        catch_delta(gb)
        gb.run(1)
        assert_cue(gb)
        assert max(oam_lines(gb)) <= 10
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
        fill_to(gb, WIN0 + 2)
        gb.run(1)
        check_golden(gb, "pour_sparkle")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_cue_golden(model):
    with story(model) as gb:
        assert pour_at(gb, WIN0 + 2) == 1
        catch_delta(gb)
        gb.run(1)
        check_golden(gb, "pour_cue")


# ---- the streak and the x2 bonus (owner 2026-10-20) --------------------------------------------------------------------
def streak_of(gb):
    return gb.mem("pour_streak")


def test_the_streak_counts_perfect_pours_in_a_row_and_a_plain_release_resets_it():
    """pour_streak: 1, 2, 3, then it stays at 3; a mug's quality: 1 for the first two, 3 (perfect and doubled) from the third; any other launch resets
    it to 0 and the next perfect pour starts again at 1. The chime follows: SFX_PERFECT every time, never the launch's sweep."""
    for model in ("dmg", "cgb"):
        with story(model) as gb:
            f0 = first_launch(gb)                  # (its trial launches are ordinary ones: measure once, so they do not break the streaks below)
            fp = f0 + WIN0 - FILL_FRAMES
            assert streak_of(gb) == 0
            seen = []
            for _ in range(5):
                p0 = sfx(gb, SFX_PERFECT)
                seen.append((hold_release(gb, fp, True), streak_of(gb), sfx(gb, SFX_PERFECT) - p0))
                drop_mugs(gb)
            assert seen == [(1, 1, 1), (1, 2, 1), (3, 3, 1), (3, 3, 1), (3, 3, 1)], seen
            l0 = sfx(gb, SFX_LAUNCH)
            assert hold_release(gb, f0, True) == 0 and streak_of(gb) == 0 and sfx(gb, SFX_LAUNCH) == l0 + 1
            drop_mugs(gb)
            assert hold_release(gb, fp, True) == 1 and streak_of(gb) == 1


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_streak_resets_when_a_shift_starts_and_when_a_life_is_lost(model):
    with story(model) as gb:
        gb.write("pour_streak", 2)
        inject_mug(gb, 0, 17)                      # a full mug at the left end: it falls off and breaks
        run_until(gb, lambda: state(gb) != PLAYING, 60)
        assert streak_of(gb) == 0, "a lost life ends the streak"
    with story(model, 1) as gb:
        assert streak_of(gb) == 0, "a new shift starts with none"


def bonus_run(model):
    """Five perfect pours in a row, each caught by its own patron: [(the bonus scored at the catch, the cue's frames at the catch)] and the serve score."""
    out = []
    with story(model) as gb:
        s = gb.mem("serve_score")
        fp = first_launch(gb) + WIN0 - FILL_FRAMES
        drop_mugs(gb)
        for _ in range(5):
            assert hold_release(gb, fp) == 1
            n0 = gb.mem("perfect_n")
            d = catch_delta(gb)
            out.append((d, gb.mem("cue_t")))
            gb.run(1)
            assert_cue(gb)
            assert gb.mem("perfect_n") == n0 + 1
            run_until(gb, lambda: gb.mem("cue_t") == 0, 120)
            drop_mugs(gb)
            set_patron(gb, 0, 64)
            gb.run(2)
    return out, s


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_pours_one_and_two_score_the_normal_bonus_and_three_on_score_double_that(model):
    """The perfect pour's bonus (PERFECT_MULT x the serve score) is doubled from the 3rd perfect pour in a row; the serve itself is not."""
    out, s = bonus_run(model)
    assert [d for d, _ in out] == [2 * s, 2 * s, 4 * s, 4 * s, 4 * s], (out, s)
    cue = GAME.get("CUE_FRAMES", 48)
    assert [t > 48 for _, t in out] == [False, False, True, True, True], "the doubled bonus's pop lasts longer"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_x2_pop_rises_a_little_then_holds_beside_the_mug_and_ends_within_a_second(model):
    with story(model) as gb:
        fp = first_launch(gb) + WIN0 - FILL_FRAMES
        drop_mugs(gb)
        for _ in range(3):
            assert hold_release(gb, fp) == 1
            ys = []
            catch_delta(gb)
            for _ in range(70):
                gb.run(1)
                o = gb.oam()[OAM_CUE]
                ys.append(o["y"] if o["tile"] == OBJ_CUE else 0)
            drop_mugs(gb)
            set_patron(gb, 0, 64)
            gb.run(2)
            shown = [y for y in ys if y]
            if _ < 2:
                assert max(shown) - min(shown) == 0, "the plain cue holds still"
        assert 3 <= max(shown) - min(shown) <= 4, f"the doubled pop rises a few px ({shown})"
        assert ys.count(0) > 0 and ys[-1] == 0, "and is gone within 70 frames"
        assert len(shown) <= 64


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_classic_has_no_perfect_pours_and_no_streak(model):
    """CLASSIC stays as it was: a release at any frame is an ordinary launch, no chime, no streak, no bonus, no cue."""
    from test_classic_mode import classic_at
    from test_scores import booted
    gb = booted(model)
    classic_at(gb, 1)
    gb.write("intro_timer", 255)
    set_patron(gb, 0, 64)
    gb.run(2)
    p0 = sfx(gb, SFX_PERFECT)
    for n in (FILL_FRAMES + 1, WIN0 - FILL_FRAMES + FILL_FRAMES, END - 1):
        assert hold_release(gb, n, raw=True) in (0, None)
        drop_mugs(gb)
    assert streak_of(gb) == 0 and sfx(gb, SFX_PERFECT) == p0 and gb.mem("perfect_n") == 0
    gb.stop()
