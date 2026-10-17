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
TUNE_CREDITS = 15                          # src/music.h: after the 15 listed tunes
TUNE_NONE_ = 255
TUNE_FRAMES = 5400                         # the credits tune: 352 rows x 15 frames = 5280, and the roll's start
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
        assert state(gb) == GS_STORY and gb.mem("cur_tune") == TUNE_CREDITS, "the last line stays up while the 88 s tune plays"
        run_until(gb, lambda: state(gb) == TITLE, TUNE_FRAMES)          # (the tune ends, the roll with it)
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
        for _ in range(TUNE_FRAMES + 600):                     # it ends by itself, when the credits tune has played (A held)
            if state(gb) != GS_STORY:
                break
            gb.press("a", 1)
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
def test_with_the_sound_off_the_roll_ends_after_its_own_hold(model):
    with Rom(ROOT / "build" / "game.gb", model) as gb:
        gb.run(120)
        gb.model_name = model
        hold_stage_anim(gb)
        gb.write("sound_on", 0)
        title_pick(gb, K_BONUS, K_CREDITS)
        run_until(gb, lambda: gb.mem("story_phase") == SP_CREDITS, 20)
        run_until(gb, lambda: state(gb) == TITLE, 1300)        # 504 px at half a pixel a frame, then the hold: no waiting for a tune
