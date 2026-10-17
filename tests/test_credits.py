# The credits roll (src/credits.c; owner 2026-10-17): after the story's CREDITS pages (before the STORY score entry) and from the title's
# BONUS > CREDITS. The owner's lines in the story's lettering, centred, scrolling up; the Spigoteer and three robots under the "robot
# friends" line (at most 8 sprites on a line); A speeds the scroll, B / START skip (to the score entry, or back to BONUS on CREDITS).
import re
from contextlib import contextmanager

import pytest
from conftest import K_BONUS, K_CREDITS, MENU_SETTLE, ROOT, TM_BONUS, check_golden, hold_stage_anim, menu_items, menu_tap, menu_to, title_pick
from gbtools import Rom
from test_flow import GS_INITIALS, GS_SCORES, GS_STORY, TITLE, most_per_scanline, run_until, state, tilemap_row
from test_mg import GLYPH_CH

SP_CREDITS = 8
CR_AT = 0                                  # struct cr_state in story_scratch (src/credits.c): row[20], scroll(2), sub, next, t, hold, from_story
SCROLL, SUB, NEXT, T, HOLD, FROM_STORY = 20, 22, 23, 24, 25, 26
STORY_H = (ROOT / "build" / "story.h").read_text()
FONT = int(re.search(r"#define BAR_TILE_COUNT (\d+)", (ROOT / "build" / "art.h").read_text()).group(1))   # STORY_FONT_BASE (build/story.h)
PUNCT = {FONT + 0: ".", FONT + 1: ",", FONT + 2: "!", FONT + 3: "?", FONT + 4: "'", FONT + 5: "-", FONT + 6: ":"}
LINES = ["SPIGOTEER", "GAME DESIGN, MEDIA,", "AND STORY BY", "TONY", "AND HIS TIRELESS", "TEAM OF", "ROBOT FRIENDS", "MUSIC",
         "PUBLIC DOMAIN", "MELODIES, ARRANGED", "FOR THIS GAME", "SPECIAL THANKS TO:", "GBDK-2020", "SDCC", "HUGEDRIVER", "RGBDS",
         "SAMEBOY", "PYBOY", "PAN DOCS", "THE GBDEV", "COMMUNITY", "THANKS FOR PLAYING!"]
OBJ_ROBOTS = 100


def row_text(gb, r):
    return "".join(GLYPH_CH.get(t) or PUNCT.get(t) or " " for t in tilemap_row(gb, r, 0, 20)).strip()


def scroll(gb):
    return gb.read("story_scratch", 27)[SCROLL] | gb.read("story_scratch", 27)[SCROLL + 1] << 8


def cr_t(gb):
    return gb.read("story_scratch", 27)[T]


@contextmanager
def roll_from_bonus(model):
    with Rom(ROOT / "build" / "game.gb", model) as gb:
        gb.run(120)
        gb.model_name = model
        hold_stage_anim(gb)
        title_pick(gb, K_BONUS, K_CREDITS)
        run_until(gb, lambda: gb.mem("story_phase") == SP_CREDITS, 20)
        gb.run(2)
        yield gb


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
def test_the_roll_shows_every_line_and_the_sprites_stay_within_the_limit(model):
    with roll_from_bonus(model) as gb:
        seen, most, shown = set(), 0, set()
        for _ in range(1500):
            if state(gb) == TITLE:                             # (the end: BONUS; A held there would open the roll again)
                break
            gb.press("a", 1)                                   # (A held: the fast roll)
            for r in range(32):
                t = row_text(gb, r)
                if t:
                    seen.add(t)
            most = max(most, most_per_scanline(gb))
            shown |= {(s["tile"]) for s in gb.visible_sprites()}
        assert seen == set(LINES), sorted(seen ^ set(LINES))
        assert 0 < most <= 8, most
        assert {OBJ_ROBOTS, OBJ_ROBOTS + 6, OBJ_ROBOTS + 12} <= shown, "the three robots"
        assert state(gb) == TITLE, "the end: back to the title's BONUS"
        assert gb.mem("title_menu") == TM_BONUS and menu_items(gb)[gb.mem("title_sel")] == K_CREDITS
        assert gb.regs()["SCY"] == 0


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_speeds_the_scroll_and_b_or_start_skip_back_to_bonus(model):
    with roll_from_bonus(model) as gb:
        s0, t0 = scroll(gb), cr_t(gb)
        gb.run(60)
        slow = scroll(gb) - s0
        assert 28 <= slow <= 32, slow                           # half a pixel a frame
        s0 = scroll(gb)
        gb.press("a", 30)                                       # A held 30 frames: 2 px a frame
        fast = scroll(gb) - s0
        assert 56 <= fast <= 64, fast
        gb.press("b", 2)
        run_until(gb, lambda: state(gb) == TITLE, 30)
        assert gb.mem("title_menu") == TM_BONUS and menu_items(gb)[gb.mem("title_sel")] == K_CREDITS
        menu_tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_STORY, 20)     # (story_phase still says 8 from the first roll)
        gb.run(3)
        assert scroll(gb) < 20, "the roll starts again from the top"
        gb.press("start", 2)
        run_until(gb, lambda: state(gb) == TITLE, 30)
        assert gb.mem("title_menu") == TM_BONUS


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_goldens_of_the_roll(model):
    with roll_from_bonus(model) as gb:
        run_until(gb, lambda: cr_t(gb) >= 90, 200)
        check_golden(gb, "credits_roll_top")
        run_until(gb, lambda: scroll(gb) >= 170, 400)
        check_golden(gb, "credits_roll_robots")


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
        assert gb.read("story_scratch", 27)[FROM_STORY] == 1
        for _ in range(2000):                                  # it ends by itself (A held)
            if state(gb) != GS_STORY:
                break
            gb.press("a", 1)
        gb.run(2)
        assert state(gb) in (GS_INITIALS, GS_SCORES), state(gb)
        assert gb.mem("score_tbl") == 1 and gb.regs()["SCY"] == 0
