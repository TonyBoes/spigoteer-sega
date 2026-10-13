#!/usr/bin/env python3
"""Monkey Business art (src/mk.c, docs/minigames_bosses.md 4.9; approved by the owner 2026-10-12: the proposal's reading 1 with
G1, "looks good, green boxes": A's wood counter and floor below, B's awning, the pips HUD and the barrel pile above, the
crates in leafy green) -> build/mk_art.h (src/mk.c's bank), build/mk.json (tests) and x8 previews out/preview/mk_*_x8.png.

  assets/art/monkey/band.txt       BG: the awning band, rows 1-4, 160x32, palette 5 (colour 0 = the zoo's wall)
  assets/art/monkey/pips.txt       BG: the HUD coconut pips, 2 tiles 8x8: full, empty
  assets/art/monkey/pile.txt       BG: Kiki's coconut pile 32x24, 6 states (8, 6, 4, 2, 1, 0 coconuts), palette 3
  assets/art/monkey/crates.txt     BG: the crate 16x16, 4 frames (closed, rattle 1, rattle 2, open), palette 2
  assets/art/monkey/counter.txt    BG: the wood counter, 3 tiles 8x8 (top, front a, front b), palette 6
  assets/art/monkey/monkey.txt     OBJ: the monkey 16x16: peek, run, run
  assets/art/monkey/monkey_up.txt  OBJ: the monkey bust 16x16
  assets/art/monkey/parrot.txt     OBJ: the parrot 16x16: peek, perch, wings up, wings down
  assets/art/monkey/duster.txt     OBJ: the feather duster 8x32 (2 entries 8x16): up, swing left, swing right
  assets/art/monkey/puff.txt       OBJ: the shoo puff 8x16, 2 frames

OBJ entries (8x16: top tile, bottom tile) are deduplicated across the sprites and put at OBJ tile ids 56.. (18 entries up to 91),
the rest from 96 (the coin at 92-95 is loaded once at boot); an entry with no pixels is 0xFF (not drawn).

Usage: gen_mk.py outdir previewdir
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_art import blocks, png, tile_bytes  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "assets/art/monkey"
HEADER = "; Art: approved design (owner 2026-10-12)"
OBJ_A, OBJ_A_ENTRIES, OBJ_B = 56, 18, 96


def frames(name, n, w, h):
    path = ART / f"{name}.txt"
    if not path.read_text().startswith(HEADER):
        sys.exit(f"gen_mk: assets/art/monkey/{name}.txt: the first line must start with '{HEADER}'")
    fr = [r for _, r in blocks(path)]
    if len(fr) != n or not all(len(f) == h and all(len(r) == w and set(r) <= set(".-+#") for r in f) for f in fr):
        sys.exit(f"gen_mk: assets/art/monkey/{name}.txt: needs {n} frames of {w}x{h} in . - + #")
    return fr


def carr(name, data, typ="uint8_t"):
    return f"static const {typ} {name}[{len(data)}] = {{ " + ", ".join(f"0x{b:02X}" for b in data) + " };"


def main():
    outdir, prev = Path(sys.argv[1]), Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True)
    prev.mkdir(parents=True, exist_ok=True)
    band = frames("band", 1, 160, 32)[0]
    pips = frames("pips", 2, 8, 8)
    pile = frames("pile", 6, 32, 24)
    crates = frames("crates", 4, 16, 16)
    counter = frames("counter", 3, 8, 8)
    monkey = frames("monkey", 3, 16, 16)
    mup = frames("monkey_up", 1, 16, 16)
    parrot = frames("parrot", 4, 16, 16)
    duster = frames("duster", 3, 8, 32)
    puff = frames("puff", 2, 8, 16)

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

    def tiles_of(f, w, h):
        return [tile_bytes(f, tx, ty) for ty in range(0, h, 8) for tx in range(0, w, 8)]

    band_idx, n_band = group("band", tiles_of(band, 160, 32))
    group("pips", [tile_bytes(f, 0, 0) for f in pips])
    pile_idx, n_pile = group("pile", [t for f in pile for t in tiles_of(f, 32, 24)])
    crate_idx, n_crate = group("crate", [t for f in crates for t in tiles_of(f, 16, 16)])
    group("counter", [tile_bytes(f, 0, 0) for f in counter])
    n_bg = len(bg) // 16

    ents, ent_id, n_raw = [], {}, 0

    def entry(f, ex, ey=0):
        nonlocal n_raw
        n_raw += 1
        e = tuple(tile_bytes(f, ex, ey) + tile_bytes(f, ex, ey + 8))
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

    # 16x16 sprites: left and right entries (SP_PEEK, SP_RUN0, SP_RUN1, SP_UP, SP_PPEEK, SP_PERCH, SP_FLAP0, SP_FLAP1)
    sprites = monkey + mup + parrot
    spr = [(entry(f, 0), entry(f, 8)) for f in sprites]
    dust = [(entry(f, 0, 0), entry(f, 0, 16)) for f in duster]      # top, bottom entry of the 8x32
    puf = [entry(f, 0) for f in puff]
    a_n = min(len(ents), OBJ_A_ENTRIES)
    obj_a = [b for e in ents[:a_n] for b in e]
    obj_b = [b for e in ents[a_n:] for b in e]
    if len(ents) - a_n > (127 - OBJ_B + 1) // 2:
        sys.exit("gen_mk: too many OBJ entries")
    sprid = [[obj_id(x) for x in p] for p in spr]
    dustid = [[obj_id(x) for x in p] for p in dust]
    pufid = [obj_id(x) for x in puf]

    lines = [
        "// generated by tools/gen_mk.py from assets/art/monkey/*.txt -- do not edit; #included by src/mk.c (its bank)",
        f"#define MK_BG_TILES {n_bg}   // from MK_BG: the groups below, each deduplicated",
        f"#define MKB_BAND {off['band']}      // {n_band} tiles (mk_band_map: the 4x20 map as indexes)",
        f"#define MKB_PIPS {off['pips']}      // full, empty",
        f"#define MKB_PILE {off['pile']}      // {n_pile} tiles (mk_pile_map: 6 states x 4x3 as indexes)",
        f"#define MKB_CRATE {off['crate']}     // {n_crate} tiles (mk_crate_map: 4 frames x TL TR BL BR as indexes)",
        f"#define MKB_COUNTER {off['counter']}   // top, front a, front b",
        f"#define MK_OBJ_A {OBJ_A}   // OBJ tile id of the first block: MK_OBJ_A_TILES tiles",
        f"#define MK_OBJ_A_TILES {len(obj_a) // 16}",
        f"#define MK_OBJ_B {OBJ_B}   // the second block: MK_OBJ_B_TILES tiles",
        f"#define MK_OBJ_B_TILES {len(obj_b) // 16}",
        "enum { MKS_PEEK, MKS_RUN0, MKS_RUN1, MKS_UP, MKS_PPEEK, MKS_PERCH, MKS_FLAP0, MKS_FLAP1 };   // mk_spr rows",
        carr("mk_band_map", band_idx), carr("mk_pile_map", pile_idx), carr("mk_crate_map", crate_idx),
        carr("mk_spr", [x for p in sprid for x in p]),
        carr("mk_duster", [x for p in dustid for x in p]),
        carr("mk_puff", pufid),
        carr("mk_bg_tiles", bg), carr("mk_obj_a_tiles", obj_a), carr("mk_obj_b_tiles", obj_b or [0]), ""]
    (outdir / "mk_art.h").write_text("\n".join(lines))
    (outdir / "mk.json").write_text(json.dumps({
        "bg": bg, "obj_a": obj_a, "obj_b": obj_b, "off": off, "n_bg": n_bg, "band_map": band_idx, "pile_map": pile_idx,
        "crate_map": crate_idx, "spr": sprid, "duster": dustid, "puff": pufid, "n_entries": len(ents), "n_raw_entries": n_raw}))
    png([band], prev / "mk_band_x4.png", 4)
    png(pips + counter, prev / "mk_tiles_x8.png", 8)
    png(pile + crates, prev / "mk_pile_crates_x8.png", 8)
    png(monkey + mup + parrot + duster + puff, prev / "mk_sprites_x8.png", 8, transparent=True)
    print(f"gen_mk: {n_bg} BG tiles, {len(ents)} OBJ entries")


if __name__ == "__main__":
    main()
