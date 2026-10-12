# Modes P5: CLASSIC on the title (PLAY > CLASSIC): the 1983 game's 26 levels (both waves) on our venues, from the owner's
# level guide (docs: PLAN.md "Three modes P5 as built"; src/classic.c). The bar mirroring itself is tests/test_classic.py.
#
# CLASSIC games start either through the menu or through the title's test hook title_go with bit 7 set (0x80 | level:
# CLASSIC from that level, on the frame PLAY's A would have started it).
import re

import pytest
from conftest import GAME, K_CLASSIC, K_PLAY, ROM, ROOT, check_golden, hold_stage_anim, title_pick
from gbtools import Rom
from test_flow import BONUS, GAME_OVER, LEVEL_CLEAR, PLAYING, lose_a_life, run_until, score, state
from test_patrons import MAX_P, clear_patrons, freeze, inject_mug, set_patron
from test_scores import (EMPTY, MODE_ARCADE, MODE_CLASSIC, MODE_STORY, TBL_AT, TBL_SUM, ROW_HEAD, booted, screen_text,
                         set_score, table, tap, v7_image)
from test_sound import save_ram

pytestmark = pytest.mark.timeout(240)

GS_INITIALS, GS_SCORES = 9, 10
ENTRY_X = GAME["ENTRY_X"]

# ---- the owner's level guide (uploads: tapper-levels.md), written out here as the guide gives it ------------------------
SALOON, SPORTS, PUNK, SPACE = range(4)
GUIDE = [   # (setting, directions top -> bottom, patrons per bar top -> bottom)
    (SALOON, "LLLL", "1111"), (SALOON, "LLLL", "2222"),
    (SPORTS, "RRRR", "2333"), (SPORTS, "RRRR", "2334"), (SPORTS, "RRRR", "3344"),
    (PUNK, "RRLL", "2334"), (PUNK, "LLRR", "3344"), (PUNK, "RRLL", "3444"), (PUNK, "LLRR", "4444"),
    (SPACE, "RLLR", "4444"), (SPACE, "LRRL", "4444"), (SPACE, "RLRL", "4444"), (SPACE, "LRLR", "4444"),
    # wave 2
    (SALOON, "RLRL", "4444"), (SALOON, "LRLR", "4444"),
    (SPORTS, "RRRR", "4444"), (SPORTS, "RRRR", "4444"), (SPORTS, "RRRR", "4444"),
    (PUNK, "RRLL", "4444"), (PUNK, "LLRR", "4444"), (PUNK, "RRLL", "4444"), (PUNK, "LLRR", "4444"),
    (SPACE, "RRRR", "4444"), (SPACE, "RRRR", "4444"), (SPACE, "RRRR", "4444"), (SPACE, "RRRR", "4444"),
]
GUIDE_BONUS = {2, 5, 9, 13, 15, 18, 22, 26}          # then every 13 levels
VENUE = {SALOON: 0, SPORTS: 1, PUNK: 6, SPACE: 9}      # our venues: saloon, stadium, The Chrome Cow, space lounge
SERVE = {SALOON: 50, SPORTS: 75, PUNK: 100, SPACE: 150}


def dirs_mask(s):
    return sum(1 << b for b, c in enumerate(s) if c == "R")


# ---- the table as built: read out of the ROM file (build/game.gb, or GB_ROM) at the symbols' banked addresses ----------------------
NOI = {m.group(1): int(m.group(2), 16)
       for m in re.finditer(r"DEF (\w+) 0x([0-9A-F]+)", ROM.with_suffix(".noi").read_text())}
ROM_BYTES = ROM.read_bytes()
ROW_SIZE = 10                                          # classic_row_t: set dirs caps quota spawn(16) step push gap taper


def rom_data(sym, n):
    v = NOI[sym]
    bank, a = v >> 16, v & 0xFFFF
    off = a if a < 0x4000 else bank * 0x4000 + a - 0x4000
    return ROM_BYTES[off:off + n]


def built_rows():
    raw = rom_data("_classic_table", 26 * ROW_SIZE)
    rows = []
    for i in range(26):
        r = raw[i * ROW_SIZE:(i + 1) * ROW_SIZE]
        rows.append(dict(set=r[0], dirs=r[1], caps=[((r[2] >> (2 * b)) & 3) + 1 for b in range(4)], quota=r[3],
                         spawn=r[4] | r[5] << 8, step=r[6], push=r[7], gap=r[8], taper=r[9]))
    return rows


def row_of(lv):
    while lv > 26:
        lv -= 13
    return lv


def test_the_table_matches_the_guide():
    rows = built_rows()
    for lv, (row, (st, d, caps)) in enumerate(zip(rows, GUIDE), 1):
        assert row["set"] == st, (lv, "setting")
        assert row["dirs"] == dirs_mask(d), (lv, "directions", d)
        assert row["caps"] == [int(c) for c in caps], (lv, "patrons per bar", caps)
    venues = list(rom_data("_classic_venue", 4))
    scores = list(rom_data("_classic_score", 4))
    assert venues == [VENUE[s] for s in range(4)] and scores == [SERVE[s] for s in range(4)]
    assert set(rom_data("_classic_bonus_lv", 8)) == GUIDE_BONUS
    # our numbers: harder through each wave, wave 2 harder than wave 1's end
    for a, b in zip(rows, rows[1:]):
        assert b["spawn"] <= a["spawn"] and b["step"] <= a["step"] + 2
    assert rows[13]["spawn"] <= rows[12]["spawn"] and rows[13]["step"] < rows[12]["step"]


# ---- starting a game -------------------------------------------------------------------------------------------------------
def classic_at(gb, lv):
    """The title's hook: CLASSIC from level lv, run to PLAYING."""
    title_pick(gb, K_PLAY, K_CLASSIC, press=False)
    gb.write("title_go", 0x80 | lv)
    gb.press("a", 2)
    gb.run(1)
    run_until(gb, lambda: state(gb) == PLAYING, 60)
    return gb


def caps(gb):
    return list(gb.read("bar_cap", 4))


def bar_counts(gb):
    st, br = gb.read("patron_state", MAX_P), gb.read("patron_bar", MAX_P)
    n = [0] * 4
    for i in range(MAX_P):
        if st[i]:
            n[br[i]] += 1
    return n


def test_play_classic_starts_level_1_of_the_table(boot):
    """PLAY > CLASSIC: level 1 (the saloon, every bar L, one patron a bar at most), extra lives at 20,000, one patron on
    every bar to begin with, the venue's tune, no LOOP banner. Golden classic_start."""
    title_pick(boot, K_PLAY, K_CLASSIC)
    run_until(boot, lambda: state(boot) == PLAYING, 30)
    assert boot.mem("play_mode") == 2 and boot.mem("story_on") == 0 and boot.mem("level") == 1
    assert boot.mem("cur_group") == 0 and boot.mem("bar_dirs") == 0 and caps(boot) == [1, 1, 1, 1]
    assert int.from_bytes(boot.read("extra_at", 4), "little") == 20000 and boot.mem("lives") == 3
    assert boot.mem("serve_score") == 50 and boot.mem("quota") == 10 and boot.mem("tip_first") == 2
    assert bar_counts(boot) == [1, 1, 1, 1]
    boot.run(60)
    check_golden(boot, "classic_start")


@pytest.mark.parametrize("lv", [1, 2, 3, 5, 6, 9, 10, 12, 13, 14, 19, 23, 26])
def test_each_level_loads_its_row(boot, lv):
    row = built_rows()[lv - 1]
    classic_at(boot, lv)
    st = GUIDE[lv - 1][0]
    assert boot.mem("level") == lv and boot.mem("cur_group") == VENUE[st]
    assert boot.mem("bar_dirs") == dirs_mask(GUIDE[lv - 1][1]) and caps(boot) == row["caps"]
    assert boot.mem("serve_score") == SERVE[st] and boot.mem("quota") == row["quota"]
    assert int.from_bytes(boot.read("spawn_interval", 2), "little") == row["spawn"]
    assert boot.mem("pushback_px") == 8 * row["push"] and boot.mem("empty_gap") == row["gap"]
    assert state(boot) == PLAYING, "no LOOP banner in CLASSIC (wave 2's saloon included)"


def speeds(gb):
    return int.from_bytes(gb.read("spawn_interval", 2), "little"), gb.mem("patron_speed"), gb.mem("empty_gap")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_wave_2_repeats_from_level_27_a_little_harder_each_time(model):
    got = {}
    for lv in (14, 27, 40, 53, 66, 79):
        with Rom(ROM, model) as gb:
            gb.run(120)
            classic_at(gb, lv)
            got[lv] = (gb.mem("cur_group"), gb.mem("bar_dirs"), caps(gb), gb.mem("quota"), gb.mem("serve_score"))
            got[lv] += speeds(gb)
    assert all(got[lv][:5] == got[14][:5] for lv in got), "level 27, 40, ... = row 14: the saloon, R L R L"
    sp = [got[lv][5] for lv in (14, 27, 40, 53, 66)]
    wk = [got[lv][6] for lv in (14, 27, 40, 53, 66)]
    assert sp[0] > sp[1] > sp[2] > sp[3] == sp[4], ("spawn -8 % a repeat, three at most", sp)
    assert wk[0] < wk[1] < wk[2] < wk[3] == wk[4], ("walk +10 % a repeat, three at most", wk)
    assert got[79][5:] == got[66][5:]


# ---- crowd caps -------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("lv", [1, 4, 6])
def test_a_bar_never_holds_more_than_its_cap(boot, lv):
    """Patrons come as fast as the spawn point lets them (spawn interval 1, a large quota, a slow walk): every bar fills
    to its cap and never past it."""
    classic_at(boot, lv)
    want = caps(boot)
    boot.write("intro_timer", 0)
    most = [0] * 4
    for i in range(1500):
        boot.write("spawn_interval", 1)
        boot.write(boot.addr("spawn_interval") + 1, 0)
        boot.write("quota", 200)
        boot.write("lives", 3)
        if state(boot) == PLAYING:
            boot.write("patron_speed", 40)
            boot.write("hurry_speed", 40)
        boot.run(1)
        n = bar_counts(boot)
        assert all(a <= c for a, c in zip(n, want)), (i, n, want)
        most = [max(a, b) for a, b in zip(most, n)]
    assert most == want, ("every bar reached its cap", most, want)


# ---- scoring -------------------------------------------------------------------------------------------------------------
def serve_one(gb, b=1):
    """A patron near the left end of bar b catches a full mug and is served: the score it gives."""
    clear_patrons(gb)
    freeze(gb)
    set_patron(gb, b, ENTRY_X + 2)
    s0 = score(gb)
    inject_mug(gb, b, ENTRY_X + 6)
    run_until(gb, lambda: score(gb) > s0, 120)
    return score(gb) - s0


@pytest.mark.parametrize("lv,pts", [(1, 50), (3, 75), (6, 100), (10, 150), (14, 50), (26, 150)])
def test_a_serve_scores_its_setting(boot, lv, pts):
    classic_at(boot, lv)
    assert serve_one(boot) == pts


def test_an_extra_life_at_20000_then_every_40000(boot):
    classic_at(boot, 1)
    set_score(boot, 19960)
    assert serve_one(boot) == 50 and boot.mem("lives") == 4
    assert int.from_bytes(boot.read("extra_at", 4), "little") == 60000
    set_score(boot, 59960)
    serve_one(boot)
    assert boot.mem("lives") == 4, "at most 4"
    assert int.from_bytes(boot.read("extra_at", 4), "little") == 100000


# ---- bonus rounds: after the last level of each setting, always the shake-up, faster each time ---------------------------
def clear_now(gb):
    gb.write("level_clear", 1)
    run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 30)
    run_until(gb, lambda: state(gb) in (BONUS, PLAYING), 400)
    return state(gb) == BONUS


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_bonus_round_follows_the_listed_levels_only(model):
    with Rom(ROM, model) as gb:
        gb.run(120)
        classic_at(gb, 1)
        seen = []
        for lv in range(1, 43):
            gb.write("level", lv)
            if clear_now(gb):
                seen.append(lv)
                assert gb.mem("bonus_kind") == 0, "always the can shake-up"
                gb.write("bonus_phase", 4)
                gb.write("bonus_timer", 200)
                run_until(gb, lambda: state(gb) == PLAYING, 200)
            assert gb.mem("level") == lv + 1
    assert seen == [2, 5, 9, 13, 15, 18, 22, 26, 28, 31, 35, 39, 41], seen


def test_the_shake_up_gets_faster_every_round_and_pays_3000(boot):
    classic_at(boot, 2)
    durs, swaps = [], []
    for n in range(1, 10):
        boot.write("level", 2)
        assert clear_now(boot)
        assert boot.mem("bonus_round") == n and boot.mem("bonus_kind") == 0
        durs.append(boot.mem("bonus_swap_dur"))
        swaps.append(boot.mem("bonus_swaps_total"))
        if n == 1:
            boot.run(20)
            check_golden(boot, "classic_bonus")
        boot.write("bonus_phase", 4)
        boot.write("bonus_timer", 200)
        run_until(boot, lambda: state(boot) == PLAYING, 200)
    assert all(a > b for a, b in zip(durs, durs[1:])), ("each round's swaps are quicker", durs)
    assert all(a < b for a, b in zip(swaps, swaps[1:])), ("and one more of them", swaps)
    src = (ROOT / "src" / "bonus.c").read_text()
    assert "#define BONUS_SCORE    3000" in src, "the payout never grows"


# ---- tips: the level's first tip lies where the patron who sends the 2nd empty stands ----------------------------------------
def test_the_first_tip_comes_with_the_second_empty(boot):
    classic_at(boot, 1)
    boot.write("tip_chance", 255)                      # (later tips: always; none may come before the first)
    clear_patrons(boot)
    freeze(boot)
    a = set_patron(boot, 0, 64)                         # (pushed back 32 px: neither reaches the left end)
    b = set_patron(boot, 0, 100)
    inject_mug(boot, 0, 104)
    boot.run(30)
    inject_mug(boot, 0, 68)
    empties, tip_at = 0, None
    for i in range(900):
        before = boot.mem("tip_first")
        boot.run(1)
        if boot.mem("tip_first") < before:
            empties += 1
            if empties == 1:
                assert boot.mem("tip_timer") == 0, "no tip at the first empty"
        if boot.mem("tip_timer") and tip_at is None:
            tip_at = (boot.mem("tip_bar"), boot.mem("tip_x"))
            xs = boot.read("patron_x", MAX_P)
            st = boot.read("patron_state", MAX_P)
            break
    assert empties == 2 and tip_at is not None
    # the sender: the one who has just walked on (his x is where the empty left him; frozen walkers stand still)
    sender = [p for p in (a, b) if st[p] == 1]
    assert tip_at[0] == 0 and any(tip_at[1] == xs[p] + 4 for p in sender), (tip_at, [xs[p] for p in (a, b)])
    assert boot.mem("tip_first") == 0


def test_no_random_tip_before_the_first(boot):
    classic_at(boot, 1)
    boot.write("tip_chance", 255)
    for _ in range(3):
        assert serve_one(boot, 2) == 50
        boot.run(30)
        assert boot.mem("tip_timer") == 0, "served patrons leave no tip before the level's first"


# ---- the in-level ramp ----------------------------------------------------------------------------------------------------
def test_the_ramp_speeds_the_level_up_three_times_and_a_life_resets_it(boot):
    classic_at(boot, 1)
    boot.write("intro_timer", 0)
    boot.run(2)
    sp0, wk0 = int.from_bytes(boot.read("spawn_interval", 2), "little"), boot.mem("patron_speed")
    seen = []
    for _ in range(3):
        assert 0 < int.from_bytes(boot.read("ramp_t", 2), "little") <= 600
        clear_patrons(boot)
        boot.write(boot.addr("ramp_t"), 2)
        boot.write(boot.addr("ramp_t") + 1, 0)
        boot.run(3)
        seen.append((boot.mem("ramp_k"), int.from_bytes(boot.read("spawn_interval", 2), "little"),
                     boot.mem("patron_speed")))
    assert [s[0] for s in seen] == [1, 2, 3]
    assert seen[2][1] == sp0 - sp0 * 18 // 100 and seen[2][2] == wk0 + wk0 * 15 // 100, (sp0, wk0, seen)
    assert int.from_bytes(boot.read("ramp_t", 2), "little") == 0, "three steps at most: the ramp stops"
    lose_a_life(boot)
    run_until(boot, lambda: state(boot) == PLAYING, 200)
    assert boot.mem("ramp_k") == 0 and int.from_bytes(boot.read("ramp_t", 2), "little") == 600
    assert int.from_bytes(boot.read("spawn_interval", 2), "little") == sp0 and boot.mem("patron_speed") == wk0


# ---- the screen in play: level 3 flips the whole screen -------------------------------------------------------------------
def test_golden_classic_level3(boot):
    classic_at(boot, 3)
    boot.write("tip_chance", 0)
    boot.write("intro_timer", 0)
    boot.run(240)
    assert boot.mem("bar_dirs") == 0xF and state(boot) == PLAYING
    check_golden(boot, "classic_level3")


# ---- the sprite budget on the busiest layout ------------------------------------------------------------------------------
def test_level_12_never_shows_more_than_10_sprites_a_line(boot):
    """The real CLASSIC level 12 (R L R L, every cap 4) kept crowded for 3000 frames with perf_helpers.ClassicPeak's
    second bartender (new patrons made due at once, walkers near the tap put back, lives topped up), the bartender on
    the play script: never more than 10 objects on a line, 40 in all, and never more patrons on a bar than its cap."""
    from perf_helpers import SCRIPT, ClassicPeak
    from test_perf import oam_line_counts
    classic_at(boot, 12)
    assert boot.mem("bar_dirs") == 0x5 and caps(boot) == [4, 4, 4, 4]
    boot.write("intro_timer", 0)
    boot.write("tip_chance", 0)
    rp = ClassicPeak(boot, 16)
    rp.seed()
    boot.run(2)
    held, worst, most, counts = None, 0, 0, []
    for i in range(3000):
        want = SCRIPT[i % len(SCRIPT)]
        if want != held:
            if held:
                boot.release(held)
            if want:
                boot.hold(want)
            held = want
        rp.tick()
        boot.run(1)
        line, n = oam_line_counts(boot)
        assert line <= 10 and n <= 40, (i, line, n)
        c = bar_counts(boot)
        assert max(c) <= 4, (i, c)
        counts.append(sum(c))
    if held:
        boot.release(held)
    assert boot.mem("level") == 12 and max(counts) >= 12 and sum(counts) / len(counts) >= 9, (max(counts), sum(counts) / len(counts))


# ---- game over: the CLASSIC top 5 ---------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_game_over_goes_to_the_classic_table(model):
    with booted(model, v7_image([("ARC", 900)])) as gb:
        hold_stage_anim(gb)
        classic_at(gb, 1)
        set_score(gb, 12345)
        for n in range(3):
            lose_a_life(gb)
            if n < 2:
                run_until(gb, lambda: state(gb) == PLAYING, 200)
        run_until(gb, lambda: state(gb) == GAME_OVER, 200)
        tap(gb, "start")
        run_until(gb, lambda: state(gb) == GS_INITIALS, 30)
        gb.run(2)
        tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_SCORES, 30)
        gb.run(2)
        assert table(gb, MODE_CLASSIC)[0] == ("AAA", 12345) and table(gb, MODE_ARCADE)[0] == ("ARC", 900)
        assert screen_text(gb, ROW_HEAD).strip() == "CLASSIC HIGH SCORES"
        check_golden(gb, "scores_classic")
        saved = save_ram(gb)
    b = saved[TBL_AT[MODE_CLASSIC]:TBL_AT[MODE_CLASSIC] + 4]
    assert b == b"HSC2"
    with booted(model, saved) as again:
        assert table(again, MODE_CLASSIC)[0] == ("AAA", 12345)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_stand_in_s_classic_block_loads_empty(model):
    """P5: CLASSIC's block magic is "HSC2"; a version-1 block ("HSC1", the old stand-in's scores) loads as an empty table
    and the other tables stay."""
    img = bytearray(v7_image([("ARC", 900)], story_tbl=[("STO", 800)], classic=[("OLD", 700)]))
    a = TBL_AT[MODE_CLASSIC]
    assert img[a:a + 4] == b"HSC2"
    with booted(model, bytes(img)) as gb:
        assert table(gb, MODE_CLASSIC)[0] == ("OLD", 700), "an HSC2 block loads"
    old = bytearray(img[a:a + TBL_SUM + 2])
    old[:4] = b"HSC1"
    c = (0x5A + sum(old[:TBL_SUM])) & 255
    old[TBL_SUM], old[TBL_SUM + 1] = c, c ^ 0xFF
    img[a:a + len(old)] = old
    with booted(model, bytes(img)) as gb:
        assert table(gb, MODE_CLASSIC) == EMPTY
        assert table(gb, MODE_ARCADE)[0] == ("ARC", 900) and table(gb, MODE_STORY)[0] == ("STO", 800)


# ---- the debug select's CLASSIC box ------------------------------------------------------------------------------------
def test_the_classic_box_starts_any_classic_level(boot):
    from test_debug import banner_is, combo, release_combo
    title_pick(boot, K_PLAY, K_CLASSIC, press=False)
    combo(boot)
    release_combo(boot)
    boot.run(3)
    assert boot.mem("debug_menu_open") == 1 and boot.mem("debug_classic") == 1 and banner_is(boot, "CLASSIC 01")
    tap(boot, "left")
    assert boot.mem("debug_level") == 26 and banner_is(boot, "CLASSIC 26"), "1..26, wrapping"
    for _ in range(3):
        tap(boot, "right")
    assert banner_is(boot, "CLASSIC 03")
    tap(boot, "a")
    run_until(boot, lambda: state(boot) == PLAYING, 60)
    assert boot.mem("play_mode") == 2 and boot.mem("level") == 3 and boot.mem("bar_dirs") == 0xF
    assert boot.mem("cur_group") == 1 and boot.mem("lives") == 3 and score(boot) == 0
    combo(boot)                                          # in CLASSIC play: the box opens on its level
    release_combo(boot)
    boot.run(3)
    assert boot.mem("debug_classic") == 1 and banner_is(boot, "CLASSIC 03")
