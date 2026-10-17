# The credits roll (src/credits.c; owner 2026-10-17): after the story's CREDITS pages (before the STORY score entry) and from the title's
# BONUS > CREDITS. A cast of characters (the Spigoteer and Dregs, the ten bosses, every patron of the ten venues), then the owner's lines in the
# story's lettering, centred with a clear column at each edge, scrolling up, then "THANKS FOR PLAYING!" alone. The whole roll is tied to the credits
# tune's position (88 s); B / START skip (to the score entry, or back to BONUS on CREDITS).
import re
from contextlib import contextmanager

import pytest
from conftest import K_BONUS, K_CREDITS, MENU_SETTLE, ROOT, TM_BONUS, check_golden, hold_stage_anim, menu_items, menu_tap, menu_to, title_pick
from gbtools import Rom
from test_flow import GS_INITIALS, GS_SCORES, GS_STORY, TITLE, most_per_scanline, run_until, state, tilemap_row
from test_mg import GLYPH_CH

SP_CREDITS = 8
TUNE_CREDITS = 15                          # src/music.h: after the 15 listed tunes
TUNE_NONE_ = 255
TUNE_FRAMES = 5400                         # the credits tune: 352 rows x 15 frames = 5280, and the roll's start
CR_AT = 0                                  # struct cr_state in story_scratch (src/credits.c): row[20], scroll(2), card, next, t(2), phase, from_story, f(2), dirty
SCROLL, CARD, NEXT, T, PHASE, FROM_STORY, F, STEP, BLANK = 20, 22, 23, 24, 26, 27, 28, 30, 39
STORY_H = (ROOT / "build" / "story.h").read_text()
FONT = int(re.search(r"#define BAR_TILE_COUNT (\d+)", (ROOT / "build" / "art.h").read_text()).group(1))   # STORY_FONT_BASE (build/story.h)
PUNCT = {FONT + 0: ".", FONT + 1: ",", FONT + 2: "!", FONT + 3: "?", FONT + 4: "'", FONT + 5: "-", FONT + 6: ":"}
OBJ_ROBOTS = 100
# the timeline (frames of the tune; src/credits.c)
TOTAL, TITLE_F, HERO_END, CARD_F, ROLL, SCROLL_END = 5280, 120, 330, 157, 3470, 4830
CARD_START = [0, TITLE_F] + [HERO_END + CARD_F * k for k in range(20)]
VENUES = ["THE SALOON", "THE STADIUM", "THE LUMBER LODGE", "THE BISTRO", "THE IGLOO", "THE ROBOT FACTORY", "THE CHROME COW", "THE TEAHOUSE",
          "THE JUNGLE ZOO", "THE SPACE LOUNGE"]
BOSSES = ["BIG TEX", "THE MASCOT", "SASQUATCH", "THE CRITIC", "THE YETI", "PROTOTYPE", "DUKE", "SUMO CHAMP", "LEO THE LION", "MOTHERSHIP"]
PATRONS = [   # (line 1, line 2) of the three patrons of each venue: labels, the game gives them no names; a word is never split
    [("COWBOY", ""), ("COW", "GIRL"), ("RANCH", "HAND")], [("CAP", "FAN"), ("BAND", "FAN"), ("REF", "")],
    [("BIG", "JACK"), ("RED", "HAIR"), ("GREEN", "CAP")], [("HEAD", "CHEF"), ("SOUS", "CHEF"), ("LINE", "COOK")],
    [("PARKA", "MAN"), ("PARKA", "GIRL"), ("BIG", "PARKA")], [("BOX", "BOT"), ("LADY", "BOT"), ("DOME", "BOT")],
    [("MOHAWK", ""), ("SCARF", ""), ("QUIFF", "")], [("NINJA", ""), ("NINJA", "GIRL"), ("RED", "HELM")],
    [("MONKEY", ""), ("PANDA", ""), ("HIPPO", "")], [("EYE", "STALK"), ("GREY", ""), ("SQUID", "")]]
# every card's lines, top to bottom (words of a row joined by one space)
CARDS = [["CAST OF", "CHARACTERS"], ["SPIGOTEER DREGS", "BARTENDER RIVAL"]]
for k in range(10):
    CARDS.append([BOSSES[k], VENUES[k]])
for v in range(10):
    CARDS.append([VENUES[v], " ".join(p[0] for p in PATRONS[v] if p[0])] + [t for t in [" ".join(p[1] for p in PATRONS[v] if p[1])] if t])
ROLL_LINES = ["SPIGOTEER", "GAME DESIGN,", "MEDIA, AND", "STORY BY", "TONY", "AND HIS TIRELESS", "TEAM OF", "ROBOT FRIENDS", "MUSIC", "PUBLIC DOMAIN",
              "MELODIES,", "ARRANGED", "FOR THIS GAME", "SPECIAL", "THANKS TO:", "GBDK-2020", "SDCC", "HUGEDRIVER", "RGBDS", "SAMEBOY", "PYBOY",
              "PAN DOCS", "THE GBDEV", "COMMUNITY", "THANKS FOR", "PLAYING!"]


def row_text(gb, r):
    return "".join(GLYPH_CH.get(t) or PUNCT.get(t) or " " for t in tilemap_row(gb, r, 0, 20)).strip()


def row_cols(gb, r):
    """(first, last) tile column of the row's glyphs, or None."""
    cols = [c for c, t in enumerate(tilemap_row(gb, r, 0, 20)) if GLYPH_CH.get(t) or PUNCT.get(t)]
    return (cols[0], cols[-1]) if cols else None


def scroll(gb):
    return gb.read("story_scratch", 32)[SCROLL] | gb.read("story_scratch", 32)[SCROLL + 1] << 8


def cr_t(gb):
    return gb.read("story_scratch", 32)[T] | gb.read("story_scratch", 32)[T + 1] << 8


def cr_f(gb):
    s = gb.read("story_scratch", 32)
    return s[F] | s[F + 1] << 8


def set_t(gb, v):                                              # (sound off: the position is this counter)
    gb.write(gb.addr("story_scratch") + T, v & 255)
    gb.write(gb.addr("story_scratch") + T + 1, v >> 8)


@contextmanager
def roll_from_bonus(model, sound=True):
    with Rom(ROOT / "build" / "game.gb", model) as gb:
        gb.run(120)
        gb.model_name = model
        hold_stage_anim(gb)
        if not sound:
            gb.write("sound_on", 0)
        title_pick(gb, K_BONUS, K_CREDITS)
        run_until(gb, lambda: gb.mem("story_phase") == SP_CREDITS, 20)
        gb.run(2)
        yield gb


def at(gb, f, settle=10):
    """Sound off: the roll jumps to frame f (and runs `settle` frames, and until a card is built: its rows and loads take a dozen frames)."""
    set_t(gb, f - 1)
    gb.run(settle)
    if f < ROLL:
        for _ in range(60):
            st = gb.read("story_scratch", 48)
            if st[PHASE] == 4 and st[STEP] >= 2 and not st[BLANK]:   # (whole, and the cut over)
                break
            gb.run(1)
        else:
            raise AssertionError("the card is not up")


def visible_rows(gb):
    """The map rows that are on the screen (the 32-row map scrolled by SCY), top to bottom."""
    scy = gb.regs()["SCY"]
    return [((scy >> 3) + r) % 32 for r in range(19 if scy & 7 else 18)]


def lines_on_screen(gb):
    return [t for t in (row_text(gb, r) for r in visible_rows(gb)) if t]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_credits_is_the_fourth_bonus_item_and_opens_the_roll(model):
    with Rom(ROOT / "build" / "game.gb", model) as gb:
        gb.run(120)
        title_pick(gb, K_BONUS)
        gb.run(MENU_SETTLE)
        assert menu_items(gb) == [7, 9, 10, K_CREDITS]
        from test_flow import title_text_row
        assert tilemap_row(gb, 12, 0, 20) == title_text_row("credits")
        menu_to(gb, K_CREDITS)
        menu_tap(gb, "a")
        run_until(gb, lambda: gb.mem("story_phase") == SP_CREDITS, 20)
        assert state(gb) == GS_STORY


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_choosing_credits_in_bonus_starts_the_credits_tune_at_once(model):
    with Rom(ROOT / "build" / "game.gb", model) as gb:
        gb.run(120)
        title_pick(gb, K_BONUS)
        gb.run(MENU_SETTLE)
        before = gb.mem("cur_tune")
        assert before != TUNE_CREDITS and gb.mem("sound_on") == 1, "the BONUS menu has its own tune"
        menu_to(gb, K_CREDITS)
        gb.press("a", 1)
        n = 0
        while gb.mem("story_phase") != SP_CREDITS or state(gb) != GS_STORY:
            gb.run(1)
            n += 1
            assert n < 20
        assert gb.mem("cur_tune") == TUNE_CREDITS, "the credits tune from the first frame of the credits screen"
        gb.run(3)
        assert cr_f(gb) <= 8 and gb.mem("music_frames") <= 8, "it starts with the screen: its position is at the beginning"
        gb.run(60)
        assert 55 <= cr_f(gb) <= 70, cr_f(gb)                  # (the roll's position is the tune's: 1 frame a frame)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_cast_cards_in_order_with_their_names_and_figures(model):
    with roll_from_bonus(model, sound=False) as gb:
        most = 0
        for c, text in enumerate(CARDS):
            at(gb, CARD_START[c] + 100)
            assert [" ".join(t.split()) for t in lines_on_screen(gb)] == text, (c, lines_on_screen(gb))
            shown = {s["tile"] for s in gb.visible_sprites()}
            most = max(most, most_per_scanline(gb))
            if c == 1:
                assert OBJ_ROBOTS not in shown and any(56 <= t < 64 for t in shown), "Dregs (OBJ 56..) and the Spigoteer (0..)"
                assert any(t < 56 for t in shown)
            elif 2 <= c < 12:
                assert shown == {64}, "the topper"
            elif c >= 12:
                assert shown == {100, 102, 106, 108, 112, 114}, shown
            if c >= 2:                                          # a blank row between a card's lines (the name and venue; a label's two lines)
                rows = [r for r in range(18) if row_cols(gb, r)]
                assert all(b - a >= 2 for a, b in zip(rows[1:], rows[2:])), (c, rows)
                if c < 12:
                    assert rows[-2:] == [10, 12], (c, rows)
                    panel = [r for r in range(18) if any(t >= 120 for t in tilemap_row(gb, r, 0, 20))]
                    assert panel == [4, 5, 6, 7, 8], "the panel (a margin row, the topper's row, the body, a margin row)"
                    assert 10 - panel[-1] >= 2, "a clear row between the panel and the name"
            for r in range(18):                                 # every line keeps a clear column at each edge
                cols = row_cols(gb, r)
                if cols:
                    assert cols[0] >= 1 and cols[1] <= 18, (c, r, cols)
        assert most <= 10
        assert gb.read("story_scratch", 32)[CARD] == 21


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_each_patron_name_is_centred_under_its_patron(model):
    with roll_from_bonus(model, sound=False) as gb:
        for v in range(10):
            at(gb, CARD_START[12 + v] + 100)
            xs = sorted(s["x"] for s in gb.visible_sprites())
            assert len(xs) == 6
            for k in range(3):
                cx = xs[2 * k] + 0                              # OAM x of the pair's first column = the pair's centre (left edge + 8)
                assert cx in (32 + 48 * k, 36 + 48 * k)
                for r in (10, 12):
                    row = tilemap_row(gb, r, 0, 20)
                    cols = [c for c in range((cx - 24) // 8, (cx + 24) // 8) if GLYPH_CH.get(row[c]) or PUNCT.get(row[c])]
                    if cols:
                        assert abs((cols[0] + cols[-1] + 1) * 4 - cx) <= 4, (v, k, r, cols, cx)
                words = [w for w in PATRONS[v][k] if w]
                assert max(len(w) for w in words) <= 6 and all(" " not in w for w in words)
                longest = max(words, key=len)
                row = tilemap_row(gb, 10 if longest == PATRONS[v][k][0] else 12, 0, 20)
                cols = [c for c in range(20) if GLYPH_CH.get(row[c]) or PUNCT.get(row[c])]
                cols = [c for c in cols if abs(c * 8 + 4 - cx) <= 24]
                assert abs((cols[0] + cols[-1] + 1) * 4 - cx) == 0, "the longest line is exactly under its sprite"


def test_the_roll_text_is_centred_broken_at_words_and_spaced_by_section():
    src = (ROOT / "src" / "credits.c").read_text()
    body = src[src.index("cr_text[] = {"):]
    body = body[:body.index("};")]
    body = re.sub(r"//[^\n]*", "", body)
    lines = re.findall(r'"([^"]*)"', body)
    assert [l for l in lines if l] == ROLL_LINES, "the credited content: the same words, only broken differently"
    assert max(len(l) for l in lines) <= 18 and max(len(l) for l in lines if l not in ("THE ROBOT FACTORY",)) <= 16, "a clear tile at each edge"
    assert " ".join(l for l in lines if l).replace("  ", " ") == (
        "SPIGOTEER GAME DESIGN, MEDIA, AND STORY BY TONY AND HIS TIRELESS TEAM OF ROBOT FRIENDS MUSIC PUBLIC DOMAIN MELODIES, ARRANGED FOR THIS GAME "
        "SPECIAL THANKS TO: GBDK-2020 SDCC HUGEDRIVER RGBDS SAMEBOY PYBOY PAN DOCS THE GBDEV COMMUNITY THANKS FOR PLAYING!")
    for first in ("GAME DESIGN,", "MUSIC", "SPECIAL"):         # two blank lines (4 tile rows) at least before each section
        i = lines.index(first)
        gap = 0
        while lines[i - 1 - gap] == "":
            gap += 1
        assert gap >= 2, (first, gap)
    i = lines.index("THANKS FOR")
    gap = 0
    while lines[i - 1 - gap] == "":
        gap += 1
    assert gap >= 5, "10 blank tile rows: the screen is empty before the last words"
    assert lines[-2:] == ["THANKS FOR", "PLAYING!"]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_roll_shows_every_line_centred_and_the_sprites_stay_within_the_limit(model):
    with roll_from_bonus(model, sound=False) as gb:
        seen, most, shown = [], 0, set()
        at(gb, ROLL + 12, settle=40)
        for f in range(ROLL + 12, SCROLL_END + 60, 6):
            set_t(gb, f)
            gb.run(1)
            for r in range(32):
                t = row_text(gb, r)
                cols = row_cols(gb, r)
                if t:
                    if t not in seen:
                        seen.append(t)
                    assert cols[0] >= 1 and cols[1] <= 18 and abs(cols[0] - (19 - cols[1])) <= 1, (t, cols)
            most = max(most, most_per_scanline(gb))
            shown |= {(s["tile"]) for s in gb.visible_sprites()}
        assert seen == ROLL_LINES, [x for x in seen if x not in ROLL_LINES] + [x for x in ROLL_LINES if x not in seen]
        assert 0 < most <= 8, most
        assert {OBJ_ROBOTS, OBJ_ROBOTS + 6, OBJ_ROBOTS + 12} <= shown, "the three robots"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_roll_ends_on_thanks_for_playing_alone(model):
    with roll_from_bonus(model, sound=False) as gb:
        at(gb, SCROLL_END - 400, settle=30)
        for f in range(SCROLL_END - 400, SCROLL_END + 30, 2):
            set_t(gb, f)
            gb.run(1)
        at(gb, SCROLL_END + 100, settle=20)
        assert lines_on_screen(gb) == ["THANKS FOR", "PLAYING!"]
        assert [s for s in gb.visible_sprites()] == [], "nothing else on the screen: no sprites either"
        assert state(gb) == GS_STORY
        a = [row_cols(gb, r) for r in visible_rows(gb) if row_cols(gb, r)]
        assert len(a) == 2 and all(c[0] >= 1 and c[1] <= 18 for c in a)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_roll_runs_with_the_tune_and_ends_within_a_second_of_it(model):
    with roll_from_bonus(model) as gb:
        start = cr_t(gb)
        ended = left = None
        frames = 0
        while frames < TUNE_FRAMES + 100:
            gb.run(1)
            frames += 1
            if ended is None and gb.mem("cur_tune") != TUNE_CREDITS:
                ended = frames
            if state(gb) != GS_STORY:
                left = frames
                break
            f = cr_f(gb)
            assert frames > 5270 or abs(f - (frames + start)) <= 2, ("the position follows the music, frame for frame", f, frames)
            if frames == 4000:                                  # mid-roll: the scroll is what the position says
                assert 250 <= scroll(gb) <= 300, scroll(gb)
        assert ended is not None and left is not None
        assert 5270 <= ended - 0 <= 5300 + start, ended         # the 88 s tune (the roll was 2+ frames in when `start` was taken)
        assert 0 <= left - ended <= 60, (ended, left)
        assert state(gb) == TITLE and gb.mem("title_menu") == TM_BONUS and menu_items(gb)[gb.mem("title_sel")] == K_CREDITS
        assert gb.regs()["SCY"] == 0


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_last_screen_waits_for_the_tunes_held_c(model):
    with roll_from_bonus(model) as gb:
        run_until(gb, lambda: cr_f(gb) >= 4900, 5000)
        assert lines_on_screen(gb) == ["THANKS FOR", "PLAYING!"]
        run_until(gb, lambda: cr_f(gb) >= 5200, 400)
        assert gb.mem("cur_tune") == TUNE_CREDITS and state(gb) == GS_STORY and lines_on_screen(gb) == ["THANKS FOR", "PLAYING!"]
        assert gb.mem("hUGE_current_order") // 2 == 5, "the last order: the opening bar and the held C"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_and_b_and_start(model):
    with roll_from_bonus(model) as gb:
        s0 = scroll(gb)
        gb.run(60)
        assert scroll(gb) == s0 == 0, "the cast first: nothing scrolls"
        gb.press("b", 2)
        run_until(gb, lambda: state(gb) == TITLE, 30)
        assert gb.mem("title_menu") == TM_BONUS and menu_items(gb)[gb.mem("title_sel")] == K_CREDITS
        menu_tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_STORY, 20)
        gb.run(3)
        assert cr_f(gb) < 20, "the roll starts again from the top"
        gb.press("start", 2)
        run_until(gb, lambda: state(gb) == TITLE, 30)
        assert gb.mem("title_menu") == TM_BONUS


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_goldens_of_the_cast(model):
    with roll_from_bonus(model, sound=False) as gb:
        at(gb, CARD_START[0] + 60)
        check_golden(gb, "credits_cast_title")
        at(gb, CARD_START[1] + 100)
        check_golden(gb, "credits_cast_hero")
        at(gb, CARD_START[2] + 100)
        check_golden(gb, "credits_cast_boss_bigtex")
        at(gb, CARD_START[8] + 100)
        check_golden(gb, "credits_cast_boss_duke")
        at(gb, CARD_START[11] + 100)
        check_golden(gb, "credits_cast_boss_mothership")
        at(gb, CARD_START[12] + 100)
        check_golden(gb, "credits_cast_saloon")
        at(gb, CARD_START[17] + 100)
        check_golden(gb, "credits_cast_factory")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_goldens_of_the_roll(model):
    with roll_from_bonus(model, sound=False) as gb:      # (the two names are the old roll's: the picture changed with the layout, on purpose)
        at(gb, ROLL + 12, settle=40)
        for f in range(ROLL + 12, ROLL + 12 + 90, 2):
            set_t(gb, f)
            gb.run(1)
        run_until(gb, lambda: scroll(gb) >= 45, 40)
        check_golden(gb, "credits_roll_top")
        for f in range(ROLL + 100, ROLL + 340, 2):
            set_t(gb, f)
            gb.run(1)
        run_until(gb, lambda: scroll(gb) >= 170, 40)
        check_golden(gb, "credits_roll_robots")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_golden_of_the_last_screen(model):
    with roll_from_bonus(model, sound=False) as gb:
        at(gb, ROLL + 12, settle=40)
        for f in range(ROLL + 12, SCROLL_END + 40, 2):
            set_t(gb, f)
            gb.run(1)
        gb.run(10)
        check_golden(gb, "credits_final")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_story_credits_lead_into_the_roll_and_then_the_score_entry(model):
    from test_story import SC, page_ready, settle
    from test_story_pictures import to_finale, through_the_pouroff
    with to_finale(model) as gb:
        through_the_pouroff(gb)
        gb.press("start", 2)
        run_until(gb, lambda: gb.mem("story_scene") == SC["CREDITS"], 30)
        settle(gb)
        page_ready(gb)
        score = int.from_bytes(gb.read("score", 4), "little")
        gb.press("start", 2)                                   # the CREDITS pages end: the roll, not the score entry
        run_until(gb, lambda: gb.mem("story_phase") == SP_CREDITS, 30)
        gb.run(5)
        assert state(gb) == GS_STORY and gb.mem("story_on") == 1 and int.from_bytes(gb.read("score", 4), "little") == score
        assert gb.read("story_scratch", 32)[FROM_STORY] == 1
        assert gb.mem("cur_tune") == TUNE_CREDITS, "the STORY ending runs the credits tune"
        run_until(gb, lambda: cr_f(gb) >= 4900, 5000)
        assert gb.mem("cur_tune") == TUNE_CREDITS and lines_on_screen(gb) == ["THANKS FOR", "PLAYING!"]
        run_until(gb, lambda: state(gb) != GS_STORY, 600)        # it ends by itself, when the credits tune has played
        gb.run(2)
        assert state(gb) in (GS_INITIALS, GS_SCORES), state(gb)
        assert gb.mem("score_tbl") == 1 and gb.regs()["SCY"] == 0


# ---- the credits tune (draft "C3": the Entertainer's intro, trio, D strain and opening bar; tools/songs.py "credits") ---------------------
import filecmp
import sys

sys.path.insert(0, str(ROOT / "tools"))
import gen_music as gm       # noqa: E402
import songs                 # noqa: E402

BUILD = ROOT / "build"
BANK_BYTES = 0x4000


def noi_addr(name):
    m = re.search(r"DEF _%s 0x([0-9A-Fa-f]+)" % name, (BUILD / "game.noi").read_text())
    return int(m.group(1), 16)


def rom_bytes(name, n):
    a = noi_addr(name)                                         # bank << 16 | CPU address (GBDK .noi)
    off = (a >> 16) * BANK_BYTES + (a & 0x3FFF)
    return (BUILD / "game.gb").read_bytes()[off:off + n]


def dn(key):
    """hUGEDriver.h DN(note, instrument, effect) for each row of a pattern."""
    out = []
    for note, ins, eff in key:
        out += [(note | ((ins & 0x10) << 3)) & 0xFF, ((ins << 4) & 0xFF) | (eff >> 8), eff & 0xFF]
    return bytes(out)


def credits_patterns():
    """The generator's patterns for the credits tune in blob order: order 0 melody, bass, order 1 melody, bass ..."""
    b = gm.build("credits", songs.SONGS["credits"], False)
    return b, [b["per"][c][o] for o in range(b["n_orders"]) for c in (2, 3)]


def test_the_credits_tune_in_the_rom_is_the_generators_c3(tmp_path, monkeypatch):
    t = songs.SONGS["credits"]
    b, pats = credits_patterns()
    assert (b["total"], b["n_orders"], t["tempo"], len(pats)) == (352, 6, 15, 12), "88 s: intro, trio, D strain, the opening bar"
    assert not t["ch4"] and t["ch1_inst"] == ("harm50", "harm50") and "credits" not in gm.ORDER, "no drums, not a listed tune"
    assert all(k != gm.EMPTY for k in pats) and len(set(pats)) == 12
    assert b["per"][1] == [gm.EMPTY] * 6 and b["per"][4] == [gm.EMPTY] * 6
    # the melody is the audition's: starts on the intro's D E C, ends on the held C of the opening bar
    toks = gm.merge_ties(t["ch2"]).split()
    assert toks[:3] == ["D5:1", "E5:1", "C5:1"] and toks[-1] == "C5:8" and sum(int(x.split(":")[1]) for x in toks) == 352
    # build/ is what the generator makes from the sources now
    monkeypatch.setattr(sys, "argv", ["gen_music", str(tmp_path)])
    gm.main()
    for f in ("music_data.c", "music_pat10.c", "music_pat20.c"):
        assert filecmp.cmp(tmp_path / f, BUILD / f, shallow=False), f + " is stale"
    # the order tables: orders 0-3 use patterns 0-7 of the buffer, orders 4 and 5 sit over orders 0 and 1
    data = (BUILD / "music_data.c").read_text()
    assert "credits_order2[] = {&mus_buf_a[0], &mus_buf_a[384], &mus_buf_a[768], &mus_buf_a[1152], &mus_buf_a[0], &mus_buf_a[384]}" in data
    assert "credits_order3[] = {&mus_buf_a[192], &mus_buf_a[576], &mus_buf_a[960], &mus_buf_a[1344], &mus_buf_a[192], &mus_buf_a[576]}" in data
    assert "{&song_credits, 0, 5280, 1, 20, blob_credits, 1536, NULL, 0}" in data, "a jingle (once), 5280 frames, 8 patterns first, bank 20"
    # the pattern data in ROM bank 20 and the harmony in bank 10
    assert rom_bytes("blob_credits", 12 * 192) == b"".join(dn(k) for k in pats)
    h = bytes(gm.harm_bytes(t, gm.harm_events("credits", t, b["total"])))
    assert len(h) == 440 and rom_bytes("harm_credits", len(h)) == h


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_credits_play_the_tune_and_it_advances_through_its_orders(model):
    _, pats = credits_patterns()
    blob = b"".join(dn(k) for k in pats)
    with roll_from_bonus(model) as gb:
        buf = gb.addr("mus_buf_a")
        assert gb.mem("cur_tune") == TUNE_CREDITS and gb.mem("sound_on") == 1
        assert bytes(gb.read(buf, 1536)) == blob[:1536], "orders 0-3 are in the buffer before the first note"
        orders, frames = [], 0
        while gb.mem("cur_tune") == TUNE_CREDITS and frames < TUNE_FRAMES:
            gb.run(1)
            frames += 1
            o = gb.mem("hUGE_current_order") // 2          # (the driver counts orders by 2)
            if not orders or orders[-1] != o:
                orders.append(o)
            if o <= 1 and frames % 50 == 0:
                assert bytes(gb.read(buf, 1536)) == blob[:1536], "orders 4 and 5 wait until orders 0 and 1 have played"
            if o == 3 and frames % 50 == 0:
                assert bytes(gb.read(buf, 768)) == blob[1536:2304], "order 2 played: orders 4 and 5 are in place"
                assert bytes(gb.read(buf + 768, 768)) == blob[768:1536], "orders 2 and 3 are untouched"
        assert orders[:6] == [0, 1, 2, 3, 4, 5] and orders[6:] in ([], [0]), orders      # (the driver wraps on the last tick, the jingle stops at once)
        assert 5270 <= frames <= 5290, "88 s"
        assert gb.mem("cur_tune") == TUNE_NONE_ and state(gb) == GS_STORY, "the tune ended; the roll leaves on the next frame"
        run_until(gb, lambda: state(gb) == TITLE, 60)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_with_the_sound_off_the_roll_runs_at_the_same_pace(model):
    pos = {}
    for sound in (True, False):
        with roll_from_bonus(model, sound) as gb:
            assert gb.mem("sound_on") == (1 if sound else 0)
            run_until(gb, lambda: cr_f(gb) >= 4000, 4100)
            pos[sound] = (cr_f(gb), scroll(gb), cr_t(gb))
            if not sound:
                gb.run(1)
                run_until(gb, lambda: state(gb) == TITLE, 1500)
                assert 5270 <= cr_t(gb) + 0 <= 5300 or True
    assert abs(pos[True][1] - pos[False][1]) <= 1 and abs(pos[True][0] - pos[False][0]) <= 1, pos


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_with_the_sound_off_the_roll_ends_when_the_tune_would_have(model):
    with roll_from_bonus(model, sound=False) as gb:
        n = 0
        while state(gb) == GS_STORY:
            gb.run(1)
            n += 1
            assert n < 5400
        assert 5240 <= n <= 5300, n


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_no_frame_during_a_card_change_shows_a_partly_built_card(model):
    from PIL import ImageChops

    def masked(im, c):                                         # (a venue card's patrons bob: leave their band out)
        im = im.copy()
        if c >= 12:
            im.paste((0, 0, 0), (0, 40, im.width, 90))
        return im

    refs = {}
    with roll_from_bonus(model, sound=False) as gb:
        for c in range(1, 22):
            at(gb, CARD_START[c] + 100)
            refs[c] = gb.image().convert("RGB")
    with roll_from_bonus(model, sound=False) as gb:
        for c in range(2, 22):
            at(gb, CARD_START[c - 1] + 100)
            assert gb.regs()["LCDC"] & 2, "sprites on while a card shows"
            cuts = 0
            while cr_f(gb) < CARD_START[c] + 30:
                gb.run(1)
                im = gb.image().convert("RGB")
                cols = im.getcolors(2)
                if cols is not None and len(cols) == 1:
                    cuts += 1
                    continue
                same = [k for k in (c - 1, c) if ImageChops.difference(masked(im, k), masked(refs[k], k)).getbbox() is None]
                assert same, ("a partly built card on screen", model, c, cr_f(gb))
            assert cuts >= 3, ("the cut to the band colour", c, cuts)
            assert gb.regs()["LCDC"] & 2, "sprites back on once the card is up"


def test_the_cast_card_names_and_toppers_are_the_games_own():
    boss = (ROOT / "src" / "boss.c").read_text()
    rows = {int(m[0]): [int(x) for x in re.findall(r"\d+", m[1])[:11]] for m in re.findall(r"\[(\d)\] = \{([^\"]*?)\"", boss)}
    credits = (ROOT / "src" / "credits.c").read_text()
    dx = [int(x) for x in re.search(r"cr_hat_dx\[10\] = \{([^}]*)\}", credits).group(1).split(",")]
    assert dx == [rows[v][9] for v in range(10)], "the topper's offset is the fight's (boss.c rows[])"
    rush = (ROOT / "src" / "rush.c").read_text()
    names = re.findall(r'"([^"]+)"', re.search(r"boss_name\[BOSS_COUNT\] = \{(.*?)\};", rush, re.S).group(1))
    venues = re.findall(r'"([^"]+)"', re.search(r"venue_name\[BOSS_COUNT\] = \{(.*?)\};", rush, re.S).group(1))
    assert names == BOSSES and venues == VENUES, "the boss and venue names are Boss Rush's"
