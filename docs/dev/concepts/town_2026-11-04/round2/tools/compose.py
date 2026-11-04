#!/usr/bin/env python3
"""Build the four square pictures from the town master (out/town/tools/master.py) plus the approved pictures' own props.

Transcription only: the town pixels are the master's (hand-drawn); every prop pixel (fountain, Golden Spigot, Sal, Dregs,
the INTRO crowd, the moon, the stars, the sun, the coffee stand, the suds) is copied unchanged from the approved picture
it belongs to, inside a rectangle given below; the FINALE crowd's ink pixels are copied from the 2026-11-04 mockup
(hand-drawn silhouettes). The per-picture hand clean-up (EDITS) is listed with a reason each. Nothing is generated.

    compose.py OUTDIR      writes OUTDIR/<picture>.txt (portrait-v2) for intro_before, intro_a, finale_a, credits_b
"""
import sys
from pathlib import Path

T = Path(__file__).resolve().parent
sys.path.insert(0, str(T))
import master as M          # noqa: E402
import keys as K            # noqa: E402

REPO = T.parents[2]
PICS = REPO / "assets/story/pictures"
MOCK = REPO / "docs/dev/concepts/story_scenes_2026-11-04/finale_a_mockup.txt"
W, H = 160, 104


def old(path):
    rows, on = [], False
    for ln in open(path).read().split("\n"):
        if ln.startswith("@pixels"):
            on = True
            continue
        if on and ln.strip():
            rows.append(ln)
    return rows[:H]


REF = old(PICS / "intro_before.txt")        # the approved cobble: x 0-7 of rows 88-103 is plain plaza in every picture


def fountain(x, y):
    return (9 <= y <= 47 and 92 <= x <= 116) or (48 <= y <= 52 and 72 <= x <= 125) or (53 <= y <= 87 and 72 <= x <= 135)


TOWN_KEYS = set("BOe")      # the old town's own keys: never copied (the master replaces that town)
PLAZA = {"m": "p", "g": "h"}


def copy_box(g, src, x0, y0, x1, y1, keep_town=False, skip="K k"):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            c = src[y][x]
            if c == "." or c in skip.split() or (c in TOWN_KEYS and not keep_town):
                continue
            g[y][x] = c


def copy_mask(g, src, mask):
    for y in range(H):
        for x in range(W):
            c = src[y][x]
            if mask(x, y) and c != "." and c not in "Kk" and c not in TOWN_KEYS:
                g[y][x] = c


def copy_sky(g, src, master_g, chars="NnKk", x1=W - 1):
    """moon and stars (the sun: x1 47, left of the old strings' bulbs): only where the master shows sky"""
    for y in range(88):
        for x in range(x1 + 1):
            if src[y][x] in chars and master_g[y][x] == ".":
                g[y][x] = src[y][x]


def copy_plaza(g, src, x0=0, x1=W - 1):
    """everything on the plaza that is not the plain approved cobble (the crowd, feet, suds), cobble keys mapped"""
    for y in range(89, H):
        for x in range(x0, x1 + 1):
            c = src[y][x]
            if c != REF[y][x % 8] and c != ".":
                g[y][x] = PLAZA.get(c, c)


# Dregs mopping (credits_b), his figure row by row (x from, x to): his jacket is the old picture's 'B' (kept: it was
# the town colour in the approved picture and is still the wall colour at dawn)
CREDITS_DREGS = {66: (37, 41), 67: (35, 43), 68: (34, 44), 69: (33, 46), 70: (33, 46), 71: (33, 43), 72: (33, 44),
                 73: (33, 45), 74: (33, 46), 75: (33, 45), 76: (34, 43), 77: (35, 42), 78: (36, 41), 79: (33, 44),
                 80: (32, 45), 81: (32, 45), 82: (32, 45), 83: (32, 48), 84: (32, 50), 85: (32, 51), 86: (32, 58),
                 87: (31, 60), 88: (34, 42)}


def intro_before(g, m):
    src = old(PICS / "intro_before.txt")
    copy_mask(g, src, fountain)
    copy_box(g, src, 136, 66, 159, 87)                  # Sal walking in
    copy_box(g, src, 48, 80, 71, 87)                    # the crowd's heads above the plaza edge
    for (x, y) in [(x, y) for y in range(80, 88) for x in range(48, 72)]:
        g[y][x] = PLAZA.get(g[y][x], g[y][x]) if src[y][x] in "mg" else g[y][x]
    copy_sky(g, src, m)
    copy_plaza(g, src)
    return src


def intro_a(g, m):
    src = old(PICS / "intro_a.txt")
    copy_mask(g, src, fountain)
    copy_box(g, src, 56, 64, 73, 87)                    # Dregs
    copy_box(g, src, 134, 66, 159, 87)                  # Sal's shrug
    copy_sky(g, src, m)
    copy_plaza(g, src)
    return src


def finale_a(g, m):
    src = old(PICS / "finale_a.txt")
    copy_mask(g, src, lambda x, y: fountain(x, y) or (53 <= y <= 87 and x >= 72))   # fountain, Sal's glass, Sal, Dregs
    mock = old(MOCK)
    for y in range(89, H):                              # the ten owners: the mockup's hand-drawn silhouettes
        for x in range(W):
            if mock[y][x] == "#":
                g[y][x] = "#"
    return src


def credits_b(g, m):
    src = old(PICS / "credits_b.txt")
    copy_mask(g, src, lambda x, y: fountain(x, y) and not (x < 80 and y < 64))   # (x 72-79 above the basin: the old string's end)
    for y, (x0, x1) in CREDITS_DREGS.items():
        for x in range(x0, x1 + 1):
            c = src[y][x]
            if c not in ".Kk" and c != "e":
                g[y][x] = PLAZA.get(c, c) if y == 88 else c
    copy_box(g, src, 136, 47, 159, 87, keep_town=False)  # the coffee stand and its cup sign
    copy_sky(g, src, m, chars="y", x1=47)                # the sun, behind the town
    copy_plaza(g, src)
    return src


PICTURES = {
    "intro_before": (intro_before, K.NIGHT, "INTRO pages 1-4: Fizzwater square at night, from the town master (2026-11-04 proposal): the festival's gabled houses, the clock tower, the tavern's awning, the venue's bunting; the Golden Spigot (F1) whole, the crowd waiting, the Spigoteer walking in."),
    "intro_a": (intro_a, K.NIGHT, "INTRO page 5 on: the same square after the explosion (the town master at night): the spigot gone (a broken stub), the fountain stopped, Dregs and the Spigoteer's shrug, the crowd. The ten pieces are OBJ sprites (intro_pieces.txt) leaving trails of dots (BG tiles)."),
    "finale_a": (finale_a, K.DAY, "FINALE: the same square by day (the town master in the Pour-Off venue's day colours): the Golden Spigot (F1) on the fountain, the Spigoteer with his glass in the jet, Dregs sheepish, the ten owners as a crowd of silhouettes on the plaza."),
    "credits_b": (credits_b, K.DAWN, "CREDITS: the same square at dawn (the town master backlit): the Golden Spigot (F1) drips, Dregs in an apron mops, the Sasquatch's coffee stand."),
}

HUD_KEYS = {"Z": (3, "#181040", "navy (HUD palette)"), "G": (2, "#e8a020", "gold (HUD palette)"),
            "C": (0, "#f8e8b0", "cream (HUD palette)"), "T": (1, "#c0a050", "tan (HUD palette)")}
DREGS = {"D": None}

# hand clean-up per picture: (x0, y0, x1, y1, from keys, to key, reason): inside the rectangle each pixel of a 'from' key
# becomes the 'to' key; see NOTES.md "Clean-up log"
FINALE_FIX = [(120, 64, 127, 71, "b", "W", "the jet's last water above Sal's hand foams white (water and skin are both DMG 1 by day)"),
              (128, 78, 135, 79, ".", "m", "the gaps between Sal's arm and body show the basin, not the alley's sky (skin and sky are both DMG 1)"),
              (141, 53, 159, 90, "m", "B", "Dregs's jacket keeps its lilac (DMG 2): by day the stone key is the fountain's pale stone")]
CREDITS_FIX = [(31, 66, 60, 87, "m", "e", "Dregs's and the mop's stone-grey pixels take the gold trim colour on Color (DMG unchanged: both 1): he stands in front of the gold-lit awning and shop window"),
               (136, 48, 143, 55, "B", "#", "the cup sign's backboard: ink around the sign on the gable wall (its pale gold and the wall are both DMG 2)"),
               (152, 48, 159, 55, "B", "#", "the cup sign's backboard, right side")]
EDITS = {"intro_before": [], "intro_a": [], "finale_a": FINALE_FIX, "credits_b": CREDITS_FIX}


def build(name):
    fn, keyt, desc = PICTURES[name]
    m = M.master()
    g = [r[:] for r in m]
    fn(g, m)
    for (x0, y0, x1, y1, frm, to, _why) in EDITS[name]:
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if g[y][x] in frm:
                    g[y][x] = to
    keyt = dict(keyt)
    keyt.update(HUD_KEYS)
    if "D" not in keyt:
        keyt["D"] = (0, keyt["W"][1], "Dregs's skin")
    used = sorted({c for r in g for c in r})
    missing = [c for c in used if c not in keyt]
    if missing:
        raise SystemExit(f"{name}: no key for {missing}")
    return g, {c: keyt[c] for c in used}, desc


def write(name, outdir):
    g, key, desc = build(name)
    lines = [f"; {desc}", "; Full-screen story picture, portrait-v2 at 160x104 (rows 0-12); see docs/story.md and tools/gen_story.py SCENE_PICS.",
             "@size 160 104", "@maxpal " + ("4" if name.startswith("intro") else "5"), "@key"]
    lines += [f"{c} {v[0]} {v[1]} {v[2]}" for c, v in key.items()]
    lines += ["@pixels"] + ["".join(r) for r in g]
    p = Path(outdir) / f"{name}.txt"
    p.write_text("\n".join(lines) + "\n")
    return p


if __name__ == "__main__":
    out = sys.argv[1]
    Path(out).mkdir(parents=True, exist_ok=True)
    for n in PICTURES:
        print(write(n, out))
