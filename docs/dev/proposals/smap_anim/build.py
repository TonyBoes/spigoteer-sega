"""Builds the GIFs, the frame strips and the numbers.   python3 -I build.py OUTDIR   (from the repo root; needs out/an/r3.json from r3dump.py and the A5 scratch src)
Preview and measurement only; it reads the typed frames of items.py."""
import json
import sys
from math import gcd
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import anim_lib as A  # noqa: E402
import items as I  # noqa: E402

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
STEP = 3                      # video frames per GIF frame (50 ms)
SC = 3


def lum(rgb):
    return 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]


a5 = A.load_a5()
tiles_orig = {id(a5): a5.all_tiles()}
orig_use = {}
items = I.all_items(a5)
report = []
strips = []
all_events = []                                    # (key, anim name, t0 events) for the combined estimate

for it in items:
    res = it.resolve()
    L = it.loop_len()
    ts = list(range(0, L, STEP))
    frames_dmg, frames_cgb, states = [], [], []
    for t in ts:
        px = it.state(t, res)
        states.append(px)
        d = A.render(it.scene, px, it.view, True, SC)
        c = A.render(it.scene, px, it.view, False, SC)
        frames_dmg.append(d)
        frames_cgb.append(c)
    A.save_gif([A.side_by_side(d, c) for d, c in zip(frames_dmg, frames_cgb)], OUT / f"{it.key}.gif", STEP * 1000 // 60)

    # ---- the flashing check, frame by frame (1x view, both models) ----
    worst = {}
    for model, fr in (("dmg", frames_dmg), ("cgb", frames_cgb)):
        arr = [np.asarray(f.resize((A.VW, A.VH), Image.NEAREST)).astype(np.int32) for f in fr]
        maxpix, maxd = 0.0, 0.0
        for i in range(len(arr)):
            a, b = arr[i], arr[(i + 1) % len(arr)]
            ch = np.any(a != b, axis=2)
            maxpix = max(maxpix, ch.mean() * 100)
            if ch.any():
                maxd = max(maxd, float(np.abs(lum(a) - lum(b))[ch].max()))
        # changes per pixel per second
        stack = np.stack(arr)
        trans = np.any(stack != np.roll(stack, -1, axis=0), axis=3).sum(axis=0)
        secs = L / 60
        worst[model] = (round(maxpix, 2), round(maxd), round(float(trans.max()) / secs, 2))
    # ---- tile statistics ----
    rows = []
    ev = []
    for a, base, cells in res:
        if a.name.startswith('~'):
            continue
        imgs = [base] + list(a.frames)
        orig_set = tiles_orig[id(it.scene)]
        rom_new = {x for x in imgs if x not in orig_set}
        # cells needing their own tile id: only_at on an image the map shares or lacks
        n_orig_cells = len(it.scene.cells_with(it.scene.tile(*a.at)))
        needs_id = (base not in orig_set) or (a.only_at and n_orig_cells > 1) or (a.cells_list is not None and n_orig_cells > len(a.cells_list))
        seqimgs = [base if k == 0 else a.frames[k - 1] for k in a.seq]
        n = len(a.seq)
        changes = sum(1 for i in range(n) if seqimgs[i] != seqimgs[(i + 1) % n])
        rows.append(dict(name=a.name, frames=len(imgs), distinct_new=len(rom_new), cells=len(cells), needs_id=needs_id, steps_per_loop=changes,
                         loop=n * a.period, period=a.period))
        for t in range(L):
            cur = it.frame_idx(a, t)
            prev = it.frame_idx(a, t - 1)
            ci = base if cur == 0 else a.frames[cur - 1]
            pi = base if prev == 0 else a.frames[prev - 1]
            if ci != pi:
                ev.append((t, a.name))
    per_t = {}
    for t, nme in ev:
        per_t.setdefault(t, []).append(nme)
    maxw = max((len(v) for v in per_t.values()), default=0)
    events_per_loop = len(per_t)
    rom_new_total = len({x for a, base, cells in res if not a.name.startswith("~") for x in ([base] + list(a.frames)) if x not in tiles_orig[id(it.scene)]})
    rom_new_rest = len({base for a, base, cells in res if not a.name.startswith("~") and base not in tiles_orig[id(it.scene)]})
    ids_new = sum(1 for r in rows if r["needs_id"])
    tiles_written = len(ev)
    report.append(dict(key=it.key, title=it.title, view=it.view, loop=L, gif_frames=len(ts), anims=rows, max_tiles_per_event=maxw, events_per_loop=events_per_loop,
                       tile_writes_per_loop=tiles_written, rom_new=rom_new_total, rom_new_at_rest=rom_new_rest, ids_new=ids_new, slots=len([a for a, b, c in res if not a.name.startswith("~")]), check=worst,
                       cells={r["name"]: r["cells"] for r in rows}))
    for t, nme in ev:
        all_events.append((it.key, nme, t % L, L))

    # ---- frame strip: the distinct states of the focus crop, DMG over Color, x4 ----
    x0, y0, x1, y1 = it.focus
    seen, picks = {}, []
    for t, px in zip(ts, states):
        sig = px[y0:y1, x0:x1].tobytes()
        if sig not in seen:
            seen[sig] = t
            picks.append((t, px))
    cols = []
    for t, px in picks:
        d = A.render(it.scene, px, it.view, True, 4, box=(x0, y0, x1, y1))
        c = A.render(it.scene, px, it.view, False, 4, box=(x0, y0, x1, y1))
        col = Image.new("RGB", (d.width, d.height * 2 + 4), (40, 40, 40))
        col.paste(d, (0, 0))
        col.paste(c, (0, d.height + 4))
        cols.append(col)
    sheet = Image.new("RGB", (sum(c.width + 6 for c in cols), cols[0].height), (40, 40, 40))
    xx = 0
    for c in cols:
        sheet.paste(c, (xx, 0))
        xx += c.width + 6
    sheet.save(OUT / f"strip_{it.key}.png")
    print(it.key, "loop", L, "gif frames", len(ts), "distinct strip states", len(picks), "check", worst)

json.dump(report, open(OUT / "report.json", "w"), indent=1, default=str)

# ---- the combined estimate: every animated tile of every item on one timeline (worst case: everything on screen) ----
T = 3600
cnt = np.zeros(T, int)
for key, nme, t, L in all_events:
    for k in range(T // L + 1):
        if t + k * L < T:
            cnt[t + k * L] += 1
print("ALL: tile writes per frame: max", cnt.max(), "frames with writes", int((cnt > 0).sum()), "of", T, "total tiles per second", cnt.sum() / (T / 60))
json.dump({"max": int(cnt.max()), "writes_per_s": cnt.sum() / (T / 60), "frames_with_writes": int((cnt > 0).sum()), "T": T, "hist": np.bincount(cnt).tolist()}, open(OUT / "combined.json", "w"))

# ---- per view: only what can be on screen together (the water counts wherever the river or lake shows) ----
GROUPS = {"river top (falls + water)": ["01_water", "02_falls"], "town (bunting + fountain + river water)": ["01_water", "03_fountain", "04a_bunting"],
          "lodge (smoke + water)": ["01_water", "06a_smoke_lodge"], "factory (smoke)": ["06b_smoke_factory"], "milk bar (two tails + lake water)": ["01_water", "07_cow_tail"],
          "airbase (dish + lamp, one frame set)": ["05_airbase"], "stadium (flag)": ["04b_stadium_flag"], "igloo (smoke + falls + water)": ["01_water", "02_falls", "06c_smoke_igloo"],
          "river scrolled down (falls + one upright log + water)": ["01_water", "02_falls", ("09_logs", {"VA_B"})],
          "logs view (6 logs, all groups)": ["01_water", "09_logs"],
          "ALL on screen at once (not possible)": [it.key for it in items]}
gres = {}
for g, keys in GROUPS.items():
    c = np.zeros(T, int)
    for key, nme, t, L in all_events:
        if key in keys or any(isinstance(k, tuple) and k[0] == key and nme in k[1] for k in keys):
            for k in range(T // L + 1):
                if t + k * L < T:
                    c[t + k * L] += 1
    gres[g] = dict(max_tiles=int(c.max()), max_bytes=int(c.max()) * 16, avg_bytes_per_frame=round(float(c.sum()) * 16 / T, 2), tiles_per_s=round(float(c.sum()) / (T / 60), 1))
    print(g, gres[g])
json.dump(gres, open(OUT / "groups.json", "w"), indent=1)
