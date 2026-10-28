# The pause menu's HOW TO PLAY card opens and closes through the white fade (src/pause.c CARD_FADE, src/trans.c): the pause mix loses no tick through
# it, and the menu's registers (WY, LYC, STAT, IE, the LCDC window bits) are exactly as before once the card has closed.
import pytest
from split_helpers import win_lyc

from boss_common import fight, play
from tick_helpers import FRAME, LATE, tick_log
from test_pause import CARD_FRAMES, MODES, PAUSED, menu_rows, tap

pytestmark = pytest.mark.timeout(600)


def regs(gb):
    """WY, LYC, STAT's interrupt-enable bits, IE, and the LCDC bits of the window (enable 5, map 6) and the sprites (1), the frame's start."""
    gb.run(1)
    return dict(wy=gb.mem(0xFF4A), wx=gb.mem(0xFF4B), lyc=win_lyc(gb.mem), stat=gb.mem(0xFF41) & 0x78, ie=gb.mem(0xFFFF),
                lcdc_win=gb.mem(0xFF40) & 0x60, lcdc_obj=gb.mem(0xFF40) & 0x02, lcdc_on=gb.mem(0xFF40) & 0x80, nr51=gb.mem(0xFF25), nr50=gb.mem(0xFF24))


@pytest.mark.parametrize("model", MODES)
@pytest.mark.parametrize("c", [0, 3, 7])
def test_the_card_fade_restores_the_menu_registers_exactly(model, c):
    with fight(model, c) as gb:
        play(gb)
        gb.run(40)
        tap(gb, "start", 3)
        assert gb.mem("game_state") == PAUSED and menu_rows(gb)[1] == "HOW TO PLAY", menu_rows(gb)
        before = regs(gb)
        assert before["wy"] != 0 and before["lyc"] > before["wy"], before
        tap(gb, "down")
        tap(gb, "a", CARD_FRAMES)
        card = regs(gb)
        assert card["wy"] == 0 and card["lyc"] == 255, card
        tap(gb, "b", CARD_FRAMES)
        assert menu_rows(gb)[1].startswith("> HOW TO PLAY"), menu_rows(gb)
        after = regs(gb)
        assert after == dict(before, lcdc_obj=after["lcdc_obj"]) and after["lcdc_obj"] == before["lcdc_obj"], (before, after)
        for _ in range(5):                         # (and it stays so: the menu's own frames, the window shown and hidden by the line interrupt)
            assert regs(gb) == before


@pytest.mark.parametrize("model", MODES)
@pytest.mark.parametrize("c", [0, 3])
def test_the_pause_mix_loses_no_tick_through_the_card_fades(model, c, monkeypatch):
    import test_story
    from test_sound import make_rom
    def booted_with_sound(model, ram=None, cards=True):          # (the fight's rom with the APU on: the pause mix is NR51, which reads back 0 without it)
        rom = make_rom(model, ram, sound=True, cards=cards)
        rom.run(120)
        return rom
    monkeypatch.setattr(test_story, "booted", booted_with_sound)
    with fight(model, c) as gb:
        assert gb.mem(0xFF26) & 0x80, "sound on"
        play(gb)
        gb.run(40)
        tap(gb, "start", 3)
        gb.run(20)
        st = tick_log(gb)
        n0 = len(st)
        tap(gb, "down")
        tap(gb, "a", CARD_FRAMES)
        tap(gb, "b", CARD_FRAMES)
        gb.run(10)
        t = st[max(n0 - 1, 0):]
        gaps = [(b - a) / FRAME for a, b in zip(t, t[1:])]
        assert len(t) > 125, len(t)                # (the tune ticked on the whole time: about one a frame through 130 frames)
        assert max(gaps) <= LATE, (max(gaps), [round(g, 2) for g in gaps if g > 1.3])
