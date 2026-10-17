# The credits roll (src/credits.c; owner 2026-10-17): after the story's CREDITS pages (before the STORY score entry) and from the title's
# BONUS > CREDITS. The owner's lines in the story's lettering, centred, scrolling up; the Spigoteer and three robots under the "robot
# friends" line (at most 8 sprites on a line); A speeds the scroll, B / START skip (to the score entry, or back to BONUS on CREDITS).
import re
from contextlib import contextmanager

import pytest
from conftest import K_BONUS, K_CREDITS, MENU_SETTLE, ROM, ROOT, TM_BONUS, check_golden, hold_stage_anim, menu_items, menu_tap, menu_to, title_pick
from gbtools import Rom
from test_flow import GS_INITIALS, GS_SCORES, GS_STORY, TITLE, most_per_scanline, run_until, state, tilemap_row
from test_mg import GLYPH_CH

SP_CREDITS = 8
TUNE_CREDITS = 15                          # src/music.h: after the 15 listed tunes
TUNE_NONE_ = 255
TUNE_FRAMES = 8900                         # the credits tune: 8732 frames (146 s), and the roll's start
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
    with Rom(ROM, model) as gb:
        gb.run(120)
        gb.model_name = model
        hold_stage_anim(gb)
        title_pick(gb, K_BONUS, K_CREDITS)
        run_until(gb, lambda: gb.mem("story_phase") == SP_CREDITS, 20)
        gb.run(2)
        yield gb


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_credits_is_the_fourth_bonus_item_and_opens_the_roll(model):
    with Rom(ROM, model) as gb:
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
        assert state(gb) == GS_STORY and gb.mem("cur_tune") == TUNE_CREDITS, "the last line stays up while the 146 s tune plays"
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
    m = re.search(r"DEF _%s 0x([0-9A-Fa-f]+)" % name, ROM.with_suffix(".noi").read_text())
    return int(m.group(1), 16)


def rom_bytes(name, n):
    a = noi_addr(name)                                         # bank << 16 | CPU address (GBDK .noi)
    off = (a >> 16) * BANK_BYTES + (a & 0x3FFF)
    return ROM.read_bytes()[off:off + n]


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
    assert len(gm.DUTY) == 8 and gm.DUTY[6] == (0x08, 0x80, 0xC7) and gm.HARM_INST["ring50"] == (0x80, 0x97)
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
def test_with_the_sound_off_the_roll_ends_after_its_own_hold(model):
    with Rom(ROM, model) as gb:
        gb.run(120)
        gb.model_name = model
        hold_stage_anim(gb)
        gb.write("sound_on", 0)
        title_pick(gb, K_BONUS, K_CREDITS)
        run_until(gb, lambda: gb.mem("story_phase") == SP_CREDITS, 20)
        run_until(gb, lambda: state(gb) == TITLE, 1300)        # 504 px at half a pixel a frame, then the hold: no waiting for a tune
