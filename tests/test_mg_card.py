# The HOW TO PLAY cards (owner 2026-10-14; src/mg_card.c, src/mg.c). The first time a mini-game is played its FULL card shows (a screen of its
# own: HOW TO PLAY, the name, three short lines on the buttons and the goal, the Spigoteer, PRESS A) and waits for A; the "seen" bit of each
# game is kept in the save (block "MGB1", save.c). After that the SHORT card, the banner of old (name and one line, 90 frames), shows, and A
# skips it at once. Every built game has a card; the five games being reworked (Batch D) carry a placeholder built from the banner's words.
# The mini-game tests start on a cartridge whose cards are all seen (conftest.with_cards); these ask for a fresh one (cards=False).
import re

import pytest
from conftest import BX_AT, ROOT, bx_block, check_golden, hold_stage_anim
from test_bonus import lines
from test_flow import run_until, state, tilemap_row
from test_mg import (BLANK, GLYPH_CH, GS_MINI, INTRO_LEN, MG_C, MG_COUNT, MG_H, MG_INTRO, MG_PLAY, MG_PRACTICE, MG_STORY, MG_STUB, frames,
                     mg_enter, text)
from test_mg_bonus import parse_bx
from test_mg_list import MG_FILLLINE, MG_QUICKDRAW, MG_SHAKEUP, MG_TIPS, QUEST
from test_scores import booted
from test_sound import save_ram

pytestmark = pytest.mark.timeout(300)

MG_CARD = 5
CARD_C = (ROOT / "src" / "mg_card.c").read_text()
PLAN = (ROOT / "PLAN.md").read_text()
# game ids (mg.h) in the card table's order (G_STUB, G_QD, G_BS, G_OU, G_MR, G_LR, G_AD, G_TK, G_MM, G_MK, G_TS, G_PO, G_B0, G_B1, G_B2)
IDS = [MG_STUB, 0, 5, 3, 6, 2, 9, 7, 4, 8, 1, 11, MG_SHAKEUP, MG_FILLLINE, MG_TIPS]
PENDING = ["BATTERY SORT", "MILK RUN", "LOG ROLL", "MARSHMALLOW DROP", "SHIRT CANNON"]
# the story font's punctuation (build/story.h: ST_GLYPH_PERIOD .. COLON are STORY_FONT_BASE + 0..6)
PUNCT = {QUEST - 3 + i: c for i, c in enumerate(".,!?'-:")}


def cards():
    """The card table of src/mg_card.c: [(name, [line1, line2, line3], pending)] in G_* order."""
    out = []
    for m in re.finditer(r'/\* G_\w+\s*\*/ \{ "([^"]*)", \{ "([^"]*)", "([^"]*)", "([^"]*)" \} \},(.*)', CARD_C):
        out.append((m.group(1), [m.group(2), m.group(3), m.group(4)], "PENDING" in m.group(5)))
    return out


def row_text(gb, row):
    """A map row as text, the HUD letters and digits and the story font's punctuation."""
    out = ""
    for t in tilemap_row(gb, row, 0, 20):
        out += GLYPH_CH.get(t, PUNCT.get(t, " ")) if t != BLANK else " "
    return out.strip()


def banner_words():
    """mg.c's mg_instr[] (today's banner line of each game, G_* order)."""
    body = re.search(r"mg_instr\[MG_GAMES\] = \{(.*?)\};", MG_C, re.S).group(1)
    return re.findall(r'"([^"]*)"', body)


# ---- the table ------------------------------------------------------------------------------------------------------------------
def test_every_built_game_has_a_card():
    """One entry for each of mg.h's G_* games (the stub, the Pour-Off and the three old bonus rounds included); a name, a first line, only
    characters the fonts have, no line wider than the screen's 20 columns."""
    games = re.search(r"#define MG_GAMES\s+(\d+)", MG_H).group(1)
    table = cards()
    assert len(table) == int(games) == len(IDS) == 15
    enum = re.search(r"enum \{ (G_STUB.*?) \};", MG_H).group(1).split(", ")
    assert len(enum) == len(table)
    for (name, ls, pend), g in zip(table, enum):
        assert name and ls[0], g
        for t in [name] + ls:
            assert re.fullmatch(r"[A-Z0-9 .,!?:'-]*", t) and len(t) <= 20, (g, t)
            if not pend:                       # a real card keeps two columns of margin (a placeholder is the banner's own line)
                assert len(t) <= 18, (g, t)
    names = re.search(r"mg_name\[MG_GAMES\]\s*= \{(.*?)\};", MG_C, re.S).group(1)
    assert re.findall(r'"([^"]*)"', names) == [n for n, _, _ in table], "the card names are the banner names"


def test_the_games_being_reworked_have_placeholder_cards_from_the_banner():
    """T-Shirt Cannon, Log Roll, Marshmallow Drop, Battery Sort and Milk Run: card text pending the Batch D rework (PLAN.md): their one line is
    today's banner line, the other two empty. The others have three real lines."""
    table, words = cards(), banner_words()
    assert len(words) == len(table)
    pending = [n for n, _, p in table if p]
    assert sorted(pending) == sorted(PENDING)
    for (name, ls, p), w in zip(table, words):
        if p:
            assert ls == [w, "", ""], name
        else:
            assert all(ls), name
    after = PLAN.split("card text pending the Batch D rework")[1][:300]
    assert all(n in after for n in ("T-Shirt Cannon", "Log Roll", "Marshmallow Drop", "Battery Sort", "Milk Run")), "marked in PLAN.md"


# ---- the full card ----------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_every_game_shows_its_full_card_first(model):
    """On a fresh cartridge each game starts with its card: MG_CARD, the screen all HUD text (HOW TO PLAY on row 1, the name on row 4, the
    three lines on rows 6, 8, 10, PRESS A on row 16 which blinks), no more than the Spigoteer's sprites, and it waits: 200 frames later it is
    still the card. The game's own screen does not exist yet."""
    table = cards()
    for gid, (name, ls, _) in zip(IDS, table):
        with booted(model, cards=False) as gb:
            mg_enter(gb, gid, MG_PRACTICE)
            assert state(gb) == GS_MINI and gb.mem("mg_phase") == MG_CARD and gb.mem("mg_id") == gid, name
            frames(gb, 3)
            assert row_text(gb, 1) == "HOW TO PLAY" and row_text(gb, 4) == name, name
            assert [row_text(gb, r) for r in (6, 8, 10)] == ls, name
            prompt = "A NEXT  B BACK" if gid == MG_STUB else "A START  B BACK"      # (from the list: B goes back; the stub has two pages)
            assert row_text(gb, 16) == prompt and row_text(gb, 2) == "" and row_text(gb, 12) == "", name
            for _ in range(4):                                     # the prompt blinks (32 frames on, 32 off)
                gb.run(40)
                assert row_text(gb, 16) in (prompt, ""), name
            frames(gb, 120)
            assert gb.mem("mg_phase") == MG_CARD and gb.mem("mg_t") > 100, "it waits for A"
            assert max(lines(gb)) <= 10 and len([s for s in gb.visible_sprites()]) <= 4, name
            for b in ("start", "left"):
                gb.press(b, 2)
            gb.run(5)
            assert gb.mem("mg_phase") == MG_CARD, "only A goes on (and B, from the list: back)"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_starts_the_game_then_the_short_card_shows_and_a_skips_it(model):
    """A on the full card builds the game's screen: the short card (name and one line, MG_INTRO for INTRO_LEN frames unless A); the card
    is seen from then on, also after a retry; the save has the bit; a reset keeps it (the next game's card is still fresh)."""
    with booted(model, cards=False) as gb:
        hold_stage_anim(gb)
        mg_enter(gb, MG_QUICKDRAW, MG_PRACTICE)
        check_golden(gb, "card_full_qd")
        gb.run(3)
        gb.press("a", 2)
        run_until(gb, lambda: gb.mem("mg_phase") == MG_INTRO and gb.pb.memory[0xFF40] & 0x80, 30)
        gb.run(2)
        assert text(gb, 2) == "QUICK DRAW" and text(gb, 3) == "PRESS A OR B ON DRAW", "the short card"
        check_golden(gb, "card_short_qd")
        n = 0
        while gb.mem("mg_phase") == MG_INTRO and n < 200:
            gb.run(1)
            n += 1
        assert INTRO_LEN - 8 <= n <= INTRO_LEN, "no A: the banner runs its 90 frames"
        # the same game again (a retry / the list): no full card, the short one, and A skips it at once
        mg_enter(gb, MG_QUICKDRAW, MG_PRACTICE)
        assert gb.mem("mg_phase") == MG_INTRO and text(gb, 2) == "QUICK DRAW"
        gb.run(3)
        gb.press("a", 2)
        assert gb.mem("mg_phase") == MG_COUNT and text(gb, 2) == "READY", "A skipped the short card at once"
        # another game is still new
        mg_enter(gb, 3, MG_STORY)
        assert gb.mem("mg_phase") == MG_CARD, "Order Up!'s card is its own"
        out = save_ram(gb)
    played, medals, seen = parse_bx(out)
    assert seen == 1 | 1 << 3 and played == 0 and medals == 0
    with booted(model, out, cards=False) as gb:
        mg_enter(gb, MG_QUICKDRAW, MG_PRACTICE)
        assert gb.mem("mg_phase") == MG_INTRO, "the seen bit survived the reset"
        mg_enter(gb, 7, MG_PRACTICE)
        assert gb.mem("mg_phase") == MG_CARD


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_story_shows_the_card_too_and_the_short_card_skips_there(model):
    """STORY and ARCADE start their mini-game through mg_enter as well: the full card first, A, the banner; the count-in cannot be skipped
    there (as before) but the short card can."""
    with booted(model, cards=False) as gb:
        mg_enter(gb, MG_QUICKDRAW, MG_STORY)
        assert gb.mem("mg_phase") == MG_CARD
        gb.run(3)
        gb.press("a", 2)
        run_until(gb, lambda: gb.mem("mg_phase") == MG_INTRO and gb.pb.memory[0xFF40] & 0x80, 30)
        gb.run(3)
        gb.press("a", 2)
        assert gb.mem("mg_phase") == MG_COUNT
        gb.run(3)
        gb.press("a", 2)
        gb.run(3)
        assert gb.mem("mg_phase") == MG_COUNT, "no skipping the count-in in the story"
        out = save_ram(gb)
    assert parse_bx(out)[2] == 1


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_debug_select_run_does_not_record_a_seen_card(model):
    """save_lock SAVE_LOCK_DEBUG: nothing is written, so the full card comes again each time (A still starts the game)."""
    with booted(model, cards=False) as gb:
        gb.write("save_lock", 2)
        mg_enter(gb, MG_QUICKDRAW, MG_STORY)
        gb.run(3)
        gb.press("a", 2)
        run_until(gb, lambda: gb.mem("mg_phase") == MG_INTRO and gb.pb.memory[0xFF40] & 0x80, 30)
        mg_enter(gb, MG_QUICKDRAW, MG_STORY)
        assert gb.mem("mg_phase") == MG_CARD
        out = save_ram(gb)
    assert out[BX_AT:BX_AT + 4] != b"MGB1" or parse_bx(out)[2] == 0


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_card_is_never_wider_than_the_screen_and_the_games_still_run(model):
    """Every game through the full card and A to its first play frame: the game's own screen builds (the stub and the others), <= 10 sprites
    a line all the way."""
    for gid in IDS:
        with booted(model, cards=False) as gb:
            mg_enter(gb, gid, MG_PRACTICE)
            gb.run(3)
            gb.press("a", 2)
            if gid == MG_STUB:                                     # (two pages)
                gb.run(3)
                gb.press("a", 2)
            run_until(gb, lambda: gb.mem("mg_phase") == MG_INTRO and gb.pb.memory[0xFF40] & 0x80, 30)
            gb.run(3)
            gb.press("a", 2)                                       # the short card skipped
            frames(gb, 100)
            assert state(gb) == GS_MINI and gb.mem("mg_phase") in (MG_COUNT, MG_PLAY, 2), gid


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_b_on_the_full_card_goes_back_to_the_list_with_no_medal(model):
    """From BONUS > MINI GAMES B on the full card is the pause QUIT's clean leave: the list, no medal, and the card counts as seen."""
    from test_mg_list import best, to_list
    from test_mg import GS_MGLIST
    with booted(model, cards=False) as gb:
        hold_stage_anim(gb)
        to_list(gb)
        medals = best(gb)
        gb.press("a", 2)
        run_until(gb, lambda: gb.mem("mg_phase") == MG_CARD and gb.pb.memory[0xFF40] & 0x80, 60)
        gb.run(3)
        assert row_text(gb, 16) == "A START  B BACK"
        gb.press("b", 2)
        run_until(gb, lambda: state(gb) == GS_MGLIST and gb.pb.memory[0xFF40] & 0x80, 60)
        gb.run(3)
        assert gb.mem("mg_phase") == MG_CARD or gb.mem("overlay_on") == 0
        assert best(gb) == medals, "no medal"
        mg_enter(gb, MG_QUICKDRAW, MG_PRACTICE)
        assert gb.mem("mg_phase") == MG_INTRO, "the card was read: the short one now"
        out = save_ram(gb)
    assert parse_bx(out)[2] & 1, "the seen bit is saved"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_b_on_the_card_starts_the_game_where_there_is_no_list(model):
    with booted(model, cards=False) as gb:
        mg_enter(gb, MG_QUICKDRAW, MG_STORY)
        gb.run(3)
        assert row_text(gb, 16) == "PRESS A"
        gb.press("b", 2)
        run_until(gb, lambda: gb.mem("mg_phase") == MG_INTRO and gb.pb.memory[0xFF40] & 0x80, 30)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_two_page_card_turns_its_page_before_it_starts(model):
    """The stub's card has two pages: NEXT (story / ARCADE) or A NEXT  B BACK (list) on the first, A turns, the last page's prompt is
    PRESS A / A START  B BACK, and only A on the last page starts the game."""
    with booted(model, cards=False) as gb:
        hold_stage_anim(gb)
        mg_enter(gb, MG_STUB, MG_STORY)
        gb.run(3)
        assert [row_text(gb, r) for r in (6, 8, 10, 16)] == ["PRESS A ON GREEN", "NOT ON RED", "5 ROUNDS", "NEXT"]
        check_golden(gb, "card_stub_page1")
        gb.press("a", 2)
        gb.run(3)
        assert gb.mem("mg_phase") == MG_CARD
        assert [row_text(gb, r) for r in (4, 6, 8, 10, 16)] == ["GREEN LIGHT", "EARLY IS A MISS", "SLOW IS A MISS", "KEEP YOUR EYES UP", "PRESS A"]
        gb.press("a", 2)
        run_until(gb, lambda: gb.mem("mg_phase") == MG_INTRO and gb.pb.memory[0xFF40] & 0x80, 30)
    with booted(model, cards=False) as gb:
        mg_enter(gb, MG_STUB, MG_PRACTICE)
        gb.run(3)
        assert row_text(gb, 16) == "A NEXT  B BACK"
        gb.press("a", 2)
        gb.run(3)
        assert row_text(gb, 6) == "EARLY IS A MISS" and row_text(gb, 16) == "A START  B BACK"
