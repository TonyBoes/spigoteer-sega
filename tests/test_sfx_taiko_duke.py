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


def test_don_is_a_knock_then_a_deep_boom(sgb):
    settle(sgb)
    t = trace(sgb, SFX_DON, 12)
    assert [x[1] for x in t[:8]] == [0x62, 0x81, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87] and all(x[0] == 0xF1 for x in t[:8])
    assert all(not x[1] & 8 for x in t[:8]), "15-bit noise throughout: the boom never crosses into the 7-bit buzz"
    assert t[8][0] == 0, "8 frames in all (knock, then the boom's clock sliding down), then the DAC is off"


def test_ka_is_a_bright_crack(sgb):
    settle(sgb)
    t = trace(sgb, SFX_KA, 6)
    assert [x[1] for x in t[:4]] == [0x10, 0x09, 0x09, 0x09] and all(x[0] == 0xF1 for x in t[:4])
    assert t[4][0] == 0, "4 frames in all (67 ms): short enough for eighth-note pairs 12 frames apart"


def test_hits_are_louder_than_the_old_envelope(sgb):
    settle(sgb)
    assert trace(sgb, SFX_DON, 1)[0][0] >> 4 == 15 and trace(sgb, SFX_KA, 1)[0][0] >> 4 == 15, "full volume at the strike (was 11)"


def test_rev_climbs_for_fifty_frames(sgb):
    settle(sgb)
    t = trace(sgb, SFX_REV, 54)
    steps = [x[1] for x in t[:49]]
    runs = [(v, steps.count(v)) for v in dict.fromkeys(steps)]
    assert runs == [(0x4B, 9), (0x4A, 10), (0x3B, 10), (0x3A, 10), (0x39, 10)], runs   # (the first step shares its frame with the request)
    assert all(x[0] == 0xD0 for x in t[:49]) and t[49][0] == 0, "49 frames, then the DAC is off"


def test_the_tunes_drum_groove_steps_aside_in_taiko_pour():
    """The player's drums replace the teahouse tune's own channel-4 groove while Taiko Pour is up (src/music.c taiko_solo):
    from the tune's first frames to just before the first note, no drum is written to channel 4 (NR42 / NR43 never change)."""
    from conftest import hold_stage_anim
    from test_mg import MG_PRACTICE, mg_enter
    from test_sound import make_rom
    from tk_helpers import MG_TAIKO, tk
    gb = make_rom("dmg")                # (with sound: the sound registers read back)
    gb.run(120)
    hold_stage_anim(gb)
    mg_enter(gb, MG_TAIKO, MG_PRACTICE, 0x5A17)
    for _ in range(600):
        if tk(gb)["clk"] >= 1:
            break
        gb.run(1)
    seen = set()
    for _ in range(110):
        gb.run(1)
        seen.add((gb.mem(NR42), gb.mem(NR43)))
    assert 100 < tk(gb)["clk"] < 285, "the tune is running, the first note (frame 288) not yet played"
    assert len(seen) == 1, f"channel 4 was written: {seen}"
