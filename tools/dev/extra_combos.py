#!/usr/bin/env python3
"""Read-only: the (look, palette) combination table of every venue's Color-only extra looks, derived from the Graphics Atlas plan
(tools/artifacts/palette_plan/plan_data.py: NAMES, EXTRA_LOOKS, PLANS moves / add / join, VARIANT_CUTS). Nothing is hand-typed here.

  python3 tools/dev/extra_combos.py            # one line per venue + the combo list of each
  python3 tools/dev/extra_combos.py robots     # one venue, every look with its allowed OBJ slots

A venue's palette instances are its patron OBJ slots after the plan's moves (a patron palette = an OBJ slot with its matching BG slot);
a look may spawn in every instance except the OBJ slots in VARIANT_CUTS[venue][NAME] (owner rule, uniform over the allowed pairs).
Needs build/palettes.c (run `make` first: plan_data imports game_truth).
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools/artifacts/palette_plan"))
import plan_data as P  # noqa: E402

BG_CAPACITY_NOW = {"cowboys": 5, **{v: len(b) for v, b in P.ENGINE_BG.items()}}      # the Saloon: BG 2, 3, 4, 7 (keg is on BG 0 there) and 5 (the split); plan_data ENGINE_BG: the Factory's chain (BG 2-6); every other venue: keg on BG 7: 2, 3, 4, 5 = 4
BG_CAPACITY_DEFAULT = 4


def venue_table(v):
    """-> (looks, instances {obj slot: [names who own it]}, allowed {look: [obj slots]})"""
    names = [n.split(",")[0].strip() for n in P.NAMES[v]]
    pl = P.PLANS[v]
    inst = {}
    if v != "cowboys":
        inst = {k: [names[i]] for k, i in P.PATRON_SLOT.items()}
        for name, kind, _fr, to, _lab in pl["moves"]:
            if kind != "OBJ":
                continue
            for k in list(inst):
                if name in inst[k]:
                    inst[k].remove(name)
                    inst.setdefault(to, []).append(name)
        for (_k, s), (n, _c) in pl.get("add", {}).items():
            inst.setdefault(s, []).append(n)
        for (_k, s), ns in pl.get("join", {}).items():
            inst.setdefault(s, []).extend(ns)
        inst = {k: l for k, l in inst.items() if l}    # (OBJ 0 is Sal's: a patron moved there wears her colours, and VARIANT_CUTS slot 0 entries show it is a swap target)
    looks = names + [n for n in P.EXTRA_LOOKS.get(v, []) if n not in names]
    cuts = P.VARIANT_CUTS.get(v, {})
    allowed = {l: [s for s in sorted(inst) if s not in cuts.get(l, [])] for l in looks}
    return looks, inst, allowed


def main():
    only = sys.argv[1:]
    for v in P.PLANS:
        if v == "cowboys" or (only and v not in only):
            continue
        looks, inst, allowed = venue_table(v)
        n = sum(len(a) for a in allowed.values())
        cap = BG_CAPACITY_NOW.get(v, BG_CAPACITY_DEFAULT)
        print("%-12s looks %d  instances %d (OBJ %s)  combos %d  BG slots in the engine now %d%s" % (
            v, len(looks), len(inst), sorted(inst), n, cap, "   <-- NEEDS %d MORE" % (len(inst) - cap) if len(inst) > cap else ""))
        if only:
            for l in looks:
                print("   %-8s OBJ %s" % (l, allowed[l]))
            print("   owners", {k: inst[k] for k in sorted(inst)})


if __name__ == "__main__":
    main()
