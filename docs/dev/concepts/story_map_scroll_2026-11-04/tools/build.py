"""Build every preview of the concept into ../ (run from anywhere: python3 tools/build.py)."""
import json
import sys
from pathlib import Path

from PIL import Image, ImageChops

import render as R
from render import OUT, STOPS, LEGS, TAG, frame, scale, stack, side, path, segments, sal_xy, view_cam, clampcam, IMG

ALL = set(STOPS)


def full_map(state, mode):
    """the whole 256 x 256 map as the player would see it with every sprite on it (Sal at the town)"""
    rev = R.EARLY_REV if state == "early" else ALL
    big = IMG[(state, mode)].copy()
    for name, c in STOPS.items():
        if name in rev:
            R.blit(big, R.SP["dot_open"], c[0] * 8, c[1] * 8, mode)
    if "lounge" in rev:
        R.blit(big, R.SP["ufo"], 44, 188, mode)
    if state == "late":
        R.blit(big, R.SP["bang"], 156, 126, mode)
    if state == "early":
        c = STOPS["lodge"]
        R.blit(big, R.SP["dot_locked"], c[0] * 8, c[1] * 8, mode)
    sx, sy = sal_xy(STOPS["town"])
    R.blit(big, R.SP["sal"], sx, sy, mode)
    return big


def views():
    out = {}
    spec = [("town_early", "early", "town", (0, -44), None, R.EARLY_REV, False),
            ("saloon_desert", "late", "saloon", (0, 0), "saloon", ALL, False),
            ("igloo_edge", "late", "igloo", (0, 0), "igloo", ALL, False),
            ("lounge_corner", "late", "lounge", (0, 0), "lounge", ALL, False),
            ("cow_east", "late", "cow", (0, 0), "cow", ALL, True)]
    for key, state, stop, bias, tag, rev, bang in spec:
        cam = view_cam(STOPS[stop], bias)
        ims = []
        for m in ("cgb", "dmg"):
            sx, sy = sal_xy(STOPS[stop])
            ims.append(frame(state, m, cam, sal=(sx, sy), here=stop, tick=0, text=TAG[stop] if tag else None, text_y=0,
                             revealed=rev, bang=bang or (state == "late" and stop == "town"),
                             peek=("lodge",) if state == "early" else ()))
        out[key] = (cam, ims)
    return out


def walk(mode, state="early", rev=None):
    """Sal walks from the town to the saloon (60 fps game frames, 3 px a frame; the camera follows by a quarter of the gap, at most
    4 px a frame, at least 1 px); on arrival the name tag slides in, holds 90 frames, slides out. Returns every 2nd game frame."""
    rev = rev or R.EARLY_REV
    cells = path("town", "saloon")
    pts = []
    for a, b in zip(cells, cells[1:]):
        for k in range(8):
            pts.append((a[0] * 8 + (b[0] - a[0]) * k, a[1] * 8 + (b[1] - a[1]) * k))
    pts.append((cells[-1][0] * 8, cells[-1][1] * 8))
    frames, log = [], []
    cam = list(clampcam(pts[0][0] - 4 + 8 - 80, pts[0][1] - 6 + 8 - 72))
    sal = pts[0]
    idx = 0
    t_hold, total = 60, 240
    arrive_t = None
    prev = None
    for t in range(total):
        walking = t >= t_hold and idx < len(pts) - 1
        if walking:
            idx = min(len(pts) - 1, idx + 3)
            sal = pts[idx]
            if idx == len(pts) - 1:
                arrive_t = t
        here = None
        if idx == 0 and not walking:
            here = "town"
        elif idx == len(pts) - 1:
            here = "saloon"
        sx, sy = sal[0] - 4, sal[1] - 6
        tgt = clampcam(sx + 8 - 80, sy + 8 - 72)
        for k in (0, 1):
            d = tgt[k] - cam[k]
            step = d >> 2 if abs(d) >= 4 else (1 if d > 0 else -1 if d < 0 else 0)
            step = max(-4, min(4, step))
            cam[k] += step
        text, ty = None, 0
        if arrive_t is not None:
            e = t - arrive_t
            if 4 <= e < 10:
                text, ty = TAG["saloon"], -8 + (e - 3) * 8 // 6
            elif 10 <= e < 100:
                text, ty = TAG["saloon"], 0
            elif 100 <= e < 106:
                text, ty = TAG["saloon"], -((e - 99) * 8 // 6)
        if t % 2 == 0:
            im = frame(state, mode, tuple(cam), sal=(sx, sy), sal_flip=True if walking or here == "saloon" else False, here=here,
                       walking=walking, tick=t, text=text, text_y=ty, revealed=rev, peek=("lodge",))
            frames.append(im)
            log.append((t, tuple(cam), (sx, sy), text is not None))
    return frames, log


def save_gif(frames, path_, k=3, ms=33):
    fr = [scale(f, k).convert("P", palette=Image.ADAPTIVE, colors=64, dither=Image.NONE) for f in frames]
    fr[0].save(path_, save_all=True, append_images=fr[1:], duration=ms, loop=0, optimize=False, disposal=1)


def atlas():
    """every piece I drew by hand, on one indexed sheet (palette * 4 + colour), for the lint and for looking at"""
    import kit
    from world import PAL
    items = [(1, kit.ROAD[k]) for k in sorted(kit.ROAD)]
    items += [(0, kit.FOG[k]) for k in ("F", "PA", "EN", "CNW", "INW")] + [(0, kit.MOUND)]
    items += [(4, kit.BUNT["A"]), (4, kit.BUNT["B"]), (4, kit.COBBLE["1"]), (3, kit.FENCE)]
    big = [(4, kit.HOUSE), (4, kit.TOWER), (4, kit.HALL), (1, kit.HANGAR), (1, kit.RUNWAY["D"]), (1, kit.RUNWAY["P"])]
    W = 16 * 8
    rows_needed = (len(items) + 15) // 16
    im = Image.new("P", (W, rows_needed * 8 + 40 + 16 + 40 + 16 + 8), 0)
    flat = [c for p in PAL for col in p for c in col]
    im.putpalette(flat)
    for i, (pal, rows) in enumerate(items):
        for j, r in enumerate(rows):
            for k, ch in enumerate(r):
                im.putpixel(((i % 16) * 8 + k, (i // 16) * 8 + j), pal * 4 + int(ch))
    y = rows_needed * 8
    x = 0
    for pal, rows in big:
        h, w = len(rows), len(rows[0])
        if x + w > W:
            x, y = 0, y + 32 + 8
        for j, r in enumerate(rows):
            for k, ch in enumerate(r):
                im.putpixel((x + k, y + j), pal * 4 + (int(ch) if ch != "." else 0))
        x += w
    im.save(OUT / "master" / "my_hand_drawn_pieces.png")
    d = im.copy()
    px = d.load()
    for yy in range(d.height):
        for xx in range(d.width):
            px[xx, yy] = px[xx, yy] % 4
    d.putpalette([c for s_ in R.world.DMG_SHADE for c in (s_, s_, s_)])
    d.save(OUT / "master" / "my_hand_drawn_pieces_dmg.png")


def main():
    atlas()
    OUT.mkdir(exist_ok=True)
    # 0. the masters (indexed: palette * 4 + colour, as assets/story_map/map_bg_only_indexed.png; and the DMG shades)
    (OUT / "master").mkdir(exist_ok=True)
    for st, w in (("late", R.LATE), ("early", R.EARLY)):
        w.pic().save(OUT / "master" / f"map_{st}_indexed.png")
        d = w.pic().copy()
        px = d.load()
        for y in range(256):
            for x in range(256):
                px[x, y] = px[x, y] % 4
        d.putpalette([c for s_ in R.world.DMG_SHADE for c in (s_, s_, s_)])
        d.save(OUT / "master" / f"map_{st}_dmg_indexed.png")
    # 1. the full maps
    maps = {}
    for st in ("early", "late"):
        for m in ("cgb", "dmg"):
            im = full_map(st, m)
            maps[(st, m)] = im
            scale(im, 2).save(OUT / f"map_{st}_{m}_x2.png")
    # 2. the screen views (Color over DMG, x3)
    vs = views()
    for key, (cam, ims) in vs.items():
        stack(scale(ims[0], 3), scale(ims[1], 3)).save(OUT / f"view_{key}_x3.png")
    # 3. the walk
    for m in ("cgb", "dmg"):
        fr, log = walk(m)
        save_gif(fr, OUT / f"walk_{m}.gif")
        if m == "cgb":
            json.dump(log, open(OUT / "tools" / "walk_log.json", "w"))
            WALK_FR = fr
            WLOG = log
        else:
            WALK_FR_D = fr
    # stills of the walk for the sheet
    picks = [0, 40, 52, 70]
    # 6. the contact sheet pieces
    pieces = {}
    quad = Image.new("RGB", (518, 518), (40, 40, 40))
    quad.paste(maps[("early", "cgb")], (0, 0))
    quad.paste(maps[("early", "dmg")], (262, 0))
    quad.paste(maps[("late", "cgb")], (0, 262))
    quad.paste(maps[("late", "dmg")], (262, 262))
    quad.save(OUT / "tools" / "_quad.png")
    for key, (cam, ims) in vs.items():
        side(scale(ims[0], 2), scale(ims[1], 2)).save(OUT / "tools" / f"_view_{key}.png")
    ws = []
    for p in picks:
        ws.append(side(scale(WALK_FR[p], 1), scale(WALK_FR_D[p], 1)))
    strip = Image.new("RGB", (ws[0].width * 2 + 6, ws[0].height * 2 + 6), (40, 40, 40))
    for i, w in enumerate(ws):
        strip.paste(w, ((i % 2) * (w.width + 6), (i // 2) * (w.height + 6)))
    strip.save(OUT / "tools" / "_walkstrip.png")
    import subprocess
    items = [f"Full map x1, Color | DMG; top row early (fog), bottom row late={OUT / 'tools' / '_quad.png'}",
             f"Screen: town early (Sal at the fountain, fog east and south), Color | DMG x2={OUT / 'tools' / '_view_town_early.png'}",
             f"Screen: desert, Sal at the saloon with the name tag, Color | DMG x2={OUT / 'tools' / '_view_saloon_desert.png'}",
             f"Screen: north-east edge, the igloo, Color | DMG x2={OUT / 'tools' / '_view_igloo_edge.png'}",
             f"Screen: south-west corner, UFO, mountain, air base, Color | DMG x2={OUT / 'tools' / '_view_lounge_corner.png'}",
             f"Walk town to saloon, frames 0 / 40 / 52 / 70 (x1), Color | DMG; the GIFs are walk_cgb.gif, walk_dmg.gif={OUT / 'tools' / '_walkstrip.png'}"]
    subprocess.run([sys.executable, str(R.ROOT / "tools" / "dev" / "contact_sheet.py"), str(OUT / "sheet.png"), "--scale", "1", "--cols", "1",
                    "--title", "Story map, direction A: one scrolling 256x256 map (concept 2026-11-04, nothing imported)"] + items, check=True)
    print("ok")


if __name__ == "__main__":
    main()
