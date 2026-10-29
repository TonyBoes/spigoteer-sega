# patron-rev-2 step 4: the Saloon's 8 looks. The five Color-only ones (3-7: HANK, ROSIE, REDD, MABEL, ARTIE) have their tiles in VRAM bank 1;
# the DMG keeps the three (DUSTY, EMMA, GUS).
import re

import pytest
from conftest import ROOT

pytestmark = pytest.mark.timeout(60)

MAX_P = 16


def blob():
    txt = (ROOT / "build" / "patrons_saloon_x.c").read_text()
    body = txt[txt.index("patron_tiles_saloon_x[4032] = {"):]
    body = body[:body.index("};")]
    return bytes(int(h, 16) for h in re.findall(r"0x([0-9A-F]{2})", body))


@pytest.mark.only_model("cgb")
def test_the_color_only_looks_are_in_vram_bank_1(gb):
    b = blob()
    assert len(b) == 252 * 16
    vram = gb.pb.memory
    got = bytes(vram[1, 0x9000:0x9800]) + bytes(vram[1, 0x8800:0x9000])[:124 * 16]
    assert got == b, "BG ids 0..127 at 0x9000, 128..251 at 0x8800, all from the one blob (the asm copy and its C twin alike)"


@pytest.mark.only_model("dmg")
def test_the_dmg_keeps_the_three_looks(gb):
    for _ in range(60):
        gb.run(20)
        assert all(v < 3 for v in gb.read("patron_variant", MAX_P)), "variant bytes 0-2 only"


# (look, palette instance) pairs the Palette Plan allows: OBJ slots 3 4 5 6 7 = instances 0 3 1 4 2
COMBOS = {0: [0, 1, 2], 1: [3, 1, 2], 2: [0, 1], 3: [0, 1, 4, 2], 4: [0, 3, 1, 2], 5: [0, 3, 1, 4, 2], 6: [0, 3, 1, 4, 2], 7: [0, 3, 1, 4, 2]}


@pytest.mark.only_model("cgb")
def test_the_color_saloon_spawns_only_the_31_planned_combinations_and_all_of_them(gb):
    assert sum(len(v) for v in COMBOS.values()) == 31
    seen = set()
    for _ in range(6000):
        gb.write("lives", 3)
        gb.write("quota", 250)
        gb.run(20)
        st = gb.read("patron_state", MAX_P)
        for i, v in enumerate(gb.read("patron_variant", MAX_P)):
            if st[i]:
                pi = (v ^ (v >> 3)) & 7
                assert pi in COMBOS[v & 7], (v & 7, pi)
                seen.add((v & 7, pi))
        if len(seen) == 31:
            break
    assert len(seen) == 31, sorted(set((l, p) for l, ps in COMBOS.items() for p in ps) - seen)


@pytest.mark.only_model("cgb")
def test_the_color_saloon_spawns_all_eight_looks(gb):
    seen = set()
    for _ in range(3000):
        gb.write("lives", 3)                 # (a long game of the one level: nobody is served, patrons walk to the stop and back)
        gb.write("quota", 250)
        gb.run(20)
        st = gb.read("patron_state", MAX_P)
        for i, v in enumerate(gb.read("patron_variant", MAX_P)):
            if st[i]:
                seen.add(v & 7)
                assert bool(v & 0x40) == ((v & 7) > 2), "bank 1 exactly for the looks 3-7"
        if len(seen) == 8:
            break
    assert seen == set(range(8)), (seen, gb.mem("spawned"), gb.mem("game_state"))


def _gus_tiles(gb, model):
    """GUS's (variant C) tiles as the level load leaves them in VRAM bank 0, and as the ROM holds them: (loaded, rom) lists of 16-byte tiles."""
    from test_patrons import BASE, SHIFT0_OFS, SHIFTED
    m = re.search(r"patron_tiles_cowboys\[\d+\] = \{(.*?)\};", (ROOT / "build" / "patrons_cowboys.c").read_text(), re.S)
    rom = bytes(int(h, 16) for h in re.findall(r"0x([0-9A-F]{2})", m.group(1)))
    vram = gb.pb.memory
    ids = list(range(84, 126)) + list(range(SHIFT0_OFS + 8, SHIFT0_OFS + 12)) + list(range(SHIFTED + 8, SHIFTED + 12))   # shifted, shift-0 pose, back view (offsets from the group's first tile)
    out = []
    for o in ids:
        t = BASE + o
        a = 0x9000 + 16 * t if t < 128 else 0x8800 + 16 * (t - 128)
        got = bytes(vram[0, a:a + 16]) if model == "cgb" else bytes(vram[a:a + 16])
        out.append((got, rom[16 * o:16 * o + 16]))
    return out


def _swap_planes(t):
    b = bytearray(t)
    for r in range(8):
        b[2 * r], b[2 * r + 1] = t[2 * r + 1], t[2 * r]
    return bytes(b)


@pytest.mark.only_model("cgb")
def test_gus_tiles_are_plane_swapped_on_color(gb):
    assert gb.mem("cur_group") == 0
    pairs = _gus_tiles(gb, "cgb")
    assert len(pairs) == 50
    assert any(g != r for g, r in pairs)
    assert all(g == _swap_planes(r) for g, r in pairs)


@pytest.mark.only_model("dmg")
def test_gus_tiles_are_the_original_ones_on_the_dmg(gb):
    assert gb.mem("cur_group") == 0
    assert all(g == r for g, r in _gus_tiles(gb, "dmg"))
