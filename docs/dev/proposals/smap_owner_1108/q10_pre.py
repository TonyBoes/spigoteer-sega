"""Q10 pre-world hook (owner 11-08: "I don't really like the round topped trees. Just remove them for now with the bushes ... Also remove overlapping pine trees for now").
owner_pre.apply calls apply(lay, decor) when the flag Q10 is on (tools/dev/smap_snapshot.py OWNER_FLAGS), after the town's relocation and before the world is built.

  - every round-topped tree and every bush leaves the SCENERY list: decor.ROUND, BUSH, JUNGLE_TREE, JUNGLE_BUSH and the round / jungle clusters (clusters.RR_R, RR_L, RRR, JJ, JJJ).  The ground under
    them is then what put_decor leaves: the biome's own ground tiles (flat and the tuft of the cell), no pad, no stray pixel
  - every pine cluster (clusters.PP, PPP) leaves, and so does any single pine whose box meets another pine's (none does today); the remaining single pines are snapped to the cell grid
    (the nearest 8 px phase, at most 4 px, only if the new box meets no other item's box; every single pine stands on the grid already, so nothing moves today)
  - snow spruces stay (a separate drawing); they are treated like pines only if two of them overlap (none do)
  - not touched: the venue pictures (their own trees, bamboo in the zoo picture), bamboo clumps, rocks, drifts, cacti, peaks, logs
Placement only: no pixel is drawn here.  The result is recorded in REPORT for the snapshot's printout."""
REPORT = {"removed": {}, "snapped": [], "borderline": [], "spruce_overlaps": 0}


def _box(item):
    (pal, rows), x, y = item
    return x, y, x + len(rows[0]), y + len(rows)


def _meet(a, b):
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def apply(lay, decor):
    import clusters
    ROUND_LIKE = {id(p): n for n, p in (("ROUND", decor.ROUND), ("BUSH", decor.BUSH), ("JUNGLE_TREE", decor.JUNGLE_TREE), ("JUNGLE_BUSH", decor.JUNGLE_BUSH),
                                        ("RR_R", clusters.RR_R), ("RR_L", clusters.RR_L), ("RRR", clusters.RRR), ("JJ", clusters.JJ), ("JJJ", clusters.JJJ))}
    PINE_CLUSTERS = {id(p): n for n, p in (("PP", clusters.PP), ("PPP", clusters.PPP))}
    removed = REPORT["removed"]
    keep = []
    for it in lay.SCENERY:
        n = ROUND_LIKE.get(id(it[0])) or PINE_CLUSTERS.get(id(it[0]))
        if n:
            removed[n] = removed.get(n, 0) + 1
            for vk, (_, (vx, vy)) in lay.VENUES.items():       # a removed item whose box meets a venue's picture cells: listed, not guessed
                import layouts
                w, h = layouts.SZ.get(vk, (12, 9))
                b = _box(it)
                if _meet(b, (vx * 8, vy * 8, (vx + w) * 8, (vy + h) * 8)):
                    REPORT["borderline"].append((n, it[1], it[2], vk))
            continue
        keep.append(it)
    pines = [i for i in keep if i[0] is decor.PINE]
    gone = set()
    for a in pines:
        for b in pines:
            if a is not b and _meet(_box(a), _box(b)):
                gone.add(id(a))
    for a in pines:
        if id(a) in gone:
            removed["PINE_overlap"] = removed.get("PINE_overlap", 0) + 1
    sp = [i for i in keep if i[0] is decor.SPRUCE]
    for a in sp:
        for b in sp:
            if a is not b and _meet(_box(a), _box(b)):
                gone.add(id(a))
                REPORT["spruce_overlaps"] += 1
    keep = [i for i in keep if id(i) not in gone]
    out = []
    boxes = [_box(i) for i in keep]
    for k, it in enumerate(keep):
        if it[0] is decor.PINE and (it[1] % 8 or it[2] % 8):
            x, y = it[1], it[2]
            nx, ny = ((x + 4) // 8) * 8, ((y + 4) // 8) * 8
            nb = _box((it[0], nx, ny))
            if not any(_meet(nb, b) for j, b in enumerate(boxes) if j != k):
                REPORT["snapped"].append(((x, y), (nx, ny)))
                it = (it[0], nx, ny)
                boxes[k] = nb
        out.append(it)
    lay.SCENERY = out
    print("Q10 trees:", REPORT)
