# M12: the bonus rounds Perfect Pour and Tip Shower (src/bonus2.c), rotating with the can shake-up.
import json
import re

import pytest
from conftest import ROOT, check_golden, venue
from test_bonus import enter_bonus, lines
from test_flow import (BONUS, PLAYING, patron_group_tiles, run_until, score, state, tile_id, tilemap_row)

pytestmark = pytest.mark.timeout(240)

PH_END = 4
PP_INTRO, PP_READY, PP_POUR, PP_SETTLE = range(4)
PR_NONE, PR_PERFECT, PR_GOOD, PR_LOW, PR_HIGH, PR_SPILL = range(6)
SFX_BREAK, SFX_COIN = 4, 6
SFX_COUNT = 9
B2H = (ROOT / "build" / "bonus2_art.h").read_text()
B2_BASE = 48 + int(re.search(r"#define BAR_TILE_COUNT (\d+)", (ROOT / "build" / "art.h").read_text()).group(1))   # B2_BG (src/bonus2.c): past the framework's medal icon (48 tiles), MG_GAME_BG
B2 = json.loads((ROOT / "build" / "bonus2.json").read_text())
SRC = (ROOT / "src" / "bonus2.c").read_text()


def define(name, text=SRC):
    return int(re.search(rf"#define {name}\s+(\d+)", text).group(1))


POUR_RATE, FOAM_POUR, FOAM_RISE, FOAM_RISE_STEP = (define(n) for n in ("POUR_RATE", "FOAM_POUR", "FOAM_RISE", "FOAM_RISE_STEP"))
TIPS_TIME, TRAY_DIRTY, TRAY_SURFACE = define("TIPS_TIME"), define("TRAY_DIRTY"), define("TRAY_SURFACE")
OBJ_B2 = 96
T_DOME, T_STREAK, T_HEAD = OBJ_B2 + 6, OBJ_B2 + 8, OBJ_B2 + 10
T_TRAY, T_TRAY_DIRTY, T_TOMATO = OBJ_B2, OBJ_B2 + 8, OBJ_B2 + 16   # (frames 0, 4, 8: 4 entries a tray)
TS_ITEMS = 7
GLASS_COL, GLASS_ROW, INNER_BOT = 9, 6, 80


def text_row(gb, y):
    return tilemap_row(gb, y, 0, 20)


def glyphs(s):
    out = []
    for c in s:
        if c == " ":
            continue
        out.append(tile_id("GLYPH_" + c))
    return out


def shows(gb, y, s):
    row = [t for t in text_row(gb, y) if t != tile_id("HUD_BLANK")]
    want = glyphs(s.replace("!", ""))
    return row[:len(want)] == want


def sfx(gb, i):
    return gb.read("sfx_count", SFX_COUNT)[i]


def finish(gb):
    gb.write("bonus_phase", PH_END)
    gb.write("bonus_timer", 129)
    run_until(gb, lambda: state(gb) == PLAYING, 200)   # (level 11 opens with the LOOP 2 banner)
    gb.run(2)


# ---- rotation ----------------------------------------------------------------------------------------
def test_rounds_rotate_shake_up_pour_tips(gb):
    kinds = []
    for lvl in (2, 4, 6, 8, 10, 12, 14):
        gb.write("level", lvl)
        gb.write("level_clear", 1)
        run_until(gb, lambda: state(gb) == BONUS, 400)
        kinds.append(gb.mem("bonus_kind"))
        gb.run(10)
        if kinds[-1] == 1:
            assert shows(gb, 2, "PERFECT POUR") and shows(gb, 3, "FILL TO THE LINE")
        elif kinds[-1] == 2:
            assert shows(gb, 2, "TIP SHOWER") and shows(gb, 3, "CATCH THE TIPS")
        else:
            assert shows(gb, 4, "BONUS ROUND")
        finish(gb)
        assert gb.mem("level") == lvl + 1
    assert kinds == [0, 1, 2, 0, 1, 2, 0]
    assert gb.mem("bonus_round") == 7


def test_shake_up_difficulty_counts_shake_ups(gb):
    seen = []
    for before in (0, 1, 2, 3):
        enter_bonus(gb, 2, rounds_before=before)
        seen.append((gb.mem("bonus_kind"), gb.mem("bonus_swaps_total") if gb.mem("bonus_kind") == 0 else None))
        finish(gb)
    assert seen == [(0, 7), (1, None), (2, None), (0, 8)]


# ---- Perfect Pour -----------------------------------------------------------------------------------
def enter_pour(gb):
    enter_bonus(gb, 2, rounds_before=1)
    assert gb.mem("bonus_kind") == 1
    run_until(gb, lambda: gb.mem("bonus_phase") == PP_READY, 200)
    gb.run(2)                                           # (the banner text goes through the VBlank queue)


def level(gb):
    return gb.mem("pour_liquid") + gb.mem("pour_foam")


def pour_to(gb, release_at):
    """Hold A until the visible level (beer + foam) reaches release_at, then let go. Returns the frames held."""
    gb.hold("a")
    n = 0
    while level(gb) < release_at and gb.mem("bonus_phase") in (PP_READY, PP_POUR) and n < 400:
        gb.run(1)
        n += 1
    gb.release("a")
    return n


def settle(gb):
    run_until(gb, lambda: gb.mem("pour_result") != PR_NONE, 200)
    return gb.mem("pour_result")


def test_pour_banner_glass_and_line(gb):
    enter_pour(gb)
    assert shows(gb, 2, "GLASS 1") and shows(gb, 3, "FILL TO THE LINE")
    line = gb.mem("pour_line")
    k = gb.mem("pour_target")
    assert line == B2["pour_targets"][k]
    # the glass on the BG: 2 x 5 tiles; the line's row shows that line's tiles
    rows = [tilemap_row(gb, GLASS_ROW + r, GLASS_COL, 2) for r in range(5)]
    base = B2_BASE
    lr = B2["line_row"][k]
    for r in range(5):
        want = [base + 10 + 2 * k, base + 11 + 2 * k] if r == lr else [base + 2 * r, base + 2 * r + 1]
        assert rows[r] == want, r
    # the arrows point at the line (tip row 3 of the entry)
    arrows = [s for s in gb.visible_sprites() if s["tile"] == OBJ_B2 + 22]
    assert len(arrows) == 2 and all(s["y"] - 16 + 3 == INNER_BOT - line for s in arrows)


def test_holding_a_pours_and_releasing_stops_the_beer(gb):
    enter_pour(gb)
    assert level(gb) == 0
    gb.hold("a")
    gb.run(2)
    assert gb.mem("bonus_phase") == PP_POUR
    gb.run(40)
    liq = gb.mem("pour_liquid")
    assert 9 <= liq <= 11, liq                                  # 1 px per POUR_RATE frames
    assert gb.mem("pour_foam") == FOAM_POUR
    beer = [s for s in gb.visible_sprites() if s["tile"] in (OBJ_B2, OBJ_B2 + 2)]
    assert beer and all(s["flags"] & 0x80 for s in beer), "the beer is drawn behind the glass (BG priority)"
    gb.release("a")
    gb.run(2)
    assert gb.mem("bonus_phase") == PP_SETTLE
    after = gb.mem("pour_liquid")
    gb.run(60)
    assert gb.mem("pour_liquid") == after, "no more beer once A is up"


def test_foam_keeps_rising_after_the_release(gb):
    enter_pour(gb)
    pour_to(gb, 12)
    gb.run(1)
    at_release = level(gb)
    steps = []
    for _ in range(FOAM_RISE * FOAM_RISE_STEP + 4):
        gb.run(1)
        steps.append(level(gb))
    assert steps[-1] == at_release + FOAM_RISE, (at_release, steps)
    assert steps[FOAM_RISE_STEP // 2] < steps[-1], "it rises gradually"
    assert all(b >= a for a, b in zip(steps, steps[1:]))


@pytest.mark.parametrize("off,result,points", [(0, PR_PERFECT, 3000), (1, PR_PERFECT, 3000), (-1, PR_PERFECT, 3000),
                                               (3, PR_GOOD, 1500), (-4, PR_GOOD, 1500), (-8, PR_LOW, 0), (5, PR_HIGH, 0)])
def test_scoring_bands(gb, off, result, points):
    enter_pour(gb)
    line = 24
    gb.write("pour_line", line)                         # (the arrows follow; the scoring reads pour_line)
    before = score(gb)
    target = line + off - FOAM_RISE                    # the visible level to let go at
    pour_to(gb, target)
    assert settle(gb) == result
    assert level(gb) == line + off
    assert score(gb) == before + points
    gb.run(4)
    word = {PR_PERFECT: "PERFECT", PR_GOOD: "GOOD", PR_LOW: "TOO LOW", PR_HIGH: "TOO HIGH"}[result]
    assert shows(gb, 3, word)


def test_overflow_spills_and_scores_nothing(gb):
    enter_pour(gb)
    before, breaks = score(gb), sfx(gb, SFX_BREAK)
    gb.hold("a")
    run_until(gb, lambda: gb.mem("pour_result") != PR_NONE, 400)
    gb.release("a")
    assert gb.mem("pour_result") == PR_SPILL and score(gb) == before
    assert sfx(gb, SFX_BREAK) == breaks + 1
    gb.run(4)
    assert shows(gb, 3, "SPILL")
    assert text_row(gb, 3)[12] == B2_BASE + define("B2_BANG", B2H), "SPILL!"
    sp = gb.visible_sprites()
    assert len([s for s in sp if s["tile"] == T_DOME]) == 2, "the foam heaps over the rim"
    heads0 = sorted(s["y"] for s in sp if s["tile"] == T_HEAD)
    gb.run(30)
    heads1 = sorted(s["y"] for s in gb.visible_sprites() if s["tile"] == T_HEAD)
    assert len(heads0) == 2 and heads1[0] > heads0[0], "the spill runs down the outside of the glass"
    assert not [s for s in gb.visible_sprites() if s["tile"] == OBJ_B2 + 22], "no arrows over the spill"


def test_three_glasses_with_different_lines_then_the_end(gb):
    enter_pour(gb)
    lines_seen = []
    total = score(gb)
    for g in range(3):
        run_until(gb, lambda: gb.mem("bonus_phase") == PP_READY, 300)
        assert gb.mem("pour_glass") == g
        gb.run(2)
        assert shows(gb, 2, "GLASS %d" % (g + 1))
        lines_seen.append(gb.mem("pour_line"))
        pour_to(gb, gb.mem("pour_line") - FOAM_RISE)
        assert settle(gb) == PR_PERFECT
        gb.run(2)
        # the line row on the map is this glass's
        k = gb.mem("pour_target")
        assert tilemap_row(gb, GLASS_ROW + B2["line_row"][k], GLASS_COL, 2)[0] == B2_BASE + 10 + 2 * k
    assert len(set(lines_seen)) == 3, lines_seen
    run_until(gb, lambda: gb.mem("bonus_phase") == PH_END, 300)
    gb.run(4)
    assert shows(gb, 3, "BONUS 9000")
    assert score(gb) == total + 9000
    run_until(gb, lambda: state(gb) == PLAYING, 200)


def test_pour_golden(gb):
    enter_pour(gb)
    gb.hold("a")
    gb.run(56)
    check_golden(gb, "bonus_pour")
    gb.release("a")


def test_pour_scanline_limit_for_a_whole_round(gb):
    enter_pour(gb)
    worst = 0
    plan = [lambda: gb.mem("pour_line") - FOAM_RISE, lambda: 40, lambda: 10]   # perfect, spill, low
    g = 0
    for n in range(3000):
        if gb.mem("bonus_phase") == PP_READY and g < 3:
            target = plan[g]()
            g += 1
            gb.hold("a")
            while level(gb) < target and gb.mem("bonus_phase") in (PP_READY, PP_POUR):
                gb.run(1)
                worst = max(worst, max(lines(gb)))
            gb.release("a")
        gb.run(1)
        worst = max(worst, max(lines(gb)))
        assert len(gb.visible_sprites()) <= 40
        if state(gb) == PLAYING:
            break
    assert g == 3 and state(gb) == PLAYING
    assert worst <= 10


# ---- Tip Shower ------------------------------------------------------------------------------------
def enter_tips(gb):
    enter_bonus(gb, 2, rounds_before=2)
    assert gb.mem("bonus_kind") == 2
    run_until(gb, lambda: gb.mem("bonus_phase") == 1, 200)


def clear_items(gb):
    for i in range(TS_ITEMS):
        gb.write(gb.addr("ts_type") + i, 0)
    gb.write("tips_spawn", 250)                          # no new items for a while


def drop(gb, i, kind, x, y):
    gb.write(gb.addr("ts_type") + i, kind)
    gb.write(gb.addr("ts_x") + i, x)
    gb.write(gb.addr("ts_v") + i, 16)                   # 1 px per frame
    y16 = y << 4
    gb.write(gb.addr("ts_y") + 2 * i, y16 & 0xFF)
    gb.write(gb.addr("ts_y") + 2 * i + 1, y16 >> 8)


def tray(gb):
    return gb.mem("tray_x")


def test_tips_banner_then_timer_and_coins(gb):
    enter_bonus(gb, 2, rounds_before=2)
    gb.run(10)
    assert shows(gb, 2, "TIP SHOWER") and shows(gb, 3, "CATCH THE TIPS")
    run_until(gb, lambda: gb.mem("bonus_phase") == 1, 200)
    gb.run(3)
    assert shows(gb, 2, "TIME 20") and shows(gb, 3, "COINS 00")
    gb.run(61)
    assert shows(gb, 2, "TIME 18") or shows(gb, 2, "TIME 19")


def test_tray_moves_left_and_right(gb):
    enter_tips(gb)
    x0 = tray(gb)
    gb.press("right", 20)
    gb.run(1)
    d = tray(gb) - x0
    assert 33 <= d <= 37, d                          # 1.75 px per frame
    gb.press("left", 200)
    assert tray(gb) == 8
    gb.press("right", 200)
    assert tray(gb) == 136
    sp = gb.visible_sprites()
    t = [s for s in sp if s["tile"] in (T_TRAY, T_TRAY + 2, T_TRAY + 4, T_TRAY + 6)]
    assert len(t) == 4 and min(s["x"] - 8 for s in t) == 136 - 8, "the tray at his waist moves with him"


def test_tip_shower_coins_use_sals_palette(gb):
    """Owner Q37: the falling coins wear Sal's OBJ palette 0 (CGB; DMG has 0 anyway); a tomato keeps its red."""
    enter_tips(gb)
    clear_items(gb)
    drop(gb, 0, 1, 40, 60)
    gb.run(2)
    from test_tips import OBJ_COIN
    coins = [s for s in gb.visible_sprites() if abs(s["x"] - 8 - 40) <= 8 and s["tile"] in (OBJ_COIN, OBJ_COIN + 2)]
    assert coins and all(s["flags"] & 7 == 0 for s in coins), [s for s in gb.visible_sprites()]


def test_a_coin_on_the_tray_scores_100(gb):
    enter_tips(gb)
    clear_items(gb)
    before, coins, n = score(gb), gb.mem("tips_caught"), sfx(gb, SFX_COIN)
    drop(gb, 0, 1, tray(gb) + 4, 60)
    run_until(gb, lambda: gb.mem("tips_caught") == coins + 1, 80)
    gb.run(1)                                           # (a test frame can end inside the game's frame logic)
    assert score(gb) == before + 100 and sfx(gb, SFX_COIN) == n + 1
    assert gb.read("ts_type", TS_ITEMS)[0] == 0
    gb.run(3)
    assert shows(gb, 3, "COINS 01")
    # one that misses the tray falls to the floor and is gone
    drop(gb, 1, 1, (tray(gb) + 60) % 140 + 8, 60)
    run_until(gb, lambda: gb.read("ts_type", TS_ITEMS)[1] == 0, 120)
    assert gb.mem("tips_caught") == coins + 1


def test_a_tomato_dirties_the_tray_for_a_second(gb):
    enter_tips(gb)
    clear_items(gb)
    lives = gb.mem("lives")
    drop(gb, 0, 2, tray(gb) + 4, 70)
    run_until(gb, lambda: gb.mem("tray_dirty") > 0, 80)
    assert gb.mem("tray_dirty") in (TRAY_DIRTY, TRAY_DIRTY - 1) and gb.mem("tips_tomatoes") == 1
    gb.run(1)
    assert [s for s in gb.visible_sprites() if s["tile"] == T_TRAY_DIRTY], "the tray shows the splat"
    # a coin landing now is not caught
    coins = gb.mem("tips_caught")
    drop(gb, 1, 1, tray(gb) + 4, TRAY_SURFACE - 8 - 10)
    run_until(gb, lambda: gb.read("ts_type", TS_ITEMS)[1] == 0, 80)
    assert gb.mem("tips_caught") == coins
    assert gb.mem("tray_dirty") > 0
    run_until(gb, lambda: gb.mem("tray_dirty") == 0, TRAY_DIRTY)
    gb.write("tips_spawn", 250)
    drop(gb, 1, 1, tray(gb) + 4, TRAY_SURFACE - 8 - 10)
    run_until(gb, lambda: gb.mem("tips_caught") == coins + 1, 40)
    assert gb.mem("lives") == lives
    assert [s for s in gb.visible_sprites() if s["tile"] == T_TRAY], "clean again"


def test_coins_and_tomatoes_fall_at_varied_x_and_speeds(gb):
    enter_tips(gb)
    xs, vs, kinds = set(), set(), set()
    for _ in range(600):
        gb.run(1)
        t = gb.read("ts_type", TS_ITEMS)
        for i in range(TS_ITEMS):
            if t[i] in (1, 2):
                xs.add(gb.read("ts_x", TS_ITEMS)[i]); vs.add(gb.read("ts_v", TS_ITEMS)[i]); kinds.add(t[i])
    assert kinds == {1, 2}
    assert min(xs) < 40 and max(xs) > 120 and len(vs) >= 6


def test_the_timer_ends_the_round(gb):
    enter_tips(gb)
    clear_items(gb)
    drop(gb, 0, 1, tray(gb) + 4, 80)
    run_until(gb, lambda: gb.mem("tips_caught") == 1, 60)
    gb.run(1)
    before = score(gb)
    gb.write("tips_time", 5); gb.write(gb.addr("tips_time") + 1, 0)
    gb.run(6)
    assert gb.mem("bonus_phase") == PH_END
    gb.run(3)
    assert shows(gb, 2, "TIME UP") and shows(gb, 3, "BONUS 0100")
    assert not [s for s in gb.visible_sprites() if s["tile"] == T_TOMATO]
    run_until(gb, lambda: state(gb) == PLAYING, 200)
    assert score(gb) == before


def test_tips_round_lasts_twenty_seconds(gb):
    enter_tips(gb)
    n = 0
    while gb.mem("bonus_phase") == 1:
        gb.run(1)
        n += 1
    assert abs(n - TIPS_TIME) <= 2


def test_tips_scanline_limit_for_a_whole_round(gb):
    enter_tips(gb)
    worst = 0
    for n in range(TIPS_TIME + 200):
        if n % 90 == 0:
            gb.release("left"); gb.release("right")
            gb.hold("right" if (n // 90) % 2 else "left")
        gb.run(1)
        worst = max(worst, max(lines(gb)))
        if state(gb) == PLAYING:
            break
    gb.release("left"); gb.release("right")
    assert state(gb) == PLAYING
    assert worst <= 10


def test_tips_golden(gb):
    enter_tips(gb)
    gb.press("right", 24)
    gb.run(150)
    check_golden(gb, "bonus_tips")


# ---- back to the bar ----------------------------------------------------------------------------------
@pytest.mark.parametrize("kind", [1, 2])
def test_next_level_loads_with_the_venue_restored(gb, kind):
    enter_bonus(gb, 2, rounds_before=kind)
    run_until(gb, lambda: gb.mem("bonus_phase") == 1, 200)
    gb.run(30)
    finish(gb)
    gb.run(20)
    assert gb.mem("level") == 3 and gb.mem("cur_group") == 2 and state(gb) == PLAYING
    lodge = venue("lodge")
    assert tilemap_row(gb, 7, 0, 20) == lodge["bar_map"][40:60]
    assert tilemap_row(gb, 17, 0, 20) == [lodge["floor_tile"]] * 20
    obj = b"".join(bytes(gb.read(0x8000 + t * 16, 16)) for t in range(96, 128))
    assert obj == bytes(lodge["show"]), "the performer tiles are back"
    first = B2_BASE & ~1                         # M13a: a patron group's tile k is BG id PATRON_FIRST_TILE (78) + k; the glass and '!' lie over ids from B2_BASE
    bg = b"".join(bytes(gb.read((0x9000 + t * 16) if t < 128 else (0x8800 + (t - 128) * 16), 16)) for t in range(first, first + 24))   # (ids 128+: the 0x8800 block)
    assert bg == patron_group_tiles(2)[(first - 78) * 16:(first - 78 + 24) * 16], "the patron tiles are back over the glass and '!'"
    if gb.model_name == "dmg":
        assert gb.mem(0xFF49) == 0xE4, "OBP1 is the game's again (M13a: 0xE4 in play, for lifted patrons)"


# ---- D5b: the tray at waist height (owner 2026-10-15) -----------------------------------------------------------------------------
OAM_ITEMS, OAM_TRAY, OAM_BT_TIPS = (define(n) for n in ("OAM_ITEMS", "OAM_TRAY", "OAM_BT_TIPS"))
BT_OAM_Y = 112 + 16                                      # (a parenthesised define: his OAM y)
SHOTS = ROOT / "out" / "tips"


def raw_oam(gb, i):
    a = 0xFE00 + 4 * i
    return dict(y=gb.mem(a), x=gb.mem(a + 1), tile=gb.mem(a + 2), flags=gb.mem(a + 3))


def tips_shot(gb, name):
    SHOTS.mkdir(parents=True, exist_ok=True)
    gb.screenshot(SHOTS / f"{name}.{gb.model_name}.png", 3)


def test_the_tray_is_held_at_waist_height(gb):
    """The tray's four entries sit over his body rows 8-23 (belt height, 4 px above D5b: the tray's top surface, art row 5, is his row 13),
    on the same x as his two entries and with lower OAM indexes (so it is in front of him on DMG too, where the smaller x
    wins and a tie goes to the lower index); he is drawn behind the falling items. The hitbox surface is the drawn tray top."""
    enter_tips(gb)
    clear_items(gb)
    for x_keys in ("right", "left"):                     # facing right, then facing left
        gb.press(x_keys, 10)
        gb.run(2)
        t = [raw_oam(gb, OAM_TRAY + k) for k in range(4)]
        b = [raw_oam(gb, OAM_BT_TIPS + k) for k in range(4)]
        assert [e["tile"] for e in t] == [T_TRAY + 2 * k for k in range(4)]
        assert all(e["y"] == BT_OAM_Y + 8 and e["x"] == tray(gb) + 8 * k for k, e in enumerate(t))
        assert {e["y"] for e in b} == {BT_OAM_Y, BT_OAM_Y + 16}
        body_x = sorted({e["x"] for e in b})
        assert body_x == [tray(gb) + 8, tray(gb) + 16], "his two columns are the tray's middle two"
        assert OAM_ITEMS + TS_ITEMS <= OAM_TRAY and OAM_TRAY + 4 <= OAM_BT_TIPS, "items, then the tray, then him"
        assert t[0]["y"] - 16 + 5 == TRAY_SURFACE and t[0]["y"] - 16 >= BT_OAM_Y - 16 + 8, "surface = art row 5, at his waist"
        assert BT_OAM_Y - 16 + 13 == TRAY_SURFACE


def test_the_waist_tray_catches_what_the_overhead_one_did(gb):
    """The catch box is unchanged horizontally (a coin whose x is tray_x-8 .. tray_x+16 is caught, one pixel further out falls
    past) and a coin is caught the frame its bottom reaches the drawn tray top (it falls 24 px further than before)."""
    enter_tips(gb)
    clear_items(gb)
    for dx, caught in ((-8, True), (-9, False), (16, True), (17, False), (4, True)):
        clear_items(gb)
        gb.run(1)
        x = tray(gb) + dx
        before = gb.mem("tips_caught")
        drop(gb, 0, 1, x, 60)
        seen = None
        for _ in range(120):
            gb.run(1)
            if gb.read("ts_type", TS_ITEMS)[0] == 0:
                break
            y = (gb.read("ts_y", 2 * TS_ITEMS)[0] | gb.read("ts_y", 2 * TS_ITEMS)[1] << 8) >> 4
            seen = y
        gb.run(1)
        assert (gb.mem("tips_caught") == before + 1) == caught, dx
        if caught:
            assert TRAY_SURFACE - 8 - 2 <= seen <= TRAY_SURFACE - 8, "its bottom reached the tray's top"


def test_tips_screenshots_and_a_whole_round_keeps_to_10_sprites_a_line(gb):
    """x3 pictures of the waist tray (clean, with a coin about to land, dirty); the busiest line of a whole round with items
    falling all the time (tray 4 + him 2 + items) stays within 10."""
    enter_tips(gb)
    gb.press("right", 20)
    gb.run(4)
    tips_shot(gb, "tips_waist_clean")
    clear_items(gb)
    drop(gb, 0, 1, tray(gb) + 4, TRAY_SURFACE - 8 - 30)
    gb.run(14)
    tips_shot(gb, "tips_waist_coin")
    drop(gb, 1, 2, tray(gb) + 4, 70)
    run_until(gb, lambda: gb.mem("tray_dirty") > 0, 80)
    gb.run(3)
    tips_shot(gb, "tips_waist_dirty")
    worst = 0
    gb.write("tips_spawn", 1)
    for n in range(500):
        if n % 70 == 0:
            gb.release("left"); gb.release("right")
            gb.hold("left" if (n // 70) % 2 else "right")
        gb.run(1)
        worst = max(worst, max(lines(gb)))
    gb.release("left"); gb.release("right")
    assert worst <= 10, worst
