"""The HUD row (owner-approved redesign, 2026-10-14): score at columns 0-5, the Spigoteer's head + the lives digit at 7-8, a story
goal's icon + 2 digits at 11-13 (a mug with a check; an empty mug with an arrow for a catch goal), the level's flag + 2 digits
at 17-19 (a timed shift's hourglass + seconds over them), a boss's face 12 + meter 13-19 (a drunk pint is a dark outline)."""
import re

import pytest
from conftest import K_ARCADE, K_BONUS, K_CLASSIC, K_PLAY, K_SOUNDTRACK, MENU_SETTLE, ROOT, hold_stage_anim, menu_to, title_pick
from test_flow import PLAYING, run_until, state, tilemap_row, tile_id
from test_scores import booted
import boss_common as bc
import test_story as ts

CH = {".": 0, "-": 1, "+": 2, "#": 3}
GAME_H = (ROOT / "src" / "game.h").read_text()
GOAL_BG = int(re.search(r"#define HUD_GOAL_BG\s+(\d+)", GAME_H).group(1))
HOURGLASS_BG = int(re.search(r"#define HUD_HOURGLASS_BG\s+(\d+)", GAME_H).group(1))
CURSOR_BG = int(re.search(r"#define HUD_CURSOR_BG\s+(\d+)", GAME_H).group(1))
GLYPH0 = tile_id("GLYPH_0")
HEAD, FLAG, BLANK = tile_id("HUD_HEAD"), tile_id("HUD_FLAG"), tile_id("HUD_BLANK")


def art_bytes(path, name):
    """The 16 bytes of tile `name` ('@name' block, 8 rows of . - + #) of an art file, as the converters make them."""
    rows, cur = [], None
    for line in (ROOT / path).read_text().splitlines():
        if line.startswith("@"):
            cur = line[1:].strip()
        elif cur == name and line.strip() and not line.startswith(";"):
            rows.append(line.strip())
    assert len(rows) == 8, (path, name)
    out = []
    for r in rows:
        lo = hi = 0
        for x, c in enumerate(r):
            lo |= (CH[c] & 1) << (7 - x)
            hi |= (CH[c] >> 1) << (7 - x)
        out += [lo, hi]
    return out


def vram_tile(gb, t):
    """BG tile id t (signed mode: 0..127 at 0x9000, 128..255 at 0x8800)."""
    return list(gb.read((0x9000 if t < 128 else 0x8000) + t * 16, 16))


def digits(gb, col, n):
    return [t - GLYPH0 for t in tilemap_row(gb, 0, col, n)]


def check_row(gb, lives=3, level=1):
    assert tilemap_row(gb, 0, 6, 1) == [BLANK], "column 6 is blank"
    assert tilemap_row(gb, 0, 7, 2) == [HEAD, GLYPH0 + lives], "the head and the lives digit"
    assert tilemap_row(gb, 0, 17, 3) == [FLAG, GLYPH0 + level // 10, GLYPH0 + level % 10], "the flag and the level"


def test_the_new_tiles_are_the_approved_art():
    from test_flow import ART_H
    assert "TILE_HUD_MUG " not in ART_H and "TILE_HUD_CURSOR " not in ART_H
    assert len(art_bytes("assets/tiles/bar.txt", "hud_head")) == 16 and len(art_bytes("assets/tiles/bar.txt", "hud_flag")) == 16
    # the head's moustache is one unbroken 4-pixel run with face on both sides (row 4: '#......#' -> hair/face), eyes two dark dots
    head = [r for r in (ROOT / "assets/tiles/bar.txt").read_text().split("@hud_head")[1].split("@")[0].splitlines() if r.startswith(("#", "-", "."))][:8]
    assert head[3] == "#.#..#.#" and head[5] == "#.####.#"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_meter_outline_replaces_the_u(model):
    """The boss meter's EMPTY and HALF tiles: a drunk pint is the sand outline of the full one (top and bottom rows, side
    columns; the band inside)."""
    import json
    m = json.loads((ROOT / "build" / "boss.json").read_text())["meter"]
    empty, half, full = m[0:16], m[16:32], m[32:48]
    assert empty == art_bytes("assets/art/boss/meter.txt", "EMPTY") and half == art_bytes("assets/art/boss/meter.txt", "HALF")

    def px(t, y):
        return "".join(str(((t[2 * y] >> (7 - x)) & 1) | (((t[2 * y + 1] >> (7 - x)) & 1) << 1)) for x in range(8))
    assert [px(empty, y) for y in range(8)] == ["33333333", "31113111", "31313131", "31313131", "31313131", "31313131", "31113111", "33333333"]
    assert px(half, 1) == "30003111" and px(half, 6) == "32223111"
    assert px(full, 1) == "30003000"


@pytest.mark.only_model('dmg')
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_arcade_and_classic_show_head_digit_flag_and_level(model):
    for key in (K_ARCADE, K_CLASSIC):
        with booted(model) as gb:
            hold_stage_anim(gb)
            title_pick(gb, K_PLAY, key)
            run_until(gb, lambda: state(gb) == PLAYING, 400)
            gb.run(20)
            check_row(gb, 3, gb.mem("level"))
            assert vram_tile(gb, FLAG) == art_bytes("assets/tiles/bar.txt", "hud_flag"), "the flag is a generic tile"
            assert vram_tile(gb, HEAD) == art_bytes("assets/tiles/bar.txt", "hud_head")
            assert digits(gb, 0, 6) == [0] * 6, "the score from column 0"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_serve_goal_shows_the_mug_check_and_a_catch_goal_the_empty_mug(model):
    with ts.to_shift(model, 0, 0) as gb:            # a serve goal, no timer: icon + 08 at 11-13, the flag + level 01 at 17-19
        gb.run(2)
        assert tilemap_row(gb, 0, 11, 3) == [GOAL_BG, GLYPH0, GLYPH0 + 8]
        assert vram_tile(gb, GOAL_BG) == art_bytes("assets/art/hud_icons.txt", "mugcheck")
        check_row(gb, 3, 1)
        assert tilemap_row(gb, 0, 14, 3) == [BLANK] * 3
    with ts.to_shift(model, 5, 0) as gb:            # the factory's RECYCLE 12: a catch goal
        gb.run(2)
        assert tilemap_row(gb, 0, 11, 3) == [GOAL_BG, GLYPH0 + 1, GLYPH0 + 2]
        assert vram_tile(gb, GOAL_BG) == art_bytes("assets/art/hud_icons.txt", "catch")
        check_row(gb, 3, 6)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_timed_shift_puts_the_hourglass_over_the_flag(model):
    with ts.to_shift(model, 3, 0) as gb:
        gb.run(2)
        assert tilemap_row(gb, 0, 7, 2) == [HEAD, GLYPH0 + 3]
        assert tilemap_row(gb, 0, 11, 3)[0] == GOAL_BG
        assert tilemap_row(gb, 0, 16, 4)[:2] == [BLANK, HOURGLASS_BG]
        assert FLAG not in tilemap_row(gb, 0, 0, 20)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_boss_fight_keeps_its_face_and_meter_and_the_head(model):
    with bc.fight(model, 0) as gb:
        gb.run(2)
        row = tilemap_row(gb, 0, 0, 20)
        assert row[7:9] == [HEAD, GLYPH0 + 3] and row[12] == bc.HUD_BG, "the head, the lives; the face at 12"
        assert FLAG not in row and GOAL_BG not in row[9:12]


@pytest.mark.only_model('dmg')
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_lost_life_changes_the_digit(model):
    from test_flow import lose_a_life
    with booted(model) as gb:
        hold_stage_anim(gb)
        title_pick(gb, K_PLAY, K_CLASSIC)
        run_until(gb, lambda: state(gb) == PLAYING, 400)
        gb.run(10)
        lose_a_life(gb)
        run_until(gb, lambda: state(gb) == PLAYING, 200)
        gb.run(3)
        assert tilemap_row(gb, 0, 7, 2) == [HEAD, GLYPH0 + 2]


@pytest.mark.only_model('dmg')
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_every_mini_game_shows_the_lives_as_head_and_digit(model):
    import test_mg as tm
    for gid in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9):   # mg.h: every saved mini-game (the finale shows its own, po.c)
        with booted(model) as gb:
            hold_stage_anim(gb)
            gb.model_name = model
            tm.mg_enter(gb, gid, tm.MG_STORY)
            gb.run(10)
            assert tilemap_row(gb, 0, 7, 2) == [HEAD, GLYPH0 + 3], gid
            assert tilemap_row(gb, 0, 0, 6) == [GLYPH0] * 6, "the score from column 0"
