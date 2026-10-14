# The pause menu of every mode (src/pause.c): START opens RESUME / QUIT TO MENU (QUIT asks ARE YOU SURE?), gameplay stands still,
# the music stops and its channels are muted (NR51 0) until RESUME, and QUIT ends the run through the same exits as finishing it:
# STORY (shifts, boss fights, the Pour-Off): the title, the save untouched; ARCADE / CLASSIC: the initials when the score makes the
# top 5, else the title; mini-games: the list (practice, no medal) or as the run they are part of; BOSS RUSH: its menu, no time.
# Every mini-game's quit leaves what its normal leave leaves (OBP0, the LCD handler, the mute mask, OBJ / BG tiles, palettes).
import pytest
from conftest import K_ARCADE, K_CLASSIC, K_CONTINUE, K_PLAY, MENU_SETTLE, check_golden, hold_stage_anim, menu_items, \
    menu_tap, title_pick
from test_bonus import lines
from test_flow import GS_GOAL, GS_STORY, LEVEL_CLEAR, PLAYING, TITLE, inject_mug, run_until, state, tilemap_row
from test_mg import GLYPH_CH, GS_MGLIST, GS_MINI, MG_PLAY, MG_PRACTICE, MG_RESULT, MG_STORY, MG_STUB, frames, mg_enter, until
from test_scores import GS_INITIALS, GS_SCORES, booted, set_score, table
from test_sound import make_rom

pytestmark = pytest.mark.timeout(300)

PAUSED = 5
MG_ICON_PAL = 4                          # mg.c: the medal icon's CGB BG palette
NR51, NR50 = 0xFF25, 0xFF24
PAUSE_NR51 = 0xFFF0                      # HRAM (game.h): the NR51 to restore while the menu is open, else 0
MODES = ["dmg", "cgb"]
MENU, ASK = 0, 1
GAMES = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, MG_STUB]       # mg.h: every mini-game incl. the Pour-Off, the three bonus rounds and the stub
MG_MILKRUN, MG_TAIKO, MG_POUROFF = 6, 7, 11
GLYPH_J, GLYPH_Z = 72, 75                                  # the '?' and the arrow take two rare letters' tiles while paused


def rom_s(model, ram=None):
    """A booted rom with the emulator's sound on (the APU registers read back), on the title."""
    rom = make_rom(model, ram, sound=True)
    rom.run(120)
    hold_stage_anim(rom)
    return rom


def tap(gb, b, settle=3):
    gb.press(b, 2)
    gb.run(settle)


def win_text(gb, row):
    """The window's text row (pause rows 0-5: panel, title, blank, two items, panel) with the '?' and the arrow decoded."""
    out = ""
    for t in tilemap_row(gb, row, 0, 20, True):
        out += "?" if t == GLYPH_J else ">" if t == GLYPH_Z else GLYPH_CH.get(t, " ")
    return out.strip()


def menu_rows(gb):
    return [win_text(gb, r) for r in (1, 3, 4)]


def music(gb):
    return (gb.mem16("music_frames"), gb.mem("hUGE_row"), gb.mem("hUGE_tick"), gb.mem("cur_tune"))


def tile(gb, i):
    """BG tile i's 16 bytes (ids 0-127 at 0x9000, 128-255 at 0x8800: LCDC bit 4 is clear)."""
    return bytes(gb.read((0x9000 if i < 128 else 0x8000) + i * 16, 16))


def start_arcade(gb):
    """PLAY > ARCADE (the story's engine: the goal banner first), through the banner into play."""
    title_pick(gb, K_PLAY, K_ARCADE)
    run_until(gb, lambda: state(gb) == GS_GOAL, 120)
    gb.write("tip_chance", 0)
    gb.press("a", 2)
    run_until(gb, lambda: state(gb) == PLAYING, 20)
    gb.run(120)


def start_classic(gb):
    title_pick(gb, K_PLAY, K_CLASSIC)
    run_until(gb, lambda: state(gb) == PLAYING, 120)
    gb.write("tip_chance", 0)
    gb.run(120)


def open_pause(gb):
    tap(gb, "start", 3)
    assert state(gb) == PAUSED and gb.mem("overlay_on") == 1
    rows = menu_rows(gb)
    assert rows[0] == "PAUSE" and rows[1] == "> RESUME" and rows[2] == "QUIT TO MENU", rows


def quit_yes(gb):
    """From the open menu: QUIT TO MENU, then YES."""
    tap(gb, "down")
    tap(gb, "a")
    assert win_text(gb, 1) == "ARE YOU SURE?" and win_text(gb, 4).startswith(">"), menu_rows(gb)
    tap(gb, "up")
    assert win_text(gb, 3).startswith(">") and win_text(gb, 3).endswith("YES")
    gb.press("a", 2)


def settled(gb, st, limit=60):
    run_until(gb, lambda: state(gb) == st and gb.pb.memory[0xFF40] & 0x80, limit)
    gb.run(4)


# ---- (a) the menu, in a level: it freezes everything, mutes and resumes the music ---------------------------------------------------
@pytest.mark.parametrize("model", MODES)
def test_pause_freezes_the_game_mutes_the_music_and_resumes_it(model):
    with rom_s(model) as gb:
        start_arcade(gb)
        gb.write("intro_timer", 0)
        inject_mug(gb, 2, 120)
        gb.run(30)
        assert gb.mem(NR51) == 0xFF
        glyphs = (tile(gb, GLYPH_J), tile(gb, GLYPH_Z))
        before_music = music(gb)
        tap(gb, "start", 3)
        assert state(gb) == PAUSED and gb.mem("overlay_on") == 1
        assert menu_rows(gb) == ["PAUSE", "> RESUME", "QUIT TO MENU"]
        assert tilemap_row(gb, 0, 0, 20, True) == [63] * 20 and tilemap_row(gb, 5, 0, 20, True) == [64] * 20   # the panels
        assert gb.mem(NR51) == 0, "every channel muted"
        assert gb.mem(PAUSE_NR51) == 0xFF
        assert gb.mem(0xFF45) == gb.mem(0xFF4A) + 46 and gb.mem(0xFF40) & 0x20, "the 48 px window"
        assert tile(gb, GLYPH_J) != glyphs[0] and tile(gb, GLYPH_Z) != glyphs[1], "the '?' and the arrow are loaded"
        assert max(lines(gb)) <= 10
        frozen = (gb.read("patron_state", 16), gb.read("mug_state", 12), gb.mem("bartender_x"), gb.mem16("score"),
                  gb.mem("spawn_timer"), music(gb))
        gb.hold("left")
        gb.run(120)
        gb.release("left")
        assert state(gb) == PAUSED and gb.mem(NR51) == 0
        assert (gb.read("patron_state", 16), gb.read("mug_state", 12), gb.mem("bartender_x"), gb.mem16("score"),
                gb.mem("spawn_timer"), music(gb)) == frozen, "the game and the tune stand still"
        assert before_music[0] <= music(gb)[0] <= before_music[0] + 4
        check_golden(gb, "pause_menu")
        tap(gb, "start", 3)
        assert state(gb) == PLAYING and gb.mem("overlay_on") == 0 and gb.mem(NR51) == 0xFF and gb.mem(PAUSE_NR51) == 0
        assert gb.mem(0xFF45) == gb.mem(0xFF4A) + 22, "the banner's LYC again"
        assert tilemap_row(gb, 0, 0, 20, True) == [63] * 20 and tilemap_row(gb, 1, 0, 20, True) == [54] * 20
        assert tilemap_row(gb, 2, 0, 20, True) == [64] * 20, "the banner's rows as win_init left them"
        assert (tile(gb, GLYPH_J), tile(gb, GLYPH_Z)) == glyphs, "the two letters are back"
        row0 = frozen[-1][1]
        gb.run(90)
        assert music(gb)[0] > frozen[-1][0] + 60, "the tune plays on"
        assert gb.mem("hUGE_row") != row0 or gb.mem("hUGE_tick") != frozen[-1][2], "from where it stopped"
        gb.run(1)


@pytest.mark.parametrize("model", MODES)
def test_the_tune_continues_from_the_same_note(model):
    """The driver's row and tick (and music_frames) stand still for a long pause; after RESUME the next frames are the next ticks."""
    with rom_s(model) as gb:
        start_arcade(gb)
        gb.run(37)
        tap(gb, "start", 3)
        m = music(gb)
        gb.run(300)
        assert music(gb) == m
        tap(gb, "b", 1)                                  # B resumes too
        assert state(gb) == PLAYING
        mf, row, tick, _ = m
        n = 0
        while n < 40 and gb.mem16("music_frames") < mf + 1:
            gb.run(1)
            n += 1
        got = (gb.mem("hUGE_row"), gb.mem("hUGE_tick"))
        assert got in ((row, tick), (row, tick + 1)) or (got[0] == row + 1 and got[1] in (0, 1)), (m, got)


@pytest.mark.parametrize("model", MODES)
def test_an_effect_in_progress_is_held_quietly_and_ends_after_resume(model):
    with rom_s(model) as gb:
        start_arcade(gb)
        gb.write("sfx_req", 1 << 6)                       # SFX_COIN... any effect
        gb.run(2)
        gb.write("sfx_req", 1 << 7)                       # SFX_LIFE (16 + frames: still going when START lands)
        gb.run(3)
        tap(gb, "start", 2)
        assert state(gb) == PAUSED and gb.mem(NR51) == 0
        gb.run(200)
        assert gb.mem(NR51) == 0
        tap(gb, "start", 2)
        assert gb.mem(NR51) == 0xFF
        gb.run(120)
        assert not gb.mem("hUGE_mute_mask") & 8, "the effect ended and gave channel 4 back"
        assert gb.mem(NR51) == 0xFF


# ---- (b) the menu's own keys ------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", MODES)
def test_menu_keys_resume_cancel_and_the_question(model):
    with rom_s(model) as gb:
        start_arcade(gb)
        tap(gb, "start")
        assert menu_rows(gb)[1].startswith(">") and not menu_rows(gb)[2].startswith(">")
        tap(gb, "down")
        assert menu_rows(gb)[2].startswith(">") and not menu_rows(gb)[1].startswith(">")
        tap(gb, "up")
        tap(gb, "up")
        assert menu_rows(gb)[2].startswith(">"), "wraps"
        tap(gb, "a")                                      # QUIT TO MENU: asks
        assert win_text(gb, 1) == "ARE YOU SURE?"
        assert win_text(gb, 3) == "YES" and win_text(gb, 4) == "> NO", "the cursor starts on NO"
        for key in ("a", "b", "start"):                   # NO, B and START all go back to the menu (the cursor on QUIT)
            tap(gb, key)
            assert state(gb) == PAUSED and win_text(gb, 1) == "PAUSE" and menu_rows(gb)[2].startswith(">"), key
            tap(gb, "a")                                  # the question again
            assert win_text(gb, 1) == "ARE YOU SURE?"
        tap(gb, "b")
        assert gb.mem("game_state") == PAUSED and gb.mem("lives") == 3
        tap(gb, "up")
        tap(gb, "a")                                      # RESUME
        assert state(gb) == PLAYING and gb.mem(NR51) == 0xFF


# ---- (c) ARCADE / CLASSIC: the run ends as a game over does ------------------------------------------------------------------
@pytest.mark.parametrize("model", MODES)
def test_arcade_quit_without_a_score_goes_to_the_title_with_everything_back(model):
    from test_bs import level_vram, palettes
    with booted(model) as ref:                            # a level from a fresh boot: its VRAM and palettes
        hold_stage_anim(ref)
        title_pick(ref, K_PLAY, K_ARCADE)
        run_until(ref, lambda: state(ref) == PLAYING, 120)
        ref.run(60)
        fresh, pals = level_vram(ref), palettes(ref)
    with rom_s(model) as gb:
        start_arcade(gb)
        assert gb.mem("score") == 0
        old_table = table(gb, 0)
        open_pause(gb)
        quit_yes(gb)
        settled(gb, TITLE)
        assert gb.mem("story_on") == 0 and gb.mem("overlay_on") == 0 and gb.mem(NR51) == 0xFF and gb.mem(PAUSE_NR51) == 0
        assert table(gb, 0) == old_table, "no score, no entry"
        assert gb.mem("cur_tune") == 0, "the title tune"
        assert gb.mem(0xFF45) == gb.mem(0xFF4A) + 22
        title_pick(gb, K_PLAY, K_ARCADE)
        run_until(gb, lambda: state(gb) == PLAYING, 120)
        gb.run(60)
        assert level_vram(gb) == fresh and palettes(gb) == pals


@pytest.mark.parametrize("model", MODES)
def test_arcade_quit_with_a_top_5_score_offers_the_initials(model):
    with rom_s(model) as gb:
        start_arcade(gb)
        set_score(gb, 4321)
        open_pause(gb)
        quit_yes(gb)
        settled(gb, GS_INITIALS)
        assert gb.mem("new_rank") == 0 and gb.mem("story_on") == 0
        assert gb.mem(NR51) == 0xFF
        tap(gb, "up")                                    # the initials, as after a game over: B A A, then A
        tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_SCORES, 20)
        assert table(gb, 0)[0][1] == 4321 and table(gb, 0)[0][0] == "BAA"
        gb.run(5)
        tap(gb, "a")
        settled(gb, TITLE)


@pytest.mark.parametrize("model", MODES)
def test_classic_quit_uses_its_own_table(model):
    with rom_s(model) as gb:
        start_classic(gb)
        set_score(gb, 777)
        open_pause(gb)
        quit_yes(gb)
        settled(gb, GS_INITIALS)
        tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_SCORES, 20)
        assert table(gb, 2)[0][1] == 777 and table(gb, 0)[0][1] == 0
    with rom_s(model) as gb:
        start_classic(gb)
        open_pause(gb)
        quit_yes(gb)
        settled(gb, TITLE)
        assert table(gb, 2)[0][1] == 0


@pytest.mark.parametrize("model", MODES)
def test_saying_no_keeps_playing(model):
    with rom_s(model) as gb:
        start_arcade(gb)
        open_pause(gb)
        tap(gb, "down")
        tap(gb, "a")
        assert win_text(gb, 4).startswith(">")
        tap(gb, "a")                                      # NO
        tap(gb, "up")
        tap(gb, "a")                                      # RESUME
        assert state(gb) == PLAYING
        gb.run(30)
        assert state(gb) == PLAYING and gb.mem("story_on") == 1


# ---- (d) STORY ----------------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", MODES)
def test_story_quit_goes_to_the_title_and_continue_starts_from_the_save_point(model):
    from test_story import to_shift
    from test_scores import v7_image
    c = 2
    with to_shift(model, c, 1) as gb:                     # the lumber lodge's Happy hour: step 1 reached (saved)
        saved = (gb.mem("story_progress"), gb.mem("story_reached"))
        assert saved[1] > 0
        gb.run(60)
        open_pause(gb)
        quit_yes(gb)
        settled(gb, TITLE)
        assert gb.mem("story_on") == 0 and gb.mem("boss_on") == 0 and gb.mem("overlay_on") == 0
        assert (gb.mem("story_progress"), gb.mem("story_reached")) == saved, "nothing saved by the quit"
        title_pick(gb, K_PLAY, K_CONTINUE, press=False)
        assert K_CONTINUE in menu_items(gb), "the save is still there"
        menu_tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_GOAL, 120)
        gb.run(3)
        assert gb.mem("story_on") == 1 and gb.mem("story_chapter") == c and gb.mem("lives") == 3
        assert gb.mem("story_step") == 0, "CONTINUE starts the venue again (src/story.c story_begin)"


@pytest.mark.parametrize("model", MODES)
def test_story_quit_with_no_save_leaves_no_continue(model):
    from test_story import to_goal, start_story, skip_scene
    with start_story(model) as gb:
        skip_scene(gb)
        skip_scene(gb)
        to_goal(gb)
        gb.run(60)
        open_pause(gb)
        quit_yes(gb)
        settled(gb, TITLE)
        assert gb.mem("story_on") == 0 and gb.mem("story_progress") == 0 and gb.mem("story_reached") == 0
        title_pick(gb, K_PLAY)                            # PLAY's submenu
        assert K_CONTINUE not in menu_items(gb)


@pytest.mark.parametrize("model", MODES)
def test_a_boss_fight_quits_to_the_title_with_the_boss_gone(model):
    from boss_common import fight, play
    from test_bs import level_vram, palettes
    from test_story import BOSS_BUILT
    c = sorted(BOSS_BUILT)[0]
    with booted(model) as ref:
        hold_stage_anim(ref)
        title_pick(ref, K_PLAY, K_ARCADE)
        run_until(ref, lambda: state(ref) == PLAYING, 120)
        ref.run(60)
        fresh, pals = level_vram(ref), palettes(ref)
    with fight(model, c) as gb:
        play(gb)
        gb.run(40)
        assert gb.mem("boss_on") == 1
        saved = (gb.mem("story_progress"), gb.mem("story_reached"))
        open_pause(gb)
        quit_yes(gb)
        settled(gb, TITLE)
        assert gb.mem("boss_on") == 0 and gb.mem("story_on") == 0
        assert (gb.mem("story_progress"), gb.mem("story_reached")) == saved
        title_pick(gb, K_PLAY, K_ARCADE)
        run_until(gb, lambda: state(gb) == PLAYING, 120)
        gb.run(60)
        now = level_vram(gb)
        assert now[:252 * 16] == fresh[:252 * 16] and now[256 * 16:] == fresh[256 * 16:], "no boss tile is left in use"
        assert palettes(gb) == pals, "no boss palette is left"


# ---- (e) BOSS RUSH ------------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", MODES)
def test_boss_rush_quit_returns_to_its_menu_without_a_record(model):
    from test_rush import RS_MENU, SAVE, R, into_fight, on_rush, save_part, tap as rtap, to_list
    with rom_s(model) as gb:
        to_list(gb)
        part = save_part(gb)
        rtap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_GOAL, 60)
        gb.run(3)
        into_fight(gb)
        gb.run(120)
        assert gb.mem("play_mode") == 4
        open_pause(gb)
        quit_yes(gb)
        run_until(gb, lambda: on_rush(gb, RS_MENU), 60)
        gb.run(6)
        assert gb.mem("boss_on") == 0 and gb.mem("story_on") == 0 and gb.mem(NR51) == 0xFF
        assert save_part(gb) == part, "no time recorded"


# ---- (f) mini-games -----------------------------------------------------------------------------------------------------------------------
def mini_snapshot(gb):
    return (gb.read("story_scratch", 480), gb.mem16("mg_timer"), gb.mem16("mg_score"), gb.mem("mg_phase"), gb.mem("mg_t"), music(gb))


@pytest.mark.parametrize("model", MODES)
@pytest.mark.parametrize("gid", GAMES)
def test_every_mini_game_pauses_resumes_and_quits_to_the_list_with_everything_back(model, gid):
    from test_bs import level_vram, palettes
    from test_mg_list import best
    # the reference: a level straight from a boot
    with booted(model) as ref:
        hold_stage_anim(ref)
        title_pick(ref, K_PLAY, K_ARCADE, press=False)
        ref.write("title_go", 1)
        menu_tap(ref, "a")
        run_until(ref, lambda: state(ref) == PLAYING, 60)
        ref.run(62)
        fresh, pals = level_vram(ref), palettes(ref)

    def play_to(gb, t):
        mg_enter(gb, gid, MG_PRACTICE)
        until(gb, lambda: gb.mem("mg_phase") == MG_PLAY, 400)
        while gb.mem("mg_t") < t:
            frames(gb, 1)

    # uninterrupted control
    with rom_s(model) as ctl:
        play_to(ctl, 30)
        while ctl.mem("mg_t") < 60:
            frames(ctl, 1)
        want = (ctl.read("story_scratch", 480), gb_oam(ctl), ctl.mem16("mg_timer"), ctl.mem16("mg_score"))
    with rom_s(model) as gb:
        play_to(gb, 30)
        nr51 = gb.mem(NR51)
        mask = gb.mem("hUGE_mute_mask")
        medals = best(gb)
        glyphs = (tile(gb, GLYPH_J), tile(gb, GLYPH_Z))
        gb.hold("select")                                 # START + SELECT held: the debug box opens from a level's pause,
        gb.hold("start")                                  # never from a mini-game's
        gb.run(45)
        gb.release("start")
        gb.release("select")
        gb.run(3)
        assert state(gb) == PAUSED and gb.mem("overlay_on") == 1 and gb.mem(NR51) == 0
        assert menu_rows(gb)[0] == "PAUSE" and max(lines(gb)) <= 10
        frozen = mini_snapshot(gb)
        gb.run(90)
        assert mini_snapshot(gb) == frozen, "the mini-game and the tune stand still"
        assert state(gb) == PAUSED
        tap(gb, "start", 3)
        assert state(gb) == GS_MINI and gb.mem("overlay_on") == 0 and gb.mem(NR51) == nr51 and gb.mem(PAUSE_NR51) == 0
        assert gb.mem("hUGE_mute_mask") == mask
        assert (tile(gb, GLYPH_J), tile(gb, GLYPH_Z)) == glyphs
        while gb.mem("mg_t") < 60:
            frames(gb, 1)
        got = (gb.read("story_scratch", 480), gb_oam(gb), gb.mem16("mg_timer"), gb.mem16("mg_score"))
        if gid == MG_TAIKO:       # its clock is music_frames, and the music's tick runs on the frame RESUME is pressed (the
            assert got[0][2:] == want[0][2:] and 0 <= int.from_bytes(got[0][:2], "little") - int.from_bytes(want[0][:2], "little") <= 1
            assert got[2:] == want[2:]
        else:
            assert got[0] == want[0] and got[2:] == want[2:], "the game went on as if it had never stopped"
            assert got[1] == want[1], "the sprites the window covered are drawn again"
        # QUIT: the list, nothing recorded
        tap(gb, "start", 3)
        quit_yes(gb)
        settled(gb, GS_MGLIST)
        assert gb.mem(NR51) == 0xFF and gb.mem(PAUSE_NR51) == 0 and gb.mem("overlay_on") == 0
        assert gb.mem("hUGE_mute_mask") & 0x72 == 0, "Taiko's mute mask is gone"
        assert gb.mem("mg_phase") != MG_RESULT, "no result window: no medal"
        assert gb.mem(0xFF45) == gb.mem(0xFF4A) + 22, "the banner's LYC"
        assert gb.mem(0xFF43) == 0, "no street scroll"
        if model == "dmg":
            assert gb.mem(0xFF48) == 0xD0, "OBP0 as the boot sets it"
        assert gb.mem("_shadow_OAM_base") == gb.addr("shadow_OAM") >> 8, "OAM DMA is on"
        assert best(gb) == medals, "no medal recorded"
        quit_state = exit_state(gb)
        hits = []
        hook = gb.addr("mr_lcd_isr") & 0xFFFF
        gb.pb.hook_register(0, hook, lambda _: hits.append(1), None)
        gb.run(30)
        gb.pb.hook_deregister(0, hook)
        assert not hits, "Milk Run's LCD handler is gone"
        # a level after it is a level from a fresh boot (what the other mini-games' tests check after their normal leave)
        tap(gb, "b")                                      # the list's B: the title's BONUS submenu; its B: the top level
        settled(gb, TITLE)
        tap(gb, "b")
        gb.run(MENU_SETTLE)
        title_pick(gb, K_PLAY, K_ARCADE, press=False)
        gb.write("title_go", 1)
        menu_tap(gb, "a")
        run_until(gb, lambda: state(gb) == PLAYING, 60)
        gb.run(62)
        assert level_vram(gb) == fresh and palettes(gb) == pals
    if gid != MG_POUROFF:                                 # the Pour-Off has no result window: it only ends by winning (the story)
        with rom_s(model) as gb:                          # the normal leave: the result window, B
            play_to(gb, 61)               # (the quit path played this long: its START lands in the frame after the one that read 60)
            gb.write("mg_phase", MG_RESULT)
            until(gb, lambda: gb.mem("overlay_on") == 1, 20)
            frames(gb, 3)
            gb.press("b", 2)
            settled(gb, GS_MGLIST)
            assert exit_state(gb) == quit_state, "QUIT leaves what the normal leave leaves"


def gb_oam(gb):
    return bytes(gb.read(gb.addr("shadow_OAM"), 160))


def exit_state(gb):
    """What leaving a mini-game leaves: the whole VRAM, the palettes, the LCD / palette / scroll registers, the sound's mute mask
    and pan, the OAM DMA guard, and what the visible sprites draw (their tiles and palettes)."""
    from test_bs import palettes
    regs = [gb.mem(a) for a in (0xFF40, 0xFF42, 0xFF43, 0xFF47, 0xFF48, 0xFF49, 0xFF4A, 0xFF4B, 0xFF45, NR51)]
    regs += [gb.mem("hUGE_mute_mask"), gb.mem("_shadow_OAM_base"), gb.mem("overlay_on"), gb.mem("game_state")]
    sprites = []
    for i in range(40):
        y, x, t, p = (gb.mem(0xFE00 + 4 * i + k) for k in range(4))
        if y:
            sprites.append((y, x, t, p, bytes(gb.read(0x8000 + t * 16, 32))))
    pals = palettes(gb)
    if gb.model_name == "cgb":
        pals[MG_ICON_PAL] = None                          # (the medal icon's palette: the result window sets it, nothing else shows it)
    # VRAM, without the window map's rows 3-5 (0x9C60-0x9CBF: under the window, which is never shown past row 2 after a leave; the
    # result window and the pause menu each leave their own text there)
    vram = bytes(gb.read(0x8000, 0x1C60)) + bytes(gb.read(0x9CC0, 0x340))
    return vram, pals, regs, sprites


def from_the_list(model, leave):
    """BONUS > MINI GAMES, the second game played, left by `leave` (the result window's B, or the pause menu's QUIT); the list's
    state (exit_state) and the first game's best medal."""
    from test_mg_list import best, to_list
    with rom_s(model) as gb:
        to_list(gb)
        tap(gb, "down", 3)
        tap(gb, "a", 3)                                   # the second game: it borrows OBJ tiles and palettes
        run_until(gb, lambda: state(gb) == GS_MINI and gb.pb.memory[0xFF40] & 0x80, 60)
        until(gb, lambda: gb.mem("mg_phase") == MG_PLAY, 400)
        gb.run(5)
        leave(gb)
        settled(gb, GS_MGLIST)
        gb.run(5)
        return exit_state(gb), best(gb)


def finish_it(gb):
    gb.write("mg_phase", MG_RESULT)
    until(gb, lambda: gb.mem("overlay_on") == 1, 20)
    frames(gb, 3)
    gb.press("b", 2)


def quit_it(gb):
    tap(gb, "start", 3)
    quit_yes(gb)


@pytest.mark.parametrize("model", MODES)
def test_the_list_after_a_quit_is_the_list_after_a_finish_and_records_no_medal(model):
    """The leftover-cursor bug: the list entered after a mini-game must load the mug cursor (OBJ tiles, CGB palettes 1-2) itself.
    Through the real list: the second game, once left by finishing it and once by QUIT: the list shows the same (VRAM, palettes,
    registers, the cursor sprite), and QUIT records no medal."""
    done, best_done = from_the_list(model, finish_it)
    quit_, best_quit = from_the_list(model, quit_it)
    assert quit_ == done
    assert best_quit == [0] * 10 and best_quit[1] == 0


# ---- (g) mini-games inside a run ----------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", MODES)
@pytest.mark.parametrize("gid", [0, MG_MILKRUN, MG_TAIKO])
def test_a_story_mini_game_quits_to_the_title(model, gid):
    from test_story import start_story
    with start_story(model) as gb:
        saved = (gb.mem("story_progress"), gb.mem("story_reached"))
        mg_enter(gb, gid, MG_STORY)
        until(gb, lambda: gb.mem("mg_phase") == MG_PLAY, 400)
        gb.run(20)
        tap(gb, "start", 3)
        assert state(gb) == PAUSED
        quit_yes(gb)
        settled(gb, TITLE)
        assert gb.mem("story_on") == 0 and gb.mem(PAUSE_NR51) == 0 and gb.mem("hUGE_mute_mask") & 0x72 == 0
        assert gb.mem(0xFF45) == gb.mem(0xFF4A) + 22
        if model == "dmg":
            assert gb.mem(0xFF48) == 0xD0
        assert (gb.mem("story_progress"), gb.mem("story_reached")) == saved


@pytest.mark.parametrize("model", MODES)
def test_the_pour_off_quits_as_the_story_does(model):
    from test_story import start_story
    with start_story(model) as gb:
        mg_enter(gb, MG_POUROFF, MG_STORY)
        gb.run(120)
        tap(gb, "start", 3)
        assert state(gb) == PAUSED
        quit_yes(gb)
        settled(gb, TITLE)
        assert gb.mem("story_on") == 0 and gb.mem(PAUSE_NR51) == 0


@pytest.mark.parametrize("model", MODES)
def test_an_arcade_mini_game_quit_offers_the_initials(model):
    with rom_s(model) as gb:
        start_arcade(gb)
        assert gb.mem("story_arc") == 1
        mg_enter(gb, 0, MG_STORY)
        until(gb, lambda: gb.mem("mg_phase") == MG_PLAY, 400)
        set_score(gb, 1234)
        tap(gb, "start", 3)
        quit_yes(gb)
        settled(gb, GS_INITIALS)
        assert gb.mem("story_on") == 0 and gb.mem("story_arc") == 0
        tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_SCORES, 20)
        assert table(gb, 0)[0][1] == 1234


# ---- (h) the debug box still opens from a level's pause ---------------------------------------------------------------------------------
@pytest.mark.parametrize("model", MODES)
def test_the_debug_box_from_a_level_s_pause_puts_the_window_and_sound_back(model):
    with rom_s(model) as gb:
        start_arcade(gb)
        gb.hold("start")
        gb.run(2)
        gb.hold("select")
        gb.run(40)
        gb.release("start")
        gb.release("select")
        assert state(gb) == 7, "GS_DEBUG"
        assert gb.mem(NR51) == 0xFF and gb.mem(PAUSE_NR51) == 0 and gb.mem(0xFF45) == gb.mem(0xFF4A) + 22
        tap(gb, "b", 3)
        assert state(gb) == PLAYING and gb.mem("overlay_on") == 0
