# A2: the generic Color-only extra looks, built for the Robot Factory per the Graphics Atlas slot table (docs/dev/queue_briefs/extra_looks_slots.md).
#   - the (look, palette) table is generated from the Atlas plan (tools/gen_looks.py, build/looks.c): six palette instances (OBJ 3, 6, 4, 1, 5, 7), each on
#     the BG slot the Atlas lists the same patrons on (BG 3, 6, 4, 2, 5, 7), 48 combinations; with fewer BG slots in the engine it leaves out the instance with
#     the fewest looks;
#   - the Factory's palette instances sit where the table says (OBJ and BG slots; BG 2, 3, 4, 7 loaded with the level, BG 5 reloaded early and BG 6 late by the
#     mid-frame chain, the full-mug instance);
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
    txt = (ROOT / "build" / "looks_pick.h").read_text()
    def arr(name):
        m = re.search(name + r"_5\[\d+\] = \{ (.*?) \};", txt)
        return [int(h, 16) for h in re.findall(r"0x([0-9A-F]{2})", m.group(1))]
    return arr("combo"), arr("boss")


# ---- the table -----------------------------------------------------------------------------------------------------------------------

def test_the_factory_combos_are_the_plans_table():
    t = table()
    looks, inst, allowed = EC.venue_table("robots")
    assert t["looks"] == looks == ["BOXY", "VOLTA", "BLIP", "NEKA", "TELLY", "CLANK", "TOOB", "PEPPER"]
    assert len(t["order"]) == len(P.ENGINE_BG["robots"]) == 6, "the plan has six instances and the engine six BG slots (BG 2-7)"
    assert t["order"][:3] == [3, 6, 4], "instances 0-2: the OBJ slots of BOXY, VOLTA, BLIP (the plan moved BLIP to NEKA's cyan OBJ 4)"
    assert t["order"][4] == 5, "instance 4 is OBJ 5: the one the show's dancers take (render.c pal5_check)"
    assert t["order"] == [3, 6, 4, 1, 5, 7] and t["dropped"] == [] and set(inst) == set(t["order"]), "all six of the plan's instances are in"
    assert t["bg"] == [3, 6, 4, 2, 5, 7], "each instance sits on the BG slot the Atlas lists its patrons on (BOXY BG 3, VOLTA 6, BLIP and NEKA 4, CLANK and PEPPER 2, TOOB 5, TELLY 7)"
    counts = {o: sum(o in a for a in allowed.values()) for o in inst}
    assert set(counts.values()) == {8}, "no instance has fewer looks (the Factory keeps all swaps)"
    want = [(li, pi) for li, n in enumerate(looks) for pi, o in enumerate(t["order"]) if o in allowed[n]]
    assert t["combo"] == want and len(want) == 48
    assert t["boss"] == [(l, p) for l, p in want if l != 2 and t["order"][p] not in (4, 5, 7)] and len(t["boss"]) == 21
    combo, boss = looks_c()
    spread = lambda lst: [GL.V(*lst[r * len(lst) >> 8]) for r in range(256)]       # (the pick indexes by the random byte itself: r * n >> 8)
    assert combo == spread(want), "build/looks_pick.h is this table"
    assert boss == spread(t["boss"])


def test_each_instance_sits_on_the_atlas_slots_with_the_atlas_colours():
    """The generated table against plan_slots.json (the Atlas's own export): the OBJ and BG slot of every instance list the same patrons, and the colours
    the game puts there (palettes.json, the full mug's own for CLANK and PEPPER) are the Atlas's, colours 1-3 of the OBJ slot and of its BG twin."""
    t = table()
    atlas = GL.SLOTS["robots"]
    owners = {n: i for i, n in enumerate(t["looks"])}
    for pi, (o, bg, pal) in enumerate(zip(t["order"], t["bg"], t["pal"])):
        names = sorted(atlas["obj"][str(o)]["patrons"])
        assert names == sorted(atlas["bg"][str(bg)]["patrons"]) and names, (pi, o, bg)
        assert all(n in owners for n in names), names
        if pal[0] == "pal":
            rgb5 = lambda hexs: [(int(h[1:3], 16) >> 3, int(h[3:5], 16) >> 3, int(h[5:7], 16) >> 3) for h in hexs]     # (the Atlas shows the colours lifted to 8 bits: the 5-bit values are the game's)
            assert rgb5(PALS[pal[1]]["hex"]) == rgb5(atlas["obj"][str(o)]["cols"][1:]), (pi, pal)
            assert rgb5(atlas["bg"][str(bg)]["cols"][1:]) == rgb5(atlas["obj"][str(o)]["cols"][1:]), (pi, "BG twin")


def test_with_fewer_bg_slots_the_instance_with_the_fewest_looks_is_left_out(monkeypatch):
    ALL = ["BOXY", "VOLTA", "BLIP", "NEKA", "TELLY", "CLANK", "TOOB", "PEPPER"]
    monkeypatch.setitem(P.ENGINE_BG, "robots", [2, 3, 4, 5, 6])
    t = table()
    assert t["dropped"] == [7] and t["order"] == [3, 6, 4, 1, 5], "five BG slots for six instances: the tie goes to the fewest owners, then the highest OBJ slot"
    monkeypatch.setitem(P.ENGINE_BG, "robots", [3, 4, 5, 6, 7])
    monkeypatch.setitem(P.VARIANT_CUTS, "robots", {n: [1] for n in ALL if n != "CLANK"})      # OBJ 1 only for CLANK: 1 look against 8
    t = table()
    assert t["dropped"] == [1] and t["order"] == [3, 6, 4, 7, 5], t["order"]
    monkeypatch.setitem(P.ENGINE_BG, "robots", [2, 3, 4, 5, 6])
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
        assert scratch(gb, 254, 6) == t["order"] and scratch(gb, 262, 6) == t["bg"] == [3, 6, 4, 2, 5, 7]
        wall = cgb_palette(gb, 0)[0]
        a, b, c = (PALS["robots_" + k]["rgb15"] for k in "abc")
        cyan, purple = PALS["robots_neka"]["rgb15"], PALS["robots_toob"]["rgb15"]
        assert cgb_palette(gb, 3, obj=True)[1:] == a and cgb_palette(gb, 6, obj=True)[1:] == b
        assert cgb_palette(gb, 4, obj=True)[1:] == cyan and cgb_palette(gb, 5, obj=True)[1:] == purple, "NEKA's cyan is BLIP's too; TOOB is purple on OBJ 5"
        assert cgb_palette(gb, 7, obj=True)[1:] == c, "TELLY keeps the mint on OBJ 7"
        mug = cgb_palette(gb, 1, obj=True)
        assert mug != cgb_palette(gb, 2, obj=True)
        assert [cgb_palette(gb, s)[1:] for s in (3, 4, 7)] == [a, cyan, c], "BG 3 BOXY, BG 4 BLIP and NEKA, BG 7 TELLY: loaded with the level"
        assert cgb_palette(gb, 2)[1:] == mug[1:], "BG 2: CLANK and PEPPER wear the full mug's colours"
        assert [cgb_palette(gb, s)[0] for s in (2, 3, 4, 7)] == [wall] * 4
        assert gb.read(0xFFD4, 1)[0] == 3, "the mid-frame chain is on (SPLIT_ON 3)"
        assert list(gb.read(0xFFD6, 8)) == rgb_bytes([wall] + b), "late line: VOLTA's colours in BG 6"
        assert scratch(gb, 236 + 2, 8) == rgb_bytes([wall] + purple), "early line: TOOB's purple in BG 5"
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


def take_off_near_tap(gb, x=48):
    """Nobody drinks in these runs: whoever gets near the tap is taken off the bar, or the level restarts (a patron at the tap costs a life) every few patrons and the palette rule
    (a look's first appearance in a level is its default palette: src/mirror.c pick_pal) would show only the defaults. A level of the length the game has (8-16 patrons) shows
    few of the other pairs: tests/test_palette_rule.py measures that; these tests check that every pair is reachable in a long level."""
    st, px = gb.read("patron_state", MAX_P), gb.read("patron_x", MAX_P)
    gone = [i for i in range(MAX_P) if st[i] and px[i] >= x]
    for i in gone:
        gb.write(gb.addr("patron_state") + i, 0)
        gb.write(gb.addr("patron_lift") + i, 0)
        gb.write(gb.addr("patron_draw") + i, 255)
    if gone:
        gb.write("patrons_live", sum(1 for i in range(MAX_P) if st[i] and i not in gone))
        gb.write("lists_dirty", 1)
        gb.write("lists_ok", 0)


def test_the_factory_spawns_only_the_tables_combinations_and_all_of_them(model):
    t = table()
    allowed = set(t["combo"])
    gb = factory()
    try:
        seen = set()
        for _ in range(8000):
            gb.write("lives", 3)
            gb.write("quota", 250)
            take_off_near_tap(gb)
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


LIFT_OBJ = [3, 6, 4, 1, 5, 7]
COMBOS = [(3, 2), (3, 0), (4, 3), (5, 3), (5, 1), (6, 4), (7, 3), (7, 4), (2, 2), (0, 3), (4, 5), (6, 5), (1, 5), (7, 1)]


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
    """(Run at double speed, conftest PERF_DS: the way the game ships. At normal speed the R run's frames, with the mid-frame chain and the mirrored compose,
    overrun their VBlank and show up to three frames behind the L run, where test_classic's Mirror lets b show one late.)"""
    looks = {"looks345": {0: variant(3, 2), 1: variant(4, 3), 2: variant(5, 5)},
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
