# SETTINGS > COLOR: STANDARD / GBA (the first-boot prompt: GBA COLOR MODE, STANDARD / ORIGINAL GBA; code: NORMAL / BRIGHT; the line is on a GBA only; src/bright.h, src/bright.c, main.c pal_put, title.c, save.c "SC" block): a gamma lift on every palette colour for a
# Game Boy Advance, whose Color-mode screen shows GBC colours much darker.
#
# A GBA is simulated by conftest.gba_hardware(): PyBoy's boot ROM leaves B = 0 (a plain Color); a hook on the cartridge's entry point sets B = 1, which GBDK
# crt0 stores in _is_GBA (GB_GBA=1 does it for a whole run). The game keeps its choice in bits 1-2 of that same byte (no new WRAM): bit 0 the hardware, bit 1
# BRIGHT, bit 2 "not chosen yet, ask" (a GBA with nothing saved: the title opens its first-boot SCREEN prompt, tests/test_screen_prompt.py). So 0 NORMAL on a
# Color, 1 on a GBA that chose NORMAL, 2 BRIGHT on a Color that chose it, 3 BRIGHT on a GBA, 5 a GBA that has not chosen. gba_hardware(True, 2) is a GBA
# that chose BRIGHT (the cartridge RAM gets the save block), which is what every lift test below runs.
#
# The lift is read off palette RAM: a BRIGHT run and a NORMAL run, driven the same way to the same frame, differ exactly by the 32-entry table on every colour
# (title, level, a tip's coin and the show, a story picture, a credits card, a boss fight, a scene change's fades and the pause's).
from io import BytesIO

import numpy as np
import pytest
from PIL import Image

from conftest import (K_BARCHANGE, K_DEBUG, K_ERASE, K_NO, K_PLAY, K_SET_GBA, K_SET_STD, K_SETTINGS, K_YES, MENU_SETTLE, ROM, TM_SCR, TM_SETTINGS, check_golden, gba_hardware,
                      hold_stage_anim, menu_items, menu_tap, menu_to, title_level, title_pick, trans_enable, du_block, DU_AT)
from test_sound import make_rom, save_ram

pytestmark = pytest.mark.timeout(600)

GAMMA = 0.7
TABLE = [round(31 * (i / 31) ** GAMMA) for i in range(32)]
SC_AT = 0x30


def lift_word(w):
    return TABLE[w & 31] | (TABLE[(w >> 5) & 31] << 5) | (TABLE[(w >> 10) & 31] << 10)


def lift_bytes(b):
    out = bytearray()
    for i in range(0, len(b), 2):
        w = lift_word(b[i] | (b[i + 1] << 8))
        out += bytes([w & 255, w >> 8])
    return bytes(out)


def pal_ram(gb):
    """All of palette RAM (BG 64 bytes, then OBJ 64) through the CGB's palette ports."""
    m, out = gb.pb.memory, bytearray()
    for idx, data in ((0xFF68, 0xFF69), (0xFF6A, 0xFF6B)):
        for i in range(64):
            m[idx] = i
            out.append(m[data])
    out[120:128] = bytes(8)             # (OBJ palette 7 is the title's DX badge, whose colours cycle with time: not part of the comparison)
    return bytes(out)


def sc_block(mode):
    b = bytearray(b"SC" + bytes([mode]))
    c = (0x5A + sum(b)) & 255
    return bytes(b + bytes([c, c ^ 255]))


def ram_with(*blocks):
    r = bytearray(0x2000)
    for at, b in blocks:
        r[at:at + len(b)] = b
    return bytes(r)


def rom_at(model="cgb", gba=False, ram=None, choice=2):
    """gba: a GBA that has chosen `choice` (2 BRIGHT; None: it has not chosen, the prompt is up); an image that has its own SC block keeps it."""
    with gba_hardware(gba, choice):
        rom = make_rom(model, ram, sound=False)
    rom.run(120)
    hold_stage_anim(rom)
    return rom


def flag(rom):
    return rom.mem("_is_GBA")


# ---- the table ------------------------------------------------------------------------------------------------------------------------
def test_the_table_is_a_gamma_lift_that_keeps_dark_colours_apart_and_white_and_black_fixed():
    assert TABLE[0] == 0 and TABLE[31] == 31
    assert all(b > a for a, b in zip(TABLE[:17], TABLE[1:17])), "strictly rising through the darks (0..16): dark colours stay distinguishable"
    assert all(b >= a for a, b in zip(TABLE, TABLE[1:])), "never falling (a few of the lights share a value: 16/17, 21/22, 25/26, 29/30)"
    assert all(TABLE[i] >= i for i in range(32)), "never darker"
    assert bytes(TABLE) in ROM.read_bytes(), "the ROM carries this table (src/bright.c)"


# ---- the option: Color only, defaulting to the hardware -------------------------------------------------------------------------------------
def settings_items(rom):
    title_pick(rom, K_SETTINGS)
    rom.run(MENU_SETTLE)
    return menu_items(rom)


def test_the_line_is_on_a_gba_only():
    with rom_at("cgb", True) as g:
        assert settings_items(g) == [2, K_BARCHANGE, K_SET_GBA, K_ERASE], "a GBA that chose GBA: MUSIC, BAR, COLOR: GBA, ERASE DATA"
    with rom_at("cgb", True, ram_with((SC_AT, sc_block(1)))) as g:
        assert settings_items(g) == [2, K_BARCHANGE, K_SET_STD, K_ERASE], "COLOR: STANDARD"
    with rom_at("cgb", False) as c:     # (a plain Color, even one whose save says GBA, has no line)
        assert settings_items(c) == [2, K_BARCHANGE, K_ERASE], "MUSIC, BAR, ERASE DATA"
    with rom_at("cgb", False, ram_with((SC_AT, sc_block(2)))) as c:
        assert settings_items(c) == [2, K_BARCHANGE, K_ERASE]
    for gba in (False, True):
        with rom_at("dmg", gba) as d:   # (a DMG with B = 1 is no GBA: the register means nothing there)
            assert settings_items(d) == [2, K_BARCHANGE, K_ERASE]
            assert flag(d) & 2 == 0, "BRIGHT is never on in a DMG"


def test_the_default_is_normal_and_a_gba_that_has_not_chosen_asks():
    with rom_at("cgb", False) as c:
        assert flag(c) == 0 and K_SET_STD not in settings_items(c), "a plain Color: NORMAL, no line"
    with rom_at("cgb", True, choice=None) as g:
        assert flag(g) == 5, "a GBA, nothing saved: NORMAL (bit 1 clear), the prompt asked for (bit 2)"


def test_a_saved_choice_beats_the_default():
    normal, bright = ram_with((SC_AT, sc_block(1))), ram_with((SC_AT, sc_block(2)))
    with rom_at("cgb", True, normal) as r:
        assert flag(r) == 1 and K_SET_STD in settings_items(r), "a GBA that chose NORMAL"
    with rom_at("cgb", False, bright) as r:
        assert flag(r) == 2 and K_SET_GBA not in settings_items(r), "a Color that chose BRIGHT: lifted, no line"


def test_a_choice_that_does_not_check_out_reads_as_not_chosen():
    bad = bytearray(sc_block(1))
    bad[3] ^= 1                                           # checksum
    odd = bytearray(sc_block(7))                           # a value the game never writes (valid checksum)
    for blk in (bytes(bad), bytes(odd)):
        with rom_at("cgb", True, ram_with((SC_AT, blk)), choice=None) as r:
            assert flag(r) == 5, "a GBA: not chosen, it asks again, whatever the broken block says"
        with rom_at("cgb", False, ram_with((SC_AT, blk))) as r:
            assert flag(r) == 0


# ---- the save: round trip and upgrade -------------------------------------------------------------------------------------------------
def toggle(rom, press="a"):
    """SETTINGS' COLOR line (a GBA): the key switches STANDARD <-> GBA at once, saved."""
    menu_to(rom, K_SET_STD if K_SET_STD in menu_items(rom) else K_SET_GBA)
    before = flag(rom) & 2
    menu_tap(rom, press)
    rom.run(12)
    assert flag(rom) & 2 != before and menu_items(rom)[rom.mem("title_sel")] == (K_SET_STD if before else K_SET_GBA), "switched, still on the line"


def test_the_choice_is_written_when_it_changes_and_survives_a_power_cycle():
    r = rom_at("cgb", True, ram_with((SC_AT, sc_block(1))))
    settings_items(r)
    toggle(r)
    assert flag(r) == 3
    sav = save_ram(r)
    assert sav[SC_AT:SC_AT + 5] == sc_block(2)
    r2 = rom_at("cgb", True, sav)
    assert flag(r2) == 3, "power-cycled: still GBA"
    settings_items(r2)
    toggle(r2, "start")
    assert flag(r2) == 1
    sav2 = save_ram(r2)
    assert sav2[SC_AT:SC_AT + 5] == sc_block(1), "STANDARD written explicitly (a default must not come back on a GBA)"
    r3 = rom_at("cgb", True, sav2)
    assert flag(r3) == 1, "a GBA that went back to STANDARD stays there"
    r3.stop()
    r4 = rom_at("cgb", True, ram_with((SC_AT, sc_block(2))))
    settings_items(r4)
    toggle(r4, "a")
    assert flag(r4) == 1 and save_ram(r4)[SC_AT:SC_AT + 5] == sc_block(1)


def test_an_older_save_without_the_block_loads_cleanly_and_the_other_blocks_are_untouched():
    from save_images import full_image, without, observe, SIZE
    img = full_image()
    assert img[SC_AT:SC_AT + 5] == bytes(5), "no save of any older version has anything at 0x30"
    for gba, want in ((False, 0), (True, 5)):
        with gba_hardware(gba):
            r = make_rom("cgb", img, sound=False)
        r.run(120)
        assert flag(r) == want, "not chosen: NORMAL, and a GBA asks"
        o = observe(r)
        assert o["progress"] == 2 and o["tunes"] == (0x2345 & 0xFFF1) | 1 and o["keep"] == 0x80, "the other blocks read as written"
        r.stop()


def test_erase_data_clears_the_choice_and_a_gba_is_asked_again():
    ram = ram_with((SC_AT, sc_block(1)), (DU_AT, du_block(0)))
    r = rom_at("cgb", True, ram)
    assert flag(r) == 1
    title_pick(r, K_SETTINGS)
    r.run(MENU_SETTLE)
    menu_to(r, K_ERASE)
    menu_tap(r, "a")
    menu_to(r, K_YES)
    menu_tap(r, "a")
    r.run(20)
    assert flag(r) == 5, "a GBA with nothing saved: NORMAL and the prompt again (tests/test_screen_prompt.py)"
    assert save_ram(r)[SC_AT:SC_AT + 5] == bytes(5), "ERASE DATA wrote the whole cartridge zero"


# ---- the lift on screen --------------------------------------------------------------------------------------------------------------------
def shot_title(gba):
    r = rom_at("cgb", gba)
    r.run(10)
    out = pal_ram(r), r.image()
    r.stop()
    return out


def shot_settings(gba):
    r = rom_at("cgb", gba)
    settings_items(r)
    r.run(30)
    out = pal_ram(r), r.image()
    r.stop()
    return out


def level_rom(gba):
    r = rom_at("cgb", gba)
    title_level(r)
    r.run(100)
    r.write("tip_chance", 0)
    return r


def shot_level(gba):
    r = level_rom(gba)
    out = pal_ram(r), r.image()
    r.stop()
    return out


def shot_tip(gba):
    r = level_rom(gba)
    r.write("tip_timer", 200)
    r.write("tip_bar", 1)
    r.write("tip_x", 60)
    r.run(3)
    out = pal_ram(r), r.image()
    r.stop()
    return out


def shot_show(gba):
    r = level_rom(gba)
    r.write("tip_timer", 200)
    r.write("tip_bar", 1)
    r.write("tip_x", 60)
    r.run(3)
    r.write("tip_timer", 0)
    r.write("show_timer", 100)
    r.run(3)
    out = pal_ram(r), r.image()
    r.stop()
    return out


def shot_story(gba):
    from test_story import page_ready, start_story
    with gba_hardware(gba, 2), start_story("cgb") as gb:
        page_ready(gb)
        return pal_ram(gb), gb.image()


def shot_credits(gba):
    from test_credits import roll_from_bonus
    with gba_hardware(gba, 2), roll_from_bonus("cgb", sound=False) as gb:
        gb.run(900)                                           # (the scrolling credits: the first stops' portraits are up)
        return pal_ram(gb), gb.image()


def shot_boss(gba):
    from boss_common import fight, play
    with gba_hardware(gba, 2):
        gb = fight("cgb", 5)                                  # the robot factory's Prototype: his palettes stream in through the boss loader's queue (boss.c)
        play(gb)
        gb.run(30)
        out = pal_ram(gb), gb.image()
        gb.stop()
    return out


SHOTS = {"title": shot_title, "settings": shot_settings, "level": shot_level, "tip": shot_tip, "show": shot_show, "story": shot_story,
         "credits": shot_credits, "boss": shot_boss}


def brighter(a, b):
    a, b = np.asarray(a, float).mean(), np.asarray(b, float).mean()
    return b > a + 1


BOOT_PAL = bytes.fromhex("e71c191e317e7b21")     # what the Color's boot ROM leaves in a palette the game never writes (OBJ 3, 4 and 7 on most screens)


def lift_written(n_pal):
    """The NORMAL run's palette RAM through the table, except a palette still holding the boot ROM's (the game never wrote it: nothing to lift)."""
    return b"".join(n_pal[i:i + 8] if n_pal[i:i + 8] == BOOT_PAL else lift_bytes(n_pal[i:i + 8]) for i in range(0, 128, 8))


@pytest.mark.parametrize("name", list(SHOTS))
def test_bright_is_the_table_applied_to_every_colour_normal_is_untouched(name):
    n_pal, n_img = SHOTS[name](False)
    b_pal, b_img = SHOTS[name](True)
    assert b_pal == lift_written(n_pal), f"{name}: palette RAM of a BRIGHT run is the NORMAL run's through the table"
    assert b_pal != n_pal and brighter(n_img, b_img), "and the picture is brighter"


def test_a_gba_that_chose_normal_is_byte_identical_to_a_color():
    ram = ram_with((SC_AT, sc_block(1)))
    n_pal, n_img = shot_title(False)
    r = rom_at("cgb", True, ram)
    r.run(10)
    # The title's logo is a beer-fill animation. A GBA with a saved SCREEN block boots one frame longer than a plain Color (since the save code grew: sys_time 39 against
    # 40 at the same run(10); before, equal), and the animation's bubbles follow the boot's timing, so the logo band differs between the two in its foam only (measured:
    # 150 px, x 28-69, y 17-46; the first frames of the two runs are identical, from the third they drift). The palette RAM and every pixel outside the logo band are compared.
    import numpy as np
    a, b = np.asarray(n_img.convert("RGB")).copy(), np.asarray(r.image().convert("RGB")).copy()
    a[:64], b[:64] = 0, 0
    assert pal_ram(r) == n_pal and (a == b).all(), "the title"
    r.stop()
    n_pal, n_img = shot_level(False)
    r = rom_at("cgb", True, ram)
    title_level(r)
    r.run(100)
    assert pal_ram(r) == n_pal and r.image().tobytes() == n_img.tobytes(), "a level"
    r.stop()


# ---- the fades end on the right colours ------------------------------------------------------------------------------------------------------
def start_arcade_with_fades(gba):
    from test_flow import GS_GOAL, PLAYING, run_until, state
    r = rom_at("cgb", gba)
    trans_enable(r)
    title_pick(r, K_PLAY, 0)                                # ARCADE: the drink fills the screen, the goal banner, then play
    run_until(r, lambda: state(r) == GS_GOAL, 600)
    r.write("tip_chance", 0)
    r.run(100)
    r.press("a", 2)
    run_until(r, lambda: state(r) == PLAYING, 600)
    r.run(200)
    return r


def test_the_scene_change_fades_and_the_pause_fades_end_on_the_scenes_own_colours():
    """Title -> ARCADE behind the drink fade (transitions on), then PAUSE and RESUME (the amber and white fades): in a BRIGHT run each ends on exactly the
    NORMAL run's colours through the table. White (0x7FFF) and black are fixed points of the table, so the fades' ends do not move."""
    from test_flow import run_until, state
    shots = {}
    for gba in (False, True):
        r = start_arcade_with_fades(gba)
        play = pal_ram(r)
        r.press("start", 2)
        run_until(r, lambda: state(r) == 5, 300)              # PAUSED
        r.run(120)
        paused = pal_ram(r)
        r.press("start", 2)                                   # START again: RESUME
        run_until(r, lambda: state(r) == 1, 300)
        r.run(150)
        shots[gba] = (play, paused, pal_ram(r))
        r.stop()
    (n_play, n_paused, n_back), (b_play, b_paused, b_back) = shots[False], shots[True]
    assert b_play == lift_written(n_play), "the scene after the fade"
    assert b_back == lift_written(n_back), "after the pause's fades: the scene's colours again"
    assert b_back != n_back, "(and not the NORMAL ones)"
    assert b_paused == lift_written(n_paused), "the pause card"
    assert lift_word(0x7FFF) == 0x7FFF and lift_word(0) == 0, "white and black do not move"


# ---- goldens (new): the BRIGHT picture. Emulators show the GBC colours; a real GBA is the judge of the curve. ---------------------------------------------
@pytest.mark.parametrize("name,fn", [("bright_settings", shot_settings), ("bright_level", shot_level), ("bright_story_pic", shot_story)])
def test_bright_goldens(name, fn):
    pal, img = fn(True)

    class G:                                                # check_golden wants a Rom: a stand-in holding this picture
        model_name = "cgb"
        def golden(self, path, update=False, diff_dir=None):
            from PIL import ImageChops
            from pathlib import Path
            path = Path(path)
            if update or not path.is_file():
                path.parent.mkdir(parents=True, exist_ok=True)
                img.save(path)
                return True
            ref = Image.open(path).convert("RGB")
            return ref.size == img.size and ImageChops.difference(ref, img).getbbox() is None
    check_golden(G(), name)

