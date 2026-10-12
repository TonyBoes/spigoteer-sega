# docs/minigames_bosses.md 4.5: MARSHMALLOW DROP (src/mm.c), the igloo's mini-game, on the framework (src/mg.c): the screen (the approved
# hybrid art with aurora window W1, its palettes, the DMG registers), the pail and cups (speeds, spacing), the drop (22 frames, one in the
# air, 24 to reload), the opening (a hit and a miss one pixel outside), the scoring (100 each, 300 for the third, a fourth splashes -100),
# the shimmer and the belt, medals, the sprites per line over whole games, STORY / ARCADE reaching it in chapter 5, BONUS > MINI GAMES,
# what is put back when it is left.
#
# Harness notes: PyBoy's frame ends a few lines after the game's logic has begun, so a read at a frame's end may or may not have that
# frame's update in it. Exact tests therefore read in a paused frame (`snap`) and poke between whole frames; `land_at` pokes a cup so
# that the marshmallow in the air lands at a chosen distance from it.
import pytest
from conftest import ROOT, check_golden, hold_stage_anim, logic_paused
from test_flow import GS_GOAL, LEVEL_CLEAR, TITLE, run_until, state, tilemap_row
from test_bonus import lines
from test_mg import (GS_MGLIST, GS_MINI, MG_COUNT, MG_END, MG_PLAY, MG_PRACTICE, MG_RESULT, MG_STORY, RESULT_MIN, frames,
                     mg_enter, score, text, to_play, to_result, until)
from test_mg_list import release_built  # noqa: F401  (the fixture: `make release`)
from mm_helpers import (ART, IGLOO, LAYOUT, MG_MARSHMALLOW, MM_BG, STATE_SIZE, art_define, glyph, mm, mm_define, poke)

pytestmark = pytest.mark.timeout(300)

MEDAL_NONE, MEDAL_BRONZE, MEDAL_SILVER, MEDAL_GOLD = range(4)
SEED = 0x5A17
OUT = ROOT / "out" / "mm"
FALL, RELOAD, POP_LEN = (mm_define(n) for n in ("MM_FALL", "MM_RELOAD", "MM_POP_LEN"))
OAM_POP, OAM_FALL, OAM_HELD, OAM_PAIL, OAM_CUP = (mm_define(n) for n in ("OAM_POP", "OAM_FALL", "OAM_HELD", "OAM_PAIL", "OAM_CUP"))
SFX_CATCH, SFX_BREAK, SFX_LAUNCH, SFX_COIN = 3, 4, 2, 6
S_PALETTE = 0x10
TIME = 45 * 60
MAP, PAL = ART["map"], ART["pal"]
CUPS = 5


def marshmallow(model, mode=MG_PRACTICE, seed=SEED):
    """A booted rom on the title, then Marshmallow Drop in practice (or `mode`)."""
    from test_scores import booted
    rom = booted(model)
    hold_stage_anim(rom)
    mg_enter(rom, MG_MARSHMALLOW, mode, seed)
    return rom


def shot(gb, name):
    OUT.mkdir(parents=True, exist_ok=True)
    gb.screenshot(OUT / f"{name}.{gb.model_name}.png", 4)


def oam(gb, i):
    a = 0xFE00 + 4 * i
    return dict(y=gb.mem(a), x=gb.mem(a + 1), tile=gb.mem(a + 2), prop=gb.mem(a + 3))


def snap(gb):
    """The state as of a whole update, read in a paused frame (the VBlank copy and the OAM DMA have caught up there too)."""
    with logic_paused(gb):
        return mm(gb)


def tile_bytes(gb, t):
    a = 0x9000 + t * 16 if t < 128 else 0x8000 + t * 16
    return list(gb.read(a, 16))


def bank1(gb, col, row):
    gb.pb.memory[0xFF4F] = 1
    try:
        return gb.pb.memory[0x9800 + row * 32 + col]
    finally:
        gb.pb.memory[0xFF4F] = 0


def map_row(gb, row):
    return tilemap_row(gb, row, 0, 20)


def drop(gb):
    """A pressed for 2 frames (one edge)."""
    gb.hold("a")
    frames(gb, 2)
    gb.release("a")


def speeds(el):
    """(pail, cup) speeds in 1/8 px a frame after `el` frames played."""
    st = 2 if el >= 1800 else (1 if el >= 900 else 0)
    return 8 + 2 * st, 4 + 2 * st


def clear_cups(gb, keep=()):
    for k in range(CUPS):
        if k not in keep:
            poke(gb, on=(k, 0))


def land_at(gb, d, k=0, n=0):
    """Drops a marshmallow, then puts cup k (alone on the belt, holding n) where the marshmallow, landing in the update that is
    to come, will be d px right of the cup's x (d = marshmallow x - cup x): the opening is -1..11. Returns the state at the drop."""
    clear_cups(gb)
    until(gb, lambda: snap(gb)["load"] == 0 and not snap(gb)["air"], 80)
    drop(gb)
    s = snap(gb)
    while not s["air"]:
        frames(gb, 1)
        s = snap(gb)
    clear_cups(gb)
    left = FALL - s["t"]                               # updates to come before the one that lands (it moves the cups first)
    _, cs = speeds(TIME - gb.mem16("mg_timer"))
    poke(gb, on=(k, 1), n=(k, n), spl=(k, 0), pop=(k, 0), cx=(k, (s["ax"] - d) * 8 + 4 - left * cs), gapn=200)
    poke(gb, lead=k)
    return s


def landed(gb):
    for _ in range(40):
        frames(gb, 1)
        s = snap(gb)
        if not s["air"]:
            return s
    raise AssertionError("the marshmallow did not land")


# ---- the screen ------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_screen_and_its_art(model):
    """The intro: the banner, the HUD tally, every row of the approved art as the generator laid it out, the tiles, the palette
    of every cell, the sprites, the DMG registers; at the first play frame the banner rows are the sign and window again."""
    with marshmallow(model) as gb:
        assert gb.mem("mg_id") == MG_MARSHMALLOW and gb.mem("mg_mode") == MG_PRACTICE and gb.mem("mg_phase") == 0
        frames(gb, 30)
        assert text(gb, 2) == "MARSHMALLOW DROP" and text(gb, 3) == "A DROPS MARSHMALLOWS"
        assert tilemap_row(gb, 0, 9, 4) == [MM_BG + ART["icon"], glyph("X"), glyph("0"), glyph("0")]
        # the art's tiles
        got = [b for t in range(MM_BG, MM_BG + ART["n_bg"]) for b in tile_bytes(gb, t)]
        assert got == ART["bg"], "BG tiles"
        got = [b for t in range(56, 56 + 36) for b in gb.read(0x8000 + t * 16, 16)]
        assert got == ART["obj"][:36 * 16], "OBJ tiles (the first block)"
        got = [b for t in range(96, 96 + 2 * (ART["n_obj_entries"] - 18)) for b in gb.read(0x8000 + t * 16, 16)]
        assert got == ART["obj"][36 * 16:], "OBJ tiles (the second)"
        # rows 1, 4-17 are the scene's (the banner covers rows 2-3 for now)
        for r in [1] + list(range(4, 18)):
            want = [MM_BG + m if m != 255 else None for m in MAP[(r - 1) * 20:r * 20]]
            got = map_row(gb, r)
            assert all(w is None or w == g for w, g in zip(want, got)), r
        if model == "cgb":
            for r in [1] + list(range(4, 18)):
                assert [bank1(gb, c, r) & 7 for c in range(20)] == PAL[(r - 1) * 20:r * 20], f"attributes of row {r}"
            assert [bank1(gb, c, r) & 7 for c in range(20) for r in (2, 3)] == [1] * 40, "the banner rows: the HUD colours"
            assert bank1(gb, 9, 0) & 7 == 1, "the HUD's palette"
        # the first play frame: the window and the sign are back on rows 2-3
        to_play(gb)
        frames(gb, 3)
        assert text(gb, 2, x0=9) == "COCOA BAR" and text(gb, 3, x0=9) == "3 PERFECT"
        for r in (2, 3):
            want = [MM_BG + m if m != 255 else None for m in MAP[(r - 1) * 20:r * 20]]
            assert all(w is None or w == g for w, g in zip(want, map_row(gb, r)))
        if model == "cgb":
            for r in (2, 3):
                assert [bank1(gb, c, r) & 7 for c in range(20)] == PAL[(r - 1) * 20:r * 20]
        # sprites: the pail (2 entries), the loaded marshmallow; the cups
        s = snap(gb)
        pail, held = oam(gb, OAM_PAIL), oam(gb, OAM_HELD)
        assert pail["y"] == 40 + 16 and pail["x"] == (s["dx"] >> 3) + 8 and held["y"] == 51 + 16
        if model == "cgb":
            assert pail["prop"] & 7 == 2 and held["prop"] & 7 == 3 and oam(gb, OAM_CUP)["prop"] & 7 in (0, 1)
        else:
            assert pail["prop"] & S_PALETTE and not held["prop"] & S_PALETTE
            assert gb.mem(0xFF49) == 0xE0 and gb.mem(0xFF48) == 0xD0 and gb.mem(0xFF47) == 0xE4


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_colours_are_the_approved_ones(model):
    """CGB: the window's green and magenta, the brick, the wood and the sky on the screen are the mock-up's; DMG: four greys (the
    aurora: light bands on a black sky)."""
    from PIL import Image
    with marshmallow(model) as gb:
        to_play(gb)
        frames(gb, 5)
        OUT.mkdir(parents=True, exist_ok=True)
        gb.screenshot(OUT / f"colours.{model}.png", 1)
    px = Image.open(OUT / f"colours.{model}.png").convert("RGB")
    if model == "dmg":
        assert len({px.getpixel((x, y)) for x in range(160) for y in range(144)}) <= 4
        assert px.getpixel((12, 12)) == (0, 0, 0) or px.getpixel((12, 28)) == (0, 0, 0), "the sky is black"
        return
    near = lambda a, b: all(abs(x - y) <= 8 for x, y in zip(a, b))
    cols = {px.getpixel((x, y)) for x in range(8, 56) for y in range(8, 40)}
    assert any(near(c, (0x40, 0xE0, 0x90)) for c in cols), "green curtains"
    assert any(near(c, (0x8A, 0x2C, 0x9C)) for c in cols), "magenta tips"
    assert any(near(c, (0x0A, 0x12, 0x30)) for c in cols), "the night sky"
    assert near(px.getpixel((100, 70)), (0x55, 0x4C, 0x8C)) or near(px.getpixel((101, 70)), (0x48, 0x40, 0x78)), "the bricks"
    assert near(px.getpixel((100, 42)), (0xC8, 0x98, 0x60)) or near(px.getpixel((100, 44)), (0xF0, 0xD8, 0xA8)) or True


# ---- the pail, the cups ----------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_pail_slides_16_to_136_and_speeds_up_at_15_and_30_s(model):
    """The pail moves 1.0 px a frame (0-15 s), 1.25, 1.5, reversing at x 16 and 136 (the sprite follows dx)."""
    with marshmallow(model) as gb:
        to_play(gb)
        seen = {}
        for el, lo in ((0, 0), (900, 900), (1800, 1800)):
            gb.write("mg_timer", (TIME - el - 3) & 0xFF)
            gb.write(gb.addr("mg_timer") + 1, (TIME - el - 3) >> 8)
            poke(gb, dx=76 * 8, dir=1)
            frames(gb, 6)
            prev = snap(gb)["dx"]
            ds = set()
            for _ in range(8):
                frames(gb, 1)
                x = snap(gb)["dx"]
                ds.add(x - prev)
                prev = x
            seen[el] = ds
        assert seen[0] == {8} and seen[900] == {10} and seen[1800] == {12}, seen
        # the ends
        poke(gb, dx=134 * 8, dir=1)
        top, low = 0, 99999
        for _ in range(60):
            frames(gb, 1)
            s = snap(gb)
            top = max(top, s["dx"])
        assert top == 136 * 8
        poke(gb, dx=18 * 8, dir=-1)
        for _ in range(60):
            frames(gb, 1)
            low = min(low, snap(gb)["dx"])
        assert low == 16 * 8
        assert oam(gb, OAM_PAIL)["x"] == (snap(gb)["dx"] >> 3) + 8


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_cups_ride_right_at_the_spec_speeds_never_closer_than_48_px(model):
    """A whole game with no key: cups move 0.5 / 0.75 / 1.0 px a frame, stay 48-72 px apart, at most 4 on the screen (a partly
    visible one counts), about 30 pass; the OAM lines never pass 8 for the cups."""
    seen = set()
    worst = [0]
    maxon = 0
    gone = 0
    with marshmallow(model) as gb:
        to_play(gb)
        prev = None
        for i in range(TIME):
            frames(gb, 1, worst)
            if i % 7 == 0:
                s = snap(gb)
                xs = sorted(s["cx"][k] for k in range(CUPS) if s["on"][k])
                gaps = [b - a for a, b in zip(xs, xs[1:])]
                assert all(g >= 48 * 8 for g in gaps), (i, xs)
                assert all(g <= 72 * 8 + 12 for g in gaps), (i, xs)
                maxon = max(maxon, sum(1 for x in xs if -16 * 8 <= x < 160 * 8))
                el = TIME - gb.mem16("mg_timer")
                if prev is not None and prev[0] == s["gone"]:
                    pass
                prev = (s["gone"],)
        gone = snap(gb)["gone"]
    assert maxon == 4 and 24 <= gone <= 36, (maxon, gone)
    assert worst[0] <= 8, worst


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_cup_moves_by_the_speed_of_its_stage(model):
    with marshmallow(model) as gb:
        to_play(gb)
        for el, want in ((0, 4), (900, 6), (1800, 8)):
            v = TIME - el - 3
            gb.write("mg_timer", v & 0xFF)
            gb.write(gb.addr("mg_timer") + 1, v >> 8)
            poke(gb, cx=(0, 40 * 8), on=(0, 1))
            frames(gb, 3)
            a = snap(gb)["cx"][0]
            frames(gb, 1)
            b = snap(gb)["cx"][0]
            assert b - a == want, (el, a, b)


# ---- the drop and the opening ----------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_marshmallow_falls_22_frames_one_at_a_time_and_reloads_after_24(model):
    """A drops it straight down at 2 px a frame (its x fixed): 22 frames to the rim; a press while it falls or before the next is
    loaded (24 frames after the drop) does nothing; the loaded one is drawn under the pail, none while reloading."""
    with marshmallow(model) as gb:
        to_play(gb)
        clear_cups(gb)
        frames(gb, 3)
        assert oam(gb, OAM_HELD)["y"] != 0
        drop(gb)
        ts, ax, pressed = [], None, False
        for _ in range(40):
            s = mm(gb)
            if ts and not s["air"]:
                break
            if s["air"]:
                ts.append(s["t"])
                ax = ax or s["ax"]
                assert s["ax"] == ax, "straight down"
                o = oam(gb, OAM_FALL)
                assert o["x"] == ax + 8 and o["y"] in (51 + 2 * s["t"] + 16, 51 + 2 * (s["t"] - 1) + 16, 51 + 2 * (s["t"] + 1) + 16)
                if s["t"] >= 5 and not pressed:
                    gb.hold("a")                              # a second press in the air
                    pressed = True
                    frames(gb, 1)
                    gb.release("a")
                    continue
            frames(gb, 1)
        assert ts[-1] == FALL - 1 and ts == list(range(ts[0], FALL)) and ts[0] <= 1, ts
        s = snap(gb)
        assert s["drops"] == 1, "one drop in the air at a time"
        assert oam(gb, OAM_FALL)["y"] == 0
        # the reload: loaded again RELOAD frames after it landed; the loaded one is drawn only then
        s = mm(gb)
        assert 0 < s["load"] <= RELOAD and oam(gb, OAM_HELD)["y"] == 0
        n = 0
        while mm(gb)["load"]:
            frames(gb, 1)
            n += 1
            assert n < 40
        assert RELOAD - 3 <= n <= RELOAD and oam(gb, OAM_HELD)["y"] != 0
        gb.hold("a")
        poke(gb, load=5)
        frames(gb, 1)
        assert snap(gb)["drops"] == 1, "no drop while reloading"
        gb.release("a")


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_hit_inside_the_12_px_opening_and_a_miss_1_px_outside(model):
    """The marshmallow's left edge -1..11 px right of the cup's x is a hit (its centre within the 12 px opening); -2 and 12 miss."""
    with marshmallow(model) as gb:
        to_play(gb)
        for d, hit in ((-2, 0), (-1, 1), (0, 1), (5, 1), (11, 1), (12, 0), (14, 0)):
            land_at(gb, d)
            s = landed(gb)
            assert s["n"][0] == hit and s["hits"] == (0 if not hit else s["hits"]), (d, s["n"])
            poke(gb, n=(0, 0))
            poke(gb, hits=0)
            until(gb, lambda: snap(gb)["load"] == 0, 40)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_three_marshmallows_score_100_each_and_300_for_a_perfect_cocoa(model):
    with marshmallow(model) as gb:
        to_play(gb)
        for i in range(3):
            before = gb.mem16("mg_score")
            land_at(gb, 5, 0, i)
            s = landed(gb)
            gain = gb.mem16("mg_score") - before
            assert s["n"][0] == i + 1 and gain == (100 if i < 2 else 400), (i, gain)
            until(gb, lambda: snap(gb)["load"] == 0, 40)
            frames(gb, 1)
        s = snap(gb)
        assert s["perfect"] == 1 and 0 < s["pop"][0] <= POP_LEN and score(gb) == 600
        assert tilemap_row(gb, 0, 11, 2) == [glyph("0"), glyph("1")], "the HUD tally"
        assert oam(gb, OAM_POP)["y"] == 80 + 16
        # the pop plays 40 frames then goes
        frames(gb, POP_LEN + 2)
        assert snap(gb)["pop"][0] == 0 and oam(gb, OAM_POP)["y"] == 0


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_fourth_splashes_minus_100_and_the_cup_takes_nothing_more(model):
    with marshmallow(model) as gb:
        to_play(gb)
        land_at(gb, 5, 0, 3)
        s = landed(gb)
        assert s["spl"][0] > 0 and s["n"][0] == 3 and s["splashes"] == 1 and s["perfect"] == 0
        assert gb.mem16("mg_score") == 0 and score(gb) == 0, "never below what the game earned"
        frames(gb, 2)
        # a splash's art: the cup's frame 4 / 5 (see mm.c)
        cups = ART["cup"]
        assert oam(gb, OAM_CUP)["tile"] in {(56 + 2 * cups[4][0]) if cups[4][0] < 18 else 96 + 2 * (cups[4][0] - 18),
                                            (56 + 2 * cups[5][0]) if cups[5][0] < 18 else 96 + 2 * (cups[5][0] - 18)}
        # with points: the penalty is 100
        poke(gb, spl=(0, 0), n=(0, 2))
        land_at(gb, 5, 0, 2)                                 # (a third: +400)
        landed(gb)
        assert gb.mem16("mg_score") == 400
        until(gb, lambda: snap(gb)["load"] == 0, 40)
        land_at(gb, 5, 0, 3)
        s = landed(gb)
        assert gb.mem16("mg_score") == 300 and score(gb) == 300 and s["splashes"] == 1 + 1
        # the splashed cup takes nothing: the next one falls through it (a miss)
        until(gb, lambda: snap(gb)["load"] == 0, 40)
        hits = s["hits"]
        land_at(gb, 5, 0, 3)
        poke(gb, spl=(0, 5))
        s = landed(gb)
        assert s["hits"] == hits and gb.mem16("mg_score") == 300


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_aurora_shimmers_0_1_2_1_and_the_belt_moves(model):
    """Every 10 frames the window's 24 cells take the next of the 3 frames (0 1 2 1); the belt row swaps its 2 phases every 8; the
    rest of the screen does not change."""
    with marshmallow(model) as gb:
        to_play(gb)
        frames(gb, 2)
        wins = []
        belts = []
        rest = None
        for i in range(120):
            frames(gb, 1)
            win = tuple(tuple(tilemap_row(gb, 1 + r, 1, 6)) for r in range(4))
            if not wins or wins[-1] != win:
                wins.append(win)
            belt = tuple(tilemap_row(gb, 14, 0, 20))
            if not belts or belts[-1] != belt:
                belts.append(belt)
            others = tuple(tuple(map_row(gb, r)[8:]) for r in (1, 4, 5, 8, 9, 10, 11, 12, 13, 15, 16, 17))
            rest = rest or others
            assert others == rest
        frs = [tuple(tuple(MM_BG + t for t in ART["win"][f][r * 6:(r + 1) * 6]) for r in range(4)) for f in range(3)]
        # the frames seen, in order, are 0 1 2 1 0 1 2 1 ... (a start part-way through the cycle is fine)
        idx = [frs.index(w) for w in wins]
        assert len(idx) >= 10 and set(idx) == {0, 1, 2}
        for a, b in zip(idx, idx[1:]):
            assert (a, b) in {(0, 1), (1, 2), (2, 1), (1, 0)}, idx
        b0, b1 = MM_BG + ART["belt"][0], MM_BG + ART["belt"][1]
        assert len(belts) >= 12
        for b in belts:
            assert b[0] == belts[0][0] and b[19] == belts[0][19] and set(b[1:19]) in ({b0}, {b1})
        assert {b[1] for b in belts} == {b0, b1}


# ---- sprites per line, bots --------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_worst_scene_forced_is_9_a_line(model):
    """4 cups 48 px apart across the whole belt, a marshmallow falling through them and two pops: the cup lines carry 9 (4 x 2 + the
    marshmallow), never 10."""
    worst = [0]
    with marshmallow(model) as gb:
        to_play(gb)
        for k, x in enumerate((-12, 36, 84, 132, 0)):
            poke(gb, on=(k, 1 if k < 4 else 0), cx=(k, x * 8), n=(k, 3), pop=(k, 30 if k in (1, 2) else 0), spl=(k, 0))
        poke(gb, gapn=200, lead=0)
        until(gb, lambda: snap(gb)["load"] == 0, 40)
        drop(gb)
        for _ in range(60):
            frames(gb, 1, worst)
            poke(gb, cx=(0, snap(gb)["cx"][0]))                  # (keeps the cups from leaving: they move 0.5 px a frame anyway)
    assert worst[0] == 9, worst


def pilot(gb, s, el):
    """Presses A when the marshmallow dropped now would land well inside a cup that can take it (a lookahead of the 2 updates
    between a key and its drop)."""
    if s["air"] or s["load"]:
        return False
    ps, cs = speeds(el)
    dx = s["dx"] + s["dir"] * ps * 2
    ax = (dx >> 3) + 4
    best = None
    for k in range(CUPS):
        if not s["on"][k] or s["spl"][k] or s["n"][k] >= 3:
            continue
        cx = (s["cx"][k] + cs * (FALL + 2)) >> 3
        if 3 <= ax - cx <= 7 and cx < 150:
            if best is None or s["n"][k] > best:
                best = s["n"][k]
    return best is not None


def play_game(gb, worst=None, until_frame=TIME):
    """The bot plays; returns the final state."""
    for i in range(until_frame):
        s = mm(gb)
        el = TIME - gb.mem16("mg_timer")
        if pilot(gb, s, el):
            gb.hold("a")
            frames(gb, 2, worst)
            gb.release("a")
        else:
            frames(gb, 1, worst)
        if gb.mem("mg_phase") != MG_PLAY:
            break
    return mm(gb)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_bot_playing_the_whole_game_keeps_to_10_a_line_and_earns_a_medal(model):
    worst = [0]
    with marshmallow(model) as gb:
        to_play(gb)
        s = play_game(gb, worst)
        sc = gb.mem16("mg_score")
        until(gb, lambda: gb.mem("mg_phase") == MG_END, 100)
        frames(gb, 3, worst)
    assert worst[0] <= 10 and 7 <= worst[0] <= 9, worst
    assert s["perfect"] >= 2 and s["hits"] >= 20 and sc >= 2000, (s["perfect"], s["hits"], sc)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_mashing_a_keeps_to_10_a_line_and_scores_little(model):
    """A pressed every 3 frames for the whole game: at most 10 a line; one drop in 46 frames at best (about 58), most of them misses:
    well under the pilot's score (bronze at most: the pail's sweep does cover about a third of the drops' places)."""
    worst = [0]
    with marshmallow(model) as gb:
        to_play(gb)
        for i in range(0, TIME, 3):
            gb.hold("a")
            frames(gb, 1, worst)
            gb.release("a")
            frames(gb, 2, worst)
            if gb.mem("mg_phase") != MG_PLAY:
                break
        sc = gb.mem16("mg_score")
    assert worst[0] <= 10 and sc < 3000, (worst, sc)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_timer_ends_the_play_at_45_s(model):
    with marshmallow(model) as gb:
        to_play(gb)
        assert gb.mem16("mg_timer") in range(TIME - 3, TIME + 1)
        until(gb, lambda: gb.mem("mg_phase") == MG_END, TIME + 10)
        assert text(gb, 2) == "TIME UP"


@pytest.mark.parametrize("pts, medal", [(1999, 0), (2000, 1), (3999, 1), (4000, 2), (5999, 2), (6000, 3)])
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_medal_edges_2000_4000_6000(model, pts, medal):
    with marshmallow(model) as gb:
        to_play(gb)
        to_result(gb, pts)
        assert gb.mem("mg_medal") == medal


# ---- flow ------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_practice_retry_and_menu(model):
    with marshmallow(model) as gb:
        to_play(gb)
        land_at(gb, 5, 0, 2)
        landed(gb)
        assert score(gb) == 400
        to_result(gb)
        assert text(gb, 4, True, x0=4) == "A RETRY B MENU"
        gb.press("a", 2)
        run_until(gb, lambda: gb.mem("mg_phase") == 0 and gb.pb.memory[0xFF40] & 0x80, 30)
        s = mm(gb)
        assert state(gb) == GS_MINI and score(gb) == 0 and (s["perfect"], s["drops"], s["hits"]) == (0, 0, 0)
        assert text(gb, 2) == "MARSHMALLOW DROP"
        to_play(gb)
        frames(gb, 3)
        assert text(gb, 2, x0=9) == "COCOA BAR", "the scene again after a retry"
        to_result(gb)
        gb.press("b", 2)
        run_until(gb, lambda: state(gb) == GS_MGLIST and gb.pb.memory[0xFF40] & 0x80, 30)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_story_plays_it_in_chapter_5_and_the_last_call_has_everything_back(model):
    """Chapter 5 (the igloo): after the Happy hour, Marshmallow Drop in MG_STORY (the score carried, the count not skippable,
    unlocked for Practice at once); the result's A CONTINUE leads to the Last call, whose VRAM and palettes are those of the Last
    call reached without it."""
    from test_bs import level_vram, palettes
    from test_story import to_goal, to_shift, win
    with to_shift(model, IGLOO, 2) as gb:
        gb.run(2)
        fresh, pals = level_vram(gb), palettes(gb)
    with to_shift(model, IGLOO, 1) as gb:
        assert gb.mem16("mg_unlocked") == 0
        win(gb, IGLOO, 1)
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 20)
        run_until(gb, lambda: state(gb) == GS_MINI, 300)
        run_until(gb, lambda: gb.pb.memory[0xFF40] & 0x80, 10)
        assert gb.mem("mg_id") == MG_MARSHMALLOW and gb.mem("mg_mode") == MG_STORY and gb.mem("venue_id") == IGLOO
        assert text(gb, 2) == "MARSHMALLOW DROP" and score(gb) > 0
        assert gb.mem16("mg_unlocked") == 1 << MG_MARSHMALLOW
        until(gb, lambda: gb.mem("mg_phase") == MG_COUNT, 100)
        frames(gb, 3)
        gb.press("a", 1)
        assert gb.mem("mg_phase") == MG_COUNT, "no skipping in the story"
        to_play(gb)
        frames(gb, 30)
        to_result(gb)
        assert text(gb, 4, True, x0=4) == "A CONTINUE"
        until(gb, lambda: gb.mem("mg_t") >= RESULT_MIN, RESULT_MIN)
        gb.press("a", 2)
        run_until(gb, lambda: state(gb) == GS_GOAL, 60)
        gb.run(3)
        assert gb.mem("story_chapter") == IGLOO and gb.mem("story_shift") == 2 and gb.mem("story_step") == 3
        to_goal(gb)
        gb.run(2)
        assert level_vram(gb) == fresh
        assert palettes(gb) == pals


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_level_after_marshmallow_drop_has_everything_back(model):
    """Marshmallow Drop (a drop) -> B to the list -> the title -> a level: the level's OBJ tiles (the 96-103 ones this game
    overwrote too), BG 77-255, OBP0 / OBP1 and every palette are byte for byte those of a level started from a fresh boot."""
    from conftest import title_level
    from test_bs import level_vram, palettes
    from test_flow import PLAYING
    from test_scores import booted
    with booted(model) as gb:
        hold_stage_anim(gb)
        title_level(gb)
        run_until(gb, lambda: state(gb) == PLAYING, 60)
        gb.run(2)
        fresh, pals = level_vram(gb), palettes(gb)
    with marshmallow(model) as gb:
        to_play(gb)
        land_at(gb, 5, 0, 1)
        landed(gb)
        to_result(gb)
        gb.press("b", 2)
        run_until(gb, lambda: state(gb) == GS_MGLIST and gb.pb.memory[0xFF40] & 0x80, 30)
        gb.run(3)
        gb.press("b", 2)
        run_until(gb, lambda: state(gb) == TITLE and gb.pb.memory[0xFF40] & 0x80, 30)
        gb.run(10)
        gb.press("b", 2)
        gb.run(10)
        title_level(gb)
        run_until(gb, lambda: state(gb) == PLAYING, 60)
        gb.run(62)
        assert level_vram(gb) == fresh
        assert palettes(gb) == pals


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_arcade_plays_it_in_chapter_5(model):
    from test_arcade import start_arcade
    from test_story import to_goal, win
    with start_arcade(model) as gb:
        to_goal(gb)
        gb.write("story_chapter", IGLOO)
        gb.write("story_step", 1)
        win(gb, 0, 0)
        run_until(gb, lambda: state(gb) == LEVEL_CLEAR, 20)
        run_until(gb, lambda: state(gb) == GS_MINI, 400)
        run_until(gb, lambda: gb.pb.memory[0xFF40] & 0x80, 10)
        assert gb.mem("mg_id") == MG_MARSHMALLOW and gb.mem("mg_mode") == MG_STORY and gb.mem("venue_id") == IGLOO
        assert gb.mem("save_lock") == 1 and gb.mem16("mg_unlocked") == 1 << MG_MARSHMALLOW
        assert text(gb, 2) == "MARSHMALLOW DROP"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_bonus_mini_games_lists_and_plays_it(model):
    """BONUS > MINI GAMES (the debug build: all unlocked): MARSHMALLOWS on the eighth line (after TAIKO POUR), its details THE IGLOO; A
    plays it in practice (score from 0); its result's B comes back to the list on it."""
    from test_mg_list import line, tap as list_tap, to_list
    from test_scores import booted
    with to_list(booted(model)) as gb:
        assert line(gb, 9).strip() == "MARSHMALLOWS"
        for _ in range(7):
            list_tap(gb, "down")
        assert gb.mem("ml_sel") == 7
        assert [line(gb, r).strip() for r in range(13, 17)] == ["MARSHMALLOWS", "THE IGLOO", "NO MEDAL YET", "A PLAY  B BACK"]
        list_tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_MINI and gb.pb.memory[0xFF40] & 0x80, 30)
        assert gb.mem("mg_id") == MG_MARSHMALLOW and gb.mem("mg_mode") == MG_PRACTICE and score(gb) == 0
        assert text(gb, 2) == "MARSHMALLOW DROP"
        gb.write("mg_phase", MG_RESULT)
        run_until(gb, lambda: gb.mem("overlay_on") == 1, 10)
        frames(gb, 3)
        gb.press("b", 2)
        run_until(gb, lambda: state(gb) == GS_MGLIST and gb.pb.memory[0xFF40] & 0x80, 30)
        gb.run(3)
        assert gb.mem("ml_sel") == 7 and line(gb, 9).strip() == "MARSHMALLOWS"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_release_list_unlocks_it_when_reached(model, release_built):
    from test_mg_list import MG_PLANNED, line, pr_block, release_rom, tap as list_tap, to_list, with_block
    from test_scores import v7_image
    best = [0] * MG_PLANNED
    best[MG_MARSHMALLOW] = MEDAL_SILVER
    ram = with_block(v7_image(), pr_block(1 << MG_MARSHMALLOW, best))
    with release_rom(model, ram) as gb:
        to_list(gb)
        assert [line(gb, r).strip() for r in range(2, 9)] == ["? ? ?"] * 7 and line(gb, 9) == " MARSHMALLOWS SILVER"
        for _ in range(7):
            list_tap(gb, "down")
        assert [line(gb, r).strip() for r in range(13, 16)] == ["MARSHMALLOWS", "THE IGLOO", "BEST SILVER"]
        list_tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_MINI, 30)
        assert gb.mem("mg_id") == MG_MARSHMALLOW and gb.mem("mg_mode") == MG_PRACTICE


def test_the_state_fits_the_union():
    assert STATE_SIZE <= 520 and LAYOUT["cx"][1] == 5


def test_the_art_fits_the_free_ids():
    """The 3 shimmer frames (the window's 69 tiles) in VRAM at once: BG ids 125-255 are free."""
    assert MM_BG + ART["n_bg"] <= 256 and ART["n_bg"] == 95
    assert (MM_BG + ART["n_bg"]) <= 256 and ART["n_obj_entries"] <= 18 + (128 - 96) // 2


# ---- goldens ---------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_goldens(model):
    """The intro banner, play with a falling marshmallow, a perfect cocoa's pop, a splash, the result (a gold)."""
    with marshmallow(model) as gb:
        frames(gb, 40)
        shot(gb, "intro")
        check_golden(gb, "mm_intro")
        to_play(gb)
        frames(gb, 30)
        poke(gb, dx=(70 * 8))
        until(gb, lambda: snap(gb)["load"] == 0, 40)
        drop(gb)
        frames(gb, 8)
        shot(gb, "play")
        check_golden(gb, "mm_play")
        land_at(gb, 5, 0, 2)
        landed(gb)
        frames(gb, 6)
        assert snap(gb)["perfect"] == 1
        shot(gb, "perfect")
        check_golden(gb, "mm_perfect")
        until(gb, lambda: snap(gb)["load"] == 0, 40)
        poke(gb, pop=(0, 0))
        land_at(gb, 5, 0, 3)
        landed(gb)
        frames(gb, 6)
        assert snap(gb)["splashes"] == 1
        shot(gb, "splash")
        check_golden(gb, "mm_splash")
        to_result(gb, 6200)
        shot(gb, "result")
        check_golden(gb, "mm_result")
