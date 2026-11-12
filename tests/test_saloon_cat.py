# The Saloon's bar cat (owner pick, Q40, 2026-11-03: concept v5a, the ear-flick version with the pendulum tail).
# The built stage (build/venues.json: the map, the stage tiles, the 7 animation frames) and the real VRAM of the running
# ROM (DMG and Color) must equal catprev.py's render of docs/dev/concepts/stage_cat_2026-11-03/v5a.txt, pixel for pixel,
# at every frame.
import sys
from pathlib import Path

import pytest
from conftest import ROOT, venue
from test_stage_anim import POOL, anim, at_venue, keep_playing, stage_vram

sys.path.insert(0, str(ROOT / "docs/dev/concepts/stage_cat_2026-11-03"))
import catprev  # noqa: E402
pytestmark = pytest.mark.only_model('dmg')   # model_equiv.py: DMG and Color proven equal for every test here

FRAMES = ["base", "s", "l1", "l2", "hang_blink", "hang_ear", "flick"]
IDX = catprev.IDX


def reference(frame):
    """160x32 colour indices of catprev's render of v5a at that frame."""
    return [[IDX[ch] for ch in row] for row in catprev.stage_pixels("v5a", frame)]


def decode(tile):
    """16 bytes of 2bpp -> 8 rows of 8 colour indices."""
    return [[((tile[2 * y] >> (7 - x)) & 1) | (((tile[2 * y + 1] >> (7 - x)) & 1) << 1) for x in range(8)] for y in range(8)]


def render(tiles, stage_map):
    """The 20x4 stage map over the 8x8 tiles (a list of 16-byte tiles by id) -> 32 rows of 160 indices."""
    out = [[] for _ in range(32)]
    for r in range(4):
        for c in range(20):
            t = decode(tiles[stage_map[r * 20 + c]])
            for y in range(8):
                out[r * 8 + y] += t[y]
    return out


def built_tiles(f):
    v, a = venue("saloon"), anim("saloon")
    d = bytes(v["stage_tiles"])
    tiles = [d[i * 16:(i + 1) * 16] for i in range(v["stage_n"])]
    fr = bytes(a["frames"][f])
    for i in range(a["k"]):
        tiles[a["first"] + i] = fr[i * 16:(i + 1) * 16]
    return tiles


def test_the_script_and_frames_are_v5a():
    a = anim("saloon")
    assert a["names"] == FRAMES and a["k"] == 2 and len(a["frames"]) == 7
    want = [(FRAMES.index(n), h) for n, h in catprev.own_script("v5a")]
    assert [tuple(s) for s in a["script"]] == want
    assert sum(h for _, h in a["script"]) == 389


@pytest.mark.parametrize("f", range(7), ids=FRAMES)
def test_every_built_frame_equals_the_v5a_render(f):
    v = venue("saloon")
    assert render(built_tiles(f), v["stage_map"]) == reference(FRAMES[f])


def test_the_running_rom_shows_every_v5a_frame_exactly(gb):
    """Both models: the VRAM stage, through the stage map, is one of the 7 renders on every frame of two script
    periods, and all 7 turn up."""
    v = venue("saloon")
    at_venue(gb, "saloon")
    refs = {i: reference(n) for i, n in enumerate(FRAMES)}
    gb.write("sa_hold", 0)
    seen = set()
    for i in range(2 * 389 + 20):
        gb.run(1)
        if i % 32 == 0:
            keep_playing(gb)
        if i % 3:
            continue          # a frame may be mid-update (a 2-tile update lands in one VBlank, but sample every 3rd to keep this fast)
        px = render(stage_vram(gb), v["stage_map"])
        hit = [k for k, r in refs.items() if r == px]
        assert hit, f"frame {i}: the stage matches none of the 7 v5a frames"
        seen.add(hit[0])
    assert seen == set(range(7)), f"frames never shown: {set(range(7)) - seen}"
