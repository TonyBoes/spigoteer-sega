"""Which CGB OBJ palette slots are free in each level: the code's declared users of every slot, checked against what the sampled frames showed.

Sampling alone cannot prove a slot free (an event may not happen in the 3 s window), so the verdict comes from the source: every use of an
OBJPAL_* constant, set_sprite_palette and OCPS write in src/ was read (see SLOTS below; other screens - title, minigames, bosses, story, credits - reload
their own palettes and the level load puts the level's back, so they never share a level). The sampled OAM use is only a cross-check: a slot seen in
use where the table says free, or a slot declared "always" that no sampled frame drew, is reported as a warning.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
GROUPS = ["cowboys", "sports", "lumberjacks", "chefs", "divers", "robots", "punks", "ninjas", "zoo", "aliens"]
CLASSIC_GROUP = {"classic_3": "sports", "classic_6": "punks", "classic_12": "aliens"}

# slot -> (always | event | enh, label, [(file, regex of the line)])
SLOTS = {
    0: ("always", "Sal, the bartender", [("src/render.c", r"\| OBJPAL_BARTENDER;"), ("src/main_cold.c", r"set_sprite_palette\(OBJPAL_BARTENDER"), ("src/antics.c", r"pr = OBJPAL_BARTENDER")]),
    1: ("always", "full mug (venue colours)", [("src/mugs.c", r"o->prop = is_cgb \? OBJPAL_MUG_FULL"), ("src/lift.c", r"spr_full_p = S_PALETTE \| OBJPAL_MUG_FULL"),
                                               ("src/venue.c", r"set_sprite_palette\(OBJPAL_MUG_FULL"), ("src/pour.c", r"pal = OBJPAL_MUG_FULL")]),
    2: ("event", "empty mug coming back, breaking glass (tap end)", [("src/lift.c", r"spr_empty_p = S_PALETTE \| OBJPAL_MUG_EMPTY"), ("src/venue.c", r"set_sprite_palette\(OBJPAL_MUG_EMPTY"),
                                                                    ("src/mugs.c", r"p = spr_empty_p \| S_FLIPX")]),
    3: ("event", "lifted patron A (variants 0 and 3)", [("src/lift.c", r"lift_pal\[4\] = \{ OBJPAL_PATRON_A"), ("src/lift.c", r"set_sprite_palette\(lift_pal\[v\]")]),
    4: ("enh", "enhanced patron variant, when lifted", [("src/enhance.c", r"set_sprite_palette\(OBJPAL_ENH"), ("build/palettes.h", r"#define PATRON_X_IDS"), ("build/patron_enh.h", r"enh_tab\[10\]\[24\]")]),
    5: ("event", "tip coin; show dancers", [("src/render.c", r"o->prop = is_cgb \? OBJPAL_COIN"), ("src/render.c", r"OCPS_REG = 0x80 \| \(OBJPAL_COIN"), ("src/lr.c", r"uint8_t pal = \(is_cgb \? OBJPAL_DANCER"),
                                         ("src/rom0_relief.c", r"flags = is_cgb \? OBJPAL_DANCER"), ("src/venue.c", r"set_sprite_palette\(OBJPAL_DANCER"), ("src/classic.c", r"tip_timer = TIP_FRAMES")]),
    6: ("event", "lifted patron B (variant 1)", [("src/lift.c", r"lift_pal\[4\] = \{ OBJPAL_PATRON_A"), ("src/lift.c", r"set_sprite_palette\(lift_pal\[v\]")]),
    7: ("event", "lifted patron C (variant 2)", [("src/lift.c", r"lift_pal\[4\] = \{ OBJPAL_PATRON_A"), ("src/lift.c", r"set_sprite_palette\(lift_pal\[v\]")]),
}
LEGEND = ("In use (always): drawn in the level's normal play. Event only: drawn only when its event happens (the event is named). "
          "FREE in this level: no code path of the level, its tips, its show or its lifted patrons uses the slot. Hover or focus a cell for the sources.")
PLANNED = "Planned: the tip coin moves to Sal's palette (OBJ 0); then OBJ 5 is used only by the show dancers. That change is not in the ROM yet; the table shows the ROM as built."


def _line(src, rx):
    try:
        for n, t in enumerate((ROOT / src).read_text().splitlines(), 1):
            if re.search(rx, t):
                return "%s:%d" % (src, n)
    except OSError:
        pass
    return src + ":?"


def _enh():
    """(x_ids, lifted_attr_rows): the group's extra OBJ palette (255 none) and the 8 lifted-column OAM attributes of each group, from the generated headers."""
    x = re.search(r"#define PATRON_X_IDS \{([^}]*)\}", (ROOT / "build" / "palettes.h").read_text())
    x_ids = [int(v) for v in x.group(1).split(",")]
    tab = (ROOT / "build" / "patron_enh.h").read_text()
    rows = re.findall(r"\{((?:\s*\d+,){23}\s*\d+)\s*\},\s*//\s*(\w+)", tab)
    attrs = {name: [int(v) for v in r.split(",")][16:24] for r, name in rows}
    return x_ids, attrs


def build(screens, side):
    x_ids, attrs = _enh()
    levels = []
    for s in screens:
        sid = s["id"]
        if s["group"].startswith("Levels (ARCADE"):
            g = sid[len("level_"):]
            ids = [sid, "show_" + g]
        elif sid in CLASSIC_GROUP:
            g, ids = CLASSIC_GROUP[sid], [sid]
        else:
            continue
        gi = GROUPS.index(g)
        cells = []
        for slot in range(8):
            kind, label, srcs = SLOTS[slot]
            notes = [_line(f, rx) for f, rx in srcs]
            if kind == "enh":
                lifted = sorted({i % 4 for i, a in enumerate(attrs[g]) if a & 7 == 4}) if x_ids[gi] != 255 else []
                if lifted:
                    st, lab = "event", "enhanced patron variant " + "/".join(str(v) for v in lifted) + ", when lifted"
                else:
                    st, lab = "free", "FREE in this level"
                notes.append("%s: x_ids[%d] = %s; lifted-column attributes %s" % (g, gi, x_ids[gi] if x_ids[gi] != 255 else "none", attrs[g]))
            else:
                st, lab = kind, label
            seen = [i for i in ids if (i, "cgb") in side and side[(i, "cgb")]["objpal_used"][slot]]
            obs = ("sampled sprites used it on: " + ", ".join(seen)) if seen else "no sampled sprite used it"
            warn = None
            if st == "free" and seen:
                warn = "slot %d is declared free in %s but sprites used it on %s" % (slot, sid, ", ".join(seen))
            elif st == "always" and not any(i == ids[0] for i in seen):
                warn = "slot %d is declared always-used in %s but no sampled level frame drew it" % (slot, sid)
            cells.append(dict(slot=slot, state=st, label=lab, notes=notes, observed=obs, warn=warn))
        levels.append(dict(id=sid, name=s["name"], group=s["group"], screens=ids, cells=cells))
    warnings = [c["warn"] for lv in levels for c in lv["cells"] if c["warn"]]
    return dict(levels=levels, legend=LEGEND, planned=PLANNED, warnings=warnings)
