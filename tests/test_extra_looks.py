# A2: the generic Color-only extra looks, built for the Robot Factory (docs/dev/handoffs/PLAN_extra_looks.md).
#   - the (look, palette) table is generated from the Graphics Atlas plan (tools/gen_looks.py, build/looks.c): it matches the plan's table,
#     follows the instance count of the engine's BG table, leaves out the plan's instance with the fewest looks when there are too many;
#   - the Factory's palette instances sit where the table says (OBJ and BG slots, the chain's BG 5 and 6, the full-mug instance);
#   - the Factory's five extra looks are in VRAM bank 1 (252 of 256 tiles), come from the owner's art, spawn only in allowed pairs;
#   - a lifted extra look changes no pixel and wears its OBJ palette and bank 1; an R level mirrors them pixel for pixel.
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
import plan_data as P  # noqa: E402

pytestmark = [pytest.mark.only_model("cgb"), pytest.mark.timeout(240)]

FACTORY = 5
PALS = json.loads((ROOT / "assets" / "palettes.json").read_text())


@pytest.fixture(params=["cgb"])
def model(request):
    return request.param


def variant(look, inst):
    return look | (((look ^ inst) & 7) << 3) | (0x40 if look > 2 else 0)


def table():
    return GL.venue_tables("robots")


def looks_c():
    txt = (ROOT / "build" / "looks.c").read_text()
    def arr(name):
        m = re.search(name + r"_5\[\d+\] = \{ (.*?) \};", txt)
        return [int(h, 16) for h in re.findall(r"0x([0-9A-F]{2})", m.group(1))]
    return arr("combo"), arr("boss")


# ---- the table -----------------------------------------------------------------------------------------------------------------------

def test_the_factory_combos_are_the_plans_table():
    t = table()
    looks, inst, allowed = EC.venue_table("robots")
    assert t["looks"] == looks == ["BOXY", "VOLTA", "BLIP", "NEKA", "TELLY", "CLANK", "TOOB", "PEPPER"]
    assert len(t["order"]) == len(P.ENGINE_BG["robots"]) == 5, "the instance count is the engine's BG table's (BG 2-6)"
    assert t["order"][:3] == [3, 6, 4], "instances 0-2: the OBJ slots of BOXY, VOLTA, BLIP (the plan moved BLIP to NEKA's cyan OBJ 4)"
    assert t["order"][4] == 5, "instance 4 is OBJ 5: the one the show's dancers take (render.c pal5_check)"
    assert t["dropped"] == [7] and 7 not in t["order"] and set(inst) - set(t["order"]) == {7}, "the plan has 6 instances: TELLY's OBJ 7 is left out"
    counts = {o: sum(o in a for a in allowed.values()) for o in inst}
    assert set(counts.values()) == {8}, "no instance has fewer looks (the Factory keeps all swaps): the tie goes to the fewest owners, then the highest OBJ slot"
    want = [(li, pi) for li, n in enumerate(looks) for pi, o in enumerate(t["order"]) if o in allowed[n]]
    assert t["combo"] == want and len(want) == 40
    assert t["boss"] == [(l, p) for l, p in want if l != 2 and t["order"][p] not in (4, 5, 7)] and len(t["boss"]) == 21
    combo, boss = looks_c()
    assert combo == [GL.V(l, p) for l, p in want], "build/looks.c is this table"
    assert boss == [GL.V(l, p) for l, p in t["boss"]]


def test_a_6th_instance_is_a_table_change(monkeypatch):
    monkeypatch.setitem(P.ENGINE_BG, "robots", [2, 3, 4, 5, 6, 7])
    t = table()
    assert t["order"] == [3, 6, 4, 1, 5, 7] and t["bg"] == [2, 3, 4, 5, 6, 7] and t["dropped"] == []
    assert len(t["combo"]) == 48
    assert t["pal"][5] == ("pal", "robots_c"), "TELLY's OBJ 7 keeps BLIP's old mint"


ALL = ["BOXY", "VOLTA", "BLIP", "NEKA", "TELLY", "CLANK", "TOOB", "PEPPER"]


def test_the_instance_with_the_fewest_looks_is_left_out(monkeypatch):
    monkeypatch.setitem(P.VARIANT_CUTS, "robots", {n: [1] for n in ALL if n != "CLANK"})      # OBJ 1 only for CLANK: 1 look against 8
    t = table()
    assert t["dropped"] == [1] and t["order"] == [3, 6, 4, 7, 5], t["order"]
    monkeypatch.setitem(P.VARIANT_CUTS, "robots", {n: [5] for n in ALL if n != "BOXY"})      # OBJ 5 would be the fewest, but it is the show's slot: never dropped
    t = table()
    assert t["dropped"] == [7] and t["order"] == [3, 6, 4, 1, 5], t["order"]


def test_the_factory_art_is_the_owners():
    for suffix in ("", "_back"):
        txt = (ROOT / "assets" / "art" / "patrons" / f"robots_x{suffix}.txt").read_text()
        blocks = [[r for r in b.splitlines() if r and not r.startswith(";")] for b in txt.split("\n\n")]
        blocks = [b for b in blocks if b]
        assert len(blocks) == 5
        for b, name in zip(blocks, ["neka", "telly", "clank", "toob", "pepper"]):
            src = [r for r in (ROOT / "tools" / "artifacts" / "palette_plan" / "art" / f"robots_{name}{suffix}.txt").read_text().splitlines() if r and not r.startswith(";")]
            assert b == src, (name, suffix)
            assert all(set(r) <= set(".-+#") and len(r) == 16 for r in b)


def test_the_factory_palettes_are_the_plans():
    assert PALS["robots_neka"]["hex"] == ["#58f0f8", "#7888a0", "#101828"]
    assert PALS["robots_toob"]["hex"] == ["#e8f0f8", "#9068d8", "#180830"]
    for k in ("robots_neka", "robots_toob"):
        r = [int(h[1:3], 16) >> 3 | (int(h[3:5], 16) >> 3) << 5 | (int(h[5:7], 16) >> 3) << 10 for h in PALS[k]["hex"]]
        assert PALS[k]["rgb15"] == r


# ---- the game ------------------------------------------------------------------------------------------------------------------------

def factory(model_name="cgb"):
    gb = boot_play(model_name)
    goto_group(gb, FACTORY)
    gb.write("tip_chance", 0)
    return gb


def scratch(gb, at, n):
    return [gb.read(gb.addr("story_scratch") + at + i, 1)[0] for i in range(n)]


def rgb_bytes(cols):
    out = []
    for c in cols:
        out += [c & 255, c >> 8]
    return out


def test_the_factory_loads_its_instances_where_the_table_says(model):
    gb = factory()
    try:
        t = table()
        assert scratch(gb, 254, 5) == t["order"] and scratch(gb, 262, 5) == t["bg"]
        wall = cgb_palette(gb, 0)[0]
        a, b, c = (PALS["robots_" + k]["rgb15"] for k in "abc")
        cyan, purple = PALS["robots_neka"]["rgb15"], PALS["robots_toob"]["rgb15"]
        assert cgb_palette(gb, 3, obj=True)[1:] == a and cgb_palette(gb, 6, obj=True)[1:] == b
        assert cgb_palette(gb, 4, obj=True)[1:] == cyan and cgb_palette(gb, 5, obj=True)[1:] == purple, "NEKA's cyan is BLIP's too; TOOB is purple on OBJ 5"
        mug = cgb_palette(gb, 1, obj=True)
        assert mug != cgb_palette(gb, 2, obj=True)
        assert [cgb_palette(gb, s)[1:] for s in (2, 3, 4)] == [a, b, cyan]
        assert [cgb_palette(gb, s)[0] for s in (2, 3, 4)] == [wall] * 3
        assert gb.read(0xFFD4, 1)[0] == 2, "the chain: BG 5 early, BG 6 late"
        assert list(gb.read(0xFFD6, 8)) == rgb_bytes([wall] + purple), "late line: TOOB's purple in BG 6"
        assert scratch(gb, 236 + 2, 8) == rgb_bytes([wall] + mug[1:]), "early line: the full mug's colours in BG 5 (CLANK, PEPPER)"
    finally:
        gb.stop()


def test_the_factory_keeps_looks_0_2_without_extras_on_the_dmg():
    gb = boot_play("dmg")
    try:
        goto_group(gb, FACTORY)
        for _ in range(60):
            gb.run(20)
            assert all(v < 3 for v in gb.read("patron_variant", MAX_P)), "variant bytes 0-2 only"
        assert scratch(gb, 254, 3)[:3] == [3, 6, 4], "(the DMG reads the OBJ slots for its OAM attribute: bits 0-2 are ignored there)"
    finally:
        gb.stop()


def test_the_factory_blob_is_252_tiles_in_bank_1(model):
    txt = (ROOT / "build" / "patrons_robots_x.c").read_text()
    body = txt[txt.index("patron_tiles_robots_x[4032] = {"):]
    blob = bytes(int(h, 16) for h in re.findall(r"0x([0-9A-F]{2})", body[:body.index("};")]))
    assert len(blob) == 252 * 16 and 256 - 252 == 4, "bank 1: 252 of 256 tiles (the 4 left are the only reserve)"
    gb = factory()
    try:
        vram = gb.pb.memory
        got = bytes(vram[1, 0x9000:0x9800]) + bytes(vram[1, 0x8800:0x9000])[:124 * 16]
        assert got == blob
    finally:
        gb.stop()


def test_the_factory_spawns_only_the_tables_combinations_and_all_of_them(model):
    t = table()
    allowed = set(t["combo"])
    gb = factory()
    try:
        seen = set()
        for _ in range(8000):
            gb.write("lives", 3)
            gb.write("quota", 250)
            gb.run(20)
            st = gb.read("patron_state", MAX_P)
            for i, v in enumerate(gb.read("patron_variant", MAX_P)):
                if st[i]:
                    pair = (v & 7, (v ^ (v >> 3)) & 7)
                    assert pair in allowed, pair
                    assert bool(v & 0x40) == ((v & 7) > 2)
                    seen.add(pair)
            if len(seen) == len(allowed):
                break
        assert seen == allowed, sorted(allowed - seen)
    finally:
        gb.stop()


LIFT_OBJ = [3, 6, 4, 1, 5]
COMBOS = [(3, 2), (3, 0), (4, 3), (5, 3), (5, 1), (6, 4), (7, 3), (7, 4), (2, 2), (0, 3)]


@pytest.mark.parametrize("look,inst", COMBOS, ids=[f"look{lk}-inst{i}" for lk, i in COMBOS])
def test_a_lifted_factory_look_changes_no_pixel_and_wears_its_palette(model, look, inst):
    gb = factory()
    try:
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
        x = gb.read("patron_x", MAX_P)[first]
        hook(gb, first, HOOK_LIFT)
        for i in range(12):
            gb.run(1, render=True)
            assert (screen(gb) == ref).all(), f"lift frame {i}"
        assert gb.mem("lift_hook_res") == 1 and lift_state(gb)[first] == HOOK_LIFT
        spr = lifted_sprites(gb)
        assert sorted((s["x"] - 8, s["tile"]) for s in spr) == [(x, obj_tile_of(look)), (x + 8, obj_tile_of(look) + 2)]
        assert all(s["flags"] & 0x0F == LIFT_OBJ[inst] | (8 if look > 2 else 0) for s in spr), [hex(s["flags"]) for s in spr]
        hook(gb, first, HOOK_DROP)
        for i in range(12):
            gb.run(1, render=True)
            assert (screen(gb) == ref).all(), f"drop frame {i}"
        assert lift_state(gb)[first] == 0 and lifted_sprites(gb) == []
    finally:
        gb.stop()


@pytest.mark.parametrize("name", ["looks345", "looks673"])
def test_the_factory_looks_mirror_pixel_for_pixel_on_an_r_level(model, name):
    looks = {"looks345": {0: variant(3, 2), 1: variant(4, 3), 2: variant(5, 4)},
             "looks673": {0: variant(6, 4), 1: variant(7, 3), 2: variant(3, 0)}}[name]
    a, b = tc.pair("cgb", tc.ALL_R, lv=FACTORY + 1)
    try:
        assert a.mem("cur_group") == FACTORY
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
