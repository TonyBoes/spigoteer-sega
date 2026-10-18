# The boss comes in Last call's own level (owner 2026-10-17: "each venue has only four rounds: Opening shift, Happy hour, minigame, Last call. After the
# assigned number of patrons have been served, that level kicks into boss mode, with the patron counter no longer counting and the boss making his
# entrance. The first time a boss appears in the game, the game pauses automatically and shows the instruction card for the boss. It unpauses
# automatically when the instructions are exited. This changes in both story and arcade."): src/story.c shift_won / boss_in_place, src/boss.c
# fight_start, src/pause.c pause_boss_card, src/save.c block "BK" (the boss cards seen).
import pytest
from boss_common import BS_ENTER, BS_WALK, BS_WALKIN, BS_WARM, hud, meter_tiles, row
from conftest import BK_AT, bk_block, clear_regulars
from save_images import put
from test_flow import GS_GOAL, LEVEL_CLEAR, PLAYING, run_until, state
from test_pause import CARD_FRAMES, PAUSE_NR51, PAUSED, boss_cards, card_rows, tap
from test_scores import booted, v7_image
from test_sound import save_ram
from test_story import (BOSS_BUILT, GAME_ART, SHIFT_STEP, SHIFTS, banner_text, centred, clear_bars, to_boss_banner, to_chapter, to_goal,
                        to_shift, win)

pytestmark = pytest.mark.timeout(300)

G_BOSS = 3
GLYPH_0 = GAME_ART["TILE_GLYPH_0"]
MODES = ["dmg", "cgb"]
VENUES = sorted(BOSS_BUILT)


def goal_type(gb):
    return gb.mem("story_goal")                 # (goal_t's first byte)


def last_call(model, c, bk=None):
    """Chapter c's Last call in play with 3 lives; bk: the cartridge's "BK" block (None: every boss card seen, as the test images have it)."""
    img = None
    if bk is not None:
        img = put(v7_image([], story=c, step=SHIFT_STEP[2]), BK_AT, bk)
    return to_shift(model, c, 2, image=img)


# ---- the quota meets the boss ----------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", MODES)
@pytest.mark.parametrize("c", VENUES)
def test_the_quota_triggers_the_boss_in_the_same_level_with_no_shift_clear(model, c):
    """Last call's quota met: no SHIFT / CHAPTER CLEAR (the level never clears), arrivals stop, the patrons already in are served as ever; when
    the bars are empty the level turns into his fight (his banner BOSS), the same venue, lives and score (plus the clear bonus)."""
    with last_call(model, c) as gb:
        lives, level, group = gb.mem("lives"), gb.mem("level"), gb.mem("cur_group")
        score = int.from_bytes(gb.read("score", 4), "little")
        states = set()
        win(gb, c, 2)
        gb.run(3)
        if SHIFTS[c][2]["type"] != 2:                # (a clear goal has no lead: it is the bars being empty)
            assert state(gb) == PLAYING and goal_type(gb) == G_BOSS and gb.mem("boss_on") == 0
            assert gb.mem("quota") == gb.mem("spawned"), "arrivals stop"
            spawned = gb.mem("spawned")
            for _ in range(40):                      # (a patron is still on a bar: nobody new comes, the level does not clear)
                gb.run(1)
                states.add(state(gb))
                if state(gb) != PLAYING:
                    break
                if gb.mem("patrons_live"):
                    assert gb.mem("spawned") == spawned and gb.mem("boss_on") == 0
        clear_bars(gb)
        for _ in range(80):
            gb.run(1)
            states.add(state(gb))
            if state(gb) == GS_GOAL:
                break
        assert state(gb) == GS_GOAL and LEVEL_CLEAR not in states, states
        gb.run(3)
        assert gb.mem("boss_on") == 1 and gb.mem("boss_id") == c and banner_text(gb, 1) == centred("BOSS")
        assert (gb.mem("lives"), gb.mem("level"), gb.mem("cur_group")) == (lives, level, group), "the same level"
        assert gb.mem("story_step") == SHIFT_STEP[2] and gb.mem("story_shift") == 2, "no step of his own"
        assert int.from_bytes(gb.read("score", 4), "little") >= score + 1000, "Last call's clear bonus (a caught empty or two on top)"
        assert gb.mem("mosh_on") == 0 and gb.mem("music_fast") == 0 and gb.mem16("story_timer") == 0
        assert gb.mem("quota") == 255 and gb.mem("served") == 0


@pytest.mark.parametrize("model", MODES)
def test_the_counter_stops_and_the_boss_meter_replaces_it(model):
    """Meeting the quota freezes the HUD counter at 00 (more serves change nothing); at his banner the counter's columns are blank, and when he
    has entered his face and meter are on the HUD at columns 12-19."""
    c = 0
    with last_call(model, c) as gb:
        win(gb, c, 2)
        gb.run(3)
        assert gb.mem("story_left") == 0
        counter = [gb.read(0x9800 + 11 + k, 1)[0] for k in range(3)]
        assert counter[1:] == [GLYPH_0, GLYPH_0], "00"
        gb.write("served", 200)
        gb.run(20)
        assert gb.mem("story_left") == 0 and [gb.read(0x9800 + 11 + k, 1)[0] for k in range(3)] == counter, "it does not count any more"
        clear_bars(gb)
        run_until(gb, lambda: state(gb) == GS_GOAL, 80)
        gb.run(3)
        blank = GAME_ART["TILE_HUD_BLANK"]
        assert [gb.read(0x9800 + 11 + k, 1)[0] for k in range(1)] == [blank], "the counter's icon is gone"
        to_goal(gb)
        run_until(gb, lambda: gb.mem("boss_state") == BS_WALK, 400)
        gb.run(2)
        assert hud(gb) == meter_tiles(row(c)["meter"], row(c)["meter"]), "his face and meter"


@pytest.mark.parametrize("model", MODES)
def test_the_boss_enters_after_the_banner_and_the_regulars_never_take_his_bar(model):
    """After the banner his entrance starts at once (Last call was the warm-up); the fight then runs as it always did: regulars on the other bars
    only, his meter full."""
    c = 0
    with last_call(model, c) as gb:
        to_boss_banner(gb, c)
        gb.press("a", 2)
        run_until(gb, lambda: state(gb) == PLAYING, 10)
        run_until(gb, lambda: gb.mem("boss_state") in (BS_ENTER, BS_WALKIN), 10)
        run_until(gb, lambda: gb.mem("boss_state") == BS_WALK, 400)
        assert gb.mem("boss_hp") == row(c)["meter"] and gb.mem("boss_bar") == row(c)["bar"] and gb.mem("lives") == 3
        for _ in range(900):
            gb.run(1)
            st, pb = gb.read("patron_state", 16), gb.read("patron_bar", 16)
            assert not any(st[p] and pb[p] & 3 == row(c)["bar"] for p in range(16))
            if gb.mem("patrons_live"):
                break


# ---- the first encounter's card ------------------------------------------------------------------------------------------------------------
def into_fight_start(gb, limit=600):
    """Past his banner, until the fight starts or the game pauses (the card)."""
    gb.press("a", 2)
    for _ in range(limit):
        gb.run(1)
        if state(gb) == PAUSED or gb.mem("boss_state") == BS_WALK:
            return
    raise AssertionError("neither the fight nor the card in %d frames (boss_state %d)" % (limit, gb.mem("boss_state")))


def card_pages(gb):
    """Turn the open card to its last page with A; the rows of each page seen."""
    pages = [card_rows(gb)]
    while pages[-1][16] != "A BACK":
        tap(gb, "a", CARD_FRAMES)
        pages.append(card_rows(gb))
    return pages


@pytest.mark.parametrize("model", MODES)
@pytest.mark.parametrize("c", VENUES)
def test_the_first_time_a_boss_appears_the_game_pauses_on_his_card_and_resumes_when_it_is_left(model, c):
    name, p1, p2 = boss_cards()[c]
    with last_call(model, c, bk_block(0)) as gb:
        to_boss_banner(gb, c)
        into_fight_start(gb)
        assert state(gb) == PAUSED and gb.mem("boss_on") == 1 and gb.mem(PAUSE_NR51) != 0, "paused by itself, right after his entrance"
        assert gb.mem("boss_state") == BS_WALK and gb.mem("boss_hp") == row(c)["meter"], "the fight had just begun"
        gb.run(CARD_FRAMES)
        pages = card_pages(gb)
        assert pages[0][1] == "HOW TO PLAY" and pages[0][5] == name and pages[0][7:14:2] == p1, pages[0]
        if p2:
            assert pages[-1][7:14:2] == p2
        hp, lives = gb.mem("boss_hp"), gb.mem("lives")
        tap(gb, "a", CARD_FRAMES)                   # (A on the last page leaves the card: no menu comes back)
        assert state(gb) == PLAYING and gb.mem(PAUSE_NR51) == 0, "unpaused by itself"
        assert gb.mem("overlay_on") == 0 and gb.mem(0xFF45) == gb.mem(0xFF4A) + 22, "the banner window's place again"
        assert banner_text(gb, 1) == [GAME_ART["TILE_HUD_BLANK"]] * 20 and banner_text(gb, 0) == [GAME_ART["TILE_PANEL_TOP"]] * 20, "no menu left on screen"
        assert gb.mem("boss_hp") == hp and gb.mem("lives") == lives
        gb.run(60)
        assert state(gb) == PLAYING and gb.mem("boss_hp") == hp


@pytest.mark.parametrize("model", MODES)
def test_the_card_comes_once_per_boss_and_is_saved(model):
    """Per save: the saloon's boss shows his card the first time only; the next boss still shows his; BACK (B) closes it as A does."""
    with last_call(model, 0, bk_block(0)) as gb:
        to_boss_banner(gb, 0)
        into_fight_start(gb)
        assert state(gb) == PAUSED
        gb.run(CARD_FRAMES)
        tap(gb, "b", CARD_FRAMES)                   # (B closes it, on any page)
        assert state(gb) == PLAYING
        ram = save_ram(gb)
    assert ram[BK_AT:BK_AT + 6] == bk_block(1), "the saloon's bit, in the save"
    with last_call(model, 0, ram[BK_AT:BK_AT + 6]) as gb:      # (the same cartridge: his card has been seen)
        to_boss_banner(gb, 0)
        into_fight_start(gb)
        assert state(gb) == PLAYING and gb.mem("boss_state") == BS_WALK, "no card the second time"
        gb.run(120)
        assert state(gb) == PLAYING
    with last_call(model, 1, bk_block(1)) as gb:               # (the stadium's boss is another)
        to_boss_banner(gb, 1)
        into_fight_start(gb)
        assert state(gb) == PAUSED
        gb.run(CARD_FRAMES)
        assert card_rows(gb)[5] == boss_cards()[1][0]


@pytest.mark.parametrize("model", MODES)
def test_a_bad_cards_block_shows_every_card_again(model):
    bad = bytearray(bk_block(0x3FF))
    bad[4] ^= 1
    with last_call(model, 0, bytes(bad)) as gb:
        to_boss_banner(gb, 0)
        into_fight_start(gb)
        assert state(gb) == PAUSED


@pytest.mark.parametrize("model", MODES)
def test_a_lost_life_or_a_second_fight_does_not_open_the_card_again(model):
    with last_call(model, 0, bk_block(0)) as gb:
        to_boss_banner(gb, 0)
        into_fight_start(gb)
        gb.run(CARD_FRAMES)
        tap(gb, "b", CARD_FRAMES)
        gb.run(10)
        from test_flow import lose_a_life
        lose_a_life(gb)
        run_until(gb, lambda: state(gb) == PLAYING, 200)
        gb.run(200)
        assert state(gb) == PLAYING and gb.mem("lives") == 2


# ---- save / resume -------------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", MODES)
def test_continue_after_reaching_the_boss_lands_on_the_venue_s_opening(model):
    """Last call is the last step: the save holds step 3 and CONTINUE starts the venue over at its Opening banner with 3 lives (as before:
    a venue is attempted whole), not at the boss."""
    c = 2
    with last_call(model, c) as gb:
        to_boss_banner(gb, c)
        assert (gb.mem("story_progress"), gb.mem("story_reached")) == (c, SHIFT_STEP[2])
        ram = save_ram(gb)
    from conftest import hold_stage_anim
    from test_story import to_continue
    gb = booted(model, ram)
    try:
        hold_stage_anim(gb)
        to_continue(gb)
        run_until(gb, lambda: state(gb) == GS_GOAL, 60)
        gb.run(3)
        assert gb.mem("story_chapter") == c and gb.mem("story_shift") == 0 and gb.mem("story_step") == 0 and gb.mem("boss_on") == 0
        assert gb.mem("lives") == 3 and banner_text(gb, 1) == centred("OPENING SHIFT")
    finally:
        gb.stop()


@pytest.mark.parametrize("model", MODES)
@pytest.mark.parametrize("step", [3, 4])
def test_a_save_from_before_the_change_still_loads(model, step):
    """The boss was a fifth step (4) until 2026-10-17: such a save reads as Last call (3), the chapter's progress kept; a step beyond that is bad."""
    with booted(model, v7_image([], story=2, step=step)) as gb:
        assert (gb.mem("story_progress"), gb.mem("story_reached")) == (2, 3)
    with booted(model, v7_image([], story=2, step=5)) as gb:
        assert (gb.mem("story_progress"), gb.mem("story_reached")) == (0, 0), "a step that never existed: the block is bad"


# ---- ARCADE ----------------------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", MODES)
def test_arcade_turns_last_call_into_the_boss_and_the_venue_clear_follows_his_defeat(model):
    """ARCADE plays the story's steps: a venue's Last call quota brings its boss in place; beating him is VENUE CLEAR, then the bonus round, then the
    next venue's Opening. No card in ARCADE's debug-less run when every card was seen."""
    from test_arcade import BONUS, finish_bonus, start_arcade
    with start_arcade(model) as gb:
        to_goal(gb)
        from test_story import boss_from_opening
        boss_from_opening(gb)
        assert gb.mem("story_arc") == 1 and gb.mem("boss_on") == 1 and gb.mem("boss_id") == 0 and banner_text(gb, 1) == centred("BOSS")
        to_goal(gb)
        gb.write("boss_hook", 3)
        clear_regulars(gb)
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 200)
        gb.run(3)
        assert banner_text(gb, 1) == centred("VENUE CLEAR")
        run_until(gb, lambda: state(gb) == BONUS, 400)
        finish_bonus(gb)
        assert gb.mem("story_chapter") == 1 and gb.mem("story_shift") == 0 and gb.mem("boss_on") == 0


@pytest.mark.parametrize("model", MODES)
def test_arcade_shows_the_first_boss_card_too(model):
    """The cards are per save, whatever the mode: ARCADE's first boss pauses on his card."""
    from test_arcade import start_arcade
    from test_story import boss_from_opening
    with start_arcade(model, put(bytes(0x2000), BK_AT, bk_block(0))) as gb:
        to_goal(gb)
        boss_from_opening(gb)
        into_fight_start(gb)
        assert state(gb) == PAUSED
