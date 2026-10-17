# The quick palette fade for menu screen changes (src/trans.c trans_menu, TR_FAST; owner 2026-10-17: "I want to use quick palette fade
# transition for menu flashes too"). Transitions are on here (conftest turns them off for every other test).
#   - each changed menu transition runs the fade (TR_PEND seen, the LCD off in the white, TRANS clear after, NR50 back at full);
#   - the fade is the quick one (the whole change takes well under the scene fade's frames);
#   - the screen it comes up with is the screen the plain cut shows;
#   - the tune keeps its tick (no gap over LATE frames) through the menu scenarios of test_music_transitions with the fade on.
import pytest
from PIL import Image

from conftest import K_BONUS, K_BOSSRUSH, K_MINIGAMES, K_SOUNDTRACK, MENU_SETTLE, TRANS_ADDR, hold_stage_anim, menu_to, release_gesture, \
    gesture, title_pick, trans_enable, with_unlock
from test_flow import GS_INITIALS, GS_SCORES, TITLE, run_until, state
from test_mg import GS_MGLIST, GS_MINI
from test_menu_music import GS_JUKEBOX, lcd_on, tap
from test_music_transitions import Leg, check
from test_rush import RS_LIST, RS_MENU, on_rush
from test_scores import idle_title
from test_sound import make_rom

pytestmark = pytest.mark.timeout(900)

TR_PEND, TR_FAST = 2, 0x10
MAX_FRAMES = 90                      # press to settled: the scene fade is 2 x ~30 frames plus the build; the quick one is about 16 + 16 + the build


def boot(model, ram=None, on=True):
    gb = make_rom(model, ram, sound=True)
    gb.run(120)
    hold_stage_anim(gb)
    gb.run(240)
    trans_enable(gb, on)
    return gb


def fade_trace(gb, press, ready, limit=MAX_FRAMES):
    """Press `press`, then frame by frame until `ready` holds and the fade is over; what the frames showed."""
    seen = {"pend": False, "off": False, "fast": False, "n": 0, "vol0": False}
    gb.pb.button_press(press)
    for i in range(limit):
        gb.run(1)
        if i == 1:
            gb.pb.button_release(press)
        m = gb.pb.memory
        seen["n"] = i + 1
        seen["pend"] |= bool(m[TRANS_ADDR] & TR_PEND)
        seen["fast"] |= bool(m[TRANS_ADDR] & TR_FAST)
        seen["off"] |= not m[0xFF40] & 0x80
        seen["vol0"] |= m[0xFF24] == 0
        if i > 3 and ready() and not m[TRANS_ADDR] & 0x1F and m[0xFF40] & 0x80:
            break
    else:
        raise AssertionError("never settled")
    return seen


def check_fade(seen):
    assert seen["pend"] and seen["off"] and seen["fast"], seen
    assert seen["n"] <= MAX_FRAMES, seen


def settle_image(gb, press, ready):
    gb.press(press, 2)
    run_until(gb, lambda: ready() and not gb.pb.memory[TRANS_ADDR] & 0x1F and lcd_on(gb), MAX_FRAMES)
    gb.run(30)
    return gb.image().tobytes()


def to_bonus_item(gb, k):
    title_pick(gb, K_BONUS)
    gb.run(MENU_SETTLE)
    menu_to(gb, k)
    gb.run(MENU_SETTLE)


FLOWS = {}


def flow(f):
    FLOWS[f.__name__] = f
    return f


@flow
def minilist(gb):                                # title BONUS -> MINI GAMES, then B back
    to_bonus_item(gb, K_MINIGAMES)
    return [("a", lambda: state(gb) == GS_MGLIST), ("b", lambda: state(gb) == TITLE and gb.mem("title_menu") == 2)]


@flow
def soundtrack(gb):
    to_bonus_item(gb, K_SOUNDTRACK)
    return [("a", lambda: state(gb) == GS_JUKEBOX), ("b", lambda: state(gb) == TITLE and gb.mem("title_menu") == 2)]


@flow
def rush(gb):                                    # title -> the menu -> the list -> the menu -> the title
    to_bonus_item(gb, K_BOSSRUSH)
    return [("a", lambda: on_rush(gb, RS_MENU)), ("down", None), ("a", lambda: on_rush(gb, RS_LIST)), ("b", lambda: on_rush(gb, RS_MENU)),
            ("b", lambda: state(gb) == TITLE and gb.mem("title_menu") == 2)]


@flow
def practice(gb):                                # the list -> game 0, its result window (jumped to), B back to the list
    def result():
        gb.run(70)
        gb.write("mg_phase", 4)
        run_until(gb, lambda: gb.mem("overlay_on") == 1, 120)
        gb.run(40)
    title_pick(gb, K_BONUS, K_MINIGAMES)
    run_until(gb, lambda: state(gb) == GS_MGLIST and lcd_on(gb), MAX_FRAMES)
    return [("a", lambda: state(gb) == GS_MINI), (result, None), ("b", lambda: state(gb) == GS_MGLIST)]


@flow
def scores(gb):                                  # the idle title -> the top 5 -> A back
    idle_title(gb)
    return [("a", None)]


def run_flow(model, name, on):
    gb = boot(model, None, on)
    steps = FLOWS[name](gb)
    out = []
    if name == "scores":
        gb.run(2)
        run_until(gb, lambda: state(gb) == GS_SCORES and lcd_on(gb) and not gb.pb.memory[TRANS_ADDR] & 0x1F, 200)
        gb.run(30)
        out.append((gb.image().tobytes(), False))
        gb.press("a", 2)
        run_until(gb, lambda: state(gb) == TITLE and lcd_on(gb) and not gb.pb.memory[TRANS_ADDR] & 0x1F, 200)
        gb.run(30)
        out.append((gb.image().tobytes(), True))
        gb.pb.stop(save=False)
        return out
    for b, ready in steps:
        run_until(gb, lambda: not gb.pb.memory[TRANS_ADDR] & 0x1F and lcd_on(gb), MAX_FRAMES)   # (a press during the last fade's reveal is not read)
        gb.run(3)
        if ready is None:
            b() if callable(b) else tap(gb, b)
            continue
        if on:
            seen = fade_trace(gb, b, ready)
            check_fade(seen)
            assert gb.pb.memory[0xFF24] == 0x77, "the volume is back"
        else:
            gb.press(b, 2)
            run_until(gb, lambda: ready() and lcd_on(gb), 60)
        gb.run(30)
        out.append((gb.image().tobytes(), state(gb) == TITLE))
    gb.pb.stop(save=False)
    return out


@pytest.mark.parametrize("name", [n for n in FLOWS if n != "scores"])
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_menu_screen_changes_fade_and_land_on_the_cut_picture(model, name):
    a = run_flow(model, name, True)
    b = run_flow(model, name, False)
    assert len(a) == len(b)
    for i, ((x, title), (y, _)) in enumerate(zip(a, b)):
        if title:                                # (the title's logo and bubbles run on the frame count: the colours must be the same)
            assert set(Image.frombytes("RGB", (160, 144), x).getdata()) == set(Image.frombytes("RGB", (160, 144), y).getdata()), (name, "colours", i)
        else:
            assert x == y, (name, "step", i)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_scores_screen_fades_in_and_out(model):
    a = run_flow(model, "scores", True)
    b = run_flow(model, "scores", False)
    assert a[0] == b[0]
    assert set(Image.frombytes("RGB", (160, 144), a[1][0]).getdata()) == set(Image.frombytes("RGB", (160, 144), b[1][0]).getdata())


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_debug_menu_opens_and_closes_in_the_fade(model):
    gb = boot(model, with_unlock())
    gesture(gb, taps=2)                          # (SELECT stays held; the third START opens it)
    seen = fade_trace(gb, "start", lambda: state(gb) == 7)
    check_fade(seen)
    release_gesture(gb)
    gb.run(30)
    assert gb.pb.memory[0xFF24] == 0x77
    seen = fade_trace(gb, "b", lambda: state(gb) == TITLE)
    check_fade(seen)
    gb.pb.stop(save=False)


def settled(gb):
    return not gb.pb.memory[TRANS_ADDR] & 0x1F and lcd_on(gb)


def go(gb, legs, name, press, ready, cont=True, mute_after=False, silent_ok=False):
    """One menu change as a timed leg: the press, then until `ready` and the fade is over, 6 more frames; the next leg starts settled."""
    run_until(gb, lambda: settled(gb), MAX_FRAMES)
    gb.run(8)
    l = Leg(gb, name, cont, silent_ok, mute_after)
    l.run(1) if press is None else l.press(press)
    l.until(lambda: ready() and settled(gb), MAX_FRAMES)
    l.run(6)
    legs.append(l)


def legs_table(gb, legs):
    idle_title(gb)
    go(gb, legs, "title -> scores (idle)", None, lambda: state(gb) == GS_SCORES)
    go(gb, legs, "scores -> title (A)", "a", lambda: state(gb) == TITLE)


def legs_minilist(gb, legs):
    title_pick(gb, K_BONUS)
    gb.run(MENU_SETTLE)
    menu_to(gb, K_MINIGAMES)
    go(gb, legs, "BONUS -> MINI GAMES", "a", lambda: state(gb) == GS_MGLIST)
    go(gb, legs, "MINI GAMES -> BONUS", "b", lambda: state(gb) == TITLE)


def legs_soundtrack(gb, legs):
    title_pick(gb, K_BONUS)
    gb.run(MENU_SETTLE)
    menu_to(gb, K_SOUNDTRACK)
    go(gb, legs, "BONUS -> SOUNDTRACK", "a", lambda: state(gb) == GS_JUKEBOX, cont=False, mute_after=True)
    go(gb, legs, "SOUNDTRACK -> BONUS", "b", lambda: state(gb) == TITLE, cont=False)


def legs_rush(gb, legs):
    title_pick(gb, K_BONUS)
    gb.run(MENU_SETTLE)
    menu_to(gb, K_BOSSRUSH)
    go(gb, legs, "BONUS -> BOSS RUSH", "a", lambda: on_rush(gb, RS_MENU))
    run_until(gb, lambda: settled(gb), MAX_FRAMES)
    tap(gb, "down")
    go(gb, legs, "BOSS RUSH menu -> list", "a", lambda: on_rush(gb, RS_LIST))
    go(gb, legs, "BOSS RUSH list -> menu", "b", lambda: on_rush(gb, RS_MENU))
    go(gb, legs, "BOSS RUSH menu -> BONUS", "b", lambda: state(gb) == TITLE)


def legs_practice(gb, legs):
    title_pick(gb, K_BONUS)
    gb.run(MENU_SETTLE)
    menu_to(gb, K_MINIGAMES)
    gb.press("a", 2)
    run_until(gb, lambda: state(gb) == GS_MGLIST and settled(gb), MAX_FRAMES)
    go(gb, legs, "list -> game 0", "a", lambda: state(gb) == GS_MINI, cont=False)
    gb.run(70)
    gb.write("mg_phase", 4)
    run_until(gb, lambda: gb.mem("overlay_on") == 1, 120)
    gb.run(40)
    go(gb, legs, "game 0 result -> list", "b", lambda: state(gb) == GS_MGLIST, cont=False)


MENU_SCENARIOS = {"table": legs_table, "minilist": legs_minilist, "soundtrack": legs_soundtrack, "rush": legs_rush, "practice": legs_practice}


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("scenario", list(MENU_SCENARIOS))
def test_menu_fades_keep_the_tune_in_time(model, scenario):
    legs = []
    with make_rom(model, None, sound=True) as gb:
        gb.run(120)
        hold_stage_anim(gb)
        gb.run(240)
        trans_enable(gb, True)
        MENU_SCENARIOS[scenario](gb, legs)
    check(legs)
