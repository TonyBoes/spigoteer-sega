"""A tune unlock heard IN a shift is not written to the save RAM mid-frame (the save took 113 scanlines, STORY's worst frame):
tune_heard marks it (save_migrated bit 7) and the save comes at the next quiet moment: any story_save (a shift or chapter clear),
the next shift's start (LCD off) or the title (a quit, the last game over). Unlocks heard in a scene or a menu are still saved at
once (tests/test_jukebox.py). What a power-off in between loses: that one unlock, until the next of these."""
import pytest
from test_flow import GS_STORY, TITLE, run_until, state
from test_jukebox import TUNE_COUNT  # noqa: F401
from test_pause import open_pause, quit_yes, settled
from test_scores import saved_tunes
from test_sound import save_ram
from test_story import break_a_glass, freeze_over, to_chapter, try_again, win

DIRTY = 0x80
TUNE_CLEAR, TUNE_OVER = 1, 2


def pending(gb):
    return bool(gb.mem("save_migrated") & DIRTY)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_jingle_first_heard_in_a_shift_waits_for_the_shift_clear_save(model):
    with to_chapter(model, 0) as gb:
        assert not gb.mem16("tune_unlocked") & 1 << TUNE_CLEAR and not pending(gb)
        win(gb, 0, 0)
        run_until(gb, lambda: gb.mem("cur_tune") == TUNE_CLEAR, 30)          # SHIFT CLEAR's jingle, mid-shift
        assert gb.mem16("tune_unlocked") & 1 << TUNE_CLEAR and pending(gb)
        ram = save_ram(gb)
    assert not saved_tunes(ram) & 1 << TUNE_CLEAR, "not written mid-shift"
    with to_chapter(model, 0) as gb:
        win(gb, 0, 0)
        run_until(gb, lambda: gb.mem("cur_tune") == TUNE_CLEAR, 30)
        run_until(gb, lambda: not pending(gb), 800)                          # story_level_done's story_save
        assert gb.mem16("tune_unlocked") & 1 << TUNE_CLEAR
        ram = save_ram(gb)
    assert saved_tunes(ram) & 1 << TUNE_CLEAR, "saved with the shift's progress"


def lose_the_shift(gb):
    for _ in range(2):
        break_a_glass(gb)
        freeze_over(gb)
    break_a_glass(gb)
    run_until(gb, lambda: gb.mem("cur_tune") == TUNE_OVER, 300)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_game_over_tune_is_saved_when_the_shift_starts_again(model):
    with to_chapter(model, 0) as gb:
        lose_the_shift(gb)
        assert gb.mem16("tune_unlocked") & 1 << TUNE_OVER and pending(gb)
        ram = save_ram(gb)
    assert not saved_tunes(ram) & 1 << TUNE_OVER, "not written mid-shift"
    with to_chapter(model, 0) as gb:
        lose_the_shift(gb)
        run_until(gb, lambda: state(gb) == GS_STORY, 200)
        try_again(gb)                                                        # the venue again: its screen loads with the LCD off
        assert not pending(gb)
        ram = save_ram(gb)
    assert saved_tunes(ram) & 1 << TUNE_OVER


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_quit_from_the_pause_menu_saves_the_waiting_unlock(model):
    with to_chapter(model, 0) as gb:
        gb.run(30)
        gb.write(gb.addr("tune_unlocked") + 1, gb.mem("tune_unlocked") >> 8 | 0x40)   # (a tune first heard in the shift: tune 14)
        gb.write("save_migrated", DIRTY)
        open_pause(gb)
        quit_yes(gb)
        settled(gb, TITLE)
        assert not pending(gb)
        ram = save_ram(gb)
    assert saved_tunes(ram) & 0x4000, "written by the title's flush"
