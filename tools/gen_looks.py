#!/usr/bin/env python3
"""build/looks.c + build/looks.h: the (look, palette instance) combination tables of the Color-only extra looks, generated from the Graphics Atlas plan.

  gen_looks.py outdir

Nothing is typed here: tools/dev/extra_combos.py derives each venue's looks, palette instances (OBJ slots) and each look's allowed OBJ slots from
tools/artifacts/palette_plan/plan_data.py (NAMES, EXTRA_LOOKS, PLANS moves / add / join, VARIANT_CUTS); plan_data also names what the engine can do
(ENGINE_BG: the BG slots instances may sit on) and what a boss fight owns (BOSS_OWN_OBJ). The generator

  * numbers the instances: 0-2 are the OBJ slots of looks 0-2 (patron_variant keeps `look | (instance ^ look) << 3`), then the rest, OBJ 5 last
    (instance 4 is the one the show's dancers take, render.c pal5_check);
  * puts each instance on the BG slot the Atlas lists the same patrons on (plan_slots.json, the Atlas's export; asserted distinct and inside ENGINE_BG);
  * keeps as many as the engine has BG slots (len(ENGINE_BG[venue])); when the plan has more it leaves out the instance that gives the fewest looks, then
    has the fewest owners, then the highest OBJ slot (never OBJ 5);
  * writes combo[] = V(look, instance) of every allowed pair (look-major) and combo_boss[] without look 2 and without the boss's OBJ slots;
  * checks the instance palettes (assets/palettes.json `<venue>_<name>` of the look that brought its colours) against the plan's hex.

Needs build/palettes.c (plan_data imports game_truth): run after palettes2c. Usage from the Makefile.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools/artifacts/palette_plan"))
sys.path.insert(0, os.path.join(ROOT, "tools/dev"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import plan_data as P  # noqa: E402
import extra_combos as E  # noqa: E402

GROUPS = ["cowboys", "sports", "lumberjacks", "chefs", "divers", "robots", "punks", "ninjas", "zoo", "aliens"]   # = gen_art.PATRON_GROUPS


SLOTS = json.load(open(os.path.join(ROOT, "tools/artifacts/palette_plan/plan_slots.json")))["venues"]   # the Atlas's slot plan (tools/dev/export_plan_slots.py)


def atlas_bg(v, obj_slot):
    """The BG slot the Atlas gives the patrons of OBJ slot `obj_slot` of venue v: the one BG slot that lists the same patrons (the plan's own table)."""
    owners = set(SLOTS[v]["obj"][str(obj_slot)]["patrons"])
    hit = [int(sl) for sl, e in SLOTS[v]["bg"].items() if owners <= set(e["patrons"])]   # (a BG slot may list more: the Lodge's BG 2 holds CEDAR, WILLOW, BOONE and PIP of OBJ 1 and 3)
    assert len(hit) == 1, (v, "OBJ", obj_slot, sorted(owners), "the Atlas lists them on BG", hit)
    return hit[0]


def rgb555(h):
    """the game's raw colour of an Atlas hex colour (5 bits a channel: the Atlas shows what the game holds, lifted to 8 bits)"""
    return (int(h[1:3], 16) >> 3) | (int(h[3:5], 16) >> 3) << 5 | (int(h[5:7], 16) >> 3) << 10


def V(look, pi):
    """patron_variant byte (game.h PATRON_BANK1, render.c patron_attr)"""
    return look | ((pi ^ look) << 3) | (0x40 if look > 2 else 0)


def venue_tables(v):
    looks, inst, allowed = E.venue_table(v)
    nat = []
    for k in range(3):
        nat.append(next(o for o, ns in inst.items() if looks[k] in ns))
    if v in P.NATIVE_OBJ:
        nat = list(P.NATIVE_OBJ[v])
        assert all(o in inst for o in nat), (v, "NATIVE_OBJ names an OBJ slot that is no instance", nat, sorted(inst))
    cap = len(P.ENGINE_BG[v])     # (BG slots: instances share one when the Atlas lists their patrons together, e.g. the Lodge's CEDAR, WILLOW, BOONE and PIP on BG 2; two natives may share an OBJ slot)
    rest = [o for o in sorted(inst) if o not in nat]
    dropped = []

    def key(o):
        return (sum(o in a for a in allowed.values()), len(inst[o]), -o)
    while len({atlas_bg(v, o) for o in nat + rest}) > cap:        # the engine's BG slots are short: leave out the instance that gives the fewest looks
        o = min((o for o in rest if o != 5), key=key)
        rest.remove(o)
        dropped.append(o)
    others = [o for o in rest if o != 5]
    order = nat + others[:1] + ([5] if 5 in rest else []) + others[1:]     # (OBJ 5 is instance 4 whatever the count: the one the show's dancers take)
    assert 5 not in order or order.index(5) == 4, (v, "instance 4 must be OBJ 5 (the show's slot)", order)
    # the palette of each instance
    pal = []
    adds = {s: (n, c) for (_k, s), (n, c) in P.PLANS[v].get("add", {}).items()}
    pals = json.load(open(os.path.join(ROOT, "assets/palettes.json")))
    for pi, o in enumerate(order):
        if o in adds:
            name, cols = adds[o]
            key = "%s_%s" % (v, name.lower().replace(" ", "_"))
            if key not in pals:
                pal.append(("lit", [0] + [rgb555(h) for h in cols]))     # (a palette only the plan names: its colours as literals, no assets/palettes.json entry)
                continue
            got = [c.upper() for c in pals[key]["hex"]]
            assert got == [c.upper() for c in cols], (key, got, cols)
            pal.append(("pal", key))
        elif o == 1:
            pal.append(("mug", None))        # the full mug's OBJ 1: the venue's own drink colours (venue.pal[VENUE_PAL_DRINK_FULL])
        elif o == 2:
            pal.append(("empty", None))      # the empty mug's OBJ 2: the venue's empty-drink colours (venue.pal[VENUE_PAL_DRINK_EMPTY]); returns 2
        elif o == 0:
            pal.append(("pal", "bartender"))  # Sal's OBJ 0 (the Teahouse's SENSEI): palettes.json "bartender"
        elif o == 5:
            assert "Show dancers" in SLOTS[v]["obj"]["5"]["other"], (v, "OBJ 5 is the show dancers' here")
            pal.append(("show", None))       # a patron who shares the dancers' OBJ 5: the venue's show colours (venue.pal[VENUE_PAL_SHOW]), which OBJ 5 holds anyway
        else:
            assert o in P.PATRON_SLOT, (v, "instance", pi, "OBJ", o, "has no palette: add it to plan_data")
            pal.append(("pal", ("zoo_monkey", "zoo_panda", "zoo_hippo")[P.PATRON_SLOT[o]] if v == "zoo" else "%s_%s" % (v, "abc"[P.PATRON_SLOT[o]])))      # a native slot: the art variant A, B, C's palette (robots_a, _b, _c)
    own = P.BOSS_OWN_OBJ.get(v, [])
    combo, boss = [], []
    for li, name in enumerate(looks):
        for pi, o in enumerate(order):
            if o in allowed[name] and pi == (li if li < 3 and order[li] == o else order.index(o)):   # (one instance a slot, but a native look keeps its own: patron_variant of look k < 3 is instance k)
                combo.append((li, pi))
                if li != 2 and o not in own:
                    boss.append((li, pi))
    bg = [atlas_bg(v, o) for o in order]
    assert all(b in P.ENGINE_BG[v] for b in bg), (v, "the Atlas's BG slots", bg, "must be engine slots", P.ENGINE_BG[v])
    bgcols = [[rgb555(h) for h in SLOTS[v]["bg"][str(b)]["cols"]] for b in bg]   # the BG slot's colours as the Atlas draws them (colour 0 = the wall)
    return dict(bgcols=bgcols, looks=looks, order=order, bg=bg, pal=pal, combo=combo, boss=boss, dropped=dropped, inst=inst, allowed=allowed)


def render(outdir):
    venues = list(P.ENGINE_BG)
    t = {v: venue_tables(v) for v in venues}
    mask = 0
    for v in venues:
        mask |= 1 << GROUPS.index(v)
    early6 = 0
    for v in venues:
        if P.STAGE_EARLY[v] == 6:
            early6 |= 1 << GROUPS.index(v)
    show5 = 0
    for v in venues:
        if any(k == "show" for k, _ in t[v]["pal"]):
            show5 |= 1 << GROUPS.index(v)
    h = ["// generated by tools/gen_looks.py from the Graphics Atlas plan (tools/artifacts/palette_plan/plan_data.py) -- do not edit",
         "#ifndef LOOKS_H", "#define LOOKS_H", "#include <stdint.h>", "",
         "#define LOOKS_GEN_MASK 0x%02Xu   // bit g: the patron groups whose Color-only looks come from build/looks.c (the Saloon, group 0, has its own table in src/mirror.c)" % mask,
         "#define LOOKS_EARLY6 0x%02Xu   // bit g: the generated venue g reloads BG 6 early (line 31) and BG 5 late (line 39); clear: BG 5 early, BG 6 late (the Factory)" % early6,
         "#define LOOKS_SHOW5 0x%02Xu   // bit g: the venue's OBJ 5 instance wears the show's own colours (the Space Lounge's VENUS): a show takes nothing from it, so OBJ 5 needs no give-back" % show5,
         "uint8_t looks_insts(uint8_t g, uint8_t *obj, uint8_t *bg) BANKED;   // the 8 OBJ and 8 BG palette slots of palette instances 0-7 of group g; returns how many instances the venue has (3 legacy, 5 the Saloon, the venue's own)",
         "void looks_load(uint8_t g, uint8_t part) BANKED;                    // part 0..7 of the venue's Color-only looks' tiles into VRAM bank 1 (LCD off; the caller pumps the tune between parts)",
         "uint8_t looks_pal_get(uint8_t g, uint8_t pi, uint16_t *dst) BANKED; // dst[0..3] = instance pi's palette (colour 0 = 0); returns 1 / 2 / 3 when it is the venue's full-mug / empty-mug / show colours (dst untouched), else 0",
         "uint8_t looks_bg_get(uint8_t g, uint8_t pi, uint16_t *dst) BANKED;  // dst[0..3] = the colours of the BG slot of instance pi as the Atlas draws it (colour 0 = the wall); 0 when the venue has none (the legacy palettes)",
         "", "#endif", ""]
    pk = ["// generated by tools/gen_looks.py from the Graphics Atlas plan -- do not edit",
          "// included by src/mirror.c: the pick is a plain call in the spawn's own bank (a spawn frame is the tightest of a fight)", ""]
    c = ["// generated by tools/gen_looks.py from the Graphics Atlas plan -- do not edit", "#pragma bank 255", "#include <gb/gb.h>", '#include "palettes.h"', '#include "art.h"', '#include "looks.h"', ""]
    c += ["void load_%s_x(uint8_t part) BANKED;   // build/patrons_%s_x.c" % (v, v) for v in venues] + [""]
    sw_v, sw_i, sw_p, sw_l, sw_b = [], [], [], [], []
    for v in venues:
        d, g = t[v], GROUPS.index(v)
        names = d["looks"]
        c += ["// %s: %d looks, %d palette instances (OBJ %s%s), %d combos, %d in a boss fight" % (
            v, len(names), len(d["order"]), d["order"], ", plan's OBJ %s left out: the engine has %d BG slots" % (d["dropped"], len(P.ENGINE_BG[v])) if d["dropped"] else "",
            len(d["combo"]), len(d["boss"]))]
        c += ["//   looks: " + ", ".join("%d %s" % (i, n) for i, n in enumerate(names))]
        c += ["//   instances: " + ", ".join("%d OBJ %d BG %d %s" % (i, o, b, p[1] if isinstance(p[1], str) else p[0]) for i, (o, b, p) in enumerate(zip(d["order"], d["bg"], d["pal"])))]
        for nm, lst in (("combo", d["combo"]), ("boss", d["boss"])):
            body = ", ".join("0x%02X" % V(*lst[r * len(lst) >> 8]) for r in range(256))     # (indexed by the random byte itself: r * n >> 8 is worked out here, not on a spawn frame)
            pk += ["static const uint8_t %s_%d[256] = { %s };   // %d pairs" % (nm, g, body, len(lst))]
        sw_v += ["    case %d: return boss ? boss_%d[r] : combo_%d[r];" % (g, g, g)]
        pad = lambda a: a + [0] * (8 - len(a))
        sw_i += ["    case %d: { static const uint8_t o[8] = {%s}, b[8] = {%s}; for (k = 0; k < 8; k++) { obj[k] = o[k]; bg[k] = b[k]; } return %d; }" % (
            g, ", ".join(map(str, pad(d["order"]))), ", ".join(map(str, pad(d["bg"]))), len(d["order"]))]
        cases = []
        for pi, (kind, key) in enumerate(d["pal"]):
            if kind == "pal":
                cases.append("        case %d: pal_get(PAL_%s, dst); return 0;" % (pi, key.upper()))
            elif kind == "mug":
                cases.append("        case %d: return 1;" % pi)
            elif kind == "lit":
                cases.append("        case %d: dst[0] = 0; dst[1] = 0x%04X; dst[2] = 0x%04X; dst[3] = 0x%04X; return 0;" % ((pi,) + tuple(key[1:])))
            elif kind == "empty":
                cases.append("        case %d: return 2;" % pi)
            elif kind == "show":
                cases.append("        case %d: return 3;" % pi)
        sw_l += ["    case %d: load_%s_x(part); return;" % (g, v)]
        sw_b += ["    case %d: { static const uint16_t c[8][4] = {%s}; for (k = 0; k < 4; k++) dst[k] = c[pi][k]; return 1; }" % (
            g, ", ".join("{%s}" % ", ".join("0x%04X" % x for x in cols) for cols in d["bgcols"]))]
        sw_p += ["    case %d:" % g, "        switch (pi) {", *cases, "        }", "        break;"]
        c += [""]
    dflt = ", ".join(map(str, P.INST_OBJ + [0] * 3)), ", ".join(map(str, P.INST_BG + [0] * 3))
    pk += ["", "// 1: the group has Color-only looks (the Saloon, group 0, with its own table in src/mirror.c, and the generated venues): a table, not a shift by cur_group",
           "static const uint8_t looks_on[%d] = { %s };" % (len(GROUPS), ", ".join("1" if g == 0 or (mask >> g) & 1 else "0" for g in range(len(GROUPS))))]
    pk += ["", "// patron_variant byte of a random pick (r: one random byte) among the venue's allowed (look, palette) pairs of group g; boss: a fight",
           "static uint8_t looks_variant(uint8_t g, uint8_t r, uint8_t boss) {", "    switch (g) {", *sw_v, "    }", "    return 0;", "}", ""]
    c += ["uint8_t looks_insts(uint8_t g, uint8_t *obj, uint8_t *bg) BANKED {",
          "    uint8_t k;",
          "    switch (g) {", *sw_i, "    }",
          "    { static const uint8_t o[8] = {%s}, b[8] = {%s};   // (the Saloon's five, the legacy three of every other venue)" % dflt,
          "      for (k = 0; k < 8; k++) { obj[k] = o[k]; bg[k] = b[k]; } }",
          "    return g ? 3 : 5;", "}", "",
          "void looks_load(uint8_t g, uint8_t part) BANKED {", "    switch (g) {", *sw_l, "    }", "}", "",
          "uint8_t looks_bg_get(uint8_t g, uint8_t pi, uint16_t *dst) BANKED {",
          "    uint8_t k;",
          "    switch (g) {", *sw_b, "    }", "    return 0;", "}", "",
          "uint8_t looks_pal_get(uint8_t g, uint8_t pi, uint16_t *dst) BANKED {",
          "    switch (g) {", *sw_p, "    }",
          "    patron_pal_get(g, pi, dst);", "    return 0;", "}", ""]
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "looks.h"), "w") as f:
        f.write("\n".join(h))
    with open(os.path.join(outdir, "looks_pick.h"), "w") as f:
        f.write("\n".join(pk))
    with open(os.path.join(outdir, "looks.c"), "w") as f:
        f.write("\n".join(c))
    return t


if __name__ == "__main__":
    tt = render(sys.argv[1])
    for v, d in tt.items():
        print("%s: instances OBJ %s BG %s, %d combos, %d boss combos%s" % (
            v, d["order"], d["bg"], len(d["combo"]), len(d["boss"]), "; left out OBJ %s" % d["dropped"] if d["dropped"] else ""))
