"""Numbers for NOTES.md: tiles per reveal state, palettes per view, sprites per line, path data, fog data."""
import json
import render as R
import layout
from world import STOPS, ROADS

late = layout.build()
print("== unique BG tiles on the DMG (identical 8x8 colour-index tiles merged, no flips) ==")
res = []
for p in range(0, 11):
    open_z = {"town"} | set(R.ORDER[:p]) if p else {"town"}
    # p venues revealed (0 = only the town); the story always opens a venue before its neighbour
    w = layout.apply_fog(layout.build(), open_z) if p < 10 else late
    tiles = {w.c[y][x][1] for y in range(32) for x in range(32)}
    fog = {w.c[y][x][1] for y in range(32) for x in range(32) if layout.ZONE[y][x] not in open_z}
    res.append(len(tiles))
    print(f"  {p:2d} venues revealed: {len(tiles):3d} tiles ({len(fog)} of them in fog cells)")
print("  late (no fog):", len({late.c[y][x][1] for y in range(32) for x in range(32)}), "  worst state:", max(res))
# tiles that live only in the last zone (the space lounge): where the fog tiles could be loaded
z = layout.ZONE
others = {late.c[y][x][1] for y in range(32) for x in range(32) if z[y][x] != "lounge"}
lounge_only = {late.c[y][x][1] for y in range(32) for x in range(32) if z[y][x] == "lounge"} - others
print("tiles used only by the lounge zone (free while it is fogged):", len(lounge_only))
fogtiles = set()
for p in range(0, 10):
    open_z = {"town"} | set(R.ORDER[:p]) if p else {"town"}
    w = layout.apply_fog(layout.build(), open_z)
    for y in range(32):
        for x in range(32):
            if z[y][x] not in open_z:
                fogtiles.add(w.c[y][x][1])
late_t = {late.c[y][x][1] for y in range(32) for x in range(32)}
print("fog tiles over all states:", len(fogtiles), "of which also in the late map:", len(fogtiles & late_t),
      "-> only new:", len(fogtiles - late_t))

print("== BG palettes in view ==")
for name, cam in [("town", (48, 60)), ("saloon", (0, 88)), ("igloo", (96, 0)), ("lounge", (0, 112)), ("cow", (96, 88))]:
    ps = sorted({late.c[y][x][0] for y in range(cam[1] // 8, cam[1] // 8 + 18) for x in range(cam[0] // 8, cam[0] // 8 + 20)})
    print(f"  {name}: {ps}")
worst = 0
for cy in range(0, 113, 8):
    for cx in range(0, 97, 8):
        ps = {late.c[y][x][0] for y in range(cy // 8, cy // 8 + 18) for x in range(cx // 8, cx // 8 + 20)}
        worst = max(worst, len(ps))
print("  most palettes in any view:", worst, " (the tag row uses palette 0, the panels palette 5: both already in the set)")

print("== sprites per scanline (8x16 mode: every object covers 16 lines) ==")
# objects: dots 1, Sal 2, UFO 3, '!' 1, arrows 1 each
worst, where = 0, None
for here in STOPS:
    sx, sy = R.sal_xy(STOPS[here])
    objs = []
    for n, c in STOPS.items():
        if n != here:
            objs.append((c[0] * 8, c[1] * 8, 8))
    objs += [(44, 188, 24), (156, 126, 8), (sx, sy, 16)]
    for d in R.LEGS[here]:
        ax, ay = {"R": (sx + 17, sy + 4), "L": (sx - 9, sy + 4), "U": (sx + 4, sy - 7), "D": (sx + 4, sy + 17)}[d]
        objs.append((ax, ay, 8))
    for cy in range(0, 113, 4):
        for cx in range(0, 97, 4):
            for line in range(144):
                n = 0
                for (x, y, w) in objs:
                    sxs, sys_ = x - cx, y - cy
                    if sys_ <= line < sys_ + 16 and sxs + w > 0 and sxs < 160:
                        n += (w + 7) // 8
                if n > worst:
                    worst, where = n, (here, cx, cy, line)
print("  worst row:", worst, "objects, at", where, "(limit 10)")
# total objects
print("  objects in OAM: dots 11 + Sal 2 + UFO 3 + '!' 1 + arrows <= 3 =", 11 + 2 + 3 + 1 + 3, "(limit 40)")

print("== walk data (a leg is runs of (direction, cells)) ==")
tot = 0
legs = set()
for a, ex in R.LEGS.items():
    for d, b in ex.items():
        if (b, a) not in legs:
            legs.add((a, b))
for a, b in sorted(legs):
    s = R.segments(R.path(a, b))
    tot += len(s)
    print(f"  {a:9s}-> {b:9s} {sum(n for _, n in s):2d} cells, runs {s}")
print("  legs:", len(legs), " runs:", tot, " bytes at 1 B a run:", tot, " + 1 B a leg length + exits table", 11 * 4, "B =", tot + len(legs) + 44)
print("== map data in ROM ==")
n = len(late_t)
print(f"  tiles {n} x 16 = {n * 16} B  (+ fog tiles that are new: {len(fogtiles - late_t)} x 16 = {len(fogtiles - late_t) * 16} B)")
print("  tilemap 1024 B, CGB attribute map 1024 B (512 B as nibbles), zone map 512 B as nibbles (or 44 B as rectangles)")
