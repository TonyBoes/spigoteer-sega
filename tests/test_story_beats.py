# Dramatic beats in the story script (docs/story.md "Beats"): the `|` / `||` / `@beat` marks parse (tools/gen_story.py), the
# data carries them (build/story.json "pre", "marks"), and the text engine (src/story.c type_frame / page_begin) pauses the
# right number of frames, skips a beat on A or B, and leaves every page's text as written.
import re

import pytest
from conftest import ROOT
from test_story import SC, SCENES, STORY, gen_story as _gen_story, glyph_rows, settle, skip_scene, start_story, text_rows
from test_flow import run_until

pytestmark = pytest.mark.timeout(240)

_G = []


def gen_story():
    if not _G:                                    # one module, one StoryError class
        _G.append(_gen_story())
    return _G[0]


BEAT = STORY["beat"]
SHORT, LONG = BEAT["frames"]
UNIT, GAP_SPK, GAP_PAGE = BEAT["unit"], BEAT["gap_speaker"], BEAT["gap_page"]


# ---- the script format -------------------------------------------------------------------------------------------
def parse(line):
    return gen_story().parse_marks(line, "test")


def test_marks_parse_into_control_cells():
    g = gen_story()
    assert parse("WAIT,| WHAT?") == "WAIT,\x01WHAT?"
    assert parse("WAIT,|| WHAT?") == "WAIT,\x02WHAT?"
    assert parse("SO...|") == "SO...\x01"              # the line's end: the first free cell
    assert parse("NO MARKS HERE.") == "NO MARKS HERE."
    assert g.clean_line(parse("WAIT,| WHAT?")) == "WAIT, WHAT?"
    assert g.clean_line(parse("SO...||")) == "SO..."
    assert g.marks_of([parse("A,| B"), "", parse("C.||")]) == [[0, 2, SHORT], [2, 2, LONG]]


@pytest.mark.parametrize("bad, why", [
    ("|HELLO", "right after a word"), ("HELLO |WORLD", "right after a word"), ("HELLO|WORLD", "followed by a space"),
    ("HELLO|||", "short beat"), ("HELLO,|| |", "right after a word"),
])
def test_a_misplaced_mark_fails_the_build(bad, why):
    with pytest.raises(gen_story().StoryError, match=why):
        parse(bad)


def script_with(tmp_path, monkeypatch, block):
    g = gen_story()
    text = (ROOT / "docs" / "story.md").read_text()
    first = re.search(r"^```\n(.*?)\n\n", text, re.S | re.M)
    f = tmp_path / "story.md"
    f.write_text(text[:first.start(1)] + block + "\n\n" + text[first.end():])
    return g, f


@pytest.mark.parametrize("block, why", [
    ("NARRATOR\n@beat 9\nHELLO", "not '@beat' or '@beat N'"),
    ("NARRATOR\n@beat 0\nHELLO", "not '@beat' or '@beat N'"),
    ("NARRATOR\nHELLO|", "pauses nothing"),
    ("NARRATOR\nTHIS LINE IS TOO LONG!", "max 18"),
])
def test_a_bad_page_fails_the_build(tmp_path, monkeypatch, block, why):
    g, f = script_with(tmp_path, monkeypatch, block)
    with pytest.raises(g.StoryError, match=why):
        g.parse_script(f)


def test_a_beat_at_the_end_of_a_full_line_has_no_room(tmp_path, monkeypatch):
    g, f = script_with(tmp_path, monkeypatch, "NARRATOR\nABCDEFGHIJKLMNOPQR|\nX")
    with pytest.raises(g.StoryError, match="has no room"):
        g.parse_script(f)


def test_good_beats_parse_and_beat_defaults(tmp_path, monkeypatch):
    g, f = script_with(tmp_path, monkeypatch, "NARRATOR\n@beat\nWAIT,|| WHAT?|\nNO.\n\nNARRATOR\n@beat 7\nHI")
    s = g.parse_script(f)[0]
    assert s["pages"][0][1] == ["WAIT, WHAT?", "NO."] and s["raws"][0][0] == g.BEAT_DEFAULT
    assert s["raws"][0][1][0] == "WAIT,\x02WHAT?\x01"
    assert s["raws"][1][0] == 7


def test_the_data_carries_the_beats():
    text = (ROOT / "docs" / "story.md").read_text()
    code = "".join(re.findall(r"^```\n(.*?)^```", text, re.S | re.M))
    n_marks = sum(len(re.findall(r"\|+", l)) for l in code.split("\n"))
    pages = [p for s in SCENES for p in s["pages"]]
    variants = [v for p in pages for v in p["variants"]]
    # (a variant's own marks are in the script too, not in "marks": the tests of the data count the pages')
    assert sum(len(p["marks"]) for p in pages) <= n_marks and sum(len(p["marks"]) for p in pages) > 80
    assert sum(1 for p in pages if p["pre"]) == len(re.findall(r"^@beat", code, re.M)) - 0
    assert all(p["pre"] % UNIT == 0 and p["pre"] <= 7 * UNIT for p in pages)
    intro = SCENES[SC["INTRO"]]["pages"]
    assert intro[0]["pre"] == 4 * UNIT, "the story opens on a beat"
    assert intro[5]["marks"] == [[0, 5, SHORT], [0, 11, SHORT], [0, 17, SHORT], [1, 16, LONG]], "GLUG. GLUG. GLUG. ..."
    assert variants, "the teahouse's variant keeps its own text"


def test_no_scene_text_breaks():
    """Every page: 1-3 lines of at most 18 characters of the font, marks stripped (the text shown is the script's)."""
    font = set(STORY["glyphs"])
    for s in SCENES:
        for k, p in enumerate(s["pages"]):
            assert 1 <= len(p["lines"]) <= 3 and all(len(l) <= 18 for l in p["lines"]), (s["id"], k)
            assert all(set(l) <= font and "|" not in l and "\x01" not in l for l in p["lines"]), (s["id"], k)
            for v in p["variants"]:
                assert all(len(l) <= 18 and "|" not in l for l in v["lines"]), (s["id"], k)
            for r, c, _ in p["marks"]:                    # a mark sits inside its line's cells
                assert 0 < c <= 17 and r < len(p["lines"]), (s["id"], k)


# ---- the engine ------------------------------------------------------------------------------------------------------
def typed_trace(gb, frames):
    out = []
    for _ in range(frames):
        gb.run(1)
        out.append(gb.mem("story_typed"))
    return out


def runs_of(trace, value):
    """The longest stretch of frames the typed counter stayed at value."""
    best = cur = 0
    for t in trace:
        cur = cur + 1 if t == value else 0
        best = max(best, cur)
    return best


def first_char(trace):
    return next(i for i, t in enumerate(trace) if t > 0)


def turn_page(gb):
    """A: the rest of the page, then A again turns it (story_typed back to 0 on the frame the next page begins)."""
    if gb.mem("story_typed") < 54:
        gb.press("a", 1)
        gb.run(3)
    gb.press("a", 1)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_first_page_waits_its_beat_then_types(model):
    with start_story(model) as gb:
        intro = SCENES[SC["INTRO"]]["pages"]
        # (start_story has settled the screen some frames already; the intro's first page has @beat 4 = 32 frames)
        assert intro[0]["pre"] == 32
        assert gb.mem("story_typed") in range(0, 55)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_page_gaps_and_mid_line_beats(model):
    with start_story(model) as gb:
        intro = SCENES[SC["INTRO"]]["pages"]
        # page 1 -> 2 (the narrator again, no @beat): the engine's gap for the same speaker
        turn_page(gb)
        gb.run(0)
        trace = typed_trace(gb, 20)
        assert gb.mem("story_page") == 1
        assert first_char(trace) in range(GAP_PAGE - 1, GAP_PAGE + 3), trace
        # page 2 -> 3 (the narrator again: the festival page)
        turn_page(gb)
        trace = typed_trace(gb, 20)
        assert gb.mem("story_page") == 2
        assert first_char(trace) in range(GAP_PAGE - 1, GAP_PAGE + 3), trace
        # page 3 -> 4 (the narrator -> the Spigoteer): a longer gap
        turn_page(gb)
        trace = typed_trace(gb, 30)
        assert gb.mem("story_page") == 3
        assert first_char(trace) in range(GAP_SPK - 1, GAP_SPK + 3), trace
        # page 4's "THE SPIGOTEER,|": the typing stops SHORT frames after the line's last character
        assert intro[3]["marks"] == [[1, 14, SHORT]]
        run_until(gb, lambda: gb.mem("story_typed") == 54, 200)
        assert text_rows(gb) == glyph_rows(intro[3]["lines"])


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_beat_pauses_exactly_its_frames(model):
    with start_story(model) as gb:
        skip_scene(gb)                                   # INTRO -> PRE_SALOON
        s = SCENES[SC["PRE_SALOON"]]["pages"]
        assert gb.mem("story_scene") == SC["PRE_SALOON"]
        turn_page(gb)                                    # page 2: "THAT MUSTACHE?| I" ... "TUMBLEWEEDS.| NICE."
        trace = typed_trace(gb, 120)
        assert gb.mem("story_page") == 1
        marks = s[1]["marks"]
        assert [m[2] for m in marks] == [SHORT, SHORT]
        for r, c, frames in marks:
            assert runs_of(trace, r * 18 + c + 1) == frames, (r, c, frames, trace)
        assert gb.mem("story_typed") == 54 and text_rows(gb) == glyph_rows(s[1]["lines"])


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_skips_a_beat_and_shows_the_page(model):
    with start_story(model) as gb:
        skip_scene(gb)
        s = SCENES[SC["PRE_SALOON"]]["pages"]
        turn_page(gb)
        r, c, _ = s[1]["marks"][0]
        run_until(gb, lambda: gb.mem("story_typed") == r * 18 + c + 1, 80)   # the first beat has started
        gb.run(2)
        assert gb.mem("story_typed") == r * 18 + c + 1, "still waiting in the beat"
        gb.press("a", 2)
        gb.run(3)
        assert gb.mem("story_typed") == 54 and gb.mem("story_page") == 1, "A skipped the beat and showed the rest"
        assert text_rows(gb) == glyph_rows(s[1]["lines"])
        gb.press("a", 2)
        gb.run(2)
        assert gb.mem("story_page") == 2, "A again turns the page"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_b_skips_the_page_gap_too(model):
    with start_story(model) as gb:
        skip_scene(gb)
        s = SCENES[SC["PRE_SALOON"]]["pages"]
        turn_page(gb)
        gb.press("b", 1)                                 # right after the turn: inside the page's gap
        gb.run(3)
        assert gb.mem("story_page") == 2 or gb.mem("story_typed") == 54
        assert text_rows(gb) in (glyph_rows(s[1]["lines"]), glyph_rows(s[2]["lines"]))
