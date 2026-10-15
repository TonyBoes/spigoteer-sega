# The scene transition (src/trans.c, owner 2026-10-15): a fizzy drink fills the screen from the bottom at a scene / stage change, the next scene is
# built behind it and the drink drains with its bubbles popping. Every other test runs with it off (conftest: HRAM 0xFFF1 bit 7); here it is on.
#
# What each wired change must show (both models):
#   - the drink runs: the window rises (LYC off, WY falling to 0) over the old scene, the LCD goes off for the rebuild, the window covers every frame
#     the LCD is on until the reveal (no frame shows a half-built scene), then drains and the window, LYC, sprites, banner rows and the volume
#     are put back (TRANS clear);
#   - the new scene is the one the game would have shown without the drink (same state, same picture once it has settled);
#   - the music keeps ticking at a frame's pace through all of it, the old tune goes quiet (NR50 down) and is back at full volume.
import re

import pytest
from conftest import ROM, K_ARCADE, K_CLASSIC, K_PLAY, K_STORY, TR_OFF, TRANS_ADDR, check_golden, hold_stage_anim, title_pick, trans_enable
from test_flow import GS_GOAL, LEVEL_CLEAR, PLAYING, TITLE, lose_a_life, run_until, state
from test_music_transitions import FRAME, LATE, tick_log
from test_sound import make_rom
from test_story import (BOSS_BUILT, GS_MINI, MG_RESULT, MG_RESULT_MIN, MINI_BUILT, SC, finish_mini, pre, start_story, to_shift, win)

pytestmark = pytest.mark.timeout(900)

TR_WANT, TR_PEND, TR_ARMED = 1, 2, 4
BANNER_WY = 64
GS_STORY = 11
PANEL_TOP, PANEL_BOT = 63, 64              # build/art.h TILE_PANEL_TOP / BOT
MG_MILKRUN = 6


def mem(gb, a):
    return gb.pb.memory[a]


class Trace:
    """A frame-by-frame record of everything the drink touches, from `begin` on."""

    def __init__(self, gb):
        self.gb, self.fr = gb, []
        self.stamps = tick_log(gb)
        self.n0 = len(self.stamps)
        self.snap()

    def snap(self):
        m = self.gb.pb.memory
        self.fr.append(dict(lcdc=m[0xFF40], wy=m[0xFF4A], lyc=m[0xFF45], tr=m[TRANS_ADDR], nr50=m[0xFF24], st=state(self.gb),
                            tune=self.gb.mem("cur_tune"), c=self.gb.pb._cycles()))

    def run(self, n=1):
        for _ in range(n):
            self.gb.run(1)
            self.snap()

    def until_done(self, limit=260, tail=4):
        """Frames on until the drink has run (a PEND seen, then clear with the LCD on) and `tail` more."""
        seen = False
        for _ in range(limit):
            self.run()
            f = self.fr[-1]
            seen = seen or f["tr"] & TR_PEND
            if seen and not f["tr"] & (TR_PEND | TR_ARMED) and f["lcdc"] & 0x80 and f["lyc"] != 255 and f["wy"] == BANNER_WY:
                self.run(tail)
                return
        raise AssertionError("the drink did not finish in %d frames" % limit)


def lcd_on(f):
    return f["lcdc"] & 0x80


def covering(f):
    return lcd_on(f) and f["lcdc"] & 0x20 and f["lyc"] == 255


def check_drink(t, tune_changes=None, music=True):
    """The drink's shape in a trace that began at the press that changed the scene."""
    fr = t.fr
    first = next(i for i, f in enumerate(fr) if f["tr"] & TR_PEND)
    cover = [f for f in fr[:first] if covering(f)]
    assert len(cover) >= 20, "the rise covers the old scene for ~24 frames, saw %d" % len(cover)
    wys = [f["wy"] for f in cover]
    assert wys == sorted(wys, reverse=True) and wys[0] < BANNER_WY + 80 and wys[-1] == 0, wys          # rising: WY falls to the top of the screen
    assert any(not lcd_on(f) for f in fr[first - 3:first + 40]), "the rebuild runs with the LCD off"
    # no half-built scene: between the cover and the end, every frame with the LCD on is the drink (window on, LYC off)
    end = next(i for i in range(first, len(fr)) if not fr[i]["tr"] & (TR_PEND | TR_ARMED) and lcd_on(fr[i]) and fr[i]["wy"] == BANNER_WY and fr[i]["lyc"] != 255)
    for i, f in enumerate(fr[first - 1:end], first - 1):
        if lcd_on(f):
            assert f["lcdc"] & 0x20 and f["lyc"] == 255, "frame %d shows the scene without the drink: %s" % (i, f)
    drain = [f["wy"] for f in fr[first:end] if lcd_on(f) and f["lyc"] == 255]
    assert 0 in drain and max(drain) >= 138, drain                                                     # the foam line falls back to the bottom
    assert drain == sorted(drain), drain
    # put back
    f = fr[-1]
    audible = max(x["nr50"] for x in fr) > 0                  # (a ROM built with sound off keeps NR50 at 0: the volume is not observable there)
    assert f["wy"] == BANNER_WY and f["lyc"] != 255 and f["lcdc"] & 0x02 and (f["nr50"] == 0x77 or not audible) and not f["tr"] & 7, f
    # the music: a tick every frame (never a hitch), the old tune ducked while the drink rose, the volume back
    ticks = [s for s in t.stamps[max(t.n0 - 1, 0):]]
    vol = lambda s: next((f["nr50"] for f in fr if f["c"] >= s), 0x77)
    gaps = [(b - a) / FRAME for a, b in zip(ticks, ticks[1:]) if vol(a) or vol(b)]     # (the silent hold may take as long as the rebuild does)
    assert not music or (gaps and max(gaps) <= LATE), "a tick gap of %.2f frames" % max(gaps)
    low = [f["nr50"] for f in fr[:first] if covering(f)]
    if audible and music:
        assert min(f["nr50"] for f in fr) == 0, "the tune ducks to silence under the drink"
        assert low == sorted(low, reverse=True), low                                                   # fading out as it rises
    if tune_changes is not None:
        assert (fr[0]["tune"] != fr[-1]["tune"]) == tune_changes


def window_rows(gb):
    """The banner window's map rows 0-2 (0x9C00 +): panel, text, panel."""
    m = gb.pb.memory
    return [bytes(m[0x9C00 + 32 * r + c] for c in range(20)) for r in range(3)]


def shown(gb):
    return gb.screenshot() if False else gb.image().tobytes()


@pytest.fixture(params=["dmg", "cgb"])
def title(request):
    gb = make_rom(request.param, None, sound=True)
    gb.run(120)
    hold_stage_anim(gb)
    trans_enable(gb)
    gb.model_name = request.param
    yield gb
    gb.pb.stop(save=False)


def settle(gb, n=70):
    gb.run(n)


def test_the_flag_is_off_in_every_other_test(title):
    trans_enable(title, False)
    assert mem(title, TRANS_ADDR) & TR_OFF
    title_pick(title, K_PLAY, K_STORY)
    t = Trace(title)
    t.run(90)
    assert not any(f["tr"] & TR_PEND or f["lyc"] == 255 for f in t.fr), "TR_OFF: the cut is a cut"
    assert t.fr[-1]["st"] == GS_STORY


def test_title_to_story_runs_the_drink_and_opens_the_intro(title):
    title_pick(title, K_PLAY, K_STORY, press=False)
    title.run(2)
    t = Trace(title)
    title.press("a", 2)
    t.snap()
    t.until_done()
    check_drink(t, tune_changes=False)                                    # (the title tune carries on as the intro's)
    assert t.fr[-1]["st"] == GS_STORY and title.mem("story_scene") == SC["INTRO"]
    assert window_rows(title)[0] == bytes([PANEL_TOP]) * 20 and window_rows(title)[2] == bytes([PANEL_BOT]) * 20


def test_title_to_arcade_and_classic_run_the_drink(title):
    title_pick(title, K_PLAY, K_ARCADE, press=False)
    t = Trace(title)
    title.press("a", 2)
    t.snap()
    t.until_done()
    check_drink(t)
    assert t.fr[-1]["st"] in (GS_GOAL, PLAYING)


def test_title_to_classic_runs_the_drink(title):
    title_pick(title, K_PLAY, K_CLASSIC, press=False)
    t = Trace(title)
    title.press("a", 2)
    t.snap()
    t.until_done()
    check_drink(t, tune_changes=True)
    assert t.fr[-1]["st"] == PLAYING


def test_the_scene_after_the_drink_is_the_scene_without_it(title):
    """The intro's first page, a settled frame later, is the same picture with the drink as without."""
    title_pick(title, K_PLAY, K_STORY)
    title.run(250)
    with_drink = shown(title)
    trans_enable(title, False)
    # (the same game again, drink off)
    other = make_rom(title.model_name, None, sound=True)
    other.run(120)
    hold_stage_anim(other)
    title_pick(other, K_PLAY, K_STORY)
    other.run(250)
    assert shown(other) == with_drink
    other.pb.stop(save=False)


def test_a_scene_leaves_for_the_next_behind_the_drink(title):
    """INTRO -> its chapter's PRE scene (START: scene_done), then PRE -> the venue's Opening banner."""
    title_pick(title, K_PLAY, K_STORY)
    title.run(200)
    assert title.mem("story_scene") == SC["INTRO"]
    t = Trace(title)
    title.press("start", 2)
    t.snap()
    t.until_done()
    check_drink(t)
    assert title.mem("story_scene") == pre(0) and t.fr[-1]["st"] == GS_STORY
    title.run(200)
    t = Trace(title)
    title.press("start", 2)
    t.snap()
    t.until_done()
    check_drink(t)
    assert t.fr[-1]["st"] == GS_GOAL
    rows = window_rows(title)
    assert rows[0] == bytes([PANEL_TOP]) * 20, "the goal banner's top panel is back after the drink"


def test_a_shift_clear_goes_to_the_next_shift_behind_the_drink(title):
    rom = to_shift(title.model_name, 0, 0)
    trans_enable(rom)
    win(rom, 0, 0)
    rom.run(1)
    t = Trace(rom)
    for _ in range(400):                                                  # LEVEL CLEAR plays out, then the drink
        t.run()
        if t.fr[-1]["tr"] & TR_PEND:
            break
    t.until_done()
    check_drink(t, music=False)                                           # (the story helpers' ROMs have no sound: tests/test_music_transitions.py has the tune)
    assert t.fr[-1]["st"] == GS_GOAL and rom.mem("story_shift") == 1
    rom.pb.stop(save=False)


def test_try_again_restarts_behind_the_drink(title):
    rom = to_shift(title.model_name, 0, 0)
    rom.write("lives", 1)
    lose_a_life(rom)
    run_until(rom, lambda: rom.mem("story_phase") == 4, 300)                  # SP_FAIL: TRY AGAIN is up
    rom.run(5)
    trans_enable(rom)
    t = Trace(rom)
    rom.press("a", 2)
    t.snap()
    t.until_done()
    check_drink(t, music=False)
    assert t.fr[-1]["st"] == GS_GOAL
    rom.pb.stop(save=False)


def mini_chapter():
    return next(c for c in range(10) if c in MINI_BUILT)


def test_a_shift_clear_into_the_mini_game_and_out_of_it(title):
    c = mini_chapter()
    rom = to_shift(title.model_name, c, 1)
    trans_enable(rom)
    win(rom, c, 1)
    t = Trace(rom)
    for _ in range(500):
        t.run()
        if t.fr[-1]["tr"] & TR_PEND:
            break
    t.until_done(tail=10)
    check_drink(t, music=False)
    assert t.fr[-1]["st"] == GS_MINI
    run_until(rom, lambda: rom.pb.memory[0xFF40] & 0x80, 10)              # (the result window's A: the next shift behind a drink of its own)
    rom.write("mg_phase", MG_RESULT)
    run_until(rom, lambda: rom.mem("overlay_on") == 1 and rom.mem("mg_t") >= MG_RESULT_MIN, 200)
    t = Trace(rom)
    rom.press("a", 2)
    t.snap()
    t.until_done()
    check_drink(t, music=False)
    assert t.fr[-1]["st"] != GS_MINI
    rom.pb.stop(save=False)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_milk_run_is_entered_and_left_behind_the_drink(model):
    """Milk Run's raster handler (LYC / SCX walk) is swapped for the plain one while the drink is up and put back after: the street
    runs as it does without the drink (LYC at a frame's edge the same), and leaving it is a drink too."""
    if 6 not in MINI_BUILT:
        pytest.skip("Milk Run is not a built story mini-game")

    def enter(on):
        rom = to_shift(model, 6, 1)
        trans_enable(rom, on)
        win(rom, 6, 1)
        t = Trace(rom)
        if on:
            for _ in range(500):
                t.run()
                if t.fr[-1]["tr"] & TR_PEND:
                    break
            t.until_done(tail=20)
        else:
            run_until(rom, lambda: rom.mem("game_state") == GS_MINI and rom.pb.memory[0xFF40] & 0x80, 500)
            rom.run(80)
        assert rom.mem("game_state") == GS_MINI and rom.mem("mg_id") == MG_MILKRUN
        return rom, t

    rom, t = enter(True)
    check_drink(t, music=False)
    control, _ = enter(False)
    rom.run(60)
    control.run(60)
    edge = lambda g: [(g.pb.memory[0xFF45], g.pb.memory[0xFF43]) for _ in range(6) for __ in [g.run(1)]]
    assert edge(rom) == edge(control) or {a for a, _ in edge(rom)} == {a for a, _ in edge(control)}, "Milk Run's raster split is back after the drink"
    control.pb.stop(save=False)
    # leaving: the result's A -> the next shift, behind a drink with the plain handler
    rom.write("mg_phase", MG_RESULT)
    run_until(rom, lambda: rom.mem("overlay_on") == 1 and rom.mem("mg_t") >= MG_RESULT_MIN, 200)
    t = Trace(rom)
    rom.press("a", 2)
    t.snap()
    try:
        t.until_done()
    except AssertionError:
        print([(f['st'], hex(f['tr']), f['wy'], f['lyc'], hex(f['lcdc'])) for f in t.fr[::8]])
        raise
    check_drink(t, music=False)
    assert t.fr[-1]["st"] != GS_MINI
    rom.pb.stop(save=False)


def test_no_drink_over_the_pause_menu(title):
    """A wired change asked for while the pause menu is open (the guard in lcd_off_p) is a plain cut."""
    title_pick(title, K_PLAY, K_CLASSIC)
    title.run(120)
    title.press("start", 2)
    title.run(10)
    assert state(title) == 5
    title.pb.memory[TRANS_ADDR] |= TR_WANT
    t = Trace(title)
    title.press("down", 2)
    title.press("a", 2)                                                   # (QUIT TO MENU or RESUME: whatever DISPLAY_OFF it does)
    t.run(80)
    assert not any(f["tr"] & TR_PEND for f in t.fr)


def goto_drink_frame(gb, name):
    """Title -> STORY, on to a frame by what the screen is doing: `rise` the foam line at WY <= 72 over the title, `full` the first frame the
    LCD is on again (the new scene behind a full screen), `drain` the foam line falling past WY 72 over the intro."""
    title_pick(gb, K_PLAY, K_STORY, press=False)
    gb.run(2)
    t = Trace(gb)
    gb.press("a", 2)
    t.snap()
    pend = full = False
    for _ in range(300):
        f = t.fr[-1]
        pend = pend or bool(f["tr"] & TR_PEND)
        if name == "rise" and covering(f) and f["wy"] <= 72 and not pend:
            return
        if name == "full" and pend and covering(f) and f["st"] == GS_STORY:
            gb.run(2)                                   # (the first frame after the LCD comes on is blank on hardware too)
            return
        full = full or (pend and covering(f) and f["st"] == GS_STORY)
        if name == "drain" and full and covering(f) and f["wy"] >= 72:
            return
        t.run()
    raise AssertionError("frame %s not reached" % name)


@pytest.mark.parametrize("name", ["rise", "full", "drain"])
def test_the_drinks_frames_look_as_approved(title, name):
    """Goldens of the title -> STORY transition: the foam line rising over the title, the full screen, the drink draining over the intro."""
    goto_drink_frame(title, name)
    check_golden(title, "trans_" + name)


def refs(gb):
    m = gb.pb.memory
    bg = {m[b + r * 32 + c] for b in (0x9800, 0x9C00) for r in range(32) for c in range(32)}
    obj = set()
    for i in range(40):
        t = m[0xFE02 + 4 * i]
        obj |= {t, t | 1, t & 0xFE}
    return bg, obj


DRINK_IDS = set(range(248, 252))


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_no_wired_screen_uses_the_drinks_tile_ids(model):
    """The drink borrows BG / OBJ tile ids 248-251 (src/trans.c T_FOAM..T_BUB2): none of the screens it covers or reveals may refer to them."""
    from test_mg import MG_PRACTICE, mg_enter, practice
    from test_story import BOSS_BUILT as bosses
    import boss_common
    seen = []

    def scan(gb, tag):
        bg, obj = refs(gb)
        seen.append(tag)
        assert not (bg | obj) & DRINK_IDS, (tag, sorted((bg | obj) & DRINK_IDS))

    gb = start_story(model)
    scan(gb, "intro")
    gb.pb.stop(save=False)
    for c in range(10):
        gb = to_shift(model, c, 0, banner=True)
        scan(gb, f"chapter {c} banner")
        gb.run(40)
        scan(gb, f"chapter {c} play")
        gb.pb.stop(save=False)
    for c in sorted(bosses):
        gb = boss_common.fight(model, c)
        gb.run(90)
        scan(gb, f"boss {c}")
        gb.pb.stop(save=False)
    for gid in list(range(10)) + [11, 12, 13, 14]:
        gb = practice(model)
        mg_enter(gb, gid, MG_PRACTICE)
        for k in range(3):
            gb.run(80)
            scan(gb, f"mini-game {gid} +{80 * (k + 1)}")
        gb.pb.stop(save=False)
    assert len(seen) > 40
