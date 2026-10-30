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


def verify_shown(ns):
    """Every (look, palette) combination the game can spawn has its front/back pair on the Patrons table (build.py SHOWN); else the build fails."""
    want = {(k, l, p) for k, looks in game_truth.spawn_combos().items() for l, ps in looks.items() for p in ps}
    seen = ns["SHOWN"]
    errs = ["%s look %d in palette instance %d (OBJ %d) is not on the Patrons table" % (k, l, p, ns["INST_OBJ"][p]) for k, l, p in sorted(want - seen)]
    errs += ["%s look %d in palette instance %d is on the Patrons table, the game never spawns it" % x for x in sorted(seen - want)]
    if errs:
        print("\nATLAS SELF-CHECK FAILED (patron palettes shown):", file=sys.stderr)
        for e in errs:
            print("  - " + e, file=sys.stderr)
        sys.exit(1)


# ---- checks that need no capture and no ROM (tests/test_atlas_page.py runs these in `make test`) ----
PICKS_GLOB = "docs/dev/concepts/*/PICKS.md"
Q_RE = re.compile(r"^(Q\d+|\d{4}-\d\d-\d\d)$")
# Patrons the PICKS notes accept in prose (Q24-Q37), not in the round tables; names as the notes spell them (renames applied after).
PICKS_PROSE = ["MOTH", "BLOB", "VIXEN_B", "VIXEN_D", "ASTRONAUT", "CLANK", "BUBBLE"]


def picks_names(root):
    """{accepted patron name: PICKS file} from every docs/dev/concepts/*/PICKS.md: the final-fronts table rows (Round 3) and the prose accepts,
    with the owner's renames applied (the 'Names' paragraph). A patron marked held is not accepted."""
    import glob
    import os
    res = {}
    for f in sorted(glob.glob(os.path.join(root, PICKS_GLOB))):
        t = open(f).read()
        ren = {}
        m = re.search(r"## Names.*?\n\n(.*?)(?:\n\n|\Z)", t, re.S)
        if m:
            for a, b in re.findall(r"([A-Z_]+) -> ([A-Z_]+)", m.group(1).replace("\n", " ")):
                ren[a] = b
        m = re.search(r"## Round 3.*?\n(.*?)\n\n(?:Trims|## )", t, re.S)
        names = []
        if m:
            for row in m.group(1).splitlines():
                cells = [c.strip() for c in row.strip().strip("|").split("|")]
                if len(cells) != 2 or cells[0] in ("Venue", "---"):
                    continue
                txt = re.sub(r"\([^)]*held[^)]*\)", "", cells[1])
                names += re.findall(r"\b([A-Z]{2,})\b", txt)
            names += PICKS_PROSE
        for n in names:
            res[ren.get(n, n)] = os.path.relpath(f, root)
    return res


def plan_names(P):
    """Every patron name the plan carries a row for: the game's looks, EXTRA_LOOKS, NEW_PATRONS, PLANS add / join / extras."""
    out = {x.split(",")[0].strip().upper() for v in P.NAMES.values() for x in v}
    out |= {n.upper() for v in P.EXTRA_LOOKS.values() for n in v}
    out |= {n for v in P.NEW_PATRONS.values() for n, _ in v}
    for pl in P.PLANS.values():
        out |= {a[0] for a in pl.get("add", {}).values()}
        out |= {n for ns in pl.get("join", {}).values() for n in ns}
        out |= {e["name"] for e in pl.get("extras", [])}
    return out


def check_plan(P, root):
    """Errors in the hand-kept plan alone (plan_data module P): every PLANS entry carries its Qn, every accepted pick has a row."""
    errs = []
    for k in P.NAMES:
        pl = P.PLANS.get(k)
        if pl is None:
            errs.append("%s: no PLANS entry" % k)
            continue
        q = pl.get("q")
        if not q or not all(Q_RE.match(x) for x in q):
            errs.append("PLANS[%s] carries no Qn / dated owner statement (q=%r)" % (k, q))
    have = plan_names(P)
    for n, f in sorted(picks_names(root).items()):
        if n not in have:
            errs.append("accepted in %s but has no plan row: %s" % (f, n))
    return errs


def verify_plan(P, root):
    errs = check_plan(P, root)
    if errs:
        print("\nATLAS SELF-CHECK FAILED (plan data):", file=sys.stderr)
        for e in errs:
            print("  - " + e, file=sys.stderr)
        sys.exit(1)
