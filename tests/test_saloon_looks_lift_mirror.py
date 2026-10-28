# The Saloon's Color-only looks (3-7, tiles in VRAM bank 1, OBJ palette instances 3 and 4 as sprites) lifted and mirrored. test_lift.py's
# patron sets and test_classic.py's mirror scene only ever put looks 0-2 on screen; here the same checks run with looks 3-7:
#   - lift and drop change no pixel, the two sprites use the look's bank-1 tiles, his OBJ palette and VRAM bank 1 (flags bit 3);
#   - an R level draws the same scene as the L level mirrored, pixel for pixel, with those looks walking, drinking, pushed and lifted.
import pytest
from conftest import bar_top_y
from test_lift import HOOK_DROP, HOOK_LIFT, LIFT_PAL, boot_play, freeze, hook, lifted_sprites, lift_state, obj_tile_of, screen
from test_patrons import MAX_P, WALKING, lineup, patrons
import test_classic as tc

pytestmark = [pytest.mark.only_model("cgb"), pytest.mark.timeout(240)]


@pytest.fixture(params=["cgb"])
def model(request):
    return request.param


def variant(look, inst):
    """patron_variant as the game builds it: look | ((look ^ palette instance) & 7) << 3 | bank 1 (bit 6) for the looks 3-7."""
    return look | (((look ^ inst) & 7) << 3) | (0x40 if look > 2 else 0)


COMBOS = [(3, 0), (3, 4), (4, 3), (4, 2), (5, 1), (5, 4), (6, 0), (6, 4), (7, 2), (7, 3)]    # real (look, instance) pairs of the Palette Plan


@pytest.mark.parametrize("look,inst", COMBOS, ids=[f"look{lk}-inst{i}" for lk, i in COMBOS])
def test_a_lifted_color_only_look_changes_no_pixel_and_wears_bank_1(model, look, inst):
    gb = boot_play("cgb")
    try:
        assert gb.mem("cur_group") == 0
        freeze(gb)
        gb.run(4)
        spec = {}
        first = None
        for p in sorted(patrons(gb), key=lambda p: p["i"]):
            v = gb.read("patron_variant", MAX_P)[p["i"]]
            if first is None and p["state"] == WALKING:
                first, v = p["i"], variant(look, inst)
            spec.setdefault(p["bar"], []).append((p["x"], v, 0))
        assert first is not None
        lineup(gb, spec)
        gb.run(8, render=True)
        ref = screen(gb)
        tm0 = gb.bg_tilemap()
        assert gb.read("patron_variant", MAX_P)[first] == variant(look, inst)
        x, bar = gb.read("patron_x", MAX_P)[first], gb.read("patron_bar", MAX_P)[first]
        hook(gb, first, HOOK_LIFT)
        for i in range(12):
            gb.run(1, render=True)
            assert (screen(gb) == ref).all(), f"lift frame {i}"
        assert gb.mem("lift_hook_res") == 1 and lift_state(gb)[first] == HOOK_LIFT
        spr = lifted_sprites(gb)
        assert sorted((s["x"] - 8, s["tile"]) for s in spr) == [(x, obj_tile_of(look)), (x + 8, obj_tile_of(look) + 2)]
        assert all(s["y"] - 16 == bar_top_y(bar) for s in spr)
        assert all(s["flags"] & 0x0F == LIFT_PAL[inst] | 8 for s in spr), [hex(s["flags"]) for s in spr]
        hook(gb, first, HOOK_DROP)
        for i in range(12):
            gb.run(1, render=True)
            assert (screen(gb) == ref).all(), f"drop frame {i}"
        assert lift_state(gb)[first] == 0 and lifted_sprites(gb) == []
        assert gb.bg_tilemap() == tm0
    finally:
        gb.stop()


LOOK_SETS = {"looks345": {0: variant(3, 4), 1: variant(4, 3), 2: variant(5, 4)},
             "looks673": {0: variant(6, 0), 1: variant(7, 2), 2: variant(3, 0)}}


@pytest.mark.parametrize("name", list(LOOK_SETS))
def test_the_color_only_looks_mirror_pixel_for_pixel_on_an_r_level(model, name):
    """Every bar R: the all-L scene's picture mirrored, on 30 frames: walkers, drinkers with mugs, a back-view watcher, a pushed patron
    and one lifted patron, all of them Color-only looks."""
    looks = LOOK_SETS[name]
    a, b = tc.pair("cgb", tc.ALL_R)
    try:
        lp = tc.scene(a, looks=looks)
        assert tc.scene(b, looks=looks) == lp
        tc.run_both(a, b, 6)
        assert a.mem("lift_hook_res") == 1 and b.mem("lift_hook_res") == 1
        seen = {int(v) & 7 for v in b.read("patron_variant", MAX_P)}
        assert seen >= {v & 7 for v in looks.values()}, seen
        assert lifted_sprites(b) and all(s["flags"] & 8 for s in lifted_sprites(b)), "the lifted one is a bank-1 sprite"
        mi = tc.Mirror(a, b, tc.ALL_R)
        mi.check()
        for f in range(30):
            tc.run_both(a, b, 1)
            bad = mi.check()
            assert not bad, (f, bad)
        assert b.mem("mir_short") == 0
    finally:
        tc.close(a, b)
