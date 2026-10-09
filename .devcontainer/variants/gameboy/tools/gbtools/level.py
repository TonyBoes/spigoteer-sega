"""`lvl2gb` — turn a level file into tilemap, collision and entity data, and render it back.

Inputs
  level.txt   ASCII map, one character per 8x8 tile (legend below)
  level.json  Tiled JSON export with layers named `tiles`, `collision`, `entities`
              (collision tileset tiles in the order solid, platform, hazard, ladder;
               entities as objects with a class/type; drawn with the project's own tileset PNG)

    lvl2gb build assets/levels/level1.txt  --format c   --out build/level1      # level1.c + level1.h
    lvl2gb build assets/levels/level1.json --format asm --out build/level1      # level1.asm
    lvl2gb preview assets/levels/level1.txt --tileset build/tiles.png --out out/level1.png
    lvl2gb txt assets/levels/level1.json                                        # Tiled -> ASCII, to read it

Default ASCII legend (override or extend with a sidecar level.legend.json or --legend):
    .  empty      tile 0   collision 0        S  spawn point       (entity 0)
    #  solid      tile 1   collision 1        E  enemy             (entity 1)
    =  platform   tile 2   collision 2        C  collectible       (entity 2)
    ^  hazard     tile 3   collision 3        X  exit              (entity 3)
    H  ladder     tile 4   collision 4
Entities sit on an empty tile. Legend JSON shape:
    {"tiles": {"#": {"tile": 1, "collision": 1}}, "entities": {"E": "enemy"}}

Output arrays are row-major, width*height bytes each, uncompressed. Maps wider or
taller than 32 tiles need column/row streaming in the engine — the header says so.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw

COLLISION_NAMES = ["none", "solid", "platform", "hazard", "ladder"]
DEFAULT_LEGEND = {
    "tiles": {
        ".": {"tile": 0, "collision": 0}, " ": {"tile": 0, "collision": 0},
        "#": {"tile": 1, "collision": 1}, "=": {"tile": 2, "collision": 2},
        "^": {"tile": 3, "collision": 3}, "H": {"tile": 4, "collision": 4},
    },
    "entities": {"S": "spawn", "E": "enemy", "C": "collectible", "X": "exit"},
}
ENTITY_COLOURS = {"spawn": (0, 200, 0), "enemy": (220, 0, 0), "collectible": (240, 200, 0), "exit": (0, 120, 255)}


@dataclass
class Level:
    name: str
    width: int
    height: int
    tiles: list[int]
    collision: list[int]
    entities: list[tuple[str, int, int]]      # (type, col, row)
    entity_types: list[str] = field(default_factory=list)
    source: str = ""

    @property
    def needs_streaming(self) -> bool:
        return self.width > 32 or self.height > 32


def load_legend(src: Path, explicit: str | None) -> dict:
    legend = json.loads(json.dumps(DEFAULT_LEGEND))
    sidecar = src.with_suffix(".legend.json")
    for p in [Path(explicit)] if explicit else ([sidecar] if sidecar.is_file() else []):
        extra = json.loads(p.read_text())
        legend["tiles"].update(extra.get("tiles", {}))
        legend["entities"].update(extra.get("entities", {}))
    return legend


def _ident(stem: str) -> str:
    s = "".join(c if c.isalnum() else "_" for c in stem)
    return s if not s[0].isdigit() else "_" + s


def parse_txt(src: Path, legend: dict) -> Level:
    rows = [ln.rstrip("\n") for ln in src.read_text().splitlines()
            if not ln.lstrip().startswith((";", "//"))]
    rows = [r for r in rows if r.strip() != ""] or sys.exit("empty level")
    width = max(len(r) for r in rows)
    tiles, coll, ents = [], [], []
    for y, r in enumerate(rows):
        r = r.ljust(width, ".")
        for x, ch in enumerate(r):
            if ch in legend["entities"]:
                ents.append((legend["entities"][ch], x, y))
                ch = "."
            t = legend["tiles"].get(ch) or sys.exit(f"{src}:{y+1}:{x+1}: unknown character {ch!r}")
            tiles.append(t["tile"]); coll.append(t["collision"])
    return Level(_ident(src.stem), width, len(rows), tiles, coll, ents,
                 list(dict.fromkeys(legend["entities"].values())), str(src))


def parse_tiled(src: Path, legend: dict) -> Level:
    d = json.loads(src.read_text())
    if d.get("orientation", "orthogonal") != "orthogonal" or d.get("tilewidth") != 8 or d.get("tileheight") != 8:
        sys.exit("Tiled map must be orthogonal with 8x8 tiles")
    w, h = d["width"], d["height"]
    layers = {ly["name"].lower(): ly for ly in d["layers"]}
    tilesets = sorted(d.get("tilesets", []), key=lambda t: t["firstgid"])

    def local(gid):
        gid &= 0x0FFFFFFF  # strip flip bits
        if gid == 0:
            return None, 0
        ts = next((t for t in reversed(tilesets) if t["firstgid"] <= gid), None)
        return ts, gid - ts["firstgid"]

    tl = layers.get("tiles") or sys.exit("no layer named 'tiles'")
    if tl.get("encoding", "csv") != "csv" or "data" not in tl:
        sys.exit("export the tile layers as CSV (uncompressed) JSON")
    tiles = [local(g)[1] for g in tl["data"]]
    coll = [0] * (w * h)
    if "collision" in layers:
        for i, g in enumerate(layers["collision"]["data"]):
            ts, lid = local(g)
            coll[i] = 0 if ts is None else min(lid + 1, len(COLLISION_NAMES) - 1)
    ents = []
    types = list(dict.fromkeys(legend["entities"].values()))
    if "entities" in layers:
        for o in layers["entities"].get("objects", []):
            kind = (o.get("class") or o.get("type") or o.get("name") or "entity").lower()
            if kind not in types:
                types.append(kind)
            x, y = o["x"], o["y"]
            if o.get("gid"):                     # tile objects anchor bottom-left
                y -= o.get("height", 8)
            ents.append((kind, int(x) // 8, int(y) // 8))
    return Level(_ident(src.stem), w, h, tiles, coll, ents, types, str(src))


def load(src: Path, legend_path: str | None) -> Level:
    legend = load_legend(src, legend_path)
    lv = parse_tiled(src, legend) if src.suffix.lower() == ".json" else parse_txt(src, legend)
    return lv


def budgets(lv: Level, cgb: bool) -> list[str]:
    msgs = []
    distinct = len(set(lv.tiles))
    limit = 512 if cgb else 256
    if max(lv.tiles) >= limit:
        msgs.append(f"ERROR: tile id {max(lv.tiles)} exceeds the {limit}-tile VRAM budget")
    if lv.needs_streaming:
        msgs.append(f"note: {lv.width}x{lv.height} exceeds the 32x32 hardware map; the engine must stream columns/rows")
    size = 2 * lv.width * lv.height
    if size > 16384:
        msgs.append(f"ERROR: {size} bytes of map data will not fit one ROM bank (16384); compress or split")
    elif size > 8192:
        msgs.append(f"note: {size} bytes of map data, more than half a bank")
    for kind, x, y in lv.entities:
        if not (0 <= x < lv.width and 0 <= y < lv.height):
            msgs.append(f"ERROR: entity {kind} at ({x},{y}) is outside the map")
    msgs.append(f"{lv.width}x{lv.height} tiles, {distinct} distinct tile ids, {len(lv.entities)} entities")
    return msgs


def _rows(data, width, per_row=None):
    per_row = per_row or width
    return [data[i:i + per_row] for i in range(0, len(data), per_row)]


def emit_c(lv: Level, out: Path):
    N = lv.name.upper()
    h = [f"// generated by lvl2gb from {lv.source} — do not edit", f"#ifndef {N}_H", f"#define {N}_H", "",
         "#ifndef LVL2GB_TYPES", "#define LVL2GB_TYPES",
         "typedef struct { unsigned char type, x, y; } level_entity_t;   // x,y in tiles"]
    h += [f"#define COL_{n.upper()} {i}" for i, n in enumerate(COLLISION_NAMES)]
    h += ["#endif", ""]
    h += [f"#define ENT_{t.upper()} {i}" for i, t in enumerate(lv.entity_types)]
    h += ["", f"#define {N}_WIDTH {lv.width}", f"#define {N}_HEIGHT {lv.height}",
          f"#define {N}_ENTITY_COUNT {len(lv.entities)}",
          f"#define {N}_NEEDS_STREAMING {int(lv.needs_streaming)}",
          f"extern const unsigned char {lv.name}_tiles[{lv.width * lv.height}];",
          f"extern const unsigned char {lv.name}_collision[{lv.width * lv.height}];",
          f"extern const level_entity_t {lv.name}_entities[{max(1, len(lv.entities))}];",
          "", f"#endif // {N}_H", ""]
    c = [f"// generated by lvl2gb from {lv.source} — do not edit", f'#include "{out.name}.h"', ""]
    for arr in ("tiles", "collision"):
        c.append(f"const unsigned char {lv.name}_{arr}[{lv.width * lv.height}] = {{")
        c += ["    " + ",".join(f"{v:3d}" for v in row) + "," for row in _rows(getattr(lv, arr), lv.width)]
        c += ["};", ""]
    c.append(f"const level_entity_t {lv.name}_entities[{max(1, len(lv.entities))}] = {{")
    c += [f"    {{ ENT_{k.upper()}, {x}, {y} }}," for k, x, y in lv.entities] or ["    { 0, 0, 0 },"]
    c += ["};", ""]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".h").write_text("\n".join(h))
    out.with_suffix(".c").write_text("\n".join(c))
    return [out.with_suffix(".h"), out.with_suffix(".c")]


def emit_asm(lv: Level, out: Path, section: str):
    L = "".join(p.capitalize() for p in lv.name.split("_")) or "Level"
    a = [f"; generated by lvl2gb from {lv.source} — do not edit", ""]
    a += [f"DEF {L}Width EQU {lv.width}", f"DEF {L}Height EQU {lv.height}",
          f"DEF {L}EntityCount EQU {len(lv.entities)}",
          f"DEF {L}NeedsStreaming EQU {int(lv.needs_streaming)}",
          f"EXPORT {L}Width, {L}Height, {L}EntityCount, {L}NeedsStreaming", ""]
    a += [f"DEF COL_{n.upper()} EQU {i}" for i, n in enumerate(COLLISION_NAMES)]
    a += [f"DEF ENT_{t.upper()} EQU {i}" for i, t in enumerate(lv.entity_types)]
    a += ["", f'SECTION "{L} data", {section}', ""]
    for arr in ("tiles", "collision"):
        a.append(f"{L}{arr.capitalize()}::")
        a += ["    db " + ",".join(f"${v:02x}" for v in row) for row in _rows(getattr(lv, arr), lv.width)]
        a.append("")
    a.append(f"{L}Entities::   ; db type, x, y (tiles)")
    a += [f"    db ENT_{k.upper()}, {x}, {y}" for k, x, y in lv.entities]
    a.append(f"{L}EntitiesEnd::")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".asm").write_text("\n".join(a) + "\n")
    return [out.with_suffix(".asm")]


def render(lv: Level, tileset: Path | None, scale: int, legend: dict | None = None) -> Image.Image:
    labels = {v: k for k, v in (legend or DEFAULT_LEGEND)["entities"].items()}
    W, H = lv.width * 8, lv.height * 8
    im = Image.new("RGB", (W, H), (255, 255, 255))
    if tileset:
        ts = Image.open(tileset).convert("RGB")
        cols = max(1, ts.width // 8)
        for i, t in enumerate(lv.tiles):
            sx, sy = (t % cols) * 8, (t // cols) * 8
            if sy + 8 <= ts.height:
                im.paste(ts.crop((sx, sy, sx + 8, sy + 8)), ((i % lv.width) * 8, (i // lv.width) * 8))
    else:  # no tileset: draw collision kinds as flat colours
        shade = {0: (255, 255, 255), 1: (40, 40, 40), 2: (120, 120, 120), 3: (200, 60, 60), 4: (90, 90, 200)}
        d = ImageDraw.Draw(im)
        for i, c in enumerate(lv.collision):
            x, y = (i % lv.width) * 8, (i // lv.width) * 8
            d.rectangle((x, y, x + 7, y + 7), fill=shade.get(c, (255, 0, 255)))
    im = im.resize((W * scale, H * scale), Image.NEAREST)
    d = ImageDraw.Draw(im)
    for kind, x, y in lv.entities:
        col = ENTITY_COLOURS.get(kind, (255, 0, 255))
        x0, y0 = x * 8 * scale, y * 8 * scale
        d.rectangle((x0, y0, x0 + 8 * scale - 1, y0 + 8 * scale - 1), outline=col, width=max(1, scale // 2))
        d.text((x0 + 2, y0 + 1), labels.get(kind, kind[0].upper()), fill=col)
    # 32-tile hardware-map guides
    for gx in range(32, lv.width, 32):
        d.line((gx * 8 * scale, 0, gx * 8 * scale, H * scale), fill=(255, 128, 0))
    for gy in range(32, lv.height, 32):
        d.line((0, gy * 8 * scale, W * scale, gy * 8 * scale), fill=(255, 128, 0))
    return im


def to_txt(lv: Level, legend: dict) -> str:
    rev = {}
    for ch, t in legend["tiles"].items():
        rev.setdefault((t["tile"], t["collision"]), ch)
    erev = {v: k for k, v in legend["entities"].items()}
    grid = [[rev.get((lv.tiles[y * lv.width + x], lv.collision[y * lv.width + x]), "?")
             for x in range(lv.width)] for y in range(lv.height)]
    for kind, x, y in lv.entities:
        grid[y][x] = erev.get(kind, "?")
    return "\n".join("".join(r) for r in grid)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="lvl2gb", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("build", "preview", "txt"):
        p = sub.add_parser(name)
        p.add_argument("src")
        p.add_argument("--legend", help="legend JSON (default: <src>.legend.json if present)")
        p.add_argument("--cgb", action="store_true", help="512-tile budget instead of 256")
        if name == "build":
            p.add_argument("--format", choices=["c", "asm"], required=True)
            p.add_argument("--out", required=True, help="output path without extension")
            p.add_argument("--section", default="ROMX", help="asm: section type (ROMX default, or ROM0)")
        if name == "preview":
            p.add_argument("--tileset", help="tileset PNG (8x8 tiles in id order, left-to-right); omit for collision colours")
            p.add_argument("--out", required=True)
            p.add_argument("--scale", type=int, default=4)
    a = ap.parse_args(argv)
    src = Path(a.src)
    if not src.is_file():
        sys.exit(f"no such file: {src}")
    lv = load(src, a.legend)
    msgs = budgets(lv, a.cgb)
    for m in msgs:
        print(m)
    if any(m.startswith("ERROR") for m in msgs):
        return 1
    if a.cmd == "build":
        files = emit_c(lv, Path(a.out)) if a.format == "c" else emit_asm(lv, Path(a.out), a.section)
        print("wrote", ", ".join(map(str, files)))
    elif a.cmd == "preview":
        out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
        render(lv, Path(a.tileset) if a.tileset else None, a.scale, load_legend(src, a.legend)).save(out)
        print("preview:", out, "(orange lines = 32-tile hardware map boundaries; boxes = entities)")
    else:
        print(to_txt(lv, load_legend(src, a.legend)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
