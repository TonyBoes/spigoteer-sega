# M11b story mode: the script build (tools/gen_story.py), the cut-scenes (src/story.c), the chapter goals, the story
# progress in SRAM (save.c version 3) and the title's CONTINUE.
import importlib.util
import json

import pytest
from conftest import GAME, ROOT, check_golden, hold_stage_anim
from test_flow import (GS_GOAL, GS_STORY, LEVEL_CLEAR, LIFE_LOST, PLAYING, TITLE, inject_mug, lose_a_life, run_until,
                       settle_title, state, tilemap_row)
from test_scores import V3_SUM, booted, parse_save, table, v1_image, v2_image, v3_image
from test_sound import save_ram

pytestmark = pytest.mark.timeout(240)

STORY = json.loads((ROOT / "build" / "story.json").read_text())
SCENES = STORY["scenes"]
SC = {s["id"]: i for i, s in enumerate(SCENES)}
CHAPTERS = STORY["chapters"]
GLYPH = STORY["glyphs"]
FONT = STORY["font"]
SPEAKERS = STORY["speakers"]
G_SERVE, G_CATCH, G_CLEAR = 0, 1, 2
F_NO_TAP, F_NO_BREAK = 1, 2
SP_SCENE, SP_GOAL, SP_PLAY, SP_FAIL = 1, 2, 3, 4
BOX_ROW, TEXT_ROW = 13, 14
TAP_X = GAME["TAP_X"]
CHARSET = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,!?'-: ")


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
    for name, p in STORY["portraits"].items():
        assert p["w"] <= 7 and p["h"] <= 7 and 1 <= p["pals"] <= 3, name
        assert p["y"] + p["h"] <= 12 and p["x"] >= 1, f"{name}: the frame stays above the text box"


# ---- helpers ------------------------------------------------------------------------------------------------
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


def to_chapter(model, c):
    """A rom in chapter c's level, just past the goal banner (a save with c chapters cleared: CONTINUE)."""
    if c:
        rom = start_story(model, v3_image([], story=c), cont=True)
    else:
        rom = start_story(model)
        skip_scene(rom)                                   # INTRO
    assert rom.mem("story_scene") == pre(c) and rom.mem("story_chapter") == c
    skip_scene(rom)                                       # the PRE scene
    run_until(rom, lambda: state(rom) == GS_GOAL, 30)
    rom.write("tip_chance", 0)
    rom.press("a", 2)
    run_until(rom, lambda: state(rom) == PLAYING, 10)
    return rom


def clear_bars(gb):
    """Nobody left and the quota spawned: the level clears on the next frame."""
    gb.write("quota", gb.mem("spawned"))
    for i in range(16):
        gb.write(gb.addr("patron_state") + i, 0)
    gb.write("patrons_live", 0)
    for i in range(20):
        gb.write(gb.addr("mug_state") + i, 0)
    gb.write("mugs_live", 0)


def win(gb, c):
    ch = CHAPTERS[c]
    if ch["type"] == G_SERVE:
        gb.write("served", ch["count"])
    elif ch["type"] == G_CATCH:
        gb.write("story_catches", ch["count"] - 1)
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
        assert tilemap_row(gb, y - 1, x - 1, w + 2) == [FONT["frame_tl"]] + [FONT["frame_t"]] * w + [FONT["frame_tr"]]
        assert tilemap_row(gb, y + h, x - 1, 1) == [FONT["frame_bl"]]
        # the name on the panel, the title on the HUD row
        assert tilemap_row(gb, BOX_ROW, 2, 5) == [GLYPH[c] for c in "SADIE"]
        title = SCENES[SC["PRE_SALOON"]]["title"]
        assert tilemap_row(gb, 0, (20 - len(title)) // 2, len(title)) == [GLYPH[c] for c in title]
        # the Spigoteer's sprite at bar 1's tap, nothing else
        assert gb.mem("bar") == 1 and gb.mem("bartender_x") == TAP_X
        assert len(gb.visible_sprites()) == 4
        check_golden(gb, "story_portrait")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_speaker_change_swaps_the_portrait_and_the_narrator_wipes_it(model):
    with start_story(model) as gb:
        skip_scene(gb)                                  # INTRO
        # PRE_SALOON -> chapter 1 -> win -> POST_SALOON: SADIE, SADIE, DREGS, NARRATOR, SPIGOTEER
        skip_scene(gb)
        run_until(gb, lambda: state(gb) == GS_GOAL, 30)
        gb.press("a", 2)
        win(gb, 0)
        run_until(gb, lambda: state(gb) == GS_STORY and gb.mem("story_scene") == post(0), 400)
        pages = SCENES[post(0)]["pages"]
        assert [p["speaker"] for p in pages] == ["SADIE", "SADIE", "DREGS", "NARRATOR", "SPIGOTEER"]
        for k in range(2):
            page_ready(gb)
            gb.press("a", 2)
        page_ready(gb)
        assert gb.mem("story_page") == 2 and SPEAKERS[gb.mem("story_cur")] == "DREGS"
        dregs = STORY["portraits"]["DREGS"]
        assert dregs["obj"] == 4, "the placeholder's name tag is the OBJ overlay layer"
        assert len(gb.visible_sprites()) == 4 + 4, "the Spigoteer + the overlay"
        check_golden(gb, "story_placeholder")
        rect = [tilemap_row(gb, dregs["y"] - 1 + r, dregs["x"] - 1, dregs["w"] + 2) for r in range(dregs["h"] + 2)]
        gb.press("a", 2)                               # NARRATOR: the frame wipes back to the backdrop
        page_ready(gb)
        assert gb.mem("story_cur") == 255 and len(gb.visible_sprites()) == 4
        after = [tilemap_row(gb, dregs["y"] - 1 + r, dregs["x"] - 1, dregs["w"] + 2) for r in range(dregs["h"] + 2)]
        story_ids = range(STORY["font_base"], 256)
        assert all(t not in story_ids for row in after for t in row), "no frame or portrait tile left"
        assert after != rect
        gb.press("a", 2)                               # SPIGOTEER: a new frame
        page_ready(gb)
        assert SPEAKERS[gb.mem("story_cur")] == "SPIGOTEER"
        sp = STORY["portraits"]["SPIGOTEER"]
        assert tilemap_row(gb, sp["y"] - 1, sp["x"] - 1, 1) == [FONT["frame_tl"]]


# ---- (c) chapters: goals ----------------------------------------------------------------------------------------
def banner_text(gb, row):
    return tilemap_row(gb, row, 0, 20, window=True)


def centred(s):
    row = [GLYPH[" "]] * 20
    for i, c in enumerate(s):
        row[(20 - len(s)) // 2 + i] = GLYPH[c]
    return row


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_goal_banner_and_the_hud_counter(model):
    with start_story(model) as gb:
        skip_scene(gb)
        skip_scene(gb)
        run_until(gb, lambda: state(gb) == GS_GOAL, 30)
        gb.run(5)
        assert banner_text(gb, 2) == centred(CHAPTERS[0]["line1"])
        assert banner_text(gb, 1)[5:14] == [GLYPH[c] for c in "CHAPTER 1"]
        assert gb.mem("level") == 1 and gb.mem("cur_group") == 0 and gb.mem("quota") == 255
        # the HUD: S + what is left (15) at columns 12-14
        assert tilemap_row(gb, 0, 12, 3) == [GLYPH["S"], GLYPH["1"], GLYPH["5"]]
        check_golden(gb, "story_goal")
        run_until(gb, lambda: state(gb) == PLAYING, 200)      # 3 s, then the level
        gb.write("served", 5)
        gb.run(3)
        assert gb.mem("story_left") == 10
        assert tilemap_row(gb, 0, 12, 3) == [GLYPH["S"], GLYPH["1"], GLYPH["0"]]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("c", range(9))
def test_each_chapter_goal_succeeds(model, c):
    with to_chapter(model, c) as gb:
        assert gb.mem("cur_group") == CHAPTERS[c]["venue"] and gb.mem("lives") == 3
        win(gb, c)
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 20)
        assert gb.mem("story_progress") == c, "saved only once the clear is over"
        run_until(gb, lambda: state(gb) == GS_STORY, 200)
        assert gb.mem("story_scene") == post(c) and gb.mem("story_progress") == c + 1
        assert gb.mem("story_fails") == 0
        ram = save_ram(gb)
    assert ram[:4] == b"TPR3" and ram[V3_SUM - 2] == c + 1, "the progress is in SRAM"


def fail_goal(gb, c):
    """Break chapter c's goal the way only it can (its flag or its timer), else lose all three lives."""
    ch = CHAPTERS[c]
    if ch["flags"] & F_NO_TAP:
        lose_a_life(gb)                                 # one patron at the tap is enough
        assert gb.mem("lives") == 0
    elif ch["flags"] & F_NO_BREAK:
        gb.write("intro_timer", 0)
        inject_mug(gb, 3, 150, st=2)                    # an empty off the right end of bar 3 (he is on bar 0)
        run_until(gb, lambda: state(gb) == LIFE_LOST, 30)
        gb.run(1)
        assert gb.mem("lives") == 0 and gb.mem("story_breaks") == 1
    elif ch["secs"]:
        assert gb.mem16("story_timer") == ch["secs"] * 60
        gb.write("intro_timer", 0)
        gb.write(gb.addr("story_timer"), 3)
        gb.write(gb.addr("story_timer") + 1, 0)
        run_until(gb, lambda: state(gb) == GS_STORY, 10)
        return
    else:
        for n in range(3):
            lose_a_life(gb)
            if n < 2:
                run_until(gb, lambda: state(gb) == PLAYING, 200)
    run_until(gb, lambda: state(gb) == GS_STORY, 200)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
@pytest.mark.parametrize("c", range(9))
def test_each_chapter_goal_fails_and_the_chapter_restarts(model, c):
    with to_chapter(model, c) as gb:
        fail_goal(gb, c)
        assert gb.mem("story_phase") == SP_FAIL and gb.mem("story_fails") == 1
        assert banner_text(gb, 1) == centred("TRY AGAIN")
        gb.press("a", 2)
        run_until(gb, lambda: state(gb) == GS_GOAL, 30)
        assert gb.mem("story_chapter") == c and gb.mem("lives") == 3 and gb.mem("served") == 0
        assert gb.mem("story_progress") == c, "nothing saved"
        assert gb.mem("story_scene") == pre(c), "no PRE scene again: straight to the goal"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_catch_goal_counts_real_catches(model):
    with to_chapter(model, 5) as gb:
        gb.write("intro_timer", 0)
        for k in range(3):
            inject_mug(gb, gb.mem("bar"), TAP_X + 1, st=2)
            gb.run(4)
        assert gb.mem("story_catches") == 3 and gb.mem("story_left") == 22
        assert tilemap_row(gb, 0, 12, 3) == [GLYPH["C"], GLYPH["2"], GLYPH["2"]]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_timed_chapter_shows_its_clock(model):
    with to_chapter(model, 3) as gb:
        gb.run(2)
        assert tilemap_row(gb, 0, 16, 4) == [GLYPH[c] for c in "T120"]
        gb.write("intro_timer", 0)
        gb.run(61)
        assert tilemap_row(gb, 0, 16, 4) == [GLYPH[c] for c in "T119"]


# ---- (d) the whole run's end, save and continue -------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_last_chapter_leads_to_the_finale_credits_and_the_title(model):
    with to_chapter(model, 8) as gb:
        win(gb, 8)
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
def test_the_progress_survives_a_reset_and_continue_resumes(model):
    with to_chapter(model, 0) as gb:
        win(gb, 0)
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
    with start_story(model, v3_image([], story=4)) as gb:
        assert gb.mem("story_scene") == SC["INTRO"] and gb.mem("story_chapter") == 0


# ---- (e) the save: version 3 and the migration -------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_version_2_save_keeps_its_hi_scores_and_gains_story_progress(model):
    entries = [("ABC", 500), ("DEF", 400), ("GHI", 300)]
    with booted(model, v2_image(entries)) as rom:
        assert rom.mem("save_migrated") == 2 and rom.mem("story_progress") == 0
        assert table(rom)[:3] == entries and rom.mem("title_n") == 3
        ram = save_ram(rom)
    assert parse_save(ram)[:3] == entries and ram[V3_SUM - 2] == 0, "written back as version 3 at once"
    assert ram[:V3_SUM + 2] == v3_image(entries)[:V3_SUM + 2]
    with booted(model, ram) as again:
        assert again.mem("save_migrated") == 0 and table(again)[:3] == entries


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_version_3_loads_its_progress_and_rejects_a_bad_one(model):
    with booted(model, v3_image([("ABC", 500)], story=7)) as rom:
        assert rom.mem("story_progress") == 7 and table(rom)[0] == ("ABC", 500) and rom.mem("save_migrated") == 0
    bad = bytearray(v3_image([("ABC", 500)], story=10))   # (a well-formed checksum over a progress past 9)
    with booted(model, bytes(bad)) as rom:
        assert rom.mem("story_progress") == 0 and table(rom)[0] == ("   ", 0)
    with booted(model, v1_image(777)) as rom:
        assert rom.mem("save_migrated") == 1 and table(rom)[0] == ("SPG", 777) and rom.mem("story_progress") == 0
