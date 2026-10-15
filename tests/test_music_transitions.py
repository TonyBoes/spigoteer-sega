# Every screen transition keeps the tune in time (src/music.c, owner 2026-10-15: "some music stuttering when entering or backing out of menus").
# The music engine ticks once per frame: music_tick in the main loop, music_pump inside the long LCD-off loads. A hook on the driver's
# step (hUGE_dosound, called once per tick) stamps every tick with the emulator's cycle count, so the test sees real time, not the
# frame boundaries: a tick interval over LATE frames is a hitch (the tune stalled), one under EARLY a bunched tick (a pump tick and the
# loop's own), and cur_tune changing or music_frames falling is a restart. Each leg below (one screen change, from the key press to a few
# frames after the new screen is up) asserts:
#   - every interval between ticks is within [EARLY, LATE] frames, the leg's edges included (no tick at all counts as one long gap);
#   - no restart on the legs where the tune is supposed to carry on (the title's submenus, the practice list, the table screens).
# MUSIC_REPORT=1 pytest -s tests/test_music_transitions.py prints the table of every leg.
import os
import re

import pytest
from conftest import ROM, K_ARCADE, K_BONUS, K_BOSSRUSH, K_MINIGAMES, K_PLAY, K_SETTINGS, K_SOUNDTRACK, K_STORY, MENU_SETTLE, hold_stage_anim, \
    menu_to, title_pick
from test_flow import GS_INITIALS, GS_SCORES, PLAYING, TITLE, run_until, state
from test_mg import GS_MGLIST, GS_MINI
from test_menu_music import GS_JUKEBOX, lcd_on, tap, to_list
from test_pause import PAUSED, open_pause
from test_rush import RS_LIST, RS_MENU, on_rush
from test_scores import game_over_with, idle_title
from test_sound import make_rom

pytestmark = pytest.mark.timeout(900)

REPORT = bool(os.environ.get("MUSIC_REPORT"))
MG_CARD = 5
FRAME = 70224                # T-cycles in a frame
LATE, EARLY = 1.6, 0.3       # a tick interval over / under this many frames is a hitch / a bunched tick (one frame is a tick a frame; before the fix up to 35)


def tick_at():
    """(bank, address) of hUGE_dosound, called once per music tick (build/game.noi: bank << 16 | address)."""
    v = int(re.search(r"DEF _hUGE_dosound (0x[0-9A-F]+)", ROM.with_suffix(".noi").read_text()).group(1), 16)
    return v >> 16, v & 0xFFFF


def tick_log(gb):
    """The T-cycle stamp of every music tick from now on (a hook on the driver's step), attached once to a rom."""
    if not hasattr(gb, "tick_stamps"):
        gb.tick_stamps = []
        gb.pb.hook_register(*tick_at(), lambda ctx: gb.tick_stamps.append(gb.pb._cycles()), None)
    return gb.tick_stamps


class Leg:
    """Steps frame by frame from creation, noting for each the tune playing and the cycle stamps of the music's ticks."""
    def __init__(self, gb, name, cont=True, silent_ok=False, mute_after=False):
        self.gb, self.name, self.cont, self.silent_ok, self.mute_after = gb, name, cont, silent_ok, mute_after
        self.stamps = tick_log(gb)
        self.n0 = self.n1 = len(self.stamps)
        self.c0 = self.c1 = gb.pb._cycles()
        self.cyc = [self.c0]
        self.tunes = [gb.mem("cur_tune")]
        self.mf = [gb.mem16("music_frames")]

    def run(self, n):
        for _ in range(n):
            self.gb.run(1)
            self.tunes.append(self.gb.mem("cur_tune"))
            self.mf.append(self.gb.mem16("music_frames"))
            self.c1 = self.gb.pb._cycles()
            self.cyc.append(self.c1)
            self.n1 = len(self.stamps)

    def press(self, b):
        self.gb.pb.button_press(b)
        self.run(2)
        self.gb.pb.button_release(b)
        self.run(1)

    def until(self, cond, limit=200):
        for _ in range(limit):
            if cond():
                return
            self.run(1)
        raise AssertionError(f"{self.name}: not reached")

    def intervals(self):
        """The frames between consecutive ticks over the leg (the last tick before it counts as the first one); the stretch
        after the last tick to the leg's end is included when it is already a hitch. A leg where the tune is replaced (not
        `cont`) is judged in two parts, the old tune up to the frame it was cut in and the new one from the frame it was
        started in: the silence between them is by design."""
        st = self.stamps[max(self.n0 - 1, 0):self.n1]
        if st and self.n0 and st[0] < self.c0 and self.c0 - st[0] > 2 * FRAME:
            st = st[1:]                                       # (the tune was not playing when the leg began)
        cuts = [i for i, (t0, t1, m0, m1) in enumerate(zip(self.tunes, self.tunes[1:], self.mf, self.mf[1:])) if t1 != t0 or m1 < m0]
        parts = [(st, self.c1)]
        if cuts and not self.cont:
            lo, hi = self.cyc[cuts[0]], self.cyc[cuts[-1] + 1]
            parts = [([x for x in st if x < lo], lo), ([x for x in st if x >= hi], self.c1)]
        out = []
        for i, (ticks, end) in enumerate(parts):
            out += [(b - a) / FRAME for a, b in zip(ticks, ticks[1:])]
            if len(parts) == 2 and i == 1 and not ticks:
                if not self.mute_after:                       # (the new tune never ticked in the leg)
                    out.append((end - hi) / FRAME)
                continue
            if len(parts) == 2 and i == 0 and not ticks:
                continue                                      # (no old tune was playing)
            tail = (end - (ticks[-1] if ticks else self.c0)) / FRAME
            if tail > LATE:
                out.append(tail)                              # (a tick not yet due at the leg's end is not late)
        return out

    def restarts(self):
        return sum(t1 != t0 or m1 < m0 for t0, t1, m0, m1 in zip(self.tunes, self.tunes[1:], self.mf, self.mf[1:]))

    def stats(self):
        """(the longest interval between ticks in frames, the shortest, the restarts)."""
        iv = self.intervals()
        return max(iv, default=0), min(iv, default=1), self.restarts()


def check(legs):
    bad = []
    for l in legs:
        late, early, rst = l.stats()
        if REPORT:
            print(f"{l.name:46s} longest {late:5.2f}  shortest {early:5.2f}  restarts {rst}  {'(carries on)' if l.cont else ''}")
        if l.silent_ok:
            continue
        if late > LATE or early < EARLY or (l.cont and rst):
            bad.append(f"{l.name}: longest {late:.2f} frames, shortest {early:.2f}, restarts {rst}")
    assert not bad, "\n".join(bad)


def leg(gb, legs, name, act, end, tail=6, cont=True, silent_ok=False, mute_after=False):
    l = Leg(gb, name, cont, silent_ok, mute_after)
    act(l)
    l.until(end)
    l.run(tail)
    legs.append(l)
    return l


def on_title(gb):
    return state(gb) == TITLE and lcd_on(gb)


def title_legs(gb, legs):
    """The title's menus: PLAY, BONUS, SETTINGS in and out, the table screen the idle title shows."""
    gb.run(240)
    for top, name, kind in ((K_PLAY, "PLAY", None), (K_BONUS, "BONUS", None), (K_SETTINGS, "SETTINGS", None)):
        menu_to(gb, top)
        gb.run(MENU_SETTLE)
        l = Leg(gb, f"title -> {name}")
        l.press("a")
        l.run(MENU_SETTLE + 20)
        legs.append(l)
        l = Leg(gb, f"{name} -> title")
        l.press("b")
        l.run(MENU_SETTLE + 20)
        legs.append(l)
    menu_to(gb, K_SETTINGS)
    gb.press("a", 2)
    gb.run(MENU_SETTLE + 10)
    for k in (0, 1):                                                         # MUSIC off, then on: the tune stops, then starts from its top
        l = Leg(gb, "SETTINGS MUSIC " + ("off" if k == 0 else "on"), cont=False, silent_ok=True)
        l.press("a")
        l.run(30)
        legs.append(l)
    tap(gb, "b")
    gb.run(MENU_SETTLE + 20)


def table_legs(gb, legs):
    idle_title(gb)
    leg(gb, legs, "title -> scores (idle)", lambda l: l.run(1), lambda: state(gb) == GS_SCORES and lcd_on(gb), cont=True)
    gb.run(10)
    leg(gb, legs, "scores -> title (A)", lambda l: l.press("a"), lambda: on_title(gb))


def minilist_legs(gb, legs):
    leg(gb, legs, "title -> MINI GAMES", lambda l: l.press("a"), lambda: state(gb) == GS_MGLIST and lcd_on(gb))
    gb.run(10)
    leg(gb, legs, "MINI GAMES -> title", lambda l: l.press("b"), lambda: on_title(gb))
    gb.run(MENU_SETTLE + 20)


def soundtrack_legs(gb, legs):
    menu_to(gb, K_SOUNDTRACK)
    leg(gb, legs, "title -> SOUNDTRACK", lambda l: l.press("a"), lambda: state(gb) == GS_JUKEBOX and lcd_on(gb), 0, cont=False, mute_after=True)
    gb.run(20)
    leg(gb, legs, "SOUNDTRACK -> title", lambda l: l.press("b"), lambda: on_title(gb), 10, cont=False)
    gb.run(MENU_SETTLE + 20)


def rush_legs(gb, legs):
    menu_to(gb, K_BOSSRUSH)
    leg(gb, legs, "title -> BOSS RUSH", lambda l: l.press("a"), lambda: on_rush(gb, RS_MENU))
    gb.run(20)
    tap(gb, "down")
    leg(gb, legs, "BOSS RUSH menu -> list", lambda l: l.press("a"), lambda: on_rush(gb, RS_LIST))
    gb.run(20)
    leg(gb, legs, "BOSS RUSH list -> menu", lambda l: l.press("b"), lambda: on_rush(gb, RS_MENU))
    gb.run(20)
    leg(gb, legs, "BOSS RUSH menu -> title", lambda l: l.press("b"), lambda: on_title(gb))
    gb.run(MENU_SETTLE + 20)


def list_legs(gb, legs):
    """The practice list: game -> card -> list, and game -> result -> list (a fresh cartridge: the first card is the full one)."""
    to_list(gb)
    gb.run(10)
    leg(gb, legs, "list -> card", lambda l: l.press("a"), lambda: state(gb) == GS_MINI and gb.mem("mg_phase") == MG_CARD and lcd_on(gb),
        cont=False)
    gb.run(10)
    leg(gb, legs, "card -> list (B)", lambda l: l.press("b"), lambda: state(gb) == GS_MGLIST and lcd_on(gb), cont=False)
    gb.run(10)
    tap(gb, "a")
    run_until(gb, lambda: state(gb) == GS_MINI and lcd_on(gb), 40)
    gb.run(5)
    leg(gb, legs, "card -> game (A)", lambda l: l.press("a"), lambda: state(gb) == GS_MINI and gb.mem("mg_phase") != MG_CARD and lcd_on(gb),
        cont=False)


def game_legs(gb, legs, game):
    to_list(gb)
    gb.run(10)
    for _ in range(game):
        tap(gb, "down")
    gb.run(2)
    leg(gb, legs, f"list -> game {game}", lambda l: l.press("a"), lambda: state(gb) == GS_MINI and lcd_on(gb), cont=False)
    gb.run(70)
    gb.write("mg_phase", 4)
    run_until(gb, lambda: gb.mem("overlay_on") == 1, 120)
    gb.run(40)
    leg(gb, legs, f"game {game} result -> list", lambda l: l.press("b"), lambda: state(gb) == GS_MGLIST and lcd_on(gb), cont=False)


def pause_legs(gb, legs):
    """ARCADE from the title, pause and resume, QUIT TO MENU to the title; the same from a mini-game to the list."""
    title_pick(gb, K_PLAY, K_ARCADE, press=False)
    leg(gb, legs, "title -> ARCADE (goal banner)", lambda l: l.press("a"), lambda: state(gb) == 12 and lcd_on(gb), 10, cont=False)
    gb.write("tip_chance", 0)
    leg(gb, legs, "ARCADE goal banner -> play", lambda l: l.press("a"), lambda: state(gb) == PLAYING, 10, cont=False)
    gb.run(120)
    leg(gb, legs, "pause open", lambda l: l.press("start"), lambda: state(gb) == PAUSED, 6)
    gb.run(30)
    leg(gb, legs, "pause resume", lambda l: l.press("start"), lambda: state(gb) == PLAYING, 6)
    gb.run(30)
    open_pause(gb)
    gb.run(10)
    def quit_(l):
        for _ in range(1):
            l.press("down")
        l.press("a")
        l.press("up")
        l.press("a")
    leg(gb, legs, "pause QUIT -> title", quit_, lambda: on_title(gb), 6, cont=False)


def quit_list_legs(gb, legs):
    to_list(gb)
    gb.run(10)
    tap(gb, "a")
    run_until(gb, lambda: state(gb) == GS_MINI and lcd_on(gb), 40)
    gb.run(90)
    tap(gb, "start")
    assert state(gb) == PAUSED
    gb.run(10)
    def quit_(l):
        for _ in range(2):
            l.press("down")
        l.press("a")
        l.press("up")
        l.press("a")
    leg(gb, legs, "mini-game pause QUIT -> list", quit_, lambda: state(gb) == GS_MGLIST and lcd_on(gb), 6, cont=False)


def gameover_legs(gb, legs):
    """A game over with a top-5 score: GAME OVER -> initials -> table -> title; one with none: -> table -> title."""
    game_over_with(gb, 50)
    leg(gb, legs, "GAME OVER -> initials (START)", lambda l: l.press("start"), lambda: state(gb) == GS_INITIALS and lcd_on(gb), 6, cont=False)
    gb.run(20)
    leg(gb, legs, "initials -> table (START)", lambda l: l.press("start"), lambda: state(gb) == GS_SCORES and lcd_on(gb), 6, cont=False)
    gb.run(20)
    leg(gb, legs, "table -> title (A)", lambda l: l.press("a"), lambda: on_title(gb), 6, cont=False)


def story_legs(gb, legs):
    title_pick(gb, K_PLAY, K_STORY, press=False)
    leg(gb, legs, "title -> STORY (first scene)", lambda l: l.press("a"), lambda: state(gb) != TITLE and lcd_on(gb), 20, cont=False)


def bonus_to(f):
    """The BONUS submenu with its cursor on the item the scenario f starts from."""
    def go(gb, legs):
        gb.run(40)
        title_pick(gb, K_BONUS)
        gb.run(MENU_SETTLE)
        menu_to(gb, {minilist_legs: K_MINIGAMES, soundtrack_legs: K_SOUNDTRACK, rush_legs: K_BOSSRUSH}[f])
        gb.run(30)
        f(gb, legs)
    return go


SCENARIOS = {"title": [title_legs], "table": [table_legs], "minilist": [bonus_to(minilist_legs)],
             "soundtrack": [bonus_to(soundtrack_legs)], "rush": [bonus_to(rush_legs)], "card": [list_legs], "game0": [lambda g, l: game_legs(g, l, 0)],
             "game6": [lambda g, l: game_legs(g, l, 6)], "pause": [pause_legs], "quitlist": [quit_list_legs], "over": [gameover_legs],
             "story": [story_legs]}


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("scenario", list(SCENARIOS))
def test_transitions_keep_the_tune_in_time(model, scenario):
    legs = []
    with make_rom(model, None, sound=True, cards=(scenario != "card")) as gb:
        gb.run(120)
        hold_stage_anim(gb)
        if scenario not in ("title",):
            gb.run(240)
        for f in SCENARIOS[scenario]:
            f(gb, legs)
    if REPORT:
        print(f"== {model} {scenario}")
    check(legs)
