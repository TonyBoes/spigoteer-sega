# The boss comes in Last call's own level (owner 2026-10-17: "each venue has only four rounds: Opening shift, Happy hour, minigame, Last call. After the
# assigned number of patrons have been served, that level kicks into boss mode, with the patron counter no longer counting and the boss making his
# entrance. The first time a boss appears in the game, the game pauses automatically and shows the instruction card for the boss. It unpauses
# automatically when the instructions are exited. This changes in both story and arcade."): src/story.c shift_won / boss_in_place, src/boss.c
# fight_start, src/pause.c pause_boss_card, src/save.c block "BK" (the boss cards seen).
# Owner 2026-10-18: "I don't want to immediately switch to the next stage, I want the boss to come in at the end of the stage without any kind of screen transition.
# After he comes in, and his animation is complete, if it is his first time appearing, the instruction card comes up." So there is no cover, no LCD-off swap and no
# banner: the level stays on screen, his tiles and palettes stream in over a few frames (src/boss.c ld_step), his entrance plays, and the card opens the frame after it.
import pytest
from split_helpers import win_lyc
from boss_common import BS_ENTER, BS_WALK, BS_WALKIN, BS_WARM, hud, meter_tiles, row
from conftest import BK_AT, bk_block, clear_regulars
from save_images import put
from test_flow import GS_GOAL, LEVEL_CLEAR, PLAYING, run_until, state
from test_pause import CARD_FRAMES, PAUSE_NR51, PAUSED, boss_cards, card_rows, tap
from test_scores import booted, v7_image
from test_sound import save_ram
from test_story import (BOSS_BUILT, GAME_ART, SHIFT_STEP, SHIFTS, banner_text, boss_streamed, centred, clear_bars, to_boss_banner, to_chapter, to_goal,
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
def test_the_quota_triggers_the_boss_in_the_same_level_with_no_shift_clear_and_no_screen_change(model, c):
    """Last call's quota met: no SHIFT / CHAPTER CLEAR (the level never clears), arrivals stop, the patrons already in are served as ever; when
    the bars are empty the level turns into his fight in the same screen (no banner, no goal state: the game stays PLAYING), the same venue,
    lives and score (plus the clear bonus)."""
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
        if not gb.mem("boss_on"):
            clear_bars(gb)
        for _ in range(80):
            gb.run(1)
            states.add(state(gb))
            if gb.mem("boss_on"):
                break
        assert gb.mem("boss_on") == 1 and gb.mem("boss_id") == c
        for _ in range(60):                          # (and the screen stays the level: no banner, no goal state, no clear)
            gb.run(1)
            states.add(state(gb))
        assert states == {PLAYING}, states
        assert banner_text(gb, 1) != centred("BOSS") and gb.mem("overlay_on") == 0
        assert (gb.mem("lives"), gb.mem("level"), gb.mem("cur_group")) == (lives, level, group), "the same level"
        assert gb.mem("story_step") == SHIFT_STEP[2] and gb.mem("story_shift") == 2, "no step of his own"
        assert int.from_bytes(gb.read("score", 4), "little") >= score + 1000, "Last call's clear bonus (a caught empty or two on top)"
        assert gb.mem("mosh_on") == 0 and gb.mem("music_fast") == 0 and gb.mem16("story_timer") == 0
        assert gb.mem("quota") == 255 and gb.mem("served") == 0


@pytest.mark.parametrize("model", MODES)
def test_the_counter_stops_and_the_boss_meter_replaces_it(model):
    """Meeting the quota freezes the HUD counter at 00 (more serves change nothing); when he comes in the counter's columns are blank, and when
    he has entered his face and meter are on the HUD at columns 12-19."""
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
        run_until(gb, lambda: gb.mem("boss_on") == 1, 80)
        gb.run(3)
        blank = GAME_ART["TILE_HUD_BLANK"]
        assert [gb.read(0x9800 + 11 + k, 1)[0] for k in range(6)] == [blank] * 6, "the counter's icon and digits are gone"
        assert gb.read(0x9800 + 17, 1)[0] == GAME_ART["TILE_HUD_FLAG"], "the level flag back"
        run_until(gb, lambda: gb.mem("boss_state") == BS_WALK, 600)
        gb.run(2)
        assert hud(gb) == meter_tiles(row(c)["meter"], row(c)["meter"]), "his face and meter"


@pytest.mark.parametrize("model", MODES)
def test_the_boss_enters_at_once_and_the_regulars_never_take_his_bar(model):
    """Once his tiles are in his entrance starts (Last call was the warm-up); the fight then runs as it always did: regulars on the other bars
    only, his meter full."""
    c = 0
    with last_call(model, c) as gb:
        to_boss_banner(gb, c)
        run_until(gb, lambda: gb.mem("boss_state") in (BS_ENTER, BS_WALKIN), 120)
        run_until(gb, lambda: gb.mem("boss_state") == BS_WALK, 400)
        assert gb.mem("boss_hp") == row(c)["meter"] and gb.mem("boss_bar") == row(c)["bar"] and gb.mem("lives") == 3
        for _ in range(900):
            gb.run(1)
            st, pb = gb.read("patron_state", 16), gb.read("patron_bar", 16)
            assert not any(st[p] and pb[p] & 3 == row(c)["bar"] for p in range(16))
            if gb.mem("patrons_live"):
                break


# ---- no screen change from the quota to the end of his entrance ----------------------------------------------------------------------------
LCDC, BGP, OBP0, OBP1 = 0xFF40, 0xFF47, 0xFF48, 0xFF49
BODY = {0: "big_tex", 1: "mascot", 2: "sasquatch", 3: "critic", 4: "yeti", 5: "prototype", 6: "duke", 7: "sumo", 8: "leo", 9: "mothership"}


def sample(gb):
    """(the share of the picture that is white, the DMG palette registers): a palette fade to white or a white cover moves both."""
    im = gb.image().convert("RGB")
    import numpy as np
    white = float((np.asarray(im) == 255).all(axis=2).mean())
    return white, tuple(gb.pb.memory[a] for a in (BGP, OBP0, OBP1))


@pytest.mark.parametrize("model", MODES)
@pytest.mark.parametrize("c", VENUES)
def test_no_lcd_off_and_no_palette_fade_from_the_quota_to_the_end_of_the_entrance(model, c):
    """Owner 2026-10-18: no transition. From the quota being met to the last frame of his entrance (boss_state back to BS_WALK) the LCD stays on (LCDC bit 7
    every frame), the palette registers never change (the Mothership's own light flicker aside) and the picture never goes white, the game stays PLAYING (no goal banner, no pause) and the
    window is not up; his tiles are streamed in meanwhile (BS_WARM) and the entrance runs."""
    with last_call(model, c) as gb:
        base = sample(gb)
        win(gb, c, 2)
        seen = set()
        for i in range(900):
            gb.run(1)
            if i == 3 and not gb.mem("boss_on"):     # (the goal is seen met; a serve goal's last patrons gone: a clear goal's win() emptied the bars already)
                clear_bars(gb)
            assert gb.pb.memory[LCDC] & 0x80, f"the LCD went off (frame {i}, boss_state {gb.mem('boss_state')})"
            assert state(gb) == PLAYING and gb.mem("overlay_on") == 0, (i, state(gb))
            if gb.mem("boss_on") and gb.mem("boss_state") == BS_WALK:
                break                            # (his meter and face are the HUD's next change)
            white, regs = sample(gb)
            assert white < base[0] + 0.1, f"the picture went white (frame {i}, boss_state {gb.mem('boss_state')})"
            assert c == 9 or regs == base[1], f"a palette changed (frame {i}, boss_state {gb.mem('boss_state')})"   # (the Mothership's own light flicker moves BGP / the bar palettes)
            if gb.mem("boss_on"):
                seen.add(gb.mem("boss_state"))
        assert gb.mem("boss_state") == BS_WALK, "the entrance ends"
        assert BS_WARM in seen and seen & {BS_ENTER, BS_WALKIN}, seen


@pytest.mark.parametrize("model", MODES)
@pytest.mark.parametrize("c", VENUES)
def test_his_tiles_stream_in_over_several_frames_and_arrive_intact(model, c):
    """The in-place load: his body, face and topper tiles reach VRAM through the VBlank queue over a few frames (more than two, fewer than ~45), 4 tiles
    a frame at most, and are byte for byte his art (the build's generated array) once the stream is done."""
    import re
    from conftest import ROOT
    hdr = (ROOT / "build" / f"boss_{BODY[c]}_art.h").read_text()

    def arr(name):
        m = re.search(name + r"\[\d+\] = \{([^}]*)\}", hdr)
        return bytes(int(x, 16) for x in m.group(1).replace("\n", " ").split(",") if x.strip())
    body, hat, icon = arr("boss_art_body"), arr("boss_art_hat"), arr("boss_art_icon")
    pairs_a = 21
    with last_call(model, c) as gb:
        to_boss_banner(gb, c)
        n = 0
        while not boss_streamed(gb) and n < 200:
            gb.run(1)
            n += 1
        assert 2 < n < 45, f"the stream took {n} frames"
        gb.run(2)
        vram = lambda a, k: bytes(gb.pb.memory[a + i] for i in range(k))
        na = min(len(body) // 32, pairs_a) * 32
        assert vram(0x8000 + 162 * 16, na) == body[:na], "his body, first block (BG 162..)"
        if len(body) // 32 > pairs_a:
            assert vram(0x8000 + 214 * 16, len(body) - pairs_a * 32) == body[pairs_a * 32:], "his body, second block (BG 214..)"
        assert vram(0x8000 + 252 * 16, len(icon)) == icon, "his face"
        assert vram(0x8000 + 96 * 16, len(hat)) == hat, "his topper (OBJ 96..)"


# ---- the first encounter's card ------------------------------------------------------------------------------------------------------------
def into_fight_start(gb, limit=600):
    """His entrance is over (the fight has begun) and the frames after it have run: the card, when it is due, is open (the game paused)."""
    for _ in range(limit):
        gb.run(1)
        if state(gb) == PAUSED or gb.mem("boss_state") == BS_WALK:
            gb.run(3)
            return
    raise AssertionError("neither the fight nor the card in %d frames (boss_state %d)" % (limit, gb.mem("boss_state")))


@pytest.mark.parametrize("model", MODES)
@pytest.mark.parametrize("c", VENUES)
def test_the_card_opens_only_after_his_entrance_ends_over_a_whole_picture(model, c):
    """First time he appears: the card is not open while he is BS_WARM / BS_ENTER / BS_WALKIN (his entrance animation plays out first), it opens the frame
    after the entrance ended (not in the middle of that frame: its sprites and bar rows were half done and the card's fade-out would have shown them), with
    him on his bar (his columns stamped) and the LCD on until the card's own fade; on the LCD going off the game is paused."""
    with last_call(model, c, bk_block(0)) as gb:
        win(gb, c, 2)
        history = []
        for i in range(1500):
            gb.run(1)
            if i == 3 and not gb.mem("boss_on"):
                clear_bars(gb)
            history.append((state(gb), gb.mem("boss_on") and gb.mem("boss_state"), bool(gb.pb.memory[LCDC] & 0x80), any(gb.read("boss_cols", 5))))
            if state(gb) == PAUSED:
                break
        assert state(gb) == PAUSED, "the card opened"
        card_at = len(history) - 1
        entrance = [k for k, h in enumerate(history) if h[1] in (BS_ENTER, BS_WALKIN)]
        assert entrance and card_at > entrance[-1], "after his entrance"
        assert all(h[0] == PLAYING for h in history[:card_at]), "playing until the card"
        walk = [k for k, h in enumerate(history[:card_at]) if h[1] == BS_WALK]
        assert len(walk) >= 1, "at least one whole frame of the fight (his body drawn) before the card's fade starts"
        assert history[card_at - 1][3], "him on his bar in the frame the card fades out"
        assert all(h[2] for h in history[:card_at]), "the LCD was on until the card"


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
        assert gb.mem("overlay_on") == 0 and win_lyc(gb.mem) == gb.mem(0xFF4A) + 22, "the banner window's place again"
        assert banner_text(gb, 1) == [GAME_ART["TILE_HUD_BLANK"]] * 20 and banner_text(gb, 0) == [GAME_ART["TILE_PANEL_TOP"]] * 20, "no menu left on screen"
        assert gb.mem("boss_hp") == hp and gb.mem("lives") == lives
        gb.run(60)
        assert state(gb) == PLAYING and gb.mem("boss_hp") == hp


@pytest.mark.parametrize("model", MODES)
@pytest.mark.parametrize("c", VENUES)
def test_his_card_is_on_the_screen_while_it_is_open_not_the_paused_game_behind_it(model, c):
    """Owner 2026-10-20: "the boss menu card goes blank and seems to freeze the game". The card is the window (LCDC bit 5, over the whole screen) and main.c's
    update hides the window every frame unless overlay_on is set: the first-appearance card was opened with it clear, so after its fade-in the next frame's
    update hid the card and the paused game stood on screen, frozen and unexplained. The tilemap rows were right, so only the picture shows it: the window
    is on for every frame the card is open, and the picture is the card (the frame's top row of tiles, the page's text), never the level; A leaves it."""
    from PIL import ImageChops
    with last_call(model, c, bk_block(0)) as gb:
        to_boss_banner(gb, c)
        into_fight_start(gb)
        assert state(gb) == PAUSED
        level = gb.image().convert("RGB")
        gb.run(CARD_FRAMES)
        for _ in range(30):                           # (the card stands: every frame has the window on, over the whole screen, with the card's own rows)
            gb.run(1)
            assert state(gb) == PAUSED and gb.pb.memory[LCDC] & 0x20, "the window (the card) is on screen"
            assert gb.mem("overlay_on") == 1 and gb.mem(0xFF4A) == 0
        card = gb.image().convert("RGB")
        diff = sum(1 for p in ImageChops.difference(level, card).convert("L").getdata() if p)
        assert diff > 160 * 144 * 0.5, "the picture is the card, not the level (%d of %d pixels differ)" % (diff, 160 * 144)
        pages = card_pages(gb)
        assert pages[0][1] == "HOW TO PLAY"
        tap(gb, "a", CARD_FRAMES)
        assert state(gb) == PLAYING and not gb.pb.memory[LCDC] & 0x20 and gb.mem("overlay_on") == 0, "the level is back, no window"


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
        assert gb.mem("story_arc") == 1 and gb.mem("boss_on") == 1 and gb.mem("boss_id") == 0 and state(gb) == PLAYING
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


# ---- performance: every boss fight's frames end no later than before the restructure -----------------------------------------------------------
PERF_BEFORE = {   # (model, venue): (mean, p50, p99) of the frame's end line at 579e173 (the commit before the restructure), same scenario (tools/boss_perf.py --idle --frames 400)
    ('cgb', 0): (51.2, 47, 106),
    ('cgb', 1): (49.3, 44, 103),
    ('cgb', 2): (49.5, 46, 105),
    ('cgb', 3): (49.8, 45, 105),
    ('cgb', 4): (48.6, 45, 103),
    ('cgb', 5): (50.0, 47, 109),   # owner Q89 2026-11-01: loosened from (49.7, 46, 106) by the measured cost of the Factory's two palette reloads (BG 5/6 split chain)
    ('cgb', 6): (53.1, 48, 105),
    ('cgb', 7): (46.5, 42, 101),
    ('cgb', 8): (50.6, 47, 107),
    ('cgb', 9): (52.6, 48, 108),
    ('dmg', 0): (51.0, 47, 102),
    ('dmg', 1): (48.8, 44, 98),
    ('dmg', 2): (49.1, 46, 100),
    ('dmg', 3): (49.5, 45, 100),
    ('dmg', 4): (48.3, 44, 98),
    ('dmg', 5): (49.4, 46, 101),
    ('dmg', 6): (52.8, 48, 100),
    ('dmg', 7): (46.1, 41, 96),
    ('dmg', 8): (50.2, 47, 102),
    ('dmg', 9): (52.1, 48, 103),
}


@pytest.mark.parametrize("model", MODES)
@pytest.mark.parametrize("c", VENUES)
def test_a_boss_fight_s_frames_end_no_later_than_at_579e173(model, c):
    """Owner 2026-10-18: "boss mode performance was pretty bad". The boss alone (no regulars, no input; deterministic), 400 frames of the fight at once: the
    mean, the median and the 99th percentile of the scanline the frame's work ended on (perf_helpers: logic + music tick) are no higher than the same
    numbers at 579e173, the commit before the restructure (PERF_BEFORE). boss.c boss_draw scans only the OAM entries in use (boss_near), cap_draw is byte
    arithmetic, and the fight no longer carries Last call's rounding (level.c level_pace_again: slower, more crowded regulars)."""
    import perf_helpers as ph
    from boss_common import fight
    with fight(model, c) as gb:
        gb.write("tip_chance", 0)
        ph.perf_reset(gb)
        for _ in range(400):
            gb.run(1)
            ph.sample(gb)
            gb.write("lives", 3)
            for q in range(16):
                gb.write(gb.addr("patron_state") + q, 0)
            gb.write("patrons_live", 0)
        st = ph.perf_stats(gb)
    mean, p50, p99 = PERF_BEFORE[model, c]
    assert st["n"] > 300 and st["late"] == 0, st
    assert st["mean"] <= mean and st["p50"] <= p50 and st["p99"] <= p99, f"{st} against mean {mean}, p50 {p50}, p99 {p99} at 579e173"


@pytest.mark.parametrize("model", MODES)
@pytest.mark.parametrize("c", VENUES)
def test_a_boss_fight_with_regulars_is_late_on_hardly_any_frame(model, c):
    """Owner 2026-10-18 (perf report, fix a): boss.c boss_draw counted the sprites on every line over his bar with a pass over all 40 OAM entries and a
    loop of band increments (up to 55 lines a frame), so with the regulars' mugs and the glasses about him the fight ran late on 4-17% of its frames. Now only
    the entries in use are scanned and the bands are a difference array. The level-8 script bot (perf_helpers.SCRIPT) against him for 600 frames: the frames
    that end past line 154 are under 1.5% and the mean end line stays under 76 (it was 87-98 for the worst bosses, 72-80 for the rest)."""
    import perf_helpers as ph
    from boss_common import fight
    with fight(model, c) as gb:
        gb.write("tip_chance", 0)
        gb.write("rng_state", 1)
        ph.perf_reset(gb)
        ph.play_script(gb, 600, keep=lambda g, i: g.write("lives", 3))
        st = ph.perf_stats(gb)
    assert st["n"] > 250, st
    assert st["late154"] * 1000 <= st["n"] * 15 and st["mean"] <= 76, st


@pytest.mark.parametrize("model", MODES)
@pytest.mark.parametrize("c", VENUES)
def test_a_boss_entrance_has_no_late_frame_but_dukes_hand_over(model, c):
    """The warm-up and the entrance of every boss, 320 frames: no frame ends past line 154. On the CGB the palettes of the boss tile stream (ld_step) waited for
    the next VBlank in a spin (3-6 late frames at 167-176); they are written with set_*_palette now. Duke's entrance (20 sprites of its own, boss_duke.c ent_put)
    still has the one frame where it hands over to the fight (boss_to_bar and boss_look in the same frame as the intro's last sprites)."""
    import perf_helpers as ph
    from boss_common import fight
    with fight(model, c, warm=True) as gb:
        ph.perf_reset(gb)
        for _ in range(320):
            gb.run(1)
            ph.sample(gb)
            gb.write("lives", 3)
        st = ph.perf_stats(gb)
    assert st["n"] > 300 and st["late154"] <= (1 if c == 6 else 0), st
