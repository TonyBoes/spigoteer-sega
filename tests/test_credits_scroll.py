# The scrolling credits, the game's only credits (src/credits.c "the scrolling credits"): run against the default ROM. Since 2026-11-17 the default roll is the shipped one: the shared-screen roll
# with the scene pages, ONE smooth scroll (CRFLOW=SMOOTH: no stops, no holds, no glides), set from the tune's length (owner 2026-11-13: "all one long smooth scroll matched to the song length").
#
#   timeline  the picture moves up at one constant speed (the px a frame the generator and the tune's length give), a whole px at a time, SCY follows; every venue passes in the frames its rows take
#   no pops   no 8x8 cell of the picture changes except by the scroll (sprites masked: their edges move, and the boss's body rows, which are his animation);
#             a window of the cast by default, the whole roll with CREDITS_SCAN_FULL=1
import json
import os
import re

import numpy as np
import pytest

from conftest import K_BONUS, K_CREDITS, ROM, ROOT, double_speed, hold_stage_anim, title_pick
from gbtools import Rom
from test_flow import run_until

SCROLL_ROM = ROM
# struct cr_state's fields (scroll variant)
SCROLL, POS, NEXT, T, PH = 20, 22, 24, 26, 38
GC, GL, LIVE, K, ST = 41, 42, 44, 61, 62
HOLDS = {0: 120, 1: 180, 2: 180}                       # the title, the Spigoteer, Dregs; then per venue 180, 270, 180
VENUE_HOLDS = (180, 270, 180)



def lay():
    p = ROOT / "build" / "credits_text.json"
    return json.loads(p.read_text())["layout"]


def start(model):
    if model == "cgb":
        with double_speed():                               # (the Color build runs at double speed as shipped)
            gb = Rom(SCROLL_ROM, model)
    else:
        gb = Rom(SCROLL_ROM, model)
    gb.run(120)
    hold_stage_anim(gb)
    title_pick(gb, K_BONUS, K_CREDITS)
    run_until(gb, lambda: gb.mem("story_phase") == 8, 40)
    run_until(gb, lambda: gb.read("story_scratch", 70)[LIVE] == 1, 600)       # (built behind the white, faded in once)
    return gb


def u16(st, o):
    return st[o] | st[o + 1] << 8


def holds_and_glides(gb, frames):
    """one sample per credits_update call (its entry: the state the last update left): (k, st, pos, scroll, SCY). The main loop's updates are the
    frames; a frame's picture is drawn from them, so sampling there is exact (a read after a PyBoy frame can fall before or after that frame's update)."""
    noi = ROM.with_suffix(".noi").read_text()
    v = int([l for l in noi.splitlines() if l.startswith("DEF _credits_update ")][0].split()[2], 16)
    base = gb.addr("story_scratch")
    out = []

    def cb(ctx):
        st = bytes(gb.pb.memory[base:base + 70])
        out.append((st[K], st[ST], u16(st, POS), u16(st, SCROLL), gb.pb.memory[0xFF42]))
    gb.pb.hook_register(v >> 16, v & 0xFFFF, cb, None)
    for _ in range(frames):
        gb.run(1)
    return out


def ostarts():
    """the world row each venue's scene page starts at (build/credits_text.h ct_ostart; the Color table: the DMG's cards are as tall)"""
    h = (ROOT / "build" / "credits_text.h").read_text()
    return [int(x) for x in re.search(r"ct_ostart\[10\] = \{([^}]*)\}", h).group(1).split(",")]


def speed(gb):
    """the roll's px a frame: CR->ts (8.16) as cr_flow_init computed it from the roll's length and the tune's"""
    st = gb.read("story_scratch", 70)
    return u16(st, 36) / 65536


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_roll_moves_at_one_constant_speed(model):
    """No stops: CR->k and CR->st stay 0, the timeline moves a whole px at a time (0 or 1 a frame, the speed being under 1), never stands still for 3 frames in a row, and over 1500 frames
    it goes the px the speed says (the fade in at the start aside); SCY is the published scroll."""
    with start(model) as gb:
        v = speed(gb)
        assert 0.3 < v < 0.9, v
        tl = holds_and_glides(gb, 1500)
        assert all(k == 0 and st == 0 for k, st, pos, sc, sy in tl), "no stop and no glide: one smooth scroll"
        sp = [b[2] - a[2] for a, b in zip(tl, tl[1:])]
        assert min(sp) >= 0 and max(sp) <= 1, "a whole px a frame at most"
        still = max((len(g) for g in re.findall(r"0+", "".join(str(x) for x in sp))), default=0)
        assert still <= 2, f"the picture stands still for {still} frames in a row"
        got = tl[-1][2] - tl[0][2]
        assert abs(got - v * (len(tl) - 1)) <= 3, (got, v * (len(tl) - 1))
        assert sum(sy != sc & 255 for k, st, pos, sc, sy in tl[2:]) < 3


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_each_venue_passes_in_the_frames_its_rows_take(model):
    """The frames between one scene page's top reaching the screen's top and the next one's are (their rows * 8) / the speed, to 3 frames: the same constant speed through the cards, the pages, the
    patrons and the bosses (no hold, whatever the card)."""
    os_ = ostarts()
    with start(model) as gb:
        v = speed(gb)
        first = {}
        for n in range(3400):
            gb.run(1)
            pos = u16(gb.read("story_scratch", 70), POS)
            for i in range(3):
                if i not in first and pos >= os_[i] * 8:
                    first[i] = n
            if len(first) == 3:
                break
        assert len(first) == 3, first
        for i in (0, 1):
            want = (os_[i + 1] - os_[i]) * 8 / v
            assert abs((first[i + 1] - first[i]) - want) <= 3, (i, first, want)


def sprite_mask(oam):
    m = np.zeros((144, 160), bool)
    for k in range(40):
        oy, ox = oam[4 * k], oam[4 * k + 1]
        if 0 < oy < 160 and 0 < ox < 168:
            m[max(0, oy - 16 - 4):max(0, oy + 4), max(0, ox - 8 - 3):max(0, ox + 3)] = True
    return m


def boss_bands():
    """the world px of each boss's body rows (his animation changes them: the only cells that change on the screen)"""
    L = lay()
    w = 8
    heights = [(L["H_TITLE"], L["GAP_TITLE"]), (L["H_SD"], L["G"]), (L["H_SD"], L["G"])]
    for v in range(10):
        heights += [(L["H_OWN"], L["G"]), (L["H_PAT"], L["G"]), (L["H_BOSS"], L["G"])]
    bands = []
    for i, (h, g) in enumerate(heights):
        if i >= 3 and (i - 3) % 3 == 2:
            bands.append(((w + L["R_BBODY"]) * 8, (w + L["R_BBODY"] + 2) * 8))
        w += h + g
    return bands


def scan(model, frames):
    """frame by frame, an on-screen pixel that changed other than by the scroll (the scroll's px 0..4 a frame), sprites and the boss's body masked; the list of bad frames"""
    with start(model) as gb:
        pb = gb.pb
        prev, sy_hist, oam_hist, mhist, bad, shifts = None, [0, 0], [], [], [], []
        for n in range(frames):
            pb.tick(1, True)
            st = gb.read("story_scratch", 70)
            if gb.mem("story_phase") != 8 or (st[ST] == 3 and u16(st, PH) >= 232):    # (the screen is left: the scene change's fade comes up over the end)
                break
            img = np.asarray(pb.screen.image.convert("RGB")).astype(np.int16)
            sy_hist.append(pb.memory[0xFF42])
            oam_hist.append(bytes(pb.memory[0xFE00:0xFEA0]))
            mhist.append(sprite_mask(oam_hist[-1]))
            if prev is not None and len(mhist) > 3:
                best, diffs = None, []
                scroll = u16(st, SCROLL)
                for d in range(0, 5):
                    a, b = img[0:144 - d], prev[d:144]
                    m = mhist[-1][0:144 - d] | mhist[-2][d:144] | mhist[-3][d:144]
                    diff = (np.abs(a - b).sum(axis=2) > 0) & ~m
                    diffs.append(int(diff.sum()))
                    if best is None or diff.sum() < best[1].sum():
                        best = (d, diff)
                d, diff = best
                shifts.append((d if diffs.count(min(diffs)) == 1 else None, st[ST]))       # (None: the picture looks the same at another shift: a blank screen)
                if diff.any():
                    ys, xs = np.nonzero(diff)
                    bad.append((n, d, int(diff.sum()), int(ys.min()), int(ys.max()), int(xs.min()), int(xs.max()), u16(st, SCROLL)))
            prev = img
        return bad, shifts


def near_boss(row_lo, row_hi, scroll, bands):
    for lo, hi in bands:
        y0 = lo - scroll
        if y0 - 16 < row_lo and row_hi < y0 + 40:
            return True
    return False


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_no_cell_changes_on_screen_but_by_the_scroll(model):
    full = os.environ.get("CREDITS_SCAN_FULL") == "1"
    bands = boss_bands()
    bad, shifts = scan(model, 12500 if full else 1500)
    bad = [b for b in bad if not near_boss(b[3], b[4], b[7], bands)]
    assert not bad, f"{len(bad)} frames change something: " + "; ".join("frame %s shift %s px %s rows %s-%s cols %s-%s scroll %s" % b for b in bad[:6])
    # no judder: the picture moves a whole px a frame, and a frame that stands still between two that move is a stutter
    stutter = [i for i in range(1, len(shifts) - 1) if shifts[i][0] == 0 and shifts[i - 1][0] and shifts[i + 1][0] and shifts[i - 1][1] == shifts[i][1] == shifts[i + 1][1] == 1]
    assert not stutter, f"the picture stands still for a frame inside a glide at {stutter[:8]}"
