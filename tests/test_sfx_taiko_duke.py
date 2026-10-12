# The effects added for Taiko Pour's drum (SFX_DON, SFX_KA) and Duke's engine (SFX_REV): all on channel 4, started by a
# request bit (sfx_req, bit id - 1) and stepped by src/music.c voice_tick, one frame per count.
import pytest
from test_harmony import request
from test_sound import NR52, sgb, srom  # noqa: F401  (fixtures)

pytestmark = pytest.mark.timeout(120)
NR42, NR43 = 0xFF21, 0xFF22
SFX_DON, SFX_KA, SFX_REV = 10, 11, 12


def trace(gb, sfx, n):
    """(NR42, NR43) after each of n frames, from the request on (the effect's first step is written in frame 1)."""
    request(gb, sfx)
    out = []
    for _ in range(n):
        gb.run(1)
        out.append((gb.mem(NR42), gb.mem(NR43)))
    return out


def settle(gb):
    gb.run(300)          # (the title's own sounds are over)


def test_don_is_a_knock_then_a_falling_rumble(sgb):
    settle(sgb)
    t = trace(sgb, SFX_DON, 12)
    assert [x[1] for x in t[:7]] == [0x62, 0x74, 0x75, 0x76, 0x77, 0x78, 0x79] and all(x[0] == 0xB1 for x in t[:7])
    assert t[7][0] == 0, "7 frames in all (knock, then the rumble's clock sliding down), then the DAC is off"


def test_ka_is_a_short_tick(sgb):
    settle(sgb)
    t = trace(sgb, SFX_KA, 6)
    assert t[0][0] == 0xB1
    assert [x[1] for x in t[:4]] == [0x20, 0x19, 0x19, 0x19] and t[0][0] == 0xB1
    assert t[4][0] == 0, "4 frames in all (67 ms)"


def test_rev_climbs_for_fifty_frames(sgb):
    settle(sgb)
    t = trace(sgb, SFX_REV, 54)
    steps = [x[1] for x in t[:49]]
    runs = [(v, steps.count(v)) for v in dict.fromkeys(steps)]
    assert runs == [(0x4B, 9), (0x4A, 10), (0x3B, 10), (0x3A, 10), (0x39, 10)], runs   # (the first step shares its frame with the request)
    assert all(x[0] == 0xD0 for x in t[:49]) and t[49][0] == 0, "49 frames, then the DAC is off"
