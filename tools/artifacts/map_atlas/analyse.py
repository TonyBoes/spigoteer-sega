"""Map Atlas: the numbers (per palette, per piece, per leg, the tight windows, the hitches) from the static model and the walk logs."""
from collections import Counter

import numpy as np

import static as S

GUARD = {"dmg": 160, "cgb": 145}          # tests/test_story_map_world.py PERF worst (lines of 154 a frame; the Color at double speed)
NEAR = {"dmg": 150, "cgb": 135}           # "near": 10 lines under that guard
FRAME = 154


def hexc(c):
    return "#%02x%02x%02x" % tuple(c)


def palette_rows(st):
    """one row per palette: cells, pieces, and how it behaves in the tight views (8 palettes in view: every window of the map, and the windows on the paths)"""
    n = len(st.names)
    cells = Counter(int(a) for a in st.pal.ravel())
    by_piece = [Counter() for _ in range(n)]
    for y in range(S.CH):
        for x in range(S.CW):
            by_piece[int(st.pal[y, x])][int(st.piece[y, x])] += 1
    tight_all, marg_all, marg_cells = Counter(), Counter(), Counter()
    for (x, y), v in st.pos.items():
        if len(v["pals_view"]) >= 8:
            for p in v["pals_view"]:
                tight_all[p] += 1
            m = min(v["pals_view"], key=lambda p: v["palcells"][p])
            marg_all[m] += 1
            marg_cells[m] += v["palcells"][m]
    tight_path, marg_path, path_n = Counter(), Counter(), 0
    seen = set()
    for smp in st.leg_samples:
        for fx, fy, v in smp:
            if v["view"] in seen:
                continue
            seen.add(v["view"])
            path_n += 1
            if len(v["pals_view"]) >= 8:
                for p in v["pals_view"]:
                    tight_path[p] += 1
                marg_path[min(v["pals_view"], key=lambda p: v["palcells"][p])] += 1
    rows = []
    for i in range(n):
        rows.append(dict(i=i, name=st.names[i], rgb=[hexc(c) for c in st.rgb[i]], cells=cells.get(i, 0),
                         pieces=[(st.piece_names[k], c) for k, c in by_piece[i].most_common(3)],
                         tight_all=tight_all[i], marg_all=marg_all[i], marg_cells=(marg_cells[i] // marg_all[i]) if marg_all[i] else 0,
                         tight_path=tight_path[i], marg_path=marg_path[i]))
    return rows, dict(tight_all=sum(1 for v in st.pos.values() if len(v["pals_view"]) >= 8), total_all=len(st.pos), path_windows=path_n,
                      tight_path=sum(marg_path.values()))


def piece_rows(st):
    P = len(st.piece_names)
    owner_d = {}                         # DMG tile -> set of pieces; the Color ids likewise
    owner_c = {}
    for y in range(S.CH):
        for x in range(S.CW):
            k = int(st.piece[y, x])
            owner_d.setdefault(int(st.gD[y, x]), set()).add(k)
            owner_c.setdefault(int(st.gC[y, x]), set()).add(k)
    rows = []
    for k in range(P):
        m = st.piece == k
        cells = int(m.sum())
        td = set(int(t) for t in np.unique(st.gD[m]))
        tc = set(int(t) for t in np.unique(st.gC[m]))
        own_d = sum(1 for t in td if owner_d[t] == {k})
        own_c = sum(1 for t in tc if owner_c[t] == {k})
        rows.append(dict(k=k, name=st.piece_names[k], kind=st.piece_kind[k], cells=cells, dmg=len(td), dmg_own=own_d, dmg_single=int((st.shD[m] == 1).sum()),
                         cgb=len(tc), cgb_own=own_c, cgb_single=int((st.shC[m] == 1).sum()),
                         twins=int(st.twin_cell[m].sum()), pals=sorted(set(st.names[int(p)] for p in np.unique(st.pal[m]))),
                         per100=round(100 * own_d / max(cells, 1))))
    return rows


def leg_rows(st):
    out = []
    for li, smp in enumerate(st.leg_samples):
        tp = [v["tiles_pad"] for *_, v in smp]
        pv = [len(v["pals_view"]) for *_, v in smp]
        it, ip = int(np.argmax(tp)), int(np.argmax(pv))
        out.append(dict(li=li, name=st.leg_name(li), n=len(smp), tiles=[int(t) for t in tp], pals=pv, ids=[v["ids_pad"] for *_, v in smp],
                        max_tiles=max(tp), at_tiles=smp[it][:2], max_pals=max(pv), at_pals=smp[ip][:2], n_pal8=int(sum(1 for p in pv if p >= 8)),
                        n_tile170=int(sum(1 for t in tp if t >= 170)), xy=[(a, b) for a, b, _ in smp]))
    return out


def tight_windows(st, legs):
    """for the tightest view of each leg: which pieces the tiles in its padded window belong to"""
    rows = []
    for L in sorted(legs, key=lambda r: -r["max_tiles"]):
        smp = st.leg_samples[L["li"]]
        fx, fy, v = smp[int(np.argmax(L["tiles"]))]
        p0, p1, q0, q1 = v["win"]
        seen, by = {}, Counter()
        for y in range(q0, q1 + 1):
            for x in range(p0, p1 + 1):
                t = int(st.gD[y, x])
                if t not in seen:
                    seen[t] = int(st.piece[y, x])
        for t, k in seen.items():
            by[st.piece_names[k]] += 1
        single = sum(1 for t in seen if st.cntD[t] == 1)
        twins = sum(1 for t in seen if st.twin_of[t] >= 0)
        rows.append(dict(leg=L["name"], at=(fx, fy), tiles=v["tiles_pad"], by=by.most_common(5), single=single, twins=twins, pals=len(v["pals_view"])))
    return rows


def dyn_analyse(st, dyn):
    """per model: frames, the worst numbers with where, the hitch frames; per walk the series mapped onto its leg's samples"""
    res = {}
    for m in ("dmg", "cgb"):
        walks, hits = [], []
        worst = dict(logic=(0, None), end=(0, None), drain=(0, None), endly=(0, None))
        frames = late = near = hold = vql = 0
        for key, w in sorted(dyn[m].items(), key=lambda kv: tuple(int(a) for a in kv[0].split(","))):
            s, d = (int(a) for a in key.split(","))
            li = st.exit_leg[s][d] & 0x3F                        # (bit 6: a forgiveness button, no arrow)
            rev = bool(st.exit_leg[s][d] & 0x80)
            xy = np.array([(a, b) for a, b, _ in st.leg_samples[li]])
            log = w["log"]
            prev_vql = log[0][9] if log else 0
            series = []
            for r in log:
                fx, fy, cx, cy, logic, end, lag, drain, endly, vq = r
                idx = int(((xy[:, 0] - fx) ** 2 + (xy[:, 1] - fy) ** 2).argmin())
                dv = vq - prev_vql
                prev_vql = vq
                kind = 3 if end >= FRAME else 2 if logic >= NEAR[m] else 1 if lag else 4 if dv > 0 else 0
                series.append((idx, logic, end, kind))
                frames += 1
                late += end >= FRAME
                near += (logic >= NEAR[m]) and end < FRAME
                hold += bool(lag)
                vql += dv > 0
                for nm, val in (("logic", logic), ("end", end), ("drain", drain), ("endly", endly)):
                    if val > worst[nm][0]:
                        worst[nm] = (val, (st.leg_name(li) + (" back" if rev else ""), fx, fy))
                if kind:
                    hits.append((fx, fy, kind, logic, end))
            walks.append(dict(s=s, d=d, li=li, rev=rev, series=series, frames=len(log)))
        res[m] = dict(walks=walks, hits=hits, worst=worst, frames=frames, late=late, near=near, hold=hold, vql=vql)
    return res
