#!/usr/bin/env python3
"""docs/story.md (the owner-approved script) + assets/story/portraits.json + assets/tiles/story.txt -> story mode data.

  build/story.h            scene / speaker / chapter ids, the cut-scene tile budget, the BANKED accessors
  build/story_data.c       the script (pages, scene table, names), chapter goals, the story font tiles, the picture slots
  build/story_portraits.c  the portraits (BG tiles, map, attributes, palettes, optional OBJ overlay)
  build/story.json         the same for the tests
  out/preview/story_*.png  the font, every portrait (with its frame) and the picture placeholders, x8 / x4

Both .c files are `#pragma bank 255` (autobanked). Their data is static and read only through the BANKED accessors in
the same file, which copy into the caller's WRAM buffer or write VRAM themselves (LCD off): src/story.c never passes a
pointer into its own bank to them.

The script is validated and the build fails on: a line longer than 18 characters, more than 3 lines on a page, a
character outside A-Z 0-9 . , ! ? ' - : and space, an unknown speaker, a scene title longer than 20, a chapter goal that
disagrees with the chapters table, a portrait or scene that does not fit the cut-scene budget (see story.h).
Usage: gen_story.py outdir previewdir
"""
import json
import re
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_art import GREY, IDX, blocks, fmt, rgb15, tile_bytes  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LINE_W, PAGE_LINES = 18, 3
CHARSET = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,!?'-: ")
HUD_CHARSET = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ")     # the play screen's banner has no story font loaded
SPEAKERS = ["SPIGOTEER", "DREGS", "SADIE", "COACH", "JUNE", "COLBY", "AURORA", "MANAGER-BOT", "HANA", "ZIZZ", "KIKI",
            "NARRATOR"]
NARRATOR = SPEAKERS.index("NARRATOR")
PUNCT = {".": "period", ",": "comma", "!": "excl", "?": "quest", "'": "apos", "-": "hyphen", ":": "colon"}

# ---- the cut-scene budget (src/story.c draws to it; see PLAN.md "M11b story engine as built") ----
# BG ids while a cut-scene shows: 0-35 the venue pool (stage + bar), 36-76 the HUD glyphs and panels; the patron range
# and everything above it are free (no patrons on a cut-scene): the story font, then the scene's portraits.
BG_END = 256
MAX_W = MAX_H = 7                # portrait size in tiles (56x56)
MAX_BG_PALS = 3                  # CGB BG palettes 2-4 (0 bar, 1 HUD / text box, 5-6 stage, 7 keg stay the venue's)
MAX_OBJ_PALS = 4                 # CGB OBJ palettes 3-6 (0 the Spigoteer, 1-2 the drinks)
OBJ_TILES = 32                   # OBJ ids of the show performers (OBJ_DANCER.. 127): the overlay tiles, all speakers
MAX_OBJ = 16                     # overlay entries per portrait (OAM 4..)
LINE_OBJ = 8                     # overlay sprites on one line (10 minus the Spigoteer's 2)
MAX_SPK = 3                      # portrait speakers per scene (their tiles are all loaded when the scene starts)
PIC_ROWS = 13                    # picture slot: rows 0-12, above the text box
PIC_POOL = 36                    # its own tiles at BG ids 0.. (no venue on a picture scene)

# goal types / flags (src/story.c)
G_SERVE, G_CATCH, G_CLEAR = 0, 1, 2
F_NO_TAP, F_NO_BREAK = 1, 2
# chapter: scene suffix, venue (theme index), goal, count, flags, timer seconds (0 none), banner lines (HUD glyphs only),
# and the engine column of the chapters table it must agree with
CHAPTERS = [
    ("SALOON", 0, G_SERVE, 15, 0, 0, "SERVE 15 COWBOYS", "", "serve 15"),
    ("STADIUM", 1, G_SERVE, 20, F_NO_TAP, 0, "SERVE 20 FANS", "NOBODY AT YOUR TAP", "serve 20 with no patron reaching"),
    ("LUMBER", 2, G_SERVE, 18, 0, 0, "WAKE UP 18", "SLEEPY LUMBERJACKS", "serve 18"),
    ("BISTRO", 3, G_SERVE, 20, 0, 120, "SERVE 20 CHEFS", "BEFORE THE RUSH", "serve 20 before the timer"),
    ("IGLOO", 4, G_SERVE, 20, 0, 120, "SERVE 20 COCOAS", "BEFORE THEY COOL", "serve 20 before the timer"),
    ("ROBOT", 5, G_CATCH, 25, 0, 0, "RECYCLE 25", "EMPTY BATTERIES", "catch 25 empties"),
    ("TEAHOUSE", 6, G_CLEAR, 0, F_NO_BREAK, 0, "SERVE EVERY GUEST", "NOT ONE BROKEN CUP", "with no broken glass"),
    ("SPACE", 7, G_SERVE, 25, 0, 0, "SERVE 25 GLOWING", "BEAKERS", "serve 25"),
    ("ZOO", 8, G_SERVE, 30, 0, 0, "SERVE 30 ANIMALS", "", "serve 30"),
]
PICTURE_SCENES = ["INTRO", "FINALE", "CREDITS"]


class StoryError(Exception):
    pass


def fail(msg):
    raise StoryError(msg)


# ---- the script --------------------------------------------------------------------------------------------------
def parse_script(path):
    """-> [{"id", "title", "pages": [(speaker, [lines])]}] in the order of docs/story.md."""
    text = path.read_text()
    scenes = []
    for m in re.finditer(r'^### (\w+): "([^"]*)"\n(.*?)(?=^### |^## |\Z)', text, re.S | re.M):
        sid, title, body = m.group(1), m.group(2).upper(), m.group(3)
        code = re.search(r"^```\n(.*?)^```", body, re.S | re.M)
        if not code:
            fail(f"{sid}: no script block")
        pages = []
        for blk in re.split(r"\n\s*\n", code.group(1).strip("\n")):
            lines = [l.rstrip() for l in blk.split("\n")]
            spk, body_lines = lines[0], lines[1:]
            where = f"{sid} page {len(pages) + 1}"
            if spk not in SPEAKERS:
                fail(f"{where}: unknown speaker {spk!r}")
            if not 1 <= len(body_lines) <= PAGE_LINES:
                fail(f"{where}: {len(body_lines)} lines (1-{PAGE_LINES})")
            for l in body_lines:
                if len(l) > LINE_W:
                    fail(f"{where}: {l!r} is {len(l)} characters (max {LINE_W})")
                bad = set(l) - CHARSET
                if bad:
                    fail(f"{where}: {l!r} has characters outside the font: {''.join(sorted(bad))!r}")
            pages.append((SPEAKERS.index(spk), body_lines))
        if len(title) > 20 or set(title) - CHARSET:
            fail(f"{sid}: title {title!r} (max 20, the story charset)")
        scenes.append({"id": sid, "title": title, "pages": pages})
    want = ["INTRO"] + [f"{k}_{c[0]}" for c in CHAPTERS for k in ("PRE", "POST")] + ["FINALE", "CREDITS"]
    if [s["id"] for s in scenes] != want:
        fail(f"scene order {[s['id'] for s in scenes]} != {want}")
    # the chapters table: each chapter's engine goal must match CHAPTERS
    rows = re.findall(r"^\| (\d) \| [^|]+\| [^|]+\| [^|]+\| \"[^\"]*\" / ([^|]+)\|", text, re.M)
    if len(rows) != len(CHAPTERS):
        fail(f"chapters table: {len(rows)} rows")
    for (n, eng), c in zip(rows, CHAPTERS):
        if c[8] not in eng:
            fail(f"chapter {n}: the table says {eng.strip()!r}, gen_story has {c[8]!r}")
        for l in c[6:8]:
            if len(l) > 20 or set(l) - HUD_CHARSET:
                fail(f"chapter {n} banner {l!r}: max 20, A-Z 0-9 and space")
    return scenes


# ---- art --------------------------------------------------------------------------------------------------------
def art_ids(path):
    h = path.read_text()
    return {m.group(1): int(m.group(2)) for m in re.finditer(r"#define (\w+) (\d+)", h)}


def tiles_of(px):
    """px rows (lists of 0..3) whose size is whole tiles -> (list of 16-byte tiles row-major, w, h)."""
    rows = ["".join(".-+#"[v] for v in r) for r in px]
    w, h = len(rows[0]) // 8, len(rows) // 8
    return [tuple(tile_bytes(rows, tx * 8, ty * 8)) for ty in range(h) for tx in range(w)], w, h


def read_art(path):
    rows = [r for _, r in blocks(path)]
    if len(rows) != 1:
        fail(f"{path}: one picture expected")
    px = [[IDX[c] for c in r] for r in rows[0]]
    if len({len(r) for r in px}) != 1 or len(px[0]) % 8 or len(px) % 8:
        fail(f"{path}: not whole 8x8 tiles")
    return px


FONT3 = {   # 3x5 letters for the placeholder name labels
    "A": "010101111101101", "B": "110101110101110", "C": "011100100100011", "D": "110101101101110",
    "E": "111100110100111", "F": "111100110100100", "G": "011100101101011", "H": "101101111101101",
    "I": "111010010010111", "J": "001001001101010", "K": "101101110101101", "L": "100100100100111",
    "M": "101111111101101", "N": "110101101101101", "O": "010101101101010", "P": "110101110100100",
    "Q": "010101101110011", "R": "110101110101101", "S": "011100010001110", "T": "111010010010010",
    "U": "101101101101111", "V": "101101101101010", "W": "101101111111101", "X": "101101010101101",
    "Y": "101101010010010", "Z": "111001010100111", "-": "000000111000000", " ": "000000000000000",
}


def placeholder(label):
    """32x32 BG picture (a silhouette: head and shoulders) + its 32x16 name label overlay (OBJ, '.' transparent)."""
    px = [[1] * 32 for _ in range(32)]
    for y in range(32):
        for x in range(32):
            if (x + y) % 8 == 0:
                px[y][x] = 0                                        # faint diagonal hatching
            head = (x - 15.5) ** 2 + (y - 11.5) ** 2 <= 7.5 ** 2
            body = y >= 20 and ((x - 15.5) / 13.5) ** 2 + ((y - 33) / 12.5) ** 2 <= 1
            if head or body:
                px[y][x] = 3
    for y in range(32):                                             # a rim light on the silhouette's right edge
        for x in range(31, 0, -1):
            if px[y][x] == 3:
                if x < 31 and px[y][x + 1] != 3:
                    px[y][x] = 2
                break
    if len(label) * 4 - 1 > 32:
        fail(f"placeholder label {label!r} is too long (8 characters)")
    lab = [[0] * 32 for _ in range(16)]                             # OBJ colour 0 = transparent
    w = len(label) * 4 - 1
    for y in range(7):
        for x in range(max(0, (32 - w) // 2 - 2), min(32, (32 + w) // 2 + 2)):
            lab[y][x] = 3                                           # the dark tag
    for i, ch in enumerate(label):
        g = FONT3[ch]
        for y in range(5):
            for x in range(3):
                if g[y * 3 + x] == "1":
                    lab[1 + y][(32 - w) // 2 + i * 4 + x] = 1
    return px, lab


def obj_cells(px):
    """overlay px (w x 16k, 0 = transparent) -> [(dx, dy, tile pair)] of the non-empty 8x16 cells."""
    h, w = len(px), len(px[0])
    if w % 8 or h % 16:
        fail("overlay: not whole 8x16 cells")
    rows = ["".join(".-+#"[v] for v in r) for r in px]
    out = []
    for cy in range(0, h, 16):
        for cx in range(0, w, 8):
            if any(px[cy + y][cx + x] for y in range(16) for x in range(8)):
                out.append((cx, cy, tuple(tile_bytes(rows, cx, cy)) + tuple(tile_bytes(rows, cx, cy + 8))))
    return out


def portraits(cfg):
    """speaker -> dict (w, h, x, y, tiles, map, attr, pals, obj, obj_tiles, obj_pals, dmg_obp, px, ovl px)."""
    out = {}
    for si, name in enumerate(SPEAKERS):
        if si == NARRATOR:
            continue
        c = cfg.get(name)
        if c is None:
            fail(f"assets/story/portraits.json: no entry for {name}")
        ovl = c.get("overlay")
        if "art" in c:
            px = read_art(ROOT / c["art"])
            pals = c["palettes"]
            opx = read_art(ROOT / ovl["art"]) if ovl else None
            ox, oy = (ovl["x"], ovl["y"]) if ovl else (0, 0)
            opals = ovl.get("palettes", []) if ovl else []
            obp = ovl.get("dmg_obp", 0) if ovl else 0
        else:
            px, opx = placeholder(c.get("label", name))
            pals = [c["tint"]]
            ox, oy, obp = 0, 24, 0
            opals = [["#000000", "#f8f0d8", "#e0a020", "#181008"]]   # the tag: cream on dark
        tl, w, h = tiles_of(px)
        if w > MAX_W or h > MAX_H:
            fail(f"{name}: portrait {w * 8}x{h * 8} (max {MAX_W * 8}x{MAX_H * 8})")
        x = c.get("x", 2)
        y = c.get("y", 12 - h)
        if x < 1 or x + w > 19 or y < 1 or y + h > 12:
            fail(f"{name}: the frame ({x - 1},{y - 1})..({x + w},{y + h}) leaves rows 0-12 / columns 0-19")
        if not 1 <= len(pals) <= MAX_BG_PALS:
            fail(f"{name}: {len(pals)} BG palettes (1-{MAX_BG_PALS} free while a venue shows)")
        attr = [0] * (w * h)
        if "attr" in c:
            a = c["attr"]
            if len(a) != h or any(len(r) != w for r in a):
                fail(f"{name}: attr must be {h} rows of {w} digits")
            attr = [int(ch) for r in a for ch in r]
            if max(attr) >= len(pals):
                fail(f"{name}: attr names palette {max(attr)} of {len(pals)}")
        uniq, tmap = [], []
        for t in tl:
            if t not in uniq:
                uniq.append(t)
            tmap.append(uniq.index(t))
        obj, otiles = [], []
        if opx is not None:
            for dx, dy, pair in obj_cells(opx):
                if pair not in otiles:
                    otiles.append(pair)
                obj.append((ox + dx, oy + dy, otiles.index(pair) * 2))
            if len(obj) > MAX_OBJ:
                fail(f"{name}: {len(obj)} overlay sprites (max {MAX_OBJ})")
            for line in range(-16, 80):
                n = sum(1 for o in obj if o[1] <= line < o[1] + 16)
                if n > LINE_OBJ:
                    fail(f"{name}: {n} overlay sprites on one line (max {LINE_OBJ}: the Spigoteer takes 2 of 10)")
            if not 1 <= len(opals) <= MAX_OBJ_PALS:
                fail(f"{name}: {len(opals)} overlay palettes (1-{MAX_OBJ_PALS})")
        out[si] = {"name": name, "w": w, "h": h, "x": x, "y": y, "tiles": uniq, "map": tmap, "attr": attr,
                   "pals": pals, "obj": obj, "obj_tiles": otiles, "obj_pals": opals, "dmg_obp": obp,
                   "px": px, "opx": opx, "ox": ox, "oy": oy}
    return out


# ---- output -----------------------------------------------------------------------------------------------------
def carr(name, vals, typ="uint8_t"):
    vals = list(vals)
    body = []
    for i in range(0, len(vals), 20):
        body.append("    " + ", ".join(str(v) for v in vals[i:i + 20]) + ",")
    return f"static const {typ} {name}[{max(1, len(vals))}] = {{\n" + ("\n".join(body) if vals else "    0") + "\n};"


def main():
    outdir, prev = Path(sys.argv[1]), Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True)
    prev.mkdir(parents=True, exist_ok=True)
    ids = art_ids(outdir / "art.h")
    scenes = parse_script(ROOT / "docs/story.md")
    cfg = json.loads((ROOT / "assets/story/portraits.json").read_text())
    ports = portraits(cfg)

    # the story font: punctuation, frame, icon (ids FONT_BASE..), A-Z 0-9 space are the HUD's own tiles
    font_blocks = blocks(ROOT / "assets/tiles/story.txt", named=True)
    font_names = [n for n, _ in font_blocks]
    font = []
    for n, rows in font_blocks:
        if len(rows) != 8 or any(len(r) != 8 for r in rows):
            fail(f"story.txt @{n}: not 8x8")
        font += tile_bytes(rows, 0, 0)
    font_base = ids["BAR_TILE_COUNT"]
    fid = {n: font_base + i for i, n in enumerate(font_names)}
    port_base = font_base + len(font_names)
    budget = BG_END - port_base

    def glyph(ch):
        if ch == " ":
            return ids["TILE_HUD_BLANK"]
        if ch in PUNCT:
            return fid["glyph_" + PUNCT[ch]]
        return ids["TILE_GLYPH_" + ch]

    for sp in ports.values():
        if len(sp["tiles"]) > budget:
            fail(f"{sp['name']}: {len(sp['tiles'])} tiles (budget {budget})")
    # scenes: per scene the portrait speakers; their tiles must fit together
    for s in scenes:
        spk = []
        for p, _ in s["pages"]:
            if p != NARRATOR and p not in spk:
                spk.append(p)
        if len(spk) > MAX_SPK:
            fail(f"{s['id']}: {len(spk)} speakers with portraits (max {MAX_SPK})")
        n = sum(len(ports[p]["tiles"]) for p in spk)
        if n > budget:
            fail(f"{s['id']}: its portraits need {n} BG tiles, {budget} are free")
        no = sum(len(ports[p]["obj_tiles"]) * 2 for p in spk)
        if no > OBJ_TILES:
            fail(f"{s['id']}: its overlays need {no} OBJ tiles, {OBJ_TILES} are free")
        s["spk"] = spk
        s["bg_tiles"] = n
        s["obj_tiles"] = no
        s["venue"] = 255
        s["pic"] = 255
        if s["id"] in PICTURE_SCENES:
            s["pic"] = PICTURE_SCENES.index(s["id"])
        else:
            suffix = s["id"].split("_", 1)[1]
            s["venue"] = next(c[1] for c in CHAPTERS if c[0] == suffix)

    # picture placeholders: the slot for INTRO / FINALE / CREDITS (20 x PIC_ROWS map + attributes; own tiles none yet)
    pics = []
    for sid in PICTURE_SCENES:
        title = next(s["title"] for s in scenes if s["id"] == sid)
        m = [[ids["TILE_HUD_BLANK"]] * 20 for _ in range(PIC_ROWS)]
        m[1][1], m[1][18], m[11][1], m[11][18] = fid["frame_tl"], fid["frame_tr"], fid["frame_bl"], fid["frame_br"]
        for x in range(2, 18):
            m[1][x], m[11][x] = fid["frame_t"], fid["frame_b"]
        for y in range(2, 11):
            m[y][1], m[y][18] = fid["frame_l"], fid["frame_r"]
        m[3][9] = m[3][10] = fid["spigot_icon"]

        def put(y, s):
            x0 = (20 - len(s)) // 2
            for i, ch in enumerate(s):
                m[y][x0 + i] = glyph(ch)
        put(5, title)
        put(7, sid)
        put(9, "PICTURE SLOT")
        pics.append({"id": sid, "tiles": [], "map": [v for r in m for v in r], "attr": [1] * (20 * PIC_ROWS),
                     "pals": []})

    # ---- build/story_data.c ----
    text = []
    scene_ofs = []
    for s in scenes:
        scene_ofs.append(len(text))
        for p, lines in s["pages"]:
            text.append(p)
            for i in range(PAGE_LINES):
                l = lines[i] if i < len(lines) else ""
                text.append(len(l))
                text += [ord(ch) for ch in l]
    names = []
    for n in SPEAKERS:
        names += [ord(ch) for ch in n.ljust(12, "\0")[:12]]
    hdr = []
    for s in scenes:
        spk = s["spk"] + [255] * (MAX_SPK - len(s["spk"]))
        hdr += [s["venue"], s["pic"], len(s["pages"]), len(s["spk"])] + spk + [0]
        hdr += [ord(ch) for ch in s["title"].ljust(21, "\0")]
    SCENE_HDR = 4 + MAX_SPK + 1 + 21
    goals = []
    for i, c in enumerate(CHAPTERS):
        goals += [c[2], c[3], c[4], c[5], 0, 0, 0, 0]        # type, count, flags, seconds, twist (hook), pad
        goals += [ord(ch) for ch in c[6].ljust(21, "\0")] + [ord(ch) for ch in c[7].ljust(21, "\0")]
    GOAL_LEN = 8 + 42

    d = ["// generated by tools/gen_story.py from docs/story.md -- do not edit",
         "#pragma bank 255", "#include <gb/gb.h>", "#include <gb/cgb.h>", "#include <stdint.h>", '#include "story.h"', "",
         "// the script: per page the speaker, then 3 lines of (length, characters)",
         carr("st_text", text), carr("st_scene_ofs", scene_ofs, "uint16_t"),
         "// per scene: venue (255: a picture), picture (255: none), pages, portrait speakers, their ids x3, 0, title",
         carr("st_scene_hdr", hdr), carr("st_names", names),
         "// per chapter: goal type, count, flags, timer seconds, twist (0: none; the twists are a later milestone), pad,",
         "// the two banner lines", carr("st_goals", goals), carr("st_font", font)]
    for i, p in enumerate(pics):
        d += [carr(f"st_pic{i}_map", p["map"]), carr(f"st_pic{i}_attr", p["attr"])]
    d += ["",
          "void story_scene_get(uint8_t s, uint8_t *dst) BANKED {",
          f"    const uint8_t *p = st_scene_hdr + (uint16_t)s * {SCENE_HDR};",
          "    uint8_t i;",
          f"    for (i = 0; i < {SCENE_HDR}; i++) dst[i] = p[i];",
          "}", "",
          "// page p of scene s: dst[0] the speaker, dst[1..54] the three lines padded with spaces",
          "void story_page_get(uint8_t s, uint8_t p, uint8_t *dst) BANKED {",
          "    const uint8_t *q = st_text + st_scene_ofs[s];",
          "    uint8_t i, k, n;",
          "    while (p--) { q++; for (k = 0; k < 3; k++) q += 1 + *q; }",
          "    *dst++ = *q++;",
          "    for (k = 0; k < 3; k++) {",
          "        n = *q++;",
          "        for (i = 0; i < 18; i++) *dst++ = i < n ? q[i] : ' ';",
          "        q += n;",
          "    }",
          "}", "",
          "void story_name_get(uint8_t spk, uint8_t *dst) BANKED {",
          "    const uint8_t *p = st_names + (uint16_t)spk * 12;",
          "    uint8_t i;",
          "    for (i = 0; i < 12; i++) dst[i] = p[i];",
          "}", "",
          "void story_goal_get(uint8_t ch, uint8_t *dst) BANKED {",
          f"    const uint8_t *p = st_goals + (uint16_t)ch * {GOAL_LEN};",
          "    uint8_t i;",
          f"    for (i = 0; i < {GOAL_LEN}; i++) dst[i] = p[i];",
          "}", "",
          "void story_font_load(void) BANKED {           // LCD off",
          f"    set_bkg_data(STORY_FONT_BASE, {len(font_names)}, st_font);",
          "}", "",
          "// the picture slot (LCD off): rows 0..STORY_PIC_ROWS-1; its own tiles (none in the placeholders) at ids 0..",
          "void story_pic_draw(uint8_t pic, uint8_t cgb) BANKED {",
          "    const uint8_t *m, *a;"]
    for i in range(len(pics)):
        d.append(f"    {'if' if i == 0 else 'else if'} (pic == {i}) {{ m = st_pic{i}_map; a = st_pic{i}_attr; }}")
    d += ["    else return;",
          f"    set_bkg_tiles(0, 0, 20, {PIC_ROWS}, m);",
          "    if (cgb) {",
          "        VBK_REG = VBK_BANK_1;",
          f"        set_bkg_tiles(0, 0, 20, {PIC_ROWS}, a);",
          "        VBK_REG = VBK_BANK_0;",
          "    }",
          "}", ""]
    (outdir / "story_data.c").write_text("\n".join(d))

    # ---- build/story_portraits.c ----
    P = ["// generated by tools/gen_story.py from assets/story/portraits.json -- do not edit",
         "#pragma bank 255", "#include <gb/gb.h>", "#include <stdint.h>", '#include "story.h"', ""]
    for si, sp in sorted(ports.items()):
        t = [b for tt in sp["tiles"] for b in tt]
        ot = [b for pair in sp["obj_tiles"] for b in pair]
        pal = [v for p in sp["pals"] for v in rgb15(p)]
        opal = [v for p in sp["obj_pals"] for v in rgb15(p)]
        obj = []
        for ox, oy, tile in sp["obj"]:
            obj += [oy & 255, ox & 255, tile, sp["dmg_obp"] << 4]
        P += [f"// {sp['name']}: {sp['w'] * 8}x{sp['h'] * 8} at tile ({sp['x']},{sp['y']}), {len(sp['tiles'])} tiles, "
              f"{len(sp['pals'])} BG palette(s), {len(sp['obj'])} overlay sprite(s)",
              carr(f"pt{si}_tiles", t), carr(f"pt{si}_otiles", ot)]
        hdr = [sp["w"], sp["h"], sp["x"], sp["y"], len(sp["pals"]), len(sp["tiles"]), len(sp["obj"]), len(sp["obj_pals"]),
               len(sp["obj_tiles"]) * 2]
        body = hdr + sp["map"] + [0] * (49 - len(sp["map"])) + sp["attr"] + [0] * (49 - len(sp["attr"]))
        P += [carr(f"pt{si}_hdr", body), carr(f"pt{si}_pal", pal + [0] * (12 - len(pal)), "uint16_t"),
              carr(f"pt{si}_opal", opal + [0] * (16 - len(opal)), "uint16_t"),
              carr(f"pt{si}_obj", obj + [0] * (MAX_OBJ * 4 - len(obj))), ""]
    sel = [f"    case {si}: h = pt{si}_hdr; p = pt{si}_pal; o = pt{si}_opal; e = pt{si}_obj; break;" for si in sorted(ports)]
    selt = [f"    case {si}: t = pt{si}_tiles; ot = pt{si}_otiles; break;" for si in sorted(ports)]
    P += ["// the portrait of speaker spk into the WRAM struct (w 0: none)",
          "void portrait_get(uint8_t spk, portrait_t *dst) BANKED {",
          "    const uint8_t *h, *e; const uint16_t *p, *o;",
          "    uint8_t i, *d = (uint8_t *)dst;",
          "    switch (spk) {"] + sel + [
          "    default: dst->w = 0; return;",
          "    }",
          "    for (i = 0; i < 9 + 98; i++) d[i] = h[i];",
          "    for (i = 0; i < 12; i++) dst->pal[i] = p[i];",
          "    for (i = 0; i < 16; i++) dst->opal[i] = o[i];",
          f"    for (i = 0; i < {MAX_OBJ * 4}; i++) dst->obj[i] = e[i];",
          "}", "",
          "// LCD off: its BG tiles at bg_first.., its overlay tiles at OBJ obj_first..",
          "void portrait_tiles_load(uint8_t spk, uint8_t bg_first, uint8_t obj_first) BANKED {",
          "    const uint8_t *t, *ot;",
          "    switch (spk) {"] + selt + [
          "    default: return;",
          "    }",
          "    set_bkg_data(bg_first, pt_n[spk], t);",
          "    if (pt_on[spk]) set_sprite_data(obj_first, pt_on[spk], ot);",
          "}", ""]
    nt = [len(ports[i]["tiles"]) if i in ports else 0 for i in range(len(SPEAKERS))]
    no = [len(ports[i]["obj_tiles"]) * 2 if i in ports else 0 for i in range(len(SPEAKERS))]
    P.insert(6, "// tiles per speaker: BG, OBJ (the overlay)")
    P.insert(7, carr("pt_n", nt))
    P.insert(8, carr("pt_on", no))
    (outdir / "story_portraits.c").write_text("\n".join(P))

    # ---- build/story.h ----
    H = ["// generated by tools/gen_story.py -- do not edit", "#ifndef STORY_DATA_H", "#define STORY_DATA_H",
         "#include <gb/gb.h>", "#include <stdint.h>", '#include "art.h"', "",
         f"#define STORY_SCENES {len(scenes)}"]
    for i, s in enumerate(scenes):
        H.append(f"#define SC_{s['id']} {i}")
    H += [f"#define STORY_CHAPTERS {len(CHAPTERS)}   // chapter c: SC_PRE = 1 + 2c, SC_POST = 2 + 2c",
          f"#define SPK_NARRATOR {NARRATOR}", f"#define STORY_SPEAKERS {len(SPEAKERS)}",
          f"#define G_SERVE {G_SERVE}", f"#define G_CATCH {G_CATCH}", f"#define G_CLEAR {G_CLEAR}",
          f"#define F_NO_TAP {F_NO_TAP}", f"#define F_NO_BREAK {F_NO_BREAK}", "",
          "// cut-scene BG tile budget: the story font at BAR_TILE_COUNT.. (the patron range is free: no patrons)",
          f"#define STORY_FONT_BASE BAR_TILE_COUNT", f"#define STORY_FONT_COUNT {len(font_names)}"]
    for n in font_names:
        H.append(f"#define ST_{n.upper()} (STORY_FONT_BASE + {font_names.index(n)})")
    H += [f"#define STORY_PORTRAIT_BASE (STORY_FONT_BASE + STORY_FONT_COUNT)   // the scene's portraits, one after the other",
          f"#define STORY_BG_END {BG_END}", f"#if STORY_PORTRAIT_BASE != {port_base}", "#error story.h out of date", "#endif",
          f"#define STORY_OBJ_TILES {OBJ_TILES}   // overlay tiles: OBJ_DANCER .. +31", f"#define STORY_MAX_OBJ {MAX_OBJ}",
          f"#define STORY_MAX_SPK {MAX_SPK}", f"#define STORY_PIC_ROWS {PIC_ROWS}", "",
          "typedef struct {",
          "    uint8_t w, h, x, y;          // tiles (w 0: no portrait); x, y the picture's top-left screen tile",
          "    uint8_t npal, ntiles, nobj, nobjpal, nobjtiles;",
          "    uint8_t map[49];             // tile index relative to the portrait's first tile, row-major",
          "    uint8_t attr[49];            // BG palette relative to its first slot",
          "    uint16_t pal[12];            // up to 3 BG palettes",
          "    uint16_t opal[16];           // up to 4 overlay OBJ palettes",
          f"    uint8_t obj[{MAX_OBJ * 4}];            // overlay: dy, dx (px from the picture's top-left), tile (relative), flags (bit 4 DMG OBP1)",
          "} portrait_t;",
          "typedef struct {",
          "    uint8_t venue, pic, pages, nspk, spk[3], pad;",
          "    char title[21];",
          "} scene_hdr_t;",
          "typedef struct {",
          "    uint8_t type, count, flags, secs, twist, pad[3];",
          "    char line1[21], line2[21];",
          "} goal_t;",
          "void story_scene_get(uint8_t s, uint8_t *dst) BANKED;   // dst: scene_hdr_t",
          "void story_page_get(uint8_t s, uint8_t p, uint8_t *dst) BANKED;   // dst[55]: speaker, 3 x 18 characters",
          "void story_name_get(uint8_t spk, uint8_t *dst) BANKED;  // dst[12], 0-terminated",
          "void story_goal_get(uint8_t ch, uint8_t *dst) BANKED;   // dst: goal_t",
          "void story_font_load(void) BANKED;",
          "void story_pic_draw(uint8_t pic, uint8_t cgb) BANKED;",
          "void portrait_get(uint8_t spk, portrait_t *dst) BANKED;",
          "void portrait_tiles_load(uint8_t spk, uint8_t bg_first, uint8_t obj_first) BANKED;",
          "#endif", ""]
    (outdir / "story.h").write_text("\n".join(H))

    # ---- build/story.json (tests) ----
    js = {"scenes": [{"id": s["id"], "title": s["title"], "venue": s["venue"], "pic": s["pic"], "spk": s["spk"],
                      "pages": [{"speaker": SPEAKERS[p], "lines": l} for p, l in s["pages"]],
                      "bg_tiles": s["bg_tiles"], "obj_tiles": s["obj_tiles"]} for s in scenes],
          "speakers": SPEAKERS, "font_base": font_base, "font": {n: fid[n] for n in font_names},
          "portrait_base": port_base, "bg_budget": budget, "obj_budget": OBJ_TILES,
          "glyphs": {ch: glyph(ch) for ch in sorted(CHARSET)},
          "chapters": [{"suffix": c[0], "venue": c[1], "type": c[2], "count": c[3], "flags": c[4], "secs": c[5],
                        "line1": c[6], "line2": c[7]} for c in CHAPTERS],
          "portraits": {sp["name"]: {"w": sp["w"], "h": sp["h"], "x": sp["x"], "y": sp["y"], "tiles": len(sp["tiles"]),
                                     "pals": len(sp["pals"]), "obj": len(sp["obj"]), "map": sp["map"]}
                        for sp in ports.values()},
          "pictures": [{"id": p["id"], "map": p["map"]} for p in pics],
          "text_bytes": len(text), "chars": sum(len(l) for s in scenes for _, ls in s["pages"] for l in ls),
          "pages": sum(len(s["pages"]) for s in scenes)}
    (outdir / "story.json").write_text(json.dumps(js, indent=1))

    # ---- previews ----
    im = Image.new("RGB", (len(font_names) * 9, 8), (255, 0, 255))
    for i, (_, rows) in enumerate(font_blocks):
        for y in range(8):
            for x in range(8):
                im.putpixel((i * 9 + x, y), GREY[IDX[rows[y][x]]])
    im.resize((im.width * 8, im.height * 8), Image.NEAREST).save(prev / "story_font_x8.png")
    for si, sp in ports.items():
        w, h = sp["w"] * 8, sp["h"] * 8
        pim = Image.new("RGB", (w + 16, h + 16), (40, 30, 20))
        cols = [tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in sp["pals"][0]]
        for y in range(h):
            for x in range(w):
                t = (y // 8) * sp["w"] + x // 8
                pc = [tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in sp["pals"][sp["attr"][t]]]
                pim.putpixel((x + 8, y + 8), pc[sp["px"][y][x]])
        if sp["opx"] is not None:
            oc = [tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in sp["obj_pals"][0]]
            for y, r in enumerate(sp["opx"]):
                for x, v in enumerate(r):
                    X, Y = x + sp["ox"] + 8, y + sp["oy"] + 8
                    if v and 0 <= X < pim.width and 0 <= Y < pim.height:
                        pim.putpixel((X, Y), oc[v])
        pim.resize((pim.width * 8, pim.height * 8), Image.NEAREST).save(prev / f"story_portrait_{sp['name'].lower()}_x8.png")
    print(f"gen_story: {len(scenes)} scenes, {js['pages']} pages, {js['chars']} characters, script {len(text)} B "
          f"(+ scene table {len(hdr) + 2 * len(scene_ofs)} B, goals {len(goals)} B); portraits "
          f"{sum(len(p['tiles']) for p in ports.values())} tiles; BG budget {budget} tiles from id {port_base}")


if __name__ == "__main__":
    try:
        main()
    except StoryError as e:
        sys.exit(f"gen_story: {e}")
