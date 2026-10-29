# docs/minigames_bosses.md section 5: THE POUR-OFF (src/po.c), the story's finale in the SALOON: a race against Dregs, a second
# bartender, from the opposite end of the same four bars; the first to 20 serves wins, Dregs reaching 20 first or the lives running
# out (3) loses and restarts only the Pour-Off. Runs on the mini-game framework (src/mg.c, game 11), between FINALE_A and FINALE_B
# (src/story.c). Its state is in the mg union (src/po.h, tests/po_helpers.py parses it): no WRAM global of its own.
# Covered: the start (banner, HUD, the mirrored screen, Dregs's art and palette, the crowd), Dregs's AI (picks, think delays, the
# rubber band, empties, slips), the rules (travel times, first arrival, pass-through, the 4-mug cap, empties, lives), the perfect pour,
# the race to 20 and the end, a loss restarting only the Pour-Off, the story flow FINALE_A -> Pour-Off -> FINALE_B -> CREDITS, ARCADE
# unaffected, the sprites per line (bot games and a forced worst case) and bots for the tuning targets.
import json

import pytest
from conftest import GAME, ROM, ROOT, check_golden, hold_stage_anim, venue
from po_helpers import (BT_CATCH, BT_FAIL, BT_FILL, BT_IDLE, BT_SLIDE, DREGS_X, MG_POUROFF, MUGS, PD_FILL, PD_IDLE, PD_SLIDE,
                        PD_THINK, PD_WAIT, PM_BREAK, PM_EMPTY, PM_FREE, PM_FULL, PM_HELD, PR_DREGS, PR_LIVES, PR_PLAY, PR_WIN,
                        PS_DRINKING, PS_EMPTY, PS_THIRSTY, PT_AHEAD, PT_COMIC, PT_REACT, PT_SLIP, PT_THINK0, PT_THINK15,
                        SEAT_X, SEATS, SPOUT_D, SPOUT_X, STATE_SIZE, TAP_X, WIN, Bot, mug_set, oam, po, po_win, poke, pokes,
                        quiet, seat_set)
from test_bonus import lines
from test_flow import GS_STORY, patron_group_tiles, run_until, state, tilemap_row
from test_mg import (BLANK, GLYPH_CH, GS_MINI, MG_END, MG_INTRO, MG_PLAY, MG_STORY, frames, mg_enter, text, to_play, until)
from test_scores import booted
from test_venues import attr_row, cgb_palette

pytestmark = pytest.mark.timeout(600)

SEED = 0x5A17
BG_FLIP, BG_PAT = 77, 86                  # po.c: the left keg's mirrored tiles, then the three looks' 12 tiles each
OBJ_DREGS, OBJ_DMG = 128, 184             # Dregs's 5 pictures x 8 tiles; the DMG mug copies
OBJ_MUG, OBJ_FILL, OBJ_DRINK, OBJ_POUR, OBJ_CUE = 56, 76, 84, 40, 44
S_PALETTE, S_FLIPX = 0x10, 0x20
CROWD = [(0, 0, "cowboys_a"), (0, 1, "cowboys_b"), (3, 0, "chefs_a")]     # po.c po_crowd: patron group, variant
OUT = ROOT / "out" / "po"
SFX_BREAK = 4
START_LIVES = 3
CATCH_POSE = 8
PO_C = (ROOT / "src" / "po.c").read_text()
ART = json.loads((ROOT / "build" / "po.json").read_text())
PALS = json.loads((ROOT / "assets" / "palettes.json").read_text())
SALOON = venue("saloon")


# ---- driving -------------------------------------------------------------------------------------------------------------
def enter(model, seed=SEED, mode=MG_STORY):
    """A booted rom on the title, then the Pour-Off (the story's mode) on its intro banner."""
    rom = booted(model)
    hold_stage_anim(rom)
    rom.model_name = model
    mg_enter(rom, MG_POUROFF, mode, seed)
    return rom


def start(model, seed=SEED):
    """... played from the first frame: no new patron for a while (tests place their own), the game's whole-frame state."""
    gb = enter(model, seed)
    to_play(gb)
    frames(gb, 2)
    quiet(gb)
    return gb


@pytest.fixture(params=["dmg", "cgb"])
def pour(request):
    gb = start(request.param)
    yield gb
    gb.stop()


@pytest.fixture(params=["dmg", "cgb"])
def intro(request):
    gb = enter(request.param)
    yield gb
    gb.stop()


def shot(gb, name):
    OUT.mkdir(parents=True, exist_ok=True)
    gb.screenshot(OUT / f"{name}.{gb.model_name}.png", 4)


def hud(gb):
    """The race on the HUD (columns 13-19): 'Y12 D10'."""
    return "".join(GLYPH_CH.get(t, " ") if t != BLANK else " " for t in tilemap_row(gb, 0, 13, 7))


def lives_hud(gb):
    """The lives on the HUD (columns 7-8: the Spigoteer's head and one digit, owner 2026-10-14)."""
    from test_flow import tile_id
    head, d = tilemap_row(gb, 0, 7, 2)
    assert head == tile_id("HUD_HEAD"), "the head icon"
    return int(GLYPH_CH[d])


def score(gb):
    return gb.mem16("score") | (gb.mem16(gb.addr("score") + 2) << 16)


def hold(gb, key):
    """Hold a key: the frame that sees the press runs before any state is read (po() runs a paused frame, which would take it)."""
    gb.hold(key)
    frames(gb, 1)


def run(gb, n):
    frames(gb, n)
    return po(gb)


def run_to(gb, cond, limit=400):
    """Frame by frame (<= 10 sprites a line each) until cond(state): returns the state."""
    for _ in range(limit):
        s = po(gb)
        if cond(s):
            return s
        frames(gb, 1)
    raise AssertionError(f"not reached in {limit} frames: {po(gb)['d']}")


def calm(gb, think=255):
    """Dregs does not start a drink of his own (his think delay is long): a test places the drinks it looks at."""
    pokes(gb, {f"tune.{PT_THINK0}": think, f"tune.{PT_THINK15}": think, f"tune.{PT_COMIC}": 0})


def serve_ready(gb, bar, k, own, aux=0, slot=0):
    """A thirsty patron on the seat and a full drink of `own` a step before it (the next frame meets it)."""
    seat_set(gb, bar, k)
    sx = SEAT_X[k]
    mug_set(gb, slot, PM_FULL, (sx + 16 + 2) if own == 0 else (sx - 8 - 2), bar, own, aux)


def mug_x_of(s, i):
    return s["mug"][i]["x"]


def live_mugs(s):
    return [m for m in s["mug"] if m["st"]]


def vram_bg(gb, t):
    return bytes(gb.read((0x9000 + t * 16) if t < 128 else (0x8000 + t * 16), 16))


def rev(b):
    return int(f"{b:08b}"[::-1], 2)


# ---- the start -------------------------------------------------------------------------------------------------------------
def test_the_start(intro):
    gb = intro
    assert state(gb) == GS_MINI and gb.mem("mg_id") == MG_POUROFF == 11 and gb.mem("mg_mode") == MG_STORY
    assert gb.mem("mg_phase") == MG_INTRO and gb.mem("lives") == START_LIVES and lives_hud(gb) == 3
    assert text(gb, 2) == "THE POUR OFF" and text(gb, 3) == "GET 20 SERVES FIRST"
    assert hud(gb) == "Y00 D00"
    s = po(gb)
    assert s["res"] == PR_PLAY and s["y"]["bar"] == 1 and s["y"]["x"] == TAP_X and s["d"]["bar"] == 2 and s["d"]["x"] == DREGS_X
    assert not any(q["st"] for q in s["seat"]) and not live_mugs(s)
    assert s["tune"][PT_THINK0] == 27 and s["tune"][PT_THINK15] == 16 and s["tune"][PT_AHEAD] == 40 and s["tune"][PT_SLIP] == 60
    frames(gb, 30)
    shot(gb, "intro")
    check_golden(gb, "po_intro")
    to_play(gb)
    frames(gb, 6)
    st = SALOON["stage_map"]
    for r in (0, 1, 2):                               # the banner's rows 1-3 (row 1 is blank under it) are the stage again, a row a frame
        assert tilemap_row(gb, 1 + r, 0, 20) == st[r * 20:(r + 1) * 20], r
    assert gb.mem("overlay_on") == 0 and gb.mem16("mg_timer") == 0


def test_the_screen_is_the_saloon_with_a_mirrored_keg_and_spout_at_the_left_end(pour):
    """Four bars (wall, wall, counter) under the saloon's stage; the keg and the spout at the right as ever and their mirror
    images at the left, tile by tile (DMG cannot flip BG tiles: copies in free ids), in the same colours."""
    gb = pour
    bar = SALOON["bar_map"]
    attr = SALOON["bar_attr"]
    for b in range(4):
        for r in range(3):
            row = 5 + 3 * b + r
            t = tilemap_row(gb, row, 0, 20)
            assert t[3:17] == bar[r * 20 + 3:r * 20 + 17], (b, r)
            assert t[17:20] == bar[r * 20 + 17:r * 20 + 20], (b, r)
            for c in range(3):
                src = vram_bg(gb, t[19 - c])
                want = bytes(rev(x) for x in src)
                assert vram_bg(gb, t[c]) == want, (b, r, c, "the left end is the right end mirrored")
            if gb.model_name == "cgb":
                a = attr_row(gb, row)
                assert a[17:20] == attr[r * 20 + 17:r * 20 + 20] and a[0:3] == a[::-1][0:3] == attr[r * 20 + 17:r * 20 + 20][::-1]
    for r in range(4):
        want = SALOON["stage_map"][r * 20:(r + 1) * 20]
        if r not in (1, 2):
            assert tilemap_row(gb, 1 + r, 0, 20) == want
    assert tilemap_row(gb, 17, 0, 20) == [SALOON["floor_tile"]] * 20
    assert vram_bg(gb, BG_FLIP) != bytes(16)
    shot(gb, "start")


def test_dregs_has_his_own_art_and_palette_and_does_not_read_as_a_second_spigoteer(pour):
    gb = pour
    got = bytes(gb.read(0x8000 + OBJ_DREGS * 16, 40 * 16))
    assert got == bytes(ART["dregs"]) and ART["n"] == 40
    spig = bytes(gb.read(0x8000, 40 * 16))                                              # Sal's 5 pictures
    assert spig != got[:40 * 16] and sum(a != b for a, b in zip(spig, got)) > 300                 # nothing like it, byte for byte
    s = po(gb)
    d, y = [oam(gb, i) for i in range(4, 8)], [oam(gb, i) for i in range(4)]
    assert [e["tile"] for e in d] == [OBJ_DREGS + f for f in (0, 2, 4, 6)]            # his idle frame
    assert [e["tile"] for e in y] == [0, 2, 4, 6]
    if gb.model_name == "cgb":
        assert [e["prop"] & 7 for e in d] == [3] * 4 and [e["prop"] & 7 for e in y] == [0] * 4
        assert cgb_palette(gb, 3, True) == [0, 30 | 27 << 5 | 20 << 10, 22 | 20 << 5 | 23 << 10, 4 | 3 << 5 | 5 << 10]
    else:
        assert gb.mem(0xFF49) == 0xE4                                                     # OBP1
        assert [e["prop"] & S_PALETTE for e in d] == [S_PALETTE] * 4 and [e["prop"] & S_PALETTE for e in y] == [0] * 4
    assert d[0]["prop"] & S_FLIPX and not y[0]["prop"] & S_FLIPX                         # (idle: faces right, his art faces left)
    # the frame art (the Spigoteer's 5 pictures idle, walk1, walk2, fill, fail and Dregs's 5 pictures, 8 tiles each: entries top-left, top-right, bottom-left, bottom-right,
    # each an 8x16 pair of tiles): the pixels as colour indices
    def grid(tiles, f):
        g = {}
        for e, (cx, ty) in enumerate(((0, 0), (8, 0), (0, 16), (8, 16))):
            for part in (0, 1):
                n = f * 8 + e * 2 + part
                for y in range(8):
                    lo, hi = tiles[n * 16 + 2 * y], tiles[n * 16 + 2 * y + 1]
                    for x in range(8):
                        v = (lo >> (7 - x) & 1) | (hi >> (7 - x) & 1) << 1
                        if v:
                            g[(cx + x, ty + part * 8 + y)] = v
        return g
    for f, df in enumerate((0, 1, 2, 3, 4)):             # Sal's pictures against Dregs's idle, walk1, walk2, fill and fail
        a, b = grid(spig, f), grid(got, df)
        assert sum(a.get(k) != b.get(k) for k in set(a) | set(b)) > 100, f"frame {f}: a different picture"
        # the Spigoteer's white apron (colour 1 in his palette) is a big block; Dregs wears a grey jacket (colour 2) and no apron
        assert sum(v == 1 for v in a.values()) > 20 and sum(v == 2 for v in b.values()) > 25, f"frame {f}"
    assert (ROOT / "assets/art/dregs/dregs.txt").read_text().startswith("; Art: APPROVED by the owner 2026-10-29")


def test_the_crowd_is_three_looks_loaded_per_variant_from_their_groups(pour):
    """po_crowd: the saloon's cowboy and cowgirl and a chef (the finale crowd): each look's shift-0 pose and its 2 px sway pose
    (12 tiles) from its group's own bank, and on CGB the group's palette over the wall colour."""
    gb = pour
    for i, (g, v, pal) in enumerate(CROWD):
        data = patron_group_tiles(g)
        shift0 = data[(128 + v * 4) * 16:(128 + v * 4 + 4) * 16] + data[126 * 16:128 * 16]     # (option 2: 2 columns of its own, then the shared blank pair)
        shift2 = data[(v * 42 + 6) * 16:(v * 42 + 12) * 16]
        got = b"".join(vram_bg(gb, BG_PAT + i * 12 + k) for k in range(12))
        assert got == shift0 + shift2, (i, pal)
        if gb.model_name == "cgb":
            want = [SALOON["pal"][2][0]] + [int(c) for c in PALS[pal]["rgb15"]]
            assert cgb_palette(gb, 2 + i) == want, pal
    assert [c[2] for c in CROWD] == ["cowboys_a", "cowboys_b", "chefs_a"]


def test_the_state_fits_the_mini_game_union():
    assert STATE_SIZE <= 520, STATE_SIZE                    # STORY_SCRATCH; nothing of the Pour-Off is a WRAM global of its own
    wram = ROM.with_suffix(".noi").read_text()
    assert " _po_" not in wram.replace("_po_enter", "").replace("_po_update", "")


# ---- Dregs's AI -------------------------------------------------------------------------------------------------------------
def test_dregs_picks_thinks_fills_and_slides_and_the_serve_scores_for_him(pour):
    """One decision at a time: the shortest slide from his spout (bar 0's seat at x 40), 27 frames' think delay at 0 points, a
    fill of 16 frames, the slide (his drink starts under his spout, x 16, 2 px a frame); the first thirsty patron whose 16 px it
    meets takes it (x 34): +1 for him, and the empty he slides back at the end of the drink is caught at his end."""
    gb = pour
    seat_set(gb, 0, 0)
    s = run_to(gb, lambda s: s["d"]["st"] == PD_THINK, 6)
    assert s["d"]["bar"] == 0 and s["d"]["t"] == 27
    n = 0
    while s["d"]["st"] == PD_THINK:
        s = run(gb, 1)
        n += 1
    assert n == 27 and s["d"]["st"] == PD_FILL and s["d"]["t"] == 0 and s["d"]["frame"] == BT_FILL
    n = 0
    while s["d"]["st"] == PD_FILL:
        s = run(gb, 1)
        n += 1
    assert n == 17, "16 frames of filling, then the drink is on the bar"
    assert s["d"]["st"] == PD_SLIDE and s["d"]["frame"] == BT_SLIDE
    m = live_mugs(s)
    assert len(m) == 1 and (m[0]["st"], m[0]["bar"], m[0]["own"]) == (PM_FULL, 0, 1) and m[0]["x"] == SPOUT_D + 2
    xs = [m[0]["x"]]
    while True:
        s = run(gb, 1)
        if s["seat"][0]["st"] == PS_DRINKING:
            break
        xs.append(live_mugs(s)[0]["x"])
    assert xs == list(range(18, 34, 2)) and s["mug"][0]["x"] == 48                 # (held at the patron's hand)
    assert s["mug"][0]["st"] == PM_HELD and s["mug"][0]["aux"] == 0
    assert (s["d"]["score"], s["y"]["score"], s["seat"][0]["who"]) == (1, 0, 1)
    frames(gb, 2)
    assert hud(gb) == "Y00 D01"
    s = run_to(gb, lambda s: s["seat"][0]["st"] == PS_EMPTY, 70)
    m = live_mugs(s)
    assert len(m) == 1 and (m[0]["st"], m[0]["x"], m[0]["own"]) == (PM_EMPTY, 32, 1), "the empty starts at the patron's left"
    s = run(gb, 2)
    assert not live_mugs(s) and s["d"]["catch_pose"] > 0 and s["d"]["score"] == 1 and s["d"]["slip"] == 0


def test_the_think_delay_falls_with_his_score_and_the_rubber_band_follows_the_lead(pour):
    gb = pour
    cases = [((0, 0), 27), ((15, 15), 16), ((8, 8), 27 - 11 * 8 // 15), ((8, 4), 27 - 11 * 8 // 15 + 8), ((8, 12), 27 - 11 * 8 // 15 - 6),
             ((3, 0), 27 - 11 * 3 // 15), ((0, 4), 27 - 6)]
    for (d, y), want in cases:
        pokes(gb, {"d.score": d, "y.score": y, "d.st": PD_IDLE, "d.t": 0})
        seat_set(gb, 0, 0)
        s = run_to(gb, lambda s: s["d"]["st"] == PD_THINK, 6)
        assert s["d"]["t"] == want, (d, y, s["d"]["t"], want)
        pokes(gb, {"seat.0.st": PS_EMPTY, "d.st": PD_IDLE, "d.t": 0})


def test_the_pick_is_the_shortest_slide_not_claimed_by_a_drink_in_flight_with_a_comic_one_in_eight(pour):
    gb = pour
    pokes(gb, {f"tune.{PT_COMIC}": 0})
    seat_set(gb, 3, 1)                                  # x 72
    seat_set(gb, 1, 0)                                  # x 40: shorter
    s = run_to(gb, lambda s: s["d"]["st"] == PD_THINK, 6)
    assert s["d"]["bar"] == 1
    pokes(gb, {"d.st": PD_IDLE, "d.t": 0})
    mug_set(gb, 0, PM_FULL, 24, 1, 1)                   # his drink in flight on bar 1 takes that seat: the next pick is elsewhere
    frames(gb, 1)                                       # (the pass over the mugs counts it)
    pokes(gb, {"d.st": PD_IDLE, "d.t": 0})
    s = run_to(gb, lambda s: s["d"]["st"] == PD_THINK, 6)
    assert s["d"]["bar"] == 3
    # comic waste (PT_COMIC 1: every pick): a contested seat (the middle one) or a patron about to leave, not the shortest slide
    pokes(gb, {"d.st": PD_IDLE, "d.t": 0, "mug.0.st": PM_FREE, f"tune.{PT_COMIC}": 1, "seat.3.st": PS_EMPTY, "seat.10.st": PS_EMPTY})
    seat_set(gb, 0, 0)                                  # (x 40)
    seat_set(gb, 2, 2)                                  # (x 104; 480 frames left: not about to leave)
    seats = set()
    for _ in range(12):
        pokes(gb, {"d.st": PD_IDLE, "d.t": 0, "seat.7.st": PS_THIRSTY, "seat.7.t": 240})    # bar 2, k 1: contested
        s = run_to(gb, lambda s: s["d"]["st"] == PD_THINK, 6)
        seats.add(s["d"]["bar"])
    assert seats == {2}, "only the contested seat qualifies"
    pokes(gb, {f"tune.{PT_COMIC}": 0, "d.st": PD_IDLE, "d.t": 0})
    s = run_to(gb, lambda s: s["d"]["st"] == PD_THINK, 6)
    assert s["d"]["bar"] == 0, "without comic picks: x 40 on bar 0"


def test_travel_times_are_mirrored_every_seat_is_as_far_from_his_spout_as_its_mirror_is_from_yours(pour):
    gb = pour
    calm(gb)
    frames(gb, 6)                                         # (the banner's rows are back first: a row a frame)
    times = {}
    for own in (1, 0):
        for k in range(3):
            kk = k if own else 2 - k                          # (k-th nearest to its spout: the seat that mirrors it for you)
            bar = 0 if own else 1
            pokes(gb, {f"seat.{i}.st": PS_EMPTY for i in range(6)} | {"mug.0.st": PM_FREE, "mug.1.st": PM_FREE})
            seat_set(gb, bar, kk)
            mug_set(gb, 0, PM_FULL, SPOUT_X if not own else SPOUT_D, bar, own)
            n = 0
            while po(gb)["seat"][bar * 3 + kk]["st"] != PS_DRINKING:
                frames(gb, 1)
                n += 1
                assert n < 100
            times[own, k] = n
    for k in range(3):
        assert times[1, k] == times[0, k], (k, times)
    assert times[1, 0] < times[1, 1] < times[1, 2]


def test_a_contested_seat_goes_to_the_drink_that_arrives_first(pour):
    gb = pour
    calm(gb)
    for first, head in ((1, 2), (0, 2)):
        pokes(gb, {"seat.3.st": PS_EMPTY, "seat.4.st": PS_EMPTY, "mug.0.st": PM_FREE, "mug.1.st": PM_FREE, "d.score": 0, "y.score": 0})
        seat_set(gb, 1, 1)                                # the middle seat of bar 1: x 72 from both spouts
        mug_set(gb, 0, PM_FULL, SPOUT_D + (head if first else 0), 1, 1)
        mug_set(gb, 1, PM_FULL, SPOUT_X - (0 if first else head), 1, 0)
        s = run_to(gb, lambda s: s["seat"][4]["st"] == PS_DRINKING, 80)
        assert s["seat"][4]["who"] == first and (s["d"]["score"], s["y"]["score"]) == ((1, 0) if first else (0, 1))
        # the other drink passes the patron (drinking, not thirsty) and goes on to the far end
        pokes(gb, {"seat.4.t": 0})
        s = run_to(gb, lambda s: not any(m["st"] == PM_FULL for m in s["mug"]), 80)
        assert (s["d"]["score"], s["y"]["score"]) == ((1, 0) if first else (0, 1)), "one patron, one serve"
        pokes(gb, {"seat.4.st": PS_EMPTY, "mug.0.st": PM_FREE})


def test_a_drink_that_meets_no_thirsty_patron_reaches_the_far_end_and_is_taken_with_a_thanks(pour):
    gb = pour
    calm(gb)
    stage2 = SALOON["stage_map"][20:40]
    for own, x0, end in ((0, SPOUT_X, SPOUT_D), (1, SPOUT_D, SPOUT_X)):
        pokes(gb, {"mug.0.st": PM_FREE, "d.score": 0})
        mug_set(gb, 0, PM_FULL, x0, 3, own)
        n = 0
        s = po(gb)
        while s["mug"][0]["st"] == PM_FULL:
            s = run(gb, 1)
            n += 1
            assert n < 100
        assert n == abs(end - x0) // 2 == 60 and s["mug"][0]["st"] == PM_FREE
        assert (s["d"]["score"], s["y"]["score"], gb.mem("lives")) == (0, 0, 3), "no score, no penalty"
        frames(gb, 3)
        assert text(gb, 2) == "THANKS"
        s = run_to(gb, lambda s: s["note_t"] == 0, 60)
        frames(gb, 2)
        assert tilemap_row(gb, 2, 0, 20) == stage2, "the note goes, the stage is back"


def test_two_drinks_going_opposite_ways_on_one_bar_pass_each_other(pour):
    gb = pour
    calm(gb)
    mug_set(gb, 0, PM_FULL, SPOUT_X, 2, 0)
    mug_set(gb, 1, PM_FULL, SPOUT_D, 2, 1)
    crossed = False
    for _ in range(40):
        s = run(gb, 1)
        a, b = s["mug"][0], s["mug"][1]
        assert a["st"] == b["st"] == PM_FULL
        crossed |= a["x"] < b["x"]
    assert crossed and (s["d"]["score"], s["y"]["score"]) == (0, 0) and s["mug"][0]["x"] == SPOUT_X - 80 and s["mug"][1]["x"] == SPOUT_D + 80


def test_at_most_four_mugs_a_bar_and_a_drink_that_does_not_fit_waits_in_the_hand(pour):
    """Yours: the full glass stays under the spout (the sprite), nothing is lost; when there is room it slides. Dregs's too."""
    gb = pour
    calm(gb)
    for i in range(4):
        mug_set(gb, i, PM_EMPTY, 60 + 10 * i, 1, 1)          # bar 1, his empties (still far from his end)
    hold(gb, "a")
    s = run_to(gb, lambda s: s["y"]["fill"] == 16, 30)
    gb.release("a")
    s = run(gb, 1)
    assert s["y"]["hold"] == 1 and s["y"]["fill"] == 0 and sum(1 for m in s["mug"] if m["st"] == PM_FULL) == 0
    frames(gb, 3)
    assert oam(gb, 8)["y"] and oam(gb, 8)["tile"] == OBJ_FILL + 6, "the full glass under the spout"
    poke(gb, "mug.2.st", PM_FREE)
    run_to(gb, lambda s: s["y"]["hold"] == 0, 4)                 # (the pass over the mugs counts the room, the next frame uses it)
    s = run(gb, 0)
    full = [m for m in s["mug"] if m["st"] == PM_FULL]
    assert len(full) == 1 and full[0]["x"] == SPOUT_X - 2 and full[0]["own"] == 0
    # Dregs: the glass under his spout waits too
    pokes(gb, {f"mug.{i}.st": PM_FREE for i in range(8)})
    for i in range(4):
        mug_set(gb, i, PM_EMPTY, 90 + 6 * i, 0, 0)            # bar 0: yours, far from your tap
    frames(gb, 2)                                               # (the pass over the mugs counts them)
    pokes(gb, {"d.bar": 0, "d.st": PD_FILL, "d.t": 16, "y.bar": 3})
    s = run(gb, 2)
    assert s["d"]["hold"] == 1 and s["d"]["frame"] == BT_FILL and not any(m["own"] == 1 and m["st"] == PM_FULL for m in s["mug"])
    assert oam(gb, 9)["y"] and oam(gb, 9)["tile"] == OBJ_FILL + 6 and oam(gb, 9)["x"] == SPOUT_D + 8
    poke(gb, "mug.1.st", PM_FREE)
    s = run_to(gb, lambda s: s["d"]["hold"] == 0, 4)
    assert any(m["own"] == 1 and m["st"] == PM_FULL and m["x"] == SPOUT_D + 2 for m in s["mug"])


def test_dregs_catches_his_empty_at_his_end_when_he_is_there_and_slips_when_he_is_not(pour):
    gb = pour
    calm(gb)
    pokes(gb, {"d.bar": 0})
    mug_set(gb, 0, PM_EMPTY, 60, 0, 1)
    n = 0
    s = po(gb)
    while s["mug"][0]["st"] == PM_EMPTY:
        s = run(gb, 1)
        n += 1
        assert n < 60
    assert n == 60 - 32, n                                                      # (x <= 32 on his bar)
    assert s["mug"][0]["st"] == PM_FREE and s["d"]["slip"] == 0 and s["d"]["catch_pose"] > 0 and s["d"]["score"] == 0
    # he is on another bar and never gets there (a long reaction): the empty breaks at his end, -1 and he slips for 60 frames
    pokes(gb, {"d.bar": 2, "d.score": 3, f"tune.{PT_REACT}": 255})
    mug_set(gb, 0, PM_EMPTY, 40, 0, 1)
    frames(gb, 1)
    sfx = gb.mem(gb.addr("sfx_count") + SFX_BREAK)
    s = run_to(gb, lambda s: s["mug"][0]["st"] == PM_BREAK, 40)
    assert s["mug"][0]["x"] == 8 and s["d"]["score"] == 2 and s["d"]["slip"] == 60
    assert gb.mem(gb.addr("sfx_count") + SFX_BREAK) == sfx + 1 and gb.mem("lives") == 3, "his loss costs you nothing"
    frames(gb, 3)
    assert hud(gb) == "Y00 D02" and text(gb, 2) == "OOPS"
    seat_set(gb, 3, 0)                                   # a thirsty patron: out of action, he does nothing for 60 frames
    for _ in range(45):
        s = run(gb, 1)
        assert s["d"]["frame"] == BT_FAIL and s["d"]["st"] == PD_IDLE and not any(m["own"] == 1 and m["st"] == PM_FULL for m in s["mug"])
    s = run_to(gb, lambda s: s["d"]["slip"] == 0, 20)
    s = run_to(gb, lambda s: s["d"]["st"] == PD_THINK, 8)
    assert s["d"]["bar"] == 3
    # out of action, he cannot catch an empty either, and at 0 points a slip costs no point
    pokes(gb, {"d.slip": 60, "d.score": 0, "d.bar": 0, "d.st": PD_IDLE})
    mug_set(gb, 1, PM_EMPTY, 40, 0, 1)
    frames(gb, 1)
    s = run_to(gb, lambda s: s["mug"][1]["st"] == PM_BREAK, 40)
    assert s["d"]["score"] == 0 and s["d"]["slip"] == 60, s["d"]


def test_empties_arriving_together_on_four_bars_are_one_too_many_for_his_reaction(pour):
    """His reaction takes 10 frames each time he has to change bar and an empty can be caught for 24 frames: three arriving at
    once on three bars he catches, the fourth breaks (he slips)."""
    gb = pour
    calm(gb)
    pokes(gb, {"d.bar": 0, "d.score": 5})
    for b in range(4):
        mug_set(gb, b, PM_EMPTY, 40, b, 1)
    frames(gb, 1)
    s = run_to(gb, lambda s: s["d"]["slip"] > 0, 60)
    assert sum(1 for m in s["mug"] if m["st"] == PM_FREE) >= 3 and sum(1 for m in s["mug"] if m["st"] == PM_BREAK) == 1
    assert s["d"]["score"] == 4 and s["d"]["slip"] == 60


def test_your_empties_are_caught_overlapping_you_and_break_past_the_keg_costing_a_life(pour):
    gb = pour
    calm(gb)
    mug_set(gb, 0, PM_EMPTY, 100, 1, 0)                   # on your bar, you are at the tap
    frames(gb, 1)
    s = run_to(gb, lambda s: s["mug"][0]["st"] == PM_FREE, 40)
    s = run(gb, 1)
    assert s["y"]["catch_pose"] > 0 and s["y"]["frame"] == BT_CATCH and gb.mem("lives") == 3
    gb.run(1)
    base = score(gb)
    mug_set(gb, 0, PM_EMPTY, 90, 1, 0)
    run_to(gb, lambda s: s["mug"][0]["st"] == PM_FREE, 40)
    assert score(gb) == base + 100, "an empty caught: 100 points"
    # a bar you are not on: past x 144 it breaks (a life), the HUD loses a mug
    lives = gb.mem("lives")
    mug_set(gb, 0, PM_EMPTY, 140, 0, 0)
    frames(gb, 1)
    s = run_to(gb, lambda s: s["mug"][0]["st"] == PM_BREAK, 20)
    assert s["mug"][0]["x"] == 145 and gb.mem("lives") == lives - 1 == 2
    frames(gb, 3)
    assert lives_hud(gb) == 2 and gb.mem(gb.addr("last_sfx")) == SFX_BREAK
    s = run_to(gb, lambda s: s["mug"][0]["st"] == PM_FREE, 40)
    assert s["res"] == PR_PLAY


def test_you_walk_left_to_meet_an_empty_but_not_into_dregs(pour):
    gb = pour
    calm(gb)
    hold(gb, "left")
    s = run(gb, 120)
    gb.release("left")
    assert s["y"]["x"] == 44, "the walk stops short of Dregs's end"
    mug_set(gb, 0, PM_EMPTY, 40, 1, 0)                   # (an empty from his side of the seats, slides toward you)
    frames(gb, 1)
    s = run_to(gb, lambda s: s["mug"][0]["st"] == PM_FREE, 40)
    assert s["y"]["x"] == 44 and s["y"]["catch_pose"] > 0
    hold(gb, "right")
    s = run(gb, 70)
    gb.release("right")
    assert s["y"]["x"] == TAP_X


def test_three_lives_and_the_last_one_loses_the_race(pour):
    gb = pour
    calm(gb)
    base = score(gb)
    for i in range(3):
        mug_set(gb, i, PM_EMPTY, 144, 0, 0)
    frames(gb, 1)
    s = run_to(gb, lambda s: s["res"] != PR_PLAY, 20)
    assert s["res"] == PR_LIVES and gb.mem("lives") == 0 and gb.mem("mg_phase") == MG_END
    frames(gb, 3)
    assert text(gb, 2) == "OUT OF LIVES" and lives_hud(gb) == 0
    shot(gb, "lose_lives")
    check_golden(gb, "po_lose_lives")


# ---- the perfect pour -------------------------------------------------------------------------------------------------------
def pour_to(gb, pour_t):
    """Hold A at the tap until the sparkle window's counter reaches pour_t (None: release at once when full), then release."""
    hold(gb, "a")
    run_to(gb, lambda s: s["y"]["pour_t"] == pour_t if pour_t else s["y"]["fill"] == 16, 60)
    gb.release("a")


def test_the_perfect_pour_applies_in_the_pour_off(pour):
    """Story mode everywhere: released in the sparkle window (27-31 frames of the fill) the drink is PERFECT: the story score
    doubled for that serve and a cue; released before it or after it, ordinary. The race counts one point either way."""
    gb = pour
    calm(gb)
    for pt, perfect in ((20, False), (27, True), (31, True), (32, False)):
        pokes(gb, {"y.score": 0, "mug.0.st": PM_FREE, "mug.1.st": PM_FREE})
        seat_set(gb, 1, 2)
        pour_to(gb, pt)
        s = run_to(gb, lambda s: any(m["st"] == PM_FULL for m in s["mug"]), 5)
        full = [m for m in s["mug"] if m["st"] == PM_FULL]
        assert len(full) == 1 and full[0]["aux"] == int(perfect), (pt, full)
        base = score(gb)
        s = run_to(gb, lambda s: s["seat"][5]["st"] == PS_DRINKING, 40)
        assert s["y"]["score"] == 1 and score(gb) == base + (200 if perfect else 100), (pt, score(gb) - base)
        frames(gb, 6)
        if perfect:
            assert s["cue_t"] > 0 and oam(gb, 26)["tile"] == OBJ_CUE and oam(gb, 26)["y"], "the cue beside the caught mug"
            shot(gb, "perfect")
            if pt == 27:
                check_golden(gb, "po_perfect")
        else:
            assert oam(gb, 26)["y"] == 0
        pokes(gb, {"seat.5.st": PS_EMPTY, "cue_t": 0} | {f"mug.{i}.st": PM_FREE for i in range(4)})
        frames(gb, 2)
    assert oam(gb, 26)["y"] == 0


def test_the_sparkle_shows_in_the_glass_under_the_spout(pour):
    gb = pour
    calm(gb)
    hold(gb, "a")
    run_to(gb, lambda s: s["y"]["pour_t"] == 28, 60)
    frames(gb, 1)
    e = oam(gb, 8)
    assert e["tile"] == OBJ_POUR and e["x"] == SPOUT_X + 8
    assert e["prop"] == (1 if gb.model_name == "cgb" else S_PALETTE)
    run_to(gb, lambda s: s["y"]["pour_t"] == 32, 20)
    frames(gb, 1)
    assert oam(gb, 8)["tile"] == OBJ_POUR + 2, "the foam runs over"
    gb.release("a")


# ---- the race ------------------------------------------------------------------------------------------------------------------
def test_you_win_at_20_and_dregs_wins_at_20(pour):
    gb = pour
    calm(gb)
    pokes(gb, {"y.score": 19, "d.score": 7})
    serve_ready(gb, 1, 2, 0)
    frames(gb, 1)
    s = run_to(gb, lambda s: s["res"] != PR_PLAY, 10)
    assert s["res"] == PR_WIN and s["y"]["score"] == 20 and gb.mem("mg_phase") == MG_END
    frames(gb, 3)
    assert hud(gb) == "Y20 D07" and text(gb, 2) == "YOU WIN" and gb.mem("lives") == 3
    shot(gb, "win")
    check_golden(gb, "po_win")


def test_dregs_wins_when_he_reaches_20_first(pour):
    gb = pour
    calm(gb)
    pokes(gb, {"y.score": 7, "d.score": 19})
    serve_ready(gb, 0, 0, 1)
    frames(gb, 1)
    s = run_to(gb, lambda s: s["res"] != PR_PLAY, 10)
    assert s["res"] == PR_DREGS and s["d"]["score"] == 20
    frames(gb, 3)
    assert hud(gb) == "Y07 D20" and text(gb, 2) == "DREGS WINS"
    shot(gb, "dregs_wins")
    check_golden(gb, "po_dregs_wins")
    # the outro: nothing is left running (the patron drinks, his bartender is done)
    s = run(gb, 20)
    assert s["d"]["frame"] == BT_CATCH and s["y"]["frame"] == BT_FAIL


def test_the_hud_shows_both_scores(pour):
    gb = pour
    calm(gb)
    for y, d in ((0, 0), (5, 12), (12, 5), (19, 10), (3, 18)):
        pokes(gb, {"y.score": y, "d.score": d, "hudq": 1})
        frames(gb, 3)
        assert hud(gb) == f"Y{y:02d} D{d:02d}", (y, d)


def test_a_slip_and_a_perfect_cue_screens(pour):
    gb = pour
    calm(gb)
    pokes(gb, {"d.bar": 2, "d.score": 3, f"tune.{PT_REACT}": 255, "y.score": 4})
    seat_set(gb, 0, 1, v=1)
    seat_set(gb, 1, 0, v=2)
    seat_set(gb, 3, 2, v=0)
    mug_set(gb, 0, PM_EMPTY, 30, 0, 1)
    frames(gb, 5)
    s = run_to(gb, lambda s: s["d"]["slip"] > 0, 30)
    frames(gb, 4)
    shot(gb, "slip")
    check_golden(gb, "po_slip")


# ---- the sprites on a line -----------------------------------------------------------------------------------------------------
def test_at_most_ten_sprites_on_a_line_in_the_forced_worst_case(pour):
    """Both bartenders on one bar, both glasses under their spouts, four mugs on that bar, and the PERFECT cue asked for: 4 + 2 + 4 =
    10 on a line, and the cue is left out."""
    gb = pour
    calm(gb)
    best = 0
    hold(gb, "a")
    for i in range(4):
        mug_set(gb, i, PM_EMPTY, 30 + 10 * i, 1, 0)       # yours on bar 1: they slide right, not yet near your tap
    frames(gb, 2)                                         # (the pass over the mugs counts them: no fifth one is made)
    for f in range(12):
        pokes(gb, {"y.bar": 1, "d.bar": 1, "d.st": PD_FILL, "d.t": 16, "cue_t": 47, "cue_x": 90, "cue_y": 56 + 24 + 4})
        s = run(gb, 1)
        assert max(lines(gb)) <= 10
        best = max(best, max(lines(gb)))
        if f >= 3:
            assert oam(gb, 26)["y"] == 0, "no room for the cue"
    gb.release("a")
    assert best == 10, best
    shot(gb, "worst_line")


@pytest.mark.parametrize("seed", [1, 2])
def test_at_most_ten_sprites_on_a_line_through_whole_bot_games(seed):
    """A bot that plays the race through, every frame (both models); the worst line it reaches."""
    for model in ("dmg", "cgb"):
        gb = start(model, seed)
        bot = Bot(gb, perfect=False, lag=10, lead=12, react=30)
        worst = [0]

        def each(g):
            worst[0] = max(worst[0], max(lines(g)))
            assert worst[0] <= 10

        for _ in range(3000):
            if po(gb)["res"]:
                break
            bot.step(1, each)
        assert po(gb)["res"] == PR_WIN, model
        assert worst[0] >= 5
        gb.stop()


# ---- bots: the tuning targets ---------------------------------------------------------------------------------------------------
def play_through(gb, bot=None, limit=4000):
    """Frame by frame until the race is decided (a bot plays, or nobody); the state at the end."""
    for _ in range(limit):
        s = po(gb)
        if s["res"]:
            return s
        if bot:
            bot.step(1)
        else:
            frames(gb, 1)
    raise AssertionError("the race did not end")


STEADY = dict(perfect=False, lag=10, lead=12, react=30)     # sees a new patron after 30 frames, pauses 10 after a throw


def test_a_steady_player_wins_by_three_to_six_on_average():
    """The spec's tuning target ("a player who keeps a steady rhythm wins by 3-6"), measured with a bot that sees a new patron after
    30 frames, goes to an empty's bar 12 frames before it arrives and rests 10 frames after each throw: over 12 seeds."""
    margins = []
    for seed in range(11, 23):
        gb = start("cgb", seed)
        bot = Bot(gb, **STEADY)
        s = play_through(gb, bot)
        margins.append(s["y"]["score"] - s["d"]["score"])
        gb.stop()
    assert sum(m > 0 for m in margins) >= 10, margins
    assert 3 <= sum(margins) / len(margins) <= 7, margins


def test_the_same_game_plays_out_the_same_on_both_models():
    out = []
    for model in ("dmg", "cgb"):
        gb = start(model, 13)
        s = play_through(gb, Bot(gb, **STEADY))
        out.append((s["y"]["score"], s["d"]["score"], s["served"], gb.mem("lives")))
        gb.stop()
    assert out[0] == out[1] and out[0][0] == WIN


def test_a_lazy_player_loses_more_than_he_wins():
    wins = 0
    for seed in range(11, 19):
        gb = start("cgb", seed)
        s = play_through(gb, Bot(gb, perfect=False, lag=30, lead=12, react=60))
        wins += s["res"] == PR_WIN
        gb.stop()
    assert wins <= 3, wins


def test_an_idle_player_loses_to_dregs():
    gb = start("cgb", 5)
    pokes(gb, {"spawn_t": 1})
    s = play_through(gb)
    assert s["res"] == PR_DREGS and s["d"]["score"] == WIN and s["y"]["score"] == 0 and gb.mem("lives") == 3
    assert gb.mem("mg_phase") == MG_END
    gb.stop()


def test_a_player_who_ignores_empties_loses_his_lives():
    gb = start("cgb", 6)
    bot = Bot(gb, perfect=False, lag=10, lead=-1, react=30)
    s = play_through(gb, bot)
    assert s["res"] in (PR_LIVES, PR_DREGS) and not (s["res"] == PR_DREGS and gb.mem("lives") == 3) or s["res"] == PR_LIVES
    assert s["res"] != PR_WIN
    gb.stop()


def test_the_game_takes_about_half_a_minute_with_a_steady_player():
    gb = start("cgb", 14)
    t = 0
    bot = Bot(gb, **STEADY)
    while not po(gb)["res"] and t < 4000:
        bot.step(1)
        t += 1
    assert 20 * 60 <= t + 150 <= 60 * 60, t               # (the intro and the count-in are 150 frames more)
    gb.stop()


def test_a_frame_of_the_game_ends_before_the_next_vblank():
    """Perf: the logic of every frame of a whole bot game (PERFECT pours, notes, catches) ends before the next VBlank."""
    gb = start("cgb", 3)
    bot = Bot(gb, perfect=True, lag=10, lead=12, react=30)
    worst = 0
    over = 0
    while not po(gb)["res"]:
        bot.step(1)
        v = gb.mem16("perf_logic_last")
        worst = max(worst, v)
        over += v >= 144
    assert worst <= 150 and over <= 3, (worst, over)
    assert gb.mem("drain_ticks_max") <= 14 and gb.mem16("vq_late") == 0
    gb.stop()


# ---- the story ------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_finale_flow_finale_a_the_pour_off_finale_b_and_the_credits(model):
    from test_story import PORTRAITS, SC, SCENES, glyph_rows, page_ready, settle, text_rows
    from test_story_pictures import to_finale
    with to_finale(model) as gb:
        a = SCENES[SC["FINALE_A"]]
        assert [p["speaker"] for p in a["pages"]] == ["NARRATOR"] * 4 + ["SADIE", "DREGS", "SPIGOTEER", "NARRATOR"]
        assert a["pages"][5]["lines"] == ["HOLD IT! WHO", "POURS FIRST? I", "SAY: A POUR-OFF!"]
        assert a["pages"][6]["lines"] == ["GET 20 SERVES", "FIRST! YOU'RE ON,", "DREGS."]
        assert a["pages"][7]["lines"] == ["THE POUR-OFF WILL", "BE AT SADIE'S", "SALOON."]
        for k, p in enumerate(a["pages"]):
            if k:
                gb.press("a", 2)
            page_ready(gb)
            assert text_rows(gb) == glyph_rows(p["lines"]), k
        gb.press("a", 2)                                      # the last page: the Pour-Off
        run_until(gb, lambda: state(gb) == GS_MINI, 30)
        run_until(gb, lambda: gb.pb.memory[0xFF40] & 0x80, 10)
        assert gb.mem("mg_id") == MG_POUROFF and gb.mem("mg_mode") == MG_STORY and gb.mem("lives") == START_LIVES
        assert gb.mem("story_scene") == SC["FINALE_A"] and gb.mem("story_on") == 1
        assert text(gb, 2) == "THE POUR OFF" and text(gb, 3) == "GET 20 SERVES FIRST"
        to_play(gb)
        base = score(gb)
        bot = Bot(gb, **STEADY)
        s = play_through(gb, bot)
        assert s["res"] == PR_WIN and score(gb) > base, "the race is played in the story: its score counts"
        bot.release_all()
        run_until(gb, lambda: state(gb) == GS_STORY and gb.mem("story_scene") == SC["FINALE_B"], 200)
        settle(gb)
        b = SCENES[SC["FINALE_B"]]
        assert [p["portrait"] for p in b["pages"][:2]] == ["DREGS SORRY", "DREGS SORRY"]
        page_ready(gb)
        assert text_rows(gb) == glyph_rows(b["pages"][0]["lines"]) and gb.mem("story_cur") == PORTRAITS["DREGS SORRY"]["pid"]
        check_golden(gb, "story_dregs_sorry")
        for k in range(1, len(b["pages"])):
            gb.press("a", 2)
            page_ready(gb)
            assert text_rows(gb) == glyph_rows(b["pages"][k]["lines"]), k
        gb.press("a", 2)
        run_until(gb, lambda: gb.mem("story_scene") == SC["CREDITS"], 60)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_loss_restarts_only_the_pour_off(model):
    """Dregs reaching 20 or the lives running out: the same Pour-Off again from its banner (3 lives, 0 : 0), not FINALE_A and not
    a venue; the story score carries; a win after it goes on to FINALE_B."""
    from test_story import SC, settle
    from test_story_pictures import to_finale
    with to_finale(model) as gb:
        gb.press("start", 2)                                  # skips FINALE_A
        run_until(gb, lambda: state(gb) == GS_MINI, 30)
        run_until(gb, lambda: gb.pb.memory[0xFF40] & 0x80, 10)
        to_play(gb)
        frames(gb, 2)
        calm(gb)
        restarts = gb.mem("story_restarts")
        # 1. Dregs wins
        pokes(gb, {"y.score": 7, "d.score": 19})
        serve_ready(gb, 0, 0, 1)
        add = score(gb)
        run_to(gb, lambda s: s["res"] == PR_DREGS, 10)
        run_until(gb, lambda: gb.mem("mg_phase") == MG_INTRO and gb.pb.memory[0xFF40] & 0x80 and gb.mem("game_state") == GS_MINI, 120)
        gb.run(3)
        s = po(gb)
        assert s["res"] == PR_PLAY and (s["y"]["score"], s["d"]["score"]) == (0, 0) and gb.mem("lives") == START_LIVES
        assert text(gb, 2) == "THE POUR OFF" and hud(gb) == "Y00 D00" and lives_hud(gb) == 3
        assert gb.mem("story_scene") == SC["FINALE_A"] and gb.mem("story_restarts") == restarts and gb.mem("mg_id") == MG_POUROFF
        assert score(gb) >= add
        # 2. the lives run out
        to_play(gb)
        frames(gb, 2)
        calm(gb)
        for i in range(3):
            mug_set(gb, i, PM_EMPTY, 144, 0, 0)
        run_to(gb, lambda s: s["res"] == PR_LIVES, 20)
        run_until(gb, lambda: gb.mem("mg_phase") == MG_INTRO and gb.pb.memory[0xFF40] & 0x80 and gb.mem("game_state") == GS_MINI, 120)
        gb.run(3)
        assert po(gb)["res"] == PR_PLAY and gb.mem("lives") == START_LIVES and lives_hud(gb) == 3
        assert gb.mem("story_scene") == SC["FINALE_A"] and gb.mem("story_restarts") == restarts
        # 3. a win goes on
        to_play(gb)
        frames(gb, 2)
        calm(gb)
        pokes(gb, {"y.score": 19})
        serve_ready(gb, 1, 2, 0)
        run_to(gb, lambda s: s["res"] == PR_WIN, 10)
        run_until(gb, lambda: state(gb) == GS_STORY and gb.mem("story_scene") == SC["FINALE_B"], 200)


def test_arcade_does_not_play_the_pour_off():
    """ARCADE ends its tour of the ten venues in "LOOP 2" (and a bonus round): the finale is the story's."""
    from test_arcade import BONUS, start_arcade
    from test_story import banner_text, centred, to_goal, win
    from test_flow import GS_GOAL
    with start_arcade("cgb") as gb:
        to_goal(gb)
        gb.write("story_chapter", 9)
        gb.write("story_step", 3)
        win(gb, 0, 0)
        seen = set()
        for _ in range(400):
            gb.run(1)
            seen.add((state(gb), gb.mem("mg_id") if state(gb) == GS_MINI else -1))
            if state(gb) == BONUS:
                break
        assert state(gb) == BONUS and (GS_MINI, MG_POUROFF) not in seen
        gb.write("bonus_phase", 4)
        gb.write("bonus_timer", 129)
        run_until(gb, lambda: state(gb) == GS_GOAL, 800)
        gb.run(3)
        assert gb.mem("arc_loop") == 2 and banner_text(gb, 2) == centred("LOOP 2")
        assert gb.mem("story_on") == 1 and gb.mem("story_arc") == 1 and gb.mem("mg_id") != MG_POUROFF


def test_dregs_glass_stream_falls_under_the_lowest_pixel_of_his_mirrored_spout(pour):
    """The glass under Dregs's spout reuses the spigot fill frames with their baked pour stream (aa867c0). His spout is yours mirrored
    about the screen's centre (screen x -> 159 - x), the glass sits at the mirrored x (16 for 136): the stream's columns must be
    centred on the mirror of the spout's lowest pixel run, as yours are on the spout (test_spigot)."""
    from test_spigot import nozzle, stream_pixels
    gb = pour
    calm(gb)
    pokes(gb, {"d.bar": 0, "d.st": PD_FILL, "d.t": 2, "y.bar": 3})
    ff = GAME["FILL_FRAMES"]
    for t_fill, k in ((1, 0), (ff // 3 + 1, 1), (2 * ff // 3 + 1, 2)):
        pokes(gb, {"d.st": PD_FILL, "d.t": t_fill})
        frames(gb, 2)
        o = oam(gb, 9)
        assert o["y"] and o["x"] - 8 == SPOUT_D and o["tile"] == OBJ_FILL + 2 * k, (k, o)
        cols = sorted({c for _, c in stream_pixels("saloon", k)})
        stream_x = [o["x"] - 8 + (7 - c if o["prop"] & 0x20 else c) for c in cols]
        run = nozzle("saloon")                                   # (yours: screen x of the spout's lowest run)
        want = (159 - run[0] + 159 - run[-1]) / 2
        assert abs(sum(stream_x) / len(stream_x) - want) <= 0.5, (k, stream_x, [159 - x for x in run])
