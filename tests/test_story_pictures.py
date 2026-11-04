# Story pictures (INTRO before / INTRO explosion, FINALE_A / FINALE_B, CREDITS): the full-screen pictures of the picture scenes
# (assets/story/pictures/*.txt -> build/story_pictures.c by tools/gen_story.py), the INTRO's picture switch behind a white
# flash (src/story.c pic_fx), and the picture scenes' one portrait slot that each speaker's tiles stream into
# (SW_TILES). Pixel checks compare the screen with the approved source, exact on DMG (each key's shade) and on CGB (each
# key's RGB15 colour).
import numpy as np
import pytest
import perf_helpers as ph
from PIL import Image
from conftest import ROOT, check_golden, until_game
from test_flow import GS_STORY, run_until, state, tilemap_row
from test_story import (DMG_GREY, PORTRAITS, SC, SCENES, STORY, STORY_STEPS, gen_story, page_ready, picture_switching, post, q15, settle,
                        skip_scene, start_story, through_the_pouroff, to_goal, v7_image, win)

pytestmark = pytest.mark.timeout(240)

PICS = {p["name"]: p for p in STORY["pictures"]}
BURST = STORY["burst"]                 # the INTRO's ten pieces (OBJ sprites): the places they land on, their art
SLOT_BASE = STORY["portrait_base"]
FRAME = (8, 32, 80, 104)               # a speaker page's portrait frame with its name plate: columns 1-9, rows 4-12 (x0, y0, x1, y1)
_EXPECT = {}
CRACKLE = (80, 14, 128, 46)            # the sparks' box over INTRO A (OBJ: the picture under them is exact)
SPARKS = 6                             # OAM entries of the sparks (BURST["oam"] .. +5)


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


WATER_CELLS = [tuple(c) for c in STORY["water_cells"]]   # the jets' cells (left jet's three, then the right's): their tiles flow


def jet_tiles(gb, name):
    """the six jet cells' tiles as VRAM holds them now"""
    return [[gb.pb.memory[a + k] for k in range(16)] for a in PICS[name]["water_addr"]]


def water_phases(gb, name):
    """the phase each jet (left, right) shows: its three tiles are that phase's (story.json); None when they are no phase"""
    w, t = PICS[name]["water"], jet_tiles(gb, name)
    return tuple(next((ph for ph in range(len(w)) if w[ph][j * 3:j * 3 + 3] == t[j * 3:j * 3 + 3]), None) for j in (0, 1))


def picture_diff(gb, name, skip=None):
    """Pixels of the picture area (rows 0-12) that differ from the source; `skip` = a rectangle to leave out. A picture whose
    fountain flows: its jet cells are left out here (assert_picture checks their tiles are one of the water's phases)."""
    got = np.array(gb.image())[:104, :160]
    bad = np.any(got != expected(name, gb.model_name), axis=2)
    if name == "intro_a":
        bad[CRACKLE[1]:CRACKLE[3], CRACKLE[0]:CRACKLE[2]] = False
    if PICS[name]["water"]:
        for cx, cy in WATER_CELLS:
            bad[cy * 8:cy * 8 + 8, cx * 8:cx * 8 + 8] = False
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
    if p["water"]:
        assert None not in water_phases(gb, name), f"{name}: the jets' tiles are no phase of the water"


# ---- the build -----------------------------------------------------------------------------------------------
def test_the_pictures_are_built_to_the_budget():
    assert list(PICS) == ["intro_before", "intro_a", "finale_a", "finale_contest", "credits_b"]
    by_scene = {s["id"]: s for s in SCENES}
    assert [(by_scene[i]["pic"], by_scene[i]["swpage"]) for i in ("INTRO", "FINALE_A", "FINALE_B", "CREDITS")] == [(0, 7), (2, 4), (2, 0), (4, 0)]   # (FINALE_A: the contest's set-up from page 4; FINALE_B shares the first-pour picture only)
    for name, p in PICS.items():
        sc = by_scene[p["scene"]]
        slot = sc["bg_tiles"]
        assert p["base"] == SLOT_BASE + slot, name
        assert len(p["pals"]) <= (5 if p["bg2"] else 4) and len(p["map"]) == len(p["attr"]) == 260
        ids = set(p["map"])
        assert len(ids) == p["tiles"] and ids <= set(range(36)) | set(range(p["base"], 256)), f"{name}: tile ids"
        assert p["extra"] == (BURST["extra_tiles"] if name == "intro_a" else 0)          # the trail dots' tiles, unused by the map
        assert all(a in (0, 5, 6, 7, 1) + ((2,) if p["bg2"] else ()) for a in p["attr"]) and p["hud_cells"] == p["attr"].count(1), name
        assert p["tiles"] + p["extra"] <= 36 + 256 - p["base"], name
    # the numbers of the report (the picture tiles, the HUD palette cells of CREDITS)
    assert {n: p["tiles"] for n, p in PICS.items()} == {"intro_before": 120, "intro_a": 109, "finale_a": 146, "finale_contest": 142, "credits_b": 130}
    assert {n: p["hud_cells"] for n, p in PICS.items()} == {"intro_before": 0, "intro_a": 0, "finale_a": 0, "finale_contest": 0, "credits_b": 0}
    assert {n: len(p["pals"]) for n, p in PICS.items()} == {"intro_before": 4, "intro_a": 3, "finale_a": 4, "finale_contest": 4, "credits_b": 5}
    # Option A (town import 2026-11-04): the credits' fifth palette (the dawn jets' blue) is in BG 2, which a scene with no speaker page,
    # no picture switch and no sharer never needs; no other picture may use it
    assert {n for n, p in PICS.items() if p["bg2"]} == {"credits_b"} and 2 in PICS["credits_b"]["attr"]
    # the portrait slot sits below the picture's tiles in every scene
    assert all(max(i for i in PICS[n]["map"] if i >= 36) < 256 for n in PICS)


def _pix(name):
    key, pix, _ = gen_story().parse_v2(ROOT / PICS[name]["art"])
    return key, pix


def _region(pix, x0, y0, x1, y1):
    return ["".join(r[x0:x1]) for r in pix[y0:y1]]


# The town master (owner 2026-11-04, round 6 with the roof, Q74): every picture of the square is one hand-drawn grid of material keys
# (docs/dev/concepts/town_2026-11-04: tools/master.py, compose.py) and its own key is the time of day. Each picture differs from the
# night's intro_before only where its own props stand (x0, y0, x1, y1 inclusive), above the plaza's edge (y 88).
TOWN_PROPS = {
    "intro_a": {"the broken spigot": (84, 0, 123, 47), "the stopped jets": (72, 48, 127, 71), "Dregs": (40, 64, 63, 87),
                "the Spigoteer's shrug": (134, 64, 159, 87), "the crowd's heads": (64, 76, 119, 87)},
    "finale_a": {"sun and clouds": (0, 0, 159, 23), "the Spigoteer and his glass": (112, 56, 141, 87), "Dregs": (136, 56, 159, 87),
                 "the crowd's heads": (40, 76, 127, 87)},
    "finale_contest": {"sun and clouds": (0, 0, 159, 23), "the Spigoteer": (56, 64, 79, 87), "Dregs": (136, 56, 159, 87),
                       "the crowd's heads": (40, 76, 127, 87)},
    "credits_b": {"sun and clouds": (0, 0, 159, 23), "the sun behind the town": (0, 24, 47, 47), "the drips": (80, 32, 127, 63),
                  "Dregs and his mop": (32, 64, 63, 87), "the crowd's heads": (40, 76, 127, 87), "the right house, nobody at it": (136, 64, 159, 87)},
}


def test_the_pictures_are_one_town_master_with_their_own_props():
    pics = {n: _pix(n) for n in PICS}
    ref = pics["intro_before"][1]
    assert set(TOWN_PROPS) == set(PICS) - {"intro_before"}
    for n, boxes in TOWN_PROPS.items():
        p = pics[n][1]
        stray = [(x, y) for y in range(88) for x in range(160) if p[y][x] != ref[y][x] and ref[y][x] != "K"      # (K: the night's stars)
                 and not any(x0 <= x <= x1 and y0 <= y <= y1 for x0, y0, x1, y1 in boxes.values())]
        assert not stray, (n, stray[:8])
        assert _region(p, 0, 0, 160, 8) == _region(ref, 0, 0, 160, 8), f"{n}: the bunting"
    for n, (key, _) in pics.items():                               # one gold
        assert key["y"]["hex"] == "#e8a828", n
    # the Golden Spigot, the bowl and the pedestal (x 88-116, y 24-72): the same in the three pictures that show it whole (the credits' drips aside)
    ref_sp = _region(ref, 88, 24, 117, 73)
    for n in ("finale_a", "finale_contest", "credits_b"):
        got = _region(pics[n][1], 88, 24, 117, 73)
        diff = {(x + 88, y + 24) for y, (a, b) in enumerate(zip(ref_sp, got)) for x, (c, d) in enumerate(zip(a, b)) if c != d}
        assert all(n == "credits_b" and 80 <= x <= 127 and 32 <= y <= 63 for x, y in diff), (n, sorted(diff)[:5])
    # the finale: the Spigoteer's glass is in the jet (water in the glass, the jet above it down to its rim)
    f = pics["finale_a"][1]
    assert all(f[y][122] == "b" or f[y][123] == "b" for y in range(51, 58))
    assert "".join(_region(f, 121, 60, 125, 63)).count("b") >= 6


def test_the_picture_sources_convert_exactly():
    """Each source reads back as the map/tiles in build/story.json (re-converted here), tile for tile."""
    g = gen_story()
    for name, p in PICS.items():
        r = g.read_pic(name, p["bg2"])
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
    monkeypatch.setattr(g, "SCENE_PICS", dict(g.SCENE_PICS, INTRO=[(1, "intro_before"), (8, "intro_a")]))
    with pytest.raises(g.StoryError, match=r"no 'Picture \(page 8\):' line"):
        g.check_pictures(scenes)
    monkeypatch.setattr(g, "SCENE_PICS", dict(g.SCENE_PICS, INTRO=[(1, "intro_before"), (13, "intro_a")]))
    with pytest.raises(g.StoryError, match="the scene has 12"):
        g.check_pictures(scenes)


# ---- the INTRO: before, a white flash, the explosion ------------------------------------------------------------
def burst_t(gb):
    """The burst's frame counter (src/story.c PB_T = story_scratch[168]; 255: none running)."""
    return gb.mem(gb.addr("story_scratch") + 168)


def burst_oam(gb):
    return gb.oam()[BURST["oam"]:BURST["oam"] + len(BURST["entries"])]


def pieces_oam(gb):
    """the pieces' entries without the sparks' six (OAM 20-25 once the star is gone)"""
    return burst_oam(gb)[SPARKS:]


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
        check_golden(gb, "story_narrator")  # (the same picture as test_story.py)
        for k in (1, 2, 3, 4):                                    # pages 2-5: the picture stays (3: the festival, 4: the Spigoteer's frame, 5: the mustache)
            gb.press("a", 2)
            page_ready(gb)
            assert gb.mem("story_page") == k
        assert_picture(gb, "intro_before", skip=FRAME)
        gb.press("a", 2)                                          # page 6: Dregs
        page_ready(gb)
        assert gb.mem("story_page") == 5 and gb.mem("story_cur") != 255
        assert_picture(gb, "intro_before", skip=FRAME)
        # page 7 (GLUG... KA-SPLOOOOSH!!!): white, the LCD off for the reload, the explosion fades in
        gb.press("a", 2)
        whites, lcd_off, frames = 0, 0, 2
        while gb.mem("story_typed") == 54 or gb.mem("story_scratch") != 0:
            gb.run(1)
            frames += 1
            whites += white_frame(gb)
            lcd_off += not gb.pb.memory[0xFF40] & 0x80
            assert frames < 40
        assert gb.mem("story_page") == 6
        assert 6 <= frames <= 16, f"the flash takes {frames} frames"
        assert whites >= 3, "the screen is white for a few frames"
        gb.run(2)
        assert gb.pb.memory[0xFF40] & 0x80
        page_ready(gb)
        assert gb.mem("story_cur") == 255
        run_until(gb, lambda: burst_t(gb) == 255, 80)             # (the ten pieces fly off the screen, trails behind them)
        assert_picture(gb, "intro_a")                             # page 7: the spigot gone, the fountain stopped, no frame
        assert not any(e["y"] for e in pieces_oam(gb)), "every piece has left the screen"
        assert gb.mem("story_swap") == 0
        golden_err = None
        try:
            check_golden(gb, "story_pic_intro_a")                 # (with the sparks above the stump: the same every run)
        except AssertionError as err:
            golden_err = err
        for k in (7, 8, 9, 10):                                   # pages 8-11: narrator, Dregs, the Spigoteer, narrator: still the explosion
            gb.press("a", 2)
            page_ready(gb)
            assert gb.mem("story_page") == k
            assert_picture(gb, "intro_a", skip=FRAME if k in (8, 9) else None)
        gb.press("a", 2)                                          # page 12: the Spigoteer's frame over the explosion
        page_ready(gb)
        assert gb.mem("story_page") == 11 and gb.mem("story_cur") == 0
        assert_picture(gb, "intro_a", skip=FRAME)
        gb.press("a", 2)
        gb.run(2)
        run_until(gb, lambda: gb.mem("story_phase") == 9, 80)   # the last page ends the scene: the story map
        if golden_err:
            raise golden_err


PW_AT = 300                            # src/story.c story_water's bytes in story_scratch: PW_T, PW_PH, PW_DUE, then its buffer


def assert_water_flows(gb, name, frames=72, skip=None):
    """Owner Q74 (the town approved, 2026-11-04): the jets' highlights run down the two jets: a phase step every 8 game frames, in
    order (0 1 2 3 0 ...), the left jet's tiles queued that frame and the right's the next. Nothing else of the picture moves: every
    other pixel of rows 0-12 stays as the source has it, and so does the tile map."""
    sc = gb.addr("story_scratch") + PW_AT
    log = []                                                    # per GAME frame, at the end of its logic: (PW_T, PW_PH, PW_DUE)
    def rec():
        log.append(tuple(gb.pb.memory[sc + k] for k in range(3)))
        return len(log) > frames + 1
    until_game(gb, rec, limit=frames * 3)
    log = log[1:]                                               # (until_game checks once at once: not a frame end)
    for (t0, p0, d0), (t1, p1, d1) in zip(log, log[1:]):
        assert t1 == (t0 + 1) & 255, log                        # one count a game frame
        if t1 & 7:
            assert p1 == p0, log
        else:
            assert p1 == (p0 + 1) & 3 and d1 == 2, log           # the step: the left jet's tiles go this frame ...
    for (t0, p0, d0), (t1, p1, d1) in zip(log, log[1:]):
        if not t0 & 7:
            assert d1 == 0, log                                  # ... the right jet's the next
    assert {q[1] for q in log} == {0, 1, 2, 3}
    seen = []                                                   # per EMULATOR frame: what VRAM shows
    for f in range(frames):
        gb.run(1)
        seen.append(water_phases(gb, name))
        assert None not in seen[-1], f"frame {f}: the jets' tiles are no phase of the water"
        if f % 9 == 0:
            assert_picture(gb, name, skip)                       # (everything else as the source, the jets in a phase)
    for j in (0, 1):
        ph = [q[j] for q in seen]
        assert all(b in (a, (a + 1) & 3) for a, b in zip(ph, ph[1:])), (j, ph)
        assert set(ph) == {0, 1, 2, 3}, (j, ph)
    assert gb.mem("drain_ticks_max") <= 13 and gb.mem("vq_end_ly_max") <= 153 and gb.mem16("vq_late") == 0


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_fountain_flows_at_night_and_the_rest_stays(model):
    with start_story(model) as gb:
        page_ready(gb)
        assert_water_flows(gb, "intro_before")


def test_the_water_tiles_are_the_jets_own():
    """The water's tiles (story.json, from assets/story/pictures/water.txt): phase 0 is each picture's own jet tiles, the phases
    differ, and only the jet cells' tile ids are rewritten (each one used by its cell alone). INTRO A's fountain has stopped."""
    assert [n for n, p in PICS.items() if p["water"]] == ["intro_before", "finale_a", "finale_contest", "credits_b"]
    for n, p in PICS.items():
        if not p["water"]:
            continue
        ids = [p["map"][cy * 20 + cx] for cx, cy in WATER_CELLS]
        assert all(p["map"].count(i) == 1 for i in ids), n
        assert p["water_addr"] == [(0x9000 + i * 16) if i < 128 else 0x8800 + (i - 128) * 16 for i in ids], n
        assert len(p["water"]) == STORY["water_phases"] == 4
        for j in (0, 1):
            assert len({tuple(map(tuple, p["water"][ph][j * 3:j * 3 + 3])) for ph in range(4)}) == 4, (n, j)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_start_skips_the_intro_before_and_during_the_flash(model):
    """START on page 1 and START in the middle of the white flash both end the scene cleanly: the same screen of the
    next scene (its palettes and BGP back to normal after a skipped fade)."""
    shots = []
    for when in ("page1", "flash", "fade", "burst", "done"):
        with start_story(model) as gb:
            if when != "page1":
                for _ in range(6):
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
            run_until(gb, lambda: gb.mem("story_phase") == 9, 80)      # INTRO -> the story map; A at the saloon: its PRE scene
            from test_story import through_the_map
            through_the_map(gb)
            settle(gb)
            page_ready(gb)
            assert gb.mem("story_scene") == SC["PRE_SALOON"]
            assert not any(e["y"] for e in gb.oam()[BURST["oam"]:BURST["oam"] + len(BURST["entries"])]), when   # (the crackle too)
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
    assert gb.mem("story_scene") == SC["FINALE_A"]
    return gb


@pytest.mark.parametrize("scene", ["FINALE_A", "FINALE_B"])
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_finale_streams_each_speakers_portrait_into_the_one_slot(model, scene):
    """Every page: the picture is intact (the slot is below its tiles), the speaker's portrait is exact in the slot's
    ids, a swap goes wipe -> tiles -> frame (story_swap 1, 4, 2/3) and the copy list drains inside VBlank. FINALE_B (after the
    Pour-Off) shows the same picture, from the one copy FINALE_A's slot (53 tiles with the name plate, Sadie's redraw) leaves room for (its own portraits: 46)."""
    with to_finale(model) as gb:
        if scene == "FINALE_B":
            through_the_pouroff(gb)
        s = SCENES[SC[scene]]
        slot = list(range(SLOT_BASE, SLOT_BASE + s["bg_tiles"]))
        assert max(slot) < PICS["finale_a"]["base"] and s["bg_tiles"] == (53 if scene == "FINALE_A" else 46)
        assert PICS["finale_contest"]["base"] == PICS["finale_a"]["base"]    # (the contest's picture loads over the first-pour one)
        page_ready(gb)
        assert_picture(gb, "finale_a", skip=None if s["pages"][0]["portrait"] is None else FRAME)
        if scene == "FINALE_A":
            check_golden(gb, "story_pic_finale_a")
            assert_water_flows(gb, "finale_a", 40, skip=None if s["pages"][0]["portrait"] is None else FRAME)   # (by day: the right jet into the glass)
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
            pic = "finale_contest" if scene == "FINALE_A" and k >= 3 else "finale_a"   # (FINALE_A page 4 on: the contest's set-up behind a flash; FINALE_B: the first pour)
            if name is None:
                assert gb.mem("story_cur") == 255
                assert_picture(gb, pic)
                if scene == "FINALE_A" and k == 3:                    # (a new golden: the contest's set-up on its first page; written when missing)
                    g = ROOT / "tests" / "golden" / f"story_pic_finale_contest.{gb.model_name}.png"
                    if g.exists():
                        check_golden(gb, "story_pic_finale_contest")
                    else:
                        gb.golden(g, update=True)
                    assert_water_flows(gb, "finale_contest", 40)  # (the jet runs into the basin again: nobody holds a glass up)
            else:
                assert gb.mem("story_cur") == PORTRAITS[name]["pid"], (k, name)
                assert_picture(gb, pic, skip=FRAME)
                # the portrait's tiles in the slot, from its first tile on (the tile map says so)
                p = PORTRAITS[name]
                for r in range(p["h"]):
                    assert tilemap_row(gb, p["y"] + r, p["x"], p["w"]) == \
                        [SLOT_BASE + t for t in p["map"][r * p["w"]:(r + 1) * p["w"]]], (k, name, r)
        assert {1, 2, 4} <= seen_states, f"swap states seen: {sorted(seen_states)}"
        assert 0 < gb.mem("drain_ticks_max") <= 13, gb.mem("drain_ticks_max")   # inside VBlank (17 ticks): the page turn (74 bytes) is the worst frame, see test_mashing_a_never_makes_the_drain_leave_vblank
        assert gb.mem("vq_end_ly_max") <= 153
        assert gb.mem16("vq_late") == 0


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_credits_picture_and_start_skips_the_finale(model):
    with to_finale(model) as gb:
        through_the_pouroff(gb)                                   # (START skips FINALE_A, the Pour-Off is won: FINALE_B)
        gb.press("start", 2)                                      # START skips the rest of the FINALE
        run_until(gb, lambda: gb.mem("story_scene") == SC["CREDITS"], 30)
        settle(gb)
        page_ready(gb)
        assert_picture(gb, "credits_b")
        check_golden(gb, "story_pic_credits_b")
        assert_water_flows(gb, "credits_b", 40)                  # (at dawn)
        gb.press("start", 2)                                      # ... and the CREDITS pages: on to the credits roll (tests/test_credits.py)
        run_until(gb, lambda: gb.mem("story_phase") == 8, 60)


# ---- the burst: the ten pieces fly out of the explosion ---------------------------------------------------------
def to_page5(gb):
    """Pages 1-6 (A each), then the turn onto page 7 (the explosion): returns when the switch has begun."""
    for _ in range(6):
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
        x0, y0, sw, sh = BURST["star_cells"]
        start = list(clean)
        for k, t in enumerate(BURST["star0"]):                            # (the star is drawn full size with the LCD off)
            start[(y0 + k // sw) * 20 + x0 + k % sw] = PICS["intro_a"]["ids"][t]
        assert [v for r in prev for v in r] == start, "the dots are off at the start, the star is up"
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
                logic_end.append(ph.end_line(gb))
            oam = burst_oam(gb)
            lo = SPARKS if step >= BURST["crackle_t"] else 0              # (from then on OAM 20-25 are the sparks': their own test)
            assert [v for e in oam[lo:] for v in (e["y"], e["x"])] == row(step)[lo * 2:], f"frame {step}: OAM is the table"
            for e, ent in zip(oam[lo:], ents[lo:]):
                if e["y"]:
                    assert (e["tile"], e["flags"] & 0x7F) == (ent["tile"], (ent["flip"] << 5) | BURST["pal"])
            assert line_max(gb) <= 10, f"frame {step}: {line_max(gb)} sprites on a line"
            if step == 1:
                assert line_max(gb) == 10, "the intact spigot's busiest line: ten (the limit)"
            tops.append([(e["x"] - 8 - ent["dx"], e["y"] - 16) if e["y"] and k >= lo else None for k, (e, ent) in enumerate(zip(oam, ents))])
            now = [tilemap_row(gb, r, 0, 20) for r in range(13)]
            for r in range(13):
                for c in range(20):
                    if now[r][c] != prev[r][c]:
                        changes.setdefault((c, r), []).append((step, now[r][c]))
            prev = now
        gb.run(6)
        assert not any(e["y"] for e in pieces_oam(gb)), "every piece has left the screen"
        ph.plog("logic_end", max(logic_end))
        assert max(logic_end) < (52 if ph.is_ds(gb) else 110), f"the frame's logic ends on line {max(logic_end)}: inside the frame (VBlank is 144)"   # 102 on DMG with the name plates + the sparks (was < 100, then < 106; < 110 since the INTRO got 4 more pages: its worst frame is line 107, VBlank is 144)
        assert gb.mem16("vq_late") == 0 and gb.mem("vq_end_ly_max") <= 153
        assert 0 < gb.mem("drain_ticks_max") <= 13, gb.mem("drain_ticks_max")
        assert 30 <= end <= 70, end
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
        state = {(x0 + k % sw, y0 + k // sw): PICS["intro_a"]["ids"][t] for k, t in enumerate(BURST["star0"])}
        for (t, y, tiles) in BURST["rows"]:                              # the star: a row of cells a write; a cell is seen when its tile changes
            for i, tile in enumerate(tiles):
                tid = PICS["intro_a"]["ids"][tile]
                if state[(x0 + i, y)] != tid:
                    ev.setdefault((x0 + i, y), []).append((t, tid))
                    state[(x0 + i, y)] = tid
        assert set(changes) == set(ev)
        for cell, seq in ev.items():
            assert [tile for _, tile in changes[cell]] == [tile for _, tile in seq], cell
            for (step, _), (te, _) in zip(changes[cell], seq):
                assert te <= step <= te + 8, (cell, step, te)
        assert [v for r in prev for v in r] == clean, "the sky is plain again"
        pid = PICS["intro_a"]["ids"]
        extras = set(pid[PICS["intro_a"]["tiles"]:])                      # (every appended tile, the trail's dots and the star's, is used)
        used = {tile for seq in ev.values() for _, tile in seq} | {pid[t] for t in BURST["star0"]}
        assert extras <= used and len(extras) == BURST["extra_tiles"] == PICS["intro_a"]["extra"]
        assert_picture(gb, "intro_a")
        # nothing flies while the pages go on, over a speaker's frame too
        gb.press("a", 2)
        page_ready(gb)
        assert_picture(gb, "intro_a")
        assert not any(e["y"] for e in pieces_oam(gb))


def star_cells(gb):
    """how many of the star's cells (BG map) are not the plain sky: 0 = gone, 12 = full size, fewer = the small size"""
    x0, y0, sw, sh = BURST["star_cells"]
    clean = PICS["intro_a"]["map"]
    n = 0
    for r in range(y0, y0 + sh):
        row = tilemap_row(gb, r, x0, sw)
        n += sum(row[i] != clean[r * 20 + x0 + i] for i in range(sw))
    return n


def spark_slots(gb):
    """OAM 20-25 (each one a spark slot): None for a hidden one, else (x, y, tile, flags) with y the spark's own row (the sprite's
    reference pixel: row 1, or row 14 when it is flipped upside down)"""
    out = []
    for e in burst_oam(gb)[:SPARKS]:
        fl = e["flags"] & 0x60
        out.append((e["x"] - 8, e["y"] - 16 + (14 if fl & 0x40 else 1), e["tile"], fl) if e["y"] else None)
    return out


def spark_boxes(gb):
    return [q for q in spark_slots(gb) if q]


def check_sparks(frames):
    """sparks off the stump over a stretch of frames (one list of 6 slots per frame): inside the box above the stump, only the
    spark tiles, they rise and then fall, and they come in bursts with quiet between them"""
    x0, y0, x1, y1 = CRACKLE
    xs, ys = BURST["crackle_xy"]                                      # the stump's broken top: where they leave
    for f in frames:
        for q in f:
            if q:
                assert x0 <= q[0] < x1 and y0 <= q[1] < y1, q
                assert q[1] <= ys + 1, "they never drop below the stump's top"
                assert q[2] in (96, 98, 100, 102), q
    counts = [sum(1 for q in f if q) for f in frames]
    runs, quiet, inb, gaps = 0, 0, False, []
    for c in counts:
        if c:
            if not inb:
                runs += 1
                if quiet:
                    gaps.append(quiet)
            inb, quiet = True, 0
        else:
            inb = False
            quiet += 1
    big = [g for g in gaps if g >= 8]                                 # (a burst's own sparks blink out for a frame or two: not a gap)
    assert len(big) >= 2 and max(big) >= 15, gaps                     # bursts with real quiet between them, not a steady stream
    assert len(set(big)) > 1, "irregular gaps"
    assert 3 <= max(counts) <= SPARKS, max(counts)
    assert sum(1 for c in counts if c == 0) >= len(counts) // 4, "mostly quiet between bursts"
    # arcs: each lit stretch of a slot (a spark blinks out for a frame in its last frames, so one spark can be two stretches) is at
    # most 25 frames; the long ones rise (y falls) and then fall back (y grows): the arc
    peaks = rose = fell = 0
    for i in range(SPARKS):
        ys_ = []
        for f in frames + [[None] * SPARKS]:
            if f[i]:
                ys_.append(f[i][1])
            elif ys_:
                assert len(ys_) <= 25, ("life", len(ys_))
                if len(ys_) >= 8:
                    top = ys_.index(min(ys_))
                    peaks += 0 < top < len(ys_) - 1
                    rose += min(ys_) < ys_[0]
                    fell += ys_[-1] > min(ys_)
                ys_ = []
    assert peaks >= 6 and rose >= 6 and fell >= 6, (peaks, rose, fell)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_burst_pulses_while_the_pieces_fly_then_dies_down_and_the_crackle_takes_over(model):
    """Owner 2026-10-15: the explosion graphic is in the middle, pulses while the pieces fly away, dies down once they are
    gone, replaced by an electric crackle. The star (BG cells over the spigot's spot) is up at the flash in its big size,
    swings between the big and the small size (a pulse each time it is big again), is gone a couple of frames after its last
    scheduled write, and from BURST['crackle_t'] on two flickering bolts (OBJ) sit above the stump, with the rattle sound,
    on pages 6-11 alike, inside the line limit, and gone when the scene ends."""
    SHAKE = 8                                                         # music.h SFX_SHAKE
    x0, y0, sw, sh = BURST["star_cells"]
    full = sw * sh
    with start_story(model) as gb:
        to_page5(gb)
        n = 0
        while burst_t(gb) == 255:
            gb.run(1)
            n += 1
            assert n < 40
        assert star_cells(gb) == full, "the star is up the moment the flash lets go"
        sizes, frames = [], []
        before = gb.read("sfx_count", SHAKE + 1)[SHAKE]
        for _ in range(150):
            gb.run(1)
            t = burst_t(gb)
            sizes.append(star_cells(gb))
            if t == 255 or t >= BURST["crackle_t"]:
                frames.append(spark_slots(gb))
                assert line_max(gb) <= 10
        # the pulse: full -> small -> full ... (the swings follow the generator's timeline), then 0 for good
        assert min(s for s in sizes[:25]) < full, "it shrinks between the peaks"
        assert sum(1 for k in range(1, len(sizes)) if sizes[k - 1] < full == sizes[k]) >= 1, "it grows back to full size: a pulse"
        first_zero = next(i for i, v in enumerate(sizes) if v == 0)
        assert all(v == 0 for v in sizes[first_zero:]), "gone for good"
        last_row = BURST["rows"][-1][0]
        assert last_row <= first_zero + 3 <= last_row + 8, (first_zero, last_row)
        assert 25 <= BURST["crackle_t"] <= 60 and first_zero <= BURST["crackle_t"] + 2
        # the star is still up while pieces are still flying (the last piece leaves around frame max(leave))
        assert first_zero + 1 >= max(BURST["leave"]) - 6, (first_zero, max(BURST["leave"]))
        check_sparks(frames)
        assert gb.read("sfx_count", SHAKE + 1)[SHAKE] == before, "no crackle sound"
        # it keeps sparking on the next pages, over the Spigoteer's frame too; line limit
        for page in (7, 8, 9, 10, 11):
            gb.press("a", 2)
            page_ready(gb)
            fr = []
            for _ in range(150):
                gb.run(1)
                fr.append(spark_slots(gb))
                assert line_max(gb) <= 10
            assert sum(1 for f in fr if any(f)) >= 40, page
            assert gb.read("sfx_count", SHAKE + 1)[SHAKE] == before, "no crackle sound"
            assert not any(e["y"] for e in pieces_oam(gb))
            assert star_cells(gb) == 0
        for _ in range(12):                                               # (A until the last page lets go: its beat, its typing)
            if gb.mem("story_scene") != SC["INTRO"]:
                break
            gb.press("a", 2)
            gb.run(8)
        assert gb.mem("story_scene") != SC["INTRO"]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_mashing_a_through_the_burst_keeps_the_line_limit(model):
    """A pressed every other frame from the flash on: pages 7-12 come while the pieces still fly and the trail fades (and
    the Spigoteer's frame and its overlay swap in): still at most 10 sprites on a line, the copy list inside VBlank,
    and the picture at the end is intact."""
    with start_story(model) as gb:
        to_page5(gb)
        worst, fading = 0, True
        for f in range(300):
            if f % 4 == 0 and not picture_switching(gb) and gb.mem("story_page") < 11:
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
            if gb.mem("story_page") == 11 and burst_t(gb) == 255 and gb.mem("story_swap") == 0 and gb.mem("story_typed") == 54:
                break
        assert worst <= 10
        assert gb.mem("story_scene") == SC["INTRO"] and gb.mem("story_page") == 11
        assert_picture(gb, "intro_a", skip=FRAME)
        assert gb.mem("drain_ticks_max") <= 13 and gb.mem("vq_end_ly_max") <= 153 and gb.mem16("vq_late") == 0


# ---- the owner review of the finale and the credits ------------------------------------------------------------
def mash_scene(model, scene):
    """A cut-scene ready to be crawled, and when to stop (INTRO and a PRE scene end at the goal banner, FINALE_A at the Pour-Off,
    FINALE_B on leaving the story state or when the credits roll has scrolled to its end)."""
    from test_flow import GS_GOAL
    if scene == "INTRO":
        return start_story(model), lambda g: state(g) == GS_GOAL
    if scene == "PRE":
        return start_story(model, v7_image([], story=2), cont=True), lambda g: state(g) == GS_GOAL
    gb = to_finale(model)
    if scene == "FINALE_A":
        return gb, lambda g: state(g) != GS_STORY
    through_the_pouroff(gb)
    # (FINALE_B, the CREDITS pages, the roll's scroll: the roll then holds its last line until the 88 s credits tune has played)
    return gb, lambda g: state(g) != GS_STORY or (g.mem("story_phase") == 8 and g.read("story_scratch", 27)[25] > 0)


@pytest.mark.parametrize("period", [2, 3, 4, 6])
@pytest.mark.parametrize("scene", ["INTRO", "PRE", "FINALE_A", "FINALE_B"])
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_mashing_a_never_makes_the_drain_leave_vblank(model, scene, period):
    """A pressed over and over through a whole cut-scene: whatever a press queues (the page's text, a page turn) and whatever
    a portrait change streams in the same frame (tile bursts, picture rows, attributes), the VBlank copy list drains in at
    most 13 DIV ticks and is done by line 153. It used to reach 17-18 ticks and end on line 0-2 of the next frame, where
    the LCD blocks VRAM writes: in SameBoy the last writes were lost and a name tag read DREGOTEER (src/story.c VQ_STORY_ROOM)."""
    gb, done = mash_scene(model, scene)
    gb.write("drain_ticks_max", 0)
    gb.write("vq_end_ly_max", 0)
    worst, end = 0, 0
    for i in range(1500):
        if i % period == 0:
            gb.hold("a")
        elif i % period == (period + 1) // 2:
            gb.release("a")
        gb.run(1)
        worst, end = max(worst, gb.mem("drain_ticks_max")), max(end, gb.mem("vq_end_ly_max"))
        gb.write("drain_ticks_max", 0)
        gb.write("vq_end_ly_max", 0)
        if done(gb):
            break
    gb.release("a")
    assert i < 1499, "the scene was crawled to its end"
    assert 0 < worst <= 13 and end <= 153, (worst, end)
    assert gb.mem16("vq_late") == 0



def _frames(path):
    rows = [r for r in (ROOT / path).read_text().splitlines() if r and not r.startswith(";")]
    return [rows[k:k + 24] for k in range(0, len(rows), 24)]


def _stamped(pix, frame, x0, y0, keymap, flip=False):
    """the sprite pixels of frame (its keys mapped) that the picture does not show at (x0, y0)"""
    return [(x0 + k, y0 + j) for j, r in enumerate(frame) for k, c in enumerate(r[::-1] if flip else r)
            if c != "." and pix[y0 + j][x0 + k] != keymap[c]]


def test_the_finale_shows_dregs_not_a_second_bartender():
    """Dregs is his Pour-Off sprite (assets/art/dregs/dregs.txt, the v8 idle, the owner's), whole, feet on the cobble at y 93, by day:
    skin S (DMG 1), jacket B (the wall's lilac, DMG 2), ink. The contest picture shows him in the same place (shared tiles)."""
    idle = _frames("assets/art/dregs/dregs.txt")[0]
    for n in ("finale_a", "finale_contest"):
        key, pix = _pix(n)
        assert not _stamped(pix, idle, 142, 70, {"-": "S", "+": "B", "#": "#"}), n
        assert (key["S"]["dmg"], key["B"]["dmg"]) == (1, 2)
        assert "W" not in "".join(_region(pix, 142, 70, 158, 94)), "no white shirt or apron on Dregs"


def test_the_credits_dregs_mops_and_no_coffee_stand():
    """Dregs mops in front of the tavern in his v8 fill pose (unflipped, as the game shows it), feet on the cobble at y 93, by dawn:
    skin D, head and jacket B (the dawn violet), ink, the mop in his hands. The coffee stand is gone (owner, round 5: in every picture or
    in none) and nobody stands at the right house."""
    key, c = _pix("credits_b")
    fill = _frames("assets/art/dregs/dregs.txt")[3]
    off = _stamped(c, fill, 46, 70, {"-": "D", "+": "B", "#": "#"})
    assert all(36 <= x <= 46 and 85 <= y <= 93 for x, y in off), off[:5]          # (only where the mop crosses him)
    assert len(off) < 12
    assert PICS["credits_b"]["hud_cells"] == 0 and not set("CTGZ") & set(key)
    assert set("".join(_region(c, 141, 64, 159, 88))) <= set("B#")


def test_the_contest_picture_is_the_first_pour_courtyard_with_the_two_game_sprites_and_no_pour():
    """finale_contest = finale_a outside the first pour's Spigoteer (x 112-141, y 56-93) and the game Spigoteer's box: there the square is
    the town master's (intro_before's characters, finale_a's basin line), the Golden Spigot untouched, the ten owners along the bottom, nothing
    held up to the jet; the Spigoteer is the game's idle sprite (flipped, facing Dregs) in front of the tavern, Dregs as in finale_a."""
    key, a = _pix("finale_a")
    key2, b = _pix("finale_contest")
    _, night = _pix("intro_before")
    assert key == key2
    for y in range(104):
        for x in range(160):
            in_spot = 112 <= x <= 141 and 56 <= y <= 93
            in_sal = 59 <= x <= 74 and 71 <= y <= 94
            if not (in_spot or in_sal):
                assert a[y][x] == b[y][x], (x, y)
            elif 112 <= x <= 140 and 56 <= y <= 87:
                assert b[y][x] == (a[y][x] if y == 87 and x <= 126 else night[y][x]), (x, y)
    assert _region(a, 88, 6, 119, 40) == _region(b, 88, 6, 119, 40)             # the Golden Spigot, whole
    assert _region(a, 0, 95, 160, 104) == _region(b, 0, 95, 160, 104)          # the owners
    assert not any("S" in r[112:137] for r in b[58:80])                         # nobody holds a glass up to the right jet
    sal = _frames("assets/art/bartender.txt")[0]
    assert not _stamped(b, sal, 59, 71, {"-": "W", "+": "S", "#": "#"}, flip=True)
    assert key["W"]["dmg"] == 0 and key["S"]["dmg"] == 1


def test_the_finale_spigoteer_wears_the_cream_wooly_cap_and_his_mustache_shows():
    """Owner 2026-10-20: Aurora knits a cream wooly (newsboy) cap. The owner redrew it 2026-10-29 (Q42: shading in gold
    y). Town round 6 (approved, Q74): the joined hall's lilac wall stands behind the crown now and the crown's gold shading and the
    lilac are both DMG 2, so the crown is all sunlit cream Y; an ink brim line at row 71, no pink on him, and the mustache rows are ink."""
    key, pix = _pix("finale_a")
    hat = _region(pix, 127, 65, 139, 72)
    cap = "".join(hat)
    assert cap.count("Y") >= 15 and "#" * 10 in hat[6]
    assert "r" not in "".join(_region(pix, 124, 64, 142, 90)), "no pink on the Spigoteer"
    face = _region(pix, 128, 72, 138, 82)
    assert "r" not in "".join(face) and "#####" in face[5], "the mustache (ink) is uncovered"
