# The denser story-map clouds, the test builds CLOUDS=C|D (src/smap_cloud.c: a pool of 17 entries, OAM 23-39, built from the clock and the camera; tools/dev/cloud_layout.py
# lays 26 / 44 clouds out over the world). Color only; the default build keeps today's five clouds (test_smap_clouds.py) and is built here as "T" for the numbers.
# Per build, over every leg of the map walked at double speed (the shipped Color speed): at most 10 sprites on any scanline, the pool never overflows, no cloud entry well
# inside the screen vanishes or jumps, entries 0-22 (Sal, the arrows, the bang, the dots, the UFO, the cursor) are bit-for-bit those of today's build (nothing that must
# show loses its sprite), the Color walk's perf guard of test_story_map_world.PERF untouched; the clouds are hidden after every exit; a DMG is unchanged.
import contextlib
import fcntl
import subprocess

import pytest
import test_sound
import test_story_map as sm
import test_story_map_world as w
from conftest import ROOT, double_speed

OAM_CLOUDS, POOL_END = 23, 40
CLOUD_TILES = range(74, 98)          # (OB + the cloud tiles: A B C, then P R Q in the test builds)
VARIANTS = ["T", "C", "D"]
MAX_ENTRIES = {"T": 13, "C": 16, "D": 16}
A_CLN, SV = 390, 396
TRACE = {}                            # (variant, leg) -> [OAM 0-22 bytes per frame]


def build(v, c_twin=False):
    lock = ROOT / "out" / "clouds_pool.lock"
    lock.parent.mkdir(exist_ok=True)
    with open(lock, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            name = "game-c.gb" if c_twin else "game.gb"
            subprocess.run(["make", f"BUILD=out/t_clouds{v}{'c' if c_twin else ''}", f"OUT=out/ot_clouds{v}{'c' if c_twin else ''}", "CLOUDS=" + ("" if v == "T" else v),
                            f"out/t_clouds{v}{'c' if c_twin else ''}/{name}"], cwd=ROOT, check=True, capture_output=True)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
    return ROOT / "out" / f"t_clouds{v}{'c' if c_twin else ''}" / name


@pytest.fixture(scope="session", params=VARIANTS)
def variant_rom(request):
    return request.param, build(request.param)


def line_counts(oam):
    n = [0] * 144
    for o in oam:
        if 0 < o["y"] < 160:
            for ly in range(max(0, o["y"] - 16), min(144, o["y"])):
                n[ly] += 1
    return n


def clusters(cl):
    """Clouds among cloud entries: neighbours 8 px apart on one line are one cloud."""
    es = sorted((o["y"], o["x"]) for o in cl)
    n = 0
    for i, (y, x) in enumerate(es):
        if not (i and es[i - 1] == (y, x - 8)):
            n += 1
    return n


def on_screen(o):
    return 0 < o["y"] < 160 and 0 < o["x"] < 168


def test_the_pool_keeps_the_line_limit_the_pool_and_the_perf_guard(monkeypatch, variant_rom):
    v, rom = variant_rom
    monkeypatch.setattr(test_sound, "ROM", rom)
    seen = {"maxline": 0, "cloudline": 0, "frames": 0, "visible": 0, "clouds": 0, "entries": 0, "jumps": [], "prev": None, "bad_slot": 0, "motion_bad": 0, "world": None}
    leg_trace = {}
    cur = {}
    orig = w.Watch.frame

    def frame(self):
        r = orig(self)
        o = self.gb.oam()
        pool = [e for i, e in enumerate(o) if i >= OAM_CLOUDS and e["y"]]
        lc = line_counts(o)
        seen["maxline"] = max(seen["maxline"], max(lc))
        seen["cloudline"] = max(seen["cloudline"], max(line_counts(pool)))
        seen["frames"] += 1
        vis = [e for e in pool if on_screen(e)]
        seen["visible"] += len(vis)
        seen["clouds"] += clusters(vis)
        seen["entries"] = max(seen["entries"], len(pool))
        seen["bad_slot"] += sum(1 for e in pool if e["tile"] not in CLOUD_TILES)
        sc = self.gb.read("story_scratch", 520)
        wh = sc[SV + 9]
        tk = sc[SV + 25]
        cur["tk"] = tk if "last" not in cur else cur["tk"] + (tk - cur["last"]) % 256
        cur["last"] = tk
        camx, camy = sc[SV + 12] | sc[SV + 13] << 8, sc[SV + 14] | sc[SV + 15] << 8
        world = [((e["x"] - 8 + camx) % 512, (e["y"] - 16 + camy) & 255, e["tile"]) for e in pool if 16 <= e["x"] <= 150 and 24 <= e["y"] <= 150]      # (inside the screen: the world place of each cloud entry)
        pw = seen.get("world")
        if pw is not None and not wh and not seen.get("wh"):
            for wx, wy, tl in world:                              # (a cloud drifts 1 px in 8 frames and otherwise stays where it is on the map: never more than 1 px between two frames)
                near = [(a, b) for a, b, t in pw if t == tl and b == wy and min((wx - a) % 512, (a - wx) % 512) <= 40]
                if near and min(min((wx - a) % 512, (a - wx) % 512) for a, b in near) > 1:
                    seen["motion_bad"] += 1
        seen["world"] = world
        prev = seen["prev"] if not wh and not seen.get("wh") else None      # (a window layer hides the clouds under it: no look at those frames)
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
        cur.setdefault("t", []).append((cur["tk"], [(e["y"], e["x"], e["tile"], e["flags"]) for e in o[:OAM_CLOUDS]]))
        return r
    monkeypatch.setattr(w.Watch, "frame", frame)

    allv, holds, frames = [], 0, 0
    for s, d in w.LEG_WALKS:
        seen["prev"] = None
        cur.clear()
        seen["wh"] = 0
        seen["world"] = None
        gb, wt, lines, h = w.walk("cgb", s, d, double=True)
        assert not wt.bad, (s, d, wt.bad[:3])
        TRACE[(v, s, d)] = cur.get("t", [])
        allv += lines[2:]
        holds += h
        frames += len(lines)
    allv.sort()
    p90, worst = allv[len(allv) * 9 // 10], allv[-1]
    print(f"\nCLOUDS={v}: max sprites on a line {seen['maxline']} (clouds alone {seen['cloudline']}), max pool entries {seen['entries']}, "
          f"cloud entries on screen {seen['visible'] / seen['frames']:.2f}, clouds {seen['clouds'] / seen['frames']:.2f}, jumps {len(seen['jumps'])}, perf p90 {p90} worst {worst} holds {holds}/{frames}")
    (ROOT / "out" / f"clouds_pool_walk_{v}.txt").write_text(
        f"max_line={seen['maxline']} clouds_line={seen['cloudline']} max_pool={seen['entries']} entries_on_screen_walk={seen['visible'] / seen['frames']:.2f} "
        f"clouds_walk={seen['clouds'] / seen['frames']:.2f} p90={p90} worst={worst} holds={holds}/{frames}\n")
    assert seen["maxline"] <= 10, seen["maxline"]
    assert seen["entries"] <= MAX_ENTRIES[v]
    assert not seen["bad_slot"], "a pool entry that is not a cloud tile"
    assert not seen["jumps"], seen["jumps"][:5]
    assert not seen["motion_bad"], f"{seen['motion_bad']} cloud entries moved more than 1 px on the map between two frames"
    b = w.PERF["cgb"]
    assert worst <= b["worst"] and p90 <= b["p90"], (p90, worst)
    assert holds <= b["holds"] * frames, (holds, frames)


STANDING = {}


def standing_trace(monkeypatch, v, rom):
    """Entries 0-22 frame by frame at three stops, idle and with the panels up (the cursor), with the clouds in the OAM beside them."""
    from test_story_map import tap
    monkeypatch.setattr(test_sound, "ROM", rom)
    out = []
    for stop, keys in ((3, []), (10, []), (10, ["start"]), (3, ["a"]), (10, ["a"])):
        with double_speed():
            g = sm.to_map("cgb", 10, stop=stop)
            for k in keys:
                tap(g, k, 12)
                g.run(20)
            for _ in range(70):
                g.run(1, True)
                out.append((stop, tuple(keys), tuple((e["y"], e["x"], e["tile"], e["flags"]) for e in g.oam()[:OAM_CLOUDS])))
        g.pb.stop(save=False)
    return out


def test_the_must_show_entries_are_the_same_with_and_without_the_clouds(monkeypatch, variant_rom):
    """Entries 0-22 (the arrows, Sal, the bang, the dots, the UFO, the panel's cursor) are bit for bit today's, frame for frame, standing at stops and with the panels up: the
    pool never takes a must-show sprite's entry, so a dot, the UFO or the cursor is never lost to a cloud (the cloud code writes OAM 23-39 only: the walk's pace differs by a
    frame here and there, so the walking frames cannot be compared this way). The cursor must have been there at all."""
    v, rom = variant_rom
    STANDING[v] = standing_trace(monkeypatch, v, rom)
    if v == "T":
        return
    ref = STANDING["T"]
    assert len(ref) == len(STANDING[v]) > 300
    diff = [i for i, (a, b) in enumerate(zip(ref, STANDING[v])) if a != b]
    assert not diff, (diff[:5], ref[diff[0]] if diff else None, STANDING[v][diff[0]] if diff else None)
    assert any(t[2][22][0] for t in ref), "a panel's cursor was shown in the reference run"


def steady(v, rom, monkeypatch):
    """Clouds on the screen at 4 stops x 48 clock phases (the clock set, the clouds built from it): (average clouds, range, average entries, max pool entries, max sprites on a line)."""
    monkeypatch.setattr(test_sound, "ROM", rom)
    looks, clouds, ents, mx_pool, mx_line, lo, hi = 0, 0, 0, 0, 0, 99, 0
    for stop in (0, 3, 6, 10):
        with double_speed():
            g = sm.to_map("cgb", 10, stop=stop)
        sb, so = g.addr("story_scratch"), g.addr("shadow_OAM")
        for i in range(48):
            dclk = (i * 683) % 32768
            g.pb.memory[sb + SV + 25] = dclk & 255
            g.pb.memory[sb + SV + 5] = ((dclk >> 8) << 1) & 255
            if v == "T":
                g.pb.memory[so + 36 * 4 + 2] = 0
                for e in range(23, 36):
                    g.pb.memory[so + e * 4] = 0
            g.run(12)
            o = g.oam()
            pool = [e for k, e in enumerate(o) if k >= OAM_CLOUDS and e["y"]]
            vis = [e for e in pool if on_screen(e)]
            c = clusters(vis)
            clouds += c; ents += len(vis); looks += 1
            lo, hi = min(lo, c), max(hi, c)
            mx_pool = max(mx_pool, len(pool)); mx_line = max(mx_line, max(line_counts(o)))
        g.pb.stop(save=False)
    return clouds / looks, (lo, hi), ents / looks, mx_pool, mx_line


def test_steady_state_clouds_per_screen(monkeypatch, variant_rom):
    v, rom = variant_rom
    avg, rng, ents, mx_pool, mx_line = steady(v, rom, monkeypatch)
    print(f"\nCLOUDS={v}: steady state clouds on screen {avg:.2f} (range {rng}), entries {ents:.2f}, max pool {mx_pool}, max sprites on a line {mx_line}")
    (ROOT / "out" / f"clouds_pool_steady_{v}.txt").write_text(f"clouds_avg={avg:.2f} range={rng[0]}-{rng[1]} entries_avg={ents:.2f} max_pool={mx_pool} max_line={mx_line}\n")
    assert mx_line <= 10 and mx_pool <= MAX_ENTRIES[v]
    if v == "C":
        assert 2.5 <= avg <= 3.8, avg
    if v == "D":
        assert 3.2 <= avg <= 6.0, avg


# ---- hidden on every exit -------------------------------------------------------------------------------------------------------------------------------------
def cloud_left(gb):
    for mem in (gb.read("shadow_OAM", 160), bytes(gb.pb.memory[0xFE00:0xFEA0])):
        for i in range(40):
            if mem[i * 4] and mem[i * 4 + 2] in CLOUD_TILES and i >= OAM_CLOUDS:
                return i
    return None


def placed(gb):
    oam = gb.read("shadow_OAM", 160)
    return any(oam[i * 4] for i in range(OAM_CLOUDS, POOL_END))


@pytest.mark.parametrize("path", ["venue_play", "venue_story", "festival", "menu", "beam"])
def test_no_cloud_entry_is_left_after_any_exit(monkeypatch, variant_rom, path):
    from test_flow import run_until, state
    from test_story_map import tap, SP_MAP
    v, rom = variant_rom
    if v == "T":
        pytest.skip("test_smap_clouds.py has today's")
    monkeypatch.setattr(test_sound, "ROM", rom)
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
        else:                                                    # the space lounge's beam: the clouds go at once and stay gone while the beam plays
            gb = sm.to_map("cgb", 9, stop=9, step=1) if False else sm.to_map("cgb", 9, stop=9)
            assert placed(gb)
            tap(gb, "a", 2)
            gb.run(30)
            assert gb.read("story_scratch", 520)[A_CLN] == 0 or not placed(gb), "the beam has OAM 23-31: no cloud there"
            assert not placed(gb) or cloud_left(gb) is None
            return
        gb.run(2)
        try:
            run_until(gb, lambda: not (state(gb) == sm.GS_STORY and gb.mem("story_phase") == SP_MAP), 300)
        except Exception:
            pytest.skip(f"{path}: this path did not leave the map here")
        gb.run(30)
        assert cloud_left(gb) is None, f"a cloud entry stays in OAM after {path}"


# ---- a DMG is unchanged -------------------------------------------------------------------------------------------------------------------------------------------
def test_a_dmg_runs_the_same_with_the_test_builds(monkeypatch, variant_rom):
    """No clouds on a DMG: the walk of a leg gives the same OAM (all 40 entries) and the same logic lines frame for frame as today's build."""
    v, rom = variant_rom
    monkeypatch.setattr(test_sound, "ROM", rom)
    traces = []
    orig = w.Watch.frame

    def frame(self):
        r = orig(self)
        traces.append(tuple((e["y"], e["x"], e["tile"]) for e in self.gb.oam()))
        return r
    monkeypatch.setattr(w.Watch, "frame", frame)
    out = []
    for s, d in ((0, 3), (3, 1), (10, 2)):
        traces.clear()
        gb, wt, lines, h = w.walk("dmg", s, d)
        out.append((list(traces), lines, h))
        assert not any(e[0] and e[2] in CLOUD_TILES for t in traces for e in t), "a cloud entry on a DMG"
    TRACE[("dmg", v)] = out
    if v != "T":
        ref = TRACE.get(("dmg", "T"))
        assert ref is not None
        for (ta, la, ha), (tb, lb, hb) in zip(ref, out):
            assert ta == tb, "the DMG's OAM differs"
            diff = sum(1 for a, b in zip(la, lb) if a != b)
            pa, pb = sorted(la)[len(la) * 9 // 10], sorted(lb)[len(lb) * 9 // 10]
            print(f"\nDMG {v}: {diff} of {len(la)} frames differ by {max((abs(a - b) for a, b in zip(la, lb)), default=0)} line (the one is_cgb test of the cloud hook), worst {max(la)} / {max(lb)}, p90 {pa} / {pb}")
            assert max(la) == max(lb) and pa == pb and ha == hb and diff <= len(la) // 20 and all(abs(a - b) <= 1 for a, b in zip(la, lb)), "the DMG's logic lines differ"


# ---- the asm and its C twin ---------------------------------------------------------------------------------------------------------------------------------------
def pools_at_clocks(monkeypatch, rom):
    """The pool (shadow OAM 23-38) at 4 stops x 24 clock settings, read when the game's tick has run 12 frames on from the poke (the C build is slower: its frames may be held)."""
    monkeypatch.setattr(test_sound, "ROM", rom)
    out = []
    for stop in (0, 3, 6, 10):
        with double_speed():
            g = sm.to_map("cgb", 10, stop=stop)
        sb, so = g.addr("story_scratch"), g.addr("shadow_OAM")
        for i in range(24):
            d = (i * 1367) % 32768
            g.pb.memory[sb + SV + 25] = d & 255
            g.pb.memory[sb + SV + 5] = ((d >> 8) << 1) & 255 | 1
            target = (d + 16) & 255
            for _ in range(80):
                g.run(1, True)
                if g.read("story_scratch", 520)[SV + 25] == target:
                    break
            out.append((stop, d, tuple(g.read("shadow_OAM", 160)[OAM_CLOUDS * 4:39 * 4])))
        g.pb.stop(save=False)
    return out


@pytest.mark.parametrize("v", ["C", "D"])
def test_the_asm_build_equals_its_c_twin(monkeypatch, v):
    """src/smap_cloud.c cl_half: the asm and the C of the same loops (make cfall's -DASM_PASS=0) build the same pool."""
    asm = pools_at_clocks(monkeypatch, build(v))
    ctw = pools_at_clocks(monkeypatch, build(v, c_twin=True))
    assert len(asm) == len(ctw) == 96
    diff = [(a[0], a[1]) for a, b in zip(asm, ctw) if a != b]
    assert not diff, diff[:6]
    assert sum(1 for a in asm if any(a[2][k * 4] for k in range(16))) >= 80, "the pools are not empty"
