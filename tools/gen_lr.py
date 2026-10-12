#!/usr/bin/env python3
"""Log Roll art (src/lr.c, docs/minigames_bosses.md 4.3; look A, the daytime river, approved by the owner 2026-10-12)
-> build/lr_art.h (src/lr.c's bank), build/lr.json (tests) and x8 previews out/preview/lr_*_x8.png.

  assets/art/logroll/forest.txt    BG: the pines and hedge unit 32x32 (4x4 tiles), repeated 5 times over rows 1-4
  assets/art/logroll/bank.txt      BG: the far bank, 4 tiles: row 5 variants 0 / 1, row 6 variants 0 / 1
  assets/art/logroll/water.txt     BG: river plain, ripple A frames 0 / 1, ripple B frames 0 / 1, the shadow band
  assets/art/logroll/log.txt       BG: 4 cap tiles (left top / bottom, right top / bottom), then 16 body tiles:
                                   roll frame 0..3 x variant X / Y x top / bottom
  assets/art/logroll/meter.txt     BG: balance meter tiles: dngL dngE safe tick ctrL ctrR dngE2 dngR
  assets/art/logroll/hud_drop.txt  BG: the HUD's falls icon 8x8
  assets/art/logroll/droplets.txt  OBJ: 4 splash droplets 8x8 art (the entry's bottom tile is blank)
  assets/art/logroll/marker.txt    OBJ: the balance marker 8x16
  assets/art/logroll/spigoteer.txt OBJ: the Spigoteer on the log, 6 frames 24x24 (C_a, C_b, L1, L2, SPLASH, CLIMB), each
                                   3 columns x 2 rows of 8x16 entries (padded to 24x32); right leans are the X-flip

The scene (the proposal's mock-up, rows 1-17 of the map): pines rows 1-4, far bank 5-6, river 7-17 with ripples (a hash
of the cell picks plain / ripple A / ripple B), the log on rows 12-13 (caps at columns 3 and 16, body 4-15 alternating
variant X / Y), a shadow under it (row 14, columns 3-16) and on row 7, the meter on row 16 (columns 2-17). The log's four
body tiles of one roll frame (64 B) and the two ripple tiles of one frame (32 B) are streamed into fixed slots by
src/lr.c (a VBlank copy); every other tile is resident. The streamed slots sit at BG ids 128+ (one VRAM address run).

Usage: gen_lr.py outdir previewdir
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_art import blocks, png, rgb15, tile_bytes  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "assets/art/logroll"
HEADER = "; Art: approved design (owner 2026-10-12"
BG0 = 125                   # MG_GAME_BG (src/mg.h)
STREAM_ID0 = 128            # the first streamed slot's BG id: one run of VRAM addresses (ids >= 128 are 0x8800 + 16 id)
PAL_FOREST, PAL_RIVER, PAL_LOG, PAL_METER, PAL_BANK = 2, 3, 5, 6, 7
# CGB colours of the proposal (look A): BG palettes by number, OBJ palettes for the droplets and the marker
BG_PALS = {
    2: ["#bfe0f0", "#f4fbff", "#2f7a4e", "#12342a"],   # forest / sky (colour 0 = sky)
    3: ["#e4f6fc", "#7cc0e0", "#3a80b8", "#1c4a78"],   # river
    5: ["#f0d8a0", "#c89258", "#80502c", "#2c1808"],   # log (colour 1 = the water so the rounded corners stay water)
    6: ["#fbf3dc", "#e8b050", "#c03828", "#2c1808"],   # meter plaque
    7: ["#e8d8b0", "#b8955a", "#6a4a2a", "#2a1c10"],   # far bank
}
OBJ_PALS = {
    1: ["#000000", "#f4fbff", "#7cc0e0", "#1c4a78"],   # droplets
    2: ["#000000", "#f8f8f0", "#e03830", "#301818"],   # marker
}
POSES = ["C_a", "C_b", "L1", "L2", "SPLASH", "CLIMB"]
SLOT_ENTRIES = 18           # OBJ ids 56-91 hold the first 18 entries; src/lr.c puts the rest above the BG tiles


def frames(name, n, w, hs):
    path = ART / f"{name}.txt"
    if not path.read_text().startswith(HEADER):
        sys.exit(f"gen_lr: assets/art/logroll/{name}.txt: the first line must start with '{HEADER}'")
    fr = [r for _, r in blocks(path)]
    if len(fr) != n or not all(len(f) in hs and all(len(r) == w and set(r) <= set(".-+#") for r in f) for f in fr):
        sys.exit(f"gen_lr: assets/art/logroll/{name}.txt: needs {n} frames of {w}x{'/'.join(map(str, hs))} in . - + #")
    return fr


def carr(name, data, typ="uint8_t"):
    return f"static const {typ} {name}[{len(data)}] = {{ " + ", ".join(f"0x{b:02X}" for b in data) + " };"


def hsh(c, r):
    return (c * 7 + r * 13 + (c * r) * 5) % 11


def main():
    outdir, prev = Path(sys.argv[1]), Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True); prev.mkdir(parents=True, exist_ok=True)
    forest = frames("forest", 1, 32, (32,))[0]
    bank = frames("bank", 4, 8, (8,))
    water = frames("water", 6, 8, (8,))                     # plain, ra0, ra1, rb0, rb1, shadow
    log = frames("log", 20, 8, (8,))
    meter = frames("meter", 8, 8, (8,))
    hud = frames("hud_drop", 1, 8, (8,))[0]
    drops = frames("droplets", 4, 8, (8, 16))
    marker = frames("marker", 1, 8, (16,))[0]
    spig = frames("spigoteer", 6, 24, (24,))

    T = lambda f: tuple(tile_bytes(f, 0, 0))                # an 8x8 frame -> its 16 bytes
    cap = [T(f) for f in log[:4]]                           # L top, L bottom, R top, R bottom
    body = [[T(log[4 + 4 * p + 2 * v + h]) for v in (0, 1) for h in (0, 1)] for p in range(4)]   # [roll][Xt Xb Yt Yb]
    rip = [T(water[1]), T(water[3])], [T(water[2]), T(water[4])]   # [frame][A, B]
    mt = {n: T(meter[i]) for i, n in enumerate(["dngL", "dngE", "safe", "tick", "ctrL", "ctrR", "dngE2", "dngR"])}

    # ---- the map, rows 1-17: a tile is ("S", bytes) resident, ("R", k) a roll slot, ("P", k) a ripple slot
    cells, pals = {}, {}
    for r in range(1, 18):
        for c in range(20):
            if r <= 4:
                t, p = ("S", tuple(tile_bytes(forest, 8 * (c & 3), 8 * (r - 1)))), PAL_FOREST
            elif r == 5:
                t, p = ("S", T(bank[c % 2])), PAL_BANK
            elif r == 6:
                t, p = ("S", T(bank[2 + (c // 2) % 2])), PAL_BANK
            elif 12 <= r <= 13 and 3 <= c <= 16:
                p = PAL_LOG
                if c == 3: t = ("S", cap[r - 12])
                elif c == 16: t = ("S", cap[2 + r - 12])
                else: t = ("R", (c % 2) * 2 + (r - 12))
            elif r == 16 and 2 <= c <= 17:
                n = {2: "dngL", 3: "dngE", 16: "dngE2", 17: "dngR", 9: "ctrL", 10: "ctrR"}.get(c)
                if n is None: n = "tick" if c in (6, 8, 12, 14) else "safe"
                t, p = ("S", mt[n]), PAL_METER
            else:
                p = PAL_RIVER
                if r == 7 or (r == 14 and 3 <= c <= 16): t = ("S", T(water[5]))
                else:
                    h = hsh(c, r)
                    t = ("S", T(water[0])) if h < 6 else (("P", 0) if h < 8 else ("P", 1))
            cells[(r, c)] = t; pals[(r, c)] = p

    # resident tiles in order of first use; the HUD icon first; the streamed slots at BG id STREAM_ID0
    statics = [("hud", T(hud))]
    for r in range(1, 18):
        for c in range(20):
            k, v = cells[(r, c)]
            if k == "S" and ("S", v) not in [("S", s[1]) for s in statics]:
                statics.append(("S", v))
    stream_at = STREAM_ID0 - BG0                            # slot offset of the roll tiles (4), then the ripple tiles (2)
    layout = []                                             # offset -> bytes
    it = iter(statics)
    while len(layout) < stream_at:
        layout.append(next(it)[1])
    roll_at, rip_at = len(layout), len(layout) + 4
    layout += list(body[0]) + [rip[0][0], rip[0][1]]
    layout += [s[1] for s in it]
    off_of = {}
    for i, b in enumerate(layout):
        if i < roll_at or i >= rip_at + 2:
            off_of.setdefault(b, i)
    hud_off = off_of[T(hud)]
    tmap, amap = [], []
    for r in range(1, 18):
        for c in range(20):
            k, v = cells[(r, c)]
            tmap.append(off_of[v] if k == "S" else (roll_at + v if k == "R" else rip_at + v))
            amap.append(pals[(r, c)])
    n_bg = len(layout)

    # ---- the check: the proposal's unique-tile count for look A was 53 over all roll / ripple states (51 with flips folded)
    # (here: resident + 4 roll slots x 4 frames + 2 ripple slots x 2 frames)
    all_pix = set(layout) | {b for p in body for b in p} | {b for f in rip for b in f}

    # ---- OBJ: 8x16 entries (top tile, bottom tile), deduplicated; entry e is tile 2e from OBJ base
    ents = []

    def entry(f, ex, ey):
        e = tuple(tile_bytes(f, ex, ey) + (tile_bytes(f, ex, ey + 8)))
        if e not in ents:
            ents.append(e)
        return ents.index(e)

    pose_e = []
    for f in spig:
        fp = f + ["........................"] * 8        # padded to 24x32
        pose_e.append([entry(fp, 8 * c, 16 * r) for r in range(2) for c in range(3)])
    drop_e = [entry(f + ["........"] * (16 - len(f)), 0, 0) for f in drops]
    marker_e = entry(marker, 0, 0)
    obj = [b for e in ents for b in e]
    n_ent = len(ents)

    # the 8-bit tile numbers of an entry e: SLOT_ENTRIES entries in OBJ ids 56-91 (the mug / crash frames, restored by
    # the level load), the rest from the first even id above the BG tiles (src/lr.c)
    pal_bg = [rgb15(BG_PALS[k]) for k in (2, 3, 5, 6, 7)]
    pal_obj = [rgb15(OBJ_PALS[k]) for k in (1, 2)]
    lines = [
        "// generated by tools/gen_lr.py from assets/art/logroll/*.txt -- do not edit; #included by src/lr.c (its bank)",
        f"#define LR_BG_TILES {n_bg}   // from MG_GAME_BG: the resident tiles, the 4 roll slots, the 2 ripple slots",
        f"#define LR_ROLL_AT {roll_at}   // the log's 4 body tiles (Xtop, Xbottom, Ytop, Ybottom), 64 B a frame",
        f"#define LR_RIP_AT {rip_at}   // the 2 ripple tiles (A, B), 32 B a frame",
        f"#define LRB_HUD {hud_off}   // the HUD falls icon",
        f"#define LR_ENTRIES {n_ent}   // OBJ entries (2 tiles each)",
        f"#define LR_SLOT_ENTRIES {SLOT_ENTRIES}",
        f"#define LRO_MARKER {marker_e}",
        "// the map (rows 1-17, 20 columns), BG tile offsets from MG_GAME_BG, and its CGB palettes",
        carr("lr_map", tmap), carr("lr_attr", amap),
        carr("lr_bg_tiles", [b for t in layout for b in t]),
        "// the streamed frames: the log's body tiles per roll frame, the ripple tiles per ripple frame",
        carr("lr_roll", [b for p in body for t in p for b in t]),
        carr("lr_rip", [b for f in rip for t in f for b in t]),
        carr("lr_obj_tiles", obj),
        "// OBJ entry numbers: the six poses x (top row L M R, bottom row L M R); the four droplets",
        carr("lr_pose_e", [e for p in pose_e for e in p]),
        carr("lr_drop_e", drop_e),
        "// CGB palettes: BG 2 3 5 6 7 (forest, river, log, meter, bank); OBJ 1 2 (droplets, marker)",
        carr("lr_pal_bg", [c for p in pal_bg for c in p], "uint16_t"),
        carr("lr_pal_obj", [c for p in pal_obj for c in p], "uint16_t"), ""]
    (outdir / "lr_art.h").write_text("\n".join(lines))
    (outdir / "lr.json").write_text(json.dumps({
        "bg": [b for t in layout for b in t], "roll": [[list(t) for t in p] for p in body],
        "rip": [[list(t) for t in f] for f in rip], "map": tmap, "attr": amap, "roll_at": roll_at, "rip_at": rip_at,
        "n_bg": n_bg, "hud": hud_off, "obj": obj, "n_ent": n_ent, "pose_e": pose_e, "drop_e": drop_e,
        "marker_e": marker_e, "pal_bg": pal_bg, "pal_obj": pal_obj, "slot_entries": SLOT_ENTRIES,
        "distinct_pixel_tiles": len(all_pix)}))
    # x8 previews
    png([forest], prev / "lr_forest_x8.png", 8)
    png(bank + water, prev / "lr_bank_water_x8.png", 8)
    png(log[:4] + [log[4 + 4 * p + i] for p in range(4) for i in (0, 1)], prev / "lr_log_x8.png", 8)
    png(meter + [hud], prev / "lr_meter_hud_x8.png", 8)
    png(spig, prev / "lr_spigoteer_x8.png", 8, transparent=True)
    png(drops + [marker], prev / "lr_droplets_marker_x8.png", 8, transparent=True)


if __name__ == "__main__":
    main()
