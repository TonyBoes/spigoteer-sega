"""Reduce a list of capture.Sample to one screen's atlas record (JSON-able) and write its PNG assets."""
import io
import re
from collections import Counter
from pathlib import Path

from PIL import Image

import capture as C

ROOT = Path(__file__).resolve().parent.parent.parent


def _defs():
    art = (ROOT / "build" / "art.h").read_text()
    return {m.group(1): int(m.group(2)) for m in re.finditer(r"#define (\w+) (\d+)", art)}


def regions():
    """The documented tile-id layout of a LEVEL screen as non-overlapping VRAM slot ranges (src/game.h, tools/gen_art.py, build/art.h).
    Slots 0-127 are OBJ ids 0-127; slots 128-255 are ids 128-255 (BG and OBJ share them); slots 256-383 are BG ids 0-127 (signed mode, 0x9000)."""
    d = _defs()
    mug, glass, fill, drink, coin, dancer = (d[k] for k in ("MUG_TILE_COUNT", "GLASS_TILE_COUNT", "MUG_FILL_TILE_COUNT", "MUG_DRINK_TILE_COUNT",
                                                            "COIN_TILE_COUNT", "DANCER_TILE_COUNT"))
    bt = 56                                              # OBJ_BT_END (src/game.h)
    o = bt
    reg = [
        (0, bt - 17, "OBJ ids 0-39: Sal, the bartender (5 frames x 8)", "obj", "perm"),
        (bt - 16, bt - 1, "OBJ ids 40-55: free", "free", "free"),
    ]
    reg[0] = (0, 39, reg[0][2], "obj", "perm")
    for n, label, kind in ((mug, "mug (full, empty)", "venue"), (glass, "breaking glass", "venue"), (fill, "fill glass (4 frames)", "venue"),
                           (drink, "drink in a patron's hand", "venue"), (coin, "tip coin", "perm"), (dancer, "show: dancers (4 frames)", "venue")):
        reg.append((o, o + n - 1, "OBJ ids %d-%d: %s" % (o, o + n - 1, label), "obj", kind))
        o += n
    pf, pn, pb = d["PATRON_FIRST_TILE"], d["PATRON_GROUP_TILES"], d["PATRON_TILES_PER_GROUP"]
    pend = pf + pn - 1
    back = pf + pb
    reg += [
        (128, back - 1, "ids 128-%d: patrons, shifted poses (BG; shift-0 poses double as lifted-patron OBJ)" % (back - 1), "patron", "venue"),
        (back, pend, "ids %d-%d: patrons, back views (BG)" % (back, pend), "patron", "venue"),
        (pend + 1, 239, "ids %d-239: perfect-pour sparkle / overflow / cue (OBJ, story)" % (pend + 1), "obj", "venue"),
        (240, 245, "OBJ ids 240-245: DMG bit-plane copies of the mugs", "obj", "venue"),
        (246, 255, "ids 246-255: mirror copies (CLASSIC), dust puff", "obj", "venue"),
        (256, 256 + d["VENUE_POOL"] - 1, "BG ids 0-%d: venue pool (stage from 0 up, bar + floor packed at the top)" % (d["VENUE_POOL"] - 1), "pool", "venue"),
        (256 + d["TILE_GENERIC_BASE"], 256 + d["BAR_TILE_COUNT"] - 1,
         "BG ids %d-%d: shared HUD, glyphs, panels" % (d["TILE_GENERIC_BASE"], d["BAR_TILE_COUNT"] - 1), "shared", "perm"),
        (256 + d["BAR_TILE_COUNT"], 256 + pf - 1, "BG id %d: spare (title text starts here)" % d["BAR_TILE_COUNT"], "free", "free"),
        (256 + pf, 383, "BG ids %d-127: patrons, shifted poses (BG)" % pf, "patron", "venue"),
    ]
    reg.sort(key=lambda r: r[0])
    # the 96..127 range ends the OBJ block; make sure the table has no holes or overlaps
    last = -1
    for lo, hi, *_ in reg:
        assert lo == last + 1, (lo, last, reg)
        last = hi
    assert last == 383, last
    return [dict(lo=lo, hi=hi, label=lab, kind=kind, scope=scope) for lo, hi, lab, kind, scope in reg]


REGIONS = regions()


def rgb(c):
    return C.rgb555_to_rgb(c)


def hexcol(c):
    r, g, b = rgb(c)
    return "#%02x%02x%02x" % (r, g, b)


def tile_pixels(data16):
    """8x8 colour indices from 16 bytes of 2bpp data."""
    out = []
    for y in range(8):
        lo, hi = data16[y * 2], data16[y * 2 + 1]
        out.append([((lo >> (7 - x)) & 1) | (((hi >> (7 - x)) & 1) << 1) for x in range(8)])
    return out


def save_png(im, path):
    """Smallest lossless PNG: palette mode when the picture has 256 colours or fewer."""
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = im.convert("RGB").getcolors(1 << 16)
    if cols is not None and len(cols) <= 256:
        pal = sorted(c for _, c in cols)
        idx = {c: i for i, c in enumerate(pal)}
        flat = [c for p in pal for c in p]
        out = Image.new("P", im.size)
        out.putpalette(flat)
        out.putdata([idx[p] for p in im.convert("RGB").getdata()])
        im = out
    im.save(path, optimize=True)


def sheet_image(vram, shades, tint=None):
    """384 tiles, 16 per row. shades: 4 RGB for colour indices; tint: {slot: 4 RGB} to colour a tile with its palette instead."""
    im = Image.new("RGB", (128, 192))
    px = im.load()
    for s in range(384):
        cols = (tint or {}).get(s, shades)
        t = tile_pixels(vram[s * 16:s * 16 + 16])
        ox, oy = (s % 16) * 8, (s // 16) * 8
        for y in range(8):
            for x in range(8):
                px[ox + x, oy + y] = cols[t[y][x]]
    return im


def dmg_palette(reg):
    """BGP / OBP value -> the 4 shade indices (colour index 0..3 -> shade 0..3)."""
    return [(reg >> (2 * i)) & 3 for i in range(4)]


def analyze(samples, model, assets, rel, key, step):
    """samples: list of capture.Sample. assets: Path of the output dir. rel: "img/<key>" stem. Returns (record, sidecar)."""
    cgb = model == "cgb"
    n = len(samples)
    # ---- per-sample reductions -------------------------------------------------------------------------------------------------
    per = []
    for s in samples:
        grid, used = C.screen_cells(s)
        objs, lines, h = C.oam_objects(s)
        vis = [o for o in objs if o["visible"]]
        per.append(dict(grid=grid, used=used, objs=objs, vis=vis, lines=lines, h=h, peak=max(lines)))
    # representative frame: the one showing the most sprites (the first of them), else the first
    rep = max(range(n), key=lambda i: (len(per[i]["vis"]), -i))
    R, RP = samples[rep], per[rep]
    nsamp = n

    # ---- registers over the window ----------------------------------------------------------------------------------------------
    regs = {}
    for k in ("LCDC", "SCX", "SCY", "WX", "WY"):
        vals = [s.regs[k] for s in samples]
        regs[k] = dict(first=vals[0], values=sorted(set(vals))[:12], n_values=len(set(vals)))

    rec = dict(model=model, samples=n, step=step, rep_sample=rep, rep_frame=R.t, lcdc=R.regs["LCDC"], obj_h=RP["h"],
               signed_bg=not (R.regs["LCDC"] & 0x10), regs=regs, window_on=bool(R.regs["LCDC"] & 0x20), bg_map=0x9C00 if R.regs["LCDC"] & 8 else 0x9800)

    # ---- CGB palettes -----------------------------------------------------------------------------------------------------------
    pal_used_frames = {("bg", p): 0 for p in range(8)}
    pal_used_frames.update({("obj", p): 0 for p in range(8)})
    pal_cells = Counter()
    pal_objs = Counter()
    for i, P in enumerate(per):
        bgp, objp = set(), set()
        for row in P["grid"]:
            for e in row:
                if e:
                    bgp.add(e[2])
        for o in P["vis"]:
            objp.add(o["pal"])
        for p in bgp:
            pal_used_frames[("bg", p)] += 1
        for p in objp:
            pal_used_frames[("obj", p)] += 1
    for row in RP["grid"]:
        for e in row:
            if e:
                pal_cells[e[2]] += 1
    for o in RP["vis"]:
        pal_objs[o["pal"]] += 1
    pal_seen = {"bg": [], "obj": []}                 # per slot: every distinct value held during the window (the summary needs more than the last one)
    if cgb:
        pals = {}
        for kind in ("bg", "obj"):
            lst = []
            for p in range(8):
                ser = [getattr(s, "bgpal" if kind == "bg" else "objpal")[p] for s in samples]
                changes = []
                last = None
                for s, v in zip(samples, ser):
                    if v != last:
                        changes.append([s.t, list(v)])
                        last = v
                pal_seen[kind].append(sorted(set(ser)))
                varying = sorted({c for v in ser for c in range(4) if v[c] != ser[0][c]})
                lst.append(dict(slot=p, unset=all(v == (0x1CE7, 0x1E19, 0x7E31, 0x217B) for v in ser), rep=list(getattr(R, "bgpal" if kind == "bg" else "objpal")[p]), first=list(ser[0]),
                                changes=changes if len(changes) > 1 else [], n_distinct=len(set(ser)), varying_colours=varying,
                                used_frames=pal_used_frames[(kind, p)], cells=pal_cells[p] if kind == "bg" else 0,
                                objs=pal_objs[p] if kind == "obj" else 0))
            pals[kind] = lst
        rec["pal"] = pals
    else:
        dm = {}
        for k in ("BGP", "OBP0", "OBP1"):
            ser = [s.regs[k] for s in samples]
            changes, last = [], None
            for s, v in zip(samples, ser):
                if v != last:
                    changes.append([s.t, v])
                    last = v
            used = 0
            if k == "BGP":
                used = sum(1 for P in per if any(e for row in P["grid"] for e in row))
            else:
                bit = 0 if k == "OBP0" else 1
                used = sum(1 for P in per if any(o["dmgpal"] == bit for o in P["vis"]))
            dm[k] = dict(rep=R.regs[k], shades=dmg_palette(R.regs[k]), changes=changes if len(changes) > 1 else [], n_distinct=len(set(ser)), used_frames=used,
                         objs=sum(1 for o in RP["vis"] if o["dmgpal"] == (0 if k == "OBP0" else 1)) if k != "BGP" else 0)
        rec["dmgpal"] = dm

    # ---- tiles ------------------------------------------------------------------------------------------------------------------
    nb = 2 if cgb else 1
    use = [[0] * 384 for _ in range(nb)]          # bit 0 BG, 1 window, 2 OBJ (union over the window)
    for P in per:
        for layer, bank, slot in P["used"]:
            if bank < nb and slot < 384:
                use[bank][slot] |= 1 if layer == "b" else 2
        for o in P["vis"]:
            for t in o["slots"]:
                use[o["bank"] if cgb else 0][t] |= 4
    banks = []
    side_hash = []
    sheet_imgs = []
    for b in range(nb):
        v = R.vram[b]
        loaded = ["1" if any(v[s * 16:s * 16 + 16]) else "0" for s in range(384)]
        changed = sorted(s for s in range(384) if len({sm.tilehash[b][s] for sm in samples}) > 1)
        # a tint per tile for the "in colour" sheet: the BG palette of its first reference in the kept frame, else the OBJ one
        tint = {}
        if cgb:
            for row in RP["grid"]:
                for e in row:
                    if e and e[1] == b and e[0] not in tint:
                        tint[e[0]] = [rgb(c) for c in R.bgpal[e[2]]]
            for o in RP["vis"]:
                if o["bank"] == b:
                    for t in o["slots"]:
                        if t not in tint:
                            tint[t] = [rgb(c) for c in R.objpal[o["pal"]]]
        else:
            bgs = [C.DMG_SHADES[x] for x in dmg_palette(R.regs["BGP"])]
            for row in RP["grid"]:
                for e in row:
                    if e and e[0] not in tint:
                        tint[e[0]] = bgs
            for o in RP["vis"]:
                sh = [C.DMG_SHADES[x] for x in dmg_palette(R.regs["OBP1" if o["dmgpal"] else "OBP0"])]
                for t in o["slots"]:
                    if t not in tint:
                        tint[t] = sh
        grey = [(255, 255, 255), (170, 170, 170), (85, 85, 85), (0, 0, 0)]
        sheet_imgs.append((sheet_image(v, grey), sheet_image(v, grey, tint)))
        # per region counts
        regc = []
        for rg in REGIONS:
            ref = sum(1 for s in range(rg["lo"], rg["hi"] + 1) if use[b][s])
            ldu = sum(1 for s in range(rg["lo"], rg["hi"] + 1) if not use[b][s] and loaded[s] == "1")
            free = sum(1 for s in range(rg["lo"], rg["hi"] + 1) if not use[b][s] and loaded[s] == "0")
            regc.append(dict(ref=ref, loaded_unused=ldu, empty=free, total=rg["hi"] - rg["lo"] + 1))
        banks.append(dict(bank=b, use="".join("%x" % x for x in use[b]),
                          loaded="".join(loaded), changed=changed, regions=regc,
                          counts=dict(ref=sum(1 for x in use[b] if x), loaded_unused=sum(1 for s in range(384) if not use[b][s] and loaded[s] == "1"),
                                      empty=sum(1 for s in range(384) if not use[b][s] and loaded[s] == "0"))))
        side_hash.append([h.hex() for h in R.tilehash[b]])
    rec["tiles"] = banks

    # ---- attribute map (CGB) / tile map (both) ----------------------------------------------------------------------------------
    rows = RP["grid"]
    rec["attr"] = dict(
        pal=["".join(str(e[2]) if e else "." for e in r) for r in rows],
        flags=["".join("%x" % ((e[3]) | (e[4] << 1) | (e[1] << 2) | (e[5] << 3)) if e else "." for e in r) for r in rows],
        layer=["".join(e[6] if e else "." for e in r) for r in rows],
        slot=[[e[0] if e else -1 for e in r] for r in rows],
    )

    # ---- sprites ----------------------------------------------------------------------------------------------------------------
    peak_i = max(range(n), key=lambda i: (per[i]["peak"], -i))
    pl = per[peak_i]["lines"]
    rec["oam"] = dict(
        table=[dict(i=o["i"], x=o["x"], y=o["y"], tile=o["tile"], pal=o["pal"], bank=o["bank"], dmgpal=o["dmgpal"], xflip=o["xflip"], yflip=o["yflip"],
                    prio=o["prio"]) for o in RP["vis"]],
        visible=len(RP["vis"]), max_visible=max(len(P["vis"]) for P in per), peak_line=max(P["peak"] for P in per),
        peak_line_y=pl.index(max(pl)), peak_sample_t=samples[peak_i].t, lines_over_10=max(sum(1 for c in P["lines"] if c > 10) for P in per),
        peak_series=[P["peak"] for P in per], visible_series=[len(P["vis"]) for P in per], rep_lines=RP["lines"], size=RP["h"])

    # ---- the screenshot and the animation ---------------------------------------------------------------------------------------
    rec["still"] = None
    imgs = [s.image for s in samples]
    moving = len({im.tobytes() for im in imgs}) > 1
    rec["animated"] = moving
    rec["anim"] = None
    if moving:
        gif = assets / (rel + ".gif")
        sel = [im.convert("RGB") for im in (imgs[::2] if n > 24 else imgs)]
        allc = sorted({c for im in sel for _, c in im.getcolors(1 << 16)})
        if len(allc) > 255:                                   # (a very colourful sequence: one shared adaptive palette)
            base = sel[0].quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
            sel = [im.quantize(palette=base, dither=Image.Dither.NONE) for im in sel]
        else:
            idx = {c: i for i, c in enumerate(allc)}
            flat = [v for c in allc for v in c]
            pf = []
            for im in sel:
                q = Image.new("P", im.size)
                q.putpalette(flat)
                q.putdata([idx[p] for p in im.getdata()])
                pf.append(q)
            sel = pf
        sel[0].save(gif, save_all=True, append_images=sel[1:], duration=int(step * 2 * 1000 / 60) if n > 24 else int(step * 1000 / 60), loop=0,
                    optimize=False)
        rec["anim"] = rel + ".gif"
    side = dict(
        bgpal=[tuple(p) for p in R.bgpal] if cgb else None, objpal=[tuple(p) for p in R.objpal] if cgb else None,
        bgpal_changes=[bool(x["changes"]) for x in rec["pal"]["bg"]] if cgb else None,
        objpal_changes=[bool(x["changes"]) for x in rec["pal"]["obj"]] if cgb else None,
        bgpal_seen=pal_seen["bg"] if cgb else None, objpal_seen=pal_seen["obj"] if cgb else None,
        bgpal_used=[x["used_frames"] > 0 for x in rec["pal"]["bg"]] if cgb else None,
        objpal_used=[x["used_frames"] > 0 for x in rec["pal"]["obj"]] if cgb else None,
        dmg={k: R.regs[k] for k in ("BGP", "OBP0", "OBP1")}, tilehash=side_hash, use=use,
        loaded=[b["loaded"] for b in banks], changed=[set(b["changed"]) for b in banks],
        still_img=R.image, sheet_imgs=sheet_imgs)
    return rec, side
