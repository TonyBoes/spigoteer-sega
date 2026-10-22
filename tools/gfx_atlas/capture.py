"""Sample a running ROM over a window of frames and reduce what the video hardware shows to plain data.

Everything here only READS the emulator (palette RAM through PyBoy's own BCPS/BCPD ports with the index put back, VRAM, OAM, the
LCD registers); it changes no game state.
"""
import hashlib

SW, SH = 160, 144
DMG_SHADES = [(255, 255, 255), (153, 153, 153), (85, 85, 85), (0, 0, 0)]   # PyBoy's DMG greys: what the DMG screenshots use


def rgb555_to_rgb(c):
    """The colour PyBoy draws for a 15-bit word (red in bits 0-4): each channel << 3, exactly as its screenshots do."""
    return ((c & 31) << 3, ((c >> 5) & 31) << 3, ((c >> 10) & 31) << 3)


def read_cgb_pal(m, obj):
    """The 8 palettes x 4 colours (RGB555 words) of palette RAM, by the BCPS/BCPD (OCPS/OCPD) ports; the index register is restored."""
    idx, data = (0xFF6A, 0xFF6B) if obj else (0xFF68, 0xFF69)
    keep = m[idx]
    out = []
    for p in range(8):
        cols = []
        for c in range(4):
            m[idx] = p * 8 + c * 2
            lo = m[data]
            m[idx] = p * 8 + c * 2 + 1
            cols.append(lo | (m[data] << 8))
        out.append(tuple(cols))
    m[idx] = keep
    return out


class Sample:
    """One sampled frame: registers, palettes, tile data (hashes only; the data of the kept frame is read on demand), the screen's cells, OAM."""
    __slots__ = ("t", "regs", "bgpal", "objpal", "vram", "maps", "oam", "tilehash", "cells", "winmask", "image")


def take(rom, cgb, t, image=None):
    pb = rom.pb
    m = pb.memory
    s = Sample()
    s.t = t
    s.regs = dict(LCDC=m[0xFF40], SCY=m[0xFF42], SCX=m[0xFF43], WY=m[0xFF4A], WX=m[0xFF4B], BGP=m[0xFF47], OBP0=m[0xFF48], OBP1=m[0xFF49])
    s.bgpal = read_cgb_pal(m, False) if cgb else None
    s.objpal = read_cgb_pal(m, True) if cgb else None
    v0 = bytes(m[0x8000:0x9800])
    v1 = bytes(m[1, 0x8000:0x9800]) if cgb else b""
    s.vram = (v0, v1)
    s.tilehash = ([hashlib.md5(v0[i * 16:i * 16 + 16]).digest()[:6] for i in range(384)],
                  [hashlib.md5(v1[i * 16:i * 16 + 16]).digest()[:6] for i in range(384)] if cgb else None)
    # tile maps: 0x9800 and 0x9C00, ids (bank 0) and attributes (bank 1)
    ids = [bytes(m[0x9800:0x9C00]), bytes(m[0x9C00:0x9FFF]) + bytes([m[0x9FFF]])]
    if cgb:
        att = [bytes(m[1, 0x9800:0x9C00]), bytes(m[1, 0x9C00:0x9FFF]) + bytes([m[1, 0x9FFF]])]
    else:
        att = [bytes(1024), bytes(1024)]
    s.maps = (ids, att)
    raw = bytes(m[0xFE00:0xFEA0])
    s.oam = [(raw[i], raw[i + 1], raw[i + 2], raw[i + 3]) for i in range(0, 160, 4)]
    s.image = image
    s.cells = None
    return s


def slot_of(tid, lcdc):
    """The VRAM tile slot (0-383) a BG/window map id names: LCDC bit 4 set = ids 0-255 at 0x8000; clear = signed ids around 0x9000."""
    if lcdc & 0x10:
        return tid
    return 256 + tid if tid < 128 else tid


def _entry(s, mp, mx, my, layer):
    ids, att = s.maps
    i = (my & 31) * 32 + (mx & 31)
    a = att[mp][i]
    return (slot_of(ids[mp][i], s.regs["LCDC"]), (a >> 3) & 1, a & 7, (a >> 5) & 1, (a >> 6) & 1, (a >> 7) & 1, layer)


def screen_cells(s):
    """(grid, used): the 18x20 grid of what sits under each 8x8 screen cell's centre pixel, as (slot, bank, pal, xflip, yflip, prio, layer)
    tuples (layer "b" background, "w" window; None where the BG is off on a DMG), and `used`, the set of (layer, bank, slot) of every map
    entry that shows at least one pixel (BG tiles partly scrolled in count; BG tiles wholly under the window do not). A third value, `usedpal`,
    is the set of (bank, slot, palette) of the same entries (the palette each tile is drawn with)."""
    r = s.regs
    lcdc = r["LCDC"]
    bgmap = 1 if lcdc & 0x08 else 0
    winmap = 1 if lcdc & 0x40 else 0
    wy, wx = r["WY"], r["WX"] - 7
    win_on = bool(lcdc & 0x20) and wy < SH and wx < SW
    scx, scy = r["SCX"], r["SCY"]
    cgb = s.bgpal is not None
    bg_on = cgb or bool(lcdc & 0x01)
    used = set()
    usedpal = set()

    def in_win(px, py):
        return win_on and py >= wy and px >= wx

    grid = []
    for cy in range(18):
        row = []
        for cx in range(20):
            px, py = cx * 8 + 4, cy * 8 + 4
            if in_win(px, py):
                row.append(_entry(s, winmap, (px - wx) >> 3, (py - wy) >> 3, "w"))
            elif bg_on:
                row.append(_entry(s, bgmap, (px + scx) >> 3, (py + scy) >> 3, "b"))
            else:
                row.append(None)
        grid.append(row)
    if bg_on:
        for ty in range(19):
            for tx in range(21):
                x0, y0 = tx * 8 - (scx & 7), ty * 8 - (scy & 7)
                if x0 >= SW or y0 >= SH:
                    continue
                if win_on and x0 >= wx and y0 >= wy:
                    continue                                         # wholly under the window
                e = _entry(s, bgmap, (scx >> 3) + tx, (scy >> 3) + ty, "b")
                used.add((e[6], e[1], e[0]))
                usedpal.add((e[1], e[0], e[2]))
    if win_on:
        for ty in range(((SH - wy) + 7) // 8):
            for tx in range(((SW - wx) + 7) // 8):
                e = _entry(s, winmap, tx, ty, "w")
                used.add((e[6], e[1], e[0]))
                usedpal.add((e[1], e[0], e[2]))
    return grid, used, usedpal


def oam_objects(s):
    """Visible OAM entries as dicts, plus their tile slots (8x16: the even tile and the odd one) and the per-scanline counts."""
    tall = bool(s.regs["LCDC"] & 0x04)
    h = 16 if tall else 8
    out = []
    lines = [0] * SH
    for i, (y, x, t, f) in enumerate(s.oam):
        sy, sx = y - 16, x - 8
        vis = (y > 0 and y < 160 and x > 0 and x < 168)
        slots = [t & 0xFE, t | 1] if tall else [t]
        out.append(dict(i=i, x=sx, y=sy, tile=t, flags=f, pal=f & 7, bank=(f >> 3) & 1, dmgpal=(f >> 4) & 1, xflip=(f >> 5) & 1, yflip=(f >> 6) & 1,
                        prio=(f >> 7) & 1, visible=vis, slots=slots))
        if vis:
            for ly in range(max(0, sy), min(SH, sy + h)):
                lines[ly] += 1
    return out, lines, h
