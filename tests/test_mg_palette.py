# Practice from BONUS > MINI GAMES on a Color: the HUD palette (BG 1) is the HUD's, not what the list left in it (owner 2026-11-03: "the instruction
# cards seem to have the wrong colors", "outlines around the medals whenever you get to the finishing message").
# The list's skin and the selected game's picture write their own colours into BG palette 1; the cards, the HUD row and the result window all draw in BG 1,
# and the medal icon (BG 4) is painted on the HUD's colour 3, so a stale BG 1 showed the card in the list's colours and a box round every medal.
# mg.c prelude puts the HUD palette back for a Practice start (a story start and the story map's keep theirs: smap_pal_back, the run's tint).
# The mini-game tests enter a game straight from the title (mg_enter), where BG 1 is still the HUD's, so none of them saw it: these go the player's way.
import pytest
from conftest import hold_stage_anim
from test_flow import run_until, state
from test_lift import cgb_bg_palette
from test_mg import GS_MINI, MG_COUNT, MG_PLAY, MG_RESULT
from test_mg_card import MG_CARD
from test_mg_list import tap, to_list
from test_scores import booted

pytestmark = pytest.mark.timeout(300)

# main_cold.c hud_palette(0): RGB15(31, 29, 22), (24, 20, 10), (29, 20, 4), (3, 2, 8)
HUD = [31 | 29 << 5 | 22 << 10, 24 | 20 << 5 | 10 << 10, 29 | 20 << 5 | 4 << 10, 3 | 2 << 5 | 8 << 10]
LIST_N = 13                                    # the DEBUG_MENU build's list without the stub: ten venue games, then the three bonus rounds


def from_list(model, sel, cards):
    """The title, BONUS > MINI GAMES with list entry `sel` selected, then A: the game starts (its card on a fresh cartridge)."""
    rom = booted(model, cards=cards)
    hold_stage_anim(rom)
    to_list(rom)
    for _ in range(sel):                         # (the player's way: Right to the game, then wait for its picture, which takes BG palette 0 or 1 alternately)
        tap(rom, "right")
        rom.run(30)
    rom.run(200)
    assert rom.mem("ml_sel") == sel
    tap(rom, "a")
    run_until(rom, lambda: state(rom) == GS_MINI and rom.pb.memory[0xFF40] & 0x80, 400)
    rom.run(40)
    return rom


@pytest.mark.parametrize("sel", range(LIST_N))
def test_every_card_from_the_list_is_in_the_huds_colours(sel):
    """A game's HOW TO PLAY card, reached through the list, has BG 1 as the HUD palette (it used the list's colours: a different card colour per game)."""
    rom = from_list("cgb", sel, cards=False)
    assert rom.mem("mg_phase") == MG_CARD
    assert list(cgb_bg_palette(rom, 1)) == HUD


@pytest.mark.parametrize("sel", range(LIST_N))
def test_the_game_and_its_result_from_the_list_are_in_the_huds_colours(sel):
    """The HUD row, the banner and the result window (and so the medal icon's box) draw in BG 1: the HUD palette at the start, at play and on the result."""
    rom = from_list("cgb", sel, cards=True)
    assert list(cgb_bg_palette(rom, 1)) == HUD, "the intro"
    run_until(rom, lambda: rom.mem("mg_phase") == MG_PLAY, 600)
    assert list(cgb_bg_palette(rom, 1)) == HUD, "play"
    rom.write("mg_score", 3000 & 255)
    rom.write(rom.addr("mg_score") + 1, 3000 >> 8)
    rom.write("mg_timer", 1)
    rom.write(rom.addr("mg_timer") + 1, 0)
    run_until(rom, lambda: rom.mem("mg_phase") == MG_RESULT, 900)
    rom.run(40)
    assert list(cgb_bg_palette(rom, 1)) == HUD, "the result"
    assert cgb_bg_palette(rom, 4)[3] == cgb_bg_palette(rom, 1)[3], "the medal icon's band colour is the result window's: no box round the medal"


def test_the_dmg_path_has_nothing_to_restore():
    """DMG: the HUD has no palette of its own (BGP is shared); the list start still reaches the card."""
    rom = from_list("dmg", 4, cards=False)
    assert rom.mem("mg_phase") == MG_CARD
