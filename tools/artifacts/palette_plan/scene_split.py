#!/usr/bin/env python3
"""Split an edited scene sheet (the Palette Plan's download: the dancers, the keg, the stage or the floor of one venue)
back into the source format of assets/approved/venues/<prefix>_*.txt.

    python3 tools/artifacts/palette_plan/scene_split.py <venue> <piece> <edited.png>
    python3 tools/artifacts/palette_plan/scene_split.py --selftest

<venue> is the page's venue key (cowboys sports lumberjacks chefs divers robots punks ninjas zoo aliens, the file prefix is
build.py's SCENE), <piece> is dancers, kegs, stage or floor (the download is <venue>_<piece>.png). It prints the changed
rows and attribute rows with the file and line they belong to, and writes nothing: the supervisor pastes them in.

The sheet layout is build.py's piece_layout: the blocks in file order (dancers: pose 1.. ; stage: the 160x32 stage, then
each @frame of <prefix>_anim.txt; keg: bar pixels 136-159 of the 3 bar rows; floor: the 8x8 tile), rows of at most
`width` px, GAP (8) px apart. Block sizes must not change.

Palette index (the PNG is indexed, mode P):
  - a piece that uses several palettes (the stage: BG 5 and BG 6; the keg when it and the wall are on different BG slots)
    has index = slot * 4 + colour, slot 0-7 the BG slot AS THE PLAN SHOWS IT when the PNG was made, colour 0-3 the colour
    within it ('.', '-', '+', '#'). Every pixel keeps its palette when edited; painting a whole 8x8 tile with the other
    palette's indexes changes the tile's attribute, and the attribute row is printed (0/1 as in <prefix>_attr.txt and
    <prefix>_bar_attr.txt: stage 0 = BG 5, 1 = BG 6; bar 0 = the wall's BG slot, 1 = the keg's). A tile whose pixels mix
    palettes is reported and its attribute is left alone. Slots are the plan's, so split a PNG against the same plan.
  - a piece with one palette (the dancers' OBJ palette, the floor, a keg on its wall's slot) has index = colour 0-3.
The dancers' PNG has index 0 transparent: 0 = '.', 1-3 = '-', '+', '#' (the palette's colours 1-3).
The stage's animation frames take their palette from the stage's attribute at their slots: they have no attribute of their own.
If the stage's pixels at an animated slot change, <prefix>_anim.txt's @base frame must change with them (gen_art checks it).
"""
import os
import sys

here = os.path.dirname(os.path.abspath(__file__))


def load_build():
    argv = sys.argv
    sys.argv = sys.argv[:1]                       # build.py reads its own argv (the atlas dir)
    src = open(os.path.join(here, "build.py")).read()
    ns = {"__file__": os.path.join(here, "build.py")}
    exec(src.rsplit("\nfor i, v in enumerate(venues):", 1)[0], ns)   # all but the page loop
    sys.argv = argv
    return ns


def decode(p, im):
    """-> per block (rows, slot per pixel) as drawn in the image, and notes."""
    out, notes = [], []
    for bi, (b, (bx, by)) in enumerate(zip(p["blocks"], p["pos"])):
        rows, slots = [], []
        for y in range(len(b["rows"])):
            r, sr = "", []
            for x in range(len(b["rows"][0])):
                i = im.getpixel((bx + x, by + y))
                if p["multi"]:
                    sl, c = i // 4, i % 4
                else:
                    sl, c = b["grid"][y // 8][x // 8], i
                    if i > 3:
                        notes.append("block %d (%d,%d): index %d is not a colour 0-3" % (bi + 1, x, y, i)); c = 0
                r += ".-+#"[c]; sr.append(sl)
            rows.append(r); slots.append(sr)
        out.append((rows, slots))
    return out, notes


def attr_changes(p, b, slots, orig_attr, label):
    """{(tx, ty): new attribute value} for a block's tiles, plus notes. orig_attr(tx, ty) is the source value."""
    new, notes = {}, []
    for ty in range(len(b["rows"]) // 8):
        for tx in range(len(b["rows"][0]) // 8):
            s = {slots[ty * 8 + y][tx * 8 + x] for y in range(8) for x in range(8)}
            o = b["grid"][ty][tx]
            if s == {o}:
                continue
            if len(s) > 1:
                notes.append("%s tile (%d,%d): pixels use palettes %s together; attribute left alone" % (label, tx, ty, sorted(s)))
                continue
            sl = next(iter(s))
            val = p["attr_of_slot"].get(sl)
            if val is None:
                notes.append("%s tile (%d,%d): palette slot %d has no attribute value here; attribute left alone" % (label, tx, ty, sl))
            elif val != orig_attr(tx, ty):
                new[(tx, ty)] = val
    return new, notes


def split(ns, v, name, im):
    """-> list of report lines (empty: no change)."""
    m = ns["model"](v)
    field = ns["field_model"](v, m)
    p = ns["scene_pieces"](v, m, field)[name]
    if im.mode != "P":
        return ["expected the indexed PNG the page gives (mode P); got %s" % im.mode]
    if im.size != tuple(p["size"]):
        return ["size %s: the sheet is %s (block sizes must not change)" % (im.size, tuple(p["size"]))]
    dec, notes = decode(p, im)
    rep = []
    fn = os.path.basename(p["file"])
    if name in ("dancers", "floor"):
        for b, (rows, _) in zip(p["blocks"], dec):
            if rows != b["rows"]:
                rep.append("%s %s (from line %d)" % (fn, b["label"], b["line"]))
                rep += rows + [""]
    elif name == "stage":
        lines = ns["src_lines"](p["file"])
        rows, slots = dec[0]
        for y, (n, old) in enumerate(lines):
            if rows[y] != old:
                rep += ["%s line %d (pixel row %d)" % (fn, n, y), rows[y], ""]
        sattr = [[int(c) for c in r] for _, r in ns["src_lines"](p["attr"])]
        ch, nt = attr_changes(p, p["blocks"][0], slots, lambda tx, ty: sattr[ty][tx], "stage")
        notes += nt
        if ch:
            new = ["".join(str(ch.get((tx, ty), sattr[ty][tx])) for tx in range(20)) for ty in range(4)]
            rep += ["%s (new rows)" % os.path.basename(p["attr"])] + new + [""]
        for b, (frows, fslots) in zip(p["blocks"][1:], dec[1:]):
            if frows != b["rows"]:
                rep.append("%s @%s (line %d): 8 rows, one 8-px column per tile" % (os.path.basename(p["anim"]), b["name"], b["line"]))
                rep += [" ".join(r[i:i + 8] for i in range(0, len(r), 8)) for r in frows] + [""]
            if any(s != b["grid"][0][i // 8] for r in fslots for i, s in enumerate(r)):
                notes.append("%s: palette changed; a frame takes the stage attribute's palette at its slot" % b["label"])
    else:                                          # kegs
        bar = ns["src_lines"](p["file"])
        rows, slots = dec[0]
        for y, (n, old) in enumerate(bar):
            if rows[y] != old[136:160]:
                rep += ["%s line %d (pixel row %d)" % (fn, n, y), old[:136] + rows[y], ""]
        battr = [[int(c) for c in r] for _, r in ns["src_lines"](p["attr"])]
        ch, nt = attr_changes(p, p["blocks"][0], slots, lambda tx, ty: battr[ty][17 + tx], "keg")
        notes += nt
        if ch:
            new = ["".join(str(ch[(c - 17, y)]) if (c - 17, y) in ch else str(battr[y][c]) for c in range(20)) for y in range(3)]
            rep += ["%s (new rows)" % os.path.basename(p["attr"])] + new + [""]
    return rep + ["note: " + n for n in notes]


def selftest(ns):
    """Every piece of every venue: the unedited download reports nothing; one changed pixel is reported; where a piece has two
    palettes, the first tile moved wholesale to the other palette is reported as an attribute change only."""
    bad = total = 0
    for v in ns["venues"]:
        m = ns["model"](v)
        field = ns["field_model"](v, m)
        pieces = ns["scene_pieces"](v, m, field)
        for name, _ in ns["SCENE_ORDER"]:
            p = pieces[name]
            im = ns["piece_png"](p)
            total += 1
            ok = not split(ns, v, name, im)
            e = im.copy()                                   # one pixel: colour + 1 at the first block's (0,0)
            bx, by = p["pos"][0]
            i = e.getpixel((bx, by))
            e.putpixel((bx, by), (i - i % 4 + (i % 4 + 1) % 4) if p["multi"] else (i + 1) % 4)
            r2 = split(ns, v, name, e)
            ok2 = any(not l.startswith("note:") for l in r2)
            two = p["multi"] and len(p["attr_of_slot"]) == 2
            ok3 = True
            if two:
                e = im.copy()
                o = p["blocks"][0]["grid"][0][0]
                other = next(s for s in p["attr_of_slot"] if s != o)
                for y in range(8):
                    for x in range(8):
                        e.putpixel((bx + x, by + y), other * 4 + e.getpixel((bx + x, by + y)) % 4)
                r3 = split(ns, v, name, e)
                ok3 = any("new rows" in l for l in r3) and not any(" line " in l for l in r3)
            print("%-12s %-8s unedited: %-9s one pixel: %-9s palette move: %s"
                  % (v["key"], name, "no change" if ok else "CHANGES", "reported" if ok2 else "MISSED", ("reported" if ok3 else "MISSED") if two else "n/a"))
            bad += (not ok) + (not ok2) + (not ok3)
    print("%d pieces, %d failures" % (total, bad))
    return bad


if __name__ == "__main__":
    ns = load_build()
    if sys.argv[1:] == ["--selftest"]:
        sys.exit(1 if selftest(ns) else 0)
    key, name, path = sys.argv[1:4]
    from PIL import Image
    v = next(x for x in ns["venues"] if x["key"] == key)
    out = split(ns, v, name, Image.open(path))
    print("\n".join(out) if out else "no changes")
