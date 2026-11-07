# QUIT TO MAP and RESUME (owner 2026-11-05): in a STORY chapter the pause menu's QUIT goes to the story map, Sal at the venue; A there offers
# RESUME / ENTER / BACK. RESUME restarts the shift (or boss fight, or mini-game) that was quit from its start, with the lives and the score it
# began with (HRAM 0xFFF5-0xFFFA, written when the step starts: story.c step_start); ENTER starts the venue over as A at the next venue does;
# BACK closes the panel. Everything else (ARCADE, CLASSIC, BOSS RUSH, a play from the map, BONUS > MINI GAMES) quits as before.
import pytest
import test_story as ts
from conftest import POS_OF, hold_stage_anim
from test_flow import GS_GOAL, GS_STORY, PLAYING, run_until, state
from test_mg import GS_MINI
from test_pause import open_pause, quit_yes, sv_image, tap, win_text as pause_text
from test_scores import set_score
from test_story_map import SP_MAP, tap as mtap, win_text

MODES = ["dmg", "cgb"]
HRAM_RS = 0xFFF5            # lives, step, score x4 (story.c RS_*)


def to_map_by_quit(gb):
    open_pause(gb)
    quit_yes(gb)
    run_until(gb, lambda: state(gb) == GS_STORY and gb.mem("story_phase") == SP_MAP, 200)
    gb.run(100)


def sc(gb):
    return int.from_bytes(gb.read("score", 4), "little")


def panel(gb):
    mtap(gb, "a", 20)
    gb.run(10)
    return [win_text(gb, r) for r in range(1, 4)]


def begin(model, c=2, k=1, score=12345):
    gb = ts.to_shift(model, c, k, image=sv_image(POS_OF[c], 1, POS_OF[c], score))
    return gb


@pytest.mark.parametrize("model", MODES)
def test_the_story_pause_menu_says_quit_to_map_and_arcade_says_quit_to_menu(model):
    with begin(model) as gb:
        tap(gb, "start", 3)
        assert [pause_text(gb, r) for r in (2, 3)] == ["> RESUME", "QUIT TO MAP"]


@pytest.mark.parametrize("model", MODES)
def test_quit_goes_to_the_map_at_the_venue_and_resume_restarts_the_shift_with_its_start_state(model):
    with begin(model) as gb:
        c = gb.mem("story_chapter")
        start = dict(step=gb.mem("story_step"), lives=gb.mem("lives"), timer=gb.mem16("story_timer"), score=sc(gb),
                     shift=gb.mem("story_shift"), goal=gb.mem("story_goal"))
        gb.run(240)
        assert gb.mem16("story_timer") != start["timer"] or start["timer"] == 0, "the shift ran on"
        set_score(gb, 54321)
        gb.write("lives", 1)
        gb.run(2)
        open_pause(gb)
        quit_yes(gb)
        run_until(gb, lambda: state(gb) == GS_STORY and gb.mem("story_phase") == SP_MAP, 200)
        gb.run(100)
        assert gb.mem("story_on") == 1 and gb.mem("smap_stop") == c and gb.mem("smap_flags") & 8
        assert gb.mem("boss_on") == 0
        assert panel(gb) == ["RESUME", "ENTER", "BACK"], panel(gb)
        mtap(gb, "a", 2)                                   # RESUME
        run_until(gb, lambda: state(gb) == GS_GOAL, 200)
        gb.run(3)
        assert gb.mem("story_chapter") == c and gb.mem("story_step") == start["step"] and gb.mem("story_shift") == start["shift"]
        assert gb.mem("lives") == start["lives"], "the lives the shift began with"
        assert sc(gb) == start["score"], "the score the shift began with"
        assert gb.mem16("story_timer") == start["timer"], "the clock from its start"
        assert gb.read("score_digits", 6) == bytes(int(d) for d in "%06d" % start["score"])
        assert gb.mem("smap_flags") & 8 == 0
        gb.press("a", 2)
        run_until(gb, lambda: state(gb) == PLAYING, 30)
        gb.run(30)
        assert gb.mem("story_step") == start["step"] and gb.mem("lives") == start["lives"]


@pytest.mark.parametrize("model", MODES)
def test_back_closes_the_panel_and_walking_elsewhere_keeps_the_resume(model):
    with begin(model) as gb:
        to_map_by_quit(gb)
        c = gb.mem("story_chapter")
        assert panel(gb) == ["RESUME", "ENTER", "BACK"]
        mtap(gb, "down", 4)
        mtap(gb, "down", 4)
        mtap(gb, "a", 12)                                  # BACK
        assert gb.mem("overlay_on") == 0 and gb.mem("story_phase") == SP_MAP and gb.mem("smap_stop") == c
        assert gb.mem("smap_flags") & 8, "BACK keeps it"
        mtap(gb, "b", 12)
        assert gb.mem("smap_flags") & 8


@pytest.mark.parametrize("model", MODES)
def test_enter_starts_the_venue_over_from_its_start(model):
    with begin(model) as gb:
        c = gb.mem("story_chapter")
        gb.run(60)
        to_map_by_quit(gb)
        panel(gb)
        mtap(gb, "down", 4)
        mtap(gb, "a", 2)                                   # ENTER
        run_until(gb, lambda: state(gb) == GS_GOAL, 400)
        gb.run(3)
        assert gb.mem("story_chapter") == c and gb.mem("story_step") == 0 and gb.mem("lives") == 3
        assert gb.mem("smap_flags") & 8 == 0


@pytest.mark.parametrize("model", MODES)
def test_without_a_quit_a_at_the_venue_behaves_as_before(model):
    with begin(model) as gb:
        gb.write("smap_flags", 0)
        to_map_by_quit(gb)
        gb.write("smap_flags", gb.mem("smap_flags") & ~8)
        mtap(gb, "a", 20)
        assert gb.mem("overlay_on") != 3 and gb.mem("story_phase") != SP_MAP, "the venue's PRE scene, as before"


@pytest.mark.parametrize("model", MODES)
def test_junk_in_the_resume_flag_at_power_on_does_not_offer_a_resume(model):
    from conftest import K_CONTINUE, title_pick
    from test_scores import booted, v7_image
    gb = booted(model, v7_image([], story=3, step=0))
    gb.write("smap_flags", 0x08)                           # (real hardware leaves junk)
    title_pick(gb, ts.K_PLAY, K_CONTINUE, press=False)
    gb.press("a", 8)
    run_until(gb, lambda: gb.mem("story_phase") == SP_MAP and state(gb) == GS_STORY, 400)
    gb.run(100)
    assert gb.mem("smap_flags") & 8 == 0
    gb.write("smap_stop", 3)
    gb.run(2)
    mtap(gb, "a", 20)
    assert gb.mem("overlay_on") != 3 and gb.mem("story_phase") != SP_MAP, "A starts the venue: no panel"


@pytest.mark.parametrize("model", MODES)
def test_quit_from_a_boss_fight_resumes_the_shift_that_holds_it(model):
    from boss_common import fight, play
    c = sorted(ts.BOSS_BUILT)[0]
    with fight(model, c) as gb:
        play(gb)
        gb.run(40)
        assert gb.mem("boss_on") == 1
        step = gb.mem("story_step")
        assert step == ts.SHIFT_STEP[2]
        set_score(gb, 77777)
        open_pause(gb)
        quit_yes(gb)
        run_until(gb, lambda: state(gb) == GS_STORY and gb.mem("story_phase") == SP_MAP, 200)
        gb.run(100)
        assert gb.mem("boss_on") == 0 and gb.mem("smap_stop") == c and gb.mem("smap_flags") & 8
        assert panel(gb) == ["RESUME", "ENTER", "BACK"]
        mtap(gb, "a", 2)
        run_until(gb, lambda: state(gb) == GS_GOAL, 300)
        gb.run(3)
        assert gb.mem("story_step") == step and gb.mem("boss_on") == 0, "Last call again, before his fight"
        assert sc(gb) < 77777


@pytest.mark.parametrize("model", MODES)
def test_quit_from_a_story_mini_game_resumes_that_mini_game(model):
    from test_flow import LEVEL_CLEAR
    c = sorted(ts.MINI_BUILT)[0]
    with ts.to_shift(model, c, 1) as gb:
        ts.win(gb, c, 1)
        run_until(gb, lambda: state(gb) == GS_MINI, 800)
        gid, step = gb.mem("mg_id"), gb.mem("story_step")
        assert step == ts.MINI_STEP
        gb.run(60)
        tap(gb, "start", 3)
        quit_yes(gb)
        run_until(gb, lambda: state(gb) == GS_STORY and gb.mem("story_phase") == SP_MAP, 200)
        gb.run(100)
        assert gb.mem("smap_stop") == c and gb.mem("smap_flags") & 8
        assert panel(gb) == ["RESUME", "ENTER", "BACK"]
        mtap(gb, "a", 2)
        run_until(gb, lambda: state(gb) == GS_MINI, 300)
        assert gb.mem("mg_id") == gid and gb.mem("story_step") == step and gb.mem("mg_mode") == 0


# ---- every story run quits to the map: a NEW GAME run, a CONTINUE run, a debug-select run (owner bug 2026-11-05: "quitting a stage doesn't take me back to the map") ----
def debug_shift(model, c=2, k=0):
    """The debug menu's STORY box on chapter c, shift k (nothing saved: save_lock 2), in play."""
    from conftest import K_STORY
    from test_debug import chap, open_on, pos, tap as dtap
    from test_scores import booted, v7_image
    from test_story import SHIFT_STEP
    ram = v7_image([("ABC", 500)], story=1, step=1, tunes=0x21)
    gb = booted(model, ram)
    gb.ram_in = ram
    open_on(gb, K_STORY)
    for _ in range(c):
        chap(gb, 1)
    while gb.mem("debug_pos") != SHIFT_STEP[k] + 1:
        pos(gb, 1)
    dtap(gb, "a")
    run_until(gb, lambda: state(gb) == GS_GOAL, 60)
    gb.write("tip_chance", 0)
    gb.press("a", 2)
    run_until(gb, lambda: state(gb) == PLAYING, 30)
    gb.run(60)
    return gb


@pytest.mark.parametrize("model", MODES)
def test_a_debug_select_run_quits_to_the_map_resumes_and_saves_nothing(model):
    from test_scores import v7_image
    from test_sound import save_ram
    from conftest import with_unlock
    with debug_shift(model, 2, 0) as gb:
        assert gb.mem("save_lock") == 2 and gb.mem("story_on") == 1
        start = dict(step=gb.mem("story_step"), lives=gb.mem("lives"), score=sc(gb))
        set_score(gb, 4321)
        tap(gb, "start", 3)
        assert [pause_text(gb, r) for r in (2, 3)] == ["> RESUME", "QUIT TO MAP"]
        quit_yes(gb)
        run_until(gb, lambda: state(gb) == GS_STORY and gb.mem("story_phase") == SP_MAP, 200)
        gb.run(100)
        assert gb.mem("smap_stop") == 2 and gb.mem("smap_flags") & 8 and gb.mem("story_on") == 1
        assert panel(gb) == ["RESUME", "ENTER", "BACK"]
        mtap(gb, "a", 2)                                   # RESUME
        run_until(gb, lambda: state(gb) == GS_GOAL, 300)
        gb.run(3)
        assert gb.mem("story_chapter") == 2 and gb.mem("story_step") == start["step"] and gb.mem("lives") == start["lives"] and sc(gb) == start["score"]
        gb.press("a", 2)
        run_until(gb, lambda: state(gb) == PLAYING, 30)
        gb.run(30)
        open_pause(gb)
        quit_yes(gb)
        run_until(gb, lambda: state(gb) == GS_STORY and gb.mem("story_phase") == SP_MAP, 200)
        gb.run(100)
        panel(gb)
        mtap(gb, "down", 4)
        mtap(gb, "a", 2)                                   # ENTER: the chapter's PRE scene, then its first step
        run_until(gb, lambda: gb.mem("story_phase") != SP_MAP, 300)
        assert gb.mem("save_lock") == 2 and gb.mem("story_chapter") == 2
        after = save_ram(gb)
    assert after[:40] == with_unlock(gb.ram_in)[:40], "a debug-select run writes nothing"


@pytest.mark.parametrize("model", MODES)
def test_a_new_game_run_quits_to_the_map_and_resumes(model):
    with ts.start_story(model) as gb:
        for _ in range(8):
            if state(gb) == GS_GOAL:
                break
            ts.skip_scene(gb)
        assert state(gb) == GS_GOAL and gb.mem("story_chapter") == 0 and gb.mem("save_lock") == 0
        gb.press("a", 2)
        run_until(gb, lambda: state(gb) == PLAYING, 30)
        gb.run(60)
        start_lives = gb.mem("lives")
        open_pause(gb)
        quit_yes(gb)
        run_until(gb, lambda: state(gb) == GS_STORY and gb.mem("story_phase") == SP_MAP, 200)
        gb.run(100)
        assert gb.mem("smap_stop") == 0 and gb.mem("smap_flags") & 8 and gb.mem("story_on") == 1
        assert panel(gb) == ["RESUME", "ENTER", "BACK"]
        mtap(gb, "a", 2)
        run_until(gb, lambda: state(gb) == GS_GOAL, 300)
        gb.run(3)
        assert gb.mem("story_chapter") == 0 and gb.mem("lives") == start_lives


@pytest.mark.parametrize("model", MODES)
def test_a_debug_select_run_quit_to_title_from_the_map_still_offers_continue(model):
    from conftest import K_CONTINUE
    with debug_shift(model, 2, 0) as gb:
        open_pause(gb)
        quit_yes(gb)
        run_until(gb, lambda: state(gb) == GS_STORY and gb.mem("story_phase") == SP_MAP, 200)
        gb.run(100)
        mtap(gb, "start", 20)
        gb.run(10)
        mtap(gb, "down", 4)
        gb.press("a", 2)
        run_until(gb, lambda: state(gb) == 0 and gb.pb.memory[0xFF40] & 0x80, 200)
        gb.run(60)
        assert gb.mem("story_on") == 0 and gb.mem("story_chapter") & 0x80, "DEBUG_RESUME: CONTINUE resumes the debug run"
