"""What the game itself says about its patron palettes and looks, read from the sources the ROM is built from:
build/palettes.c (generated from assets/palettes.json), src/game.h (the slot numbers), src/mirror.c (the Saloon's look / palette-instance table),
assets/art/patrons/*_back.txt (the back views and which of them are stand-ins). build.py checks every "now" claim of the page against this
and the atlas capture, and fails the build on a mismatch.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
ARTDIR = os.path.join(ROOT, "assets/art/patrons")


def _read(rel):
    return open(os.path.join(ROOT, rel)).read()


def truth():
    src = _read("build/palettes.c")
    rows = re.findall(r"\{0, (\d+), (\d+), (\d+)\},\s*// (\w+)", src)
    names = [n for *_, n in rows]
    P = {n: (int(a), int(b), int(c)) for a, b, c, n in rows}
    ids = re.search(r"patron_pal_ids\[.*?= \{(.*?)\};", src, re.S).group(1)
    groups = {g[3]: [names[int(i)] for i in g[:3]] for g in re.findall(r"\{(\d+), (\d+), (\d+)\},\s*// (\w+)", ids)}
    inst = {}                                    # venue key -> palette instances 0.. -> (colour 1, 2, 3) as 15-bit words
    for g, ns in groups.items():
        inst[g] = [P[n] for n in ns]
    inst["cowboys"] += [P["cowboys_d"], P["cowboys_e"]]       # patron_pal_get: instances 3 and 4 are the Saloon's own
    h = _read("src/game.h")
    const = lambda n: int(re.search(r"#define %s\s+(\d+)" % n, h).group(1))
    obj_of = [const("OBJPAL_PATRON_" + c) for c in "ABCDE"]
    bg_of = [const("BGPAL_PATRON"), const("BGPAL_PATRON") + 1, const("BGPAL_PATRON") + 2, const("BGPAL_BAR_B"), const("BGPAL_STAGE")]
    m = _read("src/mirror.c")
    blk = re.search(r"sal_combo\[\d+\] = \{(.*?)\};", m, re.S).group(1)
    looks, names_ = {}, {}
    for line in blk.splitlines():
        for l, p in re.findall(r"V\((\d), (\d)\)", line):
            looks.setdefault(int(l), []).append(int(p))
        c = re.search(r"//\s*([A-Z]+)\b", line)
        if c and re.search(r"V\(", line):
            names_[int(re.search(r"V\((\d),", line).group(1))] = c.group(1)
    saloon = [(names_[i], looks[i]) for i in sorted(looks)]        # [(NAME, [instances])] by look 0-7
    return dict(inst=inst, obj_of=obj_of, bg_of=bg_of, saloon=saloon)


def back_notes(path):
    """[(label comment, is a stand-in)] of a *_back.txt, one per frame, from the `; ...` line just above each frame."""
    out, last, seen = [], "", False
    for l in open(path).read().splitlines():
        if l.startswith(";"):
            last = l[1:].strip()
        elif l.strip():
            if not seen:
                out.append((last, "stand-in" in last.lower()))
                seen = True
        else:
            seen = False
            last = ""
    return out


def backs(key):
    """[(label, rows, stand-in)] of the game's current back views for a venue's looks (the Saloon's 8: cowboys_back.txt then saloon_x_back.txt)."""
    res = []
    for f in (["cowboys_back.txt", "saloon_x_back.txt"] if key == "cowboys" else ["%s_back.txt" % key]):
        p = os.path.join(ARTDIR, f)
        frames, cur = [], []
        for l in open(p).read().splitlines():
            if l.startswith(";"):
                continue
            if not l.strip():
                if cur:
                    frames.append(cur)
                    cur = []
            else:
                cur.append(l)
        if cur:
            frames.append(cur)
        notes = back_notes(p)
        assert len(frames) == len(notes), (p, len(frames), len(notes))
        res += [(n[0], rows, n[1]) for n, rows in zip(notes, frames)]
    return res


def ordered_instances(look, ps):
    """A look's palette instances, its own first (the art was drawn for it: looks 0-2 = A, B, C = instance = look; the Color-only looks 3-7 have
    no stated one, so the lowest OBJ slot), then by OBJ slot."""
    obj_of = truth()["obj_of"]
    ps = sorted(ps, key=lambda p: obj_of[p])
    if look < 3 and look in ps:
        ps.remove(look)
        ps.insert(0, look)
    return ps


def spawn_combos():
    """{venue key: {look: set of palette instances}} the game can spawn: the Saloon from sal_combo (Color), every other venue one palette per look
    (src/mirror.c spawn_variant: r % 3, instance = look)."""
    T = truth()
    out = {}
    for k in T["inst"]:
        if k == "cowboys":
            out[k] = {i: set(ps) for i, (_, ps) in enumerate(T["saloon"])}
        else:
            out[k] = {i: {i} for i in range(3)}
    return out
