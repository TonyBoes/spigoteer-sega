# The show stage's wash (owner 2026-11-03: "The wash is good enough. No sweeps."; src/lights.c, src/showlights.h, render.c pal5_check / pal5_write), Color only.
#   While a show plays the stage's BG palettes 5 and 6 (text rows 1-4) go dark with a tint that steps every two dance beats through magenta, blue, amber and green (lt_tint, read from the source here);
#   each change of tint is a crossfade over LT_BLEND frames (owner 2026-11-04: no hard cuts); 16 frames of fade in at the start and out at the end. The dim colours come from the BRIGHT-lifted stage colours. The HUD, the bars and the performers keep their palettes; the DMG is untouched.
#   The 16 bytes it writes live in story_scratch[32..47] (OBJX_CO, the fades' OBJ-colour source), with a stamp byte at story_scratch[64].
import numpy as np
import pytest

from conftest import GS_PAUSED, THEMES, double_speed, gba_hardware, logic_paused, venue as venue_art
from test_art import goto_group
from test_lift import boot_play, freeze
from test_patrons import clear_patrons
from test_show_obj5 import play
from test_story import call_banked
from test_venues import cgb_palette

from wash_helpers import BEAT, BLEND, FADE, SHOW_FRAMES, STEP, TINTS, chan, dim, dim_el

SCR_OBJXC, SCR_LTST = 32, 64
MODEL = pytest.mark.only_model("cgb")
STAGE = (5, 6)                                   # BGPAL_STAGE, BGPAL_STAGE_B
OTHERS = (0, 1, 2, 3, 4, 7)


def timer(gb):
    a = gb.addr("show_timer")
    b = gb.read(a, 2)
    return b[0] | b[1] << 8


def start(gb, frames=SHOW_FRAMES):
    with logic_paused(gb):
        a = gb.addr("show_timer")
        gb.write(a, frames & 255)
        gb.write(a + 1, frames >> 8)


def pals(gb, slots=STAGE):
    return [cgb_palette(gb, s) for s in slots]


def lit_of(gb):
    return pals(gb)


def expect(lit, el, left):
    """The palettes (5, 6) the wash makes of the lit ones at `el` frames into a show with `left` frames to go."""
    return [[dim_el(w, el, left) for w in p] for p in lit]


def near(gb, lit, spread=1):
    """What each stage palette is now matches the wash for the frame the timer says, give or take a frame (BG 5 comes through the split's buffer, BG 6 from the VBlank's: one level apart on some frames)."""
    t = timer(gb)
    got = pals(gb)
    for k in range(2):
        if not any(got[k] == expect(lit, SHOW_FRAMES - t + d, t - d)[k] for d in range(-spread, spread + 1)):
            return False
    return True


def show_play(group, ds=True):
    gb = play(group, ds)
    freeze(gb)
    clear_patrons(gb)
    gb.run(4)
    return gb


# ---- the stage goes dark -------------------------------------------------------------------------------------------------------------------------------------------------------------
@MODEL
@pytest.mark.parametrize("g", range(len(THEMES)), ids=list(THEMES))
def test_the_stage_palettes_are_dim_and_tinted_during_a_show(g):
    gb = show_play(g)
    lit = lit_of(gb)
    start(gb)
    gb.run(FADE + 4)
    assert pals(gb) != lit, "the stage palettes changed"
    seen = set()
    for i in range(200):
        gb.run(1)
        seen.add(tuple(map(tuple, pals(gb))))
        assert near(gb, lit), (THEMES[g], i, timer(gb), pals(gb))
    assert len(seen) >= 4, "it stepped through the tints"
    assert sum(sum(c & 31 for c in p) for p in pals(gb)) < sum(sum(c & 31 for c in p) for p in lit), "darker than lit"


@MODEL
def test_the_tints_step_in_order_every_two_beats():
    gb = show_play(0)
    lit = lit_of(gb)
    start(gb)
    seq = []
    for i in range(SHOW_FRAMES - FADE - 4):
        gb.run(1)
        el = SHOW_FRAMES - timer(gb)
        if el < FADE:
            continue
        got = pals(gb)
        for ti in range(4):
            if got == [[dim(w, ti, FADE) for w in p] for p in lit]:
                seq.append((el, ti))
                break
    assert seq, "no steady frame matched a tint"
    runs = []
    for el, ti in seq:
        if not runs or runs[-1][0] != ti:
            runs.append([ti, el, el])
        runs[-1][2] = el
    assert [r[0] for r in runs][:8] == [(runs[0][0] + k) & 3 for k in range(8)], runs[:8]
    for a, b in zip(runs[1:], runs[2:-1]):
        assert abs((b[1] - a[1]) - STEP) <= 2, ("a tint starts every two beats", a, b)       # (the steady part of each step, after its blend, starts a step apart)
    for r in runs[1:-1]:
        assert abs((r[2] - r[1] + 1) - (STEP - BLEND)) <= 2, ("steady for what the blend leaves", r)
    assert len({tuple(t) for t in TINTS}) == 4 and len(TINTS) == 4, "magenta, blue, amber, green"


@MODEL
def test_the_wash_fades_in_and_out_over_sixteen_frames():
    gb = show_play(0)
    lit = lit_of(gb)
    lum = lambda ps: sum(((c & 31) + ((c >> 5) & 31) + ((c >> 10) & 31)) for p in ps for c in p)
    start(gb)
    ins = []
    for i in range(FADE + 6):
        gb.run(1)
        ins.append(lum(pals(gb)))
    assert ins[0] >= ins[1] >= ins[2], "falling from the first frames"
    assert all(a >= b for a, b in zip(ins, ins[1:])), ("a steady fall in", ins)
    assert lum(lit) >= ins[0] > ins[FADE + 1], "the first frame is hardly dim, the last of the fade is dark"
    assert len(set(ins[:FADE])) >= 8, "a gradual fade, not a jump"
    out = []
    while timer(gb) > FADE:                       # (past the last tint change's blend, which ends as the fade starts)
        gb.run(1)
    while timer(gb) > 0:
        gb.run(1)
        out.append(lum(pals(gb)))
    assert all(a <= b for a, b in zip(out, out[1:])), ("a steady rise out", out)
    assert out[0] < lum(lit) and len(set(out)) >= 8
    gb.run(6)
    assert pals(gb) == lit, "the lit stage is back when the show is over"
    assert gb.mem("pal5_req") & 4 == 0


# ---- BRIGHT ------------------------------------------------------------------------------------------------------------------------------------------------------------------------
@MODEL
def test_bright_still_applies_the_dim_colours_derive_from_the_lifted_ones():
    from test_bright import lift_word
    with gba_hardware(True, 2), double_speed():
        gb = boot_play("cgb")
    try:
        freeze(gb)
        clear_patrons(gb)
        gb.run(10)
        assert gb.mem("_is_GBA") & 2, "BRIGHT is on"
        lit = lit_of(gb)
        v = venue_art(0)["pal"]
        assert lit[0] == [lift_word(w) for w in v[0]] and lit[1] == [lift_word(w) for w in v[1]], "the lit stage is the lifted one"
        start(gb)
        gb.run(FADE + 4)
        for i in range(60):
            gb.run(1)
            assert near(gb, lit), (i, timer(gb), pals(gb))
        # a plain run: the dim colours differ from a NORMAL run's (they came through the lift, not under it)
    finally:
        gb.stop()
    gb = show_play(0)
    n_lit = lit_of(gb)
    start(gb)
    gb.run(FADE + 4)
    assert near(gb, n_lit) and pals(gb) != [[dim(lift_word(w), (SHOW_FRAMES - timer(gb)) // STEP & 3, FADE) for w in p] for p in n_lit]


# ---- what it leaves alone -----------------------------------------------------------------------------------------------------------------------------------------------------------
@MODEL
@pytest.mark.parametrize("g", [0, 1, 4], ids=["saloon", "sports", "divers"])
def test_the_hud_the_bars_and_the_other_palettes_are_untouched(g):
    gb = show_play(g)
    base = pals(gb, OTHERS)
    obj = [cgb_palette(gb, i, True) for i in (0, 1, 2)]
    off = np.asarray(gb.image()).copy()
    start(gb)
    gb.run(FADE + 30)
    for i in range(80):
        gb.run(1, render=(i % 20 == 0))
        assert pals(gb, OTHERS) == base, (i, "BG 0-4 and 7")
        assert [cgb_palette(gb, i2, True) for i2 in (0, 1, 2)] == obj
    on = np.asarray(gb.image())
    assert (on[:8] == off[:8]).all(), "the HUD row"
    assert (on[56:] == off[56:]).all(), "the bars and what is under the stage"
    assert (on[8:40] != off[8:40]).any(), "the stage is what changed"


@pytest.mark.only_model("dmg")
def test_the_dmg_is_untouched():
    gb = boot_play("dmg")
    freeze(gb)
    clear_patrons(gb)
    gb.run(10)
    sc = gb.addr("story_scratch")
    for i in range(SCR_OBJXC, SCR_OBJXC + 16):
        gb.write(sc + i, 0xA5)
    gb.write(sc + SCR_LTST, 0x5A)
    regs = (gb.read(0xFF47, 1)[0], gb.read(0xFF48, 1)[0], gb.read(0xFF49, 1)[0])
    off = np.asarray(gb.image()).copy()
    start(gb)
    for i in range(SHOW_FRAMES - 4):
        gb.run(1)
        assert (gb.read(0xFF47, 1)[0], gb.read(0xFF48, 1)[0], gb.read(0xFF49, 1)[0]) == regs
        if i % 40 == 0:
            assert gb.mem("pal5_req") == 0
    assert list(gb.read(sc + SCR_OBJXC, 16)) == [0xA5] * 16 and gb.read(sc + SCR_LTST, 1)[0] == 0x5A, "the wash never touched its bytes"
    assert gb.mem("pal5_req") == 0


# ---- the scratch bytes ----------------------------------------------------------------------------------------------------------------------------------------------------------------
@MODEL
@pytest.mark.parametrize("g", [0, 3], ids=["saloon", "bistro"])
def test_junk_in_the_scratch_bytes_never_shows(g):
    """Real hardware leaves story_scratch junk: the buffer and its stamp are rebuilt by the show's first frames, whatever they held."""
    gb = show_play(g)
    lit = lit_of(gb)
    sc = gb.addr("story_scratch")
    for i in range(16):
        gb.write(sc + SCR_OBJXC + i, 0xFF)
    gb.write(sc + SCR_LTST, 1)                       # (a stamp that says the buffer is good: the tint 0's)
    call_banked(gb, "start_show")                    # (the game's own start: it clears the stamp)
    assert timer(gb) > SHOW_FRAMES - 4
    for i in range(80):
        gb.run(1)
        assert near(gb, lit), (i, timer(gb), pals(gb))


@MODEL
def test_pause_and_resume_in_the_middle_of_a_show_leaves_no_wrong_stage_colour():
    """A scene fade rewrites OBJX_CO (trans.c chain_cols, three show palettes: the Saloon), the wash's buffer: level.c obj_cols zeroes the stamp so lights_frame rebuilds, trans.c pal_in drops the VBlank request.
    A level's pause is no fade (only a boss's or mini-game's HOW TO PLAY card is), so this checks what a player can reach: the pause and its RESUME; the fade guards are the two lines named."""
    gb = show_play(0)
    lit = lit_of(gb)
    start(gb)
    gb.run(FADE + 40)
    assert near(gb, lit)
    gb.press("start", 2)
    for i in range(160):
        gb.run(1)
    assert gb.mem("game_state") == GS_PAUSED, "paused"
    gb.press("start", 2)                             # RESUME (the cursor starts on it)
    gb.run(2)
    bad, checked = [], 0
    for i in range(160):
        gb.run(1)
        if gb.mem("game_state") == 1 and timer(gb):
            checked += 1
            if not near(gb, lit, 2):
                bad.append((i, timer(gb), pals(gb)))
    assert checked > 100, "the game played on after the card"
    assert not bad, bad[:3]


@MODEL
def test_a_color_at_normal_speed_has_no_wash():
    """The ROM runs a Color at double speed (main_cold.c cpu_fast, the header byte at 0x3FFE); at normal speed the VBlank has no line to spare for the palette write (the copy list's drain starts on line 147 already),
    so lights_frame does nothing there: the tests that run a Color at normal speed see the lit stage in a show."""
    gb = show_play(0, False)
    lit = lit_of(gb)
    start(gb)
    for i in range(120):
        gb.run(1)
        assert pals(gb) == lit, i
    assert gb.mem("pal5_req") & 4 == 0


# ---- goldens (new): the stage at the four tints, steady (the show poked to the frames where each tint is on, so the picture does not move with the dance's own clock) -----------------------------
TINT_T = [592, 568, 544, 520]               # show_timer where tint 0 (magenta), 1 (blue), 2 (amber), 3 (green) has been on for a while, past its blend: el = 112, 136, 160, 184 (e // 3 = 4..7, 16 frames in)


def shot_at(gb, t):
    """The picture with the show held at `t` frames left (poked every frame: the dance's clock runs on, the wash does not move)."""
    a = gb.addr("show_timer")
    for _ in range(8):
        gb.write(a, t & 255)
        gb.write(a + 1, t >> 8)
        gb.run(1)
    gb.run(1, render=True)


@MODEL
@pytest.mark.parametrize("g", [0, 3], ids=["saloon", "bistro"])
@pytest.mark.parametrize("k", range(4), ids=["magenta", "blue", "amber", "green"])
def test_golden_the_stage_wash_at_each_tint(g, k):
    from conftest import check_golden
    gb = show_play(g)
    lit = lit_of(gb)
    start(gb)
    gb.run(FADE + 4)
    shot_at(gb, TINT_T[k])
    assert pals(gb) == [[dim(w, k, FADE) for w in p] for p in lit], "the steady tint k"
    check_golden(gb, f"wash_{THEMES[g]}_{k}")


# ---- no strobe: the crossfade (owner 2026-11-04: "Some of those lodge shows are going to give me a seizure with the flashing lights") ---------------------------------------------------------
MAX_STEP = 2          # the biggest change of any 5-bit channel of BG 5 / 6 between two frames: the blend moves a channel by (tint difference <= 14/32 of <= 31) / 16 < 1, a fade by 22/32 * 31 / 16 < 2 (the first frame jumps from lit 31 to 31: no step)


def worst_step(gb, frames):
    prev, worst = None, 0
    for _ in range(frames):
        gb.run(1)
        cur = [[(w & 31, (w >> 5) & 31, (w >> 10) & 31) for w in p] for p in pals(gb)]
        if prev:
            worst = max([worst] + [abs(a - b) for pa, pb in zip(cur, prev) for ca, cb in zip(pa, pb) for a, b in zip(ca, cb)])
        prev = cur
    return worst


@MODEL
@pytest.mark.parametrize("g", range(len(THEMES)), ids=list(THEMES))
def test_a_whole_show_never_jumps_a_stage_colour(g):
    """Every venue, Color at double speed: through a whole show (fade in, four-plus tint changes, fade out) neither stage palette changes by more than MAX_STEP in any channel in a frame."""
    gb = show_play(g)
    start(gb)
    w = worst_step(gb, SHOW_FRAMES - 2)
    assert w <= MAX_STEP


@MODEL
def test_the_tint_change_is_a_blend_over_the_set_frames():
    gb = show_play(0)
    lit = lit_of(gb)
    start(gb)
    gb.run(STEP - 2)                             # (just before the first change)
    seen = []
    for i in range(BLEND + 6):
        gb.run(1)
        seen.append(tuple(map(tuple, pals(gb))))
    assert len(set(seen)) >= BLEND // 2, "a gradual change, not a cut"
