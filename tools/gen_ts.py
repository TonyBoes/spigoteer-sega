#!/usr/bin/env python3
"""T-Shirt Cannon art and landing table (src/ts.c, docs/minigames_bosses.md 4.2; look A, the night game, plus A1, the bunting between
the floodlight masts; approved by the owner 2026-10-12) -> build/ts_art.h (src/ts.c's bank), build/ts.json (tests) and x8 previews
out/preview/ts_*_x8.png. Fails when tools/cannon_table.py's fairness rule does not hold.

  assets/art/tshirt/stands.txt    BG 8x8 x 15: sky, star 1, star 2, seat, seat (left edge), board A, board B, grass, grass dark, foul line,
                                  foul line dark, floodlight L / M / R, mast
  assets/art/tshirt/fans.txt      BG 8x16 x 6: cap fan sit / hands up A / hands up B, headband fan sit / up A / up B (BG pal 2 red, 3 blue)
  assets/art/tshirt/meter.txt     BG 8x8 x 8: the power meter's bar, top to bottom (map column 1, rows 3-10; pal 0)
  assets/art/tshirt/bunting.txt   BG 80x16: the 8 flags (map columns 7-16, rows 3-4; pal 0 / 3 alternating, the ends pal 7)
  assets/art/tshirt/hud.txt       BG 8x8 x 2: shirt icon, '!' (HUD pal 1)
  assets/art/tshirt/cannon.txt    OBJ 16x16 x 1 (2 entries): the 60 degree barrel
  assets/art/tshirt/shirt.txt     OBJ 8x8 x 4: the spin frames; puff.txt 2 frames; marker.txt 1 (the power marker)

The map is built here as the mock-up did (sky and stars, floodlights, masts, stands, ad boards, grass, bunting, the meter; sitting fans): map rows 1-17, 20 tiles each, as tile ids (offsets from TS_BG) and CGB palettes.

OBJ entries (8x16) are numbered in the order of this file and put at OBJ tile ids 56.. (the venue's drink at 56-57 is not used here).

Usage: gen_ts.py outdir previewdir
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cannon_table  # noqa: E402
from gen_art import blocks, png, rgb15, tile_bytes  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "assets/art/tshirt"
HEADER = "; Art: approved design (owner 2026-10-12)"
OBJ_FIRST = 56
STARS = [(4, 1, 1), (6, 2, 2), (1, 6, 1), (5, 8, 2), (3, 10, 1), (7, 4, 2), (0, 2, 2), (8, 12, 1), (2, 12, 2), (5, 5, 1), (12, 2, 1), (9, 3, 2)]
METER_COL, METER_ROW = 1, 3


def frames(name, n, w, h):
    path = ART / f"{name}.txt"
    if not path.read_text().startswith(HEADER):
        sys.exit(f"gen_ts: assets/art/tshirt/{name}.txt: the first line must start with '{HEADER}'")
    fr = [r for _, r in blocks(path)]
    if len(fr) != n or not all(len(f) == h and all(len(r) == w and set(r) <= set(".-+#") for r in f) for f in fr):
        sys.exit(f"gen_ts: assets/art/tshirt/{name}.txt: needs {n} frames of {w}x{h} in . - + #")
    return fr


def carr(name, data, typ="uint8_t"):
    w = 4 if typ == "uint16_t" else 2
    return f"static const {typ} {name}[{len(data)}] = {{ " + ", ".join(f"0x{b:0{w}X}" if typ != "int8_t" else str(b) for b in data) + " };"


def fan_top(c):
    return cannon_table.top_row(c)


def main():
    outdir, prev = Path(sys.argv[1]), Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True)
    prev.mkdir(parents=True, exist_ok=True)
    stands = frames("stands", 15, 8, 8)
    fans = frames("fans", 6, 8, 16)
    meter = frames("meter", 8, 8, 8)
    bunt = frames("bunting", 1, 80, 16)[0]
    hud = frames("hud", 2, 8, 8)
    cannon = frames("cannon", 1, 16, 16)
    shirt = frames("shirt", 4, 8, 8)
    puff = frames("puff", 2, 8, 8)
    marker = frames("marker", 1, 8, 8)[0]
    SKY, STAR1, STAR2, SEAT, SEAT_L, BOARD_A, BOARD_B, G1, G2, GL1, GL2, LAMP_L, LAMP_M, LAMP_R, MAST = range(15)

    bg, seen = [], {}

    def tile(f, tx=0, ty=0):
        b = tuple(tile_bytes(f, tx, ty))
        if b not in seen:
            seen[b] = len(bg)
            bg.append(b)
        return seen[b]

    st = [tile(f) for f in stands]
    cell = {}                                    # (col, row) -> (tile id, CGB palette)

    def put(c, r, t, p):
        cell[(c, r)] = (t, p)

    for r in range(1, 13):
        for c in range(20):
            put(c, r, st[SKY], 0)
    for c, r, k in STARS:
        put(c, r, st[STAR1 if k == 1 else STAR2], 0)
    for c0 in (5, 14):                           # floodlight banks on row 1
        for i, t in enumerate((LAMP_L, LAMP_M, LAMP_M, LAMP_M, LAMP_R)):
            put(c0 + i, 1, st[t], 7)
    for r in range(2, 6):
        put(16, r, st[MAST], 7)
    for r in range(2, 13):
        put(7, r, st[MAST], 7)
    for c in range(cannon_table.FAN_FIRST, cannon_table.FAN_FIRST + cannon_table.FAN_N):   # the stands under the fans
        rt = fan_top(c)
        for r in range(rt + 2, 13):
            put(c, r, st[SEAT_L if (c == 9 or (c > 9 and (c - 9) % 2 == 0)) else SEAT], 5)
    for c in range(20):
        put(c, 13, st[BOARD_A if c % 2 == 0 else BOARD_B], 5)
    for r in (14, 15, 16, 17):
        for c in range(20):
            dark = (c // 2) % 2
            t = (GL2 if dark else GL1) if r == 16 else (G2 if dark else G1)
            put(c, r, st[t], 6)
    meter_t = [tile(f) for f in meter]
    for r in range(8):                           # the power meter's bar: map column 1, rows 3-10 (63 at the top .. 0 at the bottom)
        put(METER_COL, METER_ROW + r, meter_t[r], 0)
    for j in range(10):                          # the bunting, rows 3-4, columns 7-16
        for r in range(2):
            put(7 + j, 3 + r, tile(bunt, 8 * j, 8 * r), 7 if j in (0, 9) else (0 if j % 2 else 3))
    fan_t = []                                   # [cap sit, up A, up B, band sit, up A, up B] -> top, bottom
    for f in fans:
        fan_t += [tile(f, 0, 0), tile(f, 0, 8)]
    for c in range(cannon_table.FAN_FIRST, cannon_table.FAN_FIRST + cannon_table.FAN_N):
        kind = 0 if c % 2 == 1 else 3
        rt = fan_top(c)
        put(c, rt, fan_t[2 * kind], 2 if kind == 0 else 3)
        put(c, rt + 1, fan_t[2 * kind + 1], 2 if kind == 0 else 3)
    hud_t = [tile(f) for f in hud]
    n_bg = len(bg)
    tmap = [cell[(c, r)][0] for r in range(1, 18) for c in range(20)]
    amap = [cell[(c, r)][1] for r in range(1, 18) for c in range(20)]

    ents, ent_id = [], {}

    def entry(f, x0, y0, tall):
        e = tuple(tile_bytes(f, x0, y0) + (tile_bytes(f, x0, y0 + 8) if tall else [0] * 16))
        if e not in ent_id:
            ent_id[e] = len(ents)
            ents.append(e)
        return OBJ_FIRST + 2 * ent_id[e]

    cannon_e = [entry(cannon[0], x, 0, True) for x in (0, 8)]
    shirt_e = [entry(f, 0, 0, False) for f in shirt]
    puff_e = [entry(f, 0, 0, False) for f in puff]
    marker_e = entry(marker, 0, 0, False)
    obj = [b for e in ents for b in e]
    if OBJ_FIRST + 2 * len(ents) > 92:
        sys.exit("gen_ts: too many OBJ tiles (the coin is at 92)")

    tb = cannon_table.table()
    bad = cannon_table.problems(tb)
    print(cannon_table.report(tb))
    if bad:
        sys.exit("gen_ts: the landing table breaks the fairness rule:\n  " + "\n  ".join(bad))
    sm, om = cannon_table.zones(tb)
    for t, f in enumerate(meter):                # the meter's red zones are the table's short and over powers
        for r, row in enumerate(f):
            p = cannon_table.PMAX - 8 * t - r
            if r and not (t == 7 and r == 7) and (row[3] == "+") != (p <= sm or p >= om):
                sys.exit(f"gen_ts: meter.txt tile {t} row {r} (power {p}): the red zones are power 0-{sm} and {om}-{cannon_table.PMAX}")

    pals_bg = [                                  # CGB BG palettes 0, 2, 3, 5, 6, 7
        ["#384058", "#f8f8f8", "#e04030", "#301018"],            # 0 sky, stars, red flags
        ["#384058", "#f0b888", "#e04030", "#201020"],            # 2 red fans
        ["#384058", "#f0b888", "#4878e8", "#101840"],            # 3 blue fans, blue flags
        ["#c8d0e8", "#7880a0", "#505878", "#202438"],            # 5 stands, boards
        ["#f0f0e0", "#3c9448", "#2c7038", "#1c3c28"],            # 6 grass
        ["#384058", "#f8f8f8", "#f08020", "#a8b4d8"],            # 7 windsock, pole, floodlights, masts
    ]
    pals_obj = [                                 # CGB OBJ palettes 1, 2, 3
        ["#000000", "#f8f8f8", "#a0a8c0", "#101020"],            # 1 puff, the power marker
        ["#000000", "#f8f8f8", "#e04030", "#201020"],            # 2 shirt
        ["#000000", "#d0d8e8", "#d83830", "#201428"],            # 3 cannon
    ]
    c15 = lambda pal: rgb15(pal)                 # noqa: E731
    flat = lambda ps: [c for p in ps for c in c15(p)]   # noqa: E731
    lines = [
        "// generated by tools/gen_ts.py from assets/art/tshirt/*.txt and tools/cannon_table.py -- do not edit; #included by src/ts.c (its bank)",
        f"#define TS_BG_TILES {n_bg}   // from TS_BG: the stage, the fans, the windsock looks, the bunting, the HUD pieces",
        f"#define TS_OBJ {OBJ_FIRST}   // OBJ tile id of the first entry: TS_OBJ_TILES tiles",
        f"#define TS_OBJ_TILES {len(obj) // 16}",
        f"#define TS_V0 {cannon_table.V0}   // launch speed 8.8 px/f at power 0, + TS_DV a step, TS_PMAX steps (tools/cannon_table.py)",
        f"#define TS_DV {cannon_table.DV}",
        f"#define TS_PMAX {cannon_table.PMAX}",
        f"#define TS_MUZZLE_X {cannon_table.MUZZLE[0]}   // the 60 degree barrel's tip, screen px",
        f"#define TS_MUZZLE_Y {cannon_table.MUZZLE[1]}",
        "// map rows 1-17 (20 tiles each, offsets from TS_BG) and their CGB palettes (the sitting fans, the meter's bar)",
        carr("ts_map", tmap),
        carr("ts_attr", amap),
        "// BG tile offsets: the fans [cap sit top, bottom, up A top, bottom, up B, band sit, up A, up B] (6 frames x 2), the HUD [shirt, '!']",
        carr("ts_fan", fan_t),
        carr("ts_hud", hud_t),
        "// OBJ tile ids of the 8x16 entries: the cannon [left, right], the shirt's 4 spins, the puff's 2, the power marker",
        carr("ts_cannon", cannon_e),
        carr("ts_shirt", shirt_e),
        carr("ts_puff", puff_e),
        f"#define TS_MARKER {marker_e}",
        "// CGB palettes (RGB15): BG 0, 2, 3, 5, 6, 7 and OBJ 1, 2, 3",
        carr("ts_pal_bg", flat(pals_bg), "uint16_t"),
        carr("ts_pal_obj", flat(pals_obj), "uint16_t"),
        carr("ts_bg_tiles", [b for t in bg for b in t]),
        carr("ts_obj_tiles", obj), ""]
    (outdir / "ts_art.h").write_text("\n".join(lines))
    js = cannon_table.to_json(tb)
    js.update({"n_bg": n_bg, "obj_tiles": len(obj) // 16, "map": tmap, "attr": amap, "fan": fan_t, "meter": meter_t, "hud": hud_t,
               "cannon": cannon_e, "shirt": shirt_e, "puff": puff_e, "marker": marker_e, "bg": [b for t in bg for b in t], "obj": obj,
               "pal_bg": [c15(p) for p in pals_bg], "pal_obj": [c15(p) for p in pals_obj]})
    (outdir / "ts.json").write_text(json.dumps(js))
    png(stands, prev / "ts_stage_x8.png", 8)
    png(fans + hud + meter, prev / "ts_fans_hud_meter_x8.png", 8)
    png([bunt], prev / "ts_bunting_x8.png", 8)
    png(cannon + shirt + puff + [marker], prev / "ts_sprites_x8.png", 8, transparent=True)


if __name__ == "__main__":
    main()
