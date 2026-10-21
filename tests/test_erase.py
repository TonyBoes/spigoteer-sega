# SETTINGS > ERASE DATA (owner 2026-10-16; src/title.c, src/save.c save_erase): "ERASE ALL DATA", NO (the cursor starts there) / YES. YES zeroes the whole
# 8 KB of cartridge RAM -- every block, the old versions', anything unknown -- and reloads the game's working copies from it, so the save reads exactly like a
# blank cartridge (no block checks out: every table empty, no story, the title tune only, no medals, SNAP, the debug menu locked again), then the title.
import pytest
from conftest import (check_golden, debug_unlocked, K_DEBUG, K_ERASE, K_ERASEQ, K_MUSIC, K_NO, K_PLAY, K_SETTINGS, K_YES, K_STORY, K_CONTINUE, K_ARCADE, K_BARCHANGE, K_BARKEEP, K_CLASSIC,
                      MENU_SETTLE, TM_ERASE, TM_PLAY, TM_SETTINGS, TM_TOP, menu_items, menu_tap, menu_to, sram_peek, title_pick, unlock_debug)
from save_images import SIZE, all_views, full_image, observe, put
from test_flow import cursor_on, expect_menu, menu_rows, settings_items, settings_keys, settings_row, settle_title, title_text_row, tilemap_row
from test_sound import make_rom, save_ram

pytestmark = pytest.mark.timeout(240)

MODELS = ["dmg", "cgb"]


def boot_with(model, img=None):
    """A booted title; cards=False: the image is exactly what the test gave (no HOW TO PLAY block added)."""
    rom = make_rom(model, img, sound=False, cards=False)
    rom.run(120)
    rom.model_name = model
    from conftest import hold_stage_anim
    hold_stage_anim(rom)
    return rom


def prompt(rom):
    """SETTINGS > ERASE DATA: the prompt is up (cursor on NO)."""
    title_pick(rom, K_SETTINGS, K_ERASE)
    rom.run(MENU_SETTLE)
    return rom


# ---- the line and the prompt ----
@pytest.mark.parametrize("model", MODELS)
def test_erase_data_is_the_third_settings_line_and_asks_first(model):
    rom = boot_with(model)
    try:
        title_pick(rom, K_SETTINGS)
        rom.run(MENU_SETTLE)
        assert menu_items(rom) == settings_items(rom), "MUSIC, BAR CHANGE, (a Color: SCREEN,) ERASE DATA"
        expect_menu(rom, settings_keys(rom))
        menu_to(rom, K_ERASE)
        cursor_on(rom, "erase", settings_row(rom, len(settings_items(rom)) - 1))
        menu_tap(rom, "a")
        rom.run(MENU_SETTLE)
        assert rom.mem("title_menu") == TM_ERASE and menu_items(rom) == [K_ERASEQ, K_NO, K_YES]
        assert rom.mem("title_sel") == 1, "the cursor starts on NO"
        expect_menu(rom, ("erase_q", "no", "yes"))
        cursor_on(rom, "no", 9)
        assert sram_peek(rom, 0, SIZE) == bytes(SIZE), "asking changes nothing"
    finally:
        rom.stop()


@pytest.mark.parametrize("model", MODELS)
def test_the_prompt_text_is_centred_and_fits_the_title_tile_budget(model):
    """Every new line is centred to the pixel like the others, YES by a trailing space (4 px left of the middle: the odd-length art would cost three more
    title tiles, and the title's text slot is full: tools/gen_art.py TITLE_TILE_END)."""
    from test_flow import TITLE_ART
    for key, s in (("erase", "ERASE DATA"), ("debug", "DEBUG MENU"), ("erase_q", "ERASE ALL DATA"), ("no", "NO")):
        t = TITLE_ART["text"][key]
        n = len(t["tiles"])
        assert n % 2 == 0 and t["col"] == (20 - n) // 2, key
        left = t["x"] - 1
        assert left == 160 - (left + 8 * len(s)), f"{key}: {left} px left, {160 - left - 8 * len(s)} px right"
    assert TITLE_ART["text"]["yes"]["x"] - 1 == 160 - (TITLE_ART["text"]["yes"]["x"] - 1 + 8 * 4), "YES sits in a four-tile cell"
    assert TITLE_ART["patron_base"] + 4 <= 244      # (240; 242 for the STORY difficulty prompt, 244 for its captions: the DMG mug copies' ids, made at every level start)


@pytest.mark.parametrize("model", MODELS)
def test_the_cursor_never_rests_on_the_label_and_wraps_between_no_and_yes(model):
    rom = boot_with(model)
    try:
        prompt(rom)
        seen = []
        for k in ("up", "up", "down", "down", "down"):
            menu_tap(rom, k)
            seen.append(menu_items(rom)[rom.mem("title_sel")])
        assert seen == [K_YES, K_NO, K_YES, K_NO, K_YES], "Up from NO wraps to YES past the label, Down from YES to NO"
    finally:
        rom.stop()


@pytest.mark.parametrize("key", ["a", "start", "b"])
@pytest.mark.parametrize("model", MODELS)
def test_no_and_b_go_back_to_settings_on_erase_data_and_change_nothing(model, key):
    img = full_image()
    rom = boot_with(model, img)
    try:
        prompt(rom)
        menu_tap(rom, key)                                 # (A, START or B on NO)
        rom.run(MENU_SETTLE)
        assert rom.mem("title_menu") == TM_SETTINGS and menu_items(rom)[rom.mem("title_sel")] == K_ERASE
        assert sram_peek(rom, 0, SIZE) == img, "nothing was erased"
    finally:
        rom.stop()


# ---- the erase ----
@pytest.mark.parametrize("model", MODELS)
def test_yes_zeroes_all_of_sram_and_returns_to_the_title(model):
    img = put(full_image(), 0x200, bytes([0xA5]) * (SIZE - 0x200))      # (and junk where no block lives: an erase leaves nothing)
    rom = boot_with(model, img)
    try:
        assert observe(rom)["progress"] == 2
        prompt(rom)
        menu_tap(rom, "down")                              # NO -> YES
        assert menu_items(rom)[rom.mem("title_sel")] == K_YES
        menu_tap(rom, "a")
        rom.run(MENU_SETTLE + 10)
        assert sram_peek(rom, 0, SIZE) == bytes(SIZE), "every byte"
        assert rom.mem("game_state") == 0 and rom.mem("title_menu") == TM_TOP and menu_items(rom)[rom.mem("title_sel")] == 6, "the title's top level, on SETTINGS"
        assert not debug_unlocked(rom)
        ram = save_ram(rom)
    finally:
        pass
    assert ram == bytes(SIZE), "and still, when the cartridge is read back"


def blank_view(model, img=None):
    rom = boot_with(model, img)
    try:
        o = observe(rom)
    finally:
        rom.stop()
    return o


@pytest.mark.parametrize("model", MODELS)
def test_after_the_erase_the_game_reads_exactly_like_a_blank_cartridge(model):
    blank = blank_view(model)
    assert blank["progress"] == 0 and blank["tunes"] == 1 and blank["mg_unlocked"] == 0 and blank["scores"] == bytes(60) and blank["keep"] == 0
    img = full_image()
    rom = boot_with(model, img)
    try:
        before = observe(rom)
        assert before != blank and before["keep"] == 0x80 and before["tunes"] != 1
        prompt(rom)
        menu_tap(rom, "down")
        menu_tap(rom, "a")
        rom.run(MENU_SETTLE + 30)
        assert observe(rom) == blank, "the working copies: the story, the tunes, the three tables, the practice medals, BAR CHANGE"
        assert rom.mem("save_lock") == 0 and rom.mem("sound_on") == 1
        after = save_ram(rom)
    finally:
        pass
    assert after == bytes(SIZE)
    # ... and the cartridge as the erase left it boots like a new one, and like a factory-fresh one of either kind (zeros, 0xFF)
    for image in (after, bytes([0xFF]) * SIZE, None):
        assert blank_view(model, image) == blank
    for image in (after,):
        assert all_views(model, image) == all_views(model, None)


@pytest.mark.parametrize("model", MODELS)
def test_after_the_erase_the_menus_are_the_new_game_s(model):
    from test_flow import hi_tiles
    rom = boot_with(model, full_image())
    try:
        title_pick(rom, K_PLAY)
        rom.run(MENU_SETTLE)
        assert menu_items(rom)[0] == K_CONTINUE, "a story to continue before"
        menu_tap(rom, "b")
        rom.run(MENU_SETTLE)
        prompt(rom)
        menu_tap(rom, "down")
        menu_tap(rom, "a")
        rom.run(MENU_SETTLE + 30)
        title_pick(rom, K_PLAY)
        rom.run(MENU_SETTLE)
        assert menu_items(rom) == [K_STORY, K_ARCADE, K_CLASSIC], "no CONTINUE"
        menu_tap(rom, "b")
        rom.run(MENU_SETTLE + 20)
        assert tilemap_row(rom, 0, 8, 6) == hi_tiles("000000"), "the HI line is 000000"
        title_pick(rom, K_SETTINGS)
        rom.run(MENU_SETTLE)
        assert menu_items(rom) == settings_items(rom), "BAR SNAP, and no DEBUG MENU line"
        assert menu_items(rom)[0] == K_MUSIC
    finally:
        rom.stop()


@pytest.mark.parametrize("model", MODELS)
def test_erasing_locks_the_debug_menu_again(model):
    rom = boot_with(model, full_image())
    try:
        assert debug_unlocked(rom)
        title_pick(rom, K_SETTINGS)
        rom.run(MENU_SETTLE)
        assert menu_items(rom) == settings_items(rom, K_BARKEEP, debug=True), "BAR KEEP is saved, DEBUG MENU is there"
        menu_to(rom, K_ERASE)
        menu_tap(rom, "a")
        menu_tap(rom, "down")
        menu_tap(rom, "a")
        rom.run(MENU_SETTLE + 10)
        assert not debug_unlocked(rom) and rom.mem("level_dirs") & 0x80 == 0
        title_pick(rom, K_SETTINGS)
        rom.run(MENU_SETTLE)
        assert menu_items(rom) == settings_items(rom)
        rom.hold("select")                                 # and the gesture no longer opens it
        rom.run(2)
        for _ in range(3):
            rom.press("start", 2)
            rom.run(3)
        rom.release("select")
        assert rom.mem("debug_menu_open") == 0
    finally:
        rom.stop()


@pytest.mark.parametrize("model", MODELS)
def test_an_erased_cartridge_is_a_working_one(model):
    """After the erase a score is entered and saved as on a new cartridge."""
    from test_scores import game_over_with, table
    rom = boot_with(model, full_image())
    try:
        prompt(rom)
        menu_tap(rom, "down")
        menu_tap(rom, "a")
        rom.run(MENU_SETTLE + 30)
        assert table(rom)[0] == ("   ", 0)
        game_over_with(rom, 1234)
        rom.run(60)
        ram = save_ram(rom)
    finally:
        pass
    assert ram[:4] == b"TPR7", "the first save writes the main block again"


@pytest.mark.parametrize("model", MODELS)
def test_goldens_of_the_prompt_and_of_settings_with_the_debug_line(model):
    rom = boot_with(model, put(bytes(SIZE), 0x18, __import__("conftest").du_block()))
    try:
        settle_title(rom)
        title_pick(rom, K_SETTINGS)
        rom.run(MENU_SETTLE + 10)
        check_golden(rom, "title_settings_debug")
        menu_to(rom, K_ERASE)
        menu_tap(rom, "a")
        rom.run(MENU_SETTLE + 10)
        check_golden(rom, "title_erase_prompt")
    finally:
        rom.stop()
