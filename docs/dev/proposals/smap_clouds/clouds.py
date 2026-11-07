"""Story-map sprite clouds, proposal (nothing in src/ or assets/).

    python3 -I docs/dev/proposals/smap_clouds/clouds.py OUTDIR      (from the repo root; needs the A5 scratch src: smap_import/build.py's first two steps)

The three cloud designs are typed by hand in clouds.txt.  This script only transcribes them into indexed PNGs, composites them over the integrated map
(smap_import/mapctx.py, read only), scales with nearest neighbour and runs checks.  Nothing here outlines, fills or shades; the only transform is the hardware X flip the engine
would use.  Writes under OUTDIR: clouds_dmg.png, clouds_cgb.png, sheet_designs.png, sheet_context.png, smap_clouds_dmg_color.gif, report.txt
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "docs/dev/proposals/smap_import"))
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# ---- palettes ---------------------------------------------------------------------------------------------------------------------------------------------------
DMG_SHADE = [248, 168, 88, 24]                       # the project's preview shades (smap_world/pal.py)
OBP1 = 0x90                                          # idx1 -> shade 0 (white), idx2 -> shade 1, idx3 -> shade 2
CLOUD_DMG = [None] + [DMG_SHADE[(OBP1 >> (2 * i)) & 3] for i in (1, 2, 3)]
CLOUD_CGB = [None, (0xF8, 0xF8, 0xF8), (0xB0, 0xC8, 0xF0), (0x70, 0x90, 0xC8)]
SAL_DMG = [None, 248, 168, 24]                       # OBP0 0xD0
SAL_CGB = [None, (0xF8, 0xF8, 0xF0), (0xF0, 0xB8, 0x88), (0x20, 0x20, 0x30)]


def correct(c):
    """an approximate GBC LCD colour correction (the common emulator matrix; illustrative, as the skill's figure 7 says)"""
    r, g, b = c
    return ((26 * r + 4 * g + 2 * b) // 32, (24 * g + 8 * b) // 32, (6 * r + 4 * g + 22 * b) // 32)


def rgb555(c):
    return (c[0] >> 3) | ((c[1] >> 3) << 5) | ((c[2] >> 3) << 10)


def load_grids():
    g, cur = {}, None
    for l in (HERE / "clouds.txt").read_text().split("\n"):
        if l.startswith("@"):
            cur = l[1:]
            g[cur] = []
        elif l and not l.startswith(";"):
            g[cur].append([int(c) if c != "." else 0 for c in l])
    for k, rows in g.items():
        assert len(rows) == 16 and len({len(r) for r in rows}) == 1, k
    return g


GRIDS = load_grids()
ORDER = ["A", "B", "C"]
NAMES = {"A": "A  PUFF", "B": "B  LONG", "C": "C  TOWER"}
WID = {k: len(GRIDS[k][0]) for k in ORDER}


def sheet_png(out, cgb):
    """the three clouds side by side as 8x16 columns: an indexed PNG (index 0 magenta = transparent), for the lint and the tile count"""
    cols = sum(WID[k] // 8 for k in ORDER)
    im = Image.new("P", (cols * 8, 16), 0)
    if cgb:   # CGB sprite palette: one group of four; entry 0 transparent
        pal = [(255, 0, 255)] + [CLOUD_CGB[i] for i in (1, 2, 3)]
    else:
        pal = [(255, 0, 255)] + [(CLOUD_DMG[i],) * 3 for i in (1, 2, 3)]
    im.putpalette([c for p in pal for c in p])
    x0 = 0
    for k in ORDER:
        for y, row in enumerate(GRIDS[k]):
            for x, v in enumerate(row):
                im.putpixel((x0 + x, y), v)
        x0 += WID[k]
    im.save(out)


def tiles_of():
    """unique 8x8 tiles (the lower and upper halves of each column), exact and with flips merged"""
    seen, seen_f, n = set(), set(), 0
    for k in ORDER:
        for c in range(WID[k] // 8):
            for half in (0, 1):
                t = tuple(tuple(GRIDS[k][half * 8 + y][c * 8 + x] for x in range(8)) for y in range(8))
                n += 1
                seen.add(t)
                seen_f.add(min(t, tuple(r[::-1] for r in t), tuple(reversed(t)), tuple(r[::-1] for r in reversed(t))))
    return n, len(seen), len(seen_f)


# ---- the world and Sal --------------------------------------------------------------------------------------------------------------------------------------------
def worlds():
    import mapctx as M
    return M.render(True), M.render(False), M.CW * 8, M.CH * 8


def sal_frames():
    """Sal's five pictures (assets/art/bartender.txt): 16 x 24, '.' transparent, '-' 1, '+' 2, '#' 3"""
    fr, cur = [], []
    for l in (ROOT / "assets/art/bartender.txt").read_text().split("\n"):
        if l.startswith(";"):
            continue
        if not l:
            if cur:
                fr.append(cur)
            cur = []
        else:
            cur.append([{".": 0, "-": 1, "+": 2, "#": 3}[c] for c in l])
    if cur:
        fr.append(cur)
    assert all(len(f) == 24 and len(f[0]) == 16 for f in fr[:3]), [len(f) for f in fr]
    return fr


def blit(im, grid, x, y, cols, flip=False, w=None):
    """sprite pixels onto a PIL image (clipped); cols: index -> colour"""
    W, H = im.size
    w = w or len(grid[0])
    for gy, row in enumerate(grid):
        py = y + gy
        if not 0 <= py < H:
            continue
        for gx in range(w):
            v = row[w - 1 - gx] if flip else row[gx]
            px = x + gx
            if v and 0 <= px < W:
                c = cols[v]
                im.putpixel((px, py), (c, c, c) if isinstance(c, int) else c)


# World coordinates (owner, Q114: "clouds need to stay where they are in relation to map not sal").  Four lanes 128 px apart (56, 184, 312, 440: any 144-line view holds a whole lane), one cloud per lane except lane 184 (two, same speed, 210 px apart: never on one screen),
# one cloud per lane, world x = (base + clock >> shift) & 1023 with clock = the 16-bit frame count (V_TICK and one scratch byte).  The world is 512 wide, so a cloud is on the map half of
# the time.  Hidden (OAM y 0) when off the screen.  (design, world y, base x, shift: 1 px per 2^shift frames, X flip)
CLOUDS = [("A", 56, 20, 3, 0), ("C", 184, 300, 3, 0), ("B", 184, 90, 3, 1), ("B", 312, 380, 2, 0), ("A", 440, 200, 3, 1)]


def cloud_pos(i, clk, cx, cy):
    """the screen position (sx, sy) of cloud i, or None when it is off the screen (its entries get y = 0: they cost no scanline)"""
    d, wy, base, sh, fl = CLOUDS[i]
    wx = (base + (clk >> sh)) & 1023
    sx, sy = wx - cx, wy - cy
    if sx < -24 or sx >= 160 or sy <= -16 or sy >= 144:
        return None
    return sx, sy


def draw_clouds(im, clk, cx, cy, cols):
    for i, (d, wy, base, sh, fl) in enumerate(CLOUDS):
        p = cloud_pos(i, clk, cx, cy)
        if p:
            blit(im, GRIDS[d], p[0], p[1], cols, bool(fl))


def view(world, cx, cy):
    return world.crop((cx, cy, cx + 160, cy + 144))


def camera(fx, fy, ww, wh):
    return max(0, min(fx - 80, ww - 160)), max(0, min(fy - 72, wh - 144))


def draw_sal(im, fx, fy, cx, cy, pic, up, cols):
    blit(im, SAL[pic], fx - 8 - cx, fy - 24 - cy - up, cols)


# ---- labels and sheets -------------------------------------------------------------------------------------------------------------------------------------------
def font(n):
    return ImageFont.truetype(FONT, n)


def label(im, text, size=34, bg=(30, 30, 30), fg=(255, 255, 255)):
    h = size + 22
    out = Image.new("RGB", (im.width, im.height + h), bg)
    ImageDraw.Draw(out).text((12, 8), text, font=font(size), fill=fg)
    out.paste(im, (0, h))
    return out


def up(im, s):
    return im.resize((im.width * s, im.height * s), Image.NEAREST)


def stack_h(ims, gap=20, bg=(30, 30, 30)):
    o = Image.new("RGB", (sum(i.width for i in ims) + gap * (len(ims) - 1), max(i.height for i in ims)), bg)
    x = 0
    for i in ims:
        o.paste(i, (x, 0))
        x += i.width + gap
    return o


def stack_v(ims, gap=24, bg=(30, 30, 30)):
    o = Image.new("RGB", (max(i.width for i in ims), sum(i.height for i in ims) + gap * (len(ims) - 1)), bg)
    y = 0
    for i in ims:
        o.paste(i, (0, y))
        y += i.height + gap
    return o


def pad(im, w, bg=(30, 30, 30)):
    o = Image.new("RGB", (max(w, im.width), im.height), bg)
    o.paste(im, (0, 0))
    return o


def design_panel(cgb, ground, scale=8):
    """the three designs, each alone, on a flat ground, x8"""
    cols = CLOUD_CGB if cgb else CLOUD_DMG
    ims = []
    for k in ORDER:
        im = Image.new("RGB", (WID[k] + 4, 20), ground)
        blit(im, GRIDS[k], 2, 2, cols)
        ims.append(up(im, scale))
    return stack_h(ims, gap=16)


def pair_panel(cgb, ground):
    """A, B and C each flipped, x8: the engine's mirrored groups"""
    cols = CLOUD_CGB if cgb else CLOUD_DMG
    ims = []
    for k in ORDER:
        im = Image.new("RGB", (WID[k] + 4, 20), ground)
        blit(im, GRIDS[k], 2, 2, cols, True)
        ims.append(up(im, 8))
    return stack_h(ims, gap=16)


def compose_view(cgb, world, cx, cy, fx, fy, clk, pic=0, upx=0):
    im = view(world, cx, cy).copy()
    draw_sal(im, fx, fy, cx, cy, pic, upx, SAL_CGB if cgb else SAL_DMG)
    draw_clouds(im, clk, cx, cy, CLOUD_CGB if cgb else CLOUD_DMG)
    return im


def main(outdir):
    global SAL
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    SAL = sal_frames()
    sheet_png(out / "clouds_dmg.png", False)
    sheet_png(out / "clouds_cgb.png", True)
    n, uniq, uniq_f = tiles_of()
    wc, wd, WW, WH = worlds()
    rep = [f"tiles: {n} used, {uniq} unique, {uniq_f} unique with flips merged (8 sprites: A 2, B 3, C 3)",
           "cloud colours (RGB555): " + ", ".join(f"0x{rgb555(c):04X}" for c in CLOUD_CGB[1:]) + "; DMG OBP1 = 0x%02X" % OBP1]

    # ---- sheet 1: the designs ----
    grass, water = (176, 208, 128), (88, 160, 216)
    rows = []
    rows.append(stack_h([label(design_panel(False, (248,)*3), "DMG ON WHITE GROUND", 38), label(design_panel(True, grass), "COLOR ON GRASS", 38)]))
    rows.append(stack_h([label(design_panel(False, (88,)*3), "DMG OVER WATER", 38), label(design_panel(True, water), "COLOR OVER WATER", 38)]))
    rows.append(stack_h([label(pair_panel(False, (248,)*3), "DMG X FLIPPED, SAME TILES", 38), label(pair_panel(True, (240, 224, 144)), "COLOR X FLIPPED ON SAND", 38)]))
    def corr_panel(ground):
        ims = []
        for k in ORDER:
            im = Image.new("RGB", (WID[k] + 4, 20), correct(ground))
            blit(im, GRIDS[k], 2, 2, [None] + [correct(c) for c in CLOUD_CGB[1:]])
            ims.append(up(im, 8))
        return stack_h(ims, gap=16)
    rows.append(stack_h([label(corr_panel(grass), "CORRECTED: GRASS", 38), label(corr_panel(water), "CORRECTED: WATER", 38)]))
    # 1x beside the quality bar (the igloo and its penguin) and Sal: native size, the clouds as they sit on the map
    crops = []
    for cgb, w_ in ((False, wd), (True, wc)):
        im = w_.crop((400, 8, 504, 64)).copy()                         # the igloo, the penguin, snow
        blit(im, GRIDS["C"], 6, 2, CLOUD_CGB if cgb else CLOUD_DMG)
        blit(im, GRIDS["A"], 70, 28, CLOUD_CGB if cgb else CLOUD_DMG, True)
        sal = Image.new("RGB", (20, 26), (248, 248, 248) if not cgb else (176, 208, 128))
        draw_sal(sal, 10, 25, 0, 0, 0, 0, SAL_CGB if cgb else SAL_DMG)
        strip = Image.new("RGB", (im.width + 8 + sal.width, max(im.height, sal.height)), (30, 30, 30))
        strip.paste(im, (0, 0))
        strip.paste(sal, (im.width + 8, 0))
        crops.append(strip)
    rows.append(stack_h([label(pad(crops[0], 640), "DMG 1X BY THE IGLOO", 38), label(pad(crops[1], 640), "COLOR 1X BY THE IGLOO", 38)]))
    sheet = stack_v([label(stack_v(rows, gap=30), "STORY-MAP SPRITE CLOUDS: THREE DESIGNS", 46, bg=(70, 40, 90))], gap=0)
    sheet.save(out / "sheet_designs.png")
    rep.append(f"sheet_designs.png {sheet.size}")

    # ---- sheet 2: in context x3 (world clouds at the clock value shown) ----
    views = [("TOWN: SAL AT THE TOWN STOP", 296, 236, 0),
             ("IGLOO: SNOW, THE DMG WORST CASE", 424, 100, 3040),
             ("FACTORY: SAL AT THE FACTORY, RIVER", 432, 372, 0)]
    vrows = []
    for title, fx, fy, clk in views:
        cx, cy = camera(fx, fy, WW, WH)
        pair = []
        for cgb, w_ in ((False, wd), (True, wc)):
            im = compose_view(cgb, w_, cx, cy, fx, fy, clk)
            pair.append(label(up(im, 3), "DMG" if not cgb else "COLOR", 36))
        vrows.append(label(stack_h(pair), title, 38, bg=(70, 40, 90)))
    sheet2 = stack_v(vrows, gap=30)
    sheet2.save(out / "sheet_context.png")
    rep.append(f"sheet_context.png {sheet2.size}")

    # ---- the GIF: DMG left, Color right; Sal stands at the town, walks west to the saloon, north on the west road to the stadium, stands.  The camera scrolls 296 -> 0 and 164 -> 28. ----
    path = [(296, 236), (43, 236), (8, 236), (8, 100), (80, 100)]
    frames = []
    seq = [1, 0, 2, 0]
    pos = list(map(float, path[0]))
    leg, phase, ph_t = 0, 0, 0
    total = 100 + 250 + 100
    over_sal, max_cloud_line, cam_span = 0, 0, [999, -1, 999, -1]
    for t in range(total):
        walking = 100 <= t and leg < len(path) - 1
        pic, upx = 0, 0
        if walking:
            tx, ty = path[leg + 1]
            dx, dy = tx - pos[0], ty - pos[1]
            step = min(2, max(abs(dx), abs(dy)))
            pos[0] += step * (dx > 0) - step * (dx < 0)
            pos[1] += step * (dy > 0) - step * (dy < 0)
            if abs(tx - pos[0]) < 1 and abs(ty - pos[1]) < 1:
                leg += 1
            ph_t += 1
            if ph_t >= 10:
                ph_t = 0
                phase = (phase + 1) & 3
            pic, upx = seq[phase], phase & 1
        else:
            phase = ph_t = 0
        fx, fy = int(pos[0]), int(pos[1])
        cx, cy = camera(fx, fy, WW, WH)
        cam_span = [min(cam_span[0], cx), max(cam_span[1], cx), min(cam_span[2], cy), max(cam_span[3], cy)]
        ssx, ssy = fx - 8 - cx, fy - 24 - cy                     # Sal's art box 16 x 24 (his entries 32 lines tall)
        lines = {}
        hit = False
        for i in range(len(CLOUDS)):
            p = cloud_pos(i, t, cx, cy)
            if p:
                n = len(GRIDS[CLOUDS[i][0]][0]) // 8
                for y in range(max(0, p[1]), min(144, p[1] + 16)):
                    lines[y] = lines.get(y, 0) + n
                if p[0] < ssx + 16 and p[0] + 8 * n > ssx and p[1] < ssy + 32 and p[1] + 16 > ssy:
                    hit = True
        over_sal += hit
        max_cloud_line = max([max_cloud_line] + list(lines.values()))
        if t % 3 == 0:
            pair = []
            for cgb, w_ in ((False, wd), (True, wc)):
                pair.append(up(compose_view(cgb, w_, cx, cy, fx, fy, t, pic, upx), 3))
            lab = [label(pair[0], "DMG", 36), label(pair[1], "COLOR", 36)]
            frames.append(stack_h(lab))
    rep.append(f"gif frames {len(frames)} ({total} game frames, 3 per frame, 50 ms = 60 fps), size {frames[0].size}; camera x {cam_span[0]}..{cam_span[1]}, y {cam_span[2]}..{cam_span[3]}; "
               f"most cloud entries on one line {max_cloud_line}; frames with a cloud over Sal's sprite {over_sal}")
    q = [f.quantize(colors=96, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for f in frames]
    q[0].save(out / "smap_clouds_dmg_color.gif", save_all=True, append_images=q[1:], duration=50, loop=0, optimize=True)
    rep.append("gif bytes %d" % (out / "smap_clouds_dmg_color.gif").stat().st_size)
    (out / "report.txt").write_text("\n".join(rep) + "\n")
    print("\n".join(rep))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "out/smap_clouds"))
