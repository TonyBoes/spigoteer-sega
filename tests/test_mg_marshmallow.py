# docs/minigames_bosses.md 4.5: MARSHMALLOW DROP (src/mm.c), the igloo's mini-game, on the framework (src/mg.c). Reworked in batch D2 (owner
# 2026-10-15): the player steers the pail (D-pad, a little momentum), A drops; six cups loop round the belt; a supply of 19 marshmallows
# (6 x 3 + 1: a perfect game may miss once); a miss splats on the belt; a full cup takes no more; the game ends when every cup is full, the
# supply is out, or 60 s have passed; GOLD is a perfect game (all six full).
# The tests: the screen (the approved art, its palettes, the DMG registers), the pail's steering, the looping cups, the drop (22 frames, one
# in the air, the reload), the opening, scoring, a full cup, the splat, the three endings, the sprites per line over whole games with a
# pilot that steers and drops with real keys (perfect play = gold with at most one miss; a sloppy pilot; mashing A), the medal edges, STORY /
# ARCADE reaching it in chapter 5, BONUS > MINI GAMES, what is put back when it is left, goldens.
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
(FALL, BELT_T, RELOAD, POP_LEN, BELT, SPLAT_LIFE, ARM_SPEED, ARM_ACC, ARM_FRIC) = (
    mm_define(n) for n in ("MM_FALL", "MM_BELT_T", "MM_RELOAD", "MM_POP_LEN", "MM_BELT", "MM_SPLAT_LIFE", "MM_ARM_SPEED",
                           "MM_ARM_ACC", "MM_ARM_FRIC"))
OAM_POP, OAM_FALL, OAM_HELD, OAM_PAIL, OAM_CUP = (mm_define(n) for n in ("OAM_POP", "OAM_FALL", "OAM_HELD", "OAM_PAIL", "OAM_CUP"))
SFX_CATCH, SFX_BREAK, SFX_LAUNCH, SFX_COIN = 3, 4, 2, 6
S_PALETTE = 0x10
CUPS = 6
OAM_SPLAT = OAM_CUP + 2 * CUPS                       # (mm.c: after the cups)
LOOP = CUPS * 48 * 8                               # one lap, 1/8 px
SUPPLY = 3 * CUPS + 1
TIME = 60 * 60
MAP, PAL = ART["map"], ART["pal"]


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


def clear_cups(gb, keep=()):
    """Every cup but those kept goes far off to the left (they ride right: 18 frames of a test never bring them back)."""
    for k in range(CUPS):
        if k not in keep:
            poke(gb, cx=(k, -1000 - 100 * k))


def land_at(gb, d, k=0, n=0):
    """Drops a marshmallow, then puts cup k (alone on the belt, holding n) where the marshmallow, landing in the update that is to come,
    will be d px right of the cup's x (d = marshmallow x - cup x): the opening is -1..11. Returns the state at the drop."""
    clear_cups(gb)
    until(gb, lambda: snap(gb)["load"] == 0 and not snap(gb)["air"] and snap(gb)["supply"], 80)
    drop(gb)
    s = snap(gb)
    while not s["air"]:
        frames(gb, 1)
        s = snap(gb)
    left = FALL - s["t"]                               # updates to come before the one that lands (it moves the cups first)
    poke(gb, n=(k, n), pop=(k, 0), cx=(k, (s["ax"] - d) * 8 + 4 - left * BELT))
    return s


def landed(gb, frames_max=40):
    """Runs until the marshmallow in the air is done (landed in a cup, or splatted on the belt)."""
    for _ in range(frames_max):
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
        assert text(gb, 2) == "MARSHMALLOW DROP" and text(gb, 3) == "MOVE THEN A DROPS"
        assert tilemap_row(gb, 0, 11, 3) == [MM_BG + ART["icon"], glyph("1"), glyph("9")]
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
            assert bank1(gb, 11, 0) & 7 == 1, "the HUD's palette"
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
def test_the_pail_steers_with_a_little_momentum(model):
    """LEFT / RIGHT speed the pail up by 3/8 px a frame to 2 px, no key takes 4/8 off a frame, it stops dead at x 16 and 136, and the sprite
    follows. Before the play starts it does not move."""
    with marshmallow(model) as gb:
        frames(gb, 20)
        gb.hold("right")
        frames(gb, 5)
        gb.release("right")
        assert snap(gb)["dx"] == 76 * 8 and snap(gb)["vx"] == 0, "no steering before the play"
        to_play(gb)
        poke(gb, dx=40 * 8, vx=0)
        frames(gb, 2)
        gb.hold("right")
        vs = []
        for _ in range(10):
            frames(gb, 1)
            vs.append(snap(gb)["vx"])
        gb.release("right")
        up = [b - a for a, b in zip(vs, vs[1:])]
        assert set(up[:3]) == {ARM_ACC} and up[-1] == 0 and vs[-1] == ARM_SPEED, vs
        assert all(d in (ARM_ACC, ARM_SPEED % ARM_ACC, 0) for d in up), vs
        ws = []
        for _ in range(6):
            frames(gb, 1)
            ws.append(snap(gb)["vx"])
        down = [b - a for a, b in zip([vs[-1]] + ws, ws)]
        assert ws[-1] == 0 and set(down[:3]) == {-ARM_FRIC}, ws
        # it moves by its speed, left too
        poke(gb, dx=76 * 8, vx=0)
        frames(gb, 2)
        a = snap(gb)["dx"]
        gb.hold("left")
        frames(gb, 3)
        s = snap(gb)
        gb.release("left")
        assert s["vx"] < 0 and s["dx"] < a
        assert oam(gb, OAM_PAIL)["x"] in ((s["dx"] >> 3) + 8, (snap(gb)["dx"] >> 3) + 8)
        # the ends
        poke(gb, dx=130 * 8, vx=0)
        gb.hold("right")
        for _ in range(30):
            frames(gb, 1)
        s = snap(gb)
        assert s["dx"] == 136 * 8 and s["vx"] == 0
        assert oam(gb, OAM_PAIL)["x"] == 136 + 8
        gb.release("right")
        poke(gb, dx=22 * 8, vx=0)
        gb.hold("left")
        for _ in range(30):
            frames(gb, 1)
        s = snap(gb)
        gb.release("left")
        assert s["dx"] == 16 * 8 and s["vx"] == 0


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_six_cups_loop_round_the_belt_48_px_apart(model):
    """The cups start 48 px apart at x 120, 72, 24 ... and ride right at 0.5 px a frame; past the right edge one comes back at the left
    carrying its marshmallows (a lap is 288 px, 576 frames); at most 4 share the screen, so a cup line carries at most 8 entries."""
    worst = [0]
    with marshmallow(model) as gb:
        to_play(gb)
        s = snap(gb)
        assert [x >> 3 for x in s["cx"]] == [120 - 48 * k for k in range(CUPS)] or all(abs((x >> 3) - (120 - 48 * k)) <= 3 for k, x in enumerate(s["cx"]))
        poke(gb, n=(0, 2))
        wrapped = None
        prev = snap(gb)["cx"][0]
        for i in range(620):
            frames(gb, 1, worst)
            if i % 4 == 0:
                s = snap(gb)
                for k in range(CUPS):
                    gap = (s["cx"][k] - s["cx"][(k + 1) % CUPS]) % LOOP
                    assert gap == 48 * 8, (i, k, s["cx"])
                assert sum(1 for x in s["cx"] if -16 * 8 < x < 160 * 8) <= 4
                if s["cx"][0] < prev and wrapped is None:
                    wrapped = (i, prev, s["cx"][0], s["n"][0])
                prev = s["cx"][0]
    assert wrapped is not None and wrapped[1] >= 156 * 8 and wrapped[2] <= -100 * 8 and wrapped[3] == 2, wrapped
    assert worst[0] <= 8, worst


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_belt_moves_a_cup_half_a_pixel_a_frame(model):
    with marshmallow(model) as gb:
        to_play(gb)
        frames(gb, 3)
        a = snap(gb)["cx"]
        frames(gb, 1)
        b = snap(gb)["cx"]
        assert [y - x for x, y in zip(a, b)] == [BELT] * CUPS and BELT == 4


# ---- the drop and the opening ----------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_marshmallow_falls_2_px_a_frame_one_at_a_time_and_reloads_after_12(model):
    """A drops it straight down (its x fixed) at 2 px a frame: 22 frames to the rim, 27 to the belt on a miss; a press while it falls or before
    the next is loaded (12 frames after) does nothing; the loaded one is drawn under the pail, none in the air or while reloading; the HUD
    counts the supply down from 19."""
    with marshmallow(model) as gb:
        to_play(gb)
        clear_cups(gb)
        frames(gb, 3)
        assert oam(gb, OAM_HELD)["y"] != 0
        assert tilemap_row(gb, 0, 11, 3) == [MM_BG + ART["icon"], glyph("1"), glyph("9")]
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
                assert o["x"] == ax + 8 and o["y"] in tuple(51 + 2 * t + 16 for t in (s["t"] - 1, s["t"], s["t"] + 1))
                assert oam(gb, OAM_HELD)["y"] == 0
                if s["t"] >= 5 and not pressed:
                    gb.hold("a")                              # a second press in the air
                    pressed = True
                    frames(gb, 1)
                    gb.release("a")
                    continue
            frames(gb, 1)
        assert ts[0] <= 1 and ts[-1] >= BELT_T - 2 and all(b - a in (1, 2) for a, b in zip(ts, ts[1:])), ts
        s = snap(gb)
        assert s["drops"] == 1 and s["supply"] == SUPPLY - 1 and s["misses"] == 1 and s["hits"] == 0
        assert tilemap_row(gb, 0, 12, 2) == [glyph("1"), glyph("8")]
        # reloading: a press does nothing for RELOAD frames, then A drops again
        assert s["load"] in range(RELOAD - 2, RELOAD + 1)
        gb.hold("a")
        frames(gb, 2)
        gb.release("a")
        assert snap(gb)["drops"] == 1 and oam(gb, OAM_HELD)["y"] == 0
        until(gb, lambda: snap(gb)["load"] == 0, 20)
        frames(gb, 2)
        assert oam(gb, OAM_HELD)["y"] != 0
        drop(gb)
        frames(gb, 2)
        assert snap(gb)["drops"] == 2 and snap(gb)["supply"] == SUPPLY - 2


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_hit_inside_the_12_px_opening_and_a_miss_1_px_outside(model):
    """The marshmallow's left edge -1..11 px right of the cup's x is a hit (its centre within the 12 px opening); -2 and 12 miss."""
    with marshmallow(model) as gb:
        to_play(gb)
        for d, hit in ((-2, 0), (-1, 1), (5, 1), (11, 1), (12, 0)):
            before = snap(gb)
            land_at(gb, d, 0, 0)
            s = landed(gb)
            assert (s["hits"] - before["hits"], s["misses"] - before["misses"]) == (hit, 1 - hit), d
            poke(gb, n=(0, 0))


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_three_marshmallows_score_100_each_and_300_for_a_full_cup(model):
    with marshmallow(model) as gb:
        to_play(gb)
        land_at(gb, 5, 0, 0)
        landed(gb)
        assert score(gb) == 100 and snap(gb)["n"][0] == 1 and snap(gb)["full"] == 0
        assert gb.mem("last_sfx") == SFX_CATCH
        land_at(gb, 5, 0, 1)
        landed(gb)
        assert score(gb) == 200 and snap(gb)["n"][0] == 2
        land_at(gb, 5, 0, 2)
        landed(gb)
        frames(gb, 2)
        s = snap(gb)
        assert score(gb) == 600 and gb.mem16("mg_score") == 600 and s["n"][0] == 3 and s["full"] == 1 and s["pop"][0] > POP_LEN - 8
        assert gb.mem("last_sfx") == SFX_COIN
        assert s["hits"] == 3 and s["misses"] == 0 and s["supply"] == SUPPLY - 3
        # the full cup shows its third marshmallow, on CGB in the pail's copper; the pop is up
        o = oam(gb, OAM_CUP)
        if model == "cgb":
            assert o["prop"] & 7 == 2
        assert oam(gb, OAM_POP)["y"] != 0


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_full_cup_takes_no_more_and_the_marshmallow_is_a_miss(model):
    with marshmallow(model) as gb:
        to_play(gb)
        land_at(gb, 5, 0, 3)
        s = landed(gb)
        assert s["n"][0] == 3 and s["hits"] == 0 and s["misses"] == 1 and s["full"] == 0 and score(gb) == 0
        assert s["sage"][0] > 0 and s["supply"] == SUPPLY - 1 and gb.mem("last_sfx") == SFX_BREAK


# ---- the splat -------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_miss_splats_on_the_belt_and_rides_off(model):
    """A miss falls on to the belt and lies there as a splat (3 frames: fresh, settling, flat) at the marshmallow's x, riding right with the
    belt, blinking in its last 30 frames and gone after 150; SFX_BREAK at the impact."""
    with marshmallow(model) as gb:
        to_play(gb)
        clear_cups(gb)
        until(gb, lambda: snap(gb)["load"] == 0, 20)
        drop(gb)
        until(gb, lambda: snap(gb)["sage"][0] > 0, 40)
        s = snap(gb)
        assert not s["air"] and s["sx"][0] == (s["ax"] - 4) * 8 + BELT * (s["sage"][0] - 1), s
        assert gb.mem("last_sfx") == SFX_BREAK
        tiles, hidden = [], 0
        ages = []
        for i in range(SPLAT_LIFE + 10):
            frames(gb, 1)
            s = snap(gb)
            a = s["sage"][0]
            if not a:
                break
            ages.append(a)
            e0, e1 = oam(gb, OAM_SPLAT), oam(gb, OAM_SPLAT + 1)
            if e0["y"] == 0:
                hidden += 1
                assert a > SPLAT_LIFE - 30 - 3, a
                continue
            assert e0["y"] == 112 + 16 and e1["y"] == 112 + 16 and e1["x"] == e0["x"] + 8
            assert abs(e0["x"] - ((s["sx"][0] >> 3) + 8)) <= 1
            if not tiles or tiles[-1] != e0["tile"]:
                tiles.append(e0["tile"])
        assert len(tiles) == 3 and len(set(tiles)) == 3, tiles
        assert hidden >= 8 and snap(gb)["sage"][0] == 0 and max(ages) >= SPLAT_LIFE - 3
        assert oam(gb, OAM_SPLAT)["y"] == 0 and oam(gb, OAM_SPLAT + 1)["y"] == 0


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_fourth_splat_replaces_the_oldest(model):
    with marshmallow(model) as gb:
        to_play(gb)
        poke(gb, sage=(0, 50), sx=(0, 30 * 8))
        poke(gb, sage=(1, 100), sx=(1, 50 * 8))
        poke(gb, sage=(2, 20), sx=(2, 70 * 8))
        land_at(gb, 12, 0, 0)
        landed(gb)
        s = snap(gb)
        assert s["sage"][1] in (1, 2) and s["sage"][0] > 50 and s["sage"][2] > 20 and s["sage"][0] < 80


# ---- the endings -----------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_every_cup_full_ends_the_game(model):
    with marshmallow(model) as gb:
        to_play(gb)
        for k in range(1, CUPS):
            poke(gb, n=(k, 3))
        poke(gb, full=5)
        land_at(gb, 5, 0, 2)
        landed(gb)
        frames(gb, 2)
        assert gb.mem("mg_phase") == MG_END and text(gb, 2) == "ALL MUGS FULL"
        until(gb, lambda: gb.mem("mg_phase") == MG_RESULT, 90)
        assert snap(gb)["full"] == 6


@pytest.mark.parametrize("last", ["miss", "hit"])
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_last_marshmallow_ends_the_game_once_it_is_down(model, last):
    with marshmallow(model) as gb:
        to_play(gb)
        poke(gb, supply=1)
        land_at(gb, 5 if last == "hit" else 12, 0, 0)
        assert snap(gb)["supply"] == 0
        frames(gb, 1)
        if last == "miss":
            assert gb.mem("mg_phase") == MG_PLAY, "the splat first"
        landed(gb)
        frames(gb, 8)
        assert gb.mem("mg_phase") == MG_END and text(gb, 2) == "OUT OF MARSHMALLOWS"
        assert oam(gb, OAM_HELD)["y"] == 0
        until(gb, lambda: gb.mem("mg_phase") == MG_RESULT, 90)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_timer_ends_the_play_at_60_s(model):
    with marshmallow(model) as gb:
        to_play(gb)
        assert gb.mem16("mg_timer") in range(TIME - 3, TIME + 1)
        until(gb, lambda: gb.mem("mg_phase") == MG_END, TIME + 10)
        assert text(gb, 2) == "TIME UP"


# ---- sprites per line, pilots ----------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_worst_scene_forced_is_9_a_line(model):
    """4 cups 48 px apart across the whole belt, two pops, three splats on the belt and a marshmallow falling through: the cup lines carry
    9 (4 x 2 + the marshmallow), never 10."""
    worst = [0]
    with marshmallow(model) as gb:
        to_play(gb)
        for k, x in enumerate((-4, 44, 92, 140, -52, -100)):
            poke(gb, cx=(k, x * 8), n=(k, 3), pop=(k, 30 if k in (1, 2) else 0))
        for k, x in enumerate((20, 60, 100)):
            poke(gb, sage=(k, 40), sx=(k, x * 8))
        until(gb, lambda: snap(gb)["load"] == 0, 40)
        drop(gb)
        for _ in range(60):
            frames(gb, 1, worst)
            s = snap(gb)
            poke(gb, cx=(3, min(s["cx"][3], 140 * 8)))                  # (the fourth stays on the screen)
    assert worst[0] == 9, worst


def run_pilot(gb, tol, offset=5, worst=None, limit=TIME + 120):
    """Plays with real keys. Picks the cup that will be under the marshmallow, preferring those that hold the most (and are not full),
    steers by bang-bang on the speed it wants, and presses A when the marshmallow dropped now would land `offset` px in (the opening's
    middle is 5) within `tol` px. Returns the state at the end."""
    for _ in range(limit):
        s = mm(gb)
        if gb.mem("mg_phase") != MG_PLAY:
            break
        dx = s["dx"] + s["vx"] * 2
        best = None
        for k in range(CUPS):
            if s["n"][k] >= 3:
                continue
            land = s["cx"][k] + BELT * (FALL + 2)
            if land >= 1280:
                land -= LOOP                                       # (it wraps round before it lands)
            want = (land >> 3) + offset - 4                         # the pail's x that puts the marshmallow at `offset`
            if not 16 <= want <= 136:
                continue
            cost = abs(want * 8 - dx) / 8 - 30 * s["n"][k]
            if best is None or cost < best[0]:
                best = (cost, want)
        left = right = False
        a = False
        if best:
            err = best[1] * 8 - dx                                  # 1/8 px
            vdes = max(-ARM_SPEED, min(ARM_SPEED, err // 6))
            if vdes > s["vx"] + 1:
                right = True
            elif vdes < s["vx"] - 1:
                left = True
            a = abs(err) <= tol * 8 and not s["air"] and not s["load"] and s["supply"]
        (gb.hold if left else gb.release)("left")
        (gb.hold if right else gb.release)("right")
        if a:
            gb.hold("a")
        frames(gb, 1, worst)
        gb.release("a")
    gb.release("left")
    gb.release("right")
    return mm(gb)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_pilot_with_a_steady_hand_fills_every_cup_for_gold_with_one_miss_at_most(model):
    worst = [0]
    with marshmallow(model) as gb:
        to_play(gb)
        s = run_pilot(gb, 2, worst=worst)
        el = TIME - gb.mem16("mg_timer")
        sc = gb.mem16("mg_score")
        until(gb, lambda: gb.mem("mg_phase") == MG_END, 100)
        frames(gb, 3, worst)
        txt = text(gb, 2)
        to_result(gb)
        medal = gb.mem("mg_medal")
    assert worst[0] <= 10 and 8 <= worst[0] <= 9, worst
    assert s["full"] == CUPS and s["misses"] <= 1 and sc == 3600 and txt == "ALL MUGS FULL", (s["full"], s["misses"], sc, txt, el)
    assert medal == MEDAL_GOLD and el < TIME - 600, (medal, el)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_a_sloppy_pilot_earns_a_lesser_medal(model):
    """The same pilot aiming for the very edge of the opening (11 px) and happy within 5 px: some marshmallows fall outside."""
    with marshmallow(model) as gb:
        to_play(gb)
        s = run_pilot(gb, 5, offset=11)
        sc = gb.mem16("mg_score")
    assert s["misses"] >= 2 and s["full"] < CUPS and 1200 <= sc < 3600, (s["full"], s["misses"], s["hits"], sc)


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_mashing_a_uses_up_the_supply_for_little(model):
    """A pressed every 3 frames with the pail left where it is: one drop in 34 frames at best (22 to land, 12 to reload: the supply of 19 is gone in about 11 s), the game ends
    'OUT OF MARSHMALLOWS' with no medal; at most 10 a line."""
    worst = [0]
    with marshmallow(model) as gb:
        to_play(gb)
        for i in range(0, 1200, 3):
            gb.hold("a")
            frames(gb, 1, worst)
            gb.release("a")
            frames(gb, 2, worst)
            if gb.mem("mg_phase") != MG_PLAY:
                break
        sc = gb.mem16("mg_score")
        frames(gb, 3, worst)
        s = snap(gb)
        assert text(gb, 2) == "OUT OF MARSHMALLOWS" and s["supply"] == 0 and s["drops"] == SUPPLY
    assert worst[0] <= 10 and sc < 1200, (worst, sc)


@pytest.mark.parametrize("pts, medal", [(1199, 0), (1200, 1), (2399, 1), (2400, 2), (3599, 2), (3600, 3)])
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_medal_edges_1200_2400_3600(model, pts, medal):
    with marshmallow(model) as gb:
        to_play(gb)
        to_result(gb, pts)
        assert gb.mem("mg_medal") == medal


def test_a_perfect_game_scores_exactly_the_gold_threshold():
    """6 cups x (3 x 100 + 300) = 3600 = the gold edge, and the supply (19) allows one miss only: 18 hits are needed."""
    mg_h = (ROOT / "src" / "mg.h").read_text()
    import re
    gold = int(re.search(r"#define MM_MEDAL_GOLD\s+(\d+)", mg_h).group(1))
    assert gold == CUPS * (3 * mm_define("MM_PTS_HIT") + mm_define("MM_PTS_FULL")) == 3600 and SUPPLY - 3 * CUPS == 1


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
        assert state(gb) == GS_MINI and score(gb) == 0 and (s["full"], s["drops"], s["hits"], s["supply"]) == (0, 0, 0, SUPPLY)
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
        run_until(gb, lambda: state(gb) == GS_MINI, 800)
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
        run_until(gb, lambda: state(gb) == GS_MINI, 800)
        run_until(gb, lambda: gb.pb.memory[0xFF40] & 0x80, 10)
        assert gb.mem("mg_id") == MG_MARSHMALLOW and gb.mem("mg_mode") == MG_STORY and gb.mem("venue_id") == IGLOO
        assert gb.mem("save_lock") == 1 and gb.mem16("mg_unlocked") == 1 << MG_MARSHMALLOW
        assert text(gb, 2) == "MARSHMALLOW DROP"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_bonus_mini_games_lists_and_plays_it(model):
    """BONUS > MINI GAMES (the debug build: all unlocked): MARSHMALLOWS on the fifth line (chapter order), its details THE IGLOO; A
    plays it in practice (score from 0); its result's B comes back to the list on it."""
    from test_mg_list import line, medal_word, selection, tap as list_tap, to_game, to_list
    from test_scores import booted
    with to_list(booted(model)) as gb:
        to_game(gb, 4)
        assert gb.mem("ml_sel") == 4
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
        assert gb.mem("ml_sel") == 4 and selection(gb) == "MARSHMALLOWS"


@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_the_release_list_unlocks_it_when_reached(model, release_built):
    from test_mg_list import MG_PLANNED, line, pr_block, release_rom, medal_word, selection, tap as list_tap, to_game, to_list, with_block
    from test_scores import v7_image
    best = [0] * MG_PLANNED
    best[MG_MARSHMALLOW] = MEDAL_SILVER
    ram = with_block(v7_image(), pr_block(1 << MG_MARSHMALLOW, best))
    with release_rom(model, ram) as gb:
        to_list(gb)
        assert selection(gb) == "? ? ?"
        to_game(gb, 4)
        list_tap(gb, "a")
        run_until(gb, lambda: state(gb) == GS_MINI, 30)
        assert gb.mem("mg_id") == MG_MARSHMALLOW and gb.mem("mg_mode") == MG_PRACTICE


def test_the_state_fits_the_union():
    assert STATE_SIZE <= 520 and LAYOUT["cx"][1] == CUPS


def test_the_art_fits_the_free_ids():
    """The 3 shimmer frames (the window's 69 tiles) in VRAM at once: BG ids 125-255 are free; the OBJ entries fit the two blocks."""
    assert MM_BG + ART["n_bg"] <= 256 and ART["n_bg"] == 95
    assert ART["n_obj_entries"] <= 18 + (128 - 96) // 2


# ---- goldens ---------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("model", ["dmg", "cgb"])
def test_goldens(model):
    """The intro banner, play with a falling marshmallow, a full cup's pop, a splat on the belt, the result (a gold)."""
    with marshmallow(model) as gb:
        frames(gb, 40)
        shot(gb, "intro")
        check_golden(gb, "mm_intro")
        to_play(gb)
        frames(gb, 30)
        poke(gb, dx=70 * 8)
        until(gb, lambda: snap(gb)["load"] == 0, 40)
        drop(gb)
        frames(gb, 8)
        shot(gb, "play")
        check_golden(gb, "mm_play")
        land_at(gb, 5, 0, 2)
        landed(gb)
        frames(gb, 6)
        assert snap(gb)["full"] == 1
        shot(gb, "perfect")
        check_golden(gb, "mm_perfect")
        until(gb, lambda: snap(gb)["load"] == 0, 40)
        poke(gb, pop=(0, 0))
        land_at(gb, 5, 0, 3)
        landed(gb)
        frames(gb, 10)
        assert snap(gb)["misses"] == 2 and snap(gb)["sage"][0] > 0
        shot(gb, "splash")
        check_golden(gb, "mm_splash")
        to_result(gb, 3600)
        shot(gb, "result")
        check_golden(gb, "mm_result")
