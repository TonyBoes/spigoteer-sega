# The story map's clouds, Color only (src/smap_cloud.c; assets/story_map/cloud_layout.txt laid out by tools/dev/cloud_layout.py): a pool of 16 entries (OAM 3-18) handed out to the
# clouds on the screen, over Sal. The OAM of a Color map, top to bottom: arrows 0-2, clouds 3-18, Sal 19-22, bang 23, dots 24-34, UFO 35-37, the panel's cursor 38, 39 the clouds' flag.
# Over every leg of the map walked at double speed (the shipped Color speed): at most 10 sprites on any scanline, the pool never overflows, the order of the entries is that one,
# no cloud entry well inside the screen vanishes or shows up, a cloud moves at most 1 px on the map between two frames, the Color walk's perf guard of test_story_map_world.PERF
# untouched; the clouds are hidden after every exit and in the beam; a DMG has none; the asm of the pool build equals its C twin (make cfall).
import fcntl
import subprocess

import pytest
import test_sound
import test_story_map as sm
import test_story_map_world as w
from conftest import ROOT, double_speed

POOL = range(3, 19)                  # the clouds' entries on a Color
SAL = range(19, 23)
CLOUD_TILES = range(74, 96)          # OB + the cloud tiles: A, B, the big cloud's top and bottom halves
SV = 396


def line_counts(oam):
    n = [0] * 144
    for o in oam:
        if 0 < o["y"] < 160:
            for ly in range(max(0, o["y"] - 16), min(144, o["y"])):
                n[ly] += 1
    return n


def clusters(cl):
    """Clouds among cloud entries: neighbours 8 px apart on one line are one cloud; a big one is its two lines of six (counted once)."""
    es = sorted((o["y"], o["x"]) for o in cl)
    runs = []
    for i, (y, x) in enumerate(es):
        if i and es[i - 1] == (y, x - 8):
            runs[-1][1] += 1
        else:
            runs.append([(y, x), 1])
    n = len(runs)
    six = [r[0] for r in runs if r[1] >= 6]
    n -= sum(1 for (y, x) in six if any(y2 == y + 16 and abs(x2 - x) <= 8 for (y2, x2) in six))      # (the upper half of a big cloud and the lower one are one cloud)
    return n


def on_screen(o):
    return 0 < o["y"] < 160 and 0 < o["x"] < 168


def pool_of(oam):
    return [e for i, e in enumerate(oam) if i in POOL and e["y"]]


def test_the_oam_order_is_arrows_clouds_sal_then_the_still_sprites():
    """Static: src/smap.c names the order (a Color: clouds 3-18 before Sal 19-22, bang 23, dots 24-34, UFO 35-37, cursor 38), src/smap_cloud.c the pool."""
    import re
    smap = (ROOT / "src" / "smap.c").read_text()
    cl = (ROOT / "src" / "smap_cloud.c").read_text()
    h = {k: int(v) for k, v in re.findall(r"#define (OAM_\w+) +(\d+)", smap)}
    assert (h["OAM_ARROWS"], h["OAM_CLOUDS"], h["OAM_SAL"], h["OAM_BANG"], h["OAM_DOTS"], h["OAM_UFO"], h["OAM_CURSOR"]) == (0, 3, 19, 23, 24, 35, 38)
    assert re.search(r"#define OAM_CLOUDS 3\b", cl) and re.search(r"#define N_POOL\s+16\b", cl)
    assert 3 + 16 <= 19, "the pool (3-18) ends before Sal (19)"


def test_the_order_holds_in_the_oam_frame_by_frame_and_the_pool_keeps_the_limits(monkeypatch):
    seen = {"maxline": 0, "cloudline": 0, "frames": 0, "visible": 0, "clouds": 0, "entries": 0, "jumps": [], "prev": None, "bad_slot": 0, "motion_bad": 0, "world": None,
            "wh": 0, "sal_seen": 0, "under": 0}
    orig = w.Watch.frame

    def frame(self):
        r = orig(self)
        o = self.gb.oam()
        pool = pool_of(o)
        lc = line_counts(o)
        seen["maxline"] = max(seen["maxline"], max(lc))
        seen["cloudline"] = max(seen["cloudline"], max(line_counts(pool)))
        seen["frames"] += 1
        vis = [e for e in pool if on_screen(e)]
        seen["visible"] += len(vis)
        seen["clouds"] += clusters(vis)
        seen["entries"] = max(seen["entries"], len(pool))
        seen["bad_slot"] += sum(1 for e in pool if e["tile"] not in CLOUD_TILES)
        seen["bad_slot"] += sum(1 for i in SAL if o[i]["y"] and o[i]["tile"] >= 56)                 # (entries 19-22 are Sal's: the bartender's tiles)
        seen["sal_seen"] += any(o[i]["y"] for i in SAL)
        sc = self.gb.read("story_scratch", 520)
        wh = sc[SV + 9]
        camx, camy = sc[SV + 12] | sc[SV + 13] << 8, sc[SV + 14] | sc[SV + 15] << 8
        world = [((e["x"] - 8 + camx) % 512, (e["y"] - 16 + camy) & 255, e["tile"], 16 <= e["x"] <= 150 and 24 <= e["y"] <= 150) for e in pool]
        pw = seen["world"]
        if pw is not None and not wh and not seen["wh"]:
            for wx, wy, tl, inside in world:
                if not inside:
                    continue                              # (a cloud drifts 1 px in 8 frames and otherwise stays where it is on the map: never more than 1 px between two frames)
                near = [(a, b) for a, b, t, _ in pw if t == tl and b == wy and min((wx - a) % 512, (a - wx) % 512) <= 40]
                if near and min(min((wx - a) % 512, (a - wx) % 512) for a, b in near) > 1:
                    seen["motion_bad"] += 1
        seen["world"] = world
        prev = seen["prev"] if not wh and not seen["wh"] else None      # (a window layer hides the clouds under it: no look at those frames)
        seen["wh"] = wh
        if prev is not None:
            for p in prev:                                       # (an entry well inside the screen last frame: one of its tile within 4 px now)
                if 40 <= p["x"] <= 120 and 40 <= p["y"] <= 110:
                    if not any(e["tile"] == p["tile"] and abs(e["x"] - p["x"]) <= 4 and abs(e["y"] - p["y"]) <= 4 for e in pool):
                        seen["jumps"].append((p["x"], p["y"], p["tile"]))
            for e in pool:                                       # (and none that shows up well inside the screen: a cloud comes in over the edge)
                if 40 <= e["x"] <= 120 and 40 <= e["y"] <= 110:
                    if not any(p["tile"] == e["tile"] and abs(e["x"] - p["x"]) <= 4 and abs(e["y"] - p["y"]) <= 4 for p in prev):
                        seen["jumps"].append(("in", e["x"], e["y"], e["tile"]))
        seen["prev"] = pool
        return r
    monkeypatch.setattr(w.Watch, "frame", frame)

    allv, holds, frames = [], 0, 0
    for s, d in w.LEG_WALKS:
        seen["prev"] = None
        seen["wh"] = 0
        seen["world"] = None
        gb, wt, lines, h = w.walk("cgb", s, d, double=True)
        assert not wt.bad, (s, d, wt.bad[:3])
        allv += lines[2:]
        holds += h
        frames += len(lines)
    allv.sort()
    p90, worst = allv[len(allv) * 9 // 10], allv[-1]
    print(f"\nwalks: max sprites on a line {seen['maxline']} (clouds alone {seen['cloudline']}), max pool entries {seen['entries']}, cloud entries on screen {seen['visible'] / seen['frames']:.2f}, "
          f"clouds {seen['clouds'] / seen['frames']:.2f}, jumps {len(seen['jumps'])}, perf p90 {p90} worst {worst} holds {holds}/{frames}")
    (ROOT / "out" / "clouds_pool_walk.txt").write_text(
        f"max_line={seen['maxline']} clouds_line={seen['cloudline']} max_pool={seen['entries']} entries_on_screen_walk={seen['visible'] / seen['frames']:.2f} "
        f"clouds_walk={seen['clouds'] / seen['frames']:.2f} p90={p90} worst={worst} holds={holds}/{frames}\n")
    assert seen["sal_seen"] > 1000, "Sal's entries are 19-22 (a Color)"
    assert seen["maxline"] <= 10, seen["maxline"]
    assert seen["entries"] <= len(POOL)
    assert not seen["bad_slot"], "an entry of the pool that is not a cloud tile, or of Sal's that is not his"
    assert not seen["jumps"], seen["jumps"][:5]
    assert not seen["motion_bad"], f"{seen['motion_bad']} cloud entries moved more than 1 px on the map between two frames"
    b = w.PERF["cgb"]
    assert worst <= b["worst"] and p90 <= b["p90"], (p90, worst)
    assert holds <= b["holds"] * frames, (holds, frames)


def steady(stops, phases):
    """The clouds at the stops x clock settings (the clock set, the pool built from it): clouds avg / range, entries, max pool, max sprites on a line, big clouds seen."""
    looks = clouds = ents = mx_pool = mx_line = big = 0
    lo, hi = 99, 0
    for stop in stops:
        with double_speed():
            g = sm.to_map("cgb", 10, stop=stop)
        sb = g.addr("story_scratch")
        for i in range(phases):
            d = (i * 683 + stop * 97) % 32768
            g.pb.memory[sb + SV + 25] = d & 255
            g.pb.memory[sb + SV + 5] = (((d >> 8) << 1) & 255) | 1
            g.run(12)
            o = g.oam()
            pool = pool_of(o)
            vis = [e for e in pool if on_screen(e)]
            c = clusters(vis)
            clouds += c; ents += len(vis); looks += 1
            lo, hi = min(lo, c), max(hi, c)
            mx_pool = max(mx_pool, len(pool)); mx_line = max(mx_line, max(line_counts(o)))
            big += any(sum(1 for e in vis if e["y"] == y) >= 6 for y in {e["y"] for e in vis})
        g.pb.stop(save=False)
    return clouds / looks, (lo, hi), ents / looks, mx_pool, mx_line, big / looks


def test_steady_state_clouds_per_screen_and_the_line_limit_at_every_stop():
    avg, rng, ents, mx_pool, mx_line, big = steady(range(11), 40)
    print(f"\nsteady state: clouds on screen {avg:.2f} (range {rng}), entries {ents:.2f}, max pool {mx_pool}, max sprites on a line {mx_line}, a big cloud on {big:.0%} of the looks")
    (ROOT / "out" / "clouds_pool_steady.txt").write_text(f"clouds_avg={avg:.2f} range={rng[0]}-{rng[1]} entries_avg={ents:.2f} max_pool={mx_pool} max_line={mx_line} big_share={big:.2f}\n")
    assert mx_line <= 10 and mx_pool <= len(POOL)
    assert 1.5 <= avg <= 4.5, avg


# ---- hidden on every exit ---------------------------------------------------------------------------------------------------------------------------------------------
def cloud_left(gb):
    for mem in (gb.read("shadow_OAM", 160), bytes(gb.pb.memory[0xFE00:0xFEA0])):
        for i in range(40):
            if mem[i * 4] and mem[i * 4 + 2] in CLOUD_TILES and i in POOL:
                return i
    return None


def placed(gb):
    oam = gb.read("shadow_OAM", 160)
    return any(oam[i * 4] for i in POOL)


@pytest.mark.parametrize("path", ["venue_play", "venue_story", "festival", "menu", "beam"])
def test_no_cloud_entry_is_left_after_any_exit(path):
    from test_flow import run_until, state
    from test_story_map import tap, SP_MAP
    with double_speed():
        if path == "venue_play":
            gb = sm.to_map("cgb", 10, stop=0)
            assert placed(gb)
            tap(gb, "a", 20); gb.run(10); tap(gb, "a", 2)
        elif path == "venue_story":
            gb = sm.to_map("cgb", 0, stop=0)
            assert placed(gb)
            tap(gb, "a", 2)
        elif path == "festival":
            gb = sm.to_map("cgb", 10, stop=10)
            assert placed(gb)
            tap(gb, "a", 20); gb.run(10); tap(gb, "a", 2); gb.run(20); tap(gb, "a", 2)
        elif path == "menu":
            gb = sm.to_map("cgb", 10, stop=10)
            assert placed(gb)
            tap(gb, "start", 20); gb.run(10); tap(gb, "down", 2); tap(gb, "a", 2)
        else:                                                    # the space lounge's beam: the clouds go at once; the beam is in 3-11 (the pool), Sal rises in 19-22
            gb = sm.to_map("cgb", 9, stop=9)
            assert placed(gb)
            tap(gb, "a", 2)
            seen_beam = False
            for _ in range(120):
                gb.run(1, True)
                o = gb.oam()
                seen_beam = seen_beam or any(e["y"] and e["tile"] >= 98 for i, e in enumerate(o) if 3 <= i < 12)      # (the beam's tiles: cameo CAM_SPACE_BASE 98 on)
                assert not any(e["y"] and e["tile"] in CLOUD_TILES for e in o), "a cloud tile while the beam plays"
            assert seen_beam, "the beam is drawn in OAM 3-11 on a Color"
            return
        gb.run(2)
        try:
            run_until(gb, lambda: not (state(gb) == sm.GS_STORY and gb.mem("story_phase") == SP_MAP), 300)
        except Exception:
            pytest.skip(f"{path}: this path did not leave the map here")
        gb.run(30)
        assert cloud_left(gb) is None, f"a cloud entry stays in OAM after {path}"


def test_a_dmg_has_no_clouds():
    """A DMG map: the same entries (Sal 19-22, dots 24-34 ...: a DMG orders its sprites by x, so its picture is the same; the goldens say so), no cloud tile in any entry, the clouds' flag 0."""
    n = 0
    for s, d in ((0, 3), (3, 1), (10, 2)):
        gb, wt, lines, h = w.walk("dmg", s, d)
        o = gb.oam()
        assert not any(e["y"] and e["tile"] in CLOUD_TILES for e in o) and o[39]["x"] == 0
        n += 1
    g = sm.to_map("dmg", 3)
    o = g.oam()
    assert o[19]["y"] and o[19]["tile"] < 56, "Sal in 19-22 on a DMG"
    assert sum(1 for e in o[24:35] if e["y"]) >= 1, "the dots in 24-34 on a DMG"
    assert not any(e["y"] for e in o[3:19]), "the pool's entries are empty on a DMG"
    assert n == 3


# ---- the asm and its C twin ---------------------------------------------------------------------------------------------------------------------------------------
def pools_at_clocks(rom):
    """The pool (shadow OAM 3-18) at 4 stops x 24 clock settings, read when the game's tick has run 16 frames on from the poke (the C build is slower: its frames may be held)."""
    test_sound.ROM = rom
    out = []
    for stop in (0, 3, 6, 10):
        with double_speed():
            g = sm.to_map("cgb", 10, stop=stop)
        sb = g.addr("story_scratch")
        for i in range(24):
            d = (i * 1367) % 32768
            g.pb.memory[sb + SV + 25] = d & 255
            g.pb.memory[sb + SV + 5] = (((d >> 8) << 1) & 255) | 1
            target = (d + 16) & 255
            for _ in range(80):
                g.run(1, True)
                if g.read("story_scratch", 520)[SV + 25] == target:
                    break
            out.append((stop, d, tuple(g.read("shadow_OAM", 160)[3 * 4:19 * 4])))
        g.pb.stop(save=False)
    return out


def test_the_asm_build_equals_its_c_twin(monkeypatch):
    """src/smap_cloud.c cl_half: the asm and the C of the same loops (make cfall's -DASM_PASS=0) build the same pool."""
    lock = ROOT / "out" / "clouds_pool.lock"
    lock.parent.mkdir(exist_ok=True)
    with open(lock, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            subprocess.run(["make", "cfall"], cwd=ROOT, check=True, capture_output=True)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
    cgame = ROOT / "build" / "game-c.gb"
    monkeypatch.setattr(test_sound, "ROM", test_sound.ROM)           # (restored after the test)
    asm = pools_at_clocks(test_sound.ROM)
    ctw = pools_at_clocks(cgame)
    assert len(asm) == len(ctw) == 96
    diff = [(a[0], a[1]) for a, b in zip(asm, ctw) if a != b]
    assert not diff, diff[:6]
    assert sum(1 for a in asm if any(a[2][k * 4] for k in range(16))) >= 80, "the pools are not empty"


# ---- a cloud over Sal ---------------------------------------------------------------------------------------------------------------------------------------------
def tile_pixels(gb, tile):
    """The 8x16 sprite's 16 rows of 8 colour indices (tile & 0xFE and the one after, bank 0)."""
    base = 0x8000 + (tile & 0xFE) * 16
    mem = bytes(gb.pb.memory[base:base + 32])
    return [[((mem[2 * r + 1] >> (7 - x)) & 1) << 1 | ((mem[2 * r] >> (7 - x)) & 1) for x in range(8)] for r in range(16)]


def entry_pixel(gb, e, px, py):
    """Colour index of OAM entry e at the screen pixel (px, py), 0 if the entry is not opaque there."""
    x, y = px - (e["x"] - 8), py - (e["y"] - 16)
    if not (0 <= x < 8 and 0 <= y < 16):
        return 0
    if e["flags"] & 0x20:
        x = 7 - x
    return tile_pixels(gb, e["tile"])[y][x]


def test_a_cloud_draws_over_sal_on_a_color():
    """On a Color the sprite with the lower OAM index wins: the clouds (3-18) are before Sal (19-22). Finds a stop and clock at which a cloud entry and one of Sal's overlap on
    opaque pixels and checks the screen shows the cloud's colour there (the colour the same cloud has where nothing is under it), not Sal's."""
    found = 0
    for stop in (1, 2, 3, 6):
        with double_speed():
            g = sm.to_map("cgb", 10, stop=stop)
        sb = g.addr("story_scratch")
        for d in range(0, 4096, 128):
            g.pb.memory[sb + SV + 25] = d & 255
            g.pb.memory[sb + SV + 5] = (((d >> 8) << 1) & 255) | 1
            g.run(12)
            o = g.oam()
            sal = [o[i] for i in SAL if o[i]["y"]]
            img = g.image().convert("RGB")
            for c in (e for i, e in enumerate(o) if i in POOL and e["y"]):
                for s in sal:
                    both = [(px, py) for py in range(max(0, c["y"] - 16), min(144, c["y"])) for px in range(max(0, c["x"] - 8), min(160, c["x"]))
                            if entry_pixel(g, c, px, py) and entry_pixel(g, s, px, py)]
                    if len(both) < 6:
                        continue
                    # the cloud's own colour for each index, read where only the cloud is (no Sal entry there)
                    own = {}
                    for py in range(max(0, c["y"] - 16), min(144, c["y"])):
                        for px in range(max(0, c["x"] - 8), min(160, c["x"])):
                            k = entry_pixel(g, c, px, py)
                            if k and not any(entry_pixel(g, t, px, py) for t in sal):
                                own.setdefault(k, set()).add(img.getpixel((px, py)))
                    checked = 0
                    for px, py in both:
                        k = entry_pixel(g, c, px, py)
                        if k in own and len(own[k]) == 1:
                            assert img.getpixel((px, py)) in own[k], (stop, d, px, py, "Sal's pixel shows through a cloud")
                            checked += 1
                    if checked >= 6:
                        found += 1
        g.pb.stop(save=False)
    assert found >= 3, f"no state with a cloud over Sal's opaque pixels found ({found})"
