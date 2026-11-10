# The story map's sprite clouds (src/smap.c, OAM 23-35, docs/dev/proposals/smap_clouds/): Color only (owner 11-09): a DMG never loads their tiles,
# writes OBP1 or touches OAM 23-39 for them, whatever HALF bit 5 (the old debug toggle, HRAM 0xFFF4) holds.
import contextlib

import pytest

import test_story_map as sm

HALF = 0xFFF4
HALF_BIT5 = 0x20           # (the retired DMG CLOUDS toggle's bit: poking it must change nothing)
CLOUD_COLOURS = [0x7FFF, 0x7B36, 0x664E]


def map_with(monkeypatch, model, clouds_bit):
    orig = sm.booted

    def booted(*a, **k):
        gb = orig(*a, **k)
        if clouds_bit:
            gb.pb.memory[HALF] = gb.pb.memory[HALF] | HALF_BIT5
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


@pytest.mark.parametrize("poke", [False, True])
def test_dmg_has_no_clouds_ever(monkeypatch, poke):
    gb = map_with(monkeypatch, "dmg", poke)
    assert gb.mem(0xFF49) != 0x90, "OBP1 is not the clouds'"
    assert cloud_entries(gb) == 0
    assert all(gb.read("shadow_OAM", 160)[i * 4] == 0 for i in range(23, 40))


def test_color_clouds_are_always_on_in_obj_palette_1(monkeypatch):
    from test_lift import cgb_obj_palette
    from conftest import double_speed
    with double_speed():
        gb = map_with(monkeypatch, "cgb", False)
    assert list(cgb_obj_palette(gb, 1)[1:4]) == CLOUD_COLOURS
    assert cloud_entries(gb) > 10


def test_the_release_build_has_no_dmg_clouds(monkeypatch, release_built):
    """build/release.gb: a DMG map has no clouds; a Color map has them."""
    import test_sound
    from conftest import double_speed
    monkeypatch.setattr(test_sound, "ROM", release_built)
    gb = map_with(monkeypatch, "dmg", False)
    assert gb.mem(0xFF49) != 0x90 and cloud_entries(gb) == 0
    with double_speed():
        gb = map_with(monkeypatch, "cgb", False)
    assert cloud_entries(gb) > 10


def test_dmg_does_not_load_the_cloud_tiles(monkeypatch):
    objs = bytes.fromhex(sm.SMAP["obj_hex"])
    gb = map_with(monkeypatch, "dmg", True)
    ncl = 16                                         # (SMAP_CLOUD_TILES: the clouds tiles are the last ones)
    base = 0x8000 + sm.OB * 16
    assert bytes(gb.pb.memory[base:base + len(objs) - ncl * 16]) == objs[:len(objs) - ncl * 16]
    assert bytes(gb.pb.memory[base + len(objs) - ncl * 16:base + len(objs)]) != objs[len(objs) - ncl * 16:], "the cloud tiles stay unloaded"


# ---- leaving the map: no cloud entry (tiles 74-89, OBJ palette 1) stays in the OAM of the next screen (the Dregs gag test found one) ---------------------------------
def cloud_left(gb):
    for mem in (gb.read("shadow_OAM", 160), bytes(gb.pb.memory[0xFE00:0xFEA0])):
        for i in range(40):
            y, tile = mem[i * 4], mem[i * 4 + 2]
            if y and 74 <= tile <= 89 and i >= 23:
                return i
    return None


def placed(gb):
    oam = gb.read("shadow_OAM", 160)
    return any(oam[i * 4] for i in range(23, 36))


EXITS = ["venue_play", "venue_story", "festival", "menu"]


@pytest.mark.parametrize("path", EXITS)
@pytest.mark.parametrize("model, toggle", [("cgb", False)])
def test_no_cloud_entry_is_left_after_any_exit_from_the_map(monkeypatch, model, toggle, path):
    from conftest import double_speed
    from test_flow import run_until, state
    from test_story_map import tap, GS_MINI, SP_MAP
    ctx = double_speed() if model == "cgb" else contextlib.nullcontext()
    with ctx:
        if path == "venue_play":
            gb = map_with_progress(monkeypatch, model, toggle, 10, 0)
            tap(gb, "a", 20)
            gb.run(10)
            tap(gb, "a", 2)                                  # PLAY: the venue's mini-game
        elif path == "venue_story":
            gb = map_with_progress(monkeypatch, model, toggle, 0, 0)
            tap(gb, "a", 2)                                  # the next venue
        elif path == "festival":
            gb = map_with_progress(monkeypatch, model, toggle, 10, 10)
            tap(gb, "a", 20)
            gb.run(10)
            tap(gb, "a", 2)
            gb.run(20)
            tap(gb, "a", 2)
        else:                                                # START: the menu panel, its second item (leaving the map)
            gb = map_with_progress(monkeypatch, model, toggle, 10, 10)
            tap(gb, "start", 20)
            gb.run(10)
            tap(gb, "down", 2)
            tap(gb, "a", 2)
        gb.run(2)
        left_map = lambda: not (state(gb) == sm.GS_STORY and gb.mem("story_phase") == SP_MAP)
        try:
            run_until(gb, left_map, 300)
        except Exception:
            pytest.skip(f"{path}: this path did not leave the map here")
        gb.run(30)
        assert cloud_left(gb) is None, f"a cloud entry stays in OAM after {path}"


def map_with_progress(monkeypatch, model, toggle, progress, stop):
    orig = sm.booted

    def booted(*a, **k):
        gb = orig(*a, **k)
        if toggle:
            gb.pb.memory[HALF] = gb.pb.memory[HALF] | HALF_BIT5
        return gb
    monkeypatch.setattr(sm, "booted", booted)
    gb = sm.to_map(model, progress, stop=stop)
    assert placed(gb), "the clouds are in the OAM before the exit"
    return gb
