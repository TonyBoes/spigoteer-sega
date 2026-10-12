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
from conftest import (K_BONUS, K_BOSSRUSH, K_MINIGAMES, K_SOUNDTRACK, MENU_SETTLE, ROOT, TM_BONUS, TM_TOP, check_golden,
                      hold_stage_anim, menu_items, menu_tap, menu_to, title_pick)
from gbtools import Rom
from pyboy import PyBoy
from test_flow import GS_GOAL, LEVEL_CLEAR, TITLE, run_until, state, tilemap_row
from test_mg import GLYPH_CH, GS_MGLIST, GS_MINI, MG_PRACTICE, MG_RESULT, MG_STORY, MG_STUB, frames, mg_enter, score, text
from test_scores import booted, table, v7_image
from test_sound import save_ram
from test_story import to_goal, to_shift, win

pytestmark = pytest.mark.timeout(300)

MG_QUICKDRAW, MG_ORDERUP, MG_PLANNED = 0, 3, 10
MEDAL_NONE, MEDAL_BRONZE, MEDAL_SILVER, MEDAL_GOLD = range(4)
PR_AT, PR_MEDAL = 0x40, 6
PR_LEN = PR_MEDAL + MG_PLANNED
RELEASE = ROOT / "build" / "release.gb"
# the story font's '?' (build/story.h: ST_GLYPH_QUEST = STORY_FONT_BASE + 3, STORY_FONT_BASE = BAR_TILE_COUNT)
QUEST = int(re.search(r"#define BAR_TILE_COUNT (\d+)", (ROOT / "build" / "art.h").read_text()).group(1)) + 3
assert "#define ST_GLYPH_QUEST (STORY_FONT_BASE + 3)" in (ROOT / "build" / "story.h").read_text()


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
    """A row of the list screen as text ('?' for the story font's question mark)."""
    out = ""
    for t in tilemap_row(gb, row, 0, 20):
        out += GLYPH_CH.get(t, "?" if t == QUEST else " ")
    return out.rstrip()


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
        assert menu_items(rom) == [K_SOUNDTRACK, K_MINIGAMES, K_BOSSRUSH]
        menu_to(rom, K_MINIGAMES)
        menu_tap(rom, "a")
        run_until(rom, lambda: state(rom) == GS_MGLIST, 30)


# (chapter order, docs/story.md: saloon, stadium, lodge, bistro, igloo, robot factory, Chrome Cow, teahouse, zoo, space lounge;
# the list's name column, and the venue the details line shows)
LIST = [("QUICK DRAW", "THE SALOON"), ("SHIRT CANNON", "THE STADIUM"), ("LOG ROLL", "THE LUMBER LODGE"), ("ORDER UP", "THE BISTRO"),
        ("MARSHMALLOWS", "THE IGLOO"), ("BATTERY SORT", "THE ROBOT FACTORY"), ("MILK RUN", "THE CHROME COW"),
        ("TAIKO POUR", "THE TEAHOUSE"), ("MONKEY BIZ", "THE JUNGLE ZOO"), ("ASTEROIDS", "THE SPACE LOUNGE")]


def no_row_touches_the_separator(gb, n):
    """n list lines on rows 2..n+1, then a blank row, then the separator (the panel's top: one tile repeated, not text), details below."""
    blank, sep = tilemap_row(gb, 2 + n, 0, 20), tilemap_row(gb, 3 + n, 0, 20)
    assert len(set(blank)) == 1 and len(set(sep)) == 1 and blank[0] != sep[0], "a blank row, then the separator"
    assert all(tilemap_row(gb, r, 0, 20) != sep for r in range(2, 2 + n)), "no list line is the separator"
    assert all(len(set(tilemap_row(gb, r, 0, 20))) > 1 for r in range(2, 2 + n)), "every list line has its text"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_debug_list_has_every_built_game_unlocked(model):
    """The DEBUG_MENU build (`make`): all ten games in chapter order and the stub GREEN LIGHT, all playable on a fresh cartridge; the
    selected game's venue and best medal below (rows 15-16: eleven lines leave no room for the keys line); Up / Down move and wrap;
    <= 10 sprites a line (the mug cursor); no line touches the separator (a blank row 13, the separator 14)."""
    names = [n for n, _ in LIST] + ["GREEN LIGHT"]
    with to_list(booted(model)) as gb:
        hold_stage_anim(gb)
        assert gb.mem("ml_n") == 11 and gb.mem("ml_sel") == 0 and gb.mem16("mg_unlocked") == 0
        assert line(gb, 0).strip() == "MINI GAMES  NORMAL"
        assert [line(gb, r).strip() for r in range(2, 13)] == names
        no_row_touches_the_separator(gb, 11)
        assert [line(gb, r).strip() for r in range(15, 17)] == ["THE SALOON", "NO MEDAL YET"]
        o = gb.read(0xFE00, 4)
        assert o[0] == 2 * 8 - 7 + 16 and o[1] == 8, "the mug cursor on line 0"
        check_golden(gb, "mg_list")
        for k in range(1, 10):
            tap(gb, "down")
            assert gb.mem("ml_sel") == k and [line(gb, r).strip() for r in (2 + k, 15)] == [LIST[k][0], LIST[k][1]]
        tap(gb, "down")
        assert gb.mem("ml_sel") == 10 and line(gb, 12).strip() == "GREEN LIGHT" and line(gb, 15).strip() == "THE TEST STUB"
        tap(gb, "down")
        assert gb.mem("ml_sel") == 0, "wraps"
        tap(gb, "up")
        assert gb.mem("ml_sel") == 10
        tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_MINI and gb.pb.memory[0xFF40] & 0x80, 30)
        assert gb.mem("mg_id") == MG_STUB and gb.mem("mg_mode") == MG_PRACTICE and text(gb, 2) == "GREEN LIGHT"


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
        assert gb.mem("ml_sel") == 0 and line(gb, 2).strip() == "QUICK DRAW" and gb.mem("overlay_on") == 0
        tap(gb, "b")
        run_until(gb, lambda: state(gb) == TITLE and gb.pb.memory[0xFF40] & 0x80, 30)
        gb.run(MENU_SETTLE)
        assert gb.mem("title_menu") == TM_BONUS and menu_items(gb) == [K_SOUNDTRACK, K_MINIGAMES, K_BOSSRUSH]
        assert gb.mem("title_sel") == 1, "the cursor on MINI GAMES"
        tap(gb, "b")
        gb.run(MENU_SETTLE)
        assert gb.mem("title_menu") == TM_TOP and gb.mem("title_sel") == 1, "then the top level, on BONUS"


# ---- the release build: the unlock rule, no stub ------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_release_list_is_locked_until_reached(model, release_built):
    """`make release`: all ten games in chapter order (the stub is not listed); on a fresh cartridge each is
    "? ? ?" with LOCKED details and A does nothing; with Practice's block saying Quick Draw was reached (silver its best)
    it lists by name with SILVER and plays (the others still locked); with Order Up!'s bit it lists and plays."""
    with release_rom(model) as gb:
        to_list(gb)
        assert gb.mem("ml_n") == 10
        assert [line(gb, r).strip() for r in range(2, 13)] == ["? ? ?"] * 10 + [""]
        no_row_touches_the_separator(gb, 10)
        assert [line(gb, r).strip() for r in range(14, 17)] == ["LOCKED", "REACH IT IN STORY", "OR ARCADE"]
        check_golden(gb, "mg_list_locked")
        tap(gb, "a")
        gb.run(5)
        assert state(gb) == GS_MGLIST, "a locked game does not play"
    ram = with_block(v7_image(), pr_block(1, [MEDAL_SILVER]))
    with release_rom(model, ram) as gb:
        to_list(gb)
        assert line(gb, 2) == " QUICK DRAW   SILVER" and line(gb, 3).strip() == "? ? ?"
        assert line(gb, 15).strip() == "BEST SILVER"
        tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_MINI, 30)
        assert gb.mem("mg_id") == MG_QUICKDRAW and gb.mem("mg_mode") == MG_PRACTICE
    ram = with_block(v7_image(), pr_block(1 << MG_ORDERUP, [0, 0, 0, MEDAL_BRONZE]))
    with release_rom(model, ram) as gb:
        to_list(gb)
        assert line(gb, 2).strip() == "? ? ?" and line(gb, 5) == " ORDER UP     BRONZE"
        for _ in range(3):
            tap(gb, "down")
        assert [line(gb, r).strip() for r in range(14, 17)] == ["THE BISTRO", "BEST BRONZE", "NORMAL ONLY  B BACK"]
        tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_MINI, 30)
        assert gb.mem("mg_id") == MG_ORDERUP and gb.mem("mg_mode") == MG_PRACTICE


def test_the_release_build_names_no_stub(release_built):
    """The list is the build's: the release one names all ten games (the stub is the only entry left out) (the stub's name is not even in the
    ROM's list)."""
    noi = (ROOT / "build" / "release.noi").read_text()
    assert "_ml_n" in noi and "_mg_list_enter" in noi
    rom = RELEASE.read_bytes()
    assert b"QUICK DRAW" in rom and b"ORDER UP" in rom
    dbg = (ROOT / "build" / "game.gb").read_bytes()
    assert dbg.count(b"GREEN LIGHT") > rom.count(b"GREEN LIGHT"), "the list's stub entry: debug only"


# ---- unlocks and medals in SRAM -------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_story_reaching_quick_draw_unlocks_it_and_the_medal_is_kept(model):
    """The saloon's Happy hour won: Quick Draw starts (MG_STORY) and is unlocked at once, saved in its block; a gold
    there is its best medal; both survive a reset (the story's own block as well)."""
    with to_shift(model, 0, 1) as gb:
        assert gb.mem16("mg_unlocked") == 0
        win(gb, 0, 1)
        run_until(gb, lambda: state(gb) == GS_MINI, 300)
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
        rom.write(rom.addr("story_scratch") + 2, 1)       # one round won: bronze
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
        "a medal past the two fields": pr_block(1, [16]),
        "a bit past the planned games": pr_block(1 | 1 << MG_PLANNED, [MEDAL_GOLD]),
        "blank": bytes(PR_LEN + 2),
    }
    for name, block in cases.items():
        with booted(model, with_block(good, block)) as rom:
            assert rom.mem16("mg_unlocked") == 0 and best(rom) == [0] * MG_PLANNED, name
            assert rom.mem("story_progress") == 3 and rom.mem("story_reached") == 1, name
            assert table(rom)[0] == ("ABC", 500) and table(rom, 1)[0] == ("STO", 900), name


# ---- the Practice HARD toggle (owner Q7) ------------------------------------------------------------------------------
def play_and_mode(gb):
    tap(gb, "a")
    run_until(gb, lambda: state(gb) == GS_MINI and gb.pb.memory[0xFF40] & 0x80, 30)
    return gb.mem("mg_mode")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_select_flips_normal_hard_on_milk_run_and_hard_reaches_mg_mode(model):
    """Milk Run (list line 6) reads MG_HARD: SELECT flips the header NORMAL / HARD (and LEFT / RIGHT too), the keys line says
    SEL, A then plays with MG_PRACTICE | MG_HARD; the layout holds (a blank row, the separator, the header on row 0 only)."""
    with to_list(booted(model)) as gb:
        for _ in range(6):
            tap(gb, "down")
        assert gb.mem("ml_sel") == 6 and line(gb, 0).strip() == "MINI GAMES  NORMAL"
        tap(gb, "select")
        gb.run(4)
        assert line(gb, 0).strip() == "MINI GAMES  HARD"
        no_row_touches_the_separator(gb, 11)
        assert line(gb, 8).strip() == "MILK RUN" and line(gb, 15).strip() == "THE CHROME COW"
        check_golden(gb, "mg_list_hard")
        tap(gb, "select")
        gb.run(4)
        assert line(gb, 0).strip() == "MINI GAMES  NORMAL"
        tap(gb, "right")
        gb.run(4)
        assert line(gb, 0).strip() == "MINI GAMES  HARD"
        tap(gb, "left")
        gb.run(4)
        assert line(gb, 0).strip() == "MINI GAMES  NORMAL"
        assert play_and_mode(gb) == MG_PRACTICE
    with to_list(booted(model)) as gb:
        for _ in range(6):
            tap(gb, "down")
        tap(gb, "select")
        assert play_and_mode(gb) == MG_PRACTICE | 2 and gb.mem("mg_id") == 6


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_games_without_hard_stay_normal_and_the_toggle_is_inert(model):
    """Quick Draw reads no MG_HARD: SELECT does nothing on it (the header stays NORMAL) and it starts MG_PRACTICE alone, even
    when HARD was switched on at Milk Run first (the switch stays for Milk Run: back there the header says HARD again)."""
    with to_list(booted(model)) as gb:
        tap(gb, "select")
        gb.run(4)
        assert line(gb, 0).strip() == "MINI GAMES  NORMAL"
        for _ in range(6):
            tap(gb, "down")
        tap(gb, "select")
        for _ in range(6):
            tap(gb, "up")
        gb.run(4)
        assert gb.mem("ml_sel") == 0 and line(gb, 0).strip() == "MINI GAMES  NORMAL", "HARD is not in force on Quick Draw"
        tap(gb, "select")
        gb.run(4)
        assert line(gb, 0).strip() == "MINI GAMES  NORMAL", "still inert (it did not flip back either)"
        for _ in range(6):
            tap(gb, "down")
        gb.run(4)
        assert line(gb, 0).strip() == "MINI GAMES  HARD"
        for _ in range(6):
            tap(gb, "up")
        assert play_and_mode(gb) == MG_PRACTICE and gb.mem("mg_id") == MG_QUICKDRAW


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_hard_best_is_kept_apart_in_the_release_list(model, release_built):
    """Release build, Milk Run reached with a normal BRONZE and a HARD GOLD (bits 0-1 / 2-3 of its medal byte): the list's medal
    column and the BEST line follow the mode; the keys line says SEL on Milk Run and NORMAL ONLY on Order Up."""
    MR_G = 6
    ram = with_block(v7_image(), pr_block(1 << MR_G | 1 << MG_ORDERUP, [0, 0, 0, MEDAL_SILVER, 0, 0, MEDAL_BRONZE | MEDAL_GOLD << 2]))
    with release_rom(model, ram) as gb:
        to_list(gb)
        assert line(gb, 8) == " MILK RUN     BRONZE"
        for _ in range(MR_G):
            tap(gb, "down")
        assert [line(gb, r).strip() for r in (15, 16)] == ["BEST BRONZE", "A PLAY  B BACK  SEL"]
        tap(gb, "select")
        gb.run(4)
        assert line(gb, 0).strip() == "MINI GAMES  HARD" and line(gb, 8) == " MILK RUN     GOLD"
        assert line(gb, 15).strip() == "BEST GOLD"
        no_row_touches_the_separator(gb, 10)
        for _ in range(MR_G - MG_ORDERUP):
            tap(gb, "up")
        gb.run(4)
        assert line(gb, 5) == " ORDER UP     SILVER" and line(gb, 16).strip() == "NORMAL ONLY  B BACK"
        assert line(gb, 0).strip() == "MINI GAMES  NORMAL"
