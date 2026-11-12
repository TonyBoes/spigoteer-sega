# The Practice screen's illustrations (BONUS > MINI GAMES; src/mg_list.c "THE ILLUSTRATION", tools/gen_practice_art.py, assets/art/practice/README.md), built and
# tested against PLACEHOLDERS: tests/data/practice_art/*.png (numbered cards, one picture of 56 unique tiles, one of 80; `shakeup` has none on purpose). They are
# test-only: the default build reads assets/art/practice alone, and this file builds a ROM of its own from the placeholder directory (make PRACTICE_ART_DIRS=...,
# into out/b_pa), so the real art, when it comes, never changes these tests and the placeholders never ship.
#
# What is pinned: each picture appears in the frame after the selection, pixel for pixel, on DMG (BGP shades by index) and CGB (its palette's colours); no frame ever
# shows a half-loaded picture (every row of the 10 x 8 tile frame is the old picture's, the new one's, or, for a game with none, the empty frame's: a 2-3 frame wipe at
# most); a game without a picture shows the empty frame; stepping back and a steady walk swap from the spare buffer without a stream; fast LEFT / RIGHT never runs
# a frame late; the generator refuses what does not fit.
import json
import subprocess
import sys

import pytest
from PIL import Image
from gbtools import Rom

from conftest import locked_make, K_BONUS, K_MINIGAMES, ROM, ROOT, hold_stage_anim, title_pick
from test_flow import run_until, state, tilemap_row
from test_mg import GS_MGLIST
from test_menu_scroll import LATE, mash

DATA = ROOT / "tests" / "data" / "practice_art"
GAMES = ["quickdraw", "shirtcannon", "logroll", "orderup", "marshmallows", "batterysort", "milkrun", "taikopour", "monkeybusiness", "asteroids", "shakeup",
         "perfectpour", "tipshower"]
NONE = GAMES.index("shakeup")                    # the one without a file
BOX = (8, 48, 88, 112)                           # the frame on screen: columns 1-10, rows 6-13
OL_T_BOX, BLANK = 17, 54                         # the empty frame's top-left border tile and the blank inside (src/oneline.h, build/art.h)
DMG_SHADES = [(255, 255, 255), (153, 153, 153), (85, 85, 85), (0, 0, 0)]    # BGP 0xE4 through PyBoy's grey ramp, by colour index


@pytest.fixture(scope="module")
def art_rom():
    """The ROM built from the placeholder pictures (make rebuilds only what changed)."""
    r = locked_make(["BUILD=out/b_pa", "OUT=out/o_pa", "PRACTICE_ART_DIRS=tests/data/practice_art", "out/b_pa/game.gb"], "b_pa")
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    return ROOT / "out" / "b_pa" / "game.gb"


@pytest.fixture(params=["dmg", "cgb"])
def model(request):
    return request.param


@pytest.fixture
def gb(art_rom, model):
    with Rom(art_rom, model) as g:
        g.run(120)
        g.model_name = model
        hold_stage_anim(g)
        title_pick(g, K_BONUS, K_MINIGAMES)
        run_until(g, lambda: state(g) == GS_MGLIST and g.pb.memory[0xFF40] & 0x80, 30)
        g.run(8)
        yield g


def rgb(v):
    return ((v & 31) << 3, (v >> 5 & 31) << 3, (v >> 10 & 31) << 3)


def expected(model, game):
    """The 80 x 64 picture as the screen shows it: the PNG's indices through the DMG shades or the picture's own CGB palette."""
    png = Image.open(DATA / f"{game}.png")
    pal = json.loads((ROOT / "out" / "b_pa" / "practice_art.json").read_text())["pictures"][game]["pal"]
    cols = DMG_SHADES if model == "dmg" else [rgb(v) for v in pal]
    im = Image.new("RGB", (80, 64))
    im.putdata([cols[png.getpixel((x, y))] for y in range(64) for x in range(80)])
    return im


def shot(gb):
    return gb.image().crop(BOX)


def rows(im):
    return [im.crop((0, 8 * r, 80, 8 * r + 8)).tobytes() for r in range(8)]


def empty_frame(gb):
    """The tilemap check of the empty frame: the border's eight tile kinds, a blank inside."""
    want = [[OL_T_BOX, OL_T_BOX + 1] + [OL_T_BOX + 1] * 6 + [OL_T_BOX + 1, OL_T_BOX + 2]]
    for _ in range(6):
        want.append([OL_T_BOX + 3] + [BLANK] * 8 + [OL_T_BOX + 4])
    want.append([OL_T_BOX + 5] + [OL_T_BOX + 6] * 8 + [OL_T_BOX + 7])
    return [tilemap_row(gb, 6 + r, 1, 10) for r in range(8)] == want


def tap(gb, key, settle=60):
    gb.press(key, 2)
    gb.run(settle)


def goto(gb, n, settle=60):
    """Step RIGHT to list line n (from line 0)."""
    for _ in range(n):
        tap(gb, "right", settle)


def frames_to(gb, game, limit=60, render=True):
    """Frames from now until the frame shows `game`'s picture whole (a pixel-exact match); None past `limit`."""
    want = expected(gb.model_name, game).tobytes()
    for f in range(limit):
        if shot(gb).tobytes() == want:
            return f
        gb.run(1, render)
    return None


def test_the_first_picture_is_there_on_entering(gb):
    assert shot(gb).tobytes() == expected(gb.model_name, "quickdraw").tobytes()


def test_each_picture_appears_after_the_selection_pixel_exact(gb):
    for n, game in enumerate(GAMES):
        if n:
            tap(gb, "right")
        if game == "shakeup":
            assert empty_frame(gb), "no picture: the empty frame"
        else:
            assert shot(gb).tobytes() == expected(gb.model_name, game).tobytes(), game
            assert not empty_frame(gb)


def test_going_left_shows_the_same_pictures(gb):
    tap(gb, "left")                              # (the debug list's last line, the stub: no picture)
    assert empty_frame(gb)
    for game in reversed(GAMES):
        tap(gb, "left")
        if game == "shakeup":
            assert empty_frame(gb)
        else:
            assert shot(gb).tobytes() == expected(gb.model_name, game).tobytes(), game


def test_a_game_without_a_picture_shows_the_empty_frame_and_the_next_one_replaces_it(gb):
    goto(gb, NONE)
    assert empty_frame(gb)
    tap(gb, "right")
    assert shot(gb).tobytes() == expected(gb.model_name, "perfectpour").tobytes()
    assert not empty_frame(gb)


def reference_rows(gb, game):
    """The eight tile rows of a game's picture as the screen shows it; for a game with no picture, the empty frame as the screen shows it (taken from a settled screen)."""
    if game != "shakeup":
        return rows(expected(gb.model_name, game))
    old = gb.mem("ml_sel")
    gb.write("ml_sel", NONE)
    gb.run(150)
    out = rows(shot(gb))
    gb.write("ml_sel", old)
    gb.run(150)
    return out


def test_no_frame_shows_a_half_loaded_picture(gb):
    """Every frame after a press, each of the eight tile rows of the frame is the old picture's or the new one's (the switch is a wipe of whole rows, 2-3 frames), whatever
    is streaming behind it; and the new picture does complete. The 80-tile picture streams longest; the empty frame is a picture on either side too."""
    for a, b in [("quickdraw", "shirtcannon"), ("asteroids", "shakeup"), ("shakeup", "perfectpour"), ("perfectpour", "tipshower"), ("tipshower", "quickdraw")]:
        gb.write("ml_sel", GAMES.index(a))
        gb.run(150)                              # (settled on a)
        old = reference_rows(gb, a)
        new = reference_rows(gb, b)
        gb.write("ml_sel", GAMES.index(a))
        gb.run(150)
        assert rows(shot(gb)) == old, a
        gb.write("ml_sel", GAMES.index(b))       # (cold: nothing was prefetched for b)
        flips = {}
        for f in range(60):
            gb.run(1, True)
            cur = rows(shot(gb))
            for r, row in enumerate(cur):
                assert row == old[r] or row == new[r], (a, b, f, r, "a row that is neither picture's")
                if row == new[r] and old[r] != new[r]:
                    flips.setdefault(r, f)       # (the frame this row switched; a row that stays the same in both pictures says nothing)
        assert rows(shot(gb)) == new, (a, b, "the new picture never completed")
        if flips:
            assert max(flips.values()) - min(flips.values()) <= 2, (a, b, "the switch is a wipe of at most 3 frames", flips)


def test_frames_to_load_a_56_and_an_80_tile_picture(gb, request):
    """The stream: 5 tiles a frame, then a wipe (3 frames on a Color, 2 on a DMG). A poke of the selection starts it cold (no prefetch went that way)."""
    out = {}
    for game, limit in [("perfectpour", 24), ("tipshower", 28)]:
        gb.write("ml_sel", GAMES.index(game))
        n = frames_to(gb, game, limit)
        assert n is not None, f"{game} not on screen within {limit} frames"
        out[game] = n
        gb.write("ml_sel", 0)
        gb.run(60)
    print(f"{gb.model_name}: 56 tiles shown after {out['perfectpour']} frames, 80 tiles after {out['tipshower']}")
    assert out["tipshower"] > out["perfectpour"]


def test_stepping_back_after_a_pause(gb):
    """A Color holds four pictures and prefetches both neighbours: stepping back is a wipe alone. A DMG holds two and has prefetched the way it walks: the step back
    streams the picture again."""
    tap(gb, "right", 90)
    gb.press("left", 2)
    n = frames_to(gb, "quickdraw", 30)
    assert n is not None
    if gb.model_name == "cgb":
        assert n <= 6, n


def test_a_steady_walk_finds_the_next_picture_prefetched(gb):
    tap(gb, "right", 90)                         # (idle: the neighbour in the walking direction, logroll, streams into a spare buffer)
    gb.press("right", 2)
    n = frames_to(gb, "logroll", 12)
    assert n is not None and n <= 6, n
    for game in ("orderup", "marshmallows"):     # (and on: a pause per step is enough)
        gb.run(90)
        gb.press("right", 2)
        n = frames_to(gb, game, 12)
        assert n is not None and n <= 6, (game, n)


@pytest.mark.only_model("cgb")
def test_a_color_walks_both_ways_without_a_stream(gb):
    for _ in range(3):
        tap(gb, "right", 100)
    for game in ("logroll", "shirtcannon", "quickdraw"):    # (back through the pictures the walk left in the buffers or prefetched)
        gb.run(100)
        gb.press("left", 2)
        n = frames_to(gb, game, 12)
        assert n is not None and n <= 6, (game, n)


def test_fast_left_right_never_runs_a_frame_late_and_settles(gb):
    for key in ("right", "left"):
        for period in (2, 3, 4):
            late0 = gb.mem16("vq_late")
            worst, late = mash(gb, key, period, seconds=4)
            assert late == 0 and worst <= LATE, (key, period, worst)
            assert gb.mem16("vq_late") == late0, "a VBlank drain was refused (too late in VBlank)"
    gb.run(120)
    sel = gb.mem("ml_sel")
    game = GAMES[sel] if sel < len(GAMES) else None
    if game is None or game == "shakeup":
        assert empty_frame(gb)
    else:
        assert shot(gb).tobytes() == expected(gb.model_name, game).tobytes(), game


def test_cgb_palette_slots_hold_the_pictures_palettes(art_rom):
    from test_venues import cgb_palette
    with Rom(art_rom, "cgb") as g:
        g.run(120)
        g.model_name = "cgb"
        hold_stage_anim(g)
        title_pick(g, K_BONUS, K_MINIGAMES)
        run_until(g, lambda: state(g) == GS_MGLIST and g.pb.memory[0xFF40] & 0x80, 30)
        g.run(100)
        pics = json.loads((ROOT / "out" / "b_pa" / "practice_art.json").read_text())["pictures"]
        assert cgb_palette(g, 0) == pics["quickdraw"]["pal"], "the first picture's palette is slot 0"
        g.press("right", 2)
        g.run(60)
        assert cgb_palette(g, 1) == pics["shirtcannon"]["pal"], "the next one goes into slot 1"
        assert cgb_palette(g, 0) == pics["quickdraw"]["pal"]
        g.press("right", 2)
        g.run(60)
        assert cgb_palette(g, 0) == pics["logroll"]["pal"], "then back to slot 0"


def test_the_default_build_ships_no_placeholder_and_shows_the_empty_frame():
    assert "PRACTICE_ART_DIRS ?= assets/art/practice\n" in (ROOT / "Makefile").read_text()
    with Rom(ROM, "cgb") as g:
        g.run(120)
        g.model_name = "cgb"
        hold_stage_anim(g)
        title_pick(g, K_BONUS, K_MINIGAMES)
        run_until(g, lambda: state(g) == GS_MGLIST and g.pb.memory[0xFF40] & 0x80, 30)
        g.run(8)
        if not list((ROOT / "assets" / "art" / "practice").glob("*.png")):
            assert empty_frame(g)


# ---- the generator ----
def gen(tmp_path, *extra, files=()):
    d = tmp_path / "in"
    d.mkdir(exist_ok=True)
    for f in files:
        (d / f.name).write_bytes(f.read_bytes())
    return subprocess.run([sys.executable, str(ROOT / "tools" / "gen_practice_art.py"), str(tmp_path / "b"), str(tmp_path / "p"), "--dirs", str(d), *extra], capture_output=True, text=True)


def test_the_generator_rejects_a_picture_with_too_many_tiles(tmp_path):
    """tipshower.png has 80 unique tiles; with the cap at 79 (the hard cap is 80: a 10 x 8 picture cannot have more) it fails and names the file and the count."""
    r = gen(tmp_path, "--max-tiles", "79", files=[DATA / "tipshower.png"])
    assert r.returncode != 0
    assert "tipshower.png" in r.stderr and "80 unique 8x8 tiles" in r.stderr and "at most 79" in r.stderr, r.stderr
    r = gen(tmp_path, files=[DATA / "tipshower.png"])
    assert r.returncode == 0, r.stderr


def test_the_generator_rejects_a_wrong_size_a_wrong_mode_and_too_many_colours(tmp_path):
    p = tmp_path / "in"
    p.mkdir()
    big = Image.new("P", (96, 64), 0)
    big.save(p / "quickdraw.png")
    assert "96 x 64" in gen(tmp_path).stderr
    rgbim = Image.new("RGB", (80, 64), (1, 2, 3))
    rgbim.save(p / "quickdraw.png")
    assert "indexed" in gen(tmp_path).stderr
    five = Image.new("P", (80, 64), 0)
    five.putpalette([0, 0, 0] * 8)
    five.putpixel((3, 3), 5)
    five.save(p / "quickdraw.png")
    r = gen(tmp_path)
    assert r.returncode != 0 and "index 5" in r.stderr


def test_a_missing_picture_is_allowed_and_has_no_table_entry(tmp_path):
    r = gen(tmp_path, files=[DATA / "logroll.png"])
    assert r.returncode == 0, r.stderr
    h = (tmp_path / "b" / "practice_art.h").read_text()
    assert "pa_logroll" in h and "pa_quickdraw" not in h
    assert "{ 0, 0, pa_logroll," in h


def test_the_first_directory_wins(tmp_path):
    """The real art (assets/art/practice) is listed before any placeholder directory and overrides it per game."""
    a, b = tmp_path / "a", tmp_path / "b2"
    a.mkdir(); b.mkdir()
    Image.open(DATA / "quickdraw.png").save(a / "quickdraw.png")
    Image.open(DATA / "shirtcannon.png").save(b / "quickdraw.png")
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "gen_practice_art.py"), str(tmp_path / "o"), str(tmp_path / "p"), "--dirs", str(a), str(b)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    j = json.loads((tmp_path / "o" / "practice_art.json").read_text())
    assert j["pictures"]["quickdraw"]["file"] == str(a / "quickdraw.png")
