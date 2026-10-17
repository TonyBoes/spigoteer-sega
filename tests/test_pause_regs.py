# The window registers after a note is cut off (owner 2026-10-17, SameBoy iOS: the pause menu and a mini-game's result card "float to the top of the screen"
# with the debug menu's text in the rows below their band). A note (show_note: WY 24, LYC 31, overlay_on 2) ended by anything but end_note (a life lost, a
# scene change: overlay_on = 0) left WY and LYC on the note. main.c update() puts them back, and the pause menu is the band at WY 64 again.
import pytest

from test_flow import state
from test_pause import MODES, PAUSED, rom_s, start_classic, tap

pytestmark = pytest.mark.timeout(600)

WY, MENU_LYC, PLAY_LYC = 64, 110, 86
STAT, LYC, LCDC, WYR, WXR, IE = 0xFF41, 0xFF45, 0xFF40, 0xFF4A, 0xFF4B, 0xFFFF


def regs_ok(gb, paused):
    m = gb.pb.memory
    assert m[STAT] & 0x40, "STAT: the LYC interrupt is enabled"
    assert m[IE] & 3 == 3, "IE: VBlank and LCD STAT"
    assert m[WXR] == 7 and m[WYR] == WY, (m[WXR], m[WYR])
    assert m[LYC] == (MENU_LYC if paused else PLAY_LYC), m[LYC]
    assert m[LCDC] & 0x80 and m[LCDC] & 0x40, hex(m[LCDC])


@pytest.mark.parametrize("model", MODES)
def test_the_window_registers_after_a_note_is_cut_off(model):
    with rom_s(model) as gb:
        start_classic(gb)
        gb.pb.memory[WYR] = 24
        gb.pb.memory[LYC] = 31
        gb.write("overlay_on", 0)
        gb.run(3)
        regs_ok(gb, False)
        tap(gb, "start", 3)
        assert state(gb) == PAUSED
        gb.run(20)
        regs_ok(gb, True)
