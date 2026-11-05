# The scrolling credits variant (make BUILD=out/b_scroll OUT=out/o_scroll CREDITS=SCROLL unlocked; src/credits.c "the scrolling credits").
# It is a playtest build of its own, not the default ROM: these tests skip when that ROM has not been built.
#
#   timeline  the screen holds at each stop for the frames the owner asked for (a venue: 180 band and owner, 270 regulars, 180 boss), glides between
#             stops in whole px a frame that only ever speed up and slow down, and SCY follows
#   no pops   no 8x8 cell of the picture changes except by the scroll (sprites masked: their edges move, and the boss's body rows, which are his animation);
#             a window of the cast by default, the whole roll with CREDITS_SCAN_FULL=1
import json
import os

import numpy as np
import pytest

from conftest import K_BONUS, K_CREDITS, ROOT, double_speed, hold_stage_anim, title_pick
from gbtools import Rom
from test_flow import run_until

SCROLL_ROM = ROOT / "out" / "b_scroll" / "game-unlocked.gb"
# struct cr_state's fields (scroll variant)
SCROLL, POS, NEXT, T, PH = 20, 22, 24, 26, 38
GC, GL, LIVE, K, ST = 41, 42, 44, 61, 62
HOLDS = {0: 120, 1: 180, 2: 180}                       # the title, the Spigoteer, Dregs; then per venue 180, 270, 180
VENUE_HOLDS = (180, 270, 180)

pytestmark = pytest.mark.skipif(not SCROLL_ROM.exists(), reason="the CREDITS=SCROLL ROM is not built")


def lay():
    p = ROOT / "out" / "b_scroll" / "credits_text.json"
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
    noi = (ROOT / "out" / "b_scroll" / "game-unlocked.noi").read_text()
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


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_cast_holds_and_glides_by_frames(model):
    with start(model) as gb:
        tl = holds_and_glides(gb, 1500)
        # the stops: the card index k runs 0, 1, 2 ... and each hold has the asked number of frames (the first one is cut by the frames the fade-in took)
        runs = []
        for k, st, pos, sc, sy in tl:
            if runs and runs[-1][0] == k and runs[-1][1] == st:
                runs[-1][2] += 1
            else:
                runs.append([k, st, 1])
        holds = [(k, n) for k, st, n in runs if st == 0]
        assert [k for k, n in holds][:3] == [0, 1, 2], runs
        for k, n in holds[1:3]:
            assert n == HOLDS[k] or n == HOLDS[k] + 1, (k, n)
        # a glide's speeds: whole px, up to 4, and only ever up then down; the hold is still
        prev = tl[0][2]
        sp = []
        for k, st, pos, sc, sy in tl[1:]:
            sp.append(pos - prev)
            prev = pos
        peak = sp.index(max(sp)) if max(sp) else 0
        assert max(sp) == 4 and min(sp) >= 0
        # (each glide: non-decreasing to its peak plateau then non-increasing)
        i = 0
        while i < len(sp):
            if sp[i] == 0:
                i += 1
                continue
            j = i
            while j < len(sp) and sp[j] != 0:
                j += 1
            g = sp[i:j]
            up = 0
            while up + 1 < len(g) and g[up + 1] >= g[up]:
                up += 1
            assert all(g[x + 1] <= g[x] for x in range(up, len(g) - 1)), g
            assert g[0] == 1 and g[-1] == 1 and len(g) >= 32 and len(g) <= 100, g
            i = j
        # SCY is the published scroll (it moves in the VBlank only)
        assert all(sy == sc & 255 for k, st, pos, sc, sy in tl[2:]) or sum(sy != sc & 255 for k, st, pos, sc, sy in tl[2:]) < 3


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_venue_holds_180_270_180_frames(model):
    with start(model) as gb:
        runs, last = [], None
        for _ in range(4200):
            gb.run(1)
            st = gb.read("story_scratch", 70)
            key = (st[K], st[ST])
            if last == key:
                runs[-1][2] += 1
            else:
                runs.append([key[0], key[1], 1])
            last = key
            if st[K] > 6:
                break
        holds = {k: n for k, s, n in runs if s == 0}
        for k, want in zip((3, 4, 5), VENUE_HOLDS):
            assert holds[k] in (want, want + 1), (k, holds)


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
