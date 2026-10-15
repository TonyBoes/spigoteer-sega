# Backing out to a menu: the mug cursor and the highlighted line must agree (owner 2026-10-15: "When backing out to the menu, the
# word highlight is not always in the same position as the mug"). The title's highlight is the gold text row (CGB: the BG attribute
# of the selected line, src/title.c title_enter / menu_frame); the lists (BONUS > MINI GAMES, BOSS RUSH) and the soundtrack
# player have the mug alone, so there the line under the mug must be the selected game / boss and the details below must be
# its own. Every way back is driven: B on each screen, a game's HOW TO PLAY card (B), a game's result window (B), the pause
# menu's QUIT TO MENU, the boss rush's quit and its result.
import pytest
import test_mg_list as ml
import test_pause as tp
import test_rush as tr
from conftest import (K_BONUS, K_MINIGAMES, K_SOUNDTRACK, MENU_SETTLE, TM_BONUS, TM_TOP, menu_tap, title_pick)
from test_flow import GS_GOAL, PLAYING, TITLE, run_until, state
from test_mg import GS_MGLIST, GS_MINI, MG_PLAY
from test_scores import booted

pytestmark = pytest.mark.timeout(300)

BGPAL_TEXT, BGPAL_TEXT_SEL = 3, 4            # src/title.c
OAM_CURSOR = 5                               # src/title.c: the title's cursor is OAM entry 5


def title_ok(gb, menu, sel):
    """The title shows submenu `menu` with the cursor on line `sel`: the mug on that line's row and (CGB) the gold attribute on that
    row only."""
    run_until(gb, lambda: state(gb) == TITLE and gb.pb.memory[0xFF40] & 0x80, 60)
    gb.run(MENU_SETTLE + 6)
    n = gb.mem("title_n")
    rows = list(gb.read("title_rows", n))
    assert gb.mem("title_menu") == menu and gb.mem("title_sel") == sel, (gb.mem("title_menu"), gb.mem("title_sel"))
    assert gb.mem(0xFE00 + 4 * OAM_CURSOR) == rows[sel] * 8 - 7 + 16, "the mug stands on the selected line"
    if gb.model_name == "cgb":
        pals = [gb.pb.memory[1, 0x9800 + r * 32 + 5] & 7 for r in rows]
        assert pals == [BGPAL_TEXT_SEL if k == sel else BGPAL_TEXT for k in range(n)], ("the gold line is the mug's line", pals, sel)


NAMES = [n for n, _ in ml.LIST] + ["GREEN LIGHT"]
WHERE = [w for _, w in ml.LIST] + ["THE TEST STUB"]


def list_ok(gb, sel):
    """BONUS > MINI GAMES on game `sel`: the mug (OAM 0) stands on the line that names it, and the details below are its own."""
    run_until(gb, lambda: state(gb) == GS_MGLIST and gb.pb.memory[0xFF40] & 0x80, 60)
    gb.run(8)
    assert gb.mem("ml_sel") == sel
    y = gb.mem(0xFE00)
    row = (y - 16 + 7) // 8
    assert 2 <= row <= 12 and row % 2 == 0 and (y - 16 + 7) % 8 == 0, "a game's row (every other row)"
    assert ml.line(gb, row).split("  ")[0].strip() == NAMES[sel], (row, ml.line(gb, row))
    assert ml.line(gb, 16).strip() == ml.KEYS
    assert gb.mem(0xFE00 + 1) == 8


def rush_ok(gb, scr, sel):
    """The boss rush's menu (ALL / CHOOSE) or list: the line under the mug is the selected one."""
    run_until(gb, lambda: tr.on_rush(gb, scr), 60)
    gb.run(8)
    y = gb.mem(0xFE00)
    row = (y - 16 + 7) // 8
    text = tr.line(gb, row)
    if scr == tr.RS_MENU:
        assert text.strip().split(" ")[0] == ("CHOOSE" if sel else "ALL"), text
    else:
        assert text.strip().startswith(tr.NAMES[tr.BUILT[sel]]), (text, sel)


# ---- the title's own submenus (B goes back to the top level, the cursor on the item it came from) -------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_top_level_after_b_in_a_submenu(model):
    with booted(model) as gb:
        title_ok(gb, TM_TOP, 0)
        for k, item in enumerate((0, 1, 2)):             # PLAY, BONUS, SETTINGS
            for _ in range(k):
                menu_tap(gb, "down")
            menu_tap(gb, "a")
            gb.run(MENU_SETTLE)
            menu_tap(gb, "b")
            title_ok(gb, TM_TOP, k)
            for _ in range(k):
                menu_tap(gb, "up")
            gb.run(MENU_SETTLE)


# ---- every screen under BONUS: B comes back with the cursor on the item it was opened from ------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_b_from_the_soundtrack_the_list_and_the_rush_menu(model):
    with booted(model) as gb:
        title_pick(gb, K_BONUS, K_SOUNDTRACK)
        run_until(gb, lambda: state(gb) != TITLE, 30)
        gb.run(6)
        for _ in range(3):
            if state(gb) == TITLE:
                break
            gb.press("b", 2)
            gb.run(4)
        title_ok(gb, TM_BONUS, 0)
        menu_tap(gb, "down")
        menu_tap(gb, "a")
        list_ok(gb, 0)
        gb.press("b", 2)
        title_ok(gb, TM_BONUS, 1)
        menu_tap(gb, "down")
        menu_tap(gb, "a")
        run_until(gb, lambda: tr.on_rush(gb, tr.RS_MENU), 30)
        rush_ok(gb, tr.RS_MENU, 0)
        gb.press("b", 2)
        title_ok(gb, TM_BONUS, 2)
        menu_tap(gb, "b")
        title_ok(gb, TM_TOP, 1)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("sel", [0, 5, 9, 12, 13])
def test_the_list_keeps_its_selection_through_b_and_back_in(model, sel):
    """The list on game `sel` (scrolled when it is past the tenth), B to the title, A to come back in: the same game, the mug on its line."""
    with ml.to_list(booted(model)) as gb:
        for _ in range(sel):
            ml.tap(gb, "down")
        gb.run(4)
        list_ok(gb, sel)
        gb.press("b", 2)
        title_ok(gb, TM_BONUS, 1)
        menu_tap(gb, "a")
        list_ok(gb, sel)


# ---- a game left to the list: the card's B, the result's B, QUIT TO MENU ------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("sel", [0, 6, 12])
def test_the_list_after_the_card_b_the_result_b_and_quit(model, sel):
    with ml.to_list(booted(model, cards=False)) as gb:
        for _ in range(sel):
            ml.tap(gb, "down")
        gb.run(4)
        gb.press("a", 2)                                  # the HOW TO PLAY card (first play of the game)
        run_until(gb, lambda: state(gb) == GS_MINI and gb.pb.memory[0xFF40] & 0x80, 60)
        gb.run(10)
        gb.press("b", 2)                                  # the card's B BACK
        list_ok(gb, sel)
        gb.press("b", 2)
        title_ok(gb, TM_BONUS, 1)
        menu_tap(gb, "a")
        list_ok(gb, sel)
    with tp.rom_s(model) as gb:                           # (cards seen: the game plays at once)
        ml.to_list(gb)
        for _ in range(sel):
            ml.tap(gb, "down")
        for how in (tp.finish_it, tp.quit_it):
            gb.press("a", 2)
            run_until(gb, lambda: state(gb) == GS_MINI and gb.pb.memory[0xFF40] & 0x80, 60)
            tp.until(gb, lambda: gb.mem("mg_phase") == MG_PLAY, 600)
            gb.run(5)
            how(gb)
            tp.settled(gb, GS_MGLIST)
            list_ok(gb, sel)
        gb.press("b", 2)
        title_ok(gb, TM_BONUS, 1)


# ---- the boss rush: its list and its quit -------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_boss_rush_menu_and_list_after_b_and_after_a_quit(model):
    with tp.rom_s(model) as gb:
        tr.to_list(gb)
        tr.tap(gb, "down")
        rush_ok(gb, tr.RS_LIST, 1)
        tr.tap(gb, "b")                                   # the list's B: the menu, the cursor on CHOOSE... (menu_open(1))
        rush_ok(gb, tr.RS_MENU, 1)
        tr.tap(gb, "a")
        rush_ok(gb, tr.RS_LIST, 1)                        # (the list keeps its selection)
        tr.tap(gb, "a")                                   # a fight, then QUIT TO MENU
        run_until(gb, lambda: state(gb) == GS_GOAL, 60)
        gb.press("a", 2)
        run_until(gb, lambda: state(gb) == PLAYING, 20)
        gb.run(30)
        tp.tap(gb, "start", 3)
        tp.quit_yes(gb)
        run_until(gb, lambda: tr.on_rush(gb, tr.RS_MENU), 60)
        rush_ok(gb, tr.RS_MENU, 0)
        gb.press("b", 2)
        title_ok(gb, TM_BONUS, 2)
