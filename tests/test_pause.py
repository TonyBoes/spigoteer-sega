# The pause menu of every mode (src/pause.c): START opens RESUME / QUIT TO MENU (QUIT asks ARE YOU SURE?), gameplay stands still,
# the music plays on as the bass and the drums (NR51 0xCC; Taiko Pour and the Sumo fight, clocked by it, stand still and silent) until RESUME, and QUIT ends the run through the same exits as finishing it:
# STORY (shifts, boss fights, the Pour-Off): the title, the save untouched; ARCADE / CLASSIC: the initials when the score makes the
# top 5, else the title; mini-games: the list (practice, no medal) or as the run they are part of; BOSS RUSH: its menu, no time.
# Every mini-game's quit leaves what its normal leave leaves (OBP0, the LCD handler, the mute mask, OBJ / BG tiles, palettes).
import contextlib

import pytest
from conftest import double_speed
from split_helpers import win_lyc
from tick_helpers import FRAME
from conftest import unlock_debug
from conftest import K_ARCADE, K_CLASSIC, K_CONTINUE, K_PLAY, MENU_SETTLE, check_golden, hold_stage_anim, menu_items, \
    menu_tap, title_pick
from test_bonus import lines
from test_flow import GS_GOAL, GS_STORY, LEVEL_CLEAR, PLAYING, TITLE, inject_mug, run_until, state, tilemap_row
from test_mg import GLYPH_CH, GS_MGLIST, GS_MINI, MG_PLAY, MG_PRACTICE, MG_RESULT, MG_STORY, MG_STUB, frames, mg_enter, until
from test_scores import GS_INITIALS, GS_SCORES, booted, set_score, table
from test_sound import make_rom, save_ram

pytestmark = pytest.mark.timeout(300)

PAUSED = 5
MG_ICON_PAL = 4                          # mg.c: the medal icon's CGB BG palette
NR51, NR50 = 0xFF25, 0xFF24
BASS = 0xCC                              # NR51 while paused: channel 3 (the bass) and 4 (the drums) on both sides
BASS_ONLY = 0x44                         # ... while an effect that began before the menu still owns channel 4
PAUSE_NR51 = 0xFFF0                      # HRAM (game.h): the NR51 to restore while the menu is open, else 0
MODES = ["dmg", "cgb"]
MENU, ASK = 0, 1
GAMES = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, MG_STUB]       # mg.h: every mini-game incl. the Pour-Off, the three bonus rounds and the stub
MG_MILKRUN, MG_TAIKO, MG_POUROFF = 6, 7, 11
GLYPH_J, GLYPH_Z = 72, 75                                  # the '?' and the arrow take two rare letters' tiles while paused



def taiko_phase_ok(b):
    """Taiko's beat phase counters (tk_state p24 +145, q6 +146) follow its clock (+0): clk % 24 and clk / 24 % 6."""
    clk = int.from_bytes(b[:2], "little")
    return b[145] == clk % 24 and b[146] == (clk // 24) % 6

def rom_s(model, ram=None):
    """A booted rom with the emulator's sound on (the APU registers read back), on the title."""
    rom = make_rom(model, ram, sound=True)
    rom.run(120)
    hold_stage_anim(rom)
    return rom


CARD_FRAMES = 60                  # the card opens and closes through the white fade (src/pause.c CARD_FADE): about 8 frames out, 8 of LCD-off build, 8 in


def tap(gb, b, settle=3):
    gb.press(b, 2)
    gb.run(settle)


def win_text(gb, row):
    """The window's text row (rows 0-5: panel, 4 text rows, panel; the 5-row layouts end the window at row 4) with the '?' and the arrow decoded."""
    out = ""
    for t in tilemap_row(gb, row, 0, 20, True):
        out += "?" if t == GLYPH_J else ">" if t == GLYPH_Z else GLYPH_CH.get(t, " ")
    return out.strip()


def menu_rows(gb):
    """The menu's text rows; a story run's QUIT TO MAP reads as QUIT TO MENU here (its own label is checked in tests/test_story_resume.py)."""
    return [win_text(gb, r).replace("QUIT TO MAP", "QUIT TO MENU") for r in (1, 2, 3, 4)]


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
    want = ["> RESUME", "HOW TO PLAY", "QUIT TO MENU", ""] if gb.mem("boss_on") else ["", "> RESUME", "QUIT TO MENU", ""]   # (a boss fight has the hint card)
    assert menu_rows(gb) == want, menu_rows(gb)


def quit_yes(gb):
    """From the open menu: QUIT TO MENU, then YES."""
    mini = win_text(gb, 2).endswith("HOW TO PLAY")      # (a mini-game's menu has the HOW TO PLAY row between, its answers sit a row higher)
    for _ in range(2 if mini else 1):
        tap(gb, "down")
    tap(gb, "a")
    no, yes = (3, 2) if mini and not gb.mem("boss_on") else (4, 3)
    assert win_text(gb, 1) == "ARE YOU SURE?" and win_text(gb, no).startswith(">"), menu_rows(gb)
    tap(gb, "up")
    assert win_text(gb, yes).startswith(">") and win_text(gb, yes).endswith("YES")
    gb.press("a", 2)


def settled(gb, st, limit=60):
    if st == TITLE:                              # a story run's QUIT lands on the story map (tests/test_story_resume.py): START > QUIT TO TITLE goes on to the title
        from test_story_map import SP_MAP, tap as map_tap
        run_until(gb, lambda: state(gb) in (TITLE, GS_STORY) and gb.pb.memory[0xFF40] & 0x80, limit)
        if state(gb) == GS_STORY and gb.mem("story_phase") == SP_MAP:
            gb.run(100)
            map_tap(gb, "start", 20)
            gb.run(10)
            map_tap(gb, "down", 4)
            gb.press("a", 2)
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
        before_music, before_cyc = music(gb), gb.pb._cycles()
        tap(gb, "start", 3)
        assert state(gb) == PAUSED and gb.mem("overlay_on") == 1
        assert menu_rows(gb) == ["", "> RESUME", "QUIT TO MENU", ""], "two items, centred in the four text rows"
        assert tilemap_row(gb, 0, 0, 20, True) == [63] * 20 and tilemap_row(gb, 5, 0, 20, True) == [64] * 20   # the panels
        assert gb.mem(NR51) == BASS, "only the bass and the drums (channels 3 and 4) are on"
        assert gb.mem(PAUSE_NR51) == 0xFF
        assert win_lyc(gb.mem) == gb.mem(0xFF4A) + 46 and gb.mem(0xFF40) & 0x20, "the 48 px window"
        assert tile(gb, GLYPH_J) != glyphs[0] and tile(gb, GLYPH_Z) != glyphs[1], "the '?' and the arrow are loaded"
        assert max(lines(gb)) <= 10
        frozen = (gb.read("patron_state", 16), gb.read("mug_state", 12), gb.mem("bartender_x"), gb.mem16("score"),
                  gb.mem("spawn_timer"))
        m0, m0_cyc = music(gb), gb.pb._cycles()
        gb.hold("left")
        gb.run(120)
        gb.release("left")
        assert state(gb) == PAUSED and gb.mem(NR51) == BASS
        assert (gb.read("patron_state", 16), gb.read("mug_state", 12), gb.mem("bartender_x"), gb.mem16("score"),
                gb.mem("spawn_timer")) == frozen, "the game stands still"
        assert music(gb)[0] >= m0[0] + 110, "the tune plays on, 120 frames"
        # the tap's own frames play on at a tick a frame, no more (a pause that ticked twice, or the tune jumping): in real time, not
        # in the emulator's frames (how many ticks a 5-frame window holds is 4-6 by where the tune's phase falls)
        assert 0 <= m0[0] - before_music[0] <= (m0_cyc - before_cyc) / FRAME + 1.5, (before_music, m0, (m0_cyc - before_cyc) / FRAME)
        check_golden(gb, "pause_menu")
        tap(gb, "start", 3)
        assert state(gb) == PLAYING and gb.mem("overlay_on") == 0 and gb.mem(NR51) == 0xFF and gb.mem(PAUSE_NR51) == 0
        assert win_lyc(gb.mem) == gb.mem(0xFF4A) + 22, "the banner's LYC again"
        assert tilemap_row(gb, 0, 0, 20, True) == [63] * 20 and tilemap_row(gb, 1, 0, 20, True) == [54] * 20
        assert tilemap_row(gb, 2, 0, 20, True) == [64] * 20, "the banner's rows as win_init left them"
        assert (tile(gb, GLYPH_J), tile(gb, GLYPH_Z)) == glyphs, "the two letters are back"
        mf = gb.mem16("music_frames")
        assert mf >= m0[0] + 110, "the tune carried on through the pause"
        gb.run(90)
        assert gb.mem16("music_frames") > mf + 60, "and plays on"
        gb.run(1)


@pytest.mark.parametrize("model", MODES)
def test_music_advances_while_paused_with_only_the_harmony_and_the_bass_and_resume_restores_it(model):
    """The driver keeps ticking behind the menu (a frame a frame) with NR51 at channels 3 and 4 only; RESUME gives every channel back."""
    with rom_s(model) as gb:
        start_arcade(gb)
        gb.run(37)
        tap(gb, "start", 3)
        m = music(gb)
        for _ in range(5):
            gb.run(60)
            assert gb.mem(NR51) == BASS and gb.mem(PAUSE_NR51) == 0xFF
        n = music(gb)
        assert n[0] - m[0] >= 295 and (n[1], n[2]) != (m[1], m[2]), (m, n)
        tap(gb, "b", 1)                                  # B resumes too
        assert state(gb) == PLAYING and gb.mem(NR51) == 0xFF
        gb.run(60)
        assert gb.mem16("music_frames") >= n[0] + 55, "the tune goes on from where it got to"


@pytest.mark.parametrize("model", MODES)
def test_junk_in_the_pause_byte_at_power_on_does_not_mute_the_tunes(model):
    """HRAM is not cleared at power-on (real hardware, most emulators): main() clears PAUSE_NR51 first, so the title and a
    level play every channel, not the pause mix (owner 2026-10-15: "I'm getting pause music for everything")."""
    with make_rom(model, sound=True) as gb:
        gb.pb.memory[PAUSE_NR51] = 0x5A                  # before the first instruction
        gb.run(400)
        assert gb.mem(PAUSE_NR51) == 0 and gb.mem(NR51) == 0xFF
        hold_stage_anim(gb)
        start_arcade(gb)
        gb.run(120)
        assert gb.mem(NR51) == 0xFF


@pytest.mark.parametrize("model", MODES)
def test_no_effect_sounds_while_paused(model):
    """An effect that is still going when START lands stays off the speaker, and a request made meanwhile is not heard either."""
    with rom_s(model) as gb:
        start_arcade(gb)
        gb.write("sfx_req", 1 << 7)                       # SFX_LIFE (16+ frames: still going when START lands)
        gb.run(3)
        tap(gb, "start", 2)
        assert state(gb) == PAUSED
        for _ in range(40):
            gb.write("sfx_req", (1 << 6) | (1 << 3))      # a catch / serve-like pair on channels 1 and 4, every frame
            gb.run(2)
            assert gb.mem(NR51) in (BASS, BASS_ONLY), "channels 1 and 2 stay off the mix; channel 4 only carries the drums"
        gb.run(60)
        assert gb.mem(NR51) == BASS, "the held effect has ended, the requests were dropped: the drums are on channel 4 again"
        tap(gb, "start", 2)
        assert gb.mem(NR51) == 0xFF
        gb.run(120)
        assert not gb.mem("hUGE_mute_mask") & 8, "the effects ended and gave channel 4 back"


@pytest.mark.parametrize("model", MODES)
def test_the_sumo_fight_stands_still_and_silent_while_paused(model):
    """The Sumo's beat is counted on music_frames: his fight stops the tune and mutes every channel, as Taiko Pour does."""
    from boss_common import fight, play
    gb = fight(model, 7)
    play(gb)
    gb.run(30)
    assert gb.mem16("music_frames") > 20, "the tune plays"
    tap(gb, "start", 3)                                   # (this rom's APU is off: NR51 reads 0; the tick is what shows)
    assert state(gb) == PAUSED and gb.mem("boss_on") == 1 and gb.mem(PAUSE_NR51) != 0
    mf = gb.mem16("music_frames")
    gb.run(120)
    assert gb.mem16("music_frames") == mf, "the tune stands still"
    tap(gb, "start", 3)
    assert state(gb) == PLAYING and gb.mem(PAUSE_NR51) == 0
    gb.run(30)
    assert gb.mem16("music_frames") > mf + 20


@pytest.mark.parametrize("model", MODES)
def test_an_effect_in_progress_is_held_quietly_and_ends_after_resume(model):
    with rom_s(model) as gb:
        start_arcade(gb)
        gb.write("sfx_req", 1 << 6)                       # SFX_COIN... any effect
        gb.run(2)
        gb.write("sfx_req", 1 << 7)                       # SFX_LIFE (16 + frames: still going when START lands)
        gb.run(3)
        tap(gb, "start", 2)
        assert state(gb) == PAUSED and gb.mem(NR51) in (BASS, BASS_ONLY)
        gb.run(200)
        assert gb.mem(NR51) == BASS
        tap(gb, "start", 2)
        assert gb.mem(NR51) == 0xFF
        gb.run(120)
        assert not gb.mem("hUGE_mute_mask") & 8, "the effect ended and gave channel 4 back"
        assert gb.mem(NR51) == 0xFF


# ---- (a2) no flicker: every frame of a change shows the old menu or the new one, never a mix ----------------------------------------------
def screen_frames(gb, n):
    """The next n frames as images (each rendered: what the beam drew that frame)."""
    out = []
    for _ in range(n):
        gb.run(1, True)
        out.append(gb.image().tobytes())
    return out


def torn(gb, key, n=6):
    """Press key, then n frames: those that are neither the screen before nor the screen after."""
    gb.run(3)
    before = screen_frames(gb, 1)[0]
    gb.hold(key)
    gb.run(1)
    gb.release(key)
    seen = screen_frames(gb, n)
    gb.run(6)
    after = screen_frames(gb, 1)[0]
    assert before != after, key
    return [i for i, f in enumerate(seen) if f != before and f != after]


@pytest.mark.parametrize("model", MODES)
def test_a_cursor_move_and_the_question_never_show_a_half_drawn_menu(model):
    with rom_s(model) as gb:
        start_arcade(gb)
        tap(gb, "start", 3)
        for key in ("down", "up", "down", "a", "down", "up", "b"):      # 2 items: move, move, move, ask, YES/NO, YES/NO, back
            assert torn(gb, key) == [], key


@pytest.mark.parametrize("model", MODES)
def test_the_three_item_menu_and_its_card_never_show_a_half_drawn_menu(model):
    with rom_s(model) as gb:
        mg_enter(gb, 1, MG_PRACTICE)
        until(gb, lambda: gb.mem("mg_phase") == MG_PLAY, 400)
        tap(gb, "start", 3)
        for key in ("down", "down", "down", "up", "a", "up", "b"):      # 3 items: moves, the question (5 rows to 5), back
            assert torn(gb, key) == [], key


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
        assert menu_rows(gb) == ["ARE YOU SURE?", "", "YES", "> NO"], "the question and its answers fill the four text rows"
        assert win_lyc(gb.mem) == gb.mem(0xFF4A) + 46, "the 48 px window"
        for key in ("a", "b", "start"):                   # NO, B and START all go back to the menu (the cursor on QUIT)
            tap(gb, key)
            assert state(gb) == PAUSED and menu_rows(gb) == ["", "RESUME", "> QUIT TO MENU", ""], key
            assert win_lyc(gb.mem) == gb.mem(0xFF4A) + 46, "the 48 px window"
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
        assert win_lyc(gb.mem) == gb.mem(0xFF4A) + 22
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
    with to_shift(model, c, 1, image=sv_image(c, 1, c, 12345)) as gb:   # the lumber lodge's Happy hour: step 1 reached (saved)
        saved = (gb.mem("story_progress"), gb.mem("story_reached"))
        assert saved[1] > 0
        gb.run(60)
        set_score(gb, 54321)   # scored on in the venue (below the 20,000 life)
        open_pause(gb)
        quit_yes(gb)
        settled(gb, TITLE)
        assert gb.mem("story_on") == 0 and gb.mem("boss_on") == 0 and gb.mem("overlay_on") == 0
        assert (gb.mem("story_progress"), gb.mem("story_reached")) == saved, "nothing saved by the quit"
        title_pick(gb, K_PLAY, K_CONTINUE, press=False)
        assert K_CONTINUE in menu_items(gb), "the save is still there"
        menu_tap(gb, "a")
        from test_story import through_the_map
        through_the_map(gb)                                   # (CONTINUE lands on the story map: A at the next venue)
        run_until(gb, lambda: state(gb) == GS_GOAL, 120)
        gb.run(3)
        assert gb.mem("story_on") == 1 and gb.mem("story_chapter") == c and gb.mem("lives") == 3
        assert gb.mem("story_step") == 0, "CONTINUE starts the venue again (src/story.c story_begin)"
        assert score_of(gb) == 12345, "the score the venue was entered with, not the one reached in it (owner 2026-10-14)"
        assert gb.read("score_digits", 6) == bytes([0, 1, 2, 3, 4, 5])


def sv_image(story, step, chapter, score, bad=False):
    """A version-7 save with the venue-start score block (save.c SV_AT 0x0A) for `chapter`."""
    from test_scores import v7_image
    r = bytearray(v7_image([], story=story, step=step))
    b = bytes([ord("S"), ord("V"), chapter]) + score.to_bytes(3, "little")
    c = (0x5A + sum(b)) & 255
    r[0x0A:0x12] = b + bytes([c ^ 1 if bad else c, c ^ 0xFF])
    return bytes(r)


def score_of(gb):
    return int.from_bytes(gb.read("score", 4), "little")


@pytest.mark.parametrize("model", MODES)
@pytest.mark.parametrize("img,want", [(sv_image(2, 0, 2, 777), 777), (sv_image(2, 0, 1, 777), 0), (sv_image(2, 0, 2, 777, bad=True), 0),
                                      (sv_image(2, 0, 2, 1000000), 0)])
def test_continue_takes_the_venue_start_score_only_when_it_checks_out(model, img, want):
    from test_story import start_story
    with start_story(model, img, cont=True) as gb:        # the PRE scene of chapter 2
        assert gb.mem("story_chapter") == 2 and gb.mem("lives") == 3
        assert score_of(gb) == want, "another chapter's, a bad checksum or a score out of range reads as 0"


@pytest.mark.parametrize("model", MODES)
def test_an_older_save_without_the_block_continues_with_score_0(model):
    from test_scores import v7_image
    from test_story import start_story
    with start_story(model, v7_image([], story=2, step=0), cont=True) as gb:
        assert score_of(gb) == 0


@pytest.mark.parametrize("model", MODES)
def test_entering_a_venue_keeps_its_start_score(model):
    from test_story import start_story, skip_scene
    from test_scores import saved_story
    with start_story(model, sv_image(2, 0, 2, 777), cont=True) as gb:
        assert score_of(gb) == 777
        set_score(gb, 4321)
        skip_scene(gb)                                    # the PRE scene ends: the venue is entered with 4321
        run_until(gb, lambda: state(gb) == GS_GOAL, 120)
        ram = save_ram(gb)
    assert ram[0x0A:0x0C] == b"SV" and ram[0x0C] == 2 and int.from_bytes(ram[0x0D:0x10], "little") == 4321
    assert (0x5A + sum(ram[0x0A:0x10])) & 255 == ram[0x10] and ram[0x11] == ram[0x10] ^ 0xFF


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
def mini_snapshot(gb, gid=None):
    """What stands still while paused. The tune does too only where the game is clocked by it (Taiko Pour)."""
    return (gb.read("story_scratch", 480), gb.mem16("mg_timer"), gb.mem16("mg_score"), gb.mem("mg_phase"), gb.mem("mg_t")) \
        + ((music(gb),) if gid == MG_TAIKO else ())


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
        unlock_debug(gb)                                  # the debug menu opens from a level's pause (SELECT held, START tapped three times),
        gb.hold("select")                                 # never from a mini-game's: here SELECT + START is a plain pause
        gb.run(2)
        gb.press("start", 2)
        gb.run(3)
        gb.release("select")
        gb.run(3)
        assert gb.mem("debug_menu_open") == 0
        assert state(gb) == PAUSED and gb.mem("overlay_on") == 1 and gb.mem(NR51) == (0 if gid == MG_TAIKO else BASS)
        assert menu_rows(gb)[:3] == ["> RESUME", "HOW TO PLAY", "QUIT TO MENU"] and max(lines(gb)) <= 10
        frozen = mini_snapshot(gb, gid)
        gb.run(90)
        assert mini_snapshot(gb, gid) == frozen, "the mini-game stands still (Taiko's tune too)"
        assert state(gb) == PAUSED
        tap(gb, "start", 3)
        assert state(gb) == GS_MINI and gb.mem("overlay_on") == 0 and gb.mem(NR51) == nr51 and gb.mem(PAUSE_NR51) == 0
        assert gb.mem("hUGE_mute_mask") == mask
        assert (tile(gb, GLYPH_J), tile(gb, GLYPH_Z)) == glyphs
        while gb.mem("mg_t") < 60:
            frames(gb, 1)
        got = (gb.read("story_scratch", 480), gb_oam(gb), gb.mem16("mg_timer"), gb.mem16("mg_score"))
        if gid == MG_TAIKO:       # its clock is music_frames, and the music's tick runs on the frame RESUME is pressed (the
            assert got[0][2:145] == want[0][2:145] and taiko_phase_ok(got[0]) and taiko_phase_ok(want[0]) and 0 <= int.from_bytes(got[0][:2], "little") - int.from_bytes(want[0][:2], "little") <= 1
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
        assert win_lyc(gb.mem) == gb.mem(0xFF4A) + 22, "the banner's LYC"
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
        assert win_lyc(gb.mem) == gb.mem(0xFF4A) + 22
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


# ---- (h) the debug menu still opens from a level's pause ---------------------------------------------------------------------------------
@pytest.mark.parametrize("model", MODES)
def test_the_debug_box_from_a_level_s_pause_puts_the_window_and_sound_back(model):
    with rom_s(model) as gb:
        start_arcade(gb)
        unlock_debug(gb)
        tap(gb, "start", 3)
        assert state(gb) == PAUSED
        gb.hold("select")                                 # SELECT held, START tapped three times (src/debug.c)
        gb.run(2)
        for _ in range(3):
            gb.press("start", 2)
            gb.run(3)
        gb.release("select")
        gb.run(6)                                         # (the menu comes up with the LCD off for a few frames)
        assert state(gb) == 7, "GS_DEBUG"
        assert gb.mem(NR51) == 0xFF and gb.mem(PAUSE_NR51) == 0 and win_lyc(gb.mem) == 255, "the pause is closed (sound back), the menu's window covers the screen"
        tap(gb, "b", 3)
        assert state(gb) == PLAYING and gb.mem("overlay_on") == 0
        assert win_lyc(gb.mem) == gb.mem(0xFF4A) + 22, "the banner window's LYC is back"


# ---- (g) HOW TO PLAY from the pause menu (mini-games: the card over the whole screen, the game as it was after it) ----------------------
def card_rows(gb):
    """The window's 18 rows as text (the story font's punctuation decoded as in test_mg_card)."""
    from test_mg_card import row_text
    out = []
    for r in range(18):
        t = ""
        for v in tilemap_row(gb, r, 0, 20, True):
            t += GLYPH_CH.get(v, __import__("test_mg_card").PUNCT.get(v, " ")) if v != 54 else " "
        out.append(t.strip())
    return out


def screen_state(gb):
    """What the game needs back: tiles and the BG map (the window map's rows 0-5 aside: the menu's own), palettes, registers, OAM."""
    from test_bs import palettes
    regs = [gb.mem(a) for a in (0xFF40, 0xFF42, 0xFF43, 0xFF45, 0xFF4A, 0xFF4B, NR51)] + [gb.mem("overlay_on"), gb.mem("game_state")]
    return (bytes(gb.read(0x8000, 0x1C00)), bytes(gb.read(0x9CC0, 0x340)), palettes(gb), regs, gb_oam(gb))


@pytest.mark.parametrize("model", MODES)
def test_a_mini_game_pause_menu_has_three_rows_and_the_level_two(model):
    with rom_s(model) as gb:
        mg_enter(gb, 1, MG_PRACTICE)
        until(gb, lambda: gb.mem("mg_phase") == MG_PLAY, 400)
        tap(gb, "start", 3)
        assert state(gb) == PAUSED
        assert menu_rows(gb) == ["> RESUME", "HOW TO PLAY", "QUIT TO MENU", ""], "three items, centred in the three rows of the 5-row window"
        assert win_lyc(gb.mem) == gb.mem(0xFF4A) + 38 and tilemap_row(gb, 4, 0, 20, True) == [64] * 20, "the 40 px window, its panel on row 4"
        check_golden(gb, "pause_menu_mini")
        tap(gb, "up")
        assert win_text(gb, 3).startswith(">"), "up wraps to QUIT"
        tap(gb, "down")
        assert win_text(gb, 1).startswith(">")
        tap(gb, "down")
        assert win_text(gb, 2).startswith(">")


@pytest.mark.parametrize("model", MODES)
def test_milk_runs_handler_ends_the_window_after_five_rows_in_both_menus(model):
    """Milk Run walks LYC itself (main.c mr_lcd_isr): the mini-game's menu and its question are 5 rows (WY + 38), never 6."""
    with rom_s(model) as gb:
        mg_enter(gb, MG_MILKRUN, MG_PRACTICE)
        until(gb, lambda: gb.mem("mg_phase") == MG_PLAY, 400)
        tap(gb, "start", 3)
        for step in range(2):
            gb.run(6)
            im, wy = gb.image(), gb.mem(0xFF4A)
            bg = im.getpixel((0, wy + 12))                # the menu's flat background
            assert im.getpixel((0, wy + 28)) == bg, "inside the window"
            assert im.getpixel((0, wy + 42)) != bg and im.getpixel((0, wy + 44)) != bg, (step, "the window is over after 5 rows")
            if step == 0:
                tap(gb, "down")
                tap(gb, "down")
                tap(gb, "a")                              # the question
                assert win_text(gb, 1) == "ARE YOU SURE?"


@pytest.mark.parametrize("model", MODES)
@pytest.mark.parametrize("gid", GAMES)
def test_how_to_play_from_the_pause_menu_and_back_leaves_everything_as_it_was(model, gid):
    def play_to(gb, t):
        mg_enter(gb, gid, MG_PRACTICE)
        until(gb, lambda: gb.mem("mg_phase") == MG_PLAY, 400)
        while gb.mem("mg_t") < t:
            frames(gb, 1)

    with rom_s(model) as ctl:                             # uninterrupted
        play_to(ctl, 30)
        while ctl.mem("mg_t") < 60:
            frames(ctl, 1)
        want = (ctl.read("story_scratch", 480), gb_oam(ctl), ctl.mem16("mg_timer"), ctl.mem16("mg_score"))
    with rom_s(model) as gb:
        play_to(gb, 30)
        tap(gb, "start", 3)
        assert state(gb) == PAUSED
        before = screen_state(gb)
        tap(gb, "down")
        assert win_text(gb, 2).startswith(">") and win_text(gb, 2).endswith("HOW TO PLAY")
        tap(gb, "a", CARD_FRAMES)
        assert state(gb) == PAUSED and gb.mem(NR51) == (0 if gid == MG_TAIKO else BASS)
        rows = card_rows(gb)
        assert rows[1] == "HOW TO PLAY" and rows[5] != "", rows
        assert gb.mem(0xFF4A) == 0 and gb.mem(0xFF40) & 0x20 and not gb.mem(0xFF40) & 2, "the window over the screen, sprites off"
        gb.run(60)
        assert state(gb) == PAUSED
        tap(gb, "b", CARD_FRAMES)
        assert menu_rows(gb)[:3] == ["RESUME", "> HOW TO PLAY", "QUIT TO MENU"]
        assert screen_state(gb) == before, "the game's tiles, map, palettes, sprites and registers are as they were"
        tap(gb, "up")
        tap(gb, "start", 3)                               # (cursor on RESUME: START resumes in any case)
        assert state(gb) == GS_MINI and gb.mem("overlay_on") == 0 and gb.mem(NR51) != 0
        while gb.mem("mg_t") < 60:
            frames(gb, 1)
        got = (gb.read("story_scratch", 480), gb_oam(gb), gb.mem16("mg_timer"), gb.mem16("mg_score"))
        if gid == MG_TAIKO:
            assert got[0][2:145] == want[0][2:145] and taiko_phase_ok(got[0]) and taiko_phase_ok(want[0]) and got[2:] == want[2:]
        else:
            assert got[0] == want[0] and got[2:] == want[2:], "the game went on as if it had never stopped"
            assert got[1] == want[1]


@pytest.mark.parametrize("model", MODES)
def test_the_card_in_the_pause_menu_turns_pages_and_a_on_the_last_comes_back(model):
    """The stub has a two-page card: NEXT on page 1 (A turns), A BACK on page 2 (A returns to the menu); B returns from either."""
    with rom_s(model) as gb:
        mg_enter(gb, MG_STUB, MG_PRACTICE)
        until(gb, lambda: gb.mem("mg_phase") == MG_PLAY, 400)
        tap(gb, "start", 3)
        gb.run(1, True)                                    # (PyBoy's first rendered frame of a session draws a window from its line 1: render one first)
        tap(gb, "down")
        tap(gb, "a", CARD_FRAMES)
        rows = card_rows(gb)
        assert rows[5] == "GREEN LIGHT" and rows[7] == "PRESS A ON GREEN" and rows[16] == "NEXT", rows
        from test_flow import tilemap_row
        from test_mg_card import FONT_BASE
        assert tilemap_row(gb, 0, 0, 20, window=True)[0] == FONT_BASE + 7 and tilemap_row(gb, 3, 0, 20, window=True)[9] == FONT_BASE + 15, "frame and icon"
        assert not gb.mem(0xFF40) & 2, "sprites off on the card"
        check_golden(gb, "card_stub_page1")  # (the same picture as test_mg_card.py)
        tap(gb, "a", CARD_FRAMES)
        rows = card_rows(gb)
        assert rows[5] == "GREEN LIGHT" and rows[7] == "EARLY IS A MISS" and rows[16] == "A BACK", rows
        tap(gb, "a", CARD_FRAMES)
        assert win_text(gb, 2) == "> HOW TO PLAY" and state(gb) == PAUSED
        tap(gb, "a", CARD_FRAMES)                                   # the card again: page 1
        assert card_rows(gb)[7] == "PRESS A ON GREEN"
        tap(gb, "a", CARD_FRAMES)
        tap(gb, "b", CARD_FRAMES)                                   # B on page 2 returns too
        assert win_text(gb, 2) == "> HOW TO PLAY"
        tap(gb, "up")
        tap(gb, "a", CARD_FRAMES)
        assert state(gb) == GS_MINI


# ---- (h) the card swaps in and out with no frame of the game, and fills the screen exactly (owner 2026-10-15, Batch H) ----------------
def render(gb):
    gb.run(1, True)
    return gb.image()


def press_frames(gb, key, n):
    """Press key for 2 frames then release, rendering every frame (gb.press skips them); the n images."""
    out = []
    gb.pb.button_press(key)
    for i in range(n):
        if i == 2:
            gb.pb.button_release(key)
        out.append(render(gb))
    return out


def press_wy(gb, key, n):
    """press_frames, with the window's WY and the LCD bit each frame: [(image, WY, lcd on)]."""
    out = []
    gb.pb.button_press(key)
    for i in range(n):
        if i == 2:
            gb.pb.button_release(key)
        im = render(gb)
        out.append((im, gb.mem(0xFF4A), bool(gb.mem(0xFF40) & 0x80)))
    return out


@pytest.mark.parametrize("model", MODES)
@pytest.mark.parametrize("gid", [MG_STUB, MG_MILKRUN])
def test_no_frame_shows_the_game_between_the_menu_and_the_card(model, gid):
    """The card swaps through the white fade (CARD_FADE): the menu fades to white, the LCD goes off in it, the card fades in from white. Every frame from the LCD going off
    on has the window over the whole screen (WY 0): the paused game is never between them; the first frame is the menu, the last the finished card, and back."""
    with rom_s(model) as gb:
        mg_enter(gb, gid, MG_PRACTICE)
        until(gb, lambda: gb.mem("mg_phase") == MG_PLAY, 400)
        tap(gb, "start", 3)
        render(gb)
        tap(gb, "down")
        menu = render(gb).tobytes()
        gb.run(1)
        for key in ("a", "b"):
            fr = press_wy(gb, key, CARD_FRAMES)
            off = [i for i, f in enumerate(fr) if not f[2]]
            assert off and off == list(range(off[0], off[-1] + 1)), "the LCD goes off once, in the white"
            before, after = (64, 0) if key == "a" else (0, 64)
            assert all(f[1] == before for f in fr[:off[0]]) and all(f[1] == after for f in fr[off[-1] + 1:]), [f[1] for f in fr]
            assert len(fr[off[0]][0].getcolors()) == 1, "the LCD goes off in white"
            if key == "a":
                assert fr[0][0].tobytes() == menu, "the first frame is the menu"
                card = fr[-1][0].tobytes()
            else:
                assert fr[0][0].tobytes() == card and fr[-1][0].tobytes() == menu


@pytest.mark.parametrize("model", MODES)
def test_the_card_fills_the_screen_exactly(model):
    """Lines 0-7 are the frame's top tile and lines 136-143 its bottom tile (no row lost on top, none of the game below)."""
    with rom_s(model) as gb:
        mg_enter(gb, MG_STUB, MG_PRACTICE)
        until(gb, lambda: gb.mem("mg_phase") == MG_PLAY, 400)
        tap(gb, "start", 3)
        render(gb)
        tap(gb, "down")
        tap(gb, "a", CARD_FRAMES)
        im = render(gb)
        assert gb.mem(0xFF4A) == 0 and gb.mem(0xFF4B) == 7
        for map_row, y0 in ((0, 0), (17, 136)):
            t = tile(gb, tilemap_row(gb, map_row, 0, 20, True)[1])
            idx = [sum((((t[2 * r + p] >> 4) & 1) << p) for p in (0, 1)) for r in range(8)]     # (the tile's pixel at x 3 of each row)
            cols = [im.getpixel((8 + 3, y0 + r)) for r in range(8)]
            for a in range(8):
                for b in range(8):
                    assert (idx[a] == idx[b]) == (cols[a] == cols[b]), (map_row, a, b, idx, cols)


# ---- (i) boss hint pages: HOW TO PLAY in every boss fight (Batch H, owner-approved Batch E item) ------------------------------------------
def _bosses():
    from test_story import BOSS_BUILT
    return sorted(BOSS_BUILT)


def boss_cards():
    """src/mg_card.c's boss pages: {boss id: (name, [page 1 lines], [page 2 lines])}."""
    import re
    from conftest import ROOT
    src = (ROOT / "src" / "mg_card.c").read_text()
    out = {}
    for i, m in enumerate(re.finditer(r'/\* B_\w+\s*\*/ \{ "([^"]*)", \{ "([^"]*)", "([^"]*)", "([^"]*)", "([^"]*)" \} \},', src)):
        out[i] = [m.group(1), list(m.groups()[1:]), None]
    for m in re.finditer(r'\{ MG_BOSS_CARD \+ (\d+), \{ "([^"]*)", "([^"]*)", "([^"]*)", "([^"]*)" \} \},', src):
        out[int(m.group(1))][2] = [t.replace("\\001", "\x01").replace("\\002", "\x02") for t in m.groups()[1:]]   # (\001 ROOM mug, \002 TAKEN mug)
    return out


def shown(lines):
    """A page's lines as card_rows reads them: the two capacity mugs are the story font's '!' (ROOM) and '?' (TAKEN) tiles, loaded over."""
    return [t.translate({1: "!", 2: "?"}).strip() for t in lines]


def test_every_boss_has_a_hint_card_of_one_or_two_pages_with_short_plain_lines():
    import re
    cards = boss_cards()
    assert sorted(cards) == list(range(10))
    for b, (name, p1, p2) in cards.items():
        for t in [name] + p1 + (p2 or []):
            assert re.fullmatch(r"[A-Z0-9 .,!?:'\x01\x02-]*", t) and len(t) <= 18, (b, t)
        assert p1[0] and (p2 is None or p2[0])


@pytest.mark.parametrize("model", MODES)
@pytest.mark.parametrize("c", _bosses())
def test_a_boss_fight_pause_menu_opens_his_hint_card(model, c):
    from boss_common import fight, play
    name, p1, p2 = boss_cards()[c]
    with fight(model, c) as gb:
        play(gb)
        gb.run(40)
        tap(gb, "start", 3)
        gb.run(1, True)
        assert state(gb) == PAUSED and menu_rows(gb) == ["> RESUME", "HOW TO PLAY", "QUIT TO MENU", ""], menu_rows(gb)
        assert win_lyc(gb.mem) == gb.mem(0xFF4A) + 46 and tilemap_row(gb, 5, 0, 20, True) == [64] * 20, "the 6-row window, its panel on row 5"
        if c == 0:
            check_golden(gb, "pause_menu_boss")
        tap(gb, "down")
        tap(gb, "a", CARD_FRAMES)
        rows = card_rows(gb)
        assert rows[1] == "HOW TO PLAY" and rows[5] == name and rows[7:14:2] == p1, rows
        assert rows[16] == ("NEXT" if p2 else "A BACK") and not gb.mem(0xFF40) & 2, "sprites off on the card"
        if c in (0, 7):
            check_golden(gb, f"pause_card_boss{c}_p1")
        if p2:
            tap(gb, "a", CARD_FRAMES)
            rows = card_rows(gb)
            assert rows[5] == name and rows[7:14:2] == shown(p2) and rows[16] == "A BACK", rows
            if c in (0, 7):
                check_golden(gb, f"pause_card_boss{c}_p2")
        tap(gb, "a", CARD_FRAMES)
        assert win_text(gb, 2) == "> HOW TO PLAY" and state(gb) == PAUSED
        tap(gb, "down")                                # the question: rows 3-4 as in a level, NO the cursor
        tap(gb, "a")
        assert menu_rows(gb) == ["ARE YOU SURE?", "", "YES", "> NO"], menu_rows(gb)
        tap(gb, "a")
        assert menu_rows(gb) == ["RESUME", "HOW TO PLAY", "> QUIT TO MENU", ""], menu_rows(gb)


@pytest.mark.parametrize("model", MODES)
def test_big_texs_second_page_shows_the_capacity_mugs_and_the_font_comes_back(model):
    """Rev 4: page 2 has 3 ROOM / TAKEN mug tiles (the font's '!' and '?' tiles loaded over) before each of the first three lines; closing puts the font back."""
    from boss_common import fight, play
    import re
    from conftest import ROOT
    src = (ROOT / "src" / "mg_card.c").read_text()
    body = re.search(r"cap_tiles\[32\] = \{([^}]*)\}", src).group(1)
    want = bytes(int(x, 16) for x in re.findall(r"0x[0-9A-Fa-f]{2}", body))
    with fight(model, 0) as gb:
        play(gb)
        gb.run(40)
        excl, quest = _glyph_ids()
        font = (tile(gb, excl), tile(gb, quest))      # (in a fight these ids hold his art)
        tap(gb, "start", 3)
        tap(gb, "down")
        tap(gb, "a", CARD_FRAMES)
        assert font[0] + font[1] != want
        tap(gb, "a", CARD_FRAMES)
        room, taken = tile(gb, excl), tile(gb, quest)
        assert room + taken == want and room != taken
        pattern = [(excl, excl, excl), (quest, excl, excl), (quest, quest, quest)]
        for k, p in enumerate(pattern):
            assert tuple(tilemap_row(gb, 7 + 2 * k, 0, 20, True)[2:5]) == p, k
        assert tilemap_row(gb, 13, 0, 20, True)[2] not in (excl, quest)
        check_golden(gb, "pause_card_tex_mugs_p2")
        tap(gb, "a", CARD_FRAMES)
        assert (tile(gb, excl), tile(gb, quest)) == font, "the '!' and '?' tiles are back"


def _glyph_ids():
    import re
    from conftest import ROOT
    h = (ROOT / "build" / "story.h").read_text()
    base = int(re.search(r"STORY_PORTRAIT_BASE != (\d+)", h).group(1)) - 16
    return base + 2, base + 3


@pytest.mark.parametrize("model", MODES)
@pytest.mark.parametrize("c", (1, 7))
def test_the_mascots_and_the_sumos_one_page_cards_close_on_a(model, c):
    """Rev 4: the Mascot and the Sumo have a single page: the prompt reads A BACK at once and A closes the card."""
    from boss_common import fight, play
    with fight(model, c) as gb:
        play(gb)
        gb.run(40)
        tap(gb, "start", 3)
        tap(gb, "down")
        tap(gb, "a", CARD_FRAMES)
        rows = card_rows(gb)
        assert rows[1] == "HOW TO PLAY" and rows[16] == "A BACK", rows
        tap(gb, "a", CARD_FRAMES)
        assert win_text(gb, 2) == "> HOW TO PLAY" and state(gb) == PAUSED


def _boss_state(gb):
    """The picture, the boss's own buffers and the counters: what 'the same as uninterrupted' means for a fight."""
    from test_bs import palettes
    return (bytes(gb.read(0x8000, 0x1800)), bytes(gb.read(0x9800, 0x400)), gb_oam(gb), gb.read("story_scratch", 480),
            gb.mem("boss_hp"), gb.mem("boss_on"), gb.mem("game_state"), palettes(gb))


# The fights whose Color frames, with the venue's mid-frame palette chain and its Color-only looks, overrun at normal speed (the Chrome Cow's Duke:
# 15 missed frames in 130, so the two runs below differ by a frame's phase): they run at double speed, the way the game ships (owner Q92).
HEAVY_FIGHTS = {6}


@pytest.mark.parametrize("model", MODES)
@pytest.mark.parametrize("c", _bosses())
def test_a_boss_hint_card_and_back_leaves_the_fight_as_if_it_had_not_been_opened(model, c):
    """Pause, read the pages, back, RESUME == pause, RESUME: tiles (the font tiles the card saves hold boss art), maps, palettes, OAM, his state."""
    from boss_common import fight, play

    def run(card):
        with (double_speed() if model == "cgb" and c in HEAVY_FIGHTS else contextlib.nullcontext()), fight(model, c) as gb:
            play(gb)
            gb.run(40)
            tap(gb, "start", 3)
            menu = _boss_state(gb)
            if card:
                tap(gb, "down")
                tap(gb, "a", CARD_FRAMES)
                while card_rows(gb)[16] != "A BACK":
                    tap(gb, "a", CARD_FRAMES)
                gb.run(30)
                tap(gb, "b", CARD_FRAMES)
                assert menu_rows(gb)[:3] == ["RESUME", "> HOW TO PLAY", "QUIT TO MENU"]
                assert _boss_state(gb)[:4] + _boss_state(gb)[7:] == menu[:4] + menu[7:], "the menu is as it was"
                tap(gb, "up")
            tap(gb, "start", 3)
            assert state(gb) == PLAYING and gb.mem("overlay_on") == 0
            gb.run(90)
            return _boss_state(gb)

    assert run(True) == run(False), "the fight went on as if the card had never opened"


# --- the pause mix is the bass and the drums (owner 2026-10-17): channels 3 and 4 only, on every tune a level can pause ---

def _pause_tunes():
    import songs
    return [("venue_" + n, 5 + i, n) for i, n in enumerate(songs.VENUES)] + [("show", 4, "galop")]


@pytest.mark.parametrize("model", MODES)
@pytest.mark.parametrize("tune_id,tune,song", _pause_tunes(), ids=[t[0] for t in _pause_tunes()])
def test_pause_mix_routes_only_the_bass_and_the_drums_on_every_tune(model, tune_id, tune, song):
    """Paused, NR51 routes channel 3 (bass) and channel 4 (drums) to both sides and nothing else: the melody and the
    counter-melody (channels 2 and 1) drop out. Resume gives the full mix back."""
    from test_art import goto_group
    from test_sound import start_a_show, start_game
    with rom_s(model) as gb:
        start_game(gb)
        if tune_id == "show":
            start_a_show(gb)
        else:
            goto_group(gb, tune - 5)
        gb.run(400)                                       # (the show tune is copied in the background)
        if tune_id == "show":
            gb.write("show_timer", 2000 & 255); gb.write(gb.addr("show_timer") + 1, 2000 >> 8)
        assert gb.mem("cur_tune") == tune
        tap(gb, "start", 3)
        assert state(gb) == PAUSED
        nr51 = gb.mem(NR51)
        assert nr51 == 0xCC, hex(nr51)
        assert nr51 & 0x33 == 0 and nr51 & 0x0C == 0x0C and nr51 & 0xC0 == 0xC0 and (nr51 >> 4) == (nr51 & 0xF)
        gb.run(60)
        assert gb.mem(NR51) == 0xCC
        tap(gb, "start", 3)
        assert state(gb) == PLAYING and gb.mem(NR51) == 0xFF


def test_which_tunes_have_no_drums_so_their_pause_mix_is_the_bass_alone():
    """The tunes with no channel-4 line and no groove: the two jingles Level Clear and Game Over and the credits tune.
    None of them can be paused (no level, no mini-game plays them); every other tune has drums."""
    import gen_music as gm
    import songs
    none = sorted(n for n, j in gm.JINGLES.items() if not j.get("ch4"))
    none += sorted(n for n, s in songs.SONGS.items() if not s["ch4"] and not s["groove"])
    assert none == ["clear", "over", "credits"]
