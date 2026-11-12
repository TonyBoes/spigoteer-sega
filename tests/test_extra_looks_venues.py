# The Color-only extra looks of the venues imported after the Factory (the Igloo, the Chrome Cow, the Teahouse), each on the Atlas's slots
# (tools/gen_looks.py, docs/dev/queue_briefs/extra_looks_slots.md); the Factory's own are in test_extra_looks.py. The tests are the Factory's, one per venue:
#   - the (look, palette) table is the plan's (extra_combos / VARIANT_CUTS), with the Atlas's OBJ and BG slot of every instance and its colours;
#   - the five extra looks are the owner's art in VRAM bank 1; the DMG keeps looks 0-2;
#   - the game loads the instances where the table says, spawns only allowed pairs and all of them;
#   - a lifted extra look changes no pixel and wears its OBJ palette; an R level mirrors them pixel for pixel.
import json
import re
import sys

import pytest
from conftest import ROOT, double_speed, logic_paused
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

GROUPS = ["cowboys", "sports", "lumberjacks", "chefs", "divers", "robots", "punks", "ninjas", "zoo", "aliens"]
VENUE_NAMES = ["saloon", "sports", "lodge", "bistro", "igloo", "factory", "biker", "teahouse", "zoo", "space"]
VENUES = ["divers", "punks", "ninjas"]
PALS = json.loads((ROOT / "assets" / "palettes.json").read_text())


@pytest.fixture(params=["cgb"])
def model(request):
    return request.param


def variant(look, inst):
    return look | (((look ^ inst) & 7) << 3) | (0x40 if look > 2 else 0)


def table(v):
    return GL.venue_tables(v)


def looks_c(v):
    txt = (ROOT / "build" / "looks_pick.h").read_text()
    g = GROUPS.index(v)

    def arr(name):
        m = re.search(name + r"_%d\[\d+\] = \{ (.*?) \};" % g, txt)
        return [int(h, 16) for h in re.findall(r"0x([0-9A-F]{2})", m.group(1))]
    return arr("combo"), arr("boss")


def rgb5(hexs):       # (the Atlas shows the colours lifted to 8 bits: the 5-bit values are the game's)
    return [(int(h[1:3], 16) >> 3, int(h[3:5], 16) >> 3, int(h[5:7], 16) >> 3) for h in hexs]


# ---- the table -----------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("v", VENUES)
def test_the_combos_are_the_plans_table(v):
    t = table(v)
    looks, inst, allowed = EC.venue_table(v)
    assert t["looks"] == looks and len(looks) == 8
    dup = len(P.NATIVE_OBJ.get(v, [])) - len(set(P.NATIVE_OBJ.get(v, [])))     # (a native look that shares another's OBJ slot repeats it: the Teahouse's RONIN on SAKURA's OBJ 6)
    assert len(t["order"]) == len(P.ENGINE_BG[v]) + dup == 6 + dup and t["dropped"] == [] and set(inst) == set(t["order"]), "all of the plan's instances are in"
    assert t["order"][4] == 5, "instance 4 is OBJ 5: the one the show's dancers take (render.c pal5_check)"
    want = [(li, pi) for li, n in enumerate(looks) for pi, o in enumerate(t["order"])
            if o in allowed[n] and pi == (li if li < 3 and t["order"][li] == o else t["order"].index(o))]     # (one instance an OBJ slot, but a native look keeps its own)
    assert t["combo"] == want
    own = P.BOSS_OWN_OBJ[v]
    assert t["boss"] == [(l, p) for l, p in want if l != 2 and t["order"][p] not in own]
    combo, boss = looks_c(v)
    spread = lambda lst: [GL.V(*lst[r * len(lst) >> 8]) for r in range(256)]       # (the pick indexes by the random byte itself: r * n >> 8)
    assert combo == spread(want), "build/looks_pick.h is this table"
    assert boss == spread(t["boss"])
    cuts = P.VARIANT_CUTS[v]
    for n, o_cut in cuts.items():                     # the owner's crossed-out swaps never spawn
        for li, pi in want:
            if looks[li] == n:
                assert t["order"][pi] not in o_cut, (n, t["order"][pi])


@pytest.mark.parametrize("v", VENUES)
def test_each_instance_sits_on_the_atlas_slots_with_the_atlas_colours(v):
    t = table(v)
    atlas = GL.SLOTS[v]
    owners = {n: i for i, n in enumerate(t["looks"])}
    for pi, (o, bg, pal) in enumerate(zip(t["order"], t["bg"], t["pal"])):
        names = sorted(atlas["obj"][str(o)]["patrons"])
        assert names == sorted(atlas["bg"][str(bg)]["patrons"]) and names, (pi, o, bg)
        assert all(n.split(",")[0] in owners for n in names), names
        if pal[0] == "pal":
            assert rgb5(PALS[pal[1]]["hex"]) == rgb5(atlas["obj"][str(o)]["cols"][1:]), (pi, pal)
            assert rgb5(atlas["bg"][str(bg)]["cols"][1:]) == rgb5(atlas["obj"][str(o)]["cols"][1:]), (pi, "BG twin")


@pytest.mark.parametrize("v", VENUES)
def test_the_art_is_the_owners(v):
    extras = P.EXTRA_LOOKS[v]
    assert len(extras) == 5
    for suffix in ("", "_back"):
        txt = (ROOT / "assets" / "art" / "patrons" / f"{v}_x{suffix}.txt").read_text()
        blocks = [[r for r in b.splitlines() if r and not r.startswith(";")] for b in txt.split("\n\n")]
        blocks = [b for b in blocks if b]
        assert len(blocks) == 5
        for b, name in zip(blocks, extras):
            src = [r for r in (ROOT / "tools" / "artifacts" / "palette_plan" / "art" / f"{v}_{name.lower()}{suffix}.txt").read_text().splitlines() if r and not r.startswith(";")]
            assert b == src, (name, suffix)
            assert all(set(r) <= set(".-+#") and len(r) == 16 for r in b)


@pytest.mark.parametrize("v", VENUES)
def test_the_added_palettes_are_the_plans(v):
    for (_k, slot), (name, cols) in P.PLANS[v].get("add", {}).items():
        k = f"{v}_{name.lower()}"
        assert PALS[k]["hex"] == [c.lower() for c in cols], k
        r = [int(h[1:3], 16) >> 3 | (int(h[3:5], 16) >> 3) << 5 | (int(h[5:7], 16) >> 3) << 10 for h in PALS[k]["hex"]]
        assert PALS[k]["rgb15"] == r


# ---- the game ------------------------------------------------------------------------------------------------------------------------

def venue_play(v, model_name="cgb"):
    gb = boot_play(model_name)
    goto_group(gb, GROUPS.index(v))
    gb.write("tip_chance", 0)
    return gb


def scratch(gb, at, n):
    return [gb.read(gb.addr("story_scratch") + at + i, 1)[0] for i in range(n)]


def rgb_bytes(cols):
    out = []
    for c in cols:
        out += [c & 255, c >> 8]
    return out


@pytest.mark.parametrize("v", VENUES)
def test_the_game_loads_its_instances_where_the_table_says(model, v):
    gb = venue_play(v)
    try:
        t = table(v)
        assert scratch(gb, 254, len(t["order"])) == t["order"] and scratch(gb, 262, len(t["order"])) == t["bg"]
        wall = cgb_palette(gb, 0)[0]
        assert gb.read(0xFFD4, 1)[0] == 3, "the mid-frame chain is on (SPLIT_ON 3)"
        es = P.STAGE_EARLY[v]
        late = [i for i, b in enumerate(t["bg"]) if b == 11 - es]
        early = [i for i, b in enumerate(t["bg"]) if b == es]
        for pi, (o, bg, pal) in enumerate(zip(t["order"], t["bg"], t["pal"])):
            if pal[0] != "pal":
                continue
            cols = PALS[pal[1]]["rgb15"]
            if o not in (0, 1, 2) and o != 5:
                assert cgb_palette(gb, o, obj=True)[1:] == cols, ("OBJ", o)
            if bg not in (5, 6):                      # (the chain's slots are read from their buffers below)
                assert cgb_palette(gb, bg)[1:] == cols and cgb_palette(gb, bg)[0] == wall, ("BG", bg)
        if late:
            assert list(gb.read(0xFFD6, 8)) == rgb_bytes([wall] + PALS[t["pal"][late[0]][1]]["rgb15"]) if t["pal"][late[0]][0] == "pal" else True
        if early:
            assert scratch(gb, 236 + 2, 8) == rgb_bytes([wall] + PALS[t["pal"][early[0]][1]]["rgb15"]) if t["pal"][early[0]][0] == "pal" else True
    finally:
        gb.stop()


@pytest.mark.parametrize("v", VENUES)
def test_the_dmg_keeps_looks_0_2_without_extras(v):
    gb = boot_play("dmg")
    try:
        goto_group(gb, GROUPS.index(v))
        for _ in range(60):
            gb.run(20)
            assert all(x < 3 for x in gb.read("patron_variant", MAX_P)), "variant bytes 0-2 only"
    finally:
        gb.stop()


@pytest.mark.parametrize("v", VENUES)
def test_the_blob_is_252_tiles_in_bank_1(model, v):
    txt = (ROOT / "build" / f"patrons_{v}_x.c").read_text()
    body = txt[txt.index(f"patron_tiles_{v}_x[4032] = {{"):]
    blob = bytes(int(h, 16) for h in re.findall(r"0x([0-9A-F]{2})", body[:body.index("};")]))
    assert len(blob) == 252 * 16
    gb = venue_play(v)
    try:
        vram = gb.pb.memory
        got = bytes(vram[1, 0x9000:0x9800]) + bytes(vram[1, 0x8800:0x9000])[:124 * 16]
        assert got == blob
    finally:
        gb.stop()


@pytest.mark.parametrize("v", VENUES)
def test_it_spawns_only_the_tables_combinations_and_all_of_them(model, v):
    t = table(v)
    allowed = set(t["combo"])
    gb = venue_play(v)
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


def sample_combos(v):
    """Every look once on one of its instances (rotating through them), plus the venue's two chain instances (BG 5 early, BG 6 late)."""
    t = table(v)
    out, k = [], 0
    for look in range(8):
        pis = [pi for li, pi in t["combo"] if li == look]
        out.append((look, pis[k % len(pis)]))
        k += 1
    for b in (5, 6):
        pi = t["bg"].index(b)
        li = next(li for li, p in t["combo"] if p == pi)
        out.append((li, pi))
    return out


LIFT_CASES = [(v, look, inst) for v in VENUES for look, inst in sample_combos(v)]


@pytest.mark.parametrize("v,look,inst", LIFT_CASES, ids=[f"{v}-look{lk}-inst{i}" for v, lk, i in LIFT_CASES])
def test_a_lifted_look_changes_no_pixel_and_wears_its_palette(model, v, look, inst):
    gb = venue_play(v)
    try:
        lift_obj = table(v)["order"]
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
        assert all(s["flags"] & 0x0F == lift_obj[inst] | (8 if look > 2 else 0) for s in spr), [hex(s["flags"]) for s in spr]
        hook(gb, first, HOOK_DROP)
        for i in range(12):
            gb.run(1, render=True)
            assert (screen(gb) == ref).all(), f"drop frame {i}"
        assert lift_state(gb)[first] == 0 and lifted_sprites(gb) == []
    finally:
        gb.stop()


@pytest.mark.parametrize("v", VENUES)
def test_the_looks_mirror_pixel_for_pixel_on_an_r_level(model, v):
    """(Run at double speed, conftest PERF_DS: the way the game ships.)"""
    t = table(v)
    pick = lambda look: next(pi for li, pi in t["combo"] if li == look)
    looks = {0: variant(3, pick(3)), 1: variant(6, pick(6)), 2: variant(7, pick(7))}
    with double_speed():
        a, b = tc.pair("cgb", tc.ALL_R, lv=GROUPS.index(v) + 1)
    try:
        assert a.mem("cur_group") == GROUPS.index(v)
        lp = tc.scene(a, looks=looks)
        assert tc.scene(b, looks=looks) == lp
        tc.run_both(a, b, 6)
        assert a.mem("lift_hook_res") == 1 and b.mem("lift_hook_res") == 1
        mi = tc.Mirror(a, b, tc.ALL_R)
        keg_only = lambda bad: [x for x in bad if not (isinstance(x, tuple) and x[1][0] >= 138)]   # (the keg column: the Chrome Cow's milk jug is not mirror-symmetric, as on main; no look is there)
        mi.check()
        for f in range(30):
            tc.run_both(a, b, 1)
            bad = keg_only(mi.check())
            assert not bad, (f, bad)
    finally:
        tc.close(a, b)


@pytest.mark.parametrize("v", VENUES + ["robots", "sports", "lumberjacks", "chefs", "zoo", "aliens"])
def test_the_stage_palette_reloaded_early_is_not_on_the_stages_last_row(v):
    """The chain reloads one stage palette at line 31 (the end of text row 3 of the stage) and the other at line 39: the early one may not be on the stage's 4th row."""
    stage = json.loads((ROOT / "build" / "venues.json").read_text())["venues"][VENUE_NAMES[GROUPS.index(v)]]["stage_attr"]
    assert P.STAGE_EARLY[v] not in {a & 7 for a in stage[60:80]}, (v, "the early slot is on the stage's last row")
    assert (11 - P.STAGE_EARLY[v]) in {a & 7 for a in stage[60:80]} or v == "robots", "(so the late one is the one that is)"


@pytest.mark.parametrize("v", VENUES + ["robots"])
def test_a_show_gives_slot_5_back_to_palette_instance_4(model, v):
    """Instance 4 is OBJ 5 as a sprite; a show's dancers have the slot above the stage and it is instance 4's own colours (not the chain's late palette) again below it and after the show."""
    gb = venue_play(v)
    try:
        t = table(v)
        assert t["order"][4] == 5
        mine = cgb_palette(gb, 5, obj=True)
        gb.run(3)
        with logic_paused(gb):
            gb.write("show_timer", 100)
        gb.run(3)
        assert cgb_palette(gb, 5, obj=True) != mine and gb.mem("pal5_cur") == 3, "the show's colours at the top of the frame (the patron's again below the dancers: tests/test_show_obj5.py)"
        with logic_paused(gb):
            gb.write("show_timer", 0)
        gb.run(3)
        assert cgb_palette(gb, 5, obj=True)[1:] == mine[1:] and gb.mem("pal5_cur") == 0, "given back"
    finally:
        gb.stop()
