"""The Graphics Atlas self-check: every "now" claim of the page against the game and the atlas capture.

Owner 2026-10-28: "I need to be able to trust the atlas". The hand-written parts of build.py (NAMES, PATRON_SLOT, BG_PATRON, SALOON_LOOKS,
users(), PLANS) say what the game does now or what is planned. verify_now(ns) (ns = build.py's globals) exits non-zero and lists every place
where the capture (out/atlas/data) or the game's own tables (game_truth.py: build/palettes.c, src/game.h, src/mirror.c) disagree with a "now"
claim, where a planned item is already in the game, and where a look has no back view to show.
"""
import re
import sys

import game_truth

KIND_OF = {"Sal": "Sal", "Tip coin": "Tip coin", "Pour sparkle": "Perfect-pour sparkle", "PERFECT cue": "Perfect-pour sparkle",
           "Full mug": "Mug: full", "Fill glass": "Fill glass", "Breaking glass": "Breaking glass", "Empty mug": "Mug: empty",
           "Show dancers": "Dancers"}
SKIP_KINDS = ("Mug: drinking", "Mirrored copy / dust puff")


def first(s):
    return s.split(",")[0].split(" (")[0].strip().upper()


def verify_now(ns):
    T = game_truth.truth()
    venues, NAMES, PLANS, load, hexc, users = (ns[x] for x in ("venues", "NAMES", "PLANS", "load", "hexc", "users"))
    PATRON_SLOT, BG_PATRON, SALOON_LOOKS = ns["PATRON_SLOT"], ns["BG_PATRON"], ns["SALOON_LOOKS"]
    errs = []
    for v in venues:
        k = v["key"]
        lv = load("level_" + k)["cgb"]
        E = lambda msg, v=v: errs.append("%s: %s" % (v["name"], msg))
        inst = T["inst"][k]
        # a. the patron palettes in palette RAM are the game's (assets/palettes.json)
        for i, cols in enumerate(inst):
            for kind, sl, pals in (("OBJ", T["obj_of"][i], lv["pal"]["obj"]), ("BG", T["bg_of"][i], lv["pal"]["bg"])):
                if kind == "BG" and i == 4:
                    continue                # the Saloon's BG 5 holds the stage's colours above the split line; the patron's only below it
                rep = tuple(pals[sl]["rep"][1:])
                if rep != tuple(cols):
                    E("%s %d holds %s in the capture, the game's patron palette %d is %s" % (kind, sl, [hexc(c) for c in rep], i, [hexc(c) for c in cols]))
        # b. the slot numbers the page assumes
        for i in range(3):
            if PATRON_SLOT.get(T["obj_of"][i]) != i:
                E("page says OBJ %d is not patron %s, the game's OBJPAL_PATRON_%s is OBJ %d" % (T["obj_of"][i], "ABC"[i], "ABC"[i], T["obj_of"][i]))
            if BG_PATRON.get(T["bg_of"][i]) != i:
                E("page says BG %d is not patron %s, the game's is BG %d" % (T["bg_of"][i], "ABC"[i], T["bg_of"][i]))
        if list(ns["INST_OBJ"]) != T["obj_of"] or list(ns["INST_BG"]) != T["bg_of"]:
            E("page maps palette instances to OBJ %s / BG %s, the game's game.h has OBJ %s / BG %s" % (ns["INST_OBJ"], ns["INST_BG"], T["obj_of"], T["bg_of"]))
        # c. who the page says is in each patron palette against the game's tables
        want = {}
        if k == "cowboys":
            for nm, ps in T["saloon"]:
                for p in ps:
                    want.setdefault(("OBJ", T["obj_of"][p]), set()).add(nm)
                    want.setdefault(("BG", T["bg_of"][p]), set()).add(nm)
            if [first(n) for n, _ in SALOON_LOOKS] != [n for n, _ in T["saloon"]]:
                E("page lists the Saloon's looks as %s, the game's sal_combo has %s" % ([first(n) for n, _ in SALOON_LOOKS], [n for n, _ in T["saloon"]]))
            for (n, ps), (gn, gps) in zip(SALOON_LOOKS, T["saloon"]):
                if sorted(ps) != sorted(gps):
                    E("%s: page says palette instances %s, sal_combo has %s" % (first(n), sorted(ps), sorted(gps)))
        else:
            for i in range(3):
                want[("OBJ", T["obj_of"][i])] = {first(NAMES[k][i])}
                want[("BG", T["bg_of"][i])] = {first(NAMES[k][i])}
        for kind in ("OBJ", "BG"):
            for sl in range(8):
                claim = {first(x) for x in users(kind, v, sl)[0]}
                if claim != want.get((kind, sl), set()):
                    E("%s %d: page says %s, the game has %s" % (kind, sl, sorted(claim) or "no patron", sorted(want.get((kind, sl), set())) or "no patron"))
        # d. the capture's lifted patrons sit in the slots the game's tables give looks A-C
        for o in lv["objs"]:
            m_ = re.match(r"Patron ([ABC]) \(", o["kind"])
            if m_ and k != "cowboys":
                exp = T["obj_of"]["ABC".index(m_.group(1))]
                if set(o["slots"]) != {exp}:
                    E("capture: %s is in OBJ %s, the game's palette is OBJ %d" % (o["kind"], o["slots"], exp))
        # e. the non-patron users of each OBJ palette
        used = {}
        for o in lv["objs"]:
            for s in o["slots"]:
                used.setdefault(s, set()).add(o["kind"])
        for sl in range(8):
            oth = users("OBJ", v, sl)[1]
            claimed = {KIND_OF[x] for x in oth if x in KIND_OF}
            unknown = [x for x in oth if x not in KIND_OF and not x.startswith("Boss")]
            if unknown:
                E("OBJ %d: no way to check %s against the capture" % (sl, unknown))
            seen = {x for x in used.get(sl, set()) if not x.startswith("Patron") and x not in SKIP_KINDS}
            for x in sorted(claimed - seen):
                E("OBJ %d: page says %s, the capture does not draw it there" % (sl, x))
            for x in sorted(seen - claimed):
                E("OBJ %d: the capture draws %s there, the page does not say so" % (sl, x))
        # f. the BG palettes above the playfield
        rows = lv["attr"]["pal"]
        for sl in range(8):
            for x in users("BG", v, sl)[1]:
                if x == "HUD" and str(sl) not in rows[0]:
                    E("BG %d: page says HUD, row 0 of the capture has %s" % (sl, sorted(set(rows[0]))))
                if x == "Stage" and not any(str(sl) in r for r in rows[1:5]):
                    E("BG %d: page says Stage, rows 1-4 of the capture have %s" % (sl, sorted(set("".join(rows[1:5])))))
        # g. planned items that are already in the game
        pl = PLANS.get(k, {})
        for (kind, sl), ch in pl.get("recolour", {}).items():
            cur = (lv["pal"]["obj"] if kind == "OBJ" else lv["pal"]["bg"])[sl]["rep"]
            if isinstance(ch, dict) and all(hexc(cur[i]).lower() == hx.lower() for i, hx in ch.items()):
                E("planned: %s %d colours %s are already in the game" % (kind, sl, sorted(ch)))
        for start, kind, fr, to, label in pl.get("moves", []):
            if kind != "OBJ":
                continue
            if start in KIND_OF and KIND_OF[start] in used.get(to, set()) and KIND_OF[start] not in used.get(fr, set()):
                E("planned: %s OBJ %d -> %d is already in the game" % (start, fr, to))
            if k == "cowboys" and any(first(start) == nm and T["obj_of"][p] == to for nm, ps in T["saloon"] for p in ps):
                E("planned: %s -> OBJ %d is already in the game (sal_combo)" % (start, to))
        # h. every look shows a back view (owner 2026-10-28: all current backs, except where a planned back replaces one)
        n_looks = len(T["saloon"]) if k == "cowboys" else 3
        shown = ns["back_rows_by_look"](v)
        for i in range(n_looks):
            if i >= len(shown) or not shown[i]:
                E("look %s has no back view to show" % "ABCDEFGH"[i])
    if errs:
        print("\nATLAS SELF-CHECK FAILED: %d claims disagree with the game or the capture:" % len(errs), file=sys.stderr)
        for e in errs:
            print("  - " + e, file=sys.stderr)
        sys.exit(1)
