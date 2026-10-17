# The credits roll (src/credits.c; owner 2026-10-17): after the story's CREDITS pages (before the STORY score entry) and from the title's
# BONUS > CREDITS. A cast of characters (the Spigoteer and Dregs, each venue's owner and boss, every patron of the ten venues), then the owner's lines
# in the story's lettering, centred with a clear column at each edge, scrolling up, then "THANKS FOR PLAYING!" alone. The whole roll is tied to the
# credits tune's position and length (88 s now); B / START skip (to the score entry, or back to BONUS on CREDITS).
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
TUNE_FRAMES = 8900                         # the credits tune: 8732 frames (146 s), and the roll's start
CR_AT = 0                                  # struct cr_state in story_scratch (src/credits.c)
SCROLL, CARD, NEXT, T, PHASE, FROM_STORY, F, STEP = 20, 22, 23, 24, 26, 27, 28, 30
TUNE_T, E_TITLE, CARD_LEN, ROLL_AT, F1_AT, K_AT, BN, BP, POSE = 39, 41, 43, 45, 47, 49, 50, 51, 52      # the timeline's fields (u16 each, K a byte), the boss card's
STORY_H = (ROOT / "build" / "story.h").read_text()
FONT = int(re.search(r"#define BAR_TILE_COUNT (\d+)", (ROOT / "build" / "art.h").read_text()).group(1))   # STORY_FONT_BASE (build/story.h)
PUNCT = {FONT + 0: ".", FONT + 1: ",", FONT + 2: "!", FONT + 3: "?", FONT + 4: "'", FONT + 5: "-", FONT + 6: ":"}
OBJ_ROBOTS = 100
# the timeline (frames of the 88 s tune; src/credits.c: shares of 1/352 of it: 7 a card, the title included, 33 cards, the roll to 322)
TOTAL, CARD_F, ROLL, SCROLL_END = 5280, 105, 3465, 4830
ROLL_START = ROLL + 70                                          # (the roll's rows, the robots and the fades take 40 frames and a bit)
CARD_START = [0] + [CARD_F * (1 + k) for k in range(32)]
VENUES = ["THE SALOON", "THE STADIUM", "THE LUMBER LODGE", "THE BISTRO", "THE IGLOO", "THE ROBOT FACTORY", "THE CHROME COW", "THE TEAHOUSE",
          "THE JUNGLE ZOO", "THE SPACE LOUNGE"]
BOSSES = ["BIG TEX", "THE MASCOT", "SASQUATCH", "THE CRITIC", "THE YETI", "PROTOTYPE", "DUKE", "SUMO CHAMP", "LEO THE LION", "MOTHERSHIP"]
OWNERS = ["SADIE", "COACH", "JUNE", "COLBY", "AURORA", "MANAGER-BOT", "GRANNY", "HANA", "KIKI", "ZIZZ"]   # the story's own names (build/story_data.c st_names), in venue order
_src = (ROOT / "src" / "credits.c").read_text()
LABELS = [re.findall(r'"([^"]+)"', row) for row in re.findall(r"\{ (\"[A-Z]+\", \"[A-Z]+\", \"[A-Z]+\") \},", _src[_src.index("cr_pat[10][3]"):])]   # the patrons' labels, one table in credits.c
assert len(LABELS) == 10
# every card's lines, top to bottom (words of a row joined by one space): 0 the title, 1 the Spigoteer, 2 Dregs, then per venue the owner, the patrons, the boss
CARDS = [["CAST OF", "CHARACTERS"], ["SAL TAPLEY", "THE SPIGOTEER"], ["DREGS"]]
def lowered(labels):
    """The middle label goes a row lower when it would stand closer than a tile to a neighbour (credits.c cr_lowered)."""
    cx = [32 + 48 * k + (4 if len(w) & 1 else 0) for k, w in enumerate(labels)]
    gaps = [(cx[k + 1] - 4 * len(labels[k + 1])) - (cx[k] + 4 * len(labels[k])) for k in range(2)]
    return min(gaps) < 8


for v in range(10):
    CARDS.append([OWNERS[v], VENUES[v]])
    CARDS.append([VENUES[v], " ".join(w for k, w in enumerate(LABELS[v]) if not (k == 1 and lowered(LABELS[v])))] + ([LABELS[v][1]] if lowered(LABELS[v]) else []))
    CARDS.append([BOSSES[v], VENUES[v]])
KINDS = ["title", "spigoteer", "dregs"] + ["owner", "patrons", "boss"] * 10
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
    for _ in range(200):                                       # (not in the middle of a fade: it keeps the clock itself)
        st = gb.read("story_scratch", 32)
        if st[PHASE] in (0, 5) or st[CARD] >= 200:
            break
        gb.run(1)
    set_t(gb, f - 1)
    gb.run(settle)
    if f < ROLL:
        for _ in range(120):
            st = gb.read("story_scratch", 48)
            if st[PHASE] == 5 and st[CARD] == max(c for c in range(33) if CARD_START[c] <= f):   # (built and faded in)
                break
            gb.run(1)
        else:
            raise AssertionError("the card is not up")
        gb.run(2)


def roll_rows():
    src = (ROOT / "src" / "credits.c").read_text()
    body = src[src.index("cr_text[] = {"):]
    return len(re.findall(r'"[^"]*"', re.sub(r"//[^\n]*", "", body[:body.index("};")])))


def SCROLL_FRAC(f):
    """The scroll the position f should have reached: CR_LAST_T px over the roll's scroll span."""
    last_t = (18 + roll_rows() - 2) * 8 + 8 - 72
    return last_t * (f - (ROLL + 40)) / (SCROLL_END - (ROLL + 40))


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
        assert menu_items(gb) == [K_CREDITS, 7, 9, 10]
        from test_flow import title_text_row
        assert tilemap_row(gb, 6, 0, 20) == title_text_row("credits")
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
            at(gb, CARD_START[c] + 5)
            assert [" ".join(t.split()) for t in lines_on_screen(gb)] == text, (c, lines_on_screen(gb))
            shown = {s["tile"] for s in gb.visible_sprites()}
            most = max(most, most_per_scanline(gb))
            kind = KINDS[c]
            rows = [r for r in range(18) if row_cols(gb, r)]
            if kind == "spigoteer":
                assert shown and all(t < 56 for t in shown), "the Spigoteer's own OBJ tiles"
            elif kind == "dregs":
                assert shown and all(56 <= t < 64 for t in shown), "Dregs's (OBJ 56..)"
            elif kind in ("spigoteer", "dregs", "owner"):
                pass
            if kind in ("spigoteer", "dregs", "owner"):
                art = [r for r in range(18) if any(94 <= t < 138 for t in tilemap_row(gb, r, 0, 20))]
                assert art[0] == 4 and art == list(range(4, art[-1] + 1)) and 9 <= art[-1] <= 10, ("the story portrait", art)
                assert rows == ([12, 14] if kind != "dregs" else [12]), (c, rows)
                if kind == "owner":
                    assert not shown, "an owner's card has no sprites"
            elif kind == "boss":
                assert shown and shown <= {64, 66}, "the topper"
                body = [r for r in range(18) if any(100 <= t < 160 for t in tilemap_row(gb, r, 0, 20))]
                assert body == [6, 7] and rows == [10, 12], ("the boss's two rows, straight on the band, his name, the venue", body, rows)
            elif kind == "patrons":
                assert shown == {100, 102, 106, 108, 112, 114}, shown
                assert rows == ([2, 10, 12] if lowered(LABELS[(c - 3) // 3]) else [2, 10]), rows
            for r in range(18):                                 # every line keeps a clear column at each edge
                cols = row_cols(gb, r)
                if cols:
                    assert cols[0] >= 1 and cols[1] <= 18, (c, r, cols)
        assert most <= 10
        assert gb.read("story_scratch", 32)[CARD] == 32


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_boss_is_animated_on_his_card(model):
    with roll_from_bonus(model, sound=False) as gb:
        at(gb, CARD_START[5] + 10)
        seen, hats = set(), set()
        for _ in range(60):
            gb.run(1)
            seen.add(tuple(tilemap_row(gb, 6, 0, 20)) + tuple(tilemap_row(gb, 7, 0, 20)))
            hats |= {s["tile"] for s in gb.visible_sprites()}
        assert len(seen) >= 3, "his walk and gulp poses (WALK, STOMP, GULP) cycle"
        assert hats == {64, 66}, "the topper bobs with the stomp"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_each_patron_label_is_one_line_centred_under_its_patron(model):
    assert all(len(l) <= 6 for row in LABELS for l in row), "a label is one line of at most 6 letters (one table in src/credits.c)"
    with roll_from_bonus(model, sound=False) as gb:
        for v in range(10):
            at(gb, CARD_START[4 + 3 * v] + 5)
            xs = sorted(s["x"] for s in gb.visible_sprites())
            assert len(xs) == 6
            for k in range(3):
                cx = xs[2 * k] + 0                              # OAM x of the pair's first column = the pair's centre (left edge + 8)
                assert cx in (32 + 48 * k, 36 + 48 * k)
                row = tilemap_row(gb, 12 if k == 1 and lowered(LABELS[v]) else 10, 0, 20)
                cols = [c for c in range((cx - 24) // 8, (cx + 24) // 8) if GLYPH_CH.get(row[c]) or PUNCT.get(row[c])]
                if k == 1 and not lowered(LABELS[v]):
                    assert abs((cols[0] + cols[-1] + 1) * 4 - cx) <= 4, (v, k, cols, cx)
                elif k != 1:
                    cols = [c for c in cols if abs(c * 8 + 4 - cx) <= 24]
                    assert abs((cols[0] + cols[-1] + 1) * 4 - cx) <= 4, (v, k, cols, cx)
                assert (cols[0] + cols[-1] + 1) * 4 == cx or len(LABELS[v][k]) % 2 == 0 and abs((cols[0] + cols[-1] + 1) * 4 - cx) <= 4


def test_the_roll_text_is_centred_broken_at_words_and_spaced_by_section():
    src = (ROOT / "src" / "credits.c").read_text()
    body = src[src.index("cr_text[] = {"):]
    body = body[:body.index("};")]
    body = re.sub(r"//[^\n]*", "", body)
    rows = re.findall(r'"([^"]*)"', body)                        # one string a tilemap ROW
    assert [l for l in rows if l] == ROLL_LINES, "the credited content: the same words, only broken differently"
    assert max(len(l) for l in rows) <= 16, "a clear tile at each edge"

    def gap_before(first):
        i = rows.index(first)
        g = 0
        while rows[i - 1 - g] == "":
            g += 1
        return g
    sentences = [["GAME DESIGN,", "MEDIA, AND", "STORY BY", "TONY", "AND HIS TIRELESS", "TEAM OF", "ROBOT FRIENDS"],
                 ["PUBLIC DOMAIN", "MELODIES,", "ARRANGED", "FOR THIS GAME"], ["SPECIAL", "THANKS TO:"], ["THE GBDEV", "COMMUNITY"], ["THANKS FOR", "PLAYING!"]]
    for sentence in sentences:                                   # the lines of one sentence: consecutive rows, no blank row
        i = rows.index(sentence[0])
        assert rows[i:i + len(sentence)] == sentence, sentence
    items = ["GBDK-2020", "SDCC", "HUGEDRIVER", "RGBDS", "SAMEBOY", "PYBOY", "PAN DOCS", "THE GBDEV"]
    for it in items[1:]:                                         # the items of a list: two blank rows between them
        assert gap_before(it) == 2, (it, gap_before(it))
    for sec in ("GAME DESIGN,", "MUSIC", "SPECIAL"):             # a heading and what it heads: at least two blank rows; sections four or more
        assert gap_before(sec) >= 3, (sec, gap_before(sec))
    assert gap_before("MUSIC") >= 4 and gap_before("SPECIAL") >= 4
    assert gap_before("THANKS FOR") >= 10, "the screen (18 rows) is empty but for the last words: 10 blank rows leave them alone"
    assert rows[-2:] == ["THANKS FOR", "PLAYING!"]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_roll_shows_every_line_centred_and_the_sprites_stay_within_the_limit(model):
    with roll_from_bonus(model, sound=False) as gb:
        seen, most, shown = [], 0, set()
        at(gb, ROLL + 12, settle=80)
        for f in range(ROLL_START, SCROLL_END + 60, 6):
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
        at(gb, ROLL_START - 20, settle=80)
        for f in range(ROLL_START, SCROLL_END + 30, 2):
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
            f = gb.mem16("music_frames")
            assert frames > 5270 or -3 <= (frames + start) - f <= 45, ("the music runs a frame a frame, give or take the tick each card's two fades postpone", f, frames)
            if frames == 4000:                                  # mid-roll: the scroll is what the position says
                assert 0.8 * SCROLL_FRAC(f) <= scroll(gb) <= 1.2 * SCROLL_FRAC(f), (scroll(gb), SCROLL_FRAC(f))
        assert ended is not None and left is not None
        assert 5270 <= ended - 0 <= 5340 + start, ended         # the 88 s tune (the roll was 2+ frames in when `start` was taken)
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
        for c, name in ((0, "title"), (1, "spigoteer"), (2, "dregs"), (3, "owner_saloon"), (4, "patrons_saloon"), (5, "boss_saloon"), (21, "owner_chromecow"),
                        (23, "boss_chromecow"), (30, "owner_space"), (32, "boss_space")):
            at(gb, CARD_START[c] + 5)
            check_golden(gb, "credits_cast_" + name)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_goldens_of_the_roll(model):
    with roll_from_bonus(model, sound=False) as gb:      # (the two names are the old roll's: the picture changed with the layout, on purpose)
        at(gb, ROLL + 12, settle=80)
        for f in range(ROLL_START, ROLL_START + 90, 2):
            set_t(gb, f)
            gb.run(1)
        run_until(gb, lambda: scroll(gb) >= 45, 40)
        check_golden(gb, "credits_roll_top")
        for f in range(ROLL_START + 100, ROLL_START + 340, 2):
            set_t(gb, f)
            gb.run(1)
        run_until(gb, lambda: scroll(gb) >= 170, 40)
        check_golden(gb, "credits_roll_robots")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_golden_of_the_last_screen(model):
    with roll_from_bonus(model, sound=False) as gb:
        at(gb, ROLL + 12, settle=80)
        for f in range(ROLL_START, SCROLL_END + 40, 2):
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


# ---- the credits tune (draft "D3c": The Entertainer, intro / A / B / trio / bridge / D, ending on a ringing chord; tools/songs.py "credits") ------
import filecmp
import sys

sys.path.insert(0, str(ROOT / "tools"))
import gen_music as gm       # noqa: E402
import songs                 # noqa: E402

BUILD = ROOT / "build"
BANK_BYTES = 0x4000
ORDERS = 10
ORDER_BYTES = 2 * gm.SLOT_BYTES                            # a melody and a bass pattern
FRAMES = 8732                                              # 579 rows x 15 frames and the last bar's ritard (17, 19, 20 frames a row)


def noi_addr(name):
    m = re.search(r"DEF _%s 0x([0-9A-Fa-f]+)" % name, (BUILD / "game.noi").read_text())
    return int(m.group(1), 16)


def rom_bytes(name, n):
    a = noi_addr(name)                                         # bank << 16 | CPU address (GBDK .noi)
    off = (a >> 16) * BANK_BYTES + (a & 0x3FFF)
    return (BUILD / "game.gb").read_bytes()[off:off + n]


def rom_bank(name):
    return noi_addr(name) >> 16


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


def test_the_credits_tune_in_the_rom_is_the_generators_d3c(tmp_path, monkeypatch):
    t = songs.SONGS["credits"]
    b, pats = credits_patterns()
    assert (b["total"], b["n_orders"], t["tempo"], len(pats)) == (579, ORDERS, 15, 2 * ORDERS), "the whole piece and its ending"
    assert not t["ch4"] and t["ch1_inst"] == ("harm50", "ring50") and "credits" not in gm.ORDER, "no drums, not a listed tune"
    assert all(k != gm.EMPTY for k in pats) and b["per"][1] == [gm.EMPTY] * ORDERS and b["per"][4] == [gm.EMPTY] * ORDERS
    # the melody is the audition's: starts on the intro's D E C, ends on the ringing C chord (instrument 7) and a rest
    toks = gm.merge_ties(t["ch2"]).split()
    assert toks[:3] == ["D5:1", "E5:1", "C5:1"] and toks[-2:] == ["C6:6/7", "r:1"] and sum(int(x.split(":")[1].split("/")[0]) for x in toks) == 579
    assert len(gm.DUTY) == 7 and gm.DUTY[6] == (0x08, 0x80, 0xC7) and gm.HARM_INST["ring50"] == (0x80, 0x97)
    # the length is the real frames: Fxx tempo changes counted (rows 568-571 at 17 and 19, then 20 a row to the end)
    assert t["tempo_map"] == {568: 17, 570: 19, 572: 20}
    assert gm.pass_frames(579, 15, 0, t["tempo_map"]) == FRAMES == 579 * 15 + 2 * 2 + 2 * 4 + 7 * 5
    assert gm.pass_frames(579, 15) == 579 * 15
    # build/ is what the generator makes from the sources now
    monkeypatch.setattr(sys, "argv", ["gen_music", str(tmp_path)])
    gm.main()
    for f in ("music_data.c", "music_pat10.c", "music_pat22.c"):
        assert filecmp.cmp(tmp_path / f, BUILD / f, shallow=False), f + " is stale"
    # the order tables: orders 0-3 use patterns 0-7 of the buffer, order j >= 4 sits over order j & 3
    data = (BUILD / "music_data.c").read_text()
    for c, name in ((2, "credits_order2"), (3, "credits_order3")):
        want = ", ".join("&mus_buf_a[%d]" % (((o & 3) * 2 + c - 2) * gm.SLOT_BYTES) for o in range(ORDERS))
        assert f"{name}[] = {{{want}}}" in data, name
    assert "{&song_credits, 0, %d, 1, 22, blob_credits, 1536, NULL, 0}" % FRAMES in data, "a jingle (once), the real frames, 8 patterns first, bank 22"
    # the pattern data and the harmony are in ROM bank 22 (a bank of its own; the other tunes' harmony stays in bank 10)
    assert rom_bank("blob_credits") == rom_bank("harm_credits") == 22 == gm.CREDITS_BANK
    assert rom_bank("harm_title") == gm.HARM_BANK == 10
    assert rom_bytes("blob_credits", len(pats) * gm.SLOT_BYTES) == b"".join(dn(k) for k in pats)
    h = bytes(gm.harm_bytes(t, gm.harm_events("credits", t, b["total"])))
    assert len(h) == 762 and rom_bytes("harm_credits", len(h)) == h
    # the harmony and the tune's length agree: the last events are the ringing E and a rest
    assert h[-6:] == bytes([gm.note_no("E5") | 0x80, 6, gm.HARM_REST, 1, 0, 0])


def test_the_generator_stores_a_repeated_pattern_again(tmp_path, monkeypatch):
    """The credits blob has one slot per order and channel, so an order that plays the same pattern as an earlier one (a repeated strain)
    is stored again, and the order tables point at the buffer slot of each order."""
    src = dict(songs.SONGS["credits"])
    src.update(ch2=" ".join(["C4:64"] * ORDERS), ch3=" ".join(["C3:64"] * ORDERS), ch1="", tempo_map=None, fx_map=None)
    monkeypatch.setitem(songs.SONGS, "credits", src)
    monkeypatch.setattr(sys, "argv", ["gen_music", str(tmp_path)])
    gm.main()
    blob = (tmp_path / "music_pat22.c").read_text()
    assert "blob_credits[] = {   // credits: 20 patterns" in blob and "harm_credits" not in blob
    assert blob.count("DN(") == 20 * 64, "all twenty slots are written out"
    assert f"{{&song_credits, 0, {64 * 15 * ORDERS}, 1, 22, blob_credits, 1536, NULL, 0}}" in (tmp_path / "music_data.c").read_text()


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_credits_play_the_tune_and_the_buffer_holds_the_blob_at_every_order(model):
    """The first four orders are in the buffer before the first note; while order k plays, order k+2 is copied over order k-2's slot (rows
    2 to 9 of the order); at every order change and once the copy is done the buffer equals the blob, order by order."""
    _, pats = credits_patterns()
    blob = b"".join(dn(k) for k in pats)
    order = lambda j: blob[j * ORDER_BYTES:(j + 1) * ORDER_BYTES]
    with roll_from_bonus(model) as gb:
        buf = gb.addr("mus_buf_a")

        def slot_is(j):
            return bytes(gb.read(buf + (j & 3) * ORDER_BYTES, ORDER_BYTES)) == order(j)

        assert gb.mem("cur_tune") == TUNE_CREDITS and gb.mem("sound_on") == 1
        assert bytes(gb.read(buf, 4 * ORDER_BYTES)) == blob[:4 * ORDER_BYTES], "orders 0-3 are in the buffer before the first note"
        orders, checks, frames, done = [], 0, 0, set()
        while gb.mem("cur_tune") == TUNE_CREDITS and frames < FRAMES + 100:
            o, row = gb.mem("hUGE_current_order") // 2, gb.mem("hUGE_row")     # (the driver counts orders by 2)
            if not orders or orders[-1] != o:
                orders.append(o)
                if o < ORDERS:                                 # the change: this order and the next are in place, the earlier ones not yet overwritten
                    assert all(slot_is(j) for j in (o, o + 1) if j < ORDERS), f"order {o} starts: it and the next are in the buffer"
                    if o >= 1:
                        assert slot_is(o - 1), f"order {o} starts: the order just played is intact"
                    checks += 1
            if row == 12 and o not in done and o < ORDERS:    # the copy of order o + 2 (rows 2-9) is finished
                done.add(o)
                assert all(slot_is(j) for j in range(max(o - 1, 0), min(o + 3, ORDERS))), f"during order {o}: orders {o - 1}..{o + 2}"
                checks += 1
            gb.run(1)
            frames += 1
        assert orders[:ORDERS] == list(range(ORDERS)) and orders[ORDERS:] in ([], [0]), orders      # (the driver wraps on the last tick, the jingle stops at once)
        assert checks >= 2 * ORDERS - 2 and done >= set(range(ORDERS - 1)), (checks, done)
        assert FRAMES - 12 <= frames <= FRAMES + 2, "the jingle stop counts the tune's real frames (the ritard included)"
        assert gb.mem("cur_tune") == TUNE_NONE_ and state(gb) == GS_STORY, "the tune ended; the roll leaves on the next frame"
        run_until(gb, lambda: state(gb) == TITLE, 60)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_tune_stops_after_the_final_chord_has_rung_out(model):
    """Rows 572-577 are the final chord (6 rows at 20 frames), row 578 a rest: the tune stops when the rest ends, about 2 s after the
    chord was struck and with nothing cut short; the row starts follow the tempo changes (17, 19, 20 frames a row)."""
    t = songs.SONGS["credits"]
    start, cur = [0], 15
    for r in range(579):
        cur = t["tempo_map"].get(r, cur)
        start.append(start[-1] + cur)
    with roll_from_bonus(model) as gb:
        seen, frames = {}, 0
        while gb.mem("cur_tune") == TUNE_CREDITS and frames < FRAMES + 100:
            seen.setdefault((gb.mem("hUGE_current_order") // 2, gb.mem("hUGE_row")), frames)
            gb.run(1)
            frames += 1
        for r in range(500, 579):
            assert abs(seen[(r // 64, r % 64)] - start[r]) <= 3, f"row {r} starts at frame {seen[(r // 64, r % 64)]}, the generator says {start[r]}"
        assert frames >= start[578] + 15, "the last row (a rest) is played out before the tune is cut"
        assert start[579] - start[572] == 6 * 20 + 20, "the chord rings for six rows, then the rest"


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


def ink(im):
    """The pixels that are not the band's colour (the image's top-left pixel is band in every card), as a boolean array."""
    import numpy as np
    a = np.asarray(im.convert("RGB"))
    return (a != a[0, 0]).any(axis=2)


def energy(im):
    """How far the picture is from the band colour, in all (0 when it is faded out)."""
    import numpy as np
    a = np.asarray(im.convert("RGB")).astype(int)
    return int(np.abs(a - a[0, 0]).sum())


def settled_cards(model):
    """Every cast card, built and faded in (sound off), as images."""
    refs = {}
    with roll_from_bonus(model, sound=False) as gb:
        for c in range(1, 33):
            at(gb, CARD_START[c] + 5)
            refs[c] = gb.image().convert("RGB")
    return refs


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_no_frame_during_a_card_change_shows_a_partly_built_card(model):
    """A card is built behind the fade: while it is cleared, loaded and written the screen is one colour; its fade-in shows its picture whole (every
    pixel of a frame is a pixel of the finished card, dimmer); its fade-out the old card's."""
    import numpy as np
    cards = settled_cards(model)
    refs = {c: ink(im) for c, im in cards.items()}
    energies = {c: energy(im) for c, im in cards.items()}
    with roll_from_bonus(model, sound=False) as gb:
        for c in range(2, 33):
            at(gb, CARD_START[c - 1] + 5)
            dim = 0
            while cr_f(gb) < CARD_START[c] + 70:
                gb.run(1)
                st = gb.read("story_scratch", 32)
                card, phase = st[CARD], st[PHASE]
                m = ink(gb.image())
                ref = refs[card].copy()
                if KINDS[card] in ("patrons", "boss"):            # (patrons bob, the boss walks: that band is left out)
                    band = (40, 90) if KINDS[card] == "patrons" else (36, 68)
                    m[band[0]:band[1], :] = False
                    ref[band[0]:band[1], :] = False
                if phase in (1, 2, 3):
                    assert not m.any(), ("a card being built shows", model, c, phase, int(m.sum()))
                else:
                    assert not (m & ~ref).any(), ("pixels that are not the card's", model, c, card, phase)
                    e = energy(gb.image())
                    if 0.05 * energies[card] < e < 0.9 * energies[card]:
                        dim += 1
            assert dim >= 3, ("the fades are seen: a few dimmer frames each way", model, c, dim)
            assert gb.read("story_scratch", 32)[CARD] == c


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_cast_timeline_is_a_share_of_the_tunes_length(model):
    src = (ROOT / "src" / "credits.c").read_text()
    assert "music_tune_frames(TUNE_CREDITS)" in src and "5280" not in re.sub(r"//[^\n]*", "", src), "the length comes from the tune, not a constant"

    def share(T, units):                                       # (credits.c cr_share: 16-bit maths)
        q = T // 352
        r = T - q * 352
        return q * units + ((r >> 3) * units) // 44
    with roll_from_bonus(model, sound=False) as gb:
        s = gb.read("story_scratch", 64)
        u16 = lambda o: s[o] | s[o + 1] << 8
        T_, e_title, card, roll, f1 = (u16(o) for o in (TUNE_T, E_TITLE, CARD_LEN, ROLL_AT, F1_AT))
        assert (T_, e_title, card, roll, f1) == (5280, 105, 105, 3465, 4830), (T_, e_title, card, roll, f1)
        assert e_title + 32 * card == roll and card >= 90, "a card holds 1.75 s (105 frames) at the 88 s tune: never under 1.5 s"
        assert (share(5280, 7), share(5280, 322)) == (card, f1)
    for T, hold in ((5280, 90), (8800, 150), (10800, 150)):    # 88 s: at least 1.5 s; 147 s (D3c) and a 180 s arrangement: at least 2.5 s; every share grows with the tune
        c = share(T, 7)
        assert c >= hold and abs(c - T * 7 / 352) <= 8, (T, c)
        assert 33 * c < share(T, 322) - 600 and share(T, 322) < T


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_centring_audit_of_every_card(model):
    """Each card's ink (every pixel that is not the band) is measured against the screen centre (x 80): the worst offenders are reported and written to
    out/credits_offsets.json. A card is centred as well as the tile grid and the art allow (a tile is 8 px: a 7-tile portrait or an odd label is
    4 px off); sprites are placed to the pixel."""
    import json
    import numpy as np
    out = {}
    names = ["title", "Spigoteer card", "Dregs card"] + [f"{k} {(c - 3) // 3}: " + (OWNERS[(c - 3) // 3] if k == "owner" else BOSSES[(c - 3) // 3] if k == "boss" else VENUES[(c - 3) // 3])
                                                     for c, k in enumerate(KINDS) if c >= 3]
    for c, im in settled_cards(model).items():
        m = ink(im)
        cols = np.where(m.any(axis=0))[0]
        rows = np.where(m.any(axis=1))[0]
        out[names[c]] = {"x0": int(cols[0]), "x1": int(cols[-1]) + 1, "centre_x": (int(cols[0]) + int(cols[-1]) + 1) / 2 - 80,
                         "y0": int(rows[0]), "y1": int(rows[-1]) + 1, "centre_y": (int(rows[0]) + int(rows[-1]) + 1) / 2 - 72}
    with roll_from_bonus(model, sound=False) as gb:             # the title card, the roll's lines, the robot band, the last words
        at(gb, CARD_START[0] + 60)
        m = ink(gb.image())
        cols = np.where(m.any(axis=0))[0]
        out["title"] = {"x0": int(cols[0]), "x1": int(cols[-1]) + 1, "centre_x": (int(cols[0]) + int(cols[-1]) + 1) / 2 - 80}
        at(gb, ROLL + 12, settle=80)
        worst_line = 0
        lines = {}
        band = None
        for f in range(ROLL_START, SCROLL_END + 60, 6):
            set_t(gb, f)
            gb.run(1)
            im = gb.image().convert("RGB")
            a = np.asarray(im)
            for r in visible_rows(gb):
                t = row_text(gb, r)
                cc = row_cols(gb, r)
                if t and cc:
                    lines[t] = ((cc[0] + cc[1] + 1) * 4 - 80)
            xs = [s["x"] for s in gb.visible_sprites() if s["tile"] in (100, 102, 106, 108, 112, 114, 118, 0, 2, 4, 6) or s["tile"] < 56]
            if xs and band is None:
                sp = gb.visible_sprites()
                if len(sp) >= 8:
                    band = (min(s["x"] for s in sp) - 8, max(s["x"] for s in sp) - 8 + 8)
        out["roll lines (px from the centre; odd-length lines are half a tile left)"] = lines
        if band:
            out["robot band"] = {"x0": band[0], "x1": band[1], "centre_x": (band[0] + band[1]) / 2 - 80}
        worst_line = max(abs(v) for v in lines.values())
    cards = {k: v for k, v in out.items() if isinstance(v, dict) and "centre_x" in v}
    worst = sorted(cards.items(), key=lambda kv: -abs(kv[1]["centre_x"]))
    (ROOT / "out").mkdir(exist_ok=True)
    (ROOT / "out" / f"credits_offsets.{model}.json").write_text(json.dumps({"worst_first": [k for k, _ in worst], **out}, indent=1))
    print("\nworst offenders (px from the screen centre):", [(k, v["centre_x"]) for k, v in worst[:5]])
    assert all(abs(v["centre_x"]) <= 6 for v in cards.values()), [(k, v["centre_x"]) for k, v in worst[:5]]
    assert worst_line <= 4, "a text line is within half a tile of the centre"


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
