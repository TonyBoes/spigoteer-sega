#!/usr/bin/env python3
"""Asteroid Delivery art (src/ad.c, docs/minigames_bosses.md 4.8; approved by the owner 2026-10-12: look A's stage with look
B's asteroids) -> build/ad_art.h (src/ad.c's bank), build/ad.json (tests) and x8 previews out/preview/ad_*_x8.png.

  assets/art/asteroid/sky.txt        BG: the starfield, 5 tiles 8x8 (plain + 4 star variants), palette 2
  assets/art/asteroid/sky_lane.txt   BG: the same 5 with the dotted lane separator on their top edge
  assets/art/asteroid/counter.txt    BG: the counter, 2 tiles 8x8, palette 3
  assets/art/asteroid/hud.txt        BG: the HUD's beaker icon 8x8
  assets/art/asteroid/porthole<n>.txt BG: porthole n, 24x24 (3x3 tiles), 2 frames: unlit, lit; the alien's palette 5 / 6 / 7
  assets/art/asteroid/rocks.txt      OBJ: the asteroids, 2 shapes 16x16 (2 entries 8x16 each)
  assets/art/asteroid/tumble.txt     OBJ: the spilled beaker turned 90 / 180 / 270 degrees, 3 frames 16x16
  assets/art/asteroid/halo.txt       OBJ: the glow halo, 2 frames 16x16
  assets/art/asteroid/puff.txt       OBJ: the thrust puff, 2 frames 8x16 (one entry each)
  assets/art/asteroid/arrow.txt      OBJ: the arrow over the lit porthole, 2 frames 8x16

The CGB palettes are the approved look's: the sky (A's), the counter, the three aliens' own patron palettes (assets/palettes.json
aliens_a / b / c with colour 0 = the space lounge's wall), B's blue rocks, the arrow, the puff and halo. The beaker is the
venue's own drink frame 0 (OBJ tiles 56-57, OBJ palette 1: load_venue).

OBJ entries are numbered in the order of this file and put at OBJ tile ids 58.. (17 entries up to 91), the rest from 96: the coin
at 92-95 is loaded once at boot; the venue's drink frame 0 holds 56-57. An entry with no pixels is 0xFF (not drawn).

Usage: gen_ad.py outdir previewdir
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_art import blocks, png, rgb15, tile_bytes  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "assets/art/asteroid"
HEADER = "; Art: approved design (owner 2026-10-12)"
PROPOSED = "; Art: proposed"                 # art made after the approval (the owner judges it from the x8 preview)
OBJ_A, OBJ_A_ENTRIES, OBJ_B = 58, 17, 96


def frames(name, n, w, h):
    path = ART / f"{name}.txt"
    if not path.read_text().startswith((HEADER, PROPOSED)):
        sys.exit(f"gen_ad: assets/art/asteroid/{name}.txt: the first line must start with '{HEADER}'")
    fr = [r for _, r in blocks(path)]
    if len(fr) != n or not all(len(f) == h and all(len(r) == w and set(r) <= set(".-+#") for r in f) for f in fr):
        sys.exit(f"gen_ad: assets/art/asteroid/{name}.txt: needs {n} frames of {w}x{h} in . - + #")
    return fr


def carr(name, data, typ="uint8_t"):
    return f"static const {typ} {name}[{len(data)}] = {{ " + ", ".join(f"0x{b:02X}" for b in data) + " };"


def main():
    outdir, prev = Path(sys.argv[1]), Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True); prev.mkdir(parents=True, exist_ok=True)
    sky = frames("sky", 5, 8, 8)
    sep = frames("sky_lane", 5, 8, 8)
    counter = frames("counter", 2, 8, 8)
    hud = frames("hud", 1, 8, 8)[0]
    ports = [frames(f"porthole{i}", 2, 24, 24) for i in (1, 2, 3)]
    rocks = frames("rocks", 2, 16, 16)
    tumble = frames("tumble", 3, 16, 16)
    halo = frames("halo", 2, 16, 16)
    puff = frames("puff", 2, 8, 16)
    arrow = frames("arrow", 2, 8, 16)
    edge = frames("edge", 1, 8, 16)

    bg, seen = [], {}

    def tile(f, tx, ty):
        b = tuple(tile_bytes(f, tx, ty))
        if b not in seen:
            seen[b] = len(bg)
            bg.append(b)
        return seen[b]

    sky_t = [tile(f, 0, 0) for f in sky]
    sep_t = [tile(f, 0, 0) for f in sep]
    ctr_t = [tile(f, 0, 0) for f in counter]
    hud_t = tile(hud, 0, 0)
    port_t = [[[tile(f, 8 * c, 8 * r) for r in range(3) for c in range(3)] for f in p] for p in ports]
    n_bg = len(bg)

    ents, ent_id = [], {}
    n_raw = 0

    def entry(f, ex):
        nonlocal n_raw
        n_raw += 1
        e = tuple(tile_bytes(f, ex, 0) + tile_bytes(f, ex, 8))
        if not any(e):
            return 0xFF
        if e not in ent_id:
            ent_id[e] = len(ents)
            ents.append(e)
        return ent_id[e]

    def obj_id(slot):
        if slot == 0xFF:
            return 0xFF
        return OBJ_A + 2 * slot if slot < OBJ_A_ENTRIES else OBJ_B + 2 * (slot - OBJ_A_ENTRIES)

    rock_e = [entry(f, x) for f in rocks for x in (0, 8)]
    tumble_e = [entry(f, x) for f in tumble for x in (0, 8)]
    halo_e = [entry(f, x) for f in halo for x in (0, 8)]
    puff_e = [entry(f, 0) for f in puff]
    arrow_e = [entry(f, 0) for f in arrow]
    edge_e = [entry(f, 0) for f in edge]
    a_n = min(len(ents), OBJ_A_ENTRIES)
    obj_a = [b for e in ents[:a_n] for b in e]
    obj_b = [b for e in ents[a_n:] for b in e]
    if len(ents) - a_n > (127 - OBJ_B + 1) // 2:
        sys.exit("gen_ad: too many OBJ entries")

    pj = json.load(open(ROOT / "assets/palettes.json"))
    sp = json.load(open(ROOT / "assets/approved/venues/space_pal.json"))
    wall = sp["bar"]["hex"][0]
    pals_bg = [
        ["#ffffff", "#8a98d8", "#2c3470", "#050716"],            # 0 the sky (A)
        ["#c8d8f0", "#7890c0", "#384880", "#101830"],            # 1 the counter (A)
    ] + [[wall] + pj[k]["hex"] for k in ("aliens_a", "aliens_b", "aliens_c")]
    pals_obj = [
        ["#000000", "#d8f4ff", "#5898d0", "#101860"],            # 0 the rocks (B)
        ["#000000", "#fff878", "#ffa030", "#281808"],            # 1 the arrow
        ["#000000", "#ffffff", "#90d8ff", "#4060c0"],            # 2 the puff and the halo
    ]
    c15 = lambda pal: [c for c in rgb15([h for h in pal])]       # noqa: E731

    flat = lambda ts: [b for t in ts for b in t]                 # noqa: E731
    lines = [
        "// generated by tools/gen_ad.py from assets/art/asteroid/*.txt -- do not edit; #included by src/ad.c (its bank)",
        f"#define AD_BG_TILES {n_bg}   // from AD_BG: sky, sky with the lane line, counter, the HUD icon, the three portholes",
        f"#define ADB_HUDI {hud_t}",
        f"#define AD_OBJ_A {OBJ_A}   // OBJ tile id of the first block: AD_OBJ_A_TILES tiles",
        f"#define AD_OBJ_A_TILES {len(obj_a) // 16}",
        f"#define AD_OBJ_B {OBJ_B}   // the second block: AD_OBJ_B_TILES tiles",
        f"#define AD_OBJ_B_TILES {len(obj_b) // 16}",
        "// OBJ tile ids of the 8x16 entries (0xFF: no pixels, not drawn)",
        carr("ad_rock", [obj_id(e) for e in rock_e]) + "     // shape 0 left, right; shape 1 left, right",
        carr("ad_tumble", [obj_id(e) for e in tumble_e]) + "   // 90, 180, 270 degrees: left, right",
        carr("ad_halo", [obj_id(e) for e in halo_e]) + "     // 2 frames: left, right",
        carr("ad_puff", [obj_id(e) for e in puff_e]),
        carr("ad_arrow", [obj_id(e) for e in arrow_e]),
        carr("ad_edge", [obj_id(e) for e in edge_e]) + "   // the edge warning (points right)",
        "// BG tile ids (offsets from AD_BG)",
        carr("ad_sky", sky_t) + "    // plain, 4 star variants",
        carr("ad_sep", sep_t) + "    // the same with the lane line",
        carr("ad_counter", ctr_t),
        carr("ad_port", [t for p in port_t for f in p for t in f], "uint8_t") + "   // [porthole 3][unlit, lit][9 tiles row-major]",
        "// CGB palettes (RGB15): BG 2 the sky, 3 the counter, 5 / 6 / 7 the aliens'; OBJ 3 the rocks, 7 the arrow, 6 the puff and halo",
        carr("ad_pal_bg", flat(c15(p) for p in pals_bg), "uint16_t"),
        carr("ad_pal_obj", flat(c15(p) for p in pals_obj), "uint16_t"),
        carr("ad_bg_tiles", [b for t in bg for b in t]),
        carr("ad_obj_a_tiles", obj_a),
        carr("ad_obj_b_tiles", obj_b or [0]), ""]
    # uint16 arrays print as 2-digit hex above; rewrite with 4 digits
    text = "\n".join(lines)
    import re
    def fix(m):
        name = m.group(1)
        vals = m.group(3).split(", ")
        return f"static const uint16_t {name}[{m.group(2)}] = {{ " + ", ".join(f"0x{int(v, 16):04X}" for v in vals) + " };"
    text = re.sub(r"static const uint16_t (\w+)\[(\d+)\] = \{ (.*?) \};", fix, text)
    (outdir / "ad_art.h").write_text(text)
    (outdir / "ad.json").write_text(json.dumps({
        "bg": [b for t in bg for b in t], "obj_a": obj_a, "obj_b": obj_b, "n_bg": n_bg, "sky": sky_t, "sep": sep_t,
        "counter": ctr_t, "hudi": hud_t, "port": port_t, "rock": [obj_id(e) for e in rock_e],
        "tumble": [obj_id(e) for e in tumble_e], "halo": [obj_id(e) for e in halo_e], "puff": [obj_id(e) for e in puff_e],
        "arrow": [obj_id(e) for e in arrow_e], "edge": [obj_id(e) for e in edge_e], "pal_bg": [c15(p) for p in pals_bg], "pal_obj": [c15(p) for p in pals_obj],
        "n_entries": len(ents), "n_raw_entries": n_raw}))
    png(sky + sep + counter + [hud], prev / "ad_stage_x8.png", 8)
    png([p[0] for p in ports] + [p[1] for p in ports], prev / "ad_portholes_x8.png", 8)
    png(rocks + tumble, prev / "ad_rocks_tumble_x8.png", 8, transparent=True)
    png(halo + puff + arrow + edge, prev / "ad_fx_x8.png", 8, transparent=True)


if __name__ == "__main__":
    main()
