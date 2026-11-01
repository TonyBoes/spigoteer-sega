# Owner 2026-10-31: "In the Chrome cow, the full mug and the empty mug seem to be very similar, with only one color slot swapped around. Could we use
# the full mug for the empty mug and effects as well, just recolor the items as appropriate?"  On Color, in the Chrome Cow (venue 6) every sprite that
# used OBJ palette 2 (the empty mug, the held empty, the breaking glass, the boss's capacity mugs) uses OBJ palette 1 instead, with its tiles' two bit
# planes swapped (lift.c: copies in VRAM bank 1, OAM bit 3; boss.c boss_cap_stage: in place). OBJ 2 is then free there (the Atlas import gives it to DJ, a patron: only mug, glass and capacity sprites are checked). The two palettes were not
# exactly each other swapped (#FFFFF6 / #ACDEFF against #FFFFFF / #ACCDE6), so the shown colours move by at most 3 of 31 in a channel.
import re

import pytest
from boss_common import fight, play, still_regulars
from conftest import ROOT
from test_art import goto_group
from test_flow import inject_mug
from test_venues import cgb_palette, venue

pytestmark = [pytest.mark.timeout(400), pytest.mark.only_model("cgb")]

OBJ_MUG, MUG_TILES, GLASS_TILES = 56, 4, 16
OBJ_MUG_DRINK, DRINK_TILES = 84, 8
OBJ_CAP = 124
DUKE = 6


def drink_rom():
    src = (ROOT / "build" / "venue_biker.c").read_text()
    body = re.search(r"venue_biker_drink\[\d+\] = \{(.*?)\};", src, re.S).group(1)
    return bytes(int(h, 16) for h in re.findall(r"0x([0-9A-Fa-f]{2})", body))


def px(t):
    return [(t[2 * r] >> (7 - x) & 1) | (t[2 * r + 1] >> (7 - x) & 1) << 1 for r in range(8) for x in range(8)]


def chan(c):
    return (c & 31, c >> 5 & 31, c >> 10 & 31)


def sprites(gb):
    oam = bytes(gb.read("shadow_OAM", 160))
    return [oam[i:i + 4] for i in range(0, 160, 4)]


def visible(s):
    return 0 < s[0] < 160 and 0 < s[1] < 168


def scan(gb, seen):
    for s in sprites(gb):
        if visible(s):
            seen["pal"].add(s[3] & 7)
            seen["bank1"] += bool(s[3] & 8)
            if s[2] < 128:                    # (mug, glass, capacity and show tiles; a lifted patron's tiles are 128 up: DJ wears OBJ 2 since the Atlas import)
                assert s[3] & 7 != 2, f"a visible mug or glass sprite uses OBJ palette 2: {s.hex()}"


def test_empty_mug_colours_are_the_same_roles(gb):
    """The empty mug and the glass tiles in VRAM bank 1 under OBJ 1 show the colours the bank 0 tiles showed under OBJ 2 (within 3 of 31)."""
    goto_group(gb, DUKE)
    gb.run(30)
    assert gb.mem("venue_id") == DUKE
    rom = drink_rom()
    old, new = venue(DUKE)["pal"][5], cgb_palette(gb, 1, obj=True)        # (the venue's empty-drink palette: OBJ 2 itself is DJ's yellow since the Atlas import)
    mem = gb.pb.memory
    spans = [(OBJ_MUG, MUG_TILES + GLASS_TILES), (OBJ_MUG_DRINK, DRINK_TILES)]
    checked = 0
    for first, n in spans:
        for t in range(first, first + n):
            a = 0x8000 + 16 * t
            b0, b1 = bytes(mem[0, a:a + 16]), bytes(mem[1, a:a + 16])
            for p0, p1 in zip(px(b0), px(b1)):
                assert p1 == {0: 0, 1: 2, 2: 1, 3: 3}[p0], f"tile {t}: not the planes swapped"
                if p0:
                    assert all(abs(x - y) <= 3 for x, y in zip(chan(old[p0]), chan(new[p1]))), f"tile {t}: colour moved too far"
                    checked += 1
    assert checked > 100


def test_no_sprite_uses_obj_palette_2_in_normal_play(gb):
    goto_group(gb, DUKE)
    gb.run(30)
    gb.write("tip_chance", 0)
    seen = {"pal": set(), "bank1": 0}
    shots = [(1, 72), (2, 72), (3, 8), (3, 140), (5, 100), (2, 140)]   # FULL, EMPTY, BREAKING at both ends, RETURN
    for k in range(900):
        if k % 40 == 5:
            gb.write("mugs_live", 0)
            st, x = shots[(k // 40) % len(shots)]
            inject_mug(gb, (k // 40) % 4, x, st)
        gb.run(1)
        scan(gb, seen)
    assert 1 in seen["pal"]
    assert seen["bank1"], "an empty mug or a breaking glass was on screen (the test would otherwise prove nothing)"


def test_no_sprite_uses_obj_palette_2_in_the_duke_fight(gb):
    gb = fight("cgb", DUKE)   # (a fresh Color boot: the fixture's own is unused)
    still_regulars(gb)
    play(gb)
    seen = {"pal": set(), "bank1": 0}
    caps = 0
    for k in range(240):
        gb.run(1)
        scan(gb, seen)
        caps += any(visible(s) and s[2] == OBJ_CAP and s[3] & 7 == 1 for s in sprites(gb))
    assert caps, "the capacity mugs are drawn with OBJ 1"
