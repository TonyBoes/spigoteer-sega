# The credits roll (src/credits.c; owner 2026-10-17): after the story's CREDITS pages (before the STORY score entry) and from the title's
# BONUS > CREDITS. A cast of characters (the Spigoteer and Dregs, each venue's owner and boss, every patron of the ten venues), then the owner's lines
# in the story's lettering, centred with a clear column at each edge, scrolling up, then "THANKS FOR PLAYING!" alone. The whole roll is tied to the
# credits tune's position and length (88 s now); B / START skip (to the score entry, or back to BONUS on CREDITS).
import json
import re
from contextlib import contextmanager

import pytest
from conftest import K_BONUS, K_CREDITS, MENU_SETTLE, ROM, ROOT, TM_BONUS, check_golden, hold_stage_anim, menu_items, menu_tap, menu_to, title_pick
from gbtools import Rom
from test_flow import GS_INITIALS, GS_SCORES, GS_STORY, TITLE, most_per_scanline, run_until, state, tilemap_row
from test_mg import GLYPH_CH

SP_CREDITS = 8
TUNE_CREDITS = 16                          # src/music.h: TUNE_MAP 15, TUNE_CREDITS 16, TUNE_EWFAST 17
TUNE_NONE_ = 255
TUNE_FRAMES = 10700                        # the credits tune (Easy Winners, batch 5): 10700 frames (178.3 s; 9986 at 14 frames a row, slowed to 15 on the owner's word 2026-11-13); the pictures' own clock is 9692 (TOTAL): the last words wait for the tune's end
CR_AT = 0                                  # struct cr_state in story_scratch (src/credits.c)
SCROLL, POS, NEXT, T, PH, FROM_STORY = 20, 22, 24, 26, 38, 40      # struct cr_state's fields (the scrolling credits, src/credits.c)
TUNE_T, E_TITLE, CARD_LEN, ROLL_AT, F1_AT, K_AT, BN, BP, POSE = 39, 41, 43, 45, 47, 49, 50, 51, 52      # the timeline's fields (u16 each, K a byte), the boss card's
CR_PL = 61                                  # the patron card's length (u16, after skipq)
STORY_H = (ROOT / "build" / "story.h").read_text()
FONT = int(re.search(r"#define BAR_TILE_COUNT (\d+)", (ROOT / "build" / "art.h").read_text()).group(1))   # STORY_FONT_BASE (build/story.h)
PUNCT = {FONT + 0: ".", FONT + 1: ",", FONT + 2: "!", FONT + 3: "?", FONT + 4: "'", FONT + 5: "-", FONT + 6: ":"}
OBJ_ROBOTS = 100
# the timeline (frames of the 162 s tune; src/credits.c: shares of 1/392 of it: 7 a card, 11 a patron card, the title included, 33 cards, the roll to 362)
TOTAL, CARD_F, PAT_F, ROLL, SCROLL_END = 9692, 173, 271, 6689, 8946
ROLL_START = ROLL + 70                                          # (the roll's rows, the robots and the fades take 40 frames and a bit)
CARD_START = [0, CARD_F, 2 * CARD_F]
for _v in range(10):                                            # (per venue: the owner, the patrons (longer), the boss)
    _b = 3 * CARD_F + _v * (2 * CARD_F + PAT_F)
    CARD_START += [_b, _b + CARD_F, _b + CARD_F + PAT_F]
assert len(CARD_START) == 33 and CARD_START[-1] + CARD_F == ROLL
VENUES = ["THE SALOON", "THE STADIUM", "THE LUMBER LODGE", "THE BISTRO", "THE IGLOO", "THE ROBOT FACTORY", "THE CHROME COW", "THE TEAHOUSE",
          "THE JUNGLE ZOO", "THE SPACE LOUNGE"]
BOSSES = ["BIG TEX", "THE MASCOT", "SASQUATCH", "THE CRITIC", "THE YETI", "PROTOTYPE", "DUKE", "SUMO CHAMP", "LEO THE LION", "MOTHERSHIP"]
OWNERS = ["SADIE", "COACH", "JUNE", "COLBY", "AURORA", "MANAGER-BOT", "GRANNY", "HANA", "KIKI", "ZIZZ"]   # the story's own names (build/story_data.c st_names), in venue order
CT = json.loads((ROOT / "build" / "credits_text.json").read_text())          # the pre-rendered text (tools/gen_credits.py): every row, its cells, its ink boxes
_pool_src = (ROOT / "build" / "credits_text.c").read_text()
POOL = bytes(int(x) for x in re.search(r"ct_pool\[\d+\] = \{ ([^}]*) \}", _pool_src).group(1).split(","))
TEXT_ROWS = CT["rows"]
LABELS = CT["patrons"]                                          # the patrons' labels, in the order they stand (slot A, B, C)
assert len(LABELS) == 10 and CT["venues"] == VENUES and CT["owners"] == OWNERS and CT["bosses"] == BOSSES
# every card's lines, top to bottom (words of a row joined by one space): 0 the title, 1 the Spigoteer, 2 Dregs, then per venue the owner, the patrons, the boss
CARDS = [["CAST OF", "CHARACTERS"], ["SAL TAPLEY", "THE SPIGOTEER"], ["DREGS", "RIVAL"]]

for v in range(10):
    CARDS.append([VENUES[v], OWNERS[v]])                    # (the venue is the header, the top rows, through all three cards)
    CARDS.append([VENUES[v]])                                # (the patrons: the labels, below: DMG the three base looks on one row, Color 3 + 3 + 2 on three)
    CARDS.append([VENUES[v], BOSSES[v]])


def card_text(c, model):
    """card c's lines on the model: the patrons' labels are one row of the three base looks on the DMG, three rows (3, 3, 2) of all eight on Color"""
    text = CARDS[c]
    if c >= 3 and (c - 3) % 3 == 1:
        v = (c - 3) // 3
        text = text + [" ".join(LABELS[v][a:b]) for a, b in (((0, 3),) if model == "dmg" else ((0, 3), (3, 6), (6, 8)))]
    return text


KINDS = ["title", "spigoteer", "dregs"] + ["owner", "patrons", "boss"] * 10
ROLL_LINES = [t for t in CT["roll"] if t]


def bg_tile_addr(t):
    """Where BG tile id t is in VRAM (the tile data is at 0x8800 signed: ids 128-255 at 0x8800, 0-127 at 0x9000)."""
    return 0x8000 + 16 * t if t >= 128 else 0x9000 + 16 * t


def pool_tile(i):
    return POOL[16 * i:16 * i + 16]


def matched_rows(gb):
    """[(map row, name)] for the visible map rows (top to bottom) that are one of the pre-rendered text rows: the live cells' VRAM tiles are the pool's
    tiles, the empty ones the blank tile."""
    out = []
    for r in visible_rows(gb):
        ids = tilemap_row(gb, r, 0, 20)
        live = [c for c in range(20) if ids[c] != ids[0]]
        if not live:
            continue
        for name, info in TEXT_ROWS.items():
            if info["n"] == 0 or info["col"] != live[0] or info["col"] + info["n"] - 1 != live[-1]:
                continue
            if all((ids[info["col"] + i] == ids[0]) if cell == 65535 else bytes(gb.read(bg_tile_addr(ids[info["col"] + i]), 16)) == pool_tile(cell)
                   for i, cell in enumerate(info["cells"])):
                out.append((r, name))
                break
    return out


def row_text(gb, r):
    for rr, name in matched_rows(gb):
        if rr == r:
            return " ".join(i["text"] for i in TEXT_ROWS[name]["ink"])
    return ""


def row_cols(gb, r):
    """(first, last) tile column of the text row r, or None."""
    for rr, name in matched_rows(gb):
        if rr == r:
            i = TEXT_ROWS[name]
            return (i["col"], i["col"] + i["n"] - 1)
    return None


def text_rows(gb):
    return [r for r, _ in matched_rows(gb)]


def ink_centre(name):
    """The centre (px) of a row's ink (all its items together)."""
    boxes = TEXT_ROWS[name]["ink"]
    return (boxes[0]["x0"] + boxes[-1]["x1"] + 1) / 2


def scroll(gb):
    return gb.read("story_scratch", 32)[SCROLL] | gb.read("story_scratch", 32)[SCROLL + 1] << 8


def cr_t(gb):
    return gb.read("story_scratch", 32)[T] | gb.read("story_scratch", 32)[T + 1] << 8


def cr_f(gb):
    return cr_t(gb)                                            # (the roll runs on its own clock: the frames on the screen)


def set_t(gb, v):                                              # (sound off: the position is this counter)
    gb.write(gb.addr("story_scratch") + T, v & 255)
    gb.write(gb.addr("story_scratch") + T + 1, v >> 8)


@contextmanager
def roll_from_bonus(model, sound=True):
    with Rom(ROM, model) as gb:
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
    return len(CT["roll"])


def SCROLL_FRAC(f):
    """The scroll the position f should have reached: CR_LAST_T px over the roll's scroll span."""
    last_t = (18 + roll_rows() - 2) * 8 + 8 - 72
    return last_t * (f - (ROLL + 40)) / (SCROLL_END - (ROLL + 40))


def wall(gb, c0):
    """Wall-clock frames since the cycle stamp c0 (an emulator frame is not one wall frame while the LCD is off: the cards are built with it off)."""
    return int((gb.pb._cycles() - c0) / 70224)


def visible_rows(gb):
    """The map rows that are on the screen (the 32-row map scrolled by SCY), top to bottom."""
    scy = gb.regs()["SCY"]
    return [((scy >> 3) + r) % 32 for r in range(19 if scy & 7 else 18)]


ROLL_END = 10297      # frames from the credits' first frame to the roll's leave (its own clock; 10454 until 2026-11-13, when the spigot divider and the REGULARS and BOSS labels went: the cards are 3, 2 and 3 rows shorter)


def lines_on_screen(gb):
    return [row_text(gb, r) for r in text_rows(gb)]


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_credits_is_the_fourth_bonus_item_and_opens_the_roll(model):
    with Rom(ROM, model) as gb:
        gb.run(120)
        title_pick(gb, K_BONUS)
        gb.run(MENU_SETTLE)
        assert menu_items(gb) == [K_CREDITS, 7, 9, 10]
        from test_flow import title_text_row
        assert tilemap_row(gb, 7, 0, 20) == title_text_row("credits")
        menu_to(gb, K_CREDITS)
        menu_tap(gb, "a")
        run_until(gb, lambda: gb.mem("story_phase") == SP_CREDITS, 20)
        assert state(gb) == GS_STORY


@pytest.mark.only_model('dmg')
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_choosing_credits_in_bonus_starts_the_credits_tune_at_once(model):
    with Rom(ROM, model) as gb:
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
        assert gb.mem("music_frames") <= 8, "it starts with the screen: its position is at the beginning"
        gb.run(60)
        assert 55 <= gb.mem16("music_frames") <= 75, gb.mem16("music_frames")


def plan_looks():
    """the Graphics Atlas plan's names (plan_data.NAMES, and the extras' art labels), per venue in card order"""
    import ast
    tree = ast.parse((ROOT / "tools/artifacts/palette_plan/plan_data.py").read_text())
    names = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) and n.targets[0].id == "NAMES")
    return names


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
        assert gb.read("story_scratch", 64)[FROM_STORY] == 1
        assert gb.mem("cur_tune") == TUNE_CREDITS, "the STORY ending runs the credits tune"
        run_until(gb, lambda: gb.mem("cur_tune") != TUNE_CREDITS, 11000)      # the tune plays out (10700 ticks, some 70 frames more on the wall: the roll's builds lose a few)
        assert state(gb) == GS_STORY or state(gb) in (GS_INITIALS, GS_SCORES), "the roll leaves as the tune ends (it waited for it; slowed 11-13)"
        run_until(gb, lambda: state(gb) != GS_STORY, 300)      # it ends by itself (the tune ended last: it was waiting)
        assert state(gb) in (GS_INITIALS, GS_SCORES), state(gb)
        run_until(gb, lambda: gb.regs()["SCY"] == 0, 120)       # (the roll's last scroll stays until the next screen is built behind the drink)
        assert gb.mem("score_tbl") == 1
        assert gb.mem16("tune_unlocked") & 2, "the finale done: the finished-once fact (tune_unlocked bit 1, saved in byte 4 bit 5) that opens Level Clear, Game Over, Bonus Round and both Easy Winners"


# ---- the credits tune (batch 5: The Easy Winners, slow, one pass with a drum track, ending on a ringing chord; tools/songs.py "credits") ------
import filecmp
import sys

sys.path.insert(0, str(ROOT / "tools"))
import gen_music as gm       # noqa: E402
import songs                 # noqa: E402

BUILD = ROOT / "build"
BANK_BYTES = 0x4000
ORDERS = 12
ROWS = 707
ORDER_BYTES = 2 * gm.SLOT_BYTES                            # a melody and a bass pattern
FRAMES = 10700                                             # 707 rows x 15 frames and the last bars' ritard (16, 17, 19, 21, 24 frames a row from rows 688, 692, 696, 698, 700; was 14 and 15, 16, 18, 20, 22: 9986)


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


def test_the_credits_tune_in_the_rom_is_the_generators_output(tmp_path, monkeypatch):
    t = songs.SONGS["credits"]
    b, pats = credits_patterns()
    assert (b["total"], b["n_orders"], t["tempo"], len(pats)) == (ROWS, ORDERS, 15, 2 * ORDERS), "the whole piece and its ending"
    assert not t["ch4"] and t["ch1_inst"] == ("voice", "ring50") and gm.ORDER[16] == "credits", "no drum patterns (a drum track); a listed tune since the soundtrack player lists it (batch 5)"
    assert all(k != gm.EMPTY for k in pats) and b["per"][1] == [gm.EMPTY] * ORDERS and b["per"][4] == [gm.EMPTY] * ORDERS
    # the melody is the audition's: starts on the intro's D flat, ends on the ringing D flat 5 chord (instrument 5, the ring) and a rest
    toks = gm.merge_ties(t["ch2"]).split()
    assert toks[:3] == ["D#4:2", "C5:3", "A#4:1"] and toks[-2:] == ["C#5:6/5", "r:1"] and sum(int(x.split(":")[1].split("/")[0]) for x in toks) == ROWS
    assert len(gm.DUTY) >= 7 and gm.DUTY[songs.DUTY_RING - 1] == (0x08, 0x80, 0xC7) and gm.HARM_INST["ring50"] == (0x80, 0x97)
    # the length is the real frames: Fxx tempo changes counted (rows 688-691 at 15, 692-695 at 16, 696-697 at 18, 698-699 at 20, then 22 a row to the end)
    assert t["tempo_map"] == {688: 16, 692: 17, 696: 19, 698: 21, 700: 24}
    assert gm.pass_frames(ROWS, 15, 0, t["tempo_map"]) == FRAMES == ROWS * 15 + 4 * 1 + 4 * 2 + 2 * 4 + 2 * 6 + 7 * 9
    assert gm.pass_frames(ROWS, 15) == ROWS * 15
    # build/ is what the generator makes from the sources now
    monkeypatch.setattr(sys, "argv", ["gen_music", str(tmp_path)])
    gm.main()
    for f in ("music_data.c", "music_pat10.c", "music_pat22.c", "music_pat23.c", "music_pat24.c", "music_pat25.c", "music_pat26.c"):
        assert filecmp.cmp(tmp_path / f, BUILD / f, shallow=False), f + " is stale"
    # the order tables: orders 0-3 use patterns 0-7 of the buffer, order j >= 4 sits over order j & 3
    data = (BUILD / "music_data.c").read_text()
    for c, name in ((2, "credits_order2"), (3, "credits_order3")):
        want = ", ".join("&mus_buf_a[%d]" % (((o & 3) * 2 + c - 2) * gm.SLOT_BYTES) for o in range(ORDERS))
        assert f"{name}[] = {{{want}}}" in data, name
    assert "{&song_credits, 0, %d, 3, 22, blob_credits, 1536, groove_credits, 0}" % FRAMES in data, "a jingle (once), the real frames, 8 patterns first, bank 22, streamed (buf 3), a drum track"
    assert "groove_credits[] = {255, 0, 0, 1, 2, 3, 4, 5, 6}" in data, "the track's header: the mark and the identity table src/music.c's groove row reads the drum from"
    # the pattern data and the harmony are in ROM bank 22 (a bank of its own; the other tunes' harmony is in bank 24, with the jingles)
    assert rom_bank("blob_credits") == rom_bank("harm_credits") == 22 == gm.CREDITS_BANK
    assert rom_bank("harm_title") == rom_bank("blob_title") == gm.TITLE_BANK == 23, "the streamed title: its own bank too"
    assert rom_bank("harm_venue0") == gm.HARM_BANK == 24
    assert rom_bytes("blob_credits", len(pats) * gm.SLOT_BYTES) == b"".join(dn(k) for k in pats)
    # the drum track follows the patterns in the blob: one byte a row (0 none, 1-6 the kit b n t o m x), 707 rows, padded to the 12 orders; 352 hits, 88 kicks
    track = rom_bytes("blob_credits", len(pats) * gm.SLOT_BYTES + ORDERS * 64 + 2)[len(pats) * gm.SLOT_BYTES:]
    want = []
    for tok in t["track"].split():
        k, n = tok.split(":")
        want += [gm.DRUM_ID.get(k, 0)] + [0] * (int(n) - 1)
    assert list(track[:ORDERS * 64]) == want + [0] * (ORDERS * 64 - ROWS) and len(want) == ROWS
    assert sum(1 for x in want if x) == 352 and want.count(gm.DRUM_ID["b"]) == 88 and not any(want[:28]) and want[700] == gm.DRUM_ID["o"] and not any(want[701:])
    h = bytes(gm.harm_bytes(t, gm.harm_events("credits", t, b["total"])))
    assert len(h) == 586 and rom_bytes("harm_credits", len(h)) == h
    # the harmony and the tune's length agree: the last events are the ringing A flat and a rest
    assert h[-6:] == bytes([gm.note_no("G#4") | 0x80, 6, gm.HARM_REST, 1, 0, 0])


def test_the_generator_stores_a_repeated_pattern_again(tmp_path, monkeypatch):
    """The credits blob has one slot per order and channel, so an order that plays the same pattern as an earlier one (a repeated strain)
    is stored again, and the order tables point at the buffer slot of each order."""
    src = dict(songs.SONGS["credits"])
    src.update(ch2=" ".join(["C4:64"] * ORDERS), ch3=" ".join(["C3:64"] * ORDERS), ch1="", tempo_map=None, fx_map=None, track=None)
    monkeypatch.setitem(songs.SONGS, "credits", src)
    monkeypatch.setattr(sys, "argv", ["gen_music", str(tmp_path)])
    gm.main()
    blob = (tmp_path / "music_pat22.c").read_text()
    assert "blob_credits[] = {   // credits: 24 patterns" in blob and "harm_credits" not in blob
    assert blob.count("DN(") == 2 * ORDERS * 64, "all 2 x ORDERS slots are written out"
    assert f"{{&song_credits, 0, {64 * 15 * ORDERS}, 3, 22, blob_credits, 1536, NULL, 0}}" in (tmp_path / "music_data.c").read_text()


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
        c0 = gb.pb._cycles()
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
            frames = wall(gb, c0)
        assert orders[:ORDERS] == list(range(ORDERS)) and orders[ORDERS:] in ([], [0]), orders      # (the driver wraps on the last tick, the jingle stops at once)
        assert checks >= 2 * ORDERS - 2 and done >= set(range(ORDERS - 1)), (checks, done)
        assert FRAMES - 12 <= frames <= FRAMES + 2, "the jingle stop counts the tune's real frames (the ritard included): the roll's builds pump the music, no tick is lost"
        assert gb.mem("cur_tune") == TUNE_NONE_, "the tune ended (11-13: it ends after the roll's text, the last page waited for it)"
        run_until(gb, lambda: state(gb) == TITLE, 300)   # (the roll leaves a moment after the tune)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_tune_stops_after_the_final_chord_has_rung_out(model):
    """Rows 700-705 are the final chord (6 rows at 24 frames), row 706 a rest: the tune stops when the rest ends, about 2.4 s after the
    chord was struck and with nothing cut short; the row starts follow the tempo changes (16, 17, 19, 21, 24 frames a row)."""
    t = songs.SONGS["credits"]
    start, cur = [0], 15
    for r in range(ROWS):
        cur = t["tempo_map"].get(r, cur)
        start.append(start[-1] + cur)
    with roll_from_bonus(model) as gb:
        seen, frames = {}, 0
        c0 = gb.pb._cycles()
        while gb.mem("cur_tune") == TUNE_CREDITS and frames < FRAMES + 100:
            seen.setdefault((gb.mem("hUGE_current_order") // 2, gb.mem("hUGE_row")), frames)
            gb.run(1)
            frames = wall(gb, c0)
        for r in range(600, ROWS):
            assert abs(seen[(r // 64, r % 64)] - start[r]) <= 3, f"row {r} starts at frame {seen[(r // 64, r % 64)]}, the generator says {start[r]}"
        assert frames >= start[707] - 4, "the last row (a rest) is played out before the tune is cut"
        assert start[707] - start[700] == 6 * 24 + 24, "the chord rings for six rows, then the rest"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_with_the_sound_off_the_roll_runs_at_the_same_pace(model):
    pos = {}
    for sound in (True, False):
        with roll_from_bonus(model, sound) as gb:
            assert gb.mem("sound_on") == (1 if sound else 0)
            run_until(gb, lambda: cr_f(gb) >= 7000, 7100)
            pos[sound] = (cr_f(gb), scroll(gb), cr_t(gb))
    assert abs(pos[True][0] - pos[False][0]) <= 12 and abs(pos[True][1] - pos[False][1]) <= 8, ("the sound-off clock is the frames on the screen", pos)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_with_the_sound_off_the_roll_ends_when_the_tune_would_have(model):
    with roll_from_bonus(model, sound=False) as gb:
        n = 0
        while state(gb) == GS_STORY:
            gb.run(1)
            n += 1
            assert n < ROLL_END + 200
        assert ROLL_END - 60 <= n <= ROLL_END + 60, n            # (the roll's own end: 10454 frames; the leave, the drink to the next screen, is part of it)


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


HEAD = 16                                                      # the venue header: the top two tile rows (16 px)


def body_ink(im):
    """ink() of the card's body (everything under the header): the pixels that are not its top-left pixel's colour (band when the card is up, white when faded out)."""
    return ink(im.crop((0, HEAD, 160, 144)))


def body_energy(im):
    return energy(im.crop((0, HEAD, 160, 144)))


def head_ink(im):
    return ink(im.crop((0, 0, 160, HEAD)))


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


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_no_music_tick_is_lost_through_the_fades_and_the_tune_ends_on_wall_time(model):
    """The real-time stamps of the music's ticks (tests/tick_helpers.py): no interval over 1.6 frames (a stall) from the tune's start to its last
    tick, and the tune's span is its length (one tick a frame) within 2 frames: the fades and the LCD-off builds of the 33 cards cost it nothing."""
    from tick_helpers import FRAME, LATE, tick_log
    with Rom(ROM, model) as gb:
        gb.run(120)
        gb.model_name = model
        hold_stage_anim(gb)
        stamps = tick_log(gb)
        title_pick(gb, K_BONUS, K_CREDITS)
        run_until(gb, lambda: gb.mem("story_phase") == SP_CREDITS, 20)
        n0 = len(stamps)
        run_until(gb, lambda: gb.mem("cur_tune") != TUNE_CREDITS, TUNE_FRAMES + 200)
        s = stamps[n0:]
        s = s[3:]                                               # (the first ticks: the screen's own build before the tune sounds)
        iv = [(b - a) / FRAME for a, b in zip(s, s[1:])]
        worst = max(iv[:-1])
        assert worst <= LATE, ("a tick came late: the tune stalled", round(worst, 2), iv.index(worst))
        span = (s[-1] - s[0]) / FRAME
        assert abs(span - (len(s) - 1)) <= 2, ("the tune is one tick a frame", span, len(s))
        assert abs(span + 3 - (TUNE_FRAMES - 1)) <= 5, ("the tune's length in wall frames", span)


def _to_roll(gb, last=32):
    at(gb, CARD_START[last] + 5)                                    # the last card: the boss, who tints the map's attributes
    for f in range(ROLL_START - 40, ROLL_START, 2):
        set_t(gb, f)
        gb.run(1)
    run_until(gb, lambda: gb.read("story_scratch", 32)[CARD] == 201, 200)
    gb.run(40)                                                       # (the fade in)


@pytest.mark.parametrize("path", ["bonus", "story"])
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_roll_returns_to_its_caller_within_a_second_of_the_tune_with_the_screen_on(model, path):
    from tick_helpers import FRAME
    if path == "bonus":
        ctx = roll_from_bonus(model)
    else:
        from test_story_pictures import to_finale
        ctx = to_finale(model)
    with ctx as gb:
        if path == "story":
            from test_story import SC, page_ready, settle
            from test_story_pictures import through_the_pouroff
            through_the_pouroff(gb)
            gb.press("start", 2)
            run_until(gb, lambda: gb.mem("story_scene") == SC["CREDITS"], 30)
            settle(gb)
            page_ready(gb)
            gb.press("start", 2)
            run_until(gb, lambda: gb.mem("story_phase") == SP_CREDITS, 30)
        run_until(gb, lambda: gb.mem("cur_tune") != TUNE_CREDITS, 11000)    # (the tune ends last: 10700 frames, 15 a row; the roll's own end is at about 10450, its last page waits)
        end = gb.pb._cycles()
        run_until(gb, lambda: state(gb) != GS_STORY, 900)
        assert (gb.pb._cycles() - end) / FRAME <= 300, "the roll's end waited for the tune (slowed 11-13: it ends after the roll's text) and leaves by itself a moment after it"
        gb.run(120)                                                  # (the drink or the fade, then the next screen)
        assert gb.pb.memory[0xFF40] & 0x80, "the LCD is on"
        assert len(gb.image().convert("RGB").getcolors(10000)) >= 3, "a screen, not a blank one"
        assert state(gb) == (TITLE if path == "bonus" else state(gb)) and state(gb) != GS_STORY


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_no_frame_of_the_roll_runs_past_its_vblank(model):
    """A frame whose work runs past its VBlank makes the main loop wait out a whole frame (vq_frame_begin two frames after the last), and the tune pays a tick
    for it, unpredictably (the drift of 0 to 8 frames the roll's layout used to give it). 2026-11-13: the sprite stage writes only what moved, the roll's steps
    start only if they end by line 96 (cr_room), a tick due in the picture's last lines waits for the VBlank (music_pump_cr), the patrons' sprites are written in
    place: none left over the whole credits (the one gap is the first screen's build, behind the white)."""
    from tick_helpers import FRAME, tick_log
    with Rom(ROM, model) as gb:
        gb.run(120)
        gb.model_name = model
        hold_stage_anim(gb)
        stamps = tick_log(gb)
        noi = ROM.with_suffix(".noi").read_text()
        v = int([x for x in noi.splitlines() if x.startswith("DEF _vq_frame_begin ")][0].split()[2], 16)
        begins = []
        gb.pb.hook_register(v >> 16, v & 0xFFFF, lambda ctx: begins.append(gb.pb._cycles()), None)
        title_pick(gb, K_BONUS, K_CREDITS)
        run_until(gb, lambda: gb.mem("story_phase") == SP_CREDITS, 20)
        n0 = len(stamps)
        begins.clear()
        run_until(gb, lambda: gb.mem("cur_tune") != TUNE_CREDITS, TUNE_FRAMES + 200)
        gaps = [round((b - a) / FRAME) for a, b in zip(begins, begins[1:])]
        assert sum(1 for g in gaps if g == 2) <= 2 and not [g for g in gaps if g > 2][1:], ("frames that ran past their VBlank", sum(1 for g in gaps if g == 2))
        s = stamps[n0:][3:]
        span = (s[-1] - s[0]) / FRAME
        assert abs(span - (len(s) - 1)) <= 2, ("the tune's length follows the frames", span, len(s))
