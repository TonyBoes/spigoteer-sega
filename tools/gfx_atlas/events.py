"""Everything a level can draw, not just the sampled moment: the sprite-producing events of a level, driven by the tests' own pokes and hooks.

For a level screen (an ARCADE venue or a CLASSIC level) `capture` takes the screen's own sampled window plus a scripted run of the events
below, and reduces every sampled frame to: the sprites drawn (each labelled by what it is, from its tile id: the tile layout is documented
in src/game.h), the OBJ palettes they used, the OBJ and BG tiles in use, the BG tiles per BG palette, and a few small stills of each event.
Phases (each is a run of frames sampled every other frame):
  play        the level's own play script (the bartender fills, serves, walks between bars; mugs slide, empties return; a tip coin)
  lifts       patrons A, B and C lifted by the test hook (src/lift.c lift_hook_op / lift_hook_p), each variant at least once, the
              enhanced variant included (OBJ 4 + bank-1 tiles where the venue has one), then dropped
  edge        a patron entering from the left edge (LIFT_EDGE sprite) and a served one leaving
  mugs        a full mug, an empty one, a mug held while drinking, a breaking glass and its shards
  tip         the tip coin on the counter and its blink, and a tip pocketed during the show (the HUD icon)
  show        the dancers' show (OBJ 5 swapped to the show palette)
  fail        a life lost (Sal's fail pose)
  story       STORY mode only: the perfect pour (sparkle) and the PERFECT cue
Only reads emulator state; changes only what the tests change.
"""
import os
import traceback
from collections import defaultdict

from PIL import Image

import analyze as A
import capture as C
import freepal
import objects as OB

MAX_P, MAX_M = 16, 20
WALKING, DRINKING = 1, 3
FULL, EMPTY, BREAKING, HELD = 1, 2, 3, 4
CELL_W, CELL_H = 96, 56          # one still of an event strip
STILLS = 3                        # stills per event
EV_CAP = 24                       # sprites shown per event
ROW_H = CELL_H                    # a row of the event block of the packed image: the stills, then the sprites

# names of the OBJ layout, from build/art.h and src/game.h
_d = A._defs()
OBJ_BT_END = 56
O_MUG = OBJ_BT_END
O_GLASS = O_MUG + _d["MUG_TILE_COUNT"]
O_FILL = O_GLASS + _d["GLASS_TILE_COUNT"]
O_DRINK = O_FILL + _d["MUG_FILL_TILE_COUNT"]
O_COIN = O_DRINK + _d["MUG_DRINK_TILE_COUNT"]
O_DANCER = O_COIN + _d["COIN_TILE_COUNT"]
O_DANCER_END = O_DANCER + _d["DANCER_TILE_COUNT"]
O_PATRON = _d["PATRON_FIRST_TILE"] + _d["PATRON_SHIFT0_OFS"]       # shift-0 pose of variant v: + 6 v
O_POUR, O_CUE, O_DMG, O_MIRROR = 40, 44, 240, 246   # (Q61: the pour and the dust puff are sprite-only ids 40-51)
VARIANT = "ABC"
BT_NAMES = ["Sal: standing", "Sal: walking (step 1)", "Sal: walking (step 2)", "Sal: filling, sliding, catching", "Sal: fail (a patron reached the tap)"]

DESC = {
    "bt": "one of Sal's 5 frames (8 tiles each, OAM 0-3): idle, walk 1, walk 2, fill (also the slide and the catch), fail",
    "fill": "the glass filling at the tap (OAM 4)",
    "full": "a full mug sliding along a bar",
    "empty": "an empty mug coming back",
    "held": "a mug in a patron's hand while he drinks (all poses; the empty one at the end)",
    "glass": "a glass breaking at the end of a bar; its shards fall into the bar below",
    "coin": "the tip coin on the counter (and its blink)",
    "dancers": "the dancers' show (OBJ 5 holds the show palette meanwhile)",
    "lift": "a patron lifted from the BG to two 8x16 sprites (src/lift.c)",
    "edge": "a patron entering from the left edge (or a served one leaving): a sprite with no BG footprint (LIFT_EDGE)",
    "pour": "perfect pour (STORY): the sparkle and the overflow foam in the glass",
    "cue": "the PERFECT x2 cue beside a catch (STORY, OAM 26)",
    "dmg": "DMG copies of the mugs (bit planes swapped: OBP0 colours)",
    "mirror": "CLASSIC mirrored copies / the dust puff",
}


def label_of(o, cgb, enh, edge_x):
    """(sort key, label, description key) of an OAM entry, from its tile id (8x16: the even tile) and position."""
    t = o["tile"] & 0xFE
    if t < 40:
        return (0, t // 8), BT_NAMES[t // 8], "bt"
    if t < O_CUE:
        return (4, 0), "perfect pour: sparkle and overflow", "pour"
    if t < O_CUE + 2:
        return (4, 1), "PERFECT cue", "cue"
    if t < 52:
        return (5, 1), "dust puff (tile %d)" % t, "mirror"
    if t < 56:
        return (0, 9), "OBJ ids 52-55 (unused)", "bt"
    if t < O_MUG + 2:
        return (1, 0), "full mug", "full"
    if t < O_GLASS:
        return (1, 1), "empty mug", "empty"
    if t < O_FILL:
        return (1, 2), "breaking glass and shards", "glass"
    if t < O_DRINK:
        return (1, 3), "fill glass at the tap", "fill"
    if t < O_COIN:
        return (1, 4), "mug held while drinking", "held"
    if t < O_DANCER:
        return (3, 0), "tip coin", "coin"
    if t < O_DANCER_END:
        return (3, 1), "show dancers", "dancers"
    if t >= O_PATRON and t < O_PATRON + 18 + 6:
        v = (t - O_PATRON) // 6
        if v < 3:
            en = cgb and v in enh
            if o["x"] < edge_x or o["x"] > 136:
                return (2, 3 + v), "patron %s entering / leaving (left edge)" % VARIANT[v], "edge"
            return (2, v), "lifted patron %s%s" % (VARIANT[v], " (enhanced variant)" if en else ""), "lift"
    if O_DMG <= t < O_MIRROR:
        return (5, 0), "DMG mug copies", "dmg"
    return (5, 1), "mirrored copies / dust puff (tile %d)" % t, "mirror"


SAL_POSES = ["idle", "walk 1", "walk 2", "fill (also slide/catch)", "fail"]


def level_classifier(cgb, enh, edge_x, boss=None):
    """Entry -> (sort key, kind, pose or None, group key) from the game's OAM layout (src/game.h): Sal OAM 0-3 (2x2 of 8x16), the fill glass OAM 4,
    mugs single entries, lifted patrons pairs counting down from 25, the cue 26, the coin 27, the dancers 28-39 in fours (a boss fight's topper is OAM 28)."""
    def cls(o):
        key, label, dk = label_of(o, cgb, enh, edge_x)
        i, t = o["i"], o["tile"] & 0xFE
        if dk == "bt":
            if t < 40:
                return (0, 0), "Sal", SAL_POSES[t // 8], ("sal",)
            return (9, 0), "Sprite group", None, ("g",)
        if dk == "fill":
            return (1, 0), "Fill glass", None, ("fill", i)
        if dk == "full":
            return (1, 1), "Mug: full", None, ("m", i)
        if dk == "empty":
            return (1, 2), "Mug: empty", None, ("m", i)
        if dk == "held":
            return (1, 3), "Mug: drinking", None, ("m", i)
        if dk == "glass":
            return (1, 4), "Breaking glass", None, ("m", i)
        if dk == "coin":
            return (3, 0), "Tip coin", None, ("m", i)
        if dk == "dancers":
            if boss:
                return (6, 0), "Boss: " + boss, "topper" if i == 28 else None, ("b", i) if i == 28 else ("b",)
            return (3, 1), "Dancers", None, ("d", (i - 28) // 4) if i >= 28 else ("m", i)
        if dk in ("lift", "edge"):
            v = min(2, (t - O_PATRON) // 6)
            kind = "Patron %s (%s)" % (VARIANT[v], "lifted" if dk == "lift" else "entering / leaving")
            if dk == "lift" and "enhanced" in label:
                kind = "Patron %s (lifted, enhanced)" % VARIANT[v]
            return key, kind, None, ("p", (25 - i) // 2)
        names = {"pour": "Perfect-pour sparkle", "cue": "PERFECT cue", "dmg": "DMG mug copy", "mirror": "Mirrored copy / dust puff"}
        return key, names.get(dk, "Sprite group"), None, ("m", i)
    return cls


def classifier_for(sid, cgb, GAME):
    """The classifier of a screen id: the level layout for levels, shows, boss fights and entrances; the proximity grouping for every other screen."""
    boss = None
    if sid.startswith("boss_") or sid.startswith("bossin_"):
        import scenes
        boss = scenes.BOSS_NAMES[int(sid.split("_")[1]) - 1]
    if sid.startswith(("level_", "show_", "boss_", "bossin_")):
        return level_classifier(cgb, set(), GAME["ENTRY_X"], boss if sid.startswith("boss_") else None)
    return OB.generic


class Acc:
    """Accumulates the reduced samples of one level screen and model."""

    def __init__(self, cgb, enh, edge_x):
        self.cgb, self.enh, self.edge_x = cgb, enh, edge_x
        self.objs = OB.ObjAcc(cgb, level_classifier(cgb, enh, edge_x))
        self.ev = {}                     # label -> dict
        self.sprs = {}                   # (label, slot, h, bytes) -> entry
        self.objtile = defaultdict(set)  # (bank, slot) -> labels
        self.bgpal = defaultdict(set)    # bg palette -> {(bank, slot)}
        self.bgtiles = set()             # (bank, slot) used by BG/window in any sample
        self.objpal_used = defaultdict(set)   # slot -> labels
        self.bgpal_used = set()
        self.n = 0
        self.phase_frames = defaultdict(int)
        self.order = 0

    def add(self, s, phase):
        self.n += 1
        self.phase_frames[phase] += 1
        cgb = self.cgb
        grid, used, usedpal = C.screen_cells(s)
        for b, t, p in usedpal:
            self.bgpal[p].add((b, t))
            self.bgtiles.add((b, t))
        for row in grid:
            for e in row:
                if e:
                    self.bgpal_used.add(e[2])
                    self.bgpal[e[2]].add((e[1], e[0]))
        objs, _, h = C.oam_objects(s)
        self.objs.add(s, objs, h)
        boxes = {}
        for o in objs:
            if not o["visible"]:
                continue
            key, label, dk = label_of(o, cgb, self.enh, self.edge_x)
            slot = o["pal"] if cgb else o["dmgpal"]
            v = s.vram[o["bank"] if cgb else 0]
            rows = []
            for t in o["slots"]:
                rows += A.tile_pixels(v[t * 16:t * 16 + 16])
            if o["yflip"]:
                rows.reverse()
            if o["xflip"]:
                rows = [r[::-1] for r in rows]
            if cgb:
                cols = [A.rgb(c) for c in s.objpal[o["pal"]]]
                colw = list(s.objpal[o["pal"]])
            else:
                reg = s.regs["OBP1" if o["dmgpal"] else "OBP0"]
                cols = [C.DMG_SHADES[x] for x in A.dmg_palette(reg)]
                colw = reg
            ev = self.ev.get(label)
            if ev is None:
                ev = self.ev[label] = dict(label=label, key=key, dk=dk, n=0, oam=set(), slots=defaultdict(set), crops=[], last=None)
            for t in o["slots"]:
                self.objtile[(o["bank"] if cgb else 0, t)].add(label)
            self.objpal_used[slot].add(label)
            ev["oam"].add(o["i"])
            ev["slots"][slot].add(tuple(colw) if cgb else colw)
            bb = boxes.setdefault(label, [o["x"], o["y"], o["x"] + 8, o["y"] + h])
            bb[0], bb[1], bb[2], bb[3] = min(bb[0], o["x"]), min(bb[1], o["y"]), max(bb[2], o["x"] + 8), max(bb[3], o["y"] + h)
            if not any(p for r in rows for p in r):
                continue
            im = Image.new("RGBA", (8, h))
            im.putdata([(0, 0, 0, 0) if p == 0 else cols[p] + (255,) for r in rows for p in r])
            sk = (label, slot, h, im.tobytes())
            e = self.sprs.get(sk)
            if e is None:
                e = self.sprs[sk] = dict(img=im, label=label, slot=slot, n=0, order=self.order, bank=o["bank"] if cgb else 0, tile=o["tile"],
                                         xflip=o["xflip"], yflip=o["yflip"], h=h, seen=set())
                self.order += 1
            e["seen"].add(s.t)
        for label, bb in boxes.items():
            ev = self.ev[label]
            ev["n"] += 1
            if s.image is None:
                continue
            cx, cy = (bb[0] + bb[2]) // 2, (bb[1] + bb[3]) // 2
            x0 = max(0, min(C.SW - CELL_W, cx - CELL_W // 2))
            y0 = max(0, min(C.SH - CELL_H, cy - CELL_H // 2))
            crop = s.image.convert("RGB").crop((x0, y0, x0 + CELL_W, y0 + CELL_H))
            raw = crop.tobytes()
            if raw != ev["last"] and len(ev["crops"]) < 400:
                ev["last"] = raw
                ev["crops"].append((len(bb) and sum(1 for o in objs if o["visible"] and label_of(o, cgb, self.enh, self.edge_x)[1] == label), raw, crop))
        # the still image is large: drop it
        s.image = None


def pick_stills(crops):
    """STILLS crops spread over the event (first, middle, last of the distinct ones; the busiest first for a single)."""
    if not crops:
        return []
    if len(crops) <= STILLS:
        return [c[2] for c in crops]
    best = max(range(len(crops)), key=lambda i: (crops[i][0], -i))
    idx = sorted({0, best, len(crops) - 1}) if STILLS == 3 else [best]
    if len(idx) < STILLS:
        idx = sorted(set(idx) | {len(crops) // 2})
    return [crops[i][2] for i in idx[:STILLS]]


# ---- the scripted phases -------------------------------------------------------------------------------------------------------------
class Driver:
    def __init__(self, rom, model, acc, play, GAME, classic=False):
        self.classic = classic
        self.rom, self.cgb, self.acc, self.play, self.G = rom, model == "cgb", acc, play, GAME
        self.t = 0
        self.log = []

    def frames(self, n, phase, step=None, every=2, drive=True):
        rom = self.rom
        for i in range(n):
            if drive:
                self.play.step()
            else:
                self.rom.write("lives", 3)
                self.rom.write("quota", 250)
            if step:
                step(i)
            sampling = i % every == 0
            rom.run(1, sampling)
            if sampling:
                img = rom.pb.screen.image.convert("RGB").copy()
                self.acc.add(C.take(rom, self.cgb, self.t, img), phase)
            self.t += 1

    def ready(self):
        """On to a frame of real play (a life lost's banner and the level's intro are over; the play script keeps going)."""
        for _ in range(600):
            if self.rom.mem("game_state") == 1 and self.rom.mem("intro_timer") == 0:
                return
            self.frames(1, "play")
        self.log.append("not back in play")

    def freeze(self):
        r = self.rom
        if getattr(self.play, "held", None):                 # (the play script's held button would go on: let go of it)
            r.release(self.play.held)
            self.play.held = None
        r.write("intro_timer", 255)
        r.write("spawn_timer", 0xFF)
        r.write(r.addr("spawn_timer") + 1, 0xFF)

    def unfreeze(self):
        self.rom.write("intro_timer", 0)


def put(rom, name, i, v):
    rom.write(rom.addr(name) + i, v)


def patrons(rom):
    st = rom.read("patron_state", MAX_P)
    bar, x = rom.read("patron_bar", MAX_P), rom.read("patron_x", MAX_P)
    return [dict(i=i, state=st[i], bar=bar[i], x=x[i]) for i in range(MAX_P) if st[i]]


def new_patron(rom, bar, x, state=WALKING, variant=0, timer=0, aux=0):
    i = list(rom.read("patron_state", MAX_P)).index(0)
    for n, v in (("patron_state", state), ("patron_bar", bar), ("patron_x", x), ("patron_variant", variant), ("patron_timer", timer),
                 ("patron_aux", aux), ("patron_frac", 0), ("patron_draw", 255), ("patron_mug", 255), ("patron_drinks", 0), ("patron_hurry", 0),
                 ("patron_dist", 0)):
        put(rom, n, i, v)
    rom.write("patrons_live", rom.mem("patrons_live") + 1)
    return i


def new_mug(rom, bar, x, state=FULL, timer=0, patron=255):
    i = list(rom.read("mug_state", MAX_M)).index(0)
    for n, v in (("mug_state", state), ("mug_bar", bar), ("mug_x", x), ("mug_timer", timer), ("mug_patron", patron)):
        put(rom, n, i, v)
    rom.write("mugs_live", rom.mem("mugs_live") + 1)
    return i


def hook(rom, p, op):
    rom.write("lift_hook_p", p)
    rom.write("lift_hook_res", 0)
    rom.write("lift_hook_op", op)


def phase_lifts(D, notes):
    rom = D.rom
    HL, HD = 1, 3
    D.freeze()
    for v in range(3):
        pats = [p for p in patrons(rom) if p["state"] in (WALKING, DRINKING) and p["x"] > D.G["ENTRY_X"] + 8]
        take = []
        for bar in range(4):
            c = [p for p in pats if p["bar"] == bar and p["i"] not in [t["i"] for t in take]]
            if c and len(take) < 3:
                take.append(c[0])
        k = 0
        while len(take) < 3:
            bar = k % 4
            k += 1
            i = new_patron(rom, bar, 52 + 28 * (k // 4), WALKING, v)
            take.append(dict(i=i, bar=bar))
        for n, p in enumerate(take):
            x = 40 + 40 * (n % 2) + 24 * v
            draw = rom.read("patron_draw", MAX_P)[p["i"]]
            put(rom, "patron_x", p["i"], x)
            put(rom, "patron_variant", p["i"], v)
            put(rom, "patron_state", p["i"], WALKING)
            if draw >> 3 == x >> 3:                          # (as the tests' lineup does: the same columns, maybe another variant: a redraw)
                put(rom, "patron_draw", p["i"], 255)
            put(rom, "patron_dist", p["i"], 0)
        for _ in range(40):                                  # (until the BG figures are drawn: a lift needs patron_draw)
            D.frames(1, "lifts", drive=False, every=1)
            if all(rom.read("patron_draw", MAX_P)[p["i"]] != 255 for p in take):
                break
        D.frames(4, "lifts", drive=False)
        done = 0
        for p in take:
            hook(rom, p["i"], HL)
            for _ in range(5):
                D.frames(1, "lifts", drive=False, every=1)
                if rom.mem("lift_hook_op") == 0:
                    break
            done += rom.mem("lift_hook_res") == 1
        D.frames(40, "lifts", drive=False)
        for p in take:
            hook(rom, p["i"], HD)
            D.frames(3, "lifts", drive=False, every=1)
        D.frames(10, "lifts", drive=False)
        if not done:
            notes.append("lifts: variant %s could not be lifted (the hook refused every patron)" % VARIANT[v])
    D.unfreeze()


def phase_edge(D, notes):
    """A patron entering from the left edge, once per variant (his variant poked once he is on screen: the sprite follows it), and a served one leaving."""
    rom = D.rom
    D.unfreeze()
    for v in (1, 2, 0):
        known = {p["i"] for p in patrons(rom)}
        rom.write("spawn_timer", 0)
        rom.write(rom.addr("spawn_timer") + 1, 0)
        got = None
        for k in range(500):
            if k % 10 == 0:
                rom.write("spawn_timer", 0)
                rom.write(rom.addr("spawn_timer") + 1, 0)
            D.frames(1, "edge", drive=False, every=1)
            new = [p for p in patrons(rom) if p["x"] < D.G["ENTRY_X"] - 4 and (p["i"] not in known or k > 100)]
            if new:
                got = new[0]
                break
        if got is None:
            notes.append("edge: no patron entered for variant %s" % VARIANT[v])
            continue
        put(rom, "patron_variant", got["i"], v)
        D.frames(70, "edge", drive=False)
    # a served patron slides out past the left edge: a patron at ENTRY_X catches a full mug
    D.freeze()
    for v in range(3):
        new_patron(rom, v % 4, D.G["ENTRY_X"] + 2, WALKING, v)
        D.frames(2, "edge", drive=False)
        new_mug(rom, v % 4, D.G["ENTRY_X"] + 6, FULL)
        D.frames(60, "edge", drive=False)
    D.unfreeze()


def phase_mugs(D, notes):
    rom = D.rom
    D.freeze()
    for b in range(4):
        new_mug(rom, b, D.G["SPOUT_X"] - 8 - 24 * b, FULL)
        new_mug(rom, b, 40 + 20 * b, EMPTY)
    D.frames(60, "mugs", drive=False)
    for b in range(4):
        new_mug(rom, b, D.G["GLASS_X"], BREAKING)
        new_mug(rom, b, D.G["GLASS_X_RIGHT"], BREAKING)
        D.frames(8, "mugs", drive=False)
    D.frames(60, "mugs", drive=False)
    # a mug held while drinking: a drinker with a mug in hand (the way a catch sets it up)
    for b in (0, 1):
        i = new_patron(rom, b, 72 + 24 * b, DRINKING, b, 0, 0)
        m = new_mug(rom, b, 0, HELD, 0, i)
        put(rom, "patron_mug", i, m)
    D.frames(200, "mugs", drive=False)
    D.unfreeze()


def phase_tip(D, notes):
    rom = D.rom
    put16 = lambda name, v: (rom.write(name, v & 255), rom.write(rom.addr(name) + 1, v >> 8))
    D.freeze()
    for blink in (400, 60):
        put16("show_timer", 0)
        put16("tip_timer", blink)
        rom.write("tip_bar", 1)
        rom.write("tip_x", 60)
        D.frames(blink if blink < 100 else 60, "tip", drive=False)
    put16("show_timer", 0)
    D.unfreeze()


def phase_show(D, notes):
    rom = D.rom
    put16 = lambda name, v: (rom.write(name, v & 255), rom.write(rom.addr(name) + 1, v >> 8))
    put16("tip_timer", 0)
    put16("show_timer", 704)
    D.frames(250, "show")
    put16("show_timer", 0)


def phase_fail(D, notes):
    import test_flow as TF
    rom = D.rom
    rom.write("lives", 3)
    TF.lose_a_life(rom)
    D.frames(60, "fail", drive=False)


def phase_story(model, group, cgb_enh, notes, acc_factory):
    """STORY: the perfect pour. A fresh rom in the chapter of this venue; hold A at the tap into the sparkle window and release."""
    import test_pour as TP
    acc = acc_factory()
    rom = TP.story(model, group)
    D = Driver(rom, model, acc, NoPlay(), TP.GAME)
    try:
        W0 = TP.WIN0
        rom.hold("a")
        for _ in range(60):
            D.frames(1, "story", every=1, drive=False)
            if rom.mem("pour_t") >= W0 - 1:
                break
        D.frames(3, "story", every=1, drive=False)
        rom.release("a")
        D.frames(150, "story", every=2, drive=False)
        rom.hold("a")
        D.frames(TP.FILL_FRAMES + 12, "story", every=2, drive=False)     # the overflow foam
        rom.release("a")
        D.frames(40, "story", every=2, drive=False)
    finally:
        rom.stop()
    return acc


def phase_pocket(model, group, notes, acc_factory):
    """ARCADE and STORY (the level harness has no pocket): a tip picked up starts a show, a second one picked up during it is pocketed: the HUD icon."""
    import test_pocket as TPK
    from test_story import to_chapter
    acc = acc_factory()
    rom = to_chapter(model, group)                # (STORY has the pocket like ARCADE; its venue is the group's)
    try:
        D = Driver(rom, model, acc, NoPlay(), TPK.GAME)
        D.frames(4, "pocket", drive=False)
        TPK.quiet(rom)
        TPK.start_a_show(rom)
        D.frames(30, "pocket", drive=False)
        TPK.pick_up_a_tip(rom)
        D.frames(60, "pocket", drive=False)
        if rom.mem("tip_pocket") != TPK.ICON:
            notes.append("pocket: the pocketed-tip HUD icon did not appear")
    finally:
        rom.stop()
    return acc


class NoPlay:
    def step(self, *a):
        pass


# ---- the entry point -----------------------------------------------------------------------------------------------------------------
PHASES = [phase_lifts, phase_edge, phase_mugs, phase_tip, phase_show, phase_fail]


def level_group(sid):
    """(venue group index, is classic) of a level screen id, or None."""
    if sid.startswith("level_") and sid[len("level_"):] in freepal.GROUPS:
        return freepal.GROUPS.index(sid[len("level_"):]), False
    if sid in freepal.CLASSIC_GROUP:
        return freepal.GROUPS.index(freepal.CLASSIC_GROUP[sid]), True
    return None


def enhanced_variants(g):
    try:
        x_ids, attrs = freepal._enh()
        gi = freepal.GROUPS.index(g)
        if x_ids[gi] == 255:
            return set()
        return {i % 4 for i, a in enumerate(attrs[g]) if a & 7 == 4}
    except Exception:
        return set()


def capture(rom, model, sid, base_samples, play, GAME):
    """Returns (Acc, notes). `base_samples`: the screen's own sampled window (capture.Sample list); `play`: its Play script object."""
    gi, classic = level_group(sid)
    cgb = model == "cgb"
    enh = enhanced_variants(freepal.GROUPS[gi])
    acc = Acc(cgb, enh, GAME["ENTRY_X"])
    notes = []
    for s in base_samples:
        acc.add(s, "screenshot window")
    D = Driver(rom, model, acc, play, GAME, classic)
    D.t = 1000
    D.frames(240, "play")
    for ph in PHASES:
        try:
            if ph is not phase_fail:
                D.ready()
            if os.environ.get("ATLAS_TRACE"):
                print("   phase", ph.__name__, "state", rom.mem("game_state"), "level", rom.mem("level"), "t", D.t)
            ph(D, notes)
        except Exception:
            notes.append("%s failed: %s" % (ph.__name__, traceback.format_exc().strip().splitlines()[-1]))
    if not classic:
        try:
            merge(acc, phase_pocket(model, gi, notes, lambda: Acc(cgb, enh, GAME["ENTRY_X"])))
        except Exception:
            notes.append("pocket failed: %s" % " | ".join(traceback.format_exc().strip().splitlines()[-3:]))
        try:
            import conftest as CF
            story_acc = phase_story(model, gi, enh, notes, lambda: Acc(cgb, enh, GAME["ENTRY_X"]))
            merge(acc, story_acc)
        except Exception:
            notes.append("story (perfect pour) failed: %s" % traceback.format_exc().strip().splitlines()[-1])
    return acc, notes


def merge(a, b):
    """Fold a second accumulator (the story run) into the first."""
    for k, e in b.ev.items():
        if k in a.ev:
            x = a.ev[k]
            x["n"] += e["n"]
            x["oam"] |= e["oam"]
            for s, v in e["slots"].items():
                x["slots"][s] |= v
            x["crops"] += e["crops"]
        else:
            a.ev[k] = e
    for k, e in b.sprs.items():
        if k not in a.sprs:
            e["order"] = a.order
            a.order += 1
            a.sprs[k] = e
    for k, v in b.objtile.items():
        a.objtile[k] |= v
    for k, v in b.bgpal.items():
        a.bgpal[k] |= v
    a.bgtiles |= b.bgtiles
    for k, v in b.objpal_used.items():
        a.objpal_used[k] |= v
    a.bgpal_used |= b.bgpal_used
    for k, v in b.phase_frames.items():
        a.phase_frames[k] += v
    a.n += b.n
    a.objs.merge(b.objs)


def record(acc, notes, cgb):
    """The JSON-able part of the atlas record (rec["ev"]) and the sidecar the packer needs (images)."""
    evs = sorted(acc.ev.values(), key=lambda e: (e["key"], e["label"]))
    out, imgs = [], []
    for i, e in enumerate(evs):
        sp = sorted((s for s in acc.sprs.values() if s["label"] == e["label"]), key=lambda s: (-len(s["seen"]), s["order"]))
        items = [[s["tile"], s["bank"], s["xflip"], s["yflip"], s["h"], len(s["seen"]), s["slot"]] for s in sp[:EV_CAP]]
        tiles = sorted({(b, t) for (b, t), labs in acc.objtile.items() if e["label"] in labs})
        slots = []
        for sl in sorted(e["slots"]):
            vals = sorted(e["slots"][sl])
            slots.append(dict(slot=sl, values=[list(v) if cgb else v for v in vals]))
        out.append(dict(id=i, label=e["label"], desc=DESC[e["dk"]], n=e["n"], oam=sorted(e["oam"]), slots=slots, sprites=items, n_sprites=len(sp),
                        tiles=[list(t) for t in tiles]))
        imgs.append(dict(stills=pick_stills(e["crops"]), sprites=[s["img"] for s in sp[:EV_CAP]]))
    by_slot = {}
    for sl, labs in acc.objpal_used.items():
        by_slot[sl] = sorted(labs)
    objtiles = {}
    for (b, t), labs in acc.objtile.items():
        objtiles["%d:%d" % (b, t)] = sorted(labs)
    nb = 2 if cgb else 1
    use = ["".join("1" if ((b, t) in acc.objtile or (b, t) in acc.bgtiles) else "0" for t in range(384)) for b in range(nb)]
    rec_objs, obj_imgs = acc.objs.record()
    rec = dict(events=out, objs=rec_objs, use=use, by_slot=by_slot, notes=notes, frames=acc.n, phases=dict(acc.phase_frames),
               bg_by_pal={str(p): sorted([list(x) for x in v]) for p, v in acc.bgpal.items()},
               obj_tiles=objtiles, bg_tiles=sorted([list(x) for x in acc.bgtiles]),
               cell=[CELL_W, CELL_H], stills=STILLS, cap=EV_CAP)
    return rec, imgs, obj_imgs
