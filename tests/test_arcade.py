# The three modes, P2: ARCADE is the story's playable sequence played arcade style (src/story.c story_arc): no scene,
# portrait or story text; each venue's steps in story order with the story's rules; 3 lives for the whole run, extra
# lives at 20,000 and every 40,000 after (at most 4); a bonus round after every venue (rotating); after the space
# lounge "LOOP 2" and the saloon again, harder; game over -> initials -> the ARCADE top 5; nothing saved or unlocked.
import pytest
from conftest import GAME, check_golden, hold_stage_anim, title_arcade
from test_flow import (GAME_OVER, GS_GOAL, GS_STORY, LEVEL_CLEAR, LIFE_LOST, PLAYING, TITLE, lose_a_life, run_until,
                       state)
from test_scores import (EMPTY, GS_INITIALS, GS_SCORES, MODE_ARCADE, MODE_STORY, booted, main_block, parse_save,
                         screen_text, set_score, table, v7_image)
from test_sound import save_ram
from test_story import (CHAPTERS, SHIFTS, banner_text, centred, hud_lives, lives_hud, shift_title, to_goal, win)

pytestmark = pytest.mark.timeout(240)

BONUS, GS_MINI = 6, 13
TUNE_VENUE0 = 5


def score(gb):
    return int.from_bytes(gb.read("score", 4), "little")


def start_arcade(model, ram=None):
    rom = booted(model, ram)
    hold_stage_anim(rom)
    title_arcade(rom)
    run_until(rom, lambda: state(rom) == GS_GOAL, 60)
    rom.run(3)
    return rom


def finish_step(gb):
    """Past the goal banner, the step won at once (a shift's goal met, a boss satisfied); stops at LEVEL_CLEAR."""
    if state(gb) == GS_GOAL:
        to_goal(gb)
    if gb.mem("boss_on"):
        gb.write("boss_hook", 3)
    else:
        win(gb, gb.mem("story_chapter"), gb.mem("story_shift"))
    run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 200)
    gb.run(3)


def finish_venue(gb):
    """Every step of the venue (from its current goal banner) up to its bonus round; the banners seen."""
    seen = []
    while True:
        assert state(gb) in (GS_GOAL, PLAYING)
        seen.append(banner_text(gb, 1))
        finish_step(gb)
        cleared = banner_text(gb, 1)
        run_until(gb, lambda: state(gb) in (GS_GOAL, BONUS, GS_MINI), 400)
        assert state(gb) != GS_MINI, "no mini-game is built yet"
        gb.run(3)
        if state(gb) == BONUS:
            return seen, cleared


def finish_bonus(gb):
    gb.write("bonus_phase", 4)
    gb.write("bonus_timer", 129)
    run_until(gb, lambda: state(gb) == GS_GOAL, 200)
    gb.run(3)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_arcade_starts_at_the_saloon_s_opening_banner_with_no_scene(model):
    with start_arcade(model) as gb:
        assert gb.mem("play_mode") == MODE_ARCADE and gb.mem("story_arc") == 1 and gb.mem("save_lock") == 1
        assert gb.mem("story_chapter") == 0 and gb.mem("story_shift") == 0 and gb.mem("story_step") == 0
        assert gb.mem("cur_group") == 0 and gb.mem("level") == 1 and gb.mem("lives") == 3 and score(gb) == 0
        assert int.from_bytes(gb.read("extra_at", 4), "little") == 20000
        assert banner_text(gb, 1) == centred(shift_title(0, 0)) and banner_text(gb, 2) == centred(SHIFTS[0][0]["line1"])
        assert gb.mem("story_phase") == 2 and gb.mem("story_scene") == 0, "the goal banner, no scene"
        check_golden(gb, "arcade_start")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_venues_in_story_order_lives_carry_and_a_bonus_round_after_each(model):
    with start_arcade(model) as gb:
        to_goal(gb)
        lose_a_life(gb)
        run_until(gb, lambda: state(gb) == PLAYING, 200)
        assert gb.mem("lives") == 2
        kinds = []
        for c in range(3):
            assert gb.mem("story_chapter") == c and gb.mem("cur_group") == CHAPTERS[c]["venue"] and gb.mem("level") == c + 1
            seen, cleared = finish_venue(gb)
            assert cleared == centred("VENUE CLEAR"), "not the story's CHAPTER CLEAR"
            assert gb.mem("bonus_round") == c + 1
            kinds.append(gb.mem("bonus_kind"))
            assert gb.mem("lives") == 2, "the run's lives: not refilled at a venue"
            finish_bonus(gb)
            assert gb.mem("story_scene") == 0, "no scene ever entered"
        assert kinds == [0, 1, 2], "the rounds rotate as before"
        assert gb.mem("story_chapter") == 3 and banner_text(gb, 1) == centred(shift_title(3, 0))
        assert hud_lives(gb) == lives_hud(2)
        assert gb.mem("story_progress") == 0 and gb.mem16("tune_unlocked") == 1, "nothing saved, nothing unlocked"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_after_the_space_lounge_loop_2_and_the_saloon_harder(model):
    from test_flow import loop_row
    with start_arcade(model) as gb:
        to_goal(gb)
        gb.write("story_chapter", 9)               # (the space lounge's last step: a VENUE CLEAR ends the venue)
        gb.write("story_step", 4)
        win(gb, 0, 0)
        run_until(gb, lambda: state(gb) == BONUS, 400)
        gb.write("bonus_phase", 4)
        gb.write("bonus_timer", 129)
        run_until(gb, lambda: state(gb) == GS_GOAL, 200)
        gb.run(3)
        assert gb.mem("arc_loop") == 2 and gb.mem("story_phase") == 6, "SP_LOOP"
        assert banner_text(gb, 2) == centred("LOOP 2") and banner_text(gb, 1) == centred("")
        assert gb.mem("story_chapter") == 0 and gb.mem("cur_group") == 0 and gb.mem("level") == 11
        assert gb.mem("arcade_loop") == 2
        row = loop_row(11)
        assert gb.mem16("spawn_interval") == row[4] * SHIFTS[0][0]["spawn"] // 100, "the loop's spawn, then the shift's"
        assert gb.mem("empty_gap") == row[8]
        check_golden(gb, "arcade_loop")
        run_until(gb, lambda: gb.mem("story_phase") == 2, 140)   # then the goal banner, as on every shift
        gb.run(3)
        assert banner_text(gb, 1) == centred(shift_title(0, 0)) and banner_text(gb, 2) == centred(SHIFTS[0][0]["line1"])
        to_goal(gb)
        assert state(gb) == PLAYING


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_extra_lives_at_20000_and_every_40000_at_most_four(model):
    with start_arcade(model) as gb:
        to_goal(gb)
        set_score(gb, 19_999)
        for i in range(6):                          # (the HUD digits are not poked: add_score works on `score`)
            gb.write(gb.addr("score_digits") + i, [0, 1, 9, 9, 9, 9][i])
        win(gb, 0, 0)                               # LEVEL CLEAR's 1000: past 20,000
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 30)
        gb.run(3)
        assert gb.mem("lives") == 4 and int.from_bytes(gb.read("extra_at", 4), "little") == 60_000
        assert hud_lives(gb) == lives_hud(4)
        run_until(gb, lambda: state(gb) == GS_GOAL, 400)
        to_goal(gb)
        set_score(gb, 59_999)
        win(gb, 0, 1)
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 30)
        assert gb.mem("lives") == 4, "at most four"
        assert int.from_bytes(gb.read("extra_at", 4), "little") == 100_000


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_no_extra_lives_in_the_story_or_the_harness(model):
    from conftest import K_PLAY, K_STORY, title_level, title_pick
    with booted(model) as gb:
        title_pick(gb, K_PLAY, K_STORY)
        run_until(gb, lambda: state(gb) == GS_STORY, 30)
        assert int.from_bytes(gb.read("extra_at", 4), "little") == 0
    with booted(model) as gb:
        title_level(gb)
        run_until(gb, lambda: state(gb) == PLAYING, 30)
        assert int.from_bytes(gb.read("extra_at", 4), "little") == 0


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_game_over_initials_and_the_arcade_top_5_and_nothing_else_saved(model):
    ram = v7_image([("ABC", 500)], story=3, step=1, tunes=0x21, story_tbl=[("STO", 900)])
    with start_arcade(model, ram) as gb:
        to_goal(gb)
        set_score(gb, 777)
        for n in range(3):
            lose_a_life(gb)
            if n < 2:
                run_until(gb, lambda: state(gb) == PLAYING, 200)
        run_until(gb, lambda: state(gb) == GAME_OVER, 200)
        assert gb.mem("story_on") == 0 and gb.mem("score_tbl") == MODE_ARCADE and gb.mem("new_rank") == 0
        assert table(gb)[:2] == [("AAA", 777), ("ABC", 500)] and table(gb, MODE_STORY)[0] == ("STO", 900)
        gb.press("start", 2)
        run_until(gb, lambda: state(gb) == GS_INITIALS, 30)
        gb.press("a", 2)
        run_until(gb, lambda: state(gb) == GS_SCORES, 30)
        gb.run(2)
        assert screen_text(gb, 3).strip() == "ARCADE HIGH SCORES"
        gb.press("start", 2)
        run_until(gb, lambda: state(gb) == TITLE, 30)
        out = save_ram(gb)
    assert parse_save(out)[:2] == [("AAA", 777), ("ABC", 500)]
    assert main_block(out) == (3, 1, 0x21), "the story progress and the unlocks untouched (the saloon's tune heard)"
    assert parse_save(out, MODE_STORY)[0] == ("STO", 900)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_timed_goal_out_of_lives_is_game_over_not_try_again(model):
    timed = [(c, k) for c in range(10) for k in range(3) if SHIFTS[c][k]["secs"]]
    assert timed
    with start_arcade(model) as gb:
        to_goal(gb)
        gb.write("story_timer", 2)                  # (the Opening's goal with a clock poked on: as a timed shift's)
        gb.write("intro_timer", 0)
        gb.write("lives", 1)
        run_until(gb, lambda: state(gb) == GAME_OVER, 30)
        assert gb.mem("lives") == 0 and gb.mem("story_fails") == 0, "no TRY AGAIN in ARCADE"
    with start_arcade(model) as gb:                 # lives left: TRY AGAIN and the shift again, as in the story
        to_goal(gb)
        gb.write("story_timer", 2)
        gb.write("intro_timer", 0)
        run_until(gb, lambda: state(gb) == GS_STORY, 30)
        assert gb.mem("lives") == 2 and gb.mem("story_fails") == 1 and banner_text(gb, 1) == centred("TRY AGAIN")
        gb.press("a", 2)
        run_until(gb, lambda: state(gb) == GS_GOAL, 30)
        assert gb.mem("story_shift") == 0 and gb.mem("lives") == 2
