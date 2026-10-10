# M10b arcade mode: the top-5 table with initials in SRAM (save.c), endless loops of the nine venues with a
# "LOOP n" banner and harder loops (main.c), the initials entry and the table screen (scores.c).
import pytest
from conftest import GAME, ROM, check_golden
from gbtools import Rom
from test_flow import GAME_OVER, LIFE_LOST, PLAYING, TITLE, hi_score, hi_shown, hi_tiles, lose_a_life, run_until, state
from test_sound import make_rom, save_ram, start_game

pytestmark = pytest.mark.timeout(120)

TOP_N = 5
V2_SUM = 34
V3_SUM = 36          # M11b: version 3 = version 2's table + the story progress (34) + a reserved byte, checksum at 36
V4_SUM = 36          # story shifts: version 4 = version 3 with the step reached at 35 (was reserved)


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


def parse_save(ram):
    """The table of a version-4 save (the game writes nothing else since the story shifts); checks the checksum."""
    assert ram[:4] == b"TPR4"
    c = (0x5A + sum(ram[:V4_SUM])) & 255
    assert ram[V4_SUM] == c and ram[V4_SUM + 1] == c ^ 0xFF, "checksum"
    return [(ram[4 + i * 6:7 + i * 6].decode(), int.from_bytes(ram[7 + i * 6:10 + i * 6], "little")) for i in range(TOP_N)]


def table(rom):
    """The WRAM working copy: [(initials, score)]."""
    names = bytes(rom.read("top_names", TOP_N * 3)).decode()
    raw = rom.read("top_scores", TOP_N * 4)
    return [(names[i * 3:i * 3 + 3], int.from_bytes(raw[i * 4:i * 4 + 4], "little")) for i in range(TOP_N)]


def booted(model, ram=None):
    rom = make_rom(model, ram, sound=False)
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


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_score_goes_in_at_its_rank_and_pushes_the_rest_down(model):
    ram = v2_image([("ABC", 500), ("DEF", 400), ("GHI", 300), ("JKL", 200), ("MNO", 100)])
    with booted(model, ram) as rom:
        assert table(rom)[0] == ("ABC", 500) and hi_score(rom) == 500
        game_over_with(rom, 350)
        assert rom.mem("new_rank") == 2
        want = [("ABC", 500), ("DEF", 400), ("AAA", 350), ("GHI", 300), ("JKL", 200)]
        assert table(rom) == want
        assert parse_save(save_ram(rom)) == want, "saved at game over, before the initials"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_ties_go_below_and_low_scores_stay_out(model):
    ram = v2_image([("ABC", 500), ("DEF", 400), ("GHI", 300), ("JKL", 200), ("MNO", 100)])
    for v, rank in ((300, 3), (100, 5), (50, 5), (900, 0)):
        with booted(model, ram) as rom:
            game_over_with(rom, v)
            assert rom.mem("new_rank") == rank, v
            t = table(rom)
            if rank < TOP_N:
                assert t[rank] == ("AAA", v) and [s for _, s in t] == sorted([s for _, s in t], reverse=True)
                assert hi_score(rom) == t[0][1]
            else:
                assert t == [("ABC", 500), ("DEF", 400), ("GHI", 300), ("JKL", 200), ("MNO", 100)]
                want = v4_image([("ABC", 500), ("DEF", 400), ("GHI", 300), ("JKL", 200), ("MNO", 100)])
                assert save_ram(rom)[:V4_SUM + 2] == want[:V4_SUM + 2], "SRAM untouched (since the boot's migration)"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_table_survives_a_reset(model):
    ram = v2_image([("ABC", 500), ("DEF", 400)])
    with booted(model, ram) as rom:
        game_over_with(rom, 450)
        saved = save_ram(rom)
    assert parse_save(saved)[:3] == [("ABC", 500), ("AAA", 450), ("DEF", 400)]
    with booted(model, saved) as again:
        assert table(again)[:3] == [("ABC", 500), ("AAA", 450), ("DEF", 400)]
        assert hi_score(again) == 500 and hi_shown(again) == hi_tiles("000500")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_an_old_save_migrates_to_entry_one_as_spg(model):
    with booted(model, v1_image(12340)) as rom:
        assert rom.mem("save_migrated") == 1
        assert table(rom) == [("SPG", 12340)] + [("   ", 0)] * 4
        assert hi_score(rom) == 12340 and hi_shown(rom) == hi_tiles("012340"), "the title's HI is the top score"
        ram = save_ram(rom)
    assert parse_save(ram) == [("SPG", 12340)] + [("   ", 0)] * 4, "written back as version 4 at once"
    with booted(model, ram) as again:
        assert again.mem("save_migrated") == 0 and table(again)[0] == ("SPG", 12340)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_broken_save_loads_as_an_empty_table(model):
    good = v2_image([("ABC", 500), ("DEF", 400)])
    cases = {
        "bad v1 checksum": bytes(bytearray(v1_image(100))[:8]) + b"\0\0" + bytes(0x2000 - 10),
        "v1 out of range": v1_image(1_000_000),
        "bad letter": v2_image([("A1C", 500)]),
        "out of order": v2_image([("ABC", 400), ("DEF", 500)]),
        "out of range": v2_image([("ABC", 1_000_000)]),
        "bad checksum": good[:V2_SUM] + bytes([good[V2_SUM] ^ 1]) + good[V2_SUM + 1:],
        "unknown version": b"TPR9" + good[4:],
    }
    for name, ram in cases.items():
        with booted(model, ram) as rom:
            assert table(rom) == [("   ", 0)] * TOP_N, name
            assert hi_score(rom) == 0 and rom.mem("save_migrated") == 0, name


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


def test_after_level_9_the_venues_come_round_again_with_a_loop_banner(gb):
    from test_flow import LAYOUT, patrons, tile_id, tilemap_row
    assert gb.mem("arcade_loop") == 1
    to_level(gb, 10)
    assert state(gb) == GS_LOOP and gb.mem("overlay_on") == 1
    assert gb.mem("cur_group") == 0 and gb.mem("venue_id") == 0 and gb.mem("arcade_loop") == 2
    gb.run(3)
    assert window_text(gb) == "LOOP 2"
    assert gb.regs()["WY"] == 64
    assert tilemap_row(gb, LAYOUT["HUD_ROW"], 17, 3) == [tile_id("GLYPH_L"), tile_id("GLYPH_1"), tile_id("GLYPH_0")], "L10"
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
    to_level(gb, 11)
    assert state(gb) == PLAYING and gb.mem("overlay_on") == 0 and gb.mem("cur_group") == 1 and gb.mem("arcade_loop") == 2


def test_loop_3_starts_at_level_19(gb):
    to_level(gb, 19)
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
        for lvl in (1, 9, 10, 18, 19, 27, 28, 36, 37, 45, 46, 54):
            if lvl > 1:
                to_level(gb, lvl)
            row, k = TABLE[(lvl - 1) % 9], min((lvl - 1) // 9, 3)
            speed, spawn, gap = gb.mem("patron_speed"), gb.mem16("spawn_interval"), gb.mem("empty_gap")
            b = base_speed(row[5])
            assert speed == b + b * 10 * k // 100, lvl                 # +10 % per loop, capped at +30 %
            assert spawn == row[4] - row[4] * 8 * k // 100, lvl          # -8 % per loop, capped at -24 %
            assert gap == max(80, row[8] - 5 * k) and gap >= 80, lvl     # -5 frames per loop, floor 80
            seen[lvl] = (speed, spawn, gap)
        assert seen[10][0] > base_speed(TABLE[0][5]) and seen[19][0] > seen[10][0] and seen[28][0] > seen[19][0]
        assert seen[37] == seen[28] and seen[46] == seen[28], "the ceiling: loop 4 on plays like loop 4"
        assert seen[36] == seen[45] == seen[54] and seen[54][2] == 80
        assert seen[28][0] <= base_speed(TABLE[0][5]) * 13 // 10


# ---- (c) the initials entry and the table screen ----------------------------------------------------------
GS_INITIALS, GS_SCORES = 9, 10
ROW_HEAD, ROW_FIRST, ROW_SCORE, ROW_ENTER, ROW_INITIALS, ROW_CURSOR, INI_COL = 3, 6, 5, 8, 11, 12, 8


def glyphs():
    from test_flow import tile_id
    g = {tile_id("GLYPH_" + c): c for c in "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"}
    g[tile_id("HUD_BLANK")] = " "
    g[tile_id("HUD_CURSOR")] = "^"
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
    assert "TILE_HUD_CURSOR " in ART_H


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_entering_initials_then_the_table(model):
    with booted(model, v2_image([("ABC", 500), ("DEF", 400), ("GHI", 300)])) as gb:
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
        assert screen_text(gb, ROW_HEAD).strip() == "HIGH SCORES"
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
    assert screen_text(boot, ROW_HEAD).strip() == "HIGH SCORES"
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
    assert screen_text(boot, ROW_HEAD).strip() == "HIGH SCORES"
    assert screen_text(boot, ROW_FIRST) == "    1     000000    "
    assert len(boot.visible_sprites()) == 0, "no title sprites on the table"
    run_until(boot, lambda: state(boot) == TITLE, 320)
    boot.run(5)
    assert boot.mem("title_sel") == 0
    boot.press("start", 2)
    run_until(boot, lambda: state(boot) == PLAYING, 30)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_title_hi_line_is_the_top_score_and_the_table_shows_the_save(model):
    with booted(model, v2_image([("ZED", 98765), ("QUA", 4321)])) as gb:
        assert hi_shown(gb) == hi_tiles("098765")
        idle_title(gb)
        run_until(gb, lambda: state(gb) == GS_SCORES, 30)
        gb.run(2)
        assert screen_text(gb, ROW_FIRST) == "    1 ZED 098765    "
        assert screen_text(gb, ROW_FIRST + 2) == "    2 QUA 004321    "
