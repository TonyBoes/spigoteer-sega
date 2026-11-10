# The story map's tile animations (stage 3: tools/smap_world/anims.py the frames and the schedule, build/smap_an.c the tables, src/smap_eng.c anim_step the engine).
# The map's frame counter V_TICK is the clock: group g shows image key[V_TICK] (a 256-tick loop). The screen is read frame by frame at every stop and every animated cell that
# is wholly on it (and under no sprite) must show one of the images the loop has had in the last three ticks (the writes go out in VBlank, a frame after the tick).
import contextlib
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_story_map as sm  # noqa: E402
from conftest import ROOT, double_speed  # noqa: E402
from test_story_map_world import (ANIM_MASK, DMG_GREY, SV, V_CAMX, V_CAMY, WORLD, sprite_mask, tile_idx, var)  # noqa: E402

pytestmark = pytest.mark.timeout(600)

NO_ANIMATION = (0, 2, 8)                                         # the stops whose view holds no animated cell
AN = WORLD["anim"]
V_TICK = 25
GROUPS = AN["groups"]


def cell_pal(model, cell_index):
    return (WORLD["disp_c"][10][cell_index] >> 10) & 31 if model == "cgb" else 0


def image_rgb(model, hexs, pal):
    ix = tile_idx(bytes.fromhex(hexs))
    cols = [((v & 31) << 3, ((v >> 5) & 31) << 3, ((v >> 10) & 31) << 3) for v in WORLD["pal"][pal]] if model == "cgb" else [DMG_GREY[i] for i in range(4)]
    return np.array(cols, dtype=np.uint8)[ix]


def test_the_schedule_is_sound():
    """every group's tile is its own (no other cell shows it), its image 0 is what the map holds, and a tick holds few events"""
    assert AN["loop"] == 256
    assert AN["max_events_per_tick"] <= 24
    seen = set()
    for g in GROUPS:
        assert len(g["key"]) == 256 and g["imgs_c"][0] and max(g["key"]) < len(g["imgs_c"]), g["name"]
        for c in g["cells"]:
            assert tuple(c) not in seen, ("a cell in two groups", g["name"], c)
            seen.add(tuple(c))
    for model, tkey, ikey in (("cgb", "tile_c", "imgs_c"), ("dmg", "tile_d", "imgs_d")):
        tiles = bytes.fromhex(WORLD["tiles_c" if model == "cgb" else "tiles_d"])
        disp = WORLD["disp_c" if model == "cgb" else "disp_d"][10]
        for g in GROUPS:
            t = g[tkey]
            if t is None:
                continue
            assert tiles[t * 16:t * 16 + 16].hex() == g[ikey][0], (model, g["name"], "image 0 is the tile the map holds")
            users = {c for c, w in enumerate(disp) if (w & 0x3FF) == t}
            assert users == {cy * 64 + cx for cx, cy in g["cells"]}, (model, g["name"], "the group's tile is shown by its own cells only")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("stop", list(range(11)))
def test_the_tile_animations_play(model, stop):
    ctx = double_speed() if model == "cgb" else contextlib.nullcontext()
    with ctx:
        gb = sm.to_map(model, 10, stop=stop)
    key = "imgs_c" if model == "cgb" else "imgs_d"
    seen = {}                                                  # group -> the distinct images seen on the screen
    checked = 0
    for f in range(300):
        gb.run(1, True)
        sc = gb.read("story_scratch", 520)
        tick = sc[SV + V_TICK]
        cx0, cy0 = var(sc, V_CAMX), var(sc, V_CAMY)
        scr = np.array(gb.image())
        m = np.zeros((144, 160), dtype=bool)
        sprite_mask(gb.oam(), m)
        if sc[SV + 9]:                                           # (a window is up: the name tag)
            m[max(sc[SV + 8] - 1, 0):sc[SV + 8] + sc[SV + 9] + 1, :] = True
        for g in GROUPS:
            if g["tile_c" if model == "cgb" else "tile_d"] is None:
                continue
            for cx, cy in g["cells"]:
                x, y = cx * 8 - cx0, cy * 8 - cy0
                if x < 0 or y < 0 or x + 8 > 160 or y + 8 > 144 or m[y:y + 8, x:x + 8].any():
                    continue
                pal = cell_pal(model, cy * 64 + cx)
                got = scr[y:y + 8, x:x + 8]
                ok = False
                for back in range(4):
                    k = g["key"][(tick - back) % 256]
                    if np.array_equal(got, image_rgb(model, g[key][k], pal)):
                        ok = True
                        seen.setdefault(g["name"], set()).add(k)
                        break
                assert ok, (model, stop, f, tick, g["name"], (cx, cy), "the cell shows none of the last images of its loop")
                checked += 1
    assert checked > 100 or (checked == 0 and stop in NO_ANIMATION), (model, stop, checked)
    if stop == 10:                                              # the town: the fountain's streams, the bunting and the water play
        assert len(seen.get("stream(28,24)", ())) == 3 and len(seen.get("P", ())) == 3, seen


# ---- the owner's rules: no flashing lights, no tile written more often than the hardware takes ------------------------------------------------------------------------------------
def test_the_runway_lights_fade_one_step_at_a_time():
    """owner Q13 and the standing no-flash rule: the lights brighten and dim one palette (Color) or shade (DMG) step at a time, a light changes at most every 20 ticks, never cuts"""
    lights = [g for g in GROUPS if g["item"] == "10_runway_lights"]
    assert len(lights) == 3
    for g in lights:
        for key in ("imgs_c", "imgs_d"):
            imgs = [tile_idx(bytes.fromhex(h)) for h in g[key]]
            ks = g["key"]
            ticks = [t for t in range(256) if ks[t] != ks[t - 1]]
            assert len(ticks) >= 6, g["name"]
            for t in ticks:
                a, b = imgs[ks[t - 1]].astype(int), imgs[ks[t]].astype(int)
                assert np.abs(a - b).max() == 1, (g["name"], key, t, "a light pixel changed by more than one step")
            gaps = [(b - a) % 256 for a, b in zip(ticks, ticks[1:] + ticks[:1])]
            assert min(gaps) >= 20, (g["name"], gaps)


def test_no_view_the_camera_shows_has_more_than_two_events_at_a_tick():
    """the DMG writes two tiles a frame (NSTG_MAX): a third event in one tick would wait for the group's next change (tools/dev/smap_anim_phases.py)"""
    sys.path.insert(0, str(ROOT / "tools"))
    import gen_smap_world as g
    stops, legs, _, _ = g.geometry()
    for (c0, c1, r0, r1) in set(g.path_windows(stops, legs, 1)):
        cnt = np.zeros(256, dtype=int)
        for grp in GROUPS:
            if any(c0 <= x <= c1 and r0 <= y <= r1 for x, y in grp["cells"]):
                ks = grp["key"]
                for t in range(256):
                    cnt[t] += ks[t] != ks[t - 1]
        assert cnt.max() <= 2, ((c0, c1, r0, r1), int(cnt.argmax()), int(cnt.max()))
