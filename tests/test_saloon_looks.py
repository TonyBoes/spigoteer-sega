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


def test_the_color_only_looks_are_in_vram_bank_1(gb):
    if gb.model_name != "cgb":
        pytest.skip("Color only")
    b = blob()
    assert len(b) == 252 * 16
    vram = gb.pb.memory
    got = bytes(vram[1, 0x9000:0x9800]) + bytes(vram[1, 0x8800:0x9000])[:124 * 16]
    assert got == b, "BG ids 0..127 at 0x9000, 128..251 at 0x8800, all from the one blob (the asm copy and its C twin alike)"


def test_the_dmg_keeps_the_three_looks(gb):
    if gb.model_name != "dmg":
        pytest.skip("DMG only")
    for _ in range(60):
        gb.run(20)
        assert all(v < 3 for v in gb.read("patron_variant", MAX_P)), "variant bytes 0-2 only"


def test_the_color_saloon_spawns_all_eight_looks(gb):
    if gb.model_name != "cgb":
        pytest.skip("Color only")
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
