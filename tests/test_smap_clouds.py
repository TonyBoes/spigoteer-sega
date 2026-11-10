# The story map's sprite clouds (src/smap.c, OAM 23-35, docs/dev/proposals/smap_clouds/): Color always has them; a DMG has them only when the debug menu's
# TUNING > DMG CLOUDS is ON (HALF bit 5, HRAM 0xFFF4, session only: boot clears it), so the DMG map and its perf guard stay as they were.
import pytest

import test_story_map as sm

HALF = 0xFFF4
HALF_CLOUDS = 0x20
CLOUD_COLOURS = [0x7FFF, 0x7B36, 0x664E]


def map_with(monkeypatch, model, clouds_bit):
    orig = sm.booted

    def booted(*a, **k):
        gb = orig(*a, **k)
        if clouds_bit:
            gb.pb.memory[HALF] = gb.pb.memory[HALF] | HALF_CLOUDS
        return gb
    monkeypatch.setattr(sm, "booted", booted)
    gb = sm.to_map(model, 10, stop=10)
    return gb


def cloud_entries(gb, frames=80):
    """Walk west from the town and count the frames on which a cloud entry (OAM 23-35) is on the screen."""
    gb.press("left", 6)
    seen = 0
    for _ in range(frames):
        gb.run(1, True)
        oam = gb.read("shadow_OAM", 160)
        seen += any(0 < oam[i * 4] < 160 and 0 < oam[i * 4 + 1] < 168 for i in range(23, 36))
    return seen


def test_dmg_clouds_are_off_by_default(monkeypatch):
    gb = map_with(monkeypatch, "dmg", False)
    assert gb.mem(HALF) & HALF_CLOUDS == 0
    assert gb.mem(0xFF49) != 0x90, "OBP1 is not the clouds'"
    assert cloud_entries(gb) == 0
    assert all(gb.read("shadow_OAM", 160)[i * 4] == 0 for i in range(23, 40))


def test_dmg_clouds_come_with_the_debug_toggle(monkeypatch):
    gb = map_with(monkeypatch, "dmg", True)
    assert gb.mem(0xFF49) == 0x90, "OBP1: white, light grey, mid grey"
    assert cloud_entries(gb) > 10


def test_color_clouds_are_always_on_in_obj_palette_1(monkeypatch):
    from test_lift import cgb_obj_palette
    from conftest import double_speed
    with double_speed():
        gb = map_with(monkeypatch, "cgb", False)
    assert list(cgb_obj_palette(gb, 1)[1:4]) == CLOUD_COLOURS
    assert cloud_entries(gb) > 10


def test_the_release_build_has_no_dmg_clouds(monkeypatch, release_built):
    """build/release.gb has no debug menu, so nothing can set HALF bit 5: a DMG map has no clouds; a Color map has them."""
    import test_sound
    from conftest import double_speed
    monkeypatch.setattr(test_sound, "ROM", release_built)
    gb = map_with(monkeypatch, "dmg", False)
    assert gb.mem(0xFF49) != 0x90 and cloud_entries(gb) == 0
    with double_speed():
        gb = map_with(monkeypatch, "cgb", False)
    assert cloud_entries(gb) > 10


def test_the_clouds_tiles_are_loaded_with_the_clouds(monkeypatch):
    objs = bytes.fromhex(sm.SMAP["obj_hex"])
    gb = map_with(monkeypatch, "dmg", True)
    assert bytes(gb.pb.memory[0x8000 + sm.OB * 16:0x8000 + sm.OB * 16 + len(objs)]) == objs
