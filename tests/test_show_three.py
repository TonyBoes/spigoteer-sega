# Three show palettes and the dance's step table (owner 2026-11-02, Q13 option A and Q12).
#   - Color: the Saloon's three dancers each wear their own OBJ palette (left OBJ 5, middle OBJ 4, right OBJ 3: purple, red, teal; skin and black shared). OBJ 5's is written in the VBlank, OBJ 3's and 4's in the
#     HBlanks of lines 4 and 5 (src/main.c _split_put_o, game.h EV_OBJS); below the stage each slot's patron colours go back, one palette an HBlank, lines 34, 35, 36 (EV_OBJ). The patrons that wear those
#     slots below the stage keep their own colours in the same frame.
#   - Both models: the dance steps through the venue's step table (tools/gen_art.py step_rows, src/rom0_relief.c dance_next): the Saloon shows its front pose once, then loops hop, kick left, hop, kick right
#     (frames 2 3 2 1); every other venue dances 0 1 2 3 as ever.
#   - Show start, end and a screen fade with three palettes: no wrong-colour frame.
import contextlib

import numpy as np
import pytest

from wash_helpers import wash_colours
from conftest import ROOT, double_speed, venue as venue_art, THEMES
from test_art import goto_group
from test_fade_chain import pack
from test_lift import HOOK_LIFT, boot_play, freeze, hook
from test_patrons import lineup, clear_patrons
from test_show_obj5 import (DANCERS_LAST_LINE, FIRST_BAR_LINE, EV_OBJ_LY, fade_check, patch, play, rect, rgb555, sprites, start_show, end_show, watch_show)
from test_story import call_banked
from test_venues import cgb_palette

OBJ5, OBJ4, OBJ3 = 5, 4, 3
SHOW_SLOT = [OBJ5, OBJ4, OBJ3]          # left, middle, right dancer
DANCER_X = [24, 72, 120]                 # src/rom0_relief.c dancer_x
EV_OBJS_LY = 4
MODEL = pytest.mark.only_model("cgb")


@pytest.fixture(params=[False, True], ids=["normal", "double"])
def ds(request):
    return request.param


def lift_three(gb):
    """Three patrons on bar 0, lifted: one in each of OBJ 3, OBJ 4 and OBJ 5 (the Saloon's palette instances 0, 3, 4). Returns [(slot, obj palette)]."""
    freeze(gb)
    clear_patrons(gb)
    gb.run(2)
    got = lineup(gb, {0: [(24, 4 << 3, 0)], 1: [(72, 3 << 3, 0)], 2: [(120, 0, 0)]})
    gb.run(6)
    out = []
    for key, pal in (((0, 24), OBJ5), ((1, 72), OBJ4), ((2, 120), OBJ3)):
        hook(gb, got[key][0], HOOK_LIFT)
        gb.run(6)
        assert gb.mem("lift_hook_res") == 1, ("lifted", key)
        out.append((got[key][0], pal))
    return out


def three_pals():
    return [[int(c) for c in p[1:]] for p in venue_art(0)["show_pals"]]       # skin, dress, black


# ---- the data ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
def test_the_saloon_lists_three_palettes_and_the_others_one():
    for i, t in enumerate(THEMES):
        v = venue_art(t)
        assert v["show_pal_n"] == (3 if t in ("saloon", "bistro") else 1), t
        assert v["pal"][6] == v["show_pals"][0], "the venue's show palette is the first (the left dancer's, OBJ 5)"
    pals = three_pals()
    assert [p[1] for p in pals] != [pals[0][1]] * 3 and len({p[0] for p in pals}) == 1 and len({p[2] for p in pals}) == 1, "skin and black shared, three dresses"


def test_the_step_tables_are_in_the_venue_data():
    """Rows 4-5 of a dance venue's show table (src/rom0_relief.c): [n | (intro + 1) << 4, loop frames 2 bits each]; the Saloon has an intro."""
    for t in THEMES:
        v = venue_art(t)
        if v["show_band"]:
            continue
        tab = v["show_table"][4] + v["show_table"][5]
        n, intro = tab[0] & 15, tab[0] >> 4
        loop = [(tab[1 + (i >> 2)] >> (2 * (i & 3))) & 3 for i in range(n)]
        if t == "saloon":
            assert (intro - 1, loop) == (0, [2, 3, 2, 1]), "front once, then hop, kick left, hop, kick right"
        else:
            assert (intro, loop) == (0, [0, 1, 2, 3]), t


# ---- the dance's steps ---------------------------------------------------------------------------------------------------------------------------------------------------------
def dance_frames(gb, beats):
    """The dancer_frame seen every frame from the show's start, repeats collapsed."""
    seen = []
    for _ in range(12 * beats + 6):
        gb.run(1)
        f = gb.mem("dancer_frame")
        if not seen or seen[-1] != f:
            seen.append(f)
    return seen


@pytest.mark.parametrize("v", range(10))
def test_the_dance_follows_the_venue_s_step_table(v, request):
    model = "cgb" if request.config.getoption("--model", default="cgb") != "dmg" else "dmg"
    gb = boot_play(model)
    try:
        if v:
            goto_group(gb, v)
        gb.run(10)
        freeze(gb)
        gb.write("show_timer", 0)
        gb.write(gb.addr("show_timer") + 1, 0)
        call_banked(gb, "start_show")
        assert gb.mem16("show_timer") > 0, "the show started"
        seen = dance_frames(gb, 9)
        want = [0, 2, 3, 2, 1, 2, 3, 2, 1, 2] if v == 0 else [0, 1, 2, 3, 0, 1, 2, 3, 0, 1]
        assert seen[:len(want)] == want, (v, seen)
    finally:
        gb.stop()


# ---- the picture -----------------------------------------------------------------------------------------------------------------------------------------------------------------
@MODEL
def test_each_dancer_wears_her_own_colours_and_each_patron_below_his_in_the_same_frame(ds):
    gb = play(0, ds)
    try:
        lifted = lift_three(gb)
        for p, pal in lifted:
            assert sprites(gb, pal), f"the patron on OBJ {pal} is lifted"
        gb.run(4)
        gb.run(1, render=True)
        before = pack(gb.image())
        pat_rects = [rect(sprites(gb, pal)) for _, pal in lifted]
        pat_cols = [set(rgb555(gb, base)[1:]) for base in ()] or None
        start_show(gb, 400)
        gb.run(30)
        gb.run(1, render=True)
        during = pack(gb.image())
        assert gb.mem("pal5_cur") == 3 and gb.pb.memory[gb.addr("story_scratch") + 226] & 7 == 7, "three palettes on, all three give-backs differ from the show's"
        pals = three_pals()
        for k in range(3):
            r = (DANCER_X[k], 8, DANCER_X[k] + 16, DANCERS_LAST_LINE + 1)
            bg = set(np.unique(patch(before, r)).tolist()) | wash_colours(0)
            mine = set(np.unique(patch(during, r)).tolist()) - bg
            assert mine, f"dancer {k} is on the picture"
            assert mine <= set(pals[k]), (k, "pixels in colours that are not her palette's", sorted(mine - set(pals[k])), pals[k])
            assert pals[k][1] in mine, (k, "her dress colour shows", pals[k], sorted(mine))
            for j in range(3):
                if j != k and pals[j][1] != pals[k][1]:
                    assert pals[j][1] not in mine, (k, "not her neighbour's dress")
        for (p, pal), r in zip(lifted, pat_rects):
            assert int(r[1]) >= FIRST_BAR_LINE
            assert (patch(during, r) == patch(before, r)).all(), f"the patron on OBJ {pal} below the stage: the same pixels, show or no show"
    finally:
        gb.stop()


@MODEL
def test_the_dancers_use_three_palette_slots(ds):
    gb = play(0, ds)
    try:
        start_show(gb, 400)
        gb.run(20)
        got = [sorted({s["flags"] & 7 for s in gb.oam()[28 + 4 * k:32 + 4 * k] if s["y"]}) for k in range(3)]
        assert got == [[OBJ5], [OBJ4], [OBJ3]], got
    finally:
        gb.stop()


# ---- the hardware ----------------------------------------------------------------------------------------------------------------------------------------------------------------
@MODEL
def test_the_five_writes_of_a_frame_are_each_in_their_own_hblank_and_never_in_mode_3(ds):
    """The show's OBJ 3 and OBJ 4 at lines 4 and 5 (before the dancers' first line, 8), the give-backs of OBJ 5, 4, 3 at 34, 35, 36 (after the dancers' last, 31, before the first bar's, 40): one palette an HBlank, one line each."""
    gb = play(0, ds)
    try:
        log = []

        def hook_at(name):
            a = gb.addr(name)

            def cb(_):
                m = gb.pb.memory
                log.append((name, m[0xFF44], m[0xFF41] & 3, gb.pb.register_file.A))
            gb.pb.hook_register(a >> 16, a & 0xFFFF, cb, None)
        for n in ("split_put_o", "split_put_oe"):
            hook_at(n)
        gb.run(5)
        start_show(gb, 400)
        gb.run(5)
        log.clear()
        n = 90
        gb.run(n)
        ent = [x for x in log if x[0] == "split_put_o"]
        ext = [x for x in log if x[0] == "split_put_oe"]
        assert len(ent) == len(ext) and 5 * (n - 3) <= len(ent) <= 5 * (n + 3), ("five writes a frame", len(ent), n)
        assert all(x[2] == 0 for x in ent), ("every write starts in HBlank", sorted({(x[1], x[2]) for x in ent}))
        assert all(x[2] in (0, 2) for x in ext), ("and ends in HBlank or the next line's OAM scan, never in mode 3", sorted({(x[1], x[2]) for x in ext}))
        by_ocps = {}
        for x in ent:
            by_ocps.setdefault(x[3], set()).add(x[1])
        # OCPS: 0xE8 OBJ 5, 0xE0 OBJ 4, 0xD8 OBJ 3; each is written twice a frame: the show's (OBJ 3 line 4, OBJ 4 line 5) and the give-back (OBJ 5 34, OBJ 4 35, OBJ 3 36)
        assert by_ocps == {0xE8: {EV_OBJ_LY - 1}, 0xE0: {EV_OBJS_LY + 1, EV_OBJ_LY}, 0xD8: {EV_OBJS_LY, EV_OBJ_LY + 1}}, by_ocps
        lines = sorted({x[1] for x in ent})
        assert lines == [4, 5, 34, 35, 36], lines
        assert EV_OBJS_LY + 1 < 8 and DANCERS_LAST_LINE < 34 and 36 < FIRST_BAR_LINE
        sc = gb.addr("story_scratch")
        m = gb.pb.memory
        ev = [m[sc + 369 + 2 * i] for i in range(m[sc + 286])]
        assert len(set(ev)) == len(ev), ("one event a line", ev)
    finally:
        gb.stop()


# ---- the changes -----------------------------------------------------------------------------------------------------------------------------------------------------------------
@MODEL
def test_a_show_starting_and_ending_with_three_palettes_holds_no_wrong_colour_frame(ds):
    gb = play(0, ds)
    try:
        lifted = lift_three(gb)
        gb.run(4)
        gb.run(1, render=True)
        ref = pack(gb.image())
        r_pats = [rect(sprites(gb, pal)) for _, pal in lifted]
        bg = set(np.unique(patch(ref, (8, 8, 152, DANCERS_LAST_LINE + 1))).tolist()) | wash_colours(0)
        show = {c for p in three_pals() for c in p}
        bad = []
        for i in range(130):
            if i == 5:
                start_show(gb, 60)                      # (it ends by itself after 60 frames)
            if i == 100:
                start_show(gb, 20)                      # (and a second one after)
            gb.run(1, render=True)
            img = pack(gb.image())
            for r in r_pats:
                if not (patch(img, r) == patch(ref, r)).all():
                    bad.append((i, "patron", r))
            mine = set(np.unique(patch(img, (8, 8, 152, DANCERS_LAST_LINE + 1))).tolist()) - bg
            if mine - show:
                bad.append((i, "dancers", sorted(mine - show)))
        assert not bad, (len(bad), bad[:2], bad[-2:])
        gb.run(60)
        assert gb.mem("show_timer") == 0 and gb.mem("pal5_cur") == 0 and gb.pb.memory[gb.addr("story_scratch") + 226] == 0, "over"
        gb.run(1, render=True)
        img = pack(gb.image())
        assert all((patch(img, r) == patch(ref, r)).all() for r in r_pats)
        # the give-backs held: the three slots are the patrons' again
        for (p, pal) in lifted:
            assert cgb_palette(gb, pal, obj=True)[1:] != [int(c) for c in three_pals()[SHOW_SLOT.index(pal)]], pal
    finally:
        gb.stop()


@MODEL
@pytest.mark.parametrize("variant", [1, 2])
def test_a_screen_fade_during_a_show_with_three_palettes_follows_the_screen(variant):
    fade_check(0, variant, False, lift=lift_three)


@MODEL
def test_a_screen_fade_during_a_show_with_three_palettes_follows_the_screen_at_double_speed():
    fade_check(0, 1, True, lift=lift_three)
