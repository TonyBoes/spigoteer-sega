"""Cross-screen summary: which palette slots and tile slots are the same on every level screen, which change per venue, which animate."""
import re
from collections import defaultdict
from pathlib import Path

import analyze as A

ROOT = Path(__file__).resolve().parent.parent.parent

BG_ROLES = {0: "bar / counter (BGPAL_BAR)", 1: "HUD (BGPAL_HUD)", 2: "patron variant A (BGPAL_PATRON)", 3: "patron variant B", 4: "patron variant C",
            5: "venue stage A (BGPAL_STAGE)", 6: "venue stage B (BGPAL_STAGE_B)", 7: "venue's second bar palette: keg / spout; enhanced row S (BGPAL_BAR_B)"}
OBJ_ROLES = {0: "Sal, the bartender (OBJPAL_BARTENDER)", 1: "full mug (OBJPAL_MUG_FULL)", 2: "empty mug / breaking glass (OBJPAL_MUG_EMPTY)",
             3: "lifted patron A (OBJPAL_PATRON_A)", 4: "extra palette of an enhanced patron variant (OBJPAL_ENH)",
             5: "tip coin (same every venue) \u21c4 show dancers (per venue): swapped in when a tip appears or a show starts; no tips or shows in boss fights (OBJPAL_COIN = OBJPAL_DANCER)", 6: "lifted patron B (OBJPAL_PATRON_B)", 7: "lifted patron C (OBJPAL_PATRON_C)"}


def roles():
    """The slot roles: the friendly labels above, with the BGPAL_* / OBJPAL_* defines of src/game.h (name, number, comment) read from the source."""
    defs = []
    for line in (ROOT / "src" / "game.h").read_text().splitlines():
        m = re.match(r"#define (BGPAL|OBJPAL)_(\w+)\s+(\d+)\s*(?://\s*(.*))?$", line)
        if m:
            defs.append(dict(kind="bg" if m.group(1) == "BGPAL" else "obj", name=m.group(1) + "_" + m.group(2), slot=int(m.group(3)), comment=(m.group(4) or "").strip()))
    return dict(bg=BG_ROLES, obj=OBJ_ROLES, defines=defs)


def is_level(scr):
    return scr["group"].startswith("Levels (ARCADE") or scr["group"].startswith("Levels (CLASSIC")


def show_pairs(screens):
    """(level id, show id) for each ARCADE venue: a show runs inside its level, so the two screens are one level for the summary."""
    ids = {s["id"] for s in screens}
    return [(s["id"], "show_" + s["id"][len("level_"):]) for s in screens if s["group"].startswith("Levels (ARCADE") and "show_" + s["id"][len("level_"):] in ids]


def build(screens, side, models):
    out = {}
    all_ids = [s["id"] for s in screens]
    arcade = [s["id"] for s in screens if s["group"].startswith("Levels (ARCADE")]
    levels = [s["id"] for s in screens if is_level(s)]
    out["level_screens"] = levels
    out["venue_screens"] = arcade
    out["n_screens"] = len(all_ids)
    pairs = show_pairs(screens)
    out["show_pairs"] = pairs
    for model in models:
        mo = {}
        have = [i for i in all_ids if (i, model) in side]
        lv = [i for i in levels if (i, model) in side]
        av = [i for i in arcade if (i, model) in side]
        if model == "cgb":
            pal = {}
            for kind in ("bg", "obj"):
                recs = []
                for p in range(8):
                    key, chg, used = (("bgpal", "bgpal_changes", "bgpal_used") if kind == "bg" else ("objpal", "objpal_changes", "objpal_used"))
                    vals = {i: tuple(side[(i, model)][key][p]) for i in have}
                    groups = defaultdict(list)
                    for i in have:
                        if side[(i, model)][used][p]:
                            groups[vals[i]].append(i)
                    lvals = {vals[i] for i in lv}
                    lchg = [i for i in lv if side[(i, model)][chg][p]]
                    achg = [i for i in have if side[(i, model)][chg][p]]
                    lunused = [i for i in lv if not side[(i, model)][used][p]]
                    # swapped by an event: a venue's show screen holds a value its level screen never does (or the reverse), and the slot is drawn on one of them
                    seen = key + "_seen"
                    swapped = [lid for lid, sid in pairs if (lid, model) in side and (sid, model) in side
                               and set(side[(lid, model)][seen][p]) != set(side[(sid, model)][seen][p])
                               and (side[(lid, model)][used][p] or side[(sid, model)][used][p])]
                    show_vals = sorted({v for lid, sid in pairs if lid in swapped for v in set(side[(sid, model)][seen][p]) - set(side[(lid, model)][seen][p])})
                    if swapped:
                        cls = "swapped during play (by a show / tip)"
                    elif len(lunused) == len(lv):
                        cls = "not seen in the sampled level windows"
                    elif lchg and len(lvals) == 1:
                        cls = "same start colours on every level, animates"
                    elif lchg:
                        cls = "per venue, and animates on some"
                    elif len(lvals) == 1:
                        cls = "permanent: the same on every level screen"
                    else:
                        cls = "per venue / per level"
                    recs.append(dict(slot=p, cls=cls, distinct_levels=len(lvals), n_levels=len(lv), distinct_all=len(groups),
                                     used_all=sum(len(g) for g in groups.values()), n_all=len(have),
                                     levels=[dict(id=i, cols=list(vals[i]), used=bool(side[(i, model)][used][p])) for i in lv],
                                     groups=[dict(cols=list(c), screens=ids) for c, ids in sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))],
                                     swapped_levels=swapped, swapped_cols=[list(v) for v in show_vals], distinct_swapped=len(show_vals),
                                     changing_levels=lchg, changing_all=achg, unused_levels=lunused))
                pal[kind] = recs
            mo["pal"] = pal
        else:
            d = {}
            for k in ("BGP", "OBP0", "OBP1"):
                groups = defaultdict(list)
                for i in have:
                    groups[side[(i, model)]["dmg"][k]].append(i)
                d[k] = dict(groups=[dict(value=v, shades=A.dmg_palette(v), screens=ids) for v, ids in sorted(groups.items(), key=lambda kv: -len(kv[1]))],
                            levels=sorted({side[(i, model)]["dmg"][k] for i in lv}))
            mo["dmg"] = d
        # tiles: per bank, per slot over the level screens
        banks = []
        for b in range(2 if model == "cgb" else 1):
            cls = []
            for s in range(384):
                hs = {side[(i, model)]["tilehash"][b][s] for i in lv}
                loaded = [side[(i, model)]["loaded"][b][s] == "1" for i in lv]
                anim = any(s in side[(i, model)]["changed"][b] for i in lv)
                used = any(side[(i, model)]["use"][b][s] for i in lv)
                if not any(loaded):
                    c = "."                                    # empty on every level screen
                elif anim:
                    c = "A"                                    # changes while a level runs (stage animation, dancers, ...)
                elif len(hs) == 1 and all(loaded):
                    c = "S"                                    # the same tile on every level screen
                else:
                    c = "V"                                    # differs from level screen to level screen (per venue / per mode)
                cls.append(c)
            regs = []
            for rg in A.REGIONS:
                seg = cls[rg["lo"]:rg["hi"] + 1]
                regs.append(dict(S=seg.count("S"), V=seg.count("V"), A=seg.count("A"), E=seg.count("."), total=len(seg)))
            # how often each slot's contents change across ALL screens: distinct contents per slot (empty counted)
            distinct = []
            for s in range(384):
                distinct.append(len({side[(i, model)]["tilehash"][b][s] for i in have}))
            banks.append(dict(bank=b, cls="".join(cls), regions=regs, distinct_all=distinct))
        mo["tiles"] = banks
        out[model] = mo
    return out
