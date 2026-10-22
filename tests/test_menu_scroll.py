# Scrolling the full-screen lists quickly (the Practice list, the Boss Rush list, the Soundtrack; owner 2026-10-16: "scrolling the
# fullscreen menus quickly causes slowdown"). A row's build costs ~10-15k cycles, and a step used to build four of them (the info lines,
# the header, the window's six lines on a scroll): the frame ran past its VBlank. Now a step builds only what changed and at most two rows
# a frame, the window's pending lines are remembered, not restarted. This mashes Down and Up (a tap every 2, 3 and 4 frames: the game
# has no auto-repeat, so mashing is the fastest scrolling there is) and asserts that no frame's work ran past the next VBlank
# (perf_end_last, main.c: the line the frame's logic and music tick ended on; > 143 is late) and that after the last tap the screen
# shows the selected line's details (the rows that were left pending catch up).
import pytest
from conftest import K_BONUS, K_BOSSRUSH, K_MINIGAMES, K_SOUNDTRACK, hold_stage_anim, menu_tap, menu_to, title_pick
from test_flow import tilemap_row

SECONDS = 6
LATE = 143
SCREENS = {"mglist": (K_MINIGAMES, 15), "rush": (K_BOSSRUSH, None), "soundtrack": (K_SOUNDTRACK, 14)}


def open_screen(gb, screen, again=False):
    hold_stage_anim(gb)
    if again:                                   # (B left to the BONUS submenu)
        menu_to(gb, SCREENS[screen][0])
        menu_tap(gb, "a")
    else:
        title_pick(gb, K_BONUS, SCREENS[screen][0])
    gb.run(30)
    if screen == "rush":                        # the menu's CHOOSE: the list of bosses
        menu_tap(gb, "down")
        menu_tap(gb, "a")
        gb.run(30)


def leave(gb, screen):
    for _ in range(2 if screen == "rush" else 1):
        menu_tap(gb, "b")
        gb.run(40)


def screen_text(gb):
    """The whole tilemap but the selection line's two arrows (row 3, columns 0 and 19: they bob with the time on the screen)."""
    rows = [list(tilemap_row(gb, y, 0, 20)) for y in range(18)]
    rows[3][0] = rows[3][19] = 0
    return [tuple(r) for r in rows]


def mash(gb, key, period, seconds=SECONDS):
    """Tap `key` every `period` frames; the latest end line seen and how many frames ran late."""
    worst = late = 0
    for i in range(seconds * 60):
        if i % period == 0:
            gb.hold(key)
        elif i % period == 1:
            gb.release(key)
        gb.run(1)
        e = gb.mem16("perf_end_last")
        worst = max(worst, e)
        late += e > LATE
    gb.release(key)
    return worst, late


@pytest.mark.parametrize("screen", sorted(SCREENS))
@pytest.mark.parametrize("period", [2, 3, 4])
def test_mashing_a_list_never_runs_a_frame_late(boot, screen, period):
    open_screen(boot, screen)
    for key in ("down", "up", "right", "left"):   # (the jumps and the steps wrap past either end)
        worst, late = mash(boot, key, period)
        assert late == 0, (screen, key, period, worst)
        assert worst <= LATE


@pytest.mark.parametrize("screen", sorted(SCREENS))
def test_a_mashed_list_settles_to_the_same_screen_as_a_calm_one(boot, screen):
    """The pending lines catch up: the screen after mashing equals the screen after the same number of calm taps."""
    open_screen(boot, screen)
    taps = 7
    for i in range(taps):                       # a tap every 2 frames
        boot.hold("down"); boot.run(1); boot.release("down"); boot.run(1)
    boot.run(20)
    fast = screen_text(boot)
    leave(boot, screen)                         # back to the title, then in again: the list is rebuilt whole around the same line
    open_screen(boot, screen, again=True)
    for i in range(0 if screen == "mglist" else taps):      # (the Practice list keeps its line; the others start from the first)
        boot.hold("down"); boot.run(1); boot.release("down"); boot.run(12)
    boot.run(20)
    assert screen_text(boot) == fast


@pytest.mark.parametrize("period", [2, 4])
def test_mashing_the_soundtrack_while_a_tune_plays_never_runs_a_frame_late(boot, period):
    """The bars move every frame while a tune plays (up to four 15-tile runs through the VBlank queue): selecting at full speed on top of that is
    still on time."""
    open_screen(boot, "soundtrack")
    menu_tap(boot, "a")                         # (the title tune, the only one unlocked on a fresh cartridge)
    boot.run(20)
    assert boot.mem("cur_tune") == 0
    for key in ("right", "down", "left", "up"):
        worst, late = mash(boot, key, period)
        assert late == 0, (key, period, worst)
