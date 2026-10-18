# The scene transition's palette fades (src/trans.c variants 1 and 2: fade to white, fade through amber) and the drink's borrowed tile ids.
# Every other test runs with transitions off (conftest: HRAM 0xFFF1 bit 7); here they are on, in every variant (TRANS bits 5-6).
#   - the picture after a fade, settled, is the picture without the transition (the colours came back exactly);
#   - TRANS is clear, the LCD on and the volume full after it;
#   - (the puff's tiles after every variant: tests/test_trans_puff.py)
import pytest

from conftest import K_PLAY, K_STORY, TR_OFF, TRANS_ADDR, hold_stage_anim, menu_tap, title_pick, trans_enable
from test_sound import make_rom
from test_story import to_shift, win

pytestmark = pytest.mark.timeout(900)

VARIANTS = [0, 1, 2]


def boot(model, variant, on=True):
    gb = make_rom(model, None, sound=True)
    gb.run(120)
    hold_stage_anim(gb)
    trans_enable(gb, on)
    if on:
        m = gb.pb.memory
        m[TRANS_ADDR] = (m[TRANS_ADDR] & ~0x60) | (variant << 5)
    return gb


@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_picture_after_the_transition_is_the_picture_without_it(model, variant):
    shots = []
    for on in (True, False):
        gb = boot(model, variant, on)
        title_pick(gb, K_PLAY, K_STORY, press=False)
        menu_tap(gb, "a")
        menu_tap(gb, "a")
        gb.run(300)
        shots.append(gb.image().tobytes())
        if on:
            m = gb.pb.memory
            assert not m[TRANS_ADDR] & 7, "TRANS flags clear after the transition"
            assert m[0xFF40] & 0x80
            assert m[0xFF24] in (0x77, 0)       # (a ROM without sound keeps NR50 at 0)
        gb.pb.stop(save=False)
    assert shots[0] == shots[1]


# ---- palette writes under the fade-in: every colour the scene shows without a transition is shown after it (a palette written after DISPLAY_ON, or a
# slot the scene never rewrites, would come out white or stale). The set of colours on the screen, a settled stretch later, with and without.
def colours(gb):
    return set(gb.image().getdata())


def scene_shift_next(model, variant, on):
    gb = to_shift(model, 0, 0)
    trans_enable(gb, on)
    if on:
        gb.pb.memory[TRANS_ADDR] = (gb.pb.memory[TRANS_ADDR] & ~0x60) | (variant << 5)
    win(gb, 0, 0)
    gb.run(700)
    return gb


def scene_mini(model, variant, on):
    from test_trans import mini_chapter
    c = mini_chapter()
    gb = to_shift(model, c, 1)
    trans_enable(gb, on)
    if on:
        gb.pb.memory[TRANS_ADDR] = (gb.pb.memory[TRANS_ADDR] & ~0x60) | (variant << 5)
    win(gb, c, 1)
    gb.run(700)
    return gb


def scene_boss(model, variant, on):
    from test_story import BOSS_BUILT, clear_bars
    from test_flow import GS_GOAL, LEVEL_CLEAR, run_until, state
    c = min(BOSS_BUILT)
    gb = to_shift(model, c, 2)
    trans_enable(gb, on)
    if on:
        gb.pb.memory[TRANS_ADDR] = (gb.pb.memory[TRANS_ADDR] & ~0x60) | (variant << 5)
    win(gb, c, 2)                                  # (Last call's quota met: the bars empty, then the level turns into the boss fight: the cover, his banner)
    gb.run(3)
    clear_bars(gb)
    run_until(gb, lambda: state(gb) == GS_GOAL, 800)
    gb.run(300)
    return gb


def scene_picture(model, variant, on):
    gb = boot(model, variant, on)
    title_pick(gb, K_PLAY, K_STORY, press=False)
    menu_tap(gb, "a")
    menu_tap(gb, "a")
    gb.run(200)
    gb.press("start", 2)                      # INTRO -> the chapter's PRE scene (a story picture)
    gb.run(300)
    return gb


@pytest.mark.parametrize("scene", [scene_shift_next, scene_mini, scene_boss, scene_picture], ids=lambda f: f.__name__)
@pytest.mark.parametrize("variant", [1, 2])
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_every_colour_comes_back_after_the_fade(model, variant, scene):
    a = scene(model, variant, True)
    b = scene(model, variant, False)
    ca, cb = colours(a), colours(b)
    a.pb.stop(save=False)
    b.pb.stop(save=False)
    assert cb <= ca, "colours missing after the fade: %s" % sorted(cb - ca)


@pytest.mark.parametrize("variant", [1, 2])
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_tune_ticks_through_the_fade_and_the_volume_dips_and_returns(model, variant):
    from test_music_transitions import FRAME, LATE, tick_log
    gb = boot(model, variant)
    title_pick(gb, K_PLAY, K_STORY, press=False)
    menu_tap(gb, "a")
    stamps = tick_log(gb)
    n0 = len(stamps)
    vols, marks = [], []
    gb.pb.button_press("a")
    for i in range(120):
        gb.run(1)
        if i == 2:
            gb.pb.button_release("a")
        vols.append(gb.pb.memory[0xFF24])
        marks.append((gb.pb._cycles(), vols[-1]))
    ticks = stamps[max(n0 - 1, 0):]
    vol = lambda c: next((v for t, v in marks if t >= c), 0x77)
    gaps = [(b - a) / FRAME for a, b in zip(ticks, ticks[1:]) if vol(a) or vol(b)]     # (the silent hold may take as long as the rebuild does)
    assert gaps and max(gaps) <= LATE, max(gaps)
    assert min(vols) == 0 and vols[-1] == 0x77
    gb.pb.stop(save=False)
