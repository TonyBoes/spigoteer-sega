#!/usr/bin/env python3
"""Map Atlas page: where the story map spends its tile, palette and engine budgets as Sal walks the plan.

    make map-atlas            (or: python3 tools/artifacts/map_atlas/build.py [--no-dyn] [--jobs N])

Needs the built ROM (`make`, build/game.gb and build/game.noi) for the walks; --no-dyn reuses the last walks (out/map_atlas/dyn.json).
Writes out/map_atlas/index.html and out/map_atlas/img/*.png (publish index.html with img/*.png as files).
Static numbers come from tools/gen_smap_world.py's own Model, geometry and path windows (static.py asserts the path windows are the build's).
"""
import argparse
import datetime
import html
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
sys.path.insert(0, str(HERE))
import analyse as A  # noqa: E402
import images as IM  # noqa: E402
import static as S  # noqa: E402

OUT = ROOT / "out" / "map_atlas"
LIM_T, LIM_P = S.LIM_TILES, S.LIM_PALS
esc = html.escape


def git(*a):
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def swatches(cols):
    return '<span class="sws">' + "".join(f'<i class="sw" style="background:{c}"></i>' for c in cols) + "</span>"


def stat(k, v, unit, where, cls=""):
    return f'<div class="stat {cls}"><div class="k">{k}</div><div class="v">{v} <small>{unit}</small></div><div class="w">{where}</div></div>'


def chart(n, series, ymin, ymax, lines, dots=(), w=400, h=60):
    X = lambda i: i * w / max(n - 1, 1)                       # noqa: E731
    Y = lambda v: h - 3 - (min(max(v, ymin), ymax) - ymin) / (ymax - ymin) * (h - 6)   # noqa: E731
    o = [f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" aria-hidden="true">']
    for q in range(1, 4):
        o.append(f'<line class="grid" x1="0" x2="{w}" y1="{h * q / 4:.1f}" y2="{h * q / 4:.1f}"/>')
    for cls, v in lines:
        o.append(f'<line class="{cls}" x1="0" x2="{w}" y1="{Y(v):.1f}" y2="{Y(v):.1f}"/>')
    for cls, pts in series:
        o.append(f'<polyline class="{cls}" points="' + " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in pts) + '"/>')
    for cls, i, v in dots:
        o.append(f'<circle class="{cls}" cx="{X(i):.1f}" cy="{Y(v):.1f}" r="3.2"/>')
    o.append("</svg>")
    return "".join(o)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-dyn", action="store_true", help="reuse out/map_atlas/dyn.json instead of walking the ROM")
    ap.add_argument("--jobs", type=int, default=3)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    st = S.Static()
    assert st.match_build, "the path windows are not the generator's: static.py is out of step with tools/gen_smap_world.py path_windows"
    # the generator's own worst values, for the cross-check printed at the end
    n21, at21 = st.dm.window_max(*S.G.WIN_V)
    p21, pat21 = st.cg.palette_max(*S.G.WIN_V)
    # ---- the walks -----------------------------------------------------------------------------------------------------------------------------------
    dynf = OUT / "dyn.json"
    rom = ROOT / "build" / "game.gb"
    stale = ""
    if args.no_dyn and dynf.exists():
        raw = json.loads(dynf.read_text())
    else:
        import dyn
        raw = dyn.collect(st.exits, args.jobs)
        dynf.write_text(json.dumps(raw))
    newest = max(p.stat().st_mtime for pat in ("src/*.c", "src/*.h", "assets/smap/*") for p in ROOT.glob(pat))
    if rom.exists() and rom.stat().st_mtime < newest:
        stale = "The ROM is older than the sources: run make first."
        print("WARNING:", stale)
    dy = A.dyn_analyse(st, raw)
    # ---- numbers --------------------------------------------------------------------------------------------------------------------------------------
    pal_rows, pal_sum = A.palette_rows(st)
    pc_rows = A.piece_rows(st)
    legs = A.leg_rows(st)
    tw = A.tight_windows(st, legs)
    imgs = IM.make_all(st, dy, OUT)
    commit = git("rev-parse", "--short", "HEAD")
    dirty = bool(git("status", "--porcelain", "src", "assets"))
    commit_s = commit + (" with local changes" if dirty else "")
    V = "?v=" + commit
    allv = list(st.pos.values())
    worst_all = max(v["tiles_pad"] for v in allv)
    worst_leg = max(legs, key=lambda r: r["max_tiles"])
    rest_t = max(st.rest, key=lambda r: r[3]["tiles_pad"])
    pal8_legs = [r for r in legs if r["max_pals"] >= 8]
    single_d, single_c = int((st.cntD == 1).sum()), int((st.cntC == 1).sum())
    nd, nc = len(st.cntD), len(st.cntC)
    twin_t = int((st.twin_of >= 0).sum())
    D_, C_ = dy["dmg"], dy["cgb"]

    def where(w):
        return f"{esc(w[0])}, x {w[1]} y {w[2]}"

    def late_by_leg(m):
        c = {}
        for w in dy[m]["walks"]:
            k = sum(1 for s in w["series"] if s[3] == 3)
            if k:
                nm = st.leg_name(w["li"]) + (" back" if w["rev"] else "")
                c[nm] = c.get(nm, 0) + k
        return ", ".join(f"{esc(k)} {v}" for k, v in sorted(c.items(), key=lambda kv: -kv[1])) or "none"
    stats = [
        stat("DMG tiles in view, paths", worst_leg["max_tiles"], f"of {LIM_T}", f"{esc(worst_leg['name'])}, x {worst_leg['at_tiles'][0]} y {worst_leg['at_tiles'][1]}",
             "bad" if worst_leg["max_tiles"] >= 170 else "warn" if worst_leg["max_tiles"] >= 160 else ""),
        stat("DMG tiles in view, anywhere", worst_all, f"of {LIM_T}", f"{sum(1 for v in allv if v['tiles_pad'] > LIM_T)} of {len(allv)} spots are over; no path goes there"),
        stat("Color palettes in view, paths", max(r["max_pals"] for r in legs), f"of {LIM_P}", f"{pal_sum['tight_path']} of {pal_sum['path_windows']} Color views on the paths are full; {len(pal8_legs)} of 11 legs reach it",
             "warn" if pal8_legs else ""),
        stat("DMG walk load, worst frame", D_["worst"]["logic"][0], "of 160 lines", where(D_["worst"]["logic"][1]), "warn" if D_["worst"]["logic"][0] >= 150 else ""),
        stat("Color walk load, worst frame", C_["worst"]["logic"][0], "of 145 lines", where(C_["worst"]["logic"][1]) + " (double speed)", "warn" if C_["worst"]["logic"][0] >= 135 else ""),
        stat("DMG late frames", D_["late"], f"of {D_['frames']}", "Late: the frame's logic ended on line 154 or later. " + late_by_leg("dmg"), "bad" if D_["late"] else "good"),
        stat("Color late frames", C_["late"], f"of {C_['frames']}", late_by_leg("cgb") + f". Camera waits {C_['hold']}, over 135 lines {C_['near']}", "bad" if C_["late"] else "good"),
        stat("VBlank drain, worst", f"DMG {D_['worst']['drain'][0]} · Color {C_['worst']['drain'][0]}", "of 13 ticks", f"Color at {where(C_['worst']['drain'][1])}; 13 is the picture guard, the map has none",
             "warn" if C_["worst"]["drain"][0] > 13 else ""),
        stat("DMG tiles used by one cell", single_d, f"of {nd}", f"{round(100 * single_d / nd)} percent of the DMG set is one-off art"),
        stat("Color ids used by one cell", single_c, f"of {nc}", f"{round(100 * single_c / nc)} percent; {st.cg.merged_from} blocks merge to {nc} ids by mirroring"),
        stat("DMG near-twin tiles", twin_t, f"of {nd}", "within 2 of 64 pixels of another tile"),
    ]
    # ---- costly / cheap lists -------------------------------------------------------------------------------------------------------------------------
    costly = []
    top = sorted(tw, key=lambda r: -r["tiles"])[:3]
    for r in top:
        costly.append(f"<b>{esc(r['leg'])}</b>: DMG {r['tiles']} of {LIM_T} tiles at x {r['at'][0]} y {r['at'][1]}. " +
                      ", ".join(f"{esc(k)} {v}" for k, v in r["by"][:4]) + f". {r['single']} of them used by one cell.")
    marg = sorted(pal_rows, key=lambda r: -r["marg_path"])
    costly.append("<b>Palettes in the way</b>, Color, full views on the paths (fewest-cell palette in each): " +
                  "; ".join(f"{esc(r['name'])} {r['cells']} cells, {r['marg_path']} view" + ("" if r["marg_path"] == 1 else "s") for r in marg if r["marg_path"])[:400] + ".")
    own = sorted([r for r in pc_rows], key=lambda r: -r["dmg_own"])[:5]
    costly.append("<b>Most own DMG tiles</b>: " + "; ".join(f"{esc(r['name'])} {r['dmg_own']} for {r['cells']} cells" for r in own) + ".")
    costly.append(f"<b>Walk frames</b>: DMG worst {D_['worst']['logic'][0]} lines at {where(D_['worst']['logic'][1])}; Color worst {C_['worst']['logic'][0]} at {where(C_['worst']['logic'][1])}.")
    cheap = []
    small = sorted([r for r in pal_rows if r["cells"] <= 15], key=lambda r: r["cells"])
    cheap.append("<b>Palettes with few cells</b>, Color: " + "; ".join(
        f"{esc(r['name'])} {r['cells']} cell" + ("" if r["cells"] == 1 else "s") + (f" (fewest in {r['marg_path']} full path views)" if r["marg_path"] else "") for r in small) + ".")
    flat = sorted([r for r in pc_rows if r["cells"] >= 40], key=lambda r: r["dmg"] / r["cells"])[:4]
    cheap.append("<b>Cheap ground</b>, DMG: " + "; ".join(f"{esc(r['name'])} {r['cells']} cells in {r['dmg']} tiles" for r in flat) + ".")
    onces = sorted([r for r in pc_rows if r["cells"] >= 40], key=lambda r: -r["dmg_single"] / r["cells"])[:4]
    cheap.append("<b>Almost no repeats</b>, DMG: " + "; ".join(f"{esc(r['name'])} {r['dmg_single']} of {r['cells']} cells are one-off" for r in onces) + ".")
    tw_p = sorted(pc_rows, key=lambda r: -r["twins"])[:4]
    cheap.append(f"<b>Near twins</b>, DMG: {twin_t} tiles differ from another by 2 pixels or fewer; cells with one: " + "; ".join(f"{esc(r['name'])} {r['twins']}" for r in tw_p) + ".")
    summary = ('<h2>Summary</h2><div class="stats">' + "".join(stats) + "</div>" + stale_html(stale) +
               '<h2>Costly</h2><div class="card"><ul>' + "".join(f"<li>{c}</li>" for c in costly) + "</ul></div>"
               '<h2>Cheap</h2><div class="card"><ul>' + "".join(f"<li>{c}</li>" for c in cheap) + "</ul></div>")
    # ---- details --------------------------------------------------------------------------------------------------------------------------------------
    det = []
    pcols = ["Palette", "Color cells", "Pieces", "Color views at 8, anywhere", "Color views at 8, paths", "Fewest-cell one, paths", "Fewest-cell one, anywhere"]
    prow = []
    for r in pal_rows:
        prow.append(f'<tr><td class="first" data-s="{esc(r["name"])}">{swatches(r["rgb"])} {esc(r["name"])}</td><td class="n" data-l="Color cells" data-s="{r["cells"]}">{r["cells"]}</td>'
                    f'<td data-l="Pieces" data-s="">{esc(", ".join(f"{k} {c}" for k, c in r["pieces"]))}</td>'
                    f'<td class="n" data-l="Color views at 8, anywhere" data-s="{r["tight_all"]}">{r["tight_all"]}</td>'
                    f'<td class="n" data-l="Color views at 8, paths" data-s="{r["tight_path"]}">{r["tight_path"]}</td>'
                    f'<td class="n" data-l="Fewest-cell one, paths" data-s="{r["marg_path"]}">{r["marg_path"]}</td>'
                    f'<td class="n" data-l="Fewest-cell one, anywhere" data-s="{r["marg_all"]}">{r["marg_all"]}</td></tr>')
    det.append(table_block("Palettes", "pal", pcols, prow, [0], f"{len(pal_rows)} Color BG palettes. Views at 8: Color views with all 8 palette slots used, of {pal_sum['total_all']} spots anywhere and "
                           f"{pal_sum['path_windows']} on the paths. Fewest-cell one: the palette with the fewest cells in a full view."))
    qcols = ["Piece", "Cells", "DMG tiles", "DMG own", "DMG one-off cells", "Color ids", "Color own", "Color one-off cells", "DMG twin cells", "Palettes"]
    qrow = []
    for r in sorted(pc_rows, key=lambda r: -r["dmg_own"]):
        cells = [("first", "Piece", esc(r["name"]), esc(r["name"])), ("n", "Cells", r["cells"], r["cells"]), ("n", "DMG tiles", r["dmg"], r["dmg"]), ("n", "DMG own", r["dmg_own"], r["dmg_own"]),
                 ("n", "DMG one-off cells", r["dmg_single"], r["dmg_single"]), ("n", "Color ids", r["cgb"], r["cgb"]), ("n", "Color own", r["cgb_own"], r["cgb_own"]),
                 ("n", "Color one-off cells", r["cgb_single"], r["cgb_single"]), ("n", "DMG twin cells", r["twins"], r["twins"]), ("", "Palettes", esc(", ".join(r["pals"])), len(r["pals"]))]
        qrow.append("<tr>" + "".join(f'<td class="{c}" data-l="{l}" data-s="{s}">{v}</td>' for c, l, v, s in cells) + "</tr>")
    det.append(table_block("Pieces", "pc", qcols, qrow, [0], "Venues are the picture boxes; Roads are cells within one cell of a leg; Land is the rest by palette. "
                           "Own: tiles found nowhere else on the map. One-off cells: cells whose tile no other cell uses."))
    trow = []
    for r in tw:
        trow.append(f'<tr><td class="first" data-s="{esc(r["leg"])}">{esc(r["leg"])}</td><td class="n" data-l="DMG tiles" data-s="{r["tiles"]}">{r["tiles"]}</td>'
                    f'<td data-l="Where" data-s="">x {r["at"][0]} y {r["at"][1]}</td><td data-l="Made of" data-s="">{esc(", ".join(f"{k} {v}" for k, v in r["by"]))}</td>'
                    f'<td class="n" data-l="One-off" data-s="{r["single"]}">{r["single"]}</td><td class="n" data-l="Near twins" data-s="{r["twins"]}">{r["twins"]}</td></tr>')
    det.append(table_block("Tightest views", "tw", ["Leg", "DMG tiles", "Where", "Made of", "One-off", "Near twins"], trow, [0], "The tightest padded view of each leg, DMG: which pieces the tiles belong to."))
    # legs: charts
    lg = []
    for L in legs:
        li = L["li"]
        n = L["n"]
        a, b, _ = st.legs[li]
        tt = [(i, v) for i, v in enumerate(L["tiles"])]
        pp = [(i, v) for i, v in enumerate(L["pals"])]
        parts = [f'<p class="muted">{esc(S.NAMES[st.order[a]])} at the left, {esc(S.NAMES[st.order[b]])} at the right, {n} px. Blue: walked forward. Grey: walked back.</p>']
        parts.append(f'<div class="cap"><b>DMG tiles in view</b><span>worst {L["max_tiles"]} of {LIM_T}</span></div>' + chart(n, [("la", tt)], 60, 190, [("lim", LIM_T)]))
        parts.append(f'<div class="cap"><b>Color palettes in view</b><span>worst {L["max_pals"]} of {LIM_P}, {L["n_pal8"]} px at 8</span></div>' + chart(n, [("la", pp)], 0, 9, [("lim", LIM_P)]))
        for m, nm, guard in (("dmg", "DMG walk load", 160), ("cgb", "Color walk load, double speed", 145)):
            ws = [w for w in dy[m]["walks"] if w["li"] == li]
            ser = [("lb" if w["rev"] else "la", [(s[0], s[1]) for s in w["series"]]) for w in sorted(ws, key=lambda w: not w["rev"])]
            dots = [(f"d{s[3]}", s[0], s[1]) for w in ws for s in w["series"] if s[3]]
            mx = max((s[1] for w in ws for s in w["series"]), default=0)
            late = sum(1 for w in ws for s in w["series"] if s[3] == 3)
            parts.append(f'<div class="cap"><b>{nm}</b><span>worst {mx} of {guard} lines, {late} late</span></div>' + chart(n, ser, 20, 170, [("lim", guard), ("frame", 154)], dots))
        lg.append(f'<details><summary>{esc(L["name"])} · DMG {L["max_tiles"]} tiles · Color {L["max_pals"]} palettes</summary><div class="in">' + "".join(parts) + "</div></details>")
    det.append('<details><summary>Legs</summary><div class="in"><p class="muted">Per leg, along the path. Dashed red: the limit or guard. Dotted amber: line 154, the end of the frame. '
               'Dots: red late, amber over 135 or 150 lines, blue camera wait, black drain late.</p>' + "".join(lg) + "</div></details>")
    det.append('<details><summary>How it is measured</summary><div class="in">'
               f"<p>Tiles and palettes: tools/gen_smap_world.py's own Model for the finished map. DMG tiles in view count the distinct DMG tiles in the camera's cells plus one cell on every side, "
               f"the window rule the DMG slot allocator is held to ({LIM_T} slots). Color palettes count the distinct BG palettes in the view's own cells (limit 8). "
               f"The camera follows Sal with his feet at (80, 84), clamped. Paths: every pixel of every leg and each stop's resting view; they equal the generator's path windows.</p>"
               f"<p>Cross-check with the generator: worst DMG 21 x 19 window anywhere {n21} at {at21}; worst Color palettes in 21 x 19 {p21} at {pat21}. This page, same windows: "
               f"DMG {max(v['tiles_view'] for v in allv)} and Color {max(len(v['pals_view']) for v in allv)} (cell-aligned cameras, finished map).</p>"
               "<p>Walks: build/game.gb in PyBoy, every leg both ways from a CONTINUE with all ten cleared. One record per game frame (a hook on walk_step): "
               "perf_logic_last and perf_end_last in lines of 154, a camera wait is V_LAG bit 0, the drain is drain_ticks_max and vq_end_ly_max read and cleared each frame, vq_late the count. "
               "Color runs at double speed, as shipped. Late is a frame whose logic ended on line 154 or later; near is within 10 lines of the guard in tests/test_story_map_world.py "
               "(DMG 160, Color 145). Each record's position is Sal's feet at the start of the frame, its numbers are the frame before.</p>"
               "<p>Not measured: the C build, the other unlock states, the tile animations, sprites on top.</p></div></details>")
    # ---- data -----------------------------------------------------------------------------------------------------------------------------------------
    def rows(a, f):
        return [[f(a[y, x]) for x in range(S.CW)] for y in range(S.CH)]
    dyn_cells = {}
    for m in ("dmg", "cgb"):
        dc = {}
        for w in raw[m].values():
            for r in w["log"]:
                i = (min(r[1], S.CH * 8 - 1) >> 3) * S.CW + (min(r[0], S.CW * 8 - 1) >> 3)
                e = dc.setdefault(i, [0, 0, 0, 0, 0])
                e[0] = max(e[0], r[4])
                e[1] += r[5] >= A.FRAME
                e[2] += (r[4] >= A.NEAR[m] and r[5] < A.FRAME)
                e[3] += r[6]
                e[4] += 1
        dyn_cells[m] = dc
    flat = [st.pos[(x, y)] for y in range(S.CH) for x in range(S.CW)]
    lay = IM
    layers = [dict(id="none", label="None", legend=[]),
              dict(id="dmg_path", label="DMG load, paths", legend=[(c, t) for _, c, t in lay.BANDS_TILES[:4]]),
              dict(id="dmg_all", label="DMG load, anywhere", legend=[(c, t) for _, c, t in lay.BANDS_TILES]),
              dict(id="pals", label="Palettes in view", legend=[(c, t) for _, c, t in lay.BANDS_PALS]),
              dict(id="palcell", label="Palette per cell", legend=[(imgs["pal_cols"][i], f"{st.names[i]} {r['cells']}") for i, r in enumerate(pal_rows)]),
              dict(id="piece", label="Piece per cell", legend=[(imgs["piece_cols"][i], n) for i, n in enumerate(st.piece_names)]),
              dict(id="share", label="Tile sharing", legend=[]),
              dict(id="twin", label="Near twins", legend=[(lay.TWIN, "DMG tile with a near twin")])]
    data = dict(
        cw=S.CW, ch=S.CH, layers=layers, layer0="dmg_path", guard=A.GUARD,
        share_legend={"dmg": [(c, "DMG " + t) for _, c, t in lay.BANDS_SHARE], "cgb": [(c, "Color " + t) for _, c, t in lay.BANDS_SHARE]},
        hit_legend=[(c, t) for c, t in (lay.HIT[3], lay.HIT[2], lay.HIT[1], lay.HIT[4])],
        pal=[dict(n=r["name"], c=r["rgb"]) for r in pal_rows], pieces=st.piece_names,
        cellPal=["".join(chr(48 + int(v)) for v in row) for row in st.pal], cellPiece=["".join(chr(48 + int(v)) for v in row) for row in st.piece],
        shD=rows(st.shD, int), shC=rows(st.shC, int), twin=["".join("1" if v else "0" for v in row) for row in st.twin_cell],
        pos=dict(tiles_pad=[v["tiles_pad"] for v in flat], tiles_view=[v["tiles_view"] for v in flat], ids_pad=[v["ids_pad"] for v in flat]),
        stops=[dict(name=S.NAMES[n], x=x, y=y, rest=dict(cam=list(c), v=list(v["view"]), tiles_pad=v["tiles_pad"], tiles_view=v["tiles_view"], ids_pad=v["ids_pad"]))
               for (i, n, c, v), (x, y) in zip(st.rest, st.stops)],
        legs=[r["name"] for r in legs],
        path=dict(x=[p[0] for r in legs for p in r["xy"]], y=[p[1] for r in legs for p in r["xy"]], leg=[r["li"] for r in legs for _ in r["xy"]]),
        dyn={m: {str(k): v for k, v in dyn_cells[m].items()} for m in dyn_cells})
    btns = "".join(f'<button class="stopb" data-i="{i}" style="left:{s["x"] / (S.CW * 8) * 100:.2f}%;top:{s["y"] / (S.CH * 8) * 100:.2f}%">{esc(s["name"])}</button>' for i, s in enumerate(data["stops"]))
    tpl = (HERE / "template.html").read_text()
    page = (tpl.replace("%%SUMMARY%%", summary).replace("%%DETAILS%%", "".join(det)).replace("%%STOPBTNS%%", btns)
            .replace("%%COMMIT%%", esc(commit_s)).replace("%%DATE%%", datetime.date.today().isoformat()).replace("%%V%%", V)
            .replace("%%DATA%%", json.dumps(data, separators=(",", ":")).replace("</", "<\\/")))
    page = page.replace('var mode = "cgb", layer = "none"', 'var mode = "cgb", layer = D.layer0')
    (OUT / "index.html").write_text(page)
    total = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file() and p.name != "dyn.json")
    print(f"map atlas: {OUT}/index.html, {len(list((OUT / 'img').glob('*.png')))} images, {total / 1e6:.1f} MB; build {commit_s}")
    print(f"cross-check: generator worst DMG 21x19 {n21} at {at21}, Color palettes {p21} at {pat21}; atlas same windows DMG {max(v['tiles_view'] for v in allv)}, "
          f"Color {max(len(v['pals_view']) for v in allv)}; path windows equal the generator's: {st.match_build}")
    print(f"paths: DMG tiles worst {worst_leg['max_tiles']} ({worst_leg['name']}), anywhere {worst_all}; Color palettes worst {max(r['max_pals'] for r in legs)}")
    print(f"walks: DMG {D_['frames']} frames worst {D_['worst']['logic'][0]} late {D_['late']}; Color {C_['frames']} frames worst {C_['worst']['logic'][0]} late {C_['late']}")


def stale_html(s):
    return f'<p><span class="tag bad">{esc(s)}</span></p>' if s else ""


def table_block(title, tid, cols, rows, first, note):
    opts = "".join(f'<option value="{i}" data-num="{0 if i in first else 1}">{esc(c)}</option>' for i, c in enumerate(cols) if c not in ("Pieces", "Palettes", "Made of", "Where"))
    head = "".join(f'<th class="{"" if i in first or c in ("Pieces", "Palettes", "Made of", "Where") else "n"}">{esc(c)}</th>' for i, c in enumerate(cols))
    return (f'<details><summary>{title}</summary><div class="in"><p class="muted">{note}</p><div class="sortbar"><label for="s_{tid}">Sort</label>'
            f'<select id="s_{tid}" data-for="t_{tid}">{opts}</select></div><table class="sort" id="t_{tid}"><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div></details>')


if __name__ == "__main__":
    main()
