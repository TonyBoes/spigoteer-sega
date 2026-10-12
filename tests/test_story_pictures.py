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
from test_story import (DMG_GREY, PORTRAITS, SC, SCENES, STORY, STORY_STEPS, gen_story, page_ready, picture_switching, post, q15, settle,
                        skip_scene, start_story, to_goal, v7_image, win)

pytestmark = pytest.mark.timeout(240)

PICS = {p["name"]: p for p in STORY["pictures"]}
BURST = STORY["burst"]                 # the INTRO's ten pieces (OBJ sprites): the places they land on, their art
SLOT_BASE = STORY["portrait_base"]
FRAME = (8, 40, 80, 104)               # a speaker page's portrait frame: columns 1-9, rows 5-12 (x0, y0, x1, y1)
_EXPECT = {}


def expected(name, model):
    """The picture as the screen must show it: 160x104 RGB (INTRO A: the explosion is over, nothing flies, no trail)."""
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
        assert p["extra"] == (BURST["extra_tiles"] if name == "intro_a" else 0)          # the trail dots' tiles, unused by the map
        assert all(a in (0, 5, 6, 7, 1) for a in p["attr"]) and p["hud_cells"] == p["attr"].count(1), name
        assert p["tiles"] + p["extra"] <= 36 + 256 - p["base"], name
    # the numbers of the report (the picture tiles, the HUD palette cells of CREDITS)
    assert {n: p["tiles"] for n, p in PICS.items()} == {"intro_before": 119, "intro_a": 115, "finale_a": 135, "credits_b": 131}
    assert {n: p["hud_cells"] for n, p in PICS.items()} == {"intro_before": 0, "intro_a": 0, "finale_a": 0, "credits_b": 12}
    # the portrait slot sits below the picture's tiles in every scene
    assert all(max(i for i in PICS[n]["map"] if i >= 36) < 256 for n in PICS)


def _pix(name):
    key, pix, _ = gen_story().parse_v2(ROOT / PICS[name]["art"])
    return key, pix


def _region(pix, x0, y0, x1, y1):
    return ["".join(r[x0:x1]) for r in pix[y0:y1]]


def test_the_four_pictures_are_one_square_one_fountain_one_spigot():
    """The continuity pass: the sources share one master layout (the same characters in the same places), the
    same large gold F1 spigot and the same gold in every key, three times of day."""
    pics = {n: _pix(n) for n in PICS}
    for n, (key, _) in pics.items():                               # one gold, the INTRO's
        assert key["Y"]["hex"] == "#f8f0a0" and key["y"]["hex"] == "#e8a828", n
    # the spigot, the bowl and the pedestal (x 88-118, y 6-72): identical in the three pictures that
    # show it whole (the credits' drips and the finale's glass aside)
    ref = _region(pics["intro_before"][1], 88, 6, 119, 72)
    for n in ("finale_a", "credits_b"):
        got = _region(pics[n][1], 88, 6, 119, 72)
        diff = {(x + 88, y + 6) for y, (a, b) in enumerate(zip(ref, got)) for x, (c, d) in enumerate(zip(a, b)) if c != d}
        assert all(109 <= x < 116 and 37 <= y < 43 for x, y in diff), (n, sorted(diff)[:5])   # the drips of the credits
    assert _region(pics["intro_before"][1], 72, 72, 120, 81) == _region(pics["finale_a"][1], 72, 72, 120, 81)  # the wall (the crowd aside)
    # the clock tower and the houses at the left (x 0-30, y 29-87): the same everywhere (the dawn sun sits behind them)
    ref = _region(pics["intro_before"][1], 0, 29, 31, 88)
    for n in ("intro_a", "finale_a", "credits_b"):
        got = [r.replace("y", ".") for r in _region(pics[n][1], 0, 29, 31, 88)] if n == "credits_b" else _region(pics[n][1], 0, 29, 31, 88)
        assert got == ref, n
    # the string lights hang in the three pictures that show them taut; the finale adds pennants among them
    for n in ("intro_before", "intro_a", "finale_a"):
        assert any("#" in r for r in _region(pics[n][1], 33, 41, 72, 50)), n
    assert "r" in "".join(_region(pics["finale_a"][1], 33, 41, 160, 55)) and "r" not in "".join(_region(pics["intro_before"][1], 33, 41, 160, 55))
    # the finale: the Spigoteer's glass is in the jet (water in the glass, the jet above it down to its rim)
    f = pics["finale_a"][1]
    assert all(f[y][122] == "b" or f[y][123] == "b" for y in range(51, 58))
    assert "".join(_region(f, 121, 60, 125, 63)).count("b") >= 6


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
def burst_t(gb):
    """The burst's frame counter (src/story.c PB_T = story_scratch[168]; 255: none running)."""
    return gb.mem(gb.addr("story_scratch") + 168)


def burst_oam(gb):
    return gb.oam()[BURST["oam"]:BURST["oam"] + len(BURST["entries"])]


def line_max(gb):
    """The most sprites on one scanline (every OAM entry, 8x16 mode)."""
    assert gb.pb.memory[0xFF40] & 4, "8x16 sprites"
    lines = [0] * 144
    for e in gb.oam():
        if 0 < e["y"] < 160:
            for y in range(max(0, e["y"] - 16), min(144, e["y"])):
                lines[y] += 1
    return max(lines)


def white_frame(gb):
    return bool((np.array(gb.image())[:104] > 247).all())


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_intro_before_then_flash_then_the_explosion(model):
    with start_story(model) as gb:
        assert gb.mem("story_scene") == SC["INTRO"]
        page_ready(gb)
        assert_picture(gb, "intro_before")                       # page 1: no Dregs, the whole spigot, the fountain running
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
        assert 6 <= frames <= 16, f"the flash takes {frames} frames"
        assert whites >= 3, "the screen is white for a few frames"
        gb.run(2)
        assert gb.pb.memory[0xFF40] & 0x80
        page_ready(gb)
        assert gb.mem("story_cur") == 255
        run_until(gb, lambda: burst_t(gb) == 255, 80)             # (the ten pieces fly off the screen, trails behind them)
        assert_picture(gb, "intro_a")                             # page 5: the spigot gone, the fountain stopped, no frame
        assert not any(e["y"] for e in burst_oam(gb)), "every piece has left the screen"
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
    for when in ("page1", "flash", "fade", "burst", "done"):
        with start_story(model) as gb:
            if when != "page1":
                for _ in range(4):
                    page_ready(gb)
                    gb.press("a", 2)
                if when in ("burst", "done"):                     # the pieces are flying (frame 14), or the explosion is over
                    run_until(gb, lambda: burst_t(gb) not in (255, 0) and not picture_switching(gb), 60)
                    run_until(gb, lambda: burst_t(gb) >= 14 or burst_t(gb) == 255, 60)
                    if when == "burst":
                        assert burst_t(gb) not in (255, 0) and any(e["y"] for e in gb.oam()[BURST["oam"]:]), "START comes mid-flight"
                    else:
                        run_until(gb, lambda: burst_t(gb) == 255, 80)
                else:
                    # the switch is under way (PS_FX = story_scratch[0]): in the white (steps 2-3), or in the fade (6+)
                    lo = 2 if when == "flash" else 6
                    run_until(gb, lambda: gb.mem("story_scratch") >= lo and gb.pb.memory[0xFF40] & 0x80, 40)
                    assert gb.mem("story_scratch") != 0, "START comes mid-switch"
            gb.press("start", 10)                                 # (the game reads no keys while the LCD is off: hold it)
            run_until(gb, lambda: gb.mem("story_scene") != SC["INTRO"], 30)
            settle(gb)
            page_ready(gb)
            assert gb.mem("story_scene") == SC["PRE_SALOON"]
            assert not any(e["y"] for e in gb.oam()[BURST["oam"]:BURST["oam"] + len(BURST["entries"])]), when
            shots.append(np.array(gb.image()))
    assert all((shots[0] == sh).all() for sh in shots[1:])


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


# ---- the burst: the ten pieces fly out of the explosion ---------------------------------------------------------
def to_page5(gb):
    """Pages 1-4 (A each), then the turn onto page 5: returns when the switch has begun."""
    for _ in range(4):
        page_ready(gb)
        gb.press("a", 2)
    run_until(gb, lambda: picture_switching(gb), 40)


def test_the_pieces_are_the_intact_spigot_and_intro_a_is_the_empty_fountain():
    """The ten pieces sit exactly where the spigot of intro_before is (their pixels are the picture's own), and the
    picture after the explosion (intro_a) has that spigot gone: a broken stub on the rim, no jets, a puddle."""
    _, before = _pix("intro_before")
    _, after = _pix("intro_a")
    spigot = set()
    for pc in BURST["pieces"]:
        n = m = 0
        for dy, row in enumerate(pc["rows"]):
            for dx, c in enumerate(row):
                if c != ".":
                    n += 1
                    m += before[pc["y"] + dy][pc["x"] + dx] == c
                    if before[pc["y"] + dy][pc["x"] + dx] == c:
                        spigot.add((pc["x"] + dx, pc["y"] + dy))
        assert m >= 0.85 * n, (pc["name"], m, n)                  # (a cut piece adds its own outline pixels)
    assert len(spigot) > 300
    stub = (97, 41, 109, 48)                                      # the broken pipe on the rim
    for (x, y) in spigot:
        if not (stub[0] <= x < stub[2] and stub[1] <= y < stub[3]):
            assert after[y][x] == ".", (x, y)                     # the rest of the spigot is gone
    assert sum(after[y][x] in "Yy" for x in range(stub[0], stub[2]) for y in range(stub[1], stub[3])) >= 40
    assert after[47][100] == "y" and after[40][100] == "."        # the stub is short, the rim ink is below it
    # the fountain has stopped: no water (b) where the jets ran, a little puddle (W) on the wall
    for x0, x1 in ((79, 89), (119, 129)):
        assert not any("b" in after[y][x0:x1] for y in range(50, 72))
    assert any("W" in after[71][x0:x1] for x0, x1 in ((79, 89), (119, 129)))
    # the jets run in intro_before
    assert any("b" in before[y][79:89] for y in range(50, 72))
    # the explosion's picture is the same square: the tower and houses, the rim and the wall
    assert _region(before, 0, 29, 31, 88) == _region(after, 0, 29, 31, 88)
    assert _region(before, 72, 72, 120, 81) == _region(after, 72, 72, 120, 81)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_pieces_fly_off_the_screen_and_the_trail_fades(model):
    """After the white flash lets go the ten pieces (OBJ sprites) sit where the spigot was, then leave one after another
    in their own direction, faster and faster, off the screen; behind each a trail of dots (BG map writes) turns on,
    fades and goes: every frame's OAM is the generator's table, never more than 10 sprites on a line, the frame never
    late, the copy list inside VBlank, and at the end nothing flies and the picture is intro_a."""
    ents, pieces = BURST["entries"], BURST["pieces"]
    ne, end = len(ents), BURST["end"]
    row = lambda t: BURST["pos"][min(t, end) * ne * 2:][:ne * 2]
    clean = PICS["intro_a"]["map"]
    with start_story(model) as gb:
        to_page5(gb)
        n = 0
        while burst_t(gb) == 255:                                         # the white and the LCD off for the reload
            assert not any(e["y"] for e in burst_oam(gb)), "no piece before the flash lets go"
            gb.run(1)
            n += 1
            assert n < 40
        assert burst_t(gb) == 1 and row(0) == row(1), "they sit in the spigot's place at the start"
        prev = [tilemap_row(gb, r, 0, 20) for r in range(13)]
        assert [v for r in prev for v in r] == clean, "the dots are off at the start"
        changes, tops, logic_end, last, n, fading = {}, [], [], 1, 0, True
        while last != 255:                                                # the explosion, frame by frame
            gb.run(1)
            n += 1
            assert n < 100
            t = burst_t(gb)
            if t == last:                                                 # (the frames of the reload run no step)
                continue
            step = end if t == 255 else t - 1                             # the step this frame ran
            last = t
            if fading and not picture_switching(gb):                      # the fade is over (its palette writes and blends are the
                fading = False                                            # switch's own, measured by the INTRO tests): from here on
                for v in ("drain_ticks_max", "vq_end_ly_max", "vq_late"):  # the explosion's trail alone
                    gb.write(v, 0)
            if not fading:
                logic_end.append(gb.mem16("perf_end_last"))
            oam = burst_oam(gb)
            assert [v for e in oam for v in (e["y"], e["x"])] == row(step), f"frame {step}: OAM is the table"
            for e, ent in zip(oam, ents):
                if e["y"]:
                    assert (e["tile"], e["flags"] & 0x7F) == (ent["tile"], (ent["flip"] << 5) | BURST["pal"])
            assert line_max(gb) <= 10, f"frame {step}: {line_max(gb)} sprites on a line"
            if step == 1:
                assert line_max(gb) == 10, "the intact spigot's busiest line: ten (the limit)"
            tops.append([(e["x"] - 8 - ent["dx"], e["y"] - 16) if e["y"] else None for e, ent in zip(oam, ents)])
            now = [tilemap_row(gb, r, 0, 20) for r in range(13)]
            for r in range(13):
                for c in range(20):
                    if now[r][c] != prev[r][c]:
                        changes.setdefault((c, r), []).append((step, now[r][c]))
            prev = now
        gb.run(6)
        assert not any(e["y"] for e in burst_oam(gb)), "every piece has left the screen"
        assert max(logic_end) < 100, f"the frame's logic ends on line {max(logic_end)}: inside the frame (VBlank is 144)"
        assert gb.mem16("vq_late") == 0 and gb.mem("vq_end_ly_max") <= 153
        assert 0 < gb.mem("drain_ticks_max") <= 14, gb.mem("drain_ticks_max")
        assert 30 <= end <= 60, end
        # each piece leaves in its direction and goes on, never nearer its start, until it is off the screen
        import math
        for i, pc in enumerate(pieces):
            cells = [k for k, ent in enumerate(ents) if ent["piece"] == i]
            path = [(f, fr[cells[0]]) for f, fr in enumerate(tops) if fr[cells[0]]]
            d = [math.hypot(p[0] - pc["x"], p[1] - pc["y"]) for _, p in path]
            assert all(a <= b + 1 for a, b in zip(d, d[1:])) and d[-1] >= 20, (pc["name"], d)
            for (f, p), dd in zip(path, d):
                if dd >= 12:                                              # (before that the rounding is too coarse)
                    ang = math.degrees(math.atan2(pc["y"] - p[1], p[0] - pc["x"])) % 360
                    assert min(abs(ang - pc["dir"]), 360 - abs(ang - pc["dir"])) <= 8, (pc["name"], f, ang)
            hidden = next(f for f, fr in enumerate(tops) if all(not fr[k] for k in cells)) + 1   # (tops[0] is step 1)
            assert abs(hidden - BURST["leave"][i]) <= 1, (pc["name"], hidden, BURST["leave"][i])
        # the trail: exactly the event cells change, each one bright -> faint -> plain sky, in time with its piece
        ev = {}
        for (t, x, y, tile) in BURST["events"]:
            ev.setdefault((x, y), []).append((t, PICS["intro_a"]["ids"][tile]))
        assert set(changes) == set(ev)
        for cell, seq in ev.items():
            assert [tile for _, tile in changes[cell]] == [tile for _, tile in seq], cell
            for (step, _), (te, _) in zip(changes[cell], seq):
                assert te <= step <= te + 8, (cell, step, te)
        assert [v for r in prev for v in r] == clean, "the sky is plain again"
        assert len({tile for seq in ev.values() for _, tile in seq[:2]}) == BURST["extra_tiles"] and PICS["intro_a"]["extra"] == BURST["extra_tiles"]
        assert_picture(gb, "intro_a")
        # nothing flies while the pages go on, over a speaker's frame too
        gb.press("a", 2)
        page_ready(gb)
        assert_picture(gb, "intro_a")
        assert not any(e["y"] for e in burst_oam(gb))


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_mashing_a_through_the_burst_keeps_the_line_limit(model):
    """A pressed every other frame from the flash on: pages 5-8 come while the pieces still fly and the trail fades (and
    the Spigoteer's frame and its overlay swap in): still at most 10 sprites on a line, the copy list inside VBlank,
    and the picture at the end is intact."""
    with start_story(model) as gb:
        to_page5(gb)
        worst, fading = 0, True
        for f in range(300):
            if f % 4 == 0 and not picture_switching(gb) and gb.mem("story_page") < 7:
                gb.press("a", 1)
            else:
                gb.run(1)
            if fading and burst_t(gb) != 255 and not picture_switching(gb):   # (the switch's own fade is measured elsewhere)
                fading = False
                for v in ("drain_ticks_max", "vq_end_ly_max", "vq_late"):
                    gb.write(v, 0)
            worst = max(worst, line_max(gb))
            if gb.mem("story_scene") != SC["INTRO"]:
                break
            if gb.mem("story_page") == 7 and burst_t(gb) == 255 and gb.mem("story_swap") == 0 and gb.mem("story_typed") == 54:
                break
        assert worst <= 10
        assert gb.mem("story_scene") == SC["INTRO"] and gb.mem("story_page") == 7
        assert_picture(gb, "intro_a", skip=FRAME)
        assert gb.mem("drain_ticks_max") <= 14 and gb.mem("vq_end_ly_max") <= 153 and gb.mem16("vq_late") == 0


# ---- the owner review of the finale and the credits ------------------------------------------------------------
DREGS_J2 = ['..................', '........#####.....', '......#########...', '.....###########..', '....######mmm#####', '....##############',
            '....######DDD##...', '....####DDDDDD#...', '....#D##DDDDDD#...', '....#DD#DDD###D#..', '....#DD#DDDDDDDD#.', '....#DDDDDDDDDDDD#',
            '.....#DDDDDDDD####', '.....#DDDDD###D#..', '.....#DDDDDDDDD#..', '......##DDDDDD#...', '........#DDDD#....', '........#DDD#.....',
            '.....###D#D#D###..', '....#mmD#####Dmm#.', '...#mmmD#D#D#Dmmm#', '...#mmmmD#D#Dmmmm#', '...#m#mmmD#Dmmm#m#', '...#m#mmmmDmmmm#m#',
            '...#m#mmmmmmmmm#m#', '...#D#mmmmmmmmm#D#', '....#.#########.#.']      # his approved small art (J2), rows 0-26
PENNANTS = {"r": ["#rrr#", ".#r#.", "..#.."], "y": ["#yyy#", ".#y#.", "..#.."], "b": ["#bbb#", ".#b#.", "..#.."]}


def _find(pix, shape):
    h, w = len(shape), len(shape[0])
    return [(x, y) for y in range(len(pix) - h) for x in range(len(pix[0]) - w)
            if all(pix[y + j][x + i] == shape[j][i] for j in range(h) for i in range(w) if shape[j][i] != ".")]


def test_the_finale_shows_dregs_not_a_second_bartender():
    """Dregs is his approved small art (J2, mirrored so he faces the Spigoteer): cap, long nose, grey jacket, no white
    shirt or apron, and his colours are not the Spigoteer's."""
    key, pix = _pix("finale_a")
    want = [r[::-1].replace("D", "S") for r in DREGS_J2]
    got = _region(pix, 142, 62, 160, 89)
    assert all(g[i] == w[i] for g, w in zip(got, want) for i in range(18) if w[i] != "."), "Dregs is J2"
    assert "W" not in "".join(_region(pix, 139, 60, 160, 89)), "no white shirt or apron on Dregs"
    assert "r" in "".join(_region(pix, 126, 66, 139, 89)) and "r" not in "".join(got)       # the Spigoteer's rose cozy is not Dregs's
    assert key["m"]["hex"] == "#b0a0b8" and "".join(got).count("m") > 50                  # Dregs wears the grey jacket


def test_the_credits_flags_match_the_finales_and_the_stand_and_legs_read():
    fkey, f = _pix("finale_a")
    ckey, c = _pix("credits_b")
    for ch, shape in PENNANTS.items():                      # the same pennant shape in the same colour in both pictures
        assert ckey[ch]["hex"] == fkey[ch]["hex"], ch
        assert _find(f, shape) and _find(c, shape), ch
    assert len(_find(c, PENNANTS["r"])) >= 2 and len(_find(c, PENNANTS["b"])) >= 1 and len(_find(c, PENNANTS["y"])) >= 2
    # Dregs stands on the cobbles in his apron: outlined trousers (rows 88-91, ink round a B fill, a seam between the legs)
    # and ink shoes (rows 92-93, toes to the right) below the apron's hem (y 87)
    assert all("".join(c[y][34:43]) == "#BBB#BBB#" for y in (88, 89, 90, 91))
    assert all("".join(c[y][33:39]) == "######" and "".join(c[y][40:46]) == "######" for y in (92, 93))
    # the Sasquatch's coffee stand (24 x 32 in the HUD palette cells, a cup sign on its roof, a pale steaming cup
    # in the window and his furry arm)
    stand = _region(c, 136, 56, 160, 88)
    assert set("".join(stand)) <= set("CTGZ")
    assert stand[1] == "ZGGGCCCCGGGGCCCCGGGGCCCZ"            # the striped awning
    sign = "".join(_region(c, 139, 43, 157, 56))
    assert sign.count("Y") >= 60 and sign.count("y") >= 20
    window = "".join(stand[8:23])
    assert window.count("C") >= 30 and window.count("T") >= 30 and window.count("G") >= 60       # cup and steam, hand, fur
