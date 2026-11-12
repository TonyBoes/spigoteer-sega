# The title's BONUS > BOSS RUSH (src/rush.c; owner 2026-10-12) and its part of Practice's SRAM block at 0x40 ("MGP2",
# src/save.c): the BONUS submenu's third item, the rush's menu (ALL / CHOOSE), the list of the built bosses (the
# DEBUG_MENU build all unlocked, `make release` locked until beaten in STORY or ARCADE), CHOOSE's one fight and its
# result (A retry, B back), ALL's fights back to back (lives carried, +1 a won fight up to 3, the score totalled, a NEXT
# card between them) and its end (after the last boss, or out of lives), the bests saved; a rush writes nothing to the
# story progress, the tunes or the high-score tables; "MGP1" migrates with its mini-games, a bad block loses only itself.
import re

import pytest
from conftest import (clear_regulars, K_BONUS, K_BOSSRUSH, K_CREDITS, K_MINIGAMES, K_SOUNDTRACK, MENU_SETTLE, ROOT, TM_BONUS, TM_TOP,
                      check_golden, hold_stage_anim, menu_items, title_pick)
from test_flow import GS_GOAL, GS_STORY, LEVEL_CLEAR, LIFE_LOST, PLAYING, TITLE, run_until, state, tilemap_row
from test_mg import GLYPH_CH
from ol_helpers import BLANK, band_rows_ok, header, header_text, hint, selection, text
from test_mg_list import (MEDAL_GOLD, MEDAL_SILVER, MG_PLANNED, MG_QUICKDRAW, PR_AT, QUEST, pr_block,
                          release_rom, with_block)
from test_scores import booted, table, v7_image
from test_sound import save_ram
from test_story import BOSS_BUILT, SHIFT_STEP, boss_from_opening, to_chapter, to_goal, win
from test_flow import lose_a_life
from boss_common import frames, until

pytestmark = pytest.mark.timeout(600)

SP_RUSH = 7
MODE_RUSH = 4
RUSH_AT = 387
RS_MENU, RS_LIST, RS_NEXT, RS_RESULT, RS_FIGHT = range(5)
RM_ALL, RM_CHOOSE = range(2)
# struct rush_state (src/rush.h)
SCR, MODE, SEL, LIST_SEL, BOSS, WON, N, RESULT, BEST, T, FIGHT_T, TOTAL_T, DIRTY, SAVE = \
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 14, 16
BOSS_COUNT = 10
RUSH_SAVE_N = 28
PR1_LEN = 6 + MG_PLANNED
PR_LEN = PR1_LEN + RUSH_SAVE_N
RSV_BITS, RSV_BEST = 0, 2
RSV_ALL_SCORE = RSV_BEST + 2 * BOSS_COUNT
RSV_ALL_TIME, RSV_ALL_N = RSV_ALL_SCORE + 3, RSV_ALL_SCORE + 5
NAMES = ["BIG TEX", "THE MASCOT", "SASQUATCH", "THE CRITIC", "THE YETI", "PROTOTYPE", "DUKE", "SUMO CHAMP",
         "LEO THE LION", "MOTHERSHIP"]
VENUES = ["THE SALOON", "THE STADIUM", "THE LUMBER LODGE", "THE BISTRO", "THE IGLOO", "THE ROBOT FACTORY",
          "THE CHROME COW", "THE TEAHOUSE", "THE JUNGLE ZOO", "THE SPACE LOUNGE"]
BUILT = sorted(BOSS_BUILT)                     # the built bosses in chapter order (gen_story BUILT_SLOTS["BOSS"])
STORY_H = (ROOT / "build" / "story.h").read_text()
COLON = QUEST + 3                              # ST_GLYPH_COLON = STORY_FONT_BASE + 6 (QUEST is + 3)
assert "#define ST_GLYPH_COLON (STORY_FONT_BASE + 6)" in STORY_H
LEVEL_BONUS = int(re.search(r"#define LEVEL_BONUS\s+(\d+)", (ROOT / "src" / "main_cold.c").read_text()).group(1))
SPOUT_X = 136


def line(gb, row):
    """A row of a rush screen as text (ol_helpers: '?', '-' and ':' from the story font, '@' and '$' the A and B buttons)."""
    return text(gb, row)


def lines(gb, rows):
    return [line(gb, r).strip() for r in rows]




def R(gb, off, n=1):
    a = gb.addr("story_scratch") + RUSH_AT + off
    return gb.mem(a) if n == 1 else gb.mem16(a)


def save_part(gb):
    return bytes(gb.read(gb.addr("story_scratch") + RUSH_AT + SAVE, RUSH_SAVE_N))


def mmss(f):
    s = f // 60
    return f"{s // 60}:{s % 60:02d}"


def on_rush(gb, scr=None):
    return (state(gb) == GS_STORY and gb.mem("story_phase") == SP_RUSH and gb.pb.memory[0xFF40] & 0x80
            and (scr is None or R(gb, SCR) == scr))


def tap(gb, b):
    gb.press(b, 2)
    gb.run(3)


def to_rush(gb):
    """From the title's top level: BONUS > BOSS RUSH (the rush's menu)."""
    title_pick(gb, K_BONUS, K_BOSSRUSH)
    run_until(gb, lambda: on_rush(gb, RS_MENU), 30)
    gb.run(3)
    return gb


def to_list(gb):
    to_rush(gb)
    tap(gb, "down")
    tap(gb, "a")
    run_until(gb, lambda: on_rush(gb, RS_LIST), 30)
    gb.run(3)
    return gb


def into_fight(gb, entered=True):
    """From the fight's banner (GS_GOAL) into its play (entered: the fight starts at once; a BOSS RUSH fight opens with his
    entrance, no warm-up: E9, entered=False)."""
    until(gb, lambda: state(gb) == GS_GOAL, 60)
    gb.write("tip_chance", 0)
    if entered:
        gb.write("boss_hook", 4)                  # (the fight now, no entrance: the tests of the rush itself)
    gb.press("a", 2)
    until(gb, lambda: state(gb) == PLAYING, 10)


def beat(gb):
    """The fight on: he is satisfied now (boss_hook 3), the outro, BOSS BEATEN; stops on the rush's next screen."""
    gb.write("boss_hook", 3)
    clear_regulars(gb)
    until(gb, lambda: state(gb) == LEVEL_CLEAR, 300)
    frames(gb, 3)
    until(gb, lambda: on_rush(gb), 400)
    gb.run(10)                                            # (a new screen takes ~4 frames to build, input is lost then)


def lose_life(gb):
    """A regular reaches the tap: a life (and the freeze); stops when play resumes or the run is over (the result)."""
    lose_a_life(gb)                                       # (a regular one step from the tap: any boss)
    until(gb, lambda: state(gb) != LIFE_LOST, 200)


def pr_block2(mg_bits=0, medals=(), bits=0, best=(), all_score=0, all_time=0, all_n=0, magic=b"MGP2", fix=None):
    """An "MGP2" Practice block: the mini-games' part, the rush part, checksum, complement."""
    r = bytearray(PR_LEN + 2)
    r[0:4] = magic
    r[4:6] = mg_bits.to_bytes(2, "little")
    for g, m in enumerate(medals):
        r[6 + g] = m
    p = PR1_LEN
    r[p:p + 2] = bits.to_bytes(2, "little")
    for v, f in enumerate(best):
        r[p + RSV_BEST + 2 * v:p + RSV_BEST + 2 * v + 2] = f.to_bytes(2, "little")
    r[p + RSV_ALL_SCORE:p + RSV_ALL_SCORE + 3] = all_score.to_bytes(3, "little")
    r[p + RSV_ALL_TIME:p + RSV_ALL_TIME + 2] = all_time.to_bytes(2, "little")
    r[p + RSV_ALL_N] = all_n
    if fix:
        fix(r)
    c = (0x5A + sum(r[:PR_LEN])) & 255
    r[PR_LEN], r[PR_LEN + 1] = c, c ^ 0xFF
    return bytes(r)


def parse2(ram):
    """The "MGP2" block in a battery RAM image: (mini-game bits, medals, rush part)."""
    b = ram[PR_AT:PR_AT + PR_LEN + 2]
    assert b[:4] == b"MGP2", b[:4]
    c = (0x5A + sum(b[:PR_LEN])) & 255
    assert b[PR_LEN] == c and b[PR_LEN + 1] == c ^ 0xFF, "the block's checksum"
    return int.from_bytes(b[4:6], "little"), list(b[6:PR1_LEN]), bytes(b[PR1_LEN:PR_LEN])


def rush_bits(part):
    return int.from_bytes(part[RSV_BITS:RSV_BITS + 2], "little")


def rush_best(part, v):
    return int.from_bytes(part[RSV_BEST + 2 * v:RSV_BEST + 2 * v + 2], "little")


def outside_block(ram):
    """The save but for the Practice region (0x40-0x7F: the practice block, the bonus rounds' cards seen, the EASY / HARD medals) and the boss
    cards seen "BK" (0x28-0x2D: the tests' images carry it with every card seen, so a fight does not pause)."""
    return ram[:0x28] + ram[0x2E:PR_AT] + ram[PR_AT + 0x40:]


# ---- the menu path --------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_bonus_gains_boss_rush_and_its_menu(model):
    """BONUS: SOUNDTRACK / MINI GAMES / BOSS RUSH (rows 7 / 9 / 11). A opens the rush's menu: ALL / CHOOSE with the mug
    cursor, the selected item's details below; Up / Down wrap; B goes back to BONUS with the cursor on BOSS RUSH."""
    with booted(model) as gb:
        title_pick(gb, K_BONUS)
        gb.run(MENU_SETTLE)
        assert menu_items(gb) == [K_CREDITS, K_SOUNDTRACK, K_MINIGAMES, K_BOSSRUSH]
        assert list(gb.read("title_rows", 4)) == [7, 9, 11, 13]
        tap(gb, "b")
        gb.run(MENU_SETTLE)
        to_rush(gb)
        hold_stage_anim(gb)
        assert gb.mem("story_on") == 0 and R(gb, SEL) == 0
        assert lines(gb, (0, 4, 6)) == ["BOSS RUSH", "ALL", "CHOOSE"]
        assert lines(gb, range(13, 17)) == ["EVERY BOSS IN A ROW", "NO BEST YET", "", "A PLAY  B BACK"]
        o = gb.read(0xFE00, 4)
        assert o[0] == 4 * 8 - 7 + 16 and o[1] == 6 * 8 + 8, "the mug cursor on ALL"
        check_golden(gb, "rush_menu")
        tap(gb, "down")
        assert R(gb, SEL) == 1 and lines(gb, range(13, 17)) == ["ONE BOSS ALONE", "3 LIVES", "", "A PICK  B BACK"]
        assert gb.read(0xFE00, 1)[0] == 6 * 8 - 7 + 16
        tap(gb, "down")
        assert R(gb, SEL) == 0, "wraps"
        tap(gb, "up")
        assert R(gb, SEL) == 1
        tap(gb, "b")
        run_until(gb, lambda: state(gb) == TITLE and gb.pb.memory[0xFF40] & 0x80, 30)
        gb.run(MENU_SETTLE)
        assert gb.mem("title_menu") == TM_BONUS and gb.mem("title_sel") == 3, "BONUS, the cursor on BOSS RUSH"
        tap(gb, "b")
        gb.run(MENU_SETTLE)
        assert gb.mem("title_menu") == TM_TOP


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_debug_list_has_every_built_boss_unlocked(model):
    """The DEBUG_MENU build: CHOOSE lists every built boss (the story's step table: gen_story BUILT_SLOTS["BOSS"]) in chapter order in the one-line style,
    all playable on a fresh cartridge: "< NAME >" on the selection line, his fight sprite in the window, his venue, "BEST --:--", the counter "n / N";
    LEFT / RIGHT walk the list with wrap; B goes back to the menu, on CHOOSE."""
    with to_list(booted(model)) as gb:
        hold_stage_anim(gb)
        gb.run(10)
        assert BUILT[0] == 0 and {0, 2, 3, 4} <= set(BUILT) == set(BOSS_BUILT), "Big Tex first; the first four built at least"
        n = len(BUILT)
        assert header(gb) == header_text("BOSS RUSH", f"1 / {n}") and band_rows_ok(gb)
        assert selection(gb) == NAMES[BUILT[0]] and line(gb, 12).strip() == VENUES[BUILT[0]] and line(gb, 13).strip() == "BEST --:--"
        assert hint(gb) == "@ PLAY   $ BACK"
        assert not gb.visible_sprites()
        assert set(tilemap_row(gb, 5, 0, 20)) == {54}, "a blank row under the band"
        check_golden(gb, "rush_list")
        for k in range(1, n):
            tap(gb, "right")
            gb.run(6)
            v = BUILT[k]
            assert R(gb, LIST_SEL) == k and selection(gb) == NAMES[v] and line(gb, 12).strip() == VENUES[v], k
            assert header(gb).endswith(f"{k + 1} / {n}")
        tap(gb, "right")
        assert R(gb, LIST_SEL) == 0, "wraps"
        tap(gb, "b")
        run_until(gb, lambda: on_rush(gb, RS_MENU), 30)
        assert R(gb, SEL) == 1, "the menu, on CHOOSE"


@pytest.mark.only_model('dmg')
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_list_works_for_any_number_of_built_bosses(model):
    """CHOOSE with 1..10 built bosses (the mask rewritten in RAM, the list reopened): each boss's baked tiles are found by his rank among the built,
    the counter says n, the names and the windows are right."""
    BUILT_AT = 44                                         # struct rush_state.built
    with to_list(booted(model)) as gb:
        for n in range(1, BOSS_COUNT + 1):
            tap(gb, "b")
            run_until(gb, lambda: on_rush(gb, RS_MENU), 30)
            gb.run(3)
            a = gb.addr("story_scratch") + RUSH_AT
            gb.write(a + BUILT_AT, ((1 << n) - 1) & 255)
            gb.write(a + BUILT_AT + 1, (1 << n) - 1 >> 8)
            gb.write(a + 47, n)                           # nlines
            gb.write(a + LIST_SEL, 0)
            tap(gb, "a")                                  # (the menu is on CHOOSE after B)
            run_until(gb, lambda: on_rush(gb, RS_LIST), 60)
            gb.run(8)
            assert header(gb).endswith(f"1 / {n}") and selection(gb) == NAMES[0], n
            for k in range(1, n):
                tap(gb, "right")
                gb.run(4)
                assert selection(gb) == NAMES[k], (n, k)
                body = tilemap_row(gb, 8, 7, 6)
                assert body == [136 + 12 * k + 2 * i for i in range(6)], (n, k, body)


WIN = (56, 56, 104, 88)                                   # the window's interior in pixels: columns 7-12, rows 7-10


def drawn_centre(gb):
    """The middle of what is drawn in the window's interior (the pixels that are not the backdrop's colour), in pixels: (x, y)."""
    im = gb.image().convert("RGB")
    x0, y0, x1, y1 = WIN
    back = im.getpixel((x0, y0))
    xs, ys = [], []
    for y in range(y0, y1):
        for x in range(x0, x1):
            if im.getpixel((x, y)) != back:
                xs.append(x)
                ys.append(y)
    assert xs, "something is drawn"
    return (min(xs) + max(xs) + 1) / 2, (min(ys) + max(ys) + 1) / 2


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_every_boss_is_centred_by_his_drawn_pixels(model):
    """The window's middle is (80, 72): each built boss's fight sprite, measured on the picture, lands within half a pixel of it both ways."""
    with to_list(booted(model)) as gb:
        for k, v in enumerate(BUILT):
            to_game = k
            while R(gb, LIST_SEL) != to_game:
                tap(gb, "right")
            gb.run(8)
            cx, cy = drawn_centre(gb)
            assert abs(cx - 80) <= 0.5 and abs(cy - 72) <= 0.5, (NAMES[v], cx, cy)


def test_the_list_follows_the_story_data():
    """No boss list of its own: the rush asks the story data (build/story.h BOSS_BUILT_MASK, from gen_story BUILT_SLOTS: the boss has no step
    of his own since he comes in Last call's level) which bosses are built, so a boss added to BUILT_SLOTS appears here with no edit to src/rush.c."""
    src = (ROOT / "src" / "rush.c").read_text()
    assert "BOSS_BUILT_MASK" in src
    assert len(re.findall(r'"[A-Z ]+"', src.split("boss_name[BOSS_COUNT] = {")[1].split("};")[0])) == BOSS_COUNT


# ---- the release build: the unlock rule -------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_release_list_is_locked_until_beaten(model, release_built):
    """`make release`: on a fresh cartridge every built boss is "? ? ?" (a silhouette on Color, "??" on a DMG, both centred; LOCKED, STORY OR ARCADE; no A on
    the hint row; A does nothing) and ALL is LOCKED; one boss beaten: his name, venue and sprite, A plays him, ALL still locked; two: ALL opens."""
    with release_rom(model) as gb:
        to_rush(gb)
        assert line(gb, 4).strip() == "ALL LOCKED"
        assert lines(gb, range(13, 17)) == ["LOCKED", "BEAT 2 BOSSES IN", "STORY OR ARCADE", "B BACK"]
        tap(gb, "a")
        gb.run(5)
        assert on_rush(gb, RS_MENU), "ALL is locked"
        tap(gb, "down")
        tap(gb, "a")
        run_until(gb, lambda: on_rush(gb, RS_LIST), 30)
        gb.run(8)
        n = len(BUILT)
        for k in range(n):
            assert selection(gb) == "? ? ?" and line(gb, 12).strip() == "LOCKED" and line(gb, 13).strip() == "STORY OR ARCADE", k
            assert hint(gb) == "$ BACK"
            cx, cy = drawn_centre(gb)
            assert abs(cx - 80) <= 0.5 and abs(cy - 72) <= 0.5, ("locked", k, cx, cy)
            if k == 2:
                check_golden(gb, "rush_list_locked")
            tap(gb, "right")
            gb.run(8)
        assert R(gb, LIST_SEL) == 0
        tap(gb, "a")
        gb.run(5)
        assert on_rush(gb, RS_LIST), "a locked boss does not play"
    ram = with_block(v7_image(), pr_block2(bits=1 << 2, best=[0, 0, 61 * 60 + 30]))
    with release_rom(model, ram) as gb:
        to_rush(gb)
        assert line(gb, 4).strip() == "ALL LOCKED"
        tap(gb, "down")
        tap(gb, "a")
        run_until(gb, lambda: on_rush(gb, RS_LIST), 30)
        gb.run(8)
        i = BUILT.index(2)                                # the Sasquatch
        for _ in range(i):
            tap(gb, "right")
        gb.run(8)
        assert selection(gb) == "SASQUATCH" and line(gb, 12).strip() == "THE LUMBER LODGE" and line(gb, 13).strip() == "BEST 1:01"
        assert hint(gb) == "@ PLAY   $ BACK"
        check_golden(gb, "ol_rush_unlocked")
        tap(gb, "left")
        gb.run(8)
        assert selection(gb) == "? ? ?" and hint(gb) == "$ BACK", "the neighbour is still locked"
        tap(gb, "right")
        gb.run(8)
        tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_GOAL, 60)
        assert gb.mem("boss_id") == 2 and gb.mem("play_mode") == MODE_RUSH
    ram = with_block(v7_image(), pr_block2(bits=(1 << 2) | (1 << 4)))
    with release_rom(model, ram) as gb:
        to_rush(gb)
        assert line(gb, 4).strip() == "ALL"
        tap(gb, "a")
        run_until(gb, lambda: on_rush(gb, RS_NEXT), 30)
        assert R(gb, N) == 2 and R(gb, BOSS) == 2, "ALL: the two unlocked bosses, from the Sasquatch"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_locked_boss_is_a_silhouette_on_color_and_question_marks_on_a_dmg(model, release_built):
    with release_rom(model) as gb:
        to_list(gb)
        cx, cy = drawn_centre(gb)
        im = gb.image().convert("RGB")
        colours = {im.getpixel((x, y)) for x in range(56, 104) for y in range(56, 88)}
        if model == "cgb":
            assert len(colours) == 2, "one backdrop colour and one silhouette colour"
        else:
            assert len(colours) == 2, "white and black"
            assert [t for t in tilemap_row(gb, 8, 7, 6)] != [BLANK] * 6


# ---- unlocks: a boss beaten in STORY or ARCADE ------------------------------------------------------------------------
def story_boss(gb):
    """In a venue's Opening (STORY or ARCADE): the Opening won, Last call's quota met, his fight entered."""
    boss_from_opening(gb)
    assert gb.mem("boss_on") == 1
    to_goal(gb)                                           # (in place: no banner; his tiles streamed in, the fight started at once)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_story_boss_win_unlocks_him_and_it_survives_a_reset(model):
    """Big Tex beaten in STORY: his bit in the block at once (the mini-games' part kept); after a reset the release list
    names him (and the debug-select run records nothing)."""
    ram0 = with_block(v7_image(), pr_block(1, [MEDAL_SILVER]))
    gb = to_chapter(model, 0)
    gb.pb.stop(save=False)
    with booted(model, ram0) as gb:
        hold_stage_anim(gb)
        from test_story import to_continue
        title_pick(gb, 5)                                 # (K_PLAY: STORY from the saloon)
        from conftest import K_STORY, menu_to, menu_tap
        menu_to(gb, K_STORY)
        menu_tap(gb, "a")
        menu_tap(gb, "a")                                 # (HOW HARD: NORMAL)
        run_until(gb, lambda: state(gb) == GS_STORY, 60)
        gb.write("story_step", 0)
        from test_story import skip_scene
        skip_scene(gb)                                    # INTRO (and the story map: A at the saloon)
        skip_scene(gb)                                    # PRE_SALOON
        to_goal(gb)
        assert gb.mem("story_chapter") == 0
        story_boss(gb)
        gb.write("boss_hook", 3)
        clear_regulars(gb)
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 300)
        ram = save_ram(gb)
    mg_bits, medals, part = parse2(ram)
    assert rush_bits(part) == 1 and (mg_bits, medals[0]) == (1, MEDAL_SILVER)
    with booted(model, ram) as gb:
        to_list(gb)
        assert rush_bits(save_part(gb)) == 1


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_an_arcade_boss_win_unlocks_him_but_a_debug_select_run_does_not(model):
    from test_arcade import start_arcade
    with start_arcade(model) as gb:
        to_goal(gb)
        story_boss(gb)
        gb.write("boss_hook", 3)
        clear_regulars(gb)
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 300)
        assert gb.mem("save_lock") == 1
        ram = save_ram(gb)
    assert rush_bits(parse2(ram)[2]) == 1
    with booted(model) as gb:
        title_pick(gb, 5, 1)                              # PLAY > STORY
        run_until(gb, lambda: state(gb) == GS_STORY, 60)
        gb.write("save_lock", 2)                          # (a debug-select run)
        while state(gb) != GS_GOAL:
            gb.press("start", 2)
            gb.run(3)
        to_goal(gb)
        story_boss(gb)
        gb.write("boss_hook", 3)
        clear_regulars(gb)
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 300)
        ram = save_ram(gb)
    assert ram[PR_AT:PR_AT + 4] != b"MGP2", "nothing recorded"


# ---- the block: migration and bad blocks ------------------------------------------------------------------------------
@pytest.mark.only_model('dmg')
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_mgp1_migrates_with_its_mini_games(model):
    """An "MGP1" block (2026-10-11): its mini-games and medals kept, written back at boot as "MGP2" with an empty rush
    part; the other blocks untouched."""
    good = v7_image([("ABC", 500)], story=3, step=1, story_tbl=[("STO", 900)])
    ram = with_block(good, pr_block(1 | 1 << 3, [MEDAL_GOLD, 0, 0, MEDAL_SILVER]))
    with booted(model, ram) as gb:
        assert gb.mem16("mg_unlocked") == 9 and list(gb.read("mg_best", 4)) == [MEDAL_GOLD, 0, 0, MEDAL_SILVER]
        to_rush(gb)
        assert save_part(gb) == bytes(RUSH_SAVE_N)
        out = save_ram(gb)
    assert parse2(out) == (9, [MEDAL_GOLD, 0, 0, MEDAL_SILVER] + [0] * 6, bytes(RUSH_SAVE_N))
    assert outside_block(out) == outside_block(ram)


@pytest.mark.only_model('dmg')
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_good_block_loads_and_a_bad_one_loses_only_itself(model):
    good = v7_image([("ABC", 500)], story=3, step=1, story_tbl=[("STO", 900)])
    ok = pr_block2(1, [MEDAL_GOLD], bits=0b10101, best=[600, 0, 1200], all_score=12340, all_time=3600, all_n=3)
    with booted(model, with_block(good, ok)) as gb:
        assert gb.mem16("mg_unlocked") == 1
        to_rush(gb)
        assert save_part(gb) == ok[PR1_LEN:PR_LEN]
        assert lines(gb, range(13, 16)) == ["EVERY BOSS IN A ROW", "BEST 012340", "3 BOSSES 1:00"]
    bad_sum = bytearray(ok)
    bad_sum[PR_LEN] ^= 1
    cases = {
        "checksum": bytes(bad_sum),
        "magic": pr_block2(1, [MEDAL_GOLD], bits=1, magic=b"MGP3"),
        "a boss bit past the table": pr_block2(1, [MEDAL_GOLD], bits=1 << BOSS_COUNT),
        "ALL's score out of range": pr_block2(1, [MEDAL_GOLD], all_score=1000000),
        "ALL's count out of range": pr_block2(1, [MEDAL_GOLD], all_n=BOSS_COUNT + 1),
        "a medal byte past the three fields": pr_block2(1, [64], bits=1),
        "blank": bytes(PR_LEN + 2),
    }
    for name, block in cases.items():
        with booted(model, with_block(good, block)) as gb:
            assert gb.mem16("mg_unlocked") == 0 and list(gb.read("mg_best", MG_PLANNED)) == [0] * MG_PLANNED, name
            assert gb.mem("story_progress") == 3 and gb.mem("story_reached") == 1, name
            assert table(gb)[0] == ("ABC", 500) and table(gb, 1)[0] == ("STO", 900), name
            to_rush(gb)
            assert save_part(gb) == bytes(RUSH_SAVE_N), name
            assert line(gb, 14).strip() == "NO BEST YET", name


@pytest.mark.only_model('dmg')
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_mini_game_record_keeps_the_rush_part(model):
    """mg_record rewrites the block from WRAM: the rush part is kept as it was."""
    from test_mg import mg_enter
    from test_mg import MG_STORY
    ok = pr_block2(0, [], bits=0b101, best=[700], all_score=999, all_time=60, all_n=1)
    with booted(model, with_block(v7_image(), ok)) as gb:
        mg_enter(gb, MG_QUICKDRAW, MG_STORY)
        assert gb.mem16("mg_unlocked") == 1
        ram = save_ram(gb)
    assert parse2(ram) == (1, [0] * MG_PLANNED, ok[PR1_LEN:PR_LEN])


# ---- CHOOSE -----------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_rush_fight_ends_only_when_the_bar_is_clear(model):
    """BOSS RUSH plays the same rule as the story: his meter at 0 does not end the fight while regulars are on screen
    (still PLAYING, the banner CLEAR THE BAR, the fight's clock running, no BOSS BEATEN); the bar clear then ends it
    as before (BOSS BEATEN, the result)."""
    with booted(model, v7_image([("ABC", 500)], story=2, step=1, story_tbl=[("STO", 900)])) as gb:
        to_list(gb)
        tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_GOAL, 60)
        gb.run(3)
        into_fight(gb)
        gb.write("patron_speed", 0)
        gb.write("hurry_speed", 0)
        frames(gb, 100)
        assert gb.mem("patrons_live") > 0
        gb.write("boss_hook", 3)
        frames(gb, 5)
        t = R(gb, FIGHT_T, 2)
        from test_story import banner_text, centred
        assert state(gb) == PLAYING and banner_text(gb, 0) == centred("CLEAR THE BAR")
        frames(gb, 200)
        assert state(gb) == PLAYING and R(gb, FIGHT_T, 2) >= t + 200, "the fight's clock runs on"
        clear_regulars(gb)
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 300)
        gb.run(3)
        assert banner_text(gb, 1) == centred("BOSS BEATEN")
        run_until(gb, lambda: on_rush(gb, RS_RESULT), 400)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_choose_plays_one_fight_and_comes_back(model):
    """A on a boss: his venue's boss step as the story plays it (his banner, 3 lives, the score from 0, MODE_RUSH,
    nothing else of the story), BOSS BEATEN, then the result: YOU WIN, his name, the time (the fight's PLAYING frames),
    the score (with the clear bonus), NEW BEST; A retries the same boss (3 lives, 0 again); B comes back to the list on
    him. The time is his best in the block; a slower win keeps it. Nothing outside the block is written."""
    ram0 = v7_image([("ABC", 500)], story=2, step=1, story_tbl=[("STO", 900)])
    with booted(model, ram0) as gb:
        to_list(gb)
        tap(gb, "right")                                  # the second built boss
        v = BUILT[1]
        tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_GOAL, 60)
        gb.run(3)
        assert (gb.mem("boss_on"), gb.mem("boss_id"), gb.mem("play_mode"), gb.mem("story_on")) == (1, v, MODE_RUSH, 1)
        assert gb.mem("lives") == 3 and gb.mem("story_step") == SHIFT_STEP[2] and gb.mem("save_lock") == 1
        assert R(gb, SCR) == RS_FIGHT and R(gb, MODE) == RM_CHOOSE
        into_fight(gb)
        frames(gb, 100)
        lose_life(gb)
        assert gb.mem("lives") == 2 and state(gb) == PLAYING and gb.mem("boss_on") == 1
        gb.run(50)
        t = R(gb, FIGHT_T, 2)
        assert 140 <= t <= 160
        gb.write("boss_hook", 3)
        clear_regulars(gb)
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 300)
        gb.run(3)
        from test_story import banner_text, centred
        assert banner_text(gb, 1) == centred("BOSS BEATEN")
        t = R(gb, FIGHT_T, 2)
        run_until(gb, lambda: on_rush(gb, RS_RESULT), 400)
        gb.run(3)
        sc = 0
        a = gb.addr("score")
        sc = gb.mem16(a) | gb.mem16(a + 2) << 16
        assert sc >= LEVEL_BONUS
        assert lines(gb, (3, 5, 7, 9, 13, 15)) == ["YOU WIN", NAMES[v], "TIME " + mmss(t), f"SCORE {sc:06d}",
                                                   "NEW BEST", "A RETRY  B BACK"]
        assert R(gb, RESULT) == 1 and R(gb, BEST) == 1 and rush_best(save_part(gb), v) == t
        tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_GOAL, 60)
        a = gb.addr("score")
        assert gb.mem("boss_id") == v and gb.mem("lives") == 3 and gb.mem16(a) == 0, "RETRY"
        into_fight(gb)
        frames(gb, t + 30)
        beat(gb)
        assert on_rush(gb, RS_RESULT) and R(gb, BEST) == 0 and rush_best(save_part(gb), v) == t, "slower: kept"
        assert line(gb, 13).strip() == "BEST " + mmss(t)
        tap(gb, "b")
        run_until(gb, lambda: on_rush(gb, RS_LIST), 30)
        gb.run(3)
        assert R(gb, LIST_SEL) == 1 and selection(gb) == NAMES[v] and line(gb, 13).strip() == "BEST " + mmss(t)
        ram = save_ram(gb)
    assert outside_block(ram) == outside_block(ram0), "no story progress, tunes or tables written"
    assert rush_best(parse2(ram)[2], v) == t


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_choose_out_of_lives_is_a_loss(model):
    """Three lives lost: GAME OVER over the frozen fight (not TRY AGAIN, no venue restart), then YOU LOSE; no best saved,
    nothing in the score tables; B back to the list."""
    with booted(model) as gb:
        to_list(gb)
        tap(gb, "a")
        into_fight(gb)
        for k in range(3):
            lose_life(gb)
        from test_story import banner_text, centred
        assert state(gb) == GS_STORY and banner_text(gb, 1) == centred("GAME OVER")
        assert gb.mem("story_restarts") == 0
        run_until(gb, lambda: on_rush(gb, RS_RESULT), 200)
        gb.run(3)
        assert lines(gb, (3, 5)) == ["YOU LOSE", "BIG TEX"] and line(gb, 13) == ""
        assert R(gb, RESULT) == 0 and save_part(gb) == bytes(RUSH_SAVE_N)
        assert table(gb)[0][1] == 0 and gb.mem("boss_on") == 0
        tap(gb, "b")
        run_until(gb, lambda: on_rush(gb, RS_LIST), 30)
        ram = save_ram(gb)
    assert ram[PR_AT:PR_AT + 4] != b"MGP2", "nothing written"


# ---- ALL --------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_all_chains_the_fights_and_ends_after_the_last(model):
    """ALL: a NEXT card before each fight (FIGHT n OF m, NEXT: <BOSS>, his venue, lives, score, time; A or 3 s), the
    bosses in chapter order; lives carried (a lost one stays lost), a won fight +1 up to 3; the score totalled; after
    the last boss ALL CLEAR with every boss beaten, the total time and score, NEW BEST; the best and each boss's time
    saved; A retries ALL, B back to the menu on ALL. Nothing outside the block is written."""
    ram0 = v7_image([("ABC", 500)], story=2, step=1, story_tbl=[("STO", 900)])
    with booted(model, ram0) as gb:
        to_rush(gb)
        tap(gb, "a")
        run_until(gb, lambda: on_rush(gb, RS_NEXT), 30)
        gb.run(3)
        n = len(BUILT)
        assert R(gb, MODE) == RM_ALL and R(gb, N) == n and R(gb, BOSS) == BUILT[0]
        assert lines(gb, (3, 6, 8, 13, 14, 15, 16)) == [f"FIGHT 1 OF {n}", "NEXT: BIG TEX", "THE SALOON", "LIVES 3",
                                                        "SCORE 000000", "TIME 0:00", "A GO"]
        expect_lives, total = 3, 0
        for k, v in enumerate(BUILT):
            if k:
                assert on_rush(gb, RS_NEXT) and R(gb, BOSS) == v
                assert lines(gb, (3, 6, 8)) == [f"FIGHT {k + 1} OF {n}", "NEXT: " + NAMES[v], VENUES[v]]
                assert line(gb, 13).strip() == f"LIVES {expect_lives}"
                if k == 1 and model == "dmg" or k == 1 and model == "cgb":
                    check_golden(gb, "rush_next_card")
            if k == 0:
                gb.run(200)                               # (3 s: the card goes by itself)
            else:
                tap(gb, "a")
            run_until(gb, lambda: state(gb) == GS_GOAL, 60)
            assert gb.mem("boss_id") == v and gb.mem("lives") == expect_lives
            into_fight(gb)
            frames(gb, 30)
            if k < 2:                                     # a life lost in the first two fights
                lose_life(gb)
                expect_lives -= 1
                assert gb.mem("lives") == expect_lives
            beat(gb)
            total += R(gb, FIGHT_T, 2)
            assert R(gb, WON) == k + 1 and R(gb, TOTAL_T, 2) == total
            a = gb.addr("score")
            assert gb.mem16(a) | gb.mem16(a + 2) << 16 >= (k + 1) * LEVEL_BONUS, "the score is carried and totalled"
            expect_lives = min(3, expect_lives + 1)
        assert on_rush(gb, RS_RESULT)
        a = gb.addr("score")
        sc = gb.mem16(a) | gb.mem16(a + 2) << 16
        assert sc >= n * LEVEL_BONUS
        assert lines(gb, (3, 5, 7, 9, 13, 15)) == ["ALL CLEAR", f"{n} OF {n} BOSSES", "TIME " + mmss(total),
                                                   f"SCORE {sc:06d}", "NEW BEST", "A RETRY  B BACK"]
        part = save_part(gb)
        assert int.from_bytes(part[RSV_ALL_SCORE:RSV_ALL_SCORE + 3], "little") == sc
        assert int.from_bytes(part[RSV_ALL_TIME:RSV_ALL_TIME + 2], "little") == total and part[RSV_ALL_N] == n
        assert all(rush_best(part, v) for v in BUILT)
        tap(gb, "a")
        run_until(gb, lambda: on_rush(gb, RS_NEXT), 30)
        gb.run(10)
        assert R(gb, WON) == 0 and gb.mem("lives") == 3 and R(gb, BOSS) == BUILT[0], "RETRY: ALL from the first"
        gb.press("a", 2)
        run_until(gb, lambda: state(gb) == GS_GOAL, 60)
        into_fight(gb)
        for _ in range(3):
            lose_life(gb)
        run_until(gb, lambda: on_rush(gb, RS_RESULT), 200)
        gb.run(3)
        assert lines(gb, (3, 5, 13)) == ["GAME OVER", f"0 OF {n} BOSSES", f"BEST {sc:06d}"]
        tap(gb, "b")
        run_until(gb, lambda: on_rush(gb, RS_MENU), 30)
        gb.run(3)
        assert R(gb, SEL) == 0 and line(gb, 14).strip() == f"BEST {sc:06d}"
        ram = save_ram(gb)
    assert outside_block(ram) == outside_block(ram0), "no story progress, tunes or tables written"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_all_out_of_lives_ends_the_run(model):
    """ALL with two lives lost in the first fight and the last in the second: GAME OVER, 1 OF n BOSSES, the score so far
    is the best (a run that ends early still counts its score)."""
    with booted(model) as gb:
        to_rush(gb)
        tap(gb, "a")
        run_until(gb, lambda: on_rush(gb, RS_NEXT), 30)
        gb.run(10)
        tap(gb, "a")
        into_fight(gb)
        lose_life(gb)
        lose_life(gb)
        beat(gb)
        assert on_rush(gb, RS_NEXT) and gb.mem("lives") == 2, "1 left, +1 for the win"
        tap(gb, "a")
        into_fight(gb)
        lose_life(gb)
        lose_life(gb)
        run_until(gb, lambda: on_rush(gb, RS_RESULT), 200)
        gb.run(3)
        n = len(BUILT)
        assert lines(gb, (3, 5, 13)) == ["GAME OVER", f"1 OF {n} BOSSES", "NEW BEST"]
        assert save_part(gb)[RSV_ALL_N] == 1


# ---- the list after the Mothership (the lights buffer used to overlap the struct's built / nlines and the list's selection) -------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("route", ["win", "lose", "quit"])
def test_the_list_is_intact_after_the_mothership(model, route):
    """CHOOSE on the last boss (the Mothership; the window scrolled to the end), played through his entrance (the lights flicker: 8 bytes
    written to LIGHTS_BUF) and left by a win, out of lives or QUIT TO MENU: the struct's built / top / nlines are as before and the list
    shows the same window, with the cursor able to climb to the first boss."""
    import test_pause as tp
    with booted(model) as gb:
        to_list(gb)
        tap(gb, "left")                                   # (wraps to the last line)
        assert R(gb, LIST_SEL) == len(BUILT) - 1 and BUILT[-1] == 9
        before = bytes(gb.read(gb.addr("story_scratch") + RUSH_AT, 48))
        name, centre = selection(gb), drawn_centre(gb)
        tap(gb, "a")
        into_fight(gb, entered=False)
        frames(gb, 240)                                   # (the entrance's lights)
        if route == "quit":
            tp.tap(gb, "start", 3)
            tp.quit_yes(gb)
            run_until(gb, lambda: on_rush(gb, RS_MENU), 60)
            gb.run(5)
            tap(gb, "down")
            tap(gb, "a")                                  # CHOOSE: the list
        elif route == "lose":
            for k in range(3):
                lose_life(gb)
            run_until(gb, lambda: on_rush(gb, RS_RESULT), 300)
            gb.run(5)
            tap(gb, "b")
        else:
            until(gb, lambda: gb.mem("intro_timer") == 0 and state(gb) == PLAYING, 700)
            beat(gb)
            tap(gb, "b")
        run_until(gb, lambda: on_rush(gb, RS_LIST), 60)
        gb.run(12)
        after = bytes(gb.read(gb.addr("story_scratch") + RUSH_AT, 48))
        for off in (2, 3, 44, 45, 47):                     # sel, list_sel, built (2), nlines (the palette byte 46 is the list's own)
            assert after[off] == before[off], (off, before.hex(), after.hex())
        assert selection(gb) == name == "MOTHERSHIP" and drawn_centre(gb) == centre, "the same list, the same picture"
        for _ in range(len(BUILT) - 1):
            tap(gb, "left")
        gb.run(10)
        assert R(gb, LIST_SEL) == 0 and selection(gb) == NAMES[BUILT[0]]
