# OBJ palette 5 during a show (owner 2026-11-02, Q7 "a": the dancers get their own palette above the stage line, so they stop borrowing a patron's OBJ slot).
# Color only. The show's colours go into OBJ 5 in every VBlank (render.c pal5_write); a patron whose palette instance 4 is OBJ 5 (the Saloon's MABEL and ARTIE, the Factory's
# TOOB, ...) has his own colours written back by the HBlank chain (src/main.c split_isr3, EV_OBJ, line game.h EV_OBJ_LY) between the dancers' last line (31) and the first line a patron
# can occupy (40: the top bar). Three checks, in the ten venues:
#   - the picture: the dancers' pixels are the show's colours and a lifted patron on OBJ 5 below the stage keeps his own, in the same frame (the frame with the show equals the frame without,
#     down to the pixel, below the stage);
#   - the hardware: the write is one per frame, in the HBlank of its own line (no mode 3), never on a line another palette is written on, at normal and double speed;
#   - the changes: the show starting, ending (on its own and with the Saloon's split going back to its one reload) and a fade of the screen during a show hold no wrong-colour frame.
import contextlib

import numpy as np
import pytest

from conftest import double_speed, logic_paused, venue as venue_art
from test_art import goto_group
from test_fade_chain import AMBER, WHITE, lerp, level_sets, pack, scene_change_frames
from test_lift import HOOK_LIFT, boot_play, freeze, hook
from test_patrons import lineup, clear_patrons, MAX_P
from test_venues import cgb_palette

pytestmark = pytest.mark.only_model("cgb")

EV_OBJ_LY = 35                       # game.h
DANCERS_LAST_LINE = 31               # STAGE_LAST_ROW * 8 - 1
FIRST_BAR_LINE = 40                  # BAR_TOP_Y(0)
OBJ_PAT, OBJ_SHOW = 218, 289         # scratch.h SCR_OBJ_AT / SCR_OBJ2_AT
VENUES = list(range(10))


@pytest.fixture(params=[False, True], ids=["normal", "double"])
def ds(request):
    return request.param


def show_cols(v):
    """Every colour of the venue's show palette(s): the Saloon's three dancers wear a palette each."""
    return {int(c) for p in venue_art(v)["show_pals"] for c in p[1:]}


def play(group, ds, model="cgb"):
    cm = double_speed() if ds else contextlib.nullcontext()
    with cm:
        gb = boot_play(model)
    if group:
        goto_group(gb, group)
    gb.run(10)
    return gb


def inst4_is_obj5(gb):
    return gb.read(gb.addr("story_scratch") + 254 + 4, 1)[0] == 5 and gb.mem("pal5_cur") != 2    # (INST_OBJ[4]; the Space Lounge's wears the show's colours: pal5_cur 2 from the start)


def sprites(gb, pal):
    return [s for s in gb.oam() if 0 < s["y"] < 160 and s["flags"] & 7 == pal]


def rect(ss, h=16, w=8):
    x0 = min(s["x"] for s in ss) - 8
    y0 = min(s["y"] for s in ss) - 16
    x1 = max(s["x"] for s in ss)
    return max(x0, 0), max(y0, 0), min(x1, 160), min(y0 + h + (max(s["y"] for s in ss) - min(s["y"] for s in ss)), 144)


def patch(img, r):
    x0, y0, x1, y1 = r
    return img[y0:y1, x0:x1]


def rgb555(gb, base, n=4):
    m = gb.pb.memory
    sc = gb.addr("story_scratch") + base
    return [m[sc + 2 * i] | m[sc + 2 * i + 1] << 8 for i in range(n)]


def lifted_patron(gb):
    """The venue's palette instance 4 patron on bar 0, lifted (a sprite in OBJ 5), the level frozen. Returns his slot."""
    freeze(gb)
    clear_patrons(gb)
    gb.run(2)
    slot = lineup(gb, {0: [(24, 4 << 3, 0)]})[(0, 24)][0]
    gb.run(6)
    hook(gb, slot, HOOK_LIFT)
    gb.run(6)
    assert gb.mem("lift_hook_res") == 1, "lifted"
    return slot


def start_show(gb, frames=200):
    with logic_paused(gb):
        gb.write("show_timer", frames)
        gb.write(gb.addr("show_timer") + 1, 0)


def end_show(gb):
    with logic_paused(gb):
        gb.write("show_timer", 0)
        gb.write(gb.addr("show_timer") + 1, 0)


# ---- the picture -----------------------------------------------------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("v", VENUES)
def test_the_dancers_wear_the_show_s_colours_and_a_patron_on_their_slot_keeps_his_own_below_the_stage(v, ds):
    gb = play(v, ds)
    try:
        chain = inst4_is_obj5(gb)
        show = show_cols(v)
        if chain:
            slot = lifted_patron(gb)
            assert sprites(gb, 5), "his sprite is in OBJ 5"
        gb.run(4)
        gb.run(1, render=True)
        before = pack(gb.image())
        r_pat = rect(sprites(gb, 5)) if chain else None
        start_show(gb)
        gb.run(30)
        gb.run(1, render=True)
        during = pack(gb.image())
        assert gb.mem("pal5_cur") == (3 if chain else 2)
        dancers = [s for s in gb.oam()[28:40] if s["y"]]
        assert len(dancers) == 12, "three dancers on the stage"
        r_d = rect(dancers, 24)
        r_d = (r_d[0], r_d[1], r_d[2], min(r_d[3], DANCERS_LAST_LINE + 1))
        assert r_d[3] <= DANCERS_LAST_LINE + 1
        bg = set(np.unique(patch(before, r_d)).tolist())
        mine = set(np.unique(patch(during, r_d)).tolist()) - bg
        want = {int(c) for c in show}
        assert mine, "the dancers are on the picture"
        assert mine <= want, ("dancer pixels in colours that are not the show's", sorted(mine - want), sorted(want))
        if chain:
            assert (patch(during, r_pat) == patch(before, r_pat)).all(), "the patron below the stage: the same pixels, show or no show"
            assert int(r_pat[1]) >= FIRST_BAR_LINE
            pat = {c for c in rgb555(gb, OBJ_PAT)[1:]}
            assert set(np.unique(patch(during, r_pat)).tolist()) & pat, "his own colours"
            assert not (set(np.unique(patch(during, r_pat)).tolist()) & (want - pat - bg)), "none of the show's"
    finally:
        gb.stop()


# ---- the hardware ----------------------------------------------------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("v", VENUES)
def test_the_obj_5_write_is_one_a_frame_in_its_own_line_s_hblank(v, ds):
    gb = play(v, ds)
    try:
        chain = inst4_is_obj5(gb)
        log = []

        def hook_at(name):
            a = gb.addr(name)

            def cb(_):
                m = gb.pb.memory
                log.append((name, m[0xFF44], m[0xFF41] & 3))
            gb.pb.hook_register(a >> 16, a & 0xFFFF, cb, None)
        for n in ("split_put_o", "split_put_o2", "split_put_oe", "split_put_a"):
            hook_at(n)
        gb.run(5)
        start_show(gb)
        gb.run(5)
        log.clear()
        n = 90
        gb.run(n)
        ent = [x for x in log if x[0] == "split_put_o"]
        ext = [x for x in log if x[0] == "split_put_oe"]
        if not chain:
            assert not ent, "this venue's dancers keep OBJ 5 alone: no write"
            return
        three = venue_art(v)["show_pal_n"] == 3                  # (three show palettes: OBJ 4's and 3's give-backs follow, one HBlank each: tests/test_show_three.py)
        assert all(x[2] != 3 for x in ent + ext), ("a write in mode 3", sorted({(x[1], x[2]) for x in ent + ext}))
        if three:                                                # (the Saloon's three palettes: the show's OBJ 3 and 4 at the top of the frame, the three give-backs: 5 writes a frame, tests/test_show_three.py has their lines)
            w = 3 + bin(gb.pb.memory[gb.addr("story_scratch") + 226] & 6).count("1")           # (the show's OBJ 3 and 4 at the top, OBJ 5's give-back, and one more for each of OBJ 4 and OBJ 3 a patron wears: the Saloon's five, the Bistro's four, nobody wears its OBJ 4)
            assert w * (n - 3) <= len(ext) <= w * (n + 3) and len(ent) == len(ext), (len(ent), len(ext), n, w)
            return
        assert len(ext) == len(ent) and n - 3 <= len(ent) <= n + 3, ("one write a frame", len(ent), n)
        assert {x[1] for x in ent} == {EV_OBJ_LY} and all(x[2] == 0 for x in ent), ("entry: its line, in HBlank", sorted({(x[1], x[2]) for x in ent}))
        assert {x[1] for x in ext} <= {EV_OBJ_LY, EV_OBJ_LY + 1} and all(x[2] in (0, 2) for x in ext if x[1] == EV_OBJ_LY + 1), ("exit: HBlank, or the next line's OAM scan (mode 2: palette RAM is open)", sorted({(x[1], x[2]) for x in ext}))
        others = {x[1] for x in log if x[0] == "split_put_a"}
        assert EV_OBJ_LY not in others, "no other palette is written on its line"
        sc = gb.addr("story_scratch")
        m = gb.pb.memory
        n_ev = m[sc + 286]
        lines = [m[sc + 369 + 2 * i] + (0 if ds else 0) for i in range(n_ev)]
        assert len(set(lines)) == len(lines), ("one event a line", lines)
        assert DANCERS_LAST_LINE < EV_OBJ_LY < FIRST_BAR_LINE
    finally:
        gb.stop()


# ---- the changes -----------------------------------------------------------------------------------------------------------------------------------------------------------------
def watch_show(gb, r_pat, ref, r_d, bg, show, frames, events):
    """frames of play with `events` {frame: fn}: every picture: below the stage the patron is as he was, and the dancers' pixels are the show's colours."""
    bad = []
    for i in range(frames):
        if i in events:
            events[i]()
        gb.run(1, render=True)
        img = pack(gb.image())
        if r_pat is not None and not (patch(img, r_pat) == patch(ref, r_pat)).all():
            bad.append((i, "patron", int((patch(img, r_pat) != patch(ref, r_pat)).sum())))
        d = [s for s in gb.oam()[28:40] if s["y"]]
        mine = set(np.unique(patch(img, r_d)).tolist()) - bg
        if mine - show:
            bad.append((i, "dancers", sorted(mine - show)))
    return bad


@pytest.mark.parametrize("v", [0, 1, 2, 3, 4, 5, 6, 7])
def test_a_show_starting_and_ending_holds_no_wrong_colour_frame(v, ds):
    gb = play(v, ds)
    try:
        assert inst4_is_obj5(gb)
        lifted_patron(gb)
        gb.run(4)
        gb.run(1, render=True)
        ref = pack(gb.image())
        r_pat = rect(sprites(gb, 5))
        r_d = (8, 8, 152, DANCERS_LAST_LINE + 1)
        bg = set(np.unique(patch(ref, r_d)).tolist())
        show = show_cols(v)
        bad = watch_show(gb, r_pat, ref, r_d, bg, show, 120, {5: lambda: start_show(gb, 60)})        # (the show ends by itself after 60 frames: end_show, and the Saloon's split goes back to its one reload)
        assert not bad, bad[:6]
        assert gb.mem("show_timer") == 0 and gb.mem("pal5_cur") == 0, "over"
        assert gb.pb.memory[0xFFD4] == (1 if v == 0 else 3)
        gb.run(1, render=True)
        assert (patch(pack(gb.image()), r_pat) == patch(ref, r_pat)).all()
        # a second show right after: the same
        bad = watch_show(gb, r_pat, ref, r_d, bg, show, 40, {2: lambda: start_show(gb, 20)})
        assert not bad, bad[:6]
    finally:
        gb.stop()


@pytest.mark.parametrize("v", [0, 3, 5])
def test_the_dancers_come_in_the_same_frame_whether_a_patron_is_lifted_or_not(v):
    gb = play(v, False)
    try:
        lifted_patron(gb)
        start_show(gb)
        gb.run(3)
        assert any(s["y"] for s in gb.oam()[28:40]), "no waiting for him"
    finally:
        gb.stop()


# fades: tests/test_fade_chain.py's scene change with the sprites ON and a show running over a lifted OBJ 5 patron: every pixel of every frame is in a colour of the fade's level
# (the sprites' palettes follow the BG's by a frame, so up to three eighths either side, the unfaded set only in the first step).
def fade_check(old, variant, ds, lift=lifted_patron):
    def setup(gb):
        lift(gb)
        start_show(gb, 600)
        gb.run(10)
    frames, known = scene_change_frames(old, variant, ds, setup=setup, sprites=True)
    sets = level_sets(known)
    faded = 0
    for i, f in enumerate(frames):
        if i > 4 and (f == f.flat[0]).all():                  # (the screen is white: the old scene is gone; the new one's patrons are not this test's)
            break
        best = None
        for k in range(9):                                   # (a tie goes to the deepest fade: a flat HUD is level 0 of its colour, not the unfaded screen)
            for t in (WHITE, AMBER):
                miss = (~np.isin(f[:8], sets[t, k])).sum()   # (the HUD row: no sprites)
                if best is None or miss < best[0]:
                    best = (miss, t, k)
        _, t, k = best
        faded += k < 8
        allowed = sets[t, 8] if k == 8 else np.unique(np.concatenate([sets[t, j] for j in range(max(0, k - 3), min(8 if k >= 6 else 7, k + 3) + 1)]))   # (the first step: the sprites are still the unfaded ones)
        bad = np.nonzero((~np.isin(f, allowed)).any(axis=1))[0]
        assert not len(bad), f"venue {old}, variant {variant}, frame {i} (fade level {k}/8 toward {t:#06x}): scanlines {bad.tolist()[:8]} hold colours of another level"
    assert faded >= 8


@pytest.mark.parametrize("old", [0, 1, 3, 5, 7])
def test_a_fade_to_white_during_a_show_follows_the_screen(old):
    fade_check(old, 1, False)


@pytest.mark.parametrize("old", [0, 2, 5])
def test_a_fade_through_amber_during_a_show_follows_the_screen(old):
    fade_check(old, 2, False)


@pytest.mark.parametrize("old", [0, 5])
def test_a_fade_during_a_show_follows_the_screen_at_double_speed(old):
    fade_check(old, 1, True)
