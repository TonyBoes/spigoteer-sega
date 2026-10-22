# M10b arcade mode: the top-5 table with initials in SRAM (save.c), endless loops of the ten venues with a
# "LOOP n" banner and harder loops (main.c), the initials entry and the table screen (scores.c).
import pytest
from conftest import GAME, ROM, check_golden, title_level
from gbtools import Rom
from test_flow import GAME_OVER, LIFE_LOST, PLAYING, TITLE, hi_score, hi_shown, hi_tiles, lose_a_life, run_until, state
from test_sound import make_rom, save_ram, start_game

pytestmark = pytest.mark.timeout(120)

TOP_N = 5
V2_SUM = 34
V3_SUM = 36          # M11b: version 3 = version 2's table + the story progress (34) + a reserved byte, checksum at 36
V4_SUM = 36          # story shifts: version 4 = version 3 with the step reached at 35 (was reserved)
V5_SUM = 38          # bonus menu: version 5 = version 4's bytes + the unlocked tunes at 36-37 (LE), checksum at 38
V6_SUM = 38          # the 10th venue: version 6 = version 5's bytes, the chapters (0..10) and tunes in the new order
TUNE_COUNT = 15      # music.h (title, clear, over, bonus, show, ten venue tunes)
TUNE_TITLE, TUNE_CLEAR, TUNE_OVER, TUNE_BONUS, TUNE_SHOW, TUNE_VENUE0 = range(6)
JINGLES = (1 << TUNE_CLEAR) | (1 << TUNE_OVER) | (1 << TUNE_BONUS) | (1 << TUNE_SHOW)


# ---- SRAM images --------------------------------------------------------------------------------
def v2_image(entries, size=0x2000):
    """A version-2 save: entries = [(initials, score)] best first, padded with blank entries."""
    r = bytearray(size)
    r[0:4] = b"TPR2"
    entries = list(entries) + [("   ", 0)] * (TOP_N - len(entries))
    for i, (n, s) in enumerate(entries):
        r[4 + i * 6:7 + i * 6] = n.encode()
        r[7 + i * 6:10 + i * 6] = s.to_bytes(3, "little")
    c = (0x5A + sum(r[:V2_SUM])) & 255
    r[V2_SUM], r[V2_SUM + 1] = c, c ^ 0xFF
    return bytes(r)


def v1_image(score, size=0x2000):
    """The M7 save: "TPR1", the hi score (4 bytes LE), checksum, complement."""
    r = bytearray(size)
    r[0:4] = b"TPR1"
    r[4:8] = score.to_bytes(4, "little")
    c = (0x5A + sum(r[:8])) & 255
    r[8], r[9] = c, c ^ 0xFF
    return bytes(r)


def v3_image(entries, story=0, size=0x2000):
    """A version-3 save (M11b): the version-2 table, the story progress (chapters cleared), a reserved 0, checksum."""
    r = bytearray(v2_image(entries, size))
    r[0:4] = b"TPR3"
    r[V2_SUM], r[V2_SUM + 1] = story, 0
    c = (0x5A + sum(r[:V3_SUM])) & 255
    r[V3_SUM], r[V3_SUM + 1] = c, c ^ 0xFF
    return bytes(r)


def v4_image(entries, story=0, step=0, size=0x2000):
    """A version-4 save (story shifts): the version-3 bytes, 35 the step reached in chapter `story`."""
    r = bytearray(v3_image(entries, story, size))
    r[0:4] = b"TPR4"
    r[V2_SUM + 1] = step
    c = (0x5A + sum(r[:V4_SUM])) & 255
    r[V4_SUM], r[V4_SUM + 1] = c, c ^ 0xFF
    return bytes(r)


def v5_image(entries, story=0, step=0, tunes=1, size=0x2000):
    """A version-5 save (bonus menu): the version-4 bytes, 36-37 the unlocked tunes (bit t = tune t), checksum at 38."""
    r = bytearray(v4_image(entries, story, step, size))
    r[0:4] = b"TPR5"
    r[V4_SUM:V4_SUM + 2] = tunes.to_bytes(2, "little")
    c = (0x5A + sum(r[:V5_SUM])) & 255
    r[V5_SUM], r[V5_SUM + 1] = c, c ^ 0xFF
    return bytes(r)


def v6_image(entries, story=0, step=0, tunes=1, size=0x2000):
    """A version-6 save (the 10th venue, today's): version 5's bytes with "TPR6", chapters 0..10 in the new order."""
    r = bytearray(v5_image(entries, story, step, tunes, size))
    r[0:4] = b"TPR6"
    c = (0x5A + sum(r[:V6_SUM])) & 255
    r[V6_SUM], r[V6_SUM + 1] = c, c ^ 0xFF
    return bytes(r)


def old_progress(story, step):
    """save.c old_progress: a version 3-5 save's progress (nine chapters, the old order) today: p <= 5 kept with its
    step, p >= 6 (the old 6 factory, 7 teahouse, 8 space, 9 zoo) is 6 with step 0 (The Chrome Cow not cleared)."""
    return (story, step) if story < 6 else (6, 0)


def old_tunes(m):
    """save.c old_tunes: a version-5 save's unlocks in the new tune order (old venues 6 teahouse, 7 space, 8 zoo are
    7, 9, 8 now; bits 14-15 dropped)."""
    t = m & ((1 << (TUNE_VENUE0 + 6)) - 1)
    for old, new in ((6, 7), (7, 9), (8, 8)):
        if m & 1 << (TUNE_VENUE0 + old):
            t |= 1 << (TUNE_VENUE0 + new)
    return t


def progress_unlocks(story, step):
    """save.c progress_unlocks: the tunes an old save's progress implies."""
    m = 1 << TUNE_TITLE
    n = story + 1 if step and story < 10 else story
    for c in range(n):
        m |= 1 << (TUNE_VENUE0 + c)
    return m | (JINGLES if story else 0)


# ---- version 7 (the three modes): the main block at 0 ("TPR7", progress, step, tunes, checksum, complement) and one
# top 5 per mode in its own block (src/save.c)
MODE_ARCADE, MODE_STORY, MODE_CLASSIC = range(3)
V7_SUM = 8
TBL_AT = (0x80, 0xC0, 0x100)
TBL_MAGIC = (b"HSA1", b"HSS1", b"HSC2")   # P5: CLASSIC's block is version 2 (test_classic_mode.py)
TBL_SUM = 4 + TOP_N * 6


def tbl_block(entries, t):
    """Table t's SRAM block (36 bytes): magic, 5 entries best first (padded), checksum, complement."""
    r = bytearray(TBL_SUM + 2)
    r[0:4] = TBL_MAGIC[t]
    entries = list(entries) + [("   ", 0)] * (TOP_N - len(entries))
    for i, (n, sc) in enumerate(entries):
        r[4 + i * 6:7 + i * 6] = n.encode()
        r[7 + i * 6:10 + i * 6] = sc.to_bytes(3, "little")
    c = (0x5A + sum(r[:TBL_SUM])) & 255
    r[TBL_SUM], r[TBL_SUM + 1] = c, c ^ 0xFF
    return bytes(r)


def v7_image(arcade=(), story=0, step=0, tunes=1, story_tbl=(), classic=(), size=0x2000):
    """A version-7 save (today's): the main block and the three tables."""
    r = bytearray(size)
    r[0:4] = b"TPR7"
    r[4], r[5] = story, step
    r[6:8] = tunes.to_bytes(2, "little")
    c = (0x5A + sum(r[:V7_SUM])) & 255
    r[V7_SUM], r[V7_SUM + 1] = c, c ^ 0xFF
    for t, e in enumerate((arcade, story_tbl, classic)):
        r[TBL_AT[t]:TBL_AT[t] + TBL_SUM + 2] = tbl_block(e, t)
    return bytes(r)


def main_block(ram):
    """A version-7 save's main block, checked: (progress, step, tunes)."""
    assert ram[:4] == b"TPR7"
    c = (0x5A + sum(ram[:V7_SUM])) & 255
    assert ram[V7_SUM] == c and ram[V7_SUM + 1] == c ^ 0xFF, "checksum"
    return ram[4], ram[5], int.from_bytes(ram[6:8], "little")


def saved_tunes(ram):
    return main_block(ram)[2]


def saved_story(ram):
    return main_block(ram)[:2]


def parse_save(ram, t=MODE_ARCADE):
    """Table t of a version-7 save (the main block and the table's block checked)."""
    main_block(ram)
    b = ram[TBL_AT[t]:TBL_AT[t] + TBL_SUM + 2]
    assert b[:4] == TBL_MAGIC[t]
    c = (0x5A + sum(b[:TBL_SUM])) & 255
    assert b[TBL_SUM] == c and b[TBL_SUM + 1] == c ^ 0xFF, "table checksum"
    return [(b[4 + i * 6:7 + i * 6].decode(), int.from_bytes(b[7 + i * 6:10 + i * 6], "little")) for i in range(TOP_N)]


def table(rom, t=MODE_ARCADE):
    """The WRAM working copy of table t: [(initials, score)]."""
    names = bytes(rom.read("top_names", 3 * TOP_N * 3)).decode()[t * TOP_N * 3:]
    raw = rom.read("top_scores", 3 * TOP_N * 4)[t * TOP_N * 4:]
    return [(names[i * 3:i * 3 + 3], int.from_bytes(raw[i * 4:i * 4 + 4], "little")) for i in range(TOP_N)]


def booted(model, ram=None, cards=True):
    rom = make_rom(model, ram, sound=False, cards=cards)
    rom.run(120)
    return rom


def set_score(rom, v):
    """Poke the running score (the HUD digits are not touched: the table and its screens read `score`)."""
    a = rom.addr("score")
    for i in range(4):
        rom.write(a + i, (v >> (8 * i)) & 255)


def game_over_with(rom, v):
    """From the title: start a game, give it score v, lose all three lives, stop at GAME OVER."""
    start_game(rom)
    set_score(rom, v)
    for n in range(3):
        lose_a_life(rom)
        if n < 2:
            run_until(rom, lambda: state(rom) == PLAYING, 200)
    run_until(rom, lambda: state(rom) == GAME_OVER, 200)


# ---- (a) the table in SRAM -----------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_fresh_cartridge_has_an_empty_table(model):
    with booted(model) as rom:
        assert table(rom) == [("   ", 0)] * TOP_N
        assert hi_score(rom) == 0 and rom.mem("save_migrated") == 0


FIVE = [("ABC", 500), ("DEF", 400), ("GHI", 300), ("JKL", 200), ("MNO", 100)]
EMPTY = [("   ", 0)] * TOP_N


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_score_goes_in_at_its_rank_and_pushes_the_rest_down(model):
    ram = v7_image(FIVE)
    with booted(model, ram) as rom:
        assert table(rom)[0] == ("ABC", 500) and hi_score(rom) == 500
        game_over_with(rom, 350)
        assert rom.mem("new_rank") == 2 and rom.mem("score_tbl") == MODE_ARCADE
        want = [("ABC", 500), ("DEF", 400), ("AAA", 350), ("GHI", 300), ("JKL", 200)]
        assert table(rom) == want
        assert table(rom, MODE_STORY) == EMPTY and table(rom, MODE_CLASSIC) == EMPTY, "the other tables untouched"
        assert parse_save(save_ram(rom)) == want, "saved at game over, before the initials"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_ties_go_below_and_low_scores_stay_out(model):
    ram = v7_image(FIVE)
    for v, rank in ((300, 3), (100, 5), (50, 5), (900, 0)):
        with booted(model, ram, cards=False) as rom:      # (the image as it is: the bonus block with the cards seen is not in it)
            game_over_with(rom, v)
            assert rom.mem("new_rank") == rank, v
            t = table(rom)
            if rank < TOP_N:
                assert t[rank] == ("AAA", v) and [s for _, s in t] == sorted([s for _, s in t], reverse=True)
                assert hi_score(rom) == t[0][1]
            else:
                assert t == FIVE
                assert save_ram(rom)[:0x140] == ram[:0x140], "SRAM untouched"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_table_survives_a_reset(model):
    ram = v7_image([("ABC", 500), ("DEF", 400)], story_tbl=[("STO", 9000)], classic=[("CLA", 70)])
    with booted(model, ram) as rom:
        game_over_with(rom, 450)
        saved = save_ram(rom)
    assert parse_save(saved)[:3] == [("ABC", 500), ("AAA", 450), ("DEF", 400)]
    assert parse_save(saved, MODE_STORY)[0] == ("STO", 9000) and parse_save(saved, MODE_CLASSIC)[0] == ("CLA", 70)
    with booted(model, saved) as again:
        assert table(again)[:3] == [("ABC", 500), ("AAA", 450), ("DEF", 400)]
        assert table(again, MODE_STORY)[0] == ("STO", 9000) and table(again, MODE_CLASSIC)[0] == ("CLA", 70)
        assert hi_score(again) == 500 and hi_shown(again) == hi_tiles("000500")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_version_6_save_keeps_its_story_and_starts_the_tables_fresh(model):
    """Q4 (owner 2026-10-11): the old arcade's top 5 is dropped; the story progress and the unlocks are kept, written
    back as version 7 at once (the main block and three empty tables)."""
    tunes = 1 | 1 << 5 | 1 << 6 | 0x1E
    want = tunes | progress_unlocks(3, 2)                # (plus what the progress implies, as every migration)
    with booted(model, v6_image(FIVE, story=3, step=2, tunes=tunes)) as rom:
        assert rom.mem("save_migrated") == 6
        assert table(rom) == EMPTY and table(rom, MODE_STORY) == EMPTY and table(rom, MODE_CLASSIC) == EMPTY
        assert hi_score(rom) == 0 and hi_shown(rom) == hi_tiles("000000")
        assert (rom.mem("story_progress"), rom.mem("story_reached"), rom.mem16("tune_unlocked")) == (3, 2, want)
        ram = save_ram(rom)
    assert main_block(ram) == (3, 2, want)
    assert all(parse_save(ram, t) == EMPTY for t in range(3)), "three empty tables, each with its own checksum"
    with booted(model, ram) as again:
        assert again.mem("save_migrated") == 0 and again.mem("story_progress") == 3


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_version_1_or_2_save_is_a_fresh_cartridge(model):
    for ram in (v1_image(12340), v2_image(FIVE)):
        with booted(model, ram) as rom:
            assert rom.mem("save_migrated") == 0 and table(rom) == EMPTY and hi_score(rom) == 0
            assert rom.mem("story_progress") == 0


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_bad_block_empties_only_its_own_table(model):
    good = v7_image(FIVE, story=4, step=1, story_tbl=[("STO", 900)], classic=[("CLA", 80)])

    def edit(t, k, v):
        r = bytearray(good)
        r[TBL_AT[t] + k] = v
        return bytes(r)
    cases = {
        "bad letter": (edit(MODE_ARCADE, 5, ord("1")), MODE_ARCADE),
        "out of order": (bytes(good[:TBL_AT[0]]) + tbl_block([("ABC", 400), ("DEF", 500)], 0) + good[TBL_AT[0] + 36:], MODE_ARCADE),
        "out of range": (bytes(good[:TBL_AT[1]]) + tbl_block([("ABC", 1_000_000)], 1) + good[TBL_AT[1] + 36:], MODE_STORY),
        "bad checksum": (edit(MODE_CLASSIC, TBL_SUM, good[TBL_AT[2] + TBL_SUM] ^ 1), MODE_CLASSIC),
        "wrong magic": (edit(MODE_STORY, 2, ord("A")), MODE_STORY),
    }
    full = {MODE_ARCADE: FIVE, MODE_STORY: [("STO", 900)] + EMPTY[1:], MODE_CLASSIC: [("CLA", 80)] + EMPTY[1:]}
    for name, (ram, bad) in cases.items():
        with booted(model, ram) as rom:
            for t in range(3):
                assert table(rom, t) == (EMPTY if t == bad else full[t]), (name, t)
            assert rom.mem("story_progress") == 4 and rom.mem("save_migrated") == 0, name
    r = bytearray(good)
    r[V7_SUM] ^= 1                                      # a bad main block: no story, the tables kept
    with booted(model, bytes(r)) as rom:
        assert rom.mem("story_progress") == 0 and table(rom) == FIVE and table(rom, MODE_STORY)[0] == ("STO", 900)
    with booted(model, b"TPR9" + good[4:]) as rom:     # an unknown version: nothing
        assert table(rom) == EMPTY and hi_score(rom) == 0 and rom.mem("save_migrated") == 0


# ---- (b) endless loops ------------------------------------------------------------------------------------
GS_LOOP = 8
LEVEL_CLEAR, BONUS = 3, 6


def to_level(gb, lvl):
    """Clear the current level as if it were lvl - 1, so that lvl comes next (through the bonus round if any)."""
    run_until(gb, lambda: state(gb) == PLAYING, 130)          # (past a LOOP banner)
    gb.write("level", lvl - 1)
    gb.write("level_clear", 1)
    run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 5)
    run_until(gb, lambda: state(gb) in (PLAYING, BONUS, GS_LOOP), 200)
    if state(gb) == BONUS:
        gb.write("bonus_phase", 4)
        gb.write("bonus_timer", 129)
        run_until(gb, lambda: state(gb) in (PLAYING, GS_LOOP), 40)
    assert gb.mem("level") == lvl


def window_text(gb):
    from test_flow import tile_id
    names = {tile_id("GLYPH_" + c): c for c in "0123456789LOP"}
    names[tile_id("HUD_BLANK")] = " "
    return "".join(names.get(t & 0xFF, "?") for t in gb.bg_tilemap(True)[1][:20]).strip()


def test_after_level_10_the_venues_come_round_again_with_a_loop_banner(gb):
    from test_flow import LAYOUT, patrons, tile_id, tilemap_row
    assert gb.mem("arcade_loop") == 1
    to_level(gb, 11)
    assert state(gb) == GS_LOOP and gb.mem("overlay_on") == 1
    assert gb.mem("cur_group") == 0 and gb.mem("venue_id") == 0 and gb.mem("arcade_loop") == 2
    gb.run(3)
    assert window_text(gb) == "LOOP 2"
    assert gb.regs()["WY"] == 64
    assert tilemap_row(gb, LAYOUT["HUD_ROW"], 17, 3) == [tile_id("HUD_FLAG"), tile_id("GLYPH_1"), tile_id("GLYPH_1")], "flag 11"
    check_golden(gb, "loop_banner")
    # nothing moves under the banner; the level's own intro follows it
    start = patrons(gb)
    intro = gb.mem("intro_timer")
    gb.press("left", 20)
    assert patrons(gb) == start and gb.mem("intro_timer") == intro and gb.mem("bartender_x") == GAME["TAP_X"]
    run_until(gb, lambda: state(gb) == PLAYING, 130)
    assert gb.mem("overlay_on") == 0 and gb.mem("intro_timer") == intro
    gb.run(3)
    assert gb.mem("intro_timer") < intro


def test_levels_inside_a_loop_have_no_banner(gb):
    to_level(gb, 12)
    assert state(gb) == PLAYING and gb.mem("overlay_on") == 0 and gb.mem("cur_group") == 1 and gb.mem("arcade_loop") == 2


def test_loop_3_starts_at_level_21(gb):
    to_level(gb, 21)
    assert state(gb) == GS_LOOP and gb.mem("arcade_loop") == 3 and gb.mem("cur_group") == 0
    gb.run(3)
    assert window_text(gb) == "LOOP 3"


def base_speed(step):
    return ((2048 // step) * (GAME["PATRON_FAR_X"] - GAME["ENTRY_X"]) + GAME["PATRON_FAR_X"] // 2) // GAME["PATRON_FAR_X"]


@pytest.mark.parametrize("model", ["dmg"])
def test_each_loop_is_harder_up_to_a_ceiling(model):
    from test_flow import TABLE
    with Rom(ROM, model) as gb:
        gb.model_name = model
        gb.run(120)
        start_game(gb)
        seen = {}
        for lvl in (1, 10, 11, 20, 21, 30, 31, 40, 41, 50, 51, 60):
            if lvl > 1:
                to_level(gb, lvl)
            row, k = TABLE[(lvl - 1) % 10], min((lvl - 1) // 10, 3)
            speed, spawn, gap = gb.mem("patron_speed"), gb.mem16("spawn_interval"), gb.mem("empty_gap")
            b = base_speed(row[5])
            assert speed == b + b * 10 * k // 100, lvl                 # +10 % per loop, capped at +30 %
            assert spawn == row[4] - row[4] * 8 * k // 100, lvl          # -8 % per loop, capped at -24 %
            assert gap == max(80, row[8] - 5 * k) and gap >= 80, lvl     # -5 frames per loop, floor 80
            seen[lvl] = (speed, spawn, gap)
        assert seen[11][0] > base_speed(TABLE[0][5]) and seen[21][0] > seen[11][0] and seen[31][0] > seen[21][0]
        assert seen[41] == seen[31] and seen[51] == seen[31], "the ceiling: loop 4 on plays like loop 4"
        assert seen[40] == seen[50] == seen[60] and seen[60][2] == 80
        assert seen[31][0] <= base_speed(TABLE[0][5]) * 13 // 10


# ---- (c) the initials entry and the table screen ----------------------------------------------------------
GS_INITIALS, GS_SCORES = 9, 10
ROW_HEAD, ROW_FIRST, ROW_SCORE, ROW_ENTER, ROW_INITIALS, ROW_CURSOR, INI_COL = 3, 6, 5, 8, 11, 12, 8


def glyphs():
    from test_flow import tile_id
    g = {tile_id("GLYPH_" + c): c for c in "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"}
    g[tile_id("HUD_BLANK")] = " "
    g[77] = "^"   # HUD_CURSOR_BG (src/game.h): scores.c loads the cursor there
    g[tile_id("PANEL_TOP")] = "="
    g[tile_id("PANEL_BOT")] = "_"
    return g


def screen_text(gb, y):
    g = glyphs()
    return "".join(g.get(t & 0xFF, "?") for t in gb.bg_tilemap()[y][:20])


def tap(gb, button):
    gb.press(button, 2)
    gb.run(2)


def to_initials(gb, v):
    """A game over with score v that makes the top 5, through to the initials screen."""
    game_over_with(gb, v)
    tap(gb, "start")
    run_until(gb, lambda: state(gb) == GS_INITIALS, 30)
    gb.run(2)


def idle_title(gb):
    """Pretend the title has had no key for 20 s: the table comes next."""
    a = gb.addr("title_idle")
    gb.write(a, 1199 & 255)
    gb.write(a + 1, 1199 >> 8)


def test_the_new_letters_are_in_the_hud_style():
    from test_flow import ART_H
    for c in "JQXZ":
        assert f"TILE_GLYPH_{c} " in ART_H
    assert "TILE_HUD_FLAG " in ART_H and "TILE_HUD_CURSOR " not in ART_H


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_entering_initials_then_the_table(model):
    with booted(model, v7_image([("ABC", 500), ("DEF", 400), ("GHI", 300)])) as gb:
        to_initials(gb, 450)
        assert screen_text(gb, ROW_HEAD).strip() == "NEW HIGH SCORE"
        assert screen_text(gb, ROW_SCORE).strip() == "000450"
        assert screen_text(gb, ROW_ENTER).strip() == "ENTER INITIALS"
        assert screen_text(gb, 1) == "=" * 20 and screen_text(gb, 16) == "_" * 20
        assert screen_text(gb, ROW_INITIALS) == " " * INI_COL + "A A A" + " " * 7
        assert screen_text(gb, ROW_CURSOR).index("^") == INI_COL
        # Up / Down step through A..Z and a space, wrapping both ways; Left / Right move (wrapping)
        tap(gb, "down")
        assert bytes(gb.read("ini_name", 3)) == b" AA", "below A: the space"
        tap(gb, "down")
        assert bytes(gb.read("ini_name", 3)) == b"ZAA"
        for _ in range(2):
            tap(gb, "up")
        assert bytes(gb.read("ini_name", 3)) == b"AAA", "Z: up to the space, then A"
        tap(gb, "left")
        assert gb.mem("ini_pos") == 2
        for _ in range(16):                     # A + 16 = Q
            tap(gb, "up")
        tap(gb, "right")
        assert gb.mem("ini_pos") == 0
        for _ in range(9):                      # A + 9 = J
            tap(gb, "up")
        tap(gb, "right")
        for _ in range(4):                      # space, Z, Y, X
            tap(gb, "down")
        assert bytes(gb.read("ini_name", 3)) == b"JXQ"
        assert screen_text(gb, ROW_INITIALS) == " " * INI_COL + "J X Q" + " " * 7
        assert screen_text(gb, ROW_CURSOR).index("^") == INI_COL + 2
        assert state(gb) == GS_INITIALS
        check_golden(gb, "initials")
        tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_SCORES, 30)
        gb.run(2)
        assert table(gb)[:4] == [("ABC", 500), ("JXQ", 450), ("DEF", 400), ("GHI", 300)]
        assert screen_text(gb, ROW_HEAD).strip() == "ARCADE HIGH SCORES"
        assert [screen_text(gb, ROW_FIRST + 2 * i) for i in range(5)] == [
            "    1 ABC 000500    ", "    2 JXQ 000450    ", "    3 DEF 000400    ", "    4 GHI 000300    ",
            "    5     000000    "]
        check_golden(gb, "scores")
        saved = save_ram(gb)
    assert parse_save(saved)[:2] == [("ABC", 500), ("JXQ", 450)], "the initials are saved"
    with booted(model, saved) as again:
        assert table(again)[1] == ("JXQ", 450)


def test_the_initials_screen_waits_for_a(boot):
    to_initials(boot, 50)
    boot.run(600)
    assert state(boot) == GS_INITIALS
    tap(boot, "start")                          # START saves too
    run_until(boot, lambda: state(boot) == GS_SCORES, 30)
    assert table(boot)[0] == ("AAA", 50)


def test_no_entry_shows_the_table_briefly_then_the_title(boot):
    before = table(boot)
    game_over_with(boot, 0)
    run_until(boot, lambda: state(boot) == GS_SCORES, 260)      # by itself after the GAME OVER banner
    assert table(boot) == before
    boot.run(2)
    assert screen_text(boot, ROW_HEAD).strip() == "ARCADE HIGH SCORES"
    run_until(boot, lambda: state(boot) == TITLE, 320)          # and the title after 5 s


def test_a_b_or_start_leave_the_table(boot):
    for b in ("a", "b", "start"):
        idle_title(boot)
        run_until(boot, lambda: state(boot) == GS_SCORES, 30)
        boot.run(5)
        tap(boot, b)
        run_until(boot, lambda: state(boot) == TITLE, 30)
        boot.run(5)


def test_an_idle_title_shows_the_table_and_comes_back(boot):
    boot.run(600)
    tap(boot, "down")                           # a key starts the 20 s over
    boot.run(1100)
    assert state(boot) == TITLE
    run_until(boot, lambda: state(boot) == GS_SCORES, 120)
    boot.run(3)
    assert screen_text(boot, ROW_HEAD).strip() == "ARCADE HIGH SCORES"
    assert screen_text(boot, ROW_FIRST) == "    1     000000    "
    assert len(boot.visible_sprites()) == 0, "no title sprites on the table"
    run_until(boot, lambda: state(boot) == TITLE, 320)
    boot.run(5)
    assert boot.mem("title_sel") == 0 and boot.mem("title_menu") == 0, "the top level, on PLAY"
    title_level(boot)
    run_until(boot, lambda: state(boot) == PLAYING, 30)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_idle_title_cycles_the_three_tables(model):
    ram = v7_image([("ARC", 300)], story_tbl=[("STO", 200)], classic=[("CLA", 100)])
    with booted(model, ram) as gb:
        for head, first in (("ARCADE HIGH SCORES", "    1 ARC 000300    "), ("STORY HIGH SCORES", "    1 STO 000200    "),
                            ("CLASSIC HIGH SCORES", "    1 CLA 000100    "), ("ARCADE HIGH SCORES", "    1 ARC 000300    ")):
            idle_title(gb)
            run_until(gb, lambda: state(gb) == GS_SCORES, 30)
            gb.run(2)
            assert screen_text(gb, ROW_HEAD).strip() == head and screen_text(gb, ROW_FIRST) == first
            tap(gb, "b")
            run_until(gb, lambda: state(gb) == TITLE, 30)
            gb.run(3)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_hi_line_shows_the_table_of_the_mode_under_play_s_cursor(model):
    from conftest import K_ARCADE, K_CLASSIC, K_CONTINUE, K_PLAY, K_STORY, menu_items, menu_tap, title_pick
    ram = v7_image([("ARC", 300)], story=2, story_tbl=[("STO", 2000)], classic=[("CLA", 10)])
    with booted(model, ram) as gb:
        gb.run(5)
        assert hi_shown(gb) == hi_tiles("000300"), "the top level: ARCADE's"
        title_pick(gb, K_PLAY)
        want = {K_CONTINUE: "002000", K_STORY: "002000", K_ARCADE: "000300", K_CLASSIC: "000010"}
        assert menu_items(gb) == [K_CONTINUE, K_STORY, K_ARCADE, K_CLASSIC]
        for k in menu_items(gb):
            gb.run(8)
            assert hi_shown(gb) == hi_tiles(want[k]), k
            menu_tap(gb, "down")
        menu_tap(gb, "up")                                # (on CLASSIC) B: the top level again, ARCADE's
        menu_tap(gb, "b")
        gb.run(8)
        assert hi_shown(gb) == hi_tiles("000300")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_title_hi_line_is_the_top_score_and_the_table_shows_the_save(model):
    with booted(model, v7_image([("ZED", 98765), ("QUA", 4321)])) as gb:
        assert hi_shown(gb) == hi_tiles("098765")
        idle_title(gb)
        run_until(gb, lambda: state(gb) == GS_SCORES, 30)
        gb.run(2)
        assert screen_text(gb, ROW_FIRST) == "    1 ZED 098765    "
        assert screen_text(gb, ROW_FIRST + 2) == "    2 QUA 004321    "


# ---- the attract (owner 2026-10-22): the title's idle high scores keep the music going and never come from a submenu ----------------------------------
GS_SCORES = 10


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_title_music_keeps_playing_through_the_attract_high_scores(model):
    import numpy as np
    rom = make_rom(model, None, sound=True)
    try:
        rom.run(300)
        idle_title(rom)
        snd, silent, run, seen_scores = rom.pb.sound, 0, 0, False
        t0 = rom.mem("cur_tune")
        for i in range(700):                        # (the table shows, then the title comes back)
            rom.run(1)
            a = np.array(snd.ndarray[:snd.raw_buffer_head // 2], dtype=float)
            run = run + 1 if len(a) and not np.abs(a).max() else 0
            silent = max(silent, run)
            seen_scores |= state(rom) == GS_SCORES
            assert rom.mem("cur_tune") == t0 == TUNE_TITLE, "the title tune stays the tune"
        assert seen_scores and state(rom) == TITLE, "the table came and went"
        assert silent < 30, f"{silent} silent frames in a row: the music stopped"
    finally:
        rom.stop()


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("top", ["PLAY", "BONUS", "SETTINGS"])
def test_no_high_scores_from_a_submenu(model, top):
    from conftest import K_BONUS, K_PLAY, K_SETTINGS, MENU_SETTLE, hold_stage_anim, title_pick
    rom = make_rom(model, None, sound=False)
    try:
        rom.run(120)
        hold_stage_anim(rom)
        title_pick(rom, {"PLAY": K_PLAY, "BONUS": K_BONUS, "SETTINGS": K_SETTINGS}[top])
        rom.run(MENU_SETTLE)
        menu = rom.mem("title_menu")
        assert menu != 0
        rom.run(1500)                               # (past the 1200-frame idle)
        assert state(rom) == TITLE and rom.mem("title_menu") == menu, "still the submenu: no table"
    finally:
        rom.stop()


def test_no_high_scores_from_the_gba_prompt():
    from conftest import TM_SCR, gba_hardware, hold_stage_anim
    with gba_hardware(True):
        rom = make_rom("cgb", None, sound=False)
    try:
        rom.run(120)
        hold_stage_anim(rom)
        assert rom.mem("title_menu") == TM_SCR
        rom.run(1500)
        assert state(rom) == TITLE and rom.mem("title_menu") == TM_SCR
    finally:
        rom.stop()


def test_a_submenu_restarts_the_attract_clock():
    from conftest import K_PLAY, MENU_SETTLE, hold_stage_anim, title_pick
    rom = make_rom("cgb", None, sound=False)
    try:
        rom.run(120)
        hold_stage_anim(rom)
        a = rom.addr("title_idle")
        rom.write(a, 1100 & 255)
        rom.write(a + 1, 1100 >> 8)
        title_pick(rom, K_PLAY)
        rom.run(MENU_SETTLE)
        assert rom.mem16("title_idle") < 100, "entering a menu starts the clock over"
    finally:
        rom.stop()
