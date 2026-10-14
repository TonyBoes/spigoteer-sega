# Menu transitions keep the music ticking and the mug cursor is the mug (src/mg_list.c, jukebox.c, rush.c, title.c).
# A screen rebuilt with the LCD off is one main-loop pass of several frames and the music ticks once per pass, so
# each such rebuild calls music_pump (src/music.c) between its steps and loads the title tune's patterns in one go
# (music_load_now) instead of 384 bytes a frame. The tick is seen from outside as music_frames changing (it counts up
# while a tune plays and restarts at 0 with a new one); a frame where it stands still is a silent or late one.
import pytest
from conftest import clear_regulars, K_BONUS, K_BOSSRUSH, K_MINIGAMES, K_SOUNDTRACK, MENU_SETTLE, hold_stage_anim, menu_to, title_pick
from test_flow import LEVEL_CLEAR, TITLE, run_until, state
from test_mg import GS_MGLIST, GS_MINI, MG_RESULT
from test_mg_list import MG_PLANNED
from test_scores import booted
from test_rush import RS_LIST, RS_MENU, into_fight, on_rush

pytestmark = pytest.mark.timeout(600)

GS_JUKEBOX = 14
OBJ_MUG = 56
MAX_GAP = 1                 # frames in a row without a music tick, at most


def mug_tiles(gb, n=4):
    return bytes(gb.pb.memory[0x8000 + OBJ_MUG * 16 + i] for i in range(n * 16))


def obj_palette(gb, p):
    """OBJ palette p's 8 bytes through the CGB's palette port (None on a DMG)."""
    if gb.model_name != "cgb":
        return None
    m, out = gb.pb.memory, []
    for i in range(8):
        m[0xFF6A] = p * 8 + i
        out.append(m[0xFF6B])
    return bytes(out)


def cursor_oam(gb):
    return tuple(gb.pb.memory[0xFE00 + i] for i in range(4))


class Ticks:
    """Steps frame by frame, noting whether the music ticked (music_frames changed) in each."""
    def __init__(self, gb):
        self.gb, self.last, self.flags, self.lead = gb, gb.mem16("music_frames"), [], 0

    def run(self, n):
        for _ in range(n):
            self.gb.run(1)
            now = self.gb.mem16("music_frames")
            self.flags.append(now != self.last)
            self.last = now

    def press(self, b):
        self.gb.pb.button_press(b)
        self.run(2)
        self.gb.pb.button_release(b)
        self.run(1)

    def until(self, cond, limit=120):
        for _ in range(limit):
            if cond():
                return
            self.run(1)
        raise AssertionError("not reached")

    def worst(self, upto=None):
        """The longest run of frames without a tick (and the number of such frames in all)."""
        w = run = tot = 0
        for f in self.flags[self.lead:upto]:
            run = 0 if f else run + 1
            tot += not f
            w = max(w, run)
        return w, tot


def lcd_on(gb):
    return gb.pb.memory[0xFF40] & 0x80


def tap(gb, b):
    gb.press(b, 2)
    gb.run(1)


def to_list(gb):
    title_pick(gb, K_BONUS, K_MINIGAMES)
    run_until(gb, lambda: state(gb) == GS_MGLIST and lcd_on(gb), 30)
    gb.run(3)


def to_result(gb, game):
    """From the list: play game `game` (its line), jump to its result window."""
    for _ in range(game):
        tap(gb, "down")
    gb.run(2)
    tap(gb, "a")
    run_until(gb, lambda: state(gb) == GS_MINI and lcd_on(gb), 40)
    gb.run(70)                                    # (its pictures are loaded; the intro runs)
    gb.write("mg_phase", MG_RESULT)
    run_until(gb, lambda: gb.mem("overlay_on") == 1, 120)
    gb.run(40)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("game", range(MG_PLANNED))
def test_the_list_cursor_is_the_mug_after_every_game(model, game):
    """After a game and B on its result the list's cursor is the mug: its sprite entry (tile 56, the mug's palette) and the
    pictures behind it (OBJ tiles 56.., OBJ palettes 1-2) are what the list showed the first time."""
    with booted(model) as gb:
        hold_stage_anim(gb)
        to_list(gb)
        tiles0, pal1, pal2, oam0 = mug_tiles(gb), obj_palette(gb, 1), obj_palette(gb, 2), cursor_oam(gb)
        assert oam0[2] == OBJ_MUG
        to_result(gb, game)
        gb.press("b", 2)
        run_until(gb, lambda: state(gb) == GS_MGLIST and lcd_on(gb), 60)
        gb.run(3)
        o = cursor_oam(gb)
        assert o[2] == OBJ_MUG and o[3] == oam0[3], o
        assert mug_tiles(gb) == tiles0, "the mug's pictures"
        assert obj_palette(gb, 1) == pal1 and obj_palette(gb, 2) == pal2, "the mug's palettes"


def transitions(gb):
    """Every menu transition once, from the title's top level with the title tune playing: [(name, Ticks, cut)]. `cut`: the
    frame count from which on the silence is by design (the soundtrack player stops the music), or None."""
    out = []

    def leg(name, act, end, tail=6, cut_at_end=False, lead=0):
        t = Ticks(gb)
        t.lead = lead
        act(t)
        t.until(end)
        if cut_at_end:
            cut = len(t.flags)
        t.run(tail)
        out.append((name, t, cut if cut_at_end else None))

    title_pick(gb, K_BONUS)
    gb.run(MENU_SETTLE)
    menu_to(gb, K_MINIGAMES)
    gb.run(30)
    leg("title -> MINI GAMES", lambda t: t.press("a"), lambda: state(gb) == GS_MGLIST and lcd_on(gb))
    gb.run(10)
    leg("MINI GAMES -> title", lambda t: t.press("b"), lambda: state(gb) == TITLE and lcd_on(gb))
    gb.run(MENU_SETTLE + 20)
    menu_to(gb, K_SOUNDTRACK)
    leg("title -> SOUNDTRACK", lambda t: t.press("a"), lambda: state(gb) == GS_JUKEBOX and lcd_on(gb), 0, True)
    gb.run(20)
    leg("SOUNDTRACK -> title", lambda t: t.press("b"), lambda: state(gb) == TITLE and lcd_on(gb), 10,
        lead=3)                                           # (the player was silent: the frames of the press are not the title's)
    gb.run(MENU_SETTLE + 20)
    menu_to(gb, K_BOSSRUSH)
    leg("title -> BOSS RUSH", lambda t: t.press("a"), lambda: on_rush(gb, RS_MENU))
    gb.run(20)
    tap(gb, "down")
    leg("BOSS RUSH menu -> list", lambda t: t.press("a"), lambda: on_rush(gb, RS_LIST))
    gb.run(20)
    leg("BOSS RUSH list -> menu", lambda t: t.press("b"), lambda: on_rush(gb, RS_MENU))
    gb.run(20)
    leg("BOSS RUSH menu -> title", lambda t: t.press("b"), lambda: state(gb) == TITLE and lcd_on(gb))
    gb.run(MENU_SETTLE + 20)
    return out


def after_a_game(gb, game):
    """MINI GAMES list: play `game`, B on its result: [(name, Ticks, None)] for the way back."""
    to_list(gb)
    to_result(gb, game)
    t = Ticks(gb)
    t.press("b")
    t.until(lambda: state(gb) == GS_MGLIST and lcd_on(gb))
    t.run(6)
    return [(f"game {game} -> MINI GAMES", t, None)]


def after_a_fight(gb):
    """BOSS RUSH list: CHOOSE the first boss, win: [(name, Ticks, None)] from his outro to the result screen."""
    title_pick(gb, K_BONUS, K_BOSSRUSH)
    run_until(gb, lambda: on_rush(gb, RS_MENU), 30)
    gb.run(3)
    tap(gb, "down")
    tap(gb, "a")
    run_until(gb, lambda: on_rush(gb, RS_LIST), 30)
    gb.run(3)
    tap(gb, "a")
    into_fight(gb)
    gb.write("boss_hook", 3)
    clear_regulars(gb)
    run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 300)
    run_until(gb, lambda: not lcd_on(gb), 400)           # (the result's screen is being built: the outro's own silence is not this)
    t = Ticks(gb)
    t.until(lambda: on_rush(gb, 3), 100)                 # RS_RESULT
    t.run(6)
    return [("boss fight -> BOSS RUSH result", t, None)]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_menu_transitions_keep_the_music_ticking(model):
    """On every transition between the title, BONUS > MINI GAMES, the SOUNDTRACK and BOSS RUSH (menu and list), and the way
    back from a game and from a boss fight, at most MAX_GAP frames in a row pass without a music tick."""
    bad = []
    with booted(model) as gb:
        hold_stage_anim(gb)
        gb.run(240)
        runs = transitions(gb)
    for g in (0, 6):
        with booted(model) as gb:
            hold_stage_anim(gb)
            runs += after_a_game(gb, g)
    with booted(model) as gb:
        hold_stage_anim(gb)
        runs += after_a_fight(gb)
    for name, t, cut in runs:
        w, tot = t.worst(cut)
        if w > MAX_GAP:
            bad.append(f"{name}: {w} in a row, {tot} in all: " + "".join("T" if f else "." for f in t.flags))
    assert not bad, "\n".join(bad)
