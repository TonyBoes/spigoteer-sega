"""The Graphics Atlas self-check: every "now" claim of the page against the game and the atlas capture.

Owner 2026-10-28: "I need to be able to trust the atlas". The hand-written parts of build.py (NAMES, PATRON_SLOT, BG_PATRON, SALOON_LOOKS,
users(), PLANS) say what the game does now or what is planned. verify_now(ns) (ns = build.py's globals) exits non-zero and lists every place
where the capture (out/atlas/data) or the game's own tables (game_truth.py: build/palettes.c, src/game.h, src/mirror.c) disagree with a "now"
claim, where a planned item is already in the game, and where a look has no back view to show.
"""
import os
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
    for k, d in getattr(P, "PATRON_ART", {}).items():                    # the one art table: known patron, files on disk, a source
        for first, (fr, bk, src) in d.items():
            if first not in [n.split(",")[0].strip().lower() for n in P.NAMES.get(k, [])]:
                errs.append("PATRON_ART %s/%s: not a patron of that venue" % (k, first))
            if not re.search(r"Q\d+|\d{4}-\d\d-\d\d", src or ""):
                errs.append("PATRON_ART %s/%s: no Qn or dated source" % (k, first))
            for f in (fr, bk):
                if f != "old" and not os.path.exists(os.path.join(root, "docs/dev/concepts/patron_pass", k, f + ".txt")):
                    errs.append("PATRON_ART %s/%s: file %s.txt is missing" % (k, first, f))
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


# ---- picture level: the page's thumbnails against the capture (what the ROM really draws) and the patron rules ----
def swap12(rows):
    return [x.translate(str.maketrans("-+", "+-")) for x in rows]


def patron_rule_errors(rows, gaps=(), side="front"):
    """Owner's patron rules for art not in the game yet: column x=15 clear (10-28), no ink line on the bottom row (10-29: no run of two or more
    darkest pixels on row 15), no index-0 pixel enclosed by the figure (gen_art index0_holes; gaps the owner drew are listed)."""
    import os
    sys.path.insert(0, os.path.join(game_truth.ROOT, "tools"))
    import gen_art
    errs = []
    if len(rows) != 16 or any(len(r) != 16 for r in rows):
        return ["not 16x16"]
    if side == "front" and any(r[15] != "." for r in rows):          # the owner's x=15 rule is for the fronts (10-28); backs may use it
        errs.append("column x=15 is not clear (rows %s)" % [y for y, r in enumerate(rows) if r[15] != "."])
    ink = [x for x in range(16) if rows[15][x] == "#" and rows[14][x] != "#"]
    if ink:
        errs.append("bottom row has an ink line under the body at x %s: %s" % (ink, rows[15]))
    holes = gen_art.index0_holes(rows) - set(gaps)
    if holes:
        errs.append("index 0 enclosed at (x, y) %s" % sorted(holes)[:6])
    return errs


def verify_pictures(ns):
    """a. the game's text art (assets/art/patrons, GUS and ASH swapped as the Color game does) equals the capture's VRAM tiles for every look;
    b. every thumbnail from the game is, pixel for pixel and colour for colour, the captured tiles with the captured palette RAM (re-read from the
       PNG that is published); c. every thumbnail from the plan passes the patron rules (x=15, bottom row, holes)."""
    import os
    from PIL import Image
    T = game_truth.truth()
    load, hexc, venues, OUT = ns["load"], ns["hexc"], ns["venues"], ns["OUT"]
    vkey = {v["key"]: v for v in venues}
    gaps_plan = ns.get("PLANNED_GAPS", {})
    exc = set(ns.get("ART_RULE_EXCEPTIONS", {}))
    used_exc = set()
    errs = []
    for k, idx, gf, gb, cf, cb in ns["GAME_ART"]:
        sw = (lambda r: swap12(r)) if (k in ("cowboys", "lumberjacks") and idx == 2) else (lambda r: r)
        for side, txt, cap in (("front", gf, cf), ("back", gb, cb)):
            if cap is None:
                errs.append("%s look %d %s: its tiles are not loaded in the capture" % (k, idx, side))
            elif sw(txt) != cap:
                n = sum(a != b for r1, r2 in zip(sw(txt), cap) for a, b in zip(r1, r2))
                errs.append("%s look %d %s: assets/art/patrons text differs from the capture's tiles in %d pixels (stale capture, or a transform the page does not know)" % (k, idx, side, n))
    for pic in ns["PICS"]:
        k, name, idx, side, inst = pic["who"]
        where = "%s %s %s" % (k, name.split(",")[0], side)
        im = Image.open(os.path.join(os.path.dirname(OUT), pic["rel"]))
        if im.size != (16, 16) or im.mode != "P":
            errs.append("%s: %s is %s %s, not a 16x16 indexed picture" % (where, pic["rel"], im.size, im.mode))
            continue
        pal = im.getpalette()
        got_cols = ["#%02X%02X%02X" % tuple(pal[3 * i:3 * i + 3]) for i in range(4)]
        got = ["".join(".-+#"[im.getpixel((x, y))] for x in range(16)) for y in range(16)]
        if got != pic["rows"]:
            errs.append("%s: the published PNG is not the picture the page means to show" % where)
        if pic["src"] == "game":
            cf, cb = ns["captured_look"](vkey[k], idx)
            cap = cf if side == "front" else cb
            if got != cap:
                errs.append("%s: the thumbnail is not the capture's tiles (%d pixels differ)" % (where, sum(a != b for r1, r2 in zip(got, cap or ["?" * 16] * 16) for a, b in zip(r1, r2))))
            lv = load("level_" + k)["cgb"]["pal"]
            slot = T["obj_of"][inst] if inst is not None and inst < 5 else None
            if slot is None:
                errs.append("%s: no palette instance" % where)
                continue
            want = [hexc(lv["bg"][0]["rep"][0])] + [hexc(c) for c in lv["obj"][slot]["rep"][1:]]
            if not pic.get("palplan") and [c.upper() for c in got_cols] != [c.upper() for c in want]:
                errs.append("%s: thumbnail colours %s, the capture's palette RAM (OBJ %d) has %s" % (where, got_cols, slot, want))
        else:
            nm = name.split(",")[0].strip().upper()
            g = set(gaps_plan.get((k, nm, side), ()))
            if idx is not None:                       # a look the game ships: gaps its art already has stay
                import os as _os
                sys.path.insert(0, _os.path.join(game_truth.ROOT, "tools"))
                import gen_art
                cf, cb = ns["captured_look"](vkey[k], idx)
                g |= gen_art.index0_holes(cf if side == "front" else cb) if (cf if side == "front" else cb) else set()
            found = patron_rule_errors(pic["rows"], g, side)
            for e in found:
                rule = "bottom" if e.startswith("bottom") else "holes" if e.startswith("index 0") else "x15"
                if (k, nm, side, rule) in exc:
                    used_exc.add((k, nm, side, rule))
                else:
                    errs.append("%s (planned art): %s" % (where, e))
    for x in sorted(exc - used_exc):
        errs.append("ART_RULE_EXCEPTIONS %s is no longer needed (the art passes or is not shown): remove it" % (x,))
    if errs:
        print("\nATLAS SELF-CHECK FAILED (pictures): %d problems" % len(errs), file=sys.stderr)
        for e in errs:
            print("  - " + e, file=sys.stderr)
        sys.exit(1)


def verify_primary(ns):
    """Every Saloon look has a plan primary palette, and it is one of the instances the game gives that look."""
    errs = []
    for n, ps in ns["SALOON_LOOKS"]:
        pr = ns["SALOON_PRIMARY"].get(n)
        if pr is None:
            errs.append("Saloon look %s has no SALOON_PRIMARY entry" % n)
        elif pr not in ps:
            errs.append("SALOON_PRIMARY[%s] = %d, but sal_combo gives %s only %s" % (n, pr, n, ps))
    for n in ns["SALOON_PRIMARY"]:
        if n not in [x for x, _ in ns["SALOON_LOOKS"]]:
            errs.append("SALOON_PRIMARY has %s, which is not a look in sal_combo" % n)
    if errs:
        print("\nATLAS SELF-CHECK FAILED (primary)\n  " + "\n  ".join(errs))
        raise SystemExit(1)


def verify_slots(ns):
    """Plan slots are unique per venue: two looks may share a plan OBJ slot only with the same colours (a shared palette), and the
    page's dual 'plan OBJ n / game OBJ m' numbers must differ; the NOW line is labelled."""
    errs = []
    use = {}
    for key, sl, name, cols in ns["SLOTS"]:
        use.setdefault((key, sl), {}).setdefault(cols, []).append(name)
    for (key, sl), d in sorted(use.items()):
        if len(d) > 1:
            errs.append("%s: plan OBJ %d is given to looks with different colours: %s" % (key, sl, "; ".join("%s %s" % (", ".join(n), c) for c, n in d.items())))
    errs.extend(ns.get("FIELD_ERRS", []))   # a patron on two BG palettes, or a venue whose plan does not fit its palettes
    for key, name, kind, a, b in ns["DUAL"]:
        if a == b:
            errs.append("%s %s: dual %s numbers are the same (%d)" % (key, name, kind, a))
    if errs:
        print("\nATLAS SELF-CHECK FAILED (slots)\n  " + "\n  ".join(errs))
        raise SystemExit(1)
    print("self-check: plan slots unique per venue (%d looks, %d dual numbers)" % (len(ns["SLOTS"]), len(ns["DUAL"])))
