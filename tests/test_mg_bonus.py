# The three old bonus rounds on BONUS > MINI GAMES (owner 2026-10-14): the can shake-up, Perfect Pour ("fill to the line") and Tip Shower
# ("tip catching"). They play in ARCADE (after each venue) and the shake-up in CLASSIC as ever (tests/test_bonus*.py, test_classic_mode.py);
# here: the list's entries and its scrolling (tests/test_mg_list.py has the first window), the unlock (played in ARCADE or CLASSIC; the
# DEBUG_MENU build unlocks everything), the medals (on the points the round earned: src/mg.h BONUS_*) kept in the save's own block "MGB1"
# (src/save.c, SRAM 0x70) without touching the Practice block "MGP2" or the tables, a round played inside the framework (result window,
# RETRY / MENU), <= 10 sprites a line.
import re

import pytest
from conftest import BX_AT, ROOT, bx_block, check_golden, hold_stage_anim, with_cards
from test_arcade import start_arcade
from test_bonus import lines
from test_classic_mode import classic_at, clear_now
from test_flow import BONUS, GS_GOAL, LEVEL_CLEAR, run_until, state
from test_mg import GS_MGLIST, GS_MINI, MG_PLAY, MG_PRACTICE, MG_RESULT, MG_STORY, MG_H, frames, mg_enter, score, text
from test_mg_list import (MG_QUICKDRAW, MEDAL_BRONZE, MEDAL_GOLD, MEDAL_NONE, MEDAL_SILVER, MG_FILLLINE, MG_SHAKEUP, MG_TIPS, PR2_LEN,
                          VIS, line, no_row_touches_the_separator, pr_block, release_built, release_rom, tap, to_list, with_block)  # noqa: F401
from test_scores import booted, set_score, v7_image
from test_sound import save_ram
from test_story import to_goal, win

pytestmark = pytest.mark.timeout(300)

KINDS = [(MG_SHAKEUP, "SHAKE"), (MG_FILLLINE, "POUR"), (MG_TIPS, "TIPS")]
AT = {k: [int(re.search(rf"#define BONUS_{k}_{m}\s+(\d+)", MG_H).group(1)) for m in ("BRONZE", "SILVER", "GOLD")] for k in ("SHAKE", "POUR", "TIPS")}
MEDAL_PTS = [0, 500, 1500, 3000]


def parse_bx(ram):
    """The bonus block, checked: (played bits, medals byte, cards seen)."""
    b = ram[BX_AT:BX_AT + 10]
    assert b[:4] == b"MGB1", b[:4]
    c = (0x5A + sum(b[:8])) & 255
    assert b[8] == c and b[9] == c ^ 0xFF, "the block's checksum"
    return b[4], b[5], int.from_bytes(b[6:8], "little")


def medal_of(byte, k):
    return (byte >> (2 * k)) & 3


# ---- the save block --------------------------------------------------------------------------------------------------------
def test_the_bonus_block_fits_between_the_practice_block_and_the_tables():
    """MGP2 ends at 0x40 + PR2_LEN + 2; the tables start at 0x80: the 10 bytes of MGB1 at 0x70 lie in the gap, overlapping neither."""
    assert 0x40 + PR2_LEN + 2 <= BX_AT and BX_AT + 10 <= 0x80
    src = (ROOT / "src" / "save.c").read_text()
    assert "#define BX_AT    0x70" in src and "#define BX_LEN   8" in src


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_recording_a_bonus_round_leaves_every_other_block_alone(model):
    """A medal for the Tip Shower writes MGB1 only: the main block, MGP2 (Quick Draw reached, a gold) and the three tables are byte for
    byte as they were."""
    img = v7_image([("ABC", 500)], story=3, step=1, story_tbl=[("STO", 900)], classic=[("CLA", 700)])
    with booted(model, img) as gb:                      # (the game itself writes the MGP2 block here: Quick Draw reached in the story)
        mg_enter(gb, MG_QUICKDRAW, MG_STORY)
        gb.write(gb.addr("story_scratch") + 2, 3)
        gb.write("mg_phase", MG_RESULT)
        run_until(gb, lambda: gb.mem("overlay_on") == 1, 10)
        mid = save_ram(gb)
    assert mid[0x40:0x44] == b"MGP2"
    with booted(model, mid) as gb:
        mg_enter(gb, MG_TIPS, MG_PRACTICE)
        end_round(gb, 1800)
        out = save_ram(gb)
    assert parse_bx(out) == (1 << 2, MEDAL_SILVER << 4, 0xFFFF)
    assert out[:BX_AT] == mid[:BX_AT] and out[BX_AT + 10:] == mid[BX_AT + 10:], "nothing but the ten bytes of MGB1 changed"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_bad_bonus_block_reads_as_nothing_and_the_rest_survives(model, release_built):
    """Release build, MGP2 with Quick Draw reached: MGB1 with a wrong checksum, a bit above the three rounds, a medal byte above its six bits
    or the wrong magic lists the bonus rounds as locked with no medal; the Practice list is as it was."""
    good = bx_block(0b111, MEDAL_GOLD | MEDAL_GOLD << 2 | MEDAL_GOLD << 4)
    bad = {"checksum": good[:8] + bytes([good[8] ^ 1, good[9]]),
           "a fourth round": bx_block(0b1111, 0),
           "a medal byte over six bits": bx_block(0b1, 0x40),
           "magic": b"MGB2" + good[4:]}
    base = with_block(v7_image(), pr_block(1, [MEDAL_SILVER]))
    ram = bytearray(base)
    ram[BX_AT:BX_AT + 10] = good
    with release_rom(model, bytes(ram)) as gb:
        to_list(gb)
        for _ in range(12):
            tap(gb, "down")
        assert line(gb, 9).split() == ["CAN", "SHAKE-UP", "GOLD"] and line(gb, 10).split() == ["PERFECT", "POUR", "GOLD"] and line(gb, 11).split() == ["TIP", "SHOWER", "GOLD"]
    for name, blk in bad.items():
        ram = bytearray(base)
        ram[BX_AT:BX_AT + 10] = blk
        with release_rom(model, bytes(ram)) as gb:
            to_list(gb)
            assert line(gb, 2) == " QUICK DRAW   SILVER", name
            for _ in range(12):
                tap(gb, "down")
            assert [line(gb, r).strip() for r in range(9, 12)] == ["? ? ?"] * 3, name


# ---- the unlock rule -------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_release_list_locks_the_bonus_rounds_until_played(model, release_built):
    """`make release` on a fresh cartridge: scrolled to the bonus rounds each is "? ? ?", the details say LOCKED / PLAY IT IN ARCADE / OR
    CLASSIC and A does nothing. With the shake-up and Tip Shower played (MGB1) and the shake-up at SILVER they list by name and play;
    Perfect Pour stays locked."""
    with release_rom(model, with_cards()) as gb:
        to_list(gb)
        assert gb.mem("ml_n") == 13
        for _ in range(10):
            tap(gb, "down")
        gb.run(4)
        assert gb.mem("ml_sel") == 10 and [line(gb, r).strip() for r in range(2, 12)] == ["? ? ?"] * 10
        assert [line(gb, r).strip() for r in range(14, 17)] == ["LOCKED", "PLAY IT IN ARCADE", "OR CLASSIC"]
        no_row_touches_the_separator(gb, VIS)
        tap(gb, "a")
        gb.run(5)
        assert state(gb) == GS_MGLIST, "a locked round does not play"
    ram = bytearray(with_cards(v7_image()))
    ram[BX_AT:BX_AT + 10] = bx_block(0b101, MEDAL_SILVER | MEDAL_BRONZE << 4)
    with release_rom(model, bytes(ram)) as gb:
        to_list(gb)
        for _ in range(12):
            tap(gb, "down")
        gb.run(4)
        assert gb.mem("ml_sel") == 12
        rows = [line(gb, r) for r in range(9, 12)]
        assert rows[0].split() == ["CAN", "SHAKE-UP", "SILVER"], rows
        assert rows[1].strip() == "? ? ?" and rows[2].split() == ["TIP", "SHOWER", "BRONZE"], rows
        assert [line(gb, r).strip() for r in (14, 15, 16)] == ["A BONUS ROUND", "BEST BRONZE", "NORMAL ONLY  B BACK"]
        check_golden(gb, "mg_list_bonus_release")
        tap(gb, "up")
        gb.run(4)
        assert [line(gb, r).strip() for r in range(14, 17)] == ["LOCKED", "PLAY IT IN ARCADE", "OR CLASSIC"]
        tap(gb, "a")
        gb.run(5)
        assert state(gb) == GS_MGLIST
        tap(gb, "up")
        tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_MINI and gb.pb.memory[0xFF40] & 0x80, 30)
        assert gb.mem("mg_id") == MG_SHAKEUP and gb.mem("mg_mode") == MG_PRACTICE


def reach_arcade_bonus(gb, rounds_before):
    """ARCADE: the saloon's two levels won, Quick Draw reached (its result poked, A to go on) and the venue's bonus round starts."""
    gb.write("bonus_round", rounds_before)
    for k in range(2):
        to_goal(gb)
        win(gb, 0, k)
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 20)
        run_until(gb, lambda: state(gb) in (GS_GOAL, GS_MINI), 400)
    run_until(gb, lambda: gb.pb.memory[0xFF40] & 0x80, 10)
    assert state(gb) == GS_MINI and gb.mem("mg_mode") == MG_STORY
    gb.write("mg_phase", MG_RESULT)
    run_until(gb, lambda: gb.mem("overlay_on") == 1, 10)
    gb.run(70)
    gb.write("story_step", 4)                      # (the venue's last step: the result's A ends the venue, ARCADE's bonus round follows)
    gb.press("a", 2)
    run_until(gb, lambda: state(gb) == BONUS, 300)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("before,kind", [(0, 0), (1, 1), (2, 2)])
def test_arcade_playing_a_bonus_round_unlocks_it(model, before, kind):
    """ARCADE's venue-end rotation (shake-up, Perfect Pour, Tip Shower): starting a round marks it played in MGB1 and only that one; the
    round itself is the one it always was (bonus_kind, the old state, no framework)."""
    with start_arcade(model, with_cards()) as gb:
        assert gb.mem("save_lock") == 1
        reach_arcade_bonus(gb, before)
        assert gb.mem("bonus_kind") == kind and state(gb) == BONUS and gb.mem("mg_phase") != MG_PLAY
        out = save_ram(gb)
    assert parse_bx(out) == (1 << kind, 0, 0xFFFF)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_classic_playing_the_shake_up_unlocks_it(model):
    """CLASSIC plays the shake-up after level 2: the block says it was played (and only it)."""
    with booted(model, with_cards()) as gb:
        classic_at(gb, 1)
        gb.write("level", 2)
        assert clear_now(gb) and gb.mem("bonus_kind") == 0
        out = save_ram(gb)
    assert parse_bx(out) == (1, 0, 0xFFFF)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_debug_select_run_records_no_bonus_round(model):
    """save_lock SAVE_LOCK_DEBUG (the START + SELECT select): nothing is written for a bonus round, as for the Practice block."""
    with booted(model, with_cards()) as gb:
        gb.write("save_lock", 2)
        mg_enter(gb, MG_FILLLINE, MG_PRACTICE)
        end_round(gb, 9000)
        out = save_ram(gb)
    assert parse_bx(out) == (0, 0, 0xFFFF)


# ---- playing them from the list ---------------------------------------------------------------------------------------------
def end_round(gb, points):
    """From the banner: A skips it, the round runs, `points` are what it earned, its own end phase is poked (the result window follows)."""
    gb.run(3)                                          # (the heavy first frame of a screen is over)
    gb.press("a", 2)
    run_until(gb, lambda: gb.mem("mg_phase") == MG_PLAY, 5)
    set_score(gb, points)
    gb.write("bonus_phase", 4)
    gb.write("bonus_timer", 200)
    run_until(gb, lambda: gb.mem("overlay_on") == 1, 10)
    frames(gb, 3)


def medal_for(kind, points):
    at = AT[kind]
    return sum(points >= a for a in at)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("gid,kind", KINDS)
def test_a_bonus_round_plays_in_the_framework_and_earns_its_medal(model, gid, kind):
    """The round starts in practice with the banner (name, instruction; the old rounds have no count-in), A skips it; each medal threshold
    (BONUS_* in src/mg.h) gives its medal and the result window's words; the points of the medal go on the score; a worse round never
    lowers the best; A retries (the banner again, score from 0), B comes back to the list, which shows the best medal."""
    names = {MG_SHAKEUP: ("CAN SHAKE UP", "PICK THE CALM CAN"), MG_FILLLINE: ("PERFECT POUR", "FILL TO THE LINE"), MG_TIPS: ("TIP SHOWER", "CATCH THE TIPS")}
    at = AT[kind]
    with booted(model) as gb:
        hold_stage_anim(gb)
        mg_enter(gb, gid, MG_PRACTICE)
        assert gb.mem("mg_phase") == 0 and gb.mem("bonus_kind") == gid - MG_SHAKEUP
        assert (text(gb, 2), text(gb, 3)) == names[gid]
        frames(gb, 2)
        points = [at[0] - 1, at[0], at[1], at[2]] if kind != "SHAKE" else [0, at[2]]
        best = 0
        for p in points:
            want = medal_for(kind, p)
            end_round(gb, p)
            assert gb.mem("mg_medal") == want, (kind, p)
            words = ["NO MEDAL", "BRONZE", "SILVER", "GOLD"][want]
            assert text(gb, 3, True, x0=4).split()[0] == words.split()[0], (kind, p)
            assert text(gb, 1, True, x0=4) == names[gid][0]
            assert text(gb, 4, True, x0=4) == "A RETRY B MENU"
            assert score(gb) == p + MEDAL_PTS[want]
            best = max(best, want)
            assert max(lines(gb)) <= 10
            gb.press("a", 2)                                   # RETRY: the short card, the score from 0
            run_until(gb, lambda: gb.mem("mg_phase") == 0 and gb.pb.memory[0xFF40] & 0x80, 30)
            assert state(gb) == GS_MINI and score(gb) == 0 and gb.mem("overlay_on") == 0
        end_round(gb, 0)
        gb.press("b", 2)
        run_until(gb, lambda: state(gb) == GS_MGLIST and gb.pb.memory[0xFF40] & 0x80, 30)
        gb.run(3)
        for _ in range(gid - MG_SHAKEUP + 10):
            tap(gb, "down")
        gb.run(4)
        sel = 10 + gid - MG_SHAKEUP
        row = 2 + sel - max(0, sel - VIS + 1)
        assert gb.mem("ml_sel") == sel and line(gb, row).split()[-1] == ["NO", "BRONZE", "SILVER", "GOLD"][best] or best == 0
        if best:
            assert line(gb, 15).strip() == "BEST " + ["", "BRONZE", "SILVER", "GOLD"][best]
        out = save_ram(gb)
    played, medals, _ = parse_bx(out)
    assert played == 1 << (gid - MG_SHAKEUP) and medal_of(medals, gid - MG_SHAKEUP) == best
    assert all(medal_of(medals, k) == 0 for k in range(3) if k != gid - MG_SHAKEUP)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_shake_up_played_for_real_wins_gold(model):
    """The whole shake-up inside the framework: the banner, the cans shaken and swapped, the calm one picked (+3000): GOLD."""
    with booted(model) as gb:
        mg_enter(gb, MG_SHAKEUP, MG_PRACTICE)
        gb.press("a", 2)
        run_until(gb, lambda: gb.mem("bonus_phase") == 3, 1500)               # PH_CHOOSE
        gb.write("bonus_cursor", gb.mem("bonus_calm"))
        gb.run(2)
        gb.press("a", 2)
        assert gb.mem("bonus_won") == 1
        run_until(gb, lambda: gb.mem("overlay_on") == 1, 200)
        gb.run(3)
        assert gb.mem("mg_medal") == MEDAL_GOLD and gb.mem16("mg_score") == 3000
        assert text(gb, 2, True, x0=4) == "SCORE 3000"
