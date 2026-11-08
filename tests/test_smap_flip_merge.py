# The Color flip-merge of the story map (tools/gen_smap_world.py Model.merge_flips, src/smap_eng.c add_cell): two 8 x 8 blocks that are mirror images share one tile id; the
# cell word's bit 15 selects the alternate, the slot table's bits 11-12 say which flip it is (attribute bit 5: X, bit 6: Y). Checked here:
#   - the built data: every cell of every unlock state shows the same 64 pixels as the unmerged world; the merge saves ids; the tile bank holds them; a pinned (animated) block is
#     never merged;
#   - the engine: the flip bits reach the screen (the walking tests compare the screen with the world's render, which flips the alternates), and the spare bits of the slot
#     table (13 to 15, which hardware may leave as junk) change nothing: a copy of the ROM with those bits set on every entry shows the same views.
import json
import sys

import pytest
import test_sound
import test_story_map as sm
import test_story_map_world as tw
from conftest import ROOT

pytestmark = pytest.mark.timeout(600)


@pytest.fixture(scope="module")
def gen():
    sys.path.insert(0, str(ROOT / "tools"))
    import gen_smap_world as g
    return g


def test_every_cell_of_every_state_shows_the_same_pixels_as_the_unmerged_world(gen):
    cg = gen.Model(True)
    cg.verify_fog()                                           # (asserts word_sig(word) == the cell's own block for every cell of the ten states)
    assert cg.nt < cg.nsig, "mirror images were merged"
    assert any(f for f in cg.altflip) and set(cg.altflip) <= {0, 1, 2, 3}
    assert cg.nt * 16 + 69 <= 16384, "the Color tiles fit one ROM bank"
    assert any(int(cg.alt[p].max()) for p in cg.alt), "some cell shows an alternate"
    # a cell word's bit 15 is set exactly where the cell shows the alternate; the palette stays in bits 10-14
    for c in (0, 100, 1000, 2000):
        w = cg.cell[c]
        assert (w >> 10) & 31 == int(cg.pals[10][c // gen.CW, c % gen.CW])
        assert w >> 15 == int(cg.alt[10][c // gen.CW, c % gen.CW])


def test_the_dmg_data_set_is_not_merged(gen):
    dm = gen.Model(False)
    assert dm.nt == dm.nsig and not any(dm.altflip) and not any(int(dm.alt[p].max()) for p in dm.alt)
    assert all(w < 1024 for w in dm.cell), "no DMG word carries a palette or a flip bit"


def test_a_pinned_block_is_never_merged(gen, monkeypatch):
    plain = gen.Model(True)
    # a cell whose block has a mirror image elsewhere, which the plain merge pairs
    pair = None
    for p in (10,):
        for y in range(gen.CH):
            for x in range(gen.CW):
                if int(plain.alt[p][y, x]):
                    pair = (x, y)
                    break
            if pair:
                break
    assert pair, "the plain merge made an alternate"
    # pin that cell: it must keep an id of its own (no alternate bit, and no other block shares its id)
    monkeypatch.setattr(gen.W, "ANIM_CELLS", {pair}, raising=False)
    pinned = gen.Model(True)
    x, y = pair
    assert int(pinned.alt[10][y, x]) == 0
    tid = int(pinned.grids[10][y, x])
    assert pinned.altflip[tid] == 0, "nothing is merged into a pinned block's id"
    sharers = {int(pinned.sg[10][yy, xx]) for yy in range(gen.CH) for xx in range(gen.CW) if int(pinned.grids[10][yy, xx]) == tid}
    assert len(sharers) == 1, "one distinct block per pinned id"


def test_the_slot_table_masks_variant_and_flips_apart(gen):
    world = json.loads((ROOT / "build" / "smap_world.json").read_text())
    assert world["vars_max"] <= 4
    for t, fl in enumerate(world["alt_flip_c"]):
        assert 0 <= fl <= 3
        assert world["slot_of_c"][t] < 352 and world["var_of_c"][t] < 4


@pytest.fixture
def junk_rom(tmp_path):
    """build/game.gb with bits 13..15 set on every entry of smap_c_slotvar"""
    noi = (ROOT / "build" / "game.noi").read_text()
    addr = next(int(ln.split()[2], 16) for ln in noi.splitlines() if ln.startswith("DEF _smap_c_slotvar "))
    n = len(json.loads((ROOT / "build" / "smap_world.json").read_text())["alt_flip_c"])
    bank, off = addr >> 16, addr & 0xFFFF
    rom = bytearray((ROOT / "build" / "game.gb").read_bytes())
    at = bank * 0x4000 + (off - 0x4000)
    for i in range(n):
        rom[at + 2 * i + 1] |= 0xE0                           # the high byte's bits 5..7 = word bits 13..15
    p = tmp_path / "junk.gb"
    p.write_bytes(bytes(rom))
    (tmp_path / "junk.noi").write_text(noi)                   # (the symbols are read from the file next to the ROM)
    return p


@pytest.mark.parametrize("progress, stops", [(10, (0, 4, tw.TOWN))])
def test_junk_in_the_spare_slot_table_bits_changes_nothing(monkeypatch, junk_rom, progress, stops):
    monkeypatch.setattr(test_sound, "ROM", junk_rom)
    for s in stops:
        gb = sm.to_map("cgb", progress, stop=s)
        w = tw.Watch(gb, "cgb", progress)
        w.frame()
        w.frame()
        assert not w.bad, (s, w.bad)
