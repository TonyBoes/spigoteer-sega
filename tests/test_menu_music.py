# Menu transitions keep the music ticking, and the one-line lists come back clean from a game (src/mg_list.c, jukebox.c, rush.c, title.c).
# A screen rebuilt with the LCD off is one main-loop pass of several frames and the music ticks once per pass, so
# each such rebuild calls music_pump (src/music.c) between its steps and loads the title tune's patterns in one go
# (music_load_now) instead of 384 bytes a frame. The tick is seen from outside as music_frames changing (it counts up
# while a tune plays and restarts at 0 with a new one); a frame where it stands still is a silent or late one.
import os

import pytest
from conftest import clear_regulars, K_BONUS, K_BOSSRUSH, K_MINIGAMES, K_SOUNDTRACK, MENU_SETTLE, hold_stage_anim, menu_to, title_pick
from test_flow import LEVEL_CLEAR, TITLE, run_until, state
from test_mg import GS_MGLIST, GS_MINI, MG_RESULT
import ol_helpers as oh
import test_mg_list as ml
from test_mg_list import MG_PLANNED
from test_scores import booted
from test_rush import RS_LIST, RS_MENU, into_fight, on_rush
from tick_helpers import FRAME, LATE, LOAD_MAX, load_log, tick_log

pytestmark = pytest.mark.timeout(600)

GS_JUKEBOX = 14
OBJ_MUG = 56


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
    """Steps frame by frame noting the emulator's cycle count at each frame's end and the tune playing; the ticks' stamps come from
    the hook (tick_helpers)."""
    def __init__(self, gb):
        self.gb, self.stamps, self.loads, self.lead = gb, tick_log(gb), load_log(gb), 0
        self.n_loads = len(self.loads)
        self.cyc = [gb.pb._cycles()]
        self.tunes = [gb.mem("cur_tune")]
        self.mf = [gb.mem16("music_frames")]

    def run(self, n):
        for _ in range(n):
            self.gb.run(1)
            self.cyc.append(self.gb.pb._cycles())
            self.tunes.append(self.gb.mem("cur_tune"))
            self.mf.append(self.gb.mem16("music_frames"))

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

    def frame_of_last_tick(self):
        """The index of the frame the leg's last tick fell in (its end's index in `cyc`)."""
        last = max(x for x in self.stamps if x <= self.cyc[-1])
        return next(i for i, c in enumerate(self.cyc) if c >= last)

    def worst(self, upto=None):
        """(the longest time in frames between two ticks of one tune, the longest time from a music_load_now to the next tick or None,
        the ticks) from frame `lead` to frame `upto` of the leg (the end when None). The stretch to the window's end counts too, unless
        `upto` cuts it (the music is stopped there by design); a window without two ticks is one long gap. Where a tune is replaced
        by another the cut is only known to the frame it was seen in: the ticks of the old tune and of the new one are judged apart,
        and the hole between them is the load, which has its own bound (the new tune's patterns are copied in one go before it starts)."""
        end = upto if upto is not None else len(self.cyc) - 1
        lo, hi = self.cyc[self.lead], self.cyc[end]
        st = [x for x in self.stamps if lo <= x <= hi]
        cuts = [i for i in range(self.lead, end) if self.tunes[i + 1] != self.tunes[i] or self.mf[i + 1] < self.mf[i]]
        parts = [st]
        if cuts:
            a, b = self.cyc[cuts[0]], self.cyc[cuts[-1] + 1]
            parts = [[x for x in st if x < a], [x for x in st if x >= b]]
        gaps = []
        for p in parts:
            gaps += [(y - x) / FRAME for x, y in zip(p, p[1:])]
        if upto is None and parts[-1]:
            gaps.append((hi - parts[-1][-1]) / FRAME)
        elif not st:
            gaps.append((hi - lo) / FRAME)
        holes = [((next((x for x in st if x > e), hi)) - e) / FRAME for e in self.loads[self.n_loads:] if lo <= e <= hi]
        return max(gaps, default=0), max(holes, default=None), len(st)


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
    """From the list: play game `game` (selected with RIGHT), jump to its result window."""
    for _ in range(game):
        tap(gb, "right")
    gb.run(2)
    tap(gb, "a")
    run_until(gb, lambda: state(gb) == GS_MINI and lcd_on(gb), 40)
    gb.run(70)                                    # (its pictures are loaded; the intro runs)
    gb.write("mg_phase", MG_RESULT)
    run_until(gb, lambda: gb.mem("overlay_on") == 1, 120)
    gb.run(40)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("game", range(MG_PLANNED))
def test_the_list_is_clean_after_every_game(model, game):
    """After a game and B on its result the list is what it was: the one-line screen on that game with no sprite left over (the games borrow the
    sprite tiles and palettes the old list's mug cursor used) and the same band, counter and hint."""
    with booted(model) as gb:
        hold_stage_anim(gb)
        to_list(gb)
        assert not gb.visible_sprites()
        to_result(gb, game)
        gb.press("b", 2)
        run_until(gb, lambda: state(gb) == GS_MGLIST and lcd_on(gb), 60)
        gb.run(8)
        assert gb.mem("ml_sel") == game and not gb.visible_sprites()
        assert oh.selection(gb) == ml.NAMES[game] and ml.counter(gb) == f"{game + 1} / 14"
        assert oh.hint(gb) == "@ PLAY   $ BACK" and oh.band_rows_ok(gb)


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
            cut = t.frame_of_last_tick()    # (the player stops the music, then its screen comes up: the stretch after the last tick is silent by design)
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
    back from a game and from a boss fight, no two music ticks are more than LATE frames apart."""
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
        w, hole, tot = t.worst(cut)
        if os.environ.get("MUSIC_REPORT"):
            print(f"{model} {name:34s} longest gap {w:5.2f} frames, load to first tick {hole}, {tot} ticks")
        if w > LATE:
            bad.append(f"{name}: {w:.2f} frames between two ticks ({tot} ticks in the window)")
        if hole is not None and hole > LOAD_MAX:
            bad.append(f"{name}: {hole:.2f} frames from music_load_now to the new tune's first tick")
    assert not bad, "\n".join(bad)
