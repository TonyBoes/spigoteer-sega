#!/usr/bin/env python3
"""Taiko Pour art and chart (src/tk.c, docs/minigames_bosses.md 4.7; look B "sakura stream", approved by the owner
2026-10-12) -> build/tk_art.h (src/tk.c's bank), build/tk.json (tests) and x8 previews out/preview/tk_*_x8.png.

  assets/art/taiko/band.txt    BG: the shoji window and its branch, rows 1-4, 160x32, 2 frames (the lantern flickers: 2x2 tiles)
  assets/art/taiko/lane.txt    BG: the water lane, 2 tiles 8x8 (top row, bottom row of a lane)
  assets/art/taiko/rails.txt   BG: the stone banks, 2 tiles: dim, lit (the beat flash swaps the tile's data)
  assets/art/taiko/marks.txt   BG: the hit marks A and B, 2 frames 16x16
  assets/art/taiko/blind.txt   BG: the bamboo blind, rows 12-13, 2 tiles: top, bottom
  assets/art/taiko/cup.txt     BG: the matcha bowl, 5 fill states 16x16 (empty .. full)
  assets/art/taiko/hud.txt     BG: the HUD's combo and cups icons, 2 tiles
  assets/art/taiko/notes.txt   OBJ: DON, KA, 8x16 each
  assets/art/taiko/flash.txt   OBJ: the hit flashes PERFECT, GOOD, 16x16 (2 entries each)
  assets/art/taiko/teapot.txt  OBJ: the teapot, 3 tilts (level, tilt, pour) 16x16
  assets/art/taiko/stream.txt  OBJ: the tea stream, 2 frames 8x16;  steam.txt: 2 frames;  spill.txt: 2 frames
  tools/taiko_chart.py         the chart: [(hit time in music frames, lane)] -> tk_chart (time | lane << 15)

Each BG group is deduplicated within itself (a tile's palette is the group's); OBJ entries (8x16: top tile, bottom tile) are
deduplicated across the sprites. Usage: gen_tk.py outdir previewdir
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_art import blocks, png, tile_bytes  # noqa: E402
import taiko_chart  # noqa: E402

CHART_LEVEL = "normal"       # taiko_chart.GRIDS: NORMAL's chart (tk_chart, build/tk.json); HARD's and EASY's are built in too (tk_chart_h, tk_chart_e)

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "assets/art/taiko"
HEADER = "; Art: approved design (owner 2026-10-12)"


def frames(name, n, w, h):
    path = ART / f"{name}.txt"
    if not path.read_text().startswith(HEADER):
        sys.exit(f"gen_tk: assets/art/taiko/{name}.txt: the first line must start with '{HEADER}'")
    fr = [r for _, r in blocks(path)]
    if len(fr) != n or not all(len(f) == h and all(len(r) == w and set(r) <= set(".-+#") for r in f) for f in fr):
        sys.exit(f"gen_tk: assets/art/taiko/{name}.txt: needs {n} frames of {w}x{h} in . - + #")
    return fr


def carr(name, data, typ="uint8_t"):
    return f"static const {typ} {name}[{len(data)}] = {{ " + ", ".join(f"0x{b:02X}" for b in data) + " };"


def main():
    outdir, prev = Path(sys.argv[1]), Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True)
    prev.mkdir(parents=True, exist_ok=True)
    band = frames("band", 2, 160, 32)
    lane = frames("lane", 2, 8, 8)
    rails = frames("rails", 2, 8, 8)
    marks = frames("marks", 2, 16, 16)
    blind = frames("blind", 2, 8, 8)
    cup = frames("cup", 5, 16, 16)
    hud = frames("hud", 2, 8, 8)
    notes = frames("notes", 2, 8, 16)
    flash = frames("flash", 2, 16, 16)
    pot = frames("teapot", 3, 16, 16)
    stream = frames("stream", 2, 8, 16)
    steam = frames("steam", 2, 8, 16)
    spill = frames("spill", 2, 8, 16)

    bg, off = [], {}

    def group(name, tiles):
        """Deduplicated tiles of one group -> indexes (from the group's start)."""
        uniq, idx = [], []
        for t in tiles:
            t = tuple(t)
            if t not in uniq:
                uniq.append(t)
            idx.append(uniq.index(t))
        off[name] = len(bg) // 16
        for t in uniq:
            bg.extend(t)
        return idx, len(uniq)

    def tiles16(f):
        return [tile_bytes(f, tx, ty) for ty in (0, 8) for tx in (0, 8)]     # TL TR BL BR

    # the band: frame 0's 4x20 tiles, frame 1's differ in a 2x2 patch (the lantern)
    t0 = [tile_bytes(band[0], tx * 8, ty * 8) for ty in range(4) for tx in range(20)]
    t1 = [tile_bytes(band[1], tx * 8, ty * 8) for ty in range(4) for tx in range(20)]
    changed = [i for i in range(80) if t0[i] != t1[i]]
    ys, xs = sorted({i // 20 for i in changed}), sorted({i % 20 for i in changed})
    if len(changed) != len(ys) * len(xs):
        sys.exit("gen_tk: band.txt: the lantern's changed tiles are not a rectangle")
    band_idx, n_band = group("band", t0 + t1)
    band_map, band_alt = band_idx[:80], band_idx[80:]
    alt = [band_alt[y * 20 + x] for y in ys for x in xs]
    group("hud", [tile_bytes(f, 0, 0) for f in hud])
    group("lane", [tile_bytes(f, 0, 0) for f in lane])
    group("rail", [tile_bytes(f, 0, 0) for f in rails])
    group("mark", [t for f in marks for t in tiles16(f)])            # A: TL TR BL BR, B: TL TR BL BR
    group("blind", [tile_bytes(f, 0, 0) for f in blind])
    cup_idx, n_cup = group("cup", [t for f in cup for t in tiles16(f)])
    n_bg = len(bg) // 16

    ents = []

    def entry(f, ex):
        e = tuple(tile_bytes(f, ex, 0) + tile_bytes(f, ex, 8))
        if e not in ents:
            ents.append(e)
        return 2 * ents.index(e)

    don, ka = entry(notes[0], 0), entry(notes[1], 0)
    fl = [(entry(f, 0), entry(f, 8)) for f in flash]
    pt = [(entry(f, 0), entry(f, 8)) for f in pot]
    sm = [entry(f, 0) for f in stream]
    st = [entry(f, 0) for f in steam]
    sp = [entry(f, 0) for f in spill]
    obj = [b for e in ents for b in e]
    n_obj = len(obj) // 16
    for a, b in fl + pt:                                  # a 16x16's two entries are drawn at x and x + 8: tiles t, t + 2
        if b != a + 2:
            sys.exit("gen_tk: a 16x16 sprite's two 8x16 entries must be adjacent (flash.txt, teapot.txt)")

    chart = taiko_chart.build(CHART_LEVEL)
    cs = taiko_chart.stats(chart)
    chart_h, chart_e = taiko_chart.build("hard"), taiko_chart.build("easy")   # Practice's HARD and EASY (src/tk.c tk_tune)
    lines = [
        "// generated by tools/gen_tk.py from assets/art/taiko/*.txt and tools/taiko_chart.py -- do not edit; #included by src/tk.c",
        f"#define TK_BG_TILES {n_bg}   // from TK_BG: the groups below, each deduplicated",
        f"#define TKB_BAND {off['band']}      // {n_band} tiles (tk_band_map: the 4x20 map as indexes; tk_band_alt: the lantern frame)",
        f"#define TKB_HUD {off['hud']}      // combo icon, cups icon",
        f"#define TKB_LANE {off['lane']}     // top row, bottom row",
        f"#define TKB_RAIL {off['rail']}     // dim, lit (the beat flash swaps this tile's data: tk_rail)",
        f"#define TKB_MARK {off['mark']}     // A: TL TR BL BR, then B",
        f"#define TKB_BLIND {off['blind']}    // top, bottom",
        f"#define TKB_CUP {off['cup']}      // {n_cup} tiles (tk_cup_map: 5 states x TL TR BL BR as indexes)",
        f"#define TK_BAND_ROWS {len(ys)}       // the lantern: {len(ys)} rows x {len(xs)} columns of tiles",
        f"#define TK_LANT_Y {ys[0]}          // the lantern patch's first row within the band (map row 1 + this)",
        f"#define TK_LANT_X {xs[0]}          // and its first column",
        f"#define TK_LANT_W {len(xs)}",
        f"#define TK_OBJ_TILES {n_obj}   // OBJ tiles: {n_obj // 2} 8x16 entries",
        f"#define TKO_DON {don}", f"#define TKO_KA {ka}",
        f"#define TKO_FLASH_P {fl[0][0]}   // PERFECT: left entry; the right is +2",
        f"#define TKO_FLASH_G {fl[1][0]}   // GOOD",
        f"#define TKO_POT_0 {pt[0][0]}    // teapot level; the right entry is +2",
        f"#define TKO_POT_1 {pt[1][0]}    // tilted",
        f"#define TKO_POT_2 {pt[2][0]}    // pouring",
        f"#define TKO_STREAM_0 {sm[0]}", f"#define TKO_STREAM_1 {sm[1]}",
        f"#define TKO_STEAM_0 {st[0]}", f"#define TKO_STEAM_1 {st[1]}",
        f"#define TKO_SPILL_0 {sp[0]}", f"#define TKO_SPILL_1 {sp[1]}",
        f"#define TK_NOTES {len(chart)}   // the chart's notes: tk_chart[i] = hit time (music frames) | lane << 15",
        f"#define TK_CHART_LAST {chart[-1][0]}",
        f"#define TK_NOTES_H {len(chart_h)}   // HARD: the first chart (tools/taiko_chart.py GRID); EASY: GRID_EASY",
        f"#define TK_NOTES_E {len(chart_e)}",
        carr("tk_band_map", band_map), carr("tk_band_alt", alt),
        carr("tk_cup_map", cup_idx),
        carr("tk_chart", [t | (lane << 15) for t, lane in chart], "uint16_t"),
        carr("tk_chart_h", [t | (lane << 15) for t, lane in chart_h], "uint16_t"),
        carr("tk_chart_e", [t | (lane << 15) for t, lane in chart_e], "uint16_t"),
        carr("tk_bg_tiles", bg), carr("tk_obj_tiles", obj), ""]
    (outdir / "tk_art.h").write_text("\n".join(lines))
    (outdir / "tk.json").write_text(json.dumps({
        "bg": bg, "obj": obj, "off": off, "n_bg": n_bg, "n_obj": n_obj, "band_map": band_map, "band_alt": alt,
        "cup_map": cup_idx, "chart": chart, "chart_stats": cs,
        "obj_at": {"don": don, "ka": ka, "flash_p": fl[0][0], "flash_g": fl[1][0], "pot": [p[0] for p in pt],
                   "stream": sm, "steam": st, "spill": sp},
        "lantern": {"y": ys[0], "x": xs[0], "w": len(xs), "h": len(ys)}}))
    png(band, prev / "tk_band_x4.png", 4)
    png(lane + rails + blind + hud, prev / "tk_tiles_x8.png", 8)
    png(marks + cup, prev / "tk_marks_cup_x8.png", 8)
    png(notes + stream + steam + spill, prev / "tk_notes_x8.png", 8, transparent=True)
    png(flash + pot, prev / "tk_flash_pot_x8.png", 8, transparent=True)
    print(f"gen_tk: {n_bg} BG tiles, {n_obj // 2} OBJ entries, {len(chart)} notes; chart {cs}")


if __name__ == "__main__":
    main()
