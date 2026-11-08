"""CONTINUE after quitting mid-shift (owner 2026-10-17: he quit in the Igloo's first shift, CONTINUE took him to chapter 2).

Two ways to be in a chapter's first shift: a real run (the progress is saved when the chapter before was cleared: CONTINUE returns to the
chapter, its PRE scene / Opening) and a debug-select run (save_lock: nothing is saved, so CONTINUE used to offer the real save's chapter:
the owner had cleared one chapter, the Igloo was a debug jump). A quit debug-select run now resumes at its chapter and step; the real save
is untouched."""
import pytest
import test_story as ts
from conftest import POS_OF, K_CONTINUE, K_STORY, menu_items, menu_tap, title_pick
from test_debug import chap, open_on, pos, tap
from test_flow import GS_GOAL, TITLE, run_until, state
from test_pause import open_pause, quit_yes, settled
from test_scores import booted, saved_story, v7_image
from test_sound import save_ram

pytestmark = pytest.mark.timeout(300)


def quit_to_title(gb):
    gb.run(60)
    open_pause(gb)
    quit_yes(gb)
    settled(gb, TITLE)


def continue_(gb):
    title_pick(gb, ts.K_PLAY, K_CONTINUE, press=False)
    assert K_CONTINUE in menu_items(gb), "CONTINUE is offered"
    menu_tap(gb, "a")
    ts.through_the_map(gb)                        # (CONTINUE lands on the story map: A there goes on, src/smap.c)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("c", range(1, 10))
def test_quit_in_a_real_chapters_first_shift_and_continue_returns_to_that_chapter(model, c):
    with ts.to_chapter(model, c) as gb:
        assert gb.mem("story_chapter") == c and gb.mem("save_lock") == 0
        quit_to_title(gb)
        continue_(gb)
        run_until(gb, lambda: state(gb) == GS_GOAL or gb.mem("story_phase") == ts.SP_SCENE, 120)
        assert gb.mem("story_chapter") == c, (gb.mem("story_chapter"), gb.mem("story_progress"), gb.mem("story_reached"))


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("c", range(10))
def test_quit_in_a_debug_selected_first_shift_and_continue_resumes_it_and_saves_nothing(model, c):
    ram = v7_image([], story=1, step=0)                    # (a real save: chapter 1 cleared, the Stadium is next)
    with booted(model, ram) as gb:
        open_on(gb, K_STORY)
        for _ in range(POS_OF[c]):                         # (the box steps through the chapters of the story's order; c is the venue)
            chap(gb, 1)
        while gb.mem("debug_pos") != ts.SHIFT_STEP[0] + 1:
            pos(gb, 1)
        tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_GOAL, 60)
        gb.run(3)
        assert gb.mem("save_lock") == 2 and gb.mem("story_chapter") == c
        ts.to_goal(gb)
        quit_to_title(gb)
        continue_(gb)
        run_until(gb, lambda: state(gb) == GS_GOAL, 120)
        gb.run(3)
        assert (gb.mem("story_chapter"), gb.mem("story_step"), gb.mem("story_on")) == (c, ts.SHIFT_STEP[0], 1)
        assert gb.mem("save_lock") == 2 and gb.mem("lives") == 3
        ts.to_goal(gb)
        quit_to_title(gb)
        assert gb.mem("story_chapter") & 0x80, "a second quit can be continued again"
        assert saved_story(save_ram(gb)) == (1, 0), "the real save is as it was"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_no_debug_run_no_phantom_continue(model):
    with booted(model, None) as gb:
        title_pick(gb, ts.K_PLAY, press=False)
        assert K_CONTINUE not in menu_items(gb)
