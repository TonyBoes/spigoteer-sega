# Practice's difficulty (owner 2026-10-15: "put in the selection but make every difficulty level the same right now"): BONUS > MINI GAMES
# offers EASY / NORMAL / HARD for every game (LEFT / RIGHT cycle, the header names the mode, the info lines show that mode's medal);
# a medal is saved per game per mode (mg_best bits 0-1 / 2-3 / 4-5, the bonus rounds' EASY and HARD medals in "MD" at 0x7A, NORMAL in
# MGB1); STORY and ARCADE always play NORMAL; every game plays exactly the same in the three modes for now.
import re

import pytest
import test_menu_cursor as mc
import test_mg_list as ml
from conftest import ROOT, TM_BONUS, menu_tap
from test_flow import TITLE, run_until, state
from test_mg import GS_MGLIST, GS_MINI, MG_PRACTICE, MG_RESULT, MG_STORY, frames, mg_enter, until
from test_mg_bonus import BX_AT, medal_of, parse_bx
from test_rush import pr_block2
from test_scores import booted, set_score, table, v7_image
from test_sound import save_ram

pytestmark = pytest.mark.timeout(600)

NORMAL, HARD, EASY = 0, 1, 2                      # mg.h MG_D_*: mg_mode bits 1-2
WORD = {NORMAL: "NORMAL", HARD: "HARD", EASY: "EASY"}
MODE_BITS = {NORMAL: 0, HARD: 2, EASY: 4}
DX_AT = BX_AT + 10                                # the bonus rounds' EASY / HARD medals "MD" (src/save.c)
GAMES = 14                                        # the debug list: ten venues, three bonus rounds, the stub
BONUS_FIRST = 10
BONUS_ID = {10: 12, 11: 13, 12: 14}               # list line -> MG_* id
SHIFT = {NORMAL: 0, HARD: 2, EASY: 4}


def header(gb):
    return ml.line(gb, 0).strip()


def goto_mode(gb, want):
    """Press RIGHT until the header says `want` (at most three presses)."""
    for _ in range(3):
        if header(gb) == "MINI GAMES  " + WORD[want]:
            return
        ml.tap(gb, "right")
        gb.run(4)
    assert header(gb) == "MINI GAMES  " + WORD[want]


def dx_block(easy=0, hard=0, magic=b"MD", bad_sum=False):
    b = bytearray(6)
    b[0:2] = magic
    b[2], b[3] = easy, hard
    c = (0x5A + sum(b[:4])) & 255
    b[4], b[5] = c, c ^ 0xFF
    if bad_sum:
        b[4] ^= 1
    return bytes(b)


def dx_parse(ram):
    b = ram[DX_AT:DX_AT + 6]
    assert b[:2] == b"MD", b[:2]
    c = (0x5A + sum(b[:4])) & 255
    assert b[4] == c and b[5] == c ^ 0xFF
    return b[2], b[3]


def with_bytes(ram, at, blob):
    r = bytearray(ram)
    r[at:at + len(blob)] = blob
    return bytes(r)


def mini_best(gb, g):
    return list(gb.read("mg_best", 10))[g]


def finish(gb, score=None):
    """The running game ends at once (as the tests of every game do): its result window shows."""
    if score is not None:
        set_score(gb, score)
    gb.write("mg_phase", MG_RESULT)
    run_until(gb, lambda: gb.mem("overlay_on") == 1, 20)
    frames(gb, 3)


def play_from_list(gb, rounds=None, score=None):
    """A on the selected game, then its result at once (Quick Draw: `rounds` won; a bonus round: `score` points), B back to the list."""
    gb.press("a", 2)
    run_until(gb, lambda: state(gb) == GS_MINI and gb.pb.memory[0xFF40] & 0x80, 60)
    mode = gb.mem("mg_mode")
    if rounds is not None:
        for i, w in enumerate(rounds if isinstance(rounds, tuple) else (rounds, 0)):
            gb.write(gb.addr("story_scratch") + 2 + i, w)         # Quick Draw's rounds won: the player's, the Kid's
    finish(gb, score)
    medal = gb.mem("mg_medal")
    gb.press("b", 2)
    run_until(gb, lambda: state(gb) == GS_MGLIST and gb.pb.memory[0xFF40] & 0x80, 60)
    gb.run(10)
    return mode, medal


# ---- the selection ------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_left_right_cycle_the_mode_on_every_entry_and_the_header_and_info_lines_follow(model):
    """On every one of the 14 lines: RIGHT goes NORMAL > HARD > EASY > NORMAL (EASY, NORMAL, HARD is the order on the screen, so RIGHT from
    HARD wraps to EASY), LEFT goes back, SELECT goes forward; the header names the mode, the "<MODE> ..." info line follows, the keys line
    says L R MODE; the mug stays on the line of the selected game."""
    with ml.to_list(booted(model)) as gb:
        for k in range(GAMES):
            assert gb.mem("ml_sel") == k
            for mode in (NORMAL, HARD, EASY):
                assert header(gb) == "MINI GAMES  " + WORD[mode], (k, mode)
                assert ml.line(gb, 15).strip() == WORD[mode] + " NO MEDAL YET"
                assert ml.line(gb, 16).strip() == ml.KEYS
                mc.list_ok(gb, k)
                ml.tap(gb, "right")
                gb.run(4)
            for mode in (EASY, HARD, NORMAL):         # LEFT: the other way round
                ml.tap(gb, "left")
                gb.run(4)
                assert header(gb) == "MINI GAMES  " + WORD[mode], (k, mode)
            ml.tap(gb, "select")
            gb.run(4)
            assert header(gb) == "MINI GAMES  HARD"
            ml.tap(gb, "left")
            gb.run(4)
            assert header(gb) == "MINI GAMES  NORMAL"
            ml.tap(gb, "down")
            gb.run(4)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_mode_outlasts_a_game_and_the_title_and_reaches_the_game(model):
    """The mode chosen stays on the list while a game is played and over a visit to the title; A plays the game with it (mg_mode bits 1-2),
    for every line, and the cursor and its line agree on the way back (the result window's B, then the list's B and A)."""
    with ml.to_list(booted(model)) as gb:
        for mode in (HARD, EASY, NORMAL):
            goto_mode(gb, mode)
            for k in range(GAMES):
                assert gb.mem("ml_sel") == k
                got, _ = play_from_list(gb, score=0)
                assert got == MG_PRACTICE | MODE_BITS[mode], (k, mode, got)
                mc.list_ok(gb, k)
                assert header(gb) == "MINI GAMES  " + WORD[mode]
                ml.tap(gb, "down")
                gb.run(4)
            assert gb.mem("ml_sel") == 0
        goto_mode(gb, EASY)
        gb.press("b", 2)
        mc.title_ok(gb, TM_BONUS, 1)
        menu_tap(gb, "a")
        mc.list_ok(gb, 0)
        assert header(gb) == "MINI GAMES  EASY"


# ---- a medal per game per mode ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_medal_earned_in_one_mode_shows_only_in_that_mode(model):
    """Quick Draw: a bronze in EASY, a gold in HARD, a silver in NORMAL (rounds won 1-0, 3-0, 3-1): each only under its own header, in the list's
    medal column and the info line; the byte holds them in its three two-bit fields; a worse medal later changes nothing."""
    with ml.to_list(booted(model)) as gb:
        want = {}
        for mode, rounds in ((EASY, 1), (HARD, 3), (NORMAL, (3, 1))):
            goto_mode(gb, mode)
            _, medal = play_from_list(gb, rounds=rounds)
            assert medal and header(gb) == "MINI GAMES  " + WORD[mode]
            want[mode] = medal
            assert ml.line(gb, 2).split()[-1] == ["", "BRONZE", "SILVER", "GOLD"][medal]
            assert ml.line(gb, 15).strip() == f"{WORD[mode]} BEST {['', 'BRONZE', 'SILVER', 'GOLD'][medal]}"
        assert len(set(want.values())) == 3
        assert mini_best(gb, 0) == sum(want[m] << SHIFT[m] for m in want)
        for mode in (NORMAL, HARD, EASY):
            goto_mode(gb, mode)
            assert ml.line(gb, 2).split()[-1] == ["", "BRONZE", "SILVER", "GOLD"][want[mode]]
        goto_mode(gb, HARD)
        play_from_list(gb, rounds=1)                  # a worse HARD medal: the gold stays
        assert (mini_best(gb, 0) >> 2) & 3 == want[HARD]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_medal_in_hard_is_not_in_normal_or_easy(model):
    with ml.to_list(booted(model)) as gb:
        goto_mode(gb, HARD)
        _, medal = play_from_list(gb, rounds=3)
        assert medal == 3 and mini_best(gb, 0) == 3 << 2
        assert ml.line(gb, 2).split()[-1] == "GOLD" and ml.line(gb, 15).strip() == "HARD BEST GOLD"
        for mode in (EASY, NORMAL):
            goto_mode(gb, mode)
            assert ml.line(gb, 2).strip() == "QUICK DRAW" and ml.line(gb, 15).strip() == WORD[mode] + " NO MEDAL YET"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_story_always_plays_normal_and_records_a_normal_medal(model):
    """The list left in HARD, then a mini-game of the story (mg_enter MG_STORY): mg_mode has no difficulty and a gold lands in the NORMAL field."""
    with ml.to_list(booted(model)) as gb:
        goto_mode(gb, HARD)
        gb.press("b", 2)
        mc.title_ok(gb, TM_BONUS, 1)
        mg_enter(gb, 0, MG_STORY)
        assert gb.mem("mg_mode") == MG_STORY
        gb.write(gb.addr("story_scratch") + 2, 3)
        finish(gb)
        assert gb.mem("mg_medal") == 3 and mini_best(gb, 0) == 3


# ---- the bonus rounds' medals --------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_bonus_round_keeps_a_medal_per_mode(model):
    """Can Shake-Up (line 10): bronze in EASY, gold in HARD, silver in NORMAL (1000 / 3000 / 2000 points): NORMAL's is in MGB1 byte 5 as before,
    EASY's and HARD's in the "MD" block; each shows only under its own header; the save round-trips them."""
    with ml.to_list(booted(model)) as gb:
        for _ in range(BONUS_FIRST):
            ml.tap(gb, "down")
        gb.run(4)
        for mode, pts, medal in ((EASY, 1000, 1), (HARD, 3000, 3), (NORMAL, 2000, 2)):
            goto_mode(gb, mode)
            _, got = play_from_list(gb, score=pts)
            assert got == medal, (mode, got)
        for mode, medal in ((NORMAL, 2), (HARD, 3), (EASY, 1)):
            goto_mode(gb, mode)
            assert ml.line(gb, 11).split()[-1] == ["", "BRONZE", "SILVER", "GOLD"][medal]
            assert ml.line(gb, 15).strip() == f"{WORD[mode]} BEST {['', 'BRONZE', 'SILVER', 'GOLD'][medal]}"
        ram = save_ram(gb)
    _, medals, _ = parse_bx(ram)
    assert medal_of(medals, 0) == 2, "NORMAL stays in MGB1"
    assert dx_parse(ram) == (1, 3), "EASY, HARD"
    with booted(model, ram) as gb:
        ml.to_list(gb)
        for _ in range(BONUS_FIRST):
            ml.tap(gb, "down")
        gb.run(4)
        for mode, medal in ((NORMAL, 2), (HARD, 3), (EASY, 1)):
            goto_mode(gb, mode)
            assert ml.line(gb, 11).split()[-1] == ["", "BRONZE", "SILVER", "GOLD"][medal], mode


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_all_three_bonus_rounds_and_ten_games_round_trip_in_every_mode(model):
    """Every mode's medal of every game in one save: the mini-games' bytes (MGP2) and the bonus rounds' blocks come back exactly."""
    with ml.to_list(booted(model)) as gb:
        want = [0] * 10
        for mode in (EASY, HARD, NORMAL):
            goto_mode(gb, mode)
            _, m = play_from_list(gb, rounds={EASY: 1, HARD: 3, NORMAL: (3, 1)}[mode])
            want[0] |= m << SHIFT[mode]
        ram = save_ram(gb)
    assert ml.parse_block(ram)[1][0] == want[0]
    with booted(model, ram) as gb:
        assert mini_best(gb, 0) == want[0]
        ram2 = save_ram(gb)
    assert ml.parse_block(ram2)[1][0] == want[0]


# ---- old saves and bad blocks --------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_an_old_save_keeps_its_medals_as_normal_and_has_none_for_easy_and_hard(model):
    """A save from before the difficulties (an MGP1 block with normal medals only, an MGB1 block without the "MD" block): NORMAL shows them,
    EASY and HARD show nothing; the next medal earned in EASY is written without disturbing the rest."""
    ram = ml.with_block(v7_image(), ml.pr_block(0x3FF, [ml.MEDAL_GOLD, ml.MEDAL_SILVER, ml.MEDAL_BRONZE]))
    bx = bytearray(10)
    bx[0:4] = b"MGB1"
    bx[4], bx[5] = 1, 3 << 0                          # the shake-up played, gold
    c = (0x5A + sum(bx[:8])) & 255
    bx[8], bx[9] = c, c ^ 0xFF
    ram = with_bytes(ram, BX_AT, bytes(bx))
    with ml.to_list(booted(model, ram)) as gb:
        assert list(gb.read("mg_best", 3)) == [3, 2, 1]
        assert ml.line(gb, 2).split()[-1] == "GOLD" and ml.line(gb, 15).strip() == "NORMAL BEST GOLD"
        for _ in range(BONUS_FIRST):
            ml.tap(gb, "down")
        gb.run(4)
        assert ml.line(gb, 11).split()[-1] == "GOLD"
        for mode in (HARD, EASY):
            goto_mode(gb, mode)
            assert ml.line(gb, 11).split()[-1] == "SHAKE-UP" and ml.line(gb, 15).strip() == WORD[mode] + " NO MEDAL YET"
        for _ in range(BONUS_FIRST):
            ml.tap(gb, "up")
        gb.run(4)
        for mode in (HARD, EASY):
            goto_mode(gb, mode)
            assert ml.line(gb, 2).strip() == "QUICK DRAW" and ml.line(gb, 3).strip() == "SHIRT CANNON"
        _, m = play_from_list(gb, rounds=1)           # EASY (the last goto): a bronze
        assert m == 1 and mini_best(gb, 0) == 3 | 1 << 4
        ram = save_ram(gb)
    assert ml.parse_block(ram)[1][:3] == [3 | 1 << 4, 2, 1]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_mgp2_save_with_normal_medals_loads_and_a_bad_block_reads_as_nothing(model):
    good = pr_block2(1, [3 | 2 << 2 | 1 << 4])
    with booted(model, ml.with_block(v7_image(), good)) as gb:
        assert mini_best(gb, 0) == 3 | 2 << 2 | 1 << 4 and gb.mem16("mg_unlocked") == 1
    for name, blk in {"a medal byte above the three fields": pr_block2(1, [64]),
                      "a medal byte at the top": pr_block2(1, [255]),
                      "checksum": bytes(good[:-2]) + bytes([good[-2] ^ 1, good[-1]]),
                      "magic": pr_block2(1, [3], magic=b"MGPX")}.items():
        with booted(model, ml.with_block(v7_image([("ABC", 500)]), blk)) as gb:
            assert gb.mem16("mg_unlocked") == 0 and list(gb.read("mg_best", 10)) == [0] * 10, name
            assert table(gb)[0] == ("ABC", 500), name


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_bad_md_block_reads_as_no_easy_or_hard_bonus_medals_and_leaves_mgb1_alone(model):
    bx = bytearray(10)
    bx[0:4] = b"MGB1"
    bx[4], bx[5] = 1, 2
    c = (0x5A + sum(bx[:8])) & 255
    bx[8], bx[9] = c, c ^ 0xFF
    base = with_bytes(v7_image(), BX_AT, bytes(bx))
    cases = {"good": (dx_block(1, 3), True), "checksum": (dx_block(1, 3, bad_sum=True), False), "magic": (dx_block(1, 3, magic=b"MX"), False),
             "a field above the three rounds": (dx_block(64, 0), False), "blank": (bytes(6), False)}
    for name, (blk, ok) in cases.items():
        with booted(model, with_bytes(base, DX_AT, blk)) as gb:
            ml.to_list(gb)
            for _ in range(BONUS_FIRST):
                ml.tap(gb, "down")
            gb.run(4)
            assert ml.line(gb, 11).split()[-1] == "SILVER", name          # NORMAL, from MGB1
            goto_mode(gb, EASY)
            assert (ml.line(gb, 11).split()[-1] == "BRONZE") == ok, name
            goto_mode(gb, HARD)
            assert (ml.line(gb, 11).split()[-1] == "GOLD") == ok, name


# ---- every game plays the same in every mode (for now) ------------------------------------------------------------------------
SEED = 0x1D2C
MG_IDS = [int(m.group(2)) for m in re.finditer(r"#define (MG_(?:QUICKDRAW|TSHIRT|LOGROLL|ORDERUP|MARSHMALLOW|BATTERY|MILKRUN|TAIKO|MONKEY|ASTEROID|SHAKEUP|FILLLINE|TIPS|STUB))\s+(\d+)",
                                              (ROOT / "src" / "mg.h").read_text())]
assert len(MG_IDS) == GAMES, MG_IDS


def run_script(model, game_id, mode):
    """A fresh boot, the game entered in `mode` with a fixed seed, 420 frames of a fixed key script; its whole state afterwards."""
    with booted(model) as gb:
        mg_enter(gb, game_id, MG_PRACTICE | MODE_BITS[mode], seed=SEED)
        keys = ["a", "right", "a", "down", "b", "left", "a", "up", "a", "right"]
        for i in range(420):
            if i % 14 == 3:
                gb.press(keys[(i // 14) % len(keys)], 2)
            gb.run(1)
        return (bytes(gb.read(gb.addr("story_scratch"), 520)), bytes(gb.read(gb.addr("shadow_OAM"), 160)), gb.mem16("mg_score"),
                gb.mem16("mg_timer"), gb.mem("mg_phase"), gb.mem16("mg_seed"), gb.mem("mg_medal"), bytes(gb.read(0x9800, 0x400)))


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("game_id", MG_IDS)
def test_every_game_plays_the_same_in_all_three_modes(model, game_id):
    """The same seed and keys: the game's whole state (its WRAM union, the sprites, score, timer, phase, seed, the tilemap) is byte for byte
    the same after 420 frames in NORMAL, HARD and EASY."""
    ref = run_script(model, game_id, NORMAL)
    for mode in (HARD, EASY):
        assert run_script(model, game_id, mode) == ref, (game_id, mode)


# ---- the screens (goldens) ----------------------------------------------------------------------------------------------------
def shown_list(model, mode, sel):
    """The debug list on game `sel`, the medals of every mode saved on the first games, in `mode`."""
    byte = lambda n, h, e: n | h << 2 | e << 4
    ram = ml.with_block(v7_image(), ml.pr_block(0, [byte(2, 3, 1), byte(1, 0, 3), byte(3, 1, 0), 0, 0, 0, byte(0, 2, 0)]))
    gb = booted(model, ram)
    ml.to_list(gb)
    gb.write("sa_hold", 1)
    for _ in range(sel):
        ml.tap(gb, "down")
    goto_mode(gb, mode)
    gb.run(6)
    return gb


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_list_in_each_mode_with_medals_goldens(model):
    """Golden mg_list_hard (replaced: the Practice list on Milk Run in HARD, now with its own medal and the new info lines), mg_list_easy and
    mg_list_normal_medals (new): the header, the medal column and the "<MODE> BEST" line follow the mode."""
    from conftest import check_golden
    with shown_list(model, HARD, 6) as gb:
        assert header(gb) == "MINI GAMES  HARD" and ml.line(gb, 8).split()[-1] == "SILVER" and ml.line(gb, 2).split()[-1] == "GOLD"
        assert ml.line(gb, 15).strip() == "HARD BEST SILVER"
        check_golden(gb, "mg_list_hard")
    with shown_list(model, EASY, 0) as gb:
        assert header(gb) == "MINI GAMES  EASY" and ml.line(gb, 2).split()[-1] == "BRONZE" and ml.line(gb, 3).split()[-1] == "GOLD"
        check_golden(gb, "mg_list_easy")
    with shown_list(model, NORMAL, 1) as gb:
        assert header(gb) == "MINI GAMES  NORMAL" and ml.line(gb, 2).split()[-1] == "SILVER" and ml.line(gb, 3).split()[-1] == "BRONZE"
        check_golden(gb, "mg_list_normal_medals")
