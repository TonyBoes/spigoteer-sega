# The title's BONUS > MINI GAMES (src/mg_list.c; Practice, docs/minigames_bosses.md 2.3) and Practice's SRAM block at
# 0x40 (src/save.c): the BONUS submenu's second item, the list (every built game; the DEBUG_MENU build all unlocked
# with the stub, `make release` Quick Draw, Order Up! and Battery Sort with the unlock rule), A plays in MG_PRACTICE, the result's A retries
# and B comes back to the list, the list's B goes back to BONUS; a game is unlocked once STORY or ARCADE reaches it
# (a debug-select run records nothing), its best medal is kept, and the block survives a reset; a bad block is nothing
# unlocked and leaves the other blocks alone.
import re
import subprocess
from io import BytesIO

import pytest
from conftest import (K_BONUS, K_BOSSRUSH, K_CREDITS, K_MINIGAMES, K_SOUNDTRACK, MENU_SETTLE, ROM, ROOT, TM_BONUS, TM_TOP, check_golden,
                      hold_stage_anim, menu_items, menu_tap, menu_to, title_pick)
from gbtools import Rom
from pyboy import PyBoy
from test_bonus import lines
from test_flow import GS_GOAL, LEVEL_CLEAR, TITLE, run_until, state, tilemap_row
from ol_helpers import BLANK, BOX, PUNCT, SKIN_MEDAL, attr, band_rows_ok, hint, selection
from ol_helpers import text as row_text
from test_mg import GLYPH_CH, GS_MGLIST, GS_MINI, MG_PRACTICE, MG_RESULT, MG_STORY, MG_STUB, frames, mg_enter, score, text
from test_scores import booted, table, v7_image
from test_sound import save_ram
from test_story import to_goal, to_shift, win

pytestmark = pytest.mark.timeout(300)

MG_QUICKDRAW, MG_ORDERUP, MG_PLANNED = 0, 3, 10
MG_SHAKEUP, MG_FILLLINE, MG_TIPS = 12, 13, 14
MEDAL_NONE, MEDAL_BRONZE, MEDAL_SILVER, MEDAL_GOLD = range(4)
PR_AT, PR_MEDAL = 0x40, 6
PR_LEN = PR_MEDAL + MG_PLANNED
RELEASE = ROOT / "build" / "release.gb"
# the story font's '?' (build/story.h: ST_GLYPH_QUEST = STORY_FONT_BASE + 3, STORY_FONT_BASE = BAR_TILE_COUNT)
QUEST = int(re.search(r"#define BAR_TILE_COUNT (\d+)", (ROOT / "build" / "art.h").read_text()).group(1)) + 3
BTN_A = QUEST + 4                              # ST_FRAME_TL (+7), _T, _TR: the keys line's A, B and D-pad buttons, loaded over the font's frame tiles
BTN_B, BTN_R = BTN_A + 1, BTN_A + 2
assert "#define ST_FRAME_TL (STORY_FONT_BASE + 7)" in (ROOT / "build" / "story.h").read_text()
assert "#define ST_GLYPH_QUEST (STORY_FONT_BASE + 3)" in (ROOT / "build" / "story.h").read_text()


assert "#define SKIN_TILE_MEDAL   0 " in (ROOT / "src" / "game.h").read_text()


def pr_block(unlocked=0, best=(), magic=b"MGP1"):
    """Practice's SRAM block: magic, the unlock bits (LE), a medal per planned game, checksum, complement."""
    r = bytearray(PR_LEN + 2)
    r[0:4] = magic
    r[4:6] = unlocked.to_bytes(2, "little")
    for g, m in enumerate(best):
        r[PR_MEDAL + g] = m
    c = (0x5A + sum(r[:PR_LEN])) & 255
    r[PR_LEN], r[PR_LEN + 1] = c, c ^ 0xFF
    return bytes(r)


def with_block(ram, block):
    r = bytearray(ram)
    r[PR_AT:PR_AT + len(block)] = block
    return bytes(r)


PR2_LEN = PR_LEN + 28        # the block as the game writes it, "MGP2": the boss rush's 28 bytes follow (tests/test_rush.py)


def parse_block(ram):
    b = ram[PR_AT:PR_AT + PR2_LEN + 2]
    assert b[:4] == b"MGP2", b[:4]
    c = (0x5A + sum(b[:PR2_LEN])) & 255
    assert b[PR2_LEN] == c and b[PR2_LEN + 1] == c ^ 0xFF, "the block's checksum"
    return int.from_bytes(b[4:6], "little"), list(b[PR_MEDAL:PR_LEN])


def best(rom):
    return list(rom.read("mg_best", MG_PLANNED))


def line(gb, row):
    """A row of the list screen as text (ol_helpers.text: '?' and '-' from the story font, '@' and '$' the A and B buttons)."""
    return row_text(gb, row)


def to_list(rom):
    """From the title's top level: BONUS > MINI GAMES."""
    title_pick(rom, K_BONUS, K_MINIGAMES)
    run_until(rom, lambda: state(rom) == GS_MGLIST and rom.pb.memory[0xFF40] & 0x80, 30)
    rom.run(3)
    return rom


def tap(rom, b):
    rom.press(b, 2)
    rom.run(3)


def release_rom(model, ram=None):
    rom = Rom(RELEASE, model)
    rom.pb.stop(save=False)
    rom.pb = PyBoy(str(RELEASE), window="null", sound_emulated=False, cgb=(model == "cgb"), log_level="ERROR",
                   ram_file=BytesIO(ram) if ram is not None else None)
    rom.pb.set_emulation_speed(0)
    rom.model_name = model
    rom.run(120)
    return rom


@pytest.fixture(scope="module")
def release_built():
    subprocess.run(["make", "release"], cwd=ROOT, check=True, capture_output=True)
    return RELEASE


# ---- the menu --------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_bonus_offers_soundtrack_and_mini_games(model):
    with booted(model) as rom:
        title_pick(rom, K_BONUS)
        rom.run(MENU_SETTLE)
        assert menu_items(rom) == [K_CREDITS, K_SOUNDTRACK, K_MINIGAMES, K_BOSSRUSH]
        menu_to(rom, K_MINIGAMES)
        menu_tap(rom, "a")
        run_until(rom, lambda: state(rom) == GS_MGLIST, 30)


# (chapter order, docs/story.md: saloon, stadium, lodge, bistro, igloo, robot factory, Chrome Cow, teahouse, zoo, space lounge;
# the list's name column, and the venue the details line shows)
# (chapter order, docs/story.md: saloon, stadium, lodge, bistro, igloo, robot factory, Chrome Cow, teahouse, zoo, space lounge; then the bonus rounds)
NAMES = ["QUICK DRAW", "SHIRT CANNON", "LOG ROLL", "ORDER UP", "MARSHMALLOWS", "BATTERY SORT", "MILK RUN", "TAIKO POUR", "MONKEY BUSINESS", "ASTEROIDS",
         "CAN SHAKE-UP", "PERFECT POUR", "TIP SHOWER", "GREEN LIGHT"]
GROUP = 10                                        # the first bonus round's place (src/mg_list.c ML_GROUP)
ART_ROWS = range(6, 14)                           # the illustration frame: rows 6-13, columns 1-10 (80 x 64 px)


def counter(gb):
    return row_text(gb, 7, 12, 8).strip()


def medal_icon(gb):
    return tilemap_row(gb, 9, 12, 1)[0]


def medal_word(gb):
    return row_text(gb, 11, 12, 8).strip()


def to_game(gb, k):
    """Select the k-th game with RIGHT taps."""
    while gb.mem("ml_sel") != k:
        tap(gb, "right")
    gb.run(6)


def frame_is_an_empty_frame(gb):
    """Rows 6-13, columns 1-10: the border (BOX tiles) around blank interior; no letter or other tile anywhere in it."""
    rows = [tilemap_row(gb, r, 1, 10) for r in ART_ROWS]
    assert rows[0] == [BOX] + [BOX + 1] * 8 + [BOX + 2]
    assert rows[-1] == [BOX + 5] + [BOX + 6] * 8 + [BOX + 7]
    for r in rows[1:-1]:
        assert r == [BOX + 3] + [BLANK] * 8 + [BOX + 4], r
    assert not any(t in GLYPH_CH or t in PUNCT for r in rows for t in r), "no text in the frame"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_debug_list_has_every_built_game_unlocked_in_the_one_line_style(model):
    """The DEBUG_MENU build (`make`): the ten games in chapter order, the three bonus rounds and the stub GREEN LIGHT (14), all playable on a fresh
    cartridge. The screen: the header "MINI GAMES NORMAL", the selection line "< NAME >" (rows 2-4), the empty 80 x 64 px illustration frame on rows 6-13, the
    counter "n / 14" right of it, NO MEDAL, the hint "(A) PLAY (B) BACK" on row 16; no instructions text anywhere, no sprites."""
    with to_list(booted(model)) as gb:
        hold_stage_anim(gb)
        gb.run(10)
        assert gb.mem("ml_n") == 14 and gb.mem("ml_sel") == 0 and gb.mem16("mg_unlocked") == 0
        assert line(gb, 0).strip() == "MINI GAMES  NORMAL"
        assert row_text(gb, 0, 1, 10) == "MINI GAMES" and row_text(gb, 0, 13, 6) == "NORMAL"
        assert selection(gb) == NAMES[0] and band_rows_ok(gb)
        assert counter(gb) == "1 / 14" and medal_icon(gb) == BLANK and medal_word(gb) == "NO MEDAL"
        assert hint(gb) == "@ PLAY   $ BACK"
        frame_is_an_empty_frame(gb)
        for r in (1, 5, 14):
            assert set(tilemap_row(gb, r, 1, 10)) <= {BLANK, 0}, "blank rows round the frame"
        assert not gb.visible_sprites()
        check_golden(gb, "mg_list")
        for k in range(1, 14):
            tap(gb, "right")
            gb.run(6)
            assert gb.mem("ml_sel") == k and selection(gb) == NAMES[k] and counter(gb) == f"{k + 1} / 14", k
        tap(gb, "right")
        gb.run(6)
        assert gb.mem("ml_sel") == 0 and selection(gb) == NAMES[0], "wraps"
        tap(gb, "left")
        gb.run(6)
        assert gb.mem("ml_sel") == 13 and selection(gb) == "GREEN LIGHT"
        check_golden(gb, "ol_practice_last")
        tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_MINI and gb.pb.memory[0xFF40] & 0x80, 30)
        assert gb.mem("mg_id") == MG_STUB and gb.mem("mg_mode") == MG_PRACTICE


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_up_and_down_jump_between_the_venue_games_and_the_bonus_rounds(model):
    with to_list(booted(model)) as gb:
        tap(gb, "down")
        gb.run(6)
        assert gb.mem("ml_sel") == GROUP and selection(gb) == "CAN SHAKE-UP", "DOWN: the first bonus round"
        tap(gb, "down")
        gb.run(6)
        assert gb.mem("ml_sel") == 0, "DOWN from the bonus rounds: the first venue game"
        to_game(gb, 6)
        tap(gb, "up")
        assert gb.mem("ml_sel") == 0, "UP: this group's first"
        tap(gb, "up")
        assert gb.mem("ml_sel") == GROUP, "UP from the first: the group before (wraps to the bonus rounds)"
        to_game(gb, 12)
        tap(gb, "up")
        assert gb.mem("ml_sel") == GROUP
        tap(gb, "up")
        assert gb.mem("ml_sel") == 0, "UP from the first bonus round: the venue games' first"
        for _ in range(3):
            tap(gb, "right")
        tap(gb, "down")
        assert gb.mem("ml_sel") == GROUP, "DOWN from anywhere in the venue games"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_select_cycles_the_mode_and_the_medal_shown_is_that_modes(model):
    """SELECT: EASY, NORMAL, HARD, round (it was LEFT / RIGHT); the header names it; the medal and its word are the selected game's best in that mode;
    the mode applies to every game and to the game played, and outlasts the game and the title."""
    ram = with_block(v7_image(), pr_block(0, [MEDAL_GOLD | MEDAL_SILVER << 2 | MEDAL_BRONZE << 4]))   # QUICK DRAW: NORMAL gold, HARD silver, EASY bronze
    with to_list(booted(model, ram)) as gb:
        assert row_text(gb, 0, 13, 6) == "NORMAL" and medal_word(gb) == "GOLD" and medal_icon(gb) == SKIN_MEDAL + 2
        modes = []
        for want, word, icon in (("HARD", "SILVER", SKIN_MEDAL + 1), ("EASY", "BRONZE", SKIN_MEDAL), ("NORMAL", "GOLD", SKIN_MEDAL + 2)):
            tap(gb, "select")
            gb.run(6)
            modes.append(row_text(gb, 0, 13, 6))
            assert modes[-1] == want and medal_word(gb) == word and medal_icon(gb) == icon, (want, medal_word(gb))
        assert modes == ["HARD", "EASY", "NORMAL"], "the cycle goes NORMAL, HARD, EASY here (src/mg_list.c diff_ui: EASY, NORMAL, HARD in the order shown by the cycle)"
        tap(gb, "right")
        gb.run(6)
        assert row_text(gb, 0, 13, 6) == "NORMAL", "moving keeps the mode"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_quick_draw_from_the_list_retry_and_back(model):
    """A on QUICK DRAW: it plays in practice (score from 0); its result's A retries (from 0 again), B comes back to the
    list (the cursor where it was); the list's B goes back to the title's BONUS submenu, the cursor on MINI GAMES;
    B there to the top level."""
    with to_list(booted(model)) as gb:
        tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_MINI and gb.pb.memory[0xFF40] & 0x80, 30)
        assert gb.mem("mg_id") == MG_QUICKDRAW and gb.mem("mg_mode") == MG_PRACTICE and score(gb) == 0
        assert text(gb, 2) == "QUICK DRAW" and gb.mem("story_on") == 0
        gb.write("mg_phase", MG_RESULT)
        run_until(gb, lambda: gb.mem("overlay_on") == 1, 10)
        frames(gb, 3)
        assert text(gb, 4, True, x0=4) == "A RETRY B MENU"
        gb.press("a", 2)
        run_until(gb, lambda: gb.mem("mg_phase") == 0 and gb.pb.memory[0xFF40] & 0x80, 30)
        assert state(gb) == GS_MINI and gb.mem("mg_id") == MG_QUICKDRAW and score(gb) == 0, "RETRY"
        gb.write("mg_phase", MG_RESULT)
        run_until(gb, lambda: gb.mem("overlay_on") == 1, 10)
        frames(gb, 3)
        gb.press("b", 2)
        run_until(gb, lambda: state(gb) == GS_MGLIST and gb.pb.memory[0xFF40] & 0x80, 30)
        gb.run(3)
        assert gb.mem("ml_sel") == 0 and selection(gb) == "QUICK DRAW" and gb.mem("overlay_on") == 0
        tap(gb, "b")
        run_until(gb, lambda: state(gb) == TITLE and gb.pb.memory[0xFF40] & 0x80, 30)
        gb.run(MENU_SETTLE)
        assert gb.mem("title_menu") == TM_BONUS and menu_items(gb) == [K_CREDITS, K_SOUNDTRACK, K_MINIGAMES, K_BOSSRUSH]
        assert gb.mem("title_sel") == 2, "the cursor on MINI GAMES"
        tap(gb, "b")
        gb.run(MENU_SETTLE)
        assert gb.mem("title_menu") == TM_TOP and gb.mem("title_sel") == 1, "then the top level, on BONUS"


# ---- the release build: the unlock rule, no stub ------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_release_list_is_locked_until_reached(model, release_built):
    """`make release`: the ten games and the three bonus rounds (the stub is not listed). On a fresh cartridge each is "? ? ?" with LOCKED where the
    medal goes and no A on the hint row; A does nothing. With Practice's block saying Quick Draw was reached (silver its best)
    it shows by name with SILVER and plays (the others still locked); with Order Up!'s bit it shows and plays."""
    with release_rom(model) as gb:
        to_list(gb)
        gb.run(10)
        assert gb.mem("ml_n") == 13
        assert selection(gb) == "? ? ?" and counter(gb) == "1 / 13"
        assert medal_word(gb) == "LOCKED" and medal_icon(gb) == BLANK and row_text(gb, 14) == ""
        assert hint(gb) == "$ BACK"
        frame_is_an_empty_frame(gb)
        check_golden(gb, "mg_list_locked")
        tap(gb, "a")
        gb.run(5)
        assert state(gb) == GS_MGLIST, "a locked game does not play"
        tap(gb, "down")
        gb.run(6)
        assert selection(gb) == "? ? ?" and medal_word(gb) == "LOCKED" and hint(gb) == "$ BACK"
        check_golden(gb, "ol_practice_locked_bonus")
    ram = with_block(v7_image(), pr_block(1, [MEDAL_SILVER]))
    with release_rom(model, ram) as gb:
        to_list(gb)
        gb.run(10)
        assert selection(gb) == "QUICK DRAW" and medal_word(gb) == "SILVER" and medal_icon(gb) == SKIN_MEDAL + 1
        assert hint(gb) == "@ PLAY   $ BACK"
        tap(gb, "right")
        gb.run(6)
        assert selection(gb) == "? ? ?" and medal_word(gb) == "LOCKED" and hint(gb) == "$ BACK"
        tap(gb, "left")
        gb.run(6)
        assert hint(gb) == "@ PLAY   $ BACK" and medal_word(gb) == "SILVER"
        tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_MINI, 30)
        assert gb.mem("mg_id") == MG_QUICKDRAW and gb.mem("mg_mode") == MG_PRACTICE
    ram = with_block(v7_image(), pr_block(1 << MG_ORDERUP, [0, 0, 0, MEDAL_BRONZE]))
    with release_rom(model, ram) as gb:
        to_list(gb)
        assert selection(gb) == "? ? ?"
        for _ in range(3):
            tap(gb, "right")
        gb.run(6)
        assert selection(gb) == "ORDER UP" and medal_word(gb) == "BRONZE" and counter(gb) == "4 / 13"
        tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_MINI, 30)
        assert gb.mem("mg_id") == MG_ORDERUP and gb.mem("mg_mode") == MG_PRACTICE


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_list_shows_the_saves_medals_and_nothing_invented(model):
    """Real data only: the medal icon and word of each game are its saved best in the mode shown, NO MEDAL (no icon) where there is none."""
    ram = with_block(v7_image(), pr_block(0, [2, 1, 3]))
    with to_list(booted(model, ram)) as gb:
        shown = []
        for k in range(4):
            to_game(gb, k)
            shown.append((medal_icon(gb), medal_word(gb)))
        assert shown == [(SKIN_MEDAL + 1, "SILVER"), (SKIN_MEDAL, "BRONZE"), (SKIN_MEDAL + 2, "GOLD"), (BLANK, "NO MEDAL")]
        for k in range(4, 14):
            to_game(gb, k)
            assert (medal_icon(gb), medal_word(gb)) == (BLANK, "NO MEDAL"), k


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_medal_icon_has_its_own_palette_and_the_frame_the_walls(model):
    ram = with_block(v7_image(), pr_block(0, [3]))
    with to_list(booted(model, ram)) as gb:
        gb.run(10)
        assert medal_icon(gb) == SKIN_MEDAL + 2
        if model == "cgb":
            assert attr(gb, 9, 12) == 3, "the medal palette"
            assert {attr(gb, r, c) for r in ART_ROWS for c in range(1, 11)} == {2}, "the frame is on the wall's palette"
            assert [attr(gb, r, 3) for r in (0, 1, 5, 14, 15, 16, 17)] == [5, 7, 2, 2, 6, 6, 6]
            assert [attr(gb, 16, c) for c in range(20)] == [6] * 20


# ---- the art slot -----------------------------------------------------------------------------------------------------------
def test_the_illustration_slot_is_80_by_64_pixels_and_documented():
    src = (ROOT / "src" / "mg_list.c").read_text()
    assert "assets/art/practice/<game>.png" in src and "80 x 64" in src
    assert "#define ML_ART_W        10" in src and "#define ML_ART_H        8" in src
    assert "ART HERE" not in src


# ---- unlocks and medals in SRAM -------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_story_reaching_quick_draw_unlocks_it_and_the_medal_is_kept(model):
    """The saloon's Happy hour won: Quick Draw starts (MG_STORY) and is unlocked at once, saved in its block; a gold
    there is its best medal; both survive a reset (the story's own block as well)."""
    with to_shift(model, 0, 1) as gb:
        assert gb.mem16("mg_unlocked") == 0
        win(gb, 0, 1)
        run_until(gb, lambda: state(gb) == GS_MINI, 800)
        run_until(gb, lambda: gb.pb.memory[0xFF40] & 0x80, 10)
        assert gb.mem("mg_mode") == MG_STORY and gb.mem("mg_id") == MG_QUICKDRAW
        assert gb.mem16("mg_unlocked") == 1 and best(gb)[0] == MEDAL_NONE
        gb.write(gb.addr("story_scratch") + 2, 3)         # (Quick Draw's rounds: 3-0)
        gb.write("mg_phase", MG_RESULT)
        run_until(gb, lambda: gb.mem("overlay_on") == 1, 10)
        frames(gb, 2)
        assert gb.mem("mg_medal") == MEDAL_GOLD and best(gb)[0] == MEDAL_GOLD
        ram = save_ram(gb)
    assert parse_block(ram) == (1, [MEDAL_GOLD] + [0] * (MG_PLANNED - 1))
    with booted(model, ram) as rom:
        assert rom.mem16("mg_unlocked") == 1 and best(rom) == [MEDAL_GOLD] + [0] * 9
        assert rom.mem("story_progress") == 0 and rom.mem("story_reached") >= 2, "the main block kept"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_worse_medal_never_lowers_the_best(model):
    ram = with_block(v7_image(), pr_block(1, [MEDAL_SILVER]))
    with booted(model, ram) as rom:
        mg_enter(rom, MG_QUICKDRAW, MG_PRACTICE)
        rom.write(rom.addr("story_scratch") + 2, 3); rom.write(rom.addr("story_scratch") + 3, 2)   # 3-2 won: bronze
        rom.write("mg_phase", MG_RESULT)
        run_until(rom, lambda: rom.mem("overlay_on") == 1, 10)
        frames(rom, 2)
        assert rom.mem("mg_medal") == MEDAL_BRONZE and best(rom)[0] == MEDAL_SILVER
        rom.press("a", 2)                                # retry: gold this time
        run_until(rom, lambda: rom.mem("mg_phase") == 0 and rom.pb.memory[0xFF40] & 0x80, 30)
        rom.write(rom.addr("story_scratch") + 2, 3)
        rom.write("mg_phase", MG_RESULT)
        run_until(rom, lambda: rom.mem("overlay_on") == 1, 10)
        frames(rom, 2)
        assert best(rom)[0] == MEDAL_GOLD
        assert parse_block(save_ram(rom)) == (1, [MEDAL_GOLD] + [0] * 9)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_arcade_reaching_quick_draw_unlocks_it_too(model):
    """ARCADE saves nothing of its own (save_lock 1), but the owner's rule is "reached in STORY or ARCADE": the block is
    written. A debug-select run (save_lock SAVE_LOCK_DEBUG) records nothing."""
    from test_arcade import start_arcade
    with start_arcade(model) as gb:
        assert gb.mem("save_lock") == 1
        for k in range(2):
            to_goal(gb)
            win(gb, 0, k)
            run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 20)
            run_until(gb, lambda: state(gb) in (GS_GOAL, GS_MINI), 400)
        assert state(gb) == GS_MINI and gb.mem("mg_id") == MG_QUICKDRAW and gb.mem("mg_mode") == MG_STORY
        assert gb.mem16("mg_unlocked") == 1
        ram = save_ram(gb)
    assert parse_block(ram)[0] == 1
    with booted(model) as rom:
        rom.write("save_lock", 2)
        mg_enter(rom, MG_QUICKDRAW, MG_STORY)
        assert rom.mem16("mg_unlocked") == 0, "a debug-select run: nothing recorded"
        assert save_ram(rom)[PR_AT:PR_AT + 4] != b"MGP1"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_stub_and_practice_alone_unlock_nothing(model):
    """Practice never unlocks (only STORY / ARCADE reach a game); the stub (MG_STUB) is never saved."""
    with booted(model) as rom:
        mg_enter(rom, MG_QUICKDRAW, MG_PRACTICE)
        assert rom.mem16("mg_unlocked") == 0
        mg_enter(rom, MG_STUB, MG_STORY)
        assert rom.mem16("mg_unlocked") == 0
        assert save_ram(rom)[PR_AT:PR_AT + 4] != b"MGP1"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_bad_block_unlocks_nothing_and_leaves_the_others_alone(model):
    good = v7_image([("ABC", 500)], story=3, step=1, story_tbl=[("STO", 900)])
    ok = pr_block(1, [MEDAL_GOLD, 0, 0, 0, 0, 0, 0, 0, 0, 0])
    with booted(model, with_block(good, ok)) as rom:
        assert rom.mem16("mg_unlocked") == 1 and best(rom)[0] == MEDAL_GOLD
    bad_sum = bytearray(ok)
    bad_sum[PR_LEN] ^= 1
    cases = {
        "checksum": bytes(bad_sum),
        "magic": pr_block(1, [MEDAL_GOLD], magic=b"MGP2"),
        "a medal byte past the three fields": pr_block(1, [64]),
        "a bit past the planned games": pr_block(1 | 1 << MG_PLANNED, [MEDAL_GOLD]),
        "blank": bytes(PR_LEN + 2),
    }
    for name, block in cases.items():
        with booted(model, with_block(good, block)) as rom:
            assert rom.mem16("mg_unlocked") == 0 and best(rom) == [0] * MG_PLANNED, name
            assert rom.mem("story_progress") == 3 and rom.mem("story_reached") == 1, name
            assert table(rom)[0] == ("ABC", 500) and table(rom, 1)[0] == ("STO", 900), name


