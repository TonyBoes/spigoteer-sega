# M11b story mode: the script build (tools/gen_story.py), the cut-scenes (src/story.c), the chapter goals, the story
# progress in SRAM and the title's CONTINUE. Story shifts: each chapter's Opening / Happy hour / Last call (the
# mini-game and boss slots skipped), their banners, goals, pace and arrival patterns, SRAM version 4 (the step
# reached) and the version 3 -> 4 migration. Story lives: 3 per venue carried through its shifts, a venue restart on
# the last one, the strict rules' 2 lives and their cue, the gold medal's bonus life, CONTINUE at the venue's start.
import importlib.util
import json
import re

import pytest
from conftest import GAME, ROOT, check_golden, hold_stage_anim
from test_flow import (GAME_OVER, GS_GOAL, GS_STORY, LEVEL_CLEAR, LIFE_LOST, PLAYING, TITLE, inject_mug, lose_a_life, run_until,
                       settle_title, state, tilemap_row)
from test_scores import V4_SUM, booted, parse_save, table, v1_image, v2_image, v3_image, v4_image
from test_sound import save_ram

pytestmark = pytest.mark.timeout(240)

STORY = json.loads((ROOT / "build" / "story.json").read_text())
PORTRAIT_CFG = json.loads((ROOT / "assets" / "story" / "portraits.json").read_text())
PORTRAITS = STORY["portraits"]               # every portrait (a speaker's own and his variants): approved portrait-v2 art
APPROVED = list(PORTRAITS)
SCENES = STORY["scenes"]
SC = {s["id"]: i for i, s in enumerate(SCENES)}
CHAPTERS = STORY["chapters"]
SHIFTS = STORY["shifts"]                    # per chapter: opening, happy hour, last call
SHIFT_NAMES = STORY["shift_names"]
SEQ = STORY["sequence"]
SHIFT_STEP = [next(i for i, s in enumerate(SEQ) if s["kind"] == "SHIFT" and s["index"] == k) for k in range(3)]
BOSS_STEP = next(i for i, s in enumerate(SEQ) if s["kind"] == "BOSS")
BOSS_BUILT = {c for c, steps in enumerate(STORY["steps"]) if steps[BOSS_STEP]["built"]}   # chapters whose boss is in
PATTERNS = {p["name"]: p for p in STORY["patterns"]}
GLYPH = STORY["glyphs"]
FONT = STORY["font"]
SPEAKERS = STORY["speakers"]
STORY_STEPS = len(SEQ)
G_SERVE, G_CATCH, G_CLEAR = 0, 1, 2
F_NO_TAP, F_NO_BREAK = 1, 2
SP_SCENE, SP_GOAL, SP_PLAY, SP_FAIL = 1, 2, 3, 4
BOX_ROW, TEXT_ROW = 13, 14
TAP_X = GAME["TAP_X"]
CHARSET = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,!?'-: ")
GAME_ART = {m[0]: int(m[1]) for m in re.findall(r"#define (TILE_\w+) (\d+)", (ROOT / "build" / "art.h").read_text())}
BANKS = {p[1]: int(p[2], 16) for p in (l.split() for l in (ROOT / "build" / "game.noi").read_text().splitlines())
         if len(p) == 3 and p[1].startswith("b_")}


def pre(c):
    return SC["PRE_SALOON"] + 2 * c


def post(c):
    return SC["POST_SALOON"] + 2 * c


def gen_story():
    spec = importlib.util.spec_from_file_location("gen_story", ROOT / "tools" / "gen_story.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ---- (a) the script build ------------------------------------------------------------------------------------
def test_the_script_fits_the_text_box_and_the_font():
    assert len(SCENES) == 21 and SCENES[0]["id"] == "INTRO" and SCENES[-1]["id"] == "CREDITS"
    for s in SCENES:
        assert s["pages"], s["id"]
        assert len(s["title"]) <= 20 and set(s["title"]) <= CHARSET, s["id"]
        for p in s["pages"]:
            assert p["speaker"] in SPEAKERS, s["id"]
            assert 1 <= len(p["lines"]) <= 3, s["id"]
            for line in p["lines"]:
                assert len(line) <= 18 and set(line) <= CHARSET, (s["id"], line)
    # every character of the font has a tile: A-Z 0-9 the HUD's, the punctuation the story font's
    assert set(GLYPH) == CHARSET
    assert len({GLYPH[c] for c in CHARSET}) == len(CHARSET), "no two characters share a glyph"
    assert all(FONT["glyph_" + n] == GLYPH[c] for c, n in (
        (".", "period"), (",", "comma"), ("!", "excl"), ("?", "quest"), ("'", "apos"), ("-", "hyphen"), (":", "colon")))
    # the size the report quotes: the whole script is a few KB, kept uncompressed
    assert STORY["text_bytes"] < 7000 and STORY["pages"] == sum(len(s["pages"]) for s in SCENES)


def test_the_script_matches_docs_story_md():
    md = (ROOT / "docs" / "story.md").read_text()
    for s in SCENES:
        for p in s["pages"]:
            assert "\n".join([p["speaker"]] + p["lines"]) in md, (s["id"], p["lines"])
    # the factory serves batteries now (owner change): no oil left in the script
    assert "OIL" not in md.upper().replace("TOILET", "") and "EMPTY BATTERIES." in md


@pytest.mark.parametrize("bad, why", [
    ("THIS LINE IS TOO LONG", "characters (max 18)"),
    ("WHAT; NO", "outside the font"),
    ("lower case", "outside the font"),
])
def test_the_build_fails_on_a_bad_line(tmp_path, bad, why):
    g = gen_story()
    md = (ROOT / "docs" / "story.md").read_text().replace("ONCE UPON A TAP,", bad, 1)
    f = tmp_path / "story.md"
    f.write_text(md)
    with pytest.raises(g.StoryError, match=why.replace("(", r"\(").replace(")", r"\)")):
        g.parse_script(f)


def test_the_build_fails_on_an_unknown_speaker_or_a_fourth_line(tmp_path):
    g = gen_story()
    md = (ROOT / "docs" / "story.md").read_text()
    f = tmp_path / "story.md"
    f.write_text(md.replace("SADIE\nHOWDY, STRANGER!", "SALLY\nHOWDY, STRANGER!", 1))
    with pytest.raises(g.StoryError, match="unknown speaker"):
        g.parse_script(f)
    f.write_text(md.replace("WELCOME TO MY BAR.\n", "WELCOME TO MY BAR.\nAND A FOURTH LINE\n", 1))
    with pytest.raises(g.StoryError, match="4 lines"):
        g.parse_script(f)
    f.write_text(md.replace('"Keep 15 cowboys happy" / serve 15', '"Keep 16 cowboys happy" / serve 16', 1))
    with pytest.raises(g.StoryError, match="chapter 1"):
        g.parse_script(f)


def test_the_chapter_goals_follow_the_chapters_table():
    want = [(G_SERVE, 15, 0, 0), (G_SERVE, 20, F_NO_TAP, 0), (G_SERVE, 18, 0, 0), (G_SERVE, 20, 0, 120),
            (G_SERVE, 20, 0, 120), (G_CATCH, 25, 0, 0), (G_CLEAR, 0, F_NO_BREAK, 0), (G_SERVE, 25, 0, 0),
            (G_SERVE, 30, 0, 0)]
    assert [(c["type"], c["count"], c["flags"], c["secs"]) for c in CHAPTERS] == want
    assert [c["venue"] for c in CHAPTERS] == list(range(9))


def test_the_cut_scene_budget():
    """Every scene's portraits fit the free BG ids (the patron range up) and OBJ ids together."""
    assert STORY["font_base"] == 77 and STORY["portrait_base"] == 77 + 16 and STORY["bg_budget"] == 256 - 93
    for s in SCENES:
        assert s["bg_tiles"] <= STORY["bg_budget"] and s["obj_tiles"] <= STORY["obj_budget"], s["id"]
        assert len(s["spk"]) <= 3, s["id"]
    # every speaker but the narrator has approved art (no placeholders left), the Spigoteer and Dregs a variant each
    assert sorted(p["speaker"] for p in PORTRAITS.values() if not p["variant"]) == sorted(SPEAKERS[:-1])
    assert {n: (p["speaker"], p["variant"]) for n, p in PORTRAITS.items() if p["variant"]} == \
        {"SPIGOTEER COZY": ("SPIGOTEER", "COZY"), "DREGS SORRY": ("DREGS", "SORRY")}
    for name, p in PORTRAITS.items():           # the approved 56x56 portraits (docs/story.md "Portraits")
        assert (p["w"], p["h"], p["x"], p["y"]) == (7, 7, 2, 6), f"{name}: 56x56 standing on the text box"
        assert p["tiles"] <= 44 and 1 <= p["pals"] <= 3 and p["obj"] == (1 if name == "SADIE" else 0), name
    # the busiest scenes: three portraits loaded together (FINALE: Sadie, the sorry Dregs, the cozy Spigoteer)
    most = max(s["bg_tiles"] for s in SCENES)
    assert most <= STORY["bg_budget"]
    assert SCENES[SC["FINALE"]]["bg_tiles"] == most == sum(PORTRAITS[n]["tiles"] for n in
                                                           ("SADIE", "DREGS SORRY", "SPIGOTEER COZY"))


def portrait_cfg(name):
    """portraits.json's entry of a portrait (a variant's: its own art, the speaker's place)."""
    p = PORTRAITS[name]
    c = PORTRAIT_CFG[p["speaker"]]
    return c["variants"][p["variant"]] if p["variant"] else c


def test_the_portrait_v2_converter_is_exact_or_fails(tmp_path):
    """Each approved source converts to tiles + a palette map that give back every source pixel's colour; a tile
    with two colours on one DMG shade, or a fourth palette, fails the build."""
    g = gen_story()
    for name in APPROVED:
        path = ROOT / portrait_cfg(name)["art"]
        assert PORTRAITS[name]["art"] == portrait_cfg(name)["art"]
        key, pix, _ = g.parse_v2(path)
        px, attr, pals, cells, opals, lay = g.read_v2(path)
        for y, row in enumerate(pix):
            for x, c in enumerate(row):
                k = key[c]
                base = key[k["obj"]] if k["obj"] else k
                assert px[y][x] == base["dmg"], (name, x, y)
                assert pals[attr[(y // 8) * 7 + x // 8]][px[y][x]] == base["hex"], (name, x, y)
                if k["obj"]:
                    assert opals[0][lay[y][x]] == k["hex"], (name, x, y)
        assert sum(sum(1 for v in r if v) for _, _, cell in cells for r in cell) == \
            sum(1 for r in pix for c in r if key[c]["obj"]), f"{name}: the overlay covers every accent pixel"
    f = tmp_path / "p.txt"
    keys = "@key\na 0 #f8d0a8 skin\nb 0 #00ff00 green\nc 0 #0000f8 blue\nd 0 #f80000 red\n# 3 #000000 ink\n@pixels\n"
    f.write_text("@size 8 8\n" + keys + "ab######\n" + "########\n" * 7)
    with pytest.raises(g.StoryError, match="two colours on DMG shade 0"):
        g.read_v2(f)
    f.write_text("@size 32 8\n" + keys + ("aaaaaaaabbbbbbbbccccccccdddddddd\n" * 8))
    with pytest.raises(g.StoryError, match=r"needs 4 CGB BG palettes \(max 3\)"):
        g.read_v2(f)
    f.write_text("@size 24 8\n@maxpal 2\n" + keys + ("aaaaaaaabbbbbbbbcccccccc\n" * 8))
    with pytest.raises(g.StoryError, match=r"needs 3 CGB BG palettes \(max 2\)"):
        g.read_v2(f)


def test_the_portrait_variants_follow_the_script():
    """The Spigoteer wears the cozy from the page after Aurora knits it (PRE_IGLOO page 3, his thank-you) to the end
    of the game; Dregs's sorry portrait is his apology in the FINALE (his only page there). Data, not scene checks:
    portraits.json 'variants', resolved per page by gen_story."""
    knit = SCENES[SC["PRE_IGLOO"]]["pages"]
    assert knit[1]["speaker"] == "AURORA" and knit[1]["lines"][-1] == "MUSTACHE COZY!"
    assert knit[2]["speaker"] == "SPIGOTEER" and knit[2]["lines"][0] == "IT'S... VERY COZY."
    seen = [(i, k, p["portrait"]) for i, s in enumerate(SCENES) for k, p in enumerate(s["pages"])
            if p["speaker"] == "SPIGOTEER"]
    first = (SC["PRE_IGLOO"], 2)
    assert all(n == ("SPIGOTEER COZY" if (i, k) >= first else "SPIGOTEER") for i, k, n in seen)
    assert any(i == SC["FINALE"] and n == "SPIGOTEER COZY" for i, _, n in seen), "the cozy is still on in the FINALE"
    sorry = [(s["id"], k) for s in SCENES for k, p in enumerate(s["pages"]) if p["portrait"] == "DREGS SORRY"]
    assert sorry == [("FINALE", 3)] and SCENES[SC["FINALE"]]["pages"][3]["lines"][0] == "SORRY I BROKE IT."
    assert [p["portrait"] for s in SCENES for p in s["pages"] if p["speaker"] == "DREGS"].count("DREGS") == \
        sum(1 for s in SCENES for p in s["pages"] if p["speaker"] == "DREGS") - 1
    for s in SCENES:                             # every other speaker shows his own portrait, the narrator none
        for p in s["pages"]:
            if p["speaker"] == "NARRATOR":
                assert p["portrait"] is None
            elif p["speaker"] not in ("SPIGOTEER", "DREGS"):
                assert p["portrait"] == p["speaker"]


@pytest.mark.parametrize("change, why", [
    (("SPIGOTEER", "COZY", "from", "PRE_IGLOO:2"), "page 2 of PRE_IGLOO is not SPIGOTEER's"),
    (("SPIGOTEER", "COZY", "from", "PRE_GLOO:3"), "names no scene"),
    (("SPIGOTEER", "COZY", "from", "PRE_IGLOO:9"), "has pages 1-5"),
    (("SPIGOTEER", "COZY", "from", "CREDITS"), "no page of SPIGOTEER"),
    (("DREGS", "SORRY", "to", "POST_ZOO"), "'to' comes before 'from'"),
    (("DREGS", "SORRY", "art", "assets/story/portraits/nobody.txt"), "not a portrait-v2 source"),
])
def test_the_build_fails_on_a_bad_variant(change, why):
    g = gen_story()
    scenes = g.parse_script(ROOT / "docs" / "story.md")
    cfg = json.loads(json.dumps(PORTRAIT_CFG))
    spk, var, k, v = change
    cfg[spk]["variants"][var][k] = v
    with pytest.raises(g.StoryError, match=re.escape(why)):
        g.assign_portraits(scenes, g.portraits(cfg))
    # two variants of one speaker on the same page
    cfg = json.loads(json.dumps(PORTRAIT_CFG))
    cfg["DREGS"]["variants"]["AGAIN"] = dict(cfg["DREGS"]["variants"]["SORRY"])
    with pytest.raises(g.StoryError, match="is already DREGS SORRY"):
        g.assign_portraits(scenes, g.portraits(cfg))


# ---- page text variants (owner, 2026-10-10: Hana's POST_TEAHOUSE thanks depend on the teahouse run) ----------------
NOT_ONE = ["NOT ONE CUP", "BROKEN. THAT IS", "RARE. THANK YOU."]
SO_FEW = ["SO FEW CUPS", "BROKEN. THAT IS", "RARE. THANK YOU."]


def test_the_page_text_variants_follow_the_script():
    """docs/story.md "HANA IF GLASS_BROKEN": the only text variant so far, on POST_TEAHOUSE page 1; data, one condition
    id per variant page (GLASS_BROKEN = 1, bit 0 of story_conds)."""
    assert STORY["conditions"] == {"GLASS_BROKEN": 1}
    hana = SCENES[SC["POST_TEAHOUSE"]]["pages"][0]
    assert hana["speaker"] == "HANA" and hana["lines"] == NOT_ONE
    assert hana["variants"] == [{"cond": "GLASS_BROKEN", "lines": SO_FEW}]
    assert [(s["id"], k) for s in SCENES for k, p in enumerate(s["pages"]) if p["variants"]] == [("POST_TEAHOUSE", 0)]
    md = (ROOT / "docs" / "story.md").read_text()
    assert "\n".join(["HANA"] + NOT_ONE + ["", "HANA IF GLASS_BROKEN"] + SO_FEW) in md


@pytest.mark.parametrize("old, new, why", [
    ("HANA IF GLASS_BROKEN\nSO FEW", "HANA IF CUP_SMASHED\nSO FEW", "unknown condition 'CUP_SMASHED'"),
    ("HANA IF GLASS_BROKEN\nSO FEW", "DREGS IF GLASS_BROKEN\nSO FEW", "the variant's speaker must be the page's (HANA)"),
    ("HANA IF GLASS_BROKEN\nSO FEW CUPS", "HANA IF GLASS_BROKEN\nNOT ONE CUP", "the same text as the page"),
    ("HANA IF GLASS_BROKEN\nSO FEW CUPS", "HANA IF GLASS_BROKEN\nSO FEW CUPS AND SAUCERS", "characters (max 18)"),
    ("HANA\nNOT ONE CUP\nBROKEN. THAT IS\nRARE. THANK YOU.\n\n", "", "needs the page it replaces right above it"),
    ("THANK YOU.\n\nHANA IF GLASS_BROKEN\nSO FEW CUPS\nBROKEN. THAT IS\nRARE. THANK YOU.\n",
     "THANK YOU.\n\nHANA IF GLASS_BROKEN\nSO FEW CUPS\nBROKEN. THAT IS\nRARE. THANK YOU.\n\n"
     "HANA IF GLASS_BROKEN\nA FEW CUPS\nBROKEN.\n", "a second variant IF GLASS_BROKEN"),
], ids=["condition", "speaker", "same-text", "long-line", "first-page", "twice"])
def test_the_build_fails_on_a_bad_text_variant(tmp_path, old, new, why):
    g = gen_story()
    md = (ROOT / "docs" / "story.md").read_text()
    assert old in md
    f = tmp_path / "story.md"
    f.write_text(md.replace(old, new, 1))
    with pytest.raises(g.StoryError, match=re.escape(why)):
        g.parse_script(f)


def test_every_speaker_needs_art_and_the_scene_budget_fails_the_build():
    g = gen_story()
    cfg = json.loads(json.dumps(PORTRAIT_CFG))
    del cfg["KIKI"]["art"]                       # no placeholders any more
    with pytest.raises(g.StoryError, match="no art for KIKI"):
        g.portraits(cfg)
    cfg = json.loads(json.dumps(PORTRAIT_CFG))
    cfg["KIKI"]["tint"] = ["#ffffff"] * 4        # the placeholders' old key
    with pytest.raises(g.StoryError, match="unknown portraits.json keys"):
        g.portraits(cfg)
    scenes = g.parse_script(ROOT / "docs" / "story.md")
    ports = g.portraits(PORTRAIT_CFG)
    g.assign_portraits(scenes, ports)
    most = max(s["bg_tiles"] for s in SCENES)
    g.scene_budget(scenes, ports, most)          # the real budget's tightest fit passes ...
    with pytest.raises(g.StoryError, match=f"FINALE: its portraits need {most} BG tiles, {most - 1} are free"):
        g.scene_budget(scenes, ports, most - 1)  # ... one tile less fails the build


# ---- helpers ------------------------------------------------------------------------------------------------
DMG_GREY = [(255, 255, 255), (153, 153, 153), (85, 85, 85), (0, 0, 0)]   # PyBoy's DMG shades


def q15(h):
    return tuple((int(h[i:i + 2], 16) >> 3) << 3 for i in (1, 3, 5))   # #rrggbb as the CGB shows it (RGB15)


_SOURCES = {}


def source(name):
    """The portrait's approved source: (key, pixel rows)."""
    if name not in _SOURCES:
        key, pix, _ = gen_story().parse_v2(ROOT / PORTRAITS[name]["art"])
        _SOURCES[name] = key, pix
    return _SOURCES[name]


def assert_portrait_exact(gb, name):
    """The 56x56 picture on screen is the approved source pixel for pixel: on DMG each key's shade, on CGB each key's
    colour (the BG palettes through the per-tile map, the OBJ accent over them)."""
    key, pix = source(name)
    p = STORY["portraits"][name]
    x0, y0 = p["x"] * 8, p["y"] * 8
    im = gb.image()
    bad = []
    for y, row in enumerate(pix):
        for x, c in enumerate(row):
            k = key[c]
            if gb.model_name == "cgb":
                want = q15(k["hex"])
            else:
                want = DMG_GREY[(key[k["obj"]] if k["obj"] else k)["dmg"]]
            if im.getpixel((x0 + x, y0 + y)) != want:
                bad.append((x, y, c))
    assert not bad, f"{name}: {len(bad)} pixels differ from the source, first {bad[:8]}"
    assert gb.mem("story_cur") == PORTRAITS[name]["pid"], name


def assert_on_the_box(gb, p):
    """A 56x56 frame: top row, sides down to row 12, no bottom row (the text box's top panel is its bottom edge)."""
    x, y, w, h = p["x"], p["y"], p["w"], p["h"]
    assert tilemap_row(gb, y - 1, x - 1, w + 2) == [FONT["frame_tl"]] + [FONT["frame_t"]] * w + [FONT["frame_tr"]]
    for r in range(h):
        assert tilemap_row(gb, y + r, x - 1, 1) == [FONT["frame_l"]]
        assert tilemap_row(gb, y + r, x + w, 1) == [FONT["frame_r"]]
    assert y + h == BOX_ROW
    frame = {FONT[n] for n in FONT if n.startswith("frame")}
    assert not frame & set(tilemap_row(gb, BOX_ROW, 0, 20)), "the box's top panel is not overdrawn"


def overlay_sprites(gb):
    return len(gb.visible_sprites()) - 4                  # the Spigoteer's sprite takes 4


def settle(gb):
    """A screen change (LCD off) takes several frames, and the game reads no keys meanwhile: wait for the LCD."""
    gb.run(1)
    run_until(gb, lambda: gb.pb.memory[0xFF40] & 0x80, 60)
    gb.run(2)


def page_ready(gb):
    """Show the whole page (A while it types), then let the queue drain."""
    if gb.mem("story_typed") < 54:
        gb.press("a", 2)
    run_until(gb, lambda: gb.mem("story_swap") == 0, 30)
    gb.run(3)


def text_rows(gb):
    return [tilemap_row(gb, TEXT_ROW + r, 1, 18) for r in range(3)]


def glyph_rows(lines):
    lines = list(lines) + [""] * (3 - len(lines))
    return [[GLYPH[c] for c in l.ljust(18)] for l in lines]


def start_story(model, ram=None, cont=False):
    rom = booted(model, ram)
    hold_stage_anim(rom)
    rom.press("down", 2)
    if cont:
        assert rom.mem("title_n") == 4
        rom.press("down", 2)
    rom.press("a", 2)
    run_until(rom, lambda: state(rom) == GS_STORY and rom.mem("story_phase") == SP_SCENE, 30)
    settle(rom)
    return rom


def skip_scene(gb):
    s = gb.mem("story_scene")
    gb.press("start", 2)
    run_until(gb, lambda: gb.mem("story_scene") != s or state(gb) in (GS_GOAL, TITLE), 30)
    settle(gb)


def to_goal(gb):
    """Past the goal banner (A), into the shift's play."""
    run_until(gb, lambda: state(gb) == GS_GOAL, 30)
    gb.write("tip_chance", 0)
    gb.press("a", 2)
    run_until(gb, lambda: state(gb) == PLAYING, 10)
    return gb


def to_chapter(model, c, banner=False):
    """A rom in chapter c's opening shift, just past the goal banner (banner=True: still on it; a save with c
    chapters cleared: CONTINUE)."""
    if c:
        rom = start_story(model, v4_image([], story=c), cont=True)
    else:
        rom = start_story(model)
        skip_scene(rom)                                   # INTRO
    assert rom.mem("story_scene") == pre(c) and rom.mem("story_chapter") == c
    skip_scene(rom)                                       # the PRE scene
    if banner:
        run_until(rom, lambda: state(rom) == GS_GOAL, 30)
        rom.run(2)
        return rom
    return to_goal(rom)


def to_shift(model, c, k, banner=False):
    """A rom in chapter c's shift k with 3 lives, past the banner (banner=True: still on it). CONTINUE from a save
    that reached the shift's step opens the venue's Opening banner (no PRE scene); the Opening is then won with
    story_step poked to the step before shift k, so the next playable step is k's (one SHIFT CLEAR)."""
    if k == 0:
        return to_chapter(model, c, banner)
    rom = booted(model, v4_image([], story=c, step=SHIFT_STEP[k]))
    hold_stage_anim(rom)
    rom.press("down", 2)
    rom.press("down", 2)
    rom.press("a", 2)                                     # CONTINUE: the venue's Opening
    run_until(rom, lambda: state(rom) == GS_GOAL, 60)
    assert rom.mem("story_chapter") == c and rom.mem("story_shift") == 0 and rom.mem("story_step") == 0
    to_goal(rom)
    rom.write("story_step", SHIFT_STEP[k] - 1)
    win(rom, c, 0)
    run_until(rom, lambda: state(rom) == LEVEL_CLEAR, 20)
    run_until(rom, lambda: state(rom) == GS_GOAL, 300)
    rom.run(2)
    assert rom.mem("story_chapter") == c and rom.mem("story_shift") == k and rom.mem("story_step") == SHIFT_STEP[k]
    assert rom.mem("lives") == 3
    return rom if banner else to_goal(rom)


def clear_bars(gb):
    """Nobody left and the quota spawned: the level clears on the next frame."""
    gb.write("quota", gb.mem("spawned"))
    for i in range(16):
        gb.write(gb.addr("patron_state") + i, 0)
    gb.write("patrons_live", 0)
    for i in range(20):
        gb.write(gb.addr("mug_state") + i, 0)
    gb.write("mugs_live", 0)


def beat_the_boss(gb, c):
    """After chapter c's Last call was won: its boss fight, when it is built (tests/test_boss.py plays them for
    real), its banner passed and the boss satisfied at once (boss_hook 3), up to its CHAPTER CLEAR."""
    if c not in BOSS_BUILT:
        return
    run_until(gb, lambda: state(gb) == GS_GOAL, 400)
    to_goal(gb)
    gb.write("boss_hook", 3)
    run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 200)


def win(gb, c, k=0):
    sh = SHIFTS[c][k]
    if sh["type"] == G_SERVE:
        gb.write("served", sh["count"])
    elif sh["type"] == G_CATCH:
        gb.write("story_catches", sh["count"] - 1)
        gb.write("intro_timer", 0)
        inject_mug(gb, gb.mem("bar"), TAP_X + 1, st=2)     # an empty at the bartender: caught on the next frame
    else:
        clear_bars(gb)


# ---- (b) the cut-scenes ----------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_story_from_the_title_opens_the_intro(model):
    with start_story(model) as gb:
        assert gb.mem("story_on") == 1 and gb.mem("story_scene") == SC["INTRO"] and gb.mem("story_page") == 0
        assert gb.mem("lives") == 3 and int.from_bytes(gb.read("score", 4), "little") == 0
        page_ready(gb)
        assert text_rows(gb) == glyph_rows(SCENES[0]["pages"][0]["lines"])
        # the narrator: no portrait, the golden spigot on the box's top panel
        assert gb.mem("story_cur") == 255
        assert tilemap_row(gb, BOX_ROW, 2, 1) == [FONT["spigot_icon"]]
        # the picture slot (a placeholder): the scene's title on row 5
        title = SCENES[0]["title"]
        assert tilemap_row(gb, 5, (20 - len(title)) // 2, len(title)) == [GLYPH[c] for c in title]
        check_golden(gb, "story_narrator")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_types_then_turns_the_page_and_start_skips_the_scene(model):
    with start_story(model) as gb:
        pages = SCENES[0]["pages"]
        gb.run(2)
        t0 = gb.mem("story_typed")
        gb.run(5)
        assert 0 < gb.mem("story_typed") - t0 <= 10, "the text types on, one character a frame (spaces free)"
        gb.press("a", 2)
        gb.run(2)
        assert gb.mem("story_typed") == 54 and gb.mem("story_page") == 0, "A shows the rest of the page first"
        assert text_rows(gb) == glyph_rows(pages[0]["lines"])
        gb.press("a", 2)
        gb.run(2)
        assert gb.mem("story_page") == 1 and gb.mem("story_typed") < 54, "then A turns the page"
        gb.press("b", 2)
        gb.run(2)
        assert gb.mem("story_typed") == 54, "B shows the page at once too"
        gb.run(3)
        assert text_rows(gb) == glyph_rows(pages[1]["lines"])
        gb.press("b", 2)
        gb.run(2)
        assert gb.mem("story_page") == 2
        skip_scene(gb)
        assert gb.mem("story_scene") == SC["PRE_SALOON"] and gb.mem("story_page") == 0, "START skips the scene"
        assert state(gb) == GS_STORY


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_venue_scene_has_the_backdrop_the_spigoteer_and_a_framed_portrait(model):
    with start_story(model) as gb:
        skip_scene(gb)
        page_ready(gb)
        sadie = STORY["portraits"]["SADIE"]
        assert SPEAKERS[gb.mem("story_cur")] == "SADIE"
        base = STORY["portrait_base"]               # SADIE is the scene's first portrait speaker
        assert SCENES[SC["PRE_SALOON"]]["spk"][0] == SPEAKERS.index("SADIE")
        x, y, w, h = sadie["x"], sadie["y"], sadie["w"], sadie["h"]
        for r in range(h):
            assert tilemap_row(gb, y + r, x, w) == [base + t for t in sadie["map"][r * w:(r + 1) * w]]
        assert_on_the_box(gb, sadie)
        assert_portrait_exact(gb, "SADIE")
        # the name on the panel, the title on the HUD row
        assert tilemap_row(gb, BOX_ROW, 2, 5) == [GLYPH[c] for c in "SADIE"]
        title = SCENES[SC["PRE_SALOON"]]["title"]
        assert tilemap_row(gb, 0, (20 - len(title)) // 2, len(title)) == [GLYPH[c] for c in title]
        # the Spigoteer's sprite at bar 1's tap; on CGB Sadie's gold star (1 OBJ), on DMG the BG star shows instead
        assert gb.mem("bar") == 1 and gb.mem("bartender_x") == TAP_X
        assert overlay_sprites(gb) == (1 if model == "cgb" else 0)
        check_golden(gb, "story_portrait")
        # SADIE -> SPIGOTEER (page 3): the same rectangle swapped, the star gone; then back to SADIE with her star
        gb.press("a", 2)
        page_ready(gb)
        gb.press("a", 2)
        page_ready(gb)
        assert_portrait_exact(gb, "SPIGOTEER")
        assert overlay_sprites(gb) == 0
        gb.press("a", 2)
        page_ready(gb)
        assert_portrait_exact(gb, "SADIE")
        assert_on_the_box(gb, sadie)
        assert overlay_sprites(gb) == (1 if model == "cgb" else 0)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_speaker_change_swaps_the_portrait_and_the_narrator_wipes_it(model):
    with to_shift(model, 0, 2) as gb:
        # chapter 1's last call -> win -> POST_SALOON: SADIE, SADIE, DREGS, NARRATOR, SPIGOTEER
        win(gb, 0, 2)
        beat_the_boss(gb, 0)
        run_until(gb, lambda: state(gb) == GS_STORY and gb.mem("story_scene") == post(0), 400)
        pages = SCENES[post(0)]["pages"]
        assert [p["speaker"] for p in pages] == ["SADIE", "SADIE", "DREGS", "NARRATOR", "SPIGOTEER"]
        for k in range(2):
            page_ready(gb)
            gb.press("a", 2)
        page_ready(gb)
        assert gb.mem("story_page") == 2 and SPEAKERS[gb.mem("story_cur")] == "DREGS"
        dregs = STORY["portraits"]["DREGS"]
        assert dregs["obj"] == 0 and overlay_sprites(gb) == 0
        assert_portrait_exact(gb, "DREGS")
        assert_on_the_box(gb, dregs)
        check_golden(gb, "story_dregs")
        rows = range(dregs["y"] - 1, BOX_ROW)          # the frame's rows (its bottom edge is the box's panel)
        rect = [tilemap_row(gb, r, dregs["x"] - 1, dregs["w"] + 2) for r in rows]
        gb.press("a", 2)                               # NARRATOR: the frame wipes back to the backdrop
        page_ready(gb)
        assert gb.mem("story_cur") == 255 and len(gb.visible_sprites()) == 4
        after = [tilemap_row(gb, r, dregs["x"] - 1, dregs["w"] + 2) for r in rows]
        story_ids = range(STORY["font_base"], 256)
        assert all(t not in story_ids for row in after for t in row), "no frame or portrait tile left"
        assert after != rect
        gb.press("a", 2)                               # SPIGOTEER: a new frame
        page_ready(gb)
        assert SPEAKERS[gb.mem("story_cur")] == "SPIGOTEER"
        sp = STORY["portraits"]["SPIGOTEER"]
        assert tilemap_row(gb, sp["y"] - 1, sp["x"] - 1, 1) == [FONT["frame_tl"]]
        assert_portrait_exact(gb, "SPIGOTEER")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_coach_and_the_spigoteer_swap_cleanly(model):
    """PRE_STADIUM: COACH -> SPIGOTEER -> COACH, each the approved art pixel for pixel in the same framed slot on the
    box, no overlay sprite (only Sadie has one)."""
    with start_story(model, v4_image([], story=1), cont=True) as gb:
        assert gb.mem("story_scene") == SC["PRE_STADIUM"]
        page_ready(gb)
        assert_portrait_exact(gb, "COACH")
        assert overlay_sprites(gb) == 0
        for _ in range(2):
            gb.press("a", 2)
            page_ready(gb)
        assert_portrait_exact(gb, "SPIGOTEER")
        assert_on_the_box(gb, PORTRAITS["SPIGOTEER"])
        assert overlay_sprites(gb) == 0
        check_golden(gb, "story_spigoteer")
        gb.press("a", 2)
        page_ready(gb)
        assert_portrait_exact(gb, "COACH")
        assert_on_the_box(gb, PORTRAITS["COACH"])
        assert overlay_sprites(gb) == 0


# every scene, page by page (test_every_page_shows_its_portrait): a few pages also keep a golden
TOUR_GOLDENS = {("PRE_IGLOO", 0): "story_aurora", ("PRE_IGLOO", 2): "story_spigoteer_cozy",
                ("PRE_SPACE", 2): "story_zizz", ("FINALE", 3): "story_dregs_sorry"}
PID_NAME = {p["pid"]: n for n, p in PORTRAITS.items()}


def portrait_pairs(sids=None):
    """(portrait on screen, the next page's other portrait) for every direct swap in the scenes (default: the whole
    script; no narrator page between them)."""
    out = set()
    for s in SCENES:
        if sids is not None and s["id"] not in sids:
            continue
        cur = None
        for p in s["pages"]:
            if p["portrait"] and cur and p["portrait"] != cur:
                out.add((cur, p["portrait"]))
            cur = p["portrait"]
    return out


def tour_scene(gb, sid, seen):
    """Every page of the scene on screen: the page's portrait (the speaker's own or his variant) pixel for pixel,
    framed on the box, its tile map the scene's copy of its tiles (nothing of the previous one left), the name tag;
    a narrator page: no portrait, the frame wiped. Records the swaps seen in `seen`."""
    s = SCENES[SC[sid]]
    assert gb.mem("story_scene") == SC[sid] and gb.mem("story_page") == 0
    base, first = STORY["portrait_base"], {}
    for pid in s["spk"]:                         # the scene's portraits, loaded one after the other at its start
        first[pid] = base
        base += PORTRAITS[PID_NAME[pid]]["tiles"]
    rect = (1, 5, 9, 8)                          # the 56x56 frame: columns 1-9, rows 5-12 (its bottom is the box)
    spigoteer = 4 if s["venue"] != 255 else 0    # his sprite at the tap (a venue scene; a picture scene has none)
    cur = None
    for k, page in enumerate(s["pages"]):
        if k:
            gb.press("a", 2)
        page_ready(gb)
        assert gb.mem("story_page") == k, (sid, k)
        name = page["portrait"]
        if name is None:
            assert gb.mem("story_cur") == 255, (sid, k)
            rows = [tilemap_row(gb, r, rect[0], rect[2]) for r in range(rect[1], rect[1] + rect[3])]
            if s["venue"] != 255:                # the venue backdrop: no story tile
                assert not any(t in range(STORY["font_base"], 256) for row in rows for t in row), \
                    f"{sid} page {k + 1}: the frame is wiped"
            else:                                # the picture slot back as it was drawn
                pic = STORY["pictures"][s["pic"]]["map"]
                assert rows == [pic[r * 20 + rect[0]:r * 20 + rect[0] + rect[2]]
                                for r in range(rect[1], rect[1] + rect[3])], f"{sid} page {k + 1}: the frame is wiped"
            assert len(gb.visible_sprites()) == spigoteer
        else:
            p = PORTRAITS[name]
            assert_portrait_exact(gb, name)
            assert_on_the_box(gb, p)
            b = first[p["pid"]]
            for r in range(p["h"]):
                assert tilemap_row(gb, p["y"] + r, p["x"], p["w"]) == \
                    [b + t for t in p["map"][r * p["w"]:(r + 1) * p["w"]]], f"{sid} page {k + 1} row {r}"
            assert tilemap_row(gb, BOX_ROW, 2, len(page["speaker"])) == [GLYPH[c] for c in page["speaker"]]
            assert len(gb.visible_sprites()) - spigoteer == (1 if name == "SADIE" and gb.model_name == "cgb" else 0)
            if cur and cur != name:
                seen.add((cur, name))
        if (sid, k) in TOUR_GOLDENS:
            check_golden(gb, TOUR_GOLDENS[(sid, k)])
        cur = name


@pytest.mark.parametrize("c", range(9))
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_every_page_shows_its_portrait(model, c):
    """Chapter c's PRE and POST scenes (chapter 1 also the INTRO, chapter 9 the FINALE), every page in the real
    cut-scene: all 13 portraits pixel-exact on DMG and CGB, every swap between two portraits the script makes."""
    seen = set()
    if c == 0:
        gb = start_story(model)
        tour_scene(gb, "INTRO", seen)
        skip_scene(gb)
    else:
        gb = start_story(model, v4_image([], story=c), cont=True)
    with gb:
        tour_scene(gb, SCENES[pre(c)]["id"], seen)
        skip_scene(gb)                           # the PRE scene -> the Opening; won as the chapter's last step
        to_goal(gb)
        gb.write("story_step", STORY_STEPS - 1)
        win(gb, c, 0)
        run_until(gb, lambda: state(gb) == GS_STORY and gb.mem("story_scene") == post(c), 400)
        settle(gb)
        tour_scene(gb, SCENES[post(c)]["id"], seen)
        if c == 8:
            skip_scene(gb)
            tour_scene(gb, "FINALE", seen)
    sids = (["INTRO"] if c == 0 else []) + [SCENES[pre(c)]["id"], SCENES[post(c)]["id"]] + (["FINALE"] if c == 8 else [])
    assert seen == portrait_pairs(sids)


def test_the_tour_covers_every_portrait_and_swap():
    """What test_every_page_shows_its_portrait walks: every scene with a portrait is in it (CREDITS has none), so it
    shows all 13 portraits and all the swaps of the script."""
    toured = {"INTRO", "FINALE"} | {SCENES[pre(c)]["id"] for c in range(9)} | {SCENES[post(c)]["id"] for c in range(9)}
    assert {s["id"] for s in SCENES if s["spk"]} == toured
    assert {p["portrait"] for s in SCENES for p in s["pages"] if p["portrait"]} == set(PORTRAITS)
    assert len(portrait_pairs()) == 27


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_manager_bot_s_portrait(model):
    with start_story(model, v4_image([], story=5), cont=True) as gb:
        assert gb.mem("story_scene") == SC["PRE_ROBOT"]
        page_ready(gb)
        assert_portrait_exact(gb, "MANAGER-BOT")
        assert_on_the_box(gb, STORY["portraits"]["MANAGER-BOT"])
        assert tilemap_row(gb, BOX_ROW, 2, 11) == [GLYPH[c] for c in "MANAGER-BOT"]
        check_golden(gb, "story_managerbot")


# ---- (c) chapters: shifts and goals ------------------------------------------------------------------------------
def banner_text(gb, row):
    return tilemap_row(gb, row, 0, 20, window=True)


def centred(s):
    row = [GLYPH[" "]] * 20
    for i, c in enumerate(s):
        row[(20 - len(s)) // 2 + i] = GLYPH[c]
    return row


def shift_title(c, k):
    return f"CHAPTER {c + 1} {SHIFT_NAMES[k]}"


def test_the_shift_data():
    """Opening about half the goal and slower, Happy hour the chapter goal as written, Last call faster with its own
    arrival pattern (nine different ones); the mini-game and boss slots are in the sequence, skipped until built."""
    assert SHIFT_NAMES == ["OPENING", "HAPPY HOUR", "LAST CALL"]
    assert [(s["kind"], s["index"], s["built"]) for s in SEQ] == [
        ("SHIFT", 0, True), ("SHIFT", 1, True), ("MINI", 0, False), ("SHIFT", 2, True), ("BOSS", 0, False)]
    assert SHIFT_STEP == [0, 1, 3]
    rows = gen_story().level_rows(ROOT / "src" / "level.c")
    for c, (op, happy, last) in enumerate(SHIFTS):
        ch = CHAPTERS[c]
        assert (happy["type"], happy["count"], happy["flags"], happy["secs"], happy["line1"], happy["line2"]) == (
            ch["type"], ch["count"], ch["flags"], ch["secs"], ch["line1"], ch["line2"])
        assert (happy["pattern"], happy["walk"], happy["spawn"]) == ("normal", 100, 100)
        size = [s["count"] or s["quota"] or rows[c][1] for s in (op, happy, last)]
        assert 0.4 <= size[0] / size[1] <= 0.6 and size[2] >= size[1], c
        assert (op["walk"], op["spawn"]) == (85, 115) and op["pattern"] == "normal"
        assert 105 <= last["walk"] <= 120 and 80 <= last["spawn"] <= 95 and last["pattern"] != "normal"
        assert op["type"] == happy["type"] == last["type"] and op["flags"] == happy["flags"] == last["flags"]
        for k, s in enumerate((op, happy, last)):
            assert len(shift_title(c, k)) <= 20
            for l in (s["line1"], s["line2"]):
                assert len(l) <= 20 and set(l) <= set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 "), (c, k, l)
    assert len({s[2]["pattern"] for s in SHIFTS}) == 9, "every venue's last call has its own arrival pattern"


def test_the_build_fails_on_a_shifts_table_mismatch(tmp_path):
    g = gen_story()
    md = (ROOT / "docs" / "story.md").read_text()
    f = tmp_path / "story.md"
    f.write_text(md.replace('"Serve 8 cowboys" / serve 8', '"Serve 9 cowboys" / serve 9', 1))
    with pytest.raises(g.StoryError, match="chapter 1 opening"):
        g.parse_script(f)
    f.write_text(md.replace("| Stairs down:", "| Zigzag:", 1))
    with pytest.raises(g.StoryError, match="chapter 1: the shifts table's last call"):
        g.parse_script(f)


def test_the_build_fails_on_a_last_call_that_is_not_harder(monkeypatch):
    g = gen_story()
    rows = g.shift_list()
    rows[0][2]["walk"] = 100
    with pytest.raises(g.StoryError, match="chapter 1: the last call"):
        g.check_shifts(rows)
    rows = g.shift_list()
    rows[1][2]["pattern"] = rows[0][2]["pattern"]
    with pytest.raises(g.StoryError, match="share a pattern"):
        g.check_shifts(rows)
    rows = g.shift_list()
    rows[3][0]["secs"] = 30                              # 10 chefs in 30 s: not enough of them even arrive
    with pytest.raises(g.StoryError, match="patrons arrive"):
        g.check_shifts(rows)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_goal_banner_names_the_shift_and_the_hud_counts(model):
    with start_story(model) as gb:
        skip_scene(gb)
        skip_scene(gb)
        run_until(gb, lambda: state(gb) == GS_GOAL, 30)
        gb.run(5)
        op = SHIFTS[0][0]
        assert banner_text(gb, 1) == centred("CHAPTER 1 OPENING")
        assert banner_text(gb, 2) == centred(op["line1"]) and banner_text(gb, 3) == centred(op["line2"])
        assert gb.mem("level") == 1 and gb.mem("cur_group") == 0 and gb.mem("quota") == 255
        assert gb.mem("story_step") == 0 and gb.mem("story_shift") == 0
        # the HUD: S + what is left (8) at columns 12-14
        assert tilemap_row(gb, 0, 12, 3) == [GLYPH["S"], GLYPH["0"], GLYPH["8"]]
        check_golden(gb, "story_goal")
        run_until(gb, lambda: state(gb) == PLAYING, 200)      # 3 s, then the level
        gb.write("served", 5)
        gb.run(3)
        assert gb.mem("story_left") == 3
        assert tilemap_row(gb, 0, 12, 3) == [GLYPH["S"], GLYPH["0"], GLYPH["3"]]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_last_call_banner(model):
    with to_shift(model, 8, 2, banner=True) as gb:
        gb.run(5)
        last = SHIFTS[8][2]
        assert banner_text(gb, 1) == centred("CHAPTER 9 LAST CALL")
        assert banner_text(gb, 2) == centred(last["line1"]) and banner_text(gb, 3) == centred(last["line2"])
        assert tilemap_row(gb, 0, 12, 3) == [GLYPH["S"], GLYPH["3"], GLYPH["2"]]
        check_golden(gb, "story_last_call")


def pace(gb):
    return gb.mem("patron_speed"), gb.mem("hurry_speed"), gb.mem16("spawn_interval"), gb.mem("pat_len")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("c", range(9))
def test_each_chapter_plays_its_shifts_in_order(model, c):
    """Opening -> SHIFT CLEAR -> Happy hour -> SHIFT CLEAR -> (the mini-game slot, skipped) Last call -> CHAPTER CLEAR
    -> (the boss slot, skipped) the POST scene; each shift's banner, goal and pace; the progress saved after each. A
    chapter whose boss is built (the saloon): the Last call says SHIFT CLEAR, then the fight's banner (CHAPTER 1 BOSS),
    the boss step saved as reached, CHAPTER CLEAR after the fight (tests/test_boss.py plays it)."""
    rows = gen_story().level_rows(ROOT / "src" / "level.c")
    paces = []
    with to_chapter(model, c) as gb:
        for k in range(3):
            sh = SHIFTS[c][k]
            assert gb.mem("story_shift") == k and gb.mem("story_step") == SHIFT_STEP[k] and gb.mem("lives") == 3
            assert gb.mem("cur_group") == CHAPTERS[c]["venue"] and gb.mem("level") == c + 1
            if sh["type"] != G_CLEAR:
                assert gb.mem("story_left") == sh["count"] and gb.mem("quota") == 255
            elif sh["quota"]:
                assert gb.mem("quota") == sh["quota"]
            assert gb.mem16("story_timer") == sh["secs"] * 60
            assert gb.mem16("spawn_interval") == rows[c][2] * sh["spawn"] // 100
            pat = PATTERNS[sh["pattern"]]
            assert gb.mem("pat_len") == len(pat["bars"])
            if pat["bars"]:
                assert gb.mem("pat_bar") == pat["bars"][0] and list(gb.read("pat_buf", len(pat["bars"]))) == [
                    b | "nsdb".index(w) << 4 for b, w in zip(pat["bars"], pat["waits"])]
            paces.append(pace(gb))
            win(gb, c, k)
            run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 20)
            gb.run(3)
            assert banner_text(gb, 1) == centred("CHAPTER CLEAR" if k == 2 and c not in BOSS_BUILT else "SHIFT CLEAR")
            if k < 2:
                run_until(gb, lambda: state(gb) == GS_GOAL, 300)
                gb.run(3)
                assert banner_text(gb, 1) == centred(shift_title(c, k + 1))
                assert banner_text(gb, 2) == centred(SHIFTS[c][k + 1]["line1"])
                # saved: the next step reached (after the happy hour that is the mini-game slot, not built yet)
                assert (gb.mem("story_progress"), gb.mem("story_reached")) == (c, SHIFT_STEP[k] + 1)
                to_goal(gb)
        if c in BOSS_BUILT:
            run_until(gb, lambda: state(gb) == GS_GOAL, 300)
            gb.run(3)
            assert banner_text(gb, 1) == centred(f"CHAPTER {c + 1} BOSS") and gb.mem("story_step") == BOSS_STEP
            assert (gb.mem("story_progress"), gb.mem("story_reached")) == (c, BOSS_STEP)
            to_goal(gb)
            gb.write("boss_hook", 3)
            run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 200)
            gb.run(3)
            assert banner_text(gb, 1) == centred("CHAPTER CLEAR")
        run_until(gb, lambda: state(gb) == GS_STORY, 300)
        assert gb.mem("story_scene") == post(c)
        assert (gb.mem("story_progress"), gb.mem("story_reached")) == (c + 1, 0)
        assert gb.mem("story_fails") == 0
        ram = save_ram(gb)
    assert ram[:4] == b"TPR4" and ram[34] == c + 1 and ram[35] == 0, "the progress is in SRAM"
    (o_spd, o_hur, _, _), (h_spd, h_hur, _, _), (l_spd, l_hur, _, _) = paces
    assert o_spd == h_spd * 85 // 100 and l_spd == h_spd * SHIFTS[c][2]["walk"] // 100
    assert o_spd < h_spd < l_spd
    if h_hur:
        assert (o_hur, l_hur) == (o_spd + o_spd // 2, l_spd + l_spd // 2), "hurried walkers keep 1.5x"


# ---- lives (owner's rule): 3 per venue, carried through its shifts; the last one lost restarts the venue ----------
HUD_MUG = GAME_ART["TILE_HUD_MUG"]


def hud_lives(gb):
    """HUD columns 8-11 as a string: 'U' a mug, '.' none (column 8 is the 4th, bonus, life; 9-11 lives 1-3)."""
    return "".join("U" if t == HUD_MUG else "." for t in tilemap_row(gb, 0, 8, 4))


def lives_hud(n):
    return ("U" if n > 3 else ".") + "".join("U" if i <= n else "." for i in range(1, 4))


def call_banked(gb, name):
    """Call one of the game's BANKED functions from a test: a stub in free stack space below SP (push the registers;
    ld e, bank; ld hl, addr; call ___sdcc_bcall_ehl; pop; ret), entered with the interrupted PC as its return
    address. It runs at once (or at the next interrupt when the CPU sits in HALT) and returns where the game was."""
    f, bank, bc = gb.addr(name), BANKS["b_" + name], gb.addr("___sdcc_bcall_ehl")
    rf = gb.pb.register_file
    sp, pc = rf.SP, rf.PC
    stub = sp - 200
    code = [0xF5, 0xC5, 0xD5, 0xE5, 0x1E, bank, 0x21, f & 0xFF, (f >> 8) & 0xFF, 0xCD, bc & 0xFF, bc >> 8,
            0xE1, 0xD1, 0xC1, 0xF1, 0xC9]
    for i, b in enumerate(code):
        gb.pb.memory[stub + i] = b
    gb.pb.memory[sp - 2], gb.pb.memory[sp - 1] = pc & 0xFF, pc >> 8
    rf.SP, rf.PC = sp - 2, stub
    gb.run(2)


def break_a_glass(gb):
    """An empty off the right end of bar 3 (the bartender is on bar 0): a broken glass."""
    gb.write("intro_timer", 0)
    inject_mug(gb, 3, 150, st=2)
    run_until(gb, lambda: state(gb) == LIFE_LOST, 30)


def freeze_over(gb):
    run_until(gb, lambda: state(gb) != LIFE_LOST, 200)


def try_again(gb):
    """TRY AGAIN is up: A, then the next goal banner."""
    assert gb.mem("story_phase") == SP_FAIL and banner_text(gb, 1) == centred("TRY AGAIN")
    gb.press("a", 2)
    run_until(gb, lambda: state(gb) == GS_GOAL, 30)
    gb.run(3)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_lives_carry_from_shift_to_shift(model):
    with to_chapter(model, 0) as gb:
        assert gb.mem("lives") == 3 and hud_lives(gb) == lives_hud(3)
        lose_a_life(gb)
        freeze_over(gb)
        assert gb.mem("lives") == 2 and state(gb) == PLAYING and gb.mem("story_shift") == 0
        for k in range(2):
            win(gb, 0, k)
            run_until(gb, lambda: state(gb) == GS_GOAL, 400)
            gb.run(3)
            assert gb.mem("story_shift") == k + 1 and gb.mem("lives") == 2, "not refilled between shifts"
            assert hud_lives(gb) == lives_hud(2)
            to_goal(gb)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("c", range(9))
def test_losing_the_last_life_in_the_last_call_restarts_the_venue(model, c):
    """Every chapter: the last life lost in the Last call -> TRY AGAIN -> the Opening's banner with 3 lives (no PRE
    scene); the step reached stays recorded (and is not lowered by winning the Opening again), the score carries on."""
    with to_shift(model, c, 2) as gb:
        gb.write("served", 3)
        gb.write("lives", 1)
        score = int.from_bytes(gb.read("score", 4), "little")
        lose_a_life(gb)                                 # a patron at the tap (chapter 2: the rule, 1 left to lose)
        assert gb.mem("lives") == 0
        run_until(gb, lambda: state(gb) == GS_STORY, 200)
        assert gb.mem("story_fails") == 1
        try_again(gb)
        assert gb.mem("story_chapter") == c and gb.mem("lives") == 3 and gb.mem("served") == 0
        assert gb.mem("story_shift") == 0 and gb.mem("story_step") == 0, "the venue again, from its Opening"
        assert gb.mem("story_restarts") == 1 and hud_lives(gb) == lives_hud(3)
        assert banner_text(gb, 1) == centred(shift_title(c, 0))
        assert (gb.mem("story_progress"), gb.mem("story_reached")) == (c, 3), "the step reached is kept"
        assert gb.mem("story_scene") == pre(c), "no PRE scene: straight to the goal"
        assert int.from_bytes(gb.read("score", 4), "little") >= score, "the score carries on"
        assert gb.mem("pat_len") == 0, "the Opening's normal arrivals"
        to_goal(gb)
        win(gb, c, 0)
        run_until(gb, lambda: state(gb) == GS_GOAL, 400)
        assert (gb.mem("story_progress"), gb.mem("story_reached")) == (c, 3), "Practice unlocks never go back"
        assert gb.mem("lives") == 3


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_losing_all_three_in_the_opening_restarts_the_opening(model):
    with to_chapter(model, 0) as gb:
        for n in range(3):
            lose_a_life(gb)
            if n < 2:
                freeze_over(gb)
        run_until(gb, lambda: state(gb) == GS_STORY, 200)
        try_again(gb)
        assert gb.mem("story_shift") == 0 and gb.mem("story_step") == 0 and gb.mem("lives") == 3
        assert gb.mem("story_scene") == pre(0), "no PRE scene again"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_time_up_costs_a_life_and_retries_the_shift(model):
    """Chapter 4's Last call (timed): the clock running out costs a life and the shift is played again with the
    lives left; when that was the last one, the venue restarts."""
    with to_shift(model, 3, 2) as gb:
        for left, shift in ((2, 2), (1, 2), (0, 0)):
            assert gb.mem16("story_timer") == SHIFTS[3][2]["secs"] * 60
            gb.write("intro_timer", 0)
            gb.write(gb.addr("story_timer"), 3)
            gb.write(gb.addr("story_timer") + 1, 0)
            run_until(gb, lambda: state(gb) == GS_STORY, 10)
            assert gb.mem("lives") == left
            gb.run(3)
            assert hud_lives(gb) == lives_hud(left)
            try_again(gb)
            assert gb.mem("story_shift") == shift and gb.mem("lives") == (left or 3)
            assert gb.mem16("story_timer") == SHIFTS[3][shift]["secs"] * 60
            to_goal(gb)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("c, k", [(1, 0), (1, 1), (1, 2), (6, 0), (6, 1), (6, 2)])
def test_a_strict_rule_costs_two_lives(model, c, k):
    """Chapter 2 (a fan at the tap) and 7 (a broken cup), every shift: the banner says so, breaking the rule costs 2
    lives, "2 LIVES LOST" shows over the freeze and the two lost mugs blink together; the shift goes on with the one
    left, and the next break of the rule restarts the venue."""
    with to_shift(model, c, k, banner=True) as gb:
        sh = SHIFTS[c][k]
        assert sh["flags"] == (F_NO_TAP if c == 1 else F_NO_BREAK)
        line2 = "FAN AT TAP COSTS TWO" if c == 1 else "BROKEN CUP COSTS TWO"
        assert sh["line2"] == line2 and banner_text(gb, 3) == centred(line2)
        to_goal(gb)
        gb.write("served", 2)
        if c == 1:
            lose_a_life(gb)
        else:
            break_a_glass(gb)
        gb.run(2)
        assert gb.mem("lives") == 1 and gb.mem("story_pen") == 2
        assert banner_text(gb, 1) == centred("2 LIVES LOST")
        seen = set()
        while state(gb) == LIFE_LOST:
            seen.add(hud_lives(gb))
            gb.run(1)
        assert seen == {".U..", ".UUU"}, f"the two lost mugs blink together: {seen}"
        gb.run(3)
        assert state(gb) == PLAYING and gb.mem("story_shift") == k and gb.mem("served") == 2
        assert hud_lives(gb) == lives_hud(1) and gb.mem("story_pen") == 0
        assert gb.mem("overlay_on") == 0, "the banner goes with the freeze"
        if c == 1:
            lose_a_life(gb)
        else:
            break_a_glass(gb)
        assert gb.mem("lives") == 0
        run_until(gb, lambda: state(gb) == GS_STORY, 200)
        try_again(gb)
        assert gb.mem("story_shift") == 0 and gb.mem("lives") == 3


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_strict_rule_cue(model):
    """The moment the two lost mugs light up during the freeze (chapter 2's Happy hour, a fan at the tap)."""
    with to_shift(model, 1, 1) as gb:
        lose_a_life(gb)
        run_until(gb, lambda: gb.mem("state_timer") >= 10, 20)
        gb.run(1)
        assert hud_lives(gb) == ".UUU" and gb.mem("lives") == 1
        check_golden(gb, "story_two_lives")


def teahouse_post(gb):
    """Chapter 7 played on from where gb is (any shift, past its banner): won as the chapter's last step, so its POST
    scene opens; Hana's first page shown whole."""
    to_goal(gb)
    gb.write("story_step", STORY_STEPS - 1)
    win(gb, 6, gb.mem("story_shift"))
    run_until(gb, lambda: state(gb) == GS_STORY and gb.mem("story_scene") == post(6), 400)
    settle(gb)
    page_ready(gb)
    assert gb.mem("story_page") == 0 and gb.mem("story_cur") == PORTRAITS["HANA"]["pid"]
    return text_rows(gb)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_hana_thanks_a_clean_teahouse_with_not_one_cup(model):
    """No cup broken in the teahouse run (Opening won, then the venue): NOT ONE CUP BROKEN."""
    with to_chapter(model, 6) as gb:
        assert gb.mem("story_conds") == 0
        win(gb, 6, 0)                                    # the Opening, cleanly: SHIFT CLEAR, the Happy hour
        run_until(gb, lambda: state(gb) == GS_GOAL, 400)
        gb.run(2)
        assert gb.mem("story_shift") == 1 and gb.mem("story_conds") == 0
        assert teahouse_post(gb) == glyph_rows(NOT_ONE)
        check_golden(gb, "story_hana_not_one")
        gb.screenshot(ROOT / "out" / f"hana_not_one.{gb.model_name}.png", 4)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_hana_after_a_broken_cup_says_so_few(model):
    """A cup broken in the Opening (2 lives, the run goes on) is still remembered after the Happy hour is won:
    SO FEW CUPS BROKEN."""
    with to_chapter(model, 6) as gb:
        break_a_glass(gb)
        gb.run(2)
        assert gb.mem("lives") == 1 and gb.mem("story_conds") == 1, "the strict rule's event sets GLASS_BROKEN"
        freeze_over(gb)
        win(gb, 6, 0)
        run_until(gb, lambda: state(gb) == GS_GOAL, 400)
        gb.run(2)
        assert gb.mem("story_shift") == 1 and gb.mem("story_conds") == 1, "kept from shift to shift"
        assert teahouse_post(gb) == glyph_rows(SO_FEW)
        check_golden(gb, "story_hana_so_few")
        gb.screenshot(ROOT / "out" / f"hana_so_few.{gb.model_name}.png", 4)
        gb.press("a", 2)                                 # the next page is the same for both runs
        page_ready(gb)
        assert text_rows(gb) == glyph_rows(SCENES[SC["POST_TEAHOUSE"]]["pages"][1]["lines"])


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_broken_cup_before_a_venue_restart_is_forgotten(model):
    """Cups broken in an attempt that lost its last life do not count: the restarted venue is a new run, and a clean
    one gets NOT ONE CUP."""
    with to_chapter(model, 6) as gb:
        break_a_glass(gb)                                # 3 -> 1
        freeze_over(gb)
        break_a_glass(gb)                                # the last one: TRY AGAIN, the venue again
        assert gb.mem("lives") == 0 and gb.mem("story_conds") == 1
        run_until(gb, lambda: state(gb) == GS_STORY, 200)
        try_again(gb)
        assert gb.mem("story_restarts") == 1 and gb.mem("story_shift") == 0 and gb.mem("lives") == 3
        assert gb.mem("story_conds") == 0, "a new venue attempt"
        assert teahouse_post(gb) == glyph_rows(NOT_ONE)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_other_rules_cost_one_life(model):
    with to_shift(model, 6, 1) as gb:                   # the teahouse: a patron at the tap is one life
        lose_a_life(gb)
        gb.run(2)
        assert gb.mem("lives") == 2 and gb.mem("story_pen") == 0 and gb.mem("overlay_on") == 0
    with to_shift(model, 1, 1) as gb:                   # the stadium: a broken glass is one life
        break_a_glass(gb)
        gb.run(2)
        assert gb.mem("lives") == 2 and gb.mem("story_pen") == 0


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_gold_medal_bonus_life(model):
    """story_bonus_life (the mini-game framework's call on a gold medal): 4 lives, the 4th mug at column 8, capped at
    4; the lives carry into the next shift; the bonus mug is the first to go."""
    with to_chapter(model, 0) as gb:
        call_banked(gb, "story_bonus_life")
        gb.run(2)
        assert gb.mem("lives") == 4 and hud_lives(gb) == "UUUU" and state(gb) == PLAYING
        check_golden(gb, "story_bonus_life")
        call_banked(gb, "story_bonus_life")
        gb.run(2)
        assert gb.mem("lives") == 4 and hud_lives(gb) == "UUUU", "at most 4"
        win(gb, 0, 0)
        run_until(gb, lambda: state(gb) == GS_GOAL, 400)
        gb.run(3)
        assert gb.mem("lives") == 4 and hud_lives(gb) == "UUUU"
        to_goal(gb)
        lose_a_life(gb)
        gb.run(2)
        assert gb.mem("lives") == 3 and hud_lives(gb) == ".UUU"


def test_arcade_keeps_three_lives_for_the_run(gb):
    """Arcade is unchanged: 3 lives for the whole run (not refilled at a new level), column 8 always empty."""
    assert gb.mem("story_on") == 0 and gb.mem("lives") == 3 and hud_lives(gb) == ".UUU"
    lose_a_life(gb)
    freeze_over(gb)
    assert gb.mem("lives") == 2 and hud_lives(gb) == ".UU."
    clear_bars(gb)
    run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 20)
    run_until(gb, lambda: state(gb) == PLAYING and gb.mem("level") == 2, 400)
    gb.run(3)
    assert gb.mem("lives") == 2 and hud_lives(gb) == ".UU."
    lose_a_life(gb)
    freeze_over(gb)
    lose_a_life(gb)
    freeze_over(gb)
    assert gb.mem("lives") == 0 and state(gb) == GAME_OVER


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("c", range(9))
def test_each_last_call_pattern_sends_its_arrival_order(model, c):
    """The spawns follow the pattern's bars in order (deterministic, the RNG has no say), each followed by its wait."""
    pat = PATTERNS[SHIFTS[c][2]["pattern"]]
    bars, waits = pat["bars"], pat["waits"]
    with to_shift(model, c, 2) as gb:
        iv = gb.mem16("spawn_interval")
        wait = {"n": iv, "s": STORY["pat_short"], "d": 2 * iv, "b": 4 * iv}
        gb.write("intro_timer", 0)
        got, timers = [], []
        n0 = gb.mem("spawned")
        live = set(i for i, s in enumerate(gb.read("patron_state", 16)) if s)
        for _ in range(1500):
            if len(got) == len(bars) + 1:
                break
            if gb.mem16("spawn_timer") > 1:
                gb.write(gb.addr("spawn_timer"), 1)       # (no waiting between spawns; the pattern's own wait is checked)
                gb.write(gb.addr("spawn_timer") + 1, 0)
            gb.run(1)
            assert state(gb) == PLAYING and gb.mem("lives") == 3
            now = set(i for i, s in enumerate(gb.read("patron_state", 16)) if s)
            if gb.mem("spawned") != n0:
                n0 = gb.mem("spawned")
                new = now - live
                assert len(new) == 1
                got.append(gb.mem(gb.addr("patron_bar") + new.pop()))
                timers.append(gb.mem16("spawn_timer"))
            live = now
        want = bars + bars[:1]
        assert got == want, f"arrivals {got}, pattern {want}"
        assert timers == [wait[w] for w in waits + waits[:1]]


# ---- (d) the whole run's end, save and continue -------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_last_chapter_leads_to_the_finale_credits_and_the_title(model):
    with to_shift(model, 8, 2) as gb:
        win(gb, 8, 2)
        run_until(gb, lambda: state(gb) == GS_STORY, 300)
        assert gb.mem("story_scene") == post(8) and gb.mem("story_progress") == 9
        skip_scene(gb)
        assert gb.mem("story_scene") == SC["FINALE"]
        page_ready(gb)
        assert text_rows(gb) == glyph_rows(SCENES[SC["FINALE"]]["pages"][0]["lines"])
        skip_scene(gb)
        assert gb.mem("story_scene") == SC["CREDITS"]
        skip_scene(gb)
        run_until(gb, lambda: state(gb) == TITLE, 30)
        assert gb.mem("story_on") == 0 and gb.mem("title_n") == 3, "the story is complete: no CONTINUE"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_continue_mid_venue_starts_the_venue_over(model):
    """A cleared shift is saved (the step reached), but lives are not: CONTINUE after a reset starts the venue over at
    its Opening banner (no PRE scene: a step of it was reached) with 3 lives."""
    with to_chapter(model, 0) as gb:
        lose_a_life(gb)
        freeze_over(gb)
        win(gb, 0, 0)
        run_until(gb, lambda: state(gb) == GS_GOAL, 300)
        assert gb.mem("lives") == 2
        ram = save_ram(gb)
    assert ram[:4] == b"TPR4" and (ram[34], ram[35]) == (0, 1), "chapter 1, the happy hour reached"
    with booted(model, ram) as again:
        hold_stage_anim(again)
        assert (again.mem("story_progress"), again.mem("story_reached")) == (0, 1)
        assert again.mem("title_n") == 4, "CONTINUE with no chapter cleared, a shift done"
        again.press("down", 2)
        again.press("down", 2)
        again.press("a", 2)
        run_until(again, lambda: state(again) == GS_GOAL, 60)
        again.run(3)
        assert again.mem("story_chapter") == 0 and again.mem("story_shift") == 0 and again.mem("story_step") == 0
        assert again.mem("lives") == 3 and hud_lives(again) == lives_hud(3)
        assert banner_text(again, 1) == centred("CHAPTER 1 OPENING")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("step", [2, 3])
def test_continue_keeps_the_step_reached_for_practice(model, step):
    """A save at the mini-game slot or the Last call: CONTINUE opens the venue's Opening; winning it again keeps the
    furthest step reached (the record Practice unlocks from), the next shift is the Happy hour."""
    with booted(model, v4_image([], story=4, step=step)) as rom:
        hold_stage_anim(rom)
        assert rom.mem("title_n") == 4
        rom.press("down", 2)
        rom.press("down", 2)
        rom.press("a", 2)
        run_until(rom, lambda: state(rom) == GS_GOAL, 60)
        assert (rom.mem("story_chapter"), rom.mem("story_step"), rom.mem("story_shift")) == (4, 0, 0)
        to_goal(rom)
        win(rom, 4, 0)
        run_until(rom, lambda: state(rom) == GS_GOAL, 400)
        assert rom.mem("story_shift") == 1
        assert (rom.mem("story_progress"), rom.mem("story_reached")) == (4, step)
        assert save_ram(rom)[35] == step


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_progress_survives_a_reset_and_continue_resumes(model):
    with to_shift(model, 0, 2) as gb:
        win(gb, 0, 2)
        beat_the_boss(gb, 0)
        run_until(gb, lambda: state(gb) == GS_STORY, 300)
        ram = save_ram(gb)
    with booted(model, ram) as again:
        hold_stage_anim(again)
        assert again.mem("story_progress") == 1 and again.mem("title_n") == 4
        assert list(again.read("title_items", 4)) == [0, 1, 3, 2], "ARCADE, STORY, CONTINUE, MUSIC"
        assert list(again.read("title_rows", 4)) == [5, 7, 9, 11]
        settle_title(again)
        check_golden(again, "title_continue")
        again.press("down", 2)
        again.press("down", 2)
        again.press("a", 2)
        run_until(again, lambda: state(again) == GS_STORY, 30)
        assert again.mem("story_scene") == SC["PRE_STADIUM"] and again.mem("story_chapter") == 1


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_story_starts_over_from_the_intro_even_with_a_save(model):
    with start_story(model, v4_image([], story=4, step=3)) as gb:
        assert gb.mem("story_scene") == SC["INTRO"] and gb.mem("story_chapter") == 0
        skip_scene(gb)
        skip_scene(gb)
        run_until(gb, lambda: state(gb) == GS_GOAL, 30)
        assert gb.mem("story_shift") == 0


# ---- (e) the save: version 4 and the migrations -------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_version_2_save_keeps_its_hi_scores_and_gains_story_progress(model):
    entries = [("ABC", 500), ("DEF", 400), ("GHI", 300)]
    with booted(model, v2_image(entries)) as rom:
        assert rom.mem("save_migrated") == 2 and rom.mem("story_progress") == 0 and rom.mem("story_reached") == 0
        assert table(rom)[:3] == entries and rom.mem("title_n") == 3
        ram = save_ram(rom)
    assert parse_save(ram)[:3] == entries and ram[34] == 0 and ram[35] == 0, "written back as version 4 at once"
    assert ram[:V4_SUM + 2] == v4_image(entries)[:V4_SUM + 2]
    with booted(model, ram) as again:
        assert again.mem("save_migrated") == 0 and table(again)[:3] == entries


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_version_3_save_migrates_to_version_4_at_the_chapter_start(model):
    entries = [("ABC", 500), ("DEF", 400)]
    with booted(model, v3_image(entries, story=4)) as rom:
        hold_stage_anim(rom)
        assert rom.mem("save_migrated") == 3 and table(rom)[:2] == entries
        assert (rom.mem("story_progress"), rom.mem("story_reached")) == (4, 0), "4 chapters cleared, chapter 5 not begun"
        rom.press("down", 2)
        rom.press("down", 2)
        rom.press("a", 2)                               # CONTINUE: chapter 5's PRE scene, as with version 3
        run_until(rom, lambda: state(rom) == GS_STORY, 30)
        assert rom.mem("story_scene") == pre(4) and rom.mem("story_chapter") == 4
        ram = save_ram(rom)
    assert ram[:V4_SUM + 2] == v4_image(entries, story=4)[:V4_SUM + 2], "written back as version 4 at once"
    with booted(model, ram) as again:
        assert again.mem("save_migrated") == 0 and again.mem("story_progress") == 4


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_version_4_loads_its_progress_and_rejects_a_bad_one(model):
    with booted(model, v4_image([("ABC", 500)], story=7, step=3)) as rom:
        assert (rom.mem("story_progress"), rom.mem("story_reached")) == (7, 3)
        assert table(rom)[0] == ("ABC", 500) and rom.mem("save_migrated") == 0
    for story, step in ((10, 0), (2, 5), (9, 1)):      # (well-formed checksums over a progress that cannot be)
        with booted(model, v4_image([("ABC", 500)], story=story, step=step)) as rom:
            assert rom.mem("story_progress") == 0 and table(rom)[0] == ("   ", 0), (story, step)
    with booted(model, v3_image([("ABC", 500)], story=10)) as rom:
        assert rom.mem("story_progress") == 0 and table(rom)[0] == ("   ", 0)
    with booted(model, v1_image(777)) as rom:
        assert rom.mem("save_migrated") == 1 and table(rom)[0] == ("SPG", 777) and rom.mem("story_progress") == 0
