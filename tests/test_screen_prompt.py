# The first-boot GBA COLOR MODE prompt (owner 2026-10-21, Q34, src/title.c TM_SCR): a Game Boy Advance that has not chosen between STANDARD and ORIGINAL GBA (code: NORMAL /
# BRIGHT) is asked once, on the title (a label, two lines, no caption; the whole picture is the preview: the cursor on a line shows that choice at once), with STANDARD
# highlighted. A saves the choice (the "SC" block, the one SETTINGS > GBA COLOR MODE writes) and the prompt never comes back until ERASE DATA clears it. A plain Color and a DMG are never asked.
#
# A GBA is simulated as in tests/test_bright.py (conftest.gba_hardware): no choice given = a cartridge with nothing saved.
import pytest

from conftest import (K_ERASE, K_PLAY, K_SCR, K_SCR_BRIGHT, K_SCR_NORMAL, K_SET_GBA, K_SET_STD, K_SETTINGS, K_YES, MENU_SETTLE, TM_SCR, TM_TOP,
                      check_golden, gba_hardware, hold_stage_anim, menu_items, menu_tap, menu_to, title_pick, du_block, DU_AT)
from test_bright import SC_AT, flag, lift_written, pal_ram, ram_with, sc_block, settings_items
from test_sound import make_rom, save_ram

pytestmark = pytest.mark.timeout(600)


def boot(model="cgb", gba=True, ram=None):
    with gba_hardware(gba):                         # (no choice injected: whatever `ram` holds is the cartridge)
        rom = make_rom(model, ram, sound=False)
    rom.run(120)
    hold_stage_anim(rom)
    return rom


def asking(rom):
    return rom.mem("title_menu") == TM_SCR


def move(rom, button):
    menu_tap(rom, button)
    rom.run(30)


def saved(rom):
    return save_ram(rom)[SC_AT:SC_AT + 5]


# ---- who is asked --------------------------------------------------------------------------------------------------------------------
def test_a_gba_with_nothing_saved_is_asked_before_anything_else_with_standard_highlighted():
    r = boot()
    assert asking(r), "the prompt, not PLAY / BONUS / SETTINGS"
    assert menu_items(r) == [K_SCR, K_SCR_NORMAL, K_SCR_BRIGHT] and r.mem("title_sel") == 1, "the label, STANDARD under the cursor"
    assert flag(r) == 5, "NORMAL (bit 1 clear) and asking (bit 2)"
    assert r.mem("game_state") == 0, "on the title"
    assert saved(r) == bytes(5), "looking at it saves nothing"


@pytest.mark.parametrize("model,gba", [("cgb", False), ("dmg", False), ("dmg", True)])
def test_a_plain_color_and_a_dmg_are_never_asked(model, gba):
    r = boot(model, gba)
    assert not asking(r) and r.mem("title_menu") == TM_TOP and menu_items(r)[0] == K_PLAY
    assert flag(r) & 4 == 0 and flag(r) & 2 == 0
    for _ in range(3):
        menu_tap(r, "a" if r.mem("title_sel") else "down")
        r.run(10)
    assert saved(r) == bytes(5), "nothing is written"


# ---- the preview ----------------------------------------------------------------------------------------------------------------------
def test_the_picture_follows_the_cursor_normal_is_a_colors_and_bright_is_the_table():
    r = boot()
    normal = pal_ram(r)
    move(r, "down")
    assert r.mem("title_sel") == 2 and flag(r) == 7, "ORIGINAL GBA under the cursor: bit 1 set, still asking"
    assert pal_ram(r) == lift_written(normal), "the whole title through the table (the same one SETTINGS > SCREEN writes)"
    move(r, "up")
    assert flag(r) == 5 and pal_ram(r) == normal, "and back"
    assert saved(r) == bytes(5), "nothing saved by moving"


def test_the_label_is_on_top_and_there_is_no_caption():
    from test_flow import title_text_row, tilemap_row
    r = boot()
    for want in (2, 1, 2):                                      # (down, up wrap: the label is skipped by the cursor)
        for key, row in (("scr", 7), ("scr_normal", 9), ("scr_bright", 11)):
            assert tilemap_row(r, row, 0, 20) == title_text_row(key), (key, "on its row")
        assert not any(r.image().crop((0, y * 8, 160, y * 8 + 8)).getcolors().__len__() > 1 for y in (12, 13)), "nothing under the lines: no caption"
        move(r, "down")
        assert r.mem("title_sel") == want
    move(r, "up")
    move(r, "up")
    assert r.mem("title_sel") == 2, "UP from STANDARD skips the label to the bottom line"


def test_left_right_b_and_waiting_leave_the_prompt_up():
    r = boot()
    for b in ("left", "right", "b", "select"):
        menu_tap(r, b)
        r.run(10)
        assert asking(r), b
    r.run(1500)                                              # (past the title's 1200-frame idle: the high-score attract)
    assert asking(r) and r.mem("game_state") == 0
    assert saved(r) == bytes(5)


# ---- the pick -------------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("down,button,want,bright", [(0, "a", 1, 0), (1, "a", 2, 2), (0, "start", 1, 0), (1, "start", 2, 2)])
def test_a_saves_the_choice_and_the_title_goes_on_and_it_is_never_asked_again(down, button, want, bright):
    r = boot()
    if down:
        move(r, "down")
    menu_tap(r, button)
    r.run(MENU_SETTLE + 20)
    assert not asking(r) and r.mem("title_menu") == TM_TOP and menu_items(r)[0] == K_PLAY, "the title's top level"
    assert flag(r) == 1 | bright, "the choice, and no longer asking"
    sav = saved(r)
    assert sav == sc_block(want), "the SC block, as SETTINGS writes it"
    r2 = boot("cgb", True, ram_with((SC_AT, sav)))            # power cycle: no prompt, the choice kept
    assert not asking(r2) and r2.mem("title_menu") == TM_TOP and flag(r2) == 1 | bright
    r2.stop()


def test_the_choice_is_changeable_in_settings_afterwards():
    r = boot()
    menu_tap(r, "a")                                         # STANDARD
    r.run(MENU_SETTLE + 20)
    items = settings_items(r)
    assert K_SET_STD in items
    menu_to(r, K_SET_STD)
    menu_tap(r, "a")                                         # COLOR: STANDARD -> COLOR: GBA at once
    r.run(12)
    assert flag(r) == 3 and K_SET_GBA in menu_items(r)
    assert saved(r) == sc_block(2)
    r2 = boot("cgb", True, ram_with((SC_AT, sc_block(2))))
    assert not asking(r2) and flag(r2) == 3, "BRIGHT stays across a power cycle, with no prompt"
    r2.stop()


def test_the_prompt_does_not_disturb_older_saves():
    from save_images import full_image, observe
    img = full_image()
    assert img[SC_AT:SC_AT + 5] == bytes(5)
    r = boot("cgb", True, img)
    assert asking(r), "an older save has no SC block: not chosen"
    before = observe(r)
    move(r, "down")
    menu_tap(r, "a")
    r.run(MENU_SETTLE + 20)
    after = observe(r)
    assert before == after and after["progress"] == 2 and after["tunes"] == 0x2345 | 1 and after["keep"] == 0x80, "the other blocks read as written"
    sav = save_ram(r)
    assert sav[SC_AT:SC_AT + 5] == sc_block(2)


def test_erase_data_brings_the_prompt_back():
    ram = ram_with((SC_AT, sc_block(2)), (DU_AT, du_block(0)))
    r = boot("cgb", True, ram)
    assert not asking(r) and flag(r) == 3
    title_pick(r, K_SETTINGS)
    r.run(MENU_SETTLE)
    menu_to(r, K_ERASE)
    menu_tap(r, "a")
    menu_to(r, K_YES)
    menu_tap(r, "a")
    r.run(MENU_SETTLE + 20)
    assert asking(r) and r.mem("title_sel") == 1 and flag(r) == 5, "a blank cartridge asks again, STANDARD highlighted"
    sav = save_ram(r)
    assert sav[SC_AT:SC_AT + 5] == bytes(5)
    r2 = boot("cgb", True, sav)                              # (and the next power-on, if it is not answered)
    assert asking(r2)
    r2.stop()


def test_erase_data_on_a_plain_color_goes_to_the_top_level():
    r = boot("cgb", False)
    title_pick(r, K_SETTINGS)
    r.run(MENU_SETTLE)
    menu_to(r, K_ERASE)
    menu_tap(r, "a")
    menu_to(r, K_YES)
    menu_tap(r, "a")
    r.run(MENU_SETTLE + 20)
    assert not asking(r) and r.mem("title_menu") == TM_TOP


# ---- goldens (new) -------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("name,downs", [("screen_prompt_normal", 0), ("screen_prompt_bright", 1)])
def test_the_prompt_goldens(name, downs):
    r = boot()
    for _ in range(downs):
        move(r, "down")
    r.run(30)
    check_golden(r, name)
