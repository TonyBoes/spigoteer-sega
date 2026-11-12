# The one-line menu style the three screens share (src/oneline.c, src/oneline.h; owner Q38-Q45): BONUS > SOUNDTRACK, MINI GAMES (Practice) and BOSS RUSH's
# list. The same rules on all three, DMG and Color: LEFT / RIGHT step one entry with wrap and hold-to-repeat (the first repeat 18 frames after the press,
# then every 5), UP / DOWN never repeat, the selection line "< NAME >" is a band between two light lines with blank rows around it, its arrows bob a pixel
# every 16 frames and kick out for 7 on a press, the header has the title and "n / N", the hint row is "(A) PLAY (B) BACK". What each screen shows is in
# tests/test_jukebox.py, test_mg_list.py and test_rush.py.
import pytest
from conftest import K_BONUS, K_SOUNDTRACK, K_MINIGAMES, ROOT
from ol_helpers import (ARROW_L, ARROW_L_OUT, ARROW_R, ARROW_R_OUT, BLANK, FONT, ROW_BAND, ROW_HINT, arrows, arrows_out, band_rows_ok, header, hint, hold_changes,
                        selection, text, attr, header_text)
from test_flow import run_until, state, tilemap_row
from test_scores import booted, v7_image
from conftest import title_pick
import test_rush
from test_rush import BUILT, LIST_SEL, RUSH_AT
from test_jukebox import ALL, GS_JUKEBOX, TUNE_COUNT
from test_mg import GS_MGLIST

OL_AT = 364                                    # src/scratch.h SCR_OL_AT: struct ol_state { hold, flash, key, bob, t }


def ol(gb, field):
    return gb.mem(gb.addr("story_scratch") + OL_AT + field)


def open_soundtrack(gb):
    title_pick(gb, K_BONUS, K_SOUNDTRACK)
    run_until(gb, lambda: state(gb) == GS_JUKEBOX, 30)
    gb.run(8)


def open_practice(gb):
    title_pick(gb, K_BONUS, K_MINIGAMES)
    run_until(gb, lambda: state(gb) == GS_MGLIST and gb.pb.memory[0xFF40] & 0x80, 30)
    gb.run(8)


def open_rush(gb):
    test_rush.to_list(gb)
    gb.run(8)


# name: (opener, the selection's address, entries, the UP / DOWN jump, the title, a cartridge image)
SCREENS = {
    "soundtrack": (open_soundtrack, lambda gb: gb.addr("jb_sel"), lambda gb: TUNE_COUNT, 5, "SOUNDTRACK", lambda: v7_image([], tunes=ALL)),
    "practice": (open_practice, lambda gb: gb.addr("ml_sel"), lambda gb: gb.mem("ml_n"), None, "MINI GAMES", lambda: None),
    "rush": (open_rush, lambda gb: gb.addr("story_scratch") + RUSH_AT + LIST_SEL, lambda gb: len(BUILT), 5, "BOSS RUSH", lambda: None),
}


@pytest.fixture(params=["dmg", "cgb"])
def model(request):
    return request.param


@pytest.fixture(params=sorted(SCREENS))
def screen(request):
    return request.param


@pytest.fixture
def gb(screen, model):
    opener, _, _, _, _, ram = SCREENS[screen]
    with booted(model, ram()) as g:
        opener(g)
        yield g


def sel(gb, screen):
    return gb.mem(SCREENS[screen][1](gb))


def entries(gb, screen):
    return SCREENS[screen][2](gb)


def tap(gb, b):
    gb.press(b, 2)
    gb.run(3)


@pytest.mark.only_model('dmg')
def test_left_and_right_step_one_entry_and_wrap(gb, screen):
    n = entries(gb, screen)
    assert sel(gb, screen) == 0
    tap(gb, "left")
    assert sel(gb, screen) == n - 1, "wraps to the last"
    tap(gb, "right")
    assert sel(gb, screen) == 0, "and back to the first"
    for k in range(1, n):
        tap(gb, "right")
        assert sel(gb, screen) == k
    tap(gb, "right")
    assert sel(gb, screen) == 0


@pytest.mark.parametrize("button, step", [("right", 1), ("left", -1)])
def test_a_held_direction_repeats_after_18_frames_then_every_5(gb, screen, button, step):
    n = entries(gb, screen)
    if step < 0:
        tap(gb, "left")                                  # (from the last entry, so the walk down never meets 0 within the window)
    clock = gb.addr("story_scratch") + OL_AT + 4          # the game's frame count on the screen (ol_state.t)
    changes = hold_changes(gb, button, SCREENS[screen][1](gb), 90, clock)
    first = changes[0]
    diff = [(b - a) % 256 for a, b in zip(changes, changes[1:])]
    assert diff[0] in (18, 19) and set(diff[1:]) == {5}, (changes, diff)   # (the press frame's sample can be one game frame early: the count is read after the frame, the clock ticks last)
    assert len(changes) >= 2 + (90 - 18) // 5 - 3, changes
    gb.run(30)
    final = sel(gb, screen)
    assert (final - (n - 1 if step < 0 else 0)) % n == (step * len(changes)) % n, "every change was one entry"
    assert len(hold_changes(gb, button, SCREENS[screen][1](gb), 10)) == 1, "a new press starts the delay again"


@pytest.mark.only_model('dmg')
def test_up_and_down_do_not_repeat(gb, screen):
    changes = hold_changes(gb, "down", SCREENS[screen][1](gb), 60)
    assert len(changes) == 1, changes
    changes = hold_changes(gb, "up", SCREENS[screen][1](gb), 60)
    assert len(changes) == 1, changes


def test_the_band_header_and_hint_row(gb, screen):
    title = SCREENS[screen][4]
    assert band_rows_ok(gb), "the panel's two light lines above and below the name"
    assert set(tilemap_row(gb, 5, 0, 20)) == {BLANK}, "a blank row under the band"
    if screen == "practice":
        assert header(gb) == header_text("MINI GAMES", "").replace("MINI GAMES", "MINI GAMES  NORMAL"), header(gb)
    else:
        assert header(gb) == header_text(title, f"1 / {entries(gb, screen)}")
    assert len(selection(gb)) > 3 and selection(gb) != "?"
    assert hint(gb)[:6] == "@ PLAY" and hint(gb).endswith("$ BACK"), hint(gb)
    assert text(gb, ROW_HINT) == " " * 2 + "@ PLAY" + " " * 3 + "$ BACK", repr(text(gb, ROW_HINT))
    assert not gb.visible_sprites(), "no sprite on a one-line screen"
    if gb.model_name == "cgb":
        assert [attr(gb, 2, c) for c in range(20)] == [6] * 20 and [attr(gb, 4, c) for c in range(20)] == [6] * 20
        mid = [attr(gb, ROW_BAND, c) for c in range(20)]
        assert mid[1:19] == [6] * 18 and mid[0] == mid[19] != 6, "the arrows' cells have the gold palette, the rest the panel's"


@pytest.mark.only_model('dmg')
def test_the_arrows_bob_a_pixel_every_16_frames(gb, screen):
    seen = []
    for _ in range(70):
        gb.run(1)
        seen.append((ol(gb, 3), arrows_out(gb)))
    assert {s for _, s in seen} == {(False, False), (True, True)}, "both arrows out together, then both in"
    runs, cur = [], 1
    for (a, _), (b, _) in zip(seen, seen[1:]):
        if a == b:
            cur += 1
        else:
            runs.append(cur)
            cur = 1
    assert len(runs) >= 3 and set(runs[1:]) == {16}, runs   # (the first run began before the watch did)


def test_a_press_kicks_its_arrow_out_for_7_frames(gb, screen):
    def quiet():                                          # (the bob is in and just turned: 16 frames of it ahead)
        while not (ol(gb, 3) == 0 and ol(gb, 4) & 15 == 2 and ol(gb, 1) == 0):
            gb.run(1)

    def watch(button):
        gb.pb.button_press(button)
        gb.pb.tick(1, False)
        gb.pb.button_release(button)
        seen = []
        for _ in range(12):
            gb.pb.tick(1, False)
            seen.append(arrows_out(gb))
        return seen

    quiet()
    seen = watch("right")
    assert not any(l for l, _ in seen), "only the pressed side kicks"
    assert 5 <= sum(r for _, r in seen) <= 9, ("the right arrow stays out about 7 frames (the screen follows the state through the VBlank queue)", seen)
    quiet()
    seen = watch("left")
    assert not any(r for _, r in seen) and 5 <= sum(l for l, _ in seen) <= 9, seen


@pytest.mark.only_model('dmg')
@pytest.mark.parametrize("screen", [s for s in sorted(SCREENS) if s != "practice"])   # (Practice jumps between its two groups: tests/test_mg_list.py)
def test_up_and_down_jump(gb, screen):
    n, jump = entries(gb, screen), SCREENS[screen][3]
    tap(gb, "down")
    assert sel(gb, screen) == jump % n
    tap(gb, "down")
    assert sel(gb, screen) == (2 * jump) % n
    tap(gb, "up")
    tap(gb, "up")
    assert sel(gb, screen) == 0
    tap(gb, "up")
    assert sel(gb, screen) == (n - jump) % n, "wraps"


@pytest.mark.only_model('dmg')
def test_the_counter_follows_the_selection(gb, screen):
    n = entries(gb, screen)
    for k in range(min(n, 4)):
        want = f"{k + 1} / {n}"
        if screen == "practice":
            assert want in text(gb, 7)
        else:
            assert header(gb).endswith(want), (header(gb), want)
        tap(gb, "right")
        gb.run(6)
