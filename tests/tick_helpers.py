# Real-time stamps of the music's ticks, shared by the timing tests (test_music_transitions, test_menu_music, test_pause).
# The driver steps once per tick (hUGE_dosound); a hook on it stamps every call with the emulator's T-cycle count. A test that
# counts ticks per emulator frame (or asks "did music_frames change this frame") measures the phase between the game's frame
# and PyBoy's frame boundary, which any change of code size or timing moves; the stamps measure the tune itself:
#   - a stall (a tick that came late: the tune audibly hitches) is an interval over LATE frames between two ticks;
#   - a bunch (a tick pump and the loop's own on one frame) is an interval under EARLY frames.
# One frame is one tick, so a missed tick is an interval of ~2 frames and a doubled one ~0 to 0.5: LATE and EARLY sit between.
import os
import re

from conftest import ROM

FRAME = 70224 * (2 if os.environ.get("GB_DOUBLE_SPEED") else 1)    # T-cycles in a frame (the emulator's count doubles in Color double speed: GB_DOUBLE_SPEED=1 pytest -k cgb; a DMG run of such a session is not meaningful)
LATE, EARLY = 1.6, 0.3       # a tick interval over / under this many frames is a hitch / a bunched tick


def sym_at(name):
    """(bank, address) of a symbol (build/game.noi: bank << 16 | address)."""
    v = int(re.search(r"DEF %s (0x[0-9A-F]+)" % name, ROM.with_suffix(".noi").read_text()).group(1), 16)
    return v >> 16, v & 0xFFFF


def tick_at():
    """(bank, address) of hUGE_dosound, called once per music tick."""
    return sym_at("_hUGE_dosound")


def tick_log(gb):
    """The T-cycle stamp of every music tick from now on (a hook on the driver's step), attached once to a rom."""
    if not hasattr(gb, "tick_stamps"):
        gb.tick_stamps = []
        gb.pb.hook_register(*tick_at(), lambda ctx: gb.tick_stamps.append(gb.pb._cycles()), None)
    return gb.tick_stamps


def load_log(gb):
    """The T-cycle stamp of every call of music_load_now (a screen's rebuild copying the new tune's patterns in one go)."""
    if not hasattr(gb, "load_stamps"):
        gb.load_stamps = []
        gb.pb.hook_register(*sym_at("_music_load_now"), lambda ctx: gb.load_stamps.append(gb.pb._cycles()), None)
    return gb.load_stamps


LOAD_MAX = 1.5               # music_load_now to the new tune's first tick: the copy takes ~0.9 frame (four pattern blocks and the driver's init); over this the load grew
