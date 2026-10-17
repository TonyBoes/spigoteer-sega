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
from conftest import (K_BONUS, K_BOSSRUSH, K_CREDITS, K_MINIGAMES, K_SOUNDTRACK, MENU_SETTLE, ROOT, TM_BONUS, TM_TOP, check_golden,
                      hold_stage_anim, menu_items, menu_tap, menu_to, title_pick)
from gbtools import Rom
from pyboy import PyBoy
from test_bonus import lines
from test_flow import GS_GOAL, LEVEL_CLEAR, TITLE, run_until, state, tilemap_row
from test_mg import GLYPH_CH, GS_MGLIST, GS_MINI, MG_PRACTICE, MG_RESULT, MG_STORY, MG_STUB, frames, mg_enter, score, text
from test_scores import booted, table, v7_image
from test_sound import save_ram
from test_story import to_goal, to_shift, win

pytestmark = pytest.mark.timeout(300)

MG_QUICKDRAW, MG_ORDERUP, MG_PLANNED = 0, 3, 10
MG_SHAKEUP, MG_FILLLINE, MG_TIPS = 12, 13, 14
MEDAL_NONE, MEDAL_BRONZE, MEDAL_SILVER, MEDAL_GOLD = range(4)
KEYS = "@ GO $ BACK > MODE"                   # the list's last info line (src/mg_list.c): @ the A button, $ the B button, > D-pad right
PR_AT, PR_MEDAL = 0x40, 6
PR_LEN = PR_MEDAL + MG_PLANNED
RELEASE = ROOT / "build" / "release.gb"
# the story font's '?' (build/story.h: ST_GLYPH_QUEST = STORY_FONT_BASE + 3, STORY_FONT_BASE = BAR_TILE_COUNT)
QUEST = int(re.search(r"#define BAR_TILE_COUNT (\d+)", (ROOT / "build" / "art.h").read_text()).group(1)) + 3
BTN_A = QUEST + 4                              # ST_FRAME_TL (+7), _T, _TR: the keys line's A, B and D-pad buttons, loaded over the font's frame tiles
BTN_B, BTN_R = BTN_A + 1, BTN_A + 2
assert "#define ST_FRAME_TL (STORY_FONT_BASE + 7)" in (ROOT / "build" / "story.h").read_text()
assert "#define ST_GLYPH_QUEST (STORY_FONT_BASE + 3)" in (ROOT / "build" / "story.h").read_text()


SKIN_MEDAL = 1                                 # the wood-wall tiles (src/game.h SKIN_TILE_*): ids 1, 2, 3 are the BRONZE, SILVER and GOLD icons (0 the header edge)
MEDAL_TILES = {SKIN_MEDAL: "BRONZE", SKIN_MEDAL + 1: "SILVER", SKIN_MEDAL + 2: "GOLD"}
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
    """A row of the list screen as text ('?' for the story font's question mark)."""
    out = ""
    row_tiles = tilemap_row(gb, row, 0, 20)
    for t in row_tiles[:19]:
        out += GLYPH_CH.get(t, "@" if t == BTN_A else "$" if t == BTN_B else ">" if t == BTN_R else "?" if t == QUEST else "-" if t == QUEST + 2 else " ")   # (ST_GLYPH_HYPHEN is the story font's 6th)
    t = row_tiles[19]
    if t in MEDAL_TILES:                           # (owner 2026-10-17: the best medal is an icon at column 19; the tests read it as its word at column 14, as before)
        out = out.rstrip().ljust(14) + MEDAL_TILES[t]
    else:
        out += GLYPH_CH.get(t, "@" if t == BTN_A else "$" if t == BTN_B else ">" if t == BTN_R else "?" if t == QUEST else " ")
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
        assert menu_items(rom) == [K_CREDITS, K_SOUNDTRACK, K_MINIGAMES, K_BOSSRUSH]
        menu_to(rom, K_MINIGAMES)
        menu_tap(rom, "a")
        run_until(rom, lambda: state(rom) == GS_MGLIST, 30)


# (chapter order, docs/story.md: saloon, stadium, lodge, bistro, igloo, robot factory, Chrome Cow, teahouse, zoo, space lounge;
# the list's name column, and the venue the details line shows)
BONUS_LIST = [("CAN SHAKE-UP", "A BONUS ROUND"), ("PERFECT POUR", "A BONUS ROUND"), ("TIP SHOWER", "A BONUS ROUND")]
VIS = 6                                           # the list shows six games, one every other row (src/mg_list.c ML_VIS) and scrolls


def game_row(i):
    """The screen row of the window's line i (a blank row between the games)."""
    return 2 + 2 * i


def window(gb):
    """The names the window shows, line by line."""
    return [line(gb, game_row(i)).strip() for i in range(VIS)]
LIST = [("QUICK DRAW", "THE SALOON"), ("SHIRT CANNON", "THE STADIUM"), ("LOG ROLL", "THE LUMBER LODGE"), ("ORDER UP", "THE BISTRO"),
        ("MARSHMALLOWS", "THE IGLOO"), ("BATTERY SORT", "THE ROBOT FACTORY"), ("MILK RUN", "THE CHROME COW"),
        ("TAIKO POUR", "THE TEAHOUSE"), ("MONKEY BIZ", "THE JUNGLE ZOO"), ("ASTEROIDS", "THE SPACE LOUNGE")] + BONUS_LIST


def no_row_touches_the_separator(gb, n):
    """n games on rows 2, 4 .. (a blank row between them), then a blank row, then the separator (the panel's top: one tile repeated, not
    text), details below."""
    last = game_row(n - 1)
    blank, sep = tilemap_row(gb, last + 1, 0, 20), tilemap_row(gb, last + 2, 0, 20)
    assert set(blank) <= {54} and len(set(sep)) == 1 and blank[0] != sep[0], "a blank row, then the separator"
    assert all(tilemap_row(gb, game_row(i), 0, 20) != sep for i in range(n)), "no list line is the separator"
    assert all(len(set(tilemap_row(gb, game_row(i), 0, 20))) > 1 for i in range(n)), "every list line has its text"
    assert all(set(tilemap_row(gb, game_row(i) + 1, 0, 20)) <= {54} for i in range(n - 1)), "a blank row (the wall: blank tiles and board seams) between the games"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_debug_list_has_every_built_game_unlocked_and_scrolls(model):
    """The DEBUG_MENU build (`make`): the ten games in chapter order, the three bonus rounds and the stub GREEN LIGHT (14), all playable on a
    fresh cartridge. The window shows six games on rows 2, 4 .. 12 (a blank row between them: owner 2026-10-15), a blank row 13, the separator
    14; the selected game's best medal and the keys below (rows 15-16; no venue line any more). Down past the sixth game slides the window one
    line at a time (the cursor stays on the bottom line), wraps to the top; Up from the top wraps to the bottom window; the mug stands on the
    selected line; no line touches the separator on any step; <= 10 sprites a line."""
    names = [n for n, _ in LIST] + ["GREEN LIGHT"]
    with to_list(booted(model)) as gb:
        hold_stage_anim(gb)
        assert gb.mem("ml_n") == 14 and gb.mem("ml_sel") == 0 and gb.mem16("mg_unlocked") == 0
        assert line(gb, 0).strip() == "MINI GAMES  NORMAL"
        assert window(gb) == names[:VIS]
        no_row_touches_the_separator(gb, VIS)
        assert [line(gb, r).strip() for r in range(15, 17)] == ["NORMAL NO MEDAL YET", KEYS]
        assert not any("THE " in line(gb, r) for r in range(14, 18)), "no venue line"
        keys_row = tilemap_row(gb, 16, 0, 20)
        assert [keys_row[KEYS.index(c) + 1] for c in "@$>"] == [BTN_A + 0, BTN_B, BTN_R], "the A, B and D-pad button tiles at their columns"
        assert KEYS.index("@") + 1 == 1 and KEYS.index("$") + 1 == 6 and KEYS.index(">") + 1 == 13
        assert keys_row[0] == keys_row[19], "a column spare each side"
        o = gb.read(0xFE00, 4)
        assert o[0] == 2 * 8 - 7 + 16 and o[1] == 8, "the mug cursor on line 0"
        check_golden(gb, "mg_list")
        for k in range(1, 14):
            tap(gb, "down")
            gb.run(4)                                      # (a scroll redraws four lines a frame)
            top = max(0, k - VIS + 1)
            assert gb.mem("ml_sel") == k
            assert window(gb) == names[top:top + VIS], k
            assert line(gb, 16) == " " + KEYS, k
            assert gb.read(0xFE00, 1)[0] == game_row(k - top) * 8 - 7 + 16, "the mug on the selected line"
            no_row_touches_the_separator(gb, VIS)
            assert max(lines(gb)) <= 10
        gb.run(2)
        check_golden(gb, "mg_list_scrolled")
        assert line(gb, game_row(VIS - 1)).strip() == "GREEN LIGHT" and line(gb, 15).strip() == "NORMAL NO MEDAL YET"
        tap(gb, "down")
        gb.run(4)
        assert gb.mem("ml_sel") == 0, "wraps"
        assert window(gb) == names[:VIS] and gb.read(0xFE00, 1)[0] == 2 * 8 - 7 + 16
        tap(gb, "up")
        gb.run(4)
        n = len(names)
        assert gb.mem("ml_sel") == 13 and window(gb) == names[n - VIS:]
        for _ in range(4):                                 # Up slides the window back only when the cursor leaves its top line
            tap(gb, "up")
        gb.run(4)
        assert gb.mem("ml_sel") == 9 and window(gb) == names[n - VIS:], "still the lower window"
        assert gb.read(0xFE00, 1)[0] == game_row(9 - (n - VIS)) * 8 - 7 + 16
        for _ in range(7):
            tap(gb, "up")
        gb.run(4)
        assert gb.mem("ml_sel") == 2 and window(gb) == names[2:2 + VIS], "one line up: the window slides"
        for _ in range(8):
            tap(gb, "down")
        gb.run(4)
        assert gb.mem("ml_sel") == 10
        tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_MINI and gb.pb.memory[0xFF40] & 0x80, 30)
        assert gb.mem("mg_id") == MG_SHAKEUP and gb.mem("mg_mode") == MG_PRACTICE


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
        assert gb.mem("title_menu") == TM_BONUS and menu_items(gb) == [K_CREDITS, K_SOUNDTRACK, K_MINIGAMES, K_BOSSRUSH]
        assert gb.mem("title_sel") == 2, "the cursor on MINI GAMES"
        tap(gb, "b")
        gb.run(MENU_SETTLE)
        assert gb.mem("title_menu") == TM_TOP and gb.mem("title_sel") == 1, "then the top level, on BONUS"


# ---- the release build: the unlock rule, no stub ------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_release_list_is_locked_until_reached(model, release_built):
    """`make release`: the ten games in chapter order and the three bonus rounds (the stub is not listed; ten lines show); on a fresh cartridge each is
    "? ? ?" with LOCKED details and A does nothing; with Practice's block saying Quick Draw was reached (silver its best)
    it lists by name with SILVER and plays (the others still locked); with Order Up!'s bit it lists and plays."""
    with release_rom(model) as gb:
        to_list(gb)
        assert gb.mem("ml_n") == 13
        assert window(gb) == ["? ? ?"] * VIS
        no_row_touches_the_separator(gb, VIS)
        assert [line(gb, r).strip() for r in range(15, 17)] == ["REACH IT IN STORY", "OR ARCADE"]
        assert gb.read(0xFE00, 12)[8] == 112 or gb.read(0xFE00, 12)[8] == 113, "the down arrow: games are listed below"
        check_golden(gb, "mg_list_locked")
        tap(gb, "a")
        gb.run(5)
        assert state(gb) == GS_MGLIST, "a locked game does not play"
    ram = with_block(v7_image(), pr_block(1, [MEDAL_SILVER]))
    with release_rom(model, ram) as gb:
        to_list(gb)
        assert line(gb, 2) == " QUICK DRAW   SILVER" and line(gb, 4).strip() == "? ? ?"
        assert line(gb, 15).strip() == "NORMAL BEST SILVER"
        tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_MINI, 30)
        assert gb.mem("mg_id") == MG_QUICKDRAW and gb.mem("mg_mode") == MG_PRACTICE
    ram = with_block(v7_image(), pr_block(1 << MG_ORDERUP, [0, 0, 0, MEDAL_BRONZE]))
    with release_rom(model, ram) as gb:
        to_list(gb)
        assert line(gb, 2).strip() == "? ? ?" and line(gb, game_row(3)) == " ORDER UP     BRONZE"
        for _ in range(3):
            tap(gb, "down")
        assert [line(gb, r).strip() for r in range(15, 17)] == ["NORMAL BEST BRONZE", KEYS]
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
        "a medal byte past the three fields": pr_block(1, [64]),
        "a bit past the planned games": pr_block(1 | 1 << MG_PLANNED, [MEDAL_GOLD]),
        "blank": bytes(PR_LEN + 2),
    }
    for name, block in cases.items():
        with booted(model, with_block(good, block)) as rom:
            assert rom.mem16("mg_unlocked") == 0 and best(rom) == [0] * MG_PLANNED, name
            assert rom.mem("story_progress") == 3 and rom.mem("story_reached") == 1, name
            assert table(rom)[0] == ("ABC", 500) and table(rom, 1)[0] == ("STO", 900), name


# ---- scroll arrows (src/mg_list.c ML_ARROW_*; owner 2026-10-14) ------------------------------------------------------------------------
def arrow_ys(gb):
    """(up y, down y) of OAM entries 1 and 2 (0: hidden), and their tiles."""
    o = gb.read(0xFE00, 12)
    return (o[4], o[8]), (o[6], o[10])


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_scroll_arrows_show_only_where_games_are_hidden_and_bob(model):
    with to_list(booted(model)) as gb:
        hold_stage_anim(gb)
        (up, down), tiles = arrow_ys(gb)
        assert up == 0 and 112 <= down <= 113, "top of the list: only the down arrow"
        assert gb.read(0xFE00, 12)[5] == 160 and gb.read(0xFE00, 12)[9] == 160, "the right edge (column 19)"
        seen = set()
        for _ in range(40):                                # (two bobs of 16 frames and a bit)
            gb.run(1)
            (up, down), _ = arrow_ys(gb)
            assert up == 0
            seen.add(down)
        assert seen == {112, 113}, "the down arrow bobs one pixel"
        for _ in range(10):                                # the cursor to line 10: the window slides one line
            tap(gb, "down")
        gb.run(4)
        assert gb.mem("ml_sel") == 10
        (up, down), _ = arrow_ys(gb)
        assert 23 <= up <= 24 and 112 <= down <= 113, "the middle: both"
        seen = set()
        for _ in range(40):
            gb.run(1)
            seen.add(arrow_ys(gb)[0][0])
        assert seen == {23, 24}, "the up arrow bobs the other way"
        for _ in range(3):
            tap(gb, "down")
        gb.run(4)
        assert gb.mem("ml_sel") == 13
        (up, down), _ = arrow_ys(gb)
        assert 23 <= up <= 24 and down == 0, "the end of the list: only the up arrow"
        tap(gb, "down")
        gb.run(4)
        (up, down), _ = arrow_ys(gb)
        assert up == 0 and down >= 112, "wrapped to the top"
        assert gb.read(0xFE00, 12)[6] != gb.read(0xFE00, 12)[10], "an up and a down tile"





# ---- the wood wall and the medal icons (owner 2026-10-17: v1 of the tavern mock-ups without the shelves and bottles; an icon for the best medal) ----
def attr(gb, row, col):
    return gb.pb.memory[1, 0x9800 + row * 32 + col] & 7


def tile_pixels(gb, tid):
    """The 8x8 colour indices of BG tile `tid` (ids < 128 at 0x9000, as the tests of the story font read them)."""
    b = gb.read(0x9000 + tid * 16, 16)
    return [[((b[2 * y + 1] >> (7 - x)) & 1) << 1 | ((b[2 * y] >> (7 - x)) & 1) for x in range(8)] for y in range(8)]


def test_the_medal_icons_differ_by_shape_and_by_colour_index():
    """DMG tells the three by shape (GOLD a solid disc, SILVER a disc with a small hole, BRONZE a ring), CGB by colour: each icon is drawn in its own colour
    index (gold 0, silver 1, bronze 2) of palette 3, the ground colour 3."""
    with to_list(booted("dmg")) as gb:
        shapes = {}
        for tid, idx in ((SKIN_MEDAL, 2), (SKIN_MEDAL + 1, 1), (SKIN_MEDAL + 2, 0)):
            px = tile_pixels(gb, tid)
            assert {v for r in px for v in r} == {idx, 3}, (tid, "one metal colour on the ground")
            shapes[tid] = sum(v != 3 for r in px for v in r)
        assert shapes[SKIN_MEDAL + 2] > shapes[SKIN_MEDAL + 1] > shapes[SKIN_MEDAL], shapes   # solid > small hole > ring


def test_the_list_shows_the_icons_only_for_a_medal_and_the_wall_around_it():
    """The debug list, QUICK DRAW silver, SHIRT CANNON bronze (the shown_list save of tests/test_difficulty.py is not used: the medals come from a block here)."""
    ram = with_block(v7_image(), pr_block(0, [2, 1, 3]))
    for model in ("dmg", "cgb"):
        with to_list(booted(model, ram)) as gb:
            hold_stage_anim(gb)
            assert [tilemap_row(gb, game_row(i), 19, 1)[0] for i in range(4)] == [SKIN_MEDAL + 1, SKIN_MEDAL, SKIN_MEDAL + 2, 54], "silver, bronze, gold; none: the blank tile"
            assert set(tilemap_row(gb, 1, 0, 20)) == {0}, "row 1 is the header band's edge"
            if model == "cgb":
                for i in range(VIS):
                    assert [attr(gb, game_row(i), c) for c in range(20)] == [2] * 19 + [3], i
                    assert [attr(gb, game_row(i) + 1, c) for c in range(20)] == [2] * 20, i
                assert [attr(gb, r, 3) for r in (0, 1, 13, 14, 15, 16, 17)] == [5, 7, 2, 6, 6, 6, 6]
                keys_row = tilemap_row(gb, 16, 0, 20)
                assert [attr(gb, 16, c) for c in range(20)] == [4 if keys_row[c] in (BTN_A, BTN_B, BTN_R) else 6 for c in range(20)]
                assert sum(attr(gb, 16, c) == 4 for c in range(20)) == 3
                for _ in range(8):
                    tap(gb, "down")
                tap(gb, "right")
                gb.run(8)
                for i in range(VIS):
                    assert [attr(gb, game_row(i), c) for c in range(20)] == [2] * 19 + [3], i
                assert sum(attr(gb, 16, c) == 4 for c in range(20)) == 3


def test_cgb_release_list_locked_has_no_buttons(release_built):
    with release_rom("cgb") as gb:                         # (a locked game: "REACH IT IN STORY" / "OR ARCADE", no buttons)
        to_list(gb)
        assert [attr(gb, 16, c) for c in range(20)] == [6] * 20
