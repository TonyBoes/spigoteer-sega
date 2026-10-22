"""Constructed objects: the visible OAM entries of a frame grouped into the things the game builds from them (Sal, a lifted patron, a mug, ...).

The atlas page shows these assembled figures at first glance and the raw 8x16 entries ("pieces") only on request.
A classifier maps one OAM entry to (sort key, kind, pose or None, group key): entries of one frame with the same group key belong together
(then split again by proximity, so two far-apart groups never become one wide picture). The pose is a name where the game's layout tells it, else
None and numbered ("pose 2") by the order of the tile ids. Each distinct look (kind + pixels, transparent ground, the palette the game used) is kept once.
"""
from PIL import Image

import analyze as A
import capture as C

CAP_KIND = 10          # distinct looks kept per kind
CAP_TOTAL = 80         # per screen and model
MAX_BOX = 64           # a group wider or taller than this (px) is split into single entries


def entry_image(o, s, cgb, h):
    """The entry's pixels on a transparent ground in the palette it was drawn with, flips applied (None when it draws nothing)."""
    v = s.vram[o["bank"] if cgb else 0]
    rows = []
    for t in o["slots"]:
        rows += A.tile_pixels(v[t * 16:t * 16 + 16])
    if o["yflip"]:
        rows.reverse()
    if o["xflip"]:
        rows = [r[::-1] for r in rows]
    if cgb:
        cols = [A.rgb(c) for c in s.objpal[o["pal"]]]
    else:
        cols = [C.DMG_SHADES[x] for x in A.dmg_palette(s.regs["OBP1" if o["dmgpal"] else "OBP0"])]
    if not any(p for r in rows for p in r):
        return None
    im = Image.new("RGBA", (8, h))
    im.putdata([(0, 0, 0, 0) if p == 0 else cols[p] + (255,) for r in rows for p in r])
    return im


def generic(o):
    return (9, 0), "Sprite group", None, ("g",)


def components(ents, h):
    """Split entries (dicts with x, y) into groups that touch or overlap (within 1 px)."""
    n = len(ents)
    par = list(range(n))

    def find(a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a
    for a in range(n):
        for b in range(a + 1, n):
            ea, eb = ents[a][0], ents[b][0]
            if abs(ea["x"] - eb["x"]) <= 8 + 1 and abs(ea["y"] - eb["y"]) <= h + 1:
                par[find(a)] = find(b)
    out = {}
    for a in range(n):
        out.setdefault(find(a), []).append(ents[a])
    return [out[k] for k in sorted(out)]


class ObjAcc:
    def __init__(self, cgb, classify):
        self.cgb, self.classify = cgb, classify
        self.objs = {}        # (kind, pose, size, bytes) -> dict

    def add(self, s, objs, h):
        cgb = self.cgb
        groups = {}
        for o in objs:
            if not o["visible"]:
                continue
            im = entry_image(o, s, cgb, h)
            if im is None:
                continue
            sk, kind, pose, gk = self.classify(o)
            groups.setdefault((sk, kind, gk), []).append((o, im, pose))
        for (sk, kind, gk), ents in sorted(groups.items(), key=lambda kv: kv[0][0] + (kv[0][1],)):
            for comp in components(ents, h):
                x0, y0 = min(e[0]["x"] for e in comp), min(e[0]["y"] for e in comp)
                x1, y1 = max(e[0]["x"] + 8 for e in comp), max(e[0]["y"] + h for e in comp)
                if x1 - x0 > MAX_BOX or y1 - y0 > MAX_BOX:
                    parts = [[e] for e in comp]
                else:
                    parts = [comp]
                for part in parts:
                    self._one(s, sk, kind, part, h)

    def _one(self, s, sk, kind, comp, h):
        comp = sorted(comp, key=lambda e: e[0]["i"])
        x0, y0 = min(e[0]["x"] for e in comp), min(e[0]["y"] for e in comp)
        x1, y1 = max(e[0]["x"] + 8 for e in comp), max(e[0]["y"] + h for e in comp)
        im = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
        for o, eim, _ in reversed(comp):                      # (a lower OAM index is drawn on top)
            layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
            layer.paste(eim, (o["x"] - x0, o["y"] - y0))
            im = Image.alpha_composite(im, layer)
        pose = next((e[2] for e in comp if e[2]), None)
        key = (kind, pose, im.size, im.tobytes())
        d = self.objs.get(key)
        if d is None:
            sig = tuple(sorted((e[0]["bank"] if self.cgb else 0, e[0]["tile"]) for e in comp))
            pieces = [dict(dx=e[0]["x"] - x0, dy=e[0]["y"] - y0, tile=e[0]["tile"], bank=e[0]["bank"] if self.cgb else 0, xf=e[0]["xflip"], yf=e[0]["yflip"],
                           slot=e[0]["pal"] if self.cgb else e[0]["dmgpal"], i=e[0]["i"], img=e[1]) for e in comp]
            d = self.objs[key] = dict(sk=sk, kind=kind, pose=pose, img=im, sig=sig, h=h, pieces=pieces, n=0, order=len(self.objs))
        d["n"] += 1

    def merge(self, other):
        for k, d in other.objs.items():
            if k in self.objs:
                self.objs[k]["n"] += d["n"]
            else:
                d["order"] = len(self.objs)
                self.objs[k] = d

    def record(self):
        """(list of JSON-able objects, {"objs": [images], "pool": [piece images]}). Each object: kind, pose caption, name, palette slots, number of
        entries, pieces [dx, dy, tile, bank, xflip, yflip, slot, oam index, pool index], seen (samples), size."""
        by = {}
        for d in self.objs.values():
            by.setdefault((d["sk"], d["kind"]), []).append(d)
        chosen = []
        for (sk, kind), lst in sorted(by.items()):
            keep = sorted(lst, key=lambda d: (-d["n"], d["order"]))[:CAP_KIND]
            chosen.append((sk, kind, sorted(keep, key=lambda d: (d["sig"], -d["n"], d["order"]))))
        total = sum(len(c[2]) for c in chosen)
        while total > CAP_TOTAL:                              # (drop the rarest looks of the busiest kind)
            c = max(chosen, key=lambda c: len(c[2]))
            c[2].remove(min(c[2], key=lambda d: (d["n"], -d["order"])))
            total -= 1
        out, imgs, pool, pidx = [], [], [], {}
        for sk, kind, lst in chosen:
            seen_pose = {}
            for k, d in enumerate(lst):
                pose = d["pose"] or ("pose %d" % (k + 1) if len(lst) > 1 else "")
                seen_pose[pose] = seen_pose.get(pose, 0) + 1
                if seen_pose[pose] > 1:                           # (the same pose in another palette or flipped)
                    pose += " (alt %d)" % seen_pose[pose]
                ps = []
                for p in d["pieces"][:12]:
                    b = (p["img"].size, p["img"].tobytes())
                    if b not in pidx:
                        pidx[b] = len(pool)
                        pool.append(p["img"])
                    ps.append([p["dx"], p["dy"], p["tile"], p["bank"], p["xf"], p["yf"], p["slot"], p["i"], pidx[b]])
                out.append(dict(kind=kind, pose=pose, name=kind + (": " + pose if pose else ""), slots=sorted({p["slot"] for p in d["pieces"]}),
                                entries=len(d["pieces"]), h=d["h"], pieces=ps, seen=d["n"], w=d["img"].width, hh=d["img"].height))
                imgs.append(d["img"])
        return out, dict(objs=imgs, pool=pool)
