# M14a: enhanced patron variants (patron review rec. 7; tools/gen_art.py enhanced_group, src/enhance.c). The cowgirl
# (cowboys B) is the first: her top tile row uses BG 7 (S = the venue's bar_b), her bottom row her own BG 3; lifted, her
# left column uses OBJ 4 (cowboys_x) from a re-indexed tile pair in CGB VRAM bank 1, her right column OBJ 6. The gate is
# the M13a one: a lifted patron looks exactly like his BG copy, pixel for pixel, on both models.
import importlib.util
import json

import numpy as np
import pytest

from conftest import ROOT, bar_top_row, title_arcade, venue
from test_art import goto_group
from test_bonus import enter_bonus
from test_bonus2 import PH_END
from test_flow import PLAYING, run_until, state
from test_lift import (HOOK_DROP, HOOK_LIFT, OBJ_BASE, OUT as _M13A, freeze, hook, lift_state, lifted_sprites, pair,
                       run_hooks, screen, step_same, cgb_bg_palette, cgb_obj_palette)
from test_patrons import DRINKING, MAX_P, lineup, put

pytestmark = pytest.mark.timeout(240)

ENH = json.loads((ROOT / "build" / "patron_enh.json").read_text())
PALS = json.loads((ROOT / "assets" / "palettes.json").read_text())
OUT = ROOT / "out" / "m14a"
COWGIRL = 1
BANK1 = 0x08


def rgb15(h):
    r, g, b = (int(h[i:i + 2], 16) for i in (1, 3, 5))
    return (r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10)


def attr_ids(gb, bar, col, n=3):
    return [[gb.pb.memory[1, 0x9800 + (bar_top_row(bar) + r) * 32 + c] & 7 for c in range(col, col + n)] for r in range(2)]


# the cowgirl at all 8 shifts, two per bar (LIFT_PER_BAR), the first four drinking (they sway by 2 px every 12 frames)
SHIFTS = {0: [(16, 0), (49, 1)], 1: [(18, 0), (51, 1)], 2: [(20, 0), (53, 1)], 3: [(22, 0), (55, 1)]}


def place_cowgirls(gb):
    goto_group(gb, 0)
    freeze(gb)
    slots = lineup(gb, {b: [(x, COWGIRL, 0) for x, _ in row] for b, row in SHIFTS.items()})
    return {k: v[0] for k, v in slots.items()}


def start_drinking(gb, i, t0=0):
    """Patron slot i drinks without a mug: he sways by 2 px every 12 frames until his timer reaches 90, then stands."""
    put(gb, "patron_state", i, DRINKING)
    put(gb, "patron_timer", i, t0)
    put(gb, "patron_aux", i, 0)
    put(gb, "patron_mug", i, 255)


# the enhanced set (graphics overhaul, owner round 8b): the cowgirl and robot A, nobody else
EXPECTED = {"cowboys": [COWGIRL], "robots": [0]}


def test_the_enhanced_set_is_the_cowgirl_and_robot_a():
    for g in ENH:
        assert ENH[g]["enhanced"] == EXPECTED.get(g, []), g
        if g not in EXPECTED:
            assert not ENH[g]["bank1"], g
    tab = ENH["cowboys"]["tab"]
    assert (tab[COWGIRL], tab[4 + COWGIRL], tab[8 + COWGIRL], tab[12 + COWGIRL]) == (7, 3, 7, 3), "rows: S / own"
    assert (tab[16 + COWGIRL], tab[20 + COWGIRL]) == (4 | BANK1, 6), "lifted: OBJ 4 from bank 1 | OBJ 6"
    assert tab[0] == tab[4] == 2 and tab[16] == 3, "variant A (the title's patron) is single-palette"
    tab = ENH["robots"]["tab"]
    assert tab[4 + 0] == 7 and tab[0] != 7, "robot A: top row his own palette, bottom row S (the factory's bar_b)"


# every other group's enhanced variant (robot A) through the cowgirl's checks; she has her own tests below
OTHERS = [(gi, g, ENH[g]["enhanced"][0]) for gi, g in enumerate(ENH) if ENH[g]["enhanced"] and g != "cowboys"]


def place_variant(gb, gi, v):
    goto_group(gb, gi)
    freeze(gb)
    slots = lineup(gb, {b: [(x, v, 0) for x, _ in row] for b, row in SHIFTS.items()})
    return {k: s[0] for k, s in slots.items()}


@pytest.mark.parametrize("gi,g,v", OTHERS, ids=[c[1] for c in OTHERS])
def test_enhanced_variant_lifted_equals_bg_at_every_shift(pair, gi, g, v):
    a, b = pair
    slot = None
    for gg in pair:
        slot = place_variant(gg, gi, v)
    step_same(pair, 20)
    for bars in ((0, 1), (2, 3)):
        keys = [(bb, x) for bb in bars for x, _ in SHIFTS[bb]]
        run_hooks(pair, [(slot[k], HOOK_LIFT) for k in keys])
        assert b.mem("lift_total") == 4
        for gg in pair:
            for j, k in enumerate(keys):
                start_drinking(gg, slot[k], 3 * j)
        step_same(pair, 40)
        run_hooks(pair, [(slot[k], HOOK_DROP) for k in keys])
        assert b.mem("lift_total") == 0
        step_same(pair, 40)
    assert a.bg_tilemap() == b.bg_tilemap()


@pytest.mark.parametrize("gi,g,v", OTHERS, ids=[c[1] for c in OTHERS])
def test_enhanced_variant_rows_attributes_lift_and_palettes(gb, gi, g, v):
    slot = place_variant(gb, gi, v)
    gb.run(30, render=True)
    tab = ENH[g]["tab"]
    if gb.model_name == "cgb":
        for (bb, x) in slot:
            assert attr_ids(gb, bb, x >> 3) == [[tab[v]] * 3, [tab[4 + v]] * 3], (bb, x)
        assert cgb_obj_palette(gb, 4)[1:] == [rgb15(h) for h in PALS[f"{g}_x"]["hex"]]
        for t, data in ENH[g]["bank1"].items():
            assert bytes(gb.pb.memory[1, 0x8000 + int(t) * 16:0x8000 + int(t) * 16 + 32]) == bytes(data)
    ref = screen(gb)
    keys = [(0, 16), (0, 49), (1, 18), (1, 51)]
    for k in keys:
        hook(gb, slot[k], HOOK_LIFT)
        for _ in range(4):
            gb.run(1, render=True)
            assert (screen(gb) == ref).all()
    spr = lifted_sprites(gb)
    assert len(spr) == 8
    for sp in spr:
        left = (sp["tile"] - OBJ_BASE) % 6 == 0
        if gb.model_name == "cgb":
            assert sp["flags"] & 0x0F == (tab[16 + v] if left else tab[20 + v]), sp
        else:
            assert sp["flags"] & 0x10 and not sp["flags"] & BANK1, sp
    for k in keys:
        hook(gb, slot[k], HOOK_DROP)
        for _ in range(4):
            gb.run(1, render=True)
            assert (screen(gb) == ref).all()


def test_the_lifted_cowgirl_looks_exactly_like_her_bg_copy_at_every_shift(pair):
    """Two games side by side (a: nobody lifted, b: lifts). All 8 shifts in two rounds of four lifts (bars 0-1, then
    2-3); once lifted each round's four start drinking, so they sway (shift s <-> s + 2) while lifted and while being
    dropped. Every frame of the two must be the same picture (CGB and DMG). (Their sway timers are staggered by 3
    frames: four BG patrons swaying on the same frame make the reference game's copy list spill into the next VBlank,
    a frame's lag of its BG picture that has nothing to do with the look; it happens with any variant.)"""
    a, b = pair
    slot = None
    for g in pair:
        slot = place_cowgirls(g)
    step_same(pair, 20)
    for bars in ((0, 1), (2, 3)):
        keys = [(bb, x) for bb in bars for x, _ in SHIFTS[bb]]
        run_hooks(pair, [(slot[k], HOOK_LIFT) for k in keys])
        assert b.mem("lift_total") == 4
        for g in pair:
            for j, k in enumerate(keys):
                start_drinking(g, slot[k], 3 * j)
        step_same(pair, 40)
        run_hooks(pair, [(slot[k], HOOK_DROP) for k in keys])
        assert b.mem("lift_total") == 0
        step_same(pair, 40)                           # (the sway ends)
    assert a.bg_tilemap() == b.bg_tilemap()


def test_cowgirl_rows_attributes_and_lift_attributes(gb):
    """BG: top row BG 7, bottom row BG 3 at every shift (CGB). Lifted: left entry OBJ 4 + bank 1, right OBJ 6 (CGB); DMG:
    OBP1 and never the bank bit. Zero changed pixels through the lift and the drop. x4 screenshots -> out/m14a/."""
    slot = place_cowgirls(gb)
    gb.run(30, render=True)
    if gb.model_name == "cgb":
        for (b, x) in slot:
            assert attr_ids(gb, b, x >> 3) == [[7] * 3, [3] * 3], (b, x)
    OUT.mkdir(parents=True, exist_ok=True)
    gb.screenshot(OUT / f"saloon_cowgirl_bg.{gb.model_name}.png", 4)
    ref = screen(gb)
    keys = [(0, 16), (0, 49), (1, 18), (1, 51)]
    for k in keys:
        hook(gb, slot[k], HOOK_LIFT)
        for i in range(4):
            gb.run(1, render=True)
            assert (screen(gb) == ref).all(), f"lift {k} frame {i}"
    assert all(lift_state(gb)[slot[k]] == 1 for k in keys)
    spr = lifted_sprites(gb)
    assert len(spr) == 8
    for s in spr:
        left = (s["tile"] - OBJ_BASE) % 6 == 0
        assert s["tile"] - OBJ_BASE in (6 * COWGIRL, 6 * COWGIRL + 2)
        if gb.model_name == "cgb":
            assert s["flags"] & 0x0F == ((4 | BANK1) if left else 6), s
        else:
            assert s["flags"] & 0x10 and not s["flags"] & BANK1, s
    gb.screenshot(OUT / f"saloon_cowgirl_lifted.{gb.model_name}.png", 4)
    gb.write(0xFF40, gb.mem(0xFF40) & ~2)          # sprites off for a frame: the BG alone (plain wall under the lifted)
    gb.run(1, render=True)
    gb.screenshot(OUT / f"saloon_cowgirl_lifted_bg_only.{gb.model_name}.png", 4)
    gb.write(0xFF40, gb.mem(0xFF40) | 2)
    gb.run(1, render=True)
    assert (screen(gb) == ref).all()
    for k in keys:
        hook(gb, slot[k], HOOK_DROP)
        for i in range(4):
            gb.run(1, render=True)
            assert (screen(gb) == ref).all(), f"drop {k} frame {i}"
    assert lifted_sprites(gb) == []


def bank1_ok(gb):
    for t, data in ENH["cowboys"]["bank1"].items():
        assert bytes(gb.pb.memory[1, 0x8000 + int(t) * 16:0x8000 + int(t) * 16 + 32]) == bytes(data), f"bank-1 tiles {t}"


def palettes_ok(gb):
    x = [rgb15(h) for h in PALS["cowboys_x"]["hex"]]
    assert cgb_obj_palette(gb, 4)[1:] == x, "OBJ 4 = cowboys_x"
    assert cgb_bg_palette(gb, 7) == venue("saloon")["pal"][3], "BG 7 = the saloon's bar_b (S)"
    assert venue("saloon")["pal"][3][0] == venue("saloon")["pal"][2][0], "S colour 0 = the wall"
    s = [rgb15(h) for h in json.loads((ROOT / "assets/approved/venues/saloon_pal.json").read_text())["bar_b"]["hex"]]
    assert cgb_bg_palette(gb, 7) == s


def test_bank1_tiles_and_extra_palettes_after_the_title(boot):
    """From the title (which loads the saloon and its own palettes) to level 1, the saloon."""
    from test_flow import PLAYING, run_until, state
    gb = boot
    title_arcade(gb)
    run_until(gb, lambda: state(gb) == PLAYING, 60)
    assert gb.mem("cur_group") == 0
    if gb.model_name == "dmg":
        assert list(gb.read("lift_prop", 8)) == [0x10] * 8, "DMG: OBP1, never the VRAM bank bit"
        return
    assert list(gb.read("lift_prop", 8)) == [3, 4 | BANK1, 7, 3, 3, 6, 7, 3]
    bank1_ok(gb)
    palettes_ok(gb)


@pytest.mark.parametrize("rounds_before", [0, 1, 2], ids=["shake_up", "pour", "tips"])
def test_bank1_tiles_and_extra_palettes_are_back_after_each_bonus_round(gb, rounds_before):
    enter_bonus(gb, 18, rounds_before)               # level 18 (zoo) -> bonus -> level 19 (cowboys, loop 3)
    assert gb.mem("bonus_kind") == rounds_before
    gb.run(30)
    gb.write("bonus_phase", PH_END)                 # (as test_bonus2.finish, then the "LOOP 3" banner)
    gb.write("bonus_timer", 129)
    run_until(gb, lambda: state(gb) == PLAYING, 600)
    gb.run(2)
    assert gb.mem("cur_group") == 0 and gb.mem("level") == 19
    if gb.model_name == "dmg":
        assert list(gb.read("lift_prop", 8)) == [0x10] * 8
        return
    bank1_ok(gb)
    palettes_ok(gb)
    for v in range(3):
        assert cgb_obj_palette(gb, (3, 6, 7)[v])[1:] == cgb_bg_palette(gb, 2 + v)[1:]


# ---- the validator (tools/gen_art.py) ---------------------------------------------------------------------------
def _gen_art():
    spec = importlib.util.spec_from_file_location("gen_art", ROOT / "tools" / "gen_art.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _cowgirl():
    rows = [l for l in (ROOT / "assets/art/patrons/cowboys.txt").read_text().splitlines() if l and not l.startswith(";")]
    return rows[16:32]


def _pals(ga):
    t = [ga.r15(h) for h in json.loads((ROOT / "assets/approved/venues/saloon_pal.json").read_text())["bar_b"]["hex"][1:]]
    own = [[ga.r15(h) for h in PALS[f"cowboys_{v}"]["hex"]] for v in "abc"]
    objs = {3: own[0], 6: own[1], 7: own[2], 4: [ga.r15(h) for h in PALS["cowboys_x"]["hex"]]}
    return t, own[1], objs


def test_validator_accepts_the_cowgirl():
    ga = _gen_art()
    t, b, objs = _pals(ga)
    art = _cowgirl()
    ga.check_rows("cowgirl", art, t, b)
    cols = ga.lift_columns("cowgirl", art, t, b, objs, 6)
    assert cols[0][0] == 4 | BANK1 and cols[1] == (6, None)


def test_validator_rejects_a_bad_quadrant():
    """A skin pixel in the top-left quadrant: the left column would need skin, hair, rose and dark (4 colours)."""
    ga = _gen_art()
    t, b, objs = _pals(ga)
    art = _cowgirl()
    art[5] = art[5][:4] + "-" + art[5][5:]           # (x 4, y 5): hair -> skin
    with pytest.raises(ga.ArtError, match="left column .* has 4 colours"):
        ga.lift_columns("bad", art, t, b, objs, 6)


def test_validator_rejects_a_column_no_obj_palette_holds():
    ga = _gen_art()
    t, b, objs = _pals(ga)
    del objs[4]                                      # no cowboys_x: hair + rose + dark are in no OBJ palette
    with pytest.raises(ga.ArtError, match="left column .* no OBJ palette"):
        ga.lift_columns("bad", _cowgirl(), t, b, objs, 6)


def test_validator_rejects_a_shared_colour_at_another_index_and_holes():
    ga = _gen_art()
    t, b, objs = _pals(ga)
    art = _cowgirl()
    with pytest.raises(ga.ArtError, match="index 1 in the top-row palette but 2"):
        ga.check_rows("bad", art, t, [b[1], b[0], b[2]])
    holey = list(art)
    holey[13] = holey[13][:3] + "." + holey[13][4:]   # a pixel of her rose top -> index 0, enclosed
    with pytest.raises(ga.ArtError, match="index 0 inside the figure"):
        ga.check_rows("bad", holey, t, b)


def test_cowgirl_back_view_rows(gb):
    """Her back view (watching the show): top row BG 7, bottom row BG 3 too (CGB); the others stay single-palette."""
    goto_group(gb, 0)
    freeze(gb)
    lineup(gb, {0: [(80, 0, 0)], 2: [(80, 2, 0)], 3: [(24, 0, 1), (48, COWGIRL, 1), (88, 2, 1)]})
    gb.run(30)
    if gb.model_name == "cgb":
        assert attr_ids(gb, 3, 3, 2) == [[2, 2], [2, 2]]
        assert attr_ids(gb, 3, 6, 2) == [[7, 7], [3, 3]]
        assert attr_ids(gb, 3, 11, 2) == [[4, 4], [4, 4]]
