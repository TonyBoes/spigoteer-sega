# Story pictures (INTRO before / INTRO explosion, FINALE, CREDITS): the full-screen pictures of the picture scenes
# (assets/story/pictures/*.txt -> build/story_pictures.c by tools/gen_story.py), the INTRO's picture switch behind a white
# flash (src/story.c pic_fx), and the picture scenes' one portrait slot that each speaker's tiles stream into
# (SW_TILES). Pixel checks compare the screen with the approved source, exact on DMG (each key's shade) and on CGB (each
# key's RGB15 colour).
import numpy as np
import pytest
from PIL import Image
from conftest import ROOT, check_golden
from test_flow import GS_STORY, run_until, state, tilemap_row
from test_story import (DMG_GREY, PORTRAITS, SC, SCENES, STORY, STORY_STEPS, gen_story, page_ready, post, q15, settle,
                        skip_scene, start_story, to_goal, v7_image, win)

pytestmark = pytest.mark.timeout(240)

PICS = {p["name"]: p for p in STORY["pictures"]}
SLOT_BASE = STORY["portrait_base"]
FRAME = (8, 40, 80, 104)               # a speaker page's portrait frame: columns 1-9, rows 5-12 (x0, y0, x1, y1)
_EXPECT = {}


def expected(name, model):
    """The picture as the screen must show it: 160x104 RGB."""
    if (name, model) not in _EXPECT:
        key, pix, _ = gen_story().parse_v2(ROOT / PICS[name]["art"])
        im = Image.new("RGB", (160, 104))
        for y, row in enumerate(pix):
            for x, c in enumerate(row):
                im.putpixel((x, y), q15(key[c]["hex"]) if model == "cgb" else DMG_GREY[key[c]["dmg"]])
        _EXPECT[name, model] = np.array(im)
    return _EXPECT[name, model]


def picture_diff(gb, name, skip=None):
    """Pixels of the picture area (rows 0-12) that differ from the source; `skip` = a rectangle to leave out."""
    got = np.array(gb.image())[:104, :160]
    bad = np.any(got != expected(name, gb.model_name), axis=2)
    if skip:
        x0, y0, x1, y1 = skip
        bad[y0:y1, x0:x1] = False
    return int(bad.sum())


def assert_picture(gb, name, skip=None):
    n = picture_diff(gb, name, skip)
    assert n == 0, f"{n} pixels of the screen differ from {name}"
    p = PICS[name]
    for r in range(13):                                           # the tile map is the picture's too
        row = tilemap_row(gb, r, 0, 20)
        want = p["map"][r * 20:(r + 1) * 20]
        if skip and r * 8 >= skip[1]:
            lo, hi = skip[0] // 8, skip[2] // 8
            row, want = row[:lo] + row[hi:], want[:lo] + want[hi:]
        assert row == want, f"{name}: tile map row {r}"


# ---- the build -----------------------------------------------------------------------------------------------
def test_the_pictures_are_built_to_the_budget():
    assert list(PICS) == ["intro_before", "intro_a", "finale_a", "credits_b"]
    by_scene = {s["id"]: s for s in SCENES}
    assert [(by_scene[i]["pic"], by_scene[i]["swpage"]) for i in ("INTRO", "FINALE", "CREDITS")] == [(0, 5), (2, 0), (3, 0)]
    for name, p in PICS.items():
        sc = by_scene[p["scene"]]
        slot = sc["bg_tiles"]
        assert p["base"] == SLOT_BASE + slot, name
        assert len(p["pals"]) <= 4 and len(p["map"]) == len(p["attr"]) == 260
        ids = set(p["map"])
        assert len(ids) == p["tiles"] and ids <= set(range(36)) | set(range(p["base"], 256)), f"{name}: tile ids"
        assert all(a in (0, 5, 6, 7, 1) for a in p["attr"]) and p["hud_cells"] == p["attr"].count(1), name
        assert p["tiles"] <= 36 + 256 - p["base"], name
    # the numbers of the report (the picture tiles, the HUD palette cells of CREDITS)
    assert {n: p["tiles"] for n, p in PICS.items()} == {"intro_before": 116, "intro_a": 147, "finale_a": 107, "credits_b": 96}
    assert {n: p["hud_cells"] for n, p in PICS.items()} == {"intro_before": 0, "intro_a": 0, "finale_a": 0, "credits_b": 12}
    # the portrait slot sits below the picture's tiles in every scene
    assert all(max(i for i in PICS[n]["map"] if i >= 36) < 256 for n in PICS)


def test_the_picture_sources_convert_exactly():
    """Each source reads back as the map/tiles in build/story.json (re-converted here), tile for tile."""
    g = gen_story()
    for name, p in PICS.items():
        r = g.read_pic(name)
        assert [p["ids"][t] for t in r["tmap"]] == p["map"], name
        # every cell's pixels are its tile's: DMG shades through the key, colours through the cell's palette
        for ty in range(13):
            for tx in range(20):
                cell = ty * 20 + tx
                a = r["attr"][cell]
                for y in range(8):
                    for x in range(8):
                        c = r["key"][r["pix"][ty * 8 + y][tx * 8 + x]]
                        pal = g.hud_palette() if a == "H" else None
                        if a == "H":
                            assert g.q5(c["hex"]) == pal[c["dmg"]], (name, tx, ty)
                        else:
                            assert r["pals"][a][c["dmg"]] == c["hex"], (name, tx, ty)


def test_a_bad_picture_fails_the_build(tmp_path, monkeypatch):
    g = gen_story()
    monkeypatch.setattr(g, "PIC_DIR", tmp_path)
    keys = "@key\na 0 #f8d0a8 skin\nb 0 #00ff00 green\nc 0 #0000f8 blue\nd 0 #f80000 red\ne 0 #800080 purple\n# 3 #000000 ink\n@pixels\n"
    f = tmp_path / "bad.txt"
    f.write_text("@size 8 8\n@maxpal 4\n" + keys + "ab######\n" + "########\n" * 7)
    with pytest.raises(g.StoryError, match="160x104"):
        g.read_pic("bad")
    def pic(row):
        return "@size 160 104\n@maxpal 4\n" + keys + "\n".join(row for _ in range(104)) + "\n"
    f.write_text(pic("ab" * 80))
    with pytest.raises(g.StoryError, match="two colours on DMG shade 0"):
        g.read_pic("bad")
    f.write_text(pic(("a" * 8 + "b" * 8 + "c" * 8 + "d" * 8 + "e" * 8) * 4))
    with pytest.raises(g.StoryError, match=r"needs 5 CGB BG palettes \(max 4\)"):
        g.read_pic("bad")
    f.write_text(pic("a" * 160).replace("@maxpal 4", "@maxpal 5"))
    with pytest.raises(g.StoryError, match="@maxpal 5"):
        g.read_pic("bad")


def test_a_picture_switch_needs_the_narrators_page_and_the_docs_line(monkeypatch):
    g = gen_story()
    scenes = g.parse_script(g.ROOT / "docs" / "story.md")
    g.check_pictures(scenes)
    monkeypatch.setattr(g, "SCENE_PICS", dict(g.SCENE_PICS, INTRO=[(1, "intro_before"), (4, "intro_a")]))
    with pytest.raises(g.StoryError, match="page 4, which is not the narrator's"):
        g.check_pictures(scenes)
    monkeypatch.setattr(g, "SCENE_PICS", dict(g.SCENE_PICS, INTRO=[(1, "intro_before"), (6, "intro_a")]))
    with pytest.raises(g.StoryError, match=r"no 'Picture \(page 6\):' line"):
        g.check_pictures(scenes)
    monkeypatch.setattr(g, "SCENE_PICS", dict(g.SCENE_PICS, INTRO=[(1, "intro_before"), (9, "intro_a")]))
    with pytest.raises(g.StoryError, match="the scene has 8"):
        g.check_pictures(scenes)


# ---- the INTRO: before, a white flash, the explosion ------------------------------------------------------------
def white_frame(gb):
    return bool((np.array(gb.image())[:104] > 247).all())


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_intro_before_then_flash_then_the_explosion(model):
    with start_story(model) as gb:
        assert gb.mem("story_scene") == SC["INTRO"]
        page_ready(gb)
        assert_picture(gb, "intro_before")                       # page 1: no Dregs, the whole spigot
        check_golden(gb, "story_pic_intro_before")
        for k in (1, 2):                                          # pages 2-3: the picture stays (3: the Spigoteer's frame)
            gb.press("a", 2)
            page_ready(gb)
            assert gb.mem("story_page") == k
        assert_picture(gb, "intro_before", skip=FRAME)
        gb.press("a", 2)                                          # page 4: Dregs
        page_ready(gb)
        assert gb.mem("story_page") == 3 and gb.mem("story_cur") != 255
        assert_picture(gb, "intro_before", skip=FRAME)
        # page 5 (KA-SPLOOOOSH!!!): white, the LCD off for the reload, the explosion fades in
        gb.press("a", 2)
        whites, lcd_off, frames = 0, 0, 2
        while gb.mem("story_typed") == 54 or gb.mem("story_scratch") != 0:
            gb.run(1)
            frames += 1
            whites += white_frame(gb)
            lcd_off += not gb.pb.memory[0xFF40] & 0x80
            assert frames < 40
        assert gb.mem("story_page") == 4
        assert 6 <= frames <= 14, f"the flash takes {frames} frames"
        assert whites >= 3, "the screen is white for a few frames"
        gb.run(2)
        assert gb.pb.memory[0xFF40] & 0x80
        page_ready(gb)
        assert gb.mem("story_cur") == 255
        assert_picture(gb, "intro_a")                             # page 5: the explosion, the frame gone with it
        assert gb.mem("story_swap") == 0
        check_golden(gb, "story_pic_intro_a")
        for k in (5, 6):                                          # pages 6-7: narrator, still the explosion
            gb.press("a", 2)
            page_ready(gb)
            assert gb.mem("story_page") == k
            assert_picture(gb, "intro_a")
        gb.press("a", 2)                                          # page 8: the Spigoteer's frame over the explosion
        page_ready(gb)
        assert gb.mem("story_page") == 7 and gb.mem("story_cur") == 0
        assert_picture(gb, "intro_a", skip=FRAME)
        gb.press("a", 2)
        gb.run(2)
        assert gb.mem("story_scene") != SC["INTRO"], "the last page ends the scene"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_start_skips_the_intro_before_and_during_the_flash(model):
    """START on page 1 and START in the middle of the white flash both end the scene cleanly: the same screen of the
    next scene (its palettes and BGP back to normal after a skipped fade)."""
    shots = []
    for when in ("page1", "flash", "fade"):
        with start_story(model) as gb:
            if when != "page1":
                for _ in range(4):
                    page_ready(gb)
                    gb.press("a", 2)
                # the switch is under way (PS_FX = story_scratch[0]): in the white (steps 2-3), or in the fade (6+)
                lo = 2 if when == "flash" else 6
                run_until(gb, lambda: gb.mem("story_scratch") >= lo and gb.pb.memory[0xFF40] & 0x80, 40)
                assert gb.mem("story_scratch") != 0, "START comes mid-switch"
            gb.press("start", 10)                                 # (the game reads no keys while the LCD is off: hold it)
            run_until(gb, lambda: gb.mem("story_scene") != SC["INTRO"], 30)
            settle(gb)
            page_ready(gb)
            assert gb.mem("story_scene") == SC["PRE_SALOON"]
            shots.append(np.array(gb.image()))
    assert (shots[0] == shots[1]).all() and (shots[0] == shots[2]).all()


# ---- FINALE and CREDITS: pictures, the one portrait slot --------------------------------------------------------
def to_finale(model):
    gb = start_story(model, v7_image([], story=9), cont=True)
    skip_scene(gb)                                                # PRE_SPACE -> the Opening shift
    to_goal(gb)
    gb.write("story_step", STORY_STEPS - 1)
    win(gb, 9, 0)
    run_until(gb, lambda: state(gb) == GS_STORY and gb.mem("story_scene") == post(9), 400)
    settle(gb)
    skip_scene(gb)                                                # POST_SPACE -> FINALE
    assert gb.mem("story_scene") == SC["FINALE"]
    return gb


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_finale_streams_each_speakers_portrait_into_the_one_slot(model):
    """Every page: the picture is intact (the slot is below its tiles), the speaker's portrait is exact in the slot's
    ids, a swap goes wipe -> tiles -> frame (story_swap 1, 4, 2/3) and the copy list drains inside VBlank."""
    with to_finale(model) as gb:
        s = SCENES[SC["FINALE"]]
        slot = list(range(SLOT_BASE, SLOT_BASE + s["bg_tiles"]))
        assert max(slot) < PICS["finale_a"]["base"] and s["bg_tiles"] == 44
        page_ready(gb)
        assert_picture(gb, "finale_a")
        check_golden(gb, "story_pic_finale_a")
        seen_states = set()
        gb.write("drain_ticks_max", 0)
        for k, page in enumerate(s["pages"]):
            if k:
                gb.press("a", 2)
                while True:                                       # (the swap's states, frame by frame)
                    seen_states.add(gb.mem("story_swap"))
                    if gb.mem("story_swap") == 0 and gb.mem("story_typed") > 0:
                        break
                    gb.run(1)
            page_ready(gb)
            name = page["portrait"]
            if name is None:
                assert gb.mem("story_cur") == 255
                assert_picture(gb, "finale_a")
            else:
                assert gb.mem("story_cur") == PORTRAITS[name]["pid"], (k, name)
                assert_picture(gb, "finale_a", skip=FRAME)
                # the portrait's tiles in the slot, from its first tile on (the tile map says so)
                p = PORTRAITS[name]
                for r in range(p["h"]):
                    assert tilemap_row(gb, p["y"] + r, p["x"], p["w"]) == \
                        [SLOT_BASE + t for t in p["map"][r * p["w"]:(r + 1) * p["w"]]], (k, name, r)
        assert {1, 2, 4} <= seen_states, f"swap states seen: {sorted(seen_states)}"
        assert 0 < gb.mem("drain_ticks_max") <= 14, gb.mem("drain_ticks_max")   # inside VBlank (17 ticks); the worst frame is A mashed over a tile burst
        assert gb.mem("vq_end_ly_max") <= 153
        assert gb.mem16("vq_late") == 0


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_credits_picture_and_start_skips_the_finale(model):
    with to_finale(model) as gb:
        gb.press("start", 2)                                      # START skips the rest of the FINALE
        run_until(gb, lambda: gb.mem("story_scene") == SC["CREDITS"], 30)
        settle(gb)
        page_ready(gb)
        assert_picture(gb, "credits_b")
        check_golden(gb, "story_pic_credits_b")
        gb.press("start", 2)                                      # ... and the CREDITS: on to the title
        run_until(gb, lambda: gb.mem("story_scene") != SC["CREDITS"] or state(gb) != GS_STORY, 60)
