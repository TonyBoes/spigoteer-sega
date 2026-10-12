#!/usr/bin/env python3
"""Mini-game framework art -> build/mg_art.h (src/mg.c's bank), build/mg_stub_art.h (src/mg_stub.c's bank),
build/mg.json (tests) and x8 previews in out/preview/.

  assets/art/mg_medal.txt   the result window's medal icon: 3 frames of 32x32 (GOLD, SILVER, BRONZE), BG tiles (approved)
  assets/art/mg_lamp.txt    the stub mini-game's lamp: 2 frames of 16x16 (RED, GREEN), BG tiles (a placeholder)
  assets/art/quickdraw/*.txt  Quick Draw (src/qd.c, docs/minigames_bosses.md 4.1; approved 2026-10-11) -> build/qd_art.h:
      BG: sign_parts (12 tiles 8x8: the frame, FACE, BACK, PIP_ON, PIP_OFF), sign_letters (16x16: D R A W, the left
      half of '!', badge A, badge B, badge B for DMG: inverted) and the story font's '.' (assets/tiles/story.txt @glyph_period);
      OBJ (8x16 entries): spig (2 frames 16x24, padded to 16x32 as bartender.txt: TL, TR, BL, BR entries), kid (3 frames,
      the same), tumbleweed (2 frames 16x16: left, right entries), crow (2 frames 8x16); the soda duel (approved
      2026-10-11): shake_bodies (the Kid's STAND BR entry and the Spigoteer's STAND BL entry without the holstered
      bottle: 2 tiles each), shake_bottle (5 frames 8x16), aim_bottle (2 frames 16x16), wet (3 frames 16x16) and the
      stream (5 BG tiles 8x8 in the same run: OBJ ids 128+ are BG ids too).

Each frame becomes its 8x8 BG tiles row-major: 16 for a 32x32 medal (4x4), 4 for a 16x16 lamp (TL, TR, BL, BR).
Usage: gen_mg.py outdir previewdir
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_art import blocks, png, tile_bytes  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def frames(path, n, size):
    fr = [r for _, r in blocks(path)]
    if len(fr) != n or not all(len(f) == size and all(len(r) == size and set(r) <= set(".-+#") for r in f) for f in fr):
        sys.exit(f"gen_mg: {path.relative_to(ROOT)}: needs {n} frames of {size}x{size} in . - + #")
    return fr


def bg_tiles(fr):
    out = []
    for f in fr:
        for ty in range(0, len(f), 8):
            for tx in range(0, len(f), 8):
                out += tile_bytes(f, tx, ty)
    return out


QD = ROOT / "assets/art/quickdraw"


def qd_frames(name, n, w, h):
    fr = [r for _, r in blocks(QD / f"{name}.txt")]
    if len(fr) != n or not all(len(f) == h and all(len(r) == w and set(r) <= set(".-+#") for r in f) for f in fr):
        sys.exit(f"gen_mg: assets/art/quickdraw/{name}.txt: needs {n} frames of {w}x{h} in . - + #")
    return fr


def obj_tiles(fr):
    """Frames -> 8x16 OBJ entries (top tile, bottom tile), entries row-major (16x32: TL, TR, BL, BR)."""
    out = []
    for f in fr:
        w = len(f[0])
        f = f + ["." * w] * ((-len(f)) % 16)
        for ey in range(0, len(f), 16):
            for ex in range(0, w, 8):
                out += tile_bytes(f, ex, ey) + tile_bytes(f, ex, ey + 8)
    return out


def quickdraw(outdir, prev):
    parts = qd_frames("sign_parts", 12, 8, 8)
    letters = qd_frames("sign_letters", 8, 16, 16)
    spig = qd_frames("spig", 2, 16, 24)
    kid = qd_frames("kid", 3, 16, 24)
    tw = qd_frames("tumbleweed", 2, 16, 16)
    crow = qd_frames("crow", 2, 8, 16)
    # the soda duel: only the changed entry of each STAND body is stored (the rest must be STAND's own)
    bodies = qd_frames("shake_bodies", 2, 16, 24)
    kb, sb = obj_tiles([bodies[0]]), obj_tiles([bodies[1]])
    ks, ss = obj_tiles([kid[0]]), obj_tiles([spig[0]])
    if kb[:96] != ks[:96] or sb[:64] != ss[:64] or sb[96:] != ss[96:]:
        sys.exit("gen_mg: shake_bodies.txt: only the Kid's BR entry and the Spigoteer's BL entry may differ from STAND")
    shake = qd_frames("shake_bottle", 5, 8, 16)
    aim = qd_frames("aim_bottle", 2, 16, 16)
    wet = qd_frames("wet", 3, 16, 16)
    stream = qd_frames("stream", 5, 8, 8)
    soda = kb[96:128] + sb[64:96] + obj_tiles(shake) + obj_tiles(aim) + obj_tiles(wet)
    n_soda_obj = len(soda) // 16
    for f in stream:
        soda += tile_bytes(f, 0, 0)
    period = dict(blocks(ROOT / "assets/tiles/story.txt", named=True))["glyph_period"]
    bg = []
    for f in parts:
        bg += tile_bytes(f, 0, 0)
    for k in (0, 1, 2, 3, 5, 6):                 # D R A W, badge A, badge B: TL, TR, BL, BR
        bg += bg_tiles([letters[k]])
    bg += tile_bytes(letters[4], 0, 0) + tile_bytes(letters[4], 0, 8)   # '!': its left column (the right is FACE)
    bg += tile_bytes(period, 0, 0)
    bg += bg_tiles([letters[7]])                 # badge B on DMG: a light disc (the CGB's B is frame 6 in palette 3)
    # three runs (src/qd.c loads them where a level load puts the game's own tiles back; OBJ 92-95, the coin, is loaded
    # once at boot and must stay): the Spigoteer + tumbleweed (OBJ 56..87), the Kid (96..127), the crow + the soda duel
    # (164..206)
    obj = obj_tiles(spig) + obj_tiles(tw) + obj_tiles(kid) + obj_tiles(crow) + soda
    n_spig, n_tw, n_kid, n_crow = 2 * 8, 2 * 4, 3 * 8, 2 * 2
    (outdir / "qd_art.h").write_text("\n".join([
        "// generated by tools/gen_mg.py from assets/art/quickdraw/*.txt -- do not edit; #included by src/qd.c (its bank)",
        f"#define QD_BG_TILES {len(bg) // 16}   // from QD_BG: 12 sign parts, D R A W, badge A, badge B (4 each), '!' (2), '.', badge B for DMG (4)",
        "#define QDB_FRAME 0      // the frame: TL T TR L R BL B BR",
        "#define QDB_FACE 8", "#define QDB_BACK 9", "#define QDB_PIP_ON 10", "#define QDB_PIP_OFF 11",
        "#define QDB_LETTERS 12   // D R A W: 4 tiles each (TL, TR, BL, BR)",
        "#define QDB_BADGE 28     // badge A, then badge B: 4 tiles each",
        "#define QDB_BANG 36      // '!': top, bottom", "#define QDB_PERIOD 38",
        "#define QDB_BADGE_DMG 39 // badge B on DMG: inverted (light disc, dark letter); the CGB uses badge B in BG palette 3",
        f"#define QD_OBJ_TILES {len(obj) // 16}   // the Spigoteer's poses, tumbleweed, the Kid, crow, the soda duel",
        "#define QDO_SPIG 0       // 2 frames x 8 (STAND, DRAW)",
        f"#define QDO_TW {n_spig}       // 2 frames x 4 (left entry, right entry)",
        f"#define QDO_RUN_A {n_spig + n_tw}    // tiles in the first run (the Spigoteer, the tumbleweed)",
        f"#define QDO_KID {n_spig + n_tw}      // 3 frames x 8 (STAND, DRAW, CHEER): the second run",
        f"#define QDO_KID_N {n_kid}",
        f"#define QDO_CROW {n_spig + n_tw + n_kid}     // 2 frames x 2 (PERCHED, CAW): the third run's start",
        f"#define QDO_CROW_N {n_crow}",
        f"#define QDO_RUN_C {n_crow + len(soda) // 16}    // tiles in the third run (the crow, the soda duel)",
        "// the soda duel, from the crow's end (QDO_CROW + QDO_CROW_N): OBJ 8x16 pieces, then the stream's BG tiles",
        "#define QDS_KID_BR 0     // the Kid's STAND BR entry without the holstered bottle",
        "#define QDS_SPIG_BL 2    // the Spigoteer's STAND BL entry without the hand and holster",
        "#define QDS_BOT 4        // the bottle in a fist: 5 frames x 2 (STILL, UP, DOWN, FIZZ, FOAM)",
        "#define QDS_AIM 14       // the aimed bottle: 2 frames x 4 (left entry, right entry)",
        "#define QDS_WET 22       // the wet overlay: 3 frames x 4 (SPLASH, DRIP A, DRIP B)",
        f"#define QDS_STREAM {n_soda_obj}   // BG: MID A, MID B, HEAD R, HEAD L, RISE R",
        carr("qd_bg_tiles", bg), carr("qd_obj_tiles", obj), ""]))
    png(spig + kid, prev / "qd_duelists_x8.png", 8, transparent=True)
    png(crow, prev / "qd_crow_x8.png", 8, transparent=True)
    png(bodies, prev / "qd_shake_bodies_x8.png", 8, transparent=True)
    png(shake, prev / "qd_shake_bottle_x8.png", 8, transparent=True)
    png(aim, prev / "qd_aim_bottle_x8.png", 8, transparent=True)
    png(wet, prev / "qd_wet_x8.png", 8, transparent=True)
    png(stream, prev / "qd_stream_x8.png", 8)
    png(tw, prev / "qd_tumbleweed_x8.png", 8, transparent=True)
    png(letters, prev / "qd_sign_x8.png", 8)
    png(parts, prev / "qd_sign_parts_x8.png", 8)
    return {"qd_bg": bg, "qd_obj": obj}


def carr(name, data):
    return f"static const uint8_t {name}[{len(data)}] = {{ " + ", ".join(f"0x{b:02X}" for b in data) + " };"


def main():
    outdir, prev = Path(sys.argv[1]), Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True); prev.mkdir(parents=True, exist_ok=True)
    medal = frames(ROOT / "assets/art/mg_medal.txt", 3, 32)
    lamp = frames(ROOT / "assets/art/mg_lamp.txt", 2, 16)
    mt, lt = bg_tiles(medal), bg_tiles(lamp)
    (outdir / "mg_art.h").write_text("\n".join([
        "// generated by tools/gen_mg.py from assets/art/mg_medal.txt -- do not edit; #included by src/mg.c (its bank)",
        f"#define MG_ICON_TILES {len(mt) // 16}   // GOLD, SILVER, BRONZE: 16 tiles each (4x4, row-major)",
        carr("medal_tiles", mt), ""]))
    (outdir / "mg_stub_art.h").write_text("\n".join([
        "// generated by tools/gen_mg.py from assets/art/mg_lamp.txt -- do not edit; #included by src/mg_stub.c (its bank)",
        f"#define LAMP_TILES {len(lt) // 16}   // RED, GREEN: 4 tiles each (TL, TR, BL, BR)",
        carr("lamp_tiles", lt), ""]))
    qd = quickdraw(outdir, prev)
    (outdir / "mg.json").write_text(json.dumps({"medal": mt, "lamp": lt, "medal_art": medal, "lamp_art": lamp, **qd}))
    png(medal, prev / "mg_medal_x8.png", 8)
    png(lamp, prev / "mg_lamp_x8.png", 8)


if __name__ == "__main__":
    main()
