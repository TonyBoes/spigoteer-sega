#!/usr/bin/env python3
"""Milk Run art (src/mr.c, docs/minigames_bosses.md 4.10; approved by the owner 2026-10-12) -> build/mr_art.h (src/mr.c's
bank), build/mr.json (tests) and x8 previews out/preview/mr_*_x8.png.

  assets/art/milkrun/road.txt        BG: road plain, road dashed, pavement slab, top kerb, bottom kerb: 5 tiles 8x8
  assets/art/milkrun/box.txt         BG: the milk box 16x16, 4 frames: top empty, top full, bottom empty, bottom full
  assets/art/milkrun/pothole.txt     BG: the pothole 16x16
  assets/art/milkrun/cone.txt        BG: the traffic cone 8x16 (set in pairs)
  assets/art/milkrun/verge_house.txt BG: the house 32x24 (4x3 tiles)
  assets/art/milkrun/verge_tree.txt  BG: the tree 16x16
  assets/art/milkrun/verge_tiles.txt BG: lawn, picket fence, hedge: 3 tiles 8x8
  assets/art/milkrun/hud_crate.txt   BG: the HUD's crates-left icon 8x8
  assets/art/milkrun/hud_gauge.txt   BG: the HUD speed gauge's cell, 3 tiles 8x8: empty, half, full (D4 rework)
  assets/art/milkrun/bottle.txt      OBJ: the milk-bottle pickup 8x16, 1 frame (D4 rework)
  assets/art/milkrun/bike.txt        OBJ: the bike, 3 frames 24x16 (ride A, ride B, wobble): 3 entries 8x16 a frame
  assets/art/milkrun/rider.txt       OBJ: the Spigoteer overlay, 3 frames 8x16 (one entry each)
  assets/art/milkrun/crate.txt       OBJ: the tossed crate, 2 frames 8x16 (low, high)
  assets/art/milkrun/stars.txt       OBJ: the crash stars 8x16 (the second entry is drawn X-flipped)
  assets/art/milkrun/pop.txt         OBJ: the PERFECT pop 16x16 (2 entries)

The street's verges are periodic (the lots of the proposal's mock-up): the top verge's 23 columns (houses, trees, lawn and
hedge on map rows 1-3), the bottom verge's 40 (two passes of 20: the houses alternate palettes 2 and 6 along the street)
on rows 14-17; src/mr.c streams them with the road, the kerbs, the gates and the boxes one map column at a time.

Usage: gen_mr.py outdir previewdir
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_art import blocks, png, tile_bytes  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "assets/art/milkrun"
HEADER = "; Art: approved design (owner 2026-10-12)"
TOP_LOTS, BOT_LOTS = "HTHLTHHT", "TLHHTLHT"
PAL_ROAD, PAL_HOUSE_A, PAL_BOX, PAL_GREEN, PAL_HOUSE_B, PAL_CONE = 0, 2, 3, 5, 6, 7


HEADER_NEW = "; Art: new for the D4 rework"    # (the bottle and the gauge: not yet owner-judged)


def frames(name, n, w, h, header=HEADER):
    path = ART / f"{name}.txt"
    if not path.read_text().startswith(header):
        sys.exit(f"gen_mr: assets/art/milkrun/{name}.txt: the first line must start with '{header}'")
    fr = [r for _, r in blocks(path)]
    if len(fr) != n or not all(len(f) == h and all(len(r) == w and set(r) <= set(".-+#") for r in f) for f in fr):
        sys.exit(f"gen_mr: assets/art/milkrun/{name}.txt: needs {n} frames of {w}x{h} in . - + #")
    return fr


def tiles_rowmajor(f):
    out = []
    for ty in range(0, len(f), 8):
        for tx in range(0, len(f[0]), 8):
            out.append(tile_bytes(f, tx, ty))
    return out


def carr(name, data, typ="uint8_t"):
    return f"static const {typ} {name}[{len(data)}] = {{ " + ", ".join(f"0x{b:02X}" for b in data) + " };"


def strips(houses):
    """-> (top tiles, top pals, bottom tiles, bottom pals): per column its rows, as offsets from MR_BG."""
    T = {k: v for k, v in houses.items()}
    top_t, top_p, bot_t, bot_p = [], [], [], []

    def lots(seq, passes, k0, top):
        k = k0
        for _ in range(passes):
            for lot in seq:
                if lot == "H":
                    for i in range(4):
                        pal = PAL_HOUSE_A if k % 2 == 0 else PAL_HOUSE_B
                        if top:
                            col = [(T["house"] + r * 4 + i, pal) for r in range(3)]
                        else:
                            col = [(T["fence"], PAL_GREEN)] + [(T["house"] + r * 4 + i, pal) for r in range(3)]
                        yield col
                    k += 1
                elif lot == "T":
                    for i in range(2):
                        if top:
                            col = [(T["tree"] + r * 2 + i, PAL_GREEN) for r in range(2)] + [(T["fence"], PAL_GREEN)]
                        else:
                            col = [(T["hedge"], PAL_GREEN)] + [(T["tree"] + r * 2 + i, PAL_GREEN) for r in range(2)] \
                                  + [(T["lawn"], PAL_GREEN)]
                        yield col
                else:
                    if top:
                        col = [(T["lawn"], PAL_GREEN)] * 2 + [(T["hedge"], PAL_GREEN)]
                    else:
                        col = [(T["hedge"], PAL_GREEN)] + [(T["lawn"], PAL_GREEN)] * 3
                    yield col

    for col in lots(TOP_LOTS, 1, 0, True):
        top_t += [t for t, _ in col]; top_p += [p for _, p in col]
    for col in lots(BOT_LOTS, 2, 1, False):
        bot_t += [t for t, _ in col]; bot_p += [p for _, p in col]
    return top_t, top_p, bot_t, bot_p


def main():
    outdir, prev = Path(sys.argv[1]), Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True); prev.mkdir(parents=True, exist_ok=True)
    road = frames("road", 5, 8, 8)
    box = frames("box", 4, 16, 16)
    pot = frames("pothole", 1, 16, 16)[0]
    cone = frames("cone", 1, 8, 16)[0]
    house = frames("verge_house", 1, 32, 24)[0]
    tree = frames("verge_tree", 1, 16, 16)[0]
    green = frames("verge_tiles", 3, 8, 8)
    # the HUD font's two colours: its glyph is index 0, its band index 3 (navy; DMG black). The approved art draws the band
    # with '+' (the proposal's mock-up painted indexes 2 and 3 alike); the real palette 1 has orange at index 2, so the
    # band is exported as index 3 (the art file itself is as approved).
    hudc = [r.replace("+", "#") for r in frames("hud_crate", 1, 8, 8)[0]]
    gauge = frames("hud_gauge", 3, 8, 8, HEADER_NEW)
    bottle = frames("bottle", 1, 8, 16, HEADER_NEW)
    bike = frames("bike", 3, 24, 16)
    rider = frames("rider", 3, 8, 16)
    crate = frames("crate", 2, 8, 16)
    stars = frames("stars", 1, 8, 16)[0]
    pop = frames("pop", 1, 16, 16)[0]

    bg, off = [], {}

    def add(name, tiles):
        off[name] = len(bg) // 16
        for t in tiles:
            bg.extend(t)

    add("road", [tile_bytes(f, 0, 0) for f in road])             # plain, dashed, slab, top kerb, bottom kerb
    add("box", [t for f in box for t in tiles_rowmajor(f)])      # 4 frames x (TL, TR, BL, BR)
    add("pot", tiles_rowmajor(pot))
    add("cone", tiles_rowmajor(cone))                            # top, bottom
    add("house", tiles_rowmajor(house))
    add("tree", tiles_rowmajor(tree))
    add("lawn", [tile_bytes(green[0], 0, 0)])
    add("fence", [tile_bytes(green[1], 0, 0)])
    add("hedge", [tile_bytes(green[2], 0, 0)])
    add("hudc", [tile_bytes(hudc, 0, 0)])
    add("gauge", [tile_bytes(f, 0, 0) for f in gauge])           # empty, half, full
    n_bg = len(bg) // 16
    top_t, top_p, bot_t, bot_p = strips(off)
    n_top, n_bot = len(top_t) // 3, len(bot_t) // 4

    # OBJ: 8x16 entries (top tile, bottom tile), the bike's deduplicated across its frames
    ents = []

    def entry(f, ex):
        e = tuple(tile_bytes(f, ex, 0) + tile_bytes(f, ex, 8))
        if e not in ents:
            ents.append(e)
        return 2 * ents.index(e)

    bike_t = [entry(f, 8 * c) for f in bike for c in range(3)]
    rider_t = [entry(f, 0) for f in rider]
    crate_t = [entry(f, 0) for f in crate]
    stars_t = entry(stars, 0)
    pop_t = [entry(pop, 0), entry(pop, 8)]
    bottle_t = [entry(f, 0) for f in bottle]
    obj = [b for e in ents for b in e]
    n_obj = len(obj) // 16

    names = ["ROAD0", "ROAD1", "SLAB", "KERB_TOP", "KERB_BOT"]
    lines = [
        "// generated by tools/gen_mr.py from assets/art/milkrun/*.txt -- do not edit; #included by src/mr.c (its bank)",
        f"#define MR_BG_TILES {n_bg}   // from MR_BG: road, boxes, pothole, cone, house, tree, lawn / fence / hedge, HUD crate",
        *[f"#define MRB_{n} {i}" for i, n in enumerate(names)],
        f"#define MRB_BOX {off['box']}       // 4 frames x 4 (TL TR BL BR): top empty, top full, bottom empty, bottom full",
        f"#define MRB_POT {off['pot']}       // TL TR BL BR",
        f"#define MRB_CONE {off['cone']}      // top, bottom",
        f"#define MRB_HOUSE {off['house']}     // 4x3, row-major",
        f"#define MRB_TREE {off['tree']}      // 2x2",
        f"#define MRB_LAWN {off['lawn']}", f"#define MRB_FENCE {off['fence']}", f"#define MRB_HEDGE {off['hedge']}",
        f"#define MRB_HUDC {off['hudc']}      // the HUD's crate icon",
        f"#define MR_TOP_N {n_top}   // the top verge's period in columns (3 rows each: map rows 1-3)",
        f"#define MR_BOT_N {n_bot}   // the bottom verge's period (4 rows each: map rows 14-17)",
        f"#define MR_OBJ_TILES {n_obj}   // OBJ tiles: {n_obj // 2} 8x16 entries (the bike's deduplicated, the rider, crate, stars, pop)",
        f"#define MRO_RIDER_A {rider_t[0]}", f"#define MRO_RIDER_B {rider_t[1]}", f"#define MRO_RIDER_W {rider_t[2]}",
        f"#define MRO_CRATE_LO {crate_t[0]}", f"#define MRO_CRATE_HI {crate_t[1]}",
        f"#define MRB_GAUGE {off['gauge']}     // the speed gauge's cells: empty, half, full",
        f"#define MRO_BOTTLE {bottle_t[0]}",
        f"#define MRO_STARS {stars_t}", f"#define MRO_POP_L {pop_t[0]}", f"#define MRO_POP_R {pop_t[1]}",
        "// the bike's three entries (x + 0, 8, 16) of ride A, ride B and the wobble, as OBJ tile numbers from MR_OBJ",
        carr("mr_bike_t", bike_t),
        carr("mr_top_t", top_t), carr("mr_top_a", top_p), carr("mr_bot_t", bot_t), carr("mr_bot_a", bot_p),
        carr("mr_bg_tiles", bg), carr("mr_obj_tiles", obj), ""]
    (outdir / "mr_art.h").write_text("\n".join(lines))
    (outdir / "mr.json").write_text(json.dumps({
        "bg": bg, "obj": obj, "off": off, "n_bg": n_bg, "n_obj": n_obj, "bike_t": bike_t, "rider_t": rider_t,
        "crate_t": crate_t, "bottle_t": bottle_t, "stars_t": stars_t, "pop_t": pop_t, "top_t": top_t, "top_p": top_p, "bot_t": bot_t,
        "bot_p": bot_p}))
    png(road, prev / "mr_road_x8.png", 8)
    png(box, prev / "mr_box_x8.png", 8)
    png([pot, tree], prev / "mr_pothole_tree_x8.png", 8)
    png([cone] + green + [hudc], prev / "mr_cone_verge_x8.png", 8)
    png([house], prev / "mr_house_x8.png", 8)
    png(bike, prev / "mr_bike_x8.png", 8, transparent=True)
    png(bottle + [r for r in gauge], prev / "mr_bottle_gauge_x8.png", 8, transparent=True)
    png(rider + crate + [stars, pop], prev / "mr_sprites_x8.png", 8, transparent=True)


if __name__ == "__main__":
    main()
