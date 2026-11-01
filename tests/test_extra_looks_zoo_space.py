# The Jungle Zoo's and the Space Lounge's Color-only extra looks on the Graphics Atlas slots (docs/dev/queue_briefs/extra_looks_slots.md), as test_extra_looks.py does for the Factory:
#   - the generated (look, palette instance) table (tools/gen_looks.py, build/looks.c, looks_pick.h) is the plan's: the Zoo 5 instances (OBJ 1, 6, 7, 3, 4 on BG 2, 6, 7, 3, 4),
#     23 combinations; the Space Lounge 7 (OBJ 1, 2, 7, 3, 5, 4, 6 on BG 2, 0, 7, 5, 3, 4, 6), 42 combinations (a fight leaves out OBJ 4 and 7 and look 2);
#   - the instances sit where the table says, the five extra looks are the owner's art in VRAM bank 1, spawn only in allowed pairs;
#   - a lifted extra look changes no pixel and wears its OBJ palette and bank 1; an R level mirrors them pixel for pixel; the DMG keeps looks 0-2.
import json
import re
import sys

import pytest
from conftest import ROOT
from test_art import goto_group
from test_lift import HOOK_DROP, HOOK_LIFT, boot_play, freeze, hook, lifted_sprites, lift_state, obj_tile_of, screen
from test_patrons import MAX_P, WALKING, lineup, patrons
from test_venues import cgb_palette
import test_classic as tc

sys.path.insert(0, str(ROOT / "tools"))
import gen_looks as GL  # noqa: E402
import extra_combos as EC  # noqa: E402

pytestmark = [pytest.mark.only_model("cgb"), pytest.mark.timeout(240)]

GROUP = {"zoo": 8, "aliens": 9}
WANT = {"zoo": dict(looks=["COCO", "BAMBOO", "MUDDY", "TUCO", "ELLIE", "ZIGGY", "PINKY", "RAJA"], order=[1, 6, 7, 3, 4], bg=[2, 6, 7, 3, 4], combos=23, boss=14),
        "aliens": dict(looks=["ZORP", "XENO", "GLORP", "DASH", "MOTHMA", "GLOP", "LUNA", "VENUS"], order=[1, 2, 7, 3, 5, 4, 6], bg=[2, 0, 7, 5, 3, 4, 6], combos=42, boss=23)}
EXTRAS = {"zoo": ["tuco", "ellie", "ziggy", "pinky", "raja"], "aliens": ["dash", "mothma", "glop", "luna", "venus"]}
PALS = json.loads((ROOT / "assets" / "palettes.json").read_text())
VENUES = ["zoo", "aliens"]


@pytest.fixture(params=["cgb"])
def model(request):
    return request.param


def variant(look, inst):
    return look | (((look ^ inst) & 7) << 3) | (0x40 if look > 2 else 0)


def looks_c(v):
    txt = (ROOT / "build" / "looks_pick.h").read_text()
    g = GROUP[v]

    def arr(name):
        m = re.search(name + r"_%d\[\d+\] = \{ (.*?) \};" % g, txt)
        return [int(h, 16) for h in re.findall(r"0x([0-9A-F]{2})", m.group(1))]
    return arr("combo"), arr("boss")


def game(v, model_name="cgb"):
    gb = boot_play(model_name)
    goto_group(gb, GROUP[v])
    gb.write("tip_chance", 0)
    return gb


def scratch(gb, at, n):
    return [gb.read(gb.addr("story_scratch") + at + i, 1)[0] for i in range(n)]


# ---- the table -----------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("v", VENUES)
def test_the_combos_are_the_plans_table(v):
    w = WANT[v]
    t = GL.venue_tables(v)
    looks, inst, allowed = EC.venue_table(v)
    assert t["looks"] == looks == w["looks"]
    assert t["order"] == w["order"] and t["bg"] == w["bg"] and t["dropped"] == [] and set(inst) == set(t["order"]), "all of the plan's instances are in"
    if 5 in t["order"]:
        assert t["order"].index(5) == 4, "instance 4 is OBJ 5: the show's slot"
    want = [(li, pi) for li, n in enumerate(looks) for pi, o in enumerate(t["order"]) if o in allowed[n]]
    assert t["combo"] == want and len(want) == w["combos"]
    own = (4, 7)                                # a fight: the boss body is BG 4, the topper OBJ 7 (BG 4 holds OBJ 4's palette); look 2 is the boss's
    assert t["boss"] == [(l, p) for l, p in want if l != 2 and t["order"][p] not in own] and len(t["boss"]) == w["boss"]
    combo, boss = looks_c(v)
    spread = lambda lst: [GL.V(*lst[r * len(lst) >> 8]) for r in range(256)]       # (the pick indexes by the random byte itself: r * n >> 8)
    assert combo == spread(want), "build/looks_pick.h is this table"
    assert boss == spread(t["boss"])


@pytest.mark.parametrize("v", VENUES)
def test_each_instance_sits_on_the_atlas_slots_with_the_atlas_colours(v):
    """Against plan_slots.json (the Atlas's export): the instance's OBJ slot lists its patrons, its BG slot lists the same patrons (the Space Lounge's XENO on the bar's BG 0 and
    VENUS on BG 3 are plan_data BG_PAIR: the Atlas lists both on its BG 3), and the colours the game puts there are the Atlas's."""
    t = GL.venue_tables(v)
    atlas = GL.SLOTS[v]
    rgb5 = lambda hexs: [(int(h[1:3], 16) >> 3, int(h[3:5], 16) >> 3, int(h[5:7], 16) >> 3) for h in hexs]
    for pi, (o, bg, pal) in enumerate(zip(t["order"], t["bg"], t["pal"])):
        assert atlas["obj"][str(o)]["patrons"], (pi, o)
        if pal[0] == "pal":
            assert rgb5(PALS[pal[1]]["hex"]) == rgb5(atlas["obj"][str(o)]["cols"][1:]), (pi, pal)
        if (v, o) != ("aliens", 5) and (v, o) != ("aliens", 2):
            assert sorted(atlas["bg"][str(bg)]["patrons"]) == sorted(atlas["obj"][str(o)]["patrons"]), (pi, o, bg)
            assert rgb5(atlas["bg"][str(bg)]["cols"][1:]) == rgb5(atlas["obj"][str(o)]["cols"][1:]), (pi, "BG twin")


@pytest.mark.parametrize("v", VENUES)
def test_the_art_is_the_owners(v):
    for suffix in ("", "_back"):
        txt = (ROOT / "assets" / "art" / "patrons" / f"{v}_x{suffix}.txt").read_text()
        blocks = [[r for r in b.splitlines() if r and not r.startswith(";")] for b in txt.split("\n\n")]
        blocks = [b for b in blocks if b]
        assert len(blocks) == 5
        for b, name in zip(blocks, EXTRAS[v]):
            src = [r for r in (ROOT / "tools" / "artifacts" / "palette_plan" / "art" / f"{v}_{name}{suffix}.txt").read_text().splitlines() if r and not r.startswith(";")]
            assert b == src, (name, suffix)
            assert all(set(r) <= set(".-+#") and len(r) == 16 for r in b)


def test_the_new_palettes_are_the_plans():
    want = {"zoo_tuco": ["#f8f8e8", "#f89820", "#101018"], "zoo_pinky": ["#f8b0c8", "#e04880", "#301020"], "aliens_dash": ["#f8e0c8", "#e03830", "#301818"],
            "aliens_mothma": ["#f8f0d0", "#c8a068", "#382010"], "aliens_luna": ["#f0f0f8", "#40b8a8", "#100820"]}
    for k, hx in want.items():
        assert PALS[k]["hex"] == hx
        assert PALS[k]["rgb15"] == [int(h[1:3], 16) >> 3 | (int(h[3:5], 16) >> 3) << 5 | (int(h[5:7], 16) >> 3) << 10 for h in hx]


# ---- the game ------------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("v", VENUES)
def test_the_game_loads_its_instances_where_the_table_says(v, model):
    gb = game(v)
    try:
        t = GL.venue_tables(v)
        n = len(t["order"])
        assert scratch(gb, 254, n) == t["order"] and scratch(gb, 262, n) == t["bg"]
        assert gb.read(0xFFD4, 1)[0] == 3, "the mid-frame chain is on (SPLIT_ON 3)"
        for o, b in zip(t["order"], t["bg"]):
            if b in (1,):
                continue
            got = cgb_palette(gb, b)[1:] if b not in (5, 6) else None
            if got is not None:
                assert got == cgb_palette(gb, o, obj=True)[1:], (o, b)
    finally:
        gb.stop()


@pytest.mark.parametrize("v", VENUES)
def test_the_dmg_keeps_looks_0_2_without_extras(v):
    gb = boot_play("dmg")
    try:
        goto_group(gb, GROUP[v])
        for _ in range(60):
            gb.run(20)
            assert all(x < 3 for x in gb.read("patron_variant", MAX_P)), "variant bytes 0-2 only"
    finally:
        gb.stop()


@pytest.mark.parametrize("v", VENUES)
def test_the_blob_is_252_tiles_in_bank_1(v, model):
    txt = (ROOT / "build" / f"patrons_{v}_x.c").read_text()
    body = txt[txt.index(f"patron_tiles_{v}_x[4032] = {{"):]
    blob = bytes(int(h, 16) for h in re.findall(r"0x([0-9A-F]{2})", body[:body.index("};")]))
    assert len(blob) == 252 * 16
    gb = game(v)
    try:
        vram = gb.pb.memory
        got = bytes(vram[1, 0x9000:0x9800]) + bytes(vram[1, 0x8800:0x9000])[:124 * 16]
        assert got == blob
    finally:
        gb.stop()


@pytest.mark.parametrize("v", VENUES)
def test_it_spawns_only_the_tables_combinations_and_all_of_them(v, model):
    t = GL.venue_tables(v)
    allowed = set(t["combo"])
    gb = game(v)
    try:
        seen = set()
        for _ in range(12000):
            gb.write("lives", 3)
            gb.write("quota", 250)
            gb.run(20)
            st = gb.read("patron_state", MAX_P)
            for i, x in enumerate(gb.read("patron_variant", MAX_P)):
                if st[i]:
                    pair = (x & 7, (x ^ (x >> 3)) & 7)
                    assert pair in allowed, pair
                    assert bool(x & 0x40) == ((x & 7) > 2)
                    seen.add(pair)
            if len(seen) == len(allowed):
                break
        assert seen == allowed, sorted(allowed - seen)
    finally:
        gb.stop()


def lift_cases():
    out = []
    for v in VENUES:
        t = GL.venue_tables(v)
        out += [(v, l, p) for l, p in t["combo"][::2]]
    return out


@pytest.mark.parametrize("v,look,inst", lift_cases(), ids=[f"{v}-look{lk}-inst{i}" for v, lk, i in lift_cases()])
def test_a_lifted_look_changes_no_pixel_and_wears_its_palette(model, v, look, inst):
    gb = game(v)
    try:
        freeze(gb)
        gb.run(4)
        spec = {}
        first = None
        for p in sorted(patrons(gb), key=lambda p: p["i"]):
            x = gb.read("patron_variant", MAX_P)[p["i"]]
            if first is None and p["state"] == WALKING:
                first, x = p["i"], variant(look, inst)
            spec.setdefault(p["bar"], []).append((p["x"], x, 0))
        assert first is not None
        lineup(gb, spec)
        gb.run(8, render=True)
        ref = screen(gb)
        x = gb.read("patron_x", MAX_P)[first]
        hook(gb, first, HOOK_LIFT)
        for i in range(12):
            gb.run(1, render=True)
            assert (screen(gb) == ref).all(), f"lift frame {i}"
        assert gb.mem("lift_hook_res") == 1 and lift_state(gb)[first] == HOOK_LIFT
        spr = lifted_sprites(gb)
        assert sorted((s["x"] - 8, s["tile"]) for s in spr) == [(x, obj_tile_of(look)), (x + 8, obj_tile_of(look) + 2)]
        obj = GL.venue_tables(v)["order"][inst]
        assert all(s["flags"] & 0x0F == obj | (8 if look > 2 else 0) for s in spr), [hex(s["flags"]) for s in spr]
        hook(gb, first, HOOK_DROP)
        for i in range(12):
            gb.run(1, render=True)
            assert (screen(gb) == ref).all(), f"drop frame {i}"
        assert lift_state(gb)[first] == 0 and lifted_sprites(gb) == []
    finally:
        gb.stop()


MIRROR = {"zoo": {"looks345": {0: variant(3, 3), 1: variant(4, 4), 2: variant(5, 1)}, "looks673": {0: variant(6, 6), 1: variant(7, 3), 2: variant(3, 0)}},
          "aliens": {"looks345": {0: variant(3, 3), 1: variant(4, 4), 2: variant(5, 5)}, "looks673": {0: variant(6, 6), 1: variant(7, 4), 2: variant(3, 5)}}}


@pytest.mark.parametrize("v", VENUES)
@pytest.mark.parametrize("name", ["looks345", "looks673"])
def test_the_looks_mirror_pixel_for_pixel_on_an_r_level(model, v, name):
    """(Run at double speed, conftest PERF_DS: at normal speed the R run lags the L run by frames, as the Factory's.)"""
    looks = MIRROR[v][name]
    a, b = tc.pair("cgb", tc.ALL_R, lv=GROUP[v] + 1)
    try:
        assert a.mem("cur_group") == GROUP[v]
        lp = tc.scene(a, looks=looks)
        assert tc.scene(b, looks=looks) == lp
        tc.run_both(a, b, 6)
        assert a.mem("lift_hook_res") == 1 and b.mem("lift_hook_res") == 1
        mi = tc.Mirror(a, b, tc.ALL_R)
        mi.check()
        for f in range(30):
            tc.run_both(a, b, 1)
            bad = mi.check()
            assert not bad, (f, bad)
    finally:
        tc.close(a, b)
